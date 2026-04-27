# Dev Ledger Project State

## Current Roadmap

- Roadmap v2.2 status: complete.
- Active roadmap: `docs/roadmaps/OOS_roadmap_v2_3_source_intelligence_checklist.md`
- Inactive/archive roadmap files: older roadmap drafts, `docs/roadmaps/OOS_roadmap_v2_2_ai_meaning_layer_checklist_final.md`, and Roadmap v2.2 completion documents.

## Current Progress

- Roadmap v2.3 planning created: yes
- Current item: `4.2` - GitHub Issues collector
- Completed: `6 / 16`
- Remaining: `10 / 16`
- Latest completed roadmap item: Roadmap v2.3 `4.1` - Hacker News Algolia collector
- Next planned roadmap item: Roadmap v2.3 `4.2` - GitHub Issues collector

## Branch And Commit Strategy

- Work locally in small mini-epic packages.
- Current branch: `feat/4-1-hn-algolia-collector`
- Commit locally after each green, accepted mini-epic.
- GitHub push / PR can be batched at a phase boundary when the local history is coherent.
- Do not push partial or unvalidated roadmap work.

## Workflow Notes

- Roadmap status changes only after required validation passes.
- Provider boundaries, validation, metadata, and fallback behavior come before live LLM/API calls.
- Heuristic ideation remains baseline/fallback/control until LLM primary ideation work is implemented.
- Support B added autonomous Codex workflow operations docs and local validation/status scripts without changing Roadmap v2.2 counts.
- Roadmap 5.2 added ideation mode comparison with gates, weighted scoring, genericness penalty, and mode recommendations.
- Roadmap 6.1 added deterministic anti-pattern checks with findings, severity, penalties, and genericness reuse.
- Roadmap 6.2 added isolated council critique roles, top-idea selection, suspiciously clean protection, and founder manual-review safeguards.
- Roadmap 8.1 added deterministic full AI meaning loop verification across provider-boundary stages with traceability, founder review, and AI quality rating checks.
- Roadmap 8.2 completed the local Roadmap v2.2 checkpoint with validation evidence recorded; push, merge, and tag creation remain deferred until explicitly requested.
- Roadmap v2.3 planning created the Source Intelligence Layer checklist and v0.3 source access policy. Implementation starts at item 1.1; no source intelligence product features are implemented by this planning checkpoint.
- Roadmap v2.3 item 1.1 finalized the Source Intelligence Layer v0.3 access, privacy, topic, feedback, evidence classification, cleaner, scoring, and traceability policies without implementing product features.
- Roadmap v2.3 item 1.2 standardized validation run reports, required file-based evidence, and added a Windows-native validation report helper without changing product behavior.
- Roadmap v2.3 item 2.1 added the canonical RawEvidence model, deterministic normalized content hashing, role/context-only author validation, and artifact-store roundtrip support under `artifacts/raw_evidence/` without collectors, network calls, or live LLM/API calls.
- Roadmap v2.3 item 2.2 added source registry and topic profile contracts, default Phase B/source-review policies, inactive future topic stubs, and a deterministic bounded query planner without collectors, network calls, or live LLM/API calls.
- Roadmap v2.3 item 3.1 added deterministic collection scheduling limits, scheduled collection queue items, a collector interface, and an offline FixtureCollector without real collectors, network calls, or live LLM/API calls.
- Roadmap v2.3 item 4.1 added the Hacker News Algolia collector adapter with fixture-first RawEvidence mapping, default-disabled live networking, HN item URL traceability, and author/context privacy without internet/API calls during validation or live LLM/API calls.
- Reddit source policy amendment reclassified Reddit as a Phase C controlled internal research source that is enabled by default after collector implementation, while Query Planner still skips Reddit until `collector_available=true`; roadmap item, completed, and remaining counters were not advanced by this policy-only amendment.
