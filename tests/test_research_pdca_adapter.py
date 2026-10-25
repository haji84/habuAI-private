"""End-to-end synthetic declarations; no real observations or accuracy evidence."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from master_contracts import canonical_bytes, digest, validate_adapter_result
import test_g0_training_source_contract as training_fixtures
from test_g0_forecast_contract import SyntheticContract, definition_hash, NIGHT, NOW, CUTOFF, base_ref


class ResearchPDCAAdapterTests(unittest.TestCase):
    def setUp(self):
        self.training = training_fixtures.TrainingSourceContractTests()
        self.training.setUp()
        self.addCleanup(self.training.doCleanups)
        self.root = self.training.root
        self.forecast = SyntheticContract(self.root)
        f = self.forecast
        f.features[:] = copy.deepcopy(self.training.features)
        f.manifest['feature_definition_sha256'] = definition_hash(f.features)
        node = f.nodes.pop('weather')
        node.update(id='road-source', source_kind='static')
        f.nodes['road-source'] = node
        f.objects[node['ref']['path']]['source_kind'] = 'static'
        for item in f.nodes.values():
            item['parents'] = ['road-source' if p == 'weather' else p for p in item['parents']]
            obj = f.objects[item['ref']['path']]
            if item['source_kind'] == 'feature_values':
                obj.update(feature_name='road_length_m', use_role='static_predictor')
            elif item['source_kind'] == 'snapshot':
                obj['feature_schema_sha256'] = digest(['road_length_m'])
            elif item['source_kind'] == 'validity':
                obj['feature_sources'] = {'road_length_m': obj['feature_sources']['rain_3h_mm']}
                for row in obj['rows'].values():
                    row['road_length_m'] = row.pop('rain_3h_mm')
        f.publish()
        self.request = dict(schema_version='habu-research-model-request-v1', mode='DEVELOPMENT_ONLY',
            operational_night=NIGHT, fit_cutoff='2026-10-13T18:00:00+09:00',
            forecast_as_of=NOW.isoformat(), forecast_cutoff=CUTOFF,
            feature_definition_sha256=definition_hash(f.features),
            training_manifest=self.training.ref, forecast_manifest=f.ref, exposed_nights=[])
        self.publish()

    def publish(self):
        base_ref(self.root, 'config/research-model-request.json', canonical_bytes(self.request))

    def call(self, **kwargs):
        from research_pdca_adapter import evaluate_research_request
        return evaluate_research_request(self.root, NIGHT, **kwargs)

    def test_actual_file_loader_prepares_three_candidates_and_immutable_replay(self):
        result = self.call()
        self.assertEqual([c['candidate_id'] for c in result['candidates']], ['uniform', 'HB-A0', 'HB-B1'])
        rows = validate_adapter_result(result, ('model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation'))
        self.assertEqual(rows['candidate_generation']['status'], 'PASS')
        self.assertEqual(rows['candidate_validation']['status'], 'BLOCKED')
        self.assertEqual(result['decision']['decision'], 'NEED_MORE_DATA')
        self.assertFalse(result['production_activation_authorized'])
        self.assertFalse(result['scientific_fit_authorized'])
        self.assertEqual(len(result['replay']), 1)
        replay = result['replay'][0]
        payload = (self.root / replay['path']).read_bytes()
        self.assertEqual(digest(json.loads(payload)), replay['content_sha256'])
        self.assertEqual(self.call()['replay'], result['replay'])
        (self.root / replay['path']).write_bytes(b'corrupted')
        self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')

    def test_dispatch_never_opens_legacy_or_sealed_confirmation(self):
        from model_evaluation import evaluate_models
        sealed = self.root / 'sealed/confirmation/labels.json'
        sealed.parent.mkdir(parents=True)
        sealed.write_bytes(b'no reading allowed')
        actual = Path.open
        def observe(path, *args, **kwargs):
            if 'sealed' in path.parts or path.name == 'model_learning.json':
                raise AssertionError('Legacy or sealed confirmation was opened')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', new=observe), patch('model_evaluation._validate', side_effect=AssertionError('legacy validation')):
            self.assertEqual(len(evaluate_models(self.root, NIGHT)['candidates']), 3)

    def test_legacy_evaluation_does_not_import_optional_research_adapter(self):
        from model_evaluation import evaluate_models, MissingEvidence
        (self.root / 'config/research-model-request.json').unlink()
        with patch.dict(sys.modules, {'research_pdca_adapter': None}), patch('model_evaluation._validate', side_effect=MissingEvidence('no legacy snapshot')):
            result = evaluate_models(self.root, NIGHT)
        self.assertEqual(result['stages'][0]['status'], 'BLOCKED')

    def test_missing_sources_block_without_replay_and_bad_refs_fail_closed(self):
        (self.root / self.training.ref['path']).unlink()
        result = self.call()
        self.assertEqual(result['stages'][0]['status'], 'BLOCKED')
        self.assertEqual(result['decision']['decision'], 'NEED_MORE_DATA')
        self.assertEqual(result['replay'], [])
        self.request['training_manifest']['path'] = 'sealed/confirmation/labels.json'
        self.publish()
        self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')

    def test_insufficient_qualified_classes_return_need_more_data_without_invented_zeros(self):
        f = self.training.fixture
        f.rows[:] = f.rows[:1]
        f.publish()
        self.training.build_manifest()
        self.request['training_manifest'] = self.training.ref
        self.publish()
        with patch('research_model_adapter.fit_shrinkage', side_effect=AssertionError('insufficient fit')):
            result = self.call()
        self.assertEqual(result['decision']['decision'], 'NEED_MORE_DATA')
        self.assertEqual(result['stages'][0]['status'], 'BLOCKED')
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['replay'], [])

    def test_excessive_json_nesting_returns_invalid_result(self):
        raw = b'{"nested":' * 5000 + b'0' + b'}' * 5000
        base_ref(self.root, 'config/research-model-request.json', raw)
        self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')

    def test_exposed_nights_requires_a_unique_json_array_of_actual_nights(self):
        for bad in ({}, '', {'2026-09-10': True}, [1], ['2026-09-10', '2026-09-10']):
            self.request['exposed_nights'] = bad
            self.publish()
            with self.subTest(bad=bad), patch('research_model_adapter.prepare_research_candidates', side_effect=AssertionError('invalid request reached fit')):
                result = self.call()
                self.assertEqual(result['stages'][0]['status'], 'FAIL')
                self.assertEqual(result['candidates'], [])

    def test_replay_reuse_reports_all_actual_verified_read_bytes(self):
        from prospective_inputs import ProspectiveReadContext
        self.call()
        context = ProspectiveReadContext(300, 2 * 1024**3)
        result = self.call(_read_context=context)
        self.assertEqual(result['evidence']['actual_read_bytes'], context.bytes_read)

    def test_late_request_binding_or_definition_mismatch_never_fits(self):
        import research_model_adapter
        for key, value in [('forecast_cutoff', NIGHT + 'T17:00:00+09:00'),
                           ('feature_definition_sha256', 'f' * 64), ('operational_night', '2026-10-15')]:
            original = self.request[key]
            self.request[key] = value
            self.publish()
            with patch.object(research_model_adapter, 'prepare_research_candidates', side_effect=AssertionError('fit was reached')):
                self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')
            self.request[key] = original

    def test_nested_forecast_source_cannot_open_sealed_payload(self):
        node = self.forecast.nodes['road-source']
        node['ref']['path'] = 'features/sealed/confirmation/secret.json'
        self.forecast.manifest_only()
        self.request['forecast_manifest'] = self.forecast.ref
        self.publish()
        actual = Path.open
        def observe(path, *args, **kwargs):
            if 'sealed' in path.parts:
                raise AssertionError('nested sealed payload opened')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', new=observe):
            self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')

    def test_training_mutation_during_model_preparation_is_rechecked_before_publish(self):
        import research_model_adapter
        actual = research_model_adapter.prepare_research_candidates
        def mutate(*args, **kwargs):
            prepared = actual(*args, **kwargs)
            (self.root / 'features/road-source.txt').write_bytes(b'changed after training gate')
            return prepared
        with patch.object(research_model_adapter, 'prepare_research_candidates', side_effect=mutate):
            result = self.call()
        self.assertEqual(result['stages'][0]['status'], 'FAIL')
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['replay'], [])

    def test_one_read_ledger_and_deadline_span_both_gates_and_no_partial_replay(self):
        from prospective_inputs import ProspectiveReadContext
        context = ProspectiveReadContext(30, 10)
        result = self.call(_read_context=context)
        self.assertEqual(result['stages'][0]['blocker_kind'], 'RUNTIME_BLOCKED')
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['replay'], [])
        self.assertGreater(context.bytes_read, 10)

    def test_final_stage_construction_cannot_release_candidates_after_expiry(self):
        import research_pdca_adapter as adapter
        from prospective_inputs import ProspectiveReadContext
        context = ProspectiveReadContext(300, 2 * 1024**3)
        actual = adapter.stage
        def expire(name, *args, **kwargs):
            value = actual(name, *args, **kwargs)
            if name == 'candidate_validation':
                context.deadline = 0
            return value
        with patch.object(adapter, 'stage', side_effect=expire):
            result = self.call(_read_context=context)
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['replay'], [])
        self.assertTrue(all(s['status'] == 'BLOCKED' for s in result['stages']))

    @unittest.skipIf(os.name == 'nt', 'Actual master lock requires POSIX fcntl; Ubuntu CI executes this test')
    def test_master_dispatch_uses_request_before_legacy_builder_in_actual_snapshot(self):
        from master_orchestrator import run_master
        sealed = self.root / 'sealed/confirmation/labels.json'
        sealed.parent.mkdir(parents=True)
        sealed.write_bytes(b'canonical sealed file must remain unread by inventory and parent')
        actual = Path.open
        def observe(path, *args, **kwargs):
            if 'sealed' in path.parts:
                raise AssertionError('parent read sealed confirmation')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', new=observe), patch('learning_snapshot.build_learning_snapshot', side_effect=AssertionError('legacy builder reached')):
            result = run_master(self.root, NIGHT)
        candidates = next(s for s in result['stages'] if s['name'] == 'candidate_generation')
        self.assertEqual(candidates['status'], 'PASS', str(result))
        self.assertFalse(result['completed'])
        self.assertNotEqual(result['overall_status'], 'PASS')


class ResearchConfigV3Tests(unittest.TestCase):
    def setUp(self):
        self.parent=ResearchPDCAAdapterTests()
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.root=self.parent.root
        from test_research_candidate_config_source import ConfigSourceFixture
        self.source=ConfigSourceFixture(self.root,self.parent.request['feature_definition_sha256'])
        self.source.config.update(candidate_ids=['uniform','HB-A0','HB-B1'],hba1_recipe=None)
        self.source.publish()
        self.parent.request.update(schema_version='habu-research-model-request-v3',
            candidate_config_manifest=self.source.ref,stage1_manifest=None)
        self.parent.publish()

    def update_source(self):
        self.source.publish()
        self.parent.request['candidate_config_manifest']=self.source.ref
        self.parent.publish()

    def full_seven_fixture(self):
        """Actual strict loaders, entirely synthetic row/source declarations."""
        import hashlib
        import prospective_candidate_model as legacy
        from test_prospective_candidate_model import history_rows
        from test_hba1_feature_candidate import recipe
        train=self.parent.training
        corpus=train.fixture
        templates={row['label']:copy.deepcopy(row) for row in corpus.rows}
        rows=[]
        for index,original in enumerate(history_rows()[:20]):
            label=1 if original['owner_capture_count'] else 0
            row=copy.deepcopy(templates[label])
            for name in ('active_search_ref','complete_outcome_ref'):row.pop(name,None)
            prior_night=f'2026-09-{20+index//4:02d}'
            row.update(row_id=f'full-{index}',night=prior_night,
                cell_x=5000+index,window_start_jst=prior_night+original['window_start_jst'][10:],
                capture_event_ids=[f'full-event-{index}'] if label else [],
                source_refs=['evidence/source_receipt.txt','features/road-source.txt'],
                features={name:original[name] for name in legacy.FEATURES},
                feature_source_refs={name:['features/road-source.txt'] for name in legacy.FEATURES},
                feature_available_at={name:'2026-09-30T12:00:00+09:00' for name in legacy.FEATURES})
            if not label:corpus.add_negative_proofs(row)
            rows.append(row)
        corpus.rows[:]=rows
        corpus.publish()
        template=copy.deepcopy(train.features[0])
        train.features[:]=[]
        for name in legacy.FEATURES:
            feature=copy.deepcopy(template)
            definition='Synthetic static software fixture for '+name
            feature.update(name=name,units='declared-fixture-unit',definition=definition,
                definition_sha256=hashlib.sha256(definition.encode()).hexdigest())
            train.features.append(feature)
        train.build_manifest()
        f=self.parent.forecast
        f.features[:]=copy.deepcopy(train.features)
        for sid in f.snapshots:
            prefix=sid[:-2]
            original_node=f.nodes[prefix+'-f']
            original_value=f.objects[original_node['ref']['path']]
            rid=next(iter(original_value['values']))
            original_value['values'][rid]=12.0
            snapshot=f.objects[f.nodes[sid]['ref']['path']]
            validity=f.objects[f.nodes[prefix+'-v']['ref']['path']]
            for name in legacy.FEATURES:
                if name=='road_length_m':continue
                node_id=prefix+'-f-'+name
                value=dict(original_value,feature_name=name,values={rid:rows[0]['features'][name]})
                path=f'features/{node_id}.json'
                f.add(node_id,path,'feature_values','feature',['road-source'],value)
                snapshot['features'].append(dict(path=path))
                f.nodes[sid]['parents'].append(node_id)
                validity['feature_sources'][name]=[node_id]
                validity['rows'][rid][name]=f.valid.copy()
                f.nodes[prefix+'-v']['parents'].append(node_id)
            snapshot['feature_schema_sha256']=digest(sorted(legacy.FEATURES))
        f.manifest['feature_definition_sha256']=definition_hash(f.features)
        f.publish()
        self.source.config.update(candidate_ids=['uniform','HB-A0','HB-A1'],hba1_recipe=recipe(),
            feature_definition_sha256=definition_hash(f.features))
        self.source.profile['feature_definition_sha256']=definition_hash(f.features)
        self.parent.request.update(training_manifest=train.ref,forecast_manifest=f.ref,
            feature_definition_sha256=definition_hash(f.features))
        self.update_source()

    def test_full_seven_a1_uses_actual_source_loaders_and_blocks_unregistered_stage1(self):
        self.full_seven_fixture()
        self.parent.request['stage1_manifest']=dict(path='evidence/stage1/must-not-open.json',sha256='a'*64,size_bytes=1)
        self.parent.publish()
        actual=Path.open
        def opening(path,*args,**kwargs):
            if path.name=='must-not-open.json':raise AssertionError('A1 used unregistered Stage1')
            return actual(path,*args,**kwargs)
        with patch.object(Path,'open',new=opening):result=self.parent.call()
        self.assertEqual([c['candidate_id'] for c in result['candidates']],['uniform','HB-A0','HB-A1'],str(result))
        self.assertEqual(result['stage1_dispatch']['status'],'IMPLEMENTATION_BLOCKED')
        self.assertEqual(result['stages'][-1]['blocker_kind'],'IMPLEMENTATION_BLOCKED')
        self.assertEqual(len(result['replay']),1)
        self.assertEqual(result['evidence']['request_ref']['path'],'config/research-model-request.json')
        self.assertEqual(result['candidates'][-1]['forecast_units'],4)
        self.assertEqual(result['decision']['decision'],'NEED_MORE_DATA')

    def test_v3_source_bound_old_triplet_prepares_complete_replay_without_evaluation(self):
        with patch('evaluation.stage1_source_adapter.evaluate_stage1_sources',side_effect=AssertionError('unrequested evaluation')):
            result=self.parent.call()
        self.assertEqual([c['candidate_id'] for c in result['candidates']],['uniform','HB-A0','HB-B1'],str(result))
        self.assertEqual(result['stage1_dispatch']['status'],'NOT_REQUESTED')
        self.assertEqual(len(result['replay']),1)
        payload=json.loads((self.root/result['replay'][0]['path']).read_bytes())
        self.assertEqual(payload['schema_version'],'habu-research-model-request-v3')
        self.assertEqual(payload['prepared']['schema_version'],'habu-research-candidates-prepared-v2')
        self.assertEqual(payload['prepared']['candidate_config_sha256'],digest(self.source.config))
        self.assertEqual(payload['prepared']['implementation_blockers'],[
            'CONFIGURED_STAGE1_SOURCE_PARENT_NOT_CONNECTED',
            'TRUSTED_CUMULATIVE_CAMPAIGN_LEDGER_NOT_IMPLEMENTED',
            'TRUSTED_PRE_REVEAL_FREEZE_AND_CONSUMPTION_LEDGER_NOT_IMPLEMENTED',
            'MODEL_COMPARISON_AND_WINNER_SELECTION_NOT_IMPLEMENTED'])
        self.assertEqual(payload['candidate_config_source']['config_sha256'],digest(self.source.config))
        self.assertFalse(result['official_issuance_authorized'])

    def test_nonlegacy_order_blocks_stage1_before_manifest_read_and_retains_frozen_set(self):
        self.source.config['candidate_ids']=['uniform','HB-B1','HB-A0']
        self.update_source()
        forbidden=base_ref(self.root,'evidence/stage1/unread.json',b'not JSON, must remain unopened')
        self.parent.request['stage1_manifest']=forbidden
        self.parent.publish()
        actual=Path.open
        def opening(path,*args,**kwargs):
            if path.name=='unread.json':raise AssertionError('unsupported registry opened evaluation manifest')
            return actual(path,*args,**kwargs)
        with patch.object(Path,'open',new=opening):result=self.parent.call()
        self.assertEqual(len(result['candidates']),3,str(result))
        self.assertEqual(len(result['replay']),1)
        self.assertEqual(result['stage1_dispatch']['status'],'IMPLEMENTATION_BLOCKED')
        self.assertEqual(result['decision']['decision'],'NEED_MORE_DATA')
        payload=json.loads((self.root/result['replay'][0]['path']).read_bytes())
        self.assertEqual(payload['prepared']['candidate_ids'],['uniform','HB-B1','HB-A0'])
        self.assertEqual(payload['prepared']['receipt_sha256'],digest({k:v for k,v in payload['prepared'].items() if k!='receipt_sha256'}))

    def test_old_exact_order_can_reuse_stage1_after_prediction_freeze(self):
        from test_stage1_source_adapter import SourceFixture
        fixture=SourceFixture(self.parent)
        self.parent.request.update(schema_version='habu-research-model-request-v3',stage1_manifest=fixture.ref)
        self.parent.publish()
        import research_model_adapter as models
        actual_prepare,actual_open=models.prepare_research_candidates_v2,Path.open
        hashes=[]
        def prepare(*args,**kwargs):
            prepared=actual_prepare(*args,**kwargs)
            hashes.append(prepared['receipt_sha256'])
            return prepared
        def opening(path,*args,**kwargs):
            if path.name in ('captures.csv','individuals.csv','coverage.json'):
                self.assertTrue(hashes,'Stage1 read before all3 prediction freeze')
            return actual_open(path,*args,**kwargs)
        with patch.object(models,'prepare_research_candidates_v2',side_effect=prepare),patch.object(Path,'open',new=opening):
            result=self.parent.call()
        self.assertEqual(len(result['candidates']),3,str(result))
        self.assertEqual(result['stage1_diagnostic']['pooled']['uniform']['denominator'],3)
        self.assertEqual(result['stage1_dispatch']['status'],'DIAGNOSTIC_ONLY')

    def test_a1_missing_schema_blocks_whole_set_without_partial_models_or_evaluation(self):
        from test_hba1_feature_candidate import recipe
        self.source.config.update(candidate_ids=['uniform','HB-A0','HB-A1'],hba1_recipe=recipe())
        self.update_source()
        self.parent.request['stage1_manifest']=dict(path='evidence/stage1/unread.json',sha256='a'*64,size_bytes=1)
        self.parent.publish()
        with patch('research_model_adapter.fit_shrinkage',side_effect=AssertionError('partial fit')):
            result=self.parent.call()
        self.assertEqual(result['stages'][0]['status'],'BLOCKED',str(result))
        self.assertEqual((result['candidates'],result['replay']),([],[]))
        self.assertEqual(result['decision']['decision'],'NEED_MORE_DATA')

    def test_invalid_or_late_config_cannot_reach_fit_or_any_stage1_manifest(self):
        self.parent.request['stage1_manifest']=dict(path='evidence/stage1/must-stay-unread.json',sha256='a'*64,size_bytes=1)
        for mode in ('invalid','late'):
            self.source.publish()
            if mode=='invalid':self.source.profile['candidate_config']['config_sha256']='e'*64
            else:
                stamp=self.parent.request['fit_cutoff']
                self.source.profile['readiness']['audited_at']=stamp
                self.source.profile['usable_at']=stamp
            self.source.profile_only()
            self.parent.request['candidate_config_manifest']=self.source.ref
            self.parent.publish()
            with self.subTest(mode=mode),patch('research_model_adapter.prepare_research_candidates_v2',side_effect=AssertionError('invalid config fit')):
                result=self.parent.call()
            self.assertEqual(result['stages'][0]['status'],'FAIL' if mode=='invalid' else 'BLOCKED',str(result))
            self.assertEqual(result['candidates'],[])

    def test_missing_code_is_data_blocked_before_fit_and_nested_reserved_training_never_opens(self):
        (self.root/'scripts/synthetic.py').unlink()
        with patch('research_model_adapter.prepare_research_candidates_v2',side_effect=AssertionError('missing code fit')):
            result=self.parent.call()
        self.assertEqual(result['stages'][0]['blocker_kind'],'DATA_BLOCKED',str(result))
        base_ref(self.root,'scripts/synthetic.py',b'restored')
        self.update_source()
        train=self.parent.training
        train.manifest['source_nodes'][0]['ref']['path']='evidence/ORIGINAL/must-not-read.txt'
        train.publish()
        self.parent.request['training_manifest']=train.ref
        self.parent.publish()
        actual=Path.open
        def opening(path,*args,**kwargs):
            if 'ORIGINAL' in path.parts:raise AssertionError('reserved training payload opened')
            return actual(path,*args,**kwargs)
        with patch.object(Path,'open',new=opening):result=self.parent.call()
        self.assertEqual(result['stages'][0]['status'],'FAIL',str(result))

    def test_post_stage_construction_source_mutation_is_rechecked_before_publish(self):
        import research_pdca_adapter as adapter
        original=adapter.stage
        def stage(name,*args,**kwargs):
            item=original(name,*args,**kwargs)
            if name=='candidate_validation':(self.root/'features/road-source.txt').write_bytes(b'late change')
            return item
        with patch.object(adapter,'stage',side_effect=stage):result=self.parent.call()
        self.assertEqual(result['stages'][0]['status'],'FAIL',str(result))
        self.assertEqual((result['candidates'],result['replay']),([],[]))

    def test_failed_v3_publication_cannot_release_a_diagnostic_stage1_status(self):
        from test_stage1_source_adapter import SourceFixture
        fixture=SourceFixture(self.parent)
        self.parent.request.update(schema_version='habu-research-model-request-v3',stage1_manifest=fixture.ref)
        self.parent.publish()
        with patch('research_pdca_adapter._publish',side_effect=TimeoutError('late publication')):
            result=self.parent.call()
        self.assertEqual((result['candidates'],result['replay']),([],[]))
        self.assertNotIn('stage1_diagnostic',result)
        self.assertNotIn('stage1_dispatch',result)

    def test_runtime_code_mutation_during_fit_rejects_before_publication(self):
        import research_model_adapter as models
        actual=models.prepare_research_candidates_v2
        def prepare(*args,**kwargs):
            prepared=actual(*args,**kwargs)
            (self.root/'scripts/synthetic.py').write_bytes(b'changed code')
            return prepared
        with patch.object(models,'prepare_research_candidates_v2',side_effect=prepare):result=self.parent.call()
        self.assertEqual(result['stages'][0]['status'],'FAIL',str(result))
        self.assertEqual((result['candidates'],result['replay']),([],[]))

    def test_shared_parent_guard_reaches_pure_v2_and_actual_reads_are_cumulative(self):
        import research_model_adapter as models
        from prospective_inputs import ProspectiveReadContext
        context=ProspectiveReadContext(300,2*1024**3)
        original=models.prepare_research_candidates_v2
        def prepare(*args,**kwargs):
            self.assertTrue(callable(kwargs.get('check')),'parent deadline is not propagated')
            self.assertLessEqual(kwargs['budget_seconds'],context.remaining_seconds+1)
            return original(*args,**kwargs)
        with patch.object(models,'prepare_research_candidates_v2',side_effect=prepare):result=self.parent.call(_read_context=context)
        self.assertEqual(len(result['candidates']),3,str(result))
        self.assertEqual(result['evidence']['actual_read_bytes'],context.bytes_read)

    def test_expiry_while_remaining_budget_is_computed_is_runtime_not_invalid(self):
        import g0_forecast_contract as g0
        import prospective_inputs as pi
        context=pi.ProspectiveReadContext(300,2*1024**3)
        actual=g0.load_g0_forecast_rows
        def load(*args,**kwargs):
            forecast=actual(*args,**kwargs)
            context.deadline=300
            calls=[]
            def clock():
                calls.append(True)
                return 0 if len(calls)==1 else 301
            clock_patch=patch.object(pi,'monotonic',side_effect=clock)
            clock_patch.start()
            self.addCleanup(clock_patch.stop)
            return forecast
        with patch.object(g0,'load_g0_forecast_rows',side_effect=load):result=self.parent.call(_read_context=context)
        self.assertEqual(result['stages'][0]['blocker_kind'],'RUNTIME_BLOCKED',str(result))
        self.assertEqual((result['candidates'],result['replay']),([],[]))

    def test_v3_final_publication_expiry_removes_only_owned_replay(self):
        import research_pdca_adapter as adapter
        from prospective_inputs import ProspectiveReadContext
        context=ProspectiveReadContext(300,2*1024**3)
        original=adapter._publish
        paths=[]
        def publish(*args,**kwargs):
            replay=original(*args,**kwargs)
            paths.append(self.root/replay['path'])
            context.deadline=0
            return replay
        with patch.object(adapter,'_publish',side_effect=publish):result=self.parent.call(_read_context=context)
        self.assertTrue(paths,'no native publication exercised')
        self.assertTrue(all(not path.exists() for path in paths))
        self.assertEqual((result['candidates'],result['replay']),([],[]))


if __name__ == '__main__':
    unittest.main()
