"""Ex-ante weather acquisition: real source bytes, no retroactive/fake ORIGINAL."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "exante_weather_test_module", ROOT / "scripts" / "acquire_exante_weather.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
UTC = timezone.utc


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "features/weather_sampling_sites.json").read_text())
        self.now = datetime.fromisoformat("2026-10-24T10:00:00+09:00")

    def forecast(self, url):
        params = parse_qs(urlsplit(url).query)
        lat, lon = float(params["latitude"][0]), float(params["longitude"][0])
        assert params["timezone"] == ["Asia/Tokyo"]
        assert params["past_days"] == [] if "past_days" in params else True
        hours = [(datetime.fromisoformat("2026-10-24T11:00:00") +
                  timedelta(hours=i)).isoformat(timespec="minutes")
                 for i in range(24)]
        return json.dumps({
            "timezone": "Asia/Tokyo",
            "latitude": lat,
            "longitude": lon,
            "hourly": {
                "time": hours,
                "temperature_2m": [24.0] * len(hours),
                "relative_humidity_2m": [82] * len(hours),
                "precipitation": [0.4] * len(hours),
                "pressure_msl": [1013.2] * len(hours),
                "wind_speed_10m": [3.2] * len(hours),
                "wind_direction_10m": [65] * len(hours),
            }
        }, ensure_ascii=False).encode("utf-8")

    def test_two_islands_preserve_real_source_bytes_and_cutoff(self):
        bundle = mod.acquire("2026-10-24", self.config,
                             clock=lambda: self.now,
                             fetcher=self.forecast)
        self.assertEqual(bundle["status"], "WEATHER_SOURCE_CAPTURED_NOT_PRODUCTION_P0")
        self.assertEqual(len(bundle["sites"]), 2)
        self.assertFalse(bundle["scientific_scope"]["original_p0_issued"])
        self.assertFalse(bundle["scientific_scope"]["spatial_road_interpolation_verified"])
        self.assertEqual({x["island"] for x in bundle["sites"]}, {"奄美大島", "加計呂麻島"})
        for site in bundle["sites"]:
            self.assertEqual(site["raw_sha256"],
                             hashlib.sha256(site["raw_body_utf8"].encode("utf-8")).hexdigest())
            self.assertEqual(site["resolution_minutes"], 60)
            self.assertTrue(site["future_hourly_rows"])
            for row in site["future_hourly_rows"]:
                t = datetime.fromisoformat(row["valid_at_jst"])
                self.assertGreater(t, self.now)
                self.assertLess(t, datetime.fromisoformat("2026-10-25T07:00:00+09:00"))

    def test_append_only_preserves_snapshot(self):
        bundle = mod.acquire("2026-10-24", self.config,
                             clock=lambda: self.now, fetcher=self.forecast)
        with tempfile.TemporaryDirectory() as td:
            one = mod.atomic_archive(Path(td), bundle)
            original = one.read_bytes()
            self.assertEqual(one.read_bytes(), original)
            with self.assertRaises(FileExistsError):
                mod.atomic_archive(Path(td), bundle)
            self.assertEqual(one.read_bytes(), original)

    def test_past_night_cannot_rebuild_original_weather(self):
        with self.assertRaises(mod.WeatherAcquisitionError):
            mod.acquire("2026-10-22", self.config,
                        clock=lambda: self.now, fetcher=self.forecast)

    def test_commercial_use_blocked_on_free_api(self):
        with self.assertRaises(mod.WeatherAcquisitionError):
            mod.acquire("2026-10-24", self.config,
                        clock=lambda: self.now, fetcher=self.forecast,
                        purpose="commercial")

    def test_missing_weather_variable_rejected(self):
        def invalid(url):
            doc = json.loads(self.forecast(url))
            doc["hourly"].pop("precipitation")
            return json.dumps(doc).encode("utf-8")
        with self.assertRaises(mod.WeatherAcquisitionError):
            mod.acquire("2026-10-24", self.config,
                        clock=lambda: self.now, fetcher=invalid)

    def test_incorrect_timezone_rejected(self):
        def invalid(url):
            doc = json.loads(self.forecast(url))
            doc["timezone"] = "UTC"
            return json.dumps(doc).encode("utf-8")
        with self.assertRaises(mod.WeatherAcquisitionError):
            mod.acquire("2026-10-24", self.config,
                        clock=lambda: self.now, fetcher=invalid)

    def test_untrusted_network_response_not_treated_as_forecast(self):
        with self.assertRaises(mod.WeatherAcquisitionError):
            mod.acquire("2026-10-24", self.config,
                        clock=lambda: self.now, fetcher=lambda _: b'{"error":true}')

    def test_clock_reversal_rejected(self):
        times = [self.now, self.now - timedelta(seconds=1)]
        def clock():
            return times.pop(0)
        with self.assertRaises(mod.WeatherAcquisitionError):
            mod.acquire("2026-10-24",
                        {"schema_version": self.config["schema_version"],
                         "sites": self.config["sites"][:1]},
                        clock=clock, fetcher=self.forecast)

    def test_no_future_hours_rejected(self):
        def past_only(url):
            doc = json.loads(self.forecast(url))
            doc["hourly"]["time"] = ["2026-10-24T09:00"]
            for key in mod.HOURLY:
                doc["hourly"][key] = [doc["hourly"][key][0]]
            return json.dumps(doc).encode("utf-8")
        with self.assertRaises(mod.WeatherAcquisitionError):
            mod.acquire("2026-10-24", self.config,
                        clock=lambda: self.now, fetcher=past_only)


if __name__ == "__main__":
    unittest.main()
