#!/usr/bin/env python3
"""Build a private, aggregate-only HUB NATURAL dashboard.

The audited 2026-10-20 snapshot is a frozen baseline. Import only strictly
newer operational nights from canonical GitHub data; never rewrite raw files.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
YEAR = 2026
TRUSTED_SOURCE = "user Habu log"


class CaptureDataError(ValueError):
    pass


def operational_night(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            raise ValueError("missing UTC offset")
        local = dt.astimezone(JST)
    except (TypeError, ValueError) as exc:
        raise CaptureDataError("Invalid time/offset in canonical log") from exc
    return (local.date() - timedelta(days=local.hour < 7)).isoformat()


def count(value: object) -> int:
    if type(value) is not int or value < 1 or value > 100:
        raise CaptureDataError("individual_count must be an integer 1..100")
    return value


def read_raw(repo: Path, cutoff: str) -> dict[str, int]:
    nights: Counter[str] = Counter()
    seen_sha: set[str] = set()
    seen_id: set[tuple[str, str]] = set()
    root = repo / "data/raw/habu_logs"
    if not root.exists():
        return {}
    for path in sorted(root.rglob("*.json")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen_sha:
            continue
        seen_sha.add(digest)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "habu-night-log-v2":
            continue
        if payload.get("source") != TRUSTED_SOURCE:
            continue
        night = payload.get("operational_date")
        if not isinstance(night, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", night):
            raise CaptureDataError(f"Invalid night in {path}")
        if night <= cutoff:
            continue
        events = payload.get("events")
        if not isinstance(events, list):
            raise CaptureDataError(f"No events array: {path}")
        for pos, event in enumerate(events):
            if not isinstance(event, dict) or event.get("type") != "capture":
                continue
            # Source is a user log. Other owners never count.
            if event.get("capture_owner", "self") not in ("self", "owner"):
                continue
            if event.get("species") not in (None, "ハブ", "habu", "Habu"):
                continue
            when = event.get("time_local")
            if operational_night(when) != night:
                raise CaptureDataError(f"07:00 JST night mismatch: {path}:{pos}")
            n = count(event.get("individual_count"))
            eid = event.get("event_id")
            if eid is None:
                place = event.get("place")
                if not isinstance(place, str) or not place.strip():
                    raise CaptureDataError(f"Missing event_id/place: {path}:{pos}")
                eid = f"time-place:{when}:{place}"
            if not isinstance(eid, str) or not eid.strip():
                raise CaptureDataError(f"Invalid event id: {path}:{pos}")
            key = night, eid
            if key in seen_id:
                raise CaptureDataError(f"Duplicate canonical event: {key}")
            seen_id.add(key)
            nights[night] += n
    return dict(nights)


def read_processed(repo: Path, cutoff: str) -> dict[str, int]:
    nights: Counter[str] = Counter()
    seen_ids: set[str] = set()
    root = repo / "data/processed/individuals"
    if not root.exists():
        return {}
    for path in sorted(root.rglob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                night = row.get("operational_date") or ""
                if night <= cutoff or not re.fullmatch(r"2026-\d{2}-\d{2}", night):
                    continue
                if (row.get("capture_owner") or "").lower().strip() not in ("self", "owner"):
                    continue
                individual = (row.get("individual_id") or "").strip()
                if not individual or individual in seen_ids:
                    raise CaptureDataError(f"Missing/duplicate individual_id in {path}")
                if operational_night(row.get("event_time_local", "")) != night:
                    raise CaptureDataError(f"Processed night mismatch in {path}")
                seen_ids.add(individual)
                nights[night] += 1
    return dict(nights)


def build(repo: Path) -> dict:
    baseline = json.loads((repo / "dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    cutoff = baseline["as_of_operational_night"]
    months = {x["key"]: x["n"] for x in baseline["months"]}
    nights = {x["night"]: dict(x) for x in baseline["nights"]}
    undated_captures = baseline.get("undated_captures", [])
    if not isinstance(undated_captures, list):
        raise CaptureDataError("Invalid undated reconciliation data")
    undated_by_month: Counter[str] = Counter()
    for item in undated_captures:
        if not isinstance(item, dict):
            raise CaptureDataError("Invalid undated reconciliation item")
        month, n = item.get("month"), item.get("count")
        if month not in months or type(n) is not int or not (1 <= n <= 100):
            raise CaptureDataError("Invalid undated month/count")
        if item.get("review_status") != "MONTH_TOTAL_ONLY_UNDATED_PENDING_SOURCE_RECONCILIATION":
            raise CaptureDataError("Undated month reconciliation requires review flag")
        undated_by_month[month] += n
    if any(night > cutoff for night in nights):
        raise CaptureDataError("Baseline includes future nights")
    for month, n in months.items():
        dated = sum(x["count"] for x in nights.values() if x["month"] == month)
        if n != dated + undated_by_month[month]:
            raise CaptureDataError(f"Baseline monthly reconciliation failed: {month}")
    raw = read_raw(repo, cutoff)
    processed = read_processed(repo, cutoff)
    added = dict(raw)
    for night, n in processed.items():
        if night in raw and raw[night] != n:
            raise CaptureDataError(f"Raw/processed count conflict: {night}")
        # Equal counts do not prove matching individuals: flag as review-required.
        added[night] = n
    for night, n in sorted(added.items()):
        if night in nights:
            raise CaptureDataError(f"Baseline double count: {night}")
        nights[night] = {
            "night": night, "month": night[:7], "count": n,
            "status": "GitHub登録ログからの自動集計・最終監査待ち",
            "start": "不明", "end": "不明", "events": None,
            "note": ("Raw/processed counts overlap; match not independently proven"
                     if night in raw and night in processed else
                     "Canonical data after frozen baseline")
        }
        months[night[:7]] = months.get(night[:7], 0) + n
    cumulative = 0
    monthly = []
    for month, n in sorted(months.items()):
        cumulative += n
        monthly.append({"key": month, "n": n, "cum": cumulative})
    if cumulative != sum(n["count"] for n in nights.values()) + sum(undated_by_month.values()):
        raise CaptureDataError("Generated monthly/night/undated mismatch")
    return {
        "schema_version": "habu-capture-dashboard-v2",
        "asof": max([cutoff, *added.keys()]),
        "baseline_cutoff": cutoff, "year": YEAR, "total": cumulative,
        "months": monthly,
        "nights": sorted(nights.values(), key=lambda n: n["night"]),
        "undated_captures": undated_captures,
        "undated_count": sum(undated_by_month.values()),
        "new_confirmed_nights": len(added),
        "review_status": "PROVISIONAL_LEGACY_NOT_REVALIDATED",
        "warnings": baseline.get("notes", []),
        "privacy": "AGGREGATE_ONLY_NO_COORDINATES",
        "source": "Frozen baseline + audited future-night canonical Habu logs",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def emit(repo: Path, output: Path | None = None) -> dict:
    payload = build(repo)
    target = output or repo / "dashboard/data/capture_summary.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html = (repo / "dashboard/index.html").read_text(encoding="utf-8")
    inline = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pattern = r'(<script id="snapshot" type="application/json">).*?(</script>)'
    generated, replaced = re.subn(pattern, lambda m: m[1] + inline + m[2], html, count=1, flags=re.S)
    if replaced != 1:
        raise CaptureDataError("Dashboard snapshot marker missing")
    dist = repo / "dashboard/dist"
    (dist / "data").mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(generated, encoding="utf-8")
    shutil.copyfile(target, dist / "data/capture_summary.json")
    for name in ("sw.js", "manifest.webmanifest", "_headers"):
        shutil.copyfile(repo / "dashboard" / name, dist / name)
    (dist / "assets").mkdir(exist_ok=True)
    logo = repo / "dashboard/assets/logo.png"
    shutil.copyfile(logo, dist / "assets/logo.png")
    # Generate correctly-sized install icons from the original user-provided logo.
    from PIL import Image
    with Image.open(logo) as im:
        im = im.convert("RGBA")
        for px, filename in ((192, "icon-192.png"), (512, "icon-512.png"), (180, "apple-touch-icon.png")):
            im.resize((px, px), Image.Resampling.LANCZOS).save(dist / "assets" / filename)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    data = emit(args.repo_root.resolve())
    print(f"HUB NATURAL: {data['total']} as of {data['asof']} (provisional)")


if __name__ == "__main__":
    main()
