"""HB-A0 research prior for conditional observed-unit owner capture outcomes.

Despite the lane/module name, these are not biological occupancy, animal-count,
detection-corrected or calibrated island-wide probabilities. Fit only the
existing audited TRAIN_ONLY selection; predict every supplied future unit.
"""
from __future__ import annotations

import platform
from collections import defaultdict

from master_contracts import digest

from .research_selection import (
    JST, _aware, _finite, _hash, _json_copy, _names, _night, _sources, _window,
    area_id, canonical_digest, validate_future_rows, validate_selection,
)

VERSION = "beta-binomial-area-shrinkage-v1"
SEMANTICS = "OWNER_CAPTURE_BINARY_GIVEN_QUALIFIED_OBSERVED_100M_10MIN_UNIT"
QUALIFICATION = "RESEARCH_ONLY_NOT_CONFIRMATION"
CONFIG = {
    "global_prior_alpha": 1.0, "global_prior_beta": 1.0,
    "area_prior_strength": 4.0, "area_resolution_m": 1000,
    "observation_resolution_m": 100, "observation_window_seconds": 600,
}
LIMITATIONS = [
    "Conditional observed-unit capture outcome; selection and measurement bias remain",
    "No biological occupancy, detection correction, abundance or count inference",
    "No untouched confirmation, calibration certification or formal target validation",
    "Selector identity checks do not independently authenticate source qualification",
]
MODEL_FIELDS = {
    "schema_version", "candidate_id", "model_type", "implementation_version",
    "qualification", "target_semantics", "scientific_status",
    "official_issuance_authorized", "production_activation_authorized",
    "config", "config_sha256", "selection_sha256", "corpus_sha256",
    "source_sha256", "source_received_at", "fit_cutoff", "heldout_night",
    "training_nights", "training_window_start_max", "selection_feature_names", "counts",
    "global_probability", "areas", "model_sha256",
}


def _global(positives, units):
    return (positives + CONFIG["global_prior_alpha"]) / (
        units + CONFIG["global_prior_alpha"] + CONFIG["global_prior_beta"])


def _area_probability(positives, units, global_probability):
    return (positives + CONFIG["area_prior_strength"] * global_probability) / (
        units + CONFIG["area_prior_strength"])


def fit_shrinkage(selection):
    """Fit fixed Beta(1,1) global and strength-4 1km empirical shrinkage.

    This is a pure bounded calculation. An insufficient but valid selector
    envelope returns NEED_MORE_DATA and model=None; malformed data raise
    ValueError. Receipt consistency never elevates this research-only fit.
    """
    selected = validate_selection(selection)
    common = {
        "official_issuance_authorized": False, "scientific_status": "NOT_VALIDATED",
        "production_activation_authorized": False,
    }
    if selected["status"] == "NEED_MORE_DATA":
        return dict(common, status="NEED_MORE_DATA", model=None,
            blockers=list(selected["blockers"]),
            fit_evidence={"counts": selected["counts"],
                "selection_sha256": selected["selection_sha256"],
                "independent_confirmation": "NOT_PERFORMED",
                "limitations": list(LIMITATIONS)})
    rows, counts = selected["accepted"], selected["counts"]
    global_probability = _global(counts["positives"], len(rows))
    by_area = defaultdict(lambda: [0, 0])
    for row in rows:
        stats = by_area[area_id(row["cell_x"], row["cell_y"])]
        stats[0] += 1
        stats[1] += row["label"]
    areas = {
        key: {"units": units, "positives": positives,
              "probability": _area_probability(positives, units, global_probability)}
        for key, (units, positives) in sorted(by_area.items())
    }
    model = {
        "schema_version": "1.0", "candidate_id": "HB-A0",
        "model_type": "beta_binomial_area_shrinkage", "implementation_version": VERSION,
        "qualification": QUALIFICATION, "target_semantics": SEMANTICS,
        **common, "config": dict(CONFIG), "config_sha256": canonical_digest(CONFIG),
        "selection_sha256": selected["selection_sha256"],
        "corpus_sha256": selected["corpus_sha256"],
        "source_sha256": selected["source_sha256"],
        "source_received_at": selected["source_received_at"],
        "fit_cutoff": selected["fit_cutoff"], "heldout_night": selected["heldout_night"],
        "training_nights": sorted({row["night"] for row in rows}),
        "training_window_start_max": max(_aware(row["window_start_jst"]) for row in rows).astimezone(JST).isoformat(),
        "selection_feature_names": list(selected["feature_names"]),
        "counts": dict(counts), "global_probability": global_probability, "areas": areas,
    }
    model["model_sha256"] = canonical_digest(model)
    brier = sum((areas[area_id(row["cell_x"], row["cell_y"])]["probability"] - row["label"]) ** 2
                for row in rows) / len(rows)
    return dict(common, status="DEVELOPMENT_FIT_ONLY", model=model, blockers=[],
        fit_evidence={"counts": dict(counts), "selection_sha256": selected["selection_sha256"],
            "independent_confirmation": "NOT_PERFORMED",
            "training_brier_DESCRIPTIVE_ONLY": brier,
            "python_version": platform.python_version(), "numeric_runtime": "stdlib_float64",
            "deterministic_seed": None, "learned_environmental_features": [],
            "limitations": list(LIMITATIONS)})


def _validate_model(model):
    value = _json_copy(model)
    if type(value) is not dict or set(value) != MODEL_FIELDS:
        raise ValueError("Exact serialized area shrinkage model required")
    expected = {
        "schema_version": "1.0", "candidate_id": "HB-A0",
        "model_type": "beta_binomial_area_shrinkage", "implementation_version": VERSION,
        "qualification": QUALIFICATION, "target_semantics": SEMANTICS,
        "scientific_status": "NOT_VALIDATED",
    }
    if any(value[field] != content for field, content in expected.items()):
        raise ValueError("Unrecognized or privileged shrinkage model")
    if value["official_issuance_authorized"] is not False or value["production_activation_authorized"] is not False:
        raise ValueError("Research model cannot carry production authority")
    body = {key: item for key, item in value.items() if key != "model_sha256"}
    if _hash(value["model_sha256"]) != canonical_digest(body):
        raise ValueError("Model content SHA-256 mismatch")
    if (value["config"] != CONFIG or _hash(value["config_sha256"]) != canonical_digest(CONFIG) or
        any(type(value["config"][key]) is not type(item) for key, item in CONFIG.items())):
        raise ValueError("Unregistered shrinkage configuration")
    for field in ("selection_sha256", "corpus_sha256"):
        _hash(value[field])
    cutoff = _aware(value["fit_cutoff"])
    heldout = _night(value["heldout_night"])
    if cutoff >= _aware(heldout + "T07:00:00+09:00"):
        raise ValueError("Model fit cutoff must precede held-out night start")
    _sources(value["source_sha256"], value["source_received_at"], cutoff)
    names = _names(value["selection_feature_names"])
    if names != sorted(names):
        raise ValueError("Bound training feature schema must be sorted")
    nights = value["training_nights"]
    if type(nights) is not list or not 3 <= len(nights) <= 20_000:
        raise ValueError("Eligible prior training nights required")
    for night in nights:
        if (_night(night) >= heldout or
            _aware(night + "T07:00:00+09:00") >= cutoff):
            raise ValueError("Model training night must precede fit and held-out boundaries")
    if nights != sorted(set(nights)):
        raise ValueError("Model training nights must be unique and sorted")
    latest_window = _window(value["training_window_start_max"], nights[-1])
    if latest_window >= cutoff:
        raise ValueError("Latest actual training window must strictly precede fit cutoff")
    counts = value["counts"]
    required_counts = {"accepted_rows", "rejected_rows", "nights", "positives", "negatives"}
    if (type(counts) is not dict or set(counts) != required_counts or
        any(type(n) is not int or n < 0 or n > 20_000 for n in counts.values()) or
        not 4 <= counts["accepted_rows"] <= 20_000 or
        counts["positives"] < 2 or counts["negatives"] < 2 or
        counts["positives"] + counts["negatives"] != counts["accepted_rows"] or
        counts["accepted_rows"] + counts["rejected_rows"] > 20_000 or
        counts["nights"] != len(nights) or counts["nights"] > counts["accepted_rows"]):
        raise ValueError("Invalid fitted binary-unit support counts")
    global_probability = _finite(value["global_probability"])
    if global_probability != _global(counts["positives"], counts["accepted_rows"]):
        raise ValueError("Fitted global probability contradicts counts/prior")
    areas = value["areas"]
    if type(areas) is not dict or not 1 <= len(areas) <= counts["accepted_rows"]:
        raise ValueError("Bounded nonempty fitted areas required")
    units_total, positives_total = 0, 0
    for key, stats in areas.items():
        parts = key.split("_")
        try:
            ax, ay = int(parts[-2]), int(parts[-1])
            if key != area_id(ax * 10, ay * 10):
                raise ValueError("Noncanonical fitted area identity")
        except (ValueError, IndexError) as exc:
            raise ValueError("Invalid fitted area identity") from exc
        if (type(stats) is not dict or set(stats) != {"units", "positives", "probability"} or
            type(stats["units"]) is not int or type(stats["positives"]) is not int or
            not 1 <= stats["units"] <= counts["accepted_rows"] or
            not 0 <= stats["positives"] <= stats["units"]):
            raise ValueError("Invalid fitted area support")
        if _finite(stats["probability"]) != _area_probability(stats["positives"], stats["units"], global_probability):
            raise ValueError("Fitted area probability contradicts shrinkage support")
        units_total += stats["units"]
        positives_total += stats["positives"]
    if units_total != counts["accepted_rows"] or positives_total != counts["positives"]:
        raise ValueError("Fitted area support does not cover all training units")
    return value


def predict_shrinkage(model, rows, *, cutoff_time, universe_sha256):
    """Return a score for every supplied future unit; never emit formal targets.

    The joined-row digest prevents changing/subsetting an already bound input.
    It cannot prove that the caller supplied a genuine complete source universe.
    """
    fitted = _validate_model(model)
    if _aware(fitted["fit_cutoff"]) >= _aware(cutoff_time):
        raise ValueError("Model fit cutoff must strictly precede forecast cutoff")
    future = validate_future_rows(rows, cutoff_time=cutoff_time,
        universe_sha256=universe_sha256, heldout_night=fitted["heldout_night"])
    predictions = []
    for row in future:
        key = area_id(row["cell_x"], row["cell_y"])
        probability = fitted["areas"].get(key, {}).get("probability", fitted["global_probability"])
        predictions.append({"row_id": row["row_id"],
            "operational_night": row["operational_night"],
            "window_start_jst": row["window_start_jst"],
            "cell_x": row["cell_x"], "cell_y": row["cell_y"], "area_id_1km": key,
            "probability": probability, "spatial_score": probability,
            "probability_status": "NOT_VALIDATED"})
    result = {
        "status": "RESEARCH_PREDICTIONS_ONLY", "scientific_status": "NOT_VALIDATED",
        "official_issuance_authorized": False, "production_activation_authorized": False,
        "model_sha256": fitted["model_sha256"], "universe_sha256": universe_sha256,
        "universe_digest_semantics": "CANONICAL_SUPPLIED_JOINED_ROWS_NOT_SOURCE_FILE_SHA",
        "target_semantics": SEMANTICS, "cutoff_time": _aware(cutoff_time).isoformat(),
        "operational_night": fitted["heldout_night"],
        "unit_predictions": predictions, "formal_100m_10min_status": "NOT_PRODUCED",
        "limitations": list(LIMITATIONS),
    }
    # Every generated field is bounded/validated above. A full output may be
    # larger than the joined-input limit; hashing never truncates its row set.
    result["prediction_sha256"] = digest(result)
    return result
