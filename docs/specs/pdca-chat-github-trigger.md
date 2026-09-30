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
