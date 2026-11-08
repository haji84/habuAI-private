"""Pure historical JMA source normalization, never forecast or label authority.

The fixed Koniya reference station is not road-level microclimate. Caller-supplied
receipts are checked for consistency with bytes, not independently authenticated.
No network, files, training selector, model or production issuer is accessed.
Cell columns are zero-based, including the hour at column zero. Operational
night labels describe the nominal hour-end reference instant; each variable's
explicit temporal support controls its actual use across the 07:00 boundary.
"""
from __future__ import annotations

import copy
import hashlib
import math
import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlsplit

JST = timezone(timedelta(hours=9))
MAX_BYTES = 2 * 1024 * 1024
MAX_OBSERVATIONS = 24 * 366 * 3
READINESS = ("source_received_at", "derived_at", "materialized_at", "audited_at")
RECEIPT_FIELDS = {"provider", "station_id", "station_name", "source_type", "requested_url",
                  "resolved_url", "retrieved_at", "size_bytes", "sha256", "licence_url", *READINESS}
DIRECTIONS = ("北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
              "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西")
NUMBER = re.compile(r"[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")


def _aware(value):
    if type(value) is not str:
        raise ValueError("Aware ISO timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Aware ISO timestamp required")
    return result.astimezone(JST)


def _source_url(value, day):
    if type(value) is not str or len(value) > 2048:
        raise ValueError("Bounded JMA source URL required")
    url = urlsplit(value)
    if (url.scheme != "https" or url.netloc != "www.data.jma.go.jp" or url.fragment or
            url.path != "/stats/etrn/view/hourly_a1.php"):
        raise ValueError("Expected fixed JMA hourly archive source")
    pairs = parse_qsl(url.query, keep_blank_values=True)
    query = dict(pairs)
    if len(query) != len(pairs) or set(query) - {"prec_no", "block_no", "year", "month", "day", "view"}:
        raise ValueError("Ambiguous JMA source query")
    if query.get("prec_no") != "88" or query.get("block_no") != "0980":
        raise ValueError("Expected Koniya JMA source identifiers")
    for field, expected in (("year", day.year), ("month", day.month), ("day", day.day)):
        text = query.get(field, "")
        if not re.fullmatch(r"[0-9]{1,4}", text) or int(text) != expected:
            raise ValueError("Source URL day does not match requested day")


def _receipt(raw, value, day):
    if type(value) is not dict or set(value) != RECEIPT_FIELDS:
        raise ValueError("Complete explicit historical source receipt required")
    if any(value[key] != expected for key, expected in (
            ("provider", "JMA"), ("station_id", "88901"), ("station_name", "古仁屋"),
            ("source_type", "STATION_OBSERVATION"))):
        raise ValueError("Unsupported station or historical source type")
    if (type(value["size_bytes"]) is not int or value["size_bytes"] != len(raw) or
            type(value["sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) or
            hashlib.sha256(raw).hexdigest() != value["sha256"]):
        raise ValueError("Source raw-byte size or SHA-256 mismatch")
    for key in ("requested_url", "resolved_url"):
        _source_url(value[key], day)
    licence = value["licence_url"]
    if type(licence) is not str or len(licence) > 2048:
        raise ValueError("Explicit JMA licence URL required")
    parsed = urlsplit(licence)
    if parsed.scheme != "https" or parsed.netloc not in {"www.jma.go.jp", "www.data.jma.go.jp"}:
        raise ValueError("Explicit JMA licence URL required")
    retrieved = _aware(value["retrieved_at"])
    ready = [_aware(value[key]) for key in READINESS]
    if ready[0] < retrieved or any(t < ready[0] for t in ready[1:]):
        raise ValueError("Readiness cannot precede actual source receipt")
    if ready[2] < ready[1] or ready[3] < ready[1]:
        raise ValueError("Materialization/audit cannot precede derivation")
    if retrieved < datetime.combine(day + timedelta(days=1), time(), JST):
        raise ValueError("Complete historical day cannot be retrieved before its final observation")
    return max(retrieved, *ready).isoformat()


class _Table(HTMLParser):
    """Capture only one bounded, fully closed provider table and its cell text."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.count = self.tags = 0
        self.rows, self.row, self.cell = [], None, None
        self.headings, self.heading = [], None
        self.heading_before_table = False

    def handle_starttag(self, tag, attrs):
        self.tags += 1
        if self.tags > 50_000:
            raise ValueError("Historical HTML tag capacity exceeded")
        attributes = dict(attrs)
        if tag == "h3":
            if self.heading is not None or self.inside:
                raise ValueError("Malformed historical source heading")
            self.heading = ""
        if tag == "table":
            if self.inside:
                raise ValueError("Nested source table unsupported")
            if attributes.get("id") == "tablefix1":
                self.count += 1
                if self.count != 1:
                    raise ValueError("Duplicate source table")
                self.heading_before_table = len(self.headings) == 1 and self.heading is None
                self.inside = True
            return
        if not self.inside:
            return
        if tag == "tr":
            if self.row is not None:
                # The provider legally omits </tr> on its completed TH rows.
                # Never repair an open cell or an incomplete data row.
                if self.cell is not None or not self.row or any(c["tag"] != "th" for c in self.row):
                    raise ValueError("Unclosed table row")
                self.rows.append(self.row)
                if len(self.rows) > 2:
                    raise ValueError("Excess historical source headers")
            self.row = []
        elif tag in {"td", "th"}:
            if self.row is None or self.cell is not None or len(attrs) != len(attributes):
                raise ValueError("Malformed table cell")
            self.cell = {"tag": tag, "text": "", "class": attributes.get("class", ""),
                         "rowspan": attributes.get("rowspan", "1"),
                         "colspan": attributes.get("colspan", "1"), "markup": False}
        elif self.cell is not None:
            if tag == "br":
                self.cell["text"] += "\n"
            elif self.cell["tag"] == "td":
                self.cell["markup"] = True

    def handle_endtag(self, tag):
        if tag == "h3":
            if self.heading is None:
                raise ValueError("Malformed historical source heading")
            self.headings.append(self.heading)
            self.heading = None
            if len(self.headings) > 1:
                raise ValueError("Ambiguous historical source heading")
        if not self.inside:
            return
        if tag in {"td", "th"}:
            if self.cell is None or self.cell["tag"] != tag:
                raise ValueError("Mismatched table cell")
            self.row.append(self.cell)
            self.cell = None
            if len(self.row) > 11:
                raise ValueError("Excess historical source columns")
        elif tag == "tr":
            if self.row is None or self.cell is not None:
                raise ValueError("Malformed table row")
            self.rows.append(self.row)
            self.row = None
            if len(self.rows) > 26:
                raise ValueError("Excess historical source rows")
        elif tag == "table":
            if self.row is not None or self.cell is not None:
                raise ValueError("Unclosed source table cells")
            self.inside = False

    def handle_data(self, data):
        if self.heading is not None:
            self.heading += data
            if len(self.heading) > 1024:
                raise ValueError("Historical source heading capacity exceeded")
        if self.inside and self.cell is not None:
            self.cell["text"] += data
            if len(self.cell["text"]) > 1024:
                raise ValueError("Historical cell text capacity exceeded")


def _heading(value):
    return re.sub(r"\s+", "", value).replace("（", "(").replace("）", ")").replace("％", "%")


def _source_heading(parser, day):
    """Check the body's own identity independently of caller-supplied URLs."""
    if parser.heading is not None or len(parser.headings) != 1 or not parser.heading_before_table:
        raise ValueError("Exactly one completed historical source heading before the table required")
    title = re.sub(r"\s+", "", unicodedata.normalize("NFKC", parser.headings[0]))
    match = re.fullmatch(r"古仁屋\(鹿児島県\)([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日\(1時間ごとの値\)", title)
    if match is None or tuple(map(int, match.groups())) != (day.year, day.month, day.day):
        raise ValueError("Historical source heading station, calendar date or hourly view mismatch")


def _layout(rows):
    headers, data = [], []
    for row in rows:
        if row and all(c["tag"] == "th" for c in row) and not data:
            headers.append(row)
        else:
            data.append(row)
    if len(headers) not in (1, 2) or len(data) != 24:
        raise ValueError("Expected declared headers and exactly 24 historical hours")
    grid = [[None] * 11 for _ in headers]
    for r, row in enumerate(headers):
        col = 0
        for cell in row:
            while col < 11 and grid[r][col] is not None:
                col += 1
            if not cell["rowspan"].isdigit() or not cell["colspan"].isdigit():
                raise ValueError("Invalid source header span")
            height, width = int(cell["rowspan"]), int(cell["colspan"])
            if not 1 <= height <= len(headers) - r or not 1 <= width <= 11 - col:
                raise ValueError("Unsupported source header span")
            for y in range(r, r + height):
                for x in range(col, col + width):
                    if grid[y][x] is not None:
                        raise ValueError("Overlapping source header spans")
                    grid[y][x] = _heading(cell["text"])
            col += width
    expected = ({"時"}, {"降水量(mm)"}, {"気温(℃)"}, {"露点温度(℃)"}, {"蒸気圧(hPa)"},
                {"湿度(%)", "相対湿度(%)"}, {"平均風速(m/s)", "風速(m/s)"}, {"風向"},
                {"日照時間(h)"}, {"降雪(cm)", "降雪量(cm)"}, {"積雪(cm)"})
    if any(text not in allowed for text, allowed in zip(grid[-1], expected)):
        raise ValueError("Historical source column names or units changed")
    for row in data:
        if (len(row) != 11 or any(c["tag"] != "td" or c["rowspan"] != "1" or c["colspan"] != "1" for c in row)):
            raise ValueError("Expected 11 unmerged historical data cells")
    return data


def _value(cell, hour, column, unit, start, end, support, *, bounds=None, direction=False):
    raw, text = cell["text"], cell["text"].strip()
    quality = "NORMAL"
    if cell["class"] != "data_0_0":
        quality = "UNKNOWN_CLASS"
    elif cell["markup"]:
        quality = "UNSUPPORTED_MARKUP"
    elif any(mark in text for mark in (")", "]", "#")):
        quality = "QUASI_NORMAL" if ")" in text else "INSUFFICIENT" if "]" in text else "SUSPECT"
    elif text in {"", "///", "--", "×"}:
        quality = "MISSING_OR_UNSUPPORTED_SYMBOL"
    value = None
    if quality == "NORMAL":
        if direction:
            if text in DIRECTIONS or text == "静穏":
                value = text
            else:
                quality = "UNKNOWN_DIRECTION"
        elif NUMBER.fullmatch(text):
            numeric = float(text)
            if math.isfinite(numeric) and bounds[0] <= numeric <= bounds[1]:
                value = numeric
            else:
                quality = "OUT_OF_RANGE"
        else:
            quality = "INVALID_NUMBER"
    return {"value": value, "unit": unit, "kind": "OBSERVED" if value is not None else "UNKNOWN",
            "quality": quality, "raw_value": raw,
            "source_cell": {"hour": hour, "column": column, "td_class": cell["class"]},
            "valid_start": start.isoformat(), "valid_end": end.isoformat(), "temporal_support": support}


def normalize_jma_hourly(raw_bytes, *, day: str, receipt: dict) -> dict:
    """Bind one fixed Koniya archive day; preserve unknown quality without filling."""
    if type(raw_bytes) is not bytes or not 0 < len(raw_bytes) <= MAX_BYTES:
        raise ValueError("Bounded nonempty raw source bytes required")
    if type(day) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day):
        raise ValueError("ISO calendar source day required")
    calendar_day = date.fromisoformat(day)
    usable = _receipt(raw_bytes, receipt, calendar_day)
    parser = _Table()
    try:
        parser.feed(raw_bytes.decode("utf-8-sig"))
        parser.close()
    except UnicodeDecodeError as exc:
        raise ValueError("Unsupported source text encoding") from exc
    _source_heading(parser, calendar_day)
    if parser.count != 1 or parser.inside or parser.cell is not None or parser.row is not None:
        raise ValueError("One complete historical source table required")
    rows, seen, observations = _layout(parser.rows), set(), []
    for cells in rows:
        text = cells[0]["text"].strip()
        if not re.fullmatch(r"[0-9]{1,2}", text):
            raise ValueError("Invalid historical hour")
        hour = int(text)
        if hour not in range(1, 25) or hour in seen:
            raise ValueError("Duplicate or out-of-range historical hour")
        seen.add(hour)
        end = datetime.combine(calendar_day, time(), JST) + timedelta(hours=hour)
        start = end - timedelta(hours=1)
        specs = (("precipitation_mm", 1, "mm", start, "PRECEDING_HOUR_ACCUMULATION", (0, 10_000)),
                 ("temperature_c", 2, "degC", end, "POINT_OBSERVATION", (-100, 70)),
                 ("relative_humidity_pct", 5, "%", end, "POINT_OBSERVATION", (0, 100)),
                 ("wind_speed_mps", 6, "m/s", end - timedelta(minutes=10), "PRECEDING_TEN_MINUTE_MEAN", (0, 150)))
        values = {name: _value(cells[col], hour, col, unit, begin, end, support, bounds=bounds)
                  for name, col, unit, begin, support, bounds in specs}
        wind = _value(cells[7], hour, 7, "16_point_compass", end - timedelta(minutes=10), end,
                      "PRECEDING_TEN_MINUTE_DIRECTION", direction=True)
        values["wind_direction_16pt"] = wind
        derived = copy.deepcopy(wind)
        category = wind["value"]
        derived.update(unit="degree", value=DIRECTIONS.index(category) * 22.5 if category in DIRECTIONS else None,
                       kind="DERIVED_FROM_OBSERVATION" if category in DIRECTIONS else "UNKNOWN",
                       angular_bin_half_width_deg=11.25, wind_from_semantics=True)
        values["wind_direction_deg"] = derived
        observations.append({"valid_start": start.isoformat(), "valid_end": end.isoformat(),
            "support_kind": "HOURLY_REFERENCE_STATION", "values": values,
            "operational_night": (end - timedelta(hours=7)).date().isoformat(),
            "station_id": "88901", "source_sha256": receipt["sha256"]})
    observations.sort(key=lambda row: row["valid_end"])
    return {"schema_version": "historical-environment-source-v1", "source": copy.deepcopy(receipt),
            "observations": observations, "usable_at": usable,
            "geographic_support": "REFERENCE_STATION_ONLY", "historical_ex_ante_proven": False,
            "training_eligibility": "NOT_ASSESSED"}


def antecedent_rainfall(observations: list, *, window_start: str, horizons=(24, 48, 72)) -> dict:
    """Sum only complete, known, unique hour accumulations in [t-h, t)."""
    end = _aware(window_start)
    if (type(observations) is not list or len(observations) > MAX_OBSERVATIONS or
            type(horizons) is not tuple or not 1 <= len(horizons) <= 3 or
            any(type(h) is not int or not 1 <= h <= 72 for h in horizons) or len(set(horizons)) != len(horizons)):
        raise ValueError("Bounded observations and unique 1..72 hour horizons required")
    parsed = []
    stations = set()
    for row in observations:
        if type(row) is not dict:
            raise ValueError("Historical observation object required")
        start, finish = _aware(row.get("valid_start")), _aware(row.get("valid_end"))
        if start >= finish:
            raise ValueError("Positive historical accumulation interval required")
        if row.get("station_id") is not None:
            stations.add(row["station_id"])
        parsed.append((start, finish, row))
    if len(stations) > 1:
        raise ValueError("Reference station rain series cannot be mixed")
    result = {}
    for hours in horizons:
        beginning = end - timedelta(hours=hours)
        relevant = sorted((item for item in parsed if item[0] < end and item[1] > beginning),
                          key=lambda item: (item[0], item[1]))
        cursor, seconds, amounts, reasons = beginning, 0.0, [], set()
        for start, finish, row in relevant:
            if (finish - start != timedelta(hours=1) or start < beginning or finish > end or
                    start.minute or start.second or start.microsecond):
                reasons.add("UNSUPPORTED_OR_PARTIAL_INTERVAL")
                continue
            if start < cursor:
                reasons.add("DUPLICATE_OR_OVERLAPPING_INTERVAL")
                continue
            if start > cursor:
                reasons.add("INCOMPLETE_COVERAGE")
            cursor = finish
            values = row.get("values")
            rain = values.get("precipitation_mm") if type(values) is dict else None
            if (row.get("support_kind") != "HOURLY_REFERENCE_STATION" or type(rain) is not dict or
                    rain.get("kind") != "OBSERVED" or rain.get("unit") != "mm" or
                    type(rain.get("value")) not in (float, int) or not math.isfinite(rain["value"]) or rain["value"] < 0 or
                    rain.get("quality") != "NORMAL" or
                    rain.get("temporal_support", "PRECEDING_HOUR_ACCUMULATION") != "PRECEDING_HOUR_ACCUMULATION"):
                reasons.add("UNKNOWN_OR_INVALID_PRECIPITATION")
                continue
            if (("valid_start" in rain and _aware(rain["valid_start"]) != start) or
                    ("valid_end" in rain and _aware(rain["valid_end"]) != finish)):
                reasons.add("PRECIPITATION_SUPPORT_MISMATCH")
                continue
            seconds += (finish - start).total_seconds()
            amounts.append(float(rain["value"]))
        if cursor != end or seconds != hours * 3600:
            reasons.add("INCOMPLETE_COVERAGE")
        total = None
        if not reasons:
            try:
                total = math.fsum(amounts)
            except OverflowError:
                reasons.add("NONFINITE_ACCUMULATION")
            if total is not None and not math.isfinite(total):
                total = None
                reasons.add("NONFINITE_ACCUMULATION")
        result[str(hours)] = {"value_mm": total, "coverage_hours": seconds / 3600,
            "expected_hours": hours, "coverage_fraction": seconds / (hours * 3600),
            "status": "UNKNOWN" if reasons else "COMPLETE", "reasons": sorted(reasons),
            "valid_start": beginning.isoformat(), "valid_end": end.isoformat()}
    return result
