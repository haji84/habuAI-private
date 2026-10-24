"""Read-only G0 interface freeze. Contract consistency is never scientific authority.

No observation or confirmation outcome is read. Actual cohort/fold allocation,
valid-time suitability and trusted freeze receipts remain separate prerequisites.
"""
from __future__ import annotations

from datetime import datetime, time
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

from evidence_audit import JST, night_for, timestamp
from master_contracts import canonical_bytes, digest, safe_path, validate_night

VERSION = 'habu-codex-cycle-v1'
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_REFERENCES = 256
POLICY_PATH = 'protocols/development/g0-policy-v1.json'
POLICY_DIGEST = '741ce69c523a2d5cb1e010c4ca4ff49d02682fdd644d5aa4b9b54ed87c49a97a'
READINESS_FIELDS = {'source_received_at', 'derived_at', 'materialized_at', 'audited_at'}
MANIFEST_FIELDS = {'schema_version', 'kind', 'cycle_id', 'base_main_sha', 'frozen_at', 'policy_ref', 'code_manifest'}


def _time(value):
    if not isinstance(value, str) or not value:
        raise ValueError('TIMEZONE_REQUIRED')
    return timestamp(value)


def operational_night(event_time: str) -> str:
    return night_for(_time(event_time))


def training_boundary(evaluated_night: str, fit_cutoff: str, forecast_cutoff: str):
    validate_night(evaluated_night)
    start = datetime.combine(datetime.fromisoformat(evaluated_night).date(), time(7), JST)
    return min(start, _time(fit_cutoff), _time(forecast_cutoff))


def require_ready_before(readiness: dict, boundary: str):
    """Reject missing readiness; an old raw receipt cannot backdate later review."""
    if not isinstance(readiness, dict) or set(readiness) != READINESS_FIELDS:
        raise ValueError('READINESS_FIELDS')
    ready = max(_time(value) for value in readiness.values())
    if ready >= _time(boundary):
        raise ValueError('NOT_AVAILABLE_BEFORE_BOUNDARY')
    return ready


def _relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or PureWindowsPath(value).drive or PurePosixPath(value).is_absolute()
            or any(p in ('', '.', '..') for p in value.split('/'))):
        raise ValueError('UNSAFE_REFERENCE_PATH')
    return value


def _local_path(root, relative):
    path = safe_path(root, relative)
    current = root
    for part in ('', *Path(relative).parts):
        if part:
            current = current / part
        if getattr(current, 'is_junction', lambda: False)():
            raise ValueError('REPARSE_PATH')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('REFERENCE_OUTSIDE_ROOT')
    return path


def code_paths(root: Path) -> list[str]:
    """Registry-owned conservative closure; a manifest cannot omit a new helper."""
    root = Path(root)
    result = set()
    for folder, suffix in (('src', '.py'), ('scripts', '.py'), ('schemas', '.json')):
        directory = _local_path(root, folder)
        if not directory.is_dir():
            raise ValueError('MISSING_CODE_DIRECTORY')
        for p in directory.rglob('*'):
            _local_path(root, p.relative_to(root).as_posix())
            if p.is_symlink():
                raise ValueError('SYMLINK_CODE_PATH')
            if p.is_file() and p.suffix == suffix:
                result.add(p.relative_to(root).as_posix())
                if len(result) > MAX_REFERENCES:
                    raise ValueError('REFERENCE_LIMIT')
    result.update(('requirements-analysis.txt', 'requirements-osm.txt'))
    return sorted(result)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def validate_cycle(root: Path, manifest: dict) -> dict:
    """Validate only the declared cycle contract, with bounded byte-exact reads.

    Sequential hash rechecks detect ordinary changes, not hostile concurrent
    filesystem replacement. No returned field authorizes fitting or production.
    """
    root = Path(root)
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise ValueError('MANIFEST_FIELDS')
    canonical_bytes(manifest)
    if manifest['schema_version'] != VERSION or manifest['kind'] != 'DEVELOPMENT_CONTRACT_ONLY':
        raise ValueError('CONTRACT_VERSION_OR_KIND')
    if not isinstance(manifest['cycle_id'], str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', manifest['cycle_id']):
        raise ValueError('CYCLE_ID')
    if not isinstance(manifest['base_main_sha'], str) or not re.fullmatch(r'[a-f0-9]{40}', manifest['base_main_sha']):
        raise ValueError('BASE_MAIN_SHA')
    _time(manifest['frozen_at'])
    refs = manifest['code_manifest']
    if not isinstance(refs, list) or not 1 <= len(refs) <= MAX_REFERENCES:
        raise ValueError('REFERENCE_LIMIT')
    expected_paths = set(code_paths(root))
    consumed = {}
    total = 0

    def read(ref):
        nonlocal total
        if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
            raise ValueError('REFERENCE_FIELDS')
        relative = _relative(ref['path'])
        if not isinstance(ref['sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', ref['sha256']):
            raise ValueError('REFERENCE_SHA256')
        if relative in consumed:
            raise ValueError('DUPLICATE_REFERENCE')
        path = _local_path(root, relative)
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError('FILE_LIMIT')
        with path.open('rb') as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        total += len(raw)
        if len(raw) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError('FILE_LIMIT')
        if hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise ValueError('HASH_MISMATCH: ' + relative)
        consumed[relative] = ref['sha256']
        return raw

    actual_paths = []
    for ref in refs:
        if not isinstance(ref, dict):
            raise ValueError('REFERENCE_FIELDS')
        relative = _relative(ref.get('path'))
        if relative not in expected_paths:
            raise ValueError('CODE_CLOSURE')
        actual_paths.append(relative)
        read(ref)
    if set(actual_paths) != expected_paths:
        raise ValueError('CODE_CLOSURE')
    policy_ref = manifest['policy_ref']
    if not isinstance(policy_ref, dict) or policy_ref.get('path') != POLICY_PATH:
        raise ValueError('POLICY_PATH')
    policy = json.loads(read(policy_ref), object_pairs_hook=_unique_object)
    if digest(policy) != POLICY_DIGEST:
        raise ValueError('POLICY_DRIFT')
    # Reject ordinary mutation after validation without claiming an atomic snapshot.
    for relative, expected in consumed.items():
        path = _local_path(root, relative)
        with path.open('rb') as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        total += len(raw)
        if len(raw) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError('FILE_LIMIT')
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('INPUT_CHANGED')
    if set(code_paths(root)) != expected_paths:
        raise ValueError('CODE_CLOSURE_CHANGED')
    return dict(status='CONTRACT_VALIDATED', scientific_status='NOT_VALIDATED',
                cycle_sha256=digest(manifest), code_sha256=digest({p: consumed[p] for p in sorted(expected_paths)}),
                policy_sha256=POLICY_DIGEST, input_hashes=consumed,
                fold_allocation=policy['fold_allocation'], confirmation_selection=policy['confirmation_selection'],
                fit_authorized=False, production_authorized=False)
