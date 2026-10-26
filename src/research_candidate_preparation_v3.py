"""Pure opt-in uniform/A1/A2 preparation; declared consistency, no admission.

Native learners/predictors are unchanged. No reader, outcome evaluator, writer,
trusted campaign counter, source authenticity or parent integration is supplied.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time

import research_model_adapter as legacy
from models import hba1_feature_candidate as a1, hba2_feature_candidate as a2
from models.research_selection import ResearchInputCapacity, validate_selection, validate_future_rows

VERSION='habu-research-candidates-prepared-v3'
CONFIG_VERSION='habu-research-candidate-config-v3'
CANDIDATES=('uniform','HB-A1','HB-A2')
CONFIG_FIELDS={'schema_version','mode','candidate_ids','hba1_recipe','hba2_recipe','feature_definition_sha256'}
MAX_JSON_BYTES=16*1024**2
MAX_OUTPUT_BYTES=16*1024**2
MAX_JSON_NODES=2_000_000
MAX_DEPTH=12
MAX_TRAIN_ROWS=20_000
MAX_FORECAST_ROWS=120_000
ResearchCapacityBlocked=legacy.ResearchCapacityBlocked
ResearchBudgetExhausted=legacy.ResearchBudgetExhausted
IMPLEMENTATION_BLOCKERS=[
    'A2_SOURCE_CONFIG_ADAPTER_NOT_IMPLEMENTED','A2_FULL_G0_SCORE_SUMMARY_NOT_IMPLEMENTED',
    'A2_STAGE1_SOURCE_ADAPTER_NOT_IMPLEMENTED','A2_PARENT_DISPATCH_NOT_IMPLEMENTED',
    'TRUSTED_CUMULATIVE_CAMPAIGN_LEDGER_NOT_IMPLEMENTED',
    'TRUSTED_PRE_REVEAL_FREEZE_AND_CONSUMPTION_LEDGER_NOT_IMPLEMENTED',
    'MODEL_COMPARISON_AND_WINNER_SELECTION_NOT_IMPLEMENTED',
    'REAL_SOURCE_TRAIN_AND_SCIENTIFIC_ELIGIBILITY_NOT_ESTABLISHED']
LIMITATIONS=['DECLARED_HASHES_NOT_FILE_OR_ISSUER_AUTHENTICATION',
    'NO_OUTCOMES_METRICS_WINNER_OR_CONFIRMATION_CONSUMED','CROSS_INVOCATION_LIMITS_REQUIRE_TRUSTED_CALLER',
    'COOPERATIVE_DEADLINE_NOT_HARD_PREEMPTION']
FIT_A1_FIELDS=a1.FLAG_FIELDS|{'schema_version','status','model','blockers','training_selection_sha256',
    'counts','recipe_sha256','registration_status','receipt_sha256'}
COMMON_A2_FIELDS=a1.FLAG_FIELDS|{'purpose','registration_status','candidate_id','target_semantics'}
FIT_A2_FIELDS=COMMON_A2_FIELDS|{'schema_version','status','recipe_sha256','assessment','model','runtime',
    'export_consistency','blockers','receipt_sha256'}
PREDICT_FIELDS=a1.FLAG_FIELDS|{'schema_version','candidate_id','model_sha256','recipe_sha256',
    'training_selection_sha256','universe_sha256','cutoff_time','operational_night','target_semantics','unit_predictions','prediction_sha256'}
UNIT_FIELDS={'row_id','operational_night','window_start_jst','cell_x','cell_y','area_id_1km',
    'probability','spatial_score','probability_status'}


def _walk(value,guard):
    pending=[(value,0)];nodes=0
    while pending:
        guard();item,depth=pending.pop();nodes+=1
        if nodes>MAX_JSON_NODES or depth>MAX_DEPTH:
            raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v3 JSON nodes/depth')
        kind=type(item)
        if kind in (dict,list):
            if nodes+len(pending)+len(item)>MAX_JSON_NODES:
                raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v3 JSON nodes')
            if kind is dict:
                for key in item:
                    guard()
                    if type(key) is not str or len(key)>512:raise ValueError('Bounded v3 JSON string keys required')
            for child in (item.values() if kind is dict else item):
                guard();pending.append((child,depth+1))
        elif kind is str:
            if len(item)>4096:raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v3 JSON string')
        elif kind is int:
            if item.bit_length()>1024:raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v3 integer')
        elif kind is float:
            if not math.isfinite(item):raise ValueError('Finite v3 JSON number required')
        elif kind not in (bool,type(None)):raise ValueError('JSON-only v3 inputs required')


def _encoded(value,guard,limit=MAX_JSON_BYTES,*,sort_keys=True):
    _walk(value,guard);size=0
    for part in json.JSONEncoder(sort_keys=sort_keys,ensure_ascii=False,separators=(',',':'),allow_nan=False).iterencode(value):
        guard();raw=part.encode('utf-8');size+=len(raw)
        if size>limit:raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v3 complete encoded JSON bytes')
        yield raw
    guard()


def _copy(value,guard):
    # Preserve native child dictionary insertion order as well as whole values.
    raw=bytearray()
    for part in _encoded(value,guard,sort_keys=False):raw.extend(part)
    guard();result=json.loads(raw);guard();return result


def _digest(value,guard):
    result=hashlib.sha256()
    for part in _encoded(value,guard):result.update(part)
    guard();return result.hexdigest()


def _same(value,expected,guard):
    # JSON type identity matters: False/0, True/1 and integer/float are distinct.
    return _digest(value,guard)==_digest(expected,guard)


def _seal_valid(value,field,guard):
    if type(value) is not dict or a1._hash(value.get(field))!=_digest({k:v for k,v in value.items() if k!=field},guard):
        raise ValueError('Native v3 child content digest mismatch')


def _flags(value,guard):
    for key,expected in a1._flags().items():
        guard()
        if type(value.get(key)) is not type(expected) or value[key]!=expected:
            raise ValueError('Native child cannot claim source authentication or authority')


def _finish(value,guard):
    # Both snapshots are checked: native _seal alone only bounds the prehash body.
    # A JSON snapshot also separates repeated model/fit-receipt subobjects.
    value=_copy(value,guard)
    for _ in _encoded(value,guard,MAX_OUTPUT_BYTES):pass
    value['receipt_sha256']=_digest(value,guard)
    for _ in _encoded(value,guard,MAX_OUTPUT_BYTES):pass
    guard();return value


def _config(value,expected,definition,guard):
    a1._fields(value,CONFIG_FIELDS)
    if value['schema_version']!=CONFIG_VERSION or value['mode']!='DEVELOPMENT_ONLY' or not _same(value['candidate_ids'],list(CANDIDATES),guard):
        raise ValueError('Only fixed ordered uniform/A1/A2 development config v3 is supported')
    if _digest(value,guard)!=expected or a1._hash(value['feature_definition_sha256'])!=definition:
        raise ValueError('V3 config or feature-definition digest mismatch')
    recipes={'HB-A1':_digest(value['hba1_recipe'],guard),'HB-A2':_digest(value['hba2_recipe'],guard)}
    a1._recipe(value['hba1_recipe'],recipes['HB-A1'],guard)
    if value['hba1_recipe']['feature_mask']!=[True]*7:raise ValueError('Full seven-column A1 recipe required')
    a2._recipe(value['hba2_recipe'],recipes['HB-A2'],guard);guard()
    return dict(uniform=None,**recipes)


def _known_raw(rows,guard):
    legacy._v2_supplied_hba1_raw_fields(rows,guard)
    for row in rows:
        for name,value in row['features'].items():
            guard()
            if name in a1.FEATURES:a2._f32(value)


def _ready_runtime(value,recipe):
    a2._runtime(value,recipe)


def _blocked_runtime(value,recipe,guard):
    a1._fields(value,a2.RUNTIME_FIELDS)
    if (value['schema_version']!='habu-hba2-runtime-v1' or value['status']!='CAPABILITY_BLOCKED' or
            not _same(value['expected_versions'],a2.PINS,guard) or value['input_dtype']!='IEEE754_BINARY32' or
            not _same(value['requirements_sha256'],recipe['requirements_sha256'],guard)):
        raise ValueError('Blocked native runtime recipe identity mismatch')
    for field,names in (('observed_versions',set(a2.PINS)),('auxiliary_versions',{'joblib','threadpoolctl'})):
        a1._fields(value[field],names)
        for item in value[field].values():
            guard()
            if item is not None and (type(item) is not str or len(item)>128):raise ValueError('Bounded observed runtime version required')
    for field in ('python_version','python_implementation','platform'):
        if type(value[field]) is not str or not 1<=len(value[field])<=512:raise ValueError('Bounded runtime platform required')
    mismatch=sorted('MISSING_OR_MISMATCHED_PACKAGE:'+name for name in a2.PINS if value['observed_versions'][name]!=a2.PINS[name])
    issues=value['issues']
    if mismatch:
        if not _same(issues,mismatch,guard):raise ValueError('Blocked runtime issues contradict observed versions')
    elif (type(issues) is not list or len(issues)!=1 or type(issues[0]) is not str or
            (issues[0]!='IMPORTED_BACKEND_VERSION_MISMATCH' and
             re.fullmatch(r'PINNED_BACKEND_IMPORT_FAILED:[A-Za-z_][A-Za-z0-9_]{0,127}',issues[0]) is None)):
        raise ValueError('Exact native import capability failure required')


def _fit_a2(value,assessment,recipe,recipe_sha,guard):
    value=_copy(value,guard);a1._fields(value,FIT_A2_FIELDS);_seal_valid(value,'receipt_sha256',guard);_flags(value,guard)
    if (value['schema_version']!='habu-hba2-standalone-fit-v1' or value['purpose']!='DEVELOPMENT_ONLY' or
            value['registration_status']!='STANDALONE_NOT_REGISTERED' or value['candidate_id']!='HB-A2' or
            value['target_semantics']!=a2.TARGET or value['recipe_sha256']!=recipe_sha or
            not _same(value['assessment'],assessment,guard)):
        raise ValueError('A2 native fit differs from complete common assessment/recipe')
    if value['status']=='CAPABILITY_BLOCKED':
        _blocked_runtime(value['runtime'],recipe,guard)
        if value['model'] is not None or value['export_consistency'] is not None or not _same(value['blockers'],value['runtime']['issues'],guard):
            raise ValueError('Blocked A2 fit contradicts model/export/issues')
        return value,None
    if value['status']!='DEVELOPMENT_FIT_ONLY' or value['blockers']!=[]:raise ValueError('Expected complete A2 native fit')
    model=a2._model(value['model'],guard);_ready_runtime(value['runtime'],recipe)
    if not _same(model['recipe'],recipe,guard) or not _same(model['runtime'],value['runtime'],guard):
        raise ValueError('A2 model and native runtime/recipe disagree')
    for field in a2.TRAIN_FIELDS:
        guard()
        if not _same(model[field],assessment[field],guard):raise ValueError('A2 common TRAIN identity mismatch: '+field)
    export=value['export_consistency']
    a1._fields(export,{'status','method','rows_checked','tolerance','max_abs_raw_error','max_abs_probability_error'})
    if (export['status']!='NATIVE_JSON_AGREEMENT' or export['method']!='PUBLIC_DECISION_FUNCTION_AND_PREDICT_PROBA' or
            type(export['rows_checked']) is not int or export['rows_checked']!=assessment['counts']['accepted_rows'] or
            type(export['tolerance']) is not float or export['tolerance']!=1e-12):
        raise ValueError('A2 exact native export consistency required')
    for field in ('max_abs_raw_error','max_abs_probability_error'):
        if type(export[field]) is not float or not 0<=a1._finite(export[field])<=1e-12:raise ValueError('A2 export tolerance exceeded')
    return value,model


def _fit_a1(value,assessment,recipe,recipe_sha,guard):
    value=_copy(value,guard);a1._fields(value,FIT_A1_FIELDS);_seal_valid(value,'receipt_sha256',guard);_flags(value,guard)
    if (value['schema_version']!=a1.FIT_VERSION or value['status']!='DEVELOPMENT_FIT_ONLY' or value['blockers']!=[] or
            value['registration_status']!='STANDALONE_NOT_REGISTERED' or value['recipe_sha256']!=recipe_sha or
            value['training_selection_sha256']!=assessment['training_selection_sha256'] or
            not _same(value['counts'],assessment['counts'],guard)):
        raise ValueError('A1 native fit differs from ready common selection/recipe')
    model=a1._model(value['model'],guard)
    if not _same(model['recipe'],recipe,guard):raise ValueError('A1 native recipe disagreement')
    for field in a2.TRAIN_FIELDS:
        guard()
        if not _same(model[field],assessment[field],guard):raise ValueError('A1 common TRAIN identity mismatch: '+field)
    return value,model


def _prediction(candidate,model,value,future,selected,recipe_sha,cutoff,joined_sha,guard):
    value=_copy(value,guard)
    fields=PREDICT_FIELDS if candidate=='HB-A1' else PREDICT_FIELDS|{'purpose','registration_status'}
    a1._fields(value,fields);_seal_valid(value,'prediction_sha256',guard);_flags(value,guard)
    version=a1.PREDICTION_VERSION if candidate=='HB-A1' else 'habu-hba2-unit-prediction-v1'
    if (value['schema_version']!=version or value['candidate_id']!=candidate or value['model_sha256']!=model['model_sha256'] or
            value['recipe_sha256']!=recipe_sha or value['training_selection_sha256']!=selected['selection_sha256'] or
            value['universe_sha256']!=joined_sha or value['cutoff_time']!=cutoff or
            value['operational_night']!=selected['heldout_night'] or value['target_semantics']!=a1.TARGET):
        raise ValueError('Native prediction common identity mismatch')
    if candidate=='HB-A2' and (value['purpose']!='DEVELOPMENT_ONLY' or value['registration_status']!='STANDALONE_NOT_REGISTERED'):
        raise ValueError('A2 standalone prediction only')
    units=value['unit_predictions']
    if type(units) is not list or len(units)!=len(future):raise ValueError('Complete native future coverage required')
    if [unit.get('row_id') for unit in units if type(unit) is dict]!=[row['row_id'] for row in future]:
        raise ValueError('Native prediction order differs from supplied full future rows')
    expected={r['row_id']:r for r in future};seen=set()
    if candidate=='HB-A2':
        matrix=[]
        for row in future:
            guard();matrix.append([a2._f32(row['features'][name]) for name in a2.FEATURES])
        _,numbers=a2._raw_prob(model['trees'],matrix,guard)
        scores={row['row_id']:round(number,8) for row,number in zip(future,numbers)}
    else:scores={row['row_id']:a1._score_owned_row(model,row,guard) for row in future}
    for unit in units:
        guard();a1._fields(unit,UNIT_FIELDS);identity=unit['row_id']
        if type(identity) is not str or identity not in expected or identity in seen:raise ValueError('Native future identity mismatch')
        seen.add(identity);row=expected[identity]
        for field in ('operational_night','window_start_jst','cell_x','cell_y'):
            if not _same(unit[field],row[field],guard):raise ValueError('Native future row/physical identity mismatch')
        if unit['probability_status']!='NOT_VALIDATED' or unit['area_id_1km']!=legacy.area_id(row['cell_x'],row['cell_y']):
            raise ValueError('Native probability status/area mismatch')
        for field in ('probability','spatial_score'):
            if type(unit[field]) is not float or unit[field]!=scores[identity]:raise ValueError('Native score contradicts actual model')
    guard();return value


def _uniform(model,prediction,future,selected,cutoff,joined,guard):
    model=_copy(model,guard);prediction=_copy(prediction,guard)
    legacy._validate_uniform_model(model,guard)
    if (not _same(model['counts'],selected['counts'],guard) or
            model['training_selection_sha256']!=selected['selection_sha256'] or
            model['training_cutoff']!=selected['fit_cutoff']):
        raise ValueError('Uniform common TRAIN identity mismatch')
    a1._fields(prediction,{'candidate_id','model_sha256','universe_sha256','cutoff_time','scientific_status',
        'unit_predictions','target_semantics','formal_100m_10min_status','production_activation_authorized','prediction_sha256'})
    _seal_valid(prediction,'prediction_sha256',guard)
    if (prediction['candidate_id']!='uniform' or prediction['model_sha256']!=model['model_sha256'] or
            prediction['universe_sha256']!=joined or prediction['cutoff_time']!=cutoff or
            prediction['scientific_status']!='NOT_VALIDATED' or prediction['target_semantics']!=a1.TARGET or
            prediction['formal_100m_10min_status']!='NOT_PRODUCED' or prediction['production_activation_authorized'] is not False):
        raise ValueError('Uniform native prediction identity/status mismatch')
    units=prediction['unit_predictions']
    if type(units) is not list or len(units)!=len(future):raise ValueError('Complete uniform future rows required')
    for unit,row in zip(units,future):
        guard();a1._fields(unit,UNIT_FIELDS)
        for field in ('row_id','operational_night','window_start_jst','cell_x','cell_y'):
            if not _same(unit[field],row[field],guard):raise ValueError('Uniform ordered future identity mismatch')
        if unit['area_id_1km']!=legacy.area_id(row['cell_x'],row['cell_y']) or unit['probability_status']!='NOT_VALIDATED':
            raise ValueError('Uniform physical/status mismatch')
        for field in ('probability','spatial_score'):
            if type(unit[field]) is not float or unit[field]!=model['probability']:
                raise ValueError('Uniform score contradicts its fixed Beta model')
    return model,prediction


def prepare_research_candidates_v3(selection,forecast_rows,*,candidate_config,expected_config_sha256,
        cutoff_time,joined_universe_sha256,feature_definition_sha256,budget_seconds=30,check=None):
    """Prepare a whole fixed diagnostic set, never a source/science admission."""
    if type(budget_seconds) not in (int,float) or not 0<budget_seconds<=300 or not math.isfinite(budget_seconds):
        raise ValueError('Finite positive budget at most300 seconds required')
    if check is not None and not callable(check):raise ValueError('Callable parent check required')
    deadline=time.monotonic()+budget_seconds;first_abort=None
    def guard():
        nonlocal first_abort
        if first_abort is not None:raise first_abort
        if check is not None:
            try:check()
            except BaseException as error:
                if first_abort is None:first_abort=error
                raise
        if time.monotonic()>=deadline:raise ResearchBudgetExhausted('RUNTIME_BLOCKED: shared v3 deadline expired')
    def remaining():
        guard();left=deadline-time.monotonic()
        if left<=0:raise ResearchBudgetExhausted('RUNTIME_BLOCKED: no remaining v3 budget')
        return left
    try:
        guard();expected=a1._hash(expected_config_sha256);definition=a1._hash(feature_definition_sha256);joined=a1._hash(joined_universe_sha256)
        if type(cutoff_time) is not str or not 1<=len(cutoff_time)<=64:raise ValueError('Bounded aware forecast cutoff required')
        if type(forecast_rows) is not list:raise ValueError('Explicit full future list required')
        if len(forecast_rows)>MAX_FORECAST_ROWS:raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v3 future rows')
        if type(selection) is dict and sum(len(selection[k]) for k in ('accepted','rejected') if type(selection.get(k)) is list)>MAX_TRAIN_ROWS:
            raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v3 TRAIN rows')
        config,train,rows=_copy([candidate_config,selection,forecast_rows],guard)
        recipes=_config(config,expected,definition,guard)
        selected=validate_selection(train);guard()
        if any(name not in a1.FEATURES for name in selected['feature_names']):raise ValueError('Only required seven raw features or proper subset allowed')
        future=validate_future_rows(rows,cutoff_time=cutoff_time,universe_sha256=joined,
            heldout_night=selected['heldout_night'],feature_names=selected['feature_names']);guard()
        _known_raw(selected['accepted'],guard);_known_raw(future,guard)
        row_ids=[];raw_features=[]
        for row in selected['accepted']:
            guard();row_ids.append(row['row_id']);raw_features.append(dict(row_id=row['row_id'],features=row['features']))
        common=dict(schema_version=VERSION,purpose='DEVELOPMENT_ONLY',candidate_ids=list(CANDIDATES),
            candidate_config_sha256=expected,feature_definition_sha256=definition,recipe_sha256_by_id=recipes,
            training_selection_sha256=selected['selection_sha256'],training_rows_sha256=_digest(selected['accepted'],guard),
            training_row_ids_sha256=_digest(row_ids,guard),raw_feature_rows_sha256=_digest(raw_features,guard),
            heldout_night=selected['heldout_night'],fit_cutoff=selected['fit_cutoff'],cutoff_time=cutoff_time,
            joined_universe_sha256=joined,forecast_units=len(future),
            joined_digest_semantics='CANONICAL_SUPPLIED_JOINED_ROWS_NOT_SOURCE_UNIVERSE_FILE',
            validation_status='NOT_VALIDATED',replay_status='PREPARED_NOT_PUBLISHED_OR_TRUSTED_SEALED',
            preregistration='CALLER_DEPENDENCY_REQUIRED',
            campaign_limits=dict(candidate_configurations=3,improvement_rounds=2,cross_invocation_enforcement='CALLER_OR_TRUSTED_LEDGER_REQUIRED'),
            implementation_blockers=list(IMPLEMENTATION_BLOCKERS),limitations=list(LIMITATIONS),**a1._flags())
        reasons=list(selected['blockers']) if selected['status']=='NEED_MORE_DATA' else []
        if selected['feature_names']!=sorted(a1.FEATURES):reasons.append('HB_A1_A2_REQUIRES_EXACT_SEVEN_RAW_FEATURE_SCHEMA')
        if selected['counts']['accepted_rows']<20 or selected['counts']['nights']<5:reasons.append('HB_A1_A2_REQUIRES_20_ROWS_AND_5_PRIOR_TRAIN_NIGHTS')
        if min(selected['counts']['positives'],selected['counts']['negatives'])<2:reasons.append('HB_A1_A2_REQUIRES_TWO_POSITIVE_AND_TWO_NEGATIVE_ROWS')
        if reasons:return _finish(dict(common,status='NEED_MORE_DATA',candidates=[],blockers=list(dict.fromkeys(reasons)),capability_receipt=None),guard)
        assessment=a2.assess_hba2(selected,recipe=config['hba2_recipe'],expected_recipe_sha256=recipes['HB-A2'],budget_seconds=remaining(),check=guard);guard()
        if assessment['status']!='SOFTWARE_INPUTS_READY':raise ValueError('Ready preflight assessment contradiction')
        fitted2=a2.fit_hba2(selected,recipe=config['hba2_recipe'],expected_recipe_sha256=recipes['HB-A2'],budget_seconds=remaining(),check=guard);guard()
        fit2,model2=_fit_a2(fitted2,assessment,config['hba2_recipe'],recipes['HB-A2'],guard)
        if model2 is None:return _finish(dict(common,status='CAPABILITY_BLOCKED',candidates=[],blockers=list(fit2['blockers']),capability_receipt=fit2),guard)
        fitted1=a1.fit_hba1(selected,recipe=config['hba1_recipe'],expected_recipe_sha256=recipes['HB-A1'],budget_seconds=remaining(),check=guard);guard()
        fit1,model1=_fit_a1(fitted1,assessment,config['hba1_recipe'],recipes['HB-A1'],guard)
        predictions={}
        for identity,model,function in (('HB-A1',model1,a1.predict_hba1),('HB-A2',model2,a2.predict_hba2)):
            native=function(model,rows,cutoff_time=cutoff_time,joined_universe_sha256=joined,budget_seconds=remaining(),check=guard);guard()
            predictions[identity]=_prediction(identity,model,native,future,selected,recipes[identity],cutoff_time,joined,guard)
        uniform_model,uniform_prediction=legacy._uniform(selected,future,cutoff_time,joined,guard);guard()
        uniform_model,uniform_prediction=_uniform(uniform_model,uniform_prediction,future,selected,cutoff_time,joined,guard)
        expected_rows={row['row_id']:row for row in future};prepared=[]
        for identity,model,prediction,fit in (('uniform',uniform_model,uniform_prediction,None),
                ('HB-A1',model1,predictions['HB-A1'],fit1),('HB-A2',model2,predictions['HB-A2'],fit2)):
            guard();candidate=legacy._candidate(identity,model,prediction,joined,expected_rows,selected,cutoff_time,guard);guard()
            candidate.update(candidate_config_sha256=expected,feature_definition_sha256=definition,
                training_selection_sha256=common['training_selection_sha256'],training_rows_sha256=common['training_rows_sha256'],
                training_row_ids_sha256=common['training_row_ids_sha256'],raw_feature_rows_sha256=common['raw_feature_rows_sha256'],
                recipe_sha256=recipes[identity],fit_receipt=fit)
            prepared.append(candidate)
        return _finish(dict(common,status='DIAGNOSTIC_CANDIDATES_PREPARED',candidates=prepared,blockers=[],capability_receipt=None),guard)
    except BaseException as error:
        if first_abort is not None:raise first_abort
        if isinstance(error,(ResearchInputCapacity,a1.HBA1CapacityBlocked,a2.HBA2CapacityBlocked)):
            raise ResearchCapacityBlocked('CAPACITY_BLOCKED: '+str(error)) from error
        if isinstance(error,(KeyError,TypeError,IndexError,OverflowError,RecursionError)):
            raise ValueError('Invalid v3 contract structure') from error
        raise
