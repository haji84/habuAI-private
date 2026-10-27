"""Synthetic engineering diagnostics; no qualified real TRAIN or authority."""
import importlib
import importlib.util
import inspect
import copy
import hashlib
import json
import math
import os
import shutil
import tempfile
import time
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import g0_forecast_contract as g0
import prospective_inputs as pi
from master_contracts import canonical_bytes,digest
from models import hba1_feature_candidate as a1,hba2_feature_candidate as a2
from test_g0_forecast_contract import SyntheticContract,base_ref,definition_hash,NIGHT,NOW,READY
from test_g0_full_universe_score_summary import SummaryFixture
from test_research_candidate_config_source_v2 import Source2Fixture


class SummaryV2Fixture:
    """Real synthetic A1 fit; explicitly hand-declared A2 interpreter model."""
    def __init__(self,root,*,numeric=False):
        old=SummaryFixture(root,unequal=True)
        self.root,self.forecast,self.selection=root,old.forecast,old.selection
        self.rows=old.rows
        self.source=Source2Fixture(root)
        self.source.config['feature_definition_sha256']=old.profile['feature_definition_sha256']
        self.source.profile['feature_definition_sha256']=old.profile['feature_definition_sha256']
        self.source.publish()
        candidates=old.prepared['candidates']
        self.models={'uniform':copy.deepcopy(candidates[0]['model']),'HB-A1':copy.deepcopy(candidates[2]['model'])}
        spec=self.source.config['hba2_recipe']
        assessment=a2.assess_hba2(self.selection,recipe=spec,expected_recipe_sha256=digest(spec),budget_seconds=300)
        if numeric:
            fit=a2.fit_hba2(self.selection,recipe=spec,expected_recipe_sha256=digest(spec),budget_seconds=300)
            if fit['status']!='DEVELOPMENT_FIT_ONLY':raise AssertionError(('Genuine pinned A2 fit unavailable',fit['status'],fit['blockers']))
            model=fit['model']
        else:
            runtime=dict(schema_version='habu-hba2-runtime-v1',status='PINNED_BACKEND_READY',
                expected_versions=dict(a2.PINS),observed_versions=dict(a2.PINS),auxiliary_versions={'joblib':'hand-declared','threadpoolctl':'hand-declared'},
                python_version='hand-declared',python_implementation='hand-declared',platform='hand-declared',
                input_dtype='IEEE754_BINARY32',requirements_sha256=copy.deepcopy(spec['requirements_sha256']),issues=[])
            model=dict(schema_version='habu-hba2-research-model-v1',status='DEVELOPMENT_RESEARCH_FIT_ONLY',candidate_id='HB-A2',
                target_semantics=a2.TARGET,recipe=copy.deepcopy(spec),recipe_sha256=digest(spec),feature_names=list(a2.FEATURES),
                input_dtype='IEEE754_BINARY32',initial_raw_score=0.0,learning_rate=.1,classes=[0,1],runtime=runtime,
                trees=[dict(nodes=[dict(left=-1,right=-1,feature=None,threshold=None,value=.25)]) for _ in range(32)],
                **{k:copy.deepcopy(assessment[k]) for k in a2.TRAIN_FIELDS},**a2._flags())
            model['model_sha256']=digest(model)
        self.models['HB-A2']=model
        self.lineage=copy.deepcopy(old.lineage)
        self.lineage['model_sha256_by_id']={k:v['model_sha256'] for k,v in self.models.items()}
        self.profile=copy.deepcopy(old.profile)
        self.profile.update(schema_version='habu-g0-full-universe-score-source-v2',candidate_config_manifest=self.source.ref,models=[])
        self.publish_models()

    def binding(self,ref,field,sha):
        return dict(ref=ref,**{field:sha},readiness=dict.fromkeys(pi.READINESS_FIELDS,READY),usable_at=READY)

    def publish_models(self):
        self.profile['models']=[dict(candidate_id=k,artifact=self.binding(base_ref(self.root,'models/candidates/'+k+'.json',canonical_bytes(v)),
            'model_sha256',v['model_sha256'])) for k,v in self.models.items()]
        self.publish_lineage()

    def publish_lineage(self):
        self.profile['fit_lineage']=self.binding(base_ref(self.root,'protocols/development/lineage.json',canonical_bytes(self.lineage)),
            'lineage_sha256',digest(self.lineage));self.publish()

    def publish(self):self.ref=base_ref(self.root,'config/summary-v2.json',canonical_bytes(self.profile))


class SourceSummaryV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=tempfile.TemporaryDirectory();cls.fixture=SummaryV2Fixture(Path(cls.base.name))

    @classmethod
    def tearDownClass(cls):cls.base.cleanup()

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('g0_full_universe_score_summary_v2'),'Missing v2')
        self.module=importlib.import_module('g0_full_universe_score_summary_v2')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'fixture'
        shutil.copytree(self.base.name,self.root)
        self.f=copy.deepcopy(self.fixture);self.f.root=self.root;self.f.forecast.root=self.root;self.f.source.root=self.root
        self.context=pi.ProspectiveReadContext(300,2*1024**3)

    def call(self,context=None):
        return self.module.score_g0_forecast_summary_v2(self.root,self.f.ref,NIGHT,NOW,
            expected_feature_definition_sha256=self.f.profile['feature_definition_sha256'],
            expected_candidate_config_sha256=digest(self.f.source.config),context=self.context if context is None else context)

    def test_full_fixed_three_unequal_domain_matches_independent_native_rowwise_oracle(self):
        with patch.object(a1,'fit_hba1',side_effect=AssertionError('runtime fit')),patch.object(a2,'_backend',side_effect=AssertionError('runtime backend')):
            value=self.call()
        self.assertEqual(value['status'],'COMPLETE_DECLARED_SCORE_SUMMARY')
        self.assertEqual(value['candidate_ids'],['uniform','HB-A1','HB-A2'])
        self.assertEqual(value['full_counts'],dict(cell_count=6,window_count=3,shard_count=6,unit_count=18,area_count=4))
        predictions={ident:a1.predict_hba1(m,self.f.rows,cutoff_time=self.f.profile['forecast_cutoff'],joined_universe_sha256=digest(self.f.rows))
            if ident=='HB-A1' else a2.predict_hba2(m,self.f.rows,cutoff_time=self.f.profile['forecast_cutoff'],joined_universe_sha256=digest(self.f.rows))
            for ident,m in self.f.models.items() if ident!='uniform'}
        from fractions import Fraction
        for item in value['model_summaries']:
            ident=item['candidate_id'];groups={};stream=hashlib.sha256(b'HABU-G0-SCORE-STREAM-V2\0')
            header=dict(candidate_id=ident,model_sha256=self.f.models[ident]['model_sha256'],recipe_sha256=self.f.models[ident].get('recipe_sha256'),
                candidate_config_sha256=digest(self.f.source.config),feature_definition_sha256=self.f.profile['feature_definition_sha256'],
                training_selection_sha256=self.f.lineage['selection_sha256'],fit_lineage_sha256=digest(self.f.lineage),
                operational_night=NIGHT,fit_cutoff=self.f.profile['fit_cutoff'],forecast_cutoff=self.f.profile['forecast_cutoff'],score_semantics='MEAN_NATIVE_UNIT_SPATIAL_SCORE')
            def frame(tag,v):
                b=canonical_bytes(v);stream.update(tag+len(b).to_bytes(8,'big')+b)
            frame(b'H',header)
            for i,row in enumerate(self.f.rows):
                probability=self.f.models['uniform']['probability'] if ident=='uniform' else predictions[ident]['unit_predictions'][i]['spatial_score']
                area=a1.area_id(row['cell_x'],row['cell_y']);groups.setdefault(area,[]).append(probability)
                frame(b'R',dict(ordinal=i,row_id=row['row_id'],native_score=probability))
            frame(b'T',dict(row_count=18,canonical_joined_rows_sha256=value['forecast_receipt']['canonical_joined_rows_sha256']))
            expected=[dict(area_id=a,unit_count=len(v),mean_native_score=float(sum((Fraction(x) for x in v),Fraction())/len(v))) for a,v in sorted(groups.items())]
            self.assertEqual(item['area_summaries'],expected);self.assertEqual(item['score_stream_sha256'],stream.hexdigest())
            self.assertEqual(item['top10_area_ids'],[v['area_id'] for v in sorted(expected,key=lambda v:(-v['mean_native_score'],v['area_id']))])
        self.assertTrue(all(x is False for x in value['authorities'].values()))
        self.assertEqual(value['summary_sha256'],digest({k:v for k,v in value.items() if k!='summary_sha256'}))

    def test_missing_whole_support_still_checks_last_raw_f32_and_physical_values(self):
        self.f.profile['fit_lineage']=None;self.f.profile['models'][2]['artifact']=None;self.f.publish()
        good=self.call();self.assertEqual(good['status'],'NEED_MORE_DATA');self.assertEqual(good['model_summaries'],[])
        f=self.f.forecast;node=f.nodes[f.manifest['shards'][-1]['snapshot_id']];snap=f.objects[node['ref']['path']]
        target=next(r['path'] for r in snap['features'] if 'temperature_c'==f.objects[r['path']]['feature_name'])
        row=next(reversed(f.objects[target]['values']));f.objects[target]['values'][row]=1e300;f.publish()
        self.f.profile['forecast_manifest']=f.ref;self.f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_actual_prior_charge_preserves_streams_but_not_execution_hash(self):
        before=self.call();ctx=pi.ProspectiveReadContext(300,2*1024**3)
        g0.G0ArtifactReader(self.root,ctx).read(base_ref(self.root,'config/prior.bin',b'prior'),parse=False)
        deadline,max_bytes,check=ctx.deadline,ctx.max_bytes,ctx.check
        value=self.call(ctx)
        self.assertEqual(before['model_summaries'],value['model_summaries'])
        self.assertNotEqual(before['summary_sha256'],value['summary_sha256'])
        self.assertEqual(value['actual_read_bytes']-before['actual_read_bytes'],5)
        self.assertEqual((ctx.deadline,ctx.max_bytes,ctx.check),(deadline,max_bytes,check))
        self.assertNotIn('check',ctx.__dict__)

    def test_known_last_model_contradiction_cannot_hide_under_missing_lineage(self):
        self.f.profile['fit_lineage']=None
        model=self.f.models['HB-A2'];model['training_rows_sha256']='a'*64;model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
        self.f.publish_models();self.f.profile['fit_lineage']=None;self.f.publish()
        with self.assertRaisesRegex(ValueError,'TRAIN'):self.call()

    def test_known_extra_train_schema_is_invalid_when_all_models_are_missing(self):
        self.f.lineage['feature_names']=sorted([*self.f.lineage['feature_names'],'unexpected_column'])
        self.f.lineage['model_sha256_by_id']={ident:None for ident in self.module.CANDIDATES}
        self.f.publish_lineage()
        for entry in self.f.profile['models']:entry['artifact']=None
        self.f.publish()
        with self.assertRaisesRegex(ValueError,'TRAIN.*schema'):self.call()

    def test_source2_late_is_own_admission_barrier_before_model_or_g0_payloads(self):
        self.f.source.profile['readiness']['audited_at']=self.f.profile['fit_cutoff'];self.f.source.profile['usable_at']=self.f.profile['fit_cutoff']
        self.f.source.profile_only();self.f.profile['candidate_config_manifest']=self.f.source.ref;self.f.publish()
        paths=[];original=Path.open
        def opened(p,*a,**kw):paths.append(p.relative_to(self.root).as_posix());return original(p,*a,**kw)
        with patch.object(Path,'open',opened),self.assertRaises(self.module.config_source.CandidateConfigSourceBlocked):self.call()
        self.assertFalse(any(p.startswith(('models/candidates/','features/')) for p in paths))

    def test_new_own_late_cannot_hide_last_shard_corruption(self):
        self.f.profile['readiness']['audited_at']=self.f.profile['forecast_cutoff'];self.f.profile['usable_at']=self.f.profile['forecast_cutoff'];self.f.publish()
        with self.assertRaises(self.module.ScoreSummarySourceBlocked):self.call()
        f=self.f.forecast;path=f.nodes[f.manifest['shards'][-1]['validity_id']]['ref']['path'];(self.root/path).write_bytes(b'{}')
        with self.assertRaises(ValueError) as caught:self.call()
        self.assertNotIsInstance(caught.exception,self.module.ScoreSummarySourceBlocked)

    def test_exact_context_consumer_gate_rejects_unowned_objects_before_reads(self):
        module=self.module
        reducer=object.__new__(module._ScoreReducerV2);object.__setattr__(reducer,'context',self.context)
        class Sub(module._ScoreReducerV2):pass
        sub=object.__new__(Sub);object.__setattr__(sub,'context',self.context)
        for candidate,ctx,collect in ((object(),self.context,False),(sub,self.context,False),(reducer,None,False),(reducer,self.context,True),
                (reducer,pi.ProspectiveReadContext(300,2*1024**3),False)):
            with self.subTest(type=type(candidate),context=ctx,collect=collect),patch.object(g0._Reader,'read',side_effect=AssertionError('invalid gate read')):
                with self.assertRaises(ValueError):g0._validate(self.root,self.f.forecast.ref,NIGHT,NOW,self.f.profile['feature_definition_sha256'],300,collect,ctx,_summary_v2=candidate)

    def test_new_consumer_requires_literal_false_collection_and_present_owned_context(self):
        reducer=object.__new__(self.module._ScoreReducerV2);object.__setattr__(reducer,'context',self.context)
        bare=object.__new__(self.module._ScoreReducerV2)
        for candidate,collect in [(reducer,0),(reducer,None),(reducer,[]),(bare,False)]:
            with self.subTest(candidate=type(candidate),collect=collect),patch.object(g0._Reader,'read',side_effect=AssertionError('invalid slot payload read')):
                with self.assertRaises(ValueError):g0._validate(self.root,self.f.forecast.ref,NIGHT,NOW,self.f.profile['feature_definition_sha256'],300,collect,self.context,_summary_v2=candidate)

    def test_owned_final_children_and_fully_sealed_output_capacity(self):
        a=self.call(pi.ProspectiveReadContext(300,2*1024**3));b=self.call(pi.ProspectiveReadContext(300,2*1024**3));saved=copy.deepcopy(a)
        b['candidate_config_source_receipt']['consumed_refs'][0]['sha256']='a'*64
        b['model_bindings'][0]['artifact']['ref']['sha256']='a'*64
        self.assertEqual(a,saved)
        sealed=len(canonical_bytes(a));body=len(canonical_bytes({k:v for k,v in a.items() if k!='summary_sha256'}))
        self.assertLess(body,sealed)
        with patch.object(self.module,'MAX_OUTPUT_BYTES',sealed-1),self.assertRaises(pi.InputCapacityError):self.call(pi.ProspectiveReadContext(300,2*1024**3))

    def test_delegated_native_window_overflow_is_local_invalid_input_not_raw_runtime_overflow(self):
        for ident in ('HB-A1','HB-A2'):
            original=copy.deepcopy(self.f.models[ident]);model=self.f.models[ident]
            model['training_window_start_max']='0001-01-01T00:00:00+23:00'
            model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
            self.f.publish_models();self.f.profile['fit_lineage']=None;self.f.publish()
            with self.subTest(model=ident),self.assertRaises(ValueError):self.call()
            self.f.models[ident]=original

    def test_all_known_raw_contradictions_reject_even_without_last_model_and_lineage(self):
        self.f.profile['fit_lineage']=None;self.f.profile['models'][2]['artifact']=None
        f=self.f.forecast;original=copy.deepcopy(f.objects)
        for name,poison in [('humidity_pct',101),('precipitation_mm',-1),('slope_deg',90),('road_length_m',0),
                ('wind_cross_road_proxy',1.1),('temperature_c',1e300),('tpi_m',-1e300),('temperature_c',True),('temperature_c',float('nan'))]:
            f.objects=copy.deepcopy(original)
            node=f.nodes[f.manifest['shards'][-1]['snapshot_id']];snap=f.objects[node['ref']['path']]
            path=next(r['path'] for r in snap['features'] if f.objects[r['path']]['feature_name']==name)
            row=next(reversed(f.objects[path]['values']));f.objects[path]['values'][row]=poison
            identifier=next(k for k,v in f.nodes.items() if v['ref']['path']==path)
            f.overwrite_node_raw(identifier,json.dumps(f.objects[path],allow_nan=True).encode())
            self.f.profile['forecast_manifest']=f.ref;self.f.publish()
            with self.subTest(feature=name,poison=poison),self.assertRaises(ValueError):self.call(pi.ProspectiveReadContext(300,2*1024**3))

    def test_metadata_frame_state_caps_and_no_collector_or_preparation_evasion(self):
        module=self.module
        with self.assertRaises(pi.InputCapacityError):module._copy([None]*2_000_000,self.context.check)
        nested=None
        for _ in range(14):nested=[nested]
        with self.assertRaises(pi.InputCapacityError):module._copy(nested,self.context.check)
        reducer=object.__new__(module._ScoreReducerV2);object.__setattr__(reducer,'context',self.context);object.__setattr__(reducer,'hashes',{'uniform':hashlib.sha256()})
        with self.assertRaises(pi.InputCapacityError):reducer._frame('uniform',b'R',{'row_id':'x'*4096})
        for name,cap in [('MAX_AREAS',3),('MAX_STATES',11)]:
            with self.subTest(cap=name),patch.object(module,name,cap),self.assertRaises(pi.InputCapacityError):self.call(pi.ProspectiveReadContext(300,2*1024**3))
        import research_candidate_preparation_v3 as prep
        with (patch.object(g0,'MAX_MODEL_ROWS',1),patch.object(g0,'load_g0_forecast_rows',side_effect=AssertionError('collector')),
                patch.object(prep,'prepare_research_candidates_v3',side_effect=AssertionError('preparer'))):
            self.assertEqual(self.call()['full_counts']['unit_count'],18)

    def test_code_or_membership_change_during_rows_cannot_publish_after_rescan(self):
        original=self.module.config_old.recheck_research_candidate_config
        code=self.root/'src/models/hba2_feature_candidate.py';raw=code.read_bytes()
        def changed(*args,**kwargs):code.write_bytes(raw+b'\n# changed');return original(*args,**kwargs)
        with patch.object(self.module.config_old,'recheck_research_candidate_config',changed),self.assertRaises(ValueError):self.call()
        code.write_bytes(raw)
        def extra(*args,**kwargs):base_ref(self.root,'src/new-unbound.py',b'# unbound');return original(*args,**kwargs)
        with patch.object(self.module.config_old,'recheck_research_candidate_config',extra),self.assertRaises(ValueError):self.call()

    def test_actual_last_digest_and_fully_sealed_bound_callback_abort_is_original(self):
        class Falsey(OverflowError):
            def __bool__(self):return False
            def __eq__(self,other):raise AssertionError('exception equality is not identity')
        for name in ('_digest','_encoded'):
            for cls in (pi.InputCapacityError,Falsey,KeyboardInterrupt):
                ctx=pi.ProspectiveReadContext(300,2*1024**3);native=ctx.check;armed=[False];marker=cls('final real callback')
                def guard():
                    if armed[0]:raise marker
                    native()
                actual=getattr(self.module,name)
                def operation(value,*args,**kwargs):
                    result=actual(value,*args,**kwargs)
                    if isinstance(value,dict) and value.get('schema_version')==self.module.VERSION:
                        if name=='_digest' or 'summary_sha256' in value:armed[0]=True
                    return result
                ctx.check=guard
                with self.subTest(stage=name,error=cls),patch.object(self.module,name,operation),self.assertRaises(cls) as caught:self.call(ctx)
                self.assertIs(caught.exception,marker);self.assertTrue(armed[0]);self.assertIs(ctx.check,guard)

    def test_proper_missing_raw_schema_is_whole_need_after_all_remaining_known_values(self):
        f=self.f.forecast;missing='wind_cross_road_proxy'
        removed={k for k,v in f.nodes.items() if f.objects[v['ref']['path']].get('feature_name')==missing}
        paths={f.nodes[k]['ref']['path'] for k in removed}
        for k in removed:del f.nodes[k]
        for p in paths:del f.objects[p]
        f.features=[v for v in f.features if v['name']!=missing];f.manifest['features']=f.features
        f.manifest['feature_definition_sha256']=definition_hash(f.features)
        for node in f.nodes.values():
            node['parents']=[p for p in node['parents'] if p not in removed];value=f.objects[node['ref']['path']]
            if value.get('schema_version')=='2.0':
                value['features']=[v for v in value['features'] if v['path'] not in paths]
                value['feature_schema_sha256']=digest(sorted(v['name'] for v in f.features))
            if value.get('schema_version')=='habu-g0-validity-v1':
                value['feature_sources'].pop(missing)
                for v in value['rows'].values():v.pop(missing)
        f.publish();definition=definition_hash(f.features)
        self.f.source.config['feature_definition_sha256']=definition;self.f.source.profile['feature_definition_sha256']=definition;self.f.source.publish()
        self.f.profile.update(feature_definition_sha256=definition,forecast_manifest=f.ref,candidate_config_manifest=self.f.source.ref);self.f.publish()
        value=self.call();self.assertEqual(value['status'],'NEED_MORE_DATA');self.assertEqual(value['model_summaries'],[])
        self.assertEqual(value['full_counts']['unit_count'],18)
        last=next(v for v in reversed(list(f.objects.values())) if v.get('feature_name')=='temperature_c')
        last['values'][next(reversed(last['values']))]=1e300;f.publish();self.f.profile['forecast_manifest']=f.ref;self.f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_sealed_native_children_keep_full_values_order_and_are_not_borrowed(self):
        saved={};actual_load=self.module.config_source.load_research_candidate_config_v2;actual_finish=self.module._ScoreReducerV2._finish
        def source(*args,**kwargs):
            result=actual_load(*args,**kwargs);saved['source']=result['receipt'];saved['source_raw']=json.dumps(result['receipt'],ensure_ascii=False);return result
        def finish(reducer,receipt,refs):
            saved['forecast']=receipt;saved['forecast_raw']=json.dumps(receipt,ensure_ascii=False)
            return actual_finish(reducer,receipt,refs)
        with patch.object(self.module.config_source,'load_research_candidate_config_v2',source),patch.object(self.module._ScoreReducerV2,'_finish',finish):value=self.call()
        self.assertEqual(json.dumps(value['candidate_config_source_receipt'],ensure_ascii=False),saved['source_raw'])
        self.assertEqual(json.dumps(value['forecast_receipt'],ensure_ascii=False),saved['forecast_raw'])
        before=copy.deepcopy(value);saved['source']['consumed_refs'].clear();saved['forecast']['consumed_sha256'].clear()
        self.assertEqual(value,before)

    def test_real_expiry_and_actual_caller_origins_at_new_model_math_rescan_and_seal(self):
        ctx=pi.ProspectiveReadContext(.001,2*1024**3);time.sleep(.01)
        with self.assertRaises(TimeoutError):self.call(ctx)
        for owner,name in ((a2,'_model'),(a2,'_raw_prob'),(self.module,'_copy'),(self.module.config_old,'recheck_research_candidate_config')):
            for cls in (pi.InputCapacityError,OverflowError,KeyboardInterrupt):
                ctx=pi.ProspectiveReadContext(300,2*1024**3);marker=cls('caller-origin');armed=[False];native=ctx.check;original=getattr(owner,name)
                def check():
                    if armed[0]:raise marker
                    native()
                def operation(*args,**kwargs):armed[0]=True;return original(*args,**kwargs)
                ctx.check=check
                with self.subTest(seam=name,error=cls),patch.object(owner,name,operation),self.assertRaises(cls) as caught:self.call(ctx)
                self.assertIs(caught.exception,marker);self.assertIs(ctx.check,check)


class GenuinePinnedSummaryV2Tests(unittest.TestCase):
    def test_actual_pinned_fit_export_and_full_summary_public_prediction_parity_is_required_on_CI(self):
        import importlib.metadata
        try:versions={k:importlib.metadata.version(k) for k in a2.PINS}
        except importlib.metadata.PackageNotFoundError:versions={}
        if versions!=a2.PINS:
            if os.environ.get('GITHUB_ACTIONS','').lower()=='true':self.fail('Required genuine pinned A2 numeric summary gate unavailable')
            self.skipTest('Actual pinned numerical backend unavailable; no fit claimed')
        import numpy as np
        from sklearn.ensemble import GradientBoostingClassifier
        fitted=[];actual_fit=GradientBoostingClassifier.fit
        def actual_observed_fit(estimator,*args,**kwargs):
            result=actual_fit(estimator,*args,**kwargs);fitted.append(estimator);return result
        with tempfile.TemporaryDirectory() as folder,patch.object(GradientBoostingClassifier,'fit',actual_observed_fit):
            f=SummaryV2Fixture(Path(folder),numeric=True);module=importlib.import_module('g0_full_universe_score_summary_v2')
            self.assertEqual(len(fitted),1)
            split=next(tree['nodes'][0] for tree in f.models['HB-A2']['trees'] if tree['nodes'][0]['left']!=-1)
            threshold=split['threshold'];lower=np.float32(threshold)
            if float(lower)>threshold:lower=np.nextafter(lower,np.float32(-math.inf))
            upper=np.nextafter(lower,np.float32(math.inf));self.assertLessEqual(float(lower),threshold);self.assertGreater(float(upper),threshold)
            feature=a2.FEATURES[split['feature']];forecast=f.forecast;changed=0
            for node in forecast.nodes.values():
                path=node['ref']['path'];value=forecast.objects[path]
                if value.get('feature_name')!=feature:continue
                for rid in value['values']:
                    value['values'][rid]=float(lower if changed%2==0 else upper);changed+=1
            self.assertEqual(changed,18);forecast.publish();f.profile['forecast_manifest']=forecast.ref;f.publish()
            f.rows=g0.load_g0_forecast_rows(f.root,forecast.ref,NIGHT,NOW,expected_feature_definition_sha256=f.profile['feature_definition_sha256'])['rows']
            result=module.score_g0_forecast_summary_v2(f.root,f.ref,NIGHT,NOW,expected_feature_definition_sha256=f.profile['feature_definition_sha256'],
                expected_candidate_config_sha256=digest(f.source.config),context=pi.ProspectiveReadContext(300,2*1024**3))
            matrix=np.asarray([[r['features'][name] for name in a2.FEATURES] for r in f.rows],dtype=np.float32)
            native=fitted[0].predict_proba(matrix)[:,1].tolist()
            _,pure=a2._raw_prob(f.models['HB-A2']['trees'],matrix.tolist(),lambda:None)
            self.assertLessEqual(max(abs(a-b) for a,b in zip(native,pure)),1e-12)
            predicted=a2.predict_hba2(f.models['HB-A2'],f.rows,cutoff_time=f.profile['forecast_cutoff'],joined_universe_sha256=digest(f.rows),budget_seconds=300)
            self.assertEqual([u['probability'] for u in predicted['unit_predictions']],[round(p,8) for p in native])
            areas={}
            for unit in predicted['unit_predictions']:areas.setdefault(unit['area_id_1km'],[]).append(unit['spatial_score'])
            from fractions import Fraction
            self.assertEqual(result['model_summaries'][2]['area_summaries'],[dict(area_id=k,unit_count=len(v),mean_native_score=float(sum((Fraction(x) for x in v),Fraction())/len(v))) for k,v in sorted(areas.items())])


class FixedConsumerAdmissionTests(unittest.TestCase):
    def test_incomplete_instance_callbacks_publish_zero_rows_and_reject_before_reader(self):
        module=importlib.import_module('g0_full_universe_score_summary_v2')
        for mutate in (False,True):
            with self.subTest(late_mutation=mutate),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);f=SyntheticContract(root);ctx=pi.ProspectiveReadContext(300,2*1024**3)
                reducer=object.__new__(module._ScoreReducerV2);object.__setattr__(reducer,'context',ctx)
                external=[];reader_calls=[];original=g0._Reader.__init__
                path=next(root/v['ref']['path'] for v in f.nodes.values() if v['source_kind']=='feature_values')
                def add(row):
                    external.append(row)
                    if mutate and len(external)==1:path.write_bytes(b'{}')
                hooks={'_prepare':lambda *a:None,'_add':add,'_rescan_metadata':lambda:None,'_finish':lambda *a:{'arbitrary_finish':True},'check':lambda:None}
                for name,value in hooks.items():
                    try:setattr(reducer,name,value)
                    except AttributeError:pass
                def actual_reader(reader,*args):reader_calls.append(True);return original(reader,*args)
                rejected=False
                with patch.object(g0._Reader,'__init__',actual_reader):
                    try:g0._validate(root,f.ref,NIGHT,NOW,f.manifest['feature_definition_sha256'],300,False,ctx,_summary_v2=reducer)
                    except ValueError:rejected=True
                self.assertEqual((rejected,len(reader_calls),len(external)),(True,0,0))

    def test_ordinary_instance_hooks_check_and_reader_cannot_be_replaced(self):
        module=importlib.import_module('g0_full_universe_score_summary_v2');reducer=object.__new__(module._ScoreReducerV2)
        for name in ('_prepare','_add','_rescan_metadata','_finish','check','reader','context'):
            with self.subTest(attribute=name),self.assertRaises(AttributeError):setattr(reducer,name,lambda *a:None)


class SummaryV2ContractTests(unittest.TestCase):
    def test_explicit_v2_entry_exists_without_widening_old_summary(self):
        self.assertIsNotNone(importlib.util.find_spec('g0_full_universe_score_summary_v2'),
            'Missing explicit fixed uniform/A1/A2 full-domain summary')
        module=importlib.import_module('g0_full_universe_score_summary_v2')
        self.assertEqual(list(inspect.signature(module.score_g0_forecast_summary_v2).parameters),
            ['root','summary_manifest_ref','operational_night','as_of',
             'expected_feature_definition_sha256','expected_candidate_config_sha256','context'])

    def test_g0_has_separate_closed_v2_slot_old_slot_default_is_unchanged(self):
        params=inspect.signature(g0._validate).parameters
        self.assertIn('_summary_v2',params,'Missing narrow closed second consumer slot')
        self.assertIsNone(params['_summary_v2'].default)
        self.assertIsNone(params['_summary'].default)


if __name__=='__main__':unittest.main()
