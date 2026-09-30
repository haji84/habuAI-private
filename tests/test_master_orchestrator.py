import importlib.util
import json
import types
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

class MasterTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('master_orchestrator'), 'durable master orchestrator is missing')
        import master_orchestrator
        self.master = master_orchestrator
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_master(self, budget=300):
        return self.master.run_master(self.root, '2026-09-30', budget)

    def file(self, path, content='{}'):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def test_missing_evidence_returns_every_stage_and_honest_blockers(self):
        r = self.run_master()
        self.assertEqual(r['overall_status'], 'BLOCKED')
        self.assertFalse(r['completed'])
        self.assertEqual({s['name'] for s in r['stages']}, {'evidence_audit', 'operational_scoring', 'model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation', 'development', 'promotion_decision', 'champion_handoff'})
        self.assertTrue(r['implementation_blockers'])
        self.assertTrue(r['data_blockers'])
        self.assertEqual(json.loads((self.root/'reports/pdca/2026-09-30/pdca_result.json').read_text())['run_id'], r['run_id'])

    def test_duplicate_reuses_verified_run_and_input_changes_make_new_run(self):
        source = self.file('data/processed/model_learning.json')
        r = self.run_master()
        self.assertEqual(self.run_master(), r)
        source.write_text('{"changed":true}')
        self.assertNotEqual(self.run_master()['run_id'], r['run_id'])

    def test_original_and_raw_bytes_preserved(self):
        a = self.file('data/raw/sample.bin', 'raw bytes')
        b = self.file('predictions/original/2026-09-30/P0/prediction.json', '{broken')
        r = self.run_master()
        self.assertEqual(r['overall_status'], 'FAIL')
        self.assertEqual(a.read_text(), 'raw bytes')
        self.assertEqual(b.read_text(), '{broken')

    def test_midrun_learning_mutation_fails_even_with_snapshot(self):
        source = self.file('data/processed/model_learning.json')
        original = self.master.run_pipeline
        def mutate(root, night, **kwargs):
            self.assertNotEqual(root, self.root)
            source.write_text('{"changed":true}')
            return original(root, night, **kwargs)
        with patch.object(self.master, 'run_pipeline', mutate):
            r = self.run_master()
        self.assertEqual(r['overall_status'], 'FAIL')
        self.assertIn('INPUT_CHANGED', str(r))

    def test_corrupt_stage_output_rejected_not_reused(self):
        r = self.run_master()
        output = self.root/'reports/pdca/2026-09-30/runs'/r['run_id']/'stages/operational_scoring.json'
        output.write_text('{}')
        retry = self.run_master()
        self.assertEqual(retry['overall_status'], 'FAIL')
        self.assertIn('CHECKPOINT_INVALID', str(retry))

    def test_corrupt_checkpoint_rejected(self):
        r = self.run_master()
        p = self.root/'reports/pdca/2026-09-30/runs'/r['run_id']/'checkpoint.json'
        p.write_text('{broken')
        self.assertEqual(self.run_master()['overall_status'], 'FAIL')

    def test_interruption_persists_fail_and_budget_ledger(self):
        with patch.object(self.master, 'run_pipeline', side_effect=KeyboardInterrupt):
            r = self.run_master()
        self.assertEqual(r['overall_status'], 'FAIL')
        self.assertIn('INTERRUPTED', str(r))
        self.assertGreaterEqual(self.run_master()['budget']['elapsed_seconds'], r['budget']['elapsed_seconds'])

    def test_budget_exhaustion_has_all_stages_and_retry_conditions(self):
        r = self.run_master(0)
        self.assertEqual(len(r['stages']), 9)
        self.assertEqual(r['overall_status'], 'BLOCKED')
        self.assertIn('BUDGET_EXHAUSTED', str(r))
        self.assertTrue(r['required_conditions'])
        self.assertEqual(self.run_master(0)['budget'], r['budget'])

    def test_interrupted_stage_resumes_and_preserves_elapsed_budget(self):
        with patch.object(self.master, 'run_pipeline', side_effect=KeyboardInterrupt):
            interrupted = self.run_master()
        resumed = self.run_master()
        operational = next(s for s in resumed['stages'] if s['name'] == 'operational_scoring')
        self.assertEqual(operational['status'], 'BLOCKED')
        self.assertNotIn('INTERRUPTED', operational['reason'])
        self.assertGreaterEqual(resumed['budget']['elapsed_seconds'], interrupted['budget']['elapsed_seconds'])

    def test_budget_retry_requires_larger_limit_and_preserves_ledger(self):
        first = self.run_master(0)
        retry = self.run_master(300)
        operational = next(s for s in retry['stages'] if s['name'] == 'operational_scoring')
        self.assertNotIn('BUDGET_EXHAUSTED', operational['reason'])
        self.assertEqual(first['run_id'], retry['run_id'])
        self.assertGreaterEqual(retry['budget']['elapsed_seconds'], first['budget']['elapsed_seconds'])

    def test_operational_exception_still_attempts_independent_research(self):
        self.file('predictions/original/2026-09-30/P0/prediction.json', '{broken')
        # This unit test exercises unavailable-adapter behavior explicitly, even
        # after the real model adapter is installed by a later slice.
        with patch.object(self.master, '_adapter', return_value=None) as adapter:
            r = self.run_master()
        adapter.assert_any_call('model_evaluation', 'evaluate_models')
        research = next(s for s in r['stages'] if s['name'] == 'feature_research')
        self.assertEqual(research['blocker_kind'], 'IMPLEMENTATION_BLOCKED')
        self.assertIn('evaluate_models', research['reason'])

    def test_tampered_generated_operational_artifact_invalidates_resume(self):
        r = self.run_master()
        p = self.root/'reports/pdca/2026-09-30/runs'/r['run_id']/'snapshot/reports/pdca/2026-09-30/pdca_result.json'
        p.write_text('{}')
        self.assertEqual(self.run_master()['overall_status'], 'FAIL')

    def test_independent_model_adapter_receives_snapshot_and_generated_replay_survives(self):
        def evaluate(root, night, budget):
            self.assertNotEqual(root, self.root)
            replay = root/'predictions/replay/example.json'
            replay.parent.mkdir(parents=True)
            replay.write_text('{"replay":true}')
            return {'schema_version': '1.0', 'stages': [
                {'name': name, 'status': 'BLOCKED', 'reason': 'Missing audited learning rows',
                 'requires': ['audited learning rows'], 'evidence': [], 'metrics': {},
                 'implementation_version': 'test-adapter'}
                for name in ('model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation')],
                'candidates': [], 'folds': [], 'replay': [], 'research_questions': [],
                'decision': {'decision': 'NEED_MORE_DATA', 'reasons': [], 'required_conditions': []},
                'implementation_blockers': [], 'data_blockers': ['Audited learning rows']}
        with patch.dict(sys.modules, {'model_evaluation': types.SimpleNamespace(evaluate_models=evaluate)}):
            result = self.run_master()
        self.assertNotEqual(result['overall_status'], 'FAIL')
        self.assertFalse((self.root/'predictions/replay/example.json').exists())
        self.assertIn('Audited learning rows', result['data_blockers'])
        self.assertEqual(self.run_master(), result)

    def test_hard_interruption_charges_inflight_time_before_resuming(self):
        script = """import sys, os
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import master_orchestrator as m
def die(root, night, **kwargs):
    os._exit(77)
m.run_pipeline = die
m.run_master(Path(sys.argv[2]), '2026-09-30', 300)
"""
        p = subprocess.run([sys.executable, '-c', script, str(ROOT/'src'), str(self.root)])
        self.assertEqual(p.returncode, 77)
        cp = next((self.root/'reports/pdca/2026-09-30/runs').glob('*/checkpoint.json'))
        checkpoint = json.loads(cp.read_text())
        self.assertEqual(checkpoint.get('active_stage'), 'operational_scoring')
        self.assertIsNotNone(checkpoint['active_since'])
        result = self.run_master()
        self.assertNotEqual(result['overall_status'], 'FAIL')
        self.assertGreaterEqual(result['budget']['elapsed_seconds'], checkpoint['elapsed_seconds'])

    def test_concurrent_cli_commands_share_one_verified_run(self):
        command = [sys.executable, str(ROOT/'scripts/run_pdca.py'), '--root', str(self.root), '--night', '2026-09-30']
        a = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        b = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        x, xe = a.communicate(timeout=30)
        y, ye = b.communicate(timeout=30)
        self.assertEqual((a.returncode, b.returncode), (2, 2), (xe, ye))
        self.assertEqual(json.loads(x), json.loads(y))
        self.assertEqual(len(list((self.root/'reports/pdca/2026-09-30/runs').iterdir())), 1)

    def test_malformed_adapter_blockers_become_fail_not_exception(self):
        def evaluate(root, night, budget):
            return {'schema_version': '1.0', 'stages': [
                {'name': name, 'status': 'BLOCKED', 'reason': 'Evidence missing',
                 'requires': [], 'evidence': [], 'metrics': {}, 'implementation_version': 'test'}
                for name in ('model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation')],
                'candidates': [], 'implementation_blockers': [{'malformed': True}], 'data_blockers': []}
        with patch.dict(sys.modules, {'model_evaluation': types.SimpleNamespace(evaluate_models=evaluate)}):
            result = self.run_master()
        self.assertEqual(result['overall_status'], 'FAIL')

    def test_final_manifest_references_an_existing_verified_checkpoint(self):
        result = self.run_master()
        directory = self.root/'reports/pdca/2026-09-30/runs'/result['run_id']
        cp = json.loads((directory/'checkpoint.json').read_text())
        from master_contracts import digest
        self.assertTrue(any(digest(json.loads(p.read_text())) == result['checkpoint_sha256']
                            for p in directory.glob('*checkpoint*.json')))
        self.assertTrue(cp['result_sha256'])

    def test_code_policy_and_champion_identity_changes_invalidate_previous_run(self):
        result = self.run_master()
        for path in ('src/adapter.py', 'policies/promotion.json', 'models/current.json', 'requirements-analysis.txt'):
            self.file(path, 'changed')
            changed = self.run_master()
            self.assertNotEqual(changed['run_id'], result['run_id'])
            result = changed

    def interrupt_after_operational(self):
        script = """import sys, os, types
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import master_orchestrator as m
def die(root, night, budget):
    os._exit(77)
sys.modules['model_evaluation'] = types.SimpleNamespace(evaluate_models=die)
m.run_master(Path(sys.argv[2]), '2026-09-30', 300)
"""
        result = subprocess.run([sys.executable, '-c', script, str(ROOT/'src'), str(self.root)])
        self.assertEqual(result.returncode, 77)
        return next((self.root/'reports/pdca/2026-09-30/runs').iterdir())

    def test_interrupted_run_rejects_tampered_completed_stage_artifact(self):
        directory = self.interrupt_after_operational()
        (directory/'snapshot/reports/pdca/2026-09-30/pdca_result.json').write_text('{"tampered":true}')
        result = self.run_master()
        self.assertEqual(result['overall_status'], 'FAIL')
        self.assertIn('CHECKPOINT_INVALID', str(result))

    def test_interrupted_run_rejects_uncommitted_new_replay_artifact(self):
        directory = self.interrupt_after_operational()
        replay = directory/'snapshot/predictions/replay/injected.json'
        replay.parent.mkdir(parents=True)
        replay.write_text('{"injected":true}')
        result = self.run_master()
        self.assertEqual(result['overall_status'], 'FAIL')
        self.assertIn('CHECKPOINT_INVALID', str(result))

    def test_malformed_operational_blockers_replace_stale_pass(self):
        pointer = self.file('reports/pdca/2026-09-30/pdca_result.json', '{"overall_status":"PASS"}')
        payload = {'overall_status': 'PASS', 'stages': [], 'implementation_blockers': [{}]}
        with patch.object(self.master, 'run_pipeline', return_value=payload):
            result = self.run_master()
        self.assertEqual(result['overall_status'], 'FAIL')
        self.assertEqual(json.loads(pointer.read_text())['overall_status'], 'FAIL')

    def test_contradictory_operational_pass_cannot_validate_failed_child(self):
        payload = {'overall_status': 'PASS', 'stages': [{'name': 'integrity', 'status': 'FAIL', 'reason': 'hash mismatch'}]}
        with patch.object(self.master, 'run_pipeline', return_value=payload):
            result = self.run_master()
        operational = next(s for s in result['stages'] if s['name'] == 'operational_scoring')
        self.assertEqual(operational['status'], 'FAIL')
        self.assertEqual(operational['validity_status'], 'INVALID')
        self.assertTrue(any(s['name'] == 'feature_research' for s in result['stages']))

    def test_missing_operational_stage_structure_fails(self):
        for stages in ([], [{}], 'invalid'):
            with self.subTest(stages=stages), tempfile.TemporaryDirectory() as td:
                with patch.object(self.master, 'run_pipeline', return_value={'overall_status':'PASS', 'stages': stages}):
                    result = self.master.run_master(Path(td), '2026-09-30')
                self.assertEqual(result['overall_status'], 'FAIL')

    def test_generated_artifact_validation_failure_replaces_stale_pass(self):
        pointer = self.file('reports/pdca/2026-09-30/pdca_result.json', '{"overall_status":"PASS"}')
        original = self.master.run_pipeline
        outside = self.file('external.txt', 'not an artifact')
        def symlink_output(root, night, **kwargs):
            result = original(root, night, **kwargs)
            (root/'reports/unsafe.json').symlink_to(outside)
            return result
        with patch.object(self.master, 'run_pipeline', symlink_output):
            result = self.run_master()
        self.assertEqual(result['overall_status'], 'FAIL')
        self.assertEqual(json.loads(pointer.read_text())['overall_status'], 'FAIL')

    def test_provenance_and_model_specs_are_snapshotted_and_identity_bound(self):
        evidence = self.file('evidence/provenance.json', '{"source":"audited"}')
        spec = self.file('model_specs/candidate.json', '{"family":"registered"}')
        result = self.run_master()
        snapshot = self.root/'reports/pdca/2026-09-30/runs'/result['run_id']/'snapshot'
        self.assertTrue((snapshot/'evidence/provenance.json').is_file())
        self.assertEqual((snapshot/'model_specs/candidate.json').read_bytes(), spec.read_bytes())
        evidence.write_text('{"source":"changed"}')
        self.assertNotEqual(self.run_master()['run_id'], result['run_id'])

    def test_paths_cannot_escape_and_symlink_inputs_rejected(self):
        with self.assertRaises(ValueError):
            self.master.run_master(self.root, '../escape')
        (self.root/'data').symlink_to(ROOT/'data', target_is_directory=True)
        self.assertEqual(self.run_master()['overall_status'], 'FAIL')

    def test_cli_uses_master_and_reports_missing_implementations(self):
        p = subprocess.run([sys.executable, str(ROOT/'scripts/run_pdca.py'), '--root', str(self.root), '--night', '2026-09-30'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        r = json.loads(p.stdout)
        self.assertTrue(r['implementation_blockers'])
        self.assertEqual(len(r['stages']), 9)
