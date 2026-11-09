"""Restore all committed Habu text-safe raw archives and check byte integrity.

This test deliberately proves actual source bytes exist in git rather than
merely trusting hashes in a manifest. Raw and ORIGINAL source stay immutable.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from scripts.text_safe_byte_archive import restore_file

ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = ROOT / 'data/raw/attachment_archives'


class OctoberBackfillTransportTests(unittest.TestCase):
    def test_all_archives_restore_byte_exactly(self):
        manifests = sorted(ARCHIVES.glob('*/*/manifest.json'))
        self.assertGreaterEqual(len(manifests), 10)
        for manifest_path in manifests:
            with self.subTest(archive=str(manifest_path.relative_to(ROOT))):
                archive = manifest_path.parent
                manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
                self.assertEqual(manifest['raw_sha256'], archive.name)
                self.assertIn(manifest['kind'], ('gpx', 'pdca_artifact'))
                with tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / 'restored'
                    result = restore_file(archive, output)
                    self.assertTrue(result['byte_exact'])
                    self.assertEqual(result['raw_size_bytes'], manifest['raw_size_bytes'])
                    raw = output.read_bytes()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), archive.name)
                    if manifest['kind'] == 'gpx':
                        root = ElementTree.fromstring(raw)
                        self.assertTrue(root.tag.endswith('gpx'))
                        self.assertGreater(len(root.findall('.//{http://www.topografix.com/GPX/1/1}trkpt')), 100)
                    else:
                        with ZipFile(output) as package:
                            self.assertIsNone(package.testzip())
                            self.assertTrue(package.namelist())

    def test_single_byte_corruption_is_rejected(self):
        archive = sorted(ARCHIVES.glob('pdca_artifact/*/manifest.json'))[0].parent
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'tampered'
            shutil.copytree(archive, dest)
            part = dest / 'part_000.b64'
            original = part.read_text('ascii')
            part.write_text(('A' if original[0] != 'A' else 'B') + original[1:], 'ascii')
            with self.assertRaises(ValueError):
                restore_file(dest, Path(directory) / 'restored')


if __name__ == '__main__':
    unittest.main()
