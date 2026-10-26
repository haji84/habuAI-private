import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.data_access import HabuDataAccess, JST, operational_night, filter_as_of

class DataAccessTests(unittest.TestCase):
    def test_operational_night_uses_0700_boundary(self):
        self.assertEqual(operational_night(datetime(2026, 9, 27, 6, 59, tzinfo=JST)), "2026-09-26")
        self.assertEqual(operational_night(datetime(2026, 9, 27, 7, 0, tzinfo=JST)), "2026-09-27")

    def test_filter_as_of_blocks_future_rows(self):
        cutoff = datetime(2026, 9, 26, 18, 30, tzinfo=JST)
        rows = [
            {"datetime_jst": "2026-09-26T18:20:00+09:00", "v": "past"},
            {"datetime_jst": "2026-09-26T18:40:00+09:00", "v": "future"},
        ]
        self.assertEqual([r["v"] for r in filter_as_of(rows, cutoff)], ["past"])

    def test_missing_processed_files_are_empty_not_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = HabuDataAccess(Path(tmp)).night("2026-09-26")
            self.assertEqual(result["events"], [])
            self.assertEqual(result["captures"], [])

if __name__ == "__main__":
    unittest.main()
