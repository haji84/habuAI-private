# PR #136: registered typed-return prompt micro-ablation

Status: DESIGN EXPERIMENT ONLY. No model replacement, no score threshold changes, no publication authority.
Date: 2026-11-02.
Scope: existing PR #136, Qwen2.5-Coder 1.5B, localhost Ollama, known synthetic development cases only.

## Observation that motivates this change

The four fixed, **already revealed** development examples run at HEAD `3548690c1e73bc0f7dadc07245c10bef0f009020` in [GitHub Actions 41392682549](https://github.com/haji84/habuAI-private/actions/runs/41392682549) produced:
- Model replies 4/4. Each produced one raw alert, including both known-correct examples.
- Structured bug reproduction: 0, even though the source line was sometimes correctly quoted.
- Python `check(kind)` submissions used arrays of objects for the argument and used those arrays again as alleged actual/required outputs. The trusted fixed witness therefore rejected the proposals as `UNTESTED_MODEL_INPUT`.
- A JS numeric-boundary bug used `input_json=[300]`, but incorrectly claimed `required_json=[300,true]` instead of a return-value boolean; this was `CLAIMED_REQUIREMENT_CONTRADICTED`.
- A correct JS boundary check was flagged despite a verified correct witness, producing `NO_DEFECT_ON_TRUSTED_WITNESS`.

None of these statuses proves a real PR defect, and the four development examples are not unseen.

## One bounded change, before observing a rerun

In **synthetic evidence mode only**, clarify the distinction between the JSON *argument list* and the JSON *function return values*. Provide one unrelated toy demonstration: required `check(n)=n+2`, bad code returns `n+1`, input `[4]`, actual `5`, required `6`. A correct implementation must produce no finding. Do not include target-case labels, expected values or witness inputs in model prompts.

No change to the fixed v1 cohort, Python/JS samples, scorer, baseline holdout prompt, model weights/tag, acceptance metrics, error accounting, general PR reviewer prompt or source-anchoring rules.

## Registered measures and stop condition

Run the new contract tests, then the existing six-case real-model smoke, four-case structured development diagnostic and original 40-case Qwen evaluation with exact source HEAD, model digest and original corpus blob. Preserve every old run. Report exactly:
- model replies and malformed/missing cases,
- model-issued raw alerts on known-correct cases,
- claimed inputs/outputs and trusted witness verdict categories,
- strictly reproduced structured counterexamples,
- code quote rejects,
- full CI failures versus model quality failures.

A better *format* is not improved precision or recall. This single experiment cannot qualify the model. If the new result is still weak, maintain `QUALITY_HOLD` and describe a scoped, owner-approved alternative model research gate instead of changing thresholds or repeatedly fitting the known 40.


## Observed outcome and safe rollback decision

Actual model [Actions run 41393834020](https://github.com/haji84/habuAI-private/actions/runs/41393834020) executed the four already-revealed synthetic development cases at exact HEAD `e8a32b19194ed78052b9fda2bdec1b09f77653f5`, `qwen2.5-coder:1.5b`, digest `d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668`.

- All four model requests returned a response with one raw finding (including both known-clean cases).
- Both Python samples wrote non-JSON `True`/`False` in fields that must contain JSON literals. These were `INVALID_MODEL_RESPONSE`, not correct abstentions.
- Both JS samples supplied `input_json=[4]` instead of the approved fixed witness input `[300]`, and were rejected as `UNTESTED_MODEL_INPUT`. One clean JS response copied the toy `actual_json=5`, `required_json=6` example despite unrelated source logic.
- Reproduced structured behavioral claims: **0**. The diagnostic summary counted **2/4** parse-accepted completions and `INCOMPLETE_HOLD`. Since invalid model replies are excluded from its completed-case false-alert counter, that counter (1) must not be used to imply only one clean raw alert: the raw replies visibly flagged **both** clean examples.
- Same run's six-case real model smoke: grounded positives **0/2**, raw false alarms in clean cases **4/4**, `QUALITY_HOLD`. Model-free contracts were **134/134 PASS**.

The generic toy example did not fix the semantic problem and contaminated responses. **Decision: REJECT THIS PROMPT CHANGE**. Restore the previous evidence-only prompt in a new non-force commit, preserve these failed results, and keep the independent synthetic witness gate. Do not alter the protected fixed 40 examples, labels, thresholds or recorded old runs. No claim of unseen precision/recall improvement or independent approval.
