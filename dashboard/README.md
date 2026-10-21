# Habu Capture dashboard: private-by-default

This dashboard is a read-only view of the personal Habu capture count.

- Baseline 2026-04 through operational night 2026-10-20: 238 *provisional* personal captures from two previous spreadsheets. The historic baseline is frozen until source-by-source reconciliation is completed.
- After cutoff: `data/raw/habu_logs/<year>/*.json` in `habu-night-log-v2` format with `source="user Habu log"` and `type="capture"`, or audited `data/processed/individuals/<year>/*.csv` with `capture_owner=self|owner`. A raw count must match an overlapping processed count.
- `07:00 Asia/Tokyo` determines the operational night. A single event may capture more than one individual.
- Sightings, roadkills, other captors, Himehabu and unknowns are not added. Duplicate ambiguous events raise an error; a failed build must not silently replace the last good aggregate.
- Coordinates and detailed field locations are excluded from the exported dashboard JSON. This does **not** automatically authorize publication.
- The baseline has an unresolved 2026-09-28 mismatch: 5 recorded captures in the historical snapshot versus 6 individual records in GitHub raw/processed. No automatic revision is permitted until the source is reconciled.

## Execution

```sh
python -m unittest discover -s tests -p test_capture_dashboard.py -v
python scripts/build_capture_dashboard.py
```

The `Habu capture dashboard build` GitHub Action runs on approved pushes to main and PRs, and uploads the updated offline HTML + aggregate JSON as a **private Actions artifact**. It does not expose a public website or bypass PR governance. After downloaded together, opening `dashboard/index.html` loads the neighboring `data/capture_summary.json` when same-origin loading is allowed; otherwise the snapshot included in the HTML is shown with a clear snapshot indicator.

A permanently accessible iPhone URL requires a separately approved authentication and hosting arrangement. Never add a GitHub personal access token to browser source, commit raw files publicly, or enable unauthenticated Pages automatically.
