#!/usr/bin/env python3
"""Inventory real raw GPX tracks and label eligibility by source, never by silence.

A GPX without owner capture AND complete search/outcome evidence is UNKNOWN,
not a zero-capture night. This tool NEVER builds model_learning.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
JST = ZoneInfo("Asia/Tokyo")
MAX_SOURCE_BYTES = 15_000_000
MAX_POINTS_PER_TRACK = 100_000


class InventoryError(ValueError):
    pass


def _time(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise InventoryError("GPX timestamps must be timezone-aware")
    return dt.astimezone(JST)


def _night(value: datetime) -> str:
    local = value.astimezone(JST)
    if local.hour < 7:
        local -= timedelta(days=1)
    return local.date().isoformat()


def audit_real_gpx(path: Path):
    if not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
        raise InventoryError("Missing or oversized raw GPX")
    if b"<!DOCTYPE" in path.read_bytes()[:8192] or b"<!ENTITY" in path.read_bytes()[:8192]:
        raise InventoryError("Unsupported XML entity declaration")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            digest.update(chunk)
    count = 0
    start = None
    end = None
    nights = Counter()
    backward_time_jumps = 0
    try:
        for event, element in ET.iterparse(path, events=("end",)):
            if element.tag.rsplit("}", 1)[-1] != "trkpt":
                continue
            count += 1
            if count > MAX_POINTS_PER_TRACK:
                raise InventoryError("Too many GPX track points")
            lat = float(element.attrib["lat"])
            lon = float(element.attrib["lon"])
            if not 27 <= lat <= 29 or not 128 <= lon <= 130.5:
                raise InventoryError("GPX point outside expected Amami domain")
            times = [x for x in element if x.tag.rsplit("}", 1)[-1] == "time"]
            if len(times) != 1 or not times[0].text:
                raise InventoryError("GPX point missing timestamp")
            dt = _time(times[0].text)
            if end is not None and dt < end:
                backward_time_jumps += 1
            start = start or dt
            end = dt
            nights[_night(dt)] += 1
            element.clear()
    except (ET.ParseError, KeyError, TypeError, ValueError) as exc:
        raise InventoryError("Malformed or out-of-order GPX") from exc
    if count < 2:
        raise InventoryError("Too few GPX samples")
    return {
        "source_path": path.as_posix(), "sha256": digest.hexdigest(),
        "source_bytes": path.stat().st_size,
        "points": count, "start_jst": start.isoformat(), "end_jst": end.isoformat(),
        "operational_night_point_counts": dict(nights),
        "gpx_track_valid": backward_time_jumps == 0,
        "backward_time_jumps": backward_time_jumps,
        "complete_search_effort_verified": False,
        "complete_habu_outcome_ledger_verified": False,
        "negative_label_eligible": False,
        "observed_zero_captures": None,
        "scientific_label_status": "UNKNOWN_OUTCOME_EFFORT" if backward_time_jumps == 0 else "TRACK_CLOCK_QC_FAILED",
    }


def build_inventory(root: Path = ROOT) -> dict:
    root = Path(root)
    paths = sorted((root / "data/raw/gpx").glob("*.gpx"))
    records = []
    for path in paths:
        try:
            record = audit_real_gpx(path)
        except (InventoryError, OSError, ValueError) as exc:
            record = {"gpx_track_valid": False, "scientific_label_status": "TRACK_INVALID",
                      "points": 0, "reason": str(exc), "negative_label_eligible": False}
        record["source_path"] = path.relative_to(root).as_posix()
        # A filename with a date is not independent evidence of when and how
        # long the owner actually searched, or that all captures were recorded.
        record["archive_class"] = "RAW_GPX_SOURCE_UNQUALIFIED"
        records.append(record)
    manifests = sorted((root/"data/raw/gpx_archives").glob("*.gpx.lines/manifest.json"))
    archived = []
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (manifest.get("schema_version") != "line-gpx-archive-v1" or
                not re.fullmatch("[a-f0-9]{64}", manifest.get("raw_sha256", ""))):
            raise InventoryError("Invalid reconstructed-GPX manifest")
        archived.append({
            "source_manifest":path.relative_to(root).as_posix(),
            "operational_night_claimed":manifest["operational_date"],
            "declared_points":manifest["trackpoint_count"],
            "declared_raw_sha256":manifest["raw_sha256"],
            "completeness": "ARCHIVE_REQUIRES_BYTE_EXACT_RECONSTRUCTION",
            "negative_label_eligible": False,
        })
    # Independent capture-event and individual ledgers must both be present.
    captured = {
        path.stem for path in (root/"data/processed/capture_events").rglob("*.csv")
    }
    individual = {
        path.stem for path in (root/"data/processed/individuals").rglob("*.csv")
    }
    for row in records:
        nights = set(row["operational_night_point_counts"])
        row["paired_event_and_individual_ledgers"] = bool(nights & captured & individual)
        # Even if a CSV happens to exist, GPS alone cannot certify complete
        # search effort, Negative, or a usable ex-ante forecast universe.
    return {
        "schema_version": "habu-raw-track-evidence-inventory-v1",
        "status": "TRAINING_INPUTS_INCOMPLETE",
        "raw_gpx_files": len(records),
        "raw_gpx_track_points": sum(x["points"] for x in records),
        "archive_manifests": len(archived),
        "raw_gpx": records,
        "archives": archived,
        "formal_model_learning_rows": 0,
        "official_original_p0_scored": False,
        "reason": "Raw track presence is not proof of complete searched exposure, individual outcome capture ledger, historical ex-ante weather/road/terrain features, or an untouched confirmation split.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    out = build_inventory(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":out["status"], "raw_gpx_files":out["raw_gpx_files"],
        "raw_gpx_track_points":out["raw_gpx_track_points"],
        "archive_manifests":out["archive_manifests"],
        "formal_model_learning_rows": 0
    },ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
