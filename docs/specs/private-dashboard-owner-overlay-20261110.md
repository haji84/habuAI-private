# HUB NATURAL private dashboard overlay: owner capture totals and research model status

## Purpose

This is an **opt-in, offline/private** connector for the existing HUB NATURAL v2 dashboard. `haji84/habuAI-private` is currently a **public** repository, despite its name. **Never commit the 2026-11 original Habu GPS tracks, exact capture positions, owner's private JSON, or protected dashboard/dist files to GitHub.**

Existing `scripts/build_capture_dashboard.py` builds a frozen historical baseline. It does not read user Library originals automatically. The provided overlay adapter builds on the generated dashboard JSON without modifying the prior capture baseline or the source dashboard code. This patch includes only reusable, location-free code and synthetic tests.

## Local/private use

```sh
python scripts/build_capture_dashboard.py
python scripts/apply_private_dashboard_overlay.py \
  --base dashboard/data/capture_summary.json \
  --overlay /path/to/PRIVATE/owner_nights_overlay.json \
  --output dashboard/dist/data/capture_summary.json
python -m http.server 8080 --directory dashboard/dist
```

**Do not use the private generated output in public GitHub Pages, public Cloudflare Pages, or public Actions artifacts.** Any deployed private site needs independent confirmation that both production and preview URLs enforce owner-only authentication. Do not automatically enable a hosting workflow here.

Alternatively, the existing dashboard has a manual JSON-import control. Import a complete `habu-capture-dashboard-v2` JSON produced by the adapter directly from the protected local file.

## Private overlay contract

`habu-private-dashboard-owner-overlay-v1`:

```json
{
  "schema_version": "habu-private-dashboard-owner-overlay-v1",
  "source": "OWNER_LOG_AND_GPX_PRIVATE_REVIEW",
  "private_only": true,
  "nights": [
    {"night": "2026-12-01", "capture_count": 2, "session_kind": "SEARCH", "gpx_time_place_crosscheck": true},
    {"night": "2026-12-03", "capture_count": 0, "session_kind": "RESEARCH_NON_SEARCH", "gpx_time_place_crosscheck": false}
  ],
  "expected_monthly": {"2026-12": 2},
  "owner_claimed_total": 8,
  "research_models": {"official_100m_10min_status": "BLOCKED"}
}
```

Illustrative only; do not commit actual owner data. `owner_claimed_total` remains a separate reference with an unknown reporting cutoff and is never used to silently rewrite nightly counts. Previously accepted dates may be present only with matching counts and matching search status, otherwise reject. Every extra night needs a verified owner statement. A `RESEARCH_NON_SEARCH` day is excluded from the capture-effort denominator and cannot become a Negative label. GPX proximity is just time/place source corroboration, **not** independent proof of each animal's identity or of fully searched road coverage.

## Model coverage vs production

- Private research samples are **overlapping**, so counts across model families are never added together.
- `owner_claimed_total` and source-derived nightly total may conflict; preserve both and report the difference, never forge an event or date to make them agree.
- Current research models are not the formally authorized G0 model. Source-qualified 100m ±10min learning needs independently confirmed active search coverage, complete capture outcomes and ex-ante weather/terrain evidence. Formal Negative labels must never be generated from GPS pass-through alone.
- Data sources remain in a protected Library or other authenticated owner-only storage. A code-only PR does not deploy a dashboard or connect a private data source.

## Tests

`python -m unittest discover -s tests -p test_private_dashboard_overlay.py -v`

The 9 synthetic tests cover monthly/count consistency, duplicate and frozen baseline checks, survey night exclusions, rejection of coordinates, and prevention of false G0 promotion.