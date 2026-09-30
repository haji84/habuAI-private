"""Canonical, fail-closed contracts shared by the master stages."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

SCHEMA_VERSION = '1.0'
IMPLEMENTATION_VERSION = 'master-v1'
STATUSES = {'PASS', 'PARTIAL', 'BLOCKED', 'FAIL', 'NOT_VALIDATED', 'NOT_APPLICABLE'}
STAGE_NAMES = ('evidence_audit', 'operational_scoring', 'model_evaluation',
               'feature_research', 'candidate_generation', 'candidate_validation',
               'development', 'promotion_decision', 'champion_handoff')


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ValueError('Unsafe relative path')
    result = root / p
    current = root
    if current.is_symlink():
        raise ValueError('Symlink root is forbidden')
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'Symlink path is forbidden: {relative}')
    return result


def validate_night(night: str) -> None:
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', night):
        raise ValueError('Night must be YYYY-MM-DD')
    date.fromisoformat(night)


def atomic_json(path: Path, value) -> None:
    payload = canonical_bytes(value) + b'\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def stage(name: str, status: str, reason: str, *, requires=None, evidence=None,
          metrics=None, blocker_kind=None) -> dict:
    if name not in STAGE_NAMES or status not in STATUSES:
        raise ValueError('Invalid stage contract')
    return dict(name=name, status=status, reason=reason, requires=requires or [],
                evidence=evidence or [], metrics=metrics or {},
                implementation_version=IMPLEMENTATION_VERSION,
                execution_status='BLOCKED' if status == 'BLOCKED' else 'FAILED' if status == 'FAIL' else 'EXECUTED',
                validity_status='VALIDATED' if status == 'PASS' else 'INVALID' if status == 'FAIL' else 'NOT_VALIDATED',
                gate_outcome='PASS' if status == 'PASS' else 'FAIL' if status == 'FAIL' else 'NOT_EVALUATED',
                blocker_kind=blocker_kind)


def validate_stage(value: dict, expected: str) -> dict:
    required = {'name', 'status', 'reason', 'requires', 'evidence', 'metrics', 'implementation_version'}
    if not isinstance(value, dict) or not required <= value.keys() or value['name'] != expected:
        raise ValueError(f'Malformed stage contract: {expected}')
    if value['status'] not in STATUSES or not isinstance(value['reason'], str):
        raise ValueError(f'Malformed stage status: {expected}')
    if not isinstance(value['requires'], list) or not isinstance(value['evidence'], list) or not isinstance(value['metrics'], dict):
        raise ValueError(f'Malformed stage evidence: {expected}')
    if value['status'] == 'NOT_APPLICABLE' and (not value['reason'] or not value['evidence']):
        raise ValueError('NOT_APPLICABLE requires evidence')
    normalized = stage(expected, value['status'], value['reason'])
    normalized.update(value)
    canonical_bytes(normalized)
    return normalized


def overall_status(stages: list[dict]) -> str:
    statuses = {s['status'] for s in stages}
    if 'FAIL' in statuses:
        return 'FAIL'
    if 'BLOCKED' in statuses:
        return 'BLOCKED'
    if statuses & {'PARTIAL', 'NOT_VALIDATED'}:
        return 'PARTIAL'
    return 'PASS'


def validate_adapter_result(value: dict, names: tuple[str, ...]) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('stages'), list):
        raise ValueError('Malformed adapter result')
    for key in ('implementation_blockers', 'data_blockers'):
        blockers = value.get(key, [])
        if not isinstance(blockers, list) or not all(isinstance(item, str) for item in blockers):
            raise ValueError(f'Malformed adapter {key}')
    rows = {}
    for item in value['stages']:
        if not isinstance(item, dict) or item.get('name') in rows:
            raise ValueError('Malformed or duplicate adapter stage')
        rows[item.get('name')] = item
    for name in names:
        validate_stage(rows.get(name), name)
    canonical_bytes(value)
    return rows


def validate_operational_result(value: dict) -> str:
    """Validate the legacy boundary and derive severity from its child stages."""
    if not isinstance(value, dict) or value.get('overall_status') not in STATUSES:
        raise ValueError('Malformed operational result/status')
    children = value.get('stages')
    if not isinstance(children, list) or not children:
        raise ValueError('Operational result requires nonempty child stages')
    for child in children:
        if (not isinstance(child, dict) or not isinstance(child.get('name'), str)
                or child.get('status') not in STATUSES or not isinstance(child.get('reason'), str)):
            raise ValueError('Malformed operational child stage')
    for key in ('implementation_blockers', 'data_blockers'):
        blockers = value.get(key, [])
        if not isinstance(blockers, list) or not all(isinstance(item, str) for item in blockers):
            raise ValueError(f'Malformed operational {key}')
    derived = overall_status(children)
    if value['overall_status'] != derived:
        raise ValueError(f'Contradictory operational summary: {value["overall_status"]}; children: {derived}')
    canonical_bytes(value)
    return derived
