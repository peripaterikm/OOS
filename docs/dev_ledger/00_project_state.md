# Dev Ledger Project State

## Current Roadmap

- Roadmap v2.5 status: complete (`24 / 24`, tag `v2.5`).
- Active roadmap: `docs/roadmaps/OOS_roadmap_v2_6_real_weekly_loop_operationalization_checklist.md`
- Inactive/archive roadmap files: `docs/roadmaps/OOS_roadmap_v2_5_opportunity_formation_and_founder_learning_checklist.md`, `docs/roadmaps/OOS_roadmap_v2_3_source_intelligence_checklist.md`, older roadmap drafts, and Roadmap v2.2 completion documents.

## Current Progress

- Roadmap v2.6 planning created: yes
- Current item: `1.1` - Weekly run artifact contract
- Roadmap state: `active / planned`
- Completed: `0 / 9`
- Remaining: `9 / 9`
- Latest completed roadmap item: Roadmap v2.5 `8.1` - Roadmap v2.5 final validation
- Next planned roadmap item: Roadmap v2.6 `1.1` - Weekly run artifact contract
- Roadmap v2.5 GitHub state: PR `#40` merged to `main`; tag `v2.5` created and pushed.

## Branch And Commit Strategy

- Work locally in small mini-epic packages.
- Current branch: `planning/v2-6-roadmap`
- MVP branch: `feat/source-intelligence-mvp-discovery-loop`
- Commit locally after each green, accepted mini-epic.
- Roadmap v2.5 implementation branch was merged through PR `#40` and released with tag `v2.5`.
- Roadmap v2.6 planning is on this branch; do not push, merge, tag, or release until explicitly approved.
- Do not push partial or unvalidated follow-up work.

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
- Roadmap v2.4 item 8.2 final checkpoint rerun passed full unittest discovery, `scripts/oos-validate.ps1`, and `git diff --check`; root-level `verify.ps1` is absent and recorded as controlled unavailable; Roadmap v2.4 is complete at `17 / 17`; no push, PR, merge, tag, release, live internet/API call, or live LLM/API call was performed.
- Roadmap v2.4 gap item 6.1 added deterministic weak signal aggregation, the `WeakPatternCandidate` model, discovery-run `weak_pattern_candidates.json` artifacts, and founder package rendering through existing quality sections without live internet/API calls or live LLM/API calls.
- Roadmap v2.4 gap item 6.2 added the `ClusterSynthesis` model, deterministic cluster synthesis stub, future-only prompt contract, and local-preview `cluster_synthesis` budget-role validation without live internet/API calls or live LLM/API calls.
- Roadmap v2.4 gap item 7.1 added deterministic Kill Archive feedback into scoring, `kill_pattern_flag`/`kill_pattern_penalty`, discovery-run `kill_archive_warnings.json` artifacts, and founder package warning details without auto-killing, live internet/API calls, or live LLM/API calls.
- First real open-source signal run v1 executed a bounded HN + GitHub Issues pass with existing v2.4 capabilities, generated founder package artifacts under `artifacts/discovery_runs/first_real_open_source_signal_run_v1/`, and recorded protocol/run-report docs without live LLM/API calls, source-code feature changes, or tracked runtime artifacts.
- Roadmap v2.5 planning created the Opportunity Formation & Founder Learning checklist from first-run lessons: GitHub vendor-promo noise, candidate duplicates, mojibake, price false positives, and the strongest unpaid-invoice/SMB cash-collection pain. Implementation starts at item `1.1`; no source code features, live collection, live internet/API calls, or live LLM/API calls were performed by this planning checkpoint.
- Roadmap v2.5 item 1.1 added tracked founder manual labels for all 18 first-run candidate signals under `examples/first_real_open_source_signal_run_v1/`, preserving duplicate evidence IDs, source URLs, classifications, founder labels, recommended actions, and issue tags for future source-quality hardening without additional live collection, source-code feature implementation, live internet/API calls, or live LLM/API calls.

## Roadmap v2.4 Final Branch Notes

- Final branch: `feat/v2-4-final-validation-and-gap-closure`.
- Completed: `17 / 17`.
- Remaining: `0 / 17`.
- Latest completed roadmap item: Roadmap v2.4 `8.2`.
- Local 8.x / gap-closure commits recorded on this branch:
  - `21e44fb Add v2.4 end-to-end validation report`
  - `4fcd7b0 Close roadmap v2.4 completion checkpoint`
  - `8ab1e94 Add weak signal aggregation protocol`
  - `c804404 Add cluster synthesis contract`
  - `620332a Add kill archive scoring feedback`
  - final 8.2 checkpoint rerun commit follows this project-state update.
- No release tag was created.
- No push, PR, or merge was performed by Codex.

- Roadmap v2.5 item 1.2 added deterministic GitHub vendor-promo/SEO suppression with classification downgrade, scoring caps, founder-package risk notes, and fixture-only tests against first-run false positives without live collection, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 1.3 hardened PriceSignal extraction against receipt thresholds, tax/deduction/regulatory limits, `$1.25M` truncation, and weak vendor-commercial WTP phrases while preserving organic affordability complaints without live collection, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 1.4 added deterministic CandidateSignal dedup before founder-facing packages and weak-pattern aggregation, preserving duplicate evidence/signal/source metadata while keeping raw artifacts intact and avoiding live internet/API or live LLM/API calls.
- Roadmap v2.5 item 1.5 extended deterministic mojibake repair for founder-facing evidence, candidate summaries, and founder package outputs, preserving raw evidence traceability without additional live collection, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 1.6 ran a second bounded HN + GitHub live comparison after Block 1 hardening, recorded ignored runtime artifacts under `artifacts/discovery_runs/second_controlled_open_source_signal_run_v1/`, and confirmed vendor-promo, price false-positive, duplicate, and mojibake behavior before moving to evidence packs.
- Roadmap v2.5 item 2.1 added the deterministic `EvidencePack` contract with serializable evidence items, source summaries, risk notes, optional price/weak-pattern/kill-warning IDs, explicit insufficient-evidence representation, and traceability-preserving validation without live collection, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 2.2 added a deterministic EvidencePack builder that consumes existing candidate signals, price signals, weak patterns, kill archive warnings, and discovery artifacts, writes `evidence_packs.json` in discovery runs, preserves traceability, and records risk notes without live collection, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 2.3 displayed deterministic EvidencePack sections in founder package JSON/Markdown outputs with compact counts, evidence IDs, source URLs, linked price/weak-pattern/kill-warning IDs, and risk notes while preserving existing quality sections without live collection, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 3.1 added a no-LLM deterministic OpportunityCandidate baseline from EvidencePack inputs, preserving evidence IDs, signal IDs, source URLs, unsupported assumptions, conservative confidence, and risk notes without live collection, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 3.2 added a future-only LLM opportunity synthesis contract from EvidencePack and deterministic OpportunityCandidate inputs, with evidence-bound prompt/schema validation, advisory-only response checks, and local-preview `opportunity_synthesis` budget-role support without live collection, live internet/API calls, live LLM/API calls, or provider execution.
- Roadmap v2.5 item 3.3 added an offline deterministic/mock opportunity synthesis dry-run that builds the 3.1 baseline, constructs the 3.2 synthesis request, validates a schema-compliant evidence-bound mock response, records prompt hash/preview and no-live-provider flags, and avoids live collection, live internet/API calls, live LLM/API calls, and provider execution.
- Roadmap v2.5 item 4.1 added a deterministic post-synthesis opportunity quality gate with pass/park/reject decisions, traceability checks, conservative rationale, and founder-decision authority preserved without live collection, live internet/API calls, live LLM/API calls, or provider execution.
- Roadmap v2.5 item 4.2 added deterministic evidence sufficiency scoring with explicit dimensions, missing-evidence/risk factors, score bands, and narrow quality-gate inclusion while preserving founder-decision authority and no-auto-promote behavior.
- Roadmap v2.5 item 4.3 added deterministic false-positive opportunity suppression for generic, vendor/SEO, product-submission, disguised-consulting, buyerless, unsupported-assumption-heavy, and low-sufficiency opportunities, with quality-gate integration that prevents pass for high/critical false positives without auto-promotion.
- Roadmap v2.5 item 5.1 added a structured FounderDecisionV2 taxonomy with five decision values, decision-specific reason categories, deterministic IDs, traceability fields, validation, serialization, and summaries without changing scoring, mapping feedback, or founder preference profiles.
- Roadmap v2.5 item 5.2 added deterministic founder feedback mapping from `FounderDecisionV2` to opportunity, evidence-pack, optional cluster, evidence, source-signal, and source-URL lineage, with feedback tags, signal impact, recommended future handling, serialization, validation, and record-only semantics without scoring mutation, ML-training claims, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 5.3 added deterministic FounderPreferenceProfile built from `FounderDecisionV2` and optional `FounderFeedbackMapping` inputs, with preferred pain types, rejected/promoted patterns, recurring kill reasons, evidence gap aggregation, scoring hints, package warnings, and fixture-driven tests without ML-training claims, scoring mutation, internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 6.1 added a deterministic `WeeklyOpportunityReviewPackage` that aggregates existing founder decisions, feedback mappings, preference profiles, and opportunity candidates into a founder-facing weekly review with structured sections, traceability-preserving item IDs, clear empty states, advisory-only enforcement, and JSON/Markdown rendering without live collection, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 6.2 added a deterministic next-best-founder-actions layer (`FounderAction` model, `build_next_best_founder_actions()`) that converts the `WeeklyOpportunityReviewPackage` into a prioritized, flattened list of advisory actions with stable action IDs, 10 action types, priority bands, linked source artifact IDs, suggested next steps, and JSON/Markdown rendering without autonomous decisions, portfolio transitions, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 6.3 added deterministic parking lot / revisit logic (`ParkingLotRecord` model, `RevisitMatch` model, `build_parking_lot_records()`, `match_revisit_candidates()`) that builds parked records from PARK/REVISIT_LATER decisions, matches new evidence using three-tier deterministic matching (pattern keys then token overlap then substring), surfaces advisory revisit matches in the weekly review revisit_queue section, and avoids autonomous portfolio transitions, embeddings, ML, LLM, live internet/API calls, or live LLM/API calls.
- Roadmap v2.5 item 7.1 created the opportunity quality evaluation dataset v1 with 10 synthetic labeled cases under `examples/evaluation_dataset_v2_5/opportunity_quality_cases_v1.json`, a loader with validation in `src/oos/evaluation_dataset.py`, and 14 focused tests covering dataset integrity, case-type coverage, label-decision consistency, and deterministic gate evaluation without live APIs, LLM calls, or internet access.
- Roadmap v2.5 item 7.2 created deterministic regression metrics (`OpportunityQualityRegressionMetrics` model, `compute_regression_metrics()`) that load the v1 quality dataset, run the existing `evaluate_opportunity_quality()` pipeline on each case, compare actual gate outputs to expected labels, and produce JSON-serializable aggregate and per-case metrics (total_cases, gate_match_rate=1.0, false_positive_rate=0.4, duplicate_rate=0.1, unsupported_assumptions_count=30) with 52 focused tests and no live APIs, LLM calls, or internet access.
- Roadmap v2.5 item 7.3 created deterministic end-to-end fixture validation (`V2_5EndToEndValidationReport` model, `run_v2_5_end_to_end_fixture_validation()`) that processes all 10 quality fixture cases through the full v2.5 advisory pipeline — evidence packs, quality gates, founder decisions, feedback mappings, preference profiles, parking lot records, weekly review packaging, and next-best actions — with 37 focused tests, 5-stage traceability verification, advisory-only enforcement (0 autonomous decisions), deterministic output, and no live APIs, LLM calls, or internet access.
- Roadmap v2.5 item 8.1 closed the roadmap with a final validation checkpoint: 1106 tests, 0 failures; `scripts/oos-validate.ps1` pass; `git diff --check` clean; roadmap state `completed` at `24 / 24`. PR `#40` was merged to `main`, and tag `v2.5` was created and pushed. Item 7.4 (third controlled live run) remains optional/deferred.
- Roadmap v2.6 planning created the Real Weekly Loop / Operationalization checklist with 9 implementation items: weekly run artifact contract, unified weekly cycle builder, CLI command, founder inbox v2, founder decision import, weekly cycle status command, run reports and dashboard index, fixture end-to-end validation, and final v2.6 checkpoint. Implementation starts at item 1.1; no source code features, live collection, live internet/API calls, or live LLM/API calls were performed by this planning checkpoint.
