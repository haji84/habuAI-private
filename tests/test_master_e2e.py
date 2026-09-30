import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('pdca_bridge'), 'shared durable bridge is missing')
        import pdca_bridge
        self.bridge = pdca_bridge
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def repository(self):
        root = self.base/'repo'
        root.mkdir()
        for name in ('src', 'scripts'):
            shutil.copytree(ROOT/name, root/name, ignore=shutil.ignore_patterns('__pycache__'))
        (root/'data/raw').mkdir(parents=True)
        (root/'data/raw/exact.bin').write_bytes(b'protected\x00raw')
        remote = self.base/'remote.git'
        for command in (["git", "init", "--bare", str(remote)], ["git", "init", "-b", "main", str(root)]):
            subprocess.run(command, check=True, capture_output=True)
        self.git(root, 'add', '.')
        self.git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'source')
        self.git(root, 'remote', 'add', 'origin', str(remote))
        self.git(root, 'push', 'origin', 'main')
        commit = self.git(root, 'rev-parse', 'HEAD').strip()
        return root, self.bridge.GitTransport(root), commit

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL, text=True)

    def issue(self, number=1):
        return {'number': number, 'state': 'open', 'title': '[HABU PDCA] 2026-09-28', 'body': 'Run audited PDCA', 'user': {'login': 'owner'}}

    def test_authoritative_owner_and_calendar_validation(self):
        command = self.bridge.authorize_command('owner/repo', self.issue())
        self.assertEqual(command['night'], '2026-09-28')
        for title in ('[HABU PDCA] 2026-02-30', '[HABU PDCA] 2026-09-28 2026-09-29', 'prefix [HABU PDCA] 2026-09-28'):
            with self.subTest(title=title), self.assertRaises(ValueError):
                self.bridge.authorize_command('owner/repo', dict(self.issue(), title=title))
        bad = self.issue(); bad['user']['login'] = 'outsider'
        with self.assertRaises(ValueError):
            self.bridge.authorize_command('owner/repo', bad)

    def test_identity_ignores_kernel_and_incidental_packages(self):
        from master_orchestrator import inspect_run_identity
        root = self.base/'input'; root.mkdir()
        before = inspect_run_identity(root, '2026-09-28')
        with patch('platform.platform', return_value='another kernel'):
            after = inspect_run_identity(root, '2026-09-28')
        self.assertEqual(before['run_id'], after['run_id'])

    def test_transport_cas_and_explicit_paths_leave_worktree_untouched(self):
        root, transport, source = self.repository()
        path = 'reports/pdca/2026-09-28/bridge/receipt.json'
        first = transport.publish('pdca/test', source, None, {path: b'{"state":"RUNNING"}'})
        self.assertEqual(transport.read(first, path), b'{"state":"RUNNING"}')
        with self.assertRaises(self.bridge.TransportError):
            transport.publish('pdca/test', source, None, {path: b'{}'})
        with self.assertRaises(ValueError):
            transport.publish('pdca/test', source, first, {'src/untrusted.py': b'bad'})
        self.assertEqual(self.git(root, 'status', '--porcelain'), '')

    def test_compact_bundle_restores_fresh_workdir_and_valid_exit_two(self):
        root, transport, source = self.repository()
        result = self.bridge.run_local(root, '2026-09-28', self.base/'attempt.json', timeout_seconds=60)
        self.assertEqual(result['result']['overall_status'], 'BLOCKED')
        run_id = result['result']['run_id']
        bundle = self.bridge.build_bundle(root, '2026-09-28', run_id, source, transport)
        self.assertFalse(any(p.endswith('/snapshot/data/raw/exact.bin') for p in bundle['files']))
        commit = transport.publish('pdca/run-'+run_id, source, None, bundle['files'])
        fresh = self.base/'fresh'
        self.bridge.restore_bundle(transport, commit, bundle['manifest_path'], fresh, source)
        resumed = self.bridge.run_local(fresh, '2026-09-28', self.base/'retry.json', timeout_seconds=60)
        self.assertEqual(resumed['result'], result['result'])
        self.assertEqual((fresh/'data/raw/exact.bin').read_bytes(), b'protected\x00raw')

    def test_crash_cannot_reuse_stale_pass(self):
        root, _, _ = self.repository()
        stale = root/'reports/pdca/2026-09-28/pdca_result.json'
        stale.parent.mkdir(parents=True)
        stale.write_text('{"overall_status":"PASS"}')
        script = root/'scripts/run_pdca.py'
        script.write_text('raise SystemExit(9)\n')
        result = self.bridge.run_local(root, '2026-09-28', self.base/'attempt.json', timeout_seconds=60)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('execution', result['reason'].lower())
        self.assertNotIn('result', result)

    def test_bundle_tamper_traversal_and_size_caps_fail_closed(self):
        root, transport, source = self.repository()
        result = self.bridge.run_local(root, '2026-09-28', self.base/'attempt.json', timeout_seconds=60)
        run_id = result['result']['run_id']
        with patch.object(self.bridge, 'MAX_BUNDLE_BYTES', 10):
            with self.assertRaises(self.bridge.RecoveryBlocked):
                self.bridge.build_bundle(root, '2026-09-28', run_id, source, transport)
        bundle = self.bridge.build_bundle(root, '2026-09-28', run_id, source, transport)
        manifest = json.loads(bundle['files'][bundle['manifest_path']])
        manifest['files'][0]['path'] = '../../escape'
        bundle['files'][bundle['manifest_path']] = json.dumps(manifest).encode()
        commit = transport.publish('pdca/bad', source, None, bundle['files'])
        with self.assertRaises((ValueError, self.bridge.RecoveryBlocked)):
            self.bridge.restore_bundle(transport, commit, bundle['manifest_path'], self.base/'bad', source)

    def test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore(self):
        root, transport, source = self.repository()
        script = """import os,sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/src')
from master_orchestrator import run_master
from pdca_bridge import GitTransport,build_bundle
root=Path(sys.argv[1]); transport=GitTransport(root); source=sys.argv[2]
def publish(directory, checkpoint):
    bundle=build_bundle(root,'2026-09-28',checkpoint['run_id'],source,transport)
    branch='pdca/run-'+checkpoint['run_id']
    transport.publish(branch,source,transport.head(branch),bundle['files'])
    if 'stages/operational_scoring.json' in checkpoint['outputs']:
        os._exit(77)
run_master(root,'2026-09-28',checkpoint_callback=publish,attempt_deadline='2099-01-01T00:00:00+00:00')
"""
        process = subprocess.run([sys.executable, '-c', script, str(root), source], capture_output=True)
        self.assertEqual(process.returncode, 77, process.stderr.decode())
        directory = next((root/'reports/pdca/2026-09-28/runs').iterdir())
        run_id = directory.name
        remote = transport.head('pdca/run-'+run_id)
        fresh = self.base/'recovered'
        manifest = f'reports/pdca/2026-09-28/bridge/recovery-{run_id}.json'
        self.bridge.restore_bundle(transport, remote, manifest, fresh, source)
        before = json.loads((fresh/f'reports/pdca/2026-09-28/runs/{run_id}/checkpoint.json').read_text())
        result = self.bridge.run_local(fresh, '2026-09-28', self.base/'after-crash.json', timeout_seconds=60)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertGreaterEqual(result['result']['budget']['elapsed_seconds'], before['elapsed_seconds'])

    def test_recovery_never_imports_supplemental_source_code(self):
        root, transport, source = self.repository()
        (root/'src/injected.py').write_text('raise RuntimeError("untrusted")')
        output = self.base/'direct.json'
        subprocess.run([sys.executable, str(root/'scripts/run_pdca.py'), '--root', str(root), '--night', '2026-09-28', '--output', str(output)], capture_output=True)
        result = json.loads(output.read_text())
        with self.assertRaises(self.bridge.RecoveryBlocked):
            self.bridge.build_bundle(root, '2026-09-28', result['run_id'], source, transport)

    def test_fixed_bridge_budget_cannot_be_reset_by_new_attempt(self):
        from master_orchestrator import run_master
        root = self.base/'input'; root.mkdir()
        result = run_master(root, '2026-09-28', budget_floor=300)
        self.assertEqual(result['overall_status'], 'BLOCKED')
        self.assertIn('BUDGET_EXHAUSTED', str(result))
        self.assertGreaterEqual(result['budget']['elapsed_seconds'], 300)

    def api(self, source):
        class FakeGitHub:
            default_branch = 'main'
            def __init__(self):
                self.source = source
                self.issues = {1: self_outer.issue(), 2: self_outer.issue(2)}
                self.prs = {}
                self.comments = {}
                self.handled = set()
                self.fail_comment = False
            def default_source(self):
                return self.source
            def issue(self, number):
                return self.issues[number]
            def ensure_pr(self, branch, night):
                self.prs.setdefault(branch, 'https://example.invalid/pr/'+str(len(self.prs)+1))
                return self.prs[branch]
            def upsert_comment(self, number, command_id, text):
                if self.fail_comment:
                    self.fail_comment = False
                    raise RuntimeError('injected comment failure')
                self.comments[(number, command_id)] = text
            def mark_handled(self, number):
                self.handled.add(number)
        self_outer = self
        return FakeGitHub()

    def test_two_commands_converge_and_partial_publication_recovers(self):
        root, transport, source = self.repository()
        api = self.api(source)
        api.fail_comment = True
        with self.assertRaises(RuntimeError):
            self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'attempt-1')
        first = self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'attempt-2')
        duplicate = self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'attempt-3')
        second_issue = self.bridge.execute_command(root, 'owner/repo', 2, api, transport, 'attempt-4')
        self.assertEqual(first['run_id'], second_issue['run_id'])
        self.assertEqual(first['result_sha256'], duplicate['result_sha256'])
        self.assertEqual(len(api.prs), 1)
        self.assertEqual(len(api.comments), 2)
        self.assertEqual(api.handled, {1, 2})
        self.assertEqual(first['scientific_status'], 'BLOCKED')
        self.assertEqual(first['state'], 'HANDLED')

    def test_stale_processing_label_does_not_hide_unfinished_command(self):
        command = self.issue()
        command['labels'] = [{'name': 'pdca-processing'}]
        pending = self.bridge.discover_commands('owner/repo', [command], lambda c: None)
        self.assertEqual(pending, [1])
        handled = self.bridge.discover_commands('owner/repo', [command], lambda c: {'state':'HANDLED', 'command':c})
        self.assertEqual(handled, [1])  # An unverified terminal claim is not authority.

    def test_workflows_share_executor_without_permission_changes(self):
        event = (ROOT/'.github/workflows/pdca-command.yml').read_text()
        poller = (ROOT/'.github/workflows/pdca-command-poller.yml').read_text()
        self.assertIn('workflow_call:', event)
        self.assertIn('group: habu-pdca-executor', event)
        self.assertIn('uses: ./.github/workflows/pdca-command.yml', poller)
        for workflow in (event, poller):
            permissions = workflow.split('permissions:\n', 1)[1].split('\n\n', 1)[0]
            self.assertEqual(set(line.strip() for line in permissions.splitlines()),
                             {'contents: write', 'issues: write', 'pull-requests: write'})
            self.assertNotIn('git add', workflow)

    def test_scientific_dependency_change_creates_new_run_identity(self):
        import importlib.metadata
        from master_orchestrator import inspect_run_identity
        root = self.base/'input'; root.mkdir()
        before = inspect_run_identity(root, '2026-09-28')
        original = importlib.metadata.version
        with patch('importlib.metadata.version', side_effect=lambda name: '999.0' if name == 'numpy' else original(name)):
            after = inspect_run_identity(root, '2026-09-28')
        self.assertNotEqual(before['run_id'], after['run_id'])

    def test_transport_enforces_caps_for_receipts_too(self):
        root, transport, source = self.repository()
        with patch.object(self.bridge, 'MAX_FILE_BYTES', 2):
            with self.assertRaises(self.bridge.RecoveryBlocked):
                transport.publish('pdca/oversized', source, None,
                                  {'reports/pdca/2026-09-28/bridge/receipt.json': b'123'})

    def test_publication_time_cannot_extend_reserved_deadline(self):
        from datetime import datetime, timezone, timedelta
        root, transport, source = self.repository()
        api = self.api(source)
        start = datetime(2026, 9, 30, tzinfo=timezone.utc)
        calls = []
        def clock():
            calls.append(None)
            return start if len(calls) <= 3 else start + timedelta(seconds=30)
        with patch.object(self.bridge, '_now', side_effect=clock), patch.object(
                self.bridge, 'run_local', return_value={'status':'FAIL', 'reason':'injected stop'}) as worker:
            self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'attempt-1')
        self.assertLessEqual(worker.call_args.kwargs['timeout_seconds'], 210)

    def test_changed_source_new_issue_changes_run_but_old_receipt_stays_pinned(self):
        root, transport, source = self.repository()
        api = self.api(source)
        old = self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'first')
        (root/'data/raw/new.bin').write_bytes(b'new evidence')
        self.git(root, 'add', 'data/raw/new.bin')
        self.git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'new source')
        self.git(root, 'push', 'origin', 'main')
        api.source = self.git(root, 'rev-parse', 'HEAD').strip()
        repeated = self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'repeat')
        new = self.bridge.execute_command(root, 'owner/repo', 2, api, transport, 'new')
        self.assertEqual(repeated['run_id'], old['run_id'])
        self.assertEqual(repeated['source_commit'], source)
        self.assertNotEqual(new['run_id'], old['run_id'])

    def test_expired_lost_attempt_reservation_is_shared_across_issue_ids(self):
        from datetime import datetime, timezone, timedelta
        root, transport, source = self.repository()
        api = self.api(source)
        with patch.object(self.bridge, 'run_local', return_value={'status':'FAIL', 'reason':'injected stop'}):
            first = self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'lost')
        run_id = first['run_id']
        path = f'reports/pdca/2026-09-28/bridge/run-{run_id}.json'
        branch = 'pdca/run-'+run_id
        head = transport.head(branch)
        record = json.loads(transport.read(head, path))
        record.update(state='RUNNING', ledger_elapsed=260,
                      lease_expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        record['attempt'].update(base_elapsed=260, limit_seconds=40)
        transport.publish(branch, source, head, {path: json.dumps(record).encode()})
        with patch.object(self.bridge, 'run_local') as worker:
            second = self.bridge.execute_command(root, 'owner/repo', 2, api, transport, 'retry')
        worker.assert_not_called()
        self.assertEqual(second['run_id'], run_id)
        self.assertIn('BUDGET_EXHAUSTED', second['reason'])
        self.assertEqual(second['ledger_elapsed'], 300)

    def test_bundle_hash_and_checkpoint_hash_corruption_are_rejected(self):
        root, transport, source = self.repository()
        result = self.bridge.run_local(root, '2026-09-28', self.base/'attempt.json', timeout_seconds=60)
        run_id = result['result']['run_id']
        bundle = self.bridge.build_bundle(root, '2026-09-28', run_id, source, transport)
        target = next(path for path in bundle['files'] if path.endswith('/checkpoint.json'))
        bundle['files'][target] += b' '
        commit = transport.publish('pdca/corrupt', source, None, bundle['files'])
        with self.assertRaisesRegex(ValueError, 'hash/size'):
            self.bridge.restore_bundle(transport, commit, bundle['manifest_path'], self.base/'corrupt', source)
        directory = root/f'reports/pdca/2026-09-28/runs/{run_id}'
        (directory/'checkpoint.json').write_text('{}')
        with self.assertRaises((ValueError, KeyError)):
            self.bridge.verify_checkpoint(directory, run_id)

    def test_restore_requires_complete_inventory_and_result_binding(self):
        root, transport, source = self.repository()
        result = self.bridge.run_local(root, '2026-09-28', self.base/'attempt.json', timeout_seconds=60)
        run_id = result['result']['run_id']
        bundle = self.bridge.build_bundle(root, '2026-09-28', run_id, source, transport)
        manifest = json.loads(bundle['files'][bundle['manifest_path']])
        manifest['sources'] = []
        bundle['files'][bundle['manifest_path']] = json.dumps(manifest).encode()
        commit = transport.publish('pdca/omitted', source, None, bundle['files'])
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.bridge.restore_bundle(transport, commit, bundle['manifest_path'], self.base/'omitted', source)

    def test_sandbox_lifecycle_and_full_master_keep_production_blocked(self):
        from datetime import datetime
        import champion_registry as registry
        from test_champion_registry import evidence_fixture
        from test_prediction_lineage import forecast_fixture
        from issue_prediction import issue_prediction
        from master_orchestrator import run_master
        with registry.sandbox_registry() as ctx:
            issued = []
            previous = None
            model_ids = []
            for probability in (.2, .8):
                model, evidence = evidence_fixture(ctx.root, probability)
                model_ids.append(model['model_id'])
                with patch.object(registry, '_now', return_value='2026-09-30T18:00:00+09:00'):
                    event = registry.promote(ctx, model['model_id'], evidence, previous)
                previous = event['event_sha256']
                source, sha = forecast_fixture(ctx.root)
                prediction = issue_prediction(ctx, source, sha, '2026-09-30',
                    clock=lambda: datetime.fromisoformat('2026-09-30T20:00:00+09:00'))
                issued.append((prediction, prediction.read_bytes()))
                self.assertEqual(json.loads(prediction.read_text())['grid_predictions'][0]['probability'], probability)
            registry.rollback(ctx, model_ids[0], 'sandbox verification', previous)
            self.assertEqual(issued[0][0].read_bytes(), issued[0][1])
            self.assertIsNone(registry.champion_at(ctx.root, '2099-01-01T00:00:00Z'))
            master = run_master(ctx.root, '2026-09-30')
            self.assertEqual(len(master['stages']), 9)
            self.assertFalse(master['completed'])
            self.assertEqual(master['overall_status'], 'BLOCKED')
            self.assertFalse((ctx.root/'predictions/original').exists())

    def test_discovery_retries_do_not_starve_later_commands(self):
        first, second = self.issue(1), self.issue(2)
        def receipt(command):
            if command['issue'] == 1:
                return {'command': command, 'state': 'RETRYABLE',
                        'last_attempt_at': '2026-09-30T12:00:00+00:00'}
        self.assertEqual(self.bridge.discover_commands('owner/repo', [first, second], receipt), [2, 1])

    def test_checkpoint_publication_limit_retains_specific_blocker(self):
        root, _, _ = self.repository()
        context = self.base/'context.json'
        context.write_text('{}')
        context.with_suffix('.error.json').write_text(json.dumps({
            'status': 'BLOCKED', 'reason': 'RECOVERY_BUNDLE_LIMIT: 20MiB maximum'}))
        with patch.object(self.bridge.subprocess, 'run', return_value=subprocess.CompletedProcess([], 75)):
            outcome = self.bridge.run_local(root, '2026-09-28', self.base/'attempt.json', context_path=context)
        self.assertEqual(outcome['status'], 'FAIL')
        self.assertEqual(outcome.get('recovery_status'), 'BLOCKED')
        self.assertIn('RECOVERY_BUNDLE_LIMIT', outcome['reason'])

    def test_handled_receipt_cannot_override_verified_scientific_result(self):
        root, transport, source = self.repository()
        api = self.api(source)
        receipt = self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'first')
        self.assertEqual(receipt['scientific_status'], 'BLOCKED')
        command = receipt['command']; branch = 'pdca/command-'+command['command_id']
        path = f'reports/pdca/2026-09-28/bridge/command-{command["command_id"]}.json'
        receipt.update(scientific_status='PASS', completed=True, result_sha256='0'*64)
        transport.publish(branch, source, transport.head(branch), {path: json.dumps(receipt).encode()})
        with self.assertRaisesRegex(ValueError, 'HANDLED|receipt'):
            self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'duplicate')

    def test_skeletal_handled_receipt_does_not_hide_command(self):
        diagnostics = []
        pending = self.bridge.discover_commands('owner/repo', [self.issue()],
            lambda c: {'state':'HANDLED', 'command':c}, diagnostics=diagnostics)
        self.assertEqual(pending, [1])
        self.assertIn('HANDLED', diagnostics[0]['reason'])

    def test_corrupt_receipt_is_audited_without_starving_later_command(self):
        diagnostics = []
        def lookup(command):
            if command['issue'] == 1:
                raise ValueError('invalid JSON receipt')
        pending = self.bridge.discover_commands('owner/repo', [self.issue(1), self.issue(2)],
                                               lookup, diagnostics=diagnostics)
        self.assertEqual(pending, [2, 1])
        self.assertEqual(diagnostics[0]['issue'], 1)
        self.assertIn('invalid JSON receipt', diagnostics[0]['reason'])
        self.assertEqual(diagnostics[0]['status'], 'FAIL')

    def test_publication_refuses_mixed_report_tree_without_discarding_it(self):
        root, transport, source = self.repository()
        path = 'reports/pdca/2026-09-28/bridge/receipt.json'
        first = transport.publish('pdca/probe', source, None, {path:b'{}'})
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(td)/'index'),
                       GIT_AUTHOR_NAME='Test', GIT_COMMITTER_NAME='Test',
                       GIT_AUTHOR_EMAIL='test@example.invalid', GIT_COMMITTER_EMAIL='test@example.invalid')
            transport.git('read-tree', first, env=env)
            blob = transport.git('hash-object', '-w', '--stdin', data=b'raise RuntimeError("injected")').decode().strip()
            transport.git('update-index', '--add', '--cacheinfo', '100644', blob, 'src/injected.py', env=env)
            tree = transport.git('write-tree', env=env).decode().strip()
            mixed = transport.git('commit-tree', tree, '-p', first, data=b'external change\n', env=env).decode().strip()
        transport.git('push', '--quiet', 'origin', mixed+':refs/heads/pdca/probe')
        with self.assertRaisesRegex(ValueError, 'report|source'):
            transport.publish('pdca/probe', source, mixed, {path:b'{"state":"RUNNING"}'})
        self.assertEqual(transport.head('pdca/probe'), mixed)
        self.assertIn(b'injected', transport.read(mixed, 'src/injected.py'))

    def test_discovery_only_suppresses_verified_durable_handled_receipt(self):
        root, transport, source = self.repository()
        api = self.api(source)
        receipt = self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'first')
        validate = lambda command, value: self.bridge.verify_handled_receipt(transport, command, value, source)
        pending = self.bridge.discover_commands('owner/repo', [self.issue()], lambda c: receipt,
                                               receipt_validator=validate)
        self.assertEqual(pending, [])
        receipt['completed'] = True
        diagnostics = []
        pending = self.bridge.discover_commands('owner/repo', [self.issue(), self.issue(2)],
            lambda c: receipt if c['issue'] == 1 else None, receipt_validator=validate, diagnostics=diagnostics)
        self.assertEqual(pending, [2, 1])
        self.assertIn('authoritative', diagnostics[0]['reason'])

    def test_report_blob_size_is_checked_before_materialization(self):
        root, transport, source = self.repository()
        path = 'reports/pdca/2026-09-28/bridge/receipt.json'
        head = transport.publish('pdca/size', source, None, {path:b'12345'})
        with patch.object(self.bridge, 'MAX_FILE_BYTES', 2), patch.object(transport, 'git', wraps=transport.git) as git:
            with self.assertRaises(self.bridge.RecoveryBlocked):
                transport.read(head, path)
            self.assertFalse(any(call.args[0] == 'show' for call in git.call_args_list))
            self.assertEqual(transport.read(source, 'data/raw/exact.bin'), b'protected\x00raw')

    def test_unconsumed_source_change_can_share_run_without_mixed_report_tree(self):
        root, transport, source = self.repository()
        api = self.api(source)
        first = self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'first')
        (root/'README.md').write_text('Unconsumed documentation change')
        self.git(root, 'add', 'README.md')
        self.git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'readme')
        self.git(root, 'push', 'origin', 'main')
        api.source = self.git(root, 'rev-parse', 'HEAD').strip()
        second = self.bridge.execute_command(root, 'owner/repo', 2, api, transport, 'second')
        self.assertEqual(first['run_id'], second['run_id'])
        self.assertEqual(second['source_commit'], source)
        self.assertEqual(second['command_source_commit'], api.source)
        self.assertEqual(self.bridge.execute_command(root, 'owner/repo', 2, api, transport, 'repeat'), second)

    def test_nonobject_and_missing_receipts_leave_healthy_command_discoverable(self):
        for invalid in ([], None, 42):
            with self.subTest(invalid=invalid):
                diagnostics = []
                def lookup(command):
                    if command['issue'] == 2:
                        return None
                    if invalid is None:
                        raise self.bridge.TransportError('missing committed receipt artifact')
                    return invalid
                pending = self.bridge.discover_commands('owner/repo', [self.issue(), self.issue(2)],
                                                       lookup, diagnostics=diagnostics)
                self.assertEqual(pending, [2, 1])
                self.assertEqual(diagnostics[0]['issue'], 1)
                self.assertEqual(diagnostics[0]['status'], 'FAIL')

    def test_new_issue_cannot_advertise_mixed_completed_shared_run(self):
        root, transport, source = self.repository()
        api = self.api(source)
        first = self.bridge.execute_command(root, 'owner/repo', 1, api, transport, 'first')
        branch = first['run_branch']; head = transport.head(branch)
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(td)/'index'),
                       GIT_AUTHOR_NAME='Test', GIT_COMMITTER_NAME='Test',
                       GIT_AUTHOR_EMAIL='test@example.invalid', GIT_COMMITTER_EMAIL='test@example.invalid')
            transport.git('read-tree', head, env=env)
            blob = transport.git('hash-object', '-w', '--stdin', data=b'raise RuntimeError("injected")').decode().strip()
            transport.git('update-index', '--add', '--cacheinfo', '100644', blob, 'src/injected.py', env=env)
            tree = transport.git('write-tree', env=env).decode().strip()
            mixed = transport.git('commit-tree', tree, '-p', head, data=b'external source change\n', env=env).decode().strip()
        transport.git('push', '--quiet', 'origin', mixed+':refs/heads/'+branch)
        with patch.object(api, 'ensure_pr', wraps=api.ensure_pr) as publish:
            with self.assertRaisesRegex(ValueError, 'Mixed report branch'):
                self.bridge.execute_command(root, 'owner/repo', 2, api, transport, 'second')
        publish.assert_not_called()
        self.assertEqual(api.handled, {1})
        self.assertEqual(len(api.comments), 1)
        self.assertEqual(transport.head(branch), mixed)
