"""Private, additive capture/GPS evidence; never edits a ledger or trains a model.

This is a declared row interface, NOT a parser for the private legacy candidate
JSON (whose format has not been inspected). The caller must verify the original
bytes and bind their digest before supplying rows. Digest syntax here is not
proof of authenticity. No input is independently certified by this function.

Required event fields: event_id, individual_ids, source_sha256, recorded_at
(aware ISO), time_semantics, uncertainty_seconds, latitude, longitude,
owner_role, species, event_type, count. Coordinates are a pair or both null;
count may be null and individual_ids may be empty. Optional source_reference
and individual_ids_complete preserve declared source identity/completeness.
No individual ID is created for an unknown animal. Distinct events containing
the same known individual require reconciliation outside this helper.

Candidate residuals refer to recorded_at, NOT a reconstructed emergence time.
Measured points with local source-clock conflicts retain their recorded times
and candidates, but propagate the conflict rather than claiming a precise match.
The 600-second/100-metre conjunction is a descriptive compatibility screen,
not prediction success or formal Positive/Negative qualification. Even a
single compatible measured sample does not establish a continuous route.
All returned event/point identities and residuals belong in PRIVATE storage.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
import re

from src.gpx_audit import distance_m


MAX_EVENTS = 10_000
MAX_POINTS = 500_000
MAX_COMPARISONS = 2_000_000
MAX_CANDIDATES = 200_000
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_EVENT_KEYS = {"event_id", "individual_ids", "source_sha256", "recorded_at",
               "time_semantics", "uncertainty_seconds", "latitude", "longitude",
               "owner_role", "species", "event_type", "count"}
_OPTIONAL_KEYS = {"source_reference", "individual_ids_complete"}


def _fail(code="CAPTURE_SCHEMA_INVALID"):
    # Never echo source data or identifiers into a CLI error.
    raise ValueError(code)


def _text(value, maximum=256):
    if not isinstance(value, str) or not value or len(value) > maximum or any(
            ord(c) < 32 for c in value):
        _fail()
    return value


def _digest(value):
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        _fail("CAPTURE_SOURCE_INVALID")
    return value


def _time(value):
    _text(value, 64)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            _fail()
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        _fail()


def _number(value, low, high):
    if type(value) not in (float, int) or not low <= value <= high or not math.isfinite(value):
        _fail()
    return value


def _coords(row, *, nullable=False):
    lat, lon = row.get("latitude"), row.get("longitude")
    if nullable and lat is None and lon is None:
        return False
    # Reused distance_m projects to UTM52N; never silently apply it globally.
    _number(lat, 0, 84)
    _number(lon, 126, 132)
    return True


def _event(row, source_sha256):
    if not isinstance(row, dict) or not _EVENT_KEYS <= row.keys() or row.keys() - _EVENT_KEYS - _OPTIONAL_KEYS:
        _fail()
    _text(row["event_id"])
    if _digest(row["source_sha256"]) != source_sha256:
        _fail("CAPTURE_SOURCE_INVALID")
    ids = row["individual_ids"]
    if not isinstance(ids, list) or len(ids) > 1000:
        _fail()
    for identity in ids:
        _text(identity)
    if len(set(ids)) != len(ids):
        _fail("CAPTURE_IDENTITY_CONFLICT")
    count = row["count"]
    if count is not None and (type(count) is not int or not 1 <= count <= 1000 or len(ids) > count):
        _fail()
    if "individual_ids_complete" in row:
        if type(row["individual_ids_complete"]) is not bool:
            _fail()
        if row["individual_ids_complete"] and (count is None or count != len(ids)):
            _fail()
    if "source_reference" in row:
        _text(row["source_reference"], 2048)
    if row["time_semantics"] not in ("OBSERVED_AT", "CAPTURE_COMPLETED_AT", "RECORDED_AT", "UNKNOWN"):
        _fail()
    _number(row["uncertainty_seconds"], 0, 31_536_000)
    if row["owner_role"] not in ("OWNER", "OTHER", "UNKNOWN"):
        _fail()
    if row["species"] not in ("HABU", "HIMEHABU", "OTHER", "UNKNOWN"):
        _fail()
    if row["event_type"] not in ("CAPTURE", "CAPTURED_THEN_ESCAPED", "SIGHTING", "ROADKILL", "ESCAPED", "UNKNOWN"):
        _fail()
    return _time(row["recorded_at"]), _coords(row, nullable=True)


def _measured_points(points):
    prepared, identities = [], set()
    for row in points:
        if not isinstance(row, dict) or type(row.get("exclude_point")) is not bool:
            _fail("CAPTURE_ROUTE_INVALID")
        if row.get("origin") != "GPS_MEASURED":
            _fail("CAPTURE_ROUTE_INVALID")
        if "temporal_context_uncertain" in row and type(row["temporal_context_uncertain"]) is not bool:
            _fail("CAPTURE_ROUTE_INVALID")
        digest = _digest(row.get("source_sha256"))
        seq = row.get("sequence")
        if type(seq) is not int or seq < 0 or seq > MAX_POINTS:
            _fail("CAPTURE_ROUTE_INVALID")
        identity = f"{digest}:{seq}"
        if row.get("point_id") != identity or identity in identities:
            _fail("CAPTURE_ROUTE_INVALID")
        identities.add(identity)
        if row["exclude_point"]:
            continue
        _coords(row)
        for field in ("accuracy_m", "hdop"):
            if row.get(field) is not None:
                _number(row[field], 0, 1_000_000)
        prepared.append((_time(row.get("time_utc")), identity, row))
    prepared.sort(key=lambda p: (p[0], p[1]))
    return prepared


def _window(instant):
    try:
        lower = instant - timedelta(seconds=600)
    except OverflowError:
        lower = datetime.min.replace(tzinfo=timezone.utc)
    try:
        upper = instant + timedelta(seconds=600)
    except OverflowError:
        upper = datetime.max.replace(tzinfo=timezone.utc)
    return lower, upper


def match_captures(events: list[dict], route_points: list[dict], *, source_sha256: str) -> dict:
    """Return PRIVATE sidecars for explicit source-bound candidates; no I/O.

    Identity conflicts fail closed rather than adding a duplicate to a count.
    The operation/output budgets apply across all events, including repeated
    visits. Input arrays, nested IDs and route rows are never modified.
    """
    _digest(source_sha256)
    if not isinstance(events, list) or not isinstance(route_points, list):
        _fail()
    if len(events) > MAX_EVENTS or len(route_points) > MAX_POINTS:
        _fail("CAPTURE_BUDGET_EXCEEDED")
    prepared_events, event_ids, individual_ids = [], set(), set()
    for event in events:
        instant, has_coords = _event(event, source_sha256)
        if event["event_id"] in event_ids or individual_ids.intersection(event["individual_ids"]):
            _fail("CAPTURE_IDENTITY_CONFLICT")
        event_ids.add(event["event_id"])
        individual_ids.update(event["individual_ids"])
        prepared_events.append((event, instant, has_coords))
    fixes = _measured_points(route_points)
    times = [fix[0] for fix in fixes]
    rows, comparisons, total_candidates = [], 0, 0
    summary = dict(events=len(events), capture_positive_events=0,
                   capture_positive_individuals=0, unknown_count_positive_events=0,
                   known_individual_count=len(individual_ids), owner_capture_individuals=0,
                   canonical_updates=0, model_updates=0, formal_positive=0, formal_negative=0,
                   matched_events=0, ambiguous_events=0, time_only_events=0,
                   candidate_samples=0, route_points=len(route_points), qualifying_route_points=len(fixes))
    for event, instant, has_coords in prepared_events:
        positive = event["species"] == "HABU" and event["event_type"] in ("CAPTURE", "CAPTURED_THEN_ESCAPED")
        if positive:
            summary["capture_positive_events"] += 1
            if event["count"] is None:
                summary["unknown_count_positive_events"] += 1
            else:
                summary["capture_positive_individuals"] += event["count"]
                if event["owner_role"] == "OWNER":
                    summary["owner_capture_individuals"] += event["count"]
        candidates = []
        if has_coords:
            lower, upper = _window(instant)
            left, right = bisect_left(times, lower), bisect_right(times, upper)
            comparisons += right - left
            if comparisons > MAX_COMPARISONS:
                _fail("CAPTURE_BUDGET_EXCEEDED")
            for fix_time, identity, fix in fixes[left:right]:
                residual = distance_m(event, fix)
                if residual <= 100:
                    total_candidates += 1
                    if total_candidates > MAX_CANDIDATES:
                        _fail("CAPTURE_BUDGET_EXCEEDED")
                    candidates.append(dict(point_id=identity, source_sha256=fix["source_sha256"],
                                           sequence=fix["sequence"], delta_seconds=(fix_time - instant).total_seconds(),
                                           distance_m=residual, origin="GPS_MEASURED",
                                           accuracy_m=fix.get("accuracy_m"), hdop=fix.get("hdop"),
                                           temporal_context_uncertain=fix.get("temporal_context_uncertain", False),
                                           distance_semantics="RECORDED_COORDINATE_CENTERS"))
        if not has_coords:
            status = "TIME_ONLY_POSITIVE_EVIDENCE" if positive else "TIME_ONLY_REACTION_EVIDENCE"
            summary["time_only_events"] += 1
        elif any(candidate["temporal_context_uncertain"] for candidate in candidates):
            status = "SOURCE_CLOCK_AMBIGUOUS"
            summary["ambiguous_events"] += 1
        elif event["time_semantics"] != "OBSERVED_AT" or event["uncertainty_seconds"] > 0:
            status = "TIMING_AMBIGUOUS"
            summary["ambiguous_events"] += 1
        elif len(candidates) > 1:
            status = "MULTIPLE_SAMPLE_CANDIDATES"
            summary["ambiguous_events"] += 1
        elif candidates:
            status = "SINGLE_SAMPLE_CANDIDATE"
            summary["matched_events"] += 1
        else:
            status = "NO_SAMPLE_CANDIDATE"
        rows.append(dict(event=deepcopy(event), recorded_count=event["count"],
                         known_individual_count=len(event["individual_ids"]),
                         capture_positive_evidence=positive, match_status=status, candidates=candidates,
                         usage="POST_SEARCH_RESEARCH_ONLY", formal_positive=False,
                         formal_negative=False, predictive_success=False))
    summary["candidate_samples"] = total_candidates
    summary["recorded_positive_quantity_sum_complete"] = summary["unknown_count_positive_events"] == 0
    return dict(schema_version="habu-capture-route-sidecars-v1", source_sha256=source_sha256,
                source_bytes_verified_by_helper=False, sidecars=rows, summary=summary,
                policy=dict(time_tolerance_seconds=600, distance_tolerance_m=100,
                            distance_crs="EPSG:32652", time_anchor="RECORDED_AT_ONLY",
                            count_semantics="SOURCE_RECORDED_QUANTITY_NOT_CANONICAL_UNIQUE_TOTAL",
                            independent_source_or_label_certification=False))
