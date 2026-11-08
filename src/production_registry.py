"""Pure, unsubmitted transition proposals under the existing Task8 design.

Supplied JSON can establish consistency only. Nothing here authenticates a
review, source, clock or model, activates proposed event/pointer bytes, or
selects an actual registry ref, transport, context or publication authority.

TaskS contracts are JSON-only. ``habu-registry-core-policy-v1`` declares an
existing anchor(commit_sha, root_event_sha256, files_sha256), repository/ref,
scoped paths, compatible code hashes and required gate IDs. A snapshot supplies
complete canonical scoped file bytes for every commit from that anchor and
intent/gate proofs for subsequent activations. This v1 supports one fixed
declared policy epoch and an anchored suffix, not pre-anchor/global history.
The non-genesis anchor is supplied, never synthesized; genesis anchors block.
Historical anchor bytes are hash-bound, not reauthenticated or scientifically
reproduced. Changing that anchor cannot establish new authority.

An intent envelope separates its premerge document+reviewed_ref from merged_ref;
only the latter names the subsequently observed merge commit. Events contain no
own future state-commit SHA. Inference records bind model/code, cutoff/windows,
input/component hashes and actual supplied output bytes. They do not prove that
inference ran, that external model/input hashes are authentic, or that science
passed. The host must establish those independently. Compatible-code listing is
a declared allowlist, not a compatibility proof; v1 does not rebind one model
digest to different code/protocol metadata.

Proposals include an immutable pending descriptor (transition proof included)
for byte-exact ambiguous-ACK reconciliation. No function performs I/O, constructs
ProductionContext, authenticates observed_at, updates a ref or allocates a live
version. Fixed runtime limits are cooperative and do not claim hard preemption.

Privacy: the actual repository is PUBLIC. These inline-byte proposals are
synthetic/unpublished mechanics, not permission to send private GPS, logs,
derived models, inference or search routes to any public ref. A future host
writer must freshly verify remote visibility and an independently reviewed,
authorized durable-artifact layout; it cannot treat candidate private/complete
flags or these false-authority results as publication permission. Private
durability/public-hash-only design is unresolved; no storage/visibility/genesis
choice or new service is made here.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from time import monotonic

from master_contracts import canonical_bytes

MAX_NODES = 100_000
MAX_DEPTH = 24
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_STRING_BYTES = 64 * 1024
MAX_FILES = 4096
FLAGS = dict(source_authentication='NOT_ATTESTED',
             scientific_reproduction='NOT_REPRODUCED',
             production_authorized=False, official_issuance_authorized=False,
             registry_activated=False)
POLICY_FIELDS = {'schema_version', 'repository', 'task_id', 'registry_root',
                 'record_directory', 'pointer_path', 'intent_prefix',
                 'allowed_operations', 'code_sha256'}
INTENT_FIELDS = {'schema_version', 'repository', 'task_id', 'operation',
                 'expected_previous_event_sha256', 'reviewed_intent',
                 'artifact_bindings'}
PREDECESSOR_FIELDS = {'schema_version', 'ref_commit_sha', 'current_event_sha256',
                      'files', 'current_pointer'}
BINDINGS = {'code_sha256', 'policy_sha256', 'model_sha256',
            'evidence_sha256', 'protocol_sha256'}


class _Rejected(ValueError):
    def __init__(self, code, status='FAIL'):
        self.code, self.status = code, status


class _Budget:
    def __init__(self, seconds):
        kind = type(seconds)
        if (not (kind is int or kind is float) or not 0 < seconds <= 30
                or not math.isfinite(seconds)):
            raise _Rejected('INVALID_BUDGET')
        self.deadline = monotonic() + seconds
        self.nodes = self.input_bytes = self.encoded_bytes = 0

    def check(self):
        if monotonic() >= self.deadline:
            raise _Rejected('DEADLINE_EXCEEDED', 'BLOCKED')


def _owned(value, budget):
    """Copy only exact JSON builtins, never deepcopy or foreign type equality."""
    active = set()

    def visit(item, depth):
        budget.check()
        budget.nodes += 1
        if budget.nodes > MAX_NODES or depth > MAX_DEPTH:
            raise _Rejected('JSON_CAPACITY_EXCEEDED', 'BLOCKED')
        kind = type(item)
        if kind is str:
            if len(item) > MAX_STRING_BYTES:
                raise _Rejected('STRING_CAPACITY_EXCEEDED', 'BLOCKED')
            try:
                size = len(item.encode('utf-8'))
            except UnicodeError:
                raise _Rejected('INVALID_JSON_TEXT') from None
            if size > MAX_STRING_BYTES:
                raise _Rejected('STRING_CAPACITY_EXCEEDED', 'BLOCKED')
            budget.input_bytes += size
            result = item
        elif kind is int:
            if not -(2**63) <= item < 2**63:
                raise _Rejected('INTEGER_RANGE')
            result = item
        elif kind is float:
            if not math.isfinite(item):
                raise _Rejected('NONFINITE_JSON_NUMBER')
            result = item
        elif kind is bool or item is None:
            result = item
        elif kind is dict or kind is list:
            identity = id(item)
            if identity in active:
                raise _Rejected('JSON_CYCLE')
            active.add(identity)
            if kind is dict:
                result = {}
                for key, child in item.items():
                    if type(key) is not str:
                        raise _Rejected('JSON_KEY_TYPE')
                    result[visit(key, depth + 1)] = visit(child, depth + 1)
            else:
                result = [visit(child, depth + 1) for child in item]
            active.remove(identity)
        else:
            raise _Rejected('JSON_TYPE_REQUIRED')
        budget.input_bytes += 8
        if budget.input_bytes > MAX_JSON_BYTES:
            raise _Rejected('JSON_BYTE_CAPACITY_EXCEEDED', 'BLOCKED')
        budget.check()
        return result

    return visit(value, 0)


def _fields(value, expected):
    if type(value) is not dict or set(value) != expected:
        raise _Rejected('EXACT_FIELDS_REQUIRED')


def _sha(value, length=64):
    if type(value) is not str or re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is None:
        raise _Rejected('INVALID_HASH')
    return value


def _text(value):
    if (type(value) is not str or not value or len(value) > 256
            or value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise _Rejected('INVALID_IDENTIFIER')
    return value


def _repository(value):
    _fields(value, {'id', 'full_name'})
    if type(value['id']) is not int or value['id'] <= 0:
        raise _Rejected('REPOSITORY_ID_REQUIRED')
    name = _text(value['full_name'])
    if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+', name) is None:
        raise _Rejected('REPOSITORY_NAME_REQUIRED')


def _path(value):
    _text(value)
    if '\\' in value or ':' in value:
        raise _Rejected('CANONICAL_PATH_REQUIRED')
    parts = value.split('/')
    if any(part == '' or part == '.' or part == '..' or part != part.rstrip(' .') for part in parts):
        raise _Rejected('CANONICAL_PATH_REQUIRED')
    lower = [part.casefold() for part in parts]
    if ('.git' in lower or 'sealed' in lower or 'confirmation' in lower
            or lower[:2] == ['data', 'raw']
            or lower[:2] == ['predictions', 'original']
            or lower[:2] == ['predictions', 'recovered_original']):
        raise _Rejected('PROTECTED_PATH_FORBIDDEN')
    return value


def _inside(path, directory):
    return path.startswith(directory + '/')


def _encode(value, budget, newline=False):
    budget.check()
    raw = canonical_bytes(value) + (b'\n' if newline else b'')
    budget.encoded_bytes += len(raw)
    if budget.encoded_bytes > MAX_JSON_BYTES:
        raise _Rejected('ENCODING_CAPACITY_EXCEEDED', 'BLOCKED')
    budget.check()
    return raw


def _hash(raw, budget):
    result = hashlib.sha256()
    for offset in range(0, len(raw), 65536):
        budget.check()
        result.update(raw[offset:offset + 65536])
        budget.check()
    budget.check()
    return result.hexdigest()


def _result(status, *, reason=None, spec=None, computed=None):
    return dict(schema_version='habu-production-transition-proposal-v1',
                status=status, reason_codes=[] if reason is None else [reason],
                commit_spec=spec, computed={} if computed is None else computed,
                **FLAGS)


def prepare_transition_proposal(predecessor, intent, *, policy, expected_ref_sha,
                                expected_previous_event_sha256, max_seconds=1.0):
    """Return an inert addition and CAS descriptor, never active-pointer bytes.

    ``policy`` supplies a declared namespace/layout, not an authenticated policy.
    ``reviewed_intent`` binds an exact repository/commit/path/hash as a declaration;
    neither it nor a successful proposal attests independent review or science.
    Budgets include snapshotting, canonical encoding and hashing cooperatively.
    No hard preemption, Git commit, atomicity or real clock provenance is claimed.
    Collision checks cover only the supplied, unauthenticated file inventory.
    ``expected_absent`` is an unexecuted precondition; a future authorized writer
    must obtain/verify the actual complete tree and enforce it, never trust a
    caller's inventory or treat this proposal as evidence of remote absence.
    """
    try:
        budget = _Budget(max_seconds)
        values = _owned(dict(predecessor=predecessor, intent=intent, policy=policy,
                             expected_ref_sha=expected_ref_sha,
                             expected_previous_event_sha256=expected_previous_event_sha256), budget)
        predecessor, intent, policy = (values[key] for key in ('predecessor', 'intent', 'policy'))
        expected_ref_sha = values['expected_ref_sha']
        expected_previous_event_sha256 = values['expected_previous_event_sha256']
        _fields(policy, POLICY_FIELDS)
        if policy['schema_version'] != 'habu-production-proposal-policy-v1':
            raise _Rejected('POLICY_SCHEMA')
        _repository(policy['repository'])
        _text(policy['task_id'])
        _sha(policy['code_sha256'])
        root = _path(policy['registry_root'])
        directory = _path(policy['record_directory'])
        pointer_path = _path(policy['pointer_path'])
        intent_prefix = _path(policy['intent_prefix'])
        if (not _inside(directory, root) or not _inside(pointer_path, root)
                or directory == pointer_path or _inside(pointer_path, directory)
                or _inside(directory, pointer_path)):
            raise _Rejected('REGISTRY_LAYOUT_SCOPE')
        operations = policy['allowed_operations']
        if (type(operations) is not list or not 1 <= len(operations) <= 2
                or any(type(operation) is not str or operation not in ('PROMOTE', 'ROLLBACK') for operation in operations)
                or len(set(operations)) != len(operations)):
            raise _Rejected('POLICY_OPERATIONS')
        policy_sha = _hash(_encode(policy, budget), budget)
        _fields(intent, INTENT_FIELDS)
        if intent['schema_version'] != 'habu-production-transition-request-v1':
            raise _Rejected('INTENT_SCHEMA')
        _repository(intent['repository'])
        if intent['repository'] != policy['repository'] or intent['task_id'] != policy['task_id']:
            raise _Rejected('INTENT_IDENTITY')
        if type(intent['operation']) is not str or intent['operation'] not in operations:
            raise _Rejected('OPERATION_NOT_ALLOWED')
        reviewed = intent['reviewed_intent']
        _fields(reviewed, {'repository', 'commit_sha', 'path', 'sha256'})
        _repository(reviewed['repository'])
        if reviewed['repository'] != policy['repository']:
            raise _Rejected('REVIEWED_INTENT_REPOSITORY')
        _sha(reviewed['commit_sha'], 40)
        _sha(reviewed['sha256'])
        if not _inside(_path(reviewed['path']), intent_prefix) or not reviewed['path'].endswith('.json'):
            raise _Rejected('REVIEWED_INTENT_PATH')
        bindings = intent['artifact_bindings']
        _fields(bindings, BINDINGS)
        for value in bindings.values():
            _sha(value)
        if bindings['code_sha256'] != policy['code_sha256'] or bindings['policy_sha256'] != policy_sha:
            raise _Rejected('ARTIFACT_BINDING_MISMATCH')
        if predecessor is None or expected_ref_sha is None or expected_previous_event_sha256 is None:
            raise _Rejected('EXISTING_PREDECESSOR_REQUIRED', 'BLOCKED')
        _sha(expected_ref_sha, 40)
        _sha(expected_previous_event_sha256)
        if type(predecessor) is not dict:
            raise _Rejected('PREDECESSOR_OBJECT_REQUIRED')
        if set(predecessor) - PREDECESSOR_FIELDS:
            raise _Rejected('EXACT_FIELDS_REQUIRED')
        if ('schema_version' in predecessor and predecessor['schema_version'] !=
                'habu-production-registry-predecessor-v1'):
            raise _Rejected('PREDECESSOR_SCHEMA')
        if predecessor.get('ref_commit_sha') is None or predecessor.get('current_event_sha256') is None:
            raise _Rejected('EXISTING_PREDECESSOR_REQUIRED', 'BLOCKED')
        if predecessor.get('current_pointer') is None or predecessor.get('files') is None:
            raise _Rejected('POINTER_PROOF_MISSING', 'BLOCKED')
        _fields(predecessor, PREDECESSOR_FIELDS)
        if predecessor['schema_version'] != 'habu-production-registry-predecessor-v1':
            raise _Rejected('PREDECESSOR_SCHEMA')
        _sha(predecessor['ref_commit_sha'], 40)
        _sha(predecessor['current_event_sha256'])
        _sha(intent['expected_previous_event_sha256'])
        if (predecessor['ref_commit_sha'] != expected_ref_sha
                or predecessor['current_event_sha256'] != expected_previous_event_sha256
                or intent['expected_previous_event_sha256'] != expected_previous_event_sha256):
            raise _Rejected('PREDECESSOR_CONFLICT')
        pointer = predecessor['current_pointer']
        if type(pointer) is dict:
            if set(pointer) - {'event_sha256'}:
                raise _Rejected('EXACT_FIELDS_REQUIRED')
            if pointer.get('event_sha256') is None:
                raise _Rejected('POINTER_PROOF_MISSING', 'BLOCKED')
        _fields(pointer, {'event_sha256'})
        _sha(pointer['event_sha256'])
        if pointer['event_sha256'] != expected_previous_event_sha256:
            raise _Rejected('POINTER_EVENT_CONFLICT')
        files = predecessor['files']
        if type(files) is not list:
            raise _Rejected('FILE_MANIFEST_REQUIRED')
        if len(files) > MAX_FILES:
            raise _Rejected('FILE_CAPACITY_EXCEEDED', 'BLOCKED')
        by_path = {}
        for item in files:
            budget.check()
            if type(item) is dict:
                if set(item) - {'path', 'sha256'}:
                    raise _Rejected('EXACT_FIELDS_REQUIRED')
                if item.get('path') == pointer_path and item.get('sha256') is None:
                    raise _Rejected('POINTER_PROOF_MISSING', 'BLOCKED')
            _fields(item, {'path', 'sha256'})
            path = _path(item['path'])
            if not _inside(path, root) or path in by_path:
                raise _Rejected('FILE_SCOPE_OR_DUPLICATE')
            by_path[path] = _sha(item['sha256'])
        for path in by_path:
            budget.check()
            parts = path.split('/')
            if any('/'.join(parts[:index]) in by_path for index in range(1, len(parts))):
                raise _Rejected('FILE_DIRECTORY_CONFLICT')
        if pointer_path not in by_path:
            raise _Rejected('POINTER_PROOF_MISSING', 'BLOCKED')
        pointer_sha = _hash(_encode(pointer, budget, newline=True), budget)
        if by_path[pointer_path] != pointer_sha:
            raise _Rejected('POINTER_HASH_CONFLICT')
        request_sha = _hash(_encode(intent, budget), budget)
        record = dict(schema_version='habu-production-transition-proposal-record-v1',
                      status='PROPOSAL_NOT_ACTIVATED', repository=intent['repository'],
                      task_id=intent['task_id'], operation=intent['operation'],
                      expected_ref_sha=expected_ref_sha,
                      expected_previous_event_sha256=expected_previous_event_sha256,
                      expected_pointer_sha256=pointer_sha,
                      reviewed_intent=reviewed, artifact_bindings=bindings,
                      request_sha256=request_sha, policy_sha256=policy_sha, **FLAGS)
        raw = _encode(record, budget, newline=True)
        record_sha = _hash(raw, budget)
        path = _path(directory + '/' + record_sha + '.json')
        if path in by_path:
            if by_path[path] != record_sha:
                raise _Rejected('IMMUTABLE_RECORD_CONFLICT')
            raise _Rejected('PROPOSAL_RECORD_ALREADY_PRESENT', 'BLOCKED')
        for existing in by_path:
            budget.check()
            if _inside(path, existing) or _inside(existing, path):
                raise _Rejected('FILE_DIRECTORY_CONFLICT')
        file_manifest_sha = _hash(_encode([{'path': name, 'sha256': by_path[name]}
                                          for name in sorted(by_path)], budget), budget)
        spec = dict(parents=[expected_ref_sha], immutable_additions=[dict(
            path=path, sha256=record_sha, size_bytes=len(raw), content_utf8=raw.decode('utf-8'),
            expected_absent=True)],
            pointer_update=dict(path=pointer_path, expected_file_sha256=pointer_sha,
                                expected_previous_event_sha256=expected_previous_event_sha256,
                                next_proposal_sha256=record_sha))
        budget.check()
        return _result('PROPOSAL_NOT_ACTIVATED', spec=spec, computed=dict(
            request_sha256=request_sha, policy_sha256=policy_sha,
            predecessor_files_sha256=file_manifest_sha, proposal_record_sha256=record_sha))
    except _Rejected as exc:
        return _result(exc.status, reason=exc.code)


# TaskS is a separate closed contract. The original proposal API above and its
# identifiers remain unchanged. These are proposed bytes, never live events.
CORE_POLICY_FIELDS = {'schema_version', 'repository', 'task_id', 'state_ref',
    'registry_root', 'event_directory', 'issuance_directory', 'pointer_path',
    'version_index_path', 'intent_prefix', 'anchor', 'compatible_code_sha256',
    'required_gate_ids'}
CORE_DOCUMENT_FIELDS = {'path', 'sha256', 'size_bytes', 'content_utf8'}
CORE_INTENT_FIELDS = {'schema_version', 'repository', 'task_id', 'operation',
    'operation_id', 'expected_previous_event_sha256', 'model_sha256',
    'code_sha256', 'code_manifest', 'protocol_sha256', 'evidence_sha256', 'policy_sha256'}
CORE_EVENT_FIELDS = {'schema_version', 'operation_id', 'operation',
    'previous_event_sha256', 'model_sha256', 'code_sha256', 'code_manifest',
    'protocol_sha256', 'policy_sha256', 'evidence_sha256', 'intent_sha256',
    'gate_decision_sha256', 'reviewed_ref', 'merged_ref', 'observed_at', 'event_sha256'}
CORE_INFERENCE_FIELDS = {'schema_version', 'operation_id', 'operational_night',
    'cutoff_time', 'training_cutoff', 'forecast_windows', 'selected_event_sha256',
    'model_sha256', 'code_sha256', 'input_bundle_sha256', 'component_receipts_sha256', 'output'}
CORE_ISSUANCE_FIELDS = (CORE_INFERENCE_FIELDS - {'output'}) | {
    'version', 'observed_at', 'output_ref'}
CORE_MAX_COMMITS = 128
_JST = timezone(timedelta(hours=9))


def _required(value, fields):
    if value is None:
        raise _Rejected('REQUIRED_FACT_MISSING', 'BLOCKED')
    if type(value) is not dict or set(value) - fields:
        raise _Rejected('EXACT_FIELDS_REQUIRED')
    if set(value) != fields:
        raise _Rejected('REQUIRED_FACT_MISSING', 'BLOCKED')


def _array(value, nonempty=False):
    if value is None:
        raise _Rejected('REQUIRED_FACT_MISSING', 'BLOCKED')
    if type(value) is not list:
        raise _Rejected('ARRAY_REQUIRED')
    if nonempty and not value:
        raise _Rejected('REQUIRED_FACT_MISSING', 'BLOCKED')
    return value


def _stamp(value):
    if (type(value) is not str or re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value) is None):
        raise _Rejected('AWARE_TIMESTAMP_REQUIRED')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise _Rejected('INVALID_TIMESTAMP') from None


def _operational_night(when):
    try:
        return (when.astimezone(_JST) - timedelta(hours=7)).date().isoformat()
    except OverflowError:
        raise _Rejected('TIMESTAMP_RANGE') from None


def _night(value):
    if type(value) is not str or re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is None:
        raise _Rejected('OPERATIONAL_NIGHT_REQUIRED')
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise _Rejected('OPERATIONAL_NIGHT_REQUIRED') from None
    return value


def _digest(value, budget, newline=False):
    return _hash(_encode(value, budget, newline), budget)


def _core_result(status, reason=None, *, computed=None, spec=None, pending=None):
    return dict(schema_version='habu-registry-core-result-v1', status=status,
        reason_codes=[] if reason is None else [reason],
        supported_scope='SUPPORTED_ANCHORED_SUFFIX_ONLY',
        observed_time_authentication='NOT_ATTESTED', commit_spec=spec, pending=pending,
        computed={} if computed is None else computed, **FLAGS)


def _core_policy(policy, budget):
    _required(policy, CORE_POLICY_FIELDS)
    if policy['schema_version'] != 'habu-registry-core-policy-v1':
        raise _Rejected('CORE_POLICY_SCHEMA')
    _repository(policy['repository']); _text(policy['task_id'])
    ref = policy['state_ref']
    if type(ref) is not str or not ref.startswith('refs/heads/'):
        raise _Rejected('DECLARED_STATE_REF_REQUIRED')
    _path(ref[11:])
    branch = ref[11:]
    if (re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*', branch) is None
            or '..' in branch or any(part.startswith('.') or part.endswith('.lock')
                                      for part in branch.split('/'))):
        raise _Rejected('CANONICAL_STATE_REF_REQUIRED')
    root = _path(policy['registry_root'])
    parts = [policy[k] for k in ('event_directory', 'issuance_directory',
                                'pointer_path', 'version_index_path')]
    for part in parts:
        if not _inside(_path(part), root):
            raise _Rejected('CORE_LAYOUT_SCOPE')
    for index, part in enumerate(parts):
        if any(part == other or _inside(part, other) or _inside(other, part)
               for other in parts[index + 1:]):
            raise _Rejected('CORE_LAYOUT_COLLISION')
    prefix = _path(policy['intent_prefix'])
    if prefix == root or _inside(prefix, root) or _inside(root, prefix):
        raise _Rejected('REVIEWED_INTENT_LAYOUT_COLLISION')
    _required(policy['anchor'], {'commit_sha', 'root_event_sha256', 'files_sha256'})
    if any(value is None for value in policy['anchor'].values()):
        raise _Rejected('EXISTING_ANCHOR_REQUIRED', 'BLOCKED')
    _sha(policy['anchor']['commit_sha'], 40)
    _sha(policy['anchor']['root_event_sha256']); _sha(policy['anchor']['files_sha256'])
    for key, hashes in (('compatible_code_sha256', True), ('required_gate_ids', False)):
        values = _array(policy[key], True)
        for value in values:
            (_sha if hashes else _text)(value)
        if len(set(values)) != len(values):
            raise _Rejected('DUPLICATE_POLICY_REQUIREMENT')
    return _digest(policy, budget)


def _manifest_code(rows, budget):
    result = {}
    for row in _array(rows, True):
        budget.check(); _fields(row, {'path', 'sha256'})
        path = _path(row['path'])
        if path in result:
            raise _Rejected('DUPLICATE_CODE_PATH')
        result[path] = _sha(row['sha256'])
    # Existing codex-cycle/production_verification convention, not a new digest.
    return _digest(result, budget)


def _document(item, budget):
    _fields(item, CORE_DOCUMENT_FIELDS)
    _path(item['path']); _sha(item['sha256'])
    if type(item['size_bytes']) is not int or item['size_bytes'] <= 0:
        raise _Rejected('DOCUMENT_SIZE_REQUIRED')
    if type(item['content_utf8']) is not str:
        raise _Rejected('DOCUMENT_UTF8_REQUIRED')
    raw = item['content_utf8'].encode('utf-8')
    if len(raw) != item['size_bytes'] or _hash(raw, budget) != item['sha256']:
        raise _Rejected('DOCUMENT_BYTES_MISMATCH')
    def unique(pairs):
        value = {}
        for key, child in pairs:
            if key in value:
                raise _Rejected('DUPLICATE_JSON_KEY')
            value[key] = child
        return value
    try:
        value = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(_Rejected('NONFINITE_JSON_NUMBER')))
    except (ValueError, UnicodeError, RecursionError):
        raise _Rejected('INVALID_DOCUMENT_JSON') from None
    value = _owned(value, budget)
    if _encode(value, budget, True) != raw:
        raise _Rejected('CANONICAL_DOCUMENT_REQUIRED')
    return value


def _make_document(path, value, budget):
    _path(path)
    raw = _encode(value, budget, True)
    if len(raw) > MAX_STRING_BYTES:
        raise _Rejected('DOCUMENT_CAPACITY_EXCEEDED', 'BLOCKED')
    return dict(path=path, sha256=_hash(raw, budget), size_bytes=len(raw), content_utf8=raw.decode('utf-8'))


def _reviewed(ref, policy):
    _required(ref, {'commit_sha', 'path', 'sha256'})
    _sha(ref['commit_sha'], 40); _sha(ref['sha256'])
    if not _inside(_path(ref['path']), policy['intent_prefix']) or not ref['path'].endswith('.json'):
        raise _Rejected('REVIEWED_INTENT_SCOPE')


def _merged(ref):
    _required(ref, {'commit_sha', 'tree_sha', 'facts_sha256', 'merged_at'})
    _sha(ref['commit_sha'], 40); _sha(ref['tree_sha'], 40); _sha(ref['facts_sha256'])
    return _stamp(ref['merged_at'])


def _intent(envelope, gate, policy, policy_sha, budget):
    _required(envelope, {'document', 'reviewed_ref', 'merged_ref'})
    document = envelope['document']; _required(document, CORE_INTENT_FIELDS)
    if document['schema_version'] != 'habu-registry-intent-v1':
        raise _Rejected('CORE_INTENT_SCHEMA')
    _repository(document['repository'])
    if (document['repository'] != policy['repository'] or document['task_id'] != policy['task_id']
            or document['policy_sha256'] != policy_sha):
        raise _Rejected('INTENT_POLICY_IDENTITY')
    _text(document['operation_id'])
    if document['operation'] not in ('PROMOTE', 'ROLLBACK'):
        raise _Rejected('INTENT_OPERATION')
    for key in ('expected_previous_event_sha256','model_sha256','code_sha256',
                'protocol_sha256','evidence_sha256','policy_sha256'):
        _sha(document[key])
    if _manifest_code(document['code_manifest'], budget) != document['code_sha256']:
        raise _Rejected('CODE_CLOSURE_MISMATCH')
    _reviewed(envelope['reviewed_ref'], policy)
    intent_sha = _digest(document, budget, True)
    if envelope['reviewed_ref']['sha256'] != intent_sha:
        raise _Rejected('REVIEWED_INTENT_BYTES_MISMATCH')
    merged_at = _merged(envelope['merged_ref'])
    _required(gate, {'schema_version','intent_sha256','evidence_sha256','policy_sha256',
                     'reproduction_sha256','evaluated_at','gates'})
    if gate['schema_version'] != 'habu-registry-gate-decision-v1':
        raise _Rejected('GATE_SCHEMA')
    for key in ('intent_sha256','evidence_sha256','policy_sha256','reproduction_sha256'):
        _sha(gate[key])
    if (gate['intent_sha256'] != intent_sha or gate['evidence_sha256'] != document['evidence_sha256']
            or gate['policy_sha256'] != policy_sha):
        raise _Rejected('GATE_BINDING_MISMATCH')
    statuses = {}
    for row in _array(gate['gates']):
        budget.check(); _fields(row, {'gate_id','status'}); _text(row['gate_id'])
        if row['gate_id'] in statuses or row['gate_id'] not in policy['required_gate_ids']:
            raise _Rejected('GATE_SET_CONTRADICTION')
        if row['status'] not in ('PASS','FAIL','BLOCKED','NOT_VALIDATED'):
            raise _Rejected('GATE_STATUS')
        statuses[row['gate_id']] = row['status']
    if set(statuses) != set(policy['required_gate_ids']):
        raise _Rejected('REQUIRED_GATE_MISSING', 'BLOCKED')
    if 'FAIL' in statuses.values():
        raise _Rejected('REQUIRED_GATE_FAILED')
    if any(status != 'PASS' for status in statuses.values()):
        raise _Rejected('REQUIRED_GATE_NOT_VALIDATED', 'BLOCKED')
    evaluated = _stamp(gate['evaluated_at'])
    return document, intent_sha, merged_at, evaluated


def _activation_event(envelope, gate, policy, policy_sha, when, budget):
    document, intent_sha, merged, evaluated = _intent(envelope, gate, policy, policy_sha, budget)
    if _stamp(when) < max(merged, evaluated):
        raise _Rejected('ACTIVATION_BACKDATED')
    body = dict(schema_version='habu-registry-activation-v1',
        operation_id=document['operation_id'], operation=document['operation'],
        previous_event_sha256=document['expected_previous_event_sha256'],
        **{key:document[key] for key in ('model_sha256','code_sha256','code_manifest',
            'protocol_sha256','policy_sha256','evidence_sha256')},
        intent_sha256=intent_sha, gate_decision_sha256=_digest(gate, budget),
        reviewed_ref=envelope['reviewed_ref'], merged_ref=envelope['merged_ref'], observed_at=when)
    return dict(body, event_sha256=_digest(body, budget))


def _event(value, policy, budget):
    _fields(value, CORE_EVENT_FIELDS)
    if value['schema_version'] != 'habu-registry-activation-v1':
        raise _Rejected('ACTIVATION_SCHEMA')
    if value['previous_event_sha256'] is None:
        raise _Rejected('GENESIS_ANCHOR_UNSUPPORTED', 'BLOCKED')
    for key in ('previous_event_sha256','model_sha256','code_sha256','protocol_sha256',
                'policy_sha256','evidence_sha256','intent_sha256','gate_decision_sha256','event_sha256'):
        _sha(value[key])
    _text(value['operation_id'])
    if value['operation'] not in ('PROMOTE','ROLLBACK'):
        raise _Rejected('ACTIVATION_OPERATION')
    if _manifest_code(value['code_manifest'], budget) != value['code_sha256']:
        raise _Rejected('CODE_CLOSURE_MISMATCH')
    _reviewed(value['reviewed_ref'], policy)
    if value['reviewed_ref']['sha256'] != value['intent_sha256']:
        raise _Rejected('EVENT_INTENT_BINDING')
    if _merged(value['merged_ref']) > _stamp(value['observed_at']):
        raise _Rejected('ACTIVATION_BACKDATED')
    if _digest({k:v for k,v in value.items() if k != 'event_sha256'}, budget) != value['event_sha256']:
        raise _Rejected('EVENT_HASH_MISMATCH')


def _inference(record, observed_at, budget):
    _required(record, CORE_INFERENCE_FIELDS)
    if record['schema_version'] != 'habu-registry-inference-v1':
        raise _Rejected('INFERENCE_SCHEMA')
    _text(record['operation_id']); night = _night(record['operational_night'])
    observed = _stamp(observed_at)
    if _operational_night(observed) > night:
        raise _Rejected('HISTORICAL_ISSUANCE_FORBIDDEN')
    cutoff = _stamp(record['cutoff_time'])
    if cutoff > observed or _stamp(record['training_cutoff']) >= cutoff:
        raise _Rejected('INFERENCE_CUTOFF_ORDER')
    windows = _array(record['forecast_windows'], True)
    normalized = set()
    for start in windows:
        budget.check()
        when = _stamp(start); local = when.astimezone(_JST)
        if (when <= observed or _operational_night(when) != night or local.minute % 10
                or local.second or local.microsecond or when in normalized):
            raise _Rejected('NONPROSPECTIVE_OR_UNALIGNED_WINDOW')
        normalized.add(when)
    for key in ('selected_event_sha256','model_sha256','code_sha256',
                'input_bundle_sha256','component_receipts_sha256'):
        _sha(record[key])
    if type(record['output']) is not dict or not record['output']:
        raise _Rejected('INFERENCE_OUTPUT_REQUIRED')


def _version(value):
    if type(value) is not str or re.fullmatch(r'P(0|[1-9][0-9]{0,6})', value) is None:
        raise _Rejected('VERSION_REQUIRED')
    return int(value[1:])


def _state(files, values, policy, policy_sha, proofs, budget):
    pointer_path, index_path = policy['pointer_path'], policy['version_index_path']
    if pointer_path not in values or index_path not in values:
        raise _Rejected('POINTER_OR_VERSION_PROOF_MISSING', 'BLOCKED')
    pointer = values[pointer_path]; _required(pointer, {'schema_version','event_sha256'})
    if pointer['schema_version'] != 'habu-registry-pointer-v1':
        raise _Rejected('POINTER_SCHEMA')
    _sha(pointer['event_sha256'])
    index = values[index_path]; _required(index, {'schema_version','nights'})
    if index['schema_version'] != 'habu-registry-version-index-v1':
        raise _Rejected('VERSION_INDEX_SCHEMA')
    events = {}
    for path, value in values.items():
        budget.check()
        if _inside(path, policy['event_directory']):
            _event(value, policy, budget)
            key = value['event_sha256']
            if path != policy['event_directory']+'/'+key+'.json' or key in events:
                raise _Rejected('EVENT_PATH_OR_DUPLICATE')
            events[key] = value
    root = policy['anchor']['root_event_sha256']; tip = pointer['event_sha256']
    chain = []; seen = set()
    while True:
        budget.check()
        if tip in seen:
            raise _Rejected('EVENT_CHAIN_CYCLE')
        if tip not in events:
            raise _Rejected('EVENT_CHAIN_PROOF_MISSING', 'BLOCKED')
        seen.add(tip); chain.append(events[tip])
        if tip == root:
            break
        tip = events[tip]['previous_event_sha256']
    if set(events) != seen:
        raise _Rejected('ORPHAN_EVENT_RECORD')
    chain.reverse()
    activated = set(); operations = set(); models = {}; latest = _stamp(chain[0]['observed_at'])
    for position, event in enumerate(chain):
        if event['operation_id'] in operations:
            raise _Rejected('DUPLICATE_OPERATION')
        operations.add(event['operation_id'])
        if _stamp(event['observed_at']) < latest:
            raise _Rejected('EVENT_TIME_REVERSED')
        latest = _stamp(event['observed_at'])
        pair = (event['model_sha256'], event['code_sha256'])
        binding = (event['code_sha256'],event['protocol_sha256'])
        if event['model_sha256'] in models and models[event['model_sha256']] != binding:
            raise _Rejected('MODEL_METADATA_REBOUND')
        models[event['model_sha256']] = binding
        if position:
            if event['intent_sha256'] not in proofs:
                raise _Rejected('TRANSITION_PROOF_MISSING', 'BLOCKED')
            proof = proofs[event['intent_sha256']]
            expected = _activation_event(proof['intent'], proof['gate_decision'], policy,
                                         policy_sha, event['observed_at'], budget)
            if _encode(expected, budget) != _encode(event, budget):
                raise _Rejected('TRANSITION_PROOF_CONTRADICTION')
            if event['code_sha256'] not in policy['compatible_code_sha256']:
                raise _Rejected('CODE_COMPATIBILITY_NOT_ESTABLISHED', 'BLOCKED')
            if event['operation'] == 'ROLLBACK' and pair not in activated:
                raise _Rejected('ROLLBACK_NOT_PREVIOUSLY_ACTIVATED', 'BLOCKED')
        activated.add(pair)
    expected_paths = {pointer_path,index_path} | {
        policy['event_directory']+'/'+sha+'.json' for sha in events}
    issuances = {}; derived_nights = {}
    for path, record in values.items():
        budget.check()
        if not _inside(path, policy['issuance_directory']) or not path.endswith('/record.json'):
            continue
        _required(record, CORE_ISSUANCE_FIELDS)
        native = {k:v for k,v in record.items() if k in CORE_INFERENCE_FIELDS}
        ref = record['output_ref']; _fields(ref, {'path','sha256','size_bytes'})
        output_path = _path(ref['path']); _sha(ref['sha256'])
        if type(ref['size_bytes']) is not int or ref['size_bytes'] <= 0:
            raise _Rejected('DOCUMENT_SIZE_REQUIRED')
        if output_path not in values:
            raise _Rejected('ISSUANCE_OUTPUT_MISSING', 'BLOCKED')
        if any(ref[k] != files[output_path][k] for k in ('path','sha256','size_bytes')):
            raise _Rejected('ISSUANCE_OUTPUT_BINDING')
        native['output'] = values[output_path]
        _inference(native, record['observed_at'], budget)
        version = _version(record['version']); night = record['operational_night']
        prefix = policy['issuance_directory']+'/'+night+'/'+record['version']+'/'
        if path != prefix+'record.json' or output_path != prefix+'output.json':
            raise _Rejected('ISSUANCE_PATH_BINDING')
        selected = events.get(record['selected_event_sha256'])
        if selected is None:
            raise _Rejected('ISSUANCE_EVENT_MISSING', 'BLOCKED')
        if (record['model_sha256'] != selected['model_sha256'] or record['code_sha256'] != selected['code_sha256']
                or _stamp(record['observed_at']) < _stamp(selected['observed_at'])):
            raise _Rejected('ISSUANCE_SELECTION_BINDING')
        if record['operation_id'] in operations:
            raise _Rejected('DUPLICATE_OPERATION')
        operations.add(record['operation_id'])
        latest = max(latest, _stamp(record['observed_at']))
        issuances[path] = record
        derived_nights.setdefault(night, []).append((version, files[path]['sha256']))
        expected_paths.update((path,output_path))
    if set(files) != expected_paths:
        raise _Rejected('FOREIGN_OR_ORPHAN_REGISTRY_FILE')
    expected_nights = []
    for night in sorted(derived_nights):
        records = sorted(derived_nights[night])
        if [number for number,_ in records] != list(range(len(records))):
            raise _Rejected('NONCONTIGUOUS_VERSION_HISTORY')
        expected_nights.append(dict(operational_night=night,
            issuances=[dict(version='P'+str(number), record_sha256=sha) for number,sha in records]))
    if _encode(index['nights'], budget) != _encode(expected_nights, budget):
        raise _Rejected('VERSION_INDEX_CONTRADICTION')
    return dict(pointer=pointer, index=index, events=events, chain=chain, activated=activated,
                operations=operations, latest=latest, issuances=issuances, files=files, values=values,
                proofs=proofs)


def _transition(prior, state, policy):
    files = state['files']
    deleted = set(prior['files'])-set(files)
    added = set(files)-set(prior['files'])
    changed = {p for p in set(files)&set(prior['files']) if files[p]['sha256'] != prior['files'][p]['sha256']}
    if deleted or changed-{policy['pointer_path'],policy['version_index_path']}:
        raise _Rejected('IMMUTABLE_HISTORY_MUTATED')
    new_events = set(state['events'])-set(prior['events'])
    new_issues = set(state['issuances'])-set(prior['issuances'])
    if len(new_events)==1 and not new_issues and changed=={policy['pointer_path']}:
        event_sha = next(iter(new_events)); event = state['events'][event_sha]
        if (added != {policy['event_directory']+'/'+event_sha+'.json'}
                or state['pointer']['event_sha256'] != event_sha
                or event['previous_event_sha256'] != prior['pointer']['event_sha256']
                or _stamp(event['observed_at']) < prior['latest']):
            raise _Rejected('ACTIVATION_DELTA_CONTRADICTION')
        return 'ACTIVATE'
    if len(new_issues)==1 and not new_events and changed=={policy['version_index_path']}:
        record_path = next(iter(new_issues)); record = state['issuances'][record_path]
        if (added != {record_path,record['output_ref']['path']}
                or record['selected_event_sha256'] != prior['pointer']['event_sha256']
                or _stamp(record['observed_at']) < prior['latest']):
            raise _Rejected('ISSUANCE_DELTA_CONTRADICTION')
        return 'ISSUE'
    raise _Rejected('ONE_STATE_TRANSITION_PER_COMMIT_REQUIRED')


def _evidence_before_creation(event, nonprior_commits):
    # These commits are asserted to be prior review/merge evidence. They cannot
    # be the event's own containing commit or a supplied later descendant.
    if any(event[role]['commit_sha'] in nonprior_commits
           for role in ('reviewed_ref','merged_ref')):
        raise _Rejected('EVENT_PRIOR_COMMIT_CONTRADICTION')


def _snapshot(snapshot, policy, policy_sha, budget):
    _required(snapshot, {'schema_version','repository','state_ref','history_complete','commits','transition_proofs'})
    if snapshot['schema_version'] != 'habu-registry-core-snapshot-v1':
        raise _Rejected('SNAPSHOT_SCHEMA')
    _repository(snapshot['repository'])
    if snapshot['repository'] != policy['repository'] or snapshot['state_ref'] != policy['state_ref']:
        raise _Rejected('SNAPSHOT_IDENTITY')
    if type(snapshot['history_complete']) is not bool:
        raise _Rejected('HISTORY_COMPLETENESS_BOOLEAN_REQUIRED')
    if not snapshot['history_complete']:
        raise _Rejected('HISTORY_INCOMPLETE', 'BLOCKED')
    commits = _array(snapshot['commits'], True)
    if len(commits) > CORE_MAX_COMMITS:
        raise _Rejected('HISTORY_CAPACITY_EXCEEDED', 'BLOCKED')
    proofs = {}
    for proof in _array(snapshot['transition_proofs']):
        _fields(proof, {'intent','gate_decision'})
        _, sha, _, _ = _intent(proof['intent'], proof['gate_decision'], policy, policy_sha, budget)
        if sha in proofs:
            raise _Rejected('DUPLICATE_TRANSITION_PROOF')
        proofs[sha] = proof
    states = []; seen = set()
    for position, commit in enumerate(commits):
        budget.check(); _required(commit, {'commit_sha','parents','files'})
        sha = _sha(commit['commit_sha'],40)
        parents = [_sha(parent,40) for parent in _array(commit['parents'], True)]
        if sha in seen or sha in parents or len(set(parents)) != len(parents):
            raise _Rejected('COMMIT_ID_OR_CYCLE')
        seen.add(sha)
        if position == 0:
            if sha != policy['anchor']['commit_sha']:
                raise _Rejected('ANCHOR_COMMIT_MISMATCH')
        elif parents != [commits[position-1]['commit_sha']]:
            raise _Rejected('DIRECT_PARENT_HISTORY_REQUIRED')
        rows = _array(commit['files'], True)
        if len(rows) > MAX_FILES:
            raise _Rejected('FILE_CAPACITY_EXCEEDED', 'BLOCKED')
        files = {}; values = {}
        for row in rows:
            value = _document(row, budget); path = row['path']
            if not _inside(path, policy['registry_root']) or path in files:
                raise _Rejected('FILE_SCOPE_OR_DUPLICATE')
            files[path] = row; values[path] = value
        for path in files:
            parts = path.split('/')
            if any('/'.join(parts[:n]) in files for n in range(1,len(parts))):
                raise _Rejected('FILE_DIRECTORY_CONFLICT')
        if position == 0 and _digest({p:d['sha256'] for p,d in files.items()},budget) != policy['anchor']['files_sha256']:
            raise _Rejected('ANCHOR_FILES_MISMATCH')
        if states:
            prior = states[-1]
            deleted = set(prior['files'])-set(files)
            added = set(files)-set(prior['files'])
            changed = {p for p in set(files)&set(prior['files']) if files[p]['sha256'] != prior['files'][p]['sha256']}
            if deleted or changed-{policy['pointer_path'],policy['version_index_path']}:
                raise _Rejected('IMMUTABLE_HISTORY_MUTATED')
        state = _state(files,values,policy,policy_sha,proofs,budget)
        state.update(commit_sha=sha, parents=parents)
        if states:
            _transition(prior,state,policy)
        states.append(state)
    # Every non-anchor commit already has exactly its preceding supplied commit
    # as parent. An anchor parent pointing anywhere into this suffix therefore
    # closes a cycle. Unknown pre-anchor parents are deliberately not invented.
    if any(parent in seen for parent in states[0]['parents']):
        raise _Rejected('SUPPLIED_COMMIT_CHAIN_CYCLE')
    prior_commits = set(); introduced_events = set()
    for state in states:
        budget.check()
        for event_sha in set(state['events'])-introduced_events:
            _evidence_before_creation(state['events'][event_sha],seen-prior_commits)
            introduced_events.add(event_sha)
        prior_commits.add(state['commit_sha'])
    used = {event['intent_sha256'] for event in states[-1]['chain'][1:]}
    if set(proofs) != used:
        raise _Rejected('FOREIGN_TRANSITION_PROOF')
    return states


def _computed(state):
    return dict(tip_commit_sha=state['commit_sha'], current_event_sha256=state['pointer']['event_sha256'],
        activated_model_count=len(state['activated']), issuance_count=len(state['issuances']),
        scoped_file_count=len(state['files']))


def _entry(arguments, seconds, operation):
    try:
        budget = _Budget(seconds)
        values = _owned(arguments, budget)
        policy_sha = _core_policy(values['policy'], budget)
        result = operation(values, policy_sha, budget)
        budget.check()
        return result
    except _Rejected as exc:
        return _core_result(exc.status, exc.code)
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError, UnicodeError):
        return _core_result('FAIL', 'MALFORMED_CORE_FACT')


def validate_registry_snapshot(snapshot, *, policy, budget_seconds=30):
    """Check a fully supplied anchored suffix, not global history/authenticity.

    No genesis is constructed. A supplied genesis anchor is v1-unsupported.
    Full per-commit scoped inventories and canonical bytes are mandatory; the
    unchanged 4MiB/100k-node/24-depth/64KiB-string limits include repetition,
    and history additionally has a128-commit bound. Incomplete/over-capacity
    inputs block. Anchor/policy/completeness are declarations, not trust roots.
    """
    def run(v, sha, budget):
        state = _snapshot(v['snapshot'],v['policy'],sha,budget)[-1]
        return _core_result('CONSISTENT_NOT_AUTHENTICATED',computed=_computed(state))
    return _entry(dict(snapshot=snapshot,policy=policy),budget_seconds,run)


def _expected(state, ref_sha, event_sha):
    if ref_sha is None or event_sha is None:
        raise _Rejected('EXPECTED_STATE_MISSING','BLOCKED')
    if (_sha(ref_sha,40) != state['commit_sha']
            or _sha(event_sha) != state['pointer']['event_sha256']):
        raise _Rejected('EXPECTED_STATE_CONFLICT','CONFLICT')


def _proposal(state, policy, policy_sha, operation_id, kind, additions, updates, budget, computed, proof=None):
    for document in additions:
        path = document['path']
        if path in state['files']:
            raise _Rejected('IMMUTABLE_ADDITION_ALREADY_EXISTS','CONFLICT')
        document['expected_absent'] = True
    for document in updates:
        document['expected_file_sha256'] = state['files'][document['path']]['sha256']
    spec = dict(parents=[state['commit_sha']],immutable_additions=additions,updates=updates)
    pending = dict(schema_version='habu-registry-pending-v1',state_ref=policy['state_ref'],
        policy_sha256=policy_sha,parent_sha=state['commit_sha'],
        previous_event_sha256=state['pointer']['event_sha256'],operation_id=operation_id,
        kind=kind,commit_sha=None,spec_sha256=_digest(spec,budget),commit_spec=spec,
        transition_proof=proof)
    return _core_result('ACTIVATION_COMMIT_PROPOSED' if kind=='ACTIVATE' else 'ISSUANCE_COMMIT_PROPOSED',
                        spec=spec,pending=pending,computed=computed)


def prepare_activation_commit(snapshot, intent, gate_decision, *, policy, observed_at,
                              expected_ref_sha, expected_previous_event_sha256, budget_seconds=30):
    """Propose unpublished event/pointer bytes from declared gates, never activate."""
    def run(v, sha, budget):
        p=v['policy']; state=_snapshot(v['snapshot'],p,sha,budget)[-1]
        _expected(state,v['expected_ref_sha'],v['expected_previous_event_sha256'])
        event=_activation_event(v['intent'],v['gate'],p,sha,v['observed_at'],budget)
        if event['previous_event_sha256'] != state['pointer']['event_sha256']:
            raise _Rejected('INTENT_PREDECESSOR_CONFLICT','CONFLICT')
        if event['operation_id'] in state['operations']:
            raise _Rejected('OPERATION_ALREADY_RECORDED','BLOCKED')
        if any(prior['model_sha256']==event['model_sha256'] and
               (prior['code_sha256'],prior['protocol_sha256'])!=(event['code_sha256'],event['protocol_sha256'])
               for prior in state['chain']):
            raise _Rejected('MODEL_METADATA_REBOUND')
        if _stamp(v['observed_at']) < state['latest']:
            raise _Rejected('ACTIVATION_BACKDATED')
        if event['code_sha256'] not in p['compatible_code_sha256']:
            raise _Rejected('CODE_COMPATIBILITY_NOT_ESTABLISHED','BLOCKED')
        if event['operation']=='ROLLBACK' and (event['model_sha256'],event['code_sha256']) not in state['activated']:
            raise _Rejected('ROLLBACK_NOT_PREVIOUSLY_ACTIVATED','BLOCKED')
        addition=_make_document(p['event_directory']+'/'+event['event_sha256']+'.json',event,budget)
        pointer=_make_document(p['pointer_path'],dict(schema_version='habu-registry-pointer-v1',
                               event_sha256=event['event_sha256']),budget)
        return _proposal(state,p,sha,event['operation_id'],'ACTIVATE',[addition],[pointer],budget,
                         dict(next_event_sha256=event['event_sha256']),
                         proof=dict(intent=v['intent'],gate_decision=v['gate']))
    return _entry(dict(snapshot=snapshot,intent=intent,gate=gate_decision,policy=policy,
        observed_at=observed_at,expected_ref_sha=expected_ref_sha,
        expected_previous_event_sha256=expected_previous_event_sha256),budget_seconds,run)


def prepare_issuance_commit(snapshot, inference_record, *, policy, observed_at,
                            expected_ref_sha, expected_event_sha256, budget_seconds=30):
    """Propose immutable inference/version bytes; supplied inference is not attested."""
    def run(v, sha, budget):
        p=v['policy']; state=_snapshot(v['snapshot'],p,sha,budget)[-1]
        _expected(state,v['expected_ref_sha'],v['expected_event_sha256'])
        native=v['inference'];_inference(native,v['observed_at'],budget)
        event=state['events'][state['pointer']['event_sha256']]
        if (native['selected_event_sha256'] != event['event_sha256'] or native['model_sha256'] != event['model_sha256']
                or native['code_sha256'] != event['code_sha256']):
            raise _Rejected('INFERENCE_SELECTION_MISMATCH')
        if event['code_sha256'] not in p['compatible_code_sha256']:
            raise _Rejected('CODE_COMPATIBILITY_NOT_ESTABLISHED','BLOCKED')
        if _stamp(v['observed_at']) < state['latest']:
            raise _Rejected('ISSUANCE_BACKDATED')
        if native['operation_id'] in state['operations']:
            raise _Rejected('OPERATION_ALREADY_RECORDED','BLOCKED')
        night=native['operational_night']
        versions=[r for r in state['issuances'].values() if r['operational_night']==night]
        version='P'+str(len(versions));prefix=p['issuance_directory']+'/'+night+'/'+version+'/'
        output=_make_document(prefix+'output.json',native['output'],budget)
        record={k:value for k,value in native.items() if k!='output'}
        record.update(version=version,observed_at=v['observed_at'],
                      output_ref={k:output[k] for k in ('path','sha256','size_bytes')})
        document=_make_document(prefix+'record.json',record,budget)
        index=state['index'];row=next((r for r in index['nights'] if r['operational_night']==night),None)
        if row is None:
            row=dict(operational_night=night,issuances=[]);index['nights'].append(row)
        row['issuances'].append(dict(version=version,record_sha256=document['sha256']))
        index['nights'].sort(key=lambda r:r['operational_night'])
        update=_make_document(p['version_index_path'],index,budget)
        return _proposal(state,p,sha,native['operation_id'],'ISSUE',[document,output],[update],budget,
                         dict(version=version,output_sha256=output['sha256']))
    return _entry(dict(snapshot=snapshot,inference=inference_record,policy=policy,observed_at=observed_at,
        expected_ref_sha=expected_ref_sha,expected_event_sha256=expected_event_sha256),budget_seconds,run)


def _pending(value, policy, policy_sha, budget):
    _required(value, {'schema_version','state_ref','policy_sha256','parent_sha',
        'previous_event_sha256','operation_id','kind','commit_sha','spec_sha256','commit_spec','transition_proof'})
    if (value['schema_version'] != 'habu-registry-pending-v1' or value['state_ref'] != policy['state_ref']
            or value['policy_sha256'] != policy_sha):
        raise _Rejected('PENDING_IDENTITY')
    _sha(value['parent_sha'],40);_sha(value['previous_event_sha256']);_text(value['operation_id'])
    if value['commit_sha'] is not None:_sha(value['commit_sha'],40)
    if value['commit_sha'] == value['parent_sha']:
        raise _Rejected('PENDING_SELF_PARENT')
    if value['kind'] not in ('ACTIVATE','ISSUE'):
        raise _Rejected('PENDING_KIND')
    spec=value['commit_spec'];_fields(spec,{'parents','immutable_additions','updates'})
    if spec['parents'] != [value['parent_sha']]:
        raise _Rejected('PENDING_SOLE_PARENT_REQUIRED')
    if _sha(value['spec_sha256']) != _digest(spec,budget):
        raise _Rejected('PENDING_SPEC_HASH_MISMATCH')
    documents={}; parsed={}
    for field in ('immutable_additions','updates'):
        for item in _array(spec[field],True):
            flag='expected_absent' if field=='immutable_additions' else 'expected_file_sha256'
            _fields(item,CORE_DOCUMENT_FIELDS|{flag})
            if flag=='expected_absent':
                if item[flag] is not True:raise _Rejected('IMMUTABLE_ABSENCE_PRECONDITION_REQUIRED')
            else:_sha(item[flag])
            document={k:item[k] for k in CORE_DOCUMENT_FIELDS};data=_document(document,budget)
            if item['path'] in documents or not _inside(item['path'],policy['registry_root']):
                raise _Rejected('PENDING_DOCUMENT_SCOPE')
            documents[item['path']]=item;parsed[item['path']]=data
    records=[d for path,d in parsed.items() if path.endswith('/record.json') or _inside(path,policy['event_directory'])]
    if (len(records)!=1 or type(records[0]) is not dict
            or records[0].get('operation_id') != value['operation_id']):
        raise _Rejected('PENDING_OPERATION_BINDING')
    if value['kind']=='ACTIVATE':
        if len(spec['immutable_additions'])!=1 or len(spec['updates'])!=1:
            raise _Rejected('PENDING_ACTIVATION_SHAPE')
        proof=value['transition_proof'];_required(proof,{'intent','gate_decision'})
        event=records[0];_event(event,policy,budget)
        expected=_activation_event(proof['intent'],proof['gate_decision'],policy,policy_sha,event['observed_at'],budget)
        if (_encode(expected,budget)!=_encode(event,budget)
                or event['previous_event_sha256']!=value['previous_event_sha256']
                or spec['immutable_additions'][0]['path']!=policy['event_directory']+'/'+event['event_sha256']+'.json'
                or spec['updates'][0]['path']!=policy['pointer_path']
                or parsed[policy['pointer_path']]!=dict(schema_version='habu-registry-pointer-v1',event_sha256=event['event_sha256'])):
            raise _Rejected('PENDING_ACTIVATION_BINDING')
        if value['commit_sha'] is not None:
            _evidence_before_creation(event,{value['commit_sha']})
    else:
        if (value['transition_proof'] is not None or len(spec['immutable_additions'])!=2
                or len(spec['updates'])!=1 or spec['updates'][0]['path']!=policy['version_index_path']):
            raise _Rejected('PENDING_ISSUANCE_SHAPE')
        record=records[0];_fields(record,CORE_ISSUANCE_FIELDS)
        output=record['output_ref'];_fields(output,{'path','sha256','size_bytes'})
        if output['path'] not in parsed:
            raise _Rejected('PENDING_OUTPUT_BINDING')
        native={k:v for k,v in record.items() if k in CORE_INFERENCE_FIELDS}
        native['output']=parsed[output['path']]
        _inference(native,record['observed_at'],budget)
        prefix=policy['issuance_directory']+'/'+record['operational_night']+'/'+record['version']+'/'
        _version(record['version'])
        if (record['selected_event_sha256']!=value['previous_event_sha256']
                or {d['path'] for d in spec['immutable_additions']}!={prefix+'record.json',prefix+'output.json'}
                or output['path']!=prefix+'output.json'):
            raise _Rejected('PENDING_ISSUANCE_BINDING')
    return spec,documents


def reconcile_publication(pending, observed_history, *, policy, budget_seconds=30):
    """Byte/parent reconciliation only. ACK_ONLY is never production authentication.

    Unknown ACKs retain the original pending descriptor; do not rebase, allocate
    a new version, rerun inference or regenerate an event with a new timestamp.
    """
    def run(v,sha,budget):
        p=v['policy'];item=v['pending'];spec,documents=_pending(item,p,sha,budget)
        try:states=_snapshot(v['history'],p,sha,budget)
        except _Rejected as exc:
            if exc.status=='BLOCKED':return _core_result('ACK_UNKNOWN',exc.code,pending=item)
            raise
        at=next((n for n,s in enumerate(states) if s['commit_sha']==item['parent_sha']),None)
        if at is None:return _core_result('ACK_UNKNOWN','PENDING_PARENT_NOT_OBSERVED',pending=item)
        parent=states[at]
        if parent['pointer']['event_sha256'] != item['previous_event_sha256']:
            raise _Rejected('PENDING_PREDECESSOR_BINDING')
        for update in spec['updates']:
            if (update['path'] not in parent['files'] or parent['files'][update['path']]['sha256']
                    != update['expected_file_sha256']):
                raise _Rejected('PENDING_UPDATE_PRECONDITION')
        if any(d['path'] in parent['files'] for d in spec['immutable_additions']):
            raise _Rejected('PENDING_ADDITION_PRECONDITION')
        desired_files=dict(parent['files']);desired_values=dict(parent['values']);proofs=dict(parent['proofs'])
        for path,document in documents.items():
            desired_files[path]={k:document[k] for k in CORE_DOCUMENT_FIELDS}
            desired_values[path]=_document(desired_files[path],budget)
        if item['transition_proof'] is not None:
            proof=item['transition_proof'];proofs[proof['intent']['reviewed_ref']['sha256']]=proof
        desired=_state(desired_files,desired_values,p,sha,proofs,budget)
        if _transition(parent,desired,p)!=item['kind']:
            raise _Rejected('PENDING_TRANSITION_KIND')
        if at+1==len(states):return _core_result('ACK_UNKNOWN','NO_OBSERVED_CHILD',pending=item)
        child=states[at+1]
        changes={path for path in set(parent['files'])|set(child['files'])
                 if parent['files'].get(path,{}).get('sha256')!=child['files'].get(path,{}).get('sha256')}
        match=(set(documents)==changes and all(path in child['files'] and
            all(child['files'][path][k]==document[k] for k in CORE_DOCUMENT_FIELDS)
            for path,document in documents.items()))
        if not match or item['commit_sha'] is not None and item['commit_sha']!=child['commit_sha']:
            return _core_result('CONFLICT','DIFFERENT_DIRECT_CHILD',pending=item)
        acknowledged=dict(item,commit_sha=child['commit_sha'])
        return _core_result('ACK_ONLY',pending=acknowledged,
            computed=dict(observed_commit_sha=child['commit_sha'],observed_tip_sha=states[-1]['commit_sha']))
    return _entry(dict(pending=pending,history=observed_history,policy=policy),budget_seconds,run)
