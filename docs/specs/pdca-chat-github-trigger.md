# PDCA Chat-to-GitHub Trigger

When the owner asks the PDCA chat to run a specific operational night, the chat may create one GitHub issue in this repository with the exact title form:

`[HABU PDCA] YYYY-MM-DD`

The issue is an execution envelope, not a data source.

The `habu-pdca-command` workflow:
1. accepts only issues opened by the repository owner;
2. resolves the requested operational night from the title;
3. runs `scripts/run_pdca.py`;
4. uploads the generated report directory as a workflow artifact;
5. if the result is PASS or PARTIAL, commits only generated PDCA reports to a new branch;
6. comments the command issue with PASS/PARTIAL/BLOCKED/FAIL, the report branch, and the concrete reason;
7. the ChatGPT GitHub connector opens the report PR from that branch because repository Actions tokens may be prohibited from creating pull requests.

A BLOCKED run must not invent missing predictions or evidence.

The chat should use this trigger only for post-exploration PDCA. Prediction issuance remains separate.


## 2026-10-23 Actions PR permission compatibility

GitHub Actions may deny creation/approval of pull requests with HTTP 403 even when a workflow requests `pull-requests: write`. A run is **not** considered scientifically PASS merely because the report exists.

- The Actions entrypoint uses read-only PR lookup. For a report branch with an existing PR, the issue comment links that PR. Otherwise it links the exact report branch; this is a **PR handoff**, not a created or merged PR.
- Workflow permissions use `pull-requests: read`; no `POST /pulls` from the Actions executor. Report branch publication, receipt hashes and issue comment remain protected by existing commands and checks.
- The ChatGPT GitHub connector inspects the report branch/diff, opens the PR, checks CI and reviews, and merges only if safe. Do not assume a `HANDLED` command means a PR was created, a report was integrated, P0 scored, or any Master Goal gate passed.
- Pending report branches must be distinguished from merged evidence. The existing report receipt is immutable; do not fabricate P0 or modify a scientific run's source/input identity to recover from this transport failure.
