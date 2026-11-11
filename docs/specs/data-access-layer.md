# Habu Data Access Layer v1

Chat, Work, and future GORIQ use one read-only canonical interface.

## Invariants
- GitHub canonical data is the source of truth.
- Raw files remain byte-for-byte immutable.
- New material enters through incoming/ and is audited before promotion.
- Operational night boundary is 07:00 Asia/Tokyo.
- Unknown is not Negative.
- as-of reads must not expose observations created after the requested cutoff.
- Predictions and model specs are frozen before label reveal.

## Interface
- canonical_index(): discover canonical datasets.
- night(night_date, cutoff=None): retrieve one operational night.
- as_of(cutoff): retrieve only information available through a cutoff.

The interface is intentionally runtime-neutral so Chat/Work can use it now and GORIQ can replace the caller later without changing the canonical storage contract.
