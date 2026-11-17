"""Synthetic, private-only comparisons; no owner capture or GPS rows."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from private_count_clock_comparison import compare_private_sources
from private_pdca_intake import IntakeError


class PrivateCountClockComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.private = self.base / "private"
        self.private.mkdir(mode=0o700)
        (self.private / "models").mkdir(mode=0o700)
        counts = [0, 2, 1, 3, 2, 1, 1]
        self.count = {
            "schema_version": "habu-research-nightcount-poisson-v1.2",
            "nights": len(counts), "owner_captures": sum(counts),
            "elapsed_session_hours_proxy": 35.0,
            "training_nights": [
                {"night": f"2026-10-{day:02d}", "count": k,
                 "effort_hours_proxy": 5.0}
                for day, k in enumerate(counts, 1)
            ],
        }
        prior, newer = [2, 4, 4, 1, 1, 1], [1, 0, 1, 0, 0, 0]
        self.clock = {
            "schema_version": "habu-positive-event-clock-research-v1.2",
            "prior_histogram": prior, "nov_increment_histogram": newer,
            "new_histogram": [a+b for a,b in zip(prior,newer)],
            "alpha_per_bin": 1.0,
            "total_owner_recorded_capture_events_both_years": sum(prior) + sum(newer),
        }
        (self.private / "models" / "count.json").write_text(
            json.dumps(self.count), encoding="utf-8")
        (self.private / "models" / "clock.json").write_text(
            json.dumps(self.clock), encoding="utf-8")

    def test_both_models_are_analyzed_without_promotion(self):
        args = dict(repo_root=self.repo, nightcount="models/count.json",
                    eventclock="models/clock.json")
        one = compare_private_sources(self.private, **args)
        two = compare_private_sources(self.private, **args)
        self.assertEqual(one, two)
        self.assertEqual(one["status"], "RESEARCH_COMPARISON_COMPLETED")
        self.assertEqual(set(one["analyses"]), {"nightcount", "eventclock"})
        self.assertEqual(one["analyses"]["nightcount"]["sample_size"], 2)
        self.assertEqual(one["analyses"]["eventclock"]["sample_size"], 2)
        self.assertFalse(one["production_champion_activated"])
        reports = list((self.private / "research").glob("*.json"))
        self.assertEqual(len(reports), 1)
        body = json.loads(reports[0].read_text(encoding="utf-8"))
        self.assertFalse(body["production_champion_activated"])
        self.assertEqual(body["negative_labels_created"], 0)
        self.assertEqual(body["scientific_future_validation"], "NOT_PERFORMED")
        self.assertNotIn("training_nights", reports[0].read_text(encoding="utf-8"))
        self.assertFalse((self.repo / "research").exists())

    def test_not_an_authentication_bypass(self):
        with self.assertRaises(IntakeError):
            compare_private_sources(self.private, repo_root=self.repo,
                                    nightcount="../untrusted.json")
        with self.assertRaises(IntakeError):
            compare_private_sources(self.private, repo_root=self.repo)
        with self.assertRaises(IntakeError):
            compare_private_sources(self.repo, repo_root=self.repo,
                                    nightcount="models/count.json")

    def test_duplicate_model_keys_are_rejected(self):
        source = self.private / "models" / "count.json"
        source.write_text('{"schema_version":"a","schema_version":"b"}', encoding="utf-8")
        with self.assertRaises(IntakeError):
            compare_private_sources(self.private, repo_root=self.repo,
                                    nightcount="models/count.json")
        self.assertFalse((self.private / "research").exists())

    def test_conflicting_immutable_report_is_rejected(self):
        opts = dict(repo_root=self.repo, nightcount="models/count.json")
        value = compare_private_sources(self.private, **opts)
        report = self.private / "research" / (value["report_id"] + ".json")
        report.write_text('{"altered":true}', encoding="utf-8")
        with self.assertRaises(IntakeError):
            compare_private_sources(self.private, **opts)


if __name__ == "__main__":
    unittest.main()
