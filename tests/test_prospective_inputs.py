"""Regression tests for read-only future input binding; NOT official prediction tests."""
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from master_contracts import canonical_bytes, digest, file_hash
from prospective_inputs import load_prospective_inputs
import prospective_inputs as pi

NIGHT = "2026-10-14"
CUTOFF = NIGHT + "T18:00:00+09:00"
NOW = datetime.fromisoformat(NIGHT + "T18:30:00+09:00")
READY = NIGHT + "T17:00:00+09:00"
KNOWN_OUTCOMES = (
    "label", "observed", "label_available_at", "outcome", "actual_capture",
    "capture_event_ids", "capture_count", "gpx_trace", "negative_observed",
)


def write(root, path, value):
    dest = root / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical_bytes(value) + b"\n")
    return {"path": path, "sha256": file_hash(dest), "available_at": READY}


def fixtures(root):
    universe = {
        "schema_version": "1.0", "source_type": "EX_ANTE_FORECAST",
        "geographic_domain": {"crs": "EPSG:32652", "name": "test-domain"},
        "rows": [
            {"row_id": "a", "operational_night": NIGHT, "cutoff_time": CUTOFF,
             "window_start_jst": NIGHT + "T19:00:00+09:00",
             "utm_x_m": 400050, "utm_y_m": 3000050},
            {"row_id": "b", "operational_night": NIGHT, "cutoff_time": CUTOFF,
             "window_start_jst": NIGHT + "T19:10:00+09:00",
             "utm_x_m": 400150, "utm_y_m": 3000050},
        ],
    }
    uref = write(root, "features/forecast_universe.json", universe)
    feature = {
        "schema_version": "1.0", "operational_night": NIGHT,
        "cutoff_time": CUTOFF, "available_at": READY,
        "feature_name": "rain_3h_mm", "use_role": "forecast_predictor",
        "values": {"a": 0.5, "b": 1.0},
    }
    fref = write(root, "features/rain_forecast.json", feature)
    snap = {
        "schema_version": "2.0", "operational_night": NIGHT,
        "cutoff_time": CUTOFF, "universe": uref, "features": [fref],
        "feature_schema_sha256": digest(["rain_3h_mm"]),
    }
    sref = write(root, "features/forecast_snapshot.json", snap)
    return universe, feature, snap, uref, fref, sref


def run(root, sref, **kwargs):
    return load_prospective_inputs(
        root, sref["path"], sref["sha256"], NIGHT, NOW, **kwargs
    )


class ProspectiveInputsTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        (self.universe, self.feature, self.snap,
         self.uref, self.fref, self.sref) = fixtures(self.root)

    def publish(self, *, universe=None, feature=None, snap=None):
        if universe is not None:
            self.uref = write(self.root, self.uref["path"], universe)
            self.snap["universe"] = self.uref
        if feature is not None:
            self.fref = write(self.root, self.fref["path"], feature)
            self.snap["features"] = [self.fref]
        if snap is not None:
            self.snap = snap
        self.sref = write(self.root, self.sref["path"], self.snap)

    def test_full_universe_join_and_non_authority(self):
        actual = run(self.root, self.sref, model_feature_names=("rain_3h_mm",))
        self.assertEqual([x["row_id"] for x in actual["rows"]], ["a", "b"])
        self.assertEqual([x["features"]["rain_3h_mm"] for x in actual["rows"]], [0.5, 1.0])
        self.assertEqual(actual["rows"][0]["feature_source_refs"]["rain_3h_mm"], [self.fref["path"]])
        self.assertEqual(set(actual["consumed_sha256"]), {self.uref["path"], self.fref["path"], self.sref["path"]})
        self.assertFalse(actual["official_issuance_authorized"])
        self.assertNotIn("label", actual["rows"][0])

    def test_empty_features_only_with_explicit_empty_model_schema(self):
        self.snap["features"] = []
        self.snap["feature_schema_sha256"] = digest([])
        self.publish()
        actual = run(self.root, self.sref, model_feature_names=())
        self.assertEqual(actual["rows"][0]["features"], {})
        with self.assertRaisesRegex(ValueError, "registered model"):
            run(self.root, self.sref, model_feature_names=("rain_3h_mm",))

    def test_missing_feature_cell_never_defaults_to_zero(self):
        self.feature["values"].pop("b")
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "entire ex-ante universe"):
            run(self.root, self.sref)

    def test_extra_feature_cell_never_expands_universe(self):
        self.feature["values"]["observed_capture_only"] = 8
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "entire ex-ante universe"):
            run(self.root, self.sref)

    def test_future_feature_availability_is_rejected(self):
        self.fref["available_at"] = NIGHT + "T18:10:00+09:00"
        self.snap["features"] = [self.fref]
        self.publish()
        with self.assertRaisesRegex(ValueError, "not available before cutoff"):
            run(self.root, self.sref)

    def test_internal_feature_availability_cannot_exceed_receipt(self):
        self.feature["available_at"] = NIGHT + "T17:30:00+09:00"
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "Contradictory feature availability"):
            run(self.root, self.sref)

    def test_label_and_gpxtail_are_forbidden_forecast_inputs(self):
        for field, value in [("observed", True), ("label", 0),
                             ("capture_count", 0), ("gpx_trace", [])]:
            with self.subTest(field=field):
                changed = json.loads(json.dumps(self.universe))
                changed["rows"][0][field] = value
                self.publish(universe=changed)
                with self.assertRaisesRegex(ValueError, "Post-outcome"):
                    run(self.root, self.sref)

    def test_hash_mutation_rejected_without_fallback(self):
        target = self.root / self.fref["path"]
        target.write_text('{"schema_version":"1.0","values":{}}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            run(self.root, self.sref)

    def test_universe_row_identifiers_are_unique(self):
        changed = json.loads(json.dumps(self.universe))
        changed["rows"][1]["row_id"] = "a"
        self.publish(universe=changed)
        with self.assertRaisesRegex(ValueError, "duplicate universe"):
            run(self.root, self.sref)

    def test_distinct_ids_must_not_duplicate_the_same_spacetime_unit(self):
        changed = json.loads(json.dumps(self.universe))
        changed["rows"][1]["utm_x_m"] = 400060
        changed["rows"][1]["window_start_jst"] = NIGHT + "T19:00:00+09:00"
        self.publish(universe=changed)
        with self.assertRaisesRegex(ValueError, "Duplicate 100m x 10min"):
            run(self.root, self.sref)

    def test_not_an_ex_ante_universe_is_blocked(self):
        changed = dict(self.universe, source_type="EX_POST_GPX")
        self.publish(universe=changed)
        with self.assertRaisesRegex(ValueError, "ex-ante ForecastUniverse"):
            run(self.root, self.sref)

    def test_out_of_window_and_future_only_targets(self):
        changed = json.loads(json.dumps(self.universe))
        changed["rows"][0]["window_start_jst"] = NIGHT + "T18:20:00+09:00"
        self.publish(universe=changed)
        with self.assertRaisesRegex(ValueError, "expired"):
            run(self.root, self.sref)

    def test_cutoff_future_and_operational_night_boundary(self):
        changed = dict(self.snap, cutoff_time=NIGHT + "T19:00:00+09:00")
        self.publish(snap=changed)
        with self.assertRaisesRegex(ValueError, "cutoff is in the future"):
            run(self.root, self.sref)
        changed = dict(self.snap, cutoff_time="2026-10-15T00:00:00+09:00")
        self.publish(snap=changed)
        with self.assertRaisesRegex(ValueError, "cutoff is in the future"):
            run(self.root, self.sref)

    def test_feature_schema_binding(self):
        self.snap["feature_schema_sha256"] = digest(["incorrect"])
        self.publish()
        with self.assertRaisesRegex(ValueError, "Feature schema hash mismatch"):
            run(self.root, self.sref)

    def test_path_escape_and_unbound_snapshot_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported prospective input path"):
            load_prospective_inputs(self.root, "../secrets.json", self.sref["sha256"], NIGHT, NOW)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            load_prospective_inputs(self.root, self.sref["path"], "0" * 64, NIGHT, NOW)

    def test_raw_observation_path_cannot_be_masqueraded_as_forecast(self):
        self.snap["universe"]["path"] = "data/raw/gpx/observed.gpx"
        self.publish()
        with self.assertRaisesRegex(ValueError, "Unsupported prospective input path"):
            run(self.root, self.sref)

    def test_no_unreviewed_feature_names_enter_registered_model(self):
        with self.assertRaisesRegex(ValueError, "registered model"):
            run(self.root, self.sref, model_feature_names=("wind_shielding",))

    def test_universe_no_unaligned_timestamps(self):
        changed = json.loads(json.dumps(self.universe))
        changed["rows"][0]["window_start_jst"] = NIGHT + "T19:05:00+09:00"
        self.publish(universe=changed)
        with self.assertRaisesRegex(ValueError, "misaligned"):
            run(self.root, self.sref)

    def test_timezone_aliases_cannot_duplicate_the_same_spacetime_unit(self):
        self.universe["rows"][1]["utm_x_m"] = 400060
        self.universe["rows"][1]["window_start_jst"] = NIGHT + "T10:00:00Z"
        self.publish(universe=self.universe)
        with self.assertRaisesRegex(ValueError, "Duplicate 100m x 10min"):
            run(self.root, self.sref)

    def test_known_outcome_names_cannot_be_declared_as_predictors(self):
        for name in KNOWN_OUTCOMES:
            with self.subTest(name=name):
                self.feature["feature_name"] = name
                self.snap["feature_schema_sha256"] = digest([name])
                self.publish(feature=self.feature)
                with self.assertRaisesRegex(ValueError, "Post-outcome"):
                    run(self.root, self.sref, model_feature_names=(name,))

    def test_owner_capture_outcomes_and_case_aliases_are_not_predictors(self):
        for name in ("owner_capture_count", "Label", "ACTUAL_CAPTURE"):
            with self.subTest(name=name):
                self.feature["feature_name"] = name
                self.snap["feature_schema_sha256"] = digest([name])
                self.publish(feature=self.feature)
                with self.assertRaisesRegex(ValueError, "Post-outcome"):
                    run(self.root, self.sref, model_feature_names=(name,))

    def test_explicit_label_role_cannot_be_disguised_by_forecast_use_role(self):
        self.feature["source_role"] = "label"
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "source role|Post-outcome"):
            run(self.root, self.sref)

    def test_explicit_materialization_at_cutoff_cannot_use_earlier_available_at(self):
        self.feature["materialized_at"] = CUTOFF
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "readiness"):
            run(self.root, self.sref)

    def test_explicit_feature_validity_must_include_each_forecast_window(self):
        self.feature.update(valid_from="2026-10-15T19:00:00+09:00",
                            valid_until="2026-10-15T20:00:00+09:00")
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "valid.time"):
            run(self.root, self.sref)

    def test_later_reference_cannot_hide_contradictory_internal_feature_readiness(self):
        self.feature["materialized_at"] = NIGHT + "T17:20:00+09:00"
        self.publish(feature=self.feature)
        self.fref["available_at"] = NIGHT + "T17:30:00+09:00"
        self.publish()
        with self.assertRaisesRegex(ValueError, "readiness"):
            run(self.root, self.sref)

    def test_any_declared_readiness_component_at_cutoff_blocks_the_join(self):
        for field in ("source_received_at", "derived_at", "materialized_at", "audited_at"):
            with self.subTest(field=field):
                feature = dict(self.feature, readiness={
                    "source_received_at": READY, "derived_at": READY,
                    "materialized_at": READY, "audited_at": READY})
                feature["readiness"][field] = CUTOFF
                self.publish(feature=feature)
                with self.assertRaisesRegex(ValueError, "readiness"):
                    run(self.root, self.sref)

    def test_reference_and_universe_cannot_declare_late_readiness(self):
        self.snap["universe"]["audited_at"] = CUTOFF
        self.publish()
        with self.assertRaisesRegex(ValueError, "readiness"):
            run(self.root, self.sref)
        self.snap["universe"].pop("audited_at")
        self.universe["derived_at"] = CUTOFF
        self.publish(universe=self.universe)
        with self.assertRaisesRegex(ValueError, "readiness"):
            run(self.root, self.sref)

    def test_declared_usable_at_cannot_backdate_a_later_required_readiness(self):
        self.feature.update(derived_at=READY, usable_at=NIGHT + "T16:59:59+09:00")
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "usable_at.*readiness"):
            run(self.root, self.sref)

    def test_incomplete_or_timezone_naive_validity_is_rejected(self):
        self.feature["valid_from"] = NIGHT + "T19:00:00+09:00"
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "valid.time"):
            run(self.root, self.sref)
        self.feature["valid_until"] = NIGHT + "T20:00:00"
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "timezone"):
            run(self.root, self.sref)

    def test_validity_must_cover_the_end_of_the_last_full_ten_minute_window(self):
        self.feature.update(valid_from=NIGHT + "T10:00:00Z",
                            valid_until=NIGHT + "T19:19:59+09:00")
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "valid.time"):
            run(self.root, self.sref)
        self.feature["valid_until"] = NIGHT + "T10:20:00Z"
        self.feature["readiness"] = {
            "source_received_at": READY, "derived_at": READY,
            "materialized_at": READY, "audited_at": READY}
        self.publish(feature=self.feature)
        actual = run(self.root, self.sref)
        self.assertEqual([row["row_id"] for row in actual["rows"]], ["a", "b"])
        self.assertEqual(actual["qualification"], "PREPRODUCTION_INPUT_INTEGRITY_ONLY")
        self.assertFalse(actual["official_issuance_authorized"])

    def test_explicit_reference_roles_and_case_alias_metadata_are_checked(self):
        self.snap["features"][0]["role"] = "label"
        self.publish()
        with self.assertRaisesRegex(ValueError, "source role"):
            run(self.root, self.sref)
        self.snap["features"][0].pop("role")
        self.feature["metadata"] = {"LABEL": 0}
        self.publish(feature=self.feature)
        with self.assertRaisesRegex(ValueError, "Post-outcome"):
            run(self.root, self.sref)

    def test_validity_declared_only_on_reference_still_limits_forecast_scope(self):
        for reference in (self.snap["universe"], self.snap["features"][0]):
            with self.subTest(path=reference["path"]):
                reference.update(valid_from="2026-10-15T19:00:00+09:00",
                                 valid_until="2026-10-15T20:00:00+09:00")
                self.publish()
                with self.assertRaisesRegex(ValueError, "valid.time"):
                    run(self.root, self.sref)
                reference.pop("valid_from")
                reference.pop("valid_until")

    def test_outcome_fields_are_rejected_at_feature_root_and_nested_metadata(self):
        for name in KNOWN_OUTCOMES:
            for nested in (False, True):
                with self.subTest(name=name, nested=nested):
                    feature = json.loads(json.dumps(self.feature))
                    if nested:
                        feature["metadata"] = [{"evidence": {name: 0}}]
                    else:
                        feature[name] = 0
                    self.publish(feature=feature)
                    with self.assertRaisesRegex(ValueError, "Post-outcome"):
                        run(self.root, self.sref)

    def test_nested_universe_outcome_fields_are_rejected(self):
        self.universe["rows"][0]["metadata"] = {"evidence": [{"label": 0}]}
        self.publish(universe=self.universe)
        with self.assertRaisesRegex(ValueError, "Post-outcome"):
            run(self.root, self.sref)

    def test_outcome_metadata_in_snapshot_or_universe_is_rejected(self):
        self.snap["metadata"] = {"outcome": 1}
        self.publish()
        with self.assertRaisesRegex(ValueError, "Post-outcome"):
            run(self.root, self.sref)
        del self.snap["metadata"]
        self.universe["metadata"] = {"capture_event_ids": []}
        self.publish(universe=self.universe)
        with self.assertRaisesRegex(ValueError, "Post-outcome"):
            run(self.root, self.sref)

    def test_historical_predictor_names_and_outcome_like_row_ids_remain_valid(self):
        # Identifiers in values are row IDs, not schema field names. A historical
        # predictor still requires the existing ex-ante role/availability checks.
        self.universe["rows"][0]["row_id"] = "label"
        self.feature["feature_name"] = "prior_capture_count_7d"
        self.feature["values"] = {"label": 2, "b": 1}
        self.snap["feature_schema_sha256"] = digest(["prior_capture_count_7d"])
        self.publish(universe=self.universe, feature=self.feature)
        actual = run(self.root, self.sref, model_feature_names=("prior_capture_count_7d",))
        self.assertEqual(actual["rows"][0]["features"], {"prior_capture_count_7d": 2.0})
        self.assertFalse(actual["official_issuance_authorized"])

    def grow_feature_on_open(self, grown, *, on_read=1):
        target = self.root / self.fref["path"]
        original_open = Path.open
        reads = 0

        def racing_open(path, mode="r", *args, **kwargs):
            nonlocal reads
            if path == target and mode == "rb":
                reads += 1
                if reads == on_read:
                    with original_open(target, "wb") as dest:
                        dest.write(grown)
            return original_open(path, mode, *args, **kwargs)

        return patch.object(Path, "open", racing_open)

    def test_source_growth_after_stat_cannot_exceed_actual_byte_limit(self):
        grown = canonical_bytes(dict(self.feature, padding="x" * 2048)) + b"\n"
        self.snap["features"][0]["sha256"] = hashlib.sha256(grown).hexdigest()
        self.publish()
        with patch.object(pi, "MAX_SOURCE_BYTES", 1024), self.grow_feature_on_open(grown):
            with self.assertRaisesRegex(ValueError, "oversized|budget"):
                run(self.root, self.sref)

    def test_source_growth_consumes_actual_total_byte_budget(self):
        grown = canonical_bytes(dict(self.feature, padding="x" * 2048)) + b"\n"
        self.snap["features"][0]["sha256"] = hashlib.sha256(grown).hexdigest()
        self.publish()
        total = sum((self.root / ref["path"]).stat().st_size
                    for ref in (self.sref, self.uref, self.fref))
        with patch.object(pi, "MAX_SOURCE_BYTES", 4096), \
                patch.object(pi, "MAX_TOTAL_BYTES", total + 512), \
                self.grow_feature_on_open(grown):
            with self.assertRaisesRegex(ValueError, "budget"):
                run(self.root, self.sref)

    def test_final_rescan_also_limits_actual_read_bytes(self):
        grown = canonical_bytes(dict(self.feature, padding="x" * 2048)) + b"\n"
        with patch.object(pi, "MAX_SOURCE_BYTES", 1024), \
                self.grow_feature_on_open(grown, on_read=2):
            with self.assertRaisesRegex(ValueError, "oversized|budget"):
                run(self.root, self.sref)

    def test_actual_byte_budget_boundary_accepts_unchanged_inputs(self):
        sizes = [(self.root / ref["path"]).stat().st_size
                 for ref in (self.sref, self.uref, self.fref)]
        with patch.object(pi, "MAX_SOURCE_BYTES", max(sizes)), \
                patch.object(pi, "MAX_TOTAL_BYTES", sum(sizes)):
            self.assertEqual(len(run(self.root, self.sref)["rows"]), 2)

    def test_final_recheck_detects_changed_feature_bytes(self):
        changed = canonical_bytes(dict(self.feature, values={"a": 9, "b": 9})) + b"\n"
        with self.grow_feature_on_open(changed, on_read=2):
            with self.assertRaisesRegex(ValueError, "changed during validation"):
                run(self.root, self.sref)

    def test_sequential_recheck_has_no_atomic_filesystem_state_guarantee(self):
        # A writer can change an already rechecked file during a later read.
        # Output still derives from the original hash-checked bytes; production
        # atomic publication needs immutable storage or coordinated locking.
        snapshot_path = self.root / self.sref["path"]
        universe_path = self.root / self.uref["path"]
        original_open = Path.open
        universe_reads = 0

        def racing_open(path, mode="r", *args, **kwargs):
            nonlocal universe_reads
            if path == universe_path and mode == "rb":
                universe_reads += 1
                if universe_reads == 2:
                    with original_open(snapshot_path, "wb") as dest:
                        dest.write(b'{"changed_after_check":true}\n')
            return original_open(path, mode, *args, **kwargs)

        with patch.object(Path, "open", racing_open):
            actual = run(self.root, self.sref)
        self.assertNotEqual(file_hash(snapshot_path), self.sref["sha256"])
        self.assertEqual(actual["consumed_sha256"][self.sref["path"]], self.sref["sha256"])
        self.assertEqual(actual["rows"][0]["features"]["rain_3h_mm"], 0.5)
        self.assertFalse(actual["official_issuance_authorized"])

    def test_join_cell_budget_rejects_before_reading_feature_sources(self):
        # Two rows times one feature exceed this reduced test budget. Invalid
        # source bytes would otherwise fail later at the hash check.
        (self.root / self.fref["path"]).write_bytes(b"changed")
        with patch.object(pi, "MAX_JOIN_CELLS", 1):
            with self.assertRaisesRegex(ValueError, "join cell budget"):
                run(self.root, self.sref)

    def test_join_cell_budget_boundary_is_accepted(self):
        with patch.object(pi, "MAX_JOIN_CELLS", 2):
            self.assertEqual(len(run(self.root, self.sref)["rows"]), 2)

    def test_feature_count_limit_rejects_before_opening_universe(self):
        self.snap["features"] *= 33
        self.publish()
        (self.root / self.uref["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "feature count limit"):
            run(self.root, self.sref)

    def test_default_elapsed_budget_rejects_expiry_during_source_read(self):
        original_open = Path.open
        clock = [0.0]

        def slow_open(path, mode="r", *args, **kwargs):
            if mode == "rb":
                clock[0] = 31.0
            return original_open(path, mode, *args, **kwargs)

        with patch.object(pi, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(Path, "open", slow_open):
            with self.assertRaisesRegex(TimeoutError, "elapsed budget"):
                run(self.root, self.sref)

    def test_default_elapsed_budget_is_checked_during_metadata_validation(self):
        original_time = pi._time
        clock = [0.0]

        def slow_time(value):
            if value == CUTOFF:
                clock[0] = 31.0
            return original_time(value)

        with patch.object(pi, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(pi, "_time", side_effect=slow_time):
            with self.assertRaisesRegex(TimeoutError, "elapsed budget"):
                run(self.root, self.sref)

    def test_elapsed_budget_is_checked_for_each_join_cell(self):
        # Real numeric validation continues; the clock advances while the first
        # feature cell is checked, so the remaining join cannot complete.
        finite = pi.math.isfinite
        clock = [0.0]

        def slow_finite(value):
            if value == 0.5:
                clock[0] = 31.0
            return finite(value)

        with patch.object(pi, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(pi.math, "isfinite", side_effect=slow_finite):
            with self.assertRaisesRegex(TimeoutError, "elapsed budget"):
                run(self.root, self.sref)

    def test_elapsed_budget_is_checked_during_final_rescan(self):
        target = self.root / self.fref["path"]
        original_open = Path.open
        clock = [0.0]
        reads = 0

        def slow_open(path, mode="r", *args, **kwargs):
            nonlocal reads
            if path == target and mode == "rb":
                reads += 1
                if reads == 2:
                    clock[0] = 31.0
            return original_open(path, mode, *args, **kwargs)

        with patch.object(pi, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(Path, "open", slow_open):
            with self.assertRaisesRegex(TimeoutError, "elapsed budget"):
                run(self.root, self.sref)

    def test_elapsed_budget_option_rejects_invalid_values(self):
        for value in (True, False, None, "30", 0, -1, 301, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Invalid prospective elapsed budget"):
                    run(self.root, self.sref, budget_seconds=value)

    def test_elapsed_budget_option_accepts_parent_ceiling(self):
        with patch.object(pi, "monotonic", return_value=0.0):
            actual = run(self.root, self.sref, budget_seconds=300)
        self.assertFalse(actual["official_issuance_authorized"])

    def test_elapsed_budget_option_honors_smaller_caller_allowance(self):
        with patch.object(pi, "monotonic", side_effect=(0.0, 0.25)):
            with self.assertRaisesRegex(TimeoutError, "elapsed budget"):
                run(self.root, self.sref, budget_seconds=0.25)

    def test_elapsed_budget_is_checked_for_each_universe_row(self):
        coordinates = pi._coordinates
        clock = [0.0]

        def slow_coordinates(unit):
            clock[0] = 31.0
            return coordinates(unit)

        with patch.object(pi, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(pi, "_coordinates", side_effect=slow_coordinates):
            with self.assertRaisesRegex(TimeoutError, "elapsed budget"):
                run(self.root, self.sref)


if __name__ == "__main__":
    unittest.main()
