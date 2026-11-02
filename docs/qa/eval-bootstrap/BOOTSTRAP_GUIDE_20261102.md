# PR #136: Public CPU runner + Private vault bootstrap and cost boundary

Date: 2026-11-02. STATUS: PREPARED_NOT_PROVISIONED / QUALITY_HOLD.
Source: existing Public haji84/habuAI-private, PR #136. Never merge into
main as part of this bootstrap.

## Intended topology

A. Existing haji84/habuAI-private (Public): source development,
signing/scoring contract, immutable model/prompt/evaluator freeze.
B. New haji84/habuAI-eval-runner (Public): GitHub standard Ubuntu CPU
Actions and model-visible **synthetic-only public cases**. Read-only token.
C. New habuAI-eval-vault (Private): independent custodian's encrypted
labels, executed fixed witnesses, signatures. No Actions at all.

The two new repositories were NOT found in the GitHub account at design
time. The connected GitHub action set has no create_repository operation.
DO NOT call this design "created" unless those exact repositories are
verified by GitHub after provisioning.

## Exact one-time GitHub UI preparation

1. Go to https://github.com/new
   - Owner: haji84
   - Repository name: habuAI-eval-runner
   - Visibility: PUBLIC
   - Add README: yes (creates main)
   - Do not select a paid runner or import real Habu owner data
2. Go to https://github.com/new for the vault:
   - Owner: preferably a separate legitimate custodian's account, not
     the development AI's GitHub installation
   - Repository name: habuAI-eval-vault
   - Visibility: PRIVATE
   - Add README: yes
   - Do not grant the current development GitHub App access to this vault
   - Keep private plaintext, decrypting/signing keys off GitHub
   - Settings > Actions > General: disable Actions when available; never
     add a workflow. This gives 0 private-hosted Actions minutes.
3. Provide the created PUBLIC repository to the existing GitHub connector
   (select it for access if the app uses selected repositories).
   Do not connect the private vault to the development assistant.
4. Only after verifying exact names/visibility/owners, copy the nonsecret
   bootstrap source files listed below into each appropriate repo.
   The source PR remains open; do not create new PRs in Habu AI.
5. No new live Qwen evaluation can start until a truly independent
   custodian freezes a new >=40-case synthetic cohort AFTER the model and
   scorer HEAD/digests are fixed. The public Actions workflow is MANUAL,
   requires a precise packet SHA and freeze SHA, and has no auto-push trigger.

## Template paths in the existing PR

Public runner templates under docs/qa/eval-bootstrap/public-runner/
  README.md
  public_packet_guard.py
  run_public_eval.py
  tests/test_public_runner.py
  .github/workflows/evaluate.yml

Private vault templates under docs/qa/eval-bootstrap/private-vault/
  README.md
  custody-policy.json
  .gitignore

All of the above contain NONSECRET rules and publicly allowed synthetic
scaffolding only. They are safe to be inspected in the existing Public PR.
No private labels, encryption keys, tokens, personal GPX or capture site
data may be staged or generated here.

## Required gates before first public runner evaluation

- Model 7B full digest is pinned to the value actually observed on the
  previous 2026-11-02 CPU run:
  dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364.
  Any tag drift stops. Do not silently switch models.
- Current Habu AI review source HEAD, prompt, scorer, executor and all
  dependencies must be frozen BEFORE a separate custodian creates cases.
  The bootstrapped runner has a new prompt contract; prior revealed
  benchmark scores are not directly comparable to its new prompt.
- The custodian must confirm real independent access, separate local
  encryption/HMAC keys and authenticated confidentiality before writing
  any private labels. A private repo controlled by the development
  connector is insufficient alone.
- At least 40 NEW synthetic cases: >=20 verified actual defects,
  >=20 verified clean, Python/JS >=8 each, representative failure
  patterns, predetermined critical bug strata. No reuse of revealed v1.
- Custodian publishes only a signed PUBLIC packet. A public runner can
  verify its structure and SHA but cannot verify its secret HMAC
  without the independent custodian's key; this verification happens
  only at independent scoring.
- The first run outputs a PUBLIC, recoverable response ledger in Actions
  logs. Model output and quoted source are untrusted. Persist the first
  run ID and answer SHA before custodian reveals any labels.
- Only an independent evaluator may execute allowlisted fixed
  synthetic witnesses, adjudicate the model's **actual** assertions
  with concrete inputs/outcomes and score after response freeze.
  HMAC integrity is NOT independent-person identity proof.

## Hard cost and security limits

- Private vault has no Actions workflows and consumes no Private Actions
  execution minutes; GitHub private repository storage quotas still apply.
- Public runner uses only standard GitHub-hosted ubuntu-24.04
  (4 CPU, 16 GB) which GitHub documents as free for public repositories.
  No larger/paid/self-hosted runner, external model API, PAT, cloud GPU,
  secrets, cache of private labels or artifact upload.
- Manual workflow only, bounded job; public log contains PUBLIC synthetic
  prompts and model answers. Nothing automatic is triggered by pushes.
- The developer connector may have access to PUBLIC runner, but MUST
  NOT have access to the private case pack or its keys.
- No production Qwen model replacement, public deployment, new Habu AI PR,
  main merge or permission/billing changes occur automatically.

## Exact acceptance

Model formal targets remain independent semantic Precision >= 95%,
Recall >= 80%, normal-case raw false alert <= 5%, zero missed designated
critical defects, six-case calibration PASS, full CI and truly distinct
security/semantic review. No mock, v1 development reuse, or public template
is official proof. Until all gates pass, QUALITY_HOLD / UNSEALED_HOLD.
