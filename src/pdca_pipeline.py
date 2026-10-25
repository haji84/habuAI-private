from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
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
        payload["_directory_version"] = d.name
        out.append(payload)
    return out

def prediction_contract_errors(payload: dict[str, Any], night: str, scope: str) -> list[str]:
    errors = []
    if payload.get("prediction_class") != scope:
        errors.append("prediction class does not match storage scope")
    if payload.get("operational_night") != night:
        errors.append("operational night does not match storage path")
    version = payload.get("prediction_version")
    if not isinstance(version, str) or not re.fullmatch(r"P(0|[1-9][0-9]*)", version):
        errors.append("prediction version must be canonical P0, P1, P2...")
    if payload.get("prediction_version") != payload.get("_directory_version", payload.get("prediction_version")):
        errors.append("prediction version does not match storage path")
    try:
        parse_dt(str(payload["cutoff_time"]))
    except (KeyError, ValueError, TypeError):
        errors.append("invalid cutoff_time")
    return errors


def verify_predictions(predictions: list[dict[str, Any]], *, root: Path | None = None,
                       night: str | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Verify content digests and, for canonical disk records, the immutable Freeze bytes.

    Historic/hand-entered predictions lacking a sidecar remain usable only for
    descriptive diagnostics. A present but corrupted sidecar is an integrity FAIL.
    This does NOT establish production issuance authority or official-score eligibility.
    """
    rows = []
    worst = "PASS"
    for p in predictions:
        expected = p.get("payload_sha256")
        actual = canonical_prediction_hash(p)
        sidecar_status = "NOT_CHECKED"
        if not expected:
            status, reason = "PARTIAL", "payload_sha256 missing"
        elif expected != actual:
            status, reason = "FAIL", "SHA-256 mismatch"
        else:
            status, reason = "PASS", ""
        # Read only the canonical ORIGINAL path implied by the loader; never trust
        # a payload-supplied path to decide where filesystem evidence lives.
        version = p.get("_directory_version")
        canonical_path = (f"predictions/original/{night}/{version}/prediction.json"
                          if night and isinstance(version, str) and
                          re.fullmatch(r"P(0|[1-9][0-9]*)", version) else None)
        stored_path = p.get("_path")
        if (root is not None and canonical_path is not None and
                isinstance(stored_path, str) and stored_path.replace("\\", "/") == canonical_path and
                p.get("prediction_class") == "ORIGINAL"):
            from master_contracts import canonical_bytes, safe_path
            try:
                sidecar = safe_path(root, f"predictions/original/{night}/{version}/sha256.txt")
                record_path = safe_path(root, canonical_path)
                if not sidecar.exists():
                    sidecar_status = "MISSING"
                    if status == "PASS":
                        status, reason = "PARTIAL", "Immutable Freeze sidecar missing"
                elif not sidecar.is_file() or sidecar.stat().st_size > 130:
                    sidecar_status = "INVALID"
                    status, reason = "FAIL", "Invalid Freeze sidecar file"
                elif sidecar.read_bytes() != (str(expected) + "  prediction.json\n").encode("ascii"):
                    sidecar_status = "MISMATCH"
                    status, reason = "FAIL", "Immutable Freeze sidecar mismatch"
                else:
                    sidecar_status = "MATCH"
                    canonical_record = {k: v for k, v in p.items() if not k.startswith("_")}
                    if record_path.read_bytes() != canonical_bytes(canonical_record) + b"\n":
                        sidecar_status = "NONCANONICAL_BYTES"
                        status, reason = "FAIL", "Immutable prediction.json bytes changed"
            except (OSError, ValueError, UnicodeError) as exc:
                sidecar_status = "INVALID"
                status, reason = "FAIL", f"Freeze sidecar verification failed: {type(exc).__name__}"
        if status == "FAIL":
            worst = "FAIL"
        elif status == "PARTIAL" and worst != "FAIL":
            worst = "PARTIAL"
        rows.append({"prediction_version": p.get("prediction_version"), "status": status,
                     "reason": reason, "expected_sha256": expected, "actual_sha256": actual,
                     "path": p.get("_path"), "sidecar_status": sidecar_status})
    return worst, rows

def _first(row: dict[str, str], *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return str(v)
    return ""

def load_captures(root: Path) -> list[dict[str, Any]]:
    # Shared strict parser; the full audit retains rejected rows and source eligibility.
    from evidence_audit import audit_captures
    audit, _ = audit_captures(root)
    return _individual_captures(audit["events"])


def _individual_captures(events):
    captures = []
    for event in events:
        for index in range(event["capture_count"]):
            captures.append({**event, "datetime_jst": parse_dt(event["datetime_jst"]),
                             "event_group_id": event["event_id"],
                             "event_id": event["event_id"] + (f"#{index+1}" if event["capture_count"] > 1 else ""),
                             "individual_index": index+1})
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

def valid_coordinates(lat: float, lon: float) -> bool:
    return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180


def unit_key(row: dict[str, Any], dt: datetime) -> tuple[int, int, str]:
    x, y = utm52n(row["latitude"], row["longitude"])
    start = dt.astimezone(JST).replace(minute=(dt.astimezone(JST).minute // 10) * 10, second=0, microsecond=0)
    return math.floor(x / 100), math.floor(y / 100), start.isoformat()


def build_exposure(points: list[dict[str, Any]], captures: list[dict[str, Any]], night: str) -> list[dict[str, Any]]:
    positives = {unit_key(c, c["datetime_jst"]) for c in captures if c["night_date"] == night}
    units = {}
    for point in sorted(points, key=lambda p: (p["datetime_jst"], p["latitude"], p["longitude"])):
        if point["night_date"] != night:
            continue
        key = unit_key(point, point["datetime_jst"])
        row = units.setdefault(key, {"cell_x": key[0], "cell_y": key[1], "window_start_jst": key[2],
                                    "point_count": 0, "sample_latitude": point["latitude"],
                                    "sample_longitude": point["longitude"], "label": None})
        row["point_count"] += 1
        row["observation"] = "UNKNOWN"
    return sorted(units.values(), key=lambda r: (r["window_start_jst"], r["cell_x"], r["cell_y"]))

def _targets(prediction: dict[str, Any]) -> list[dict[str, Any]]:
    raw = prediction.get("targets_100m_10min") or prediction.get("targets") or []
    out=[]
    for i,t in enumerate(raw):
        lat=t.get("latitude",t.get("lat")); lon=t.get("longitude",t.get("lon",t.get("lng")))
        tv=t.get("predicted_time_jst",t.get("datetime_jst",t.get("time")))
        if lat is None or lon is None or not tv:
            continue
        try:
            if not valid_coordinates(float(lat), float(lon)):
                continue
            out.append({"target_id":t.get("target_id",f"T{i+1}"),"latitude":float(lat),"longitude":float(lon),
                        "time":parse_dt(str(tv)),"radius_m":100,
                        "tolerance_min":10})
        except (ValueError,TypeError):
            continue
    return out

def score_prediction(prediction: dict[str, Any], captures: list[dict[str, Any]], night: str,
                     exposure: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    cutoff = parse_dt(str(prediction["cutoff_time"]))
    all_targets = _targets(prediction)
    targets = sorted((t for t in all_targets if t["time"] > cutoff and night_for(t["time"]) == night),
                     key=lambda t: (str(t["target_id"]), t["time"], t["latitude"], t["longitude"]))
    actual = sorted((c for c in captures if c["night_date"] == night and c["datetime_jst"] > cutoff),
                    key=lambda c: (str(c.get("event_id", "")), c["datetime_jst"], c["latitude"], c["longitude"]))
    edges = []
    for t in targets:
        eligible = []
        for i, c in enumerate(actual):
            td = abs((c["datetime_jst"] - t["time"]).total_seconds()) / 60
            d = distance_m(t, c)
            if td <= 10 and d <= 100:
                eligible.append((d, td, i))
        edges.append([i for _, _, i in sorted(eligible)])
    # Augmenting paths allow a flexible target to move, preserving maximum cardinality.
    owners: dict[int, int] = {}
    def augment(ti: int, seen: set[int]) -> bool:
        for ci in edges[ti]:
            if ci in seen:
                continue
            seen.add(ci)
            if ci not in owners or augment(owners[ci], seen):
                owners[ci] = ti
                return True
        return False
    for ti in range(len(targets)):
        augment(ti, set())
    matched = set(owners.values())
    matches = []
    for ci, ti in sorted(owners.items(), key=lambda pair: pair[1]):
        t, c = targets[ti], actual[ci]
        matches.append({"target_id": t["target_id"], "event_id": c.get("event_id", ""),
                        "distance_m": round(distance_m(t, c), 2),
                        "time_delta_min": round(abs((c["datetime_jst"] - t["time"]).total_seconds()) / 60, 2)})
    negative_units = {(r["cell_x"], r["cell_y"], parse_dt(r["window_start_jst"]).isoformat())
                      for r in exposure or [] if r.get("observation") == "observed_negative" and r.get("label") == 0}
    negatives = sum(i not in matched and unit_key(t, t["time"]) in negative_units for i, t in enumerate(targets))
    mt, tc, ac = len(matches), len(targets), len(actual)
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
            "excluded_nonprospective_targets":len(all_targets)-tc,
            "observed_negative_targets":negatives,"unknown_targets":tc-mt-negatives,
            "precision":(mt/(mt+negatives) if mt+negatives else None),"recall":(mt/ac if tc and ac else None),"matches":matches,
            "expected_capture_count":expected_value,
            "capture_count_status":"NOT_VALIDATED",
            "capture_count_absolute_error":None,
            "diagnostic_capture_count_absolute_error":(abs(expected_value-ac) if expected_value is not None else None),
            "expected_capture_range":expected_range,
            "actual_within_expected_range":None,
            "diagnostic_actual_within_expected_range":within_range,
            "strict_official_score_eligible":False,"provenance_status":"NOT_VALIDATED",
            "provenance_reason":"Issuance lineage and observation completeness require independent validation"}

def error_analysis(scores: list[dict[str, Any]]) -> dict[str, Any]:
    return {"versions":len(scores),
            "total_targets":sum(s["target_count"] for s in scores),
            "total_captures_after_cutoff":sum(s["captures_after_cutoff"] for s in scores),
            "total_matches":sum(s["matched_targets"] for s in scores),
            "note":"Version-level errors remain separated by cutoff; totals are descriptive only."}

def exposure_feature_summary(exposure: list[dict[str, Any]]) -> dict[str, Any]:
    by_hour = {}
    for row in exposure:
        hour = str(parse_dt(row["window_start_jst"]).hour)
        value = by_hour.setdefault(hour, {"sampled_units": 0, "observed_units": 0, "positive_units": 0})
        value["sampled_units"] += int(row.get("point_count", 0) > 0)
        value["observed_units"] += int(row.get("label") is not None)
        value["positive_units"] += int(row.get("label") == 1)
    rows = [{"hour_jst": int(hour), **value,
             "positive_unit_rate": value["positive_units"] / value["observed_units"] if value["observed_units"] else None}
            for hour, value in sorted(by_hour.items(), key=lambda item: int(item[0]))]
    return {"time_of_night": rows, "note": "Sampled coverage is separate from source-qualified observation; UNKNOWN is not Negative."}

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

def historical_p0(root: Path, captures: list[dict[str, Any]], before_night: str | None = None) -> list[dict[str, Any]]:
    base=root/"predictions"/"original"
    rows=[]
    if not base.exists(): return rows
    for night_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        if before_night is not None and night_dir.name >= before_night:
            continue
        preds=load_predictions(root,night_dir.name)
        p0=next((p for p in preds if p.get("prediction_version")=="P0"),None)
        if p0 and verify_predictions([p0])[0] == "PASS" and not prediction_contract_errors(p0, night_dir.name, "ORIGINAL"):
            try: rows.append({"night":night_dir.name,"evaluation_class":"HISTORICAL_DIAGNOSTIC",**score_prediction(p0,captures,night_dir.name)})
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

def run_pipeline(root: Path, night: str, *, audited_evidence=None) -> dict[str, Any]:
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
        stages.append(Stage("load_frozen_predictions","PASS",", ".join(p["_directory_version"] for p in preds)))

    istatus, integrity=verify_predictions(preds, root=root, night=night)
    for p, row in zip(preds, integrity):
        errors = prediction_contract_errors(p, night, prediction_scope)
        if errors:
            row["status"] = "FAIL"
            row["reason"] = "; ".join(errors)
            istatus = "FAIL"
    stages.append(Stage("verify_prediction_integrity",istatus,"" if istatus=="PASS" else "See integrity report"))
    if istatus=="FAIL":
        result={"schema_version":"1.0","operational_night":night,"integrity":integrity,
                "stages":[asdict(s) for s in stages],"overall_status":"FAIL"}
        write_outputs(root,night,result); return result

    try:
        from evidence_audit import audit_evidence
        audited = audited_evidence if audited_evidence is not None else audit_evidence(root, night)
        if audited["status"] == "BLOCKED":
            stages.append(Stage("load_actual_evidence","BLOCKED","RUNTIME_BLOCKED: evidence audit limits"))
            result={"schema_version":"1.0","operational_night":night,"integrity":integrity,
                    "stages":[asdict(s) for s in stages],"overall_status":"BLOCKED",
                    "evidence_requirements":audited["input_requirements"]}
            write_outputs(root,night,result); return result
        if audited["status"] == "FAIL":
            raise ValueError("Evidence audit failed: " + str([c for c in audited["checks"] if c["status"] == "FAIL"]))
        captures = _individual_captures(audited["capture_audit"]["events"])
        exposure = [u for u in audited["observation_units"] if u["night_date"] == night]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        stages.append(Stage("load_actual_evidence","FAIL",str(exc)))
        result={"schema_version":"1.0","operational_night":night,"integrity":integrity,
                "stages":[asdict(s) for s in stages],"overall_status":"FAIL"}
        write_outputs(root,night,result); return result
    night_caps=[c for c in captures if c["night_date"]==night]
    point_count = sum(u["point_count"] for u in exposure)
    if not point_count:
        stages.append(Stage("load_actual_evidence","BLOCKED","No auditable GPX points for night"))
        result={"schema_version":"1.0","operational_night":night,"integrity":integrity,
                "stages":[asdict(s) for s in stages],"overall_status":"BLOCKED"}
        write_outputs(root,night,result); return result
    stages.append(Stage("load_actual_evidence","PASS",f"{point_count} GPX points; {len(night_caps)} captures"))

    observed_count = sum(u["label"] is not None for u in exposure)
    stages.append(Stage("build_exposure", "PASS" if observed_count == len(exposure) else "PARTIAL",
                        f"{len(exposure)} sampled/outcome units; {observed_count} eligible observations; remainder UNKNOWN"))

    scores=[]
    for p in preds:
        try: scores.append(score_prediction(p,captures,night,exposure=exposure))
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
        stages.append(Stage("score_p0","NOT_VALIDATED","Diagnostic score only; issuance lineage and observation completeness unvalidated"))
    stages.append(Stage("score_realtime","NOT_VALIDATED" if realtime else "PARTIAL","" if realtime else "No P1+ predictions"))

    errors=error_analysis(scores)
    stages.append(Stage("error_analysis","PASS"))

    feature_summary=exposure_feature_summary(exposure)
    stages.append(Stage("feature_analysis","PASS","Observed exposure by time-of-night"))

    ablation=diagnostic_ablation(next((p for p in preds if p.get("prediction_version")=="P0"),preds[0]),captures,night)
    stages.append(Stage("diagnostic_ablation","PASS","Space/time dimensions evaluated separately"))

    wf=historical_p0(root,captures,before_night=night)
    stages.append(Stage("model_evaluation","NOT_VALIDATED",
                        f"{len(wf)} validated-hash historical diagnostics; no held-out model evaluation"))

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
    stages.append(Stage("candidate_validation","NOT_VALIDATED","No replay/candidate promoted; hypotheses remain unvalidated"))
    act={"decision":"NEED_MORE_DATA",
         "reason":"Candidate hypotheses require validation in the current 100m ±10min framework before promotion"}
    stages.append(Stage("act_decision","PASS",act["decision"]))

    statuses=[s.status for s in stages]
    overall="FAIL" if "FAIL" in statuses else "BLOCKED" if "BLOCKED" in statuses else "PARTIAL" if any(s in statuses for s in ("PARTIAL", "NOT_VALIDATED")) else "PASS"
    result={"schema_version":"1.0","operational_night":night,"prediction_scope":prediction_scope,"integrity":integrity,
            "evidence":{"gpx_points":point_count,"captures":len(night_caps)},
            "exposure":exposure,"evidence_requirements":audited["input_requirements"],"p0_score":p0,"realtime_scores":realtime,"error_analysis":errors,
            "feature_analysis":feature_summary,"diagnostic_ablation":ablation,
            "walk_forward":wf,
            "legacy_chronological_diagnostic":legacy_diag,
            "candidate_hypotheses":candidate_hypotheses,
            "act_decision":act,"stages":[asdict(s) for s in stages],"overall_status":overall}
    write_outputs(root,night,result)
    return result
