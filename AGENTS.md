# Habu AI repository rules

1. Preserve every raw file byte-for-byte. Never overwrite or delete `data/raw/` without explicit owner approval.
2. Store new attachments in `incoming/` first. Record SHA-256, byte size, source, received time, and duplicate status before promotion.
3. Never fabricate elevation, roads, biological observations, captures, or GPX trajectories.
4. Unknown is not Negative. For supervised noncapture observations, GPX passage or slow travel alone is insufficient: require independently corroborated active Habu search in that time/road scope AND source-bound complete owner capture-outcome recording for that scope. Noncapture does not prove Habu absence. Preserve existing coded fail-closed restrictions.
5. The operational-night boundary is 07:00 Asia/Tokyo.
6. Walk-forward features and training data must be available strictly before the evaluated night and prediction cutoff.
7. Freeze model specs and predictions with SHA-256 before label reveal.
8. Keep official public data and auxiliary data separate. OpenStreetMap is auxiliary.
9. Do not change historical M0–M3 definitions to advantage later models.
10. Use branches, tests, evidence, and Pull Requests. Do not push unreviewed data directly to main.
11. Never commit passwords, tokens, cookies, private keys, or account recovery information.
12. A user request equivalent to 「今日の予想」「今夜の予想」「予想出して」「今日どう？」 is an OFFICIAL PREDICTION REQUEST. Do not substitute a conversational/manual forecast. Run the canonical Habu AI prediction issuance path and use its registered model, feature/universe snapshot, GIS/terrain/road inputs, weather/environment inputs, recent activity/search-pressure evidence, route logic, lineage, cutoff, and integrity evidence. If any required executor or input is unavailable or not validated, explicitly return PROVISIONAL_NOT_FREEZABLE with the missing/blocking components. Never present or Freeze a hand-built narrative estimate as P0.

## Codex parallel handoff (2026-10-25)

For multi-model high-accuracy development and ongoing source-evidence certification, read `docs/work/CODEX_PARALLEL_MASTER_20261025.md` first, then `CODEX_LANES_20261025.md`, `CODEX_MODELS_20261025.md`, `CODEX_ACCEPTANCE_20261025.md`, `CODEX_STATE_20261025.json` and `CODEX_COPY_PASTE_20261025.md`. Master Goal remains `haji84/AI-` Issue #1642. The handoff docs cannot grant new billing, public-release or production Champion authority. Codex coordinator owns shared state and integrates disjoint worker branches after exact-head CI and independent review; never call documentation an already-running autonomous job.
