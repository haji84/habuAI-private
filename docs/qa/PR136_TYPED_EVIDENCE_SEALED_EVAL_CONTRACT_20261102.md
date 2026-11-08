# PR #136: typed behavior claim and independently sealed evaluation contract

Status: IMPLEMENTATION RESEARCH / NOT A QUALITY QUALIFICATION / NO RELEASE AUTHORITY
Repository: haji84/habuAI-private
Branch: feature/dashboard-owner-effort-20261026
Date: 2026-11-02 (Asia/Tokyo)

## 1. Scope and invariants

This change is confined to the Qwen2.5-Coder 1.5B CPU code-review research tooling. The public repository's raw captures, tracks, GPS, GPX, locations, source histories, production predictions, original frozen 40 cases and labels, and acceptance thresholds are not modified. No external model API, CodeRabbit/Copilot request, paid service, deployment, new PR or main merge is authorized.

The benchmark v1 file `tools/dashboard_ai_review/holdout_v1.py` must continue to have Git blob `daac52dfed89cb946e736aed49ed109a56307ffa`. It has already been inspected by development, so it is diagnostic only and must NOT be called independent blind evaluation, irrespective of a later run's score.

## 2. Trust separation

Qwen is a **candidate generator**, not an execution oracle. An exact line quote establishes **location only**. For synthetic-only structured diagnostic calls, the model must explicitly return case_id, source_sha256, path, line, code_quote, problem, impact, and JSON-encoded input, actual and required values. The bridge must never synthesize missing model assertions or silently transform malformed outputs into an empty safe answer.

The validator checks the exact model claims against `behavioral_evidence.verify_frozen_synthetic_claim`, which executes only the immutable, pre-approved fixed synthetic source and fixed witness argument. It never executes model-generated source, shell commands, network requests, private data, or the model's chosen alternate input. Nonmatching inputs remain `UNTESTED_MODEL_INPUT`.

Even when the structured input/result pair matches the fixed independently specified witness, the free-form causal explanation remains `NARRATIVE_NOT_AUTOMATICALLY_VERIFIED`. Hashing a synthetic execution receipt proves byte integrity, NOT reviewer identity, trust in general PR code or full correctness. Do not publish a confirmed bug or authorize release from this bridge.

The new optional `review.ask_model(..., evidence_case=...)` mode is used by a separate, fixed four-case, **revealed** diagnostic probe. Normal production review, six-case calibration and the already-fixed 40-case input/label/threshold contract must retain their default behavior.

## 3. Developer quality gates

1. Exactly pin the PR HEAD, program, prompt, SHA of synthetic source and actual Qwen model digest. Store model reply SHA, raw/parsed/verified counts, explicit failures, and evidence digests.
2. Separate **model parsing** from **code location verification**, **trusted fixed-input execution**, **claim agreement**, **causal narrative review**, **independent review** and **publication authority**.
3. Reject duplicate JSON keys, NaN/Infinity, bool/int equivalence, altered source/case, forged evidence flags, missing or added fields, invalid/partial model replies, missing witness execution, and unexpected identities.
4. Measure both false alarms and recall: a model flagging everything and a verifier suppressing everything both fail the final target.
5. A model-free unit test PASS cannot qualify Qwen. A model run that returns `QUALITY_HOLD` must remain an actual unsuccessful quality gate.

## 4. Truly unseen evaluation must occur AFTER freeze

Before any independent case creation or label reveal, a reviewer separate from the implementation owner must freeze and record:

- latest immutable HEAD and complete reviewer/prompt/scorer/witness-runner code SHA-256;
- model digest and runtime/runner version;
- independent case-generation/validation policy and scope;
- exact population/strata and acceptance thresholds;
- authorized storage and review evidence boundaries, with no personal source data.

Then a distinct evaluation custodian, outside the candidate implementation and model prompt, creates at least **40 wholly new synthetic cases** (at least 20 independently reproduced buggy variants and 20 verified correct variants). Include both Python and JavaScript, boundary conditions, file persistence failures, identity/counting and non-disclosure of synthetic location-like keys. Do not reuse code, outputs, names, families as literal memorized items, labels or private fixture values from previously disclosed v1. Preserve the case source SHA and independently observed witness receipt. The model sees only the relevant synthetic specification and code, never the label, counterpart or witness answer.

The evaluator should store immutable pre-reveal model replies and a complete missing/inconclusive/abstained ledger. Reveal labels **only after** all predictions are frozen and compute genuine reproduced Precision >= 95%, Recall >= 80%, false-alert-case rate <= 5%, and zero missed designated critical cases. The reported denominator must include missed known bugs and false alarms, never redefine missing predictions as correct negatives. A first failed result stays retained forever even if a revised independent v2 is later generated.

A GitHub-visible source file, prior development logs, a model that has already inspected the cases, or a same-author secretly curated label file is **not** a sealed evaluation. If an independent custodian and verifiable separate scope are unavailable, report `UNSEALED_HOLD`, not `QUALITY_QUALIFIED`.

## 5. Independent review and final completion

Review the exact current HEAD with a genuinely distinct model or reviewer/execution identity, verify behavior and security, reproduce material findings, repair on **existing PR #136**, re-run exact-HEAD model tests and all CI, and preserve historical failed runs. Independent review is not fulfilled by the same implementation author declaring approval, and `COMMENTED` is not an `APPROVED` review. Owner Human Gates remain required for model-policy changes, new private storage, permission/auth changes, fees, main merge and deployment.

Until an independently sealed new benchmark and separate review actually pass, retain `QUALITY_HOLD`. A code-only CI green is not a product quality certificate.
