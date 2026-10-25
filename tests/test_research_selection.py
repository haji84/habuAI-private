"""Fixtures test a pure research boundary, never certify real observations."""
import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
IDENTITY = ("accepted", "corpus_sha256", "source_sha256", "source_received_at",
            "heldout_night", "fit_cutoff", "feature_names", "exposed_nights")


def fixture_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def bind_selection(value):
    value["selection_sha256"] = fixture_digest({key: value[key] for key in IDENTITY})
    return value


def selection_fixture():
    """Exact PR46 selector envelope; every source/row is an invented test fixture."""
    rows = []
    for day, labels in ((1, (1, 0)), (2, (1, 0)), (3, (0, 1))):
        for index, label in enumerate(labels):
            row_id = f"fixture-{day}-{index}"
            rows.append({"row_id": row_id, "night": f"2026-09-{day:02d}",
                "label": label, "cell_x": 4000 + index * 10 + day - 1,
                "cell_y": 30000, "features": {"rain_mm": 0.5},
                "window_start_jst": f"2026-09-{day:02d}T20:00:00+09:00",
                "capture_event_ids": [row_id + "-capture"] if label else []})
    return bind_selection({
        "status": "DEVELOPMENT_TRAINING_ELIGIBLE",
        "qualification": "RETROSPECTIVE_TRAIN_ONLY_NOT_CONFIRMATION",
        "official_issuance_authorized": False,
        "heldout_night": "2026-10-14", "fit_cutoff": "2026-10-13T12:00:00+09:00",
        "feature_names": ["rain_mm"], "corpus_sha256": "a" * 64,
        "accepted": rows, "rejected": [],
        "counts": {"accepted_rows": 6, "rejected_rows": 0, "nights": 3,
                   "positives": 3, "negatives": 3},
        "source_sha256": {"evidence/test-label.json": "b" * 64,
                          "features/test-input.json": "c" * 64},
        "source_received_at": {"evidence/test-label.json": "2026-09-30T00:00:00+09:00",
                               "features/test-input.json": "2026-09-30T00:00:00+09:00"},
        "exposed_nights": [], "blockers": [],
    })


def insufficient_fixture(*, positive_only=False):
    value = selection_fixture()
    if positive_only:
        value["accepted"] = [r for r in value["accepted"] if r["label"] == 1]
    else:
        value["accepted"] = []
    rows = value["accepted"]
    value["counts"] = {"accepted_rows": len(rows), "rejected_rows": 0,
        "nights": len({r["night"] for r in rows}),
        "positives": len(rows), "negatives": 0}
    value["status"] = "NEED_MORE_DATA"
    value["blockers"] = ["Need independently qualified binary observation units"]
    return bind_selection(value)


def future_fixture():
    return [{"row_id": name, "operational_night": "2026-10-14",
        "cutoff_time": "2026-10-14T18:00:00+09:00",
        "window_start_jst": "2026-10-14T19:00:00+09:00",
        "utm_x_m": x, "utm_y_m": 3000050,
        "features": {"rain_mm": 0.5},
        "feature_source_refs": {"rain_mm": ["features/test-forecast.json"]},
        "feature_available_at": {"rain_mm": "2026-10-14T17:00:00+09:00"}}
        for name, x in (("future-a", 400050), ("future-b", 401050),
                        ("future-unseen", 405050))]


class GateTestCase(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec("models.research_selection") if (ROOT / "src/models").exists() else None
        self.assertIsNotNone(spec, "research selection gate is missing")
        from models import research_selection
        self.gate = research_selection


class SelectionGateTests(GateTestCase):
    def validate(self, value):
        return self.gate.validate_selection(value)

    def test_exact_selector_envelope_is_copied_without_mutation(self):
        value = selection_fixture()
        actual = self.validate(value)
        self.assertEqual(actual, value)
        actual["accepted"][0]["features"]["rain_mm"] = 99
        self.assertEqual(value["accepted"][0]["features"]["rain_mm"], 0.5)

    def test_zero_rows_and_positive_only_never_claim_binary_readiness(self):
        for value in (insufficient_fixture(), insufficient_fixture(positive_only=True)):
            with self.subTest(rows=len(value["accepted"])):
                self.assertEqual(self.validate(value)["status"], "NEED_MORE_DATA")

    def test_digest_binds_each_selector_identity_field(self):
        for key in IDENTITY:
            value = selection_fixture()
            if key == "accepted":
                value[key][0]["features"]["rain_mm"] = 2.0
            elif key == "source_sha256":
                value[key]["evidence/test-label.json"] = "d" * 64
            elif key == "source_received_at":
                value[key]["evidence/test-label.json"] = "2026-10-01T00:00:00+09:00"
            elif key in ("feature_names", "exposed_nights"):
                value[key] = ["wind_ms"] if key == "feature_names" else ["2026-08-01"]
            else:
                value[key] = {"corpus_sha256": "d" * 64,
                    "heldout_night": "2026-10-15", "fit_cutoff": "2026-10-13T13:00:00+09:00"}[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(value)

    def test_unknown_boolean_and_other_labels_cannot_enter_accepted_rows(self):
        for label in (None, True, False, "1", 2, 0.0):
            value = selection_fixture()
            value["accepted"][0]["label"] = label
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.validate(bind_selection(value))

    def test_duplicate_row_unit_and_event_are_rejected_even_after_rebinding(self):
        for field in ("row_id", "unit", "capture_event_ids"):
            value = selection_fixture()
            first, second = value["accepted"][0], value["accepted"][2]
            if field == "unit":
                second.update(cell_x=first["cell_x"], cell_y=first["cell_y"],
                    night=first["night"], window_start_jst="2026-09-01T11:00:00Z")
            else:
                second[field] = copy.deepcopy(first[field])
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(bind_selection(value))

    def test_event_identity_agrees_with_binary_capture_outcome(self):
        for index, ids in ((0, []), (1, ["impossible-negative-event"]), (0, ["x", "x"])):
            value = selection_fixture()
            value["accepted"][index]["capture_event_ids"] = ids
            with self.subTest(index=index, ids=ids), self.assertRaises(ValueError):
                self.validate(bind_selection(value))

    def test_night_window_fit_boundary_and_research_exposure_are_enforced(self):
        mutations = (
            lambda v: v.update(fit_cutoff="2026-10-14T07:00:00+09:00"),
            lambda v: v.update(exposed_nights=["2026-09-01"]),
            lambda v: v["accepted"][0].update(night="2026-10-14"),
            lambda v: v["accepted"][0].update(window_start_jst="2026-09-02T07:00:00+09:00"),
            lambda v: v["accepted"][0].update(window_start_jst="2026-09-01T20:05:00+09:00"),
            lambda v: v["accepted"][0].update(window_start_jst="2026-09-01T20:00:00"),
            lambda v: v.update(fit_cutoff="2026-09-01T20:00:00+09:00"),
        )
        for mutate in mutations:
            value = selection_fixture()
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.validate(bind_selection(value))

    def test_early_morning_uses_previous_operational_night(self):
        value = selection_fixture()
        value["accepted"][0]["window_start_jst"] = "2026-09-02T00:00:00+09:00"
        value["accepted"].sort(key=lambda r: (r["night"], r["window_start_jst"], r["row_id"]))
        self.assertEqual(self.validate(bind_selection(value))["counts"]["accepted_rows"], 6)

    def test_bound_source_receipts_are_complete_and_timezone_aware(self):
        for time in ("2026-09-30", "not-a-timestamp", "2026-09-30T12:00:00"):
            value = selection_fixture()
            value["source_received_at"]["evidence/test-label.json"] = time
            with self.subTest(time=time), self.assertRaises(ValueError):
                self.validate(bind_selection(value))
        value = selection_fixture()
        del value["source_received_at"]["features/test-input.json"]
        with self.assertRaises(ValueError):
            self.validate(bind_selection(value))

    def test_unused_later_source_for_rejected_row_does_not_disqualify_accepted_rows(self):
        # PR46 hashes the entire source manifest, including rejected-row sources.
        # Its output omits accepted per-row source references/readiness fields.
        value = selection_fixture()
        value["rejected"] = [{"row_id": "future-rejected", "night": "2026-10-15",
            "reasons": ["NOT_PRIOR_TRAINING_NIGHT", "SOURCE_RECEIVED_AFTER_FIT"]}]
        value["counts"]["rejected_rows"] = 1
        value["source_sha256"]["evidence/unused-later.json"] = "e" * 64
        value["source_received_at"]["evidence/unused-later.json"] = "2026-10-16T00:00:00+09:00"
        actual = self.validate(bind_selection(value))
        self.assertEqual(actual["status"], "DEVELOPMENT_TRAINING_ELIGIBLE")
        self.assertEqual(actual["accepted"], selection_fixture()["accepted"])

    def test_missing_nonfinite_boolean_features_and_outcome_predictors_are_rejected(self):
        for feature in ({}, {"rain_mm": True}, {"rain_mm": None}, {"other": 0.5}):
            value = selection_fixture()
            value["accepted"][0]["features"] = feature
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                self.validate(bind_selection(value))
        value = selection_fixture()
        value["accepted"][0]["features"]["rain_mm"] = float("nan")
        with self.assertRaises(ValueError):
            self.validate(value)
        value = selection_fixture()
        value["feature_names"] = ["Label"]
        for row in value["accepted"]:
            row["features"] = {"Label": 0.5}
        with self.assertRaises(ValueError):
            self.validate(bind_selection(value))

    def test_counts_status_authority_and_extra_fields_cannot_be_forged(self):
        mutations = (
            lambda v: v["counts"].update(positives=4),
            lambda v: v.update(official_issuance_authorized=True),
            lambda v: v.update(qualification="AUDITED_CONFIRMATION"),
            lambda v: v.update(status="NEED_MORE_DATA"),
            lambda v: v.update(sealed_outcomes={"label": 0}),
            lambda v: v["accepted"][0].update(metadata={"label": 0}),
        )
        for mutate in mutations:
            value = selection_fixture()
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.validate(bind_selection(value))

    def test_rejected_rows_cannot_reuse_an_accepted_identity(self):
        value = selection_fixture()
        value["rejected"] = [{"row_id": value["accepted"][0]["row_id"],
            "night": "2026-09-01", "reasons": ["UNKNOWN_NOT_NEGATIVE"]}]
        value["counts"]["rejected_rows"] = 1
        with self.assertRaises(ValueError):
            self.validate(value)

    def test_unbounded_and_non_json_values_are_rejected(self):
        with patch.object(self.gate, "MAX_TRAINING_ROWS", 5), self.assertRaises(ValueError):
            self.validate(selection_fixture())
        with patch.object(self.gate, "MAX_JSON_BYTES", 64), self.assertRaises(ValueError):
            self.validate(selection_fixture())
        value = selection_fixture()
        value["accepted"][0]["features"]["rain_mm"] = object()
        with self.assertRaises(ValueError):
            self.validate(value)


class FutureGateTests(GateTestCase):
    def validate_future(self, rows, **kwargs):
        return self.gate.validate_future_rows(rows,
            cutoff_time="2026-10-14T18:00:00+09:00",
            heldout_night="2026-10-14", universe_sha256=fixture_digest(rows), **kwargs)

    def test_full_prospective_join_retains_unobserved_units_and_normalizes_cells(self):
        rows = future_fixture()
        actual = self.validate_future(rows, feature_names=("rain_mm",))
        self.assertEqual([r["row_id"] for r in actual], ["future-a", "future-b", "future-unseen"])
        self.assertEqual([r["cell_x"] for r in actual], [4000, 4010, 4050])
        self.assertNotIn("cell_x", rows[0])
        self.assertEqual(self.gate.area_id(4000, 30000), "utm52n_1km_400_3000")

    def test_wrong_full_rows_digest_rejects_subset_and_mutation(self):
        rows = future_fixture()
        expected = fixture_digest(rows)
        for changed in (rows[:-1], [dict(rows[0], utm_x_m=402050), *rows[1:]]):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.gate.validate_future_rows(changed, cutoff_time="2026-10-14T18:00:00+09:00",
                    universe_sha256=expected)

    def test_duplicate_row_and_timezone_equivalent_unit_are_rejected(self):
        for identity in ("row_id", "unit"):
            rows = future_fixture()
            if identity == "row_id":
                rows[1]["row_id"] = rows[0]["row_id"]
            else:
                rows[1].update(utm_x_m=400060, window_start_jst="2026-10-14T10:00:00Z")
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                self.validate_future(rows)

    def test_forecast_cutoff_night_window_and_feature_equality_are_rejected(self):
        changes = ({"cutoff_time": "2026-10-14T18:10:00+09:00"},
            {"operational_night": "2026-10-15"},
            {"window_start_jst": "2026-10-14T18:00:00+09:00"},
            {"window_start_jst": "2026-10-14T19:05:00+09:00"},
            {"window_start_jst": "2026-10-15T07:00:00+09:00"},
            {"feature_available_at": {"rain_mm": "2026-10-14T18:00:00+09:00"}})
        for changed in changes:
            rows = future_fixture()
            rows[0].update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.validate_future(rows)

    def test_forecast_never_defaults_missing_features_or_accepts_labels(self):
        changes = ({"features": {}}, {"features": {"rain_mm": None}},
            {"feature_source_refs": {}}, {"label": 0},
            {"metadata": {"owner_capture_count": 1}}, {"cell_x": 4999})
        for changed in changes:
            rows = future_fixture()
            rows[0].update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.validate_future(rows, feature_names=("rain_mm",))

    def test_nonfinite_boolean_and_out_of_domain_forecast_coordinates_are_rejected(self):
        for value in (True, None, -1, 999999, float("inf")):
            rows = future_fixture()
            rows[0]["utm_x_m"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                if value == float("inf"):
                    self.gate.validate_future_rows(rows, cutoff_time="2026-10-14T18:00:00+09:00",
                        universe_sha256="a" * 64)
                else:
                    self.validate_future(rows)

    def test_explicit_empty_feature_snapshot_is_valid_for_spatial_only_model(self):
        rows = future_fixture()
        for row in rows:
            row.update(features={}, feature_source_refs={}, feature_available_at={})
        self.assertEqual(len(self.validate_future(rows, feature_names=())), 3)

    def test_existing_geographic_projection_and_explicit_cells_are_supported(self):
        # At the central meridian and equator, UTM52N is exactly (500000, 0).
        rows = future_fixture()[:1]
        rows[0].pop("utm_x_m")
        rows[0].pop("utm_y_m")
        rows[0].update(latitude=0.0, longitude=129.0)
        actual = self.validate_future(rows)
        self.assertEqual((actual[0]["cell_x"], actual[0]["cell_y"]), (5000, 0))
        rows[0].pop("latitude")
        rows[0].pop("longitude")
        rows[0].update(cell_x=4000, cell_y=30000)
        self.assertEqual(self.validate_future(rows)[0]["cell_x"], 4000)

    def test_conflicting_coordinate_representations_are_rejected(self):
        rows = future_fixture()[:1]
        rows[0].update(latitude=0.0, longitude=129.0)
        with self.assertRaises(ValueError):
            self.validate_future(rows)

    def test_cell_only_forecasts_cannot_bypass_projected_coordinate_extent(self):
        for cx, cy in ((100000, 30000), (999, 30000), (9001, 30000)):
            rows = future_fixture()[:1]
            rows[0].pop("utm_x_m")
            rows[0].pop("utm_y_m")
            rows[0].update(cell_x=cx, cell_y=cy)
            with self.subTest(cx=cx, cy=cy), self.assertRaises(ValueError):
                self.validate_future(rows)

    def test_forecast_row_count_is_bounded_and_empty_universe_is_invalid(self):
        with self.assertRaises(ValueError):
            self.validate_future([])
        with patch.object(self.gate, "MAX_FORECAST_ROWS", 2), self.assertRaises(ValueError):
            self.validate_future(future_fixture())


if __name__ == "__main__":
    unittest.main()
