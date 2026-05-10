# OOS Roadmap v2.9 — Output Modes, Source URL Strictness & Correction Recovery

## 0. Roadmap Overview

### Active Roadmap

- [x] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_9_output_modes_source_url_strictness_and_correction_recovery_checklist.md`
- [ ] **0.2** Current item: `1.2 Implement --utf8 opt-in flag`
- [ ] **0.3** Roadmap state: `active / in progress`
- [ ] **0.4** Completed from this roadmap: **1 / 8**
- [ ] **0.5** Remaining: **7 / 8**
- [ ] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_8_founder_decision_correction_and_operational_polish_checklist.md` (complete, `9 / 9`, tag `v2.8` created, merged to main)

### Core Concept

Roadmap v2.8 delivered safe founder decision correction (replace/amend), parking lot cleanup, derived artifact rebuild, import history audit trail, CLI correction visibility, Windows ASCII-safe CLI output, quality gate source URL audit with documented deferral, and E2E correction workflow validation. Roadmap v2.9 picks up the three deferred items and polishes the system for operational clarity:

```
    v2.8 delivered                          v2.9 delivers
    ─────────────                           ─────────────
    Safe replace/amend workflow             --utf8 opt-in flag (deferred from v2.8 item 4.1)
    Parking lot orphan cleanup              Quality gate source URL fixture strictness
    Derived artifact rebuild model          Correction rollback/undo policy
    Import history / audit trail            Replace-all mode policy
    CLI correction-state visibility         Operational validation refresh
    Windows ASCII-safe CLI output           Final v2.9 validation checkpoint
    Quality gate source_urls deferral doc
    E2E correction workflow validation
```

### Deferred Items Carried Forward from v2.8

| # | Item | v2.8 Status | v2.9 Disposition |
|---|------|------------|-----------------|
| 1 | `--utf8` opt-in flag | **Not implemented.** v2.8 item 4.1 replaced Unicode symbols with ASCII-safe defaults but did not add the `--utf8` flag. | **Addressed: items 1.1, 1.2** |
| 2 | Quality gate fixture/source URL strictness | **Deferred.** `missing_count=1` is a fixture data gap, not a code defect. Documented in `docs/decisions/quality_gate_source_urls_deferral.md`. | **Addressed: items 2.1, 2.2** |
| 3 | `--replace-all` mode | **Deferred.** Documented in correction artifact contract Section 4.4 as "not required for v2.8". | **Addressed: item 3.2 (policy review)** |
| 4 | Optional rollback/undo | **Deferred.** Listed as v2.9+ candidate in v2.8 Appendix F item 1. | **Addressed: item 3.1 (policy review)** |
| 5 | Quality gate source URL missing scenarios clarification | **Deferred.** Documented in deferral doc. | **Addressed: items 2.1, 2.2** |

### Strategic Principles

- **Output mode polish.** ASCII-safe default is the law. `--utf8` is an opt-in escape hatch for terminals known to support UTF-8. No CP1251/CP1252 regression.
- **Source URL strictness without scanner weakening.** Fix the fixture data so the scanner can report `missing_count=0` for fixture E2E runs. Do not suppress or weaken the scanner.
- **Correction recovery prudence.** Evaluate rollback/undo and replace-all as policy items first. Implement only if small and safe; otherwise defer with explicit rationale.
- **Deterministic-first preserved.** All logic must produce deterministic output; no live LLM/API calls by default.
- **Advisory-only preserved.** No autonomous portfolio transitions. All decisions remain founder-initiated.
- **No new product layers.** This is deferred-item closure + operational polish, not feature expansion.
- **Do not rewrite v2.8.** Only implement the deferred items and fix known operational gaps.

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
- Expanding beyond the existing HN + GitHub source loop.
- Rewriting or redesigning the v2.6/v2.7/v2.8 weekly cycle pipeline.
- Replacing the v2.8 correction workflow.
- Source collection expansion.
- Broad refactor of any existing module.
- Add new idea-generation/product layers.

### LLM Role Statement

LLM integration belongs later (`v2.10+`) unless present only as disabled/future hooks. The v2.9 pipeline must complete deterministically. Existing LLM contracts remain in the codebase but are not wired into the default weekly cycle path.

### Workflow Rules

- One feature block = one branch. This planning checkpoint is docs-only on `planning/v2-9-roadmap`.
- Local commit per item during implementation.
- Push/PR/merge only at the end of a feature block and only when explicitly requested.
- Windows-native only: PowerShell, native Python venv, VS Code/Codex.
- No WSL/Linux-first assumptions.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.
- Live source runs are explicit, bounded, and approval-gated.

> Roadmap status tracks **8 implementation items** (items 1.1–5.1). Item 0.1 (planning) is complete and not counted in the implementation total. Items 0.2–0.6 are roadmap-state trackers and are not counted in the implementation total. Items 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1 are implementation; item 5.1 is the final checkpoint.

---

## 0.1 Roadmap v2.9 Planning

### Goal

Create the official Roadmap v2.9 planning checklist, mini-epic, run report, and update the Dev Ledger project state to make v2.9 the active planned roadmap after the completed v2.8 system.

### Scope

- Create this roadmap checklist document.
- Create `docs/dev_ledger/02_mini_epics/0.1-roadmap-v2-9-planning.md`.
- Create `docs/dev_ledger/03_run_reports/0.1-roadmap-v2-9-planning.md`.
- Update `docs/dev_ledger/00_project_state.md` to transition from v2.8 (complete/closed) to v2.9 (active/planned).
- Docs-only. No source code changes. No tests. No artifacts. No live API/LLM calls.

### Expected files

- `docs/roadmaps/OOS_roadmap_v2_9_output_modes_source_url_strictness_and_correction_recovery_checklist.md`
- `docs/dev_ledger/02_mini_epics/0.1-roadmap-v2-9-planning.md`
- `docs/dev_ledger/03_run_reports/0.1-roadmap-v2-9-planning.md`
- `docs/dev_ledger/00_project_state.md` (update)

### Acceptance criteria

- [ ] **0.1.1** Roadmap v2.9 document exists at the expected path with all sections.
- [ ] **0.1.2** Roadmap state is `active / planned`.
- [ ] **0.1.3** Current item is `1.1 Output mode contract and CLI policy`.
- [ ] **0.1.4** Completed: `0 / 8`.
- [ ] **0.1.5** Remaining: `8 / 8`.
- [ ] **0.1.6** Mini-epic document exists.
- [ ] **0.1.7** Run report exists.
- [ ] **0.1.8** Dev Ledger project state is updated.
- [ ] **0.1.9** `git diff --check` clean; `git status --short -uall` clean (docs-only changes).
- [ ] **0.1.10** One local commit made.

---

## 1. Output Mode Polish

## 1.1 Output mode contract and CLI policy

### Goal

Define the canonical output mode contract: ASCII-safe default behavior, optional `--utf8` opt-in semantics, which CLI commands need `--utf8`, and a non-regression guarantee for CP1251/CP1252 terminals.

### Known Gap

v2.8 item 4.1 (commit `e36a470`) replaced Unicode symbols with ASCII-safe alternatives in CLI output but did **not** implement the `--utf8` opt-in flag specified in the original scope. The `--utf8` flag was listed as acceptance criterion 4.1.3 ("`--utf8` flag forces Unicode output for UTF-8-capable terminals") and marked `[x]` done, but a code audit confirms zero occurrences of `utf8` in `src/oos/`. The v2.8 final validation (item 7.1) did not catch this discrepancy. v2.9 must define the contract first, then implement.

### Scope

- Create `docs/contracts/output_mode_contract.md` (new) documenting:
  - **ASCII-safe default.** All CLI commands output ASCII-only by default. No Unicode symbols (✅, ❌, ⚠, ─, ◉, etc.) in default output.
  - **`--utf8` opt-in.** A single `--utf8` flag that restores Unicode symbols for terminals known to support UTF-8.
  - **Scope of `--utf8`.** Which CLI commands accept `--utf8`:
    - `weekly-cycle-status-v2` — Markdown status output.
    - `weekly-dashboard-v2` — Dashboard Markdown output.
    - `build-weekly-run-report-v2` — Run report Markdown output (if terminal-rendered).
    - `import-founder-decisions-v2` — Only if correction summary output contains symbols.
    - Other commands — Explicitly excluded unless justified.
  - **CP1251/CP1252 non-regression.** Default output must render correctly on CP1251 and CP1252 terminals. Tests must verify ASCII-only output by default.
  - **Symbol mapping table.** Canonical mapping from Unicode symbols to ASCII-safe alternatives:
    | Unicode | ASCII-safe |
    |---------|-----------|
    | `✅` | `[PASS]` |
    | `❌` | `[FAIL]` |
    | `⚠` | `[WARN]` |
    | `─` (box-drawing) | `-` |
    | `◉` | `[*]` |
    | `│` (box-drawing) | `|` |
    | `├` / `└` (box-drawing) | `+` |
    | `→` | `->` |
  - **Implementation constraint.** `--utf8` must be a single boolean flag, not per-symbol or per-section. When `--utf8` is `True`, all Unicode symbols are restored.
  - **Test requirements.** Every command with `--utf8` must have tests verifying:
    - Default output is ASCII-safe (no Unicode symbols outside ASCII range 32–126, excluding newlines and tabs).
    - `--utf8` output restores Unicode symbols.
    - No information is lost in either mode.

### Expected files

- `docs/contracts/output_mode_contract.md` (new)
- `docs/dev_ledger/02_mini_epics/1.1-output-mode-contract-and-cli-policy.md`
- `docs/dev_ledger/03_run_reports/1.1-output-mode-contract-and-cli-policy.md`

### Acceptance criteria

- [x] **1.1.1** Contract document exists at `docs/contracts/output_mode_contract.md`.
- [x] **1.1.2** Contract defines ASCII-safe default as the mandatory behavior.
- [x] **1.1.3** Contract defines `--utf8` opt-in semantics: single boolean flag, all-or-nothing Unicode restore.
- [x] **1.1.4** Contract lists exactly which CLI commands accept `--utf8` and which are excluded.
- [x] **1.1.5** Symbol mapping table is exhaustive: covers all Unicode symbols currently used in CLI output.
- [x] **1.1.6** CP1251/CP1252 non-regression guarantee is explicit.
- [x] **1.1.7** Test requirements are specified: ASCII-safety check, `--utf8` restore check, no information loss.
- [x] **1.1.8** Contract references the v2.8 item 4.1 implementation gap as the motivation.
- [x] **1.1.9** No source code changes. No live APIs/LLMs.

---

## 1.2 Implement `--utf8` opt-in flag

### Goal

Implement the `--utf8` flag on the CLI commands specified in the output mode contract (item 1.1), with ASCII-safe default preserved and tests covering both modes.

### Known Gap

The v2.8 item 4.1 acceptance criterion 4.1.3 was marked complete but `--utf8` was never implemented. The ASCII-safe default is in place; only the opt-in Unicode restore path is missing.

### Scope

- Update `src/oos/cli.py`:
  - Add `--utf8` flag to `weekly-cycle-status-v2` subcommand.
  - Add `--utf8` flag to `weekly-dashboard-v2` subcommand.
  - Add `--utf8` flag to `build-weekly-run-report-v2` subcommand.
  - Pass `utf8: bool` parameter through to renderer functions.
- Update `src/oos/weekly_cycle_status.py`:
  - Accept `utf8: bool = False` parameter in `render_weekly_cycle_status_markdown()`.
  - When `utf8=False` (default): use ASCII-safe symbols (`[PASS]`, `[FAIL]`, `[WARN]`, `-`, `[*]`, etc.).
  - When `utf8=True`: use Unicode symbols (✅, ❌, ⚠, ─, ◉, etc.).
  - Centralize symbol selection in a `_status_symbols(utf8: bool) -> dict` helper.
- Update `src/oos/weekly_run_reports.py`:
  - Accept `utf8: bool = False` parameter in report and dashboard Markdown renderers.
  - Use the same symbol selection pattern as `weekly_cycle_status.py`.
- Do **not** add `--utf8` to `import-founder-decisions-v2` unless the correction summary output contains Unicode symbols. Audit during implementation.
- Add tests:
  - In `tests/test_weekly_cycle_status_v2.py`: verify ASCII-safe default output (no Unicode outside 32–126), `--utf8` Unicode output, symbol correctness in both modes.
  - In `tests/test_weekly_run_reports_v2.py`: same ASCII-safe/UTF-8 verification.
  - In `tests/test_cli.py`: verify `--utf8` flag is accepted and propagated correctly.
- Ensure no CP1251/CP1252 regression: existing ASCII-safe default behavior is unchanged.

### Expected files

- `src/oos/cli.py` (modify — add `--utf8` flag to relevant subcommands)
- `src/oos/weekly_cycle_status.py` (modify — add `utf8` parameter to renderer)
- `src/oos/weekly_run_reports.py` (modify — add `utf8` parameter to renderers)
- `tests/test_weekly_cycle_status_v2.py` (modify — add dual-mode symbol assertions)
- `tests/test_weekly_run_reports_v2.py` (modify — add dual-mode symbol assertions)
- `tests/test_cli.py` (modify — add `--utf8` flag propagation tests)
- `docs/dev_ledger/02_mini_epics/1.2-implement-utf8-opt-in-flag.md`
- `docs/dev_ledger/03_run_reports/1.2-implement-utf8-opt-in-flag.md`

### Acceptance criteria

- [ ] **1.2.1** `--utf8` flag exists on `weekly-cycle-status-v2` CLI subcommand.
- [ ] **1.2.2** `--utf8` flag exists on `weekly-dashboard-v2` CLI subcommand.
- [ ] **1.2.3** `--utf8` flag exists on `build-weekly-run-report-v2` CLI subcommand.
- [ ] **1.2.4** Default output (no `--utf8`) is ASCII-safe: no Unicode symbols outside range 32–126 (excluding `\n`, `\t`).
- [ ] **1.2.5** `--utf8` output restores Unicode symbols (✅, ❌, ⚠, ─, ◉, etc.).
- [ ] **1.2.6** No information is lost in ASCII-safe rendering compared to Unicode rendering.
- [ ] **1.2.7** CP1251/CP1252 terminals render default output without mojibake (verified by ASCII-only check).
- [ ] **1.2.8** Symbol selection is centralized in a single helper per module (no scattered `if utf8:` blocks).
- [ ] **1.2.9** `import-founder-decisions-v2` is audited; `--utf8` added only if correction summary output contains Unicode symbols.
- [ ] **1.2.10** Existing tests pass without modification (ASCII-safe defaults are backward compatible).
- [ ] **1.2.11** Focused tests (≥12) cover: ASCII-safe default for status, UTF-8 output for status, ASCII-safe default for dashboard, UTF-8 output for dashboard, ASCII-safe default for run report, UTF-8 output for run report, CLI flag propagation, no-flag default behavior, symbol mapping correctness, no information loss, CP1251/CP1252 safety, and excluded commands do not accept `--utf8`.
- [ ] **1.2.12** No live APIs/LLMs; advisory-only preserved.

---

## 2. Quality Gate Source URL Strictness

## 2.1 Quality gate source URL fixture audit and correction plan

### Goal

Re-audit the quality gate source URL traceability gap documented in v2.8 item 5.1, identify the exact fixture/test scenarios producing `missing_count != 0`, and define a precise correction plan before any code or fixture changes are made.

### Known Gap

The v2.8 Phase B audit (`docs/decisions/quality_gate_source_urls_deferral.md`) found:
- The code path `OpportunityCandidate.source_urls → OpportunityGateResult.source_urls` is **correct**.
- All 10 fixture cases in `examples/evaluation_dataset_v2_5/opportunity_quality_cases_v1.json` have non-empty `EvidencePack.source_urls`.
- The `missing_count=1` observed in the v2.7 E2E source URL traceability scan originates from **non-fixture input scenarios**: insufficient-evidence packs, canonical signal batches with empty `source_ref`, or synthetic/empty-state quality gate items.
- The deferral decision was: fix requires modifying fixture files and cascading test expectations (>50 lines across >2 files), so deferred to v2.9+.

This item creates the precise correction plan before any code or fixture changes.

### Scope

- Re-run the source URL traceability scanner against the v2.8 E2E correction workflow validation artifacts and capture the exact `missing_count` and affected artifact items.
- Identify the exact fixture/test scenario producing `missing_count != 0`:
  - Is it the evaluation dataset fixture (`examples/evaluation_dataset_v2_5/opportunity_quality_cases_v1.json`)?
  - Is it the real signal batch fixture (`examples/real_signal_batch.jsonl`)?
  - Is it the v2.6/v2.8 E2E validation fixture paths?
  - Is it an insufficient-evidence scenario triggered during E2E validation?
- Classify each affected scenario:
  - **Fixture gap:** Fixture data has empty `source_urls` that should have real URLs.
  - **Synthetic item:** The artifact is legitimately synthetic (no evidence lineage) and should have an explicit `empty_source_urls_reason`.
  - **Insufficient-evidence:** The artifact is built from an insufficient-evidence evidence pack and is exempt or needs exemption.
- Define exact changes needed (files, line ranges, change description) for each scenario.
- Estimate total change size. If ≤100 lines across ≤3 files, the fix qualifies as "small and safe." If larger, document the breakdown and confirm still in scope for v2.9.
- Update the deferral document with the correction plan.
- Update the source URL traceability contract if the plan changes any exemption policy.

### Expected files

- `docs/decisions/quality_gate_source_urls_deferral.md` (update — add correction plan section)
- `docs/contracts/source_url_traceability_contract.md` (update — if exemption policy changes)
- `docs/dev_ledger/02_mini_epics/2.1-quality-gate-source-url-fixture-audit.md`
- `docs/dev_ledger/03_run_reports/2.1-quality-gate-source-url-fixture-audit.md`

### Acceptance criteria

- [ ] **2.1.1** Source URL traceability scanner is re-run against v2.8 E2E validation artifacts; `missing_count` and affected items are captured.
- [ ] **2.1.2** Exact fixture/test scenario producing `missing_count != 0` is identified.
- [ ] **2.1.3** Each affected scenario is classified as fixture gap, synthetic item, or insufficient-evidence.
- [ ] **2.1.4** Exact changes are defined: file paths, line ranges, change descriptions.
- [ ] **2.1.5** Change size estimate is documented: lines, files, test impact.
- [ ] **2.1.6** If ≤100 lines across ≤3 files, the fix is approved for item 2.2. If larger, explicit rationale for still-in-scope is documented.
- [ ] **2.1.7** Deferral document updated with correction plan section.
- [ ] **2.1.8** Source URL traceability contract updated if exemption policy changes.
- [ ] **2.1.9** No source code changes. No fixture changes (audit/plan only). No live APIs/LLMs.

---

## 2.2 Quality gate source URL strictness / fixture cleanup

### Goal

Implement the correction plan from item 2.1: fix fixture data and/or test expectations so that the source URL traceability scanner reports `missing_count = 0` for fixture E2E runs. Do not weaken the scanner.

### Known Gap

The `missing_count=1` in the v2.7 E2E source URL traceability scan for `quality_gate_decisions` is a known fixture data gap. The scanner correctly reports it; the fix is in the fixture data, not the scanner.

### Scope

- Implement the exact changes defined in item 2.1:
  - If fixture gap: add real source URLs to the affected fixture case(s).
  - If synthetic item: add explicit `empty_source_urls_reason` field and ensure scanner exemption covers it.
  - If insufficient-evidence: ensure the scanner's insufficient-evidence exemption applies correctly, or add the exemption if missing.
- Update cascading test expectations:
  - `tests/test_opportunity_quality_gate.py` — update source URL assertions.
  - `tests/test_evaluation_dataset_v1.py` — update expected output assertions.
  - `tests/test_v2_6_end_to_end_weekly_cycle_validation.py` — update traceability step expectations.
  - `tests/test_v2_8_correction_workflow_validation.py` — update correction workflow traceability expectations.
  - `tests/test_source_url_traceability.py` — if any scanner test expectations change.
- After changes, run the source URL traceability scanner against fixture E2E artifacts and confirm `missing_count = 0` and `placeholder_count = 0`.
- Run full E2E validation (v2.6 + v2.8 correction) and confirm all traceability steps pass.
- Do **not** suppress, weaken, or modify the scanner's detection logic.
- Do **not** modify the quality gate evaluation logic (`opportunity_quality_gate.py`).

### Expected files

- `examples/evaluation_dataset_v2_5/opportunity_quality_cases_v1.json` (modify — if fixture gap)
- `examples/real_signal_batch.jsonl` (modify — if fixture gap)
- `tests/test_opportunity_quality_gate.py` (modify — update assertions)
- `tests/test_evaluation_dataset_v1.py` (modify — update expected outputs)
- `tests/test_v2_6_end_to_end_weekly_cycle_validation.py` (modify — update traceability expectations)
- `tests/test_v2_8_correction_workflow_validation.py` (modify — update traceability expectations)
- `src/oos/source_url_traceability.py` (modify — only if exemption logic needs update; must not weaken scanner)
- `docs/contracts/source_url_traceability_contract.md` (update — reflect final state)
- `docs/decisions/quality_gate_source_urls_deferral.md` (update — mark as resolved)
- `docs/dev_ledger/02_mini_epics/2.2-quality-gate-source-url-fixture-cleanup.md`
- `docs/dev_ledger/03_run_reports/2.2-quality-gate-source-url-fixture-cleanup.md`

### Acceptance criteria

- [ ] **2.2.1** Source URL traceability scanner reports `missing_count = 0` for fixture E2E runs.
- [ ] **2.2.2** Source URL traceability scanner reports `placeholder_count = 0` (no regression).
- [ ] **2.2.3** v2.6 E2E fixture validation passes all traceability steps.
- [ ] **2.2.4** v2.8 E2E correction workflow validation passes all traceability steps.
- [ ] **2.2.5** Scanner detection logic is **not** weakened, suppressed, or modified to hide gaps.
- [ ] **2.2.6** Quality gate evaluation logic (`opportunity_quality_gate.py`) is **not** modified.
- [ ] **2.2.7** All existing tests pass without unexpected changes (cascading assertion updates are expected and documented).
- [ ] **2.2.8** Deferral document is updated to reflect resolution.
- [ ] **2.2.9** Source URL traceability contract reflects final state.
- [ ] **2.2.10** Focused tests (≥8) cover: scanner `missing_count=0` post-fix, scanner `placeholder_count=0` post-fix, v2.6 E2E traceability, v2.8 correction E2E traceability, fixture data integrity, scanner non-weakening, and no regression in existing quality gate behavior.
- [ ] **2.2.11** No live APIs/LLMs; advisory-only preserved.

---

## 3. Correction Recovery Policy

## 3.1 Correction rollback / undo policy review

### Goal

Evaluate whether undo/rollback of founder decision corrections belongs in OOS. Define minimum safe semantics if in scope. Policy-first; implement only if trivially small.

### Known Gap

The v2.8 correction artifact contract (Section 13.8) lists undo/rollback as a "v2.9+ candidate." v2.8 Appendix F item 1 notes: "Requires correction stack/history navigation; v2.8 builds the foundation." The `import_history.json` audit trail and `replaced_decisions/` archive now exist, providing the raw material for undo.

### Scope

- Review the existing correction infrastructure:
  - `import_history.json` — contains `CorrectionEntry` records with old/new decision IDs and artifact checksums.
  - `replaced_decisions/` — contains archived pre-correction decision files.
  - `decision_correction_rebuild.py` — contains deterministic rebuild logic.
- Define minimum safe undo semantics:
  1. **Undo last correction.** Restore the most recent replaced/amended decisions from `replaced_decisions/` or `amended_decisions/` archive.
  2. **Restore archived decision.** Copy the archived decision back to `founder_decisions_v2.json`.
  3. **Rebuild derived artifacts.** Re-run the deterministic rebuild for feedback mappings, preference profile, and parking lot records.
  4. **Append audit history.** Record the undo as a new `CorrectionEntry` with `correction_mode = "undo"`.
  5. **Update manifest.** Record `undone_decision_ids` in the run manifest.
- Assess feasibility:
  - **Trivial case (≤50 lines, 1 file):** Implement undo as a `--undo-last` flag on `import-founder-decisions-v2`.
  - **Small case (50–150 lines, ≤3 files):** Implement with dedicated `src/oos/correction_undo.py` module.
  - **Non-trivial case (>150 lines or >3 files):** Document the policy and defer implementation to v2.10+.
- Document the decision with explicit rationale.
- If deferred, record the policy as the authoritative specification for future implementation.

### Expected files

- If policy-only or deferred:
  - `docs/decisions/correction_rollback_undo_policy.md` (new)
- If implemented (trivial/small only):
  - `src/oos/cli.py` (modify — add `--undo-last` flag)
  - `src/oos/correction_undo.py` (new — if small case)
  - `tests/test_correction_undo.py` (new)
- Always:
  - `docs/dev_ledger/02_mini_epics/3.1-correction-rollback-undo-policy.md`
  - `docs/dev_ledger/03_run_reports/3.1-correction-rollback-undo-policy.md`

### Acceptance criteria

- [ ] **3.1.1** Existing correction infrastructure (`import_history.json`, `replaced_decisions/`, `decision_correction_rebuild.py`) is reviewed.
- [ ] **3.1.2** Minimum safe undo semantics are defined: undo last correction, restore archived decision, rebuild derived artifacts, append audit history, update manifest.
- [ ] **3.1.3** Feasibility is assessed and classified as trivial, small, or non-trivial.
- [ ] **3.1.4** Decision is explicit: implement (if trivial/small) or defer (if non-trivial).
- [ ] **3.1.5** If implemented: `--undo-last` flag works correctly; tests cover undo + rebuild + audit + manifest.
- [ ] **3.1.6** If deferred: policy document records the specification with rationale.
- [ ] **3.1.7** Undo must be advisory-only: no autonomous decisions, no portfolio mutations.
- [ ] **3.1.8** Undo must be fail-closed: any inconsistency → no artifacts written.
- [ ] **3.1.9** Source URL traceability must survive undo (no placeholder URNs introduced).
- [ ] **3.1.10** No live APIs/LLMs.

---

## 3.2 Replace-all mode policy review

### Goal

Evaluate whether `--replace-all` mode is safe and needed. Prefer deferral unless a clear real-run need exists. Policy-first; implement only if trivially small.

### Known Gap

The v2.8 correction artifact contract (Section 4.4) documents `--replace-all` as "NOT recommended" and "not required for v2.8." It notes that `--replace-all` is coarse, violates R8 (silent deletion of unrelated decisions) unless the founder carefully crafts the replacement file, and is deferred to v2.9+.

### Scope

- Review the `--replace-all` semantics from the correction artifact contract Section 4.4.
- Assess whether a real-run need exists:
  - Has any v2.8 operational use revealed a scenario where surgical `--replace-review-items` is insufficient?
  - Is there a use case for wholesale decision replacement within a single run?
- If a clear need exists:
  - Define safety constraints: all-or-nothing, confirm-step prompt, pre-replacement snapshot, full rebuild.
  - Assess implementation effort. If ≤50 lines in `founder_decision_import.py`, implement. Otherwise defer.
- If no clear need exists:
  - Document the deferral with rationale.
  - Keep the contract Section 4.4 as the authoritative specification for future reference.
- Document the decision.

### Expected files

- If policy-only or deferred:
  - `docs/decisions/replace_all_mode_policy.md` (new)
- If implemented (trivial only):
  - `src/oos/founder_decision_import.py` (modify — add `--replace-all` logic)
  - `src/oos/cli.py` (modify — add `--replace-all` flag)
  - `tests/test_founder_decision_import_v2.py` (modify — add replace-all tests)
- Always:
  - `docs/dev_ledger/02_mini_epics/3.2-replace-all-mode-policy.md`
  - `docs/dev_ledger/03_run_reports/3.2-replace-all-mode-policy.md`

### Acceptance criteria

- [ ] **3.2.1** `--replace-all` semantics from the correction artifact contract Section 4.4 are reviewed.
- [ ] **3.2.2** Real-run need is assessed: either a concrete use case is identified, or absence is documented.
- [ ] **3.2.3** Safety constraints are defined if implementing: confirm-step, pre-replacement snapshot, full rebuild.
- [ ] **3.2.4** Decision is explicit: implement (if need exists AND ≤50 lines) or defer.
- [ ] **3.2.5** If implemented: `--replace-all` flag works correctly with safety constraints; tests cover all-or-nothing, confirm-step, rebuild, and traceability.
- [ ] **3.2.6** If deferred: policy document records rationale and keeps contract Section 4.4 as authoritative.
- [ ] **3.2.7** `--replace-all` must not silently delete unrelated decisions without founder awareness.
- [ ] **3.2.8** Advisory-only preserved; no autonomous decisions.
- [ ] **3.2.9** No live APIs/LLMs.

---

## 4. Operational Validation

## 4.1 Operational validation refresh

### Goal

Update the smoke/E2E validation suite to cover all new v2.9 capabilities: ASCII-safe default output, optional `--utf8` mode (if implemented), source URL strictness with `missing_count = 0`, and correction workflow still passing after all changes.

### Scope

- Update `src/oos/v2_8_correction_workflow_validation.py` (or create a v2.9-specific validation module):
  - Add step C15: Verify ASCII-safe default output on `weekly-cycle-status-v2` (no Unicode symbols outside 32–126).
  - Add step C16: Verify `--utf8` output on `weekly-cycle-status-v2` (Unicode symbols present) — if `--utf8` implemented in item 1.2.
  - Add step C17: Verify ASCII-safe default output on `weekly-dashboard-v2`.
  - Add step C18: Verify `--utf8` output on `weekly-dashboard-v2` — if implemented.
  - Add step C19: Verify source URL traceability `missing_count = 0` for quality gate decisions after fixture cleanup (item 2.2).
  - Add step C20: Verify undo workflow (if implemented in item 3.1).
- Update `tests/test_controlled_weekly_run_smoke.py`:
  - Add ASCII-safe output assertions for status and dashboard.
  - Add `--utf8` output assertions if implemented.
  - Add source URL traceability `missing_count = 0` assertion.
- Run full validation:
  - All existing v2.6 E2E steps pass.
  - All existing v2.8 correction E2E steps (C1–C14) pass.
  - New v2.9 steps (C15–C20) pass.
- Update the controlled weekly run smoke test runbook (`docs/runbooks/controlled_weekly_run_smoke_test.md`):
  - Document ASCII-safe default behavior.
  - Document `--utf8` flag usage.
  - Document source URL strictness expectations.

### Expected files

- `src/oos/v2_8_correction_workflow_validation.py` (modify — add v2.9 steps, or create `v2_9_operational_validation.py`)
- `tests/test_v2_8_correction_workflow_validation.py` (modify — add v2.9 step assertions)
- `tests/test_controlled_weekly_run_smoke.py` (modify — add output mode and traceability assertions)
- `docs/runbooks/controlled_weekly_run_smoke_test.md` (modify — update for v2.9)
- `docs/dev_ledger/02_mini_epics/4.1-operational-validation-refresh.md`
- `docs/dev_ledger/03_run_reports/4.1-operational-validation-refresh.md`

### Acceptance criteria

- [ ] **4.1.1** ASCII-safe default output is verified for `weekly-cycle-status-v2`.
- [ ] **4.1.2** ASCII-safe default output is verified for `weekly-dashboard-v2`.
- [ ] **4.1.3** `--utf8` output is verified for `weekly-cycle-status-v2` (if `--utf8` implemented).
- [ ] **4.1.4** `--utf8` output is verified for `weekly-dashboard-v2` (if `--utf8` implemented).
- [ ] **4.1.5** Source URL traceability `missing_count = 0` is verified for fixture E2E runs.
- [ ] **4.1.6** Source URL traceability `placeholder_count = 0` is verified (no regression).
- [ ] **4.1.7** All existing v2.6 E2E validation steps pass.
- [ ] **4.1.8** All existing v2.8 correction E2E validation steps (C1–C14) pass.
- [ ] **4.1.9** Undo workflow validation passes (if undo implemented in item 3.1).
- [ ] **4.1.10** Controlled weekly run smoke test runbook is updated for v2.9.
- [ ] **4.1.11** Focused tests (≥10) cover: ASCII-safe status, ASCII-safe dashboard, UTF-8 status, UTF-8 dashboard, traceability missing_count=0, traceability placeholder_count=0, v2.6 E2E still passes, v2.8 correction E2E still passes, smoke test updates, and undo validation (if implemented).
- [ ] **4.1.12** No live APIs/LLMs; advisory-only preserved.

---

## 5. Final v2.9 Checkpoint

## 5.1 Final v2.9 validation checkpoint

### Goal

Close the roadmap: verify all items complete, all tests pass, all validation gates green, output modes verified, source URL strictness achieved, correction recovery policies documented, and project state updated.

### Scope

- Run full unittest discovery: `$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`
- Run `scripts/oos-validate.ps1`.
- Run `scripts/dev-validate-final.ps1`.
- Run `scripts/run-controlled-smoke.ps1`.
- Run `scripts/dev-git-check.ps1`.
- Run `git diff --check`.
- Run `git status --short -uall`.
- Confirm all placeholder URNs eliminated (`placeholder_count = 0`).
- Confirm source URL traceability `missing_count = 0` for fixture E2E runs.
- Confirm ASCII-safe default output on all CLI commands.
- Confirm `--utf8` flag works correctly (if implemented).
- Confirm correction workflow (replace + amend) still passes fixture E2E validation.
- Confirm undo workflow passes (if implemented).
- Confirm roadmap state `completed` at `8 / 8`.
- Confirm `0` remaining.
- Update `docs/dev_ledger/00_project_state.md` to reflect v2.9 completion.
- Record final checkpoint mini-epic and run report.

### Expected files

- `docs/dev_ledger/02_mini_epics/5.1-roadmap-v2-9-final-validation.md`
- `docs/dev_ledger/03_run_reports/5.1-roadmap-v2-9-final-validation.md`
- `docs/dev_ledger/00_project_state.md` (update)

### Acceptance criteria

- [ ] **5.1.1** All 8 implementation items have `[x] Done` status.
- [ ] **5.1.2** Roadmap state is `complete / closed`.
- [ ] **5.1.3** Completed: `8 / 8`.
- [ ] **5.1.4** Remaining: `0 / 8`.
- [ ] **5.1.5** Full unittest discovery: all tests pass, 0 failures.
- [ ] **5.1.6** `scripts/oos-validate.ps1` passes.
- [ ] **5.1.7** `scripts/dev-validate-final.ps1` passes (all gates green).
- [ ] **5.1.8** `scripts/run-controlled-smoke.ps1` passes.
- [ ] **5.1.9** `scripts/dev-git-check.ps1` passes.
- [ ] **5.1.10** `git diff --check` clean.
- [ ] **5.1.11** Source URL traceability: `placeholder_count = 0`, `missing_count = 0` for fixture E2E runs.
- [ ] **5.1.12** ASCII-safe default output confirmed on all CLI commands.
- [ ] **5.1.13** `--utf8` flag works correctly (if implemented).
- [ ] **5.1.14** Correction workflow E2E validation passes (replace + amend + traceability).
- [ ] **5.1.15** Undo workflow validation passes (if implemented).
- [ ] **5.1.16** Dev Ledger updated with final state.
- [ ] **5.1.17** No push, PR, merge, tag, or release. (local commit only)

---

## Appendix A: Implementation Order and Dependencies

```
0.1 Roadmap v2.9 planning  ← this checkpoint (docs-only)
     │
1.1 Output mode contract and CLI policy  ← no dependencies
     │
1.2 Implement --utf8 opt-in flag  ← depends on 1.1 (contract)
     │
2.1 Quality gate source URL fixture audit  ← no code dependency on 1.x; can be parallel
     │
2.2 Quality gate source URL fixture cleanup  ← depends on 2.1 (audit/plan)
     │
3.1 Correction rollback/undo policy review  ← no code dependency on 1.x/2.x; can be parallel
     │
3.2 Replace-all mode policy review  ← no code dependency; can be parallel with 3.1
     │
4.1 Operational validation refresh  ← depends on 1.2, 2.2, 3.1 (if implemented)
     │
5.1 Final v2.9 validation checkpoint  ← depends on 1.1–4.1
```

Items 2.1, 3.1, and 3.2 can be worked in parallel with items 1.1–1.2. Item 4.1 benefits from all preceding items being complete.

## Appendix B: Deferred Items Closed by v2.9

| # | Item | v2.8 Status | v2.9 Disposition |
|---|------|------------|-----------------|
| 1 | `--utf8` opt-in flag not implemented | v2.8 item 4.1 gap | Closed by items 1.1, 1.2 |
| 2 | Quality gate fixture/source URL strictness deferred | v2.8 item 5.1 deferral | Closed by items 2.1, 2.2 |
| 3 | `--replace-all` mode deferred | v2.8 contract Section 4.4 | Evaluated in item 3.2 |
| 4 | Optional rollback/undo deferred | v2.8 Appendix F item 1 | Evaluated in item 3.1 |
| 5 | Quality gate source URL missing scenarios | v2.8 deferral doc | Closed by items 2.1, 2.2 |

## Appendix C: Explicit Non-Goals

- **Do not** add new product layers (no Pain Discovery Layer integration, no new pipeline stages).
- **Do not** add live LLM/API calls. All items remain deterministic-first.
- **Do not** rewrite, refactor, or redesign the v2.6/v2.7/v2.8 weekly cycle pipeline.
- **Do not** add new collectors, sources, or source expansion.
- **Do not** add a database, persistent server, or UI.
- **Do not** add embeddings, vector search, or ML features.
- **Do not** add autonomous portfolio transitions.
- **Do not** add multi-user, multi-tenant, or venture-studio features.
- **Do not** add email/push notifications or scheduled periodic runs.
- **Do not** broaden beyond the existing HN + GitHub source loop.
- **Do not** implement LLM-assisted decision suggestions or LLM-driven corrections.
- **Do not** replace the v2.8 correction workflow.
- **Do not** weaken the source URL traceability scanner.
- **Do not** add a correction UI beyond CLI flags.
- **Do not** implement batch undo (undoing multiple corrections at once) — single-step undo only if implemented.
- **Do not** add portfolio mutation or autonomous decisions.
- **Do not** add new idea-generation layers.

## Appendix D: Mitigations for Known Risks

| Risk | Mitigation |
|------|-----------|
| `--utf8` flag breaks ASCII-safe default | Item 1.2 preserves ASCII-safe as default; all existing tests must pass unchanged |
| Quality gate fixture fix cascades unexpectedly | Item 2.1 audits exact impact before item 2.2 makes changes |
| Undo implementation is larger than expected | Item 3.1 has explicit deferral path; policy-only is acceptable outcome |
| Replace-all mode is requested but unsafe | Item 3.2 prefer deferral unless clear need AND small implementation |
| v2.8 correction workflow breaks from v2.9 changes | Item 4.1 re-validates all C1–C14 steps; item 5.1 confirms E2E |
| Unicode symbol audit is incomplete | Item 1.1 contract requires exhaustive symbol mapping table |
| Source URL scanner is weakened to pass `missing_count=0` | Acceptance criterion 2.2.5 explicitly forbids scanner weakening |

## Appendix E: v2.10+ Hook Notes

The following items are explicitly out of scope for v2.9 but are recognized as natural follow-up work:

| # | Item | Rationale for deferral |
|---|------|----------------------|
| 1 | Multi-step undo (undoing more than last correction) | Requires correction stack navigation; v2.9 evaluates single-step undo only |
| 2 | LLM-assisted decision suggestions | LLM integration is deferred to v2.10+ per strategic principles |
| 3 | Pain Discovery Layer integration | PDL is a separate product layer; integration requires its own roadmap |
| 4 | Batch correction across multiple runs | Cross-run correction semantics are complex; v2.9 focuses on single-run safety |
| 5 | Automated correction suggestions | Requires recurrence memory and evidence-change detection; v2.10+ ML/LLM feature |
| 6 | Correction UI beyond CLI flags | UI is out of scope for all v2.x roadmaps per scope-v1 |
| 7 | `--utf8` on all CLI commands | v2.9 scopes `--utf8` to status/dashboard/report only; expansion is v2.10+ |
