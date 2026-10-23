"""Read-only ex-ante source gate never claims that weather alone produces P0."""
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
