"""Current development cursor advances without overwriting prior frozen cycles."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))
from check_codex_cycle import validate_current_cycle


class CycleCursorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = b'old immutable historical cycle\n'
        old = self.root / 'protocols/development/g0-contract-v1.json'
        old.parent.mkdir(parents=True)
        old.write_bytes(self.old)
        files = {'src/adapter.py': b'# adapter\n', 'scripts/check.py': b'# checker\n',
                 'schemas/record.json': b'{}\n', 'requirements-analysis.txt': b'\n',
                 'requirements-osm.txt': b'\n'}
        refs = []
        for path, raw in files.items():
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
            refs.append({'path': path, 'sha256': hashlib.sha256(raw).hexdigest()})
        policy = 'protocols/development/g0-policy-v1.json'
        raw = (ROOT / policy).read_bytes()
        (self.root / policy).write_bytes(raw)
        manifest = dict(schema_version='habu-codex-cycle-v1', kind='DEVELOPMENT_CONTRACT_ONLY',
                        cycle_id='fixture-cycle-2', base_main_sha='a' * 40,
                        frozen_at='2026-10-25T07:00:00+09:00', code_manifest=refs,
                        policy_ref={'path': policy, 'sha256': hashlib.sha256(raw).hexdigest()})
        self.target = 'protocols/development/cycles/fixture-cycle-2.json'
        target = self.root / self.target
        target.parent.mkdir(parents=True)
        raw = json.dumps(manifest).encode()
        target.write_bytes(raw)
        self.pointer = {'path': self.target, 'sha256': hashlib.sha256(raw).hexdigest()}
        self.publish_pointer()

    def publish_pointer(self):
        path = self.root / 'protocols/development/current-cycle.json'
        path.write_text(json.dumps(self.pointer), encoding='utf-8')

    def test_current_cycle_validates_and_old_cycle_bytes_remain_unchanged(self):
        result = validate_current_cycle(self.root)
        self.assertEqual(result['status'], 'CONTRACT_VALIDATED')
        self.assertFalse(result['fit_authorized'])
        self.assertEqual((self.root / 'protocols/development/g0-contract-v1.json').read_bytes(), self.old)

    def test_cursor_cannot_bless_modified_cycle_bytes(self):
        (self.root / self.target).write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'CURSOR_HASH'):
            validate_current_cycle(self.root)

    def test_cursor_cannot_read_outside_cycle_namespace(self):
        for path in ('../outside.json', 'data/raw/secret.json', 'C:/outside.json'):
            with self.subTest(path=path):
                self.pointer['path'] = path
                self.publish_pointer()
                with self.assertRaisesRegex(ValueError, 'CURSOR_PATH'):
                    validate_current_cycle(self.root)

    def test_cursor_rejects_unknown_fields_and_invalid_hash(self):
        self.pointer['scientific_pass'] = True
        self.publish_pointer()
        with self.assertRaisesRegex(ValueError, 'CURSOR_FIELDS'):
            validate_current_cycle(self.root)
        del self.pointer['scientific_pass']
        self.pointer['sha256'] = 'not-a-sha'
        self.publish_pointer()
        with self.assertRaisesRegex(ValueError, 'CURSOR_HASH'):
            validate_current_cycle(self.root)

    def test_duplicate_pointer_keys_are_rejected(self):
        path = self.root / 'protocols/development/current-cycle.json'
        path.write_bytes(b'{"path":"a","path":"b","sha256":"c"}')
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
            validate_current_cycle(self.root)

    def test_cursor_change_during_validation_is_rejected(self):
        from unittest.mock import patch
        import check_codex_cycle
        original = check_codex_cycle.validate_cycle

        def validate_then_change(root, manifest):
            result = original(root, manifest)
            (self.root / self.target).write_bytes(b'changed after read')
            return result

        with patch.object(check_codex_cycle, 'validate_cycle', side_effect=validate_then_change):
            with self.assertRaisesRegex(ValueError, 'CURSOR_CHANGED'):
                validate_current_cycle(self.root)


if __name__ == '__main__':
    unittest.main()
