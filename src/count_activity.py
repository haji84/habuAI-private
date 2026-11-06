"""Declared-cohort Gamma-Poisson count mechanics under a frozen protocol.

This supplementary capture proxy is neither biological Tonight Activity nor
detection probability. Existing count/effort and planned-intent gates retain
their own source-qualification limitations. No model, source or registry is
written, and no transport or caller-selected implementation is accepted.
Runtime package imports/metadata are read; input observations stay in RAM.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
from importlib import metadata
import hashlib
import json
import math
import sys
import time

from master_contracts import canonical_bytes, digest
from models import count_feasibility as feasibility
from models import research_selection as selection_gate
from g0_planned_effort_projection import project_planned_effort, MAX_RAW_BYTES, _decode_raw
from prospective_inputs import ProspectiveReadContext

MODEL_VERSION = 'habu-gamma-poisson-model-v1'
PROTOCOL_VERSION = 'habu-gamma-poisson-protocol-v1'
TARGET = feasibility.TARGET
RUNTIME_VERSIONS = {'numpy':'2.2.6', 'scipy':'1.15.3', 'scikit-learn':'1.5.2'}
MAX_BYTES = 16 * 1024**2
MAX_NODES = 2_000_000
MAX_DEPTH = 24
PROTOCOL_FIELDS = {'schema_version','family','target','frozen_at','prior','quantiles',
                   'numerics','capacities','reference','runtime_versions'}
CAP_FIELDS = {'min_shape','max_shape','min_rate_hours','max_rate_hours',
    'max_exposure_hours','max_training_units','max_planned_units','max_quantiles',
    'max_output_count','max_json_bytes','max_json_nodes','max_fit_seconds','max_predict_seconds'}
UNIT_FIELDS = feasibility.UNIT | {'count','active_search_seconds'}
INPUT_FIELDS = {'selection','count_projection','effort_projection'}
LINEAGE_FIELDS = {'selection_sha256','corpus_sha256','count_projection_sha256',
                  'effort_projection_sha256','feasibility_assessment_sha256'}
PLAN_FIELDS = {'raw_plan_utf8','domain','bindings','expected_domain_sha256','expected_identity','as_of_time'}


class CountActivityCapacityError(ValueError):
    """A bounded operation cannot complete; no partial fit is a valid model."""


class _RuntimeBindingError(ValueError):
    pass


def _flags():
    return dict(source_authenticity='NOT_ATTESTED', source_authentication='CALLER_DEPENDENCY_REQUIRED',
        scientific_status='NOT_VALIDATED', statistical_adequacy='NOT_ASSESSED',
        fit_authorized=False, scientific_execution_authorized=False, selection_authorized=False,
        promotion_authorized=False, confirmation_authorized=False,
        official_issuance_authorized=False, production_authorized=False,
        biological_tonight_activity_validated=False, detection_probability_produced=False)


class _Budget:
    def __init__(self, seconds, maximum):
        kind = type(seconds)
        if (kind is not int and kind is not float) or not 0 < seconds <= maximum:
            raise ValueError('Finite nonboolean bounded elapsed budget required')
        self.entered = time.monotonic()
        self.deadline = self.entered + seconds

    def check(self):
        if time.monotonic() >= self.deadline:
            raise CountActivityCapacityError('RUNTIME_CAPACITY_EXCEEDED')

    def restrict(self, seconds):
        self.deadline = min(self.deadline, self.entered + seconds)
        self.check()

    def remaining(self):
        self.check()
        return max(1e-12, self.deadline - time.monotonic())


def _fields(value, fields):
    if type(value) is not dict or set(value) != fields:
        raise ValueError('Exact count-activity fields required')


def _number(value, *, positive=False):
    kind = type(value)
    if (kind is not int and kind is not float) or not math.isfinite(value) or (positive and value <= 0):
        raise ValueError('Finite nonboolean numerical value required')
    return float(value)


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('Exact bounded nonboolean integer required')
    return value


def _hash(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Explicit SHA256 required')
    return value


def _stamp(value):
    if type(value) is not str or len(value) > 64 or 'T' not in value:
        raise ValueError('Aware bounded count time required')
    stamp = datetime.fromisoformat(value.replace('Z','+00:00'))
    if stamp.utcoffset() is None:
        raise ValueError('Aware count time required')
    return stamp


def _owned(values, budget):
    """No type-equality hooks, arbitrary iteration, deepcopy or deserialization."""
    nodes, active = 0, set()
    def visit(item, depth):
        nonlocal nodes
        budget.check(); nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise CountActivityCapacityError('INPUT_STRUCTURE_CAPACITY_EXCEEDED')
        kind = type(item)
        if kind is dict or kind is list:
            if len(item) > MAX_NODES or id(item) in active:
                raise ValueError('Bounded acyclic JSON required')
            active.add(id(item))
            if kind is dict:
                for key,value in item.items():
                    if type(key) is not str or len(key) > 512:
                        raise ValueError('Bounded builtin JSON keys required')
                    visit(value,depth+1)
            else:
                for value in item: visit(value,depth+1)
            active.remove(id(item))
        elif kind is str:
            if len(item) > MAX_BYTES:
                raise CountActivityCapacityError('INPUT_STRING_CAPACITY_EXCEEDED')
        elif kind is int:
            if not -(2**63) <= item < 2**63:
                raise ValueError('Bounded JSON integer required')
        elif kind is float:
            if not math.isfinite(item): raise ValueError('Nonfinite input')
        elif kind is not bool and kind is not type(None):
            raise ValueError('Exact builtin JSON data only')
    visit(values,0)
    raw = canonical_bytes(values); budget.check()
    if len(raw) > MAX_BYTES: raise CountActivityCapacityError('INPUT_BYTE_CAPACITY_EXCEEDED')
    result = json.loads(raw); budget.check()
    return result, len(raw), nodes


def _protocol(value, budget, *, mode, input_bytes, nodes):
    _fields(value,PROTOCOL_FIELDS)
    if (value['schema_version'] != PROTOCOL_VERSION or value['family'] != 'GAMMA_POISSON_SHAPE_RATE'
            or value['target'] != TARGET): raise ValueError('Registered Gamma-Poisson protocol required')
    _stamp(value['frozen_at'])
    _fields(value['prior'],{'alpha','beta_active_search_hours'})
    for number in value['prior'].values(): _number(number,positive=True)
    _fields(value['numerics'],{'cdf_absolute_tolerance','log_tail_tolerance'})
    for number in value['numerics'].values():
        if not 0 < _number(number) < 1: raise ValueError('Declared numerical tolerance outside (0,1)')
    caps=value['capacities']; _fields(caps,CAP_FIELDS)
    for name in ('min_shape','max_shape','min_rate_hours','max_rate_hours','max_exposure_hours'):
        _number(caps[name],positive=True)
    if caps['min_shape'] > caps['max_shape'] or caps['min_rate_hours'] > caps['max_rate_hours']:
        raise ValueError('Reversed numerical support bounds')
    for name,maximum,low in [('max_training_units',feasibility.MAX_ROWS,1),('max_planned_units',120000,1),
            ('max_quantiles',64,1),('max_output_count',2**53-1,0),
            ('max_json_bytes',MAX_BYTES,1),('max_json_nodes',MAX_NODES,1)]:
        _integer(caps[name],low,maximum)
    for name,maximum in [('max_fit_seconds',300),('max_predict_seconds',30)]:
        if not 0 < _number(caps[name]) <= maximum: raise ValueError('Declared elapsed capacity unsupported')
    budget.restrict(caps['max_fit_seconds' if mode=='fit' else 'max_predict_seconds'])
    if input_bytes > caps['max_json_bytes'] or nodes > caps['max_json_nodes']:
        raise CountActivityCapacityError('PROTOCOL_INPUT_CAPACITY_EXCEEDED')
    quantiles=value['quantiles']
    if type(quantiles) is not list or not quantiles or len(quantiles)>caps['max_quantiles']:
        raise ValueError('Explicit bounded nonempty quantiles required')
    previous=0
    for q in quantiles:
        if not previous < _number(q) < 1: raise ValueError('Strictly increasing quantiles in (0,1) required')
        previous=q
    reference=value['reference'];_fields(reference,{'active_search_hours','owner_id','observer_id','method_version'})
    if not 0 < _number(reference['active_search_hours']) <= caps['max_exposure_hours']:
        raise ValueError('Reference exposure outside declared support')
    for name in ('owner_id','observer_id','method_version'):
        if type(reference[name]) is not str or not reference[name].strip() or len(reference[name])>256:
            raise ValueError('Reference observer/search protocol identity required')
    _fields(value['runtime_versions'],set(RUNTIME_VERSIONS))
    if value['runtime_versions'] != RUNTIME_VERSIONS: raise ValueError('Only the existing pinned analysis profile is supported')
    return value


def _runtime(budget):
    budget.check()
    try:
        versions={name:metadata.version(name) for name in RUNTIME_VERSIONS}
        numpy=importlib.import_module('numpy');scipy=importlib.import_module('scipy')
        stats=importlib.import_module('scipy.stats')
        if (versions != RUNTIME_VERSIONS or numpy.__version__ != versions['numpy']
                or scipy.__version__ != versions['scipy']):
            raise _RuntimeBindingError('RUNTIME_BINDING_ERROR')
        nbinom=stats.nbinom
        if not all(callable(getattr(nbinom,name)) for name in ('ppf','cdf','logcdf','logsf')):
            raise _RuntimeBindingError('RUNTIME_BINDING_ERROR')
    except (ImportError,OSError,AttributeError,metadata.PackageNotFoundError) as exc:
        raise _RuntimeBindingError('RUNTIME_BINDING_ERROR') from exc
    budget.check()
    return versions,nbinom


def _statistics(units, protocol, budget):
    if type(units) is not list or not units: raise ValueError('Nonempty declared training unit table required')
    if len(units)>protocol['capacities']['max_training_units']:
        raise CountActivityCapacityError('TRAINING_UNIT_CAPACITY_EXCEEDED')
    total=0;seconds=[];nights=set()
    for row in units:
        budget.check();total+=_integer(row['count'],0,feasibility.MAX_INDIVIDUALS)
        e=_number(row['active_search_seconds'],positive=True)
        if e>600: raise ValueError('Measured per-unit exposure exceeds physical window')
        seconds.append(e);nights.add(row['night'])
    if total>feasibility.MAX_INDIVIDUALS: raise CountActivityCapacityError('COUNT_CAPACITY_EXCEEDED')
    exposure=math.fsum(seconds);hours=exposure/3600
    if not math.isfinite(hours) or hours<=0: raise CountActivityCapacityError('NUMERICAL_CAPACITY_EXCEEDED')
    stats=dict(rows=len(units),nights=len(nights),total_individuals=total,
        total_active_search_seconds=exposure,total_active_search_hours=hours)
    a=_number(protocol['prior']['alpha'])+total
    b=_number(protocol['prior']['beta_active_search_hours'])+hours
    caps=protocol['capacities']
    if not (math.isfinite(a) and math.isfinite(b) and caps['min_shape']<=a<=caps['max_shape']
            and caps['min_rate_hours']<=b<=caps['max_rate_hours']):
        raise CountActivityCapacityError('NUMERICAL_CAPACITY_EXCEEDED')
    return stats,dict(shape=a,rate_active_search_hours=b)


def _model_fields():
    return {'schema_version','phase','target','protocol','protocol_sha256','owner_id','observer_id','method_version',
        'fit_cutoff','heldout_night','training_units','sufficient_statistics','posterior','input_digests',
        'lineage','runtime_versions','python_version','cohort_sha256','model_sha256'} | set(_flags())


def _validate_model(model, protocol, budget):
    _fields(model,_model_fields())
    if model['schema_version']!=MODEL_VERSION or model['phase']!='DEVELOPMENT' or model['target']!=TARGET:
        raise ValueError('Registered development count model required')
    for name,value in _flags().items():
        if type(model[name]) is not type(value) or model[name]!=value:
            raise ValueError('Count model cannot grant source, science or production authority')
    if model['protocol']!=protocol or _hash(model['protocol_sha256'])!=digest(protocol):
        raise ValueError('Frozen protocol/model binding mismatch')
    if model['runtime_versions']!=RUNTIME_VERSIONS or type(model['python_version']) is not str:
        raise ValueError('Model runtime binding mismatch')
    cutoff=_stamp(model['fit_cutoff']);heldout=selection_gate._night(model['heldout_night'])
    if not _stamp(protocol['frozen_at'])<cutoff<_stamp(heldout+'T07:00:00+09:00'):
        raise ValueError('Frozen protocol and fit must precede heldout-night boundary')
    for name in ('owner_id','observer_id','method_version'):
        if model[name]!=protocol['reference'][name]: raise ValueError('Reference and fitted observer/search mode differ')
    for name,fields in [('input_digests',INPUT_FIELDS),('lineage',LINEAGE_FIELDS)]:
        _fields(model[name],fields)
        for value in model[name].values(): _hash(value)
    if type(model['training_units']) is not list or not model['training_units']:
        raise ValueError('Nonempty declared training unit table required')
    if len(model['training_units'])>protocol['capacities']['max_training_units']:
        raise CountActivityCapacityError('TRAINING_UNIT_CAPACITY_EXCEEDED')
    identities=set();physical=set();previous=None
    for row in model['training_units']:
        budget.check();_fields(row,UNIT_FIELDS);rid=selection_gate._text(row['row_id'],'row identity')
        night=selection_gate._night(row['night']);window=selection_gate._window(row['window_start_jst'],night)
        cell=selection_gate._cell(row['cell_x']),selection_gate._cell(row['cell_y']),window.astimezone(timezone.utc)
        if rid in identities or cell in physical or previous is not None and rid<=previous or night>=heldout or window>=cutoff:
            raise ValueError('Unique ordered strictly earlier training units required')
        identities.add(rid);physical.add(cell);previous=rid
    stats,posterior=_statistics(model['training_units'],protocol,budget)
    if (canonical_bytes(model['sufficient_statistics'])!=canonical_bytes(stats)
            or canonical_bytes(model['posterior'])!=canonical_bytes(posterior)):
        raise ValueError('Posterior must reproduce from the declared cohort')
    cohort={name:model[name] for name in ('target','owner_id','observer_id','method_version','fit_cutoff','heldout_night','training_units')}
    if _hash(model['cohort_sha256'])!=digest(cohort) or _hash(model['model_sha256'])!=digest({k:v for k,v in model.items() if k!='model_sha256'}):
        raise ValueError('Count model digest mismatch')
    budget.check();return model


def _result(status, budget, **values):
    budget.check()
    return dict(schema_version='habu-gamma-poisson-result-v1', status=status,
        target=TARGET, runtime_elapsed_seconds=time.monotonic()-budget.entered, **values, **_flags())


def fit_gamma_poisson(selection, count_projection, effort_projection, *, protocol, budget_seconds=300):
    """Compute a declared posterior after the existing count/effort gate only."""
    budget=_Budget(budget_seconds,300)
    (selected,count,effort,protocol),size,nodes=_owned([selection,count_projection,effort_projection,protocol],budget)
    protocol=_protocol(protocol,budget,mode='fit',input_bytes=size,nodes=nodes)
    if selected is None:
        return _result('DATA_BLOCKED',budget,model=None,missing_requirements=['TRAINING_SELECTION_REQUIRED'])
    assessment=feasibility.assess_count_feasibility(selected,count,effort,
        budget_seconds=budget.remaining(),check=budget.check)
    if assessment['status']=='NEED_MORE_DATA':
        return _result('DATA_BLOCKED',budget,model=None,missing_requirements=assessment['blockers'],feasibility=assessment)
    try:versions,_=_runtime(budget)
    except _RuntimeBindingError:
        return _result('RUNTIME_BINDING_ERROR',budget,model=None,missing_requirements=['PINNED_ANALYSIS_RUNTIME_REQUIRED'])
    by_count={r['row_id']:r for r in count['rows']};by_effort={r['row_id']:r for r in effort['rows']}
    units=[]
    for row in sorted(selected['accepted'],key=lambda r:r['row_id']):
        budget.check();unit={k:row[k] for k in feasibility.UNIT}
        unit.update(count=by_count[row['row_id']]['count'],active_search_seconds=float(by_effort[row['row_id']]['active_search_seconds']))
        units.append(unit)
    try:statistics,posterior=_statistics(units,protocol,budget)
    except CountActivityCapacityError as exc:
        return _result('NUMERICAL_CAPACITY_EXCEEDED',budget,model=None,missing_requirements=[str(exc)])
    model=dict(schema_version=MODEL_VERSION,phase='DEVELOPMENT',target=TARGET,protocol=protocol,
        protocol_sha256=digest(protocol),fit_cutoff=selected['fit_cutoff'],heldout_night=selected['heldout_night'],
        **{k:count[k] for k in ('owner_id','observer_id','method_version')},training_units=units,
        sufficient_statistics=statistics,posterior=posterior,input_digests=dict(
            selection=digest(selected),count_projection=digest(count),effort_projection=digest(effort)),
        lineage={k:assessment[k] for k in ('selection_sha256','corpus_sha256','count_projection_sha256','effort_projection_sha256')},
        runtime_versions=versions,python_version=sys.version.split()[0],**_flags())
    model['lineage']['feasibility_assessment_sha256']=assessment['assessment_sha256']
    model['cohort_sha256']=digest({k:model[k] for k in ('target','owner_id','observer_id','method_version','fit_cutoff','heldout_night','training_units')})
    model['model_sha256']=digest(model);_validate_model(model,protocol,budget)
    return _result('POSTERIOR_COMPUTED',budget,model=model,missing_requirements=[],feasibility=assessment)


def validate_gamma_poisson_model(model, *, protocol, budget_seconds=30):
    """Reproduce declared sufficient statistics and posterior; not source truth."""
    budget=_Budget(budget_seconds,30)
    (model,protocol),size,nodes=_owned([model,protocol],budget)
    protocol=_protocol(protocol,budget,mode='predict',input_bytes=size,nodes=nodes)
    _runtime(budget)
    return _validate_model(model,protocol,budget)


def _moments(a, b, exposure, protocol):
    """One shared shape/rate arithmetic kernel; no marginal quantile calls."""
    caps=protocol['capacities'];result=dict(exposure_hours=exposure,mean=None,variance=None,
        probability_zero=None,log_probability_zero=None,probability_zero_underflowed=False,
        probability_at_least_one=None,numerical_status='NUMERICAL_CAPACITY_EXCEEDED')
    if not 0<=exposure<=caps['max_exposure_hours']:return result
    ratio=exposure/b;mean=ratio*a;variance=mean+ratio*mean
    # Positive shape/exposure imply a strictly positive mathematical mean.
    # Underflow is unsupported arithmetic, not an observed/predicted zero.
    if exposure>0 and (ratio==0 or mean==0):return result
    if not all(math.isfinite(x) for x in (ratio,mean,variance)):return result
    logzero=-a*math.log1p(ratio)
    if not math.isfinite(logzero):return result
    probability_zero=math.exp(logzero)
    result.update(mean=mean,variance=variance,probability_zero=probability_zero,
        log_probability_zero=logzero,probability_zero_underflowed=probability_zero==0 and logzero<0,
        probability_at_least_one=-math.expm1(logzero),
        numerical_status='VERIFIED_DEGENERATE_ZERO' if exposure==0 else 'VERIFIED_MOMENTS_NOT_CALIBRATED')
    return result


def _distribution(a, b, exposure, protocol, nbinom, budget):
    result=_moments(a,b,exposure,protocol)
    result.update(quantiles=None,numerical_status='NUMERICAL_CAPACITY_EXCEEDED')
    if result['mean'] is None:return result
    caps=protocol['capacities'];ratio=exposure/b
    if exposure==0:
        result.update(quantiles=[dict(probability=q,count=0) for q in protocol['quantiles']],numerical_status='VERIFIED_DEGENERATE_ZERO')
        return result
    p=1/(1+ratio)
    if not 0<p<1:return result
    quantiles=[];previous=-1
    for q in protocol['quantiles']:
        budget.check()
        try:
            k=float(nbinom.ppf(q,a,p));budget.check()
            if not math.isfinite(k) or k<0 or not k.is_integer():
                result['numerical_status']='NUMERICAL_NONCONVERGENCE';return result
            if k>caps['max_output_count']:return result
            k=int(k)
            cdf=float(nbinom.cdf(k,a,p));lower=float(nbinom.cdf(k-1,a,p))
            logcdf=float(nbinom.logcdf(k,a,p));logsf=float(nbinom.logsf(k,a,p))
            logsf_lower=float(nbinom.logsf(k-1,a,p));budget.check()
            tol=protocol['numerics']['cdf_absolute_tolerance'];logtol=protocol['numerics']['log_tail_tolerance']
            if (not all(math.isfinite(x) for x in (cdf,lower,logcdf,logsf,logsf_lower)) or
                    not 0<=lower<=cdf<=1 or cdf+tol<q or logcdf+logtol<math.log(q) or
                    logsf>math.log1p(-q)+logtol or
                    not logsf_lower>math.log1p(-q) or k<previous):
                result['numerical_status']='NUMERICAL_NONCONVERGENCE';return result
        except (ValueError,OverflowError,FloatingPointError):
            result['numerical_status']='NUMERICAL_NONCONVERGENCE';return result
        quantiles.append(dict(probability=q,count=k));previous=k
    result.update(quantiles=quantiles,numerical_status='VERIFIED_MODEL_BASED_NOT_CALIBRATED')
    return result


def _prediction_inputs(model, planned_effort_inputs, protocol, budget):
    """Common raw-source projector and native model gates, under one deadline."""
    try:
        (model,plan,protocol),size,nodes=_owned([model,planned_effort_inputs,protocol],budget)
    except UnicodeEncodeError:
        return None,_result('DATA_BLOCKED',budget,predictions=None,produced_outputs=[],missing_requirements=['UNSUPPORTED_INPUT_UTF8'])
    protocol=_protocol(protocol,budget,mode='predict',input_bytes=size,nodes=nodes)
    if model is None or plan is None:
        return dict(protocol=protocol),_result('DATA_BLOCKED',budget,predictions=None,produced_outputs=[],missing_requirements=['MODEL_AND_PLANNED_INPUTS_REQUIRED'])
    try:versions,nbinom=_runtime(budget)
    except _RuntimeBindingError:
        return dict(protocol=protocol),_result('RUNTIME_BINDING_ERROR',budget,predictions=None,produced_outputs=[],missing_requirements=['PINNED_ANALYSIS_RUNTIME_REQUIRED'])
    model=_validate_model(model,protocol,budget);_fields(plan,PLAN_FIELDS)
    text=plan['raw_plan_utf8']
    if text is not None and type(text) is not str:raise ValueError('Original UTF8 text or None required')
    if text is not None and len(text)>MAX_RAW_BYTES:raise CountActivityCapacityError('RAW_PLAN_CAPACITY_EXCEEDED')
    try:raw=None if text is None else text.encode('utf-8')
    except UnicodeEncodeError:
        return dict(protocol=protocol),_result('DATA_BLOCKED',budget,predictions=None,produced_outputs=[],missing_requirements=['UNSUPPORTED_PLAN_UTF8'])
    if raw is not None and len(raw)>MAX_RAW_BYTES:raise CountActivityCapacityError('RAW_PLAN_CAPACITY_EXCEEDED')
    context=ProspectiveReadContext(budget.remaining(),MAX_BYTES)
    try:
        projected=project_planned_effort(raw,plan['domain'],plan['bindings'],
            expected_domain_sha256=plan['expected_domain_sha256'],expected_identity=plan['expected_identity'],
            as_of_time=plan['as_of_time'],context=context)
    except ValueError as exc:
        # The existing projector checks physical SHA before rejecting a BOM in
        # its strict token scanner. Preserve it; never normalize original bytes.
        if (text is not None and text.startswith('\ufeff') and
                (type(exc) is json.JSONDecodeError or str(exc)=='No bool/nonfinite/non-JSON planned-source tokens')):
            return dict(protocol=protocol),_result('DATA_BLOCKED',budget,predictions=None,produced_outputs=[],missing_requirements=['PLAN_BOM_UNSUPPORTED_BY_EXISTING_PROJECTOR'])
        raise
    budget.check()
    if projected['status']!='DECLARED_PLAN_PROJECTED':
        return dict(protocol=protocol),_result('DATA_BLOCKED',budget,predictions=None,produced_outputs=[],missing_requirements=projected['blockers'])
    if len(projected['rows'])>protocol['capacities']['max_planned_units']:
        raise CountActivityCapacityError('PLANNED_UNIT_CAPACITY_EXCEEDED')
    for name in ('owner_id','observer_id','method_version'):
        if projected['identity'][name]!=model[name]:raise ValueError('Plan and fitted observer/search mode differ')
    cutoff=_stamp(projected['cutoff_time']);night=projected['operational_night']
    if not _stamp(model['fit_cutoff'])<cutoff:raise ValueError('Fit must strictly precede own prediction cutoff')
    boundary=_stamp(night+'T07:00:00+09:00')
    if any(row['night']>=night or _stamp(row['window_start_jst'])>=boundary for row in model['training_units']):
        raise ValueError('Training rows cannot include the predicted operational night')
    return dict(model=model,plan=plan,protocol=protocol,projected=projected,raw=raw,
        versions=versions,nbinom=nbinom,night=night),None


def _aggregate_prediction(prepared,budget):
    model,plan,protocol,projected=(prepared[k] for k in ('model','plan','protocol','projected'))
    versions,nbinom,night=(prepared[k] for k in ('versions','nbinom','night'))
    exposure=math.fsum(row['planned_active_search_seconds'] for row in projected['rows'])/3600
    a=model['posterior']['shape'];b=model['posterior']['rate_active_search_hours']
    count=_distribution(a,b,exposure,protocol,nbinom,budget)
    proxy=_distribution(a,b,protocol['reference']['active_search_hours'],protocol,nbinom,budget)
    proxy['reference']=protocol['reference']
    statuses={x['numerical_status'] for x in (count,proxy)}
    status='NUMERICAL_CAPACITY_EXCEEDED' if 'NUMERICAL_CAPACITY_EXCEEDED' in statuses else 'NUMERICAL_NONCONVERGENCE' if 'NUMERICAL_NONCONVERGENCE' in statuses else 'PREDICTED'
    predictions=dict(conditional_capture_count=count,capture_activity_proxy=proxy)
    produced=[name for name,value in [('planned_capture_count',count),('capture_activity_proxy',proxy)]
              if value['mean'] is not None]
    deterministic=dict(model_sha256=model['model_sha256'],protocol_sha256=digest(protocol),
        planned_effort_receipt_sha256=projected['receipt_sha256'],predictions=predictions)
    return _result(status,budget,model_sha256=model['model_sha256'],protocol_sha256=digest(protocol),
        runtime_versions=versions,training_cutoff=model['fit_cutoff'],operational_night=night,
        numerical_protocol={k:protocol[k] for k in ('quantiles','numerics','capacities')},
        cutoff_time=projected['cutoff_time'],forecast_window=plan['domain']['horizon'],
        planned_effort_receipt_sha256=projected['receipt_sha256'],planned_source_sha256=projected['source_sha256'],
        predictions=predictions,produced_outputs=produced,
        prediction_sha256=digest(deterministic),missing_requirements=[] if status=='PREDICTED' else [status],
        assumptions=['CONDITIONAL_ON_DECLARED_FUTURE_SEARCH_PLAN','SHARED_GAMMA_RATE_INDUCES_CROSS_UNIT_COVARIANCE',
                     'MODEL_BASED_UNCALIBRATED_CAPTURE_PROXY_NOT_BIOLOGICAL_ACTIVITY_OR_DETECTION'])


def predict_gamma_poisson(model, planned_effort_inputs, *, protocol, budget_seconds=30):
    """Predict conditional on an exact UTF-8 future plan through its real gate.

    Quantile verification is cooperative, not hard preemption of native SciPy.
    A missing/failed interval never acquires calibrated or biological validity.
    The existing deterministic result/ID has no unit-detail additions.
    """
    budget=_Budget(budget_seconds,30)
    prepared,blocked=_prediction_inputs(model,planned_effort_inputs,protocol,budget)
    return blocked if blocked is not None else _aggregate_prediction(prepared,budget)


def _unit_digest(value,budget,limit):
    """Canonical SHA with the shared deadline and explicit output byte cap."""
    sha=hashlib.sha256();size=0
    encoder=json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    for chunk in encoder.iterencode(value):
        budget.check();raw=chunk.encode('utf-8');size+=len(raw)
        if size>limit:raise CountActivityCapacityError('UNIT_OUTPUT_BYTE_CAPACITY_EXCEEDED')
        sha.update(raw)
    budget.check();return sha.hexdigest()


def _unit_details(prepared,budget):
    model,protocol,projected=(prepared[k] for k in ('model','protocol','projected'))
    limit=protocol['capacities']['max_json_bytes']
    # The immutable UTF-8 bytes already passed the actual physical-source and
    # future-plan projector. Reuse its strict decoder to recover exact original
    # allocation strings, not an inverse reconstruction from ten-minute totals.
    source=_decode_raw(prepared['raw'],budget.check,0)
    if _unit_digest(source,budget,limit)!=projected['source_canonical_sha256']:
        raise ValueError('Validated original source and projection disagree')
    lineage=dict(model_sha256=model['model_sha256'],protocol_sha256=digest(protocol),
        planned_effort_receipt_sha256=projected['receipt_sha256'],
        planned_source_sha256=projected['source_sha256'],source_canonical_sha256=projected['source_canonical_sha256'],
        domain_canonical_sha256=projected['domain_canonical_sha256'],
        plan_id=source['plan_id'],revision_id=source['revision_id'])
    lineage_sha=_unit_digest(lineage,budget,limit)
    intersections={row['row_id']:[] for row in projected['rows']};originals=[]
    horizon=_stamp(prepared['plan']['domain']['horizon']['start']).astimezone(timezone.utc)
    utc=lambda stamp:stamp.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    for allocation in source['allocations']:
        budget.check();allocation_sha=_unit_digest(allocation,budget,limit)
        originals.append(dict(allocation=allocation,allocation_sha256=allocation_sha))
        first=_stamp(allocation['start']).astimezone(timezone.utc)
        last=_stamp(allocation['end']).astimezone(timezone.utc)
        cursor=first;contributed=0
        while cursor<last:
            budget.check();index=int((cursor-horizon).total_seconds())//600
            window=horizon+timedelta(seconds=index*600)
            end=min(last,window+timedelta(seconds=600));seconds=int((end-cursor).total_seconds())
            rid=f"{allocation['cell_x']}:{allocation['cell_y']}@{utc(window)}"
            if rid not in intersections or seconds<=0:
                raise ValueError('Validated allocation escapes original projected units')
            intersections[rid].append(dict(allocation_id=allocation['allocation_id'],
                allocation_sha256=allocation_sha,start_utc=utc(cursor),end_utc=utc(end),
                planned_active_search_seconds=seconds))
            contributed+=seconds;cursor=end
        if contributed!=allocation['planned_active_search_seconds']:
            raise ValueError('Original allocation intersection duration mismatch')
    a=model['posterior']['shape'];b=model['posterior']['rate_active_search_hours'];rows=[]
    for projected_row in projected['rows']:
        budget.check();parts=intersections[projected_row['row_id']]
        seconds=projected_row['planned_active_search_seconds']
        if sum(part['planned_active_search_seconds'] for part in parts)!=seconds:
            raise ValueError('Original allocations do not reproduce planned unit seconds')
        moments=_moments(a,b,seconds/3600,protocol);budget.check()
        rows.append(dict(**projected_row,window_end_utc=utc(_stamp(projected_row['window_start_utc'])+timedelta(seconds=600)),
            exposure_hours=moments['exposure_hours'],mean=moments['mean'],variance=moments['variance'],
            numerical_status=moments['numerical_status'],allocation_intersections=parts,lineage_sha256=lineage_sha))
    return rows,originals,lineage


def _unit_output_check(value,budget,byte_limit,node_limit):
    # Count the complete returned JSON, including seals/operational fields.
    # Iteration touches only generated/copied exact builtins, never callbacks.
    stack=[value];nodes=0
    while stack:
        budget.check();item=stack.pop();nodes+=1
        if nodes>node_limit:raise CountActivityCapacityError('UNIT_OUTPUT_NODE_CAPACITY_EXCEEDED')
        if type(item) is dict:stack.extend(item.values())
        elif type(item) is list:stack.extend(item)
    _unit_digest(value,budget,byte_limit)


def predict_gamma_poisson_units(model, planned_effort_inputs, *, protocol, budget_seconds=30):
    """Return the unchanged native aggregate and complete original-plan units.

    Input contract is exactly predict_gamma_poisson's closed raw-plan request;
    caller-supplied projections, actual GPS effort and modified/subset plans do
    not bypass its existing gates. Units share one Gamma rate: these means add,
    but marginal variances/quantiles must not be summed into an aggregate
    interval. No spatial differentiation, subset owner intent, route feasibility
    or source/biology/production authentication is created.

    Original allocations retain exact decoded field strings/IDs/durations and
    canonical allocation hashes, bound to unchanged physical UTF-8 source SHA.
    Unit intersections are half-open durations, not measurements or new intent.
    No per-unit PPF runs. Missing/underflow moments remain None. The distinct
    envelope seal excludes only the two named operational elapsed fields.
    Exceptions and blocked-result semantics remain those of the native API.
    """
    budget=_Budget(budget_seconds,30)
    prepared,blocked=_prediction_inputs(model,planned_effort_inputs,protocol,budget)
    aggregate=blocked if blocked is not None else _aggregate_prediction(prepared,budget)
    rows=originals=lineage=None;unit_status='NOT_PRODUCED';status=aggregate['status']
    limit=MAX_BYTES;node_limit=MAX_NODES;missing=list(aggregate['missing_requirements'])
    if prepared is not None:
        limit=prepared['protocol']['capacities']['max_json_bytes']
        node_limit=prepared['protocol']['capacities']['max_json_nodes']
    if blocked is None:
        rows,originals,lineage=_unit_details(prepared,budget)
        failed=any(row['mean'] is None for row in rows)
        unit_status='PARTIAL_NUMERICAL_CAPACITY_EXCEEDED' if failed else 'MOMENTS_COMPUTED_CONDITIONAL'
        if failed:
            status='NUMERICAL_CAPACITY_EXCEEDED'
            missing=sorted(set(missing+['UNIT_MOMENTS_NUMERICAL_CAPACITY_EXCEEDED']))
    result=dict(schema_version='habu-gamma-poisson-units-result-v1',status=status,target=TARGET,
        aggregate_prediction=aggregate,unit_predictions=rows,original_allocations=originals,lineage=lineage,
        unit_prediction_status=unit_status,missing_requirements=missing,
        produced_outputs=['planned_capture_count_unit_moments'] if rows is not None and any(r['mean'] is not None for r in rows) else [],
        domain_physical_bytes_verified=False,code_physical_bytes_verified=False,
        owner_plan_modified=False,owner_subset_intent_authenticated=False,
        assumptions=['CONDITIONAL_ON_THE_COMPLETE_SAME_ORIGINAL_FUTURE_PLAN',
            'ONE_COMMON_GAMMA_RATE_NO_SPATIAL_DIFFERENTIATION',
            'SHARED_GAMMA_RATE_INDUCES_CROSS_UNIT_COVARIANCE',
            'MARGINAL_VARIANCES_OR_QUANTILES_ARE_NOT_AN_AGGREGATE_INTERVAL'],
        omitted_operational_fields=['runtime_elapsed_seconds','aggregate_prediction.runtime_elapsed_seconds'],**_flags())
    sealed=dict(result,aggregate_prediction={k:v for k,v in aggregate.items() if k!='runtime_elapsed_seconds'})
    result['unit_prediction_sha256']=_unit_digest(sealed,budget,limit)
    result['runtime_elapsed_seconds']=time.monotonic()-budget.entered
    _unit_output_check(result,budget,limit,node_limit)
    budget.check();return result
