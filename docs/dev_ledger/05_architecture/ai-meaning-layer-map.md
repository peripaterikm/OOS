# AI Meaning Layer Map

## Current Pipeline

```text
evaluation dataset v0
→ pre-clustering dedup / fingerprinting
→ signal understanding + quality scoring
→ semantic clustering of canonical signals
→ contradiction detection + merge candidates
→ opportunity framing with evidence and assumptions
→ deterministic opportunity quality gate
→ next: pattern-guided ideation
```

## Stage Roles

- Evaluation dataset: repeatable smoke-test and calibration fixture.
- Dedup: preserves raw signals while giving downstream stages canonical inputs.
- Signal understanding: extracts structured meaning and quality scores.
- Semantic clustering: groups canonical signals by meaning.
- Contradiction detection: surfaces conflicts and possible merge candidates.
- Opportunity framing: creates evidence-linked opportunity cards with non-obvious angles.
- Opportunity quality gate: deterministic advisory pass/park/reject before ideation.

## Non-Goals So Far

- No live LLM/API calls.
- No UI.
- No database migration.
- No council or ideation changes in phases 1–4 beyond baseline compatibility.

