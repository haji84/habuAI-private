#!/usr/bin/env python3
"""Aug31 real-GPX / auxiliary-OSM road alignment and review-only noncapture candidates.

A road match or slow vehicle does not prove the owner actively searched.
Never infer snake absence, label=0, a source-original P0, or an individual ID.
Original GPS, Habu log and archived OSM bytes remain immutable.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from gpx_audit import parse_gpx, utm52n, night_date_for_time
from recover_remaining_august_nights import index_events, _match
from verify_osm_road_archive import PART_DIR, EXPECTED_SHA256, verify_archive

JST = timezone(timedelta(hours=9))
NIGHT = "2026-08-31"
GPX = "data/raw/gpx/2026-08-31__legacy.gpx"
LOG = "evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt"
QC = "evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv"
OSM_MEMBER = "04_processed_road/osm_road_centerlines.geojsonl"
OSM_MEMBER_SHA = "e5bfff98fc1af8d118d18f46b6d289a0db7f8b69cd4807fb0966103a0f57348e"
MAP_MATCH_MAX_M = 35.0
SLOW_MAX_MPS = 6.0
SLOW_MIN_MPS = 0.5
FAST_MIN_MPS = 11.0

class RoadDiagnosticError(ValueError):
    pass

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _point_segment_distance(x: float, y: float, a: tuple[float,float], b: tuple[float,float]) -> float:
    ax,ay=a;bx,by=b
    dx,dy=bx-ax,by-ay
    sq=dx*dx+dy*dy
    if sq<=1e-12:
        return math.hypot(x-ax,y-ay)
    t=max(0.0,min(1.0,((x-ax)*dx+(y-ay)*dy)/sq))
    return math.hypot(x-(ax+t*dx),y-(ay+t*dy))

class RoadMatcher:
    """Grid-indexed OSM centerline proximity. Retrospective auxiliary, not road truth."""
    def __init__(self, features: list[dict]):
        self.by_cell: dict[tuple[int,int], list[tuple[int,str,tuple[float,float],tuple[float,float]]]] = defaultdict(list)
        self.ways=0
        self.segments=0
        for feature in features:
            props=feature.get("properties", {})
            if props.get("normal_route") is not True:
                continue
            way=props.get("osm_way_id")
            if type(way) is not int:
                raise RoadDiagnosticError("OSM feature lacks exact way ID")
            geometry=feature.get("geometry") or {}
            kind=geometry.get("type")
            lines=[geometry.get("coordinates",[])] if kind=="LineString" else geometry.get("coordinates",[]) if kind=="MultiLineString" else []
            if not lines:
                raise RoadDiagnosticError("Missing OSM centerline geometry")
            self.ways+=1
            for line in lines:
                if len(line)<2:
                    continue
                prev=None
                for coordinate in line:
                    if not isinstance(coordinate,(list,tuple)) or len(coordinate)<2:
                        raise RoadDiagnosticError("Invalid road coordinate")
                    lon,lat=float(coordinate[0]),float(coordinate[1])
                    if not (math.isfinite(lat) and math.isfinite(lon) and 26<=lat<=30 and 127<=lon<=132):
                        raise RoadDiagnosticError("OSM coordinate outside audit envelope")
                    current=utm52n(lat,lon)
                    if prev is not None:
                        cx0=math.floor((min(prev[0],current[0])-MAP_MATCH_MAX_M)/100)
                        cx1=math.floor((max(prev[0],current[0])+MAP_MATCH_MAX_M)/100)
                        cy0=math.floor((min(prev[1],current[1])-MAP_MATCH_MAX_M)/100)
                        cy1=math.floor((max(prev[1],current[1])+MAP_MATCH_MAX_M)/100)
                        if (cx1-cx0+1)*(cy1-cy0+1)>1500:
                            raise RoadDiagnosticError("Unreasonably long OSM segment bbox")
                        record=(way,str(props.get("highway","")),prev,current)
                        for cx in range(cx0,cx1+1):
                            for cy in range(cy0,cy1+1):
                                self.by_cell[(cx,cy)].append(record)
                        self.segments+=1
                    prev=current
        if not self.by_cell or self.ways<1:
            raise RoadDiagnosticError("No drivable OSM auxiliary centerlines")

    def match_xy(self, x: float,y: float) -> dict[str,Any]:
        candidates=self.by_cell.get((math.floor(x/100),math.floor(y/100)), [])
        best_by_way={}
        for way,highway,a,b in candidates:
            dist=_point_segment_distance(x,y,a,b)
            if dist>MAP_MATCH_MAX_M:
                continue
            current=best_by_way.get(way)
            if current is None or dist<current[0]:
                best_by_way[way]=(dist,highway)
        if not best_by_way:
            return {"status":"NO_AUXILIARY_ROAD_WITHIN_35M","way_id":None,"distance_m":None}
        ranked=sorted((dist,way,highway) for way,(dist,highway) in best_by_way.items())
        closest=ranked[0]
        if len(ranked)>1 and ranked[1][0]-closest[0]<=8.0:
            return {"status":"AMBIGUOUS_MULTIPLE_ROADS","way_id":None,"distance_m":round(closest[0],2)}
        return {"status":"AUXILIARY_ROAD_MATCH_REVIEW","way_id":closest[1],
                "highway":closest[2],"distance_m":round(closest[0],2)}

def load_osm_matcher(root:Path)->tuple[RoadMatcher,dict]:
    # Full archive CRC, all member paths and SHA validation are already part of
    # the canonical repo archive verifier. Reuse it rather than trust file names.
    audit=verify_archive(root)
    if audit["sha256"]!=EXPECTED_SHA256:
        raise RoadDiagnosticError("OSM archive source identity changed")
    directory=root/PART_DIR
    raw=base64.b64decode(b"".join((directory/f"part_{i:03d}.b64").read_bytes()
                                    for i in range(33)).replace(b"\n",b"").replace(b"\r",b""),
                         validate=True)
    if hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA256:
        raise RoadDiagnosticError("OSM byte-identical archive mismatch")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names=[n for n in zf.namelist() if n==OSM_MEMBER or n.endswith("/"+OSM_MEMBER)]
        if len(names)!=1:
            raise RoadDiagnosticError("OSM centerline source ambiguous/missing")
        member=zf.read(names[0])
    if hashlib.sha256(member).hexdigest()!=OSM_MEMBER_SHA:
        raise RoadDiagnosticError("OSM centerline member SHA-256 mismatch")
    features=[json.loads(line) for line in member.decode("utf-8").splitlines() if line.strip()]
    matcher=RoadMatcher(features)
    return matcher, {"osm_archive_sha256":EXPECTED_SHA256,
                     "osm_centerline_member_sha256":OSM_MEMBER_SHA,
                     "osm_centerline_features":len(features),
                     "matched_eligible_ways":matcher.ways,
                     "indexed_line_segments":matcher.segments,
                     "road_source":"OpenStreetMap auxiliary, post-hoc 2026-09-25 archive",
                     "historical_aug31_pre_exploration_available":False,
                     "official_road_network_certified":False}

def _time_window(dt:datetime)->str:
    at=dt.astimezone(JST)
    return at.replace(minute=at.minute//10*10,second=0,microsecond=0).isoformat()

def _session(events:list[dict])->tuple[datetime,datetime]:
    starts=[datetime.fromisoformat(e["timestamp_interpreted_jst"]) for e in events if e["event_type"]=="exploration_start"]
    ends=[datetime.fromisoformat(e["timestamp_interpreted_jst"]) for e in events if e["event_type"]=="exploration_end"]
    if len(starts)!=1 or len(ends)!=1 or starts[0]>=ends[0]:
        raise RoadDiagnosticError("Aug31 has no single independently bounded log session")
    return starts[0],ends[0]

def _candidate_activity(group:list[dict],mask:str|None)->str:
    if mask=="CAPTURE":
        return "CAPTURE_VICINITY_REVIEW"
    if mask=="HABU_SIGHTING":
        return "HABU_SIGHTING_VICINITY_REVIEW"
    if mask=="HABU_ROADKILL":
        return "HABU_ROADKILL_VICINITY_REVIEW"
    if not group:
        return "UNKNOWN"
    inside=[p for p in group if p["inside_session"]]
    if not inside:
        return "OUTSIDE_RECORDED_SESSION"
    matched=[p for p in inside if p["road_status"]=="AUXILIARY_ROAD_MATCH_REVIEW"
             and p["hdop"] is not None and p["hdop"]<=10]
    if len(matched)<5:
        return "GPS_ROAD_MATCH_INSUFFICIENT"
    n=len(matched)
    known=[p for p in matched if p["speed_mps"] is not None]
    if len(known)<5 or len(known)/n<0.7:
        return "SPEED_EVIDENCE_INSUFFICIENT"
    slow=[p for p in known if SLOW_MIN_MPS<=p["speed_mps"]<=SLOW_MAX_MPS]
    fast=[p for p in known if p["speed_mps"]>=FAST_MIN_MPS]
    stop=[p for p in known if p["speed_mps"]<SLOW_MIN_MPS]
    span=(known[-1]["time_utc"]-known[0]["time_utc"]).total_seconds()
    if len(fast)/len(known)>=0.7:
        return "LIKELY_TRANSIT_REVIEW"
    if len(stop)/len(known)>=0.7:
        return "STATIONARY_NOT_SEARCH_PROOF"
    if (len(slow)>=5 and len(slow)/len(known)>=0.65 and
            len(fast)/len(known)<=0.1 and span>=8):
        return "LIKELY_SLOW_SEARCH_REVIEW"
    return "MIXED_OR_UNCERTAIN_ACTIVITY"

def _near_event(events:list[dict],cx:int,cy:int,at:datetime)->str|None:
    # Explicit capture contexts dominate all no-capture interpretations.
    # Spatial buffer is deliberately conservative and is NOT a precision claim.
    x,y=cx*100+50,cy*100+50
    candidates=[]
    for e in events:
        kind=e["event_type"]
        if kind not in ("capture","sighting","roadkill"):
            continue
        if kind!="capture" and e.get("species_or_native_note")!="ハブ":
            continue
        coord=e["coordinates"]
        if coord is None:
            # Unlocatable capture cannot certify absence anywhere that night.
            if kind=="capture":
                return "CAPTURE"
            continue
        t=datetime.fromisoformat(e["timestamp_interpreted_jst"])
        if abs((t-at).total_seconds())>900:
            continue
        ex,ey=utm52n(coord["latitude"],coord["longitude"])
        if math.hypot(x-ex,y-ey)<=175:
            candidates.append("CAPTURE" if kind=="capture" else "HABU_SIGHTING" if kind=="sighting" else "HABU_ROADKILL")
    return "CAPTURE" if "CAPTURE" in candidates else "HABU_SIGHTING" if "HABU_SIGHTING" in candidates else "HABU_ROADKILL" if "HABU_ROADKILL" in candidates else None

def _audit_night(root:Path,matcher:RoadMatcher,osm_evidence:dict)->tuple[dict,list[dict]]:
    gpx=root/GPX
    digest=sha256(gpx)
    with (root/QC).open(encoding="utf-8-sig",newline="") as f:
        qc=next((r for r in csv.DictReader(f) if r["operational_night"]==NIGHT),None)
    if qc is None or digest!=qc["sha256"]:
        raise RoadDiagnosticError("Aug31 original GPX SHA mismatch")
    points=parse_gpx(gpx)
    if len(points)!=int(qc["gps_points"]) or len(points)!=17906:
        raise RoadDiagnosticError("Aug31 GPX points changed")
    if any(night_date_for_time(p["time_utc"])!=NIGHT for p in points):
        raise RoadDiagnosticError("Aug31 operational-night 07:00 mismatch")
    logpath=root/LOG
    events=[e for e in index_events(logpath.read_text(encoding="utf-8"))
            if e["operational_night"]==NIGHT]
    start,end=_session(events)
    captures=[dict(e) for e in events if e["event_type"]=="capture"]
    if len(captures)!=2:
        raise RoadDiagnosticError("Aug31 source capture statements no longer two")
    hits,_=_match(captures,points)
    if hits!=2 or len({e["block_sha256"] for e in captures})!=2:
        raise RoadDiagnosticError("Aug31 capture statement/GPX mismatch")
    baseline=json.loads((root/"dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    if (next(m["n"] for m in baseline["months"] if m["key"]=="2026-08")!=47 or
            next(n["count"] for n in baseline["nights"] if n["night"]==NIGHT)!=2 or
            baseline["owner_confirmed_monthly_counts"]["2026-08"]["status"]!="OWNER_CONFIRMED"):
        raise RoadDiagnosticError("Owner-confirmed August 47 baseline mismatch")

    buckets=defaultdict(list)
    prev=None
    counters=Counter()
    for p in points:
        counters["gpx_source_points"]+=1
        if p.get("exclude_point") or (p.get("hdop") is not None and p["hdop"]>10):
            counters["quality_excluded"]+=1
            prev=None
            continue
        counters["legacy_qc_kept"]+=1
        if p.get("hdop") is None:
            counters["hdop_missing"]+=1
        xy=utm52n(p["latitude"],p["longitude"])
        at=p["time_utc"].astimezone(JST)
        within=start<=at<=end
        matched=matcher.match_xy(*xy)
        if matched["status"]=="AUXILIARY_ROAD_MATCH_REVIEW":
            counters["road_matched_samples"]+=1
        elif matched["status"]=="AMBIGUOUS_MULTIPLE_ROADS":
            counters["road_ambiguous_samples"]+=1
        else:
            counters["road_unmatched_samples"]+=1
        speed=p.get("speed_mps")
        if speed is None or not math.isfinite(speed) or not 0<=speed<=45:
            speed=None
            if prev is not None:
                last,p_xy=prev
                gap=(p["time_utc"]-last["time_utc"]).total_seconds()
                if 0<gap<=5 and not p.get("segment_break_before"):
                    observed=math.hypot(xy[0]-p_xy[0],xy[1]-p_xy[1])/gap
                    if observed<=45:
                        speed=observed
        if speed is None:
            counters["speed_unknown_samples"]+=1
        if within:
            counters["within_recorded_session_points"]+=1
        key=(math.floor(xy[0]/100),math.floor(xy[1]/100),_time_window(p["time_utc"]))
        buckets[key].append({
            "time_utc":p["time_utc"],"inside_session":within,
            "road_status":matched["status"],"way_id":matched["way_id"],
            "road_distance_m":matched["distance_m"],
            "speed_mps":round(speed,3) if speed is not None else None,
            "hdop":p.get("hdop")
        })
        prev=(p,xy)

    rows=[]
    activity_counts=Counter()
    for (cx,cy,window),group in sorted(buckets.items()):
        group.sort(key=lambda p:p["time_utc"])
        center=datetime.fromisoformat(window)+timedelta(minutes=5)
        mask=_near_event(events,cx,cy,center)
        activity=_candidate_activity(group,mask)
        activity_counts[activity]+=1
        good=[p for p in group if p["road_status"]=="AUXILIARY_ROAD_MATCH_REVIEW"]
        matched_ways=Counter(p["way_id"] for p in good)
        most_common_way=matched_ways.most_common(1)[0][0] if matched_ways else None
        candidate_noncapture=activity=="LIKELY_SLOW_SEARCH_REVIEW" and mask is None
        rows.append({
            "operational_night":NIGHT,
            "cell_x":cx,"cell_y":cy,"window_start_jst":window,
            "sample_count":len(group),
            "recorded_session_samples":sum(p["inside_session"] for p in group),
            "road_matched_samples":len(good),
            "road_ambiguous_samples":sum(p["road_status"]=="AMBIGUOUS_MULTIPLE_ROADS" for p in group),
            "osm_way_id_candidate":most_common_way,
            "maximum_speed_mps":max((p["speed_mps"] for p in group if p["speed_mps"] is not None),default=None),
            "slow_samples":sum(p["speed_mps"] is not None and SLOW_MIN_MPS<=p["speed_mps"]<=SLOW_MAX_MPS for p in group),
            "fast_samples":sum(p["speed_mps"] is not None and p["speed_mps"]>=FAST_MIN_MPS for p in group),
            "event_nearby":mask or "NONE_RECORDED",
            "activity_candidate":activity,
            "noncapture_candidate":"NO_OWNER_CAPTURE_RECORDED_REVIEW" if candidate_noncapture else "NOT_QUALIFIED",
            "observation":"UNKNOWN",
            "verified_search_effort":False,
            "verified_capture_outcome_completeness":False,
            "formal_negative_eligible":False,
            "formal_positive_eligible":False
        })
    if len(rows)!=688:
        raise RoadDiagnosticError(f"Aug31 100m x 10min baseline changed: {len(rows)}")
    if sum(r["sample_count"] for r in rows)!=counters["legacy_qc_kept"]:
        raise RoadDiagnosticError("Observed sample accounting mismatch")
    return {
        "schema_version":"habu-aug31-road-search-review-v1",
        "status":"REVIEW_ONLY_NO_TRAINING_LABELS",
        "operational_night":NIGHT,
        "input_provenance":{"gpx_path":GPX,"gpx_sha256":digest,
            "qc_path":QC,"qc_sha256":sha256(root/QC),
            "recovered_log_path":LOG,"recovered_log_extracted_sha256":sha256(logpath),
            "native_log_byte_verified":False,
            **osm_evidence},
        "session":{"has_single_start_and_end":True,
                   "start_jst":start.isoformat(),"end_jst":end.isoformat(),
                   "within_session_is_not_active_search_proof":True},
        "capture_statements":{"count":2,"both_gpx_matched":True,
            "source_event_sha256s":[e["block_sha256"] for e in captures],
            "owner_confirmed_monthly_august_count":47,
            "aug31_daily_aggregate_count":2,
            "individual_capture_identity_certified":False},
        "gps_metrics":dict(counters),
        "road_activity_candidate_counts":dict(sorted(activity_counts.items())),
        "sampled_100m_10min_units":len(rows),
        "noncapture_review_candidate_count":sum(r["noncapture_candidate"]=="NO_OWNER_CAPTURE_RECORDED_REVIEW" for r in rows),
        "formal_positive_training_rows":0,"formal_negative_training_rows":0,
        "certified_searched_road_segments":0,
        "complete_owner_capture_outcomes_certified":False,
        "source_role":"RETROSPECTIVE_DIAGNOSTIC_NOT_EX_ANTE_ROAD_UNIVERSE",
        "next_gate":["ACTUAL_SEARCH_VS_TRANSIT_INDEPENDENT_VERIFICATION",
                     "ROAD_MATCH_SECONDARY_PROOF_AND_HISTORICAL_AVAILABILITY",
                     "COMPLETE_NIGHT_CAPTURE_OUTCOME_EVIDENCE",
                     "AUG31_SOURCE_NATIVE_INDIVIDUAL_IDS",
                     "PROHIBIT_UNVISITED_OR_GPS_ONLY_NEGATIVES"]
    },rows

def analyze(root:Path=ROOT, *, matcher:RoadMatcher|None=None,
            osm_evidence:dict|None=None)->tuple[dict,list[dict]]:
    root=Path(root)
    if matcher is None:
        matcher,osm_evidence=load_osm_matcher(root)
    if osm_evidence is None:
        osm_evidence={"road_source":"synthetic diagnostic tests only",
                      "osm_archive_sha256":None,
                      "osm_centerline_member_sha256":None,
                      "historical_aug31_pre_exploration_available":False,
                      "official_road_network_certified":False}
    return _audit_night(root,matcher,osm_evidence)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--output",type=Path,default=Path("artifacts/aug31-road-review"))
    args=ap.parse_args()
    result,rows=analyze(args.root)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"summary.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (args.output/"review_cells.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"night":NIGHT,"source_gpx_points":result["gps_metrics"]["gpx_source_points"],
                      "road_matched_samples":result["gps_metrics"]["road_matched_samples"],
                      "sampled_bins":result["sampled_100m_10min_units"],
                      "road_activity_counts":result["road_activity_candidate_counts"],
                      "noncapture_review_candidates":result["noncapture_review_candidate_count"],
                      "eligible_positive":0,"eligible_negative":0},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
