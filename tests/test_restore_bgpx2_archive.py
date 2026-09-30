import base64, hashlib, json, lzma, struct, tempfile, unittest
from pathlib import Path
from scripts.restore_bgpx2_archive import restore

class RestoreBgpx2ArchiveTests(unittest.TestCase):
    def test_fixture_rejects_missing_parts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parts = root / "parts"
            parts.mkdir()
            manifest = {
                "part_count": 1,
                "xz_size_bytes": 1,
                "xz_sha256": "0" * 64,
                "payload_size_bytes": 1,
                "payload_sha256": "0" * 64,
                "raw_size_bytes": 1,
                "raw_sha256": "0" * 64,
            }
            mp = root / "manifest.json"
            mp.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                restore(parts, mp, root / "out.gpx")

if __name__ == "__main__":
    unittest.main()
