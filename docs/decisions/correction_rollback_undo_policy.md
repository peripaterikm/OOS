# Correction Rollback / Undo Policy

**Roadmap:** v2.9 item 3.1 — Policy Review
**Date:** 2026-05-10
**Status:** complete (policy review only; implementation deferred to v2.10+)
**Decision:** Defer correction rollback/undo to v2.10+

---

## 1. Purpose

This document evaluates whether rollback/undo of founder decision corrections belongs in OOS and defines a safe future policy if it does. The review is policy-only; no implementation is performed in v2.9.

The recommendation is **deferral** because rollback/undo is non-trivial (estimated >150 lines, new module, multi-artifact surgery) and the existing `--replace-review-items` mode provides an adequate safety net for the v2.9 scope.

---

## 2. Current Correction Capabilities (v2.8 delivered)

### 2.1 Correction modes

| Mode | CLI Flag | Behavior | Artifact Impact |
|------|----------|----------|----------------|
| Reject-on-reimport | (default) | Re-import of any decided opportunity is rejected | None |
| Replace-review-items | `--replace-review-items <rids>` | Surgical replacement of listed `review_item_id` values; old decisions archived to `replaced_decisions/` | Full derived artifact rebuild |
| Amend-notes-only | `--amend-notes-only <rids>` | Update `notes` and optionally `reason_categories`; decision value unchanged | In-place notes update only; no rebuild |
| Replace-all | `--replace-all` | Replace ALL existing decisions (documented in contract Section 4.4, not implemented) | N/A (deferred) |

### 2.2 Audit and archive infrastructure

| Artifact | Purpose | Write Policy |
|----------|---------|-------------|
| `import_history.json` | Append-only audit log of all correction operations | Each replace/amend appends one `CorrectionEntry`; entries are never modified or deleted |
| `replaced_decisions/` | Archive directory for pre-replacement decisions | Written on replace; contains `founder_decisions_v2_replaced_{timestamp}.json` with old decision data |
| `amended_decisions/` | Archive directory for pre-amendment notes | Written on amend; contains `founder_decisions_v2_amended_{timestamp}.json` with old notes |
| `manifest.json` | Run metadata | Records `replaced_decision_ids`, `amended_decision_ids`, and timestamps |

### 2.3 `CorrectionEntry` model (from [`founder_decision_import.py`](../../src/oos/founder_decision_import.py:134-159))

Each entry records:
- `correction_id` — deterministic SHA-256 hash
- `corrected_at` — ISO 8601 UTC timestamp
- `correction_mode` — `"replace"` or `"amend"`
- `replaced_review_item_ids` — source `review_item_id` values
- `old_decision_ids` / `new_decision_ids` — decision IDs before/after
- `old_artifact_checksums` / `new_artifact_checksums` — SHA-256 hashes
- `warnings`, `errors`
- Safety flags: `advisory_only=True`, `no_live_api=True`, `no_live_llm=True`

### 2.4 Practical workaround available

If a founder makes a wrong correction, the existing `--replace-review-items` mode can be used to issue another replacement with the original decisions. This is the practical undo mechanism available in v2.8/v2.9 without a dedicated rollback feature.

---

## 3. Definitions

### 3.1 `replace`

**What:** The founder provides a new decision for a `review_item_id` that already has a decision. The old decision is archived to `replaced_decisions/` and the new decision replaces it. All derived artifacts (feedback mappings, preference profile, parking lot records, run report, dashboard) are rebuilt.

**Scope:** One or more `review_item_id` values, explicitly listed by the founder.

**Direction:** Forward — old → new.

**Audit:** One `CorrectionEntry` appended to `import_history.json`.

### 3.2 `amend`

**What:** The founder updates only the `notes` (and optionally `reason_categories`) of an existing decision. The decision value is unchanged. No derived artifacts are rebuilt. The old notes are archived to `amended_decisions/`.

**Scope:** One or more `review_item_id` values, explicitly listed by the founder.

**Direction:** In-place mutation of notes only.

**Audit:** One `CorrectionEntry` appended to `import_history.json`.

### 3.3 `rollback`

**What:** Reverting a correction operation by restoring the pre-correction artifact state from the archive. This is the general concept; it differs from undo (Section 3.4) in that rollback could theoretically target any correction in the history, not just the most recent one.

**Scope (candidate):** One `correction_id`, one `review_item_id`, the last correction only, or an entire run.

**Direction:** Backward — new → old.

**Risk:** Higher than undo because navigating non-last corrections requires understanding interleaved artifact mutations.

### 3.4 `undo last correction`

**What:** A specific, narrow form of rollback: restore the most recent correction entry in `import_history.json`. If the last correction was a replace, restore the replaced decisions from `replaced_decisions/`. If the last correction was an amend, restore the old notes from `amended_decisions/`.

**Scope:** Exactly one `CorrectionEntry` — the most recent one.

**Direction:** Backward — reverts the most recent correction.

**Risk:** Lower than general rollback because only the tail of the correction stack is touched.

### 3.5 `restore archived decision`

**What:** Copy an archived decision from `replaced_decisions/` or `amended_decisions/` back into `founder_decisions_v2.json` without rebuilding derived artifacts. This is a manual, founder-initiated operation.

**Scope:** One `decision_id`.

**Direction:** Archive → active.

**Risk:** Moderate — requires the founder to understand which decisions were archived and why.

---

## 4. Artifact Dependency Analysis

### 4.1 Artifacts that rollback/undo would need to touch

The artifact dependency graph from the [correction artifact contract](../contracts/founder_decision_correction_artifact_contract.md) Section 5 shows the following artifacts are in scope for any correction operation. An undo would need to touch the same set:

| # | Artifact | Classification | Undo would need to |
|---|----------|---------------|-------------------|
| 1 | `founder_decisions_v2.json` | Primary | Restore old decisions, remove replacement decisions |
| 2 | `founder_feedback_mappings.json` | Derived | Full rebuild from restored decisions |
| 3 | `founder_preference_profile.json` | Derived | Full rebuild from restored decisions + mappings |
| 4 | `parking_lot_records.json` | Derived | Orphan cleanup + rebuild from restored decisions |
| 5 | `manifest.json` | Metadata | Record `undone_decision_ids` and undo timestamp |
| 6 | `run_report.json` / `run_report.md` | Derived | Regenerate with undo summary |
| 7 | `dashboard_index.json` / `dashboard.md` | Derived | Regenerate with undo indicator |
| 8 | `import_history.json` | Audit | Append new `CorrectionEntry` with `correction_mode = "undo"` |
| 9 | `replaced_decisions/` | Archive | Read old decisions from archive |
| 10 | `amended_decisions/` | Archive | Read old notes from archive (if undoing amend) |

### 4.2 What is NOT needed in a snapshot for undo-last

The `replaced_decisions/` archive already stores replaced `FounderDecisionV2` objects. However, it does NOT store:
- The full `parking_lot_records.json` state at time of correction
- The full `founder_feedback_mappings.json` state at time of correction
- The full `founder_preference_profile.json` state at time of correction

But this is acceptable because these derived artifacts can be **rebuilt deterministically** from restored decisions. The rebuild path is identical to the one used by replace mode today.

### 4.3 Dependency chain for undo-last

```
import_history.json                (read — find latest CorrectionEntry)
        │
        ├── old_decision_ids       (identify what to restore)
        ├── new_decision_ids       (identify what to remove)
        ├── correction_mode        (replace vs amend)
        │
replaced_decisions/                (read — old decisions for replace undo)
amended_decisions/                 (read — old notes for amend undo)
        │
        ▼
founder_decisions_v2.json          (WRITE — merge restored decisions)
        │
        ├──► founder_feedback_mappings.json      (REBUILD)
        │         │
        │         ▼
        ├──► founder_preference_profile.json     (REBUILD)
        │
        ├──► parking_lot_records.json            (CLEANUP + REBUILD)
        │
        ├──► manifest.json                       (UPDATE)
        │
        ├──► run_report.json / run_report.md     (REGENERATE)
        │
        └──► dashboard_index.json / dashboard.md (REGENERATE)

import_history.json                (APPEND — undo CorrectionEntry)
```

This is structurally identical to the replace-mode write path but reverses the direction: old decisions become active, replacement decisions are removed.

---

## 5. Candidate Rollback Modes

### 5.1 Mode U1: `--undo-last` (undo most recent correction)

**Trigger:** `--undo-last` flag on `import-founder-decisions-v2`

**Behavior:**
1. Read `import_history.json` — find the most recent `CorrectionEntry` by `corrected_at`.
2. If `correction_mode == "replace"`:
   - Read old decisions from `replaced_decisions/` archive matching `old_decision_ids`.
   - Remove decisions with `new_decision_ids` from `founder_decisions_v2.json`.
   - Insert restored decisions.
   - Rebuild all derived artifacts (same order as replace mode).
3. If `correction_mode == "amend"`:
   - Read old notes from `amended_decisions/` archive.
   - Restore old notes to the decision in `founder_decisions_v2.json`.
   - No derived artifact rebuild needed.
4. Append new `CorrectionEntry` with `correction_mode = "undo"`.
5. Update manifest with `undone_decision_ids` and `undone_at`.
6. Regenerate run report and dashboard.

**Safety properties:** All mandatory properties apply (Section 7).

**Estimated scope:** ~200 lines, 3 files (`src/oos/correction_undo.py` new, `src/oos/cli.py` modify, `src/oos/founder_decision_import.py` modify), 15+ tests.

**Verdict:** NOT trivial. Exceeds "≤50 lines, ≤1 file" threshold. Exceeds "50–150 lines, ≤3 files" threshold. Classified as **non-trivial**.

### 5.2 Mode U2: `--undo-correction <correction_id>` (undo specific correction)

**Trigger:** `--undo-correction <correction_id>`

**Description:** Undo any correction in the history, not just the most recent one.

**Behavior:** As U1, but requires navigating the correction stack to find the specific entry and validating that undoing it won't create inconsistent state (e.g., undoing a correction that was itself superseded by a later correction).

**Additional complexity:**
- Correction stack navigation — must verify no later correction depends on the decision being restored.
- Cross-correction validation — if correction C1 replaced decision D, and correction C2 amended D, undoing C1 is ambiguous.

**Verdict:** NOT safe for v2.9 or likely even v2.10. Requires formal correction graph analysis.

### 5.3 Mode U3: `--undo-run <run_id>` (restore entire run from archive)

**Trigger:** `--undo-run <run_id>`

**Description:** Restore the entire `founder_decisions_v2.json` and all derived artifacts to the state before any corrections were applied to a run.

**Behavior:** Requires a full pre-correction snapshot of all artifacts, which does not currently exist.

**Verdict:** NOT feasible without pre-correction snapshots. Not recommended for v2.9+.

### 5.4 Mode U4: `--restore-archived <decision_id>` (manual restore)

**Trigger:** `--restore-archived <decision_id>`

**Description:** Founder manually specifies a `decision_id` from the archive to restore. Does not rebuild derived artifacts.

**Behavior:** Simple copy from archive to active. The founder is responsible for consistency.

**Verdict:** Trivially small (~30 lines), but error-prone. Does not solve the core undo use case because the founder must know which `decision_id` to restore and must manually clean up.

---

## 6. Risk Analysis

### 6.1 What could go wrong with undo

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Partial undo writes** | Medium | High — inconsistent artifact state | All-or-nothing write policy; same atomic-ish write-then-rename pattern as replace mode |
| **Undo restores decision with stale source URLs** | Low | High — traceability contract violation | Source URL traceability check must pass after undo |
| **Undo creates orphaned parking lot records** | Medium | Medium — dangling references | Same orphan cleanup logic as replace mode |
| **Undo after amend restores notes but feedback mappings reference amended notes** | Low | Low — amend does not rebuild derived artifacts | Amend undo is notes-only; no derived artifact inconsistency |
| **Undo of non-last correction creates ambiguous state** | High (for U2) | High — inconsistent decision set | Only U1 (undo-last) is considered safe |
| **Archive file missing or corrupted** | Low | High — cannot restore | Fail-closed; if archive cannot be read, undo is rejected |
| **Multiple rapid corrections lose track of which archive to read** | Medium | Medium — wrong decisions restored | `import_history.json` `old_artifact_checksums` provide integrity verification |
| **Undo is triggered accidentally** | Low | High — unintended state change | Explicit CLI flag required; fail-closed |

### 6.2 Edge cases

1. **Undo when `import_history.json` is empty or missing.** Reject with clear error: "No corrections to undo."
2. **Undo when `replaced_decisions/` archive is missing.** Reject: "Archive not found — cannot restore pre-correction state."
3. **Undo when the most recent correction was an amend.** Restore old notes; no rebuild needed.
4. **Undo when the most recent correction was a replace of a PARK decision.** Restore the PARK decision; rebuild parking lot records (new PARK record created).
5. **Undo when the most recent correction was a replace that PROMOTEd a PARKed decision.** Restore the PARK decision; remove the PROMOTE parking lot record (orphan cleanup).
6. **Undo when multiple corrections exist but only the last is undone.** Other corrections are untouched; the audit trail records the undo.

### 6.3 Risk comparison: undo vs re-replace

| | `--undo-last` | Re-issue `--replace-review-items` |
|---|---|---|
| Automation | Automated from audit trail | Founder must manually identify and provide old decisions |
| Safety | Code path must handle edge cases | Founder controls exact input |
| Audit trail | Appends "undo" entry | Appends another "replace" entry |
| Implementation cost | ~200 lines, new module | Zero (already exists) |
| Error risk | Medium (code bugs) | Medium (founder error) |

The re-replace workaround is adequate for v2.9. Undo adds automation but also adds a new code path to maintain and test.

---

## 7. Required Safety Properties

If rollback/undo is implemented, it MUST satisfy ALL of the following:

| # | Requirement | Rationale |
|---|-------------|----------|
| **U-R1** | **Explicit CLI flag required.** E.g., `--undo-last`. No implicit undo. | Prevents accidental state reversion. |
| **U-R2** | **Fail-closed.** If any validation step fails, no artifacts are written. | Preserves existing fail-closed contract. |
| **U-R3** | **All-or-nothing.** Undo either fully succeeds or fully fails. No partial state. | Consistency with replace/amend semantics. |
| **U-R4** | **Append-only audit.** Every undo operation appends a new `CorrectionEntry` with `correction_mode = "undo"`. Existing entries are never modified or deleted. | The audit trail must record every state mutation. |
| **U-R5** | **No silent deletion.** Old decisions are always archived. Undoing a correction does not delete the correction entry — it appends a new undo entry. | The history must be fully reconstructable. |
| **U-R6** | **No portfolio mutation.** `advisory_only=True` throughout. | Founder-control boundary preserved. |
| **U-R7** | **No autonomous inference.** The system must not guess which correction to undo or which decisions to restore. | Explicit founder intent only. |
| **U-R8** | **Source URL traceability preserved.** After undo, every `FounderDecisionV2.linked_source_urls` must contain real `http`/`https` URLs. Zero `urn:oos:*` placeholders. | Must satisfy the source URL traceability contract. |
| **U-R9** | **Deterministic.** Undoing the same correction twice with the same state yields identical artifact state. | Predictability and testability. |
| **U-R10** | **Undo-last only (single-step).** Only the most recent correction can be undone. Multi-step undo is v2.11+. | Prevents correction-stack navigation complexity. |
| **U-R11** | **Derived artifacts rebuilt.** After undo, feedback mappings, preference profile, and parking lot records must be consistent with restored decisions. | No stale derived artifacts. |
| **U-R12** | **Archive integrity verified.** Before restoring from `replaced_decisions/`, the archive file must exist and be parseable. If not, undo is rejected. | No silent restore from corrupted archive. |

---

## 8. Decision

### FINAL DECISION: DEFER to v2.10+

**Rationale:**

1. **Rollback/undo is non-trivial.** Even the narrowest form (undo-last) requires:
   - A new `correction_undo.py` module (~100 lines for logic + models)
   - Modification to `cli.py` (~15 lines for `--undo-last` flag)
   - Integration with `founder_decision_import.py` (~30 lines for undo history append)
   - A new test file `test_correction_undo.py` (~20 tests, ~150 lines)
   - Total estimate: ~200 source lines, 4 files — clearly non-trivial.

2. **The existing re-replace workaround is adequate for v2.9.** A founder who makes a wrong correction can issue another `--replace-review-items` with the original decisions. This is founder-controlled, uses the existing code path, and appends a clear audit entry.

3. **The audit trail already provides undo-readiness.** `import_history.json` and `replaced_decisions/` capture everything needed for undo. The foundation is solid. The implementation gap is in the navigation and safe-write logic, not in missing data.

4. **v2.9 is a deferred-item-closure roadmap.** Adding a new correction mode (undo) crosses into feature expansion territory. The roadmap's strategic principles state: "This is deferred-item closure + operational polish, not feature expansion."

5. **The policy review itself has value.** This document records safety requirements (U-R1 through U-R12), defines the undo semantics precisely, and provides a concrete implementation plan for v2.10+.

6. **Pre-correction snapshots may be needed for robust undo.** Currently, only replaced decisions are archived — not the full artifact state. While derived artifacts can be rebuilt, a full pre-correction snapshot would make undo simpler and safer. This is a v2.10 design consideration.

---

## 9. Recommended Future Implementation Plan (v2.10+)

### 9.1 Pre-conditions for v2.10 implementation

1. All v2.9 items are complete and validated.
2. The correction workflow E2E validation (v2.8 C1–C14) passes without undo.
3. The replace/amend path has been exercised in at least one real run (not just fixture).
4. A concrete need for undo has been demonstrated (founder feedback, not hypothetical).

### 9.2 Target mode: U1 (`--undo-last`) only

Multi-step undo (U2) and run-level undo (U3) are explicitly NOT recommended for v2.10. They require correction-stack navigation and pre-correction snapshots, respectively, which are complex design problems in their own right.

### 9.3 Implementation scope (v2.10 estimate)

| File | Change |
|------|--------|
| `src/oos/correction_undo.py` (new) | `UndoResult` model, `undo_last_correction()` function — reads `import_history.json`, identifies last entry, reads archive, restores decisions, rebuilds derived artifacts |
| `src/oos/cli.py` (modify) | Add `--undo-last` flag to `import-founder-decisions-v2` subcommand |
| `src/oos/founder_decision_import.py` (modify) | Expose `read_import_history()` and `_write_import_history()` for undo path; or call undo logic directly |
| `tests/test_correction_undo.py` (new) | 20+ tests: undo replace, undo amend, undo with empty history, undo with missing archive, undo with multiple corrections, undo idempotency, undo source URL traceability, undo parking lot consistency, undo fail-closed, undo advisory flags |
| `docs/decisions/correction_rollback_undo_policy.md` (update) | Mark as implemented at v2.10; update with actual implementation details |

### 9.4 Design pre-work for v2.10

Before implementing undo, the following design decisions should be addressed:

1. **Pre-correction snapshot.** Should a full artifact snapshot be taken before each correction? This would simplify undo but increase storage. The current `replaced_decisions/` archive is adequate for undo-last but fragile for edge cases (e.g., if the archive is accidentally deleted).

2. **Undo entry in `CorrectionEntry`.** The `correction_mode` field should accept `"undo"` as a valid value. The `CorrectionEntry` model already supports this (it's a free-form `str`), but [validation tests](../../tests/test_founder_decision_import_v2.py) may need updating.

3. **CLI output for undo.** The undo result should report restored decision IDs, removed decision IDs, artifact rebuild counts, and source URL traceability pass/fail.

4. **Undo and the manifest.** The manifest should record `undone_decision_ids` and `undone_at`, similar to how it records `replaced_decision_ids` and `replaced_at`.

5. **Interaction with `--replace-all`.** If `--replace-all` is implemented in v2.9 (item 3.2), undo-last must handle the case where the last correction was a replace-all.

### 9.5 Non-implementation work for v2.10

Even if implementation is deferred, the following is recommended in v2.10:

- Add a `--show-history` flag to `weekly-cycle-status-v2` that renders the correction history in a human-readable Markdown section, including undo instructions.
- Document the re-replace workaround in the weekly run smoke test runbook as the recommended correction-recovery path.

---

## 10. Non-Goals

This policy review does **not**:

1. Implement rollback/undo code.
2. Modify `src/`, `tests/`, `scripts/`, `examples/`, `artifacts/`.
3. Add CLI flags.
4. Create new correction modes.
5. Change replace/amend behavior.
6. Add pre-correction snapshots.
7. Implement multi-step undo (undoing more than the last correction).
8. Implement run-level undo (restoring an entire run from archive).
9. Implement a graphical or interactive undo UI.
10. Call live APIs or LLMs.
11. Make autonomous decisions or portfolio mutations.

---

## Appendix A: Self-Audit

| Question | Answer |
|-----------|--------|
| Did this avoid implementation? | **Yes.** Policy/docs only. No `.py` files modified. |
| Did this avoid source/test changes? | **Yes.** No source or test files changed. |
| Did this review existing correction infrastructure? | **Yes.** Analyzed `import_history.json`, `replaced_decisions/`, `decision_correction_rebuild.py`, and `founder_decision_import.py`. |
| Did this define safe undo semantics? | **Yes.** Section 7 defines 12 safety requirements (U-R1 through U-R12). |
| Did this assess feasibility? | **Yes.** Classified as non-trivial (>200 lines, 4 files). |
| Did this make an explicit decision? | **Yes.** DEFER to v2.10+. |
| Did this provide a future implementation plan? | **Yes.** Section 9 provides v2.10 scope, file list, and design pre-work. |
| Did this preserve founder-control assumptions? | **Yes.** Advisory-only, explicit CLI flag, founder-initiated, no autonomous decisions. |
| Did this avoid live APIs/LLMs? | **Yes.** No network, API, or LLM calls. |
| Did this preserve source URL traceability? | **Yes.** U-R8 requires zero placeholder URNs after undo. |
| Is the recommendation aligned with roadmap principles? | **Yes.** "Correction recovery prudence" and "this is deferred-item closure, not feature expansion." |

---

## Appendix B: Comparison — Correction Modes Summary

| Mode | CLI Flag | Scope | Direction | Implemented |
|------|----------|-------|-----------|-------------|
| Reject-on-reimport | (default) | All decisions | N/A | v2.6 |
| Replace-review-items | `--replace-review-items` | Listed `review_item_id` values | Forward (old→new) | v2.8 |
| Amend-notes-only | `--amend-notes-only` | Listed `review_item_id` values | In-place (notes only) | v2.8 |
| Replace-all | `--replace-all` | All decisions in run | Forward (old→new) | Policy only (v2.9 item 3.2) |
| Undo-last | `--undo-last` | Most recent correction | Backward (new→old) | Policy only (this document) |
| Undo-specific | `--undo-correction <id>` | Specific `correction_id` | Backward (new→old) | Not recommended |
| Undo-run | `--undo-run <run_id>` | Entire run | Backward (new→old) | Not recommended |
| Restore-archived | `--restore-archived <id>` | Specific `decision_id` | Archive→active | Not recommended |
