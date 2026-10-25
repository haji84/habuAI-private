"""HB-B1: pure, fixed-prior hierarchical TRAIN_ONLY ranking diagnostics.

Scores describe qualified observation-conditioned binary owner-capture units.
They are not detection-corrected animal presence, calibrated forecast risk, an
official 100m +/-10 minute target, or authority to issue a production P0.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import json
import re
from zoneinfo import ZoneInfo

from master_contracts import digest, validate_night
from models.research_selection import (
    canonical_digest, validate_future_rows, validate_selection,
)

JST = ZoneInfo("Asia/Tokyo")
VERSION = "habu-hierarchy-shrinkage-v1"
FAMILY = "FIXED_PRIOR_HIERARCHICAL_BETA_BERNOULLI_RANKER"
TRAINING_QUALIFICATION = "RETROSPECTIVE_TRAIN_ONLY_NOT_CONFIRMATION"
LEVELS = ("1000m", "500m", "250m", "100m", "10min")
SIZES = (1000, 500, 250, 100)
GEOMETRY = "CELL_ORIGIN_PROXY_NOT_POINT_GEOMETRY"
SCORE_SEMANTICS = "OBSERVATION_CONDITIONED_BINARY_OWNER_CAPTURE_SHRINKAGE_DIAGNOSTIC"
RECIPE = {
    "global_beta": {"alpha": 1, "beta": 1},
    "parent_strength": 4,
    "spatial_sizes_m": list(SIZES),
    "coordinate_crs": "EPSG:32652",
    "coordinate_representative": "100M_CELL_ORIGIN",
    "temporal_slot_minutes": 10,
    "temporal_period_slots": 144,
    "temporal_policy": "JST_CYCLIC_CATEGORY_NO_NEIGHBOR_SMOOTHING",
}
LIMITATIONS = [
    "TRAIN_ONLY input qualification and hashes do not independently authenticate evidence",
    "Selection, search effort and detection bias are not corrected",
    "100m cell origins are proxies; true point membership at 250m is unavailable",
    "Clock slots repeat modulo 144 with no adjacent-slot smoothing",
    "No independent confirmation, calibration, official KPI, route or production authority",
    "A joined-row digest binds supplied coverage, not true universe completeness",
]
MODEL_FIELDS = {
    "schema_version", "candidate_id", "family", "status", "training_qualification",
    "training_selection_sha256", "training_corpus_sha256", "training_cutoff",
    "heldout_night", "training_nights", "training_window_start_max",
    "feature_names", "feature_schema_sha256", "predictors_used",
    "recipe", "recipe_sha256", "geometry_semantics", "score_semantics", "parameters",
    "fit_evidence", "limitations", "science_status", "production_activation_authorized",
    "official_stage1_recall_computed", "official_100m_10min_kpi_computed", "model_sha256",
}


def _time(value):
    if not isinstance(value, str):
        raise ValueError("Aware timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("Aware timestamp required")
    return result.astimezone(JST)


def _path(cell_x, cell_y, when):
    # Canonical selection only retains a 100m integer cell. Multiplying by 100
    # gives its origin, NOT the original observation point or cell centre.
    x_m, y_m = cell_x * 100, cell_y * 100
    spatial = tuple(f"utm52n_{'1km' if size == 1000 else str(size) + 'm'}_"
                    f"{x_m // size}_{y_m // size}" for size in SIZES)
    slot = (when.hour * 60 + when.minute) // 10 % 144
    return (*spatial, slot)


def _research_flags():
    return {
        "science_status": "NOT_VALIDATED",
        "production_activation_authorized": False,
        "official_stage1_recall_computed": False,
        "official_100m_10min_kpi_computed": False,
    }


def _seal(value, field):
    # Input bounds are enforced at the shared gate. A complete, generated
    # hierarchy expands those rows, so its artifact hash must not reuse the
    # input byte cap and accidentally discard an otherwise valid universe.
    value[field] = digest(value)
    return value


def fit_hierarchy(selection):
    """Fit only a validated PR46 selector return value, with no file discovery.

    A valid insufficient/positive-only selector result returns NEED_MORE_DATA
    and model=None. Malformed, unknown-label or altered selections raise ValueError.
    A ready return is the JSON-serializable model itself, bound to its selection.
    """
    selected = validate_selection(selection)
    if selected["status"] != "DEVELOPMENT_TRAINING_ELIGIBLE":
        return {
            "status": "NEED_MORE_DATA", "model": None, "candidate_id": "HB-B1",
            "training_selection_sha256": selected["selection_sha256"],
            "fit_evidence": dict(selected["counts"]),
            "blockers": list(selected["blockers"]), **_research_flags(),
        }
    counts = [defaultdict(lambda: [0, 0]) for _ in LEVELS]
    for row in selected["accepted"]:
        path = _path(row["cell_x"], row["cell_y"], _time(row["window_start_jst"]))
        for depth, table in enumerate(counts, 1):
            node = table[path[:depth]]
            node[0] += 1
            node[1] += row["label"]
    parameters = {
        "global": {"units": selected["counts"]["accepted_rows"],
                   "positives": selected["counts"]["positives"]},
        "levels": {
            level: [{"path": list(path), "units": value[0], "positives": value[1]}
                    for path, value in sorted(table.items())]
            for level, table in zip(LEVELS, counts)
        },
    }
    model = {
        "schema_version": VERSION, "candidate_id": "HB-B1",
        "family": FAMILY,
        "status": "DEVELOPMENT_CANDIDATE_FITTED",
        "training_qualification": selected["qualification"],
        "training_selection_sha256": selected["selection_sha256"],
        "training_corpus_sha256": selected["corpus_sha256"],
        "training_cutoff": _time(selected["fit_cutoff"]).isoformat(),
        "heldout_night": selected["heldout_night"],
        "training_nights": sorted({row["night"] for row in selected["accepted"]}),
        "training_window_start_max": max(_time(row["window_start_jst"])
                                         for row in selected["accepted"]).isoformat(),
        "feature_names": list(selected["feature_names"]),
        "feature_schema_sha256": canonical_digest(selected["feature_names"]),
        "predictors_used": ["100m_cell_origin", "jst_10min_clock_slot"],
        "recipe": json.loads(json.dumps(RECIPE)),
        "recipe_sha256": canonical_digest(RECIPE),
        "geometry_semantics": GEOMETRY, "score_semantics": SCORE_SEMANTICS,
        "parameters": parameters, "fit_evidence": dict(selected["counts"]),
        "limitations": list(LIMITATIONS), **_research_flags(),
    }
    return _seal(model, "model_sha256")


def _count(node):
    n, k = node.get("units"), node.get("positives")
    if type(n) is not int or type(k) is not int or not 1 <= n <= 20000 or not 0 <= k <= n:
        raise ValueError("Invalid hierarchical sufficient statistics")
    return n, k


def _check_path(path, depth):
    if not isinstance(path, list) or len(path) != depth:
        raise ValueError("Invalid hierarchical path")
    coordinates = []
    for index, part in enumerate(path[:4]):
        size = SIZES[index]
        prefix = "1km" if size == 1000 else str(size) + "m"
        match = re.fullmatch(r"utm52n_" + prefix + r"_(0|[1-9][0-9]*)_(0|[1-9][0-9]*)", str(part))
        if not match:
            raise ValueError("Invalid projected hierarchy unit")
        coordinates.append((int(match[1]), int(match[2])))
    if depth == 5 and (type(path[-1]) is not int or not 0 <= path[-1] < 144):
        raise ValueError("Invalid cyclic clock slot")
    if depth >= 4:
        cell_x, cell_y = coordinates[3]
        if not 0 <= cell_x <= 100000 or not 0 <= cell_y <= 100000:
            raise ValueError("Cell outside training selector domain")
        expected = _path(cell_x, cell_y, datetime(2000, 1, 1, tzinfo=JST))[:4]
        if tuple(path[:4]) != expected:
            raise ValueError("Hierarchy does not follow physical cell-origin geometry")


def _checked_tables(model):
    if not isinstance(model, dict) or set(model) != MODEL_FIELDS:
        raise ValueError("Exact hierarchy model envelope required")
    if model.get("model_sha256") != canonical_digest(
            {key: value for key, value in model.items() if key != "model_sha256"}):
        raise ValueError("Missing or changed hierarchy model hash")
    if (model.get("schema_version") != VERSION or model.get("candidate_id") != "HB-B1"
            or model.get("family") != FAMILY
            or model.get("training_qualification") != TRAINING_QUALIFICATION
            or model.get("status") != "DEVELOPMENT_CANDIDATE_FITTED"
            or canonical_digest(model.get("recipe")) != canonical_digest(RECIPE)
            or model.get("recipe_sha256") != canonical_digest(RECIPE)
            or model.get("geometry_semantics") != GEOMETRY
            or model.get("score_semantics") != SCORE_SEMANTICS
            or model.get("predictors_used") != ["100m_cell_origin", "jst_10min_clock_slot"]
            or model.get("limitations") != LIMITATIONS
            or any(type(model[key]) is not type(value) or model[key] != value
                   for key, value in _research_flags().items())):
        raise ValueError("Unrecognized or changed hierarchy recipe/authority")
    if any(type(model[key]) is not str or not re.fullmatch("[0-9a-f]{64}", model[key])
           for key in ("training_selection_sha256", "training_corpus_sha256")):
        raise ValueError("Missing hierarchy training identity")
    names = model["feature_names"]
    if (type(names) is not list or not 1 <= len(names) <= 32
            or any(type(name) is not str or not re.fullmatch("[A-Za-z][A-Za-z0-9_]{0,63}", name)
                   for name in names) or names != sorted(set(names))
            or model["feature_schema_sha256"] != canonical_digest(names)):
        raise ValueError("Invalid hierarchy feature schema")
    if type(model["heldout_night"]) is not str:
        raise ValueError("Hierarchy held-out operational night required")
    validate_night(model["heldout_night"])
    fit_cutoff = _time(model["training_cutoff"])
    if fit_cutoff >= _time(model["heldout_night"] + "T07:00:00+09:00"):
        raise ValueError("Hierarchy training cutoff must precede held-out night start")
    parameters = model.get("parameters")
    if (not isinstance(parameters, dict) or set(parameters) != {"global", "levels"}
            or not isinstance(parameters["global"], dict)
            or set(parameters["global"]) != {"units", "positives"}
            or not isinstance(parameters["levels"], dict)
            or set(parameters["levels"]) != set(LEVELS)):
        raise ValueError("Invalid hierarchy parameters")
    n, k = _count(parameters["global"])
    evidence = model.get("fit_evidence")
    if (not isinstance(evidence, dict)
            or set(evidence) != {"accepted_rows", "rejected_rows", "nights", "positives", "negatives"}
            or any(type(value) is not int for value in evidence.values())
            or evidence["accepted_rows"] != n or evidence["positives"] != k
            or evidence["negatives"] != n-k or not 3 <= evidence["nights"] <= n
            or k < 2 or n-k < 2 or not 0 <= evidence["rejected_rows"] <= 20000-n):
        raise ValueError("Hierarchy fit counts do not match parameters")
    nights = model["training_nights"]
    if type(nights) is not list or len(nights) != evidence["nights"]:
        raise ValueError("Hierarchy training nights do not match actual fit evidence")
    for night in nights:
        if type(night) is not str:
            raise ValueError("Hierarchy training night required")
        validate_night(night)
        if night >= model["heldout_night"] or _time(night + "T07:00:00+09:00") >= fit_cutoff:
            raise ValueError("Hierarchy training night must precede held-out night and fit cutoff")
    if nights != sorted(set(nights)):
        raise ValueError("Hierarchy training nights must be unique and sorted")
    last_window = _time(model["training_window_start_max"])
    if (last_window >= fit_cutoff or last_window.minute % 10 or last_window.second
            or last_window.microsecond
            or (last_window - timedelta(hours=7)).date().isoformat() != nights[-1]):
        raise ValueError("Hierarchy latest training observation must precede fit cutoff")
    tables = []
    parents = {(): (n, k)}
    for depth, level in enumerate(LEVELS, 1):
        nodes = parameters["levels"][level]
        if not isinstance(nodes, list) or not 1 <= len(nodes) <= n:
            raise ValueError("Bounded hierarchical parameter table required")
        table, children = {}, defaultdict(lambda: [0, 0])
        for node in nodes:
            if not isinstance(node, dict) or set(node) != {"path", "units", "positives"}:
                raise ValueError("Invalid hierarchical node")
            _check_path(node["path"], depth)
            path = tuple(node["path"])
            if path in table or path[:-1] not in parents:
                raise ValueError("Duplicate or orphaned hierarchy node")
            node_n, node_k = _count(node)
            table[path] = (node_n, node_k)
            children[path[:-1]][0] += node_n
            children[path[:-1]][1] += node_k
        if {key: tuple(value) for key, value in children.items()} != parents:
            raise ValueError("Hierarchy child counts do not partition parent observations")
        tables.append(table)
        parents = table
    return (k + 1) / (n + 2), tables


def _scores(path, global_mean, tables):
    scores, prior = [], global_mean
    for depth, table in enumerate(tables, 1):
        n, k = table.get(path[:depth], (0, 0))
        prior = (k + 4 * prior) / (n + 4)
        scores.append(prior)
    return scores


def rank_hierarchy(model, rows, *, cutoff_time, universe_sha256):
    """Score every supplied future joined unit; never derive a universe from labels.

    universe_sha256 is the canonical digest of the complete supplied label-free
    joined row array. It is distinct from an upstream Universe source-file hash.
    True ex-ante coverage/authenticity still requires upstream independent proof.
    """
    global_mean, tables = _checked_tables(model)
    cutoff = _time(cutoff_time)
    if _time(model["training_cutoff"]) >= cutoff:
        raise ValueError("Model fit must precede forecast cutoff strictly")
    future = validate_future_rows(
        rows, cutoff_time=cutoff_time, universe_sha256=universe_sha256,
        heldout_night=model["heldout_night"], feature_names=model["feature_names"],
    )
    groups = [dict() for _ in SIZES]
    units = []
    for row in future:
        when = _time(row["window_start_jst"])
        path = _path(row["cell_x"], row["cell_y"], when)
        scores = _scores(path, global_mean, tables)
        item = {
            "row_id": row["row_id"], "operational_night": row["operational_night"],
            "window_start_jst": when.isoformat(), "cell_id": path[3],
            "area_1km": path[0], "zone_500m": path[1], "zone_250m": path[2],
            "tenmin_slot": path[4], "rank_score_diagnostic": scores[-1],
            "hierarchy_scores": dict(zip(LEVELS, scores)),
        }
        units.append(item)
        for index, group in enumerate(groups):
            node_path = path[:index+1]
            if node_path not in group:
                group[node_path] = {
                    "unit_id": path[index],
                    "parent_unit_id": path[index-1] if index else "GLOBAL",
                    "path": list(node_path), "rank_score_diagnostic": scores[index],
                    "training_units": tables[index].get(node_path, (0, 0))[0],
                    "candidate_units": 0,
                }
            group[node_path]["candidate_units"] += 1
    rankings = {}
    for level, group in zip(LEVELS, groups):
        ranked = sorted(group.values(), key=lambda value: (-value["rank_score_diagnostic"], value["path"]))
        conditional = defaultdict(int)
        for rank, item in enumerate(ranked, 1):
            conditional[item["parent_unit_id"]] += 1
            item["rank"] = rank
            item["conditional_rank"] = conditional[item["parent_unit_id"]]
        rankings[level] = ranked
    time_ranked = sorted(units, key=lambda value: (-value["rank_score_diagnostic"], value["row_id"]))
    conditional = defaultdict(int)
    rankings["10min"] = []
    for rank, item in enumerate(time_ranked, 1):
        conditional[item["cell_id"]] += 1
        item["rank"] = rank
        rankings["10min"].append({
            "row_id": item["row_id"],
            "unit_id": item["cell_id"] + "@" + item["window_start_jst"],
            "parent_unit_id": item["cell_id"], "tenmin_slot": item["tenmin_slot"],
            "rank_score_diagnostic": item["rank_score_diagnostic"],
            "rank": rank, "conditional_rank": conditional[item["cell_id"]],
            "candidate_units": 1,
        })
    output = {
        "schema_version": VERSION, "status": "RESEARCH_HIERARCHY_RANKING_DIAGNOSTICS",
        "candidate_id": "HB-B1", "model_sha256": model["model_sha256"],
        "training_selection_sha256": model["training_selection_sha256"],
        "universe_sha256": universe_sha256,
        "universe_digest_semantics": "CANONICAL_JOINED_ROWS_NOT_SOURCE_UNIVERSE_FILE",
        "universe_rows": len(future), "operational_night": model["heldout_night"],
        "cutoff_time": cutoff.isoformat(), "geometry_semantics": GEOMETRY,
        "score_semantics": SCORE_SEMANTICS,
        "unit_scores": sorted(units, key=lambda value: value["row_id"]),
        "hierarchy_rankings": rankings, "area_rank_top10": rankings["1000m"][:10],
        "formal_100m_10min_targets_produced": False,
        "forecast_universe_completeness_verified": False,
        "route_status": "NOT_PRODUCED", "limitations": list(LIMITATIONS),
        **_research_flags(),
    }
    return _seal(output, "prediction_sha256")
