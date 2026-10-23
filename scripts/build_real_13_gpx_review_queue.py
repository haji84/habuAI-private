#!/usr/bin/env python3
"""Issue review queue for all 13 raw GPX files with four source-backed August nights.

No raw log means UNKNOWN, not a confirmed zero. Monthly dashboard totals are
historical administrative aggregates, not individual outcome or effort receipts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from inventory_real_gpx_sources import build_inventory
from reconcile_august_field_candidates import reconcile

def build_queue(root=ROOT):
    root=Path(root)
    inventory=build_inventory(root)
    overlap=reconcile(root)
    baseline=json.loads((root/"dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    nights={r["night"]:r for r in baseline["nights"]}
    records=[]
    for track in inventory["raw_gpx"]:
        path=Path(track["source_path"])
        # A filename is used only as a join candidate. The true operational
        # night must also appear in the measured GPX timestamp inventory.
        filename_night=path.name.split("__legacy.gpx")[0]
        measured=set(track.get("operational_night_point_counts",{}))
        trustworthy=(track.get("gpx_track_valid") is True and measured=={filename_night})
        candidate=overlap["gpx_nights"].get(filename_night) if trustworthy else None
        count=nights.get(filename_night,{}).get("count")
        records.append({
            "gpx_source":track["source_path"],
            "operational_night":filename_night,
            "gps_source_sha256":track.get("sha256"),
            "raw_track_points":track.get("points",0),
            "gpX_night_and_clock_consistent":trustworthy,
            "candidate_capture_statements":len(candidate["capture_candidate_statements"]) if candidate else 0,
            "gps_corrob_capture_statements":sum(
                r["match_status"]=="GPX_SPACETIME_CORROBORATION_ONLY"
                for r in candidate["capture_candidate_statements"]) if candidate else 0,
            "gpx_corrob_reaction_controls":sum(
                r["match_status"]=="GPX_SPACETIME_CORROBORATION_ONLY"
                for r in candidate["reaction_controls"]) if candidate else 0,
            "dashboard_daily_aggregate_claim":count,
            "dashboard_is_event_or_individual_proof":False,
            "historical_primary_log_complete":False,
            "capture_quantity_and_owner_verified":False,
            "source_category":"RECOVERED_EXTRACTED_AUGUST_LOG_REVIEW_ONLY"
                if candidate else "NO_PRIMARY_CAPTURE_LOG_RECONCILIATION_IN_REPO",
            "eligible_training_positives":0,
            "eligible_training_negatives":0,
            "unknown_label":True,
            "reason":"Extracted candidate events have no verified owner and exact counts; "
                     "nightwide search/capture reporting is not certified"
                     if candidate else "No independently verified event/individual/reaction "
                     "ledger linked to this raw track",
        })
    records.sort(key=lambda z:z["operational_night"])
    august=sum(x["operational_night"].startswith("2026-08") for x in records)
    september=sum(x["operational_night"].startswith("2026-09") for x in records)
    return {
        "schema_version":"habu-real-13-gpx-candidate-review-queue-v1",
        "status":"SOURCE_MATCH_PROGRESS_TRAINING_BLOCKED",
        "raw_gpx_files":len(records),"august_raw_gpx_files":august,
        "september_raw_gpx_files":september,
        "raw_gpx_point_total":inventory["raw_gpx_track_points"],
        "night_rows":records,
        "gpx_raw_archive_sept28_excluded_as_separate_source":True,
        "candidate_capture_mentions":overlap["candidate_event_mentions_total"],
        "candidate_spacetime_matched":overlap["gpx_proximity_matched_capture_mentions"],
        "source_backed_nights":sum(x["source_category"]=="RECOVERED_EXTRACTED_AUGUST_LOG_REVIEW_ONLY" for x in records),
        "review_only_positives":overlap["candidate_event_mentions_total"],
        "admitted_owner_positive_individuals":0,
        "admitted_negative_units":0,
        "review_queue_open":True,
        "model_learning_generated":False,
        "formal_walk_forward_performed":False,
        "required_resolution":[
            "recover_and_verify_native_8_2_to_8_29_logs",
            "event_identity_ownership_quantity_reconciliation",
            "source_complete_capture_and_reaction_ledger",
            "explicit_search_effort_and_detection_coverage",
            "exante_weather_terrain_roads_availability_by_historical_cutoff",
            "independent_full_universe_holdout_split"
        ]
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    report=build_queue(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in (
        "status","raw_gpx_files","august_raw_gpx_files","september_raw_gpx_files",
        "candidate_capture_mentions","candidate_spacetime_matched",
        "source_backed_nights","admitted_owner_positive_individuals","admitted_negative_units"
    )},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
