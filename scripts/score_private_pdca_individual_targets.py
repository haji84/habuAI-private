#!/usr/bin/env python3
"""Score an existing private ORIGINAL P0 using typed DEVELOPMENT evidence.

The hash-bound request contains the individual kernel's protocol and bundle,
with source bodies replaced by their existing path/SHA/size references. Source
paths are relative to evidence/ in the private workspace. The P0 must already
contain an individual_target_binding with protocol_sha256 (the canonical
protocol without assessment_as_of) and exante_sources_sha256 (the canonical
object with universe_source_id, targets_source_id and their complete transitive
source metadata sorted by ID). The request separately binds the P0 payload SHA.
The protocol's prediction SHA is the frozen inference SHA, avoiding a cycle
with the enclosing P0's payload SHA. The typed selection's declared freeze
precedes the information cutoff. The ORIGINAL record's creation and publication
freeze occur in that order at or after cutoff and before the forecast horizon.
This companion neither writes nor issues.

--prepare-binding validates existing typed ex-ante files before the actual
wall-clock cutoff. Its closed request is {schema_version:
'habu-private-individual-binding-request-v1', protocol: <v1 without
assessment_as_of>, exante: {universe_source_id, targets_source_id, sources}}.
Preparation accepts exactly two physical bodies under evidence/exante/: UNIVERSE
with no parents, and TARGETS whose sole parent is that universe. SUPPORT and
outcome roles, other paths and hidden ancestors are rejected before body reads.
Ordinary scoring retains its existing SUPPORT semantics. Typed files and their
namespace are consistency declarations, not authenticated outcome-free sources.
No target, timestamp, policy or persisted prediction is made.
The returned binding can be consumed unchanged later, but is not an authenticated
prereveal receipt or permission to issue. Default scoring is unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts'), str(ROOT)]

import g0_forecast_contract as g0
import individual_time_target_evaluation as individual
from master_contracts import canonical_bytes, digest, validate_night
from master_inventory import local_path
from pdca_pipeline import canonical_prediction_hash, prediction_contract_errors
import prospective_inputs as pi
# Bind the private path guard to the installed sibling, not a foreign regular
# package named "scripts" that would override this repository's namespace.
from backfill_historical_environment import assert_private_directory


REQUEST_VERSION = 'habu-private-individual-pdca-request-v1'
FREEZE_VERSION = 'habu-frozen-individual-target-binding-v1'
RESULT_VERSION = 'habu-private-individual-pdca-result-v1'
PREPARATION_VERSION = 'habu-private-individual-binding-request-v1'
EXANTE_FIELDS = {'universe_source_id', 'targets_source_id', 'sources'}
MAX_RECORD_BYTES = 2 * 1024**2
MAX_READ_BYTES = 48 * 1024**2
SCORE_FIELDS = ('individual_recall', 'matched_individuals', 'denominator_min', 'denominator_max',
                'matching_bounds', 'recall_bounds', 'registered_verified_individual_count',
                'unknown_count_event_count', 'identity_incomplete_event_count',
                'unscorable_individual_count', 'unscorable_target_count', 'false_positives',
                'precision', 'denominator_status')
TARGET_COUNT_FIELDS = {'unknown_targets': 'unknown_target_ids',
                       'confirmed_false_positive_targets': 'false_positive_target_ids'}


class MissingInput(ValueError):
    pass


class InvalidBinding(ValueError):
    pass


def _document(text, context):
    value = json.loads(text, parse_float=individual._source_float,
                       object_pairs_hook=lambda pairs: pi._unique_json_object(pairs, context.check))
    if type(value) is not dict:
        raise InvalidBinding('SOURCE_OBJECT_REQUIRED')
    canonical_bytes(value)
    context.check()
    return value


def _read_unbound(reader, path, limit, missing):
    context = reader.context
    target = local_path(reader.root, path)
    if not target.exists():
        raise MissingInput(missing)
    raw = pi._bounded_bytes(target, pi._LocalByteBudget(context, limit), context.check)
    return raw, dict(path=path, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _frozen_p0(reader, night):
    directory = f'predictions/original/{night}/P0/'
    raw, p0_ref = _read_unbound(reader, directory + 'prediction.json', MAX_RECORD_BYTES, 'ORIGINAL_P0_REQUIRED')
    p0 = _document(raw.decode('utf-8'), reader.context)
    payload_sha = p0.get('payload_sha256')
    individual._sha(payload_sha)
    if (any(key.startswith('_') for key in p0) or p0.get('prediction_version') != 'P0' or
            prediction_contract_errors(p0, night, 'ORIGINAL') or
            canonical_prediction_hash(p0) != payload_sha or canonical_bytes(p0) + b'\n' != raw):
        raise InvalidBinding('ORIGINAL_P0_CANONICAL_INTEGRITY_FAILED')
    sidecar, sidecar_ref = _read_unbound(reader, directory + 'sha256.txt', 130, 'P0_FREEZE_SIDECAR_REQUIRED')
    if sidecar != (payload_sha + '  prediction.json\n').encode('ascii'):
        raise InvalidBinding('P0_FREEZE_SIDECAR_MISMATCH')
    binding = p0.get('individual_target_binding')
    if binding is None:
        raise MissingInput('P0_FROZEN_INDIVIDUAL_BINDING_REQUIRED')
    individual._fields(binding, {'schema_version', 'protocol_sha256', 'exante_sources_sha256'})
    if binding['schema_version'] != FREEZE_VERSION:
        raise InvalidBinding('P0_FROZEN_BINDING_VERSION_REQUIRED')
    for key in ('protocol_sha256', 'exante_sources_sha256'):
        individual._sha(binding[key])
    return p0, binding, (p0_ref, sidecar_ref)


def _bound_request(reader, path, expected_sha):
    individual._sha(expected_sha)
    if type(path) is not str or not path.startswith('config/') or not path.endswith('.json') or any(
            part.casefold() in {'sealed', 'confirmation', 'incoming', 'original'}
            for part in path.split('/')):
        raise InvalidBinding('PRIVATE_REQUEST_PATH_REQUIRED')
    g0._ref(dict(path=path, sha256=expected_sha, size_bytes=1))
    raw, ref = _read_unbound(reader, path, MAX_RECORD_BYTES, 'PRIVATE_REQUEST_REQUIRED')
    if ref['sha256'] != expected_sha:
        raise InvalidBinding('PRIVATE_REQUEST_SHA_MISMATCH')
    return _document(raw.decode('utf-8'), reader.context), ref


def _freeze_context(request, p0, binding, night, context, entered):
    individual._fields(request, {'schema_version', 'p0_payload_sha256', 'protocol', 'bundle'})
    if request['schema_version'] != REQUEST_VERSION or request['p0_payload_sha256'] != p0['payload_sha256']:
        raise InvalidBinding('REQUEST_ORIGINAL_P0_BINDING_MISMATCH')
    protocol = request['protocol']
    individual._fields(protocol, individual.PROTOCOL)
    if digest({k: v for k, v in protocol.items() if k != 'assessment_as_of'}) != binding['protocol_sha256']:
        raise InvalidBinding('P0_FROZEN_PROTOCOL_MISMATCH')
    budget = individual._Budget(context.remaining_seconds)
    times = individual._protocol(protocol, budget)
    context.deadline = min(context.deadline, entered + budget.limits['max_seconds'])
    budget.deadline = min(budget.deadline, context.deadline)
    context.check()
    _, cutoff, horizon_start, _ = times
    created_at = p0.get('created_at')
    if created_at is None:
        raise MissingInput('P0_CREATED_AT_REQUIRED')
    if (protocol['context']['operational_night'] != night or
            individual._time(p0['cutoff_time']) != cutoff or
            not cutoff <= individual._time(created_at) <= individual._time(p0['frozen_at']) < horizon_start or
            individual._time(protocol['assessment_as_of']) > datetime.now(timezone.utc)):
        raise InvalidBinding('P0_FROZEN_CONTEXT_MISMATCH')
    if (p0.get('model_sha256') != protocol['lineage']['model_sha256'] or
            p0.get('inference_sha256') != protocol['lineage']['prediction_sha256']):
        raise InvalidBinding('P0_FROZEN_LINEAGE_MISMATCH')
    return protocol, times, budget


def _exante_metadata(bundle, binding, protocol, cutoff, context, *, preparation=False):
    individual._fields(bundle, EXANTE_FIELDS if preparation else individual.BUNDLE)
    if not preparation and bundle['schema_version'] != 'habu-individual-target-evaluation-input-v1':
        raise InvalidBinding('INDIVIDUAL_BUNDLE_VERSION_REQUIRED')
    nodes = bundle['sources']
    if type(nodes) is not list:
        raise InvalidBinding('SOURCE_LIST_REQUIRED')
    if preparation and len(nodes) != 2:
        raise InvalidBinding('PREPARATION_TWO_TYPED_SOURCES_REQUIRED')
    if len(nodes) > protocol['capacities']['max_sources']:
        raise pi.InputCapacityError('SOURCE_CAPACITY_EXCEEDED')
    by_id, paths = {}, set()
    for node in nodes:
        context.check()
        individual._fields(node, individual.NODE - {'raw_json_utf8'})
        ident = individual._text(node['id'])
        role = node['role']
        if ident in by_id or type(role) is not str or role not in individual.KINDS:
            raise InvalidBinding('SOURCE_ID_OR_ROLE_INVALID')
        if preparation and role not in {'UNIVERSE', 'TARGETS'}:
            raise InvalidBinding('PREPARATION_EXANTE_SOURCES_ONLY')
        ref = g0._ref(node['ref'])
        if preparation and not ref['path'].startswith('evidence/exante/'):
            raise InvalidBinding('PREPARATION_EXANTE_NAMESPACE_REQUIRED')
        path = ref['path'].casefold()
        if not ref['path'].startswith('evidence/') or path in paths or any(
                part in {'sealed', 'confirmation', 'incoming', 'original'} for part in path.split('/')):
            raise InvalidBinding('UNSAFE_OR_DUPLICATE_EVIDENCE_PATH')
        if ref['size_bytes'] > protocol['capacities']['max_raw_source_bytes']:
            raise pi.InputCapacityError('SOURCE_CAPACITY_EXCEEDED')
        paths.add(path)
        individual._ids(node['parents'], protocol['capacities']['max_sources'])
        by_id[ident] = node
    roots = {field: bundle[field] for field in ('universe_source_id', 'targets_source_id')}
    for field, role in (('universe_source_id', 'UNIVERSE'), ('targets_source_id', 'TARGETS')):
        ident = roots[field]
        if type(ident) is not str or ident not in by_id or by_id[ident]['role'] != role:
            raise MissingInput('FROZEN_EXANTE_SOURCES_REQUIRED')
        if by_id[ident]['ref']['sha256'] != protocol['exante_source_sha256'][role.lower()]:
            raise InvalidBinding('P0_EXANTE_SOURCE_SHA_MISMATCH')
    universe, target = roots['universe_source_id'], roots['targets_source_id']
    if universe not in by_id[target]['parents']:
        raise InvalidBinding('P0_EXANTE_UNIVERSE_PARENT_REQUIRED')
    if preparation and (by_id[universe]['parents'] or by_id[target]['parents'] != [universe]):
        raise InvalidBinding('PREPARATION_DIRECT_UNIVERSE_PARENT_REQUIRED')
    closure, pending = set(), list(roots.values())
    while pending:
        context.check()
        ident = pending.pop()
        if ident in closure:
            continue
        if ident not in by_id or (ident not in roots.values() and by_id[ident]['role'] != 'SUPPORT'):
            raise InvalidBinding('P0_EXANTE_PARENT_ROLE_INVALID')
        closure.add(ident)
        pending.extend(by_id[ident]['parents'])
    exante = [by_id[ident] for ident in sorted(closure)]
    if preparation and closure != set(by_id):
        raise InvalidBinding('PREPARATION_EXACT_EXANTE_CLOSURE_REQUIRED')
    if digest(dict(**roots, sources=exante)) != binding['exante_sources_sha256']:
        raise InvalidBinding('P0_EXANTE_CLOSURE_MISMATCH')
    for node in exante:
        individual._fields(node['readiness'], individual.READINESS)
        for stamp in (*node['readiness'].values(), node['usable_at']):
            individual._time(stamp)
    clocks = g0.validate_readiness_graph(
        [{k: node[k] for k in ('id', 'parents', 'readiness', 'usable_at')} for node in exante],
        cutoff, check=context.check)
    if max(clocks['ready_by_id'].values()) > individual._time(protocol['frozen_at']):
        raise InvalidBinding('P0_EXANTE_FREEZE_PRECEDES_READINESS')
    return exante


def _source_text(reader, node, *, exante=False):
    ref = node['ref']
    if not local_path(reader.root, ref['path']).exists():
        raise MissingInput('FROZEN_EXANTE_SOURCE_NOT_SUPPLIED' if exante else 'TYPED_SOURCE_NOT_SUPPLIED')
    try:
        return reader.read(ref, small=True, parse=False).decode('utf-8')
    except pi.InputCapacityError:
        raise
    except (OSError, ValueError):
        raise InvalidBinding('EXANTE_SOURCE_VALIDATION_FAILED' if exante else 'TYPED_SOURCE_VALIDATION_FAILED') from None


def _exante_texts(reader, nodes, protocol, times, budget):
    texts, primary = {}, {}
    for node in nodes:
        role = node['role']
        text = _source_text(reader, node, exante=True)
        texts[node['id']] = text
        try:
            body = individual._owned(_document(text, reader.context), budget)
            if (body.get('schema_version') != 'habu-individual-target-source-v1' or
                    body.get('kind') != individual.KINDS[role]):
                raise ValueError
            if role == 'SUPPORT':
                individual._fields(body, {'schema_version', 'kind', 'details'})
            else:
                primary[role] = body
        except individual._Capacity:
            raise
        except (ValueError, KeyError, RecursionError):
            raise InvalidBinding('FROZEN_EXANTE_BODY_MISMATCH') from None
    # Use the exact kernel validators before even opening the outcome bodies.
    # The final kernel call revalidates these same bytes with the complete DAG.
    try:
        rows, _ = individual._universe(primary['UNIVERSE'], protocol, times, budget)
        individual._targets(primary['TARGETS'], protocol, rows,
                            protocol['exante_source_sha256']['universe'], times, budget)
    except (individual._Missing, individual._Capacity):
        raise
    except (ValueError, KeyError, OverflowError, RecursionError):
        raise InvalidBinding('FROZEN_EXANTE_BODY_MISMATCH') from None
    return texts


def _result(status, blockers):
    return dict(schema_version=RESULT_VERSION, execution_status=status, blockers=blockers,
                **dict.fromkeys((*SCORE_FIELDS, *TARGET_COUNT_FIELDS)), source_authentication='NOT_ATTESTED',
                prereveal_authentication='NOT_ATTESTED', scientific_status='NOT_VALIDATED',
                official_100m_10min_kpi_computed=False, official_issuance_authorized=False,
                strict_official_score_eligible=False, scientific_authorized=False,
                confirmation_authorized=False, production_authorized=False)


def score_private_individual_targets(root, *, night, request_path, request_sha256, budget_seconds=30):
    """Read and recheck a private workspace; return only diagnostic aggregates."""
    try:
        validate_night(night)
        kind = type(budget_seconds)
        if (kind is not int and kind is not float) or not 0 < budget_seconds <= 30:
            raise InvalidBinding('BOUNDED_BUDGET_REQUIRED')
        context = pi.ProspectiveReadContext(budget_seconds, MAX_READ_BYTES)
        entered = context.deadline - budget_seconds
        root = assert_private_directory(root)
        reader = g0.G0ArtifactReader(local_path(root), context)
        p0, binding, p0_refs = _frozen_p0(reader, night)
        request, request_ref = _bound_request(reader, request_path, request_sha256)
        protocol, times, validation_budget = _freeze_context(request, p0, binding, night, context, entered)
        bundle = request['bundle']
        exante = _exante_metadata(bundle, binding, protocol, times[1], context)
        texts = _exante_texts(reader, exante, protocol, times, validation_budget)
        for node in bundle['sources']:
            if node['id'] not in texts:
                texts[node['id']] = _source_text(reader, node)
            node['raw_json_utf8'] = texts[node['id']]
        scored = individual.evaluate_individual_targets(
            bundle, protocol=protocol, budget_seconds=context.remaining_seconds)
        reader.rescan()
        for ref in (*p0_refs, request_ref):
            reader.read(ref, small=True, parse=False)
        result = _result(scored['execution_status'], scored['blockers'])
        result.update({key: scored.get(key) for key in SCORE_FIELDS})
        if scored.get('receipt_sha256'):
            result.update({key: len(scored[value]) for key, value in TARGET_COUNT_FIELDS.items()})
            result.update(p0_payload_sha256=p0['payload_sha256'], request_sha256=request_ref['sha256'],
                          p0_record_sha256=p0_refs[0]['sha256'], p0_freeze_sidecar_sha256=p0_refs[1]['sha256'],
                          frozen_protocol_sha256=binding['protocol_sha256'],
                          frozen_exante_sources_sha256=binding['exante_sources_sha256'],
                          individual_diagnostic_sha256=scored['receipt_sha256'])
        context.check()
    except MissingInput as exc:
        result = _result('DATA_BLOCKED', [str(exc)])
    except individual._Missing as exc:
        result = _result('DATA_BLOCKED', [str(exc)])
    except (TimeoutError, pi.InputCapacityError, individual._Capacity):
        result = _result('RUNTIME_BLOCKED', ['PRIVATE_SCORE_RUNTIME_OR_CAPACITY_BLOCKED'])
    except InvalidBinding as exc:
        result = _result('FAIL', [str(exc)])
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        result = _result('FAIL', ['PRIVATE_SCORE_SOURCE_VALIDATION_FAILED'])
    return dict(**result, receipt_sha256=digest(result))


def _preparation_result(status, blockers):
    return dict(_result(status, blockers), schema_version='habu-private-individual-binding-result-v1',
                individual_target_binding=None, prepared_at=None, request_sha256=None)


def prepare_private_individual_binding(root, *, night, request_path, request_sha256, budget_seconds=30):
    """Read-only, actual-clock validation; never opens outcome sources or a P0.

    A later issuer must independently validate this declarative receipt and its
    exact inputs. This function neither creates issuance lineage nor authenticates
    the source's claimed earlier freeze/readiness times.
    """
    try:
        validate_night(night)
        kind = type(budget_seconds)
        if (kind is not int and kind is not float) or not 0 < budget_seconds <= 30:
            raise InvalidBinding('BOUNDED_BUDGET_REQUIRED')
        context = pi.ProspectiveReadContext(budget_seconds, MAX_READ_BYTES)
        entered = context.deadline - budget_seconds
        started = datetime.now(timezone.utc)
        root = assert_private_directory(root)
        reader = g0.G0ArtifactReader(local_path(root), context)
        request, ref = _bound_request(reader, request_path, request_sha256)
        individual._fields(request, {'schema_version', 'protocol', 'exante'})
        if request['schema_version'] != PREPARATION_VERSION:
            raise InvalidBinding('PREPARATION_REQUEST_VERSION_REQUIRED')
        budget = individual._Budget(context.remaining_seconds)
        request = individual._owned(request, budget)
        protocol, exante = request['protocol'], request['exante']
        times = individual._precutoff_protocol(protocol, budget)
        context.deadline = min(context.deadline, entered + budget.limits['max_seconds'])
        budget.deadline = min(budget.deadline, context.deadline)
        context.check()
        individual._digest(request, budget)
        if protocol['context']['operational_night'] != night:
            raise InvalidBinding('PREPARATION_NIGHT_MISMATCH')
        frozen, cutoff = individual._time(protocol['frozen_at']), times[1]
        if not frozen <= started < cutoff:
            raise MissingInput('PREPARATION_BEFORE_ACTUAL_CUTOFF_REQUIRED')
        individual._fields(exante, EXANTE_FIELDS)
        nodes = exante['sources']
        if type(nodes) is not list or len(nodes) > protocol['capacities']['max_sources']:
            raise InvalidBinding('PREPARATION_SOURCE_LIST_REQUIRED')
        # Validate identities before deterministic sorting; no caller-selected code.
        for node in nodes:
            individual._fields(node, individual.NODE - {'raw_json_utf8'})
            individual._text(node['id'])
        binding = dict(schema_version=FREEZE_VERSION, protocol_sha256=individual._digest(protocol, budget),
            exante_sources_sha256=individual._digest(dict(
                universe_source_id=exante['universe_source_id'], targets_source_id=exante['targets_source_id'],
                sources=sorted(nodes, key=lambda row: row['id'])), budget))
        closure = _exante_metadata(exante, binding, protocol, cutoff, context, preparation=True)
        texts = _exante_texts(reader, closure, protocol, times, budget)
        # Check the known physical input projection with the same native JSON
        # byte cap. Future outcome sizes remain unknown and are checked at scoring.
        physical = dict(exante, sources=[dict(node, raw_json_utf8=texts[node['id']]) for node in closure])
        individual._digest([physical, protocol], budget)
        reader.rescan()
        reader.read(ref, small=True, parse=False)
        completed = datetime.now(timezone.utc)
        if not started <= completed < cutoff:
            raise MissingInput('PREPARATION_CLOCK_REVERSED_OR_CUTOFF_REACHED')
        context.check()
        budget.check()
        result = _preparation_result('BINDING_PREPARED', [])
        result.update(individual_target_binding=binding, prepared_at=completed.isoformat(),
                      request_sha256=ref['sha256'])
        result['receipt_sha256'] = individual._digest(result, budget)
        individual._digest(result, budget)
        context.check()
        if not completed <= datetime.now(timezone.utc) < cutoff:
            raise MissingInput('PREPARATION_CLOCK_REVERSED_OR_CUTOFF_REACHED')
    except (MissingInput, individual._Missing) as exc:
        result = _preparation_result('DATA_BLOCKED', [str(exc)])
    except (TimeoutError, pi.InputCapacityError, individual._Capacity):
        result = _preparation_result('RUNTIME_BLOCKED', ['PRIVATE_PREPARATION_RUNTIME_OR_CAPACITY_BLOCKED'])
    except InvalidBinding as exc:
        result = _preparation_result('FAIL', [str(exc)])
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        result = _preparation_result('FAIL', ['PRIVATE_PREPARATION_SOURCE_VALIDATION_FAILED'])
    return result if 'receipt_sha256' in result else dict(**result, receipt_sha256=digest(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--night', required=True)
    parser.add_argument('--request-path', required=True)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--budget-seconds', type=float, default=30)
    parser.add_argument('--prepare-binding', action='store_true',
                        help='Read-only pre-cutoff binding preparation using the actual clock; no outcomes, P0 writes or issuance.')
    args = parser.parse_args()
    operation = prepare_private_individual_binding if args.prepare_binding else score_private_individual_targets
    report = operation(
        args.root, night=args.night, request_path=args.request_path,
        request_sha256=args.request_sha256, budget_seconds=args.budget_seconds)
    print(json.dumps(report, ensure_ascii=True, allow_nan=False))
    if report['execution_status'] == 'FAIL':
        return 1
    return 2 if report['execution_status'] in {'DATA_BLOCKED', 'RUNTIME_BLOCKED'} else 0


if __name__ == '__main__':
    raise SystemExit(main())
