"""Append-only lifecycle mechanics; production authority remains unimplemented.

Hashes validate consistency, never issuer authenticity. The temporary sandbox
context is for lifecycle/inference tests only and cannot be selected by JSON/CLI.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
import json
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import model_evaluation
from master_contracts import atomic_json, canonical_bytes, digest, file_hash, safe_path, stage, validate_night
from prediction_authority_policy import AUTHORITY_BLOCKER, SCOPE

_LIVE_CONTEXTS = set()


@dataclass(eq=False, frozen=True)
class SandboxContext:
    root: Path


@contextmanager
def sandbox_registry():
    """Allocate a fresh isolated ephemeral namespace, never attach to an existing registry."""
    with tempfile.TemporaryDirectory(prefix='habu-sandbox-mechanics-') as directory:
        context = SandboxContext(Path(directory))
        _LIVE_CONTEXTS.add(context)
        try:
            yield context
        finally:
            _LIVE_CONTEXTS.discard(context)


def _sandbox(context):
    if isinstance(context, SandboxContext):
        if context not in _LIVE_CONTEXTS:
            raise ValueError('Expired or unregistered sandbox context')
        return context
    return None


def _now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an aware ISO string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must be timezone aware')
    return result


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Invalid SHA-256 identifier')
    return value


def _json(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('Expected JSON object')
        canonical_bytes(value)
        return value
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'Invalid registry artifact: {path}') from exc


def _read_ref(root, reference):
    if not isinstance(reference, dict):
        raise ValueError('Artifact reference object required')
    path = safe_path(root, reference['path'])
    if not path.is_file() or file_hash(path) != _hash(reference['sha256']):
        raise ValueError('Artifact hash mismatch: '+str(path))
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference['sha256']:
        raise ValueError('Artifact changed between hash and decoding')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Expected artifact object')
    canonical_bytes(value)
    return value


def verify_model(model):
    required = {'schema_version', 'family', 'implementation_version', 'parameters', 'hyperparameters',
                'status', 'evidence_refs', 'training_cutoff', 'training_data_sha256', 'feature_schema_sha256',
                'protocol_sha256', 'code_sha256', 'produced_outputs', 'model_id', 'model_sha256'}
    if not isinstance(model, dict) or not required <= model.keys():
        raise ValueError('Incomplete model artifact')
    if model['schema_version'] != '1.0' or model['status'] != 'CANDIDATE':
        raise ValueError('Unsupported model artifact schema/status')
    if (model['implementation_version'] != model_evaluation.VERSION or
            model['code_sha256'] != file_hash(Path(model_evaluation.__file__))):
        raise ValueError('Model is not bound to the installed reviewed inference adapter')
    for field in ('training_data_sha256', 'feature_schema_sha256', 'protocol_sha256', 'code_sha256'):
        _hash(model[field])
    if model['feature_schema_sha256'] != digest([]):
        raise ValueError('Current registered baselines require an empty feature schema')
    expected = ['spatial_score'] + (['unit_probability'] if model['family'] in ('uniform', 'observed_unit_prevalence') else [])
    if model['produced_outputs'] != expected:
        raise ValueError('Produced outputs do not match the actual registered adapter')
    timestamp(model['training_cutoff'])
    model_evaluation.predict_model(model, [])  # validates content hash, family and fitted state
    return model


def _evidence(root, value):
    if not isinstance(value, dict) or value.get('schema_version') != '1.0':
        raise ValueError('Validation envelope schema required')
    model = verify_model(_read_ref(root, value['model']))
    if value.get('model_id') != model['model_id']:
        raise ValueError('Validation/model binding mismatch')
    for reference in value.get('artifact_refs', []):
        _read_ref(root, reference)
    return model


def validate_candidate(root, validation):
    """Check supported artifact integrity; do not mistake summaries for verified gates.

    Current adapters lack formal outputs and complete outcome-ledger reproduction.
    Future authority integration must implement those verifiers before acceptance.
    """
    try:
        model = _evidence(Path(root), validation)
        folds = validation.get('folds', [])
        if not isinstance(folds, list) or any(not isinstance(f, dict) for f in folds):
            raise ValueError('Invalid confirmation folds')
        nights = {f.get('night') for f in folds}
        for night in nights:
            validate_night(night)
        blockers = ['DATA_BLOCKED: complete hash-bound outcome coverage including outside-universe misses is not established']
        if len(nights) < 5:
            blockers.append('DATA_BLOCKED: fewer than five distinct untouched confirmation nights')
        if len({n[:4] for n in nights}) < 2:
            blockers.append('DATA_BLOCKED: cross-year confirmation unavailable')
        implementation = [AUTHORITY_BLOCKER,
            'IMPLEMENTATION_BLOCKED: complete-outcome-ledger and independent confirmation reproduction verifier',
            'IMPLEMENTATION_BLOCKED: mandatory formal 100m +/-10min inference/validation, true retraining ablation and calibration gates']
        return {'status': 'BLOCKED', 'decision': 'NEED_MORE_DATA', 'model_id': model['model_id'],
                'implementation_blockers': implementation, 'data_blockers': blockers, 'runtime_blockers': [],
                'validity_status': 'NOT_VALIDATED', 'gate_outcome': 'NOT_EVALUATED'}
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return {'status': 'FAIL', 'decision': 'REJECT_CANDIDATE', 'reason': str(exc),
                'implementation_blockers': [], 'data_blockers': [], 'runtime_blockers': [],
                'validity_status': 'INVALID', 'gate_outcome': 'FAIL'}


def _base(context):
    return safe_path(context.root, 'sandbox/champion_registry')


@contextmanager
def registry_lock(context):
    context = _sandbox(context)
    if context is None:
        raise ValueError(AUTHORITY_BLOCKER)
    base = _base(context)
    base.mkdir(parents=True, exist_ok=True)
    with (base/'registry.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield context
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _immutable(path, value):
    raw = canonical_bytes(value)+b'\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('Conflicting immutable record')
        return
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _chain(context):
    base = _base(context)
    pointer = base/'current.json'
    if not pointer.exists():
        return []
    tip = _hash(_json(pointer)['event_sha256'])
    chain, seen = [], set()
    while tip is not None:
        if tip in seen:
            raise ValueError('Registry chain cycle')
        seen.add(tip)
        event = _json(safe_path(base, 'events/'+_hash(tip)+'.json'))
        if event.get('event_sha256') != tip or digest({k:v for k,v in event.items() if k != 'event_sha256'}) != tip:
            raise ValueError('Registry event hash mismatch')
        if event.get('qualification') != SCOPE or event.get('schema_version') != '1.0':
            raise ValueError('Registry scope/schema mismatch')
        model = verify_model(_read_ref(context.root, event['model']))
        evidence = _read_ref(context.root, event['evidence'])
        bound = _evidence(context.root, evidence)
        if bound['model_id'] != model['model_id'] or event['next_model_id'] != model['model_id']:
            raise ValueError('Registry event model/evidence mismatch')
        timestamp(event['activated_at'])
        chain.append((event, model))
        tip = event['previous_event_sha256']
    chain.reverse()
    for i, (event, _) in enumerate(chain):
        previous = chain[i-1][0] if i else None
        if event['previous_model_id'] != (previous['next_model_id'] if previous else None):
            raise ValueError('Registry model transition mismatch')
        if previous and timestamp(previous['activated_at']) > timestamp(event['activated_at']):
            raise ValueError('Registry activation time reversed')
        if event['operation'] == 'ROLLBACK' and event['next_model_id'] not in {row[0]['next_model_id'] for row in chain[:i]}:
            raise ValueError('Rollback target was never committed')
        if event['operation'] not in ('PROMOTE','ROLLBACK'):
            raise ValueError('Unknown registry operation')
    return chain


def _champion_locked(context, cutoff):
    when = timestamp(cutoff)
    eligible = [(e,m) for e,m in _chain(context) if timestamp(e['activated_at']) <= when]
    if not eligible:
        return None
    event, model = eligible[-1]
    return {'qualification': SCOPE, 'event': event, 'model': model, 'model_path': event['model']['path']}


def champion_at(root, cutoff):
    timestamp(cutoff)
    if _sandbox(root) is None:
        # Never load forged/self-declared production state before the authority adapter exists.
        return None
    with registry_lock(root):
        return _champion_locked(root, cutoff)


def _commit_pointer(base, event):
    atomic_json(base/'current.json', {'event_sha256': event['event_sha256']})


def _transition(context, model_id, evidence_path, expected_previous, operation, reason):
    chain = _chain(context)
    current = chain[-1][0] if chain else None
    previous_hash = current['event_sha256'] if current else None
    source = evidence_path.relative_to(context.root).as_posix()
    evidence_ref = {'path': source, 'sha256': file_hash(safe_path(context.root, source))}
    evidence = _read_ref(context.root, evidence_ref)
    model = _evidence(context.root, evidence)
    if model['model_id'] != model_id:
        raise ValueError('Requested model does not match evidence')
    if expected_previous != previous_hash:
        if (current and current['previous_event_sha256'] == expected_previous and
                current['next_model_id'] == model_id and current['evidence'] == evidence_ref and
                current['operation'] == operation and current['reason'] == reason):
            return dict(current, event_path=f'sandbox/champion_registry/events/{previous_hash}.json')
        raise ValueError('Registry compare-and-swap conflict')
    base = _base(context)
    model_path = safe_path(base, 'models/'+_hash(model_id)+'.json')
    _immutable(model_path, model)
    activated = _now()
    if current and timestamp(activated) < timestamp(current['activated_at']):
        raise ValueError('Activation clock precedes committed event')
    body = {'schema_version': '1.0', 'qualification': SCOPE, 'operation': operation, 'reason': reason,
            'previous_event_sha256': previous_hash, 'previous_model_id': current['next_model_id'] if current else None,
            'next_model_id': model_id, 'activated_at': activated,
            'model': {'path': model_path.relative_to(context.root).as_posix(), 'sha256': file_hash(model_path)},
            'evidence': evidence_ref, 'scientific_validation': 'NOT_VALIDATED'}
    event = dict(body, event_sha256=digest(body))
    path = safe_path(base, 'events/'+event['event_sha256']+'.json')
    _immutable(path, event)
    _commit_pointer(base, event)  # only this committed pointer chain activates events
    return dict(event, event_path=path.relative_to(context.root).as_posix())


def promote(root, model_id, evidence_path, expected_previous):
    if _sandbox(root) is None:
        return {'status': 'BLOCKED', 'reason': AUTHORITY_BLOCKER, 'implementation_blockers': [AUTHORITY_BLOCKER]}
    with registry_lock(root):
        return _transition(root, model_id, Path(evidence_path), expected_previous, 'PROMOTE', 'sandbox lifecycle exercise')


def rollback(root, target_id, reason, expected_previous):
    if _sandbox(root) is None:
        return {'status': 'BLOCKED', 'reason': AUTHORITY_BLOCKER, 'implementation_blockers': [AUTHORITY_BLOCKER]}
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('Rollback reason required')
    with registry_lock(root):
        chain = _chain(root)
        prior = next((e for e,m in reversed(chain) if m['model_id'] == target_id), None)
        if prior is None:
            raise ValueError('Rollback requires a previously committed validated artifact')
        return _transition(root, target_id, safe_path(root.root, prior['evidence']['path']), expected_previous, 'ROLLBACK', reason)


def evaluate_promotion(snapshot_root, night, evaluation_result):
    """Decision-only adapter. It cannot promote from a caller's evaluation summary."""
    validate_night(night)
    value = evaluation_result if isinstance(evaluation_result, dict) else {}
    implementation = list(value.get('implementation_blockers', [])) + [AUTHORITY_BLOCKER]
    data = list(value.get('data_blockers', []))
    runtime = list(value.get('runtime_blockers', []))
    failed = any(s.get('status') == 'FAIL' for s in value.get('stages', []))
    decision = 'REJECT_CANDIDATE' if failed or value.get('decision', {}).get('decision') == 'REJECT_CANDIDATE' else 'NEED_MORE_DATA'
    upstream_reasons = list(value.get('decision', {}).get('reasons', []))
    upstream_reasons += [s.get('reason', '') for s in value.get('stages', []) if s.get('status') == 'FAIL']
    upstream_reasons = list(dict.fromkeys(r for r in upstream_reasons if r))
    reason = ('Upstream evaluation invalid: '+ '; '.join(upstream_reasons)) if failed else AUTHORITY_BLOCKER
    return {'schema_version': '1.0',
            'stages': [stage('promotion_decision', 'FAIL' if failed else 'BLOCKED', reason,
                             blocker_kind=None if failed else 'IMPLEMENTATION_BLOCKED'),
                       stage('champion_handoff', 'BLOCKED', AUTHORITY_BLOCKER, requires=['promotion_decision'],
                             blocker_kind='IMPLEMENTATION_BLOCKED')],
            'decision': {'decision': decision, 'reasons': [reason]+upstream_reasons, 'required_conditions': implementation+data+runtime},
            'implementation_blockers': implementation, 'data_blockers': data, 'runtime_blockers': runtime}
