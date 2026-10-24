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
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gpx_audit import parse_gpx, utm52n, distance_m, night_date_for_time

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
    if sum(x["count"] for x in existing) != month_total or month_total != 45:
        raise ValueError("Archived August baseline is not the expected 45")
    if any(x["night"]=="2026-08-31" for x in existing):
        raise ValueError("August 31 already included: reassess overlap before any additions")
    rows=[]
    nights=[]
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
        bins=defaultdict(list)
        accepted=[]
        for p in points:
            if p["exclude_point"] or (p["hdop"] is not None and p["hdop"]>10):
                continue
            x,y=utm52n(p["latitude"],p["longitude"])
            start=p["time_utc"].astimezone().replace(second=0,microsecond=0)
            # Align on local JST 10min boundaries while storing explicit offset.
            jst=p["time_utc"]+timedelta(hours=9)
            w=jst.replace(minute=(jst.minute//10)*10,second=0,microsecond=0)
            k=(math.floor(x/100),math.floor(y/100),w.isoformat()+"+09:00")
            bins[k].append(p)
            accepted.append(p)
        for (cx,cy,window),group in sorted(bins.items()):
            group.sort(key=lambda p:p["time_utc"])
            speeds=[p["speed_mps"] for p in group if p["speed_mps"] is not None and math.isfinite(p["speed_mps"])]
            stop_count=sum(s<0.5 for s in speeds)
            rows.append({
                "night":night,"cell_x":cx,"cell_y":cy,"window_start_jst":window,
                "sample_count":len(group),"first_point_utc":group[0]["time_utc"].isoformat(),
                "last_point_utc":group[-1]["time_utc"].isoformat(),
                "hdop_max":max((p["hdop"] for p in group if p["hdop"] is not None),default=None),
                "speed_observed_samples":len(speeds),"speed_mps_max":max(speeds,default=None),
                "stationary_samples_below_0_5mps":stop_count,
                "source_gpx":path.relative_to(root).as_posix(),"source_sha256":checksum,
                "passage":"SAMPLED_GPS_ONLY","search_effort_verified":False,
                "capture_outcome_complete":False,"observation":"UNKNOWN",
                "formal_negative_eligible":False,"formal_positive_eligible":False
            })
        nights.append({
            "night":night,"gps_points":len(points),"qc_pass_samples":len(accepted),
            "gps_excluded_or_hdop_gt10":len(points)-len(accepted),
            "segment_breaks":sum(bool(p.get("segment_break_before")) for p in points),
            "sampled_100m_10min_units":len(bins),
            "source_sha256":checksum,"search_effort_verified":False,
            "formal_negative_rows":0,"formal_positive_rows":0
        })
    return {"schema_version":"august-sampled-exposure-audit-v1",
            "scope":"GPS point occupancy, not searched-road confirmation",
            "monthly_baseline_count":month_total,"baseline_nights":len(existing),
            "aug31_in_existing_day_ledger":False,
            "aug31_candidate_capture_mentions":2,
            "aug31_personal_distinct_individuals_certified":False,
            "revised_monthly_count":None,
            "aug31_candidate_events":[
                {"native_time":"2026/08/31 21:43","native_note":"ハブ捕獲100~120オス",
                 "individual_id":None,"owner_verified":False,"duplicate_checked":False},
                {"native_time":"2026/09/01 1:17","native_note":"ハブ捕獲100~120オス",
                 "individual_id":None,"owner_verified":False,"duplicate_checked":False}],
            "total_sampled_units":len(rows),"formal_negative_rows":0,"formal_positive_rows":0,
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
