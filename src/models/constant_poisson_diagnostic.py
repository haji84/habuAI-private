"""Declared-cohort constant Poisson mechanics, never a source forecast or grant.

Count/effort admission belongs to the existing strict feasibility gate. This
module has no file/network/backend access, target generator or registry seam.
Scalar scenarios are counterfactual exposure, not measured or planned forecasts.
"""
from datetime import timezone
import hashlib
import json
import math
from time import monotonic

from models import count_feasibility as feasibility
from models import research_selection as selection_gate
from g0_forecast_contract import ForecastCapacityError

TARGET = feasibility.TARGET
MODEL_VERSION = 'habu-constant-poisson-model-v1'
FIT_VERSION = 'habu-constant-poisson-fit-v1'
SCENARIO_VERSION = 'habu-constant-poisson-scenario-v1'
MAX_JSON_BYTES = 16 * 1024 ** 2
MAX_JSON_NODES = 2_000_000
MAX_ROWS = MAX_EVENTS = 20_000
MAX_INDIVIDUALS = 100_000
MAX_SOURCE_NODES = 16_384
MAX_SOURCE_EDGES = 32_768
MAX_SCENARIO_SECONDS = 12_000_000
UNIT_FIELDS = {'row_id', 'night', 'cell_x', 'cell_y', 'window_start_jst', 'count', 'active_search_seconds'}
COHORT_FIELDS = {'target', 'owner_id', 'observer_id', 'method_version', 'fit_cutoff', 'heldout_night', 'training_units'}
INPUT_FIELDS = {'selection', 'count_projection', 'effort_projection'}
LINEAGE_FIELDS = {'selection_sha256', 'corpus_sha256', 'count_projection_sha256',
                  'effort_projection_sha256', 'feasibility_assessment_sha256'}


class PoissonCapacityBlocked(ValueError):
    """CAPACITY_BLOCKED: no partial fit or truncated diagnostic."""


class _CallbackFailure(BaseException):
    # Existing child gates classify some ValueErrors. Carry caller exceptions
    # through those handlers and restore the very same object at the API edge.
    def __init__(self, original):
        self.original = original


class _Budget:
    def __init__(self, seconds, check):
        entered = monotonic()
        if (type(seconds) not in (int, float) or not 0 < seconds <= 30 or
                not math.isfinite(seconds) or (check is not None and not callable(check))):
            raise ValueError('Finite 0<budget_seconds<=30 and optional callable required')
        self.deadline, self.check = entered + seconds, check

    def guard(self):
        if self.check is not None:
            try:
                self.check()
            except BaseException as exc:
                raise _CallbackFailure(exc) from exc
        if monotonic() >= self.deadline:
            raise TimeoutError('RUNTIME_BLOCKED: constant Poisson deadline')

    def remaining(self):
        self.guard()
        seconds = self.deadline - monotonic()
        if seconds <= 0:
            raise TimeoutError('RUNTIME_BLOCKED: constant Poisson deadline')
        return min(30, seconds)


def _run(seconds, check, work):
    budget = _Budget(seconds, check)
    try:
        budget.guard()
        result = work(budget)
        budget.guard()
        return result
    except _CallbackFailure as exc:
        raise exc.original
    except (feasibility.CountCapacityBlocked, selection_gate.ResearchInputCapacity, ForecastCapacityError) as exc:
        raise PoissonCapacityBlocked('CAPACITY_BLOCKED: ' + str(exc)) from exc


def _cap(value, maximum, label):
    if value > maximum:
        raise PoissonCapacityBlocked('CAPACITY_BLOCKED: ' + label)


def _encoded(value, guard):
    total = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        guard()
        raw = chunk.encode('utf-8')
        total += len(raw)
        _cap(total, MAX_JSON_BYTES, 'combined JSON bytes')
        yield raw
    guard()


def _digest(value, guard):
    hashed = hashlib.sha256()
    for raw in _encoded(value, guard):
        hashed.update(raw)
    guard()
    return hashed.hexdigest()


def _owned(value, guard):
    pending, nodes = [(value, 0)], 0
    while pending:
        guard()
        item, depth = pending.pop()
        nodes += 1
        _cap(depth, 12, 'JSON depth')
        _cap(nodes, MAX_JSON_NODES, 'JSON nodes')
        kind = type(item)
        if kind in (dict, list):
            _cap(nodes + len(pending) + len(item), MAX_JSON_NODES, 'JSON width')
            if kind is dict:
                for key in item:
                    guard()
                    if type(key) is not str or len(key) > 512:
                        raise ValueError('Bounded string JSON keys required')
            for child in item.values() if kind is dict else item:
                guard()
                pending.append((child, depth + 1))
        elif kind is str:
            _cap(len(item), 4096, 'JSON string')
        elif kind is int:
            _cap(item.bit_length(), 16_384, 'JSON integer')
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError('Nonfinite JSON input')
        elif kind not in (bool, type(None)):
            raise ValueError('JSON-only constant Poisson inputs required')
    raw = bytearray()
    for chunk in _encoded(value, guard):
        raw.extend(chunk)
    guard()
    result = json.loads(raw)
    guard()
    return result


def _pre_fit(selected, count, effort, guard):
    if type(selected) is dict:
        _cap(sum(len(selected[k]) for k in ('accepted', 'rejected') if type(selected.get(k)) is list),
             MAX_ROWS, 'selected rows')
    nodes = edges = events = individuals = 0
    for value in (count, effort):
        guard()
        if type(value) is not dict:
            continue
        if type(value.get('source_nodes')) is list:
            nodes += len(value['source_nodes'])
            _cap(nodes, MAX_SOURCE_NODES, 'combined source nodes')
            for node in value['source_nodes']:
                guard()
                if type(node) is dict and type(node.get('parents')) is list:
                    edges += len(node['parents'])
                    _cap(edges, MAX_SOURCE_EDGES, 'combined source edges')
        if type(value.get('rows')) is list:
            _cap(len(value['rows']), MAX_ROWS, 'projection rows')
            for row in value['rows']:
                guard()
                if type(row) is dict and type(row.get('events')) is list:
                    events += len(row['events'])
                    _cap(events, MAX_EVENTS, 'capture events')
                    for event in row['events']:
                        guard()
                        if type(event) is dict and type(event.get('individual_ids')) is list:
                            individuals += len(event['individual_ids'])
                            _cap(individuals, MAX_INDIVIDUALS, 'individual IDs')


def _flags():
    return dict(source_authenticity='NOT_ATTESTED', source_authentication='CALLER_DEPENDENCY_REQUIRED',
                statistical_adequacy='NOT_ASSESSED', fit_authorized=False,
                scientific_execution_authorized=False, official_issuance_authorized=False,
                confirmation_authorized=False, selection_authorized=False, production_authorized=False)


def _recipe():
    return dict(schema_version='habu-constant-poisson-recipe-v1', family='POISSON', target=TARGET,
                count_units='individuals', exposure_units='active_search_seconds',
                estimator='SUM_COUNT_OVER_FSUM_SECONDS', row_order='ROW_ID_ASCENDING',
                zero_count_rule='EXACT_ZERO_RATE_BOUNDARY')


def _numeric(value):
    if not math.isfinite(value):
        raise ValueError('NUMERIC_BLOCKED: nonfinite arithmetic')
    return value


def _statistics(units, guard):
    total, seconds, nights = 0, [], set()
    for row in units:
        guard()
        total += row['count']
        _cap(total, MAX_INDIVIDUALS, 'cohort individual count')
        seconds.append(row['active_search_seconds'])
        nights.add(row['night'])
    guard()
    try:
        exposure = _numeric(math.fsum(seconds))
        rate = _numeric(total / exposure) if total else 0.0
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError('NUMERIC_BLOCKED: exposure/rate representation') from exc
    guard()
    return dict(rows=len(units), nights=len(nights), total_individuals=total,
                total_active_search_seconds=exposure), dict(lambda_per_active_search_second=rate)


def _mean(rate, seconds, guard):
    guard()
    try:
        value = _numeric(rate * seconds)
    except OverflowError as exc:
        raise ValueError('NUMERIC_BLOCKED: conditional mean overflow') from exc
    if rate > 0 and seconds > 0 and value == 0:
        raise ValueError('NUMERIC_BLOCKED: positive conditional mean underflow')
    guard()
    return value


def _log_mass(mean, count, guard):
    guard()
    if mean == 0:
        return 0.0 if count == 0 else None
    try:
        value = _numeric(count * math.log(mean) - mean - math.lgamma(count + 1))
    except OverflowError as exc:
        raise ValueError('NUMERIC_BLOCKED: conditional log mass overflow') from exc
    if value > 0:
        raise ValueError('NUMERIC_BLOCKED: conditional log mass exceeds zero')
    guard()
    return value


def _same(actual, expected, guard):
    if _digest(actual, guard) != _digest(expected, guard):
        raise ValueError('Exact canonical typed model statistic/parameter required')


def _checked(model, guard):
    fields = {'schema_version', 'phase', 'target', 'recipe', 'recipe_sha256', 'fit_cutoff', 'heldout_night',
              'owner_id', 'observer_id', 'method_version', 'input_digests', 'lineage', 'training_units',
              'cohort_sha256', 'sufficient_statistics', 'parameters', 'model_sha256'} | set(_flags())
    feasibility._fields(model, fields)
    if model['schema_version'] != MODEL_VERSION or model['phase'] != 'DEVELOPMENT' or model['target'] != TARGET:
        raise ValueError('Fixed development count model required')
    for key, expected in _flags().items():
        if type(model[key]) is not type(expected) or model[key] != expected:
            raise ValueError('Count diagnostic cannot grant authority or authentication')
    _same(model['recipe'], _recipe(), guard)
    if feasibility._hash(model['recipe_sha256']) != _digest(_recipe(), guard):
        raise ValueError('Fixed recipe digest mismatch')
    for key in ('owner_id', 'observer_id', 'method_version'):
        feasibility._text(model[key])
    for key, fields in (('input_digests', INPUT_FIELDS), ('lineage', LINEAGE_FIELDS)):
        feasibility._fields(model[key], fields)
        for value in model[key].values():
            guard()
            feasibility._hash(value)
    heldout = selection_gate._night(model['heldout_night'])
    cutoff = feasibility._time(model['fit_cutoff'])
    if cutoff >= feasibility._time(heldout + 'T07:00:00+09:00'):
        raise ValueError('Fit must strictly precede heldout-night07:00')
    units = model['training_units']
    if type(units) is not list or not units:
        raise ValueError('Nonempty complete training unit table required')
    _cap(len(units), MAX_ROWS, 'model rows')
    previous, identities, physical = None, set(), set()
    for row in units:
        guard()
        feasibility._fields(row, UNIT_FIELDS)
        identifier = selection_gate._text(row['row_id'], 'row identity')
        night = selection_gate._night(row['night'])
        try:
            window = selection_gate._window(row['window_start_jst'], night)
        except OverflowError as exc:
            raise ValueError('Model window outside supported time range') from exc
        cx, cy = selection_gate._cell(row['cell_x']), selection_gate._cell(row['cell_y'])
        key = cx, cy, window.astimezone(timezone.utc)
        if (identifier in identities or key in physical or previous is not None and identifier <= previous or
                night >= heldout or window >= cutoff):
            raise ValueError('Unique ordered earlier TRAIN unit identities required')
        if type(row['count']) is not int or not 0 <= row['count'] <= MAX_INDIVIDUALS:
            raise ValueError('Exact bounded nonboolean individual count required')
        if (type(row['active_search_seconds']) is not float or
                not math.isfinite(row['active_search_seconds']) or not 0 < row['active_search_seconds'] <= 600):
            raise ValueError('Positive bounded finite float exposure required')
        identities.add(identifier)
        physical.add(key)
        previous = identifier
    stats, parameters = _statistics(units, guard)
    _same(model['sufficient_statistics'], stats, guard)
    _same(model['parameters'], parameters, guard)
    cohort = {key: model[key] for key in COHORT_FIELDS}
    if feasibility._hash(model['cohort_sha256']) != _digest(cohort, guard):
        raise ValueError('Model cohort digest mismatch')
    guard()
    if feasibility._hash(model['model_sha256']) != _digest({k: v for k, v in model.items() if k != 'model_sha256'}, guard):
        raise ValueError('Model content digest mismatch')
    guard()
    return model


def _pre_model(model):
    if type(model) is dict and type(model.get('training_units')) is list:
        _cap(len(model['training_units']), MAX_ROWS, 'model rows')


def _validated(model, budget):
    _pre_model(model)
    return _checked(_owned(model, budget.guard), budget.guard)


def validate_constant_poisson_model(model, *, budget_seconds=30, check=None):
    """Return a detached integrity-checked JSON declaration, never source proof."""
    return _run(budget_seconds, check, lambda budget: _validated(model, budget))


def _finish(result, guard):
    guard()
    result['receipt_sha256'] = _digest(result, guard)
    # The self-hash is part of the returned JSON and consumes the same cap.
    for _ in _encoded(result, guard):
        pass
    guard()
    return result


def _fit(selection, count, effort, budget):
    guard = budget.guard
    _pre_fit(selection, count, effort, guard)
    selected, count, effort = _owned([selection, count, effort], guard)
    assessment = feasibility.assess_count_feasibility(selected, count, effort,
        budget_seconds=budget.remaining(), check=guard)
    guard()
    inputs = {key: None if value is None else _digest(value, guard)
              for key, value in zip(('selection', 'count_projection', 'effort_projection'), (selected, count, effort))}
    recipe = _recipe()
    result = dict(schema_version=FIT_VERSION, status='NEED_MORE_DATA', phase='DEVELOPMENT', target=TARGET,
                  recipe_sha256=_digest(recipe, guard), feasibility=assessment, model=None,
                  input_digests=inputs, training_log_likelihood=None, **_flags())
    if assessment['status'] == 'NEED_MORE_DATA':
        return _finish(result, guard)
    by_count, by_effort = {}, {}
    for projection, index in ((count, by_count), (effort, by_effort)):
        for row in projection['rows']:
            guard()
            index[row['row_id']] = row
    guard()
    ordered = sorted(selected['accepted'], key=lambda row: row['row_id'])
    guard()
    units = []
    for row in ordered:
        guard()
        unit = {key: row[key] for key in feasibility.UNIT}
        unit.update(count=by_count[row['row_id']]['count'],
                    active_search_seconds=float(by_effort[row['row_id']]['active_search_seconds']))
        units.append(unit)
    statistics, parameters = _statistics(units, guard)
    model = dict(schema_version=MODEL_VERSION, phase='DEVELOPMENT', target=TARGET, recipe=recipe,
        recipe_sha256=result['recipe_sha256'], fit_cutoff=selected['fit_cutoff'], heldout_night=selected['heldout_night'],
        **{key: count[key] for key in ('owner_id', 'observer_id', 'method_version')},
        input_digests=inputs, lineage=dict(selection_sha256=assessment['selection_sha256'],
            corpus_sha256=assessment['corpus_sha256'], count_projection_sha256=assessment['count_projection_sha256'],
            effort_projection_sha256=assessment['effort_projection_sha256'], feasibility_assessment_sha256=assessment['assessment_sha256']),
        training_units=units, sufficient_statistics=statistics, parameters=parameters, **_flags())
    model['cohort_sha256'] = _digest({key: model[key] for key in COHORT_FIELDS}, guard)
    guard()
    model['model_sha256'] = _digest(model, guard)
    guard()
    model = validate_constant_poisson_model(model, budget_seconds=budget.remaining(), check=guard)
    terms = []
    for row in model['training_units']:
        guard()
        mean = _mean(parameters['lambda_per_active_search_second'], row['active_search_seconds'], guard)
        term = _log_mass(mean, row['count'], guard)
        if term is None:
            raise ValueError('NUMERIC_BLOCKED: impossible fitted positive count')
        terms.append(term)
    guard()
    try:
        likelihood = _numeric(math.fsum(terms))
    except OverflowError as exc:
        raise ValueError('NUMERIC_BLOCKED: training likelihood overflow') from exc
    guard()
    result.update(status='DECLARED_COHORT_FITTED', model=model, training_log_likelihood=likelihood)
    return _finish(result, guard)


def fit_constant_poisson(selection, count_projection=None, effort_projection=None, *, budget_seconds=30, check=None):
    """Fit the whole internally consistent cohort; all source authority is external."""
    return _run(budget_seconds, check, lambda budget: _fit(selection, count_projection, effort_projection, budget))


def _scenario(model, seconds, count, budget):
    guard = budget.guard
    _pre_model(model)
    model, seconds, count = _owned([model, seconds, count], guard)
    model = validate_constant_poisson_model(model, budget_seconds=budget.remaining(), check=guard)
    if (type(seconds) not in (int, float) or not 0 <= seconds <= MAX_SCENARIO_SECONDS or
            not math.isfinite(seconds)):
        raise ValueError('Finite nonboolean bounded scenario seconds required')
    if count is not None and (type(count) is not int or not 0 <= count <= MAX_INDIVIDUALS):
        raise ValueError('Exact nonnegative bounded scenario count required')
    seconds = float(seconds)
    mean = _mean(model['parameters']['lambda_per_active_search_second'], seconds, guard)
    guard()
    probability_zero = _numeric(math.exp(-mean))
    log_mass, probability, status = None, None, 'NOT_REQUESTED'
    if count is not None:
        log_mass = _log_mass(mean, count, guard)
        if log_mass is None:
            probability, status = 0.0, 'ZERO_MASS'
        else:
            probability, status = _numeric(math.exp(log_mass)), 'FINITE_LOG_MASS'
    guard()
    if not 0 <= probability_zero <= 1 or probability is not None and not 0 <= probability <= 1:
        raise ValueError('NUMERIC_BLOCKED: invalid probability')
    return _finish(dict(schema_version=SCENARIO_VERSION, status='SCENARIO_ONLY', target=TARGET,
        model_sha256=model['model_sha256'], scenario_active_search_seconds=seconds, scenario_count=count,
        conditional_mean=mean, probability_zero=probability_zero, log_probability=log_mass,
        probability=probability, likelihood_status=status, **_flags()), guard)


def evaluate_constant_poisson_scenario(model, active_search_seconds, *, count=None, budget_seconds=30, check=None):
    """Conditional scalar mechanics only; no future rows, source or observed score."""
    return _run(budget_seconds, check, lambda budget: _scenario(model, active_search_seconds, count, budget))
