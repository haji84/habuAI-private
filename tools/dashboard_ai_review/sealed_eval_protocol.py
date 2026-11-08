"""Fail-closed custody/commit/reveal protocol for synthetic code-review benchmarks.

No model invocation, arbitrary code execution, network, storage, approval, or
production release. A separate custodian must hold REAL private signing keys.
Toy keys in unit tests prove protocol mechanics only. HMAC checks message
integrity under a supplied key, never that its holder is truly independent.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re

import grounding

SCHEMA = "habu-reviewer-sealed-gate-v1"
THRESHOLDS = {
    "precision_min": 0.95, "recall_min": 0.80,
    "clean_false_alert_max": 0.05, "critical_misses_max": 0,
}
HEX16 = re.compile(r"^[0-9a-f]{16}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PATH = re.compile(r"^fixture/sealed_([0-9a-f]{16})\.(py|js)$")
CASE_FIELDS = frozenset({
    "case_id", "language", "path", "source", "patch", "source_sha256",
    "label", "critical", "test_input", "observed", "required", "runner_id",
    "witness_sha256",
})
RESPONSE_FIELDS = frozenset({
    "case_id", "source_sha256", "findings", "response_sha256",
})
FINDING_FIELDS = frozenset({"line", "code_quote", "problem", "impact"})
ADJ_FIELDS = frozenset({
    "case_id", "ordinal", "response_sha256", "witness_sha256", "verdict",
})
FREEZE_FIELDS = frozenset({
    "stage", "schema", "implementation_owner", "git_head", "model_name",
    "model_digest", "reviewer_sha256", "prompt_sha256", "scorer_sha256",
    "executor_sha256", "thresholds",
})


def _duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("NONFINITE_JSON_VALUE")


def parse_json(raw: str):
    if not isinstance(raw, str) or not raw or len(raw) > 250000:
        raise ValueError("INVALID_JSON_ENVELOPE")
    return json.loads(raw, object_pairs_hook=_duplicate_keys,
                      parse_constant=_nonfinite)


def canonical(value) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("NONCANONICAL_JSON") from exc


def sha(value) -> str:
    raw = value if isinstance(value, str) else canonical(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _key(key: bytes):
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("MISSING_INDEPENDENT_SIGNING_KEY")


def signature(payload: dict, key: bytes) -> str:
    _key(key)
    return hmac.new(key, canonical(payload).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def sign(payload: dict, key: bytes) -> dict:
    """Demo helper: real custody keys must never appear in repo or logs."""
    if not isinstance(payload, dict):
        raise ValueError("INVALID_SIGNED_PAYLOAD")
    # Deep-copy to prevent mutable aliases changing after signing.
    normalized = parse_json(canonical(payload))
    return {"payload": normalized, "signature": signature(normalized, key)}


def _verify(packet: dict, key: bytes) -> dict:
    if (not isinstance(packet, dict)
            or set(packet) != {"payload", "signature"}
            or not isinstance(packet["payload"], dict)
            or not isinstance(packet["signature"], str)
            or not HEX64.fullmatch(packet["signature"])
            or not hmac.compare_digest(packet["signature"],
                                       signature(packet["payload"], key))):
        raise ValueError("BAD_SIGNATURE")
    return packet["payload"]


def _thresholds_exact(value) -> bool:
    return (type(value) is dict
            and set(value) == set(THRESHOLDS)
            and all(type(value[k]) is type(expected) and value[k] == expected
                    for k, expected in THRESHOLDS.items()))


def _exact_new_file_patch(path: str, source: str) -> str:
    """For synthetic fixtures only; don't permit an unrelated presented diff."""
    if not source.endswith("\n") or "\r" in source or "\x00" in source:
        raise ValueError("SYNTHETIC_SOURCE_CHANGED")
    lines = source.splitlines()
    return (
        f"diff --git a/{path} b/{path}\n"
        f"new file mode 100644\n--- /dev/null\n+++ b/{path}\n"
        f"@@ -0,0 +1,{len(lines)} @@\n"
        + "".join("+" + line + "\n" for line in lines)
    )


def _freeze(payload: dict):
    if (not isinstance(payload, dict) or set(payload) != FREEZE_FIELDS
            or payload["stage"] != "freeze" or payload["schema"] != SCHEMA
            or not isinstance(payload["implementation_owner"], str)
            or not payload["implementation_owner"].strip()
            or not isinstance(payload["model_name"], str)
            or not payload["model_name"].strip()
            or not isinstance(payload["git_head"], str)
            or not HEX40.fullmatch(payload["git_head"])
            or any(not isinstance(payload[field], str)
                   or not HEX64.fullmatch(payload[field])
                   for field in ("model_digest", "reviewer_sha256",
                                 "prompt_sha256", "scorer_sha256",
                                 "executor_sha256"))
            or not _thresholds_exact(payload["thresholds"])):
        raise ValueError("INVALID_FREEZE_OR_CHANGED_THRESHOLDS")


def _typed_equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _typed_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def _validate_cases(cases: list):
    if not isinstance(cases, list) or not 40 <= len(cases) <= 256:
        raise ValueError("INSUFFICIENT_OR_UNBOUNDED_COHORT")
    ids = set()
    positive = negative = 0
    languages = {"python": 0, "js": 0}
    critical = 0
    for case in cases:
        if not isinstance(case, dict) or set(case) != CASE_FIELDS:
            raise ValueError("INVALID_CASE_SCHEMA")
        cid = case["case_id"]
        if not isinstance(cid, str) or not HEX16.fullmatch(cid) or cid in ids:
            raise ValueError("DUPLICATE_OR_INVALID_CASE")
        ids.add(cid)
        path = case["path"]
        if not isinstance(path, str):
            raise ValueError("INVALID_SYNTHETIC_PATH")
        match = PATH.fullmatch(path)
        if (not match or match.group(1) != cid
                or (case["language"] != "python" if match.group(2) == "py"
                    else case["language"] != "js")):
            raise ValueError("INVALID_SYNTHETIC_PATH")
        if (not isinstance(case["source"], str)
                or not 0 < len(case["source"]) <= 2800
                or not isinstance(case["patch"], str)
                or not 0 < len(case["patch"]) <= 3500
                or not case["patch"].startswith(
                    f"diff --git a/{path} b/{path}\n")
                or not isinstance(case["source_sha256"], str)
                or case["source_sha256"] != sha(case["source"])
                or case["patch"] != _exact_new_file_patch(path, case["source"])):
            raise ValueError("SYNTHETIC_SOURCE_CHANGED")
        if case["label"] not in ("BUG", "CLEAN"):
            raise ValueError("INVALID_LABEL")
        if type(case["critical"]) is not bool:
            raise ValueError("INVALID_CRITICAL_FLAG")
        if (not isinstance(case["test_input"], list)
                or not isinstance(case["runner_id"], str)
                or not case["runner_id"]
                or not isinstance(case["witness_sha256"], str)
                or not HEX64.fullmatch(case["witness_sha256"])):
            raise ValueError("INVALID_EXECUTION_WITNESS")
        actual_digest = sha({
            "case_id": cid, "source_sha256": case["source_sha256"],
            "input": case["test_input"], "observed": case["observed"],
            "required": case["required"], "runner_id": case["runner_id"],
        })
        if actual_digest != case["witness_sha256"]:
            raise ValueError("WITNESS_DIGEST_MISMATCH")
        if case["label"] == "BUG":
            positive += 1
            if _typed_equal(case["observed"], case["required"]):
                raise ValueError("BUG_WITHOUT_EXECUTION_DISCREPANCY")
            critical += bool(case["critical"])
        else:
            negative += 1
            if case["critical"]:
                raise ValueError("INVALID_CRITICAL_FLAG_ON_CLEAN")
            if not _typed_equal(case["observed"], case["required"]):
                raise ValueError("CLEAN_HAS_EXECUTION_DISCREPANCY")
        languages[case["language"]] += 1
    if (positive < 20 or negative < 20
            or any(num < 8 for num in languages.values())
            or critical < 1):
        raise ValueError("UNBALANCED_OR_UNVERIFIED_COHORT")


def _public(cases):
    return [{"case_id": c["case_id"], "path": c["path"],
             "patch": c["patch"], "source_sha256": c["source_sha256"]}
            for c in cases]


def seal_cohort(freeze: dict, cases: list, custodian_id: str,
                custodian_key: bytes) -> dict:
    """Only a separate evaluator should call with *private* unlogged labels."""
    fp = freeze.get("payload") if isinstance(freeze, dict) else None
    _freeze(fp)
    if (not isinstance(custodian_id, str) or not custodian_id
            or custodian_id == fp["implementation_owner"]):
        raise ValueError("ROLE_SEPARATION")
    _validate_cases(cases)
    return sign({
        "stage": "cohort", "schema": SCHEMA,
        "freeze_sha256": sha(fp), "custodian_id": custodian_id,
        "cases": cases,
    }, custodian_key)


def seal_public_cases(cohort: dict, custodian_key: bytes) -> dict:
    """The ONLY custodian output allowed to reach a prediction collector.

    The private cohort stays in the custodian's separately controlled process.
    A public signed envelope binds the case prompts to the PRIVATE cohort's
    SHA without exposing labels, witness inputs, expected values or outcomes.
    """
    cp = cohort.get("payload") if isinstance(cohort, dict) else None
    if not isinstance(cp, dict) or cp.get("stage") != "cohort":
        raise ValueError("INVALID_PRIVATE_COHORT")
    _validate_cases(cp["cases"])
    return sign({
        "stage": "public", "schema": SCHEMA,
        "freeze_sha256": cp["freeze_sha256"],
        "cohort_sha256": sha(cp), "custodian_id": cp["custodian_id"],
        "public_cases": _public(cp["cases"]),
    }, custodian_key)


def _public_packet(public_envelope: dict) -> dict:
    payload = (public_envelope.get("payload")
               if isinstance(public_envelope, dict) else None)
    if (not isinstance(payload, dict) or set(payload) != {
            "stage", "schema", "freeze_sha256", "cohort_sha256",
            "custodian_id", "public_cases"}
            or payload["stage"] != "public" or payload["schema"] != SCHEMA
            or not isinstance(payload["custodian_id"], str)
            or not payload["custodian_id"]
            or any(not isinstance(payload[x], str)
                   or not HEX64.fullmatch(payload[x])
                   for x in ("freeze_sha256", "cohort_sha256"))):
        raise ValueError("PUBLIC_CASES_REQUIRED")
    cases = payload["public_cases"]
    if not isinstance(cases, list) or not 40 <= len(cases) <= 256:
        raise ValueError("PUBLIC_CASES_REQUIRED")
    seen = set()
    for c in cases:
        if (not isinstance(c, dict)
                or set(c) != {"case_id", "path", "patch", "source_sha256"}):
            raise ValueError("PUBLIC_CASES_REQUIRED")
        cid = c["case_id"]
        path = c["path"]
        if (not isinstance(cid, str) or not HEX16.fullmatch(cid)
                or cid in seen or not isinstance(path, str)
                or not isinstance(c["source_sha256"], str)
                or not HEX64.fullmatch(c["source_sha256"])):
            raise ValueError("PUBLIC_CASES_REQUIRED")
        match = PATH.fullmatch(path)
        if (not match or match.group(1) != cid
                or not isinstance(c["patch"], str)
                or not 0 < len(c["patch"]) <= 3500
                or not c["patch"].startswith(
                    f"diff --git a/{path} b/{path}\n")):
            raise ValueError("PUBLIC_CASES_REQUIRED")
        seen.add(cid)
    return payload


def public_projection(public_envelope: dict) -> list[dict]:
    """This has NO access to a secret cohort, labels, or witness results."""
    payload = _public_packet(public_envelope)
    return parse_json(canonical(payload["public_cases"]))


def _validate_responses(responses, cases):
    if not isinstance(responses, list) or len(responses) != len(cases):
        raise ValueError("PREDICTION_POPULATION")
    expected = {case["case_id"]: case for case in cases}
    seen = set()
    for row in responses:
        if not isinstance(row, dict) or set(row) != RESPONSE_FIELDS:
            raise ValueError("MODEL_RESPONSE_SCHEMA")
        cid = row["case_id"]
        if cid not in expected or cid in seen:
            raise ValueError("PREDICTION_POPULATION")
        seen.add(cid)
        if (row["source_sha256"] != expected[cid]["source_sha256"]
                or not isinstance(row["findings"], list)
                or len(row["findings"]) > 3):
            raise ValueError("MODEL_RESPONSE_SCHEMA")
        for claim in row["findings"]:
            if not isinstance(claim, dict) or set(claim) != FINDING_FIELDS:
                raise ValueError("MODEL_RESPONSE_SCHEMA")
            if (type(claim["line"]) is not int
                    or not 0 < claim["line"] <= 100000
                    or any(not isinstance(claim[key], str)
                           or not claim[key].strip()
                           for key in ("code_quote", "problem", "impact"))):
                raise ValueError("MODEL_RESPONSE_SCHEMA")
        if (not isinstance(row["response_sha256"], str)
                or row["response_sha256"] != sha({
                    k: v for k, v in row.items() if k != "response_sha256"
                })):
            raise ValueError("MODEL_RESPONSE_HASH")
    if seen != set(expected):
        raise ValueError("PREDICTION_POPULATION")


def seal_predictions(freeze: dict, public_envelope: dict,
                     model_visible: list[dict], responses: list,
                     collector_id: str, key: bytes) -> dict:
    """A collector sees ONLY a public, label-free packet and model replies.

    HMAC authenticity of the custodian's public packet is checked by the
    independent scorer after prediction Freeze. The collector has no access
    to the custodian key or the private cohort, by design.
    """
    fp = freeze.get("payload") if isinstance(freeze, dict) else None
    _freeze(fp)
    pub = _public_packet(public_envelope)
    if pub["freeze_sha256"] != sha(fp):
        raise ValueError("FREEZE_BINDING")
    if model_visible != public_projection(public_envelope):
        raise ValueError("MODEL_PROMPT_OR_LABEL_LEAK")
    if (not isinstance(collector_id, str) or not collector_id
            or collector_id in (fp["implementation_owner"],
                                pub["custodian_id"])):
        raise ValueError("ROLE_SEPARATION")
    _validate_responses(responses, pub["public_cases"])
    return sign({
        "stage": "predictions", "schema": SCHEMA,
        "freeze_sha256": sha(fp),
        "cohort_sha256": pub["cohort_sha256"],
        "public_sha256": sha(pub),
        "collector_id": collector_id, "responses": responses,
    }, key)


def seal_adjudications(predictions: dict, adjudications: list,
                       reviewer_id: str, key: bytes) -> dict:
    pp = predictions.get("payload") if isinstance(predictions, dict) else None
    if (not isinstance(pp, dict) or pp.get("stage") != "predictions"
            or not isinstance(reviewer_id, str) or not reviewer_id
            or reviewer_id == pp.get("collector_id")
            or not isinstance(adjudications, list)):
        raise ValueError("ROLE_SEPARATION")
    return sign({
        "stage": "adjudications", "schema": SCHEMA,
        "predictions_sha256": sha(pp), "reviewer_id": reviewer_id,
        "adjudications": adjudications,
    }, key)


def score(freeze: dict, cohort: dict, public_envelope: dict,
          predictions: dict, adjudications: dict,
          *, owner_key: bytes, custodian_key: bytes,
          collector_key: bytes, reviewer_key: bytes) -> dict:
    """Check signed stages and measure BOTH errors. Never self-approve quality.

    HMAC and role-name checks are NOT proof of independent people or models;
    source generation, executor isolation, chronology, semantic verification
    and signer identity must be separately audited outside this public code.
    """
    keys = (owner_key, custodian_key, collector_key, reviewer_key)
    if any(type(key) is not bytes for key in keys) or len(set(keys)) != 4:
        raise ValueError("ROLE_KEYS_NOT_INDEPENDENT")
    fp = _verify(freeze, owner_key)
    cp = _verify(cohort, custodian_key)
    pub = _verify(public_envelope, custodian_key)
    pp = _verify(predictions, collector_key)
    rp = _verify(adjudications, reviewer_key)
    _freeze(fp)
    if (cp.get("stage") != "cohort" or cp.get("schema") != SCHEMA
            or cp.get("freeze_sha256") != sha(fp)):
        raise ValueError("FREEZE_BINDING")
    if cp.get("custodian_id") == fp["implementation_owner"]:
        raise ValueError("ROLE_SEPARATION")
    cases = cp.get("cases")
    _validate_cases(cases)
    _public_packet(public_envelope)
    if (pub["cohort_sha256"] != sha(cp)
            or pub["freeze_sha256"] != sha(fp)
            or pub["custodian_id"] != cp.get("custodian_id")
            or pub["public_cases"] != _public(cases)):
        raise ValueError("COHORT_BINDING")
    if (pp.get("stage") != "predictions" or pp.get("schema") != SCHEMA
            or pp.get("freeze_sha256") != sha(fp)):
        raise ValueError("FREEZE_BINDING")
    if pp.get("cohort_sha256") != sha(cp):
        raise ValueError("COHORT_BINDING")
    if pp.get("public_sha256") != sha(pub):
        raise ValueError("PUBLIC_CASE_BINDING")
    if pp.get("collector_id") in (
            fp["implementation_owner"], cp["custodian_id"]):
        raise ValueError("ROLE_SEPARATION")
    responses = pp.get("responses")
    _validate_responses(responses, cases)
    if (rp.get("stage") != "adjudications" or rp.get("schema") != SCHEMA
            or rp.get("predictions_sha256") != sha(pp)):
        raise ValueError("PREDICTIONS_BINDING")
    if rp.get("reviewer_id") in (
            fp["implementation_owner"], cp["custodian_id"],
            pp["collector_id"]):
        raise ValueError("ROLE_SEPARATION")
    rows = rp.get("adjudications")
    if not isinstance(rows, list):
        raise ValueError("ADJUDICATION_POPULATION")
    case_by_id = {case["case_id"]: case for case in cases}
    response_by_id = {row["case_id"]: row for row in responses}
    verdicts = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != ADJ_FIELDS:
            raise ValueError("ADJUDICATION_POPULATION")
        cid, ordinal = row["case_id"], row["ordinal"]
        if (cid not in response_by_id or type(ordinal) is not int
                or not 1 <= ordinal <= len(response_by_id[cid]["findings"])
                or (cid, ordinal) in verdicts
                or row["response_sha256"] != response_by_id[cid]["response_sha256"]):
            raise ValueError("ADJUDICATION_POPULATION")
        if row["witness_sha256"] != case_by_id[cid]["witness_sha256"]:
            raise ValueError("WITNESS_RECEIPT_MISMATCH")
        if row["verdict"] not in ("REPRODUCED", "REFUTED", "INCONCLUSIVE"):
            raise ValueError("UNKNOWN_ADJUDICATION")
        if case_by_id[cid]["label"] == "CLEAN" and row["verdict"] == "REPRODUCED":
            raise ValueError("CLEAN_CASE_CANNOT_HAVE_REPRODUCED_BUG")
        if row["verdict"] == "REPRODUCED":
            # Even a separately signed behavior witness does not turn an
            # invented line or a comment-only quote into a valid finding.
            case = case_by_id[cid]
            finding = response_by_id[cid]["findings"][ordinal - 1]
            anchored, _ = grounding.ground_candidates(
                [finding], case["source"],
                grounding.added_source_lines(case["patch"]))
            if len(anchored) != 1:
                raise ValueError("UNANCHORED_MODEL_CLAIM")
        verdicts[(cid, ordinal)] = row["verdict"]
    required_keys = {
        (row["case_id"], ordinal)
        for row in responses
        for ordinal in range(1, len(row["findings"]) + 1)
    }
    if set(verdicts) != required_keys:
        raise ValueError("ADJUDICATION_POPULATION")

    issued = sum(len(row["findings"]) for row in responses)
    confirmed = sum(value == "REPRODUCED" for value in verdicts.values())
    hit = {cid for (cid, ordinal), value in verdicts.items()
           if value == "REPRODUCED"}
    defects = [case for case in cases if case["label"] == "BUG"]
    clean = [case for case in cases if case["label"] == "CLEAN"]
    raw_alerts_clean = sum(
        bool(response_by_id[case["case_id"]]["findings"]) for case in clean)
    critical_misses = sum(
        case["critical"] and case["case_id"] not in hit for case in defects)
    precision = confirmed / issued if issued else 0.0
    recall = len(hit) / len(defects)
    false_alert_rate = raw_alerts_clean / len(clean)
    screening = (precision >= THRESHOLDS["precision_min"]
                 and recall >= THRESHOLDS["recall_min"]
                 and false_alert_rate <= THRESHOLDS["clean_false_alert_max"]
                 and critical_misses == THRESHOLDS["critical_misses_max"])
    return {
        "schema": SCHEMA, "case_count": len(cases),
        "known_bug_cases": len(defects), "known_clean_cases": len(clean),
        "issued_findings": issued, "confirmed_true_findings": confirmed,
        "verified_bug_cases_hit": len(hit),
        "missed_bug_cases": len(defects) - len(hit),
        "clean_raw_alert_cases": raw_alerts_clean,
        "critical_misses": critical_misses,
        "precision": precision, "recall": recall,
        "clean_false_alert_rate": false_alert_rate,
        "metric_screen_pass": screening,
        "freeze_sha256": sha(fp), "cohort_sha256": sha(cp),
        "public_sha256": sha(pub),
        "prediction_sha256": sha(pp), "adjudication_sha256": sha(rp),
        "claim_explanations_independently_verified": False,
        "custodian_identity_cryptographically_independent": False,
        "independent_safety_review_completed": False,
        "quality_qualified": False, "release_authorized": False,
        "decision": "INDEPENDENT_REVIEW_BLOCKED" if screening else "QUALITY_HOLD",
    }
