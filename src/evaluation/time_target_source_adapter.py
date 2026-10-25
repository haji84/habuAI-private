"""Declared G0 cell-centre T2 consistency, never source or prereveal truth."""
from datetime import timedelta

import g0_forecast_contract as g0
from master_inventory import local_path
import prospective_inputs as pi
import research_model_adapter as models
import time_target_evaluation as t2
from evaluation import full_ledger_stage1 as pure
from evaluation import stage1_source_adapter as source

VERSION='habu-time-target-source-diagnostic-v1'
MAX_PROTOCOL_BYTES=64*1024
MAX_TARGET_BYTES=256*1024
COUNTERS={'actual_read_bytes','validation_read_bytes'}
RESERVED={'original','incoming','reports','sealed','confirmation'}


def _hash(value,check):
    return pure._digest(value,check)


def _guard(root,ref):
    g0._ref(ref)
    path=ref['path']
    if (any(part.casefold() in RESERVED for part in path.split('/')) or
            any(ord(c)<32 or ord(c)==127 for c in path)):
        raise ValueError('Reserved time-target source reference')
    local_path(root,path)


def _put(refs,ref):
    ref=dict(ref)
    g0._ref(ref)
    previous=refs.get(ref['path'])
    if previous is not None and previous!=ref:
        raise ValueError('Conflicting time-target source byte bindings')
    refs[ref['path']]=ref


def _bound(root,value,maximum,cutoff,*,parents=(),fit=None):
    g0._object(value,g0.BOUND_FIELDS,'Prior time-target bound reference')
    ref=g0._base_ref(value)
    source._export_ref(root,ref)
    if ref['size_bytes']>maximum:
        raise pi.InputCapacityError('CAPACITY_BLOCKED: time-target source file')
    ready=g0.validate_readiness(value['readiness'],value['usable_at'],cutoff,parent_usable_at=parents)
    if fit is not None and any(g0._stamp(stamp)<fit for stamp in value['readiness'].values()):
        raise ValueError('Target availability precedes admitted native fit cutoff')
    return ref,ready


def _stable(receipt):
    for key in COUNTERS:
        if type(receipt.get(key)) is not int or receipt[key]<0:
            raise ValueError('Exact nonnegative forecast read counters required')
    if receipt['validation_read_bytes']>receipt['actual_read_bytes']:
        raise ValueError('Forecast read counters contradict each other')
    return {key:value for key,value in receipt.items() if key not in COUNTERS}


def _revalidate(root,forecast,definitions,context,reader,refs):
    check=context.check
    ref=forecast['receipt']['manifest_ref']
    source._export_ref(root,ref)
    # G0 keeps role-specific namespaces (including exact OSM parts). This
    # metadata-only preflight adds no read permission and no ref-size inference.
    manifest=pure._copy_json(reader.read(ref,small=True),check)
    pending=[manifest]
    while pending:
        check(); value=pending.pop()
        if type(value) is dict:
            if g0.REF_FIELDS<=value.keys():
                bound=g0._base_ref(value); _guard(root,bound); _put(refs,bound)
            pending.extend(value.values())
        elif type(value) is list:
            pending.extend(value)
    loaded=g0.load_g0_forecast_rows(root,ref,forecast['receipt']['operational_night'],
        pi._time(forecast['receipt']['cutoff_time']),expected_feature_definition_sha256=definitions,
        budget_seconds=min(pi.MAX_BUDGET_SECONDS,context.remaining_seconds),_read_context=context)
    if (_hash(loaded['rows'],check)!=_hash(forecast['rows'],check) or
            _hash(_stable(loaded['receipt']),check)!=_hash(_stable(forecast['receipt']),check)):
        raise ValueError('Complete forecast source revalidation differs from owned declaration')
    check()
    return loaded['receipt']


def _point_universe(bundle,forecast,check):
    if bundle['universe'] is None:
        return None
    night=bundle['universe']['nights'][0]
    result=dict(schema_version='habu-time-target-universe-v1',
        **{key:night[key] for key in ('operational_night','cutoff_time','horizon_start','horizon_end',
            'scope','scope_sha256')},forecast_receipt_sha256=_hash(forecast['receipt'],check),
        joined_forecast_sha256=forecast['receipt']['canonical_joined_rows_sha256'],units=[])
    for row in forecast['rows']:
        check()
        result['units'].append({key:row[key] for key in ('row_id','window_start_jst','utm_x_m','utm_y_m')})
    result['universe_sha256']=_hash(result,check)
    return result


def _evaluate(root,stage1_manifest_ref,forecast,prepared,*,candidate_config,expected_config_sha256,
        feature_definition_sha256,candidate_id,frozen_targets_ref,protocol_ref,expected_protocol_sha256,context):
    if not isinstance(context,pi.ProspectiveReadContext):
        raise ValueError('Existing shared prospective context required')
    check=context.check; check(); initial=context.bytes_read
    source._prepared_limits(forecast,prepared,check)
    candidate_config,forecast,prepared,stage1_manifest_ref,frozen_targets_ref,protocol_ref=pure._copy_json(
        [candidate_config,forecast,prepared,stage1_manifest_ref,frozen_targets_ref,protocol_ref],check)
    config,admitted=source._configured_export_prepared(candidate_config,forecast,prepared,
        expected_config_sha256,feature_definition_sha256,check)
    forecast,prepared,night,_,_,_=admitted
    if type(candidate_id) is not str or candidate_id not in config['candidate_ids']:
        raise ValueError('Explicit admitted configured candidate required')
    candidate=next(c for c in prepared['candidates'] if c['candidate_id']==candidate_id)
    source._export_ref(root,stage1_manifest_ref)
    source._export_ref(root,forecast['receipt']['manifest_ref'])
    cutoff=pi._time(forecast['receipt']['cutoff_time'])
    target_ref,target_ready=None,None
    if frozen_targets_ref is not None:
        target_ref,target_ready=_bound(root,frozen_targets_ref,MAX_TARGET_BYTES,cutoff,
            fit=g0._stamp(prepared['fit_cutoff']))
    protocol_byte_ref,protocol_ready=_bound(root,protocol_ref,MAX_PROTOCOL_BYTES,cutoff,
        parents=() if target_ready is None else (target_ready,))
    pure._sha(expected_protocol_sha256)
    reader=g0.G0ArtifactReader(root,context); refs={}
    _put(refs,stage1_manifest_ref); _put(refs,forecast['receipt']['manifest_ref'])
    _put(refs,protocol_byte_ref)
    if target_ref is not None: _put(refs,target_ref)
    entry=_revalidate(root,forecast,feature_definition_sha256,context,reader,refs)
    protocol=reader.read(protocol_byte_ref,small=True)
    targets=None if target_ref is None else reader.read(target_ref,small=True)
    t2._known_caps(None,targets,None,check)
    _,targets,_,protocol=t2._owned([None,targets,None,protocol],check)
    times=t2._protocol(protocol,expected_protocol_sha256,check)
    windows,rows=[],{}
    for row in forecast['rows']:
        check(); instant=pi._time(row['window_start_jst']); windows.append(instant)
        rows[row['row_id']]=(instant,row['utm_x_m'],row['utm_y_m'])
    if (protocol['operational_night']!=night or times!=(cutoff,min(windows),max(windows)+timedelta(seconds=600))):
        raise ValueError('Protocol differs from complete strict forecast chronology')
    if protocol['frozen_at'] is not None and g0._stamp(protocol['frozen_at'])<protocol_ready:
        raise ValueError('Declared freeze precedes protocol availability')
    if targets is not None:
        t2._targets(targets,protocol,times,rows,check)
        for key in ('model_sha256','prediction_sha256'):
            if targets[key] is not None and targets[key]!=candidate[key]:
                raise ValueError('External target native input lineage differs from explicit candidate')
    bundle=source.project_stage1_sources_v2(root,stage1_manifest_ref,forecast,prepared,
        candidate_config=config,expected_config_sha256=expected_config_sha256,
        feature_definition_sha256=feature_definition_sha256,context=context)
    universe=_point_universe(bundle,forecast,check)
    result=t2.evaluate_time_targets(universe,targets,bundle['ledger'],protocol=protocol,
        expected_protocol_sha256=expected_protocol_sha256,budget_seconds=min(30,context.remaining_seconds),check=check)
    final=_revalidate(root,forecast,feature_definition_sha256,context,reader,refs)
    for ref in bundle['stage1_result']['source_receipt']['consumed_refs']:
        check(); source._export_ref(root,ref); _put(refs,ref)
    # One final combined reread, using explicit already-bound sizes. Whole G0
    # reloads cover additional nested refs not exposed in its source hash map.
    for ref in refs.values():
        check(); _guard(root,ref); reader.read(ref,parse=False)
    consumed={}
    maps=(entry['consumed_sha256'],final['consumed_sha256'],
        bundle['stage1_result']['source_receipt']['consumed_sha256'],
        {path:ref['sha256'] for path,ref in reader.refs.items()})
    for bindings in maps:
        for path,sha in bindings.items():
            check()
            if path in consumed and consumed[path]!=sha:
                raise ValueError('Conflicting actual consumed source hashes')
            consumed[path]=sha
    projections={key:None if value is None else _hash(value,check) for key,value in
        dict(universe=universe,targets=targets,ledger=bundle['ledger'],stage1_bundle=bundle).items()}
    if {k:projections[k] for k in ('universe','targets','ledger')}!=result['input_digests']:
        raise ValueError('T2 input projections changed before source seal')
    check()
    receipt=dict(candidate_id=candidate_id,input_lineage=dict(
        candidate_config_sha256=expected_config_sha256,feature_definition_sha256=feature_definition_sha256,
        forecast_manifest_ref=forecast['receipt']['manifest_ref'],forecast_receipt_sha256=_hash(forecast['receipt'],check),
        forecast_declaration_sha256=_hash(_stable(forecast['receipt']),check),
        joined_forecast_sha256=forecast['receipt']['canonical_joined_rows_sha256'],
        prepared_input_sha256=_hash(prepared,check),prepared_receipt_sha256=prepared['receipt_sha256'],
        model_sha256=candidate['model_sha256'],prediction_sha256=candidate['prediction_sha256']),
        external_target_selection=dict(origin='CALLER_PROVIDED_DECLARATION',protocol_ref=protocol_ref,
            frozen_targets_ref=frozen_targets_ref,protocol_sha256=expected_protocol_sha256,
            targets_sha256=None if targets is None else targets['targets_sha256'],declared_frozen_at=protocol['frozen_at']),
        projection_sha256=projections,consumed_sha256=consumed,
        forecast_revalidation={key:{counter:value[counter] for counter in COUNTERS} for key,value in
            (('entry',entry),('final',final))},initial_read_bytes=initial,actual_read_bytes=context.bytes_read,
        validation_read_bytes=context.bytes_read-initial)
    outer=pure._copy_json(dict(schema_version=VERSION,purpose='DEVELOPMENT_EVALUATION_ONLY',
        point_geometry='DECLARED_G0_CELL_CENTRE',stage1_bundle=bundle,universe=universe,targets=targets,
        time_target_result=result,source_receipt=receipt,source_authentication='NOT_ATTESTED',
        prereveal_authentication='NOT_ATTESTED',fit_authorized=False,scientific_authorized=False,
        confirmation_authorized=False,selection_authorized=False,promotion_authorized=False,
        production_authorized=False),check)
    outer=pure._finish(outer,check)
    for _ in pure._encoded(outer,check): pass
    check()
    return outer


def evaluate_time_target_sources_v1(root,stage1_manifest_ref,forecast,prepared,*,candidate_config,
        expected_config_sha256,feature_definition_sha256,candidate_id,frozen_targets_ref,protocol_ref,
        expected_protocol_sha256,context):
    """Read-only caller-supplied selections at source-declared G0 cell centres."""
    try:
        return _evaluate(root,stage1_manifest_ref,forecast,prepared,candidate_config=candidate_config,
            expected_config_sha256=expected_config_sha256,feature_definition_sha256=feature_definition_sha256,
            candidate_id=candidate_id,frozen_targets_ref=frozen_targets_ref,protocol_ref=protocol_ref,
            expected_protocol_sha256=expected_protocol_sha256,context=context)
    except (pure.Stage1CapacityBlocked,t2.TimeTargetCapacityBlocked,models.ResearchCapacityBlocked,
            models.ResearchInputCapacity,models._hba1.HBA1CapacityBlocked) as exc:
        raise pi.InputCapacityError(str(exc)) from exc
    except pure.Stage1BudgetBlocked as exc:
        raise TimeoutError(str(exc)) from exc
