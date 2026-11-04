"""Fixed, JSON-only research inference adapters. No source or issuance authority.

Only this module owns dispatch. Supplied closures/times are declarations, never
authenticated runtime or historical availability. Budgets are cooperative; one
native arithmetic operation or import is not hard-preemptible.

The planned-unit adapter consumes native Gamma state, {plan} and {protocol};
its planned_count_units port retains the full original-plan unit envelope.
The detection adapter is stateless {}, consumes {bundle} and {protocol}, and
exposes only detection_opportunity_diagnostic. Both ports retain source/native
seals and unknowns; partial diagnostics cannot satisfy a complete mandatory
output. Neither is a formal target, route intent or biological activity model.
The conditional-route adapter consumes native Gamma state and requires its full
typed canonical digest to equal decision_input.model. Its complete native route
envelope omits only elapsed duration; fewer alternatives remain a partial port.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from time import monotonic

MAX_BYTES = 32 * 1024**2
MAX_NODES = 2_000_000
MAX_DEPTH = 24
MAX_ROWS = 120_000
JST = timezone(timedelta(hours=9))


class _Stop(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


def _fail(code='INVALID_INPUT'):
    raise _Stop('FAIL', code)


class _Budget:
    def __init__(self, seconds):
        if type(seconds) is not int and type(seconds) is not float:
            _fail('INVALID_BUDGET')
        if not 0 < seconds <= 300 or not math.isfinite(seconds):
            _fail('INVALID_BUDGET')
        self.deadline = monotonic() + seconds

    def check(self):
        if monotonic() >= self.deadline:
            raise _Stop('BUDGET_BLOCKED', 'SHARED_DEADLINE_EXCEEDED')

    def remaining(self):
        remaining=self.deadline-monotonic()
        if remaining<=0:
            raise _Stop('BUDGET_BLOCKED','SHARED_DEADLINE_EXCEEDED')
        return remaining


def _owned(value, budget):
    """Reject custom types before iteration/comparison; no candidate callbacks."""
    nodes, byte_count, active = 0, 0, set()

    def visit(item, depth):
        nonlocal nodes, byte_count
        budget.check()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise _Stop('CAPACITY_BLOCKED', 'JSON_CAPACITY')
        kind = type(item)
        if kind is str:
            if len(item) > MAX_BYTES:
                raise _Stop('CAPACITY_BLOCKED', 'JSON_CAPACITY')
            byte_count += len(item.encode('utf-8')) + 2
            result = item
        elif kind is int:
            if item.bit_length() > 256:
                _fail('INTEGER_CAPACITY')
            byte_count += 80
            result = item
        elif kind is float:
            if not math.isfinite(item):
                _fail('NONFINITE_JSON')
            byte_count += 32
            result = item
        elif kind is bool or item is None:
            byte_count += 5
            result = item
        elif kind is dict or kind is list:
            if id(item) in active:
                _fail('JSON_CYCLE')
            if len(item) > MAX_NODES:
                raise _Stop('CAPACITY_BLOCKED', 'JSON_CAPACITY')
            active.add(id(item))
            byte_count += len(item) * 2 + 2
            if kind is dict:
                result = {}
                for key, val in item.items():
                    if type(key) is not str:
                        _fail('JSON_KEY_TYPE')
                    result[visit(key, depth+1)] = visit(val, depth+1)
            else:
                result = [visit(val, depth+1) for val in item]
            active.remove(id(item))
        else:
            _fail('BUILTIN_JSON_ONLY')
        if byte_count > MAX_BYTES:
            raise _Stop('CAPACITY_BLOCKED', 'JSON_CAPACITY')
        return result

    return visit(value, 0)


def _digest(value, budget=None):
    count, h = 0, hashlib.sha256()
    for chunk in json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                  allow_nan=False).iterencode(value):
        if budget:
            budget.check()
        raw = chunk.encode('utf-8')
        count += len(raw)
        if count > MAX_BYTES:
            raise _Stop('CAPACITY_BLOCKED', 'JSON_CAPACITY')
        h.update(raw)
    return h.hexdigest()


def _fields(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        _fail('EXACT_FIELDS_REQUIRED')


def _hash(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
        _fail('HASH_FORMAT')
    return value


def _name(value):
    if type(value) is not str or not re.fullmatch('[A-Za-z][A-Za-z0-9_.-]{0,127}', value):
        _fail('IDENTITY_FORMAT')
    return value


def _time(value):
    if type(value) is not str or len(value) > 64:
        _fail('AWARE_TIME_REQUIRED')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        _fail('AWARE_TIME_REQUIRED')
    return result


def _number(value, low, high):
    if type(value) is not int and type(value) is not float:
        _fail('FINITE_NUMBER_REQUIRED')
    if not low <= value <= high or not math.isfinite(value):
        _fail('NUMERIC_RANGE')
    return value


def _context(cutoff, night=None, end=None):
    start = _time(cutoff)
    local = start.astimezone(JST)
    own_night = (local - timedelta(hours=7)).date().isoformat()
    if night is not None and own_night != night:
        _fail('NIGHT_CUTOFF_MISMATCH')
    boundary = datetime.fromisoformat(own_night+'T07:00:00+09:00') + timedelta(days=1)
    finish = boundary if end is None else _time(end)
    if not start < finish <= boundary:
        _fail('FORECAST_HORIZON')
    return start, finish, own_night


def _flags():
    return dict(source_authentication='NOT_ATTESTED', scientific_status='NOT_VALIDATED',
                policy_admission='NOT_ATTESTED',
                fit_authorized=False, selection_authorized=False, production_authorized=False,
                official_issuance_authorized=False)


# Data only. Callables are selected by literal branches below, never by input.
_SPECS = (
    ('legacy_spatial_v1', ('universe_rows',), (('spatial_rows','LEGACY_SPATIAL_SCORE_AND_OPTIONAL_UNIT_PROBABILITY','native'),), ()),
    ('hba1_unit_v1', ('forecast_rows','joined_universe_sha256','cutoff_time'), (('unit_predictions','OWNER_CAPTURE_BINARY_GIVEN_QUALIFIED_OBSERVED_100M_10MIN_UNIT','probability'),), ()),
    ('hba2_unit_v1', ('forecast_rows','joined_universe_sha256','cutoff_time'), (('unit_predictions','OWNER_CAPTURE_BINARY_GIVEN_QUALIFIED_OBSERVED_100M_10MIN_UNIT','probability'),), ()),
    ('constant_poisson_scenario_v1', ('active_search_seconds',), (('count_scenario','COUNTERFACTUAL_EXPOSURE_CONDITIONAL_COUNT_NOT_FORECAST','individuals'),), ()),
    ('gamma_poisson_planned_count_v1', ('plan',), (
        ('planned_capture_count','CAPTURE_COUNT_CONDITIONAL_ON_DECLARED_FUTURE_SEARCH_PLAN','individuals'),
        ('capture_activity_proxy','STANDARDIZED_CAPTURE_PROXY_NOT_BIOLOGICAL_ACTIVITY_OR_DETECTION','individuals')), ()),
    ('gamma_poisson_planned_units_v1', ('plan',), (('planned_count_units','UNIT_MOMENTS_CONDITIONAL_ON_COMPLETE_ORIGINAL_PLAN_SHARED_GAMMA_NOT_ROUTE_INTENT','individuals'),), ()),
    ('independent_opportunity_detection_v1', ('bundle',), (('detection_opportunity_diagnostic','CONDITIONAL_INDEPENDENT_OPPORTUNITY_DIAGNOSTIC_NOT_BIOLOGICAL_ACTIVITY','diagnostic'),), ()),
    ('time_target_candidates_v1', ('unit_predictions','cutoff_time','forecast_end'), (('candidate_time_targets','DECLARED_CELL_CENTRE_INDIVIDUAL_TARGET_CANDIDATES','target_tokens'),), ('unit_predictions',)),
    ('conditional_route_candidates_v1', ('graph_input','decision_input'), (('conditional_route_candidates','CONDITIONAL_ORIGINAL_PLAN_ROUTE_CANDIDATES_NOT_NAVIGATION_OR_OWNER_INTENT','route_candidates'),), ()),
)


def adapter_contract(adapter_id):
    """Detached schema descriptor; None means no registered executor."""
    if type(adapter_id) is not str:
        return None
    for identifier, inputs, outputs, dependencies in _SPECS:
        if identifier == adapter_id:
            shape = dict(fields=list(inputs), allowed_dependency_slots=list(dependencies))
            out = {name:dict(semantics=semantics, unit=unit) for name,semantics,unit in outputs}
            return dict(adapter_id=identifier, adapter_version='1', input_schema=shape, output_schema=out,
                        input_schema_sha256=_digest(shape), output_schema_sha256=_digest(out))
    return None


def describe_adapters():
    return [adapter_contract(row[0]) for row in _SPECS]


def required_code_paths():
    """Conservative fixed local-module closure; hashes still need trusted reading."""
    return sorted({
        'src/output_adapters.py', 'src/composite_inference.py', 'src/model_evaluation.py',
        'src/master_contracts.py', 'src/pdca_pipeline.py', 'src/gpx_audit.py',
        'src/models/hba1_feature_candidate.py', 'src/models/hba2_feature_candidate.py',
        'src/models/research_selection.py', 'src/prospective_candidate_model.py',
        'src/models/constant_poisson_diagnostic.py', 'src/models/count_feasibility.py',
        'src/g0_forecast_contract.py', 'requirements-analysis.txt', 'requirements-osm.txt',
        'src/_owner_capture_occurrence_core.py', 'src/aug31_positive_source_review.py',
        'src/august_positive_source_review.py', 'src/codex_cycle_contract.py',
        'src/evaluation/feature_candidate_calibration_source.py', 'src/evaluation/full_ledger_stage1.py',
        'src/evaluation/stage1_score_summary_transport_v2.py', 'src/evaluation/stage1_source_adapter.py',
        'src/event_matching.py', 'src/evidence_audit.py', 'src/g0_full_universe_score_summary.py',
        'src/g0_full_universe_score_summary_v2.py', 'src/g0_training_source_contract.py',
        'src/gpx_attachment_archive.py', 'src/master_inventory.py',
        'src/models/feature_candidate_diagnostics.py', 'src/models/hierarchy_shrinkage.py',
        'src/models/occupancy_shrinkage.py', 'src/prospective_inputs.py',
        'src/research_candidate_config_source.py', 'src/research_candidate_config_source_v2.py',
        'src/research_candidate_preparation_v3.py', 'src/research_model_adapter.py',
        'src/research_pdca_adapter.py', 'src/research_score_summary_request.py',
        'src/sept28_positive_source_review.py', 'src/training_corpus.py',
        'src/count_activity.py', 'src/g0_planned_effort_projection.py', 'src/detection_evaluation.py',
        'src/route_planning.py', 'src/route_graph.py',
    })


def _window_rows(rows, cutoff, end=None, *, legacy=False, budget):
    start, finish, night = _context(cutoff, end=end)
    if type(rows) is not list or not 1 <= len(rows) <= MAX_ROWS:
        _fail('BOUNDED_NONEMPTY_UNIVERSE_REQUIRED')
    seen, physical = set(), set()
    for row in rows:
        budget.check()
        if type(row) is not dict:
            _fail('ROW_TYPE')
        if legacy:
            required={'row_id','operational_night','cutoff_time','utm_x_m','utm_y_m'}
            if not required.issubset(row) or set(row)-required-{'window_start_jst'}:
                _fail('EXACT_FIELDS_REQUIRED')
            _number(row['utm_x_m'],100000,900000); _number(row['utm_y_m'],0,10000000)
        if row['operational_night'] != night or ('cutoff_time' in row and _time(row['cutoff_time']) != start):
            _fail('ROW_TIME_SCOPE')
        window = _time(row['window_start_jst']) if 'window_start_jst' in row else None
        if window is None and not legacy:
            _fail('WINDOW_REQUIRED')
        if window is not None:
            if not start < window < finish or window + timedelta(minutes=10) > finish:
                _fail('ROW_OUTSIDE_HORIZON')
            if window.astimezone(JST).minute % 10 or window.second or window.microsecond:
                _fail('TEN_MINUTE_WINDOW_REQUIRED')
        if 'cell_x' in row and 'cell_y' in row:
            key=(row['cell_x'],row['cell_y'],window)
        elif 'utm_x_m' in row and 'utm_y_m' in row:
            key=(math.floor(row['utm_x_m']/100),math.floor(row['utm_y_m']/100),window)
        else:
            key=None  # The native future-row validator checks other coordinate representations.
        if key is not None:
            if key in physical:
                _fail('DUPLICATE_PHYSICAL_UNIT')
            physical.add(key)
        identifier = row['row_id']
        if type(identifier) is not str or not identifier or len(identifier)>256 or any(ord(c)<32 for c in identifier):
            _fail('ROW_IDENTITY')
        if identifier in seen:
            _fail('DUPLICATE_UNIT')
        seen.add(identifier)


def _legacy(state, inputs, budget):
    import model_evaluation
    _fields(state, {'schema_version','family','implementation_version','parameters','hyperparameters',
        'status','evidence_refs','training_cutoff','training_data_sha256','feature_schema_sha256',
        'protocol_sha256','code_sha256','produced_outputs','model_id','model_sha256'})
    if (state['schema_version']!='1.0' or state['implementation_version']!=model_evaluation.VERSION or
            state['status']!='CANDIDATE' or state['feature_schema_sha256']!=_digest([])):
        _fail('LEGACY_MODEL_CONTRACT')
    probability = state['family'] in ('uniform','observed_unit_prevalence')
    if state['produced_outputs'] != ['spatial_score'] + (['unit_probability'] if probability else []):
        _fail('LEGACY_CAPABILITIES')
    for field in ('training_data_sha256','protocol_sha256','code_sha256'):
        _hash(state[field])
    rows = inputs['universe_rows']
    cutoff = rows[0]['cutoff_time'] if type(rows) is list and rows else None
    _window_rows(rows, cutoff, legacy=True, budget=budget)
    # In v1 _fit this field is the latest training LABEL availability, not
    # a later fit-process completion time. Preserve its distinct semantics.
    _,_,night=_context(cutoff)
    if _time(state['training_cutoff'])>=_time(night+'T07:00:00+09:00'):
        _fail('LEGACY_LABELS_NOT_BEFORE_EVALUATED_NIGHT')
    # Existing scalar implementation has no callback. Bound rows and check
    # before/after each deterministic chunk, then keep the full output universe.
    result = []
    for at in range(0,len(rows),128):
        budget.check()
        result.extend(model_evaluation.predict_model(state, rows[at:at+128]))
    budget.check()
    return dict(spatial_rows=sorted(result,key=lambda row:row['universe_row_id']))


def _targets(state, inputs, config, budget):
    _fields(state, set())
    _time(inputs['forecast_end'])
    _fields(config, {'target_budget','minimum_score','time_anchor_policy','spatial_center_policy',
                     'overlap_policy','tie_policy','target_semantics'})
    k=config['target_budget']
    if type(k) is not int or not 0 <= k <= 100:
        _fail('TARGET_CAPACITY')
    threshold=_number(config['minimum_score'],0,1)
    if (config['time_anchor_policy']!='WINDOW_MIDPOINT' or config['spatial_center_policy']!='DECLARED_CELL_CENTRE'
            or config['overlap_policy'] not in ('KEEP_ALL','SUPPRESS_200M_1200S')
            or config['tie_policy']!='TIME_THEN_ROW_ID' or config['target_semantics']!='INDIVIDUAL_TOKEN'):
        _fail('TARGET_POLICY')
    rows=inputs['unit_predictions']
    _window_rows(rows, inputs['cutoff_time'], inputs['forecast_end'], budget=budget)
    values=[]
    for row in rows:
        budget.check()
        _fields(row,{'row_id','operational_night','window_start_jst','cell_x','cell_y','area_id_1km',
                     'probability','spatial_score','probability_status'})
        for field in ('cell_x','cell_y'):
            if type(row[field]) is not int:
                _fail('CELL_INTEGER_REQUIRED')
        _number(row['cell_x'],1000,8999);_number(row['cell_y'],0,99999)
        probability=_number(row['probability'],0,1)
        _number(row['spatial_score'],0,1)
        if row['area_id_1km']!=f"utm52n_1km_{row['cell_x']//10}_{row['cell_y']//10}":
            _fail('AREA_CELL_MISMATCH')
        if row['spatial_score'] != probability or row['probability_status']!='NOT_VALIDATED':
            _fail('UNIT_PROBABILITY_SEMANTICS')
        if probability >= threshold:
            values.append((row, _time(row['window_start_jst'])+timedelta(minutes=5)))
    values.sort(key=lambda x:(-x[0]['probability'],x[1],x[0]['row_id']))
    targets=[]
    for row, anchor in values:
        budget.check()
        if len(targets)>=k:
            break
        x,y=row['cell_x']*100+50.,row['cell_y']*100+50.
        if config['overlap_policy']=='SUPPRESS_200M_1200S' and any(
            math.hypot(x-t['utm_x_m'],y-t['utm_y_m'])<=200 and
            abs((anchor-_time(t['time'])).total_seconds())<=1200 for t in targets):
            continue
        targets.append(dict(target_id='candidate-'+row['row_id'], source_unit_id=row['row_id'],
            operational_night=row['operational_night'],utm_x_m=x,utm_y_m=y,time=anchor.isoformat(),
            score=row['probability'],radius_m=100,tolerance_seconds=600,
            point_provenance='DECLARED_CELL_CENTRE_NOT_MEASURED_ROAD_POINT',
            target_semantics='INDIVIDUAL_TOKEN'))
    return dict(candidate_time_targets=targets)


def _port(semantics, unit, payload, budget, empty_reason=None):
    return dict(schema_version='habu-adapter-output-v1', semantics=semantics, unit=unit,
        execution_status='EXECUTED',validity_status='NOT_VALIDATED',missing_requirements=[],
        payload=payload,payload_sha256=_digest(payload,budget),empty_reason=empty_reason)


def _blocked(status, code):
    result=dict(schema_version='habu-adapter-execution-v1',status=status,missing_requirements=[code],
                produced_outputs=[],outputs={},native_payload=None,**_flags())
    result['execution_sha256']=_digest(result)
    return result


def _route_composite_scope(inputs,cutoff,night,end):
    """Bind supplied native contexts before execution/missing-artifact paths.

    The composite has no forecast_start field. Native R still binds that start
    to the exact original plan/domain horizon; it is not invented from cutoff.
    """
    contexts=[]
    for field in ('graph_input','decision_input'):
        if field not in inputs or inputs[field] is None:continue
        value=inputs[field]
        if type(value) is not dict:_fail('ROUTE_CONTEXT_OBJECT_REQUIRED')
        context=value.get('context')
        _fields(context,{'operational_night','cutoff_time','forecast_start','forecast_end','mode'})
        if (_time(context['cutoff_time'])!=cutoff or context['operational_night']!=night or
                _time(context['forecast_end'])!=end):
            _fail('ROUTE_COMPOSITE_SCOPE_MISMATCH')
        contexts.append(context)
    decision=inputs.get('decision_input')
    plan=decision.get('planned_effort_inputs') if type(decision) is dict else None
    if type(plan) is dict and type(plan.get('domain')) is dict:
        domain=plan['domain'];horizon=domain['horizon']
        if (_time(domain['cutoff_time'])!=cutoff or domain['operational_night']!=night or
                _time(horizon['end'])!=end or
                any(_time(c['forecast_start'])!=_time(horizon['start']) for c in contexts)):
            _fail('ROUTE_ORIGINAL_PLAN_COMPOSITE_SCOPE_MISMATCH')


def _execute(adapter_id, version, state, inputs, config, budget):
    contract=adapter_contract(adapter_id)
    if contract is None:
        return _blocked('IMPLEMENTATION_BLOCKED','ADAPTER_NOT_IMPLEMENTED')
    if version!='1':
        _fail('ADAPTER_VERSION')
    if type(inputs) is not dict or type(config) is not dict:
        _fail('INPUT_OBJECT_REQUIRED')
    required=set(contract['input_schema']['fields'])
    if set(inputs)-required:
        _fail('UNEXPECTED_INPUT_FIELD')
    if required-set(inputs):
        return _blocked('DATA_BLOCKED','REQUIRED_INPUT_MISSING')
    if adapter_id not in ('time_target_candidates_v1','gamma_poisson_planned_count_v1',
                           'gamma_poisson_planned_units_v1','independent_opportunity_detection_v1',
                           'conditional_route_candidates_v1'):
        _fields(config,set())
    omitted=[]
    if adapter_id=='legacy_spatial_v1':
        native=_legacy(state,inputs,budget)
    elif adapter_id in ('hba1_unit_v1','hba2_unit_v1'):
        from models import hba1_feature_candidate, hba2_feature_candidate
        _window_rows(inputs['forecast_rows'],inputs['cutoff_time'],budget=budget)
        function=hba1_feature_candidate.predict_hba1 if adapter_id=='hba1_unit_v1' else hba2_feature_candidate.predict_hba2
        try:
            native=function(state,inputs['forecast_rows'],cutoff_time=inputs['cutoff_time'],
                joined_universe_sha256=inputs['joined_universe_sha256'],budget_seconds=min(30,budget.remaining()),check=budget.check)
        except (hba1_feature_candidate.HBA1CapacityBlocked,hba2_feature_candidate.HBA2CapacityBlocked):
            raise _Stop('CAPACITY_BLOCKED','NATIVE_CAPACITY') from None
    elif adapter_id=='constant_poisson_scenario_v1':
        from models.constant_poisson_diagnostic import evaluate_constant_poisson_scenario, PoissonCapacityBlocked
        try:
            native=evaluate_constant_poisson_scenario(state,inputs['active_search_seconds'],
                budget_seconds=min(30,budget.remaining()),check=budget.check)
        except PoissonCapacityBlocked:
            raise _Stop('CAPACITY_BLOCKED','NATIVE_CAPACITY') from None
    elif adapter_id in ('gamma_poisson_planned_count_v1','gamma_poisson_planned_units_v1'):
        from count_activity import predict_gamma_poisson, predict_gamma_poisson_units, CountActivityCapacityError
        _fields(config,{'protocol'})
        try:
            function=predict_gamma_poisson if adapter_id=='gamma_poisson_planned_count_v1' else predict_gamma_poisson_units
            native=function(state,inputs['plan'],protocol=config['protocol'],
                                        budget_seconds=min(30,budget.remaining()))
        except CountActivityCapacityError:
            raise _Stop('CAPACITY_BLOCKED','NATIVE_CAPACITY') from None
        # Preserve the complete deterministic numerical/status/provenance
        # projection. Actual elapsed duration is operational metadata and is
        # explicitly not part of native or composite prediction identity.
        native={key:value for key,value in native.items() if key!='runtime_elapsed_seconds'}
        omitted=['runtime_elapsed_seconds']
        if adapter_id=='gamma_poisson_planned_units_v1':
            native['aggregate_prediction']={key:value for key,value in native['aggregate_prediction'].items()
                                            if key!='runtime_elapsed_seconds'}
            omitted.append('aggregate_prediction.runtime_elapsed_seconds')
    elif adapter_id=='independent_opportunity_detection_v1':
        from detection_evaluation import evaluate_detection_opportunities
        _fields(state,set());_fields(config,{'protocol'})
        native=evaluate_detection_opportunities(inputs['bundle'],protocol=config['protocol'],
                                               budget_seconds=min(30,budget.remaining()))
    elif adapter_id=='conditional_route_candidates_v1':
        from route_planning import plan_route_candidates
        _fields(config,{'graph_policy','route_policy'})
        decision=inputs['decision_input']
        if decision is None:return _blocked('DATA_BLOCKED','ROUTE_DECISION_REQUIRED')
        if type(decision) is not dict or 'model' not in decision:_fail('ROUTE_DECISION_MODEL_REQUIRED')
        # Typed canonical JSON distinguishes false/0 and binds every field,
        # not just a caller-supplied model_id or model_sha256 assertion.
        if _digest(state,budget)!=_digest(decision['model'],budget):_fail('ROUTE_STATE_MODEL_MISMATCH')
        native=plan_route_candidates(inputs['graph_input'],decision,graph_policy=config['graph_policy'],
                                    policy=config['route_policy'],budget_seconds=min(30,budget.remaining()))
        native={key:value for key,value in native.items() if key!='runtime_elapsed_seconds'}
        omitted=['runtime_elapsed_seconds']
    else:
        native=_targets(state,inputs,config,budget)
    budget.check()
    native=_owned(native,budget)
    outputs={};status='EXECUTED';missing=[]
    is_gamma=adapter_id=='gamma_poisson_planned_count_v1'
    is_units=adapter_id=='gamma_poisson_planned_units_v1'
    is_detection=adapter_id=='independent_opportunity_detection_v1'
    is_route=adapter_id=='conditional_route_candidates_v1'
    diagnostic_available=False;diagnostic_partial=False
    if is_gamma:
        native_status=native['status']
        if native_status not in ('PREDICTED','DATA_BLOCKED','RUNTIME_BINDING_ERROR',
                                 'NUMERICAL_CAPACITY_EXCEEDED','NUMERICAL_NONCONVERGENCE'):
            _fail('NATIVE_STATUS_INVALID')
        missing=list(native['missing_requirements'])
        if native_status!='PREDICTED':
            status='PARTIAL' if native['produced_outputs'] else native_status
    if is_units:
        native_status=native['status']
        if native_status not in ('PREDICTED','DATA_BLOCKED','RUNTIME_BINDING_ERROR',
                                 'NUMERICAL_CAPACITY_EXCEEDED','NUMERICAL_NONCONVERGENCE'):
            _fail('NATIVE_STATUS_INVALID')
        rows=native['unit_predictions']
        diagnostic_available=rows is not None and any(row['mean'] is not None for row in rows)
        diagnostic_partial=(native_status!='PREDICTED' or
                            native['unit_prediction_status']!='MOMENTS_COMPUTED_CONDITIONAL' or
                            rows is None or any(row['mean'] is None for row in rows))
        missing=list(native['missing_requirements'])
        if diagnostic_partial and not missing:missing=[native['unit_prediction_status']]
        status=('PARTIAL' if diagnostic_partial else 'EXECUTED') if diagnostic_available else native_status
        if not diagnostic_available and status=='PREDICTED':
            status='DATA_BLOCKED';missing=['UNIT_MOMENTS_NOT_PRODUCED']
    if is_detection:
        native_status=native['execution_status']
        if native_status not in ('COMPUTED','PARTIAL','DATA_BLOCKED','RUNTIME_BLOCKED','FAIL'):
            _fail('NATIVE_STATUS_INVALID')
        diagnostic_available=(native_status in ('COMPUTED','PARTIAL') and
            type(native['n']) is int and native['n']>0 and native['known_subset_sensitivity'] is not None)
        diagnostic_partial=native_status!='COMPUTED'
        missing=list(native['blockers'])
        if diagnostic_partial and native['numerical_status'] not in ('NOT_COMPUTED','VERIFIED_MODEL_BASED_NOT_CALIBRATED'):
            missing=sorted(set(missing+[native['numerical_status']]))
        if diagnostic_partial and not missing:missing=[native['reason_code']]
        status=('PARTIAL' if diagnostic_partial else 'EXECUTED') if diagnostic_available else native_status
        if not diagnostic_available and status in ('COMPUTED','PARTIAL'):
            status='DATA_BLOCKED';missing=sorted(set(missing+['EMPIRICAL_DETECTION_NOT_PRODUCED']))
    if is_route:
        native_status=native['execution_status']
        if native_status not in ('COMPUTED_RESEARCH_ONLY','PARTIAL_RESEARCH_ONLY','NO_FEASIBLE_CANDIDATE',
                                 'DATA_BLOCKED','IMPLEMENTATION_BLOCKED','RUNTIME_BLOCKED','FAIL'):
            _fail('NATIVE_STATUS_INVALID')
        diagnostic_available=native_status in ('COMPUTED_RESEARCH_ONLY','PARTIAL_RESEARCH_ONLY') and bool(native['routes'])
        missing=list(native['blockers'])+list(native.get('missing_alternatives',[]))
        diagnostic_partial=(native_status!='COMPUTED_RESEARCH_ONLY' or native['search_exhausted'] or
            bool(native.get('missing_alternatives')) or
            [r['label'] for r in native['routes']]!=config['route_policy']['alternatives']['labels'])
        if diagnostic_available:
            status='PARTIAL' if diagnostic_partial else 'EXECUTED'
            if diagnostic_partial and not missing:missing=['REQUESTED_ROUTE_CANDIDATES_NOT_COMPLETE']
        else:
            status='DATA_BLOCKED' if native_status in ('COMPUTED_RESEARCH_ONLY','PARTIAL_RESEARCH_ONLY','NO_FEASIBLE_CANDIDATE') else native_status
            if not missing:missing=['ROUTE_CANDIDATES_NOT_PRODUCED']
        missing=sorted(set(missing))
    for name,definition in contract['output_schema'].items():
        if is_units or is_detection or is_route:
            if not diagnostic_available:continue
            # Complete deterministic native envelope, including classifications,
            # original allocation lineage and seals. Never a naked mean/probability.
            payload=native
        elif is_gamma:
            if name not in native['produced_outputs']:
                continue
            key='conditional_capture_count' if name=='planned_capture_count' else name
            payload=native['predictions'][key]
            if payload['mean'] is None:
                _fail('NATIVE_PRODUCED_WITHOUT_MEAN')
        else:
            payload=native if name=='count_scenario' else native[name]
        empty='NO_UNITS_MEET_DECLARED_POLICY' if name=='candidate_time_targets' and not payload else None
        outputs[name]=_port(definition['semantics'],definition['unit'],payload,budget,empty)
        if (is_units or is_detection or is_route) and diagnostic_partial:
            outputs[name]['execution_status']='PARTIAL'
            outputs[name]['missing_requirements']=list(missing)
        if is_gamma and payload['numerical_status'] not in ('VERIFIED_MODEL_BASED_NOT_CALIBRATED','VERIFIED_DEGENERATE_ZERO'):
            outputs[name]['execution_status']='PARTIAL'
            outputs[name]['missing_requirements']=[payload['numerical_status']]
    result=dict(schema_version='habu-adapter-execution-v1',adapter_id=adapter_id,adapter_version=version,
        status=status,missing_requirements=missing,produced_outputs=sorted(outputs),outputs=outputs,
        omitted_native_operational_fields=omitted,
        native_payload=native,state_sha256=_digest(state,budget),input_sha256=_digest(inputs,budget),
        config_sha256=_digest(config,budget),**_flags())
    result['execution_sha256']=_digest(result,budget)
    budget.check()
    return result


def execute_adapter(adapter_id, state, inputs, *, config, adapter_version, budget_seconds=30):
    """Execute one reviewed algorithm. Missing capabilities never become outputs."""
    try:
        budget=_Budget(budget_seconds)
        adapter_id,adapter_version,state,inputs,config=_owned([adapter_id,adapter_version,state,inputs,config],budget)
        _name(adapter_id)
        if type(adapter_version) is not str:
            _fail('ADAPTER_VERSION')
        return _execute(adapter_id,adapter_version,state,inputs,config,budget)
    except _Stop as error:
        return _blocked(error.status,error.code)
    except TimeoutError:
        return _blocked('BUDGET_BLOCKED','NATIVE_DEADLINE_EXCEEDED')
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError,UnicodeError):
        return _blocked('FAIL','NATIVE_OR_SCHEMA_INVALID')
