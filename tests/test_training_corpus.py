"""Training read/selection + logistic fit regressions (synthetic data only)."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from master_contracts import canonical_bytes, digest
from training_corpus import select_training_rows
from train_spacetime_candidate import fit_candidate
from prospective_spacetime import _read_candidate_model


class AuditedTrainingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        p = self.root / "evidence/source_receipt.txt"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"actual receipt bytes stand-in")
        self.source_sha = hashlib.sha256(p.read_bytes()).hexdigest()
        self.rows = []
        for i, (night, label) in enumerate([
            ("2026-09-10", 1), ("2026-09-11", 0),
            ("2026-09-12", 1), ("2026-09-12", 0),
        ]):
            self.rows.append({
                "row_id": f"row-{i}", "night": night,
                "cell_x": 4000 + i, "cell_y": 30000,
                "window_start_jst": night + f"T21:{i*10:02d}:00+09:00",
                "observation": "capture_observed" if label else "observed_negative",
                "label": label, "quality": "AUDITED_OBSERVED",
                "search_role": "SEARCH",
                "all_captures_recorded": True,
                "gpx_segment_eligible": True,
                "capture_event_ids": [f"CAP-{i}"] if label else [],
                "label_available_at": "2026-09-30T12:00:00+09:00",
                "audit_available_at": "2026-09-30T13:00:00+09:00",
                "source_refs": ["evidence/source_receipt.txt"],
                "outcome_source_ref": "evidence/source_receipt.txt",
                "features": {"road_length_m": float(8 + i)},
                "feature_available_at": {"road_length_m": "2026-09-30T12:00:00+09:00"},
                "feature_valid_for_night": True,
            })
        self.corpus = {
            "schema_version": "1.0",
            "qualification": "AUDITED_TRAIN_ONLY",
            "source_manifest": [{
                "path": "evidence/source_receipt.txt", "sha256": self.source_sha,
                "received_at": "2026-09-30T12:00:00+09:00",
            }],
            "rows": self.rows,
        }
        self.publish()

    def publish(self):
        name = "data/processed/observations.json"
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = canonical_bytes(self.corpus) + b"\n"
        target.write_bytes(raw)
        self.path, self.sha = name, hashlib.sha256(raw).hexdigest()

    def select(self, *, night="2026-10-20", cutoff="2026-10-19T19:00:00+09:00",
               exposed=()):
        return select_training_rows(
            self.root, self.path, self.sha, night, cutoff,
            require_features=("road_length_m",), exposed_nights=exposed,
        )

    def add_development_holdout(self, *, observation="capture_observed"):
        source_path = self.root / "evidence/future_observation.txt"
        source_path.write_bytes(b"synthetic later observation source")
        self.corpus["source_manifest"].append({
            "path": "evidence/future_observation.txt",
            "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "received_at": "2026-10-21T11:00:00+09:00",
        })
        heldout = {
            "row_id": "future-fold-row", "night": "2026-10-20",
            "cell_x": 4100, "cell_y": 30000,
            "window_start_jst": "2026-10-20T21:00:00+09:00",
            "observation": observation,
            "label": 1 if observation == "capture_observed" else None,
            "quality": "AUDITED_OBSERVED" if observation == "capture_observed" else "UNKNOWN",
            "search_role": "SEARCH", "all_captures_recorded": True,
            "gpx_segment_eligible": True,
            "capture_event_ids": ["CAP-NEW-FOLD"] if observation == "capture_observed" else [],
            "label_available_at": "2026-10-21T12:00:00+09:00",
            "audit_available_at": "2026-10-21T13:00:00+09:00",
            "source_refs": ["evidence/future_observation.txt", "evidence/source_receipt.txt"],
            "outcome_source_ref": "evidence/future_observation.txt",
            "features": {"road_length_m": 13.0},
            "feature_available_at": {"road_length_m": "2026-09-30T12:00:00+09:00"},
            "feature_valid_for_night": True,
        }
        self.rows.append(heldout)
        self.publish()
        return heldout

    def test_later_development_fold_is_descriptive_not_independent_confirmation(self):
        from development_walkforward import evaluate_development_folds
        self.add_development_holdout()
        result = evaluate_development_folds(
            self.root, self.path, self.sha, ("2026-10-20",),
            ("road_length_m",), "2026-10-21T22:00:00+09:00")
        self.assertEqual(result["status"], "RETROSPECTIVE_DEVELOPMENT_ONLY")
        self.assertEqual(result["eligible_evaluated_nights"], 1)
        self.assertEqual(result["folds"][0]["observed_units"], 1)
        self.assertEqual(result["independent_confirmation"], "NOT_PERFORMED")
        self.assertFalse(result["official_accuracy_evaluated"])
        self.assertEqual(result["stage1_top10_recall"], "NOT_EVALUATED")

    def test_development_walkforward_does_not_score_unknown_holdout(self):
        from development_walkforward import evaluate_development_folds
        self.add_development_holdout(observation="UNKNOWN")
        result = evaluate_development_folds(
            self.root, self.path, self.sha, ("2026-10-20",),
            ("road_length_m",), "2026-10-21T22:00:00+09:00")
        self.assertEqual(result["status"], "NEED_MORE_DATA")
        self.assertEqual(result["eligible_evaluated_nights"], 0)
        self.assertEqual(result["folds"][0]["unknown_units"], 1)

    def test_development_walkforward_cannot_reuse_later_received_sources(self):
        from development_walkforward import evaluate_development_folds
        r = evaluate_development_folds(
            self.root, self.path, self.sha, ("2026-09-20",),
            ("road_length_m",), "2026-10-21T22:00:00+09:00")
        self.assertEqual(r["status"], "NEED_MORE_DATA")
        self.assertEqual(r["folds"][0]["training_counts"]["accepted_rows"], 0)

    def test_prior_verified_eligible_rows_can_fit_nonofficial_candidate(self):
        rows = self.select()
        self.assertEqual(rows["status"], "DEVELOPMENT_TRAINING_ELIGIBLE")
        self.assertEqual(rows["counts"]["accepted_rows"], 4)
        self.assertEqual(rows["counts"]["nights"], 3)
        result = fit_candidate(rows)
        self.assertEqual(result["status"], "DEVELOPMENT_FIT_ONLY")
        self.assertEqual(result["independent_confirmation"], "NOT_PERFORMED")
        self.assertFalse(result["official_issuance_authorized"])
        self.assertLessEqual(result["fit_evidence"]["iterations"], 400)
        model = result["model"]
        self.assertEqual(model["training_data_sha256"], rows["selection_sha256"])
        self.assertEqual(model["feature_schema_sha256"], digest(["road_length_m"]))
        self.assertEqual(model["model_sha256"], digest({k: v for k, v in model.items() if k != "model_sha256"}))
        file = self.root / "models/candidates/from-training.json"
        file.parent.mkdir(parents=True)
        raw = canonical_bytes(model) + b"\n"
        file.write_bytes(raw)
        retrieved = _read_candidate_model(
            self.root, "models/candidates/from-training.json",
            hashlib.sha256(raw).hexdigest(),
        )
        self.assertEqual(retrieved, model)
        self.assertFalse((self.root / "predictions/original").exists())

    def test_later_received_history_must_not_train_earlier_fold(self):
        result = self.select(night="2026-09-20", cutoff="2026-09-19T19:00:00+09:00")
        self.assertEqual(result["status"], "NEED_MORE_DATA")
        self.assertEqual(result["counts"]["accepted_rows"], 0)
        self.assertTrue(all("SOURCE_RECEIVED_AFTER_FIT" in r["reasons"] for r in result["rejected"]))
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            fit_candidate(result)

    def test_research_exposed_night_is_excluded_not_claimed_confirmation(self):
        result = self.select(exposed=("2026-09-12",))
        self.assertEqual(result["status"], "NEED_MORE_DATA")
        self.assertEqual(result["counts"]["accepted_rows"], 2)
        self.assertTrue(any("NOT_PRIOR_TRAINING_NIGHT" in item["reasons"] for item in result["rejected"]))

    def test_unqualified_non_capture_passage_never_turns_into_negative(self):
        self.rows[1]["search_role"] = "UNKNOWN"
        self.publish()
        result = self.select()
        self.assertEqual(result["counts"]["negatives"], 1)
        self.assertIn("UNVERIFIED_NEGATIVE_EXPOSURE", result["rejected"][0]["reasons"])
        self.assertEqual(result["status"], "NEED_MORE_DATA")

    def test_unknown_is_not_negative(self):
        self.rows[1].update(observation="UNKNOWN", label=None, capture_event_ids=[])
        self.publish()
        r = self.select()
        self.assertEqual(r["counts"]["negatives"], 1)
        self.assertEqual(r["status"], "NEED_MORE_DATA")
        self.assertIn("UNKNOWN_NOT_NEGATIVE", r["rejected"][0]["reasons"])

    def test_repeated_capture_id_even_in_excluded_row_is_error(self):
        self.rows[2]["capture_event_ids"] = self.rows[0]["capture_event_ids"]
        self.publish()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.select()

    def test_missing_historic_feature_validity_blocks_fit(self):
        self.rows[0]["feature_valid_for_night"] = False
        self.publish()
        result = self.select()
        self.assertEqual(result["status"], "NEED_MORE_DATA")
        self.assertTrue(any("FEATURE_HISTORICAL_VALIDITY_UNPROVEN" in r["reasons"]
                            for r in result["rejected"]))

    def test_time_equal_to_fit_boundary_never_trains(self):
        self.rows[0]["audit_available_at"] = "2026-10-19T19:00:00+09:00"
        self.publish()
        r = self.select()
        self.assertEqual(r["counts"]["accepted_rows"], 3)
        self.assertIn("AUDIT_AVAILABLE_AT_NOT_READY_FOR_FIT", r["rejected"][0]["reasons"])

    def test_observation_source_cannot_predate_capture_event(self):
        self.add_development_holdout()
        self.corpus["source_manifest"][-1]["received_at"] = "2026-10-20T20:00:00+09:00"
        self.publish()
        with self.assertRaisesRegex(ValueError, "Outcome source timing"):
            self.select(night="2026-10-22", cutoff="2026-10-21T23:00:00+09:00")

    def test_duplicate_spacetime_unit_with_distinct_row_ids_rejected(self):
        row = self.rows[1]
        row["night"] = self.rows[0]["night"]
        row["window_start_jst"] = self.rows[0]["window_start_jst"]
        row["cell_x"] = self.rows[0]["cell_x"]
        row["cell_y"] = self.rows[0]["cell_y"]
        self.publish()
        with self.assertRaisesRegex(ValueError, "Duplicate or conflicting 100m"):
            self.select()

    def test_same_spacetime_in_different_timezone_spelling_is_duplicate(self):
        row = self.rows[1]
        row["night"] = self.rows[0]["night"]
        row["window_start_jst"] = "2026-09-10T12:00:00Z"
        row["cell_x"] = self.rows[0]["cell_x"]
        row["cell_y"] = self.rows[0]["cell_y"]
        self.publish()
        with self.assertRaisesRegex(ValueError, "Duplicate or conflicting 100m"):
            self.select()

    def test_missing_spatial_unit_is_not_training_evidence(self):
        self.rows[0].pop("cell_x")
        self.publish()
        with self.assertRaisesRegex(ValueError, "integer 100m observation cell"):
            self.select()

    def test_source_bytes_changed_in_place_rejected(self):
        (self.root / "evidence/source_receipt.txt").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.select()

    def test_stale_or_forged_selection_is_not_sufficient(self):
        selected = self.select()
        selected["accepted"][0]["label"] = 1 - selected["accepted"][0]["label"]
        with self.assertRaisesRegex(ValueError, "Unbound"):
            fit_candidate(selected)

    def test_selection_hash_binds_source_receipts_and_fit_boundary(self):
        first = self.select()
        self.assertEqual(first["status"], "DEVELOPMENT_TRAINING_ELIGIBLE")
        modified = self.select(night="2026-10-22", cutoff="2026-10-21T19:00:00+09:00")
        self.assertEqual(first["accepted"], modified["accepted"])
        self.assertNotEqual(first["selection_sha256"], modified["selection_sha256"])
        fitted = fit_candidate(first)
        self.assertEqual(fitted["model"]["training_data_sha256"], first["selection_sha256"])

    def test_tampered_selection_provenance_fails_fitter(self):
        selection = self.select()
        selection["source_received_at"]["evidence/source_receipt.txt"] = (
            "2026-09-01T12:00:00+09:00")
        with self.assertRaisesRegex(ValueError, "Unbound"):
            fit_candidate(selection)

    def test_naive_or_future_fit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Naive"):
            self.select(cutoff="2026-10-19T19:00:00")
        with self.assertRaisesRegex(ValueError, "Fit cutoff"):
            self.select(cutoff="2026-10-20T07:00:00+09:00")
        with self.assertRaisesRegex(ValueError, "Fit cutoff"):
            self.select(cutoff="2026-10-20T08:00:00+09:00")


if __name__ == "__main__":
    unittest.main()
