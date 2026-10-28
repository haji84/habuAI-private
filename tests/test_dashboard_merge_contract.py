"""HUB NATURAL merge safety contract: keep PDCA refresh disabled until review."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DashboardMergeContract(unittest.TestCase):
    def test_owner_effort_snapshot(self):
        data = json.loads((ROOT / "dashboard/owner_effort_2026-10-26.json").read_text(encoding="utf-8"))
        text = json.dumps(data, ensure_ascii=False)
        self.assertIn("249", text)
        self.assertIn("97", text)

    def test_no_unreviewed_pdca_auto_trigger(self):
        workflow = (ROOT / ".github/workflows/hub-natural-dashboard.yml").read_text(encoding="utf-8")
        # Never enable workflow_run from the other PR without a trusted-main
        # source review and independent authorization of deployment gates.
        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("HUB_NATURAL_ACCESS_VERIFIED", workflow)

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
