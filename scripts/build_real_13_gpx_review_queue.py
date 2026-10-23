#!/usr/bin/env python3
"""Issue review queue for all 13 GPX files using recovered native August source.

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
from reconcile_native_august_habu_gpx import make_actual_join

def build_queue(root=ROOT):
    root=Path(root)
    inventory=build_inventory(root)
    native=make_actual_join(root, inventory=inventory)
    by_source={x["night"]:x for x in native["gpx_nights"]}
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
        candidate=by_source.get(filename_night)
        count=nights.get(filename_night,{}).get("count")
        records.append({
            "gpx_source":track["source_path"],
            "operational_night":filename_night,
            "gps_source_sha256":track.get("sha256"),
            "raw_track_points":track.get("points",0),
            "gpX_night_and_clock_consistent":trustworthy,
            "candidate_capture_statements":candidate["candidate_capture_events"] if candidate else 0,
            "habu_presence_positive_diagnostic_only":candidate["habu_presence_positive_diagnostic_events"] if candidate else 0,
            "gps_corrob_capture_statements":candidate["candidate_capture_events_spatially_corrob"] if candidate else 0,
            "gpx_corrob_reaction_controls":sum(
                r["match_status"]=="GPX_SPACETIME_CORROBORATION_ONLY"
                for r in candidate["reactions"]) if candidate else 0,
            "source_timestamped_blocks_on_night":candidate["source_timestamped_blocks_on_night"] if candidate else 0,
            "source_original_sha256":native["original_sha256"],
            "dashboard_daily_aggregate_claim":count,
            "dashboard_is_event_or_individual_proof":False,
            "historical_primary_log_complete":False,
            "capture_quantity_and_owner_verified":False,
            "source_category":"NATIVE_AUGUST_SOURCE_PRESENT_OUTCOMES_UNVERIFIED"
                if candidate and candidate["source_present_for_night"]
                else "NO_NATIVE_FIELD_LOG_COVERAGE_FOR_GPXT_NIGHT",
            "eligible_training_positives":0,
            "eligible_training_negatives":0,
            "unknown_label":True,
            "reason":"Native source recovered; per-event owner/quantity or full-night observation completeness still unaudited"
                     if candidate and candidate["source_present_for_night"]
                     else "Native August log ends before this GPX night; no complete owner-event ledger",
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
        "candidate_capture_mentions":sum(x["candidate_capture_events"] for x in native["gpx_nights"]),
        "habu_presence_positive_diagnostic_only":native["event_presence_positive_diagnostic_only"],
        "original_capture_statements_all_nights":native["original_source_event_block_count"],
        "original_source_sha256":native["original_sha256"],
        "previous_extracted_aliases_deduplicated":native["legacy_extracted_capture_aliases_found"],
        "candidate_spacetime_matched":sum(x["candidate_capture_events_spatially_corrob"] for x in native["gpx_nights"]),
        "source_backed_nights":sum(x["source_category"]=="NATIVE_AUGUST_SOURCE_PRESENT_OUTCOMES_UNVERIFIED" for x in records),
        "review_only_positives":sum(x["candidate_capture_events"] for x in native["gpx_nights"]),
        "admitted_owner_positive_individuals":0,
        "admitted_negative_units":0,
        "review_queue_open":True,
        "model_learning_generated":False,
        "formal_walk_forward_performed":False,
        "required_resolution":[
            "native_source_recovered_needs_individual_role_and_quantity_review",
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
