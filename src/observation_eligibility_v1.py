"""Read-only review of existing fauna motion packets; this API cannot grant labels.

Consumes the existing audit_august_75_fauna_motion_review dictionaries, not a new
observation-row schema. Whole-file SHA binding and packet membership are checked
here. The upstream original-source parser still owns source-block interpretation.
Independent scoped search/outcome certification is deliberately not implemented
by accepting packet booleans. A later reviewed certifier must supply that proof.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence

from master_contracts import digest

VERSION = "observation-eligibility-motion-review-v1"
TARGET = "SOURCE_QUALIFIED_OWNER_CAPTURE_BINARY"
FIELD_LOG = "evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt"
UNRESOLVED_MOTION = "DIRECT_FAUNA_POINT_OBSERVATION_MOTION_UNRESOLVED"
MISSING_PROOF = (
    "INDEPENDENT_SCOPED_ACTIVE_HABU_SEARCH_PROOF_MISSING",
    "SCOPED_COMPLETE_OWNER_CAPTURE_OUTCOME_PROOF_MISSING",
    "SOURCE_QUALIFIED_OWNER_CAPTURE_EVENT_NOT_ESTABLISHED",
    "CANONICAL_INDIVIDUAL_IDENTITY_NOT_ESTABLISHED",
)


def review_motion_packets(
    packets: Sequence[dict], anchors: Sequence[dict], source_blobs: Mapping[str, bytes]
) -> dict:
    """Return deterministic audit diagnostics, always UNKNOWN/null, never fit rows.

    source_blobs contains byte-exact existing log/GPX inputs by repository path.
    Hashes verify referenced file bytes, not witness authenticity, search intent,
    completeness, source selectors, organism ownership or individual identity.
    No input is modified and no filesystem, model, or forecast is read or written.
    """
    source_manifest = []
    for path, raw in sorted(source_blobs.items()):
        if not isinstance(path, str) or not isinstance(raw, bytes):
            raise TypeError("source_blobs must map repository paths to bytes")
        source_manifest.append({"path": path, "sha256": hashlib.sha256(raw).hexdigest(),
                                "size_bytes": len(raw)})
    actual = {entry["path"]: entry for entry in source_manifest}
    by_group = defaultdict(list)
    for anchor in anchors:
        by_group[anchor.get("review_group_id")].append(anchor)
    ids = [packet.get("review_group_id") for packet in packets]
    global_errors = []
    if len(set(ids)) != len(ids):
        global_errors.append("DUPLICATE_REVIEW_GROUP")
    blocks = [anchor.get("source_block_sha256") for anchor in anchors]
    if len(set(blocks)) != len(blocks):
        global_errors.append("DUPLICATE_SOURCE_ANCHOR")
    if set(by_group) - set(ids):
        global_errors.append("ORPHAN_SOURCE_ANCHOR")
    reviews = []
    ordered = sorted(packets, key=lambda p: (
        p.get("review_motion_priority") != UNRESOLVED_MOTION,
        str(p.get("night", "")), str(p.get("review_group_id", ""))))
    for packet in ordered:
        group_id = packet.get("review_group_id")
        linked = by_group.get(group_id, [])
        errors = []
        if not isinstance(group_id, str) or not group_id:
            errors.append("REVIEW_GROUP_ID_MISSING")
        if (not linked or type(packet.get("independent_original_fauna_note_count")) is not int
                or packet["independent_original_fauna_note_count"] != len(linked)
                or sorted(packet.get("source_event_block_sha256s", [])) != sorted(
                    anchor.get("source_block_sha256", "") for anchor in linked)
                or sorted(packet.get("matched_candidate_ids", [])) != sorted({
                    anchor.get("candidate_id", "") for anchor in linked})):
            errors.append("PACKET_ANCHOR_MEMBERSHIP_MISMATCH")
        if any(anchor.get("night") != packet.get("night") for anchor in linked):
            errors.append("PACKET_ANCHOR_NIGHT_MISMATCH")
        packet_claims = ("independently_verified_habu_search_on_entire_road",
                         "capture_result_ledger_complete", "source_proves_zero_habu_captures",
                         "model_positive_rows", "model_negative_rows")
        anchor_claims = ("independently_certified_habu_targeted_search",
                         "observed_entire_road_cell_as_searched",
                         "complete_capture_outcomes_for_cell", "formal_positive_eligible",
                         "formal_negative_eligible")
        if (any(packet.get(key) for key in packet_claims)
                or any(anchor.get("training_label") is not None
                       or anchor.get("training_observation") != "UNKNOWN"
                       or any(anchor.get(key) for key in anchor_claims) for anchor in linked)):
            errors.append("UNSUPPORTED_LABEL_OR_PROOF_CLAIM")
        refs = {}
        for anchor in linked:
            if (not isinstance(anchor.get("source_block_sha256"), str)
                    or not re.fullmatch(r"[a-f0-9]{64}", anchor["source_block_sha256"])
                    or type(anchor.get("original_source_line")) is not int
                    or anchor["original_source_line"] < 1
                    or anchor.get("source_logged_fauna_observation_at_point") is not True):
                errors.append("SOURCE_ANCHOR_CONTRACT_MISMATCH")
            for path, expected in (
                (FIELD_LOG, anchor.get("source_field_log_sha256")),
                (f"data/raw/gpx/{anchor.get('night')}__legacy.gpx",
                 anchor.get("actual_gpx_source_sha256")),
            ):
                if path not in actual:
                    errors.append("SOURCE_BYTES_MISSING")
                elif actual[path]["sha256"] != expected:
                    errors.append("SOURCE_HASH_MISMATCH")
                else:
                    refs[path] = {"path": path, "sha256": expected}
        reviews.append({
            "review_group_id": group_id, "night": packet.get("night"),
            "packet_sha256": digest(packet),
            "source_anchor_sha256": digest(sorted(linked, key=lambda a: str(a.get("source_block_sha256")))),
            "source_refs": [refs[path] for path in sorted(refs)],
            "source_reference_integrity": "FAIL" if errors else "HASHES_VERIFIED",
            "source_selector_status": "NOT_REAUTHENTICATED_BY_THIS_GATE",
            "review_motion_priority": packet.get("review_motion_priority"),
            "source_anchor_count": len(linked),
            "training_observation": "UNKNOWN", "training_label": None,
            "formal_positive_eligible": False, "formal_negative_eligible": False,
            "reasons": list(MISSING_PROOF), "integrity_errors": sorted(set(errors)),
        })
    failed = sum(bool(review["integrity_errors"]) for review in reviews)
    result = {
        "implementation_version": VERSION, "target_semantics": TARGET,
        "status": "FAIL" if global_errors or failed else "PARTIAL" if packets else "BLOCKED",
        "scientific_status": "NOT_VALIDATED", "label_assignment_supported": False,
        "input_packets_sha256": digest(list(packets)), "input_anchors_sha256": digest(list(anchors)),
        "source_manifest": source_manifest, "integrity_errors": global_errors,
        "counts": {"packets": len(packets), "anchors": len(anchors), "eligible": 0,
                   "unknown": len(packets), "integrity_rejected_packets": failed},
        "missing_proof_counts": dict(Counter(reason for review in reviews for reason in review["reasons"])),
        "packet_reviews": reviews,
    }
    result["audit_sha256"] = digest(result)
    return result
