"""11 genuinely indexed August nights: time/location GPS corroboration, no fake labels."""
import hashlib
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import recover_remaining_august_nights as rem


class RemainingAugustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=rem.recover(ROOT)
        cls.by_date={d["night"]:d for d in cls.report["nights"]}

    def test_expected_remaining_nights_and_source(self):
        self.assertEqual(set(self.by_date),set(rem.TARGETS))
        self.assertEqual(len(self.by_date),11)
        self.assertEqual(self.report["library_read_line_count"],10506)
        self.assertFalse(self.report["native_original_txt_bytes_verified"])
        self.assertEqual(self.report["source_file_sha256"],
            hashlib.sha256((ROOT/rem.SOURCE).read_bytes()).hexdigest())
        self.assertEqual(self.report["final_positive_training_rows"],0)
        self.assertEqual(self.report["final_negative_training_rows"],0)
        self.assertFalse(self.report["p0_retroactively_issued"])

    def test_known_early_nights_still_match_previous_source_reconciliation(self):
        # Previous independent 8/17 Library read documented these encounter blocks.
        for night,mentions in [("2026-08-13",2),("2026-08-15",3),("2026-08-17",2)]:
            self.assertEqual(self.by_date[night]["capture_mentions"],mentions)
            self.assertEqual(self.by_date[night]["capture_gpx_matched"],mentions)

    def test_no_capture_statement_becomes_exact_count_without_native_explicit_quantity(self):
        for n in self.report["nights"]:
            self.assertEqual(n["positive_labels"],
                 "EXPLICIT_CAPTURE_EVENT_CANDIDATES_NOT_OWNER_INDIVIDUALS")
            self.assertEqual(n["negative_labels"],
                 "UNKNOWN_NO_VERIFIED_COMPLETE_SEARCH_EFFORT")
            self.assertFalse(n["official_training_eligible"])
            for e in n["events"]:
                self.assertEqual(hashlib.sha256(e["source_block"].encode()).hexdigest(),
                                 e["block_sha256"])
                if e["event_type"]!="capture":
                    self.assertEqual(e["capture_mention_lower_bound"],0)

    def test_07_am_boundary_and_roadkill_separation(self):
        self.assertEqual(rem._night(rem._clock("2026/08/14 0:32")),"2026-08-13")
        self.assertEqual(rem._night(rem._clock("2026/08/14 7:00")),"2026-08-14")
        self.assertEqual(rem._night(rem._clock("2026/09/01 1:29")),"2026-08-31")
        for rec in self.report["nights"]:
            self.assertGreater(rec["gpx_points"],0)
            self.assertLessEqual(rec["capture_gpx_matched"],rec["capture_mentions"])
            self.assertGreaterEqual(rec["roadkill_events"],rec["habu_roadkill_events"])

    def test_baseline_absence_is_not_zero(self):
        for night in ("2026-08-21","2026-08-31"):
            self.assertIsNone(self.by_date[night]["dashboard_day_count"])
            self.assertIn("NO_DAY_LEVEL_BASELINE_NOT_ZERO_CAPTURE",self.by_date[night]["source_limitations"])


if __name__=="__main__":
    unittest.main()
