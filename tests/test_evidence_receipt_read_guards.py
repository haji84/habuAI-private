"""Real filesystem read guards; synthetic sources confer no observation roles."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import evidence_audit as audit
from master_contracts import canonical_bytes

NOW = '2026-10-25T20:00:00+09:00'
NIGHT = '2026-10-22'
PAYLOAD = b'INDEPENDENT SYNTHETIC OUTSIDE SENTINEL\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class EvidenceReceiptReadGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'workspace'
        self.root.mkdir()
        self.outside = self.base / 'outside'
        self.outside.mkdir()
        self.sentinel = self.outside / 'sentinel.bin'
        self.sentinel.write_bytes(PAYLOAD)
        self.links = []
        self.addCleanup(self.remove_links)

    def remove_links(self):
        for link in reversed(self.links):
            # Remove only created links, never recursively follow their targets.
            if os.name == 'nt':
                if link.is_junction():
                    os.rmdir(link)
            elif link.is_symlink():
                link.unlink()

    def directory_link(self, link, target):
        self.assertTrue(link.absolute().is_relative_to(self.base.absolute()))
        self.assertTrue(target.absolute().is_relative_to(self.base.absolute()))
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.assertTrue(link.is_junction())
            self.assertFalse(link.is_symlink())
        else:
            link.symlink_to(target, target_is_directory=True)
            self.assertTrue(link.is_symlink())
        self.links.append(link)

    def receipt(self, relative, *, name='receipt.json', duplicate=False, **updates):
        raw = (self.root / relative).read_bytes()
        row = dict(sha256=sha(raw), bytes=len(raw),
                   received_at_utc='2026-10-24T00:00:00+00:00', source='synthetic')
        row['raw_duplicate_path' if duplicate else 'raw_path'] = relative
        row.update(updates)
        path = self.root / 'evidence/raw_intake' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_bytes(row))
        return path, row

    def watch_opens(self, watched):
        opened = []
        native = Path.open

        def observe(path, *args, **kwargs):
            if path == watched or path.is_relative_to(watched):
                opened.append(path)
            return native(path, *args, **kwargs)
        return opened, observe

    def test_direct_external_directory_link_rejects_before_payload_open(self):
        link = self.root / 'data/raw/junction'
        self.directory_link(link, self.outside)
        target = link / 'sentinel.bin'
        a = audit.Audit(self.root, NOW)
        opened, observe = self.watch_opens(target)
        with patch.object(Path, 'open', observe), self.assertRaises(ValueError) as caught:
            a.read('data/raw/junction/sentinel.bin')
        self.assertIn('Reparse' if os.name == 'nt' else 'Symlink', str(caught.exception))
        self.assertEqual(opened, [])
        self.assertEqual((a.reads, a.read_bytes, a.consumed), (0, 0, {}))
        self.assertEqual(self.sentinel.read_bytes(), PAYLOAD)

    def test_receipt_external_raw_reference_is_fail_without_payload_open(self):
        link = self.root / 'data/raw/junction'
        self.directory_link(link, self.outside)
        relative = 'data/raw/junction/sentinel.bin'
        receipt, _ = self.receipt(relative)
        a = audit.Audit(self.root, NOW)
        opened, observe = self.watch_opens(link / 'sentinel.bin')
        with patch.object(Path, 'open', observe):
            audit._receipts(a)
        self.assertEqual(opened, [])
        self.assertEqual(a.receipts, {})
        self.assertEqual([c['status'] for c in a.checks], ['FAIL'])
        self.assertEqual((a.reads, a.read_bytes), (1, receipt.stat().st_size))
        self.assertEqual(self.sentinel.read_bytes(), PAYLOAD)

    def test_receipt_anchor_link_rejects_before_external_scan_or_open(self):
        inside = self.root / 'data/raw/inside.bin'
        inside.parent.mkdir(parents=True)
        inside.write_bytes(PAYLOAD)
        receipt, _ = self.receipt('data/raw/inside.bin')
        external_receipts = self.outside / 'receipts'
        external_receipts.mkdir()
        receipt.rename(external_receipts / receipt.name)
        receipt.parent.rmdir()
        anchor = self.root / 'evidence/raw_intake'
        self.directory_link(anchor, external_receipts)
        a = audit.Audit(self.root, NOW)
        scanned = []
        native_scan = os.scandir
        opened, observe = self.watch_opens(anchor)

        def scan(path):
            if Path(path) == anchor:
                scanned.append(Path(path))
            return native_scan(path)

        with patch.object(os, 'scandir', scan), patch.object(Path, 'open', observe):
            with self.assertRaises(ValueError):
                audit._receipts(a)
        self.assertEqual((scanned, opened), ([], []))
        self.assertEqual((a.reads, a.read_bytes, a.receipts), (0, 0, {}))
        self.assertTrue((external_receipts / receipt.name).is_file())

    def test_missing_normal_anchor_keeps_entire_audit_state_unchanged(self):
        a = audit.Audit(self.root, NOW)
        before = dict(a.__dict__)
        self.assertIsNone(audit._receipts(a))
        self.assertEqual(a.__dict__, before)

    def test_normal_receipts_keep_order_duplicate_and_earliest_selection(self):
        relative = 'data/raw/日本 語/内 部.part~1draft.txt'
        raw = self.root / relative
        raw.parent.mkdir(parents=True)
        raw.write_bytes(PAYLOAD)
        late, _ = self.receipt(relative, name='a.json', received_at_utc='2026-10-24T03:00:00+00:00')
        early, _ = self.receipt(relative, name='b.json', duplicate=True,
                                received_at_utc='2026-10-24T01:00:00+00:00')
        middle, _ = self.receipt(relative, name='c.json', received_at_utc='2026-10-24T02:00:00+00:00')
        order = []
        class Record(audit.Audit):
            def read(self, path, *, max_bytes=None):
                order.append(path)
                return super().read(path, max_bytes=max_bytes)
        a = Record(self.root, NOW)
        audit._receipts(a)
        receipts = [p.relative_to(self.root).as_posix() for p in (late, early, middle)]
        self.assertEqual(order, [p for receipt in receipts for p in (receipt, relative)])
        self.assertEqual((a.reads, a.read_bytes), (6, sum(p.stat().st_size for p in (late, early, middle)) + 3 * len(PAYLOAD)))
        self.assertEqual([c['status'] for c in a.checks], ['PASS'] * 3)
        self.assertEqual(a.receipts[relative]['_ref']['path'], receipts[1])
        source = a.source(relative, sha(PAYLOAD), len(PAYLOAD))
        self.assertEqual(source['availability_basis'], 'VERIFIED_RECEIPT')
        self.assertEqual(source['available_at'], '2026-10-24T01:00:00+00:00')
        self.assertIsNone(source['historical_available_at'])
        self.assertEqual(source['use_roles'], ['diagnostic_only'])
        self.assertEqual(a.reads, 6)

    def test_hash_and_time_failures_keep_ordinary_fail_semantics(self):
        raw = self.root / 'data/raw/inside.bin'
        raw.parent.mkdir(parents=True)
        raw.write_bytes(PAYLOAD)
        self.receipt('data/raw/inside.bin', name='bad_hash.json', sha256='0' * 64)
        self.receipt('data/raw/inside.bin', name='future.json', received_at_utc='2026-10-27T00:00:00+00:00')
        a = audit.Audit(self.root, NOW)
        audit._receipts(a)
        self.assertEqual(a.receipts, {})
        self.assertEqual([c['status'] for c in a.checks], ['FAIL', 'FAIL'])
        self.assertEqual([c['reason'] for c in a.checks], ['RECEIPT_HASH_OR_SIZE_MISMATCH', 'FUTURE_RECEIPT'])
        self.assertEqual(a.reads, 4)
        self.assertEqual(raw.read_bytes(), PAYLOAD)

    def test_rejected_reference_does_not_block_unrelated_valid_receipt(self):
        link = self.root / 'data/raw/junction'
        self.directory_link(link, self.outside)
        self.receipt('data/raw/junction/sentinel.bin', name='a_bad.json', duplicate=True)
        inside = self.root / 'data/raw/inside.bin'
        inside.write_bytes(PAYLOAD)
        self.receipt('data/raw/inside.bin', name='b_good.json')
        a = audit.Audit(self.root, NOW)
        audit._receipts(a)
        self.assertEqual([c['status'] for c in a.checks], ['FAIL', 'PASS'])
        self.assertEqual(set(a.receipts), {'data/raw/inside.bin'})
        self.assertEqual(a.reads, 3)

    def test_receipt_leaf_directory_link_rejects_without_open_attempt(self):
        anchor = self.root / 'evidence/raw_intake'
        anchor.mkdir(parents=True)
        leaf = anchor / 'receipt.json'
        self.directory_link(leaf, self.outside)
        opened, observe = self.watch_opens(leaf)
        a = audit.Audit(self.root, NOW)
        with patch.object(Path, 'open', observe):
            audit._receipts(a)
        self.assertEqual(opened, [])
        self.assertEqual((a.reads, a.read_bytes, a.receipts), (0, 0, {}))
        self.assertEqual([c['status'] for c in a.checks], ['FAIL'])

    @unittest.skipIf(os.name == 'nt', 'actual POSIX file symlink; Windows directory junctions run above')
    def test_posix_receipt_file_symlink_rejects_before_external_open(self):
        inside = self.root / 'data/raw/inside.bin'
        inside.parent.mkdir(parents=True)
        inside.write_bytes(PAYLOAD)
        receipt, _ = self.receipt('data/raw/inside.bin')
        outside_receipt = self.outside / 'receipt.json'
        receipt.rename(outside_receipt)
        receipt.symlink_to(outside_receipt)
        self.links.append(receipt)
        a = audit.Audit(self.root, NOW)
        opened, observe = self.watch_opens(receipt)
        with patch.object(Path, 'open', observe):
            audit._receipts(a)
        self.assertEqual((opened, a.reads, a.receipts), ([], 0, {}))
        self.assertEqual([c['status'] for c in a.checks], ['FAIL'])

    def test_root_and_existing_root_ancestor_links_reject_payload_reads(self):
        for kind in ('root', 'ancestor'):
            with self.subTest(kind=kind):
                actual = self.outside / kind
                target = actual / 'nested' if kind == 'ancestor' else actual
                payload = target / 'data/raw/payload.bin'
                payload.parent.mkdir(parents=True)
                payload.write_bytes(PAYLOAD)
                link = self.base / ('alias-' + kind)
                self.directory_link(link, actual)
                logical_root = link / 'nested' if kind == 'ancestor' else link
                logical_payload = logical_root / 'data/raw/payload.bin'
                a = audit.Audit(logical_root, NOW)
                opened, observe = self.watch_opens(logical_payload)
                with patch.object(Path, 'open', observe), self.assertRaises(ValueError):
                    a.read('data/raw/payload.bin')
                self.assertEqual((opened, a.reads, a.read_bytes), ([], 0, 0))
                self.assertEqual(payload.read_bytes(), PAYLOAD)

    def test_portable_alias_components_reject_before_open(self):
        parent = self.root / 'data/raw/normal'
        parent.mkdir(parents=True)
        (parent / 'payload.bin').write_bytes(PAYLOAD)
        for relative in ('data/raw/normal./payload.bin', 'data/raw/normal /payload.bin',
                         'data/raw/normal/payload.bin:stream', 'data/raw/NORMAL~1/payload.bin',
                         'data/raw/NORMAL~2.txt/payload.bin'):
            with self.subTest(path=relative):
                a = audit.Audit(self.root, NOW)
                opened, observe = self.watch_opens(self.root / relative)
                with patch.object(Path, 'open', observe), self.assertRaisesRegex(ValueError, 'Ambiguous portable path component'):
                    a.read(relative)
                self.assertEqual((opened, a.reads, a.read_bytes), ([], 0, 0))

    def test_max_size_namespace_and_expiry_validation_precede_path_guard(self):
        import master_inventory
        guard = master_inventory.local_path
        calls = []
        def observe(*args, **kwargs):
            calls.append(args)
            return guard(*args, **kwargs)
        with patch.object(master_inventory, 'local_path', observe):
            a = audit.Audit(self.root, NOW)
            with self.assertRaisesRegex(ValueError, 'SOURCE_EXPECTED_SIZE'):
                a.read('data/raw/missing', max_bytes=True)
            with self.assertRaisesRegex(ValueError, 'UNAPPROVED_INPUT_NAMESPACE'):
                a.read('reports/forbidden')
            a.deadline = 0
            with self.assertRaises(audit.AuditBudgetExceeded):
                a.read('data/raw/missing')
        self.assertEqual(calls, [])

    def test_actual_remaining_plus_one_and_read_caps_are_unchanged(self):
        relative = 'data/raw/inside.bin'
        raw = self.root / relative
        raw.parent.mkdir(parents=True)
        raw.write_bytes(PAYLOAD)
        a = audit.Audit(self.root, NOW)
        with self.assertRaisesRegex(ValueError, 'SOURCE_SIZE_LIMIT'):
            a.read(relative, max_bytes=3)
        self.assertEqual((a.reads, a.read_bytes, a.consumed), (1, 4, {}))
        a = audit.Audit(self.root, NOW)
        with patch.object(audit, 'MAX_READ_BYTES', 3), self.assertRaises(audit.AuditBudgetExceeded):
            a.read(relative)
        self.assertEqual((a.reads, a.read_bytes, a.consumed), (1, 4, {}))
        a = audit.Audit(self.root, NOW)
        opened, observe = self.watch_opens(raw)
        with patch.object(audit, 'MAX_READS', 0), patch.object(Path, 'open', observe):
            with self.assertRaises(audit.AuditBudgetExceeded):
                a.read(relative)
        self.assertEqual((opened, a.reads, a.read_bytes), ([], 1, 0))

    def test_receipt_budget_exhaustion_remains_runtime_not_receipt_fail(self):
        inside = self.root / 'data/raw/inside.bin'
        inside.parent.mkdir(parents=True)
        inside.write_bytes(PAYLOAD)
        self.receipt('data/raw/inside.bin')
        a = audit.Audit(self.root, NOW)
        with patch.object(audit, 'MAX_READS', 1), self.assertRaises(audit.AuditBudgetExceeded):
            audit._receipts(a)
        self.assertEqual((a.reads, a.receipts, a.checks), (2, {}, []))

    def test_normal_final_reread_retains_hash_accounting_and_detects_change(self):
        relative = 'data/raw/inside.bin'
        raw = self.root / relative
        raw.parent.mkdir(parents=True)
        raw.write_bytes(PAYLOAD)
        a = audit.Audit(self.root, NOW)
        self.assertEqual(a.read(relative), PAYLOAD)
        self.assertEqual(a.read(relative), PAYLOAD)
        self.assertEqual((a.reads, a.read_bytes), (2, 2 * len(PAYLOAD)))
        raw.write_bytes(b'X' + PAYLOAD[1:])
        with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED_DURING_AUDIT'):
            a.read(relative)
        self.assertEqual(a.consumed, {relative: sha(PAYLOAD)})
        self.assertEqual((a.reads, a.read_bytes), (3, 3 * len(PAYLOAD)))

    def test_bad_receipt_anchor_returns_whole_audit_fail_without_units(self):
        anchor = self.root / 'evidence/raw_intake'
        self.directory_link(anchor, self.outside)
        result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['observation_units'], [])
        self.assertEqual(result['outcome_ledger']['events'], [])
        self.assertEqual(result['input_hashes'], {})


if __name__ == '__main__':
    unittest.main()
