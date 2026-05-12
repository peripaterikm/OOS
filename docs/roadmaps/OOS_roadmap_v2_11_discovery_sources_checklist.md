# OOS Roadmap v2.11 — Operational Discovery Pilot

## 0. Roadmap Overview

### Active Roadmap

- [x] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md`
- [x] **0.2** Current item: `9 — Pilot Run Design and Source Quality Report Contract`
- [ ] **0.3** Roadmap state: `operational_pilot`
- [x] **0.4** Completed from this roadmap: **8 / 10**
- [ ] **0.5** Remaining: **2 / 10**
- [ ] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md` (complete, `8 / 9`, item 5 skipped; tag `v2.10`, merged to main via PR #50)

### Branch and Version

- **Planning branch:** `planning/v2-11-discovery-sources-roadmap` (docs-only)
- **Implementation branch:** `feat/v2-11-discovery-sources-foundation` (active)
- **Based on:** v2.10 / PR #50 / tag `v2.10`
- **Status:** Implementation (item 1 complete)

### Core Concept

Roadmap v2.10 closed recovery/correction capabilities. Roadmap v2.11 was originally scoped as *Discovery Sources and Market Scout Foundation* — expanding and hardening the external signal discovery layer.

**Strategic reorientation (2026-05-12):** v2.11 is re-scoped into an **Operational Discovery Pilot**. See [`docs/decisions/operational_discovery_pilot_reorientation_v2_11.md`](docs/decisions/operational_discovery_pilot_reorientation_v2_11.md) for the full decision.

Items 1–6 (adapter contract, raw evidence schema, source registry, HN hardening plan, GitHub Issues hardening plan, Product Hunt feasibility plan) are complete and remain useful references.

The remaining items (7–10) focus on running a pilot on **HN + GitHub Issues** (with Stack Exchange as optional stretch) to prove the system finds useful business pains before expanding sources further.

Source expansion (Product Hunt, pimenov.ai, Reddit, etc.) is deferred to v2.14+ pending a Go decision in v2.13.

```
    v2.10 delivered                              v2.11 delivers (reoriented)
    ─────────────                               ─────────────────────────
    undo-last implementation                    Source adapter contract (done)
    replace-all gated                           Raw evidence artifact schema (done)
    Terminal encoding audit                     Source registry + allowlist (done)
    UTF-8 expansion audit                       HN connector hardening plan (done)
    Operational polish                          GitHub Issues hardening plan (done)
    Final v2.10 checkpoint                      Product Hunt feasibility plan (done)
                                                --- reorientation ---
                                                Operational Discovery Pilot decision
                                                PainCluster contract + scoring formula
                                                Pilot run design + source quality report
                                                Final v2.11 pilot planning checkpoint
```

### Strategic Principles (Updated for Reorientation)

- **Pilot first, expand later.** Run an operational pilot on HN + GitHub Issues before adding any new sources. Prove the system finds useful business pains.
- **Safe adapters first.** No source without a defined adapter contract and deterministic fixture tests.
- **Traceability always.** Every raw evidence item must carry a stable `source_url`. No source without stable source URL provenance.
- **Deterministic-first preserved.** All logic must produce deterministic output. No live API calls in unit tests. No LLM calls in validation.
- **Advisory-only preserved.** No autonomous portfolio transitions. All decisions remain founder-initiated.
- **No new product layers.** This is pilot validation, not pipeline expansion.
- **No broad scraping.** Each source must have a defined access method (API, RSS, sitemap, static allowlist) that respects ToS/robots.
- **No live API calls in unit tests.** Tests must use deterministic fixtures.

### Explicit Non-Goals (Across All v2.11 Items)

- Adding ANY new sources beyond HN + GitHub Issues + optional Stack Exchange during the pilot
- Implementing Product Hunt now (feasibility plan preserved as reference)
- Implementing pimenov.ai now (deferred to context/intelligence layer)
- Reddit, Discord, Slack, X/Twitter (deferred to v2.14+)
- AlternativeTo, YC, Crunchbase, blogs/newsletters (deferred to v2.14+)
- App marketplaces, job boards (deferred to v2.14+)
- Broad web crawling
- Paywalled source ingestion
- Live API calls in unit tests
- LLM-based source extraction in default tests
- Database or persistent server architecture
- UI/dashboard work
- Replacing existing signal scoring
- New opportunity/portfolio product layers
- Autonomous founder decisions
- Replacing founder review

### LLM Role Statement

LLM integration in discovery sources belongs later (`v2.12+`) unless present only as disabled/future hooks. The v2.11 pipeline must complete deterministically. Existing LLM contracts remain in the codebase but are not wired into source discovery by default.

### Workflow Rules

- Planning branch: `planning/v2-11-discovery-sources-roadmap` (docs-only, this file). Implementation branch: `feat/v2-11-discovery-sources` (future; do not use planning branch for implementation).
- Local commit per roadmap item during implementation.
- Push/PR/merge/tag only when explicitly requested.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Windows-native only: PowerShell, native Python venv, VS Code/Codex.
- No WSL/Linux-first assumptions.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.

### Founder Approval Gate (Planning → Implementation Transition)

- **Planning roadmap merge does not authorize source implementation.** This roadmap is a planning/assessment deliverable only. Merging it to `main` records the plan; it does not grant license to begin implementing connectors, collectors, or any source-layer code.
- **Implementation branch requires explicit founder approval.** No work on `feat/v2-11-discovery-sources` may begin until the founder explicitly approves the transition from planning to implementation.
- **No connector/source implementation begins until explicitly approved.** Items 1–9 produce contracts, plans, feasibility assessments, and runbooks. None of these deliverables are implementation. Actual collector/connector code, fixture updates, and integration into the weekly run are gated behind founder sign-off.
- **Risky sources remain deferred unless separately approved.** Reddit, LinkedIn, Twitter/X, Telegram, review sites, job boards, app marketplaces, Q&A sites, and newsletters are deferred to v2.14+. If any deferred source is considered for early implementation, it requires a separate, explicit founder approval outside this roadmap.

> Roadmap status tracks **10 implementation items** (items 1–10). Item 7 (reorientation decision) is a docs-only decision item. Items 0.1–0.6 are roadmap-state trackers and are not counted in the implementation total.

---

## 0. Roadmap v2.11 Planning

### Intent

Create the official Roadmap v2.11 planning checklist. Docs-only. No source code, tests, scripts, examples, artifacts, or generated outputs.

### Allowed Change Type

- Create: `docs/roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md` (this file)

### Validation Expectation

- `.\scripts\dev-git-check.ps1` passes.
- `git status --short` shows only the new roadmap file before commit.
- After commit, working tree is clean.

### Definition of Done

- [x] **0.0.1** Roadmap v2.11 document exists at `docs/roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md`.
- [ ] **0.0.2** Roadmap state is `planning`; transitions to `ready for implementation` when planning checkpoint closes.
- [ ] **0.0.3** Current item is `1 — Discovery Source Adapter Contract`.
- [ ] **0.0.4** Completed: `0 / 10`.
- [ ] **0.0.5** Remaining: `10 / 10`.
- [x] **0.0.6** Branch `planning/v2-11-discovery-sources-roadmap` exists and is checked out.
- [ ] **0.0.7** All sections present: overview, scope summary, current source baseline, non-goals, numbered checklist (0–10), source-specific requirements, risk gates, validation commands, git discipline, recommended planning order, founder approval gate, v2.12+ hooks.
- [x] **0.0.8** `.\scripts\dev-git-check.ps1` passes.
- [x] **0.0.9** `git status --short` shows only this file before commit.
- [x] **0.0.10** One local commit made with message: `[v2.11] Add discovery sources roadmap`.

### Current Source Baseline

Before v2.11, OOS external signal discovery is limited to:

| Source | Access Method | Status | Collector Adapter |
|--------|--------------|--------|-------------------|
| Hacker News | Algolia Search API (`hn.algolia.com`) | Implemented (v2.3 item 4.1) | `HackerNewsCollector` |
| GitHub Issues | GitHub REST API (`api.github.com`) | Implemented (v2.3 item 4.2) | `GitHubIssuesCollector` |
| Manual JSON/JSONL import | File-based import | Operational | Not a collector; ingestion gateway only |

Additional collector adapters exist as stubs (Stack Exchange, RSS/regulatory from v2.3 item 4.3). **These stubs are out of scope for v2.11 implementation. They exist as future hooks / planning references only.** They are not part of the default weekly run, and no implementation work on stub collectors is authorized under this v2.11 planning roadmap.

**The gap:** OOS processes signals well, but the discovery surface is too narrow. Two sources cannot provide sufficient signal diversity for robust opportunity formation. v2.11 addresses this by defining the adapter contract, hardening existing sources, and planning the first new-source candidates.

---

## 1. Discovery Source Adapter Contract

### Intent

Define a canonical adapter contract that every discovery source must satisfy. The contract specifies the interface, error handling, rate-limit policy, fixture requirements, and `source_url` traceability guarantees. This is the gate through which all new sources must pass.

### Allowed Change Type

- Create: `docs/contracts/discovery_source_adapter_contract.md` (or equivalent contract document)
- Do NOT modify existing source code, tests, scripts, or artifacts.

### Validation Expectation

- Contract document exists and is internally consistent.
- Contract references existing [`source_url_traceability_contract.md`](docs/contracts/source_url_traceability_contract.md).
- Contract defines:
  - Required adapter interface (async/sync, parameters, return type)
  - Fixture-first testing policy (no live API in unit tests)
  - Rate-limit policy (respect `Retry-After`, `X-RateLimit-*` headers)
  - Auth policy (token/env-var pattern, no hardcoded secrets)
  - Error classification (transient vs permanent, retry strategy)
  - `source_url` field requirements (must be stable, resolvable, non-placeholder)
  - `RawEvidence` mapping requirements
  - Noise floor expectations (what constitutes unacceptable noise)
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [x] **1.1** Discovery source adapter contract exists at `docs/contracts/discovery_source_adapter_contract.md`.
- [x] **1.2** Contract defines required interface, fixture policy, rate-limit policy, auth policy, error handling, `source_url` requirements, `RawEvidence` mapping, and noise floor.
- [x] **1.3** Contract references `source_url_traceability_contract.md`.
- [ ] **1.4** `.\scripts\dev-git-check.ps1` passes.
- [ ] **1.5** One local commit made.

---

## 2. Raw Evidence Artifact Schema

### Intent

Define the canonical `RawEvidence` artifact schema that all source adapters produce. This unifies the data format before evidence enters the cleaning/classification pipeline. The schema must support all current and planned source types without per-source field proliferation.

### Allowed Change Type

- Create or update: `docs/contracts/raw_evidence_artifact_schema.md` (or equivalent contract document)
- May reference existing `RawEvidence` model in `src/oos/` but must not modify it in this planning item.
- Do NOT modify source code, tests, scripts, or artifacts.

### Validation Expectation

- Schema document exists and defines:
  - Required fields: `source_url`, `source_type`, `collected_at`, `content_preview`, `metadata`
  - Optional fields: `title`, `author`, `published_at`, `tags`, `comments`, `score`
  - `source_type` enum: existing types + planned types (product_hunt, pimenov_ai)
  - Field validation rules (max lengths, required formats, UTF-8 guarantee)
  - How `source_url` must be structured per source type
  - How `metadata` bag works (per-source extra fields without schema breakage)
- Schema is compatible with existing `RawEvidence` model in `src/oos/`.
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [x] **2.1** Raw evidence artifact schema document exists at `docs/contracts/raw_evidence_artifact_schema.md`.
- [x] **2.2** Schema defines required fields, optional fields, `source_type` enum, validation rules, `source_url` structure, and metadata bag policy.
- [x] **2.3** Schema is compatible with existing `RawEvidence` model (no breaking changes to existing fields).
- [ ] **2.4** `.\scripts\dev-git-check.ps1` passes.
- [ ] **2.5** One local commit made.

---

## 3. Source Registry and Source Allowlist Policy

### Intent

Define the source registry (the canonical list of approved discovery sources) and the source allowlist policy (rules for adding, suspending, or removing sources). The registry gates which sources participate in the default weekly run.

### Allowed Change Type

- Create or update: source registry configuration in `config/` (e.g., `config/source_registry.json`)
- Create: `docs/contracts/source_allowlist_policy.md` (or equivalent)
- Do NOT modify source code, tests, scripts, or artifacts beyond configuration files.

### Validation Expectation

- Source registry file exists and lists all current sources (HN, GitHub Issues) with:
  - `source_id`, `source_type`, `status` (active/inactive/suspended), `collector_adapter`, `access_method`, `rate_limit_policy_ref`, `fixture_path`
- Allowlist policy document defines:
  - Criteria for source acceptance (stable URL pattern, deterministic access method, fixture availability, ToS/robots compliance)
  - Criteria for source suspension (rate-limit abuse, ToS violation, noise rate > threshold)
  - Criteria for source removal
  - Approval process (founder review required for all new sources)
  - Default-disabled policy for all new sources (must pass controlled smoke before `active`)
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [x] **3.1** Source registry file exists at `config/source_registry.json`.
- [x] **3.2** Source allowlist policy document exists at `docs/contracts/source_allowlist_policy.md`.
- [x] **3.3** Registry lists HN and GitHub Issues with correct status and metadata.
- [x] **3.4** Allowlist policy defines acceptance, suspension, removal criteria and approval process.
- [x] **3.5** `.\scripts\dev-git-check.ps1` passes.
- [x] **3.6** One local commit made.

---

## 4. Hacker News Connector Hardening Plan

### Intent

Assess the current Hacker News collector adapter (v2.3 item 4.1) and produce a hardening plan. The assessment covers: current handling quality, noise patterns, missing coverage (comments, Ask HN, Show HN, Launch HN), `source_url` traceability gaps, and rate-limit compliance.

### Allowed Change Type

- Create: `docs/decisions/hn_connector_hardening_plan.md` (or equivalent decision document)
- May read (but not modify): `src/oos/` HN collector adapter, existing HN fixtures.
- Do NOT modify source code, tests, scripts, or artifacts.

### Validation Expectation

- Hardening plan document exists and covers:
  - Current implementation assessment (what works, what doesn't)
  - Preferred API method (official HN API via Firebase, Algolia for search)
  - Coverage gaps: posts vs comments, Ask HN, Show HN, Launch HN
  - `source_url` traceability audit (are all URLs stable and resolvable?)
  - Noise filter recommendations (duplicate detection, low-score thresholds, off-topic filtering)
  - Rate-limit compliance (current behavior vs expected)
  - Fixture quality assessment (are fixtures representative?)
  - Recommended implementation changes (prioritized)
- No implementation in this item. This is assessment and planning only.
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [x] **4.1** HN connector hardening plan exists at `docs/decisions/hacker_news_connector_hardening_plan.md`.
- [x] **4.2** Plan covers: current assessment, preferred API method, coverage gaps, `source_url` audit, noise filters, rate-limit compliance, fixture quality, recommended changes. Also covers: HN source categories, access-method options, source registry alignment, raw evidence mapping, evidence_kind classification rules, source_url traceability, deduplication plan, noise/quality filters, query/collection strategy, validation plan, controlled smoke plan, implementation plan, risks and mitigations, non-goals.
- [x] **4.3** Plan is implementation-ready (each recommendation has clear scope, expected files, and acceptance criteria).
- [ ] **4.4** `.\scripts\dev-git-check.ps1` passes.
- [ ] **4.5** One local commit made.

---

## 5. GitHub Issues Connector Hardening Plan

### Intent

Assess the current GitHub Issues collector adapter (v2.3 item 4.2) and produce a hardening plan. The assessment covers: current handling quality, PR filtering effectiveness, repo allowlist coverage, keyword search quality, label/comment/state capture, and rate-limit/auth compliance.

### Allowed Change Type

- Create: `docs/decisions/github_issues_connector_hardening_plan.md` (or equivalent decision document)
- May read (but not modify): `src/oos/` GitHub Issues collector adapter, existing GitHub fixtures.
- Do NOT modify source code, tests, scripts, or artifacts.

### Validation Expectation

- Hardening plan document exists and covers:
  - Current implementation assessment (what works, what doesn't)
  - PR filtering effectiveness (are PRs reliably excluded from issue results?)
  - Repo allowlist coverage (which repos are configured, which should be added/removed)
  - Keyword search quality (are queries producing relevant signals?)
  - Label/comment/state capture completeness
  - Created/updated timestamp handling
  - `source_url` traceability audit (are all issue URLs stable and resolvable?)
  - Rate-limit/auth policy (token requirements, rate-limit headers, `Retry-After` handling)
  - Fixture quality assessment
  - Recommended implementation changes (prioritized)
- No implementation in this item. This is assessment and planning only.
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [x] **5.1** GitHub Issues connector hardening plan exists at `docs/decisions/github_issues_connector_hardening_plan.md`.
- [x] **5.2** Plan covers: current assessment, PR filtering, repo allowlist, keyword search, label/comment/state capture, timestamps, `source_url` audit, rate-limit/auth, fixture quality, recommended changes. Also covers: GitHub source categories, access-method options, source registry alignment, raw evidence mapping, evidence_kind classification rules, source_url traceability (including removal of `github://` fallback), deduplication plan, noise/quality filters, repo allowlist and query strategy, rate limit and auth policy, comments policy, validation plan, controlled smoke plan, implementation plan, risks and mitigations, non-goals.
- [x] **5.3** Plan is implementation-ready (each recommendation has clear scope, expected files, and acceptance criteria).
- [ ] **5.4** `.\scripts\dev-git-check.ps1` passes.
- [ ] **5.5** One local commit made.

---

## 6. Product Hunt Feasibility and Connector Plan

### Intent

Assess Product Hunt as a new discovery source candidate and produce a connector implementation plan. Product Hunt is treated as a **solution-signal/product-pattern source**, not a pure pain-signal source. It reveals what products are being built, which problems founders are targeting, and what launch patterns are emerging — valuable for opportunity context even when the signals are not direct pain complaints.

### Allowed Change Type

- Create: `docs/decisions/product_hunt_feasibility_and_connector_plan.md` (or equivalent decision document)
- Do NOT implement the connector. Do NOT call the Product Hunt API.
- Do NOT modify source code, tests, scripts, or artifacts.

### Validation Expectation

- Feasibility document exists and covers:
  - Product Hunt API assessment (GraphQL availability, auth requirements, rate limits)
  - Data model mapping: product name, tagline, description, comments, makers, topics, launch date → `RawEvidence` fields
  - `source_url` traceability (product page URL pattern)
  - Anti-hype scoring design (launch-theater filters: vote velocity vs quality, maker reputation signals, comment substance)
  - Fixture strategy (how to create deterministic test fixtures)
  - Access method recommendation (API key requirements, rate limits, cost)
  - Known limitations (API coverage, historical data access, ToS constraints)
  - Implementation scope estimate (files, lines, test surface)
- No implementation. No API calls.
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [x] **6.1** Product Hunt feasibility document exists at `docs/decisions/product_hunt_feasibility_connector_plan.md`.
- [x] **6.2** Document covers: API assessment (Section 5), data model mapping (Section 7), `source_url` traceability (Section 10), anti-hype scoring (Section 12), fixture strategy (Section 4.2), access method (Section 4), known limitations (Section 17), implementation scope (Section 16). Also covers: context (Section 1), feasibility summary (Section 2), current-state assessment (Section 3), source registry alignment (Section 6), evidence kind classification (Section 8), comments policy (Section 9), deduplication plan (Section 11), query/collection strategy (Section 13), validation plan (Section 14), controlled smoke plan (Section 15), recommendation (Section 19), non-goals (Section 18), decision (Section 20).
- [x] **6.3** Document explicitly states: no implementation until API feasibility and auth requirements are documented and approved (Sections 19, 20). Implementation requires explicit founder approval.
- [ ] **6.4** `.\scripts\dev-git-check.ps1` passes.
- [ ] **6.5** One local commit made.

---

## 7. Operational Discovery Pilot Reorientation

### Intent

Re-scope v2.11 from source expansion into an Operational Discovery Pilot. Stop adding new sources. Run a pilot on HN + GitHub Issues (primary) with Stack Exchange as optional stretch. See [`docs/decisions/operational_discovery_pilot_reorientation_v2_11.md`](docs/decisions/operational_discovery_pilot_reorientation_v2_11.md) for the full decision document.

### Allowed Change Type

- Create: `docs/decisions/operational_discovery_pilot_reorientation_v2_11.md`
- Update: this roadmap file.
- Do NOT modify source code, tests, scripts, or artifacts.

### Definition of Done

- [x] **7.1** Reorientation decision document exists at `docs/decisions/operational_discovery_pilot_reorientation_v2_11.md`.
- [x] **7.2** Document covers: context, core decision, why this change, pilot objectives, source scope, deferred sources, PainCluster definition, scoring formula, source quality report, founder review loop, success/failure criteria, updated dev order, non-goals, decision.
- [x] **7.3** Roadmap file updated with reoriented title, trackers, and remaining items 8–10.
- [ ] **7.4** `.\scripts\dev-git-check.ps1` passes.
- [ ] **7.5** One local commit made.

---

## 8. PainCluster Contract and Scoring Formula

### Intent

Define the PainCluster artifact contract and the explicit pain-first scoring formula for the operational pilot. PainCluster is the first-class artifact for cross-source pain consolidation. The scoring formula provides a deterministic, explainable ranking of candidate signals.

### Allowed Change Type

- Create: `docs/contracts/pain_cluster_contract.md` (or equivalent contract document)
- Create: `docs/contracts/pain_first_scoring_contract.md` (or equivalent contract document)
- Do NOT modify source code, tests, scripts, or artifacts.

### Validation Expectation

- PainCluster contract defines:
  - Minimum fields: `cluster_id`, `actor`, `workflow`, `object`, `pain_verb`/`pain_pattern`, `source_evidence_list`, `source_diversity`, `recurrence`, `business_relevance`, `noise_risk`, `representative_quotes`, `linked_candidate_signals`, `linked_opportunity_candidates`
  - Cross-source consolidation rule: same pain across HN + GitHub Issues + Stack Exchange must become one PainCluster
  - Relationship to existing cluster/signal artifacts
- Scoring contract defines:
  - Formula: `overall = 0.25*pain_explicitness + 0.20*recurrence + 0.15*business_cost + 0.15*icp_fit + 0.10*source_reliability + 0.10*freshness + 0.05*actionability - 0.20*noise_risk`
  - Each component: range (0.0–1.0), definition, how to compute deterministically
  - Weight policy: pilot defaults, tunable in v2.12
  - No LLM required for scoring
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [x] **8.1** PainCluster contract exists at `docs/contracts/pain_cluster_contract.md`.
- [x] **8.2** Scoring formula integrated into `docs/contracts/pain_cluster_contract.md` (single combined contract; separate `pain_first_scoring_contract.md` not needed — formula, component definitions, and deterministic computation are all in the PainCluster contract).
- [x] **8.3** PainCluster contract defines all minimum fields (19 fields: cluster_id through notes) and cross-source consolidation rule.
- [x] **8.4** Scoring contract defines formula (`overall = 0.25*pain_explicitness + 0.20*recurrence + 0.15*business_cost + 0.15*icp_fit + 0.10*source_reliability + 0.10*freshness + 0.05*actionability - 0.20*noise_risk`), all 8 component definitions with 0.0/0.5/1.0 scoring guidance, and deterministic computation.
- [ ] **8.5** `.\scripts\dev-git-check.ps1` passes.
- [ ] **8.6** One local commit made.

---

## 9. Pilot Run Design and Source Quality Report Contract

### Intent

Design the operational pilot run: collection schedule, processing pipeline, weekly report artifact, and founder review loop. Define the Source Quality Report contract that gates each pilot run.

### Allowed Change Type

- Create: `docs/runbooks/operational_pilot_run_design.md` (or equivalent runbook)
- Create: `docs/contracts/source_quality_report_contract.md` (or equivalent contract)
- Do NOT modify source code, tests, scripts, or artifacts.

### Validation Expectation

- Pilot run design defines:
  - Collection schedule (frequency, sources, query strategy)
  - Processing pipeline: raw evidence → classify → signal extraction → dedup → clustering → scoring → opportunity framing → founder review package
  - Founder review loop: PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER with feedback into scoring
  - Weekly cadence and artifact delivery
  - No live API calls in unit tests; fixtures for deterministic validation
- Source quality report contract defines:
  - Report sections: raw evidence collected, accepted/weak/noise signals, top pain clusters, opportunity candidates, source quality by source, main noise categories, founder decisions needed, next validation actions
  - Artifact format (JSON + Markdown)
  - Per-source breakdown mandatory
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [ ] **9.1** Pilot run design exists at `docs/runbooks/operational_pilot_run_design.md`.
- [ ] **9.2** Source quality report contract exists at `docs/contracts/source_quality_report_contract.md`.
- [ ] **9.3** Pilot run design covers: schedule, pipeline, founder review loop, weekly cadence, fixture policy.
- [ ] **9.4** Report contract defines all required sections, artifact format, and per-source breakdown.
- [ ] **9.5** `.\scripts\dev-git-check.ps1` passes.
- [ ] **9.6** One local commit made.

---

## 10. Final v2.11 Pilot Planning Checkpoint

### Intent

Close the v2.11 pilot planning phase. Verify all planning artifacts are complete, all documents are internally consistent, and the roadmap is ready to hand off to pilot implementation. Produce a planning closure summary.

### Allowed Change Type

- Update: roadmap overview trackers (0.1–0.6) in this file.
- Create: `docs/dev_ledger/03_run_reports/10.0-roadmap-v2-11-pilot-planning.md` (planning closure run report)
- Do NOT modify source code, tests, scripts, existing artifacts, or any file outside allowed scope.

### Validation Expectation

- All pilot planning items (items 7–9) have their contract/plan/design documents created.
- All documents are internally consistent (no contradictory requirements).
- Cross-references between documents are valid (no broken links).
- `.\scripts\dev-validate-final.ps1` passes.
- `.\scripts\dev-git-check.ps1` passes.
- Roadmap overview trackers (0.1–0.6) are updated to reflect completion.
- Planning closure run report recorded.

### Definition of Done

- [ ] **10.1** All pilot planning items (7–9) are complete and committed.
- [ ] **10.2** Cross-document consistency review complete (no conflicts).
- [ ] **10.3** Roadmap overview trackers (0.1–0.6) updated: state → `ready for pilot implementation`, current item → `none / planning complete`, completed → `10 / 10`, remaining → `0 / 10`.
- [ ] **10.4** Planning closure run report exists at `docs/dev_ledger/03_run_reports/10.0-roadmap-v2-11-pilot-planning.md`.
- [ ] **10.5** `.\scripts\dev-validate-final.ps1` passes.
- [ ] **10.6** `.\scripts\dev-git-check.ps1` passes.
- [ ] **10.7** One local commit made.

---

## Risk Gates

The following gates apply to all v2.11 implementation items. If any gate cannot be satisfied for a given source, that source must remain `inactive` or be removed from the registry.

| # | Gate | Scope |
|---|------|-------|
| G1 | No source without stable `source_url` | Every source adapter |
| G2 | No connector without deterministic fixture tests | Every source adapter |
| G3 | No live API calls in unit tests | All tests |
| G4 | No scraping if ToS/robots risk is unclear | Every new source |
| G5 | No source promoted to default weekly run until controlled smoke passes | Source registry `status: active` |
| G6 | No source accepted if noise rate exceeds threshold and no filter exists | Source quality scoring |
| G7 | No source without defined rate-limit and auth policy | Every source adapter |
| G8 | No source that cannot produce valid `RawEvidence` with `source_url` | Every source adapter |

---

## Validation Commands

Use only the following wrapper scripts for validation during v2.11 implementation:

```
.\scripts\dev-git-check.ps1
.\scripts\dev-test.ps1
.\scripts\run-controlled-smoke.ps1
.\scripts\dev-validate-final.ps1
```

Do NOT use chained shell commands for validation. Each validation step must use a single wrapper script.

---

## Git Discipline

- One roadmap/block branch per work phase.
  - Planning: `planning/v2-11-discovery-sources-roadmap` (this branch; docs-only)
  - Implementation: `feat/v2-11-discovery-sources` (future)
- One local commit per roadmap item during implementation.
- Push/PR/merge/tag only when explicitly requested.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Planning branch only creates the roadmap. Do NOT push, create PR, merge, or tag from this branch unless explicitly approved.

---

## Recommended v2.11 Planning Order (Reoriented)

This roadmap is a **pilot planning roadmap**, not an implementation branch. Items 1–6 (completed) produced source contracts and feasibility plans. Items 7–10 (remaining) focus on operational pilot design. No source code, connector implementation, or fixture changes are authorized by this roadmap.

1. **Source contracts and hardening plans** (items 1–6, COMPLETE)
   - Adapter contract, raw evidence schema, source registry, HN hardening plan, GitHub Issues hardening plan, Product Hunt feasibility plan are all complete and remain useful references.
2. **Reorientation decision** (item 7, COMPLETE)
   - Docs-only decision to re-scope v2.11 from source expansion to operational pilot.
3. **PainCluster contract and scoring** (item 8, COMPLETE)
   - Define PainCluster artifact, cross-source consolidation, and explicit pain-first scoring formula.
4. **Pilot run design and source quality report** (item 9, CURRENT)
   - Define operational pilot run schedule, pipeline, founder review loop, and source quality report contract.
5. **Final pilot planning checkpoint** (item 10)
   - Close pilot planning phase; verify all artifacts; produce closure run report.
6. **Defer all new sources** (v2.14+ conditional on Go decision in v2.13)
   - Product Hunt, pimenov.ai, Reddit, review sites, job boards, LinkedIn/X/Telegram, app marketplaces, Q&A sites, newsletters, Discord, Slack remain deferred.

---

## Deferred Sources (v2.14+ Only If Pilot Passes Go Decision)

The following source candidates are explicitly deferred to v2.14+ and are conditional on a Go decision in v2.13 after the operational pilot completes. They are noted here to prevent scope creep:

| Source | Reason for Deferral | Earliest Roadmap |
|--------|-------------------|-----------------|
| Reddit | API volatility, high noise, moderation complexity | v2.14+ (conditional) |
| Discord | No stable public API; scraping risk | v2.14+ (conditional) |
| Slack | No public API for community content; workspace access barriers | v2.14+ (conditional) |
| X/Twitter | API cost/restrictions; legal review required | v2.14+ (conditional) |
| Product Hunt | Solution-pattern source; feasibility plan preserved as reference | v2.14+ (conditional) |
| AlternativeTo | Review-based; signal-type fit unclear | v2.14+ (conditional) |
| YC RFS / YC companies | Curated lists; not a structured pain feed | v2.14+ (conditional) |
| Crunchbase | Company data, not pain signals | v2.14+ (conditional) |
| Blogs / newsletters | Ingest pipeline complexity; copyright considerations | v2.14+ (conditional) |
| pimenov.ai | Expert/context source, not direct pain source; deferred to context/intelligence layer | v2.14+ (conditional) |
| G2/Capterra/review sites | ToS review required; scraping risk; paywall barriers | v2.14+ (conditional) |
| Job boards (LinkedIn, Indeed, etc.) | Scraping risk; ToS barriers | v2.14+ (conditional) |
| App marketplaces (Google Play, App Store) | Review-based signals; scraping risk | v2.14+ (conditional) |
| Stack Exchange / Stack Overflow | Optional stretch source for pilot; reassess inclusion after 1–2 weekly cycles | v2.12 (if pilot allows) |

---

*Roadmap v2.11 — Operational Discovery Pilot. Planning phase. Do not implement sources beyond pilot scope.*
