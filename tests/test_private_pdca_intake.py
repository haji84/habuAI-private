import importlib.util
import hashlib
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "private_pdca_intake", Path(__file__).resolve().parents[1] / "scripts" / "private_pdca_intake.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PrivateIntakeTests(unittest.TestCase):
    def directory_alias(self, link, target, *, junction=False):
        self.assertTrue(link.is_relative_to(self.root))
        self.assertTrue(target.is_relative_to(self.root))
        if junction:
            if os.name != "nt":
                self.skipTest("Actual Windows junction control requires Windows")
            result = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                                    capture_output=True, check=False)
            if result.returncode:
                self.skipTest("Junction unavailable without elevation: " + str(result.returncode))
        else:
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        def remove_alias():
            try:
                os.rmdir(link) if junction else link.unlink()
            except FileNotFoundError:
                pass
        self.addCleanup(remove_alias)

    def parent_alias_rejected(self, child, *, junction=False):
        self.private.mkdir(mode=0o700)
        outside = self.repo / "forbidden-test-output"
        outside.mkdir()
        self.directory_alias(self.private / child, outside, junction=junction)
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, log_file=self.log)
        self.assertEqual(list(outside.iterdir()), [])

    def test_raw_parent_symlink_cannot_escape_private_root(self):
        self.parent_alias_rejected("raw")

    def test_receipts_parent_symlink_cannot_escape_private_root(self):
        self.parent_alias_rejected("receipts")

    def test_raw_parent_junction_cannot_escape_private_root(self):
        self.parent_alias_rejected("raw", junction=True)

    def test_receipts_parent_junction_cannot_escape_private_root(self):
        self.parent_alias_rejected("receipts", junction=True)

    def test_receipt_leaf_symlink_is_not_reused(self):
        result = mod.intake(self.repo, self.private, log_file=self.log)
        receipt = self.private / "receipts" / (result["receipt_id"] + ".json")
        outside = self.repo / "synthetic-receipt.json"
        receipt.rename(outside)
        before = outside.read_bytes()
        try:
            receipt.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, log_file=self.log)
        self.assertEqual(outside.read_bytes(), before)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.private = self.root / "private"
        self.log = self.root / "log.txt"
        # Explicitly synthetic, non-identifying test input; not an owner log/route.
        self.log.write_text(
            "2000/01/01 19:36\nSYNTHETIC_NONLOCATION_ONLY\nエリア探索開始\n"
            "2000/01/01 19:55\n捕獲\nハブ捕獲~90幼体\n"
            "2000/01/02 0:12\n目撃\n1匹\nヒメハブ\n"
            "2000/01/02 0:15\n轢死\n1匹\nハブ\n"
            "2000/01/02 1:27\nSYNTHETIC_NONLOCATION_ONLY\nエリア探索終了\n",
            encoding="utf-8",
        )
        self.gpx = self.root / "route.gpx"
        self.gpx.write_text('<gpx creator="SYNTHETIC_TEST_ONLY"><trk><trkseg>'
                            '<trkpt lat="0" lon="0"/></trkseg></trk></gpx>')

    def test_07_rollover_and_species_separation(self):
        a = mod.summarize_log(self.log.read_text(encoding="utf-8"))
        self.assertEqual(list(a["nights"]), ["2000-01-01"])
        n = a["nights"]["2000-01-01"]
        self.assertEqual(n["owner_habu_capture_events"], 1)
        self.assertEqual(n["habu_sighting_events"], 0)
        self.assertEqual(n["habu_roadkill_events"], 1)
        self.assertEqual(n["start_events"], 1)
        self.assertEqual(n["end_events"], 1)

    def test_private_immutable_deduplicated_intake(self):
        a = mod.intake(self.repo, self.private, log_file=self.log, gpx_file=self.gpx)
        b = mod.intake(self.repo, self.private, log_file=self.log, gpx_file=self.gpx)
        self.assertEqual(a, b)
        self.assertEqual(len(list((self.private / "raw" / "gpx").glob("*.gpx"))), 1)
        self.assertNotIn("SYNTHETIC_NONLOCATION_ONLY", json.dumps(a))
        src_hash = hashlib.sha256(self.gpx.read_bytes()).hexdigest()
        self.assertEqual(
            (self.private / "raw" / "gpx" / f"{src_hash}.gpx").read_bytes(),
            self.gpx.read_bytes(),
        )
        receipt = json.loads(next((self.private / "receipts").glob("*.json")).read_text())
        self.assertEqual(receipt["pdca"], "NOT_RUN")

    def test_public_repo_and_symlinks_refused(self):
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.repo / "private", gpx_file=self.gpx)
        self.private.mkdir()
        link = self.root / "link.gpx"
        try:
            link.symlink_to(self.gpx)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, gpx_file=link)

    def test_corrupt_gpx_rejected_without_archive(self):
        self.gpx.write_text("<gpx><trk>")
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, gpx_file=self.gpx)
        self.assertFalse((self.private / "raw" / "gpx").exists())

    def test_bad_timestamp_rejected(self):
        with self.assertRaises(mod.IntakeError):
            mod.summarize_log("2026/02/30 21:00\n捕獲\nハブ捕獲~90幼体")


if __name__ == "__main__":
    unittest.main()
