#!/usr/bin/env python3
"""Join the newly recovered byte-identical August primary field log to 13 real GPX.

Source-event diagnostics only. A user-uploaded log can establish an explicit
capture statement; it does not, without role/quantity review and complete
observer-effort proof, establish eligible supervised Positive/Negative units.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from reconcile_august_field_candidates import _gpx_match, _native_stamp, _night
from inventory_real_gpx_sources import build_inventory

RAW = "data/raw/habu_logs/2026/2026-08-02_to_2026-08-30.owner-raw.txt"
META = "evidence/raw_intake/august-2026-native-habu-log-recovery.json"
OLD_REVIEW = "evidence/master-goal-1642/recovered_sources/overlap-candidate-review.json"
PROTECTED = "evidence/master-goal-1642/baseline-audit.json"
_DATE = re.compile(r"^2026/08/(\d\d)\s+(\d{1,2}):(\d\d)$")
_NUMBER = re.compile(r"^\d{1,3}(?:\.\d+)?$")
_COUNT = re.compile(r"(?<!\d)(\d+)匹")


class OriginalLogError(ValueError):
    pass


def load_original(root):
    original = (root/RAW).read_bytes()
    metadata = json.loads((root/META).read_text(encoding="utf-8"))
    actual_sha=hashlib.sha256(original).hexdigest()
    if (metadata["sha256"] != actual_sha
            or metadata["source_bytes"] != len(original)
            or metadata["line_count"] != 10016
            or b"\r" in original
            or not original.startswith("ハブログ\n".encode())
            or original.endswith(b"\n")):
        raise OriginalLogError("Native August original byte/checksum/format mismatch")
    return original.decode("utf-8"), metadata


def parse_original(root):
    text,meta=load_original(root)
    lines=text.split("\n")
    starts=[]
    for idx,line in enumerate(lines):
        if _DATE.fullmatch(line.strip()):
            starts.append(idx)
    statements=[]; reactions=[]; markers=[]; timed_nights=Counter()
    for i,start in enumerate(starts):
        end=starts[i+1] if i+1<len(starts) else len(lines)
        raw_lines=lines[start:end]
        when_text=raw_lines[0].strip()
        when=_native_stamp(when_text)
        night=_night(when)
        timed_nights[night] += 1
        payload=[x.strip() for x in raw_lines[1:]]
        event_kind=next((x for x in payload[:5] if x in ("捕獲","目撃","轢死")),None)
        is_habu_capture=(event_kind=="捕獲" and any(
            x.startswith("ハブ捕獲") and "捕獲なし" not in x
            for x in payload))
        is_habu_roadkill=(event_kind=="轢死" and "ハブ" in payload)
        is_habu_sighting=(event_kind=="目撃" and "ハブ" in payload)
        is_hime_sighting=(event_kind=="目撃" and "ヒメハブ" in payload)
        has_marker=any(x in ("エリア探索開始","エリア探索終了") for x in payload)
        if not (is_habu_capture or is_habu_roadkill or is_habu_sighting or is_hime_sighting or has_marker):
            continue
        pair=None
        for j in range(len(payload)-1):
            if _NUMBER.fullmatch(payload[j]) and _NUMBER.fullmatch(payload[j+1]):
                lat=float(payload[j]);lon=float(payload[j+1])
                if 27 <= lat <= 29 and 128 <= lon <= 130.5:
                    pair=(payload[j],payload[j+1])
                    break
        ident=f"aug2026-native-L{start+1:05d}"
        base={
            "review_id":ident,
            "source_original_line":start+1,
            "native_timestamp":when_text,
            "operational_night_07_jst":night,
            "exact_event_time_hhmm":True,
            "source_kind":"LIBRARY_USER_UPLOADED_NATIVE_LOG",
            "original_source_sha256":meta["sha256"],
        }
        if is_habu_capture:
            notes=[x for x in payload if x.startswith("ハブ捕獲")]
            explicit=[]
            for phrase in notes:
                explicit += [int(n) for n in _COUNT.findall(phrase)]
            if len(explicit)>1 or any(c<1 or c>100 for c in explicit):
                raise OriginalLogError("Conflicting explicit quantity in native capture block")
            item={**base,
                "native_event_kind":"捕獲","native_species_text":notes,
                "exact_individual_count":explicit[0] if explicit else None,
                "minimum_possible_individuals":explicit[0] if explicit else 1,
                "individual_count_is_explicit":bool(explicit),
                "owner_capture_verified":False,
                "source_coordinates_present":bool(pair),
                "training_positive_eligible":False,
                "reason":"Owner identity, duplicates and complete outcome ledger require independent review"
            }
            if pair: item.update(native_latitude=pair[0],native_longitude=pair[1])
            statements.append(item)
        elif is_habu_roadkill or is_habu_sighting or is_hime_sighting:
            item={**base,
                "native_event_kind":event_kind,
                "category":"HABU_ROADKILL_NONCAPTURE" if is_habu_roadkill else
                           "HABU_SIGHTING_NONCAPTURE" if is_habu_sighting else
                           "HIMEHABU_SIGHTING_NONCAPTURE",
                "source_coordinates_present":bool(pair),
                "training_positive_eligible":False
            }
            if pair:item.update(native_latitude=pair[0],native_longitude=pair[1])
            reactions.append(item)
        if has_marker:
            markers.append({**base,
                "search_start": "エリア探索開始" in payload,
                "search_end": "エリア探索終了" in payload,
                "complete_search_exposure_verified":False
            })
    return statements,reactions,markers,meta,timed_nights


def make_actual_join(root=ROOT, *, inventory=None):
    root=Path(root)
    captures,reactions,markers,meta,timed_nights=parse_original(root)
    overlap=json.loads((root/OLD_REVIEW).read_text(encoding="utf-8"))
    # Prevent aliasing the old extracted 11 statements as eleven *new* events.
    current={(x["native_timestamp"], x.get("native_latitude"), x.get("native_longitude"))
             for x in captures}
    aliases=[]
    for row in overlap["capture_candidates"]:
        key=(row["native_timestamp"],row["native_latitude"],row["native_longitude"])
        if key not in current:
            raise OriginalLogError("Recovered extraction candidate missing from native source")
        aliases.append(row["review_id"])
    if len(set(aliases))!=len(aliases):
        raise OriginalLogError("Repeated old source candidate review ID")
    inventory=inventory if inventory is not None else build_inventory(root)
    baseline=json.loads((root/"dashboard/baseline_2026.json").read_text(encoding="utf-8"))
    baseline_nights={row["night"]:row for row in baseline["nights"]}
    protected=json.loads((root/PROTECTED).read_text(encoding="utf-8"))["protected_hashes"]
    by_night=defaultdict(lambda:{"capture":[],"reaction":[],"markers":[]})
    for row in captures:by_night[row["operational_night_07_jst"]]["capture"].append(row)
    for row in reactions:by_night[row["operational_night_07_jst"]]["reaction"].append(row)
    for row in markers:by_night[row["operational_night_07_jst"]]["markers"].append(row)
    diagnostic=[]
    for track in inventory["raw_gpx"]:
        path=track["source_path"]
        night=Path(path).name.split("__legacy.gpx")[0]
        expected=protected.get(path)
        if expected is None or track.get("sha256")!=expected:
            raise OriginalLogError("Source GPX has no independent verified checksum")
        group=by_night[night]
        matchable_cap=[x for x in group["capture"] if x["source_coordinates_present"]]
        matchable_react=[x for x in group["reaction"] if x["source_coordinates_present"]]
        # Use real GPX, not the older derivative trajectory/10m label table.
        matched=_gpx_match(root/path,expected,matchable_cap,matchable_react)
        item_lookup=matched["matches"]
        normalized_capture=[{
            "source_id":x["review_id"],
            "source_line":x["source_original_line"],
            "native_timestamp":x["native_timestamp"],
            "quantity_exact_when_explicit":x["exact_individual_count"],
            "quantity_lower_bound":x["minimum_possible_individuals"],
            "owner_identity_confirmed":False,
            "training_positive_eligible":False,
            **(item_lookup[x["review_id"]] if x["source_coordinates_present"]
               else {"match_status":"MISSING_SOURCE_EVENT_COORDINATE"})
        } for x in group["capture"]]
        normalized_reactions=[{
            "source_id":x["review_id"],"category":x["category"],
            "source_line":x["source_original_line"],
            "training_positive_eligible":False,
            **(item_lookup[x["review_id"]] if x["source_coordinates_present"]
               else {"match_status":"MISSING_SOURCE_EVENT_COORDINATE"})
        } for x in group["reaction"]]
        claims=baseline_nights.get(night,{}).get("count")
        diagnostic.append({
            "night":night, "gpx_path":path, "gpx_sha256":matched["source_sha256"],
            "gpx_points":matched["point_count"],
            "source_present_for_night":timed_nights.get(night,0)>0,
            "source_timestamped_blocks_on_night":timed_nights.get(night,0),
            "full_night_outcome_ledger_verified":False,
            "search_effort_complete_and_detection_verified":False,
            "candidate_capture_events":len(normalized_capture),
            "candidate_capture_events_spatially_corrob":sum(
                r["match_status"]=="GPX_SPACETIME_CORROBORATION_ONLY"
                for r in normalized_capture),
            "minimum_capture_individual_mentions":sum(
                r["quantity_lower_bound"] for r in normalized_capture),
            "explicit_quantity_capture_events":sum(
                r["quantity_exact_when_explicit"] is not None for r in normalized_capture),
            "reactions":normalized_reactions,
            "capture_candidates":normalized_capture,
            "search_marker_count":len(group["markers"]),
            "dashboard_daily_count_claim_unverified_as_individual_ledger":claims,
            "dashboard_claim_used_as_ground_truth":False,
            "eligible_positive_individuals":0,
            "eligible_negative_roadtime_units":0,
            "unknown_without_complete_search_reporting":True
        })
    diagnostic.sort(key=lambda x:x["night"])
    return {
        "schema_version":"habu-native-august-source-gpx-join-v1",
        "status":"NATIVE_SOURCE_EVENT_LINKS_REVIEW_REQUIRED",
        "original_source_path":RAW,
        "original_bytes":meta["source_bytes"],
        "original_sha256":meta["sha256"],
        "original_source_event_block_count":len(captures),
        "original_source_habu_roadkill_or_sighting_blocks":len(reactions),
        "legacy_extracted_capture_aliases_found":len(aliases),
        "legacy_aliases_not_double_counted":True,
        "gpx_files":len(diagnostic),
        "august_gpx_files":sum(x["night"].startswith("2026-08") for x in diagnostic),
        "september_gpx_files":sum(x["night"].startswith("2026-09") for x in diagnostic),
        "gpx_nights":diagnostic,
        "formal_training_positive_individuals":0,
        "formal_training_negative_units":0,
        "scientific_unknown_label_remains":True,
        "canonical_capture_db_changed":False,
        "model_learning_generated":False,
        "official_walkforward_run":False,
        "official_p0_issued":False,
        "blockers":[
            "CAPTURE_OWNER_QUALITY_UNRESOLVED",
            "NONEXPLICIT_INDIVIDUAL_QUANTITIES_MUST_NOT_BE_DEFAULTED",
            "SEARCH_EFFORT_AND_FULL_OUTCOMES_UNVERIFIED",
            "UNKNOWN_GPX_PASSAGES_NOT_VERIFIED_NEGATIVES",
            "EX_ANTE_HISTORICAL_FORECAST_AVAILABILITY_NOT_VERIFIED",
            "FORECAST_UNIVERSE_NOT_FROZEN_HISTORICALLY"
        ]
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=make_actual_join(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":result["status"],"raw_source_sha256":result["original_sha256"],
        "gpX_nights":result["gpx_files"],
        "capture_event_blocks_in_source":result["original_source_event_block_count"],
        "matched_candidate_capture_events":sum(x["candidate_capture_events_spatially_corrob"] for x in result["gpx_nights"]),
        "roadkill_or_sighting_blocks_in_source":result["original_source_habu_roadkill_or_sighting_blocks"],
        "old_extracted_candidates_deduplicated":result["legacy_extracted_capture_aliases_found"],
        "training_positives":0,"training_negatives":0
    },ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
