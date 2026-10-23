#!/usr/bin/env python3
"""Link recovered August field-log capture/reaction CANDIDATES to actual GPX.

Read-only scientific intake, not canonical import and not training.
The extracted TXT hashes refer to a saved representation, never original TXT bytes.
Unknown quantity and capture ownership remain unresolved after a GPS match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gpx_audit import utm52n

JST = ZoneInfo("Asia/Tokyo")
REVIEW_PATH = "evidence/master-goal-1642/recovered_sources/overlap-candidate-review.json"
EXPECTED_REVIEW_SCHEMA = "habu_overlap_candidate_review_audit_v1"
MAX_RAW_BYTES = 15_000_000
MAX_GPX_POINTS = 75_000
MAX_CANDIDATES = 400
MAX_MATCH_SECONDS = 600
MAX_MATCH_DISTANCE_M = 100.0

class IntakeError(ValueError):
    pass

def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _native_stamp(source):
    m = re.fullmatch(r"(\d{4})/(\d\d)/(\d\d)\s+(\d{1,2}):(\d\d)", source)
    if not m:
        raise IntakeError("Native field log timestamp is not exact to minute")
    return datetime(*(int(x) for x in m.groups()), tzinfo=JST)

def _night(dt):
    local = dt.astimezone(JST)
    if local.hour < 7:
        local -= timedelta(days=1)
    return local.date().isoformat()

def _read_review(root):
    p = root / REVIEW_PATH
    payload = json.loads(p.read_text(encoding="utf-8"))
    if payload.get("schema") != EXPECTED_REVIEW_SCHEMA:
        raise IntakeError("Unsupported prior recovered review schema")
    sources = {x["path"]: x for x in payload["sources"]}
    src = "evidence/master-goal-1642/recovered_sources/august-extracted.txt"
    if src not in sources:
        raise IntakeError("August extracted source not documented")
    extracted = root / src
    if digest_file(extracted) != sources[src]["content_sha256"]:
        raise IntakeError("Extracted saved-read bytes changed; refuse review-derived matches")
    if sources[src]["hash_scope"] != "extracted_read_content_not_original_bytes":
        raise IntakeError("Extraction provenance changed unexpectedly")
    text = extracted.read_text(encoding="utf-8")
    if len(payload["capture_candidates"]) > MAX_CANDIDATES:
        raise IntakeError("Candidate budget exceeded")
    for kind in ("capture_candidates", "reaction_controls", "search_markers"):
        for row in payload[kind]:
            if row["source_extracted_path"] != "august-extracted.txt":
                raise IntakeError("Unexpected event source")
            if row["raw_block"].strip() not in text:
                raise IntakeError("Raw event candidate not present in saved extracted log")
            when = _native_stamp(row["native_timestamp"])
            if _night(when) != row["operational_night_07_jst"]:
                raise IntakeError("Recovered night does not follow 07:00 JST rule")
    return payload, sources[src], digest_file(p)

def _gpx_match(path, expected_digest, captures, reactions):
    if not path.is_file() or path.stat().st_size > MAX_RAW_BYTES:
        raise IntakeError("Missing/oversized actual GPX source")
    actual = digest_file(path)
    if actual != expected_digest:
        raise IntakeError("GPX content differs from previously audited digest")
    target_events = []
    for group, records in (("capture", captures), ("reaction", reactions)):
        for row in records:
            t = _native_stamp(row["native_timestamp"])
            x, y = utm52n(float(row["native_latitude"]), float(row["native_longitude"]))
            target_events.append({
                "review_id": row["review_id"], "type": group, "when": t,
                "utm": (x, y), "best": None
            })
    point_count = 0
    rejected = Counter()
    first_time = last_time = None
    try:
        with path.open("rb") as stream:
            # Segment timestamp gaps are not filled; a nearby point only
            # corroborates a location and event time, never exposure completeness.
            for _, elem in ET.iterparse(stream, events=("end",)):
                if elem.tag.rsplit("}", 1)[-1] != "trkpt":
                    continue
                point_count += 1
                if point_count > MAX_GPX_POINTS:
                    raise IntakeError("GPX point safety budget exceeded")
                stamp = elem.find("{*}time")
                if stamp is None or not stamp.text:
                    rejected["missing_time"] += 1
                    elem.clear()
                    continue
                dt = datetime.fromisoformat(stamp.text.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    rejected["naive_time"] += 1
                    elem.clear()
                    continue
                dt = dt.astimezone(JST)
                first_time = min(first_time, dt) if first_time else dt
                last_time = max(last_time, dt) if last_time else dt
                hdop = elem.find("{*}hdop")
                if hdop is not None and hdop.text:
                    value = float(hdop.text)
                    if not math.isfinite(value) or value < 0 or value > 10:
                        rejected["hdop_over_10"] += 1
                        elem.clear()
                        continue
                lat, lon = float(elem.attrib["lat"]), float(elem.attrib["lon"])
                if not all(math.isfinite(v) for v in (lat, lon)) or not 27 <= lat <= 29 or not 128 <= lon <= 130.5:
                    rejected["invalid_coordinates"] += 1
                    elem.clear()
                    continue
                for target in target_events:
                    seconds = abs((dt-target["when"]).total_seconds())
                    if seconds > MAX_MATCH_SECONDS:
                        continue
                    # cheap geographic bound before projecting to UTM meters
                    tx, ty = target["utm"]
                    px, py = utm52n(lat, lon)
                    dist = math.hypot(px-tx, py-ty)
                    if dist > MAX_MATCH_DISTANCE_M:
                        continue
                    key = (seconds, dist)
                    if target["best"] is None or key < target["best"]:
                        target["best"] = key
                elem.clear()
    except (ET.ParseError, KeyError, TypeError, ValueError) as e:
        raise IntakeError("Malformed actual GPX track source: " + str(e)) from e
    if point_count < 2:
        raise IntakeError("GPX has no usable samples")
    matches = {}
    for item in target_events:
        best = item["best"]
        matches[item["review_id"]] = (
            {"match_status": "GPX_SPACETIME_CORROBORATION_ONLY",
             "absolute_time_delta_s": round(best[0], 3),
             "spatial_distance_m": round(best[1], 3)}
            if best is not None else {"match_status": "NO_GPX_PROXIMITY_MATCH"})
    return {
        "source_sha256": actual, "point_count": point_count,
        "first_point_jst": first_time.isoformat() if first_time else None,
        "last_point_jst": last_time.isoformat() if last_time else None,
        "gps_quality_rejected": dict(rejected),
        "matches": matches,
    }

def reconcile(root=ROOT):
    root = Path(root)
    review, source, review_sha = _read_review(root)
    captures_by_night = defaultdict(list)
    reactions_by_night = defaultdict(list)
    for row in review["capture_candidates"]:
        if row["native_event_kind"] != "捕獲" or not any("ハブ" in x for x in row["native_species_text"]):
            raise IntakeError("Non-Habu or noncapture candidate mislabeled")
        captures_by_night[row["operational_night_07_jst"]].append(row)
    for row in review["reaction_controls"]:
        reactions_by_night[row["operational_night_07_jst"]].append(row)
    gpx_bound = {x["operational_night"]: x for x in review["gpx_temporal_diagnostics"]}
    by_night = {}
    for night in sorted(gpx_bound):
        path = root / "data/raw/gpx" / (night+"__legacy.gpx")
        info = _gpx_match(path,gpx_bound[night]["sha256"],captures_by_night[night],reactions_by_night[night])
        captures = []
        for row in captures_by_night[night]:
            record = {
                "source_review_id": row["review_id"], "native_event_kind": "捕獲",
                "source_extracted_line": row["line_start"],
                "native_timestamp": row["native_timestamp"],
                "operational_night": night,
                "source_role": "RECOVERED_FIELD_LOG_CANDIDATE",
                "explicit_exact_individual_count": row["exact_individual_count"],
                "minimum_possible_individuals": row["individual_count_lower_bound"],
                "owner_capture_verified": False,
                "workbook_role_conflict": any(x.get("target_role") == "反応" for x in row["workbook_corroboration"]),
                "training_positive_eligible": False,
                "review_issues": row["review_issues"],
                **info["matches"][row["review_id"]]
            }
            if record["explicit_exact_individual_count"] is not None:
                raise IntakeError("Unreviewed quantity promotion")
            captures.append(record)
        reactions = []
        for row in reactions_by_night[night]:
            raw = row["raw_block"]
            is_habu_roadkill = row["native_event_kind"] == "轢死" and "\nハブ\n" in raw
            reactions.append({
                "source_review_id": row["review_id"],
                "category": "HABU_ROADKILL_NONCAPTURE" if is_habu_roadkill else "OTHER_SPECIES_SIGHTING_NONCAPTURE",
                "native_event_kind": row["native_event_kind"],
                "source_extracted_line": row["line_start"],
                "training_positive_eligible": False,
                **info["matches"][row["review_id"]]
            })
        markers = [
            {"native_event_kind": x["native_event_kind"],
             "native_timestamp": x["native_timestamp"],
             "source_extracted_line": x["line_start"]}
            for x in review["search_markers"] if x["operational_night_07_jst"] == night
        ]
        by_night[night] = {
            "actual_gpx_sha256": info["source_sha256"],
            "actual_gpx_points": info["point_count"],
            "gps_quality_rejected": info["gps_quality_rejected"],
            "capture_candidate_statements": captures,
            "reaction_controls": reactions,
            "search_markers": markers,
            "exhaustive_owner_capture_ledger_verified": False,
            "complete_search_exposure_verified": False,
            "eligible_positive_individuals": 0,
            "eligible_negative_units": 0,
            "learning_snapshot_eligible": False,
            "source_status": "RECOVERED_LOG_MATCHED_NOT_CANONICAL"
        }
    return {
        "schema_version": "habu-august-extracted-gpx-candidate-reconciliation-v1",
        "status": "EVENT_CANDIDATES_CORROBORATED_TRAINING_BLOCKED",
        "representation": "derived_recovered_read_content_not_original_txt_bytes",
        "extracted_source_path": source["path"],
        "extracted_source_sha256": source["content_sha256"],
        "candidate_review_sha256": review_sha,
        "gpx_nights": by_night,
        "candidate_event_mentions_total": sum(len(x["capture_candidate_statements"]) for x in by_night.values()),
        "gpx_proximity_matched_capture_mentions": sum(
            x["match_status"]=="GPX_SPACETIME_CORROBORATION_ONLY"
            for night in by_night.values() for x in night["capture_candidate_statements"]
        ),
        "gpx_proximity_matched_reaction_controls": sum(
            x["match_status"]=="GPX_SPACETIME_CORROBORATION_ONLY"
            for night in by_night.values() for x in night["reaction_controls"]
        ),
        "exact_owner_capture_positive_individuals": 0,
        "observed_negative_units": 0,
        "unknown_passage_not_negative": True,
        "independent_original_binary_verification": False,
        "formally_eligible_training_rows": 0,
        "official_1km_top10_scored": False,
        "official_100m_10min_scored": False,
        "blockers": [
            "ORIGINAL_FIELD_LOG_BYTES_UNAVAILABLE",
            "CAPTURE_QUANTITY_UNSTATED",
            "OWNER_IDENTITY_NOT_EXPLICIT_IN_CAPTURE_BLOCKS",
            "WORKBOOK_TARGET_ROLE_CONFLICT",
            "COMPLETE_NIGHT_SEARCH_AND_OUTCOME_UNVERIFIED",
            "EX_ANTE_FEATURES_AND_FULL_FORECAST_UNIVERSE_MISSING"
        ]
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=reconcile(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":result["status"],
        "capture_candidate_mentions":result["candidate_event_mentions_total"],
        "matched_capture_mentions":result["gpx_proximity_matched_capture_mentions"],
        "matched_reactions":result["gpx_proximity_matched_reaction_controls"],
        "eligible_owner_positive_individuals":0, "verified_negative_units":0
    },ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
