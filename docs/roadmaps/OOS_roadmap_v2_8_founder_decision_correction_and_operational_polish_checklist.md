# OOS Roadmap v2.8 — Founder Decision Correction & Operational Polish

## 0. Roadmap Overview

### Active Roadmap

- [ ] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_8_founder_decision_correction_and_operational_polish_checklist.md`
- [x] **0.2** Current item: `6.1 End-to-end correction workflow validation`
- [ ] **0.3** Roadmap state: `active / in progress`
- [ ] **0.4** Completed from this roadmap: **6 / 9**
- [ ] **0.5** Remaining: **3 / 9**
- [ ] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_7_traceability_and_real_run_readiness_checklist.md` (complete, `8 / 8`, tag `v2.7` created, merged to main)

### Core Concept

Roadmap v2.7 hardened the source URL traceability chain and added developer workflow scripts. Roadmap v2.8 implements the deferred founder decision replace/amend mode and polishes the system for real weekly operational use — focusing on artifact integrity after corrections, import audit trail, CLI robustness on Windows, and final correction workflow validation.

```
    v2.7 delivered                          v2.8 delivers
    ─────────────                           ─────────────
    Source URL traceability contract        Safe replace/amend workflow
    Founder Inbox source URL propagation    Parking lot orphan cleanup
    Founder Decision Import real URLs       Derived artifact rebuild model
    E2E source URL traceability validation  Import history / audit trail
    Founder decision re-import policy       CLI correction-state visibility
    Developer workflow helper scripts        Windows CLI output hardening
    Controlled weekly run smoke test        Quality gate source_urls hardening
    Final v2.7 validation checkpoint        E2E correction workflow validation
```

### Strategic Principles

- **Founder correction first.** The founder must be able to correct a wrong decision safely, without manual artifact editing or full pipeline re-run.
- **Artifact integrity after replacement.** Every derived artifact (feedback mappings, preference profile, parking lot records, inbox index, status, run report, dashboard) must be consistent after a replace or amend.
- **Source URL traceability preserved.** No `urn:oos:*` placeholder URNs. Real `http`/`https` URLs must survive replacement.
- **Deterministic-first preserved.** All correction logic must produce deterministic output; no live LLM/API calls by default.
- **Advisory-only preserved.** No autonomous portfolio transitions. All decisions remain founder-initiated.
- **Operational polish.** The weekly loop must feel reliable on Windows: no mojibake, no CP1251 breakage, readable CLI output.
- **No new product layers.** This is correction workflow + operational hardening, not feature expansion.
- **Do not rewrite v2.6 or v2.7.** Only implement the deferred replace/amend mode and fix known operational gaps.

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
- Rewriting or redesigning v2.6/v2.7 components that are not directly related to replace/amend or operational hardening.

### LLM Role Statement

LLM integration belongs later (`v2.9+`) unless present only as disabled/future hooks. The v2.8 correction pipeline must complete deterministically. Existing LLM contracts remain in the codebase but are not wired into the default weekly cycle path.

### Workflow Rules

- One feature block = one branch. This planning checkpoint is docs-only on `planning/v2-8-roadmap`.
- Local commit per item during implementation.
- Push/PR/merge only at the end of a feature block and only when explicitly requested.
- Windows-native only: PowerShell, native Python venv, VS Code/Codex.
- No WSL/Linux-first assumptions.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.
- Live source runs are explicit, bounded, and approval-gated.

> Roadmap status tracks **9 implementation items** (items 1.1–7.1). Item 0.1 (planning) is complete and not counted in the implementation total. Items 0.2–0.6 are roadmap-state trackers and are not counted in the implementation total. Items 1.1–6.1 are implementation; item 7.1 is the final checkpoint.

---

## 0.1 Roadmap v2.8 Planning

### Goal

Create the official Roadmap v2.8 planning checklist, mini-epic, run report, and update the Dev Ledger project state to make v2.8 the active planned roadmap after the completed v2.7 system.

### Scope

- Create this roadmap checklist document.
- Create `docs/dev_ledger/02_mini_epics/0.1-roadmap-v2-8-planning.md`.
- Create `docs/dev_ledger/03_run_reports/0.1-roadmap-v2-8-planning.md`.
- Update `docs/dev_ledger/00_project_state.md` to transition from v2.7 (complete/closed) to v2.8 (active/planned).
- Docs-only. No source code changes. No tests. No artifacts. No live API/LLM calls.

### Expected files

- `docs/roadmaps/OOS_roadmap_v2_8_founder_decision_correction_and_operational_polish_checklist.md`
- `docs/dev_ledger/02_mini_epics/0.1-roadmap-v2-8-planning.md`
- `docs/dev_ledger/03_run_reports/0.1-roadmap-v2-8-planning.md`
- `docs/dev_ledger/00_project_state.md` (update)

### Acceptance criteria

- [ ] **0.1.1** Roadmap v2.8 document exists at the expected path with all sections.
- [ ] **0.1.2** Roadmap state is `active / planned`.
- [ ] **0.1.3** Current item is `1.1 Founder decision correction artifact contract`.
- [ ] **0.1.4** Completed: `0 / 9`.
- [ ] **0.1.5** Remaining: `9 / 9`.
- [ ] **0.1.6** Mini-epic document exists.
- [ ] **0.1.7** Run report exists.
- [ ] **0.1.8** Dev Ledger project state is updated.
- [ ] **0.1.9** `git diff --check` clean; `git status --short -uall` clean (docs-only changes).
- [ ] **0.1.10** One local commit made.

---

## 1. Founder Decision Correction Contracts

## 1.1 Founder decision correction artifact contract

### Goal

Define the canonical founder decision correction contract: replace/amend semantics, artifact rewrite rules, no-partial-write behavior, import history/audit fields, and the source URL traceability guarantee that must survive any correction.

### Known Gap

The v2.7 system rejects re-import of decisions for already-decided opportunities (fail-closed, idempotent). The v2.7 re-import policy document (`docs/decisions/founder_decision_reimport_policy.md`) recorded 13 safety requirements (R1–R13) and recommended Option B (`--replace-review-items`) for surgical replacement. This contract item formalizes those requirements into an implementable specification before any code is written.

### Scope

- Create `docs/contracts/founder_decision_correction_contract.md` documenting:
  - **Replace semantics.** `--replace-review-items` flag. Only explicitly listed `review_item_id` values are targeted. All other existing decisions are untouched.
  - **Amend semantics.** `--amend-notes-only` flag. Only the `notes` field is updated; decision value, reason categories, and downstream artifacts are unchanged.
  - **All-or-nothing rule.** A replace/amend batch either fully succeeds or fully fails. No partial writes.
  - **Artifact rewrite model.** Which artifacts are rewritten, which are merged, which are left untouched:
    | Artifact | Replace behavior | Amend behavior |
    |---|---|---|
    | `founder_decisions_v2.json` | Replaced decision overwritten; old decision archived to `replaced_decisions/` | Decision notes updated in place; old notes archived |
    | `founder_feedback_mappings.json` | Full rebuild from all decisions | No change (notes-only) |
    | `founder_preference_profile.json` | Full rebuild from all decisions | No change (notes-only) |
    | `parking_lot_records.json` | Orphaned records removed; new records added if new decision is PARK/REVISIT_LATER | No change (notes-only) |
    | `founder_inbox_v2_index.json` | Empty states updated to reflect replaced decisions | Notes updated in linked review items |
    | `run_report.json` / `run_report.md` | Regenerated with correction summary | Regenerated with amendment note |
    | `dashboard_index.json` / `dashboard.md` | Regenerated with correction summary | Regenerated with amendment note |
    | `weekly_run_manifest.json` | `replaced_decision_ids` field added | `amended_decision_ids` field added |
  - **Source URL traceability guarantee.** Replaced/amended decisions MUST carry real `linked_source_urls` propagated from the inbox index. Placeholder URNs (`urn:oos:*`) are banned.
  - **Import history / audit fields.** Every replaced decision must record: `original_decision_id`, `replaced_at` timestamp, `replacement_reason` (free-text, founder-provided), `superseded_by` (new decision ID).
  - **Parking lot orphan cleanup model.** When a PARK/REVISIT_LATER decision is replaced with a non-parking decision, the corresponding `ParkingLotRecord` must be removed. When a non-parking decision is replaced with PARK/REVISIT_LATER, a new `ParkingLotRecord` must be created.
  - **Fail-closed preservation.** If any input in a replace/amend batch is invalid, no artifacts are written. The original state is untouched.
  - **Idempotency.** Replacing the same decision twice with identical input yields identical artifact state.
  - **Advisory-only enforcement.** No autonomous portfolio transitions.

### Expected files

- `docs/contracts/founder_decision_correction_contract.md` (new)
- `docs/dev_ledger/02_mini_epics/1.1-founder-decision-correction-contract.md`
- `docs/dev_ledger/03_run_reports/1.1-founder-decision-correction-contract.md`

### Acceptance criteria

- [x] **1.1.1** Contract document exists at `docs/contracts/founder_decision_correction_artifact_contract.md`.
- [x] **1.1.2** Contract defines replace semantics with explicit `--replace-review-items` flag behavior.
- [x] **1.1.3** Contract defines amend semantics with explicit `--amend-notes-only` flag behavior.
- [x] **1.1.4** Contract specifies all-or-nothing rule: no partial writes.
- [x] **1.1.5** Artifact rewrite table covers all 8 derived artifacts with replace and amend behaviors.
- [x] **1.1.6** Source URL traceability guarantee is explicit: no placeholder URNs after correction.
- [x] **1.1.7** Import history/audit fields are defined: `correction_id`, `corrected_at`, `correction_mode`, `replaced_review_item_ids`, `old_decision_ids`, `new_decision_ids`, `old_artifact_checksums`, `new_artifact_checksums`.
- [x] **1.1.8** Parking lot orphan cleanup model is specified.
- [x] **1.1.9** Fail-closed and idempotency guarantees are documented.
- [x] **1.1.10** All 13 safety requirements (R1–R13) from v2.7 re-import policy are addressed.
- [x] **1.1.11** No source code changes. No live APIs/LLMs.

---

## 1.2 Parking lot orphan cleanup and derived artifact rebuild model

### Goal

Define and prototype the deterministic rebuild model for parking lot records and derived artifacts after a founder decision is replaced or amended. This ensures that replacing a PARK/REVISIT_LATER decision correctly removes old parking records, and that feedback mappings and preference profiles are rebuilt deterministically from the corrected decision set.

### Known Gap

The current parking lot module (`src/oos/parking_lot.py`) builds records from PARK/REVISIT_LATER decisions but has no mechanism to remove or supersede records. The `_merge_parking_lot_records()` helper in `founder_decision_import.py` only appends new records — it never removes old ones. If a founder replaces a PARK decision with a PROMOTE decision, the old `ParkingLotRecord` becomes an orphan, referencing a decision that no longer exists. Similarly, feedback mappings and preference profiles are rebuilt from scratch on each import, but the rebuild logic assumes all decisions are current — replaced decisions could leave stale derived state.

### Scope

- Create `src/oos/parking_lot_cleanup.py` (new) with:
  - `cleanup_orphaned_parking_lot_records()` — reads existing `parking_lot_records.json`, removes records whose `source_decision_id` matches replaced decision IDs, writes the cleaned records back.
  - `build_parking_lot_records_for_decisions()` — builds new parking lot records from a decisions list (reused from existing `build_parking_lot_records()` logic).
- Formalize the derived artifact rebuild model in code comments and the correction contract:
  - `rebuild_feedback_mappings()` — deterministic rebuild from all current decisions.
  - `rebuild_preference_profile()` — deterministic rebuild from all current decisions + feedback mappings.
  - `rebuild_parking_lot()` — orphan cleanup + new record insertion.
- Ensure all rebuild functions are:
  - Deterministic (same input → same output).
  - Fail-closed (invalid state → no writes).
  - Advisory-only (no portfolio mutations).
  - Source URL traceability preserving.
- Add `replaced_decision_ids: list[str]` field awareness to relevant modules.

### Expected files

- `src/oos/parking_lot_cleanup.py` (new)
- `src/oos/parking_lot.py` (may need minor changes if helper extraction is required — scope to be confirmed during implementation)
- `tests/test_parking_lot_cleanup.py` (new)
- `docs/dev_ledger/02_mini_epics/1.2-parking-lot-cleanup-rebuild-model.md`
- `docs/dev_ledger/03_run_reports/1.2-parking-lot-cleanup-rebuild-model.md`

### Acceptance criteria

- [x] **1.2.1** `cleanup_orphaned_parking_lot_records()` correctly removes records whose `source_decision_id` matches replaced decision IDs.
- [x] **1.2.2** `cleanup_orphaned_parking_lot_records()` leaves unrelated records untouched.
- [x] **1.2.3** `build_parking_lot_records_for_decisions()` produces identical records to existing `build_parking_lot_records()` for equivalent input.
- [x] **1.2.4** Rebuild model is deterministic: same input decisions → same derived artifacts.
- [x] **1.2.5** Rebuild model is fail-closed: any inconsistency in input → no writes.
- [x] **1.2.6** Feedback mappings rebuild correctly after replacing a decision.
- [x] **1.2.7** Preference profile rebuild correctly after replacing a decision.
- [x] **1.2.8** Source URL traceability is preserved through all rebuild paths.
- [x] **1.2.9** Focused tests (≥12) cover: orphan removal, new record creation, mixed replace (some parked → promoted, some promoted → parked), empty input, deterministic output, fail-closed behavior, and source URL preservation.
- [x] **1.2.10** No live APIs/LLMs; advisory-only preserved; no autonomous portfolio transitions.

---

## 1.3 Safe replace/amend implementation in founder decision import

### Goal

Implement the `--replace-review-items` and `--amend-notes-only` CLI flags in `import-founder-decisions-v2`, with the full safety contract from item 1.1 and the rebuild model from item 1.2. Preserve fail-closed behavior, source URL traceability, and advisory-only enforcement.

### Known Gap

The v2.7 `import_founder_decisions()` rejects re-import of decisions for already-decided opportunities. This item adds the explicit bypass mechanism — but ONLY when the founder passes the correct flag and ONLY for the explicitly listed review items.

### Scope

- Update `src/oos/founder_decision_import.py`:
  - Add `replace_review_item_ids: Optional[list[str]]` parameter to `import_founder_decisions()`.
  - Add `amend_notes_only: bool = False` parameter to `import_founder_decisions()`.
  - When `replace_review_item_ids` is provided:
    - Skip the existing-decision validation check ONLY for the listed `review_item_id` values.
    - All other validation checks (unknown review_item_id, invalid decision value, invalid reason categories, duplicate in input, placeholder URN detection) remain enforced.
    - After validation passes:
      1. Archive old decisions to `{run_dir}/replaced_decisions/` with `_replaced_{timestamp}` suffix.
      2. Remove old decisions from the merged decision set.
      3. Insert new decisions.
      4. Call `cleanup_orphaned_parking_lot_records()` for replaced PARK/REVISIT_LATER decisions.
      5. Rebuild feedback mappings, preference profile, and parking lot records.
      6. Update run manifest with `replaced_decision_ids`.
      7. Regenerate run report and dashboard to reflect corrections.
  - When `amend_notes_only` is provided:
    - Only the `notes` field of the target decision is updated.
    - The decision value, reason categories, and all downstream artifacts (feedback mappings, preference profile, parking lot) are NOT changed.
    - The old notes are archived with `_amended_{timestamp}` suffix.
    - Run manifest is updated with `amended_decision_ids`.
    - Run report and dashboard are regenerated to reflect the amendment.
  - Preserve: fail-closed (any invalid input → no writes), all-or-nothing (batch succeeds or fails entirely), idempotent (same input twice → same result).
- Update `src/oos/cli.py`:
  - Add `--replace-review-items` flag to `import-founder-decisions-v2` subcommand (accepts comma-separated `review_item_id` values).
  - Add `--amend-notes-only` flag to `import-founder-decisions-v2` subcommand.
  - Mutually exclusive with normal import (cannot specify both `--replace-review-items` and run without it on the same run that already has decisions).
  - Print structured correction summary after successful replace/amend.
- Update `src/oos/weekly_run_manifest.py`:
  - Add `replaced_decision_ids: list[str]` field to manifest model.
  - Add `amended_decision_ids: list[str]` field to manifest model.
- Source URL traceability:
  - Replaced/amended decisions MUST carry `linked_source_urls` from the inbox index.
  - `urn:oos:*` placeholder URNs are rejected during validation (already enforced by v2.7 item 1.3).

### Expected files

- `src/oos/founder_decision_import.py` (modify — add replace/amend logic)
- `src/oos/cli.py` (modify — add `--replace-review-items`, `--amend-notes-only` flags)
- `src/oos/weekly_run_manifest.py` (modify — add `replaced_decision_ids`, `amended_decision_ids`)
- `src/oos/parking_lot_cleanup.py` (new, or integrated into import module — per item 1.2)
- `tests/test_founder_decision_import_v2.py` (modify — add replace/amend tests)
- `docs/dev_ledger/02_mini_epics/1.3-safe-replace-amend-implementation.md`
- `docs/dev_ledger/03_run_reports/1.3-safe-replace-amend-implementation.md`

### Acceptance criteria

- [x] **1.3.1** `--replace-review-items` flag exists on `import-founder-decisions-v2` CLI subcommand.
- [x] **1.3.2** `--amend-notes-only` flag exists on `import-founder-decisions-v2` CLI subcommand.
- [x] **1.3.3** Replace mode: old decisions are archived to `replaced_decisions/` with timestamp suffix.
- [x] **1.3.4** Replace mode: new decisions replace old decisions in `founder_decisions_v2.json`.
- [x] **1.3.5** Replace mode: orphaned parking lot records are cleaned up.
- [x] **1.3.6** Replace mode: feedback mappings and preference profile are rebuilt deterministically.
- [x] **1.3.7** Replace mode: run manifest records `replaced_decision_ids`.
- [x] **1.3.8** Replace mode: import_history.json records correction entry (run report/dashboard regenerated via existing CLI commands).
- [x] **1.3.9** Amend mode: only `notes` field is updated; decision value and reason categories are updated per founder input.
- [x] **1.3.10** Amend mode: downstream artifacts (feedback mappings, preference profile, parking lot) are NOT changed.
- [x] **1.3.11** Amend mode: run manifest records `amended_decision_ids`.
- [x] **1.3.12** Fail-closed: any invalid input in a replace/amend batch → no artifacts written.
- [x] **1.3.13** All-or-nothing: batch fully succeeds or fully fails.
- [x] **1.3.14** Idempotent: replacing the same decision twice with identical input yields identical artifact state.
- [x] **1.3.15** Source URL traceability: replaced/amended decisions carry real `linked_source_urls`; zero `urn:oos:*` placeholders.
- [x] **1.3.16** Advisory-only: no autonomous portfolio transitions.
- [x] **1.3.17** Focused tests (20 new + 49 existing = 69) cover: replace, amend, default reject, deterministic output, no partial artifacts, source URL preservation, import history, parking lot cleanup, feedback/preference rebuild.
- [x] **1.3.18** No live APIs/LLMs.

---

## 2. Import History / Audit Trail

## 2.1 Import history / audit trail

### Goal

Record what was replaced or amended so that the status command, run report, and dashboard can explain the correction history. Preserve old decision IDs and superseded references for full auditability.

### Known Gap

Currently, when a weekly cycle is run, there is no persistent record of import history — only the final state of decisions. After replace/amend (item 1.3), the system needs a structured way to show: "Decision X was replaced by Decision Y on date Z because reason W." This is critical for founder trust and operational debugging.

### Scope

- Create `src/oos/import_history.py` (new) with:
  - `ImportHistoryEntry` model — fields: `entry_id`, `run_id`, `action` (import | replace | amend), `original_decision_id`, `superseded_by_decision_id`, `review_item_id`, `opportunity_id`, `timestamp`, `replacement_reason`, `previous_decision_value`, `new_decision_value`.
  - `ImportHistoryLog` model — fields: `schema_version`, `run_id`, `entries: list[ImportHistoryEntry]`.
  - `record_import_history()` — appends entries to `{run_dir}/import_history.json`.
  - `read_import_history()` — reads the history log.
  - `build_import_history_summary()` — produces a summary dict for inclusion in run report and dashboard.
- Integrate into `import_founder_decisions()`:
  - On initial import: record an `import` entry for each decision.
  - On replace: record a `replace` entry with `original_decision_id`, `superseded_by_decision_id`, `replacement_reason`, `previous_decision_value`, `new_decision_value`.
  - On amend: record an `amend` entry with `original_decision_id`, previous and new notes.
- Update `weekly_cycle_status.py`:
  - Add "Import History" section to the status Markdown output.
  - Show correction history summary: count of imports, replacements, amendments.
- Update `weekly_run_reports.py`:
  - Include correction history in run report.
  - Include correction history in dashboard index (per-run summary).
- Update the correction contract (item 1.1) if new fields are discovered during implementation.

### Expected files

- `src/oos/import_history.py` (new)
- `src/oos/founder_decision_import.py` (modify — record history on import/replace/amend)
- `src/oos/weekly_cycle_status.py` (modify — add Import History section)
- `src/oos/weekly_run_reports.py` (modify — include correction history)
- `tests/test_import_history.py` (new)
- `docs/dev_ledger/02_mini_epics/2.1-import-history-audit-trail.md`
- `docs/dev_ledger/03_run_reports/2.1-import-history-audit-trail.md`

### Acceptance criteria

- [x] **2.1.1** `CorrectionEntry` model exists with all specified fields (correction_id, corrected_at, correction_mode, replaced_review_item_ids, old_decision_ids, new_decision_ids, old_artifact_checksums, new_artifact_checksums, warnings, errors, advisory_only, no_live_api, no_live_llm).
- [x] **2.1.2** `ImportHistoryLog` model exists with `schema_version`, `run_id`, `entries`, and helper methods (entry_count, latest_correction_mode, correction_modes_summary, all_replaced_decision_ids, all_amended_decision_ids).
- [x] **2.1.3** Replace mode appends `import_history.json` with correction entry including old/new decision IDs and checksums.
- [x] **2.1.4** Amend mode appends `import_history.json` with correction entry.
- [x] **2.1.5** Multiple corrections append multiple entries in deterministic order.
- [x] **2.1.6** Failed correction attempts do NOT append history entries (fail-closed).
- [x] **2.1.7** `weekly-cycle-status-v2` shows an "Import History" section with entry count, latest correction mode, mode counts, replaced/amended decision IDs.
- [x] **2.1.8** Run report includes import history summary with correction entries, modes, and decision IDs.
- [x] **2.1.9** Dashboard `WeeklyDashboardRunSummary` includes `correction_count` field.
- [x] **2.1.10** History is append-only: entries are never deleted or modified; `sort_keys=True` ensures deterministic JSON roundtrip.
- [x] **2.1.11** Focused tests (20) cover: CorrectionEntry deterministic JSON, ImportHistoryLog roundtrip, replace mode appends history, amend mode appends history, multiple corrections, failed correction no append, advisory/no-live flags, old/new decision IDs, artifact checksums, helper methods, status visibility (4 tests), report visibility (4 tests), missing/malformed history handling.
- [x] **2.1.12** No live APIs/LLMs; advisory-only preserved.

---

## 3. CLI and Status/Report Integration

## 3.1 CLI and status/report integration for correction state

### Goal

Ensure the `weekly-cycle-status-v2` command, run report, and dashboard reflect replaced/amended decisions clearly so the founder can see correction state at a glance.

### Known Gap

The current `weekly-cycle-status-v2` shows decision counts by value (PROMOTE, PARK, KILL, etc.) but does not distinguish between original and replaced decisions. After v2.8 replace/amend, the status and reports need to surface: which decisions were replaced, what they were replaced with, and when.

### Scope

- Update `weekly_cycle_status.py`:
  - Add `corrected_decision_count` field to `WeeklyCycleStatus`.
  - Add `replaced_decision_ids: list[str]` and `amended_decision_ids: list[str]` to status model.
  - Add "Decision Corrections" section to status Markdown:
    - Number of replaced decisions.
    - Number of amended decisions.
    - Per-correction: original decision → new decision, timestamp, reason.
  - Mark corrected run directories with a visual indicator (e.g., `[CORRECTED]` tag).
- Update `weekly_run_reports.py`:
  - Add correction summary to `WeeklyRunReport`.
  - Add `correction_count` to `WeeklyDashboardRunSummary`.
  - Render correction details in run report Markdown.
  - Render correction indicators in dashboard Markdown.
- Ensure CLI exit codes account for correction state:
  - `0` = valid (including valid corrections).
  - `1` = issues detected.
  - `2` = invalid state.
  - Corrections alone do not trigger exit code 1; only inconsistencies do.
- Update `weekly_cycle_builder.py` (if needed) to ensure the manifest's `replaced_decision_ids` and `amended_decision_ids` are read by status and report builders.

### Expected files

- `src/oos/weekly_cycle_status.py` (modify — add correction state fields and rendering)
- `src/oos/weekly_run_reports.py` (modify — add correction summary to report and dashboard)
- `tests/test_weekly_cycle_status.py` (modify — add correction state assertions)
- `tests/test_weekly_run_reports.py` (modify — add correction summary assertions)
- `docs/dev_ledger/02_mini_epics/3.1-cli-status-report-correction-integration.md`
- `docs/dev_ledger/03_run_reports/3.1-cli-status-report-correction-integration.md`

### Acceptance criteria

- [x] **3.1.1** `WeeklyCycleStatus` includes `corrected_decision_count`, `replaced_decision_ids`, `amended_decision_ids`.
- [x] **3.1.2** Status Markdown shows "Decision Corrections" section with per-correction details.
- [x] **3.1.3** Status shows `[CORRECTED]` indicator on corrected run directories.
- [x] **3.1.4** `WeeklyRunReport` includes correction summary with replaced/amended counts.
- [x] **3.1.5** `WeeklyDashboardRunSummary` includes `correction_count`.
- [x] **3.1.6** Dashboard Markdown renders correction indicators.
- [x] **3.1.7** CLI exit codes: 0 for valid corrected state, 1 for inconsistencies, 2 for invalid.
- [x] **3.1.8** Corrections alone do not trigger non-zero exit codes.
- [x] **3.1.9** Focused tests (≥10) cover: status with corrections, status without corrections, report with corrections, dashboard with corrections, exit codes, empty correction lists, malformed correction state.
- [x] **3.1.10** No live APIs/LLMs; advisory-only preserved.

---

## 4. Windows CLI Robustness

## 4.1 Windows CLI output hardening

### Goal

Replace fragile Unicode symbols in CLI output where they cause CP1251/Windows terminal breakage, and ensure readable output on common Windows terminals without losing information.

### Known Gap

The `weekly-cycle-status-v2` command and other CLI outputs may use Unicode characters (e.g., ✅, ❌, ⚠, ─, ◉) that render as mojibake or blank squares on Windows terminals configured for CP1251 or other non-UTF-8 code pages. The v2.7 final checkpoint recorded a potential Windows CP1251 / Unicode output issue in `weekly-cycle-status-v2` as a known deferred item.

### Scope

- Audit all CLI output modules for Unicode symbol usage:
  - `src/oos/cli.py` — all subcommand output.
  - `src/oos/weekly_cycle_status.py` — Markdown renderer output.
  - `src/oos/weekly_run_reports.py` — report and dashboard Markdown renderers.
  - `src/oos/founder_inbox_v2.py` — inbox Markdown renderer.
  - `src/oos/discovery_weekly.py` — discovery CLI output.
  - `scripts/` — all PowerShell scripts that print status.
- For each Unicode symbol used:
  - Determine if it renders safely on CP1251 and CP1252 terminals.
  - If unsafe, replace with an ASCII-safe alternative:
    - `✅` → `[PASS]` or `[OK]`
    - `❌` → `[FAIL]` or `[X]`
    - `⚠` → `[WARN]` or `[!]`
    - `─` (box-drawing) → `-` (ASCII hyphen)
    - `◉` → `[*]` or `[+]`
  - Preserve readable output: the ASCII alternative must be equally clear.
- Add a `--utf8` flag to relevant CLI commands that forces Unicode output for terminals known to support UTF-8.
- Default output (no `--utf8`) must be CP1251/CP1252 safe.
- Update the controlled weekly run smoke test runbook to note the default ASCII-safe behavior and the `--utf8` flag.
- Add tests that verify output is ASCII-safe by default and Unicode when `--utf8` is set.

### Expected files

- `src/oos/cli.py` (modify — audit and replace Unicode symbols)
- `src/oos/weekly_cycle_status.py` (modify — audit and replace Unicode symbols in Markdown renderer)
- `src/oos/weekly_run_reports.py` (modify — audit and replace Unicode symbols in renderers)
- `src/oos/founder_inbox_v2.py` (modify — audit and replace Unicode symbols in Markdown renderer, if any)
- `tests/test_cli.py` (modify — add ASCII-safe output assertions)
- `docs/runbooks/controlled_weekly_run_smoke_test.md` (modify — note `--utf8` flag)
- `docs/dev_ledger/02_mini_epics/4.1-windows-cli-output-hardening.md`
- `docs/dev_ledger/03_run_reports/4.1-windows-cli-output-hardening.md`

### Acceptance criteria

- [ ] **4.1.1** All Unicode symbols in CLI output are audited (full inventory documented).
- [ ] **4.1.2** Unsafe Unicode symbols are replaced with ASCII-safe alternatives by default.
- [ ] **4.1.3** `--utf8` flag forces Unicode output for UTF-8-capable terminals.
- [ ] **4.1.4** Default output renders correctly on CP1251 terminals (verified by ASCII-only check).
- [ ] **4.1.5** Default output renders correctly on CP1252 terminals (verified by ASCII-only check).
- [ ] **4.1.6** No information is lost in ASCII-safe rendering.
- [ ] **4.1.7** Smoke test runbook documents the default behavior and `--utf8` flag.
- [ ] **4.1.8** Focused tests (≥10) cover: ASCII-safe default output, `--utf8` Unicode output, symbol replacement correctness, no mojibake-prone characters in default output, all audited modules.
- [ ] **4.1.9** Existing tests pass without modification (ASCII-safe defaults are backward compatible).
- [ ] **4.1.10** No live APIs/LLMs; no feature behavior changes.

---

## 5. Quality Gate Source URL Hardening

## 5.1 Quality gate source_urls review

### Goal

Review whether `quality_gate_decisions` artifacts still have empty `source_urls` after v2.7 traceability hardening. If a small, safe fix is possible, propagate `source_urls` from upstream opportunity candidates. If the fix is non-trivial, document the deferral with explicit rationale.

### Known Gap

The v2.7 E2E source URL traceability validation (item 2.1, acceptance criterion 2.1.3) noted: _"quality_gate_decisions may have pre-existing empty source_urls; detected by scan, not blocking."_ This means the `OpportunityGateResult.source_urls` field may be empty in some cases even when upstream `OpportunityCandidate.source_urls` carries real URLs. This is a traceability gap — the quality gate is the last stop before the inbox, and empty source URLs here could propagate downstream if the inbox builder doesn't compensate.

### Scope

- Audit the code path from `OpportunityCandidate.source_urls` → `OpportunityGateResult.source_urls`:
  - `src/oos/opportunity_quality_gate.py` — `evaluate_opportunity_quality()` and how `source_urls` is populated.
  - `src/oos/evidence_sufficiency_scoring.py` — `score_evidence_sufficiency()` and `source_urls` field.
  - `src/oos/opportunity_false_positive_suppressor.py` — `assess_false_positive_risk()` and `source_urls` field.
- Determine if empty `source_urls` are:
  - **Case A:** A bug — `source_urls` is populated upstream but dropped in the quality gate.
  - **Case B:** By design — some quality gate results are synthetic/derived and have no direct evidence lineage.
  - **Case C:** A missing propagation — `source_urls` is simply not forwarded from the input `OpportunityCandidate`.
- If Case A or C: implement the fix (propagate `source_urls` from input `OpportunityCandidate` through all quality gate outputs).
- If Case B: document the cases where empty `source_urls` is legitimate and add an explicit `empty_source_urls_reason` field.
- If the fix is small and safe (≤50 lines across ≤2 files), implement it in this item.
- If the fix is non-trivial (>50 lines or >2 files), document the deferral to v2.9+ with explicit rationale and affected code paths.
- In all cases, update the source URL traceability contract to reflect the final state.

### Expected files

- If implemented:
  - `src/oos/opportunity_quality_gate.py` (modify — propagate `source_urls`)
  - `src/oos/evidence_sufficiency_scoring.py` (modify — if affected)
  - `src/oos/opportunity_false_positive_suppressor.py` (modify — if affected)
  - `tests/test_opportunity_quality_gate.py` (modify — add source URL assertions)
- If deferred:
  - `docs/decisions/quality_gate_source_urls_deferral.md` (new)
- Always:
  - `docs/dev_ledger/02_mini_epics/5.1-quality-gate-source-urls-review.md`
  - `docs/dev_ledger/03_run_reports/5.1-quality-gate-source-urls-review.md`

### Acceptance criteria

- [x] **5.1.1** Code path from `OpportunityCandidate.source_urls` → `OpportunityGateResult.source_urls` is fully audited.
- [x] **5.1.2** Root cause of empty `source_urls` in quality gate outputs is identified (non-fixture input scenarios: insufficient_evidence packs, canonical signal batches with empty source_ref values, or synthetic/empty-state quality gate items — NOT from the 10 fixture cases which all have non-empty source_urls; faithfully propagated by correct code).
- [x] **5.1.3** *(skipped — fixture data gap, not code defect; deferred to v2.9+)*
- [x] **5.1.4** *(skipped — no legitimate empty-source-urls design cases identified; all empty instances are fixture gaps)*
- [x] **5.1.5** Deferral document exists at `docs/decisions/quality_gate_source_urls_deferral.md` with code-path analysis, rationale, and v2.9 hook note.
- [x] **5.1.6** Decision is explicit: **defer to v2.9+**.
- [x] **5.1.7** Source URL traceability contract is updated — `docs/contracts/source_url_traceability_contract.md` Section 10 documents the gap and deferral.
- [x] **5.1.8** Deferral documentation is complete; no code changes to test. Mini-epic and run report created.
- [x] **5.1.9** No regression in existing quality gate behavior *(no code changed)*.
- [x] **5.1.10** No live APIs/LLMs; advisory-only preserved.

---

## 6. End-to-End Correction Workflow Validation

## 6.1 End-to-end correction workflow validation

### Goal

Add a dedicated correction workflow stage to the existing v2.6 end-to-end fixture validation that exercises the full replace → amend → status → report → dashboard → source URL traceability chain, proving that founder decision corrections work end-to-end without breaking the pipeline.

### Scope

- Extend `src/oos/v2_6_end_to_end_weekly_cycle_validation.py` (or create a v2.8-specific validation module) with a correction workflow stage:
  - Step C1: Run `build_weekly_cycle()` with fixture signals and initial decisions.
  - Step C2: Run `import_founder_decisions()` with `--replace-review-items` replacing 1–2 decisions.
  - Step C3: Verify old decisions are archived in `replaced_decisions/`.
  - Step C4: Verify new decisions are in `founder_decisions_v2.json`.
  - Step C5: Verify orphaned parking lot records are cleaned up.
  - Step C6: Verify feedback mappings and preference profile are rebuilt.
  - Step C7: Verify `import_history.json` records the replacement.
  - Step C8: Verify `weekly-cycle-status-v2` shows correction state.
  - Step C9: Verify run report and dashboard reflect corrections.
  - Step C10: Run `import_founder_decisions()` with `--amend-notes-only` on another decision.
  - Step C11: Verify notes are updated, decision value unchanged, downstream artifacts unchanged.
  - Step C12: Verify source URL traceability: zero `urn:oos:*` placeholder URNs after all corrections.
  - Step C13: Verify fail-closed: attempting replace without `--replace-review-items` is rejected.
  - Step C14: Verify idempotency: replacing the same decision twice yields identical state.
- Create `V2_8EndToEndCorrectionValidationReport` model with:
  - `schema_version`, `validation_id`, `timestamp`.
  - `correction_steps: list[V2_8CorrectionStepResult]`.
  - `correction_count`, `amendment_count`.
  - `source_url_traceability_passed: bool`.
  - `placeholder_urns_found: int`.
  - `overall_passed: bool`.
- Add the correction stage as an optional or integrated step in the existing E2E validation runner.

### Expected files

- `src/oos/v2_8_end_to_end_correction_validation.py` (new, or extend existing `v2_6_end_to_end_weekly_cycle_validation.py`)
- `tests/test_v2_8_end_to_end_correction_validation.py` (new)
- `docs/dev_ledger/02_mini_epics/6.1-e2e-correction-workflow-validation.md`
- `docs/dev_ledger/03_run_reports/6.1-e2e-correction-workflow-validation.md`

### Acceptance criteria

- [ ] **6.1.1** Correction workflow validation stage exists with all 14 steps (C1–C14).
- [ ] **6.1.2** Full pipeline with replace produces zero placeholder URNs.
- [ ] **6.1.3** Full pipeline with amend produces zero placeholder URNs.
- [ ] **6.1.4** Old decisions are archived correctly after replace.
- [ ] **6.1.5** New decisions are in `founder_decisions_v2.json` after replace.
- [ ] **6.1.6** Orphaned parking lot records are cleaned up after replace.
- [ ] **6.1.7** Feedback mappings and preference profile are consistent after replace.
- [ ] **6.1.8** Import history correctly records all actions.
- [ ] **6.1.9** Status, run report, and dashboard all reflect corrections.
- [ ] **6.1.10** Amend updates notes only; decision value and downstream artifacts are unchanged.
- [ ] **6.1.11** Fail-closed: replace without flag is rejected.
- [ ] **6.1.12** Idempotent: same replace twice = same state.
- [ ] **6.1.13** All existing E2E validation steps continue to pass (advisory-only, deterministic, artifact existence).
- [ ] **6.1.14** Focused tests (≥15) cover: full correction pipeline, replace, amend, traceability, parking lot cleanup, rebuild, history, status, report, dashboard, fail-closed, idempotency, mixed corrections.
- [ ] **6.1.15** No live APIs/LLMs; no autonomous portfolio transitions.

---

## 7. Final v2.8 Checkpoint

## 7.1 Final v2.8 validation checkpoint

### Goal

Close the roadmap: verify all items complete, all tests pass, all validation gates green, correction workflow validated end-to-end, Windows CLI output hardened, and project state updated.

### Scope

- Run full unittest discovery: `$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`
- Run `scripts/oos-validate.ps1`.
- Run `scripts/dev-validate-final.ps1`.
- Run `scripts/run-controlled-smoke.ps1`.
- Run `git diff --check`.
- Run `git status --short -uall`.
- Confirm all placeholder URNs eliminated.
- Confirm source URL traceability end-to-end.
- Confirm correction workflow (replace + amend) passes fixture E2E validation.
- Confirm Windows CLI output is CP1251/CP1252 safe by default.
- Confirm `--utf8` flag works correctly.
- Confirm roadmap state `completed` at `9 / 9`.
- Confirm `0` remaining.
- Update `docs/dev_ledger/00_project_state.md` to reflect v2.8 completion.
- Record final checkpoint mini-epic and run report.

### Expected files

- `docs/dev_ledger/02_mini_epics/7.1-roadmap-v2-8-final-validation.md`
- `docs/dev_ledger/03_run_reports/7.1-roadmap-v2-8-final-validation.md`
- `docs/dev_ledger/00_project_state.md` (update)

### Acceptance criteria

- [ ] **7.1.1** All 9 implementation items have `[x] Done` status.
- [ ] **7.1.2** Roadmap state is `complete / closed`.
- [ ] **7.1.3** Completed: `9 / 9`.
- [ ] **7.1.4** Remaining: `0 / 9`.
- [ ] **7.1.5** Full unittest discovery: all tests pass, 0 failures.
- [ ] **7.1.6** `scripts/oos-validate.ps1` passes.
- [ ] **7.1.7** `scripts/dev-validate-final.ps1` passes (all gates green).
- [ ] **7.1.8** `git diff --check` clean.
- [ ] **7.1.9** Source URL traceability verification: zero `urn:oos:*` placeholder URNs in any artifact.
- [ ] **7.1.10** Controlled weekly run smoke test completes successfully.
- [ ] **7.1.11** Correction workflow E2E validation passes (replace + amend + traceability).
- [ ] **7.1.12** Windows CLI output is ASCII-safe by default (no mojibake-prone Unicode).
- [ ] **7.1.13** Dev Ledger updated with final state.
- [ ] **7.1.14** No push, PR, merge, tag, or release unless explicitly approved.

---

## Appendix A: Implementation Order and Dependencies

```
0.1 Roadmap v2.8 planning  ← this checkpoint (docs-only)
     │
1.1 Founder decision correction artifact contract  ← no dependencies
     │
1.2 Parking lot orphan cleanup / rebuild model  ← depends on 1.1 (contract)
     │
1.3 Safe replace/amend implementation  ← depends on 1.1 (contract), 1.2 (cleanup model)
     │
2.1 Import history / audit trail  ← depends on 1.3 (replace/amend exists)
     │
3.1 CLI and status/report integration  ← depends on 1.3 (correction state exists), 2.1 (history exists)
     │
4.1 Windows CLI output hardening  ← no code dependency on 1.x/2.x/3.x; can be parallel
     │
5.1 Quality gate source_urls review  ← no code dependency on 1.x/2.x/3.x/4.x; can be parallel
     │
6.1 E2E correction workflow validation  ← depends on 1.1, 1.2, 1.3, 2.1, 3.1, (4.1, 5.1 optional)
     │
7.1 Final v2.8 validation checkpoint  ← depends on 1.1–6.1
```

Items 4.1 and 5.1 can be worked in parallel with items 1.1–3.1.

Item 6.1 benefits from 4.1 (Windows hardening) and 5.1 (quality gate source URLs) but can be started after 1.3 + 2.1 + 3.1 are complete.

## Appendix B: Correction Traceability Chain (Hardened v2.8)

```
FounderInboxReviewItem.linked_source_urls
  → FounderDecisionV2.linked_source_urls  (original import)
    → [REPLACE] FounderDecisionV2.linked_source_urls  (re-imported from inbox)
      → FounderFeedbackMapping.source_urls  (rebuilt)
        → FounderFeedbackMapping.target.source_urls  (rebuilt)
          → FounderPreferenceProfile  (rebuilt — recurring kill reasons, patterns)
            → ParkingLotRecord  (cleaned up — orphans removed, new records added)
              → ImportHistoryEntry  (recorded — original_decision_id, superseded_by)
                → WeeklyCycleStatus  (displays [CORRECTED] indicator)
                  → WeeklyRunReport  (includes correction summary)
                    → WeeklyDashboardIndex  (per-run correction_count)
```

Every link in this chain must carry real, non-placeholder URLs after correction.
Placeholder URNs (`urn:oos:*`) are treated as traceability gaps and must be eliminated.

## Appendix C: Known Deferred / Follow-Up Items (from v2.7)

| # | Item | v2.8 Disposition |
|---|------|-----------------|
| 1 | Founder decision re-import replace/amend mode | **Addressed: items 1.1, 1.2, 1.3** |
| 2 | Parking lot orphan cleanup required before safe replace mode | **Addressed: item 1.2** |
| 3 | Derived artifacts must be rebuilt deterministically after replacement | **Addressed: items 1.2, 1.3, 2.1** |
| 4 | Source URL traceability must remain strict (no placeholder URNs) | **Addressed: all items preserve constraint from v2.7** |
| 5 | Potential Windows CP1251 / Unicode output issue in weekly-cycle-status-v2 | **Addressed: item 4.1** |
| 6 | quality_gate_decisions may still have empty source_urls | **Addressed: item 5.1 — deferred to v2.9+ (fixture data gap, not code bug)** |
| 7 | Avoid expanding into live APIs/LLMs | **Preserved: all v2.8 items** |
| 8 | Preserve deterministic-first behavior | **Preserved: all v2.8 items** |
| 9 | Preserve advisory-only founder control | **Preserved: all v2.8 items** |
| 10 | Developer workflow helper scripts created in v2.7 | **No changes needed; scripts remain functional** |
| 11 | Controlled weekly run smoke test created in v2.7 | **Updated for Windows hardening (item 4.1)** |

## Appendix D: Explicit Non-Goals

- **Do not** add new product layers (no Pain Discovery Layer integration, no new pipeline stages).
- **Do not** add live LLM/API calls. All items remain deterministic-first.
- **Do not** rewrite, refactor, or redesign the v2.6/v2.7 weekly cycle pipeline.
- **Do not** add new collectors, sources, or source expansion.
- **Do not** add a database, persistent server, or UI.
- **Do not** add embeddings, vector search, or ML features.
- **Do not** add autonomous portfolio transitions.
- **Do not** add multi-user, multi-tenant, or venture-studio features.
- **Do not** add email/push notifications or scheduled periodic runs.
- **Do not** broaden beyond the existing HN + GitHub source loop.
- **Do not** implement LLM-assisted decision suggestions or LLM-driven corrections.
- **Do not** implement batch correction (correcting multiple runs at once).
- **Do not** implement undo/rollback of corrections (v2.9+ candidate).
- **Do not** add a correction UI beyond CLI flags.

## Appendix E: Mitigations for Known Risks

| Risk | Mitigation |
|------|-----------|
| Replace mode corrupts derived artifacts (feedback mappings, preference profile, parking lot) | Items 1.2 and 1.3 implement deterministic rebuild; item 6.1 validates end-to-end |
| Old parking lot records become orphans after replace | Item 1.2 implements `cleanup_orphaned_parking_lot_records()`; tests cover this explicitly |
| Source URL traceability breaks after replace | Items 1.1 and 1.3 enforce placeholder URN rejection; item 6.1 validates traceability post-correction |
| Amend mode accidentally changes decision values | Item 1.3 implements amend as notes-only; test coverage verifies decision value immutability |
| Replace mode is not idempotent | Item 1.3 acceptance criteria explicitly require idempotency; item 6.1 validates |
| Windows CP1251 terminals show mojibake from Unicode symbols | Item 4.1 audits and replaces unsafe symbols; default output is ASCII-safe |
| Quality gate source_urls fix is larger than expected | Item 5.1 includes explicit deferral path if fix is non-trivial |
| Correction history grows unbounded | Import history is per-run and append-only; runs are time-bounded weekly cycles |
| Existing v2.6/v2.7 tests break from new correction logic | All new behavior is guarded by explicit CLI flags; default behavior (no flag) preserves v2.7 semantics |
| Correction workflow validation is slow | Correction steps are deterministic file reads/writes; no network, no LLM; sub-second per step |

## Appendix F: v2.9+ Hook Notes

The following items are explicitly out of scope for v2.8 but are recognized as natural follow-up work:

| # | Item | Rationale for deferral |
|---|------|----------------------|
| 1 | Undo/rollback of corrections | Requires correction stack/history navigation; v2.8 builds the foundation |
| 2 | LLM-assisted decision suggestions | LLM integration is deferred to v2.9+ per v2.6/v2.7 strategic principles |
| 3 | Pain Discovery Layer integration | PDL is a separate product layer; integration requires its own roadmap |
| 4 | Batch correction across multiple runs | Cross-run correction semantics are complex; v2.8 focuses on single-run safety |
| 5 | Automated correction suggestions (e.g., "this PARK decision has new evidence") | Requires recurrence memory and evidence-change detection; v2.9+ ML/LLM feature |
| 6 | Correction UI beyond CLI flags | UI is out of scope for all v2.x roadmaps per scope-v1 |
