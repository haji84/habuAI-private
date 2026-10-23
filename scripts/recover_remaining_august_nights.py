#!/usr/bin/env python3
"""Recover all remaining August GPX nights from a preserved Library text READ.

Neither this extracted text nor GPS proximity authenticates owner capture counts.
Never auto-create owner-individual IDs, negatives, model_learning or ORIGINAL P0.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gpx_audit import parse_gpx, distance_m

JST = ZoneInfo("Asia/Tokyo")
SOURCE = "evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt"
SOURCE_LIBRARY_ID = "libfile_76fd960f5a1481918b03b1b4c9bd9f88"
TARGETS = (
    "2026-08-13", "2026-08-15", "2026-08-17", "2026-08-19",
    "2026-08-21", "2026-08-23", "2026-08-24", "2026-08-27",
    "2026-08-28", "2026-08-29", "2026-08-31",
)
DAY_LINE = re.compile(r"(?m)^2026/(?:08|09)/\d\d \d{1,2}:\d\d$")
LAT = re.compile(r"2[78]\.\d{4,}$")
LON = re.compile(r"129\.\d{4,}$")


class RecoveryError(ValueError):
    pass


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _clock(raw):
    matched = re.fullmatch(r"(\d{4})/(\d\d)/(\d\d) (\d{1,2}):(\d\d)", raw)
    if not matched:
        raise RecoveryError("Invalid original clock: " + raw)
    return datetime(*map(int, matched.groups()), tzinfo=JST)


def _night(stamp):
    return (stamp.astimezone(JST) - timedelta(hours=7)).date().isoformat()


def _coordinates(lines):
    pairs = []
    for first, second in zip(lines, lines[1:]):
        if LAT.fullmatch(first) and LON.fullmatch(second):
            lat, lon = float(first), float(second)
            if math.isfinite(lat) and math.isfinite(lon):
                pairs.append((lat, lon))
    return pairs[0] if len(pairs) == 1 else None


def index_events(text):
    """Parse all dated blocks; retain their exact Library-read bytes and line offsets."""
    if len(text.splitlines()) != 10506:
        raise RecoveryError("Library read 10506-line coverage is not complete")
    matches = list(DAY_LINE.finditer(text))
    if not matches:
        raise RecoveryError("No dated events in recovered text")
    out = []
    for i, marker in enumerate(matches):
        pos = marker.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[pos:end].rstrip()+"\n"
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        if not lines:
            continue
        when = _clock(lines[0])
        kind = ("capture" if len(lines)>1 and lines[1] == "捕獲" else
                "sighting" if len(lines)>1 and lines[1] == "目撃" else
                "roadkill" if len(lines)>1 and lines[1] == "轢死" else
                "exploration_start" if "エリア探索開始" in lines else
                "exploration_end" if "エリア探索終了" in lines else
                "weather_or_context")
        quantity = next((v for v in lines[2:] if re.fullmatch(r"\d+匹(以上)?",v)),None)
        category = (lines[2] if kind=="capture" and len(lines)>2 else
                    lines[lines.index(quantity)+1] if quantity and lines.index(quantity)+1<len(lines) else None)
        if kind=="capture" and not (category or "").startswith("ハブ捕獲"):
            kind="capture_unclassified"
        location = _coordinates(lines)
        explicit_count = None
        if kind=="capture" and category:
            n = re.search(r"(?<!\d)(\d+)匹(?!以上)",category)
            if n: explicit_count=int(n.group(1))
        out.append({
            "operational_night":_night(when),
            "source_line":text.count("\n",0,pos)+1,
            "block_sha256":hashlib.sha256(block.encode("utf-8")).hexdigest(),
            "timestamp_native":lines[0],"timestamp_interpreted_jst":when.isoformat(),
            "event_type":kind,"species_or_native_note":category,
            "quantity_literal":quantity,
            "exact_owner_count_native":explicit_count if kind=="capture" else 0,
            "capture_mention_lower_bound":1 if kind=="capture" else 0,
            "coordinates":({"latitude":location[0],"longitude":location[1]} if location else None),
            "source_block":block,
            "gpx_proximity":None
        })
    return out


def _qc(root):
    src = root/"evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv"
    with src.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    return {x["operational_night"]:x for x in rows}


def _match(events, points):
    valid = sorted((p for p in points if not p.get("exclude_point")
                    and (p.get("hdop") is None or p["hdop"]<=10)),
                   key=lambda p:p["time_utc"])
    stamps=[p["time_utc"] for p in valid]
    hits=0
    for event in events:
        if event["coordinates"] is None or event["event_type"] not in ("capture","sighting","roadkill"):
            continue
        at=datetime.fromisoformat(event["timestamp_interpreted_jst"]).astimezone(timezone.utc)
        lo=bisect.bisect_left(stamps,at-timedelta(minutes=10))
        hi=bisect.bisect_right(stamps,at+timedelta(minutes=10))
        best=None
        ref=event["coordinates"]
        for p in valid[lo:hi]:
            dist=distance_m(ref,p)
            if dist<=100:
                delta=abs((p["time_utc"]-at).total_seconds())
                c=(round(delta,3),round(dist,2),p["time_utc"].isoformat())
                if best is None or c<best:best=c
        event["gpx_proximity"]=(
            {"status":"ACTUAL_GPX_SPACETIME_CORROBORATED",
             "seconds_offset":best[0],"distance_m":best[1],
             "sample_utc":best[2]} if best else
            {"status":"NO_MATCH_WITHIN_100M_10MIN"})
        if best and event["event_type"]=="capture":hits+=1
    return hits,len(valid)


def recover(root=ROOT):
    root=Path(root)
    p=root/SOURCE
    text=p.read_text(encoding="utf-8")
    all_events=index_events(text)
    qc=_qc(root)
    baseline=json.loads((root/"dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    results=[]
    for night in TARGETS:
        events=[dict(e) for e in all_events if e["operational_night"]==night]
        if not events:
            raise RecoveryError("No indexed log events for "+night)
        q=qc.get(night)
        if not q:
            raise RecoveryError("No independent original GPX inventory for "+night)
        track=root/f"data/raw/gpx/{night}__legacy.gpx"
        sha=_sha(track)
        if sha!=q["sha256"]:
            raise RecoveryError("Original GPX hash mismatch: "+night)
        points=parse_gpx(track)
        if len(points)!=int(q["gps_points"]):
            raise RecoveryError("Original GPX track point count mismatch: "+night)
        if any(_night(pt["time_utc"])!=night for pt in points):
            raise RecoveryError("GPX contains another night: "+night)
        matches,eligible=_match(events,points)
        counts=Counter(e["event_type"] for e in events)
        capture=[e for e in events if e["event_type"]=="capture"]
        killed=[e for e in events if e["event_type"]=="roadkill"]
        known=[n["count"] for n in baseline["nights"] if n["night"]==night]
        if len(known)>1:
            raise RecoveryError("Ambiguous baseline date")
        conflicts = []
        if counts["capture_unclassified"]:conflicts.append("NON_HABU_OR_AMBIGUOUS_CAPTURE_EVENT")
        if not known:conflicts.append("NO_DAY_LEVEL_BASELINE_NOT_ZERO_CAPTURE")
        if known and known[0]<len(capture):conflicts.append("BASELINE_FEWER_THAN_EXPLICIT_CAPTURE_EVENTS")
        if matches!=len(capture):conflicts.append("CAPTURE_GPX_PROXIMITY_NOT_COMPLETE")
        if not counts["exploration_start"] or not counts["exploration_end"]:
            conflicts.append("EXPLORATION_SESSION_MARKER_INCOMPLETE")
        results.append({
            "night":night,
            "source_file":SOURCE,
            "source_library_file_id":SOURCE_LIBRARY_ID,
            "source_library_read_not_native_file_bytes":True,
            "gpx_path":track.relative_to(root).as_posix(),
            "gpx_sha256":sha,"gpx_points":len(points),"gpx_qc_candidate_points":eligible,
            "capture_mentions":len(capture),
            "capture_gpx_matched":matches,
            "capture_exact_individual_count_from_text":None if any(x["exact_owner_count_native"] is None for x in capture) else sum(x["exact_owner_count_native"] for x in capture),
            "capture_minimum_mentioned":len(capture),
            "dashboard_day_count":known[0] if known else None,
            "sighting_events":counts["sighting"],
            "roadkill_events":len(killed),
            "habu_roadkill_events":sum(1 for e in killed if e["species_or_native_note"]=="ハブ"),
            "ambiguous_capture_events":counts["capture_unclassified"],
            "exploration_start_events":counts["exploration_start"],
            "exploration_end_events":counts["exploration_end"],
            "unknown_weather_events":counts["weather_or_context"],
            "source_limitations":conflicts,
            "positive_labels":"EXPLICIT_CAPTURE_EVENT_CANDIDATES_NOT_OWNER_INDIVIDUALS",
            "negative_labels":"UNKNOWN_NO_VERIFIED_COMPLETE_SEARCH_EFFORT",
            "official_training_eligible":False,
            "events":events,
        })
    return {
        "schema_version":"habu-remaining-august-library-log-vs-gpx-v1",
        "status":"RECOVERED_EVENT_CANDIDATES_NOT_TRAINING_APPROVED",
        "source_path":SOURCE,
        "source_file_sha256":_sha(p),
        "source_library_file_id":SOURCE_LIBRARY_ID,
        "library_read_line_count":len(text.splitlines()),
        "native_original_txt_bytes_verified":False,
        "night_count":len(results),
        "total_capture_mentions":sum(x["capture_mentions"] for x in results),
        "total_capture_gpx_matches":sum(x["capture_gpx_matched"] for x in results),
        "final_positive_training_rows":0,
        "final_negative_training_rows":0,
        "p0_retroactively_issued":False,
        "nights":results,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--output",type=Path)
    opts=ap.parse_args()
    report=recover(opts.root)
    if opts.output:
        opts.output.parent.mkdir(parents=True,exist_ok=True)
        opts.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":report["status"],
        "source_sha256":report["source_file_sha256"],
        "nights":[{
            k:x[k] for k in ("night","gpx_points","capture_mentions",
                           "capture_gpx_matched","sighting_events","roadkill_events",
                           "habu_roadkill_events","dashboard_day_count","source_limitations")
        } for x in report["nights"]],
        "training_rows":0,
    },ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
