"""Actual synthetic source readers/refits; no real Habu science or authority."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
from master_contracts import canonical_bytes, digest
from codex_cycle_contract import code_paths
from test_g0_forecast_contract import base_ref
from test_feature_candidate_calibration_parent import CalibrationFixture, NIGHT, FIT, CUTOFF, ready
from test_stage1_source_adapter import csv_bytes


class ReproductionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('promotion_reproduction'),
                             'substantive reproduction module missing')
        self.module = importlib.import_module('promotion_reproduction')
        self.fixture = CalibrationFixture(self)
        self.root = self.fixture.root
        self.policy = json.loads((ROOT / 'protocols/development/g0-policy-v1.json').read_bytes())
        self.code = {}
        for path in code_paths(ROOT):
            raw = (ROOT / path).read_bytes()
            base_ref(self.root, path, raw)
            self.code[path] = hashlib.sha256(raw).hexdigest()
        # The source configuration validator binds the full actual test snapshot.
        self.fixture.case.source.publish()
        self.stage1()
        fold = dict(fold_id='development-one', operational_night=NIGHT, fit_cutoff=FIT,
            forecast_cutoff=CUTOFF, forecast_as_of=NIGHT+'T18:30:00+09:00',
            feature_definition_sha256=self.fixture.parent.request['feature_definition_sha256'],
            training_manifest_ref=self.fixture.parent.request['training_manifest'],
            forecast_manifest_ref=self.fixture.parent.request['forecast_manifest'],
            expected_prepared_ref=self.put('evidence/reproduction/expected-prepared.json', self.fixture.prepared),
            stage1_manifest_ref=self.stage1_ref, calibration_manifest_ref=self.fixture.profile_ref,
            composite_model_ref=None, inference_bundle_ref=None, frozen_prediction_ref=None)
        self.bundle = dict(schema_version='habu-promotion-reproduction-request-v1',
            purpose='DEVELOPMENT_REPRODUCTION_ONLY', policy_sha256=digest(self.policy),
            selected_candidate_id='HB-A1', candidate_config_ref=self.fixture.case.source.ref,
            code_manifest=self.code, protocol_ref=None, exposure_history_ref=None,
            ablation_protocol_ref=None, folds=[fold])

    def put(self, path, value):
        return base_ref(self.root, path, canonical_bytes(value))

    def stage1(self):
        scope = dict(schema_version='habu-stage1-scope-source-v1', operational_night=NIGHT,
            cutoff_time=CUTOFF, horizon_start=NIGHT+'T19:00:00+09:00',
            horizon_end=NIGHT+'T19:20:00+09:00',
            scope=dict(crs='EPSG:32652', bbox_utm=[390000,2990000,450000,3010000]))
        captures, individuals = [], []
        for name, x, count in [('synthetic-evaluation-event',400050,2),('outside',430050,1)]:
            captures.append(dict(event_id=name,operational_date=NIGHT,
                event_time_local=NIGHT+'T19:03:00+09:00',event_type='capture',
                event_count=str(count),utm_x_m=str(x),utm_y_m='3000050'))
            for i in range(count):
                individuals.append(dict(individual_id=name+'-'+str(i),event_id=name,
                    individual_index=str(i+1),operational_date=NIGHT,
                    event_time_local=NIGHT+'T19:03:00+09:00'))
        refs = {name:base_ref(self.root,'evidence/reproduction/'+name+'.csv',csv_bytes(rows))
                for name,rows in [('captures',captures),('individuals',individuals)]}
        coverage = dict(schema_version='habu-stage1-coverage-source-v1',declaration='DECLARED_COMPLETE',
            operational_night=NIGHT,scope_sha256=digest(scope['scope']),
            horizon_start=scope['horizon_start'],horizon_end=scope['horizon_end'],
            captures_ref=refs['captures'],individuals_ref=refs['individuals'],
            event_ids=['synthetic-evaluation-event','outside'],
            individual_ids=['synthetic-evaluation-event-0','synthetic-evaluation-event-1','outside-0'])
        refs['scope'] = self.put('evidence/reproduction/scope.json',scope)
        refs['coverage'] = self.put('evidence/reproduction/coverage.json',coverage)
        nodes = [dict(id=name,ref=ref,source_kind='RAW',role=name,parents=[],
            readiness=ready(NIGHT+'T17:00:00+09:00' if name=='scope' else '2026-10-29T09:00:00+09:00'),
            usable_at=NIGHT+'T17:00:00+09:00' if name=='scope' else '2026-10-29T09:00:00+09:00')
            for name,ref in refs.items()]
        self.stage_manifest = dict(schema_version='habu-stage1-source-contract-v2',
            purpose='DEVELOPMENT_EVALUATION_ONLY',operational_night=NIGHT,
            evaluation_as_of='2026-10-29T11:00:00+09:00',
            forecast_manifest_sha256=self.fixture.parent.forecast.ref['sha256'],
            joined_universe_sha256=self.fixture.forecast['receipt']['canonical_joined_rows_sha256'],
            scope_id='scope',captures_id='captures',individuals_id='individuals',coverage_id='coverage',
            source_nodes=nodes,readiness=ready('2026-10-29T09:00:00+09:00'),
            usable_at='2026-10-29T09:00:00+09:00',
            candidate_config_sha256=digest(self.fixture.case.source.config),
            feature_definition_sha256=self.fixture.parent.request['feature_definition_sha256'])
        self.stage1_ref = self.put('evidence/reproduction/stage1-manifest.json',self.stage_manifest)

    def call(self, **kwargs):
        return self.module.reproduce_candidate(self.bundle,self.policy,input_root=self.root,**kwargs)

    def test_actual_refits_full_denominator_and_proper_scores_execute(self):
        before = {p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.call()
        self.assertEqual(result['execution_status'],'PARTIAL',result)
        fold = result['folds'][0]
        self.assertEqual(fold['refit']['status'],'NUMERIC_REPRODUCED')
        self.assertEqual(fold['stage1']['pooled']['HB-A1']['denominator'],3)
        self.assertAlmostEqual(fold['stage1']['pooled']['HB-A1']['recall'],2/3)
        self.assertEqual(fold['stage1']['per_night'][0]['outside_universe_individuals'],1)
        self.assertEqual(fold['proper_scores']['observed_units'],2)
        self.assertIsInstance(fold['proper_scores']['mean_night_brier'],float)
        self.assertEqual(result['source_authentication'],'NOT_ATTESTED')
        self.assertIs(result['production_authorized'],False)
        self.assertEqual(result['confirmation']['status'],'NOT_VALIDATED')
        self.assertIn('FORMAL_TARGET_GENERATOR_NOT_REGISTERED',result['implementation_blockers'])
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_expected_state_swap_is_rejected_after_real_refit(self):
        altered = copy.deepcopy(self.fixture.prepared)
        altered['candidates'][-1]['model']['intercept'] = 999
        self.bundle['folds'][0]['expected_prepared_ref'] = self.put('evidence/reproduction/wrong-model.json',altered)
        result = self.call()
        self.assertEqual(result['execution_status'],'FAIL',result)
        self.assertIn('REFIT_OUTPUT_MISMATCH',result['discrepancies'])

    def test_missing_expected_model_does_not_hide_actual_math(self):
        self.bundle['folds'][0]['expected_prepared_ref'] = None
        result = self.call()
        self.assertTrue(result['folds'][0]['stage1']['pooled'])
        self.assertIn('EXPECTED_PREPARED_NOT_SUPPLIED',result['data_blockers'])

    def test_missing_stage1_is_named_without_hiding_refit_or_calibration(self):
        self.bundle['folds'][0]['stage1_manifest_ref'] = None
        result = self.call()
        self.assertEqual(result['folds'][0]['refit']['status'],'NUMERIC_REPRODUCED')
        self.assertEqual(result['folds'][0]['proper_scores']['observed_units'],2)
        self.assertIn('FULL_OUTCOME_MANIFEST_NOT_SUPPLIED',result['data_blockers'])

    def test_missing_training_blocks_no_model_or_fake_eligible_zero(self):
        self.bundle['folds'][0]['training_manifest_ref'] = None
        result = self.call()
        self.assertEqual(result['execution_status'],'BLOCKED')
        self.assertIn('TRAINING_MANIFEST_NOT_SUPPLIED',result['data_blockers'])
        self.assertIsNone(result['eligible_training_units'])

    def test_unknown_policy_or_candidate_threshold_override_fails(self):
        self.policy['metrics']['stage1_threshold'] = 0
        self.bundle['policy_sha256'] = digest(self.policy)
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_code_closure_cannot_omit_changed_helper(self):
        self.bundle['code_manifest'].pop('src/event_matching.py')
        result = self.call()
        self.assertEqual(result['execution_status'],'FAIL')
        self.assertIn('CODE_CLOSURE_MISMATCH',result['discrepancies'])

    def test_reserved_nested_reference_rejected_before_sealed_read(self):
        manifest = self.fixture.parent.training.manifest
        manifest['source_nodes'][0]['ref']['path'] = 'sealed/confirmation/private.json'
        self.bundle['folds'][0]['training_manifest_ref'] = self.put('protocols/development/bad-nested.json',manifest)
        original = Path.open
        def opening(path,*args,**kwargs):
            if any(p.casefold() in ('sealed','confirmation') for p in path.parts):
                raise AssertionError('sealed source opened')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',new=opening):
            self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_custom_object_and_metaclass_never_execute_callbacks(self):
        calls=[]
        class Meta(type):
            def __eq__(cls, other):
                calls.append('eq')
                return False
            __hash__=type.__hash__
        class Evil(metaclass=Meta):
            def __deepcopy__(self,memo):
                calls.append('copy')
                return self
        self.bundle['folds'] = Evil()
        result = self.call()
        self.assertEqual(result['execution_status'],'FAIL')
        self.assertEqual(calls,[])

    def test_invalid_budget_is_structured_and_does_not_overflow(self):
        for value in (True,0,-1,31*10,10**1000,math.inf):
            with self.subTest(value=str(value)[:24]):
                self.assertEqual(self.call(budget_seconds=value)['execution_status'],'FAIL')

    def test_caller_metric_field_is_not_accepted_as_evidence(self):
        self.bundle['metrics']={'stage1':1,'brier':0}
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_duplicate_fold_and_non_development_mode_fail_closed(self):
        self.bundle['folds'].append(copy.deepcopy(self.bundle['folds'][0]))
        self.assertEqual(self.call()['execution_status'],'FAIL')
        self.bundle['folds'].pop()
        self.bundle['purpose']='CONFIRMATION'
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_original_g0_unknown_qualified_mask_is_not_zero(self):
        observation=self.fixture.observation
        row=observation.rows[1]
        row.update(observation='UNKNOWN',label=None,quality='UNKNOWN')
        observation.publish()
        self.fixture.observed=observation.select()
        self.fixture.rebind_protocol()
        self.bundle['folds'][0]['calibration_manifest_ref']=self.fixture.profile_ref
        result=self.call()
        self.assertEqual(result['folds'][0]['proper_scores']['observed_units'],1)
        self.assertEqual(result['folds'][0]['observation_counts']['rejected_rows'],1)

    def test_receipt_covers_final_deduplicated_result(self):
        result=self.call()
        self.assertEqual(result['receipt_sha256'],digest({k:v for k,v in result.items() if k!='receipt_sha256'}))

    def ablation_spec(self):
        from models.research_selection import IDENTITY_FIELDS
        observed=copy.deepcopy(self.fixture.observed['selection'])
        for row,future in zip(observed['accepted'],self.fixture.forecast['rows']):
            row['row_id']=future['row_id']
        observed['selection_sha256']=digest({k:observed[k] for k in IDENTITY_FIELDS})
        spec=dict(schema_version='habu-hba1-retrained-ablation-protocol-v1',phase='DEVELOPMENT',
            target=self.fixture.case.source.config['hba1_recipe']['target'],
            base_recipe=self.fixture.case.source.config['hba1_recipe'],
            groups=[dict(id='temperature',drop_features=['temperature_c'])],
            folds=[dict(night=NIGHT,training_selection_sha256=self.fixture.selected['selection']['selection_sha256'],
                joined_forecast_sha256=self.fixture.forecast['receipt']['canonical_joined_rows_sha256'],
                cutoff_time=CUTOFF,evaluation_selection_sha256=observed['selection_sha256'])])
        return spec

    def test_true_retraining_ablation_uses_same_qualified_sources(self):
        self.bundle['ablation_protocol_ref']=self.put('protocols/development/reproduction-ablation.json',self.ablation_spec())
        result=self.call()
        self.assertIsNotNone(result['ablation'],'actual ablation execution missing')
        self.assertEqual(result['ablation']['status'],'DESCRIPTIVE_RETRAINED_ABLATION_ONLY',result)
        fold=result['ablation']['fold_results'][0]
        full,ablated=fold['full'],fold['ablations'][0]
        self.assertNotEqual(full['model_sha256'],ablated['model_sha256'])
        self.assertEqual(full['training_selection_sha256'],ablated['training_selection_sha256'])
        self.assertEqual(ablated['feature_mask'],[False,True,True,True,True,True,True])
        self.assertTrue(any(a!=b for a,b in zip(full['coefficients'][1:],ablated['coefficients'][1:])))

    def test_ablation_cannot_replace_selected_full_recipe(self):
        spec=copy.deepcopy(self.ablation_spec())
        spec['base_recipe']['implementation_sha256']['src/models/hba1_feature_candidate.py']='f'*64
        self.bundle['ablation_protocol_ref']=self.put('protocols/development/reproduction-ablation.json',spec)
        result=self.call()
        self.assertEqual(result['execution_status'],'FAIL')
        self.assertIn('ABLATION_RECIPE_MISMATCH',result['discrepancies'])

    def test_midrun_source_mutation_invalidates_completion_without_private_error(self):
        import research_model_adapter
        actual=research_model_adapter.prepare_research_candidates_v2
        path=self.root/self.fixture.parent.training.manifest['source_nodes'][0]['ref']['path']
        def changed(*args,**kwargs):
            value=actual(*args,**kwargs)
            path.write_bytes(b'SYNTHETIC_PRIVATE_SENTINEL')
            return value
        with patch.object(research_model_adapter,'prepare_research_candidates_v2',side_effect=changed):
            result=self.call()
        self.assertEqual(result['execution_status'],'FAIL')
        self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL',json.dumps(result))

    def test_deadline_and_readonly_runtime(self):
        self.assertEqual(self.call(budget_seconds=1e-12)['execution_status'],'BLOCKED')
        actual=Path.open
        def readonly(path,mode='r',*args,**kwargs):
            if any(flag in mode for flag in ('w','a','x','+')):
                raise AssertionError('reproduction attempted a write')
            return actual(path,mode,*args,**kwargs)
        with patch.object(Path,'open',new=readonly):
            self.assertEqual(self.call()['execution_status'],'PARTIAL')

    def paired_projection(self):
        from evaluation.stage1_source_adapter import project_stage1_sources_v2
        from prospective_inputs import ProspectiveReadContext
        projection=project_stage1_sources_v2(self.root,self.stage1_ref,self.fixture.forecast,
            self.fixture.prepared,candidate_config=self.fixture.case.source.config,
            expected_config_sha256=digest(self.fixture.case.source.config),
            feature_definition_sha256=self.fixture.parent.request['feature_definition_sha256'],
            context=ProspectiveReadContext(300,2*1024**3))
        def next_day(value):
            if type(value) is str:return value.replace(NIGHT,'2026-10-29')
            if type(value) is list:return [next_day(v) for v in value]
            if type(value) is dict:return {next_day(k):next_day(v) for k,v in value.items()}
            return value
        other=next_day(projection)
        other['ledger']['ledger_sha256']=digest({k:v for k,v in other['ledger'].items() if k!='ledger_sha256'})
        other['scores']['universe_sha256']=digest(other['universe'])
        return projection,other

    def test_cohort_math_rejects_global_individual_reuse_across_nights(self):
        function=getattr(self.module,'_combine_stage1',None)
        self.assertIsNotNone(function,'cohort-wide ledger validation missing')
        first,other=self.paired_projection()
        with self.assertRaises(ValueError):
            function([first,other],self.fixture.case.source.config,lambda:None)

    def test_cohort_bootstrap_preserves_full_pooled_denominator(self):
        function=getattr(self.module,'_combine_stage1',None)
        self.assertIsNotNone(function,'cohort-wide ledger validation missing')
        first,other=self.paired_projection()
        for event in other['ledger']['events']:
            event['event_id']+='-next'
            event['individual_ids']=[i+'-next' for i in event['individual_ids']]
        other['ledger']['ledger_sha256']=digest({k:v for k,v in other['ledger'].items() if k!='ledger_sha256'})
        result=function([first,other],self.fixture.case.source.config,lambda:None)
        self.assertEqual(result['pooled']['HB-A1']['denominator'],6)
        self.assertEqual(result['pooled']['HB-A1']['numerator'],4)
        self.assertEqual(result['paired_uncertainty']['night_count'],2)
        self.assertEqual(result['paired_uncertainty']['replicates'],2000)

    def composite(self, mutate=None):
        from output_adapters import adapter_contract,required_code_paths
        from composite_inference import predict_composite
        state=self.fixture.candidate['model']
        contract=adapter_contract('hba1_unit_v1')
        model=dict(schema_version='2.0',kind='registered_composite',recipe_id='synthetic_hba1',
            protocol_sha256=digest(self.fixture.case.source.config),policy_sha256=digest(self.policy),
            training_cutoff=state['fit_cutoff'],code_manifest={p:self.code[p] for p in required_code_paths()},
            components=[dict(component_id='spatial',adapter_id='hba1_unit_v1',adapter_version='1',role='spatial',
                state_sha256=digest(state),config_sha256=digest({}),
                input_schema_sha256=contract['input_schema_sha256'],
                output_schema_sha256=contract['output_schema_sha256'],dependencies={})],
            output_bindings={'unit_predictions':dict(component_id='spatial',output='unit_predictions')},
            mandatory_capabilities=['unit_predictions'])
        artifacts={digest(state):state,digest({}):{}}
        inputs=dict(schema_version='habu-composite-inference-input-v1',operational_night=NIGHT,
            cutoff_time=CUTOFF,forecast_end=self.fixture.parent.forecast.manifest['horizon']['end'],
            artifacts=artifacts,artifact_available_at={key:'2026-10-27T19:00:00+09:00' for key in artifacts},
            inputs={'spatial':dict(forecast_rows=self.fixture.forecast['rows'],
                joined_universe_sha256=self.fixture.forecast['receipt']['canonical_joined_rows_sha256'],
                cutoff_time=CUTOFF)},input_available_at={'spatial':NIGHT+'T17:00:00+09:00'})
        if mutate:mutate(model,inputs)
        model['model_id']=model['model_sha256']=digest(model)
        frozen=predict_composite(model,inputs)
        fold=self.bundle['folds'][0]
        fold['composite_model_ref']=self.put('evidence/reproduction/composite-model.json',model)
        fold['inference_bundle_ref']=self.put('evidence/reproduction/composite-input.json',inputs)
        fold['frozen_prediction_ref']=self.put('evidence/reproduction/composite-frozen.json',frozen)
        return frozen

    def test_shared_predictor_recomputes_complete_frozen_bundle_from_actual_state(self):
        frozen=self.composite()
        self.assertEqual(frozen['status'],'EXECUTED')
        result=self.call()
        self.assertEqual(result['folds'][0]['inference_reproduction']['status'],'NUMERIC_REPRODUCED',result)

    def test_a_reproduced_predictor_failure_is_not_successful_inference(self):
        frozen=self.composite(lambda model,inputs:model['components'][0].update(adapter_version='2'))
        self.assertEqual(frozen['status'],'FAIL')
        self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_composite_code_policy_and_horizon_bind_actual_sources(self):
        for change in ('code','policy','horizon'):
            def mutate(model,inputs):
                if change=='code':model['code_manifest']['src/output_adapters.py']='f'*64
                if change=='policy':model['policy_sha256']='f'*64
                if change=='horizon':inputs['forecast_end']=NIGHT+'T19:30:00+09:00'
            frozen=self.composite(mutate)
            self.assertEqual(frozen['status'],'EXECUTED')
            with self.subTest(change=change):
                self.assertEqual(self.call()['execution_status'],'FAIL')

    def test_observation_event_identity_must_match_complete_ledger(self):
        observation=self.fixture.observation
        observation.rows[0]['capture_event_ids']=['unrelated-source-event']
        observation.publish()
        self.fixture.observed=observation.select()
        self.fixture.rebind_protocol()
        self.bundle['folds'][0]['calibration_manifest_ref']=self.fixture.profile_ref
        result=self.call()
        self.assertEqual(result['execution_status'],'FAIL')
        self.assertIn('OBSERVATION_LEDGER_EVENT_MISMATCH',result['discrepancies'])

    def test_controller_root_object_cannot_execute_path_callback(self):
        calls=[]
        class Evil:
            def __fspath__(self):
                calls.append('path')
                return str(self.root)
        result=self.module.reproduce_candidate(self.bundle,self.policy,input_root=Evil())
        self.assertEqual(result['execution_status'],'FAIL')
        self.assertEqual(calls,[])

    def test_development_row_count_is_not_global_scientific_eligibility(self):
        result=self.call()
        self.assertIsNone(result['eligible_training_units'])
        self.assertEqual(result['development_training_unique_units'],20)
        self.assertEqual(result['fit_training_row_memberships'],20)

    def test_final_source_rescan_discards_invalid_computed_result(self):
        original=self.module._combine_stage1
        source=self.root/'evidence/reproduction/captures.csv'
        def change(*args,**kwargs):
            result=original(*args,**kwargs)
            source.write_bytes(b'SYNTHETIC_PRIVATE_SENTINEL')
            return result
        with patch.object(self.module,'_combine_stage1',side_effect=change):
            result=self.call()
        self.assertEqual(result['execution_status'],'FAIL')
        self.assertNotIn('cohort_stage1',result)
        self.assertNotIn('computed_gates',result)
        self.assertNotIn('receipt_sha256',result)
        self.assertEqual(result['folds'],[])

    def test_cohort_native_capacity_error_is_resource_block_not_invalid_data(self):
        original=self.module._combine_stage1
        def small(*args,**kwargs):
            with patch.object(self.module.stage1_pure,'MAX_EVENTS',1):
                return original(*args,**kwargs)
        with patch.object(self.module,'_combine_stage1',side_effect=small):
            result=self.call()
        self.assertEqual(result['execution_status'],'BLOCKED')
        self.assertIn('RESOURCE_BUDGET_BLOCKED',result['runtime_blockers'])

    def test_paired_subset_reports_unavailable_fold_without_claiming_complete(self):
        result=self.module._paired([
            dict(fold_id='known',comparison=dict(mean_brier_improvement=.1)),
            dict(fold_id='unavailable')],lambda:None)
        self.assertIs(result.get('cohort_complete'),False)
        self.assertEqual(result['missing_fold_ids'],['unavailable'])
        self.assertEqual(result['paired_nights'],1)

    def test_event_offset_representation_preserves_fixed_jst_observation_unit(self):
        observed={'accepted':[dict(cell_x=4000,cell_y=30000,
            window_start_jst=NIGHT+'T19:00:00+09:00',capture_event_ids=['same'])]}
        ledger={'events':[dict(event_id='same',utm_x_m=400050,utm_y_m=3000050,
            datetime=NIGHT+'T15:48:00+05:45')]}
        try:
            self.module._match_observation_ledger(observed,ledger,lambda:None)
            accepted=True
        except ValueError:
            accepted=False
        self.assertTrue(accepted,'equivalent actual instant was floored in its display offset')

    def test_downstream_spatial_ties_reuse_existing_lexical_cell_order(self):
        rows=[dict(row_id=str(i),utm_x_m=i*500+50,utm_y_m=3000050) for i in range(995,1006)]
        candidate={'prediction':{'unit_predictions':[dict(row_id=str(i),spatial_score=.5)
                                                     for i in range(995,1006)]}}
        ledger={'events':[dict(utm_x_m=499550,utm_y_m=3000050,individual_ids=['one'])]}
        result=self.module._spatial({'rows':rows},candidate,ledger,lambda:None)
        # Existing lexical IDs rank 1000..1005,995..998; 999 is the one miss.
        self.assertEqual(result['500m']['numerator'],0)
        self.assertEqual(result['500m']['denominator'],1)

    def test_honest_unsupported_recipe_is_an_implementation_blocker(self):
        for recipe in ('HB-A2','HB-A0','future_registered_recipe'):
            self.bundle['selected_candidate_id']=recipe
            result=self.call()
            with self.subTest(recipe=recipe):
                self.assertEqual(result['execution_status'],'BLOCKED')
                self.assertIn('RECIPE_SOURCE_REPRODUCTION_NOT_IMPLEMENTED',result['implementation_blockers'])
                self.assertEqual(result['folds'],[])
                self.assertIs(result['production_authorized'],False)

    def test_receipt_binds_exact_request_and_frozen_policy_even_when_component_missing(self):
        self.bundle['folds'][0]['training_manifest_ref']=None
        result=self.call()
        self.assertEqual(result.get('input_digests'),dict(request=digest(self.bundle),policy=digest(self.policy)))

    def test_malformed_composite_containers_fail_without_escaping_attribute_error(self):
        for field in ('components','code_manifest','artifacts','inputs','input_available_at'):
            def malformed(model,inputs):
                if field=='components':model[field]=[None]
                elif field=='code_manifest':model[field]=None
                else:inputs[field]=None
            self.composite(malformed)
            escaped=None
            try:
                result=self.call()
            except Exception as exc:
                escaped=type(exc).__name__
            with self.subTest(field=field):
                self.assertIsNone(escaped,'malformed source escaped structured failure')
                self.assertEqual(result['execution_status'],'FAIL')

    def test_missing_composite_state_is_data_block_without_hiding_other_numerics(self):
        for missing_kind,reason in [('state','COMPOSITE_FITTED_STATE_NOT_SUPPLIED'),
                                    ('config','COMPOSITE_CONFIG_NOT_SUPPLIED'),
                                    ('input','COMPOSITE_COMPONENT_INPUT_NOT_SUPPLIED')]:
            def missing(model,inputs):
                if missing_kind=='input':
                    inputs['inputs'].pop('spatial')
                    inputs['input_available_at'].pop('spatial')
                else:
                    sha=model['components'][0][missing_kind+'_sha256']
                    inputs['artifacts'].pop(sha)
                    inputs['artifact_available_at'].pop(sha)
            self.assertEqual(self.composite(missing)['status'],'BLOCKED')
            result=self.call()
            with self.subTest(missing_kind=missing_kind):
                self.assertEqual(result['execution_status'],'PARTIAL')
                self.assertIn(reason,result['data_blockers'])
                self.assertEqual(result['folds'][0]['inference_reproduction']['status'],'BLOCKED')
                self.assertEqual(result['folds'][0]['stage1']['pooled']['HB-A1']['denominator'],3)


if __name__=='__main__':
    unittest.main()
