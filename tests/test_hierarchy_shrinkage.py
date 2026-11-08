"""Controlled PR46-shaped fixtures; these are not real source-qualified fits."""
import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


IDENTITY = ("accepted", "corpus_sha256", "source_sha256", "source_received_at",
            "heldout_night", "fit_cutoff", "feature_names", "exposed_nights")


def selection_fixture(*, positive_only=False):
    """Exact select_training_rows return envelope, with fictional unit evidence."""
    accepted = []
    for day in (1, 2, 3):
        for index, cell_x in enumerate((5002, 5003)):
            label = 1 if positive_only or index == 0 else 0
            accepted.append({
                "row_id": f"fixture-{day}-{index}", "night": f"2026-10-{day:02}",
                "label": label, "cell_x": cell_x, "cell_y": 31002,
                "features": {"temperature_c": 24.0},
                "window_start_jst": f"2026-10-{day:02}T23:50:00+09:00",
                "capture_event_ids": [f"fixture-event-{day}-{index}"] if label else [],
            })
    value = {
        "status": "NEED_MORE_DATA" if positive_only else "DEVELOPMENT_TRAINING_ELIGIBLE",
        "qualification": "RETROSPECTIVE_TRAIN_ONLY_NOT_CONFIRMATION",
        "official_issuance_authorized": False,
        "heldout_night": "2026-10-24", "fit_cutoff": "2026-10-23T06:00:00+09:00",
        "feature_names": ["temperature_c"], "corpus_sha256": "a" * 64,
        "accepted": accepted, "rejected": [],
        "counts": {"accepted_rows": 6, "rejected_rows": 0, "nights": 3,
                   "positives": 6 if positive_only else 3,
                   "negatives": 0 if positive_only else 3},
        "source_sha256": {"evidence/fixture-outcome.json": "b" * 64},
        "source_received_at": {"evidence/fixture-outcome.json": "2026-10-04T09:00:00+09:00"},
        "exposed_nights": [],
        "blockers": ["Need >=3 eligible prior nights and >=2 independently qualified"
                     " positives and >=2 confirmed no-capture observation units"] if positive_only else [],
    }
    value["selection_sha256"] = digest({key: value[key] for key in IDENTITY})
    return value


def future_row(row_id="future-known", *, cell_x=5002, cell_y=31002,
               start="2026-10-24T23:50:00+09:00"):
    """The existing joined prospective-input row shape, not an outcome row."""
    return {
        "row_id": row_id, "operational_night": "2026-10-24",
        "cutoff_time": "2026-10-24T18:00:00+09:00", "window_start_jst": start,
        "cell_x": cell_x, "cell_y": cell_y,
        "features": {"temperature_c": 24.0},
        "feature_source_refs": {"temperature_c": ["features/fixture-forecast.json"]},
        "feature_available_at": {"temperature_c": "2026-10-24T17:00:00+09:00"},
    }


class HierarchyShrinkageTests(unittest.TestCase):
    def setUp(self):
        # Missing implementation is an assertion failure in the initial RED run.
        self.assertIsNotNone(importlib.util.find_spec("models.hierarchy_shrinkage")
                             if (ROOT / "src/models").is_dir() else None,
                             "HB-B1 hierarchy implementation is missing")
        from models import hierarchy_shrinkage
        self.h = hierarchy_shrinkage

    def fit(self):
        return self.h.fit_hierarchy(selection_fixture())

    def rank(self, model, rows):
        return self.h.rank_hierarchy(model, rows,
                                     cutoff_time="2026-10-24T18:00:00+09:00",
                                     universe_sha256=digest(rows))

    def test_sparse_positives_shrink_through_every_spatial_and_clock_parent(self):
        model = self.fit()
        result = self.rank(model, [future_row()])
        levels = result["unit_scores"][0]["hierarchy_scores"]
        # Global=(3+1)/(6+2)=1/2. Same 1km/500m. Positive 250m has 3/3.
        for name, expected in (("1000m", 1/2), ("500m", 1/2), ("250m", 5/7),
                               ("100m", 41/49), ("10min", 311/343)):
            self.assertAlmostEqual(levels[name], expected, places=12)
        self.assertEqual(model["candidate_id"], "HB-B1")
        self.assertEqual(model["fit_evidence"]["accepted_rows"], 6)
        self.assertEqual(model["fit_evidence"]["positives"], 3)

    def test_unseen_cell_slot_and_area_inherit_only_their_nearest_parent(self):
        model = self.fit()
        rows = [future_row("unseen-slot", start="2026-10-25T00:00:00+09:00"),
                future_row("unseen-cell", cell_x=5001),
                future_row("unseen-500", cell_x=5007),
                future_row("unseen-area", cell_x=5020)]
        output = {row["row_id"]: row for row in self.rank(model, rows)["unit_scores"]}
        for row_id, expected in (("unseen-slot", 41/49), ("unseen-cell", 5/7),
                                 ("unseen-500", 1/2), ("unseen-area", 1/2)):
            self.assertAlmostEqual(output[row_id]["rank_score_diagnostic"], expected, places=12)

    def test_250m_boundaries_use_physical_cell_origin_and_disclose_proxy_geometry(self):
        result = self.rank(self.fit(), [future_row("left"), future_row("right", cell_x=5003)])
        units = {row["row_id"]: row for row in result["unit_scores"]}
        self.assertEqual(units["left"]["zone_250m"], "utm52n_250m_2000_12400")
        self.assertEqual(units["right"]["zone_250m"], "utm52n_250m_2001_12400")
        self.assertEqual(units["left"]["cell_id"], "utm52n_100m_5002_31002")
        self.assertEqual(result["geometry_semantics"], "CELL_ORIGIN_PROXY_NOT_POINT_GEOMETRY")
        self.assertEqual(self.fit()["geometry_semantics"], result["geometry_semantics"])

    def test_full_unobserved_future_universe_is_scored_with_ten_unique_top_areas(self):
        rows = [future_row(f"area-{index}", cell_x=5002 + index * 10) for index in range(13)]
        rows.append(future_row("another-window", start="2026-10-25T00:00:00+09:00"))
        output = self.rank(self.fit(), rows)
        self.assertEqual({row["row_id"] for row in output["unit_scores"]}, {r["row_id"] for r in rows})
        self.assertEqual(output["universe_rows"], 14)
        self.assertEqual(output["universe_sha256"], digest(rows))
        areas = output["hierarchy_rankings"]["1000m"]
        self.assertEqual(len(areas), 13)
        self.assertEqual(len(output["area_rank_top10"]), 10)
        self.assertEqual(len({row["unit_id"] for row in output["area_rank_top10"]}), 10)
        self.assertEqual(sum(row["candidate_units"] for row in areas), 14)
        for level in ("500m", "250m", "100m"):
            self.assertEqual(sum(row["candidate_units"] for row in output["hierarchy_rankings"][level]), 14)

    def test_clock_slots_are_jst_cyclic_categories_even_across_utc_midnight(self):
        rows = [future_row("last", start="2026-10-24T14:50:00+00:00"),
                future_row("first", start="2026-10-24T15:00:00+00:00")]
        output = {row["row_id"]: row for row in self.rank(self.fit(), rows)["unit_scores"]}
        self.assertEqual(output["last"]["tenmin_slot"], 143)
        self.assertEqual(output["first"]["tenmin_slot"], 0)
        self.assertAlmostEqual(output["last"]["rank_score_diagnostic"], 311/343)
        self.assertAlmostEqual(output["first"]["rank_score_diagnostic"], 41/49)

    def test_positive_only_data_yields_no_model_or_probability_fit(self):
        output = self.h.fit_hierarchy(selection_fixture(positive_only=True))
        self.assertEqual(output["status"], "NEED_MORE_DATA")
        self.assertIsNone(output["model"])
        self.assertNotIn("parameters", output)
        self.assertFalse(output["production_activation_authorized"])

    def test_missing_or_bool_labels_and_unbound_selection_are_rejected(self):
        for label in (None, False):
            selection = selection_fixture()
            selection["accepted"][0]["label"] = label
            selection["selection_sha256"] = digest({key: selection[key] for key in IDENTITY})
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.h.fit_hierarchy(selection)
        selection = selection_fixture()
        selection["accepted"][0]["cell_x"] += 1
        with self.assertRaises(ValueError):
            self.h.fit_hierarchy(selection)

    def test_fits_and_predictions_are_pure_serializable_and_content_bound(self):
        selection = selection_fixture()
        before = copy.deepcopy(selection)
        model = self.h.fit_hierarchy(selection)
        self.assertEqual(selection, before)
        self.assertEqual(model, self.h.fit_hierarchy(selection))
        self.assertEqual(model["training_selection_sha256"], selection["selection_sha256"])
        self.assertEqual(model["model_sha256"], digest({k: v for k, v in model.items() if k != "model_sha256"}))
        rows = [future_row()]
        original = copy.deepcopy(rows)
        model_copy = copy.deepcopy(model)
        output = self.rank(json.loads(json.dumps(model)), rows)
        self.assertEqual(rows, original)
        self.assertEqual(model, model_copy)
        self.assertEqual(output["prediction_sha256"], digest({k: v for k, v in output.items() if k != "prediction_sha256"}))
        self.assertEqual(output, self.rank(model, rows))

    def test_altered_model_and_changed_fixed_recipe_cannot_be_ranked(self):
        model = self.fit()
        model["parameters"]["global"]["positives"] += 1
        with self.assertRaises(ValueError):
            self.rank(model, [future_row()])
        model = self.fit()
        model["recipe"]["parent_strength"] = 5
        model["model_sha256"] = digest({k: v for k, v in model.items() if k != "model_sha256"})
        with self.assertRaises(ValueError):
            self.rank(model, [future_row()])

    def test_rehashed_model_cannot_bypass_frozen_family_readiness_or_lineage(self):
        mutations = (
            ("training_cutoff", "2026-10-24T17:59:59+09:00"),
            ("family", "ARBITRARY_UNREGISTERED"),
            ("training_qualification", "SEALED_CONFIRMATION"),
            ("training_corpus_sha256", "not-a-sha"),
            ("official_issuance_authorized", True),
        )
        for field, value in mutations:
            model = self.fit()
            model[field] = value
            model["model_sha256"] = digest({k: v for k, v in model.items() if k != "model_sha256"})
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.rank(model, [future_row()])
        for value in (0, True, 2, 7):
            model = self.fit()
            model["fit_evidence"]["nights"] = value
            model["model_sha256"] = digest({k: v for k, v in model.items() if k != "model_sha256"})
            with self.subTest(nights=value), self.assertRaises(ValueError):
                self.rank(model, [future_row()])

    def test_rehashed_single_class_parameters_cannot_claim_binary_readiness(self):
        model = self.fit()
        model["parameters"]["global"]["positives"] = 0
        for nodes in model["parameters"]["levels"].values():
            for node in nodes:
                node["positives"] = 0
        model["fit_evidence"].update(positives=0, negatives=6)
        model["model_sha256"] = digest({k: v for k, v in model.items() if k != "model_sha256"})
        with self.assertRaises(ValueError):
            self.rank(model, [future_row()])

    def test_rehashed_cutoff_cannot_precede_or_equal_training_observation_times(self):
        for cutoff in ("1900-01-01T00:00:00+09:00", "2026-10-03T23:49:59+09:00",
                       "2026-10-03T23:50:00+09:00"):
            model = self.fit()
            model["training_cutoff"] = cutoff
            model["model_sha256"] = digest({k: v for k, v in model.items() if k != "model_sha256"})
            with self.subTest(cutoff=cutoff), self.assertRaises(ValueError):
                self.rank(model, [future_row()])

    def test_model_preserves_actual_training_nights_and_latest_unit_time(self):
        model = self.fit()
        self.assertEqual(model.get("training_nights"), ["2026-10-01", "2026-10-02", "2026-10-03"])
        self.assertEqual(model.get("training_window_start_max"), "2026-10-03T23:50:00+09:00")
        for nights in (["2026-10-01", "2026-10-01", "2026-10-03"],
                       ["2026-10-03", "2026-10-02", "2026-10-01"],
                       ["2026-10-01", "2026-10-02"],
                       ["2026-10-01", "2026-10-02", "2026-10-24"]):
            changed = copy.deepcopy(model)
            changed["training_nights"] = nights
            changed["model_sha256"] = digest({k: v for k, v in changed.items() if k != "model_sha256"})
            with self.subTest(nights=nights), self.assertRaises(ValueError):
                self.rank(changed, [future_row()])
    def test_future_outcomes_duplicate_units_and_cutoff_equality_are_rejected(self):
        cases = []
        row = future_row()
        row["label"] = 0
        cases.append([row])
        cases.append([future_row("one"), future_row("two", start="2026-10-24T14:50:00+00:00")])
        row = future_row()
        row["feature_available_at"]["temperature_c"] = row["cutoff_time"]
        cases.append([row])
        cases.append([future_row(start="2026-10-24T18:00:00+09:00")])
        row = future_row()
        row["operational_night"] = "2026-10-25"
        cases.append([row])
        model = self.fit()
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.rank(model, rows)

    def test_partial_or_changed_future_universe_digest_is_rejected(self):
        rows = [future_row("known"), future_row("unseen", cell_x=6000)]
        with self.assertRaises(ValueError):
            self.h.rank_hierarchy(self.fit(), rows[:1],
                                   cutoff_time="2026-10-24T18:00:00+09:00",
                                   universe_sha256=digest(rows))

    def test_valid_large_universe_is_not_dropped_when_rank_diagnostics_expand_json(self):
        # The input is below the shared gate's 16MiB bound. All hierarchy
        # diagnostics can legitimately exceed it without narrowing the universe.
        rows = [future_row(f"unseen-{index}", cell_x=1000 + index % 5000,
                           cell_y=31000 + index // 5000)
                for index in range(20000)]
        output = self.rank(self.fit(), rows)
        self.assertEqual(len(output["unit_scores"]), 20000)
        self.assertEqual(sum(row["candidate_units"]
                             for row in output["hierarchy_rankings"]["1000m"]), 20000)
        self.assertEqual(output["prediction_sha256"], digest(
            {key: value for key, value in output.items() if key != "prediction_sha256"}))

    def test_full_eligible_training_capacity_has_a_reloadable_model(self):
        selection = selection_fixture()
        template = selection["accepted"][0]
        accepted = []
        for index in range(20000):
            row = copy.deepcopy(template)
            day, label = index % 3 + 1, index % 2
            row.update(row_id=f"capacity-{index:05}", night=f"2026-10-{day:02}",
                       window_start_jst=f"2026-10-{day:02}T23:50:00+09:00",
                       cell_x=1000 + (index % 800) * 10, cell_y=31000 + (index // 800) * 10,
                       label=label,
                       capture_event_ids=[f"capacity-event-{index}"] if label else [])
            accepted.append(row)
        selection["accepted"] = sorted(accepted, key=lambda r: (r["night"], r["window_start_jst"], r["row_id"]))
        selection["counts"].update(accepted_rows=20000, positives=10000, negatives=10000)
        selection["selection_sha256"] = digest({key: selection[key] for key in IDENTITY})
        model = self.h.fit_hierarchy(selection)
        self.assertEqual(model["fit_evidence"]["accepted_rows"], 20000)
        self.assertEqual(len(model["parameters"]["levels"]["1000m"]), 20000)
        output = self.rank(json.loads(json.dumps(model)), [future_row(cell_x=1000, cell_y=31000)])
        self.assertEqual(len(output["unit_scores"]), 1)

    def test_diagnostics_never_authorize_formal_targets_kpis_or_production(self):
        model = self.fit()
        output = self.rank(model, [future_row()])
        for artifact in (model, output):
            self.assertEqual(artifact["science_status"], "NOT_VALIDATED")
            self.assertFalse(artifact["production_activation_authorized"])
            self.assertFalse(artifact["official_stage1_recall_computed"])
            self.assertFalse(artifact["official_100m_10min_kpi_computed"])
        self.assertFalse(output["formal_100m_10min_targets_produced"])
        self.assertFalse(output["forecast_universe_completeness_verified"])
        self.assertEqual(output["route_status"], "NOT_PRODUCED")


if __name__ == "__main__":
    unittest.main()
