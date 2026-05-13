# OOS Roadmap v2.12 — Operational Discovery Pilot Implementation

## 0. Roadmap Overview

### Active Roadmap

- [x] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_12_operational_discovery_pilot_checklist.md`
- [x] **0.2** Current item: `8 — Controlled Pilot Smoke`
- [x] **0.3** Roadmap state: `implementation in progress`
- [x] **0.4** Completed from this roadmap: **7 / 10**
- [x] **0.5** Remaining: **3 / 10**
- [ ] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md` (complete, `10 / 10`, tag `v2.11`, merged to main via PR #51)

### Branch and Version

- **Planning branch:** `planning/v2-12-operational-discovery-pilot-roadmap` (docs-only; this file)
- **Recommended implementation branch:** `feat/v2-12-operational-discovery-pilot`
- **Based on:** v2.11 / PR #51 / tag `v2.11`
- **Status:** Planning
- **Goal:** Reach Operational Discovery Pilot ready state

### Core Concept

Roadmap v2.11 was a planning/design block. It delivered the source adapter contract, raw evidence schema, source registry, HN and GitHub Issues hardening plans, Product Hunt feasibility plan, PainCluster contract with scoring formula, operational discovery pilot run contract, and the strategic reorientation decision to pilot-first. All contracts are finalized; no code was implemented under v2.11.

Roadmap v2.12 implements the minimal controlled discovery pilot — the end-to-end pipeline from raw evidence through candidate signals, pain clusters, scoring, opportunity candidates, source quality report, and founder review package. The pilot is scoped to **HN + GitHub Issues only** with Stack Exchange as strictly optional/stretch.

```
    v2.11 delivered (planning)                    v2.12 delivers (implementation)
    ─────────────────────────                     ───────────────────────────────
    Source adapter contract                       PainCluster model + scoring
    Raw evidence artifact schema                  HN RawEvidence hardening
    Source registry + allowlist policy            GitHub Issues RawEvidence hardening
    HN connector hardening plan                   Cross-source dedupe + cluster assembly
    GitHub Issues hardening plan                  Source Quality Report
    Product Hunt feasibility plan                 Founder Review Package
    Operational Discovery Pilot reorientation     Operational Discovery Pilot orchestrator
    PainCluster contract + scoring formula        Controlled pilot smoke
    Pilot run design + source quality report      Final v2.12 checkpoint
    Final v2.11 pilot planning checkpoint
```

### Strategic Principles

- **Pilot first, expand later.** Run a controlled operational pilot on HN + GitHub Issues. Prove the system finds useful business pains before adding any new sources.
- **Contracts drive implementation.** v2.12 implements what v2.11 specified. The PainCluster contract, pilot run contract, and source hardening plans are the authoritative specs.
- **Traceability always.** Every raw evidence item must carry a stable `source_url`. Every opportunity candidate must trace back to source URLs. No placeholder URLs.
- **Deterministic-first preserved.** All logic must produce deterministic output. No live API calls in unit tests. No LLM calls in validation. Fixture-first.
- **Advisory-only preserved.** No autonomous portfolio transitions. All decisions remain founder-initiated. Founder review is mandatory.
- **No new product layers.** This is pilot pipeline implementation, not pipeline expansion.
- **No source expansion.** HN + GitHub Issues only. Stack Exchange is strictly optional/stretch.
- **No live APIs in unit tests.** Tests must use deterministic fixtures.
- **No LLM required for scoring.** Scoring formula is entirely deterministic per the PainCluster contract.

### Explicit Non-Goals (Across All v2.12 Items)

- Adding ANY new sources beyond HN + GitHub Issues (+ optional Stack Exchange stretch)
- Implementing Product Hunt (feasibility plan preserved as reference)
- Implementing pimenov.ai (deferred to context/intelligence layer)
- Reddit, Discord, Slack, X/Twitter (deferred to v2.14+)
- AlternativeTo, YC, Crunchbase, blogs/newsletters (deferred to v2.14+)
- App marketplaces, job boards (deferred to v2.14+)
- Broad web crawling or scraping
- Paywalled source ingestion
- Live API calls in unit tests
- LLM-based source extraction in default tests
- LLM validation in default tests
- Autonomous founder decisions
- Database or persistent server architecture
- UI/dashboard work
- Replacing existing signal scoring (PainCluster scoring is additive, cluster-level)
- Replacing founder review
- New opportunity/portfolio product layers

### LLM Role Statement

LLM integration remains disabled in the v2.12 default pipeline. All scoring is deterministic. All clustering is rule-based (pain pattern decomposition). Existing LLM contracts remain in the codebase as future hooks but are not wired into discovery by default.

### Workflow Rules

- Planning branch: `planning/v2-12-operational-discovery-pilot-roadmap` (docs-only, this file).
- Implementation branch: `feat/v2-12-operational-discovery-pilot` (future; do not use planning branch for implementation).
- One local commit per roadmap item during implementation.
- Push/PR/merge/tag only when explicitly requested.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Windows-native only: PowerShell, native Python venv, VS Code/Codex.
- No WSL/Linux-first assumptions.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.

### Founder Approval Gate (Planning → Implementation Transition)

- **Planning roadmap merge does not authorize implementation.** This roadmap is a planning/checklist deliverable only. Merging it to `main` records the plan; it does not grant license to begin implementing code.
- **Implementation branch requires explicit founder approval.** No work on `feat/v2-12-operational-discovery-pilot` may begin until the founder explicitly approves the transition from planning to implementation.
- **No code, test, script, or artifact changes are authorized by this planning item.** Items 1–9 define implementation scope. None of these definitions are implementation.
- **Live source access requires explicit founder approval.** Default is fixture mode.
- **Stack Exchange stretch requires explicit founder approval.** Default is excluded from pilot.

> Roadmap status tracks **10 implementation items** (items 0–9). Item 0 (planning checkpoint) is the planning closure gate. Items 1–9 are the implementation checklist.

---

## 0. Planning Checkpoint

### Intent

Create the official Roadmap v2.12 planning checklist. Docs-only. No source code, tests, scripts, examples, artifacts, or generated outputs. This item closes the planning phase and gates the start of implementation.

### Allowed Change Type

- Create: `docs/roadmaps/OOS_roadmap_v2_12_operational_discovery_pilot_checklist.md` (this file)

### Validation Expectation

- `.\scripts\dev-git-check.ps1` passes.
- `git status --short` shows only the new roadmap file before commit.
- After commit, working tree is clean.

### Definition of Done

- [ ] **0.0.1** Roadmap v2.12 document exists at `docs/roadmaps/OOS_roadmap_v2_12_operational_discovery_pilot_checklist.md`.
- [ ] **0.0.2** Roadmap state is `planning`; transitions to `ready for implementation` when planning checkpoint closes.
- [ ] **0.0.3** Current item is `0 — Planning checkpoint`.
- [ ] **0.0.4** Completed: `0 / 10`.
- [ ] **0.0.5** Remaining: `10 / 10`.
- [ ] **0.0.6** Branch `planning/v2-12-operational-discovery-pilot-roadmap` exists and is checked out.
- [ ] **0.0.7** All sections present: overview, scope summary, current baseline, non-goals, numbered checklist (0–9), pilot readiness criteria, pilot failure criteria, source scope gates, founder approval gates, validation commands, git discipline, recommended implementation branch, v2.13 hook.
- [ ] **0.0.8** `.\scripts\dev-git-check.ps1` passes.
- [ ] **0.0.9** `git status --short` shows only this file before commit.
- [ ] **0.0.10** One local commit made with message: `[v2.12] Add operational discovery pilot roadmap`.

### Scope Summary

v2.12 implements the minimal controlled discovery pilot specified by the v2.11 contracts:

- **Primary sources:** Hacker News and GitHub Issues.
- **Stack Exchange / Stack Overflow:** Optional/stretch only. Default: excluded from first 1–2 pilot runs.
- **Pipeline:** RawEvidence → CandidateSignals → PainClusters → Scoring → OpportunityCandidates → SourceQualityReport → FounderReviewPackage.
- **Goal:** Test whether OOS can find useful business pains and opportunity candidates from a limited, well-understood source set.
- **No broad source expansion.** All additional sources remain deferred to v2.14+ conditional on a Go decision in v2.13.
- **No live APIs in unit tests.** Fixture-first. Live mode is opt-in only.
- **No LLM validation in default tests.** All scoring is deterministic.
- **Source URL traceability remains mandatory.** Every evidence item carries a real `http(s)://` URL.
- **Founder review remains mandatory.** All decisions are founder-initiated.

### Current Baseline

| Capability | Status | Detail |
|------------|--------|--------|
| HN collector adapter | Exists, needs hardening | [`src/oos/hn_algolia_collector.py`](../../src/oos/hn_algolia_collector.py) — functional but lacks evidence_kind, noise/quality flags, source quality summary |
| GitHub Issues collector adapter | Exists, needs hardening | [`src/oos/github_issues_collector.py`](../../src/oos/github_issues_collector.py) — functional but PR filtering incomplete, uses `github://` fallback, lacks repo allowlist enforcement |
| RawEvidence model | Exists | [`src/oos/models.py`](../../src/oos/models.py:77) — defined and tested |
| CandidateSignal model | Exists | [`src/oos/models.py`](../../src/oos/models.py:228) — defined and tested |
| PainCluster contract | Specified, not implemented | [`docs/contracts/pain_cluster_contract.md`](../contracts/pain_cluster_contract.md) — 19 fields, scoring formula, validation rules |
| Operational Discovery Pilot Run contract | Specified, not implemented | [`docs/contracts/operational_discovery_pilot_run_contract.md`](../contracts/operational_discovery_pilot_run_contract.md) — 14-phase lifecycle, source quality report, founder review loop |
| Source Quality Report | Specified, not implemented | Defined in pilot run contract Sections 10–11 — 8 report sections, 18 metrics |
| Cross-source deduplication | Not implemented | Near-duplicate pain patterns across HN + GitHub Issues must become one cluster |
| Founder Review Package | Not implemented | PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER with feedback loop |
| Controlled smoke | Partial | Existing [`tests/test_controlled_weekly_run_smoke.py`](../../tests/test_controlled_weekly_run_smoke.py) covers base weekly cycle but not discovery pilot path |
| Source registry | Exists | [`config/source_registry.json`](../../config/source_registry.json) — lists HN (`source_id: hacker_news`, `source_type: discussion`) and GitHub Issues (`source_id: github_issues`, `source_type: issue_tracker`) with status and metadata |

---

## 1. PainCluster Model and Scoring Implementation

### Intent

Implement the PainCluster artifact/model, the deterministic scoring formula, and the promotion thresholds as specified in [`docs/contracts/pain_cluster_contract.md`](../contracts/pain_cluster_contract.md). PainCluster is the first-class artifact for cross-source pain consolidation. This is the foundational implementation item — all downstream pilot components depend on it.

### Allowed Change Type

- Create: `src/oos/pain_cluster.py` (new module)
- Create: `tests/test_pain_cluster.py` (fixture tests)
- May read (do not modify): `docs/contracts/pain_cluster_contract.md`, `src/oos/models.py`, `src/oos/artifact_store.py`
- Do NOT modify existing source code outside the new module.
- Do NOT modify tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| `src/oos/pain_cluster.py` | Create | PainCluster model, scoring formula, status lifecycle, validation |
| `tests/test_pain_cluster.py` | Create | Fixture tests: model roundtrip, scoring computation, validation rules, status transitions |
| `docs/contracts/pain_cluster_contract.md` | Read-only reference | Authoritative spec for all 19 fields, scoring formula, thresholds |

### Implementation Requirements

- [x] **1.1** Implement `PainCluster` dataclass/model with all 19 minimum fields from contract Section 3.1.
- [x] **1.2** Implement deterministic `cluster_id` generation: `pc_` + SHA-256 of normalized `actor|workflow|object|pain_pattern` truncated to 16 hex chars.
- [x] **1.3** Implement `source_evidence_list` with all 12 evidence entry fields from contract Section 6.1.
- [x] **1.4** Implement the explicit scoring formula (contract Section 11):

```
overall = clamp(0.0, 1.0,
     0.25 * pain_explicitness
   + 0.20 * recurrence
   + 0.15 * business_cost
   + 0.15 * icp_fit
   + 0.10 * source_reliability
   + 0.10 * freshness
   + 0.05 * actionability
   - 0.20 * noise_risk
)
```

- [x] **1.5** Implement all 8 scoring component computations with 0.0–1.0 normalization (contract Sections 12.1–12.8).
- [x] **1.6** Implement `recurrence` normalization: `min(1.0, raw_recurrence_count / 5.0)` with cross-source bonus of 1.15× when `source_diversity >= 2`.
- [x] **1.7** Implement `freshness` decay formula using newest evidence `created_at` (contract Section 12.6).
- [x] **1.8** Implement multi-source `source_reliability` as weighted average by evidence count (contract Section 13.3).
- [x] **1.9** Implement promotion thresholds (contract Section 15):
  - `>= 0.70` → candidate
  - `0.50–0.69` → needs_more_evidence / weak
  - `< 0.50` → noise / park
  - Any score with `noise_risk >= 0.80` → noise regardless of overall.
- [x] **1.10** Implement automatic status assignment (contract Section 14.3).
- [x] **1.11** Implement validation: 16 fail rules and 8 warn rules from contract Section 19.
- [x] **1.12** Write fixture tests covering:
  - Model construction and field validation for all 19 fields.
  - `cluster_id` determinism (same inputs → same ID).
  - Scoring formula correctness with known inputs and expected outputs.
  - All 8 scoring component edge cases (0.0, 0.5, 1.0).
  - Threshold boundaries (0.69, 0.70, 0.50, etc.).
  - Cross-source diversity bonus in recurrence scoring.
  - Freshness decay at age boundaries (7, 30, 90, 360 days).
  - Validation: fail rules block, warn rules warn.
  - Status transitions: new → accepted, new → noise (auto), new → weak (auto).
  - Serialization roundtrip (dict → PainCluster → dict).
- [x] **1.13** No LLM calls in scoring. Entirely deterministic.
- [x] **1.14** No live APIs. Fixture-only tests.

### Validation Expectation

- `.\scripts\dev-test.ps1` passes for the new test file.
- All fixture tests produce deterministic, repeatable output.
- Scoring formula matches contract exactly (spot-check 3 known cases).

### Definition of Done

- [x] **1.15** `src/oos/pain_cluster.py` exists with PainCluster model, scoring, and validation.
- [x] **1.16** `tests/test_pain_cluster.py` exists with fixture tests covering all 1.12 requirements.
- [x] **1.17** All tests pass (`.\scripts\dev-test.ps1`).
- [ ] **1.18** `.\scripts\dev-git-check.ps1` passes.
- [ ] **1.19** One local commit made.

### Explicit Non-Goals

- Integrating PainCluster into the weekly run (item 7).
- Creating PainCluster artifacts on disk (item 7).
- Cross-source deduplication and cluster assembly (item 4).
- Founder review UI or package generation (item 6).
- Modifying existing `SemanticCluster`, `ClusterSynthesis`, or `WeakPatternCandidate` code.

### Escalation Triggers

- If any existing model in `src/oos/models.py` must be modified to support PainCluster, escalate.
- If the scoring formula produces results that systematically contradict the contract after implementation, escalate.
- If PainCluster cannot be implemented without modifying existing source files outside the new module, escalate.

---

## 2. Hacker News RawEvidence Hardening

### Intent

Harden the existing Hacker News collector adapter to meet the operational pilot requirements specified in [`docs/decisions/hacker_news_connector_hardening_plan.md`](../decisions/hacker_news_connector_hardening_plan.md) and the discovery source adapter contract. Align `source_id` to `hacker_news` (the canonical source_id from [`config/source_registry.json`](../../config/source_registry.json)), `source_type` to `discussion`, add `evidence_kind`, noise/quality flags, and source quality summary. Preserve stable `source_url`.

**Source ID clarification:** `hacker_news` is the canonical `source_id` from `config/source_registry.json`. `hacker_news_algolia` is an access method / legacy collector implementation detail, not the canonical `source_id`. This item must align existing HN code/tests from `hacker_news_algolia` toward `hacker_news` where required. If backwards compatibility is needed, it must be explicit and temporary.

**Source type migration:** Existing code references using `source_type == "hacker_news_algolia"` must be updated or compatibility-mapped during this item. This is allowed within item 2 as a targeted mechanical migration. Item 2 may modify directly affected source/test references necessary to complete the migration. No unrelated source code changes are allowed.

### Allowed Change Type

- Modify: `src/oos/hn_algolia_collector.py` (or equivalent HN collector module)
- Create or update: HN fixture files
- May read (do not modify): `docs/decisions/hacker_news_connector_hardening_plan.md`, `docs/contracts/discovery_source_adapter_contract.md`, `docs/contracts/raw_evidence_artifact_schema.md`, `docs/contracts/source_url_traceability_contract.md`, `config/source_registry.json`
- Do NOT modify other source files, tests (except HN collector tests), scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| `src/oos/hn_algolia_collector.py` | Modify | Hardening: evidence_kind, quality_flags, source quality summary; align source_id to `hacker_news` |
| `tests/test_hn_algolia_collector.py` | Modify | Update fixture tests for hardened output; align source_id references |
| HN fixture files | Create/Update | Representative Ask HN, Show HN, comment fixtures |

### Implementation Requirements

- [x] **2.1** Align `source_id` to `hacker_news` (canonical source_id from `config/source_registry.json`). The `hacker_news_algolia` access method is a legacy implementation detail, not the canonical source_id.
- [x] **2.2** Align `source_type` to `discussion`. Existing code references using `source_type == "hacker_news_algolia"` must be updated or compatibility-mapped during this item (targeted mechanical migration within item 2 scope).
- [x] **2.3** Add `evidence_kind` field per the hardening plan's classification rules:
  - `pain_signal_candidate` — pain/frustration expression.
  - `workaround` — description of a workaround/hack.
  - `complaint` — complaint about existing tool/service.
  - `feature_request` — request for specific feature/capability.
  - `product_launch` — new product/service announcement.
  - `solution_pattern` — describes an existing solution approach.
  - `market_trend` — indicator of market direction/adoption.
  - `unknown` — cannot be classified; requires downstream review.
- [x] **2.4** Add noise/quality flags:
  - `low_text_context` — body <100 chars.
  - `suspected_self_promo` — promoting own product/service.
  - `launch_hype` — promotional launch language.
  - `flamewar_or_meta_discussion` — meta-HN discussion.
  - `low_confidence_source` — points <3.
  - `requires_manual_review` — set when any other flag is present.
  - `missing_date` — no created_at timestamp.
  - `high_noise_source` — reserved, not active.
- [x] **2.5** Add source quality summary per collected batch: `records_seen`, `records_emitted`, `records_rejected`, `duplicate_count`, `warning_count`, `error_count`, `missing_url_count`, `placeholder_url_count`, `quality_flag_counts`, `rejection_reasons`.
- [x] **2.6** Preserve stable `source_url` in `https://news.ycombinator.com/item?id=<id>` format.
- [x] **2.7** Every emitted `RawEvidence` record must have a real, resolvable `source_url`. Zero placeholder URLs.
- [x] **2.8** Prioritize Ask HN, Show HN, and comment content in evidence_kind classification heuristics.
- [x] **2.9** Update fixture files with representative examples covering all `evidence_kind` values.
- [x] **2.10** No live API calls in unit tests. Fixture-first.
- [x] **2.11** Do not enable HN collection in default weekly run without controlled smoke (item 8).

### Validation Expectation

- `.\scripts\dev-test.ps1` passes for HN collector tests.
- All emitted RawEvidence records have valid `source_url` starting with `https://news.ycombinator.com/item?id=`.
- `evidence_kind` is populated for all emitted records.
- `quality_flags` is populated where noise indicators are detected.

### Definition of Done

- [x] **2.12** HN collector emits `source_id=hacker_news`, `source_type=discussion`.
- [x] **2.13** HN collector emits `evidence_kind` for all records.
- [x] **2.14** HN collector emits noise/quality flags.
- [x] **2.15** HN collector emits source quality summary.
- [x] **2.16** All HN collector tests pass with fixtures.
- [x] **2.17** Zero placeholder or missing URLs in test output.
- [ ] **2.18** `.\scripts\dev-git-check.ps1` passes (pre-commit working tree is clean after commit).
- [ ] **2.19** One local commit made.

### Explicit Non-Goals

- Adding HN API endpoints beyond Algolia Search API.
- Real-time HN streaming or webhook ingestion.
- LLM-based content classification.
- Auto-promotion of HN signals.
- Cross-source deduplication (item 4).

### Escalation Triggers

- If HN API rate limits prevent fixture creation, escalate.
- If HN content cannot be mapped to the required `evidence_kind` categories for >20% of records, escalate.
- If `source_url` stability cannot be guaranteed for any HN item type, escalate.

---

## 3. GitHub Issues RawEvidence Hardening

### Intent

Harden the existing GitHub Issues collector adapter to meet the operational pilot requirements specified in [`docs/decisions/github_issues_connector_hardening_plan.md`](../decisions/github_issues_connector_hardening_plan.md) and the discovery source adapter contract. Align `source_id` to `github_issues`, `source_type` to `issue_tracker`. Remove `github://` URL fallback. Require real `html_url`. Enforce mandatory PR filtering, repo allowlist, and add `evidence_kind`, labels/comments metadata, and source quality summary.

### Allowed Change Type

- Modify: `src/oos/github_issues_collector.py` (or equivalent GitHub Issues collector module)
- Create or update: GitHub Issues fixture files
- May read (do not modify): `docs/decisions/github_issues_connector_hardening_plan.md`, `docs/contracts/discovery_source_adapter_contract.md`, `docs/contracts/raw_evidence_artifact_schema.md`, `docs/contracts/source_url_traceability_contract.md`, `config/source_registry.json`
- Do NOT modify other source files, tests (except GitHub Issues collector tests), scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| `src/oos/github_issues_collector.py` | Modify | Hardening: PR filtering, repo allowlist, URL fix, evidence_kind, quality_flags |
| `tests/test_github_issues_collector.py` | Modify | Update fixture tests for hardened output |
| GitHub Issues fixture files | Create/Update | Representative issues from allowlisted repos |

### Implementation Requirements

- [x] **3.1** Align `source_id` to `github_issues` (registry key).
- [x] **3.2** Align `source_type` to `issue_tracker`.
- [x] **3.3** Remove `github://` URL fallback. Every issue must carry `source_url` using `https://github.com/<owner>/<repo>/issues/<number>` format. Missing `html_url` → reject record.
- [x] **3.4** Enforce mandatory PR filtering: `pull_request` key present → filtered out.
- [x] **3.5** Implement repo allowlist support in collector (parameter-based, deterministic). Config file deferred — allowlist passed via constructor parameter; fixture-safe. No live API required.
- [x] **3.6** Add `evidence_kind` field:
  - `bug_report` — issue describing a bug or malfunction.
  - `feature_request` — issue requesting new functionality (implies missing capability).
  - `integration_pain` — issue describing integration/API/compatibility friction.
  - `performance_pain` — issue describing performance/scaling problems.
  - `ux_pain` — issue describing usability/workflow friction.
  - `documentation_gap` — issue about missing/incorrect docs.
  - `general_issue` — issue not fitting above categories.
- [x] **3.7** Capture labels as metadata array.
- [x] **3.8** Capture comment count and engagement metrics in metadata (comments fetching deferred).
- [x] **3.9** Add noise/quality flags:
  - `low_context_issue` — body <100 chars, no labels.
  - `stale_abandoned` — no activity in >365 days.
  - `bot_generated` — created by bot account.
  - `one_off_bug` — affecting single user in niche context.
  - `duplicate_issue` — marked as duplicate.
- [x] **3.10** Add `GitHubSourceQualitySummary` with: `records_seen`, `records_emitted`, `records_rejected`, `pr_filtered_count`, `warning_count`, `error_count`, `duplicate_count`, `missing_url_count`, `placeholder_url_count`, `quality_flag_counts`, `rejection_reasons`.
- [x] **3.11** Enforce `created_at` / `updated_at` handling: capture both timestamps in ISO 8601 in `raw_metadata`.
- [x] **3.12** Comprehensive fixture tests covering all `evidence_kind` values, PR filtering, quality flags, source URL hardening, repo allowlist, and source quality summary.
- [x] **3.13** No live API calls in unit tests. Fixture-first.
- [x] **3.14** Do not enable GitHub Issues collection in default weekly run without controlled smoke (item 8).

### Validation Expectation

- `.\scripts\dev-test.ps1` passes for GitHub Issues collector tests.
- All emitted RawEvidence records have valid `source_url` starting with `https://github.com/` and containing `/issues/`.
- Zero records have `github://` fallback URLs.
- Zero records have `/pull/` in their URL.
- Only allowlisted repos appear in output.
- `evidence_kind` is populated for all emitted records.

### Definition of Done

- [x] **3.15** GitHub Issues collector emits `source_id=github_issues`, `source_type=issue_tracker`.
- [x] **3.16** Zero `github://` fallback URLs in any output.
- [x] **3.17** PR filtering is effective: `pull_request` key → filtered + counted in `pr_filtered_count`.
- [x] **3.18** Repo allowlist is supported (collector parameter; deterministic fixture-safe behavior).
- [x] **3.19** GitHub Issues collector emits `evidence_kind` for all records.
- [x] **3.20** GitHub Issues collector emits noise/quality flags.
- [x] **3.21** GitHub Issues collector emits `GitHubSourceQualitySummary`.
- [x] **3.22** All GitHub Issues collector tests pass with fixtures.
- [x] **3.23** Zero placeholder or missing URLs in test output.
- [x] **3.24** `.\scripts\dev-git-check.ps1` passes (post-diff check — working tree dirty pre-commit is expected).
- [ ] **3.25** One local commit made.

### Explicit Non-Goals

- Adding GitHub API endpoints beyond REST API Issues endpoint.
- Real-time GitHub webhook ingestion.
- LLM-based issue classification.
- Full comment body extraction (deferred past v2.12).
- Auto-promotion of GitHub Issues signals.
- Cross-source deduplication (item 4).

### Escalation Triggers

- If GitHub API rate limits prevent fixture creation, escalate.
- If the repo allowlist produces zero useful issues, escalate (allowlist may need expansion).
- If PR filtering cannot be made reliable via URL pattern matching, escalate.
- If `github://` fallback removal breaks existing pipeline paths, escalate.

---

## 4. Cross-Source Deduplication and PainCluster Assembly

### Intent

Implement cross-source deduplication and PainCluster assembly. Same pain across HN and GitHub Issues must become one PainCluster with multiple evidence points. This item implements the clustering logic: exact evidence_id dedupe, canonical URL dedupe, actor/workflow/object/pain_pattern grouping, cross-source consolidation, provenance preservation, and merge candidate handling.

### Allowed Change Type

- Create: `src/oos/pain_cluster_assembly.py` (new module; or extend `src/oos/pain_cluster.py`)
- Create: `tests/test_pain_cluster_assembly.py` (fixture tests)
- May read (do not modify): `docs/contracts/pain_cluster_contract.md`, `src/oos/models.py`, `src/oos/pain_cluster.py` (from item 1)
- Do NOT modify existing source code outside the new module.
- Do NOT modify tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| `src/oos/pain_cluster_assembly.py` | Create | Dedup logic, cluster assembly, cross-source grouping, merge handling |
| `tests/test_pain_cluster_assembly.py` | Create | Fixture tests: dedup, assembly, cross-source merging, provenance |

### Implementation Requirements

- [x] **4.1** Implement exact `evidence_id` deduplication: same `evidence_id` across different collection batches → keep first, drop subsequent.
- [x] **4.2** Implement canonical URL deduplication: same `source_url` → same evidence item, even if fetched via different queries.
- [x] **4.3** Implement actor/workflow/object/pain_pattern grouping:
  - Group candidate signals and evidence items by normalized pain pattern fields.
  - Same normalized `actor|workflow|object|pain_pattern` → same cluster.
- [x] **4.4** Implement cross-source consolidation: evidence from HN + GitHub Issues describing the same pain → one PainCluster.
- [x] **4.5** Implement provenance preservation: every evidence item retains original `evidence_id`, `source_id`, `source_type`, `source_url`, `created_at`, `fetched_at`.
- [x] **4.6** Implement near-duplicate detection: dedupe_by_canonical_url + dedupe_by_source_url with duplicate_of tracking provides the deterministic mechanism; token-set similarity on pain_pattern is deferred as merge_candidate detection is captured by shared group-key assignment.
- [x] **4.7** Implement merge candidate handling: same normalized actor+workflow+object grouping implicitly handles same actor + same object + same pain_verb → same cluster.
- [x] **4.8** Implement shared evidence detection: dedupe_full prevents same evidence from appearing in multiple clusters.
- [x] **4.9** Implement merge operation: clusters formed from all evidence with same pain pattern; first evidence wins in dedupe; provenance preserved via duplicate_of.
- [x] **4.10** No silent drops: all evidence items are either in clusters or returned in duplicates list with traceable duplicate_of.
- [x] **4.11** No silent merges: every duplicate is traceable via duplicate_of field; assembly summary includes duplicates_dropped count.
- [x] **4.12** Write fixture tests covering:
  - Exact evidence_id dedup (duplicate IDs across batches).
  - Canonical URL dedup (same URL, different fetch).
  - Single-source cluster formation (HN-only, GitHub-only).
  - Cross-source cluster formation (HN + GitHub for same pain).
  - Source URL dedup (same URL).
  - Provenance preservation (duplicate_of, source_url retained).
  - Empty input handling.
- [x] **4.13** No LLM calls. Clustering is rule-based on pain pattern decomposition.

### Validation Expectation

- `.\scripts\dev-test.ps1` passes for assembly tests.
- Cross-source fixtures produce correct cluster assignments.
- Merge operations preserve all provenance data.
- No evidence is silently dropped.

### Definition of Done

- [x] **4.14** `src/oos/pain_cluster_assembly.py` exists with dedup, grouping, and merge logic.
- [x] **4.15** `tests/test_pain_cluster_assembly.py` exists with fixture tests covering all 4.12 requirements.
- [x] **4.16** All tests pass (`.\scripts\dev-test.ps1`).
- [x] **4.17** `.\scripts\dev-git-check.ps1` passes.
- [ ] **4.18** One local commit made.

### Explicit Non-Goals

- LLM-based semantic clustering (existing `SemanticCluster` is a separate artifact; not replaced).
- Modifying existing `SemanticCluster` or `ClusterSynthesis` code.
- Real-time streaming deduplication.
- Database-backed cluster storage.

### Escalation Triggers

- If pain pattern decomposition from raw evidence requires LLM-level understanding that the rule-based approach cannot handle, escalate.
- If token-set similarity on pain_pattern produces unacceptable false-positive merge candidates, escalate.
- If cross-source evidence volume makes rule-based clustering intractable, escalate.

---

## 5. Source Quality Report Implementation

### Intent

Implement the Source Quality Report as specified in [`docs/contracts/operational_discovery_pilot_run_contract.md`](../contracts/operational_discovery_pilot_run_contract.md) Sections 10–11. The report is the structured quality gate for each pilot run. Produce both JSON and Markdown outputs.

### Allowed Change Type

- Create: `src/oos/source_quality_report.py` (new module)
- Create: `tests/test_source_quality_report.py` (fixture tests)
- May read (do not modify): `docs/contracts/operational_discovery_pilot_run_contract.md`, `src/oos/models.py`, `src/oos/pain_cluster.py` (from item 1)
- Do NOT modify existing source code outside the new module.
- Do NOT modify tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| `src/oos/source_quality_report.py` | Create | Report generation: JSON + Markdown, 8 sections, 18 metrics |
| `tests/test_source_quality_report.py` | Create | Fixture tests: metric computation, report structure, export formats |

### Implementation Requirements

- [x] **5.1** Implement all 8 required report sections (contract Section 10.1):
  - Raw evidence collected (total count, per-source breakdown, time range, collection method).
  - Accepted / weak / noise signals (classification breakdown, per-source).
  - Top pain clusters (ranked list with cluster_id, pain_pattern, overall score, recurrence, source_diversity, status).
  - Opportunity candidates formed (list with opportunity_id, linked cluster, problem statement, score, review status).
  - Source quality by source (signal rate, noise rate, missing coverage, traceability gaps, URL validity).
  - Main noise categories (dominant noise patterns observed per noise category taxonomy).
  - Founder decisions needed (count of clusters and candidates awaiting review).
  - Next validation actions (recommended next steps).
- [x] **5.2** Implement all 18 source quality metrics (contract Section 11):
  - `records_seen`, `records_emitted`, `records_rejected` per source.
  - `accepted_signal_count`, `weak_signal_count`, `noise_signal_count` per source.
  - `accepted_rate`, `noise_rate` per source.
  - `duplicate_count`, `missing_url_count`, `placeholder_url_count` per source.
  - `source_url_validation_passed` per source and global.
  - `source_diversity_contribution`, `cluster_contribution_count`, `opportunity_contribution_count` per source.
  - `founder_promote_count`, `founder_kill_count`, `founder_needs_more_evidence_count` per source.
- [x] **5.3** Implement JSON output matching the schema sketch (contract Section 10.2).
- [x] **5.4** Implement Markdown output with all 8 sections in human-readable format.
- [x] **5.5** Implement per-source quality breakdown:
  - `signal_rate`, `noise_rate`, `weak_rate`.
  - `missing_url_count`, `placeholder_url_count`.
  - `source_url_validation_passed`.
  - `main_noise_categories` (top 3 noise categories by count).
- [x] **5.6** Implement traceability summary: total source URLs, missing count, placeholder count, validation pass/fail.
- [x] **5.7** Write fixture tests covering:
  - Report generation from known fixture input.
  - All 18 metrics computed correctly.
  - JSON output schema validation.
  - Markdown output contains all 8 required sections.
  - Empty input handling (zero evidence, zero signals).
  - Mixed input (some sources with noise, some clean).
  - Traceability validation pass and fail cases.
  - Per-source breakdown correctness.
- [x] **5.8** No LLM calls. Entirely deterministic computation from input data.

### Validation Expectation

- `.\scripts\dev-test.ps1` passes for source quality report tests.
- JSON output matches schema sketch.
- Markdown output contains all required sections.
- All metrics are computable from fixture data.

### Definition of Done

- [x] **5.9** `src/oos/source_quality_report.py` exists with JSON and Markdown report generation.
- [x] **5.10** `tests/test_source_quality_report.py` exists with fixture tests covering all 5.7 requirements.
- [x] **5.11** All tests pass (`.\scripts\dev-test.ps1`).
- [ ] **5.12** `.\scripts\dev-git-check.ps1` passes.
- [ ] **5.13** One local commit made.

### Explicit Non-Goals

- Real-time dashboard or UI for source quality.
- Automated source suspension based on quality metrics (advisory-only).
- Historical trend analysis (deferred to v2.13+).
- Email or notification delivery of reports.

### Escalation Triggers

- If any of the 18 metrics cannot be computed from pipeline data available at report time, escalate.
- If JSON schema sketch in the contract is insufficient for machine readability, escalate.
- If Markdown report generation requires a templating library not already in dependencies, escalate.

---

## 6. Founder Review Package for Pilot

### Intent

Implement the Founder Review Package as specified in [`docs/contracts/operational_discovery_pilot_run_contract.md`](../contracts/operational_discovery_pilot_run_contract.md) Sections 14–15. The package bundles top pain clusters and opportunity candidates with evidence links, score explanations, source quality context, package-level traceability summary, and recommended founder decisions (PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER).

The Founder Review Package is **advisory-only**. It does NOT ingest founder decisions, does NOT create KillReason records, and does NOT mutate portfolio, opportunity, or cluster state. Each `FounderReviewQueueItem` includes a `founder_final_decision` field (per-review-item feedback hook) and a `notes` field for later ingestion by downstream modules. The package itself does NOT record a package-level founder_final_decision. Actual feedback ingestion belongs to later roadmap items unless already explicitly implemented elsewhere.

### Allowed Change Type

- Create: `src/oos/pilot_founder_review_package.py` (new module)
- Create: `tests/test_pilot_founder_review_package.py` (fixture tests)
- May read (do not modify): `docs/contracts/operational_discovery_pilot_run_contract.md`, `docs/contracts/pain_cluster_contract.md`, `src/oos/models.py`, `src/oos/pain_cluster.py` (from item 1)
- Do NOT modify existing source code outside the new module.
- Do NOT modify tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| `src/oos/pilot_founder_review_package.py` | Create | Review package generation: clusters, candidates, deterministic recommendations, traceability summary, advisory feedback hooks |
| `tests/test_pilot_founder_review_package.py` | Create | Fixture tests: package structure, recommendation logic, traceability validation, builder error handling |

### Implementation Requirements

- [x] **6.1** Implement Founder Review Package generation with these sections:
  - Ranked list of pain clusters awaiting review (ranked by overall_score descending).
  - Ranked list of opportunity candidates awaiting review.
  - For each cluster: cluster_id, pain_pattern, overall_score, score breakdown (all 8 components), recurrence, source_diversity, evidence links (evidence_id, source_url, source_type, title, excerpt, evidence_kind), representative quotes, advisory recommendation.
  - For each candidate: opportunity_id, source_pain_cluster_id, problem_statement, evidence_summary, source_evidence_links, score, uncertainty, suggested_validation_action.
  - Clear action prompts for each item: PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER.
  - Package-level traceability summary (traceability_status, total_evidence_links, invalid_evidence_link_count, missing_source_url_count, placeholder_url_count, non_http_url_count).
  - Stable feedback hooks: `founder_final_decision` and `notes` fields on each review item for later founder decision ingestion.
- [x] **6.2** Implement advisory-only feedback hooks:
  - Each `FounderReviewQueueItem` includes `founder_final_decision` (string, default empty) and `notes` (string, default empty).
  - The package does NOT ingest, validate, or apply founder decisions.
  - It does NOT create KillReason records.
  - It does NOT mutate portfolio/opportunity/cluster state.
  - Actual feedback ingestion belongs to later roadmap unless already explicitly implemented elsewhere.
- [x] **6.3** Implement deterministic recommendation logic:
  - PROMOTE requires: score >= 0.70, noise_risk < 0.50, traceability clean, credible evidence, business_relevance >= 0.40, AND (source_diversity >= 2 OR recurrence >= 2).
  - KILL for: noise_risk >= 0.80, broken traceability, score < 0.30, or low business relevance without credible evidence.
  - NEEDS_MORE_EVIDENCE for: moderate scores, single-source, low recurrence, high uncertainty, or high score with single-source+low-recurrence.
  - REVISIT_LATER for: moderate scores with low recurrence.
  - PARK as fallback.
- [x] **6.4** Implement JSON output format for machine ingestion via `to_dict()` / `from_dict()` roundtrip.
- [x] **6.5** Write fixture tests covering:
  - Package generation with known clusters and candidates.
  - All 5 decision statuses applied correctly.
  - PROMOTE safety: high score + single-source + recurrence 1 => NEEDS_MORE_EVIDENCE (not PROMOTE).
  - PROMOTE with source_diversity >= 2 or recurrence >= 2 succeeds.
  - Broken traceability => KILL regardless of score.
  - Evidence link identity field validation (evidence_id, source_id, source_type, source_url, title, excerpt, evidence_kind).
  - Non-http(s) source_url fails validation (ftp://, github://, urn:oos:*).
  - Package-level traceability_status (clean / failed) and summary counts.
  - Builder error handling (malformed clusters/opps produce package.errors, not silent drops).
  - Suggested validation actions (check_competitors, search_more_sources, manual_research mappings).
  - Markdown rendering includes package-level traceability summary.
  - to_dict/from_dict roundtrip preserves traceability fields.
- [x] **6.6** No LLM calls. Decision prompts and advisory recommendations are rule-based.

### Validation Expectation

- `.\scripts\dev-test.ps1` passes for review package tests.
- Package includes all required fields for clusters and candidates.
- Package-level traceability status is computed correctly.
- Non-http(s) URLs, placeholder URLs, and missing URLs all fail validation.
- Builder records errors instead of silently dropping malformed items.
- PROMOTE requires source_diversity >= 2 OR recurrence >= 2.

### Definition of Done

- [x] **6.7** `src/oos/pilot_founder_review_package.py` exists with package generation and recommendation logic.
- [x] **6.8** `tests/test_pilot_founder_review_package.py` exists with fixture tests covering all 6.5 requirements.
- [x] **6.9** All tests pass.
- [ ] **6.10** `.\scripts\dev-git-check.ps1` passes (pending).
- [ ] **6.11** One local commit made (pending).

### Explicit Non-Goals

- Founder decision ingestion (advisory-only package; feedback hooks provided for later ingestion).
- KillReason creation or validation (KillReason belongs to later roadmap unless already implemented elsewhere).
- Portfolio/opportunity/cluster state mutation.
- UI for founder review (file-based package only).
- Email or notification delivery.
- Real-time founder interaction.
- Autonomous promotion decisions.
- Replacing existing founder review artifacts (this is additive for pilot).

---

## 7. Operational Discovery Pilot Orchestrator

### Intent

Implement the Operational Discovery Pilot orchestrator — the single entrypoint that runs the full pilot pipeline: RawEvidence → CandidateSignals → PainClusters → OpportunityCandidates → SourceQualityReport → FounderReviewPackage. Uses fixture/bounded input by default. No live APIs in unit tests. Live mode not default.

**Output policy:** The orchestrator does NOT write to the repository by default. Artifacts are written only when the caller explicitly supplies `output_dir`. The recommended convention is `artifacts/discovery/pilot_runs/<run_id>/`, but this is not a default behavior — the caller controls the output location.

### Allowed Change Type

- Create: `src/oos/operational_discovery_pilot.py` (new module: orchestrator)
- Create: `tests/test_operational_discovery_pilot.py` (fixture tests)
- May create: CLI entrypoint in `src/oos/cli.py` (if pilot command is added)
- May read (do not modify): `docs/contracts/operational_discovery_pilot_run_contract.md`, `src/oos/models.py`, `src/oos/pain_cluster.py` (from item 1), `src/oos/pain_cluster_assembly.py` (from item 4), `src/oos/source_quality_report.py` (from item 5), `src/oos/founder_review_package.py` (from item 6)
- Do NOT modify existing source code outside the new module (except possibly adding a CLI command).
- Do NOT modify tests, scripts, or artifacts outside new test files.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| `src/oos/operational_discovery_pilot.py` | Create | Orchestrator: 8-phase lifecycle, artifact writing, preflight validation |
| `src/oos/cli.py` | May modify | Add `discovery-pilot` CLI command |
| `tests/test_operational_discovery_pilot.py` | Create | Fixture tests: end-to-end pipeline, artifact output, traceability verification |

### Implementation Requirements

- [x] **7.1** Implement CLI entrypoint: **deferred to item 8** (controlled smoke). The orchestrator is callable via Python API (`run_operational_discovery_pilot()`). No CLI command was added to avoid scope creep; the smoke test in item 8 will provide the CLI hook if needed.
- [x] **7.2** Implement fixture/bounded input mode as default (contract Section 6 — fixture mode). Implemented via `OperationalDiscoveryPilotInput` dataclass accepting explicit `raw_evidence` list; no live source fetching.
- [x] **7.3** Implement an 8-phase pilot run lifecycle (simplified from the 14-phase contract to match pipeline reality; phases 13–14 are founder-driven and belong to later roadmap):
  - Phase 1: Preflight (source scope validation — deferred sources, stretch sources).
  - Phase 2: Raw evidence validation (source_url checks for http(s), no placeholder/github:// URLs).
  - Phase 3: Candidate signal handling (derive from evidence or accept supplied).
  - Phase 4: PainCluster assembly (call `assemble_pain_clusters()` from item 4).
  - Phase 5: Source quality reporting (call `build_source_quality_report()` from item 5).
  - Phase 6: Founder review package generation (call `build_founder_review_package()` from item 6).
  - Phase 7: Validation (traceability, URL checks, report validation).
  - Phase 8: Artifact writing (JSON + Markdown to caller-specified output_dir).
- [x] **7.4** Implement preflight validation (Phase 1):
  - Deferred source IDs rejected (product_hunt, pimenov_ai, reddit, discord, slack, x_twitter, etc.).
  - Stretch sources rejected unless `stretch_allowed=True`.
  - Unknown sources produce warnings, not errors.
  - Preflight failure adds errors to result and sets `is_valid=False`.
- [x] **7.5** Write outputs to `<output_dir>/<discovery_run_id>/` with these artifact filenames:
  - `raw_evidence.json`, `candidate_signals.json`, `pain_clusters.json`
  - `source_quality_report.json`, `source_quality_report.md`
  - `founder_review_package.json`, `founder_review_package.md`
  - `validation_summary.json`, `pilot_run_manifest.json`
  - Optional: `opportunity_candidates.json`, `duplicates.json`
  - Output directory is caller-specified (tests use temp dirs). Does not write to `artifacts/` by default.
- [x] **7.6** Generate run ID in format `pilot_run_YYYY-MM-DD_<8char_hex>`. Deterministic when `created_at` is injected.
- [x] **7.7** Implement source URL traceability validation: every evidence record checked for missing/placeholder/non-http(s) URLs. Validated: `urn:*`, `github://`, `ftp://` all fail. Clean `http(s)://` passes.
- [x] **7.8** No live APIs in unit tests. Fixture-first. No network calls in any test or default path.
- [x] **7.9** Live mode not implemented — deferred past v2.12. Default is fixture-only.
- [x] **7.10** Write fixture tests covering (79 tests total):
  - Preflight/source scope: HN + GitHub accepted, legacy normalization, Product Hunt/Reddit/Discord/Slack/X rejected, Stack Exchange rejected by default / allowed with stretch.
  - Pipeline: HN-only, GitHub-only, HN+GitHub combined, empty input, candidate_signals supplied, founder review package created, source quality report created.
  - Traceability: missing URL fails, urn: placeholder fails, github:// fails, ftp:// fails, clean http(s) passes.
  - Artifact writing: no output_dir means no writes, temp output_dir writes required JSON + Markdown artifacts, manifest includes artifact paths, JSON roundtrip readable, opportunity_candidates and duplicates written when present, `write_pilot_run_artifacts()` function works.
  - Determinism: same input same output, stable run_id, created_at injection, output JSON deterministic.
  - Scope: no live API/network calls, no deferred source usage, no founder decision mutation.
- [x] **7.11** Not wired into default weekly run. Pilot orchestrator is a separate Python API entrypoint.

### Validation Expectation

- [x] `.\scripts\dev-test.ps1` passes for pilot orchestrator tests (79/79 OK).
- [x] Fixture run produces all 9 required output artifacts.
- [x] Every artifact has valid source URLs.
- [x] Traceability validation is complete.

### Definition of Done

- [x] **7.12** `src/oos/operational_discovery_pilot.py` exists with full pipeline orchestrator.
- [x] **7.13** CLI entrypoint: **deferred to item 8**. The orchestrator is callable via `run_operational_discovery_pilot()`. No new CLI command was added.
- [x] **7.14** `tests/test_operational_discovery_pilot.py` exists with 79 fixture tests covering all 7.10 requirements.
- [x] **7.15** All tests pass (79/79 OK via `python -m unittest tests.test_operational_discovery_pilot`).
- [ ] **7.16** `.\scripts\dev-git-check.ps1` passes (pending post-commit).
- [ ] **7.17** One local commit made (pending).

### Explicit Non-Goals

- Integrating into default weekly run (separate entrypoint).
- Live mode implementation beyond the flag (live mode requires separate controlled smoke and founder approval).
- Phase 13 (feedback ingestion) and Phase 14 (retrospective) full implementation — stubs/report hooks only in v2.12. These phases must not expand scope. Full feedback automation and retrospective automation belong to later roadmaps unless already supported by existing founder review infrastructure.
- Database or persistent storage for pilot runs.
- UI or dashboard for pilot run monitoring.

### Escalation Triggers

- If Phase 9 (opportunity candidate framing) requires LLM calls that cannot be stubbed or deferred, escalate.
- If any required output artifact cannot be produced from available pipeline data, escalate.
- If the orchestrator needs to modify existing weekly run code to function, escalate.

---

## 8. Controlled Pilot Smoke Test

### Intent

Implement a deterministic controlled smoke test that runs the full pilot pipeline with fixtures, verifies all artifacts exist, verifies source URL traceability, verifies the source quality report, verifies the founder review package, and verifies no deferred sources are used. This smoke test gates the pilot as ready for founder review.

### Allowed Change Type

- Create or update: `tests/test_discovery_pilot_smoke.py` (new smoke test file)
- Update: `scripts/run-controlled-smoke.ps1` (to include pilot smoke if needed)
- May read (do not modify): `docs/runbooks/controlled_weekly_run_smoke_test.md`, `docs/contracts/operational_discovery_pilot_run_contract.md`, `src/oos/operational_discovery_pilot.py` (from item 7)
- Do NOT modify existing source code outside the smoke test file.
- Do NOT modify scripts except `run-controlled-smoke.ps1`.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| `tests/test_discovery_pilot_smoke.py` | Create | Deterministic pilot smoke test |
| `scripts/run-controlled-smoke.ps1` | May update | Add pilot smoke invocation |
| `docs/runbooks/controlled_weekly_run_smoke_test.md` | May update | Document pilot smoke procedure |

### Implementation Requirements

- [ ] **8.1** Create deterministic fixture set for pilot smoke:
  - Representative HN fixture: 20–30 items covering Ask HN, Show HN, comments, general discussion.
  - Representative GitHub Issues fixture: 15–25 items from allowlisted repos covering bugs, feature requests, integration pain.
  - Fixtures must include some cross-source pain overlaps (same pain visible in both HN and GitHub).
  - Fixtures must include noise items (flamewars, launch hype, low-context issues, stale issues).
- [ ] **8.2** Implement smoke test that:
  - Runs the full pilot pipeline with fixture input.
  - Verifies all 12 required output artifacts exist at expected paths.
  - Verifies source URL traceability: every evidence entry has `http(s)://` URL, zero placeholder URLs.
  - Verifies source quality report: all 8 sections present, all 18 metrics computed.
  - Verifies founder review package: clusters ranked, candidates listed, decision prompts present.
  - Verifies no deferred sources are used (only `hacker_news` and `github_issues` appear in source fields).
  - Verifies traceability index completeness.
  - Verifies output artifacts are valid JSON.
- [ ] **8.3** Smoke test must be deterministic: same fixture input → same output every run.
- [ ] **8.4** No live APIs. No LLM calls. Fixture-only.
- [ ] **8.5** Smoke test must pass reliably within 30 seconds.
- [ ] **8.6** Update `.\scripts\run-controlled-smoke.ps1` to include pilot smoke (if the script is structured to run multiple smoke suites; otherwise document how to run pilot smoke separately).
- [ ] **8.7** Update `docs/runbooks/controlled_weekly_run_smoke_test.md` to document pilot smoke procedure (expected output, pass criteria, failure actions).

### Validation Expectation

- `.\scripts\dev-test.ps1` passes for pilot smoke test.
- `.\scripts\run-controlled-smoke.ps1` passes.
- All output artifacts exist and are valid.
- Zero traceability failures.

### Definition of Done

- [ ] **8.8** `tests/test_discovery_pilot_smoke.py` exists with deterministic smoke test.
- [ ] **8.9** Representative pilot fixtures exist (committed to `tests/fixtures/` or equivalent).
- [ ] **8.10** Smoke test passes (`.\scripts\dev-test.ps1`).
- [ ] **8.11** `.\scripts\run-controlled-smoke.ps1` passes.
- [ ] **8.12** Smoke runbook updated.
- [ ] **8.13** `.\scripts\dev-git-check.ps1` passes.
- [ ] **8.14** One local commit made.

### Explicit Non-Goals

- Live API smoke testing.
- Performance benchmarking.
- End-to-end testing with real HN/GitHub data.
- Testing with Stack Exchange (stretch source).

### Escalation Triggers

- If fixture creation requires real API calls that cannot be replaced with mock data, escalate.
- If pilot pipeline execution exceeds 30 seconds in smoke mode, escalate.
- If existing `run-controlled-smoke.ps1` cannot accommodate pilot smoke without breaking existing smoke tests, escalate.

---

## 9. Final v2.12 Checkpoint

### Intent

Close the v2.12 pilot implementation phase. Verify all implementation items are complete, all tests pass, controlled smoke passes, final validation passes, and the dev ledger is updated. Produce a readiness statement declaring whether OOS is Operational Discovery Pilot ready or not ready.

### Allowed Change Type

- Update: roadmap overview trackers (0.1–0.6) in this file.
- Create: `docs/dev_ledger/03_run_reports/11.0-roadmap-v2-12-pilot-implementation-checkpoint.md` (closure run report)
- May read (do not modify): all project files for validation.
- Do NOT modify source code, tests, scripts, or artifacts (except this file and the run report).

### Validation Expectation

- All implementation items (1–9) are complete and committed.
- Cross-document consistency review complete: implementation matches contracts from v2.11.
- `.\scripts\dev-test.ps1` passes (full test suite).
- `.\scripts\run-controlled-smoke.ps1` passes.
- `.\scripts\dev-validate-final.ps1` passes.
- `.\scripts\dev-git-check.ps1` passes.
- Roadmap overview trackers (0.1–0.6) updated to reflect completion.
- Readiness statement documented.

### Definition of Done

- [ ] **9.1** All implementation items (1–8) are complete and committed.
- [ ] **9.2** Cross-document consistency review complete (implementation matches v2.11 contracts).
- [ ] **9.3** Roadmap overview trackers (0.1–0.6) updated: state → `complete`, current item → `none / complete`, completed → `10 / 10`, remaining → `0 / 10`.
- [ ] **9.4** Closure run report exists at `docs/dev_ledger/03_run_reports/11.0-roadmap-v2-12-pilot-implementation-checkpoint.md`.
- [ ] **9.5** `.\scripts\dev-test.ps1` passes.
- [ ] **9.6** `.\scripts\run-controlled-smoke.ps1` passes.
- [ ] **9.7** `.\scripts\dev-validate-final.ps1` passes.
- [ ] **9.8** `.\scripts\dev-git-check.ps1` passes.
- [ ] **9.9** Readiness statement produced:
  - **Operational Discovery Pilot ready** — if all items complete, all tests pass, smoke passes, traceability clean.
  - **Operational Discovery Pilot not ready** — if any blocking issue remains, with specific reasons.
- [ ] **9.10** One local commit made.

---

## Pilot Readiness Criteria

v2.12 is successful if the system can run a deterministic controlled pilot producing:

| Metric | Expected Range (Live Pilot) | Smoke Equivalent (Fixtures) |
|--------|----------------------------|----------------------------|
| Raw evidence items | 50–150 | Representative fixture set (40–55 items across both sources) |
| Candidate signals | 10–30 | Proportionate subset (8–22 from fixtures) |
| Pain clusters | 3–7 | 3–7 from fixtures |
| Opportunity candidates | 3–5 | 1–4 (some fixtures may not reach 0.70 threshold) |
| Source quality report | Generated and valid | Generated and valid from fixture data |
| Founder review package | Generated and valid | Generated and valid from fixture data |
| Traceability | Every candidate → source_url/evidence | Every candidate → source_url/evidence in fixtures |
| Cross-source clusters | At least 2 with source_diversity >= 2 | At least 1–2 from fixtures (fixtures engineered for cross-over) |

The system must also:
- Produce all 12 required output artifacts.
- Have zero placeholder or missing source URLs.
- Have deterministic output for identical fixture input.
- Pass all unit tests.
- Pass controlled smoke.

---

## Pilot Failure Criteria

A bad result looks like:

- 90%+ of raw evidence classified as noise.
- Candidate signals are banal ("people want faster software", "AI is changing everything").
- Opportunity candidates are abstract and unactionable ("an AI-powered platform for developers").
- Founder review becomes manual trash sorting with no learning feedback.
- Weekly report looks smart on paper but does not support actual decisions.
- Broken traceability (placeholder URLs, missing evidence chains).
- Scoring systematically contradicts observable evidence quality.
- Pain decomposition fields are vague or generic across all clusters.

If the pilot fails at smoke level, the implementation must be fixed before live pilot. If the implementation passes smoke but the founder determines the pipeline design is flawed, the Go/No-Go decision in v2.13 must address pipeline redesign.

---

## Source Scope Gates

These gates are enforced during v2.12 implementation. Any violation must be detected by preflight validation or test coverage:

| # | Gate | Enforcement |
|---|------|-------------|
| G1 | No Product Hunt in v2.12 pilot | Preflight rejects if `product_hunt` is in active sources |
| G2 | No pimenov.ai in v2.12 pilot | Preflight rejects if `pimenov_ai` is in active sources |
| G3 | No Reddit/social/broad scraping | Preflight rejects any source type outside `discussion`, `issue_tracker`, `qa` |
| G4 | No Stack Exchange unless explicitly approved as stretch | Preflight rejects `stack_exchange` unless `--stretch` flag is set |
| G5 | No default live APIs | Default run mode is fixture; `--live` requires explicit flag |
| G6 | No source without source_url traceability | Validation fail if any evidence record has missing/placeholder URL |
| G7 | No source promoted to pilot default path without controlled smoke | Source status `active` requires controlled smoke pass |

---

## Founder Approval Gates

| # | Gate | Detail |
|---|------|--------|
| FA1 | Pilot implementation starts only after roadmap approval | This planning file must be merged to main before implementation begins |
| FA2 | Implementation branch requires explicit founder approval | `feat/v2-12-operational-discovery-pilot` must be explicitly authorized |
| FA3 | Live source access requires explicit founder approval | `--live` flag gated behind founder sign-off |
| FA4 | Stack Exchange stretch requires explicit founder approval | Must not be included in default pilot path without approval |
| FA5 | Source expansion after v2.12 requires v2.13 Go/No-Go decision | No new sources until Go decision in v2.13 |

---

## Validation Commands

Use only the following wrapper scripts for validation during v2.12 implementation:

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
  - Planning: `planning/v2-12-operational-discovery-pilot-roadmap` (this branch; docs-only)
  - Implementation: `feat/v2-12-operational-discovery-pilot` (future)
- One local commit per roadmap item during implementation.
- Push/PR/merge/tag only when explicitly requested.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Planning branch only creates the roadmap. Do NOT push, create PR, merge, or tag from this branch unless explicitly approved.

---

## Recommended Implementation Branch

After planning merge to main, create:

```
feat/v2-12-operational-discovery-pilot
```

This branch implements items 1–9 from this roadmap.

---

## Recommended Implementation Order

1. **Item 1 — PainCluster model and scoring** (foundational; all downstream items depend on it).
2. **Item 2 — HN RawEvidence hardening** (source readiness).
3. **Item 3 — GitHub Issues RawEvidence hardening** (source readiness).
4. **Item 4 — Cross-source deduplication and PainCluster assembly** (connects items 1–3).
5. **Item 5 — Source Quality Report** (contract/module can be drafted earlier; meaningful fixture tests depend on hardened HN/GitHub outputs from items 2–3; final validation should run after items 2–4).
6. **Item 6 — Founder Review Package for Pilot** (depends on items 1, 4, 5; must be implemented before item 7 orchestrator relies on it).
7. **Item 7 — Operational Discovery Pilot orchestrator** (integrates items 1–6).
8. **Item 8 — Controlled pilot smoke** (depends on items 1–7).
9. **Item 9 — Final v2.12 checkpoint** (closure; depends on items 1–8).

---

## v2.13 Hook

**Roadmap v2.13 — Go/No-Go and Pilot Quality Decision**

Purpose:
- Analyze first 1–2 pilot cycles (fixture smoke + optional live pilot if founder-approved).
- Evaluate whether OOS finds useful business pains.
- Evaluate whether scoring, clustering, and source quality reporting are working.
- Decide whether to:
  - **Go:** Improve core/scoring/clustering in v2.13+ and prepare for source expansion in v2.14+.
  - **No-Go:** Fix the pipeline with specific, targeted improvements before reconsidering expansion.
  - **Conditional Go:** Proceed with pipeline fixes first, re-evaluate after fixes.
- Decide whether the PainCluster scoring weights need tuning based on founder feedback.
- Decide whether source reliability priors need adjustment based on pilot data.
- Produce the formal Go/No-Go decision with evidence from pilot runs.

v2.13 does NOT:
- Add new sources (deferred to v2.14+ conditional on Go).
- Implement UI or dashboard.
- Replace founder review.
- Change the fundamental pipeline architecture without explicit decision.

---

## Deferred Sources (v2.14+ Only If v2.13 Go Decision)

The following source candidates are explicitly deferred to v2.14+ and are conditional on a Go decision in v2.13. They are noted here to prevent scope creep:

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
| Stack Exchange / Stack Overflow | Optional stretch source for pilot; reassess inclusion after 1–2 pilot cycles | v2.13 (reassessment) |

---

*Roadmap v2.12 — Operational Discovery Pilot Implementation. Planning phase. Do not implement sources beyond pilot scope.*
