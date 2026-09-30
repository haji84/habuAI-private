import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.restore_line_gpx_archive import restore


class September28GpxArchiveTests(unittest.TestCase):
    def test_archive_restores_exact_verified_gpx(self):
        root = Path(__file__).resolve().parents[1]
        parts = root / "data/raw/gpx_archives/2026-09-28-探索.gpx.lines"
        manifest = parts / "manifest.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "2026-09-28-探索.gpx"
            result = restore(parts, manifest, output)
            self.assertTrue(result["byte_exact"])
            self.assertEqual(result["raw_size_bytes"], 6068111)
            self.assertEqual(result["trackpoint_count"], 22990)
            self.assertEqual(
                result["raw_sha256"],
                "2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3",
            )
            self.assertEqual(
                hashlib.sha256(output.read_bytes()).hexdigest(),
                result["raw_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
