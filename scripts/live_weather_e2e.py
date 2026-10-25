#!/usr/bin/env python3
"""Exercise real weather API for a future operational night, archive immutable evidence.

No P0 is issued; this is a live source acceptance check, not model readiness.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acquire_exante_weather import acquire, atomic_archive
from audit_p0_exante_assets import audit

JST = ZoneInfo("Asia/Tokyo")


def next_unstarted_night(now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware clock required")
    local = now.astimezone(JST)
    date = local.date() if local.hour < 7 else local.date() + timedelta(days=1)
    return date.isoformat()


def live_smoke(repo: Path) -> dict:
    now = datetime.now(JST)
    night = next_unstarted_night(now)
    config = json.loads((repo / "features/weather_sampling_sites.json").read_text(encoding="utf-8"))
    weather = acquire(night, config, purpose="noncommercial-research")
    archive = atomic_archive(repo, weather)
    sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
    cutoff = datetime.fromisoformat(weather["available_at_utc"])
    verified = audit(repo, night, cutoff,
                     weather_snapshot=archive.relative_to(repo).as_posix())
    weather_status = next(x for x in verified["items"] if x["input"] == "weather")
    if weather_status["status"] != "SOURCE_VERIFIED_NOT_PRODUCTION_READY":
        raise RuntimeError("Weather source acceptance failed: " + weather_status["reason"])
    # Conservative: success only for verified, actually fetched weather evidence.
    return {
        "status": "LIVE_WEATHER_SOURCE_ACCEPTED_NOT_OFFICIAL_P0",
        "night": night,
        "acquired_at_utc": weather["available_at_utc"],
        "source_sha256": sha256,
        "snapshot_relative_path": archive.relative_to(repo).as_posix(),
        "site_ids": [x["site_id"] for x in weather["sites"]],
        "hours_by_site": {x["site_id"]: len(x["future_hourly_rows"]) for x in weather["sites"]},
        "weather_audit": weather_status["status"],
        "official_original_p0_issued": False,
        "production_model_ready": False,
    }


def main() -> int:
    try:
        result = live_smoke(ROOT)
        destination = ROOT / "artifacts/live-weather-e2e"
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc),
                          "official_original_p0_issued": False},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
