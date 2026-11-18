# Habu AI owner-private research handoff v1 (2026-11-18 JST)

Parent: [HABU Master Goal #1642](https://github.com/haji84/AI-/issues/1642)
Proposed in existing Draft PR #163; this is *not* approved production deployment.

## Why
The existing `scripts/private_pdca_intake.py` already archives real owner LOG and GPX privately with hashes and an immutable receipt, but its result remains `pdca=NOT_RUN`. Lack of frozen ORIGINAL P0 or 100m×10min qualified Negatives must not suppress meaningful, independent owner-data research.

This slice **reuses** that intake. It adds `scripts/private_owner_research.py` to immediately re-read verified archived bytes, bind an immutable private diagnostic research report, and return only limited counts/status to the caller.

## Single-entry local/private command
For an authorized private runtime (not public Actions):
```sh
python scripts/private_owner_research.py --repo-root /path/to/habuAI-private --private-root /owner-only/private-dir --log /original/owner-log.txt --gpx /original/owner-track.gpx
```

Existing receipt replay, without re-upload:
```sh
python scripts/private_owner_research.py --repo-root /path/to/habuAI-private --private-root /owner-only/private-dir --receipt-id <64-character-receipt-id>
```

Do not place the private root inside, adjacent *under*, or within the public repository checkout. This step requires a trusted private filesystem with owner-only permissions.

## Evidence and research semantics
- Real log/GPX bytes are archived using the existing byte-exact private intake. Original `raw/` and `receipts/` files are never modified by research.
- On replay the receipt ID, source binding, expected archive path, declared file size, byte SHA-256 and parsed log diagnostic are verified. Corrupted/replaced source fails rather than silently claiming success.
- One canonical receipt yields one immutable research artifact `research/<receipt_id>.json` outside GitHub. Reprocessing unchanged sources is idempotent; altered prior research contents are rejected.
- Habu **capture event count** and event-time-of-night are extracted; roadkill and Himehabu are not owner Habu captures. Generic multi-individual counts are **not inferred**. `verified_individual_count=null` until evidence supports it.
- Private event records contain precise event timestamps and stable source-derived event keys **only within private storage**, not stdout/GitHub. No GPX positions are included in the report.
- GPS-only does **not** mean zero catches. Missing night, missing search-role or incomplete outcomes do not create Negatives. Unknown remains Unknown.
- No historical ORIGINAL P0 is generated; no official model accuracy, fitted candidate or Champion authorization is asserted. The report explicitly records `P0_score=NOT_EVALUATED`, `research_candidate_fit=NOT_RUN` and `production_champion_activated=false`.

## Validation
`tests/test_private_owner_research.py` covers a one-command intake+research, cross-midnight grouping, Himehabu and roadkill separation, repeat idempotence, archive alteration rejection, receipt tampering, GPS-only Unknown, and public checkout isolation. All test data are synthetic.

## Next actual-science integration
1. Use these private receipt-bound event records as a source of positive observations or night-level outcome evidence in the **existing** NightCount/EventClock and research training code. A separate, deduplicated capture-individual ledger is required before individual-count fitting.
2. Bind a scoped, owner-confirmed search session and complete outcome record to the matching GPX segment. Do not infer Negative from GPS alone.
3. Run old/new models on identical chronological eligible folds and save actual Brier/count/ranking deltas with uncertainty. This first receipt bridge alone does not calculate those metrics.
4. Re-test on untouched future nights and only then consider Champion promotion after full formal gates.

**No personal GPS files or real logs are committed by this slice.** Public CI may test the code with synthetic fixtures only.
