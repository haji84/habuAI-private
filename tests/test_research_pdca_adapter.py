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


class ResearchConfigV4Tests(unittest.TestCase):
    """Actual source-backed synthetic execution, without issuer/science authority."""
    def setUp(self):
        from test_stage1_configured_source_adapter import ConfiguredSourceFixture
        self.fixture = ConfiguredSourceFixture(self)
        self.parent, self.root = self.fixture.parent, self.fixture.root
        self.full_recipe = copy.deepcopy(self.fixture.config['hba1_recipe'])
        self.publish()

    def publish(self):
        self.fixture.case.update_source()
        self.fixture.source.publish()
        self.fixture.publish()
        self.parent.request.update(schema_version='habu-research-model-request-v4',
            candidate_config_manifest=self.fixture.case.source.ref,
            stage1_manifest=self.fixture.source.ref)
        self.parent.publish()

    def choices(self, ids):
        self.fixture.config.update(candidate_ids=list(ids),
            hba1_recipe=copy.deepcopy(self.full_recipe) if 'HB-A1' in ids else None)
        self.publish()

    def assert_failed(self, result, *, runtime=False):
        self.assertEqual((result['candidates'], result['replay']), ([], []), str(result))
        self.assertNotIn('stage1_diagnostic', result)
        self.assertNotIn('stage1_dispatch', result)
        self.assertTrue(all(s['status'] == ('BLOCKED' if runtime else 'FAIL') for s in result['stages']), str(result))
        if runtime:
            self.assertTrue(all(s['blocker_kind'] == 'RUNTIME_BLOCKED' for s in result['stages']), str(result))
        self.assertEqual(list((self.root/'predictions/replay').rglob('*.json')), [])

    def test_v4_all_six_orders_use_actual_v2_source_metrics_and_one_replay(self):
        import itertools
        for optional in itertools.permutations(('HB-A0', 'HB-B1', 'HB-A1'), 2):
            ids = ['uniform', *optional]
            self.choices(ids)
            result = self.parent.call()
            self.assertEqual([c['candidate_id'] for c in result['candidates']], ids, str(result))
            diagnostic = result['stage1_diagnostic']
            self.assertEqual(diagnostic['candidate_ids'], ids)
            self.assertEqual(diagnostic['source_summary'], dict(capture_events=2, individuals=3))
            self.assertEqual(diagnostic['per_night'][0]['outside_universe_individuals'], 1)
            self.assertEqual(diagnostic['paired_uncertainty']['replicates'], 2000)
            self.assertEqual(diagnostic['paired_uncertainty']['seed'], 0)
            for scores in diagnostic['pooled'].values():
                self.assertEqual((scores['numerator'], scores['denominator']), (2, 3))
            for key in ('official_threshold_pass', 'selection_authorized', 'promotion_authorized',
                        'confirmation_authorized', 'production_authorized'):
                self.assertIs(diagnostic[key], False)
            dispatch = result['stage1_dispatch']
            self.assertEqual(set(dispatch), {'status','registry','source_contract_version','candidate_config_sha256',
                'feature_definition_sha256','candidate_ids','trusted_pre_reveal_authorized','trusted_campaign_authorized',
                'source_issuer_authenticated','loaded_bytecode_authenticated','confirmation_authorized'})
            self.assertEqual(dispatch['status'], 'DIAGNOSTIC_ONLY')
            self.assertEqual(dispatch['registry'], 'habu-stage1-scores-v2')
            self.assertEqual(dispatch['source_contract_version'], 'habu-stage1-source-contract-v2')
            self.assertEqual(dispatch['candidate_config_sha256'], digest(self.fixture.config))
            self.assertEqual(dispatch['candidate_ids'], ids)
            self.assertEqual(result['decision']['decision'], 'NEED_MORE_DATA')
            self.assertEqual(result['stages'][-1]['status'], 'BLOCKED')
            self.assertEqual(len(result['replay']), 1)
            payload = json.loads((self.root/result['replay'][0]['path']).read_bytes())
            self.assertEqual(payload['schema_version'], 'habu-research-model-request-v4')
            self.assertEqual(payload['stage1_diagnostic'], diagnostic)
            self.assertEqual(payload['parent_dispatch']['status'], 'CONFIG_SOURCE_STAGE1_V4_SOFTWARE_ONLY')
            prepared = payload['prepared']
            self.assertEqual(prepared['receipt_sha256'], digest({k:v for k,v in prepared.items() if k!='receipt_sha256'}))
            self.assertIn('CONFIGURED_STAGE1_SOURCE_PARENT_NOT_CONNECTED', prepared['implementation_blockers'])
            # Standalone comparison uses the same production API, with an
            # independent transport invocation; numeric expectations above are literal.
            standalone = self.fixture.evaluate()
            self.assertEqual(diagnostic['input_digests'], standalone['input_digests'])
            self.assertEqual(diagnostic['pooled'], standalone['pooled'])

    def test_v4_null_stage1_never_opens_evaluation(self):
        self.parent.request['stage1_manifest'] = None
        self.parent.publish()
        actual = Path.open
        def opening(path, *args, **kwargs):
            if 'stage1' in path.parts: raise AssertionError('Null Stage1 opened evaluation')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', new=opening): result = self.parent.call()
        self.assertEqual(len(result['candidates']), 3, str(result))
        self.assertEqual(result['stage1_dispatch']['status'], 'NOT_REQUESTED')
        self.assertNotIn('stage1_diagnostic', result)
        self.assertEqual(len(result['replay']), 1)

    def test_v4_insufficient_training_keeps_no_partial_set_or_evaluation(self):
        training = self.parent.training
        training.fixture.rows[:] = training.fixture.rows[:2]
        training.fixture.publish(); training.build_manifest()
        self.parent.request['training_manifest'] = training.ref
        self.parent.publish()
        actual = Path.open
        def opening(path,*a,**kw):
            if 'stage1' in path.parts: raise AssertionError('Insufficient TRAIN opened evaluation')
            return actual(path,*a,**kw)
        with patch.object(Path,'open',new=opening): result = self.parent.call()
        self.assertEqual((result['candidates'],result['replay']),([],[]))
        self.assertNotIn('stage1_diagnostic',result)
        self.assertTrue(all(s['blocker_kind']=='DATA_BLOCKED' for s in result['stages']),str(result))
        self.assertEqual(result['decision']['decision'],'NEED_MORE_DATA')
        self.assertEqual(list((self.root/'predictions/replay').rglob('*.json')),[])

    def test_v4_unknown_incomplete_and_missing_references_keep_empty_metrics(self):
        for missing in ('UNKNOWN', 'INCOMPLETE', 'null-root', 'missing-csv'):
            with self.subTest(missing=missing):
                self.fixture.source.manifest['coverage_id'] = 'coverage'
                self.fixture.source.coverage['declaration'] = missing if missing in ('UNKNOWN','INCOMPLETE') else 'DECLARED_COMPLETE'
                self.publish()
                if missing == 'null-root':
                    self.fixture.source.manifest['coverage_id'] = None
                    self.fixture.source.nodes.pop('coverage')
                    self.fixture.source.manifest_only()
                    self.parent.request.update(schema_version='habu-research-model-request-v4', stage1_manifest=self.fixture.source.ref)
                    self.parent.publish()
                elif missing == 'missing-csv':
                    (self.root/self.fixture.source.nodes['captures']['ref']['path']).unlink()
                result = self.parent.call()
                self.assertEqual(len(result['candidates']), 3, str(result))
                self.assertEqual(len(result['replay']), 1)
                d = result['stage1_diagnostic']
                self.assertEqual((d['status'], d['per_night'], d['pooled'], d['paired_uncertainty']),
                                 ('NEED_MORE_DATA', [], {}, {}))

    def test_v4_stage1_v1_payload_rejects_after_native_admission_before_labels(self):
        import research_model_adapter as models
        from evaluation import stage1_source_adapter as source
        self.fixture.source.manifest['schema_version'] = source.VERSION
        self.fixture.source.manifest.pop('candidate_config_sha256')
        self.fixture.source.manifest.pop('feature_definition_sha256')
        self.fixture.source.manifest_only()
        self.parent.request.update(schema_version='habu-research-model-request-v4', stage1_manifest=self.fixture.source.ref)
        self.parent.publish()
        actual_prepare, actual_admit, actual_open = models.prepare_research_candidates_v2, source._configured_prepared, Path.open
        phases = []
        def prepare(*a, **kw):
            value = actual_prepare(*a, **kw); phases.append('prepared'); return value
        def admit(*a, **kw):
            value = actual_admit(*a, **kw); phases.append('admitted'); return value
        def opening(path, *a, **kw):
            if path.name == 'manifest.json' and 'stage1' in path.parts:
                self.assertIn('prepared', phases); self.assertIn('admitted', phases); phases.append('manifest')
            if path.name in ('captures.csv','individuals.csv','coverage.json'):
                raise AssertionError('Source-v1 downgrade reached labels')
            return actual_open(path, *a, **kw)
        with patch.object(models,'prepare_research_candidates_v2',side_effect=prepare), \
                patch.object(source,'_configured_prepared',side_effect=admit), patch.object(Path,'open',new=opening):
            result = self.parent.call()
        self.assertIn('manifest', phases, str(result))
        self.assert_failed(result)

    def test_v4_each_private_admission_resource_class_is_runtime_before_manifest(self):
        import prospective_inputs as pi
        import research_model_adapter as models
        from evaluation import full_ledger_stage1 as pure, stage1_source_adapter as source
        errors = (pure.Stage1CapacityBlocked, models.ResearchCapacityBlocked,
            models.ResearchInputCapacity, models._hba1.HBA1CapacityBlocked,
            pure.Stage1BudgetBlocked, TimeoutError, pi.InputCapacityError)
        actual = Path.open
        def opening(path, *a, **kw):
            if 'stage1' in path.parts: raise AssertionError('Resource failure opened Stage1 manifest')
            return actual(path, *a, **kw)
        for error in errors:
            with self.subTest(error=error.__name__), patch.object(Path,'open',new=opening), \
                    patch.object(source,'_configured_prepared',side_effect=error('explicit synthetic boundary exhaustion')):
                result = self.parent.call()
            self.assert_failed(result, runtime=True)


    def test_v4_request_and_config_contradictions_reject_before_fit(self):
        import research_model_adapter as models
        original_request = copy.deepcopy(self.parent.request)
        for mode in ('extra','missing','null-config','inline-config','unknown-request','bad-ref','fourth','hba2','definitions'):
            self.parent.request = copy.deepcopy(original_request)
            original_config = copy.deepcopy(self.fixture.config)
            if mode == 'extra': self.parent.request['unexpected'] = None
            elif mode == 'missing': self.parent.request.pop('stage1_manifest')
            elif mode == 'null-config': self.parent.request['candidate_config_manifest'] = None
            elif mode == 'inline-config': self.parent.request['candidate_config_manifest'] = copy.deepcopy(self.fixture.config)
            elif mode == 'unknown-request': self.parent.request['schema_version'] = 'habu-research-model-request-v99'
            elif mode == 'bad-ref': self.parent.request['stage1_manifest']['size_bytes'] = True
            elif mode == 'definitions': self.parent.request['feature_definition_sha256'] = 'a'*64
            else:
                self.fixture.config['candidate_ids'] = ['uniform','HB-A0','HB-A1','HB-B1'] if mode == 'fourth' else ['uniform','HB-A0','HB-A2']
                self.fixture.case.update_source()
                self.parent.request['candidate_config_manifest'] = self.fixture.case.source.ref
            self.parent.publish()
            with self.subTest(mode=mode), patch.object(models,'prepare_research_candidates_v2',side_effect=AssertionError('Invalid request/config reached fit')):
                result = self.parent.call()
            self.assert_failed(result)
            self.fixture.config.clear(); self.fixture.config.update(original_config)
            self.publish()

    def test_v4_rehashed_native_models_reject_before_first_stage1_manifest_open(self):
        import research_model_adapter as models
        from test_stage1_configured_source_adapter import reseal
        self.choices(['uniform','HB-A0','HB-B1'])
        actual_prepare, actual_open = models.prepare_research_candidates_v2, Path.open
        changes = [(ident, key, stamp) for ident,key in [('uniform','training_cutoff'),('HB-A0','fit_cutoff'),('HB-B1','training_cutoff')]
            for stamp in ('2026-10-15T12:00:00+09:00','2026-10-12T18:00:00+09:00')]
        changes += [('HB-A0','heldout_night','2026-10-15'),('HB-B1','heldout_night','2026-10-15'),
            ('uniform','probability',0.99),('uniform','schema_version','unknown'),('HB-B1','status','NOT_FITTED')]
        for ident,key,value in changes:
            def prepare(*a, **kw):
                prepared = actual_prepare(*a, **kw)
                candidate = next(c for c in prepared['candidates'] if c['candidate_id'] == ident)
                candidate['model'][key] = value
                reseal(prepared)
                return prepared
            def opening(path, *a, **kw):
                if 'stage1' in path.parts: raise AssertionError('Invalid native model opened Stage1 manifest')
                return actual_open(path, *a, **kw)
            with self.subTest(candidate=ident,key=key,value=value), patch.object(models,'prepare_research_candidates_v2',side_effect=prepare), patch.object(Path,'open',new=opening):
                self.assert_failed(self.parent.call())
        self.choices(['uniform','HB-B1','HB-A1'])
        for mode in ('future-fit','recipe','prediction'):
            def prepare(*a, **kw):
                prepared = actual_prepare(*a, **kw)
                candidate = prepared['candidates'][-1]
                if mode == 'future-fit': candidate['model']['fit_cutoff'] = '2026-10-15T12:00:00+09:00'
                elif mode == 'recipe': candidate['model']['recipe_sha256'] = 'a'*64
                else: candidate['prediction']['recipe_sha256'] = 'b'*64
                reseal(prepared)
                return prepared
            with self.subTest(a1=mode), patch.object(models,'prepare_research_candidates_v2',side_effect=prepare), patch.object(Path,'open',new=opening):
                self.assert_failed(self.parent.call())

    def test_v4_native_admission_preserves_caller_guard_exception_identity(self):
        from research_pdca_adapter import _v4_stage1_admission
        from prospective_inputs import ProspectiveReadContext, InputCapacityError
        from evaluation import stage1_source_adapter as source
        context = ProspectiveReadContext(300,2*1024**3)
        errors = [TimeoutError('caller timeout'),InputCapacityError('caller capacity'),
                  ValueError('caller invalid'),RuntimeError('caller stop')]
        for error in errors:
            # Exercise the actual helper/check boundary without pretending to
            # execute an estimator; the exception is explicitly injected.
            with self.subTest(error=type(error).__name__), patch.object(context,'check',side_effect=error), \
                    patch.object(source,'_configured_prepared',side_effect=AssertionError('expired caller reached native admission')):
                with self.assertRaises(type(error)) as caught:
                    _v4_stage1_admission({}, {}, {}, 'a'*64, 'b'*64, context)
                self.assertIs(caught.exception, error)
            with self.subTest(inner=type(error).__name__), patch.object(source,'_configured_prepared',side_effect=error):
                with self.assertRaises(type(error)) as caught:
                    _v4_stage1_admission({}, {}, {}, 'a'*64, 'b'*64, context)
                self.assertIs(caught.exception, error)

    def test_v4_nested_reserved_refs_never_open_payloads(self):
        actual = Path.open
        original_request = copy.deepcopy(self.parent.request)
        for field in ('training_manifest','forecast_manifest','stage1_manifest'):
            raw = (self.root/original_request[field]['path']).read_bytes()
            for segment in ('SeAlEd','confirmation','ORIGINAL','incoming','reports'):
                self.parent.request = copy.deepcopy(original_request)
                forbidden = f'evidence/{segment}/unread.json'
                manifest = json.loads(raw)
                manifest['source_nodes'][0]['ref'] = base_ref(self.root,forbidden,b'never read')
                ref = base_ref(self.root,original_request[field]['path'],canonical_bytes(manifest))
                self.parent.request[field] = ref; self.parent.publish()
                def opening(path, *a, **kw):
                    if path == self.root/forbidden: raise AssertionError('Reserved payload opened')
                    return actual(path, *a, **kw)
                with self.subTest(field=field,segment=segment), patch.object(Path,'open',new=opening):
                    self.assert_failed(self.parent.call())
            base_ref(self.root,original_request[field]['path'],raw)
        self.parent.request = original_request; self.parent.publish()

    def test_v4_unknown_cannot_hide_known_source_identity_or_raw_causal_contradiction(self):
        f = self.fixture.source
        for mode in ('subset','pre-event'):
            f.coverage['declaration'] = 'UNKNOWN'
            self.publish()
            if mode == 'subset':
                f.coverage['event_ids'] = ['inside']
                f.coverage['individual_ids'] = ['inside-1','inside-2']
                f.node('coverage',canonical_bytes(f.coverage))
            else:
                f.nodes['captures']['readiness']['source_received_at'] = '2026-10-14T17:00:00+09:00'
            self.fixture.publish()
            self.parent.request.update(schema_version='habu-research-model-request-v4',stage1_manifest=f.ref)
            self.parent.publish()
            with self.subTest(mode=mode): self.assert_failed(self.parent.call())
            f.coverage['event_ids'] = ['inside','outside']
            f.coverage['individual_ids'] = ['inside-1','inside-2','outside-1']

    def test_v4_same_context_actual_bytes_and_source_mutation_before_publish(self):
        import prospective_inputs as pi
        import research_pdca_adapter as parent
        from evaluation import stage1_source_adapter as source
        context = pi.ProspectiveReadContext(300,2*1024**3)
        actual = source.evaluate_stage1_sources_v2
        def evaluation(*a, **kw):
            self.assertIs(kw['context'],context)
            result = actual(*a, **kw)
            (self.root/self.fixture.source.nodes['captures']['ref']['path']).write_bytes(b'changed after evaluation')
            return result
        with patch.object(source,'evaluate_stage1_sources_v2',side_effect=evaluation):
            self.assert_failed(self.parent.call(_read_context=context))
        self.publish()
        context = pi.ProspectiveReadContext(300,2*1024**3)
        result = self.parent.call(_read_context=context)
        self.assertEqual(len(result['replay']),1,str(result))
        self.assertEqual(result['evidence']['actual_read_bytes'],context.bytes_read)
        self.assertGreater(context.bytes_read,result['stage1_diagnostic']['source_receipt']['actual_read_bytes'])

    def test_v4_stage_construction_mutation_rejects_before_native_publish(self):
        import research_pdca_adapter as parent
        original = parent.stage
        for target in ('scripts/synthetic.py','evidence/stage1/captures.csv'):
            before = (self.root/target).read_bytes()
            def staging(*a, **kw):
                value = original(*a, **kw)
                (self.root/target).write_bytes(b'changed after first stage')
                return value
            with self.subTest(target=target), patch.object(parent,'stage',side_effect=staging):
                self.assert_failed(self.parent.call())
            (self.root/target).write_bytes(before)

    def test_v4_shared_cap_and_expiry_after_native_admission_prevent_manifest(self):
        from prospective_inputs import ProspectiveReadContext
        from evaluation import stage1_source_adapter as source
        actual, actual_open = source._configured_prepared, Path.open
        for mode in ('bytes','deadline'):
            context = ProspectiveReadContext(300,2*1024**3)
            def admit(*a, **kw):
                value = actual(*a, **kw)
                if mode == 'bytes': context.max_bytes = context.bytes_read-1
                else: context.deadline = 0
                return value
            def opening(path,*a,**kw):
                if 'stage1' in path.parts: raise AssertionError('Expired admission read evaluation manifest')
                return actual_open(path,*a,**kw)
            with self.subTest(mode=mode), patch.object(source,'_configured_prepared',side_effect=admit),patch.object(Path,'open',new=opening):
                self.assert_failed(self.parent.call(_read_context=context),runtime=True)

    def test_v4_post_native_link_interrupt_cleans_only_new_owned_artifact(self):
        import research_pdca_adapter as parent
        actual = parent.os.link
        linked = []
        def link(*a, **kw):
            actual(*a, **kw); linked.append(a[1]); raise TimeoutError('After real native link')
        with patch.object(parent.os,'link',side_effect=link): result = self.parent.call()
        self.assertTrue(linked,'Native publication was not exercised')
        self.assert_failed(result,runtime=True)
        self.assertEqual(list((self.root/'predictions/replay').rglob('*.tmp')),[])

    def test_v4_late_expiry_cleans_new_replay_but_preserves_existing_reuse(self):
        import research_pdca_adapter as parent
        from prospective_inputs import ProspectiveReadContext
        actual = parent._publish
        context = ProspectiveReadContext(300,2*1024**3)
        published = []
        def publish(*a,**kw):
            value = actual(*a,**kw); published.append(value); context.deadline=0; return value
        with patch.object(parent,'_publish',side_effect=publish): result = self.parent.call(_read_context=context)
        self.assertTrue(published,'No actual new artifact')
        self.assert_failed(result,runtime=True)
        healthy = self.parent.call()
        self.assertEqual(len(healthy['replay']),1,str(healthy))
        path = self.root/healthy['replay'][0]['path']; before = path.read_bytes()
        context = ProspectiveReadContext(300,2*1024**3)
        with patch.object(parent,'_publish',side_effect=publish): result = self.parent.call(_read_context=context)
        self.assertEqual((result['candidates'],result['replay']),([],[]))
        self.assertEqual(result['stages'][0]['blocker_kind'],'RUNTIME_BLOCKED')
        self.assertEqual(path.read_bytes(),before)

    def test_v4_actual_sept28_sources_keep_five_six_summary_and_no_denominator(self):
        import subprocess
        f = self.fixture.source
        for role,path in [('captures','data/processed/capture_events/2026/2026-09-28.csv'),
                          ('individuals','data/processed/individuals/2026/2026-09-28.csv')]:
            f.node(role,subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT),'2026-10-25T18:00:00+09:00')
        f.manifest['scope_id'] = f.manifest['coverage_id'] = None
        f.nodes.pop('scope'); f.nodes.pop('coverage')
        f.manifest.update(evaluation_as_of='2026-10-25T19:00:00+09:00',
            readiness=f.ready('2026-10-25T18:00:00+09:00'),usable_at='2026-10-25T18:00:00+09:00')
        self.fixture.publish()
        self.parent.request.update(schema_version='habu-research-model-request-v4',stage1_manifest=f.ref)
        self.parent.publish()
        result = self.parent.call()
        self.assertEqual(len(result['candidates']),3,str(result))
        self.assertEqual(len(result['replay']),1)
        d = result['stage1_diagnostic']
        self.assertEqual(d['source_summary'],dict(capture_events=5,individuals=6))
        self.assertEqual((d['status'],d['per_night'],d['pooled'],d['paired_uncertainty']),('NEED_MORE_DATA',[],{},{}))
        self.assertIs(result['scientific_fit_authorized'],False)

    def test_v4_real_junction_or_symlink_manifest_never_opens_external_bytes(self):
        import subprocess
        import tempfile
        actual = Path.open
        link = self.root/'evidence/linked-stage1'
        with tempfile.TemporaryDirectory(prefix='stage1-v4-external-') as temp:
            external = Path(temp)
            sentinel = external/'manifest.json'
            before = (self.root/self.fixture.source.ref['path']).read_bytes()
            sentinel.write_bytes(before)
            self.parent.request['stage1_manifest'] = dict(self.fixture.source.ref,path='evidence/linked-stage1/manifest.json')
            self.parent.publish()
            opened = []
            def opening(path,*a,**kw):
                if path in (sentinel,link/'manifest.json'): opened.append(path)
                return actual(path,*a,**kw)
            try:
                if os.name == 'nt':
                    subprocess.run(['cmd','/c','mklink','/J',str(link),str(external)],check=True,capture_output=True)
                    self.assertTrue(link.is_junction())
                else:
                    link.symlink_to(external,target_is_directory=True)
                    self.assertTrue(link.is_symlink())
                with patch.object(Path,'open',new=opening): self.assert_failed(self.parent.call())
                self.assertEqual(opened,[])
                self.assertEqual(sentinel.read_bytes(),before)
            finally:
                # Sever only the verified temporary link; never recursively
                # clean a tree through an external junction/symlink.
                self.assertEqual(link.parent,self.root/'evidence')
                if link.is_symlink() or (os.name == 'nt' and link.is_junction()):
                    os.rmdir(link) if os.name == 'nt' else link.unlink()

    @unittest.skipIf(os.name == 'nt','Actual master lock requires POSIX fcntl; Ubuntu CI executes v4')
    def test_v4_actual_master_snapshot_dispatch_remains_diagnostic(self):
        from master_orchestrator import run_master
        result = run_master(self.root,NIGHT)
        generation = next(s for s in result['stages'] if s['name']=='candidate_generation')
        self.assertEqual(generation['status'],'PASS',str(result))
        self.assertFalse(result['completed'])
        self.assertNotEqual(result['overall_status'],'PASS')


class ResearchLegacyWholeOracleTests(unittest.TestCase):
    """Eight pre-edit native-Git whole outputs plus real physical REPLAY identity."""
    ORACLES = {
        'v1_complete': ('c1a90f286c438ee1773efdf75165900598e9b05ec3774240818848deafd103cf','cd9a07a18a5e257583f6ab9e5d0e502d0a2867bbda5f7c44de1f441e1dad2faf',177664,204382,'b0bc9c552d400cd13a94d3c3df851a298b360bc100a16284ea7da9231a78fb7b',26718),
        'v2_complete': ('893d9364df4efadf34e8fb03490ce415ee9d414ab428c35ee3d2a00ecc011958',None,254109,254109,'89378f8ebe84036ebf16ea4d0379352a86c788072b7ffb39012470c951252b9a',32810),
        'v2_unknown': ('cdd4d527c18ddbe730231f18aa61f7b9841e448d3cd1bb930978ff20ad0c56ae',None,251617,251617,'243b598a3fa7ab672740f1f84c4ea75e53b345db3c38bc19a74a0d51aa714f2d',30358),
        'v3_legacy_null': ('969b29c8f7e20daf62a1a9f9d01bf26fc1e348a7d479d0e4269caae960ff6db4',None,316516,316516,'65a641843a561ec0c9a34f73f4e70fc9920f4ec7d64f288d03adb8b6e48d73ed',35621),
        'v3_legacy_complete': ('ab158b23683404cc3897479f9ecb7136bbfcb3a8d00a677fe10bbbbbcdd0778b',None,380051,380051,'50189e30f3f2e460a969cccef5b66b014ab4207fbb8f21ed463397cabaea1385',41716),
        'v3_reversed_requested_blocked': ('fffc3ddea40fd39f3ce80316bf44438f4106b8f8e1d73ddceef3c1ff36de00a0',None,324547,324547,'2c4b8f8171d940fd0002036f9dc46ff94ee13c4853ce71583f9cb76247570a82',35754),
        'v3_a1_null': ('486c22154815499e3dcfd34bcc6dc5a3f4f06d0ecc830a68c72acd0b3c4a7e25',None,1167524,1167524,'b66f77cc182e6577de85fc9b4fa92ad5ef25cfc56886e4360ad92b02d1c8110e',55580),
        'v3_a1_requested_blocked': ('70cefa3c1d2ef9131aaaf202c36406ddd2f729ef0fcf6c848a21a333df8e786b',None,1176038,1176038,'f4f28e09c657cecb5bcba187d175f97f302d132411f1f9b32b628fa7d66771d5',55713),
    }

    def test_eight_whole_legacy_artifacts_and_first_reused_reads_are_unchanged(self):
        import hashlib
        import subprocess
        import codex_cycle_contract as cycle
        from test_stage1_source_adapter import SourceFixture
        # The baseline was collected at5d4b84f. Native HEAD policy must retain
        # that exact blob; use HEAD so genuine shallow CI needs no history fetch.
        policy = subprocess.check_output(['git','show','HEAD:'+cycle.POLICY_PATH],cwd=ROOT)
        self.assertEqual((len(policy),hashlib.sha256(policy).hexdigest()),
                         (1751,'79112d4f845b620ff928743cb1f6d14af62ce8bcf474f51fb32ec911d67941ac'))
        actual_read = Path.read_bytes
        def native(path):
            return policy if path == ROOT/cycle.POLICY_PATH else actual_read(path)
        for name, (first_sha, second_sha, first_bytes, second_bytes, physical_sha, size) in self.ORACLES.items():
            with self.subTest(name=name), patch.object(Path,'read_bytes',new=native):
                configured = name.startswith('v3')
                case = ResearchConfigV3Tests() if configured else ResearchPDCAAdapterTests()
                case.setUp()
                try:
                    parent = case.parent if configured else case
                    if name.startswith('v2'):
                        fixture = SourceFixture(parent)
                        if name == 'v2_unknown':
                            fixture.coverage['declaration'] = 'UNKNOWN'; fixture.publish()
                    elif name == 'v3_legacy_complete':
                        SourceFixture(parent)
                        parent.request['schema_version'] = 'habu-research-model-request-v3'; parent.publish()
                    elif name == 'v3_reversed_requested_blocked':
                        case.source.config['candidate_ids'] = ['uniform','HB-B1','HB-A0']; case.update_source()
                        parent.request['stage1_manifest'] = base_ref(parent.root,'evidence/stage1/unread.json',b'not JSON, must remain unopened'); parent.publish()
                    elif name.startswith('v3_a1'):
                        case.full_seven_fixture()
                        if name.endswith('requested_blocked'):
                            parent.request['stage1_manifest'] = base_ref(parent.root,'evidence/stage1/unread.json',b'not JSON, must remain unopened'); parent.publish()
                    first = parent.call()
                    self.assertEqual(digest(first), first_sha)
                    self.assertEqual(first['evidence']['actual_read_bytes'], first_bytes)
                    path = parent.root/first['replay'][0]['path']
                    before = path.read_bytes()
                    self.assertEqual((hashlib.sha256(before).hexdigest(), len(before)), (physical_sha,size))
                    second = parent.call()
                    self.assertEqual(digest(second), second_sha or first_sha)
                    self.assertEqual(second['evidence']['actual_read_bytes'], second_bytes)
                    self.assertEqual(second['replay'], first['replay'])
                    self.assertEqual(path.read_bytes(), before)
                    self.assertEqual(len(list((parent.root/'predictions/replay').rglob('*.json'))), 1)
                finally:
                    case.doCleanups()


if __name__ == '__main__':
    unittest.main()
