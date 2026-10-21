# Habu DB 07:00 JST capture-view correction

## Correction evidence
- Applies the owner's **07:00 JST operational-night boundary** to the older capture-view projection.
- Observation/event datetime is unchanged. **00:00:00–06:59:59 JST belongs to the preceding operational night**, 07:00:00 onwards belongs to that calendar day.
- A second independent local validation detected 101 pre-07:00 rows in the **older capture DB display/view** with unadjusted calendar dates. This set includes non-capture records; 101 is **not** a number of Habu captured.
- The principal unified event CSV (3,853 rows) had **zero** parseable timestamps with an incorrect operational night. The 1,117 additional September/October event rows likewise had zero.
- The corrected view and revised Excel were built without changing existing source records, immutable ORIGINAL predictions or any historic raw ZIP.
- Post-midnight attribution confirmed for `2026-09-29 00:00/00:08/00:19` to night `2026-09-28` and `2026-10-15 00:20` to night `2026-10-14`. The **07:00 threshold is exclusive to previous night**.
- Existing additional owner captures: **2026-09: 50**, **2026-10 through 10/20: 17**, total 67, unchanged. GPS alignment unchanged.
- 24 older legacy capture-display rows with unparseable/missing dates or times are not silently fixed. Their original evidence remains available for manual review.

## Corrected workbook restore
A new immutable version of the workbook is stored as XZ/base64 text chunks under:

`data/raw/attachment_archives/integrated_db_workbook_07h/7f0dd533fcf9bc27f2cb797fb63a7cf416973a1c7ce2cb9d90a219d4483824de/`

- Workbook source SHA-256: `7f0dd533fcf9bc27f2cb797fb63a7cf416973a1c7ce2cb9d90a219d4483824de`
- Source byte count: **813,283**
- Count: **9** encoded parts plus manifest.
- Reconstruct with existing `scripts/text_safe_byte_archive.py restore` and validate restored SHA-256.
- The previous 1,868,956-byte ZIP with SHA-256 `67075a32bba202f62a51604d757660f36d4d8115e0b5b250cbb85961ec7a737a` is preserved as older forensic source with a now-superseded display-sheet projection, NOT deleted or overwritten.

## Quality gates
- Python 7 test cases for cutoff, duplicate prevention, simultaneous captures and reaction classification **PASS in the local sandbox**.
- This does **not** imply GitHub CI pass; PR #43 CI is currently red and this PR should remain Draft until reviewed.
- Original Habu capture count based on legacy ambiguous `capture_or_sighting` rows is still unresolved. This is a data view fix, not a model upgrade.
