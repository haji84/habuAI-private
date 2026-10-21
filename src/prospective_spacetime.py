"""Read-only 100m x 10min candidate inference from PR #32 prospective inputs.

This connector does NOT produce an ORIGINAL P0, authorize a Champion, or
claim measured/calibrated probability skill. It only tests a declared model
candidate against as-of, hash-bound feature/universe snapshots.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from time import monotonic

from master_contracts import canonical_bytes, digest, file_hash, safe_path
from prospective_inputs import load_prospective_inputs

VERSION = "prospective-logit-candidate-v1"
MAX_MODEL_BYTES = 128 * 1024
MAX_ROWS = 120_000
MAX_CANDIDATES = 100
SHA = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")
PRODUCED = ["unit_probability", "spatiotemporal_ranking"]


def _aware(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Aware ISO timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timezone required")
    return result


def _finite(value, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Invalid numeric " + field)
    return float(value)


def _read_candidate_model(root: Path, relative: str, expected_sha: str):
    if (not isinstance(relative, str) or
        Path(relative).parts[:2] != ("models", "candidates") or
        Path(relative).suffix != ".json" or
        not isinstance(expected_sha, str) or not SHA.fullmatch(expected_sha)):
        raise ValueError("Bound models/candidates JSON and SHA-256 required")
    path = safe_path(root, relative)
    if not path.is_file() or path.stat().st_size > MAX_MODEL_BYTES:
        raise ValueError("Missing or oversized candidate model")
    with path.open("rb") as stream:
        raw = stream.read(MAX_MODEL_BYTES + 1)
    if len(raw) > MAX_MODEL_BYTES or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("Candidate model bytes do not match SHA-256")
    model = json.loads(raw)
    if not isinstance(model, dict):
        raise ValueError("Candidate model must be a JSON object")
    canonical_bytes(model)
    required = {
        "schema_version", "model_type", "implementation_version",
        "qualification", "coefficients", "intercept", "threshold",
        "max_candidates", "feature_schema_sha256", "training_cutoff",
        "training_data_sha256", "produced_outputs", "model_sha256",
    }
    if not required.issubset(model):
        raise ValueError("Incomplete candidate model artifact")
    if (model["schema_version"] != "1.0" or
        model["model_type"] != "linear_logit_100m_10min" or
        model["implementation_version"] != VERSION or
        model["qualification"] != "UNVALIDATED_CANDIDATE" or
        model["produced_outputs"] != PRODUCED):
        raise ValueError("Candidate has unrecognized or privileged model capability")
    body = {k: v for k, v in model.items() if k != "model_sha256"}
    if model["model_sha256"] != digest(body):
        raise ValueError("Candidate model content digest mismatch")
    for field in ("feature_schema_sha256", "training_data_sha256"):
        if not isinstance(model[field], str) or not SHA.fullmatch(model[field]):
            raise ValueError("Invalid candidate evidence hash")
    coefficients = model["coefficients"]
    if not isinstance(coefficients, dict) or not 1 <= len(coefficients) <= 32:
        raise ValueError("Nonempty bounded candidate coefficients required")
    if any(not isinstance(n, str) or not NAME.fullmatch(n) for n in coefficients):
        raise ValueError("Invalid feature name in candidate model")
    for name, value in coefficients.items():
        if abs(_finite(value, name)) > 20:
            raise ValueError("Unbounded candidate coefficient")
    if model["feature_schema_sha256"] != digest(sorted(coefficients)):
        raise ValueError("Candidate feature schema is not bound to coefficients")
    if abs(_finite(model["intercept"], "intercept")) > 30:
        raise ValueError("Unbounded candidate intercept")
    threshold = _finite(model["threshold"], "threshold")
    if not 0 <= threshold <= 1:
        raise ValueError("Invalid candidate threshold")
    number = model["max_candidates"]
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= MAX_CANDIDATES:
        raise ValueError("Invalid bounded top candidate count")
    _aware(model["training_cutoff"])
    return model


def infer_candidate(
    root: Path, snapshot_path: str, snapshot_sha256: str,
    night: str, as_of: datetime, model_path: str, model_sha256: str,
    *, budget_seconds: float = 30.0,
) -> dict:
    """Return ordered candidate units only; never Freeze or mutate any input.

    The linear-logit coefficients are externally specified candidate parameters.
    Until true training, untouched confirmation and Task8 activation are proved,
    probability numbers are UNVALIDATED development outputs, not trusted odds.
    """
    if (isinstance(budget_seconds, bool) or
        not isinstance(budget_seconds, (int, float)) or
        not math.isfinite(budget_seconds) or not 0 < budget_seconds <= 300):
        raise ValueError("Invalid shared execution budget")
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("Timezone-aware issue time required")
    deadline = monotonic() + budget_seconds

    def check():
        if monotonic() >= deadline:
            raise TimeoutError("Candidate inference elapsed budget exceeded")

    root = Path(root).absolute()
    check()
    model = _read_candidate_model(root, model_path, model_sha256)
    check()
    names = tuple(sorted(model["coefficients"]))
    # Input validator from PR #32 rejects post-outcome fields, tampering,
    # stale/future cells and missing/extra ex-ante feature values.
    left = deadline - monotonic()
    if left <= 0:
        raise TimeoutError("No remaining input-validation budget")
    bound = load_prospective_inputs(
        root, snapshot_path, snapshot_sha256, night, as_of,
        model_feature_names=names, budget_seconds=left,
    )
    check()
    cutoff = _aware(bound["cutoff_time"])
    if _aware(model["training_cutoff"]) >= cutoff:
        raise ValueError("Candidate training cutoff is not before forecast cutoff")
    if model["feature_schema_sha256"] != bound["feature_schema_sha256"]:
        raise ValueError("Registered candidate feature schema mismatch")
    rows = bound["rows"]
    if not rows or len(rows) > MAX_ROWS:
        raise ValueError("Candidate inference row budget exceeded")
    results = []
    for row in rows:
        check()
        values = row["features"]
        terms = [_finite(model["intercept"], "intercept")]
        for name in names:
            terms.append(model["coefficients"][name] * _finite(values[name], name))
        logit = math.fsum(terms)
        if not math.isfinite(logit):
            raise ValueError("Invalid candidate logit")
        p = 1 / (1 + math.exp(-max(-30.0, min(30.0, logit))))
        x, y = float(row["utm_x_m"]), float(row["utm_y_m"])
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("Invalid candidate cell coordinates")
        results.append({
            "row_id": row["row_id"],
            "operational_night": night,
            "window_start_jst": row["window_start_jst"],
            "utm_x_m": x,
            "utm_y_m": y,
            "cell_x_100m": math.floor(x / 100),
            "cell_y_100m": math.floor(y / 100),
            "candidate_probability": p,
            "probability_status": "UNVALIDATED",
        })
    ranked = sorted(results, key=lambda v: (-v["candidate_probability"], v["row_id"]))
    selected = [r for r in ranked if r["candidate_probability"] >= model["threshold"]][
        :model["max_candidates"]
    ]
    check()
    # A sequential rescan detects many concurrent modifications but does not
    # prove an atomic snapshot. Trusted immutable source receipts remain missing.
    sources = dict(bound["consumed_sha256"])
    sources[model_path] = model_sha256
    for name, expected in sources.items():
        check()
        if file_hash(safe_path(root, name)) != expected:
            raise ValueError("Candidate input changed during inference")
    check()
    return {
        "schema_version": "1.0",
        "status": "PREPRODUCTION_CANDIDATE_INFERENCE",
        "qualification": "UNVALIDATED_MODEL_AND_INPUT_PROVENANCE",
        "official_issuance_authorized": False,
        "prediction_class": "CANDIDATE_DIAGNOSTIC_NOT_ORIGINAL",
        "formal_100m_10min_status": "NOT_VALIDATED",
        "operational_night": night,
        "cutoff_time": bound["cutoff_time"],
        "model_path": model_path,
        "model_sha256": model_sha256,
        "model_content_sha256": model["model_sha256"],
        "input_snapshot_sha256": snapshot_sha256,
        "feature_schema_sha256": bound["feature_schema_sha256"],
        "consumed_sha256": sources,
        "unit_predictions": sorted(results, key=lambda v: v["row_id"]),
        "candidate_targets_100m_10min": selected,
        "not_produced": [
            "OFFICIAL_P0", "CALIBRATED_TIME_PROBABILITY",
            "FULL_NIGHT_SCORABLE_UNIVERSE", "COUNT_SIZE_ROUTE_ABC",
            "REGISTERED_PRODUCTION_CHAMPION", "TRUSTED_IMMUTABLE_ISSUANCE",
        ],
    }
