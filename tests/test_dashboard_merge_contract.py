"""HUB NATURAL merge safety contract: keep PDCA refresh disabled until review."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DashboardMergeContract(unittest.TestCase):
    def test_owner_effort_snapshot(self):
        data = json.loads((ROOT / "dashboard/owner_effort_2026-10-26.json").read_text(encoding="utf-8"))
        expected = data["expected"]
        self.assertEqual(expected["total_captures"], 249)
        self.assertEqual(expected["effort_nights"], 97)
        self.assertEqual(expected["positive_nights"], 86)
        self.assertEqual(expected["zero_nights"], 11)
        self.assertEqual(sum(m["captures"] for m in data["monthly_expected"]), 249)
        self.assertEqual(sum(m["nights"] for m in data["monthly_expected"]), 97)
        self.assertEqual(sum(m["positive"] for m in data["monthly_expected"]), 86)
        self.assertEqual(sum(m["zero"] for m in data["monthly_expected"]), 11)
        self.assertTrue(all(m["positive"] + m["zero"] == m["nights"] for m in data["monthly_expected"]))
        self.assertEqual(len(data["confirmed_zero_nights"]), 11)
        self.assertEqual(len(set(data["confirmed_zero_nights"])), 11)
        self.assertFalse(set(data["confirmed_zero_nights"]) & set(data["excluded_effort_nights"]))

    def test_no_unreviewed_pdca_auto_trigger(self):
        workflow = (ROOT / ".github/workflows/hub-natural-dashboard.yml").read_text(encoding="utf-8")
        # Never enable workflow_run from the other PR without a trusted-main
        # source review and independent authorization of deployment gates.
        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("if: ${{ false }}", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("deploy-protected:", workflow)
        self.assertGreaterEqual(workflow.count("if: ${{ false }}"), 2)

    def test_no_precise_location_in_owner_effort_snapshot(self):
        data = json.loads((ROOT / "dashboard/owner_effort_2026-10-26.json").read_text(encoding="utf-8"))
        forbidden = {"lat", "lon", "latitude", "longitude", "coordinates", "gps", "gpx", "route", "address"}
        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(k.lower() for k in value))
                for v in value.values(): walk(v)
            elif isinstance(value, list):
                for v in value: walk(v)
        walk(data)

if __name__ == "__main__":
    unittest.main()
