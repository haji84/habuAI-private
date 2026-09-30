# Task6a residual raw-log failure repair

Commit: `957e8eb` (`fix: retain failed raw capture evidence for eligibility`). Only `src/evidence_audit.py` and `tests/test_evidence_audit.py` committed. No remote writes, raw/ORIGINAL changes, dependency changes, workflow changes, or subagents.

Read repository AGENTS.md, bounded Task6a plan, original seven-finding review, and task-6a-rereview.md. Working HEAD when inspected was `1b8562ef6091a086d8e667ac2fa89c824e457f9c`; owned paths were initially clean.

## Change

Failed raw-log reconciliation now retains the failed source, hash, JSON selector and reason in existing `capture_audit.rejected`. Existing rejected-evidence guards therefore block negative eligibility and full-domain completeness conservatively across scope. No quantity, location, canonical identity or label is invented. Aggregate `raw_log_counts` FAIL remains intact; independently qualified CSV positives remain in observation units and the outcome ledger. Valid raw count reconciliation remains unchanged.

The broad rejection scope is intentional: a failed raw source does not establish reliable count/location or complete source reconciliation. This uses the parent's permitted conservative fail-closed eligibility decision without adding schema/parser features.

## Red/green evidence

Initial attempted command `python -m pytest -q tests/test_evidence_audit.py -k 'failed_raw_capture or valid_qualified_raw_capture'` could not run: installed Python has no pytest. No dependency was installed. Switched to repository unittest-compatible tests.

RED, before production change:

```sh
PYTHONPATH=src:tests python -m unittest test_evidence_audit.EvidenceAuditTests.test_failed_raw_capture_cannot_establish_negative_or_complete_ledger test_evidence_audit.EvidenceAuditTests.test_valid_qualified_raw_capture_reconciliation_preserves_eligibility
```

Ran 2 tests; 4 failing subtests, each `AssertionError: 0 is not None`. Both null individual count and contradictory summary reproduced the bug with both an empty qualified CSV and a separate qualified positive CSV. Valid raw reconciliation passed.

GREEN, after production change: same command ran 2 tests, OK. Regressions additionally assert UNKNOWN, no zero labels, NOT_ESTABLISHED, no complete scopes, retained qualified positive, exact failure selector/hash, aggregate FAIL, and builder refusal `UPSTREAM_AUDIT_FAILED`.

Focused regression command:

```sh
PYTHONPATH=src:tests python -m unittest test_evidence_audit test_learning_snapshot
```

46 tests passed (0.614s). Includes existing qualified header-only empty logs, mixed capture/noncapture logs, valid counts, and builder guards. `git diff --check` passed. Commit contains exactly the two owned files. Tracked working-tree status was clean after commit.

Full repository CI and independent review remain parent-owned per assignment; no whole-suite claim is made here. This repair establishes synthetic contract behavior, not historical source completeness or scientific validation.
