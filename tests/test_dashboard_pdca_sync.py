"""Independent source-grade test: PR #92 evidence reconciles with PR #136 once.

PDCA science status does not authorize prediction accuracy or training labels.
"""
import json
import unittest
from pathlib import Path

from scripts.build_capture_dashboard import build

ROOT = Path(__file__).resolve().parents[1]

class PdcaDashboardSourceReconciliationTests(unittest.TestCase):
    def test_owner_tally_matches_source_and_does_not_double_add(self):
        payload = build(ROOT)
        self.assertEqual(payload["asof"], "2026-10-30")
        self.assertEqual(payload["total"], 262)
        self.assertEqual(payload["months"][-1]["n"], 36)
        self.assertEqual(payload["months"][0]["n"], 10)
        nights = {r["night"]: r for r in payload["nights"]}
        self.assertEqual(nights["2026-10-22"]["count"], 2)
        self.assertEqual(nights["2026-10-24"]["count"], 4)
        self.assertEqual(nights["2026-10-26"]["count"], 3)
        self.assertEqual(nights["2026-10-28"]["count"], 2)
        self.assertEqual(nights["2026-10-29"]["count"], 2)
        self.assertEqual(nights["2026-10-30"]["count"], 6)
        self.assertEqual(sum(x["count"] for x in payload["nights"]), 262)
        self.assertEqual(payload["effort"]["total_nights"], 101)

    def test_source_level_pdca_is_not_scientific_validation(self):
        payload = build(ROOT)
        stats = payload["owner_chat_statistics"]
        self.assertEqual(stats["report_nights"], 2)
        self.assertEqual(stats["reported_capture_events"], 6)
        self.assertEqual(stats["fauna_sighting_events"], 53)
        self.assertEqual(stats["fauna_sighting_quantity"], 59)
        self.assertEqual(stats["roadkill_events"], 4)
        self.assertEqual(stats["habu_roadkill_events"], 2)
        self.assertEqual(stats["formal_training_positive_from_review"], 0)
        self.assertEqual(stats["formal_training_negative_from_review"], 0)
        self.assertEqual(stats["gps_gap_nights"], [{"night": "2026-10-24", "gap_seconds": 4054}])
        self.assertEqual([x["result"] for x in stats["pdca_status_by_night"]], ["BLOCKED", "BLOCKED"])
        self.assertTrue(all(x["official_p0_scored"] is False for x in stats["pdca_status_by_night"]))
        self.assertEqual(
            stats["owner_capture_size_distribution"],
            {"小型": 4, "超大型": 1, "かなり大型": 1},
        )
        self.assertEqual(
            stats["capture_road_surface_distribution"], {"ウエット": 3, "ドライ": 3}
        )

    def test_source_receipts_are_deidentified_and_provisional(self):
        for night, n in (("2026-10-22", 2), ("2026-10-24", 4)):
            path = ROOT / "data/reconstructions/habu_captures" / (
                night + "-owner-chat-dashboard-intake.json"
            )
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(doc["operational_night"], night)
            self.assertEqual(len(doc["capture_events"]), n)
            self.assertEqual(doc["source"]["kind"], "owner_habu_log_chat_transcript")
            self.assertFalse(doc["scientific_restrictions"]["individual_identity_independently_certified"])
            self.assertFalse(doc["scientific_restrictions"]["complete_capture_outcomes_certified"])
            self.assertFalse(doc["scientific_restrictions"]["actual_searched_road_scopes_certified"])
            self.assertEqual(doc["scientific_restrictions"]["eligible_learning_negative_count"], 0)
            self.assertEqual(doc["scientific_restrictions"]["eligible_learning_positive_count"], 0)
            for event in doc["capture_events"]:
                self.assertFalse({"lat", "lon", "address", "place", "coordinates"}.intersection(event))

    def test_public_repo_disables_artifact_and_manual_deploy(self):
        workflow = (ROOT / ".github/workflows/hub-natural-dashboard.yml").read_text(encoding="utf-8")
        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("data/reconstructions/habu_captures/", workflow)
        self.assertIn("if: ${{ false }}", workflow)
        self.assertNotIn("pull-requests: write", workflow)

if __name__ == "__main__":
    unittest.main()
