#!/usr/bin/env python3
"""Review-only August 2026 source certification queue; NEVER creates training labels.

Reuse PR #77's actual-GPX audit; no additional independent parser or "empty
log == zero" inference. The returned matrix is a source review queue, not proof
that any road was searched or that a Habu was absent.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_august_sampled_exposure import audit

REQUIRED_BY_NIGHT=(
    "AUTHENTIC_NATIVE_LOG_AND_PROVENANCE",
    "ROAD_SEGMENT_ACTIVE_SEARCH_ATTESTATION",
    "OWNER_CAPTURE_OUTCOME_COMPLETENESS",
    "INDIVIDUAL_IDENTITY_AND_DUPLICATE_RECONCILIATION",
    "EX_ANTE_SOURCE_AVAILABILITY_AND_FORECAST_UNIVERSE",
)

def build_review_queue(root:Path=ROOT)->dict:
    root=Path(root)
    report,units=audit(root)
    if len(report["nights"])!=12 or len(units)!=8965:
        raise ValueError("SOURCE_INVENTORY_DRIFT")
    if any(row["observation"]!="UNKNOWN" or row["formal_negative_eligible"] or row["formal_positive_eligible"] for row in units):
        raise ValueError("UNAPPROVED_MODEL_LABEL_IN_SOURCE_AUDIT")
    source_log_path=root/"evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt"
    source_log_sha=hashlib.sha256(source_log_path.read_bytes()).hexdigest()
    by_night=Counter(row["night"] for row in units)
    inside=Counter(row["night"] for row in units if row["within_explicit_session_window"])
    nights=[]
    for n in report["nights"]:
        night=n["night"]
        blockers=list(REQUIRED_BY_NIGHT)
        if not n["paired_session_window"]:
            blockers.append("SESSION_START_END_NOT_PAIRED")
        if n["raw_gpx_max_sampling_gap_s"]>60:
            blockers.append("GPS_SAMPLING_GAP_OVER_60_SECONDS")
        if n["baseline_owner_capture_count"] is None:
            blockers.append("DAY_LEVEL_OWNER_CAPTURE_BASELINE_MISSING")
        if n["candidate_statement_quantity_matches_baseline"] is False:
            blockers.append("CAPTURE_QUANTITY_BASELINE_DISCREPANCY")
        if night=="2026-08-31":
            blockers.append("AUG31_TWO_CAPTURE_STATEMENTS_INDIVIDUAL_IDENTITY_UNVERIFIED")
        if night=="2026-08-21":
            blockers.append("ZERO_CAPTURE_RECORD_NOT_COMPLETE_OUTCOME_PROOF")
        row={
            "night":night,
            "gpx_path":f"data/raw/gpx/{night}__legacy.gpx",
            "gpx_sha256":n["source_sha256"],
            "source_log_path":source_log_path.relative_to(root).as_posix(),
            "source_log_sha256":source_log_sha,
            "source_log_is_library_extracted_not_native_bytes":True,
            "gp_point_count":n["gps_points"],
            "quality_retained_samples":n["qc_pass_samples"],
            "sampling_max_gap_seconds":n["raw_gpx_max_sampling_gap_s"],
            "sampled_position_time_units":by_night[night],
            "position_time_units_wholly_inside_paired_session":inside[night] if n["paired_session_window"] else None,
            "explicit_start_end_pair":n["paired_session_window"],
            "capture_statement_count":n["source_capture_event_mentions"],
            "candidate_statement_quantity":n["source_capture_quantity_candidate_sum"],
            "archived_dashboard_individual_count":n["baseline_owner_capture_count"],
            "native_owner_identity_certified":False,
            "capture_outcomes_complete":False,
            "searched_road_sections_certified":False,
            "road_matched_search_exposure_units":0,
            "formal_eligible_positive_units":0,
            "formal_eligible_negative_units":0,
            "disposition":"UNKNOWN_NOT_MODEL_ELIGIBLE",
            "blocking_proof":blockers,
        }
        nights.append(row)
    if sum(n["sampled_position_time_units"] for n in nights)!=report["total_sampled_units"]:
        raise ValueError("SAMPLED_GPX_UNIT_TOTAL_INCONSISTENT")
    if sum(n["position_time_units_wholly_inside_paired_session"] or 0 for n in nights)!=report["total_session_window_units"]:
        raise ValueError("PAIRED_SESSION_UNIT_TOTAL_INCONSISTENT")
    return {
        "schema_version":"august-source-eligibility-queue-v1",
        "scope":"2026 August actual GPX nights",
        "source":"scripts/audit_august_sampled_exposure.py",
        "scope_note":"sampled GPS position/time units are not confirmed searched road sections",
        "count_integrity":{"baseline_august":47,
                           "historical_pr77_august_total":45,
                           "owner_confirmed_august_47":True,
                           "owner_confirmed_aug31_day_count":2,
                           "aug31_independently_verified_individuals":None,
                           "aug31_capture_statement_candidates":report["aug31_candidate_events"]},
        "totals":{"nights":12,"gp_samples":sum(n["gp_point_count"] for n in nights),
                  "position_time_units":len(units),
                  "within_session_candidate_units":report["total_session_window_units"],
                  "paired_session_nights":sum(n["explicit_start_end_pair"] for n in nights),
                  "certified_searched_road_units":0,
                  "eligible_positive_units":0,"eligible_negative_units":0},
        "nights":nights,
        "official_model_training_allowed":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--output",type=Path,default=Path("artifacts/august-certification/evidence_review_queue.json"))
    args=p.parse_args()
    receipt=build_review_queue(args.root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"nights":receipt["totals"]["nights"],"sampled_bins":receipt["totals"]["position_time_units"],
                      "inside_explicit_session":receipt["totals"]["within_session_candidate_units"],
                      "certified_searched_road_units":0,"negative_labels":0,
                      "status":"REVIEW_QUEUE_NOT_MODEL_TRAINING"}))
if __name__=="__main__":main()
