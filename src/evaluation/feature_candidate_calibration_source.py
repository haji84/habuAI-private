"""One source-consistent development calibration fold, without trust or authority.

The later observation selector is an evaluation identity only. It is never the
forecasting model's TRAIN, fit cutoff, prediction cutoff or feature input.
"""
from __future__ import annotations

import g0_forecast_contract as g0
import g0_training_source_contract as training
import prospective_inputs as pi
import research_model_adapter as models
from codex_cycle_contract import training_boundary
from master_contracts import validate_night
from models import feature_candidate_diagnostics as pure
from research_candidate_config_source import RESERVED
from . import stage1_source_adapter as native
from . import full_ledger_stage1 as native_pure

VERSION = 'habu-feature-calibration-source-v1'
FIELDS = {'schema_version', 'purpose', 'evaluation_as_of', 'candidate_id',
          'protocol', 'observation_manifest', 'observation_selector'}
SELECTOR_FIELDS = {'heldout_night', 'fit_cutoff', 'forecast_cutoff', 'exposed_nights'}
MAX_PROFILE_BYTES = 256 * 1024
MAX_PROTOCOL_BYTES = 64 * 1024


class CallerFailure(BaseException):
    """Keep a real caller check outside legacy preparation normalization."""
    def __init__(self, origin):
        self.origin = origin


class ObservationBlocked(training.G0TrainingInputBlocked):
    """Retain the completed selector's reasons, without a metric or replay."""
    def __init__(self, reason, observation, profile):
        super().__init__(reason)
        selected = observation['selection']
        self.details = dict(schema_version=VERSION, status='NEED_MORE_DATA',
            source_authentication='NOT_ATTESTED', observation_manifest=profile['observation_manifest'],
            observation_selector=profile['observation_selector'],
            observation_source_receipt=observation['receipt'],
            selection_sha256=selected['selection_sha256'], counts=selected['counts'],
            rejected=selected['rejected'], blockers=selected['blockers'], **_flags())


def prepare(selection, rows, *, context, **options):
    """Call the unchanged configured preparer once, preserving FIRST origin."""
    first = []
    external = type(context).check is not pi.ProspectiveReadContext.check

    def check():
        if first:
            raise first[0]
        try:
            context.check()
        except BaseException as exc:
            if not external:
                raise
            first.append(CallerFailure(exc))
            raise first[0] from None

    check()
    try:
        value = models.prepare_research_candidates_v2(selection, rows,
            budget_seconds=context.remaining_seconds, check=check, **options)
    except BaseException:
        if first:
            raise first[0]
        raise
    check()
    return value


def input_ref(ref):
    training._reference(ref, 'manifest')
    _namespace(ref['path'])
    return ref


def _namespace(path):
    if any(part.casefold() in RESERVED for part in path.split('/')):
        raise ValueError('Reserved calibration source namespace')


def _owned(value, check):
    try:
        return pure._copy_inputs([value], check)[0]
    except pure.DiagnosticCapacityBlocked as exc:
        raise pi.InputCapacityError(str(exc)) from exc


def _namespaces(value, check):
    pending = [value]
    while pending:
        check()
        item = pending.pop()
        if type(item) is dict:
            if 'path' in item:
                if type(item['path']) is not str:
                    raise ValueError('Calibration source path must be a string')
                _namespace(item['path'])
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)


def _read(reader, ref, maximum):
    g0._capacity(ref['size_bytes'], maximum, 'calibration artifact bytes')
    reader._limits[ref['path']] = min(reader._limits.get(ref['path'], maximum), maximum)
    return _owned(reader.read(ref, small=maximum <= g0.MAX_SMALL_BYTES), reader.context.check)


def preflight(root, ref, *, context):
    """Read only explicit declarations/protocol, never a corpus or source payload."""
    input_ref(ref)
    reader = g0.G0ArtifactReader(root, context)
    profile = _read(reader, ref, MAX_PROFILE_BYTES)
    pure._fields(profile, FIELDS)
    if (profile['schema_version'] != VERSION or
            profile['purpose'] != 'DEVELOPMENT_EVALUATION_ONLY' or profile['candidate_id'] != 'HB-A1'):
        raise ValueError('Explicit single HB-A1 development calibration required')
    _namespaces(profile, context.check)
    evaluation = pi._time(profile['evaluation_as_of'])
    pure._fields(profile['protocol'], {'ref', 'readiness', 'usable_at'})
    input_ref(profile['protocol']['ref'])
    times = profile['protocol']['readiness']
    g0._object(times, pi.READINESS_FIELDS, 'Required four protocol readiness timestamps')
    if g0._stamp(profile['protocol']['usable_at']) != max(g0._stamp(t) for t in times.values()):
        raise ValueError('Protocol usable_at must equal exact readiness maximum')
    training._ready(times, profile['protocol']['usable_at'], evaluation)
    protocol = _read(reader, profile['protocol']['ref'], MAX_PROTOCOL_BYTES)
    pure._fields(protocol, pure.PROTOCOL_FIELDS)
    if (protocol['schema_version'] != pure.PROTOCOL_VERSION or
            protocol['phase'] != 'DEVELOPMENT' or protocol['target'] != pure.TARGET):
        raise ValueError('Only existing pure development calibration protocol supported')
    # Validate declared numerical controls before any held-out source payload.
    # The unchanged pure function repeats these checks when it owns all inputs.
    edges = protocol['bin_edges']
    if type(edges) is not list or len(edges) < 2:
        raise ValueError('At least two fixed reliability bin endpoints required')
    g0._capacity(len(edges)-1, pure.MAX_BINS, 'reliability bins')
    for index, edge in enumerate(edges):
        context.check()
        number = pure._number(edge)
        if not 0 <= number <= 1 or index and not edges[index-1] < number:
            raise ValueError('Strict ordered reliability bins in [0,1] required')
    if edges[0] != 0 or edges[-1] != 1:
        raise ValueError('Reliability endpoints must be exactly zero and one')
    if not 1e-15 <= pure._number(protocol['log_loss_clip']) < .5:
        raise ValueError('Invalid fixed diagnostic clipping')
    pure._hash(protocol['evaluation_selection_sha256'])
    pure._hash(protocol['predictions_sha256'])
    args = profile['observation_selector']
    pure._fields(args, SELECTOR_FIELDS)
    validate_night(args['heldout_night'])
    if (type(args['exposed_nights']) is not list or
            len(args['exposed_nights']) > pure.MAX_ROWS or
            any(type(n) is not str for n in args['exposed_nights']) or
            len(set(args['exposed_nights'])) != len(args['exposed_nights'])):
        raise ValueError('Original observation selector exposed nights required')
    for night in args['exposed_nights']:
        context.check()
        validate_night(night)
    if training_boundary(args['heldout_night'], args['fit_cutoff'], args['forecast_cutoff']) >= evaluation:
        raise ValueError('Original observation selection boundary must precede assessment')
    input_ref(profile['observation_manifest'])
    manifest = _read(reader, profile['observation_manifest'], g0.MAX_SMALL_BYTES)
    pure._fields(manifest, training.FIELDS)
    if manifest['schema_version'] != training.VERSION or manifest['kind'] != 'TRAIN_ONLY_SOURCE_CLOSURE':
        raise ValueError('Original strict observation source closure required')
    _namespaces(manifest, context.check)
    context.check()
    return dict(profile=profile, protocol=protocol, manifest=manifest, reader=reader)


def _refs(value, result, check):
    pending = [value]
    while pending:
        check()
        item = pending.pop()
        if type(item) is dict:
            if g0.REF_FIELDS <= item.keys():
                ref = {key: item[key] for key in g0.REF_FIELDS}
                g0._ref(ref)
                previous = result.get(ref['path'])
                if previous is not None and previous != ref:
                    raise ValueError('Conflicting original calibration reference')
                result[ref['path']] = ref
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)


def _unit(row):
    return row['cell_x'], row['cell_y'], pi._time(row['window_start_jst'])


def _flags():
    return dict(fit_authorized=False, selection_authorized=False,
        promotion_authorized=False, scientific_execution_authorized=False,
        official_issuance_authorized=False, production_authorized=False,
        confirmation_authorized=False, trusted_pre_reveal_authorized=False)


def evaluate(root, admission, forecast, prepared, actual_training, candidate_config, *,
             expected_config_sha256, feature_definition_sha256, context):
    check = context.check
    profile, protocol, reader = admission['profile'], admission['protocol'], admission['reader']
    # Existing pure native validators check complete fixed-three output before
    # the first held-out corpus/source payload. No Stage1 outcome loader runs.
    try:
        _, projection = native._configured_prepared(candidate_config, forecast, prepared,
            expected_config_sha256, feature_definition_sha256, check)
    except (native_pure.Stage1CapacityBlocked, models.ResearchCapacityBlocked,
            models.ResearchInputCapacity, models._hba1.HBA1CapacityBlocked) as exc:
        raise pi.InputCapacityError(str(exc)) from exc
    except native_pure.Stage1BudgetBlocked as exc:
        raise TimeoutError(str(exc)) from exc
    forecast, prepared, night = projection[:3]
    selected = models.validate_selection(actual_training['selection'])
    check()
    if (prepared['training_selection_sha256'] != selected['selection_sha256'] or
            prepared['fit_cutoff'] != selected['fit_cutoff'] or
            prepared['heldout_night'] != selected['heldout_night'] or selected['heldout_night'] != night):
        raise ValueError('Actual parent TRAIN/fold identity mismatch')
    for key, value in (
            ('training_rows_sha256', selected['accepted']),
            ('training_row_ids_sha256', [r['row_id'] for r in selected['accepted']]),
            ('raw_feature_rows_sha256', [dict(row_id=r['row_id'], features=r['features']) for r in selected['accepted']])):
        if prepared[key] != pure._digest(value, check):
            raise ValueError('Actual parent TRAIN rows differ from configured prepared lineage')
    candidate = next((c for c in prepared['candidates'] if c['candidate_id'] == 'HB-A1'), None)
    if candidate is None:
        raise ValueError('Configured three-slot set must include native HB-A1')
    model, prediction = candidate['model'], candidate['prediction']
    if (prediction.get('schema_version') != models._hba1.PREDICTION_VERSION or
            prediction.get('target_semantics') != models._hba1.TARGET):
        raise ValueError('Native HB-A1 probability target required')
    folds = pure._folds(protocol['folds'], {night}, protocol['evaluation_selection_sha256'], check)
    actual_fold = dict(night=night, model_sha256=candidate['model_sha256'],
        training_selection_sha256=selected['selection_sha256'], training_cutoff=selected['fit_cutoff'],
        train_nights=sorted({r['night'] for r in selected['accepted']}))
    if folds[night] != actual_fold or model['training_nights'] != actual_fold['train_nights']:
        raise ValueError('Calibration protocol must bind the actual model/TRAIN fold')
    if pi._time(profile['evaluation_as_of']) <= pi._time(forecast['receipt']['cutoff_time']):
        raise ValueError('Post-forecast assessment required')
    future = {}
    native_units = {u['row_id']: u for u in prediction['unit_predictions']}
    for row in forecast['rows']:
        check()
        unit = _unit(row)
        if unit in future:
            raise ValueError('Duplicate physical forecast unit')
        output = native_units[row['row_id']]
        probability = pure._number(output.get('probability'))
        if (not 0 <= probability <= 1 or output.get('probability_status') != 'NOT_VALIDATED' or
                probability != output['spatial_score'] or
                probability != models._hba1._score_owned_row(model, row, check)):
            raise ValueError('Native probability differs from actual model inference')
        future[unit] = row, probability
    args = profile['observation_selector']
    observation = training.select_g0_training_rows(root, profile['observation_manifest'],
        args['heldout_night'], args['fit_cutoff'], args['forecast_cutoff'],
        expected_feature_definition_sha256=feature_definition_sha256,
        exposed_nights=tuple(args['exposed_nights']), budget_seconds=context.remaining_seconds,
        _read_context=context)
    observed = observation['selection']
    check()
    if pure._hash(protocol['evaluation_selection_sha256']) != observed['selection_sha256']:
        raise ValueError('Calibration protocol observation selection hash mismatch')
    refs = dict(reader.refs)
    _refs(admission['manifest'], refs, check)
    _refs(profile, refs, check)
    for path, sha in observation['receipt']['consumed_sha256'].items():
        check()
        if path not in refs or refs[path]['sha256'] != sha:
            raise ValueError('Observation source receipt is not bound to original refs')
    corpus = _read(reader, observation['receipt']['corpus_ref'], 16 * 1024**2)
    rows = corpus.get('rows')
    if type(rows) is not list or len(rows) > pure.MAX_ROWS:
        raise pi.InputCapacityError('CAPACITY_BLOCKED: complete calibration observation rows')
    train_units = {_unit(r) for r in selected['accepted']}
    train_events = {event for r in selected['accepted'] for event in r['capture_event_ids']}
    for row in rows:
        check()
        if row['night'] != night:
            raise ValueError('Complete observation corpus must be the actual evaluated night')
        if _unit(row) in train_units or train_events.intersection(row['capture_event_ids']):
            raise ValueError('TRAIN and evaluation observation/event overlap')
    if any(r['night'] != night for r in observed['accepted'] + observed['rejected']):
        raise ValueError('Observation selector cannot filter other development nights')
    if not observed['accepted']:
        raise ObservationBlocked('No qualified observed units for descriptive calibration', observation, profile)
    predictions = []
    for row in observed['accepted']:
        check()
        if _unit(row) not in future:
            raise ObservationBlocked('Observed unit outside full forecast; no subset calibration', observation, profile)
        original, probability = future[_unit(row)]
        if row['features'] != original['features']:
            raise ValueError('Observed physical predictor values differ from original strict forecast')
        predictions.append(dict({key:row[key] for key in pure.PREDICTION_FIELDS
                                 if key not in ('probability','model_sha256','training_selection_sha256')},
            probability=probability, model_sha256=candidate['model_sha256'],
            training_selection_sha256=selected['selection_sha256']))
    try:
        diagnostic = pure.describe_feature_candidate_development(protocol, observed, predictions,
            expected_protocol_sha256=pure._digest(protocol, check),
            budget_seconds=context.remaining_seconds, check=check)
    except pure.DiagnosticCapacityBlocked as exc:
        raise pi.InputCapacityError(str(exc)) from exc
    for ref in refs.values():
        check()
        reader.read(ref, parse=False)
    reader.rescan()
    check()
    receipt = dict(schema_version=VERSION, status='DECLARED_SOURCE_CONSISTENCY_ONLY',
        source_authentication='NOT_ATTESTED', evaluation_as_of=profile['evaluation_as_of'],
        observation_manifest_ref=profile['observation_manifest'], observation_selector=args,
        observation_receipt=observation['receipt'], observation_selection_sha256=observed['selection_sha256'],
        observation_selection_status=observed['status'], observation_blockers=observed['blockers'],
        observation_rejected=observed['rejected'], candidate_config_sha256=expected_config_sha256,
        feature_definition_sha256=feature_definition_sha256, actual_fold=actual_fold,
        model_sha256=candidate['model_sha256'], prediction_sha256=candidate['prediction_sha256'],
        forecast_manifest_ref=forecast['receipt']['manifest_ref'],
        joined_universe_sha256=forecast['receipt']['canonical_joined_rows_sha256'],
        prepared_receipt_sha256=prepared['receipt_sha256'],
        consumed_refs=[refs[p] for p in sorted(refs)],
        consumed_sha256={p:refs[p]['sha256'] for p in sorted(refs)},
        actual_read_bytes=context.bytes_read, **_flags())
    receipt['receipt_sha256'] = pure._digest(receipt, check)
    result = dict(dispatch_status='SOURCE_BOUND_CALIBRATION_DISPATCHED_CONSISTENCY_ONLY',
        diagnostic=diagnostic, source_receipt=receipt, source_authentication='NOT_ATTESTED',
        calibration_status='NOT_VALIDATED', statistical_adequacy='NOT_ASSESSED',
        selection_decision='NEED_MORE_DATA', observation_use='DEVELOPMENT_NOT_UNTOUCHED_CONFIRMATION',
        resolved_parent_capabilities=['SOURCE_BOUND_CALIBRATION_PARENT_DISPATCH_NOT_IMPLEMENTED'],
        **_flags())
    check()
    return result


def recheck(calibration, prepared, context):
    """Guard parent memory after result/stage construction, without resealing."""
    expected = calibration['source_receipt']['prepared_receipt_sha256']
    if (prepared.get('receipt_sha256') != expected or
            pure._digest({k:v for k,v in prepared.items() if k != 'receipt_sha256'}, context.check) != expected):
        raise ValueError('Native preparation changed after calibration')
    context.check()

