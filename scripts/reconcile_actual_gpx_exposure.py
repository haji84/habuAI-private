#!/usr/bin/env python3
"""Reconcile a REAL byte-exact GPX with event, individual and monthly ledgers.

Never reclassify a GPS passage as a verified search/negative. A count conflict
quarantines all candidate labels; no model_learning.json or P0 is written.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gpx_audit import utm52n, distance_m, mark_point_anomalies

JST = ZoneInfo("Asia/Tokyo")
MAX_GPX_BYTES = 20_000_000
MAX_GPX_POINTS = 100_000
MAX_CAPTURE_EVENTS = 1000


class ReconciliationError(ValueError):
    pass


def timestamp(value):
    if not isinstance(value, str):
        raise ReconciliationError("Timestamp must be a string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReconciliationError("Invalid timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ReconciliationError("Timezone missing")
    return result.astimezone(JST)


def night_for(when):
    local = when.astimezone(JST)
    if local.hour < 7:
        local -= timedelta(days=1)
    return local.date().isoformat()


def source_hash(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path):
    if not path.is_file():
        raise ReconciliationError("Missing capture or individual source: " + str(path))
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ReconciliationError("Invalid CSV columns")
        return list(reader)


def reconstruct_archive(directory: Path):
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "line-gpx-archive-v1":
        raise ReconciliationError("Unknown archive schema")
    parts = sorted(directory.glob("part_*.txt"))
    n = manifest.get("part_count")
    if type(n) is not int or not 1 <= n <= 100 or len(parts) != n:
        raise ReconciliationError("GPX part count conflict")
    if [x.name for x in parts] != [f"part_{i:03d}.txt" for i in range(n)]:
        raise ReconciliationError("GPX part names are not contiguous")
    raw = b"\n".join(part.read_bytes() for part in parts)
    if len(raw) > MAX_GPX_BYTES or len(raw) != manifest["raw_size_bytes"]:
        raise ReconciliationError("GPX raw byte count conflict")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest["raw_sha256"]:
        raise ReconciliationError("GPX source SHA conflict")
    return raw, manifest, digest


def parse_points(raw: bytes, *, expected: int):
    if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
        raise ReconciliationError("Untrusted GPX entity declaration")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ReconciliationError("GPX XML parse failure") from exc
    points = []
    for seq, el in enumerate(root.findall(".//{*}trkpt")):
        if len(points) >= MAX_GPX_POINTS:
            raise ReconciliationError("GPX point budget exceeded")
        try:
            lat, lon = float(el.attrib["lat"]), float(el.attrib["lon"])
            stamp = el.find("{*}time")
            if stamp is None or not stamp.text:
                raise ReconciliationError("Missing GPX timestamp")
            if not (math.isfinite(lat) and math.isfinite(lon)
                    and 27.0 <= lat <= 29.0 and 128.0 <= lon <= 130.5):
                raise ReconciliationError("Out-of-domain track point")
            hdop_tag = el.find("{*}hdop")
            hdop = float(hdop_tag.text) if hdop_tag is not None and hdop_tag.text else None
            if hdop is not None and (not math.isfinite(hdop) or hdop < 0):
                raise ReconciliationError("Invalid GPX HDOP")
            points.append({
                "sequence": seq,
                "latitude": lat, "longitude": lon,
                "time_utc": timestamp(stamp.text).astimezone(timezone.utc),
                "hdop": hdop,
            })
        except (KeyError, TypeError, ValueError) as exc:
            raise ReconciliationError("Malformed GPX track point") from exc
    if len(points) != expected or not points:
        raise ReconciliationError("GPX point count differs from archive")
    return mark_point_anomalies(points)


def load_capture_ledger(root, night):
    event_path = root / f"data/processed/capture_events/{night[:4]}/{night}.csv"
    individual_path = root / f"data/processed/individuals/{night[:4]}/{night}.csv"
    raw_log_path = root / f"data/raw/habu_logs/{night[:4]}/{night}.json"
    events = _rows(event_path)
    individuals = _rows(individual_path)
    raw_log = json.loads(raw_log_path.read_text(encoding="utf-8"))
    if raw_log.get("operational_date") != night:
        raise ReconciliationError("Source Habu log operational night mismatch")
    if not 1 <= len(events) <= MAX_CAPTURE_EVENTS:
        raise ReconciliationError("No valid candidate events")
    ids, result = set(), []
    for row in events:
        event_id = row.get("event_id")
        count_text = row.get("event_count")
        if (not event_id or event_id in ids or row.get("event_type") != "capture"
                or not isinstance(count_text, str) or not count_text.isdecimal()
                or int(count_text) < 1):
            raise ReconciliationError("Duplicate or invalid owner capture event")
        ids.add(event_id)
        time = timestamp(row["event_time_local"])
        if night_for(time) != night or row.get("operational_date") != night:
            raise ReconciliationError("Capture night differs from 07:00 rule")
        lat, lon = float(row["latitude"]), float(row["longitude"])
        if not (27 <= lat <= 29 and 128 <= lon <= 130.5):
            raise ReconciliationError("Bad capture coordinates")
        result.append({
            "event_id": event_id, "time": time,
            "latitude": lat, "longitude": lon,
            "count": int(count_text)
        })
    grouped = defaultdict(set)
    seen_individuals = set()
    for row in individuals:
        ident, eid = row.get("individual_id"), row.get("event_id")
        if (not ident or ident in seen_individuals or eid not in ids
                or row.get("operational_date") != night):
            raise ReconciliationError("Duplicate, orphan or wrong-night individual")
        seen_individuals.add(ident)
        grouped[eid].add(ident)
    if any(len(grouped[e["event_id"]]) != e["count"] for e in result):
        raise ReconciliationError("Individual and event counts differ")
    raw_events = Counter()
    for x in raw_log.get("events", []):
        if x.get("type") == "capture":
            when = timestamp(x["time_local"])
            if night_for(when) != night or type(x.get("individual_count")) is not int:
                raise ReconciliationError("Raw capture log record invalid")
            raw_events[(when.isoformat(), x["individual_count"])] += 1
    db_events = Counter((x["time"].isoformat(), x["count"]) for x in result)
    if raw_events != db_events:
        raise ReconciliationError("Raw log and processed events disagree")
    summary = raw_log.get("capture_summary") or {}
    total = sum(e["count"] for e in result)
    if (summary.get("individuals") != total
            or summary.get("capture_events") != len(result)):
        raise ReconciliationError("Raw log count summary mismatch")
    return result, {
        "raw_log_sha256": source_hash(raw_log_path),
        "capture_events_sha256": source_hash(event_path),
        "individuals_sha256": source_hash(individual_path),
        "raw_events": len(raw_events), "capture_events": len(result),
        "individual_count": total,
    }


def _bucket(dt):
    local = dt.astimezone(JST)
    return local.replace(minute=(local.minute // 10) * 10, second=0, microsecond=0)


def reconcile(root, night, *, gps_distance_m=100, gps_time_seconds=600):
    root = Path(root)
    manifest_dir = root / f"data/raw/gpx_archives/{night}-探索.gpx.lines"
    raw, manifest, sha = reconstruct_archive(manifest_dir)
    points = parse_points(raw, expected=manifest["trackpoint_count"])
    if any(night_for(p["time_utc"]) != night for p in points):
        raise ReconciliationError("GPX spans a different operational night")
    events, ledger = load_capture_ledger(root, night)
    baseline = json.loads((root / "dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    entries = [x for x in baseline.get("nights", []) if x.get("night") == night]
    if len(entries) != 1 or type(entries[0].get("count")) is not int:
        raise ReconciliationError("Cannot resolve unique frozen baseline night count")
    baseline_count = entries[0]["count"]
    recorded = ledger["individual_count"]
    eligible_points = []
    sampled = defaultdict(int)
    reasons = Counter()
    for p in points:
        if p["exclude_point"]:
            reasons["gpx_excluded_anomaly"] += 1
            continue
        if p["hdop"] is None or p["hdop"] > 10:
            reasons["hdop_missing_or_over_10"] += 1
            continue
        if p["segment_break_before"]:
            reasons["broken_segment_at_sample"] += 1
            continue
        eligible_points.append(p)
        x, y = utm52n(p["latitude"], p["longitude"])
        key = (math.floor(x/100), math.floor(y/100), _bucket(p["time_utc"]).isoformat())
        sampled[key] += 1
    matches = []
    for e in events:
        candidates = []
        for p in eligible_points:
            dt = abs((p["time_utc"]-e["time"].astimezone(timezone.utc)).total_seconds())
            if dt <= gps_time_seconds:
                distance = distance_m(e, p)
                if distance <= gps_distance_m:
                    candidates.append((dt, distance))
        if candidates:
            delta, dist = min(candidates)
            matches.append({
                "event_id": e["event_id"], "count": e["count"],
                "proximity": "GPX_TIME_SPACE_MATCH_ONLY",
                "minimum_time_difference_seconds": round(delta, 2),
                "distance_m": round(dist, 1)
            })
        else:
            matches.append({"event_id": e["event_id"], "count": e["count"],
                            "proximity": "NO_QUALIFIED_GPX_MATCH"})
    blockers = []
    if baseline_count != recorded:
        blockers.append({"code": "FROZEN_BASELINE_CAPTURE_COUNT_CONFLICT",
                         "baseline": baseline_count, "raw_event_and_individuals": recorded})
    if len([x for x in matches if x["proximity"]=="GPX_TIME_SPACE_MATCH_ONLY"]) != len(events):
        blockers.append({"code": "CAPTURE_GPX_PROXIMITY_INCOMPLETE"})
    blockers.append({"code": "SEARCH_EXPOSURE_AND_COMPLETE_OUTCOME_ATTESTATION_MISSING"})
    blockers.append({"code": "EX_ANTE_FORECAST_UNIVERSE_AND_FEATURE_AVAILABILITY_MISSING"})
    result = {
        "schema_version": "habu-actual-gpx-event-effort-reconciliation-v1",
        "operational_night": night,
        "status": "TRAINING_BLOCKED",
        "individual_capture_count_source": recorded,
        "individual_capture_count_frozen_baseline": baseline_count,
        "event_count": len(events),
        "event_individual_total": recorded,
        "gpx": {"source_sha256":sha, "point_count":len(points),
                "first_point_jst":points[0]["time_utc"].astimezone(JST).isoformat(),
                "last_point_jst":points[-1]["time_utc"].astimezone(JST).isoformat(),
                "eligible_sample_points":len(eligible_points),
                "qc_rejected_by_reason":dict(reasons),
                "sampled_100m_10min_units":len(sampled)},
        "event_gpx_matches": matches,
        "gpX_passage_evidence_only": True,
        "observed_negative_count": 0,
        "formal_model_training_rows": 0,
        "P0_scored": False,
        "stage1_top10_recall_scored": False,
        "formal_100m_10min_scored": False,
        "unknown_not_negative": True,
        "known_historical_exposure_csv_labels_promoted": False,
        "input_source_hashes": ledger,
        "blockers": blockers,
        "next_action": "Resolve five-versus-six individual mismatch using source evidence before registering any positive; verify searching effort and full outcomes before creating negatives; bind an independent ex-ante universe and per-input cutoff."
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--night", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.night != "2026-09-28":
        print(json.dumps({"status":"BLOCKED","reason":"Only byte-exact 2026-09-28 source supported by this first slice"},ensure_ascii=False))
        return 2
    result = reconcile(args.root, args.night)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result["status"] == "TRAINING_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
