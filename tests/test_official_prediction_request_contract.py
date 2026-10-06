import unittest
from pathlib import Path


class OfficialPredictionRequestContractTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_agents_forbid_manual_today_prediction_shortcut(self):
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("OFFICIAL PREDICTION REQUEST", text)
        self.assertIn("今日の予想", text)
        self.assertIn("PROVISIONAL_NOT_FREEZABLE", text)
        self.assertIn("Never present or Freeze a hand-built narrative estimate as P0", text)

    def test_normative_contract_requires_canonical_execution(self):
        text = (
            self.root / "docs/specs/official-prediction-request-execution.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Status: Normative", text)
        self.assertIn("run Habu AI and return its current official forecast", text)
        self.assertIn("terrain wind shielding / exposure", text)
        self.assertIn("recent capture pressure", text)
        self.assertIn("ForecastUniverse reference/hash", text)
        self.assertIn("MODEL_INFERENCE_BLOCKED", text)
        self.assertIn("ROUTE_OPTIMIZER_BLOCKED", text)

    def test_freeze_spec_rejects_bypassed_manual_estimate(self):
        text = (
            self.root / "docs/specs/prediction-freeze-versioning.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Official prediction request execution gate", text)
        self.assertIn("not eligible for P0 Freeze", text)
        self.assertIn("PROVISIONAL_NOT_FREEZABLE", text)


if __name__ == "__main__":
    unittest.main()
