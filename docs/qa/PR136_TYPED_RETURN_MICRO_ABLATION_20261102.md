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
