"""Time-blocked retrospective DEVELOPMENT diagnostics, never confirmation.

This reuses the canonical TRAIN_ONLY selector and fitted diagnostic adapter.
Held-out rows are scored only AFTER fitting each prior-night-only model, but
historic/research-visible labels are not untouched confirmation labels.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from train_spacetime_candidate import fit_candidate
from training_corpus import LABELS, QUALITIES, _read, aware, select_training_rows
from master_contracts import validate_night

JST = ZoneInfo("Asia/Tokyo")
MAX_FOLDS = 12


def _predict(model, row):
    """Fixed numeric transform also used by the candidate inference design."""
    names = sorted(model["coefficients"])
    values = row["features"]
    if not isinstance(values, dict) or set(values) != set(names):
        raise ValueError("Held-out feature schema mismatch")
    t = aware(row["window_start_jst"]).astimezone(JST)
    phase = (t.hour * 3600 + t.minute * 60 + t.second) * 2 * math.pi / 86400
    if any(type(values[name]) not in (int, float) or
           not math.isfinite(values[name]) for name in names):
        raise ValueError("Invalid numeric heldout feature")
    z = math.fsum([model["intercept"]] + [
        model["coefficients"][name] * float(values[name]) for name in names
    ] + [
        model["time_coefficients"]["sin"] * math.sin(phase),
        model["time_coefficients"]["cos"] * math.cos(phase),
    ])
    if not math.isfinite(z):
        raise ValueError("Nonfinite fold inference")
    return 1 / (1 + math.exp(-max(-30., min(30., z))))


def evaluate_development_folds(
    root: Path, corpus_path: str, corpus_sha256: str,
    fold_nights: tuple[str, ...], feature_names: tuple[str, ...],
    evaluation_as_of: str,
) -> dict:
    """Compare logistic candidate to a prior-night prevalence baseline.

    Results are descriptive Brier errors on qualified *observed units only*.
    No P0, Stage1 Recall, calibrated biology occurrence probability or
    untouched confirmation result can be produced by this function.
    """
    if (not isinstance(fold_nights, tuple) or not 1 <= len(fold_nights) <= MAX_FOLDS
            or list(fold_nights) != sorted(set(fold_nights))):
        raise ValueError("Unique increasing bounded development folds required")
    if not isinstance(feature_names, tuple) or not feature_names:
        raise ValueError("Explicit model features required")
    for night in fold_nights:
        validate_night(night)
    as_of = aware(evaluation_as_of)
    root = Path(root).absolute()
    corpus = _read(root, corpus_path, corpus_sha256)
    if not isinstance(corpus, dict) or corpus.get("qualification") != "AUDITED_TRAIN_ONLY":
        raise ValueError("Unqualified retrospective corpus")
    records = corpus.get("rows")
    if not isinstance(records, list):
        raise ValueError("Missing retrospective observation rows")
    receipts = {source["path"]: aware(source["received_at"])
                for source in corpus.get("source_manifest", [])}
    evaluations = []
    for night in fold_nights:
        # A fold's training snapshot must have been available before that
        # heldout night. Later arrived historical labels NEVER backfill this fit.
        cutoff = (datetime.fromisoformat(night + "T07:00:00+09:00")
                  - timedelta(microseconds=1)).isoformat()
        selection = select_training_rows(
            root, corpus_path, corpus_sha256, night, cutoff,
            require_features=feature_names,
        )
        if selection["status"] != "DEVELOPMENT_TRAINING_ELIGIBLE":
            evaluations.append({"night": night, "status": "NEED_MORE_DATA",
                                "training_counts": selection["counts"],
                                "blockers": selection["blockers"]})
            continue
        fitted = fit_candidate(selection)
        model = fitted["model"]
        negatives = selection["counts"]["negatives"]
        positives = selection["counts"]["positives"]
        baseline = (positives + 1.0) / (positives + negatives + 2.0)
        scores, comparisons, unknown = [], [], 0
        seen = set()
        for row in records:
            if row.get("night") != night:
                continue
            key = row.get("row_id")
            if not isinstance(key, str) or not key or key in seen:
                raise ValueError("Duplicate evaluation row identity")
            seen.add(key)
            t = aware(row["window_start_jst"])
            if t >= as_of:
                raise ValueError("Cannot evaluate an unfinished future observation")
            observation = row.get("observation")
            if observation == "UNKNOWN" and row.get("label") is None:
                unknown += 1
                continue
            label = row.get("label")
            if (observation not in LABELS or type(label) is not int or
                label != LABELS[observation] or row.get("quality") not in QUALITIES):
                raise ValueError("Invalid or unqualified heldout observed outcome")
            if (observation == "observed_negative" and
                (row.get("search_role") not in ("SEARCH", "PASSAGE") or
                 row.get("all_captures_recorded") is not True or
                 row.get("gpx_segment_eligible") is not True)):
                raise ValueError("Heldout Negative lacks qualified passage evidence")
            if (row.get("feature_valid_for_night") is not True or
                set(row.get("features", {})) != set(feature_names)):
                raise ValueError("Heldout historical features are not validated")
            historical_cutoff = aware(cutoff)
            if (aware(row["label_available_at"]) < t or
                aware(row["audit_available_at"]) < aware(row["label_available_at"]) or
                aware(row["label_available_at"]) > as_of or
                aware(row["audit_available_at"]) > as_of):
                raise ValueError("Heldout observation timing or audit readiness invalid")
            outcome_ref = row.get("outcome_source_ref")
            if outcome_ref not in row.get("source_refs", ()) or outcome_ref not in receipts or (
                receipts[outcome_ref] < t or
                receipts[outcome_ref] > aware(row["label_available_at"])):
                raise ValueError("Heldout label lacks consistent post-event source receipt")
            available = row.get("feature_available_at")
            if not isinstance(available, dict) or set(available) != set(feature_names):
                raise ValueError("Heldout feature availability missing")
            if any(aware(available[name]) >= historical_cutoff for name in feature_names):
                raise ValueError("Heldout feature arrived after prospective fold cutoff")
            score = _predict(model, row)
            scores.append((score - label) ** 2)
            comparisons.append((baseline - label) ** 2)
        if not scores:
            evaluations.append({"night": night, "status": "NEED_MORE_DATA",
                                "reason": "No qualified observed heldout units",
                                "unknown_units": unknown})
            continue
        evaluations.append({
            "night": night, "status": "RETROSPECTIVE_DEVELOPMENT_ONLY",
            "observed_units": len(scores), "unknown_units": unknown,
            "candidate_brier": math.fsum(scores) / len(scores),
            "prior_prevalence_baseline_brier": math.fsum(comparisons) / len(comparisons),
            "brier_improvement": (math.fsum(comparisons) - math.fsum(scores)) / len(scores),
            "model_content_sha256": model["model_sha256"],
            "training_selection_sha256": selection["selection_sha256"],
            "training_counts": selection["counts"],
        })
    # Missing or already disclosed confirmation outcomes cannot be converted
    # to validation through a second protocol ID.
    valid = [f for f in evaluations if f["status"] == "RETROSPECTIVE_DEVELOPMENT_ONLY"]
    return {
        "schema_version": "1.0",
        "status": "RETROSPECTIVE_DEVELOPMENT_ONLY" if valid else "NEED_MORE_DATA",
        "official_accuracy_evaluated": False,
        "independent_confirmation": "NOT_PERFORMED",
        "stage1_top10_recall": "NOT_EVALUATED",
        "formal_100m_10min": "NOT_EVALUATED",
        "denominator_coverage": "NOT_ESTABLISHED",
        "champion_promotion": "NOT_AUTHORIZED",
        "eligible_evaluated_nights": len(valid),
        "mean_night_brier_improvement_descriptive": (
            math.fsum(f["brier_improvement"] for f in valid) / len(valid) if valid else None
        ),
        "folds": evaluations,
    }
