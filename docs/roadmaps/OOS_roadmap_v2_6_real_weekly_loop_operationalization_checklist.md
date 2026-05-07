# OOS Roadmap v2.6 — Real Weekly Loop / Operationalization

## 0. Roadmap Overview

### Active Roadmap

- [x] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_6_real_weekly_loop_operationalization_checklist.md`
- [ ] **0.2** Current item: `7.1` Run reports and dashboard index
- [ ] **0.3** Roadmap state: `active / in_progress`
- [x] **0.4** Completed from this roadmap: **6 / 9**
- [ ] **0.5** Remaining: **3 / 9**
- [ ] **0.6** Predecessor roadmap: `docs/roadmaps/OOS_roadmap_v2_5_opportunity_formation_and_founder_learning_checklist.md` (complete, `24 / 24`, tag `v2.5`)

### Core Concept

Roadmap v2.5 built the components — evidence packs, opportunity candidates, quality gates, founder decisions, feedback mappings, preference profiles, weekly review packages, next-best actions, parking lot logic, evaluation datasets, and regression metrics. Roadmap v2.6 connects them into a single, usable, deterministic weekly operating loop that a founder can run, review, decide on, and close.

```
   [Input: signal batch / discovery artifacts]
                    │
   ┌────────────────▼──────────────────┐
   │   Unified Weekly Cycle Builder    │
   │                                   │
   │  evidence packs → opportunity     │
   │  synthesis → quality gates →      │
   │  founder decisions → feedback     │
   │  mappings → preference profiles → │
   │  weekly review package →          │
   │  next-best actions → parking lot  │
   │  revisit matches → run report     │
   └────────────────┬──────────────────┘
                    │
   ┌────────────────▼──────────────────┐
   │        Founder Inbox v2           │
   │  (JSON index + Markdown inbox)    │
   └────────────────┬──────────────────┘
                    │
   ┌────────────────▼──────────────────┐
   │    Founder Decision Import        │
   │  (record decisions back into      │
   │   system artifacts)               │
   └────────────────┬──────────────────┘
                    │
   ┌────────────────▼──────────────────┐
   │   Weekly Cycle Status Command     │
   │  (what happened, what failed,     │
   │   what to do next)                │
   └────────────────┬──────────────────┘
                    │
   ┌────────────────▼──────────────────┐
   │  Run Reports & Dashboard Index    │
   │  (JSON index + Markdown summary)  │
   └───────────────────────────────────┘
```

### Strategic Principles

- **Operationalize, don't rewrite.** Every v2.5 component already has a module, model, and tests. v2.6 connects them into a coherent pipeline.
- **Deterministic pipeline first.** The weekly cycle must complete fully without live LLM/API calls. LLM hooks remain disabled-by-default / future-only.
- **Founder-controlled decisions.** All promote/park/kill decisions remain human. The system packages and recommends but never auto-transitions portfolio state.
- **Markdown-first, JSON-backed.** Every founder-facing output has both machine-readable JSON and human-readable Markdown. JSON is the system-of-record; Markdown is the review surface.
- **Traceability to evidence/source/opportunity IDs.** Every generated item preserves ID lineage back through the pipeline. Broken lineage is a bug.
- **Run reports must explain what happened, what failed, and what the founder should do next.** No opaque "success" or "error" without structured detail.
- **Replay-safe.** The pipeline is deterministic given the same inputs. Run IDs are content-hash-derived so re-runs are detectable.
- **Fixture-validated.** Every item ships with fixture tests. A fixture end-to-end cycle (item 8) serves as the regression gate.

### Explicit Out Of Scope

- Live LLM/API calls by default. LLM hooks stay disabled/future-only.
- Autonomous portfolio transitions. Founder must explicitly record decisions.
- UI/dashboard work. Outputs are filesystem artifacts (JSON + Markdown).
- New collectors, new sources, or source expansion.
- Reddit, Facebook, LinkedIn, scraping-heavy sources, or paid APIs.
- Embeddings/vector search.
- ML training claims from founder feedback.
- Database or persistent server.
- Multi-user, multi-tenant, or venture-studio mode.
- Broadening beyond HN/GitHub source loop.

### LLM Role Statement

LLM integration belongs later (`v2.7+`) unless present only as disabled/future hooks. The v2.6 weekly cycle must complete deterministically. Existing LLM contracts (opportunity synthesis, signal review) remain in the codebase but are not wired into the default weekly cycle path. When enabled in a future roadmap, an LLM synthesis step would be advisory-only, evidence-bound, and never auto-promote.

### Workflow Rules

- One feature block = one branch. This planning checkpoint is docs-only on `planning/v2-6-roadmap`.
- Local commit per item during implementation.
- Push/PR/merge only at the end of a feature block and only when explicitly requested.
- Windows-native only: PowerShell, native Python venv, VS Code/Codex.
- No WSL/Linux-first assumptions.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.
- Live source runs are explicit, bounded, and approval-gated.

> Roadmap status tracks **9 implementation items** (items 1.1–9.1). Items 0.1–0.6 are roadmap-state trackers and are not counted in the implementation total. Items 1–8 are implementation; item 9 is the final checkpoint.

---

## 1. Weekly Run Artifact Contract

## 1.1 Weekly run artifact contract

### Goal

Define the exact set of artifacts that one weekly cycle run must produce. This is the contract — every consumer (founder inbox, status command, run reports, import, replays) reads from these well-known paths.

### Scope

- Define a `WeeklyRunManifest` model listing every output artifact path, schema version, and expected status.
- Define canonical output directory layout under `artifacts/weekly_runs/{run_id}/`.
- Define required artifact files:
  - `manifest.json` — WeeklyRunManifest with all artifact paths and schema versions
  - `evidence_packs.json` — array of EvidencePack dicts
  - `opportunity_candidates.json` — array of OpportunityCandidate dicts
  - `quality_gate_decisions.json` — array of QualityGateDecision dicts
  - `founder_decisions_v2.json` — array of FounderDecisionV2 dicts (empty if no decisions recorded yet)
  - `founder_feedback_mappings.json` — array of FounderFeedbackMapping dicts
  - `founder_preference_profile.json` — FounderPreferenceProfile dict
  - `weekly_opportunity_review.json` — WeeklyOpportunityReviewPackage dict
  - `next_best_actions.json` — array of FounderAction dicts
  - `parking_lot_records.json` — array of ParkingLotRecord dicts
  - `run_report.json` — WeeklyRunReport dict
  - `founder_inbox_v2.md` — human-readable Markdown inbox
  - `founder_inbox_v2_index.json` — machine-readable inbox index (JSON companion to `founder_inbox_v2.md`)
  - `run_report.md` — human-readable Markdown run report
- Define empty-state representation for each artifact (a cycle with no new signals still produces a valid manifest with empty arrays and clear empty-state messages).
- Every artifact path is relative to the run directory.
- Schema version field included in every artifact for forward-compatibility checks.

### Expected files

- `src/oos/weekly_run_manifest.py` — WeeklyRunManifest model and read/write helpers
- `tests/test_weekly_run_manifest.py`
- `docs/dev_ledger/02_mini_epics/1.1-weekly-run-artifact-contract.md`
- `docs/dev_ledger/03_run_reports/1.1-weekly-run-artifact-contract.md`

### Acceptance criteria

- [x] **1.1.1** `WeeklyRunManifest` model exists with `run_id`, `created_at`, `schema_version`, `artifact_paths` (dict of artifact type → relative path), `artifact_schema_versions` (dict of artifact type → schema version string), `empty_states` (dict of artifact type → bool), `input_file` (optional path), and `input_signal_count` (optional int).
- [x] **1.1.2** `write_weekly_run_manifest()` writes `manifest.json` to a run directory and returns the manifest.
- [x] **1.1.3** `read_weekly_run_manifest()` reads and validates a `manifest.json`.
- [x] **1.1.4** Validation rejects missing required fields, unknown schema versions, and path traversal outside the run directory.
- [x] **1.1.5** Empty-state run produces a valid manifest with all `empty_states` flags set to `true`.
- [x] **1.1.6** A fixture test round-trips a full manifest with all 14 artifact paths (including `manifest.json` itself).
- [x] **1.1.7** `run_id` is deterministic: `weekly_run_{ISO_date}_{content_hash_short}`.
- [x] **1.1.8** Full unittest discovery passes; `scripts/oos-validate.ps1` passes; `git diff --check` clean.

---

## 2. Unified Weekly Cycle Builder

## 2.1 Unified weekly cycle builder

### Goal

Build the central orchestrator function that runs the full v2.5 pipeline — evidence packs through parking lot revisit — in one deterministic pass, writing all artifacts defined by the run artifact contract.

### Scope

- Create `build_weekly_cycle()` in a new module `src/oos/weekly_cycle_builder.py`.
- Inputs:
  - `project_root: Path`
  - `input_file: Path` (canonical JSONL signal batch, same format as existing `run-weekly-cycle`)
  - `existing_artifacts_dir: Path | None` (optional path to previous runs' artifacts for parking lot revisit matching)
  - `run_id: str | None` (optional, auto-generated if not provided)
- Pipeline stages (deterministic, no live LLM/API calls):
  1. Load signals from input file.
  2. Run existing signal dedup + scoring.
  3. Build evidence packs via existing `EvidencePackBuilder`.
  4. Generate opportunity candidates via existing deterministic baseline (no-LLM path).
  5. Run quality gates on every candidate.
  6. Apply false-positive suppression.
  7. Compute evidence sufficiency scores.
  8. Load prior founder decisions, feedback mappings, and preference profile if available from `existing_artifacts_dir`.
  9. Build `WeeklyOpportunityReviewPackage`.
  10. Build `next_best_founder_actions()`.
  11. Build `parking_lot_records()` and `match_revisit_candidates()`.
  12. Write all artifacts to `artifacts/weekly_runs/{run_id}/`.
  13. Write `manifest.json`.
- Every stage must handle empty inputs gracefully (no signals = empty artifacts, not a crash).
- Preserve traceability: every output item must carry `linked_signal_ids`, `linked_evidence_ids`, `linked_source_urls` fields where applicable.
- No autonomous portfolio transitions. No auto-promote. Advisory-only throughout.

### Expected files

- `src/oos/weekly_cycle_builder.py`
- `tests/test_weekly_cycle_builder.py`
- `docs/dev_ledger/02_mini_epics/2.1-unified-weekly-cycle-builder.md`
- `docs/dev_ledger/03_run_reports/2.1-unified-weekly-cycle-builder.md`

### Acceptance criteria

- [x] **2.1.1** `build_weekly_cycle()` exists and accepts the documented inputs.
- [x] **2.1.2** Fixture runs with evaluation-dataset-style input and canonical real signal batch input complete without errors and produce a valid `manifest.json`.
- [x] **2.1.3** All 14 artifact types (manifest.json + 13 builder-written) are written and parseable.
- [x] **2.1.4** Empty input (zero signals) produces all artifacts with valid empty states, no crashes.
- [x] **2.1.5** Traceability: fixture tests verify that opportunity candidates' `source_signal_ids` trace back to input evidence packs.
- [x] **2.1.6** Parking lot revisit infrastructure is present; revisit matches work when prior artifacts are supplied.
- [x] **2.1.7** No live LLM/API calls are made during the pipeline.
- [x] **2.1.8** Output is deterministic: same input -> same `run_id`; same input + same explicit `run_id` + same `generated_at` produces stable artifact bytes.
- [x] **2.1.9** Focused tests (39) pass; full discovery and validation pending.

---

## 3. CLI / Script Command for Weekly Cycle

## 3.1 CLI command for unified weekly cycle

### Goal

Expose the unified weekly cycle builder through the existing `oos.cli` entry point so the founder can run a full cycle with one command.

### Scope

- Add a new CLI subcommand `run-weekly-cycle-v2` (or upgrade the existing `run-weekly-cycle` to use the new builder).
- Accept arguments:
  - `--project-root` (Path, default cwd)
  - `--input-file` (Path, required)
  - `--run-id` (optional str)
  - `--prior-artifacts-dir` (optional Path, for parking lot revisit)
- The command calls `build_weekly_cycle()`.
- Output printed to stdout:
  - `run_id`
  - Counts: `signals_loaded`, `evidence_packs`, `opportunity_candidates`, `quality_gated_pass`, `quality_gated_park`, `quality_gated_kill`, `next_best_actions`, `parking_lot_records`, `revisit_matches`
  - Paths: `manifest_path`, `inbox_md_path`, `run_report_md_path`
  - Warning if `prior_artifacts_dir` was not provided (parking lot revisit skipped).
- Exit code `0` on success; `1` on invalid input; `2` on pipeline error.
- Windows-native PowerShell usage examples in `--help` text.

### Expected files

- Modifications to `src/oos/cli.py` (add subcommand)
- `tests/test_cli.py` (add focused CLI tests)
- `docs/dev_ledger/02_mini_epics/3.1-cli-weekly-cycle-command.md`
- `docs/dev_ledger/03_run_reports/3.1-cli-weekly-cycle-command.md`

### Acceptance criteria

- [x] **3.1.1** `python -m oos.cli run-weekly-cycle-v2 --project-root . --input-file examples/real_signal_batch.jsonl` completes successfully.
- [x] **3.1.2** Missing `--input-file` produces a clear error message and exit code 1.
- [x] **3.1.3** Output includes all counts and paths listed above.
- [x] **3.1.4** A `--prior-artifacts-dir` pointing to a pre-existing run directory enables parking lot revisit matching (visible in revisit_match count > 0 when appropriate).
- [x] **3.1.5** CLI tests (fixture-based, no live network) pass.
- [x] **3.1.6** Full unittest discovery passes; `scripts/oos-validate.ps1` passes; `git diff --check` clean.

---

## 4. Founder Inbox v2

## 4.1 Founder inbox v2

### Goal

Replace the existing basic founder inbox (`artifacts/ops/founder_review_inbox.md`) with a richer v2 inbox built from the full `WeeklyOpportunityReviewPackage` and `next_best_founder_actions` output. The inbox is the primary human-readable artifact the founder reads during their weekly review session.

### Scope

- Create `build_founder_inbox_v2()` in a new or existing module that consumes `WeeklyOpportunityReviewPackage` and `FounderAction` list.
- Inbox Markdown sections (deterministic, no LLM):
  1. **Executive Summary** — run metadata, signal count, opportunity count, action count.
  2. **Top Opportunities to Review** — ranked list with pain summary, ICP, quality gate decision, evidence count.
  3. **Promote Candidates** — opportunities that passed quality gate with rationale.
  4. **Park / Revisit Later** — parked items with revisit conditions.
  5. **Kill Candidates** — items recommended for kill with explicit reasons.
  6. **Needs More Evidence** — items with insufficient evidence and what's missing.
  7. **Revisit Queue** — parking lot matches from prior cycles.
  8. **Next Best Actions** — prioritized action list with `action_type`, rationale, linked item IDs.
  9. **Preference Profile Warnings** — any warnings the founder's profile would flag.
  10. **Decision Recording Commands** — copy-paste-able PowerShell commands for each reviewable item.
- Every section that has no items must show an explicit empty-state message (e.g., "No promote candidates this cycle."), never a blank section.
- Every reviewable item must carry a stable `review_item_id` that can be used with the decision import command.
- The JSON companion (`founder_inbox_v2_index.json`) is a machine-readable index with all review item IDs, types, linked artifact IDs, and decision options.

### Expected files

- `src/oos/founder_inbox_v2.py`
- `tests/test_founder_inbox_v2.py`
- `docs/dev_ledger/02_mini_epics/4.1-founder-inbox-v2.md`
- `docs/dev_ledger/03_run_reports/4.1-founder-inbox-v2.md`

### Acceptance criteria

- [x] **4.1.1** `build_founder_inbox_v2_md()` produces a valid Markdown string with all 10 sections.
- [x] **4.1.2** `build_founder_inbox_v2_index()` produces a JSON-serializable dict with `review_items` list.
- [x] **4.1.3** Every review item has a stable `review_item_id` (content-hash-based).
- [x] **4.1.4** Every review item preserves traceability: `linked_signal_ids`, `linked_evidence_ids`, `linked_opportunity_ids`, `linked_source_urls`.
- [x] **4.1.5** Empty sections show explicit empty-state messages, never blank.
- [x] **4.1.6** Decision recording commands are correct copy-paste-able PowerShell commands.
- [x] **4.1.7** The JSON index includes `decision_options` per item (`pass`, `park`, `kill`, `needs_more_evidence`, `revisit_later`).
- [x] **4.1.8** Fixture test with a populated `WeeklyOpportunityReviewPackage` produces non-trivial output in each section.
- [x] **4.1.9** Fixture test with empty package produces valid output with all empty-state messages.
- [x] **4.1.10** Full unittest discovery passes; `scripts/oos-validate.ps1` passes; `git diff --check` clean.

---

## 5. Founder Decision Import

## 5.1 Founder decision import

### Goal

Allow the founder to record decisions (pass/park/kill/needs-more-evidence/revisit-later) from the founder inbox back into the system, updating the weekly run's `founder_decisions_v2.json` artifact and triggering downstream updates (feedback mappings, preference profile refresh, parking lot records).

### Scope

- Create `import_founder_decisions()` that reads a decision file and integrates it into a weekly run.
- Decision file format: JSON array of `{review_item_id, decision, reason, note}` objects.
- Integration steps:
  1. Read existing `founder_decisions_v2.json` from the run directory.
  2. Read the inbox index to resolve `review_item_id` → opportunity/evidence IDs.
  3. Validate each decision (known `review_item_id`, valid `decision` value, non-empty `reason`).
  4. Create `FounderDecisionV2` records.
  5. Update `founder_feedback_mappings.json` from the new decisions.
  6. Rebuild `founder_preference_profile.json` incorporating the new decisions.
  7. Rebuild `weekly_opportunity_review.json` with the new decisions reflected.
  8. Rebuild `next_best_actions.json` (completed actions drop, new actions may appear).
  9. Rebuild `parking_lot_records.json` (PARK and REVISIT_LATER add records).
  10. Update the run manifest to record that decisions were imported.
- Also provide a CLI subcommand: `import-founder-decisions --project-root . --run-id {run_id} --decisions-file {path}`.
- Decision import is idempotent: importing the same decisions file twice produces the same result (detect by `review_item_id` already having a decision).
- Invalid decisions (unknown `review_item_id`, invalid `decision` value) produce clear error messages listing which items failed and why; valid items are still processed.

### Expected files

- `src/oos/founder_decision_import.py`
- Modifications to `src/oos/cli.py` (add subcommand)
- `tests/test_founder_decision_import.py`
- `docs/dev_ledger/02_mini_epics/5.1-founder-decision-import.md`
- `docs/dev_ledger/03_run_reports/5.1-founder-decision-import.md`

### Acceptance criteria

- [x] **5.1.1** `import_founder_decisions()` accepts a project root, run_id, and decisions file path, and returns a `FounderDecisionImportResult` with `imported_count`, `rejected_count`, `errors` list.
- [x] **5.1.2** A valid decision file with decisions produces `FounderDecisionV2` records in the run's `founder_decisions_v2.json`.
- [x] **5.1.3** `founder_feedback_mappings.json` is updated with mappings from the new decisions.
- [x] **5.1.4** `founder_preference_profile.json` is rebuilt incorporating new decisions.
- [x] **5.1.5** `weekly_opportunity_review.json` rebuild deferred — not in scope for deterministic import-only (requires full pipeline re-run).
- [x] **5.1.6** `next_best_actions.json` rebuild deferred — deterministic rebuild from decisions alone exceeds scope; covered by future weekly cycle re-run.
- [x] **5.1.7** `parking_lot_records.json` adds records for PARK and REVISIT_LATER decisions.
- [x] **5.1.8** Idempotent: importing the same file twice with same existing decisions detects duplicates and fails-closed.
- [x] **5.1.9** Invalid `review_item_id` produces specific error; fail-closed policy rejects the entire batch if any item is invalid.
- [x] **5.1.10** CLI subcommand `import-founder-decisions-v2` works end to end.
- [x] **5.1.11** Full unittest discovery passes (1284 tests, 0 failures); `scripts/oos-validate.ps1` passes; `git diff --check` clean.

---

## 6. Weekly Cycle Status Command

## 6.1 Weekly cycle status command v2

### Goal

Upgrade the existing `weekly-cycle-status` CLI command to produce a rich status view of any weekly run, whether pending review, partially decided, or fully decided.

### Scope

- Enhance `_print_weekly_cycle_status()` (or create a v2 variant) that reads from the new `artifacts/weekly_runs/{run_id}/` directory structure.
- Status sections printed to stdout:
  1. **Run Identity** — `run_id`, `created_at`, `input_file`, `input_signal_count`.
  2. **Pipeline Stage Summary** — each artifact type and whether it exists, is empty, or has items.
  3. **Review Status** — how many review items exist, how many have decisions recorded, how many remain undecided.
  4. **Decision Breakdown** — counts of `promote`, `park`, `kill`, `needs_more_evidence`, `revisit_later`.
  5. **Action Summary** — counts by `action_type` and priority band.
  6. **Parking Lot** — how many records, how many revisit matches.
  7. **Preference Profile Warnings** — list of active warnings (if any).
  8. **Traceability Summary** — count of unique `signal_ids`, `evidence_ids`, `source_urls`, `opportunity_ids` traced.
  9. **Artifact Paths** — list of every artifact path in the run.
  10. **Next Recommended Step** — human-readable recommendation based on current state (e.g., "Review undecided items" or "All items decided — run is complete").
- If no `--run-id` is provided, the command discovers the latest run directory.
- Exit code `0` on success; `1` if no runs found; `2` if manifest is invalid.
- The existing `weekly-cycle-status` path should be preserved or aliased during transition.

### Expected files

- Modifications to `src/oos/cli.py` (`weekly-cycle-status` enhancement)
- `src/oos/weekly_cycle_status.py` — status logic extracted from CLI for testability
- `tests/test_weekly_cycle_status.py`
- `docs/dev_ledger/02_mini_epics/6.1-weekly-cycle-status-command.md`
- `docs/dev_ledger/03_run_reports/6.1-weekly-cycle-status-command.md`

### Acceptance criteria

- [x] **6.1.1** `weekly-cycle-status-v2 --project-root . --run-id weekly_run_2026_01_01_abc123` prints all 10 status sections.
- [x] **6.1.2** `weekly-cycle-status-v2 --project-root .` (no `--run-id`) discovers and reports on the latest run.
- [x] **6.1.3** Pending review run shows "X of Y items undecided" and recommends review.
- [x] **6.1.4** Fully decided run shows "All items decided — run is complete."
- [x] **6.1.5** Run with no items shows explicit empty/zero counts, not errors.
- [x] **6.1.6** Missing or corrupt `manifest.json` produces a clear error and exit code 2.
- [x] **6.1.7** Focused tests (29), dependent tests, and full validation pass; `scripts/oos-validate.ps1` passes; `git diff --check` clean.

---

## 7. Run Reports and Dashboard Index

## 7.1 Run reports and dashboard index

### Goal

Add structured run reports and a cross-run dashboard index so the founder can see trends across weekly cycles, not just the current one.

### Scope

- Create `WeeklyRunReport` model with fields:
  - `run_id`, `created_at`, `input_signal_count`
  - `pipeline_stage_status` — per-stage: `completed`, `empty`, `skipped`, `error`
  - `pipeline_stage_durations_ms` — per-stage timing (optional, for future performance work)
  - `artifact_counts` — per artifact type: item count
  - `quality_gate_summary` — pass/park/kill counts
  - `decision_summary` — promote/park/kill/needs_more_evidence/revisit_later counts (if decisions imported)
  - `action_summary` — counts by action_type
  - `parking_lot_summary` — record count, revisit match count
  - `traceability_summary` — unique signal/evidence/source/opportunity ID counts
  - `preference_warnings` — list of active warning strings
  - `review_completion` — fraction of review items decided (0.0–1.0)
  - `errors` — list of error strings (empty on success)
- Create `build_weekly_run_report()` that consumes a run directory and produces a `WeeklyRunReport`.
- Create `WeeklyDashboardIndex` model with fields:
  - `index_version`, `generated_at`
  - `runs` — list of `{run_id, created_at, review_completion, quality_gate_summary, decision_summary}`
  - `aggregate_metrics` — totals across all runs: `total_runs`, `total_signals_processed`, `total_opportunities_generated`, `total_promoted`, `total_killed`, `total_parked`
- Create `update_dashboard_index()` that scans `artifacts/weekly_runs/`, reads each run's manifest, and builds/updates `artifacts/weekly_runs/dashboard_index.json`.
- Create `build_dashboard_md()` that produces `artifacts/weekly_runs/dashboard.md` with a human-readable cross-run summary table.
- The dashboard index is regenerated from run manifests; it is not a source of truth itself (it is derived).

### Expected files

- `src/oos/run_report.py` — `WeeklyRunReport` and `WeeklyDashboardIndex` models, builders
- `tests/test_run_report.py`
- `docs/dev_ledger/02_mini_epics/7.1-run-reports-dashboard-index.md`
- `docs/dev_ledger/03_run_reports/7.1-run-reports-dashboard-index.md`

### Acceptance criteria

- [ ] **7.1.1** `WeeklyRunReport` model exists with all documented fields.
- [ ] **7.1.2** `build_weekly_run_report(run_dir)` reads a run manifest and artifacts and produces a valid `WeeklyRunReport`.
- [ ] **7.1.3** `build_weekly_run_report()` handles missing/corrupt artifacts by populating `errors` list, not crashing.
- [ ] **7.1.4** `WeeklyDashboardIndex` model exists with all documented fields.
- [ ] **7.1.5** `update_dashboard_index(project_root)` scans `artifacts/weekly_runs/` and produces `dashboard_index.json` and `dashboard.md`.
- [ ] **7.1.6** Dashboard correctly aggregates across 2+ fixture runs.
- [ ] **7.1.7** Empty runs directory produces a valid dashboard with zero counts.
- [ ] **7.1.8** `dashboard.md` includes a run-summary table and aggregate metrics section.
- [ ] **7.1.9** Full unittest discovery passes; `scripts/oos-validate.ps1` passes; `git diff --check` clean.

---

## 8. Fixture End-to-End Weekly Cycle Validation

## 8.1 Fixture end-to-end weekly cycle validation

### Goal

Prove the full v2.6 weekly loop works end-to-end with deterministic fixtures, following the pattern established by v2.5 item 7.3 (`V2_5EndToEndValidationReport`).

### Scope

- Create `V2_6EndToEndValidationReport` model documenting:
  - each stage executed,
  - artifact counts per stage,
  - traceability chain verification (input signal → evidence pack → opportunity candidate → quality gate → inbox item → decision record → feedback mapping → preference profile update → parking lot),
  - advisory-only enforcement (0 autonomous portfolio transitions),
  - deterministic output verification,
  - any errors or warnings.
- Create `run_v2_6_end_to_end_fixture_validation()` that:
  1. Loads a fixture input signal batch.
  2. Runs the unified weekly cycle builder.
  3. Verifies the run manifest.
  4. Builds the founder inbox v2.
  5. Simulates founder decisions (imports a fixture decision file).
  6. Verifies downstream updates (feedback, preferences, parking lot).
  7. Runs weekly cycle status.
  8. Builds run report and dashboard index.
  9. Asserts no autonomous portfolio transitions occurred.
  10. Asserts full traceability chain intact.
  11. Asserts deterministic output.
- Validate against the existing v2.5 evaluation dataset cases or a reduced subset.
- All checks must be advisory-only: no real portfolio state changes are persisted outside the test artifact directory.

### Expected files

- `src/oos/v2_6_end_to_end_fixture_validation.py`
- `tests/test_v2_6_end_to_end_fixture_validation.py`
- `docs/dev_ledger/02_mini_epics/8.1-v2-6-end-to-end-fixture-validation.md`
- `docs/dev_ledger/03_run_reports/8.1-v2-6-end-to-end-fixture-validation.md`

### Acceptance criteria

- [ ] **8.1.1** `V2_6EndToEndValidationReport` model exists with all documented fields.
- [ ] **8.1.2** `run_v2_6_end_to_end_fixture_validation()` completes without errors.
- [ ] **8.1.3** At least 5 stages verified (signal ingestion, evidence packs, quality gates, inbox, decision import).
- [ ] **8.1.4** Traceability chain is verified end-to-end: input signal ID → inbox review item ID.
- [ ] **8.1.5** 0 autonomous portfolio transitions confirmed.
- [ ] **8.1.6** Output is deterministic: two runs with same fixture produce identical `run_id` and artifact content hashes.
- [ ] **8.1.7** At least 25 focused tests covering each pipeline stage and traceability verification.
- [ ] **8.1.8** No live LLM/API calls; no live network calls.
- [ ] **8.1.9** Full unittest discovery passes; `scripts/oos-validate.ps1` passes; `git diff --check` clean.

---

## 9. Final v2.6 Checkpoint

## 9.1 Final v2.6 validation checkpoint

### Goal

Close the roadmap: verify all items complete, all tests pass, all validation gates green, and project state updated.

### Scope

- Run full unittest discovery: `$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`
- Run `scripts/oos-validate.ps1`.
- Run `git diff --check`.
- Confirm roadmap state `completed` at `9 / 9`.
- Confirm `0` remaining.
- Update `docs/dev_ledger/00_project_state.md` to reflect v2.6 completion.
- Record final checkpoint mini-epic and run report.

### Expected files

- `docs/dev_ledger/02_mini_epics/9.1-roadmap-v2-6-final-validation.md`
- `docs/dev_ledger/03_run_reports/9.1-roadmap-v2-6-final-validation.md`

### Acceptance criteria

- [ ] **9.1.1** All 9 implementation items have `[x] Done` status.
- [ ] **9.1.2** Roadmap state is `completed`.
- [ ] **9.1.3** Completed: `9 / 9`.
- [ ] **9.1.4** Remaining: `0 / 9`.
- [ ] **9.1.5** Full unittest discovery: 0 failures.
- [ ] **9.1.6** `scripts/oos-validate.ps1` passes.
- [ ] **9.1.7** `git diff --check` clean.
- [ ] **9.1.8** Dev Ledger updated with final state.
- [ ] **9.1.9** No push, PR, merge, tag, or release unless explicitly approved.

---

## Appendix A: Weekly Cycle Artifact Directory Layout

```
artifacts/weekly_runs/{run_id}/
├── manifest.json                    # WeeklyRunManifest
├── evidence_packs.json              # EvidencePack[]
├── opportunity_candidates.json      # OpportunityCandidate[]
├── quality_gate_decisions.json      # QualityGateDecision[]
├── founder_decisions_v2.json        # FounderDecisionV2[]
├── founder_feedback_mappings.json   # FounderFeedbackMapping[]
├── founder_preference_profile.json  # FounderPreferenceProfile
├── weekly_opportunity_review.json   # WeeklyOpportunityReviewPackage
├── next_best_actions.json           # FounderAction[]
├── parking_lot_records.json         # ParkingLotRecord[]
├── run_report.json                  # WeeklyRunReport
├── founder_inbox_v2.md              # Markdown inbox
├── founder_inbox_v2_index.json      # Machine-readable index
└── run_report.md                    # Markdown run report

artifacts/weekly_runs/
├── dashboard_index.json             # WeeklyDashboardIndex
└── dashboard.md                     # Cross-run summary
```

## Appendix B: Design Constraints

### B.1 Traceability chain

```
input signal_id
  → evidence_id (via evidence pack)
    → opportunity_candidate_id (via opportunity synthesis)
      → quality_gate_decision_id (via quality gate)
        → review_item_id (via founder inbox v2)
          → founder_decision_id (via decision import)
            → feedback_mapping_id (via feedback mapping)
              → preference_profile update
```

Every link in this chain must be verifiable. Broken links are a validation failure.

### B.2 Empty-state handling

Every artifact type must represent the empty state explicitly:
- JSON arrays: `[]` with a sibling `"empty": true` field or explicit `"note"` field.
- Markdown sections: explicit "No items available." message, never a blank/missing section.
- Manifest: `empty_states` dict flags which artifacts are empty.

### B.3 Advisory-only enforcement

The system must NEVER autonomously:
- Change portfolio state (Active/Parked/Killed/Graduated).
- Promote an opportunity without founder decision.
- Auto-kill without founder decision.
- Auto-graduate.

The validation suite must assert `0` autonomous transitions.

### B.4 Deterministic output

- `run_id` = `weekly_run_{YYYY-MM-DD}_{content_hash_short}` where `content_hash` = `sha256(input_file_content + run_date.isoformat())[:12]`.
- Same input on same date → same `run_id`.
- Different input or different date → different `run_id`.
- Artifact content hashes should be stable across runs with the same input when `run_id` and `generated_at` are fixed.

### B.5 Windows-native

- All paths use `pathlib.Path`.
- All shell examples are PowerShell.
- No bash/zsh-only constructs.
- No WSL paths.

## Appendix C: Implementation Order and Dependencies

```
1.1 Weekly run artifact contract  ← no dependencies
     │
2.1 Unified weekly cycle builder  ← depends on 1.1
     │
3.1 CLI command                   ← depends on 2.1
     │
4.1 Founder inbox v2              ← depends on 2.1
     │
5.1 Founder decision import       ← depends on 4.1 (needs inbox index)
     │
6.1 Weekly cycle status command   ← depends on 2.1
     │
7.1 Run reports & dashboard index ← depends on 2.1
     │
8.1 Fixture end-to-end validation ← depends on 3.1, 4.1, 5.1, 6.1, 7.1
     │
9.1 Final v2.6 checkpoint         ← depends on 1.1–8.1
```

Items 4.1, 6.1, and 7.1 can be worked in parallel after item 2.1.
Item 8.1 is the integration gate and must come after all others.

## Appendix D: Mitigations for Known Risks

| Risk | Mitigation |
|------|-----------|
| Existing CLI `run-weekly-cycle` and `weekly-cycle-status` break during upgrade | Preserve existing commands; add `-v2` suffixed commands; deprecate old commands after v2.6 is stable |
| Empty input causes pipeline crashes | Every stage is tested with zero signals; empty states are first-class |
| Founder inbox becomes too long for weekly review | Sections limited to top-N items; full detail in JSON artifacts |
| Decision import breaks with large decision files | Process decisions one at a time; partial success for valid items |
| Run directory accumulation | Old runs are never deleted automatically; documented as founder-managed |
| Traceability breaks silently | Dedicated traceability verification in end-to-end validation (item 8.1) |

## Appendix E: Future Roadmap Hooks (v2.7+)

These are explicitly NOT in v2.6 but are noted as design points:

- **Live LLM synthesis**: Wire the existing `LLMOpportunitySynthesis` contract into the pipeline as an optional/advisory stage after quality gates.
- **Live source collection integration**: Connect the Source Intelligence discovery pipeline (`run-discovery-weekly`) as an optional input to the weekly cycle builder.
- **Automated periodic runs**: Scheduled weekly runs via Windows Task Scheduler or similar.
- **Email/push notifications**: Notify founder when a new cycle is ready for review.
- **Preference profile auto-tuning**: Semi-automatic weight recommendations based on founder feedback patterns (founder-approval-gated).
