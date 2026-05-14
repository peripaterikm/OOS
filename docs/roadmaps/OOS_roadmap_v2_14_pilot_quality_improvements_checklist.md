# OOS Roadmap v2.14 — Pilot Quality Improvements

**Status:** Active / item 1 ready
**Branch:** `ops/v2-13-pilot-cycle-1-run`
**Created:** 2026-05-14
**Based on:** v2.13 Pilot Cycle 1 CONDITIONAL GO decision
**Parent decision:** [`docs/operations/pilot_cycle_1_conditional_go_summary_v2_13.md`](../operations/pilot_cycle_1_conditional_go_summary_v2_13.md)

---

## 0. Roadmap Overview

### Active Roadmap

- [x] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md`
- [x] **0.2** Current item: `1 — Noise Classification Hardening`
- [x] **0.3** Roadmap state: `active / item 1 ready`
- [x] **0.4** Completed from this roadmap: **1 / 11**
- [x] **0.5** Remaining: **10 / 11**
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

- Wire quality flags into scoring and tiering so noise can be rejected.
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

Wire existing quality flags on [`CandidateSignal`](src/oos/candidate_signal_extractor.py) into actual noise classification decisions. Currently, quality flags exist (e.g., `low_confidence_extraction`, `generic_language`, `missing_actor`) but are decorative — they do not affect scoring, tiering, or acceptance. The pipeline accepts 100% of candidate signals regardless of flags. This item makes quality flags consequential: signals with sufficient quality problems are classified as noise and tiered accordingly.

### Allowed Scope

- Modify: [`src/oos/candidate_signal_extractor.py`](src/oos/candidate_signal_extractor.py) — add noise classification logic
- Modify: [`src/oos/signal_scoring_model_v2.py`](src/oos/signal_scoring_model_v2.py) — integrate quality flags into scoring penalties
- Modify: tests for candidate signal extraction and scoring
- Create: deterministic noise classification function with clear thresholds

### Non-Goals

- Adding new quality flag dimensions (use existing flags only)
- LLM-based noise classification
- Source-specific noise classification (that is deferred to source quality report improvements)
- Auto-killing signals (classification only; founder retains kill authority)
- Modifying the evidence cleaner or RawEvidence model

### Implementation Requirements

1. Define explicit noise classification rules based on existing quality flags:
   - `low_confidence_extraction = true` → noise candidate (unless founder override exists in preference profile)
   - `generic_language = true` + `missing_actor = true` → noise candidate
   - `vendor_promo = true` → noise candidate
   - `no_business_cost = true` → noise candidate
2. Add `noise_classification` field to `CandidateSignal`:
   - Values: `clean`, `suspected_noise`, `confirmed_noise`
   - `suspected_noise` = flags present but not meeting `confirmed_noise` threshold
   - `confirmed_noise` = meets explicit noise classification rules
3. Integrate noise classification into scoring:
   - `suspected_noise` → score penalty (e.g., 0.7x multiplier)
   - `confirmed_noise` → score floor (e.g., max 0.3 score) or exclusion from clusters
4. Update the pilot orchestrator to surface noise counts in run artifacts.
5. Preserve backward compatibility: existing fixture tests must still pass (fixtures may need quality flag annotation).

### Tests/Validation Expectations

- Unit tests verify noise classification rules produce expected outputs for known clean, suspected, and confirmed noise inputs
- Unit tests verify scoring penalties are applied correctly
- Existing signal extraction tests still pass (with fixture updates if needed)
- Controlled smoke test verifies noise counts appear in pilot run artifacts
- At least 15 focused tests

### Definition of Done

- [ ] **1.1** `noise_classification` field exists on `CandidateSignal`
- [ ] **1.2** Noise classification rules function exists and is deterministic
- [ ] **1.3** Scoring integrates noise classification with penalties
- [ ] **1.4** Pilot orchestrator surfaces noise counts
- [ ] **1.5** All existing tests pass (with fixture updates if needed)
- [ ] **1.6** At least 15 focused tests pass
- [ ] **1.7** `.\scripts\dev-git-check.ps1` passes
- [ ] **1.8** One local commit made with message: `[v2.14] 1 noise classification hardening`

---

## 2. Quality Flags to Scoring/Tier Integration

### Intent

Extend the noise classification work (item 1) to full integration with the scoring model and tier system. Quality flags should affect not just a binary noise/clean decision but the full scoring pipeline: component scores, overall score, tier assignment, and cluster eligibility. This ensures that signals with partial quality concerns are down-ranked even if they don't meet the full `confirmed_noise` threshold.

### Allowed Scope

- Modify: [`src/oos/signal_scoring_model_v2.py`](src/oos/signal_scoring_model_v2.py) — per-flag scoring adjustments
- Modify: [`src/oos/pain_cluster.py`](src/oos/pain_cluster.py) — cluster eligibility gates based on signal quality
- Modify: tests for scoring and clustering

### Non-Goals

- Changing the scoring formula weights (only adding quality flag integration)
- Adding new scoring dimensions
- LLM-based scoring
- Tier system redesign

### Implementation Requirements

1. Map each quality flag to a scoring adjustment:
   - `low_confidence_extraction` → `specificity` component penalty (0.5x)
   - `generic_language` → `pain_explicitness` component penalty (0.5x)
   - `missing_actor` → `icp_match` component penalty (0.5x)
   - `no_business_cost` → `cost_signal` component penalty (0.0 — zero out)
   - `vendor_promo` → overall score cap (max 0.4)
2. Add tier eligibility gates:
   - `confirmed_noise` signals are excluded from cluster membership
   - `suspected_noise` signals can join clusters but with reduced weight in cluster scoring
3. Add `quality_penalty_breakdown` to scoring metadata for traceability.
4. Update Source Quality Report to reflect per-signal quality flag distribution.

### Tests/Validation Expectations

- Unit tests verify each quality flag produces the correct scoring adjustment
- Unit tests verify tier gates exclude `confirmed_noise` from clusters
- Unit tests verify `suspected_noise` signals have reduced cluster weight
- Scoring metadata includes `quality_penalty_breakdown`
- At least 20 focused tests

### Definition of Done

- [ ] **2.1** Quality flag → scoring adjustment mapping implemented
- [ ] **2.2** Tier eligibility gates for noise signals implemented
- [ ] **2.3** `quality_penalty_breakdown` in scoring metadata
- [ ] **2.4** Source Quality Report reflects quality flag distribution
- [ ] **2.5** All existing tests pass
- [ ] **2.6** At least 20 focused tests pass
- [ ] **2.7** `.\scripts\dev-git-check.ps1` passes
- [ ] **2.8** One local commit made with message: `[v2.14] 2 quality flags to scoring tier integration`

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

- [ ] **3.1** Deterministic title generation template implemented
- [ ] **3.2** Title validation rules implemented (specificity, length, no catch-all keywords)
- [ ] **3.3** `title_quality_score` field and computation implemented
- [ ] **3.4** Low-quality titles flagged in cluster metadata and Source Quality Report
- [ ] **3.5** All existing tests pass
- [ ] **3.6** At least 15 focused tests pass
- [ ] **3.7** `.\scripts\dev-git-check.ps1` passes
- [ ] **3.8** One local commit made with message: `[v2.14] 3 cluster title generation cleanup`

---

## 4. Cluster Split/Merge Tuning

### Intent

Eliminate catch-all clusters by tuning the split/merge logic in cluster assembly. Pilot Cycle 1 produced clusters that grouped signals sharing only superficial keywords (e.g., "AI", "LLM", "developer") rather than a coherent pain pattern. This item tightens the similarity threshold for cluster membership and adds over-merge detection.

### Allowed Scope

- Modify: [`src/oos/pain_cluster_assembly.py`](src/oos/pain_cluster_assembly.py) — split/merge logic
- Modify: [`src/oos/pain_cluster.py`](src/oos/pain_cluster.py) — cluster cohesion metrics
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
3. Tighten merge threshold:
   - Increase required overlap from current threshold (audit current value first)
   - Require at least 2 of {actor, workflow, object} to match for merge, not just 1
4. Add `split_suggestion` to cluster metadata when auto-split identifies viable sub-groups.
5. Update Source Quality Report with catch-all cluster count.

### Tests/Validation Expectations

- Unit tests verify cohesion score computation
- Unit tests verify over-merge detection triggers at correct thresholds
- Unit tests verify auto-split produces higher-cohesion sub-groups
- Unit tests verify merge threshold prevents superficial-keyword-only merges
- Catch-all clusters flagged in Source Quality Report
- At least 20 focused tests

### Definition of Done

- [ ] **4.1** `cohesion_score` field and computation implemented
- [ ] **4.2** Over-merge detection with `catch_all_risk` flag implemented
- [ ] **4.3** Auto-split suggestion for low-cohesion large clusters implemented
- [ ] **4.4** Merge threshold tightened (at least 2 of {actor, workflow, object} match)
- [ ] **4.5** Source Quality Report includes catch-all cluster count
- [ ] **4.6** All existing tests pass
- [ ] **4.7** At least 20 focused tests pass
- [ ] **4.8** `.\scripts\dev-git-check.ps1` passes
- [ ] **4.9** One local commit made with message: `[v2.14] 4 cluster split merge tuning`

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
- Unit tests verify Markdown formatting consistency
- Markdown output is human-readable and well-structured
- At least 15 focused tests

### Definition of Done

- [ ] **5.1** Cluster quality summary with scores and flags in each cluster section
- [ ] **5.2** Evidence excerpts (first 200 chars) per signal
- [ ] **5.3** Signal-to-noise ratio summary at package top
- [ ] **5.4** Consistent Markdown formatting with quality badges
- [ ] **5.5** Redundant sections removed or collapsed
- [ ] **5.6** All existing tests pass
- [ ] **5.7** At least 15 focused tests pass
- [ ] **5.8** `.\scripts\dev-git-check.ps1` passes
- [ ] **5.9** One local commit made with message: `[v2.14] 5 founder review package clarity`

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

- [ ] **6.1** Deterministic stub produces candidates from qualifying clusters
- [ ] **6.2** Candidate fields populated: title, pain_summary, target_buyer, evidence_ids, source_urls, confidence
- [ ] **6.3** Opportunity synthesis wired into pilot orchestrator
- [ ] **6.4** `opportunity_candidates.json` in pilot run artifacts
- [ ] **6.5** LLM contract hardened (prompt template, validation, version; provider disabled)
- [ ] **6.6** All existing tests pass
- [ ] **6.7** At least 20 focused tests pass
- [ ] **6.8** `.\scripts\dev-git-check.ps1` passes
- [ ] **6.9** One local commit made with message: `[v2.14] 6 opportunity synthesis contract deterministic stub hardening`

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

- [ ] **7.1** `accepted_count` reconciled with quality flags (no contradiction)
- [ ] **7.2** `accepted_with_flags_count` (or renamed `needs_review_count`) correctly computed
- [ ] **7.3** `rejected_count` added to report
- [ ] **7.4** `acceptance_rate` metric added
- [ ] **7.5** All existing tests pass
- [ ] **7.6** At least 10 focused tests pass
- [ ] **7.7** `.\scripts\dev-git-check.ps1` passes
- [ ] **7.8** One local commit made with message: `[v2.14] 7 source quality report contradiction fix`

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

*Roadmap v2.14 — Pilot Quality Improvements. Item 0 planning checkpoint complete; item 1 is next. No source expansion. No runtime artifacts committed.*
