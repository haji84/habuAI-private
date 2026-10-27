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
    for ref in (value['request_ref'], value['request']['summary_manifest'], value['request']['stage1_manifest']):
        add(ref)
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


if __name__ == '__main__':
    raise SystemExit(main())
