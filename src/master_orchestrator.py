"""Durable parent for the existing PDCA command; never issues predictions.

Adapters receive an isolated snapshot root. They may write generated evidence there,
not to source data or ORIGINAL. Hashes prove consistency, not production authority.
"""
from __future__ import annotations

import fcntl
import importlib
import importlib.metadata
import json
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from master_contracts import (SCHEMA_VERSION, STAGE_NAMES, atomic_json, digest,
                              file_hash, overall_status, safe_path, stage,
                              validate_night, validate_stage, validate_adapter_result,
                              validate_operational_result)
from pdca_pipeline import run_pipeline

SOURCE_DIRS = ('data', 'predictions', 'features', 'models', 'protocols', 'policies',
               'config', 'schemas', 'src', 'scripts', 'docs', '.github',
               'evidence', 'model_specs')
LEGACY_INPUT = 'reports/legacy_chronological_walkforward.json'
MODEL_STAGES = ('model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation')
POLICY = {'version': 'master-v1', 'max_candidates': 3, 'max_rounds': 2,
          'formal_radius_m': 100, 'formal_tolerance_minutes': 10,
          'stage1_recall_minimum': 0.90, 'production_activation': 'trusted_runner_required'}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _inventory(root: Path) -> dict:
    paths = []
    for name in SOURCE_DIRS:
        base = safe_path(root, name)
        if base.exists():
            for path in base.rglob('*'):
                if '__pycache__' in path.parts or path.suffix == '.pyc':
                    continue
                safe_path(root, path.relative_to(root).as_posix())
                if path.is_file():
                    paths.append(path)
    paths += list(root.glob('requirements*.txt'))
    paths += [root/name for name in ('pyproject.toml', 'uv.lock', 'poetry.lock', 'AGENTS.md', LEGACY_INPUT) if (root/name).exists()]
    result = {}
    for path in sorted(set(paths)):
        relative = path.relative_to(root).as_posix()
        safe_path(root, relative)
        result[relative] = {'sha256': file_hash(path), 'size_bytes': path.stat().st_size}
    return result


def _snapshot_matches(snapshot, inputs):
    actual = _inventory(snapshot)
    # REPLAY is an output namespace. Existing replay inputs remain hash checked.
    actual = {p: value for p, value in actual.items()
              if p in inputs or not p.startswith('predictions/replay/')}
    return actual == inputs


def _generated_artifacts(snapshot, inputs):
    artifacts = {}
    for path in sorted(snapshot.rglob('*')):
        relative = path.relative_to(snapshot).as_posix()
        safe_path(snapshot, relative)
        if path.is_file() and relative not in inputs:
            artifacts['snapshot/' + relative] = file_hash(path)
    return artifacts


def _runtime():
    return {'python': sys.version, 'platform': platform.platform(),
            'dependencies': sorted([d.metadata['Name'], d.version] for d in importlib.metadata.distributions() if d.metadata['Name'])}


def _code_hash():
    base = Path(__file__).resolve().parents[1]
    return digest({p.relative_to(base).as_posix(): file_hash(p)
                   for folder in ('src', 'scripts') for p in sorted((base/folder).glob('*.py'))})


def _adapter(module: str, function: str):
    try:
        imported = importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if exc.name == module:
            return None
        raise
    return getattr(imported, function, None)


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _evidence(inputs):
    entries = [dict(path=p, **info, source_type=p.split('/')[0], available_at=None,
                    quality='UNKNOWN', recovery_class='UNKNOWN', search_role='UNKNOWN')
               for p, info in inputs.items()]
    missing = []
    if not any(p.startswith('predictions/original/') for p in inputs):
        missing.append('ORIGINAL predictions')
    if 'data/processed/model_learning.json' not in inputs:
        missing.append('Audited learning snapshot with availability and forecast universe')
    return {'schema_version': SCHEMA_VERSION, 'entries': entries, 'missing': missing,
            'input_snapshot_sha256': digest(inputs)}


def run_master(root: Path, night: str, budget_seconds: int = 300) -> dict:
    validate_night(night)
    if isinstance(budget_seconds, bool) or not isinstance(budget_seconds, int) or budget_seconds < 0:
        raise ValueError('Budget must be a nonnegative integer')
    root = Path(root).absolute()
    base = safe_path(root, f'reports/pdca/{night}')
    base.mkdir(parents=True, exist_ok=True)
    lock = safe_path(root, f'reports/pdca/{night}/.master.lock')
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        return _run_locked(root, base, night, budget_seconds)


def _run_locked(root, base, night, budget_seconds):
    started = time.monotonic()
    inventory_error = None
    try:
        inputs = _inventory(root)
    except Exception as exc:
        inputs = {}
        inventory_error = f'INPUT_INVALID: {type(exc).__name__}: {exc}'
    runtime = _runtime()
    code = _code_hash()
    identity = {'night': night, 'inputs': inputs, 'code': code,
                'policy': POLICY, 'runtime': runtime, 'inventory_error': inventory_error}
    run_id = digest(identity)
    directory = safe_path(root, f'reports/pdca/{night}/runs/{run_id}')
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = safe_path(directory, 'snapshot')
    checkpoint_path = safe_path(directory, 'checkpoint.json')
    output_hashes = {}
    outputs = {}
    elapsed_before = 0.0
    round_number = 0
    created = _now()
    error = inventory_error
    retry_names = []
    active_stage = None
    active_since = None
    evidence = _evidence(inputs)

    if checkpoint_path.exists():
        try:
            cp = _read(checkpoint_path)
            if digest(cp) != _read(directory/'checkpoint.sha256.json')['sha256'] or cp['run_id'] != run_id:
                raise ValueError('checkpoint digest/identity mismatch')
            elapsed_before = cp['elapsed_seconds']
            if cp.get('active_since'):
                # Conservatively charge downtime after a killed worker too.
                elapsed_before += max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(cp['active_since'])).total_seconds())
            round_number = cp['round_number']
            created = cp['created_at']
            output_hashes = cp['outputs']
            for relative, expected in output_hashes.items():
                path = safe_path(directory, relative)
                if file_hash(path) != expected:
                    raise ValueError(f'output digest mismatch: {relative}')
            if not _snapshot_matches(snapshot, inputs):
                raise ValueError('snapshot input digest mismatch')
            if _generated_artifacts(snapshot, inputs) != {p: h for p, h in output_hashes.items() if p.startswith('snapshot/')}:
                raise ValueError('uncommitted or changed generated artifacts')
            if cp.get('result_sha256'):
                result_path = safe_path(directory, 'run_manifest.json')
                if file_hash(result_path) != cp['result_sha256']:
                    raise ValueError('manifest digest mismatch')
                result = _read(result_path)
                # Re-read sources even for duplicate commands before publishing pointer.
                if _inventory(root) != inputs or _code_hash() != code or _runtime() != runtime:
                    raise ValueError('source changed during checkpoint verification')
                retry_names = [s['name'] for s in result['stages']
                               if 'INTERRUPTED' in s['reason'] or
                               ('BUDGET_EXHAUSTED' in s['reason'] and budget_seconds > result['budget']['limit_seconds'])]
                if not retry_names:
                    atomic_json(base/'pdca_result.json', result)
                    return result
            for name in STAGE_NAMES:
                relative = f'stages/{name}.json'
                if relative in output_hashes:
                    outputs[name] = _read(directory/relative)
                    validate_stage(outputs[name]['stage'], name)
            for name in retry_names:
                outputs.pop(name, None)
                output_hashes.pop(f'stages/{name}.json', None)
        except Exception as exc:
            error = f'CHECKPOINT_INVALID: {type(exc).__name__}: {exc}'
            outputs = {}
            output_hashes = {}
    elif any(directory.iterdir()):
        error = 'CHECKPOINT_INVALID: incomplete run without checkpoint; fresh input identity required'

    def elapsed():
        return elapsed_before + max(0.0, time.monotonic() - started)

    def checkpoint(result_sha=None):
        cp = {'schema_version': SCHEMA_VERSION, 'run_id': run_id, 'outputs': dict(output_hashes),
              'elapsed_seconds': elapsed(), 'round_number': round_number,
              'created_at': created, 'result_sha256': result_sha,
              'active_stage': active_stage, 'active_since': active_since}
        atomic_json(checkpoint_path, cp)
        atomic_json(directory/'checkpoint.sha256.json', {'sha256': digest(cp)})
        return cp

    def save(name, value, payload=None, *, collect=True):
        nonlocal active_stage, active_since
        value = validate_stage(value, name)
        if collect:
            generated = _generated_artifacts(snapshot, inputs)
            for path, expected in output_hashes.items():
                if path.startswith('snapshot/') and generated.get(path) != expected:
                    raise ValueError(f'COMPLETED_ARTIFACT_CHANGED: {path}')
            output_hashes.update(generated)
        artifact = {'stage': value, 'payload': payload}
        relative = f'stages/{name}.json'
        atomic_json(safe_path(directory, relative), artifact)
        output_hashes[relative] = file_hash(directory/relative)
        outputs[name] = artifact
        active_stage = active_since = None
        checkpoint()

    def begin(name):
        nonlocal active_stage, active_since
        active_stage, active_since = name, _now()
        checkpoint()

    def blocked(name, reason, kind='IMPLEMENTATION_BLOCKED'):
        return stage(name, 'BLOCKED', reason, requires=[reason], blocker_kind=kind)

    def remaining():
        return max(0, budget_seconds - elapsed())

    current = 'evidence_audit'
    interrupted = False
    try:
        if error:
            raise ValueError(error)
        if not snapshot.exists():
            snapshot.mkdir()
            for relative, info in inputs.items():
                dest = safe_path(snapshot, relative)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(safe_path(root, relative), dest)
                if file_hash(dest) != info['sha256']:
                    raise ValueError(f'INPUT_CHANGED: {relative}')
        if not _snapshot_matches(snapshot, inputs):
            raise ValueError('INPUT_CHANGED: snapshot differs')
        atomic_json(directory/'evidence_manifest.json', evidence)
        output_hashes['evidence_manifest.json'] = file_hash(directory/'evidence_manifest.json')
        if 'evidence_audit' not in outputs:
            save('evidence_audit', stage('evidence_audit', 'NOT_VALIDATED',
                 'Byte snapshot verified; availability, trajectory quality and search eligibility unresolved',
                 evidence=['evidence_manifest.json']))
        if 'operational_scoring' not in outputs:
            current = 'operational_scoring'
            if not remaining():
                save(current, blocked(current, 'BUDGET_EXHAUSTED', 'RUNTIME_BLOCKED'))
            else:
                try:
                    begin(current)
                    result = run_pipeline(snapshot, night)
                    save(current, stage(current, validate_operational_result(result),
                         'Existing operational pipeline: ' + '; '.join(s['reason'] for s in result['stages'] if s['status'] != 'PASS'),
                         evidence=['snapshot/reports/pdca/'+night+'/pdca_result.json'],
                         blocker_kind='DATA_BLOCKED' if result['overall_status'] == 'BLOCKED' else None), result)
                except Exception as exc:
                    save(current, stage(current, 'FAIL', f'MALFORMED_OPERATIONAL_EVIDENCE: {type(exc).__name__}: {exc}'), collect=False)
        evaluation = outputs.get('model_evaluation', {}).get('payload')
        if not all(name in outputs for name in MODEL_STAGES):
            current = 'model_evaluation'
            adapter = _adapter('model_evaluation', 'evaluate_models')
            if not remaining():
                for name in MODEL_STAGES:
                    save(name, blocked(name, 'BUDGET_EXHAUSTED', 'RUNTIME_BLOCKED'))
            elif adapter is None:
                for name in MODEL_STAGES:
                    save(name, blocked(name, 'IMPLEMENTATION_BLOCKED: model_evaluation.evaluate_models unavailable'))
            elif round_number >= POLICY['max_rounds']:
                for name in MODEL_STAGES:
                    save(name, blocked(name, 'ROUND_LIMIT: fresh approved command/input required', 'RUNTIME_BLOCKED'))
            else:
                round_number += 1
                begin(current)
                evaluation = adapter(snapshot, night, int(remaining()))
                if not isinstance(evaluation, dict) or evaluation.get('schema_version') != SCHEMA_VERSION:
                    raise ValueError('Malformed evaluation result')
                if len(evaluation.get('candidates', [])) > POLICY['max_candidates']:
                    raise ValueError('Candidate budget exceeded')
                rows = validate_adapter_result(evaluation, MODEL_STAGES)
                for name in MODEL_STAGES:
                    save(name, rows[name], evaluation)
        current = 'development'
        if current not in outputs:
            save(current, blocked(current, 'IMPLEMENTATION_BLOCKED: approved development executor adapter unavailable'))
        if 'promotion_decision' not in outputs or 'champion_handoff' not in outputs:
            current = 'promotion_decision'
            adapter = _adapter('champion_registry', 'evaluate_promotion')
            if not remaining():
                for name in ('promotion_decision', 'champion_handoff'):
                    save(name, blocked(name, 'BUDGET_EXHAUSTED', 'RUNTIME_BLOCKED'))
            elif adapter is None:
                for name in ('promotion_decision', 'champion_handoff'):
                    save(name, blocked(name, 'IMPLEMENTATION_BLOCKED: champion_registry.evaluate_promotion unavailable'))
            else:
                begin(current)
                decision = adapter(snapshot, night, evaluation)
                rows = validate_adapter_result(decision, ('promotion_decision', 'champion_handoff'))
                for name in ('promotion_decision', 'champion_handoff'):
                    save(name, rows[name], decision)
    except (Exception, KeyboardInterrupt) as exc:
        interrupted = isinstance(exc, KeyboardInterrupt)
        reason = 'INTERRUPTED: retry verifies checkpoint and cumulative budget' if interrupted else f'{type(exc).__name__}: {exc}'
        save(current, stage(current, 'FAIL', reason), collect=False)
        error = reason

    # Include every stage even when malformed operational evidence or exceptions occur.
    for name in STAGE_NAMES:
        if name not in outputs:
            save(name, blocked(name, f'UPSTREAM_FAILURE: {error}', 'RUNTIME_BLOCKED'), collect=False)
    try:
        if not inventory_error and (_inventory(root) != inputs or not _snapshot_matches(snapshot, inputs) or _code_hash() != code or _runtime() != runtime):
            save('evidence_audit', stage('evidence_audit', 'FAIL', 'INPUT_CHANGED: consumed source, snapshot, code or runtime changed during run'), collect=False)
    except Exception as exc:
        save('evidence_audit', stage('evidence_audit', 'FAIL', f'INPUT_CHANGED: {exc}'), collect=False)

    # Finalization verifies committed artifacts; it never adopts interrupted output.
    try:
        if _generated_artifacts(snapshot, inputs) != {p: h for p, h in output_hashes.items() if p.startswith('snapshot/')}:
            raise ValueError('Uncommitted or changed generated artifacts at finalization')
        stages = [outputs[name]['stage'] for name in STAGE_NAMES]
        status = overall_status(stages)
        implementation = [s['reason'] for s in stages if s.get('blocker_kind') == 'IMPLEMENTATION_BLOCKED']
        data = evidence['missing'] + [s['reason'] for s in stages if s.get('blocker_kind') == 'DATA_BLOCKED']
        for artifact in outputs.values():
            payload = artifact.get('payload')
            if isinstance(payload, dict):
                implementation.extend(payload.get('implementation_blockers', []))
                data.extend(payload.get('data_blockers', []))
        implementation = list(dict.fromkeys(implementation))
        data = list(dict.fromkeys(data))
        operational = outputs.get('operational_scoring', {}).get('payload') or {}
        result = dict(operational)
        cp = checkpoint()
        atomic_json(directory/'finalization_checkpoint.json', cp)
        output_hashes['finalization_checkpoint.json'] = file_hash(directory/'finalization_checkpoint.json')
        result.update(schema_version=SCHEMA_VERSION, run_id=run_id, operational_night=night,
                      command_key=digest({'night': night, 'inputs': inputs}), code_sha256=code,
                      input_manifest_sha256=digest(evidence), policy_sha256=digest(POLICY),
                      champion_before={p: v for p, v in inputs.items() if p.startswith('models/')},
                      runtime=runtime, stages=stages, created_at=created, updated_at=_now(),
                      overall_status=status, completed=status == 'PASS',
                      execution_status='FAILED' if status == 'FAIL' else 'BLOCKED' if status == 'BLOCKED' else 'EXECUTED',
                      validity_status='VALIDATED' if status == 'PASS' else 'NOT_VALIDATED',
                      gate_outcome='PASS' if status == 'PASS' else 'FAIL' if status == 'FAIL' else 'NOT_EVALUATED',
                      implementation_blockers=implementation, data_blockers=data,
                      budget={'limit_seconds': budget_seconds, 'elapsed_seconds': cp['elapsed_seconds'],
                              'round_number': round_number, 'max_rounds': 2, 'max_candidates': 3},
                      required_conditions=[s['reason'] for s in stages if s['status'] not in ('PASS', 'NOT_APPLICABLE')],
                      checkpoint_sha256=digest(cp), operational_result=operational,
                      decision={'decision': 'NEED_MORE_DATA', 'reasons': ['Master gates not validated'],
                                'required_conditions': ['Resolve implementation/data blockers; trusted production verification required']})
        atomic_json(directory/'run_manifest.json', result)
        checkpoint(file_hash(directory/'run_manifest.json'))
        atomic_json(base/'pdca_result.json', result)
        return result
    except Exception as exc:
        # A malformed artifact/aggregation must replace an old compatibility PASS.
        reason = f'FINALIZATION_FAILED: {type(exc).__name__}: {exc}'
        save('evidence_audit', stage('evidence_audit', 'FAIL', reason), collect=False)
        stages = [outputs[name]['stage'] for name in STAGE_NAMES]
        cp = checkpoint()
        atomic_json(directory/'finalization_checkpoint.json', cp)
        output_hashes['finalization_checkpoint.json'] = file_hash(directory/'finalization_checkpoint.json')
        result = {'schema_version': SCHEMA_VERSION, 'run_id': run_id, 'operational_night': night,
                  'command_key': digest({'night': night, 'inputs': inputs}), 'code_sha256': code,
                  'input_manifest_sha256': digest(evidence), 'policy_sha256': digest(POLICY),
                  'champion_before': {p: v for p, v in inputs.items() if p.startswith('models/')},
                  'runtime': runtime, 'stages': stages, 'created_at': created, 'updated_at': _now(),
                  'overall_status': 'FAIL', 'completed': False, 'execution_status': 'FAILED',
                  'validity_status': 'INVALID', 'gate_outcome': 'FAIL',
                  'implementation_blockers': [s['reason'] for s in stages if s.get('blocker_kind') == 'IMPLEMENTATION_BLOCKED'],
                  'data_blockers': evidence['missing'], 'required_conditions': [reason],
                  'budget': {'limit_seconds': budget_seconds, 'elapsed_seconds': cp['elapsed_seconds'],
                             'round_number': round_number, 'max_rounds': 2, 'max_candidates': 3},
                  'checkpoint_sha256': digest(cp)}
        atomic_json(directory/'run_manifest.json', result)
        checkpoint(file_hash(directory/'run_manifest.json'))
        atomic_json(base/'pdca_result.json', result)
        return result
