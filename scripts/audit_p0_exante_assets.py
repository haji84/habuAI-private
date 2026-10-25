#!/usr/bin/env python3
"""Audit actual ex-ante weather/road/DEM/model source availability, without issuing P0."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_osm_road_archive import verify_archive, ArchiveVerificationError

ROOT = Path(__file__).resolve().parents[1]
JST = ZoneInfo("Asia/Tokyo")

def _aware(text: str) -> datetime:
    result = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timezone-aware cutoff is required")
    return result.astimezone(JST)


def _inside(root: Path, path: Path) -> Path:
    root = root.resolve()
    target = path if path.is_absolute() else root / path
    resolved = target.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Source path escapes the trusted repository")
    return resolved


def audit(root: Path, night: str, cutoff: datetime, *,
          weather_snapshot: str | None = None) -> dict:
    from datetime import date
    if date.fromisoformat(night).isoformat() != night:
        raise ValueError("Invalid operational night")
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("Timezone-aware cutoff required")
    root = Path(root).resolve()
    cutoff = cutoff.astimezone(JST)
    start = datetime.fromisoformat(night + "T07:00:00+09:00")
    end = start + timedelta(days=1)
    checks = []

    def add(name, state, reason, **evidence):
        checks.append({"input": name, "status": state, "reason": reason, **evidence})

    if not start - timedelta(days=1) <= cutoff < end:
        add("cutoff", "BLOCKED", "Cutoff is outside a plausible ex-ante timeframe")

    if not weather_snapshot:
        add("weather", "BLOCKED", "No actual captured weather snapshot supplied")
    else:
        path = _inside(root, Path(weather_snapshot))
        try:
            payload = json.loads(path.read_bytes())
            if payload["schema_version"] != "habu-exante-weather-evidence-v1":
                raise ValueError("Invalid weather schema")
            if payload["operational_night"] != night:
                raise ValueError("Weather operational night mismatch")
            if payload.get("access_mode") != "noncommercial-research":
                raise ValueError("Weather source license mode unsupported")
            samples = payload["sites"]
            if len(samples) < 2 or set(row["island"] for row in samples) != {"奄美大島", "加計呂麻島"}:
                raise ValueError("Both island reference points are required")
            latest = _aware(payload["available_at_utc"])
            if latest > cutoff:
                raise ValueError("Weather was not available by requested cutoff")
            for row in samples:
                if _aware(row["available_at_utc"]) > cutoff:
                    raise ValueError("Weather site availability exceeds cutoff")
                if hashlib.sha256(row["raw_body_utf8"].encode("utf-8")).hexdigest() != row["raw_sha256"]:
                    raise ValueError("Weather bytes changed after receipt")
                if row["resolution_minutes"] != 60 or not row["future_hourly_rows"]:
                    raise ValueError("Unsupported weather time resolution")
                for hour in row["future_hourly_rows"]:
                    valid = _aware(hour["valid_at_jst"])
                    if not start <= valid < end:
                        raise ValueError("Hour belongs to a different exploration night")
            add("weather", "SOURCE_VERIFIED_NOT_PRODUCTION_READY",
                "Two archived hourly samples have internally consistent bytes/cutoff; road-scale interpolation and trusted retrieval attestation not yet verified",
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        except (OSError, UnicodeError, TypeError, ValueError, KeyError) as exc:
            add("weather", "BLOCKED", "Weather snapshot invalid or unavailable: " + str(exc))

    osm = root / "evidence/osm/osm_processing_audit.json"
    if osm.is_file():
        try:
            audit_json = json.loads(osm.read_text(encoding="utf-8"))
            if (audit_json.get("official_status") != "auxiliary_not_official" or
                    audit_json.get("candidate_cell_count") != 16990):
                raise ValueError("OSM processing metadata not consistent")
            source = verify_archive(root)
            add("road", "AUXILIARY_CANDIDATE_ONLY",
                "OSM ZIP raw bytes/CRC verified; 16,990 road candidate cells remain nonofficial and not a certified ex-ante model universe",
                candidate_cells=16990,
                archived_parts=source["part_count"],
                archive_sha256=source["sha256"],
                archive_bytes=source["archive_bytes"],
                archive_files=source["filenames"])
        except (OSError, KeyError, ValueError, ArchiveVerificationError) as exc:
            add("road", "BLOCKED", "OSM source audit invalid: " + str(exc))
    else:
        add("road", "BLOCKED", "No trusted OSM road audit artifact")

    # A source catalog/algorithm isn't an actual per-road DEM value dataset.
    dem_root = root / "data/raw/gis"
    dem_candidates = []
    if dem_root.is_dir():
        dem_candidates = [p for p in dem_root.rglob("*")
                          if p.is_file() and p.suffix.lower() in (".tif", ".tiff", ".asc", ".vrt")]
    if not dem_candidates:
        add("terrain", "BLOCKED", "No DEM raster with per-road derived elevation/slope/wind evidence")
    else:
        add("terrain", "BLOCKED", "DEM files exist but no trusted hashed 100m road-cell feature binding or coverage has been validated")

    learning = root / "data/processed/model_learning.json"
    if learning.is_file():
        add("learning", "BLOCKED", "Model-learning input exists but independent cutoffs/outcome audit not attested")
    else:
        add("learning", "BLOCKED", "Missing data/processed/model_learning.json")
    add("production_model", "BLOCKED",
        "Champion registry is SANDBOX_MECHANICS; no trusted production inference/activation and formal 100m×10min output")
    return {
        "schema_version": "habu-p0-exante-assets-audit-v1",
        "operational_night": night,
        "cutoff_time": cutoff.isoformat(),
        "status": "BLOCKED",
        "original_p0_issued": False,
        "items": checks,
        "note": "No P0 Freeze, 1km Recall, 100m±10min KPI or model promotion is produced by this audit.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--night", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--weather-snapshot")
    args = parser.parse_args()
    report = audit(args.root, args.night, _aware(args.cutoff),
                   weather_snapshot=args.weather_snapshot)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
