"""Synthetic numeric execution; no real source, fit or issuance authority."""
import copy
from contextlib import nullcontext
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def context():
    return dict(operational_night='2026-10-11', cutoff_time='2026-10-11T18:00:00+09:00',
                forecast_end='2026-10-12T07:00:00+09:00')


def legacy_fixture(score=.25):
    state = dict(schema_version='1.0', family='uniform', implementation_version='bounded-spatial-baselines-v1',
        parameters=dict(default=score, area_values={},smoothing=1.), hyperparameters={}, training_cutoff='2026-10-10T12:00:00+09:00',
        training_data_sha256='a'*64, feature_schema_sha256=digest([]), evidence_refs=[{'protocol_sha256':'b'*64}], protocol_sha256='b'*64, code_sha256='c'*64,
        status='CANDIDATE', produced_outputs=['spatial_score','unit_probability'])
    state['model_id'] = state['model_sha256'] = digest(state)
    rows = [dict(row_id='synthetic-unit', operational_night='2026-10-11', cutoff_time=context()['cutoff_time'],
                 window_start_jst='2026-10-11T20:00:00+09:00', utm_x_m=500050., utm_y_m=3100050.)]
    return state, dict(universe_rows=rows)


def target_config():
    return dict(target_budget=2, minimum_score=.5, time_anchor_policy='WINDOW_MIDPOINT',
        spatial_center_policy='DECLARED_CELL_CENTRE', overlap_policy='KEEP_ALL',
        tie_policy='TIME_THEN_ROW_ID', target_semantics='INDIVIDUAL_TOKEN')


def unit_rows():
    return [dict(row_id='z', operational_night='2026-10-11', window_start_jst='2026-10-11T20:00:00+09:00',
                 cell_x=5000, cell_y=31000, area_id_1km='utm52n_1km_500_3100', probability=.8,
                 spatial_score=.8, probability_status='NOT_VALIDATED'),
            dict(row_id='a', operational_night='2026-10-11', window_start_jst='2026-10-11T20:00:00+09:00',
                 cell_x=5001, cell_y=31000, area_id_1km='utm52n_1km_500_3100', probability=.8,
                 spatial_score=.8, probability_status='NOT_VALIDATED')]


def gamma_fixture(max_count=None):
    from tests.test_count_activity import protocol,plan_fixture,plan_inputs,count_fixture
    from count_activity import fit_gamma_poisson
    p=protocol()
    if max_count is not None:p['capacities']['max_output_count']=max_count
    state=fit_gamma_poisson(*count_fixture(),protocol=p)['model']
    return state,{'plan':plan_inputs(plan_fixture())},{'protocol':p}


class OutputAdapterTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('output_adapters'), 'fixed adapter executor missing')
        self.api = importlib.import_module('output_adapters')

    def run_adapter(self, name='legacy_spatial_v1', state=None, inputs=None, config=None, **kw):
        s, i = legacy_fixture()
        inputs=i if inputs is None else copy.deepcopy(inputs)
        if name in ('hba1_unit_v1','hba2_unit_v1','time_target_candidates_v1'):
            inputs.setdefault('cutoff_time',context()['cutoff_time'])
        if name=='time_target_candidates_v1':inputs.setdefault('forecast_end',context()['forecast_end'])
        return self.api.execute_adapter(name, s if state is None else state, i if inputs is None else inputs,
            config={} if config is None else config, adapter_version='1', **kw)

    def test_real_legacy_scores_change_with_actual_state_and_no_authority(self):
        a=self.run_adapter(); s,i=legacy_fixture(.75); b=self.run_adapter(state=s,inputs=i)
        self.assertEqual(a['outputs']['spatial_rows']['payload'][0]['spatial_score'],.25)
        self.assertEqual(b['outputs']['spatial_rows']['payload'][0]['probability'],.75)
        self.assertNotEqual(a['execution_sha256'],b['execution_sha256'])
        self.assertFalse(a['production_authorized']); self.assertFalse(a['official_issuance_authorized'])
        self.assertEqual(a['source_authentication'],'NOT_ATTESTED')

    def test_real_hba1_numeric_probability_uses_sealed_model(self):
        from tests.test_hba1_feature_candidate import fixture,recipe
        from models import hba1_feature_candidate as model
        _,folds=fixture(); rows=folds[0]['forecast_rows']; spec=recipe()
        state=model.fit_hba1(folds[0]['training_selection'],recipe=spec,expected_recipe_sha256=digest(spec))['model']
        state['coefficients']=[0.] * len(state['coefficients'])
        state['model_sha256']=digest({k:v for k,v in state.items() if k!='model_sha256'})
        result=self.run_adapter('hba1_unit_v1',state,dict(forecast_rows=rows,joined_universe_sha256=digest(rows)))
        self.assertEqual([u['probability'] for u in result['outputs']['unit_predictions']['payload']],[.5]*4)
        self.assertEqual(result['native_payload']['scientific_status'],'NOT_VALIDATED')

    def test_real_hba2_json_tree_numeric_output(self):
        from test_hba2_feature_candidate import synthetic_model,fixture
        from models import hba2_feature_candidate as model
        _,folds=fixture();rows=folds[0]['forecast_rows'];state=synthetic_model(model)
        r=self.run_adapter('hba2_unit_v1',state,dict(forecast_rows=rows,joined_universe_sha256=digest(rows)))
        self.assertEqual([u['probability'] for u in r['outputs']['unit_predictions']['payload']], [round(1/(1+math.exp(-.8)),8)]*4)

    def test_real_count_scenario_is_not_planned_or_biological_forecast(self):
        from tests.test_count_feasibility import fixture
        from models.constant_poisson_diagnostic import fit_constant_poisson
        state=fit_constant_poisson(*fixture())['model']
        r=self.run_adapter('constant_poisson_scenario_v1',state,dict(active_search_seconds=300))
        self.assertEqual(r['outputs']['count_scenario']['payload']['conditional_mean'],1.)
        self.assertEqual(r['native_payload']['status'],'SCENARIO_ONLY')
        self.assertNotIn('expected_capture_count',r['produced_outputs'])
        self.assertNotIn('tonight_activity',r['produced_outputs'])

    def test_unknown_adapter_or_import_string_is_fail_closed(self):
        for name in ['os.system','unknown','not_implemented_future_model']:
            self.assertEqual(self.run_adapter(name)['status'],'IMPLEMENTATION_BLOCKED')

    def test_missing_input_is_blocked_but_outcome_injection_fails(self):
        self.assertEqual(self.run_adapter(inputs={})['status'],'DATA_BLOCKED')
        _,i=legacy_fixture();i['universe_rows'][0]['capture_count']=1
        self.assertEqual(self.run_adapter(inputs=i)['status'],'FAIL')

    def test_nonfinite_custom_and_naive_time_are_rejected_without_callbacks(self):
        calls=[]
        class Meta(type):
            def __eq__(self,other):calls.append('eq');return False
            def __hash__(self):calls.append('hash');return 1
        class Evil(metaclass=Meta):
            def __iter__(self):calls.append('iter');return iter(())
        for value in [Evil(),float('nan'),float('inf'),{'x':Evil()}]:
            self.assertEqual(self.run_adapter(state=value)['status'],'FAIL')
        self.assertEqual(calls,[])
        s,i=legacy_fixture();i['universe_rows'][0]['cutoff_time']='2026-10-11T18:00:00'
        self.assertEqual(self.api.execute_adapter('legacy_spatial_v1',s,i,config={},adapter_version='1')['status'],'FAIL')

    def test_type_depth_and_budget_guards_are_bounded_and_sanitized(self):
        nested={};cur=nested
        for _ in range(40):cur['private']={};cur=cur['private']
        for value in [nested,{'private':'x'*20_000_000}]:
            r=self.run_adapter(state=value);self.assertNotIn('private',json.dumps(r));self.assertIn(r['status'],['FAIL','CAPACITY_BLOCKED'])
        for seconds in [True,float('inf'),10**10000,-1]:
            self.assertEqual(self.run_adapter(budget_seconds=seconds)['status'],'FAIL')
        self.assertEqual(self.run_adapter(budget_seconds=1e-12)['status'],'BUDGET_BLOCKED')

    def test_cutoff_horizon_night_and_duplicate_units_checked_before_legacy(self):
        for field,value in [('window_start_jst',context()['cutoff_time']),('window_start_jst','2026-10-12T07:00:00+09:00'),('operational_night','2026-10-12')]:
            _,i=legacy_fixture();i['universe_rows'][0][field]=value
            self.assertEqual(self.run_adapter(inputs=i)['status'],'FAIL')
        _,i=legacy_fixture();i['universe_rows']*=2
        self.assertEqual(self.run_adapter(inputs=i)['status'],'FAIL')

    def test_native_output_hashes_detachment_and_registry_not_mutable(self):
        s,i=legacy_fixture();old=copy.deepcopy((s,i));r=self.run_adapter(state=s,inputs=i)
        self.assertEqual((s,i),old)
        self.assertEqual(r['execution_sha256'],digest({k:v for k,v in r.items() if k!='execution_sha256'}))
        port=r['outputs']['spatial_rows'];self.assertEqual(port['payload_sha256'],digest(port['payload']))
        d=self.api.describe_adapters();d[0]['adapter_id']='evil';self.assertNotIn('evil',[x['adapter_id'] for x in self.api.describe_adapters()])

    def test_candidate_selector_ties_cell_centres_midpoint_and_individual_tokens(self):
        r=self.run_adapter('time_target_candidates_v1',{},dict(unit_predictions=unit_rows()),target_config())
        targets=r['outputs']['candidate_time_targets']['payload']
        self.assertEqual([x['source_unit_id'] for x in targets],['a','z'])
        self.assertEqual(targets[0]['utm_x_m'],500150.)
        self.assertEqual(targets[0]['time'],'2026-10-11T20:05:00+09:00')
        self.assertEqual((targets[0]['radius_m'],targets[0]['tolerance_seconds']),(100,600))
        self.assertEqual(targets[0]['point_provenance'],'DECLARED_CELL_CENTRE_NOT_MEASURED_ROAD_POINT')
        self.assertNotIn('formal_time_targets',r['produced_outputs'])

    def test_selector_requires_every_policy_and_distinguishes_executed_empty(self):
        conf=target_config();conf.pop('minimum_score')
        self.assertEqual(self.run_adapter('time_target_candidates_v1',{},dict(unit_predictions=unit_rows()),conf)['status'],'FAIL')
        conf=target_config();conf['minimum_score']=.9
        r=self.run_adapter('time_target_candidates_v1',{},dict(unit_predictions=unit_rows()),conf)
        self.assertEqual(r['status'],'EXECUTED');self.assertEqual(r['outputs']['candidate_time_targets']['payload'],[])
        self.assertEqual(r['outputs']['candidate_time_targets']['empty_reason'],'NO_UNITS_MEET_DECLARED_POLICY')

    def test_selector_declared_suppression_and_bad_probability_rejected(self):
        conf=target_config();conf['overlap_policy']='SUPPRESS_200M_1200S'
        self.assertEqual(len(self.run_adapter('time_target_candidates_v1',{},dict(unit_predictions=unit_rows()),conf)['outputs']['candidate_time_targets']['payload']),1)
        rows=unit_rows();rows[0]['probability']=1.1
        self.assertEqual(self.run_adapter('time_target_candidates_v1',{},dict(unit_predictions=rows),conf)['status'],'FAIL')

    def test_legacy_without_windows_stays_spatial_only(self):
        _,inputs=legacy_fixture();del inputs['universe_rows'][0]['window_start_jst']
        r=self.run_adapter(inputs=inputs)
        self.assertEqual(r['status'],'EXECUTED');self.assertEqual(r['produced_outputs'],['spatial_rows'])

    def test_same_physical_unit_cannot_be_duplicated_under_new_identity(self):
        _,inputs=legacy_fixture();other=copy.deepcopy(inputs['universe_rows'][0]);other['row_id']='another'
        inputs['universe_rows'].append(other);self.assertEqual(self.run_adapter(inputs=inputs)['status'],'FAIL')
        rows=unit_rows();rows[1]['cell_x']=rows[0]['cell_x']
        self.assertEqual(self.run_adapter('time_target_candidates_v1',{},dict(unit_predictions=rows),target_config())['status'],'FAIL')

    def test_selector_rejects_wrong_area_and_boolean_score(self):
        for mode in ('area','boolean'):
            rows=unit_rows()
            if mode=='area':rows[0]['area_id_1km']='utm52n_1km_0_0'
            else:rows[0].update(probability=1.,spatial_score=True)
            self.assertEqual(self.run_adapter('time_target_candidates_v1',{},dict(unit_predictions=rows),target_config())['status'],'FAIL')

    def test_fixed_closure_contains_static_transitive_local_helpers(self):
        import ast
        seen=set();todo=['output_adapters','composite_inference','count_activity','detection_evaluation']
        while todo:
            module=todo.pop();path=ROOT/'src'/Path(*module.split('.')).with_suffix('.py')
            if module in seen or not path.exists():continue
            seen.add(module)
            for node in ast.walk(ast.parse(path.read_text(encoding='utf8'))):
                if isinstance(node,ast.Import):todo.extend(x.name for x in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module:
                    todo.append(node.module);todo.extend(node.module+'.'+x.name for x in node.names)
        closure=set(self.api.required_code_paths())
        self.assertFalse({'src/'+x.replace('.','/')+'.py' for x in seen}-closure)

    def test_no_runtime_source_or_network_reads_for_materialized_prediction(self):
        import model_evaluation
        with patch('builtins.open',side_effect=AssertionError('file I/O')),patch('socket.socket',side_effect=AssertionError('network I/O')):
            self.assertEqual(self.run_adapter()['status'],'EXECUTED')

    def test_native_capacity_exception_is_not_mislabeled_as_bad_data(self):
        from tests.test_count_feasibility import fixture
        from models import constant_poisson_diagnostic as native
        state=native.fit_constant_poisson(*fixture())['model']
        with patch.object(native,'MAX_ROWS',1):
            r=self.run_adapter('constant_poisson_scenario_v1',state,dict(active_search_seconds=300))
        self.assertEqual(r['status'],'CAPACITY_BLOCKED');self.assertEqual(r['produced_outputs'],[])

    def test_selector_requires_explicit_horizon_not_optional_default(self):
        inputs=dict(unit_predictions=unit_rows(),cutoff_time=context()['cutoff_time'],forecast_end=None)
        self.assertEqual(self.run_adapter('time_target_candidates_v1',{},inputs,target_config())['status'],'FAIL')

    def test_legacy_latest_label_availability_must_precede_evaluated_night(self):
        for latest_label in ('2026-10-11T07:00:00+09:00','2026-10-11T17:00:00+09:00'):
            state,inputs=legacy_fixture();state['training_cutoff']=latest_label
            state['model_id']=state['model_sha256']=digest({k:v for k,v in state.items() if k not in ('model_id','model_sha256')})
            self.assertEqual(self.run_adapter(state=state,inputs=inputs)['status'],'FAIL')

    def test_gamma_actual_numeric_count_and_proxy_are_separate_deterministic_outputs(self):
        state,inputs,config=gamma_fixture()
        a=self.run_adapter('gamma_poisson_planned_count_v1',state,inputs,config)
        b=self.run_adapter('gamma_poisson_planned_count_v1',state,inputs,config)
        self.assertEqual(a['status'],'EXECUTED');self.assertEqual(a,b)
        self.assertAlmostEqual(a['outputs']['planned_capture_count']['payload']['mean'],4/7,delta=1e-14)
        self.assertEqual([q['count'] for q in a['outputs']['planned_capture_count']['payload']['quantiles']],[0,0,2])
        self.assertAlmostEqual(a['outputs']['capture_activity_proxy']['payload']['mean'],16/7,delta=1e-14)
        self.assertEqual(a['omitted_native_operational_fields'],['runtime_elapsed_seconds'])
        self.assertNotIn('runtime_elapsed_seconds',a['native_payload'])
        self.assertFalse(a['native_payload']['biological_tonight_activity_validated'])

    def test_gamma_missing_raw_plan_and_runtime_mismatch_never_stamp_success(self):
        state,inputs,config=gamma_fixture();inputs['plan']['raw_plan_utf8']=None
        r=self.run_adapter('gamma_poisson_planned_count_v1',state,inputs,config)
        self.assertEqual(r['status'],'DATA_BLOCKED');self.assertEqual(r['produced_outputs'],[])
        self.assertEqual(r['native_payload']['status'],'DATA_BLOCKED')
        import scipy
        state,inputs,config=gamma_fixture()
        with patch.object(scipy,'__version__','synthetic-wrong'):
            r=self.run_adapter('gamma_poisson_planned_count_v1',state,inputs,config)
        self.assertEqual(r['status'],'RUNTIME_BINDING_ERROR');self.assertEqual(r['outputs'],{})

    def test_gamma_partial_quantiles_keep_verified_mean_without_full_success(self):
        state,inputs,config=gamma_fixture(0)
        r=self.run_adapter('gamma_poisson_planned_count_v1',state,inputs,config)
        self.assertEqual(r['status'],'PARTIAL')
        port=r['outputs']['planned_capture_count']
        self.assertEqual(port['execution_status'],'PARTIAL');self.assertIsNone(port['payload']['quantiles'])
        self.assertAlmostEqual(port['payload']['mean'],4/7,delta=1e-14)
        self.assertEqual(port['missing_requirements'],['NUMERICAL_CAPACITY_EXCEEDED'])
        self.assertEqual(port['validity_status'],'NOT_VALIDATED')

    def test_gamma_real_plan_hash_and_readiness_are_rechecked(self):
        state,inputs,config=gamma_fixture();inputs['plan']['raw_plan_utf8']+=' '
        self.assertEqual(self.run_adapter('gamma_poisson_planned_count_v1',state,inputs,config)['status'],'FAIL')
        state,inputs,config=gamma_fixture();inputs['plan']['planned']=True
        self.assertEqual(self.run_adapter('gamma_poisson_planned_count_v1',state,inputs,config)['status'],'FAIL')

    def test_gamma_mean_absence_does_not_fabricate_produced_outputs(self):
        from tests.test_count_activity import count_fixture,plan_fixture,plan_inputs,protocol
        from count_activity import fit_gamma_poisson
        p=protocol();p['capacities']['max_exposure_hours']=.1;p['reference']['active_search_hours']=.05
        state=fit_gamma_poisson(*count_fixture(),protocol=p)['model']
        r=self.run_adapter('gamma_poisson_planned_count_v1',state,{'plan':plan_inputs(plan_fixture())},{'protocol':p})
        self.assertEqual(r['status'],'PARTIAL');self.assertNotIn('planned_capture_count',r['produced_outputs'])
        self.assertNotIn('planned_capture_count',r['outputs']);self.assertIn('capture_activity_proxy',r['produced_outputs'])

    def test_remaining_budget_never_passes_negative_time_to_native_kernel(self):
        with patch.object(self.api,'monotonic',side_effect=[0.,.9,1.1]):
            budget=self.api._Budget(1.)
            try:remaining=budget.remaining()
            except self.api._Stop as error:self.assertEqual(error.status,'BUDGET_BLOCKED')
            else:self.assertGreater(remaining,0.)

    def test_gamma_positive_exposure_underflow_never_becomes_zero_proxy_output(self):
        from tests.test_count_activity import protocol,count_fixture,plan_fixture,plan_inputs
        from count_activity import fit_gamma_poisson
        p=protocol();p['prior']=dict(alpha=1e300,beta_active_search_hours=1e300)
        p['capacities'].update(max_shape=1e301,max_rate_hours=1e301)
        p['reference']['active_search_hours']=1e-300
        state=fit_gamma_poisson(*count_fixture(),protocol=p)['model']
        r=self.run_adapter('gamma_poisson_planned_count_v1',state,{'plan':plan_inputs(plan_fixture())},{'protocol':p})
        self.assertEqual(r['status'],'PARTIAL')
        self.assertNotIn('capture_activity_proxy',r['produced_outputs'])
        self.assertIsNone(r['native_payload']['predictions']['capture_activity_proxy']['mean'])
        self.assertAlmostEqual(r['outputs']['planned_capture_count']['payload']['mean'],.25,delta=1e-14)


    def test_eight_fixed_adapters_and_closed_native_unit_detection_ports(self):
        contracts={c['adapter_id']:c for c in self.api.describe_adapters()}
        self.assertEqual(len(contracts),8)
        for name,slot,port in [('gamma_poisson_planned_units_v1','plan','planned_count_units'),
                               ('independent_opportunity_detection_v1','bundle','detection_opportunity_diagnostic')]:
            self.assertIn(name,contracts)
            self.assertEqual(contracts[name]['adapter_version'],'1')
            self.assertEqual(contracts[name]['input_schema'],dict(fields=[slot],allowed_dependency_slots=[]))
            self.assertEqual(set(contracts[name]['output_schema']),{port})

    def test_gamma_units_preserve_complete_native_envelope_seal_and_original_plan(self):
        from count_activity import predict_gamma_poisson_units
        state,inputs,config=gamma_fixture();before=copy.deepcopy((state,inputs,config))
        expected=predict_gamma_poisson_units(state,inputs['plan'],protocol=config['protocol'])
        expected.pop('runtime_elapsed_seconds');expected['aggregate_prediction'].pop('runtime_elapsed_seconds')
        r=self.run_adapter('gamma_poisson_planned_units_v1',state,inputs,config)
        self.assertEqual(r['status'],'EXECUTED',r)
        self.assertEqual(r['native_payload'],expected)
        self.assertEqual(r['outputs']['planned_count_units']['payload'],expected)
        self.assertEqual(r['omitted_native_operational_fields'],['runtime_elapsed_seconds','aggregate_prediction.runtime_elapsed_seconds'])
        self.assertEqual(expected['unit_prediction_sha256'],digest({k:v for k,v in expected.items() if k!='unit_prediction_sha256'}))
        self.assertEqual(r,self.run_adapter('gamma_poisson_planned_units_v1',state,inputs,config))
        self.assertEqual((state,inputs,config),before)
        self.assertFalse(expected['owner_subset_intent_authenticated'])
        self.assertFalse(r['production_authorized'])

    def test_gamma_units_missing_plan_and_runtime_have_no_output(self):
        from count_activity import _RuntimeBindingError
        for missing in (True,False):
            state,inputs,config=gamma_fixture()
            if missing:inputs['plan']['raw_plan_utf8']=None
            with patch('count_activity._runtime',side_effect=_RuntimeBindingError('RUNTIME_BINDING_ERROR')) if not missing else nullcontext():
                r=self.run_adapter('gamma_poisson_planned_units_v1',state,inputs,config)
            self.assertEqual(r['status'],'DATA_BLOCKED' if missing else 'RUNTIME_BINDING_ERROR',r)
            self.assertEqual(r['outputs'],{});self.assertEqual(r['produced_outputs'],[])
            self.assertIsNone(r['native_payload']['unit_predictions'])

    def test_gamma_units_partial_quantiles_are_not_complete_port(self):
        state,inputs,config=gamma_fixture(0)
        r=self.run_adapter('gamma_poisson_planned_units_v1',state,inputs,config)
        self.assertEqual(r['status'],'PARTIAL',r)
        port=r['outputs']['planned_count_units'];self.assertEqual(port['execution_status'],'PARTIAL')
        self.assertIsNone(port['payload']['aggregate_prediction']['predictions']['conditional_capture_count']['quantiles'])
        self.assertTrue(port['missing_requirements'])

    def test_gamma_units_unavailable_moments_do_not_become_produced_zero(self):
        from tests.test_count_activity import protocol,count_fixture,plan_fixture,plan_inputs
        from count_activity import fit_gamma_poisson
        p=protocol();p['capacities']['max_exposure_hours']=1e-9;p['reference']['active_search_hours']=1e-10
        state=fit_gamma_poisson(*count_fixture(),protocol=p)['model']
        plan=plan_fixture();plan.domain['cells']=[[4000,30000]];plan.plan['domain_sha256']=digest(plan.domain)
        plan.plan['allocations']=plan.plan['allocations'][:1]
        plan.plan['allocations'][0].update(start=plan.domain['horizon']['start'],end=plan.domain['horizon']['end'],planned_active_search_seconds=1200)
        plan.publish()
        r=self.run_adapter('gamma_poisson_planned_units_v1',state,{'plan':plan_inputs(plan)},{'protocol':p})
        self.assertEqual(r['status'],'NUMERICAL_CAPACITY_EXCEEDED',r)
        self.assertEqual(r['produced_outputs'],[])
        self.assertTrue(all(row['mean'] is None for row in r['native_payload']['unit_predictions']))

    def test_detection_preserves_actual_complete_native_math_and_receipt(self):
        from tests.test_detection_evaluation import fixture
        from detection_evaluation import evaluate_detection_opportunities
        bundle,protocol=fixture();expected=evaluate_detection_opportunities(bundle,protocol=protocol)
        r=self.run_adapter('independent_opportunity_detection_v1',{},dict(bundle=bundle),dict(protocol=protocol))
        self.assertEqual(r['status'],'EXECUTED',r)
        self.assertEqual(r['native_payload'],expected)
        self.assertEqual(r['outputs']['detection_opportunity_diagnostic']['payload'],expected)
        self.assertEqual(r['omitted_native_operational_fields'],[])
        self.assertEqual(r,self.run_adapter('independent_opportunity_detection_v1',{},dict(bundle=bundle),dict(protocol=protocol)))
        self.assertEqual(expected['receipt_sha256'],digest({k:v for k,v in expected.items() if k!='receipt_sha256'}))
        self.assertFalse(expected['biological_tonight_activity_validated'])

    def test_detection_zero_n_and_missing_bundle_never_produce_prior_or_empirical_output(self):
        from tests.test_detection_evaluation import fixture,publish
        for absent in (True,False):
            bundle,p=fixture()
            for row in bundle['opportunities']:row.update(detected=None,detection_time=None)
            publish(bundle,p)
            r=self.run_adapter('independent_opportunity_detection_v1',{},dict(bundle=None if absent else bundle),dict(protocol=p))
            self.assertEqual(r['status'],'DATA_BLOCKED',r)
            self.assertEqual(r['produced_outputs'],[]);self.assertEqual(r['outputs'],{})
            self.assertIsNone(r['native_payload']['known_subset_sensitivity'])

    def test_detection_known_subset_and_numerical_runtime_unknown_remain_partial(self):
        from tests.test_detection_evaluation import fixture,publish
        from detection_evaluation import _Runtime
        for runtime in (False,True):
            bundle,p=fixture()
            if not runtime:bundle['opportunities'][1].update(detected=None,detection_time=None);publish(bundle,p)
            with patch('detection_evaluation._runtime',side_effect=_Runtime('RUNTIME_BINDING_ERROR')) if runtime else nullcontext():
                r=self.run_adapter('independent_opportunity_detection_v1',{},dict(bundle=bundle),dict(protocol=p))
            self.assertEqual(r['status'],'PARTIAL',r)
            self.assertEqual(r['outputs']['detection_opportunity_diagnostic']['execution_status'],'PARTIAL')
            self.assertTrue(r['missing_requirements'])
            if runtime:self.assertIsNone(r['native_payload']['posterior_quantiles'])
            else:self.assertIsNone(r['native_payload']['observed_sensitivity'])

    def test_detection_native_capacity_and_invalid_source_do_not_produce_payload_port(self):
        from tests.test_detection_evaluation import fixture
        for mode in ('capacity','source'):
            bundle,p=fixture()
            if mode=='capacity':p['capacities']['max_opportunities']=1
            else:bundle['sources'][0]['ref']['sha256']='0'*64
            r=self.run_adapter('independent_opportunity_detection_v1',{},dict(bundle=bundle),dict(protocol=p))
            self.assertEqual(r['status'],'RUNTIME_BLOCKED' if mode=='capacity' else 'FAIL',r)
            self.assertEqual(r['outputs'],{});self.assertEqual(r['produced_outputs'],[])
            self.assertIsNotNone(r['native_payload'])

    def test_new_adapters_reject_state_config_version_and_custom_callbacks(self):
        from tests.test_detection_evaluation import fixture
        bundle,p=fixture();state,inputs,config=gamma_fixture()
        rows=[('independent_opportunity_detection_v1',{},dict(bundle=bundle),dict(protocol=p)),
              ('gamma_poisson_planned_units_v1',state,inputs,config)]
        calls=[]
        class Meta(type):
            def __eq__(self,other):calls.append('eq');return False
            def __hash__(self):calls.append('hash');return 1
        class Evil(metaclass=Meta):pass
        for name,state,inputs,config in rows:
            self.assertEqual(self.api.execute_adapter(name,state,inputs,config=config,adapter_version='2')['status'],'FAIL')
            self.assertEqual(self.api.execute_adapter(name,state,dict(inputs,callback=Evil()),config=config,adapter_version='1')['status'],'FAIL')
            self.assertEqual(self.run_adapter(name,state,inputs,dict(config,override={} ))['status'],'FAIL')
        self.assertEqual(self.run_adapter(rows[0][0],{'model':'injected'},rows[0][2],rows[0][3])['status'],'FAIL')
        self.assertEqual(calls,[])

    def test_new_native_kernels_share_remaining_deadline(self):
        from tests.test_detection_evaluation import fixture
        from detection_evaluation import evaluate_detection_opportunities
        bundle,p=fixture();clock=[0.];seen=[]
        def native(*args,**kwargs):
            seen.append(kwargs['budget_seconds']);result=evaluate_detection_opportunities(*args,**kwargs);clock[0]=5.;return result
        with patch.object(self.api,'monotonic',side_effect=lambda:clock[0]),patch('detection_evaluation.evaluate_detection_opportunities',side_effect=native):
            r=self.run_adapter('independent_opportunity_detection_v1',{},dict(bundle=bundle),dict(protocol=p),budget_seconds=1.)
        self.assertEqual(r['status'],'BUDGET_BLOCKED');self.assertEqual(r['outputs'],{})
        self.assertEqual(seen,[1.])

    def test_detection_local_source_closure_cannot_be_omitted(self):
        self.assertIn('src/detection_evaluation.py',self.api.required_code_paths())


    def test_gamma_units_partial_real_zero_does_not_fill_missing_positive_moments(self):
        from tests.test_count_activity import protocol,count_fixture,plan_fixture,plan_inputs
        from count_activity import fit_gamma_poisson
        p=protocol();p['capacities']['max_exposure_hours']=1e-9;p['reference']['active_search_hours']=1e-10
        state=fit_gamma_poisson(*count_fixture(),protocol=p)['model']
        r=self.run_adapter('gamma_poisson_planned_units_v1',state,{'plan':plan_inputs(plan_fixture())},{'protocol':p})
        self.assertEqual(r['status'],'PARTIAL',r)
        rows=r['outputs']['planned_count_units']['payload']['unit_predictions']
        self.assertTrue(any(row['exposure_hours']==0 and row['mean']==0 for row in rows))
        self.assertTrue(any(row['exposure_hours']>0 and row['mean'] is None for row in rows))
        self.assertEqual(r['outputs']['planned_count_units']['execution_status'],'PARTIAL')


if __name__=='__main__':unittest.main()
