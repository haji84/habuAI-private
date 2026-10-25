# Real multi-night GPX inventory: source visibility is not training eligibility

The repository already contains August 2026 **13 byte-preserved GPX tracks**, a September 28 byte-exact 24-part archive (22,990 points), and the processed 9/28 Habu event/individual CSVs. `scripts/inventory_real_gpx_sources.py` examines all `data/raw/gpx/*.gpx` in actual CI, computes SHA-256, point count, 07:00 JST operational night coverage and clock-order quality, and inventories recovery archive manifests.

**The inventory deliberately does not label an unpaired GPX night "zero captures."** The current majority of the August tracks have no verified corresponding raw Habu capture/reaction event log and unique owner individual ledger committed on main. Their GPS track existence is evidence of positional samples but not a certificate of complete search effort, observer detection, or outcome absence. Such passages are UNKNOWN for supervised negative training. Any GPX clock conflict is flagged rather than silently used.

The September 28 night is separately reconciled against original owner log, event CSV, individual IDs, frozen monthly capture count and GPS proximity in [PR #70](https://github.com/haji84/habuAI-private/pull/70), with aggregate count corrected in [PR #71](https://github.com/haji84/habuAI-private/pull/71). It has five event observations containing six personally captured Habu, not five individuals. This corrected daily quantity does not automatically certify every sampled 100m×10min road cell as searched/non-capture, nor does it give all historical nights a complete outcome ledger.

`python scripts/inventory_real_gpx_sources.py --output artifacts/reconciliation/gpx-nights.json`

The real CI run uploads this diagnostic inventory to a 30-day workflow artifact; an artifact is **not** a permanent canonical raw archive. To become a full `model_learning.json` training input, each participating night must have:
- verified GPX byte identity and quality, proper operational boundary, road map matching and actual observation effort;
- complete owner-capture event ledger with one-to-many individual IDs, plus separate sighting/roadkill, and source availability;
- full outcome recording or clearly stated incomplete coverage; unmatched passage is UNKNOWN until Negative eligibility is proven;
- independent ex-ante road ForecastUniverse and historical weather/terrain snapshots available by each training prediction cutoff;
- untouched temporal confirmation nights and a valid full-denominator 1km Top10 + 100m±10min evaluation, without fabricated positives.

A few weeks of August GPX without matching full capture logs cannot be silently promoted to a genuine trained production model. Issue #64 remains BLOCKED until full sources are recovered and cross-checked.
