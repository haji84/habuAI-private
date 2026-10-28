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


def read_owner_chat_reviews(repo: Path, cutoff: str) -> dict[str, dict]:
    """Use reviewed owner-chat capture statements for aggregate reporting ONLY.

    Chat/Issue receipts are not native raw GPS/log originals or independently
    certified individual identities. Never treat these rows as model labels.
    """
    records: dict[str, dict] = {}
    seen_event_ids: set[str] = set()
    root = repo / "data/reconstructions/habu_captures"
    for path in sorted(root.glob("*-owner-chat-dashboard-intake.json")) if root.exists() else []:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema_version") != "habu-owner-chat-dashboard-intake-v1":
            raise CaptureDataError("Unexpected owner-chat dashboard intake schema: "+path.name)
        night = value.get("operational_night")
        if not isinstance(night, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", night):
            raise CaptureDataError("Malformed owner-chat intake operational night")
        if night <= cutoff:
            raise CaptureDataError("Owner-chat intake must never rewrite frozen baseline")
        if path.name != night + "-owner-chat-dashboard-intake.json" or night in records:
            raise CaptureDataError("Owner-chat night/path duplicate or mismatch")
        source=value.get("source")
        if not isinstance(source,dict) or source.get("kind") != "owner_habu_log_chat_transcript":
            raise CaptureDataError("Owner-chat reconstruction lacks provenance type")
        issue=source.get("owner_authored_issue","")
        if not re.fullmatch(r"https://github\.com/haji84/habuAI-private/issues/[1-9]\d*",issue):
            raise CaptureDataError("Owner-chat intake has no bound source issue")
        # Do not interpret a user-supplied capture *summary* as individual proof.
        events=value.get("capture_events")
        if not isinstance(events,list) or not events or len(events)>100:
            raise CaptureDataError("Owner-chat capture events missing or too many")
        count=0
        sizes=Counter()
        surfaces=Counter()
        for e in events:
            if (not isinstance(e,dict) or e.get("owner") != "self" or
                    e.get("species") != "ハブ" or e.get("count") != 1):
                raise CaptureDataError("Owner-chat individual claim must be one explicitly owner-captured Habu")
            if operational_night(e.get("event_time_local")) != night:
                raise CaptureDataError("Owner-chat event time outside 07:00 JST night")
            eid=e.get("event_id")
            if not isinstance(eid,str) or not re.fullmatch(r"owner-chat-\d{8}-\d{4}",eid) or eid in seen_event_ids:
                raise CaptureDataError("Duplicate or malformed owner-chat source-event id")
            seen_event_ids.add(eid)
            size=e.get("size_class")
            if size not in ("小型","中型","大型","かなり大型","超大型","規格外クラス","不明"):
                raise CaptureDataError("Unknown Habu size class")
            surface=e.get("road_surface")
            if surface not in ("ドライ","ウエット","ソークド","不明"):
                raise CaptureDataError("Unsupported source road-surface category")
            sizes[size]+=1
            surfaces[surface]+=1
            count+=1
        obs=value.get("observations")
        if not isinstance(obs,dict):
            raise CaptureDataError("Missing source fauna/roadkill audit fields")
        metrics=("sighting_event_count","sighting_quantity_reported","roadkill_event_count",
                 "habu_roadkill_count","other_person_habu_capture_count")
        if any(type(obs.get(k)) is not int or obs[k]<0 for k in metrics):
            raise CaptureDataError("Invalid source observation counts")
        if obs["sighting_quantity_reported"]<obs["sighting_event_count"] or obs["habu_roadkill_count"]>obs["roadkill_event_count"]:
            raise CaptureDataError("Invalid source reaction quantities")
        limits=value.get("scientific_restrictions",{})
        if (limits.get("eligible_learning_positive_count")!=0 or
                limits.get("eligible_learning_negative_count")!=0 or
                limits.get("individual_identity_independently_certified") is not False or
                limits.get("complete_capture_outcomes_certified") is not False or
                limits.get("actual_searched_road_scopes_certified") is not False):
            raise CaptureDataError("Review-only owner-chat report cannot promote scientific training evidence")
        pdca=value.get("pdca",{})
        if not isinstance(pdca,dict) or pdca.get("result") not in ("BLOCKED","PARTIAL","PASS","FAIL","NOT_VALIDATED"):
            raise CaptureDataError("Invalid PDCA source-status receipt")
        if type(pdca.get("issue_number")) is not int or not issue.endswith("/"+str(pdca["issue_number"])):
            raise CaptureDataError("PDCA issue source mismatch")
        if pdca.get("scientific_hit_at_stage1") is not None or pdca.get("official_p0_verified") is not False:
            raise CaptureDataError("Missing official P0 must not be marked scored")
        session=value.get("session",{})
        if not isinstance(session,dict) or operational_night(session.get("started_local"))!=night or operational_night(session.get("ended_local"))!=night:
            raise CaptureDataError("Owner-chat session timestamps do not match operational night")
        if type(session.get("session_duration_minutes")) is not int or not 1<=session["session_duration_minutes"]<=1440:
            raise CaptureDataError("Invalid owner-chat session duration")
        gps=value.get("gps",{})
        if gps and (type(gps.get("gap_duration_seconds")) is not int or gps["gap_duration_seconds"]<0 or
                    gps.get("missing_track_not_interpolated") is not True):
            raise CaptureDataError("GPS gap must remain unobserved, never interpolated")
        temp=value.get("observed_air_temperature_c_user_reported_unlocated",[])
        if not isinstance(temp,list) or any(type(v) not in (float,int) or v<-30 or v>60 for v in temp):
            raise CaptureDataError("Invalid unlocated owner temperature reports")
        records[night] = {
            "count":count,
            "source_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "status":"本人ハブログ会話記録・元TXT/個体独立審査待ち",
            "source_issue_number":pdca["issue_number"],
            "sighting_events":obs["sighting_event_count"],
            "sighting_quantity":obs["sighting_quantity_reported"],
            "roadkill_events":obs["roadkill_event_count"],
            "habu_roadkill_events":obs["habu_roadkill_count"],
            "other_person_captures":obs["other_person_habu_capture_count"],
            "size_distribution":dict(sizes),
            "road_surface_captures":dict(surfaces),
            "session_duration_minutes":session["session_duration_minutes"],
            "gps_gap_seconds":gps.get("gap_duration_seconds") if gps else None,
            "pdca_status":pdca["result"],
            "official_p0_scored":False,
            "user_observed_temperature_c_unlocated":temp,
            "is_model_training_eligible":False,
        }
    return records


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
    reviewed = read_owner_chat_reviews(repo, cutoff)
    added = {night:row["count"] for night,row in reviewed.items()}
    for night,n in raw.items():
        if night in reviewed and reviewed[night]["count"] != n:
            raise CaptureDataError("Owner-chat and canonical raw capture quantity conflict: "+night)
        added[night]=n
    for night, n in processed.items():
        if night in added and added[night] != n:
            raise CaptureDataError(f"Capture count disagreement across source families: {night}")
        if night in raw and raw[night] != n:
            raise CaptureDataError(f"Raw/processed count conflict: {night}")
        # Equal counts do not prove matching individuals: flag as review-required.
        added[night] = n
    for night, n in sorted(added.items()):
        if night in nights:
            raise CaptureDataError(f"Baseline double count: {night}")
        source = reviewed.get(night)
        nights[night] = {
            "night": night, "month": night[:7], "count": n,
            "status": ("本人の捕獲記録・元TXT/個体原本認証は別審査" if source else
                       "GitHub登録ログからの自動集計・最終監査待ち"),
            "start": ("あり" if source else "不明"),
            "end": ("あり" if source else "不明"),
            "events": (n if source else None),
            "sighting": (source["sighting_events"] if source else None),
            "roadkill": (source["roadkill_events"] if source else None),
            "other_capture": (source["other_person_captures"] if source else None),
            "pdca_status": (source["pdca_status"] if source else "NOT_RECORDED"),
            "note": ("会話原文の捕獲数量として計上。目撃・轢死は加算しない。元TXT/GPX全原本・探索範囲・捕獲漏れ・個体IDの科学認証は未完了。" if source else
                     ("Raw/processed counts overlap; match not independently proven" if night in raw and night in processed else
                      "Canonical data after frozen baseline")),
        }
        months[night[:7]] = months.get(night[:7], 0) + n
    cumulative = 0
    monthly = []
    for month, n in sorted(months.items()):
        cumulative += n
        monthly.append({"key": month, "n": n, "cum": cumulative})
    if cumulative != sum(n["count"] for n in nights.values()) + sum(undated_by_month.values()):
        raise CaptureDataError("Generated monthly/night/undated mismatch")
    owner_chat_statistics = {
        "report_nights":len(reviewed),
        "reported_capture_events":sum(x["count"] for x in reviewed.values()),
        "fauna_sighting_events":sum(x["sighting_events"] for x in reviewed.values()),
        "fauna_sighting_quantity":sum(x["sighting_quantity"] for x in reviewed.values()),
        "roadkill_events":sum(x["roadkill_events"] for x in reviewed.values()),
        "habu_roadkill_events":sum(x["habu_roadkill_events"] for x in reviewed.values()),
        "owner_capture_size_distribution":dict(sum((Counter(x["size_distribution"]) for x in reviewed.values()),Counter())),
        "capture_road_surface_distribution":dict(sum((Counter(x["road_surface_captures"]) for x in reviewed.values()),Counter())),
        "gps_gap_nights":[{"night":night,"gap_seconds":x["gps_gap_seconds"]}
                          for night,x in sorted(reviewed.items()) if x["gps_gap_seconds"] is not None],
        "pdca_status_by_night":[{"night":night,"result":x["pdca_status"],
                                  "official_p0_scored":False,
                                  "source_issue_number":x["source_issue_number"]}
                                  for night,x in sorted(reviewed.items())],
        "temperature_reports_unlocated_c":[{"night":night,"values":x["user_observed_temperature_c_unlocated"]}
                                          for night,x in sorted(reviewed.items()) if x["user_observed_temperature_c_unlocated"]],
        "formal_training_positive_from_review":0,
        "formal_training_negative_from_review":0,
        "source_level":"OWNER_CHAT_TRANSCRIBED_SCIENTIFIC_ELIGIBILITY_UNVERIFIED",
        "not_entire_2026_dataset":True
    }
    return {
        "schema_version": "habu-capture-dashboard-v2",
        "asof": max([cutoff, *added.keys()]),
        "baseline_cutoff": cutoff, "year": YEAR, "total": cumulative,
        "months": monthly,
        "nights": sorted(nights.values(), key=lambda n: n["night"]),
        "undated_captures": undated_captures,
        "undated_count": sum(undated_by_month.values()),
        "new_confirmed_nights": len(set(raw) | set(processed)),
        "new_owner_report_nights": len(reviewed),
        "owner_chat_statistics": owner_chat_statistics,
        "owner_confirmed_monthly_counts": owner_confirmed,
        "review_status": "PROVISIONAL_LEGACY_NOT_REVALIDATED",
        "warnings": baseline.get("notes", []),
        "privacy": "AGGREGATE_ONLY_NO_COORDINATES",
        "source": "Frozen baseline + reviewed owner-chat reports and canonical future-night logs (source grades kept separate)",
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
