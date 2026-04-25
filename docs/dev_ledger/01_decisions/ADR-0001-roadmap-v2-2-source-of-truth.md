# ADR-0001: Roadmap v2.2 Source Of Truth

## Status

Accepted

## Context

Multiple roadmap files exist in the repository, including older drafts and final-looking variants.

## Decision

`docs/roadmaps/OOS_roadmap_v2_2_8_weeks_checklist.md` is the active development source of truth for Roadmap v2.2.

Older roadmap files are inactive/archive references only and must not drive implementation status.

## Consequences

- Roadmap progress updates apply only to the active checklist.
- Acceptance tests should verify the active checklist, not archived files.
- If active and inactive roadmap files disagree, prefer the active checklist unless the user explicitly overrides it.

