from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from gpx_audit import parse_gpx, utm52n

JST = ZoneInfo("Asia/Tokyo")

@dataclass
class Stage:
    name: str
    status: str
    reason: str = ""

def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return dt.astimezone(JST)

def night_for(dt: datetime) -> str:
    local = dt.astimezone(JST)
    if local.hour < 7:
        local -= timedelta(days=1)
    return local.date().isoformat()

def canonical_prediction_hash(payload: dict[str, Any]) -> str:
    clean = {k: v for k, v in payload.items() if k != "payload_sha256" and not k.startswith("_")}
    raw = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def load_predictions(root: Path, night: str, cls: str = "original") -> list[dict[str, Any]]:
    base = root / "predictions" / cls / night
    if not base.exists():
        return []
    out = []
    dirs = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("P")]
    dirs.sort(key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 10**9)
    for d in dirs:
        p = d / "prediction.json"
        if not p.exists():
            continue
        payload = json.loads(p.read_text(encoding="utf-8"))
        payload["_path"] = str(p.relative_to(root))
        payload.setdefault("prediction_version", d.name)
        out.append(payload)
    return out

def verify_predictions(predictions: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    rows = []
    worst = "PASS"
    for p in predictions:
        expected = p.get("payload_sha256")
        actual = canonical_prediction_hash(p)
        if not expected:
            status = "PARTIAL"
            worst = "PARTIAL"
            reason = "payload_sha256 missing"
        elif expected != actual:
            status = "FAIL"
            worst = "FAIL"
            reason = "SHA-256 mismatch"
        else:
            status = "PASS"
            reason = ""
        rows.append({"prediction_version": p.get("prediction_version"), "status": status,
                     "reason": reason, "expected_sha256": expected, "actual_sha256": actual,
                     "path": p.get("_path")})
    return worst, rows

def _first(row: dict[str, str], *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return str(v)
    return ""

def load_captures(root: Path) -> list[dict[str, Any]]:
    candidates = list((root / "data" / "raw" / "capture_db").rglob("*.csv"))
    candidates += list((root / "data" / "processed" / "capture_events").rglob("*.csv"))
    captures: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for path in sorted(set(candidates)):
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                event = _first(row, "event_normalized", "event_type", "event", "type").lower()
                if event and "capture" not in event and "捕獲" not in event:
                    continue
                t = _first(row, "datetime_jst", "event_time_local", "datetime", "time_jst", "timestamp")
                lat = _first(row, "latitude", "lat")
                lon = _first(row, "longitude", "lon", "lng")
                if not (t and lat and lon):
                    continue
                try:
                    dt = parse_dt(t); la = float(lat); lo = float(lon)
                    count = max(1, int(float(_first(row, "event_count", "count") or "1")))
                except (ValueError, TypeError):
                    continue
                event_id = _first(row, "event_id", "id")
                op_night = _first(row, "operational_date", "night_date") or night_for(dt)
                for idx in range(1, count + 1):
                    key = (event_id, idx) if event_id else (dt.isoformat(), round(la, 7), round(lo, 7), idx)
                    if key in seen:
                        continue
                    seen.add(key)
                    captures.append({"datetime_jst": dt, "latitude": la, "longitude": lo,
                                     "night_date": op_night,
                                     "event_id": f"{event_id}#{idx}" if count > 1 and event_id else event_id,
                                     "event_group_id": event_id, "individual_index": idx,
                                     "source": str(path.relative_to(root))})
    return captures

def _archive_raw_bytes(archive_dir: Path) -> bytes:
    manifest_path = archive_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    parts = sorted(archive_dir.glob(manifest.get("part_glob", "part_*.txt")))
    if len(parts) != int(manifest["part_count"]):
        raise ValueError(f"GPX archive part count mismatch: {archive_dir}")
    text = "\n".join(p.read_text(encoding=manifest.get("encoding", "utf-8")) for p in parts)
    raw = text.encode(manifest.get("encoding", "utf-8"))
    if len(raw) != int(manifest["raw_size_bytes"]):
        raise ValueError(f"GPX archive byte size mismatch: {archive_dir}")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest["raw_sha256"]:
        raise ValueError(f"GPX archive SHA-256 mismatch: {archive_dir}")
    return raw

def _points_from_raw_gpx(raw: bytes) -> list[dict[str, Any]]:
    name = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".gpx", delete=False) as fh:
            fh.write(raw)
            name = fh.name
        return parse_gpx(Path(name))
    finally:
        if name:
            try:
                os.unlink(name)
            except FileNotFoundError:
                pass

def load_gpx_points(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    sources: list[tuple[str, bytes]] = []
    for path in sorted((root / "data" / "raw" / "gpx").rglob("*.gpx")):
        raw = path.read_bytes()
        sources.append((str(path.relative_to(root)), raw))
    for manifest in sorted((root / "data" / "raw" / "gpx_archives").rglob("manifest.json")):
        archive_dir = manifest.parent
        raw = _archive_raw_bytes(archive_dir)
        sources.append((str(archive_dir.relative_to(root)), raw))

    for source, raw in sources:
        digest = hashlib.sha256(raw).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        for p in _points_from_raw_gpx(raw):
            if p.get("exclude_point"):
                continue
            dt = p["time_utc"].astimezone(JST)
            out.append({"datetime_jst": dt, "latitude": float(p["latitude"]),
                        "longitude": float(p["longitude"]), "night_date": night_for(dt),
                        "source": source, "gpx_sha256": digest})
    return out

def distance_m(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax, ay = utm52n(float(a["latitude"]), float(a["longitude"]))
    bx, by = utm52n(float(b["latitude"]), float(b["longitude"]))
    return math.hypot(ax-bx, ay-by)

def build_exposure(points: list[dict[str, Any]], captures: list[dict[str, Any]], night: str) -> list[dict[str, Any]]:
    pts = [p for p in points if p["night_date"] == night]
    caps = [c for c in captures if c["night_date"] == night]
    units: dict[tuple[int,int,str], dict[str, Any]] = {}
    for p in pts:
        x,y = utm52n(p["latitude"],p["longitude"])
        t = p["datetime_jst"].replace(minute=(p["datetime_jst"].minute//10)*10,second=0,microsecond=0)
        key=(math.floor(x/100),math.floor(y/100),t.isoformat())
        u=units.setdefault(key,{"cell_x":key[0],"cell_y":key[1],"window_start_jst":t,
                                "point_count":0,"sample_latitude":p["latitude"],
                                "sample_longitude":p["longitude"],"label":0})
        u["point_count"]+=1
    for u in units.values():
        probe={"latitude":u["sample_latitude"],"longitude":u["sample_longitude"]}
        start=u["window_start_jst"]; end=start+timedelta(minutes=10)
        u["label"]=1 if any(start <= c["datetime_jst"] < end and distance_m(probe,c) <= 100 for c in caps) else 0
        u["observation"]="capture_observed" if u["label"] else "observed_negative"
        u["window_start_jst"]=start.isoformat()
    return sorted(units.values(),key=lambda x:(x["window_start_jst"],x["cell_x"],x["cell_y"]))

def _targets(prediction: dict[str, Any]) -> list[dict[str, Any]]:
    raw = prediction.get("targets_100m_10min") or prediction.get("targets") or []
    out=[]
    for i,t in enumerate(raw):
        lat=t.get("latitude",t.get("lat")); lon=t.get("longitude",t.get("lon",t.get("lng")))
        tv=t.get("predicted_time_jst",t.get("datetime_jst",t.get("time")))
        if lat is None or lon is None or not tv:
            continue
        try:
            out.append({"target_id":t.get("target_id",f"T{i+1}"),"latitude":float(lat),"longitude":float(lon),
                        "time":parse_dt(str(tv)),"radius_m":float(t.get("radius_m",100)),
                        "tolerance_min":float(t.get("time_tolerance_min",10))})
        except (ValueError,TypeError):
            continue
    return out

def score_prediction(prediction: dict[str, Any], captures: list[dict[str, Any]], night: str) -> dict[str, Any]:
    cutoff=parse_dt(str(prediction["cutoff_time"]))
    targets=_targets(prediction)
    actual=[c for c in captures if c["night_date"]==night and c["datetime_jst"]>cutoff]
    used:set[int]=set(); matches=[]
    for t in targets:
        best=None
        for i,c in enumerate(actual):
            if i in used: continue
            td=abs((c["datetime_jst"]-t["time"]).total_seconds())/60
            if td>t["tolerance_min"]: continue
            d=distance_m(t,c)
            if d>t["radius_m"]: continue
            key=(d,td)
            if best is None or key<best[0]: best=(key,i,c,d,td)
        if best:
            _,i,c,d,td=best; used.add(i)
            matches.append({"target_id":t["target_id"],"event_id":c.get("event_id",""),
                            "distance_m":round(d,2),"time_delta_min":round(td,2)})
    mt=len(matches); tc=len(targets); ac=len(actual)
    expected=prediction.get("expected_capture_count")
    expected_range=prediction.get("expected_capture_range")
    try:
        expected_value=float(expected) if expected is not None else None
    except (TypeError,ValueError):
        expected_value=None
    within_range=None
    if isinstance(expected_range,list) and len(expected_range)==2:
        try:
            lo,hi=float(expected_range[0]),float(expected_range[1])
            within_range=lo <= ac <= hi
        except (TypeError,ValueError):
            within_range=None
    return {"prediction_version":prediction.get("prediction_version"),"cutoff_time":cutoff.isoformat(),
            "formal_100m_10min_status":"SCORED" if tc else "NOT_PRODUCED",
            "target_count":tc,"captures_after_cutoff":ac,"matched_targets":mt,"matched_captures":mt,
            "precision":(mt/tc if tc else None),"recall":(mt/ac if tc and ac else None),"matches":matches,
            "expected_capture_count":expected_value,
            "capture_count_absolute_error":(abs(expected_value-ac) if expected_value is not None else None),
            "expected_capture_range":expected_range,
            "actual_within_expected_range":within_range}

def error_analysis(scores: list[dict[str, Any]]) -> dict[str, Any]:
    return {"versions":len(scores),
            "total_targets":sum(s["target_count"] for s in scores),
            "total_captures_after_cutoff":sum(s["captures_after_cutoff"] for s in scores),
            "total_matches":sum(s["matched_targets"] for s in scores),
            "note":"Version-level errors remain separated by cutoff; totals are descriptive only."}

def exposure_feature_summary(exposure: list[dict[str, Any]]) -> dict[str, Any]:
    by_hour: dict[str, dict[str, int]] = {}
    for row in exposure:
        hour = str(parse_dt(row["window_start_jst"]).hour)
        x = by_hour.setdefault(hour, {"observed_units": 0, "positive_units": 0})
        x["observed_units"] += 1
        x["positive_units"] += int(row["label"])
    rows = []
    for hour in sorted(by_hour, key=int):
        x = by_hour[hour]
        rows.append({"hour_jst": int(hour), **x,
                     "positive_unit_rate": x["positive_units"] / x["observed_units"] if x["observed_units"] else None})
    return {"time_of_night": rows,
            "note": "Observed-exposure association only; this is not causal feature importance."}

def diagnostic_ablation(prediction: dict[str, Any], captures: list[dict[str, Any]], night: str) -> dict[str, Any]:
    cutoff = parse_dt(str(prediction["cutoff_time"]))
    targets = _targets(prediction)
    actual = [c for c in captures if c["night_date"] == night and c["datetime_jst"] > cutoff]
    full = spatial = temporal = 0
    for t in targets:
        has_full = has_spatial = has_temporal = False
        for cap in actual:
            td = abs((cap["datetime_jst"] - t["time"]).total_seconds()) / 60
            d = distance_m(t, cap)
            has_spatial = has_spatial or d <= t["radius_m"]
            has_temporal = has_temporal or td <= t["tolerance_min"]
            has_full = has_full or (d <= t["radius_m"] and td <= t["tolerance_min"])
        full += int(has_full); spatial += int(has_spatial); temporal += int(has_temporal)
    return {"prediction_version": prediction.get("prediction_version"),
            "target_count": len(targets),
            "full_space_time_hits": full,
            "spatial_only_hits": spatial,
            "temporal_only_hits": temporal,
            "interpretation": "Diagnostic dimension ablation only; not a model-feature ablation."}

def historical_p0(root: Path, captures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base=root/"predictions"/"original"
    rows=[]
    if not base.exists(): return rows
    for night_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        preds=load_predictions(root,night_dir.name)
        p0=next((p for p in preds if p.get("prediction_version")=="P0"),None)
        if p0:
            try: rows.append({"night":night_dir.name,**score_prediction(p0,captures,night_dir.name)})
            except (KeyError,ValueError): pass
    return rows

def load_legacy_chronological_diagnostic(root: Path) -> dict[str, Any] | None:
    path = root / "reports" / "legacy_chronological_walkforward.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    valid = (
        data.get("evaluation_class") == "LEGACY_10M_CHRONOLOGICAL_DIAGNOSTIC"
        and data.get("official_100m_10min_kpi") is False
        and data.get("future_leakage_guard") is True
    )
    return {
        "status": "VALID" if valid else "INVALID",
        "path": str(path.relative_to(root)),
        "evaluation_class": data.get("evaluation_class"),
        "official_100m_10min_kpi": data.get("official_100m_10min_kpi"),
        "future_leakage_guard": data.get("future_leakage_guard"),
        "available_nights": data.get("available_nights", []),
        "summary": data.get("summary", {}),
        "group_ablation": data.get("group_ablation", []),
        "top_standardized_coefficients": data.get("top_standardized_coefficients", [])[:20],
        "warning": data.get("warning", ""),
    }

def legacy_candidate_hypotheses(diagnostic: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not diagnostic or diagnostic.get("status") != "VALID":
        return []
    rows = []
    for item in diagnostic.get("group_ablation", []):
        delta = item.get("mean_brier_delta_vs_full")
        if delta is None:
            continue
        if delta >= 0.01:
            interpretation = "Removing this group worsened legacy chronological Brier score."
            action = "retain_and_retest_in_current_100m_model"
        elif delta <= -0.01:
            interpretation = "Removing this group improved legacy chronological Brier score."
            action = "candidate_for_respecification_or_regularization"
        else:
            interpretation = "Legacy chronological effect was small by this threshold."
            action = "low_priority_retest"
        rows.append({
            "feature_group": item.get("omitted_group"),
            "mean_brier_delta_when_omitted": delta,
            "legacy_interpretation": interpretation,
            "candidate_action": action,
            "decision_status": "HYPOTHESIS_ONLY",
            "warning": "Legacy 10m diagnostic; not causal evidence and not an official 100m ±10min result.",
        })
    return rows

def write_outputs(root: Path, night: str, result: dict[str, Any]) -> Path:
    out=root/"reports"/"pdca"/night
    out.mkdir(parents=True,exist_ok=True)
    (out/"pdca_result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
    exposure=result.get("exposure",[])
    if exposure:
        with (out/"exposure_100m_10min.csv").open("w",encoding="utf-8-sig",newline="") as fh:
            w=csv.DictWriter(fh,fieldnames=list(exposure[0].keys())); w.writeheader(); w.writerows(exposure)
    lines=[f"# Habu AI PDCA {night}","",f"Overall: {result['overall_status']}","",
           "## Stages"]+[f"- {s['name']}: {s['status']} {s['reason']}".rstrip() for s in result["stages"]]
    if result.get("p0_score"):
        s=result["p0_score"]; lines += ["","## P0",f"- formal 100m ±10min: {s['formal_100m_10min_status']}",f"- targets: {s['target_count']}",f"- captures after cutoff: {s['captures_after_cutoff']}",f"- matches: {s['matched_targets']}",f"- precision: {s['precision']}",f"- recall: {s['recall']}",f"- expected capture count: {s['expected_capture_count']}",f"- count absolute error: {s['capture_count_absolute_error']}",f"- actual within expected range: {s['actual_within_expected_range']}"]
    legacy=result.get("legacy_chronological_diagnostic")
    if legacy:
        lines += ["","## Legacy chronological diagnostic",
                  f"- status: {legacy.get('status')}",
                  f"- future leakage guard: {legacy.get('future_leakage_guard')}",
                  f"- official 100m ±10min KPI: {legacy.get('official_100m_10min_kpi')}",
                  f"- completed folds: {legacy.get('summary',{}).get('completed_folds')}"]
    hypotheses=result.get("candidate_hypotheses",[])
    if hypotheses:
        lines += ["","## Candidate hypotheses"]
        lines += [f"- {h.get('feature_group')}: {h.get('candidate_action')} ({h.get('mean_brier_delta_when_omitted')})" for h in hypotheses]
    (out/"pdca_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return out

def run_pipeline(root: Path, night: str) -> dict[str, Any]:
    stages: list[Stage]=[]
    prediction_scope="ORIGINAL"
    preds=load_predictions(root,night)
    if not preds:
        preds=load_predictions(root,night,"recovered_original")
        if preds:
            prediction_scope="RECOVERED_ORIGINAL"
            stages.append(Stage("load_frozen_predictions","PARTIAL",
                                "Using retrospectively recovered prediction history; strict official score ineligible"))
        else:
            stages.append(Stage("load_frozen_predictions","BLOCKED",f"No ORIGINAL or recovered prediction for {night}"))
            result={"schema_version":"1.0","operational_night":night,"stages":[asdict(s) for s in stages],"overall_status":"BLOCKED"}
            write_outputs(root,night,result); return result
    else:
        stages.append(Stage("load_frozen_predictions","PASS",", ".join(p["prediction_version"] for p in preds)))

    istatus, integrity=verify_predictions(preds)
    stages.append(Stage("verify_prediction_integrity",istatus,"" if istatus=="PASS" else "See integrity report"))
    if istatus=="FAIL":
        result={"schema_version":"1.0","operational_night":night,"integrity":integrity,
                "stages":[asdict(s) for s in stages],"overall_status":"FAIL"}
        write_outputs(root,night,result); return result

    try:
        captures=load_captures(root); points=load_gpx_points(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        stages.append(Stage("load_actual_evidence","FAIL",str(exc)))
        result={"schema_version":"1.0","operational_night":night,"integrity":integrity,
                "stages":[asdict(s) for s in stages],"overall_status":"FAIL"}
        write_outputs(root,night,result); return result
    night_caps=[c for c in captures if c["night_date"]==night]; night_pts=[p for p in points if p["night_date"]==night]
    if not night_pts:
        stages.append(Stage("load_actual_evidence","BLOCKED","No auditable GPX points for night"))
        result={"schema_version":"1.0","operational_night":night,"integrity":integrity,
                "stages":[asdict(s) for s in stages],"overall_status":"BLOCKED"}
        write_outputs(root,night,result); return result
    stages.append(Stage("load_actual_evidence","PASS",f"{len(night_pts)} GPX points; {len(night_caps)} captures"))

    exposure=build_exposure(points,captures,night)
    stages.append(Stage("build_exposure","PASS",f"{len(exposure)} observed 100m x 10min units"))

    scores=[]
    for p in preds:
        try: scores.append(score_prediction(p,captures,night))
        except (KeyError,ValueError) as e:
            stages.append(Stage("score_predictions","PARTIAL",f"{p.get('prediction_version')}: {e}"))
    p0=next((s for s in scores if s["prediction_version"]=="P0"),None)
    realtime=[s for s in scores if s["prediction_version"]!="P0"]
    if not p0:
        stages.append(Stage("score_p0","PARTIAL","P0 not scorable"))
    elif p0.get("formal_100m_10min_status")!="SCORED":
        stages.append(Stage("score_p0","PARTIAL","P0 has no recoverable 100m ±10min targets; count forecast only"))
    elif prediction_scope!="ORIGINAL":
        stages.append(Stage("score_p0","PARTIAL","Recovered historical prediction is not strict official-score eligible"))
    else:
        stages.append(Stage("score_p0","PASS"))
    stages.append(Stage("score_realtime","PASS" if realtime else "PARTIAL","" if realtime else "No P1+ predictions"))

    errors=error_analysis(scores)
    stages.append(Stage("error_analysis","PASS"))

    feature_summary=exposure_feature_summary(exposure)
    stages.append(Stage("feature_analysis","PASS","Observed exposure by time-of-night"))

    ablation=diagnostic_ablation(next((p for p in preds if p.get("prediction_version")=="P0"),preds[0]),captures,night)
    stages.append(Stage("diagnostic_ablation","PASS","Space/time dimensions evaluated separately"))

    wf=historical_p0(root,captures)
    stages.append(Stage("walk_forward","PASS" if wf else "PARTIAL",
                        f"{len(wf)} historical ORIGINAL P0 nights" if wf else "No scorable historical P0"))

    legacy_diag=load_legacy_chronological_diagnostic(root)
    if legacy_diag is None:
        stages.append(Stage("legacy_chronological_diagnostic","PASS",
                            "Optional legacy diagnostic unavailable; current KPI unaffected"))
    elif legacy_diag.get("status")!="VALID":
        stages.append(Stage("legacy_chronological_diagnostic","FAIL","Legacy diagnostic contract invalid"))
    else:
        folds=legacy_diag.get("summary",{}).get("completed_folds",0)
        stages.append(Stage("legacy_chronological_diagnostic","PASS",
                            f"{folds} future-blocked legacy 10m folds; non-official diagnostic"))

    candidate_hypotheses=legacy_candidate_hypotheses(legacy_diag)
    stages.append(Stage("candidate_validation","PASS","No replay/candidate promoted; hypotheses remain unvalidated"))
    act={"decision":"NEED_MORE_DATA",
         "reason":"Candidate hypotheses require validation in the current 100m ±10min framework before promotion"}
    stages.append(Stage("act_decision","PASS",act["decision"]))

    statuses=[s.status for s in stages]
    overall="FAIL" if "FAIL" in statuses else "BLOCKED" if "BLOCKED" in statuses else "PARTIAL" if "PARTIAL" in statuses else "PASS"
    result={"schema_version":"1.0","operational_night":night,"prediction_scope":prediction_scope,"integrity":integrity,
            "evidence":{"gpx_points":len(night_pts),"captures":len(night_caps)},
            "exposure":exposure,"p0_score":p0,"realtime_scores":realtime,"error_analysis":errors,
            "feature_analysis":feature_summary,"diagnostic_ablation":ablation,
            "walk_forward":wf,
            "legacy_chronological_diagnostic":legacy_diag,
            "candidate_hypotheses":candidate_hypotheses,
            "act_decision":act,"stages":[asdict(s) for s in stages],"overall_status":overall}
    write_outputs(root,night,result)
    return result
