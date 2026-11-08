"""Synthetic normalized GPS declarations, never authenticated field evidence."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import route_planning as native
from tests.test_route_planning import fixture as route_fixture,n,way
from route_graph import build_route_graph


def source(body,ready):
    raw=json.dumps(body,ensure_ascii=False,indent=2)+'\n'
    return dict(raw_json_utf8=raw,sha256=hashlib.sha256(raw.encode()).hexdigest(),size_bytes=len(raw.encode()),
        readiness={k:ready for k in ('source_received_at','derived_at','materialized_at','audited_at')},
        availability_basis='DECLARED_SYNTHETIC_NORMALIZED_SOURCE')


def fixture(route_args=None):
    gi,d,gp,rp=route_fixture(**(route_args or {}))
    prediction=native.plan_route_candidates(gi,d,graph_policy=gp,policy=rp)
    original=dict(schema_version='habu-original-route-bundle-v1',graph_input=gi,decision_input=d,
        graph_policy=gp,route_policy=rp,route_prediction_sha256=prediction['route_prediction_sha256'])
    selected=prediction['routes'][0]
    selection=dict(schema_version='habu-declared-route-selection-v1',
        original_route_prediction_sha256=prediction['route_prediction_sha256'],selected_route_label=selected['label'],
        selected_route_sha256=selected['route_sha256'],selected_at='2026-10-26T19:59:00+09:00')
    graph=build_route_graph(gi,policy=gp)
    incoming=next(e['edge_id'] for e in graph['edges'] if e['from_node']=='osm:1' and e['to_node']=='osm:2')
    points=[dict(point_id='p1',sequence=0,observed_at='2026-10-26T20:00:00+09:00',latitude=28.0,longitude=129.00005,accuracy_m=3.),
        dict(point_id='p2',sequence=1,observed_at='2026-10-26T20:00:59+09:00',latitude=28.0,longitude=129.0004,accuracy_m=3.)]
    observation=dict(schema_version='habu-normalized-route-observations-v1',origin='NORMALIZED_GPS_MEASURED_DECLARATION',
        original_route_prediction_sha256=prediction['route_prediction_sha256'],selected_route_sha256=selected['route_sha256'],points=points,
        current_state=dict(kind='ARRIVED_VIA_EDGE',current_point_id='p2',previous_point_id='p1',current_node_id='osm:2',incoming_edge_id=incoming))
    execution=dict(schema_version='habu-route-execution-input-v2',update_as_of='2026-10-26T20:01:00+09:00',
        selection_source=source(selection,'2026-10-26T19:59:30+09:00'),observation_source=source(observation,'2026-10-26T20:01:00+09:00'))
    policy=dict(schema_version='habu-route-execution-policy-v2',phase='DEVELOPMENT',frozen_at='2026-10-26T19:30:00+09:00',
        purpose='CONDITIONAL_RESELECTION_OF_UNCHANGED_ORIGINAL_PLAN',budget_basis='ORIGINAL_WALLCLOCK_DEADLINE',
        association='DECLARED_EDGE_ENDPOINTS_ONLY',max_position_age_seconds=120.,max_observation_gap_seconds=120.,
        max_accuracy_m=10.,max_endpoint_distance_m=10.,proximity_distance_m=20.,
        capacities=dict(max_points=1000,max_distance_checks=100000,max_source_bytes=1000000,
            max_json_bytes=16000000,max_json_nodes=2000000,max_seconds=30.))
    return original,execution,policy


def edit(execution,key,fn):
    old=execution[key];body=json.loads(old['raw_json_utf8']);fn(body)
    execution[key]=source(body,old['readiness']['audited_at'])


class RouteExecutionTests(unittest.TestCase):
    def test_execution_clocks_reject_submicrosecond_and_fractional_offsets(self):
        cases=['point','selection','policy','asof']+['selection_source:'+k for k in ('source_received_at','derived_at','materialized_at','audited_at')]+['observation_source:'+k for k in ('source_received_at','derived_at','materialized_at','audited_at')]
        for target in cases:
            with self.subTest(target=target):
                self.original,self.execution,self.policy=fixture()
                if target=='point':edit(self.execution,'observation_source',lambda b:b['points'][-1].update(observed_at='2026-10-26T20:01:00.0000001+09:00'))
                elif target=='selection':edit(self.execution,'selection_source',lambda b:b.update(selected_at='2026-10-26T19:59:00.0000001+09:00'))
                elif target=='policy':self.policy['frozen_at']='2026-10-26T19:30:00.0000001+09:00'
                elif target=='asof':self.execution['update_as_of']='2026-10-26T20:01:00.0000001+09:00'
                else:
                    source_name,key=target.split(':');self.execution[source_name]['readiness'][key]=self.execution[source_name]['readiness'][key].replace('+09:00','.0000001+09:00')
                self.assertEqual(self.call()['execution_status'],'FAIL')
        self.original,self.execution,self.policy=fixture()
        self.execution['update_as_of']='2026-10-26T20:01:00+09:00:00.0000001'
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_supported_microsecond_clocks_preserve_exact_future_boundary(self):
        self.execution['update_as_of']='2026-10-26T20:01:00.000001+09:00'
        edit(self.execution,'observation_source',lambda b:b['points'][-1].update(observed_at='2026-10-26T20:01:00.000001+09:00'))
        self.execution['observation_source']['readiness']={k:self.execution['update_as_of'] for k in self.execution['observation_source']['readiness']}
        self.assertEqual(self.call()['execution_status'],'COMPUTED_RESEARCH_ONLY')
        self.execution['update_as_of']='2026-10-26T20:01:00+09:00'
        self.assertEqual(self.call()['execution_status'],'DATA_BLOCKED')

    def test_late_shared_deadline_discards_every_unsealed_derived_claim(self):
        for stage in ('prepare','original','remaining','proximity','seal'):
            with self.subTest(stage=stage):
                expired=False;calls=0
                target={'prepare':'_prepare_route_context','original':'_run_prepared_route',
                    'remaining':'_run_prepared_route','proximity':'_proximity','seal':'_seal'}[stage]
                module=self.module() if stage=='proximity' else native
                actual=getattr(module,target)
                def after(*args,**kwargs):
                    nonlocal expired,calls
                    value=actual(*args,**kwargs);calls+=1
                    if stage!='remaining' or calls==2:expired=True
                    return value
                with patch.object(module,target,side_effect=after),patch.object(native.time,'monotonic',side_effect=lambda:31. if expired else 0.):
                    r=self.call()
                self.assertEqual(r['execution_status'],'RUNTIME_BLOCKED',r)
                self.assertEqual(r,{**self.module()._empty(),'execution_status':'RUNTIME_BLOCKED','blockers':r['blockers']})

    def test_selection_and_its_complete_readiness_strictly_precede_points(self):
        for case in ('late_receipt','equal_receipt','equal_selection','policy_equal_selection'):
            with self.subTest(case=case):
                self.original,self.execution,self.policy=fixture()
                first=json.loads(self.execution['observation_source']['raw_json_utf8'])['points'][0]['observed_at']
                if case=='late_receipt':
                    self.execution['selection_source']['readiness']['audited_at']=self.execution['update_as_of']
                elif case=='equal_receipt':self.execution['selection_source']['readiness']['audited_at']=first
                elif case=='equal_selection':
                    edit(self.execution,'selection_source',lambda b:b.update(selected_at=first))
                    self.execution['selection_source']['readiness']={k:first for k in self.execution['selection_source']['readiness']}
                else:self.policy['frozen_at']=json.loads(self.execution['selection_source']['raw_json_utf8'])['selected_at']
                r=self.call();self.assertEqual(r['execution_status'],'FAIL',r)
                self.assertEqual(r,{**self.module()._empty(),'blockers':r['blockers']})

    def test_late_invalid_position_discards_precomputed_diagnostic_and_bindings(self):
        edit(self.execution,'observation_source',lambda b:b['current_state'].update(current_node_id='osm:1'))
        r=self.call()
        self.assertEqual(r,{**self.module()._empty(),'blockers':r['blockers']})

    def setUp(self):self.original,self.execution,self.policy=fixture()
    def module(self):
        self.assertTrue((ROOT/'src/route_execution.py').is_file(),'Remaining-state native executor missing')
        return importlib.import_module('route_execution')
    def call(self,diagnose=False,**kw):
        m=self.module();fn=m.diagnose_route_execution if diagnose else m.reroute_remaining_plan
        r=fn(self.original,self.execution,policy=self.policy,**kw)
        for key in ('production_authorized','official_issuance_authorized','navigation_authorized','fit_authorized','source_authorized'):
            self.assertIs(r[key],False)
        return r
    def test_arrived_state_keeps_original_return_and_one_preparation(self):
        with patch.object(native,'build_route_graph',wraps=native.build_route_graph) as graph,patch.object(native,'predict_gamma_poisson_units',wraps=native.predict_gamma_poisson_units) as count:
            r=self.call()
        self.assertEqual(graph.call_count,1);self.assertEqual(count.call_count,1)
        self.assertEqual(r['execution_status'],'COMPUTED_RESEARCH_ONLY',r)
        self.assertTrue(r['remaining_routes'])
        self.assertEqual(r['remaining_routes'][0]['arrival_node_id'],'osm:1')
        self.assertEqual(r['remaining_routes'][0]['depart_at'],'2026-10-26T11:01:00Z')
        self.assertEqual(r['remaining_state']['remaining_budget_seconds'],1740.)
        self.assertTrue(r['original_return_required'])
    def test_same_original_plan_model_sources_and_repeat_hash_preserved(self):
        before=copy.deepcopy([self.original,self.execution,self.policy]);a=self.call();b=self.call()
        a.pop('runtime_elapsed_seconds',None);b.pop('runtime_elapsed_seconds',None)
        self.assertEqual(a,b);self.assertEqual(before,[self.original,self.execution,self.policy])
        self.assertFalse(a['owner_plan_modified']);self.assertFalse(a['owner_subset_intent_authenticated'])
    def test_unknown_precision_blocks_reroute_but_diagnostic_not_zero(self):
        edit(self.execution,'observation_source',lambda b:b['points'][-1].update(accuracy_m=None))
        r=self.call();self.assertEqual(r['execution_status'],'DATA_BLOCKED');self.assertEqual(r['remaining_routes'],[])
        d=self.call(diagnose=True);self.assertEqual(d['proximity']['unresolved_points'],1)
        self.assertEqual(d['capture_outcome'],'NOT_ASSESSED');self.assertIsNone(d['verified_active_search_seconds'])
    def test_future_point_and_future_readiness_rejected(self):
        edit(self.execution,'observation_source',lambda b:b['points'][-1].update(observed_at='2026-10-26T20:02:00+09:00'))
        self.assertEqual(self.call()['execution_status'],'FAIL')
        self.original,self.execution,self.policy=fixture();self.execution['observation_source']['readiness']['audited_at']='2026-10-26T20:02:00+09:00'
        self.assertEqual(self.call()['execution_status'],'DATA_BLOCKED')
    def test_unchanged_original_hash_and_explicit_selection_required(self):
        self.original['route_prediction_sha256']='0'*64;self.assertEqual(self.call()['execution_status'],'FAIL')
        self.original,self.execution,self.policy=fixture()
        edit(self.execution,'selection_source',lambda b:b.update(selected_route_sha256='0'*64))
        self.assertEqual(self.call()['execution_status'],'FAIL')
    def test_incoming_edge_must_terminate_at_actual_associated_node(self):
        edit(self.execution,'observation_source',lambda b:b['current_state'].update(current_node_id='osm:1'))
        self.assertEqual(self.call()['execution_status'],'FAIL')
    def test_past_and_mixed_units_not_rewarded_as_future_full_units(self):
        self.execution['update_as_of']='2026-10-26T20:16:00+09:00'
        def later(b):
            b['points'][0]['observed_at']='2026-10-26T20:15:00+09:00';b['points'][1]['observed_at']='2026-10-26T20:15:59+09:00'
        edit(self.execution,'observation_source',later)
        self.execution['observation_source']['readiness']={k:self.execution['update_as_of'] for k in self.execution['observation_source']['readiness']}
        r=self.call();self.assertTrue(r['remaining_routes'],r)
        for candidate in r['remaining_routes']:self.assertNotIn('a',candidate['completed_allocation_ids'])
        self.assertEqual(r['remaining_state']['remaining_budget_seconds'],840.)
    def test_proximity_only_no_unselected_counterfactual_outcomes(self):
        r=self.call(diagnose=True);self.assertEqual(r['proximity']['observed_points'],2)
        self.assertEqual(r['proximity']['kind'],'POINT_TO_SELECTED_PLANNED_EDGE_DISTANCE_ONLY')
        self.assertEqual(r['whole_route_adherence'],'NOT_ESTABLISHED');self.assertEqual(r['route_benefit'],'NOT_VALIDATED')
        self.assertTrue(all(x['actual_outcome']=='NOT_OBSERVED' for x in r['unselected_route_outcomes']))
        self.assertEqual([x['label'] for x in r['unselected_route_outcomes']],['B','C'])
        self.assertTrue(all(x['route_sha256'] is None for x in r['unselected_route_outcomes']))
        self.assertEqual(r['graph_status'],'GRAPH_BUILT_RESEARCH_ONLY')
    def test_explicit_policy_and_strict_foreign_keys_no_callback(self):
        calls=[]
        class Bad(str):
            def __eq__(self,o):calls.append(1);raise AssertionError('callback')
            __hash__=str.__hash__
        self.execution[Bad('foreign')]=1
        self.assertEqual(self.call()['execution_status'],'FAIL');self.assertEqual(calls,[])
        self.original,self.execution,self.policy=fixture();self.policy['proximity_distance_m']=True
        self.assertEqual(self.call()['execution_status'],'FAIL')
    def test_huge_budget_and_source_hash_mismatch_fail_closed(self):
        self.assertEqual(self.call(budget_seconds=10**1000)['execution_status'],'FAIL')
        self.execution['observation_source']['raw_json_utf8']+=' '
        self.assertEqual(self.call()['execution_status'],'FAIL')
    def test_distance_work_cap_preserves_unknown_instead_of_fake_zero(self):
        self.policy['capacities']['max_distance_checks']=1
        r=self.call(diagnose=True);self.assertEqual(r['execution_status'],'RUNTIME_BLOCKED');self.assertIsNone(r['proximity'])

    def test_remaining_native_result_is_versioned_and_binds_original_and_entry(self):
        r=self.call();inner=r['remaining_native_result']
        self.assertEqual(inner['schema_version'],'habu-conditional-route-remaining-result-v2')
        self.assertEqual(inner['original_decision_input_sha256'],native.digest(self.original['decision_input']))
        self.assertEqual(inner['remaining_entry_state']['incoming_edge_id'],r['remaining_state']['incoming_edge_id'])
        expected=native.digest({k:v for k,v in r.items() if k not in ('execution_sha256','runtime_elapsed_seconds')})
        self.assertEqual(r['execution_sha256'],expected)
        self.assertEqual(inner['route_prediction_sha256'],native.digest({k:v for k,v in inner.items() if k!='route_prediction_sha256'}))

    def test_first_no_and_only_turn_history_survives_current_node_dwell(self):
        for restriction in ('no_right_turn','only_right_turn'):
            relation=dict(type='relation',id=20,version=1,tags={'type':'restriction','restriction':restriction},members=[
                dict(type='way',ref=10,role='from'),dict(type='node',ref=2,role='via'),dict(type='way',ref=11,role='to')])
            self.original,self.execution,self.policy=fixture(dict(elements=[n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2]),way(11,[2,3]),relation]))
            r=self.call();self.assertTrue(r['remaining_routes'],r)
            for route in r['remaining_routes']:
                if restriction.startswith('no_'):
                    self.assertNotIn('b',route['completed_allocation_ids'])
                    self.assertFalse(route['edge_ids'][0].startswith('way:11:'))
                else:self.assertTrue(route['edge_ids'][0].startswith('way:11:'))

    def test_unit_with_past_and_future_original_allocations_has_no_future_full_mean(self):
        allocations=[dict(allocation_id='a1',start='2026-10-26T20:01:00+09:00',end='2026-10-26T20:03:00+09:00',planned_active_search_seconds=120),
            dict(allocation_id='a2',start='2026-10-26T20:08:00+09:00',end='2026-10-26T20:10:00+09:00',planned_active_search_seconds=120)]
        self.original,self.execution,self.policy=fixture(dict(allocations=allocations,anchors=[('a1',2,'way:10:1'),('a2',2,'way:10:1')]))
        self.execution['update_as_of']='2026-10-26T20:04:00+09:00';self.policy['max_position_age_seconds']=300
        r=self.call();self.assertEqual(r['remaining_routes'],[],r);self.assertIsNone(r['expected_captures'])
        self.assertIn('TOUCHED_UNIT_INCOMPLETE_NO_PARTIAL_CREDIT',r['remaining_native_result']['feasibility_reasons'])

    def test_source_readiness_dag_policy_freeze_and_unknown_history(self):
        for mutate in (lambda e,p:e['observation_source']['readiness'].update(derived_at='2026-10-26T19:00:00+09:00'),
                       lambda e,p:p.update(frozen_at='2026-10-26T20:01:00+09:00'),
                       lambda e,p:edit(e,'observation_source',lambda b:b.update(current_state=None))):
            self.original,self.execution,self.policy=fixture();mutate(self.execution,self.policy)
            r=self.call();self.assertIn(r['execution_status'],('FAIL','DATA_BLOCKED'));self.assertEqual(r['remaining_routes'],[])

    def test_shared_solver_work_is_not_reset_between_original_and_remaining(self):
        d=self.call(diagnose=True);r=self.call()
        self.assertGreater(r['work']['shortest_path_calls'],d['work']['shortest_path_calls'])
        self.assertLessEqual(r['work']['shortest_path_calls'],self.original['route_policy']['capacities']['max_shortest_path_calls'])

    def test_raw_duplicates_nonfinite_depth_and_custom_metaclass_cannot_call_native(self):
        for raw in ('{"x":1,"x":2}','{"x":NaN}', '['*40+'0'+']'*40):
            self.original,self.execution,self.policy=fixture();s=self.execution['observation_source'];s.update(raw_json_utf8=raw,sha256=hashlib.sha256(raw.encode()).hexdigest(),size_bytes=len(raw))
            with patch.object(native,'build_route_graph',side_effect=AssertionError('must reject before native')):
                self.assertIn(self.call()['execution_status'],('FAIL','RUNTIME_BLOCKED'))
        calls=[]
        class Meta(type):
            def __eq__(self,other):calls.append(1);raise AssertionError('metaclass')
        class Bad(metaclass=Meta):pass
        self.original,self.execution,self.policy=fixture();self.execution['observation_source']=Bad()
        self.assertEqual(self.call()['execution_status'],'FAIL');self.assertEqual(calls,[])

    def test_no_io_or_fake_time_budget(self):
        import socket,subprocess
        with patch('builtins.open',side_effect=AssertionError('read')),patch.object(socket.socket,'connect',side_effect=AssertionError('network')),patch.object(subprocess,'Popen',side_effect=AssertionError('execute')):
            self.assertEqual(self.call()['execution_status'],'COMPUTED_RESEARCH_ONLY')
        self.assertEqual(self.call(budget_seconds=1e-12)['execution_status'],'RUNTIME_BLOCKED')

    def test_unstarted_requires_observed_support_from_original_departure(self):
        def stationary(b):
            b['current_state']=dict(kind='UNSTARTED_STATIONARY',current_point_id='p2',current_node_id='osm:1')
            for p in b['points']:p['longitude']=129.00005
        edit(self.execution,'observation_source',stationary)
        self.assertTrue(self.call()['remaining_routes'])
        edit(self.execution,'observation_source',lambda b:b.update(points=b['points'][-1:]))
        self.assertEqual(self.call()['execution_status'],'DATA_BLOCKED')

    def test_original_solver_expenditure_consumes_remaining_solver_cap(self):
        o=self.original
        old=native.plan_route_candidates(o['graph_input'],o['decision_input'],graph_policy=o['graph_policy'],policy=o['route_policy'])
        cap=old['work']['shortest_path_calls'];o['route_policy']['capacities']['max_shortest_path_calls']=cap
        new=native.plan_route_candidates(o['graph_input'],o['decision_input'],graph_policy=o['graph_policy'],policy=o['route_policy'])
        o['route_prediction_sha256']=new['route_prediction_sha256']
        for name in ('selection_source','observation_source'):
            edit(self.execution,name,lambda b:b.update(original_route_prediction_sha256=o['route_prediction_sha256'],selected_route_sha256=new['routes'][0]['route_sha256']))
        r=self.call();self.assertEqual(r['work']['shortest_path_calls'],cap)
        self.assertEqual(r['remaining_routes'],[]);self.assertTrue(r['remaining_native_result']['search_exhausted'])

    def test_later_audit_can_describe_old_points_but_not_post_horizon_points(self):
        self.execution['update_as_of']='2026-10-26T21:00:00+09:00'
        self.assertEqual(self.call(diagnose=True)['execution_status'],'DIAGNOSTIC_ONLY')
        def late(b):
            b['points'][0]['observed_at']='2026-10-26T20:31:00+09:00'
            b['points'][1]['observed_at']='2026-10-26T20:32:00+09:00'
        edit(self.execution,'observation_source',late)
        self.execution['observation_source']['readiness']={k:self.execution['update_as_of'] for k in self.execution['observation_source']['readiness']}
        self.assertEqual(self.call(diagnose=True)['execution_status'],'FAIL')

    def test_duplicate_identity_unsupported_origin_and_source_size_rejected(self):
        for modify in (lambda b:b['points'][1].update(point_id='p1'),
                       lambda b:b.update(origin='GPS_INTERPOLATED'),
                       lambda b:b['points'][1].update(sequence=True)):
            self.original,self.execution,self.policy=fixture();edit(self.execution,'observation_source',modify)
            self.assertIn(self.call()['execution_status'],('FAIL','IMPLEMENTATION_BLOCKED'))
        self.original,self.execution,self.policy=fixture();self.execution['observation_source']['size_bytes']=True
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_original_plan_byte_tamper_cannot_be_resealed_by_new_execution_source(self):
        plan=self.original['decision_input']['planned_effort_inputs'];before=copy.deepcopy(plan)
        plan['raw_plan_utf8']+=' '
        r=self.call();self.assertIn(r['execution_status'],('FAIL','DATA_BLOCKED'));self.assertEqual(r['remaining_routes'],[])
        self.assertEqual(plan['raw_plan_utf8'],before['raw_plan_utf8']+' ')


if __name__=='__main__':unittest.main()
