#!/usr/bin/env python3
"""Verify byte-equivalent user Library Habu TXT and audit ALL August personal capture statements.

Monthly aggregation/owner confirmation is distinct from authenticated individual
IDs or observed searched-road noncapture labels. No source bytes are modified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from recover_remaining_august_nights import index_events
from gpx_audit import utm52n

LIBRARY_RAW_SHA256="130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c"
LIBRARY_RAW_BYTES=116496
LIBRARY_RAW_LINES=10506
SOURCE="evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt"
LIBRARY_ORIGINAL_ID="libfile_76fd960f5a1481918b03b1b4c9bd9f88"
NIGHT_START="2026-08-01"
NIGHT_END="2026-08-31"

class SourceProvenanceError(ValueError):
    pass

def _hash(data: bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _event_id(event:dict)->str:
    return "capture-source-"+event["block_sha256"][:20]

def audit_original(root:Path=ROOT)->tuple[dict,list[dict]]:
    root=Path(root)
    source_path=root/SOURCE
    raw=source_path.read_bytes()
    sha=_hash(raw)
    if len(raw)!=LIBRARY_RAW_BYTES or sha!=LIBRARY_RAW_SHA256:
        raise SourceProvenanceError("Library native byte SHA or byte count does not match")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SourceProvenanceError("Unexpected source BOM not matching native UTF8 original")
    text=raw.decode("utf-8")
    if len(text.splitlines())!=LIBRARY_RAW_LINES:
        raise SourceProvenanceError("Native original line count mismatch")
    all_events=index_events(text)
    august=[e for e in all_events if NIGHT_START<=e["operational_night"]<=NIGHT_END]
    captures=[e for e in august if e["event_type"]=="capture"]
    if len(captures)!=46:
        raise SourceProvenanceError("Native capture event count does not match independent 46-event audit")
    if any(e["coordinates"] is None for e in captures):
        raise SourceProvenanceError("Native capture event lacks unique original coordinate pair")
    if len({e["block_sha256"] for e in captures})!=len(captures):
        raise SourceProvenanceError("Duplicate native capture text blocks; require review")
    baseline=json.loads((root/"dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    aug=next(m for m in baseline["months"] if m["key"]=="2026-08")
    confirm=baseline.get("owner_confirmed_monthly_counts",{}).get("2026-08",{})
    if (aug["n"]!=47 or confirm.get("count")!=47 or
            confirm.get("status")!="OWNER_CONFIRMED"):
        raise SourceProvenanceError("Owner-confirmed August 47 source baseline mismatch")
    days={n["night"]:n["count"] for n in baseline["nights"] if n["month"]=="2026-08"}
    if len(days)!=17 or sum(days.values())!=47:
        raise SourceProvenanceError("August day-level owner aggregate changed")
    by_night=defaultdict(list)
    for e in captures:
        by_night[e["operational_night"]].append(e)
    if set(by_night)!=set(days):
        raise SourceProvenanceError("All owner-confirmed August capture nights must occur in the uploaded original log")

    two_quantity=[e for e in captures if e["exact_owner_count_native"] is not None and e["exact_owner_count_native"]>1]
    if len(two_quantity)!=1 or two_quantity[0]["exact_owner_count_native"]!=2 or two_quantity[0]["operational_night"]!="2026-08-19":
        raise SourceProvenanceError("August 19 original two-individual event changed")

    quantities=Counter()
    reviews=[]
    for night in sorted(by_night):
        events=by_night[night]
        note_quantity=sum(e["exact_owner_count_native"] or 1 for e in events)
        quantities[night]=note_quantity
        if note_quantity!=days[night]:
            raise SourceProvenanceError(f"Owner daily aggregate does not reconcile to native original: {night}")
        for e in events:
            reviews.append({
                "candidate_event_id":_event_id(e),
                "night":night,
                "source_line":e["source_line"],
                "source_block_sha256":e["block_sha256"],
                "timestamp_native":e["timestamp_native"],
                "captured_quantity_candidate":e["exact_owner_count_native"] or 1,
                "explicit_two_quantity":e["exact_owner_count_native"]==2,
                "source_note":e["species_or_native_note"],
                "native_source_sha256":sha,
                "native_owner_identity_record":"USER_OWNER_MONTHLY_AGGREGATE_ONLY",
                "original_canonical_individual_id":None,
                "field_device_authentication":False,
                "individual_unique_identity_independently_verified":False,
                "scientific_positive_eligible":False,
                "scientific_negative_eligible":False
            })
    if sum(quantities.values())!=47:
        raise SourceProvenanceError("Source August quantity differs from owner 47")
    aug31=by_night["2026-08-31"]
    if len(aug31)!=2 or {e["timestamp_native"] for e in aug31}!={"2026/08/31 21:43","2026/09/01 1:17"}:
        raise SourceProvenanceError("Two exact Aug31 original record timestamps missing")
    a,b=aug31
    axy=utm52n(a["coordinates"]["latitude"],a["coordinates"]["longitude"])
    bxy=utm52n(b["coordinates"]["latitude"],b["coordinates"]["longitude"])
    distance=math.hypot(axy[0]-bxy[0],axy[1]-bxy[1])
    if not 8000<distance<10000:
        raise SourceProvenanceError("Aug31 distinct capture record geography unexpectedly changed")

    # A nearby second source statement may describe a new capture or a
    # re-observation. Preserve the owner-confirmed 47 and flag source pairs
    # for individual review instead of claiming either identity by inference.
    close_event_pairs=[]
    for i,first in enumerate(captures):
        first_time=datetime.fromisoformat(first["timestamp_interpreted_jst"])
        fx,fy=utm52n(first["coordinates"]["latitude"],first["coordinates"]["longitude"])
        for second in captures[i+1:]:
            if second["operational_night"]!=first["operational_night"]:
                continue
            second_time=datetime.fromisoformat(second["timestamp_interpreted_jst"])
            gap=abs((second_time-first_time).total_seconds())/60
            if gap>30:
                continue
            sx,sy=utm52n(second["coordinates"]["latitude"],second["coordinates"]["longitude"])
            metres=math.hypot(fx-sx,fy-sy)
            if metres<=100:
                close_event_pairs.append({
                    "night":first["operational_night"],
                    "first_source_block_sha256":first["block_sha256"],
                    "second_source_block_sha256":second["block_sha256"],
                    "first_source_line":first["source_line"],
                    "second_source_line":second["source_line"],
                    "minutes_apart":round(gap,2),
                    "source_location_separation_m":round(metres,1),
                    "duplicate_identity_proven":False,
                    "distinct_individuals_proven":False,
                    "review_state":"NEEDS_INDEPENDENT_INDIVIDUAL_EVIDENCE"
                })
    first_line=Counter(e["event_type"] for e in august)
    summary={
        "schema_version":"habu-august-native-library-byte-matched-capture-audit-v1",
        "verification_date":"2026-10-24",
        "library_native_original":{"library_file_id":LIBRARY_ORIGINAL_ID,
            "raw_file_size_bytes":LIBRARY_RAW_BYTES,
            "raw_file_sha256":LIBRARY_RAW_SHA256,
            "raw_utf8_line_count":LIBRARY_RAW_LINES,
            "independently_materialized_bytes_checked":True,
            "provenance_method":"Owner-uploaded Library raw file materialized; independent direct SHA256 compared with repository copy",
            "field_device_cryptographic_signature_verified":False},
        "repository_source":{"path":SOURCE,"sha256":sha,
            "byte_identical_to_library_native":True,
            "repo_source_raw_overwritten":False},
        "owner_confirmed_august_count":47,
        "native_capture_event_statements":len(captures),
        "native_capture_statement_quantity_sum":sum(quantities.values()),
        "august_capture_nights":len(quantities),
        "all_daily_capture_statement_quantities_match_owner_dashboard":True,
        "double_quantity_capture_night":"2026-08-19",
        "aug31_two_capture_event_blocks":len(aug31),
        "aug31_capture_event_blocks_distinct":len({e["block_sha256"] for e in aug31})==2,
        "aug31_source_record_separation_m":round(distance,1),
        "aug31_distinct_physical_individual_ids_verified":False,
        "native_august_event_type_counts":dict(sorted(first_line.items())),
        "spacetime_near_duplicate_review_pairs":close_event_pairs,
        "spacetime_near_duplicate_pair_count":len(close_event_pairs),
        "day_counts":[{"night":night,"source_capture_events":len(by_night[night]),
                       "native_statement_quantity":quantities[night],
                       "owner_confirmed_day_count":days[night]} for night in sorted(by_night)],
        "candidate_event_ids":[r["candidate_event_id"] for r in reviews],
        "canonical_individual_ids_verified":False,
        "complete_search_outcome_capture_ledger_certified":False,
        "observed_searched_road_segments_certified":False,
        "formal_positive_training_rows":0,
        "formal_negative_training_rows":0,
        "historical_prediction_changed":False,
        "evidence_grade":"LIBRARY_NATIVE_BYTE_MATCHED_CAPTURE_STATEMENTS_OWNER_MONTHLY_CONFIRMED",
        "training_grade":"NOT_VALIDATED_INDIVIDUAL_IDS_AND_SEARCH_EFFORT"
    }
    return summary,reviews

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--output",type=Path,default=Path("artifacts/august-native-certification"))
    args=p.parse_args()
    report,events=audit_original(args.root)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.output/"capture_events_review.json").write_text(json.dumps(events,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"sha256":report["library_native_original"]["raw_file_sha256"],
       "byte_identical":report["repository_source"]["byte_identical_to_library_native"],
       "events":report["native_capture_event_statements"],
       "reported_quantity":report["native_capture_statement_quantity_sum"],
       "owner_dashboard_quantity":report["owner_confirmed_august_count"],
       "night_count":report["august_capture_nights"],
       "aug31_source_record_separation_m":report["aug31_source_record_separation_m"],
       "formal_positive":0,"formal_negative":0},ensure_ascii=False))
if __name__=="__main__":
    main()
