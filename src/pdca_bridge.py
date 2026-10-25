"""Fixed owner-command executor and bounded repository-backed recovery transport.

Restored report branches are data, never executable code. Only explicit report
paths are published; source snapshots are reconstructed from a trusted commit.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from master_contracts import (STAGE_NAMES, atomic_json, canonical_bytes, digest,
                              file_hash, overall_status, safe_path, validate_night, validate_stage)

MAX_FILES = 2000
MAX_BUNDLE_BYTES = 20 * 1024 * 1024
MAX_FILE_BYTES = 5 * 1024 * 1024
SCIENTIFIC_BUDGET = 300
ATTEMPT_TIMEOUT = 240
LEASE_SECONDS = 600


def inspect_run_identity(*args, **kwargs):
    """Load the actual scientific engine only when a scientific operation runs."""
    from master_orchestrator import inspect_run_identity as inspect_identity
    return inspect_identity(*args, **kwargs)


class TransportError(RuntimeError):
    pass


class RecoveryBlocked(ValueError):
    pass


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{40}', value):
        raise ValueError('Invalid pinned source commit')
    return value


def _run_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ValueError('Invalid scientific run ID')
    return value


def _now():
    return datetime.now(timezone.utc)


def authorize_command(repository, issue):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository')
    title, body = issue.get('title', ''), issue.get('body') or ''
    if (issue.get('user', {}).get('login', '').lower() != repository.split('/')[0].lower()
            or issue.get('state') != 'open' or not title.startswith('[HABU PDCA]')):
        raise ValueError('Command must be an open owner issue with exact [HABU PDCA] prefix')
    dates = re.findall(r'(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)', title)
    if len(dates) != 1:
        raise ValueError('Command needs exactly one operational date')
    validate_night(dates[0])
    number = issue['number']
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise ValueError('Invalid issue number')
    command = {'repository': repository, 'issue': number, 'night': dates[0],
               'text_sha256': digest({'title': title.strip(), 'body': body.strip()})}
    return dict(command, command_id=digest(command))


class GitTransport:
    """CAS report commits using an isolated index; works with origin or local bare tests."""
    def __init__(self, root, remote='origin'):
        self.root, self.remote = Path(root), remote

    def git(self, *args, data=None, env=None, check=True):
        process = subprocess.run(['git', '-C', str(self.root), *args], input=data,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        if check and process.returncode:
            raise TransportError(f'git {args[0]} failed: {process.stderr.decode(errors="replace")[:500]}')
        return process.stdout if check else process

    def head(self, branch):
        self._branch(branch)
        output = self.git('ls-remote', '--heads', self.remote, 'refs/heads/'+branch).decode().strip()
        if not output:
            return None
        commit = _sha(output.split()[0])
        self.git('fetch', '--quiet', '--no-tags', self.remote, 'refs/heads/'+branch)
        return commit

    def _branch(self, branch):
        if not re.fullmatch(r'pdca/[A-Za-z0-9_-]+', branch):
            raise ValueError('Only deterministic PDCA report branches are supported')

    def read(self, commit, path):
        _sha(commit)
        safe_path(Path('/validate'), path)
        mode = self.git('ls-tree', commit, '--', path).decode().split()
        if not mode or mode[0] not in ('100644', '100755') or mode[1] != 'blob':
            raise TransportError(f'Missing/nonregular committed artifact: {path}')
        # Report/control blobs are untrusted bounded data. Trusted source
        # reconstruction deliberately has a separate larger-input contract.
        if path.startswith('reports/pdca/'):
            size = int(self.git('cat-file', '-s', mode[2]))
            if size > MAX_FILE_BYTES:
                raise RecoveryBlocked('RECOVERY_BUNDLE_LIMIT: report blob exceeds 5MiB before materialization')
        # The already-resolved immutable blob avoids native Windows pathname
        # disambiguation/length limits on a long "commit:path" revision.
        return self.git('cat-file', 'blob', mode[2])

    def source_workspace(self, commit, target):
        _sha(commit)
        target = Path(target)
        if target.exists() and any(target.iterdir()):
            raise ValueError('Source workspace must be empty')
        target.mkdir(parents=True, exist_ok=True)
        for record in self.git('ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
            if not record:
                continue
            header, raw_path = record.split(b'\t', 1)
            mode, kind, blob = header.decode().split()
            relative = raw_path.decode('utf-8')
            if mode not in ('100644', '100755') or kind != 'blob':
                raise ValueError('Source symlinks/submodules are not executable recovery inputs')
            path = safe_path(target, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.git('cat-file', 'blob', blob))
        return target

    def assert_report_tree(self, commit, source_commit):
        """Refuse mixed report/source branches; never silently rebuild or discard them."""
        _sha(commit); _sha(source_commit)
        if self.git('merge-base', '--is-ancestor', source_commit, commit, check=False).returncode:
            raise ValueError('Report branch does not descend from pinned source')
        for raw_path in self.git('diff', '--name-only', '--no-renames', '-z', source_commit, commit, '--').split(b'\0'):
            if not raw_path:
                continue
            path = raw_path.decode('utf-8')
            safe_path(Path('/validate'), path)
            if not re.fullmatch(r'reports/pdca/\d{4}-\d{2}-\d{2}/(?:bridge|runs)/.+', path):
                raise ValueError('Mixed report branch changes pinned source: '+path)
            mode = self.git('ls-tree', commit, '--', path).decode().split()
            if not mode or mode[0] not in ('100644', '100755') or mode[1] != 'blob':
                raise ValueError('Report branch contains deleted or nonregular artifact: '+path)

    def publish(self, branch, source_commit, expected_previous, files):
        self._branch(branch)
        _sha(source_commit)
        if self.head(branch) != expected_previous:
            raise TransportError('Remote branch compare-and-swap conflict')
        if not files:
            raise ValueError('Publication cannot be empty')
        _limits(files)
        for path in files:
            safe_path(Path('/validate'), path)
            if not re.fullmatch(r'reports/pdca/\d{4}-\d{2}-\d{2}/(?:bridge|runs)/.+', path):
                raise ValueError('Publication outside explicit report paths')
        if expected_previous:
            self.assert_report_tree(expected_previous, source_commit)
        base = expected_previous or source_commit
        with tempfile.TemporaryDirectory() as temporary:
            environment = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary)/'index'),
                               GIT_AUTHOR_NAME='github-actions[bot]', GIT_COMMITTER_NAME='github-actions[bot]',
                               GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
                               GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')
            self.git('read-tree', base, env=environment)
            for path, content in sorted(files.items()):
                blob = self.git('hash-object', '-w', '--stdin', data=content).decode().strip()
                self.git('update-index', '--add', '--cacheinfo', '100644', blob, path, env=environment)
            tree = self.git('write-tree', env=environment).decode().strip()
            commit = self.git('commit-tree', tree, '-p', base, data=b'PDCA durable report generation\n', env=environment).decode().strip()
        # Non-force push rejects a concurrent writer even after the preceding head check.
        self.git('push', '--quiet', self.remote, commit+':refs/heads/'+branch)
        return commit


def verify_checkpoint(directory, run_id, require_result=False):
    directory = Path(directory)
    before = (directory/'checkpoint.json').read_bytes()
    cp = json.loads(before)
    checksum = json.loads((directory/'checkpoint.sha256.json').read_text())
    if cp['run_id'] != run_id or digest(cp) != checksum['sha256']:
        raise ValueError('Checkpoint identity/digest mismatch')
    for relative, expected in cp['outputs'].items():
        if file_hash(safe_path(directory, relative)) != expected:
            raise ValueError(f'Checkpoint artifact mismatch: {relative}')
    if (directory/'checkpoint.json').read_bytes() != before:
        raise ValueError('Checkpoint generation changed during read')
    if require_result or cp.get('result_sha256'):
        if file_hash(directory/'run_manifest.json') != cp.get('result_sha256'):
            raise ValueError('Current run manifest is not checkpoint-bound')
        result = json.loads((directory/'run_manifest.json').read_text())
        finalization = json.loads((directory/'finalization_checkpoint.json').read_text())
        if digest(finalization) != result['checkpoint_sha256']:
            raise ValueError('Finalization checkpoint chain mismatch')
        if result['run_id'] != run_id:
            raise ValueError('Result identity mismatch')
        names = [s['name'] for s in result['stages']]
        if set(names) != set(STAGE_NAMES) or len(names) != len(STAGE_NAMES):
            raise ValueError('Every required stage must occur exactly once')
        for item in result['stages']:
            validate_stage(item, item['name'])
        if overall_status(result['stages']) != result['overall_status'] or result['completed'] != (result['overall_status'] == 'PASS'):
            raise ValueError('Result aggregate/completion disagrees with stages')
    return cp


def _limits(files):
    if len(files) > MAX_FILES or sum(len(raw) for raw in files.values()) > MAX_BUNDLE_BYTES or any(len(raw) > MAX_FILE_BYTES for raw in files.values()):
        raise RecoveryBlocked('RECOVERY_BUNDLE_LIMIT: maximum 2000 files, 20MiB total, 5MiB per file')


def build_bundle(root, night, run_id, source_commit, transport):
    validate_night(night); _run_id(run_id); _sha(source_commit)
    prefix = f'reports/pdca/{night}/runs/{run_id}/'
    directory = safe_path(Path(root), prefix)
    cp = verify_checkpoint(directory, run_id)
    identity = inspect_run_identity(Path(root), night, execution_root=root)
    if identity['run_id'] != run_id:
        raise ValueError('Recovery source scientific identity changed')
    evidence = json.loads((directory/'evidence_manifest.json').read_text())
    files = {}
    relative_files = set(cp['outputs']) | {'checkpoint.json', 'checkpoint.sha256.json', 'evidence_manifest.json'}
    if cp.get('result_sha256'):
        relative_files.add('run_manifest.json')
    for relative in relative_files:
        files[prefix+relative] = safe_path(directory, relative).read_bytes()
    sources = []
    for entry in evidence['entries']:
        path = entry['path']
        try:
            raw = transport.read(source_commit, path)
        except TransportError:
            raw = b''
        origin = 'commit'
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            if Path(path).parts[0] not in {'data', 'features', 'evidence', 'predictions', 'models', 'model_specs', 'protocols', 'policies'}:
                raise RecoveryBlocked('RECOVERY_SOURCE_UNAVAILABLE: executable/config input is not pinned: '+path)
            if raw:
                raise RecoveryBlocked('RECOVERY_SOURCE_UNAVAILABLE: consumed source differs from pinned commit: '+path)
            raw = safe_path(directory/'snapshot', path).read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise RecoveryBlocked('RECOVERY_SOURCE_UNAVAILABLE: '+path)
            origin = 'bundle'
            files[prefix+'snapshot/'+path] = raw
        sources.append({'path': path, 'sha256': entry['sha256'], 'size_bytes': entry['size_bytes'], 'origin': origin})
    manifest_path = f'reports/pdca/{night}/bridge/recovery-{run_id}.json'
    manifest = {'schema_version': '1.0', 'night': night, 'run_id': run_id, 'source_commit': source_commit,
                'identity': identity, 'sources': sources, 'files': [{'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)} for path, raw in sorted(files.items())]}
    files[manifest_path] = canonical_bytes(manifest)+b'\n'
    _limits(files)
    verify_checkpoint(directory, run_id)
    return {'manifest_path': manifest_path, 'files': files, 'manifest': manifest}


def restore_bundle(transport, bundle_commit, manifest_path, destination, trusted_source_commit):
    _sha(trusted_source_commit)
    # Every reuse path, including a new issue sharing a completed run, must
    # establish report-only provenance before restoring or advertising it.
    transport.assert_report_tree(bundle_commit, trusted_source_commit)
    raw_manifest = transport.read(bundle_commit, manifest_path)
    if len(raw_manifest) > MAX_FILE_BYTES:
        raise RecoveryBlocked('Oversized recovery manifest')
    manifest = json.loads(raw_manifest)
    night, run_id = manifest['night'], manifest['run_id']
    validate_night(night); _run_id(run_id)
    if manifest['source_commit'] != trusted_source_commit or manifest_path != f'reports/pdca/{night}/bridge/recovery-{run_id}.json':
        raise ValueError('Recovery source/manifest binding mismatch')
    prefix = f'reports/pdca/{night}/runs/{run_id}/'
    files = {manifest_path: raw_manifest}
    sizes = [entry['size_bytes'] for entry in manifest['files']]
    if (len(sizes)+1 > MAX_FILES or any(type(size) is not int or size < 0 or size > MAX_FILE_BYTES for size in sizes)
            or sum(sizes)+len(raw_manifest) > MAX_BUNDLE_BYTES):
        raise RecoveryBlocked('RECOVERY_BUNDLE_LIMIT: declared report inventory exceeds caps')
    for entry in manifest['files']:
        path = entry['path']
        safe_path(Path('/validate'), path)
        if not path.startswith(prefix) or path in files or entry['size_bytes'] > MAX_FILE_BYTES:
            raise ValueError('Unsafe, duplicate or oversized bundle path')
        raw = transport.read(bundle_commit, path)
        if len(raw) != entry['size_bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Recovery bundle hash/size mismatch')
        files[path] = raw
        _limits(files)
    evidence = json.loads(files[prefix+'evidence_manifest.json'])
    inventory = {e['path']: {'sha256': e['sha256'], 'size_bytes': e['size_bytes']}
                 for e in evidence['entries']}
    restored_inventory = {e['path']: {'sha256': e['sha256'], 'size_bytes': e['size_bytes']}
                          for e in manifest['sources']}
    if (len(inventory) != len(evidence['entries']) or len(restored_inventory) != len(manifest['sources'])
            or inventory != restored_inventory or digest(inventory) != evidence['input_snapshot_sha256']):
        raise ValueError('Recovery inventory is incomplete or inconsistent')
    identity = manifest['identity']
    if (identity.get('run_id') != run_id or identity.get('night') != night or identity.get('inputs') != inventory
            or digest({k: v for k, v in identity.items() if k != 'run_id'}) != run_id):
        raise ValueError('Recovery scientific identity does not bind inventory')
    if prefix+'run_manifest.json' in files:
        result = json.loads(files[prefix+'run_manifest.json'])
        if (result['input_manifest_sha256'] != digest(evidence) or result['code_sha256'] != identity['code']
                or result['policy_sha256'] != digest(identity['policy']) or result['runtime'] != identity['runtime']
                or result['operational_night'] != night):
            raise ValueError('Recovery result identity mismatch')
    destination = transport.source_workspace(trusted_source_commit, destination)
    for entry in manifest['sources']:
        relative = entry['path']
        path = safe_path(destination, relative)
        if entry['origin'] not in ('commit', 'bundle'):
            raise ValueError('Unknown source origin')
        if entry['origin'] == 'bundle' and Path(relative).parts[0] not in {'data', 'features', 'evidence', 'predictions', 'models', 'model_specs', 'protocols', 'policies'}:
            raise ValueError('Recovery cannot install executable source from report branches')
        raw = transport.read(trusted_source_commit, relative) if entry['origin'] == 'commit' else files[prefix+'snapshot/'+relative]
        if len(raw) != entry['size_bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Pinned source reconstruction mismatch')
        path.parent.mkdir(parents=True, exist_ok=True)
        # Existing pinned raw/ORIGINAL can only already equal the expected bytes.
        if path.exists() and path.read_bytes() != raw:
            raise RecoveryBlocked('RECOVERY_SOURCE_UNAVAILABLE: cannot overwrite pinned input '+relative)
        if not path.exists():
            path.write_bytes(raw)
        snapshot_path = safe_path(destination, prefix+'snapshot/'+relative)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(raw)
    for relative, raw in files.items():
        path = safe_path(destination, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != raw:
            raise ValueError('Restore would overwrite differing artifact')
        path.write_bytes(raw)
    verify_checkpoint(destination/prefix, run_id)
    return manifest


def run_local(root, night, attempt_output, timeout_seconds=ATTEMPT_TIMEOUT, context_path=None):
    root, attempt_output = Path(root), Path(attempt_output)
    validate_night(night)
    compatibility = safe_path(root, f'reports/pdca/{night}/pdca_result.json')
    compatibility.unlink(missing_ok=True)
    attempt_output.unlink(missing_ok=True)
    identity = inspect_run_identity(root, night, execution_root=root)
    command = [sys.executable, str(root/'scripts/run_pdca.py'), '--root', str(root), '--night', night,
               '--budget-seconds', str(SCIENTIFIC_BUDGET), '--output', str(attempt_output)]
    if context_path is not None:
        command += ['--bridge-context', str(context_path)]
    try:
        process = subprocess.run(command, capture_output=True, timeout=timeout_seconds)
        if process.returncode not in (0, 2) or not attempt_output.is_file():
            raise ValueError(f'Unexpected execution exit {process.returncode} or missing attempt output')
        result = json.loads(attempt_output.read_text())
        if result['run_id'] != identity['run_id'] or result['operational_night'] != night:
            raise ValueError('Attempt result is not bound to expected scientific identity')
        for key, expected in [('code_sha256', identity['code']), ('policy_sha256', digest(identity['policy'])), ('runtime', identity['runtime'])]:
            if result[key] != expected:
                raise ValueError('Result code/policy/runtime mismatch')
        directory = root/f'reports/pdca/{night}/runs/{result["run_id"]}'
        verify_checkpoint(directory, result['run_id'], require_result=True)
        if result != json.loads((directory/'run_manifest.json').read_text()):
            raise ValueError('Attempt output differs from authoritative manifest')
        if (process.returncode == 2) != (result['overall_status'] in ('BLOCKED', 'FAIL')):
            raise ValueError('Execution status and manifest severity disagree')
        return {'status': result['overall_status'], 'result': result, 'exit_code': process.returncode,
                'reason': '; '.join(result['required_conditions'])}
    except (ValueError, OSError, subprocess.TimeoutExpired, KeyError, TypeError) as exc:
        failure = {'status': 'FAIL', 'reason': f'BRIDGE_EXECUTION_FAILED: {exc}', 'run_id': identity['run_id']}
        if context_path is not None:
            error_path = Path(context_path).with_suffix('.error.json')
            try:
                publication_error = json.loads(error_path.read_text())
                if publication_error.get('status') in ('BLOCKED', 'FAIL') and isinstance(publication_error.get('reason'), str):
                    failure.update(recovery_status=publication_error['status'],
                                   reason=failure['reason']+'; '+publication_error['reason'])
            except (OSError, ValueError, AttributeError):
                pass  # Missing/malformed diagnostics never replace the current failure.
        atomic_json(attempt_output, failure)
        return failure


def discover_commands(repository, issues, receipt_lookup, *, receipt_validator=None, diagnostics=None):
    pending = []
    diagnostics = diagnostics if diagnostics is not None else []
    for issue in issues:
        if 'pull_request' in issue:
            continue
        try:
            command = authorize_command(repository, issue)
        except (ValueError, KeyError, TypeError):
            continue
        try:
            receipt = receipt_lookup(command)
            if receipt is not None and not isinstance(receipt, dict):
                raise ValueError('Receipt must be an object')
            if receipt and receipt.get('state') == 'HANDLED':
                if receipt_validator is None:
                    raise ValueError('HANDLED receipt has no authoritative run/result verification')
                receipt_validator(command, receipt)
                continue
            attempted = (receipt or {}).get('last_attempt_at', '')
            if not isinstance(attempted, str):
                raise ValueError('Malformed receipt attempt time')
            pending.append((0, attempted, command['issue']))
        except (ValueError, KeyError, TypeError, AttributeError, OSError, TransportError) as exc:
            diagnostics.append({'issue': command['issue'], 'command_id': command['command_id'],
                                'status': 'FAIL', 'reason': 'CORRUPT_OR_UNVERIFIED_RECEIPT: '+str(exc)})
            # Retain the command for explicit failure/review, behind healthy work.
            # Never treat corruption as HANDLED or reset its scientific ledger.
            pending.append((1, '', command['issue']))
    return [number for _, _, number in sorted(pending)]


class GitHubAPI:
    """Existing gh/GITHUB_TOKEN transport; no added permissions or arbitrary commands."""
    def __init__(self, repository):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid repository')
        self.repository = repository
        self.default_branch = None

    def request(self, path='', method='GET', value=None):
        command = ['gh', 'api', '--method', method, 'repos/'+self.repository+('/'+path if path else '')]
        data = None
        if value is not None:
            command += ['--input', '-']
            data = canonical_bytes(value)
        process = subprocess.run(command, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode:
            raise TransportError('GitHub API request failed: '+process.stderr.decode(errors='replace')[:500])
        return json.loads(process.stdout) if process.stdout.strip() else None

    def pages(self, path):
        result = []
        for page in range(1, 101):
            rows = self.request(path+('&' if '?' in path else '?')+f'per_page=100&page={page}')
            result.extend(rows)
            if len(rows) < 100:
                return result
        raise RecoveryBlocked('GitHub listing pagination bound exceeded')

    def default_source(self):
        from urllib.parse import quote
        self.default_branch = self.request()['default_branch']
        return _sha(self.request('commits/'+quote(self.default_branch, safe=''))['sha'])

    def issue(self, number):
        return self.request('issues/'+str(int(number)))

    def open_issues(self):
        return self.pages('issues?state=open&sort=created&direction=asc')

    def ensure_pr(self, branch, night):
        from urllib.parse import urlencode
        query = urlencode({'state': 'all', 'head': self.repository.split('/')[0]+':'+branch, 'base': self.default_branch})
        existing = self.request('pulls?'+query)
        if existing:
            return existing[0]['html_url']
        return self.request('pulls', 'POST', {'head': branch, 'base': self.default_branch,
            'title': 'PDCA evidence: '+night,
            'body': 'Bounded generated evidence and verified recovery metadata. Scientific BLOCKED/FAIL is recorded honestly; this report does not complete Master Goal #1642.'})['html_url']

    def upsert_comment(self, number, command_id, body):
        marker = '<!-- habu-pdca:'+command_id+' -->'
        text = marker+'\n'+body
        existing = [c for c in self.pages(f'issues/{number}/comments')
                    if marker in (c.get('body') or '') and c.get('user', {}).get('login') == 'github-actions[bot]']
        if existing:
            self.request('issues/comments/'+str(existing[0]['id']), 'PATCH', {'body': text})
        else:
            self.request(f'issues/{number}/comments', 'POST', {'body': text})

    def mark_handled(self, number):
        try:
            self.request('labels/pdca-handled')
        except TransportError:
            self.request('labels', 'POST', {'name': 'pdca-handled', 'color': '5319e7',
                                           'description': 'Command evidence persisted; not scientific/master completion'})
        self.request(f'issues/{number}/labels', 'POST', {'labels': ['pdca-handled']})


def _record(transport, branch, path):
    head = transport.head(branch)
    if head is None:
        return None, None
    value = json.loads(transport.read(head, path))
    if not isinstance(value, dict) or value.get('schema_version') != '1.0':
        raise ValueError('Malformed durable receipt object/schema')
    return head, value


def _write_record(transport, branch, source, previous, path, value):
    return transport.publish(branch, source, previous, {path: canonical_bytes(value)+b'\n'})


def checkpoint_publisher(context_path):
    """Fixed synchronous worker callback; every acknowledged generation is remote."""
    context_path = Path(context_path)
    context = json.loads(context_path.read_text())
    transport = GitTransport(context['transport_root'], context['remote'])
    def publish(directory, checkpoint):
        try:
            if checkpoint['run_id'] != context['run_id']:
                raise ValueError('Checkpoint does not match prebound command identity')
            bundle = build_bundle(context['execution_root'], context['night'], context['run_id'], context['source_commit'], transport)
            record = dict(context['run_record'], ledger_elapsed=checkpoint['elapsed_seconds'],
                          manifest_path=bundle['manifest_path'],
                          state='COMPUTED' if checkpoint.get('result_sha256') else 'RUNNING',
                          result_sha256=checkpoint.get('result_sha256'))
            files = dict(bundle['files'])
            files[context['run_record_path']] = canonical_bytes(record)+b'\n'
            _limits(files)
            head = transport.publish(context['run_branch'], context['source_commit'], context['expected_head'], files)
            context.update(expected_head=head, run_record=record)
            atomic_json(context_path, context)
        except Exception as exc:
            # Stop the subprocess. The supervisor writes a retryable current-attempt
            # FAIL receipt; unacknowledged work is never called remotely durable.
            atomic_json(context_path.with_suffix('.error.json'), {'status': 'BLOCKED' if isinstance(exc, RecoveryBlocked) else 'FAIL',
                'reason': 'CHECKPOINT_PUBLICATION_FAILED: '+str(exc)})
            raise SystemExit(75) from exc
    return publish, context


def verify_handled_receipt(transport, command, receipt, trusted_default_source):
    """Return authoritative science only after the HANDLED summary is cross-checked."""
    if (not isinstance(receipt, dict) or receipt.get('schema_version') != '1.0'
            or receipt.get('command') != command or receipt.get('state') != 'HANDLED'):
        raise ValueError('Invalid HANDLED command receipt')
    source = _sha(receipt['source_commit'])
    run_id = _run_id(receipt['run_id'])
    bundle_commit = _sha(receipt['bundle_commit'])
    transport.git('fetch', '--quiet', '--no-tags', transport.remote, source)
    if transport.git('merge-base', '--is-ancestor', source, trusted_default_source, check=False).returncode:
        raise ValueError('HANDLED receipt source is not trusted default history')
    branch = 'pdca/run-'+run_id
    if receipt.get('run_branch') != branch:
        raise ValueError('HANDLED receipt run branch mismatch')
    head = transport.head(branch)
    if head is None or transport.git('merge-base', '--is-ancestor', bundle_commit, head, check=False).returncode:
        raise ValueError('HANDLED receipt bundle is not committed in its run branch')
    transport.assert_report_tree(head, source)
    path = f'reports/pdca/{command["night"]}/bridge/run-{run_id}.json'
    record = json.loads(transport.read(bundle_commit, path))
    if (record.get('state') != 'COMPUTED' or record.get('run_id') != run_id
            or record.get('night') != command['night'] or record.get('source_commit') != source
            or record.get('budget_limit') != SCIENTIFIC_BUDGET):
        raise ValueError('HANDLED receipt lacks matching committed run evidence')
    with tempfile.TemporaryDirectory(prefix='habu-verify-handled-') as temporary:
        destination = Path(temporary)/'source'
        manifest = restore_bundle(transport, bundle_commit, record['manifest_path'], destination, source)
        directory = destination/f'reports/pdca/{command["night"]}/runs/{run_id}'
        verify_checkpoint(directory, run_id, require_result=True)
        result = json.loads((directory/'run_manifest.json').read_text())
        result_sha = file_hash(directory/'run_manifest.json')
        if (receipt.get('scientific_status') != result['overall_status']
                or type(receipt.get('completed')) is not bool or receipt['completed'] != result['completed']
                or receipt.get('result_sha256') != result_sha or record.get('result_sha256') != result_sha
                or receipt.get('ledger_elapsed') != result['budget']['elapsed_seconds']
                or receipt.get('max_budget_seconds') != SCIENTIFIC_BUDGET
                or record.get('identity') != manifest['identity']):
            raise ValueError('HANDLED receipt contradicts authoritative run result')
    return result


def execute_command(repository_root, repository, issue_number, api, transport, attempt_id):
    """Refetch authorization, bind a receipt, execute or recover, then finish publication."""
    command = authorize_command(repository, api.issue(int(issue_number)))
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', str(attempt_id)):
        raise ValueError('Invalid attempt identity')
    night = command['night']
    command_branch = 'pdca/command-'+command['command_id']
    command_path = f'reports/pdca/{night}/bridge/command-{command["command_id"]}.json'
    command_head, receipt = _record(transport, command_branch, command_path)
    default_source = _sha(api.default_source())
    transport.git('fetch', '--quiet', '--no-tags', transport.remote, default_source)
    source = _sha(receipt['source_commit']) if receipt else default_source
    command_source = _sha(receipt.get('command_source_commit', source)) if receipt else source
    transport.git('fetch', '--quiet', '--no-tags', transport.remote, command_source)
    if transport.git('merge-base', '--is-ancestor', command_source, default_source, check=False).returncode:
        raise ValueError('Command branch source is not trusted default history')
    transport.git('fetch', '--quiet', '--no-tags', transport.remote, source)
    if transport.git('merge-base', '--is-ancestor', source, default_source, check=False).returncode:
        raise RecoveryBlocked('Recorded source is not an ancestor of the trusted default branch')
    if receipt and (receipt.get('command') != command or receipt.get('schema_version') != '1.0'):
        raise ValueError('Command receipt does not match current authorization')
    if receipt:
        transport.assert_report_tree(command_head, command_source)
    if receipt and receipt.get('state') == 'HANDLED':
        verify_handled_receipt(transport, command, receipt, default_source)
        return receipt
    if receipt and receipt.get('state') != 'HANDLED':
        receipt['last_attempt_at'] = _now().isoformat()
        command_head = _write_record(transport, command_branch, command_source, command_head, command_path, receipt)
    with tempfile.TemporaryDirectory(prefix='habu-pdca-') as temporary:
        temporary = Path(temporary)
        planned = transport.source_workspace(source, temporary/'planned')
        identity = inspect_run_identity(planned, night, execution_root=planned)
        if receipt and receipt['run_id'] != identity['run_id'] and receipt.get('state') != 'HANDLED':
            raise RecoveryBlocked('Recorded source/runtime identity cannot be reproduced; budget is not reset')
        run_id = receipt['run_id'] if receipt else identity['run_id']
        run_branch = 'pdca/run-'+run_id
        run_path = f'reports/pdca/{night}/bridge/run-{run_id}.json'
        run_head, record = _record(transport, run_branch, run_path)
        if receipt is None:
            receipt = {'schema_version': '1.0', 'command': command, 'source_commit': source,
                       'command_source_commit': command_source, 'run_id': run_id,
                       'attempt_id': str(attempt_id), 'last_attempt_at': _now().isoformat(),
                       'state': 'RUNNING', 'max_budget_seconds': SCIENTIFIC_BUDGET,
                       'lease_expires_at': (_now()+timedelta(seconds=LEASE_SECONDS)).isoformat()}
            command_head = _write_record(transport, command_branch, command_source, command_head, command_path, receipt)
        if record and (record.get('run_id') != run_id or record.get('night') != night or record.get('budget_limit') != SCIENTIFIC_BUDGET):
            raise ValueError('Shared run receipt contract mismatch')
        if record and record.get('source_commit') != source:
            # Two source commits may differ only in unconsumed files. Reuse is
            # allowed only when the complete scientific identity agrees.
            if record.get('identity') != identity:
                raise ValueError('Conflicting shared scientific run identity')
            source = _sha(record['source_commit'])
            transport.git('fetch', '--quiet', '--no-tags', transport.remote, source)
            if transport.git('merge-base', '--is-ancestor', source, default_source, check=False).returncode:
                raise ValueError('Shared run source is not trusted history')
        if record and record.get('state') == 'COMPUTED':
            restore_bundle(transport, run_head, record['manifest_path'], temporary/'restored', source)
            directory = temporary/'restored'/f'reports/pdca/{night}/runs/{run_id}'
            verify_checkpoint(directory, run_id, require_result=True)
            result = json.loads((directory/'run_manifest.json').read_text())
            if file_hash(directory/'run_manifest.json') != record.get('result_sha256'):
                raise ValueError('Shared completed result receipt mismatch')
        else:
            now = _now()
            if record and record.get('state') == 'RUNNING' and datetime.fromisoformat(record['lease_expires_at']) > now:
                return dict(receipt, state='RETRYABLE', reason='An unexpired run lease owns this execution')
            floor = float(record.get('ledger_elapsed', 0)) if record else 0.0
            if record and record.get('state') == 'RUNNING':
                prior = record['attempt']
                floor = max(floor, prior['base_elapsed']+prior['limit_seconds'])
            if floor >= SCIENTIFIC_BUDGET:
                receipt.update(state='RETRYABLE', reason='BUDGET_EXHAUSTED: cumulative scientific command allowance consumed', ledger_elapsed=floor)
                _write_record(transport, command_branch, command_source, command_head, command_path, receipt)
                return receipt
            if record and record.get('manifest_path'):
                restore_bundle(transport, run_head, record['manifest_path'], temporary/'restored', source)
                execution_root = temporary/'restored'
            else:
                execution_root = planned
            limit = min(ATTEMPT_TIMEOUT, SCIENTIFIC_BUDGET-floor)
            attempt = {'id': str(attempt_id), 'started_at': now.isoformat(), 'deadline': (now+timedelta(seconds=limit)).isoformat(),
                       'base_elapsed': floor, 'limit_seconds': limit}
            record = dict(record or {}, schema_version='1.0', run_id=run_id, night=night, source_commit=source,
                          identity=identity, budget_limit=SCIENTIFIC_BUDGET, ledger_elapsed=floor,
                          state='RUNNING', attempt=attempt,
                          lease_expires_at=(now+timedelta(seconds=LEASE_SECONDS)).isoformat())
            run_head = _write_record(transport, run_branch, source, run_head, run_path, record)
            context_path = temporary/'checkpoint-context.json'
            atomic_json(context_path, {'transport_root': str(transport.root), 'remote': transport.remote,
                'execution_root': str(execution_root), 'night': night, 'run_id': run_id, 'source_commit': source,
                'run_branch': run_branch, 'run_record_path': run_path, 'run_record': record,
                'expected_head': run_head, 'attempt': attempt})
            remaining_attempt = max(0.0, (datetime.fromisoformat(attempt['deadline'])-_now()).total_seconds())
            outcome = run_local(execution_root, night, temporary/'attempt-output.json',
                                timeout_seconds=remaining_attempt, context_path=context_path)
            run_head, published = _record(transport, run_branch, run_path)
            if 'result' not in outcome:
                elapsed = min(limit, max(0, (_now()-now).total_seconds()))
                record = dict(published or record, state='RETRYABLE', ledger_elapsed=max(floor+elapsed, float((published or record).get('ledger_elapsed', 0))))
                # Preserve a fully committed computation for publication-only retry.
                if published and published.get('state') == 'COMPUTED':
                    record = published
                run_head = _write_record(transport, run_branch, source, run_head, run_path, record)
                receipt.update(state='RETRYABLE', scientific_status='FAIL', reason=outcome['reason'],
                               recovery_status=outcome.get('recovery_status', 'NOT_APPLICABLE'),
                               ledger_elapsed=record['ledger_elapsed'])
                _write_record(transport, command_branch, command_source, command_head, command_path, receipt)
                return receipt
            result = outcome['result']
            if not published or published.get('state') != 'COMPUTED':
                raise RecoveryBlocked('Successful local computation has no durable terminal checkpoint')
            record = published
        receipt.update(state='COMPUTED', source_commit=source, scientific_status=result['overall_status'],
                       completed=result['completed'], result_sha256=record['result_sha256'], bundle_commit=run_head,
                       run_branch=run_branch, ledger_elapsed=result['budget']['elapsed_seconds'])
        command_head = _write_record(transport, command_branch, command_source, command_head, command_path, receipt)
        receipt['pr_url'] = api.ensure_pr(run_branch, night)
        command_head = _write_record(transport, command_branch, command_source, command_head, command_path, receipt)
        reasons = '; '.join(result.get('required_conditions', []))[:3000]
        api.upsert_comment(command['issue'], command['command_id'],
            f'Habu AI PDCA: **{result["overall_status"]}**\n\nOperational night: {night}\nRun: `{run_id}`\n'
            f'Report: {receipt["pr_url"]}\n\n{reasons}\n\nCommand evidence is persisted. Master Goal #1642 remains incomplete; handled does not mean scientific completion.')
        api.mark_handled(command['issue'])
        receipt.update(state='HANDLED', lease_expires_at=None)
        _write_record(transport, command_branch, command_source, command_head, command_path, receipt)
        return receipt
