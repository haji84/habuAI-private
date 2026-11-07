"""Explicit local command dispatch; synthetic private evidence, no publication."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import types
import tempfile
import unittest
from unittest.mock import patch

import test_private_individual_pdca_scoring as fixtures
from master_contracts import canonical_bytes


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'scripts/run_pdca.py'


class RunPdcaRuntimeTests(unittest.TestCase):
    def test_missing_posix_lock_reports_blocker_without_writing_output(self):
        # Exercise the real dispatcher and master import on all CI platforms.
        harness = '''import importlib.abc,runpy,sys
class BlockLock(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='fcntl':
   raise ModuleNotFoundError('blocked test dependency',name=fullname)
sys.meta_path.insert(0,BlockLock())
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', harness,
                                  str(COMMAND), '--root', str(root), '--night', '2026-11-07',
                                  '--output', str(root/'must-not-exist.json')],
                                 cwd=root, capture_output=True, timeout=30)
            self.assertEqual(run.returncode, 2, run.stderr.decode(errors='replace'))
            self.assertEqual(run.stderr, b'')
            report = json.loads(run.stdout)
            self.assertEqual(report['operational_night'], '2026-11-07')
            self.assertEqual(report['overall_status'], 'BLOCKED')
            self.assertEqual(report['execution_status'], 'RUNTIME_BLOCKED')
            self.assertEqual(report['blockers'], ['PDCA_POSIX_RUNTIME_UNAVAILABLE'])
            self.assertFalse(report['completed'])
            self.assertEqual(list(root.iterdir()), [])


class RunPdcaPrivateIndividualTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PrivateIndividualPdcaTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.raw = canonical_bytes(self.fixture.request) + b'\n'
        self.fixture.request_path.write_bytes(self.raw)
        self.args = ['--root', str(self.fixture.root), '--night', fixtures.NIGHT,
                     '--private-individual-request-path',
                     self.fixture.request_path.relative_to(self.fixture.root).as_posix(),
                     '--private-individual-request-sha256', hashlib.sha256(self.raw).hexdigest()]

    def inventory(self):
        return {p.relative_to(self.fixture.root).as_posix(): p.read_bytes()
                for p in self.fixture.root.rglob('*') if p.is_file()}

    def execute(self, args=None):
        before = self.inventory()
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(COMMAND),
                                 *(self.args if args is None else args)],
                                cwd=self.fixture.root, capture_output=True, timeout=30)
        self.assertEqual(self.inventory(), before)
        return result

    def test_actual_entry_returns_exact_existing_companion_aggregate_without_writes(self):
        expected = self.fixture.score(0)
        run = self.execute()
        self.assertEqual(run.returncode, 0, run.stderr.decode(errors='replace'))
        self.assertEqual(run.stderr, b'')
        actual = json.loads(run.stdout)
        self.assertEqual(actual, expected)
        self.assertEqual(actual['individual_recall'], .5)
        for flag in ('production_authorized', 'official_issuance_authorized',
                     'official_100m_10min_kpi_computed', 'strict_official_score_eligible'):
            self.assertIs(actual[flag], False)
        for private in (str(self.fixture.root), 'synthetic-owner', 'individual0', '3000050'):
            self.assertNotIn(private, run.stdout.decode())

    def test_missing_original_and_outcomes_keep_diagnostic_unknown(self):
        self.fixture.remove_ledger()
        run = self.execute()
        self.assertEqual(run.returncode, 2, run.stderr.decode(errors='replace'))
        result = json.loads(run.stdout)
        self.assertEqual(result['execution_status'], 'DATA_BLOCKED')
        self.assertIsNone(result['individual_recall'])
        (self.fixture.p0_dir / 'prediction.json').unlink()
        run = self.execute()
        self.assertEqual(run.returncode, 2, run.stderr.decode(errors='replace'))
        result = json.loads(run.stdout)
        self.assertIn('ORIGINAL_P0_REQUIRED', result['blockers'])
        self.assertIsNone(result['individual_recall'])

    def test_wrong_request_hash_fails_without_score(self):
        args = self.args.copy(); args[-1] = '0'*64
        run = self.execute(args)
        self.assertEqual(run.returncode, 1, run.stderr.decode(errors='replace'))
        self.assertEqual(run.stderr, b'')
        result = json.loads(run.stdout)
        self.assertEqual(result['execution_status'], 'FAIL')
        self.assertIsNone(result['individual_recall'])

    def test_incomplete_mode_and_writing_or_bridge_options_rejected(self):
        variants = [self.args[:-2], self.args[:4] + self.args[-2:],
                    self.args + ['--output', str(self.fixture.root/'must-not-exist.json')],
                    self.args + ['--bridge-context', str(self.fixture.root/'absent.json')],
                    self.args + ['--budget-seconds', '31'],
                    self.args + ['--budget-seconds', '0'],
                    self.args[:2] + self.args[4:]]
        for args in variants:
            with self.subTest(args=args[-2:]):
                run = self.execute(args)
                self.assertEqual(run.returncode, 2)
                self.assertIn(b'error:', run.stderr)
                self.assertEqual(run.stdout, b'')
                self.assertNotIn(b'Traceback', run.stderr)

    def test_help_is_available_without_posix_master_and_explains_boundary(self):
        run = self.execute(['--help'])
        self.assertEqual(run.returncode, 0, run.stderr.decode(errors='replace'))
        for text in (b'--private-individual-request-path', b'read-only', b'no publication'):
            self.assertIn(text, run.stdout)

    def test_private_mode_never_imports_master_in_fresh_process(self):
        harness = '''import importlib.abc,runpy,sys
class BlockMaster(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname in ('master_orchestrator','pdca_bridge'):
   raise AssertionError('PRIVATE_MODE_IMPORTED_MASTER_OR_BRIDGE')
sys.meta_path.insert(0,BlockMaster())
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        run = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', harness,
                              str(COMMAND), *self.args], capture_output=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr.decode(errors='replace'))
        self.assertEqual(json.loads(run.stdout)['execution_status'], 'DIAGNOSTIC_COMPUTED')

    def poisoned_scripts_environment(self):
        poison = self.fixture.root/'foreign-pythonpath'
        package = poison/'scripts'; package.mkdir(parents=True)
        (package/'__init__.py').write_text('', encoding='utf-8')
        (package/'score_private_pdca_individual_targets.py').write_text(
            "print('FOREIGN_SCORER_IMPORTED')\n"
            "def score_private_individual_targets(*args,**kwargs):\n"
            " return {'execution_status':'DIAGNOSTIC_COMPUTED','individual_recall':1}\n", encoding='utf-8')
        (package/'backfill_historical_environment.py').write_text(
            "from pathlib import Path\nprint('FOREIGN_PRIVATE_GUARD_IMPORTED')\n"
            "def assert_private_directory(root): return Path(root)\n", encoding='utf-8')
        return dict(os.environ, PYTHONPATH=str(poison))

    def test_foreign_scripts_package_cannot_replace_native_scorer(self):
        env = self.poisoned_scripts_environment()
        self.fixture.remove_ledger()
        before = self.inventory()
        run = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(COMMAND), *self.args],
                             cwd=self.fixture.root, env=env, capture_output=True, timeout=30)
        self.assertEqual(self.inventory(), before)
        self.assertNotIn(b'FOREIGN_', run.stdout + run.stderr)
        self.assertEqual(run.returncode, 2, run.stderr.decode(errors='replace'))
        report = json.loads(run.stdout)
        self.assertEqual(report['execution_status'], 'DATA_BLOCKED')
        self.assertIsNone(report['individual_recall'])

    def test_standalone_companion_cannot_import_foreign_private_guard(self):
        env = self.poisoned_scripts_environment()
        (self.fixture.root/'.git').mkdir()
        args = ['--root', str(self.fixture.root), '--night', fixtures.NIGHT,
                '--request-path', self.args[-3], '--request-sha256', self.args[-1]]
        before = self.inventory()
        run = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(fixtures.COMMAND), *args],
                             cwd=self.fixture.root, env=env, capture_output=True, timeout=30)
        self.assertEqual(self.inventory(), before)
        self.assertNotIn(b'FOREIGN_', run.stdout + run.stderr)
        self.assertEqual(run.returncode, 1, run.stderr.decode(errors='replace'))
        report = json.loads(run.stdout)
        self.assertEqual(report['execution_status'], 'FAIL')
        self.assertIsNone(report['individual_recall'])

    def test_legacy_default_budget_output_and_exit_status_are_preserved(self):
        for status, budget, expected_code in [('PASS', None, 0), ('BLOCKED', 0, 2), ('FAIL', 5, 2)]:
            calls = []; module = types.ModuleType('master_orchestrator')
            def run_master(*args, **kwargs):
                calls.append((args, kwargs)); return {'overall_status': status, 'legacy': True}
            module.run_master = run_master
            output = self.fixture.root/'legacy-output.json'
            argv = [str(COMMAND), '--root', str(self.fixture.root), '--night', fixtures.NIGHT,
                    '--output', str(output)]
            if budget is not None: argv += ['--budget-seconds', str(budget)]
            with patch.dict(sys.modules, {'master_orchestrator': module}), patch.object(sys, 'argv', argv):
                namespace = runpy.run_path(str(COMMAND), run_name='dispatch_test')
                captured = io.StringIO()
                with contextlib.redirect_stdout(captured): code = namespace['main']()
            self.assertEqual(code, expected_code)
            self.assertEqual(calls, [((self.fixture.root.resolve(), fixtures.NIGHT,
                                      300 if budget is None else budget), {})])
            self.assertEqual(output.read_text(encoding='utf-8'), captured.getvalue())

    def test_legacy_bridge_retains_fixed_budget_and_checkpoint_arguments(self):
        calls = []; checkpoints = []
        master = types.ModuleType('master_orchestrator')
        bridge = types.ModuleType('pdca_bridge')
        callback = lambda *args: None
        def run_master(*args, **kwargs):
            calls.append((args, kwargs)); return {'overall_status': 'PASS'}
        def publisher(path):
            checkpoints.append(path)
            return callback, {'attempt': {'base_elapsed': 17, 'deadline': 'synthetic-aware-deadline'}}
        master.run_master = run_master
        bridge.checkpoint_publisher = publisher
        bridge.SCIENTIFIC_BUDGET = 300
        path = self.fixture.root/'legacy-bridge.json'
        argv = [str(COMMAND), '--root', str(self.fixture.root), '--night', fixtures.NIGHT,
                '--bridge-context', str(path)]
        with patch.dict(sys.modules, {'master_orchestrator': master, 'pdca_bridge': bridge}):
            namespace = runpy.run_path(str(COMMAND), run_name='dispatch_test')
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(namespace['main'](), 0)
            self.assertEqual(checkpoints, [path])
            self.assertEqual(calls, [((self.fixture.root.resolve(), fixtures.NIGHT, 300),
                {'checkpoint_callback': callback, 'budget_floor': 17,
                 'attempt_deadline': 'synthetic-aware-deadline'})])
            with patch.object(sys, 'argv', argv+['--budget-seconds','29']):
                with self.assertRaisesRegex(ValueError, 'fixed at 300'):
                    namespace['main']()
            self.assertEqual(len(checkpoints), 1)
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
