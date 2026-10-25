"""Read-only validation of an explicitly frozen, contract-only G0 manifest."""
import json
import hashlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from codex_cycle_contract import MAX_FILE_BYTES, validate_cycle, _unique_object, _local_path, _relative


def _read(root, relative):
    path = _local_path(root, _relative(relative))
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('FILE_LIMIT')
    return raw


def validate_current_cycle(root=ROOT):
    """Follow only a byte-bound development cursor; historical cycles stay intact."""
    root = Path(root)
    cursor_path = 'protocols/development/current-cycle.json'
    cursor_file = _local_path(root, cursor_path)
    cursor_raw = None
    if cursor_file.exists():
        cursor_raw = _read(root, cursor_path)
        pointer = json.loads(cursor_raw, object_pairs_hook=_unique_object)
        if not isinstance(pointer, dict) or set(pointer) != {'path', 'sha256'}:
            raise ValueError('CURSOR_FIELDS')
        relative = pointer['path']
        try:
            _relative(relative)
        except ValueError as exc:
            raise ValueError('CURSOR_PATH') from exc
        if not relative.startswith('protocols/development/cycles/') or not relative.endswith('.json'):
            raise ValueError('CURSOR_PATH')
        sha = pointer['sha256']
        if not isinstance(sha, str) or not re.fullmatch(r'[a-f0-9]{64}', sha):
            raise ValueError('CURSOR_HASH')
        raw = _read(root, relative)
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('CURSOR_HASH')
    else:
        relative = 'protocols/development/g0-contract-v1.json'
        raw = _read(root, relative)
    result = validate_cycle(root, json.loads(raw, object_pairs_hook=_unique_object))
    if _read(root, relative) != raw or (cursor_raw is not None and _read(root, cursor_path) != cursor_raw):
        raise ValueError('CURSOR_CHANGED')
    if cursor_raw is None and _local_path(root, cursor_path).exists():
        raise ValueError('CURSOR_CHANGED')
    return result


def main():
    result = validate_current_cycle()
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
