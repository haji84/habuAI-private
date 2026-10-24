#!/usr/bin/env python3
"""Adjudicate motion near 75 source-linked fauna review packets, without inventing search.

A logged animal encounter is a point observation. GPS motion near that point
cannot attest the owner was searching for Habu or that all captures were logged.
This tool produces only private human-review queues and aggregate audit counts.
"""
from __future__ import annotations
import argparse
import bisect
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from audit_august_native_capture_original import LIBRARY_RAW_SHA256,SOURCE
from audit_august_fauna_sighting_context import analyze_sightings
from audit_aug31_road_search_candidates import load_osm_matcher
from gpx_audit import parse_gpx,utm52n,night_date_for_time
from recover_remaining_august_nights import _clock,index_events

RECEIPT="evidence/recovered_sources/2026-08-fauna-gpx-road-sighting-ci-receipt.json"
QC="evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv"
WINDOW_SECONDS=90
SOURCE_RADIUS_METRES=100.0
MAX_CONSECUTIVE_GPS_GAP_S=5.0
REVISIT_BURST_GAP_SECONDS=90.0

class ActivityReviewError(ValueError):
    pass

def _sha_bytes(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _compact_id(values:list[str])->str:
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()[:24]

def motion_classification(sample_speeds:list[float|None],
                          contiguous_seconds:float, point_count:int)->str:
    """Motion context only: every return remains UNVERIFIED owner search effort."""
    known=[v for v in sample_speeds if v is not None and math.isfinite(v) and 0<=v<=45]
    if point_count<6 or contiguous_seconds<8 or len(known)<5 or len(known)/point_count<0.7:
        return "INSUFFICIENT_CONTIGUOUS_GPX_MOTION"
    n=len(known)
    stopped=sum(v<0.5 for v in known)/n
    slow=sum(0.5<=v<=6 for v in known)/n
    fast=sum(v>=11 for v in known)/n
    if fast>=0.65:
        return "FAST_PASSAGE_NEAR_LOGGED_FAUNA"
    if stopped>=0.65:
        return "STATIONARY_NEAR_LOGGED_FAUNA"
    if slow>=0.65 and fast<=0.10:
        return "LOW_SPEED_MOVEMENT_NEAR_LOGGED_FAUNA"
    return "MIXED_MOVEMENT_NEAR_LOGGED_FAUNA"

def _source_key(e:dict)->tuple[int,int]:
    c=e["source_coordinates"]
    x,y=utm52n(float(c["latitude"]),float(c["longitude"]))
    return math.floor(x/100),math.floor(y/100)

def _verified_night_point_grid(root:Path,night:str,qc:dict)->dict:
    track=root/f"data/raw/gpx/{night}__legacy.gpx"
    sha=_sha_bytes(track)
    if sha!=qc["sha256"]:
        raise ActivityReviewError(f"GPX source digest mismatch: {night}")
    original=parse_gpx(track)
    if len(original)!=int(qc["gps_points"]):
        raise ActivityReviewError(f"GPX original point count mismatch: {night}")
    if any(night_date_for_time(p["time_utc"])!=night for p in original):
        raise ActivityReviewError(f"JST07:00 source scope changed: {night}")
    grid=defaultdict(list)
    for original_index,p in enumerate(original):
        if p.get("exclude_point") or p.get("segment_break_before") or p["hdop"] is None or not 0<=p["hdop"]<=10:
            continue
        x,y=utm52n(p["latitude"],p["longitude"])
        speed=p.get("speed_mps")
        if speed is not None and (not math.isfinite(speed) or not 0<=speed<=45):
            speed=None
        grid[(math.floor(x/100),math.floor(y/100))].append({
            "time_utc":p["time_utc"],"x":x,"y":y,
            "hdop":p["hdop"],"speed_mps":speed,
            "sequence":p["sequence"],"original_gpx_point_index":original_index,
            "segment_break_before":p["segment_break_before"]
        })
    for key in grid:
        grid[key].sort(key=lambda p:p["time_utc"])
    return {"night":night,"source_gpx_sha256":sha,"all_points":len(original),
            "strict_quality_grid":grid}

def _nearby_grid_points(grid:dict,xy:tuple[float,float],radius:float)->list[dict]:
    x,y=xy
    cx,cy=math.floor(x/100),math.floor(y/100)
    shift=math.ceil(radius/100)+1
    rows=[]
    for ix in range(cx-shift,cx+shift+1):
        for iy in range(cy-shift,cy+shift+1):
            for p in grid.get((ix,iy),()):
                if math.hypot(p["x"]-x,p["y"]-y)<=radius:
                    rows.append(p)
    rows.sort(key=lambda p:(p["time_utc"],p["sequence"]))
    return rows

def _count_temporal_clusters(points:list[dict],*,split_seconds:float)->int:
    if not points:
        return 0
    stamps=sorted({p["time_utc"] for p in points})
    return 1+sum((b-a).total_seconds()>split_seconds for a,b in zip(stamps,stamps[1:]))

def _motion_context(event:dict,night_index:dict,matcher)->dict:
    if event["source_event_type"]!="sighting" or not event["same_source_bin_has_strict_gpx_and_osm_alignment"]:
        raise ActivityReviewError("Non-strict or non-sighting source cannot create a priority motion record")
    if not event["candidate_id"] or not event["candidate_review_group_id"]:
        raise ActivityReviewError("Strict original fauna source lacks prior review packet identity")
    at=_clock(event["timestamp_native"]).astimezone(timezone.utc)
    pos=event["source_coordinates"]
    if not pos:
        raise ActivityReviewError("Strict original sighting missing coordinates")
    x,y=utm52n(float(pos["latitude"]),float(pos["longitude"]))
    source_way=event["gpx"].get("source_osm_way_candidate")
    if source_way is None or not event["gpx"]["auxiliary_osm_same_way"]:
        raise ActivityReviewError("Strict fauna anchor lacks unambiguous auxiliary road")
    point_grid=night_index["strict_quality_grid"]
    space=_nearby_grid_points(point_grid,(x,y),SOURCE_RADIUS_METRES)
    near_t=[p for p in space if abs((p["time_utc"]-at).total_seconds())<=WINDOW_SECONDS]
    on_way=[]
    for p in near_t:
        match=matcher.match_xy(p["x"],p["y"])
        if match["status"]=="AUXILIARY_ROAD_MATCH_REVIEW" and match["way_id"]==source_way:
            on_way.append(p)
    # This is a contiguous measured-pair sum only. A gap is not filled with a
    # fabricated searched path, interval or length.
    paired_seconds=0.0
    longest_gap=0.0
    for p,q in zip(on_way,on_way[1:]):
        d=(q["time_utc"]-p["time_utc"]).total_seconds()
        longest_gap=max(longest_gap,d)
        if (0<d<=MAX_CONSECUTIVE_GPS_GAP_S and
                q["original_gpx_point_index"]==p["original_gpx_point_index"]+1):
            paired_seconds+=d
    speeds=[p["speed_mps"] for p in on_way]
    mode=motion_classification(speeds,paired_seconds,len(on_way))
    # These are timestamp clusters of GPS points in the SAME 100m grid cell.
    # They do not count confirmed repeat search passes.
    own_cell=[p for p in space if (math.floor(p["x"]/100),math.floor(p["y"]/100))==_source_key(event)]
    visit_clusters=_count_temporal_clusters(own_cell,split_seconds=REVISIT_BURST_GAP_SECONDS)
    known=[v for v in speeds if v is not None]
    return {
        "source_block_sha256":event["source_block_sha256"],
        "night":event["night"],
        "candidate_id":event["candidate_id"],
        "review_group_id":event["candidate_review_group_id"],
        "original_source_line":event["source_line"],
        "original_sighting_source_time":event["timestamp_native"],
        "organism_category":event["category"],
        "organism_original_note":event["organism_note_exact"],
        "point_coordinates":pos, # Actions private artifact ONLY
        "osm_auxiliary_way_id":source_way,
        "actual_gpx_source_sha256":night_index["source_gpx_sha256"],
        "source_field_log_sha256":LIBRARY_RAW_SHA256,
        "local_window_seconds_each_direction":WINDOW_SECONDS,
        "spatial_source_radius_metres":SOURCE_RADIUS_METRES,
        "strict_quality_gpx_points_in_radius_window":len(near_t),
        "same_auxiliary_osm_way_gpx_points_in_window":len(on_way),
        "speed_available_sample_count":len(known),
        "speed_unknown_sample_count":len(on_way)-len(known),
        "stopped_speed_samples":sum(v<0.5 for v in known),
        "low_speed_samples":sum(0.5<=v<=6 for v in known),
        "fast_speed_samples":sum(v>=11 for v in known),
        "measured_adjacent_same_way_gpx_pair_seconds":round(paired_seconds,2),
        "max_observed_sample_gap_in_selected_context_s":round(longest_gap,3),
        "source_100m_cell_gpx_time_clusters_not_confirmed_repeat_passes":visit_clusters,
        "local_motion_context":mode,
        "source_logged_fauna_observation_at_point":True,
        "speed_from_same_gpx_as_initial_candidate_selection":True,
        "independently_certified_habu_targeted_search":False,
        "observed_entire_road_cell_as_searched":False,
        "complete_capture_outcomes_for_cell":False,
        "training_observation":"UNKNOWN",
        "training_label":None,
        "formal_positive_eligible":False,
        "formal_negative_eligible":False
    }

def audit_priority_packets(root:Path=ROOT)->tuple[dict,list[dict],list[dict]]:
    root=Path(root)
    baseline=json.loads((root/"dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    months={m["key"]:m["n"] for m in baseline["months"]}
    if months["2026-08"]!=47 or sum(m["n"] for m in baseline["months"])!=243:
        raise ActivityReviewError("Owner-confirmed August 47 or cumulative 243 drift")
    prior=json.loads((root/RECEIPT).read_text(encoding="utf-8"))
    if (prior["recovered_gpx_night_sighting_records"]!=705 or
            prior["unique_existing_packet_groups_with_strict_fauna_sighting_context"]!=75 or
            prior["unique_original_review_candidate_cells_with_strict_fauna_sighting_context"]!=94 or
            prior["strict_fauna_sighting_source_events_on_those_candidate_cells"]!=99):
        raise ActivityReviewError("Prior original sighting source receipt changed")
    summary,fauna_events,packet_source=analyze_sightings(root)
    if (summary["totals"]["sightings_matched_100m_10min_actual_gpx"]!=705 or
            summary["totals"]["candidate_review_groups_with_strict_fauna_observation"]!=75):
        raise ActivityReviewError("Recomputed source evidence does not agree with prior known inputs")
    anchored=[e for e in fauna_events if e["source_event_type"]=="sighting"
              and e["same_source_bin_has_strict_gpx_and_osm_alignment"]]
    identified_groups=[g for g in packet_source if g["review_priority_biological_observation_context"]]
    if len(anchored)!=99 or len(identified_groups)!=75 or len({e["candidate_id"] for e in anchored})!=94:
        raise ActivityReviewError("75 original review-group/99 direct-source anchor inventory mismatch")
    with (root/QC).open(newline="",encoding="utf-8-sig") as fh:
        quality={r["operational_night"]:r for r in csv.DictReader(fh)}
    matcher,source=load_osm_matcher(root)
    if source["historical_aug31_pre_exploration_available"] is not False:
        raise ActivityReviewError("OSM incorrectly treated as pre-exploration road truth")
    night_indexes={}
    for night in sorted({e["night"] for e in anchored}):
        night_indexes[night]=_verified_night_point_grid(root,night,quality[night])
    events=[]
    for sighting in anchored:
        events.append(_motion_context(sighting,night_indexes[sighting["night"]],matcher))
    if len(events)!=99 or len({e["source_block_sha256"] for e in events})!=99:
        raise ActivityReviewError("A strict sighting original source event was lost or repeated")
    by_group=defaultdict(list)
    for e in events:
        by_group[e["review_group_id"]].append(e)
    if len(by_group)!=75 or set(by_group)!={g["review_group_id"] for g in identified_groups}:
        raise ActivityReviewError("Not all 75 original review packets were retained")
    groups=[]
    for parent in identified_groups:
        group_id=parent["review_group_id"]
        matched=by_group[group_id]
        class_counts=Counter(e["local_motion_context"] for e in matched)
        if sum(class_counts.values())!=parent["strict_source_gpx_osm_sighting_anchor_count"]:
            raise ActivityReviewError("Sighting source counts disagree with existing review-group evidence")
        modes=set(class_counts)
        if "FAST_PASSAGE_NEAR_LOGGED_FAUNA" in modes:
            review="TRANSIT_COMPETES_WITH_LOGGED_FAUNA_OBSERVATION"
        elif any(k in modes for k in ("LOW_SPEED_MOVEMENT_NEAR_LOGGED_FAUNA",
                                     "STATIONARY_NEAR_LOGGED_FAUNA")):
            review="LOCAL_SLOW_OR_STOPPED_FAUNA_CONTEXT_PRIORITY"
        else:
            review="DIRECT_FAUNA_POINT_OBSERVATION_MOTION_UNRESOLVED"
        group={
            "review_group_id":group_id,
            "night":parent["night"],
            "source_review_window":parent["time_window"],
            "independent_original_fauna_note_count":len(matched),
            "source_event_block_sha256s":sorted(e["source_block_sha256"] for e in matched),
            "matched_candidate_ids":sorted({e["candidate_id"] for e in matched}),
            "speed_motion_classes":dict(sorted(class_counts.items())),
            "sum_actual_same_way_gpx_measured_pair_seconds":round(sum(e["measured_adjacent_same_way_gpx_pair_seconds"] for e in matched),2),
            "review_motion_priority":review,
            "priority_rank_score_for_review_only":(len(matched)*3+
                 sum(class_counts[m] for m in ("LOW_SPEED_MOVEMENT_NEAR_LOGGED_FAUNA",
                                               "STATIONARY_NEAR_LOGGED_FAUNA"))*2),
            "original_source_fauna_recorded_at_point":True,
            "local_speed_is_not_an_independent_research_validation":True,
            "independently_verified_habu_search_on_entire_road":False,
            "capture_result_ledger_complete":False,
            "source_proves_zero_habu_captures":False,
            "model_positive_rows":0,"model_negative_rows":0,
            "eligibility":"HUMAN_OR_INDEPENDENT_EVIDENCE_REQUIRED"
        }
        groups.append(group)
    groups.sort(key=lambda g:(-g["priority_rank_score_for_review_only"],g["night"],g["review_group_id"]))
    motion_counts=Counter(e["local_motion_context"] for e in events)
    group_counts=Counter(g["review_motion_priority"] for g in groups)
    if sum(motion_counts.values())!=99 or sum(group_counts.values())!=75:
        raise ActivityReviewError("Motion adjudication count mismatch")
    if any(e["training_label"] is not None or e["formal_negative_eligible"]
           or e["independently_certified_habu_targeted_search"] for e in events):
        raise ActivityReviewError("Illegal promotion of GPS-fauna evidence into scientific training")
    by_night=defaultdict(list)
    for group in groups:
        by_night[group["night"]].append(group)
    compact={
        "schema_version":"habu-august-fauna-75-review-packet-motion-audit-v1",
        "status":"SOURCE_LINKED_LOCAL_MOTION_CONTEXT_ONLY_NO_SEARCH_CREDENTIAL",
        "owner_confirmed_august_captures":47,
        "owner_confirmed_season_total_through_oct20":243,
        "source_native_habu_text_sha256":LIBRARY_RAW_SHA256,
        "prior_sighting_evidence_receipt_path":RECEIPT,
        "osm_auxiliary_source_sha256":source["osm_archive_sha256"],
        "source_osm_historical_exante_available":False,
        "original_sighting_source_statements_with_real_gpx":705,
        "source_strict_fauna_anchor_events_considered":len(events),
        "unique_strict_sighting_candidate_cells":94,
        "high_priority_original_review_packets":len(groups),
        "original_total_review_candidates_unmodified":3491,
        "original_total_review_packets_unmodified":774,
        "local_context_half_window_seconds":WINDOW_SECONDS,
        "gps_spatial_radius_from_sighting_m":SOURCE_RADIUS_METRES,
        "speed_classification_is_vehicle_motion_not_search_proof":True,
        "selection_bias_warning":"Original 3491 candidates were preselected partly using slow GPS speed. Reassessing speed on these same candidate cells is NOT independent evidence of Habu-focused searching.",
        "sighting_note_is_independent_source_modality_but_not_independent_witness":True,
        "motion_event_classes":dict(sorted(motion_counts.items())),
        "source_events_with_at_least_six_same_way_actual_gpx_fixes":sum(
            e["same_auxiliary_osm_way_gpx_points_in_window"]>=6 for e in events),
        "source_events_with_at_least_eight_seconds_measured_consecutive_gpx_pairs":sum(
            e["measured_adjacent_same_way_gpx_pair_seconds"]>=8 for e in events),
        "source_events_with_temporally_separated_same_cell_gpx_clusters":sum(
            e["source_100m_cell_gpx_time_clusters_not_confirmed_repeat_passes"]>=2 for e in events),
        "these_clusters_are_not_verified_repeat_passes":True,
        "review_packet_motion_classes":dict(sorted(group_counts.items())),
        "nights_with_strict_source_observations":[{
            "night":night,"priority_review_packets":len(group_list),
            "strict_original_sighting_events":sum(g["independent_original_fauna_note_count"] for g in group_list),
            "packets_with_low_or_stop_movement":sum(g["review_motion_priority"]=="LOCAL_SLOW_OR_STOPPED_FAUNA_CONTEXT_PRIORITY" for g in group_list),
            "packets_with_transit_conflict":sum(g["review_motion_priority"]=="TRANSIT_COMPETES_WITH_LOGGED_FAUNA_OBSERVATION" for g in group_list)
        } for night,group_list in sorted(by_night.items())],
        "road_search_units_independently_certified":0,
        "capture_outcome_completeness_certified":False,
        "individual_capture_id_independently_verified":False,
        "formal_positive_training_rows":0,
        "formal_negative_training_rows":0,
        "all_review_group_observations_remain_unknown":True,
        "official_training_eligible":False,
        "evidence_limits":[
            "Wildlife sightings directly evidence only the original point observation",
            "GPS slow/stationary or repeated time clusters do not attest Habu-directed road search",
            "Fast movement may coexist with sighting and does not erase original observation",
            "The 75 group IDs are review partitions, never confirmed road traversals or captures",
            "Capture-result completeness must be independently proven per spatial/time scope",
            "OSM September source is retrospective auxiliary not historical frozen road universe"
        ],
        "priority_group_ids_without_spatial_data":[g["review_group_id"] for g in groups]
    }
    return compact,groups,events

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--output",type=Path,default=Path("artifacts/august-75-fauna-review"))
    args=parser.parse_args()
    summary,groups,events=audit_priority_packets(args.root)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"aggregate.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.output/"75_group_motion_review_private.json").write_text(json.dumps(groups,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.output/"99_source_anchor_motion_review_private.json").write_text(json.dumps(events,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "review_packets":len(groups),
        "source_fauna_anchor_events":len(events),
        "vehicle_motion_classes":summary["motion_event_classes"],
        "packet_review_classes":summary["review_packet_motion_classes"],
        "actual_habu_search_certified":0,
        "training_positives":0,"training_negatives":0
    },ensure_ascii=False))
if __name__=="__main__":
    main()
