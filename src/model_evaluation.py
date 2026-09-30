"""Bounded, diagnostic learning evaluation on explicit audited snapshots.

These registered baselines emit spatial scores (and probabilities where defined),
not operational 100m +/-10 minute targets. Nothing here grants production authority.
"""
from __future__ import annotations

import json
import math
import os
import random
import tempfile
import time
from collections import defaultdict
from datetime import datetime, time as day_time, timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

from master_contracts import canonical_bytes, digest, file_hash, safe_path, stage, validate_night
from pdca_pipeline import utm52n

JST = ZoneInfo('Asia/Tokyo')
VERSION = 'bounded-spatial-baselines-v1'
NAMES = ('model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation')
FAMILIES = ('uniform', 'historical_capture_prior', 'observed_unit_prevalence', 'duration_normalized_area_rate')
INPUT_NAMESPACES = {'data', 'features', 'evidence', 'model_specs', 'protocols', 'policies', 'models'}
IMPLEMENTATION_BLOCKERS = [
    'IMPLEMENTATION_BLOCKED: formal 100m +/-10min time-target model adapter',
    'IMPLEMENTATION_BLOCKED: feature-aware retraining ablation and adjusted/interactions research',
    'IMPLEMENTATION_BLOCKED: independent confirmation selection/consumption lock and trusted runner',
    'IMPLEMENTATION_BLOCKED: count/activity/detection/route/rerouting model executors',
]


class MissingEvidence(ValueError):
    pass


class BudgetExhausted(ValueError):
    pass


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError('availability timestamp must be an ISO string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('availability timestamp requires timezone')
    return result


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Nonfinite or nonnumeric value')
    return float(value)


def _coordinates(row):
    if 'utm_x_m' in row and 'utm_y_m' in row:
        x, y = _finite(row['utm_x_m']), _finite(row['utm_y_m'])
        if not (100000 <= x <= 900000 and 0 <= y <= 10000000):
            raise ValueError('Invalid EPSG:32652 coordinates')
        return x, y
    lat, lon = _finite(row['latitude']), _finite(row['longitude'])
    if not (0 <= lat <= 84 and 126 <= lon <= 132):
        raise ValueError('Coordinates outside UTM52N domain')
    return utm52n(lat, lon)


def _area(row, size=1000):
    x, y = _coordinates(row)
    return f'{math.floor(x/size)},{math.floor(y/size)}'


def _read(root, relative, consumed, expected=None):
    if not isinstance(relative, str) or not Path(relative).parts or Path(relative).parts[0] not in INPUT_NAMESPACES:
        raise ValueError('Unsupported external input reference')
    path = safe_path(root, relative)
    if not path.is_file():
        raise MissingEvidence(f'Missing referenced artifact: {relative}')
    actual = file_hash(path)
    if expected is not None and actual != expected:
        raise ValueError(f'Input hash mismatch: {relative}')
    consumed[relative] = actual
    value = json.loads(path.read_text(encoding='utf-8'))
    canonical_bytes(value)
    return value


def _reference(root, reference, consumed):
    if not isinstance(reference, dict):
        raise ValueError('Artifact reference must be an object')
    available = _timestamp(reference['available_at'])
    expected = reference['sha256']
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError('Invalid reference hash')
    return _read(root, reference['path'], consumed, expected), available


def _validate(root, requested_night, consumed, check):
    snapshot = _read(root, 'data/processed/model_learning.json', consumed)
    if not isinstance(snapshot, dict):
        raise ValueError('LearningSnapshot root must be an object')
    if snapshot.get('upstream_status') == 'FAIL':
        raise ValueError('Upstream evidence audit failed')
    if snapshot['schema_version'] != '1.0':
        raise ValueError('Unsupported learning schema')
    universe, universe_available = _reference(root, snapshot['universe'], consumed)
    protocol, protocol_available = _reference(root, snapshot['protocol'], consumed)
    if not isinstance(universe, dict) or not isinstance(protocol, dict):
        raise ValueError('ForecastUniverse and protocol roots must be objects')
    if snapshot['candidate_universe_sha256'] != snapshot['universe']['sha256']:
        raise ValueError('Universe hash does not match learning snapshot')
    if universe['schema_version'] != '1.0' or universe['source_type'] != 'EX_ANTE_FORECAST':
        raise ValueError('Universe must be explicit ex-ante forecast input, never held-out GPX')
    if not isinstance(universe['geographic_domain'], dict) or not universe['geographic_domain']:
        raise MissingEvidence('Forecast universe geographic domain required')
    if protocol['schema_version'] != '1.0':
        raise ValueError('Unsupported protocol schema')
    research = protocol['research_used_nights']
    confirmation = protocol['confirmation_used_nights']
    if not isinstance(research, list) or not isinstance(confirmation, list):
        raise ValueError('Protocol split lists required')
    for night in research + confirmation:
        validate_night(night)
    if len(set(research)) != len(research) or len(set(confirmation)) != len(confirmation) or set(research) & set(confirmation):
        raise ValueError('Research/confirmation nights must be unique and disjoint')
    families = protocol['registered_candidates']
    if (not isinstance(families, list) or not 1 <= len(families) <= 3 or len(set(families)) != len(families)
            or families[0] != 'uniform' or any(f not in FAMILIES for f in families)):
        raise ValueError('At most three preregistered bounded candidates, uniform baseline first')
    if 'duration_normalized_area_rate' in families:
        if _finite(protocol['effort_reference_seconds']) <= 0:
            raise ValueError('Positive ex-ante reference effort required')
    frozen_at = _timestamp(protocol['frozen_at'])
    sources = {}
    if not isinstance(snapshot['source_manifest'], list):
        raise ValueError('Source manifest must be an array')
    for source in snapshot['source_manifest']:
        check()
        if not isinstance(source, dict):
            raise ValueError('Source manifest entries must be objects')
        if 'role' not in source:
            raise MissingEvidence('Source provenance role is required')
        if source['role'] not in ('label', 'feature', 'universe', 'protocol'):
            raise ValueError('Unrecognized source provenance role')
        relative = source['path']
        if relative in sources:
            raise ValueError('Duplicate source manifest path')
        # Provenance sources may be non-JSON, so hash their raw bytes directly.
        if not Path(relative).parts or Path(relative).parts[0] not in INPUT_NAMESPACES:
            raise ValueError('Unsupported source namespace')
        path = safe_path(root, relative)
        if not path.is_file():
            raise MissingEvidence(f'Missing provenance source: {relative}')
        actual = file_hash(path)
        if actual != source['sha256']:
            raise ValueError(f'Provenance hash mismatch: {relative}')
        consumed[relative] = actual
        sources[relative] = (source, _timestamp(source['available_at']))
    if not sources:
        raise MissingEvidence('Source manifest with hashes and availability required')
    units = {}
    unit_keys = set()
    if not isinstance(universe['rows'], list):
        raise ValueError('ForecastUniverse rows must be an array')
    for row in universe['rows']:
        check()
        if not isinstance(row, dict):
            raise ValueError('ForecastUniverse rows must be objects')
        row_id = row['row_id']
        if not isinstance(row_id, str) or not row_id or row_id in units:
            raise ValueError('Duplicate or invalid universe row ID')
        validate_night(row['operational_night'])
        cutoff = _timestamp(row['cutoff_time'])
        window = _timestamp(row['window_start_jst']).astimezone(JST)
        if window.minute % 10 or window.second or window.microsecond:
            raise ValueError('Universe time window must align to ten minutes')
        local_night = (window - timedelta(hours=7)).date().isoformat()
        if local_night != row['operational_night'] or cutoff >= window:
            raise ValueError('Universe operational night/cutoff mismatch')
        if max(universe_available, protocol_available, frozen_at) >= cutoff:
            raise ValueError('Universe/protocol availability must precede cutoff')
        x, y = _coordinates(row)
        key = (row['operational_night'], math.floor(x/100), math.floor(y/100), window.isoformat())
        if key in unit_keys:
            raise ValueError('Conflicting universe unit')
        unit_keys.add(key)
        units[row_id] = row
    if not units:
        raise MissingEvidence('Explicit nonempty forecast universe rows required')
    rows = []
    ids, references, events = set(), set(), set()
    if not isinstance(snapshot['rows'], list):
        raise ValueError('LearningSnapshot rows must be an array')
    for row in snapshot['rows']:
        check()
        if not isinstance(row, dict):
            raise ValueError('LearningSnapshot rows must be objects')
        row_id, reference = row['row_id'], row['universe_row_id']
        if row_id in ids or reference in references or reference not in units:
            raise ValueError('Duplicate/conflicting learning unit or absent universe row')
        ids.add(row_id)
        references.add(reference)
        unit = units[reference]
        for key in ('operational_night', 'cutoff_time', 'window_start_jst'):
            if row[key] != unit[key]:
                raise ValueError('Learning/universe time or night mismatch')
        x, y = _coordinates(unit)
        if row['cell_x'] != math.floor(x/100) or row['cell_y'] != math.floor(y/100):
            raise ValueError('Learning/universe cell mismatch')
        cutoff = _timestamp(row['cutoff_time'])
        if not isinstance(row['observed'], bool):
            raise ValueError('observed must be boolean')
        available = _timestamp(row['label_available_at']) if row['observed'] else None
        if available is not None and available < _timestamp(row['window_start_jst']):
            raise ValueError('Label availability precedes observation window')
        label = row['label']
        if row['observed']:
            if isinstance(label, bool) or label not in (0, 1):
                raise ValueError('Observed rows require explicit binary label')
        elif label is not None:
            raise ValueError('Unknown/unobserved label must be null, never Negative')
        capture_count = row['capture_count']
        event_ids = row['capture_event_ids']
        if not isinstance(capture_count, int) or isinstance(capture_count, bool) or capture_count < 0:
            raise ValueError('capture_count must be a nonnegative verified integer')
        if not isinstance(event_ids, list) or not all(isinstance(e, str) and e for e in event_ids) or len(set(event_ids)) != len(event_ids):
            raise ValueError('Invalid capture event IDs')
        if label == 1:
            if not event_ids or capture_count < len(event_ids):
                raise ValueError('Positive rows need confirmed capture counts and event IDs')
        elif capture_count or event_ids:
            raise ValueError('Nonpositive/unknown row cannot claim captures')
        for event in event_ids:
            if event in events:
                raise ValueError('Canonical capture event duplicated across learning rows/nights')
            events.add(event)
        if row['observed'] and row['quality'] not in ('AUDITED_OBSERVED', 'GOLD', 'SILVER', 'COMPLETE_REAL_GPX', 'HIGH_QUALITY_GPS_RECONSTRUCTION'):
            raise MissingEvidence('Audited observation quality contract required; unknown/spatial-only cannot provide temporal negatives')
        if not isinstance(row['source_refs'], list) or not row['source_refs']:
            raise MissingEvidence('Row provenance source_refs required')
        label_sources = []
        for ref in row['source_refs']:
            if ref not in sources:
                raise ValueError('Unknown provenance source reference')
            source, source_available = sources[ref]
            if source['role'] == 'label':
                label_sources.append(ref)
                if row['observed'] and source_available > available:
                    raise ValueError('Label availability precedes provenance source availability')
            if source.get('role') in ('feature', 'universe') and source_available >= cutoff:
                raise ValueError('Predictor source availability leakage')
        if row['observed'] and not label_sources:
            raise MissingEvidence('Observed labels require label-role source coverage')
        features, available_at = row['features'], row['feature_available_at']
        if not isinstance(features, dict) or not isinstance(available_at, dict) or set(features) != set(available_at):
            raise MissingEvidence('All features require individual availability timestamps')
        feature_sources = row.get('feature_source_refs')
        if not isinstance(feature_sources, dict) or set(feature_sources) != set(features):
            raise MissingEvidence('Every feature requires explicit feature_source_refs binding')
        for feature, value in features.items():
            _finite(value)
            feature_available = _timestamp(available_at[feature])
            if feature_available >= cutoff:
                raise ValueError(f'Feature availability leakage: {feature}')
            bindings = feature_sources[feature]
            if not isinstance(bindings, list) or not bindings:
                raise MissingEvidence(f'Feature source binding missing: {feature}')
            for ref in bindings:
                if not isinstance(ref, str) or ref not in row['source_refs'] or ref not in sources:
                    raise ValueError(f'Unknown or undeclared feature source: {feature}')
                source, source_available = sources[ref]
                if source['role'] != 'feature':
                    raise ValueError(f'Feature binding requires feature-role source: {feature}')
                if source_available > feature_available:
                    raise ValueError(f'Feature availability precedes bound source availability: {feature}')
        for effort in ('duration_seconds', 'distance_m'):
            if effort in row and row[effort] is not None and _finite(row[effort]) < 0:
                raise ValueError('Measured effort cannot be negative')
        if row['observed'] and row['operational_night'] in confirmation and frozen_at >= available:
            raise ValueError('Protocol was not frozen before confirmation label reveal')
        # Exact coordinates come from the immutable forecast universe only.
        rows.append(dict(row, utm_x_m=x, utm_y_m=y))
    if references != set(units):
        raise MissingEvidence('Learning snapshot must retain every universe row, including unobserved units')
    return snapshot, universe, protocol, rows


def _fit(family, train, protocol_sha, code_sha, protocol):
    labels = [r['label'] for r in train]
    base_probability = (sum(labels) + 1) / (len(labels) + 2)
    grouped = defaultdict(list)
    for row in train:
        grouped[_area(row)].append(row)
    values = {}
    if family == 'historical_capture_prior':
        total = sum(r['capture_count'] for r in train)
        values = {a: (sum(r['capture_count'] for r in rows)+1)/(total+len(grouped)) for a, rows in grouped.items()}
        default = 1/(total+len(grouped))
    elif family == 'observed_unit_prevalence':
        values = {a: (sum(r['label'] for r in rows)+1)/(len(rows)+2) for a, rows in grouped.items()}
        default = base_probability
    elif family == 'duration_normalized_area_rate':
        if any(not r.get('duration_seconds') or not r.get('effort_method') or not r.get('observer_version') for r in train):
            raise MissingEvidence('Measured duration_seconds, effort_method and observer_version required for effort-normalized rate')
        duration = sum(r['duration_seconds'] for r in train)
        prior = sum(r['capture_count'] for r in train)/duration
        reference = protocol['effort_reference_seconds']
        values = {a: (sum(r['capture_count'] for r in rows)+prior*reference)/(sum(r['duration_seconds'] for r in rows)+reference) for a, rows in grouped.items()}
        default = prior
    else:
        default = base_probability
    body = {'schema_version': '1.0', 'family': family, 'implementation_version': VERSION,
            'parameters': {'area_values': values, 'default': default, 'smoothing': 1.0},
            'hyperparameters': {'smoothing': 1.0, 'area_size_m': 1000,
                                'effort_reference_seconds': protocol.get('effort_reference_seconds') if family == 'duration_normalized_area_rate' else None},
            'status': 'CANDIDATE', 'evidence_refs': [{'protocol_sha256': protocol_sha}],
            'training_cutoff': max((r['label_available_at'] for r in train), key=_timestamp),
            'training_data_sha256': digest(sorted(train, key=lambda r: r['row_id'])),
            'feature_schema_sha256': digest([]), 'protocol_sha256': protocol_sha,
            'code_sha256': code_sha, 'produced_outputs': ['spatial_score'] + (['unit_probability'] if family in ('uniform', 'observed_unit_prevalence') else [])}
    model_sha = digest(body)
    return dict(body, model_id=model_sha, model_sha256=model_sha)


def predict_model(model: dict, universe_rows: list[dict]) -> list[dict]:
    """Execute a registered model; returns actual row scores, never time targets.

    The model is the exact serialized `fold['model']` object. `model_sha256` and
    `model_id` equal the canonical digest of all other model fields. Spatial
    score-only families return probability=None and are never Brier-scored.
    """
    family = model.get('family')
    if family not in FAMILIES:
        raise ValueError('Unregistered model family')
    body = {k: v for k, v in model.items() if k not in ('model_id', 'model_sha256')}
    if digest(body) != model.get('model_sha256') or model.get('model_id') != model.get('model_sha256'):
        raise ValueError('Model digest mismatch')
    parameters = model['parameters']
    default = _finite(parameters['default'])
    areas = parameters['area_values']
    if not isinstance(areas, dict) or default < 0:
        raise ValueError('Invalid model parameters')
    for value in areas.values():
        if _finite(value) < 0:
            raise ValueError('Invalid negative area score')
    rows, seen = [], set()
    for unit in universe_rows:
        if _timestamp(model['training_cutoff']) >= _timestamp(unit['cutoff_time']):
            raise ValueError('Model training availability must precede forecast cutoff')
        identity = unit['row_id']
        if identity in seen:
            raise ValueError('Duplicate inference universe row')
        seen.add(identity)
        score = default if family == 'uniform' else areas.get(_area(unit), default)
        probability = score if family in ('uniform', 'observed_unit_prevalence') else None
        if probability is not None and not 0 <= probability <= 1:
            raise ValueError('Invalid probability')
        x, y = _coordinates(unit)
        rows.append({'universe_row_id': identity, 'operational_night': unit['operational_night'],
                     'utm_x_m': x, 'utm_y_m': y, 'spatial_score': score, 'probability': probability})
    return sorted(rows, key=lambda r: r['universe_row_id'])


def _metrics(predictions, test):
    observed = [r for r in test if r['observed']]
    lookup = {p['universe_row_id']: p for p in predictions}
    total = sum(r['capture_count'] for r in observed)
    events = sum(len(r['capture_event_ids']) for r in observed)
    result = {'observed_units': len(observed), 'unknown_units': len(test)-len(observed)}
    for size in (1000, 500, 250, 100):
        scores = defaultdict(list)
        for prediction in predictions:
            scores[_area(prediction, size)].append(prediction['spatial_score'])
        ranked = sorted(scores, key=lambda a: (-mean(scores[a]), a))[:10]
        hit = [r for r in observed if _area(r, size) in ranked]
        recall = sum(r['capture_count'] for r in hit)/total if total else None
        value = {'status': 'NOT_VALIDATED', 'top10': ranked,
                 'restricted_individual_recall': recall, 'restricted_event_recall': sum(len(r['capture_event_ids']) for r in hit)/events if events else None,
                 'included_confirmed_individuals': total, 'included_distinct_events': events,
                 'scope': 'OBSERVED_UNITS_WITHIN_FORECAST_UNIVERSE',
                 'denominator_coverage': 'NOT_ESTABLISHED',
                 'coverage_reason': 'Complete hash-bound outcome ledger including captures outside the forecast universe is unavailable',
                 'gate_outcome': 'NOT_EVALUATED'}
        result['stage1' if size == 1000 else f'spatial_{size}m'] = value
    pairs = [(lookup[r['universe_row_id']]['probability'], r['label']) for r in observed]
    valid_probability = bool(pairs) and all(p is not None for p, _ in pairs)
    result['brier'] = mean((p-y)**2 for p, y in pairs) if valid_probability else None
    result['calibration'] = {'status': 'DESCRIPTIVE' if valid_probability else 'NOT_PRODUCED', 'bins': []}
    if valid_probability:
        for index in range(5):
            group = [(p, y) for p, y in pairs if min(4, int(p*5)) == index]
            if group:
                result['calibration']['bins'].append({'bin': index, 'count': len(group), 'mean_probability': mean(p for p, _ in group), 'observed_fraction': mean(y for _, y in group)})
    result['formal_100m_10min'] = {'status': 'NOT_PRODUCED', 'reason': 'Models emit spatial scores, not actual time targets'}
    return result


def _research(rows):
    observed = [r for r in rows if r['observed']]
    names = sorted({name for r in observed for name in r['features']})
    associations = []
    for feature in names:
        pairs = [(r['features'][feature], r['label']) for r in observed if feature in r['features']]
        mx, my = mean(x for x, _ in pairs), mean(y for _, y in pairs)
        denominator = math.sqrt(sum((x-mx)**2 for x, _ in pairs)*sum((y-my)**2 for _, y in pairs))
        correlation = sum((x-mx)*(y-my) for x, y in pairs)/denominator if denominator else None
        associations.append({'feature': feature, 'observed_units': len(pairs), 'pearson_association': correlation, 'interpretation': 'Descriptive association only; no causal or adjusted effect'})
    return associations


def _drift(train, test):
    features = sorted({name for r in train + test for name in r['features']})
    shifts = {}
    for feature in features:
        before = [r['features'][feature] for r in train if feature in r['features']]
        after = [r['features'][feature] for r in test if feature in r['features']]
        shifts[feature] = mean(after)-mean(before) if before and after else None
    before, after = defaultdict(int), defaultdict(int)
    for row in train:
        before[_area(row)] += 1
    for row in test:
        after[_area(row)] += 1
    area_shift = sum(abs(before[a]/len(train)-after[a]/len(test)) for a in set(before)|set(after))/2
    return {'status': 'DESCRIPTIVE', 'feature_mean_shift': shifts, 'area_total_variation': area_shift,
            'reason': 'Distribution comparison only; no validated drift threshold'}


def _comparison(family, folds, check):
    baseline = {f['night']: f['metrics']['brier'] for f in folds if f['family'] == 'uniform'}
    pairs = [(f['night'], baseline[f['night']]-f['metrics']['brier']) for f in folds
             if f['family'] == family and f['metrics']['brier'] is not None and baseline.get(f['night']) is not None]
    if family == 'uniform' or not pairs:
        return {'status': 'NOT_VALIDATED', 'reason': 'Baseline or score-only family; no paired probability comparison'}
    improvements = [value for _, value in pairs]
    rng = random.Random(1642)
    draws = []
    for draw in range(2000):
        if draw % 100 == 0:
            check()
        draws.append(mean(rng.choices(improvements, k=len(improvements))))
    draws.sort()
    delta = mean(improvements)
    return {'status': 'REJECT_CANDIDATE' if delta <= 0 else 'NOT_VALIDATED',
            'mean_brier_improvement': delta, 'paired_nights': [night for night, _ in pairs],
            'uncertainty': {'status': 'NOT_VALIDATED', 'scope': 'RESEARCH_DIAGNOSTIC',
                            'method': 'deterministic night-cluster bootstrap', 'draws': 2000,
                            'interval_95': [draws[49], draws[1949]],
                            'reason': 'Research nights are not untouched independent confirmation'}}


def _immutable_replay(root, night, content):
    raw = canonical_bytes(content)+b'\n'
    relative = f'predictions/replay/{night}/{digest(content)}.json'
    path = safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('Immutable REPLAY artifact was changed')
    else:
        fd, temporary = tempfile.mkstemp(prefix='.replay-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != raw:
                    raise ValueError('Conflicting immutable REPLAY artifact')
        finally:
            os.unlink(temporary)
    return {'path': relative, 'sha256': file_hash(path)}


def evaluate_models(root: Path, night: str, budget_seconds: int = 300) -> dict:
    validate_night(night)
    root = Path(root)
    started = time.monotonic()
    def check():
        if time.monotonic() - started >= budget_seconds:
            raise BudgetExhausted('BUDGET_EXHAUSTED: retry with remaining cumulative budget')
    result = {'schema_version': '1.0', 'stages': [], 'candidates': [], 'folds': [], 'replay': [],
              'research_questions': [], 'implementation_blockers': list(IMPLEMENTATION_BLOCKERS), 'data_blockers': [],
              'decision': {'decision': 'NEED_MORE_DATA', 'reasons': [], 'required_conditions': list(IMPLEMENTATION_BLOCKERS)}}
    consumed = {}
    status, reason = 'NOT_VALIDATED', 'Diagnostic bounded spatial evaluation; scientific/full-scope gates remain unvalidated'
    try:
        check()
        snapshot, universe, protocol, rows = _validate(root, night, consumed, check)
        code_sha = file_hash(Path(__file__))
        universe_lookup = {r['row_id']: r for r in universe['rows']}
        research = set(protocol['research_used_nights'])
        research_rows = [r for r in rows if r['operational_night'] in research and r['operational_night'] <= night]
        # Confirmation rows are never inspected for fitting, scoring or research here.
        result['research_questions'] = [
            'Which ex-ante covariates explain observed-unit uncertainty after adjustment?',
            'Are measured search duration/distance and observer effects available?',
            'Do results replicate across independent future nights and calendar years?']
        as_of = datetime.combine(datetime.fromisoformat(night).date()+timedelta(days=1), day_time(7), JST)
        available_rows = [r for r in research_rows if not r['observed'] or _timestamp(r['label_available_at']) < as_of]
        result['associations'] = _research(available_rows)
        families = protocol['registered_candidates']
        for heldout in sorted({r['operational_night'] for r in research_rows}):
            check()
            test = [r for r in research_rows if r['operational_night'] == heldout]
            if any(r['observed'] and _timestamp(r['label_available_at']) >= as_of for r in test):
                result['data_blockers'].append(f'{heldout}: test labels not available by evaluation boundary')
                continue
            cutoff = min(_timestamp(r['cutoff_time']) for r in test)
            night_start = datetime.combine(datetime.fromisoformat(heldout).date(), day_time(7), JST)
            train = [r for r in available_rows if r['observed'] and r['operational_night'] < heldout
                     and _timestamp(r['label_available_at']) < min(cutoff, night_start)]
            if not train or {r['label'] for r in train} != {0, 1}:
                result['data_blockers'].append(f'{heldout}: insufficient prior training nights/classes with labels available before test night/cutoff')
                continue
            if not any(r['observed'] for r in test):
                result['data_blockers'].append(f'{heldout}: no observed labels for evaluation')
                continue
            test_universe = [universe_lookup[r['universe_row_id']] for r in test]
            fitted = {}
            try:
                for family in families:
                    check()
                    fitted[family] = _fit(family, train, snapshot['protocol']['sha256'], code_sha, protocol)
            except MissingEvidence as exc:
                result['data_blockers'].append(f'{heldout}: common-fold eligibility blocked: {exc}')
                continue
            for family in families:
                check()
                model = fitted[family]
                predictions = predict_model(model, test_universe)
                fold = {'night': heldout, 'family': family, 'model': model,
                        'train_row_ids': sorted(r['row_id'] for r in train), 'test_row_ids': sorted(r['row_id'] for r in test),
                        'universe_sha256': snapshot['candidate_universe_sha256'],
                        'test_universe_sha256': digest(sorted(test_universe, key=lambda r:r['row_id'])),
                        'predictions': predictions,
                        'labels': [{'universe_row_id': r['universe_row_id'], 'observed': r['observed'], 'label': r['label'],
                                    'capture_count': r['capture_count'], 'capture_event_ids': r['capture_event_ids']} for r in sorted(test, key=lambda r:r['row_id'])],
                        'metrics': _metrics(predictions, test), 'drift': _drift(train, test), 'evidence_scope': 'RESEARCH_DIAGNOSTIC',
                        'training_data_sha256': model['training_data_sha256'], 'input_sha256': consumed['data/processed/model_learning.json']}
                result['folds'].append(fold)
                result['replay'].append(_immutable_replay(root, heldout, fold))
        for family in families:
            folds = [f for f in result['folds'] if f['family'] == family]
            briers = [f['metrics']['brier'] for f in folds if f['metrics']['brier'] is not None]
            result['candidates'].append({'family': family, 'fold_nights': [f['night'] for f in folds],
                                         'mean_brier': mean(briers) if briers else None,
                                         'status': 'NOT_VALIDATED' if folds else 'BLOCKED',
                                         'comparison': _comparison(family, result['folds'], check)})
        comparisons = [c['comparison'] for c in result['candidates'] if 'mean_brier_improvement' in c['comparison']]
        if comparisons and all(c['mean_brier_improvement'] <= 0 for c in comparisons):
            result['decision']['decision'] = 'REJECT_CANDIDATE'
            reason = 'Probability candidates show no paired research Brier improvement over uniform; no candidate eligible for promotion'
        result['validation'] = {'independent_confirmation': 'NOT_VALIDATED', 'cross_year': 'NOT_VALIDATED',
                                'ablation': 'NOT_VALIDATED', 'uncertainty': 'NOT_VALIDATED',
                                'reason': 'Research labels cannot be reused as independent confirmation; feature-aware retraining and mandatory output adapters absent'}
        if len({f['night'] for f in result['folds']}) < 5:
            result['data_blockers'].append('Fewer than five held-out nights; five is a floor, not proof of adequacy')
        if len({f['night'][:4] for f in result['folds']}) < 2:
            result['data_blockers'].append('Cross-year evidence unavailable')
        result['data_blockers'].append('Full Stage1 outcome denominator coverage is not established; restricted-universe recall is diagnostic only')
        result['data_blockers'].append('Independent prospective confirmation and measured effort coverage unresolved')
        if not result['folds']:
            status, reason = 'BLOCKED', 'No eligible audited folds with prior training evidence'
        check()
        for relative, expected in consumed.items():
            if file_hash(safe_path(root, relative)) != expected:
                raise ValueError(f'Consumed input changed during evaluation: {relative}')
        if file_hash(Path(__file__)) != code_sha:
            raise ValueError('Evaluation code changed during execution')
    except BudgetExhausted as exc:
        status, reason = 'BLOCKED', str(exc)
        result['data_blockers'].append(reason)
    except (MissingEvidence, KeyError, FileNotFoundError) as exc:
        status, reason = 'BLOCKED', f'DATA_BLOCKED: required audited snapshot contract/evidence missing: {exc}'
        result['data_blockers'].append(reason)
    except (ValueError, TypeError, OSError, OverflowError) as exc:
        status, reason = 'FAIL', f'INVALID_MODEL_EVIDENCE: {exc}'
        result['decision']['decision'] = 'REJECT_CANDIDATE'
        result['data_blockers'].append(reason)
    result['output_status'] = {
        'formal_100m_10min': {'status': 'NOT_PRODUCED', 'reason': IMPLEMENTATION_BLOCKERS[0]},
        'feature_ablation': {'status': 'NOT_VALIDATED', 'reason': IMPLEMENTATION_BLOCKERS[1]},
        **{name: {'status': 'BLOCKED', 'reason': 'IMPLEMENTATION_BLOCKED: required model executor unavailable'}
           for name in ('count', 'activity', 'detection', 'routes', 'rerouting')},
        **{name: {'status': 'NOT_VALIDATED' if result['folds'] else 'BLOCKED',
                  'reason': 'Diagnostic spatial scores only; full independent validation unavailable'}
           for name in ('stage1', 'spatial_500m', 'spatial_250m', 'spatial_100m')},
    }
    result['data_blockers'] = sorted(set(result['data_blockers']))
    result['decision']['reasons'] = [reason]
    result['decision']['required_conditions'].extend(result['data_blockers'])
    result['evidence'] = {'consumed_inputs': consumed, 'confirmation_labels_used': False,
                          'scope': 'diagnostic only; no production trust inferred from supplied flags'}
    for name in NAMES:
        stage_status = status
        stage_reason = reason
        if status not in ('FAIL', 'BLOCKED') and name == 'candidate_generation':
            stage_status, stage_reason = 'PASS', 'Executed fixed registered adapters; immutable diagnostic REPLAY emitted'
        elif status not in ('FAIL', 'BLOCKED') and name == 'candidate_validation':
            stage_status, stage_reason = 'BLOCKED', '; '.join(IMPLEMENTATION_BLOCKERS)
        result['stages'].append(dict(stage(name, stage_status, stage_reason,
            evidence=result['replay'] if name == 'candidate_generation' else [],
            metrics={'fold_count': len(result['folds'])},
            blocker_kind='IMPLEMENTATION_BLOCKED' if name == 'candidate_validation' and status not in ('FAIL', 'BLOCKED') else 'DATA_BLOCKED' if stage_status == 'BLOCKED' else None), implementation_version=VERSION))
    return result
