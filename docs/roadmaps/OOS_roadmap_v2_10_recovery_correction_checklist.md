# OOS Roadmap v2.10 — Recovery Correction Closure

## 0. Roadmap Overview

### Active Roadmap

- [x] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md`
- [ ] **0.2** Current item: `4.1 — Replace-All Readiness Gate`
- [x] **0.3** Roadmap state: `ready for implementation`
- [ ] **0.4** Completed from this roadmap: **3 / 9**
- [ ] **0.5** Remaining: **6 / 9**
- [ ] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_9_output_modes_source_url_strictness_and_correction_recovery_checklist.md` (complete, `8 / 8`, tag `v2.9`, merged to main via PR #49)

### Branch and Version

- **Planning branch:** `planning/v2-10-roadmap` (docs-only; merged to main)
- **Implementation branch:** `feat/v2-10-recovery-correction` (active)
- **Based on:** v2.9 / PR #49 merge commit `35bc991` / tag `v2.9`
- **Status:** Ready for implementation

### Core Concept

Roadmap v2.9 delivered output mode polish (`--utf8`), quality gate source URL strictness (`missing_count=0`), and correction recovery policy reviews (undo-last and replace-all both deferred with authoritative specifications). Roadmap v2.10 picks up both deferred policy items and closes recovery/correction capabilities safely:

```
    v2.9 delivered                              v2.10 delivers
    ─────────────                               ─────────────
    --utf8 opt-in flag                          undo-last implementation (deferred from v2.9 item 3.1)
    Quality gate source URL strictness          replace-all implementation (deferred from v2.9 item 3.2)
    Correction rollback/undo policy             Terminal encoding auto-detection audit/policy
    Replace-all mode policy                     Optional --utf8 expansion audit
    Operational validation refresh              Operational polish after v2.9
    Final v2.9 validation checkpoint            Final v2.10 validation checkpoint
```

### Deferred Items Carried Forward from v2.9

| # | Item | v2.9 Status | v2.10 Disposition |
|---|------|------------|-------------------|
| 1 | `--undo-last` rollback/undo | Policy review complete (item 3.1); classified non-trivial (~200 lines, 4 files, 12 safety requirements U-R1–U-R12) | **Primary implementation target: items 1, 2, 3** |
| 2 | `--replace-all` mode | Policy review complete (item 3.2); classified small (~80 lines, 2 files, 13 safety requirements RA-R1–RA-R13) | **Gated implementation: items 4, 5** |
| 3 | Terminal encoding auto-detection | Explicitly deferred in output mode contract Section 1.3 | **Audit/policy only: item 6** |
| 4 | `--utf8` expansion to more CLI commands | Output mode contract Section 3.4 requires justification per command | **Optional audit: item 7** |

### Strategic Principles

- **Recovery safety first.** undo-last must exist and have tests/smoke coverage before replace-all can proceed. No replace-all without undo-last.
- **Correction traceability preserved.** All destructive correction operations must preserve the audit trail (`import_history.json` append-only, `replaced_decisions/` archive, `amended_decisions/` archive).
- **ASCII-safe default remains the law.** No automatic terminal encoding detection that changes runtime behavior without explicit approval. `--utf8` remains opt-in.
- **Gated, not parallel.** replace-all is explicitly blocked unless undo-last safety gates pass (items 1–3 complete, validated, and green).
- **Deterministic-first preserved.** All logic must produce deterministic output; no live LLM/API calls by default.
- **Advisory-only preserved.** No autonomous portfolio transitions. All decisions remain founder-initiated.
- **No new product layers.** This is correction recovery closure + operational polish, not feature expansion.
- **Do not rewrite v2.8/v2.9.** Only implement the deferred policy items and close known gaps.

### Explicit Non-Goals (Across All v2.10 Items)

- New OOS product layers (no Pain Discovery Layer integration, no new pipeline stages).
- Live LLM/API calls by default. LLM hooks remain disabled/future-only.
- Autonomous portfolio transitions.
- UI/dashboard work beyond file-system Markdown + JSON.
- New collectors, new sources, or source expansion.
- Embeddings, vector search, or ML features.
- Database or persistent server.
- Multi-user, multi-tenant, or venture-studio mode.
- Email/push notifications or scheduled periodic runs.
- Broad CLI rewrite or refactor of any existing module.
- Multi-step undo (undoing more than the last correction) — v2.11+.
- Run-level undo (`--undo-run <run_id>`) — requires pre-correction snapshots; v2.11+.
- Restore-archived (`--restore-archived <decision_id>`) — error-prone manual mode; not recommended.
- Automatic terminal encoding behavior without prior audit and explicit approval.
- `--utf8` on all CLI commands — only evidence-driven expansion per audit (item 7).

### LLM Role Statement

LLM integration belongs later (`v2.11+`) unless present only as disabled/future hooks. The v2.10 pipeline must complete deterministically. Existing LLM contracts remain in the codebase but are not wired into the default weekly cycle path.

### Workflow Rules

- Planning branch: `planning/v2-10-roadmap` (docs-only, this file). Implementation branch: `feat/v2-10-recovery-correction` (future; do not use planning branch for implementation).
- Local commit per roadmap item during implementation.
- Push/PR/merge/tag only when explicitly requested.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Windows-native only: PowerShell, native Python venv, VS Code/Codex.
- No WSL/Linux-first assumptions.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.

> Roadmap status tracks **9 implementation items** (items 1–9). Item 0 (planning checkpoint) is the current planning item and is not counted in the implementation total. Items 0.1–0.6 are roadmap-state trackers and are not counted in the implementation total.

---

## 0. Roadmap v2.10 Planning

### Intent

Create the official Roadmap v2.10 planning checklist. Docs-only. No source code, tests, scripts, examples, artifacts, or generated outputs.

### Allowed Change Type

- Create: `docs/roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md` (this file)

### Validation Expectation

- `.\scripts\dev-git-check.ps1` passes.
- `git status --short` shows only the new roadmap file before commit.
- After commit, working tree is clean.

### Definition of Done

- [x] **0.0.1** Roadmap v2.10 document exists at `docs/roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md`.
- [x] **0.0.2** Roadmap state was `planning`; now `ready for implementation`.
- [x] **0.0.3** Current item was `0 — Planning checkpoint`; now `1 — Undo-last contract finalization`.
- [x] **0.0.4** Completed: `0 / 9`.
- [x] **0.0.5** Remaining: `9 / 9`.
- [x] **0.0.6** Branch `planning/v2-10-roadmap` exists and is checked out.
- [x] **0.0.7** All sections present: overview, scope summary, non-goals, numbered checklist (0–9), safety gates, validation commands, git discipline.
- [x] **0.0.8** `.\scripts\dev-git-check.ps1` passes.
- [x] **0.0.9** `git status --short` shows only this file before commit.
- [x] **0.0.10** One local commit made with message: `Add Roadmap v2.10 recovery correction checklist`.

---

## Scope Summary

Roadmap v2.10 focuses on **safely closing recovery/correction capabilities** after v2.9:

1. **undo-last is the primary implementation target.** The policy review (v2.9 item 3.1) defined 12 safety requirements (U-R1–U-R12). v2.10 implements the narrow U1 mode (`--undo-last`) only.
2. **replace-all is gated.** The policy review (v2.9 item 3.2) defined 13 safety requirements (RA-R1–RA-R13) and a strict completeness check. replace-all MUST NOT proceed unless undo-last exists and has test/smoke coverage (items 1–3 complete and green). The gate is explicit and non-negotiable.
3. **Encoding auto-detection starts as audit/policy, not automatic behavior.** The output mode contract (v2.9 item 1.1) explicitly deferred terminal encoding detection to v2.10+. v2.10 audits the feasibility and defines policy; it does NOT implement automatic detection unless separately approved.
4. **`--utf8` expansion is optional and evidence-driven.** The output mode contract Section 3.4 requires per-command justification. v2.10 audits which commands would benefit; implementation only if evidence supports it and change is trivial.
5. **Operational polish after v2.9.** Refresh the validation suite to cover undo-last and (if gated in) replace-all. Verify all v2.8/v2.9 correction workflow steps still pass.

---

## Numbered Checklist

### 1. Undo-Last Contract Finalization

- [x] **1.1** Finalize the undo-last contract from the v2.9 policy document.

**Intent:** Translate the 12 safety requirements (U-R1–U-R12) from [`docs/decisions/correction_rollback_undo_policy.md`](../decisions/correction_rollback_undo_policy.md) into an implementation-ready contract. Define exact artifact write order, the `CorrectionEntry` schema for `correction_mode = "undo"`, manifest fields (`undone_decision_ids`, `undone_at`), and CLI output expectations. Resolve the design pre-work items listed in the policy Section 9.4 (pre-correction snapshot decision, undo entry schema, CLI output format, manifest updates, interaction with replace-all).

**Allowed change type:** Create new contract file in `docs/contracts/`. No source code changes. (Policy document status updates belong to item 9 final checkpoint, not this item.)

**Validation expectation:** Contract is self-consistent with the 12 safety requirements U-R1–U-R12. No source code changes.

**Definition of done:**
- [x] **1.1.1** Contract document created at `docs/contracts/undo_last_contract.md` (or equivalent path).
- [x] **1.1.2** Contract defines artifact write order matching the dependency chain in policy Section 4.3.
- [x] **1.1.3** Contract defines `CorrectionEntry` schema for `correction_mode = "undo"`.
- [x] **1.1.4** Contract defines manifest fields: `undone_decision_ids` and `undone_at`.
- [x] **1.1.5** Contract defines CLI output format for undo result.
- [x] **1.1.6** Design pre-work items from policy Section 9.4 are resolved.
- [x] **1.1.7** No source code changes. No live APIs/LLMs.

---

### 2. Undo-Last Implementation

- [x] **2.1** Implement `--undo-last` on `import-founder-decisions-v2`.

**Intent:** Implement the narrow U1 mode defined in the policy document Section 5.1 and the finalized contract (item 1). Create `src/oos/correction_undo.py` with `UndoResult` model and `undo_last_correction()` function. Add `--undo-last` flag to `import-founder-decisions-v2` in [`src/oos/cli.py`](../../src/oos/cli.py). Integrate with [`src/oos/founder_decision_import.py`](../../src/oos/founder_decision_import.py) for history reading and audit append. Satisfy all 12 safety requirements U-R1–U-R12.

**Allowed change type:** Create `src/oos/correction_undo.py`. Modify `src/oos/cli.py` and `src/oos/founder_decision_import.py`.

**Validation expectation:** All undo-last tests pass. Correction workflow E2E (v2.8 C1–C14) still passes. Fail-closed behavior verified: empty history rejected, missing archive rejected, partial writes impossible. Source URL traceability survives undo (U-R8: zero placeholder URNs after undo).

**Definition of done:**
- [x] **2.1.1** `src/oos/correction_undo.py` created with `UndoResult` model and `undo_last_correction()` function.
- [x] **2.1.2** `--undo-last` flag added to `import-founder-decisions-v2` in `src/oos/cli.py`.
- [x] **2.1.3** Integration with `src/oos/founder_decision_import.py` for history/audit operations (CorrectionEntry extended with undo-specific fields, ImportHistoryLog.from_dict handles undo entries).
- [x] **2.1.4** Undo-replace path works: old decisions restored from `replaced_decisions/`, new decisions removed, derived artifacts rebuilt.
- [x] **2.1.5** Undo-amend path works: old notes restored from `amended_decisions/`, no derived artifact rebuild.
- [x] **2.1.6** Audit trail preserved: new `CorrectionEntry` appended with `correction_mode = "undo"`.
- [x] **2.1.7** Manifest updated with `undone_decision_ids` and `undone_at`.
- [x] **2.1.8** All 12 safety requirements U-R1–U-R12 satisfied.
- [x] **2.1.9** Existing v2.8 correction E2E validation (C1–C14) still passes (1739 tests pass).
- [x] **2.1.10** No live APIs/LLMs; advisory-only preserved.

---

### 3. Undo-Last Validation and Smoke Coverage

- [x] **3.1** Create tests and smoke coverage for `--undo-last`.

**Intent:** Deliver the test suite specified in the policy document Section 9.3: 20+ tests covering undo-replace, undo-amend, undo with empty history, undo with missing archive, undo with multiple corrections, undo idempotency, undo source URL traceability, undo parking lot consistency, undo fail-closed, undo advisory flags. Add undo-last to the controlled smoke test. Update the correction workflow E2E validation to include undo-last steps.

**Allowed change type:** Create `tests/test_correction_undo.py`. Modify `tests/test_v2_8_correction_workflow_validation.py` (or equivalent E2E validation file). Modify `scripts/run-controlled-smoke.ps1` (or its supporting test module).

**Validation expectation:** `.\scripts\dev-test.ps1` passes all undo tests. `.\scripts\run-controlled-smoke.ps1` passes including undo-last step. Correction E2E validation passes all steps including undo.

**Definition of done:**
- [x] **3.1.1** `tests/test_correction_undo.py` created with 20+ tests.
- [x] **3.1.2** Undo-replace test: undo restores replaced decisions, rebuilds derived artifacts.
- [x] **3.1.3** Undo-amend test: undo restores old notes, no rebuild.
- [x] **3.1.4** Undo with empty history: rejected with clear error.
- [x] **3.1.5** Undo with missing archive: rejected (fail-closed).
- [x] **3.1.6** Undo with multiple corrections: only last correction undone.
- [x] **3.1.7** Undo idempotency: same state, same result.
- [x] **3.1.8** Undo source URL traceability: zero placeholder URNs after undo.
- [x] **3.1.9** Undo parking lot consistency: orphan records cleaned up.
- [x] **3.1.10** Undo fail-closed: no partial writes on any failure.
- [x] **3.1.11** Undo advisory flags: `advisory_only=True` throughout.
- [x] **3.1.12** Controlled smoke test includes undo-last step.
- [x] **3.1.13** Correction E2E validation includes undo-last steps (C21+).
- [x] **3.1.14** `.\scripts\dev-git-check.ps1` passes after all test changes.

---

### 4. Replace-All Readiness Gate

- [ ] **4.1** Verify undo-last gate conditions before allowing replace-all implementation.

**Intent:** This is a safety gate, not a code item. Before any replace-all code is written, confirm: (a) undo-last items 1–3 are complete with all tests passing, (b) undo-last smoke coverage exists, (c) a concrete real-run need for replace-all has been demonstrated (founder feedback, not hypothetical), and (d) the policy document pre-conditions (Section 9.1) are all satisfied.

**Allowed change type:** Update this roadmap checklist only (mark gate as passed/failed). No source code changes.

**Validation expectation:** All pre-conditions from [`docs/decisions/replace_all_mode_policy.md`](../decisions/replace_all_mode_policy.md) Section 9.1 are demonstrably satisfied before proceeding to item 5.

**Definition of done:**
- [ ] **4.1.1** Undo-last items 1–3 are complete (`[x]` status on all sub-items).
- [ ] **4.1.2** Undo-last test suite passes (20+ tests green).
- [ ] **4.1.3** Controlled smoke test passes with undo-last step.
- [ ] **4.1.4** Correction E2E validation passes with undo-last steps.
- [ ] **4.1.5** Pre-condition (1): All v2.9 items remain complete and validated.
- [ ] **4.1.6** Pre-condition (2): Correction workflow E2E (v2.8 C1–C14 + v2.10 undo steps) passes.
- [ ] **4.1.7** Pre-condition (3): `--replace-review-items` exercised in at least one real run (not just fixture).
- [ ] **4.1.8** Pre-condition (4): Concrete real-run need for `--replace-all` demonstrated.
- [ ] **4.1.9** Pre-condition (5): Undo-last handles replace-all as undoable operation (design confirmed in contract from item 1).
- [ ] **4.1.10** Gate is explicitly marked `PASSED` or `BLOCKED` in this checklist. If `BLOCKED`, items 5.x are skipped and v2.10 closes without replace-all.

---

### 5. Replace-All Implementation (Only If Gate Passes)

- [ ] **5.1** Implement `--replace-all` with strict completeness check.

**Intent:** Only if item 4 gate is `PASSED`. Implement the `--replace-all` mode defined in the policy document Section 9.2: strict completeness check (RA-R6), dry-run/plan mode (RA-R4), confirm-step prompt (RA-R5), and all 13 safety requirements RA-R1–RA-R13. Add `replace_all: bool = False` parameter to `import_founder_decisions()` in [`src/oos/founder_decision_import.py`](../../src/oos/founder_decision_import.py). Add `--replace-all` and `--dry-run` flags to `import-founder-decisions-v2` in [`src/oos/cli.py`](../../src/oos/cli.py).

**Allowed change type:** Modify `src/oos/founder_decision_import.py` and `src/oos/cli.py`. Create or modify `tests/test_replace_all_correction.py` (or equivalent test file for replace-all).

**Validation expectation:** Replace-all with complete file succeeds. Replace-all with incomplete file (missing opportunity IDs) is rejected with list of missing opportunities. Dry-run shows plan without modifying artifacts. Confirm-step prompt requires explicit "yes". All 13 safety requirements RA-R1–RA-R13 satisfied. Undo-last correctly handles a replace-all correction as the last entry.

**Definition of done:**
- [ ] **5.1.1** Item 4 gate is `PASSED`.
- [ ] **5.1.2** `--replace-all` flag added to `import-founder-decisions-v2` in `src/oos/cli.py`.
- [ ] **5.1.3** `--dry-run` flag added to `import-founder-decisions-v2` in `src/oos/cli.py`.
- [ ] **5.1.4** `replace_all: bool = False` parameter added to `import_founder_decisions()`.
- [ ] **5.1.5** `_import_replace_all_mode()` function implemented (~50 lines).
- [ ] **5.1.6** Strict completeness check (RA-R6): rejects incomplete replacement files with list of missing opportunities.
- [ ] **5.1.7** Dry-run/plan mode (RA-R4): shows old/new decision counts, removed/added opportunity IDs, parking lot impact.
- [ ] **5.1.8** Confirm-step prompt (RA-R5): requires explicit "yes" before writes.
- [ ] **5.1.9** All old decisions archived to `replaced_decisions/` before new decisions written (RA-R7).
- [ ] **5.1.10** `CorrectionEntry` with `correction_mode = "replace_all"` appended to `import_history.json` (RA-R8).
- [ ] **5.1.11** Source URL traceability passes after replace-all: zero placeholder URNs (RA-R11).
- [ ] **5.1.12** Derived artifacts rebuilt: feedback mappings, preference profile, parking lot records consistent (RA-R13).
- [ ] **5.1.13** Undo-last correctly handles `correction_mode = "replace_all"` as most recent correction.
- [ ] **5.1.14** All 13 safety requirements RA-R1–RA-R13 satisfied.
- [ ] **5.1.15** 15+ tests covering: complete file, incomplete file (rejected), dry-run, idempotency, archive, audit trail, parking lot rebuild, source URL traceability, fail-closed, advisory flags, confirm-step prompt, undo-after-replace-all.
- [ ] **5.1.16** No live APIs/LLMs; advisory-only preserved.

---

### 6. Encoding Auto-Detection Audit/Policy

- [ ] **6.1** Audit terminal encoding auto-detection feasibility and define policy.

**Intent:** The output mode contract (v2.9 item 1.1, Section 1.3) explicitly deferred automatic terminal encoding detection to v2.10+. This item audits the feasibility on Windows (CP1251/CP1252 detection, `sys.stdout.encoding`, `chcp`, `GetConsoleOutputCP()`) and defines a policy document. The audit must answer: is reliable detection possible without platform-specific hacks? Can it be deterministic? What are the false-positive/false-negative risks? The policy must state whether auto-detection is recommended, and if so, under what constraints it could be implemented in a future roadmap (v2.11+). **This item does NOT implement auto-detection.** It produces an audit/policy document only.

**Allowed change type:** Create `docs/decisions/terminal_encoding_auto_detection_policy.md`. No source code changes. No runtime behavior changes.

**Validation expectation:** Policy document exists with clear recommendation (recommend / do not recommend / recommend with constraints). ASCII-safe default remains unchanged. No `sys.stdout.encoding` probes, no `chcp` checks, no `GetConsoleOutputCP()` calls introduced.

**Definition of done:**
- [ ] **6.1.1** Audit document created at `docs/decisions/terminal_encoding_auto_detection_policy.md`.
- [ ] **6.1.2** Windows terminal encoding landscape audited: CP1251, CP1252, CP65001 (UTF-8), Windows Terminal, VS Code terminal, legacy `cmd.exe`.
- [ ] **6.1.3** Detection methods evaluated: `sys.stdout.encoding`, `chcp`, `GetConsoleOutputCP()`, environment variables, terminal capability probing.
- [ ] **6.1.4** Determinism assessed: can detection be deterministic on all supported Windows configurations?
- [ ] **6.1.5** False-positive/false-negative risks documented.
- [ ] **6.1.6** Explicit recommendation made: recommend / do not recommend / recommend with constraints.
- [ ] **6.1.7** If recommended: constraints defined (e.g., opt-out flag `--ascii`, detection override, fail-closed to ASCII-safe on uncertainty).
- [ ] **6.1.8** ASCII-safe default is confirmed unchanged. No runtime behavior modified.
- [ ] **6.1.9** No source code changes. No live APIs/LLMs.

---

### 7. Optional `--utf8` Expansion Audit

- [ ] **7.1** Audit which CLI commands would benefit from `--utf8` expansion.

**Intent:** The output mode contract (v2.9 item 1.1, Section 3.4) requires per-command justification for adding `--utf8`. v2.9 scoped `--utf8` to `weekly-cycle-status-v2`, `weekly-dashboard-v2`, and `build-weekly-run-report-v2`. This item audits the remaining CLI commands to determine if any produce terminal-facing output with visually significant symbols that would benefit from `--utf8`. Produce a documented recommendation. Implementation only if evidence supports it and change is trivial (≤30 lines per command, ≤2 files total).

**Allowed change type:** Primary deliverable: create `docs/decisions/utf8_expansion_audit_v2_10.md` (audit-first). Source code changes are permitted ONLY if the audit explicitly recommends expansion AND the change is trivial (≤30 lines per command, ≤2 files total). If the audit does not recommend expansion, NO source code changes are permitted; the audit document alone closes this item.

**Validation expectation:** If no commands qualify, audit document records the finding and no code changes are made. If commands qualify and are implemented, each added `--utf8` has tests covering both output modes, and ASCII-safe default remains enforced.

**Definition of done:**
- [ ] **7.1.1** Audit document created at `docs/decisions/utf8_expansion_audit_v2_10.md`.
- [ ] **7.1.2** All CLI commands not currently supporting `--utf8` are reviewed.
- [ ] **7.1.3** Per-command assessment: does terminal output contain status symbols, arrows, separators, or other visually significant markers?
- [ ] **7.1.4** Explicit recommendation for each command: add `--utf8` / do not add `--utf8`, with rationale.
- [ ] **7.1.5** If any command qualifies: implementation is trivial (≤30 lines per command, ≤2 files total).
- [ ] **7.1.6** If implemented: each added `--utf8` has tests covering ASCII-safe default and UTF-8 mode.
- [ ] **7.1.7** ASCII-safe default is confirmed unchanged.
- [ ] **7.1.8** No live APIs/LLMs.

---

### 8. Operational Validation Refresh

- [ ] **8.1** Update the validation suite to cover all new v2.10 capabilities.

**Intent:** Refresh the smoke/E2E validation suite to cover undo-last (and replace-all if gated in). Verify all existing v2.8 correction workflow steps (C1–C14) and v2.9 operational steps still pass. Update the controlled weekly run smoke test runbook. Run full validation.

**Allowed change type:** Modify `tests/test_v2_8_correction_workflow_validation.py` (or create v2.10 validation module). Modify `tests/test_controlled_weekly_run_smoke.py`. Modify `docs/runbooks/controlled_weekly_run_smoke_test.md`.

**Validation expectation:** `.\scripts\dev-test.ps1` passes all tests. `.\scripts\run-controlled-smoke.ps1` passes all steps. `.\scripts\dev-validate-final.ps1` passes all gates. Correction E2E validation passes all steps including v2.10 additions.

**Definition of done:**
- [ ] **8.1.1** Undo-last validation steps added to E2E correction workflow validation.
- [ ] **8.1.2** All v2.8 correction E2E steps (C1–C14) still pass.
- [ ] **8.1.3** All v2.9 operational validation steps still pass.
- [ ] **8.1.4** Replace-all validation steps added (only if item 5 was implemented).
- [ ] **8.1.5** Controlled weekly run smoke test updated for v2.10.
- [ ] **8.1.6** Smoke test runbook updated with undo-last instructions (and replace-all if implemented).
- [ ] **8.1.7** ASCII-safe default verified on all CLI commands (no regression).
- [ ] **8.1.8** Source URL traceability `missing_count = 0` and `placeholder_count = 0` confirmed (no regression).
- [ ] **8.1.9** `.\scripts\dev-validate-final.ps1` passes all gates.
- [ ] **8.1.10** No live APIs/LLMs; advisory-only preserved.

---

### 9. Final v2.10 Checkpoint

- [ ] **9.1** Close the roadmap: verify all items complete, all tests pass, all validation gates green.

**Intent:** Final validation checkpoint. Run full unittest discovery, all validation scripts, and confirm roadmap completion. Update project state. Mark roadmap as `complete / closed`.

**Allowed change type:** Update this roadmap checklist. Update `docs/decisions/correction_rollback_undo_policy.md` to mark as "implemented at v2.10". Update `docs/dev_ledger/00_project_state.md` to reflect v2.10 completion. Create mini-epic and run report for final checkpoint.

**Validation expectation:** All items 1–8 have `[x]` status (excluding items 4–5 if gate was `BLOCKED`). Full unittest discovery passes. All validation scripts pass. Working tree clean.

**Definition of done:**
- [ ] **9.1.1** All applicable implementation items have `[x] Done` status.
- [ ] **9.1.2** Roadmap state is `complete / closed`.
- [ ] **9.1.3** Completed count matches expected: 9 / 9 if replace-all was implemented; 8 / 9 if replace-all gate was BLOCKED and item 5 was skipped.
- [ ] **9.1.4** Remaining: `0`.
- [ ] **9.1.5** Full unittest discovery: all tests pass, 0 failures.
- [ ] **9.1.6** `.\scripts\dev-validate-final.ps1` passes (all gates green).
- [ ] **9.1.7** `.\scripts\run-controlled-smoke.ps1` passes (all steps).
- [ ] **9.1.8** `.\scripts\dev-git-check.ps1` passes.
- [ ] **9.1.9** `git diff --check` clean.
- [ ] **9.1.10** `git status --short` clean (working tree clean).
- [ ] **9.1.11** Source URL traceability: `placeholder_count = 0`, `missing_count = 0`.
- [ ] **9.1.12** ASCII-safe default output confirmed on all CLI commands.
- [ ] **9.1.13** `--utf8` flag works correctly (no regression from v2.9).
- [ ] **9.1.14** Undo-last workflow passes E2E validation.
- [ ] **9.1.15** Replace-all workflow passes E2E validation (only if item 5 was implemented).
- [ ] **9.1.16** Dev Ledger updated with final v2.10 state.
- [ ] **9.1.17** No push, PR, merge, tag, or release. (local commit only)

---

## Safety Gates

The following gates are non-negotiable and must be satisfied before specific items can proceed:

### Gate A: Replace-All Blocked Without Undo-Last

- **Condition:** Items 1, 2, and 3 must be complete with all tests and smoke coverage passing before item 5 (replace-all implementation) can begin.
- **Enforcement:** Item 4 is the explicit gate checkpoint. If item 4 is `BLOCKED`, items 5.x are skipped.
- **Rationale:** Replace-all is a destructive wholesale operation. Undo-last is the safety net. There must be a proven undo path before replace-all is allowed.

### Gate B: Destructive Correction Operations Preserve Traceability

- **Condition:** Every correction operation (replace, amend, undo, replace-all) must append to `import_history.json` (never modify or delete existing entries) and archive pre-correction state to `replaced_decisions/` or `amended_decisions/`.
- **Enforcement:** Tests must verify append-only behavior and archive integrity for every correction mode.
- **Rationale:** The audit trail is the system's memory. No operation may destroy it.

### Gate C: Default Output Must Remain ASCII-Safe Unless `--utf8` Is Explicit

- **Condition:** Default terminal-facing output (no `--utf8` flag) must contain only characters with `ord(c) < 128`, excluding newlines and tabs.
- **Enforcement:** Item 8 operational validation must verify ASCII-safety on all CLI commands. No automatic encoding detection may change default behavior in v2.10.
- **Rationale:** CP1251/CP1252 terminal compatibility must not regress.

### Gate D: Terminal Encoding Auto-Detection Must Not Change Runtime Behavior in v2.10

- **Condition:** Item 6 produces an audit/policy document only. No `sys.stdout.encoding` probes, no `chcp` checks, no `GetConsoleOutputCP()` calls are introduced. The output mode decision tree remains: `--utf8 present? → YES → utf8 mode | NO → ascii_safe mode`.
- **Enforcement:** Code review must confirm no encoding detection logic exists in any module.
- **Rationale:** Encoding detection is platform-specific, fragile, and non-deterministic. It must not be introduced without explicit approval beyond the audit/policy phase.

---

## Validation Commands

Use only wrapper scripts. Do not use chained shell commands.

| Step | Command | Expected |
|------|---------|----------|
| 1 | `.\scripts\dev-git-check.ps1` | 6/6 checks pass |
| 2 | `.\scripts\dev-test.ps1` | All tests pass, 0 failures |
| 3 | `.\scripts\run-controlled-smoke.ps1` | All steps pass |
| 4 | `.\scripts\dev-validate-final.ps1` | All gates green |
| 5 | `git status --short` | Clean working tree (after commit) |

---

## Git Discipline

- **Planning branch:** `planning/v2-10-roadmap` (docs-only). **Implementation branch:** `feat/v2-10-recovery-correction` (future; do not use planning branch for implementation).
- **One local commit per roadmap item.** Commit after each item's definition of done is satisfied.
- **Push/PR/merge/tag only when explicitly requested.** Do not push. Do not create PR. Do not merge. Do not tag.
- **Always run `.\scripts\dev-git-check.ps1` after each item completion.**
- **Commit message format:** `[v2.10] <item-number> <short-description>`

---

## Appendix A: Implementation Order and Dependencies

```
0. Planning checkpoint  ← this item (docs-only)
     │
1. Undo-last contract finalization  ← no dependencies
     │
2. Undo-last implementation  ← depends on 1 (contract)
     │
3. Undo-last validation and smoke coverage  ← depends on 2 (implementation)
     │
4. Replace-all readiness gate  ← depends on 1, 2, 3
     │
     ├── GATE PASSED → 5. Replace-all implementation  ← depends on 4 (gate)
     │
     └── GATE BLOCKED → skip 5, proceed to 6
     │
6. Encoding auto-detection audit/policy  ← no code dependency on 1–5; can be parallel
     │
7. Optional --utf8 expansion audit  ← no code dependency on 1–6; can be parallel
     │
8. Operational validation refresh  ← depends on 2, 3, (5 if gated in), 6, 7
     │
9. Final v2.10 checkpoint  ← depends on 1–8
```

Items 6 and 7 can be worked in parallel with items 1–5. Item 8 benefits from all preceding items being complete.

---

## Appendix B: Deferred Items Closed by v2.10

| # | Item | v2.9 Status | v2.10 Disposition |
|---|------|------------|-------------------|
| 1 | `--undo-last` rollback/undo | Policy review complete; deferred to v2.10+ | Closed by items 1, 2, 3 |
| 2 | `--replace-all` mode | Policy review complete; deferred to v2.10+ | Closed by items 4, 5 (or explicitly blocked) |
| 3 | Terminal encoding auto-detection | Explicitly deferred in output mode contract | Closed by item 6 (audit/policy) |
| 4 | `--utf8` expansion to more CLI commands | Output mode contract Section 3.4 | Closed by item 7 (audit; optional implementation) |

---

## Appendix C: v2.11+ Hook Notes

The following items are explicitly out of scope for v2.10 but are recognized as natural follow-up work:

| # | Item | Rationale for deferral |
|---|------|----------------------|
| 1 | Multi-step undo (`--undo-correction <id>`) | Requires correction stack navigation and cross-correction validation; v2.10 implements single-step undo-last only |
| 2 | Run-level undo (`--undo-run <run_id>`) | Requires pre-correction snapshots; not feasible without design work |
| 3 | Restore-archived (`--restore-archived <id>`) | Error-prone manual mode; not recommended per policy |
| 4 | Automatic terminal encoding detection (implementation) | v2.10 produces audit/policy only; implementation deferred to v2.11+ |
| 5 | `--utf8` on all CLI commands | v2.10 audits and implements only if trivial; full expansion is v2.11+ |
| 6 | LLM-assisted decision suggestions | LLM integration is deferred to v2.11+ per strategic principles |
| 7 | Pain Discovery Layer integration | PDL is a separate product layer; integration requires its own roadmap |
| 8 | Batch correction across multiple runs | Cross-run correction semantics are complex; v2.10 focuses on single-run safety |
| 9 | Correction UI beyond CLI flags | UI is out of scope for all v2.x roadmaps per scope-v1 |

---

## Appendix D: Mitigations for Known Risks

| Risk | Mitigation |
|------|-----------|
| Undo-last implementation exceeds estimate (>200 lines) | Contract (item 1) scopes implementation precisely; if >200 lines, reassess whether to split into sub-items |
| Undo-last breaks v2.8 correction E2E | Item 3 validates all C1–C14 steps still pass; item 8 does full refresh |
| Replace-all gate is never satisfied | Items 4–5 are explicitly gated; v2.10 can close without replace-all |
| Replace-all strict completeness check is too strict | Policy document RA-R6 is the authoritative spec; strict mode protects against silent deletion |
| Encoding auto-detection audit recommends implementation | Audit is non-binding; implementation requires separate approval in v2.11+ |
| `--utf8` expansion cascades into many files | Item 7 has explicit triviality threshold (≤30 lines/command, ≤2 files); if exceeded, expansion is deferred |
| ASCII-safe default regresses from v2.9 | Item 8 verifies ASCII-safety on all commands; Gate C is non-negotiable |
| Source URL traceability regresses after undo/replace-all | Both U-R8 and RA-R11 require zero placeholder URNs; item 8 validates |
