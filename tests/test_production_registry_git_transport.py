"""Exercise Task8 proposals against disposable local Git, without production authority."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

from tests.test_production_registry import checksum, core_fixture, core_inference

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import production_registry as registry
from master_contracts import canonical_bytes

GIT = shutil.which('git')
PROTECTED = {
    'data/raw/untouched-fixture.txt': b'synthetic raw fixture\n',
    'predictions/original/fixture/untouched.txt': b'synthetic ORIGINAL fixture\n',
}
ARCHIVE_REF = 'refs/heads/fixture-archive'
PROOF_REF = 'refs/heads/fixture-reviewed-evidence'
INTENT_PATH = 'protocols/intents/next.json'
GATE_PATH = 'fixtures/gate.json'


class LocalRegistry:
    """Test-only file transport. All repositories, objects and refs are disposable."""

    def __init__(self, workspace):
        self.workspace = Path(workspace).resolve(strict=True)
        if any((p / '.git').exists() for p in (self.workspace, *self.workspace.parents)):
            raise ValueError('The Git fixture must be outside every worktree')
        template = self.workspace / 'empty-template'
        template.mkdir()
        self.upstream = self.workspace / 'upstream.git'
        self.clients = [self.workspace / 'client-a.git', self.workspace / 'client-b.git']
        self.repositories = {self.upstream, *self.clients}
        self.env = {key: value for key, value in os.environ.items()
                    if not key.upper().startswith('GIT_')}
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_ALLOW_PROTOCOL='file', GIT_TERMINAL_PROMPT='0',
                        GIT_AUTHOR_NAME='Registry fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_NAME='Registry fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid',
                        GIT_AUTHOR_DATE='2000-01-01T00:00:00Z', GIT_COMMITTER_DATE='2000-01-01T00:00:00Z',
                        LC_ALL='C')
        self.options = ['-c', 'protocol.allow=never', '-c', 'protocol.file.allow=always',
                        '-c', 'core.hooksPath=' + template.as_posix()]
        self.run('init', '--bare', '--object-format=sha1', '--template=' + str(template),
                 str(self.upstream))
        declared, self.policy, intent, gate = core_fixture()
        self.ref = self.policy['state_ref']
        self.anchor_event = self.policy['anchor']['root_event_sha256']
        self.predecessor = self.commit(self.upstream, [], PROTECTED)
        initial = {row['path']: row['content_utf8'].encode('utf-8')
                   for row in declared['commits'][0]['files']}
        self.anchor = self.commit(self.upstream, [self.predecessor], initial)
        self.git(self.upstream, 'update-ref', self.ref, self.anchor)
        self.git(self.upstream, 'update-ref', ARCHIVE_REF, self.predecessor)
        self.policy['anchor']['commit_sha'] = self.anchor

        document = intent['document']
        document['policy_sha256'] = checksum(self.policy)
        gate.update(intent_sha256=checksum(document, True), policy_sha256=checksum(self.policy))
        evidence = {path: canonical_bytes(value) + b'\n'
                    for path, value in ((INTENT_PATH, document), (GATE_PATH, gate))}
        self.review_commit = self.commit(self.upstream, [self.predecessor], evidence)
        self.git(self.upstream, 'update-ref', PROOF_REF, self.review_commit)
        self.reviewed_ref = dict(commit_sha=self.review_commit, path=INTENT_PATH,
                                 sha256=hashlib.sha256(evidence[INTENT_PATH]).hexdigest())
        self.merged_ref = dict(intent['merged_ref'], commit_sha=self.review_commit,
            tree_sha=self.git(self.upstream, 'rev-parse', self.review_commit+'^{tree}').stdout.decode().strip())
        for client in self.clients:
            self.run('clone', '--bare', '--no-local', '--branch', self.ref.removeprefix('refs/heads/'),
                     self.upstream.as_uri(), str(client))

    def run(self, *arguments, stdin=None, env=None, check=True):
        return subprocess.run([GIT, *self.options, *arguments], cwd=self.workspace,
            env=self.env if env is None else env, input=stdin, capture_output=True,
            timeout=20, check=check)

    def git(self, repository, *arguments, **kwargs):
        if repository not in self.repositories:
            raise ValueError('Only disposable registry fixture repositories are allowed')
        return self.run('--git-dir', str(repository), *arguments, **kwargs)

    def commit(self, repository, parents, files):
        index_env = dict(self.env, GIT_INDEX_FILE=str(repository / 'fixture-index'))
        read_tree = [parents[0]] if parents else ['--empty']
        self.git(repository, 'read-tree', *read_tree, env=index_env)
        for path, raw in files.items():
            oid = self.git(repository, 'hash-object', '-w', '--stdin', stdin=raw).stdout.decode().strip()
            self.git(repository, 'update-index', '--add', '--cacheinfo', f'100644,{oid},{path}',
                     env=index_env)
        tree = self.git(repository, 'write-tree', env=index_env).stdout.decode().strip()
        parent_options = [arg for parent in parents for arg in ('-p', parent)]
        return self.git(repository, 'commit-tree', tree, *parent_options, '-m',
                        'Synthetic registry transport fixture').stdout.decode().strip()

    def blob(self, repository, revision, path):
        return self.git(repository, 'show', f'{revision}:{path}').stdout

    def proof(self, repository, reviewed_ref, merged_ref):
        revision = reviewed_ref['commit_sha']
        intent = json.loads(self.blob(repository, revision, reviewed_ref['path']))
        gate = json.loads(self.blob(repository, revision, GATE_PATH))
        return dict(intent=dict(document=intent, reviewed_ref=reviewed_ref, merged_ref=merged_ref),
                    gate_decision=gate)

    def snapshot(self, repository):
        """Read the real first-parent history, parent IDs and blobs after ref observation."""
        revisions = self.git(repository, 'rev-list', '--first-parent', '--reverse',
                             self.predecessor+'..'+self.ref).stdout.decode().splitlines()
        commits, proofs = [], {}
        for revision in revisions:
            parents = self.git(repository, 'rev-list', '--parents', '-n', '1',
                               revision).stdout.decode().split()[1:]
            entries = self.git(repository, 'ls-tree', '-r', '-z', revision, '--',
                               self.policy['registry_root']).stdout.split(b'\0')
            files = []
            for entry in entries[:-1]:
                header, raw_path = entry.split(b'\t', 1)
                mode, kind, oid = header.split()
                if (mode, kind) != (b'100644', b'blob'):
                    raise AssertionError('Unexpected registry fixture tree object')
                path = raw_path.decode('utf-8')
                raw = self.git(repository, 'cat-file', 'blob', oid.decode()).stdout
                files.append(dict(path=path, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                                  content_utf8=raw.decode('utf-8')))
                if path.startswith(self.policy['event_directory']+'/'):
                    event = json.loads(raw)
                    if event['event_sha256'] != self.anchor_event:
                        proofs[event['intent_sha256']] = self.proof(repository,
                            event['reviewed_ref'], event['merged_ref'])
            commits.append(dict(commit_sha=revision, parents=parents, files=files))
        return dict(schema_version='habu-registry-core-snapshot-v1', repository=self.policy['repository'],
                    state_ref=self.ref, history_complete=True, commits=commits,
                    transition_proofs=list(proofs.values()))

    def issue(self, snapshot):
        return registry.prepare_issuance_commit(snapshot, core_inference(snapshot), policy=self.policy,
            observed_at='2026-11-04T18:00:00+09:00', expected_ref_sha=self.anchor,
            expected_event_sha256=self.anchor_event)

    def activation(self, snapshot, repository):
        proof = self.proof(repository, self.reviewed_ref, self.merged_ref)
        return registry.prepare_activation_commit(snapshot, proof['intent'], proof['gate_decision'],
            policy=self.policy, observed_at='2026-11-04T10:00:00+09:00',
            expected_ref_sha=self.anchor, expected_previous_event_sha256=self.anchor_event)

    @staticmethod
    def proposed_files(proposal):
        spec = proposal['commit_spec']
        return {item['path']: item['content_utf8'].encode('utf-8')
                for item in spec['immutable_additions'] + spec['updates']}

    def candidates(self):
        issue, activate = self.clients
        proposals = [self.issue(self.snapshot(issue)), self.activation(self.snapshot(activate), activate)]
        if [p['status'] for p in proposals] != ['ISSUANCE_COMMIT_PROPOSED', 'ACTIVATION_COMMIT_PROPOSED']:
            raise AssertionError([p['reason_codes'] for p in proposals])
        commits = [self.commit(client, proposal['commit_spec']['parents'], self.proposed_files(proposal))
                   for client, proposal in zip(self.clients, proposals)]
        return proposals, commits

    def push(self, repository, revision):
        return self.git(repository, 'push', '--porcelain', '--no-verify', self.upstream.as_uri(),
                        revision + ':' + self.ref, check=False)


@unittest.skipUnless(GIT, 'Native Git is required for the local transport exercise')
class ProductionRegistryGitTransportTests(unittest.TestCase):
    def assert_unprivileged(self, result):
        for key in ('production_authorized', 'official_issuance_authorized', 'registry_activated'):
            self.assertIs(result[key], False)

    def assert_protected(self, fixture, tip):
        for path, raw in PROTECTED.items():
            self.assertEqual(fixture.blob(fixture.upstream, tip, path), raw)
            self.assertEqual(fixture.blob(fixture.upstream, ARCHIVE_REF, path), raw)
        refs = fixture.git(fixture.upstream, 'for-each-ref', '--format=%(refname)').stdout.decode().splitlines()
        self.assertEqual(set(refs), {fixture.ref, PROOF_REF, ARCHIVE_REF})
        self.assertEqual(fixture.git(fixture.upstream, 'rev-parse', ARCHIVE_REF).stdout.decode().strip(),
                         fixture.predecessor)

    def test_real_nonforce_siblings_reject_stale_activation_or_issuance(self):
        for winner in (0, 1):
            with self.subTest(winner=winner), tempfile.TemporaryDirectory() as directory:
                git = LocalRegistry(directory)
                proposals, commits = git.candidates()
                loser = 1 - winner
                first = git.push(git.clients[winner], commits[winner])
                second = git.push(git.clients[loser], commits[loser])
                self.assertEqual(first.returncode, 0)
                self.assertNotEqual(second.returncode, 0)
                self.assertRegex(second.stdout + second.stderr, b'fetch first|non-fast-forward')
                observed = git.snapshot(git.upstream)
                self.assertEqual(observed['commits'][-1]['commit_sha'], commits[winner])
                self.assertEqual(observed['commits'][-1]['parents'], [git.anchor])
                for index, status in ((winner, 'ACK_ONLY'), (loser, 'CONFLICT')):
                    result = registry.reconcile_publication(
                        dict(proposals[index]['pending'], commit_sha=commits[index]),
                        observed, policy=git.policy)
                    self.assertEqual(result['status'], status, result['reason_codes'])
                    self.assert_unprivileged(result)
                self.assertEqual(git.issue(observed)['status'], 'CONFLICT')
                self.assert_protected(git, commits[winner])

    def test_concurrent_local_updates_and_lost_ack_reconcile_without_resending(self):
        with tempfile.TemporaryDirectory() as directory:
            git = LocalRegistry(directory)
            proposals, commits = git.candidates()
            pending = [p['pending'] for p in proposals]  # The client has no commit acknowledgment.
            before = registry.reconcile_publication(pending[0], git.snapshot(git.upstream), policy=git.policy)
            self.assertEqual(before['status'], 'ACK_UNKNOWN')
            barrier = threading.Barrier(2)

            def race(index):
                barrier.wait(timeout=10)
                return git.push(git.clients[index], commits[index]).returncode

            with ThreadPoolExecutor(max_workers=2) as workers:
                codes = list(workers.map(race, (0, 1)))
            self.assertEqual(codes.count(0), 1)
            observed = git.snapshot(git.upstream)
            tip = observed['commits'][-1]['commit_sha']
            winner = commits.index(tip)
            self.assertEqual(codes[winner], 0)
            accepted = registry.reconcile_publication(pending[winner], observed, policy=git.policy)
            self.assertEqual(accepted['status'], 'ACK_ONLY')
            self.assertEqual(accepted['pending']['commit_sha'], tip)
            repeated = registry.reconcile_publication(accepted['pending'], git.snapshot(git.upstream),
                                                     policy=git.policy)
            self.assertEqual(repeated, accepted)
            conflict = registry.reconcile_publication(pending[1-winner], observed, policy=git.policy)
            self.assertEqual(conflict['status'], 'CONFLICT')
            for result in (before, accepted, repeated, conflict):
                self.assert_unprivileged(result)
            self.assert_protected(git, tip)

    def test_git_fast_forward_alone_cannot_ack_an_extra_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            git = LocalRegistry(directory)
            client = git.clients[0]
            issue = git.issue(git.snapshot(client))
            invalid = git.commit(client, [git.anchor, git.review_commit], git.proposed_files(issue))
            self.assertEqual(git.push(client, invalid).returncode, 0)
            observed = git.snapshot(git.upstream)
            self.assertEqual(observed['commits'][-1]['parents'], [git.anchor, git.review_commit])
            result = registry.reconcile_publication(issue['pending'], observed, policy=git.policy)
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['reason_codes'], ['DIRECT_PARENT_HISTORY_REQUIRED'])
            self.assert_unprivileged(result)
            self.assert_protected(git, invalid)

    def test_fixture_refuses_non_file_protocol_and_external_git_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            git = LocalRegistry(directory)
            refused = git.git(git.clients[0], 'ls-remote', 'https://127.0.0.1:1/fixture', check=False)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"transport 'https' not allowed", refused.stderr)
            with self.assertRaises(ValueError):
                git.git(ROOT, 'show-ref')
            self.assert_protected(git, git.anchor)


if __name__ == '__main__':
    unittest.main()
