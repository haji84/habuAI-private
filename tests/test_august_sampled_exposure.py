import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_august_sampled_exposure import audit,NIGHTS

class SourceContract(unittest.TestCase):
    def test_distinct_12_gpx_nights(self):
        self.assertEqual(len(NIGHTS),12)
        self.assertEqual(len(set(NIGHTS)),12)
        self.assertIn("2026-08-31",NIGHTS)
    def test_real_source_report_remains_candidate_only(self):
        report, rows=audit(ROOT)
        self.assertEqual(report["monthly_baseline_count"],45)
        self.assertFalse(report["aug31_in_existing_day_ledger"])
        self.assertIsNone(report["revised_monthly_count"])
        self.assertFalse(report["aug31_personal_distinct_individuals_certified"])
        self.assertEqual(report["formal_negative_rows"],0)
        self.assertEqual(report["formal_positive_rows"],0)
        self.assertEqual(len(report["nights"]),12)
        self.assertTrue(rows)
        for night in report["nights"]:
            print("AUGUST_EXPOSURE_EVIDENCE", night["night"],
                  "gps_points", night["gps_points"],
                  "sampled_cells", night["sampled_100m_10min_units"],
                  "session_window_cells", night["gps_units_inside_session_window"],
                  "paired_session", night["paired_session_window"],
                  "valid_points", night["qc_pass_samples"], flush=True)
        print("AUGUST_EXPOSURE_TOTAL", report["total_sampled_units"], flush=True)
        self.assertTrue(all(r["observation"]=="UNKNOWN" for r in rows))
        self.assertTrue(all(not r["formal_negative_eligible"] for r in rows))
if __name__=="__main__":unittest.main()
