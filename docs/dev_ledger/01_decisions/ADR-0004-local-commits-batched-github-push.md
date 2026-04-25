# ADR-0004: Local Commits With Batched GitHub Push

## Status

Accepted

## Context

Roadmap v2.2 is being developed locally in small validated packages.

## Decision

Create local commits after each green mini-epic. GitHub push / PR may be batched at a phase boundary instead of after every mini-epic.

## Consequences

- Local history should remain clean and mini-epic scoped.
- Do not push or open PRs for unvalidated or partial work.
- A phase boundary can gather several local commits into one reviewable PR.

