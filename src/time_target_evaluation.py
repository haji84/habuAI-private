"""Pure, bounded EVENT-primary full-ledger time-target diagnostics.

Explicit UTM points, source hashes and completeness declarations are supplied
claims, not authenticated provenance. This module has no input/output, target
generator, fitter, issuer, parent dispatch or production authority.
"""
from datetime import datetime, time as day_time, timedelta, timezone
import hashlib
import json
import math
import time

from codex_cycle_contract import POLICY_DIGEST
from evaluation import full_ledger_stage1 as stage1
from event_matching import ordered_event_owners

VERSION = "habu-full-ledger-time-target-diagnostic-v1"
MAX_JSON_BYTES = 16 * 1024 ** 2
MAX_JSON_NODES = 2_000_000
MAX_JSON_DEPTH = 12
MAX_UNITS = 120_000
MAX_TARGETS = 100
MAX_EVENTS = 20_000
MAX_INDIVIDUALS = 100_000
MAX_SOURCES = 20_000
MAX_EDGES = 2_000_000
MAX_BUDGET_SECONDS = 30
JST = timezone(timedelta(hours=9))
UTC = timezone.utc


class TimeTargetCapacityBlocked(ValueError):
    """CAPACITY_BLOCKED: supplied inputs cannot be partially evaluated."""


def _limit(message):
    raise TimeTargetCapacityBlocked("CAPACITY_BLOCKED: " + message)


def _encoded(value, tick):
    total = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        tick()
        raw = chunk.encode("utf-8")
        total += len(raw)
        if total > MAX_JSON_BYTES:
            _limit("canonical JSON bytes")
        yield raw
    tick()


def _digest(value, tick):
    result = hashlib.sha256()
    for raw in _encoded(value, tick):
        result.update(raw)
    return result.hexdigest()


def _known_caps(universe, targets, ledger, tick):
    for value, key, maximum in ((universe, "units", MAX_UNITS),
                                (targets, "targets", MAX_TARGETS),
                                (ledger, "events", MAX_EVENTS),
                                (ledger, "source_refs", MAX_SOURCES)):
        tick()
        if type(value) is dict and type(value.get(key)) is list and len(value[key]) > maximum:
            _limit(key)
    total = 0
    if type(ledger) is dict and type(ledger.get("events")) is list:
        for event in ledger["events"]:
            tick()
            if type(event) is dict and type(event.get("individual_ids")) is list:
                total += len(event["individual_ids"])
                if total > MAX_INDIVIDUALS:
                    _limit("individual identities")


def _owned(values, tick):
    """Bound the combined inputs before encoding/copying or index allocation."""
    pending = [(value, 0, False) for value in values]
    ancestors, nodes = set(), 0
    while pending:
        tick()
        value, depth, leaving = pending.pop()
        kind = type(value)
        if leaving:
            ancestors.remove(id(value))
            continue
        nodes += 1
        if depth > MAX_JSON_DEPTH or nodes > MAX_JSON_NODES:
            _limit("JSON complexity")
        if kind in (dict, list):
            if id(value) in ancestors:
                raise ValueError("Recursive JSON input")
            if len(value) > MAX_JSON_NODES - nodes - len(pending):
                _limit("JSON container width")
            ancestors.add(id(value))
            pending.append((value, depth, True))
            if kind is dict:
                for key in value:
                    tick()
                    if type(key) is not str or len(key) > 128:
                        raise ValueError("Bounded string JSON keys required")
                children = value.values()
            else:
                children = value
            pending.extend((child, depth + 1, False) for child in children)
        elif kind is str:
            if len(value) > 1024:
                _limit("JSON string length")
        elif kind is float:
            if not math.isfinite(value):
                raise ValueError("Nonfinite JSON input")
        elif kind not in (int, bool, type(None)):
            raise ValueError("JSON-only diagnostic inputs required")
    return json.loads(b"".join(_encoded(values, tick)))


def _identity(value):
    value = stage1._text(value, 128)
    if not value.isprintable():
        raise ValueError("Printable canonical identity required")
    return value


def _self_hash(value, key, tick):
    actual = stage1._sha(value[key])
    if actual != _digest({k: v for k, v in value.items() if k != key}, tick):
        raise ValueError("Projection self-hash mismatch")
    return actual


def _nullable_sha(value):
    return None if value is None else stage1._sha(value)


def _instant(value):
    return stage1._time(value).astimezone(UTC)


def _chronology(value):
    night = value["operational_night"]
    try:
        start = datetime.combine(stage1._night(night), day_time(7), JST)
        end = start + timedelta(days=1)
    except OverflowError as exc:
        raise ValueError("Operational night outside supported range") from exc
    cutoff, lower, upper = (_instant(value[key]) for key in ("cutoff_time", "horizon_start", "horizon_end"))
    if not start <= lower < upper <= end or cutoff >= lower:
        raise ValueError("Forecast horizon/cutoff contradict operational night")
    return cutoff, lower, upper


def _protocol(value, expected, tick):
    stage1._fields(value, ("schema_version", "phase", "g0_policy_sha256", "target_semantics",
        "operational_night", "cutoff_time", "horizon_start", "horizon_end", "scope_sha256",
        "universe_sha256", "targets_sha256", "frozen_at", "time_anchor", "radius_m",
        "tolerance_seconds", "matching_policy"))
    for key, fixed in (("schema_version", "habu-time-target-diagnostic-protocol-v1"),
                       ("phase", "DEVELOPMENT"), ("g0_policy_sha256", POLICY_DIGEST),
                       ("target_semantics", "OWNER_CAPTURE_EVENT_POINT_TIME"),
                       ("time_anchor", "WINDOW_MIDPOINT_300_SECONDS"),
                       ("matching_policy", "ORDERED_DFS_MAX_EVENT_CARDINALITY_V1")):
        if value[key] != fixed:
            raise ValueError("Unsupported fixed diagnostic protocol")
    if (type(value["radius_m"]) is not int or value["radius_m"] != 100 or
            type(value["tolerance_seconds"]) is not int or value["tolerance_seconds"] != 600):
        raise ValueError("Fixed 100m/600-second diagnostic required")
    if stage1._sha(expected) != _digest(value, tick):
        raise ValueError("Protocol digest mismatch")
    stage1._sha(value["scope_sha256"])
    _nullable_sha(value["universe_sha256"])
    _nullable_sha(value["targets_sha256"])
    times = _chronology(value)
    if value["frozen_at"] is not None and _instant(value["frozen_at"]) > times[0]:
        raise ValueError("Declared target freeze after cutoff")
    return times


def _key(x, y, instant):
    return (math.floor(x / 100), math.floor(y / 100), instant)


def _universe(value, protocol, times, tick):
    stage1._fields(value, ("schema_version", "operational_night", "cutoff_time", "horizon_start", "horizon_end",
        "scope", "scope_sha256", "forecast_receipt_sha256", "joined_forecast_sha256", "units", "universe_sha256"))
    if value["schema_version"] != "habu-time-target-universe-v1":
        raise ValueError("Explicit point universe projection required")
    sha = _self_hash(value, "universe_sha256", tick)
    if protocol["universe_sha256"] != sha:
        raise ValueError("Protocol does not bind supplied universe")
    if (value["operational_night"] != protocol["operational_night"] or
            _chronology(value) != times or value["scope_sha256"] != protocol["scope_sha256"]):
        raise ValueError("Universe and protocol night/horizon/scope differ")
    scope = value["scope"]
    stage1._fields(scope, ("crs", "bbox_utm"))
    if scope["crs"] != "EPSG:32652" or type(scope["bbox_utm"]) is not list or len(scope["bbox_utm"]) != 4:
        raise ValueError("Explicit UTM52N scope required")
    x0, y0, x1, y1 = map(stage1._number, scope["bbox_utm"])
    if not (100000 <= x0 < x1 <= 900000 and 0 <= y0 < y1 <= 10000000):
        raise ValueError("Invalid UTM52N scope")
    if stage1._sha(value["scope_sha256"]) != _digest(scope, tick):
        raise ValueError("Scope projection digest mismatch")
    stage1._sha(value["forecast_receipt_sha256"])
    stage1._sha(value["joined_forecast_sha256"])
    rows, keys = {}, set()
    for row in stage1._items(value["units"], MAX_UNITS, empty=True):
        tick()
        stage1._fields(row, ("row_id", "window_start_jst", "utm_x_m", "utm_y_m"))
        ident = _identity(row["row_id"])
        instant = _instant(row["window_start_jst"])
        try:
            window_end = instant + timedelta(seconds=600)
        except OverflowError as exc:
            raise ValueError("Window outside supported range") from exc
        if (instant.minute % 10 or instant.second or instant.microsecond or
                not times[0] < instant or not times[1] <= instant < window_end <= times[2]):
            raise ValueError("Explicit aligned post-cutoff whole window required")
        x, y = stage1._number(row["utm_x_m"]), stage1._number(row["utm_y_m"])
        if not x0 <= x < x1 or not y0 <= y < y1:
            raise ValueError("Universe point outside fixed UTM scope")
        key = _key(x, y, instant)
        if ident in rows or key in keys:
            raise ValueError("Duplicate universe row or cell/window identity")
        rows[ident] = (instant, x, y)
        keys.add(key)
    return rows, keys


def _targets(value, protocol, times, rows, tick):
    stage1._fields(value, ("schema_version", "produced", "model_sha256", "prediction_sha256",
                          "universe_sha256", "targets", "targets_sha256"))
    if value["schema_version"] != "habu-time-target-set-v1" or type(value["produced"]) is not bool:
        raise ValueError("Explicit produced time-target projection required")
    if _self_hash(value, "targets_sha256", tick) != protocol["targets_sha256"]:
        raise ValueError("Protocol does not bind supplied targets")
    for key in ("model_sha256", "prediction_sha256", "universe_sha256"):
        _nullable_sha(value[key])
    if (value["universe_sha256"] is not None and protocol["universe_sha256"] is not None and
            value["universe_sha256"] != protocol["universe_sha256"]):
        raise ValueError("Target universe binding mismatch")
    if value["produced"]:
        stage1._sha(value["universe_sha256"])
    result, identities, selected = [], set(), set()
    for row in stage1._items(value["targets"], MAX_TARGETS, empty=True):
        tick()
        stage1._fields(row, ("target_id", "universe_row_id", "predicted_time"))
        ident, ref = _identity(row["target_id"]), _identity(row["universe_row_id"])
        instant = _instant(row["predicted_time"])
        if (instant.minute % 10 != 5 or instant.second or instant.microsecond or
                not times[0] < instant or not times[1] <= instant < times[2]):
            raise ValueError("Post-cutoff midpoint target required")
        if ident in identities or ref in selected:
            raise ValueError("Duplicate target or selected row")
        if rows is not None:
            if ref not in rows or instant != rows[ref][0] + timedelta(seconds=300):
                raise ValueError("Target does not bind its universe row midpoint")
            result.append((ident, instant, rows[ref][1], rows[ref][2]))
        identities.add(ident)
        selected.add(ref)
    if not value["produced"] and identities:
        raise ValueError("Unproduced target set must be empty")
    return sorted(result)


def _ledger(value, universe, protocol, times, tick):
    nights = None if universe is None else {protocol["operational_night"]: universe}
    try:
        by_night, incomplete = stage1._ledger(value, nights, tick)
    except stage1.Stage1CapacityBlocked as exc:
        raise TimeTargetCapacityBlocked(str(exc)) from exc
    complete = False
    for scope in value["complete_scopes"]:
        tick()
        if (scope["operational_night"] != protocol["operational_night"] or
                scope["scope_sha256"] != protocol["scope_sha256"] or
                (_instant(scope["horizon_start"]), _instant(scope["horizon_end"])) != times[1:]):
            raise ValueError("Ledger scope contradicts known protocol")
        complete = scope["declaration"] == "DECLARED_COMPLETE"
    events = []
    for night, group in by_night.items():
        tick()
        if night != protocol["operational_night"]:
            raise ValueError("Foreign ledger night")
        for event in group:
            tick()
            ident = _identity(event["event_id"])
            for individual in event["individual_ids"]:
                tick()
                _identity(individual)
            instant = _instant(event["datetime"])
            if not times[0] < instant or not times[1] <= instant < times[2]:
                raise ValueError("Event contradicts protocol cutoff/horizon")
            events.append((ident, instant, stage1._number(event["utm_x_m"]),
                           stage1._number(event["utm_y_m"]), len(event["individual_ids"])))
    return sorted(events), incomplete or not complete


def evaluate_time_targets(universe, frozen_targets, ledger, *, protocol,
                          expected_protocol_sha256, budget_seconds=30, check=None):
    """Evaluate one supplied frozen target set; return no partial result on error."""
    entered = time.monotonic()
    if (type(budget_seconds) not in (int, float) or not 0 < budget_seconds <= MAX_BUDGET_SECONDS or
            not math.isfinite(budget_seconds) or (check is not None and not callable(check))):
        raise ValueError("Finite bounded time budget and optional callable check required")
    deadline = entered + budget_seconds

    def tick():
        if check is not None:
            check()
        if time.monotonic() >= deadline:
            raise TimeoutError("RUNTIME_BLOCKED: time-target deadline")

    tick()
    _known_caps(universe, frozen_targets, ledger, tick)
    universe, frozen_targets, ledger, protocol = _owned([universe, frozen_targets, ledger, protocol], tick)
    tick()
    times = _protocol(protocol, expected_protocol_sha256, tick)
    rows, keys = (None, None) if universe is None else _universe(universe, protocol, times, tick)
    targets = [] if frozen_targets is None else _targets(frozen_targets, protocol, times, rows, tick)
    events, incomplete = ([], False) if ledger is None else _ledger(ledger, universe, protocol, times, tick)
    blockers = set()
    if universe is None:
        blockers.add("UNIVERSE_REQUIRED")
    if frozen_targets is None:
        blockers.add("TARGET_SET_REQUIRED")
    else:
        if not frozen_targets["produced"]:
            blockers.add("TARGETS_NOT_PRODUCED")
        elif frozen_targets["model_sha256"] is None or frozen_targets["prediction_sha256"] is None:
            blockers.add("PREDICTION_LINEAGE_REQUIRED")
    if ledger is None:
        blockers.add("LEDGER_REQUIRED")
    elif incomplete:
        blockers.add("COMPLETE_LEDGER_REQUIRED")
    if protocol["frozen_at"] is None:
        blockers.add("DECLARED_FREEZE_REQUIRED")
    result = {"schema_version": VERSION, "status": "NEED_MORE_DATA" if blockers else "DIAGNOSTIC_ONLY",
        "operational_night": protocol["operational_night"], "protocol_sha256": expected_protocol_sha256,
        "input_digests": {"universe": None if universe is None else _digest(universe, tick),
                          "targets": None if frozen_targets is None else _digest(frozen_targets, tick),
                          "ledger": None if ledger is None else _digest(ledger, tick)},
        "blockers": sorted(blockers), "metrics": {}, "matching": [], "unmatched_target_ids": [],
        "unmatched_event_ids": [], "outside_universe_event_ids": [], "precision": None, "false_positives": None,
        "source_authentication": "NOT_ATTESTED", "prereveal_authentication": "NOT_ATTESTED",
        "statistical_adequacy": "NOT_ASSESSED", "fit_authorized": False, "scientific_authorized": False,
        "confirmation_authorized": False, "selection_authorized": False,
        "official_100m_10min_kpi_computed": False, "production_authorized": False}
    if not blockers:
        if len(targets) * len(events) > MAX_EDGES:
            _limit("target/event edge candidates")
        eligible, outside = set(), []
        for index, event in enumerate(events):
            tick()
            ident, instant, x, y, count = event
            window = instant.replace(minute=instant.minute // 10 * 10, second=0, microsecond=0)
            if _key(x, y, window) in keys:
                eligible.add(index)
            else:
                outside.append(ident)
        edges, edge_count = [], 0
        for ident, instant, x, y in targets:
            tick()
            neighbors = []
            for index, event in enumerate(events):
                tick()
                if index not in eligible:
                    continue
                event_id, actual_time, ax, ay, count = event
                delta = abs((instant - actual_time).total_seconds())
                distance = math.hypot(x - ax, y - ay)
                if delta <= 600 and distance <= 100:
                    if edge_count >= MAX_EDGES:
                        _limit("stored edges")
                    neighbors.append((distance, delta, event_id, index))
                    edge_count += 1
            neighbors.sort()
            edges.append([row[3] for row in neighbors])
        owners = ordered_event_owners(edges, check=tick)
        matched_targets, covered_individuals = set(), 0
        for event_index, target_index in sorted(owners.items(), key=lambda item: item[1]):
            tick()
            ident, instant, x, y = targets[target_index]
            event_id, actual_time, ax, ay, count = events[event_index]
            result["matching"].append({"target_id": ident, "event_id": event_id,
                "distance_m": math.hypot(x - ax, y - ay),
                "time_delta_seconds": abs((instant - actual_time).total_seconds())})
            matched_targets.add(target_index)
            covered_individuals += count
        total_individuals = 0
        for index, event in enumerate(events):
            tick()
            total_individuals += event[4]
            if index not in owners:
                result["unmatched_event_ids"].append(event[0])
        for index, target in enumerate(targets):
            tick()
            if index not in matched_targets:
                result["unmatched_target_ids"].append(target[0])
        matched = len(owners)
        result["outside_universe_event_ids"] = outside
        result["metrics"] = {"event_numerator": matched, "event_denominator": len(events),
            "event_recall": matched / len(events) if events else None,
            "false_negative_events": len(events) - matched,
            "individuals_in_matched_events": covered_individuals, "individual_denominator": total_individuals,
            "secondary_individual_coverage": covered_individuals / total_individuals if total_individuals else None,
            "total_targets": len(targets), "matched_targets": matched,
            "unknown_targets": len(targets) - matched, "outside_universe_events": len(outside)}
    tick()
    result["receipt_sha256"] = _digest(result, tick)
    tick()
    return result
