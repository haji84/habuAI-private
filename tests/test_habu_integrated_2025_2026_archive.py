"""Guard byte-exact historical Habu DB ZIP archival and source reconciliation."""
import csv
import hashlib
import io
import json
import tempfile
import unicodedata
import unittest
import zipfile
from pathlib import Path

from scripts.text_safe_byte_archive import restore_file

SHA = "67075a32bba202f62a51604d757660f36d4d8115e0b5b250cbb85961ec7a737a"
ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/attachment_archives/integrated_db" / SHA

class HistoricalHabuDbArchiveTests(unittest.TestCase):
    def test_restore_preserves_source_bytes_and_counts(self):
        manifest = json.loads((ARCHIVE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["part_count"], 25)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "source.zip"
            result = restore_file(ARCHIVE, target)
            self.assertTrue(result["byte_exact"])
            self.assertEqual(result["raw_sha256"], SHA)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), SHA)
            with zipfile.ZipFile(target) as z:
                self.assertIsNone(z.testzip())
                files = z.namelist()
                self.assertTrue(any("08-29完全統合版.xlsx" in p for p in files))
                self.assertTrue(any("10-20統合更新版.xlsx" in p for p in files))
                self.assertTrue(any("ハブ" in unicodedata.normalize("NFC", p) and p.endswith(".txt") for p in files))
                records = list(csv.DictReader(io.StringIO(
                    z.read("監査CSV・レポート/全期間イベント統合_2025-2026.csv").decode("utf-8-sig"))))
                new = list(csv.DictReader(io.StringIO(
                    z.read("監査CSV・レポート/新規イベント_2026-09_10.csv").decode("utf-8-sig"))))
                capture = [r for r in new if r["event_class"] == "CAPTURE_HABU"]
                self.assertEqual(len(records), 3853)
                self.assertEqual(len(new), 1117)
                self.assertEqual(len(capture), 67)
                self.assertEqual(sum(r["exploration_night"].startswith("2026-09") for r in capture), 50)
                self.assertEqual(sum(r["exploration_night"].startswith("2026-10") for r in capture), 17)
                self.assertEqual(len({r["dedup_key"] for r in new}), 1117)

if __name__ == "__main__":
    unittest.main()
