#!/usr/bin/env python3
"""Build personal capture aggregates from audited baseline and new canonical Habu logs.

Only dates strictly AFTER baseline cutoff are imported. Historic discrepancies are
reported for human audit, not silently re-counted. Generated JSON excludes locations.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import shutil
import hashlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
YEAR = 2026
TRUSTED_SOURCE = "user Habu log"


class DataAuditError(ValueError):
    pass


def operating_night(timestamp: str) -> str:
    try:
        dt = datetime.fromisoformat(timestamp)
        if dt.tzinfo is None:
            raise ValueError("timestamp has no timezone")
        dt = dt.astimezone(JST)
    except Exception as exc:
        raise DataAuditError(f"invalid timestamp: {timestamp}") from exc
    return (dt.date() - timedelta(days=1) if dt.hour < 7 else dt.date()).isoformat()


def _safe_count(raw: object, source: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1 or raw > 100:
        raise DataAuditError(f"invalid capture individual_count at {source}: {raw!r}")
    return raw


def _captures_from_raw(repo: Path, cutoff: str) -> dict[str, int]:
    seen_files: set[str] = set()
    unique_events: dict[tuple[str, str], tuple[int, str]] = {}
    day_counts: Counter[str] = Counter()
    for path in sorted((repo / "data/raw/habu_logs").rglob("*.json")):
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest in seen_files:
            continue
        seen_files.add(digest)
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise DataAuditError(f"invalid raw JSON: {path}") from exc
        if payload.get("schema_version") != "habu-night-log-v2":
            continue
        if payload.get("source") != TRUSTED_SOURCE:
            # Unknown/third-party sources are not assumed to be owner captures.
            continue
        night = payload.get("operational_date")
        if not isinstance(night, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", night):
            raise DataAuditError(f"bad operational date: {path}")
        if night <= cutoff or not night.startswith(f"{YEAR}-"):
            continue
        if not isinstance(payload.get("events"), list):
            raise DataAuditError(f"no events list: {path}")
        for index, evt in enumerate(payload["events"]):
            if not isinstance(evt, dict) or evt.get("type") != "capture":
                continue
            if evt.get("capture_owner", "self") not in ("self", "owner"):
                continue
            when = evt.get("time_local")
            if not isinstance(when, str) or operating_night(when) != night:
                raise DataAuditError(f"07:00 boundary mismatch: {path} event[{index}]")
            count = _safe_count(evt.get("individual_count"), f"{path} event[{index}]")
            event_id = evt.get("event_id")
            # Identical times at same place are possible: different event_ids are allowed.
            if event_id is not None:
                if not isinstance(event_id, str) or not event_id.strip():
                    raise DataAuditError(f"bad event_id: {path} event[{index}]")
                key = (night, "id:" + event_id)
            else:
                place = str(evt.get("place") or "").strip()
                if not place:
                    raise DataAuditError(f"missing place / event_id: {path} event[{index}]")
                key = (night, "timeplace:" + when + ":" + place)
            previous = unique_events.get(key)
            if previous is not None:
                raise DataAuditError(f"duplicate or ambiguous capture event {key} in {previous[1]} and {path}")
            unique_events[key] = (count, str(path))
            day_counts[night] += count
    return dict(day_counts)


def _captures_from_processed(repo: Path, cutoff: str) -> dict[str, int]:
    # Processed individuals are authoritative only when each row's owner is explicit.
    # Historical CSV has no such proof, and is behind the cutoff anyway.
    ids: dict[str, tuple[str, str]] = {}
    day_counts: Counter[str] = Counter()
    for path in sorted((repo / "data/processed/individuals").rglob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                night = row.get("operational_date", "")
                if night <= cutoff or not night.startswith(f"{YEAR}-"):
                    continue
                if row.get("capture_owner", "").strip().lower() not in {"self", "owner"}:
                    continue
                iid = row.get("individual_id", "").strip()
                when = row.get("event_time_local", "")
                if not iid or operating_night(when) != night:
                    raise DataAuditError(f"invalid individual or 07:00 boundary: {path} {iid}")
                if iid in ids:
                    raise DataAuditError(f"duplicate individual_id: {iid}")
                ids[iid] = (night, str(path))
                day_counts[night] += 1
    return dict(day_counts)


def build(repo: Path) -> dict:
    baseline_path = repo / "dashboard/baseline_2026.json"
    base = json.loads(baseline_path.read_text(encoding="utf-8"))
    cutoff = base["as_of_operational_night"]
    months = {m["key"]: int(m["n"]) for m in base["months"]}
    nights = {n["night"]: dict(n) for n in base["nights"]}
    if any(n["night"] > cutoff for n in nights.values()):
        raise DataAuditError("baseline includes records after cutoff")
    if sum(months.values()) != sum(int(n["count"]) for n in nights.values()):
        raise DataAuditError("baseline total and night counts do not match")
    raw = _captures_from_raw(repo, cutoff)
    processed = _captures_from_processed(repo, cutoff)
    new_by_night = dict(raw)
    for night, count in processed.items():
        if night in raw and raw[night] != count:
            raise DataAuditError(f"raw/processed individual count mismatch on {night}: {raw[night]} != {count}")
        new_by_night[night] = count
    for night, count in sorted(new_by_night.items()):
        if night in nights:
            raise DataAuditError(f"attempt to double count baseline night: {night}")
        nights[night] = {"night": night, "month": night[:7], "count": count, "status": "新規ログ・自動集計（要最終監査）", "start": "不明", "end": "不明", "events": None, "sighting": None, "roadkill": None, "other_capture": None, "note": "GitHub正本の登録済みログから反映"}
        months[night[:7]] = months.get(night[:7], 0) + count
    cumulative = 0
    monthly_out = []
    for month, n in sorted(months.items()):
        cumulative += n
        monthly_out.append({"key": month, "n": n, "cum": cumulative})
    newest = max([cutoff, *new_by_night.keys()])
    return {
        "schema_version": "habu-capture-dashboard-v2",
        "asof": newest,
        "baseline_cutoff": cutoff,
        "year": YEAR,
        "total": cumulative,
        "months": monthly_out,
        "nights": sorted(nights.values(), key=lambda n: n["night"]),
        "new_confirmed_nights": len(new_by_night),
        "review_status": "PROVISIONAL_LEGACY_NOT_REVALIDATED",
        "warnings": base.get("notes", []),
        "privacy": "AGGREGATE_ONLY_NO_COORDINATES",
        "source": "Baseline snapshot + canonical Habu night logs after cutoff; never count sightings/roadkills/other captures",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    data = build(repo)
    dest = (args.output or repo / "dashboard/data/capture_summary.json").resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Keep source dashboard immutable: export an updated self-contained offline copy.
    source_html = (repo / "dashboard/index.html").read_text(encoding="utf-8")
    json_inline = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pattern = r'(<script id="snapshot" type="application/json">).*?(</script>)'
    rendered, replacements = re.subn(pattern, lambda m: m.group(1) + json_inline + m.group(2), source_html, count=1, flags=re.S)
    if replacements != 1:
        raise DataAuditError("dashboard snapshot script not found")
    dist = repo / "dashboard/dist"
    (dist / "data").mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(rendered, encoding="utf-8")
    shutil.copyfile(dest, dist / "data/capture_summary.json")
    print(f"{dist} : {data['total']} personal captures / {data['asof']}")

if __name__ == "__main__":
    main()
