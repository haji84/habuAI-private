#!/usr/bin/env python3
"""Public-reference weather collection; NEVER reads capture logs or GPX.

Station: Koniya JMA 88901 (official hourly observations).
Weather grid: approximate publicly known Koniya reference (28.15, 129.32).
Open-Meteo historical forecast archive is a post-hoc model reference, NOT an
independent observation and NOT evidence of a forecast known at P0 cutoff.
"""
import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

JST = dt.timezone(dt.timedelta(hours=9))
JMA = "https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php"
OM = "https://historical-forecast-api.open-meteo.com/v1/forecast"
VARS = ("temperature_2m", "relative_humidity_2m", "precipitation",
        "rain", "wind_speed_10m", "wind_direction_10m")


def days(start, end):
    a = dt.date.fromisoformat(start)
    b = dt.date.fromisoformat(end)
    if a > b or (b - a).days > 45:
        raise ValueError("INVALID_DATE_RANGE")
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]


def get(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "HabuAI-noncommercial-public-weather-audit/1.0"})
    with urllib.request.urlopen(request, timeout=12) as response:
        resolved = response.geturl()
        host = urllib.parse.urlsplit(resolved).hostname
        if response.status != 200 or host not in (
            "www.data.jma.go.jp", "historical-forecast-api.open-meteo.com"):
            raise ValueError("UNEXPECTED_HTTP_SOURCE")
        raw = response.read(2_000_001)
    if not 0 < len(raw) <= 2_000_000:
        raise ValueError("SOURCE_SIZE_INVALID")
    return raw, resolved


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def jma_url(day):
    p = dict(prec_no="88", block_no="0980", year=str(day.year),
             month=str(day.month), day=str(day.day), view="")
    return JMA + "?" + urllib.parse.urlencode(p)


def model_url(start, end):
    return OM + "?" + urllib.parse.urlencode({
        "latitude": "28.15", "longitude": "129.32",
        "start_date": start, "end_date": end,
        "hourly": ",".join(VARS), "timezone": "Asia/Tokyo",
        "wind_speed_unit": "ms"})


def collect(start, end, fetch=get):
    calendar = days(start, end)
    now = dt.datetime.now(dt.timezone.utc)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from historical_environment import normalize_jma_hourly
    results = dict(schema_version="habu-koniya-weather-observations-v1",
                   date_start=start, date_end=end, generated_at=now.isoformat(),
                   privacy="PUBLIC_WEATHER_REFERENCE_ONLY_NO_OWNER_COORDS",
                   historical_asof_forecast_proof=False,
                   formal_100m_10min_labels_created=0,
                   jma=dict(station="古仁屋", station_id="88901",
                            observation_rows=[], source_receipts=[], missing=[]),
                   model_archive=dict(status="NOT_ACQUIRED", rows=[]))
    for day in calendar:
        # Strict JMA normalizer requires a completed civil day.
        if day >= now.astimezone(JST).date():
            results["jma"]["missing"].append(dict(day=day.isoformat(),
                                                   reason="CALENDAR_DAY_INCOMPLETE"))
            continue
        url = jma_url(day)
        try:
            raw, resolved = fetch(url)
            ts = dt.datetime.now(dt.timezone.utc).isoformat()
            receipt = dict(provider="JMA", station_id="88901",
                station_name="古仁屋", source_type="STATION_OBSERVATION",
                requested_url=url, resolved_url=resolved, retrieved_at=ts,
                size_bytes=len(raw), sha256=digest(raw),
                licence_url="https://www.jma.go.jp/jma/kishou/info/coment.html",
                source_received_at=ts, derived_at=ts,
                materialized_at=ts, audited_at=ts)
            norm = normalize_jma_hourly(raw, day=day.isoformat(), receipt=receipt)
            if len(norm["observations"]) != 24:
                raise ValueError("JMA_MISSING_HOURS")
            results["jma"]["observation_rows"].extend(norm["observations"])
            results["jma"]["source_receipts"].append(dict(
                day=day.isoformat(), sha256=receipt["sha256"], size_bytes=len(raw),
                url=url, source_role="OBSERVED_HOURLY_AT_KONIYA_ONLY"))
        except Exception as exc:
            results["jma"]["missing"].append(dict(day=day.isoformat(),
                              reason="JMA_UNVERIFIED_" + type(exc).__name__))
    url = model_url(start, end)
    try:
        raw, resolved = fetch(url)
        obj = json.loads(raw)
        h = obj["hourly"]
        times = h["time"]
        if (not isinstance(times, list) or not times or len(times) > 1200
                or times != sorted(set(times))
                or any(k not in h or len(h[k]) != len(times) for k in VARS)):
            raise ValueError("MODEL_HOURLY_GRID_INVALID")
        results["model_archive"] = dict(
            status="ARCHIVED_FORECAST_MODEL_NOT_MEASUREMENT",
            requested_url=url, resolved_url=resolved, raw_sha256=digest(raw),
            retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            reference_grid_public_approx=dict(latitude=28.15, longitude=129.32),
            units=obj.get("hourly_units", {}),
            hourly=dict(time=times, **{k:h[k] for k in VARS}),
            source_readiness="POSTHOC_ONLY_NOT_AN_ORIGINAL_P0")
    except Exception as exc:
        results["model_archive"] = dict(status="NOT_VERIFIED",
             reason="ARCHIVED_MODEL_UNAVAILABLE_" + type(exc).__name__)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    yesterday = dt.datetime.now(JST).date() - dt.timedelta(days=1)
    start, end = a.start or yesterday.replace(day=1).isoformat(), a.end or yesterday.isoformat()
    result = collect(start, end)
    out = Path(a.output)
    if out.exists():
        raise SystemExit("REFUSE_OVERWRITE")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, ensure_ascii=False,
                              indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(dict(source_status=result["model_archive"]["status"],
              jma_days=len(result["jma"]["source_receipts"]),
              jma_missing=len(result["jma"]["missing"]),
              has_private_coordinates=False), ensure_ascii=False))
    if not result["jma"]["source_receipts"] and result["model_archive"]["status"] == "NOT_VERIFIED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
