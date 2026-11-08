"""Standalone HB-A1 software fits and nonselectable development ablations.

Reuses the existing fixed logistic numeric core; no new optimizer, real-source
authentication, trusted freeze, confirmation reader or parent dispatch exists.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import re
from time import monotonic

import prospective_candidate_model as learner
from models.research_selection import validate_selection, validate_future_rows, area_id, _sources

TARGET = 'OWNER_CAPTURE_BINARY_GIVEN_QUALIFIED_OBSERVED_100M_10MIN_UNIT'
NUMERIC_RECIPE = 'LEGACY_L2_320_LR_0_15_L2_0_04_UNPENALIZED_INTERCEPT'
RECIPE_VERSION = 'habu-hba1-fixed-logistic-recipe-v1'
MODEL_VERSION = 'habu-hba1-research-model-v1'
FIT_VERSION = 'habu-hba1-standalone-fit-v1'
PREDICTION_VERSION = 'habu-hba1-unit-prediction-v1'
PROTOCOL_VERSION = 'habu-hba1-retrained-ablation-protocol-v1'
ABLATION_VERSION = 'habu-hba1-retrained-ablation-diagnostic-v1'
MAX_JSON_BYTES = 16 * 1024**2
MAX_JSON_NODES = 2_000_000
MAX_TRAIN_ROWS = 20_000
MAX_FORECAST_ROWS = 120_000
MAX_OBSERVED_ROWS = 20_000
MAX_FOLDS = 8
MAX_GROUPS = 4
MAX_EVENT_MEMBERSHIPS = 100_000
FEATURES = learner.FEATURES
RECIPE_FIELDS = {'schema_version', 'target', 'numeric_recipe', 'feature_mask', 'implementation_sha256'}
CODE_PATHS = {'src/prospective_candidate_model.py', 'src/models/hba1_feature_candidate.py'}
PROTOCOL_FIELDS = {'schema_version', 'phase', 'target', 'base_recipe', 'groups', 'folds'}
DECLARATION_FIELDS = {'night', 'training_selection_sha256', 'joined_forecast_sha256',
                      'cutoff_time', 'evaluation_selection_sha256'}
FOLD_FIELDS = {'night', 'training_selection', 'forecast_rows', 'evaluation_selection'}
FLAG_FIELDS = {'source_authentication', 'source_authenticity', 'scientific_status', 'fit_authorized',
               'selection_authorized', 'promotion_authorized', 'scientific_execution_authorized',
               'official_issuance_authorized', 'production_activation_authorized'}
MODEL_FIELDS = FLAG_FIELDS | {'schema_version', 'status', 'candidate_id', 'target_semantics', 'recipe',
    'recipe_sha256', 'feature_names', 'means', 'scales', 'coefficients', 'training_selection_sha256',
    'corpus_sha256', 'source_sha256', 'source_received_at', 'fit_cutoff', 'heldout_night',
    'training_nights', 'training_window_start_max', 'counts', 'training_row_ids_sha256', 'training_rows_sha256',
    'raw_feature_rows_sha256', 'model_sha256'}


class HBA1CapacityBlocked(ValueError):
    """CAPACITY_BLOCKED: return no truncated/partially successful calculation."""


def _flags():
    return dict(source_authentication='CALLER_DEPENDENCY_REQUIRED', source_authenticity='NOT_ATTESTED',
        scientific_status='NOT_VALIDATED', fit_authorized=False, selection_authorized=False,
        promotion_authorized=False, scientific_execution_authorized=False,
        official_issuance_authorized=False, production_activation_authorized=False)


def _cap(value, maximum, label):
    if value > maximum:
        raise HBA1CapacityBlocked('CAPACITY_BLOCKED: ' + label)


def _fields(value, expected):
    if type(value) is not dict or set(value) != expected:
        raise ValueError('Exact HB-A1 contract fields required')


def _hash(value):
    if type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('Explicit HB-A1 SHA-256 required')
    return value


def _finite(value):
    try:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Finite nonboolean HB-A1 number required')
        return float(value)
    except OverflowError as exc:
        raise ValueError('HB-A1 number exceeds finite range') from exc


def _time(value):
    if type(value) is not str or not 1 <= len(value) <= 64:
        raise ValueError('Aware HB-A1 timestamp required')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.utcoffset() is None:
            raise ValueError('Aware HB-A1 timestamp required')
        return result.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError('HB-A1 timestamp exceeds UTC range') from exc


def _night(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Canonical HB-A1 night required')
    _time(value + 'T07:00:00+09:00')
    return value


def _budget(seconds, check):
    if type(seconds) not in (int, float) or not 0 < seconds <= 300 or not math.isfinite(seconds):
        raise ValueError('HB-A1 budget must be finite, positive and at most 300 seconds')
    if check is not None and not callable(check):
        raise ValueError('Parent check must be callable')
    deadline = monotonic() + seconds

    def guard():
        if check is not None:
            check()
        if monotonic() >= deadline:
            raise TimeoutError('RUNTIME_BLOCKED: shared HB-A1 deadline expired')
    guard()
    return guard


def _encode(value, check):
    count = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        check()
        raw = chunk.encode('utf-8')
        count += len(raw)
        _cap(count, MAX_JSON_BYTES, 'combined canonical JSON bytes')
        yield raw
    check()


def _own(values, check):
    pending, nodes = [(values, 0)], 0
    while pending:
        check()
        item, depth = pending.pop()
        nodes += 1
        _cap(nodes, MAX_JSON_NODES, 'combined JSON nodes')
        _cap(depth, 12, 'JSON depth')
        kind = type(item)
        if kind in (dict, list):
            _cap(nodes + len(pending) + len(item), MAX_JSON_NODES, 'combined JSON nodes')
            if kind is dict:
                for key in item:
                    check()
                    if type(key) is not str or len(key) > 512:
                        raise ValueError('Bounded string HB-A1 JSON keys required')
            for child in (item.values() if kind is dict else item):
                check()
                pending.append((child, depth+1))
        elif kind is str:
            _cap(len(item), 4096, 'JSON string')
        elif kind is int:
            _cap(item.bit_length(), 1024, 'JSON integer size')
        elif kind is float:
            _finite(item)
        elif kind not in (bool, type(None)):
            raise ValueError('JSON-only HB-A1 contracts required')
    raw = bytearray()
    for chunk in _encode(values, check):
        raw.extend(chunk)
    check()
    owned = json.loads(raw)
    check()
    return owned


def _digest(value, check):
    hashed = hashlib.sha256()
    for raw in _encode(value, check):
        hashed.update(raw)
    check()
    return hashed.hexdigest()


def _seal(value, field, check):
    value[field] = _digest(value, check)
    check()
    return value


def _recipe(value, expected, check):
    _fields(value, RECIPE_FIELDS)
    if (value['schema_version'] != RECIPE_VERSION or value['target'] != TARGET or
            value['numeric_recipe'] != NUMERIC_RECIPE):
        raise ValueError('Only the fixed legacy HB-A1 numerical recipe is supported')
    mask = value['feature_mask']
    if type(mask) is not list or len(mask) != 7 or any(type(flag) is not bool for flag in mask) or not any(mask):
        raise ValueError('Nonempty seven-column boolean feature mask required')
    _fields(value['implementation_sha256'], CODE_PATHS)
    for sha in value['implementation_sha256'].values():
        check()
        _hash(sha)
    if _digest(value, check) != _hash(expected):
        raise ValueError('HB-A1 recipe content digest mismatch')
    return [index for index, included in enumerate(mask) if included]


def _selection(value, check):
    check()
    selected = validate_selection(value)
    check()
    if selected['feature_names'] != sorted(FEATURES):
        raise ValueError('All seven raw HB-A1 features required, including removed features')
    matrix, labels = [], []
    for row in selected['accepted']:
        check()
        try:
            matrix.append(learner._features(row['features']))
        except OverflowError as exc:
            raise ValueError('HB-A1 raw feature exceeds finite range') from exc
        labels.append(row['label'])
    return selected, matrix, labels


def _training(value, check):
    selected, matrix, labels = _selection(value, check)
    _cap(len(matrix), MAX_TRAIN_ROWS, 'training rows')
    reasons = []
    if selected['status'] == 'NEED_MORE_DATA':
        reasons.extend(selected['blockers'])
    if len(matrix) < 20 or selected['counts']['nights'] < 5:
        reasons.append('HB_A1_REQUIRES_20_SELECTED_ROWS_AND_5_PRIOR_TRAIN_NIGHTS')
    return selected, matrix, labels, reasons


def _fit(selected, matrix, labels, recipe, check):
    check()
    try:
        means, scales, coefficients = learner._fit_numeric(matrix, labels,
            feature_mask=recipe['feature_mask'], check=check)
    except OverflowError as exc:
        raise ValueError('HB-A1 numerical fit overflow; no model produced') from exc
    indices = [i for i, included in enumerate(recipe['feature_mask']) if included]
    for vector in (means, scales, coefficients):
        for number in vector:
            check()
            _finite(number)
    if any(scale <= 0 for scale in scales):
        raise ValueError('HB-A1 fitted scales must be positive')
    features, row_ids, windows = [], [], []
    for row in selected['accepted']:
        check()
        row_ids.append(row['row_id'])
        windows.append(_time(row['window_start_jst']))
        features.append(dict(row_id=row['row_id'], features=row['features']))
    model = dict(schema_version=MODEL_VERSION, status='DEVELOPMENT_RESEARCH_FIT_ONLY',
        candidate_id='HB-A1', target_semantics=TARGET, recipe=recipe,
        recipe_sha256=_digest(recipe, check), feature_names=[FEATURES[i] for i in indices],
        means=means, scales=scales, coefficients=coefficients,
        training_selection_sha256=selected['selection_sha256'], corpus_sha256=selected['corpus_sha256'],
        source_sha256=selected['source_sha256'], source_received_at=selected['source_received_at'],
        fit_cutoff=selected['fit_cutoff'], heldout_night=selected['heldout_night'],
        training_nights=sorted({row['night'] for row in selected['accepted']}),
        training_window_start_max=max(windows).isoformat(), counts=selected['counts'],
        training_row_ids_sha256=_digest(row_ids, check), training_rows_sha256=_digest(selected['accepted'], check),
        raw_feature_rows_sha256=_digest(features, check), **_flags())
    return _seal(model, 'model_sha256', check)


def fit_hba1(training_selection, *, recipe, expected_recipe_sha256, budget_seconds=30, check=None):
    """Pure standalone software fit; insufficient selected data return no model."""
    guard = _budget(budget_seconds, check)
    expected = _hash(expected_recipe_sha256)
    selected_input, spec = _own([training_selection, recipe], guard)
    _recipe(spec, expected, guard)
    selected, matrix, labels, reasons = _training(selected_input, guard)
    model = None if reasons else _fit(selected, matrix, labels, spec, guard)
    result = dict(schema_version=FIT_VERSION, status='NEED_MORE_DATA' if reasons else 'DEVELOPMENT_FIT_ONLY',
        model=model, blockers=reasons, training_selection_sha256=selected['selection_sha256'],
        counts=selected['counts'], recipe_sha256=expected, registration_status='STANDALONE_NOT_REGISTERED', **_flags())
    return _seal(result, 'receipt_sha256', guard)


def _model(value, check):
    _fields(value, MODEL_FIELDS)
    if _hash(value['model_sha256']) != _digest({k: v for k, v in value.items() if k != 'model_sha256'}, check):
        raise ValueError('HB-A1 model content digest mismatch')
    if (value['schema_version'] != MODEL_VERSION or value['status'] != 'DEVELOPMENT_RESEARCH_FIT_ONLY' or
            value['candidate_id'] != 'HB-A1' or value['target_semantics'] != TARGET):
        raise ValueError('Standalone HB-A1 research model required')
    for key, expected in _flags().items():
        if (type(expected) is bool and value[key] is not expected) or (type(expected) is str and value[key] != expected):
            raise ValueError('HB-A1 model cannot claim source authentication or authority')
    indices = _recipe(value['recipe'], value['recipe_sha256'], check)
    if value['feature_names'] != [FEATURES[i] for i in indices]:
        raise ValueError('HB-A1 model feature order differs from recipe')
    for field, size in (('means', len(indices)), ('scales', len(indices)), ('coefficients', len(indices)+1)):
        vector = value[field]
        if type(vector) is not list or len(vector) != size:
            raise ValueError('HB-A1 numerical model dimensions differ from recipe')
        for number in vector:
            check()
            _finite(number)
    if any(scale <= 0 for scale in value['scales']):
        raise ValueError('HB-A1 numerical scales must be positive')
    cutoff, night = _time(value['fit_cutoff']), _night(value['heldout_night'])
    if cutoff >= _time(night+'T07:00:00+09:00'):
        raise ValueError('HB-A1 fit cutoff must precede held-out night start')
    training = value['training_nights']
    if type(training) is not list or not 5 <= len(training) <= MAX_TRAIN_ROWS:
        raise ValueError('At least five declared training nights required')
    for earlier in training:
        check()
        if _time(_night(earlier)+'T07:00:00+09:00') >= cutoff or earlier >= night:
            raise ValueError('HB-A1 training nights must precede fit and held-out night')
    if training != sorted(set(training)):
        raise ValueError('HB-A1 training nights must be sorted and unique')
    maximum = _time(value['training_window_start_max'])
    if (maximum >= cutoff or maximum.minute % 10 or maximum.second or maximum.microsecond or
            learner._night(maximum) != training[-1]):
        raise ValueError('HB-A1 actual maximum training window conflicts with cutoff/night/alignment')
    counts = value['counts']
    _fields(counts, {'accepted_rows', 'rejected_rows', 'nights', 'positives', 'negatives'})
    if (any(type(n) is not int for n in counts.values()) or
            not 20 <= counts['accepted_rows'] <= MAX_TRAIN_ROWS or
            not 0 <= counts['rejected_rows'] <= MAX_TRAIN_ROWS-counts['accepted_rows'] or
            counts['nights'] != len(training) or counts['nights'] > counts['accepted_rows'] or
            counts['positives'] < 2 or counts['negatives'] < 2 or
            counts['positives']+counts['negatives'] != counts['accepted_rows']):
        raise ValueError('HB-A1 model training counts conflict')
    for key in ('training_selection_sha256', 'corpus_sha256', 'training_row_ids_sha256',
                'training_rows_sha256', 'raw_feature_rows_sha256'):
        _hash(value[key])
    _sources(value['source_sha256'], value['source_received_at'], cutoff, check=check)
    check()
    return value


def _future(rows, cutoff, joined_sha, night, check):
    check()
    _cap(len(rows) if type(rows) is list else 0, MAX_FORECAST_ROWS, 'forecast rows')
    future = validate_future_rows(rows, cutoff_time=cutoff, universe_sha256=joined_sha,
        heldout_night=night, feature_names=sorted(FEATURES))
    check()
    for row in future:
        check()
        try:
            learner._features(row['features'])
        except OverflowError as exc:
            raise ValueError('HB-A1 future feature exceeds finite range') from exc
    return future


def _score_owned_row(model, row, check):
    """Exact native scalar for an admitted model and owned, checked row."""
    indices = [i for i, included in enumerate(model['recipe']['feature_mask']) if included]
    values = [row['features'][FEATURES[i]] for i in indices]
    terms = []
    for coefficient, value, mu, scale in zip(model['coefficients'][1:], values, model['means'], model['scales']):
        check()
        # Callback exceptions are outside the local arithmetic normalization.
        try:
            normalized = _finite((value-mu)/scale)
            terms.append(_finite(coefficient*normalized))
        except OverflowError as exc:
            raise ValueError('HB-A1 numeric score exceeds finite range') from exc
    check()
    try:
        _finite(model['coefficients'][0] + sum(terms))
        probability = round(_finite(learner._score(values, model['coefficients'], model['means'], model['scales'])), 8)
    except OverflowError as exc:
        raise ValueError('HB-A1 numeric score exceeds finite range') from exc
    if not 0 <= probability <= 1:
        raise ValueError('HB-A1 probability outside [0,1]')
    check()
    return probability


def _predict(model, future, cutoff, joined_sha, check):
    if _time(model['fit_cutoff']) >= _time(cutoff):
        raise ValueError('HB-A1 fit cutoff must strictly precede prediction cutoff')
    units = []
    for row in future:
        check()
        probability = _score_owned_row(model, row, check)
        units.append(dict(row_id=row['row_id'], operational_night=row['operational_night'],
            window_start_jst=row['window_start_jst'], cell_x=row['cell_x'], cell_y=row['cell_y'],
            area_id_1km=area_id(row['cell_x'], row['cell_y']), probability=probability,
            spatial_score=probability, probability_status='NOT_VALIDATED'))
    result = dict(schema_version=PREDICTION_VERSION, candidate_id='HB-A1',
        model_sha256=model['model_sha256'], recipe_sha256=model['recipe_sha256'],
        training_selection_sha256=model['training_selection_sha256'], universe_sha256=joined_sha,
        cutoff_time=cutoff, operational_night=model['heldout_night'], target_semantics=TARGET,
        unit_predictions=units, **_flags())
    return _seal(result, 'prediction_sha256', check)


def predict_hba1(model, forecast_rows, *, cutoff_time, joined_universe_sha256, budget_seconds=30, check=None):
    """Predict every joined future unit, without ranking areas or dispatching."""
    guard = _budget(budget_seconds, check)
    model, rows = _own([model, forecast_rows], guard)
    validated = _model(model, guard)
    future = _future(rows, cutoff_time, joined_universe_sha256, validated['heldout_night'], guard)
    result = _predict(validated, future, cutoff_time, joined_universe_sha256, guard)
    guard()
    return result


def _groups(values, check):
    if type(values) is not list or not values:
        raise ValueError('Nonempty preregistered ablation groups required')
    _cap(len(values), MAX_GROUPS, 'ablation groups')
    identifiers, drops = set(), set()
    for value in values:
        check()
        _fields(value, {'id', 'drop_features'})
        identifier = value['id']
        if (type(identifier) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', identifier) or
                identifier.casefold() in {'full', 'baseline', 'hb-a1', 'uniform', 'selected', 'champion'} or
                identifier.casefold() in identifiers):
            raise ValueError('Distinct nonreserved ablation group ID required')
        features = value['drop_features']
        if (type(features) is not list or not features or len(features) >= 7 or
                any(type(name) is not str or name not in FEATURES for name in features)):
            raise ValueError('Ablation removes a nonempty proper subset of fixed features')
        ordered = tuple(name for name in FEATURES if name in features)
        if list(ordered) != features or ordered in drops:
            raise ValueError('Drop features must follow fixed order without duplicate masks')
        identifiers.add(identifier.casefold())
        drops.add(ordered)
    return values


def _physical(row, night_key='night'):
    return row[night_key], row['cell_x'], row['cell_y'], _time(row['window_start_jst'])


def _preflight(plan, inputs, check):
    _fields(plan, PROTOCOL_FIELDS)
    if plan['schema_version'] != PROTOCOL_VERSION or plan['phase'] != 'DEVELOPMENT' or plan['target'] != TARGET:
        raise ValueError('Development-only HB-A1 ablation protocol required')
    _recipe(plan['base_recipe'], _digest(plan['base_recipe'], check), check)
    if plan['base_recipe']['feature_mask'] != [True]*7:
        raise ValueError('Ablation baseline uses all seven features')
    groups = _groups(plan['groups'], check)
    declarations = plan['folds']
    if type(declarations) is not list or not declarations or type(inputs) is not list or len(inputs) != len(declarations):
        raise ValueError('Every declared outer fold requires one complete input')
    _cap(len(inputs), MAX_FOLDS, 'outer folds')
    prepared, reasons, nights = [], [], []
    totals = dict(training=0, forecast=0, observed=0, events=0)
    evaluation_ids, evaluation_events, event_units, unit_labels = set(), set(), {}, {}

    def register_unit(unit, label):
        check()
        if unit in unit_labels and unit_labels[unit] != label:
            raise ValueError('Known binary label conflicts for the same physical observation across folds')
        if unit not in unit_labels:
            _cap(len(unit_labels)+1, MAX_TRAIN_ROWS+MAX_OBSERVED_ROWS, 'physical unit memberships')
        unit_labels[unit] = label

    def register_event(event, unit):
        check()
        totals['events'] += 1
        _cap(totals['events'], MAX_EVENT_MEMBERSHIPS, 'event memberships')
        if event in event_units and event_units[event] != unit:
            raise ValueError('Canonical event identity moved to another physical observation across folds')
        event_units[event] = unit
    for declaration, payload in zip(declarations, inputs):
        check()
        _fields(declaration, DECLARATION_FIELDS)
        _fields(payload, FOLD_FIELDS)
        night = _night(declaration['night'])
        if payload['night'] != night:
            raise ValueError('Outer fold declaration/input night mismatch')
        nights.append(night)
        train, matrix, labels, missing = _training(payload['training_selection'], check)
        observed, _, _ = _selection(payload['evaluation_selection'], check)
        if (train['selection_sha256'] != _hash(declaration['training_selection_sha256']) or
                observed['selection_sha256'] != _hash(declaration['evaluation_selection_sha256']) or
                train['heldout_night'] != night):
            raise ValueError('Outer fold selection/held-out night binding mismatch')
        future = _future(payload['forecast_rows'], declaration['cutoff_time'],
            _hash(declaration['joined_forecast_sha256']), night, check)
        totals['training'] += len(matrix)
        totals['forecast'] += len(future)
        totals['observed'] += len(observed['accepted'])
        _cap(totals['training'], MAX_TRAIN_ROWS, 'combined training rows')
        _cap(totals['forecast'], MAX_FORECAST_ROWS, 'combined forecast rows')
        _cap(totals['observed'], MAX_OBSERVED_ROWS, 'combined observed rows')
        expected = {row['row_id']: row for row in future}
        train_ids, train_events, train_units = set(), set(), set()
        for row in train['accepted']:
            check()
            unit = _physical(row)
            register_unit(unit, row['label'])
            train_ids.add(row['row_id'])
            train_units.add(unit)
            for event in row['capture_event_ids']:
                register_event(event, unit)
                train_events.add(event)
        mask = []
        for row in observed['accepted']:
            check()
            unit = _physical(row)
            register_unit(unit, row['label'])
            original = expected.get(row['row_id'])
            if (row['night'] != night or original is None or unit != _physical(original, 'operational_night') or
                    row['features'] != original['features'] or row['row_id'] in train_ids or unit in train_units or
                    row['row_id'] in evaluation_ids):
                raise ValueError('Observed mask must match future raw units/features without TRAIN overlap')
            evaluation_ids.add(row['row_id'])
            for event in row['capture_event_ids']:
                register_event(event, unit)
                if event in train_events or event in evaluation_events:
                    raise ValueError('Capture event reused across TRAIN/evaluation or evaluation folds')
                evaluation_events.add(event)
            mask.append({key: row[key] for key in ('row_id', 'night', 'cell_x', 'cell_y', 'window_start_jst', 'label', 'capture_event_ids')})
        if not mask:
            missing.append('NO_KNOWN_OBSERVED_DEVELOPMENT_UNITS')
        reasons.extend(night+': '+reason for reason in missing)
        prepared.append(dict(night=night, selected=train, matrix=matrix, labels=labels,
            future=future, observed=observed, observed_mask_sha256=_digest(mask, check), declaration=declaration))
    if nights != sorted(set(nights)):
        raise ValueError('Outer folds must be unique and sorted')
    check()
    return groups, prepared, reasons


def _evidence(model, prediction, prepared, check):
    probabilities = {row['row_id']: row['probability'] for row in prediction['unit_predictions']}
    errors = []
    for row in prepared['observed']['accepted']:
        check()
        errors.append((probabilities[row['row_id']]-row['label'])**2)
    check()
    return dict(recipe_sha256=model['recipe_sha256'], model_sha256=model['model_sha256'],
        prediction_sha256=prediction['prediction_sha256'], feature_mask=model['recipe']['feature_mask'],
        feature_names=model['feature_names'], means=model['means'], scales=model['scales'], coefficients=model['coefficients'],
        training_selection_sha256=model['training_selection_sha256'], training_row_ids_sha256=model['training_row_ids_sha256'],
        training_rows_sha256=model['training_rows_sha256'], raw_feature_rows_sha256=model['raw_feature_rows_sha256'],
        joined_forecast_sha256=prepared['declaration']['joined_forecast_sha256'],
        observed_mask_sha256=prepared['observed_mask_sha256'], brier=math.fsum(errors)/len(errors))


def describe_retrained_ablations(protocol, folds, *, expected_protocol_sha256, budget_seconds=30, check=None):
    """Fit all declared development ablations, publish only a complete diagnostic.

    Evaluation labels never enter a fit. Global all-fold preflight checks known
    contradictions even if another fold is data-blocked. No model/prediction is
    released before all fits, whole-universe predictions and final seal complete.
    """
    guard = _budget(budget_seconds, check)
    expected = _hash(expected_protocol_sha256)
    plan, inputs = _own([protocol, folds], guard)
    if _digest(plan, guard) != expected:
        raise ValueError('Ablation protocol content digest mismatch')
    groups, prepared, reasons = _preflight(plan, inputs, guard)
    results = []
    if not reasons:
        for fold in prepared:
            guard()
            declaration = fold['declaration']
            baseline = _fit(fold['selected'], fold['matrix'], fold['labels'], plan['base_recipe'], guard)
            predicted = _predict(baseline, fold['future'], declaration['cutoff_time'], declaration['joined_forecast_sha256'], guard)
            full = _evidence(baseline, predicted, fold, guard)
            ablations = []
            for group in groups:
                guard()
                reduced = dict(plan['base_recipe'], feature_mask=[name not in group['drop_features'] for name in FEATURES])
                model = _fit(fold['selected'], fold['matrix'], fold['labels'], reduced, guard)
                prediction = _predict(model, fold['future'], declaration['cutoff_time'], declaration['joined_forecast_sha256'], guard)
                evidence = _evidence(model, prediction, fold, guard)
                evidence.update(group_id=group['id'], drop_features=group['drop_features'],
                    ablated_minus_full_brier=evidence['brier']-full['brier'])
                ablations.append(evidence)
            results.append(dict(night=fold['night'], forecast_units=len(fold['future']), observed_units=len(fold['observed']['accepted']),
                evaluation_selection_sha256=fold['observed']['selection_sha256'],
                evaluation_selection_status=fold['observed']['status'], evaluation_selection_blockers=fold['observed']['blockers'],
                full=full, ablations=ablations))
    paired = []
    if results:
        for index, group in enumerate(groups):
            guard()
            paired.append(dict(group_id=group['id'], paired_nights=len(results),
                mean_full_brier=math.fsum(fold['full']['brier'] for fold in results)/len(results),
                mean_ablated_brier=math.fsum(fold['ablations'][index]['brier'] for fold in results)/len(results),
                mean_ablated_minus_full_brier=math.fsum(fold['ablations'][index]['ablated_minus_full_brier'] for fold in results)/len(results)))
    result = dict(schema_version=ABLATION_VERSION,
        status='NEED_MORE_DATA' if reasons else 'DESCRIPTIVE_RETRAINED_ABLATION_ONLY',
        protocol_sha256=expected, target_semantics=TARGET, blockers=reasons, fold_results=results, paired_summary=paired,
        statistical_adequacy='NOT_ASSESSED', confirmation_status='NOT_PERFORMED',
        registration_status='DIAGNOSTIC_NOT_A_CANDIDATE',
        limitations=['DECLARED_CODE_MODEL_SOURCE_HASHES_NOT_AUTHENTICATED',
            'TRAIN_ROW_READINESS_AND_PARTIAL_NIGHT_QUALIFICATION_REQUIRE_CALLER',
            'NO_PRE_REVEAL_FREEZE_OR_CONFIRMATION_AUTHENTICATION',
            'BINARY_OBSERVED_MASK_NOT_FULL_CAPTURE_LEDGER_STAGE1_DENOMINATOR',
            'NO_SELECTION_RESELECTION_RECALIBRATION_OR_PROMOTION',
            'POSITIVE_ABLATED_MINUS_FULL_BRIER_FAVORS_FULL_MODEL'], **_flags())
    return _seal(result, 'ablation_sha256', guard)
