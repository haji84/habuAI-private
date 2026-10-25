"""Synthetic contract checks for the real-archive future-road materializer.

These fixtures cannot authorize a production forecast or validate field access.
"""
import importlib.util
import base64
import importlib
import io
import json
import math
import os
import subprocess
import tempfile
import unittest
import zipfile
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



class StrictOsmProducerTests(unittest.TestCase):
    """Synthetic archive identities are test-only; no real availability is fabricated."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo, self.output = self.root / 'repo', self.root / 'capsule'
        self.repo.mkdir()
        self.g0 = importlib.import_module('g0_forecast_contract')
        self.pi = importlib.import_module('prospective_inputs')
        raw = csv_source([row(4000, 30000), row(4001, 30000, length=20)])
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(self.g0.OSM_CSV_MEMBER, raw)
        zipped = stream.getvalue()
        encoded = base64.b64encode(zipped)
        chunk = (len(encoded) - 1) // 32
        self.parts = []
        for index in range(33):
            target = self.repo / self.g0.OSM_PARTS_PATH / f'part_{index:03d}.b64'
            target.parent.mkdir(parents=True, exist_ok=True)
            piece = encoded[index * chunk:(index + 1) * chunk] if index < 32 else encoded[32 * chunk:]
            target.write_bytes(piece)
            self.parts.append((target, piece))
        for relative in [self.g0.POLICY_PATH, 'scripts/build_osm_prospective_universe.py']:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((SCRIPT.parents[1] / relative).read_bytes())
        self.patches = [patch.multiple(self.g0, OSM_ARCHIVE_SHA256=module.digest(zipped),
                                      OSM_ARCHIVE_BYTES=len(zipped), OSM_PART_CHUNK_BYTES=chunk,
                                      OSM_CSV_SHA256=module.digest(raw), OSM_CSV_BYTES=len(raw), OSM_EXPECTED_CELLS=2),
                        patch.object(module, '_git_head', return_value='a' * 40, create=True)]
        clock = datetime.fromisoformat(READY)
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock.astimezone(tz or timezone.utc)
        self.patches.append(patch.object(module, 'datetime', Clock))
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def call(self, **kwargs):
        return module.materialize_g0(self.repo, self.output, NIGHT, CUTOFF, START,
                                     kwargs.pop('windows', 8), **kwargs)

    def test_complete_typed_capsule_validates_before_atomic_publication(self):
        original = self.g0.validate_g0_forecast
        validated = []
        def validate(root, *args, **kwargs):
            self.assertFalse(self.output.exists())
            result = original(root, *args, **kwargs)
            validated.append(result)
            return result
        with patch.object(self.g0, 'validate_g0_forecast', side_effect=validate):
            result = self.call()
        self.assertEqual(len(validated), 1)
        self.assertEqual(result['rows'], 16)
        self.assertEqual(result['windows'], 8)
        self.assertEqual(result['shards'], 8)
        self.assertEqual(result['validation_clock'], 'DECLARED_FUTURE_CUTOFF_REHEARSAL')
        self.assertFalse(result['issuance_authorized'])
        self.assertFalse(result['production_authorized'])
        self.assertEqual(result['historical_access'], 'NOT_ATTESTED')
        manifest = json.loads((self.output / result['manifest_ref']['path']).read_bytes())
        proof_node = next(n for n in manifest['source_nodes'] if n['id'] == 'osm-csv')
        proof = json.loads((self.output / proof_node['provenance_ref']['path']).read_bytes())
        self.assertEqual(proof['source_git_sha'], 'a' * 40)
        self.assertEqual(proof['started_at'], datetime.fromisoformat(READY).astimezone(timezone.utc).isoformat())
        self.assertTrue(all(p['readiness']['source_received_at'] == proof['started_at'] for p in proof['parts']))
        for target, original_bytes in self.parts:
            self.assertEqual(target.read_bytes(), original_bytes)
            self.assertEqual((self.output / target.relative_to(self.repo)).read_bytes(), original_bytes)
        checked = self.g0.load_g0_forecast_rows(self.output, result['manifest_ref'], NIGHT,
                                               datetime.fromisoformat(CUTOFF),
                                               expected_feature_definition_sha256=result['feature_definition_sha256'])
        self.assertEqual(len(checked['rows']), 16)
        self.assertEqual(checked['rows'][0]['features']['road_length_m'], 10)
        self.assertEqual(checked['rows'][-1]['features']['road_length_m'], 20)

    def test_existing_output_and_canonical_descendants_are_never_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / 'preserve'
        sentinel.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            self.call()
        self.assertEqual(sentinel.read_bytes(), b'keep')
        self.output = self.repo / 'candidate'
        with self.assertRaisesRegex(ValueError, 'outside|canonical'):
            self.call()
        self.assertFalse(self.output.exists())

    def test_missing_or_file_output_parent_rejects_before_any_source_read(self):
        for parent in (self.root / 'new-parent' / 'nested-parent', self.root / 'file-parent'):
            with self.subTest(parent=parent):
                if parent.name == 'file-parent':
                    parent.write_bytes(b'preserve existing file')
                self.output = parent / 'capsule'
                with patch.object(Path, 'open', side_effect=AssertionError('source bytes opened')), \
                     patch.object(module, '_git_head', side_effect=AssertionError('source Git read')):
                    with self.assertRaisesRegex(ValueError, 'existing.*parent|parent.*directory'):
                        self.call()
                self.assertFalse(self.output.exists())
                if parent.name == 'file-parent':
                    self.assertEqual(parent.read_bytes(), b'preserve existing file')
                else:
                    self.assertFalse((self.root / 'new-parent').exists())

    def test_strict_cli_does_not_create_missing_output_parent(self):
        self.output = self.root / 'missing-parent' / 'capsule'
        args = [str(SCRIPT), '--strict-g0', '--repo-root', str(self.repo), '--output-root', str(self.output),
                '--night', NIGHT, '--cutoff', CUTOFF, '--first-window', START, '--windows', '1']
        with patch.object(module.sys, 'argv', args), \
             patch.object(module, '_git_head', side_effect=AssertionError('source Git read')):
            with self.assertRaisesRegex(ValueError, 'existing.*parent|parent.*directory'):
                module.main()
        self.assertFalse(self.output.parent.exists())

    def test_competing_empty_directory_at_publication_is_not_replaced(self):
        factory = module._noreplace_publisher
        raced_identity = []
        def race_factory():
            publish = factory()
            def race(source, destination):
                destination.mkdir()
                raced_identity.append((destination.stat().st_dev, destination.stat().st_ino))
                return publish(source, destination)
            return race
        with patch.object(module, '_noreplace_publisher', side_effect=race_factory):
            with self.assertRaises(OSError):
                self.call()
        self.assertTrue(self.output.is_dir())
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertEqual((self.output.stat().st_dev, self.output.stat().st_ino), raced_identity[0])
        self.assertEqual(list(self.root.glob('.g0-osm-pending-*')), [])

    def test_interrupt_after_native_publication_removes_only_owned_directory(self):
        factory = module._noreplace_publisher
        def interrupted_factory():
            publish = factory()
            def interrupted(source, destination):
                publish(source, destination)
                raise KeyboardInterrupt('interrupt after native move')
            return interrupted
        with patch.object(module, '_noreplace_publisher', side_effect=interrupted_factory):
            with self.assertRaises(KeyboardInterrupt):
                self.call(windows=1)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.g0-osm-pending-*')), [])

    def test_all_owned_directories_are_sealed_children_before_root(self):
        synced, barriers = [], []
        original = module._G0CapsuleWriter.sync_directory
        real_barrier = module._sync_directory
        def track(writer, path):
            synced.append(Path(path))
            return original(writer, path)
        def barrier(path):
            barriers.append(Path(path))
            return real_barrier(path)
        with patch.object(module._G0CapsuleWriter, 'sync_directory', side_effect=track, autospec=True), \
             patch.object(module, '_sync_directory', side_effect=barrier):
            self.call(windows=1)
        staging = next(path for path in synced if path.name.startswith('.g0-osm-pending-'))
        directories = {staging} | {staging / path.relative_to(self.output)
                                  for path in self.output.rglob('*') if path.is_dir()}
        sealed = synced[-len(directories)-1:-1]
        self.assertEqual(set(sealed), directories)
        self.assertEqual(sealed[-1], staging)
        self.assertEqual([len(p.parts) for p in sealed], sorted((len(p.parts) for p in sealed), reverse=True))
        if os.name == 'posix':
            self.assertEqual(barriers, synced)
        else:
            self.assertEqual(barriers, [])

    def test_unsupported_posix_publisher_has_no_unsafe_rename_fallback(self):
        with patch.object(module.os, 'name', 'posix'), patch.object(module.sys, 'platform', 'darwin'), \
             patch.object(module.os, 'rename', side_effect=AssertionError('unsafe rename fallback')):
            with self.assertRaisesRegex(self.g0.ForecastCapabilityError, 'CAPABILITY_BLOCKED'):
                module._noreplace_publisher()

    def test_post_cutoff_current_intake_is_blocked_instead_of_backdated(self):
        with patch.object(module, 'aware', wraps=module.aware):
            with self.assertRaisesRegex(ValueError, 'cutoff'):
                module.materialize_g0(self.repo, self.output, NIGHT, READY, START, 1)
        self.assertFalse(self.output.exists())

    def test_whole_domain_validation_failure_leaves_no_published_manifest(self):
        with patch.object(self.g0, 'validate_g0_forecast', side_effect=ValueError('last shard invalid')):
            with self.assertRaisesRegex(ValueError, 'last shard'):
                self.call()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.g0-osm-pending-*')), [])

    def test_actual_read_ledger_includes_intake_copy_check_and_final_rescan(self):
        context = self.pi.ProspectiveReadContext(30, self.g0.MAX_TOTAL_READ_BYTES)
        context.account(123)
        result = self.call(_read_context=context)
        self.assertEqual(result['actual_read_bytes'], context.bytes_read)
        self.assertEqual(result['producer_read_bytes'], context.bytes_read - 123)
        self.assertGreater(result['producer_read_bytes'], result['validation']['validation_read_bytes'])
        self.assertFalse(result['validation']['fit_authorized'])

    def test_model_capacity_is_separate_and_never_truncates_declared_horizon(self):
        with patch.object(self.g0, 'MAX_MODEL_ROWS', 5):
            result = self.call()
            self.assertEqual(result['rows'], 16)
            self.assertEqual(result['validation']['row_count'], 16)
            with self.assertRaisesRegex(self.g0.ForecastCapacityError, 'collector rows'):
                self.g0.load_g0_forecast_rows(self.output, result['manifest_ref'], NIGHT, datetime.fromisoformat(CUTOFF),
                                               expected_feature_definition_sha256=result['feature_definition_sha256'])

    def test_expired_context_rejects_before_any_input_open_or_output_creation(self):
        context = self.pi.ProspectiveReadContext(30, self.g0.MAX_TOTAL_READ_BYTES)
        context.deadline = -1
        with patch.object(Path, 'open', side_effect=AssertionError('expired input opened')):
            with self.assertRaises(TimeoutError):
                self.call(_read_context=context)
        self.assertFalse(self.output.exists())

    def test_incomplete_original_parts_and_boundary_crossing_do_not_publish(self):
        target, _ = self.parts[-1]
        target.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.call()
        self.assertFalse(self.output.exists())
        with self.assertRaises(ValueError):
            module.materialize_g0(self.repo, self.output, NIGHT, CUTOFF, '2026-10-15T06:50:00+09:00', 2)
        self.assertFalse(self.output.exists())

    def test_completion_clock_and_deadline_after_rename_remove_own_output(self):
        for mode in ('cutoff', 'deadline'):
            with self.subTest(mode=mode):
                context = self.pi.ProspectiveReadContext(30, self.g0.MAX_TOTAL_READ_BYTES)
                original_rename = module.os.rename
                clock = [datetime.fromisoformat(READY)]
                class Clock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return clock[0].astimezone(tz or timezone.utc)
                def late_rename(source, destination):
                    original_rename(source, destination)
                    if mode == 'cutoff':
                        clock[0] = datetime.fromisoformat(CUTOFF)
                    else:
                        context.deadline = -1
                with patch.object(module, 'datetime', Clock), patch.object(module.os, 'rename', side_effect=late_rename):
                    with self.assertRaises((ValueError, TimeoutError)):
                        self.call(_read_context=context)
                self.assertFalse(self.output.exists())
                self.assertEqual(list(self.root.glob('.g0-osm-pending-*')), [])

    def test_original_final_rescan_mutation_blocks_without_publishing(self):
        original = self.g0.G0ArtifactReader.rescan
        def mutate(reader):
            if reader.root == self.repo:
                target, raw = self.parts[-1]
                target.write_bytes(raw + b'!')
            return original(reader)
        with patch.object(self.g0.G0ArtifactReader, 'rescan', side_effect=mutate, autospec=True):
            with self.assertRaises(ValueError):
                self.call()
        self.assertFalse(self.output.exists())

    def test_input_ancestor_indirection_rejected_before_open(self):
        alias = self.root / 'alias'
        if os.name == 'nt':
            made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(self.repo)], capture_output=True)
            self.assertEqual(made.returncode, 0, made.stderr)
        else:
            alias.symlink_to(self.repo, target_is_directory=True)
        original_repo = self.repo
        self.repo = alias
        try:
            with patch.object(Path, 'open', side_effect=AssertionError('indirect input opened')):
                with self.assertRaisesRegex(ValueError, '[Rr]eparse|[Ss]ymlink|[Jj]unction'):
                    self.call()
        finally:
            self.assertEqual(alias.absolute().parent.resolve(), self.root.resolve())
            if os.name == 'nt':
                self.assertTrue(alias.is_junction())
                os.rmdir(alias)
            else:
                self.assertTrue(alias.is_symlink())
                alias.unlink()
            self.assertTrue(original_repo.is_dir())
            self.assertTrue(all(target.read_bytes() == raw for target, raw in self.parts))
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

