"""Read-only ex-ante source gate never claims that weather alone produces P0."""
import importlib.util
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
