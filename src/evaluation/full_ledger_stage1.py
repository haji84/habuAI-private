"""Pure Stage1 diagnostics on explicit individual ledgers, never confirmation.

Supplied source hashes and completeness declarations are not authenticated here.
No filesystem, model fitter, held-out loader, issuer or registry is accessed.
"""
from __future__ import annotations

from datetime import date, datetime, time as day_time, timedelta, timezone
import hashlib
import json
import math
from pathlib import PurePosixPath
import random
import re
import time

from codex_cycle_contract import POLICY_DIGEST

VERSION = "habu-full-ledger-stage1-diagnostic-v1"
JST = timezone(timedelta(hours=9))
MAX_NIGHTS = 128
MAX_AREA_NIGHT_CELLS = 120_000
MAX_EVENTS = 20_000
MAX_INDIVIDUALS = 100_000
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_JSON_NODES = 2_000_000
MAX_SOURCES = 20_000
MAX_BUDGET_SECONDS = 300
TOP_K = 10
MINIMUM_NIGHTS = 5
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 0
SHA = re.compile(r"[a-f0-9]{64}\Z")
AREA = re.compile(r"utm52n_1km_(0|[1-9][0-9]*)_(0|[1-9][0-9]*)\Z")
CANDIDATE_IDS = {"uniform", "HB-A0", "HB-B1"}


class Stage1CapacityBlocked(ValueError):
    """CAPACITY_BLOCKED: no truncation or partial metrics."""


class Stage1BudgetBlocked(ValueError):
    """RUNTIME_BLOCKED: no partial result is returned after the deadline."""


def _encoded(value, check):
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False)
    total = 0
    for chunk in encoder.iterencode(value):
        check()
        raw = chunk.encode("utf-8")
        total += len(raw)
        if total > MAX_JSON_BYTES:
            raise Stage1CapacityBlocked("CAPACITY_BLOCKED: JSON byte limit")
        yield raw
    check()


def _copy_json(value, check):
    pending, nodes = [(value, 0)], 0
    while pending:
        check()
        item, depth = pending.pop()
        nodes += 1
        if depth > 12 or nodes > MAX_JSON_NODES:
            raise Stage1CapacityBlocked("CAPACITY_BLOCKED: JSON complexity")
        kind = type(item)
        if kind in (dict, list):
            if len(item) > MAX_JSON_NODES - nodes - len(pending):
                raise Stage1CapacityBlocked("CAPACITY_BLOCKED: JSON nodes")
            if kind is dict and any(type(k) is not str or len(k) > 512 for k in item):
                raise ValueError("Bounded string JSON keys required")
            pending.extend((v, depth + 1) for v in (item.values() if kind is dict else item))
        elif kind is str:
            if len(item) > 4096:
                raise Stage1CapacityBlocked("CAPACITY_BLOCKED: JSON string length")
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("Nonfinite JSON input")
        elif kind not in (int, bool, type(None)):
            raise ValueError("JSON-only diagnostic inputs required")
    return json.loads(b"".join(_encoded(value, check)))


def _digest(value, check):
    result = hashlib.sha256()
    for chunk in _encoded(value, check):
        result.update(chunk)
    return result.hexdigest()


def _fields(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError("Exact diagnostic contract fields required")


def _items(value, limit, *, empty=False):
    if type(value) is not list or (not empty and not value):
        raise ValueError("Explicit diagnostic list required")
    if len(value) > limit:
        raise Stage1CapacityBlocked("CAPACITY_BLOCKED: diagnostic list limit")
    return value


def _text(value, maximum=128):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError("Bounded nonempty diagnostic identity required")
    return value


def _sha(value):
    if type(value) is not str or not SHA.fullmatch(value):
        raise ValueError("Explicit SHA-256 required")
    return value


def _number(value):
    if type(value) not in (int, float):
        raise ValueError("Finite nonboolean number required")
    try:
        if not math.isfinite(value):
            raise ValueError("Finite nonboolean number required")
        return float(value)
    except OverflowError as exc:
        raise ValueError("Number outside finite range") from exc


def _time(value):
    _text(value, 64)
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("Timezone-aware diagnostic time required")
    try:
        result.astimezone(JST)
        result.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError("Diagnostic time outside supported range") from exc
    return result


def _night(value):
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Operational night required")
    return date.fromisoformat(value)


def _area_id(x, y):
    return f"utm52n_1km_{math.floor(x / 1000)}_{math.floor(y / 1000)}"


def _path(value):
    _text(value, 512)
    parsed = PurePosixPath(value)
    if ("\\" in value or ":" in value or any(ord(c) < 32 or ord(c) == 127 for c in value) or
            parsed.is_absolute() or str(parsed) != value or
            any(p in ("", ".", "..") for p in value.split("/")) or
            parsed.parts[0] not in ("data", "evidence", "features", "policies", "reports")):
        raise ValueError("Canonical relative source reference required")
    return value


def _ref(value):
    _fields(value, ("path", "sha256", "bytes"))
    path = _path(value["path"])
    _sha(value["sha256"])
    if type(value["bytes"]) is not int or not 0 <= value["bytes"] <= 2 * 1024 ** 3:
        raise ValueError("Explicit bounded source byte size required")
    return path


def _universe(value, check):
    _fields(value, ("schema_version", "nights"))
    if value["schema_version"] != "habu-stage1-universe-v1":
        raise ValueError("Unsupported Stage1 universe projection")
    nights, total = {}, 0
    for row in _items(value["nights"], MAX_NIGHTS, empty=True):
        check()
        _fields(row, ("operational_night", "scope", "scope_sha256", "cutoff_time",
                      "horizon_start", "horizon_end", "area_ids"))
        night = row["operational_night"]
        start = datetime.combine(_night(night), day_time(7), JST)
        try:
            end = start + timedelta(days=1)
        except OverflowError as exc:
            raise ValueError("Operational night outside supported range") from exc
        if night in nights:
            raise ValueError("Duplicate operational night")
        lower, upper, cutoff = _time(row["horizon_start"]), _time(row["horizon_end"]), _time(row["cutoff_time"])
        if not (start <= lower < upper <= end and cutoff < lower):
            raise ValueError("Forecast horizon/cutoff contradict operational night")
        _fields(row["scope"], ("crs", "bbox_utm"))
        bbox = row["scope"]["bbox_utm"]
        if row["scope"]["crs"] != "EPSG:32652" or type(bbox) is not list or len(bbox) != 4:
            raise ValueError("Explicit UTM52N scope bounds required")
        x0, y0, x1, y1 = map(_number, bbox)
        if not (100000 <= x0 < x1 <= 900000 and 0 <= y0 < y1 <= 10000000):
            raise ValueError("Invalid UTM52N scope bounds")
        if _sha(row["scope_sha256"]) != _digest(row["scope"], check):
            raise ValueError("Declared scope projection digest mismatch")
        areas = _items(row["area_ids"], MAX_AREA_NIGHT_CELLS)
        total += len(areas)
        if total > MAX_AREA_NIGHT_CELLS:
            raise Stage1CapacityBlocked("CAPACITY_BLOCKED: area-night limit")
        for ident in areas:
            check()
            match = AREA.fullmatch(ident) if type(ident) is str else None
            if not match:
                raise ValueError("Canonical 1km area identity required")
            ax, ay = map(int, match.groups())
            if not (ax * 1000 < x1 and (ax + 1) * 1000 > x0 and
                    ay * 1000 < y1 and (ay + 1) * 1000 > y0):
                raise ValueError("Forecast area is outside declared scope")
        if areas != sorted(set(areas)):
            raise ValueError("Forecast areas must be sorted and unique")
        nights[night] = row
    if list(nights) != sorted(nights):
        raise ValueError("Operational nights must be sorted")
    return nights


def _scores(value, universe, nights, check):
    _fields(value, ("schema_version", "universe_sha256", "candidates"))
    if value["schema_version"] != "habu-stage1-scores-v1":
        raise ValueError("Unsupported Stage1 score projection")
    if _sha(value["universe_sha256"]) != _digest(universe, check):
        raise ValueError("Scores do not bind the complete forecast universe")
    candidates = {}
    for candidate in _items(value["candidates"], 3):
        check()
        _fields(candidate, ("candidate_id", "score_semantics", "model_sha256", "prediction_sha256", "scores"))
        ident = candidate["candidate_id"]
        if type(ident) is not str or ident not in CANDIDATE_IDS or ident in candidates:
            raise ValueError("Fixed unique candidate registry required")
        _text(candidate["score_semantics"])
        _sha(candidate["model_sha256"])
        _sha(candidate["prediction_sha256"])
        scores = candidate["scores"]
        if type(scores) is not dict or set(scores) != set(nights):
            raise ValueError("All candidates must cover the same complete nights")
        for night, values in scores.items():
            if type(values) is not dict or set(values) != set(nights[night]["area_ids"]):
                raise ValueError("All candidates must cover every forecast area")
            for number in values.values():
                check()
                _number(number)
            if ident == "uniform" and len(set(values.values())) != 1:
                raise ValueError("Uniform baseline must have constant spatial scores per night")
        candidates[ident] = candidate
    if next(iter(candidates)) != "uniform":
        raise ValueError("Uniform baseline must be first and present")
    return candidates


def _source_paths(value, sources, check, *, empty=False):
    paths = _items(value, 32, empty=empty)
    for path in paths:
        check()
        if _path(path) not in sources:
            raise ValueError("Unbound ledger source reference")
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate ledger source binding")
    return set(paths)


def _ledger(value, nights, check):
    _fields(value, ("schema_version", "source_refs", "complete_scopes", "events", "ledger_sha256"))
    if value["schema_version"] != "habu-stage1-ledger-v1":
        raise ValueError("Unsupported individual ledger projection")
    if _sha(value["ledger_sha256"]) != _digest({k: v for k, v in value.items() if k != "ledger_sha256"}, check):
        raise ValueError("Ledger projection digest mismatch")
    sources = {}
    for ref in _items(value["source_refs"], MAX_SOURCES, empty=True):
        check()
        path = _ref(ref)
        if path in sources:
            raise ValueError("Duplicate source identity")
        sources[path] = ref
    scopes, incomplete = {}, False
    for scope in _items(value["complete_scopes"], MAX_NIGHTS, empty=True):
        check()
        _fields(scope, ("operational_night", "scope_sha256", "horizon_start", "horizon_end",
                        "declaration", "coverage_ref", "source_paths"))
        night = scope["operational_night"]
        if type(night) is not str or night not in nights or night in scopes:
            raise ValueError("Duplicate or foreign ledger scope")
        forecast = nights[night]
        if (_sha(scope["scope_sha256"]) != forecast["scope_sha256"] or
                any(_time(scope[key]) != _time(forecast[key]) for key in ("horizon_start", "horizon_end"))):
            raise ValueError("Ledger and forecast scope/horizon differ")
        if scope["declaration"] not in ("DECLARED_COMPLETE", "INCOMPLETE", "UNKNOWN"):
            raise ValueError("Explicit ledger completeness declaration required")
        complete = scope["declaration"] == "DECLARED_COMPLETE"
        incomplete = incomplete or not complete
        _source_paths(scope["source_paths"], sources, check, empty=not complete)
        ref = scope["coverage_ref"]
        if ref is not None or complete:
            if sources.get(_ref(ref)) != ref:
                raise ValueError("Unbound complete-coverage reference")
        scopes[night] = scope
    individuals, events, count = set(), set(), 0
    by_night = {night: [] for night in nights}
    for event in _items(value["events"], MAX_EVENTS, empty=True):
        check()
        _fields(event, ("event_id", "operational_night", "datetime", "utm_x_m", "utm_y_m",
                        "individual_ids", "source_paths"))
        ident = _text(event["event_id"])
        if ident in events:
            raise ValueError("Duplicate canonical event identity")
        events.add(ident)
        night = event["operational_night"]
        if type(night) is not str or night not in nights:
            raise ValueError("Event outside selected operational nights")
        forecast, instant = nights[night], _time(event["datetime"])
        try:
            actual_night = (instant.astimezone(JST) - timedelta(hours=7)).date().isoformat()
        except OverflowError as exc:
            raise ValueError("Actual night outside supported range") from exc
        if (actual_night != night or
                not _time(forecast["horizon_start"]) <= instant < _time(forecast["horizon_end"])):
            raise ValueError("Actual event contradicts night/horizon")
        x, y = _number(event["utm_x_m"]), _number(event["utm_y_m"])
        x0, y0, x1, y1 = forecast["scope"]["bbox_utm"]
        if not (x0 <= x < x1 and y0 <= y < y1):
            raise ValueError("Actual event point outside fixed geographic scope")
        refs = _source_paths(event["source_paths"], sources, check)
        if night in scopes and not refs <= set(scopes[night]["source_paths"]):
            raise ValueError("Event source is outside ledger coverage sources")
        ids = _items(event["individual_ids"], MAX_INDIVIDUALS)
        count += len(ids)
        if count > MAX_INDIVIDUALS:
            raise Stage1CapacityBlocked("CAPACITY_BLOCKED: individual limit")
        for individual in ids:
            check()
            individual = _text(individual)
            if individual in individuals:
                raise ValueError("Duplicate canonical individual identity")
            individuals.add(individual)
        by_night[night].append(dict(event, area_id=_area_id(x, y)))
    return by_night, incomplete or set(scopes) != set(nights)


def _common():
    return {
        "schema_version": VERSION, "scientific_status": "NOT_VALIDATED",
        "policy_sha256": POLICY_DIGEST, "top_k": TOP_K,
        "source_authenticated": False, "confirmation_source_authenticated": False,
        "official_stage1_recall_computed": False, "official_threshold_pass": False,
        "fit_authorized": False, "production_authorized": False,
        "scope_digest_semantics": "CANONICAL_SUPPLIED_UTM_SCOPE_NOT_SOURCE_FILE_SHA",
        "denominator_semantics": "DECLARED_COMPLETE_INDIVIDUAL_LEDGER_INCLUDING_OUTSIDE_UNIVERSE_MISSES",
        "limitations": ["Source hashes and completeness declarations are not independently authenticated",
                        "No trusted pre-reveal receipt, independent confirmation or geographic completeness is proved",
                        "Fixed input scores are used for ranking only, never recalibrated or converted to probabilities"],
    }


def _finish(result, check):
    check()
    result["receipt_sha256"] = _digest(result, check)
    check()
    return result


def _percentile(ordered, fraction):
    """Linear interpolation at (n-1)*fraction, without external libraries."""
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _uncertainty(per_night, pooled, candidates, check):
    """Paired night draws preserve the common full-cohort denominator."""
    rng = random.Random(BOOTSTRAP_SEED)
    count = len(per_night)
    informative = sum(item["denominator"] > 0 for item in per_night)
    differences = {ident: [] for ident in candidates if ident != "uniform"}
    zero_denominator = 0
    for _ in range(BOOTSTRAP_REPLICATES):
        check()
        sample = [per_night[rng.randrange(count)] for _ in range(count)]
        denominator = sum(item["denominator"] for item in sample)
        if not denominator:
            zero_denominator += 1
            continue
        for ident, draws in differences.items():
            check()
            difference = sum(item["candidates"][ident]["numerator"] -
                             item["candidates"]["uniform"]["numerator"] for item in sample)
            draws.append(difference / denominator)
    comparisons = {}
    for ident, draws in differences.items():
        check()
        draws.sort()
        check()
        comparisons[ident] = {
            "pooled_recall_difference": (pooled[ident]["numerator"] - pooled["uniform"]["numerator"]) /
            pooled[ident]["denominator"] if pooled[ident]["denominator"] else None,
            "interval_95": [_percentile(draws, 0.025), _percentile(draws, 0.975)]
            if informative >= 2 and draws else None,
            "status": "DESCRIPTIVE_ONLY" if informative >= 2 and draws else "TOO_FEW_INFORMATIVE_NIGHTS",
        }
    return {
        "method": "PAIRED_NIGHT_BLOCK_BOOTSTRAP", "seed": BOOTSTRAP_SEED,
        "replicates": BOOTSTRAP_REPLICATES, "night_count": count,
        "informative_night_count": informative,
        "valid_replicates": BOOTSTRAP_REPLICATES - zero_denominator,
        "zero_denominator_draws": zero_denominator,
        "percentile_method": "LINEAR_AT_N_MINUS_ONE_TIMES_QUANTILE",
        "comparisons": comparisons, "minimum_nights": MINIMUM_NIGHTS,
        "minimum_nights_status": "MET_NOT_SUFFICIENT" if count >= MINIMUM_NIGHTS else "BELOW_PROCESS_FLOOR",
        "adequacy": "NOT_ESTABLISHED", "independence": "NOT_VERIFIED",
        "small_n_warning": informative < MINIMUM_NIGHTS,
    }


def evaluate_full_ledger_stage1(forecast_universe, candidate_scores, ledger, *, budget_seconds=30):
    """Compute complete-cohort diagnostic counts; missing data never yields partial metrics."""
    if (type(budget_seconds) not in (int, float) or not 0 < budget_seconds <= MAX_BUDGET_SECONDS or
            not math.isfinite(budget_seconds)):
        raise ValueError("Budget must be finite, positive and at most 300 seconds")
    deadline = time.monotonic() + budget_seconds

    def check():
        if time.monotonic() >= deadline:
            raise Stage1BudgetBlocked("RUNTIME_BLOCKED: shared Stage1 deadline expired")

    check()
    universe, scores, outcomes = _copy_json([forecast_universe, candidate_scores, ledger], check)
    base = dict(_common(), per_night=[], pooled={}, paired_uncertainty={})
    if any(value is None for value in (universe, scores, outcomes)):
        return _finish(dict(base, status="NEED_MORE_DATA", blockers=["MISSING_INPUT_PROJECTION"]), check)
    nights = _universe(universe, check)
    candidates = _scores(scores, universe, nights, check)
    events, missing = _ledger(outcomes, nights, check)
    if not nights or missing:
        return _finish(dict(base, status="NEED_MORE_DATA", blockers=["COMPLETE_MATCHING_LEDGER_SCOPE_REQUIRED"]), check)
    per_night = []
    for night, forecast in nights.items():
        check()
        actual = events[night]
        ids = [ident for event in actual for ident in event["individual_ids"]]
        areas = set(forecast["area_ids"])
        counts = {}
        for event in actual:
            check()
            counts[event["area_id"]] = counts.get(event["area_id"], 0) + len(event["individual_ids"])
        nightly = {
            "operational_night": night, "denominator": len(ids), "denominator_events": len(actual),
            "denominator_individual_ids_sha256": _digest(sorted(ids), check),
            "denominator_event_ids_sha256": _digest(sorted(event["event_id"] for event in actual), check),
            "forecast_area_count": len(areas), "unique_actual_areas": len(counts),
            "outside_universe_individuals": sum(number for area, number in counts.items() if area not in areas),
            "candidates": {},
        }
        for ident, candidate in candidates.items():
            check()
            values = candidate["scores"][night]
            top = sorted(values, key=lambda area: (-values[area], area))[:TOP_K]
            check()
            numerator = sum(counts.get(area, 0) for area in top)
            nightly["candidates"][ident] = {
                "top10_area_ids": top, "numerator": numerator, "denominator": len(ids),
                "recall": numerator / len(ids) if ids else None,
            }
        per_night.append(nightly)
    denominator = sum(item["denominator"] for item in per_night)
    pooled = {}
    for ident in candidates:
        check()
        numerator = sum(item["candidates"][ident]["numerator"] for item in per_night)
        pooled[ident] = {"numerator": numerator, "denominator": denominator,
                         "recall": numerator / denominator if denominator else None}
    return _finish(dict(base, status="DIAGNOSTIC_ONLY", per_night=per_night, pooled=pooled,
                        paired_uncertainty=_uncertainty(per_night, pooled, candidates, check),
                        candidate_lineage={ident: {key: candidate[key] for key in
                                                   ("score_semantics", "model_sha256", "prediction_sha256")}
                                           for ident, candidate in candidates.items()},
                        unique_forecast_areas=len({area for forecast in nights.values() for area in forecast["area_ids"]}),
                        unique_actual_areas=len({event["area_id"] for rows in events.values() for event in rows}),
                        input_digests={"universe": _digest(universe, check), "scores": _digest(scores, check),
                                       "ledger": _digest(outcomes, check)},
                        blockers=[] if denominator else ["NO_CONFIRMED_INDIVIDUALS"]), check)
