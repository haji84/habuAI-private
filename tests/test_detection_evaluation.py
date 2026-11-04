"""Synthetic source-bound detector trials; no actual biological observations."""
import copy
from datetime import datetime, timezone
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
sys.path.insert(0,str(ROOT/'src'))
from master_contracts import digest

READY='2026-10-24T11:00:00+09:00'
TRUTH_FIELDS=('opportunity_id','site_id','start_time','end_time','truth_status',
              'truth_method','truth_available_at','truth_capture_event_refs')
DETECTION_FIELDS=('opportunity_id','site_id','start_time','end_time','observer_id','mode',
    'protocol_version','effort','detected','detection_time','outcome_available_at','capture_event_refs',
    'cluster_id','independence_status','depletion_status')


def source(identifier,role,body,parents=()):
    raw=json.dumps(body,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    encoded=raw.encode('utf-8')
    return dict(id=identifier,role=role,source_kind='DERIVED' if parents else 'RAW',parents=list(parents),
        ref=dict(path='evidence/detection/'+identifier+'.json',sha256=hashlib.sha256(encoded).hexdigest(),
                 size_bytes=len(encoded)),raw_json_utf8=raw,
        readiness=dict(source_received_at='2026-10-24T09:00:00+09:00',
            derived_at='2026-10-24T10:00:00+09:00',materialized_at=READY,audited_at=READY),usable_at=READY)


def fixture():
    protocol=dict(schema_version='habu-detection-protocol-v1',phase='DEVELOPMENT',
        target='DETECTOR_SENSITIVITY_GIVEN_INDEPENDENT_KNOWN_POSITIVE_OPPORTUNITY',
        frozen_at='2026-10-19T12:00:00+09:00',assessment_as_of='2026-10-24T12:00:00+09:00',
        prior=dict(alpha=1,beta=1),quantile_probabilities=[0,.025,.5,.975,1],
        numerics=dict(cdf_absolute_tolerance=1e-10,log_tail_tolerance=1e-8),
        capacities=dict(max_opportunities=100,max_sources=20,max_json_bytes=1_000_000,
            max_json_nodes=50_000,max_depth=24,max_string_bytes=200_000,max_quantiles=10,
            min_shape=1e-6,max_shape=1e6,min_tail_probability=1e-12,max_seconds=30),
        runtime_versions={'numpy':'2.2.6','scipy':'1.15.3','scikit-learn':'1.5.2'},
        scope=dict(site_ids=['synthetic-site'],start_time='2026-10-20T07:00:00+09:00',
                   end_time='2026-10-23T07:00:00+09:00'),
        observer_binding=dict(observer_id='synthetic-observer',mode='synthetic-search',protocol_version='fixture-1'),
        effort_policy=dict(unit='minutes',method='synthetic-direct',min_value=1,max_value=60),
        truth_methods=['SYNTHETIC_INDEPENDENT_CHANNEL'],
        cohort_policy='COMPLETE_REGISTERED_INDEPENDENT_TRUTH',
        unknown_policy='REPORT_KNOWN_SUBSET_NO_FULL_COHORT_CLAIM',
        cluster_policy='ONE_OPPORTUNITY_PER_SITE_NIGHT',removal_policy='NON_REMOVAL_OPPORTUNITIES_ONLY',
        minimum_group_support=1)
    rows=[]
    for i,detected in enumerate((True,False,True)):
        day=f'2026-10-{20+i}'
        rows.append(dict(opportunity_id='trial-'+str(i),site_id='synthetic-site',
            start_time=day+'T19:00:00+09:00',end_time=day+'T19:10:00+09:00',
            truth_status='KNOWN_POSITIVE',truth_method='SYNTHETIC_INDEPENDENT_CHANNEL',
            truth_available_at='2026-10-23T08:00:00+09:00',truth_capture_event_refs=[],
            truth_source_id='truth',detection_source_id='detector',
            observer_id='synthetic-observer',mode='synthetic-search',protocol_version='fixture-1',
            effort=dict(value=10,unit='minutes',method='synthetic-direct'),detected=detected,
            detection_time=day+'T19:03:00+09:00' if detected else None,
            outcome_available_at='2026-10-23T08:00:00+09:00',capture_event_refs=[],
            cluster_id='synthetic-site:'+day,independence_status='DECLARED_INDEPENDENT',
            depletion_status='NON_REMOVAL'))
    bundle=dict(schema_version='habu-detection-opportunity-bundle-v1',cohort_source_id='cohort',
                opportunities=rows,sources=[])
    publish(bundle,protocol)
    return bundle,protocol


def publish(bundle,protocol):
    rows=bundle['opportunities']
    truth=dict(schema_version='habu-detection-source-v1',kind='TRUTH_RECORDS',
               records=[{k:r[k] for k in TRUTH_FIELDS} for r in rows])
    detector=dict(schema_version='habu-detection-source-v1',kind='DETECTION_RECORDS',
                  records=[{k:r[k] for k in DETECTION_FIELDS} for r in rows])
    cohort=dict(schema_version='habu-detection-source-v1',kind='REGISTERED_COHORT',
        opportunity_ids=[r['opportunity_id'] for r in rows],selection_rule=protocol['cohort_policy'],
        scope=protocol['scope'],observer_binding=protocol['observer_binding'],
        registered_at=protocol['frozen_at'],basis_source_ids=['truth'])
    bundle['sources']=[source('truth','TRUTH',truth),source('detector','DETECTION',detector),
                       source('cohort','COHORT',cohort,['truth'])]


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('detection_evaluation'),'independent-opportunity evaluator missing')
        self.api=importlib.import_module('detection_evaluation')
        self.bundle,self.protocol=fixture()

    def call(self,**kwargs):
        return self.api.evaluate_detection_opportunities(self.bundle,protocol=self.protocol,**kwargs)

    def test_actual_beta_math_and_distinct_empirical_posterior_mean(self):
        before=copy.deepcopy((self.bundle,self.protocol))
        result=self.call()
        self.assertEqual(result['execution_status'],'COMPUTED',result)
        self.assertEqual((result['n'],result['s']),(3,2))
        self.assertAlmostEqual(result['observed_sensitivity'],2/3)
        self.assertAlmostEqual(result['posterior_mean'],.6)
        self.assertEqual(result['posterior_parameters'],dict(alpha=3,beta=2))
        self.assertEqual(result['posterior_quantiles'][0]['value'],0)
        self.assertEqual(result['posterior_quantiles'][-1]['value'],1)
        self.assertEqual(result['source_authentication'],'NOT_ATTESTED')
        self.assertIs(result['scientific_authorized'],False)
        self.assertIs(result['production_authorized'],False)
        self.assertIsNone(result['false_positive_rate'])
        self.assertEqual(result['false_positive_status'],'NOT_VALIDATED')
        self.assertIsNone(result['brier'])
        self.assertEqual(before,(self.bundle,self.protocol))

    def test_unknown_result_is_not_false_or_complete_denominator(self):
        row=self.bundle['opportunities'][1]
        row.update(detected=None,detection_time=None)
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual(result['execution_status'],'PARTIAL')
        self.assertEqual((result['registered_cohort_size'],result['n'],result['s'],result['unknown_results']),(3,2,2,1))
        self.assertIsNone(result['observed_sensitivity'])
        self.assertEqual(result['known_subset_sensitivity'],1)

    def test_zero_n_does_not_present_prior_half_as_observed_sensitivity(self):
        for row in self.bundle['opportunities']:row.update(detected=None,detection_time=None)
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual(result['execution_status'],'DATA_BLOCKED')
        self.assertEqual(result['n'],0)
        self.assertIsNone(result['observed_sensitivity'])
        self.assertIsNone(result['known_subset_sensitivity'])
        self.assertIsNone(result['posterior_quantiles'])

    def test_undetected_known_positive_is_a_real_miss(self):
        for row in self.bundle['opportunities']:row.update(detected=False,detection_time=None)
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual((result['n'],result['s']),(3,0))
        self.assertEqual(result['observed_sensitivity'],0)
        self.assertAlmostEqual(result['posterior_mean'],.2)

    def test_registered_failure_row_cannot_be_omitted(self):
        self.bundle['opportunities'].pop(1)
        result=self.call()
        self.assertIsNone(result['observed_sensitivity'])
        self.assertIn('REGISTERED_DENOMINATOR_INCOMPLETE',result['blockers'])
        self.assertEqual(result['registered_cohort_size'],3)

    def test_captured_outcome_cannot_supply_its_own_independent_truth(self):
        row=self.bundle['opportunities'][0]
        row['truth_capture_event_refs']=row['capture_event_refs']=['same-capture']
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertIn('SAME_CAPTURE_USED_AS_TRUTH',result['blockers'])
        self.assertIsNone(result['observed_sensitivity'])
        self.assertEqual(result['n'],2)

    def test_detector_ancestry_cannot_be_laundered_as_truth(self):
        truth=self.bundle['sources'][0]
        truth.update(source_kind='DERIVED',parents=['detector'])
        result=self.call()
        self.assertEqual(result['execution_status'],'DATA_BLOCKED')
        self.assertIn('COHORT_SELECTED_FROM_DETECTOR_OUTCOMES',result['blockers'])
        self.assertIsNone(result['observed_sensitivity'])

    def test_gpx_passage_is_neither_positive_truth_nor_negative_control(self):
        for row in self.bundle['opportunities']:row['truth_method']='GPX_PASSAGE'
        self.protocol['truth_methods']=['GPX_PASSAGE']
        publish(self.bundle,self.protocol)
        self.assertEqual(self.call()['execution_status'],'DATA_BLOCKED')

    def test_repeat_site_night_and_removal_do_not_gain_iid_beta_qualification(self):
        first,_,last=self.bundle['opportunities']
        for key in ('start_time','end_time','detection_time','cluster_id'):last[key]=first[key]
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertIn('REPEATED_SITE_NIGHT_NOT_INDEPENDENT',result['blockers'])
        self.assertEqual(result['n'],1)
        self.bundle,self.protocol=fixture()
        self.bundle['opportunities'][0]['depletion_status']='REMOVAL'
        publish(self.bundle,self.protocol)
        self.assertIn('REMOVAL_OR_DEPLETION_NOT_SUPPORTED',self.call()['blockers'])

    def test_observer_mode_and_source_scope_must_agree(self):
        self.bundle['opportunities'][0]['observer_id']='another-observer'
        # Actual source has the original observer, so this is contradictory.
        self.assertEqual(self.call()['execution_status'],'FAIL')
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertIn('OBSERVER_MODE_OR_EFFORT_OUTSIDE_PROTOCOL',result['blockers'])

    def test_exact_original_utf8_size_and_hash_are_not_canonical_json_hashes(self):
        self.bundle['sources'][0]['raw_json_utf8']+=' '
        self.assertEqual(self.call()['execution_status'],'FAIL')
        self.bundle,self.protocol=fixture()
        self.bundle['sources'][0]['ref']['size_bytes']+=1
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_wrong_truth_time_and_future_readiness_fail_closed(self):
        self.bundle['opportunities'][0]['start_time']='2026-10-20T20:00:00+09:00'
        self.assertEqual(self.call()['execution_status'],'FAIL')
        self.bundle,self.protocol=fixture()
        self.bundle['sources'][0]['readiness']['audited_at']=self.protocol['assessment_as_of']
        self.bundle['sources'][0]['usable_at']=self.protocol['assessment_as_of']
        self.assertEqual(self.call()['execution_status'],'DATA_BLOCKED')

    def test_duplicate_opportunity_or_json_key_is_invalid(self):
        self.bundle['opportunities'].append(copy.deepcopy(self.bundle['opportunities'][0]))
        self.assertEqual(self.call()['execution_status'],'FAIL')
        self.bundle,self.protocol=fixture()
        raw='{"schema_version":"x","schema_version":"y"}'
        node=self.bundle['sources'][0];node['raw_json_utf8']=raw
        node['ref'].update(sha256=hashlib.sha256(raw.encode()).hexdigest(),size_bytes=len(raw.encode()))
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_custom_metaclass_and_deepcopy_never_execute(self):
        calls=[]
        class Meta(type):
            def __eq__(cls,other):calls.append('eq');return False
            __hash__=type.__hash__
        class Evil(metaclass=Meta):
            def __deepcopy__(self,memo):calls.append('copy');return self
        self.bundle['opportunities']=Evil()
        self.assertEqual(self.call()['execution_status'],'FAIL')
        self.assertEqual(calls,[])

    def test_required_numerics_and_preregistered_prior_cannot_be_invented(self):
        for value in (None,[],[True]):
            self.protocol['quantile_probabilities']=value
            self.assertNotEqual(self.call()['execution_status'],'COMPUTED')
        self.bundle,self.protocol=fixture()
        self.protocol['prior']['alpha']=2
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_ppf_failure_keeps_valid_empirical_estimate_without_interval_fallback(self):
        from scipy.stats import beta
        with patch.object(beta,'ppf',return_value=float('nan')):
            result=self.call()
        self.assertEqual(result['execution_status'],'PARTIAL')
        self.assertAlmostEqual(result['observed_sensitivity'],2/3)
        self.assertIsNone(result['posterior_quantiles'])
        self.assertEqual(result['numerical_status'],'NUMERICAL_NONCONVERGENCE')

    def test_cdf_inverse_failure_and_tail_capacity_are_explicit(self):
        from scipy.stats import beta
        with patch.object(beta,'cdf',return_value=.123456):
            result=self.call()
        self.assertEqual(result['numerical_status'],'NUMERICAL_NONCONVERGENCE')
        self.protocol['quantile_probabilities']=[1e-30,.5]
        result=self.call()
        self.assertEqual(result['numerical_status'],'NUMERICAL_CAPACITY_EXCEEDED')
        self.assertIsNone(result['posterior_quantiles'])

    def test_missing_or_wrong_analysis_runtime_never_silently_switches_backend(self):
        import importlib.metadata
        actual=importlib.metadata.version
        def version(name):return '0.0.0' if name=='scipy' else actual(name)
        with patch.object(importlib.metadata,'version',side_effect=version):
            result=self.call()
        self.assertEqual(result['numerical_status'],'RUNTIME_BINDING_ERROR')
        self.assertIsNone(result['posterior_quantiles'])

    def test_deadline_caps_and_boolean_budget_are_structured(self):
        for value in (True,0,10**1000,math.inf):
            self.assertEqual(self.call(budget_seconds=value)['execution_status'],'FAIL')
        self.assertEqual(self.call(budget_seconds=1e-12)['execution_status'],'RUNTIME_BLOCKED')
        self.protocol['capacities']['max_opportunities']=2
        self.assertEqual(self.call()['execution_status'],'RUNTIME_BLOCKED')

    def test_receipt_binds_input_policy_and_actual_source_bytes(self):
        result=self.call()
        self.assertEqual(result['input_digests'],dict(bundle=digest(self.bundle),protocol=digest(self.protocol)))
        self.assertEqual(result['receipt_sha256'],digest({k:v for k,v in result.items() if k!='receipt_sha256'}))
        self.assertEqual(result['source_sha256']['truth'],self.bundle['sources'][0]['ref']['sha256'])

    def test_contradictory_truth_record_in_another_supplied_source_is_not_ignored(self):
        body=json.loads(self.bundle['sources'][0]['raw_json_utf8'])
        body['records'][0]['truth_status']='KNOWN_NEGATIVE'
        self.bundle['sources'].append(source('contradiction','TRUTH',body))
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_invalid_unused_detector_record_cannot_hide_behind_registered_subset(self):
        body=json.loads(self.bundle['sources'][1]['raw_json_utf8'])
        extra=copy.deepcopy(body['records'][0]);extra.update(opportunity_id='unused',detected=1)
        body['records'].append(extra)
        self.bundle['sources'][1]=source('detector','DETECTION',body)
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_unknown_snapshot_before_trial_end_does_not_assert_a_missed_detection(self):
        row=self.bundle['opportunities'][1]
        row.update(detected=None,detection_time=None,outcome_available_at='2026-10-21T19:05:00+09:00')
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual(result['execution_status'],'PARTIAL')
        self.assertEqual((result['n'],result['s'],result['unknown_results']),(2,2,1))

    def test_preregistered_group_support_does_not_admit_full_sensitivity(self):
        self.protocol['minimum_group_support']=4
        result=self.call()
        self.assertEqual(result['execution_status'],'PARTIAL')
        self.assertIsNone(result['observed_sensitivity'])
        self.assertAlmostEqual(result['known_subset_sensitivity'],2/3)
        self.assertIn('PREREGISTERED_GROUP_SUPPORT_NOT_MET',result['blockers'])

    def test_known_negative_control_is_separate_and_requires_its_own_support(self):
        self.bundle['opportunities'][2]['truth_status']='KNOWN_NEGATIVE'
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual((result['n'],result['s'],result['known_negative_n']),(2,1,1))
        self.assertEqual(result['false_positive_rate'],1)
        self.protocol['minimum_group_support']=2
        result=self.call()
        self.assertIsNone(result['false_positive_rate'])
        self.assertAlmostEqual(result['observed_sensitivity'],.5)

    def test_broken_fixed_runtime_is_structured_binding_error(self):
        original=self.api.importlib.import_module
        def imported(name,*args,**kwargs):
            return object() if name=='scipy' else original(name,*args,**kwargs)
        escaped=None
        with patch.object(self.api.importlib,'import_module',side_effect=imported):
            try:result=self.call()
            except Exception as exc:escaped=type(exc).__name__
        self.assertIsNone(escaped)
        self.assertEqual(result['numerical_status'],'RUNTIME_BINDING_ERROR')
        self.assertAlmostEqual(result['observed_sensitivity'],2/3)

    def test_declared_string_capacity_is_checked_even_if_source_missing(self):
        self.protocol['capacities']['max_string_bytes']=8
        self.bundle['sources']=[]
        self.assertEqual(self.call()['execution_status'],'RUNTIME_BLOCKED')

    def test_uniform_kernel_and_beta_one_two_match_independent_cdf_oracles(self):
        # Kernel-only prior check; the public n=0 path remains DATA_BLOCKED.
        result=self.api._posterior(0,0,self.protocol,self.api._Budget(30))
        for point in result['posterior_quantiles']:
            self.assertAlmostEqual(point['value'],point['probability'])
        self.bundle['opportunities']=self.bundle['opportunities'][1:2]
        self.protocol['quantile_probabilities']=[.25,.5,.75]
        publish(self.bundle,self.protocol)
        result=self.call()
        for actual,expected in zip(result['posterior_quantiles'],(.1339745962155614,.2928932188134524,.5)):
            self.assertAlmostEqual(actual['value'],expected)

    def test_shape_capacity_retains_empirical_and_nonmonotone_ppf_never_succeeds(self):
        self.protocol['capacities']['max_shape']=2
        result=self.call()
        self.assertEqual(result['numerical_status'],'NUMERICAL_CAPACITY_EXCEEDED')
        self.assertAlmostEqual(result['observed_sensitivity'],2/3)
        self.bundle,self.protocol=fixture()
        self.protocol['quantile_probabilities']=[.4,.6]
        self.protocol['numerics']=dict(cdf_absolute_tolerance=.9,log_tail_tolerance=.9)
        from scipy.stats import beta
        with patch.object(beta,'ppf',side_effect=[.6,.55]):
            result=self.call()
        self.assertEqual(result['numerical_status'],'NUMERICAL_NONCONVERGENCE')
        self.assertIsNone(result['posterior_quantiles'])

    def test_no_source_or_output_write_process_or_network_side_effect(self):
        self.call()  # Warm only the fixed installed analysis runtime.
        import socket
        import subprocess
        original=Path.open
        def readonly(path,mode='r',*args,**kwargs):
            if any(char in mode for char in 'wax+'):raise AssertionError('unexpected file write')
            return original(path,mode,*args,**kwargs)
        with (patch.object(Path,'open',new=readonly),
              patch.object(socket.socket,'connect',side_effect=AssertionError('network')),
              patch.object(subprocess,'run',side_effect=AssertionError('process'))):
            self.assertEqual(self.call()['execution_status'],'COMPUTED')

    def test_unavailable_bundle_does_not_invent_zero_negative_controls(self):
        result=self.api.evaluate_detection_opportunities(None,protocol=self.protocol)
        self.assertEqual(result['execution_status'],'DATA_BLOCKED')
        self.assertIsNone(result['n'])
        self.assertIsNone(result['known_negative_n'])

    def test_overlapping_site_trials_do_not_evade_repeat_guard_across_night_boundary(self):
        first=self.bundle['opportunities'][0]
        first['end_time']='2026-10-21T20:00:00+09:00'
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual(result['n'],1)
        self.assertIsNone(result['observed_sensitivity'])
        self.assertIn('OVERLAPPING_SITE_OPPORTUNITIES_NOT_INDEPENDENT',result['blockers'])

    def test_aware_offset_equivalence_is_not_a_source_contradiction(self):
        for row in self.bundle['opportunities']:
            for key in ('start_time','end_time','truth_available_at','detection_time','outcome_available_at'):
                if row[key] is not None:
                    row[key]=datetime.fromisoformat(row[key]).astimezone(timezone.utc).isoformat()
        result=self.call()  # Original source bytes still use +09:00.
        self.assertEqual(result['execution_status'],'COMPUTED')
        self.assertEqual((result['n'],result['s']),(3,2))

    def test_cyclic_or_missing_parent_readiness_graph_is_rejected(self):
        for parents in (['cohort'],['absent']):
            self.bundle,self.protocol=fixture()
            self.bundle['sources'][0].update(source_kind='DERIVED',parents=parents)
            result=self.call()
            self.assertEqual(result['execution_status'],'FAIL')
            self.assertIsNone(result['observed_sensitivity'])

    def test_different_names_and_independence_flags_do_not_replace_observational_parents(self):
        support=source('shared-declaration','SUPPORT',dict(schema_version='habu-detection-source-v1',
            kind='SUPPORT',details={'independent':True}))
        for node in self.bundle['sources'][:2]:
            node.update(source_kind='DERIVED',parents=[support['id']])
        self.bundle['sources'].append(support)
        result=self.call()
        self.assertEqual(result['execution_status'],'DATA_BLOCKED')
        self.assertEqual(result['n'],0)
        self.assertIn('INDEPENDENT_OBSERVATIONAL_CHANNELS_NOT_ESTABLISHED',result['blockers'])

    def test_custom_objects_at_all_public_boundaries_run_no_callbacks(self):
        calls=[]
        class Meta(type):
            def __eq__(cls,other):calls.append('eq');raise AssertionError('metaclass equality')
            __hash__=type.__hash__
        class Evil(metaclass=Meta):
            def __deepcopy__(self,memo):calls.append('copy');raise AssertionError('deepcopy')
            def __iter__(self):calls.append('iter');raise AssertionError('iteration')
        for target in ('bundle','protocol','source','row','quantile','budget'):
            with self.subTest(target=target):
                bundle,protocol=fixture();seconds=30
                if target=='bundle':bundle=Evil()
                elif target=='protocol':protocol=Evil()
                elif target=='source':bundle['sources'][0]=Evil()
                elif target=='row':bundle['opportunities'][0]=Evil()
                elif target=='quantile':protocol['quantile_probabilities'][0]=Evil()
                else:seconds=Evil()
                result=self.api.evaluate_detection_opportunities(bundle,protocol=protocol,budget_seconds=seconds)
                self.assertEqual(result['execution_status'],'FAIL')
        self.assertEqual(calls,[])


    def test_missing_source_nodes_are_data_blocked(self):
        self.bundle['sources']=[]
        result=self.call()
        self.assertEqual(result['execution_status'],'DATA_BLOCKED')
        self.assertEqual(result['reason_code'],'SOURCE_NODES_NOT_SUPPLIED')
        self.assertIsNone(result['n'])

    def test_shared_readiness_depth_limit_retains_capacity_status(self):
        for count,status in ((32,'COMPUTED'),(33,'RUNTIME_BLOCKED')):
            self.bundle,self.protocol=fixture()
            self.protocol['capacities']['max_sources']=100
            for i in range(count):
                self.bundle['sources'].append(source('support-'+str(i),'SUPPORT',
                    dict(schema_version='habu-detection-source-v1',kind='SUPPORT',details={}),
                    parents=[] if not i else ['support-'+str(i-1)]))
            result=self.call()
            self.assertEqual(result['execution_status'],status)
            if status=='RUNTIME_BLOCKED':
                self.assertEqual(result['reason_code'],'SOURCE_GRAPH_CAPACITY_EXCEEDED')
                self.assertIsNone(result['n'])

    def test_cross_night_trial_is_not_a_single_night_independent_opportunity(self):
        first,second=self.bundle['opportunities'][:2]
        first.update(start_time='2026-10-21T06:55:00+09:00',
                     end_time='2026-10-21T07:05:00+09:00',
                     detection_time='2026-10-21T06:57:00+09:00')
        second.update(start_time='2026-10-21T07:10:00+09:00',
                      end_time='2026-10-21T07:20:00+09:00')
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual(result['n'],2)
        self.assertIsNone(result['observed_sensitivity'])
        self.assertIn('CROSS_NIGHT_OPPORTUNITY_UNSUPPORTED',result['blockers'])

    def test_half_open_trials_can_touch_at_the07_night_boundary(self):
        first,second=self.bundle['opportunities'][:2]
        first.update(start_time='2026-10-21T06:50:00+09:00',
                     end_time='2026-10-21T07:00:00+09:00',
                     detection_time='2026-10-21T06:57:00+09:00')
        second.update(start_time='2026-10-21T07:00:00+09:00',
                      end_time='2026-10-21T07:10:00+09:00')
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual(result['execution_status'],'COMPUTED')
        self.assertEqual((result['n'],result['s']),(3,2))

    def test_detection_at_exclusive_trial_end_is_rejected(self):
        row=self.bundle['opportunities'][0]
        row['detection_time']=row['end_time']
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual(result['execution_status'],'FAIL')
        self.assertIsNone(result['observed_sensitivity'])

    def test_declared_time_effort_cannot_exceed_opportunity_duration(self):
        for unit,value in (('seconds',600),('minutes',10),('hours',1)):
            self.bundle,self.protocol=fixture()
            self.protocol['effort_policy'].update(unit=unit,max_value=1000)
            for row in self.bundle['opportunities']:row['effort'].update(unit=unit,value=value)
            first=self.bundle['opportunities'][0]
            first.update(end_time='2026-10-20T19:01:00+09:00',
                         detection_time='2026-10-20T19:00:30+09:00')
            publish(self.bundle,self.protocol)
            result=self.call()
            self.assertIsNone(result['observed_sensitivity'])
            self.assertIn('TIME_EFFORT_EXCEEDS_OPPORTUNITY_DURATION',result['blockers'])

    def test_unknown_effort_units_are_not_guessed_time_conversions(self):
        self.protocol['effort_policy']['unit']='person_minutes'
        for row in self.bundle['opportunities']:row['effort']['unit']='person_minutes'
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual(result['execution_status'],'DATA_BLOCKED')
        self.assertEqual(result['reason_code'],'SUPPORTED_TIME_EFFORT_POLICY_REQUIRED')
        self.assertIsNone(result['n'])

    def test_time_effort_equal_to_interval_is_valid(self):
        self.protocol['effort_policy']['unit']='seconds'
        for row in self.bundle['opportunities']:row['effort'].update(unit='seconds',value=60)
        self.bundle['opportunities'][0].update(end_time='2026-10-20T19:01:00+09:00',
            detection_time='2026-10-20T19:00:30+09:00')
        publish(self.bundle,self.protocol)
        result=self.call()
        self.assertEqual(result['execution_status'],'COMPUTED')
        self.assertEqual((result['n'],result['s']),(3,2))


if __name__=='__main__':unittest.main()
