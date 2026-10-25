#!/usr/bin/env python3
"""Recover August12 and September2 Habu event excerpts and compare actual GPX.

Both log sources are preserved extracted/indexed TEXT, not byte-exact original
TXT files. Event candidates remain distinct from audited personal captures;
roadkill/sightings never count as user-captured Habu. GPX cannot prove an animal
or absence of one, and must not create Negative labels on its own.
"""
from __future__ import annotations

import argparse
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
DATELINE = re.compile(r"(?m)^2026/\d{2}/\d{2} \d{1,2}:\d{2}$")
COORD_LAT = re.compile(r"2[78]\.\d{4,}$")
COORD_LON = re.compile(r"129\.\d{4,}$")
SOURCES = {
    "2026-08-12": {
        "log_path": "evidence/master-goal-1642/recovered_sources/august-extracted.txt",
        "first": "2026/08/12 20:56",
        "next": "2026/08/13 20:25",
        "gpx_path": "data/raw/gpx/2026-08-12__legacy.gpx",
        "source_category": "LIBRARY_PRESERVED_EXTRACTED_READ_NOT_ORIGINAL_TXT_BYTES",
        "library_file_id": "libfile_d6d1412b897081918d50057af2ca4a3e",
    },
    "2026-09-02": {
        "log_path": "evidence/recovered_sources/2026-09-02-habu-log-indexed-excerpt.txt",
        "first": "2026/09/02 21:58",
        "next": None,
        "gpx_path": "data/raw/gpx/2026-09-02__legacy.gpx",
        "source_category": "LIBRARY_INDEXED_READ_EXCERPT_NOT_ORIGINAL_TXT_BYTES",
        "library_file_id": "libfile_b4c4dbc4ff388191a205400dc2e344d8",
    },
}


class RecoveryError(ValueError):
    pass


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _time(label):
    match = re.fullmatch(r"(20\d\d)/(\d\d)/(\d\d) (\d{1,2}):(\d\d)", label)
    if not match:
        raise RecoveryError("Unparseable field-log clock")
    y, mo, day, hh, minute = map(int, match.groups())
    return datetime(y, mo, day, hh, minute, tzinfo=JST)


def night(dt):
    local = dt.astimezone(JST)
    return (local - timedelta(days=1) if local.hour < 7 else local).date().isoformat()


def segment_source(text, source):
    first = text.find(source["first"])
    if first < 0:
        raise RecoveryError("Missing source start marker")
    tail = text.find(source["next"], first+len(source["first"])) if source["next"] else len(text)
    if tail < 0:
        raise RecoveryError("Missing next night boundary")
    return text[first:tail].rstrip()+"\n", text[:first].count("\n")+1


def coordinates(block):
    lines = [x.strip() for x in block.splitlines() if x.strip()]
    pairs = []
    for lat, lon in zip(lines, lines[1:]):
        if COORD_LAT.fullmatch(lat) and COORD_LON.fullmatch(lon):
            value = (float(lat), float(lon))
            if math.isfinite(value[0]) and math.isfinite(value[1]):
                pairs.append(value)
    if len(pairs) != 1:
        return None
    return pairs[0]


def events_from_excerpt(excerpt, line_offset, operational_night):
    markers = list(DATELINE.finditer(excerpt))
    if not markers or markers[0].start() != 0:
        raise RecoveryError("Missing leading event clock")
    events = []
    for i, marker in enumerate(markers):
        end = markers[i+1].start() if i+1 < len(markers) else len(excerpt)
        block = excerpt[marker.start():end].rstrip()+"\n"
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        when = _time(lines[0])
        if night(when) != operational_night:
            raise RecoveryError("Unexpected operational night within recovered range")
        kind = ("capture" if "捕獲" in lines[1:3] else
                "sighting" if "目撃" in lines[1:3] else
                "roadkill" if "轢死" in lines[1:3] else
                "exploration_start" if "エリア探索開始" in lines else
                "exploration_end" if "エリア探索終了" in lines else
                "weather_or_context")
        specimen = lines[2] if kind == "capture" and len(lines) > 2 else None
        if kind == "capture" and not specimen.startswith("ハブ捕獲"):
            raise RecoveryError("Unrecognized capture species; quarantine")
        if kind in ("sighting","roadkill"):
            # Count/species text are source literal, not assumed owner capture.
            count_markers = [value for value in lines[2:] if re.fullmatch(r"\d+匹(以上)?",value)]
            quantity_literal = count_markers[0] if len(count_markers) == 1 else None
            category = lines[lines.index(quantity_literal)+1] if quantity_literal and lines.index(quantity_literal)+1<len(lines) else None
        else:
            quantity_literal, category = None, specimen
        location = coordinates(block)
        event = {
            "source_line_start": line_offset+excerpt[:marker.start()].count("\n"),
            "source_block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
            "field_log_time": lines[0],
            "timestamp_jst_interpreted": when.isoformat(),
            "event_type": kind,
            "species_or_native_note": category,
            "source_quantity_literal": quantity_literal,
            "explicit_exact_personal_capture_count": None if kind == "capture" else 0,
            "capture_statement_lower_bound": 1 if kind == "capture" else 0,
            "coordinates": {"lat":location[0],"lon":location[1]} if location else None,
            "raw_extracted_text_block": block,
        }
        events.append(event)
    return events


def parse_qc(root):
    file=root/"evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv"
    with file.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    return {r["operational_night"]:r for r in rows}


def recover(root=ROOT):
    root=Path(root)
    qc=parse_qc(root)
    baseline=json.loads((root/"dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    report={"schema_version":"habu-two-night-recovered-log-gpx-review-v1",
            "status":"SOURCE_EVENT_CANDIDATES_RECOVERED_NOT_TRAINING_APPROVED",
            "original_native_log_file_bytes_verified":False,
            "official_original_prediction_issued":False,
            "eligible_verified_negative_rows":0,
            "eligible_final_model_training_rows":0,
            "nights":[]}
    for op,src in SOURCES.items():
        log=root/src["log_path"];track=root/src["gpx_path"]
        raw=log.read_text(encoding="utf-8")
        excerpt,offset=segment_source(raw,src)
        events=events_from_excerpt(excerpt,offset,op)
        gpx_sha=_sha(track);q=qc[op]
        if q["sha256"]!=gpx_sha:
            raise RecoveryError("Source GPX SHA differs from historical QC registry")
        points=parse_gpx(track)
        if len(points)!=int(q["gps_points"]):
            raise RecoveryError("GPX source point count changed")
        start=_time(q["operational_night"].replace("-","/")+" 12:00")
        if any(night(p["time_utc"]) != op for p in points):
            raise RecoveryError("GPX source contains point from another operational night")
        qualified=[p for p in points if not p.get("exclude_point")
                   and (p.get("hdop") is None or p["hdop"]<=10)]
        matched=[]
        for e in events:
            if e["coordinates"] is None or e["event_type"] not in ("capture","sighting","roadkill"):
                e["gpx_match"]=None
                continue
            ref=e["coordinates"];when=datetime.fromisoformat(e["timestamp_jst_interpreted"]).astimezone(timezone.utc)
            candidate=None
            for p in qualified:
                delta=abs((p["time_utc"]-when).total_seconds())
                if delta>600:
                    continue
                dist=distance_m({"latitude":ref["lat"],"longitude":ref["lon"]},p)
                if dist<=100:
                    pair=(round(delta,3),round(dist,2),p["time_utc"].isoformat())
                    if candidate is None or pair<candidate:candidate=pair
            e["gpx_match"]=(
                {"status":"ACTUAL_GPX_SPACETIME_CORROBORATED",
                 "seconds_offset":candidate[0],"distance_m":candidate[1],
                 "gpx_sample_utc":candidate[2]} if candidate else
                {"status":"NO_GPXCORROBORATION_WITHIN_100M_10MIN"})
            if candidate and e["event_type"]=="capture":matched.append(e["field_log_time"])
        c=Counter(e["event_type"] for e in events)
        night_records=[n for n in baseline["nights"] if n["night"]==op]
        if len(night_records)!=1:raise RecoveryError("Missing or duplicated canonical day aggregate")
        one={"operational_night":op,"capture_event_mentions":c["capture"],
             "capture_statement_lower_bound_sum":c["capture"],
             "baseline_owner_capture_count":night_records[0]["count"],
             "exact_count_each_capture_confirmed_from_native_text":False,
             "owner_identity_verified_by_independent_individual_ids":False,
             "sighting_event_count":c["sighting"],"roadkill_event_count":c["roadkill"],
             "habu_roadkill_count_explicit":sum(1 for e in events if e["event_type"]=="roadkill" and e["species_or_native_note"]=="ハブ"),
             "exploration_start_markers":c["exploration_start"],
             "exploration_end_markers":c["exploration_end"],
             "weather_or_context_markers":c["weather_or_context"],
             "actual_gpx_sha256":gpx_sha,"actual_gpx_points":len(points),
             "gpx_points_quality_candidate":len(qualified),
             "actual_gpx_capture_event_matches":len(matched),
             "source_extracted_path":src["log_path"],
             "source_library_file_id":src["library_file_id"],
             "text_scope":src["source_category"],
             "source_extracted_file_sha256":_sha(log),
             "source_excerpt_sha256":hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
             "gpx_quality_and_exposure_role":"GPS_PASSAGE_ONLY_NOT_PROVEN_SEARCH_EFFORT",
             "positive_labels":"CANDIDATE_EXPLICIT_CAPTURE_STATEMENTS_ONLY",
             "negative_labels":"UNKNOWN_NOT_GENERATED",
             "individual_count_authority":"SOURCE_EVENT_COUNT_UNVERIFIED_OWNER_INDIVIDUALS",
             "events":events}
        report["nights"].append(one)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    r=recover(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"nights":[{
        k:n[k] for k in ("operational_night","capture_event_mentions","baseline_owner_capture_count",
                        "sighting_event_count","roadkill_event_count","habu_roadkill_count_explicit",
                        "actual_gpx_capture_event_matches","actual_gpx_points")}
        for n in r["nights"]],"formal_training_rows":0},ensure_ascii=False))
    return 0


if __name__=="__main__":
    main()
