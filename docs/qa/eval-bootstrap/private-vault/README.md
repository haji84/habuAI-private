# habuAI-eval-vault (PRIVATE, no Actions)

Template for a new PRIVATE GitHub repository managed by an independent evaluation custodian. This is NOT the existing public haji84/habuAI-private repo.

## Purpose

Hold sealed, genuine new synthetic assessment labels and fixed witness evidence. Do not reuse the already-revealed original 40 cases as a claim of unseen quality.

## Security and zero-private-minute policy

- Do NOT create a .github/workflows directory. Disable Actions in Settings > Actions > General if available. The vault does not execute Qwen or a model.
- Keep repository access restricted to the independent case custodian and independent scorer. Do not grant the public runner, development AI, GitHub app or another collaborator access to unrevealed labels.
- A Private repo under the SAME account with the SAME installed development AI is NOT automatically independent. If the development account can access the label files, record CUSTODY_NOT_INDEPENDENT and STOP.
- Encrypt all private case packs with authenticated encryption (e.g. age or AES-256-GCM) before committing them. NEVER store the decryption key or signing key in GitHub, Actions secrets, connected AI apps, issues, commits or logs.
- The Public runner receives ONLY public fields: case_id, path, patch, source_sha256, and nonsecret hash commitments. No labels, fixed witness inputs, actual results, required outputs, critical indicators or paired correct versions.
- No real GPS/GPX, capture locations, personal secrets or original operational logs. Only independently created synthetic code.
- A private GitHub repo without workflows consumes zero GitHub-hosted Actions compute minutes; GitHub storage quota and other possible costs remain subject to the account settings.

## Proper sealed evaluation sequence

1. **Freeze** model name, full model digest, prompt/runner/scorer/executor SHA-256, target repository HEAD and unchanged thresholds BEFORE cases are created.
2. **Private cohort generation**: independent custodian creates >=40 wholly NEW synthetic cases (BUG>=20, CLEAN>=20, Python>=8, JavaScript>=8) and obtains actual fixed witness execution receipts. Code, requirements and sources cannot copy the previously revealed v1 cases.
3. **Private signing**: custodian keeps unencrypted labels only locally, protects signing key separately, and stores authenticated encrypted private case pack in this vault. The public signed envelope has no labels.
4. **Public first response**: public runner processes all >=40 questions from the label-free envelope, with frozen model/prompt. All answers and omissions are fixed to the initial Actions run ID, HEAD and source hashes before labels are revealed.
5. **Independent reveal**: distinct independent reviewer verifies source-specific citations, model-claimed reproductions and original trusted execution receipts, then computes Precision, Recall, raw clean false-alert rate and designated critical misses.

HMAC signatures alone DO NOT prove separate people or actual execution. They only verify message integrity under specific signing keys. Authoritative role isolation requires separate permissions, audit trail, and genuine independent control.

## Only allowed files in the real vault

- README.md and custody-policy.json: nonsecret policies
- .gitignore: forbid accidental raw, secrets or plaintext check-in
- encrypted/<assessment-id>.age: authenticated ciphertext AFTER independent custodian encrypts original pack
- Nonsecret commitments and first-run proof hashes

Do NOT store actual plaintext cases or HMAC/decryption keys. Do NOT enable private runner jobs. Do NOT automatically merge or deploy.

Current implementation contract and model-quality tests stay in the EXISTING public PR #136, tools/dashboard_ai_review/sealed_eval_protocol.py. That existing repo must never receive the secret pack or keys.

## Gate

Until independent custodian identity, separate access control, truly unseen cases, fixed witness execution, first-run prediction freeze and independent semantic review are verified, verdict remains UNSEALED_HOLD / QUALITY_HOLD. This Private repo is NOT a model approval.
