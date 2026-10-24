import sys
import json
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
        self.assertEqual(len(report["aug31_candidate_events"]),2)
        self.assertEqual({e["source_native_time"] for e in report["aug31_candidate_events"]},
                         {"2026/08/31 21:43","2026/09/01 1:17"})
        self.assertEqual(len({e["source_block_sha256"] for e in report["aug31_candidate_events"]}),2)
        self.assertTrue(all(e["gpx_proximity"]["status"]=="ACTUAL_GPX_SPACETIME_CORROBORATED"
                            for e in report["aug31_candidate_events"]))
        self.assertTrue(all(e["decision"]=="UNRESOLVED"
                            for e in report["aug31_candidate_events"]))
        self.assertEqual(report["formal_negative_rows"],0)
        self.assertEqual(report["formal_positive_rows"],0)
        self.assertEqual(len(report["nights"]),12)
        self.assertEqual(report["total_sampled_units"],8965)
        self.assertEqual(report["total_session_window_units"],6694)
        self.assertEqual(report["session_covered_nights"],9)
        self.assertEqual(set(report["gps_nights_with_max_sampling_gap_over_60s"]),
                         {"2026-08-13","2026-08-21","2026-08-29"})
        self.assertEqual({n["night"] for n in report["nights"] if not n["paired_session_window"]},
                         {"2026-08-12","2026-08-13","2026-08-29"})
        self.assertTrue(all(not n["complete_capture_outcomes_attested"] for n in report["nights"]))
        self.assertEqual(next(n for n in report["nights"] if n["night"]=="2026-08-19")["source_capture_individuals_lower_bound"],6)
        self.assertIsNone(next(n for n in report["nights"] if n["night"]=="2026-08-31")["baseline_owner_capture_count"])
        self.assertTrue(all(n["raw_gpx_gaps_over_300_s"]==0 for n in report["nights"]))
        self.assertTrue(rows)
        for night in report["nights"]:
            print("AUGUST_EXPOSURE_EVIDENCE", night["night"],
                  "gps_points", night["gps_points"],
                  "sampled_cells", night["sampled_100m_10min_units"],
                  "session_window_cells", night["gps_units_inside_session_window"],
                  "paired_session", night["paired_session_window"],
                  "valid_points", night["qc_pass_samples"],
                  "max_gap_s", night["raw_gpx_max_sampling_gap_s"],
                  "gaps_over_30s", night["raw_gpx_gaps_over_30_s"],
                  "reported_capture_events", night["source_capture_event_mentions"],
                  "capture_lower_bound", night["source_capture_individuals_lower_bound"],
                  "baseline_count", night["baseline_owner_capture_count"],
                  "blockers", ",".join(night["blockers"]), flush=True)
        print("AUGUST_EXPOSURE_TOTAL", report["total_sampled_units"], flush=True)
        self.assertTrue(all("COMPLETE_OWNER_CAPTURE_OUTCOMES_NOT_ATTESTED" in n["blockers"]
                            for n in report["nights"]))
        self.assertTrue(all(r["observation"]=="UNKNOWN" for r in rows))
        self.assertTrue(all(not r["formal_negative_eligible"] for r in rows))
        receipt=json.loads((ROOT/"evidence/recovered_sources/2026-08-12night-sampled-exposure-ci-receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["totals"]["raw_gpx_points"],231715)
        self.assertEqual(receipt["totals"]["kept_samples"],225219)
        self.assertEqual(receipt["totals"]["sampled_spacetime_units"],8965)
        self.assertEqual(receipt["totals"]["inside_paired_session_units"],6694)
        self.assertFalse(receipt["complete_owner_capture_outcomes_certified"])
        self.assertFalse(receipt["active_road_search_certified"])
        stored={n["night"]:n for n in receipt["nights"]}
        self.assertEqual(len(stored),12)
        for n in report["nights"]:
            prior=stored[n["night"]]
            self.assertEqual(n["gps_points"],prior["raw_gpx_points"])
            self.assertEqual(n["qc_pass_samples"],prior["gps_qa_kept_samples"])
            self.assertEqual(n["sampled_100m_10min_units"],prior["sampled_100m_10m_units"])
            self.assertEqual(n["gps_units_inside_session_window"],prior["fully_inside_paired_session_units"])
            self.assertEqual(n["paired_session_window"],prior["paired_session_markers"])
            self.assertEqual(n["source_sha256"],prior["source_gpx_sha256"])
            self.assertAlmostEqual(n["raw_gpx_max_sampling_gap_s"],prior["independent_qc_max_gap_seconds"],places=2)
if __name__=="__main__":unittest.main()
