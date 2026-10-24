#!/usr/bin/env python3
"""Evidence-only join of August fauna sightings with actual GPX and auxiliary OSM roads.

A contemporaneous animal sighting is direct evidence that something was observed
at the recorded place, NOT that an entire road/100m/10min zone was searched or
that Habu were absent. All existing noncapture candidate labels stay UNKNOWN.
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
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from audit_august_native_capture_original import LIBRARY_RAW_SHA256,LIBRARY_RAW_BYTES,SOURCE
from audit_august_sampled_exposure import NIGHTS
from audit_aug31_road_search_candidates import _time_window,load_osm_matcher,JST
from build_august_source_evidence_packets import build_packets
from gpx_audit import parse_gpx,utm52n,night_date_for_time
from recover_remaining_august_nights import index_events,_clock,_night,_coordinates

QC_PATH="evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv"
ANCHOR_MAX_SECONDS=600
ANCHOR_MAX_METRES=100.0
STRICT_MAX_SECONDS=90
STRICT_MAX_METRES=35.0

class SightingEvidenceError(ValueError):
    pass

_MERGED_LINE=re.compile(r"(?m)^あ(2026/(?:08|09)/\d\d \d{1,2}:\d\d)[ \t]*\n[ \t]*目撃[ \t]*$")

def _restore_embedded_native_sighting(parent:dict,segment:str,line:int,parent_side:str,*,raw_span:str|None=None)->dict:
    """Derive one original observation from an exact parent source byte span."""
    # Parsing may strip the stray source prefix; SHA must bind the original span.
    raw_source_span=raw_span if raw_span is not None else segment
    nonempty=[v.strip() for v in segment.splitlines() if v.strip()]
    if len(nonempty)<5 or nonempty[1]!="目撃":
        raise SightingEvidenceError("Embedded sighting structure does not match source")
    when=_clock(nonempty[0])
    positions=[i for i,v in enumerate(nonempty) if re.fullmatch(r"\d+匹(以上)?",v)]
    if len(positions)!=1 or positions[0]+1>=len(nonempty):
        raise SightingEvidenceError("Embedded source sighting quantity/category ambiguous")
    coords=_coordinates(nonempty)
    if coords is None:
        raise SightingEvidenceError("Embedded original sighting lacks unique coordinates")
    return {
        **parent,
        "operational_night":_night(when),
        "source_line":line,
        "timestamp_native":nonempty[0],
        "timestamp_interpreted_jst":when.isoformat(),
        "event_type":"sighting",
        "quantity_literal":nonempty[positions[0]],
        "species_or_native_note":nonempty[positions[0]+1],
        "coordinates":{"latitude":coords[0],"longitude":coords[1]},
        "block_sha256":hashlib.sha256(raw_source_span.encode("utf-8")).hexdigest(),
        "source_block":raw_source_span,
        "source_parse_stripped_spurious_prefix":raw_span is not None,
        "original_parent_block_sha256":parent["block_sha256"],
        "recovery_kind":"EXACT_NATIVE_BYTE_SPAN_COMPOUND_SIGHTING",
        "recovery_span_part":parent_side,
    }

def restore_compound_sighting_blocks(original_events:list[dict])->tuple[list[dict],list[dict]]:
    """Repair a pasted source line starting 'あ2026/...' without editing native TXT.

    Require exactly a complete leading sighting and a complete trailing sighting
    with their own literal timestamps and coordinates. Never interpret chat
    comments like 'なう(2026/...' as encounter timestamps.
    """
    recovered=[]
    notes=[]
    for e in original_events:
        if e["event_type"]!="sighting" or "あ2026/" not in e["source_block"]:
            recovered.append(e)
            continue
        matches=list(_MERGED_LINE.finditer(e["source_block"]))
        if len(matches)!=1:
            raise SightingEvidenceError("Multiple/unresolved compound sighting splits")
        marker=matches[0]
        prefix=e["source_block"][:marker.start()]
        suffix=e["source_block"][marker.start()+len("あ"):]
        if not prefix.strip() or not suffix.strip():
            raise SightingEvidenceError("Empty exact native sighting source span")
        left=_restore_embedded_native_sighting(e,prefix,e["source_line"],"BEFORE_EMBEDDED_TIMESTAMP")
        second_line=e["source_line"]+prefix.count("\n")
        right=_restore_embedded_native_sighting(e,suffix,second_line,"AFTER_STRAY_SOURCE_A",raw_span=e["source_block"][marker.start():])
        if left["operational_night"]!=right["operational_night"] or left["timestamp_native"]==right["timestamp_native"]:
            raise SightingEvidenceError("Compound sighting night/clock malformed")
        recovered.extend((left,right))
        notes.append({
            "original_parent_block_sha256":e["block_sha256"],
            "original_parent_first_source_line":e["source_line"],
            "embedded_marker_source_line":second_line,
            "recovered_two_source_timestamp_lines":[left["timestamp_native"],right["timestamp_native"]],
            "two_distinct_coordinate_pairs_in_native_block":True,
            "native_original_bytes_modified":False,
            "field_device_authentication_inferred":False,
            "operation":"SPLIT_SINGLE_COMPOUND_SOURCE_BLOCK_INTO_TWO_EXPLICIT_SIGHTINGS",
        })
    return recovered,notes

def source_category(source_event:dict)->tuple[str,str|None]:
    """Keep source's literal organism category, never infer Habu from all sightings."""
    kind=source_event["event_type"]
    if kind=="roadkill":
        return "ROADKILL_NOT_A_SIGHTING",source_event["species_or_native_note"]
    if kind=="sighting":
        native=source_event.get("species_or_native_note")
        if not isinstance(native,str) or not native.strip():
            return "UNCLASSIFIED_SIGHTING",native
        normalized=native.strip()
        if normalized=="ハブ":
            return "HABU_SIGHTING",normalized
        if normalized=="ヒメハブ":
            return "HIMEHABU_SIGHTING_NOT_HABU",normalized
        return "OTHER_FAUNA_SIGHTING",normalized
    return "NOT_FAUNA_SIGHTING",source_event.get("species_or_native_note")

def _source_night_boundaries(events:list[dict])->tuple[datetime|None,datetime|None]:
    starts=[datetime.fromisoformat(e["timestamp_interpreted_jst"]) for e in events if e["event_type"]=="exploration_start"]
    ends=[datetime.fromisoformat(e["timestamp_interpreted_jst"]) for e in events if e["event_type"]=="exploration_end"]
    if len(starts)==1 and len(ends)==1 and starts[0]<ends[0]:
        return starts[0],ends[0]
    return None,None

def load_verified_points(root:Path,night:str, qc:dict)->list[dict]:
    path=root/f"data/raw/gpx/{night}__legacy.gpx"
    if hashlib.sha256(path.read_bytes()).hexdigest()!=qc["sha256"]:
        raise SightingEvidenceError(f"Actual GPX original SHA mismatch for {night}")
    points=parse_gpx(path)
    if len(points)!=int(qc["gps_points"]):
        raise SightingEvidenceError(f"Actual GPX point count mismatch for {night}")
    if any(night_date_for_time(p["time_utc"])!=night for p in points):
        raise SightingEvidenceError(f"Actual GPX JST 07:00 night mismatch for {night}")
    valid=[]
    for p in points:
        if p.get("exclude_point") or (p["hdop"] is not None and p["hdop"]>10):
            continue
        x,y=utm52n(p["latitude"],p["longitude"])
        valid.append({"time_utc":p["time_utc"],"x":x,"y":y,
                      "hdop":p.get("hdop"),"speed_mps":p.get("speed_mps"),
                      "source_gpx":path.relative_to(root).as_posix(),
                      "sample_utm_cell":[math.floor(x/100),math.floor(y/100)],
                      "sample_10min_window":_time_window(p["time_utc"])})
    if any(a["time_utc"]>b["time_utc"] for a,b in zip(valid,valid[1:])):
        raise SightingEvidenceError(f"GPX time regressed {night}")
    return valid

def nearest_gpx(event:dict, valid:list[dict], times:list[datetime], matcher)->dict:
    """Time-first proximity within source-actual ±10m and 100m, no interpolation."""
    loc=event.get("coordinates")
    if not loc:
        return {"status":"NO_SOURCE_EVENT_COORDINATE","seconds_offset":None,
                "metres_offset":None,"same_original_100m_10min_bin":False,
                "auxiliary_osm_same_way":False,"strict_gps_source_alignment":False}
    target=datetime.fromisoformat(event["timestamp_interpreted_jst"]).astimezone(timezone.utc)
    x,y=utm52n(float(loc["latitude"]),float(loc["longitude"]))
    lo=bisect.bisect_left(times,target-timedelta(seconds=ANCHOR_MAX_SECONDS))
    hi=bisect.bisect_right(times,target+timedelta(seconds=ANCHOR_MAX_SECONDS))
    best=None
    for p in valid[lo:hi]:
        # No GPS segment interpolation. Compare source coordinate to actual points.
        if abs(p["x"]-x)>ANCHOR_MAX_METRES or abs(p["y"]-y)>ANCHOR_MAX_METRES:
            continue
        dist=math.hypot(p["x"]-x,p["y"]-y)
        if dist>ANCHOR_MAX_METRES:
            continue
        sec=abs((p["time_utc"]-target).total_seconds())
        rank=(round(sec,3),round(dist,3),p["time_utc"].isoformat())
        if best is None or rank<best[0]:
            best=(rank,p,sec,dist)
    if best is None:
        return {"status":"NO_ACTUAL_GPX_WITHIN_100M_10MIN",
                "seconds_offset":None,"metres_offset":None,
                "same_original_100m_10min_bin":False,"auxiliary_osm_same_way":False,
                "strict_gps_source_alignment":False}
    _,matched,sec,dist=best
    road_event=matcher.match_xy(x,y)
    road_gpx=matcher.match_xy(matched["x"],matched["y"])
    same_way=bool(road_event["status"]=="AUXILIARY_ROAD_MATCH_REVIEW" and
                  road_gpx["status"]=="AUXILIARY_ROAD_MATCH_REVIEW" and
                  road_event["way_id"]==road_gpx["way_id"])
    known_good_hdop=matched["hdop"] is not None and 0<=matched["hdop"]<=10
    strict=(sec<=STRICT_MAX_SECONDS and dist<=STRICT_MAX_METRES and known_good_hdop)
    bin_event=(math.floor(x/100),math.floor(y/100),_time_window(target))
    bin_gpx=(matched["sample_utm_cell"][0],matched["sample_utm_cell"][1],
             matched["sample_10min_window"])
    exact_bin=bin_event==bin_gpx
    return {
        "status":"CLOSE_GPX_SOURCE_OBSERVATION" if strict else "BROAD_GPX_SPACETIME_ONLY",
        "seconds_offset":round(sec,3),
        "metres_offset":round(dist,2),
        "gps_timestamp_utc":matched["time_utc"].isoformat(),
        "gps_hdop":matched["hdop"],
        "gps_speed_source_mps":matched["speed_mps"],
        "gps_point_strict_accuracy_screen":known_good_hdop,
        "same_original_100m_10min_bin":exact_bin,
        "strict_gps_source_alignment":strict,
        "source_osm_road_status":road_event["status"],
        "gps_osm_road_status":road_gpx["status"],
        "auxiliary_osm_same_way":same_way,
        "source_osm_way_candidate":road_event["way_id"] if road_event["status"]=="AUXILIARY_ROAD_MATCH_REVIEW" else None,
        "gps_osm_way_candidate":road_gpx["way_id"] if road_gpx["status"]=="AUXILIARY_ROAD_MATCH_REVIEW" else None,
        "road_alignment_is_retrospective_auxiliary_only":True,
    }

def _event_key(source_event:dict)->tuple:
    loc=source_event["coordinates"]
    x,y=utm52n(loc["latitude"],loc["longitude"])
    t=datetime.fromisoformat(source_event["timestamp_interpreted_jst"])
    return (source_event["operational_night"],math.floor(x/100),math.floor(y/100),_time_window(t))

def analyze_sightings(root:Path=ROOT, *, matcher=None, matcher_evidence=None,
                      packets=None)->tuple[dict,list[dict],list[dict]]:
    root=Path(root)
    native_data=(root/SOURCE).read_bytes()
    if len(native_data)!=LIBRARY_RAW_BYTES or hashlib.sha256(native_data).hexdigest()!=LIBRARY_RAW_SHA256:
        raise SightingEvidenceError("Aug native Library TXT exact source no longer matches")
    raw_index_events=index_events(native_data.decode("utf-8"))
    all_events,source_recovery=restore_compound_sighting_blocks(raw_index_events)
    selected=set(NIGHTS)
    august=[e for e in all_events if "2026-08-01"<=e["operational_night"]<="2026-08-31"]
    selected_events=[e for e in august if e["operational_night"] in selected]
    sightings=[e for e in selected_events if e["event_type"]=="sighting"]
    roadkills=[e for e in selected_events if e["event_type"]=="roadkill"]
    all_aug_sightings=[e for e in august if e["event_type"]=="sighting"]
    original_index_sightings=sum(e["event_type"]=="sighting" and
                                "2026-08-01"<=e["operational_night"]<="2026-08-31" for e in raw_index_events)
    original_index_sightings_with_gpx=sum(e["event_type"]=="sighting" and e["operational_night"] in selected for e in raw_index_events)
    if (len(source_recovery)!=1 or original_index_sightings!=915 or
            original_index_sightings_with_gpx!=704 or len(sightings)!=705 or
            len(all_aug_sightings)!=916 or len(roadkills)!=11):
        raise SightingEvidenceError("Native sighting/source compound block inventory changed")
    if len({e["block_sha256"] for e in sightings})!=len(sightings):
        raise SightingEvidenceError("Duplicate sighting event source blocks")
    if matcher is None:
        matcher,matcher_evidence=load_osm_matcher(root)
    if matcher_evidence is None:
        matcher_evidence={"road_source":"TEST_ONLY","historical_aug31_pre_exploration_available":False}
    if packets is None:
        packet_summary,review_groups,review_cells=build_packets(root)
    else:
        packet_summary,review_groups,review_cells=packets
    if packet_summary["noncapture_review_candidate_cells"]!=3491 or len(review_cells)!=3491:
        raise SightingEvidenceError("Review candidate universe changed")
    review_by_key={}
    for cell in review_cells:
        key=(cell["night"],cell["cell_x"],cell["cell_y"],cell["window_start_jst"])
        if key in review_by_key:
            raise SightingEvidenceError("Duplicate GPS candidate key")
        review_by_key[key]=cell
    group_for_candidate={}
    for group in review_groups:
        for cid in group["member_candidate_ids"]:
            if cid in group_for_candidate:
                raise SightingEvidenceError("Candidate in multiple review groups")
            group_for_candidate[cid]=group["review_group_id"]
    if set(group_for_candidate)!={c["candidate_id"] for c in review_cells}:
        raise SightingEvidenceError("Group membership does not match original 3491 review candidates")

    original_qa={}
    with (root/QC_PATH).open(encoding="utf-8-sig",newline="") as f:
        original_qa={r["operational_night"]:r for r in csv.DictReader(f)}
    indexed=defaultdict(list)
    for e in selected_events:
        indexed[e["operational_night"]].append(e)
    day_rows=[]
    event_rows=[]
    grouped_sightings=defaultdict(list)
    for night in NIGHTS:
        events=indexed[night]
        day_sightings=[e for e in events if e["event_type"]=="sighting"]
        day_roadkills=[e for e in events if e["event_type"]=="roadkill"]
        valid=load_verified_points(root,night,original_qa[night])
        timestamps=[p["time_utc"] for p in valid]
        start,end=_source_night_boundaries(events)
        matching=Counter()
        category_counts=Counter()
        candidate_overlap=0
        strong_overlap=0
        source_bin_overlap=0
        strict_matched=0
        road_aligned=0
        event_near=0
        for e in day_sightings+day_roadkills:
            typ,note=source_category(e)
            match=nearest_gpx(e,valid,timestamps,matcher)
            key=_event_key(e) if e["coordinates"] else None
            candidate=review_by_key.get(key)
            same_bin=bool(match.get("same_original_100m_10min_bin"))
            strong=bool(candidate is not None and
                        match["strict_gps_source_alignment"] and
                        same_bin and match["auxiliary_osm_same_way"] and
                        match.get("source_osm_way_candidate")==candidate["osm_way_candidate"] and
                        start is not None and
                        start<=datetime.fromisoformat(e["timestamp_interpreted_jst"])<=end)
            if e["event_type"]=="sighting":
                category_counts[typ]+=1
                matching[match["status"]]+=1
                source_bin_overlap+=int(candidate is not None)
                strong_overlap+=int(strong)
                strict_matched+=int(match["strict_gps_source_alignment"])
                road_aligned+=int(match["auxiliary_osm_same_way"])
                event_near+=int(match["status"]!="NO_ACTUAL_GPX_WITHIN_100M_10MIN" and match["status"]!="NO_SOURCE_EVENT_COORDINATE")
                candidate_overlap+=int(candidate is not None)
                if strong:
                    grouped_sightings[candidate["candidate_id"]].append(e["block_sha256"])
            event_rows.append({
                "night":night,
                "source_block_sha256":e["block_sha256"],
                "source_line":e["source_line"],
                "original_merged_source_parent_sha256":e.get("original_parent_block_sha256"),
                "sighting_recovery_kind":e.get("recovery_kind"),
                "timestamp_native":e["timestamp_native"],
                "source_coordinates":e["coordinates"],  # private Actions artifact ONLY
                "source_event_type":e["event_type"],
                "organism_note_exact":note,
                "category":typ,
                "quantity_literal_from_source":e.get("quantity_literal"),
                "log_session_has_paired_start_end":start is not None,
                "source_event_within_recorded_session":(
                    start<=datetime.fromisoformat(e["timestamp_interpreted_jst"])<=end
                    if start is not None else None),
                "same_source_100m_10min_review_candidate":candidate is not None,
                "candidate_id":candidate["candidate_id"] if candidate else None,
                "candidate_review_group_id":group_for_candidate.get(candidate["candidate_id"]) if candidate else None,
                "same_source_bin_has_strict_gpx_and_osm_alignment":strong,
                "gpx":match,
                "source_note_is_not_independent_witness_authentication":True,
                "observation":"UNKNOWN",
                "training_label":None,
                "confirmed_search_effort_for_entire_road_segment":False,
                "capture_outcome_ledger_complete":False
            })
        day_rows.append({
            "night":night,
            "source_sighting_statements":len(day_sightings),
            "roadkill_separate_reaction_statements":len(day_roadkills),
            "gps_original_points":int(original_qa[night]["gps_points"]),
            "gps_quality_retained_samples":len(valid),
            "paired_session":start is not None,
            "sightings_with_gpx_within_100m_10min":event_near,
            "sightings_strict_within_35m_90s_and_known_hdop":strict_matched,
            "sightings_unambiguously_near_same_auxiliary_osm_way":road_aligned,
            "sighting_source_bin_in_original_3491_candidate_cells":source_bin_overlap,
            "sighting_source_bin_strict_gpx_same_way_and_session":strong_overlap,
            "sighting_categories":dict(sorted(category_counts.items())),
            "gpx_match_status_counts":dict(sorted(matching.items())),
            "scientifically_certified_active_road_search_segments":0,
            "formally_approved_noncapture_training_labels":0
        })
    if len(event_rows)!=len(sightings)+len(roadkills):
        raise SightingEvidenceError("Event encounter rows lost")
    if sum(r["source_sighting_statements"] for r in day_rows)!=705:
        raise SightingEvidenceError("Source sightings not fully accounted")
    if sum(r["roadkill_separate_reaction_statements"] for r in day_rows)!=11:
        raise SightingEvidenceError("Roadkill source reactions lost")
    if any(e["training_label"] is not None or e["observation"]!="UNKNOWN" for e in event_rows):
        raise SightingEvidenceError("Unverified animal observations promoted to labels")

    category=Counter(e["category"] for e in event_rows if e["source_event_type"]=="sighting")
    species=Counter(e["organism_note_exact"] for e in event_rows if e["source_event_type"]=="sighting")
    overlaps={c["candidate_id"]:c for c in review_cells if c["candidate_id"] in grouped_sightings}
    unique_groups={group_for_candidate[cid] for cid in overlaps}
    packet_context=[]
    for g in review_groups:
        sightings_at=[(cid,grouped_sightings[cid]) for cid in g["member_candidate_ids"] if cid in grouped_sightings]
        packet_context.append({
            "review_group_id":g["review_group_id"],
            "night":g["night"],
            "time_window":g["window_start_jst"],
            "source_matched_fauna_sighting_blocks":[sha for _,blocks in sightings_at for sha in blocks],
            "strict_source_gpx_osm_sighting_anchor_count":sum(len(blocks) for _,blocks in sightings_at),
            "review_priority_biological_observation_context":bool(sightings_at),
            "search_effort_certified":False,
            "noncapture_training_eligible":False,
            "review_status":"SOURCE_SIGHTING_CONTEXT_ONLY"
        })
    summary={
        "schema_version":"habu-august-fauna-original-gpx-auxiliary-road-evidence-v1",
        "source":{"user_native_txt_byte_sha256":LIBRARY_RAW_SHA256,
                  "user_native_txt_exact_bytes_verified":True,
                  "original_field_device_signed_witness":False,
                  "source_compound_event_repairs":source_recovery,
                  "original_timestamp_line_sighting_blocks_in_august":original_index_sightings,
                  "original_timestamp_line_sighting_blocks_with_actual_gpx":original_index_sightings_with_gpx,
                  "source_path":SOURCE,
                  "original_gpx_qc_csv_path":QC_PATH,
                  "osm_archive_sha256":matcher_evidence.get("osm_archive_sha256"),
                  "osm_centerlines_sha256":matcher_evidence.get("osm_centerline_member_sha256"),
                  "osm_used_only_retrospectively":True},
        "scope":{"actual_gpx_nights":12,
                 "august_source_sighting_statements_all_nights":len(all_aug_sightings),
                 "source_sighting_statements_with_actual_gpx_nights":len(sightings),
                 "roadkill_reaction_statements_with_actual_gpx_nights":len(roadkills),
                 "existing_review_candidate_cells":len(review_cells),
                 "existing_review_packets":len(review_groups),
                 "owner_confirmed_monthly_captures":47},
        "totals":{
            "source_sightings":len(sightings),
            "native_compound_sighting_repairs":len(source_recovery),
            "sightings_matched_100m_10min_actual_gpx":sum(r["sightings_with_gpx_within_100m_10min"] for r in day_rows),
            "sightings_strict_35m_90s_known_hdop":sum(r["sightings_strict_within_35m_90s_and_known_hdop"] for r in day_rows),
            "sightings_matching_same_unambiguous_auxiliary_osm_way":sum(r["sightings_unambiguously_near_same_auxiliary_osm_way"] for r in day_rows),
            "original_non_capture_candidate_cell_overlapping_sighting_source_bin":len({e["candidate_id"] for e in event_rows if e["source_event_type"]=="sighting" and e["candidate_id"]}),
            "candidate_cells_with_strict_same_gpx_osm_sighting_observation":len(overlaps),
            "candidate_review_groups_with_strict_fauna_observation":len(unique_groups),
            "strict_sighting_anchor_event_count_in_candidate_cells":sum(len(v) for v in grouped_sightings.values()),
            "roadkill_entries_not_misclassified_as_sightings":len(roadkills),
            "habu_roadkill_reactions_separate_from_captures":sum(e["species_or_native_note"]=="ハブ" for e in roadkills),
            "sightings_with_missing_unique_source_coordinate":sum(e["coordinates"] is None for e in sightings),
            "all_organism_field_notes_distinct":len(species),
            "habu_sightings_explicit":category["HABU_SIGHTING"],
            "himehabu_sightings_distinct":category["HIMEHABU_SIGHTING_NOT_HABU"],
            "other_fauna_sightings":category["OTHER_FAUNA_SIGHTING"],
            "unknown_species_sightings":category["UNCLASSIFIED_SIGHTING"],
            "scientifically_certified_road_search_segments":0,
            "scientific_positive_training_rows_added":0,
            "scientific_negative_training_rows_added":0
        },
        "sighting_categories":dict(sorted(category.items())),
        "top_source_organism_notes":dict(species.most_common(24)),
        "by_night":day_rows,
        "explicit_non_inferences":[
            "Wildlife sighting is a site-specific observer field note, not full-100m continuous search proof",
            "Sighted frogs, birds and rodents are not direct evidence of Habu present or absent",
            "Himehabu is not classified as owner-captured Habu",
            "OSM September-25 auxiliary archive is not pre-August-31 P0 input",
            "GPS proximity is not independent witness or source-device authentication",
            "Missing sightings or capture records are not automatic zero observations",
            "No authenticated all-captures-complete ledger by searched road segment",
        ],
        "evidence_state":"ACTUAL_SIGHTING_FIELD_NOTES_LINKED_TO_GPXSOURCE_OSM__TRAINING_BLOCKED",
        "scientific_training_eligible":False
    }
    return summary,event_rows,packet_context

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--output",type=Path,default=Path("artifacts/august-fauna-context"))
    args=parser.parse_args()
    summary,events,groups=analyze_sightings(args.root)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # All source coordinates, precise times and way IDs stay in PRIVATE 7-day CI artifact.
    (args.output/"source_sighting_gpx_road_private.json").write_text(json.dumps(events,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.output/"packet_sighting_context_private.json").write_text(json.dumps(groups,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "sighting_source_statements":summary["totals"]["source_sightings"],
        "native_compound_source_repairs":summary["totals"]["native_compound_sighting_repairs"],
        "gpx_matched":summary["totals"]["sightings_matched_100m_10min_actual_gpx"],
        "strict_gpx_anchor":summary["totals"]["sightings_strict_35m_90s_known_hdop"],
        "same_auxiliary_road":summary["totals"]["sightings_matching_same_unambiguous_auxiliary_osm_way"],
        "review_candidate_cells_with_strict_sighting_observation":summary["totals"]["candidate_cells_with_strict_same_gpx_osm_sighting_observation"],
        "review_groups_with_strict_observation":summary["totals"]["candidate_review_groups_with_strict_fauna_observation"],
        "roadkill_separate":summary["totals"]["roadkill_entries_not_misclassified_as_sightings"],
        "formal_negative":0,"formal_positive":0},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
