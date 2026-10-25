"""Synthetic diagnostic foundation tests; no qualified source fit or authority."""
import copy
import importlib
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path
from statistics import mean
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
from master_contracts import digest
from test_hba1_feature_candidate import fixture, recipe
import research_model_adapter as adapter
from models import hba1_feature_candidate as hba1
from models import occupancy_shrinkage as a0
from test_g0_forecast_contract import SyntheticContract, base_ref, definition_hash, NIGHT, CUTOFF, NOW, READY
from test_research_candidate_config_source import ConfigSourceFixture
import g0_forecast_contract as g0
import prospective_inputs as pi
import codex_cycle_contract as cycle


class SharedScalarSeamTests(unittest.TestCase):
    def setUp(self):
        protocol, folds = fixture()
        self.selection = folds[0]['training_selection']
        self.rows = folds[0]['forecast_rows']
        self.cutoff = protocol['folds'][0]['cutoff_time']
        self.config = dict(schema_version=adapter.CONFIG_VERSION_V2, mode='DEVELOPMENT_ONLY',
            candidate_ids=['uniform','HB-A0','HB-A1'], hba1_recipe=recipe(),
            feature_definition_sha256='f'*64)
        self.prepared = adapter.prepare_research_candidates_v2(self.selection,self.rows,
            candidate_config=self.config,expected_config_sha256=digest(self.config),
            cutoff_time=self.cutoff,joined_universe_sha256=digest(self.rows),
            feature_definition_sha256='f'*64)

    def test_uniform_shared_scalar_and_serialized_guard_keep_native_artifact(self):
        scalar = getattr(adapter,'_uniform_probability',None)
        self.assertTrue(callable(scalar),'shared existing uniform scalar is missing')
        guard = getattr(adapter,'_validate_uniform_model',None)
        self.assertTrue(callable(guard),'exact uniform serialized guard is missing')
        model = self.prepared['candidates'][0]['model']
        self.assertEqual(scalar(model['counts']),model['probability'])
        self.assertEqual(guard(model,lambda:None),model)
        bad = copy.deepcopy(model);bad['probability']=0.0
        bad['model_sha256']=digest({k:v for k,v in bad.items() if k!='model_sha256'})
        with self.assertRaises(ValueError):guard(bad,lambda:None)

    def test_a0_scalar_reuses_area_lookup_and_fallback(self):
        scalar = getattr(a0,'_probability_for_area',None)
        self.assertTrue(callable(scalar),'shared native A0 lookup is missing')
        candidate = self.prepared['candidates'][1]
        for row in candidate['prediction']['unit_predictions']:
            self.assertEqual(scalar(candidate['model'],row['area_id_1km']),row['probability'])
        self.assertEqual(scalar(candidate['model'],'utm52n_1km_999_999'),candidate['model']['global_probability'])

    def test_a1_scalar_retains_native_order_rounding_and_local_overflow_checks(self):
        scalar = getattr(hba1,'_score_owned_row',None)
        self.assertTrue(callable(scalar),'shared native A1 scalar is missing')
        candidate = self.prepared['candidates'][2]
        for row,unit in zip(self.rows,candidate['prediction']['unit_predictions']):
            self.assertEqual(scalar(candidate['model'],row,lambda:None),unit['probability'])

    def test_a0_guard_checks_callback_inside_owned_copy(self):
        marker = RuntimeError('owned model guard callback')
        def stop():raise marker
        with self.assertRaises(RuntimeError) as caught:
            a0._validate_model(self.prepared['candidates'][1]['model'],check=stop)
        self.assertIs(caught.exception,marker)


class SummaryFixture:
    def __init__(self,root,unequal=False):
        self.root=root
        self.forecast=SyntheticContract(root)
        f=self.forecast
        # Test-only producer: use all seven bounded raw features, never a real source.
        f.features=[]
        native=fixture()[1][0]['forecast_rows'][0]['features']
        for name in hba1.FEATURES:
            definition='Synthetic fixed '+name
            f.features.append(dict(name=name,units='synthetic',version='1',definition=definition,
                definition_sha256=hashlib.sha256(definition.encode()).hexdigest(),
                code_ref=copy.deepcopy(f.manifest['features'][0]['code_ref']),deployment='forecast_predictor',required_source_ids=['weather']))
        from datetime import timedelta
        from test_g0_forecast_contract import START,row_id
        if unequal:
            f.cells=[[4000,30000],[4001,30000],[4010,30000],[4020,30000],[4021,30000],[4030,30000]]
            f.valid=dict(start=START,end=NIGHT+'T19:30:00+09:00')
        cp,tp=([[0,2],[2,3],[3,6]],[[0,1],[1,3]]) if unequal else ([[0,1],[1,2]],[[0,1],[1,2]])
        f.nodes={key:f.nodes[key] for key in ('roads','weather','domain')}
        f.objects={node['ref']['path']:f.objects[node['ref']['path']] for node in f.nodes.values()}
        for key in ('roads','weather'):
            f.nodes[key]['valid_time']=f.valid.copy();f.objects[f.nodes[key]['ref']['path']]['valid_time']=f.valid.copy()
        f.nodes['domain']['valid_time']=f.valid.copy()
        f.objects[f.nodes['domain']['ref']['path']]['cells']=f.cells
        f.objects[f.nodes['roads']['ref']['path']]['data']['road_cells']=f.cells
        f.snapshots=[];shards=[]
        native_rows=fixture()[1][0]['forecast_rows']
        for ci,cells in enumerate(cp):
            for ti,times in enumerate(tp):
                sid=f'c{ci}t{ti}';units=[];values={name:{} for name in hba1.FEATURES}
                for cell_index in range(*cells):
                    cell=f.cells[cell_index]
                    for time_index in range(*times):
                        stamp=datetime.fromisoformat(START)+timedelta(minutes=10*time_index);rid=row_id(cell,stamp)
                        units.append(dict(row_id=rid,operational_night=NIGHT,cutoff_time=CUTOFF,window_start_jst=stamp.isoformat(),
                            utm_x_m=cell[0]*100+50,utm_y_m=cell[1]*100+50))
                        native=native_rows[(cell_index+time_index)%4]['features']
                        for name in hba1.FEATURES:values[name][rid]=native[name]
                f.add(sid+'-u','features/'+sid+'-universe.json','forecast_universe','universe',['domain'],
                    dict(schema_version='1.0',source_type='EX_ANTE_FORECAST',geographic_domain={'crs':'EPSG:32652','name':'SYNTHETIC'},rows=units))
                refs=[];ids=[]
                for index,name in enumerate(hba1.FEATURES):
                    identifier=sid+'-f'+str(index);path='features/'+identifier+'.json'
                    f.add(identifier,path,'feature_values','feature',['weather'],dict(schema_version='1.0',operational_night=NIGHT,
                        cutoff_time=CUTOFF,available_at=READY,feature_name=name,use_role='forecast_predictor',values=values[name]))
                    refs.append({'path':path});ids.append(identifier)
                f.add(sid+'-s','features/'+sid+'-snapshot.json','snapshot','protocol',[sid+'-u',*ids],
                    dict(schema_version='2.0',operational_night=NIGHT,cutoff_time=CUTOFF,universe={'path':f.nodes[sid+'-u']['ref']['path']},
                        features=refs,feature_schema_sha256=digest(sorted(hba1.FEATURES))))
                f.snapshots.append(sid+'-s')
                f.add(sid+'-v','features/'+sid+'-validity.json','validity','protocol',ids,
                    dict(schema_version='habu-g0-validity-v1',feature_sources={name:[identifier] for name,identifier in zip(hba1.FEATURES,ids)},
                        rows={unit['row_id']:{name:f.valid.copy() for name in hba1.FEATURES} for unit in units}))
                shards.append(dict(shard_id=sid,cell_partition=ci,time_partition=ti,snapshot_id=sid+'-s',validity_id=sid+'-v'))
        f.manifest['features']=f.features
        f.manifest['feature_definition_sha256']=definition_hash(f.features)
        f.manifest.update(cell_partitions=cp,time_partitions=tp,shards=shards,horizon=f.valid.copy())
        f.publish()
        # Current code bytes, independently from the immutable old-code oracle.
        for path in cycle.code_paths(ROOT):base_ref(root,path,(ROOT/path).read_bytes())
        self.source=ConfigSourceFixture(root,definition_hash(f.features))
        self.selection=fixture()[1][0]['training_selection']
        self.selection['heldout_night']=NIGHT
        from test_prospective_candidate_model import rebind
        rebind(self.selection)
        self.rows=g0.load_g0_forecast_rows(root,f.ref,NIGHT,NOW,
            expected_feature_definition_sha256=definition_hash(f.features))['rows']
        self.prepared=adapter.prepare_research_candidates_v2(self.selection,self.rows,
            candidate_config=self.source.config,expected_config_sha256=digest(self.source.config),
            cutoff_time=CUTOFF,joined_universe_sha256=digest(self.rows),feature_definition_sha256=definition_hash(f.features))
        models=self.prepared['candidates']
        first=models[2]['model']
        self.lineage=dict(schema_version='habu-g0-fitted-lineage-declaration-v1',kind='LABEL_FREE_TRAIN_IDENTITY_DECLARATION',
            heldout_night=NIGHT,fit_cutoff=self.selection['fit_cutoff'],selection_sha256=self.selection['selection_sha256'],
            corpus_sha256=first['corpus_sha256'],source_sha256=first['source_sha256'],source_received_at=first['source_received_at'],
            training_nights=first['training_nights'],training_window_start_max=first['training_window_start_max'],
            counts=first['counts'],feature_names=self.selection['feature_names'],training_rows_sha256=first['training_rows_sha256'],
            training_row_ids_sha256=first['training_row_ids_sha256'],raw_feature_rows_sha256=first['raw_feature_rows_sha256'],
            model_sha256_by_id={c['candidate_id']:c['model_sha256'] for c in models})
        def binding(ref,field,sha):
            return dict(ref=ref,**{field:sha},readiness=dict.fromkeys(pi.READINESS_FIELDS,READY),usable_at=READY)
        self.profile=dict(schema_version='habu-g0-full-universe-score-source-v1',kind='UNCONNECTED_DEVELOPMENT_SCORE_SUMMARY',
            operational_night=NIGHT,fit_cutoff=self.selection['fit_cutoff'],forecast_cutoff=CUTOFF,
            feature_definition_sha256=definition_hash(f.features),forecast_manifest=f.ref,candidate_config_manifest=self.source.ref,
            fit_lineage=binding(base_ref(root,'protocols/development/lineage.json',__import__('master_contracts').canonical_bytes(self.lineage)),
                'lineage_sha256',digest(self.lineage)),models=[],readiness=dict.fromkeys(pi.READINESS_FIELDS,READY),usable_at=READY)
        for c in models:
            ref=base_ref(root,'models/candidates/'+c['candidate_id']+'.json',json.dumps(c['model'],indent=2).encode())
            self.profile['models'].append(dict(candidate_id=c['candidate_id'],artifact=binding(ref,'model_sha256',c['model_sha256'])))
        self.publish()

    def publish(self):
        self.ref=base_ref(self.root,'config/score-summary.json',__import__('master_contracts').canonical_bytes(self.profile))


class SourceSummaryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('g0_full_universe_score_summary'),'standalone summary entry is missing')
        self.module=importlib.import_module('g0_full_universe_score_summary')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.f=SummaryFixture(self.root)

    def call(self,**kwargs):
        return self.module.score_g0_forecast_summary(self.root,self.f.ref,NIGHT,NOW,
            expected_feature_definition_sha256=self.f.profile['feature_definition_sha256'],
            expected_candidate_config_sha256=digest(self.f.source.config),**kwargs)

    def test_source_bound_full_three_summary_equals_whole_native_mean_and_top10(self):
        value=self.call()
        self.assertEqual(value['status'],'COMPLETE_DECLARED_SCORE_SUMMARY')
        self.assertEqual(value['full_counts']['unit_count'],4)
        for summary,candidate in zip(value['model_summaries'],self.f.prepared['candidates']):
            groups={}
            for row in candidate['prediction']['unit_predictions']:groups.setdefault(row['area_id_1km'],[]).append(row['spatial_score'])
            self.assertEqual(summary['area_summaries'],[dict(area_id=area,unit_count=len(values),mean_native_score=mean(values)) for area,values in sorted(groups.items())])
        self.assertTrue(all(v is False for v in value['authorities'].values()))
        self.assertEqual(value['summary_sha256'],digest({k:v for k,v in value.items() if k!='summary_sha256'}))
        self.assertNotIn('prediction',value)

    def test_missing_model_and_lineage_release_no_partial_scores(self):
        self.f.profile['fit_lineage']=None;self.f.profile['models'][2]['artifact']=None;self.f.publish()
        value=self.call()
        self.assertEqual(value['status'],'NEED_MORE_DATA');self.assertEqual(value['model_summaries'],[])
        self.assertEqual(value['forecast_receipt']['row_count'],4)

    def test_last_shard_corruption_is_not_hidden_by_missing_lineage(self):
        self.f.profile['fit_lineage']=None
        node=self.f.forecast.nodes['c1t1-v'];(self.root/node['ref']['path']).write_bytes(b'{}')
        self.f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_sorted_sidecar_and_a0_names_native_a1_names_are_distinct_valid_orders(self):
        self.assertEqual(self.f.lineage['feature_names'],sorted(hba1.FEATURES))
        self.assertEqual(self.f.prepared['candidates'][1]['model']['selection_feature_names'],sorted(hba1.FEATURES))
        self.assertEqual(self.f.prepared['candidates'][2]['model']['feature_names'],list(hba1.FEATURES))
        self.assertEqual(self.call()['status'],'COMPLETE_DECLARED_SCORE_SUMMARY')

    def test_deadline_callback_exception_identity_and_no_context_refill(self):
        marker=OverflowError('parent guard identity')
        context=pi.ProspectiveReadContext(30,2*1024**3)
        def stop():raise marker
        with self.assertRaises(OverflowError) as caught:self.call(_read_context=context,check=stop)
        self.assertIs(caught.exception,marker)

    def test_missing_lineage_does_not_hide_conflicting_native_corpus_claim(self):
        self.f.profile['fit_lineage']=None
        artifact=self.f.profile['models'][1]['artifact'];model=copy.deepcopy(self.f.prepared['candidates'][1]['model'])
        model['corpus_sha256']='f'*64;model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
        artifact['ref']=base_ref(self.root,artifact['ref']['path'],json.dumps(model).encode());artifact['model_sha256']=model['model_sha256']
        self.f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_framed_stream_equals_independent_whole_native_oracle(self):
        from master_contracts import canonical_bytes
        value=self.call();lineage=self.f.lineage
        for summary,candidate in zip(value['model_summaries'],self.f.prepared['candidates']):
            ident=candidate['candidate_id'];model=candidate['model']
            hashed=hashlib.sha256(b'HABU-G0-SCORE-STREAM-V1\0')
            def frame(tag,payload):
                raw=canonical_bytes(payload);hashed.update(tag+len(raw).to_bytes(8,'big')+raw)
            frame(b'H',dict(candidate_id=ident,model_sha256=model['model_sha256'],recipe_sha256=model.get('recipe_sha256'),
                candidate_config_sha256=digest(self.f.source.config),feature_definition_sha256=self.f.profile['feature_definition_sha256'],
                training_selection_sha256=lineage['selection_sha256'],fit_lineage_sha256=digest(lineage),operational_night=NIGHT,
                fit_cutoff=self.f.profile['fit_cutoff'],forecast_cutoff=CUTOFF,score_semantics='MEAN_NATIVE_UNIT_SPATIAL_SCORE'))
            for index,row in enumerate(candidate['prediction']['unit_predictions']):
                frame(b'R',dict(ordinal=index,row_id=row['row_id'],native_score=row['spatial_score']))
            frame(b'T',dict(row_count=len(self.f.rows),canonical_joined_rows_sha256=digest(self.f.rows)))
            self.assertEqual(summary['score_stream_sha256'],hashed.hexdigest())

    def test_unequal_shards_and_all_areas_match_whole_native_oracle(self):
        self.f=SummaryFixture(self.root,unequal=True)
        value=self.call()
        self.assertEqual(value['full_counts']['unit_count'],18);self.assertEqual(value['full_counts']['area_count'],4)
        for summary,candidate in zip(value['model_summaries'],self.f.prepared['candidates']):
            groups={}
            for row in candidate['prediction']['unit_predictions']:groups.setdefault(row['area_id_1km'],[]).append(row['spatial_score'])
            expected=[dict(area_id=area,unit_count=len(scores),mean_native_score=mean(scores)) for area,scores in sorted(groups.items())]
            self.assertEqual(summary['area_summaries'],expected)
            self.assertEqual(summary['top10_area_ids'],[row['area_id'] for row in sorted(expected,key=lambda r:(-r['mean_native_score'],r['area_id']))])

    def test_sealed_output_cap_includes_own_hash_and_boundary_equality(self):
        from master_contracts import canonical_bytes
        value=self.call();length=len(canonical_bytes(value))
        with patch.object(self.module,'MAX_OUTPUT_BYTES',length-1),self.assertRaises(pi.InputCapacityError):self.call()
        with patch.object(self.module,'MAX_OUTPUT_BYTES',length):self.assertEqual(self.call(),value)

    def rewrite_lineage(self):
        from master_contracts import canonical_bytes
        binding=self.f.profile['fit_lineage']
        binding['ref']=base_ref(self.root,binding['ref']['path'],canonical_bytes(self.f.lineage))
        binding['lineage_sha256']=digest(self.f.lineage);self.f.publish()

    def test_lineage_window_outside_local_datetime_range_is_value_error(self):
        for stamp in ('9999-12-31T23:59:00+00:00', '0001-01-01T00:00:00+23:00'):
            with self.subTest(stamp=stamp):
                self.f.lineage['training_window_start_max']=stamp
                self.rewrite_lineage()
                with self.assertRaises(ValueError):self.call()

    def test_missing_lineage_does_not_hide_a0_window_range_error(self):
        self.f.profile['fit_lineage']=None
        entry=self.f.profile['models'][1]['artifact']
        for stamp in ('9999-12-31T23:59:00+00:00', '0001-01-01T00:00:00+23:00'):
            with self.subTest(stamp=stamp):
                model=copy.deepcopy(self.f.prepared['candidates'][1]['model'])
                model['training_window_start_max']=stamp
                model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
                entry['ref']=base_ref(self.root,entry['ref']['path'],json.dumps(model).encode())
                entry['model_sha256']=model['model_sha256'];self.f.publish()
                with self.assertRaises(ValueError):self.call()

    def test_lineage_global_source_received_equality_at_fit_is_not_qualified_early(self):
        path=next(iter(self.f.lineage['source_received_at']))
        self.f.lineage['source_received_at'][path]=self.f.profile['fit_cutoff']
        self.rewrite_lineage()
        # Bind both native declarations so no incidental hash/map mismatch masks
        # the strict temporal test.
        for c,entry in zip(self.f.prepared['candidates'],self.f.profile['models']):
            if c['candidate_id']=='uniform':continue
            model=copy.deepcopy(c['model']);model['source_received_at'][path]=self.f.profile['fit_cutoff']
            model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
            entry['artifact']['ref']=base_ref(self.root,entry['artifact']['ref']['path'],json.dumps(model).encode())
            entry['artifact']['model_sha256']=model['model_sha256']
            self.f.lineage['model_sha256_by_id'][c['candidate_id']]=model['model_sha256']
        self.rewrite_lineage()
        with self.assertRaises(ValueError):self.call()

    def test_consistent_late_model_readiness_blocks_after_full_g0_rescan(self):
        binding=self.f.profile['models'][2]['artifact']
        binding['readiness']['audited_at']=CUTOFF;binding['usable_at']=CUTOFF
        self.f.profile['usable_at']=CUTOFF;self.f.publish()
        seen=[];original=g0.G0ArtifactReader.rescan
        def observe(reader):seen.append(set(reader.refs));return original(reader)
        with patch.object(g0.G0ArtifactReader,'rescan',observe),self.assertRaises(self.module.ScoreSummarySourceBlocked):self.call()
        self.assertTrue(any('features/c1t1-validity.json' in paths for paths in seen))

    def partial_forecast(self):
        keep={'humidity_pct','precipitation_mm','road_length_m'};f=self.f.forecast
        f.features=[item for item in f.features if item['name'] in keep]
        for shard in f.manifest['shards']:
            sid=shard['shard_id'];snap=f.objects[f.nodes[sid+'-s']['ref']['path']]
            paths={ref['path'] for ref in snap['features'] if f.objects[ref['path']]['feature_name'] in keep}
            snap['features']=[ref for ref in snap['features'] if ref['path'] in paths];snap['feature_schema_sha256']=digest(sorted(keep))
            ids=[ident for ident,node in f.nodes.items() if node['ref']['path'] in paths]
            for ident in list(f.nodes):
                node=f.nodes[ident]
                if ident.startswith(sid+'-f') and node['ref']['path'] not in paths:del f.nodes[ident]
            f.nodes[sid+'-s']['parents']=[sid+'-u',*ids];f.nodes[sid+'-v']['parents']=ids
            sidecar=f.objects[f.nodes[sid+'-v']['ref']['path']]
            sidecar['feature_sources']={k:v for k,v in sidecar['feature_sources'].items() if k in keep}
            sidecar['rows']={rid:{k:v for k,v in row.items() if k in keep} for rid,row in sidecar['rows'].items()}
        f.manifest['features']=f.features;f.manifest['feature_definition_sha256']=definition_hash(f.features);f.publish()
        sha=definition_hash(f.features)
        self.f.source.config['feature_definition_sha256']=sha;self.f.source.profile['feature_definition_sha256']=sha;self.f.source.publish()
        self.f.profile.update(feature_definition_sha256=sha,candidate_config_manifest=self.f.source.ref,forecast_manifest=f.ref);self.f.publish()

    def test_valid_three_raw_features_block_whole_set_without_partial_or_imputation(self):
        self.partial_forecast();value=self.call()
        self.assertEqual(value['status'],'NEED_MORE_DATA');self.assertEqual(value['model_summaries'],[])
        self.assertEqual(value['forecast_receipt']['row_count'],4)

    def test_partial_raw_schema_does_not_hide_supplied_humidity101_in_last_unit(self):
        self.partial_forecast();f=self.f.forecast
        payload=f.objects[f.nodes['c1t1-f1']['ref']['path']]
        payload['values']={rid:101 for rid in payload['values']};f.publish()
        self.f.profile['forecast_manifest']=f.ref;self.f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_ref_ownership_parent_checks_do_not_mutate_original_binding(self):
        original=copy.deepcopy(self.f.ref);changed=[False]
        def mutate():
            if not changed[0]:self.f.ref['sha256']='f'*64;changed[0]=True
        value=self.call(check=mutate)
        self.assertEqual(value['source_manifest_ref'],original)

    def test_final_digest_expiry_and_model_mutation_before_rescan_publish_nothing(self):
        context=pi.ProspectiveReadContext(30,2*1024**3);actual=self.module._digest
        def expire(value,*args,**kwargs):
            result=actual(value,*args,**kwargs)
            if type(value) is dict and value.get('summary_kind')=='UNCONNECTED_DIAGNOSTIC_ONLY':context.deadline=-1
            return result
        with patch.object(self.module,'_digest',expire),self.assertRaises(TimeoutError):self.call(_read_context=context)
        self.assertGreater(context.bytes_read,0)
        original=self.module._ScoreReducer._rescan_metadata
        path=self.root/self.f.profile['models'][2]['artifact']['ref']['path']
        def mutate(reducer):path.write_bytes(b'{}');return original(reducer)
        with patch.object(self.module._ScoreReducer,'_rescan_metadata',mutate),self.assertRaises(ValueError):self.call()

    def test_code_bytes_recipe_and_preflight_reserved_namespace_are_real_guards(self):
        path=self.root/'src/models/hba1_feature_candidate.py';path.write_bytes(path.read_bytes()+b'\n# changed\n')
        with self.assertRaises(ValueError):self.call()
        self.f.profile['models'][0]['artifact']['ref']['path']='models/candidates/ORIGINAL./bad.json';self.f.publish()
        opened=[];original=Path.open
        def observe(path,*args,**kwargs):opened.append(str(path));return original(path,*args,**kwargs)
        with patch.object(Path,'open',observe),self.assertRaises(ValueError):self.call()
        self.assertFalse(any('ORIGINAL.' in path for path in opened))

    def test_combined_metadata_capacity_precedes_any_native_model_owned_copy(self):
        with patch.object(self.module,'MAX_METADATA_BYTES',128),patch.object(self.module,'_model',side_effect=AssertionError('native copy started')):
            with self.assertRaises(pi.InputCapacityError):self.call()

    def test_missing_lineage_cannot_hide_supplied_finite_model_arithmetic_overflow(self):
        self.f.profile['fit_lineage']=None
        model=copy.deepcopy(self.f.prepared['candidates'][2]['model']);model['coefficients']=[1e308]*8
        model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
        binding=self.f.profile['models'][2]['artifact'];binding['model_sha256']=model['model_sha256']
        binding['ref']=base_ref(self.root,binding['ref']['path'],json.dumps(model).encode());self.f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_actual_prior_byte_charges_deadline_and_context_identity_are_preserved(self):
        context=pi.ProspectiveReadContext(30,2*1024**3)
        g0.G0ArtifactReader(self.root,context).read(self.f.profile['models'][0]['artifact']['ref'],parse=False)
        before,deadline=context.bytes_read,context.deadline;seen=[];actual=g0.G0ArtifactReader.read
        def observe(reader,*args,**kwargs):seen.append(reader.context);return actual(reader,*args,**kwargs)
        with patch.object(g0.G0ArtifactReader,'read',observe):value=self.call(_read_context=context)
        self.assertTrue(all(item is context for item in seen));self.assertLessEqual(context.deadline,deadline)
        self.assertEqual(value['actual_read_bytes'],context.bytes_read)
        self.assertEqual(value['summary_read_bytes'],context.bytes_read-before)
        limited=pi.ProspectiveReadContext(30,100)
        with self.assertRaises(pi.InputCapacityError):self.call(_read_context=limited)
        self.assertEqual(limited.max_bytes,100);self.assertEqual(limited.bytes_read,101)

    def test_invalid_budget_huge_integer_is_value_error_without_open_or_overflow(self):
        for budget in (True,0,-1,301,float('nan'),float('inf'),10**1000):
            with self.subTest(budget=str(budget)[:20]),patch.object(Path,'open',side_effect=AssertionError('input opened')):
                with self.assertRaises(ValueError):self.call(budget_seconds=budget)

    def test_old_collector_caps_stay_enforced_and_summary_does_not_publish_rows(self):
        with patch.object(g0,'MAX_MODEL_ROWS',3):
            with self.assertRaises(pi.InputCapacityError):g0.load_g0_forecast_rows(self.root,self.f.forecast.ref,NIGHT,NOW,
                expected_feature_definition_sha256=self.f.profile['feature_definition_sha256'])
            value=self.call()
        self.assertEqual(value['status'],'COMPLETE_DECLARED_SCORE_SUMMARY')
        self.assertFalse({'rows','prediction','prepared','candidates','unit_predictions','unit_scores'}&set(value))

    def test_unsupported_b1_config_is_explicit_before_native_outcome_payloads(self):
        self.f.source.config['candidate_ids']=['uniform','HB-A0','HB-B1'];self.f.source.config['hba1_recipe']=None
        self.f.source.publish();self.f.profile['candidate_config_manifest']=self.f.source.ref
        self.f.profile['models'][2]=dict(candidate_id='HB-B1',artifact=None);self.f.publish()
        with self.assertRaisesRegex(g0.ForecastCapabilityError,'IMPLEMENTATION_BLOCKED'):self.call()

    def test_known_missing_readiness_schema_is_not_masked_by_an_absent_model_file(self):
        self.f.profile['readiness'].pop('audited_at')
        self.f.profile['models'][0]['artifact']['ref']['path']='models/candidates/absent.json';self.f.publish()
        with self.assertRaises(ValueError) as caught:self.call()
        self.assertNotIsInstance(caught.exception,self.module.ScoreSummarySourceBlocked)

    def test_shard_declaration_order_does_not_change_canonical_score_stream(self):
        before=self.call()
        self.f.forecast.manifest['shards'].reverse();self.f.forecast.publish()
        self.f.profile['forecast_manifest']=self.f.forecast.ref;self.f.publish()
        after=self.call()
        self.assertEqual(before['model_summaries'],after['model_summaries'])
        self.assertEqual(before['forecast_receipt']['canonical_joined_rows_sha256'],after['forecast_receipt']['canonical_joined_rows_sha256'])

    def test_real_missing_metadata_is_data_blocked_without_reclassifying_callback_errors(self):
        path=self.root/self.f.profile['models'][0]['artifact']['ref']['path'];path.unlink()
        with self.assertRaises(self.module.ScoreSummarySourceBlocked):self.call()

    def test_same_file_not_found_callback_instance_survives_reader_proof_and_final_rescan(self):
        for stage in ('reader','proof','final-rescan'):
            marker=FileNotFoundError('caller cancellation '+stage);active=[False]
            def parent():
                if active[0]:raise marker
            if stage=='reader':
                original=g0.G0ArtifactReader.read
                def observe(reader,ref,**kwargs):
                    active[0]=ref['path'].startswith('models/candidates/')
                    try:return original(reader,ref,**kwargs)
                    finally:active[0]=False
                target=patch.object(g0.G0ArtifactReader,'read',observe)
            elif stage=='proof':
                original=self.module._lineage
                def observe(*args,**kwargs):
                    active[0]=True
                    try:return original(*args,**kwargs)
                    finally:active[0]=False
                target=patch.object(self.module,'_lineage',observe)
            else:
                original=g0.G0ArtifactReader.rescan
                def observe(reader):
                    active[0]=any(path.startswith('models/candidates/') for path in reader.refs)
                    try:return original(reader)
                    finally:active[0]=False
                target=patch.object(g0.G0ArtifactReader,'rescan',observe)
            with self.subTest(stage=stage),target,self.assertRaises(FileNotFoundError) as caught:self.call(check=parent)
            self.assertIs(caught.exception,marker)

    def test_caller_exception_identity_at_final_hash_and_sealed_encoding(self):
        for stage in ('hash','sealed-encoding'):
            for exception_type in (ValueError,OverflowError,TimeoutError,KeyboardInterrupt):
                marker=exception_type('caller '+stage);active=[False]
                def parent():
                    if active[0]:raise marker
                name='_digest' if stage=='hash' else '_encoded';original=getattr(self.module,name)
                def observe(value,*args,**kwargs):
                    active[0]=(type(value) is dict and value.get('summary_kind')=='UNCONNECTED_DIAGNOSTIC_ONLY' and
                        (stage=='hash' or 'summary_sha256' in value))
                    try:return original(value,*args,**kwargs)
                    finally:active[0]=False
                with self.subTest(stage=stage,exception=exception_type.__name__),patch.object(self.module,name,observe),self.assertRaises(exception_type) as caught:
                    self.call(check=parent)
                self.assertIs(caught.exception,marker)


class ExactMeanTests(unittest.TestCase):
    def test_exact_accumulator_matches_statistics_mean_including_ulp_subnormal_zero(self):
        module=importlib.import_module('g0_full_universe_score_summary')
        accumulator=getattr(module,'_ExactMean',None)
        self.assertTrue(callable(accumulator),'bounded exact native mean state is missing')
        for values in ([1.0,2**-53,2**-53],[5e-324,0.0],[-0.0,0.0],[0.1,0.2,0.8,1.0]):
            state=accumulator(lambda:None)
            for value in values:state.add(value)
            self.assertEqual(state.value(),mean(values))
        with patch.object(module,'MAX_SUM_BITS',5),self.assertRaises(pi.InputCapacityError):accumulator(lambda:None).add(1.0)


if __name__ == '__main__':unittest.main()
