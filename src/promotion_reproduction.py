"""Read-only DEVELOPMENT reproduction of the existing configured HB-A1 recipe.

This is a numeric executor, never an authentication or activation entrypoint.
``reproduce_candidate(bundle, frozen_policy, *, input_root, budget_seconds=300)``
reads exact {path,sha256,size_bytes} references using the existing guarded G0
readers. input_root is a controller-selected exact str/native concrete Path;
no callable, transport, executable model format or write destination is accepted.

Request exact fields are REQUEST_FIELDS below. Folds have FOLD_FIELDS. The
candidate_config_ref names the existing DEVELOPMENT_CANDIDATE_CONFIG_SOURCE;
HB-A1 is the implemented selected_candidate_id; other printable recipe IDs are
explicit implementation blockers. expected_prepared_ref is the complete existing
configured-v2 artifact, not a metrics summary. stage1_manifest_ref and
calibration_manifest_ref use their unchanged DEVELOPMENT source contracts.
The three composite refs name the shared registered model, input, and complete
frozen PredictionBundle. Null prerequisites are reported; they do not suppress
other executable development calculations. Protocol/history are the existing
locked split metadata projections. ablation_protocol_ref is the existing HB-A1
DEVELOPMENT retraining protocol, covering all supplied folds.

frozen_policy is exactly the existing g0-policy-v1 (canonical POLICY_DIGEST).
No candidate threshold override, implicit partial product scope or invented
calibration/spatial threshold is allowed. The conservative installed code
closure is codex_cycle_contract.code_paths, checked against input-root bytes
and the installed source before and after execution. This binds source bytes,
not loaded bytecode, OS isolation, historical availability or source authenticity.

Outputs separate execution, validity and computed predicates. Metrics use actual
source-contract-validated observed masks and the complete individual ledger, including
outside-universe misses. All authority flags stay false. DEVELOPMENT sources
never become untouched confirmation; no sealed/confirmation payload is opened.
No replay, source, model, label, log, budget ledger or pointer is written.
eligible_training_units remains null: scientific/global eligibility is not
authenticated here. development_training_unique_units counts distinct actually
selected physical units; fit_training_row_memberships counts repeated fit inputs.
Locked split metadata is checked for declared consistency, not authenticated
group-to-source projections or a trusted global consumption/budget history.
Interrupted/invalid runs discard all unsealed computed results.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import random
import sys

import codex_cycle_contract as cycle
import g0_forecast_contract as g0
import g0_training_source_contract as training
import model_evaluation
import prospective_inputs as pi
import research_model_adapter as models
import research_candidate_config_source as configuration
from master_contracts import validate_night
from models import hba1_feature_candidate as hba1
from models.research_selection import IDENTITY_FIELDS
from evaluation import feature_candidate_calibration_source as calibration
from evaluation import stage1_source_adapter as stage1_source
from evaluation import full_ledger_stage1 as stage1_pure
from evaluation.locked_protocol_manifest import validate_locked_protocol

VERSION = 'habu-promotion-reproduction-v1'
REQUEST_FIELDS = {'schema_version', 'purpose', 'policy_sha256', 'selected_candidate_id',
    'candidate_config_ref', 'code_manifest', 'protocol_ref', 'exposure_history_ref',
    'ablation_protocol_ref', 'folds'}
FOLD_FIELDS = {'fold_id', 'operational_night', 'fit_cutoff', 'forecast_cutoff',
    'forecast_as_of', 'feature_definition_sha256', 'training_manifest_ref',
    'forecast_manifest_ref', 'expected_prepared_ref', 'stage1_manifest_ref',
    'calibration_manifest_ref', 'composite_model_ref', 'inference_bundle_ref',
    'frozen_prediction_ref'}
RESERVED = {'sealed', 'confirmation', 'original', 'incoming'}
MAX_BYTES = 16 * 1024**2
MAX_NODES = 2_000_000
MAX_FOLDS = 8
INSTALLED_ROOT = Path(__file__).resolve().parents[1]


class _Invalid(ValueError):
    pass


def _fields(value, expected):
    if type(value) is not dict or set(value) != expected:
        raise _Invalid('EXACT_FIELDS_REQUIRED')


def _owned(value, check):
    """Validate exact builtins before copying/encoding or invoking older helpers."""
    nodes = 0
    def copy(item, depth):
        nonlocal nodes
        check()
        nodes += 1
        if nodes > MAX_NODES or depth > 24:
            raise pi.InputCapacityError('JSON_CAPACITY_BLOCKED')
        kind = type(item)
        if kind is dict:
            result = {}
            for key, val in item.items():
                if type(key) is not str or len(key) > 512:
                    raise _Invalid('JSON_STRING_KEYS_REQUIRED')
                result[key] = copy(val, depth+1)
            return result
        if kind is list:
            return [copy(val, depth+1) for val in item]
        if kind is str:
            if len(item) > 1024*1024:
                raise pi.InputCapacityError('JSON_STRING_CAPACITY_BLOCKED')
            return item
        if kind is bool or item is None:
            return item
        if kind is int:
            if item.bit_length() > 256:
                raise _Invalid('JSON_INTEGER_LIMIT')
            return item
        if kind is float and math.isfinite(item):
            return item
        raise _Invalid('BUILTIN_JSON_REQUIRED')
    result = copy(value, 0)
    _digest(result, check)
    return result


def _digest(value, check):
    sha, size = hashlib.sha256(), 0
    for part in json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                 allow_nan=False).iterencode(value):
        check()
        raw = part.encode('utf-8')
        size += len(raw)
        if size > MAX_BYTES:
            raise pi.InputCapacityError('JSON_BYTE_CAPACITY_BLOCKED')
        sha.update(raw)
    check()
    return sha.hexdigest()


def _no_reveal(value, check):
    pending = [value]
    while pending:
        check()
        item = pending.pop()
        if type(item) is dict:
            path = item.get('path')
            if type(path) is str and any(p.casefold() in RESERVED for p in path.split('/')):
                raise _Invalid('RESERVED_SOURCE_NAMESPACE')
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)


def _read(reader, ref):
    _no_reveal(ref, reader.context.check)
    value = reader.read(ref)
    value = _owned(value, reader.context.check)
    _no_reveal(value, reader.context.check)
    return value


def _remember(reader, bindings):
    """Bind every helper-consumed file now, then reread it again at completion."""
    for path, sha in bindings.items():
        reader.context.check()
        _no_reveal({'path': path}, reader.context.check)
        target = pi._local_path(reader.root, path, reader.context.check)
        ref = dict(path=path, sha256=sha, size_bytes=target.stat().st_size)
        reader.read(ref, parse=False)


def _code(reader, manifest):
    paths = cycle.code_paths(INSTALLED_ROOT)
    if type(manifest) is not dict or set(manifest) != set(paths):
        raise _Invalid('CODE_CLOSURE_MISMATCH')
    for path in paths:
        reader.context.check()
        sha = manifest[path]
        if type(sha) is not str or not pi.SHA256.fullmatch(sha):
            raise _Invalid('CODE_CLOSURE_MISMATCH')
        installed = pi._local_path(INSTALLED_ROOT, path, reader.context.check)
        raw = pi._bounded_bytes(installed, pi._LocalByteBudget(reader.context,
            pi.MAX_SOURCE_BYTES), reader.context.check)
        if hashlib.sha256(raw).hexdigest() != sha:
            raise _Invalid('CODE_CLOSURE_MISMATCH')
        reader.read(dict(path=path, sha256=sha, size_bytes=len(raw)), parse=False)
    reader.context.check()


def _unit(row):
    return row['cell_x'], row['cell_y'], pi._time(row['window_start_jst'])


def _spatial(forecast, candidate, ledger, check):
    """Coordinate bins and complete individual denominator; no new threshold."""
    if ledger is None:
        return {}
    scores = {u['row_id']: u['spatial_score'] for u in candidate['prediction']['unit_predictions']}
    events = ledger['events']
    denominator = sum(len(event['individual_ids']) for event in events)
    result = {}
    for size in (500, 250, 100):
        grouped = {}
        for row in forecast['rows']:
            check()
            # G0 supplies explicit point geometry; never infer a point from ranks.
            key = model_evaluation._area(row,size)
            grouped.setdefault(key, []).append(scores[row['row_id']])
        ranking = sorted(grouped, key=lambda key: (-math.fsum(grouped[key])/len(grouped[key]), key))[:10]
        numerator = 0
        for event in events:
            check()
            key = model_evaluation._area(event,size)
            if key in ranking:
                numerator += len(event['individual_ids'])
        result[str(size)+'m'] = dict(numerator=numerator, denominator=denominator,
            recall=numerator/denominator if denominator else None,
            top10_cells=[[int(axis) for axis in key.split(',')] for key in ranking], gate_outcome='NOT_EVALUATED',
            validity_status='NOT_VALIDATED', reason='POLICY_THRESHOLD_UNSPECIFIED')
    return result


def _observation(root, admission, reader, definition):
    profile = admission['profile']
    args = profile['observation_selector']
    selected = training.select_g0_training_rows(root, profile['observation_manifest'],
        args['heldout_night'], args['fit_cutoff'], args['forecast_cutoff'],
        expected_feature_definition_sha256=definition, exposed_nights=tuple(args['exposed_nights']),
        budget_seconds=reader.context.remaining_seconds, _read_context=reader.context)
    _remember(reader, selected['receipt']['consumed_sha256'])
    return selected['selection']


def _project_observation(observed, future, check):
    """Explicit physical-unit ID alias, leaving the source selection unchanged."""
    projected = _owned(observed, check)
    rows = {_unit(row): row for row in future}
    aliases = []
    for row in projected['accepted']:
        check()
        original = rows.get(_unit(row))
        if original is None or row['features'] != original['features']:
            raise _Invalid('OBSERVATION_FORECAST_UNIT_MISMATCH')
        aliases.append(dict(source_row_id=row['row_id'], forecast_row_id=original['row_id']))
        row['row_id'] = original['row_id']
    projected['selection_sha256'] = _digest({key:projected[key] for key in IDENTITY_FIELDS}, check)
    models.validate_selection(projected)
    return projected, dict(source_selection_sha256=observed['selection_sha256'],
        projected_selection_sha256=projected['selection_sha256'], row_aliases=aliases)


def _match_observation_ledger(observed, ledger, check):
    """Complete binary outcome scopes and canonical ledger must agree exactly."""
    by_unit={}
    for event in ledger['events']:
        check()
        instant=pi._time(event['datetime']).astimezone(pi.JST)
        start=instant.replace(minute=instant.minute//10*10,second=0,microsecond=0)
        unit=math.floor(event['utm_x_m']/100),math.floor(event['utm_y_m']/100),start
        by_unit.setdefault(unit,set()).add(event['event_id'])
    for row in observed['accepted']:
        check()
        if set(row['capture_event_ids'])!=by_unit.get(_unit(row),set()):
            raise _Invalid('OBSERVATION_LEDGER_EVENT_MISMATCH')


def _paired(folds, check):
    values = [fold['comparison']['mean_brier_improvement'] for fold in folds if 'comparison' in fold]
    missing = [fold['fold_id'] for fold in folds if 'comparison' not in fold]
    coverage = dict(cohort_complete=not missing,missing_fold_ids=missing,
                    expected_fold_count=len(folds),scope='AVAILABLE_DEVELOPMENT_NIGHTS_ONLY')
    if not values:
        return dict(status='NOT_VALIDATED', paired_nights=0, interval_95=None,**coverage)
    rng, draws = random.Random(1642), []
    for _ in range(2000):
        check()
        draws.append(math.fsum(rng.choices(values, k=len(values)))/len(values))
    draws.sort()
    return dict(status='DESCRIPTIVE_DEVELOPMENT_ONLY', paired_nights=len(values),
        mean_brier_improvement=math.fsum(values)/len(values), interval_95=[draws[49],draws[1949]],
        method='EXISTING_MODEL_EVALUATION_NIGHT_BOOTSTRAP', replicates=2000, seed=1642,
        confidence=.95, independent_confirmation=False, gate_outcome='NOT_EVALUATED',**coverage)


def _combine_stage1(projections, config, check):
    """One full-cohort computation enforces global event/individual uniqueness."""
    projections = _owned(projections, check)
    universe = dict(schema_version='habu-stage1-universe-v1', nights=[])
    ledger = dict(schema_version='habu-stage1-ledger-v1', source_refs=[],
                  complete_scopes=[], events=[])
    refs, candidates = {}, None
    lineage = {}
    for projection in projections:
        check()
        universe['nights'].extend(projection['universe']['nights'])
        source = projection['ledger']
        for ref in source['source_refs']:
            path = ref['path']
            if path in refs and refs[path] != ref:
                raise _Invalid('COHORT_SOURCE_BINDING_CONFLICT')
            refs[path] = ref
        ledger['complete_scopes'].extend(source['complete_scopes'])
        ledger['events'].extend(source['events'])
        current = projection['scores']['candidates']
        ids = [c['candidate_id'] for c in current]
        if candidates is None:
            candidates = [{k:v for k,v in c.items() if k!='scores'} | {'scores':{}}
                          for c in current]
        if ids != [c['candidate_id'] for c in candidates]:
            raise _Invalid('COHORT_CANDIDATE_SET_MISMATCH')
        for target, item in zip(candidates,current):
            ident = item['candidate_id']
            for key in ('score_semantics','candidate_config_sha256','recipe_sha256'):
                if item[key] != target[key]:
                    raise _Invalid('COHORT_RECIPE_SEMANTICS_MISMATCH')
            for night, values in item['scores'].items():
                if night in target['scores']:
                    raise _Invalid('COHORT_NIGHT_REUSED')
                target['scores'][night] = values
                lineage.setdefault(ident,{})[night] = dict(model_sha256=item['model_sha256'],
                    prediction_sha256=item['prediction_sha256'])
    for candidate in candidates:
        binding = lineage[candidate['candidate_id']]
        candidate['model_sha256'] = _digest({n:v['model_sha256'] for n,v in binding.items()},check)
        candidate['prediction_sha256'] = _digest({n:v['prediction_sha256'] for n,v in binding.items()},check)
    universe['nights'].sort(key=lambda row:row['operational_night'])
    ledger['source_refs'] = [refs[p] for p in sorted(refs)]
    ledger['ledger_sha256'] = _digest(ledger,check)
    scores = dict(schema_version='habu-stage1-scores-v2',universe_sha256=_digest(universe,check),
        candidate_config_sha256=_digest(config,check),
        feature_definition_sha256=config['feature_definition_sha256'],candidates=candidates)
    result = stage1_pure.evaluate_full_ledger_stage1_v2(universe,scores,ledger,
        candidate_config=config,expected_config_sha256=_digest(config,check),
        feature_definition_sha256=config['feature_definition_sha256'],budget_seconds=300,check=check)
    result.pop('receipt_sha256')
    result['fold_model_lineage'] = lineage
    result['model_binding_semantics'] = 'FOLD_MODEL_COLLECTION_DIGEST_NOT_SINGLE_FITTED_MODEL'
    result['receipt_sha256'] = _digest(result,check)
    return result


def _composite(fold, candidate, forecast, reader, result, code_manifest):
    refs = [fold[key] for key in ('composite_model_ref','inference_bundle_ref','frozen_prediction_ref')]
    if any(ref is None for ref in refs):
        result['data_blockers'].append('COMPOSITE_REPRODUCTION_INPUTS_NOT_SUPPLIED')
        return dict(status='BLOCKED')
    model, inputs, frozen = [_read(reader, ref) for ref in refs]
    try:
        import composite_inference as composite
    except ModuleNotFoundError as exc:
        if exc.name != 'composite_inference':
            raise
        result['implementation_blockers'].append('SHARED_COMPOSITE_PREDICTOR_NOT_AVAILABLE')
        return dict(status='BLOCKED')
    # Reuse the shared contract fields; validate containers before .get/.items.
    _fields(model,composite.MODEL_FIELDS)
    _fields(inputs,composite.BUNDLE_FIELDS)
    components = model['components']
    if type(components) is not list or not components:
        raise _Invalid('COMPOSITE_CONTAINER_SCHEMA_REQUIRED')
    if type(model['code_manifest']) is not dict or type(model['output_bindings']) is not dict:
        raise _Invalid('COMPOSITE_CONTAINER_SCHEMA_REQUIRED')
    for field in ('artifacts','inputs','artifact_available_at','input_available_at'):
        if type(inputs[field]) is not dict:
            raise _Invalid('COMPOSITE_CONTAINER_SCHEMA_REQUIRED')
    for item in components:
        _fields(item,composite.COMPONENT_FIELDS)
        if type(item['dependencies']) is not dict:
            raise _Invalid('COMPOSITE_CONTAINER_SCHEMA_REQUIRED')
        for field in ('component_id','adapter_id','adapter_version','role'):
            if type(item[field]) is not str or not item[field] or len(item[field])>128:
                raise _Invalid('COMPOSITE_COMPONENT_ID_REQUIRED')
        for field in ('state_sha256','config_sha256','input_schema_sha256','output_schema_sha256'):
            if type(item[field]) is not str or not pi.SHA256.fullmatch(item[field]):
                raise _Invalid('COMPOSITE_COMPONENT_HASH_REQUIRED')
    if len(components) != 1 or components[0]['adapter_id'] != 'hba1_unit_v1':
        result['implementation_blockers'].append('COMPOSITE_REPRODUCTION_SHAPE_NOT_SUPPORTED')
        return dict(status='BLOCKED')
    component = components[0]
    if model['policy_sha256'] != cycle.POLICY_DIGEST:
        raise _Invalid('COMPOSITE_POLICY_SOURCE_MISMATCH')
    if any(code_manifest.get(path)!=sha for path,sha in model['code_manifest'].items()):
        raise _Invalid('COMPOSITE_CODE_SOURCE_MISMATCH')
    if 'locked_protocol' in result and model['protocol_sha256']!=result['locked_protocol']['protocol_sha256']:
        raise _Invalid('COMPOSITE_PROTOCOL_SOURCE_MISMATCH')
    if (set(inputs['artifact_available_at'])!=set(inputs['artifacts']) or
            set(inputs['input_available_at'])!=set(inputs['inputs'])):
        raise _Invalid('COMPOSITE_AVAILABILITY_SCHEMA_REQUIRED')
    if component['state_sha256']!=_digest(candidate['model'],reader.context.check):
        raise _Invalid('COMPOSITE_STATE_REFIT_MISMATCH')
    if component['config_sha256']!=_digest({},reader.context.check):
        raise _Invalid('COMPOSITE_CONFIG_SOURCE_MISMATCH')
    if component['config_sha256'] in inputs['artifacts']:
        _fields(inputs['artifacts'][component['config_sha256']],set())
    missing=[]
    if component['state_sha256'] not in inputs['artifacts']:
        missing.append('COMPOSITE_FITTED_STATE_NOT_SUPPLIED')
    if component['config_sha256'] not in inputs['artifacts']:
        missing.append('COMPOSITE_CONFIG_NOT_SUPPLIED')
    if component['component_id'] not in inputs['inputs']:
        missing.append('COMPOSITE_COMPONENT_INPUT_NOT_SUPPLIED')
    actual_input = inputs['inputs'].get(component['component_id'])
    expected_input = dict(forecast_rows=forecast['rows'],
        joined_universe_sha256=forecast['receipt']['canonical_joined_rows_sha256'],
        cutoff_time=fold['forecast_cutoff'])
    if (inputs['operational_night'] != fold['operational_night'] or
            pi._time(inputs['cutoff_time']) != pi._time(fold['forecast_cutoff'])):
        raise _Invalid('COMPOSITE_INPUT_SOURCE_MISMATCH')
    manifest=_read(reader,fold['forecast_manifest_ref'])
    if pi._time(inputs['forecast_end'])!=pi._time(manifest['horizon']['end']):
        raise _Invalid('COMPOSITE_HORIZON_SOURCE_MISMATCH')
    if component['component_id'] in inputs['inputs']:
        if _digest(actual_input,reader.context.check)!=_digest(expected_input,reader.context.check):
            raise _Invalid('COMPOSITE_INPUT_SOURCE_MISMATCH')
        if (pi._time(inputs['input_available_at'][component['component_id']]) <
                pi._time(manifest['usable_at'])):
            raise _Invalid('COMPOSITE_INPUT_READINESS_SOURCE_MISMATCH')
    if component['state_sha256'] in inputs['artifacts']:
        state=inputs['artifacts'][component['state_sha256']]
        if _digest(state,reader.context.check)!=component['state_sha256']:
            raise _Invalid('COMPOSITE_STATE_REFIT_MISMATCH')
    if missing:
        result['data_blockers'].extend(missing)
        return dict(status='BLOCKED')
    actual = composite.predict_composite(model, inputs, budget_seconds=reader.context.remaining_seconds)
    port=actual.get('outputs',{}).get('unit_predictions',{})
    if actual.get('status')=='FAIL' or port.get('execution_status')!='EXECUTED':
        raise _Invalid('COMPOSITE_PREDICTOR_DID_NOT_EXECUTE')
    if _digest(actual, reader.context.check) != _digest(frozen, reader.context.check):
        raise _Invalid('COMPOSITE_PREDICTION_MISMATCH')
    return dict(status='NUMERIC_REPRODUCED' if actual['status']=='EXECUTED' else 'PARTIAL_NUMERIC_REPRODUCED',
        predictor_execution_status=actual['status'],
        prediction_sha256=_digest(actual, reader.context.check))


def _fold(root, fold, request, reader, result, ablation_inputs, projections, training_units):
    check, context = reader.context.check, reader.context
    output = dict(fold_id=fold['fold_id'], operational_night=fold['operational_night'])
    missing = False
    for field, reason in (('training_manifest_ref','TRAINING_MANIFEST_NOT_SUPPLIED'),
                           ('forecast_manifest_ref','FORECAST_MANIFEST_NOT_SUPPLIED')):
        if fold[field] is None:
            result['data_blockers'].append(reason)
            missing = True
    if request['candidate_config_ref'] is None:
        result['data_blockers'].append('CANDIDATE_CONFIG_NOT_SUPPLIED')
        missing = True
    if missing:
        return output
    # Preflight every top-level source manifest's nested namespaces before gates.
    for field in ('training_manifest_ref','forecast_manifest_ref'):
        _read(reader, fold[field])
    _read(reader, request['candidate_config_ref'])
    definition = fold['feature_definition_sha256']
    config_result = configuration.load_research_candidate_config(root, request['candidate_config_ref'],
        heldout_night=fold['operational_night'], fit_cutoff=fold['fit_cutoff'],
        forecast_cutoff=fold['forecast_cutoff'], expected_feature_definition_sha256=definition,
        context=context)
    config = config_result['config']
    _remember(reader, config_result['receipt']['consumed_sha256'])
    actual_training = training.select_g0_training_rows(root, fold['training_manifest_ref'],
        fold['operational_night'], fold['fit_cutoff'], fold['forecast_cutoff'],
        expected_feature_definition_sha256=definition, budget_seconds=context.remaining_seconds,
        _read_context=context)
    _remember(reader, actual_training['receipt']['consumed_sha256'])
    selected = actual_training['selection']
    output['training_counts'] = selected['counts']
    result['fit_training_row_memberships'] += selected['counts']['accepted_rows']
    for row in selected['accepted']:
        check()
        key=(row['night'],*_unit(row))
        if key in training_units and training_units[key]!=row['label']:
            raise _Invalid('COHORT_TRAINING_LABEL_CONFLICT')
        training_units[key]=row['label']
    result['development_training_unique_units']=len(training_units)
    forecast = g0.load_g0_forecast_rows(root, fold['forecast_manifest_ref'],fold['operational_night'],
        pi._time(fold['forecast_as_of']), expected_feature_definition_sha256=definition,
        budget_seconds=context.remaining_seconds, _read_context=context)
    _remember(reader, forecast['receipt']['consumed_sha256'])
    if pi._time(forecast['receipt']['cutoff_time']) != pi._time(fold['forecast_cutoff']):
        raise _Invalid('FORECAST_CUTOFF_MISMATCH')
    prepared = models.prepare_research_candidates_v2(selected,forecast['rows'],candidate_config=config,
        expected_config_sha256=_digest(config,check),cutoff_time=fold['forecast_cutoff'],
        joined_universe_sha256=forecast['receipt']['canonical_joined_rows_sha256'],
        feature_definition_sha256=definition,budget_seconds=context.remaining_seconds,check=check)
    if prepared['status'] != 'DIAGNOSTIC_CANDIDATES_PREPARED':
        result['data_blockers'].append('INSUFFICIENT_QUALIFIED_RECIPE_TRAINING')
        output['refit'] = dict(status='BLOCKED', blockers=prepared['blockers'])
        return output
    candidate = next((c for c in prepared['candidates'] if c['candidate_id']=='HB-A1'),None)
    if candidate is None:
        raise _Invalid('SELECTED_RECIPE_NOT_IN_FIXED_CONFIG')
    output['refit'] = dict(status='NUMERIC_REPRODUCED', prepared_sha256=prepared['receipt_sha256'],
        model_sha256=candidate['model_sha256'], prediction_sha256=candidate['prediction_sha256'],
        recipe_sha256=candidate['model']['recipe_sha256'])
    if fold['expected_prepared_ref'] is None:
        result['data_blockers'].append('EXPECTED_PREPARED_NOT_SUPPLIED')
        output['refit']['expected_state_comparison']='NOT_SUPPLIED'
        output['refit']['status']='NUMERIC_RECOMPUTED'
    elif _digest(_read(reader,fold['expected_prepared_ref']),check) != _digest(prepared,check):
        raise _Invalid('REFIT_OUTPUT_MISMATCH')
    else:
        output['refit']['expected_state_comparison']='EXACT'
    output['inference_reproduction'] = _composite(fold,candidate,forecast,reader,result,request['code_manifest'])
    projection = None
    if fold['stage1_manifest_ref'] is None:
        result['data_blockers'].append('FULL_OUTCOME_MANIFEST_NOT_SUPPLIED')
    else:
        _read(reader,fold['stage1_manifest_ref'])
        projection = stage1_source.project_stage1_sources_v2(root,fold['stage1_manifest_ref'],forecast,prepared,
            candidate_config=config,expected_config_sha256=_digest(config,check),
            feature_definition_sha256=definition,context=context)
        output['stage1'] = projection['stage1_result']
        _remember(reader,output['stage1']['source_receipt']['consumed_sha256'])
        if output['stage1']['status']=='NEED_MORE_DATA':
            result['data_blockers'].append('COMPLETE_INDEPENDENT_INDIVIDUAL_LEDGER_NOT_ESTABLISHED')
        else:
            output['spatial'] = _spatial(forecast,candidate,projection['ledger'],check)
            projections.append((projection,config))
    if fold['calibration_manifest_ref'] is None:
        result['data_blockers'].append('OBSERVATION_CALIBRATION_MANIFEST_NOT_SUPPLIED')
    else:
        admission = calibration.preflight(root,fold['calibration_manifest_ref'],context=context)
        _no_reveal(admission['profile'],check)
        calibrated = calibration.evaluate(root,admission,forecast,prepared,actual_training,config,
            expected_config_sha256=_digest(config,check),feature_definition_sha256=definition,context=context)
        _remember(reader,calibrated['source_receipt']['consumed_sha256'])
        output['proper_scores'] = calibrated['diagnostic']
        observed = _observation(root,admission,reader,definition)
        output['observation_counts'] = observed['counts']
        if projection is not None and output['stage1']['status']!='NEED_MORE_DATA':
            _match_observation_ledger(observed,projection['ledger'],check)
        uniform = prepared['candidates'][0]
        future = {_unit(r):r for r in forecast['rows']}
        probabilities = {u['row_id']:u['probability'] for u in uniform['prediction']['unit_predictions']}
        errors = [(probabilities[future[_unit(row)]['row_id']]-row['label'])**2
                  for row in observed['accepted']]
        baseline = math.fsum(errors)/len(errors)
        output['comparison'] = dict(comparator='uniform', baseline_brier=baseline,
            mean_brier_improvement=baseline-output['proper_scores']['mean_night_brier'])
        projected, alias = _project_observation(observed,forecast['rows'],check)
        output['ablation_observation_alias'] = alias
        ablation_inputs.append(dict(night=fold['operational_night'],training_selection=selected,
            forecast_rows=forecast['rows'],evaluation_selection=projected))
    return output


def _run(bundle, policy, root, context, result):
    check = context.check
    request, policy = _owned([bundle,policy],check)
    _fields(request,REQUEST_FIELDS)
    if (request['schema_version']!='habu-promotion-reproduction-request-v1' or
            request['purpose']!='DEVELOPMENT_REPRODUCTION_ONLY'):
        raise _Invalid('DEVELOPMENT_HBA1_REPRODUCTION_REQUIRED')
    selected_id=request['selected_candidate_id']
    if (type(selected_id) is not str or not selected_id or len(selected_id)>128 or
            not selected_id.isprintable()):
        raise _Invalid('PRINTABLE_RECIPE_ID_REQUIRED')
    result['input_digests']=dict(request=_digest(request,check),policy=_digest(policy,check))
    if _digest(policy,check)!=cycle.POLICY_DIGEST or request['policy_sha256']!=cycle.POLICY_DIGEST:
        raise _Invalid('FROZEN_POLICY_MISMATCH')
    _no_reveal(request,check)
    folds=request['folds']
    if type(folds) is not list or not folds or len(folds)>MAX_FOLDS:
        raise _Invalid('BOUNDED_FOLDS_REQUIRED')
    identities,nights=set(),[]
    for fold in folds:
        _fields(fold,FOLD_FIELDS)
        ident=fold['fold_id']
        if type(ident) is not str or not ident or len(ident)>80 or ident in identities:
            raise _Invalid('DUPLICATE_OR_INVALID_FOLD')
        identities.add(ident)
        validate_night(fold['operational_night'])
        nights.append(fold['operational_night'])
        for key in ('fit_cutoff','forecast_cutoff','forecast_as_of'):
            pi._time(fold[key])
    if nights!=sorted(set(nights)):
        raise _Invalid('UNIQUE_SORTED_FOLD_NIGHTS_REQUIRED')
    if selected_id!='HB-A1':
        result['execution_status']='BLOCKED'
        result['reason_code']='RECIPE_SOURCE_REPRODUCTION_NOT_IMPLEMENTED'
        result['implementation_blockers'].append('RECIPE_SOURCE_REPRODUCTION_NOT_IMPLEMENTED')
        return
    reader=g0.G0ArtifactReader(root,context)
    _code(reader,request['code_manifest'])
    if request['protocol_ref'] is None or request['exposure_history_ref'] is None:
        result['data_blockers'].append('LOCKED_PROTOCOL_OR_EXPOSURE_HISTORY_NOT_SUPPLIED')
    else:
        plan=_read(reader,request['protocol_ref'])
        history=_read(reader,request['exposure_history_ref'])
        result['locked_protocol']=validate_locked_protocol(plan,history)
        if plan['selected_recipe']!=request['selected_candidate_id']:
            raise _Invalid('LOCKED_RECIPE_SELECTION_MISMATCH')
        declared={c['operational_night'] for c in plan['forecast_cohorts']}
        if declared!=set(nights) or any(f['purpose']!='DEVELOPMENT_FORECAST' for f in plan['folds']):
            raise _Invalid('DEVELOPMENT_PROTOCOL_FOLD_COVERAGE_MISMATCH')
    ablation_inputs,projections,training_units=[],[],{}
    for fold in folds:
        check()
        result['folds'].append(_fold(root,fold,request,reader,result,ablation_inputs,projections,training_units))
    if request['ablation_protocol_ref'] is None:
        result['data_blockers'].append('ABLATION_PROTOCOL_NOT_SUPPLIED')
    elif len(ablation_inputs)!=len(folds):
        result['data_blockers'].append('ABLATION_SOURCE_OBSERVATIONS_INCOMPLETE')
    else:
        protocol=_read(reader,request['ablation_protocol_ref'])
        recipe_sha=_digest(protocol['base_recipe'],check)
        if any(fold.get('refit',{}).get('recipe_sha256')!=recipe_sha for fold in result['folds']):
            raise _Invalid('ABLATION_RECIPE_MISMATCH')
        result['ablation']=hba1.describe_retrained_ablations(protocol,ablation_inputs,
            expected_protocol_sha256=_digest(protocol,check),budget_seconds=context.remaining_seconds,check=check)
        if result['ablation']['status']=='DESCRIPTIVE_RETRAINED_ABLATION_ONLY':
            expected={fold['operational_night']:fold['refit']['model_sha256'] for fold in result['folds']}
            if any(fold['full']['model_sha256']!=expected.get(fold['night'])
                   for fold in result['ablation']['fold_results']):
                raise _Invalid('ABLATION_FULL_MODEL_REFIT_MISMATCH')
    if len(projections)==len(folds):
        config=projections[0][1]
        if any(_digest(c,check)!=_digest(config,check) for _,c in projections):
            raise _Invalid('COHORT_CONFIG_CHANGED')
        result['cohort_stage1']=_combine_stage1([p for p,_ in projections],config,check)
    result['comparison']=_paired(result['folds'],check)
    result['coverage']=dict(development_nights=nights,development_years=sorted({n[:4] for n in nights}),
        confirmation_nights=[],cross_year_status='NOT_VALIDATED')
    result['computed_gates']={}
    counts=[f['stage1']['pooled']['HB-A1'] for f in result['folds']
            if 'stage1' in f and f['stage1']['status']!='NEED_MORE_DATA']
    if len(counts)==len(folds):
        numerator=sum(item['numerator'] for item in counts)
        denominator=sum(item['denominator'] for item in counts)
        result['computed_gates']['stage1']=dict(numerator=numerator,denominator=denominator,
            recall=numerator/denominator if denominator else None,threshold=.9,
            numeric_threshold_met=numerator/denominator>=.9 if denominator else None,
            validity_status='NOT_VALIDATED',gate_outcome='NOT_EVALUATED')
    # Recheck all inputs, source closures and installed code after every numeric job.
    _code(reader,request['code_manifest'])
    reader.rescan()
    result['consumed_input_recheck_complete']=True
    result['consumed_sha256']={p:r['sha256'] for p,r in sorted(reader.refs.items())}
    result['actual_read_bytes']=context.bytes_read
    done=any('refit' in fold and fold['refit']['status'] in ('NUMERIC_REPRODUCED','NUMERIC_RECOMPUTED')
             for fold in result['folds'])
    result['execution_status']='PARTIAL' if done else 'BLOCKED'
    result['reason_code']='DEVELOPMENT_NUMERICS_REPRODUCED' if done else 'REQUIRED_INPUTS_BLOCKED'
    check()


def reproduce_candidate(bundle, frozen_policy, *, input_root, budget_seconds=300):
    """Execute available DEV calculations and return structured fail-closed facts."""
    result=dict(schema_version=VERSION,execution_status='FAIL',validity_status='NOT_VALIDATED',
        gate_outcome='NOT_EVALUATED',decision='NEED_MORE_DATA',reason_code=None,folds=[],
        eligible_training_units=None,development_training_unique_units=None,fit_training_row_memberships=0,
        comparison={},ablation=None,data_blockers=[],runtime_blockers=[],consumed_input_recheck_complete=False,
        implementation_blockers=['FORMAL_TARGET_GENERATOR_NOT_REGISTERED'],discrepancies=[],
        required_conditions=['TRUSTED_PRE_REVEAL_FREEZE_AND_GLOBAL_CONSUMPTION_PROOF',
            'FIVE_UNTOUCHED_CONFIRMATION_NIGHTS_AND_CROSS_YEAR_SUPPORT',
            'SPATIAL_CALIBRATION_DRIFT_ACCURACY_THRESHOLDS_UNSPECIFIED',
            'TRUSTED_CUMULATIVE_CAMPAIGN_BUDGET_LEDGER',
            'LOCKED_PROTOCOL_GROUP_SOURCE_PROJECTIONS_AND_AUTHENTICATION_NOT_ESTABLISHED',
            'EXACT_CODE_CI_REVIEW_VERIFICATION_SEPARATE_FROM_NUMERIC_REPRODUCTION'],
        confirmation=dict(status='NOT_VALIDATED',consumption_authenticated=False),
        source_authentication='NOT_ATTESTED',scientific_authorized=False,confirmation_authorized=False,
        selection_authorized=False,promotion_authorized=False,official_issuance_authorized=False,
        production_authorized=False,consumed_sha256={},runtime=dict(python=sys.version.split()[0]))
    sealed=False
    try:
        kind=type(budget_seconds)
        if (kind is not int and kind is not float or not 0<budget_seconds<=300 or
                not math.isfinite(budget_seconds)):
            raise _Invalid('INVALID_BUDGET')
        if type(input_root) is not str and type(input_root) is not type(Path()):
            raise _Invalid('CONTROLLER_ROOT_TYPE_REQUIRED')
        context=pi.ProspectiveReadContext(budget_seconds,g0.MAX_TOTAL_READ_BYTES)
        _run(bundle,frozen_policy,Path(input_root),context,result)
        for key in ('data_blockers','runtime_blockers','implementation_blockers','required_conditions'):
            result[key]=sorted(set(result[key]))
        result['receipt_sha256']=_digest(result,context.check)
        context.check()
        sealed=True
    except _Invalid as exc:
        result.update(execution_status='FAIL',validity_status='INVALID',gate_outcome='FAIL',
            decision='REJECT_CANDIDATE',reason_code=str(exc),discrepancies=[str(exc)],folds=[])
    except (training.G0TrainingInputBlocked,configuration.CandidateConfigSourceBlocked,
            calibration.ObservationBlocked) as exc:
        result.update(execution_status='BLOCKED',reason_code='SOURCE_QUALIFICATION_BLOCKED')
        result['data_blockers'].append('SOURCE_QUALIFICATION_BLOCKED')
    except (FileNotFoundError,NotADirectoryError):
        result.update(execution_status='BLOCKED',reason_code='REFERENCED_INPUT_NOT_AVAILABLE')
        result['data_blockers'].append('REFERENCED_INPUT_NOT_AVAILABLE')
    except (TimeoutError,pi.InputCapacityError,models.ResearchBudgetExhausted,models.ResearchCapacityBlocked,
            stage1_pure.Stage1CapacityBlocked,stage1_pure.Stage1BudgetBlocked,hba1.HBA1CapacityBlocked):
        result.update(execution_status='BLOCKED',reason_code='RESOURCE_BUDGET_BLOCKED')
        result['runtime_blockers'].append('RESOURCE_BUDGET_BLOCKED')
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,OSError,RecursionError,UnicodeError):
        result.update(execution_status='FAIL',validity_status='INVALID',gate_outcome='FAIL',
            decision='REJECT_CANDIDATE',reason_code='SOURCE_VALIDATION_FAILED',
            discrepancies=['SOURCE_VALIDATION_FAILED'],folds=[])
    if not sealed:
        # A changed source/deadline cannot leave a usable stale computed bundle.
        for key in ('cohort_stage1','computed_gates','coverage','locked_protocol','receipt_sha256'):
            result.pop(key,None)
        result.update(folds=[],comparison={},ablation=None,eligible_training_units=None,
            development_training_unique_units=None,fit_training_row_memberships=None,
            consumed_input_recheck_complete=False,consumed_sha256={})
    for key in ('data_blockers','runtime_blockers','implementation_blockers','required_conditions'):
        result[key]=sorted(set(result[key]))
    return result
