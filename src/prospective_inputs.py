"""Read-only ex-ante ForecastUniverse/Feature Snapshot binding.

This is a preproduction input-integrity check, never production Champion authority.
It cannot reconstruct source availability or prove today's forecast is issuable.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic
from zoneinfo import ZoneInfo

from master_contracts import canonical_bytes, digest, validate_night
from master_inventory import local_path as guarded_local_path
from model_evaluation import _coordinates

JST = ZoneInfo("Asia/Tokyo")
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 384 * 1024 * 1024
MAX_FORECAST_ROWS = 2_000_000
MAX_JOIN_CELLS = 400_000
MAX_FEATURES = 32
DEFAULT_BUDGET_SECONDS = 30.0
MAX_BUDGET_SECONDS = 300.0
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
POST_OUTCOME_FIELDS = {
    "label", "observed", "label_available_at", "outcome", "actual_capture",
    "capture_event_ids", "capture_count", "gpx_trace", "negative_observed",
    "owner_capture_count", "outcome_available_at",
}
READINESS_FIELDS = {"source_received_at", "derived_at", "materialized_at", "audited_at"}


class InputCapacityError(ValueError):
    """A resource limit blocks validation; this is not invalid scientific evidence."""


class ProspectiveReadContext:
    """One absolute deadline and actual byte ledger across nested input checks."""

    def __init__(self, budget_seconds: float, max_bytes: int):
        self._validate_limits(budget_seconds, max_bytes)
        self.deadline = monotonic() + budget_seconds
        self.max_bytes = max_bytes
        self.bytes_read = 0

    @staticmethod
    def _validate_limits(budget_seconds, max_bytes):
        if (isinstance(budget_seconds, bool) or not isinstance(budget_seconds, (int, float)) or
                not math.isfinite(budget_seconds) or not 0 < budget_seconds <= MAX_BUDGET_SECONDS):
            raise ValueError("Invalid prospective elapsed budget")
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise ValueError("Invalid prospective byte budget")

    def restrict(self, budget_seconds: float, max_bytes: int):
        """Only tighten existing absolute bounds, including already charged bytes."""
        self._validate_limits(budget_seconds, max_bytes)
        self.check()
        self.deadline = min(self.deadline, monotonic() + budget_seconds)
        self.max_bytes = min(self.max_bytes, max_bytes)
        if self.bytes_read > self.max_bytes:
            raise InputCapacityError("CAPACITY_BLOCKED: cumulative actual read bytes")

    def check(self):
        if monotonic() >= self.deadline:
            raise TimeoutError("Prospective input elapsed budget exceeded")
        if self.bytes_read > self.max_bytes:
            raise InputCapacityError("CAPACITY_BLOCKED: cumulative actual read bytes")

    def account(self, count: int):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Actual byte count must be a nonnegative integer")
        self.bytes_read += count
        self.check()
        if self.bytes_read > self.max_bytes:
            raise InputCapacityError("CAPACITY_BLOCKED: cumulative actual read bytes")

    @property
    def remaining_bytes(self):
        self.check()
        return max(0, self.max_bytes - self.bytes_read)

    @property
    def remaining_seconds(self):
        self.check()
        return max(0.0, self.deadline - monotonic())


class _LocalByteBudget(list):
    def __init__(self, context: ProspectiveReadContext | None, source_limit=MAX_SOURCE_BYTES):
        super().__init__([0])
        self.context = context
        self.source_limit = min(MAX_SOURCE_BYTES, source_limit)


def _time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timestamp requires a timezone")
    return result


def _night(value: datetime) -> str:
    return (value.astimezone(JST) - timedelta(hours=7)).date().isoformat()


def _reject_outcome_fields(value, check) -> None:
    """Reject known outcome schema keys, including nested metadata."""
    pending = [value]
    while pending:
        check()
        item = pending.pop()
        if isinstance(item, dict):
            if any(key.casefold() in POST_OUTCOME_FIELDS for key in item):
                raise ValueError("Post-outcome data forbidden in prospective inputs")
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


def _bounded_bytes(target: Path, budget: list[int], check) -> bytes:
    check()
    # stat is only an early rejection: the file may grow before or during read.
    source_limit = getattr(budget, "source_limit", MAX_SOURCE_BYTES)
    if not target.is_file():
        raise ValueError("Missing prospective input")
    if target.stat().st_size > source_limit:
        raise InputCapacityError("Missing or oversized prospective input")
    limit = min(source_limit, MAX_TOTAL_BYTES - budget[0])
    context = getattr(budget, "context", None)
    if context is not None:
        context.check()
        limit = min(limit, context.max_bytes - context.bytes_read)
    with target.open("rb") as source:
        raw = source.read(limit + 1)
    if context is not None:
        context.account(len(raw))
    check()
    if len(raw) > source_limit:
        raise InputCapacityError("Prospective input is oversized")
    if len(raw) > limit:
        raise InputCapacityError("Prospective input budget exceeded")
    budget[0] += len(raw)
    return raw


def _local_path(root: Path, relative: str, check) -> Path:
    """Reject all absolute ancestors and descendants before every read/rescan."""
    check()
    target = guarded_local_path(root, relative)
    check()
    return target


def _unique_json_object(pairs, check):
    result = {}
    for key, value in pairs:
        check()
        if key in result:
            raise ValueError("Duplicate JSON key in prospective input")
        result[key] = value
    check()
    return result


def _read_bound(root: Path, ref: dict, consumed: dict, budget: list[int], check):
    check()
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
    target = _local_path(root, path, check)
    raw = _bounded_bytes(target, budget, check)
    actual = hashlib.sha256(raw).hexdigest()
    check()
    if actual != expected:
        raise ValueError("Prospective input hash mismatch")
    value = json.loads(raw, object_pairs_hook=lambda pairs: _unique_json_object(pairs, check))
    check()
    canonical_bytes(value)
    check()
    if not isinstance(value, dict):
        raise ValueError("Prospective input must be an object")
    consumed[path] = expected
    return value


def _declared_readiness(value: dict, cutoff: datetime, available: datetime | None = None) -> None:
    """Reject contradictory declared readiness; missing closure stays unvalidated."""
    if "available_at" in value:
        internal = _time(value["available_at"])
        if internal >= cutoff or (available is not None and internal > available):
            raise ValueError("Contradictory declared readiness/availability")
        available = internal
    nested = value.get("readiness", {})
    if not isinstance(nested, dict) or not set(nested) <= READINESS_FIELDS:
        raise ValueError("Invalid declared readiness fields")
    declared = []
    for key in READINESS_FIELDS:
        times = [_time(record[key]) for record in (value, nested) if key in record]
        if len(set(times)) > 1:
            raise ValueError("Contradictory declared readiness timestamps")
        declared.extend(times)
    if "usable_at" in value:
        usable = _time(value["usable_at"])
        if declared and usable < max(declared):
            raise ValueError("Declared usable_at precedes required readiness")
        declared.append(usable)
    if declared:
        ready = max(declared)
        if ready >= cutoff:
            raise ValueError("Declared readiness is not strictly before forecast cutoff")
        if available is not None and ready > available:
            raise ValueError("Declared readiness exceeds advertised availability")


def _declared_role(value: dict, allowed: set[str]) -> None:
    for key in ("source_role", "role"):
        if key in value and (not isinstance(value[key], str) or value[key].casefold() not in allowed):
            raise ValueError("Declared source role is incompatible with prospective input")


def _declared_validity(value: dict, first: datetime, last: datetime) -> None:
    if "valid_from" not in value and "valid_until" not in value:
        return
    if "valid_from" not in value or "valid_until" not in value:
        raise ValueError("Declared valid-time interval needs both endpoints")
    start, end = _time(value["valid_from"]), _time(value["valid_until"])
    if start >= end or start > first or end < last:
        raise ValueError("Declared valid-time does not cover every forecast window")


def _available(ref: dict, cutoff: datetime) -> datetime:
    ready = _time(ref["available_at"])
    if ready >= cutoff:
        raise ValueError("Prospective input was not available before cutoff")
    _declared_readiness(ref, cutoff, ready)
    return ready


def _join_payload_sequence(snapshot, operational_night, as_of, model_feature_names, check):
    """Pure validation state machine; yields byte references, never reads files."""
    feature_refs = snapshot.get("features")
    if not isinstance(feature_refs, list):
        raise ValueError("Feature references must be a list")
    if len(feature_refs) > MAX_FEATURES:
        raise ValueError("Prospective feature count limit exceeded")
    _reject_outcome_fields(snapshot, check)
    if snapshot.get("schema_version") != "2.0":
        raise ValueError("Prospective feature snapshot v2 required")
    if snapshot.get("operational_night") != operational_night:
        raise ValueError("Snapshot operational night mismatch")
    cutoff = _time(snapshot["cutoff_time"])
    if cutoff > as_of:
        raise ValueError("Forecast cutoff is in the future")
    if _night(cutoff) != operational_night:
        raise ValueError("Forecast cutoff does not belong to operational night")
    _declared_readiness(snapshot, cutoff)
    universe_ref = snapshot["universe"]
    universe_available = _available(universe_ref, cutoff)
    _declared_role(universe_ref, {"universe"})
    universe = (yield universe_ref)
    if (universe.get("schema_version") != "1.0" or
        universe.get("source_type") != "EX_ANTE_FORECAST" or
        not isinstance(universe.get("geographic_domain"), dict) or
        not universe["geographic_domain"]):
        raise ValueError("Explicit ex-ante ForecastUniverse required")
    _declared_role(universe, {"universe"})
    _declared_readiness(universe, cutoff, universe_available)
    units = universe.get("rows")
    if not isinstance(units, list) or not 0 < len(units) <= MAX_FORECAST_ROWS:
        raise ValueError("Invalid prospective universe row count")
    if len(units) * len(feature_refs) > MAX_JOIN_CELLS:
        raise ValueError("Prospective join cell budget exceeded")
    _reject_outcome_fields(universe, check)
    rows = []
    row_ids = set()
    occupied_units = set()
    first_window = last_window_end = None
    for unit in units:
        check()
        if not isinstance(unit, dict):
            raise ValueError("ForecastUniverse row must be an object")
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
        space_time = (math.floor(x / 100), math.floor(y / 100), start.astimezone(timezone.utc))
        if space_time in occupied_units:
            raise ValueError("Duplicate 100m x 10min forecast unit")
        occupied_units.add(space_time)
        first_window = start if first_window is None else min(first_window, start)
        end = start + timedelta(minutes=10)
        last_window_end = end if last_window_end is None else max(last_window_end, end)
        rows.append(dict(unit, features={}, feature_source_refs={}, feature_available_at={}))
    _declared_validity(universe_ref, first_window, last_window_end)
    _declared_validity(universe, first_window, last_window_end)
    by_name = {}
    for ref in feature_refs:
        check()
        feature_available = _available(ref, cutoff)
        _declared_role(ref, {"feature"})
        _declared_validity(ref, first_window, last_window_end)
        feature = (yield ref)
        # values has row identifiers as keys, not schema fields; its values are
        # separately required to be finite numbers below.
        _reject_outcome_fields({key: value for key, value in feature.items() if key != "values"}, check)
        if (feature.get("schema_version") != "1.0" or
            feature.get("use_role") not in ("static_predictor", "forecast_predictor") or
            feature.get("operational_night") != operational_night or
            _time(feature["cutoff_time"]) != cutoff):
            raise ValueError("Invalid ex-ante feature scope")
        if _time(feature["available_at"]) > feature_available:
            raise ValueError("Contradictory feature availability")
        _declared_role(feature, {"feature", "static_predictor", "forecast_predictor"})
        _declared_readiness(feature, cutoff, feature_available)
        _declared_validity(feature, first_window, last_window_end)
        name = feature.get("feature_name")
        if not isinstance(name, str) or not name.strip() or name in by_name:
            raise ValueError("Missing or duplicate feature name")
        if name.strip().casefold() in POST_OUTCOME_FIELDS:
            raise ValueError("Post-outcome field cannot be a prospective predictor")
        values = feature.get("values")
        if not isinstance(values, dict) or set(values) != row_ids:
            raise ValueError("Feature must cover the entire ex-ante universe")
        for row in rows:
            check()
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
    return {"cutoff_time": cutoff.isoformat(), "universe_ref": universe_ref,
            "feature_schema_sha256": schema_sha, "rows": rows}


def join_prospective_payloads(snapshot, universe, feature_payloads, operational_night, as_of, *,
                              model_feature_names=None, check=lambda: None):
    """Join owned parsed payloads without file I/O or byte/authenticity claims.

    Callers must first verify bounded bytes/hash/JSON decoding and retain their
    final rescan. This pure result carries no qualification or source receipt.
    """
    if not callable(check):
        raise ValueError("Prospective join check must be callable")
    check()
    validate_night(operational_night)
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("Issuance as_of must be timezone aware")
    if not all(isinstance(value, dict) for value in (snapshot, universe, feature_payloads)):
        raise ValueError("Owned prospective JSON objects required")
    sequence = _join_payload_sequence(snapshot, operational_night, as_of, model_feature_names, check)
    try:
        requested = next(sequence)
        paths = []
        for ref in snapshot["features"]:
            check()
            if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
                raise ValueError("Input reference path required")
            paths.append(ref["path"])
        universe_path = requested.get("path")
        if (not isinstance(universe_path, str) or universe_path in paths or
                len(set(paths)) != len(paths)):
            raise ValueError("Duplicate prospective source reference")
        if len(feature_payloads) != len(paths) or set(feature_payloads) != set(paths):
            raise ValueError("Owned feature payloads must match all snapshot references")
        payloads = dict(feature_payloads)
        payloads[universe_path] = universe
        while True:
            check()
            payload = payloads[requested["path"]]
            if not isinstance(payload, dict):
                raise ValueError("Prospective input must be an object")
            requested = sequence.send(payload)
    except StopIteration as finished:
        result = finished.value
    check()
    return result


def load_prospective_inputs(
    root: Path,
    snapshot_path: str,
    snapshot_sha256: str,
    operational_night: str,
    as_of: datetime,
    *,
    model_feature_names: tuple[str, ...] | None = None,
    budget_seconds: float = DEFAULT_BUDGET_SECONDS,
    _read_context: ProspectiveReadContext | None = None,
) -> dict:
    """Validate and join all forecast rows; do not sample only historical positives.

    A signed trusted upstream availability receipt and a separately approved
    model are still mandatory for any future official issuance.
    """
    if (isinstance(budget_seconds, bool) or not isinstance(budget_seconds, (int, float)) or
        not math.isfinite(budget_seconds) or not 0 < budget_seconds <= MAX_BUDGET_SECONDS):
        raise ValueError("Invalid prospective elapsed budget")
    deadline = monotonic() + budget_seconds
    if _read_context is not None and not isinstance(_read_context, ProspectiveReadContext):
        raise ValueError("Invalid shared prospective read context")

    def check():
        if _read_context is not None:
            _read_context.check()
        if monotonic() >= deadline:
            raise TimeoutError("Prospective input elapsed budget exceeded")

    check()
    validate_night(operational_night)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("Issuance as_of must be timezone aware")
    root = Path(root).absolute()
    consumed: dict[str, str] = {}
    budget = _LocalByteBudget(_read_context)
    snapshot = _read_bound(
        root, {"path": snapshot_path, "sha256": snapshot_sha256}, consumed, budget, check
    )
    sequence = _join_payload_sequence(snapshot, operational_night, as_of, model_feature_names, check)
    try:
        requested = next(sequence)
        while True:
            payload = _read_bound(root, requested, consumed, budget, check)
            requested = sequence.send(payload)
    except StopIteration as finished:
        joined = finished.value
    # Sequential checks can detect changes, but cannot provide an atomic
    # filesystem snapshot. Returned rows derive from the hash-checked read bytes.
    recheck_budget = _LocalByteBudget(_read_context)
    for path, expected in consumed.items():
        check()
        if hashlib.sha256(_bounded_bytes(_local_path(root, path, check), recheck_budget, check)).hexdigest() != expected:
            raise ValueError("Prospective input changed during validation")
    check()
    return {
        "schema_version": "2.0",
        "qualification": "PREPRODUCTION_INPUT_INTEGRITY_ONLY",
        "official_issuance_authorized": False,
        "operational_night": operational_night,
        "cutoff_time": joined["cutoff_time"],
        "universe_ref": joined["universe_ref"],
        "feature_schema_sha256": joined["feature_schema_sha256"],
        "consumed_sha256": consumed,
        "rows": joined["rows"],
    }
