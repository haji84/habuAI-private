"""Synthetic source-bound post-night diagnostics; never data/confirmation authority."""
import copy
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'tests')]
import g0_forecast_contract as g0
import g0_training_source_contract as training
import prospective_inputs as pi
import research_model_adapter as models
from master_contracts import canonical_bytes, digest
from models import feature_candidate_diagnostics as pure
from test_g0_forecast_contract import base_ref
import test_research_pdca_adapter as parent_cases
import test_training_corpus as corpus_cases

NIGHT = '2026-10-28'
FIT = '2026-10-27T18:00:00+09:00'
CUTOFF = NIGHT + 'T18:00:00+09:00'
TRUTH = '2026-10-29T09:00:00+09:00'
ASSESSMENT = '2026-10-29T11:00:00+09:00'
VERSION = 'habu-research-model-request-v5'


def retime(value):
    if type(value) is str:
        return value.replace('2026-10-14', NIGHT)
    if type(value) is list:
        return [retime(v) for v in value]
    if type(value) is dict:
        return {retime(k): retime(v) for k, v in value.items()}
    return value


def ready(stamp):
    return dict.fromkeys(pi.READINESS_FIELDS, stamp)


class ObservationCorpus:
    add_source = corpus_cases.AuditedTrainingTests.add_source
    add_negative_proofs = corpus_cases.AuditedTrainingTests.add_negative_proofs

    def __init__(self, root, forecast, definitions):
        self.root = root
        self.rows = []
        self.corpus = dict(schema_version='1.0', qualification='AUDITED_TRAIN_ONLY',
                           source_manifest=[], rows=self.rows)
        label = self.add_source('evidence/calibration/outcomes.txt',
            b'explicitly synthetic owner binary outcome fixture',
            '2026-10-29T08:00:00+09:00', 'label')
        feature_path = 'features/sources/weather.json'
        self.add_source(feature_path, (root / feature_path).read_bytes(),
                        NIGHT+'T17:00:00+09:00', 'feature')
        for index, future in enumerate(forecast['rows'][:2]):
            label_value = 1-index
            row = dict(row_id='observation-'+str(index), night=NIGHT,
                cell_x=future['cell_x'], cell_y=future['cell_y'],
                window_start_jst=future['window_start_jst'],
                observation='capture_observed' if label_value else 'observed_negative',
                label=label_value, quality='AUDITED_OBSERVED',
                search_role='SEARCH', all_captures_recorded=True, gpx_segment_eligible=True,
                capture_event_ids=['synthetic-evaluation-event'] if label_value else [],
                source_refs=[label['path'], feature_path], outcome_source_ref=label['path'],
                label_available_at='2026-10-29T08:00:00+09:00', audit_available_at=TRUTH,
                features=copy.deepcopy(future['features']),
                feature_available_at={name:NIGHT+'T17:00:00+09:00' for name in future['features']},
                feature_source_refs={name:[feature_path] for name in future['features']},
                feature_valid_for_night=True)
            if not label_value:
                self.add_negative_proofs(row)
            self.rows.append(row)
        self.definitions = copy.deepcopy(definitions)
        self.selector = dict(heldout_night='2026-10-30',
            fit_cutoff='2026-10-29T10:00:00+09:00',
            forecast_cutoff='2026-10-29T10:00:00+09:00', exposed_nights=[])
        self.publish()

    def bound(self, ref):
        return dict(ref=ref, readiness=ready(TRUTH), usable_at=TRUTH)

    def publish(self):
        self.corpus_ref = base_ref(self.root, 'data/processed/calibration-observations.json',
                                  canonical_bytes(self.corpus))
        paths = {s['path']: ('road-source' if s['role']=='feature' else 'observation-'+str(i))
                 for i,s in enumerate(self.corpus['source_manifest'])}
        nodes = []
        for source in self.corpus['source_manifest']:
            path = source['path']
            raw = (self.root/path).read_bytes()
            parents = ([paths[r['path']] for r in json.loads(raw)['basis_source_refs']]
                       if source['role'] in ('active_search','complete_outcome') else [])
            times = ready(TRUTH)
            times['source_received_at'] = source['received_at']
            nodes.append(dict(id=paths[path], ref=base_ref(self.root,path,raw),
                source_role=source['role'], source_kind='DERIVED' if parents else 'RAW',
                parents=parents, readiness=times, usable_at=TRUTH))
        validity = dict(schema_version='habu-g0-training-validity-v1',
            corpus_sha256=self.corpus_ref['sha256'],
            feature_definition_sha256=digest(sorted(
                [dict(f,code_ref={k:f['code_ref'][k] for k in g0.REF_FIELDS})
                 for f in self.definitions], key=lambda f:f['name'])),
            rows={})
        for row in self.rows:
            start = datetime.fromisoformat(row['window_start_jst'])
            validity['rows'][row['row_id']] = {name:dict(
                valid_time=dict(start=start.isoformat(),end=(start+timedelta(minutes=10)).isoformat()),
                source_ids=[paths[p] for p in row['feature_source_refs'][name]])
                for name in row['features']}
        policy_path = g0.POLICY_PATH
        self.manifest = dict(schema_version=training.VERSION,kind='TRAIN_ONLY_SOURCE_CLOSURE',
            corpus=self.bound(self.corpus_ref),
            policy=self.bound(base_ref(self.root,policy_path,(self.root/policy_path).read_bytes())),
            row_validity=self.bound(base_ref(self.root,'features/calibration-validity.json',canonical_bytes(validity))),
            features=self.definitions, feature_definition_sha256=validity['feature_definition_sha256'],
            source_nodes=nodes, readiness=ready(TRUTH), usable_at=TRUTH)
        self.ref = base_ref(self.root,'protocols/development/calibration-observations.json',
                            canonical_bytes(self.manifest))

    def select(self):
        return training.select_g0_training_rows(self.root,self.ref,
            self.selector['heldout_night'],self.selector['fit_cutoff'],self.selector['forecast_cutoff'],
            expected_feature_definition_sha256=self.manifest['feature_definition_sha256'],
            exposed_nights=self.selector['exposed_nights'])


class CalibrationFixture:
    def __init__(self, case):
        self.case = parent_cases.ResearchConfigV3Tests()
        self.case.setUp()
        case.addCleanup(self.case.doCleanups)
        self.case.full_seven_fixture()
        self.parent, self.root = self.case.parent, self.case.root
        for path in ('src/prospective_candidate_model.py','src/models/hba1_feature_candidate.py'):
            base_ref(self.root,path,(ROOT/path).read_bytes())
        f = self.parent.forecast
        f.objects = retime(f.objects)
        f.nodes = retime(f.nodes)
        f.manifest = retime(f.manifest)
        f.valid = retime(f.valid)
        with patch('test_g0_forecast_contract.READY', NIGHT+'T17:00:00+09:00'):
            f.publish()
        self.parent.request.update(operational_night=NIGHT,fit_cutoff=FIT,
            forecast_cutoff=CUTOFF,forecast_as_of=NIGHT+'T18:30:00+09:00',forecast_manifest=f.ref)
        self.case.update_source()
        self.selected = training.select_g0_training_rows(self.root,self.parent.request['training_manifest'],
            NIGHT,FIT,CUTOFF,expected_feature_definition_sha256=self.parent.request['feature_definition_sha256'])
        self.forecast = g0.load_g0_forecast_rows(self.root,f.ref,NIGHT,
            pi._time(self.parent.request['forecast_as_of']),
            expected_feature_definition_sha256=self.parent.request['feature_definition_sha256'])
        self.prepared = models.prepare_research_candidates_v2(self.selected['selection'],self.forecast['rows'],
            candidate_config=self.case.source.config,expected_config_sha256=digest(self.case.source.config),
            feature_definition_sha256=self.parent.request['feature_definition_sha256'],
            cutoff_time=CUTOFF,joined_universe_sha256=self.forecast['receipt']['canonical_joined_rows_sha256'])
        assert self.prepared['status']=='DIAGNOSTIC_CANDIDATES_PREPARED', self.prepared
        self.observation = ObservationCorpus(self.root,self.forecast,self.parent.training.features)
        self.observed = self.observation.select()
        self.rebind_protocol()
        self.parent.request.update(schema_version=VERSION,calibration_manifest=self.profile_ref,stage1_manifest=None)
        self.parent.publish()

    def rebind_protocol(self):
        self.candidate = next(c for c in self.prepared['candidates'] if c['candidate_id']=='HB-A1')
        lookup = {(u['cell_x'],u['cell_y'],pi._time(u['window_start_jst'])):u
                  for u in self.candidate['prediction']['unit_predictions']}
        self.predictions = [dict(
            {k:row[k] for k in ('row_id','night','cell_x','cell_y','window_start_jst')},
            probability=lookup[(row['cell_x'],row['cell_y'],pi._time(row['window_start_jst']))]['probability'],
            model_sha256=self.candidate['model_sha256'],
            training_selection_sha256=self.selected['selection']['selection_sha256'])
            for row in self.observed['selection']['accepted']]
        self.protocol = dict(schema_version=pure.PROTOCOL_VERSION,phase='DEVELOPMENT',target=pure.TARGET,
            evaluation_selection_sha256=self.observed['selection']['selection_sha256'],
            predictions_sha256=digest(self.predictions),bin_edges=[0,.25,.5,.75,1],log_loss_clip=1e-6,
            folds=[dict(night=NIGHT,model_sha256=self.candidate['model_sha256'],
                training_selection_sha256=self.selected['selection']['selection_sha256'],
                training_cutoff=FIT,train_nights=sorted({r['night'] for r in self.selected['selection']['accepted']}))])
        self.profile = dict(schema_version='habu-feature-calibration-source-v1',
            purpose='DEVELOPMENT_EVALUATION_ONLY',evaluation_as_of=ASSESSMENT,candidate_id='HB-A1',
            protocol=dict(ref=base_ref(self.root,'protocols/development/calibration-protocol.json',
                                      canonical_bytes(self.protocol)),readiness=ready(TRUTH),usable_at=TRUTH),
            observation_manifest=self.observation.ref,observation_selector=self.observation.selector)
        self.publish_profile()

    def publish_profile(self):
        self.profile_ref = base_ref(self.root,'protocols/development/calibration-source.json',
                                   canonical_bytes(self.profile))
        if self.parent.request.get('schema_version')==VERSION:
            self.parent.request['calibration_manifest']=self.profile_ref
            self.parent.publish()

    def call(self, **kwargs):
        from research_pdca_adapter import evaluate_research_request
        return evaluate_research_request(self.root,NIGHT,**kwargs)


class CalibrationParentTests(unittest.TestCase):
    def setUp(self):
        self.f = CalibrationFixture(self)

    def test_native_post_night_positive_keeps_actual_train_and_validation_blocked(self):
        f = self.f
        self.assertEqual(f.observed['selection']['status'],'NEED_MORE_DATA')
        self.assertEqual(f.observed['selection']['counts']['accepted_rows'],2)
        self.assertGreater(pi._time(TRUTH),pi._time(CUTOFF))
        result = f.call()
        self.assertIn('calibration',result,str(result['stages']))
        envelope = result['calibration']
        self.assertEqual(envelope['dispatch_status'],'SOURCE_BOUND_CALIBRATION_DISPATCHED_CONSISTENCY_ONLY')
        child = envelope['diagnostic']
        expected = pure.describe_feature_candidate_development(f.protocol,f.observed['selection'],
            f.predictions,expected_protocol_sha256=digest(f.protocol))
        self.assertEqual(child,expected)
        p0,p1 = [p['probability'] for p in f.predictions]
        self.assertAlmostEqual(child['mean_night_brier'],((1-p0)**2+p1**2)/2)
        self.assertEqual(child['calibration_status'],'NOT_VALIDATED')
        self.assertEqual(result['decision']['decision'],'NEED_MORE_DATA')
        self.assertEqual([c['candidate_id'] for c in result['candidates']],['uniform','HB-A0','HB-A1'])
        native = next(c for c in result['candidates'] if c['candidate_id']=='HB-A1')
        self.assertEqual(native,f.candidate)
        self.assertEqual(native['model']['fit_cutoff'],FIT)
        self.assertEqual(native['prediction']['cutoff_time'],CUTOFF)
        self.assertEqual(len(result['replay']),1)
        self.assertTrue(all(value is False for key,value in envelope.items() if key.endswith('_authorized')))

    def assert_blocked(self, result, *, runtime=False, invalid=False):
        self.assertEqual((result['candidates'],result['replay']),([],[]),str(result))
        self.assertNotIn('calibration',result)
        self.assertTrue(all(s['status']==('FAIL' if invalid else 'BLOCKED') for s in result['stages']),str(result['stages']))
        if not invalid:
            self.assertTrue(all(s['blocker_kind']==('RUNTIME_BLOCKED' if runtime else 'DATA_BLOCKED')
                                for s in result['stages']))
        self.assertEqual(list((self.f.root/'predictions/replay').rglob('*.json')),[])

    def test_observation_payload_only_after_one_real_prepare_and_never_in_train(self):
        f=self.f
        actual=models.prepare_research_candidates_v2
        original_read=g0.G0ArtifactReader.read
        calls=[]
        completed=[]
        def prepare(selection,rows,**options):
            self.assertEqual(selection,f.selected['selection'])
            self.assertEqual(rows,f.forecast['rows'])
            calls.append((selection['selection_sha256'],options['cutoff_time']))
            value=actual(selection,rows,**options)
            completed.append(True)
            return value
        protected={s['path'] for s in f.observation.corpus['source_manifest'] if s['role']!='feature'}
        protected.add(f.observation.corpus_ref['path'])
        def read(reader,ref,**options):
            if ref['path'] in protected:self.assertEqual(completed,[True])
            return original_read(reader,ref,**options)
        with patch.object(models,'prepare_research_candidates_v2',prepare),patch.object(g0.G0ArtifactReader,'read',read):
            result=f.call()
        self.assertIn('calibration',result)
        self.assertEqual(calls,[(f.selected['selection']['selection_sha256'],CUTOFF)])

    def test_actual_preparer_callback_first_falsey_typeerror_is_original(self):
        class Origin(TypeError):
            def __bool__(self):return False
            def __eq__(self,other):raise AssertionError('caller exception equality must not run')
        origin=Origin('opaque caller failure')
        class Context(pi.ProspectiveReadContext):
            def check(self):
                frame=sys._getframe()
                while frame:
                    if frame.f_code.co_name=='_v2_supplied_hba1_raw_fields':raise origin
                    frame=frame.f_back
                return super().check()
        context=Context(300,2*1024**3)
        with self.assertRaises(Origin) as raised:self.f.call(_read_context=context)
        self.assertIs(raised.exception,origin)
        self.assertEqual(list((self.f.root/'predictions/replay').rglob('*.json')),[])

    def test_instance_check_callable_first_escapes_real_parent_unchanged(self):
        from types import MethodType
        class Origin(TypeError):
            def __bool__(self):return False
            def __eq__(self,other):raise AssertionError('caller origin equality must not run')
        for binding in ('function','method'):
            with self.subTest(binding=binding):
                origin=Origin('opaque instance callback origin')
                context=pi.ProspectiveReadContext(300,2*1024**3)
                native_check=context.check
                hits=[]
                def supplied_check(*args):
                    frame=sys._getframe()
                    while frame:
                        if frame.f_code.co_name=='_v2_supplied_hba1_raw_fields':
                            hits.append(True)
                            raise origin
                        frame=frame.f_back
                    return native_check()
                context.check=(supplied_check if binding=='function' else MethodType(supplied_check,context))
                with self.assertRaises(Origin) as raised:self.f.call(_read_context=context)
                self.assertIs(raised.exception,origin)
                self.assertEqual(hits,[True])
                self.assertEqual(list((self.f.root/'predictions/replay').rglob('*.json')),[])

    def test_wrong_actual_fold_rejects_before_observation_payload(self):
        f=self.f
        f.protocol['folds'][0]['training_selection_sha256']='e'*64
        f.profile['protocol']['ref']=base_ref(f.root,f.profile['protocol']['ref']['path'],canonical_bytes(f.protocol))
        f.publish_profile()
        original=g0.G0ArtifactReader.read
        def read(reader,ref,**options):
            self.assertNotEqual(ref['path'],f.observation.corpus_ref['path'])
            return original(reader,ref,**options)
        with patch.object(g0.G0ArtifactReader,'read',read):result=f.call()
        self.assert_blocked(result,invalid=True)

    def test_missing_original_manifest_is_data_blocked_not_selection_json_fallback(self):
        self.f.root.joinpath(self.f.observation.ref['path']).unlink()
        self.assert_blocked(self.f.call())

    def test_selection_json_cannot_substitute_for_original_source_closure(self):
        f=self.f
        f.profile['observation_manifest']=base_ref(f.root,f.observation.ref['path'],canonical_bytes(f.observed['selection']))
        f.publish_profile()
        self.assert_blocked(f.call(),invalid=True)

    def test_protocol_and_profile_reject_extra_fields_and_sealed_namespaces(self):
        f=self.f
        f.profile['observation_manifest']['path']='protocols/development/sealed/outcomes.json'
        f.publish_profile()
        original=g0.G0ArtifactReader.read
        def read(reader,ref,**options):
            self.assertNotIn('/sealed/',ref['path'])
            return original(reader,ref,**options)
        with patch.object(g0.G0ArtifactReader,'read',read):result=f.call()
        self.assert_blocked(result,invalid=True)

    def test_observation_late_readiness_does_not_move_actual_fit(self):
        f=self.f
        f.profile['observation_selector']['fit_cutoff']=TRUTH
        f.publish_profile()
        self.assert_blocked(f.call())

    def test_unknown_observation_never_imputed_as_negative(self):
        f=self.f
        row=f.observation.rows[1]
        row.update(observation='UNKNOWN',label=None,quality='UNKNOWN')
        f.observation.publish()
        f.observed=f.observation.select()
        f.rebind_protocol()
        result=f.call()
        self.assertIn('calibration',result)
        env=result['calibration']
        self.assertEqual(env['source_receipt']['observation_selection_status'],'NEED_MORE_DATA')
        self.assertEqual(sum(b['count'] for b in env['diagnostic']['pooled_reliability_bins']),1)
        self.assertIn('UNKNOWN_NOT_NEGATIVE',env['source_receipt']['observation_rejected'][0]['reasons'])
        self.assertEqual(result['decision']['decision'],'NEED_MORE_DATA')

    def test_no_negative_scope_proof_is_retained_as_rejected_not_zero(self):
        f=self.f
        f.observation.rows[1].pop('active_search_ref')
        f.observation.publish()
        f.observed=f.observation.select()
        f.rebind_protocol()
        result=f.call()
        self.assertIn('calibration',result)
        env=result['calibration']
        self.assertEqual(sum(b['count'] for b in env['diagnostic']['pooled_reliability_bins']),1)
        self.assertIn('NEGATIVE_SCOPE_PROOF_MISSING',env['source_receipt']['observation_rejected'][0]['reasons'])
        self.assertEqual(env['calibration_status'],'NOT_VALIDATED')

    def test_full_other_night_corpus_cannot_hide_behind_selector_rejection(self):
        f=self.f
        row=f.observation.rows[0]
        row['night']='2026-10-27'
        row['window_start_jst']=row['window_start_jst'].replace(NIGHT,row['night'])
        f.observation.publish()
        f.profile['observation_manifest']=f.observation.ref
        f.protocol['evaluation_selection_sha256']=f.observation.select()['selection']['selection_sha256']
        f.profile['protocol']['ref']=base_ref(f.root,f.profile['protocol']['ref']['path'],canonical_bytes(f.protocol))
        f.publish_profile()
        self.assert_blocked(f.call(),invalid=True)

    def test_outside_forecast_accepted_unit_blocks_instead_of_subset_score(self):
        f=self.f
        row=f.observation.rows[0]
        row['cell_x']+=20
        f.observation.publish()
        f.profile['observation_manifest']=f.observation.ref
        f.protocol['evaluation_selection_sha256']=f.observation.select()['selection']['selection_sha256']
        f.profile['protocol']['ref']=base_ref(f.root,f.profile['protocol']['ref']['path'],canonical_bytes(f.protocol))
        f.publish_profile()
        self.assert_blocked(f.call())

    def test_train_event_cannot_be_reused_as_development_observation(self):
        f=self.f
        f.observation.rows[0]['capture_event_ids']=next(r['capture_event_ids']
            for r in f.selected['selection']['accepted'] if r['capture_event_ids'])
        f.observation.publish()
        f.profile['observation_manifest']=f.observation.ref
        f.protocol['evaluation_selection_sha256']=f.observation.select()['selection']['selection_sha256']
        f.profile['protocol']['ref']=base_ref(f.root,f.profile['protocol']['ref']['path'],canonical_bytes(f.protocol))
        f.publish_profile()
        self.assert_blocked(f.call(),invalid=True)

    def test_actual_byte_cap_and_deadline_never_publish_partial_metrics(self):
        for budget in ('bytes','deadline'):
            with self.subTest(budget=budget):
                context=pi.ProspectiveReadContext(300,1024 if budget=='bytes' else 2*1024**3)
                if budget=='deadline':context.deadline=0
                self.assert_blocked(self.f.call(_read_context=context),runtime=True)

    def test_final_source_mutation_after_stage_build_is_detected(self):
        import research_pdca_adapter as parent
        actual=parent.stage
        changed=[]
        def stage(*args,**kwargs):
            if not changed:
                target=self.f.root/self.f.observation.corpus_ref['path']
                raw=target.read_bytes()
                target.write_bytes(bytes([raw[0]^1])+raw[1:])
                changed.append(True)
            return actual(*args,**kwargs)
        with patch.object(parent,'stage',stage):result=self.f.call()
        self.assertEqual(changed,[True])
        self.assert_blocked(result,invalid=True)

    def test_changed_outcome_does_not_change_actual_model_or_native_prediction(self):
        f=self.f
        original=f.call()
        original_replay=f.root/original['replay'][0]['path']
        before=original_replay.read_bytes()
        row=f.observation.rows[0]
        row.update(observation='UNKNOWN',label=None,quality='UNKNOWN',capture_event_ids=[])
        f.observation.publish()
        f.observed=f.observation.select()
        f.rebind_protocol()
        changed=f.call()
        self.assertIn('calibration',changed)
        self.assertEqual(original['candidates'],changed['candidates'])
        self.assertNotEqual(original['calibration']['diagnostic'],changed['calibration']['diagnostic'])
        self.assertEqual(original_replay.read_bytes(),before)

    def test_every_original_ref_and_shared_actual_byte_ledger_are_preserved(self):
        class Context(pi.ProspectiveReadContext):
            def __init__(self):
                super().__init__(300,2*1024**3)
                self.counts=[]
            def account(self,n):
                self.counts.append(n)
                super().account(n)
        context=Context()
        context.account(17)
        deadline=context.deadline
        result=self.f.call(_read_context=context)
        self.assertIn('calibration',result)
        self.assertLessEqual(context.deadline,deadline)
        self.assertEqual(context.bytes_read,sum(context.counts))
        self.assertEqual(result['evidence']['actual_read_bytes'],context.bytes_read)
        receipt=result['calibration']['source_receipt']
        paths={r['path'] for r in receipt['consumed_refs']}
        self.assertIn(self.f.observation.ref['path'],paths)
        self.assertIn(self.f.observation.corpus_ref['path'],paths)
        self.assertIn(self.f.profile_ref['path'],paths)
        self.assertIn(self.f.profile['protocol']['ref']['path'],paths)
        for source in self.f.observation.corpus['source_manifest']:
            self.assertIn(source['path'],paths)

    def test_oversized_native_preparation_is_runtime_blocked_before_truth(self):
        actual=models.prepare_research_candidates_v2
        def prepare(*args,**kwargs):
            value=actual(*args,**kwargs)
            value['unexpected_large_json']='x'*(17*1024**2)
            return value
        with patch.object(models,'prepare_research_candidates_v2',prepare):result=self.f.call()
        self.assert_blocked(result,runtime=True)

    def test_profile_physical_size_cap_stops_before_payload(self):
        f=self.f
        raw=canonical_bytes(f.profile)+b' '*(256*1024)
        f.profile_ref=base_ref(f.root,f.profile_ref['path'],raw)
        f.parent.request['calibration_manifest']=f.profile_ref
        f.parent.publish()
        self.assert_blocked(f.call(),runtime=True)

    def test_known_rehashed_probability_cannot_disagree_with_native_model(self):
        actual=models.prepare_research_candidates_v2
        def prepare(*args,**kwargs):
            value=actual(*args,**kwargs)
            candidate=next(c for c in value['candidates'] if c['candidate_id']=='HB-A1')
            unit=candidate['prediction']['unit_predictions'][0]
            unit['probability']=unit['spatial_score']=0.12345678
            candidate['prediction']['prediction_sha256']=digest({k:v for k,v in candidate['prediction'].items()
                                                                 if k!='prediction_sha256'})
            candidate['prediction_sha256']=candidate['prediction']['prediction_sha256']
            value['receipt_sha256']=digest({k:v for k,v in value.items() if k!='receipt_sha256'})
            return value
        with patch.object(models,'prepare_research_candidates_v2',prepare):result=self.f.call()
        self.assert_blocked(result,invalid=True)

    def test_empty_qualified_cohort_returns_missing_data_no_means(self):
        f=self.f
        f.observation.rows.clear()
        f.observation.publish()
        f.profile['observation_manifest']=f.observation.ref
        f.protocol['evaluation_selection_sha256']=f.observation.select()['selection']['selection_sha256']
        f.protocol['predictions_sha256']=digest([])
        f.profile['protocol']['ref']=base_ref(f.root,f.profile['protocol']['ref']['path'],canonical_bytes(f.protocol))
        f.publish_profile()
        self.assert_blocked(f.call())

    def test_source_growth_after_calibration_is_capacity_not_success(self):
        import research_pdca_adapter as parent
        actual=parent.stage
        def stage(*args,**kwargs):
            target=self.f.root/self.f.observation.corpus_ref['path']
            target.write_bytes(target.read_bytes()+b' ')
            return actual(*args,**kwargs)
        with patch.object(parent,'stage',stage):result=self.f.call()
        self.assert_blocked(result,runtime=True)

    def test_deadline_expiry_after_descriptive_result_drops_metrics_and_replay(self):
        import research_pdca_adapter as parent
        context=pi.ProspectiveReadContext(300,2*1024**3)
        actual=parent.stage
        def stage(*args,**kwargs):
            context.deadline=0
            return actual(*args,**kwargs)
        with patch.object(parent,'stage',stage):result=self.f.call(_read_context=context)
        self.assert_blocked(result,runtime=True)

    def test_v5_cannot_co_dispatch_stage1_or_other_candidates(self):
        self.f.parent.request['stage1_manifest']=self.f.observation.ref
        self.f.parent.publish()
        self.assert_blocked(self.f.call(),invalid=True)

    def test_original_selector_boundary_is_not_synthesized_from_assessment(self):
        f=self.f
        f.profile['observation_selector']['fit_cutoff']=ASSESSMENT
        f.profile['observation_selector']['forecast_cutoff']=ASSESSMENT
        f.publish_profile()
        self.assert_blocked(f.call(),invalid=True)

    def test_json_depth_capacity_is_runtime_not_invalid_or_success(self):
        nested=None
        for _ in range(14):nested=[nested]
        self.f.profile['extra']=nested
        self.f.publish_profile()
        self.assert_blocked(self.f.call(),runtime=True)

    def test_insufficient_actual_train_never_reads_observation_truth(self):
        f=self.f
        train=f.parent.training
        train.fixture.rows.clear()
        train.fixture.publish()
        train.build_manifest()
        f.parent.request['training_manifest']=train.ref
        f.parent.publish()
        original=g0.G0ArtifactReader.read
        def read(reader,ref,**options):
            self.assertNotEqual(ref['path'],f.observation.corpus_ref['path'])
            return original(reader,ref,**options)
        with patch.object(g0.G0ArtifactReader,'read',read):result=f.call()
        self.assert_blocked(result)

    def test_unknown_profile_field_is_invalid_not_silently_ignored(self):
        self.f.profile['predictions']=self.f.predictions
        self.f.publish_profile()
        self.assert_blocked(self.f.call(),invalid=True)

    def test_protocol_equal_assessment_readiness_is_data_blocked(self):
        self.f.profile['protocol'].update(readiness=ready(ASSESSMENT),usable_at=ASSESSMENT)
        self.f.publish_profile()
        self.assert_blocked(self.f.call())

    def test_post_stage_native_model_mutation_is_not_published(self):
        import research_pdca_adapter as parent
        actual=parent.stage
        original=models.prepare_research_candidates_v2
        prepared=[]
        def prepare(*args,**kwargs):
            value=original(*args,**kwargs)
            prepared.append(value)
            return value
        def stage(*args,**kwargs):
            prepared[0]['candidates'][2]['model']['coefficients'][0]+=1
            return actual(*args,**kwargs)
        with patch.object(models,'prepare_research_candidates_v2',prepare),patch.object(parent,'stage',stage):
            result=self.f.call()
        self.assert_blocked(result,invalid=True)

    def test_malformed_bins_are_rejected_before_observation_payload(self):
        f=self.f
        f.protocol['bin_edges']=[0,.7,.5,1]
        f.profile['protocol']['ref']=base_ref(f.root,f.profile['protocol']['ref']['path'],canonical_bytes(f.protocol))
        f.publish_profile()
        original=g0.G0ArtifactReader.read
        def read(reader,ref,**options):
            self.assertNotEqual(ref['path'],f.observation.corpus_ref['path'])
            return original(reader,ref,**options)
        with patch.object(g0.G0ArtifactReader,'read',read):result=f.call()
        self.assert_blocked(result,invalid=True)

    def test_known_selection_hash_contradiction_is_not_hidden_by_empty_data(self):
        f=self.f
        f.observation.rows.clear()
        f.observation.publish()
        f.profile['observation_manifest']=f.observation.ref
        f.publish_profile()
        self.assert_blocked(f.call(),invalid=True)

    def test_all_unknown_cohort_preserves_each_original_rejection_without_metrics(self):
        f=self.f
        for row in f.observation.rows:
            row.update(observation='UNKNOWN',label=None,quality='UNKNOWN',capture_event_ids=[])
        f.observation.publish()
        original=f.observation.select()['selection']
        f.protocol['evaluation_selection_sha256']=original['selection_sha256']
        f.protocol['predictions_sha256']=digest([])
        f.profile['observation_manifest']=f.observation.ref
        f.profile['protocol']['ref']=base_ref(f.root,f.profile['protocol']['ref']['path'],canonical_bytes(f.protocol))
        f.publish_profile()
        result=f.call()
        self.assert_blocked(result)
        self.assertIn('calibration_observation_blockers',result)
        details=result['calibration_observation_blockers']
        self.assertEqual(details['rejected'],original['rejected'])
        self.assertEqual(details['blockers'],original['blockers'])
        self.assertNotIn('diagnostic',details)

    def test_late_prepared_self_hash_change_cannot_be_published(self):
        import research_pdca_adapter as parent
        actual=parent.stage
        original=models.prepare_research_candidates_v2
        prepared=[]
        def prepare(*args,**kwargs):
            value=original(*args,**kwargs)
            prepared.append(value)
            return value
        def stage(*args,**kwargs):
            prepared[0]['receipt_sha256']='f'*64
            return actual(*args,**kwargs)
        with patch.object(models,'prepare_research_candidates_v2',prepare),patch.object(parent,'stage',stage):
            result=self.f.call()
        self.assert_blocked(result,invalid=True)

    def test_legitimate_corpus_above_small_metadata_cap_uses_original_corpus_limit(self):
        f=self.f
        f.observation.corpus['synthetic_padding']=['x'*4096 for _ in range(2048)]
        f.observation.publish()
        self.assertGreater(f.observation.corpus_ref['size_bytes'],g0.MAX_SMALL_BYTES)
        self.assertLess(f.observation.corpus_ref['size_bytes'],16*1024**2)
        f.observed=f.observation.select()
        f.rebind_protocol()
        result=f.call()
        self.assertIn('calibration',result,str(result['stages']))
        self.assertEqual(result['calibration']['diagnostic']['calibration_status'],'NOT_VALIDATED')
        self.assertEqual(result['decision']['decision'],'NEED_MORE_DATA')


if __name__ == '__main__':
    unittest.main()
