"""Synthetic weather collector tests, no network and no capture coordinates."""
import datetime as dt
import json
import unittest
from tools.habu_weather import collect_koniya_weather as c


def fake(url):
    if "data.jma.go.jp" in url:
        raise OSError("OFFLINE_SYNTHETIC")
    if "historical-forecast-api.open-meteo.com" not in url:
        raise ValueError("WRONG_PROVIDER")
    time = ["2026-11-13T18:00", "2026-11-13T19:00"]
    payload = {"hourly": {"time": time, **{
        k: [21.0, 22.0] for k in c.VARS}}}
    return json.dumps(payload).encode(), url


class WeatherAcquisitionTests(unittest.TestCase):
    def test_date_scope_and_station_identity(self):
        self.assertEqual(len(c.days("2026-11-01", "2026-11-14")), 14)
        url = c.jma_url(dt.date(2026,11,13))
        self.assertIn("block_no=0980", url)
        self.assertIn("prec_no=88",url)
        with self.assertRaises(ValueError):
            c.days("2026-12-01","2026-11-01")

    def test_independent_weather_roles_and_missingness(self):
        d = c.collect("2026-11-13","2026-11-13",fetch=fake)
        self.assertEqual(d["jma"]["source_receipts"], [])
        self.assertEqual(len(d["jma"]["missing"]),1)
        self.assertEqual(d["model_archive"]["status"],
                         "ARCHIVED_FORECAST_MODEL_NOT_MEASUREMENT")
        self.assertFalse(d["historical_asof_forecast_proof"])
        self.assertEqual(d["formal_100m_10min_labels_created"],0)
        self.assertNotIn("捕獲",json.dumps(d,ensure_ascii=False))

    def test_invalid_model_response_not_made_into_weather(self):
        def broken(url):
            if "data.jma.go.jp" in url:
                raise ConnectionError("OFFLINE")
            return b'{"hourly":{"time":["2026-11-13T18:00","2026-11-13T18:00"]}}',url
        d=c.collect("2026-11-13","2026-11-13",fetch=broken)
        self.assertEqual(d["model_archive"]["status"],"NOT_VERIFIED")

    def test_research_model_url_uses_coarse_station_not_capture_point(self):
        u=c.model_url("2026-11-01","2026-11-14")
        self.assertIn("latitude=28.15",u)
        self.assertIn("longitude=129.32",u)
        self.assertNotIn("session",u)
        self.assertNotIn("capture",u)


if __name__=="__main__":
    unittest.main()
