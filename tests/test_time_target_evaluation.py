"""Synthetic T2 contracts; frozen legacy source runs on the same actual runtime."""
import ast
import copy
from datetime import datetime, timedelta, timezone
import functools
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codex_cycle_contract import POLICY_DIGEST
from evaluation import full_ledger_stage1 as stage1

try:
    import time_target_evaluation as t2
    from event_matching import ordered_event_owners
except ModuleNotFoundError:
    t2 = None
    ordered_event_owners = None


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def seal(value, key):
    value[key] = digest({k: v for k, v in value.items() if k != key})
    return value


def stamp(clock):
    return "2026-09-30T" + clock + "+09:00"


def fixture():
    scope = {"crs": "EPSG:32652", "bbox_utm": [299000, 2999000, 302000, 3002000]}
    universe = {"schema_version": "habu-time-target-universe-v1",
                "operational_night": "2026-09-30", "cutoff_time": stamp("19:00:00"),
                "horizon_start": stamp("20:00:00"), "horizon_end": stamp("23:00:00"),
                "scope": scope, "scope_sha256": digest(scope),
                "forecast_receipt_sha256": "a" * 64, "joined_forecast_sha256": "b" * 64,
                "units": [{"row_id": ident, "window_start_jst": stamp(clock),
                           "utm_x_m": 300050, "utm_y_m": 3000050}
                          for ident, clock in (("a", "21:00:00"), ("b", "21:10:00"), ("c", "20:50:00"))]}
    targets = {"schema_version": "habu-time-target-set-v1", "produced": True,
               "model_sha256": "c" * 64, "prediction_sha256": "d" * 64,
               "universe_sha256": None,
               "targets": [{"target_id": "A", "universe_row_id": "a", "predicted_time": stamp("21:05:00")},
                           {"target_id": "B", "universe_row_id": "b", "predicted_time": stamp("21:15:00")}]}
    source = {"path": "evidence/synthetic/captures.json", "sha256": "e" * 64, "bytes": 123}
    ledger = {"schema_version": "habu-stage1-ledger-v1", "source_refs": [source],
              "complete_scopes": [{"operational_night": "2026-09-30", "scope_sha256": digest(scope),
                  "horizon_start": universe["horizon_start"], "horizon_end": universe["horizon_end"],
                  "declaration": "DECLARED_COMPLETE", "coverage_ref": copy.deepcopy(source),
                  "source_paths": [source["path"]]}],
              "events": [{"event_id": ident, "operational_night": "2026-09-30", "datetime": stamp(clock),
                          "utm_x_m": 300050, "utm_y_m": 3000050, "individual_ids": ids,
                          "source_paths": [source["path"]]}
                         for ident, clock, ids in (("E1", "21:08:00", ["I1", "I2"]),
                                                   ("E2", "20:57:00", ["I3"]))]}
    protocol = {"schema_version": "habu-time-target-diagnostic-protocol-v1", "phase": "DEVELOPMENT",
                "g0_policy_sha256": POLICY_DIGEST, "target_semantics": "OWNER_CAPTURE_EVENT_POINT_TIME",
                "operational_night": "2026-09-30", "cutoff_time": universe["cutoff_time"],
                "horizon_start": universe["horizon_start"], "horizon_end": universe["horizon_end"],
                "scope_sha256": digest(scope), "universe_sha256": None, "targets_sha256": None,
                "frozen_at": universe["cutoff_time"], "time_anchor": "WINDOW_MIDPOINT_300_SECONDS",
                "radius_m": 100, "tolerance_seconds": 600, "matching_policy": "ORDERED_DFS_MAX_EVENT_CARDINALITY_V1"}
    return rebound(universe, targets, ledger, protocol)


def rebound(universe, targets, ledger, protocol):
    if universe is not None:
        seal(universe, "universe_sha256")
        protocol["universe_sha256"] = universe["universe_sha256"]
    if targets is not None:
        if universe is not None:
            targets["universe_sha256"] = universe["universe_sha256"]
        seal(targets, "targets_sha256")
        protocol["targets_sha256"] = targets["targets_sha256"]
    if ledger is not None:
        seal(ledger, "ledger_sha256")
    return universe, targets, ledger, protocol


def evaluate(values, **kwargs):
    universe, targets, ledger, protocol = values
    return t2.evaluate_time_targets(universe, targets, ledger, protocol=protocol,
                                   expected_protocol_sha256=digest(protocol), **kwargs)


class TimeTargetContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(t2, "new bounded T2 API is required")

    def test_greedy_trap_uses_two_events_and_three_individuals(self):
        result = evaluate(fixture())
        self.assertEqual(result["status"], "DIAGNOSTIC_ONLY")
        self.assertEqual([(m["target_id"], m["event_id"]) for m in result["matching"]], [("A", "E2"), ("B", "E1")])
        self.assertEqual(result["metrics"]["event_numerator"], 2)
        self.assertEqual(result["metrics"]["event_denominator"], 2)
        self.assertEqual(result["metrics"]["individuals_in_matched_events"], 3)
        self.assertEqual(result["metrics"]["individual_denominator"], 3)
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["false_positives"])

    def test_exact_utm_100m_and_600seconds_are_inclusive(self):
        u, t, l, p = fixture()
        t["targets"] = t["targets"][:1]
        l["events"] = l["events"][:1]
        l["events"][0].update(datetime=stamp("21:15:00"), utm_x_m=300150)
        u["units"].append({"row_id": "neighbor", "window_start_jst": stamp("21:10:00"),
                           "utm_x_m": 300150, "utm_y_m": 3000050})
        result = evaluate(rebound(u, t, l, p))
        self.assertEqual(result["matching"][0]["distance_m"], 100)
        self.assertEqual(result["matching"][0]["time_delta_seconds"], 600)
        l["events"][0]["utm_x_m"] += 0.00001
        self.assertEqual(evaluate(rebound(u, t, l, p))["metrics"]["event_numerator"], 0)

    def test_outside_universe_close_event_is_fn_and_neighbor_unit_can_match(self):
        u, t, l, p = fixture()
        t["targets"] = t["targets"][:1]
        l["events"] = l["events"][:1]
        l["events"][0]["utm_x_m"] = 300149
        result = evaluate(rebound(u, t, l, p))
        self.assertEqual(result["metrics"]["false_negative_events"], 1)
        self.assertEqual(result["outside_universe_event_ids"], ["E1"])
        u["units"].append({"row_id": "neighbor", "window_start_jst": stamp("21:00:00"),
                           "utm_x_m": 300150, "utm_y_m": 3000050})
        result = evaluate(rebound(u, t, l, p))
        self.assertEqual(result["metrics"]["event_numerator"], 1)
        self.assertEqual(result["outside_universe_event_ids"], [])

    def test_abstention_is_not_missing_output(self):
        u, t, l, p = fixture()
        t["targets"] = []
        result = evaluate(rebound(u, t, l, p))
        self.assertEqual(result["status"], "DIAGNOSTIC_ONLY")
        self.assertEqual(result["metrics"]["event_recall"], 0)
        l["events"] = []
        self.assertIsNone(evaluate(rebound(u, t, l, p))["metrics"]["event_recall"])
        t["produced"] = False
        result = evaluate(rebound(u, t, l, p))
        self.assertEqual(result["status"], "NEED_MORE_DATA")
        self.assertEqual(result["metrics"], {})
        self.assertIn("TARGETS_NOT_PRODUCED", result["blockers"])

    def test_prior_night_cutoff_is_valid(self):
        u, t, l, p = fixture()
        p["cutoff_time"] = u["cutoff_time"] = p["frozen_at"] = "2026-09-29T18:00:00+09:00"
        self.assertEqual(evaluate(rebound(u, t, l, p))["status"], "DIAGNOSTIC_ONLY")

    def test_exact_output_fields_bind_full_inputs_and_false_authority(self):
        values = fixture()
        result = evaluate(values)
        self.assertEqual(set(result), set("schema_version status operational_night protocol_sha256 input_digests blockers metrics matching unmatched_target_ids unmatched_event_ids outside_universe_event_ids precision false_positives source_authentication prereveal_authentication statistical_adequacy fit_authorized scientific_authorized confirmation_authorized selection_authorized official_100m_10min_kpi_computed production_authorized receipt_sha256".split()))
        self.assertEqual(result["receipt_sha256"], digest({k: v for k, v in result.items() if k != "receipt_sha256"}))
        self.assertEqual(result["input_digests"], dict(zip(("universe", "targets", "ledger"), map(digest, values[:3]))))
        self.assertNotEqual(result["input_digests"]["universe"], values[0]["universe_sha256"])
        self.assertEqual(result["source_authentication"], "NOT_ATTESTED")
        self.assertEqual(result["prereveal_authentication"], "NOT_ATTESTED")
        self.assertEqual(result["statistical_adequacy"], "NOT_ASSESSED")
        for name in ("fit_authorized", "scientific_authorized", "confirmation_authorized", "selection_authorized",
                     "official_100m_10min_kpi_computed", "production_authorized"):
            self.assertIs(result[name], False)

    def test_secondary_count_does_not_reoptimize_event_tie(self):
        u, t, l, p = fixture()
        t["targets"] = t["targets"][:1]
        l["events"][0]["individual_ids"] = ["one"]
        l["events"][1].update(datetime=l["events"][0]["datetime"], individual_ids=["two", "three"])
        result = evaluate(rebound(u, t, l, p))
        self.assertEqual(result["matching"][0]["event_id"], "E1")
        self.assertEqual(result["metrics"]["event_recall"], .5)
        self.assertEqual(result["metrics"]["secondary_individual_coverage"], 1 / 3)

    def test_permutations_preserve_assignment_and_metrics(self):
        values = fixture()
        original = evaluate(values)
        for order in itertools.permutations(range(3)):
            u, t, l, p = copy.deepcopy(values)
            u["units"] = [u["units"][index] for index in order]
            t["targets"].reverse()
            l["events"].reverse()
            current = evaluate(rebound(u, t, l, p))
            self.assertEqual(current["matching"], original["matching"])
            self.assertEqual(current["metrics"], original["metrics"])

    def test_utc_aliases_share_units_and_match(self):
        u, t, l, p = fixture()
        original = evaluate((u, t, l, p))
        for row, keys in ((u, ("cutoff_time", "horizon_start", "horizon_end")),
                          (p, ("cutoff_time", "horizon_start", "horizon_end", "frozen_at")),
                          (l["complete_scopes"][0], ("horizon_start", "horizon_end"))):
            for key in keys:
                row[key] = datetime.fromisoformat(row[key]).astimezone(timezone.utc).isoformat()
        for row in u["units"]:
            row["window_start_jst"] = datetime.fromisoformat(row["window_start_jst"]).astimezone(timezone.utc).isoformat()
        for row in t["targets"]:
            row["predicted_time"] = datetime.fromisoformat(row["predicted_time"]).astimezone(timezone.utc).isoformat()
        for row in l["events"]:
            row["datetime"] = datetime.fromisoformat(row["datetime"]).astimezone(timezone.utc).isoformat()
        current = evaluate(rebound(u, t, l, p))
        self.assertEqual(current["matching"], original["matching"])
        self.assertEqual(current["metrics"], original["metrics"])

    def test_just_after_temporal_tolerance_is_not_match(self):
        u, t, l, p = fixture()
        t["targets"] = t["targets"][:1]
        l["events"] = l["events"][:1]
        l["events"][0]["datetime"] = stamp("21:15:00.000001")
        result = evaluate(rebound(u, t, l, p))
        self.assertEqual(result["metrics"]["event_numerator"], 0)
        self.assertEqual(result["outside_universe_event_ids"], [])

    def test_last_whole_window_and_seven_am_event_boundary(self):
        u, t, l, p = fixture()
        u["horizon_start"] = p["horizon_start"] = stamp("20:00:00")
        u["horizon_end"] = p["horizon_end"] = "2026-10-01T07:00:00+09:00"
        l["complete_scopes"][0]["horizon_end"] = p["horizon_end"]
        u["units"] = [dict(u["units"][0], window_start_jst="2026-10-01T06:50:00+09:00")]
        t["targets"] = [dict(t["targets"][0], predicted_time="2026-10-01T06:55:00+09:00")]
        l["events"] = [dict(l["events"][0], datetime="2026-10-01T06:59:59.999999+09:00")]
        self.assertEqual(evaluate(rebound(u, t, l, p))["metrics"]["event_numerator"], 1)
        l["events"][0]["datetime"] = "2026-10-01T07:00:00+09:00"
        with self.assertRaises(ValueError):
            evaluate(rebound(u, t, l, p))

    def test_missing_and_incomplete_return_no_partial_lists(self):
        for mask in range(1, 8):
            values = list(fixture())
            for index in range(3):
                if mask & (1 << index):
                    values[index] = None
            result = evaluate(values)
            self.assertEqual(result["status"], "NEED_MORE_DATA")
            self.assertEqual(result["metrics"], {})
            for key in ("matching", "unmatched_target_ids", "unmatched_event_ids", "outside_universe_event_ids"):
                self.assertEqual(result[key], [])
        for declaration in ("UNKNOWN", "INCOMPLETE", None):
            u, t, l, p = fixture()
            if declaration is None:
                l["complete_scopes"] = []
            else:
                l["complete_scopes"][0]["declaration"] = declaration
            result = evaluate(rebound(u, t, l, p))
            self.assertEqual(result["metrics"], {})
            self.assertIn("COMPLETE_LEDGER_REQUIRED", result["blockers"])

    def test_missing_freeze_and_lineage_are_explicit(self):
        u, t, l, p = fixture()
        t["model_sha256"] = t["prediction_sha256"] = p["frozen_at"] = None
        result = evaluate(rebound(u, t, l, p))
        self.assertEqual(result["blockers"], ["DECLARED_FREEZE_REQUIRED", "PREDICTION_LINEAGE_REQUIRED"])
        self.assertEqual(result["metrics"], {})

    def test_known_scope_and_horizon_contradictions_even_without_universe(self):
        mutations = [lambda l: l["complete_scopes"][0].update(scope_sha256="f" * 64),
                     lambda l: l["complete_scopes"][0].update(horizon_end=stamp("23:10:00")),
                     lambda l: l["events"][0].update(datetime=stamp("23:01:00")),
                     lambda l: l["events"][0].update(utm_x_m=99999),
                     lambda l: l["events"][0].update(operational_night="2026-09-29")]
        for change in mutations:
            with self.subTest(change=change):
                u, t, l, p = fixture()
                change(l)
                with self.assertRaises(ValueError):
                    evaluate(rebound(None, t, l, p))

    def test_supplied_point_outside_scope_is_invalid_not_filtered(self):
        u, t, l, p = fixture()
        l["events"][0]["utm_x_m"] = 303000
        with self.assertRaises(ValueError):
            evaluate(rebound(u, None, l, p))

    def test_missing_input_does_not_hide_late_freeze_or_target_contradictions(self):
        for change in (lambda t, p: p.update(frozen_at=stamp("19:00:00.000001")),
                       lambda t, p: t["targets"][0].update(predicted_time=stamp("19:00:00")),
                       lambda t, p: t.update(universe_sha256="f" * 64),
                       lambda t, p: t.update(produced=False)):
            u, t, l, p = fixture()
            change(t, p)
            with self.assertRaises(ValueError):
                evaluate(rebound(None, t, None, p))

    def test_unproduced_known_nonnull_binding_cannot_contradict_protocol(self):
        u, t, l, p = fixture()
        t.update(produced=False, targets=[], universe_sha256="f" * 64)
        seal(t, "targets_sha256")
        p["targets_sha256"] = t["targets_sha256"]
        with self.assertRaises(ValueError):
            evaluate((u, t, l, p))

    def test_unproduced_nullable_lineage_is_need_not_fabricated_prediction(self):
        u, t, l, p = fixture()
        t.update(produced=False, targets=[], model_sha256=None, prediction_sha256=None, universe_sha256=None)
        seal(t, "targets_sha256")
        p["targets_sha256"] = t["targets_sha256"]
        result = evaluate((u, t, l, p))
        self.assertEqual(result["blockers"], ["TARGETS_NOT_PRODUCED"])
        self.assertEqual(result["metrics"], {})

    def test_unselected_universe_rows_are_validated(self):
        for updates in ({"utm_x_m": 400000}, {"window_start_jst": stamp("22:55:00")},
                        {"row_id": "a"}, {"utm_y_m": False}):
            u, t, l, p = fixture()
            u["units"][2].update(updates)
            with self.assertRaises(ValueError):
                evaluate(rebound(u, t, l, p))

    def test_projection_hash_and_protocol_bindings_are_checked(self):
        for index, key in ((0, "universe_sha256"), (1, "targets_sha256"), (2, "ledger_sha256")):
            values = list(fixture())
            values[index][key] = "f" * 64
            with self.assertRaises(ValueError):
                evaluate(values)
        for key in ("universe_sha256", "targets_sha256"):
            values = list(fixture())
            values[3][key] = None
            with self.assertRaises(ValueError):
                evaluate(values)
        values = fixture()
        with self.assertRaises(ValueError):
            t2.evaluate_time_targets(*values[:3], protocol=values[3], expected_protocol_sha256="f" * 64)

    def test_duplicate_ids_and_alias_unit_keys_reject(self):
        mutations = [lambda u, t, l: u["units"].append(copy.deepcopy(u["units"][0])),
                     lambda u, t, l: u["units"].append(dict(u["units"][0], row_id="alias")),
                     lambda u, t, l: t["targets"].append(copy.deepcopy(t["targets"][0])),
                     lambda u, t, l: t["targets"].append(dict(t["targets"][0], target_id="alias")),
                     lambda u, t, l: l["events"].append(copy.deepcopy(l["events"][0])),
                     lambda u, t, l: l["events"][1].update(individual_ids=["I1"])]
        for change in mutations:
            with self.subTest(change=change):
                u, t, l, p = fixture()
                change(u, t, l)
                with self.assertRaises(ValueError):
                    evaluate(rebound(u, t, l, p))

    def test_unknown_geometry_proxy_and_invalid_known_types_reject(self):
        mutations = [lambda u, t, l, p: u["units"][0].update(point_geometry="CELL_ORIGIN_PROXY_NOT_POINT_GEOMETRY"),
                     lambda u, t, l, p: u["scope"].update(crs="EPSG:4326"),
                     lambda u, t, l, p: u["units"][0].update(utm_x_m=True),
                     lambda u, t, l, p: u["units"][0].update(window_start_jst=stamp("21:01:00")),
                     lambda u, t, l, p: t.update(produced=1),
                     lambda u, t, l, p: p.update(radius_m=100.0),
                     lambda u, t, l, p: t["targets"][0].update(universe_row_id="missing"),
                     lambda u, t, l, p: l["events"][0].update(event_id="bad\nidentity"),
                     lambda u, t, l, p: l["events"][0].update(individual_ids=[]),
                     lambda u, t, l, p: l["events"][0].update(source_paths=[])]
        for change in mutations:
            with self.subTest(change=change):
                values = fixture()
                change(*values)
                with self.assertRaises(ValueError):
                    evaluate(rebound(*values))

    def test_invalid_dates_and_naive_times_reject_even_missing(self):
        for key, value in (("operational_night", "9999-12-31"), ("cutoff_time", "0001-01-01T00:00:00+09:00"),
                           ("horizon_start", "2026-09-30T20:00:00"), ("horizon_end", "not-time")):
            p = fixture()[3]
            p[key] = value
            with self.assertRaises(ValueError):
                evaluate((None, None, None, p))

    def test_actual_sept28_five_events_six_individuals_do_not_supply_t2_denominator(self):
        # Actual immutable Git source bytes; no invented target/scope/completeness.
        from evaluation.stage1_source_adapter import _captures, _individuals
        root = Path(__file__).resolve().parents[1]
        paths = ["data/processed/capture_events/2026/2026-09-28.csv",
                 "data/processed/individuals/2026/2026-09-28.csv"]
        refs, raw = [], []
        for path in paths:
            value = subprocess.check_output(["git", "show", "HEAD:" + path], cwd=root)
            raw.append(value)
            refs.append({"path": path, "sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)})
        captures = _captures(raw[0], lambda: None)
        individuals = _individuals(raw[1], captures, lambda: None)
        self.assertEqual((len(captures), len(individuals)), (5, 6))
        ledger = {"schema_version": "habu-stage1-ledger-v1", "source_refs": refs,
                  "complete_scopes": [], "events": []}
        for event in captures.values():
            ledger["events"].append({key: event[key] for key in (
                "event_id", "operational_night", "datetime", "utm_x_m", "utm_y_m", "individual_ids")})
            ledger["events"][-1]["source_paths"] = paths[:]
        seal(ledger, "ledger_sha256")
        protocol = fixture()[3]
        # These are an explicit diagnostic request, never a historical issuance
        # or an assertion about actual search geography. Scope remains unknown.
        protocol.update(operational_night="2026-09-28", cutoff_time="2026-09-27T18:00:00+09:00",
                        horizon_start="2026-09-28T07:00:00+09:00", horizon_end="2026-09-29T07:00:00+09:00",
                        frozen_at=None, scope_sha256=digest({"scope": "NOT_ESTABLISHED"}),
                        universe_sha256=None, targets_sha256=None)
        result = evaluate((None, None, ledger, protocol))
        self.assertEqual(result["status"], "NEED_MORE_DATA")
        self.assertEqual(result["metrics"], {})
        self.assertIn("COMPLETE_LEDGER_REQUIRED", result["blockers"])
        self.assertIn("TARGET_SET_REQUIRED", result["blockers"])
        self.assertIs(result["official_100m_10min_kpi_computed"], False)
        self.assertIs(result["production_authorized"], False)


class TimeTargetResourceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(t2)

    def test_actual_row_caps_are_before_owned_copy(self):
        for index, key, maximum in ((0, "units", 120000), (1, "targets", 100),
                                    (2, "events", 20000), (2, "source_refs", 20000)):
            values = list(fixture())
            values[index][key] = [None] * (maximum + 1)
            with patch.object(t2, "_owned", side_effect=AssertionError("must block before copy")):
                with self.assertRaisesRegex(t2.TimeTargetCapacityBlocked, "CAPACITY_BLOCKED"):
                    evaluate(values)

    def test_individual_cap_before_copy(self):
        values = fixture()
        values[2]["events"][0]["individual_ids"] = ["x"] * 100001
        with patch.object(t2, "_owned", side_effect=AssertionError("must block before copy")):
            with self.assertRaises(t2.TimeTargetCapacityBlocked):
                evaluate(values)

    def test_full_universe_index_uses_one_key_per_unit_plus_event(self):
        u, t, l, p = fixture()
        # A substantial full, unobserved universe; preserve the original three
        # real fixture units rather than sampling to selected/observed cells.
        u["scope"]["bbox_utm"] = [299000, 2999000, 330000, 3030000]
        u["scope_sha256"] = p["scope_sha256"] = digest(u["scope"])
        l["complete_scopes"][0]["scope_sha256"] = p["scope_sha256"]
        u["units"].extend({"row_id": f"unobserved-{index}", "window_start_jst": stamp("21:00:00"),
                           "utm_x_m": 310050 + index % 100 * 100,
                           "utm_y_m": 3000050 + index // 100 * 100} for index in range(8000))
        original = t2._key
        calls = [0]
        def key(*args):
            calls[0] += 1
            return original(*args)
        with patch.object(t2, "_key", key):
            result = evaluate(rebound(u, t, l, p))
        self.assertEqual(calls[0], len(u["units"]) + len(l["events"]))
        self.assertEqual(result["metrics"]["event_numerator"], 2)

    def test_edge_candidate_capacity_rejects_before_partial_matching(self):
        with patch.object(t2, "MAX_EDGES", 3), patch.object(t2, "ordered_event_owners", side_effect=AssertionError("no partial matching")):
            with self.assertRaisesRegex(t2.TimeTargetCapacityBlocked, "edge candidates"):
                evaluate(fixture())

    def test_combined_byte_depth_node_and_string_caps(self):
        values = fixture()
        combined = json.dumps(list(values), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        with patch.object(t2, "MAX_JSON_BYTES", len(combined) - 1):
            with self.assertRaises(t2.TimeTargetCapacityBlocked):
                evaluate(values)
        with patch.object(t2, "MAX_JSON_NODES", 12):
            with self.assertRaises(t2.TimeTargetCapacityBlocked):
                evaluate(values)
        for value in ("x" * 1025, [[[[[[[[[[[[[None]]]]]]]]]]]]]):
            with self.assertRaises(t2.TimeTargetCapacityBlocked):
                evaluate((value, None, None, values[3]))

    def test_nonfinite_recursive_and_non_json_are_rejected(self):
        recursive = []
        recursive.append(recursive)
        for value in (recursive, float("nan"), float("inf"), {"x": object()}, {1: "key"}, {"x" * 129: None}):
            with self.assertRaises(ValueError):
                evaluate((value, None, None, fixture()[3]))

    def test_budget_and_callback_types(self):
        for value in (True, 0, -1, 31, 10 ** 400, float("inf"), float("nan"), "30"):
            with self.assertRaises(ValueError):
                evaluate(fixture(), budget_seconds=value)
        with self.assertRaises(ValueError):
            evaluate(fixture(), check=1)

    def test_caller_exception_identity_is_not_reclassified(self):
        failure = RuntimeError("actual caller failure")
        def check():
            raise failure
        with self.assertRaises(RuntimeError) as raised:
            evaluate(fixture(), check=check)
        self.assertIs(raised.exception, failure)

    def test_one_deadline_expires_without_output(self):
        with patch.object(t2.time, "monotonic", side_effect=[0, 31]):
            with self.assertRaisesRegex(TimeoutError, "RUNTIME_BLOCKED"):
                evaluate(fixture())

    def test_expiry_inside_actual_matching_and_after_final_seal(self):
        real_matcher = t2.ordered_event_owners
        active = False
        def matcher(edges, *, check):
            nonlocal active
            active = True
            return real_matcher(edges, check=check)
        def expiry():
            if active:
                raise TimeoutError("caller matching expiry")
        with patch.object(t2, "ordered_event_owners", matcher):
            with self.assertRaises(TimeoutError):
                evaluate(fixture(), check=expiry)
        real_digest = t2._digest
        clock = [0]
        def final_digest(value, tick):
            result = real_digest(value, tick)
            if type(value) is dict and value.get("schema_version") == t2.VERSION:
                clock[0] = 31
            return result
        with patch.object(t2, "_digest", final_digest), patch.object(t2.time, "monotonic", lambda: clock[0]):
            for values in (fixture(), (None, None, None, fixture()[3])):
                clock[0] = 0
                with self.assertRaisesRegex(TimeoutError, "RUNTIME_BLOCKED"):
                    evaluate(values)

    def test_owned_inputs_detach_before_validation(self):
        values = fixture()
        baseline = evaluate(copy.deepcopy(values))
        original = t2._protocol
        def mutate_input(value, expected, tick):
            values[0]["units"].clear()
            values[2]["events"].clear()
            return original(value, expected, tick)
        with patch.object(t2, "_protocol", mutate_input):
            current = evaluate(values)
        self.assertEqual(current, baseline)


FIXTURE_SOURCE_SHA = "4f3204fd704b6cfd7df1f199d29dbea55057eb546cd2b9c5aef1f4d5221a22cc"


def original_source():
    path = Path(__file__).with_name("fixtures") / "pdca_pipeline_be045_original.py.txt"
    raw = path.read_text(encoding="utf-8").encode("utf-8")
    if len(raw) != 32918 or hashlib.sha256(raw).hexdigest() != FIXTURE_SOURCE_SHA:
        raise AssertionError("Immutable original scorer source fixture changed")
    return raw


def original_module():
    name = "_pdca_pipeline_be045_original"
    module = types.ModuleType(name)
    module.__file__ = str(Path(__file__).with_name("fixtures") / "pdca_pipeline_be045_original.py.txt")
    sys.modules[name] = module
    exec(compile(original_source(), module.__file__, "exec"), module.__dict__)
    return module


@functools.lru_cache(maxsize=1)
def recursive_program():
    tree = ast.parse(original_source())
    scorer = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "score_prediction")
    index = next(i for i, node in enumerate(scorer.body) if isinstance(node, ast.FunctionDef) and node.name == "augment")
    statements = ast.Module(body=scorer.body[index - 1:index + 2], type_ignores=[])
    return compile(statements, "checksum-bound-original-owners", "exec")


def recursive_owners(edges):
    environment = {"edges": edges, "targets": range(len(edges))}
    exec(recursive_program(), environment)
    return environment["owners"]


class OrderedMatcherCompatibilityTests(unittest.TestCase):
    def test_all_small_ordered_graphs_exact_original_owners(self):
        self.assertIsNotNone(ordered_event_owners)
        orders = [list(row) for length in range(4) for row in itertools.permutations(range(3), length)]
        for rows in itertools.product(orders, repeat=3):
            edges = list(rows)
            self.assertEqual(ordered_event_owners(edges), recursive_owners(edges))

    def test_seeded_graphs_preserve_owners_and_insertion_order(self):
        rng = random.Random(80427)
        for _ in range(200):
            size = rng.randrange(1, 9)
            edges = [rng.sample(range(size), rng.randrange(size + 1)) for _ in range(size)]
            original = recursive_owners(edges)
            self.assertEqual(list(ordered_event_owners(edges).items()), list(original.items()))

    def test_deep_augmenting_chain_is_iterative(self):
        length = 1800
        edges = [[index, index + 1] for index in range(length)] + [[0]]
        owners = ordered_event_owners(edges)
        self.assertEqual(len(owners), length + 1)
        self.assertEqual(owners[0], length)
        self.assertEqual(owners[length], length - 1)

    def test_matcher_propagates_same_callback_exception(self):
        failure = TimeoutError("parent matching budget")
        calls = [0]
        def check():
            calls[0] += 1
            if calls[0] == 6:
                raise failure
        with self.assertRaises(TimeoutError) as raised:
            ordered_event_owners([[0, 1], [0]], check=check)
        self.assertIs(raised.exception, failure)

    def test_checksum_original_whole_scorer_same_runtime(self):
        import pdca_pipeline as current
        old = original_module()
        rng = random.Random(93103)
        total_targets = total_matched = 0
        for trial in range(80):
            prediction = {"cutoff_time": stamp("20:00:00"), "prediction_version": "synthetic",
                          "expected_capture_count": 2.5, "expected_capture_range": [1, 3], "targets": []}
            captures = []
            for index in range(rng.randrange(6)):
                instant = datetime.fromisoformat(stamp("19:50:00")) + timedelta(minutes=rng.randrange(90))
                prediction["targets"].append({"target_id": str(index), "predicted_time_jst": instant.isoformat(),
                    "latitude": 28.15 + rng.randrange(4) * .0003, "longitude": 129.30})
            for index in range(rng.randrange(6)):
                instant = datetime.fromisoformat(stamp("19:50:00")) + timedelta(minutes=rng.randrange(90))
                captures.append({"event_id": str(index), "night_date": "2026-09-30", "datetime_jst": instant,
                                 "latitude": 28.15 + rng.randrange(4) * .0003, "longitude": 129.30})
            exposure = [{"cell_x": 100, "cell_y": 200, "window_start_jst": stamp("21:00:00"),
                         "observation": "observed_negative", "label": 0}]
            first = old.score_prediction(prediction, captures, "2026-09-30", exposure)
            second = current.score_prediction(prediction, captures, "2026-09-30", exposure)
            self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True), trial)
            total_targets += second["target_count"]
            total_matched += second["matched_captures"]
        self.assertGreater(total_targets, 0, "whole-output corpus must exercise real target parsing")
        self.assertGreater(total_matched, 0, "whole-output corpus must exercise actual matching")


if __name__ == "__main__":
    unittest.main()
