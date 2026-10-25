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
from unittest.mock import patch
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

    def test_pure_builder_import_does_not_require_posix_file_lock(self):
        import builtins
        original = builtins.__import__
        def reject_posix_lock(name, *args, **kwargs):
            if name == "fcntl":
                raise AssertionError("Pure builder import attempted a POSIX lock")
            return original(name, *args, **kwargs)
        fresh_spec = importlib.util.spec_from_file_location("isolated_osm_builder", SCRIPT)
        fresh = importlib.util.module_from_spec(fresh_spec)
        with patch("builtins.__import__", side_effect=reject_posix_lock):
            fresh_spec.loader.exec_module(fresh)
            self.assertEqual(fresh.EXPECTED_CELLS, 16990)

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

    def materialize_fixture(self, repo, output):
        # Keep parsing and all filesystem operations real; replace only archive I/O.
        parse = module.parse_road_cells
        with patch.object(module, "load_verified_road_csv", return_value=csv_source(self.rows)), \
             patch.object(module, "parse_road_cells", side_effect=lambda raw: parse(raw, expected_cells=2)):
            return module.materialize(repo, output, NIGHT, CUTOFF, START, 1)

    def test_materializer_rejects_completion_at_cutoff_without_leaving_a_shard(self):
        # Losing the final clock check would publish data first saved at/after cutoff.
        for delayed_operation in ("canonical", "fsync", "rename"):
            with self.subTest(delayed_operation=delayed_operation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                repo = root / "canonical"
                repo.mkdir()
                output = root / "output"
                clock = [datetime.fromisoformat(READY)]

                class Clock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return clock[0].astimezone(tz or timezone.utc)

                owner = module if delayed_operation == "canonical" else module.os
                real_operation = getattr(owner, delayed_operation)

                def completes_at_cutoff(*args, **kwargs):
                    result = real_operation(*args, **kwargs)
                    clock[0] = datetime.fromisoformat(CUTOFF)
                    return result

                with patch.object(module, "datetime", Clock), \
                     patch.object(owner, delayed_operation, side_effect=completes_at_cutoff):
                    with self.assertRaisesRegex(ValueError, "cutoff"):
                        self.materialize_fixture(repo, output)
                self.assertEqual(list(output.rglob("*.json")), [])
                self.assertEqual(list(output.rglob(".forecast-pending-*")), [])
                self.assertFalse(any(p.name == "20261014T100000000000Z" for p in output.rglob("*")))

    def test_materializer_rejects_snapshot_publication_at_cutoff(self):
        # Source readiness alone cannot authorize a snapshot completed after cutoff.
        for operation in ("serialization", "fsync", "rename"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                repo = root / "canonical"
                repo.mkdir()
                output = root / "output"
                clock = [datetime.fromisoformat(READY)]
                snapshot_started = [False]
                real_canonical, real_fsync, real_rename = module.canonical, module.os.fsync, module.os.rename

                class Clock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return clock[0].astimezone(tz or timezone.utc)

                def serialize(value):
                    encoded = real_canonical(value)
                    if isinstance(value, dict) and value.get("schema_version") == "2.0":
                        snapshot_started[0] = True
                        if operation == "serialization":
                            clock[0] = datetime.fromisoformat(CUTOFF)
                    return encoded

                def sync(fd):
                    real_fsync(fd)
                    if snapshot_started[0] and operation == "fsync":
                        clock[0] = datetime.fromisoformat(CUTOFF)

                def rename(source, destination):
                    real_rename(source, destination)
                    if Path(destination).name == "snapshot.json" and operation == "rename":
                        clock[0] = datetime.fromisoformat(CUTOFF)

                with patch.object(module, "datetime", Clock), \
                     patch.object(module, "canonical", side_effect=serialize), \
                     patch.object(module.os, "fsync", side_effect=sync), \
                     patch.object(module.os, "rename", side_effect=rename):
                    with self.assertRaisesRegex(ValueError, "cutoff"):
                        self.materialize_fixture(repo, output)
                self.assertEqual(list(output.rglob("*.json")), [])
                self.assertEqual(list(output.rglob(".forecast-pending-*")), [])

    def test_materializer_records_actual_source_readiness_and_completion(self):
        # Backdating refs to build start would fail the literal source-ready assertions.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "canonical"
            repo.mkdir()
            output = root / "output"
            clock = [datetime.fromisoformat(READY)]

            class Clock(datetime):
                @classmethod
                def now(cls, tz=None):
                    return clock[0].astimezone(tz or timezone.utc)

            real_rename = module.os.rename

            def source_publication(*args, **kwargs):
                result = real_rename(*args, **kwargs)
                clock[0] = datetime.fromisoformat("2026-10-14T19:30:00+09:00")
                return result

            with patch.object(module, "datetime", Clock), \
                 patch.object(module.os, "rename", side_effect=source_publication):
                result = self.materialize_fixture(repo, output)
            snapshot = json.loads((output / result["snapshot"]).read_text())
            ready = datetime.fromisoformat("2026-10-14T19:30:00+09:00")
            for reference in [snapshot["universe"], *snapshot["features"]]:
                self.assertEqual(datetime.fromisoformat(reference["available_at"]), ready)
                self.assertLess(datetime.fromisoformat(reference["available_at"]), datetime.fromisoformat(CUTOFF))
                self.assertEqual(module.digest((output / reference["path"]).read_bytes()), reference["sha256"])
            self.assertEqual(datetime.fromisoformat(result["completed_at"]), ready)
            self.assertEqual(module.digest((output / result["snapshot"]).read_bytes()), result["snapshot_sha256"])
            self.assertEqual(result["status"], "PREPRODUCTION_INPUT_ONLY")

    def test_materializer_rejects_symlinks_before_changing_any_canonical_bytes(self):
        # Checking only output_root would write a shard through any nested directory link.
        for relative in ("features", "features/forecast_builds", "features/forecast_builds/" + NIGHT,
                         "features/forecast_builds/" + NIGHT + "/.materialization.lock"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                repo = root / "canonical"
                raw = repo / "data" / "raw"
                raw.mkdir(parents=True)
                sentinel = raw / "original.bin"
                sentinel.write_bytes(b"immutable raw bytes")
                output = root / "output"
                link = output / relative
                link.parent.mkdir(parents=True)
                link.symlink_to(sentinel if link.name == ".materialization.lock" else raw)

                class Clock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return datetime.fromisoformat(READY).astimezone(tz or timezone.utc)

                with patch.object(module, "datetime", Clock):
                    with self.assertRaisesRegex(ValueError, "[Ss]ymlink"):
                        self.materialize_fixture(repo, output)
                self.assertEqual({p.relative_to(repo).as_posix(): p.read_bytes()
                                  for p in repo.rglob("*") if p.is_file()},
                                 {"data/raw/original.bin": b"immutable raw bytes"})

    def test_materializer_rejects_output_ancestors_that_place_shards_inside_repository(self):
        # An outside output root may still contain the canonical repository below features/.
        for relative in ("features", "features/forecast_builds", "features/forecast_builds/" + NIGHT):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                repo = output / relative
                raw = repo / "data" / "raw"
                raw.mkdir(parents=True)
                (raw / "original.bin").write_bytes(b"immutable raw bytes")

                class Clock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return datetime.fromisoformat(READY).astimezone(tz or timezone.utc)

                with patch.object(module, "datetime", Clock):
                    with self.assertRaisesRegex(ValueError, "outside the canonical repository"):
                        self.materialize_fixture(repo, output)
                self.assertEqual({p.relative_to(repo).as_posix(): p.read_bytes()
                                  for p in repo.rglob("*") if p.is_file()},
                                 {"data/raw/original.bin": b"immutable raw bytes"})

    def test_materializer_rejects_symlink_output_root_and_ancestor(self):
        for relative in ("alias", "alias/nested"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                repo = root / "canonical"
                repo.mkdir()
                actual_output = root / "actual-output"
                actual_output.mkdir()
                (root / "alias").symlink_to(actual_output, target_is_directory=True)
                class Clock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return datetime.fromisoformat(READY).astimezone(tz or timezone.utc)

                with patch.object(module, "datetime", Clock):
                    with self.assertRaisesRegex(ValueError, "[Ss]ymlink"):
                        self.materialize_fixture(repo, root / relative)
                self.assertEqual(list(actual_output.iterdir()), [])

    def test_timezone_aware_inputs_only(self):
        with self.assertRaisesRegex(ValueError, "Timezone-aware"):
            self.build(ready="2026-10-14T19:00:00")

    def test_feature_schema_hash_contract_is_identical_to_validator(self):
        names = sorted(module.FEATURE_NAMES)
        self.assertEqual(module.digest(module.canonical(names)), module.digest(module.canonical(sorted(names))))


if __name__ == "__main__":
    unittest.main()

