"""Pure, unsubmitted transition proposals under the existing Task8 design.

Supplied JSON can establish consistency only. Nothing here authenticates a
review, source, clock or model; creates an ActivationEvent/active pointer; or
selects a registry ref, transport, production context or publication authority.
"""
from __future__ import annotations

import hashlib
import math
import re
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
