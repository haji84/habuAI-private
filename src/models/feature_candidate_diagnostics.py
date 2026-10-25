"""Pure, nonselectable descriptive diagnostics on declared development units.

No source/model bytes, labels from sealed cohorts, fitting, recalibration,
candidate registration or promotion are accessed. Hashes bind supplied content;
they do not prove provenance, actual model predictions or pre-reveal freezing.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import re
from time import monotonic

from models.research_selection import validate_selection

VERSION = 'habu-feature-candidate-development-diagnostic-v1'
PROTOCOL_VERSION = 'habu-feature-candidate-development-protocol-v1'
TARGET = 'OWNER_CAPTURE_BINARY_ON_AUDITED_OBSERVED_100M_600S_UNITS'
MAX_JSON_BYTES = 16 * 1024**2
MAX_JSON_NODES = 2_000_000
MAX_ROWS = 20_000
MAX_NIGHTS = 64
MAX_BINS = 20
JST = timezone(timedelta(hours=9))
PROTOCOL_FIELDS = {'schema_version', 'phase', 'target', 'evaluation_selection_sha256',
                   'predictions_sha256', 'bin_edges', 'log_loss_clip', 'folds'}
FOLD_FIELDS = {'night', 'model_sha256', 'training_selection_sha256', 'training_cutoff', 'train_nights'}
PREDICTION_FIELDS = {'row_id', 'night', 'cell_x', 'cell_y', 'window_start_jst',
                     'probability', 'model_sha256', 'training_selection_sha256'}


class DiagnosticCapacityBlocked(ValueError):
    """CAPACITY_BLOCKED: no truncated or partial diagnostic is returned."""


def _cap(value, limit, label):
    if value > limit:
        raise DiagnosticCapacityBlocked('CAPACITY_BLOCKED: ' + label)


def _fields(value, fields):
    if type(value) is not dict or set(value) != fields:
        raise ValueError('Exact development diagnostic fields required')


def _hash(value):
    if type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ValueError('Explicit SHA-256 required')
    return value


def _number(value):
    if type(value) not in (int, float):
        raise ValueError('Finite nonboolean diagnostic number required')
    try:
        if not math.isfinite(value):
            raise ValueError('Finite diagnostic number required')
        return float(value)
    except OverflowError as exc:
        raise ValueError('Diagnostic number exceeds finite range') from exc


def _night(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Canonical operational night required')
    date.fromisoformat(value)
    return value


def _time(value):
    if type(value) is not str or not 1 <= len(value) <= 64:
        raise ValueError('Aware diagnostic timestamp required')
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.utcoffset() is None:
            raise ValueError('Aware diagnostic timestamp required')
        return stamp.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError('Diagnostic timestamp exceeds UTC range') from exc


def _start(night):
    return _time(_night(night) + 'T07:00:00+09:00')


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


def _copy_inputs(values, check):
    # Check complexity and combined encoding before any owned Python snapshot.
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
                        raise ValueError('Bounded string JSON keys required')
            for child in (item.values() if kind is dict else item):
                check()
                pending.append((child, depth + 1))
        elif kind is str:
            _cap(len(item), 4096, 'JSON string')
        elif kind is int:
            _cap(item.bit_length(), 1024, 'JSON integer size')
        elif kind is float:
            _number(item)
        elif kind not in (bool, type(None)):
            raise ValueError('JSON-only diagnostic inputs required')
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


def _folds(value, nights, evaluation_sha, check):
    if type(value) is not list:
        raise ValueError('Explicit development fold declarations required')
    _cap(len(value), MAX_NIGHTS, 'evaluation nights')
    result, models = {}, {}
    for fold in value:
        check()
        _fields(fold, FOLD_FIELDS)
        night = _night(fold['night'])
        if night in result:
            raise ValueError('Duplicate development fold')
        model = _hash(fold['model_sha256'])
        selection = _hash(fold['training_selection_sha256'])
        if selection == evaluation_sha:
            raise ValueError('Evaluation selection cannot also declare the training selection')
        cutoff = _time(fold['training_cutoff'])
        training = fold['train_nights']
        if type(training) is not list or not training:
            raise ValueError('Nonempty declared training nights required')
        _cap(len(training), MAX_NIGHTS, 'declared training nights')
        for earlier in training:
            check()
            if not _start(earlier) < cutoff < _start(night):
                raise ValueError('Training night start < training cutoff < evaluation night start required')
        if training != sorted(set(training)):
            raise ValueError('Training nights must be sorted and unique')
        identity = (selection, cutoff, tuple(training))
        if model in models and models[model] != identity:
            raise ValueError('Same model hash has conflicting training declarations')
        models[model] = identity
        result[night] = fold
    if list(result) != sorted(nights):
        raise ValueError('Exactly one sorted fold per observed development night required')
    return result


def _metrics(pairs, check):
    brier, log_loss = [], []
    positives = 0
    for probability, label, clipped in pairs:
        check()
        brier.append((probability-label)**2)
        log_loss.append(-math.log(clipped) if label else -math.log1p(-clipped))
        positives += label
    count = len(pairs)
    check()
    return dict(observed_units=count, positives=positives,
        brier=math.fsum(brier)/count if count else None,
        log_loss=math.fsum(log_loss)/count if count else None)


def describe_feature_candidate_development(protocol, observed_selection, predictions, *,
        expected_protocol_sha256, budget_seconds=30, check=None):
    """Describe the entire supplied, content-bound development observed cohort.

    Shared selector validation is bounded but has no callback parameter: checks
    bracket that call. This is cooperative cancellation, not hard preemption.
    Caller owns authentic source/model/training bindings, row readiness and the
    pre-reveal protocol/freeze history; none is authenticated by this pure API.
    """
    if type(budget_seconds) not in (int, float) or not 0 < budget_seconds <= 300 or not math.isfinite(budget_seconds):
        raise ValueError('Diagnostic budget must be finite, positive and at most 300 seconds')
    if check is not None and not callable(check):
        raise ValueError('Parent check must be callable')
    parent_check, deadline = check, monotonic() + budget_seconds

    def guard():
        if parent_check is not None:
            parent_check()
        if monotonic() >= deadline:
            raise TimeoutError('RUNTIME_BLOCKED: development diagnostic deadline expired')

    guard()
    expected = _hash(expected_protocol_sha256)
    if type(predictions) is not list:
        raise ValueError('Explicit predictions list required')
    _cap(len(predictions), MAX_ROWS, 'predictions')
    if type(observed_selection) is dict and type(observed_selection.get('accepted')) is list:
        _cap(len(observed_selection['accepted']), MAX_ROWS, 'observed units')
    plan, selected_input, rows = _copy_inputs([protocol, observed_selection, predictions], guard)
    _fields(plan, PROTOCOL_FIELDS)
    if (plan['schema_version'] != PROTOCOL_VERSION or plan['phase'] != 'DEVELOPMENT' or plan['target'] != TARGET):
        raise ValueError('Only the declared development binary observed-unit target is supported')
    if _digest(plan, guard) != expected:
        raise ValueError('Development protocol content digest mismatch')
    selected = validate_selection(selected_input)
    guard()
    if _hash(plan['evaluation_selection_sha256']) != selected['selection_sha256']:
        raise ValueError('Observed evaluation selection digest mismatch')
    if _hash(plan['predictions_sha256']) != _digest(rows, guard):
        raise ValueError('Development prediction content digest mismatch')
    edges = plan['bin_edges']
    if type(edges) is not list or len(edges) < 2:
        raise ValueError('At least two fixed bin endpoints required')
    _cap(len(edges)-1, MAX_BINS, 'reliability bins')
    for index, edge in enumerate(edges):
        guard()
        number = _number(edge)
        if not 0 <= number <= 1 or (index and not edges[index-1] < number):
            raise ValueError('Strictly increasing reliability endpoints in [0,1] required')
    if edges[0] != 0 or edges[-1] != 1:
        raise ValueError('Reliability endpoints must be exactly 0 and 1')
    epsilon = _number(plan['log_loss_clip'])
    if not 1e-15 <= epsilon < .5:
        raise ValueError('Fixed log-loss clipping must be in [1e-15, 0.5)')
    nights = {row['night'] for row in selected['accepted']}
    _cap(len(nights), MAX_NIGHTS, 'evaluation nights')
    folds = _folds(plan['folds'], nights, selected['selection_sha256'], guard)
    accepted = {row['row_id']: row for row in selected['accepted']}
    predicted = {}
    for row in rows:
        guard()
        _fields(row, PREDICTION_FIELDS)
        row_id = row['row_id']
        if type(row_id) is not str or row_id not in accepted or row_id in predicted:
            raise ValueError('Predictions must bind each selected observed row exactly once')
        observed = accepted[row_id]
        if (row['night'] != observed['night'] or type(row['cell_x']) is not int or
                type(row['cell_y']) is not int or row['cell_x'] != observed['cell_x'] or
                row['cell_y'] != observed['cell_y'] or
                _time(row['window_start_jst']) != _time(observed['window_start_jst'])):
            raise ValueError('Prediction physical 100m x 600s unit differs from selected observation')
        fold = folds[row['night']]
        if (_hash(row['model_sha256']) != fold['model_sha256'] or
                _hash(row['training_selection_sha256']) != fold['training_selection_sha256']):
            raise ValueError('Prediction model/training identity differs from declared fold')
        probability = _number(row['probability'])
        if not 0 <= probability <= 1:
            raise ValueError('Diagnostic probability must be in [0,1]')
        predicted[row_id] = probability
    if set(predicted) != set(accepted):
        raise ValueError('Every selected observation must have a prediction; no subset scoring')
    per_night_pairs = {night: [] for night in sorted(nights)}
    bins = [[] for _ in range(len(edges)-1)]
    all_pairs = []
    for row in selected['accepted']:
        guard()
        probability, label = predicted[row['row_id']], row['label']
        pair = probability, label, min(1-epsilon, max(epsilon, probability))
        per_night_pairs[row['night']].append(pair)
        all_pairs.append(pair)
        bins[min(len(bins)-1, bisect_right(edges, probability)-1)].append((probability, label))
    per_night = []
    for night, pairs in per_night_pairs.items():
        guard()
        per_night.append(dict(night=night, **_metrics(pairs, guard)))
    reliability = []
    for index, pairs in enumerate(bins):
        guard()
        probabilities, labels = [], []
        for probability, label in pairs:
            guard()
            probabilities.append(probability)
            labels.append(label)
        count = len(pairs)
        reliability.append(dict(lower=edges[index], upper=edges[index+1],
            upper_inclusive=index == len(bins)-1, count=count,
            mean_probability=math.fsum(probabilities)/count if count else None,
            observed_fraction=math.fsum(labels)/count if count else None))
    pooled = _metrics(all_pairs, guard)
    result = dict(schema_version=VERSION,
        status='DESCRIPTIVE_DEVELOPMENT_DIAGNOSTIC_ONLY' if all_pairs else 'NEED_MORE_DATA',
        target=TARGET, protocol_sha256=expected, predictions_sha256=plan['predictions_sha256'],
        evaluation_selection_sha256=selected['selection_sha256'],
        evaluation_selection_status=selected['status'], evaluation_selection_blockers=selected['blockers'],
        observed_units=len(all_pairs), evaluation_nights=len(nights), per_night=per_night,
        mean_night_brier=math.fsum(row['brier'] for row in per_night)/len(per_night) if per_night else None,
        mean_night_log_loss=math.fsum(row['log_loss'] for row in per_night)/len(per_night) if per_night else None,
        pooled_unit_brier=pooled['brier'], pooled_unit_log_loss=pooled['log_loss'],
        pooled_reliability_bins=reliability, log_loss_clip=epsilon,
        calibration_status='NOT_VALIDATED', statistical_adequacy='NOT_ASSESSED',
        source_authentication='CALLER_DEPENDENCY_REQUIRED', source_authenticity='NOT_ATTESTED',
        preregistration='CALLER_DEPENDENCY_REQUIRED', model_training_binding='CALLER_ASSERTED_NOT_ATTESTED',
        fit_authorized=False, scientific_execution_authorized=False, selection_authorized=False,
        promotion_authorized=False, official_issuance_authorized=False, production_authorized=False,
        implementation_blockers=['TRAIN_ONLY_ABLATION_PARENT_DISPATCH_NOT_IMPLEMENTED',
            'SOURCE_BOUND_CALIBRATION_PARENT_DISPATCH_NOT_IMPLEMENTED'],
        limitations=['DEVELOPMENT_ONLY_NOT_CONFIRMATION_OR_CALIBRATION_CERTIFICATION',
            'NO_PRE_REVEAL_FREEZE_OR_SOURCE_AUTHENTICATION',
            'DECLARED_MODEL_TRAINING_HASHES_AND_NIGHTS_NOT_REATTESTED',
            'TRAIN_ROW_READINESS_AND_PARTIAL_NIGHT_QUALIFICATION_REQUIRE_CALLER',
            'SELECTOR_BINARY_READINESS_IS_NOT_CALIBRATION_ADEQUACY',
            'POOLED_BIN_COUNTS_ARE_NOT_EQUAL_NIGHT_WEIGHTED_METRICS',
            'OBSERVATION_SELECTION_BIAS_AND_DEPENDENT_UNITS_NOT_CORRECTED',
            'NO_SELECTION_RESELECTION_FIT_RECALIBRATION_OR_PROMOTION'])
    result['diagnostic_sha256'] = _digest(result, guard)
    guard()
    return result
