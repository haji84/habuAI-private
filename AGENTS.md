# Habu AI repository rules

1. Preserve every raw file byte-for-byte. Never overwrite or delete `data/raw/` without explicit owner approval.
2. Store new attachments in `incoming/` first. Record SHA-256, byte size, source, received time, and duplicate status before promotion.
3. Never fabricate elevation, roads, biological observations, captures, or GPX trajectories.
4. Unknown is not Negative. Negative requires observed search or passage in the matching 100m × 10-minute unit.
5. The operational-night boundary is 07:00 Asia/Tokyo.
6. Walk-forward features and training data must be available strictly before the evaluated night and prediction cutoff.
7. Freeze model specs and predictions with SHA-256 before label reveal.
8. Keep official public data and auxiliary data separate. OpenStreetMap is auxiliary.
9. Do not change historical M0–M3 definitions to advantage later models.
10. Use branches, tests, evidence, and Pull Requests. Do not push unreviewed data directly to main.
11. Never commit passwords, tokens, cookies, private keys, or account recovery information.

