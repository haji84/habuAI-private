import importlib
import importlib.util
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from master_contracts import digest, file_hash, canonical_bytes
import model_evaluation


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b'\n')
    return {'path': relative, 'sha256': file_hash(path)}


def model_fixture(probability=.2):
    body = dict(schema_version='1.0', family='uniform', implementation_version=model_evaluation.VERSION,
                parameters={'area_values': {}, 'default': probability, 'smoothing': 1.0},
                hyperparameters={'smoothing': 1.0, 'area_size_m': 1000, 'effort_reference_seconds': None},
                status='CANDIDATE', evidence_refs=[], training_cutoff='2026-09-01T00:00:00+09:00',
                training_data_sha256=digest([]), feature_schema_sha256=digest([]), protocol_sha256=digest({}),
                code_sha256=file_hash(Path(model_evaluation.__file__)), produced_outputs=['spatial_score', 'unit_probability'])
    return dict(body, model_id=digest(body), model_sha256=digest(body))


def evidence_fixture(root, probability=.2):
    model = model_fixture(probability)
    reference = write(root, 'models/'+model['model_id']+'.json', model)
    evidence = {'schema_version': '1.0', 'model': reference, 'model_id': model['model_id'],
                'folds': [], 'qualification': 'SYNTHETIC_FIXTURE', 'decision': 'ACCEPT_CANDIDATE', 'trusted': True}
    ref = write(root, 'evidence/'+model['model_id']+'.json', evidence)
    return model, root/ref['path']


class ChampionRegistryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('champion_registry'), 'Champion registry missing')
        self.r = importlib.import_module('champion_registry')

    def test_production_activation_ignores_self_declared_trust(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); model, evidence=evidence_fixture(root)
            result=self.r.promote(root, model['model_id'], evidence, None)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertIn('IMPLEMENTATION_BLOCKED', str(result))
            self.assertIsNone(self.r.champion_at(root, '2099-01-01T00:00:00Z'))
            self.assertFalse((root/'models/champion_registry').exists())

    def test_candidate_validation_rejects_tampered_model_and_wrong_adapter(self):
        for change in ['tamper', 'adapter']:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as td:
                root=Path(td); model, path=evidence_fixture(root)
                value=json.loads(path.read_text()); mp=root/value['model']['path']
                artifact=json.loads(mp.read_text()); artifact['parameters']['default']=.9
                if change == 'adapter':
                    artifact['implementation_version']='unreviewed-v999'
                    body={k:v for k,v in artifact.items() if k not in ('model_id','model_sha256')}
                    artifact.update(model_id=digest(body), model_sha256=digest(body))
                    value['model_id']=artifact['model_id']
                mp.write_bytes(canonical_bytes(artifact))
                if change == 'adapter':
                    value['model']['sha256']=file_hash(mp)
                result=self.r.validate_candidate(root, value)
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['decision'], 'REJECT_CANDIDATE')

    def test_artifact_mutation_between_hash_and_decode_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _, path=evidence_fixture(root)
            value=json.loads(path.read_text())
            reference=write(root,'evidence/outcomes.json',{'captures':1})
            value['artifact_refs']=[reference]
            original=self.r.file_hash
            def change_after_hash(path):
                result=original(path)
                if path.name=='outcomes.json': path.write_text('{"captures":0}')
                return result
            with patch.object(self.r,'file_hash',side_effect=change_after_hash):
                result=self.r.validate_candidate(root,value)
            self.assertEqual(result['status'],'FAIL')

    def test_retry_same_transition_is_idempotent_and_code_identity_is_bound(self):
        with self.r.sandbox_registry() as ctx:
            model,path=evidence_fixture(ctx.root)
            first=self.r.promote(ctx,model['model_id'],path,None)
            self.assertEqual(self.r.promote(ctx,model['model_id'],path,None),first)
            artifact=json.loads(path.read_text())
            model_path=ctx.root/artifact['model']['path']
            forged=json.loads(model_path.read_text()); forged['code_sha256']='0'*64
            body={k:v for k,v in forged.items() if k not in ('model_id','model_sha256')}
            forged.update(model_id=digest(body),model_sha256=digest(body))
            artifact['model']=write(ctx.root,'models/forged.json',forged); artifact['model_id']=forged['model_id']
            self.assertEqual(self.r.validate_candidate(ctx.root,artifact)['status'],'FAIL')

    def test_invalid_probability_state_rejected_even_without_matching_rows(self):
        for family, field in [('uniform','default'), ('uniform','unused_area'),
                              ('observed_unit_prevalence','default'), ('observed_unit_prevalence','unused_area')]:
            for rows in [[], [{'row_id':'x','operational_night':'2026-09-30',
                               'cutoff_time':'2026-09-30T19:00:00+09:00',
                               'utm_x_m':400050, 'utm_y_m':3000050}]]:
                with self.subTest(family=family, field=field, rows=rows), self.r.sandbox_registry() as ctx:
                    model=model_fixture(); model['family']=family
                    if field=='default': model['parameters']['default']=1.5
                    else: model['parameters']['area_values']['899,9999']=1.5
                    body={k:v for k,v in model.items() if k not in ('model_id','model_sha256')}
                    model.update(model_id=digest(body),model_sha256=digest(body))
                    with self.assertRaisesRegex(ValueError,'probability'):
                        model_evaluation.predict_model(model,rows)
                    reference=write(ctx.root,'models/invalid.json',model)
                    evidence={'schema_version':'1.0','model':reference,'model_id':model['model_id']}
                    self.assertEqual(self.r.validate_candidate(ctx.root,evidence)['status'],'FAIL')
                    path=ctx.root/write(ctx.root,'evidence/invalid.json',evidence)['path']
                    with self.assertRaises(ValueError): self.r.promote(ctx,model['model_id'],path,None)
                    self.assertIsNone(self.r.champion_at(ctx,'2099-01-01T00:00:00Z'))

    def test_score_only_fitted_values_above_one_remain_valid(self):
        for family in ['historical_capture_prior','duration_normalized_area_rate']:
            with self.subTest(family=family):
                model=model_fixture(); model.update(family=family,produced_outputs=['spatial_score'])
                model['parameters'].update(default=1.5,area_values={'899,9999':2.0})
                body={k:v for k,v in model.items() if k not in ('model_id','model_sha256')}
                model.update(model_id=digest(body),model_sha256=digest(body))
                self.assertEqual(model_evaluation.predict_model(model,[]),[])
                rows=model_evaluation.predict_model(model,[{'row_id':'x','operational_night':'2026-09-30',
                     'cutoff_time':'2026-09-30T19:00:00+09:00','utm_x_m':400050,'utm_y_m':3000050}])
                self.assertIsNone(rows[0]['probability'])
                self.assertEqual(rows[0]['spatial_score'],1.5)

    def test_restricted_summary_and_insufficient_folds_never_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _, path=evidence_fixture(root)
            value=json.loads(path.read_text())
            value['folds']=[{'night':'2026-09-01','metrics':{'stage1':{'restricted_individual_recall':1.0,'gate_outcome':'PASS'}}}]
            result=self.r.validate_candidate(root, value)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertNotEqual(result['decision'], 'ACCEPT_CANDIDATE')
            self.assertIn('outcome', str(result).lower())
            self.assertIn('formal', str(result).lower())
            self.assertIn('confirmation', str(result).lower())

    def test_sandbox_lifecycle_preserves_artifact_and_historical_selection(self):
        with self.r.sandbox_registry() as ctx:
            a, ap=evidence_fixture(ctx.root, .2); b, bp=evidence_fixture(ctx.root, .8)
            with patch.object(self.r, '_now', return_value='2026-09-29T18:00:00+09:00'):
                first=self.r.promote(ctx, a['model_id'], ap, None)
            with patch.object(self.r, '_now', return_value='2026-09-30T18:00:00+09:00'):
                second=self.r.promote(ctx, b['model_id'], bp, first['event_sha256'])
            self.assertEqual(first['qualification'], 'SANDBOX_MECHANICS')
            old=self.r.champion_at(ctx, '2026-09-29T19:00:00+09:00')
            self.assertEqual(old['model']['model_id'], a['model_id'])
            self.assertEqual(old['model']['status'], 'CANDIDATE')
            self.assertEqual(self.r.champion_at(ctx, '2026-09-30T19:00:00+09:00')['model']['model_id'], b['model_id'])
            self.assertIsNone(self.r.champion_at(ctx.root, '2099-01-01T00:00:00Z'))
            rollback=self.r.rollback(ctx, a['model_id'], 'mechanical rollback', second['event_sha256'])
            self.assertEqual(rollback['next_model_id'], a['model_id'])
            with self.assertRaises(ValueError):
                self.r.promote(ctx, b['model_id'], bp, first['event_sha256'])  # ABA stale token

    def test_sandbox_context_cannot_be_reused_after_exit(self):
        with self.r.sandbox_registry() as ctx:
            model, path=evidence_fixture(ctx.root)
        with self.assertRaises(ValueError):
            self.r.promote(ctx, model['model_id'], path, None)

    def test_cas_concurrency_allows_one_transition(self):
        with self.r.sandbox_registry() as ctx:
            a, ap=evidence_fixture(ctx.root, .2); b,bp=evidence_fixture(ctx.root,.8)
            def attempt(item):
                model,path=item
                try: return self.r.promote(ctx, model['model_id'], path, None)
                except ValueError: return None
            with ThreadPoolExecutor(2) as pool:
                results=list(pool.map(attempt, [(a,ap),(b,bp)]))
            self.assertEqual(sum(r is not None for r in results), 1)

    def test_orphan_event_before_pointer_commit_never_becomes_active(self):
        with self.r.sandbox_registry() as ctx:
            a, ap=evidence_fixture(ctx.root)
            with patch.object(self.r, '_commit_pointer', side_effect=OSError('crash')):
                with self.assertRaises(OSError): self.r.promote(ctx,a['model_id'],ap,None)
            self.assertIsNone(self.r.champion_at(ctx, '2099-01-01T00:00:00Z'))
            result=self.r.promote(ctx,a['model_id'],ap,None)
            self.assertEqual(self.r.champion_at(ctx, '2099-01-01T00:00:00Z')['event']['event_sha256'],result['event_sha256'])

    def test_changed_committed_evidence_or_event_fails_lookup(self):
        for kind in ['evidence','event','model']:
            with self.subTest(kind=kind), self.r.sandbox_registry() as ctx:
                model,path=evidence_fixture(ctx.root)
                event=self.r.promote(ctx,model['model_id'],path,None)
                record=self.r.champion_at(ctx,'2099-01-01T00:00:00Z')
                if kind=='event': path=ctx.root / event['event_path']
                elif kind=='model': path=ctx.root / record['model_path']
                path.write_text('{}')
                with self.assertRaises(ValueError): self.r.champion_at(ctx,'2099-01-01T00:00:00Z')

    def test_rollback_requires_prior_committed_validated_record(self):
        with self.r.sandbox_registry() as ctx:
            a,ap=evidence_fixture(ctx.root,.2); b,bp=evidence_fixture(ctx.root,.8)
            first=self.r.promote(ctx,a['model_id'],ap,None)
            with self.assertRaises(ValueError): self.r.rollback(ctx,b['model_id'],'not active before',first['event_sha256'])

    def test_adapter_preserves_failures_and_blocker_classes_without_writes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source={'stages':[{'name':'candidate_validation','status':'FAIL','reason':'tampered'}],
                    'implementation_blockers':['executor absent'], 'data_blockers':['labels absent'],
                    'runtime_blockers':['budget'], 'decision':{'decision':'REJECT_CANDIDATE','reasons':['tampered']}}
            result=self.r.evaluate_promotion(root,'2026-09-30',source)
            self.assertEqual([s['name'] for s in result['stages']],['promotion_decision','champion_handoff'])
            self.assertEqual(result['stages'][0]['status'],'FAIL')
            self.assertEqual(result['decision']['decision'],'REJECT_CANDIDATE')
            self.assertIn('tampered', str(result['decision']['reasons']))
            for key in ['implementation_blockers','data_blockers','runtime_blockers']:
                self.assertTrue(set(source[key]) <= set(result[key]))
            self.assertEqual(list(root.iterdir()), [])
