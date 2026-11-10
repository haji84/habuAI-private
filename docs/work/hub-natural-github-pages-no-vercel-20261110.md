# HUB NATURAL: No Vercel, aggregate-only deployment plan (2026-11-10)

Owner correction: **Vercel must not be used** for Habu AI / HUB NATURAL. The previous Vercel authorization request is withdrawn and its link should be ignored. The two Vercel-specific scripts/tests were removed from PR #160, and Vercel-specific CI commands were removed.

## Approved architectural boundaries

1. Public GitHub: code and deliberate public aggregate summaries. No plaintext GPX, individual capture positions, detailed observation times, logs, or decryption keys.
2. Private encrypted vault: source GPX, original logs and detailed research-model inputs. Verify archive SHA, authenticated decryption, source hashes and provenance in the private runtime.
3. Public static dashboard: the allowlisted aggregate-only export (2026 total 270, November 8, monthly totals, research-only model sample sizes). Publishing aggregates means they are public plaintext, not encrypted in the browser.
4. Formal scientific G0 100m x ±10 minute training and automatic production promotion remain separate gates; do not infer them from the public dashboard.

## GitHub Pages candidate (not activated)

A GitHub-only workflow is staged at `.github/workflows/hub-natural-public-aggregate-pages.yml`: it runs on `main` pushes changing the release payload or workflow, and supports manual `workflow_dispatch` on `main` for re-deployment. It never runs a deployment from a feature PR. It publishes exactly `index.html` and `data/public_summary.json` from `dashboard/public-release/`, verifying the JSON and the embedded HTML summary match. GitHub Pages must first be enabled in repository Settings → Pages → Source: GitHub Actions; `GITHUB_TOKEN` cannot enable Pages by itself. The workflow cannot run from this Draft PR.

Before first release, confirm that only aggregate fields are intentionally public and the GitHub Pages deployment owner/environment is configured. Run the existing dashboard CI for the exact PR HEAD, review the privacy diff, merge after authorization, manually run the Pages workflow, and verify the real URL and mobile display. Any failed check keeps deployment blocked.

GitHub Pages does not support custom server response headers the way a dedicated host can; the generated HTML includes a restrictive CSP meta tag, and the page performs no network I/O. Security headers or access-restricted private pages are not claimed. Do not deploy the legacy private dashboard or the entire repository.

## Status

- Release package prepared and validated locally; the Pages workflow is eligible to fire after main merge. Its initial deployment may be blocked until one-time repository Pages settings are applied. No hosted site activation is asserted.
- No dependency on Vercel or Cloudflare.
- PR #160 is a development PR; hosting change and production release must not be described as completed until real deployment and verification.
