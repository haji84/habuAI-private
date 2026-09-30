import unittest

import pandas as pd

from scripts.legacy_chronological_walkforward import run_walk_forward


class LegacyChronologicalWalkForwardTests(unittest.TestCase):
    def test_future_nights_never_enter_training(self):
        rows = []
        nights = [
            "2026-08-13",
            "2026-08-15",
            "2026-08-17",
            "2026-08-19",
        ]
        for n_i, night in enumerate(nights):
            for i in range(12):
                rows.append({
                    "operational_night": night,
                    "habu_capture": 1 if i == 0 else 0,
                    "sin_hour": float(i % 2),
                    "cos_hour": float((i + 1) % 2),
                    "mean_speed_mps": float(i),
                    "rain_1h_mm": float(n_i),
                })
        report = run_walk_forward(pd.DataFrame(rows), min_train_nights=2)
        self.assertTrue(report["future_leakage_guard"])
        self.assertEqual(report["folds"][0]["test_night"], "2026-08-17")
        self.assertEqual(
            report["folds"][0]["train_nights"],
            ["2026-08-13", "2026-08-15"],
        )
        for fold in report["folds"]:
            self.assertTrue(all(n < fold["test_night"] for n in fold["train_nights"]))
            self.assertEqual(fold["future_nights_used"], [])

    def test_report_is_explicitly_non_official_legacy_diagnostic(self):
        rows = []
        for night in ["2026-08-13", "2026-08-15", "2026-08-17"]:
            for i in range(10):
                rows.append({
                    "operational_night": night,
                    "habu_capture": int(i == 0),
                    "sin_hour": float(i % 2),
                    "cos_hour": float((i + 1) % 2),
                })
        report = run_walk_forward(pd.DataFrame(rows), min_train_nights=2)
        self.assertEqual(
            report["evaluation_class"],
            "LEGACY_10M_CHRONOLOGICAL_DIAGNOSTIC",
        )
        self.assertFalse(report["official_100m_10min_kpi"])


if __name__ == "__main__":
    unittest.main()
