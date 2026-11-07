#!/usr/bin/env python3
"""Audit actual ex-ante weather/road/DEM/model source availability, without issuing P0."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_osm_road_archive import verify_archive, ArchiveVerificationError
from acquire_exante_weather import MAX_RESPONSE_BYTES, validate_archived_sample, validate_sites

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


class _AssetBlocked(ValueError):
    pass


def _strict_aware(value: str) -> datetime:
    if type(value) is not str or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?"
            r"(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", value):
        raise ValueError("Strict aware timestamp required")
    return _aware(value)


def _terrain_evidence(private, report_path, expected_sha, cutoff):
    from build_gsi_road_dem import (ByteBudget, CELLS_SHA256, child, digest, encoded,
                                    join_road_dem, private_root, validate_derived)

    if private is None or report_path is None or type(expected_sha) is not str or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise _AssetBlocked("TERRAIN_REPORT_BINDING_REQUIRED")
    root = private_root(private)
    report_file = child(root, report_path)
    with report_file.open("rb") as stream:
        raw = stream.read(256 * 1024 + 1)
    if len(raw) > 256 * 1024 or digest(raw) != expected_sha:
        raise _AssetBlocked("TERRAIN_REPORT_HASH_MISMATCH")
    report = json.loads(raw)
    if (encoded(report) != raw or report["schema_version"] != "gsi-road-dem-conversion-v1" or
            report["target_crs"] != "EPSG:32652" or report["road_sha256"] != CELLS_SHA256 or
            report["formal_p0_eligible"] is not False or report["terrain_wind_shielding_verified"] is not False):
        raise _AssetBlocked("TERRAIN_REPORT_SCHEMA_OR_SCOPE_INVALID")
    completed = _strict_aware(report["completed_at"])
    if completed >= cutoff:
        raise _AssetBlocked("TERRAIN_NOT_BEFORE_CUTOFF")
    names = ("verified-public-roads.csv", "road-neighbour-dem-50m.asc",
             "required-node-source-map.csv", "road-dem-join.json")
    artifacts = report["artifacts"]
    if type(artifacts) is not list or len(artifacts) != len(names):
        raise _AssetBlocked("TERRAIN_DERIVED_CLOSURE_INVALID")
    by_name = {Path(a["path"]).name: a for a in artifacts}
    if set(by_name) != set(names):
        raise _AssetBlocked("TERRAIN_DERIVED_CLOSURE_INVALID")
    paths = [a["path"] for a in artifacts] + [a["readiness_receipt"]["path"] for a in artifacts]
    if len(set(p.casefold() for p in paths)) != len(paths):
        raise _AssetBlocked("TERRAIN_DERIVED_CLOSURE_INVALID")
    budget = ByteBudget()
    for a in artifacts:
        if a["schema_version"] != "gsi-derived-readiness-v1" or a["code_sha256"] != report["code_sha256"]:
            raise _AssetBlocked("TERRAIN_DERIVED_CLOSURE_INVALID")
        for key in ("source_received_at", "derived_at", "materialized_at", "audited_at", "usable_at"):
            if _strict_aware(a[key]) > completed:
                raise _AssetBlocked("TERRAIN_DERIVED_AFTER_COMPLETION")
        validate_derived(root, a, budget)
    road, dem, _, join = (by_name[name] for name in names)
    if road["sha256"] != CELLS_SHA256:
        raise _AssetBlocked("TERRAIN_ROAD_SOURCE_MISMATCH")
    with child(root, join["path"]).open("rb") as stream:
        join_raw = stream.read(join["size_bytes"] + 1)
    if len(join_raw) != join["size_bytes"] or digest(join_raw) != join["sha256"]:
        raise _AssetBlocked("TERRAIN_DERIVED_CHANGED")
    recorded = json.loads(join_raw)
    join_cutoff = _strict_aware(recorded["cutoff_time"])
    if join_cutoff > _strict_aware(join["derived_at"]):
        raise _AssetBlocked("TERRAIN_DERIVED_CLOCK_ORDER_INVALID")
    replayed = join_road_dem(child(root, road["path"]), child(root, dem["path"]),
        road_sha256=road["sha256"], dem_sha256=dem["sha256"], dem_epsg=32652,
        road_available_at=road["usable_at"], dem_available_at=dem["usable_at"],
        cutoff_time=recorded["cutoff_time"])
    if encoded({key: recorded[key] for key in replayed}) != encoded(replayed):
        raise _AssetBlocked("TERRAIN_RECOMPUTATION_MISMATCH")
    counts = {key: replayed[key] for key in ("total_cells", "coverage_cells", "missing_cells")}
    if encoded({key: report[key] for key in counts}) != encoded(counts) or report["status"] != replayed["status"]:
        raise _AssetBlocked("TERRAIN_RECOMPUTATION_MISMATCH")
    budget = ByteBudget()
    for artifact in artifacts:
        validate_derived(root, artifact, budget)
    with child(root, report_path).open("rb") as stream:
        if stream.read(len(raw) + 1) != raw:
            raise _AssetBlocked("TERRAIN_DERIVED_CHANGED")
    return dict(**counts, sha256=expected_sha, joined_sha256=join["sha256"],
                readiness_pairs_verified=len(artifacts), available_at=completed.isoformat(),
                source_authentication="NOT_ATTESTED", formal_p0_eligible=False,
                terrain_wind_shielding_verified=False)


def _check_private_weather_context(root, payload, cutoff):
    if payload["provider"] != "Open-Meteo" or payload["source_class"] != "forecast_predictor":
        raise _AssetBlocked("WEATHER_SOURCE_SCOPE_INVALID")
    with (root / "features/weather_sampling_sites.json").open("rb") as stream:
        config_raw = stream.read(65537)
    if len(config_raw) > 65536:
        raise _AssetBlocked("WEATHER_SITE_CONFIG_INVALID")
    config = json.loads(config_raw, object_pairs_hook=_unique_weather_object)
    if type(config) is not dict or type(config.get("sites")) is not list or any(type(row) is not dict for row in config["sites"]):
        raise _AssetBlocked("WEATHER_SITE_CONFIG_INVALID")
    expected = {site["site_id"]: (site["island"], [site["latitude"], site["longitude"]])
                for site in validate_sites(config)}
    samples = payload["sites"]
    actual = {site["site_id"]: (site["island"], site["requested_point"]) for site in samples}
    if len(samples) != len(actual) or actual != expected:
        raise _AssetBlocked("WEATHER_REGISTERED_SITES_MISMATCH")
    started = _strict_aware(payload["acquisition_started_at_utc"])
    latest = _strict_aware(payload["available_at_utc"])
    received = [_strict_aware(site["available_at_utc"]) for site in samples]
    if started > min(received) or latest != max(received):
        raise _AssetBlocked("WEATHER_RECEIPT_CLOCK_ORDER_INVALID")
    if latest >= cutoff:
        raise _AssetBlocked("WEATHER_NOT_BEFORE_CUTOFF")


def _unique_weather_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _AssetBlocked("WEATHER_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _private_provider_hours(row, cutoff):
    raw = json.loads(row["raw_body_utf8"], object_pairs_hook=_unique_weather_object)
    expected_units = {"time": "iso8601", "temperature_2m": "°C", "relative_humidity_2m": "%",
        "precipitation": "mm", "pressure_msl": "hPa", "wind_speed_10m": "m/s", "wind_direction_10m": "°"}
    units = raw.get("hourly_units")
    if type(units) is not dict or any(units.get(key) != value for key, value in expected_units.items()):
        raise _AssetBlocked("WEATHER_PROVIDER_UNITS_MISMATCH")
    for stamp in raw["hourly"]["time"]:
        if type(stamp) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}", stamp):
            raise _AssetBlocked("WEATHER_PROVIDER_JST_HOUR_REQUIRED")
        datetime.fromisoformat(stamp)
    future_hours = sum(_strict_aware(hour["valid_at_jst"]) > cutoff for hour in row["future_hourly_rows"])
    if not future_hours:
        raise _AssetBlocked("WEATHER_NO_POSTCUTOFF_HOURS")
    return future_hours


def audit(root: Path, night: str, cutoff: datetime, *,
          weather_snapshot: str | None = None, weather_root: Path | None = None,
          weather_sha256: str | None = None, terrain_root: Path | None = None,
          terrain_report: str | None = None, terrain_sha256: str | None = None) -> dict:
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

    private_weather = weather_root is not None or weather_sha256 is not None
    if not weather_snapshot and not private_weather:
        add("weather", "BLOCKED", "No actual captured weather snapshot supplied")
    else:
        if not private_weather:
            path = _inside(root, Path(weather_snapshot))
        try:
            if private_weather:
                from build_gsi_road_dem import child, private_root

                if (weather_root is None or not weather_snapshot or type(weather_sha256) is not str or
                        not re.fullmatch(r"[0-9a-f]{64}", weather_sha256)):
                    raise _AssetBlocked("WEATHER_ARCHIVE_BINDING_REQUIRED")
                path = child(private_root(weather_root), weather_snapshot)
                max_archive_bytes = 4 * MAX_RESPONSE_BYTES + 256 * 1024
                with path.open("rb") as stream:
                    weather_raw = stream.read(max_archive_bytes + 1)
                if len(weather_raw) > max_archive_bytes or hashlib.sha256(weather_raw).hexdigest() != weather_sha256:
                    raise _AssetBlocked("WEATHER_ARCHIVE_HASH_MISMATCH")
            else:
                weather_raw = path.read_bytes()
            payload = json.loads(weather_raw, object_pairs_hook=_unique_weather_object) if private_weather else json.loads(weather_raw)
            if payload["schema_version"] != "habu-exante-weather-evidence-v1":
                raise ValueError("Invalid weather schema")
            if payload["operational_night"] != night:
                raise ValueError("Weather operational night mismatch")
            if payload.get("access_mode") != "noncommercial-research":
                raise ValueError("Weather source license mode unsupported")
            samples = payload["sites"]
            if len(samples) < 2 or set(row["island"] for row in samples) != {"奄美大島", "加計呂麻島"}:
                raise ValueError("Both island reference points are required")
            if private_weather:
                _check_private_weather_context(root, payload, cutoff)
            elif _aware(payload["available_at_utc"]) > cutoff:
                raise ValueError("Weather was not available by requested cutoff")
            postcutoff_hours = 0
            for row in samples:
                if not private_weather and _aware(row["available_at_utc"]) > cutoff:
                    raise ValueError("Weather site availability exceeds cutoff")
                if hashlib.sha256(row["raw_body_utf8"].encode("utf-8")).hexdigest() != row["raw_sha256"]:
                    raise ValueError("Weather bytes changed after receipt")
                if row["resolution_minutes"] != 60 or not row["future_hourly_rows"]:
                    raise ValueError("Unsupported weather time resolution")
                for hour in row["future_hourly_rows"]:
                    valid = _aware(hour["valid_at_jst"])
                    if not start <= valid < end:
                        raise ValueError("Hour belongs to a different exploration night")
                validate_archived_sample(row, night)
                if private_weather:
                    postcutoff_hours += _private_provider_hours(row, cutoff)
            if private_weather:
                with child(private_root(weather_root), weather_snapshot).open("rb") as stream:
                    if stream.read(len(weather_raw) + 1) != weather_raw:
                        raise _AssetBlocked("WEATHER_ARCHIVE_CHANGED")
            private_counts = {}
            if private_weather:
                private_counts = dict(sample_sites=len(samples), post_cutoff_hourly_rows=postcutoff_hours,
                                      hourly_rows=sum(len(site["future_hourly_rows"]) for site in samples))
            add("weather", "SOURCE_VERIFIED_NOT_PRODUCTION_READY",
                "Two archived hourly samples have internally consistent bytes/cutoff; road-scale interpolation and trusted retrieval attestation not yet verified",
                sha256=hashlib.sha256(weather_raw).hexdigest(), **private_counts)
        except _AssetBlocked as exc:
            add("weather", "BLOCKED", str(exc))
        except (OSError, UnicodeError, TypeError, ValueError, KeyError, AttributeError, OverflowError, RecursionError) as exc:
            reason = ("WEATHER_PRIVATE_EVIDENCE_INVALID" if private_weather else
                      "Weather snapshot invalid or unavailable: " + str(exc))
            add("weather", "BLOCKED", reason)

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
    if any(value is not None for value in (terrain_root, terrain_report, terrain_sha256)):
        try:
            terrain = _terrain_evidence(terrain_root, terrain_report, terrain_sha256, cutoff)
            add("terrain", "TERRAIN_RECOMPUTED_NOT_PRODUCTION_READY",
                "Exact archived road and DEM inputs reproduced the auxiliary terrain coverage. "
                "Source authentication and wind shielding remain unverified.", **terrain)
        except _AssetBlocked as exc:
            add("terrain", "BLOCKED", str(exc))
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError):
            add("terrain", "BLOCKED", "TERRAIN_PRIVATE_EVIDENCE_INVALID")
    elif not dem_candidates:
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
    parser.add_argument("--weather-root", type=Path, help="Weather evidence directory outside Git")
    parser.add_argument("--weather-sha256", help="Expected SHA-256 of the private weather archive")
    parser.add_argument("--terrain-root", type=Path, help="Terrain evidence directory outside Git")
    parser.add_argument("--terrain-report", help="Relative GSI conversion report below the private terrain root")
    parser.add_argument("--terrain-sha256", help="Expected SHA-256 of the exact conversion report bytes")
    args = parser.parse_args()
    private_sources = any(value is not None for value in
        (args.weather_root, args.weather_sha256, args.terrain_root, args.terrain_report, args.terrain_sha256))
    try:
        cutoff = _strict_aware(args.cutoff) if private_sources else _aware(args.cutoff)
    except (ValueError, OverflowError):
        parser.error("A valid timezone-aware cutoff is required")
    report = audit(args.root, args.night, cutoff,
                   weather_snapshot=args.weather_snapshot, weather_root=args.weather_root,
                   weather_sha256=args.weather_sha256, terrain_root=args.terrain_root,
                   terrain_report=args.terrain_report, terrain_sha256=args.terrain_sha256)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
