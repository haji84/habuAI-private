"""Verify staged source bytes and event/individual grain before canonical intake."""
import collections
import csv
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest import mock
from datetime import datetime, timedelta
from pathlib import Path

from scripts import build_september51_07h_view as builder

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'evidence/raw_intake/2026-10-21-september-corrected-source-receipt.json'

class CorrectedSeptemberSourceTests(unittest.TestCase):
    def setUp(self):
        self.receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))
        self.items = {r['kind']: r for r in self.receipt['sources']}

    def test_received_source_bytes_and_embedded_workbook(self):
        for item in self.receipt['sources']:
            raw = (ROOT / item['repository_path']).read_bytes()
            self.assertEqual(len(raw), item['size_bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'])
            blob = b'blob ' + str(len(raw)).encode() + b'\0' + raw
            self.assertEqual(hashlib.sha1(blob).hexdigest(), item['git_blob_sha1'])
        book = self.items['corrected_workbook']
        with zipfile.ZipFile(ROOT / self.items['validation_pack']['repository_path']) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(z.read(book['original_filename']),
                             (ROOT / book['repository_path']).read_bytes())

    def test_event_and_individual_counts_and_boundary(self):
        with zipfile.ZipFile(ROOT / self.items['validation_pack']['repository_path']) as z:
            def rows(name):
                return list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))))
            events = rows('csv/新規イベント_2026-09_10.csv')
            master = rows('csv/全期間イベント統合_2025-2026.csv')
            captures = [r for r in events if r['event_class'] == 'CAPTURE_HABU']
            individuals = rows('csv/新規ハブ捕獲個体_2026-09_10.csv')
            self.assertEqual(len(events), 1117)
            self.assertEqual(len(master), 3853)
            self.assertEqual(len({r['dedup_key'] for r in events}), 1117)
            self.assertEqual(len(captures), 67)
            self.assertEqual(sum(int(r['count_min']) for r in captures), 68)
            for month, event_count, individual_count in [('2026-09', 50, 51), ('2026-10', 17, 17)]:
                selected = [r for r in captures if r['exploration_night'].startswith(month)]
                self.assertEqual(len(selected), event_count)
                self.assertEqual(sum(int(r['count_min']) for r in selected), individual_count)
            self.assertEqual(len(individuals), 68)
            self.assertEqual(len({r['individual_id'] for r in individuals}), 68)
            by_event = collections.defaultdict(list)
            for r in individuals:
                by_event[r['event_id']].append(r)
            self.assertEqual(set(by_event), {r['record_id'] for r in captures})
            for event in captures:
                self.assertEqual(len(by_event[event['record_id']]), int(event['count_min']))
            midnight = [r for r in captures if r['event_time_jst'] == '2026-09-29 00:00']
            self.assertEqual(len(midnight), 1)
            self.assertEqual(midnight[0]['exploration_night'], '2026-09-28')
            self.assertEqual(midnight[0]['count_min'], '2')
            self.assertEqual(len(by_event[midnight[0]['record_id']]), 2)
            # Each row here is one individual. Summing repeated event_count would overcount.
            for r in events:
                dt = datetime.fromisoformat(r['event_time_jst'])
                self.assertEqual((dt - timedelta(hours=7)).date().isoformat(), r['exploration_night'])

    def test_non_owner_categories_are_separate(self):
        with zipfile.ZipFile(ROOT / self.items['validation_pack']['repository_path']) as z:
            rows = list(csv.DictReader(io.StringIO(z.read('csv/新規イベント_2026-09_10.csv').decode('utf-8-sig'))))
        counts = collections.Counter(r['event_class'] for r in rows)
        self.assertEqual(counts['CAPTURE_HABU'], 67)
        self.assertEqual(counts['ROADKILL_HABU'], 4)
        self.assertEqual(counts['SIGHTING_HABU'], 4)
        self.assertEqual(counts['OTHER_PERSON_CAPTURE_HABU'], 1)

    def test_derived_display_applies_07h_without_rewriting_source(self):
        with zipfile.ZipFile(ROOT / self.items['validation_pack']['repository_path']) as z:
            original = list(csv.DictReader(io.StringIO(z.read('csv/本人捕獲_全期間原DB+追加.csv').decode('utf-8-sig'))))
        path = ROOT / 'data/processed/reconciliation_candidates/2026-10-21/historical_capture_display_september51_07h.csv'
        with path.open(encoding='utf-8-sig', newline='') as f:
            corrected = list(csv.DictReader(f))
        self.assertEqual(len(original), 314)
        self.assertEqual(len(corrected), 314)
        changed = 0
        unknown = 0
        for source, result in zip(original, corrected):
            self.assertEqual({k:v for k,v in source.items() if k != 'night'},
                             {k:v for k,v in result.items() if k != 'night'})
            changed += source['night'] != result['night']
            try:
                instant = datetime.fromisoformat(source['date'] + ' ' + source['time'])
            except ValueError:
                unknown += 1
                self.assertEqual(source['night'], result['night'])
                continue
            self.assertEqual(result['night'], (instant-timedelta(hours=7)).date().isoformat())
        self.assertEqual(changed, 101)
        self.assertEqual(unknown, 23)

class CandidateWriteProtectionTests(unittest.TestCase):
    """Real temporary files reproduce the destructive behaviors being repaired."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'candidate'
        self.root.mkdir()
        self.receipt_path = self.root / RECEIPT.relative_to(ROOT)
        self.receipt_path.parent.mkdir(parents=True)
        self.receipt_path.write_bytes(RECEIPT.read_bytes())
        self.receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))
        self.sources = []
        for item in self.receipt['sources']:
            path = self.root / item['repository_path']
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / item['repository_path'], path)
            self.sources.append(path)
        self.target = self.root / 'data/processed/reconciliation_candidates/2026-10-21/historical_capture_display_september51_07h.csv'
        self.source_bytes = {p:p.read_bytes() for p in self.sources}

    def assert_sources_unchanged(self):
        for path, raw in self.source_bytes.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_build_reuses_identical_target_without_touching_it(self):
        first = builder.build(self.root)
        self.assertEqual(first['output_sha256'], '979ba7f96259c9202d084e302d08cd8f72f04017b80d4d23cc465242ca26ad07')
        before = self.target.stat()
        builder.build(self.root)
        after = self.target.stat()
        self.assertEqual((after.st_ino, after.st_mtime_ns), (before.st_ino, before.st_mtime_ns))
        self.assert_sources_unchanged()

    def test_build_refuses_different_existing_target(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b'keep different candidate unchanged')
        with self.assertRaises((ValueError, OSError)):
            builder.build(self.root)
        self.assertEqual(self.target.read_bytes(), b'keep different candidate unchanged')
        self.assert_sources_unchanged()

    def test_build_refuses_symlink_target_without_touching_source(self):
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(self.sources[0])
        with self.assertRaises((ValueError, OSError)):
            builder.build(self.root)
        self.assertTrue(self.target.is_symlink())
        self.assert_sources_unchanged()

    def test_build_refuses_symlink_output_ancestor(self):
        outside = Path(self.temp.name) / 'outside-output'
        outside.mkdir()
        (self.root / 'data').symlink_to(outside, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            builder.build(self.root)
        self.assertEqual(list(outside.iterdir()), [])
        self.assert_sources_unchanged()

    def test_build_rejects_source_paths_outside_incoming(self):
        item = self.receipt['sources'][0]
        aliases = ['elsewhere/book.xlsx', 'incoming/../elsewhere/book.xlsx']
        outside = self.root / 'elsewhere/book.xlsx'
        outside.parent.mkdir();outside.write_bytes(self.sources[0].read_bytes())
        aliases.append(str(outside))
        for alias in aliases:
            with self.subTest(alias=alias):
                item['repository_path'] = alias
                self.receipt_path.write_text(json.dumps(self.receipt), encoding='utf-8')
                with self.assertRaises((ValueError, OSError)):
                    builder.build(self.root)
                self.assertFalse(self.target.exists())
                self.assert_sources_unchanged()

    def test_build_rejects_symlink_source_file(self):
        outside = Path(self.temp.name) / 'outside-book.xlsx'
        shutil.copyfile(self.sources[0], outside)
        self.sources[0].unlink();self.sources[0].symlink_to(outside)
        with self.assertRaises((ValueError, OSError)):
            builder.build(self.root)
        self.assertEqual(outside.read_bytes(), self.source_bytes[self.sources[0]])
        self.assertFalse(self.target.exists())

    def test_build_rejects_symlink_source_ancestor(self):
        parent = self.sources[0].parent
        outside = Path(self.temp.name) / 'outside-incoming'
        parent.rename(outside)
        parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            builder.build(self.root)
        self.assertFalse(self.target.exists())
        self.assert_sources_unchanged()

    def test_build_rejects_receipt_symlink(self):
        real = Path(self.temp.name) / 'receipt.json'
        self.receipt_path.rename(real);self.receipt_path.symlink_to(real)
        with self.assertRaises((ValueError, OSError)):
            builder.build(self.root)
        self.assertFalse(self.target.exists())
        self.assert_sources_unchanged()

    def test_build_rechecks_source_changed_after_initial_validation(self):
        original_parse = builder.xml_display_rows
        def change_source_then_parse(value):
            # Appended bytes leave the ZIP readable, so only a final hash check catches this.
            self.sources[1].write_bytes(self.source_bytes[self.sources[1]] + b'changed after verification')
            return original_parse(value)
        with mock.patch.object(builder, 'xml_display_rows', side_effect=change_source_then_parse):
            with self.assertRaises((ValueError, OSError)):
                builder.build(self.root)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.sources[0].read_bytes(), self.source_bytes[self.sources[0]])

    def assert_build_refuses_without_waiting(self):
        code = (
            'import sys\nfrom pathlib import Path\n'
            'from scripts.build_september51_07h_view import build\n'
            'try:\n build(Path(sys.argv[1]))\n'
            'except (ValueError, OSError):\n sys.exit(0)\n'
            'sys.exit(7)\n'
        )
        try:
            result = subprocess.run([sys.executable, '-c', code, str(self.root)],
                                    cwd=ROOT, capture_output=True, timeout=1)
        except subprocess.TimeoutExpired:
            self.fail('nonregular FIFO blocked before regular-file rejection')
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_build_refuses_fifo_source_without_waiting(self):
        self.sources[0].unlink()
        os.mkfifo(self.sources[0])
        self.assert_build_refuses_without_waiting()
        self.assertTrue(stat.S_ISFIFO(self.sources[0].stat().st_mode))
        self.assertEqual(self.sources[1].read_bytes(), self.source_bytes[self.sources[1]])
        self.assertFalse(self.target.exists())

    def test_build_refuses_existing_fifo_target_without_waiting(self):
        self.target.parent.mkdir(parents=True)
        os.mkfifo(self.target)
        self.assert_build_refuses_without_waiting()
        self.assertTrue(stat.S_ISFIFO(self.target.stat().st_mode))
        self.assert_sources_unchanged()

if __name__ == '__main__':
    unittest.main()
