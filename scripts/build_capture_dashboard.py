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
                raise CaptureDataError("Duplicate canonical event (details withheld)")
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
    # PR #92 owner-chat evidence is reconciled by night and count in build();
    # it is NOT an additional +6 capture operation.
    overlay = json.loads(path.read_text(encoding="utf-8"))
    if (overlay.get("schema_version") != "habu-owner-effort-confirmation-v1"
            or overlay.get("count_scope") != "owner_confirmed_personal_capture_and_search_nights"
            or overlay.get("time_boundary") != "07:00 Asia/Tokyo"
            or overlay.get("as_of_operational_night", "") <= cutoff):
        raise CaptureDataError("Invalid owner effort overlay")
    return overlay


def read_owner_night_tallies(repo: Path, after_night: str) -> dict[str, int]:
    """Validated owner-confirmed night totals without invented event times or GPS.

    A nightly file is a replacement tally, never an increment operation.
    Git history tracks revisions, and registered canonical events must agree.
    """
    root = repo / "data/raw/habu_owner_nights"
    tallies: dict[str, int] = {}
    if not root.exists():
        return tallies
    allowed = {
        "schema_version", "source", "operational_date", "owner_confirmed",
        "search_performed", "capture_count", "revision",
    }
    for path in sorted(root.rglob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(item, dict) or set(item) != allowed:
            raise CaptureDataError(f"Invalid owner nightly tally fields: {path}")
        night = item["operational_date"]
        if not isinstance(night, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", night):
            raise CaptureDataError(f"Invalid owner nightly date: {path}")
        try:
            if datetime.strptime(night, "%Y-%m-%d").date().isoformat() != night:
                raise ValueError("Invalid calendar date")
        except ValueError as exc:
            raise CaptureDataError(f"Invalid owner nightly calendar date: {path}") from exc
        if night <= after_night or path.stem != night or path.parent.name != night[:4] or night in tallies:
            raise CaptureDataError(f"Owner tally overlaps protected history or another date: {path}")
        number = item["capture_count"]
        if (item["schema_version"] != "habu-owner-night-v1" or item["source"] != TRUSTED_SOURCE
                or item["owner_confirmed"] is not True or item["search_performed"] is not True
                or type(number) is not int or not 0 <= number <= 100
                or type(item["revision"]) is not int or item["revision"] < 1):
            raise CaptureDataError(f"Unconfirmed/invalid owner nightly tally: {path}")
        tallies[night] = number
    return tallies


def apply_owner_amendments(repo: Path, months: dict, nights: dict) -> list[dict]:
    """Apply explicit user-approved replacements without altering archived originals.

    One JSON file per operational night is the current confirmation. Git history
    retains previous revisions; the previous count and effort state are checked
    before applying an amendment. Unknown nights cannot be introduced this way.
    """
    root = repo / "data/raw/habu_owner_amendments"
    audit: list[dict] = []
    if not root.exists():
        return audit
    allowed = {
        "schema_version", "source", "operational_date", "revision",
        "owner_confirmed", "original_captures", "original_search_performed",
        "capture_count", "search_performed", "reason",
    }
    seen: set[str] = set()
    for path in sorted(root.rglob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(item, dict) or set(item) != allowed:
            raise CaptureDataError(f"Invalid owner amendment fields: {path}")
        date = item["operational_date"]
        if not isinstance(date, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", date):
            raise CaptureDataError(f"Invalid amendment date: {path}")
        try:
            if datetime.strptime(date, "%Y-%m-%d").date().isoformat() != date:
                raise ValueError("Invalid calendar date")
        except ValueError as exc:
            raise CaptureDataError(f"Invalid amendment calendar date: {path}") from exc
        if path.stem != date or path.parent.name != date[:4] or date in seen:
            raise CaptureDataError(f"Duplicate/mismatched amendment path: {path}")
        seen.add(date)
        if item["schema_version"] != "habu-owner-amendment-v1" or item["source"] != TRUSTED_SOURCE:
            raise CaptureDataError(f"Untrusted amendment source: {path}")
        if item["owner_confirmed"] is not True or type(item["revision"]) is not int or item["revision"] < 1:
            raise CaptureDataError(f"Unconfirmed amendment: {path}")
        reason = item["reason"]
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 200:
            raise CaptureDataError(f"Amendment needs a brief reason: {path}")
        old = item["original_captures"]
        new = item["capture_count"]
        searched_before = item["original_search_performed"]
        searched_after = item["search_performed"]
        if (type(old) is not int or type(new) is not int or old < 0 or
                not 0 <= new <= 100 or type(searched_before) is not bool or
                type(searched_after) is not bool or (new > 0 and not searched_after)):
            raise CaptureDataError(f"Invalid amendment counts/search state: {path}")
        record = nights.get(date)
        if record is None or record["count"] != old or record["effort_confirmed"] is not searched_before:
            raise CaptureDataError(f"Owner amendment conflicts with existing night: {date}")
        if new == old and searched_after == searched_before:
            raise CaptureDataError(f"Amendment has no change: {date}")
        month = date[:7]
        months[month] += new - old
        if months[month] < 0:
            raise CaptureDataError(f"Negative monthly total after amendment: {month}")
        record["count"] = new
        record["effort_confirmed"] = searched_after
        record["effort_status"] = (
            "OWNER_AMENDED_CAPTURE" if new else
            "OWNER_AMENDED_ZERO" if searched_after else "OWNER_AMENDED_NOT_SEARCH"
        )
        record["status"] = "本人確認済み・訂正適用"
        record["note"] = "本人承認の訂正を適用。元の捕獲記録は保持。モデル学習用証拠ではない。"
        audit.append({"night": date, "revision": item["revision"],
                      "previous_count": old, "corrected_count": new,
                      "search_performed": searched_after})
    return audit


def apply_owner_effort(repo: Path, cutoff: str, months: dict, nights: dict,
                       added: dict, overlay: dict | None) -> tuple[dict, list, list]:
    """Reconcile explicit effort; never infer zero nights from missing observations."""
    # A confirmed daily tally is the single future-night source of truth.
    # When an individual-event log later arrives for that night its count must
    # match. Equal totals reconcile once; mismatches block generation.
    daily = read_owner_night_tallies(repo, max(cutoff, overlay["as_of_operational_night"]) if overlay else cutoff)
    for day, number in daily.items():
        if day in added and added[day] != number:
            raise CaptureDataError(f"Owner nightly and canonical capture counts conflict: {day}")
        if number > 0:
            added[day] = number
    captures = overlay.get("capture_nights", []) if overlay else []
    confirmed_zero = set(overlay.get("confirmed_zero_nights", [])) if overlay else set()
    excluded = set(overlay.get("excluded_effort_nights", [])) if overlay else set()
    historical = set()
    if overlay and len(confirmed_zero) != len(overlay.get("confirmed_zero_nights", [])):
        raise CaptureDataError("Duplicate confirmed zero date")
    if overlay and len(excluded) != len(overlay.get("excluded_effort_nights", [])):
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
            "status": "本人確定・探索夜の合計値" if night in daily else ("本人捕獲集計・個体証拠は別監査" if night in historical else "GitHub登録ログからの自動集計・最終監査待ち"),
            "start": "不明", "end": "不明", "events": None,
            "note": "本人確認済みの合計捕獲数。個体時刻・地点は未認証。" if night in daily else ("本人確認済みの捕獲数。研究用探索強度・GPX証拠とは別。" if night in historical else "Canonical capture log"),
        }
        months[night[:7]] = months.get(night[:7], 0) + n
    future_zero = read_confirmed_zero_effort(repo, max(cutoff, overlay["as_of_operational_night"]) if overlay else cutoff)
    if set(future_zero) & set(daily):
        raise CaptureDataError("Duplicate future zero-night sources")
    confirmed_zero.update(future_zero)
    confirmed_zero.update(day for day, number in daily.items() if number == 0)
    for night in confirmed_zero | excluded:
        if not isinstance(night, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", night):
            raise CaptureDataError("Invalid effort date")
    for night in sorted(confirmed_zero):
        months.setdefault(night[:7], 0)
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
            scoped_month = [n for n in nights.values()
                            if n["month"] == m["month"] and n["night"] <= scope]
            confirmed_month = [n for n in scoped_month if n["effort_confirmed"]]
            monthly_actual = {
                "captures": sum(n["count"] for n in scoped_month),
                "nights": len(confirmed_month),
                "positive": sum(n["count"] > 0 for n in confirmed_month),
                "zero": sum(n["count"] == 0 for n in confirmed_month),
            }
            if monthly_actual != {key: m[key] for key in monthly_actual}:
                raise CaptureDataError(f"Owner monthly effort mismatch: {m['month']}")
    # Seed totals are checked first. Later user amendments revise the derived
    # dashboard, not the verified 2026-10-26 baseline or its source records.
    amendments = apply_owner_amendments(repo, months, nights)
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
    return effort, list(by_month.values()), amendments


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
    reviewed = read_owner_chat_reviews(repo, cutoff)
    owner_overlay_counts = {x["night"]: x["count"] for x in overlay.get("capture_nights", [])} if overlay else {}
    for night, source in reviewed.items():
        reported = source["count"]
        if night in added and added[night] != reported:
            raise CaptureDataError("Owner-chat and canonical count disagreement: " + night)
        if night in owner_overlay_counts and owner_overlay_counts[night] != reported:
            raise CaptureDataError("Owner-chat and owner-effort tally disagree: " + night)
        # The receipt validates the SAME individuals represented in the tally.
        # Source families are not cumulative. Never add 2+2 or 4+4.
        added[night] = reported
    effort, effort_months, amendments = apply_owner_effort(repo, cutoff, months, nights, added, overlay)
    for night, receipt in reviewed.items():
        item = nights[night]
        if item["count"] != receipt["count"]:
            raise CaptureDataError("Owner-chat source quantity differs from dashboard: " + night)
        item["sighting"] = receipt["sighting_events"]
        item["roadkill"] = receipt["roadkill_events"]
        item["other_capture"] = receipt["other_person_captures"]
        item["pdca_status"] = receipt["pdca_status"]
        item["events"] = receipt["count"]
        item["status"] = "本人確定集計と会話記録が一致・科学検証は別"
        item["note"] = "元ログ復元記録と夜別合計が一致。目撃と轢死は加算しない。GPS空白や研究用Negativeは別監査。"
    cumulative = 0
    monthly = []
    for month, n in sorted(months.items()):
        cumulative += n
        monthly.append({"key": month, "n": n, "cum": cumulative})
    if cumulative != sum(n["count"] for n in nights.values()) + sum(undated_by_month.values()):
        raise CaptureDataError("Generated monthly/night/undated mismatch")
    owner_chat_statistics = {
        "report_nights": len(reviewed),
        "reported_capture_events": sum(x["count"] for x in reviewed.values()),
        "fauna_sighting_events": sum(x["sighting_events"] for x in reviewed.values()),
        "fauna_sighting_quantity": sum(x["sighting_quantity"] for x in reviewed.values()),
        "roadkill_events": sum(x["roadkill_events"] for x in reviewed.values()),
        "habu_roadkill_events": sum(x["habu_roadkill_events"] for x in reviewed.values()),
        "owner_capture_size_distribution": dict(sum((Counter(x["size_distribution"]) for x in reviewed.values()), Counter())),
        "capture_road_surface_distribution": dict(sum((Counter(x["road_surface_captures"]) for x in reviewed.values()), Counter())),
        "gps_gap_nights": [{"night": night, "gap_seconds": x["gps_gap_seconds"]}
                           for night, x in sorted(reviewed.items()) if x["gps_gap_seconds"] is not None],
        "pdca_status_by_night": [{"night": night, "result": x["pdca_status"],
                                  "official_p0_scored": False,
                                  "source_issue_number": x["source_issue_number"]}
                                 for night, x in sorted(reviewed.items())],
        "temperature_reports_unlocated_c": [{"night": night, "values": x["user_observed_temperature_c_unlocated"]}
                                            for night, x in sorted(reviewed.items()) if x["user_observed_temperature_c_unlocated"]],
        "formal_training_positive_from_review": 0,
        "formal_training_negative_from_review": 0,
        "source_level": "OWNER_CHAT_TRANSCRIBED_SCIENTIFIC_ELIGIBILITY_UNVERIFIED",
        "not_entire_2026_dataset": True,
    }
    return {
        "schema_version": "habu-capture-dashboard-v2",
        "asof": max([cutoff, *nights.keys()]),
        "baseline_cutoff": cutoff, "year": YEAR, "total": cumulative,
        "months": monthly,
        "effort": effort,
        "effort_months": effort_months,
        "owner_chat_statistics": owner_chat_statistics,
        "new_owner_report_nights": len(reviewed),
        "owner_amendments": amendments,
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
    for name in ("sw.js", "manifest.webmanifest", "_headers", "intake.html", "intake-core.js", "field.html", "field-core.js", "field-app.js", "field.webmanifest"):
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
