"""Deterministic, bounded candidate fit on selected historical TRAIN_ONLY rows.

This fit is development evidence, never independent confirmation, official P0
or a permitted Champion activation. It emits an envelope consumed by the
existing prospective_spacetime._read_candidate_model adapter.
"""
from __future__ import annotations

import math
from zoneinfo import ZoneInfo

import numpy as np

from master_contracts import digest
from models.research_selection import validate_selection
from prospective_spacetime import VERSION, PRODUCED
from training_corpus import aware

JST = ZoneInfo("Asia/Tokyo")
REGULARIZATION = 1.0
MAX_STEPS = 400
GRADIENT_TOL = 1e-5


def fit_candidate(selection, *, threshold=0.5, max_candidates=50):
    selection = validate_selection(selection)
    if not isinstance(selection, dict) or selection.get("status") != "DEVELOPMENT_TRAINING_ELIGIBLE":
        raise ValueError("Insufficient audited prior-night training observations")
    rows = selection.get("accepted")
    names = selection.get("feature_names")
    identity = {key: selection.get(key) for key in (
        "accepted", "corpus_sha256", "source_sha256", "source_received_at",
        "heldout_night", "fit_cutoff", "feature_names", "exposed_nights",
    )}
    if (not isinstance(rows, list) or not 4 <= len(rows) <= 20000 or
            not isinstance(names, list) or not 1 <= len(names) <= 32 or
            len(names) != len(set(names)) or names != sorted(names) or
            not isinstance(selection.get("source_sha256"), dict) or
            not isinstance(selection.get("source_received_at"), dict) or
            not isinstance(selection.get("corpus_sha256"), str) or
            not isinstance(selection.get("exposed_nights"), list) or
            digest(identity) != selection.get("selection_sha256")):
        raise ValueError("Unbound training selection or feature schema")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or \
       not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Invalid candidate threshold")
    if type(max_candidates) is not int or not 1 <= max_candidates <= 100:
        raise ValueError("Invalid top candidate bound")
    cutoff = aware(selection["fit_cutoff"])
    nights = set()
    identifiers = set()
    raw_features = []
    clock_features = []
    labels = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("row_id"), str) or \
           row["row_id"] in identifiers:
            raise ValueError("Duplicate fitted observation")
        identifiers.add(row["row_id"])
        night = row["night"]
        if night >= selection["heldout_night"]:
            raise ValueError("Holdout-night label leaked into candidate fit")
        nights.add(night)
        time = aware(row["window_start_jst"]).astimezone(JST)
        if time >= cutoff or (time.hour * 3600 + time.minute * 60 + time.second) < 0:
            raise ValueError("Training observation is not before fit cutoff")
        if type(row.get("label")) is not int or row["label"] not in (0, 1):
            raise ValueError("Unknown label cannot train binary model")
        feats = row.get("features")
        if not isinstance(feats, dict) or set(feats) != set(names):
            raise ValueError("Missing model training features")
        fv = [feats[name] for name in names]
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in fv):
            raise ValueError("Nonfinite training value")
        phase = 2 * math.pi * (time.hour * 3600 + time.minute * 60 + time.second) / 86400
        raw_features.append(fv)
        clock_features.append([math.sin(phase), math.cos(phase)])
        labels.append(row["label"])
    if len(nights) < 3 or sum(labels) < 2 or len(labels) - sum(labels) < 2:
        raise ValueError("Missing class balance or multiple eligible prior nights")
    matrix = np.asarray(raw_features, dtype=np.float64)
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale[scale < 1e-12] = 1.0
    adjusted = (matrix - mean) / scale
    X = np.column_stack((
        np.ones(len(labels), dtype=np.float64),
        adjusted,
        np.asarray(clock_features, dtype=np.float64),
    ))
    y = np.asarray(labels, dtype=np.float64)
    if not np.isfinite(X).all() or not np.isfinite(mean).all() or not np.isfinite(scale).all():
        raise ValueError("Unbounded training design matrix")
    coeff = np.zeros(X.shape[1], dtype=np.float64)
    # Stable curvature upper bound for the regularized logistic objective.
    squared_frobenius = np.sum(X * X) / len(y)
    step = 1.0 / (0.25 * squared_frobenius + REGULARIZATION)
    completed = 0
    converged = False
    gradient_norm = None
    for index in range(MAX_STEPS):
        z = np.clip(X @ coeff, -30.0, 30.0)
        probabilities = 1.0 / (1.0 + np.exp(-z))
        gradient = X.T @ (probabilities - y) / len(y)
        gradient[1:] += REGULARIZATION * coeff[1:]
        gradient_norm = float(np.linalg.norm(gradient))
        if not math.isfinite(gradient_norm):
            raise ValueError("Nonfinite optimization state")
        completed = index + 1
        if gradient_norm <= GRADIENT_TOL:
            converged = True
            break
        coeff -= step * gradient
    if not converged:
        raise ValueError("Candidate fit did not converge within bounded steps")
    raw_weights = coeff[1:1 + len(names)] / scale
    raw_intercept = coeff[0] - float(np.dot(raw_weights, mean))
    if not math.isfinite(raw_intercept) or abs(raw_intercept) > 30 or \
       any(not math.isfinite(float(x)) or abs(float(x)) > 20 for x in raw_weights) or \
       any(abs(float(x)) > 20 for x in coeff[-2:]):
        raise ValueError("Fitted coefficients exceed registered inference limits")
    candidate = {
        "schema_version": "1.0",
        "model_type": "linear_logit_100m_10min",
        "implementation_version": VERSION,
        "qualification": "UNVALIDATED_CANDIDATE",
        "coefficients": {name: float(raw_weights[i]) for i, name in enumerate(names)},
        "intercept": float(raw_intercept),
        "threshold": float(threshold),
        "max_candidates": max_candidates,
        "feature_schema_sha256": digest(names),
        "training_cutoff": cutoff.isoformat(),
        "training_data_sha256": selection["selection_sha256"],
        "produced_outputs": list(PRODUCED),
        "time_basis": "jst_clock_cyclic",
        "time_coefficients": {"sin": float(coeff[-2]), "cos": float(coeff[-1])},
    }
    candidate["model_sha256"] = digest(candidate)
    # Reuse the same model contract without writing any artifacts.
    # _read_candidate_model is file-based; full validated model is verified
    # against inference schema during subsequent hash-bound publication/read.
    p = 1.0 / (1.0 + np.exp(-np.clip(X @ coeff, -30.0, 30.0)))
    brier = float(np.mean((p - y) ** 2))
    return {
        "status": "DEVELOPMENT_FIT_ONLY",
        "official_issuance_authorized": False,
        "independent_confirmation": "NOT_PERFORMED",
        "model": candidate,
        "fit_evidence": {
            "rows": len(y), "prior_nights": len(nights),
            "positives": int(np.sum(y)), "negatives": int(len(y) - np.sum(y)),
            "iterations": completed, "gradient_norm": gradient_norm,
            "converged": True, "dtype": "float64",
            "numpy_version": np.__version__,
            "regularization_l2": REGULARIZATION,
            "training_brier_DESCRIPTIVE_ONLY": brier,
            "selection_sha256": selection["selection_sha256"],
            "limitations": [
                "TRAIN_ONLY observations, not untouched future confirmation",
                "Selection and measurement bias are not corrected",
                "No calibration or island-wide occurrence probability certified",
                "Not a true pre-exploration issued P0",
            ],
        },
    }
