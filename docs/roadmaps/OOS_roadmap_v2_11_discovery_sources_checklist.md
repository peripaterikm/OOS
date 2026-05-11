# OOS Roadmap v2.11 — Discovery Sources and Market Scout Foundation

## 0. Roadmap Overview

### Active Roadmap

- [x] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md`
- [x] **0.2** Current item: `4 — Hacker News Connector Hardening Plan`
- [ ] **0.3** Roadmap state: `implementation`
- [ ] **0.4** Completed from this roadmap: **3 / 10**
- [ ] **0.5** Remaining: **7 / 10**
- [ ] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md` (complete, `8 / 9`, item 5 skipped; tag `v2.10`, merged to main via PR #50)

### Branch and Version

- **Planning branch:** `planning/v2-11-discovery-sources-roadmap` (docs-only)
- **Implementation branch:** `feat/v2-11-discovery-sources-foundation` (active)
- **Based on:** v2.10 / PR #50 / tag `v2.10`
- **Status:** Implementation (item 1 complete)

### Core Concept

Roadmap v2.10 closed recovery/correction capabilities. Roadmap v2.11 shifts focus upstream: expanding and hardening the external signal discovery layer.

OOS already has a deterministic processing pipeline (signal → evidence → cluster → opportunity → founder decision). The pipeline works well, but the external discovery layer is too narrow. Current automated/semi-automated external sources are effectively:

- **Hacker News** (via Algolia API)
- **GitHub Issues** (via GitHub REST API)

Plus manual JSON/JSONL import as an ingestion gateway, not a true source.

v2.11 defines the foundation for connecting additional signal sources safely, deterministically, and with [`source_url`](docs/contracts/source_url_traceability_contract.md) traceability. It does not build new product layers. It expands the top of the funnel.

```
    v2.10 delivered                              v2.11 delivers
    ─────────────                               ─────────────
    undo-last implementation                    Source adapter contract
    replace-all gated                           Raw evidence artifact schema
    Terminal encoding audit                     Source registry + allowlist
    UTF-8 expansion audit                       HN connector hardening plan
    Operational polish                          GitHub Issues connector hardening plan
    Final v2.10 checkpoint                      Product Hunt feasibility + connector plan
                                                pimenov.ai feasibility + connector plan
                                                Source quality scoring + weekly report
                                                Controlled discovery smoke design
                                                Final v2.11 planning checkpoint
```

### Strategic Principles

- **Safe adapters first.** No source without a defined adapter contract and deterministic fixture tests.
- **Traceability always.** Every raw evidence item must carry a stable `source_url`. No source without stable source URL provenance.
- **Deterministic-first preserved.** All logic must produce deterministic output. No live API calls in unit tests. No LLM calls in validation.
- **Advisory-only preserved.** No autonomous portfolio transitions. All decisions remain founder-initiated.
- **No new product layers.** This is source expansion and hardening, not pipeline expansion.
- **No broad scraping.** Each source must have a defined access method (API, RSS, sitemap, static allowlist) that respects ToS/robots.
- **No live API calls in unit tests.** Tests must use deterministic fixtures.

### Explicit Non-Goals (Across All v2.11 Items)

- Reddit implementation (deferred to v2.12+ pending feasibility review)
- LinkedIn/X/Telegram scraping (deferred to v2.12+ pending legal/access review)
- Broad web crawling
- Paywalled source ingestion
- Live API calls in unit tests
- LLM-based source extraction in default tests
- Database or persistent server architecture
- UI/dashboard work
- Replacing existing signal scoring
- New opportunity/portfolio product layers
- Autonomous founder decisions
- G2/Capterra/review sites (deferred to v2.12+)
- Job boards (deferred to v2.12+)
- Stack Overflow / Q&A sites (deferred to v2.12+)
- App marketplaces (deferred to v2.12+)
- Newsletters/media bundle (deferred to v2.12+)

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
- **Risky sources remain deferred unless separately approved.** Reddit, LinkedIn, Twitter/X, Telegram, review sites, job boards, app marketplaces, Q&A sites, and newsletters are deferred to v2.12+. If any deferred source is considered for early implementation, it requires a separate, explicit founder approval outside this roadmap.

> Roadmap status tracks **10 implementation items** (items 1–10). Item 0 (planning checkpoint) is the current planning item and is not counted in the implementation total. Items 0.1–0.6 are roadmap-state trackers and are not counted in the implementation total.

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

- [ ] **4.1** HN connector hardening plan exists at `docs/decisions/hn_connector_hardening_plan.md`.
- [ ] **4.2** Plan covers: current assessment, preferred API method, coverage gaps, `source_url` audit, noise filters, rate-limit compliance, fixture quality, recommended changes.
- [ ] **4.3** Plan is implementation-ready (each recommendation has clear scope, expected files, and acceptance criteria).
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

- [ ] **5.1** GitHub Issues connector hardening plan exists at `docs/decisions/github_issues_connector_hardening_plan.md`.
- [ ] **5.2** Plan covers: current assessment, PR filtering, repo allowlist, keyword search, label/comment/state capture, timestamps, `source_url` audit, rate-limit/auth, fixture quality, recommended changes.
- [ ] **5.3** Plan is implementation-ready (each recommendation has clear scope, expected files, and acceptance criteria).
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

- [ ] **6.1** Product Hunt feasibility document exists at `docs/decisions/product_hunt_feasibility_and_connector_plan.md`.
- [ ] **6.2** Document covers: API assessment, data model mapping, `source_url` traceability, anti-hype scoring, fixture strategy, access method, known limitations, implementation scope.
- [ ] **6.3** Document explicitly states: no implementation until API feasibility and auth requirements are documented and approved.
- [ ] **6.4** `.\scripts\dev-git-check.ps1` passes.
- [ ] **6.5** One local commit made.

---

## 7. pimenov.ai Feasibility and Connector Plan

### Intent

Assess [pimenov.ai](https://pimenov.ai) as a new discovery source candidate and produce a connector implementation plan. pimenov.ai is a curated Russian-language resource covering AI use-cases, implementations, and industry context. It is treated as a **curated AI/use-case/context source**, not a raw pain-signal source. Its value is in trend awareness, idea expansion, and context enrichment for AI-adjacent opportunities.

### Allowed Change Type

- Create: `docs/decisions/pimenov_ai_feasibility_and_connector_plan.md` (or equivalent decision document)
- Do NOT implement the connector. Do NOT scrape the site.
- Do NOT modify source code, tests, scripts, or artifacts.

### Validation Expectation

- Feasibility document exists and covers:
  - Site structure analysis (blog, knowledge base, cases sections — from publicly visible structure only)
  - Access method recommendation: RSS feed availability, sitemap presence, static page allowlist
  - Data model mapping: title, URL, section, tags/categories (if available), publication/update date (if available), summary, extracted AI-use-case pattern → `RawEvidence` fields
  - `source_url` traceability (page URL pattern)
  - Signal type decision: should this source produce raw signals, trend/context notes, or idea-expansion evidence? Recommended default.
  - Access policy: safe/static/RSS/sitemap-based only; no broad crawling; no scraping of pages not in allowlist
  - Language handling (Russian-language content; UTF-8 guarantee; optional translation note)
  - Fixture strategy (how to create deterministic test fixtures from RSS/sitemap/content)
  - Known limitations (language barrier, curation bias, update frequency)
  - Implementation scope estimate (files, lines, test surface)
- No implementation. No scraping. No live HTTP requests.
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [ ] **7.1** pimenov.ai feasibility document exists at `docs/decisions/pimenov_ai_feasibility_and_connector_plan.md`.
- [ ] **7.2** Document covers: site structure, access method (RSS/sitemap/static), data model mapping, `source_url` traceability, signal type decision, access policy, language handling, fixture strategy, known limitations, implementation scope.
- [ ] **7.3** Document explicitly states: no broad scraping; only safe/static/RSS/sitemap-based access.
- [ ] **7.4** `.\scripts\dev-git-check.ps1` passes.
- [ ] **7.5** One local commit made.

---

## 8. Source Quality Scoring and Weekly Source Report

### Intent

Define a source quality scoring framework that evaluates each discovery source on signal relevance, noise rate, traceability compliance, and yield consistency. Produce a weekly source report artifact that the founder can review to decide whether to keep, suspend, or adjust source configuration.

### Allowed Change Type

- Create: `docs/contracts/source_quality_scoring_contract.md` (or equivalent)
- Create: `docs/contracts/weekly_source_report_contract.md` (or equivalent)
- Do NOT modify source code, tests, scripts, or artifacts.

### Validation Expectation

- Source quality scoring contract defines:
  - Quality dimensions: `signal_relevance_score`, `noise_rate`, `traceability_compliance` (no placeholder URNs), `yield_consistency` (week-over-week variance), `distinct_signal_count`
  - Scoring formula (deterministic, no LLM)
  - Thresholds: `healthy`, `warning`, `unhealthy`
  - Per-source scoring, not aggregate-only
- Weekly source report contract defines:
  - Report artifact format (JSON + Markdown)
  - Fields: `run_id`, `run_timestamp`, per-source scores, aggregate summary, source health trends, recommendations (keep/suspend/adjust)
  - CLI command to generate the report (e.g., `--source-report`)
  - No live API/LLM calls during report generation
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [ ] **8.1** Source quality scoring contract exists at `docs/contracts/source_quality_scoring_contract.md`.
- [ ] **8.2** Weekly source report contract exists at `docs/contracts/weekly_source_report_contract.md`.
- [ ] **8.3** Scoring contract defines quality dimensions, formula, and thresholds.
- [ ] **8.4** Report contract defines artifact format, fields, CLI command, and no-live-calls policy.
- [ ] **8.5** `.\scripts\dev-git-check.ps1` passes.
- [ ] **8.6** One local commit made.

---

## 9. Controlled Discovery Smoke Design

### Intent

Design the controlled smoke test that validates new discovery sources before they are promoted to the default weekly run. The smoke test must run deterministically (fixture-based), verify `source_url` traceability, measure noise rate, and produce a pass/fail report. Every new source must pass controlled smoke before its status changes from `inactive` to `active` in the source registry.

### Allowed Change Type

- Create: `docs/runbooks/controlled_discovery_smoke_test.md` (or equivalent runbook)
- Do NOT create test files, scripts, or artifacts in this item.
- Do NOT modify source code.

### Validation Expectation

- Smoke test runbook defines:
  - Purpose: gate new sources before default weekly run inclusion
  - Prerequisites: source adapter implemented, fixtures available, source in registry with `status: inactive`
  - Test phases:
    1. Fixture load and validate (fixtures must be valid `RawEvidence`)
    2. Adapter dry-run (run collector with fixtures, no live API)
    3. `source_url` traceability check (no placeholder URNs, all URLs stable)
    4. Noise rate measurement (deterministic classifier, threshold check)
    5. Output artifact validation (valid JSON, required fields present)
    6. Pass/fail determination
  - Pass criteria:
    - All fixtures load without error
    - 100% `source_url` traceability (no `urn:oos:` placeholders)
    - Noise rate below configured threshold (per source type)
    - Output artifacts are valid and complete
  - Fail criteria and required actions
  - Integration with existing `.\scripts\run-controlled-smoke.ps1` or new script if needed
- `.\scripts\dev-git-check.ps1` passes.

### Definition of Done

- [ ] **9.1** Controlled discovery smoke runbook exists at `docs/runbooks/controlled_discovery_smoke_test.md`.
- [ ] **9.2** Runbook defines: purpose, prerequisites, test phases (fixture, dry-run, traceability, noise, output, pass/fail), pass/fail criteria, required actions on failure.
- [ ] **9.3** Runbook references existing smoke infrastructure where applicable.
- [ ] **9.4** `.\scripts\dev-git-check.ps1` passes.
- [ ] **9.5** One local commit made.

---

## 10. Final v2.11 Planning Checkpoint

### Intent

Close the v2.11 planning phase. Verify all planning artifacts are complete, all documents are internally consistent, and the roadmap is ready to hand off to implementation. Produce a planning closure summary.

### Allowed Change Type

- Update: roadmap overview trackers (0.1–0.6) in this file.
- Create: `docs/dev_ledger/03_run_reports/10.0-roadmap-v2-11-planning.md` (planning closure run report)
- Do NOT modify source code, tests, scripts, existing artifacts, or any file outside allowed scope.

### Validation Expectation

- All 9 planning items (items 1–9) have their contract/plan/design documents created.
- All documents are internally consistent (no contradictory requirements).
- Cross-references between documents are valid (no broken links).
- `.\scripts\dev-validate-final.ps1` passes.
- `.\scripts\dev-git-check.ps1` passes.
- Roadmap overview trackers (0.1–0.6) are updated to reflect completion.
- Planning closure run report recorded.

### Definition of Done

- [ ] **10.1** All planning items (1–9) are complete and committed.
- [ ] **10.2** Cross-document consistency review complete (no conflicts).
- [ ] **10.3** Roadmap overview trackers (0.1–0.6) updated: state → `ready for implementation`, current item → `none / planning complete`, completed → `10 / 10`, remaining → `0 / 10`.
- [ ] **10.4** Planning closure run report exists at `docs/dev_ledger/03_run_reports/10.0-roadmap-v2-11-planning.md`.
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

## Recommended v2.11 Planning Order

This roadmap is a **planning roadmap**, not an implementation branch. All items 1–9 produce planning/design/assessment deliverables (contracts, plans, feasibility documents, runbooks). No source code, connector implementation, or fixture changes are authorized by this roadmap.

1. **Contract/schema/registry first** (items 1, 2, 3)
   - The adapter contract, raw evidence schema, and source registry are prerequisites for all source work.
2. **HN/GitHub hardening plans next** (items 4, 5)
   - Assessing and planning hardening for existing sources before planning new ones ensures the foundation is solid.
3. **Product Hunt and pimenov.ai as first new-source candidates** (items 6, 7)
   - Feasibility and connector plans for the first new sources. Implementation follows in a future implementation branch (v2.11 or early v2.12) depending on scope.
4. **Source quality reporting** (item 8)
   - Quality scoring and weekly report contracts provide visibility into source health once implemented.
5. **Controlled smoke** (item 9)
   - Smoke design runbook gates new sources before production inclusion once implemented.
6. **Defer risky sources** (v2.12+)
   - Reddit, review sites, job boards, LinkedIn/X/Telegram remain deferred.

---

## v2.12+ Hooks

The following source candidates are explicitly deferred to v2.12 or later. They are noted here to prevent scope creep during v2.11:

| Source | Reason for Deferral | Earliest Roadmap |
|--------|-------------------|-----------------|
| Reddit | Requires feasibility review (API changes, ToS, noise management) | v2.12+ |
| G2/Capterra/review sites | Requires ToS review; scraping risk; paywall/authentication barriers | v2.12+ |
| Job boards (LinkedIn, Indeed, etc.) | Scraping risk; ToS barriers; structured data access unclear | v2.12+ |
| Stack Overflow / Q&A sites | API available but signal type fit needs analysis | v2.12+ |
| App marketplaces (Google Play, App Store, etc.) | Review-based signals; scraping risk | v2.12+ |
| Newsletters/media bundle | Ingest pipeline complexity; copyright considerations | v2.12+ |
| Telegram | API access model; scraping risk; language/region considerations | v2.12+ |
| Twitter/X | API access cost and restrictions changed significantly; legal review required | v2.12+ |
| LinkedIn | Scraping prohibited by ToS; API access restricted; legal review required | v2.12+ |

---

*Roadmap v2.11 — Discovery Sources and Market Scout Foundation. Planning phase. Do not implement.*
