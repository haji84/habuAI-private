"""Candidate model learns measured exposed road-time units, never hindsight weather."""
import copy
import hashlib
import json
import math
import sys
import tempfile
import unittest
from statistics import mean
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import prospective_candidate_model as p

IDENTITY = ("accepted", "corpus_sha256", "source_sha256", "source_received_at",
            "heldout_night", "fit_cutoff", "feature_names", "exposed_nights")


def rebind(selection):
    raw = json.dumps({key: selection[key] for key in IDENTITY}, sort_keys=True,
                     separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    selection["selection_sha256"] = hashlib.sha256(raw).hexdigest()
    return selection


def selection_for(history):
    """Synthetic serialized gate fixture; not authentication of source bytes."""
    accepted = []
    for index, row in enumerate(history):
        x, y = (int(part) for part in row["cell_id"].split("_")[-2:])
        label = int(row.get("owner_capture_count", 0) > 0)
        accepted.append({
            "row_id": f"fixture-{index}", "night": row["operational_night"],
            "cell_x": x, "cell_y": y, "window_start_jst": row["window_start_jst"],
            "label": label, "features": {name: row[name] for name in p.FEATURES},
            "capture_event_ids": [f"fixture-event-{index}"] if label else [],
        })
    accepted.sort(key=lambda row: (row["night"], row["window_start_jst"], row["row_id"]))
    positives = sum(row["label"] for row in accepted)
    return rebind({
        "status": "DEVELOPMENT_TRAINING_ELIGIBLE",
        "qualification": "RETROSPECTIVE_TRAIN_ONLY_NOT_CONFIRMATION",
        "official_issuance_authorized": False,
        "accepted": accepted, "rejected": [], "blockers": [],
        "counts": {"accepted_rows": len(accepted), "rejected_rows": 0,
                   "nights": len({row["night"] for row in accepted}),
                   "positives": positives, "negatives": len(accepted) - positives},
        "corpus_sha256": "c" * 64,
        "source_sha256": {"features/fixture.json": "a" * 64,
                          "evidence/fixture.json": "b" * 64},
        "source_received_at": {"features/fixture.json": "2026-09-30T12:00:00+09:00",
                               "evidence/fixture.json": "2026-10-09T12:00:00+09:00"},
        "heldout_night": "2026-10-11", "fit_cutoff": "2026-10-10T00:00:00+09:00",
        "feature_names": sorted(p.FEATURES), "exposed_nights": [],
    })


def fit_rows(rows=None, **kwargs):
    rows = history_rows() if rows is None else rows
    return p.train_candidate(rows, training_selection=selection_for(rows), **kwargs)


def history_rows():
    rows = []
    base = datetime.fromisoformat("2026-10-01T00:00:00+09:00")
    for n in range(7):
        date = (base + timedelta(days=n)).date().isoformat()
        later = (base + timedelta(days=n+1)).date().isoformat()
        for cell in range(4):
            rows.append({
                "operational_night": date,
                "cell_id": f"utm52n_100m_{5000+cell}_{31000+n}",
                "window_start_jst": date + "T21:00:00+09:00",
                "forecast_cutoff": date + "T18:00:00+09:00",
                "features_available_at": date + "T17:00:00+09:00",
                "weather_source_role": "EX_ANTE_FORECAST",
                "features_source_sha256": "a"*64,
                "exposure_proof": "GPX_PASSAGE_VALIDATED",
                "outcome_source_sha256": "b"*64,
                "owner_capture_count": 1 if cell == n % 4 else 0,
                "outcome_available_at": later + "T09:00:00+09:00",
                "temperature_c": 21.0+cell, "humidity_pct": 85.0,
                "precipitation_mm": 0.1*n, "slope_deg": 12.0+cell,
                "tpi_m": -3.0+cell, "road_length_m": 30.0+cell,
                "wind_cross_road_proxy": 0.5,
            })
    return rows


def future_row():
    row = copy.deepcopy(history_rows()[0])
    row.update(operational_night="2026-10-24",
               window_start_jst="2026-10-24T21:00:00+09:00",
               forecast_cutoff="2026-10-24T16:00:00+09:00",
               features_available_at="2026-10-24T15:00:00+09:00")
    for key in ("exposure_proof", "owner_capture_count", "outcome_available_at",
                "outcome_source_sha256"):
        row.pop(key)
    return row


def seal_model(model):
    model.pop("model_sha256", None)
    raw = json.dumps(model, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=True).encode()
    model["model_sha256"] = hashlib.sha256(raw).hexdigest()
    return model


# Immutable pre-extraction oracle, not a second maintained implementation.
# Exact src/prospective_candidate_model.py from this commit/Git blob. The local
# text fixture is verified before compile; no test needs Git, network or a
# platform hash allowlist. read_text normalizes checkout CRLF to Git's LF bytes.
LEGACY_REFERENCE_COMMIT = 'd9bd4d66e61ac20a4491230d2f5faec8634dff8f'
LEGACY_REFERENCE_BLOB = '978c97c0fff6e89f57dda28430c92cc6ee80f716'
LEGACY_REFERENCE_SHA256 = 'aac9841c2013569966bc16ab2bb914ae893e873d8f299aa74a411db3a876a01a'


def legacy_reference():
    path = ROOT / 'tests/fixtures/prospective_candidate_model_d9bd4d66.py.txt'
    source = path.read_text(encoding='utf-8')
    if hashlib.sha256(source.encode('utf-8')).hexdigest() != LEGACY_REFERENCE_SHA256:
        raise AssertionError('Immutable pre-extraction reference source digest changed')
    namespace = {'__name__': '_pinned_legacy_prospective_candidate', '__file__': str(path)}
    exec(compile(source, str(path), 'exec'), namespace)
    return namespace


def legacy_reference_fit(rows=None):
    rows = history_rows() if rows is None else rows
    return legacy_reference()['train_candidate'](rows,
        training_cutoff='2026-10-10T00:00:00+09:00', training_selection=selection_for(rows))


class CandidateModelIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = fit_rows(training_cutoff="2026-10-10T00:00:00+09:00")

    def rank(self, model):
        return p.rank_future(model, [future_row()],
                             issued_at="2026-10-24T17:00:00+09:00",
                             operational_night="2026-10-24")

    def test_changed_coefficients_with_unchanged_digest_are_rejected_before_scoring(self):
        model = copy.deepcopy(self.valid)
        model["coefficients"][0] += 10
        with patch.object(p, "_score", wraps=p._score) as score:
            with self.assertRaises(p.CandidateInputError):
                self.rank(model)
            score.assert_not_called()

    def test_rehashed_invalid_vectors_order_and_authority_are_rejected(self):
        changes = (
            ("means", self.valid["means"][:-1]),
            ("means", self.valid["means"] + [1.0]),
            ("scales", []), ("scales", [0.0] * 7), ("scales", [-1.0] * 7),
            ("scales", [True] * 7), ("scales", [float("inf")] * 7),
            ("means", [False] * 7), ("means", [float("nan")] * 7),
            ("coefficients", self.valid["coefficients"][:-1]),
            ("coefficients", self.valid["coefficients"] + [1.0]),
            ("coefficients", [True] * 8), ("coefficients", [float("nan")] * 8),
            ("feature_names", list(reversed(p.FEATURES))),
            ("schema_version", "habu-prospective-candidate-v999"),
            ("production_activation_authorized", True),
            ("production_activation_authorized", 0),
            ("official_stage1_recall_computed", True),
            ("official_100m_10min_kpi_computed", True),
            ("immutable_original_issued", True),
        )
        for field, value in changes:
            model = seal_model(dict(copy.deepcopy(self.valid), **{field: value}))
            with self.subTest(field=field, value=repr(value)), \
                    patch.object(p, "_score", wraps=p._score) as score:
                with self.assertRaises(p.CandidateInputError):
                    self.rank(model)
                score.assert_not_called()

    def test_rehashed_invalid_metadata_and_chronology_are_rejected(self):
        changes = (
            ("training_cutoff", "2026-10-05T00:00:00+09:00"),
            ("train_nights", list(reversed(self.valid["train_nights"]))),
            ("train_nights", self.valid["train_nights"][:-1]),
            ("development_split_nights", ["2026-10-05", "2026-10-06"]),
            ("development_split_nights", ["2026-10-06", "2026-10-06"]),
            ("development_split_nights", ["2026-02-30", "2026-10-07"]),
            ("train_units", True), ("development_units", 0),
            ("train_positive_units", self.valid["train_units"]),
            ("development_brier_diagnostic", 2.0),
            ("independent_confirmation", "PERFORMED"),
            ("training_selection_sha256", "not-a-digest"),
            ("training_source_review", "SOURCE_AUTHENTICATED"),
        )
        for field, value in changes:
            with self.subTest(field=field), self.assertRaises(p.CandidateInputError):
                self.rank(seal_model(dict(copy.deepcopy(self.valid), **{field: value})))

    def test_missing_malformed_and_unbounded_model_envelopes_are_rejected(self):
        models = [None, [], {}, dict(self.valid, model_sha256="0"*64)]
        for field in ("model_sha256", "means", "feature_names", "production_activation_authorized"):
            model = copy.deepcopy(self.valid)
            model.pop(field)
            models.append(seal_model(model) if field != "model_sha256" else model)
        recursive = copy.deepcopy(self.valid)
        recursive["cycle"] = recursive
        models.extend([recursive, dict(self.valid, metadata="x"*4097),
                       dict(self.valid, metadata=object())])
        for index, model in enumerate(models):
            with self.subTest(index=index), self.assertRaises(p.CandidateInputError):
                self.rank(model)

    def test_model_snapshot_is_owned_before_forecast_rows_are_validated(self):
        supplied = copy.deepcopy(self.valid)
        original = p._validate_row

        def mutate_caller_model(row):
            supplied["coefficients"][0] += 10
            return original(row)

        with patch.object(p, "_validate_row", side_effect=mutate_caller_model):
            result = self.rank(supplied)
        self.assertEqual(result["model_sha256"], self.valid["model_sha256"])
        self.assertEqual(result["targets_100m_10min"][0]["probability_diagnostic"], 0.33976141)

    def test_full_legacy_v1_metadata_is_preserved_and_scores_identically(self):
        model = copy.deepcopy(self.valid)
        model["schema_version"] = "habu-prospective-candidate-v1"
        for old, new in (("untouched_holdout_nights", "development_split_nights"),
                         ("holdout_units", "development_units"),
                         ("holdout_brier_diagnostic", "development_brier_diagnostic")):
            model[old] = model.pop(new)
        model.pop("training_selection_sha256")
        model.pop("independent_confirmation")
        model["training_source_review"] = "INPUT_CONTRACT_ONLY_NOT_INDEPENDENTLY_ATTESTED"
        seal_model(model)
        raw = json.dumps(model, sort_keys=True, separators=(",", ":")).encode()
        result = self.rank(model)
        self.assertEqual(result["targets_100m_10min"][0]["probability_diagnostic"], 0.33976141)
        self.assertEqual(result["model_sha256"], model["model_sha256"])
        self.assertEqual(json.dumps(model, sort_keys=True, separators=(",", ":")).encode(), raw)


class CandidateTests(unittest.TestCase):
    def test_gpx_passage_alone_is_source_training_blocked(self):
        with self.assertRaisesRegex(p.CandidateInputError, "SOURCE_TRAINING_BLOCKED"):
            p.train_candidate(history_rows(), training_cutoff="2026-10-10T00:00:00+09:00")

    def test_training_development_split_and_prospective_rank(self):
        model = fit_rows(history_rows(),
                                  training_cutoff="2026-10-10T00:00:00+09:00")
        self.assertEqual(len(model["train_nights"]), 5)
        self.assertEqual(len(model["development_split_nights"]), 2)
        self.assertFalse(model["production_activation_authorized"])
        self.assertFalse(model["official_stage1_recall_computed"])
        self.assertGreaterEqual(model["development_brier_diagnostic"], 0)
        future = copy.deepcopy(history_rows()[0])
        future.update(operational_night="2026-10-24",
                      window_start_jst="2026-10-24T21:00:00+09:00",
                      forecast_cutoff="2026-10-24T16:00:00+09:00",
                      features_available_at="2026-10-24T15:00:00+09:00")
        for k in ("exposure_proof", "owner_capture_count", "outcome_available_at",
                  "outcome_source_sha256"):
            future.pop(k)
        forecast = p.rank_future(model, [future],
                                 issued_at="2026-10-24T17:00:00+09:00",
                                 operational_night="2026-10-24")
        self.assertEqual(len(forecast["targets_100m_10min"]), 1)
        self.assertEqual(forecast["area_rank_top10"][0]["area_1km"],
                         "utm52n_1km_500_3100")
        self.assertFalse(forecast["formal_100m_10min_eligible"])
        self.assertFalse(forecast["production_p0_freeze_allowed"])
        self.assertEqual(forecast["route_candidates_A_B_C"], "NOT_PRODUCED")

    def test_future_weather_leakage_cannot_enter_train(self):
        rows = history_rows()
        rows[0]["features_available_at"] = "2026-10-01T20:00:00+09:00"
        with self.assertRaises(p.CandidateInputError):
            fit_rows(rows, training_cutoff="2026-10-10T00:00:00+09:00")

    def test_unqualified_zero_is_unknown_not_negative(self):
        rows = history_rows()
        selected = selection_for(rows)
        selected["accepted"][1]["label"] = None
        with self.assertRaises(p.CandidateInputError):
            p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00",
                              training_selection=rebind(selected))

    def test_recent_label_is_not_training_input(self):
        rows = history_rows()
        rows[0]["outcome_available_at"] = "2026-10-11T00:00:00+09:00"
        with self.assertRaises(p.CandidateInputError):
            fit_rows(rows, training_cutoff="2026-10-10T00:00:00+09:00")

    def test_no_two_night_training_shortcut(self):
        with self.assertRaises(p.CandidateInputError):
            fit_rows(history_rows()[:20],
                              training_cutoff="2026-10-10T00:00:00+09:00")

    def test_sightings_are_never_automatically_captures(self):
        rows = history_rows()
        rows[0].pop("owner_capture_count")
        rows[0]["sighting_count"] = 1
        with self.assertRaises(p.CandidateInputError):
            fit_rows(rows, training_cutoff="2026-10-10T00:00:00+09:00")

    def test_models_cannot_rank_preissuance_targets(self):
        model = fit_rows(history_rows(),
                                  training_cutoff="2026-10-10T00:00:00+09:00")
        future = copy.deepcopy(history_rows()[0])
        future.update(operational_night="2026-10-24",
                      window_start_jst="2026-10-24T16:00:00+09:00",
                      forecast_cutoff="2026-10-24T15:00:00+09:00",
                      features_available_at="2026-10-24T14:00:00+09:00")
        for key in ("exposure_proof", "owner_capture_count", "outcome_available_at", "outcome_source_sha256"):
            future.pop(key)
        with self.assertRaises(p.CandidateInputError):
            p.rank_future(model, [future],
                          issued_at="2026-10-24T17:00:00+09:00",
                          operational_night="2026-10-24")

    def test_training_fingerprint_reproducible(self):
        one = fit_rows(history_rows(), training_cutoff="2026-10-10T00:00:00+09:00")
        two = fit_rows(history_rows(), training_cutoff="2026-10-10T00:00:00+09:00")
        self.assertEqual(one["model_sha256"], two["model_sha256"])

    def test_forged_or_insufficient_selection_is_source_training_blocked(self):
        for field, value in (("official_issuance_authorized", True),
                             ("qualification", "AUDITED_CONFIRMATION"),
                             ("status", "NEED_MORE_DATA"),
                             ("fit_cutoff", "2026-10-10T01:00:00+09:00")):
            selected = selection_for(history_rows())
            selected[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                    p.CandidateInputError, "SOURCE_TRAINING_BLOCKED"):
                p.train_candidate(history_rows(), training_cutoff="2026-10-10T00:00:00+09:00",
                                  training_selection=rebind(selected))

    def test_history_unit_features_and_binary_outcomes_must_match_selected_rows(self):
        mutations = (
            ("cell", lambda rows: rows[0].update(cell_id="utm52n_100m_6000_31000")),
            ("window", lambda rows: rows[0].update(window_start_jst="2026-10-01T21:10:00+09:00")),
            ("feature", lambda rows: rows[0].update(temperature_c=21.125)),
            ("label", lambda rows: rows[1].update(owner_capture_count=1)),
            ("missing row", lambda rows: rows.pop()),
            ("night", lambda rows: rows[0].update(
                operational_night="2026-09-30", window_start_jst="2026-09-30T21:00:00+09:00",
                forecast_cutoff="2026-09-30T18:00:00+09:00",
                features_available_at="2026-09-30T17:00:00+09:00")),
        )
        for name, mutate in mutations:
            rows = history_rows()
            selected = selection_for(rows)
            mutate(rows)
            with self.subTest(name=name), self.assertRaisesRegex(
                    p.CandidateInputError, "SOURCE_TRAINING_BLOCKED"):
                p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00",
                                  training_selection=selected)

    def test_rehashed_selection_feature_change_cannot_rebind_legacy_history(self):
        rows = history_rows()
        selected = selection_for(rows)
        selected["accepted"][0]["features"]["temperature_c"] += 0.25
        with self.assertRaisesRegex(p.CandidateInputError, "SOURCE_TRAINING_BLOCKED"):
            p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00",
                              training_selection=rebind(selected))

    def test_selection_cannot_omit_one_of_the_legacy_predictors(self):
        rows = history_rows()
        selected = selection_for(rows)
        selected["feature_names"].remove("temperature_c")
        for row in selected["accepted"]:
            row["features"].pop("temperature_c")
        with self.assertRaisesRegex(p.CandidateInputError, "SOURCE_TRAINING_BLOCKED"):
            p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00",
                              training_selection=rebind(selected))

    def test_history_duplicate_actual_unit_cannot_use_another_timezone_spelling(self):
        rows = history_rows()
        selected = selection_for(rows)
        duplicate = dict(rows[0], window_start_jst="2026-10-01T12:00:00Z")
        rows.append(duplicate)
        with self.assertRaises(p.CandidateInputError):
            p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00",
                              training_selection=selected)

    def test_source_selection_never_requires_gpx_passage_as_negative_proof(self):
        rows = history_rows()
        for row in rows:
            row.pop("exposure_proof")
        model = fit_rows(rows, training_cutoff="2026-10-10T00:00:00+09:00")
        self.assertEqual(model["train_units"], 20)

    def test_equal_instants_with_other_timezone_spelling_match_selection(self):
        rows = history_rows()
        selected = selection_for(rows)
        rows[0]["window_start_jst"] = "2026-10-01T12:00:00Z"
        model = p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00",
                                  training_selection=selected)
        self.assertEqual(model["train_units"], 20)

    def test_features_equal_to_forecast_cutoff_cannot_train(self):
        rows = history_rows()
        rows[0]["features_available_at"] = rows[0]["forecast_cutoff"]
        with self.assertRaises(p.CandidateInputError):
            fit_rows(rows, training_cutoff="2026-10-10T00:00:00+09:00")

    def test_features_equal_to_forecast_cutoff_cannot_rank(self):
        model = fit_rows(training_cutoff="2026-10-10T00:00:00+09:00")
        row = future_row()
        row["features_available_at"] = row["forecast_cutoff"]
        with self.assertRaises(p.CandidateInputError):
            p.rank_future(model, [row], issued_at="2026-10-24T17:00:00+09:00",
                          operational_night="2026-10-24")

    def test_declared_forecast_cutoff_cannot_follow_actual_issuance(self):
        model = fit_rows(training_cutoff="2026-10-10T00:00:00+09:00")
        row = future_row()
        row["forecast_cutoff"] = "2026-10-24T18:00:00+09:00"
        with self.assertRaises(p.CandidateInputError):
            p.rank_future(model, [row], issued_at="2026-10-24T17:00:00+09:00",
                          operational_night="2026-10-24")

    def test_future_outcomes_and_unrecognized_nested_payloads_cannot_rank(self):
        model = fit_rows(training_cutoff="2026-10-10T00:00:00+09:00")
        fields = {
            "owner_capture_count": 0, "outcome_available_at": "2026-10-25T09:00:00+09:00",
            "outcome_source_sha256": "b" * 64, "exposure_proof": "GPX_PASSAGE_VALIDATED",
            "label": None, "capture_event_ids": [], "negative_observed": True,
            "label_available_at": "2026-10-25T09:00:00+09:00",
            "audit_available_at": "2026-10-25T10:00:00+09:00",
            "metadata": {"future_outcome": {"label": 1}},
        }
        for field, value in fields.items():
            row = future_row()
            row[field] = value
            with self.subTest(field=field), self.assertRaises(p.CandidateInputError):
                p.rank_future(model, [row], issued_at="2026-10-24T17:00:00+09:00",
                              operational_night="2026-10-24")

    def test_internal_split_is_development_only_and_binds_selection(self):
        rows = history_rows()
        selected = selection_for(rows)
        model = p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00",
                                  training_selection=selected)
        self.assertNotIn("untouched_holdout_nights", model)
        self.assertEqual(model["schema_version"], "habu-prospective-candidate-v2")
        self.assertEqual(model["development_split_nights"], ["2026-10-06", "2026-10-07"])
        self.assertEqual(model["development_units"], 8)
        self.assertEqual(model["independent_confirmation"], "NOT_PERFORMED")
        self.assertEqual(model["training_selection_sha256"], selected["selection_sha256"])

    def test_valid_selected_fit_preserves_existing_numeric_routine(self):
        model = fit_rows(training_cutoff="2026-10-10T00:00:00+09:00")
        self.assertEqual(model["means"], [22.5, 85.0, 0.2, 13.5, -1.5, 31.5, 0.5])
        expected = [-1.1281752644830656, -0.0864273165075385, 0.0, 0.0,
                    -0.0864273165075385, -0.0864273165075385, -0.0864273165075385, 0.0]
        for actual, value in zip(model["coefficients"], expected):
            self.assertAlmostEqual(actual, value, places=12)
        self.assertEqual(model["development_brier_diagnostic"], 0.19376964)
        forecast = p.rank_future(model, [future_row()], issued_at="2026-10-24T17:00:00+09:00",
                                 operational_night="2026-10-24")
        self.assertEqual(forecast["targets_100m_10min"][0]["probability_diagnostic"], 0.33976141)

    def test_binary_fit_does_not_treat_multiple_capture_count_as_multiple_units(self):
        rows = history_rows()
        selected = selection_for(rows)
        rows[0]["owner_capture_count"] = 2
        model = p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00",
                                  training_selection=selected)
        self.assertEqual(model["train_positive_units"], 5)
        self.assertEqual(model["train_units"], 20)

    def test_existing_v1_serialized_diagnostic_model_can_rank_without_rewriting(self):
        # Frozen synthetic v1 numeric state, not a source-authenticated model.
        legacy = {
            "schema_version": "habu-prospective-candidate-v1",
            "status": "DIAGNOSTIC_WALK_FORWARD_CANDIDATE_ONLY",
            "training_cutoff": "2026-10-10T00:00:00+09:00",
            "untouched_holdout_nights": ["2026-10-06", "2026-10-07"],
            "means": [22.5, 85.0, 0.2, 13.5, -1.5, 31.5, 0.5],
            "scales": [1.118033988749895, 1e-9, 0.14142135623730953,
                       1.118033988749895, 1.118033988749895, 1.118033988749895, 1e-9],
            "coefficients": [-1.1281752644830656, -0.0864273165075385, 0.0, 0.0,
                             -0.0864273165075385, -0.0864273165075385, -0.0864273165075385, 0.0],
            "production_activation_authorized": False,
        }
        raw = json.dumps(legacy, sort_keys=True, separators=(",", ":")).encode()
        legacy["model_sha256"] = hashlib.sha256(raw).hexdigest()
        original = copy.deepcopy(legacy)
        forecast = p.rank_future(legacy, [future_row()], issued_at="2026-10-24T17:00:00+09:00",
                                 operational_night="2026-10-24")
        self.assertEqual(forecast["targets_100m_10min"][0]["probability_diagnostic"], 0.33976141)
        self.assertEqual(legacy, original)
        self.assertFalse(forecast["production_p0_freeze_allowed"])

    def test_pr46_source_bound_selector_connects_to_legacy_numeric_fit(self):
        try:
            from training_corpus import select_training_rows
        except ModuleNotFoundError as exc:
            if exc.name == "training_corpus":
                self.skipTest("PR46 repaired source-bound selector is not yet on this base")
            raise
        rows = history_rows()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = []

            def source(relative, raw, role, received="2026-10-09T12:00:00+09:00"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                ref = {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()}
                manifest.append(dict(ref, role=role, received_at=received))
                return ref

            label = source("evidence/fixture-labels.txt", b"synthetic owner capture outcomes", "label")
            feature = source("features/fixture-inputs.txt", b"synthetic ex-ante features", "feature",
                             "2026-09-30T12:00:00+09:00")
            corpus_rows = []
            for index, (history, accepted) in enumerate(zip(rows, selection_for(rows)["accepted"])):
                history.pop("exposure_proof")
                history.update(features_source_sha256=feature["sha256"],
                               outcome_source_sha256=label["sha256"],
                               outcome_available_at="2026-10-09T12:00:00+09:00")
                observed = dict(accepted,
                    observation="capture_observed" if accepted["label"] else "observed_negative",
                    quality="AUDITED_OBSERVED", label_available_at="2026-10-09T12:00:00+09:00",
                    audit_available_at="2026-10-09T13:00:00+09:00",
                    source_refs=[label["path"], feature["path"]], outcome_source_ref=label["path"],
                    feature_available_at={name: history["features_available_at"] for name in p.FEATURES},
                    feature_source_refs={name: [feature["path"]] for name in p.FEATURES},
                    feature_valid_for_night=True)
                if not accepted["label"]:
                    start = datetime.fromisoformat(accepted["window_start_jst"])
                    scope = {"night": accepted["night"], "cell_x": accepted["cell_x"],
                             "cell_y": accepted["cell_y"], "start": start.isoformat(),
                             "end": (start + timedelta(minutes=10)).isoformat()}
                    search = source(f"evidence/search-{index}.txt",
                                    f"synthetic active Habu search {index}".encode(), "search_evidence")
                    observed["source_refs"].append(search["path"])
                    for role, kind, basis in (
                        ("active_search", "active_habu_search_scope", search),
                        ("complete_outcome", "complete_owner_capture_outcome_scope", label),
                    ):
                        receipt = dict(schema_version="1.0", kind=kind, scope=scope,
                                       qualified_at="2026-10-09T13:00:00+09:00", basis_source_refs=[basis])
                        if role == "active_search":
                            receipt.update(search_role="SEARCH", evidence_type="INDEPENDENT_ACTIVE_HABU_SEARCH")
                        else:
                            receipt["recording_rule"] = "ALL_OWNER_HABU_CAPTURES_RECORDED"
                        raw = json.dumps(receipt, sort_keys=True).encode()
                        ref = source(f"evidence/{role}-{index}.json", raw, role,
                                     "2026-10-09T13:00:00+09:00")
                        observed[role + "_ref"] = ref
                        observed["source_refs"].append(ref["path"])
                    observed.update(search_role="SEARCH", all_captures_recorded=True, gpx_segment_eligible=True)
                corpus_rows.append(observed)
            corpus = dict(schema_version="1.0", qualification="AUDITED_TRAIN_ONLY",
                          source_manifest=manifest, rows=corpus_rows)
            raw = json.dumps(corpus, sort_keys=True).encode()
            target = root / "data/processed/fixture.json"
            target.parent.mkdir(parents=True)
            target.write_bytes(raw)
            sha = hashlib.sha256(raw).hexdigest()
            selected = select_training_rows(root, "data/processed/fixture.json", sha,
                "2026-10-11", "2026-10-10T00:00:00+09:00", require_features=tuple(p.FEATURES))
            model = p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00",
                                      training_selection=selected)
            self.assertEqual(model["train_units"], 20)
            self.assertEqual(model["development_brier_diagnostic"], 0.19376964)
            self.assertEqual(model["training_selection_sha256"], selected["selection_sha256"])
            (root / label["path"]).write_bytes(b"mutated fixture source")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                select_training_rows(root, "data/processed/fixture.json", sha,
                    "2026-10-11", "2026-10-10T00:00:00+09:00", require_features=tuple(p.FEATURES))


class SharedNumericCoreTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(p, '_fit_numeric', None)), 'shared numeric fit core is missing')
        rows = history_rows()[:20]
        self.matrix = [[row[name] for name in p.FEATURES] for row in rows]
        self.labels = [int(row['owner_capture_count'] > 0) for row in rows]

    def fit(self, **kwargs):
        return p._fit_numeric(self.matrix, self.labels, **kwargs)

    def test_legacy_default_entire_serialized_model_is_unchanged(self):
        reference = legacy_reference()
        rows = history_rows()
        expected = reference['train_candidate'](rows, training_cutoff='2026-10-10T00:00:00+09:00',
            training_selection=selection_for(rows))
        result = fit_rows(training_cutoff='2026-10-10T00:00:00+09:00')
        self.assertEqual(result, expected)
        self.assertEqual(json.dumps(result, sort_keys=True), json.dumps(expected, sort_keys=True))
        options = dict(issued_at='2026-10-24T17:00:00+09:00', operational_night='2026-10-24')
        self.assertEqual(p.rank_future(result, [future_row()], **options),
                         reference['rank_future'](expected, [future_row()], **options))
        numeric = self.fit()
        self.assertEqual(numeric, (result['means'], result['scales'], result['coefficients']))
        self.assertEqual(numeric, self.fit(feature_mask=[True] * 7))

    def test_legacy_equivalence_is_runtime_local_even_with_shared_libm_ulp_variation(self):
        original_exp = math.exp
        def adjacent_exp(value):
            return math.nextafter(original_exp(value), math.inf)
        with patch.object(p.math, 'exp', side_effect=adjacent_exp):
            self.test_legacy_default_entire_serialized_model_is_unchanged()

    def test_pinned_reference_is_independent_of_shared_core_and_current_score(self):
        expected = legacy_reference_fit()
        with patch.object(p, '_fit_numeric', side_effect=AssertionError('production core accessed')), \
                patch.object(p, '_score', side_effect=AssertionError('production score accessed')):
            self.assertEqual(legacy_reference_fit(), expected)

    def test_same_runtime_reference_detects_an_actual_numeric_core_regression(self):
        expected = legacy_reference_fit()
        core = p._fit_numeric
        def changed(*args, **kwargs):
            means, scales, coefficients = core(*args, **kwargs)
            coefficients[0] += .01
            return means, scales, coefficients
        with patch.object(p, '_fit_numeric', side_effect=changed):
            actual = fit_rows(training_cutoff='2026-10-10T00:00:00+09:00')
        self.assertNotEqual(actual, expected)
        self.assertNotEqual(actual['model_sha256'], expected['model_sha256'])

    def test_every_nonempty_subset_refits_from_zero_on_all_same_rows(self):
        original = copy.deepcopy((self.matrix, self.labels))
        score = p._score
        for bits in range(1, 128):
            mask = [bool(bits & (1 << index)) for index in range(7)]
            calls = []
            def observe(x, coef, means, scales):
                if len(calls) < len(self.labels): calls.append(list(coef))
                return score(x, coef, means, scales)
            with self.subTest(bits=bits), patch.object(p, '_score', side_effect=observe):
                means, scales, coefficients = self.fit(feature_mask=mask)
            indices = [i for i in range(7) if mask[i]]
            self.assertEqual(means, [mean(row[i] for row in self.matrix) for i in indices])
            self.assertEqual(len(scales), sum(mask))
            self.assertEqual(len(coefficients), sum(mask)+1)
            self.assertEqual(calls, [[0.0] * (sum(mask)+1)] * len(self.labels))
            self.assertTrue(all(math.isfinite(value) for value in coefficients))
        self.assertEqual((self.matrix, self.labels), original)

    def test_real_refit_is_different_from_zeroing_full_model_weights(self):
        _, _, full = self.fit()
        mask = [True, False, False, False, False, False, False]
        means, scales, reduced = self.fit(feature_mask=mask)
        self.assertNotAlmostEqual(full[1], reduced[1], places=6)
        full_means, full_scales, _ = self.fit()
        zeroed = [full[0], full[1], 0, 0, 0, 0, 0, 0]
        self.assertNotAlmostEqual(p._score(self.matrix[0], zeroed, full_means, full_scales),
                                 p._score([self.matrix[0][0]], reduced, means, scales), places=6)

    def test_masks_invalid_all_false_nonbool_and_wrong_shape_are_rejected(self):
        for mask in ([], [True]*6, [True]*8, [False]*7, [1]*7, '1111111', True, [True]*6+[None]):
            with self.subTest(mask=mask), self.assertRaises(ValueError): self.fit(feature_mask=mask)

    def test_numeric_inputs_are_bounded_finite_and_strict_binary(self):
        for kind in ('empty', 'shape', 'labelcount', 'labelbool', 'unknown', 'featurebool', 'nan', 'hugeint'):
            with self.subTest(kind=kind):
                self.setUp()
                if kind == 'empty': self.matrix, self.labels = [], []
                elif kind == 'shape': self.matrix[0].pop()
                elif kind == 'labelcount': self.labels.pop()
                elif kind == 'labelbool': self.labels[0] = True
                elif kind == 'unknown': self.labels[0] = None
                elif kind == 'featurebool': self.matrix[0][0] = True
                elif kind == 'nan': self.matrix[0][0] = float('nan')
                else: self.matrix[0][0] = 10**1000
                with self.assertRaises(ValueError): self.fit()
        with self.assertRaises(ValueError): p._fit_numeric([[0]*7]*20_001, [0]*20_001)

    def test_core_owns_scalar_matrix_labels_and_mask_before_caller_callback(self):
        expected = self.fit(feature_mask=[True, False, True, True, True, True, True])
        mask = [True, False, True, True, True, True, True]
        def mutate():
            self.matrix[0][0] = 300
            self.labels[0] = 1-self.labels[0]
            mask[:] = [True]*7
        result = self.fit(feature_mask=mask, check=mutate)
        self.assertEqual(result, expected)

    def test_callback_interrupts_projection_scaling_optimizer_and_final_return(self):
        checkpoints = []
        def record(): checkpoints.append(1)
        expected = self.fit(check=record)
        self.assertGreater(len(checkpoints), 320*len(self.labels))
        for stop in (1, 25, 100, len(checkpoints)//2, len(checkpoints)):
            count = [0]
            def cancel():
                count[0] += 1
                if count[0] == stop: raise TimeoutError('parent exhausted')
            with self.subTest(stop=stop), self.assertRaises(TimeoutError): self.fit(check=cancel)
        self.assertEqual(expected, self.fit())

    def test_train_callback_is_shared_and_includes_final_hash_boundary(self):
        expected = legacy_reference_fit()
        result = fit_rows(training_cutoff='2026-10-10T00:00:00+09:00', check=lambda: None)
        self.assertEqual(result, expected)
        class LateHash:
            def __init__(self, real): self.real = real
            def hexdigest(self):
                ready[0] = False
                return self.real.hexdigest()
        ready = [True]
        real = hashlib.sha256
        def hashing(raw=b''): return LateHash(real(raw))
        def check():
            if not ready[0]: raise TimeoutError('expired after final model hash')
        # Only the legacy model serialization hash is patched; selector digest
        # lives in the shared hashlib module too, so trigger only its exact bytes.
        def model_hash(raw=b''):
            return hashing(raw) if b'"schema_version":"habu-prospective-candidate-v2"' in raw else real(raw)
        with patch.object(p.hashlib, 'sha256', side_effect=model_hash), self.assertRaises(TimeoutError):
            fit_rows(training_cutoff='2026-10-10T00:00:00+09:00', check=check)

    def test_legacy_history_caller_mutation_after_core_entry_cannot_change_fit(self):
        rows = history_rows()
        selected = selection_for(rows)
        expected = legacy_reference_fit(copy.deepcopy(rows))
        numeric = p._fit_numeric
        entered = [False]
        def enter(matrix, labels, **kwargs):
            entered[0] = True
            return numeric(matrix, labels, **kwargs)
        def mutate():
            if entered[0]:
                rows[0]['temperature_c'] = 200
                selected['accepted'][0]['label'] = 1
        with patch.object(p, '_fit_numeric', side_effect=enter):
            model = p.train_candidate(rows, training_cutoff='2026-10-10T00:00:00+09:00',
                training_selection=selected, check=mutate)
        self.assertEqual(model, expected)


if __name__ == "__main__":
    unittest.main()
