"""Read-only ex-ante source gate never claims that weather alone produces P0."""
import importlib.util
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collector = load("habu_weather_assets_test", "acquire_exante_weather.py")
assets = load("habu_exante_assets_test", "audit_p0_exante_assets.py")


class AssetsTests(unittest.TestCase):
    def test_repository_has_auxiliary_road_but_no_verified_dem_or_production_model(self):
        report = assets.audit(ROOT, "2026-10-24",
                              datetime.fromisoformat("2026-10-24T17:00:00+09:00"))
        self.assertEqual(report["status"], "BLOCKED")
        self.assertFalse(report["original_p0_issued"])
        states = {i["input"]: i["status"] for i in report["items"]}
        self.assertEqual(states["road"], "AUXILIARY_CANDIDATE_ONLY")
        self.assertEqual(states["terrain"], "BLOCKED")
        self.assertEqual(states["learning"], "BLOCKED")
        self.assertEqual(states["production_model"], "BLOCKED")
        self.assertEqual(states["weather"], "BLOCKED")

    def test_internally_valid_weather_still_cannot_bypass_missing_model(self):
        config = json.loads((ROOT / "features/weather_sampling_sites.json").read_text())
        now = datetime.fromisoformat("2026-10-24T10:00:00+09:00")

        def response(url):
            from urllib.parse import urlsplit, parse_qs
            p = parse_qs(urlsplit(url).query)
            times = [(datetime.fromisoformat("2026-10-24T11:00:00") +
                      timedelta(hours=i)).isoformat(timespec="minutes")
                     for i in range(18)]
            return json.dumps({
                "timezone": "Asia/Tokyo",
                "latitude": float(p["latitude"][0]),
                "longitude": float(p["longitude"][0]),
                "hourly": {
                    "time": times,
                    **{k: [3.0] * len(times) for k in collector.HOURLY},
                },
            }).encode("utf-8")

        weather = collector.acquire("2026-10-24", config, clock=lambda: now,
                                    fetcher=response)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            location = collector.atomic_archive(root, weather)
            cutoff = datetime.fromisoformat("2026-10-24T10:10:00+09:00")
            report = assets.audit(root, "2026-10-24", cutoff,
                                  weather_snapshot=location.relative_to(root).as_posix())
            values = {i["input"]: i["status"] for i in report["items"]}
            self.assertEqual(values["weather"], "SOURCE_VERIFIED_NOT_PRODUCTION_READY")
            self.assertEqual(values["terrain"], "BLOCKED")
            self.assertEqual(values["production_model"], "BLOCKED")
            self.assertFalse(report["original_p0_issued"])

    def test_weather_after_cutoff_cannot_claim_predeparture_input(self):
        config = json.loads((ROOT / "features/weather_sampling_sites.json").read_text())
        now = datetime.fromisoformat("2026-10-24T10:00:00+09:00")
        hours = ["2026-10-24T11:00", "2026-10-24T12:00"]

        def fake(url):
            from urllib.parse import urlsplit, parse_qs
            p = parse_qs(urlsplit(url).query)
            return json.dumps({
                "timezone": "Asia/Tokyo",
                "latitude": float(p["latitude"][0]),
                "longitude": float(p["longitude"][0]),
                "hourly": {"time": hours,
                           **{key: [1, 2] for key in collector.HOURLY}},
            }).encode()
        weather = collector.acquire("2026-10-24", config, clock=lambda: now,
                                    fetcher=fake)
        with tempfile.TemporaryDirectory() as td:
            path = collector.atomic_archive(Path(td), weather)
            report = assets.audit(
                Path(td), "2026-10-24",
                datetime.fromisoformat("2026-10-24T09:59:00+09:00"),
                weather_snapshot=path.relative_to(td).as_posix())
            state = {i["input"]: i["status"] for i in report["items"]}
            self.assertEqual(state["weather"], "BLOCKED")

    def test_escaped_path_cannot_be_loaded(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                assets.audit(Path(td), "2026-10-24",
                             datetime.fromisoformat("2026-10-24T10:00:00+09:00"),
                             weather_snapshot="../../etc/passwd")


class TerrainEvidenceTests(unittest.TestCase):
    night = "2026-10-24"
    available = "2026-10-24T08:00:00+09:00"
    joined_at = "2026-10-24T08:10:00+09:00"
    complete_at = "2026-10-24T08:20:00+09:00"
    cutoff = "2026-10-24T10:00:00+09:00"

    def setUp(self):
        from build_gsi_road_dem import CODE_PATHS, digest, encoded, join_road_dem

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.terrain = self.root / "private-terrain"
        self.terrain.mkdir()
        self.encode = encoded
        self.digest = digest
        self.code = {path: digest((ROOT / path).read_bytes()) for path in CODE_PATHS}
        road = self.artifact("verified-public-roads.csv", b"cell_id,cell_center_x,cell_center_y,candidate_source,road_direction_deg,island_name\n"
                             b"utm52n_100m_1001_1001,100150,100150,osm_auxiliary,25,synthetic\n"
                             b"utm52n_100m_1010_1010,101050,101050,osm_auxiliary,25,synthetic\n")
        dem = self.artifact("road-neighbour-dem-50m.asc", b"ncols 5\nnrows 5\nxllcorner 100000\nyllcorner 100000\ncellsize 50\nNODATA_value -999999\n"
                            + b"1 2 3 4 5\n" * 5)
        mapping = self.artifact("required-node-source-map.csv", b"synthetic_mapping\n")
        self.join = join_road_dem(self.terrain / road["path"], self.terrain / dem["path"],
            road_sha256=road["sha256"], dem_sha256=dem["sha256"], dem_epsg=32652,
            road_available_at=self.available, dem_available_at=self.available, cutoff_time=self.joined_at)
        joined = self.artifact("road-dem-join.json", self.encode(self.join), self.complete_at)
        self.report = dict(schema_version="gsi-road-dem-conversion-v1", status=self.join["status"],
            total_cells=2, coverage_cells=1, missing_cells=1, road_sha256=road["sha256"],
            target_crs="EPSG:32652", formal_p0_eligible=False, terrain_wind_shielding_verified=False,
            completed_at=self.complete_at, code_sha256=self.code, artifacts=[road, dem, mapping, joined])

    def artifact(self, filename, raw, available=None):
        stamp = available or self.available
        (self.terrain / filename).write_bytes(raw)
        doc = dict(schema_version="gsi-derived-readiness-v1", path=filename, sha256=self.digest(raw),
            size_bytes=len(raw), source_received_at=stamp, derived_at=stamp, materialized_at=stamp,
            audited_at=stamp, usable_at=stamp, code_sha256=self.code)
        proof = self.encode(doc)
        seal = filename + ".readiness.json"
        (self.terrain / seal).write_bytes(proof)
        return dict(doc, readiness_receipt=dict(path=seal, sha256=self.digest(proof), size_bytes=len(proof)))

    def audit_terrain(self, *, cutoff=None, expected=None, private=None):
        raw = self.encode(self.report)
        (self.terrain / "conversion.json").write_bytes(raw)
        # Only the production archive's pinned fingerprint is substituted for this tiny synthetic road fixture.
        with patch("build_gsi_road_dem.CELLS_SHA256", self.report["road_sha256"]):
            out = assets.audit(self.root, self.night, datetime.fromisoformat(cutoff or self.cutoff),
                terrain_root=private or self.terrain, terrain_report="conversion.json",
                terrain_sha256=expected or hashlib.sha256(raw).hexdigest())
        self.assertFalse(out["original_p0_issued"])
        self.assertEqual(out["status"], "BLOCKED")
        return next(x for x in out["items"] if x["input"] == "terrain")

    def test_bound_private_terrain_is_recomputed_with_explicit_unknowns(self):
        terrain = self.audit_terrain()
        self.assertEqual(terrain["status"], "TERRAIN_RECOMPUTED_NOT_PRODUCTION_READY")
        self.assertEqual((terrain["coverage_cells"], terrain["missing_cells"], terrain["total_cells"]), (1, 1, 2))
        self.assertFalse(terrain["formal_p0_eligible"])
        self.assertFalse(terrain["terrain_wind_shielding_verified"])
        self.assertNotIn("utm52n_", json.dumps(terrain))
        self.assertNotIn(str(self.terrain), json.dumps(terrain))

    def test_report_and_all_derivation_availability_must_precede_cutoff(self):
        self.assertEqual(self.audit_terrain(cutoff=self.complete_at)["reason"], "TERRAIN_NOT_BEFORE_CUTOFF")
        self.assertEqual(self.audit_terrain(expected="0" * 64)["reason"], "TERRAIN_REPORT_HASH_MISMATCH")

    def test_resealed_claimed_slope_is_rejected_by_native_recomputation(self):
        self.join["cells"][0]["slope_deg"] = 44
        self.report["artifacts"][-1] = self.artifact("road-dem-join.json", self.encode(self.join), self.complete_at)
        self.assertEqual(self.audit_terrain()["reason"], "TERRAIN_RECOMPUTATION_MISMATCH")

    def test_changed_artifact_and_tracked_path_fail_without_private_path_in_output(self):
        (self.terrain / "required-node-source-map.csv").write_bytes(b"changed\n")
        bad = self.audit_terrain()
        self.assertEqual(bad["status"], "BLOCKED")
        self.assertNotIn(str(self.terrain), json.dumps(bad))
        self.assertEqual(self.audit_terrain(private=ROOT)["status"], "BLOCKED")


class WeatherRawIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.fromisoformat("2026-10-24T10:00:00+09:00")
        config = json.loads((ROOT / "features/weather_sampling_sites.json").read_bytes())

        def response(url):
            from urllib.parse import parse_qs, urlsplit
            point = parse_qs(urlsplit(url).query)
            return json.dumps({
                "timezone": "Asia/Tokyo",
                "latitude": float(point["latitude"][0]),
                "longitude": float(point["longitude"][0]),
                "hourly_units": {"time": "iso8601", "temperature_2m": "°C",
                    "relative_humidity_2m": "%", "precipitation": "mm", "pressure_msl": "hPa",
                    "wind_speed_10m": "m/s", "wind_direction_10m": "°"},
                "hourly": {
                    "time": ["2026-10-24T11:00", "2026-10-24T12:00"],
                    "temperature_2m": [24.0, 25.0],
                    "relative_humidity_2m": [82, 80],
                    "precipitation": [0.4, 0.0],
                    "pressure_msl": [1013.2, 1013.5],
                    "wind_speed_10m": [3.2, 2.5],
                    "wind_direction_10m": [65, 70],
                },
            }).encode("utf-8")

        self.weather = collector.acquire("2026-10-24", config,
                                         clock=lambda: self.now, fetcher=response)

    def audit_weather(self, weather, *, cutoff=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            location = collector.atomic_archive(root, weather)
            report = assets.audit(root, "2026-10-24", cutoff or self.now,
                                  weather_snapshot=location.relative_to(root).as_posix())
            self.assertFalse(report["original_p0_issued"])
            self.assertEqual(report["status"], "BLOCKED")
            return next(row for row in report["items"] if row["input"] == "weather")

    def test_normalized_temperature_humidity_and_rain_must_match_original_bytes(self):
        for key, changed in (("temperature_2m", 99.0),
                             ("relative_humidity_2m", 1),
                             ("precipitation", 200.0)):
            with self.subTest(variable=key):
                altered = copy.deepcopy(self.weather)
                altered["sites"][0]["future_hourly_rows"][0][key] = changed
                for field in ("raw_body_utf8", "raw_sha256", "available_at_utc"):
                    self.assertEqual(altered["sites"][0][field],
                                     self.weather["sites"][0][field])
                self.assertEqual(self.audit_weather(altered)["status"], "BLOCKED")

    def test_original_normalizer_bundle_is_accepted_offline_without_mutation(self):
        from unittest.mock import patch
        original = copy.deepcopy(self.weather)
        # Only network I/O is replaced; normalization/archive/audit are real.
        with patch("acquire_exante_weather.urlopen", side_effect=AssertionError("No network")):
            self.assertEqual(self.audit_weather(self.weather)["status"],
                             "SOURCE_VERIFIED_NOT_PRODUCTION_READY")
        self.assertEqual(self.weather, original)

    def test_private_archive_requires_exact_reference_and_keeps_the_repository_road_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            location = collector.atomic_archive(root, self.weather)
            relative = location.relative_to(root).as_posix()
            raw = location.read_bytes()
            expected = hashlib.sha256(raw).hexdigest()
            later = self.now + timedelta(microseconds=1)
            for root_value, path, sha, cutoff, state in (
                (root, relative, expected, later, "SOURCE_VERIFIED_NOT_PRODUCTION_READY"),
                (root, relative, expected, self.now, "BLOCKED"),
                (root, relative, "0" * 64, later, "BLOCKED"),
                (root, relative, None, later, "BLOCKED"),
                (root, "../" + relative, expected, later, "BLOCKED"),
                (ROOT, relative, expected, later, "BLOCKED"),
            ):
                with self.subTest(status=state, path=path, sha=sha):
                    report = assets.audit(ROOT, "2026-10-24", cutoff, weather_snapshot=path,
                        weather_root=root_value, weather_sha256=sha)
                    items = {item["input"]: item for item in report["items"]}
                    self.assertEqual(items["weather"]["status"], state)
                    self.assertEqual(items["road"]["status"], "AUXILIARY_CANDIDATE_ONLY")
                    self.assertFalse(report["original_p0_issued"])
                    self.assertNotIn(str(root), json.dumps(items["weather"]))
                    if state != "BLOCKED":
                        self.assertEqual(items["weather"]["sha256"], expected)
            self.assertEqual(location.read_bytes(), raw)

    def test_private_archive_rejects_elapsed_hours_duplicate_fields_wrong_units_and_bad_provider_clock(self):
        with tempfile.TemporaryDirectory() as td:
            private = Path(td)
            for case in ("elapsed", "duplicate_archive", "duplicate_raw", "wrong_units", "provider_clock"):
                with self.subTest(case=case):
                    value = copy.deepcopy(self.weather)
                    if case in ("duplicate_raw", "wrong_units", "provider_clock"):
                        site = value["sites"][0]
                        raw = site["raw_body_utf8"]
                        if case == "duplicate_raw":
                            raw = '{"timezone":"UTC",' + raw[1:]
                        elif case == "wrong_units":
                            raw = raw.replace('"m/s"', '"km/h"')
                        else:
                            raw = raw.replace('"2026-10-24T11:00"', '"2026-10-24T11:00+08:60"')
                        site["raw_body_utf8"] = raw
                        site["raw_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                    path = collector.atomic_archive(private / case, value)
                    data = path.read_bytes()
                    if case == "duplicate_archive":
                        data = b'{"provider":"unknown provider",' + data[1:]
                        path = path.with_name("duplicate.json")
                        path.write_bytes(data)
                    cutoff = self.now + (timedelta(hours=3) if case == "elapsed" else timedelta(seconds=2))
                    result = assets.audit(ROOT, "2026-10-24", cutoff, weather_root=private,
                        weather_snapshot=path.relative_to(private).as_posix(),
                        weather_sha256=hashlib.sha256(data).hexdigest())
                    weather = next(row for row in result["items"] if row["input"] == "weather")
                    self.assertEqual(weather["status"], "BLOCKED")
                    if case == "elapsed":
                        self.assertEqual(weather["reason"], "WEATHER_NO_POSTCUTOFF_HOURS")

    def test_private_bad_site_config_and_cli_offset_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            private = root / "private"
            path = collector.atomic_archive(private, self.weather)
            data = path.read_bytes()
            (root / "features").mkdir()
            (root / "features/weather_sampling_sites.json").write_text("[]", encoding="utf-8")
            result = assets.audit(root, "2026-10-24", self.now + timedelta(seconds=2), weather_root=private,
                weather_snapshot=path.relative_to(private).as_posix(), weather_sha256=hashlib.sha256(data).hexdigest())
            self.assertEqual(next(row for row in result["items"] if row["input"] == "weather")["status"], "BLOCKED")
            run = subprocess.run([sys.executable, str(ROOT / "scripts/audit_p0_exante_assets.py"),
                "--night", "2026-10-24", "--cutoff", "2026-10-24T10:00:02+08:60", "--weather-root", str(private),
                "--weather-snapshot", path.relative_to(private).as_posix(),
                "--weather-sha256", hashlib.sha256(data).hexdigest()], capture_output=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertNotIn(b"SOURCE_VERIFIED", run.stdout)

    def test_private_archive_rejects_resealed_clock_and_sampling_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cutoff = self.now + timedelta(seconds=2)
            for changed in ("offset", "started_after_receipt", "unregistered_site", "provider"):
                with self.subTest(changed=changed):
                    altered = copy.deepcopy(self.weather)
                    if changed == "offset":
                        altered["available_at_utc"] = "2026-10-24T00:00:00+00:60"
                    elif changed == "started_after_receipt":
                        altered["acquisition_started_at_utc"] = "2026-10-24T01:00:01+00:00"
                    elif changed == "unregistered_site":
                        altered["sites"][0]["site_id"] = "unregistered_site"
                    else:
                        altered["provider"] = "unknown provider"
                    location = collector.atomic_archive(root, altered)
                    report = assets.audit(ROOT, "2026-10-24", cutoff,
                        weather_root=root, weather_snapshot=location.relative_to(root).as_posix(),
                        weather_sha256=hashlib.sha256(location.read_bytes()).hexdigest())
                    weather = next(row for row in report["items"] if row["input"] == "weather")
                    self.assertEqual(weather["status"], "BLOCKED")
                    self.assertNotIn(str(root), json.dumps(weather))

    def test_remaining_variables_and_bool_substitution_are_rejected(self):
        for key, changed in (("pressure_msl", 999.0), ("wind_speed_10m", 12),
                             ("wind_direction_10m", 180), ("precipitation", False)):
            with self.subTest(variable=key, changed=changed):
                altered = copy.deepcopy(self.weather)
                index = 1 if changed is False else 0
                altered["sites"][0]["future_hourly_rows"][index][key] = changed
                self.assertEqual(self.audit_weather(altered)["status"], "BLOCKED")

    def test_row_omission_order_extra_fields_and_changed_time_are_rejected(self):
        for change in ("omit", "reverse", "extra", "time"):
            with self.subTest(change=change):
                altered = copy.deepcopy(self.weather)
                rows = altered["sites"][0]["future_hourly_rows"]
                if change == "omit":
                    rows.pop()
                elif change == "reverse":
                    rows.reverse()
                elif change == "extra":
                    rows[0]["invented_value"] = 1
                else:
                    rows[0]["valid_at_jst"] = "2026-10-24T10:30:00+09:00"
                self.assertEqual(self.audit_weather(altered)["status"], "BLOCKED")

    def test_declared_grid_url_and_receipt_hour_selection_are_rechecked(self):
        for change in ("grid", "url", "receipt"):
            with self.subTest(change=change):
                altered = copy.deepcopy(self.weather)
                sample = altered["sites"][0]
                if change == "grid":
                    sample["provider_grid_point"][0] += 0.01
                elif change == "url":
                    sample["request_url"] = "https://example.invalid/other"
                else:
                    sample["available_at_utc"] = "2026-10-24T02:30:00+00:00"
                cutoff = datetime.fromisoformat("2026-10-24T12:30:00+09:00")
                self.assertEqual(self.audit_weather(altered, cutoff=cutoff)["status"], "BLOCKED")

    def test_corrupt_and_malformed_original_body_cannot_be_rebound_as_valid(self):
        import hashlib
        for change in ("sha", "missing_variable", "nonfinite", "wrong_timezone"):
            with self.subTest(change=change):
                altered = copy.deepcopy(self.weather)
                sample = altered["sites"][0]
                raw = json.loads(sample["raw_body_utf8"])
                if change in ("sha", "missing_variable"):
                    del raw["hourly"]["precipitation"]
                elif change == "nonfinite":
                    raw["hourly"]["temperature_2m"][0] = float("inf")
                else:
                    raw["timezone"] = "UTC"
                sample["raw_body_utf8"] = json.dumps(raw)
                if change != "sha":
                    sample["raw_sha256"] = hashlib.sha256(
                        sample["raw_body_utf8"].encode("utf-8")).hexdigest()
                original = copy.deepcopy(altered)
                self.assertEqual(self.audit_weather(altered)["status"], "BLOCKED")
                self.assertEqual(altered, original)

    def test_huge_original_numeric_values_fail_closed_in_archive_audit(self):
        import hashlib
        for change in ("forecast", "grid"):
            with self.subTest(change=change):
                altered = copy.deepcopy(self.weather)
                sample = altered["sites"][0]
                raw = json.loads(sample["raw_body_utf8"])
                if change == "forecast":
                    raw["hourly"]["temperature_2m"][0] = 10 ** 400
                else:
                    raw["latitude"] = 10 ** 400
                sample["raw_body_utf8"] = json.dumps(raw)
                sample["raw_sha256"] = hashlib.sha256(
                    sample["raw_body_utf8"].encode("utf-8")).hexdigest()
                self.assertEqual(self.audit_weather(altered)["status"], "BLOCKED")

    def test_declared_hourly_resolution_requires_aligned_one_hour_cadence(self):
        import hashlib
        cases = {
            "half_hour": ("2026-10-24T11:00", "2026-10-24T11:30"),
            "off_hour": ("2026-10-24T11:15", "2026-10-24T12:15"),
            "missing_hour": ("2026-10-24T11:00", "2026-10-24T13:00"),
            "off_second": ("2026-10-24T11:00:01", "2026-10-24T12:00:01"),
            "off_microsecond": ("2026-10-24T11:00:00.000001", "2026-10-24T12:00:00.000001"),
        }
        for name, times in cases.items():
            with self.subTest(cadence=name):
                altered = copy.deepcopy(self.weather)
                for sample in altered["sites"]:
                    raw = json.loads(sample["raw_body_utf8"])
                    raw["hourly"]["time"] = list(times)
                    sample["raw_body_utf8"] = json.dumps(raw)
                    sample["raw_sha256"] = hashlib.sha256(
                        sample["raw_body_utf8"].encode("utf-8")).hexdigest()
                    for row, stamp in zip(sample["future_hourly_rows"], times):
                        row["valid_at_jst"] = datetime.fromisoformat(stamp).replace(
                            tzinfo=collector.JST).isoformat()
                    # The original provider normalizer admits these exact raw
                    # bytes/derived values; only the declared cadence is false.
                    point = sample["requested_point"]
                    site = {"site_id": sample["site_id"], "island": sample["island"],
                            "latitude": point[0], "longitude": point[1]}
                    self.assertEqual(collector._normalize(
                        site, sample["raw_body_utf8"].encode("utf-8"), self.now,
                        "2026-10-24", sample["request_url"]), sample)
                    self.assertEqual(sample["resolution_minutes"], 60)
                self.assertEqual(self.audit_weather(altered)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
