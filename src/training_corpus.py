"""Audited TRAIN_ONLY selection for future model fits, not retrospective P0s.

Consumes an explicit bounded, source-hash-checked corpus. GPX absence never
creates a Negative, and research-exposed nights never become untouched confirmation.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from master_contracts import canonical_bytes, digest, file_hash, safe_path, validate_night

JST = ZoneInfo("Asia/Tokyo")
HEX = re.compile(r"[0-9a-f]{64}\Z")
MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 20000
MAX_FEATURES = 32
LABELS = {"capture_observed": 1, "observed_negative": 0}
QUALITIES = {"AUDITED_OBSERVED", "GOLD", "COMPLETE_REAL_GPX"}
SOURCE_ROLES = {"label", "feature", "search_evidence", "active_search", "complete_outcome"}
TARGET_FEATURES = {
    "label", "observed", "label_available_at", "outcome", "actual_capture",
    "capture_event_ids", "capture_count", "owner_capture_count", "gpx_trace",
    "negative_observed", "outcome_available_at", "audit_available_at",
    "all_captures_recorded", "gpx_segment_eligible", "search_role",
}
MAX_SCOPE_BYTES = 64 * 1024


def aware(value):
    if not isinstance(value, str):
        raise ValueError("Timezone-aware timestamp required")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.utcoffset() is None:
        raise ValueError("Naive timestamp forbidden")
    return dt


def _source_path(root, relative):
    """Reject static path indirection before each source read or rescan."""
    root = Path(root)
    path = safe_path(root, relative)
    absolute = path.absolute()
    for current in reversed((absolute, *absolute.parents)):
        try:
            attributes = getattr(current.lstat(), "st_file_attributes", 0)
        except FileNotFoundError:
            continue
        if (current.is_symlink() or getattr(current, "is_junction", lambda: False)() or
                attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
            raise ValueError("Training source reparse path is forbidden")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Training source resolves outside root")
    return path


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key in training input")
        result[key] = value
    return result


def _read(root, relative, sha256):
    if not isinstance(relative, str) or Path(relative).parts[:2] != ("data", "processed"):
        raise ValueError("Only data/processed training corpus is permitted")
    if not isinstance(sha256, str) or not HEX.fullmatch(sha256):
        raise ValueError("Corpus content SHA-256 required")
    path = _source_path(root, relative)
    if not path.is_file():
        raise ValueError("Missing source corpus")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError("Missing, overlarge or changed source corpus")
    value = json.loads(raw, object_pairs_hook=_unique_json_object)
    canonical_bytes(value)
    return value


def source_manifest(root, corpus):
    """Bind declared source roles to bytes, without certifying their authenticity."""
    manifest = corpus.get("source_manifest")
    if not isinstance(manifest, list) or not manifest:
        raise ValueError("Source manifest required")
    sources = {}
    for source in manifest:
        if not isinstance(source, dict) or set(source) != {"path", "sha256", "received_at", "role"}:
            raise ValueError("Source receipt requires an explicit role")
        path, sha = source["path"], source["sha256"]
        if (not isinstance(path, str) or not Path(path).parts or
                Path(path).parts[0] not in ("data", "evidence", "features") or
                not isinstance(sha, str) or not HEX.fullmatch(sha) or path in sources or
                source["role"] not in SOURCE_ROLES):
            raise ValueError("Duplicate or invalid source identity/role")
        if file_hash(_source_path(root, path)) != sha:
            raise ValueError("Training source SHA-256 mismatch")
        sources[path] = dict(source, received_at=aware(source["received_at"]))
    return sources


def feature_eligibility_reasons(row, names, sources, boundary):
    """Use the same predictor role/readiness gate for training and diagnostics."""
    if any(name.casefold() in TARGET_FEATURES for name in names):
        raise ValueError("Target/outcome fields cannot be training predictors")
    features, times = row.get("features"), row.get("feature_available_at")
    if (not isinstance(features, dict) or not isinstance(times, dict) or
            set(features) != set(names) or set(times) != set(names)):
        return ["FEATURE_COVERAGE_MISSING"]
    bindings = row.get("feature_source_refs")
    if not isinstance(bindings, dict) or set(bindings) != set(names):
        return ["FEATURE_SOURCE_BINDING_MISSING"]
    reasons = []
    for name in names:
        if type(features[name]) not in (float, int) or not math.isfinite(features[name]):
            raise ValueError("Nonfinite historic feature")
        refs = bindings[name]
        if (not isinstance(refs, list) or not refs or
                any(not isinstance(ref, str) for ref in refs) or len(set(refs)) != len(refs) or
                any(ref not in row.get("source_refs", ()) or ref not in sources or
                    sources[ref]["role"] != "feature" for ref in refs)):
            raise ValueError("Feature binding requires declared feature-role sources")
        ready = aware(times[name])
        if any(sources[ref]["received_at"] > ready for ref in refs):
            raise ValueError("Feature availability precedes its source receipt")
        if ready >= boundary:
            reasons.append("FEATURE_NOT_READY_FOR_FIT")
    if row.get("feature_valid_for_night") is not True:
        reasons.append("FEATURE_HISTORICAL_VALIDITY_UNPROVEN")
    return reasons


def negative_eligibility_reasons(root, row, sources, boundary):
    """Require independent scoped search and complete-outcome receipts.

    Receipts are bounded JSON sources with schema_version, kind, qualified_at,
    scope (night/cell/start/end), and hash-bound basis_source_refs. Search proof
    must cite search_evidence, separate from the label sources; completeness
    must cite the row's label source. These are structural gates, not external
    authentication of a receipt or permission to promote historical evidence.
    """
    if row.get("observation") != "observed_negative":
        return []
    if (row.get("search_role") != "SEARCH" or
            row.get("all_captures_recorded") is not True or
            row.get("gpx_segment_eligible") is not True):
        return ["UNVERIFIED_NEGATIVE_EXPOSURE"]
    refs = [row.get("active_search_ref"), row.get("complete_outcome_ref")]
    if any(not isinstance(ref, dict) or set(ref) != {"path", "sha256"} for ref in refs):
        return ["NEGATIVE_SCOPE_PROOF_MISSING"]
    if refs[0]["path"] == refs[1]["path"]:
        return ["NEGATIVE_SCOPE_NOT_INDEPENDENT"]
    window = aware(row["window_start_jst"]).astimezone(JST)
    reasons = []
    search_basis, outcome_basis = set(), set()
    for ref, role, kind in zip(refs, ("active_search", "complete_outcome"),
                              ("active_habu_search_scope", "complete_owner_capture_outcome_scope")):
        path = ref["path"]
        if (not isinstance(path, str) or path not in row.get("source_refs", ()) or path not in sources or
                sources[path]["role"] != role or ref["sha256"] != sources[path]["sha256"]):
            raise ValueError("Negative scope reference has invalid hash or source role")
        with _source_path(root, path).open("rb") as stream:
            raw = stream.read(MAX_SCOPE_BYTES + 1)
        if len(raw) > MAX_SCOPE_BYTES or hashlib.sha256(raw).hexdigest() != ref["sha256"]:
            raise ValueError("Negative scope receipt oversized or SHA-256 mismatch")
        receipt = json.loads(raw, object_pairs_hook=_unique_json_object)
        if (not isinstance(receipt, dict) or receipt.get("schema_version") != "1.0" or
                receipt.get("kind") != kind):
            raise ValueError("Unrecognized negative scope receipt")
        scope = receipt.get("scope")
        if not isinstance(scope, dict) or set(scope) != {"night", "cell_x", "cell_y", "start", "end"}:
            raise ValueError("Explicit negative night/cell/time scope required")
        start, end = aware(scope["start"]), aware(scope["end"])
        if (scope["night"] != row["night"] or type(scope["cell_x"]) is not int or
                type(scope["cell_y"]) is not int or scope["cell_x"] != row["cell_x"] or
                scope["cell_y"] != row["cell_y"] or start > window or
                end < window + timedelta(minutes=10) or
                (start.astimezone(JST) - timedelta(hours=7)).date().isoformat() != row["night"] or
                ((end - timedelta(microseconds=1)).astimezone(JST) - timedelta(hours=7)).date().isoformat() != row["night"]):
            reasons.append("NEGATIVE_SCOPE_MISMATCH")
        qualified = aware(receipt["qualified_at"])
        if qualified < end or sources[path]["received_at"] > qualified:
            raise ValueError("Negative scope qualification precedes evidence readiness")
        if qualified >= boundary:
            reasons.append("NEGATIVE_SCOPE_NOT_READY")
        basis = receipt.get("basis_source_refs")
        if not isinstance(basis, list) or not basis:
            raise ValueError("Negative scope requires bound independent basis sources")
        seen = set()
        for source_ref in basis:
            if not isinstance(source_ref, dict) or set(source_ref) != {"path", "sha256"}:
                raise ValueError("Invalid negative scope basis reference")
            relative = source_ref["path"]
            expected_role = "search_evidence" if role == "active_search" else "label"
            if (not isinstance(relative, str) or relative in seen or relative not in sources or
                    relative not in row.get("source_refs", ()) or relative == path or
                    sources[relative]["role"] != expected_role or
                    source_ref["sha256"] != sources[relative]["sha256"] or
                    not end <= sources[relative]["received_at"] <= qualified):
                raise ValueError("Negative scope basis hash/role/readiness mismatch")
            seen.add(relative)
            (search_basis if role == "active_search" else outcome_basis).add(source_ref["sha256"])
        if role == "active_search":
            if (receipt.get("search_role") != "SEARCH" or
                    receipt.get("evidence_type") != "INDEPENDENT_ACTIVE_HABU_SEARCH"):
                reasons.append("UNVERIFIED_NEGATIVE_EXPOSURE")
        elif (receipt.get("recording_rule") != "ALL_OWNER_HABU_CAPTURES_RECORDED" or
                row.get("outcome_source_ref") not in seen):
            reasons.append("INCOMPLETE_NEGATIVE_OUTCOMES")
    if search_basis & outcome_basis:
        reasons.append("NEGATIVE_SCOPE_NOT_INDEPENDENT")
    return sorted(set(reasons))


def select_training_rows(
    root: Path, corpus_path: str, corpus_sha256: str,
    heldout_night: str, fit_cutoff: str,
    *, require_features: tuple[str, ...], exposed_nights: tuple[str, ...] = (),
):
    """Select only rows already independently qualified by an evidence auditor.

    Source hashes are byte-consistency checks, not independent authenticity proof.
    This selector does not grant scientific confirmation or a Champion promotion.
    """
    validate_night(heldout_night)
    if not isinstance(require_features, tuple) or not 1 <= len(require_features) <= MAX_FEATURES:
        raise ValueError("Bounded nonempty declared feature list required")
    if any(not isinstance(x, str) or not re.fullmatch("[A-Za-z][A-Za-z0-9_]{0,63}", x)
           for x in require_features) or len(set(require_features)) != len(require_features):
        raise ValueError("Invalid or repeated feature names")
    if any(name.casefold() in TARGET_FEATURES for name in require_features):
        raise ValueError("Target/outcome fields cannot be training predictors")
    for night in exposed_nights:
        validate_night(night)
    boundary = datetime.fromisoformat(heldout_night + "T07:00:00+09:00")
    requested = aware(fit_cutoff)
    if requested >= boundary:
        raise ValueError("Fit cutoff must precede held-out night start strictly")
    effective = requested
    corpus = _read(Path(root), corpus_path, corpus_sha256)
    if not isinstance(corpus, dict) or corpus.get("schema_version") != "1.0" or \
       corpus.get("qualification") != "AUDITED_TRAIN_ONLY":
        raise ValueError("Unaudited training corpus forbidden")
    rows = corpus.get("rows")
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("Bounded rows array required")
    sources = source_manifest(root, corpus)
    source_hashes = {path: (source["sha256"], source["received_at"]) for path, source in sources.items()}
    accepted, rejected, seen, events, units = [], [], set(), set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid training row")
        row_id = row.get("row_id")
        night = row.get("night")
        if not isinstance(row_id, str) or not row_id or row_id in seen:
            raise ValueError("Duplicated training row identity")
        seen.add(row_id)
        validate_night(night)
        # Every capture/event identity is globally unique, even among rejected
        # rows. Merely partitioning duplicates may otherwise count them twice.
        ids = row.get("capture_event_ids")
        if not isinstance(ids, list) or any(not isinstance(i, str) or not i for i in ids):
            raise ValueError("Capture event identities are required")
        if len(ids) != len(set(ids)) or events.intersection(ids):
            raise ValueError("Cross-row capture event duplicate")
        events.update(ids)
        win = aware(row["window_start_jst"]).astimezone(JST)
        if (win - timedelta(hours=7)).date().isoformat() != night:
            raise ValueError("Incorrect 07:00 operational night")
        if win.minute % 10 or win.second or win.microsecond:
            raise ValueError("Unaligned observation window")
        # Row IDs are transport identifiers, not scientific observation identities.
        # A second ID for one 100m x 10min unit must not double-weight a
        # capture or observed passage in training/validation.
        cx, cy = row.get("cell_x"), row.get("cell_y")
        if (type(cx) is not int or type(cy) is not int or
                not 0 <= cx <= 100000 or not 0 <= cy <= 100000):
            raise ValueError("Audited integer 100m observation cell required")
        unit = (cx, cy, win.astimezone(timezone.utc))
        if unit in units:
            raise ValueError("Duplicate or conflicting 100m x 10min observation unit")
        units.add(unit)
        reasons = []
        if night >= heldout_night or night in exposed_nights:
            reasons.append("NOT_PRIOR_TRAINING_NIGHT")
        if win >= effective:
            reasons.append("WINDOW_NOT_PRIOR_TO_FIT")
        observation = row.get("observation")
        label = row.get("label")
        if observation == "UNKNOWN" and label is None:
            reasons.append("UNKNOWN_NOT_NEGATIVE")
        elif observation not in LABELS or type(label) is not int or label != LABELS[observation]:
            raise ValueError("Invalid observed outcome class")
        if observation in LABELS and row.get("quality") not in QUALITIES:
            reasons.append("OBSERVATION_NOT_QUALIFIED")
        if observation == "capture_observed" and not ids:
            raise ValueError("Positive capture requires unique event IDs")
        if observation == "observed_negative" and ids:
            raise ValueError("Negative cannot contain capture events")
        refs = row.get("source_refs")
        if not isinstance(refs, list) or not refs or len(set(refs)) != len(refs) or \
           any(path not in source_hashes for path in refs):
            raise ValueError("Unbound observation source reference")
        if observation in LABELS:
            outcome_ref = row.get("outcome_source_ref")
            if (not isinstance(outcome_ref, str) or outcome_ref not in refs or
                    sources[outcome_ref]["role"] != "label"):
                raise ValueError("Observed label requires an explicit bound outcome source")
            outcome_received = source_hashes[outcome_ref][1]
            label_ready = aware(row["label_available_at"]) if row.get("label_available_at") else None
            audit_ready = aware(row["audit_available_at"]) if row.get("audit_available_at") else None
            if (outcome_received < win or
                (label_ready is not None and outcome_received > label_ready) or
                (audit_ready is not None and label_ready is not None and audit_ready < label_ready)):
                raise ValueError("Outcome source timing contradicts observed event or label readiness")
        features = row.get("features")
        reasons.extend(feature_eligibility_reasons(row, require_features, sources, effective))
        reasons.extend(negative_eligibility_reasons(root, row, sources, effective))
        for key in ("label_available_at", "audit_available_at"):
            if observation in LABELS:
                if row.get(key) is None:
                    reasons.append("MISSING_" + key.upper())
                elif aware(row[key]) >= effective:
                    reasons.append(key.upper() + "_NOT_READY_FOR_FIT")
        for ref in refs:
            if source_hashes[ref][1] >= effective:
                reasons.append("SOURCE_RECEIVED_AFTER_FIT")
        if reasons:
            rejected.append({"row_id": row_id, "night": night,
                             "reasons": sorted(set(reasons))})
        else:
            accepted.append({
                "row_id": row_id, "night": night, "label": label,
                "cell_x": cx, "cell_y": cy,
                "features": {x: float(features[x]) for x in require_features},
                "window_start_jst": win.isoformat(), "capture_event_ids": list(ids),
            })
    # Recheck every source after selection. This is not an atomic snapshot.
    for path, (sha, _) in source_hashes.items():
        if file_hash(_source_path(root, path)) != sha:
            raise ValueError("Training source changed during selection")
    if file_hash(_source_path(root, corpus_path)) != corpus_sha256:
        raise ValueError("Training corpus changed during selection")
    accepted.sort(key=lambda r: (r["night"], r["window_start_jst"], r["row_id"]))
    rejected.sort(key=lambda r: r["row_id"])
    nights = sorted({r["night"] for r in accepted})
    positives = sum(r["label"] == 1 for r in accepted)
    negatives = len(accepted) - positives
    # A positive-only corpus must not be converted into calibrated binary risk.
    ready = len(nights) >= 3 and positives >= 2 and negatives >= 2
    selection_identity = {
        "accepted": accepted,
        "corpus_sha256": corpus_sha256,
        "source_sha256": {path: source_hashes[path][0] for path in sorted(source_hashes)},
        "source_received_at": {
            path: source_hashes[path][1].isoformat() for path in sorted(source_hashes)
        },
        "heldout_night": heldout_night,
        "fit_cutoff": effective.isoformat(),
        "feature_names": sorted(require_features),
        "exposed_nights": sorted(set(exposed_nights)),
    }
    return {
        "status": "DEVELOPMENT_TRAINING_ELIGIBLE" if ready else "NEED_MORE_DATA",
        "qualification": "RETROSPECTIVE_TRAIN_ONLY_NOT_CONFIRMATION",
        "official_issuance_authorized": False,
        "heldout_night": heldout_night, "fit_cutoff": effective.isoformat(),
        "feature_names": sorted(require_features), "corpus_sha256": corpus_sha256,
        "accepted": accepted, "rejected": rejected,
        "counts": {"accepted_rows": len(accepted), "rejected_rows": len(rejected),
                   "nights": len(nights), "positives": positives, "negatives": negatives},
        "source_sha256": selection_identity["source_sha256"],
        "source_received_at": selection_identity["source_received_at"],
        "exposed_nights": selection_identity["exposed_nights"],
        "selection_sha256": digest(selection_identity),
        "blockers": [] if ready else [
            "Need >=3 eligible prior nights and >=2 independently qualified"
            " positives and >=2 confirmed no-capture observation units"
        ],
    }
