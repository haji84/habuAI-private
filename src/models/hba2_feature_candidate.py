"""Standalone declared-consistency HB-A2; pinned library fit, JSON-only inference.

No source reader, confirmation, candidate registration, model selection or writer.
Native import/one tree stage is cooperative rather than hard-preemptible.
"""
from __future__ import annotations

import importlib.metadata
import math
import platform
import struct

from models import hba1_feature_candidate as base
from models.research_selection import ResearchInputCapacity, area_id

TARGET, FEATURES = base.TARGET, base.FEATURES
PINS = {'scikit-learn':'1.5.2', 'numpy':'2.2.6', 'scipy':'1.15.3'}
PARAMS = dict(loss='log_loss', learning_rate=.1, n_estimators=32, subsample=1.0,
    criterion='friedman_mse', min_samples_split=10, min_samples_leaf=5,
    min_weight_fraction_leaf=0.0, max_depth=2, min_impurity_decrease=0.0,
    init='zero', random_state=0, max_features=None, verbose=0, max_leaf_nodes=None,
    warm_start=False, validation_fraction=.1, n_iter_no_change=None, tol=.0001, ccp_alpha=0.0)
REQUIREMENT_PATHS = {'requirements-analysis.txt', 'requirements-osm.txt'}
CODE_PATHS = {'src/models/hba2_feature_candidate.py', 'src/models/hba1_feature_candidate.py',
    'src/prospective_candidate_model.py', 'src/models/research_selection.py', 'src/gpx_audit.py'}
RECIPE_FIELDS = {'schema_version','target','algorithm','feature_names','params',
    'runtime_versions','requirements_sha256','implementation_sha256'}
TRAIN_FIELDS = ('training_selection_sha256','corpus_sha256','source_sha256','source_received_at',
    'fit_cutoff','heldout_night','training_nights','training_window_start_max','counts',
    'training_rows_sha256','training_row_ids_sha256','raw_feature_rows_sha256')
RUNTIME_FIELDS = {'schema_version','status','expected_versions','observed_versions','auxiliary_versions',
    'python_version','python_implementation','platform','input_dtype','requirements_sha256','issues'}
MODEL_FIELDS = set(TRAIN_FIELDS) | base.FLAG_FIELDS | {'schema_version','status','candidate_id',
    'target_semantics','recipe','recipe_sha256','feature_names','input_dtype','initial_raw_score',
    'learning_rate','classes','trees','runtime','model_sha256'}


class HBA2CapacityBlocked(ValueError):
    """CAPACITY_BLOCKED; never a partial model or sampled universe."""


def _flags():
    return base._flags()


def _common():
    return dict(purpose='DEVELOPMENT_ONLY', registration_status='STANDALONE_NOT_REGISTERED',
        candidate_id='HB-A2', target_semantics=TARGET, **_flags())


def _run(function, seconds, check):
    try:
        return function(base._budget(seconds, check))
    except (base.HBA1CapacityBlocked, ResearchInputCapacity) as exc:
        raise HBA2CapacityBlocked('CAPACITY_BLOCKED: '+str(exc)) from exc
    except (KeyError, TypeError, IndexError, OverflowError, RecursionError) as exc:
        raise ValueError('Invalid HB-A2 contract structure') from exc


def _f32(value):
    value = base._finite(value)
    try:
        result = struct.unpack('<f', struct.pack('<f', value))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError('HB-A2 raw feature exceeds finite binary32') from exc
    if not math.isfinite(result):
        raise ValueError('HB-A2 raw feature becomes nonfinite binary32')
    return result


def _recipe(value, expected, check):
    base._fields(value, RECIPE_FIELDS)
    if (value['schema_version'] != 'habu-hba2-gbc-recipe-v1' or value['target'] != TARGET or
            value['algorithm'] != 'SKLEARN_GBC_BINARY_LOG_LOSS_ZERO_INIT_V1' or
            value['feature_names'] != list(FEATURES) or
            base._digest(value['params'], check) != base._digest(PARAMS, check) or
            value['runtime_versions'] != PINS):
        raise ValueError('Exact fixed HB-A2 development recipe required')
    for field, paths in (('requirements_sha256', REQUIREMENT_PATHS), ('implementation_sha256', CODE_PATHS)):
        base._fields(value[field], paths)
        for item in value[field].values(): check(); base._hash(item)
    if base._digest(value, check) != base._hash(expected):
        raise ValueError('HB-A2 recipe content digest mismatch')


def _train_cap(value):
    if type(value) is not dict or type(value.get('accepted')) is not list or type(value.get('rejected')) is not list:
        raise ValueError('Exact bounded TRAIN selection required')
    if len(value['accepted']) + len(value['rejected']) > base.MAX_TRAIN_ROWS:
        raise HBA2CapacityBlocked('CAPACITY_BLOCKED: HB-A2 actual TRAIN rows')


def _assessment(value, recipe, expected, check):
    _recipe(recipe, expected, check)
    selected, raw_matrix, labels = base._selection(value, check)
    matrix = []
    # Every known row is cast before insufficient-data/backend classification.
    for row in raw_matrix:
        check()
        cast = []
        for item in row: check(); cast.append(_f32(item))
        matrix.append(cast)
    rows = selected['accepted']
    reasons = list(selected['blockers']) if selected['status'] == 'NEED_MORE_DATA' else []
    if len(rows) < 20 or selected['counts']['nights'] < 5:
        reasons.append('HB_A2_REQUIRES_20_SELECTED_ROWS_AND_5_PRIOR_TRAIN_NIGHTS')
    result = dict(schema_version='habu-hba2-feasibility-v1',
        status='NEED_MORE_DATA' if reasons else 'SOFTWARE_INPUTS_READY',
        recipe_sha256=expected, training_selection_sha256=selected['selection_sha256'],
        corpus_sha256=selected['corpus_sha256'], source_sha256=selected['source_sha256'],
        source_received_at=selected['source_received_at'], fit_cutoff=selected['fit_cutoff'],
        heldout_night=selected['heldout_night'], training_nights=sorted({r['night'] for r in rows}),
        training_window_start_max=max((base._time(r['window_start_jst']) for r in rows), default=None),
        counts=selected['counts'], training_rows_sha256=base._digest(rows,check),
        training_row_ids_sha256=base._digest([r['row_id'] for r in rows],check),
        raw_feature_rows_sha256=base._digest([dict(row_id=r['row_id'],features=r['features']) for r in rows],check),
        backend_status='NOT_PROBED', runtime=None, blockers=sorted(set(reasons)), **_common())
    if result['training_window_start_max'] is not None:
        result['training_window_start_max'] = result['training_window_start_max'].isoformat()
    return base._seal(result,'receipt_sha256',check), matrix, labels


def assess_hba2(training_selection, *, recipe, expected_recipe_sha256, budget_seconds=30, check=None):
    def execute(guard):
        _train_cap(training_selection)
        owned, spec = base._own([training_selection,recipe],guard)
        return _assessment(owned,spec,expected_recipe_sha256,guard)[0]
    return _run(execute,budget_seconds,check)


def _backend(recipe, check):
    """Only reached for enough validated TRAIN; metadata never authenticates code."""
    def version(name):
        check()
        try: return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: return None
    observed = {name:version(name) for name in PINS}
    runtime = dict(schema_version='habu-hba2-runtime-v1', status='CAPABILITY_BLOCKED',
        expected_versions=dict(PINS), observed_versions=observed,
        auxiliary_versions={name:version(name) for name in ('joblib','threadpoolctl')},
        python_version=platform.python_version(), python_implementation=platform.python_implementation(),
        platform=platform.platform(), input_dtype='IEEE754_BINARY32',
        requirements_sha256=recipe['requirements_sha256'],
        issues=sorted('MISSING_OR_MISMATCHED_PACKAGE:'+name for name in PINS if observed[name] != PINS[name]))
    check()
    if runtime['issues']: return runtime,None
    try:
        import numpy as np
        import scipy
        import sklearn
        from sklearn.ensemble import GradientBoostingClassifier
    except ImportError:
        check(); runtime['issues']=['PINNED_BACKEND_IMPORT_FAILED']; return runtime,None
    check()
    if {'numpy':np.__version__,'scipy':scipy.__version__,'scikit-learn':sklearn.__version__} != PINS:
        runtime['issues']=['IMPORTED_BACKEND_VERSION_MISMATCH']; return runtime,None
    runtime['status']='PINNED_BACKEND_READY'
    return runtime,(np,GradientBoostingClassifier)


def _runtime(value, recipe):
    base._fields(value,RUNTIME_FIELDS)
    if (value['schema_version']!='habu-hba2-runtime-v1' or value['status']!='PINNED_BACKEND_READY' or
            value['expected_versions']!=PINS or value['observed_versions']!=PINS or value['issues']!=[] or
            value['input_dtype']!='IEEE754_BINARY32' or value['requirements_sha256']!=recipe['requirements_sha256']):
        raise ValueError('Pinned declared HB-A2 runtime identity required')
    base._fields(value['auxiliary_versions'],{'joblib','threadpoolctl'})
    for item in value['auxiliary_versions'].values():
        if item is not None and (type(item) is not str or not 1<=len(item)<=128):
            raise ValueError('Bounded actual auxiliary version required')
    for field in ('python_version','python_implementation','platform'):
        if type(value[field]) is not str or not 1<=len(value[field])<=512:
            raise ValueError('Bounded declared Python/platform identity required')


def _trees(values, check):
    if type(values) is not list or len(values)!=32:
        raise ValueError('Exactly 32 finished HB-A2 trees required')
    for tree in values:
        check(); base._fields(tree,{'nodes'})
        nodes=tree['nodes']
        if type(nodes) is not list or not 1<=len(nodes)<=7:
            raise ValueError('Bounded depth-two HB-A2 tree required')
        seen,pending=set(),[(0,0)]
        while pending:
            check(); index,depth=pending.pop()
            if index in seen or depth>2: raise ValueError('Cyclic/shared or deep HB-A2 tree')
            seen.add(index); node=nodes[index]
            base._fields(node,{'left','right','feature','threshold','value'})
            left,right=node['left'],node['right']
            if type(left) is not int or type(right) is not int:
                raise ValueError('Nonboolean integer tree children required')
            if left==right==-1:
                if node['feature'] is not None or node['threshold'] is not None or type(node['value']) is not float:
                    raise ValueError('Canonical finite leaf required')
                base._finite(node['value'])
            else:
                if (not 0<=left<len(nodes) or not 0<=right<len(nodes) or left==right or
                        type(node['feature']) is not int or not 0<=node['feature']<7 or
                        node['value'] is not None or type(node['threshold']) is not float):
                    raise ValueError('Canonical finite split required')
                base._finite(node['threshold']); pending.extend(((left,depth+1),(right,depth+1)))
        if len(seen)!=len(nodes): raise ValueError('Unreachable HB-A2 tree nodes')


def _raw_prob(trees, matrix, check):
    raw_values,probabilities=[],[]
    for row in matrix:
        check(); raw=0.0
        for tree in trees:
            check(); index=0; nodes=tree['nodes']
            while nodes[index]['left']!=-1:
                node=nodes[index]; index=node['left'] if row[node['feature']]<=node['threshold'] else node['right']
            term=base._finite(.1*nodes[index]['value'])
            raw=base._finite(raw+term)
        exp=math.exp(-raw if raw>=0 else raw)
        probability=base._finite(1/(1+exp) if raw>=0 else exp/(1+exp))
        raw_values.append(raw); probabilities.append(probability)
    check(); return raw_values,probabilities


def _export(estimator, check):
    if (base._digest(estimator.get_params(deep=False),check)!=base._digest(PARAMS,check) or
            estimator.classes_.tolist()!=[0,1] or estimator.n_features_in_!=7 or
            estimator.n_estimators_!=32 or estimator.n_trees_per_iteration_!=1 or
            estimator.init_!='zero' or estimator.estimators_.shape!=(32,1)):
        raise ValueError('Unexpected pinned estimator recipe/classes/completeness')
    result=[]
    for estimator_tree in estimator.estimators_[:,0]:
        check(); tree=estimator_tree.tree_; count=tree.node_count
        if not 1<=count<=7 or tree.max_depth>2 or tree.value.shape!=(count,1,1):
            raise ValueError('Unexpected native regression tree shape')
        nodes=[]
        for index in range(count):
            check(); left,right=int(tree.children_left[index]),int(tree.children_right[index])
            leaf=left==right==-1
            nodes.append(dict(left=left,right=right,feature=None if leaf else int(tree.feature[index]),
                threshold=None if leaf else float(tree.threshold[index]),
                value=float(tree.value[index,0,0]) if leaf else None))
        result.append(dict(nodes=nodes))
    _trees(result,check); return result


def _model(value, check):
    base._fields(value,MODEL_FIELDS)
    if base._hash(value['model_sha256'])!=base._digest({k:v for k,v in value.items() if k!='model_sha256'},check):
        raise ValueError('HB-A2 model content digest mismatch')
    _recipe(value['recipe'],value['recipe_sha256'],check)
    if (value['schema_version']!='habu-hba2-research-model-v1' or value['status']!='DEVELOPMENT_RESEARCH_FIT_ONLY' or
            value['candidate_id']!='HB-A2' or value['target_semantics']!=TARGET or
            value['feature_names']!=list(FEATURES) or value['input_dtype']!='IEEE754_BINARY32' or
            type(value['initial_raw_score']) is not float or value['initial_raw_score']!=0.0 or
            type(value['learning_rate']) is not float or value['learning_rate']!=.1 or
            base._digest(value['classes'],check)!=base._digest([0,1],check)):
        raise ValueError('Exact research-only HB-A2 model required')
    for key,item in _flags().items():
        if type(value[key]) is not type(item) or value[key]!=item:
            raise ValueError('HB-A2 cannot claim source authentication or authority')
    _runtime(value['runtime'],value['recipe']); _trees(value['trees'],check)
    cutoff,night=base._time(value['fit_cutoff']),base._night(value['heldout_night'])
    if cutoff>=base._time(night+'T07:00:00+09:00'): raise ValueError('HB-A2 fit must precede heldout night')
    nights=value['training_nights']
    if type(nights) is not list or not 5<=len(nights)<=base.MAX_TRAIN_ROWS or nights!=sorted(set(nights)):
        raise ValueError('Sorted distinct HB-A2 training nights required')
    for earlier in nights:
        check()
        if base._time(base._night(earlier)+'T07:00:00+09:00')>=cutoff or earlier>=night:
            raise ValueError('HB-A2 training night exceeds fit/heldout chronology')
    latest=base._time(value['training_window_start_max'])
    if (latest>=cutoff or latest.minute%10 or latest.second or latest.microsecond or
            base.learner._night(latest)!=nights[-1]):
        raise ValueError('HB-A2 actual latest training window mismatch')
    counts=value['counts']; base._fields(counts,{'accepted_rows','rejected_rows','nights','positives','negatives'})
    if (any(type(n) is not int for n in counts.values()) or not 20<=counts['accepted_rows']<=base.MAX_TRAIN_ROWS or
            not 0<=counts['rejected_rows']<=base.MAX_TRAIN_ROWS-counts['accepted_rows'] or
            counts['nights']!=len(nights) or counts['nights']>counts['accepted_rows'] or
            min(counts['positives'],counts['negatives'])<2 or counts['positives']+counts['negatives']!=counts['accepted_rows']):
        raise ValueError('HB-A2 native counts contradict support')
    for key in ('training_selection_sha256','corpus_sha256','training_rows_sha256',
                'training_row_ids_sha256','raw_feature_rows_sha256'): base._hash(value[key])
    base._sources(value['source_sha256'],value['source_received_at'],cutoff)
    check(); return value


def fit_hba2(training_selection, *, recipe, expected_recipe_sha256, budget_seconds=30, check=None):
    def execute(guard):
        _train_cap(training_selection)
        selected,spec=base._own([training_selection,recipe],guard)
        assessment,matrix,labels=_assessment(selected,spec,expected_recipe_sha256,guard)
        result=dict(schema_version='habu-hba2-standalone-fit-v1',status='NEED_MORE_DATA',
            recipe_sha256=expected_recipe_sha256,assessment=assessment,model=None,runtime=None,
            export_consistency=None,blockers=assessment['blockers'],**_common())
        if assessment['status']=='NEED_MORE_DATA': return base._seal(result,'receipt_sha256',guard)
        runtime,backend=_backend(spec,guard)
        result['runtime']=runtime
        if backend is None:
            result.update(status='CAPABILITY_BLOCKED',blockers=runtime['issues'])
            return base._seal(result,'receipt_sha256',guard)
        np,classifier=backend
        guard(); array=np.asarray(matrix,dtype=np.float32); guard()
        if not np.isfinite(array).all(): raise ValueError('Nonfinite native HB-A2 float32 matrix')
        estimator=classifier(**PARAMS)
        def monitor(*args,**kwargs): guard(); return False
        guard(); estimator.fit(array,labels,monitor=monitor); guard()
        trees=_export(estimator,guard)
        guard(); native_raw=estimator.decision_function(array).tolist(); guard()
        native_prob=estimator.predict_proba(array)[:,1].tolist(); guard()
        raw,prob=_raw_prob(trees,matrix,guard)
        errors=[0.0,0.0]
        for actual,expected,p,q in zip(raw,native_raw,prob,native_prob):
            guard(); errors[0]=max(errors[0],abs(actual-base._finite(expected)))
            errors[1]=max(errors[1],abs(p-base._finite(q)))
        if len(raw)!=len(native_raw) or len(prob)!=len(native_prob) or max(errors)>1e-12:
            raise ValueError('Pinned native/JSON export discrepancy')
        model=dict(schema_version='habu-hba2-research-model-v1',status='DEVELOPMENT_RESEARCH_FIT_ONLY',
            candidate_id='HB-A2',target_semantics=TARGET,recipe=spec,recipe_sha256=expected_recipe_sha256,
            feature_names=list(FEATURES),input_dtype='IEEE754_BINARY32',initial_raw_score=0.0,
            learning_rate=.1,classes=[0,1],trees=trees,runtime=runtime,
            **{key:assessment[key] for key in TRAIN_FIELDS},**_flags())
        model=base._seal(model,'model_sha256',guard); _model(model,guard)
        result.update(status='DEVELOPMENT_FIT_ONLY',model=model,blockers=[],
            export_consistency=dict(status='NATIVE_JSON_AGREEMENT',method='PUBLIC_DECISION_FUNCTION_AND_PREDICT_PROBA',
                rows_checked=len(matrix),tolerance=1e-12,max_abs_raw_error=errors[0],max_abs_probability_error=errors[1]))
        return base._seal(result,'receipt_sha256',guard)
    return _run(execute,budget_seconds,check)


def predict_hba2(model, forecast_rows, *, cutoff_time, joined_universe_sha256, budget_seconds=30, check=None):
    def execute(guard):
        if type(forecast_rows) is not list: raise ValueError('Complete future rows required')
        if len(forecast_rows)>base.MAX_FORECAST_ROWS:
            raise HBA2CapacityBlocked('CAPACITY_BLOCKED: HB-A2 complete future rows')
        owned,rows=base._own([model,forecast_rows],guard)
        fitted=_model(owned,guard)
        future=base._future(rows,cutoff_time,joined_universe_sha256,fitted['heldout_night'],guard)
        if base._time(fitted['fit_cutoff'])>=base._time(cutoff_time):
            raise ValueError('HB-A2 fit must precede forecast cutoff')
        matrix=[]
        for row in future:
            guard(); matrix.append([_f32(row['features'][name]) for name in FEATURES])
        _,prob=_raw_prob(fitted['trees'],matrix,guard)
        units=[]
        for row,number in zip(future,prob):
            guard(); number=round(number,8)
            units.append(dict(row_id=row['row_id'],operational_night=row['operational_night'],
                window_start_jst=row['window_start_jst'],cell_x=row['cell_x'],cell_y=row['cell_y'],
                area_id_1km=area_id(row['cell_x'],row['cell_y']),probability=number,
                spatial_score=number,probability_status='NOT_VALIDATED'))
        result=dict(schema_version='habu-hba2-unit-prediction-v1',model_sha256=fitted['model_sha256'],
            recipe_sha256=fitted['recipe_sha256'],training_selection_sha256=fitted['training_selection_sha256'],
            universe_sha256=joined_universe_sha256,cutoff_time=cutoff_time,operational_night=fitted['heldout_night'],
            unit_predictions=units,**_common())
        return base._seal(result,'prediction_sha256',guard)
    return _run(execute,budget_seconds,check)
