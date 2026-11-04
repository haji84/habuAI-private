"""Synthetic numeric execution; no real source, fit or issuance authority."""
import copy
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
        for name in ['os.system','unknown','gamma_poisson_planned_count_v1']:
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
        seen=set();todo=['output_adapters','composite_inference']
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


if __name__=='__main__':unittest.main()
