# Replace-All Mode Policy

**Roadmap:** v2.9 item 3.2 — Policy Review
**Date:** 2026-05-10
**Status:** complete (policy review only; implementation deferred to v2.10+)
**Decision:** Defer `--replace-all` correction mode to v2.10+

---

## 1. Purpose

This document evaluates whether a broad `--replace-all` correction mode belongs in OOS and defines a safe future policy if it does. The review is policy-only; no implementation is performed in v2.9.

The recommendation is **deferral** because `--replace-all` is coarse, violates the safety requirement R8 (no silent deletion of unrelated decisions), has no demonstrated real-run need, and the existing `--replace-review-items` mode plus the "re-run the weekly cycle" workaround provide adequate correction flexibility for the v2.9 scope.

---

## 2. Current Correction Modes (v2.8 delivered)

### 2.1 Mode summary

| Mode | CLI Flag | Scope | Implemented |
|------|----------|-------|-------------|
| Reject-on-reimport | (default) | All decisions | v2.6 |
| Replace-review-items | `--replace-review-items <rids>` | Listed `review_item_id` values only | v2.8 |
| Amend-notes-only | `--amend-notes-only <rids>` | Listed `review_item_id` values (notes only) | v2.8 |
| Replace-all | `--replace-all` | ALL existing decisions in run | NOT implemented |

### 2.2 Why replace-review-items is sufficient

The `--replace-review-items` flag (v2.8 item 1.3) provides **surgical replacement**: only explicitly listed `review_item_id` values are targeted. All other existing decisions are untouched. This satisfies the core correction use cases:

- Correct a wrong decision (PROMOTE → PARK, KILL → PROMOTE, etc.)
- Replace PARK with a different decision after re-evaluation
- Any single-decision or small-batch correction

A founder who needs to correct many decisions can list them all explicitly. The only case `--replace-all` adds is the ability to skip listing individual IDs — which is a minor convenience, not a capability gap.

### 2.3 Re-run workaround for wholesale changes

If a founder needs to replace every decision in a run, the existing "re-run the weekly cycle" workaround works:

1. Create a new decisions file with the corrected entries.
2. Re-run `run-weekly-cycle-v2` with the same input signals and the corrected decisions file.
3. This produces a new run with fresh artifacts and a clean audit trail.

The re-run is safe, deterministic, preserves traceability, and does not require any new code. It is the preferred path for wholesale decision changes.

---

## 3. Replace-All Definition

### 3.1 What replace-all means

**Trigger:** `--replace-all` flag on `import-founder-decisions-v2`

**Behavior:** Replace ALL existing decisions in a run with a new decisions file.

**Artifact impact (if implemented):**

| # | Artifact | Classification | Replace-all would need to |
|---|----------|---------------|---------------------------|
| 1 | `founder_decisions_v2.json` | Primary | Overwrite entirely with new decision set |
| 2 | `founder_feedback_mappings.json` | Derived | Full rebuild from new decisions |
| 3 | `founder_preference_profile.json` | Derived | Full rebuild from new decisions + mappings |
| 4 | `parking_lot_records.json` | Derived | Orphan cleanup (all old records) + rebuild from new decisions |
| 5 | `manifest.json` | Metadata | Record all old decision IDs as `replaced_decision_ids` |
| 6 | `run_report.json` / `run_report.md` | Derived | Regenerate with replace-all summary |
| 7 | `dashboard_index.json` / `dashboard.md` | Derived | Regenerate with replace-all indicator |
| 8 | `replaced_decisions/` | Archive | Archive ALL old decisions |
| 9 | `import_history.json` | Audit | Append one `CorrectionEntry` with `correction_mode = "replace_all"` |

### 3.2 How replace-all differs from replace-review-items

| Property | `--replace-review-items` | `--replace-all` |
|----------|--------------------------|-----------------|
| Scope | Listed `review_item_id` values only | All decisions |
| R8 (no silent deletion) | Satisfied — only listed items affected | **Violated** — ALL old decisions are wiped |
| Founder control | Founder explicitly names each item | Founder provides a complete replacement file (error-prone) |
| Safety | High — surgical | Low — any omission in the replacement file silently deletes a decision |
| Use case | Fix one or a few decisions | Wholesale decision replacement |
| Audit trail | Clear: known old IDs → known new IDs | Clear but coarse: all old IDs → all new IDs |

### 3.3 Contract definition (v2.8 artifact contract Section 4.4)

The v2.8 correction artifact contract Section 4.4 defines `--replace-all` as:

> **Recommendation:** **NOT recommended** unless explicitly justified. This mode is coarse and violates R8 (silent deletion of unrelated decisions) unless the founder carefully crafts the new decisions file to include all previously decided opportunities.
>
> **Deferral note:** Implementation of `--replace-all` is **not required** for v2.8. Documented here for completeness. May be revisited in v2.9+.

This policy review confirms the contract's assessment: `--replace-all` remains coarse and is not needed.

---

## 4. Use Cases

### 4.1 Hypothetical use cases for replace-all

| # | Use Case | Assessment |
|---|----------|-----------|
| 1 | Founder changes mind about all decisions in a run | Re-run the weekly cycle. Safer, deterministic, produces a new run with clean audit trail. |
| 2 | Founder imported wrong decisions file and wants to start over | Re-run the weekly cycle. Replace-all in-place is riskier than a fresh run. |
| 3 | Founder wants to batch-update all decisions from a new perspective | `--replace-review-items` with all IDs explicitly listed works today. |
| 4 | Automated batch correction from an external system | Not a v2.9 use case. Correction must remain founder-initiated and explicit. |

### 4.2 No demonstrated real-run need

As of v2.9 (2026-05-10), zero real-run scenarios have been reported where `--replace-review-items` was insufficient and `--replace-all` was the only viable path. The surgical mode covers all observed correction needs.

### 4.3 Why replace-all is not a convenience worth the risk

The convenience of `--replace-all` (not listing individual IDs) is traded against the safety of `--replace-review-items` (no silent deletion). In a system where decisions are the primary founder-controlled artifact, silent deletion of an accidentally omitted decision is a material risk. The inconvenience of listing IDs explicitly is a feature, not a bug — it forces the founder to confirm each decision being replaced.

---

## 5. Artifact Dependency Analysis

### 5.1 Replace-all impact by artifact

The following analysis traces how `--replace-all` would affect each artifact in the OOS weekly run. The dependency graph is from the [correction artifact contract](../contracts/founder_decision_correction_artifact_contract.md) Section 5.

#### 5.1.1 `founder_decisions_v2.json`

**Impact:** Complete overwrite.
**Risk:** **High.** If the replacement file is missing any previously decided opportunity, that decision is silently deleted.
**Mitigation:** Dry-run/plan mode that shows which old decisions would be lost. Confirm-step prompt requiring the founder to acknowledge the deletion list.

#### 5.1.2 `import_history.json`

**Impact:** One new `CorrectionEntry` appended with `correction_mode = "replace_all"`.
**Risk:** **Low.** Append-only audit trail; old entries preserved.
**Mitigation:** Standard append-only contract. No modification or deletion of existing entries.

#### 5.1.3 `replaced_decisions/`

**Impact:** ALL old decisions archived to a single archive file.
**Risk:** **Low.** Archive grows with each replace-all but storage is negligible.
**Mitigation:** Standard archive pattern. Timestamped filenames prevent collision.

#### 5.1.4 `founder_feedback_mappings.json`

**Impact:** Full rebuild from the new decision set.
**Risk:** **Low.** Deterministic rebuild from decisions. Same code path as `--replace-review-items`.
**Mitigation:** Standard rebuild. No additional risk beyond the primary decision overwrite.

#### 5.1.5 `founder_preference_profile.json`

**Impact:** Full rebuild from new decisions + new feedback mappings.
**Risk:** **Low.** Deterministic rebuild. Same code path as `--replace-review-items`.
**Mitigation:** Standard rebuild. Preference profile correctly reflects new decisions.

#### 5.1.6 `parking_lot_records.json`

**Impact:** Orphan cleanup (ALL old parking lot records removed), then rebuild from new PARK/REVISIT_LATER decisions.
**Risk:** **Medium.** All parking lot records are wiped and rebuilt. Any parking lot metadata (revisit_count, created_at) is lost unless preserved from the archive.
**Mitigation:** Archive old parking lot state alongside old decisions. Rebuild from new decisions only. The `import_history.json` entry records the transition.

#### 5.1.7 `manifest.json`

**Impact:** `replaced_decision_ids` set to ALL old decision IDs. `empty_states` updated.
**Risk:** **Low.** Manifest correctly records the replace-all operation.
**Mitigation:** Standard manifest update pattern.

#### 5.1.8 `run_report.json` / `run_report.md` and `dashboard_index.json` / `dashboard.md`

**Impact:** Regenerated with replace-all correction summary.
**Risk:** **Low.** Standard regeneration.
**Mitigation:** Report shows correction count, old/new decision IDs, and replace-all indicator.

### 5.2 Replace-all vs replace-review-items: artifact impact comparison

| Artifact | Replace-review-items | Replace-all |
|----------|---------------------|-------------|
| `founder_decisions_v2.json` | Merge: remove targeted old, add new | Complete overwrite |
| `import_history.json` | Append one replace entry | Append one replace_all entry |
| `replaced_decisions/` | Archive targeted old decisions | Archive ALL old decisions |
| `founder_feedback_mappings.json` | Full rebuild | Full rebuild (same) |
| `founder_preference_profile.json` | Full rebuild | Full rebuild (same) |
| `parking_lot_records.json` | Orphan cleanup + rebuild | Full orphan cleanup + rebuild |
| `manifest.json` | Record targeted `replaced_decision_ids` | Record ALL `replaced_decision_ids` |
| `run_report` / `dashboard` | Regenerated | Regenerated (same) |

The rebuild paths for derived artifacts are identical. The difference is scope: targeted vs. wholesale. The risk is entirely in the primary artifact overwrite, not in the derived rebuilds.

---

## 6. Risk Analysis

### 6.1 Top risks

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|-----------|-----------|
| 1 | **Silent deletion of omitted decisions.** Founder provides a replacement file that is missing one or more previously decided opportunities. Those decisions are lost. | **Critical** | Medium | Dry-run/plan mode showing deletion list; confirm-step prompt; fail if replacement file does not cover all previously decided opportunities (strict mode). |
| 2 | **Accidental replace-all.** Founder runs `--replace-all` without understanding the consequences. | **High** | Low | Explicit CLI flag required; confirm-step prompt; dry-run mode first. |
| 3 | **Incomplete replacement file.** Founder intends to replace all but accidentally provides a partial file. | **High** | Medium | Strict mode: reject if replacement file does not cover ALL existing opportunity IDs. |
| 4 | **Parking lot history loss.** All parking lot metadata is wiped on rebuild. | **Medium** | High (on every replace-all) | Archive old parking lot state. `import_history.json` records the transition. |
| 5 | **Preference profile discontinuity.** Replace-all resets the preference profile, potentially losing long-term founder learning signals. | **Medium** | High (on every replace-all) | Preference profile is rebuilt deterministically from decisions; no long-term state beyond the current run is stored. Acceptable if all decisions are intentionally replaced. |
| 6 | **Source URL traceability gap.** Replacement decisions might carry fewer or different source URLs than the old decisions. | **Medium** | Medium | Source URL traceability check must pass after replace-all (same as replace-review-items). Fail-closed if placeholder URNs detected. |
| 7 | **Idempotency confusion.** Re-running `--replace-all` with the same file twice archives the same decisions again and appends duplicate audit entries. | **Low** | Low | Idempotent in artifact state (same decisions → same files) but not in audit trail (two entries). Acceptable — audit trail records every operation. |

### 6.2 Edge cases

1. **Replace-all with empty replacement file.** All decisions removed. Run becomes effectively empty. Must be explicitly allowed or rejected based on policy.
2. **Replace-all when `founder_decisions_v2.json` does not exist yet.** No old decisions to archive. Equivalent to a normal import. Should this be allowed? If yes, it's indistinguishable from `--replace-review-items` with a new import. If no, reject with "no existing decisions to replace."
3. **Replace-all after a previous replace-review-items.** The old decisions include previously replaced decisions. Archive correctly captures all current decisions. No special handling needed.
4. **Replace-all after a previous amend-notes-only.** Amended notes are lost unless the replacement file includes the amended notes. The founder must be aware of this.
5. **Replace-all on a run that was itself the result of a replace-all.** The archive preserves the intermediate state. The audit trail shows the full chain.

### 6.3 Risk comparison: replace-all vs re-run weekly cycle

| | `--replace-all` | Re-run `run-weekly-cycle-v2` |
|---|---|---|
| In-place edit | Yes | No (new run created) |
| Old run preserved | Via `replaced_decisions/` | Entire old run directory preserved |
| Audit trail | One `replace_all` entry | New run with clean audit trail |
| Downstream artifact rebuild | Yes | Yes (built fresh) |
| Risk of silent deletion | High (if replacement file incomplete) | None (new run, old run untouched) |
| Implementation cost | ~80 lines + tests | Zero (already exists) |
| Convenience | Slightly more convenient (no new run directory) | Marginally less convenient |

The re-run workaround is safer and already exists. The marginal convenience of in-place replace-all does not justify the implementation risk.

---

## 7. Required Safety Properties

If `--replace-all` is implemented in v2.10+, it MUST satisfy ALL of the following:

| # | Requirement | Rationale |
|---|-------------|----------|
| **RA-R1** | **Explicit CLI flag required.** `--replace-all` must be an explicit flag. No implicit replace-all behavior. | Prevents accidental wholesale replacement. |
| **RA-R2** | **Fail-closed.** If any validation step fails, no artifacts are written. | Preserves existing fail-closed contract from v2.6. |
| **RA-R3** | **All-or-nothing.** Replace-all either fully succeeds or fully fails. No partial artifact state. | Consistency with replace/amend semantics. |
| **RA-R4** | **Dry-run/plan mode required before execution.** A `--dry-run` flag must show exactly which old decisions would be replaced and which new decisions would be written, without modifying any artifacts. | Founder must review the replacement plan before committing. |
| **RA-R5** | **Confirm-step prompt.** After dry-run, the CLI must prompt "Replace all N decisions? This cannot be undone via --undo-last (v2.10+). Type 'yes' to confirm:" before executing writes. | Prevents accidental execution. |
| **RA-R6** | **Strict mode: reject incomplete replacement.** The replacement file must cover ALL existing opportunity IDs. If any existing opportunity is not addressed in the replacement file, replace-all is rejected with a list of missing opportunities. | Prevents silent deletion of omitted decisions (mitigates Risk #1). |
| **RA-R7** | **Archive all replaced decisions.** ALL old decisions must be written to `replaced_decisions/` with a timestamped filename before any new decisions are written. | Audit trail and recovery. |
| **RA-R8** | **Append-only audit.** One `CorrectionEntry` with `correction_mode = "replace_all"` appended to `import_history.json`. Existing entries never modified or deleted. | Audit trail integrity. |
| **RA-R9** | **No portfolio mutation.** `advisory_only=True` throughout. | Founder-control boundary preserved. |
| **RA-R10** | **No autonomous inference.** The system must not create, modify, or delete decisions the founder did not explicitly address. | Explicit founder intent only. |
| **RA-R11** | **Source URL traceability preserved.** After replace-all, every `FounderDecisionV2.linked_source_urls` must contain real `http`/`https` URLs. Zero `urn:oos:*` placeholders. | Source URL traceability contract. |
| **RA-R12** | **Deterministic.** Same input replacement file on same run state yields identical artifact state. | Predictability and testability. |
| **RA-R13** | **Derived artifacts rebuilt.** After replace-all, feedback mappings, preference profile, and parking lot records must be consistent with new decisions. | No stale derived artifacts. |

### 7.1 Comparison: Replace-all safety vs Replace-review-items safety

Replace-all requires 5 additional safety properties beyond the 13 standard requirements (R1–R13) that replace-review-items already satisfies:

| New for replace-all | Not needed for replace-review-items |
|---------------------|-------------------------------------|
| RA-R4: Dry-run/plan mode required | Not needed — scope is explicit and small |
| RA-R5: Confirm-step prompt | Not needed — each item is individually listed |
| RA-R6: Strict mode (reject incomplete) | Not applicable — scope is per-item, not all-or-nothing |
| RA-R4/R5/R6 exist specifically to mitigate the silent-deletion risk that replace-review-items avoids by design. | |

---

## 8. Decision

### FINAL DECISION: DEFER to v2.10+

**Rationale:**

1. **`--replace-all` is coarse and violates R8 by design.** The v2.8 correction artifact contract Section 4.4 explicitly states this mode is "NOT recommended" because it "violates R8 (silent deletion of unrelated decisions) unless the founder carefully crafts the new decisions file." The surgical `--replace-review-items` mode satisfies R8 by targeting only listed items.

2. **No demonstrated real-run need.** Zero scenarios have been reported where `--replace-review-items` was insufficient and `--replace-all` was the only solution. The existing mode covers all observed correction use cases.

3. **The re-run workaround is safe and already exists.** A founder who needs wholesale decision replacement can re-run `run-weekly-cycle-v2` with the corrected decisions file. This creates a new run with clean artifacts, preserves the old run intact, and requires zero new code.

4. **Implementing replace-all safely requires non-trivial safety machinery.** Dry-run mode, confirm-step prompt, and strict-mode validation (RA-R4 through RA-R6) add ~80 lines of new code and ~15 new tests. This exceeds the "trivial" threshold (≤50 lines, 1 file) specified in the roadmap scope.

5. **v2.9 is deferred-item-closure, not feature expansion.** The roadmap's strategic principles state: "This is deferred-item closure + operational polish, not feature expansion." Adding a new correction mode crosses into feature expansion territory, especially when the existing modes are sufficient.

6. **The policy review itself has value.** This document records 13 safety requirements (RA-R1 through RA-R13), analyzes replace-all's impact on all 9 artifacts, identifies 7 top risks with mitigations, and provides a concrete v2.10+ implementation plan. The v2.8 contract Section 4.4 remains the authoritative specification for future reference.

7. **The 3.1 rollback/undo policy was also deferred for similar reasons.** Consistency across correction recovery items (3.1 and 3.2) reinforces the principle that v2.9 evaluates these as policy items and defers implementation to v2.10+.

---

## 9. Recommended Future Implementation Plan (v2.10+)

### 9.1 Pre-conditions for v2.10 implementation

1. All v2.9 items are complete and validated.
2. The correction workflow E2E validation (v2.8 C1–C14) passes with the existing replace/amend modes.
3. The `--replace-review-items` path has been exercised in at least one real run.
4. A concrete real-run need for `--replace-all` has been demonstrated (founder feedback, not hypothetical).
5. The undo-last feature (3.1, deferred to v2.10+) has been implemented, since undo-last must handle the case where the last correction was a replace-all.

### 9.2 Target mode: `--replace-all` with strict completeness check

The implementation should enforce RA-R6 (strict mode): the replacement file MUST cover ALL existing opportunity IDs. If any existing opportunity is missing from the replacement file, replace-all is rejected. This eliminates the silent-deletion risk.

If the founder truly wants to delete a decision, they must explicitly do so via `--replace-review-items` for that specific item. Replace-all is for wholesale replacement with a complete file, not for deleting decisions by omission.

### 9.3 Implementation scope (v2.10 estimate)

| File | Change |
|------|--------|
| `src/oos/founder_decision_import.py` (modify) | Add `replace_all: bool = False` parameter to `import_founder_decisions()`. Add `_import_replace_all_mode()` function (~50 lines): validate completeness (all existing opportunity IDs covered), archive all old decisions, write all new decisions, rebuild derived artifacts, append audit history. |
| `src/oos/cli.py` (modify) | Add `--replace-all` and `--dry-run` flags to `import-founder-decisions-v2` subcommand (~15 lines). |
| `tests/test_founder_decision_import_v2.py` (modify) | 15+ tests: replace-all with complete file, replace-all with incomplete file (rejected), replace-all dry-run, replace-all idempotency, replace-all archive, replace-all audit trail, replace-all parking lot rebuild, replace-all source URL traceability, replace-all fail-closed, replace-all advisory flags. |
| `docs/decisions/replace_all_mode_policy.md` (update) | Mark as implemented at v2.10; update with actual implementation details. |

**Total estimate:** ~80 source lines, 2 files modified, 15+ tests. Classified as **small** (50–150 lines, ≤3 files).

### 9.4 Design pre-work for v2.10

Before implementing `--replace-all`, the following design decisions should be addressed:

1. **Strict vs. lenient completeness check.** Should `--replace-all` reject incomplete replacement files (strict, RA-R6) or allow them with a warning (lenient)? Recommendation: strict. Silent deletion is the primary risk. If the founder truly wants to delete a decision, they should use `--replace-review-items` with an explicit KILL.

2. **Interaction with `--undo-last`.** If undo-last is implemented (3.1), it must handle the case where the last correction was a replace-all. This means restoring all old decisions from the `replaced_decisions/` archive.

3. **Interaction with `--dry-run`.** The dry-run output should show: count of old decisions to be archived, count of new decisions to be written, list of opportunity IDs that would be removed, list of opportunity IDs that would be added, and any warnings about decision-type transitions (e.g., PARK → KILL pattern changes).

4. **Replace-all and the parking lot.** Since all parking lot records are rebuilt, the dry-run should show how many parking lot records would be removed and how many new ones would be created.

5. **`correction_mode` field.** The `CorrectionEntry.correction_mode` field should accept `"replace_all"` as a valid value. The existing `correction_mode` field in [`founder_decision_import.py`](src/oos/founder_decision_import.py:148) is a free-form `str`, so no schema change is needed.

### 9.5 Non-implementation work for v2.10

Even if implementation is deferred, the following is recommended:

- Keep the v2.8 correction artifact contract Section 4.4 as the authoritative specification for `--replace-all` semantics.
- Document the re-run workaround in the weekly run smoke test runbook as the recommended path for wholesale decision changes.
- If undo-last is implemented in v2.10, ensure `correction_mode = "replace_all"` is handled as an undoable operation.

---

## 10. Non-Goals

This policy review does **not**:

1. Implement `--replace-all` code.
2. Modify `src/`, `tests/`, `scripts/`, `examples/`, `artifacts/`.
3. Add CLI flags (`--replace-all`, `--dry-run`).
4. Create new correction modes.
5. Change replace/amend behavior.
6. Add confirm-step prompts or dry-run modes.
7. Implement strict-mode completeness validation.
8. Add portfolio mutation or autonomous decisions.
9. Call live APIs or LLMs.
10. Create a UI beyond CLI flags.
11. Implement batch cross-run replacement.
12. Weaken the source URL traceability scanner.

---

## Appendix A: Self-Audit

| Question | Answer |
|-----------|--------|
| Did this avoid implementation? | **Yes.** Policy/docs only. No `.py` files modified. |
| Did this avoid source/test changes? | **Yes.** No source or test files changed. |
| Did this review the existing contract? | **Yes.** Reviewed v2.8 correction artifact contract Section 4.4. |
| Did this assess real-run need? | **Yes.** Zero demonstrated scenarios where replace-all is necessary. |
| Did this analyze artifact impact? | **Yes.** Section 5 covers all 9 artifacts. |
| Did this identify risks? | **Yes.** Section 6 identifies 7 top risks with mitigations and 5 edge cases. |
| Did this define safety requirements? | **Yes.** Section 7 defines 13 safety requirements (RA-R1 through RA-R13). |
| Did this make an explicit decision? | **Yes.** DEFER to v2.10+. |
| Did this provide a future implementation plan? | **Yes.** Section 9 provides v2.10 scope, file list, and design pre-work. |
| Did this preserve founder-control assumptions? | **Yes.** Advisory-only, explicit CLI flag, founder-initiated, no autonomous decisions. |
| Did this avoid live APIs/LLMs? | **Yes.** No network, API, or LLM calls. |
| Did this preserve source URL traceability? | **Yes.** RA-R11 requires zero placeholder URNs after replace-all. |
| Is the recommendation aligned with roadmap principles? | **Yes.** "Correction recovery prudence" and "this is deferred-item closure, not feature expansion." |

---

## Appendix B: Comparison — All Correction Modes

| Mode | CLI Flag | Scope | Direction | Implemented |
|------|----------|-------|-----------|-------------|
| Reject-on-reimport | (default) | All decisions | N/A | v2.6 |
| Replace-review-items | `--replace-review-items` | Listed `review_item_id` values | Forward (old→new) | v2.8 |
| Amend-notes-only | `--amend-notes-only` | Listed `review_item_id` values (notes only) | In-place | v2.8 |
| Replace-all | `--replace-all` | All decisions in run | Forward (old→new) | Policy only (this document) |
| Undo-last | `--undo-last` | Most recent correction | Backward (new→old) | Policy only (v2.9 item 3.1) |

---

## Appendix C: How This Differs from the Rollback/Undo Policy (3.1)

| Aspect | Rollback/Undo (3.1) | Replace-all (3.2) |
|--------|---------------------|-------------------|
| Problem | Revert a wrong correction | Wholesale decision replacement |
| Scope | Reverse a correction | Replace all decisions |
| Existing workaround | Re-issue `--replace-review-items` with original decisions | Re-run `run-weekly-cycle-v2` with corrected decisions file |
| Primary risk | Partial undo writes, stale source URLs | Silent deletion of omitted decisions |
| Safety requirements | 12 (U-R1 through U-R12) | 13 (RA-R1 through RA-R13) |
| New requirements beyond replace-review-items | 5 (undo-specific) | 5 (replace-all-specific, including dry-run, confirm, strict mode) |
| Implementation estimate | ~200 lines, 4 files | ~80 lines, 2 files |
| Verdict | DEFER (non-trivial) | DEFER (no demonstrated need; re-run workaround exists) |
| v2.10+ target | U1 (`--undo-last`) only | `--replace-all` with strict completeness check |
