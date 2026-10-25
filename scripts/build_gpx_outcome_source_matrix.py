#!/usr/bin/env python3
"""Crosswalk actual GPX nights to independently existing capture and reaction sources.

Do not infer a 0-capture night from missing logs or inventory statistics.
This is an evidence availability matrix, never a ModelLearning dataset.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from inventory_real_gpx_sources import build_inventory

ROOT = Path(__file__).resolve().parents[1]
QC = Path("evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv")


class SourceMatrixError(ValueError):
    pass


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _source(root: Path, relative: str):
    path = root / relative
    if not path.is_file():
        return {"present": False, "sha256": None}
    return {"present": True, "sha256": _sha(path)}


def build_source_matrix(root: Path = ROOT):
    root = Path(root)
    inventory = build_inventory(root)
    qc_file = root / QC
    if not qc_file.is_file():
        raise SourceMatrixError("Historical GPX QC registry is missing")
    with qc_file.open(encoding="utf-8-sig", newline="") as f:
        qc_rows = list(csv.DictReader(f))
    if len(qc_rows) != 13:
        raise SourceMatrixError("Expected 13 independent historical track QC rows")
    qc_by_night = {}
    for row in qc_rows:
        night = row["operational_night"]
        if night in qc_by_night:
            raise SourceMatrixError("Duplicate night in GPX QC history")
        qc_by_night[night] = row

    result = []
    for record in inventory["raw_gpx"]:
        nights = sorted(record.get("operational_night_point_counts", {}))
        base = {"gpx_path": record["source_path"],
                "gpx_sha256": record.get("sha256"),
                "gpx_valid": record.get("gpx_track_valid", False),
                "raw_gpx_points": record["points"]}
        if not nights:
            result.append({**base, "night": None, "classification": "INVALID_TRACK",
                           "positive": "UNKNOWN", "negative": "UNKNOWN",
                           "training_eligible": False})
            continue
        for night in nights:
            historical = qc_by_night.get(night)
            if historical is None:
                raise SourceMatrixError("GPX night missing from independent historical QC")
            if historical["sha256"] != record.get("sha256"):
                raise SourceMatrixError("Historical QC SHA differs from repository raw GPX")
            if int(historical["gps_points"]) != record["points"]:
                raise SourceMatrixError("Historical QC point count differs")
            if record.get("gpx_track_valid") is False:
                condition = "GPX_CLOCK_OR_SCHEMA_BLOCKED"
            else:
                condition = "OUTCOME_LEDGER_MISSING"
            raw_log = f"data/raw/habu_logs/{night[:4]}/{night}.json"
            captures = f"data/processed/capture_events/{night[:4]}/{night}.csv"
            individuals = f"data/processed/individuals/{night[:4]}/{night}.csv"
            sources = {role: _source(root, rel) for role, rel in (
                ("raw_owner_habu_log", raw_log),
                ("capture_event_ledger", captures),
                ("individual_ledger", individuals))}
            if all(s["present"] for s in sources.values()) and record.get("gpx_track_valid"):
                condition = "PRESENT_BUT_OUTCOME_AND_EXPOSURE_AUDIT_REQUIRED"
            result.append({
                **base, "night": night,
                "sampled_points_this_night": record["operational_night_point_counts"][night],
                "historical_qc_path": QC.as_posix(),
                "historical_qc_sha256": _sha(qc_file),
                "sources": sources, "classification": condition,
                "positive": "UNKNOWN_UNTIL_INDIVIDUAL_EVENT_VALIDATION",
                "negative": "UNKNOWN_UNTIL_SEARCH_EFFORT_AND_COMPLETE_OUTCOME",
                "training_eligible": False, "official_kpi_eligible": False,
            })
    nights = {r["night"] for r in result if r["night"]}
    missing = sorted(set(qc_by_night) - nights)
    if missing:
        raise SourceMatrixError("Historical QC nights missing corresponding original GPX: " + ",".join(missing))
    counts = Counter(r["classification"] for r in result)
    return {"schema_version": "habu-gpx-outcome-source-availability-v1",
            "status": "BLOCKED_MISSING_COMPLETE_OUTCOMES_AND_EXANTE_FEATURES",
            "source_qc_sha256": _sha(qc_file),
            "raw_file_count": inventory["raw_gpx_files"],
            "raw_point_count": inventory["raw_gpx_track_points"],
            "unique_nights": len(nights),
            "august_nights": sum(n.startswith("2026-08") for n in nights),
            "september_nights": sum(n.startswith("2026-09") for n in nights),
            "category_counts": dict(counts),
            "nights": sorted(result, key=lambda r: (r["night"] or "", r["gpx_path"])),
            "verified_positive_training_rows": 0,
            "verified_negative_training_rows": 0,
            "unknown_policy": "No original owner log means unknown, not zero captures",
            "original_p0_issued": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = build_source_matrix(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "raw_file_count", "raw_point_count",
                                            "august_nights", "september_nights",
                                            "category_counts", "verified_positive_training_rows",
                                            "verified_negative_training_rows")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    main()
