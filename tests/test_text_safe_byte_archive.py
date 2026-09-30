import json
import tempfile
import unittest
from pathlib import Path

from scripts.text_safe_byte_archive import pack_file, restore_file


class TextSafeByteArchiveTests(unittest.TestCase):
    def test_round_trip_preserves_arbitrary_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.gpx"
            original = (
                b"\xef\xbb\xbf<?xml version=\"1.0\"?>\r\n"
                b"<gpx>\x00\xffmeasured\r\n</gpx>\r\n"
            )
            source.write_bytes(original)
            archive = root / "archive"

            manifest = pack_file(
                source,
                archive,
                kind="gpx",
                source_name="chat",
                source_ref="file-example",
                part_chars=16,
            )
            output = root / "restored.gpx"
            result = restore_file(archive, output)

            self.assertEqual(output.read_bytes(), original)
            self.assertTrue(result["byte_exact"])
            self.assertEqual(result["raw_sha256"], manifest["raw_sha256"])
            self.assertGreater(manifest["part_count"], 1)

    def test_rejects_tampered_part(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.bin"
            source.write_bytes(bytes(range(256)) * 8)
            archive = root / "archive"
            pack_file(
                source,
                archive,
                kind="other",
                source_name="chat",
                part_chars=32,
            )

            part = sorted(archive.glob("part_*.b64"))[0]
            text = part.read_text(encoding="ascii")
            part.write_text(("A" if text[0] != "A" else "B") + text[1:], encoding="ascii")

            with self.assertRaises(ValueError):
                restore_file(archive, root / "out.bin")

    def test_rejects_missing_part(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.bin"
            source.write_bytes(b"x" * 1024)
            archive = root / "archive"
            manifest = pack_file(
                source,
                archive,
                kind="other",
                source_name="chat",
                part_chars=16,
            )
            self.assertGreater(manifest["part_count"], 1)
            sorted(archive.glob("part_*.b64"))[-1].unlink()

            with self.assertRaises(ValueError):
                restore_file(archive, root / "out.bin")

    def test_manifest_contains_transport_and_raw_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "night.gpx"
            source.write_bytes(b"<gpx>night</gpx>")
            archive = root / "archive"
            pack_file(
                source,
                archive,
                kind="gpx",
                source_name="chat",
                source_ref="turn-file-id",
                part_chars=16,
            )

            manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "habu-text-safe-byte-archive-v1")
            self.assertEqual(manifest["original_filename"], "night.gpx")
            self.assertEqual(manifest["kind"], "gpx")
            self.assertEqual(manifest["source"], "chat")
            self.assertEqual(manifest["source_ref"], "turn-file-id")
            self.assertEqual(manifest["compression"], "xz")
            self.assertEqual(manifest["transfer_encoding"], "base64")


if __name__ == "__main__":
    unittest.main()
