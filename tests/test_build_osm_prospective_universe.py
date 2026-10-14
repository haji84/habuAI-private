"""Synthetic contract checks for the real-archive future-road materializer.

These fixtures cannot authorize a production forecast or validate field access.
"""
import importlib.util
import io
import json
import math
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_osm_prospective_universe.py"
spec = importlib.util.spec_from_file_location("build_osm_prospective_universe", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

NIGHT = "2026-10-14"
CUTOFF = NIGHT + "T20:00:00+09:00"
START = NIGHT + "T21:00:00+09:00"
READY = NIGHT + "T19:00:00+09:00"

FIELDS = ["cell_id", "cell_x_index", "cell_y_index", "cell_center_x", "cell_center_y",
          "normal_route", "road_length_m", "road_direction_deg", "candidate_source",
          "island_name"]


def csv_source(rows):
    import csv
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def row(x, y, *, island="奄美大島", length=10.0, direction=15.0):
    return {
        "cell_id": f"utm52n_100m_{x}_{y}", "cell_x_index": str(x),
        "cell_y_index": str(y), "cell_center_x": str(x * 100 + 50),
        "cell_center_y": str(y * 100 + 50), "normal_route": "True",
        "road_length_m": str(length), "road_direction_deg": str(direction),
        "candidate_source": "osm_auxiliary", "island_name": island,
    }


class ProspectiveRoadUniverseTests(unittest.TestCase):
    def setUp(self):
        self.rows = [row(4000, 30000), row(4001, 30000, island="加計呂麻島")]
        self.cells = module.parse_road_cells(csv_source(self.rows), expected_cells=2)

    def build(self, **kw):
        return module.build_artifacts(self.cells, NIGHT, kw.get("cutoff", CUTOFF),
                                      kw.get("start", START), kw.get("windows", 2),
                                      kw.get("ready", READY))

    def test_original_archive_hash_is_pinned(self):
        self.assertEqual(len(module.ARCHIVE_SHA256), 64)
        self.assertEqual(len(module.CELLS_SHA256), 64)
        self.assertEqual(module.EXPECTED_CELLS, 16990)

    def test_prospective_universe_has_all_cells_in_each_future_window(self):
        universe, features = self.build()
        self.assertEqual(len(universe["rows"]), 4)
        self.assertEqual(universe["source_type"], "EX_ANTE_FORECAST")
        self.assertEqual(universe["geographic_domain"]["source_class"], "osm_auxiliary")
        self.assertEqual(universe["geographic_domain"]["official_road_eligibility"], "NOT_VALIDATED")
        self.assertEqual(len(features), 3)
        self.assertEqual({x["feature_name"] for x in features}, set(module.FEATURE_NAMES))
        for feat in features:
            self.assertEqual(set(feat["values"]), {x["row_id"] for x in universe["rows"]})
            self.assertEqual(feat["cutoff_time"], CUTOFF)
        self.assertFalse({"label", "capture_count", "gpx_trace"} & set(universe["rows"][0]))

    def test_real_road_direction_is_encoded_as_undirected_axial_vector(self):
        _, feats = self.build(windows=1)
        values = {x["feature_name"]: x["values"] for x in feats}
        first = next(iter(values["road_axial_cos"]))
        self.assertAlmostEqual(values["road_axial_cos"][first], math.cos(math.radians(30)))
        self.assertAlmostEqual(values["road_axial_sin"][first], math.sin(math.radians(30)))

    def test_no_unknown_or_prohibited_route_is_silently_included(self):
        for replacement in [{"normal_route": "False"}, {"candidate_source": "official_road_gis"},
                            {"island_name": "別の島"}, {"road_direction_deg": "nan"},
                            {"road_length_m": "-1"}, {"cell_center_x": "0"}]:
            with self.subTest(replacement=replacement):
                changed = list(self.rows)
                changed[0] = dict(changed[0], **replacement)
                with self.assertRaises(ValueError):
                    module.parse_road_cells(csv_source(changed), expected_cells=2)

    def test_missing_or_duplicate_cell_rejected(self):
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            module.parse_road_cells(csv_source(self.rows[:1]), expected_cells=2)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.parse_road_cells(csv_source([self.rows[0], self.rows[0]]), expected_cells=2)

    def test_source_availability_precedes_cutoff(self):
        with self.assertRaisesRegex(ValueError, "readiness"):
            self.build(ready=NIGHT + "T20:00:00+09:00")
        with self.assertRaisesRegex(ValueError, "readiness"):
            self.build(ready=NIGHT + "T20:10:00+09:00")

    def test_future_window_cannot_be_backdated(self):
        with self.assertRaisesRegex(ValueError, "order"):
            self.build(start=NIGHT + "T19:00:00+09:00")
        with self.assertRaisesRegex(ValueError, "ten-minute"):
            self.build(start=NIGHT + "T21:05:00+09:00")

    def test_operational_boundary_and_shard_capacity(self):
        with self.assertRaisesRegex(ValueError, "boundary"):
            self.build(start="2026-10-15T06:50:00+09:00", windows=2)
        with self.assertRaisesRegex(ValueError, "shard size"):
            self.build(windows=7)

    def test_materializer_does_not_write_to_canonical_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "outside the canonical repository"):
                module.materialize(root, root / "features" / "generated",
                                   NIGHT, CUTOFF, START, 1)
            self.assertFalse((root / "features").exists())

    def test_timezone_aware_inputs_only(self):
        with self.assertRaisesRegex(ValueError, "Timezone-aware"):
            self.build(ready="2026-10-14T19:00:00")

    def test_feature_schema_hash_contract_is_identical_to_validator(self):
        names = sorted(module.FEATURE_NAMES)
        self.assertEqual(module.digest(module.canonical(names)), module.digest(module.canonical(sorted(names))))


if __name__ == "__main__":
    unittest.main()
