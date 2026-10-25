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
VERSION_V2 = "habu-full-ledger-stage1-diagnostic-v2"
SCORES_VERSION_V2 = "habu-stage1-scores-v2"
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


def _scores(value, universe, nights, check, *, registry=None):
    _fields(value, ("schema_version", "universe_sha256", "candidates"))
    if value["schema_version"] != "habu-stage1-scores-v1":
        raise ValueError("Unsupported Stage1 score projection")
    _sha(value['universe_sha256'])
    if universe is not None and value['universe_sha256'] != _digest(universe, check):
        raise ValueError("Scores do not bind the complete forecast universe")
    candidates = {}
    for candidate in _items(value["candidates"], 3):
        check()
        _fields(candidate, ("candidate_id", "score_semantics", "model_sha256", "prediction_sha256", "scores"))
        ident = candidate["candidate_id"]
        if type(ident) is not str or ident not in (CANDIDATE_IDS if registry is None else registry) or ident in candidates:
            raise ValueError("Fixed unique candidate registry required")
        _text(candidate["score_semantics"])
        _sha(candidate["model_sha256"])
        _sha(candidate["prediction_sha256"])
        scores = candidate["scores"]
        if type(scores) is not dict or (nights is not None and set(scores) != set(nights)):
            raise ValueError("All candidates must cover the same complete nights")
        if nights is None:
            if len(scores) > MAX_NIGHTS:
                raise Stage1CapacityBlocked("CAPACITY_BLOCKED: score nights")
            if candidates and set(scores) != set(next(iter(candidates.values()))['scores']):
                raise ValueError("All candidates must cover the same supplied score nights")
        total = 0
        for night, values in scores.items():
            if type(values) is not dict or (nights is not None and set(values) != set(nights[night]["area_ids"])):
                raise ValueError("All candidates must cover every forecast area")
            if nights is None:
                _night(night)
                total += len(values)
                if total > MAX_AREA_NIGHT_CELLS:
                    raise Stage1CapacityBlocked("CAPACITY_BLOCKED: supplied score areas")
                if not values or any(type(area) is not str or not AREA.fullmatch(area) for area in values):
                    raise ValueError("Canonical nonempty score areas required")
                for area in values:
                    check()
                    ax, ay = map(int, AREA.fullmatch(area).groups())
                    if not (100 <= ax < 900 and 0 <= ay < 10000):
                        raise ValueError('Supplied score area outside the UTM52N coordinate domain')
                if candidates and set(values) != set(next(iter(candidates.values()))['scores'][night]):
                    raise ValueError("All candidates must cover the same supplied areas")
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
        if type(night) is not str or (nights is not None and night not in nights) or night in scopes:
            raise ValueError("Duplicate or foreign ledger scope")
        if nights is None:
            _sha(scope['scope_sha256'])
            try:
                start = datetime.combine(_night(night), day_time(7), JST)
                end = start + timedelta(days=1)
            except OverflowError as exc:
                raise ValueError('Supplied ledger night outside supported range') from exc
            if not start <= _time(scope['horizon_start']) < _time(scope['horizon_end']) <= end:
                raise ValueError('Supplied ledger horizon contradicts operational night')
        else:
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
    by_night = {night: [] for night in (nights if nights is not None else scopes)}
    for event in _items(value["events"], MAX_EVENTS, empty=True):
        check()
        _fields(event, ("event_id", "operational_night", "datetime", "utm_x_m", "utm_y_m",
                        "individual_ids", "source_paths"))
        ident = _text(event["event_id"])
        if ident in events:
            raise ValueError("Duplicate canonical event identity")
        events.add(ident)
        night = event["operational_night"]
        if type(night) is not str or (nights is not None and night not in nights):
            raise ValueError("Event outside selected operational nights")
        if nights is None:
            _night(night)
        forecast = nights[night] if nights is not None else scopes.get(night)
        instant = _time(event['datetime'])
        try:
            actual_night = (instant.astimezone(JST) - timedelta(hours=7)).date().isoformat()
        except OverflowError as exc:
            raise ValueError("Actual night outside supported range") from exc
        if (actual_night != night or (forecast is not None and
                not _time(forecast["horizon_start"]) <= instant < _time(forecast["horizon_end"]))):
            raise ValueError("Actual event contradicts night/horizon")
        x, y = _number(event["utm_x_m"]), _number(event["utm_y_m"])
        if nights is None:
            # Coordinate type/domain only; this is not a fabricated cohort
            # scope. Geographic membership awaits the missing universe.
            if not (100000 <= x < 900000 and 0 <= y < 10000000):
                raise ValueError('Actual point outside the UTM52N coordinate domain')
        else:
            x0, y0, x1, y1 = nights[night]["scope"]["bbox_utm"]
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
        by_night.setdefault(night, []).append(dict(event, area_id=_area_id(x, y)))
        if nights is None and len(by_night) > MAX_NIGHTS:
            raise Stage1CapacityBlocked('CAPACITY_BLOCKED: supplied ledger event nights')
    return by_night, incomplete or (nights is not None and set(scopes) != set(nights))


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


def evaluate_full_ledger_stage1(forecast_universe, candidate_scores, ledger, *, budget_seconds=30, check=None):
    """Compute complete-cohort diagnostic counts; missing data never yields partial metrics."""
    if (type(budget_seconds) not in (int, float) or not 0 < budget_seconds <= MAX_BUDGET_SECONDS or
            not math.isfinite(budget_seconds)):
        raise ValueError("Budget must be finite, positive and at most 300 seconds")
    deadline = time.monotonic() + budget_seconds
    caller_check = check
    if caller_check is not None and not callable(caller_check):
        raise ValueError("Parent budget check must be callable")

    def check():
        if caller_check is not None:
            caller_check()
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
    return _finish(_measure(universe, scores, outcomes, nights, candidates, events, base, check), check)


def _measure(universe, scores, outcomes, nights, candidates, events, base, check, *, _summary_identity=False):
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
    return dict(base, status="DIAGNOSTIC_ONLY", per_night=per_night, pooled=pooled,
                        paired_uncertainty=_uncertainty(per_night, pooled, candidates, check),
                        candidate_lineage={ident: {key: candidate[key] for key in
                                                   (("score_semantics", "model_sha256", "recipe_sha256", "score_stream_sha256")
                                                    if _summary_identity else
                                                    ("score_semantics", "model_sha256", "prediction_sha256"))}
                                           for ident, candidate in candidates.items()},
                        unique_forecast_areas=len({area for forecast in nights.values() for area in forecast["area_ids"]}),
                        unique_actual_areas=len({event["area_id"] for rows in events.values() for event in rows}),
                        input_digests={"universe": _digest(universe, check), "scores": _digest(scores, check),
                                       "ledger": _digest(outcomes, check)},
                        blockers=[] if denominator else ["NO_CONFIRMED_INDIVIDUALS"])


def _configured_scores(value, universe, nights, choices, config_sha, definition_sha, recipe_sha, check):
    _fields(value, ('schema_version', 'universe_sha256', 'candidate_config_sha256',
                    'feature_definition_sha256', 'candidates'))
    if (value['schema_version'] != SCORES_VERSION_V2 or
            _sha(value['candidate_config_sha256']) != config_sha or
            _sha(value['feature_definition_sha256']) != definition_sha):
        raise ValueError('Configured score version/config/feature-definition mismatch')
    rows = _items(value['candidates'], 3)
    if [row.get('candidate_id') if type(row) is dict else None for row in rows] != choices:
        raise ValueError('Scores must preserve exactly the three configured candidates in order')
    projected = []
    for row in rows:
        check()
        _fields(row, ('candidate_id', 'score_semantics', 'model_sha256', 'prediction_sha256',
                      'candidate_config_sha256', 'recipe_sha256', 'scores'))
        expected_recipe = recipe_sha if row['candidate_id'] == 'HB-A1' else None
        if (_sha(row['candidate_config_sha256']) != config_sha or row['recipe_sha256'] != expected_recipe):
            raise ValueError('Candidate config or full HB-A1 recipe digest mismatch')
        projected.append({key: row[key] for key in
            ('candidate_id', 'score_semantics', 'model_sha256', 'prediction_sha256', 'scores')})
    # Reuse score structure/common-universe validation. The per-call registry
    # never modifies the legacy module constant or the public v1 API.
    _scores(dict(schema_version='habu-stage1-scores-v1', universe_sha256=value['universe_sha256'],
                 candidates=projected), universe, nights, check, registry=tuple(choices))
    return {row['candidate_id']: row for row in rows}


def evaluate_full_ledger_stage1_v2(forecast_universe, candidate_scores, ledger, *, candidate_config,
        expected_config_sha256, feature_definition_sha256, budget_seconds=30, check=None):
    """Configured three-slot pure diagnostic, never registration or selection.

All supplied inputs are validated before missing-data return. Absent universe
facts are left unknown rather than synthesized from an observed ledger.
"""
    if (type(budget_seconds) not in (int, float) or not 0 < budget_seconds <= MAX_BUDGET_SECONDS or
            not math.isfinite(budget_seconds)):
        raise ValueError('Budget must be finite, positive and at most 300 seconds')
    deadline = time.monotonic() + budget_seconds
    parent_check = check
    if parent_check is not None and not callable(parent_check):
        raise ValueError('Parent budget check must be callable')

    def guard():
        if parent_check is not None:
            parent_check()
        if time.monotonic() >= deadline:
            raise Stage1BudgetBlocked('RUNTIME_BLOCKED: shared Stage1 v2 deadline expired')

    guard()
    expected, definition = _sha(expected_config_sha256), _sha(feature_definition_sha256)
    # One combined 16MiB snapshot/copy, not four independent byte allowances.
    universe, scores, outcomes, config = _copy_json(
        [forecast_universe, candidate_scores, ledger, candidate_config], guard)
    from research_model_adapter import _v2_config, ResearchCapacityBlocked
    try:
        choices = _v2_config(config, expected, definition, guard)
    except ResearchCapacityBlocked as exc:
        raise Stage1CapacityBlocked(str(exc)) from exc
    recipe_sha = _digest(config['hba1_recipe'], guard) if 'HB-A1' in choices else None
    nights = _universe(universe, guard) if universe is not None else None
    candidates = _configured_scores(scores, universe, nights, choices, expected,
        definition, recipe_sha, guard) if scores is not None else None
    events, incomplete = _ledger(outcomes, nights, guard) if outcomes is not None else (None, True)
    if nights is None and candidates is not None and outcomes is not None:
        score_nights = set(next(iter(candidates.values()))['scores'])
        for records in (outcomes['complete_scopes'], outcomes['events']):
            for record in records:
                guard()
                if record['operational_night'] not in score_nights:
                    raise ValueError('Supplied ledger night is absent from the complete supplied candidate scores')
    base = dict(_common(), schema_version=VERSION_V2,
        candidate_ids=list(choices), candidate_config_sha256=expected, feature_definition_sha256=definition,
        per_night=[], pooled={}, paired_uncertainty={})
    base['limitations'].append('Config/recipe digests are declared identities, not trusted preregistration or file authentication')
    if any(value is None for value in (universe, scores, outcomes)):
        result = dict(base, status='NEED_MORE_DATA', blockers=['MISSING_INPUT_PROJECTION'])
    elif not nights or incomplete:
        result = dict(base, status='NEED_MORE_DATA', blockers=['COMPLETE_MATCHING_LEDGER_SCOPE_REQUIRED'])
    else:
        result = _measure(universe, scores, outcomes, nights, candidates, events, base, guard)
        for ident, lineage in result['candidate_lineage'].items():
            guard()
            lineage.update(candidate_config_sha256=expected, recipe_sha256=recipe_sha if ident == 'HB-A1' else None)
    if 'input_digests' not in result:
        result['input_digests'] = {name: _digest(value, guard) if value is not None else None
            for name, value in (('universe', universe), ('scores', scores), ('ledger', outcomes))}
    result['input_digests']['config'] = expected
    return _finish(result, guard)


# Explicit summary identities do not satisfy the native prediction contract.
SUMMARY_VERSION = 'habu-full-ledger-stage1-summary-diagnostic-v1'
SUMMARY_SCORES_VERSION = 'habu-stage1-summary-scores-v1'
SUMMARY_PROJECTION_VERSION = 'habu-g0-score-summary-projection-v1'
SUMMARY_SEMANTICS = 'MEAN_NATIVE_UNIT_SPATIAL_SCORE'
SUMMARY_PROJECTION_FIELDS = ('schema_version','purpose','summary_manifest_ref','summary_manifest_canonical_sha256',
    'operational_night','fit_cutoff','forecast_cutoff','forecast_manifest_ref','canonical_joined_rows_sha256',
    'domain_ref','horizon','candidate_ids','candidate_config_source','candidate_config_sha256',
    'feature_definition_sha256','fit_lineage','training_selection_sha256','model_bindings','full_counts','model_summaries')
SUMMARY_CONFIG_FIELDS = ('manifest_ref','manifest_canonical_sha256','config_ref','config_sha256','cycle_ref',
    'cycle_canonical_sha256','code_sha256_by_path','code_map_sha256','policy_ref','policy_canonical_sha256')
SUMMARY_AUTHORITIES = ('fit_authorized','selection_authorized','promotion_authorized',
    'scientific_execution_authorized','official_issuance_authorized','production_activation_authorized',
    'confirmation_authorized','trusted_campaign_authorized','trusted_pre_reveal_authorized')


def _summary_bound(value, check):
    """New combined limit only; preserve insertion order and all old defaults."""
    pending=[(value,0)];nodes=0
    while pending:
        check();item,depth=pending.pop();nodes+=1
        if depth>12 or nodes>MAX_JSON_NODES:
            raise Stage1CapacityBlocked('CAPACITY_BLOCKED: summary transport JSON complexity')
        kind=type(item)
        if kind in (dict,list):
            if len(item)>MAX_JSON_NODES-nodes-len(pending):
                raise Stage1CapacityBlocked('CAPACITY_BLOCKED: summary transport pending nodes')
            if kind is dict:
                for key in item:
                    check()
                    if type(key) is not str or len(key)>512:
                        raise ValueError('Bounded string JSON keys required')
            pending.extend((child,depth+1) for child in (item.values() if kind is dict else item))
        elif kind is str:
            if len(item)>4096 or len(item.encode('utf-8'))>4096:
                raise Stage1CapacityBlocked('CAPACITY_BLOCKED: summary transport string length')
        elif kind is int:
            if item.bit_length()>64:
                raise Stage1CapacityBlocked('CAPACITY_BLOCKED: summary transport integer width')
        elif kind is float:
            if not math.isfinite(item):raise ValueError('Nonfinite summary metadata')
        elif kind not in (bool,type(None)):
            raise ValueError('JSON-only summary declarations required')
    # Streaming canonical encoding bounds bytes before an additional owned copy.
    for _ in _encoded(value,check):pass


def _summary_copy(value, check):
    _summary_bound(value,check)
    def own(item):
        check()
        if type(item) is dict:
            result={}
            for key,child in item.items():check();result[key]=own(child)
            return result
        if type(item) is list:
            result=[]
            for child in item:check();result.append(own(child))
            return result
        return item
    return own(value)


def _summary_ref(value):
    _fields(value,('path','sha256','size_bytes'))
    path=_text(value['path'],512)
    parsed=PurePosixPath(path)
    if ('\\' in path or ':' in path or parsed.is_absolute() or str(parsed)!=path or
            any(ord(c)<32 or ord(c)==127 for c in path) or
            any(part in ('','.','..') or part.casefold() in
                {'original','incoming','reports','sealed','confirmation'} for part in path.split('/'))):
        raise ValueError('Canonical non-reveal summary reference required')
    _sha(value['sha256'])
    if type(value['size_bytes']) is not int or not 0<value['size_bytes']<=128*1024**2:
        raise ValueError('Explicit bounded physical source size required')
    return value


def _summary_binding(value,field,cutoff,check):
    _fields(value,('ref',field,'readiness','usable_at'))
    _summary_ref(value['ref']);_sha(value[field])
    from prospective_inputs import READINESS_FIELDS
    _fields(value['readiness'],READINESS_FIELDS)
    stamps=[]
    for stamp in value['readiness'].values():check();stamps.append(_time(stamp))
    # The actual producer also includes parent availability in this maximum.
    # The compact projection intentionally does not carry those execution
    # receipts, so pure admission checks the known lower bound, not a false
    # equality with only this node's own stamps. Source admission redoes all
    # original parent-aware checks before constructing this projection.
    usable=_time(value['usable_at'])
    if usable<max(stamps) or usable>=cutoff:
        raise ValueError('Summary bound source readiness contradicts cutoff')


def _summary_projection(value,choices,config_sha,definition_sha,recipe_sha,check):
    """Validate a declared content projection, without attesting absent files."""
    _fields(value,SUMMARY_PROJECTION_FIELDS)
    if (value['schema_version']!=SUMMARY_PROJECTION_VERSION or
            value['purpose']!='DEVELOPMENT_EVALUATION_ONLY' or value['candidate_ids']!=choices or
            _sha(value['candidate_config_sha256'])!=config_sha or
            _sha(value['feature_definition_sha256'])!=definition_sha):
        raise ValueError('Summary projection version/config/definition mismatch')
    if set(choices)!={'uniform','HB-A0','HB-A1'}:
        raise ValueError('IMPLEMENTATION_BLOCKED: summary supports uniform/A0/A1 only')
    night=value['operational_night'];_night(night)
    fit,cutoff=_time(value['fit_cutoff']),_time(value['forecast_cutoff'])
    night_start=_time(night+'T07:00:00+09:00')
    if not fit<night_start<=cutoff:
        raise ValueError('Summary fit/cutoff chronology mismatch')
    for key in ('summary_manifest_ref','forecast_manifest_ref','domain_ref'):_summary_ref(value[key])
    for key in ('summary_manifest_canonical_sha256','canonical_joined_rows_sha256','training_selection_sha256'):_sha(value[key])
    source=value['candidate_config_source'];_fields(source,SUMMARY_CONFIG_FIELDS)
    for key in ('manifest_ref','config_ref','cycle_ref','policy_ref'):_summary_ref(source[key])
    for key in ('manifest_canonical_sha256','config_sha256','cycle_canonical_sha256','code_map_sha256','policy_canonical_sha256'):_sha(source[key])
    if source['config_sha256']!=config_sha:
        raise ValueError('Summary source config identity mismatch')
    code=source['code_sha256_by_path']
    from codex_cycle_contract import MAX_REFERENCES,POLICY_PATH
    if type(code) is not dict or not code or len(code)>MAX_REFERENCES:
        raise ValueError('Bounded full summary code map required')
    for path,identity in code.items():
        check();_text(path,512);_sha(identity)
        if ('\\' in path or ':' in path or any(ord(c)<32 or ord(c)==127 for c in path) or
                any(part in ('','.','..') or part.casefold() in {'original','incoming','reports','sealed','confirmation'}
                    for part in path.split('/')) or not
                ((path.startswith(('src/','scripts/')) and path.endswith('.py')) or
                 (path.startswith('schemas/') and path.endswith('.json')) or
                 path in {'requirements-analysis.txt','requirements-osm.txt'})):
            raise ValueError('Summary runtime code path mismatch')
    if (_digest(code,check)!=source['code_map_sha256'] or source['policy_ref']['path']!=POLICY_PATH or
            source['policy_canonical_sha256']!=POLICY_DIGEST):
        raise ValueError('Summary code/policy identity mismatch')
    _summary_binding(value['fit_lineage'],'lineage_sha256',cutoff,check)
    # Reuse the original pure horizon rules, without materializing any units.
    from g0_forecast_contract import _horizon,MAX_DOMAIN_CELLS,MAX_WINDOWS,MAX_SHARDS,MAX_DOMAIN_ROWS
    try:first,last,windows=_horizon(value['horizon'],night,cutoff)
    except OverflowError as exc:raise ValueError('Summary horizon exceeds datetime range') from exc
    full=value['full_counts'];_fields(full,('cell_count','window_count','shard_count','unit_count','area_count'))
    limits=dict(cell_count=MAX_DOMAIN_CELLS,window_count=MAX_WINDOWS,shard_count=MAX_SHARDS,
                unit_count=MAX_DOMAIN_ROWS,area_count=10_000)
    if any(type(full[key]) is not int or not 0<full[key]<=limit for key,limit in limits.items()):
        raise ValueError('Summary full counts are invalid')
    if (full['window_count']!=windows or full['unit_count']!=full['cell_count']*windows or
            full['area_count']>full['cell_count']):
        raise ValueError('Summary full rectangular counts disagree')
    bindings=_items(value['model_bindings'],3);summaries=_items(value['model_summaries'],3)
    if (len(bindings)!=3 or len(summaries)!=3 or
            [b.get('candidate_id') if type(b) is dict else None for b in bindings]!=choices or
            [s.get('candidate_id') if type(s) is dict else None for s in summaries]!=choices):
        raise ValueError('Summary full ordered candidate set required')
    area_ids=None;area_unit_counts=None;models={}
    for binding,model in zip(bindings,summaries):
        check();_fields(binding,('candidate_id','artifact'))
        _summary_binding(binding['artifact'],'model_sha256',cutoff,check)
        _fields(model,('candidate_id','model_sha256','recipe_sha256','score_semantics','score_stream_sha256',
                      'unit_count','area_summaries','top10_area_ids'))
        ident=model['candidate_id'];expected_recipe=recipe_sha if ident=='HB-A1' else None
        if (_sha(model['model_sha256'])!=binding['artifact']['model_sha256'] or
                model['recipe_sha256']!=expected_recipe or model['score_semantics']!=SUMMARY_SEMANTICS or
                type(model['unit_count']) is not int or model['unit_count']!=full['unit_count']):
            raise ValueError('Summary native model/recipe/score binding mismatch')
        _sha(model['score_stream_sha256'])
        areas=_items(model['area_summaries'],10_000);ids=[];total=0;means={};counts={}
        if len(areas)!=full['area_count']:raise ValueError('Incomplete summary area set')
        for area in areas:
            check();_fields(area,('area_id','unit_count','mean_native_score'))
            ident_area=area['area_id'];match=AREA.fullmatch(ident_area) if type(ident_area) is str else None
            if not match:raise ValueError('Canonical summary area required')
            ax,ay=map(int,match.groups())
            if not (100<=ax<900 and 0<=ay<10000):raise ValueError('Summary area outside UTM52N')
            number=area['unit_count'];score=_number(area['mean_native_score'])
            if type(number) is not int or number<=0 or number%windows or not 0<=score<=1:
                raise ValueError('Summary physical area count or native probability invalid')
            ids.append(ident_area);total+=number;means[ident_area]=score;counts[ident_area]=number
        if ids!=sorted(set(ids)) or total!=full['unit_count'] or area_ids is not None and ids!=area_ids:
            raise ValueError('Summary areas must cover the complete shared sorted domain')
        if area_unit_counts is not None and counts!=area_unit_counts:
            raise ValueError('All candidates must cover the same physical per-area unit counts')
        if ident=='uniform' and len(set(means.values()))!=1:raise ValueError('Uniform summary must be spatially constant')
        def rank(area):check();return (-means[area],area)
        if model['top10_area_ids']!=sorted(means,key=rank)[:TOP_K]:
            raise ValueError('Summary Top10 differs from complete native means')
        area_ids=ids;area_unit_counts=counts;models[ident]=model
    return night,area_ids,models


def _summary_scores(value,universe,nights,choices,config_sha,definition_sha,recipe_sha,check):
    _fields(value,('schema_version','universe_sha256','candidate_config_sha256','feature_definition_sha256',
        'score_summary_projection','score_summary_projection_sha256','summary_execution_receipt_sha256','candidates'))
    if (value['schema_version']!=SUMMARY_SCORES_VERSION or _sha(value['candidate_config_sha256'])!=config_sha or
            _sha(value['feature_definition_sha256'])!=definition_sha):
        raise ValueError('Summary score header/config/definition mismatch')
    _sha(value['summary_execution_receipt_sha256'])
    body=value['score_summary_projection']
    if _sha(value['score_summary_projection_sha256'])!=_digest(body,check):
        raise ValueError('Summary stable whole projection digest mismatch')
    night,areas,models=_summary_projection(body,choices,config_sha,definition_sha,recipe_sha,check)
    if (_sha(value['universe_sha256'])!=(_digest(universe,check) if universe is not None else value['universe_sha256']) or
            nights is not None and (list(nights)!=[night] or nights[night]['area_ids']!=areas)):
        raise ValueError('Summary scores must bind exactly one complete forecast night')
    if nights is not None:
        scope=nights[night]
        if (any(_time(scope[key])!=_time(body[source]) for key,source in
                (('cutoff_time','forecast_cutoff'),)) or
                _time(scope['horizon_start'])!=_time(body['horizon']['start']) or
                _time(scope['horizon_end'])!=_time(body['horizon']['end'])):
            raise ValueError('Summary universe cutoff/horizon mismatch')
    rows=_items(value['candidates'],3)
    if len(rows)!=3 or [r.get('candidate_id') if type(r) is dict else None for r in rows]!=choices:
        raise ValueError('Exact ordered summary candidates required')
    result={}
    for row in rows:
        check();_fields(row,('candidate_id','score_semantics','model_sha256','recipe_sha256','score_stream_sha256','scores'))
        model=models[row['candidate_id']]
        for key in ('score_semantics','model_sha256','recipe_sha256','score_stream_sha256'):
            if row[key]!=model[key]:raise ValueError('Summary candidate identity differs from complete projection')
        values=row['scores']
        if type(values) is not dict or list(values)!=[night] or type(values[night]) is not dict or list(values[night])!=areas:
            raise ValueError('Summary score map must preserve the exact complete sorted areas')
        for area in model['area_summaries']:
            check()
            if _number(values[night][area['area_id']])!=area['mean_native_score']:
                raise ValueError('Summary candidate mean differs from content projection')
        result[row['candidate_id']]=row
    return result


def evaluate_full_ledger_stage1_summary_v1(forecast_universe,summary_scores,ledger,*,candidate_config,
        expected_config_sha256,feature_definition_sha256,budget_seconds=30,check=None):
    """Pure one-night diagnostic with explicit framed-stream content identity."""
    if type(budget_seconds) not in (int,float) or not math.isfinite(budget_seconds) or not 0<budget_seconds<=MAX_BUDGET_SECONDS:
        raise ValueError('Budget must be finite, positive and at most 300 seconds')
    parent_check=check
    if parent_check is not None and not callable(parent_check):raise ValueError('Parent check must be callable')
    deadline=time.monotonic()+budget_seconds
    callback_error=None
    def guard():
        nonlocal callback_error
        if parent_check is not None:
            try:parent_check()
            except BaseException as exc:callback_error=exc;raise
        if time.monotonic()>=deadline:raise Stage1BudgetBlocked('RUNTIME_BLOCKED: summary Stage1 deadline expired')
    guard();expected,definition=_sha(expected_config_sha256),_sha(feature_definition_sha256)
    universe,scores,outcomes,config=_summary_copy([forecast_universe,summary_scores,ledger,candidate_config],guard)
    from research_model_adapter import _v2_config,ResearchCapacityBlocked
    try:choices=_v2_config(config,expected,definition,guard)
    except ResearchCapacityBlocked as exc:
        if exc is callback_error:raise
        raise Stage1CapacityBlocked(str(exc)) from exc
    if set(choices)!={'uniform','HB-A0','HB-A1'}:
        raise ValueError('IMPLEMENTATION_BLOCKED: summary supports uniform/A0/A1 only')
    recipe=_digest(config['hba1_recipe'],guard)
    nights=_universe(universe,guard) if universe is not None else None
    candidates=_summary_scores(scores,universe,nights,choices,expected,definition,recipe,guard) if scores is not None else None
    events,incomplete=_ledger(outcomes,nights,guard) if outcomes is not None else (None,True)
    if nights is None and candidates is not None and outcomes is not None:
        body=scores['score_summary_projection'];night=body['operational_night']
        first,last=_time(body['horizon']['start']),_time(body['horizon']['end'])
        # Full scores already bind their night/horizon even if geographic
        # universe facts are absent. Check these known temporal intersections
        # without inventing a bbox, scope digest, cohort or denominator.
        for row in outcomes['complete_scopes']:
            guard()
            if (row['operational_night']!=night or _time(row['horizon_start'])!=first or
                    _time(row['horizon_end'])!=last):
                raise ValueError('Ledger scope night/horizon differs from complete summary scores')
        for row in outcomes['events']:
            guard()
            if row['operational_night']!=night or not first<=_time(row['datetime'])<last:
                raise ValueError('Ledger actual time/night differs from complete summary scores')
    base=dict(_common(),schema_version=SUMMARY_VERSION,candidate_ids=list(choices),candidate_config_sha256=expected,
        feature_definition_sha256=definition,score_identity_kind='G0_SCORE_SUMMARY_PROJECTION_V1',
        score_summary_projection_sha256=scores['score_summary_projection_sha256'] if scores is not None else None,
        summary_execution_receipt_sha256=scores['summary_execution_receipt_sha256'] if scores is not None else None,
        source_authentication='NOT_ATTESTED',source_consistency='DECLARED_CONSISTENCY_ONLY',
        fit_lineage_authentication='CALLER_DEPENDENCY_REQUIRED',authorities=dict.fromkeys(SUMMARY_AUTHORITIES,False),
        per_night=[],pooled={},paired_uncertainty={})
    base['limitations'].append('Framed streams and supplied content hashes do not authenticate native predictions, files or prereveal execution')
    if any(value is None for value in (universe,scores,outcomes)):
        result=dict(base,status='NEED_MORE_DATA',blockers=['MISSING_INPUT_PROJECTION'])
    elif not nights or incomplete:
        result=dict(base,status='NEED_MORE_DATA',blockers=['COMPLETE_MATCHING_LEDGER_SCOPE_REQUIRED'])
    else:result=_measure(universe,scores,outcomes,nights,candidates,events,base,guard,_summary_identity=True)
    if 'input_digests' not in result:
        result['input_digests']={name:_digest(value,guard) if value is not None else None
            for name,value in (('universe',universe),('scores',scores),('ledger',outcomes))}
    result['input_digests']['config']=expected
    _summary_bound(result,guard);result=_finish(result,guard);_summary_bound(result,guard);guard()
    return result
