# OOS Roadmap v2.7 — Traceability Hardening & Real-Run Readiness

## 0. Roadmap Overview

### Active Roadmap

- [ ] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_7_traceability_and_real_run_readiness_checklist.md`
- [ ] **0.2** Current item: `1.1 Source URL traceability contract`
- [ ] **0.3** Roadmap state: `active / planned`
- [ ] **0.4** Completed from this roadmap: **0 / 8**
- [ ] **0.5** Remaining: **8 / 8**
- [ ] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_6_real_weekly_loop_operationalization_checklist.md` (complete, `9 / 9`, tag `v2.6` created, merged to main)

### Core Concept

Roadmap v2.6 connected v2.5 components into a running weekly operating loop with CLI, founder inbox, decision import, status, run reports, and end-to-end fixture validation. Roadmap v2.7 hardens the traceability chain and founder workflow so that the weekly loop is production-ready for real, repeated use.

```
    v2.6 delivered                        v2.7 hardens
    ─────────────                         ─────────────
    WeeklyRunManifest                     source_urls at every hop
    Unified weekly cycle builder          no placeholder URNs
    CLI: run-weekly-cycle-v2              FounderInboxReviewItem source_urls
    Founder Inbox v2                      FounderDecisionImport real URLs
    Founder Decision Import               E2E source URL traceability gate
    weekly-cycle-status-v2               decision re-import policy
    Run reports + dashboard index         dev workflow helper scripts
    Fixture E2E validation (v2.6)        controlled real-run smoke test
```

### Strategic Principles

- **Traceability hardening first.** Every artifact in the chain must carry real `source_urls`; placeholder URNs are a bug.
- **Real-run readiness.** The founder must be able to run a bounded weekly cycle with real signals, review the inbox, record decisions, and verify the full traceability chain without surprises.
- **Developer workflow automation.** Common operations (git snapshot, validation check, post-merge sync, PR readiness) should be one command.
- **Deterministic-first preserved.** All hardening must maintain deterministic output; no live LLM/API calls by default.
- **Advisory-only preserved.** No autonomous portfolio transitions.
- **No new product layers.** This is hardening, not feature expansion.
- **Do not rewrite v2.6.** Only fix known gaps and add workflow support.

### Explicit Out Of Scope

- New collectors, new sources, or source expansion.
- Live LLM/API calls by default. LLM hooks remain disabled/future-only.
- Autonomous portfolio transitions.
- UI/dashboard work beyond file-system Markdown + JSON.
- Embeddings/vector search.
- ML training claims from founder feedback.
- Database or persistent server.
- Multi-user, multi-tenant, or venture-studio mode.
- Reddit, Facebook, LinkedIn, scraping-heavy sources, or paid APIs.
- New product layers (Pain Discovery Layer integration, automated periodic runs, email/push notifications).
- Rebuilding or redesigning the weekly cycle pipeline.
- Expanding beyond the existing HN + GitHub source loop.

### LLM Role Statement

LLM integration belongs later (`v2.8+`) unless present only as disabled/future hooks. The v2.7 hardened pipeline must complete deterministically. Existing LLM contracts remain in the codebase but are not wired into the default weekly cycle path.

### Workflow Rules

- One feature block = one branch. This planning checkpoint is docs-only on `planning/v2-7-roadmap`.
- Local commit per item during implementation.
- Push/PR/merge only at the end of a feature block and only when explicitly requested.
- Windows-native only: PowerShell, native Python venv, VS Code/Codex.
- No WSL/Linux-first assumptions.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.
- Live source runs are explicit, bounded, and approval-gated.

> Roadmap status tracks **8 implementation items** (items 1.1–6.1). Item 0.1 (planning) is complete and not counted in the implementation total. Items 0.2–0.6 are roadmap-state trackers and are not counted in the implementation total. Items 1.1–5.1 are implementation; item 6.1 is the final checkpoint.

---

## 0.1 Roadmap v2.7 Planning

### Goal

Create the official Roadmap v2.7 planning checklist, mini-epic, run report, and update the Dev Ledger project state to make v2.7 the active planned roadmap.

### Scope

- Create this roadmap checklist document.
- Create `docs/dev_ledger/02_mini_epics/0.1-roadmap-v2-7-planning.md`.
- Create `docs/dev_ledger/03_run_reports/0.1-roadmap-v2-7-planning.md`.
- Update `docs/dev_ledger/00_project_state.md` to transition from v2.6 (complete) to v2.7 (active/planned).
- Docs-only. No source code changes. No tests. No artifacts. No live API/LLM calls.

### Expected files

- `docs/roadmaps/OOS_roadmap_v2_7_traceability_and_real_run_readiness_checklist.md`
- `docs/dev_ledger/02_mini_epics/0.1-roadmap-v2-7-planning.md`
- `docs/dev_ledger/03_run_reports/0.1-roadmap-v2-7-planning.md`
- `docs/dev_ledger/00_project_state.md` (update)

### Acceptance criteria

- [x] **0.1.1** Roadmap v2.7 document exists at the expected path with all sections.
- [x] **0.1.2** Roadmap state is `active / planned`.
- [x] **0.1.3** Current item is `1.1 Source URL traceability contract`.
- [x] **0.1.4** Completed: `0 / 8`.
- [x] **0.1.5** Remaining: `8 / 8`.
- [x] **0.1.6** Mini-epic document exists.
- [x] **0.1.7** Run report exists.
- [x] **0.1.8** Dev Ledger project state is updated.
- [x] **0.1.9** `git diff --check` clean; `git status --short -uall` clean (docs-only changes).
- [x] **0.1.10** One local commit made.

---

## 1. Source URL Traceability

## 1.1 Source URL traceability contract

### Goal

Define the canonical source URL traceability contract for the v2.6+ weekly loop: every artifact in the chain must carry real `source_urls`, and placeholder URNs (`urn:oos:founder_import:placeholder`) used by the founder decision import must be replaced with real source URLs propagated from upstream artifacts.

### Known Gap

The v2.6 founder decision import (`src/oos/founder_decision_import.py`, line 517–518) uses `urn:oos:founder_import:placeholder` when `source_urls` is empty after collecting evidence items. This placeholder leaks into `FounderDecisionV2.linked_source_urls`, `FounderFeedbackMapping.source_urls`, `FounderFeedbackMapping.target.source_urls`, and all downstream artifacts. No upstream artifact should lose its real source URLs, so the placeholder is a failure to propagate, not a data absence.

### Scope

- Audit every module in the weekly cycle pipeline that carries `source_urls` or `linked_source_urls`:
  - `evidence_pack.py` — `EvidencePack.source_urls`
  - `evidence_pack_builder.py` — propagates from `CandidateSignal.source_url`
  - `opportunity_sketch.py` — `OpportunityCandidate.source_urls`
  - `opportunity_quality_gate.py` — `OpportunityGateResult.source_urls`
  - `evidence_sufficiency_scoring.py` — `EvidenceSufficiencyScore.source_urls`
  - `opportunity_false_positive_suppressor.py` — `OpportunityFalsePositiveAssessment.source_urls`
  - `founder_decision_taxonomy.py` — `FounderDecisionV2.linked_source_urls`
  - `founder_feedback_mapping.py` — `FounderFeedbackMapping.source_urls`, `TargetReference.source_urls`
  - `founder_inbox_v2.py` — `FounderInboxReviewItem` (currently missing `linked_source_urls`)
  - `founder_decision_import.py` — collects and forwards source URLs (currently uses placeholder)
  - `weekly_cycle_builder.py` — orchestrates all of the above
- Define a `SourceURLTraceability` contract documenting:
  - Required `source_urls` / `linked_source_urls` field for every artifact type.
  - Minimum cardinality: at least one real URL (not a `urn:` placeholder) per item.
  - Validation rule: placeholder URNs are treated as missing traceability.
  - Empty-state exception: insufficient-evidence artifacts may have empty `source_urls` with an explicit `insufficient_evidence: true` flag.

### Expected files

- `docs/contracts/source_url_traceability_contract.md` (new)
- `src/oos/source_url_traceability.py` (new) — `SourceURLTraceabilityReport` model, validation helpers
- `tests/test_source_url_traceability.py` (new)
- `docs/dev_ledger/02_mini_epics/1.1-source-url-traceability-contract.md`
- `docs/dev_ledger/03_run_reports/1.1-source-url-traceability-contract.md`

### Acceptance criteria

- [ ] **1.1.1** `SourceURLTraceabilityReport` model exists with fields for each artifact type and its source URL status.
- [ ] **1.1.2** Validation helper `check_source_url_traceability(run_dir)` scans all artifacts in a weekly run and reports which items have placeholder URNs or missing source URLs.
- [ ] **1.1.3** Audit confirms every relevant module's `source_urls` / `linked_source_urls` field is documented.
- [ ] **1.1.4** Contract document lists the expected traceability path: `CandidateSignal.source_url` → `EvidencePack.source_urls` → `OpportunityCandidate.source_urls` → `OpportunityGateResult.source_urls` → `FounderInboxReviewItem.linked_source_urls` → `FounderDecisionV2.linked_source_urls` → `FounderFeedbackMapping.source_urls`.
- [ ] **1.1.5** Placeholder URN detection works: `urn:oos:*` patterns are flagged as traceability gaps.
- [ ] **1.1.6** Insufficient-evidence artifacts with `insufficient_evidence: true` are exempt from placeholder checks.
- [ ] **1.1.7** Focused tests pass; no live APIs/LLMs; no autonomous decisions.

---

## 1.2 Founder Inbox source URL propagation

### Goal

Add a `linked_source_urls` field to `FounderInboxReviewItem` and populate it from upstream evidence packs and opportunity candidates during inbox generation.

### Known Gap

`FounderInboxReviewItem` (in [`src/oos/founder_inbox_v2.py`](src/oos/founder_inbox_v2.py:116)) has `linked_evidence_ids`, `linked_opportunity_ids`, `linked_source_artifact_ids`, but no `linked_source_urls`. The inbox index JSON is the machine-readable record that the founder decision import reads from. Without source URLs in the inbox, the decision import cannot propagate real URLs.

### Scope

- Add `linked_source_urls: list[str]` field to `FounderInboxReviewItem`.
- Update `FounderInboxReviewItem.to_dict()` to include `linked_source_urls`.
- In `build_founder_inbox_v2()`, populate `linked_source_urls` from:
  - Evidence packs' `source_urls` for evidence-derived review items.
  - Opportunity candidates' `source_urls` for opportunity-derived review items.
  - Empty list for synthetic/derived items (e.g., next-best actions with no direct evidence lineage).
- Update `FounderInboxReviewItem` validation to allow empty `linked_source_urls` only when the item has no evidence lineage (explicitly noted).
- Update the inbox index JSON schema to include `linked_source_urls`.
- Update the Markdown inbox rendering to optionally display source URLs (compact, linked representation where possible).

### Expected files

- `src/oos/founder_inbox_v2.py` (modify — add field, update builder, update to_dict)
- `tests/test_founder_inbox_v2.py` (modify — add source URL assertions)
- `docs/dev_ledger/02_mini_epics/1.2-founder-inbox-source-url-propagation.md`
- `docs/dev_ledger/03_run_reports/1.2-founder-inbox-source-url-propagation.md`

### Acceptance criteria

- [ ] **1.2.1** `FounderInboxReviewItem` has a `linked_source_urls: list[str]` field with default `[]`.
- [ ] **1.2.2** `FounderInboxReviewItem.to_dict()` includes `linked_source_urls`.
- [ ] **1.2.3** Review items built from evidence packs have non-empty `linked_source_urls` (when source URLs exist upstream).
- [ ] **1.2.4** Review items built from opportunity candidates have non-empty `linked_source_urls`.
- [ ] **1.2.5** Synthetic items (e.g., next-best actions without evidence lineage) have empty `linked_source_urls` without error.
- [ ] **1.2.6** Existing inbox tests pass with the new field (backward compatible — new field defaults to `[]`).
- [ ] **1.2.7** New focused tests verify source URL propagation from evidence packs and opportunity candidates through inbox items.
- [ ] **1.2.8** No live APIs/LLMs; no autonomous decisions.

---

## 1.3 Founder Decision Import source URL propagation

### Goal

Replace the `urn:oos:founder_import:placeholder` in [`src/oos/founder_decision_import.py`](src/oos/founder_decision_import.py:518) with real source URLs propagated from the founder inbox index, evidence packs, and opportunity candidates.

### Known Gap

The current `import_founder_decisions()` in [`src/oos/founder_decision_import.py`](src/oos/founder_decision_import.py) collects `source_urls` from evidence items when building `FounderDecisionV2` and `FounderFeedbackMapping` records. When no source URLs are collected (which currently happens because the inbox doesn't carry them), it falls back to `urn:oos:founder_import:placeholder`. This placeholder then propagates into all downstream artifacts.

### Scope

- After item 1.2 (Founder Inbox source URL propagation), the inbox index will carry `linked_source_urls` per review item.
- Update `import_founder_decisions()` to:
  - Read `linked_source_urls` from the inbox index for each resolved `review_item_id`.
  - Use those URLs as the primary source for `linked_source_urls` in `FounderDecisionV2`.
  - Fall back to collecting URLs from evidence pack artifacts only if inbox URLs are absent.
  - Remove the `urn:oos:founder_import:placeholder` fallback entirely.
  - If no source URLs are resolvable after both inbox and evidence pack lookup, record a specific warning but still fail-closed (do not write placeholder URNs).
- Update `FounderDecisionV2` validation to reject placeholder URNs.
- Update `FounderFeedbackMapping` validation to reject placeholder URNs (already validates non-empty `source_urls` at line 327–328).

### Expected files

- `src/oos/founder_decision_import.py` (modify — replace placeholder logic)
- `src/oos/founder_decision_taxonomy.py` (modify — add placeholder URN rejection to validation)
- `src/oos/founder_feedback_mapping.py` (modify — add placeholder URN rejection to validation, if not already present)
- `tests/test_founder_decision_import_v2.py` (modify — add source URL propagation assertions)
- `docs/dev_ledger/02_mini_epics/1.3-founder-decision-import-source-url-propagation.md`
- `docs/dev_ledger/03_run_reports/1.3-founder-decision-import-source-url-propagation.md`

### Acceptance criteria

- [ ] **1.3.1** `urn:oos:founder_import:placeholder` no longer appears in any code path.
- [ ] **1.3.2** `import_founder_decisions()` resolves `linked_source_urls` from the inbox index for each `review_item_id`.
- [ ] **1.3.3** When inbox URLs are available, they are used directly and appear in `FounderDecisionV2.linked_source_urls` and `FounderFeedbackMapping.source_urls`.
- [ ] **1.3.4** `FounderDecisionV2` validation rejects `urn:oos:*` placeholder patterns in `linked_source_urls`.
- [ ] **1.3.5** `FounderFeedbackMapping` validation rejects `urn:oos:*` placeholder patterns in `source_urls`.
- [ ] **1.3.6** Existing decision import tests pass with real source URLs (fixture inbox must carry URLs after item 1.2).
- [ ] **1.3.7** New focused tests verify end-to-end URL propagation: inbox `linked_source_urls` → decision `linked_source_urls` → feedback mapping `source_urls`.
- [ ] **1.3.8** No live APIs/LLMs; fail-closed behavior preserved; idempotent behavior preserved.

---

## 2. E2E Source URL Traceability Validation

## 2.1 E2E source URL traceability validation

### Goal

Add a dedicated source URL traceability verification stage to the existing v2.6 end-to-end fixture validation (`src/oos/v2_6_end_to_end_weekly_cycle_validation.py`) that asserts every artifact in the chain carries real source URLs and no placeholder URNs survive the full pipeline.

### Scope

- Extend `V2_6EndToEndValidationReport` (or create a v2.7-specific `V2_7SourceURLTraceabilityReport`) with source URL traceability fields:
  - `source_url_traceability_checks: list[SourceURLTraceabilityCheck]`
  - `placeholder_urns_found: int`
  - `missing_source_urls_found: int`
  - `source_url_traceability_passed: bool`
- Create a `_check_source_url_traceability()` function that:
  1. Walks the full run directory after `build_weekly_cycle()`.
  2. Reads each artifact (evidence packs, opportunity candidates, quality gate results, inbox index, decision records, feedback mappings).
  3. Verifies every item that should have source URLs does have them.
  4. Verifies zero `urn:oos:*` placeholder URNs exist.
  5. Records any violations with artifact path, item index, and field name.
- Integrate source URL traceability into the existing v2.6 E2E fixture validation runner as an additional step.
- Update the end-to-end validation test suite with focused source URL traceability tests.

### Expected files

- `src/oos/v2_6_end_to_end_weekly_cycle_validation.py` (modify — add source URL traceability stage)
- `src/oos/source_url_traceability.py` (modify or reuse from item 1.1)
- `tests/test_v2_6_end_to_end_weekly_cycle_validation.py` (modify — add source URL traceability assertions)
- `docs/dev_ledger/02_mini_epics/2.1-e2e-source-url-traceability-validation.md`
- `docs/dev_ledger/03_run_reports/2.1-e2e-source-url-traceability-validation.md`

### Acceptance criteria

- [ ] **2.1.1** Source URL traceability stage exists in the E2E validation report.
- [ ] **2.1.2** Full pipeline run with fixture data produces zero placeholder URNs.
- [ ] **2.1.3** Full pipeline run with fixture data has non-empty `source_urls` on every artifact that should carry them.
- [ ] **2.1.4** Traceability chain is verified: `CandidateSignal.source_url` → `EvidencePack.source_urls` → `OpportunityCandidate.source_urls` → `FounderInboxReviewItem.linked_source_urls` → `FounderDecisionV2.linked_source_urls` → `FounderFeedbackMapping.source_urls` and `TargetReference.source_urls`.
- [ ] **2.1.5** E2E validation continues to pass all existing checks (advisory-only, deterministic, artifact existence).
- [ ] **2.1.6** At least 8 focused source URL traceability tests.
- [ ] **2.1.7** No live APIs/LLMs; no autonomous decisions.

---

## 3. Founder Decision Re-Import Policy

## 3.1 Founder decision re-import policy review & safe replace mode, only if justified

### Goal

Review the current founder decision import idempotency behavior, document the intended semantics, and — only if justified by real founder workflow needs — add an explicit `--replace` or `--amend` mode with clear safety constraints.

### Known Gap

The current `import_founder_decisions()` (`src/oos/founder_decision_import.py`) rejects re-import of previously-imported decisions (duplicate `review_item_id` → fail-closed). This is safe but inflexible. A founder who makes a mistake in a decision record has no in-system way to correct it other than manual artifact editing. The question is whether to add an explicit `--replace` mode.

### Scope

- **Phase A — Policy review (always performed):**
  - Document the current duplicate-rejection behavior.
  - Enumerate the safety properties that must hold if a replace mode is added:
    1. Only the founder can initiate replacement (explicit CLI flag).
    2. The replaced decision, feedback mapping, and preference profile update must be cleanly removed before the new decision is written.
    3. Downstream artifacts (feedback mappings, preference profile, parking lot records) must be rebuilt consistently.
    4. The run manifest must record that a replacement occurred.
    5. Replacement must not affect decisions in other runs.
    6. The original decision must be preserved in a `replaced_decisions/` subdirectory or `_replaced` suffix for audit.
  - Evaluate whether the founder workflow really requires this now, or whether "re-run the weekly cycle" is sufficient for the v2.7 timeframe.
  - Record the policy decision in a dedicated document.

- **Phase B — Implementation (only if justified):**
  - Add `--replace` flag to `import-founder-decisions-v2` CLI.
  - Implement replacement logic in `import_founder_decisions()`:
    - Detect existing decisions for the same `review_item_id`.
    - Archive old decisions to `{run_dir}/replaced_decisions/` with timestamp suffix.
    - Remove old feedback mappings linked to the replaced decisions.
    - Rebuild preference profile excluding the replaced decisions.
    - Update parking lot records if the old decision was PARK/REVISIT_LATER.
    - Write new decisions, feedback mappings, preference profile, parking lot updates.
    - Update run manifest with `replaced_decision_ids` list.
  - Add `--amend` flag as an alias or a lighter-weight variant (TBD during policy review).
  - Add focused tests for replace, replace-idempotency, replace-then-rerun safety.

### Expected files

- `docs/decisions/founder_decision_reimport_policy.md` (new — Phase A always produced)
- If Phase B implemented:
  - `src/oos/founder_decision_import.py` (modify)
  - `src/oos/cli.py` (modify — add `--replace` / `--amend` flags)
  - `tests/test_founder_decision_import_v2.py` (modify)
  - `docs/dev_ledger/02_mini_epics/3.1-founder-decision-reimport-policy.md`
  - `docs/dev_ledger/03_run_reports/3.1-founder-decision-reimport-policy.md`
- If Phase B deferred:
  - Only `docs/decisions/founder_decision_reimport_policy.md` and the mini-epic / run report recording the deferral.

### Acceptance criteria

- [ ] **3.1.1** Policy review document exists at `docs/decisions/founder_decision_reimport_policy.md`.
- [ ] **3.1.2** Document records: current behavior, safety properties for replace mode, evaluation of need, and final decision (implement now / defer to v2.8+).
- [ ] **3.1.3** If deferred: mini-epic and run report record the decision with clear rationale and v2.8 hook note.
- [ ] **3.1.4** If implemented: `--replace` flag works end-to-end with fixture decisions; old decisions archived; downstream artifacts consistent.
- [ ] **3.1.5** If implemented: replacement is idempotent (replacing same decision twice = same result).
- [ ] **3.1.6** If implemented: focused tests (≥12) cover replacement, idempotency, safety, and fail-closed rejection of unsafe inputs.
- [ ] **3.1.7** No live APIs/LLMs; advisory-only preserved; no autonomous decisions.

---

## 4. Developer Workflow Helper Scripts

## 4.1 Developer workflow helper scripts

### Goal

Add Windows-native PowerShell helper scripts to `scripts/` for common developer operations: git snapshot, final validation check, post-merge sync, and PR readiness check. One command per operation, no magic.

### Scope

- Create `scripts/dev-snapshot.ps1` — captures a git snapshot:
  - Records current branch, HEAD commit hash, and timestamp.
  - Runs `git status --short -uall` and `git diff --check`.
  - Writes `dev_snapshot_{timestamp}.txt` to `_local_hold/` (gitignored).
  - Optionally runs `scripts/oos-validate.ps1` if `--validate` flag is passed.
- Create `scripts/dev-validate-final.ps1` — runs the final validation checklist:
  - Full unittest discovery with `-v`.
  - `scripts/oos-validate.ps1`.
  - `git diff --check`.
  - `git status --short -uall`.
  - Prints a one-line pass/fail summary.
  - Exit code 0 on all pass, 1 on any failure.
- Create `scripts/dev-post-merge-sync.ps1` — post-merge housekeeping:
  - `git fetch --prune`.
  - Switch back to the current feature branch (or `main` if on a detached HEAD).
  - Prints the merge commit and current state.
  - Does NOT push, tag, or release.
- Create `scripts/dev-pr-readiness.ps1` — PR readiness checklist:
  - Runs `dev-validate-final.ps1`.
  - Checks that no `.env`, `.venv`, or generated `artifacts/` files are staged.
  - Checks that no `reports/` files are staged unless explicitly allowed.
  - Checks that the branch is not `main` or `master`.
  - Prints a readiness summary: "READY for PR" or lists blocking issues.
- Ensure all scripts are:
  - Windows-native PowerShell (no bash/zsh).
  - `Set-StrictMode -Version Latest; $ErrorActionPreference = 'Stop'`.
  - Self-contained (no external dependencies beyond git and the local Python venv structure).
  - Documented with comment-based help (`<# .SYNOPSIS #>`).

### Expected files

- `scripts/dev-snapshot.ps1` (new)
- `scripts/dev-validate-final.ps1` (new)
- `scripts/dev-post-merge-sync.ps1` (new)
- `scripts/dev-pr-readiness.ps1` (new)
- `docs/dev_ledger/02_mini_epics/4.1-developer-workflow-helper-scripts.md`
- `docs/dev_ledger/03_run_reports/4.1-developer-workflow-helper-scripts.md`

### Acceptance criteria

- [ ] **4.1.1** `scripts/dev-snapshot.ps1` exists and runs without error, producing a snapshot file in `_local_hold/`.
- [ ] **4.1.2** `scripts/dev-validate-final.ps1` runs full unittest discovery, `oos-validate.ps1`, `git diff --check`, and `git status`; exits 0 on clean pass.
- [ ] **4.1.3** `scripts/dev-post-merge-sync.ps1` runs `git fetch --prune` and reports current state.
- [ ] **4.1.4** `scripts/dev-pr-readiness.ps1` runs validation and blocks PR if secrets, env files, or generated artifacts are staged.
- [ ] **4.1.5** All scripts have comment-based help.
- [ ] **4.1.6** All scripts use `$ErrorActionPreference = 'Stop'`.
- [ ] **4.1.7** No bash/zsh constructs; no WSL paths.
- [ ] **4.1.8** Scripts do not push, PR, merge, tag, or release.
- [ ] **4.1.9** Scripts do not make live API/LLM calls.
- [ ] **4.1.10** Manual smoke test: `scripts/dev-validate-final.ps1` passes on the current clean working tree.

---

## 5. Controlled Real-Run Readiness

## 5.1 Controlled weekly run smoke test / runbook

### Goal

Create a documented, reproducible runbook for executing a bounded weekly cycle with real (previously collected) fixture signals, reviewing the output, recording decisions, and verifying the full traceability chain. This runbook serves as the controlled real-run smoke test before any live collection is attempted.

### Scope

- Create `docs/runbooks/controlled_weekly_run_smoke_test.md` — a step-by-step runbook covering:
  1. **Pre-flight checks**: `dev-validate-final.ps1`, git status, venv activation.
  2. **Input selection**: using `examples/real_signal_batch.jsonl` or a bounded fixture.
  3. **Run**: `python -m oos.cli run-weekly-cycle-v2 --project-root . --input-file examples/real_signal_batch.jsonl`.
  4. **Inbox review**: open `artifacts/weekly_runs/{run_id}/founder_inbox_v2.md`.
  5. **Decision recording**: create a fixture decisions file and run `import-founder-decisions-v2`.
  6. **Status check**: `python -m oos.cli weekly-cycle-status-v2 --project-root . --run-id {run_id}`.
  7. **Run report**: `python -m oos.cli build-weekly-run-report-v2 --project-root . --run-id {run_id}`.
  8. **Dashboard update**: `python -m oos.cli weekly-dashboard-v2 --project-root .`.
  9. **Traceability verification**: run source URL traceability check (from item 1.1/2.1).
  10. **Expected outputs**: manifest all artifacts present, inbox sections populated, decisions recorded, source URLs traceable, no placeholder URNs.
  11. **Cleanup**: artifact directory management guidance.
- The runbook must be copy-paste-able for a founder/developer on Windows with a working Python venv.
- All commands must be PowerShell.
- The runbook must note what is NOT expected: no live collection, no live LLM/API calls, no portfolio auto-transitions.
- Optionally, create a `scripts/run-controlled-smoke.ps1` that executes the runbook steps automatically against a temp directory and reports results.

### Expected files

- `docs/runbooks/controlled_weekly_run_smoke_test.md` (new)
- `scripts/run-controlled-smoke.ps1` (new, optional — only if automated smoke is feasible without live network)
- `docs/dev_ledger/02_mini_epics/5.1-controlled-weekly-run-smoke-test.md`
- `docs/dev_ledger/03_run_reports/5.1-controlled-weekly-run-smoke-test.md`

### Acceptance criteria

- [ ] **5.1.1** Runbook exists at `docs/runbooks/controlled_weekly_run_smoke_test.md`.
- [ ] **5.1.2** Runbook covers all 11 steps listed above.
- [ ] **5.1.3** Every command in the runbook is copy-paste-able PowerShell.
- [ ] **5.1.4** Runbook explicitly states: no live collection, no live LLM/API calls, no portfolio auto-transitions.
- [ ] **5.1.5** A manual walk-through of the runbook with fixture data completes without errors (validated after item 2.1).
- [ ] **5.1.6** Traceability verification step confirms zero placeholder URNs.
- [ ] **5.1.7** Runbook documents expected output counts and empty-state expectations.
- [ ] **5.1.8** Optional: `scripts/run-controlled-smoke.ps1` passes when run against a temp project root.
- [ ] **5.1.9** No live APIs/LLMs; no autonomous decisions; deterministic output.

---

## 6. Final v2.7 Checkpoint

## 6.1 Final v2.7 validation checkpoint

### Goal

Close the roadmap: verify all items complete, all tests pass, all validation gates green, source URL traceability verified, developer workflow scripts functional, and project state updated.

### Scope

- Run full unittest discovery: `$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`
- Run `scripts/oos-validate.ps1`.
- Run `scripts/dev-validate-final.ps1`.
- Run `git diff --check`.
- Run `git status --short -uall`.
- Run the controlled weekly run smoke test (manual or via `scripts/run-controlled-smoke.ps1`).
- Confirm all placeholder URNs eliminated.
- Confirm source URL traceability end-to-end.
- Confirm roadmap state `completed` at `8 / 8`.
- Confirm `0` remaining.
- Update `docs/dev_ledger/00_project_state.md` to reflect v2.7 completion.
- Record final checkpoint mini-epic and run report.

### Expected files

- `docs/dev_ledger/02_mini_epics/6.1-roadmap-v2-7-final-validation.md`
- `docs/dev_ledger/03_run_reports/6.1-roadmap-v2-7-final-validation.md`
- `docs/dev_ledger/00_project_state.md` (update)

### Acceptance criteria

- [ ] **6.1.1** All 8 implementation items have `[x] Done` status.
- [ ] **6.1.2** Roadmap state is `complete / closed`.
- [ ] **6.1.3** Completed: `8 / 8`.
- [ ] **6.1.4** Remaining: `0 / 8`.
- [ ] **6.1.5** Full unittest discovery: 0 failures.
- [ ] **6.1.6** `scripts/oos-validate.ps1` passes.
- [ ] **6.1.7** `scripts/dev-validate-final.ps1` passes.
- [ ] **6.1.8** `git diff --check` clean.
- [ ] **6.1.9** Source URL traceability verification: zero `urn:oos:*` placeholder URNs in any artifact.
- [ ] **6.1.10** Controlled weekly run smoke test completes successfully.
- [ ] **6.1.11** Dev Ledger updated with final state.
- [ ] **6.1.12** No push, PR, merge, tag, or release unless explicitly approved.

---

## Appendix A: Implementation Order and Dependencies

```
0.1 Roadmap v2.7 planning  ← this checkpoint (docs-only)
     │
1.1 Source URL traceability contract  ← no dependencies
     │
1.2 Founder Inbox source URL propagation  ← depends on 1.1 (contract)
     │
1.3 Founder Decision Import source URL propagation  ← depends on 1.2 (inbox URLs)
     │
2.1 E2E source URL traceability validation  ← depends on 1.1, 1.2, 1.3
     │
3.1 Founder decision re-import policy review  ← no code dependency on 1.x/2.x; can be parallel
     │
4.1 Developer workflow helper scripts  ← no code dependency on 1.x/2.x/3.x; can be parallel
     │
5.1 Controlled weekly run smoke test / runbook  ← depends on 2.1 (traceability), 4.1 (validation scripts)
     │
6.1 Final v2.7 validation checkpoint  ← depends on 1.1–5.1
```

Items 3.1 and 4.1 can be worked in parallel with items 1.1–2.1.

Item 5.1 benefits from 2.1 (traceability validation) and 4.1 (helper scripts) but its runbook document can be drafted in parallel.

## Appendix B: Traceability Chain (Hardened v2.7)

```
CandidateSignal.source_url
  → EvidencePack.source_urls
    → OpportunityCandidate.source_urls
      → OpportunityGateResult.source_urls
        → FounderInboxReviewItem.linked_source_urls  ← NEW in v2.7
          → FounderDecisionV2.linked_source_urls
            → FounderFeedbackMapping.source_urls
              → FounderFeedbackMapping.target.source_urls
```

Every link in this chain must carry real, non-placeholder URLs.
Placeholder URNs (`urn:oos:*`) are treated as traceability gaps and must be eliminated.

## Appendix C: Known Deferred / Follow-Up Items (from v2.6)

| # | Item | v2.7 Disposition |
|---|------|-----------------|
| 1 | Replace `source_urls` placeholder URN in founder decision import | **Addressed: items 1.2 + 1.3** |
| 2 | Add `linked_source_urls` to `FounderInboxReviewItem` | **Addressed: item 1.2** |
| 3 | Propagate `source_urls` from EvidencePack through inbox → decision import → FounderFeedbackMapping | **Addressed: items 1.1–1.3, validated by 2.1** |
| 4 | Add `source_urls` traceability assertion to E2E validation | **Addressed: item 2.1** |
| 5 | Review founder decision re-import semantics | **Addressed: item 3.1** |
| 6 | Add developer workflow helper scripts | **Addressed: item 4.1** |
| 7 | Add controlled real weekly run smoke test / runbook | **Addressed: item 5.1** |
| 8 | Preserve deterministic-first behavior | **Continued: all v2.7 items** |
| 9 | Preserve advisory-only founder control | **Continued: all v2.7 items** |
| 10 | Avoid live API/LLM calls by default | **Continued: all v2.7 items** |

## Appendix D: Explicit Non-Goals

- **Do not** add new product layers (no Pain Discovery Layer integration, no new pipeline stages).
- **Do not** add live LLM/API calls. All items remain deterministic-first.
- **Do not** rewrite, refactor, or redesign the v2.6 weekly cycle pipeline.
- **Do not** add new collectors, sources, or source expansion.
- **Do not** add a database, persistent server, or UI.
- **Do not** add embeddings, vector search, or ML features.
- **Do not** add autonomous portfolio transitions.
- **Do not** add multi-user, multi-tenant, or venture-studio features.
- **Do not** add email/push notifications or scheduled periodic runs.
- **Do not** broaden beyond the existing HN + GitHub source loop.

## Appendix E: Mitigations for Known Risks

| Risk | Mitigation |
|------|-----------|
| Placeholder URN elimination breaks tests that depend on it | Tests are updated as part of items 1.2–1.3; fixture inbox data must carry source URLs |
| Source URL propagation changes break backward compatibility | New `linked_source_urls` field defaults to `[]` in `FounderInboxReviewItem`; field additions are additive, not breaking |
| Decision re-import policy review finds no safe replace mode | Phase B is explicitly conditional; deferral is documented and acceptable |
| Developer workflow scripts depend on venv structure | Scripts use relative paths from project root; documented prerequisites |
| Smoke test runbook becomes stale as pipeline evolves | Runbook references explicit CLI commands, not internal APIs; commands are stable from v2.6 |
| Traceability verification slows down E2E validation | Checks are deterministic and fast (artifact reads, no network); added as a discrete step, not interleaved |
