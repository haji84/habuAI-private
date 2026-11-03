"""Synthetic provider tables only; these tests do not attest real field evidence."""
import copy
import hashlib
import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
JST = timezone(timedelta(hours=9))


def table(*, change=None, header=None):
    headings = header or ["時", "降水量(mm)", "気温(℃)", "露点温度(℃)",
                          "蒸気圧(hPa)", "相対湿度(％)", "風速(m/s)", "風向",
                          "日照時間(h)", "降雪(cm)", "積雪(cm)"]
    rows = []
    for hour in range(1, 25):
        cells = [str(hour), "1.5", "22.3", "99.9", "20.1", "80", "2.5", "北北東", "--", "--", "--"]
        if change:
            cells = change(hour, cells)
        if cells is not None:
            rows.append("<tr>" + "".join('<td class="data_0_0">' + c + "</td>" for c in cells) + "</tr>")
    return ('<!doctype html><html><meta charset="utf-8"><table id="tablefix1"><tr>' +
            "".join("<th>" + h + "</th>" for h in headings) + "</tr>" +
            "".join(rows) + "</table></html>").encode("utf-8")


def receipt(raw, *, day="2026-11-01"):
    year, month, date = (int(x) for x in day.split("-"))
    url = ("https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php?prec_no=88&block_no=0980"
           f"&year={year}&month={month}&day={date}&view=p1")
    return dict(provider="JMA", station_id="88901", station_name="古仁屋",
                source_type="STATION_OBSERVATION", requested_url=url, resolved_url=url,
                retrieved_at="2026-11-03T10:00:00+09:00", size_bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                licence_url="https://www.jma.go.jp/jma/kishou/info/coment.html",
                source_received_at="2026-11-03T10:00:01+09:00",
                derived_at="2026-11-03T10:00:02+09:00",
                materialized_at="2026-11-03T10:00:03+09:00",
                audited_at="2026-11-03T10:00:04+09:00")


def rainfall_rows(*, hours=72):
    end = datetime(2026, 11, 2, tzinfo=JST)
    rows = []
    for index in range(hours):
        # Most recent day=1mm/h, previous=2mm/h, oldest=3mm/h.
        finish = end - timedelta(hours=index)
        rows.append(dict(valid_start=(finish - timedelta(hours=1)).isoformat(),
                         valid_end=finish.isoformat(), support_kind="HOURLY_REFERENCE_STATION",
                         values={"precipitation_mm": dict(value=float(index // 24 + 1), unit="mm",
                             kind="OBSERVED", quality="NORMAL", raw_value=str(index // 24 + 1),
                             source_cell={"hour": finish.hour or 24, "column": 1, "td_class": "data_0_0"})}))
    return rows


class HistoricalEnvironmentTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module("historical_environment")
        except ModuleNotFoundError as exc:
            if exc.name != "historical_environment":
                raise
            self.fail("The historical source normalizer has not been implemented")

    def normalize(self, raw=None, **changes):
        raw = table() if raw is None else raw
        provenance = receipt(raw)
        provenance.update(changes)
        return self.module.normalize_jma_hourly(raw, day="2026-11-01", receipt=provenance)

    def test_normal_values_keep_station_and_variable_support_without_qualification(self):
        result = self.normalize()
        self.assertEqual(len(result["observations"]), 24)
        first = result["observations"][0]
        self.assertEqual(first["valid_start"], "2026-11-01T00:00:00+09:00")
        self.assertEqual(first["valid_end"], "2026-11-01T01:00:00+09:00")
        values = first["values"]
        self.assertEqual(set(values), {"precipitation_mm", "temperature_c", "relative_humidity_pct",
                                      "wind_speed_mps", "wind_direction_deg", "wind_direction_16pt"})
        self.assertEqual(values["precipitation_mm"]["value"], 1.5)
        self.assertEqual(values["wind_direction_deg"]["value"], 22.5)
        self.assertEqual(values["wind_direction_deg"]["kind"], "DERIVED_FROM_OBSERVATION")
        self.assertEqual(values["wind_direction_deg"]["angular_bin_half_width_deg"], 11.25)
        self.assertTrue(values["wind_direction_deg"]["wind_from_semantics"])
        self.assertEqual(values["wind_direction_16pt"]["value"], "北北東")
        self.assertEqual(values["temperature_c"]["valid_start"], first["valid_end"])
        self.assertEqual(values["temperature_c"]["valid_end"], first["valid_end"])
        self.assertEqual(values["wind_speed_mps"]["valid_start"], "2026-11-01T00:50:00+09:00")
        self.assertEqual(values["precipitation_mm"]["source_cell"],
                         {"hour": 1, "column": 1, "td_class": "data_0_0"})
        self.assertEqual(result["geographic_support"], "REFERENCE_STATION_ONLY")
        self.assertFalse(result["historical_ex_ante_proven"])
        self.assertEqual(result["training_eligibility"], "NOT_ASSESSED")

    def test_calm_wind_category_does_not_invent_a_north_azimuth(self):
        def change(hour, cells):
            cells[7] = "静穏"
            return cells
        values = self.normalize(table(change=change))["observations"][0]["values"]
        self.assertEqual(values["wind_direction_16pt"]["value"], "静穏")
        self.assertEqual(values["wind_direction_16pt"]["kind"], "OBSERVED")
        self.assertIsNone(values["wind_direction_deg"]["value"])
        self.assertEqual(values["wind_direction_deg"]["kind"], "UNKNOWN")

    def test_provider_multilevel_headers_with_humidity_and_mean_wind_are_supported(self):
        first = ["時", "降水量(mm)", "気温(℃)", "露点温度(℃)", "蒸気圧(hPa)", "湿度(％)"]
        headers = "<tr>" + "".join('<th rowspan="2">' + h + "</th>" for h in first)
        headers += '<th colspan="2">風速・風向</th><th rowspan="2">日照時間(h)</th><th colspan="2">雪</th></tr>'
        headers += '<tr><th>平均風速(m/s)</th><th>風向</th><th>降雪(cm)</th><th>積雪(cm)</th></tr>'
        raw = table()
        begin, end = raw.index(b"<tr>"), raw.index(b"</tr>") + len(b"</tr>")
        raw = raw[:begin] + headers.encode() + raw[end:]
        self.assertEqual(len(self.normalize(raw)["observations"]), 24)

    def test_valid_provider_implicit_header_row_end_is_supported(self):
        raw = table().replace(b"</th></tr><tr>", b"</th><tr>", 1)
        self.assertEqual(len(self.normalize(raw)["observations"]), 24)

    def test_24_hour_rollover_and_operational_nights_are_not_calendar_midnight(self):
        rows = self.normalize()["observations"]
        self.assertEqual(rows[-1]["valid_end"], "2026-11-02T00:00:00+09:00")
        self.assertEqual(rows[5]["operational_night"], "2026-10-31")
        self.assertEqual(rows[6]["operational_night"], "2026-11-01")

    def test_quality_symbols_remain_unknown_and_raw_text_is_preserved(self):
        for token in ["1.5 )", "1.5 ]", "1.5 #", "///", " ", "--", "×", "NaN", "inf"]:
            with self.subTest(token=token):
                raw = table(change=lambda h, cells: cells[:1] + [token] + cells[2:] if h == 1 else cells)
                item = self.normalize(raw)["observations"][0]["values"]["precipitation_mm"]
                self.assertIsNone(item["value"])
                self.assertEqual(item["kind"], "UNKNOWN")
                self.assertEqual(item["raw_value"], token)

    def test_unknown_cell_class_cannot_certify_a_numeric_value(self):
        raw = table().replace(b'class="data_0_0">1.5', b'class="unrecognized_quality">1.5', 1)
        item = self.normalize(raw)["observations"][0]["values"]["precipitation_mm"]
        self.assertEqual(item["kind"], "UNKNOWN")
        self.assertIsNone(item["value"])

    def test_negative_precipitation_out_of_range_humidity_and_speed_are_unknown(self):
        for column, value, name in [(1, "-1", "precipitation_mm"), (5, "101", "relative_humidity_pct"),
                                    (6, "-2", "wind_speed_mps")]:
            with self.subTest(name=name):
                def change(hour, cells):
                    if hour == 1:
                        cells[column] = value
                    return cells
                item = self.normalize(table(change=change))["observations"][0]["values"][name]
                self.assertIsNone(item["value"])
                self.assertEqual(item["kind"], "UNKNOWN")

    def test_bad_column_count_duplicate_or_missing_hour_are_rejected(self):
        cases = [lambda h, c: c[:-1] if h == 1 else c,
                 lambda h, c: ["1"] + c[1:] if h == 2 else c,
                 lambda h, c: None if h == 2 else c,
                 lambda h, c: ["0"] + c[1:] if h == 1 else c]
        for change in cases:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    self.normalize(table(change=change))

    def test_wrong_units_or_swapped_headers_are_rejected(self):
        for old, new in [("降水量(mm)", "降水量(cm)"), ("風速(m/s)", "風速(km/h)"),
                         ("相対湿度(％)", "気温(℃)")]:
            with self.subTest(new=new):
                with self.assertRaises(ValueError):
                    self.normalize(table().replace(old.encode(), new.encode()))

    def test_missing_or_duplicated_target_table_is_rejected(self):
        for raw in [table().replace(b'tablefix1', b'other'), table() + table()]:
            with self.subTest(raw_size=len(raw)):
                with self.assertRaises(ValueError):
                    self.normalize(raw)

    def test_truncated_or_nested_data_cells_are_rejected(self):
        for raw in [table()[:-25], table().replace(b">1.5</td>", b"><td>1.5</td></td>", 1)]:
            with self.subTest(raw_size=len(raw)):
                with self.assertRaises(ValueError):
                    self.normalize(raw)

    def test_raw_sha_size_and_byte_limit_are_enforced(self):
        for changes in [{"sha256": "0" * 64}, {"sha256": "z" * 64}, {"size_bytes": 1},
                        {"size_bytes": True}]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.normalize(**changes)
        with self.assertRaises(ValueError):
            self.normalize(b"x" * (2 * 1024 * 1024 + 1))

    def test_unapproved_station_source_url_or_day_are_rejected(self):
        for changes in [{"provider": "Other"}, {"station_id": "12345"},
                        {"source_type": "EX_ANTE_FORECAST"}, {"requested_url": "https://example.com/"},
                        {"resolved_url": receipt(table())["resolved_url"].replace("0980", "1111")}]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.normalize(**changes)
        with self.assertRaises(ValueError):
            self.module.normalize_jma_hourly(table(), day="2026-02-30", receipt=receipt(table()))

    def test_naive_or_backdated_readiness_cannot_make_source_usable(self):
        for name in ["retrieved_at", "source_received_at", "derived_at", "materialized_at", "audited_at"]:
            for instant in ["2026-11-03T10:00:00", "2026-11-01T10:00:00+09:00"]:
                if name == "retrieved_at" and "+09" in instant:
                    continue
                with self.subTest(name=name, instant=instant):
                    with self.assertRaises(ValueError):
                        self.normalize(**{name: instant})
        self.assertEqual(self.normalize()["usable_at"], "2026-11-03T10:00:04+09:00")

    def test_utc_receipts_and_input_ownership(self):
        raw = table()
        original = receipt(raw)
        original["audited_at"] = "2026-11-03T01:00:05Z"
        saved = copy.deepcopy(original)
        result = self.module.normalize_jma_hourly(raw, day="2026-11-01", receipt=original)
        self.assertEqual(result["usable_at"], "2026-11-03T10:00:05+09:00")
        result["source"]["provider"] = "mutated"
        self.assertEqual(original, saved)

    def test_hand_calculated_rain_sums_and_input_order_independence(self):
        result = self.module.antecedent_rainfall(rainfall_rows(), window_start="2026-11-02T00:00:00+09:00")
        self.assertEqual([result[str(h)]["value_mm"] for h in (24, 48, 72)], [24.0, 72.0, 144.0])
        self.assertTrue(all(result[str(h)]["status"] == "COMPLETE" for h in (24, 48, 72)))
        self.assertEqual(result["72"]["coverage_hours"], 72.0)

    def test_missing_old_hour_does_not_destroy_complete_recent_24h(self):
        rows = rainfall_rows()
        rows.pop()
        result = self.module.antecedent_rainfall(rows, window_start="2026-11-02T00:00:00+09:00")
        self.assertEqual(result["24"]["value_mm"], 24.0)
        self.assertEqual(result["48"]["value_mm"], 72.0)
        self.assertIsNone(result["72"]["value_mm"])
        self.assertIn("INCOMPLETE_COVERAGE", result["72"]["reasons"])
        self.assertEqual(result["72"]["coverage_hours"], 71.0)

    def test_unknown_or_nonfinite_rain_never_becomes_zero(self):
        for key, value in [("kind", "UNKNOWN"), ("value", None), ("value", float("nan")),
                           ("value", float("inf")), ("value", -1), ("unit", "cm")]:
            rows = rainfall_rows()
            rows[0]["values"]["precipitation_mm"][key] = value
            with self.subTest(key=key, value=value):
                result = self.module.antecedent_rainfall(rows, window_start="2026-11-02T00:00:00+09:00")
                self.assertIsNone(result["24"]["value_mm"])
                self.assertEqual(result["24"]["status"], "UNKNOWN")

    def test_duplicate_and_overlapping_intervals_block_the_affected_sum(self):
        for mutate in [lambda r: r.append(copy.deepcopy(r[0])),
                       lambda r: r[0].update(valid_start="2026-11-01T22:30:00+09:00")]:
            rows = rainfall_rows()
            mutate(rows)
            result = self.module.antecedent_rainfall(rows, window_start="2026-11-02T00:00:00+09:00")
            self.assertIsNone(result["24"]["value_mm"])
            self.assertTrue(result["24"]["reasons"])

    def test_current_hour_or_later_rain_is_not_antecedent(self):
        rows = rainfall_rows()
        later = copy.deepcopy(rows[0])
        later.update(valid_start="2026-11-02T00:00:00+09:00", valid_end="2026-11-02T01:00:00+09:00")
        later["values"]["precipitation_mm"]["value"] = 999.0
        rows.append(later)
        result = self.module.antecedent_rainfall(rows, window_start="2026-11-01T15:00:00Z")
        self.assertEqual(result["24"]["value_mm"], 24.0)

    def test_partial_hour_window_and_naive_or_unbounded_requests_rejected(self):
        for instant, horizons in [("2026-11-02T00:00:00", (24,)),
                                  ("2026-11-02T00:00:00+09:00", (0,)),
                                  ("2026-11-02T00:00:00+09:00", (True,)),
                                  ("2026-11-02T00:00:00+09:00", ([],)),
                                  ("2026-11-02T00:00:00+09:00", (24, 24)),
                                  ("2026-11-02T00:00:00+09:00", (999999,))]:
            with self.subTest(instant=instant, horizons=horizons):
                with self.assertRaises(ValueError):
                    self.module.antecedent_rainfall(rainfall_rows(), window_start=instant, horizons=horizons)
        result = self.module.antecedent_rainfall(rainfall_rows(), window_start="2026-11-02T00:10:00+09:00")
        self.assertIsNone(result["24"]["value_mm"])

    def test_rain_does_not_accept_wrong_temporal_or_reference_support(self):
        for change in [lambda row: row.update(support_kind="RECONSTRUCTED_ROAD_ESTIMATE"),
                       lambda row: row["values"]["precipitation_mm"].update(quality="QUASI_NORMAL"),
                       lambda row: row["values"]["precipitation_mm"].update(temporal_support="POINT_OBSERVATION"),
                       lambda row: row["values"]["precipitation_mm"].update(valid_start="2026-11-01T22:00:00+09:00")]:
            rows = rainfall_rows()
            change(rows[0])
            result = self.module.antecedent_rainfall(rows, window_start="2026-11-02T00:00:00+09:00")
            self.assertIsNone(result["24"]["value_mm"])

    def test_distinct_station_series_are_not_pooled_as_one_rain_history(self):
        rows = rainfall_rows()
        rows[0]["station_id"], rows[1]["station_id"] = "88901", "another-station"
        with self.assertRaises(ValueError):
            self.module.antecedent_rainfall(rows, window_start="2026-11-02T00:00:00+09:00")

    def test_normalized_zero_rain_with_complete_hour_coverage_is_a_real_zero(self):
        raw = table(change=lambda h, cells: cells[:1] + ["0.0"] + cells[2:])
        observations = self.normalize(raw)["observations"]
        result = self.module.antecedent_rainfall(observations, window_start="2026-11-02T00:00:00+09:00", horizons=(24,))
        self.assertEqual(result["24"]["value_mm"], 0.0)
        self.assertEqual(result["24"]["status"], "COMPLETE")


if __name__ == "__main__":
    unittest.main()
