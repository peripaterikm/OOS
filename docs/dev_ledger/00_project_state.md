# Dev Ledger Project State

## Current Roadmap

- Roadmap v2.2 status: complete.
- Active roadmap: `docs/roadmaps/OOS_roadmap_v2_4_signal_quality_and_ai_layers_checklist.md`
- Inactive/archive roadmap files: older roadmap drafts, `docs/roadmaps/OOS_roadmap_v2_2_ai_meaning_layer_checklist_final.md`, and Roadmap v2.2 completion documents.

## Current Progress

- Roadmap v2.3 planning created: yes
- Current item: `6.2`
- Completed: `14 / 17`
- Remaining: `3 / 17`
- Latest completed roadmap item: Roadmap v2.4 `6.1` - Weak signal aggregation protocol
- Next planned roadmap item: Roadmap v2.4 `6.2` - Cluster synthesis LLM contract

## Branch And Commit Strategy

- Work locally in small mini-epic packages.
- Current branch: `feat/8-x-v2-4-final-validation`
- MVP branch: `feat/source-intelligence-mvp-discovery-loop`
- Commit locally after each green, accepted mini-epic.
- GitHub push / PR deferred until the MVP Source Intelligence slice is working and explicitly requested.
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
- Roadmap v2.3 item 4.2 added the GitHub Issues collector adapter with fixture-first RawEvidence mapping, default-disabled live networking, issue URL traceability, safe metadata preservation, pull request filtering, and author/context privacy without internet/API calls during validation or live LLM/API calls.
- Roadmap v2.3 item 4.3 added Stack Exchange and RSS/regulatory collector adapters with fixture-first RawEvidence mapping, default-disabled live networking, source URL traceability, safe metadata preservation, and author/context privacy without internet/API calls during validation or live LLM/API calls.
- Roadmap v2.3 MVP execution overlay created a local-only branch workflow for reaching the first working Source Intelligence loop before the next GitHub checkpoint.
- Roadmap v2.3 item 5.1 added deterministic RawEvidence cleaning and rule-based evidence classification with HN/GitHub ambiguity defaulting to human review, artifact roundtrip support, and no internet/API or live LLM/API calls during validation.
- Roadmap v2.3 item 5.2 added deterministic CandidateSignal extraction from CleanedEvidence plus EvidenceClassification, rule-based measurement methods for every signal dimension, source traceability, artifact roundtrip support, and no internet/API or live LLM/API calls during validation.
- Roadmap v2.3 item 6.2-lite added an offline weekly discovery CLI that loads local RawEvidence fixtures, runs cleaning, classification, and CandidateSignal extraction, and writes discovery run artifacts plus source-yield-lite counters without internet/API or live LLM/API calls during validation.
- Roadmap v2.3 item 7.1-lite added a founder-facing discovery package JSON and Markdown artifact with deterministic ranking, signal traceability, recommended founder actions, and MVP limitations without automating founder decisions or making internet/API or live LLM/API calls during validation.
- Roadmap v2.3 item 8.1-lite added an adapter-only meaning-loop dry run for Source Intelligence CandidateSignals, writing `meaning_loop_dry_run.json` and `meaning_loop_dry_run.md` with compatibility status, adapted records, and candidate-signal-to-source traceability without invoking live LLM/API calls.
- Source Intelligence MVP+1 live collection mode implemented locally on `feat/source-intelligence-live-collection-mode`, adding explicit `--use-collectors` plus `--allow-live-network` gating, bounded collector routing for implemented Phase B collectors, collector-mode reporting, and mocked validation with no live internet/API calls.
- Full Roadmap v2.3 item 6.1 Source Yield Analytics and item 7.2 Traceability/compliance hardening are still deferred for the MVP slice; item 8.2 completion checkpoint is not yet complete.
- Roadmap v2.4 item 1.1 hardened live Source Intelligence relevance with HTML/entity cleanup, UTF-8 decode hardening, ai_cfo_smb relevance gating, anti-marketing downgrades, non-flat deterministic scoring, finance-specific HN/GitHub query templates, RSS feed URL skips, and mocked validation without live internet/API or live LLM/API calls.
- Roadmap v2.4 item 1.1b follow-up hardened founder-package ranking and deduplication, repaired additional mojibake fragments, downgraded GitHub install/tutorial/generic finance copy, added explicit noise coverage for obvious junk, and preserved roadmap counters at current item 1.2.
- GitHub push / PR remains deferred until the selected 5.x offline review block is complete and the owner explicitly approves.

- Roadmap v2.4 item 1.2 formalized live quality acceptance smoke with a deterministic artifact-only checker, CLI report writer, RSS controlled-skip checks, duplicate/mojibake/install-copy gates, and documented known limitations without live internet/API or live LLM/API calls during validation.
- Roadmap v2.4 item 2.1 added deterministic persona-based Customer Voice Query generation for `ai_cfo_smb`, inactive future-topic stubs, proposed-by-default approval state, a disabled future LLM prompt contract, and a JSON/Markdown CLI preview without live internet/API or live LLM/API calls during validation.
- Roadmap v2.4 item 2.2 added approval-gated Customer Voice QueryPlanner integration with deterministic preview plans, source-fit filtering, Reddit/source-policy gating, and a JSON/Markdown preview CLI without running collectors, internet/API calls, or live LLM/API calls during validation.
- Roadmap v2.4 item 3.1 added deterministic Scoring model v2 with component score breakdowns, embeddings-disabled weights, soft signal-type multipliers, caps/penalties, `CandidateSignal` scoring metadata, and no embeddings, internet/API, or live LLM/API calls during validation.
- Roadmap v2.4 item 3.2 added a semantic relevance provider boundary with disabled-by-default behavior, a deterministic keyword stub for local tests/previews, scoring v2 diagnostics, and no embeddings, external API, internet, or live LLM/API calls during validation.
- Roadmap v2.4 item 4.1 added LLM provider request/response contracts, disabled-by-default provider behavior, deterministic local mock provider, fail-closed budget policies/state, token/cost estimation, and circuit breaker controls without secrets, dependencies, internet/API calls, or live LLM/API calls during validation.
- Roadmap v2.4 item 4.2 added deterministic prompt-safety and PII redaction helpers, fail-closed blocking for secrets/private keys/cards, safe `LLMRequest` builders, and a safety envelope with asymmetric prior and evidence citation requirements without secrets, dependencies, internet/API calls, or live LLM/API calls during validation.
- Roadmap v2.4 item 4.3 added LLM signal review and JTBD extraction contracts, deterministic prompt builders, prompt-safety integration, JSON parsing/validation, and a deterministic mock review flow for tests/local preview only without real LLM providers, secrets, dependencies, internet/API calls, or live LLM/API calls.
- Roadmap v2.4 4.x work is complete locally on `feat/4-x-llm-infrastructure-contracts`; push/PR/merge remains deferred until explicitly approved.
- Roadmap v2.4 item 5.1 added an offline deterministic LLM Signal Review dry-run that reads existing discovery artifacts, builds safe review requests, runs deterministic mock review only, validates structured review/JTBD outputs, and writes JSON/Markdown reports without real provider calls, internet/API calls, or live LLM/API calls.
- Roadmap v2.4 item 5.2 added a deterministic evidence-only PriceSignal extractor, future LLM prompt contract, explicit-price scoring boost, price signal artifacts in discovery runs, and founder discovery package price hints without dependencies, internet/API calls, or live LLM/API calls.
- Roadmap v2.4 item 7.2 upgraded founder discovery packages with deterministic quality sections for time-sensitive opportunities, implied burdens, explicit price signals, optional weak-pattern and kill-archive artifacts, customer voice query yield, advisory offline LLM review outputs, and evidence confidence/risk notes without dependencies, internet/API calls, or live LLM/API calls.
- Roadmap v2.4 item 8.1 recorded fixture and bounded live-smoke validation for HN, GitHub, and mixed HN/GitHub runs through the existing discovery pipeline and founder package, with no live LLM/API calls and live internet/API calls limited to explicit smoke validation only.
- Roadmap v2.4 item 8.2 checkpoint validation passed full unittest discovery and `scripts/oos-validate.ps1`, but final `17 / 17` closure is blocked because root-level `verify.ps1` is absent and Roadmap v2.4 items `6.2` and `7.1` remain unchecked without their expected implementation/report evidence; no release tag was created.
- Roadmap v2.4 gap item 6.1 added deterministic weak signal aggregation, the `WeakPatternCandidate` model, discovery-run `weak_pattern_candidates.json` artifacts, and founder package rendering through existing quality sections without live internet/API calls or live LLM/API calls.
