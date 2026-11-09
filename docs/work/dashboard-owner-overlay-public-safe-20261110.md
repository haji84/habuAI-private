# HUB NATURAL owner overlay: public repository boundary

`haji84/habuAI-private` is a public GitHub repository. The owner has authorized continued development there. **Public repository does not mean the contents are encrypted.** Actual GPX/capture coordinates, raw observation logs and plaintext Library JSON are excluded from the public branch unless independently verified as encrypted payloads and explicitly intended for publication.

## Current outcomes (owner-only dataset, not a public data commit)

- Frozen October 30 dashboard snapshot: 262 owner captures.
- November 1/3/5/6/7/9: owner capture counts 2/2/0/2/not-search/2; November sum 8. November 7 is a non-search temperature survey, never a negative search sample.
- On 2026-11-10, the owner explicitly confirmed **270 personally captured Habu in 2026 through the November 9 search night**. The frozen October 30 count (262) plus the November 1–9 captures (8) also equals **270**; the annual aggregate discrepancy is **resolved**. The prior owner statement of 269 is superseded but retained in the historical evidence. This confirms the aggregate only, not every individual record's independent certification or official model eligibility.
- Private working dashboard update and model evidence were saved in protected Library `/ハブAI/Dashboard/Private/` and `/ハブAI/Derived/2026/11/`.
- Research models are updated but official G0 100m x ±10 min fit/promotion remains BLOCKED. GPS presence alone cannot certify negative observations.

## Safe deployment sequence

1. Keep any raw GPS, exact capture locations, animal-level timestamps, private owner overlay and private generated HTML/JSON out of public commit history.
2. The code in `scripts/apply_private_dashboard_overlay.py` is reusable on either a private locally built dashboard or an authenticated deployment. Public anonymous deployment can only consume an intentional sanitized aggregate export; do not publish source data to make it work.
3. A public summary of monthly totals is still **plaintext** in the browser, even if its source GPX is encrypted at rest. If truly encrypted browser data is desired, key management and a separate authenticated decryption flow must be designed and verified before deployment.
4. Run the existing dashboard and new synthetic tests, review PR, and only then integrate into main. The code-only PR does not automatically update the live hosted dashboard.

This document intentionally includes no individual capture positions, GPX payloads, or credentials.
