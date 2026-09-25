import csv
import tempfile
import unittest
from pathlib import Path

from scripts.register_raw_file import audit_file, sha256_file


class RegisterRawFileTests(unittest.TestCase):
    def test_audit_preserves_file_and_reports_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "night.gpx"
            original = b"<gpx>measured</gpx>"
            path.write_bytes(original)
            result = audit_file(path, "gpx")
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(result["sha256"], sha256_file(path))
            self.assertEqual(result["status"], "unreviewed_incoming")

    def test_duplicate_is_flagged_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "night.gpx"
            path.write_text("same", encoding="utf-8")
            manifest = root / "manifest.csv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["path", "sha256"])
                writer.writeheader()
                writer.writerow({"path": "data/raw/gpx/old.gpx", "sha256": sha256_file(path)})
            result = audit_file(path, "gpx", manifest)
            self.assertTrue(result["duplicate"])
            self.assertEqual(result["status"], "duplicate_review_required")

    def test_wrong_extension_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fake.csv"
            path.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                audit_file(path, "gpx")


if __name__ == "__main__":
    unittest.main()

