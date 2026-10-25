"""Verify the actual archived OSM road-grid bytes used by the ex-ante gate."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "habu_verify_osm_road_archive", ROOT / "scripts/verify_osm_road_archive.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RealArchiveTests(unittest.TestCase):
    def test_archived_33_part_zip_passes_sha_and_crc(self):
        report = mod.verify_archive(ROOT)
        self.assertEqual(report["status"], "ARCHIVE_INTEGRITY_VERIFIED_AUXILIARY_ONLY")
        self.assertEqual(report["sha256"], mod.EXPECTED_SHA256)
        self.assertEqual(report["part_count"], 33)
        self.assertGreater(report["archive_bytes"], 0)
        self.assertGreater(report["file_count"], 0)
        self.assertFalse(report["road_forecast_universe_certified"])
        self.assertFalse(report["per_road_dem_features_certified"])

    def test_wrong_digest_cannot_be_laundered_into_road_evidence(self):
        with self.assertRaises(mod.ArchiveVerificationError):
            mod.verify_archive(ROOT, expected_sha256="0" * 64)

    def test_absent_parts_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(mod.ArchiveVerificationError):
                mod.verify_archive(Path(tmp))


if __name__ == "__main__":
    unittest.main()
