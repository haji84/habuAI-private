"""All real GPX 13-source review queue must preserve source gaps and Unknown."""
import sys
from contextlib import redirect_stdout
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_real_13_gpx_review_queue as q

class ReviewQueueOutput(unittest.TestCase):
    def test_cli_refuses_canonical_output_but_preserves_reports(self):
        report = {key: 0 for key in ("raw_gpx_files", "august_raw_gpx_files", "september_raw_gpx_files",
                                    "candidate_capture_mentions", "candidate_spacetime_matched",
                                    "source_backed_nights", "admitted_owner_positive_individuals",
                                    "admitted_negative_units")}
        report["status"] = "SYNTHETIC_ONLY"
        with tempfile.TemporaryDirectory(prefix="queue-output-") as directory:
            root = Path(directory)
            for relative in ("data/raw/source.txt", "predictions/original/P0.json",
                             "reports/review.json"):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic immutable source")
                error = None
                with patch.object(sys, "argv", ["queue", "--root", str(root), "--output", str(path)]), \
                        patch.object(q, "build_queue", return_value=report), redirect_stdout(io.StringIO()):
                    try:
                        self.assertEqual(q.main(), 0)
                    except ValueError as exc:
                        error = exc
                if relative.startswith("reports/"):
                    self.assertIsNone(error)
                    self.assertEqual(json.loads(path.read_bytes()), report)
                else:
                    self.assertEqual(path.read_bytes(), b"synthetic immutable source")
                    self.assertIsNotNone(error)

class ReviewQueue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=q.build_queue(ROOT)

    def test_exact_13_split_and_11_overlap_candidates(self):
        s=self.report
        self.assertEqual(s["raw_gpx_files"],13)
        self.assertEqual(s["august_raw_gpx_files"],12)
        self.assertEqual(s["september_raw_gpx_files"],1)
        self.assertEqual(s["raw_gpx_point_total"],243747)
        self.assertEqual(s["source_backed_nights"],11)
        self.assertEqual(s["candidate_capture_mentions"],30)
        self.assertEqual(s["habu_presence_positive_diagnostic_only"],30)
        self.assertEqual(s["admitted_owner_positive_individuals"],0)
        self.assertEqual(s["candidate_spacetime_matched"],30)

    def test_daily_dashboard_aggregate_never_promoted_to_individual_ground_truth(self):
        s=self.report
        self.assertEqual(s["admitted_owner_positive_individuals"],0)
        self.assertEqual(s["admitted_negative_units"],0)
        self.assertTrue(s["review_queue_open"])
        self.assertFalse(s["model_learning_generated"])
        self.assertFalse(s["formal_walk_forward_performed"])
        self.assertTrue(all(not row["dashboard_is_event_or_individual_proof"] for row in s["night_rows"]))
        self.assertTrue(all(row["unknown_label"] for row in s["night_rows"]))
        self.assertTrue(all(row["eligible_training_negatives"]==0 for row in s["night_rows"]))

    def test_august12_and_august15_capture_statements_correspond_to_source(self):
        nights={x["operational_night"]:x for x in self.report["night_rows"]}
        self.assertEqual(nights["2026-08-12"]["candidate_capture_statements"],4)
        self.assertEqual(nights["2026-08-15"]["candidate_capture_statements"],3)
        self.assertEqual(nights["2026-08-13"]["candidate_capture_statements"],2)
        self.assertEqual(nights["2026-08-17"]["candidate_capture_statements"],2)
        self.assertEqual(nights["2026-09-02"]["candidate_capture_statements"],0)
        self.assertEqual(nights["2026-08-19"]["candidate_capture_statements"],5)
        self.assertEqual(nights["2026-08-28"]["candidate_capture_statements"],4)
        self.assertGreater(nights["2026-08-21"]["source_timestamped_blocks_on_night"],0)
        self.assertEqual(nights["2026-08-21"]["candidate_capture_statements"],0)
        self.assertEqual(nights["2026-08-31"]["source_timestamped_blocks_on_night"],0)
        self.assertEqual(nights["2026-09-02"]["source_timestamped_blocks_on_night"],0)
        self.assertEqual(self.report["previous_extracted_aliases_deduplicated"],11)
        self.assertTrue(all(not n["capture_quantity_and_owner_verified"] for n in nights.values()))

if __name__=="__main__":
    unittest.main()
