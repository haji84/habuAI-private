import tempfile
import unittest
from pathlib import Path

from scripts.ingest_attachment import ingest_attachment
from scripts.register_raw_file import sha256_file


class IngestAttachmentTests(unittest.TestCase):
    def test_stages_and_promotes_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "upload.gpx"
            original = b"\xef\xbb\xbf<gpx>\r\nmeasured\r\n</gpx>\r\n"
            source.write_bytes(original)
            expected = sha256_file(source)

            result = ingest_attachment(
                source,
                repo_root=root / "repo",
                kind="gpx",
                source="chat",
                source_ref="file-example",
                expected_sha256=expected,
                promote=True,
            )

            incoming = root / "repo" / result["incoming_path"]
            raw = root / "repo" / result["raw_path"]
            self.assertEqual(incoming.read_bytes(), original)
            self.assertEqual(raw.read_bytes(), original)
            self.assertEqual(sha256_file(raw), expected)
            self.assertEqual(result["promote_status"], "promoted")
            self.assertTrue(result["byte_preserved"])

    def test_is_idempotent_by_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "night.gpx"
            source.write_bytes(b"<gpx>same</gpx>")
            repo = root / "repo"

            first = ingest_attachment(
                source, repo_root=repo, kind="gpx", source="chat", promote=True
            )
            second = ingest_attachment(
                source, repo_root=repo, kind="gpx", source="chat", promote=True
            )

            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(second["staged_status"], "already_staged")
            self.assertIn(
                second["promote_status"],
                {"already_present_by_sha256", "already_present_same_path"},
            )

    def test_rejects_expected_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "night.gpx"
            source.write_bytes(b"<gpx/>")
            with self.assertRaises(ValueError):
                ingest_attachment(
                    source,
                    repo_root=root / "repo",
                    kind="gpx",
                    source="chat",
                    expected_sha256="0" * 64,
                )

    def test_rejects_raw_filename_collision_with_different_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "night.gpx"
            source.write_bytes(b"<gpx>new</gpx>")
            repo = root / "repo"
            raw = repo / "data" / "raw" / "gpx" / "night.gpx"
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b"<gpx>old</gpx>")

            with self.assertRaises(FileExistsError):
                ingest_attachment(
                    source,
                    repo_root=repo,
                    kind="gpx",
                    source="chat",
                    promote=True,
                )


if __name__ == "__main__":
    unittest.main()
