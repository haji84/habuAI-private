#!/usr/bin/env python3
"""Expand PR #80's real-GPX/OSM candidate classifier to the other eleven August nights.

No independent active-search attestation or full capture-outcome proof is
available. Every output is a private diagnostic candidate, never label 0/1.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from audit_aug31_road_search_candidates import (
    JST,LOG,QC,_time_window,_candidate_activity,_near_event,
    load_osm_matcher,RoadMatcher
)
from audit_august_sampled_exposure import NIGHTS
from gpx_audit import parse_gpx,utm52n,night_date_for_time
from recover_remaining_august_nights import index_events,_match

REST=tuple(n for n in NIGHTS if n!="2026-08-31")
PR77_RECEIPT="evidence/recovered_sources/2026-08-12night-sampled-exposure-ci-receipt.json"

class RemainingRoadAuditError(ValueError):
    pass

def _read_inputs(root:Path):
    with (root/QC).open(encoding="utf-8-sig",newline="") as f:
        qc={r["operational_night"]:r for r in csv.DictReader(f)}
    previous=json.loads((root/PR77_RECEIPT).read_text(encoding="utf-8"))
    if previous["totals"]["nights"]!=12 or previous["totals"]["sampled_spacetime_units"]!=8965:
        raise RemainingRoadAuditError("Historical August GPS diagnostic receipt changed")
    by_previous={r["night"]:r for r in previous["nights"]}
    original_text=(root/LOG).read_text(encoding="utf-8")
    events=index_events(original_text)
    by_night=defaultdict(list)
    for event in events:
        by_night[event["operational_night"]].append(event)
    baseline=json.loads((root/"dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    month=next(m["n"] for m in baseline["months"] if m["key"]=="2026-08")
    if month!=47 or baseline["owner_confirmed_monthly_counts"]["2026-08"]["status"]!="OWNER_CONFIRMED":
        raise RemainingRoadAuditError("Owner-confirmed August capture count changed")
    day_count={d["night"]:d["count"] for d in baseline["nights"] if d["month"]=="2026-08"}
    return qc,by_previous,by_night,day_count

def _one_night(root:Path,matcher:RoadMatcher,night:str,qc:dict,old:dict,
               original_events:list, owner_count:int|None)->tuple[dict,list[dict]]:
    path=root/f"data/raw/gpx/{night}__legacy.gpx"
    import hashlib
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if sha!=qc["sha256"] or sha!=old["source_gpx_sha256"]:
        raise RemainingRoadAuditError(f"GPX SHA mismatch {night}")
    points=parse_gpx(path)
    if len(points)!=int(qc["gps_points"]) or len(points)!=old["raw_gpx_points"]:
        raise RemainingRoadAuditError(f"GPX original point count mismatch {night}")
    if any(night_date_for_time(p["time_utc"])!=night for p in points):
        raise RemainingRoadAuditError(f"Wrong 07:00 JST night in {night}")

    events=list(original_events)
    captures=[dict(e) for e in events if e["event_type"]=="capture"]
    matched,_=_match(captures,points)
    if len(captures)!=matched:
        raise RemainingRoadAuditError(f"Original capture-statement GPX proximity incomplete: {night}")
    capture_quantity_candidates=sum(e["exact_owner_count_native"] or 1 for e in captures)
    if owner_count is not None and capture_quantity_candidates!=owner_count:
        raise RemainingRoadAuditError(f"Legacy owner day count differs from capture statements: {night}")
    starts=[datetime.fromisoformat(e["timestamp_interpreted_jst"]) for e in events if e["event_type"]=="exploration_start"]
    ends=[datetime.fromisoformat(e["timestamp_interpreted_jst"]) for e in events if e["event_type"]=="exploration_end"]
    valid_session=len(starts)==1 and len(ends)==1 and starts[0]<ends[0]
    begin=starts[0] if valid_session else None
    finish=ends[0] if valid_session else None
    if valid_session!=old["paired_session_markers"]:
        raise RemainingRoadAuditError(f"Session coverage drift: {night}")

    bins=defaultdict(list)
    qc_kept=matched_samples=ambiguous_samples=unmatched_samples=0
    prev=None
    for p in points:
        if p.get("exclude_point") or (p.get("hdop") is not None and p["hdop"]>10):
            prev=None
            continue
        qc_kept+=1
        xy=utm52n(p["latitude"],p["longitude"])
        near=matcher.match_xy(*xy)
        if near["status"]=="AUXILIARY_ROAD_MATCH_REVIEW":
            matched_samples+=1
        elif near["status"]=="AMBIGUOUS_MULTIPLE_ROADS":
            ambiguous_samples+=1
        else:
            unmatched_samples+=1
        s=p.get("speed_mps")
        if s is None or not math.isfinite(s) or not 0<=s<=45:
            s=None
            if prev is not None and not p.get("segment_break_before"):
                past,oldxy=prev
                gap=(p["time_utc"]-past["time_utc"]).total_seconds()
                if 0<gap<=5:
                    calculated=math.hypot(xy[0]-oldxy[0],xy[1]-oldxy[1])/gap
                    if calculated<=45:
                        s=calculated
        at=p["time_utc"].astimezone(JST)
        within=bool(valid_session and begin<=at<=finish)
        key=(math.floor(xy[0]/100),math.floor(xy[1]/100),_time_window(p["time_utc"]))
        bins[key].append({"time_utc":p["time_utc"],"inside_session":within,
                          "road_status":near["status"],"way_id":near["way_id"],
                          "speed_mps":round(s,3) if s is not None else None,
                          "hdop":p.get("hdop")})
        prev=(p,xy)
    if qc_kept!=old["gps_qa_kept_samples"] or len(bins)!=old["sampled_100m_10m_units"]:
        raise RemainingRoadAuditError(f"Historical GPS quality/cell total drift: {night}")
    review=[]
    classes=Counter()
    for (cx,cy,window),group in sorted(bins.items()):
        group.sort(key=lambda p:p["time_utc"])
        event_kind=_near_event(events,cx,cy,datetime.fromisoformat(window)+timedelta(minutes=5))
        if not valid_session and not event_kind:
            mode="SESSION_BOUNDARIES_UNVERIFIED"
        else:
            mode=_candidate_activity(group,event_kind)
        classes[mode]+=1
        matches=[p for p in group if p["road_status"]=="AUXILIARY_ROAD_MATCH_REVIEW"]
        ways=Counter(p["way_id"] for p in matches)
        noncapture=mode=="LIKELY_SLOW_SEARCH_REVIEW" and event_kind is None
        review.append({
            "night":night,"cell_x":cx,"cell_y":cy,"window_start_jst":window,
            "samples":len(group),
            "sampled_road_matches":len(matches),
            "sampled_ambiguous_road_matches":sum(p["road_status"]=="AMBIGUOUS_MULTIPLE_ROADS" for p in group),
            "osm_way_candidate":ways.most_common(1)[0][0] if ways else None,
            "paired_session":valid_session,
            "samples_inside_session":sum(p["inside_session"] for p in group),
            "activity_candidate":mode,
            "nearby_habu_event":event_kind or "NONE_RECORDED",
            "noncapture_review_candidate":noncapture,
            "owner_capture_outcome_complete":False,
            "actual_search_road_segment_verified":False,
            "observation":"UNKNOWN",
            "label":None
        })
    ins=sum(all(p["inside_session"] for p in binpoints) for binpoints in bins.values()) if valid_session else 0
    if ins!=old["fully_inside_paired_session_units"]:
        raise RemainingRoadAuditError(f"Paired-session cell total drift: {night}")
    if sum(row["samples"] for row in review)!=qc_kept:
        raise RemainingRoadAuditError(f"GPS sample accounting discrepancy: {night}")
    return {
        "night":night,"gpx_sha256":sha,"gpx_points":len(points),"gps_quality_kept":qc_kept,
        "road_matched_samples":matched_samples,"road_ambiguous_samples":ambiguous_samples,
        "road_unmatched_samples":unmatched_samples,"sampled_spacetime_units":len(review),
        "paired_session":valid_session,
        "units_fully_inside_recorded_session":ins if valid_session else None,
        "source_capture_event_mentions":len(captures),
        "source_capture_gpxtime_matches":matched,
        "capture_statement_quantity_candidate_sum":capture_quantity_candidates,
        "owner_dashboard_night_count":owner_count,
        "owner_confirmed_monthly_total":47,
        "capture_outcomes_complete":False,
        "official_active_search_road_segments":0,
        "formal_positive_training_rows":0,"formal_negative_training_rows":0,
        "noncapture_review_candidates":sum(row["noncapture_review_candidate"] for row in review),
        "activity_classes":dict(sorted(classes.items())),
        "gpx_sampling_max_gap_seconds":float(qc["max_gap_s"]),
        "source_unresolved":"SEARCH_EFFORT_AND_COMPLETE_CAPTURE_OUTCOMES"
    },review

def analyze_remaining(root:Path=ROOT, *, matcher:RoadMatcher|None=None,
                      matcher_evidence:dict|None=None)->tuple[dict,list[dict]]:
    root=Path(root)
    qc,history,events_by_night,counts=_read_inputs(root)
    if matcher is None:
        matcher,matcher_evidence=load_osm_matcher(root)
    if matcher_evidence is None:
        matcher_evidence={"road_source":"test-injected match engine only","historical_aug31_pre_exploration_available":False}
    reports=[];rows=[]
    for night in REST:
        report,units=_one_night(root,matcher,night,qc[night],history[night],events_by_night[night],counts.get(night))
        reports.append(report)
        rows.extend(units)
    if len(reports)!=11 or sum(x["gpx_points"] for x in reports)!=213809:
        raise RemainingRoadAuditError("Remaining source inventory altered")
    if len(rows)!=8277 or sum(x["gps_quality_kept"] for x in reports)!=208239:
        raise RemainingRoadAuditError("Historical 11-night sampled source total altered")
    if sum(x["paired_session"] for x in reports)!=8:
        raise RemainingRoadAuditError("Expected eight usable session-marker pairs")
    if sum(x["noncapture_review_candidates"] for x in reports)!=sum(r["noncapture_review_candidate"] for r in rows):
        raise RemainingRoadAuditError("Candidate counting mismatch")
    return {
        "schema_version":"habu-remaining11-august-osm-road-review-v1",
        "status":"REVIEW_ONLY_NOT_OWNER_SEARCH_ATTESTATION",
        "night_count":11,"original_gpx_point_total":213809,
        "quality_kept_samples":208239,"sampled_spacetime_unit_count":8277,
        "paired_recorded_session_nights":8,
        "gps_road_match_count":sum(x["road_matched_samples"] for x in reports),
        "review_noncapture_candidate_count":sum(x["noncapture_review_candidates"] for x in reports),
        "owner_confirmed_august_monthly_count":47,
        "capture_statement_count":sum(x["source_capture_event_mentions"] for x in reports),
        "match_count":sum(x["source_capture_gpxtime_matches"] for x in reports),
        "scientifically_certified_road_search_segments":0,
        "formal_positive_training_rows":0,"formal_negative_training_rows":0,
        "no_original_P0_backfilled":True,
        "input_osm":matcher_evidence,
        "nightly_reports":reports,
        "training_blockers":["NO_INDEPENDENT_SEARCH_EFFORT_ATTESTATION",
                             "NO_COMPLETE_OWNER_CAPTURE_OUTCOMES",
                             "NO_CANONICAL_INDIVIDUAL_ID_RECONCILIATION",
                             "OSM_IS_POSTHOC_AUXILIARY_NOT_EX_ANTE_AUGUST_ROAD_UNIVERSE"],
    },rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--output",type=Path,default=Path("artifacts/remaining-11-august-road-review"))
    opts=ap.parse_args()
    summary,rows=analyze_remaining(opts.root)
    opts.output.mkdir(parents=True,exist_ok=True)
    (opts.output/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (opts.output/"review_cells.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    print(json.dumps({"nights":summary["night_count"],"source_gpx_points":summary["original_gpx_point_total"],
                      "road_matched_samples":summary["gps_road_match_count"],
                      "sampled_units":summary["sampled_spacetime_unit_count"],
                      "review_noncapture_candidates":summary["review_noncapture_candidate_count"],
                      "per_night":[{"night":x["night"],"units":x["sampled_spacetime_units"],
                                    "road_samples":x["road_matched_samples"],
                                    "noncapture_candidates":x["noncapture_review_candidates"],
                                    "paired_session":x["paired_session"]} for x in summary["nightly_reports"]],
                      "formal_positive":0,"formal_negative":0},ensure_ascii=False))
if __name__=="__main__":
    main()
