# Dev Ledger Project State

## Current Roadmap

- Active roadmap: `docs/roadmaps/OOS_roadmap_v2_2_8_weeks_checklist.md`
- Inactive/archive roadmap files: older roadmap drafts and `docs/roadmaps/OOS_roadmap_v2_2_ai_meaning_layer_checklist_final.md`

## Current Progress

- Current item: `6.1` — Deterministic anti-pattern checks
- Completed: `10 / 16`
- Remaining: `6 / 16`
- Latest completed roadmap item: `5.2` — Ideation mode comparison with weighted metrics
- Next planned roadmap item: `6.1` — Deterministic anti-pattern checks

## Branch And Commit Strategy

- Work locally in small mini-epic packages.
- Commit locally after each green, accepted mini-epic.
- GitHub push / PR can be batched at a phase boundary when the local history is coherent.
- Do not push partial or unvalidated roadmap work.

## Workflow Notes

- Roadmap status changes only after required validation passes.
- Provider boundaries, validation, metadata, and fallback behavior come before live LLM/API calls.
- Heuristic ideation remains baseline/fallback/control until LLM primary ideation work is implemented.
- Support B added autonomous Codex workflow operations docs and local validation/status scripts without changing Roadmap v2.2 counts.
- Roadmap 5.2 added ideation mode comparison with gates, weighted scoring, genericness penalty, and mode recommendations.
