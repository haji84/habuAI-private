"""Pure model boundary for the existing PR46 TRAIN_ONLY selector envelope.

This validates internal consistency, not source authenticity, observation
qualification or confirmation authority. Call the repaired source-bound selector
first. No files, sealed outcomes, raw parsers or production issuers are accessed.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePosixPath

from gpx_audit import utm52n

JST = timezone(timedelta(hours=9))
MAX_TRAINING_ROWS = 20_000
MAX_FORECAST_ROWS = 120_000
MAX_FEATURES = 32
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_JSON_NODES = 2_000_000
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")
IDENTITY_FIELDS = ("accepted", "corpus_sha256", "source_sha256", "source_received_at",
                   "heldout_night", "fit_cutoff", "feature_names", "exposed_nights")
SELECTION_FIELDS = set(IDENTITY_FIELDS) | {
    "status", "qualification", "official_issuance_authorized", "rejected",
    "counts", "selection_sha256", "blockers",
}
ROW_FIELDS = {"row_id", "night", "label", "cell_x", "cell_y", "features",
              "window_start_jst", "capture_event_ids"}
OUTCOME_FEATURES = {
    "label", "observed", "label_available_at", "outcome", "actual_capture",
    "capture_event_ids", "capture_count", "owner_capture_count", "gpx_trace",
    "negative_observed", "outcome_available_at", "audit_available_at",
    "all_captures_recorded", "gpx_segment_eligible", "search_role",
}


class ResearchInputCapacity(ValueError):
    """Bounded JSON capacity exceeded, without consuming the remaining input."""


def _json_copy(value, *, check=lambda: None):
    """Reject Python-only, recursive, oversized or nonfinite payloads first."""
    pending, nodes = [(value, 0)], 0
    while pending:
        check()
        item, depth = pending.pop()
        nodes += 1
        if depth > 12 or nodes > MAX_JSON_NODES:
            raise ResearchInputCapacity("Research input exceeds bounded JSON complexity")
        kind = type(item)
        if kind is dict:
            if len(item) > MAX_JSON_NODES - nodes - len(pending):
                raise ResearchInputCapacity("Research input exceeds bounded JSON complexity")
            if any(type(key) is not str or len(key) > 512 for key in item):
                raise ValueError("JSON object keys must be bounded strings")
            pending.extend((child, depth + 1) for child in item.values())
        elif kind is list:
            if len(item) > MAX_JSON_NODES - nodes - len(pending):
                raise ResearchInputCapacity("Research input exceeds bounded JSON complexity")
            pending.extend((child, depth + 1) for child in item)
        elif kind is str:
            if len(item) > 4096:
                raise ValueError("Unbounded research string")
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("Nonfinite JSON value")
        elif kind not in (int, bool, type(None)):
            raise ValueError("Research input must contain JSON values only")
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False)
    raw, chunks = bytearray(), iter(encoder.iterencode(value))
    while True:
        check()
        try:
            chunk = next(chunks)
            encoded = chunk.encode("utf-8")
        except StopIteration:
            break
        except (TypeError, ValueError, RecursionError, OverflowError) as exc:
            raise ValueError("Invalid JSON research input") from exc
        if len(raw) + len(encoded) > MAX_JSON_BYTES:
            raise ResearchInputCapacity("Research input exceeds bounded JSON bytes")
        raw.extend(encoded)
    check()
    result = json.loads(raw)
    check()
    return result


def canonical_digest(value, *, check=lambda: None):
    """SHA-256 of JSON canonical bytes, matching master_contracts.digest."""
    value = _json_copy(value, check=check)
    hashed = hashlib.sha256()
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        check()
        hashed.update(chunk.encode('utf-8'))
    result = hashed.hexdigest()
    check()
    return result


def _text(value, field, maximum=256):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError("Bounded nonempty " + field + " required")
    return value


def _hash(value):
    if type(value) is not str or not SHA256.fullmatch(value):
        raise ValueError("Research SHA-256 required")
    return value


def _night(value):
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Operational night must be YYYY-MM-DD")
    date.fromisoformat(value)
    return value


def _aware(value):
    _text(value, "timezone-aware ISO timestamp", 64)
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    return result


def _window(value, night):
    window = _aware(value).astimezone(JST)
    if (window - timedelta(hours=7)).date().isoformat() != _night(night):
        raise ValueError("Window does not match 07:00 operational night")
    if window.minute % 10 or window.second or window.microsecond:
        raise ValueError("Unaligned 10-minute observation window")
    return window


def _finite(value):
    try:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Finite nonboolean numeric input required")
        result = float(value)
    except OverflowError as exc:
        raise ValueError("Numeric value exceeds finite range") from exc
    return result


def _cell(value):
    if type(value) is not int or not 0 <= value <= 100_000:
        raise ValueError("Integer 100m observation cell required")
    return value


def area_id(cell_x, cell_y):
    """Frozen EPSG:32652 1km bin identifier from integer 100m cells."""
    return f"utm52n_1km_{_cell(cell_x) // 10}_{_cell(cell_y) // 10}"


def _source_path(value):
    _text(value, "source path", 512)
    path = PurePosixPath(value)
    if ("\\" in value or ":" in value or path.is_absolute() or
        any(part in ("", ".", "..") for part in value.split("/")) or
        not path.parts or path.parts[0] not in ("data", "evidence", "features")):
        raise ValueError("Invalid research source path")
    return value


def _names(value, *, allow_empty=False):
    if type(value) not in (list, tuple) or not (0 if allow_empty else 1) <= len(value) <= MAX_FEATURES:
        raise ValueError("Bounded declared feature names required")
    if any(type(n) is not str or not NAME.fullmatch(n) or n.casefold() in OUTCOME_FEATURES for n in value):
        raise ValueError("Invalid feature name or outcome predictor")
    if len(set(value)) != len(value):
        raise ValueError("Duplicate feature name")
    return list(value)


def _sources(hashes, times, cutoff=None, *, check=lambda: None):
    # The selector retains the whole manifest, including rejected/unused sources.
    # Accepted rows omit source_refs and readiness evidence; this model-only
    # boundary cannot reconstruct per-row source eligibility from global times.
    if (type(hashes) is not dict or not 1 <= len(hashes) <= MAX_TRAINING_ROWS or
        type(times) is not dict or set(times) != set(hashes)):
        raise ValueError("Complete bound source hashes and receipt times required")
    for path, sha in hashes.items():
        check()
        _source_path(path)
        _hash(sha)
        _aware(times[path])


def validate_selection(selection):
    """Return a validated copy of the existing selector's serialized envelope.

    A structurally valid zero-row/single-class selection remains NEED_MORE_DATA.
    Malformed inputs, UNKNOWN/bool labels and inconsistent assertions raise
    ValueError. The repaired source-bound selector must enforce per-row source,
    feature, label and audit readiness; this cannot re-attest discarded receipts.
    Global source metadata include unused/rejected sources and may be later.
    """
    value = _json_copy(selection)
    if type(value) is not dict or set(value) != SELECTION_FIELDS:
        raise ValueError("Exact PR46 training selection envelope required")
    if (value["qualification"] != "RETROSPECTIVE_TRAIN_ONLY_NOT_CONFIRMATION" or
        value["official_issuance_authorized"] is not False):
        raise ValueError("Research-only training qualification required")
    heldout = _night(value["heldout_night"])
    cutoff = _aware(value["fit_cutoff"])
    if cutoff >= _aware(heldout + "T07:00:00+09:00"):
        raise ValueError("Fit cutoff must strictly precede held-out night start")
    names = _names(value["feature_names"])
    if names != sorted(names):
        raise ValueError("Selector feature names must be sorted")
    _hash(value["corpus_sha256"])
    _sources(value["source_sha256"], value["source_received_at"], cutoff)
    exposed = value["exposed_nights"]
    if type(exposed) is not list or len(exposed) > MAX_TRAINING_ROWS:
        raise ValueError("Bounded exposed-night list required")
    for night in exposed:
        _night(night)
    if exposed != sorted(set(exposed)):
        raise ValueError("Exposed nights must be unique and sorted")
    rows, rejected = value["accepted"], value["rejected"]
    if (type(rows) is not list or type(rejected) is not list or
        len(rows) + len(rejected) > MAX_TRAINING_ROWS):
        raise ValueError("Bounded training rows required")
    row_ids, units, events, nights, positives = set(), set(), set(), set(), 0
    for row in rows:
        if type(row) is not dict or set(row) != ROW_FIELDS:
            raise ValueError("Exact accepted TRAIN_ONLY row required")
        row_id = _text(row["row_id"], "training row identity")
        if row_id in row_ids:
            raise ValueError("Duplicate training row identity")
        row_ids.add(row_id)
        night = _night(row["night"])
        window = _window(row["window_start_jst"], night)
        if night >= heldout or night in exposed or window >= cutoff:
            raise ValueError("Training must use unexposed earlier-night rows before fit")
        cx, cy = _cell(row["cell_x"]), _cell(row["cell_y"])
        unit = (cx, cy, window.astimezone(timezone.utc))
        if unit in units:
            raise ValueError("Duplicate 100m x 10min observation unit")
        units.add(unit)
        if type(row["label"]) is not int or row["label"] not in (0, 1):
            raise ValueError("UNKNOWN or boolean cannot be a binary observed label")
        ids = row["capture_event_ids"]
        if type(ids) is not list or len(ids) > MAX_TRAINING_ROWS:
            raise ValueError("Bounded capture event identities required")
        for event in ids:
            _text(event, "capture event identity")
            if event in events:
                raise ValueError("Duplicate capture event identity")
            events.add(event)
        if bool(ids) != bool(row["label"]):
            raise ValueError("Capture event identities contradict observed binary label")
        features = row["features"]
        if type(features) is not dict or set(features) != set(names):
            raise ValueError("Complete training feature coverage required")
        for number in features.values():
            _finite(number)
        nights.add(night)
        positives += row["label"]
    if rows != sorted(rows, key=lambda r: (r["night"], r["window_start_jst"], r["row_id"])):
        raise ValueError("Accepted rows must preserve deterministic selector order")
    for row in rejected:
        if type(row) is not dict or set(row) != {"row_id", "night", "reasons"}:
            raise ValueError("Exact rejected-row audit summary required")
        row_id = _text(row["row_id"], "rejected row identity")
        _night(row["night"])
        if row_id in row_ids:
            raise ValueError("Duplicate accepted/rejected row identity")
        row_ids.add(row_id)
        reasons = row["reasons"]
        if type(reasons) is not list or not 1 <= len(reasons) <= 64:
            raise ValueError("Rejected row must declare bounded reasons")
        for reason in reasons:
            _text(reason, "rejection reason")
        if reasons != sorted(set(reasons)):
            raise ValueError("Rejection reasons must be unique and sorted")
    counts = {"accepted_rows": len(rows), "rejected_rows": len(rejected),
              "nights": len(nights), "positives": positives, "negatives": len(rows) - positives}
    if (type(value["counts"]) is not dict or set(value["counts"]) != set(counts) or
        any(type(number) is not int for number in value["counts"].values()) or value["counts"] != counts):
        raise ValueError("Training selection counts do not match actual rows")
    ready = len(nights) >= 3 and positives >= 2 and counts["negatives"] >= 2
    if value["status"] != ("DEVELOPMENT_TRAINING_ELIGIBLE" if ready else "NEED_MORE_DATA"):
        raise ValueError("Training readiness assertion does not match actual rows")
    blockers = value["blockers"]
    if type(blockers) is not list or len(blockers) > 64 or bool(blockers) == ready:
        raise ValueError("Training blockers contradict readiness")
    for blocker in blockers:
        _text(blocker, "training blocker", 4096)
    identity = {key: value[key] for key in IDENTITY_FIELDS}
    if _hash(value["selection_sha256"]) != canonical_digest(identity):
        raise ValueError("Training selection SHA-256 mismatch")
    return value


def _future_coordinates(row):
    cells = "cell_x" in row or "cell_y" in row
    projected = "utm_x_m" in row or "utm_y_m" in row
    geographic = "latitude" in row or "longitude" in row
    if projected:
        if not {"utm_x_m", "utm_y_m"}.issubset(row):
            raise ValueError("Both projected coordinates required")
        x, y = _finite(row["utm_x_m"]), _finite(row["utm_y_m"])
        if not (100_000 <= x <= 900_000 and 0 <= y <= 10_000_000):
            raise ValueError("Invalid EPSG:32652 forecast coordinates")
    elif geographic:
        if not {"latitude", "longitude"}.issubset(row):
            raise ValueError("Both geographic coordinates required")
        lat, lon = _finite(row["latitude"]), _finite(row["longitude"])
        if not (0 <= lat <= 84 and 126 <= lon <= 132):
            raise ValueError("Coordinates outside UTM52N domain")
        x, y = utm52n(lat, lon)
    elif cells:
        if not {"cell_x", "cell_y"}.issubset(row):
            raise ValueError("Both integer forecast cells required")
        cx, cy = _cell(row["cell_x"]), _cell(row["cell_y"])
        if not 1000 <= cx <= 9000:
            raise ValueError("Forecast cell origin outside EPSG:32652 extent")
        return cx, cy
    else:
        raise ValueError("Explicit forecast coordinates required")
    cx, cy = math.floor(x / 100), math.floor(y / 100)
    if cells and (type(row.get("cell_x")) is not int or type(row.get("cell_y")) is not int or
                  row["cell_x"] != cx or row["cell_y"] != cy):
        raise ValueError("Forecast cells contradict coordinates")
    if projected and geographic:
        lat, lon = _finite(row["latitude"]), _finite(row["longitude"])
        if not (0 <= lat <= 84 and 126 <= lon <= 132):
            raise ValueError("Coordinates outside UTM52N domain")
        gx, gy = utm52n(lat, lon)
        if (math.floor(gx / 100), math.floor(gy / 100)) != (cx, cy):
            raise ValueError("Forecast geographic/projected cells disagree")
    return _cell(cx), _cell(cy)


def validate_future_rows(rows, *, cutoff_time, universe_sha256, heldout_night=None,
                         feature_names=None):
    """Validate all supplied label-free joined forecast rows; retain every row.

    universe_sha256 is the canonical digest of the supplied *joined rows*, not
    the upstream Universe file's byte SHA. Upstream availability, authentic
    provenance and actual completeness still need the PR32 input validator.
    Returned rows preserve operational_night and add normalized 100m cell fields.
    """
    value = _json_copy(rows)
    if type(value) is not list or not 1 <= len(value) <= MAX_FORECAST_ROWS:
        raise ValueError("Bounded nonempty full forecast rows required")
    if _hash(universe_sha256) != canonical_digest(value):
        raise ValueError("Full forecast joined-row digest mismatch")
    cutoff = _aware(cutoff_time)
    night = (cutoff.astimezone(JST) - timedelta(hours=7)).date().isoformat()
    if heldout_night is not None and _night(heldout_night) != night:
        raise ValueError("Forecast cutoff does not belong to held-out operational night")
    names = sorted(_names(feature_names, allow_empty=True)) if feature_names is not None else None
    required = {"row_id", "operational_night", "cutoff_time", "window_start_jst",
                "features", "feature_source_refs", "feature_available_at"}
    allowed = required | {"utm_x_m", "utm_y_m", "latitude", "longitude", "cell_x", "cell_y"}
    seen_ids, seen_units = set(), set()
    for row in value:
        if type(row) is not dict or not required.issubset(row) or not set(row).issubset(allowed):
            raise ValueError("Exact label-free prospective joined row required")
        row_id = _text(row["row_id"], "forecast row identity")
        if row_id in seen_ids:
            raise ValueError("Duplicate forecast row identity")
        seen_ids.add(row_id)
        if row["operational_night"] != night or _aware(row["cutoff_time"]) != cutoff:
            raise ValueError("Forecast night or cutoff mismatch")
        window = _window(row["window_start_jst"], night)
        if window <= cutoff:
            raise ValueError("Forecast window must strictly follow cutoff")
        cx, cy = _future_coordinates(row)
        unit = (cx, cy, window.astimezone(timezone.utc))
        if unit in seen_units:
            raise ValueError("Duplicate 100m x 10min forecast unit")
        seen_units.add(unit)
        features, refs, times = row["features"], row["feature_source_refs"], row["feature_available_at"]
        if type(features) is not dict or type(refs) is not dict or type(times) is not dict:
            raise ValueError("Explicit forecast feature values, sources and times required")
        own_names = sorted(_names(list(features), allow_empty=True))
        if names is None:
            names = own_names
        if own_names != names or set(refs) != set(names) or set(times) != set(names):
            raise ValueError("Forecast features must cover the same full declared schema")
        for name in names:
            _finite(features[name])
            if _aware(times[name]) >= cutoff:
                raise ValueError("Forecast feature must be available strictly before cutoff")
            if type(refs[name]) is not list or not 1 <= len(refs[name]) <= 32:
                raise ValueError("Bounded feature source bindings required")
            for path in refs[name]:
                _source_path(path)
            if len(set(refs[name])) != len(refs[name]):
                raise ValueError("Duplicate forecast feature source binding")
        row["cell_x"], row["cell_y"] = cx, cy
    return value
