"""Verify that recovered October field archives match the exact original bytes."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from scripts.text_safe_byte_archive import restore_file

ROOT = Path(__file__).resolve().parents[1]


class OctoberBackfillTransportTests(unittest.TestCase):
    SOURCES = (
        ("pdca_artifact", "227cd0a55e9c41e2a8ce6df3cfbffc38c1fddaeeb5825021fb65abd5eba036d5", 48305),
        ("gpx", "32ac595025362dd0ccbc5f2383de03a144debc9c8acd5ade19acd8a49e77b95f", 5927634),
    )

    def test_original_bytes_can_be_reconstructed_from_repository(self):
        for kind, digest, size in self.SOURCES:
            with self.subTest(kind=kind, sha256=digest):
                archive = ROOT / "data/raw/attachment_archives" / kind / digest
                self.assertTrue(archive.is_dir(), f"missing archive {archive}")
                with tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / "restored"
                    result = restore_file(archive, output)
                    self.assertTrue(result["byte_exact"])
                    self.assertEqual(result["raw_size_bytes"], size)
                    self.assertEqual(result["raw_sha256"], digest)
                    raw = output.read_bytes()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
                    if kind == "gpx":
                        root = ElementTree.fromstring(raw)
                        self.assertTrue(root.tag.endswith("gpx"))
                        self.assertGreater(len(root.findall('.//{http://www.topografix.com/GPX/1/1}trkpt')), 1000)
                    elif kind == "pdca_artifact":
                        with ZipFile(output) as package:
                            self.assertIsNone(package.testzip())
                            self.assertTrue(package.namelist())

    def test_corrupt_archive_refuses_restoration(self):
        import shutil
        kind, digest, _ = self.SOURCES[0]
        source = ROOT / "data/raw/attachment_archives" / kind / digest
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "tampered"
            shutil.copytree(source, target)
            part = target / "part_000.b64"
            raw = part.read_text("ascii")
            part.write_text(("A" if raw[0] != "A" else "B") + raw[1:], "ascii")
            with self.assertRaises(ValueError):
                restore_file(target, Path(directory) / "restored")


if __name__ == "__main__":
    unittest.main()
