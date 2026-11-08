# PR #136: approved Qwen2.5-Coder 7B CPU-only comparison

Status: OWNER APPROVED ISOLATED RESEARCH, NOT MODEL ACTIVATION OR QUALITY APPROVAL.
Date: 2026-11-02. Existing PR #136, branch feature/dashboard-owner-effort-20261026 only.

## Owner Human Gate and immutable boundaries

Owner approved exactly this bounded trial: synthetic data only, no additional billing,
no new PR, no main merge, no production model switch, no public release, no
permissions/authentication changes. No owner GPS/GPX, actual capture coordinates,
personally identifiable raw logs, secrets, credentials, or private snapshots enter
model prompts or GitHub Actions artifacts.

AGENTS.md and docs/work/CODEX_PR136_REVIEW_QUALITY_COMPLETION_20261102.md remain
authoritative. Frozen 40-case source tools/dashboard_ai_review/holdout_v1.py:
Git blob daac52dfed89cb946e736aed49ed109a56307ffa; bytes SHA-256
6a679c26f775970a2d55e53e8d3870c6c9cbd8320c530b77725de83af7e8fc8a.
Do not modify labels, examples, oracle witnesses, scoring thresholds, or old results.

## Isolated compute and model identity

- Standard public-repository GitHub-hosted ubuntu-24.04, 4 CPU/16 GiB class;
  public standard hosted-runner usage is documented as free:
  https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
- Ollama 0.40.11 installer is downloaded from the existing approved GitHub release
  and checked against SHA-256
  25f64b810b947145095956533e1bdf56eacea2673c55a7e586be4515fc882c9f.
- qwen2.5-coder:7b is downloaded for localhost Ollama inference only.
  Published manifest:
  https://registry.ollama.ai/v2/library/qwen2.5-coder/manifests/7b
  Model-layer SHA-256 60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463,
  exactly 4,683,074,048 bytes. Check actual model blob and model digest
  (official tag digest prefix dae161e27b0e) before inference.
- Single standard runner, no GPU, no third-party model API, no remote inference,
  no artifacts or caches, read-only contents permission, no id-token grants.
  Dedicated localhost-only Ollama process, local ephemeral model directory.
  The research job is time-bounded, and the fixed cases are not stored as
  reusable newly sealed data.

The addition of this comparison workflow triggers one experiment when its
workflow file is changed by the existing PR synchronize event. Other branch
changes do not retrigger the costly model trial. The job is limited to PR #136
in the exact same repository and branch. Its successful code/test stage cannot
authorize a release.

## Same evaluation contract as historical 1.5B

The existing 1.5B code (review.py), unchanged six smoke (quality.py) and
40-case scorer (measure_holdout.py) are immutable for this trial; the comparison
driver pins all three Git blob SHAs. It calls review.ask_model(model=7B)
but does not change the prompt, JSON format, grounding, parser, fixtures,
labels, thresholds or scoring. No hand-built "expected finding" is fed to 7B.

**Historical comparison anchor (revealed development data only):**
- 1.5B exact HEAD 4d34554d566e1b7f13cceabf40e2f52b2fe83341,
  six-case real Qwen run:
  https://github.com/haji84/habuAI-private/actions/runs/41394311696
  Source-anchored defect detection 0/2, clean-case raw false alarms 4/4;
  quality HOLD.
- 1.5B fixed 40-case real Qwen:
  https://github.com/haji84/habuAI-private/actions/runs/41394311614
  Completed 40/40, raw alerts 40, false-alert clean cases 20/20,
  location-anchored findings 7, provisional bug return-line cases 3/20,
  33 citation rejects; semantic precision/recall were NOT proven.
- 1.5B model digest:
  d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668.

The 7B run records the 7B's actual full model digest, exact PR HEAD,
source/corpus SHAs, per-case hashed answer receipts, bounded synthetic claim
text, 6-case and 40-case raw/grounded/rejected metrics, complete/missing counts,
model call failures, elapsed time and run ID URL. Case results are not silently
filtered to make a better score.

## Mandatory decision

The previously revealed 6+40 examples are **development diagnostics**, not a
true unseen holdout and not independent model approval. Code citation is
location only, not a verified behavioral defect; proxy precision/recall are
not semantic precision/recall. A larger model is not presumed more accurate.
If Qwen 7B fails, crashes, times out, emits unverified claims, or reports
false positives, preserve all evidence and maintain QUALITY_HOLD.

If 7B improves these known-case metrics, the next stage would STILL require
a separately generated, sealed, genuinely unseen >=40 synthetic examples
(>=20 proven buggy, >=20 proven correct), independently verified requirements,
fresh predictions frozen before label reveal, separate implementer/reviewer,
and formal exact-HEAD tests. No model promotion without new Human Gate.
The comparison workflow always fails its final release hold explicitly, even
when all diagnostic requests complete: a passing research test must never be
mistaken for product qualification.
