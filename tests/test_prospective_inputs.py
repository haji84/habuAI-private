"""Regression tests for read-only future input binding; NOT official prediction tests."""
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from master_contracts import canonical_bytes, digest, file_hash
from prospective_inputs import load_prospective_inputs

NIGHT = "2026-10-14"
CUTOFF = NIGHT + "T18:00:00+09:00"
NOW = datetime.fromisoformat(NIGHT + "T18:30:00+09:00")
READY = NIGHT + "T17:00:00+09:00"


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

    def test_no_unreviewed_feature_names_enter_registered_model(self):
        with self.assertRaisesRegex(ValueError, "registered model"):
            run(self.root, self.sref, model_feature_names=("wind_shielding",))

    def test_universe_no_unaligned_timestamps(self):
        changed = json.loads(json.dumps(self.universe))
        changed["rows"][0]["window_start_jst"] = NIGHT + "T19:05:00+09:00"
        self.publish(universe=changed)
        with self.assertRaisesRegex(ValueError, "misaligned"):
            run(self.root, self.sref)


if __name__ == "__main__":
    unittest.main()
