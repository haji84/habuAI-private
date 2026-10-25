"""Behavioral tests for the additive G0 boundary; fixtures are not field data."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import codex_cycle_contract as contract


class CycleContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        files = {'src/helper.py': b'# implementation\n',
                 'scripts/check.py': b'# checker\n',
                 'schemas/record.json': b'{}\n',
                 'requirements-analysis.txt': b'-r requirements-osm.txt\n',
                 'requirements-osm.txt': b'pandas==2.2.3\n'}
        refs = []
        for path, raw in files.items():
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
            refs.append({'path': path, 'sha256': hashlib.sha256(raw).hexdigest()})
        self.policy = json.loads((ROOT / 'protocols/development/g0-policy-v1.json').read_text(encoding='utf-8'))
        policy_path = self.root / 'protocols/development/g0-policy-v1.json'
        policy_path.parent.mkdir(parents=True)
        raw = json.dumps(self.policy, sort_keys=True).encode()
        policy_path.write_bytes(raw)
        self.manifest = dict(schema_version='habu-codex-cycle-v1',
                             kind='DEVELOPMENT_CONTRACT_ONLY', cycle_id='20261025-g0',
                             base_main_sha='4981592789f5a6fe01800df85105f2d0c49c0b4a',
                             frozen_at='2026-10-25T08:00:00+09:00',
                             policy_ref=dict(path='protocols/development/g0-policy-v1.json', sha256=hashlib.sha256(raw).hexdigest()),
                             code_manifest=refs)

    def validate(self):
        return contract.validate_cycle(self.root, self.manifest)

    def test_valid_contract_grants_no_science_or_execution_authority(self):
        result = self.validate()
        self.assertEqual(result['status'], 'CONTRACT_VALIDATED')
        self.assertEqual(result['scientific_status'], 'NOT_VALIDATED')
        self.assertFalse(result['fit_authorized'])
        self.assertFalse(result['production_authorized'])

    def test_code_tamper_fails(self):
        (self.root / 'src/helper.py').write_bytes(b'# changed\n')
        with self.assertRaisesRegex(ValueError, 'HASH_MISMATCH'):
            self.validate()

    def test_missing_transitive_helper_in_manifest_fails(self):
        self.manifest['code_manifest'] = self.manifest['code_manifest'][1:]
        with self.assertRaisesRegex(ValueError, 'CODE_CLOSURE'):
            self.validate()

    def test_new_unbound_helper_fails(self):
        (self.root / 'src/new_helper.py').write_bytes(b'# newly imported\n')
        with self.assertRaisesRegex(ValueError, 'CODE_CLOSURE'):
            self.validate()

    def test_helper_added_during_validation_fails_final_membership_check(self):
        from unittest.mock import patch
        original = contract.digest

        def digest_and_add_helper(value):
            if value == self.policy:
                (self.root / 'src/new_helper.py').write_bytes(b'# concurrently added\n')
            return original(value)

        with patch.object(contract, 'digest', side_effect=digest_and_add_helper):
            with self.assertRaisesRegex(ValueError, 'CODE_CLOSURE_CHANGED'):
                self.validate()

    def test_duplicate_reference_fails(self):
        self.manifest['code_manifest'].append(copy.deepcopy(self.manifest['code_manifest'][0]))
        with self.assertRaisesRegex(ValueError, 'DUPLICATE'):
            self.validate()

    def test_path_traversal_and_windows_paths_fail(self):
        for bad in ('../outside.py', '/etc/passwd', 'C:/outside.py', 'src\\helper.py', 'src/../helper.py'):
            with self.subTest(path=bad):
                self.manifest['code_manifest'][0]['path'] = bad
                with self.assertRaises(ValueError):
                    self.validate()

    def test_policy_mutation_cannot_be_blessed_by_rehashing(self):
        path = self.root / self.manifest['policy_ref']['path']
        self.policy['metrics']['stage1_threshold'] = 0.8
        raw = json.dumps(self.policy).encode()
        path.write_bytes(raw)
        self.manifest['policy_ref']['sha256'] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, 'POLICY_DRIFT'):
            self.validate()

    def test_outcome_reference_is_rejected_without_opening_it(self):
        self.manifest['sealed_outcomes'] = {'path': 'does-not-exist.json'}
        with self.assertRaisesRegex(ValueError, 'MANIFEST_FIELDS'):
            self.validate()

    def test_unallocated_folds_cannot_claim_ready(self):
        path = self.root / self.manifest['policy_ref']['path']
        self.policy['fold_allocation'] = 'CONFIRMATION_READY'
        raw = json.dumps(self.policy).encode()
        path.write_bytes(raw)
        self.manifest['policy_ref']['sha256'] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, 'POLICY_DRIFT'):
            self.validate()

    def test_reference_size_is_bounded(self):
        with (self.root / 'src/helper.py').open('wb') as stream:
            stream.truncate(contract.MAX_FILE_BYTES + 1)
        with self.assertRaisesRegex(ValueError, 'FILE_LIMIT'):
            self.validate()

    def test_duplicate_policy_keys_are_rejected(self):
        path = self.root / self.manifest['policy_ref']['path']
        raw = b'{"target":"A","target":"B"}'
        path.write_bytes(raw)
        self.manifest['policy_ref']['sha256'] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
            self.validate()

    def test_junction_reference_is_rejected(self):
        from unittest.mock import patch
        with patch.object(Path, 'is_junction', return_value=True, create=True):
            with self.assertRaisesRegex(ValueError, 'REPARSE'):
                self.validate()

    def test_bad_sha_and_naive_freeze_fail(self):
        for key, bad in (('base_main_sha', 'not-a-sha'), ('frozen_at', '2026-10-25T08:00:00')):
            original = self.manifest[key]
            self.manifest[key] = bad
            with self.assertRaises(ValueError):
                self.validate()
            self.manifest[key] = original

    def test_operational_night_uses_0700_jst(self):
        self.assertEqual(contract.operational_night('2026-10-24T21:59:59Z'), '2026-10-24')
        self.assertEqual(contract.operational_night('2026-10-24T22:00:00Z'), '2026-10-25')

    def test_effective_boundary_blocks_same_night_training(self):
        boundary = contract.training_boundary('2026-10-25', '2026-10-25T19:00:00+09:00', '2026-10-25T18:00:00+09:00')
        self.assertEqual(boundary.isoformat(), '2026-10-25T07:00:00+09:00')

    def test_effective_boundary_uses_earlier_forecast_cutoff(self):
        boundary = contract.training_boundary('2026-10-25', '2026-10-24T20:00:00+09:00', '2026-10-24T19:00:00+09:00')
        self.assertEqual(boundary.isoformat(), '2026-10-24T19:00:00+09:00')

    def test_readiness_max_is_strict_and_cannot_backdate_audit(self):
        ready = dict(source_received_at='2026-10-23T00:00:00Z', derived_at='2026-10-23T01:00:00Z',
                     materialized_at='2026-10-23T02:00:00Z', audited_at='2026-10-24T22:00:00Z')
        with self.assertRaisesRegex(ValueError, 'NOT_AVAILABLE_BEFORE_BOUNDARY'):
            contract.require_ready_before(ready, '2026-10-25T07:00:00+09:00')
        ready['audited_at'] = '2026-10-24T21:59:59Z'
        self.assertEqual(contract.require_ready_before(ready, '2026-10-25T07:00:00+09:00').isoformat(),
                         '2026-10-25T06:59:59+09:00')

    def test_missing_readiness_is_unknown_not_early(self):
        with self.assertRaisesRegex(ValueError, 'READINESS_FIELDS'):
            contract.require_ready_before({'source_received_at': '2026-10-23T00:00:00Z'}, '2026-10-25T07:00:00+09:00')


if __name__ == '__main__':
    unittest.main()
