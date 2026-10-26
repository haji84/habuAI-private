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



def read_confirmed_zero_effort(repo: Path, cutoff: str) -> set[str]:
    """Only explicit owner-confirmed post-baseline zero-capture search nights."""
    root = repo / "data/raw/habu_effort"
    confirmed: set[str] = set()
    if not root.exists():
        return confirmed
    for path in sorted(root.rglob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if item.get("schema_version") != "habu-effort-night-v1":
            continue
        if item.get("source") != TRUSTED_SOURCE:
            raise CaptureDataError(f"Invalid effort source: {path}")
        night = item.get("operational_date")
        if not isinstance(night, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", night):
            raise CaptureDataError(f"Invalid effort night: {path}")
        if night <= cutoff:
            raise CaptureDataError("Historical effort needs audited owner confirmation")
        if item.get("owner_confirmed") is not True or item.get("search_performed") is not True or item.get("capture_count") != 0:
            raise CaptureDataError(f"Unconfirmed/invalid zero effort night: {path}")
        if night in confirmed:
            raise CaptureDataError(f"Duplicate effort night: {night}")
        confirmed.add(night)
    return confirmed


def read_owner_effort_overlay(repo: Path, cutoff: str) -> dict | None:
    """Owner tally is separate from research-quality exposure or GPX evidence."""
    path = repo / "dashboard/owner_effort_2026-10-26.json"
    if not path.exists():
        return None
    overlay = json.loads(path.read_text(encoding="utf-8"))
    if (overlay.get("schema_version") != "habu-owner-effort-confirmation-v1"
            or overlay.get("count_scope") != "owner_confirmed_personal_capture_and_search_nights"
            or overlay.get("time_boundary") != "07:00 Asia/Tokyo"
            or overlay.get("as_of_operational_night", "") <= cutoff):
        raise CaptureDataError("Invalid owner effort overlay")
    return overlay


def apply_owner_effort(repo: Path, cutoff: str, months: dict, nights: dict,
                       added: dict, overlay: dict | None) -> tuple[dict, list]:
    """Reconcile explicit effort; never infer zero nights from missing observations."""
    captures = overlay.get("capture_nights", []) if overlay else []
    confirmed_zero = set(overlay.get("confirmed_zero_nights", [])) if overlay else set()
    excluded = set(overlay.get("excluded_effort_nights", [])) if overlay else set()
    historical = set()
    if len(confirmed_zero) != len(overlay.get("confirmed_zero_nights", [])) if overlay else False:
        raise CaptureDataError("Duplicate confirmed zero date")
    if len(excluded) != len(overlay.get("excluded_effort_nights", [])) if overlay else False:
        raise CaptureDataError("Duplicate excluded date")
    if confirmed_zero & excluded:
        raise CaptureDataError("Zero night is excluded at the same time")
    for item in captures:
        night, n = item.get("night"), item.get("count")
        if not isinstance(night, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", night) or type(n) is not int or n < 1:
            raise CaptureDataError("Invalid owner capture night")
        if night <= cutoff or night in nights or night in historical or night in confirmed_zero or night in excluded:
            raise CaptureDataError("Owner capture overlaps frozen baseline or other owner date")
        historical.add(night)
        if night in added and added[night] != n:
            raise CaptureDataError("Owner-confirmed and canonical capture counts conflict")
        added[night] = n
    for night in sorted(added):
        if night in nights:
            raise CaptureDataError(f"Baseline double count: {night}")
        n = added[night]
        nights[night] = {
            "night": night, "month": night[:7], "count": n,
            "status": "本人捕獲集計・個体証拠は別監査" if night in historical else "GitHub登録ログからの自動集計・最終監査待ち",
            "start": "不明", "end": "不明", "events": None,
            "note": "本人確認済みの捕獲数。研究用探索強度・GPX証拠とは別。" if night in historical else
                    ("Raw/processed counts overlap; match not independently proven"
                     if night in added and night not in historical else "Canonical capture log"),
        }
        months[night[:7]] = months.get(night[:7], 0) + n
    future_zero = read_confirmed_zero_effort(repo, max(cutoff, overlay["as_of_operational_night"]) if overlay else cutoff)
    confirmed_zero.update(future_zero)
    for night in confirmed_zero | excluded:
        if not isinstance(night, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", night):
            raise CaptureDataError("Invalid effort date")
    for night in sorted(confirmed_zero):
        if night in nights and nights[night]["count"] != 0:
            raise CaptureDataError("Confirmed zero conflicts with captured individuals")
        if night not in nights:
            nights[night] = {
                "night": night, "month": night[:7], "count": 0,
                "start": "不明", "end": "不明", "events": None,
                "status": "本人確認済み・捕獲ゼロの探索夜",
                "note": "個人の稼働集計に採用。科学的NegativeやExposureではない。"
            }
    for night in excluded:
        if night in nights and nights[night]["count"] > 0:
            raise CaptureDataError("Excluded effort conflicts with capture event")
    for night, item in nights.items():
        included = night not in excluded and (item["count"] > 0 or night in confirmed_zero)
        item["effort_confirmed"] = included
        if night in excluded:
            item["effort_status"] = "EXCLUDED_NOT_SEARCH"
        elif night in confirmed_zero:
            item["effort_status"] = "OWNER_CONFIRMED_ZERO"
            if night in ("2026-04-12", "2026-04-17"):
                item["status"] = "本人確認済み・捕獲0匹／稼働1晩"
                item["note"] = "稼働統計は本人確認済み。位置・時間帯・研究用Negativeは別途扱う。"
        elif included:
            item["effort_status"] = "CAPTURE_CONFIRMED_NIGHT"
        else:
            item["effort_status"] = "UNVERIFIED_EFFORT"
    by_month: dict[str, dict] = {}
    for month in sorted(months):
        subset = [n for n in nights.values() if n["month"] == month and n["effort_confirmed"]]
        positive = sum(n["count"] > 0 for n in subset)
        zeros = sum(n["count"] == 0 for n in subset)
        total = len(subset)
        by_month[month] = {
            "key": month, "captures": months[month], "nights": total,
            "positive_nights": positive, "zero_nights": zeros,
            "per_night_average": round(months[month] / total, 4) if total else None,
            "capture_success_rate": round(positive / total, 4) if total else None,
        }
    total_effort = sum(x["nights"] for x in by_month.values())
    positive = sum(x["positive_nights"] for x in by_month.values())
    zero = sum(x["zero_nights"] for x in by_month.values())
    if positive + zero != total_effort:
        raise CaptureDataError("Effort classification totals disagree")
    captures_total = sum(months.values())
    effort = {
        "total_nights": total_effort, "positive_nights": positive, "zero_nights": zero,
        "per_night_average": round(captures_total / total_effort, 4) if total_effort else None,
        "capture_success_rate": round(positive / total_effort, 4) if total_effort else None,
        "classification": "OWNER_CONFIRMED_PERSONAL_EFFORT",
        "not_model_exposure": True, "not_negative_training_labels": True,
    }
    if overlay:
        scope = overlay["as_of_operational_night"]
        scoped = [n for n in nights.values() if n["night"] <= scope and n["effort_confirmed"]]
        scoped_captures = sum(n["count"] for n in nights.values() if n["night"] <= scope)
        actual = {
            "total_captures": scoped_captures, "effort_nights": len(scoped),
            "positive_nights": sum(n["count"] > 0 for n in scoped),
            "zero_nights": sum(n["count"] == 0 for n in scoped),
        }
        if actual != overlay.get("expected"):
            raise CaptureDataError(f"Owner totals fail reconciliation: {actual}")
        for m in overlay.get("monthly_expected", []):
            got = next((x for x in by_month.values() if x["key"] == m["month"]), None)
            if not got or any(got[field] != m[alias] for field, alias in (
                    ("captures", "captures"), ("nights", "nights"),
                    ("positive_nights", "positive"), ("zero_nights", "zero"))):
                raise CaptureDataError(f"Owner monthly effort mismatch: {m['month']}")
    return effort, list(by_month.values())


def build(repo: Path) -> dict:
    baseline = json.loads((repo / "dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    cutoff = baseline["as_of_operational_night"]
    months = {x["key"]: x["n"] for x in baseline["months"]}
    nights = {x["night"]: dict(x) for x in baseline["nights"]}
    owner_confirmed = baseline.get("owner_confirmed_monthly_counts", {})
    if not isinstance(owner_confirmed, dict):
        raise CaptureDataError("Invalid owner confirmation metadata")
    for month, confirmation in owner_confirmed.items():
        if (month not in months or not isinstance(confirmation, dict) or
                confirmation.get("status") != "OWNER_CONFIRMED" or
                confirmation.get("count") != months[month] or
                confirmation.get("scope") != "monthly_personal_capture_total" or
                confirmation.get("independent_event_time_location_gpx_verification") is not False):
            raise CaptureDataError("Owner-confirmed monthly count mismatch")
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
    overlay = read_owner_effort_overlay(repo, cutoff)
    effort, effort_months = apply_owner_effort(repo, cutoff, months, nights, added, overlay)
    cumulative = 0
    monthly = []
    for month, n in sorted(months.items()):
        cumulative += n
        monthly.append({"key": month, "n": n, "cum": cumulative})
    if cumulative != sum(n["count"] for n in nights.values()) + sum(undated_by_month.values()):
        raise CaptureDataError("Generated monthly/night/undated mismatch")
    return {
        "schema_version": "habu-capture-dashboard-v2",
        "asof": max([cutoff, *added.keys(), *(overlay.get("confirmed_zero_nights", []) if overlay else [])]),
        "baseline_cutoff": cutoff, "year": YEAR, "total": cumulative,
        "months": monthly,
        "effort": effort,
        "effort_months": effort_months,
        "nights": sorted(nights.values(), key=lambda n: n["night"]),
        "undated_captures": undated_captures,
        "undated_count": sum(undated_by_month.values()),
        "new_confirmed_nights": len(added),
        "owner_confirmed_monthly_counts": owner_confirmed,
        "review_status": "OWNER_CONFIRMED_PERSONAL_TOTALS_NOT_SCIENTIFIC_EXPOSURE" if overlay else "PROVISIONAL_LEGACY_NOT_REVALIDATED",
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
    confirmed = ",".join(sorted(k for k,v in data["owner_confirmed_monthly_counts"].items() if v.get("status")=="OWNER_CONFIRMED"))
    print(f"HUB NATURAL: {data['total']} as of {data['asof']} (owner-confirmed months: {confirmed}; individual scientific verification pending)")


if __name__ == "__main__":
    main()
