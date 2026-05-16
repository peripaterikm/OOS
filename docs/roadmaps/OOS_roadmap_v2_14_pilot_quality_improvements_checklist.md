# OOS Roadmap v2.14 — Pilot Quality Improvements

**Status:** Active / item 8 ready
**Branch:** `ops/v2-13-pilot-cycle-1-run`
**Created:** 2026-05-14
**Based on:** v2.13 Pilot Cycle 1 CONDITIONAL GO decision
**Parent decision:** [`docs/operations/pilot_cycle_1_conditional_go_summary_v2_13.md`](../operations/pilot_cycle_1_conditional_go_summary_v2_13.md)

---

## 0. Roadmap Overview

### Active Roadmap

- [x] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md`
- [x] **0.2** Current item: `8 — Targeted regression fixtures from Run 1 / Run 2 summaries`
- [x] **0.3** Roadmap state: `active / item 8 ready`
- [x] **0.4** Completed from this roadmap: **8 / 11**
- [x] **0.5** Remaining: **3 / 11**
- [x] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md` (complete, `12 / 12`)

### Strategic Purpose

v2.13 Pilot Cycle 1 demonstrated that the OOS pipeline is technically stable and traceable, but quality problems prevent a clean GO. This roadmap addresses those quality problems before any source expansion or broader operational cycle.

```
    v2.13 delivered (operational test)              v2.14 delivers (quality improvements)
    ────────────────────────────────                ──────────────────────────────────────
    Pilot Cycle 1 Run 1 (broad)                     Noise classification hardening
    Pilot Cycle 1 Run 2 (targeted)                  Quality flags → scoring integration
    CONDITIONAL GO decision                         Cluster title generation cleanup
    Confirmed theme: Agent Debugging                Cluster split/merge tuning
    Weaker theme: LLM App Testing                   Founder review package clarity
    5 quality problems identified                   Opportunity synthesis hardening
                                                    Source Quality Report contradiction fix
                                                    Targeted regression fixtures
                                                    Controlled quality smoke
                                                    Final v2.14 checkpoint
```

### Core Concept

v2.14 is **quality improvement, not feature expansion**. It takes the specific quality problems identified in Pilot Cycle 1 and fixes them in the pipeline. The output is a pipeline that can reliably separate signal from noise, produce consistent cluster titles, eliminate catch-all clusters, synthesize opportunity candidates from real clusters, and produce a non-contradictory Source Quality Report. No new sources, no new features, no scope creep.

### Source Constraint

| Constraint | Detail |
|-----------|--------|
| Allowed sources | HN (`hacker_news`) + GitHub Issues (`github_issues`) **only** |
| Source expansion | **BLOCKED** until after explicit GO decision in a future pilot cycle |
| No Product Hunt | BLOCKED |
| No Reddit | BLOCKED |
| No pimenov.ai | BLOCKED |
| No broad web | BLOCKED |
| No Stack Exchange | BLOCKED |

### Strategic Principles

- **Quality-first.** Fix noise classification, cluster quality, opportunity synthesis, and report consistency before doing anything else.
- **No source expansion.** HN + GitHub Issues only. All other sources remain blocked.
- **No live APIs in tests.** Fixture-first preserved. Tests use deterministic fixtures from Run 1 and Run 2 summaries.
- **No LLM validation in default tests.** All scoring is deterministic. LLM contracts may be hardened but remain disabled by default.
- **Runtime artifacts stay outside repo** unless explicitly approved per item.
- **Founder review remains manual.** No automated Go/No-Go or promotion decisions.
- **Traceability to source_url remains mandatory.** Every artifact must trace back to a real `http(s)://` URL.

### Scope

- Wire quality flags into Founder Review Package recommendation behavior via quality summary aggregation, promotion blockers, and founder-visible quality context.
- Fix cluster title generation for consistency and specificity.
- Tune cluster split/merge to eliminate catch-all clusters.
- Harden opportunity synthesis to produce candidates from real clusters.
- Fix Source Quality Report contradiction between `needs_review_count` and `accepted_count`.
- Improve founder review package clarity.
- Create targeted regression fixtures from Run 1 and Run 2 summaries.
- Run controlled quality smoke on the Agent Debugging theme.
- Final v2.14 validation checkpoint.

### Explicit Non-Goals (Across All v2.14 Items)

- Source expansion of any kind
- Product Hunt implementation
- Reddit integration
- pimenov.ai integration
- Stack Exchange / Stack Overflow inclusion
- Discord / Slack / X (Twitter) integration
- AlternativeTo / YC / Crunchbase integration
- App marketplaces / job boards / blogs / newsletters
- Broad scraping
- Automated founder decisions
- Autonomous source expansion
- Portfolio mutation
- `KillReason` record creation
- Production deployment
- UI / dashboard work
- Database / server architecture
- LLM integration as default (contracts may be hardened; execution remains disabled by default)

### Artifact Policy (v2.14)

- Runtime artifacts stay outside repo unless explicitly approved per item.
- No committed repository artifacts from pilot runs.
- Regression fixtures from Run 1/Run 2 summaries are **docs-derived fixtures** — small, curated, deterministic JSON files based on summarized patterns, not full runtime JSON dumps.
- Validation reports may be committed in the final checkpoint if explicitly allowed.

### Workflow Rules

- Branch: `ops/v2-13-pilot-cycle-1-run` (reuse existing branch for v2.14 planning/docs)
- One local commit per roadmap item during execution.
- Push/PR/merge/tag only when explicitly requested.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Windows-native only: PowerShell, native Python venv.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.

---

## 0. Planning Checkpoint

### Intent

Create the official Roadmap v2.14 planning checklist. Docs-only. No source code, tests, scripts, examples, or artifacts. This item closes the planning phase.

### Allowed Scope

- Create: `docs/roadmaps/OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md` (this file)
- Read (do not modify): `docs/operations/pilot_cycle_1_conditional_go_summary_v2_13.md`, existing source files
- Update: `docs/dev_ledger/00_project_state.md` for roadmap bookkeeping only

### Non-Goals

- Creating source code, test, script, or artifact files
- Modifying any existing file outside this roadmap document except `docs/dev_ledger/00_project_state.md` bookkeeping
- Running any part of the pilot pipeline
- Making live API or LLM calls

### Implementation Requirements

- Roadmap document exists at the specified path
- All 11 items (0–10) are defined with intent, allowed scope, non-goals, implementation requirements, tests/validation expectations, and definition of done
- Roadmap overview trackers (0.1–0.6) are updated to show item 0 complete and item 1 next
- v2.14 intent, scope, non-goals, quality targets, branch strategy, and source-expansion block are verified against the v2.13 Conditional Go decision

### Tests/Validation Expectations

- `.\scripts\dev-git-check.ps1` passes
- `git status --short` shows only docs-only roadmap and dev-ledger changes before commit

### Definition of Done

- [x] **0.0.1** Roadmap v2.14 document exists at `docs/roadmaps/OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md`
- [x] **0.0.2** Roadmap state is `active / item 1 ready`
- [x] **0.0.3** Current item is `1 — Noise Classification Hardening`
- [x] **0.0.4** Completed: `1 / 11`
- [x] **0.0.5** Remaining: `10 / 11`
- [x] **0.0.6** All 11 items defined with all required sections
- [x] **0.0.7** `.\scripts\dev-git-check.ps1` passes or reports only the expected pre-commit dirty tree
- [x] **0.0.8** `git status --short` shows only docs-only roadmap and dev-ledger changes before commit
- [x] **0.0.9** One local commit made with message: `[v2.14] 0 planning checkpoint`

---

## 1. Noise Classification Hardening

### Intent

Implement a deterministic noise classifier that maps quality flags (including `vendor_promo`, `low_confidence_extraction`, `generic_language`, `missing_actor`) and content signals to one of three outcomes: `accepted`, `weak`, or `noise`. Wire the classifier into Source Quality Report signal counting (accepted/weak/noise) and ensure candidate signal field propagation from evidence. This item does NOT implement scoring/tier integration (that is Item 2). It does NOT add a `noise_classification` field to CandidateSignal unless already present. It does NOT modify `candidate_signal_extractor.py` or `signal_scoring_model_v2.py` unless those files were actually touched during implementation.

### Allowed Scope

- Create/Modify: [`src/oos/noise_classifier.py`](src/oos/noise_classifier.py) — deterministic noise classification function with severity groups, alias resolution, pain marker detection, and rule-ordered classification
- Modify: [`src/oos/source_quality_report.py`](src/oos/source_quality_report.py) — integrate noise classifier into accepted/weak/noise signal counting
- Modify: [`src/oos/operational_discovery_pilot.py`](src/oos/operational_discovery_pilot.py) — propagate `quality_flags` and `evidence_kind` from evidence → derived candidate signals
- Modify: [`tests/test_noise_classifier.py`](tests/test_noise_classifier.py) — focused tests for all classification rules, flag aliases, pain matching, and edge cases
- May touch: [`tests/test_source_quality_report.py`](tests/test_source_quality_report.py), [`tests/test_operational_discovery_pilot.py`](tests/test_operational_discovery_pilot.py) if existing tests need updating

### Non-Goals

- Adding new quality flag dimensions (use existing flags only)
- LLM-based noise classification
- Source-specific noise classification (deferred to source quality report improvements)
- Auto-killing signals (classification only; founder retains kill authority)
- Modifying the evidence cleaner or RawEvidence model
- Scoring/tier integration (belongs to Item 2)
- Adding `noise_classification` field to `CandidateSignal` (not required for classification)
- Modifying `candidate_signal_extractor.py` or `signal_scoring_model_v2.py` (not required for Item 1)
- Implementing `CandidateSignal.noise_classification` field (not needed; classification is external)

### Implementation Requirements

1. Define explicit noise classification rules based on existing quality flags and content signals:
   - Severe flags (e.g., `bot_generated`, `maintainer_housekeeping`, `flamewar_or_meta_discussion`) → `noise`
   - `low_text_context` + no clear pain → `noise`; `low_text_context` + clear pain → `weak` (never `accepted`)
   - `suspected_self_promo` / `vendor_promo` + `product_launch` + no clear pain → `noise`
   - `generic_language` + `unclear_actor` / `missing_actor` + no clear pain → `noise`
   - Medium-risk flags (`low_confidence_extraction`, `generic_language`, `stale_issue`, etc.) → `weak`
   - No negative flags → `accepted`
2. Resolve known flag aliases: `vendor_promo` → `suspected_self_promo`, `missing_actor` → `unclear_actor`
3. Use token/phrase-aware pain matching: single-word pain markers require word boundaries (`\b`); phrase markers match as substrings
4. Integrate noise classifier into Source Quality Report signal counting (accepted/weak/noise)
5. Propagate `quality_flags` and `evidence_kind` from evidence items into derived candidate signals in the pilot orchestrator

### Tests/Validation Expectations

- Unit tests verify noise classification rules produce expected outputs for all flag combinations
- Unit tests verify flag aliases (`vendor_promo`, `missing_actor`) resolve correctly
- Unit tests verify `low_text_context` behavior: no-pain → noise, with-pain → weak, never accepted
- Unit tests verify pain matching: word boundaries for single words, substring for phrases
- Unit tests verify none of the previously-missing flags classify as `accepted`-clean
- Existing tests continue to pass
- At least 50 focused tests

### Definition of Done

- [x] **1.1** Deterministic `classify_noise()` function in [`src/oos/noise_classifier.py`](src/oos/noise_classifier.py) with severity mapping, flag aliases, token/phrase-aware pain marker detection, and rule-ordered classification
- [x] **1.2** Noise classification rules function exists and is deterministic
- [x] **1.3** Quality flags integrated into Source Quality Report signal counting (accepted/weak/noise) in [`src/oos/source_quality_report.py`](src/oos/source_quality_report.py)
- [x] **1.4** Pilot orchestrator propagates `quality_flags` from evidence → derived candidate signals in [`src/oos/operational_discovery_pilot.py`](src/oos/operational_discovery_pilot.py)
- [x] **1.5** Previously-missing flags (`vendor_promo`, `low_confidence_extraction`, `generic_language`, `missing_actor`) are handled; none classify as `accepted`-clean
- [x] **1.6** Token/phrase-aware pain matching: `bug` does not match inside `debugging`
- [x] **1.7** `low_text_context` + clear pain → `weak` (never `accepted`)
- [x] **1.8** All existing and new tests pass
- [x] **1.9** `.\scripts\dev-git-check.ps1` passes
- [x] **1.10** One local commit made with message: `[v2.14] 1 harden noise classification`

**Item 1 complete; item 2 is next.**

---

## 2. Quality Flags to Scoring/Tier Integration

### Intent

Integrate quality flags into the Founder Review Package recommendation behavior via quality summary aggregation, promotion blockers, and founder-visible quality context. Quality evidence summary (noise classification from Item 1) feeds into promotion gates: clusters with high noise ratios, severe flags, or only weak evidence are blocked from PROMOTE. This ensures that signals with quality concerns are appropriately flagged for founder review without rewriting the broad scoring model.

### Allowed Scope

- Modify: [`src/oos/noise_classifier.py`](src/oos/noise_classifier.py) — `compute_evidence_quality_summary()` and `compute_quality_gate_reasons()` for cluster-level quality aggregation and gate reasoning
- Modify: [`src/oos/pilot_founder_review_package.py`](src/oos/pilot_founder_review_package.py) — integrate quality summary and blockers into review item recommendation logic and Markdown rendering
- Modify: tests for noise classifier and founder review package

### Non-Goals

- Changing the scoring formula weights
- Creating signal_scoring_model_v2.py
- Rewriting PainCluster scoring weights
- Implementing full cluster eligibility scoring model beyond FRP promotion gates
- Adding new scoring dimensions or tier system redesign
- LLM-based scoring
- Broad scoring model rewrite

### Implementation Requirements

1. `compute_evidence_quality_summary()` aggregates per-evidence noise classifications into cluster-level quality summary with severity counts.
2. `compute_quality_gate_reasons()` computes promotion_blockers and quality_gate_reasons from quality summary + traceability/source-scope flags.
3. `FounderReviewQueueItem` carries quality_summary, promotion_blockers, quality_gate_reasons, evidence_quality_counts, and dominant_quality_flags.
4. `recommend_decision()` checks promotion_blockers before PROMOTE; blockers route to KILL, NEEDS_MORE_EVIDENCE, or PARK.
5. Markdown renderer exposes a compact "Quality Gate" block per review item with evidence quality counts, ratios, dominant flags, blockers, and gate reasons.
6. Alias resolution (`vendor_promo` → `suspected_self_promo`, `missing_actor` → `unclear_actor`) applied in severity bucket counting within quality summary.

### Tests/Validation Expectations

- Unit tests verify quality summary severity counts resolve aliases
- Unit tests verify promotion blockers prevent PROMOTE
- Unit tests verify Markdown includes Quality Gate section per review item
- Unit tests verify backward-compatible older review items render without crashing
- JSON roundtrip preserves quality fields
- At least 20 focused tests

### Definition of Done

- [x] **2.1** Quality summary aggregation with alias resolution implemented
- [x] **2.2** Promotion blocker and quality gate reason computation implemented
- [x] **2.3** Quality fields added to FounderReviewQueueItem and roundtrip
- [x] **2.4** `recommend_decision()` checks promotion_blockers before PROMOTE
- [x] **2.5** Markdown Quality Gate block per review item
- [x] **2.6** All existing tests pass
- [x] **2.7** At least 20 focused tests pass
- [x] **2.8** One local commit made with message: `[v2.14] 2 integrate quality flags into scoring tiers`

**Item 2 complete; item 3 is next.**

---

## 3. Cluster Title Generation Cleanup

### Intent

Fix inconsistent cluster titles. Pilot Cycle 1 produced clusters with titles ranging from concrete ("Debugging LLM Agent Execution Traces") to vague ("AI Development Tooling Gaps"). Inconsistent titling makes founder review harder and reduces cluster utility. This item implements deterministic title generation rules that produce consistent, specific, pain-focused cluster titles.

### Allowed Scope

- Modify: [`src/oos/pain_cluster_assembly.py`](src/oos/pain_cluster_assembly.py) — title generation logic
- Modify: [`src/oos/pain_cluster.py`](src/oos/pain_cluster.py) — title validation rules
- Modify: tests for cluster assembly

### Non-Goals

- LLM-based title generation
- Manual title curation
- Cluster content changes (only title generation)

### Implementation Requirements

1. Define deterministic title template: `{pain_verb} {object} {context}` where:
   - `pain_verb` — from the cluster's dominant pain signal (e.g., "Debugging", "Monitoring", "Managing")
   - `object` — from the cluster's dominant workflow/object (e.g., "LLM Agent Traces", "Prompt Versions")
   - `context` — from the cluster's dominant actor or environment (e.g., "in Production", "for AI Developers")
2. Add title validation rules:
   - Minimum specificity: title must contain at least one concrete noun (not just "Development" or "Tooling")
   - Maximum length: 100 characters
   - No catch-all keywords: titles must not contain "General", "Miscellaneous", "Various", "Other"
3. Add `title_quality_score` field to cluster metadata (0.0–1.0) based on:
   - Specificity of pain_verb (is it concrete vs. generic?)
   - Specificity of object (is it a real thing vs. a category?)
   - Presence of context
4. Flag low-quality titles (`title_quality_score < 0.5`) in cluster metadata and Source Quality Report.

### Tests/Validation Expectations

- Unit tests verify title generation produces specific, template-conforming titles for known cluster compositions
- Unit tests verify title validation rejects catch-all keywords
- Unit tests verify `title_quality_score` computation
- Low-quality titles flagged in cluster metadata
- At least 15 focused tests

### Definition of Done

- [x] **3.1** Deterministic `generate_cluster_review_title()` implemented in `src/oos/pain_cluster_assembly.py` with pattern-based, component-derived, and evidence-based fallback tiers
- [x] **3.2** Title validation rules: non-empty, ≤90 chars, no `[dead]`, no `needs_more_evidence`, no malformed grammar, no raw HN prefixes
- [x] **3.3** Evidence prioritization: primary_pain beats context_only, accepted beats noise evidence, product_launch does not dominate
- [x] **3.4** Founder Review Package integration: `FounderReviewQueueItem.title` uses `generate_cluster_review_title()`, Markdown renders cleaned title, JSON roundtrip preserves title
- [x] **3.5** All existing tests pass (2521 tests OK)
- [x] **3.6** At least 15 focused tests pass (17 title-generation tests + 7 FRP integration tests = 24 total)
- [x] **3.7** `.\scripts\dev-git-check.ps1` passes
- [x] **3.8** One local commit made with message: `[v2.14] 3 clean cluster review titles`

**Item 3 complete; item 4 is next.**

---

## 4. Cluster Split/Merge Tuning

### Intent

Eliminate catch-all clusters by tuning the split/merge logic in cluster assembly. Pilot Cycle 1 produced clusters that grouped signals sharing only superficial keywords (e.g., "AI", "LLM", "developer") rather than a coherent pain pattern. This item implements canonical pain anchors plus `_should_merge()` compatibility checks to govern cluster membership, replaces simple anchor|actor pre-grouping with union-find clustering, handles actor over-splitting, and adds over-merge detection.

### Allowed Scope

- Modify: [`src/oos/pain_cluster_assembly.py`](src/oos/pain_cluster_assembly.py) — split/merge logic, `_should_merge()` active clustering via union-find
- Modify: [`src/oos/pain_cluster.py`](src/oos/pain_cluster.py) — cluster cohesion metrics (only if required)
- Modify: tests for cluster assembly

### Non-Goals

- Redesigning the clustering algorithm
- Adding embedding-based clustering (stays deterministic/keyword-based)
- LLM-based cluster curation

### Implementation Requirements

1. Add `cohesion_score` field to `PainCluster` (0.0–1.0):
   - Based on actor overlap, workflow overlap, object overlap, and pain_verb overlap
   - Low cohesion (< 0.4) = potential catch-all cluster
2. Add over-merge detection:
   - If a cluster has >8 member signals, check cohesion
   - If cohesion < 0.4 with >8 members, flag as `catch_all_risk = true`
   - Attempt auto-split: identify sub-groups within the cluster with higher internal cohesion
3. Active merge/split logic via `_should_merge()` and union-find clustering:
   - Same strong specific canonical anchor may merge even if actor differs unknown/generic.
   - Generic anchor requires ≥2 of {actor, workflow_family, object} to match.
   - Specific↔generic anchor crossing requires all 3 dimensions to match.
   - Incompatible anchors (block-pairs) never merge.
   - Product launch / self-promo and low-context evidence cannot dominate concrete bug clusters.
   - Noise evidence does not merge with accepted evidence.
   - Deterministic ordering (stable sort by evidence_id) ensures reproducible clusters.
4. Add `split_suggestion` to cluster metadata when auto-split identifies viable sub-groups.
5. Update Source Quality Report with catch-all cluster count.

### Tests/Validation Expectations

- Unit tests verify cohesion score computation
- Unit tests verify over-merge detection triggers at correct thresholds
- Unit tests verify auto-split produces higher-cohesion sub-groups
- Unit tests verify merge threshold prevents superficial-keyword-only merges
- Unit tests verify actor-mismatch merge for same strong anchor
- Unit tests verify provenance↔generic LLM debugging not merged
- Unit tests verify prompt_trace_replay↔stack_trace_context not merged
- Unit tests verify checkpoint/state↔eval/testing not merged
- Unit tests verify product_launch↔bug_report not merged without specific anchor
- Catch-all clusters flagged in Source Quality Report
- At least 39 focused tests

### Definition of Done

- [x] **4.1** `cohesion_score` field and computation implemented
- [x] **4.2** Over-merge detection with `catch_all_risk` flag implemented
- [x] **4.3** Auto-split suggestion for low-cohesion large clusters implemented
- [x] **4.4** `_should_merge()` wired into active union-find clustering (Codex fix 1)
- [x] **4.5** Actor over-splitting fixed: same strong anchor merges despite unknown/generic actor (Codex fix 2)
- [x] **4.6** No-overmerge tests strengthened with assertion helpers and specific assertions (Codex fix 3)
- [x] **4.7** Roadmap reflects implemented logic: canonical anchors + `_should_merge()` compatibility checks (Codex fix 4)
- [x] **4.8** Source Quality Report includes catch-all cluster count
- [x] **4.9** All existing tests pass (474 focused tests OK)
- [x] **4.10** At least 39 focused tests pass (39 focused tests OK)
- [x] **4.11** `.\scripts\dev-git-check.ps1` passes
- [x] **4.12** One local commit made with message: `[v2.14] Fix cluster split merge review findings`

**Item 4 complete (Codex review fixes applied); item 5 is next.**

---

## 5. Founder Review Package Clarity Improvements

### Intent

Improve the founder review package structure, ordering, and evidence presentation based on Pilot Cycle 1 friction. The review package should make it easy to quickly assess cluster quality, trace evidence to sources, and spot noise. Specific improvements: cluster quality indicators at top, evidence excerpts, clearer signal-to-noise ratio display, and consistent formatting.

### Allowed Scope

- Modify: [`src/oos/pilot_founder_review_package.py`](src/oos/pilot_founder_review_package.py) — package structure and rendering
- Modify: tests for founder review package

### Non-Goals

- UI / dashboard work
- Interactive review tools
- Changing the review protocol or decision taxonomy
- Adding new artifact types

### Implementation Requirements

1. Add cluster-level quality summary at the top of each cluster section:
   - `cohesion_score` (from item 4)
   - `title_quality_score` (from item 3)
   - `catch_all_risk` flag (from item 4)
   - `noise_signal_count` / `clean_signal_count` / `suspected_noise_count`
   - Overall cluster quality: `high`, `medium`, `low`
2. Add evidence excerpt per signal in the review package (first 200 chars of cleaned text).
3. Add signal-to-noise ratio summary at package top:
   - Total signals / clean / suspected_noise / confirmed_noise
   - Per-source breakdown
4. Ensure consistent Markdown formatting:
   - Cluster titles always in `### {title}`
   - Evidence links always as `- [source_url](source_url)`
   - Quality flags always as inline badges: `[LOW_CONFIDENCE]`, `[GENERIC]`, `[NOISE]`
5. Remove or collapse redundant sections that added friction in Pilot Cycle 1.

### Tests/Validation Expectations

- Unit tests verify cluster quality summary fields are present and correct
- Unit tests verify evidence excerpts are included and truncated correctly
- Unit tests verify signal-to-noise ratio summary at package top
- Unit tests verify per-source SNR breakdown table
- Unit tests verify Markdown formatting consistency
- Markdown output is human-readable and well-structured
- At least 15 focused tests

### Definition of Done

- [x] **5.1** Cluster quality summary with scores and flags in each cluster section
- [x] **5.2** Evidence excerpts (first 200 chars) per signal
- [x] **5.3** Signal-to-noise ratio summary at package top (aggregate + per-source breakdown)
- [x] **5.4** Consistent Markdown formatting with quality badges
- [x] **5.5** Redundant sections removed or collapsed; "Review Counts" renamed to "Decision Breakdown"
- [x] **5.6** All existing tests pass (2609 tests OK)
- [x] **5.7** At least 15 focused tests pass (18 new Codex fix tests + 17 existing = 35 Item 5 tests)
- [x] **5.8** `.\scripts\dev-git-check.ps1` passes (dirty tree expected pre-commit)
- [x] **5.9** Codex fixes applied: stale review_priority reassigned after sort, cluster_quality_label blocker-aware, per-source SNR breakdown, Decision Breakdown rename
- [x] **5.10** One local commit made with message: `[v2.14] Fix founder review clarity findings`

**Item 5 complete (Codex review fixes applied); item 6 is next.**

---

## 6. Opportunity Synthesis Contract / Deterministic Stub Hardening

### Intent

Harden the opportunity synthesis pipeline so it produces opportunity candidates from real clusters. Pilot Cycle 1 produced zero opportunity candidates despite 80 signals and 14 + 12 pain clusters. The deterministic opportunity synthesis stub from v2.5 works on evaluation-dataset fixtures but produces nothing on operational pilot data. This item hardens the stub to produce at least baseline opportunity candidates from real clusters and prepares the LLM contract for future activation.

### Allowed Scope

- Modify: [`src/oos/ai_ideation_evaluation.py`](src/oos/ai_ideation_evaluation.py) — opportunity synthesis logic
- Modify: [`src/oos/llm_opportunity_synthesis_contract.py`](src/oos/llm_opportunity_synthesis_contract.py) — contract hardening (disabled by default)
- Modify: [`src/oos/operational_discovery_pilot.py`](src/oos/operational_discovery_pilot.py) — wire opportunity synthesis into pilot pipeline
- Modify: tests for opportunity synthesis and pilot orchestrator

### Non-Goals

- Activating LLM integration (contract hardened, execution disabled)
- Guaranteeing high-quality opportunities (baseline/deterministic only)
- Adding new ideation modes

### Implementation Requirements

1. Harden deterministic stub to consume `PainCluster` inputs and produce at least 1 `OpportunityCandidate` per cluster meeting minimum thresholds:
   - Cluster has >= 2 clean signals
   - Cluster has `cohesion_score >= 0.4`
   - Cluster is not `catch_all_risk = true`
2. Each deterministic candidate must include:
   - `title` — from cluster title + "Opportunity" suffix
   - `pain_summary` — one-sentence synthesis of cluster pain
   - `target_buyer` — from cluster's dominant actor
   - `evidence_ids` — linked signal IDs from the cluster
   - `source_urls` — linked source URLs from cluster evidence
   - `confidence` — `low` (deterministic stub baseline)
3. Wire opportunity synthesis into the pilot orchestrator so it runs after cluster assembly.
4. Hardened LLM contract (disabled by default):
   - Update prompt template to accept `PainCluster` inputs
   - Add validation rules for cluster-derived candidates
   - Add `contract_version` field
   - Keep provider disabled; deterministic stub is the default path
5. Add `opportunity_candidates.json` to pilot run artifacts.

### Tests/Validation Expectations

- Unit tests verify deterministic stub produces candidates for qualifying clusters
- Unit tests verify zero candidates for non-qualifying clusters (low cohesion, catch-all, insufficient signals)
- Unit tests verify candidate fields are populated correctly
- Unit tests verify LLM contract validation rules (disabled provider, mock response only)
- Pilot orchestrator writes `opportunity_candidates.json`
- At least 20 focused tests

### Definition of Done

- [x] **6.1** Deterministic stub produces candidates from qualifying clusters
- [x] **6.2** Candidate fields populated: title, pain_summary, target_buyer, evidence_ids, source_urls, confidence
- [x] **6.3** Opportunity synthesis wired into pilot orchestrator
- [x] **6.4** `opportunity_candidates.json` in pilot run artifacts
- [x] **6.5** LLM contract hardened (prompt template, validation, version; provider disabled)
- [x] **6.6** All existing tests pass
- [x] **6.7** At least 20 focused tests pass
- [x] **6.8** `.\scripts\dev-git-check.ps1` passes
- [x] **6.9** One local commit made with message: `[v2.14] 6 harden opportunity synthesis stub`

**Item 6 complete; item 7 is next.**

---

## 7. Source Quality Report Contradiction Fix

### Intent

Fix the contradiction in the Source Quality Report where `needs_review_count > 0` coexists with `accepted_count = total_count`. If items need review, they should not all be accepted. This is a logic bug in the report builder: quality flags and review status are tracked but not reconciled with acceptance decisions.

### Allowed Scope

- Modify: [`src/oos/source_quality_report.py`](src/oos/source_quality_report.py) — reconcile needs_review and acceptance logic
- Modify: tests for source quality report

### Non-Goals

- Redesigning the Source Quality Report
- Adding new metrics
- Changing the report format or sections

### Implementation Requirements

1. Audit the acceptance and needs_review logic paths:
   - Identify where `accepted_count` is computed
   - Identify where `needs_review_count` is computed
   - Determine why they diverge (signals counted as both accepted and needs_review)
2. Fix the reconciliation:
   - `accepted_count` must exclude `needs_review_count` signals, OR
   - `needs_review_count` must be a subset of `accepted_count` with explicit "accepted but flagged" semantics
   - Chosen approach: `accepted_count = total - rejected_count`; `needs_review_count` = signals with quality flags that were still accepted (i.e., `accepted_with_flags`)
3. Rename `needs_review_count` to `accepted_with_flags_count` for clarity, OR keep name but add explicit documentation that these are accepted signals with quality concerns.
4. Add `rejected_count` to the report (signals rejected due to noise classification from item 1).
5. Add `acceptance_rate = accepted_count / total_count` metric.

### Tests/Validation Expectations

- Unit tests verify `accepted_count + rejected_count = total_count`
- Unit tests verify `accepted_with_flags_count <= accepted_count`
- Unit tests verify no contradiction between counts
- Unit tests verify `rejected_count > 0` when noise classification is active
- At least 10 focused tests

### Definition of Done

- [x] **7.1** Quality dimensions separated: traceability_status, source_scope_status, classification_health, evidence_quality_status in `SourceQualityHealth`
- [x] **7.2** `noise_rate`, `weak_rate`, `flagged_record_count`, `flagged_record_rate` added to per-source metrics and report-level health
- [x] **7.3** Per-source contradiction detection (5 contradiction types: high accepted+flagged, accepted+non-zero noise/weak, traceability clean+noisy evidence, clusters from weak/noise sources, sensitive quality-risk flags)
- [x] **7.4** Report-level contradiction warnings (traceability clean but classification failing)
- [x] **7.5** Per-source quality warnings based on noise_rate, weak_rate, flagged_record_rate thresholds
- [x] **7.6** `classify_noise_for_evidence()` invoked via evidence-merged dict (evidence_id lookup for title/body/excerpt), not raw signal dict
- [x] **7.7** `WEAK_RATE_PROBLEMATIC` threshold corrected (0.50 → 0.70) to match test expectations
- [x] **7.8** Markdown rendering updated: Quality Status table, Quality Risk Summary, Quality Flags table, Per-Source Quality Warnings, Contradiction Warnings section
- [x] **7.9** Backward-compatible serialization: old reports without `quality_health` or new fields load safely with defaults
- [x] **7.10** Classifier parity tests: vendor_promo, missing_actor, low_text_context, positive pain flags all yield correct accepted/weak/noise counts
- [x] **7.11** All 98 source_quality_report tests pass; all 2713 tests pass in `dev-test.ps1 -Full`; controlled smoke 31/31 PASS
- [x] **7.12** One local commit made with message: `[v2.14] 7 fix source quality report contradictions`

---

## 8. Targeted Regression Fixtures from Run 1 / Run 2 Summaries

### Intent

Create small, curated, deterministic regression fixtures based on summarized patterns from Pilot Cycle 1 Run 1 and Run 2. These fixtures provide stable, repeatable test inputs that exercise the quality problems identified in the pilot without committing full runtime artifacts or requiring live API calls.

### Allowed Scope

- Create: fixture files under `tests/fixtures/v2_14/` (small, curated, deterministic JSON)
- May read (do not modify): summarized patterns from Run 1 and Run 2 (from the Conditional Go Summary, not raw runtime artifacts)
- Modify: tests that consume the new fixtures

### Non-Goals

- Committing runtime artifacts from Run 1 or Run 2
- Copying full `raw_evidence.json` or `candidate_signals.json` from pilot outputs
- Creating fixtures that require live API calls
- Creating fixtures for sources other than HN and GitHub Issues

### Implementation Requirements

1. Create `tests/fixtures/v2_14/` directory.
2. Create curated regression fixture sets:
   - `clean_signals_fixture.json` — 5–8 signals representing clean, specific pain from Agent Debugging theme (derived from Run 1/Run 2 patterns, not copied from runtime)
   - `noise_signals_fixture.json` — 5–8 signals with quality flags: generic, vendor-promo, missing-actor, low-confidence (derived from observed noise patterns)
   - `mixed_signals_fixture.json` — combination of clean + noise signals to test end-to-end classification
   - `catch_all_cluster_fixture.json` — signals that should NOT be clustered together (superficial keyword match only)
   - `agent_debugging_theme_fixture.json` — 10–12 signals focused on the confirmed Agent Debugging / Observability theme
3. Each fixture must be:
   - Valid `CandidateSignal` JSON (matching the existing schema)
   - Traced to real `http(s)://` source URLs (use example URLs from HN/GitHub patterns, not actual pilot URLs)
   - Annotated with expected quality flags, expected noise classification, and expected cluster assignments
4. Fixtures are **derived from summarized patterns**, not copied from runtime outputs. No raw pilot JSON is committed.

### Tests/Validation Expectations

- Fixture files are valid JSON and conform to `CandidateSignal` schema
- Fixture files contain expected quality flag annotations
- Existing tests continue to pass
- At least 10 focused tests using the new fixtures (test noise classification, cluster assembly, title generation)

### Definition of Done

- [ ] **8.1** `tests/fixtures/v2_14/` directory exists
- [ ] **8.2** Five fixture files created: clean, noise, mixed, catch_all_cluster, agent_debugging_theme
- [ ] **8.3** All fixtures are valid `CandidateSignal` JSON
- [ ] **8.4** Fixtures annotated with expected quality flags and classifications
- [ ] **8.5** At least 10 focused tests using new fixtures pass
- [ ] **8.6** All existing tests pass
- [ ] **8.7** `.\scripts\dev-git-check.ps1` passes
- [ ] **8.8** One local commit made with message: `[v2.14] 8 targeted regression fixtures`

---

## 9. Controlled Quality Smoke for Agent Debugging Theme

### Intent

Run a deterministic, fixture-only controlled quality smoke test focused on the confirmed Agent Debugging / Observability / Provenance theme. This smoke test exercises the entire v2.14 quality-improved pipeline on the theme-specific regression fixture (from item 8) and verifies that:
- Noise is classified and rejected
- Clusters have consistent, specific titles
- No catch-all clusters are produced
- Opportunity candidates are synthesized
- Source Quality Report has no contradictions

### Allowed Scope

- Modify: [`scripts/run-controlled-smoke.ps1`](scripts/run-controlled-smoke.ps1) — add quality smoke step
- Modify: tests for controlled smoke
- Read: v2.14 regression fixtures from item 8

### Non-Goals

- Live API calls
- Running on real pilot data
- Testing themes other than Agent Debugging
- Modifying the smoke test runbook beyond the new step

### Implementation Requirements

1. Add Step 11 (or next available) to `scripts/run-controlled-smoke.ps1`:
   - Run the full operational discovery pilot on `agent_debugging_theme_fixture.json` and `mixed_signals_fixture.json` (from item 8)
   - Verify: noise rate > 0% (some signals rejected)
   - Verify: acceptance rate < 100%
   - Verify: at least 1 cluster with `title_quality_score >= 0.5`
   - Verify: zero `catch_all_risk = true` clusters
   - Verify: at least 1 opportunity candidate synthesized
   - Verify: Source Quality Report `accepted_count + rejected_count = total_count`
2. Update [`docs/runbooks/controlled_weekly_run_smoke_test.md`](docs/runbooks/controlled_weekly_run_smoke_test.md) with the new quality smoke section.
3. Step must run on temp directory; no artifacts committed.

### Tests/Validation Expectations

- Quality smoke step passes on v2.14 fixtures
- All smoke assertions pass
- Existing smoke steps still pass
- Smoke runbook updated

### Definition of Done

- [ ] **9.1** Quality smoke step added to `scripts/run-controlled-smoke.ps1`
- [ ] **9.2** Smoke step passes on v2.14 fixtures (temp directory)
- [ ] **9.3** All existing smoke steps still pass
- [ ] **9.4** Smoke runbook updated with quality smoke section
- [ ] **9.5** `.\scripts\dev-git-check.ps1` passes
- [ ] **9.6** One local commit made with message: `[v2.14] 9 controlled quality smoke agent debugging theme`

---

## 10. Final v2.14 Checkpoint

### Intent

Close the v2.14 Pilot Quality Improvements roadmap. Verify all items are complete, all tests pass, all smoke tests pass, and the dev ledger is updated. Confirm that quality targets are met and the pipeline is ready for a re-evaluation pilot cycle. Do not start v2.15 or source expansion without explicit roadmap.

### Allowed Scope

- Update: roadmap overview trackers (0.1–0.6) in this file
- Update: [`docs/dev_ledger/00_project_state.md`](docs/dev_ledger/00_project_state.md) — record v2.14 completion
- Create: closure run report under `docs/dev_ledger/03_run_reports/`
- May read (do not modify): all project files for validation

### Non-Goals

- Starting v2.15 or source expansion
- Modifying pipeline code (all code changes are in items 1–9)
- Running live pilots
- Pushing, creating PR, merging, or tagging
- Creating KillReason records or portfolio mutations

### Implementation Requirements

1. Verify all items (0–10) are complete and committed.
2. Update roadmap overview trackers:
   - State → `complete / closed`
   - Current item → `none / complete`
   - Completed → `11 / 11`
   - Remaining → `0 / 11`
3. Run full validation suite:
   - `.\scripts\dev-test.ps1 -Full -Verbose`
   - `.\scripts\run-controlled-smoke.ps1`
   - `.\scripts\dev-validate-final.ps1`
   - `.\scripts\dev-git-check.ps1`
4. Create closure run report at `docs/dev_ledger/03_run_reports/v2_14_final_validation.md`.
5. Update `docs/dev_ledger/00_project_state.md` to record v2.14 completion and next steps.
6. Verify: no source expansion was performed. No runtime artifacts committed.

### Tests/Validation Expectations

- All tests pass (expected > current test count due to new tests from items 1–9)
- `.\scripts\run-controlled-smoke.ps1` passes (all steps including new quality smoke)
- `.\scripts\dev-validate-final.ps1` passes (all gates green)
- `.\scripts\dev-git-check.ps1` passes (6/6)
- `git status` clean
- `git diff --check` clean

### Definition of Done

- [ ] **10.1** All items (0–10) are complete and committed
- [ ] **10.2** Roadmap overview trackers updated: state → `complete / closed`
- [ ] **10.3** Full validation suite passes (dev-test, controlled-smoke, dev-validate-final, dev-git-check)
- [ ] **10.4** Closure run report exists
- [ ] **10.5** `docs/dev_ledger/00_project_state.md` updated
- [ ] **10.6** Zero source expansion confirmed
- [ ] **10.7** Zero runtime artifacts committed
- [ ] **10.8** `.\scripts\dev-git-check.ps1` passes
- [ ] **10.9** One local commit made with message: `[v2.14] 10 final validation checkpoint`

---

## Quality Targets (v2.14 Success Criteria)

These are the quality targets that v2.14 must meet before a re-evaluation pilot cycle. They are derived from the Pilot Cycle 1 quality problems.

| # | Target | Current (v2.13) | v2.14 Target | Measurement |
|---|--------|-----------------|--------------|-------------|
| QT-1 | Noise rejection rate | 0% (all accepted) | > 0% (some signals classified as noise) | `rejected_count > 0` in Source Quality Report |
| QT-2 | Acceptance rate | 100% (all accepted) | < 100% (not all signals pass) | `acceptance_rate` in Source Quality Report |
| QT-3 | Catch-all clusters | Present (several clusters) | 0 clusters with `catch_all_risk = true` | `catch_all_risk` flag in cluster metadata |
| QT-4 | Cluster title quality | Inconsistent (vague titles present) | All clusters have `title_quality_score >= 0.5` | `title_quality_score` in cluster metadata |
| QT-5 | Opportunity candidates | 0 | >= 1 per qualifying cluster | `opportunity_candidates.json` count |
| QT-6 | Source Quality Report consistency | Contradiction present | `accepted_count + rejected_count = total_count` | Source Quality Report validation |
| QT-7 | Source URL traceability | Clean (all valid) | Clean (all valid) — maintain | `validation_summary.json` |
| QT-8 | Controlled smoke pass | Pass (v2.13 smoke) | Pass (v2.14 quality smoke) | `run-controlled-smoke.ps1` Step 11 |

---

## v2.15 Hook

After v2.14 quality targets are met:

1. **Re-run pilots** on HN + GitHub Issues with the same bounded scope as Pilot Cycle 1.
2. **Re-evaluate** using the v2.13 Go/No-Go Decision Framework.
3. **If GO criteria met:** Proceed to v2.15 Second Pilot Cycle or Cautious Source Expansion Planning.
4. **If CONDITIONAL GO persists:** Further quality tuning in v2.15.
5. **If NO-GO:** Core Discovery Pipeline Repair.
6. **Source expansion remains BLOCKED** until an explicit GO decision.

---

## Validation Commands

Use only the following wrapper scripts for validation during v2.14 execution:

```
.\scripts\dev-git-check.ps1
.\scripts\dev-test.ps1
.\scripts\run-controlled-smoke.ps1
.\scripts\dev-validate-final.ps1
```

Do NOT use chained shell commands for validation. Each validation step must use a single wrapper script.

---

## Git Discipline

- Branch: `ops/v2-13-pilot-cycle-1-run` (reuse for v2.14 planning/docs)
- One local commit per roadmap item during execution.
- Push/PR/merge/tag only when explicitly requested.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Do NOT push, create PR, merge, or tag from this branch unless explicitly approved.

---

*Roadmap v2.14 — Pilot Quality Improvements. Item 7 fix applied; item 8 is next. No source expansion. No runtime artifacts committed.*
