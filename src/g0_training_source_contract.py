"""Strict TRAIN_ONLY source declarations before the existing row selector.

This additive, conservative gate binds declared source closure and four readiness
times. It does not authenticate witnesses, certify search intent, assign labels
or authorize scientific fitting. The existing source-bound selector owns row and
negative-proof checks; the forecast module owns the shared reader/readiness DAG.
"""
from __future__ import annotations

import json
from datetime import timedelta

import g0_forecast_contract as g0
from codex_cycle_contract import training_boundary
from master_contracts import canonical_bytes, digest
from prospective_inputs import ProspectiveReadContext, READINESS_FIELDS, InputCapacityError
from training_corpus import MAX_BYTES, MAX_ROWS, SOURCE_ROLES, aware, select_training_rows

VERSION = "habu-g0-training-source-contract-v1"
NODE_FIELDS = {"id", "ref", "source_role", "source_kind", "parents", "readiness", "usable_at"}
FIELDS = {"schema_version", "kind", "corpus", "policy", "row_validity", "features",
          "feature_definition_sha256", "source_nodes", "readiness", "usable_at"}


class G0TrainingInputBlocked(ValueError):
    """A legacy corpus lacks this stricter mode's required available inputs."""


def _fields(value, fields):
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Exact G0 training source declaration fields required")


def _reference(value, purpose):
    g0._ref(value)
    path = value["path"]
    if purpose == "manifest":
        allowed = path.startswith("protocols/development/")
    elif purpose == "corpus":
        allowed = path.startswith("data/processed/")
    elif purpose == "policy":
        allowed = path == g0.POLICY_PATH
    elif purpose == "code":
        allowed = path.startswith(("src/", "scripts/")) and path.endswith(".py")
    else:
        allowed = path.split("/")[0] in {"data", "evidence", "features"}
    if (not allowed or any(ord(char) < 32 or ord(char) == 127 for char in path) or
            any(part.casefold() in {"sealed", "confirmation"} for part in path.split("/"))):
        raise ValueError("Forbidden G0 training source namespace, including sealed confirmation")
    return value


def _available(readiness, boundary):
    if type(readiness) is not dict or set(readiness) != READINESS_FIELDS:
        raise G0TrainingInputBlocked("G0_INPUT_BLOCKED: all four source readiness times required")
    if any(aware(value) >= boundary for value in readiness.values()):
        raise G0TrainingInputBlocked("G0_INPUT_BLOCKED: strict training source not available before boundary")


def _ready(readiness, usable_at, boundary, *, parents=()):
    _available(readiness, boundary)
    return g0.validate_readiness(readiness, usable_at, boundary, parent_usable_at=parents)


def _bound(value, purpose):
    _fields(value, {"ref", "readiness", "usable_at"})
    _reference(value["ref"], purpose)


def _validate_row_validity(value, corpus, corpus_sha, definitions_sha, definitions, by_id, by_path, raw_sources, check):
    _fields(value, {"schema_version", "corpus_sha256", "feature_definition_sha256", "rows"})
    if (value["schema_version"] != "habu-g0-training-validity-v1" or
            value["corpus_sha256"] != corpus_sha or value["feature_definition_sha256"] != definitions_sha):
        raise ValueError("Training physical validity corpus/definition mismatch")
    rows, validity = corpus.get("rows"), value["rows"]
    if type(rows) is not list or len(rows) > MAX_ROWS or type(validity) is not dict or len(validity) != len(rows):
        raise ValueError("Complete bounded training physical validity rows required")
    seen = set()
    for row in rows:
        check()
        if type(row) is not dict or type(row.get("row_id")) is not str or row["row_id"] in seen:
            raise ValueError("Unique physical training row identities required")
        identity = row["row_id"]
        seen.add(identity)
        physical = validity.get(identity)
        _fields(physical, set(definitions))
        bindings = row.get("feature_source_refs")
        _fields(bindings, set(definitions))
        start = aware(row.get("window_start_jst"))
        try:
            end = start + timedelta(seconds=600)
        except OverflowError as exc:
            raise ValueError("Training window exceeds supported time range") from exc
        for name in definitions:
            check()
            _fields(physical[name], {"valid_time", "source_ids"})
            g0._cover(physical[name]["valid_time"], start, end)
            identifiers, paths = physical[name]["source_ids"], bindings[name]
            if (type(identifiers) is not list or not identifiers or
                    any(type(identifier) is not str for identifier in identifiers) or
                    len(set(identifiers)) != len(identifiers) or type(paths) is not list or not paths or
                    any(type(path) is not str for path in paths) or len(set(paths)) != len(paths)):
                raise ValueError("Explicit unique per-feature training source bindings required")
            expected = set()
            for path in paths:
                node = by_path.get(path)
                if node is None or node["source_role"] != "feature":
                    raise ValueError("Training feature must bind feature-role source closure")
                expected.add(node["id"])
            if set(identifiers) != expected or any(identifier not in by_id for identifier in identifiers):
                raise ValueError("Training physical validity source identity mismatch")
            leaves = set().union(*(raw_sources[identifier] for identifier in identifiers))
            if leaves != set(definitions[name]["required_source_ids"]):
                raise ValueError("Training feature derivation does not bind the registered raw source set")
    if seen != set(validity):
        raise ValueError("Extra or missing training physical validity rows")


def select_g0_training_rows(root, manifest_ref, heldout_night, fit_cutoff, forecast_cutoff,
                            *, expected_feature_definition_sha256, exposed_nights=(),
                            budget_seconds=30, _read_context=None):
    """Return a declaration receipt and unchanged source-bound selector output.

    Unlike legacy selection, *every* source in this strict corpus must be ready
    before min(fit, forecast, evaluated-night start). Later unused/rejected
    sources block this mode without changing their legacy row classifications.
    No sealed confirmation payload is an allowed source in this API.
    """
    if _read_context is not None and not isinstance(_read_context, ProspectiveReadContext):
        raise ValueError("Expected shared ProspectiveReadContext")
    context = _read_context or ProspectiveReadContext(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
    context.restrict(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
    boundary = training_boundary(heldout_night, fit_cutoff, forecast_cutoff)
    _reference(manifest_ref, "manifest")
    owned_ref = json.loads(canonical_bytes(manifest_ref))
    reader = g0.G0ArtifactReader(root, context)
    manifest = reader.read(owned_ref, small=True)
    _fields(manifest, FIELDS)
    if manifest["schema_version"] != VERSION or manifest["kind"] != "TRAIN_ONLY_SOURCE_CLOSURE":
        raise ValueError("Unsupported strict TRAIN_ONLY source contract")
    _bound(manifest["corpus"], "corpus")
    _bound(manifest["policy"], "policy")
    _bound(manifest["row_validity"], "source")
    if type(manifest["features"]) is not list or not manifest["features"]:
        raise ValueError("Explicit registered training feature definitions required")
    for feature in manifest["features"]:
        context.check()
        _fields(feature, g0.FEATURE_FIELDS)
        _fields(feature["code_ref"], g0.BOUND_FIELDS)
        _reference(g0._base_ref(feature["code_ref"]), "code")
    nodes = manifest["source_nodes"]
    if type(nodes) is not list or not nodes or len(nodes) > g0.MAX_SOURCE_NODES:
        raise InputCapacityError("CAPACITY_BLOCKED: bounded nonempty source closure required")
    by_path, by_id, projection = {}, {}, []
    # Validate all namespaces/readiness before opening any bound source payload.
    for node in nodes:
        context.check()
        _fields(node, NODE_FIELDS)
        _reference(node["ref"], "source")
        if (type(node["source_role"]) is not str or type(node["source_kind"]) is not str or
                node["source_role"] not in SOURCE_ROLES or node["source_kind"] not in {"RAW", "DERIVED"}):
            raise ValueError("Explicit training source kind and existing source role required")
        path, identifier = node["ref"]["path"], node["id"]
        if path in by_path or not isinstance(identifier, str) or identifier in by_id:
            raise ValueError("Duplicate source path/identity in training closure")
        if (type(node["parents"]) is not list or
                bool(node["parents"]) != (node["source_kind"] == "DERIVED") or
                node["source_role"] in {"active_search", "complete_outcome"} and node["source_kind"] != "DERIVED"):
            raise ValueError("Derived training source must preserve its source parents")
        _available(node["readiness"], boundary)
        projection.append({key: node[key] for key in ("id", "parents", "readiness", "usable_at")})
        by_path[path], by_id[identifier] = node, node
    graph = g0.validate_readiness_graph(projection, boundary, check=context.check)
    ancestors, raw_sources = {}, {}
    for identifier in graph["topological_order"]:
        context.check()
        node = by_id[identifier]
        inherited = set().union(*(ancestors[parent] for parent in node["parents"])) if node["parents"] else set()
        if node["source_role"] == "feature" and inherited - {"feature"}:
            raise G0TrainingInputBlocked("CAPABILITY_BLOCKED: typed lagged label/effort feature projection required")
        ancestors[identifier] = inherited | {node["source_role"]}
        leaves = set()
        if node["source_role"] == "feature" and node["source_kind"] == "RAW":
            leaves.add(identifier)
        for parent in node["parents"]:
            leaves.update(raw_sources[parent])
        raw_sources[identifier] = leaves
    policy_ready = _ready(manifest["policy"]["readiness"], manifest["policy"]["usable_at"], boundary)
    policy = reader.read(manifest["policy"]["ref"], small=True)
    if digest(policy) != g0.POLICY_DIGEST:
        raise ValueError("Frozen G0 policy drift")
    definitions, code_ready, definitions_sha = g0._definitions(
        manifest["features"], expected_feature_definition_sha256, reader, boundary)
    if manifest["feature_definition_sha256"] != definitions_sha:
        raise ValueError("Training strict feature definition binding mismatch")
    for definition in definitions.values():
        for identifier in definition["required_source_ids"]:
            node = by_id.get(identifier)
            if node is None or node["source_role"] != "feature" or node["source_kind"] != "RAW":
                raise ValueError("Registered required training raw feature source missing or wrong role")
    corpus_binding = manifest["corpus"]
    corpus_ready = _ready(corpus_binding["readiness"], corpus_binding["usable_at"], boundary,
        parents=[*graph["ready_by_id"].values(), *code_ready.values()])
    corpus_ref = corpus_binding["ref"]
    if corpus_ref["size_bytes"] > MAX_BYTES:
        raise InputCapacityError("CAPACITY_BLOCKED: training corpus byte limit")
    corpus = reader.read(corpus_ref)
    validity_binding = manifest["row_validity"]
    validity_ready = _ready(validity_binding["readiness"], validity_binding["usable_at"], boundary,
        parents=[corpus_ready])
    _ready(manifest["readiness"], manifest["usable_at"], boundary,
        parents=[corpus_ready, policy_ready, validity_ready])
    physical = reader.read(validity_binding["ref"])
    _validate_row_validity(physical, corpus, corpus_ref["sha256"], definitions_sha,
        definitions, by_id, by_path, raw_sources, context.check)
    sources = corpus.get("source_manifest")
    if type(sources) is not list or len(sources) != len(nodes):
        raise ValueError("Source closure must bind the complete corpus manifest")
    seen = set()
    for source in sources:
        context.check()
        _fields(source, {"path", "sha256", "received_at", "role"})
        if type(source["path"]) is not str:
            raise ValueError("Corpus source identity must be a string")
        node = by_path.get(source["path"])
        if (node is None or source["path"] in seen or source["sha256"] != node["ref"]["sha256"] or
                source["role"] != node["source_role"] or
                aware(source["received_at"]) != aware(node["readiness"]["source_received_at"])):
            raise ValueError("Corpus source identity/role/received time mismatch")
        seen.add(source["path"])
        if node["source_role"] in {"active_search", "complete_outcome"}:
            receipt = reader.read(node["ref"])
            basis = receipt.get("basis_source_refs")
            if type(basis) is not list or not basis:
                raise ValueError("Derived scope receipt source basis missing")
            expected = set()
            for ref in basis:
                _fields(ref, {"path", "sha256"})
                parent = by_path.get(ref["path"])
                if parent is None or parent["ref"]["sha256"] != ref["sha256"]:
                    raise ValueError("Scope source basis is outside the declared closure")
                expected.add(parent["id"])
            if set(node["parents"]) != expected:
                raise ValueError("Scope receipt derivation parents differ from bound actual basis")
        else:
            reader.read(node["ref"], parse=False)
    context.check()
    selection = select_training_rows(reader.root, corpus_ref["path"], corpus_ref["sha256"],
        heldout_night, fit_cutoff, require_features=tuple(sorted(definitions)),
        exposed_nights=exposed_nights, _read_context=context)
    reader.rescan()
    context.check()
    receipt = dict(schema_version=VERSION, status="G0_TRAINING_DECLARATION_VALIDATED",
        manifest_ref=owned_ref, corpus_ref=dict(corpus_ref), training_selection_sha256=selection["selection_sha256"],
        row_validity_ref=dict(validity_binding["ref"]),
        feature_definition_sha256=definitions_sha, legacy_feature_names_sha256=digest(sorted(definitions)),
        source_authentication="NOT_ATTESTED", scientific_fit_authorized=False, production_authorized=False,
        source_count=len(nodes), training_boundary=boundary.isoformat(),
        consumed_sha256={path: ref["sha256"] for path, ref in reader.refs.items()}, actual_read_bytes=context.bytes_read)
    receipt["receipt_sha256"] = digest(receipt)
    result = {"receipt": receipt, "selection": selection}
    context.check()
    return result
