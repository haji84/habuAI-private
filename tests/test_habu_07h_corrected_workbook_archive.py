"""Regression: 07:00 JST boundary and corrected source workbook are immutable."""
import hashlib
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.run_pdca import operational_night
from scripts.text_safe_byte_archive import restore_file

ROOT = Path(__file__).resolve().parents[1]
SHA = "7f0dd533fcf9bc27f2cb797fb63a7cf416973a1c7ce2cb9d90a219d4483824de"
ARCHIVE = ROOT / "data" / "raw" / "attachment_archives" / "integrated_db_workbook_07h" / SHA

class SevenAmCorrectedWorkbookTests(unittest.TestCase):
    def test_seven_am_boundary(self):
        tz = ZoneInfo("Asia/Tokyo")
        cases = [
            (datetime(2026, 9, 29, 0, 19, tzinfo=tz), "2026-09-28"),
            (datetime(2026, 10, 15, 0, 20, tzinfo=tz), "2026-10-14"),
            (datetime(2026, 10, 21, 6, 59, tzinfo=tz), "2026-10-20"),
            (datetime(2026, 10, 21, 7, 0, tzinfo=tz), "2026-10-21"),
        ]
        for point, expected in cases:
            with self.subTest(timestamp=point):
                self.assertEqual(operational_night(point), expected)

    def test_corrected_workbook_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "corrected.xlsx"
            outcome = restore_file(ARCHIVE, path)
            self.assertTrue(outcome["byte_exact"])
            self.assertEqual(outcome["raw_size_bytes"], 813283)
            self.assertEqual(outcome["part_count"], 9)
            self.assertEqual(outcome["raw_sha256"], SHA)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), SHA)

if __name__ == "__main__":
    unittest.main()
