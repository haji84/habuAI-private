#!/usr/bin/env python3
"""Source-safe August GPS sampled Exposure diagnostics, never formal Negative labels."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gpx_audit import parse_gpx, utm52n, night_date_for_time
from recover_remaining_august_nights import index_events, _match

NIGHTS = ("2026-08-12","2026-08-13","2026-08-15","2026-08-17",
          "2026-08-19","2026-08-21","2026-08-23","2026-08-24",
          "2026-08-27","2026-08-28","2026-08-29","2026-08-31")

def audit(root: Path):
    qc_path = root / "evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv"
    with qc_path.open(encoding="utf-8-sig",newline="") as f:
        qc = {r["operational_night"]:r for r in csv.DictReader(f)}
    baseline = json.loads((root/"dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    existing = [x for x in baseline["nights"] if x["month"] == "2026-08"]
    month_total = next(x["n"] for x in baseline["months"] if x["key"]=="2026-08")
    # The original PR #77 receipt remains frozen at 45 (before the owner correction).
    # Current baseline now contains the owner's confirmed 47, including 8/31=2.
    by_day={r["night"]:r["count"] for r in existing}
    confirmation=baseline.get("owner_confirmed_monthly_counts",{}).get("2026-08",{})
    original_receipt=json.loads((root/"evidence/recovered_sources/2026-08-12night-sampled-exposure-ci-receipt.json").read_text(encoding="utf-8"))
    if original_receipt["baseline_capture_total_unchanged"]!=45:
        raise ValueError("Historical frozen exposure receipt changed")
    if (month_total!=47 or by_day.get("2026-08-31")!=2 or
            sum(n for day,n in by_day.items() if day!="2026-08-31")!=45 or
            sum(by_day.values())!=47 or
            confirmation.get("status")!="OWNER_CONFIRMED" or
            confirmation.get("count")!=47):
        raise ValueError("Owner-confirmed August 47 reconciliation not verified")
    events=index_events((root/"evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt").read_text(encoding="utf-8"))
    by_night=defaultdict(list)
    for event in events:
        by_night[event["operational_night"]].append(event)
    rows=[]
    nights=[]
    aug31_candidates=[]
    for night in NIGHTS:
        path=root/f"data/raw/gpx/{night}__legacy.gpx"
        blob=path.read_bytes()
        checksum=hashlib.sha256(blob).hexdigest()
        expected=qc[night]
        if checksum!=expected["sha256"]:
            raise ValueError(f"GPX digest mismatch: {night}")
        points=parse_gpx(path)
        if len(points)!=int(expected["gps_points"]):
            raise ValueError(f"GPX point count mismatch: {night}")
        if any(night_date_for_time(p["time_utc"])!=night for p in points):
            raise ValueError(f"GPX day boundary mismatch: {night}")
        source_capture_events=[dict(e) for e in by_night[night] if e["event_type"]=="capture"]
        if night=="2026-08-31":
            if len(source_capture_events)!=2:
                raise ValueError("August 31 source capture mentions changed; require source review")
            matched,_=_match(source_capture_events,points)
            if matched!=2 or len({e["block_sha256"] for e in source_capture_events})!=2:
                raise ValueError("August 31 capture source block or GPX audit mismatch")
            aug31_candidates=[{
                "event_candidate_id":"aug31-source-"+e["block_sha256"][:16],
                "source_library_read_line":e["source_line"],
                "source_block_sha256":e["block_sha256"],
                "source_native_time":e["timestamp_native"],
                "gpx_proximity":e["gpx_proximity"],
                "species_note_native":e["species_or_native_note"],
                "independent_individual_id":None,
                "owner_capture_certified":False,
                "duplicate_checked_against_native_db":False,
                "decision":"UNRESOLVED"
            } for e in source_capture_events]
        baseline_days=[r["count"] for r in existing if r["night"]==night]
        baseline_day_count=baseline_days[0] if len(baseline_days)==1 else None
        capture_quantity_candidate_sum=sum(e["exact_owner_count_native"] or 1 for e in source_capture_events)
        starts=sorted(e["timestamp_interpreted_jst"] for e in by_night[night] if e["event_type"]=="exploration_start")
        ends=sorted(e["timestamp_interpreted_jst"] for e in by_night[night] if e["event_type"]=="exploration_end")
        bounded_session=len(starts)==1 and len(ends)==1 and starts[0]<ends[0]
        # Point-to-point sampling gaps, not proof of a vehicle stop or a searched road.
        gaps=[(later["time_utc"]-earlier["time_utc"]).total_seconds()
              for earlier,later in zip(points,points[1:])]
        max_gap_s=round(max(gaps,default=0),3)
        if abs(max_gap_s-float(expected["max_gap_s"]))>0.02:
            raise ValueError(f"Independent GPX max-gap QC mismatch: {night}")
        bins=defaultdict(list)
        accepted=[]
        for p in points:
            if p["exclude_point"] or (p["hdop"] is not None and p["hdop"]>10):
                continue
            x,y=utm52n(p["latitude"],p["longitude"])
            # Align on local JST 10min boundaries while storing explicit offset.
            jst=p["time_utc"].astimezone(timezone(timedelta(hours=9)))
            w=jst.replace(minute=(jst.minute//10)*10,second=0,microsecond=0)
            k=(math.floor(x/100),math.floor(y/100),w.isoformat())
            bins[k].append(p)
            accepted.append(p)
        for (cx,cy,window),group in sorted(bins.items()):
            group.sort(key=lambda p:p["time_utc"])
            speeds=[p["speed_mps"] for p in group if p["speed_mps"] is not None and math.isfinite(p["speed_mps"])]
            stop_count=sum(s<0.5 for s in speeds)
            during_session=bool(bounded_session and
                group[0]["time_utc"].astimezone(timezone(timedelta(hours=9))).isoformat()>=starts[0] and
                group[-1]["time_utc"].astimezone(timezone(timedelta(hours=9))).isoformat()<=ends[0])
            rows.append({
                "night":night,"cell_x":cx,"cell_y":cy,"window_start_jst":window,
                "sample_count":len(group),"first_point_utc":group[0]["time_utc"].isoformat(),
                "last_point_utc":group[-1]["time_utc"].isoformat(),
                "hdop_max":max((p["hdop"] for p in group if p["hdop"] is not None),default=None),
                "speed_observed_samples":len(speeds),"speed_mps_max":max(speeds,default=None),
                "stationary_samples_below_0_5mps":stop_count,
                "source_gpx":path.relative_to(root).as_posix(),"source_sha256":checksum,
                "passage":"SAMPLED_GPS_ONLY","within_explicit_session_window":during_session,
                "search_effort_verified":False,
                "capture_outcome_complete":False,"observation":"UNKNOWN",
                "formal_negative_eligible":False,"formal_positive_eligible":False
            })
        unique_spatial_cells=len({(cx,cy) for cx,cy,_ in bins})
        session_units=sum(1 for row in rows if row["night"]==night and row["within_explicit_session_window"])
        limitations=[]
        if not bounded_session: limitations.append("START_END_SESSION_MARKERS_INCOMPLETE")
        if max_gap_s>60: limitations.append("GPS_SAMPLING_GAP_OVER_60_SECONDS")
        if baseline_day_count is None: limitations.append("NO_DAY_LEVEL_OWNER_CAPTURE_BASELINE")
        elif capture_quantity_candidate_sum!=baseline_day_count:
            limitations.append("CAPTURE_STATEMENT_QUANTITY_VS_BASELINE_DISCREPANCY")
        limitations.extend(["ORIGINAL_NATIVE_LOG_BYTES_NOT_VERIFIED",
                            "ACTIVE_SEARCH_BY_ROAD_SECTION_NOT_ATTESTED",
                            "COMPLETE_OWNER_CAPTURE_OUTCOMES_NOT_ATTESTED",
                            "CAPTURE_INDIVIDUAL_OWNERSHIP_NOT_CERTIFIED",
                            "ROAD_NETWORK_VISIT_NOT_VALIDATED"])
        nights.append({
            "night":night,"gps_points":len(points),"qc_pass_samples":len(accepted),
            "gps_excluded_or_hdop_gt10":len(points)-len(accepted),
            "segment_breaks":sum(bool(p.get("segment_break_before")) for p in points),
            "sampled_100m_10min_units":len(bins),
            "unique_sampled_100m_spatial_cells":unique_spatial_cells,
            "additional_spatial_cell_time_windows":len(bins)-unique_spatial_cells,
            "raw_gpx_max_sampling_gap_s":max_gap_s,
            "raw_gpx_gaps_over_30_s":sum(g>30 for g in gaps),
            "raw_gpx_gaps_over_60_s":sum(g>60 for g in gaps),
            "raw_gpx_gaps_over_300_s":sum(g>300 for g in gaps),
            "baseline_owner_capture_count":baseline_day_count,
            "source_capture_event_mentions":len(source_capture_events),
            "source_capture_quantity_candidate_sum":capture_quantity_candidate_sum,
            "candidate_statement_quantity_matches_baseline":(capture_quantity_candidate_sum==baseline_day_count if baseline_day_count is not None else None),
            "original_native_log_verified":False,
            "complete_capture_outcomes_attested":False,
            "blockers":limitations,
            "explicit_session_starts":len(starts),"explicit_session_ends":len(ends),
            "paired_session_window":bounded_session,
            "gps_units_inside_session_window":session_units,
            "session_window_start_jst":starts[0] if bounded_session else None,
            "session_window_end_jst":ends[0] if bounded_session else None,
            "session_window_duration_min":round((datetime.fromisoformat(ends[0])-datetime.fromisoformat(starts[0])).total_seconds()/60,2) if bounded_session else None,
            "source_sha256":checksum,"search_effort_verified":False,
            "formal_negative_rows":0,"formal_positive_rows":0
        })
    return {"schema_version":"august-sampled-exposure-audit-v1",
            "scope":"GPS point occupancy, not searched-road confirmation",
            "monthly_baseline_count":month_total,"baseline_nights":len(existing),
            "historical_pr77_baseline_count":45,
            "aug31_in_existing_day_ledger":True,
            "aug31_owner_confirmed_day_count":2,
            "aug31_candidate_capture_mentions":2,
            "aug31_personal_distinct_individuals_certified":False,
            "owner_confirmed_august_monthly_total":True,
            "revised_monthly_count":47,
            "aug31_candidate_events":aug31_candidates,
            "total_sampled_units":len(rows),
            "total_session_window_units":sum(n["gps_units_inside_session_window"] for n in nights),
            "session_covered_nights":sum(bool(n["paired_session_window"]) for n in nights),
            "gps_nights_with_max_sampling_gap_over_60s":[n["night"] for n in nights if n["raw_gpx_max_sampling_gap_s"]>60],
            "training_eligibility":"BLOCKED_UNVERIFIED_SEARCH_AND_CAPTURE_OUTCOMES",
            "formal_negative_rows":0,"formal_positive_rows":0,
            "unvisited_not_assumed_negative":True,
            "nights":nights},rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--output",type=Path,default=Path("artifacts/august-exposure"))
    args=ap.parse_args()
    report,rows=audit(args.root)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (args.output/"sampled_exposure.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else [])
        if rows: writer.writeheader();writer.writerows(rows)
    print(json.dumps({"nights":len(report["nights"]),"samples":report["total_sampled_units"],
                      "positive_approved":0,"negative_approved":0}))
if __name__=="__main__":main()
