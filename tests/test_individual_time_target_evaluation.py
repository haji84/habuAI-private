"""Synthetic individual-token bounds; no real identities, sources or policy."""
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

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from master_contracts import digest

CTX=dict(operational_night='2026-10-26',cutoff_time='2026-10-26T19:00:00+09:00',
         horizon_start='2026-10-26T20:00:00+09:00',horizon_end='2026-10-26T23:00:00+09:00')
SCOPE=dict(crs='EPSG:32652',bbox_utm=[299000,2999000,302000,3002000])
LINEAGE=dict(model_sha256='a'*64,prediction_sha256='b'*64,selection_policy_sha256='c'*64)
OBSERVATION=dict(observation_target='OWNER_CAPTURED_HABU_INDIVIDUALS',owner_id='synthetic-owner')


def position(x=300050.,y=3000050.,radius=0.):
    return dict(crs='EPSG:32652',x_m=x,y_m=y,uncertainty_radius_m=radius)


def node(ident,role,body,*,parents=(),ready=None):
    ready=ready or ('2026-10-26T18:00:00+09:00' if role=='UNIVERSE' else
        '2026-10-26T18:45:00+09:00' if role=='TARGETS' else '2026-10-27T08:00:00+09:00')
    raw=json.dumps(body,sort_keys=True,indent=2,ensure_ascii=False)+'\n';encoded=raw.encode()
    return dict(id=ident,role=role,parents=list(parents),raw_json_utf8=raw,
        ref=dict(path='evidence/synthetic/'+ident+'.json',sha256=hashlib.sha256(encoded).hexdigest(),size_bytes=len(encoded)),
        readiness=dict.fromkeys(('source_received_at','derived_at','materialized_at','audited_at'),ready),usable_at=ready)


def bodies(bundle):
    return {s['role']:json.loads(s['raw_json_utf8']) for s in bundle['sources']}


def publish(bundle,protocol,values):
    universe=node('universe','UNIVERSE',values['UNIVERSE'])
    target=values['TARGETS'];target['universe_source_sha256']=universe['ref']['sha256']
    targets=node('targets','TARGETS',target,parents=['universe'])
    ledger=node('ledger','LEDGER',values['LEDGER'])
    bundle['sources']=[universe,targets,ledger]
    protocol['exante_source_sha256']=dict(universe=universe['ref']['sha256'],targets=targets['ref']['sha256'])
    if 'ASCERTAINMENT' in values:
        for role,ident in [('ACTIVE_SEARCH','active-search'),('OUTCOME_SCOPE','outcome-scope')]:
            value=values[role]
            if role=='OUTCOME_SCOPE':value['ledger_source_sha256']=ledger['ref']['sha256']
            bundle['sources'].append(node(ident,role,value,parents=['ledger'] if role=='OUTCOME_SCOPE' else []))
        values['ASCERTAINMENT']['ledger_source_sha256']=ledger['ref']['sha256']
        bundle['sources'].append(node('ascertainment','ASCERTAINMENT',values['ASCERTAINMENT'],parents=['active-search','outcome-scope']))
        bundle['ascertainment_source_id']='ascertainment'


def fixture():
    p=dict(schema_version='habu-individual-target-protocol-v1',phase='DEVELOPMENT',target_semantics='VERIFIED_INDIVIDUAL_TOKEN',
        **OBSERVATION,
        radius_m=100,tolerance_seconds=600,crs='EPSG:32652',distance_method='EUCLIDEAN',
        uncertainty_method='FINITE_BOUNDS_CERTAIN_POSSIBLE_OR_UNKNOWN',
        matching_policy='ORDERED_DFS_MAX_INDIVIDUAL_CARDINALITY_V1',tie_policy='DISTANCE_THEN_TIME_THEN_INDIVIDUAL_ID',
        numeric_margins=dict(distance_m=0.,time_seconds=0.),context=copy.deepcopy(CTX),scope=copy.deepcopy(SCOPE),
        frozen_at='2026-10-26T18:45:00+09:00',assessment_as_of='2026-10-27T12:00:00+09:00',
        lineage=copy.deepcopy(LINEAGE),exante_source_sha256={},
        capacities=dict(max_targets=100,max_units=120000,max_events=20000,max_individuals=100000,max_sources=4096,
            max_json_bytes=16*1024**2,max_json_nodes=2000000,max_depth=24,max_raw_source_bytes=4*1024**2,
            max_pair_checks=2000000,max_edges=2000000,max_seconds=30))
    universe=dict(schema_version='habu-individual-target-source-v1',kind='FUTURE_UNIVERSE',context=copy.deepcopy(CTX),scope=copy.deepcopy(SCOPE),
        units=[dict(row_id='u0',cell_x=3000,cell_y=30000,window_start_jst='2026-10-26T21:00:00+09:00')])
    targets=dict(schema_version='habu-individual-target-source-v1',kind='FROZEN_TARGETS',context=copy.deepcopy(CTX),
        scope_sha256=digest(SCOPE),produced=True,**OBSERVATION,**copy.deepcopy(LINEAGE),universe_source_sha256=None,
        frozen_at=p['frozen_at'],targets=[dict(target_id='t0',source_unit_id='u0',predicted_time='2026-10-26T21:05:00+09:00',
            time_uncertainty_seconds=0.,position=position())])
    ledger=dict(schema_version='habu-individual-target-source-v1',kind='VERIFIED_INDIVIDUAL_LEDGER',context=copy.deepcopy(CTX),
        scope_sha256=digest(SCOPE),scope_declaration='DECLARED_COMPLETE',**OBSERVATION,events=[dict(event_id='event0',operational_night='2026-10-26',
            recorded_time='2026-10-26T21:05:00+09:00',time_uncertainty_seconds=0.,position=position(),
            verified_individual_ids=['individual0','individual1'],declared_count=2,individual_ids_complete=True,
            outcome_available_at='2026-10-26T21:06:00+09:00')])
    b=dict(schema_version='habu-individual-target-evaluation-input-v1',universe_source_id='universe',targets_source_id='targets',
        ledger_source_id='ledger',ascertainment_source_id=None,sources=[])
    publish(b,p,dict(UNIVERSE=universe,TARGETS=targets,LEDGER=ledger));return b,p


def add_ascertainment(bundle,protocol,*,active_kind='INDEPENDENT_ACTIVE_SEARCH_COVERAGE',radius=150.,start='2026-10-26T20:50:00+09:00',end='2026-10-26T21:20:00+09:00'):
    values=bodies(bundle);common=dict(schema_version='habu-individual-target-source-v1',context=copy.deepcopy(protocol['context']),scope_sha256=digest(protocol['scope']),**OBSERVATION)
    coverage=[dict(coverage_id='coverage0',center_x_m=300050.,center_y_m=3000050.,radius_m=radius,start=start,end=end)]
    values['ACTIVE_SEARCH']=dict(**common,kind=active_kind,coverage_semantics='WHOLE_REGION_ACTIVE_HABU_SEARCH',
        independence_basis='SEPARATE_SEARCH_RECORD_NOT_CAPTURE_OR_GPS_INFERENCE',coverage=copy.deepcopy(coverage))
    values['OUTCOME_SCOPE']=dict(**common,kind='COMPLETE_CAPTURE_OUTCOME_COVERAGE',ledger_source_sha256=None,
        coverage_semantics='COMPLETE_OWNER_CAPTURE_OUTCOMES',event_ids=[e['event_id'] for e in values['LEDGER']['events']],coverage=copy.deepcopy(coverage))
    values['ASCERTAINMENT']=dict(**common,kind='TARGET_ASCERTAINMENT',ledger_source_sha256=None,
        records=[dict(target_id='t0',active_search_source_id='active-search',outcome_source_id='outcome-scope')])
    publish(bundle,protocol,values)


class IndividualTargetTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('individual_time_target_evaluation'),'individual evaluator missing')
        self.api=importlib.import_module('individual_time_target_evaluation');self.bundle,self.protocol=fixture()

    def call(self,**kw):return self.api.evaluate_individual_targets(self.bundle,protocol=self.protocol,**kw)

    def test_one_target_two_verified_individuals_is_half_not_old_event_coverage_one(self):
        result=self.call();self.assertEqual(result['execution_status'],'DIAGNOSTIC_COMPUTED',result)
        self.assertEqual((result['matched_individuals'],result['denominator_min'],result['denominator_max']),(1,2,2))
        self.assertEqual(result['individual_recall'],.5);self.assertEqual(len(result['matching']),1)
        self.assertEqual(result['matching'][0]['individual_id'],'individual0')
        from tests.test_time_target_evaluation import fixture as old_fixture,rebound,evaluate
        u,t,l,p=old_fixture();t['targets']=t['targets'][:1];l['events']=l['events'][:1]
        old=evaluate(rebound(u,t,l,p));self.assertEqual(old['metrics']['secondary_individual_coverage'],1)
        self.assertFalse(result['official_100m_10min_kpi_computed']);self.assertFalse(result['production_authorized'])

    def test_unknown_unsearched_unmatched_target_is_not_false_positive(self):
        values=bodies(self.bundle);values['LEDGER']['events'][0]['position']=position(300149.)
        values['LEDGER']['events'][0]['recorded_time']='2026-10-26T21:16:00+09:00'
        values['LEDGER']['events'][0]['outcome_available_at']='2026-10-26T21:17:00+09:00'
        publish(self.bundle,self.protocol,values);result=self.call()
        self.assertEqual(result['individual_recall'],0)
        self.assertIsNone(result['false_positives']);self.assertIsNone(result['precision'])
        self.assertEqual(result['unknown_target_ids'],['t0'])

    def test_fixed_inclusive_distance_and_time_boundaries_do_not_gain_epsilon(self):
        for dx,seconds,expected in ((100,600,.5),(100.00001,600,0),(100,600.00001,0)):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle)
            values['UNIVERSE']['units'].append(dict(row_id='neighbor',cell_x=3001,cell_y=30000,window_start_jst='2026-10-26T21:10:00+09:00'))
            event=values['LEDGER']['events'][0];event['position']=position(300050+dx)
            event['recorded_time']='2026-10-26T21:15:00.000010+09:00' if seconds>600 else '2026-10-26T21:15:00+09:00'
            event['outcome_available_at']='2026-10-26T21:16:00+09:00';publish(self.bundle,self.protocol,values)
            self.assertEqual(self.call()['individual_recall'],expected)

    def test_outside_future_universe_stays_a_fixed_miss_in_full_denominator(self):
        values=bodies(self.bundle);values['LEDGER']['events'][0]['position']=position(300149.)
        publish(self.bundle,self.protocol,values);result=self.call()
        self.assertEqual(result['individual_recall'],0);self.assertEqual(result['denominator_min'],2)
        self.assertEqual(result['outside_eligible_individual_ids'],['individual0','individual1'])

    def test_unknown_position_time_or_count_is_not_removed_to_improve_recall(self):
        for unknown in ('position','time','count','identity'):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle);event=values['LEDGER']['events'][0]
            if unknown=='position':event['position']=None
            elif unknown=='time':event.update(recorded_time=None,time_uncertainty_seconds=None)
            elif unknown=='count':event.update(declared_count=None,individual_ids_complete=False)
            else:event.update(verified_individual_ids=['individual0'],individual_ids_complete=False)
            publish(self.bundle,self.protocol,values);result=self.call()
            self.assertIsNone(result['individual_recall'],result)
            self.assertTrue(result['unscorable_individual_count'] or result['identity_incomplete_event_count'] or result['unknown_count_event_count'])
            self.assertEqual(result['registered_verified_individual_count'],1 if unknown=='identity' else 2)
            if unknown=='count':self.assertIsNone(result['denominator_max'])

    def test_positive_margins_only_create_unresolved_bounds_not_expanded_confirmed_match(self):
        values=bodies(self.bundle);event=values['LEDGER']['events'][0]
        event['position']=position(300150.00001);event['recorded_time']='2026-10-26T21:15:00+09:00';event['outcome_available_at']='2026-10-26T21:16:00+09:00'
        values['UNIVERSE']['units'].append(dict(row_id='neighbor',cell_x=3001,cell_y=30000,window_start_jst='2026-10-26T21:10:00+09:00'))
        self.protocol['numeric_margins']=dict(distance_m=.001,time_seconds=.001)
        publish(self.bundle,self.protocol,values);result=self.call()
        self.assertIsNone(result['individual_recall']);self.assertEqual(result['matched_individuals'],0)
        self.assertEqual(result['matching_bounds'],dict(certain=0,possible=1))
        self.assertEqual(result['recall_bounds'],dict(lower=0.,upper=.5))

    def test_sources_are_exact_utf8_and_prereveal_clocks_not_authenticated(self):
        self.bundle['sources'][0]['raw_json_utf8']+=' '
        self.assertEqual(self.call()['execution_status'],'FAIL')
        self.bundle,self.protocol=fixture();self.bundle['sources'][1]['usable_at']=self.protocol['context']['cutoff_time']
        for key in self.bundle['sources'][1]['readiness']:self.bundle['sources'][1]['readiness'][key]=self.bundle['sources'][1]['usable_at']
        result=self.call();self.assertEqual(result['execution_status'],'DATA_BLOCKED')
        self.assertFalse(result['source_authorized']);self.assertFalse(result['prereveal_authorized'])

    def test_duplicate_individuals_targets_and_incomplete_multiplicity_fail_closed(self):
        for mode in ('individual','target','count'):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle)
            if mode=='individual':values['LEDGER']['events'][0]['verified_individual_ids']=['same','same']
            elif mode=='target':values['TARGETS']['targets']*=2
            else:values['LEDGER']['events'][0]['declared_count']=1
            publish(self.bundle,self.protocol,values);self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_whole_cylinder_separate_active_and_outcome_sources_are_required_for_fp(self):
        for short in (False,True):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle);values['LEDGER']['events']=[]
            publish(self.bundle,self.protocol,values)
            add_ascertainment(self.bundle,self.protocol,end='2026-10-26T21:10:00+09:00' if short else '2026-10-26T21:20:00+09:00')
            result=self.call()
            self.assertEqual(result['false_positives'],None if short else 1,result)
            self.assertEqual(result['unknown_target_ids'],['t0'] if short else [])

    def test_gps_only_or_capture_ledger_cannot_prove_whole_region_search(self):
        add_ascertainment(self.bundle,self.protocol,active_kind='GPS_ONLY')
        result=self.call();self.assertNotEqual(result.get('false_positives'),1)
        self.assertNotEqual(result['execution_status'],'DIAGNOSTIC_COMPUTED')

    def test_exact_builtin_boundaries_deadline_and_no_io(self):
        calls=[]
        class Meta(type):
            def __eq__(cls,other):calls.append('eq');raise AssertionError('metaclass')
            __hash__=type.__hash__
        class Evil(metaclass=Meta):
            def __deepcopy__(self,memo):calls.append('copy');raise AssertionError('copy')
        self.bundle['sources'][0]=Evil();self.assertEqual(self.call()['execution_status'],'FAIL');self.assertEqual(calls,[])
        self.bundle,self.protocol=fixture()
        for value in (True,0,10**1000,math.inf):self.assertEqual(self.call(budget_seconds=value)['execution_status'],'FAIL')
        self.assertEqual(self.call(budget_seconds=1e-12)['execution_status'],'RUNTIME_BLOCKED')
        import socket,subprocess
        with (patch('builtins.open',side_effect=AssertionError('I/O')),
              patch.object(socket.socket,'connect',side_effect=AssertionError('network')),
              patch.object(subprocess,'Popen',side_effect=AssertionError('process'))):
            self.assertEqual(self.call()['execution_status'],'DIAGNOSTIC_COMPUTED')

    def test_input_immutability_determinism_and_complete_output_seal(self):
        before=copy.deepcopy((self.bundle,self.protocol));first=self.call();second=self.call()
        self.assertEqual(first,second);self.assertEqual(before,(self.bundle,self.protocol))
        self.assertEqual(first['receipt_sha256'],digest({k:v for k,v in first.items() if k!='receipt_sha256'}))
        self.assertEqual(first['source_authentication'],'NOT_ATTESTED');self.assertFalse(first['scientific_authorized'])

    def test_greedy_trap_relocates_first_owner_and_matches_two_individuals(self):
        values=bodies(self.bundle)
        values['UNIVERSE']['units']+= [dict(row_id='early',cell_x=3000,cell_y=30000,window_start_jst='2026-10-26T20:50:00+09:00'),
            dict(row_id='later',cell_x=3000,cell_y=30000,window_start_jst='2026-10-26T21:10:00+09:00')]
        target=copy.deepcopy(values['TARGETS']['targets'][0]);target.update(target_id='t1',source_unit_id='later',predicted_time='2026-10-26T21:15:00+09:00')
        values['TARGETS']['targets'].append(target)
        event=values['LEDGER']['events'][0];event.update(recorded_time='2026-10-26T21:08:00+09:00',verified_individual_ids=['A'],declared_count=1,outcome_available_at='2026-10-26T21:09:00+09:00')
        second=copy.deepcopy(event);second.update(event_id='event1',recorded_time='2026-10-26T20:57:00+09:00',verified_individual_ids=['B'],outcome_available_at='2026-10-26T20:58:00+09:00')
        values['LEDGER']['events'].append(second);publish(self.bundle,self.protocol,values)
        result=self.call();self.assertEqual(result['individual_recall'],1)
        self.assertEqual([(m['target_id'],m['individual_id']) for m in result['matching']],[('t0','B'),('t1','A')])

    def test_finite_source_precision_can_resolve_matching_without_defaulting_to_zero(self):
        values=bodies(self.bundle);event=values['LEDGER']['events'][0]
        event.update(position=position(radius=10),time_uncertainty_seconds=30)
        publish(self.bundle,self.protocol,values);result=self.call()
        self.assertEqual(result['individual_recall'],.5)
        self.assertEqual(result['matching_bounds'],dict(certain=1,possible=1))

    def test_uncertainty_crossing_seven_am_keeps_scope_membership_unresolved(self):
        values=bodies(self.bundle)
        self.protocol['context']['horizon_end']='2026-10-27T07:00:00+09:00'
        for value in values.values():value['context']=copy.deepcopy(self.protocol['context'])
        values['UNIVERSE']['units'].append(dict(row_id='last',cell_x=3000,cell_y=30000,window_start_jst='2026-10-27T06:50:00+09:00'))
        values['LEDGER']['events'][0].update(recorded_time='2026-10-27T06:59:00+09:00',time_uncertainty_seconds=120,
            outcome_available_at='2026-10-27T07:02:00+09:00')
        publish(self.bundle,self.protocol,values);result=self.call()
        self.assertIsNone(result['individual_recall']);self.assertEqual(result['registered_verified_individual_count'],2)
        self.assertEqual((result['denominator_min'],result['denominator_max']),(0,2))
        self.assertEqual(result['unscorable_individual_count'],2)

    def test_duplicate_forecast_left_after_one_individual_is_unknown_until_whole_scope_is_ascertained(self):
        for proof in (False,True):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle)
            values['UNIVERSE']['units'].append(dict(row_id='later',cell_x=3000,cell_y=30000,window_start_jst='2026-10-26T21:10:00+09:00'))
            target=copy.deepcopy(values['TARGETS']['targets'][0]);target.update(target_id='t1',source_unit_id='later',predicted_time='2026-10-26T21:15:00+09:00')
            values['TARGETS']['targets'].append(target)
            values['LEDGER']['events'][0].update(verified_individual_ids=['individual0'],declared_count=1,
                recorded_time='2026-10-26T21:10:00+09:00',outcome_available_at='2026-10-26T21:11:00+09:00')
            publish(self.bundle,self.protocol,values)
            if proof:
                add_ascertainment(self.bundle,self.protocol,end='2026-10-26T21:30:00+09:00')
                values=bodies(self.bundle);values['ASCERTAINMENT']['records'].append(dict(target_id='t1',active_search_source_id='active-search',outcome_source_id='outcome-scope'))
                publish(self.bundle,self.protocol,values)
            result=self.call();self.assertEqual(result['matched_individuals'],1)
            self.assertEqual(result['false_positives'],1 if proof else None)
            self.assertEqual(result['precision'],.5 if proof else None)
            self.assertEqual(len(result['unknown_target_ids']),0 if proof else 1)

    def test_unselected_invalid_universe_cell_below_scope_is_not_ignored(self):
        values=bodies(self.bundle)
        values['UNIVERSE']['units'].append(dict(row_id='invalid-extra',cell_x=2980,cell_y=30000,window_start_jst='2026-10-26T21:00:00+09:00'))
        publish(self.bundle,self.protocol,values)
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_shared_raw_parent_does_not_authenticate_independent_search_for_fp(self):
        values=bodies(self.bundle);values['LEDGER']['events']=[];publish(self.bundle,self.protocol,values)
        add_ascertainment(self.bundle,self.protocol)
        shared=node('shared','SUPPORT',dict(schema_version='habu-individual-target-source-v1',kind='SUPPORT',details={'basis':'one observational record'}))
        self.bundle['sources'].append(shared)
        for source in self.bundle['sources']:
            if source['role'] in ('LEDGER','ACTIVE_SEARCH'):source['parents']=['shared']
        result=self.call();self.assertIsNone(result['false_positives'])
        self.assertEqual(result['unknown_target_ids'],['t0'])

    def test_bound_universe_and_ledger_hashes_also_require_physical_readiness_parents(self):
        self.bundle['sources'][1]['parents']=[]
        self.assertEqual(self.call()['execution_status'],'FAIL')
        self.bundle,self.protocol=fixture();add_ascertainment(self.bundle,self.protocol)
        for source in self.bundle['sources']:
            if source['role']=='OUTCOME_SCOPE':source['parents']=[]
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_invalid_auxiliary_proof_is_not_hidden_by_shared_parent_rejection(self):
        values=bodies(self.bundle);values['LEDGER']['events']=[];publish(self.bundle,self.protocol,values)
        add_ascertainment(self.bundle,self.protocol)
        values=bodies(self.bundle);values['OUTCOME_SCOPE']['event_ids']=['unbound-event'];publish(self.bundle,self.protocol,values)
        shared=node('shared','SUPPORT',dict(schema_version='habu-individual-target-source-v1',kind='SUPPORT',details={'basis':'one record'}))
        self.bundle['sources'].append(shared)
        for source in self.bundle['sources']:
            if source['role'] in ('LEDGER','ACTIVE_SEARCH'):source['parents']=['shared']
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_missing_ids_and_unknown_total_never_generate_individuals_or_exact_denominator(self):
        values=bodies(self.bundle);values['LEDGER']['events'][0].update(verified_individual_ids=None,declared_count=None,individual_ids_complete=False)
        publish(self.bundle,self.protocol,values);result=self.call()
        self.assertEqual(result['registered_verified_individual_count'],0)
        self.assertIsNone(result['individual_recall']);self.assertIsNone(result['denominator_max'])
        self.assertEqual(result['matching'],[]);self.assertEqual(result['unknown_count_event_count'],1)

    def test_source_graph_duplicate_json_caps_and_missing_bundle_are_structured(self):
        for mode in ('cycle','missing-source','duplicate-json','capacity'):
            self.bundle,self.protocol=fixture()
            if mode=='cycle':self.bundle['sources'][0]['parents']=['targets']
            elif mode=='missing-source':self.bundle['sources']=[]
            elif mode=='duplicate-json':
                raw='{"schema_version":"a","schema_version":"b"}';source=self.bundle['sources'][2]
                source['raw_json_utf8']=raw;source['ref'].update(sha256=hashlib.sha256(raw.encode()).hexdigest(),size_bytes=len(raw.encode()))
            else:self.protocol['capacities']['max_edges']=1
            result=self.call();self.assertEqual(result['execution_status'],'DATA_BLOCKED' if mode=='missing-source' else 'RUNTIME_BLOCKED' if mode=='capacity' else 'FAIL')
            self.assertIsNone(result['individual_recall']);self.assertIsNone(result['denominator_max'])
        result=self.api.evaluate_individual_targets(None,protocol=self.protocol)
        self.assertEqual(result['execution_status'],'DATA_BLOCKED')

    def test_declared_empty_target_set_is_not_a_missing_generator_or_positive_forecast(self):
        values=bodies(self.bundle);values['TARGETS']['targets']=[];publish(self.bundle,self.protocol,values)
        result=self.call();self.assertEqual(result['individual_recall'],0);self.assertEqual(result['matched_individuals'],0)
        self.assertEqual(result['denominator_min'],2)
        values['TARGETS']['produced']=False;publish(self.bundle,self.protocol,values)
        self.assertEqual(self.call()['execution_status'],'DATA_BLOCKED')

    def test_unknown_target_geometry_is_explicitly_unscorable_even_if_known_outcomes_are_misses(self):
        values=bodies(self.bundle);values['TARGETS']['targets'][0]['position']=None
        values['LEDGER']['events'][0]['position']=position(300149.)
        publish(self.bundle,self.protocol,values);result=self.call()
        self.assertIsNone(result['individual_recall']);self.assertEqual(result['denominator_min'],2)
        self.assertEqual(result['unscorable_target_count'],1)

    def test_submicrosecond_source_time_is_not_silently_truncated_onto_600s_boundary(self):
        values=bodies(self.bundle)
        values['UNIVERSE']['units'].append(dict(row_id='neighbor',cell_x=3001,cell_y=30000,window_start_jst='2026-10-26T21:10:00+09:00'))
        values['LEDGER']['events'][0].update(recorded_time='2026-10-26T21:15:00.0000001+09:00',position=position(300150.),outcome_available_at='2026-10-26T21:16:00+09:00')
        publish(self.bundle,self.protocol,values)
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_unknown_observation_target_blocks_without_inventing_habu_or_owner(self):
        for role in ('TARGETS','LEDGER','ACTIVE_SEARCH','OUTCOME_SCOPE','ASCERTAINMENT'):
            self.bundle,self.protocol=fixture()
            if role not in ('TARGETS','LEDGER'):add_ascertainment(self.bundle,self.protocol)
            values=bodies(self.bundle);values[role]['observation_target']='UNKNOWN'
            publish(self.bundle,self.protocol,values);result=self.call()
            self.assertEqual(result['execution_status'],'DATA_BLOCKED',result)
            self.assertIsNone(result['individual_recall']);self.assertIsNone(result['denominator_max'])
        self.bundle,self.protocol=fixture();self.protocol['owner_id']=None
        self.assertEqual(self.call()['execution_status'],'DATA_BLOCKED')

    def test_foreign_fauna_person_or_roadkill_and_wrong_owner_cannot_be_owner_capture_denominator(self):
        for target in ('OWNER_CAPTURED_OTHER_FAUNA','OTHER_PERSON_CAPTURED_HABU','OWNER_FOUND_ROADKILL_HABU'):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle);values['LEDGER']['observation_target']=target
            publish(self.bundle,self.protocol,values);self.assertEqual(self.call()['execution_status'],'FAIL')
        self.bundle,self.protocol=fixture();values=bodies(self.bundle);values['LEDGER']['owner_id']='other-owner'
        publish(self.bundle,self.protocol,values);self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_numeric_margin_does_not_turn_bare_ascertainment_boundary_into_confirmed_fp(self):
        values=bodies(self.bundle);values['LEDGER']['events']=[];publish(self.bundle,self.protocol,values)
        add_ascertainment(self.bundle,self.protocol,radius=100.,start='2026-10-26T20:55:00+09:00',end='2026-10-26T21:15:00+09:00')
        self.protocol['numeric_margins']=dict(distance_m=1.,time_seconds=1.)
        result=self.call();self.assertIsNone(result['false_positives']);self.assertEqual(result['unknown_target_ids'],['t0'])

    def test_raw_decimal_precision_is_not_silently_rounded_onto_100m_boundary(self):
        values=bodies(self.bundle)
        values['UNIVERSE']['units'].append(dict(row_id='neighbor',cell_x=3001,cell_y=30000,window_start_jst='2026-10-26T21:00:00+09:00'))
        values['LEDGER']['events'][0]['position']=position(300150.)
        publish(self.bundle,self.protocol,values)
        self.assertEqual(self.call()['individual_recall'],.5)
        source=self.bundle['sources'][2]
        raw=source['raw_json_utf8'].replace('300150.0','300150.000000000000001')
        self.assertNotEqual(raw,source['raw_json_utf8'])
        source['raw_json_utf8']=raw;source['ref'].update(sha256=hashlib.sha256(raw.encode()).hexdigest(),size_bytes=len(raw.encode()))
        result=self.call();self.assertEqual(result['execution_status'],'FAIL',result)
        self.assertIsNone(result['individual_recall'])

    def test_extreme_decimal_exponent_is_structured_and_exact_zero_lexeme_is_supported(self):
        for token,expected in (('0e3','DIAGNOSTIC_COMPUTED'),('0e'+'9'*1000,'FAIL'),('1e-9999','FAIL')):
            self.bundle,self.protocol=fixture();source=self.bundle['sources'][2]
            raw=source['raw_json_utf8'].replace('"uncertainty_radius_m": 0.0','"uncertainty_radius_m": '+token)
            source['raw_json_utf8']=raw;source['ref'].update(sha256=hashlib.sha256(raw.encode()).hexdigest(),size_bytes=len(raw.encode()))
            self.assertEqual(self.call()['execution_status'],expected)

    def test_late_deadline_discards_unsealed_denominator_and_classification_outputs(self):
        ticks=[0]
        def clock():
            ticks[0]+=1
            return 31. if ticks[0]>=1500 else 0.
        with patch.object(self.api.time,'monotonic',clock):result=self.call()
        self.assertEqual(result['execution_status'],'RUNTIME_BLOCKED')
        self.assertEqual(result['blockers'],['SHARED_DEADLINE_EXCEEDED'])
        self.assertIsNone(result['individual_recall']);self.assertIsNone(result['denominator_max'])
        for field in ('full_canonical_denominator','false_positive_target_ids','outside_eligible_individual_ids',
                      'input_digests','source_sha256','work','receipt_sha256'):
            self.assertNotIn(field,result)

    def test_derived_distance_radius_and_time_do_not_round_a_strict_excess_into_certain(self):
        for mode,tiny in (('hypot',1e-9),('radius',1e-15),('time',1e-15),('radius',5e-324),('time',5e-324)):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle)
            values['UNIVERSE']['units'].extend([
                dict(row_id='neighbor-space',cell_x=3001,cell_y=30000,window_start_jst='2026-10-26T21:00:00+09:00'),
                dict(row_id='neighbor-time',cell_x=3000,cell_y=30000,window_start_jst='2026-10-26T21:10:00+09:00')])
            event=values['LEDGER']['events'][0]
            if mode=='hypot':event['position']=position(300150.,3000050.+tiny)
            elif mode=='radius':event['position']=position(300150.,radius=tiny)
            else:event.update(recorded_time='2026-10-26T21:15:00+09:00',time_uncertainty_seconds=tiny,outcome_available_at='2026-10-26T21:16:00+09:00')
            publish(self.bundle,self.protocol,values);result=self.call()
            self.assertEqual(result['matched_individuals'],0,(mode,tiny,result))
            self.assertEqual(result['matching_bounds']['possible'],0 if mode=='hypot' else 1)
            self.assertEqual(result['individual_recall'],0 if mode=='hypot' else None)

    def test_derived_whole_cylinder_distance_and_time_excess_never_confirms_fp(self):
        for mode,tiny in (('hypot',1e-9),('time',1e-15),('time',5e-324)):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle);values['LEDGER']['events']=[]
            if mode=='time':values['TARGETS']['targets'][0]['time_uncertainty_seconds']=tiny
            publish(self.bundle,self.protocol,values)
            add_ascertainment(self.bundle,self.protocol,radius=150. if mode=='hypot' else 100.,start='2026-10-26T20:55:00+09:00',end='2026-10-26T21:15:00+09:00')
            if mode=='hypot':
                values=bodies(self.bundle)
                for role in ('ACTIVE_SEARCH','OUTCOME_SCOPE'):
                    values[role]['coverage'][0].update(center_x_m=300100.,center_y_m=3000050.+tiny)
                publish(self.bundle,self.protocol,values)
            result=self.call();self.assertIsNone(result['false_positives'],(mode,tiny,result))
            self.assertEqual(result['unknown_target_ids'],['t0'])

    def test_tiny_source_radius_crossing_scope_is_denominator_uncertainty_not_certain(self):
        for tiny in (1e-15,5e-324):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle)
            self.protocol['scope']['bbox_utm'][0]=300050;values['UNIVERSE']['scope']=copy.deepcopy(self.protocol['scope'])
            for role in ('TARGETS','LEDGER'):values[role]['scope_sha256']=digest(self.protocol['scope'])
            values['LEDGER']['events'][0]['position']=position(radius=tiny)
            publish(self.bundle,self.protocol,values);result=self.call()
            self.assertEqual((result['denominator_min'],result['denominator_max']),(0,2),result)
            self.assertIsNone(result['individual_recall'])

    def test_tiny_bounds_crossing_missing_space_or_time_unit_are_not_certain_eligible(self):
        for mode in ('space','time'):
            self.bundle,self.protocol=fixture();values=bodies(self.bundle);event=values['LEDGER']['events'][0]
            if mode=='space':
                values['UNIVERSE']['units'][0]['cell_x']=3001;values['TARGETS']['targets'][0]['position']=position(300150.)
                event['position']=position(300100.,radius=5e-324)
            else:event.update(recorded_time='2026-10-26T21:10:00+09:00',time_uncertainty_seconds=5e-324,outcome_available_at='2026-10-26T21:11:00+09:00')
            publish(self.bundle,self.protocol,values);result=self.call()
            self.assertEqual(result['matching_bounds'],dict(certain=0,possible=1),result)
            self.assertIsNone(result['individual_recall']);self.assertEqual(result['outside_eligible_individual_ids'],[])

    def test_tiny_coverage_scope_excess_and_horizon_interval_are_not_lost(self):
        values=bodies(self.bundle);values['LEDGER']['events']=[];publish(self.bundle,self.protocol,values)
        add_ascertainment(self.bundle,self.protocol)
        values=bodies(self.bundle)
        for role in ('ACTIVE_SEARCH','OUTCOME_SCOPE'):
            values[role]['coverage'][0].update(center_x_m=299000.,radius_m=5e-324)
        publish(self.bundle,self.protocol,values);self.assertEqual(self.call()['execution_status'],'FAIL')
        self.bundle,self.protocol=fixture();values=bodies(self.bundle)
        values['LEDGER']['events'][0].update(recorded_time='2026-10-26T23:00:00+09:00',time_uncertainty_seconds=5e-324,outcome_available_at='2026-10-26T23:01:00+09:00')
        publish(self.bundle,self.protocol,values);result=self.call()
        self.assertEqual((result['denominator_min'],result['denominator_max']),(0,2),result)
        self.assertIsNone(result['individual_recall'])

    def test_frozen_distance_tie_order_uses_exact_squared_distance_not_rounded_hypot(self):
        values=bodies(self.bundle)
        values['UNIVERSE']['units'].append(dict(row_id='neighbor',cell_x=3001,cell_y=30000,window_start_jst='2026-10-26T21:00:00+09:00'))
        far=values['LEDGER']['events'][0];far.update(position=position(300149.,3000050.000000001),verified_individual_ids=['individual0'],declared_count=1)
        close=copy.deepcopy(far);close.update(event_id='event1',position=position(300149.),verified_individual_ids=['individual1'])
        values['LEDGER']['events'].append(close);publish(self.bundle,self.protocol,values)
        result=self.call();self.assertEqual(result['matching'][0]['individual_id'],'individual1',result)
        self.assertEqual(result['individual_recall'],.5)


if __name__=='__main__':unittest.main()
