"""Synthetic original-plan route scenarios; no real GPS/intent or safety claim."""
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from master_contracts import digest
from gpx_audit import utm52n
from tests.test_count_activity import protocol as count_protocol,plan_fixture,plan_inputs
from tests.test_count_feasibility import fixture as training_fixture
from tests.test_route_graph import fixture as graph_fixture,put_source,way
from count_activity import fit_gamma_poisson,predict_gamma_poisson_units
from route_graph import build_route_graph


def source(body,available='2026-10-26T18:30:00+09:00'):
    raw=json.dumps(body,sort_keys=True,indent=2,ensure_ascii=False)+'\n';encoded=raw.encode()
    return dict(raw_json_utf8=raw,sha256=hashlib.sha256(encoded).hexdigest(),size_bytes=len(encoded),
        available_at=available,availability_basis='DECLARED_SYNTHETIC_MATERIALIZATION')


def n(identifier,lon,lat=28.0):
    return dict(type='node',id=identifier,version=1,lon=lon,lat=lat)


def cell(node):
    x,y=utm52n(node['lat'],node['lon']);return [math.floor(x/100),math.floor(y/100)]


def fixture(elements=None,allocations=None,anchors=None):
    elements=elements or [n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2]),way(11,[2,3])]
    nodes={v['id']:v for v in elements if v['type']=='node'}
    anchors=anchors or [('a',2,'way:10:1'),('b',3,'way:11:1')]
    plan=plan_fixture();plan.domain['horizon']['end']='2026-10-26T20:30:00+09:00'
    plan.plan['horizon']=dict(plan.domain['horizon'])
    plan.domain['cells']=sorted({tuple(cell(nodes[node])) for _,node,_ in anchors})
    plan.domain['cells']=[list(v) for v in plan.domain['cells']]
    if allocations is None:
        allocations=[dict(allocation_id='a',start='2026-10-26T20:05:00+09:00',end='2026-10-26T20:15:00+09:00',planned_active_search_seconds=600),
                     dict(allocation_id='b',start='2026-10-26T20:17:00+09:00',end='2026-10-26T20:22:00+09:00',planned_active_search_seconds=300)]
    by_id={a:v for a,v,_ in anchors}
    plan.plan['allocations']=copy.deepcopy(allocations)
    for allocation in plan.plan['allocations']:
        allocation['cell_x'],allocation['cell_y']=cell(nodes[by_id[allocation['allocation_id']]])
    plan.plan['domain_sha256']=digest(plan.domain);plan.publish()
    cp=count_protocol();model=fit_gamma_poisson(*training_fixture(),protocol=cp)['model']
    gi,gp=graph_fixture(elements)
    gi['domain']=dict(crs='EPSG:4326',polygons=[[[[128.96,27.96],[129.04,27.96],[129.04,28.04],[128.96,28.04],[128.96,27.96]]]])
    gi['domain']['sha256']=digest(gi['domain'])
    gi['context']=dict(operational_night='2026-10-26',cutoff_time='2026-10-26T19:00:00+09:00',
        forecast_start=plan.domain['horizon']['start'],forecast_end=plan.domain['horizon']['end'],mode='motor_vehicle')
    for claim in gi['coverage'].values():
        claim.update(domain_sha256=gi['domain']['sha256'],valid_start=gi['context']['forecast_start'],valid_end=gi['context']['forecast_end'])
    gi['sources'][0]['available_at']='2026-10-26T16:00:00+09:00'
    graph=build_route_graph(gi,policy=gp)
    count=predict_gamma_poisson_units(model,plan_inputs(plan),protocol=cp)
    originals={a['allocation']['allocation_id']:a for a in count['original_allocations']}
    links=dict(schema_version='habu-route-allocation-links-v1',graph_sha256=graph['graph_sha256'],
        graph_policy_sha256=digest(gp),graph_domain_sha256=gi['domain']['sha256'],context=gi['context'],
        model_sha256=model['model_sha256'],count_protocol_sha256=digest(cp),planned_source_sha256=count['lineage']['planned_source_sha256'],
        records=[dict(allocation_id=aid,allocation_sha256=originals[aid]['allocation_sha256'],
            association_type='OSM_NODE',node_id='osm:'+str(node),way_ref=ref) for aid,node,ref in anchors])
    profile=dict(schema_version='habu-route-travel-profile-v1',profile_id='synthetic-speed',context=gi['context'],
        identity=plan.identity,speed_m_per_second=10.0,turn_seconds=0.0,speed_basis='DECLARED_PLANNING_ASSUMPTION')
    decision=dict(schema_version='habu-conditional-route-decision-v1',graph_sha256=graph['graph_sha256'],
        graph_policy_sha256=digest(gp),graph_domain_sha256=gi['domain']['sha256'],context=gi['context'],
        model=model,count_protocol=cp,planned_effort_inputs=plan_inputs(plan),links_source=source(links),
        travel_profile_source=source(profile),start_node_id='osm:1',end_node_id='osm:1',require_return=True,
        depart_at=gi['context']['forecast_start'],time_budget_seconds=1800)
    policy=dict(schema_version='habu-conditional-route-policy-v1',phase='DEVELOPMENT',frozen_at='2026-10-25T12:00:00+09:00',
        mode='motor_vehicle',association='REAL_OSM_NODE_IN_ORIGINAL_100M_CELL',
        search_timing='FULL_ORIGINAL_ALLOCATION_STATIONARY_NODE',wait_policy='WAIT_AT_LINKED_NODE_UNTIL_ORIGINAL_START',
        partial_unit_policy='EXCLUDE_CANDIDATES_WITH_TOUCHED_INCOMPLETE_UNITS',shortest_path_objective='TRAVEL_TIME_ONLY',
        access_policy='ALLOW_DECLARED_NOT_VERIFIED_ONLY',known_speed_limit_policy='ENFORCE_PLAIN_KMH_OTHER_TAGS_BLOCK',
        uncertainty_mode='TRAVEL_ONLY_NOT_AVAILABLE',speed_bounds_m_per_second=dict(minimum=.01,maximum=30),
        utility=dict(expected_capture_weight=1.0,elapsed_seconds_weight=0.0,uncertainty_weight=0.0),
        alternatives=dict(labels=['A','B','C'],b_max_overlap=.5,c_max_overlap=.5,c_min_expected_reward=.01,
            c_objective='TRAVEL_TIME_ONLY',overlap_metric='SHARED_UNIQUE_DIRECTED_LENGTH_OVER_MIN_UNIQUE_LENGTH'),
        minimum_completed_allocations=1,minimum_completed_units=1,
        capacities=dict(max_reward_waypoints=50,beam_width=64,max_depth=20,max_expanded_states=10000,
            max_shortest_path_calls=10000,max_shortest_path_states=100000,max_shortest_path_relaxations=500000,
            max_graph_nodes=100000,max_graph_edges=200000,max_json_nodes=2000000,max_json_bytes=16000000,
            max_source_bytes=2000000,max_seconds=30))
    return gi,decision,gp,policy


def edit_source(decision,name,edit):
    old=decision[name];body=json.loads(old['raw_json_utf8']);edit(body)
    decision[name]=source(body,old['available_at'])


class RoutePlanningTests(unittest.TestCase):
    def setUp(self):
        self.api=importlib.import_module('route_planning') if importlib.util.find_spec('route_planning') else None
        self.assertIsNotNone(self.api,'Native conditional route executor missing')
        self.graph,self.decision,self.graph_policy,self.policy=fixture()

    def call(self,**kw):
        return self.api.plan_route_candidates(self.graph,self.decision,graph_policy=self.graph_policy,policy=self.policy,**kw)

    def test_actual_native_math_and_small_enumerable_complete_plan_optimum(self):
        before=copy.deepcopy((self.graph,self.decision,self.graph_policy,self.policy))
        result=self.call();self.assertEqual(result['execution_status'],'COMPUTED_RESEARCH_ONLY',result)
        a=result['routes'][0];self.assertEqual(a['label'],'A')
        self.assertEqual(a['completed_allocation_ids'],['a','b'])
        self.assertAlmostEqual(a['expected_captures'],4/7,delta=1e-14)
        # Exhaustive feasible source subsets are {a},{b},{a,b}; common rate
        # gives 8/21,4/21,4/7. The last is the literal maximum at lambda_t=0.
        self.assertAlmostEqual(a['utility'],max(8/21,4/21,4/7),delta=1e-14)
        self.assertEqual(result['navigation_status'],'NAVIGATION_BLOCKED')
        self.assertEqual(result['uncertainty'],None)
        self.assertEqual(result['uncertainty_status'],'NOT_AVAILABLE')
        self.assertFalse(result['production_authorized']);self.assertFalse(result['scientific_authorized'])
        self.assertFalse(result['global_optimum_proven'])
        self.assertEqual(before,(self.graph,self.decision,self.graph_policy,self.policy))

    def test_transit_wait_and_repeat_edges_never_add_capture_reward(self):
        result=self.call();a=result['routes'][0]
        self.assertGreater(a['travel_seconds'],0);self.assertGreater(a['wait_seconds'],0)
        self.assertEqual(a['search_seconds'],900)
        self.assertEqual(len(a['credited_unit_ids']),len(set(a['credited_unit_ids'])))
        self.assertEqual(a['arrival_node_id'],'osm:1')
        self.assertLessEqual(datetime.fromisoformat(a['arrived_at']),datetime.fromisoformat(self.decision['context']['forecast_end']))
        self.assertEqual(len(result['routes']),1)
        self.assertIn('NO_FEASIBLE_DIVERSE_B',result['missing_alternatives'])

    def test_oneway_return_and_disconnected_real_nodes_never_create_connectors(self):
        elements=[n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2],oneway='yes'),way(11,[2,3],oneway='yes')]
        self.graph,self.decision,self.graph_policy,self.policy=fixture(elements)
        result=self.call();self.assertEqual(result['routes'],[])
        self.assertIn('RETURN_UNREACHABLE',result['feasibility_reasons'])

    def test_linked_node_and_way_must_be_incident_and_same_native_cell(self):
        for change in ('cell','way','absent','projection'):
            self.graph,self.decision,self.graph_policy,self.policy=fixture()
            def edit(body):
                link=body['records'][0]
                if change=='cell':link.update(node_id='osm:3',way_ref='way:11:1')
                elif change=='way':link.update(node_id='osm:1',way_ref='way:11:1')
                elif change=='absent':link['node_id']='osm:999'
                else:link['association_type']='EDGE_PROJECTION'
            edit_source(self.decision,'links_source',edit)
            result=self.call()
            self.assertIn(result['execution_status'],('FAIL','DATA_BLOCKED','IMPLEMENTATION_BLOCKED'))
            self.assertEqual(result['routes'],[])

    def test_shared_real_node_can_bind_either_actual_incident_way(self):
        edit_source(self.decision,'links_source',lambda b:b['records'][0].update(way_ref='way:11:1'))
        self.assertEqual(self.call()['execution_status'],'COMPUTED_RESEARCH_ONLY')

    def test_own_cutoff_hash_context_identity_and_source_bytes_are_enforced(self):
        for bad in ('available','hash','context','identity','allocation'):
            self.graph,self.decision,self.graph_policy,self.policy=fixture()
            if bad=='available':self.decision['links_source']['available_at']=self.decision['context']['cutoff_time']
            elif bad=='hash':self.decision['links_source']['raw_json_utf8']+=' '
            elif bad=='context':edit_source(self.decision,'travel_profile_source',lambda b:b['context'].update(mode='motorcar'))
            elif bad=='identity':edit_source(self.decision,'travel_profile_source',lambda b:b['identity'].update(observer_id='foreign'))
            else:edit_source(self.decision,'links_source',lambda b:b['records'][0].update(allocation_sha256='0'*64))
            with self.subTest(bad=bad):
                value=self.call();self.assertNotEqual(value['execution_status'],'COMPUTED_RESEARCH_ONLY');self.assertEqual(value['routes'],[])

    def test_missing_native_model_or_source_plan_cannot_be_replaced_by_means(self):
        self.decision['model']=None
        value=self.call();self.assertEqual(value['execution_status'],'DATA_BLOCKED')
        self.assertIsNone(value['expected_captures']);self.assertEqual(value['routes'],[])
        self.graph,self.decision,self.graph_policy,self.policy=fixture()
        self.decision['unit_means']=[99]
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_uncertainty_missing_is_neither_a_declared_danger_score_nor_zero_risk(self):
        self.policy['utility']['uncertainty_weight']=1
        value=self.call();self.assertEqual(value['execution_status'],'IMPLEMENTATION_BLOCKED')
        self.assertIn('ACTUAL_UNCERTAINTY_METADATA_NOT_AVAILABLE',value['blockers'])
        self.assertEqual(value['routes'],[])

    def test_unknown_access_is_not_permission_but_unknown_global_coverage_stays_visible(self):
        elements=[n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2],motor_vehicle='unknown'),way(11,[2,3])]
        self.graph,self.decision,self.graph_policy,self.policy=fixture(elements)
        result=self.call();self.assertEqual(result['routes'],[])
        self.assertIn('ACCESS_UNKNOWN_EDGE_EXCLUDED',result['feasibility_reasons'])
        self.assertEqual(result['navigation_status'],'NAVIGATION_BLOCKED')

    def test_no_turn_constraint_remains_active_after_search_dwell(self):
        relation=dict(type='relation',id=20,version=1,tags={'type':'restriction','restriction':'no_right_turn'},members=[
            dict(type='way',ref=10,role='from'),dict(type='node',ref=2,role='via'),dict(type='way',ref=11,role='to')])
        self.graph,self.decision,self.graph_policy,self.policy=fixture([
            n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2]),way(11,[2,3]),relation])
        value=self.call()
        for route in value['routes']:
            self.assertNotEqual(route['completed_allocation_ids'],['a','b'])
            for before,after in zip(route['edge_ids'],route['edge_ids'][1:]):
                self.assertFalse(before.startswith('way:10:1:0:0:1') and after.startswith('way:11:1:0:0:1'))

    def test_unsupported_restriction_does_not_become_unrestricted_research_traversal(self):
        relation=dict(type='relation',id=20,version=1,tags={'type':'restriction','restriction':'no_right_turn','except':'motorcar'},members=[
            dict(type='way',ref=10,role='from'),dict(type='node',ref=2,role='via'),dict(type='way',ref=11,role='to')])
        self.graph,self.decision,self.graph_policy,self.policy=fixture([
            n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2]),way(11,[2,3]),relation])
        self.assertEqual(self.call()['execution_status'],'IMPLEMENTATION_BLOCKED')

    def test_global_search_caps_keep_honest_exhaustion_without_optimality(self):
        self.policy['capacities']['max_shortest_path_states']=1
        value=self.call();self.assertTrue(value['search_exhausted'])
        self.assertFalse(value['global_optimum_proven'])
        self.assertLessEqual(value['work']['shortest_path_states'],1)
        self.assertIn('SHORTEST_PATH_GLOBAL_CAPACITY_EXCEEDED',value['blockers'])

    def test_no_callback_or_write_and_native_output_bindings_are_deterministic(self):
        calls=[]
        class Meta(type):
            def __eq__(cls,other):calls.append('eq');raise AssertionError('custom equality')
            __hash__=type.__hash__
        class Evil(metaclass=Meta):
            def __deepcopy__(self,memo):calls.append('copy');raise AssertionError('copy')
        decision=copy.deepcopy(self.decision);decision['model']=Evil()
        with patch.object(self.api,'build_route_graph',side_effect=AssertionError('guard before helper')):
            value=self.api.plan_route_candidates(self.graph,decision,graph_policy=self.graph_policy,policy=self.policy)
        self.assertEqual(value['execution_status'],'FAIL');self.assertEqual(calls,[])
        import socket,subprocess
        with (patch.object(Path,'write_bytes',side_effect=AssertionError('write')),
              patch.object(Path,'write_text',side_effect=AssertionError('write')),
              patch.object(socket.socket,'connect',side_effect=AssertionError('network')),
              patch.object(subprocess,'Popen',side_effect=AssertionError('process'))):
            first=self.call();second=self.call()
        self.assertEqual(first['route_prediction_sha256'],second['route_prediction_sha256'])
        native=predict_gamma_poisson_units(self.decision['model'],self.decision['planned_effort_inputs'],protocol=self.decision['count_protocol'])
        self.assertEqual(first['native_bindings']['unit_prediction_sha256'],native['unit_prediction_sha256'])

    def test_deadline_and_boolean_or_over_engineering_limits_fail_closed(self):
        for value in (True,0,10**1000):
            self.assertEqual(self.call(budget_seconds=value)['execution_status'],'FAIL')
        self.assertEqual(self.call(budget_seconds=1e-12)['execution_status'],'RUNTIME_BLOCKED')
        self.policy['capacities']['beam_width']=65
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_three_exclusive_branches_match_literal_abc_objectives(self):
        elements=[n(1,129.00005),n(2,129.015),n(3,128.984),n(4,129.00005,28.0125),
            way(10,[1,2]),way(11,[1,3]),way(12,[1,4])]
        allocations=[dict(allocation_id=aid,start='2026-10-26T'+start+'+09:00',end='2026-10-26T'+end+'+09:00',planned_active_search_seconds=seconds)
            for aid,start,end,seconds in [('a','20:05:00','20:10:00',300),('b','20:11:00','20:15:00',240),('c','20:16:00','20:19:00',180)]]
        self.graph,self.decision,self.graph_policy,self.policy=fixture(elements,allocations,
            [('a',2,'way:10:1'),('b',3,'way:11:1'),('c',4,'way:12:1')])
        edit_source(self.decision,'travel_profile_source',lambda b:b.update(speed_m_per_second=5))
        result=self.call();routes=result['routes']
        self.assertEqual([r['label'] for r in routes],['A','B','C'],result)
        self.assertEqual([r['completed_allocation_ids'] for r in routes],[['a'],['b'],['c']])
        for route,seconds in zip(routes,[300,240,180]):self.assertAlmostEqual(route['expected_captures'],seconds/3600*8/3.5,delta=1e-14)
        self.assertEqual(len({r['route_sha256'] for r in routes}),3)
        self.assertLess(routes[2]['travel_seconds'],routes[0]['travel_seconds'])
        self.assertEqual(result['missing_alternatives'],[])

    def test_only_turn_is_not_reset_by_dwell_or_shortest_path_leg(self):
        relation=dict(type='relation',id=20,version=1,tags={'type':'restriction','restriction':'only_right_turn'},members=[
            dict(type='way',ref=10,role='from'),dict(type='node',ref=2,role='via'),dict(type='way',ref=11,role='to')])
        self.graph,self.decision,self.graph_policy,self.policy=fixture([
            n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2]),way(11,[2,3]),relation])
        result=self.call();self.assertTrue(result['routes'],result)
        for route in result['routes']:
            for before,after in zip(route['edge_ids'],route['edge_ids'][1:]):
                if before=='way:10:1:0:0:1':self.assertEqual(after,'way:11:1:0:0:1')

    def test_infeasible_second_allocation_in_same_unit_gets_no_prorated_or_full_credit(self):
        allocations=[dict(allocation_id='a1',start='2026-10-26T20:01:00+09:00',end='2026-10-26T20:03:00+09:00',planned_active_search_seconds=120),
            dict(allocation_id='a2',start='2026-10-26T20:08:00+09:00',end='2026-10-26T20:10:00+09:00',planned_active_search_seconds=120)]
        self.graph,self.decision,self.graph_policy,self.policy=fixture([
            n(1,129.00005),n(2,129.00008),n(3,129.00095),way(10,[1,2]),way(11,[2,3])],allocations,
            [('a1',2,'way:10:1'),('a2',3,'way:11:1')])
        edit_source(self.decision,'travel_profile_source',lambda b:b.update(speed_m_per_second=.1))
        result=self.call();self.assertEqual(result['routes'],[])
        self.assertIsNone(result['expected_captures'])
        self.assertIn('TOUCHED_UNIT_INCOMPLETE_NO_PARTIAL_CREDIT',result['feasibility_reasons'])

    def test_known_numeric_speed_limit_blocks_faster_assumed_travel(self):
        self.graph,self.decision,self.graph_policy,self.policy=fixture([
            n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2],maxspeed='1'),way(11,[2,3])])
        result=self.call();self.assertEqual(result['routes'],[])
        self.assertIn('KNOWN_SPEED_LIMIT_EDGE_EXCLUDED',result['feasibility_reasons'])

    def test_native_graph_failure_and_resource_capacity_have_distinct_status(self):
        self.graph['sources'][0]['sha256']='0'*64
        self.assertEqual(self.call()['execution_status'],'FAIL')
        self.graph,self.decision,self.graph_policy,self.policy=fixture()
        self.graph_policy['capacities']['max_nodes']=1
        self.graph['policy_sha256']=digest(self.graph_policy);self.decision['graph_policy_sha256']=digest(self.graph_policy)
        self.assertEqual(self.call()['execution_status'],'RUNTIME_BLOCKED')

    def test_missing_protocol_or_source_availability_is_data_blocked(self):
        self.decision['count_protocol']=None
        self.assertEqual(self.call()['execution_status'],'DATA_BLOCKED')
        self.graph,self.decision,self.graph_policy,self.policy=fixture()
        self.decision['links_source']['available_at']=None
        self.assertEqual(self.call()['execution_status'],'DATA_BLOCKED')

    def test_global_expansion_cap_retains_a_feasible_incumbent(self):
        self.policy['capacities']['max_expanded_states']=1
        result=self.call()
        self.assertEqual(result['execution_status'],'PARTIAL_RESEARCH_ONLY',result)
        self.assertEqual(result['routes'][0]['completed_allocation_ids'],['a'])
        self.assertAlmostEqual(result['routes'][0]['expected_captures'],8/21,delta=1e-14)
        self.assertTrue(result['search_exhausted']);self.assertFalse(result['global_optimum_proven'])
        self.assertEqual(result['work']['expanded_states'],1)

    def test_known_source_closure_is_not_ignored_to_reach_an_anchor(self):
        self.graph['closures']=[dict(source_sha256=self.graph['sources'][0]['sha256'],target_type='way',target_id=11,
            valid_start=self.graph['context']['forecast_start'],valid_end=self.graph['context']['forecast_end'],
            available_at='2026-10-26T18:00:00+09:00',mode='motor_vehicle',status='CLOSED')]
        native=build_route_graph(self.graph,policy=self.graph_policy)
        self.decision['graph_sha256']=native['graph_sha256']
        edit_source(self.decision,'links_source',lambda b:b.update(graph_sha256=native['graph_sha256']))
        result=self.call();self.assertEqual(result['routes'],[])
        self.assertEqual(result['execution_status'],'DATA_BLOCKED')

    def test_source_duplicate_json_and_hidden_nonfinite_values_are_rejected(self):
        for bad in ('duplicate','nonfinite'):
            self.graph,self.decision,self.graph_policy,self.policy=fixture()
            if bad=='duplicate':raw='{"schema_version":"x","schema_version":"y"}'
            else:raw='{"value":NaN}'
            node=self.decision['links_source'];node.update(raw_json_utf8=raw,
                sha256=hashlib.sha256(raw.encode()).hexdigest(),size_bytes=len(raw.encode()))
            self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_output_seal_binds_every_deterministic_field_and_budget_is_shared(self):
        result=self.call()
        self.assertEqual(result['route_prediction_sha256'],digest({k:v for k,v in result.items() if k not in ('route_prediction_sha256','runtime_elapsed_seconds')}))
        clock=[0.];original=self.api.build_route_graph
        def graph(*args,**kwargs):
            value=original(*args,**kwargs);clock[0]=31;return value
        with (patch.object(self.api.time,'monotonic',side_effect=lambda:clock[0]),
              patch.object(self.api,'build_route_graph',side_effect=graph),
              patch.object(self.api,'predict_gamma_poisson_units',side_effect=AssertionError('expired before next helper'))):
            value=self.call()
        self.assertEqual(value['execution_status'],'RUNTIME_BLOCKED');self.assertEqual(value['routes'],[])

    def test_unrepresentable_numeric_maxspeed_is_unknown_not_an_infinite_legal_limit(self):
        self.graph,self.decision,self.graph_policy,self.policy=fixture([
            n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2],maxspeed='9'*400),way(11,[2,3])])
        result=self.call();self.assertEqual(result['routes'],[])
        self.assertIn('UNSUPPORTED_SPEED_LIMIT_EDGE_EXCLUDED',result['feasibility_reasons'])

    def test_submicrosecond_lateness_is_not_rounded_into_full_allocation_feasibility(self):
        graph=build_route_graph(self.graph,policy=self.graph_policy)
        distance=next(e['length_m'] for e in graph['edges'] if e['from_node']=='osm:1' and e['to_node']=='osm:2')
        edit_source(self.decision,'travel_profile_source',lambda b:b.update(speed_m_per_second=distance/(300+1e-7)))
        result=self.call();self.assertEqual(result['routes'],[])
        self.assertIn('LATE_FOR_FULL_ORIGINAL_ALLOCATION',result['feasibility_reasons'])

    def test_submicrosecond_return_overrun_is_not_rounded_inside_horizon(self):
        graph=build_route_graph(self.graph,policy=self.graph_policy)
        distance=next(e['length_m'] for e in graph['edges'] if e['from_node']=='osm:2' and e['to_node']=='osm:1')
        edit_source(self.decision,'travel_profile_source',lambda b:b.update(speed_m_per_second=distance/(900+1e-7)))
        self.decision.update(start_node_id='osm:2',end_node_id='osm:1',require_return=False)
        result=self.call();self.assertEqual(result['routes'],[])
        self.assertIn('RETURN_EXCEEDS_BUDGET_OR_HORIZON',result['feasibility_reasons'])

    def test_native_runtime_failure_is_not_misreported_as_missing_data(self):
        import scipy
        with patch.object(scipy,'__version__','0.0.0'):result=self.call()
        self.assertEqual(result['execution_status'],'RUNTIME_BLOCKED')
        self.assertIn('NATIVE_COUNT_RUNTIME_BINDING_ERROR',result['blockers'])
        self.assertEqual(result['routes'],[])

    def test_scoped_motor_vehicle_limit_cannot_hide_behind_generic_fifty(self):
        self.graph,self.decision,self.graph_policy,self.policy=fixture([
            n(1,129.00005),n(2,129.0004),n(3,129.0013),
            way(10,[1,2],maxspeed='50',**{'maxspeed:motor_vehicle':'1'}),way(11,[2,3])])
        result=self.call()
        self.assertEqual(result['routes'],[])
        self.assertIn('UNSUPPORTED_SCOPED_SPEED_LIMIT_EDGE_EXCLUDED',result['feasibility_reasons'])

    def test_scoped_speed_grammars_are_excluded_with_or_without_generic_limit(self):
        for key in ('maxspeed:motorcar','maxspeed:hgv','maxspeed:advisory','maxspeed:type','maxspeed:unit'):
            for generic in (False,True):
                with self.subTest(key=key,generic=generic):
                    tags={key:'1'}
                    if generic:tags['maxspeed']='50'
                    self.graph,self.decision,self.graph_policy,self.policy=fixture([
                        n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2],**tags),way(11,[2,3])])
                    result=self.call();self.assertEqual(result['routes'],[])
                    self.assertIn('UNSUPPORTED_SCOPED_SPEED_LIMIT_EDGE_EXCLUDED',result['feasibility_reasons'])

    def test_plain_numeric_speed_limits_remain_supported_and_units_do_not_get_guessed(self):
        for limit in ('50','40','36'):
            with self.subTest(limit=limit):
                self.graph,self.decision,self.graph_policy,self.policy=fixture([
                    n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2],maxspeed=limit),way(11,[2,3])])
                result=self.call();self.assertEqual(result['execution_status'],'COMPUTED_RESEARCH_ONLY')
                self.assertAlmostEqual(result['routes'][0]['expected_captures'],4/7,delta=1e-14)
        for value in ('50 mph','50 km/h','walk','30;50'):
            with self.subTest(value=value):
                self.graph,self.decision,self.graph_policy,self.policy=fixture([
                    n(1,129.00005),n(2,129.0004),n(3,129.0013),way(10,[1,2],maxspeed=value),way(11,[2,3])])
                result=self.call();self.assertEqual(result['routes'],[])
                self.assertIn('UNSUPPORTED_SPEED_LIMIT_EDGE_EXCLUDED',result['feasibility_reasons'])


if __name__=='__main__':unittest.main()
