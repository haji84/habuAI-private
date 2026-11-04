"""Synthetic immutable composite graph and complete prediction receipts."""
import ast
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from test_output_adapters import digest,legacy_fixture,context,target_config,gamma_fixture


def seal(model):
    model['model_id']=model['model_sha256']=digest({k:v for k,v in model.items() if k not in ('model_id','model_sha256')})
    return model


def fixture():
    from output_adapters import adapter_contract,required_code_paths
    state,inputs=legacy_fixture();config={};a=adapter_contract('legacy_spatial_v1')
    model=dict(schema_version='2.0',kind='registered_composite',recipe_id='synthetic-spatial',
        protocol_sha256='a'*64,policy_sha256='b'*64,training_cutoff=state['training_cutoff'],
        code_manifest={p:'c'*64 for p in required_code_paths()},
        components=[dict(component_id='spatial',adapter_id=a['adapter_id'],adapter_version='1',role='spatial',
          state_sha256=digest(state),config_sha256=digest(config),input_schema_sha256=a['input_schema_sha256'],
          output_schema_sha256=a['output_schema_sha256'],dependencies={})],
        output_bindings={'spatial_rows':dict(component_id='spatial',output='spatial_rows')},mandatory_capabilities=['spatial_rows'])
    artifacts={digest(state):state,digest(config):config};ready='2026-10-10T13:00:00+09:00'
    bundle=dict(schema_version='habu-composite-inference-input-v1',**context(),artifacts=artifacts,
        artifact_available_at={key:ready for key in artifacts},inputs={'spatial':inputs},input_available_at={'spatial':ready})
    return seal(model),bundle


def gamma_composite(max_count=None):
    from output_adapters import adapter_contract
    m,b=fixture();state,inputs,config=gamma_fixture(max_count);a=adapter_contract('gamma_poisson_planned_count_v1')
    assert a is not None, 'fixed Gamma-Poisson adapter missing'
    component=m['components'][0];component.update(adapter_id=a['adapter_id'],state_sha256=digest(state),
        config_sha256=digest(config),input_schema_sha256=a['input_schema_sha256'],output_schema_sha256=a['output_schema_sha256'])
    m['training_cutoff']=state['fit_cutoff'];m['output_bindings']={'planned_capture_count':{'component_id':'spatial','output':'planned_capture_count'}};m['mandatory_capabilities']=['planned_capture_count']
    domain=inputs['plan']['domain'];b.update(operational_night=domain['operational_night'],cutoff_time=domain['cutoff_time'],forecast_end=domain['horizon']['end'])
    b['artifacts']={digest(state):state,digest(config):config};b['artifact_available_at']={key:'2026-10-26T18:45:00+09:00' for key in b['artifacts']}
    b['inputs']={'spatial':inputs};b['input_available_at']={'spatial':'2026-10-26T18:45:00+09:00'}
    return seal(m),b


class CompositeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('composite_inference'),'pure composite executor missing')
        self.api=importlib.import_module('composite_inference')

    def test_actual_numeric_execution_and_complete_deterministic_receipts(self):
        m,b=fixture();old=copy.deepcopy((m,b));a=self.api.predict_composite(m,b);z=self.api.predict_composite(m,b)
        self.assertEqual(a,z);self.assertEqual((m,b),old)
        self.assertEqual(a['status'],'EXECUTED');self.assertEqual(a['outputs']['spatial_rows']['payload'][0]['spatial_score'],.25)
        self.assertEqual(a['produced_outputs'],['spatial_rows']);self.assertFalse(a['production_authorized'])
        self.assertEqual(a['code_identity'],'SUPPLIED_CLOSURE_NOT_ATTESTED')
        self.assertEqual(a['prediction_sha256'],digest({k:v for k,v in a.items() if k!='prediction_sha256'}))
        self.assertEqual(a['component_receipts'][0]['state_sha256'],m['components'][0]['state_sha256'])

    def test_state_config_and_model_identity_tampering_fail(self):
        for mode in ['state','model','config']:
            m,b=fixture()
            if mode=='state':b['artifacts'][m['components'][0]['state_sha256']]['parameters']['default']=.9
            elif mode=='model':m['recipe_id']='swapped'
            else:b['artifacts'][m['components'][0]['config_sha256']]['private']='injected'
            self.assertEqual(self.api.predict_composite(m,b)['status'],'FAIL')

    def test_missing_artifact_or_input_blocks_without_placeholder(self):
        for field in ['artifacts','inputs']:
            m,b=fixture();key=m['components'][0]['state_sha256'] if field=='artifacts' else 'spatial'
            del b[field][key];del b['artifact_available_at' if field=='artifacts' else 'input_available_at'][key]
            r=self.api.predict_composite(m,b)
            self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['produced_outputs'],[])
            self.assertEqual(r['outputs']['spatial_rows']['execution_status'],'DATA_BLOCKED')

    def test_unknown_adapter_and_unsupported_mandatory_capability_block(self):
        m,b=fixture();m['components'][0]['adapter_id']='unreviewed.import';seal(m)
        self.assertEqual(self.api.predict_composite(m,b)['status'],'BLOCKED')
        m,b=fixture();m['mandatory_capabilities'].append('biological_tonight_activity');seal(m)
        r=self.api.predict_composite(m,b)
        self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['outputs']['biological_tonight_activity']['execution_status'],'IMPLEMENTATION_BLOCKED')
        self.assertIn('spatial_rows',r['produced_outputs'])

    def test_hash_schema_version_closure_and_duplicate_writers_rejected(self):
        for mutate in [lambda m:m['components'][0].update(output_schema_sha256='0'*64),
                       lambda m:m['components'][0].update(adapter_version='2'),
                       lambda m:m['code_manifest'].pop('src/output_adapters.py'),
                       lambda m:m['components'].append(copy.deepcopy(m['components'][0])),
                       lambda m:m['output_bindings'].update(alias=copy.deepcopy(m['output_bindings']['spatial_rows']))]:
            m,b=fixture();mutate(m);seal(m);self.assertEqual(self.api.predict_composite(m,b)['status'],'FAIL')

    def test_dependency_cycles_missing_nodes_and_wrong_ports_rejected(self):
        for dep in [dict(component_id='spatial',output='spatial_rows'),dict(component_id='missing',output='spatial_rows'),dict(component_id='spatial',output='formal_targets')]:
            m,b=fixture();m['components'][0]['dependencies']={'universe_rows':dep};seal(m)
            self.assertEqual(self.api.predict_composite(m,b)['status'],'FAIL')

    def test_aware_readiness_strict_cutoff_horizon_and_training_cutoff(self):
        for mode in ['artifact','input','naive','training','night']:
            m,b=fixture()
            if mode=='artifact':b['artifact_available_at'][m['components'][0]['state_sha256']]=b['cutoff_time']
            if mode=='input':b['input_available_at']['spatial']=b['cutoff_time']
            if mode=='naive':b['cutoff_time']='2026-10-11T18:00:00'
            if mode=='training':m['training_cutoff']='2026-10-09T12:00:00+09:00';seal(m)
            if mode=='night':b['operational_night']='2026-10-12'
            self.assertEqual(self.api.predict_composite(m,b)['status'],'FAIL')

    def test_no_external_output_or_callable_accepted_and_private_error_sanitized(self):
        calls=[]
        def malicious():calls.append(1)
        for key,value in [('output',{'secret':'SYNTHETIC_PRIVATE_SENTINEL'}),('callback',malicious)]:
            m,b=fixture();b[key]=value;r=self.api.predict_composite(m,b)
            self.assertEqual(r['status'],'FAIL');self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL',json.dumps(r))
        self.assertEqual(calls,[])

    def test_single_shared_budget_and_false_boolean_not_numeric_budget(self):
        m,b=fixture();self.assertEqual(self.api.predict_composite(m,b,budget_seconds=True)['status'],'FAIL')
        self.assertEqual(self.api.predict_composite(m,b,budget_seconds=1e-12)['status'],'BUDGET_BLOCKED')

    def test_completed_dependency_executes_candidate_selector_without_formal_claim(self):
        from tests.test_hba1_feature_candidate import fixture as hfixture,recipe
        from models import hba1_feature_candidate as hba
        from output_adapters import adapter_contract
        m,b=fixture();_,folds=hfixture();spec=recipe();rows=folds[0]['forecast_rows']
        state=hba.fit_hba1(folds[0]['training_selection'],recipe=spec,expected_recipe_sha256=digest(spec))['model'];cfg=target_config()
        source=m['components'][0];a=adapter_contract('hba1_unit_v1');source.update(adapter_id=a['adapter_id'],input_schema_sha256=a['input_schema_sha256'],output_schema_sha256=a['output_schema_sha256'],state_sha256=digest(state))
        a=adapter_contract('time_target_candidates_v1');target=dict(component_id='target',adapter_id=a['adapter_id'],adapter_version='1',role='candidate_selector',state_sha256=digest({}),config_sha256=digest(cfg),input_schema_sha256=a['input_schema_sha256'],output_schema_sha256=a['output_schema_sha256'],dependencies={'unit_predictions':dict(component_id='spatial',output='unit_predictions')})
        m['components']=[target,source];m['training_cutoff']=state['fit_cutoff'];m['output_bindings']={'candidate_time_targets':dict(component_id='target',output='candidate_time_targets')};m['mandatory_capabilities']=['candidate_time_targets']
        b['artifacts']={digest(state):state,digest({}):{},digest(cfg):cfg};b['artifact_available_at']={k:'2026-10-10T13:00:00+09:00' for k in b['artifacts']};b['inputs']={'spatial':dict(forecast_rows=rows,joined_universe_sha256=digest(rows),cutoff_time=b['cutoff_time']),'target':dict(cutoff_time=b['cutoff_time'],forecast_end=b['forecast_end'])};b['input_available_at']={k:'2026-10-10T13:00:00+09:00' for k in b['inputs']}
        r=self.api.predict_composite(seal(m),b);self.assertEqual(r['status'],'EXECUTED')
        self.assertEqual([x['component_id'] for x in r['component_receipts']],['spatial','target'])
        self.assertNotIn('formal_time_targets',r['produced_outputs']);self.assertFalse(r['official_issuance_authorized'])
        self.assertEqual(r['component_receipts'][1]['dependencies']['unit_predictions']['component_id'],'spatial')

    def test_missing_child_does_not_hide_executed_unrelated_output(self):
        m,b=fixture();child=copy.deepcopy(m['components'][0]);child.update(component_id='count',adapter_id='not_implemented_future_model')
        m['components'].append(child);m['output_bindings']['planned_capture_count']={'component_id':'count','output':'planned_capture_count'};m['mandatory_capabilities'].append('planned_capture_count');seal(m)
        r=self.api.predict_composite(m,b);self.assertEqual(r['status'],'BLOCKED')
        self.assertEqual(r['outputs']['planned_capture_count']['execution_status'],'IMPLEMENTATION_BLOCKED')
        self.assertEqual(r['outputs']['spatial_rows']['payload'][0]['spatial_score'],.25)

    def test_input_and_output_tampering_changes_full_result_binding(self):
        m,b=fixture();a=self.api.predict_composite(m,b);b['inputs']['spatial']['universe_rows'][0]['utm_x_m']+=100
        z=self.api.predict_composite(m,b);self.assertNotEqual(a['input_bundle_sha256'],z['input_bundle_sha256'])
        self.assertNotEqual(a['prediction_sha256'],z['prediction_sha256'])
        self.assertNotEqual(a['outputs']['spatial_rows']['payload_sha256'],z['outputs']['spatial_rows']['payload_sha256'])

    def test_shared_deadline_not_restarted_after_actual_first_component(self):
        import output_adapters
        m,b=fixture();clock=[0.];native=output_adapters._execute
        def execute(*args,**kwargs):
            result=native(*args,**kwargs);clock[0]=5.;return result
        with patch.object(output_adapters,'monotonic',side_effect=lambda:clock[0]),patch.object(output_adapters,'_execute',side_effect=execute):
            r=self.api.predict_composite(m,b,budget_seconds=1.)
        self.assertEqual(r['status'],'BUDGET_BLOCKED');self.assertEqual(r['outputs'],{})

    def test_unconsumed_outcome_artifact_and_wrong_source_readiness_fail(self):
        m,b=fixture();extra={'future_outcome':'SYNTHETIC_PRIVATE_SENTINEL'};h=digest(extra)
        b['artifacts'][h]=extra;b['artifact_available_at'][h]='2026-10-10T13:00:00+09:00'
        r=self.api.predict_composite(m,b);self.assertEqual(r['status'],'FAIL');self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL',json.dumps(r))
        m,b=fixture();b['artifact_available_at'][m['components'][0]['state_sha256']]='2026-10-09T00:00:00+09:00'
        self.assertEqual(self.api.predict_composite(m,b)['status'],'FAIL')

    def test_explicit_composite_context_cannot_use_optional_helper_defaults(self):
        for field in ('operational_night','forecast_end'):
            m,b=fixture();b[field]=None
            self.assertEqual(self.api.predict_composite(m,b)['status'],'FAIL')

    def test_resealed_legacy_same_night_labels_cannot_enter_composite(self):
        m,b=fixture();component=m['components'][0];oldsha=component['state_sha256'];state=b['artifacts'].pop(oldsha)
        del b['artifact_available_at'][oldsha];state['training_cutoff']='2026-10-11T17:00:00+09:00'
        state['model_id']=state['model_sha256']=digest({k:v for k,v in state.items() if k not in ('model_id','model_sha256')})
        component['state_sha256']=digest(state);b['artifacts'][digest(state)]=state;b['artifact_available_at'][digest(state)]='2026-10-11T17:30:00+09:00'
        m['training_cutoff']=state['training_cutoff'];seal(m)
        self.assertEqual(self.api.predict_composite(m,b)['status'],'FAIL')

    def test_gamma_composite_binds_actual_planned_payload_and_deterministic_receipts(self):
        m,b=gamma_composite();a=self.api.predict_composite(m,b);z=self.api.predict_composite(m,b)
        self.assertEqual(a,z);self.assertEqual(a['status'],'EXECUTED')
        self.assertAlmostEqual(a['outputs']['planned_capture_count']['payload']['mean'],4/7,delta=1e-14)
        self.assertEqual(a['policy_admission'],'NOT_ATTESTED')
        self.assertFalse(a['official_issuance_authorized'])

    def test_gamma_partial_mean_does_not_satisfy_mandatory_complete_count(self):
        m,b=gamma_composite(0);r=self.api.predict_composite(m,b)
        self.assertEqual(r['status'],'BLOCKED');self.assertIn('planned_capture_count',r['produced_outputs'])
        self.assertEqual(r['outputs']['planned_capture_count']['execution_status'],'PARTIAL')
        self.assertIn('planned_capture_count',r['missing_requirements'])
        self.assertIsNone(r['outputs']['planned_capture_count']['payload']['quantiles'])

    def test_gamma_plan_scope_must_equal_composite_scope(self):
        for key,value in [('cutoff_time','2026-10-26T19:01:00+09:00'),('forecast_end','2026-10-26T20:30:00+09:00')]:
            m,b=gamma_composite();b[key]=value
            self.assertEqual(self.api.predict_composite(m,b)['status'],'FAIL')

    def test_gamma_uncomputed_mean_is_not_produced_just_because_proxy_executes(self):
        from tests.test_count_activity import count_fixture
        from count_activity import fit_gamma_poisson
        m,b=gamma_composite();c=m['components'][0];config=b['artifacts'][c['config_sha256']]
        config['protocol']['capacities']['max_exposure_hours']=.1
        config['protocol']['reference']['active_search_hours']=.05
        state=fit_gamma_poisson(*count_fixture(),protocol=config['protocol'])['model']
        c.update(state_sha256=digest(state),config_sha256=digest(config))
        b['artifacts']={digest(state):state,digest(config):config}
        b['artifact_available_at']={key:'2026-10-26T18:45:00+09:00' for key in b['artifacts']}
        m['output_bindings']['capture_activity_proxy']={'component_id':'spatial','output':'capture_activity_proxy'}
        r=self.api.predict_composite(seal(m),b)
        self.assertEqual(r['status'],'BLOCKED')
        self.assertNotIn('planned_capture_count',r['produced_outputs'])
        self.assertIsNone(r['outputs']['planned_capture_count']['payload'])
        self.assertIn('capture_activity_proxy',r['produced_outputs'])

    def test_gamma_no_plan_blocks_actual_bound_output_and_keeps_native_reason(self):
        m,b=gamma_composite();b['inputs']['spatial']['plan']['raw_plan_utf8']=None
        r=self.api.predict_composite(m,b)
        self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['produced_outputs'],[])
        self.assertEqual(r['outputs']['planned_capture_count']['execution_status'],'DATA_BLOCKED')
        self.assertEqual(r['component_receipts'][0]['execution']['native_payload']['status'],'DATA_BLOCKED')


if __name__=='__main__':unittest.main()
