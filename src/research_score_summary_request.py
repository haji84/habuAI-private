"""Explicit no-fit diagnostic request and buffered stdout caller.

No master/PDCA/backend dispatch, native prediction, issuer or P0 permission.
Original child receipts retain their own phase counters and complete hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import g0_forecast_contract as g0
import prospective_inputs as pi
import research_candidate_config_source as source
from evaluation import full_ledger_stage1 as pure
from evaluation import stage1_score_summary_transport_v2 as bridge

REQUEST_PATH = 'config/research-score-summary-request.json'
REQUEST_VERSION = 'habu-research-score-summary-request-v1'
COMMAND_VERSION = 'habu-research-score-summary-command-v1'
MAX_REQUEST_BYTES = 64 * 1024
REQUEST_FIELDS = ('schema_version', 'mode', 'operational_night', 'forecast_as_of',
    'feature_definition_sha256', 'candidate_config_sha256', 'summary_manifest', 'stage1_manifest')


class _Guard:
    __slots__ = ('context', 'first')

    def __init__(self, context):
        self.context, self.first = context, None

    def __call__(self):
        if self.first is not None:
            raise self.first
        try:
            self.context.check()
        except BaseException as error:
            self.first = error
            raise


def _pure(guard, function, *args):
    # Only locally invoked, owned pure JSON capacity sites are normalized.
    try:
        return function(*args, guard)
    except (pure.Stage1CapacityBlocked, pure.Stage1BudgetBlocked) as error:
        if guard.first is not None:
            raise guard.first
        if isinstance(error, pure.Stage1CapacityBlocked):
            raise pi.InputCapacityError(str(error)) from error
        raise TimeoutError(str(error)) from error


def _bound(value, guard):
    return _pure(guard, pure._summary_bound, value)


def _copy(value, guard):
    return _pure(guard, pure._summary_copy, value)


def _digest(value, guard):
    return _pure(guard, pure._digest, value)


def _context(context):
    if not isinstance(context, pi.ProspectiveReadContext):
        raise ValueError('Actual existing prospective context required')
    if (type(context.bytes_read) is not int or context.bytes_read < 0 or
            type(context.max_bytes) is not int or not 0 < context.max_bytes <= g0.MAX_TOTAL_READ_BYTES):
        raise ValueError('Bounded nonnegative actual context required')
    initial = context.bytes_read  # Before the first actual caller check.
    guard = _Guard(context)
    guard()
    if context.bytes_read >= context.max_bytes:
        raise pi.InputCapacityError('CAPACITY_BLOCKED: request allowance exhausted')
    if not 0 < context.remaining_seconds <= 300:
        raise ValueError('Actual remaining deadline must be positive and at most300s')
    return initial, guard


def _decode(raw, guard):
    text = raw.decode('utf-8')
    # Bound decoder recursion before allocating an additional owned JSON tree.
    depth, quoted, escaped = 0, False, False
    for char in text:
        guard()
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '{[':
            depth += 1
            if depth > 12:
                raise pi.InputCapacityError('CAPACITY_BLOCKED: request JSON depth')
        elif char in '}]':
            depth -= 1
    def nonfinite(_):
        raise ValueError('Nonfinite request JSON')
    value = json.loads(text, object_pairs_hook=lambda pairs: pi._unique_json_object(pairs, guard),
                       parse_constant=nonfinite)
    _bound(value, guard)
    return value


def _request(root, night, context, guard):
    pure._night(night)
    target = pi._local_path(root, REQUEST_PATH, guard)
    raw = pi._bounded_bytes(target, pi._LocalByteBudget(context, MAX_REQUEST_BYTES), guard)
    value = _decode(raw, guard)
    pure._fields(value, REQUEST_FIELDS)
    if (value['schema_version'] != REQUEST_VERSION or value['mode'] != 'DEVELOPMENT_ONLY' or
            value['operational_night'] != night):
        raise ValueError('Explicit diagnostic request version/mode/night required')
    pure._night(value['operational_night'])
    pure._time(value['forecast_as_of'])
    pure._sha(value['feature_definition_sha256'])
    pure._sha(value['candidate_config_sha256'])
    bridge._shape_ref(value['summary_manifest'])
    source.input_ref(value['summary_manifest'])
    bridge._shape_ref(value['stage1_manifest'])
    bridge.old.input_ref(value['stage1_manifest'])
    ref = dict(path=REQUEST_PATH, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    _bound([ref, value], guard)
    return ref, value


def evaluate_research_score_summary_request(root, night, *, context):
    """Owned four-field nonpublication value; exactly one genuine child call."""
    _, guard = _context(context)
    root = Path(root).absolute()
    try:
        ref, request = _request(root, night, context, guard)
        request_sha = _digest(request, guard)
        child = bridge.evaluate_stage1_summary_sources_v2(root,
            request['summary_manifest'], request['stage1_manifest'], night,
            pure._time(request['forecast_as_of']),
            expected_feature_definition_sha256=request['feature_definition_sha256'],
            expected_candidate_config_sha256=request['candidate_config_sha256'], context=context)
        # No child modifications/reseal: retain its original complete execution.
        value = dict(request_ref=ref, request_canonical_sha256=request_sha, request=request, child=child)
        _bound(value, guard)
        value = _copy(value, guard)
        guard()
        return value
    except BaseException:
        if guard.first is not None:
            raise guard.first
        raise


def _recheck(root, value, context, guard):
    child = value['child']
    bridge._sealed(child, 'receipt_sha256', guard)
    first = child['source_admission_receipt']
    execution = child['summary_execution_receipt']
    bridge._sealed(first, 'receipt_sha256', guard)
    bridge._sealed(execution, 'summary_sha256', guard)
    expected = set(first['code_sha256_by_path'])
    if execution['candidate_config_source_receipt']['code_sha256_by_path'] != first['code_sha256_by_path']:
        raise ValueError('Child code identities differ')
    refs = {}
    def add(ref):
        bridge._shape_ref(ref)
        ref = dict(ref)
        if ref['path'] in refs and refs[ref['path']] != ref:
            raise ValueError('Conflicting original final source sizes/hashes')
        refs[ref['path']] = ref
    # A declaration alone is not admission: whole NMD must not open a target
    # that the child did not consume. Actual manifest refs are in its receipts.
    add(value['request_ref'])
    for receipt in (first, execution, child['source_receipt']):
        if receipt is not None:
            for ref in receipt['consumed_refs']:
                guard()
                add(ref)
    _bound([value, refs], guard)
    source._membership(root, expected, guard)
    reader = bridge._Reader(root, context, guard)
    for ref in refs.values():
        guard()
        reader.read(ref, parse=False)
    source._membership(root, expected, guard)
    guard()


def _command(root, night, context):
    initial, guard = _context(context)
    try:
        value = evaluate_research_score_summary_request(root, night, context=context)
        child = value['child']
        child_entry, child_return = child['entry_initial_read_bytes'], child['actual_read_bytes']
        if not initial <= child_entry <= child_return <= context.bytes_read:
            raise ValueError('Command/child actual ledger order mismatch')
        _recheck(Path(root).absolute(), value, context, guard)
        final = context.bytes_read
        result = dict(schema_version=COMMAND_VERSION, purpose='DEVELOPMENT_DIAGNOSTIC_ONLY',
            status=child['status'], operational_night=night, request_ref=value['request_ref'],
            request_canonical_sha256=value['request_canonical_sha256'], child=child,
            child_receipt_sha256=child['receipt_sha256'], entry_initial_read_bytes=initial,
            child_entry_read_bytes=child_entry, child_return_read_bytes=child_return,
            final_read_bytes=final, command_read_bytes=final-initial,
            phase_read_ledger=dict(request_and_admission_bytes=child_entry-initial,
                child_execution_bytes=child_return-child_entry, after_child_bytes=final-child_return),
            source_authentication='NOT_ATTESTED', scientific_status='NOT_VALIDATED',
            authorities=dict.fromkeys(pure.SUMMARY_AUTHORITIES, False), limitations=[
                'STANDALONE_DIAGNOSTIC_NOT_MASTER_PDCA_BACKEND_OR_NATIVE_PREDICTION',
                'DECLARED_CONSISTENCY_NOT_TRUSTED_ISSUER_PREREVEAL_OR_PROTOCOL_AUTHORITY',
                'NO_OFFICIAL_P0_PRODUCTION_OR_SCIENTIFIC_PERMISSION',
                'COOPERATIVE_FINAL_RECHECKS_AND_STDOUT_WRITE_ARE_NOT_AN_ATOMIC_FILESYSTEM_TRANSACTION'])
        _bound(result, guard)
        result['receipt_sha256'] = _digest(result, guard)
        _bound(result, guard)  # Include own SHA, all children and duplicate fields.
        buffer = bytearray()
        encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False,
                                   separators=(',', ':'), sort_keys=False)
        for text in encoder.iterencode(result):
            guard()
            chunk = text.encode('utf-8')
            if len(buffer) + len(chunk) > pure.MAX_JSON_BYTES:
                raise pi.InputCapacityError('CAPACITY_BLOCKED: complete stdout buffer')
            buffer.extend(chunk)
        buffer.extend(b'\n')
        if len(buffer) > pure.MAX_JSON_BYTES:
            raise pi.InputCapacityError('CAPACITY_BLOCKED: complete stdout buffer')
        guard()  # An actual last guarded read/expiry must precede ledger equality.
        if context.bytes_read != final:
            raise ValueError('Actual command ledger changed during final seal')
        return bytes(buffer)
    except BaseException:
        if guard.first is not None:
            raise guard.first
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--night', required=True)
    args = parser.parse_args(argv)
    context = pi.ProspectiveReadContext(300, g0.MAX_TOTAL_READ_BYTES)
    buffer = _command(args.root, args.night, context)
    # One fully validated buffer; stdout/process failure is not transactional.
    written = sys.stdout.buffer.write(buffer)
    if written != len(buffer):
        raise OSError('Incomplete diagnostic stdout publication; no automatic retry')
    return 0


# Master-only additive diagnostic publication. The standalone functions above
# retain their original bodies and schemas.
MASTER_OBSERVATION_VERSION = 'habu-master-score-summary-observation-v1'
MASTER_NAMES = ('model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation')
MASTER_REQUIREMENT = 'TRUSTED_SCIENTIFIC_AND_PRODUCTION_GATES_UNMET'
MASTER_IMPLEMENTATION = 'IMPLEMENTATION_BLOCKED: trusted scientific validation and production admission remain unmet'
PARENT_MAX_BYTES = 5 * 1024**2
PARENT_WRAPPER_BYTES = 64 * 1024
PARENT_LIVE_BYTES = 16 * 1024**2
_MASTER_ORIGINS = {
    'MASTER_REMAINING_DEADLINE': ('BLOCKED', 'RUNTIME_BLOCKED', 'BUDGET_EXHAUSTED: diagnostic master remaining deadline'),
    'PARENT_OWNED_CAPACITY': ('BLOCKED', 'RUNTIME_BLOCKED', 'CAPACITY_BLOCKED: diagnostic parent publication bounds'),
    'PARENT_OWNED_DEADLINE': ('BLOCKED', 'RUNTIME_BLOCKED', 'BUDGET_EXHAUSTED: diagnostic parent actual deadline'),
    'PARENT_OWNED_BYTE_LIMIT': ('BLOCKED', 'RUNTIME_BLOCKED', 'CAPACITY_BLOCKED: diagnostic parent actual read allowance'),
    'DELEGATED_UNPROVEN': ('FAIL', None, 'DIAGNOSTIC_FAILED: UNPROVEN_DELEGATED_ORIGIN'),
    'INPUT_IO_OR_CALLER': ('FAIL', None, 'DIAGNOSTIC_FAILED: INPUT_IO_OR_CALLER_ORIGIN'),
    'INTERRUPTED': ('FAIL', None, 'INTERRUPTED: diagnostic parent retains checkpoint and cumulative budget'),
    'OTHER_BASE_EXCEPTION': ('FAIL', None, 'DIAGNOSTIC_FAILED: BASE_EXCEPTION_ORIGIN'),
}
_MASTER_CONTEXTS = None
_BASE_CONTEXT_CHECK = pi.ProspectiveReadContext.check


def _base_context_check(context, method):
    from types import MethodType
    return (type(context) is pi.ProspectiveReadContext and 'check' not in vars(context) and
            type(method) is MethodType and method.__self__ is context and
            method.__func__ is _BASE_CONTEXT_CHECK)


def _new_master_context(allowance, deadline, *, max_bytes=g0.MAX_TOTAL_READ_BYTES):
    """Local one-use construction provenance, not caller/issuer authority."""
    import math
    import weakref
    global _MASTER_CONTEXTS
    if type(deadline) is not float or not math.isfinite(deadline):
        raise ValueError('Actual absolute master deadline required')
    if type(max_bytes) is not int or not 0 < max_bytes <= g0.MAX_TOTAL_READ_BYTES:
        raise ValueError('Bounded master allowance required')
    context = pi.ProspectiveReadContext(allowance, max_bytes)
    context.deadline = min(context.deadline, deadline)  # Initial unconsumed only.
    if _MASTER_CONTEXTS is None:
        _MASTER_CONTEXTS = weakref.WeakKeyDictionary()
    _MASTER_CONTEXTS[context] = (context.deadline, context.max_bytes)
    return context


def _take_master_context(context):
    if type(context) is not pi.ProspectiveReadContext or _MASTER_CONTEXTS is None:
        return None
    record = _MASTER_CONTEXTS.pop(context, None)  # Consume even rejected proof.
    if (record is None or not _base_context_check(context, context.check) or
            type(context.deadline) is not float or context.deadline != record[0] or
            type(context.max_bytes) is not int or context.max_bytes != record[1] or
            type(context.bytes_read) is not int or context.bytes_read < 0):
        return None
    return record


class _ParentState:
    def __init__(self, provenance=None):
        self.provenance, self.first, self.owned = provenance, None, None
        self.origin, self.residuals = None, []


class _ParentGuard(_Guard):
    __slots__ = ('state',)

    def __init__(self, context, state):
        super().__init__(context)
        self.state = state

    def __call__(self):
        reviewed = False
        try:
            if self.first is not None:
                raise self.first
            method = self.context.check
            proof = self.state.provenance
            reviewed = (proof is not None and _base_context_check(self.context, method) and
                type(self.context.deadline) is float and self.context.deadline == proof[0] and
                type(self.context.max_bytes) is int and self.context.max_bytes == proof[1])
            method()  # Invoke the exact method whose origin was just checked.
        except BaseException as error:
            if self.first is None:
                self.first = error
            if self.state.first is None:
                self.state.first = error
            # Bound method + one-use construction + this actual call/error;
            # neither a class name nor a mutable caller flag proves ownership.
            if reviewed:
                import time
                if type(error) is TimeoutError and time.monotonic() >= self.context.deadline:
                    self.state.owned, self.state.origin = error, 'PARENT_OWNED_DEADLINE'
                elif type(error) is pi.InputCapacityError and self.context.bytes_read > self.context.max_bytes:
                    self.state.owned, self.state.origin = error, 'PARENT_OWNED_BYTE_LIMIT'
            raise


class _MasterDiagnosticFailure(Exception):
    """Private report carrier; original exceptions are never source JSON."""
    def __init__(self, primary, origin, residuals=()):
        super().__init__('Diagnostic parent reporting boundary')
        self.primary, self.origin, self.residuals = primary, origin, list(residuals)


def _parent_capacity(state):
    error = pi.InputCapacityError('CAPACITY_BLOCKED: diagnostic parent publication bounds')
    state.owned, state.origin = error, 'PARENT_OWNED_CAPACITY'
    raise error


def _parent_length(value, guard, state):
    # This catch is restricted to a known NEW pure JSON capacity site.
    try:
        _bound(value, guard)
    except pi.InputCapacityError as error:
        if guard.first is not None:
            raise guard.first
        state.owned, state.origin = error, 'PARENT_OWNED_CAPACITY'
        raise
    count = 0
    for part in json.JSONEncoder(ensure_ascii=False, allow_nan=False,
            separators=(',', ':'), sort_keys=True).iterencode(value):
        guard()
        count += len(part.encode('utf-8'))
        if count > PARENT_LIVE_BYTES:
            _parent_capacity(state)
    return count


def _parent_nodes(value, guard, state):
    pending, count = [value], 0
    while pending:
        guard()
        item = pending.pop(); count += 1
        if count > pure.MAX_JSON_NODES:
            _parent_capacity(state)
        if type(item) in (dict, list):
            children = item.values() if type(item) is dict else item
            if len(item) > pure.MAX_JSON_NODES-count-len(pending):
                _parent_capacity(state)
            pending.extend(children)
    return count


def _parent_wrappers(value, guard, state):
    # Check BEFORE canonical_bytes allocates any additional full wrapper buffer.
    _parent_length(value, guard, state)
    total = 0
    for row in value['stages']:
        size = _parent_length(dict(stage=row, payload=value), guard, state) + 1
        if size > PARENT_WRAPPER_BYTES:
            _parent_capacity(state)
        total += size
    if total > PARENT_WRAPPER_BYTES:
        _parent_capacity(state)
    return total


def _parent_adapter(observation):
    from master_contracts import stage
    nmd = observation['status'] == 'NEED_MORE_DATA'
    rows = []
    for name in MASTER_NAMES:
        reason = ('NEED_MORE_DATA: complete admitted diagnostic scope unavailable' if nmd else
                  MASTER_REQUIREMENT if name == 'candidate_validation' else 'DEVELOPMENT_DIAGNOSTIC_ONLY')
        rows.append(stage(name, 'BLOCKED' if nmd or name == 'candidate_validation' else 'NOT_VALIDATED',
            reason, requires=[MASTER_REQUIREMENT], evidence=['snapshot/'+observation['artifact_ref']['path']],
            metrics=dict(diagnostic_status=observation['status'],
                command_receipt_sha256=observation['command_receipt_sha256'],
                artifact_sha256=observation['artifact_ref']['sha256']),
            blocker_kind='DATA_BLOCKED' if nmd else 'IMPLEMENTATION_BLOCKED' if name == 'candidate_validation' else None))
    return dict(schema_version='1.0', stages=rows, candidates=[], folds=[], replay=[], research_questions=[],
        implementation_blockers=[MASTER_IMPLEMENTATION],
        data_blockers=['NEED_MORE_DATA: complete admitted diagnostic scope unavailable'] if nmd else [],
        decision=dict(decision='NEED_MORE_DATA', reasons=['DEVELOPMENT_DIAGNOSTIC_ONLY'], required_conditions=[MASTER_REQUIREMENT]),
        diagnostic_observation=observation, scientific_status='NOT_VALIDATED',
        authorities=dict.fromkeys(pure.SUMMARY_AUTHORITIES, False))


def _failure_adapter(failure):
    from master_contracts import stage, canonical_bytes
    status, kind, reason = _MASTER_ORIGINS[failure.origin]
    interrupted = failure.origin == 'INTERRUPTED'
    residuals = list(failure.residuals)
    if len(residuals) > 8:
        raise ValueError('Unbounded cleanup residual report')
    for relative in residuals:
        if (type(relative) is not str or len(relative.encode('utf-8')) > 512 or
                '\\' in relative or ':' in relative or Path(relative).is_absolute() or
                any(ord(c)<32 or ord(c)==127 for c in relative) or
                any(part in ('', '.', '..') or part.endswith(('.', ' ')) for part in relative.split('/'))):
            raise ValueError('Unsafe cleanup residual report')
    if residuals:
        status, kind = 'FAIL', None
        reason = ('INTERRUPTED: ' if interrupted else '')+'DIAGNOSTIC_FAILED: UNTRUSTED_RESIDUAL'
    metrics = dict(diagnostic_status='FAILED_DIAGNOSTIC', origin_code=failure.origin,
                   cleanup_residuals=residuals, interrupted=interrupted)
    value = dict(schema_version='1.0', stages=[stage(name, status, reason, requires=[reason],
        evidence=[], metrics=dict(metrics), blocker_kind=kind) for name in MASTER_NAMES],
        candidates=[], folds=[], replay=[], research_questions=[], implementation_blockers=[MASTER_IMPLEMENTATION],
        data_blockers=[], decision=dict(decision='REJECT_CANDIDATE' if status == 'FAIL' else 'NEED_MORE_DATA',
            reasons=[reason], required_conditions=[MASTER_REQUIREMENT]), diagnostic_observation=None,
        scientific_status='NOT_VALIDATED', authorities=dict.fromkeys(pure.SUMMARY_AUTHORITIES, False))
    # Administrative failure reporting must remain possible on an expired model
    # context. It reads no source and neither creates nor refills a context.
    sizes = [len(canonical_bytes(dict(stage=row, payload=value)))+1 for row in value['stages']]
    if len(canonical_bytes(value)) > PARENT_WRAPPER_BYTES or sum(sizes) > PARENT_WRAPPER_BYTES:
        raise ValueError('Failure report exceeds complete wrapper bounds')
    return value


def _parent_cleanup(root, ownership):
    from research_pdca_adapter import _cleanup_owned
    return _cleanup_owned(root, ownership)


def _parent_impl(root, night, context, state):
    import os
    import stat
    import tempfile
    ownership = []
    guard = _ParentGuard(context, state)
    try:
        if not isinstance(context, pi.ProspectiveReadContext):
            raise ValueError('Actual existing prospective context required')
        if (type(context.bytes_read) is not int or context.bytes_read < 0 or
                type(context.max_bytes) is not int or not 0 < context.max_bytes <= g0.MAX_TOTAL_READ_BYTES):
            raise ValueError('Bounded actual context required')
        initial = context.bytes_read
        guard()
        if not 0 < context.remaining_seconds <= 300:
            raise ValueError('Actual positive remaining deadline at most300 required')
        root = Path(root).absolute()
        raw = _command(root, night, context)
        returned_bytes = context.bytes_read  # BEFORE decode/hash guards can read.
        if len(raw) > PARENT_MAX_BYTES or 3*len(raw)+4*PARENT_WRAPPER_BYTES > PARENT_LIVE_BYTES:
            _parent_capacity(state)
        command = _decode(raw, guard)
        bridge._sealed(command, 'receipt_sha256', guard)
        if command['schema_version'] != COMMAND_VERSION or command['operational_night'] != night:
            raise ValueError('Original command version/night mismatch')
        child = command['child']
        bridge._sealed(child, 'receipt_sha256', guard)
        c1, ce = command['final_read_bytes'], command['entry_initial_read_bytes']
        if not initial <= ce <= c1 or returned_bytes != c1:
            raise ValueError('Original returned command ledger differs from actual return')
        if command['status'] not in ('DIAGNOSTIC_ONLY', 'NEED_MORE_DATA'):
            raise ValueError('Complete diagnostic or whole NMD required')
        command_size = _parent_length(command, guard, state)
        # Reserve the fixed small observation/adapter/four-wrapper trees BEFORE
        # constructing them. No near-limit child can hide their duplicate nodes.
        if _parent_nodes(command, guard, state) + 8192 > pure.MAX_JSON_NODES:
            _parent_capacity(state)
        if 2*len(raw)+command_size+4*PARENT_WRAPPER_BYTES > PARENT_LIVE_BYTES:
            _parent_capacity(state)
        physical = hashlib.sha256(raw).hexdigest()
        relative = f'reports/pdca/{night}/diagnostics/score-summary-v1/{physical}.json'
        ref = dict(path=relative, sha256=physical, size_bytes=len(raw))
        # Conservative complete-envelope preflight, never returned as evidence.
        observation = dict(schema_version=MASTER_OBSERVATION_VERSION, purpose='MASTER_DEVELOPMENT_DIAGNOSTIC_ONLY',
            status=command['status'], operational_night=night, artifact_ref=ref,
            command_receipt_sha256=command['receipt_sha256'], child_receipt_sha256=child['receipt_sha256'],
            request_ref=command['request_ref'], request_canonical_sha256=command['request_canonical_sha256'],
            entry_read_bytes=initial, command_entry_read_bytes=ce, command_final_read_bytes=c1,
            parent_final_read_bytes=context.max_bytes, parent_read_bytes=context.max_bytes,
            phase_read_ledger=dict(before_command_bytes=ce-initial, command_execution_bytes=c1-ce,
                after_command_bytes=context.max_bytes), publication_disposition='CREATED',
            source_authentication='NOT_ATTESTED', scientific_status='NOT_VALIDATED',
            authorities=dict.fromkeys(pure.SUMMARY_AUTHORITIES, False), limitations=[
                'DEVELOPMENT_DIAGNOSTIC_NOT_NATIVE_PREDICTION_OR_OFFICIAL_P0',
                'DECLARED_CONSISTENCY_NOT_ISSUER_PREREVEAL_OR_PROTOCOL_AUTHORITY',
                'PARENT_READS_DO_NOT_RESEAL_ORIGINAL_COMMAND_OR_CHILDREN',
                'COOPERATIVE_RECHECK_PUBLICATION_NOT_ATOMIC_INPUT_TRANSACTION',
                'NO_SCIENTIFIC_CHAMPION_OR_PRODUCTION_PERMISSION'],
            artifact_identity_kind='PHYSICAL_COMMAND_UTF8_WITH_ORIGINAL_LF',
            command_identity_kind='ORIGINAL_CANONICAL_RECEIPT_SHA256', receipt_sha256='0'*64)
        _parent_wrappers(_parent_adapter(observation), guard, state)
        target = pi._local_path(root, relative, guard)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = pi._local_path(root, relative, guard)
        fd, temporary = tempfile.mkstemp(prefix='.score-summary-', dir=target.parent)
        identity = os.fstat(fd)
        temp_relative = Path(temporary).relative_to(root).as_posix()
        temp_owned = (temp_relative, identity.st_dev, identity.st_ino)
        ownership.append(temp_owned)
        if not stat.S_ISREG(identity.st_mode):
            os.close(fd)
            raise ValueError('Exclusive regular temporary required')
        with os.fdopen(fd, 'wb') as stream:
            for offset in range(0, len(raw), 1024**2):
                guard()
                part = memoryview(raw)[offset:offset+1024**2]
                if stream.write(part) != len(part):
                    raise OSError('Incomplete diagnostic file write')
            stream.flush(); os.fsync(stream.fileno())
        guard()
        target = pi._local_path(root, relative, guard)
        final_owned = (relative, identity.st_dev, identity.st_ino)
        ownership.append(final_owned)  # Before link: interrupted native creation.
        disposition = 'CREATED'
        try:
            os.link(temporary, target)
        except FileExistsError:
            ownership.remove(final_owned)  # Existing leaves are NEVER owned.
            disposition = 'REUSED'
        reader = g0.G0ArtifactReader(root, context)
        readback = reader.read(ref, parse=False)
        if readback != raw:
            raise ValueError('Original raw diagnostic readback differs')
        del readback
        residual = _parent_cleanup(root, [temp_owned])
        ownership.remove(temp_owned)  # Never retry a failed cleanup operation.
        if residual:
            state.residuals.extend(residual)
            raise ValueError('Untrusted residual temporary diagnostic')
        _recheck(root, dict(request_ref=command['request_ref'], child=child), context, guard)
        reader.rescan()
        guard()
        final = context.bytes_read
        observation.update(parent_final_read_bytes=final, parent_read_bytes=final-initial,
            publication_disposition=disposition,
            phase_read_ledger=dict(before_command_bytes=ce-initial, command_execution_bytes=c1-ce,
                                  after_command_bytes=final-c1))
        del observation['receipt_sha256']
        observation['receipt_sha256'] = _digest(observation, guard)
        value = _parent_adapter(observation)
        envelopes = _parent_wrappers(value, guard, state)
        if len(raw)+command_size+envelopes+_parent_length(value, guard, state) > PARENT_LIVE_BYTES:
            _parent_capacity(state)
        guard()
        if context.bytes_read != final:
            raise ValueError('Actual parent ledger changed during final seal')
        ownership.clear()  # Transfer only after the terminal check succeeded.
        return value
    except BaseException as error:
        primary = state.first if state.first is not None else error
        if state.first is None:
            state.first = primary
        if ownership:
            try:
                state.residuals.extend(_parent_cleanup(Path(root).absolute(), ownership))
            except BaseException:
                state.residuals.extend(row[0] for row in ownership)
        state.residuals = list(dict.fromkeys(state.residuals))
        if state.residuals:
            try:
                BaseException.add_note(primary, 'Diagnostic cleanup residual retained; checkpoint must fail closed')
            except BaseException:
                pass  # Even a hostile exception's note hook cannot replace it.
        raise primary


def evaluate_master_score_summary_request(root, night, *, context):
    """Direct API: small adapter, one raw artifact, FIRST original error."""
    return _parent_impl(root, night, context, _ParentState())


def _evaluate_for_master(root, night, *, context):
    state = _ParentState(_take_master_context(context))
    try:
        return _parent_impl(root, night, context, state)
    except BaseException as error:
        primary = state.first if state.first is not None else error
        if primary is state.owned:
            origin = state.origin
        elif isinstance(primary, KeyboardInterrupt):
            origin = 'INTERRUPTED'
        elif isinstance(primary, (source.CandidateConfigSourceBlocked, pi.InputCapacityError,
                                  TimeoutError, g0.ForecastCapabilityError, g0.ForecastCapacityError)):
            origin = 'DELEGATED_UNPROVEN'
        elif not isinstance(primary, Exception):
            origin = 'OTHER_BASE_EXCEPTION'
        else:
            origin = 'INPUT_IO_OR_CALLER'
        raise _MasterDiagnosticFailure(primary, origin, state.residuals) from None


if __name__ == '__main__':
    raise SystemExit(main())
