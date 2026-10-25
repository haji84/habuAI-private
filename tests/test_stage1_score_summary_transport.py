"""Synthetic summary identity/denominator controls; never source qualification."""
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from master_contracts import canonical_bytes,digest
import prospective_inputs as pi
import g0_forecast_contract as g0
import g0_full_universe_score_summary as summary
from evaluation import full_ledger_stage1 as pure,stage1_source_adapter as source
from test_g0_forecast_contract import NIGHT,NOW,CUTOFF,base_ref
from test_g0_full_universe_score_summary import SummaryFixture
from test_stage1_source_adapter import SourceFixture

PROJECTION_FIELDS=('schema_version','purpose','summary_manifest_ref','summary_manifest_canonical_sha256',
    'operational_night','fit_cutoff','forecast_cutoff','forecast_manifest_ref','canonical_joined_rows_sha256',
    'domain_ref','horizon','candidate_ids','candidate_config_source','candidate_config_sha256',
    'feature_definition_sha256','fit_lineage','training_selection_sha256','model_bindings','full_counts','model_summaries')
CONFIG_FIELDS=('manifest_ref','manifest_canonical_sha256','config_ref','config_sha256','cycle_ref',
    'cycle_canonical_sha256','code_sha256_by_path','code_map_sha256','policy_ref','policy_canonical_sha256')

def independent_projection(value,forecast):
    """Test-side literal schema reconstruction, independent from transport code."""
    body=dict(schema_version='habu-g0-score-summary-projection-v1',purpose='DEVELOPMENT_EVALUATION_ONLY',
        summary_manifest_ref=value['source_manifest_ref'],summary_manifest_canonical_sha256=value['source_manifest_canonical_sha256'])
    for key in ('operational_night','fit_cutoff','forecast_cutoff'):
        body[key]=value[key]
    body.update(forecast_manifest_ref=value['forecast_receipt']['manifest_ref'],
        canonical_joined_rows_sha256=value['forecast_receipt']['canonical_joined_rows_sha256'],
        domain_ref=forecast.nodes[forecast.manifest['domain_id']]['ref'],horizon=forecast.manifest['horizon'])
    body['candidate_ids']=value['candidate_ids']
    body['candidate_config_source']={key:value['candidate_config_source_receipt'][key] for key in CONFIG_FIELDS}
    for key in ('candidate_config_sha256','feature_definition_sha256','fit_lineage','training_selection_sha256',
                'model_bindings','full_counts','model_summaries'):
        body[key]=value[key]
    assert tuple(body)==PROJECTION_FIELDS
    return copy.deepcopy(body)

class TransportFixture:
    def __init__(self,root,*,reverse=False):
        self.root=root;self.f=SummaryFixture(root,unequal=True)
        self.config=self.f.source.config
        if reverse:
            self.config['candidate_ids']=['uniform','HB-A1','HB-A0']
            self.f.source.publish()
            self.f.profile['candidate_config_manifest']=self.f.source.ref
            self.f.profile['models']=[self.f.profile['models'][i] for i in (0,2,1)]
            self.f.publish()
        parent=SimpleNamespace(root=root,forecast=self.f.forecast,
            request=dict(forecast_as_of=NOW.isoformat(),feature_definition_sha256=self.f.profile['feature_definition_sha256']),
            publish=lambda:None)
        self.events=SourceFixture(parent)
        self.events.scope['horizon_end']=self.f.forecast.valid['end']
        self.events.coverage['horizon_end']=self.f.forecast.valid['end']
        self.events.publish()
        self.expected=self.raw_summary()
        self.projection=independent_projection(self.expected,self.f.forecast)
        self.events.manifest.update(schema_version='habu-stage1-summary-source-contract-v1',
            candidate_config_sha256=digest(self.config),feature_definition_sha256=self.f.profile['feature_definition_sha256'],
            score_summary_projection_sha256=digest(self.projection))
        self.events.manifest_only()
    def raw_summary(self,**kw):
        return summary.score_g0_forecast_summary(self.root,self.f.ref,NIGHT,NOW,
            expected_feature_definition_sha256=self.f.profile['feature_definition_sha256'],
            expected_candidate_config_sha256=digest(self.config),budget_seconds=300,**kw)
    def call(self,context=None):
        return source.evaluate_stage1_summary_sources(self.root,self.f.ref,self.events.ref,NIGHT,NOW,
            expected_feature_definition_sha256=self.f.profile['feature_definition_sha256'],
            expected_candidate_config_sha256=digest(self.config),
            context=context or pi.ProspectiveReadContext(300,2*1024**3))
    def native_bundle(self):
        context=pi.ProspectiveReadContext(300,2*1024**3)
        forecast=g0.load_g0_forecast_rows(self.root,self.f.forecast.ref,NIGHT,NOW,
            expected_feature_definition_sha256=self.f.profile['feature_definition_sha256'],_read_context=context,
            budget_seconds=context.remaining_seconds)
        manifest=dict(self.events.manifest,schema_version='habu-stage1-source-contract-v2')
        manifest.pop('score_summary_projection_sha256')
        ref=base_ref(self.root,'evidence/stage1/native-manifest.json',canonical_bytes(manifest))
        return source.project_stage1_sources_v2(self.root,ref,forecast,self.f.prepared,
            candidate_config=self.config,expected_config_sha256=digest(self.config),
            feature_definition_sha256=self.f.profile['feature_definition_sha256'],context=context)
    def pure_inputs(self):
        bundle=self.native_bundle()
        candidates=[]
        for model in self.projection['model_summaries']:
            candidates.append({key:model[key] for key in ('candidate_id','score_semantics','model_sha256','recipe_sha256','score_stream_sha256')})
            candidates[-1]['scores']={NIGHT:{row['area_id']:row['mean_native_score'] for row in model['area_summaries']}}
        scores=dict(schema_version='habu-stage1-summary-scores-v1',universe_sha256=digest(bundle['universe']),
            candidate_config_sha256=digest(self.config),feature_definition_sha256=self.f.profile['feature_definition_sha256'],
            score_summary_projection=copy.deepcopy(self.projection),score_summary_projection_sha256=digest(self.projection),
            summary_execution_receipt_sha256=self.expected['summary_sha256'],candidates=candidates)
        return bundle,scores
    def pure_call(self,u,s,l,**kw):
        return pure.evaluate_full_ledger_stage1_summary_v1(u,s,l,candidate_config=self.config,
            expected_config_sha256=digest(self.config),feature_definition_sha256=self.f.profile['feature_definition_sha256'],
            budget_seconds=300,**kw)

class Stage1SummaryTransportTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(source,'evaluate_stage1_summary_sources',None)),
                        'Missing physical-source summary Stage1 entry')
        self.assertTrue(callable(getattr(pure,'evaluate_full_ledger_stage1_summary_v1',None)),
                        'Missing explicit pure summary identity entry')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.f=TransportFixture(self.root)
    def assert_sealed(self,value,field='receipt_sha256'):
        self.assertEqual(value[field],digest({k:v for k,v in value.items() if k!=field}))
    def forbid_outcomes(self):
        actual=Path.open
        def opening(path,*a,**kw):
            if path.name in ('captures.csv','individuals.csv','coverage.json'):
                raise AssertionError('Outcome opened before all summary/scope admission')
            return actual(path,*a,**kw)
        return patch.object(Path,'open',new=opening)

    def test_complete_source_keeps_count_two_and_outside_universe_miss(self):
        value=self.f.call()
        self.assertEqual(value['schema_version'],'habu-stage1-summary-source-result-v1')
        self.assertEqual(len(value),24);self.assertEqual(len(value['source_receipt']),22)
        self.assertEqual(value['status'],'DIAGNOSTIC_ONLY')
        self.assertEqual(value['source_summary'],dict(capture_events=2,individuals=3))
        result=value['stage1_result']
        self.assertEqual(result['per_night'][0]['outside_universe_individuals'],1)
        for row in result['pooled'].values():self.assertEqual((row['numerator'],row['denominator']),(2,3))
        self.assertEqual(value['score_summary_projection'],self.f.projection)
        self.assertEqual(value['score_summary_projection']['full_counts'],
            dict(cell_count=6,window_count=3,shard_count=6,unit_count=18,area_count=4))
        self.assertTrue(all(v is False for v in value['authorities'].values()))
        self.assert_sealed(value);self.assert_sealed(result)
        self.assert_sealed(value['summary_execution_receipt'],'summary_sha256')

    def test_pure_reuses_all_native_numeric_fields_without_prediction_impersonation(self):
        bundle,scores=self.f.pure_inputs()
        result=self.f.pure_call(bundle['universe'],scores,bundle['ledger'])
        for key in ('per_night','pooled','paired_uncertainty','unique_forecast_areas','unique_actual_areas'):
            self.assertEqual(result[key],bundle['stage1_result'][key])
        self.assertEqual(result['score_identity_kind'],'G0_SCORE_SUMMARY_PROJECTION_V1')
        for lineage in result['candidate_lineage'].values():
            self.assertEqual(set(lineage),{'score_semantics','model_sha256','recipe_sha256','score_stream_sha256'})
        self.assert_sealed(result)
        with self.assertRaises(ValueError):pure.evaluate_full_ledger_stage1_v2(bundle['universe'],scores,bundle['ledger'],
            candidate_config=self.f.config,expected_config_sha256=digest(self.f.config),
            feature_definition_sha256=self.f.f.profile['feature_definition_sha256'])

    def test_genuine_prior_read_changes_whole_receipt_but_not_all_twenty_content_fields(self):
        fresh=pi.ProspectiveReadContext(300,2*1024**3);a=self.f.call(fresh)
        prior=pi.ProspectiveReadContext(300,2*1024**3)
        ref=base_ref(self.root,'features/genuine-prior.json',b'{"genuine_prior_read":true}')
        g0.G0ArtifactReader(self.root,prior).read(ref,small=True)
        initial=prior.bytes_read;self.assertGreater(initial,0)
        b=self.f.call(prior)
        self.assertEqual(a['score_summary_projection'],b['score_summary_projection'])
        self.assertEqual(a['score_summary_projection_sha256'],b['score_summary_projection_sha256'])
        self.assertNotEqual(a['summary_execution_receipt_sha256'],b['summary_execution_receipt_sha256'])
        self.assertNotEqual(a['stage1_result']['receipt_sha256'],b['stage1_result']['receipt_sha256'])
        for value,context,charge in ((a,fresh,0),(b,prior,initial)):
            self.assertEqual(value['entry_initial_read_bytes'],charge)
            self.assertEqual(value['actual_read_bytes'],context.bytes_read)
            self.assertEqual(value['transport_read_bytes'],context.bytes_read-charge)
            self.assertEqual(value['source_receipt']['actual_read_bytes'],context.bytes_read)
            self.assert_sealed(value);self.assert_sealed(value['summary_execution_receipt'],'summary_sha256')
            self.assert_sealed(value['stage1_result'])
        for key in ('per_night','pooled','paired_uncertainty'):
            self.assertEqual(a['stage1_result'][key],b['stage1_result'][key])

    def test_old_whole_sha_or_old_pin_field_rejects_before_outcome_reads(self):
        original=copy.deepcopy(self.f.events.manifest)
        for mode in ('whole','old-field'):
            self.f.events.manifest=copy.deepcopy(original)
            if mode=='whole':self.f.events.manifest['score_summary_projection_sha256']=self.f.expected['summary_sha256']
            else:self.f.events.manifest['score_summary_sha256']=self.f.events.manifest.pop('score_summary_projection_sha256')
            self.f.events.manifest_only()
            with self.subTest(mode=mode),self.forbid_outcomes(),self.assertRaises(ValueError):self.f.call()

    def test_pure_rejects_fully_rehashed_stream_model_or_area_contradictions(self):
        bundle,original=self.f.pure_inputs()
        for mode in ('stream','model','count','mean','order','extra-prediction'):
            scores=copy.deepcopy(original);body=scores['score_summary_projection']
            if mode=='stream':body['model_summaries'][1]['score_stream_sha256']='e'*64
            if mode=='model':body['model_bindings'][1]['artifact']['model_sha256']='e'*64
            if mode=='count':body['model_summaries'][1]['area_summaries'][0]['unit_count']+=1
            if mode=='mean':body['model_summaries'][1]['area_summaries'][0]['mean_native_score']=0.99
            if mode=='order':body['model_summaries'].reverse()
            if mode=='extra-prediction':scores['candidates'][0]['prediction_sha256']='e'*64
            scores['score_summary_projection_sha256']=digest(body)
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                self.f.pure_call(bundle['universe'],scores,bundle['ledger'])

    def test_reserved_nested_forecast_ref_is_rejected_before_payload_open(self):
        f=self.f.f.forecast;node=f.nodes['roads'];old_path=node['ref']['path']
        path='features/ORIGINAL/forbidden.json';raw=canonical_bytes(f.objects[old_path])
        node['ref']=base_ref(self.root,path,raw);f.objects[path]=f.objects.pop(old_path);f.publish()
        self.f.f.profile['forecast_manifest']=f.ref;self.f.f.publish()
        actual=Path.open
        def opening(target,*a,**kw):
            if 'ORIGINAL' in target.parts:raise AssertionError('Protected forecast payload opened')
            return actual(target,*a,**kw)
        with patch.object(Path,'open',new=opening),self.assertRaises(ValueError):self.f.call()

    def test_full_cell_edge_is_proved_before_any_outcomes(self):
        events=self.f.events;events.scope['scope']['bbox_utm'][0]=400001
        events.coverage['scope_sha256']=digest(events.scope['scope']);events.publish()
        with self.forbid_outcomes(),self.assertRaises(ValueError):self.f.call()

    def test_unknown_and_missing_scope_keep_known_counts_but_no_metrics(self):
        self.f.events.coverage['declaration']='UNKNOWN';self.f.events.publish()
        value=self.f.call()
        self.assertEqual(value['status'],'NEED_MORE_DATA');self.assertEqual(value['stage1_result']['pooled'],{})
        self.assertIsNotNone(value['score_summary_projection'])
        self.f.events.manifest['scope_id']=None;self.f.events.nodes.pop('scope');self.f.events.manifest_only()
        value=self.f.call()
        self.assertEqual(value['stage1_result']['pooled'],{})
        self.assertEqual(value['source_summary'],dict(capture_events=2,individuals=3))

    def test_missing_lineage_retains_actual_nmd_summary_without_any_evaluation_reads(self):
        self.f.f.profile['fit_lineage']=None;self.f.f.publish()
        actual=Path.open
        def opening(path,*a,**kw):
            if 'stage1' in path.parts:raise AssertionError('NMD reached Stage1 source')
            return actual(path,*a,**kw)
        with patch.object(Path,'open',new=opening):value=self.f.call()
        self.assertEqual(value['status'],'NEED_MORE_DATA')
        self.assertEqual(value['summary_execution_receipt']['status'],'NEED_MORE_DATA')
        for key in ('score_summary_projection','score_summary_projection_sha256','stage1_result','source_receipt','source_summary'):
            self.assertIsNone(value[key])
        self.assert_sealed(value)

    def test_missing_input_never_hides_known_bad_csv_or_pure_projection(self):
        self.f.events.manifest['scope_id']=None;self.f.events.nodes.pop('scope')
        self.f.events.node('captures',b'event_id\r\ninvalid\r\n');self.f.events.manifest_only()
        with self.assertRaises(ValueError):self.f.call()
        # Config is supplied even when all three projection inputs are absent.
        original=self.f.config['candidate_ids'];self.f.config['candidate_ids']=['uniform','HB-A0','HB-A0']
        with self.assertRaises(ValueError):self.f.pure_call(None,None,None)
        self.f.config['candidate_ids']=original

    def test_source_preserves_exact_caller_exception_objects(self):
        for error in (FileNotFoundError,ValueError,OverflowError,TimeoutError,KeyboardInterrupt):
            for point in (1,150):
                marker=error('same caller exception');context=pi.ProspectiveReadContext(300,2*1024**3)
                original=context.check;calls=[0]
                def check():
                    calls[0]+=1
                    if calls[0]==point:raise marker
                    original()
                context.check=check
                with self.subTest(error=error.__name__,point=point):
                    try:self.f.call(context)
                    except BaseException as caught:self.assertIs(caught,marker)
                    else:self.fail('Caller cancellation was swallowed')

    def test_pure_preserves_same_caller_object_and_combined_metadata_integer_cap(self):
        bundle,scores=self.f.pure_inputs()
        for error in (FileNotFoundError,ValueError,OverflowError,TimeoutError,KeyboardInterrupt):
            marker=error('same pure callback')
            def stop():raise marker
            try:self.f.pure_call(bundle['universe'],scores,bundle['ledger'],check=stop)
            except BaseException as caught:self.assertIs(caught,marker)
            else:self.fail('Pure caller cancellation swallowed')
        scores['score_summary_projection']['full_counts']['unit_count']=1<<65
        with self.assertRaises(pure.Stage1CapacityBlocked):self.f.pure_call(bundle['universe'],scores,bundle['ledger'])

    def test_final_source_and_code_mutation_is_detected_after_real_pure_evaluation(self):
        actual=pure.evaluate_full_ledger_stage1_summary_v1
        target=self.root/'models/candidates/HB-A0.json'
        def evaluate(*a,**kw):
            result=actual(*a,**kw);target.write_bytes(target.read_bytes()+b' ');return result
        with patch.object(pure,'evaluate_full_ledger_stage1_summary_v1',side_effect=evaluate),self.assertRaises(ValueError):self.f.call()

    def test_cumulative_byte_limit_is_not_refilled_for_transport(self):
        complete=self.f.call();context=pi.ProspectiveReadContext(300,complete['actual_read_bytes']-1)
        with self.assertRaises(pi.InputCapacityError):self.f.call(context)
        self.assertGreater(context.bytes_read,context.max_bytes)

    def test_both_declared_orders_keep_exact_model_order_and_numeric_means(self):
        other=tempfile.TemporaryDirectory();self.addCleanup(other.cleanup)
        f=TransportFixture(Path(other.name),reverse=True);value=f.call()
        self.assertEqual(value['candidate_ids'],['uniform','HB-A1','HB-A0'])
        self.assertEqual([x['candidate_id'] for x in value['score_summary_projection']['model_summaries']],value['candidate_ids'])
        for row in value['stage1_result']['pooled'].values():self.assertEqual((row['numerator'],row['denominator']),(2,3))

    def test_b1_is_explicitly_blocked_before_stage1_manifest_or_outcomes(self):
        f=self.f.f;f.source.config.update(candidate_ids=['uniform','HB-A0','HB-B1'],hba1_recipe=None)
        f.source.publish();f.profile['candidate_config_manifest']=f.source.ref
        f.profile['models'][2]['candidate_id']='HB-B1';f.publish()
        actual=Path.open
        def opening(path,*a,**kw):
            if 'stage1' in path.parts:raise AssertionError('B1 opened evaluation input')
            return actual(path,*a,**kw)
        with patch.object(Path,'open',new=opening),self.assertRaisesRegex(g0.ForecastCapabilityError,'IMPLEMENTATION_BLOCKED'):
            self.f.call()

    def test_real_rebound_forecast_with_retained_pin_rejects_in_both_context_phases(self):
        old_pin=self.f.events.manifest['score_summary_projection_sha256'];f=self.f.f.forecast
        node=next(node for node in f.nodes.values() if node['source_kind']=='feature_values')
        values=f.objects[node['ref']['path']]['values'];key=next(iter(values));values[key]+=0.125;f.publish()
        self.f.f.profile['forecast_manifest']=f.ref;self.f.f.publish()
        changed=self.f.raw_summary()
        self.assertNotEqual(digest(independent_projection(changed,f)),old_pin)
        self.f.events.manifest.update(forecast_manifest_sha256=f.ref['sha256'],
            joined_universe_sha256=changed['forecast_receipt']['canonical_joined_rows_sha256'])
        self.f.events.manifest_only()
        for charged in (False,True):
            context=pi.ProspectiveReadContext(300,2*1024**3)
            if charged:
                ref=base_ref(self.root,'features/real-prior-charge.json',b'{"prior":1}')
                g0.G0ArtifactReader(self.root,context).read(ref,small=True)
            with self.subTest(charged=charged),self.forbid_outcomes(),self.assertRaises(ValueError):self.f.call(context)

    def test_pure_known_ledger_contradiction_survives_missing_universe(self):
        bundle,scores=self.f.pure_inputs();ledger=bundle['ledger']
        ledger['events'].append(copy.deepcopy(ledger['events'][0]))
        ledger['ledger_sha256']=digest({k:v for k,v in ledger.items() if k!='ledger_sha256'})
        with self.assertRaisesRegex(ValueError,'Duplicate canonical event'):self.f.pure_call(None,scores,ledger)

    def test_complete_explicit_zero_has_null_recall_and_no_invented_individuals(self):
        events=self.f.events
        events.coverage['captures_ref']=events.node('captures',b'event_id,operational_date,event_time_local,event_type,event_count,utm_x_m,utm_y_m\r\n')
        events.coverage['individuals_ref']=events.node('individuals',b'individual_id,event_id,individual_index,operational_date,event_time_local\r\n')
        events.coverage.update(event_ids=[],individual_ids=[])
        events.node('coverage',canonical_bytes(events.coverage));events.manifest_only()
        value=self.f.call()
        self.assertEqual(value['source_summary'],dict(capture_events=0,individuals=0))
        self.assertEqual(value['stage1_result']['blockers'],['NO_CONFIRMED_INDIVIDUALS'])
        for row in value['stage1_result']['pooled'].values():
            self.assertEqual(row,dict(numerator=0,denominator=0,recall=None))

    def test_missing_actual_csv_is_nmd_but_changed_present_bytes_are_invalid(self):
        path=self.root/self.f.events.nodes['individuals']['ref']['path'];path.unlink()
        value=self.f.call()
        self.assertEqual(value['status'],'NEED_MORE_DATA')
        self.assertIn('FILE:individuals',value['source_receipt']['missing_inputs'])
        self.assertEqual(value['stage1_result']['pooled'],{})
        path.write_bytes(b'changed actual supplied bytes')
        with self.assertRaises(ValueError):self.f.call()

    def test_final_complete_wrapper_cap_includes_own_hash_at_exact_boundary(self):
        complete=self.f.call();size=len(canonical_bytes(complete))
        with patch.object(pure,'MAX_JSON_BYTES',size):
            self.assertEqual(self.f.call(),complete)
        with patch.object(pure,'MAX_JSON_BYTES',size-1),self.assertRaises(pi.InputCapacityError):self.f.call()

    def test_combined_copy_cap_rejects_before_outcomes_and_preserves_summary_receipt(self):
        before=canonical_bytes(self.f.expected)
        bound=len(canonical_bytes([self.f.expected,self.f.projection]))-1
        with patch.object(pure,'MAX_JSON_BYTES',bound),self.forbid_outcomes(),self.assertRaises(pi.InputCapacityError):self.f.call()
        self.assertEqual(canonical_bytes(self.f.expected),before)

    def test_late_cancel_after_actual_wrapper_hash_keeps_same_object(self):
        context=pi.ProspectiveReadContext(300,2*1024**3);original_check=context.check;hashed=[False]
        marker=FileNotFoundError('late wrapper caller cancellation');actual=pure._finish
        def finish(value,check):
            result=actual(value,check)
            if value.get('schema_version')=='habu-stage1-summary-source-result-v1':hashed[0]=True
            return result
        def check():
            if hashed[0]:raise marker
            original_check()
        context.check=check
        with patch.object(pure,'_finish',side_effect=finish):
            try:self.f.call(context)
            except BaseException as caught:self.assertIs(caught,marker)
            else:self.fail('Late wrapper cancellation released a result')

    def test_supplied_duplicate_individual_or_pre_event_raw_readiness_is_invalid(self):
        events=self.f.events;original=copy.deepcopy(events.individuals)
        events.individuals.append(copy.deepcopy(events.individuals[0]));events.publish()
        with self.assertRaises(ValueError):self.f.call()
        events.individuals=original;events.publish()
        events.nodes['captures']['readiness']['source_received_at']='2026-10-14T17:00:00+09:00';events.manifest_only()
        with self.assertRaises(ValueError):self.f.call()

    def test_source_calls_complete_summary_once_and_never_collector(self):
        actual=summary.score_g0_forecast_summary;calls=[]
        def compute(*a,**kw):calls.append(kw['_read_context']);return actual(*a,**kw)
        context=pi.ProspectiveReadContext(300,2*1024**3)
        with patch.object(summary,'score_g0_forecast_summary',side_effect=compute),\
                patch.object(g0,'load_g0_forecast_rows',side_effect=AssertionError('Summary transport invoked collector')):
            value=self.f.call(context)
        self.assertEqual(value['score_summary_projection']['full_counts']['unit_count'],18)
        self.assertEqual(calls,[context]);self.assertEqual(value['actual_read_bytes'],context.bytes_read)

    def test_invalid_pure_horizon_is_valueerror_without_recasting_callbacks(self):
        bundle,scores=self.f.pure_inputs()
        scores['score_summary_projection']['horizon']['end']='9999-12-31T23:59:59+00:00'
        scores['score_summary_projection_sha256']=digest(scores['score_summary_projection'])
        with self.assertRaises(ValueError):self.f.pure_call(None,scores,bundle['ledger'])

    def test_summary_profile_purpose_namespace_is_checked_before_first_payload(self):
        self.f.f.ref=base_ref(self.root,'data/raw/must-not-open-summary.json',canonical_bytes(self.f.f.profile))
        actual=Path.open
        def opening(path,*a,**kw):
            if path.name=='must-not-open-summary.json':raise AssertionError('Wrong-purpose summary profile opened')
            return actual(path,*a,**kw)
        with patch.object(Path,'open',new=opening),self.assertRaises(ValueError):self.f.call()

    def test_summary_profile_small_cap_applies_before_metadata_preflight_read(self):
        raw=canonical_bytes(self.f.f.profile);raw+=b' '*(summary.MAX_PROFILE_BYTES+1-len(raw))
        self.f.f.ref=base_ref(self.root,'config/oversize-summary.json',raw)
        actual=Path.open
        def opening(path,*a,**kw):
            if path.name=='oversize-summary.json':raise AssertionError('Oversize summary profile opened')
            return actual(path,*a,**kw)
        with patch.object(Path,'open',new=opening),self.assertRaises(pi.InputCapacityError):self.f.call()

    def test_parent_bound_readiness_can_follow_own_metadata_stamps(self):
        f=self.f.f
        for binding in [f.profile['fit_lineage'],*(row['artifact'] for row in f.profile['models'])]:
            binding['readiness']=dict.fromkeys(pi.READINESS_FIELDS,'2026-09-30T23:00:00+09:00')
            binding['usable_at']=self.f.expected['candidate_config_source_receipt']['usable_at']
        f.publish();actual=self.f.raw_summary()
        self.assertEqual(actual['status'],'COMPLETE_DECLARED_SCORE_SUMMARY')
        self.f.events.manifest['score_summary_projection_sha256']=digest(independent_projection(actual,f.forecast))
        self.f.events.manifest_only()
        self.assertEqual(self.f.call()['status'],'DIAGNOSTIC_ONLY')

    def test_capacity_named_valueerror_from_caller_is_not_reclassified_as_internal_capacity(self):
        import research_model_adapter as models
        bundle,scores=self.f.pure_inputs();active=[False];actual=models._v2_config
        marker=models.ResearchCapacityBlocked('exact caller ValueError subclass')
        def validate(*a,**kw):
            active[0]=True
            try:return actual(*a,**kw)
            finally:active[0]=False
        def check():
            if active[0]:raise marker
        with patch.object(models,'_v2_config',side_effect=validate):
            try:self.f.pure_call(bundle['universe'],scores,bundle['ledger'],check=check)
            except BaseException as caught:self.assertIs(caught,marker)
            else:self.fail('Caller cancellation was swallowed')

    def test_common_universe_cannot_have_different_candidate_area_unit_counts(self):
        bundle,scores=self.f.pure_inputs()
        areas=scores['score_summary_projection']['model_summaries'][1]['area_summaries']
        self.assertEqual([row['unit_count'] for row in areas],[6,3,6,3])
        areas[0]['unit_count']-=3;areas[1]['unit_count']+=3
        scores['score_summary_projection_sha256']=digest(scores['score_summary_projection'])
        for universe in (bundle['universe'],None):
            with self.subTest(universe_absent=universe is None),self.assertRaises(ValueError):
                self.f.pure_call(universe,scores,bundle['ledger'])

    def test_missing_universe_does_not_hide_known_projection_ledger_time_contradictions(self):
        bundle,scores=self.f.pure_inputs()
        control=self.f.pure_call(None,scores,bundle['ledger'])
        self.assertEqual(control['status'],'NEED_MORE_DATA');self.assertEqual(control['pooled'],{})
        for mode in ('scope-horizon','actual-time'):
            ledger=copy.deepcopy(bundle['ledger'])
            if mode=='scope-horizon':ledger['complete_scopes'][0]['horizon_end']='2026-10-14T19:40:00+09:00'
            else:
                ledger['complete_scopes']=[];ledger['events'][0]['datetime']='2026-10-14T20:00:00+09:00'
            ledger['ledger_sha256']=digest({k:v for k,v in ledger.items() if k!='ledger_sha256'})
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.f.pure_call(None,scores,ledger)

if __name__=='__main__':unittest.main()
