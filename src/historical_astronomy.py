"""Normalize official NAOJ noon calculations at one public municipal reference.

No local astronomy engine, observations, interpolation, files, network, labels
or model authority. Lunar age is not an illumination fraction or road moonlight.
Source-cell columns are zero-based; data-row numbers start at one after headers.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, time, timedelta
import hashlib
from html.parser import HTMLParser
import math
import re
from urllib.parse import parse_qsl, urlsplit

from historical_environment import JST, MAX_BYTES, READINESS, RECEIPT_FIELDS, _aware

PROVIDER = "NAOJ"
SOURCE_TYPE = "ASTRONOMICAL_CALCULATION_RETRIEVED_RETROSPECTIVELY"
LICENCE_URL = "https://eco.mtk.nao.ac.jp/koyomi/site/"
DEFINITION_URL = "https://www.nao.ac.jp/faq/a0204.html"
REFERENCE_SOURCE_URL = "https://eco.mtk.nao.ac.jp/cgi-bin/koyomi/koyomix.cgi?choice=3&choice0=3&city_go46525=1"
REFERENCE_KEY = "大島郡瀬戸内町(鹿児島県)"
LATITUDE = "28.1463888888889"
LONGITUDE = "129.314722222222"


def _date(value):
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Exact ISO source calendar date required")
    return date.fromisoformat(value)


def _query(value, first, length):
    if type(value) is not str or len(value) > 4096:
        raise ValueError("Bounded official calculation URL required")
    url = urlsplit(value)
    if (url.scheme != "https" or url.netloc != "eco.mtk.nao.ac.jp" or url.fragment or
            url.path != "/cgi-bin/koyomi/koyomix.cgi"):
        raise ValueError("Official NAOJ numeric calculation endpoint required")
    pairs = parse_qsl(url.query, keep_blank_values=True, encoding="euc-jp", errors="strict")
    query = dict(pairs)
    expected = dict(year=str(first.year), month=str(first.month), day=str(first.day), hour="12", min="0",
        choice="1", choice0="1", key=REFERENCE_KEY, lat=LATITUDE, lon=LONGITUDE, hgt="0", lst="9",
        div="1", divu="3", len=str(length), lenu="3", nomenu="1", btn04="Go")
    if query.get("phase") == "1":
        query.pop("phase")  # Optional diagram does not change the numeric table.
    if len(pairs) != len(dict(pairs)) or query != expected:
        raise ValueError("Calculation query station, dates, noon or interval mismatch")


def _provenance(raw, receipt, first, last, length):
    if type(receipt) is not dict or set(receipt) != RECEIPT_FIELDS:
        raise ValueError("Complete common source receipt required")
    for name, expected in (("provider", PROVIDER), ("station_id", "46525"),
            ("station_name", "大島郡瀬戸内町役場"), ("source_type", SOURCE_TYPE), ("licence_url", LICENCE_URL)):
        if receipt[name] != expected:
            raise ValueError("Official municipal calculation source binding mismatch")
    if (type(receipt["size_bytes"]) is not int or receipt["size_bytes"] != len(raw) or
            type(receipt["sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"]) or
            hashlib.sha256(raw).hexdigest() != receipt["sha256"]):
        raise ValueError("Raw calculation size or SHA-256 mismatch")
    for field in ("requested_url", "resolved_url"):
        _query(receipt[field], first, length)
    retrieved = _aware(receipt["retrieved_at"])
    ready = [_aware(receipt[name]) for name in READINESS]
    if (ready[0] < retrieved or any(t < ready[0] for t in ready[1:]) or
            ready[2] < ready[1] or ready[3] < ready[1]):
        raise ValueError("Calculation readiness cannot precede source or derivation")
    if retrieved < datetime.combine(last, time(12), JST):
        raise ValueError("Retrospective receipt cannot predate the requested last noon")
    return max(retrieved, *ready).isoformat()


class _MoonTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.tables = self.tags = 0
        self.rows, self.row, self.cell = [], None, None
        self.titles, self.title, self.outside = [], None, []

    def handle_starttag(self, tag, attrs):
        self.tags += 1
        if self.tags > 50_000:
            raise ValueError("Calculation HTML tag bound exceeded")
        a = dict(attrs)
        if len(a) != len(attrs):
            raise ValueError("Duplicate calculation HTML attributes")
        if ("hidden" in a or a.get("aria-hidden", "").casefold() == "true" or
                re.search(r"display\s*:\s*none|visibility\s*:\s*hidden", a.get("style", ""), re.I)):
            raise ValueError("Hidden calculation markup cannot establish source identity")
        if tag == "h3":
            if self.title is not None:
                raise ValueError("Nested calculation heading")
            self.title = ""
        if tag == "table":
            if self.inside:
                raise ValueError("Nested calculation table")
            if "result" in a.get("class", "").split():
                self.tables += 1
                if self.tables != 1:
                    raise ValueError("Duplicate numeric calculation table")
                self.inside = True
            return
        if not self.inside:
            return
        if tag == "tr":
            if self.row is not None:
                raise ValueError("Unclosed calculation row")
            self.row = []
        elif tag in {"th", "td"}:
            if self.row is None or self.cell is not None or a.get("colspan", "1") != "1" or a.get("rowspan", "1") != "1":
                raise ValueError("Malformed numeric calculation cell")
            self.cell = {"tag": tag, "text": ""}
        elif self.cell is not None:
            raise ValueError("Markup inside numeric calculation cell unsupported")

    def handle_endtag(self, tag):
        if tag == "h3":
            if self.title is None:
                raise ValueError("Unmatched calculation heading")
            self.titles.append(self.title.strip())
            self.title = None
            if len(self.titles) > 20:
                raise ValueError("Calculation heading bound exceeded")
        if not self.inside:
            return
        if tag in {"td", "th"}:
            if self.cell is None or self.cell["tag"] != tag:
                raise ValueError("Unmatched numeric cell")
            self.row.append(self.cell)
            self.cell = None
            if len(self.row) > 7:
                raise ValueError("Extra numeric calculation columns")
        elif tag == "tr":
            if self.row is None or self.cell is not None:
                raise ValueError("Unclosed numeric cell")
            self.rows.append(self.row)
            self.row = None
            if len(self.rows) > 32:
                raise ValueError("Monthly calculation row bound exceeded")
        elif tag == "table":
            if self.row is not None or self.cell is not None:
                raise ValueError("Incomplete calculation table")
            self.inside = False

    def handle_data(self, text):
        if self.title is not None:
            self.title += text
            if len(self.title) > 1024:
                raise ValueError("Calculation heading text bound exceeded")
        if not self.inside:
            self.outside.append(text)
        if self.inside and self.cell is not None:
            self.cell["text"] += text
            if len(self.cell["text"]) > 1024:
                raise ValueError("Calculation cell text bound exceeded")


def normalize_naoj_moon_age(raw_bytes, period_start, period_end, receipt):
    """Return exact noon point values for an inclusive same-month source period."""
    if type(raw_bytes) is not bytes or not 0 < len(raw_bytes) <= MAX_BYTES:
        raise ValueError("Bounded nonempty calculation source bytes required")
    first, last = _date(period_start), _date(period_end)
    length = (last - first).days + 1
    if first > last or (first.year, first.month) != (last.year, last.month) or not 1 <= length <= 31:
        raise ValueError("Bounded inclusive same-calendar-month period required")
    usable_at = _provenance(raw_bytes, receipt, first, last, length)
    parser = _MoonTable()
    try:
        parser.feed(raw_bytes.decode("euc-jp"))
        parser.close()
    except UnicodeDecodeError as exc:
        raise ValueError("Expected original EUC-JP calculation bytes") from exc
    if (parser.tables != 1 or parser.inside or parser.row is not None or parser.cell is not None or
            parser.title is not None or parser.titles.count("月の高度・方位") != 1):
        raise ValueError("One complete official lunar numeric result required")
    compact = re.sub(r"\s+", "", "".join(parser.outside))
    locations = re.findall(r"緯度:[^°]+°経度:[^°]+°標高:[^m]+m標準時:UT[+-][0-9.]+h", compact)
    if locations != ["緯度:28.1464°経度:129.3147°標高:0.0m標準時:UT+9h"]:
        raise ValueError("Calculation body reference location or standard time mismatch")
    headers = ["年月日", "時刻", "高度[°]", "方位[°]", "視半径[″]", "月齢", "天体"]
    if (len(parser.rows) != length + 1 or
            [cell["text"].strip() for cell in parser.rows[0]] != headers or
            any(cell["tag"] != "th" for cell in parser.rows[0])):
        raise ValueError("Calculation columns, units or period coverage mismatch")
    observations = []
    for index, cells in enumerate(parser.rows[1:]):
        if len(cells) != 7 or any(cell["tag"] != "td" for cell in cells):
            raise ValueError("Seven lunar numeric data columns required")
        values = [cell["text"].strip() for cell in cells]
        expected_day = first + timedelta(days=index)
        if values[0] != expected_day.strftime("%Y/%m/%d") or values[1] != "12:00:00" or values[6] != "月":
            raise ValueError("Calculation body day, noon, chronology or celestial object mismatch")
        raw_value = cells[5]["text"]
        numeric = float(values[5]) if re.fullmatch(r"[0-9]{1,2}\.[0-9]", values[5]) else None
        if numeric is not None and (not math.isfinite(numeric) or not 0 <= numeric < 31):
            numeric = None
        instant = datetime.combine(expected_day, time(12), JST).isoformat()
        observations.append({"valid_start": instant, "valid_end": instant,
            "support_kind": "NOON_REFERENCE_LOCATION_CALCULATION", "source_sha256": receipt["sha256"],
            "values": {"moon_age_days": {"value": numeric, "unit": "day",
                "kind": "ASTRONOMICAL_CALCULATION" if numeric is not None else "UNKNOWN",
                "quality": "NORMAL_NUMERIC" if numeric is not None else "UNKNOWN_OR_UNSUPPORTED_SOURCE_VALUE",
                "raw_value": raw_value, "source_cell": {"data_row": index + 1, "column": 5},
                "temporal_support": "POINT_CALCULATION", "decimal_resolution_days": 0.1}}})
    return {"schema_version": "historical-environment-source-v1", "source": copy.deepcopy(receipt),
        "observations": observations, "usable_at": usable_at, "source_encoding": "EUC-JP",
        "reference_location_source_url": REFERENCE_SOURCE_URL, "moon_age_definition_url": DEFINITION_URL,
        "geographic_support": "REFERENCE_LOCATION_CALCULATION_ONLY", "historical_ex_ante_proven": False,
        "training_eligibility": "NOT_ASSESSED", "illumination_fraction_status": "NOT_PRODUCED",
        "road_surface_moonlight_status": "NOT_PRODUCED"}
