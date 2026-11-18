"""Private owner-source -> immediately usable descriptive research receipt.

Reuses the established byte-preserving intake. No canonical P0, Negative label,
model fit or production authority is conferred by this adapter.
Private event timestamps never enter stdout or the public GitHub checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from private_pdca_intake import (
    IntakeError, STAMP, MAX_LOG_BYTES, MAX_RAW_BYTES, MAX_RECEIPT_BYTES,
    _ReadBudget, _digest, _read_bytes, _temp_owner, cleanup_owned_temp,
    guard_private_path, intake, operational_night, source_receipt_id, summarize_log,
)

HEX = re.compile(r"[0-9a-f]{64}\Z")
VERSION = "habu-owner-private-research-receipt-v1"
MAX_RESEARCH_BYTES = 8 * 1024 * 1024


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise IntakeError("Duplicate receipt JSON key")
        result[key] = value
    return result


def _private_roots(repo_root: Path, private_root: Path):
    repo = Path(repo_root).resolve(strict=True)
    private = Path(private_root).resolve(strict=True)
    if (private == repo or private in repo.parents or repo in private.parents or
            (os.name == "posix" and private.stat().st_mode & 0o077)):
        raise IntakeError("Private source store is not isolated/owner-only")
    guard_private_path(private, private)
    return private


def _events(text: str, source_hash: str):
    """Literal log events only. Never infer number of animals from one event."""
    starts = list(STAMP.finditer(text))
    result = []
    for index, match in enumerate(starts):
        stamp = datetime(*map(int, match.groups()))
        block = text[match.end():starts[index + 1].start() if index + 1 < len(starts) else len(text)]
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or lines[0] not in ("捕獲", "目撃", "轢死"):
            continue
        kind = lines[0]
        species = [line for line in lines[1:] if line == "ハブ" or line.startswith("ハブ捕獲")]
        if not species or any("ヒメハブ" in line for line in lines[1:]):
            continue
        record = {
            "event_key": hashlib.sha256((source_hash + ":" + str(index)).encode("ascii")).hexdigest(),
            "event_type": {"捕獲": "owner_habu_capture", "目撃": "habu_sighting",
                           "轢死": "habu_roadkill"}[kind],
            "operational_night": operational_night(stamp),
            "event_time_jst": stamp.replace(tzinfo=timezone(timedelta(hours=9))).isoformat(),
            "individual_count": None,
            "count_status": "UNRESOLVED_EVENT_NOT_INDIVIDUAL",
        }
        result.append(record)
    return result


def _read_receipt(private: Path, receipt_id: str, budget: _ReadBudget):
    if type(receipt_id) is not str or not HEX.fullmatch(receipt_id):
        raise IntakeError("Invalid receipt ID")
    receipt_path = private / "receipts" / (receipt_id + ".json")
    guard_private_path(private, receipt_path)
    try:
        raw = _read_bytes(receipt_path, MAX_RECEIPT_BYTES, budget)
        receipt = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise IntakeError("Invalid receipt JSON") from exc
    if (type(receipt) is not dict or receipt.get("schema") != "habu-private-intake-v1" or
            receipt.get("receipt_id") != receipt_id):
        raise IntakeError("Wrong private intake receipt")
    rows = receipt.get("sources")
    if type(rows) is not list or not 1 <= len(rows) <= 2:
        raise IntakeError("Invalid source rows")
    if source_receipt_id(rows) != receipt_id:
        raise IntakeError("Receipt ID and source records conflict")
    verified = {}
    for row in rows:
        if type(row) is not dict or set(row) != {"type", "sha256", "size_bytes", "private_archive"}:
            raise IntakeError("Invalid bound source record")
        kind, sha, size = row["type"], row["sha256"], row["size_bytes"]
        if (kind not in ("log", "gpx") or kind in verified or
                type(sha) is not str or not HEX.fullmatch(sha) or
                type(size) is not int or not 0 < size <= (MAX_LOG_BYTES if kind == "log" else MAX_RAW_BYTES)):
            raise IntakeError("Unsupported source type/hash/size")
        archive = private / "raw" / kind / (sha + (".txt" if kind == "log" else ".gpx"))
        guard_private_path(private, archive)
        if row["private_archive"] != str(archive):
            raise IntakeError("Source archive path differs from trusted intake layout")
        actual, read_size = _digest(archive, budget, expected_size=size)
        if actual != sha or read_size != size:
            raise IntakeError("Archived source changed")
        verified[kind] = {"sha256": sha, "size_bytes": size, "path": archive}
    if "log" in verified:
        source = verified["log"]
        raw = _read_bytes(source["path"], MAX_LOG_BYTES, budget)
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise IntakeError("Archived log changed during reparse")
        try:
            text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeError as exc:
            raise IntakeError("Archived log is not UTF-8") from exc
        diagnostic = summarize_log(text, _budget=budget)
        if diagnostic != receipt.get("log_diagnostic"):
            raise IntakeError("Receipt and archived diagnostic disagree")
    else:
        text = None
        if receipt.get("log_diagnostic") != {"status": "NOT_RUN", "reason": "Log absent"}:
            raise IntakeError("GPX-only receipt has fabricated log diagnostic")
        diagnostic = None
    return verified, text, diagnostic


def _immutable_report(private: Path, receipt_id: str, report: dict, budget: _ReadBudget):
    raw = (json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False) + "\n").encode("utf-8")
    if not 0 < len(raw) <= MAX_RESEARCH_BYTES:
        raise IntakeError("Research report size limit")
    dest = private / "research" / (receipt_id + ".json")
    guard_private_path(private, dest)
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    guard_private_path(private, dest)
    if dest.exists():
        if _read_bytes(dest, MAX_RESEARCH_BYTES, budget) != raw:
            raise IntakeError("Existing research report differs; no silent overwrite")
        return dest
    temp = token = None
    try:
        with NamedTemporaryFile(dir=dest.parent, prefix=".pending-", delete=False) as out:
            temp = Path(out.name)
            token = _temp_owner(out)
            guard_private_path(private, temp)
            os.chmod(temp, 0o600)
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        budget.check()
        guard_private_path(private, dest)
        try:
            os.link(temp, dest)
        except FileExistsError:
            if _read_bytes(dest, MAX_RESEARCH_BYTES, budget) != raw:
                raise IntakeError("Concurrent immutable report conflict")
    finally:
        cleanup_owned_temp(private, temp, token, sys.exception())
    if _read_bytes(dest, MAX_RESEARCH_BYTES, budget) != raw:
        raise IntakeError("Research report readback mismatch")
    return dest


def research_receipt(repo_root: Path, private_root: Path, receipt_id: str) -> dict:
    """Index owner evidence in an isolated, immutable, *private* research report."""
    private = _private_roots(repo_root, private_root)
    budget = _ReadBudget(300)
    verified, text, diagnostic = _read_receipt(private, receipt_id, budget)
    events = _events(text, verified["log"]["sha256"]) if text is not None else []
    nights = []
    if diagnostic is not None:
        keys = {"owner_habu_capture": "owner_habu_capture_events",
                "habu_sighting": "habu_sighting_events",
                "habu_roadkill": "habu_roadkill_events"}
        for night, stats in sorted(diagnostic["nights"].items()):
            night_events = [e for e in events if e["operational_night"] == night]
            for kind, field in keys.items():
                if sum(e["event_type"] == kind for e in night_events) != stats[field]:
                    raise IntakeError("Derived event count differs from archived diagnostic")
            hours = {}
            for event in night_events:
                if event["event_type"] == "owner_habu_capture":
                    hour = event["event_time_jst"][11:13]
                    hours[hour] = hours.get(hour, 0) + 1
            nights.append({
                "operational_night": night, **stats,
                "capture_event_hours_jst": dict(sorted(hours.items())),
                "verified_individual_count": None,
                "complete_search_outcomes": "NOT_CERTIFIED",
                "search_role": "UNKNOWN",
                "negative_labels": 0,
            })
    report = {
        "schema_version": VERSION, "receipt_id": receipt_id,
        "status": "OWNER_SOURCE_DIAGNOSTIC_READY" if diagnostic is not None else "GPX_ONLY_NO_OUTCOME_LABELS",
        "source_hashes": {kind: value["sha256"] for kind, value in verified.items()},
        "research_nights": nights, "private_event_records": events,
        "count_interpretation": "CAPTURE_EVENTS_NOT_VERIFIED_INDIVIDUAL_COUNTS",
        "gpx_source_attached": "gpx" in verified,
        "event_spatial_match": "NOT_PERFORMED",
        "P0_score": "NOT_EVALUATED",
        "research_candidate_fit": "NOT_RUN",
        "model_comparison": "NOT_EVALUATED",
        "formal_negative_labels_created": 0,
        "production_champion_activated": False,
        "scope": "PRIVATE_RESEARCH_ONLY",
    }
    report["content_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()
    _immutable_report(private, receipt_id, report, budget)
    return {
        "receipt_id": receipt_id, "research_status": report["status"],
        "research_content_sha256": report["content_sha256"],
        "research_nights_indexed": len(nights),
        "capture_events_indexed": sum(row["owner_habu_capture_events"] for row in nights),
        "formal_negative_labels_created": 0,
        "official_model_activated": False,
        "research_candidate_fit": "NOT_RUN",
    }


def intake_and_research(repo_root: Path, private_root: Path, *, log_file=None,
                        gpx_file=None, receipt_id=None) -> dict:
    if receipt_id is not None:
        if log_file is not None or gpx_file is not None:
            raise IntakeError("Use saved receipt OR new intake, not both")
        return research_receipt(repo_root, private_root, receipt_id)
    result = intake(repo_root, private_root, log_file=log_file, gpx_file=gpx_file)
    return research_receipt(repo_root, private_root, result["receipt_id"])


def main():
    parser = argparse.ArgumentParser(description="Private owner-source research intake")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--gpx", type=Path)
    parser.add_argument("--receipt-id")
    args = parser.parse_args()
    result = intake_and_research(args.repo_root, args.private_root,
                                 log_file=args.log, gpx_file=args.gpx,
                                 receipt_id=args.receipt_id)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
