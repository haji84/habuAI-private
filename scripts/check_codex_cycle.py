"""Read-only validation of an explicitly frozen, contract-only G0 manifest."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from codex_cycle_contract import MAX_FILE_BYTES, validate_cycle, _unique_object


def main():
    path = ROOT / 'protocols/development/g0-contract-v1.json'
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('FILE_LIMIT')
    result = validate_cycle(ROOT, json.loads(raw, object_pairs_hook=_unique_object))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
