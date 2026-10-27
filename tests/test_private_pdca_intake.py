import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "private_pdca_intake", Path(__file__).resolve().parents[1] / "scripts" / "private_pdca_intake.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PrivateIntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.private = self.root / "private"
        self.log = self.root / "log.txt"
        self.log.write_text(
            """2026/10/26 19:36
894-1510
鹿児島県 瀬戸内町
古仁屋瀬久井西6-5
日本
エリア探索開始
2026/10/26 19:55
捕獲
ハブ捕獲~90幼体
28.12
129.34
2026/10/27 0:12
目撃
1匹
ヒメハブ
2026/10/27 0:15
轢死
1匹
ハブ
2026/10/27 1:27
894-1510
鹿児島県 瀬戸内町
日本
エリア探索終了
""",
            encoding="utf-8",
        )
        self.gpx = self.root / "route.gpx"
        self.gpx.write_text('<gpx><trk><trkseg><trkpt lat="28.1" lon="129.3"/></trkseg></trk></gpx>')

    def test_07_rollover_and_species_separation(self):
        a = mod.summarize_log(self.log.read_text())
        self.assertEqual(list(a["nights"]), ["2026-10-26"])
        n = a["nights"]["2026-10-26"]
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
        self.assertNotIn("28.12", json.dumps(a))
        self.assertNotIn("129.34", json.dumps(a))
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
        link.symlink_to(self.gpx)
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
