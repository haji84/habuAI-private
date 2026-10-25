"""Synthetic independent metric controls; these are not real capture evidence."""
import copy
from datetime import date, timedelta
import importlib
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from master_contracts import digest


def area(number):
    return f"utm52n_1km_{number}_3000"


def fixtures(count=1):
    universe = {"schema_version": "habu-stage1-universe-v1", "nights": []}
    ledger = {
        "schema_version": "habu-stage1-ledger-v1",
        "source_refs": [
            {"path": "evidence/synthetic-captures.json", "sha256": "a" * 64, "bytes": 20},
            {"path": "evidence/synthetic-coverage.json", "sha256": "b" * 64, "bytes": 10},
        ],
        "complete_scopes": [], "events": [],
    }
    candidates = []
    for candidate in ("uniform", "HB-A0", "HB-B1"):
        candidates.append({"candidate_id": candidate, "score_semantics": "NATIVE_DIAGNOSTIC_SCORE",
                           "model_sha256": "c" * 64, "prediction_sha256": "d" * 64, "scores": {}})
    for number in range(count):
        night = (date(2026, 10, 14) + timedelta(days=number)).isoformat()
        tomorrow = (date.fromisoformat(night) + timedelta(days=1)).isoformat()
        scope = {"crs": "EPSG:32652", "bbox_utm": [100000, 0, 900000, 10000000]}
        universe["nights"].append({
            "operational_night": night, "scope": scope, "scope_sha256": digest(scope),
            "cutoff_time": night + "T18:00:00+09:00", "horizon_start": night + "T19:00:00+09:00",
            "horizon_end": tomorrow + "T07:00:00+09:00", "area_ids": [area(i) for i in range(200, 212)],
        })
        ledger["complete_scopes"].append({
            "operational_night": night, "scope_sha256": digest(scope),
            "horizon_start": night + "T19:00:00+09:00", "horizon_end": tomorrow + "T07:00:00+09:00",
            "declaration": "DECLARED_COMPLETE", "coverage_ref": copy.deepcopy(ledger["source_refs"][1]),
            "source_paths": [ledger["source_refs"][0]["path"]],
        })
        for suffix, x, ids in (("inside", 200050, [f"{night}-i1", f"{night}-i2"]),
                               ("outside", 250050, [f"{night}-i3"])):
            ledger["events"].append({
                "event_id": f"{night}-{suffix}", "operational_night": night,
                "datetime": night + "T21:03:00+09:00", "utm_x_m": x, "utm_y_m": 3000050,
                "individual_ids": ids, "source_paths": [ledger["source_refs"][0]["path"]],
            })
        for candidate in candidates:
            reverse = candidate["candidate_id"] == "HB-B1"
            candidate["scores"][night] = {area(i): float(i if reverse else 1) for i in range(200, 212)}
    scores = {"schema_version": "habu-stage1-scores-v1", "universe_sha256": digest(universe),
              "candidates": candidates}
    ledger["ledger_sha256"] = digest(ledger)
    return universe, scores, ledger


def bind_ledger(value):
    value["ledger_sha256"] = digest({k: v for k, v in value.items() if k != "ledger_sha256"})
    return value


class FullLedgerStage1Tests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec("evaluation.full_ledger_stage1")
        self.assertIsNotNone(spec, "Independent full-ledger evaluator must be implemented")
        self.module = importlib.import_module("evaluation.full_ledger_stage1")
        self.universe, self.scores, self.ledger = fixtures()

    def run_metric(self, **options):
        return self.module.evaluate_full_ledger_stage1(self.universe, self.scores, self.ledger, **options)

    def test_outside_universe_individual_is_a_miss_and_two_individual_event_counts_two(self):
        result = self.run_metric()
        night = result["per_night"][0]
        self.assertEqual(night["denominator"], 3)
        self.assertEqual(night["denominator_events"], 2)
        self.assertEqual(night["outside_universe_individuals"], 1)
        self.assertEqual(night["candidates"]["uniform"]["numerator"], 2)
        self.assertAlmostEqual(result["pooled"]["uniform"]["recall"], 2 / 3)
        self.assertEqual(result["pooled"]["HB-B1"]["numerator"], 0)

    def test_ties_use_lexical_area_identity_and_unique_top10(self):
        for candidate in self.scores["candidates"]:
            candidate["scores"]["2026-10-14"] = {area(i): 1 for i in reversed(range(200, 212))}
        result = self.run_metric()
        for candidate in result["per_night"][0]["candidates"].values():
            self.assertEqual(candidate["top10_area_ids"], [area(i) for i in range(200, 210)])
            self.assertEqual(len(set(candidate["top10_area_ids"])), 10)

    def test_pooled_is_ratio_of_counts_not_mean_of_nightly_recalls(self):
        self.universe, self.scores, self.ledger = fixtures(2)
        self.ledger["events"][2]["individual_ids"].extend(f"extra-{i}" for i in range(8))
        bind_ledger(self.ledger)
        result = self.run_metric()
        pooled = result["pooled"]["uniform"]
        self.assertEqual((pooled["numerator"], pooled["denominator"]), (12, 14))
        self.assertAlmostEqual(pooled["recall"], 12 / 14)
        self.assertNotAlmostEqual(pooled["recall"], ((2 / 3) + (10 / 11)) / 2)

    def test_one_hundred_percent_diagnostic_never_grants_science_or_authority(self):
        self.ledger["events"][1]["utm_x_m"] = 200060
        bind_ledger(self.ledger)
        result = self.run_metric()
        self.assertEqual(result["status"], "DIAGNOSTIC_ONLY")
        self.assertEqual(result["pooled"]["uniform"]["recall"], 1)
        self.assertEqual(result["scientific_status"], "NOT_VALIDATED")
        for flag in ("source_authenticated", "confirmation_source_authenticated", "official_stage1_recall_computed",
                     "official_threshold_pass", "fit_authorized", "production_authorized"):
            self.assertIs(result[flag], False)
        self.assertEqual(result["receipt_sha256"], digest({k: v for k, v in result.items() if k != "receipt_sha256"}))

    def test_none_inputs_need_more_data_without_partial_metrics(self):
        result = self.module.evaluate_full_ledger_stage1(None, None, None)
        self.assertEqual(result["status"], "NEED_MORE_DATA")
        self.assertEqual((result["per_night"], result["pooled"]), ([], {}))

    def test_missing_or_noncomplete_scope_does_not_release_partial_metrics(self):
        for mode in ("missing", "unknown", "incomplete"):
            self.universe, self.scores, self.ledger = fixtures(2)
            if mode == "missing":
                self.ledger["complete_scopes"].pop()
            else:
                self.ledger["complete_scopes"][-1]["declaration"] = mode.upper()
            bind_ledger(self.ledger)
            result = self.run_metric()
            self.assertEqual(result["status"], "NEED_MORE_DATA")
            self.assertEqual((result["per_night"], result["pooled"], result["paired_uncertainty"]), ([], {}, {}))

    def test_complete_declared_empty_ledger_is_zero_with_null_recall(self):
        self.ledger["events"] = []
        bind_ledger(self.ledger)
        result = self.run_metric()
        self.assertEqual(result["pooled"]["uniform"]["denominator"], 0)
        self.assertIsNone(result["pooled"]["uniform"]["recall"])

    def test_missing_empty_duplicate_event_or_individual_ids_never_default_to_one(self):
        for mutation in ("missing", "empty", "duplicate_individual", "duplicate_event"):
            self.universe, self.scores, self.ledger = fixtures()
            if mutation == "missing":
                self.ledger["events"][0].pop("individual_ids")
            elif mutation == "empty":
                self.ledger["events"][0]["individual_ids"] = []
            elif mutation == "duplicate_individual":
                self.ledger["events"][1]["individual_ids"] = self.ledger["events"][0]["individual_ids"][:1]
            else:
                self.ledger["events"][1]["event_id"] = self.ledger["events"][0]["event_id"]
            bind_ledger(self.ledger)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.run_metric()

    def test_event_cannot_escape_night_horizon_or_actual_geographic_scope(self):
        for field, value in (("datetime", "2026-10-15T07:00:00+09:00"),
                             ("datetime", "2026-10-14T18:59:59+09:00"),
                             ("datetime", "2026-10-14T21:00:00"),
                             ("operational_night", "2026-10-15"), ("utm_x_m", 900001),
                             ("utm_y_m", True)):
            self.universe, self.scores, self.ledger = fixtures()
            self.ledger["events"][0][field] = value
            bind_ledger(self.ledger)
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.run_metric()

    def test_early_morning_is_previous_operational_night_and_timezone_aliases_agree(self):
        self.ledger["events"][0]["datetime"] = "2026-10-14T17:03:00Z"
        bind_ledger(self.ledger)
        result = self.run_metric()
        self.assertEqual(result["per_night"][0]["operational_night"], "2026-10-14")
        self.assertEqual(result["per_night"][0]["denominator"], 3)

    def test_source_hash_scope_hash_and_reference_binding_are_checked(self):
        for mutation in ("ledger_hash", "source_hash", "scope_hash", "unbound_event", "coverage_ref", "path"):
            self.universe, self.scores, self.ledger = fixtures()
            if mutation == "ledger_hash":
                self.ledger["ledger_sha256"] = "0" * 64
            elif mutation == "source_hash":
                self.ledger["source_refs"][0]["sha256"] = "invalid"
            elif mutation == "scope_hash":
                self.ledger["complete_scopes"][0]["scope_sha256"] = "f" * 64
            elif mutation == "unbound_event":
                self.ledger["events"][0]["source_paths"] = ["evidence/not-bound.json"]
            elif mutation == "coverage_ref":
                self.ledger["complete_scopes"][0]["coverage_ref"]["sha256"] = "f" * 64
            else:
                self.ledger["source_refs"][0]["path"] = "evidence/../outside.json"
            if mutation != "ledger_hash":
                bind_ledger(self.ledger)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.run_metric()

    def test_no_candidate_may_narrow_expand_or_rebind_the_universe(self):
        for mutation in ("missing_area", "extra_area", "extra_night", "wrong_hash", "bool_score", "nan_score"):
            self.universe, self.scores, self.ledger = fixtures()
            scores = self.scores["candidates"][1]["scores"]
            if mutation == "missing_area":
                scores["2026-10-14"].pop(area(200))
            elif mutation == "extra_area":
                scores["2026-10-14"][area(250)] = 1
            elif mutation == "extra_night":
                scores["2026-10-15"] = scores["2026-10-14"]
            elif mutation == "wrong_hash":
                self.scores["universe_sha256"] = "f" * 64
            else:
                scores["2026-10-14"][area(200)] = True if mutation == "bool_score" else float("nan")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.run_metric()

    def test_fixed_candidate_registry_and_uniform_requirement(self):
        for mutation in ("no_uniform", "duplicate", "unknown", "four"):
            self.universe, self.scores, self.ledger = fixtures()
            if mutation == "no_uniform":
                self.scores["candidates"].pop(0)
            elif mutation == "duplicate":
                self.scores["candidates"][1]["candidate_id"] = "uniform"
            elif mutation == "unknown":
                self.scores["candidates"][1]["candidate_id"] = "unregistered"
            else:
                self.scores["candidates"].append(copy.deepcopy(self.scores["candidates"][1]))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.run_metric()

    def test_input_objects_are_not_mutated_and_no_files_are_opened(self):
        before = copy.deepcopy((self.universe, self.scores, self.ledger))
        with patch("builtins.open", side_effect=AssertionError("No evidence or sealed reads")), \
             patch.object(Path, "open", side_effect=AssertionError("No evidence or sealed reads")):
            result = self.run_metric()
        self.assertEqual((self.universe, self.scores, self.ledger), before)
        self.assertEqual(result["scientific_status"], "NOT_VALIDATED")

    def test_paired_night_bootstrap_has_hand_computable_weighted_endpoints(self):
        self.universe, self.scores, self.ledger = fixtures(2)
        self.ledger["events"][2]["utm_x_m"] = 211050
        self.ledger["events"][2]["individual_ids"].extend(f"extra-{i}" for i in range(8))
        bind_ledger(self.ledger)
        result = self.run_metric()
        uncertainty = result["paired_uncertainty"]
        self.assertEqual(uncertainty["method"], "PAIRED_NIGHT_BLOCK_BOOTSTRAP")
        self.assertEqual((uncertainty["seed"], uncertainty["replicates"]), (0, 2000))
        self.assertEqual((uncertainty["valid_replicates"], uncertainty["zero_denominator_draws"]), (2000, 0))
        identical = uncertainty["comparisons"]["HB-A0"]
        self.assertEqual(identical["interval_95"], [0, 0])
        different = uncertainty["comparisons"]["HB-B1"]
        self.assertAlmostEqual(different["pooled_recall_difference"], 8 / 14)
        self.assertEqual(different["interval_95"], [-2 / 3, 10 / 11])
        self.assertEqual(result, self.run_metric())

    def test_small_n_withholds_interval_and_five_nights_do_not_prove_adequacy(self):
        for count in (1, 4, 5):
            self.universe, self.scores, self.ledger = fixtures(count)
            result = self.run_metric()
            uncertainty = result["paired_uncertainty"]
            self.assertEqual(uncertainty["night_count"], count)
            self.assertEqual(uncertainty["informative_night_count"], count)
            self.assertEqual(uncertainty["minimum_nights_status"],
                             "BELOW_PROCESS_FLOOR" if count < 5 else "MET_NOT_SUFFICIENT")
            self.assertEqual(uncertainty["adequacy"], "NOT_ESTABLISHED")
            self.assertEqual(uncertainty["independence"], "NOT_VERIFIED")
            if count == 1:
                self.assertIsNone(uncertainty["comparisons"]["HB-B1"]["interval_95"])
                self.assertEqual(uncertainty["comparisons"]["HB-B1"]["status"], "TOO_FEW_INFORMATIVE_NIGHTS")
            self.assertIs(result["official_threshold_pass"], False)

    def test_zero_denominator_draws_are_counted_and_never_silently_converted(self):
        self.universe, self.scores, self.ledger = fixtures(2)
        self.ledger["events"] = []
        bind_ledger(self.ledger)
        empty = self.run_metric()["paired_uncertainty"]
        self.assertEqual((empty["valid_replicates"], empty["zero_denominator_draws"]), (0, 2000))
        self.assertIsNone(empty["comparisons"]["HB-B1"]["pooled_recall_difference"])
        self.assertIsNone(empty["comparisons"]["HB-B1"]["interval_95"])
        self.universe, self.scores, self.ledger = fixtures(2)
        self.ledger["events"] = self.ledger["events"][:2]
        bind_ledger(self.ledger)
        mixed = self.run_metric()["paired_uncertainty"]
        self.assertGreater(mixed["zero_denominator_draws"], 0)
        self.assertEqual(mixed["valid_replicates"] + mixed["zero_denominator_draws"], 2000)
        self.assertEqual(mixed["informative_night_count"], 1)
        self.assertIsNone(mixed["comparisons"]["HB-B1"]["interval_95"])

    def test_native_semantics_and_unique_area_totals_remain_explicit(self):
        result = self.run_metric()
        self.assertEqual(result["candidate_lineage"]["HB-B1"]["score_semantics"], "NATIVE_DIAGNOSTIC_SCORE")
        self.assertEqual(result["candidate_lineage"]["HB-B1"]["model_sha256"], "c" * 64)
        self.assertEqual(result["unique_forecast_areas"], 12)
        self.assertEqual(result["unique_actual_areas"], 2)

    def test_invalid_budgets_are_rejected_without_implicit_coercion(self):
        for value in (True, 0, -1, float("nan"), float("inf"), 301, "30"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_metric(budget_seconds=value)

    def test_deadline_is_shared_and_rechecked_after_final_receipt_seal(self):
        with patch.object(self.module.time, "monotonic", side_effect=[0, 1]):
            with self.assertRaises(self.module.Stage1BudgetBlocked):
                self.run_metric(budget_seconds=1)
        for inputs in ((None, None, None), fixtures(2)):
            clock = [0]
            original = self.module._digest

            def digest_then_expire(value, check):
                result = original(value, check)
                if type(value) is dict and "status" in value:
                    clock[0] = 1
                return result

            with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]), \
                 patch.object(self.module, "_digest", side_effect=digest_then_expire):
                with self.subTest(inputs_missing=inputs[0] is None), self.assertRaises(self.module.Stage1BudgetBlocked):
                    self.module.evaluate_full_ledger_stage1(*inputs, budget_seconds=1)

    def test_capacities_raise_explicit_block_without_truncating_the_cohort(self):
        for constant, limit in (("MAX_NIGHTS", 0), ("MAX_AREA_NIGHT_CELLS", 11),
                                ("MAX_EVENTS", 1), ("MAX_INDIVIDUALS", 2),
                                ("MAX_JSON_BYTES", 100), ("MAX_JSON_NODES", 5)):
            with patch.object(self.module, constant, limit):
                with self.subTest(constant=constant), self.assertRaises(self.module.Stage1CapacityBlocked):
                    self.run_metric()

    def test_stream_byte_limit_stops_before_consuming_remaining_encoder_chunks(self):
        seen = []

        class Encoder:
            def __init__(self, **options):
                pass

            def iterencode(self, value):
                for chunk in ('[', '"' + 'x' * 20 + '"', ']'):
                    seen.append(chunk)
                    yield chunk

        with patch.object(self.module.json, "JSONEncoder", Encoder), patch.object(self.module, "MAX_JSON_BYTES", 10):
            with self.assertRaises(self.module.Stage1CapacityBlocked):
                self.module._copy_json([], lambda: None)
        self.assertEqual(len(seen), 2)

    def test_recursive_or_non_json_inputs_and_unknown_keys_are_rejected(self):
        recursive = []
        recursive.append(recursive)
        with self.assertRaises(self.module.Stage1CapacityBlocked):
            self.module.evaluate_full_ledger_stage1(recursive, None, None)
        for value in ({"unknown": object()}, {"unknown": {1: 2}}):
            with self.assertRaises(ValueError):
                self.module.evaluate_full_ledger_stage1(value, None, None)
        self.universe["source_authenticated"] = True
        with self.assertRaises(ValueError):
            self.run_metric()

    def test_uniform_baseline_cannot_be_a_disguised_spatial_ranking(self):
        self.scores["candidates"][0]["scores"]["2026-10-14"][area(211)] = 100
        with self.assertRaises(ValueError):
            self.run_metric()

    def test_datetime_overflow_and_enormous_numeric_budget_are_value_errors(self):
        for case in ("night", "event", "budget"):
            self.universe, self.scores, self.ledger = fixtures()
            options = {}
            if case == "night":
                self.universe["nights"][0]["operational_night"] = "9999-12-31"
            elif case == "event":
                self.ledger["events"][0]["datetime"] = "0001-01-01T00:00:00+14:00"
                bind_ledger(self.ledger)
            else:
                options["budget_seconds"] = 10 ** 1000
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.run_metric(**options)

    def test_deadline_expiry_during_resampling_cannot_return_a_candidate_result(self):
        self.universe, self.scores, self.ledger = fixtures(2)
        clock = [0]

        class ExpiringRandom:
            def __init__(self, seed):
                pass

            def randrange(self, count):
                clock[0] = 1
                return 0

        with patch.object(self.module.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(self.module.random, "Random", ExpiringRandom):
            with self.assertRaises(self.module.Stage1BudgetBlocked):
                self.run_metric(budget_seconds=1)

    def test_exact_07_boundary_and_uniform_only_registry_remain_supported(self):
        self.universe["nights"][0]["cutoff_time"] = "2026-10-14T06:59:59+09:00"
        self.universe["nights"][0]["horizon_start"] = "2026-10-14T07:00:00+09:00"
        self.ledger["complete_scopes"][0]["horizon_start"] = "2026-10-14T07:00:00+09:00"
        self.ledger["events"][0]["datetime"] = "2026-10-14T07:00:00+09:00"
        self.scores["candidates"] = self.scores["candidates"][:1]
        self.scores["universe_sha256"] = digest(self.universe)
        bind_ledger(self.ledger)
        result = self.run_metric()
        self.assertEqual(result["pooled"]["uniform"]["denominator"], 3)
        self.assertEqual(result["paired_uncertainty"]["comparisons"], {})
        self.ledger["events"][0]["datetime"] = "2026-10-14T06:59:59+09:00"
        bind_ledger(self.ledger)
        with self.assertRaises(ValueError):
            self.run_metric()

    def test_control_characters_are_not_canonical_source_references(self):
        for value in ("evidence/hidden\x00.json", "evidence/hidden\n.json", "evidence/hidden\x7f.json"):
            self.universe, self.scores, self.ledger = fixtures()
            self.ledger["source_refs"][0]["path"] = value
            self.ledger["events"][0]["source_paths"] = [value]
            self.ledger["events"][1]["source_paths"] = [value]
            self.ledger["complete_scopes"][0]["source_paths"] = [value]
            bind_ledger(self.ledger)
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_metric()


if __name__ == "__main__":
    unittest.main()
