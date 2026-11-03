"""Synthetic NAOJ numeric tables; no private locations or real source bodies."""
import copy
import hashlib
import importlib
from pathlib import Path
import sys
import unittest
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def source_url(*, start="2025-01-01", length=2, **changes):
    year, month, day = [int(v) for v in start.split("-")]
    params = dict(year=str(year), month=str(month), day=str(day), hour="12", min="0",
        choice="1", choice0="1", key="大島郡瀬戸内町(鹿児島県)", lat="28.1463888888889",
        lon="129.314722222222", hgt="0", lst="9", div="1", divu="3", len=str(length),
        lenu="3", nomenu="1", btn04="Go")
    params.update(changes)
    return "https://eco.mtk.nao.ac.jp/cgi-bin/koyomi/koyomix.cgi?" + urlencode(params, encoding="euc-jp")


def body(*, rows=None, header="月齢", title="月の高度・方位", location=None):
    location = location or "緯度:28.1464° 経度:129.3147° 標高:0.0 m 標準時:UT+9<sup>h</sup>"
    rows = rows if rows is not None else [("2025/01/01", "12:00:00", "1.2"), ("2025/01/02", "12:00:00", "2.2")]
    data = "".join("<tr><td>" + date + "</td><td>" + instant + "</td><td>30.1</td><td>155.0</td><td>948.1</td><td>" + age + "</td><td>月</td></tr>" for date, instant, age in rows)
    return ("<!doctype html><html><h3>" + title + "</h3><div>指定地点</div><div>" + location +
        '</div><table class="result" summary="データ"><tr><th>年月日</th><th>時刻</th><th>高度[°]</th><th>方位[°]</th><th>視半径[″]</th><th>' + header +
        "</th><th>天体</th></tr>" + data + "</table><h3>ご利用にあたって</h3></html>").encode("euc-jp")


def provenance(raw):
    return dict(provider="NAOJ", station_id="46525", station_name="大島郡瀬戸内町役場",
        source_type="ASTRONOMICAL_CALCULATION_RETRIEVED_RETROSPECTIVELY",
        requested_url=source_url(), resolved_url=source_url(),
        retrieved_at="2026-11-03T12:00:00+09:00", source_received_at="2026-11-03T12:00:01+09:00",
        derived_at="2026-11-03T12:00:02+09:00", materialized_at="2026-11-03T12:00:03+09:00",
        audited_at="2026-11-03T12:00:04+09:00", sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw), licence_url="https://eco.mtk.nao.ac.jp/koyomi/site/")


class HistoricalAstronomyTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module("historical_astronomy")
        except ModuleNotFoundError as exc:
            if exc.name != "historical_astronomy":
                raise
            self.fail("Historical astronomy adapter is not implemented")

    def normalize(self, raw=None, **changes):
        raw = body() if raw is None else raw
        receipt = provenance(raw)
        receipt.update(changes)
        return self.module.normalize_naoj_moon_age(raw, "2025-01-01", "2025-01-02", receipt)

    def test_noon_numeric_age_remains_a_calculation_with_owned_provenance(self):
        raw = body()
        receipt = provenance(raw)
        saved = copy.deepcopy(receipt)
        result = self.module.normalize_naoj_moon_age(raw, "2025-01-01", "2025-01-02", receipt)
        self.assertEqual(len(result["observations"]), 2)
        first = result["observations"][0]
        self.assertEqual(first["valid_start"], "2025-01-01T12:00:00+09:00")
        self.assertEqual(first["valid_start"], first["valid_end"])
        self.assertEqual(first["values"]["moon_age_days"]["value"], 1.2)
        self.assertEqual(first["values"]["moon_age_days"]["unit"], "day")
        self.assertEqual(first["values"]["moon_age_days"]["kind"], "ASTRONOMICAL_CALCULATION")
        self.assertEqual(result["geographic_support"], "REFERENCE_LOCATION_CALCULATION_ONLY")
        self.assertFalse(result["historical_ex_ante_proven"])
        self.assertEqual(result["training_eligibility"], "NOT_ASSESSED")
        self.assertEqual(result["illumination_fraction_status"], "NOT_PRODUCED")
        self.assertEqual(result["road_surface_moonlight_status"], "NOT_PRODUCED")
        self.assertEqual(result["usable_at"], "2026-11-03T12:00:04+09:00")
        result["source"]["provider"] = "changed"
        self.assertEqual(receipt, saved)

    def test_body_date_and_noon_must_match_even_when_source_is_rehashed(self):
        for rows in [[("2025/01/02", "12:00:00", "1.2"), ("2025/01/03", "12:00:00", "2.2")],
                     [("2025/01/01", "00:00:00", "1.2"), ("2025/01/02", "12:00:00", "2.2")]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.normalize(body(rows=rows))

    def test_duplicate_missing_or_reordered_days_never_count_as_complete_period(self):
        for rows in [[("2025/01/01", "12:00:00", "1.2")] * 2,
                     [("2025/01/01", "12:00:00", "1.2")],
                     [("2025/01/02", "12:00:00", "2.2"), ("2025/01/01", "12:00:00", "1.2")]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.normalize(body(rows=rows))

    def test_wrong_reference_point_timezone_title_or_age_units_reject(self):
        cases = [body(location="緯度:35.0000° 経度:129.3147° 標高:0.0 m 標準時:UT+9h"),
                 body(location="緯度:28.1464° 経度:129.3147° 標高:0.0 m 標準時:UT+0h"),
                 body(title="太陽の高度・方位"), body(header="月齢[hour]")]
        for raw in cases:
            with self.subTest(raw_size=len(raw)), self.assertRaises(ValueError):
                self.normalize(raw)

    def test_unknown_values_remain_unknown_without_zero_or_phase_imputation(self):
        for raw_value in ["", "---", "NaN", "inf", "-1", "31.1", "1.2 ]"]:
            with self.subTest(raw_value=raw_value):
                item = self.normalize(body(rows=[("2025/01/01", "12:00:00", raw_value),
                    ("2025/01/02", "12:00:00", "2.2")]))["observations"][0]["values"]["moon_age_days"]
                self.assertIsNone(item["value"])
                self.assertEqual(item["kind"], "UNKNOWN")
                self.assertEqual(item["raw_value"], raw_value)

    def test_new_moon_age_reset_is_not_mistaken_for_invalid_chronology(self):
        rows = [("2025/01/01", "12:00:00", "29.5"), ("2025/01/02", "12:00:00", "0.5")]
        self.assertEqual(self.normalize(body(rows=rows))["observations"][1]["values"]["moon_age_days"]["value"], .5)

    def test_wrong_url_station_period_noon_or_duplicate_parameter_reject(self):
        for url in [source_url(lat="35.0"), source_url(key="東京(東京都)"), source_url(length=1),
                    source_url(hour="19"), source_url() + "&lst=9", source_url().replace("koyomix.cgi", "koyomiy.cgi")]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.normalize(requested_url=url)
        for changes in [{"station_id": "13"}, {"provider": "OTHER"}, {"source_type": "OBSERVATION"},
                        {"resolved_url": source_url(start="2025-01-02")}, {"licence_url": "https://example.com/"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.normalize(**changes)

    def test_raw_bytes_hash_size_encoding_and_capacity_are_enforced(self):
        for changes in [{"sha256": "0" * 64}, {"sha256": "invalid"}, {"size_bytes": 1}, {"size_bytes": True}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.normalize(**changes)
        for raw in [b"", b"x" * (2 * 1024 * 1024 + 1), b"\xff"]:
            with self.subTest(length=len(raw)), self.assertRaises(ValueError):
                self.normalize(raw)

    def test_duplicate_tables_headers_or_location_blocks_reject(self):
        raw = body()
        table_start, table_end = raw.index(b"<table"), raw.index(b"</table>") + 8
        duplicated = raw[:table_end] + raw[table_start:table_end] + raw[table_end:]
        for invalid in [duplicated, raw.replace(b"<th>", b"<th></th><th>", 1),
                        raw.replace(b"</div><table", b"</div>" + "<div>緯度:28.1464° 経度:129.3147° 標高:0.0 m 標準時:UT+9h</div><table".encode("euc-jp"), 1)]:
            with self.subTest(length=len(invalid)), self.assertRaises(ValueError):
                self.normalize(invalid)

    def test_hidden_identity_or_result_markup_cannot_substitute_visible_source_evidence(self):
        raw = body()
        for invalid in [raw.replace(b"<h3>", b'<h3 hidden>', 1),
                        raw.replace(b"<h3>", b'<h3 style="display:none">', 1),
                        raw.replace(b"<table class=", b'<table aria-hidden="true" class=', 1)]:
            with self.subTest(length=len(invalid)), self.assertRaises(ValueError):
                self.normalize(invalid)

    def test_template_content_is_not_a_visible_provider_result(self):
        with self.assertRaises(ValueError):
            self.normalize(b"<template>" + body() + b"</template>")

    def test_script_text_cannot_supply_a_missing_visible_reference_location(self):
        raw = body(location="Reference unavailable")
        script = '<script>"緯度:28.1464° 経度:129.3147° 標高:0.0 m 標準時:UT+9h"</script>'.encode("euc-jp")
        with self.assertRaises(ValueError):
            self.normalize(raw.replace(b"</html>", script + b"</html>"))

    def test_backdated_or_naive_readiness_rejects(self):
        for name in ["retrieved_at", "source_received_at", "derived_at", "materialized_at", "audited_at"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.normalize(**{name: "2026-11-03T12:00:00"})
        with self.assertRaises(ValueError):
            self.normalize(derived_at="2025-01-03T12:00:00+09:00")

    def test_period_is_bounded_same_calendar_month_and_inclusive(self):
        for start, end in [("2025-01-02", "2025-01-01"), ("2025-01-01", "2025-02-01"),
                           ("2025-02-30", "2025-03-01"), ("2025-1-1", "2025-01-02")]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.module.normalize_naoj_moon_age(body(), start, end, provenance(body()))


if __name__ == "__main__":
    unittest.main()
