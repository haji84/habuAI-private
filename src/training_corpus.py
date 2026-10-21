"""Audited TRAIN_ONLY selection for future model fits, not retrospective P0s.

Consumes an explicit bounded, source-hash-checked corpus. GPX absence never
creates a Negative, and research-exposed nights never become untouched confirmation.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
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


def aware(value):
    if not isinstance(value, str):
        raise ValueError("Timezone-aware timestamp required")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.utcoffset() is None:
        raise ValueError("Naive timestamp forbidden")
    return dt


def _read(root, relative, sha256):
    if not isinstance(relative, str) or Path(relative).parts[:2] != ("data", "processed"):
        raise ValueError("Only data/processed training corpus is permitted")
    if not isinstance(sha256, str) or not HEX.fullmatch(sha256):
        raise ValueError("Corpus content SHA-256 required")
    path = safe_path(root, relative)
    if not path.is_file():
        raise ValueError("Missing source corpus")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError("Missing, overlarge or changed source corpus")
    value = json.loads(raw)
    canonical_bytes(value)
    return value


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
    source_manifest = corpus.get("source_manifest")
    if not isinstance(source_manifest, list) or not source_manifest:
        raise ValueError("Source manifest required")
    source_hashes = {}
    for source in source_manifest:
        if not isinstance(source, dict) or set(source) != {"path", "sha256", "received_at"}:
            raise ValueError("Invalid source receipt contract")
        path, sha = source["path"], source["sha256"]
        if (not isinstance(path, str) or not Path(path).parts or
                Path(path).parts[0] not in ("data", "evidence", "features") or
                not isinstance(sha, str) or not HEX.fullmatch(sha) or path in source_hashes):
            raise ValueError("Duplicate or invalid source identity")
        if file_hash(safe_path(Path(root), path)) != sha:
            raise ValueError("Training source SHA-256 mismatch")
        source_hashes[path] = (sha, aware(source["received_at"]))
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
        if observation == "observed_negative" and (
            row.get("search_role") not in ("SEARCH", "PASSAGE") or
            row.get("all_captures_recorded") is not True or
            row.get("gpx_segment_eligible") is not True
        ):
            reasons.append("UNVERIFIED_NEGATIVE_EXPOSURE")
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
            if not isinstance(outcome_ref, str) or outcome_ref not in refs:
                raise ValueError("Observed label requires an explicit bound outcome source")
            outcome_received = source_hashes[outcome_ref][1]
            label_ready = aware(row["label_available_at"]) if row.get("label_available_at") else None
            audit_ready = aware(row["audit_available_at"]) if row.get("audit_available_at") else None
            if (outcome_received < win or
                (label_ready is not None and outcome_received > label_ready) or
                (audit_ready is not None and label_ready is not None and audit_ready < label_ready)):
                raise ValueError("Outcome source timing contradicts observed event or label readiness")
        features = row.get("features")
        feature_times = row.get("feature_available_at")
        if not isinstance(features, dict) or not isinstance(feature_times, dict) or \
           set(features) != set(require_features) or set(feature_times) != set(require_features):
            reasons.append("FEATURE_COVERAGE_MISSING")
        else:
            for name in require_features:
                value = features[name]
                if type(value) not in (float, int) or not math.isfinite(value):
                    raise ValueError("Nonfinite historic feature")
                if row.get("feature_valid_for_night") is not True:
                    reasons.append("FEATURE_HISTORICAL_VALIDITY_UNPROVEN")
                if aware(feature_times[name]) >= effective:
                    reasons.append("FEATURE_NOT_READY_FOR_FIT")
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
        if file_hash(safe_path(Path(root), path)) != sha:
            raise ValueError("Training source changed during selection")
    if file_hash(safe_path(Path(root), corpus_path)) != corpus_sha256:
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
