#!/usr/bin/env python3
"""Bundle already-observed August noncapture candidates into auditable review packets.

This is an evidential triage queue, NEVER a training label compiler. Even an
authenticated raw field log cannot prove uninterrupted active road searching.
All packet classifications remain UNKNOWN until independently supplied proof.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from audit_aug31_road_search_candidates import analyze as analyze31,load_osm_matcher
from audit_remaining_august_road_candidates import analyze_remaining
from audit_august_native_capture_original import audit_original,LIBRARY_RAW_SHA256

BASIS_RECEIPTS=(
    "evidence/recovered_sources/2026-08-31-road-search-candidate-ci-receipt.json",
    "evidence/recovered_sources/2026-08-remaining-11-road-search-review-ci-receipt.json",
    "evidence/recovered_sources/2026-08-native-original-library-byte-proof.json",
)
BLOCKERS=(
    "ACTIVE_SEARCH_VS_TRANSPORT_NOT_INDEPENDENTLY_PROVEN",
    "COMPLETE_CAPTURE_OUTCOME_LEDGER_NOT_ESTABLISHED",
    "CANONICAL_CAPTURE_INDIVIDUAL_IDS_NOT_VERIFIED",
    "RETROSPECTIVE_OSM_AUXILIARY_NOT_EX_ANTE_PREDICTION_UNIVERSE",
)
class PacketAuditError(ValueError):
    pass

def _digest(text:str)->str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _normalized(row:dict,*,night:str,src_sha:str)->dict|None:
    aug31=night=="2026-08-31"
    if aug31:
        is_candidate=row.get("noncapture_candidate")=="NO_OWNER_CAPTURE_RECORDED_REVIEW"
        way=row.get("osm_way_id_candidate")
        samples=row.get("sample_count")
        road_samples=row.get("road_matched_samples")
        events=row.get("event_nearby")
        role=row.get("activity_candidate")
    else:
        is_candidate=row.get("noncapture_review_candidate") is True
        way=row.get("osm_way_candidate")
        samples=row.get("samples")
        road_samples=row.get("sampled_road_matches")
        events=row.get("nearby_habu_event")
        role=row.get("activity_candidate")
    if not is_candidate:
        return None
    if way is None or events!="NONE_RECORDED" or role!="LIKELY_SLOW_SEARCH_REVIEW":
        raise PacketAuditError("Review candidate has unresolved animal context or no road identity")
    x,y,window=int(row["cell_x"]),int(row["cell_y"]),row["window_start_jst"]
    if samples<=0 or road_samples<=0 or road_samples>samples:
        raise PacketAuditError("Invalid candidate GPX/OSM evidence counts")
    identity=_digest(f"august-review-v1|{night}|{src_sha}|{x}|{y}|{window}|{way}")[:24]
    return {
        "candidate_id":identity,"night":night,"cell_x":x,"cell_y":y,
        "window_start_jst":window,"osm_way_candidate":way,
        "quality_gpx_samples":samples,"osm_road_nearby_samples":road_samples,
        "source_gpx_sha256":src_sha,
        "source_habu_txt_sha256":LIBRARY_RAW_SHA256,
        "native_txt_source_verified":True,
        "field_search_road_attested":False,
        "complete_night_outcome_attested":False,
        "canonical_capture_individual_ids_verified":False,
        "observation":"UNKNOWN","label":None,
        "review_disposition":"PENDING_INDEPENDENT_SEARCH_AND_CAPTURE_COVERAGE_PROOF",
    }

def _build_groups(cells:list[dict])->list[dict]:
    # Spatial adjacency in a single 10-minute window and same OSM way is a
    # review grouping, not a claim that those roads were continuously driven.
    partitions=defaultdict(list)
    for cell in cells:
        partitions[(cell["night"],cell["window_start_jst"],cell["osm_way_candidate"])].append(cell)
    groups=[]
    for (night,window,way),items in sorted(partitions.items()):
        positions={(r["cell_x"],r["cell_y"]):r for r in items}
        if len(positions)!=len(items):
            raise PacketAuditError("Duplicate sampled cells within one source road/time partition")
        unvisited=set(positions)
        while unvisited:
            seed=min(unvisited)
            todo=deque([seed])
            unvisited.remove(seed)
            component=[]
            while todo:
                cell=todo.popleft()
                component.append(positions[cell])
                cx,cy=cell
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        other=(cx+dx,cy+dy)
                        if other in unvisited:
                            unvisited.remove(other)
                            todo.append(other)
            component.sort(key=lambda x:(x["cell_x"],x["cell_y"],x["candidate_id"]))
            member_ids=[c["candidate_id"] for c in component]
            group_id="AGRP-"+_digest("|".join([night,window,str(way),*member_ids]))[:22]
            sample_sum=sum(c["quality_gpx_samples"] for c in component)
            matched_sum=sum(c["osm_road_nearby_samples"] for c in component)
            groups.append({
                "review_group_id":group_id,"night":night,"window_start_jst":window,
                "candidate_osm_way_id":way,
                "spatially_adjacent_sampled_cells":len(component),
                "native_gpx_samples":sample_sum,
                "osm_matched_gpx_samples":matched_sum,
                "member_candidate_ids":member_ids,
                "sampled_cell_coordinates": [[c["cell_x"],c["cell_y"]] for c in component],
                "spatial_grouping_only_not_proven_driven_route":True,
                "owner_search_effort_proof":"NOT_YET_INDEPENDENTLY_VERIFIED",
                "complete_capture_outcome_proof":"NOT_YET_ESTABLISHED",
                "canonical_individual_event_proof":"NOT_YET_ESTABLISHED",
                "promoted_model_negative_count":0,
                "review_status":"REVIEW_REQUIRED",
                "priority_score_for_review_only":matched_sum+3*len(component)
            })
    groups.sort(key=lambda g:(-g["priority_score_for_review_only"],g["night"],g["review_group_id"]))
    if len(groups)!=len({g["review_group_id"] for g in groups}):
        raise PacketAuditError("Review group ID collision")
    if sum(g["spatially_adjacent_sampled_cells"] for g in groups)!=len(cells):
        raise PacketAuditError("Review grouping loses or duplicates candidate cells")
    return groups

def build_packets(root:Path=ROOT)->tuple[dict,list[dict],list[dict]]:
    root=Path(root)
    native_report,captured_events=audit_original(root)
    proof=json.loads((root/BASIS_RECEIPTS[2]).read_text(encoding="utf-8"))
    if (proof.get("verification_result")!="EXACT_SOURCE_BYTES_IDENTICAL" or
            proof["user_uploaded_native_source"]["native_raw_sha256"]!=LIBRARY_RAW_SHA256 or
            proof["user_uploaded_native_source"]["native_raw_size_bytes"]!=116496):
        raise PacketAuditError("Independent native Library-byte verification receipt missing or invalid")
    if native_report["repository_source"]["sha256"]!=LIBRARY_RAW_SHA256:
        raise PacketAuditError("Native source audit does not agree with user original")
    if native_report["native_capture_statement_quantity_sum"]!=47 or len(captured_events)!=46:
        raise PacketAuditError("Owner-confirmed full-month capture source reconciliation changed")

    matcher,osm_info=load_osm_matcher(root)
    r31,rows31=analyze31(root,matcher=matcher,osm_evidence=osm_info)
    r11,rows11=analyze_remaining(root,matcher=matcher,matcher_evidence=osm_info)
    if r31["sampled_100m_10min_units"]!=688 or r11["sampled_spacetime_unit_count"]!=8277:
        raise PacketAuditError("GPX sampled cell universe changed")
    if r31["noncapture_review_candidate_count"]!=426 or r11["review_noncapture_candidate_count"]!=3065:
        raise PacketAuditError("Versioned noncapture review candidates no longer match source CI")

    r31source=json.loads((root/BASIS_RECEIPTS[0]).read_text(encoding="utf-8"))
    r11source=json.loads((root/BASIS_RECEIPTS[1]).read_text(encoding="utf-8"))
    if r31source["summary"]["noncapture_review_candidates"]!=426 or r11source["counts"]["noncapture_review_candidates"]!=3065:
        raise PacketAuditError("Frozen prior real-source receipts disagree")
    sha31=r31["input_provenance"]["gpx_sha256"]
    by_night_sha={x["night"]:x["gpx_sha256"] for x in r11["nightly_reports"]}
    cells=[row for row in (_normalized(r,night="2026-08-31",src_sha=sha31) for r in rows31) if row]
    for row in rows11:
        source=by_night_sha[row["night"]]
        c=_normalized(row,night=row["night"],src_sha=source)
        if c:cells.append(c)
    if len(cells)!=3491 or len({c["candidate_id"] for c in cells})!=3491:
        raise PacketAuditError("Candidate count/identity drift")
    # Explicit zero-capture note on Aug21 remains unqualified and cannot be
    # laundered into a complete denominator from source-file presence.
    if any(c["label"] is not None or c["observation"]!="UNKNOWN" for c in cells):
        raise PacketAuditError("Unverified noncapture became training label")

    groups=_build_groups(cells)
    bynight=Counter(c["night"] for c in cells)
    groups_night=Counter(g["night"] for g in groups)
    month={"2026-08":47}
    night_rows=[]
    for night in sorted(set(bynight)|{x["night"] for x in r11["nightly_reports"]}|{"2026-08-31"}):
        owner=next((d for d in native_report["day_counts"] if d["night"]==night),None)
        night_rows.append({
            "night":night,"review_candidate_cells":bynight.get(night,0),
            "review_packets":groups_night.get(night,0),
            "native_capture_statements":owner["source_capture_events"] if owner else 0,
            "source_statement_quantity":owner["native_statement_quantity"] if owner else None,
            "owner_day_total":owner["owner_confirmed_day_count"] if owner else None,
            "road_search_proof_certified":False,
            "complete_capture_outcomes_certified":False,
            "negative_training_labels":0,
        })
    # Aggregate-only data can be committed. Coordinates and OSM IDs in the
    # full packet/observed cell files are private short-lived CI artifacts.
    summary={
        "schema_version":"habu-august-scientific-evidence-packet-queue-v1",
        "source_provenance":{
            "owner_native_txt_byte_matched_sha256":LIBRARY_RAW_SHA256,
            "native_file_bytes_verified":True,
            "source_event_statements":native_report["native_capture_event_statements"],
            "source_statement_capture_quantity":native_report["native_capture_statement_quantity_sum"],
            "all_17_night_capture_counts_match_owner_confirmed":True,
            "aug31_distinct_source_capture_records":2,
            "aug31_record_separation_m":native_report["aug31_source_record_separation_m"],
            "canonical_individual_ids_independently_verified":False,
            "source_osm_archive_sha256":osm_info["osm_archive_sha256"],
            "osm_not_available_at_aug31_original_forecast_cutoff":True,
        },
        "owner_monthly_capture_total":47,
        "august_12_actual_gpx_nights":12,
        "sampled_100m_10min_total":8965,
        "road_gpx_match_samples":r31["gps_metrics"]["road_matched_samples"]+r11["gps_road_match_count"],
        "noncapture_review_candidate_cells":len(cells),
        "review_packets_grouped_by_single_window_osm_way_and_spatial_adjacency":len(groups),
        "review_grouping_is_not_verified_road_travel":True,
        "capture_candidates_frozen_as_training_labels":0,
        "scientifically_certified_road_search_segments":0,
        "formally_eligible_non_capture_labels":0,
        "formally_eligible_capture_labels":0,
        "review_blockers":list(BLOCKERS),
        "training_allowed":False,
        "no_training_data_or_original_predictions_written":True,
        "relevant_source_receipts":list(BASIS_RECEIPTS),
        "night_summaries":night_rows,
        "top_review_groups_without_geocoordinates":[{
            "review_group_id":g["review_group_id"],"night":g["night"],
            "candidate_cells":g["spatially_adjacent_sampled_cells"],
            "candidate_samples":g["native_gpx_samples"],
            "priority_score_for_review_only":g["priority_score_for_review_only"]
        } for g in groups[:20]],
    }
    return summary,groups,cells

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--output",type=Path,default=Path("artifacts/august-evidence-packets"))
    args=ap.parse_args()
    summary,groups,cells=build_packets(args.root)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.output/"review_packets_private.json").write_text(json.dumps(groups,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (args.output/"review_cells_private.csv").open("w",encoding="utf-8-sig",newline="") as fp:
        writer=csv.DictWriter(fp,fieldnames=list(cells[0]))
        writer.writeheader();writer.writerows(cells)
    print(json.dumps({"native_original_bytes_verified":True,
                      "original_capture_events":summary["source_provenance"]["source_event_statements"],
                      "owner_confirmed_august":47,
                      "review_non_capture_cells":len(cells),
                      "spatial_review_packets":len(groups),
                      "training_positive":0,"training_negative":0},ensure_ascii=False))
if __name__=="__main__":
    main()
