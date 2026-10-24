"""PDCA-triggered private dashboard refresh is source-gated and fail-closed."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_capture_dashboard import build, CaptureDataError

ROOT=Path(__file__).resolve().parents[1]

class PdcaDashboardSynchronizationTests(unittest.TestCase):
    def test_owner_readouts_and_capture_totals_are_distinct_from_pdca_science(self):
        data=build(ROOT)
        s=data["owner_chat_statistics"]
        self.assertEqual(data["asof"],"2026-10-24")
        self.assertEqual(data["total"],249)
        self.assertEqual(data["months"][-1]["n"],23)
        self.assertEqual(s["report_nights"],2)
        self.assertEqual(s["reported_capture_events"],6)
        self.assertEqual(s["fauna_sighting_events"],53)
        self.assertEqual(s["fauna_sighting_quantity"],59)
        self.assertEqual(s["roadkill_events"],4)
        self.assertEqual(s["habu_roadkill_events"],2)
        self.assertEqual(s["formal_training_positive_from_review"],0)
        self.assertEqual(s["formal_training_negative_from_review"],0)
        self.assertEqual([x["result"] for x in s["pdca_status_by_night"]],["BLOCKED","BLOCKED"])
        self.assertTrue(all(x["official_p0_scored"] is False for x in s["pdca_status_by_night"]))
        self.assertTrue(s["not_entire_2026_dataset"])
        self.assertEqual(s["gps_gap_nights"],[{"night":"2026-10-24","gap_seconds":4054}])

    def test_canonical_input_only_no_pdca_issue_as_unverified_capture_source(self):
        workflow=(ROOT/".github/workflows/hub-natural-dashboard.yml").read_text(encoding="utf-8")
        self.assertIn('workflows: ["habu-pdca-command"]',workflow)
        self.assertIn("types: [completed]",workflow)
        self.assertIn("head_repository.full_name == github.repository",workflow)
        self.assertIn("data/reconstructions/habu_captures/*-owner-chat-dashboard-intake.json",workflow)
        self.assertIn("HUB_NATURAL_ACCESS_VERIFIED == 'true'",workflow)
        self.assertIn("python scripts/build_capture_dashboard.py",workflow)
        self.assertIn("source_intake_rule",workflow)
        self.assertNotIn("pull-requests: write",workflow)
        self.assertNotIn("pages deploy dashboard/dist --project-name=hub-natural-private --branch=main\n  verify-build",workflow)

    def test_source_timestamps_and_unverified_scientific_labels(self):
        for night,individuals in (("2026-10-22",2),("2026-10-24",4)):
            p=ROOT/f"data/reconstructions/habu_captures/{night}-owner-chat-dashboard-intake.json"
            info=json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(info["operational_night"],night)
            self.assertEqual(len(info["capture_events"]),individuals)
            self.assertEqual(info["source"]["kind"],"owner_habu_log_chat_transcript")
            self.assertFalse(info["source"]["native_log_bytes_archived"])
            self.assertFalse(info["source"]["gpx_original_archived_in_repo"])
            self.assertFalse(info["scientific_restrictions"]["complete_capture_outcomes_certified"])
            self.assertFalse(info["scientific_restrictions"]["actual_searched_road_scopes_certified"])
            self.assertEqual(info["scientific_restrictions"]["eligible_learning_negative_count"],0)

if __name__=="__main__":
    unittest.main()
