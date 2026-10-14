"""Read-only ex-ante ForecastUniverse/Feature Snapshot binding.

This is a preproduction input-integrity check, never production Champion authority.
It cannot reconstruct source availability or prove today's forecast is issuable.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from master_contracts import canonical_bytes, digest, safe_path, validate_night
from model_evaluation import _coordinates

JST = ZoneInfo("Asia/Tokyo")
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 384 * 1024 * 1024
MAX_FORECAST_ROWS = 2_000_000
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
POST_OUTCOME_FIELDS = {
    "label", "observed", "label_available_at", "outcome", "actual_capture",
    "capture_event_ids", "capture_count", "gpx_trace", "negative_observed",
}


def _time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timestamp requires a timezone")
    return result


def _night(value: datetime) -> str:
    return (value.astimezone(JST) - timedelta(hours=7)).date().isoformat()


def _read_bound(root: Path, ref: dict, consumed: dict, budget: list[int]):
    if not isinstance(ref, dict):
        raise ValueError("Input reference must be an object")
    path, expected = ref.get("path"), ref.get("sha256")
    if not isinstance(path, str) or not path or not isinstance(expected, str) or not SHA256.fullmatch(expected):
        raise ValueError("Input reference path and SHA-256 required")
    parts = Path(path).parts
    if not parts or not (parts[0] == "features" or parts[:2] == ("data", "processed")):
        raise ValueError("Unsupported prospective input path")
    if path in consumed:
        raise ValueError("Duplicate prospective source reference")
    target = safe_path(root, path)
    if not target.is_file() or target.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Missing or oversized prospective input")
    budget[0] += target.stat().st_size
    if budget[0] > MAX_TOTAL_BYTES:
        raise ValueError("Prospective input budget exceeded")
    raw = target.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError("Prospective input hash mismatch")
    value = json.loads(raw)
    canonical_bytes(value)
    if not isinstance(value, dict):
        raise ValueError("Prospective input must be an object")
    consumed[path] = expected
    return value


def _available(ref: dict, cutoff: datetime) -> datetime:
    ready = _time(ref["available_at"])
    if ready >= cutoff:
        raise ValueError("Prospective input was not available before cutoff")
    return ready


def load_prospective_inputs(
    root: Path,
    snapshot_path: str,
    snapshot_sha256: str,
    operational_night: str,
    as_of: datetime,
    *,
    model_feature_names: tuple[str, ...] | None = None,
) -> dict:
    """Validate and join all forecast rows; do not sample only historical positives.

    A signed trusted upstream availability receipt and a separately approved
    model are still mandatory for any future official issuance.
    """
    validate_night(operational_night)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("Issuance as_of must be timezone aware")
    root = Path(root).absolute()
    consumed: dict[str, str] = {}
    budget = [0]
    snapshot = _read_bound(
        root, {"path": snapshot_path, "sha256": snapshot_sha256}, consumed, budget
    )
    if snapshot.get("schema_version") != "2.0":
        raise ValueError("Prospective feature snapshot v2 required")
    if snapshot.get("operational_night") != operational_night:
        raise ValueError("Snapshot operational night mismatch")
    cutoff = _time(snapshot["cutoff_time"])
    if cutoff > as_of:
        raise ValueError("Forecast cutoff is in the future")
    if _night(cutoff) != operational_night:
        raise ValueError("Forecast cutoff does not belong to operational night")
    universe_ref = snapshot["universe"]
    _available(universe_ref, cutoff)
    universe = _read_bound(root, universe_ref, consumed, budget)
    if (universe.get("schema_version") != "1.0" or
        universe.get("source_type") != "EX_ANTE_FORECAST" or
        not isinstance(universe.get("geographic_domain"), dict) or
        not universe["geographic_domain"]):
        raise ValueError("Explicit ex-ante ForecastUniverse required")
    units = universe.get("rows")
    if not isinstance(units, list) or not 0 < len(units) <= MAX_FORECAST_ROWS:
        raise ValueError("Invalid prospective universe row count")
    rows = []
    row_ids = set()
    occupied_units = set()
    for unit in units:
        if not isinstance(unit, dict) or POST_OUTCOME_FIELDS.intersection(unit):
            raise ValueError("Post-outcome data forbidden in ForecastUniverse")
        row_id = unit.get("row_id")
        if not isinstance(row_id, str) or not row_id.strip() or row_id in row_ids:
            raise ValueError("Missing or duplicate universe row ID")
        row_ids.add(row_id)
        if unit.get("operational_night") != operational_night:
            raise ValueError("Universe night mismatch")
        if _time(unit["cutoff_time"]) != cutoff:
            raise ValueError("Universe cutoff mismatch")
        start = _time(unit["window_start_jst"])
        jst = start.astimezone(JST)
        if (start <= as_of or _night(start) != operational_night or
            jst.minute % 10 != 0 or jst.second or jst.microsecond):
            raise ValueError("Universe window is expired, misaligned or off-night")
        x, y = _coordinates(unit)  # Checked UTM52N or exact coordinates.
        space_time = (math.floor(x / 100), math.floor(y / 100), start.isoformat())
        if space_time in occupied_units:
            raise ValueError("Duplicate 100m x 10min forecast unit")
        occupied_units.add(space_time)
        rows.append(dict(unit, features={}, feature_source_refs={}, feature_available_at={}))
    feature_refs = snapshot.get("features")
    if not isinstance(feature_refs, list):
        raise ValueError("Feature references must be a list")
    by_name = {}
    for ref in feature_refs:
        _available(ref, cutoff)
        feature = _read_bound(root, ref, consumed, budget)
        if (feature.get("schema_version") != "1.0" or
            feature.get("use_role") not in ("static_predictor", "forecast_predictor") or
            feature.get("operational_night") != operational_night or
            _time(feature["cutoff_time"]) != cutoff):
            raise ValueError("Invalid ex-ante feature scope")
        name = feature.get("feature_name")
        if not isinstance(name, str) or not name.strip() or name in by_name:
            raise ValueError("Missing or duplicate feature name")
        if _time(feature["available_at"]) > _time(ref["available_at"]):
            raise ValueError("Contradictory feature availability")
        values = feature.get("values")
        if not isinstance(values, dict) or set(values) != row_ids:
            raise ValueError("Feature must cover the entire ex-ante universe")
        for row in rows:
            number = values[row["row_id"]]
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
                raise ValueError("Nonfinite, missing or nonnumeric forecast feature")
            row["features"][name] = float(number)
            row["feature_source_refs"][name] = [ref["path"]]
            row["feature_available_at"][name] = ref["available_at"]
        by_name[name] = ref["path"]
    names = sorted(by_name)
    if model_feature_names is not None and names != sorted(model_feature_names):
        raise ValueError("Feature names do not match the registered model")
    schema_sha = digest(names)
    if snapshot.get("feature_schema_sha256") != schema_sha:
        raise ValueError("Feature schema hash mismatch")
    # Detect source replacement during any preceding joins, before returning rows.
    for path, expected in consumed.items():
        if hashlib.sha256(safe_path(root, path).read_bytes()).hexdigest() != expected:
            raise ValueError("Prospective input changed during validation")
    return {
        "schema_version": "2.0",
        "qualification": "PREPRODUCTION_INPUT_INTEGRITY_ONLY",
        "official_issuance_authorized": False,
        "operational_night": operational_night,
        "cutoff_time": cutoff.isoformat(),
        "universe_ref": universe_ref,
        "feature_schema_sha256": schema_sha,
        "consumed_sha256": consumed,
        "rows": rows,
    }
