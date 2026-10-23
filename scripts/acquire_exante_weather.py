#!/usr/bin/env python3
"""Fetch, validate and atomically archive prospective weather as ex-ante evidence.

This is SOURCE ACQUISITION ONLY. It never issues ORIGINAL P0, estimates a capture
count, interpolates to 100 m, or promotes a model. Live API usage is limited to
non-commercial research; a commercial licence is not implied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
HOURLY = (
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "pressure_msl", "wind_speed_10m", "wind_direction_10m",
)
ENDPOINT = "https://api.open-meteo.com/v1/forecast"
LICENSE_URI = "https://open-meteo.com/en/terms"
MAX_RESPONSE_BYTES = 2_000_000
ROOT = Path(__file__).resolve().parents[1]


class WeatherAcquisitionError(ValueError):
    pass


def _aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise WeatherAcquisitionError("Timezone-aware timestamp required")
    return value.astimezone(JST)


def night_for(dt: datetime) -> str:
    local = _aware(dt)
    return (local - timedelta(days=1) if local.hour < 7 else local).date().isoformat()


def _window(night: str):
    from datetime import date
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", night) or date.fromisoformat(night).isoformat() != night:
        raise WeatherAcquisitionError("Invalid operational night")
    beginning = datetime.fromisoformat(night + "T07:00:00+09:00")
    return beginning, beginning + timedelta(days=1)


def validate_sites(config: dict) -> list[dict]:
    if config.get("schema_version") != "habu-weather-sampling-sites-v1":
        raise WeatherAcquisitionError("Unsupported site schema")
    rows = config.get("sites")
    if not isinstance(rows, list) or not rows or len(rows) > 10:
        raise WeatherAcquisitionError("Expected 1..10 configured sites")
    result, seen = [], set()
    for row in rows:
        ident = row.get("site_id")
        if not isinstance(ident, str) or not re.fullmatch(r"[a-z0-9_]{3,48}", ident) or ident in seen:
            raise WeatherAcquisitionError("Invalid or duplicated site ID")
        seen.add(ident)
        lat, lon = row.get("latitude"), row.get("longitude")
        if (type(lat) not in (int, float) or type(lon) not in (int, float)
                or not math.isfinite(lat) or not math.isfinite(lon)
                or not 27.8 <= lat <= 28.7 or not 128.9 <= lon <= 129.9):
            raise WeatherAcquisitionError("Site outside target sampling envelope")
        if row.get("island") not in ("奄美大島", "加計呂麻島"):
            raise WeatherAcquisitionError("Unknown target island")
        result.append(row)
    return result


def _url(site: dict) -> str:
    # Hardcoded HTTPS host + enumerated variables, never caller-supplied URL.
    params = {
        "latitude": str(site["latitude"]),
        "longitude": str(site["longitude"]),
        "hourly": ",".join(HOURLY),
        "timezone": "Asia/Tokyo",
        "forecast_days": "3",
        "wind_speed_unit": "ms",
    }
    return ENDPOINT + "?" + urlencode(params)


def _fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "HabuAIResearch/1.0 (+https://github.com/haji84/habuAI-private)"})
    with urlopen(request, timeout=15) as response:
        if getattr(response, "status", 200) != 200:
            raise WeatherAcquisitionError("Weather API HTTP status is not 200")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise WeatherAcquisitionError("Weather API response too large")
    return raw


def _normalize(site: dict, raw: bytes, received_at: datetime,
               night: str, request_url: str) -> dict:
    if not raw or len(raw) > MAX_RESPONSE_BYTES:
        raise WeatherAcquisitionError("Empty or oversized weather response")
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WeatherAcquisitionError("Invalid weather JSON") from exc
    if not isinstance(data, dict) or data.get("error"):
        raise WeatherAcquisitionError("Weather provider returned an error")
    if data.get("timezone") != "Asia/Tokyo":
        raise WeatherAcquisitionError("Unexpected provider timezone")
    hourly = data.get("hourly")
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
        raise WeatherAcquisitionError("No hourly forecast")
    times = hourly["time"]
    if not times or len(times) > 240:
        raise WeatherAcquisitionError("Unreasonable number of weather hours")
    for key in HOURLY:
        if not isinstance(hourly.get(key), list) or len(hourly[key]) != len(times):
            raise WeatherAcquisitionError("Missing required hourly variable: " + key)
    first, last = _window(night)
    eligible, previous = [], None
    for index, label in enumerate(times):
        if not isinstance(label, str):
            raise WeatherAcquisitionError("Invalid hourly time")
        try:
            parsed = datetime.fromisoformat(label)
        except ValueError as exc:
            raise WeatherAcquisitionError("Unparseable hourly timestamp") from exc
        # Open-Meteo timezone=Asia/Tokyo returns local time with no offset.
        hour = parsed.replace(tzinfo=JST) if parsed.tzinfo is None else parsed.astimezone(JST)
        if previous is not None and hour <= previous:
            raise WeatherAcquisitionError("Non-monotonic hourly forecast")
        previous = hour
        row = {}
        for key in HOURLY:
            value = hourly[key][index]
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise WeatherAcquisitionError("Invalid numeric forecast")
            row[key] = value
        if max(first, received_at) < hour < last:
            if any(v is None for v in row.values()):
                raise WeatherAcquisitionError("Missing prospective hourly values")
            eligible.append({"valid_at_jst": hour.isoformat(), **row})
    if not eligible:
        raise WeatherAcquisitionError("No future hours within the selected operational night")
    latitude, longitude = data.get("latitude"), data.get("longitude")
    if (type(latitude) not in (int, float) or type(longitude) not in (int, float)
            or not math.isfinite(latitude) or not math.isfinite(longitude)
            or abs(latitude - site["latitude"]) > 0.4 or abs(longitude - site["longitude"]) > 0.4):
        raise WeatherAcquisitionError("Unexpected provider grid location")
    return {
        "site_id": site["site_id"], "island": site["island"],
        "requested_point": [site["latitude"], site["longitude"]],
        "provider_grid_point": [latitude, longitude],
        "request_url": request_url,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_body_utf8": raw.decode("utf-8"),
        "available_at_utc": received_at.astimezone(timezone.utc).isoformat(),
        "resolution_minutes": 60,
        "future_hourly_rows": eligible,
    }


def acquire(night: str, config: dict, *, clock=None, fetcher=None,
            purpose: str = "noncommercial-research") -> dict:
    if purpose != "noncommercial-research":
        raise WeatherAcquisitionError("Open-Meteo free endpoint not licensed for commercial use")
    clock = clock or (lambda: datetime.now(timezone.utc))
    fetcher = fetcher or _fetch
    start = _aware(clock())
    _, end = _window(night)
    if start >= end:
        raise WeatherAcquisitionError("Selected night is over; cannot recreate an ex-ante forecast")
    sites = validate_sites(config)
    outputs = []
    for site in sites:
        url = _url(site)
        body = fetcher(url)
        received = _aware(clock())
        if received < start:
            raise WeatherAcquisitionError("Clock reversed during acquisition")
        if received >= end:
            raise WeatherAcquisitionError("Forecast acquisition completed after the target night")
        if not isinstance(body, bytes):
            raise WeatherAcquisitionError("Fetcher must return response bytes")
        outputs.append(_normalize(site, body, received, night, url))
    available = max(datetime.fromisoformat(o["available_at_utc"]) for o in outputs)
    return {
        "schema_version": "habu-exante-weather-evidence-v1",
        "source_class": "forecast_predictor",
        "operational_night": night, "timezone": "Asia/Tokyo",
        "acquisition_started_at_utc": start.astimezone(timezone.utc).isoformat(),
        "available_at_utc": available.isoformat(),
        "provider": "Open-Meteo",
        "model_specification": "best_match_by_provider; exact underlying run not independently certified",
        "access_mode": purpose, "terms_url": LICENSE_URI,
        "sites": outputs,
        "status": "WEATHER_SOURCE_CAPTURED_NOT_PRODUCTION_P0",
        "scientific_scope": {
            "weather_resolution_minutes": 60,
            "spatial_road_interpolation_verified": False,
            "original_p0_issued": False,
            "training_or_stage_gate_verified": False,
        },
    }


def atomic_archive(root: Path, bundle: dict) -> Path:
    root = Path(root).resolve()
    night = bundle["operational_night"]
    _window(night)
    when = datetime.fromisoformat(bundle["available_at_utc"]).astimezone(timezone.utc)
    raw = (json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
           + "\n").encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    location = root / "evidence" / "exante" / "weather" / night
    location.mkdir(parents=True, exist_ok=True)
    target = location / (when.strftime("%Y%m%dT%H%M%S%fZ") + "-" + digest[:16] + ".json")
    # O_EXCL keeps distinct source snapshots append-only.
    with target.open("xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--night", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--purpose", default="noncommercial-research",
                        choices=("noncommercial-research", "commercial"))
    args = parser.parse_args()
    config = json.loads((args.root / "features/weather_sampling_sites.json").read_text(encoding="utf-8"))
    try:
        bundle = acquire(args.night, config, purpose=args.purpose)
        path = atomic_archive(args.root, bundle)
    except (WeatherAcquisitionError, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({
        "status": bundle["status"], "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "available_at_utc": bundle["available_at_utc"],
        "sample_sites": len(bundle["sites"]),
        "original_p0_issued": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
