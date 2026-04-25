# Artifact Flow And Traceability

## Principles

- Signals, clusters, opportunities, decisions, and kill reasons are first-class artifacts.
- Original signal IDs must be preserved.
- Duplicates are marked, not deleted.
- AI-shaped artifacts carry prompt/model/input metadata when applicable.
- Deterministic stages must not pretend to be LLM-generated.

## Flow

```text
raw signal inputs
→ Signal artifacts
→ dedup metadata on signals
→ canonical signal set for recurrence-sensitive analysis
→ signal understanding records
→ semantic clusters
→ contradiction reports / merge candidates
→ opportunity cards
→ opportunity gate decisions
```

## Traceability Requirements

- Every duplicate points to a canonical signal.
- Every cluster links to real signal IDs and canonical signal IDs.
- Every contradiction and merge candidate links back to source IDs.
- Every opportunity evidence claim links to source signal IDs and cluster ID.
- Every gate decision preserves opportunity ID, linked signal IDs, and linked cluster ID.

