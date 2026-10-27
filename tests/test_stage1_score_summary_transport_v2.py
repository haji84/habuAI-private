"""Closed synthetic summary-v2 transport; no source/fit/production authority."""
from pathlib import Path
import importlib.util
import copy
import inspect
import ast
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
import prospective_inputs as pi
import g0_forecast_contract as g0
import g0_full_universe_score_summary_v2 as producer
from models import hba1_feature_candidate as a1,hba2_feature_candidate as a2
from master_contracts import canonical_bytes,digest
from test_g0_forecast_contract import NIGHT,NOW,base_ref
from test_g0_full_universe_score_summary_v2 import SummaryV2Fixture
from test_stage1_source_adapter import SourceFixture

def projection(value,forecast):
    node=next(n for n in forecast.manifest['source_nodes']if n['id']==forecast.manifest['domain_id'])
    stable=('manifest_ref','manifest_canonical_sha256','config_ref','config_sha256','cycle_ref','cycle_canonical_sha256',
        'code_sha256_by_path','code_map_sha256','policy_ref','policy_canonical_sha256')
    result=dict(schema_version='habu-g0-score-summary-projection-v2',purpose='DEVELOPMENT_EVALUATION_ONLY',
        summary_manifest_ref=value['source_manifest_ref'],summary_manifest_canonical_sha256=value['source_manifest_canonical_sha256'])
    for k in('operational_night','fit_cutoff','forecast_cutoff'):result[k]=value[k]
    result.update(forecast_manifest_ref=value['forecast_receipt']['manifest_ref'],canonical_joined_rows_sha256=value['forecast_receipt']['canonical_joined_rows_sha256'],
        domain_ref=node['ref'],horizon=forecast.manifest['horizon'],candidate_ids=value['candidate_ids'],candidate_config_source={k:value['candidate_config_source_receipt'][k]for k in stable})
    for k in('candidate_config_sha256','feature_definition_sha256','fit_lineage','training_selection_sha256','model_bindings','full_counts','model_summaries'):result[k]=value[k]
    return result

def targets(root,f):
    e=SourceFixture(SimpleNamespace(root=root,forecast=f.forecast,request=dict(forecast_as_of=NOW.isoformat(),feature_definition_sha256=f.profile['feature_definition_sha256']),publish=lambda:None))
    e.scope['horizon_end']=e.coverage['horizon_end']=f.forecast.valid['end']
    for row,count in zip(e.captures,(1,2)):row['event_count']=str(count)
    e.individuals=[]
    for event in e.captures:
        for index in range(1,int(event['event_count'])+1):
            e.individuals.append(dict(individual_id=event['event_id']+'-'+str(index),event_id=event['event_id'],individual_index=str(index),operational_date=NIGHT,event_time_local=event['event_time_local']))
    e.coverage['individual_ids']=[r['individual_id']for r in e.individuals]
    e.publish()
    actual=producer.score_g0_forecast_summary_v2(root,f.ref,NIGHT,NOW,expected_feature_definition_sha256=f.profile['feature_definition_sha256'],expected_candidate_config_sha256=digest(f.source.config),context=pi.ProspectiveReadContext(300,2*1024**3))
    p=projection(actual,f.forecast)
    e.manifest.update(schema_version='habu-stage1-summary-source-contract-v2',candidate_config_sha256=digest(f.source.config),feature_definition_sha256=f.profile['feature_definition_sha256'],score_summary_projection_sha256=digest(p))
    e.manifest_only();return e,p

class PublicSeamTests(unittest.TestCase):
    def test_new_explicit_public_entry_is_available(self):
        name='evaluation.stage1_score_summary_transport_v2'
        self.assertIsNotNone(importlib.util.find_spec(name),'Missing explicit fixed U/A1/A2 source bridge')
        module=__import__(name,fromlist=['evaluate_stage1_summary_sources_v2'])
        self.assertTrue(callable(module.evaluate_stage1_summary_sources_v2))
    def test_legacy_default_body_AST_retains_exact_native950_identity(self):
        from evaluation import stage1_source_adapter as old
        fn=next(n for n in ast.parse(inspect.getsource(old)).body if isinstance(n,ast.FunctionDef)and n.name=='_evaluate')
        self.assertEqual(fn.args.kwonlyargs[-1].arg,'_summary_v2');fn.args.kwonlyargs.pop();fn.args.kw_defaults.pop()
        branch=next(i for i,n in enumerate(fn.body)if isinstance(n,ast.If)and ast.unparse(n.test)=='_summary_v2 is not None')
        fn.body.pop(branch)
        self.assertEqual(hashlib.sha256(ast.dump(fn,include_attributes=False).encode()).hexdigest(),'66dd7229f2765333c59811f53eee3b406bf7a2242cadbb5fbb7e3f61287a02cd')

class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=tempfile.TemporaryDirectory();cls.f=SummaryV2Fixture(Path(cls.base.name));cls.e,cls.p=targets(Path(cls.base.name),cls.f)
    @classmethod
    def tearDownClass(cls):cls.base.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'fixture';shutil.copytree(self.base.name,self.root)
        self.f=copy.deepcopy(self.__class__.f);self.f.root=self.root;self.f.forecast.root=self.root;self.f.source.root=self.root
        self.e=copy.deepcopy(self.__class__.e);self.e.root=self.root
        from evaluation import stage1_score_summary_transport_v2
        self.module=stage1_score_summary_transport_v2
    def call(self,context=None):
        with patch.object(a1,'fit_hba1',side_effect=AssertionError('API fit forbidden')),patch.object(a2,'_backend',side_effect=AssertionError('API backend forbidden')):
            return self.module.evaluate_stage1_summary_sources_v2(self.root,self.f.ref,self.e.ref,NIGHT,NOW,
                expected_feature_definition_sha256=self.f.profile['feature_definition_sha256'],expected_candidate_config_sha256=digest(self.f.source.config),context=context if context is not None else pi.ProspectiveReadContext(300,2*1024**3))
    def sealed(self,v,key='receipt_sha256'):self.assertEqual(v[key],digest({k:x for k,x in v.items()if k!=key}))
    def test_complete_two_loads_count2_outside_and_original_children(self):
        c=pi.ProspectiveReadContext(300,2*1024**3);old=(c.deadline,c.max_bytes,c.check)
        actual=self.module.source2.load_research_candidate_config_v2;children=[]
        def loading(*a,**kw):
            v=actual(*a,**kw);children.append(json.dumps(v['receipt'],ensure_ascii=False));return v
        with patch.object(self.module.source2,'load_research_candidate_config_v2',side_effect=loading)as load:
            v=self.call(c)
        self.assertEqual(load.call_count,2);self.assertEqual(len(v),27);self.assertEqual(len(v['phase_read_ledger']),13);self.assertEqual(len(v['source_receipt']),22)
        self.assertEqual(v['status'],'DIAGNOSTIC_ONLY');self.assertEqual(v['score_summary_projection'],self.p)
        self.assertEqual(v['stage1_result']['per_night'][0]['outside_universe_individuals'],2)
        for row in v['stage1_result']['pooled'].values():self.assertEqual((row['numerator'],row['denominator']),(1,3))
        self.assertEqual((c.deadline,c.max_bytes,c.check),old);self.assertEqual(c.bytes_read,v['actual_read_bytes'])
        self.sealed(v);self.sealed(v['stage1_result']);self.sealed(v['source_admission_receipt']);self.sealed(v['summary_execution_receipt'],'summary_sha256')
        self.assertTrue(all(x is False for x in v['authorities'].values()))
        self.assertEqual(json.dumps(v['source_admission_receipt'],ensure_ascii=False),children[0])
        self.assertEqual(json.dumps(v['summary_execution_receipt']['candidate_config_source_receipt'],ensure_ascii=False),children[1])
    def test_source2_valid_late_halts_before_poisoned_forecast(self):
        self.f.source.profile['readiness']['audited_at']=self.f.profile['fit_cutoff'];self.f.source.profile['usable_at']=self.f.profile['fit_cutoff'];self.f.source.profile_only()
        self.f.profile['candidate_config_manifest']=self.f.source.ref;self.f.publish()
        (self.root/'features/g0-contract.json').write_bytes(b'{}')
        actual=Path.open;opened=[]
        def opening(p,*a,**kw):
            if p.is_relative_to(self.root)and p.relative_to(self.root).as_posix().startswith(('features/','models/')):opened.append(str(p))
            return actual(p,*a,**kw)
        with patch.object(Path,'open',opening),self.assertRaises(self.module.source2.CandidateConfigSourceBlocked):self.call()
        self.assertEqual(opened,[])
    def test_prior_and_producer_entry_real_byte_preserve_content(self):
        a=self.call();root=self.root;fired=[]
        bound=base_ref(root,'config/one.bin',b'x')
        class Context(pi.ProspectiveReadContext):
            def check(c):
                super().check()
                if not fired and sys._getframe(1).f_code is producer._context.__code__:
                    fired.append(1);g0.G0ArtifactReader(root,c).read(bound,parse=False)
        c=Context(300,2*1024**3);b=self.call(c);p=b['phase_read_ledger'];child=b['summary_execution_receipt']
        self.assertEqual(fired,[1]);self.assertEqual(a['score_summary_projection'],b['score_summary_projection'])
        self.assertNotEqual(a['summary_execution_receipt_sha256'],b['summary_execution_receipt_sha256'])
        self.assertEqual(child['actual_read_bytes']-child['summary_read_bytes'],p['after_post_admission_metadata']+1)
    def test_unknown_missing_and_malformed_supplied_sources(self):
        self.e.coverage['declaration']='UNKNOWN';self.e.publish();v=self.call()
        self.assertEqual(v['status'],'NEED_MORE_DATA');self.assertEqual(v['stage1_result']['pooled'],{})
        self.e.individuals[-1]['individual_index']='1';self.e.publish()
        with self.assertRaises(ValueError):self.call()
    def test_missing_scope_still_checks_known_horizon(self):
        self.e.manifest['scope_id']=None;self.e.nodes.pop('scope');self.e.coverage['horizon_end']=NIGHT+'T19:20:00+09:00'
        self.e.nodes['coverage']['ref']=base_ref(self.root,'evidence/stage1/coverage.json',canonical_bytes(self.e.coverage));self.e.manifest_only()
        with self.assertRaisesRegex(ValueError,'horizon'):self.call()
    def test_whole_cell_scope_rejects_before_outcomes(self):
        self.e.scope['scope']['bbox_utm'][0]=400001;self.e.coverage['scope_sha256']=digest(self.e.scope['scope']);self.e.publish()
        actual=Path.open
        def opening(p,*a,**kw):
            if p.name in('captures.csv','individuals.csv','coverage.json'):raise AssertionError('outcomes before wholecell scope')
            return actual(p,*a,**kw)
        with patch.object(Path,'open',opening),self.assertRaisesRegex(ValueError,'whole forecast cell'):self.call()
    def test_closed_slot_rejects_incomplete_subclass_and_callbacks(self):
        from evaluation import stage1_source_adapter as sa
        ctx=pi.ProspectiveReadContext(300,2*1024**3)
        class Child(self.module._State):pass
        for obj in(object(),self.module._State.__new__(self.module._State),Child.__new__(Child)):
            with self.subTest(type=type(obj).__name__),self.assertRaises(ValueError):sa._evaluate(self.root,self.e.ref,None,None,context=ctx,_summary_v2=obj)
        with self.assertRaises(AttributeError):self.module._State.__new__(self.module._State)._add=lambda:None
        with self.assertRaises(ValueError):self.module._State(None,None,None,None,None,None,None,None,None,None,_owner=self.module._OWNED)
    def test_exact_first_parent_object_through_csv_and_final_seals(self):
        from evaluation import stage1_source_adapter as sa
        classes=(OverflowError,UnicodeError,StopIteration,KeyboardInterrupt,pi.InputCapacityError)
        class Falsey(OverflowError):
            def __bool__(self):return False
            def __eq__(self,other):raise AssertionError('no equality')
        for kind in(*classes,Falsey):
            marker=kind('parent marker')
            class Context(pi.ProspectiveReadContext):
                def check(c):
                    super().check()
                    if sys._getframe(2).f_code is sa._csv.__code__:raise marker
            with self.subTest(kind=kind.__name__),self.assertRaises(BaseException)as caught:self.call(Context(300,2*1024**3))
            self.assertIs(caught.exception,marker)
    def test_global_prior_cap_and_final_membership_mutation(self):
        c=pi.ProspectiveReadContext(300,1)
        with self.assertRaises(pi.InputCapacityError):self.call(c)
        self.assertGreater(c.bytes_read,0)
        actual=self.module._rescan
        def changed(*a):
            (self.root/'src/extra.py').write_text('pass\n');return actual(*a)
        with patch.object(self.module,'_rescan',changed),self.assertRaises(ValueError):self.call()
    def test_whole_NMD_opens_no_outcome_but_missing_top_rejects(self):
        self.f.profile['fit_lineage']=None;self.f.profile['models'][2]['artifact']=None;self.f.publish()
        actual=Path.open;opened=[]
        def opening(p,*a,**kw):
            if p.name in('manifest.json','captures.csv','individuals.csv','coverage.json'):opened.append(str(p))
            return actual(p,*a,**kw)
        with patch.object(Path,'open',opening):v=self.call()
        self.assertEqual(v['status'],'NEED_MORE_DATA');self.assertEqual(opened,[])
        for k in('score_summary_projection','stage1_result','source_receipt','source_summary'):self.assertIsNone(v[k])
        self.assertEqual(v['summary_execution_receipt']['model_summaries'],[])
        (self.root/self.e.ref['path']).unlink()
        with self.assertRaisesRegex(ValueError,'manifest is missing'):self.call()
    def test_missing_role_and_explicit_complete_empty_remain_distinct(self):
        path=self.root/self.e.nodes['coverage']['ref']['path'];raw=path.read_bytes();path.unlink()
        v=self.call();self.assertEqual(v['status'],'NEED_MORE_DATA');self.assertIn('FILE:coverage',v['source_receipt']['missing_inputs'])
        path.write_bytes(raw);self.e.captures=[];self.e.individuals=[]
        # Explicit headers are required even for empty supplied CSVs.
        cr=base_ref(self.root,'evidence/stage1/captures.csv',b'event_id,operational_date,event_time_local,event_type,event_count,utm_x_m,utm_y_m\n')
        ir=base_ref(self.root,'evidence/stage1/individuals.csv',b'individual_id,event_id,individual_index,operational_date,event_time_local\n')
        self.e.nodes['captures']['ref']=cr;self.e.nodes['individuals']['ref']=ir
        self.e.coverage.update(event_ids=[],individual_ids=[],captures_ref=cr,individuals_ref=ir)
        self.e.nodes['coverage']['ref']=base_ref(self.root,'evidence/stage1/coverage.json',canonical_bytes(self.e.coverage));self.e.manifest_only()
        v=self.call();self.assertEqual(v['stage1_result']['pooled']['uniform']['denominator'],0)
    def test_projection_poison_is_known_even_without_universe(self):
        p=copy.deepcopy(self.p);p['model_summaries'][2]['area_summaries'][0]['unit_count']-=3;p['model_summaries'][2]['area_summaries'][1]['unit_count']+=3
        with self.assertRaises(ValueError):self.module._pure(None,None,None,self.f.source.config,p,lambda:None)
    def test_two_load_drift_and_final_original_size_growth_reject(self):
        actual=self.module.source2.load_research_candidate_config_v2;calls=[]
        def changed(*a,**kw):
            result=actual(*a,**kw);calls.append(1)
            if len(calls)==1:
                p=self.root/'src/synthetic_feature.py';p.write_bytes(p.read_bytes()+b' ')
            return result
        with patch.object(self.module.source2,'load_research_candidate_config_v2',changed),self.assertRaises(ValueError):self.call()
        self.assertEqual(calls,[1])
    def test_final_seal_first_object_and_fully_sealed_cap(self):
        marker=OverflowError('finalseal');target=self.module._finish.__code__;hits=[]
        class Context(pi.ProspectiveReadContext):
            def check(c):
                super().check()
                if sys._getframe(2).f_code is target:hits.append(1);raise marker
        with self.assertRaises(BaseException)as caught:self.call(Context(300,2*1024**3))
        self.assertIs(caught.exception,marker);self.assertEqual(hits,[1])
        # The hash field itself must push a previously fitting body over cap.
        payload={'x':'x'};body=len(canonical_bytes(payload))
        with patch.object(self.module.pure,'MAX_JSON_BYTES',body+1),self.assertRaises(pi.InputCapacityError):
            self.module._finish(payload,lambda:None)
    def test_physical_byte_read_at_last_parent_check_cannot_escape_sealed_ledger(self):
        bound=base_ref(self.root,'config/final-one.bin',b'x');root=self.root;finished=[];fired=[]
        actual=self.module._finish
        def finish(value,check):
            result=actual(value,check)
            if value.get('schema_version')==self.module.VERSION:finished.append(1)
            return result
        class Context(pi.ProspectiveReadContext):
            def check(c):
                super().check()
                if finished and not fired:
                    fired.append(1);g0.G0ArtifactReader(root,c).read(bound,parse=False)
        with patch.object(self.module,'_finish',finish),self.assertRaisesRegex(ValueError,'ledger changed'):
            self.call(Context(300,2*1024**3))
        self.assertEqual(fired,[1])
    def test_actual_account_boundary_parent_object_is_not_pure_normalization(self):
        for cls in(self.module.pure.Stage1CapacityBlocked,self.module.pure.Stage1BudgetBlocked,UnicodeError,KeyboardInterrupt):
            marker=cls('actual caller account');charged=[]
            class Context(pi.ProspectiveReadContext):
                def account(c,n):
                    super().account(n);charged.append(n);raise marker
            with self.subTest(cls=cls.__name__),self.assertRaises(BaseException)as caught:self.call(Context(300,2*1024**3))
            self.assertIs(caught.exception,marker);self.assertTrue(charged)
    def test_reserved_alias_refs_reject_before_payload_and_wrong_version(self):
        actual=self.e.ref
        for path in('evidence/ORIGINAL/x.json','evidence/./x.json','evidence/x./m.json','evidence/x /m.json','evidence/X~1/m.json','evidence/a:b.json','evidence/\\x.json'):
            self.e.ref=dict(actual,path=path)
            with self.subTest(path=path),patch.object(Path,'open',side_effect=AssertionError('unsafe reference opened payload')),self.assertRaises(ValueError):self.call()
        self.e.ref=actual;self.e.manifest['schema_version']='habu-stage1-summary-source-contract-v1';self.e.manifest_only()
        with self.assertRaises(ValueError):self.call()

class GenuinePinnedNumericGate(unittest.TestCase):
    def test_genuine_pinned_synthetic_A2_complete_bridge(self):
        from importlib.metadata import version,PackageNotFoundError
        ready=True
        try:ready=all(version(k)==v for k,v in a2.PINS.items())
        except PackageNotFoundError:ready=False
        if not ready:
            if os.environ.get('GITHUB_ACTIONS','').lower()=='true':self.fail('Genuine pinned numeric Stage1-v2 gate cannot skip on CI')
            self.skipTest('Genuine pinned NumPy/SciPy/sklearn dependencies unavailable in this interpreter')
        from evaluation import stage1_score_summary_transport_v2 as module
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);f=SummaryV2Fixture(root,numeric=True);e,p=targets(root,f)
            c=pi.ProspectiveReadContext(300,2*1024**3)
            with patch.object(a1,'fit_hba1',side_effect=AssertionError('no fit in API')),patch.object(a2,'_backend',side_effect=AssertionError('no backend in API')):
                result=module.evaluate_stage1_summary_sources_v2(root,f.ref,e.ref,NIGHT,NOW,expected_feature_definition_sha256=f.profile['feature_definition_sha256'],expected_candidate_config_sha256=digest(f.source.config),context=c)
            self.assertEqual(result['status'],'DIAGNOSTIC_ONLY');self.assertEqual(result['score_summary_projection'],p)
            self.assertEqual(result['stage1_result']['candidate_lineage']['HB-A2']['model_sha256'],f.models['HB-A2']['model_sha256'])
            self.assertEqual(result['stage1_result']['pooled']['HB-A2']['denominator'],3)
            self.assertTrue(all(v is False for v in result['authorities'].values()))


if __name__=='__main__':unittest.main()
