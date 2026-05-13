# OOS Roadmap v2.13 — Operational Pilot Cycle 1 / Go-No-Go Decision

## 0. Roadmap Overview

### Active Roadmap

- [x] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md`
- [x] **0.2** Current item: `2 — Pilot Cycle 1 Brief`
- [x] **0.3** Roadmap state: `execution`
- [x] **0.4** Completed from this roadmap: **2 / 12**
- [x] **0.5** Remaining: **10 / 12**
- [x] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_12_operational_discovery_pilot_checklist.md` (complete, `10 / 10`, PR #52 merged, tag `v2.12`)

### Branch and Version

- **Planning branch:** `planning/v2-13-operational-pilot-go-no-go` (docs-only; this file)
- **Recommended implementation branch:** `ops/v2-13-operational-pilot-cycle-1`
- **Based on:** v2.12 / PR #52 + PR #53 / tag `v2.12`
- **Status:** Planning
- **Goal:** Run first controlled operational pilot cycle and produce Go / Conditional Go / No-Go decision

### Strategic Purpose

v2.12 made OOS Operational Discovery Pilot ready.
v2.13 must answer:
**Is the Operational Discovery Pilot useful?**

```
    v2.12 delivered (implementation)              v2.13 delivers (operational decision)
    ────────────────────────────────              ──────────────────────────────────────
    PainCluster model + scoring                   Pilot Cycle 1 Brief
    HN RawEvidence hardening                      Hacker News Pilot Query Plan
    GitHub Issues RawEvidence hardening           GitHub Issues Repo Allowlist + Query Plan
    Cross-source dedupe + cluster assembly        Pilot Input Preparation
    Source Quality Report                         Pilot Run Procedure
    Founder Review Package                        Founder Review Protocol
    Operational Discovery Pilot orchestrator      Pilot Results Report
    Controlled pilot smoke                        Noise and Quality Analysis
    Final v2.12 checkpoint                        Go / Conditional Go / No-Go Decision
                                                  Final v2.13 checkpoint
```

### Core Concept

v2.13 is **operational, not feature expansion**. It takes the v2.12 pilot-ready pipeline and runs a controlled operational cycle with real or bounded inputs to produce evidence for a Go/No-Go decision. The output is not new code — it is a founder-reviewed decision about whether OOS discovery is working well enough to justify continued investment, source expansion, or pipeline repair.

### Strategic Principles

- **Operational, not expansionary.** v2.13 runs the pilot; it does not add features, sources, or layers.
- **Primary sources:** Hacker News + GitHub Issues.
- **Stack Exchange / Stack Overflow:** Optional/stretch only; requires explicit founder approval.
- **Broad source expansion remains deferred.** All additional sources wait for v2.13 Go decision.
- **Live source access requires explicit founder approval.** Default is fixture/bounded input mode.
- **No live APIs in unit tests.** Fixture-first preserved.
- **No LLM validation in default tests.** All scoring is deterministic.
- **Founder review is mandatory.** No automated Go/No-Go.
- **Traceability to source_url is mandatory.** Every candidate must trace back to a real `http(s)://` URL.
- **KillReason creation requires explicit founder review and decision.** Not automated.

### Scope

- Run first controlled operational pilot cycle on HN + GitHub Issues.
- Define founder ICP and preference profile to calibrate relevance.
- Prepare bounded query plans for HN and GitHub Issues.
- Prepare pilot inputs (fixture/manual bounded or live with founder approval).
- Execute pilot run and generate all artifacts.
- Conduct founder review of top clusters and opportunity candidates.
- Produce Pilot Results Report.
- Produce Noise and Quality Analysis.
- Make formal Go / Conditional Go / No-Go decision.
- Record decision and close v2.13.

### Explicit Non-Goals (Across All v2.13 Items)

- Product Hunt implementation
- pimenov.ai implementation
- Reddit
- Discord
- Slack
- X/Twitter
- AlternativeTo
- YC / Crunchbase
- App marketplaces
- Job boards
- Blogs / newsletters
- Broad scraping
- Automated founder decisions
- Autonomous source expansion
- Portfolio mutation
- KillReason creation unless founder explicitly reviews and decides
- Production deployment
- UI / dashboard work
- Database / server architecture
- Any source code, test, script, or example changes
- Committed repository artifacts unless explicitly approved per-item

### Artifact Policy (v2.13 Operational Pilot)

- **No committed repository artifacts unless explicitly approved per-item.** The repository must not accumulate unapproved runtime outputs.
- **Runtime pilot outputs are allowed only under explicit caller-provided `output_dir`.** The pilot orchestrator writes artifacts only when the caller supplies a destination directory; it does not default-write to `artifacts/` or any repository path.
- **Generated pilot outputs must remain uncommitted** unless explicitly approved as sample/evidence artifacts by the founder or by a roadmap item that authorizes committing specific outputs.
- **Validation and dev ledger reports may be committed only in the final checkpoint** (item 11) if the roadmap item explicitly allows them. Interim validation reports must not be committed.
- **No directory defaults.** The roadmap does not assume or hardcode `artifacts/`, `reports/`, or any output location. Caller controls destination.

### LLM Role Statement

LLM integration remains disabled in the v2.13 default pilot path. All scoring is deterministic. All clustering is rule-based. Existing LLM contracts remain in the codebase as future hooks but are not wired into discovery by default. The pilot cycle may optionally surface signals that suggest LLM-assisted classification could help — but such observations are recorded for v2.14 planning, not acted upon in v2.13.

### Workflow Rules

- Planning branch: `planning/v2-13-operational-pilot-go-no-go` (docs-only, this file).
- Implementation branch: `ops/v2-13-operational-pilot-cycle-1` (future; do not use planning branch for implementation).
- One local commit per roadmap item during execution.
- Push/PR/merge/tag only when explicitly requested.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Windows-native only: PowerShell, native Python venv, VS Code/Codex.
- No WSL/Linux-first assumptions.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.

### Founder Approval Gate (Planning → Execution Transition)

- **Planning roadmap merge does not authorize execution.** This roadmap is a planning/checklist deliverable only. Merging it to `main` records the plan; it does not grant license to begin the operational pilot cycle.
- **Execution branch requires explicit founder approval.** No work on `ops/v2-13-operational-pilot-cycle-1` may begin until the founder explicitly approves the transition from planning to execution.
- **No code, test, script, or artifact changes are authorized by this planning item.** Items 1–11 define operational pilot scope. None of these definitions are implementation.
- **Live source access requires explicit founder approval.** Default is fixture/bounded input mode.
- **Stack Exchange stretch requires explicit founder approval.** Default is excluded from pilot.
- **Go/No-Go decision requires founder review, not automated scoring alone.**

> Roadmap status tracks **12 planning items** (items 0–11). Item 0 (planning checkpoint) is the planning closure gate. Items 1–11 are the operational pilot execution checklist. This is a planning roadmap; execution happens on a separate branch after founder approval.

---

## 0. Planning Checkpoint

### Intent

Create the official Roadmap v2.13 planning checklist. Docs-only. No source code, tests, scripts, examples, artifacts, or generated outputs. This item closes the planning phase and gates the start of the operational pilot cycle.

### Allowed Change Type

- Create: `docs/roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md` (this file)

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| `docs/roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md` | Create | Full roadmap planning checklist |
| `docs/roadmaps/OOS_roadmap_v2_12_operational_discovery_pilot_checklist.md` | Read-only reference | Predecessor roadmap structure and template |
| `docs/vision.md` | Read-only reference | Project vision constraints |
| `docs/scope-v1.md` | Read-only reference | Scope boundaries |
| `docs/dev_ledger/00_project_state.md` | Read-only reference | Current project state |

### Validation Expectation

- `.\scripts\dev-git-check.ps1` passes.
- `git status --short` shows only the v2.13 roadmap file before commit.
- After commit, working tree is clean.

### Definition of Done

- [x] **0.0.1** Roadmap v2.13 document exists at `docs/roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md`.
- [x] **0.0.2** Roadmap state is `planning`; transitions to `ready for execution` when planning checkpoint closes.
- [x] **0.0.3** Current item is `0 — Planning checkpoint`.
- [x] **0.0.4** Completed: `0 / 12`.
- [x] **0.0.5** Remaining: `12 / 12`.
- [x] **0.0.6** Branch `planning/v2-13-operational-pilot-go-no-go` exists and is checked out.
- [x] **0.0.7** All sections present: overview, scope summary, non-goals, numbered checklist (0–11), pilot success criteria, pilot failure criteria, source gates, founder approval gates, validation commands, git discipline, recommended execution branch, v2.14 hook.
- [x] **0.0.8** `.\scripts\dev-git-check.ps1` passes.
- [x] **0.0.9** `git status --short` shows only this file before commit.
- [x] **0.0.10** One local commit made with message: `[v2.13] Populate operational pilot go-no-go roadmap`.

### Explicit Non-Goals

- Creating any source code files.
- Creating any test files.
- Creating any script files.
- Creating any artifact files.
- Modifying any existing file outside this roadmap document.
- Running the pilot.
- Making live API calls.
- Making LLM calls.

### Escalation Triggers

- If this file cannot be written to the expected path, escalate.
- If any file outside this roadmap must be modified to complete the planning checkpoint, escalate.

---

## 1. Founder ICP and Preference Profile

### Intent

Define the founder's Ideal Customer Profile (ICP) and preference profile to calibrate the pilot's relevance engine. Without an explicit ICP, the pilot cannot distinguish interesting opportunities from banal noise. This item creates a structured founder preference document that the pilot uses to filter and rank clusters and candidates.

### Allowed Change Type

- Create: Founder ICP and Preference Profile document (location TBD during execution — likely under `docs/` or `config/`)
- May read (do not modify): `src/oos/founder_preference_profile.py`, `docs/vision.md`, `docs/scope-v1.md`
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| Founder preference profile doc | Create | Structured ICP and preference definitions |
| `src/oos/founder_preference_profile.py` | Read-only reference | Existing preference profile model |
| `config/` | Read-only reference | Existing configuration patterns |

### Requirements

- [x] **1.1** Define interesting ICPs: target customer segments the founder wants to serve.
- [x] **1.2** Define excluded markets: markets/segments explicitly out of scope.
- [x] **1.3** Define preferred business types: SaaS, API-first, workflow automation, devtools, data products, etc.
- [x] **1.4** Define minimum business relevance: what threshold makes a pain signal relevant.
- [x] **1.5** Define what counts as an interesting opportunity: concrete, specific, actionable.
- [x] **1.6** Define what is banal/noise: generic pain, vague complaints, obvious trends.
- [x] **1.7** Define founder review rubric: how the founder will evaluate clusters and candidates during review.

### Validation Expectation

- ICP document exists and is complete.
- All 7 required definitions are present and non-empty.
- Document format supports machine consumption (structured fields) for potential downstream integration.
- Founder confirms ICP is accurate before pilot begins.

### Definition of Done

- [x] **1.8** Founder ICP and Preference Profile document exists.
- [x] **1.9** All 7 required definitions are populated.
- [x] **1.10** Founder has reviewed and approved the ICP document.
- [ ] **1.11** `.\scripts\dev-git-check.ps1` passes.
- [ ] **1.12** One local commit made.

### Explicit Non-Goals

- Implementing automated ICP matching in code.
- Modifying `src/oos/founder_preference_profile.py`.
- Defining ICPs for markets the founder is not interested in.
- Auto-classifying signals by ICP during this item (classification happens during pilot run).

### Escalation Triggers

- If the founder cannot define ICP with sufficient specificity for the pilot, escalate.
- If ICP definitions are too broad to produce meaningful relevance filtering, escalate.
- If defining ICP requires modifying source code, escalate.

---

## 2. Pilot Cycle 1 Brief

### Intent

Create the formal Pilot Cycle 1 brief that defines scope, expectations, success/failure criteria, timebox, and expected outputs. This brief is the operational contract for the first pilot cycle. It gates the start of any pilot execution.

### Allowed Change Type

- Create: Pilot Cycle 1 Brief document (location TBD during execution — likely under `docs/operations/`)
- May read (do not modify): `docs/contracts/operational_discovery_pilot_run_contract.md`, `docs/roadmaps/OOS_roadmap_v2_12_operational_discovery_pilot_checklist.md`
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| Pilot Cycle 1 Brief | Create | Formal pilot brief with scope, criteria, timebox |
| `docs/contracts/operational_discovery_pilot_run_contract.md` | Read-only reference | Pilot run contract from v2.11 |
| `docs/roadmaps/OOS_roadmap_v2_12_operational_discovery_pilot_checklist.md` | Read-only reference | Predecessor roadmap scope |

### Requirements

- [ ] **2.1** Define purpose: what question is this pilot cycle answering?
- [ ] **2.2** Define source scope: HN + GitHub Issues only; Stack Exchange stretch status.
- [ ] **2.3** Define expected evidence volume: 50–150 raw evidence items (or smaller if explicitly approved for first dry cycle).
- [ ] **2.4** Define success criteria: 1–2 genuinely interesting opportunities with traceability and manageable noise.
- [ ] **2.5** Define failure criteria: 90%+ noise, banal clusters, abstract candidates, broken traceability.
- [ ] **2.6** Define timebox: maximum calendar time for the pilot cycle.
- [ ] **2.7** Define expected output package: raw evidence, candidate signals, pain clusters, source quality report, founder review package.
- [ ] **2.8** Define founder review deadline: when the founder must complete review.

### Validation Expectation

- Pilot brief exists and is complete.
- All 8 required sections are present.
- Brief is specific enough to judge success/failure unambiguously.
- Founder approves the brief before pilot begins.

### Definition of Done

- [ ] **2.9** Pilot Cycle 1 Brief document exists.
- [ ] **2.10** All 8 required sections are populated.
- [ ] **2.11** Founder has reviewed and approved the brief.
- [ ] **2.12** `.\scripts\dev-git-check.ps1` passes.
- [ ] **2.13** One local commit made.

### Explicit Non-Goals

- Writing pilot execution code.
- Running any part of the pilot.
- Defining pilot cycles beyond Cycle 1.
- Expanding source scope beyond what v2.12 implemented.

### Escalation Triggers

- If success/failure criteria cannot be made specific enough to support a Go/No-Go decision, escalate.
- If expected evidence volume cannot be achieved with available sources, escalate.
- If the founder cannot commit to a review deadline, escalate.

---

## 3. Hacker News Pilot Query Plan

### Intent

Define the specific Hacker News search queries, filters, and collection parameters for Pilot Cycle 1. This plan ensures the pilot collects relevant evidence (not random HN content) and respects explicit scope boundaries (no broad scraping).

### Allowed Change Type

- Create: HN Pilot Query Plan document (location TBD during execution)
- May read (do not modify): `src/oos/hn_algolia_collector.py`, `src/oos/query_planner.py`, `config/source_registry.json`, `docs/decisions/hacker_news_connector_hardening_plan.md`
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| HN Pilot Query Plan | Create | Query definitions, filters, collection parameters |
| `src/oos/hn_algolia_collector.py` | Read-only reference | Existing HN collector capabilities |
| `config/source_registry.json` | Read-only reference | Source configuration |

### Requirements

- [ ] **3.1** Define Ask HN / Show HN / relevant search queries aligned with founder ICP.
- [ ] **3.2** Focus on AI agents / devtools / automation / data / workflow pain themes (or themes aligned with founder ICP from item 1).
- [ ] **3.3** Define minimum and maximum records per query to bound collection.
- [ ] **3.4** Identify query noise risks: which queries may produce high noise, and how to handle them.
- [ ] **3.5** Explicitly state: no broad scraping. Collection is query-bounded.
- [ ] **3.6** Require explicit `source_url` traceability for every collected item (`https://news.ycombinator.com/item?id=<id>`).
- [ ] **3.7** Define collection method: fixture/bounded manual vs. live (requires founder approval per FA gates).

### Validation Expectation

- Query plan exists and is complete.
- All 7 required sections are populated.
- Queries are aligned with founder ICP (cross-check with item 1 output).
- No query implies broad/unbounded scraping.

### Definition of Done

- [ ] **3.8** HN Pilot Query Plan document exists.
- [ ] **3.9** All 7 required sections are populated.
- [ ] **3.10** Query plan is aligned with founder ICP from item 1.
- [ ] **3.11** `.\scripts\dev-git-check.ps1` passes.
- [ ] **3.12** One local commit made.

### Explicit Non-Goals

- Executing HN queries or collecting data.
- Adding new HN API endpoints beyond Algolia Search API.
- Defining queries for sources other than HN.
- LLM-based query generation.

### Escalation Triggers

- If defined queries cannot produce evidence aligned with founder ICP, escalate.
- If noise risk assessment suggests >50% expected noise rate, escalate.
- If live HN collection is the only viable path but founder has not approved live access, escalate.

---

## 4. GitHub Issues Repo Allowlist and Query Plan

### Intent

Define the GitHub repository allowlist and issue search logic for Pilot Cycle 1. This plan ensures the pilot collects relevant issues from approved repositories only, excludes pull requests, and respects explicit scope boundaries.

### Allowed Change Type

- Create: GitHub Issues Repo Allowlist and Query Plan document (location TBD during execution)
- May read (do not modify): `src/oos/github_issues_collector.py`, `config/source_registry.json`, `docs/decisions/github_issues_connector_hardening_plan.md`
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| GitHub Issues Repo Allowlist + Query Plan | Create | Allowlist, search logic, collection parameters |
| `src/oos/github_issues_collector.py` | Read-only reference | Existing GitHub Issues collector capabilities |
| `config/source_registry.json` | Read-only reference | Source configuration |

### Requirements

- [ ] **4.1** Define repo allowlist: specific GitHub repositories approved for issue collection.
- [ ] **4.2** Define issue search logic: keywords, labels, state filters.
- [ ] **4.3** Exclude pull requests explicitly (enforce `pull_request` key filtering).
- [ ] **4.4** Require `html_url` for every collected issue (`https://github.com/<owner>/<repo>/issues/<number>`).
- [ ] **4.5** Focus on AI agents / devtools / data / automation / integration pain themes (aligned with founder ICP).
- [ ] **4.6** Require explicit `source_url` traceability for every collected item.
- [ ] **4.7** No default live access unless explicitly approved by founder.

### Validation Expectation

- Allowlist and query plan exist and are complete.
- All 7 required sections are populated.
- Allowlist repos are relevant to founder ICP.
- No repository is included without explicit justification.

### Definition of Done

- [ ] **4.8** GitHub Issues Repo Allowlist and Query Plan document exists.
- [ ] **4.9** All 7 required sections are populated.
- [ ] **4.10** Repo allowlist is aligned with founder ICP from item 1.
- [ ] **4.11** Founder has reviewed and approved the repo allowlist.
- [ ] **4.12** `.\scripts\dev-git-check.ps1` passes.
- [ ] **4.13** One local commit made.

### Explicit Non-Goals

- Executing GitHub queries or collecting issues.
- Adding repositories outside the allowlist.
- Collection from private repositories.
- LLM-based issue search generation.

### Escalation Triggers

- If the allowlist produces zero useful issues, escalate (allowlist may need expansion).
- If the allowlist includes repositories without clear relevance to founder ICP, escalate.
- If live GitHub Issues collection is required but founder has not approved live access, escalate.

---

## 5. Pilot Input Preparation Procedure

### Intent

Define the procedure for preparing pilot inputs: how raw evidence will be collected or assembled, whether live collection is opted in, how fixture/manual fallback works, and what validation occurs before the orchestrator runs.

### Allowed Change Type

- Create: Pilot Input Preparation Procedure document (location TBD during execution)
- May read (do not modify): `src/oos/operational_discovery_pilot.py`, `src/oos/hn_algolia_collector.py`, `src/oos/github_issues_collector.py`, `docs/contracts/operational_discovery_pilot_run_contract.md`
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| Pilot Input Preparation Procedure | Create | Step-by-step input preparation process |
| `src/oos/operational_discovery_pilot.py` | Read-only reference | Orchestrator input format |
| `docs/contracts/operational_discovery_pilot_run_contract.md` | Read-only reference | Pilot run contract |

### Requirements

- [ ] **5.1** Define how raw evidence will be collected or prepared: live collection vs. manual bounded input vs. fixture fallback.
- [ ] **5.2** Define live opt-in procedure: explicit founder approval gate, scope confirmation.
- [ ] **5.3** Define fixture/manual JSON fallback: how to prepare bounded input without live APIs.
- [ ] **5.4** Define validation before orchestrator: source identity checks, URL traceability, format validation.
- [ ] **5.5** Explicitly state: no deferred sources in pilot inputs (only HN + GitHub Issues, unless Stack Exchange stretch is approved).
- [ ] **5.6** Define source identity checks: every evidence item must carry correct `source_id` and `source_type`.

### Validation Expectation

- Input preparation procedure exists and is complete.
- All 6 required sections are populated.
- Procedure covers both live and fixture paths clearly.
- Founder understands and approves the chosen collection method.

### Definition of Done

- [ ] **5.7** Pilot Input Preparation Procedure document exists.
- [ ] **5.8** All 6 required sections are populated.
- [ ] **5.9** Collection method (live vs. fixture) is explicitly chosen and founder-approved.
- [ ] **5.10** `.\scripts\dev-git-check.ps1` passes.
- [ ] **5.11** One local commit made.

### Explicit Non-Goals

- Writing collection scripts.
- Implementing new input formats.
- Modifying the orchestrator input schema.
- Collecting data by any method before founder approval.

### Escalation Triggers

- If the chosen collection method cannot produce sufficient evidence volume, escalate.
- If fixture preparation requires data that cannot be obtained without live APIs, escalate.
- If source identity checks reveal systemic mismatches in available data, escalate.

---

## 6. Pilot Run Procedure

### Intent

Define the step-by-step procedure for executing the operational discovery pilot on the prepared inputs. This covers running the orchestrator, verifying all output artifacts, and confirming traceability and source scope before founder review.

### Allowed Change Type

- Create: Pilot Run Procedure document (location TBD during execution)
- May read (do not modify): `src/oos/operational_discovery_pilot.py`, `docs/contracts/operational_discovery_pilot_run_contract.md`, `docs/contracts/pain_cluster_contract.md`
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| Pilot Run Procedure | Create | Step-by-step execution procedure |
| `src/oos/operational_discovery_pilot.py` | Read-only reference | Orchestrator entrypoint and output format |
| `docs/contracts/operational_discovery_pilot_run_contract.md` | Read-only reference | Pilot run contract |

### Requirements

- [ ] **6.1** Define the exact command(s) to run the operational discovery pilot on bounded inputs.
- [ ] **6.2** Define expected artifacts: raw evidence, candidate signals, pain clusters, source quality report, founder review package.
- [ ] **6.3** Define verification steps for each artifact: existence, format, content quality.
- [ ] **6.4** Define traceability verification: every candidate signal traces to a real `source_url`.
- [ ] **6.5** Define source scope verification: only `hacker_news` and `github_issues` appear; no deferred sources.
- [ ] **6.6** Explicitly state: no live APIs unless explicitly approved by founder.

### Validation Expectation

- Pilot run procedure exists and is complete.
- All 6 required sections are populated.
- Procedure is specific enough to execute without ambiguity.

### Definition of Done

- [ ] **6.7** Pilot Run Procedure document exists.
- [ ] **6.8** All 6 required sections are populated.
- [ ] **6.9** `.\scripts\dev-git-check.ps1` passes.
- [ ] **6.10** One local commit made.

### Explicit Non-Goals

- Executing the pilot run.
- Modifying the orchestrator.
- Adding new verification tools.
- Automating the run procedure (manual execution is acceptable for Cycle 1).

### Escalation Triggers

- If the orchestrator cannot produce all required artifacts from available inputs, escalate.
- If traceability verification reveals systemic URL failures, escalate.
- If source scope verification finds deferred sources in pilot outputs, escalate.

---

## 7. Founder Review Protocol

### Intent

Define the structured protocol for founder review of pilot outputs. This protocol ensures the founder reviews top clusters and opportunity candidates systematically, records decisions in structured form, and captures validation actions. The protocol prevents the review from devolving into unstructured browsing.

### Allowed Change Type

- Create: Founder Review Protocol document (location TBD during execution)
- May read (do not modify): `src/oos/pilot_founder_review_package.py`, `src/oos/founder_decision_taxonomy.py`, `docs/contracts/operational_discovery_pilot_run_contract.md`
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| Founder Review Protocol | Create | Structured review process and decision recording |
| `src/oos/pilot_founder_review_package.py` | Read-only reference | Review package format |
| `src/oos/founder_decision_taxonomy.py` | Read-only reference | Decision taxonomy |

### Requirements

- [ ] **7.1** Define review scope: top clusters and opportunity candidates to review, ranked by score.
- [ ] **7.2** Define the five decision types with criteria:
  - `PROMOTE` — opportunity worth real validation.
  - `PARK` — interesting but not now.
  - `KILL` — not worth pursuing; requires explicit `KillReason`.
  - `NEEDS_MORE_EVIDENCE` — promising but insufficient data.
  - `REVISIT_LATER` — check again after more cycles.
- [ ] **7.3** Require founder notes for every reviewed item.
- [ ] **7.4** Require classification of each item: interesting / banal / unclear / actionable.
- [ ] **7.5** Define validation action capture for promoted items:
  - `interview` — talk to potential users.
  - `landing_page` — test demand with a landing page.
  - `manual_research` — deeper manual investigation.
  - `collect_more_evidence` — expand source scope for this pain.
  - `kill_no_action` — kill with no further action.
- [ ] **7.6** Define how decisions are recorded and where they are stored.

### Validation Expectation

- Founder review protocol exists and is complete.
- All 6 required sections are populated.
- Decision types have clear criteria.
- Protocol produces structured decision records, not free-form notes.

### Definition of Done

- [ ] **7.7** Founder Review Protocol document exists.
- [ ] **7.8** All 6 required sections are populated.
- [ ] **7.9** Founder confirms they can follow the protocol within the review timebox.
- [ ] **7.10** `.\scripts\dev-git-check.ps1` passes.
- [ ] **7.11** One local commit made.

### Explicit Non-Goals

- Automating founder decisions.
- Creating KillReason records automatically.
- Implementing the review protocol in code.
- Building a review UI or dashboard.

### Escalation Triggers

- If the review protocol requires more time than the founder can commit, escalate.
- If decision criteria are too ambiguous to produce consistent Go/No-Go input, escalate.
- If KillReason creation cannot be done without modifying source code, escalate.

---

## 8. Pilot Results Report

### Intent

Define the structure and requirements for the Pilot Results Report. This report aggregates all pilot outputs into a single document that supports the Go/No-Go decision. It covers quantitative metrics (counts, scores, traceability status) and qualitative observations (noise categories, operational friction).

### Allowed Change Type

- Create: Pilot Results Report template and final report (location TBD during execution)
- May read (do not modify): `src/oos/source_quality_report.py`, `src/oos/pilot_founder_review_package.py`, `docs/contracts/operational_discovery_pilot_run_contract.md`
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| Pilot Results Report | Create | Aggregated pilot results |
| `src/oos/source_quality_report.py` | Read-only reference | Source quality metrics |
| `src/oos/pilot_founder_review_package.py` | Read-only reference | Review package format |

### Requirements

- [ ] **8.1** Report raw evidence count (total, per-source).
- [ ] **8.2** Report candidate signal count.
- [ ] **8.3** Report pain cluster count.
- [ ] **8.4** Report opportunity candidate count.
- [ ] **8.5** Report source quality by source (signal rate, noise rate, missing URLs, etc.).
- [ ] **8.6** Identify noise categories observed.
- [ ] **8.7** Summarize founder review outcomes (promote/park/kill/needs_more_evidence/revisit_later counts).
- [ ] **8.8** List top 3–5 opportunities with scores and traceability status.
- [ ] **8.9** Report traceability status (total URLs, missing, placeholder, validation pass/fail).
- [ ] **8.10** Report operational friction: any issues encountered during the pilot run.

### Validation Expectation

- Pilot results report exists and is complete.
- All 10 required sections are populated.
- Quantitative metrics are accurate (cross-checked against raw artifacts).
- Report supports a clear Go/No-Go recommendation.

### Definition of Done

- [ ] **8.11** Pilot Results Report document exists.
- [ ] **8.12** All 10 required sections are populated with actual pilot data.
- [ ] **8.13** Report includes explicit traceability status.
- [ ] **8.14** `.\scripts\dev-git-check.ps1` passes.
- [ ] **8.15** One local commit made.

### Explicit Non-Goals

- Automating report generation (manual assembly from pilot artifacts is acceptable for Cycle 1).
- Creating a real-time dashboard.
- Making the report machine-readable beyond JSON artifacts already produced.

### Escalation Triggers

- If pilot artifacts are insufficient to populate all report sections, escalate.
- If traceability verification reveals systemic failures, escalate.
- If quantitative metrics contradict qualitative observations, escalate.

---

## 9. Noise and Quality Analysis

### Intent

Conduct a structured analysis of noise and quality issues observed during the pilot cycle. This analysis identifies what worked, what produced noise, and what needs improvement. It directly informs the Go/No-Go decision and, if Conditional Go, defines the v2.14 quality improvement scope.

### Allowed Change Type

- Create: Noise and Quality Analysis document (location TBD during execution)
- May read (do not modify): `src/oos/source_quality_report.py`, `src/oos/pain_cluster.py`, pilot output artifacts
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| Noise and Quality Analysis | Create | Structured noise/quality findings |
| `src/oos/source_quality_report.py` | Read-only reference | Source quality metrics |
| Pilot run artifacts | Read-only input | Raw data for analysis |

### Requirements

- [ ] **9.1** Identify high-noise sources/queries/repos: which inputs produced the most noise.
- [ ] **9.2** Identify weak scoring areas: where did scoring fail to match evidence quality.
- [ ] **9.3** Identify clustering failures: where did pain clusters miss real patterns or merge unrelated pains.
- [ ] **9.4** Identify overly abstract opportunities: which candidates were too vague to act on.
- [ ] **9.5** Identify founder review burden: how much manual effort was required, and whether it was sustainable.
- [ ] **9.6** Recommend v2.14 quality fixes if needed: specific, scoped improvements for next cycle.

### Validation Expectation

- Noise and quality analysis exists and is complete.
- All 6 required sections are populated.
- Analysis is evidence-based (cites specific clusters, sources, or metrics).
- Recommendations are specific and scoped (not vague "improve scoring").

### Definition of Done

- [ ] **9.7** Noise and Quality Analysis document exists.
- [ ] **9.8** All 6 required sections are populated with evidence from the pilot.
- [ ] **9.9** `.\scripts\dev-git-check.ps1` passes.
- [ ] **9.10** One local commit made.

### Explicit Non-Goals

- Implementing noise fixes during v2.13.
- Modifying scoring weights or clustering logic.
- Adding new noise detection modules.
- Automated noise classification.

### Escalation Triggers

- If noise analysis reveals that >90% of evidence is noise, escalate (this is a failure criterion).
- If scoring systematically contradicts founder judgment, escalate.
- If clustering failures affect >50% of clusters, escalate.

---

## 10. Go / Conditional Go / No-Go Decision

### Intent

Make the formal Go / Conditional Go / No-Go decision based on pilot results, noise analysis, and founder review. This is the primary output of v2.13. The decision determines the next roadmap direction: source expansion, quality improvement, or pipeline repair.

### Allowed Change Type

- Create: Go/No-Go Decision document (location TBD during execution)
- May read (do not modify): Pilot Results Report, Noise and Quality Analysis, founder review decisions
- Do NOT modify source code, tests, scripts, or artifacts.

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| Go/No-Go Decision | Create | Formal decision with rationale and next steps |
| Pilot Results Report | Read-only input | Evidence for decision |
| Noise and Quality Analysis | Read-only input | Quality evidence for decision |
| Founder review decisions | Read-only input | Founder judgment |

### Decision Criteria

- [ ] **10.1** **GO** — if pilot produces 1–2 genuinely interesting opportunities with traceability and manageable noise:
  - Opportunities are specific, actionable, aligned with founder ICP.
  - Noise is manageable (<50% of evidence).
  - Founder review was useful, not burdensome.
  - Traceability is clean (zero placeholder/missing URLs).
  - Scoring aligns with founder judgment.
  - **Next roadmap:** source expansion or second pilot cycle.
- [ ] **10.2** **CONDITIONAL GO** — if opportunities exist but quality/scoring/filtering needs improvement:
  - Some interesting signals but also significant noise.
  - Scoring partially aligns with founder judgment but needs tuning.
  - Founder review was somewhat burdensome but produced insights.
  - Traceability is acceptable but has minor issues.
  - **Next roadmap:** v2.14 Pilot Quality Improvements.
- [ ] **10.3** **NO-GO** — if pilot produces mostly noise, banal opportunities, or broken scoring:
  - 90%+ noise.
  - Banal/generic pain clusters.
  - Abstract, unactionable opportunity candidates.
  - Founder review feels like manual trash sorting.
  - Scoring systematically contradicts founder judgment.
  - Broken traceability.
  - No idea worth validating.
  - **Next roadmap:** Core Discovery Pipeline Repair.
- [ ] **10.4** Define next roadmap based on result (v2.14 hook).
- [ ] **10.5** Record decision with explicit rationale citing pilot evidence.

### Validation Expectation

- Go/No-Go decision document exists.
- Decision is clearly stated with supporting evidence from pilot outputs.
- Next roadmap direction is explicitly defined.
- Founder has signed off on the decision.

### Definition of Done

- [ ] **10.6** Go/No-Go Decision document exists.
- [ ] **10.7** Decision is recorded (GO / CONDITIONAL GO / NO-GO) with rationale.
- [ ] **10.8** Next roadmap direction is explicitly stated.
- [ ] **10.9** Founder has reviewed and signed off on the decision.
- [ ] **10.10** `.\scripts\dev-git-check.ps1` passes.
- [ ] **10.11** One local commit made.

### Explicit Non-Goals

- Making the decision without founder review.
- Automating the Go/No-Go calculus.
- Starting the next roadmap during v2.13.
- Expanding sources before the Go decision is recorded.

### Escalation Triggers

- If pilot results are ambiguous and do not clearly support GO, CONDITIONAL GO, or NO-GO, escalate.
- If founder disagrees with the evidence-based recommendation, escalate.
- If the decision requires information not produced by the pilot, escalate.

---

## 11. Final v2.13 Checkpoint

### Intent

Close the v2.13 operational pilot cycle. Verify all items are complete, all documents are committed, the Go/No-Go decision is recorded, and the dev ledger is updated. Do not start v2.14 without explicit roadmap.

### Allowed Change Type

- Update: roadmap overview trackers (0.1–0.6) in this file.
- Create: `docs/dev_ledger/03_run_reports/` run report for v2.13 closure.
- May read (do not modify): all project files for validation.
- Do NOT modify source code, tests, scripts, or artifacts (except this file and the run report).

### Main Files Likely Affected

| File | Action | Scope |
|------|--------|-------|
| This file | Update | Trackers, final state |
| `docs/dev_ledger/03_run_reports/` | Create | v2.13 closure run report |
| `docs/dev_ledger/00_project_state.md` | Read-only reference | Current project state for context |

### Validation Expectation

- All operational items (1–10) are complete and committed.
- Go/No-Go decision is recorded.
- `.\scripts\dev-git-check.ps1` passes.
- `.\scripts\dev-validate-final.ps1` passes.
- `.\scripts\run-controlled-smoke.ps1` passes.
- Roadmap overview trackers (0.1–0.6) updated to reflect completion.
- Dev ledger updated.

### Definition of Done

- [ ] **11.1** All operational items (1–10) are complete and committed.
- [ ] **11.2** Go/No-Go decision is recorded with rationale.
- [ ] **11.3** Roadmap overview trackers (0.1–0.6) updated: state → `complete`, current item → `none / complete`, completed → `12 / 12`, remaining → `0 / 12`.
- [ ] **11.4** Closure run report exists at `docs/dev_ledger/03_run_reports/`.
- [ ] **11.5** `.\scripts\run-controlled-smoke.ps1` passes.
- [ ] **11.6** `.\scripts\dev-validate-final.ps1` passes.
- [ ] **11.7** `.\scripts\dev-git-check.ps1` passes.
- [ ] **11.8** Do not start v2.14 without explicit roadmap.
- [ ] **11.9** One local commit made.

### Explicit Non-Goals

- Starting v2.14 implementation.
- Modifying pipeline code.
- Creating new sources.
- Pushing, creating PR, merging, or tagging.

### Escalation Triggers

- If any operational item is incomplete and cannot be completed, escalate.
- If the Go/No-Go decision has not been recorded, escalate.
- If validation fails and cannot be resolved without code changes, escalate.

---

## Pilot Success Criteria

v2.13 is successful if the pilot cycle produces a clear Go/No-Go decision supported by evidence. Specific quantitative targets:

| Metric | Target | Notes |
|--------|--------|-------|
| Raw evidence items | 50–150 | Or smaller if explicitly approved for first dry cycle |
| Candidate signals | 10–30 | Proportionate to evidence volume |
| Pain clusters | 3–7 | Cross-source where possible |
| Opportunity candidates | 3–5 | Quality over quantity |
| Ideas worth real validation | 1–2 | Specific, actionable, ICP-aligned |
| Source URL traceability | 100% for every candidate | Zero placeholder or missing URLs |
| Founder review | Manageable and useful | Not manual trash sorting |
| Source quality report | Helps decide what to tune | Actionable insights |

---

## Pilot Failure Criteria

A bad result looks like:

- **90%+ noise** — overwhelming majority of evidence is irrelevant.
- **Banal/generic pain clusters** — "people want faster software", "AI is changing everything".
- **Abstract opportunity candidates** — "an AI-powered platform for developers", "a better DevOps tool".
- **Source quality report does not help decisions** — metrics exist but provide no actionable insight.
- **Founder review feels like manual trash sorting** — no learning, no useful output, high burden.
- **Scoring does not match founder judgment** — systematic divergence between scores and reality.
- **Broken traceability** — placeholder URLs, missing evidence chains, unresolvable sources.
- **No idea worth validating** — nothing passes the "would I test this?" threshold.

If the pilot fails, the system must not proceed to source expansion. The Go/No-Go decision must route to pipeline repair.

---

## Source Gates

These gates are enforced during v2.13 execution. Any violation must be detected and escalated:

| # | Gate | Enforcement |
|---|------|-------------|
| G1 | No Product Hunt in v2.13 | Rejected if `product_hunt` appears in any pilot input or output |
| G2 | No pimenov.ai in v2.13 | Rejected if `pimenov_ai` appears in any pilot input or output |
| G3 | No deferred sources; gate by `source_id` | Default allowed `source_id`: `hacker_news`, `github_issues`. Default allowed `source_type`: `discussion`, `issue_tracker`. Stack Exchange / Stack Overflow (`stack_exchange`, `stack_overflow`) allowed only if explicitly approved as stretch. Rejected if any deferred `source_id` appears: `product_hunt`, `pimenov_ai`, `reddit`, `discord`, `slack`, `x_twitter` / `twitter` / `x`, `alternative_to`, `yc` / `y_combinator` / `crunchbase`, app marketplaces, job boards, blogs/newsletters, `broad_web_crawl`. Do not rely on `source_type` alone to distinguish allowed vs deferred sources. |
| G4 | No Stack Exchange unless explicitly approved as stretch | Rejected unless founder has explicitly approved stretch |
| G5 | No live source access without explicit founder approval | Default is fixture/bounded input; live requires explicit opt-in |
| G6 | No source without source_url traceability | Every evidence item must have a real `http(s)://` URL |
| G7 | No source promoted to default path without controlled smoke | Source status changes require controlled smoke pass |

---

## Founder Approval Gates

| # | Gate | Detail |
|---|------|--------|
| FA1 | Pilot cycle starts only after roadmap approval | This planning file must be merged to main before execution begins |
| FA2 | Execution branch requires explicit founder approval | `ops/v2-13-operational-pilot-cycle-1` must be explicitly authorized |
| FA3 | Live HN collection requires explicit founder approval | Must not be default; opt-in only |
| FA4 | Live GitHub Issues collection requires explicit founder approval | Must not be default; opt-in only |
| FA5 | GitHub repo allowlist requires founder approval | Founder must review and approve the allowlist before collection |
| FA6 | Stack Exchange stretch requires explicit founder approval | Must not be included in default pilot path |
| FA7 | Go/No-Go decision requires founder review, not automated scoring alone | The decision is founder-made, evidence-supported |

---

## Validation Commands

Use only the following wrapper scripts for validation during v2.13 execution:

```
.\scripts\dev-git-check.ps1
.\scripts\dev-test.ps1
.\scripts\run-controlled-smoke.ps1
.\scripts\dev-validate-final.ps1
```

Do NOT use chained shell commands for validation. Each validation step must use a single wrapper script.

---

## Git Discipline

- One roadmap/planning branch for this file: `planning/v2-13-operational-pilot-go-no-go`.
- One operation branch after roadmap merge: `ops/v2-13-operational-pilot-cycle-1`.
- One local commit per roadmap item during execution.
- Push/PR/merge/tag only when explicitly requested.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Planning branch only creates and maintains the roadmap. Do NOT push, create PR, merge, or tag from this branch unless explicitly approved.

---

## Recommended Execution Branch

After planning merge to main, create:

```
ops/v2-13-operational-pilot-cycle-1
```

This branch executes items 1–11 from this roadmap. It is an operational branch (not a feature branch) — it runs the pilot, produces documents, and records the Go/No-Go decision.

---

## v2.14 Hook

Based on the v2.13 Go/No-Go decision:

- **GO:** Second pilot cycle or cautious source expansion planning.
  - Evaluate which sources to add next (Stack Exchange, then one at a time).
  - Run a second pilot cycle to confirm findings.
  - Begin planning controlled source expansion.

- **CONDITIONAL GO:** v2.14 Pilot Quality Improvements.
  - Implement fixes identified in Noise and Quality Analysis.
  - Tune scoring weights based on founder feedback.
  - Improve clustering for identified failure modes.
  - Reduce founder review burden.
  - Re-run pilot after fixes and re-evaluate.

- **NO-GO:** Core Discovery Pipeline Repair.
  - Diagnose root causes of pipeline failure.
  - Fix scoring, clustering, or traceability as needed.
  - Reconsider source strategy and ICP alignment.
  - Do not expand sources until pipeline fundamentals are solid.

---

## Deferred Sources (v2.14+ Only Conditional on Go Decision)

The following source candidates are explicitly deferred to v2.14+ and are conditional on a Go or Conditional Go decision in v2.13. They are noted here to prevent scope creep:

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
| pimenov.ai | Expert/context source, not direct pain source | v2.14+ (conditional) |
| G2/Capterra/review sites | ToS review required; scraping risk; paywall barriers | v2.14+ (conditional) |
| Job boards (LinkedIn, Indeed, etc.) | Scraping risk; ToS barriers | v2.14+ (conditional) |
| App marketplaces (Google Play, App Store) | Review-based signals; scraping risk | v2.14+ (conditional) |
| Stack Exchange / Stack Overflow | Optional stretch source for pilot; reassess inclusion after Cycle 1 | v2.13 (reassessment via stretch gate) |

---

*Roadmap v2.13 — Operational Pilot Cycle 1 / Go-No-Go Decision. Planning phase. Docs-only. Do not execute without explicit founder approval.*
