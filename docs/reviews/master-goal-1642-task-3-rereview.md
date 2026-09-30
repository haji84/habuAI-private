# Task 3 fix-round 1 independent re-review

Scope: `1277d91..856f8bb`, limited to `src/model_evaluation.py`, `tests/test_model_evaluation.py`, `schemas/model-learning.json`; updated remediation report; prior five Important findings and regressions introduced by their fixes. No implementation edits, subagents or full-suite rerun.

**Spec compliance: approved for bounded Task 3. Code quality: approved for this fix.** All five prior Important findings are ADDRESSED. No remaining/new Critical or Important issue identified in this scoped re-review. Approval does not establish scientific validation, complete Stage1 denominator coverage, production trust or whole-Master completion.

| Prior finding | Disposition | Reviewed evidence |
|---|---|---|
| Provenance roles/coverage bypass source availability | ADDRESSED | Source roles required and recognized; observed rows require label-role coverage; every feature has explicit source binding constrained to declared feature-role sources. Source availability cannot exceed declared field availability, and predictor availability remains strictly before cutoff. Missing contract blocks; contradictions fail. |
| Canonical event reused across nights | ADDRESSED | Event uniqueness is global across learning rows rather than keyed by night. Cross-night train/test duplicate regression returns FAIL without folds. |
| Genuine unknown rows need invented observation metadata | ADDRESSED | Unobserved rows accept null label availability and UNKNOWN quality without label-role provenance; remain in predictions but outside fitting, associations and scored-label denominators. Observed-row requirements remain enforced. |
| Malformed root escapes four-stage result contract | ADDRESSED | Root/nested object and collection shapes are checked explicitly; `[]`, null and numeric roots return four FAIL stages with concrete invalid-evidence reasons. |
| Restricted recall can imply full Stage1 denominator/gate | ADDRESSED | Recall/count fields explicitly identify restricted/included-universe metrics, denominator coverage is NOT_ESTABLISHED, and all Stage1 gate outcomes are NOT_EVALUATED. Complete outcome coverage remains a specific blocker. |

Independent verification: eight selected tests passed (six newly added regression methods, immutable replay/reproducibility, and confirmation exclusion). Additional focused probes confirmed that binding a feature to a label-role source, omitting its bound path from row provenance, and a future label source each return FAIL with zero folds. A genuine unknown row retained all six diagnostic folds and reduced association observed-unit count from 36 to 35. The reported 32-model / 136-total suite is implementer/parent evidence, not a full suite repeated by this reviewer.

The updated schema reflects required provenance roles and feature mappings, nullable unobserved label availability, and observed-only observation requirements. Existing numeric tests retain their expected arithmetic under the explicitly renamed restricted-metric fields. The fixture now has a separate legitimate early feature source rather than relabeling observation provenance.

Task 4 / later builders must consume the revised metric and provenance contract. In particular, restricted recall cannot establish a full Stage1 pass; later complete-outcome coverage must include outside-universe captures within the approved evaluation domain/time scope as denominator misses. Feature-aware research/ablation, confirmation consumption locking, formal temporal targets, requested output executors and trusted production persistence remain explicit later-slice requirements.
