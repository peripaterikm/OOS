# Founder Decision Re-Import Policy

**Roadmap:** v2.7 item 3.1, Phase A — Policy Review
**Date:** 2026-05-08
**Status:** complete (policy review only; implementation deferred to v2.8+)
**Decision:** Defer founder decision replace/amend mode to v2.8+

---

## 1. Current Behavior (v2.6 + v2.7 items 1.1–2.1)

The founder decision import ([`src/oos/founder_decision_import.py`](../../src/oos/founder_decision_import.py)) implements the following semantics:

### 1.1 Import contract
- **Explicit founder decisions only.** All decisions come from a founder-authored JSON array or JSONL file.
- **Fail-closed.** If any single input decision is invalid (unknown `review_item_id`, invalid decision value, invalid reason categories, duplicate `review_item_id` in input, or existing decision for the same opportunity), **no artifacts are written**. The entire batch is rejected.
- **No partial writes.** Artifact writing happens only after all validation passes.
- **No portfolio mutation.** `advisory_only=True` throughout. No autonomous portfolio transitions.
- **No live APIs/LLMs.** All logic is deterministic and local.

### 1.2 Re-import / idempotency behavior
- **Duplicate `review_item_id` rejection.** If an inbox review item's `linked_opportunity_ids` overlap with any existing `FounderDecisionV2.opportunity_id`, the import is rejected with the error: _"import is idempotent — remove this item or use a new review_item_id"_.
- **This is currently a hard rejection.** There is no `--replace` flag, no `--amend` flag, no override mechanism.
- **The validation layer (not the write layer) enforces this.** The check happens in [`validate_founder_decision_inputs()`](../../src/oos/founder_decision_import.py:300-311), before any artifacts are touched.

### 1.3 Source URL traceability (added in v2.7 items 1.1–2.1)
- **Real source URLs required.** Every imported `FounderDecisionV2` must carry `linked_source_urls` with at least one real `http://` or `https://` URL.
- **Placeholder URNs rejected.** `urn:oos:*` patterns are banned in `linked_source_urls` (validated in [`create_founder_decision()`](../../src/oos/founder_decision_taxonomy.py:310-317)) and in `FounderFeedbackMapping.source_urls` (validated in [`validate_founder_feedback_mapping()`](../../src/oos/founder_feedback_mapping.py:334-340)).
- **Source URLs propagate from inbox `linked_source_urls`** (populated by the founder inbox builder from upstream evidence packs).

### 1.4 Downstream artifacts derived from imported decisions
| Artifact | How derived | Rebuilt on each import? |
|---|---|---|
| `founder_decisions_v2.json` | Written directly from imported + merged decisions | Yes |
| `founder_feedback_mappings.json` | `map_founder_decision_to_feedback()` for each decision | Yes (full rebuild) |
| `founder_preference_profile.json` | `build_founder_preference_profile()` from all decisions + mappings | Yes (full rebuild) |
| `parking_lot_records.json` | `build_parking_lot_records()` for PARK/REVISIT_LATER decisions; merged with existing via `_merge_parking_lot_records()` | Partial (new records added; old records deduplicated by `record_id` but **never removed**) |
| `manifest.json` | Empty states updated | Yes |

---

## 2. Problem Statement

A founder who records decisions may need to correct them:

- **Correct a wrong decision.** E.g., the founder promoted something that should have been PARKed, or KILLed something that deserves a second look.
- **Amend notes or reason categories.** The decision value stays the same but the rationale changes.
- **Replace PARK with PROMOTE or KILL.** A PARKed opportunity may later be re-evaluated within the same run.
- **Replace KILL with PARK or PROMOTE.** A KILLed opportunity may be reconsidered after new information surfaces.

Without a replace/amend mode, the founder's only options are:

1. **Manually edit JSON artifacts** in the run directory (error-prone, breaks traceability, violates the artifact immutability contract).
2. **Re-run the entire weekly cycle** with the corrected decisions file (expensive, loses the original decision history, regenerates all artifacts including non-decision ones).

Neither option is ideal for a founder who just needs to fix one or two decision records.

---

## 3. Safety Requirements for Any Replace/Amend Mode

If a replace or amend mode is implemented (in v2.7 or later), it MUST satisfy ALL of the following safety properties:

| # | Requirement | Rationale |
|---|---|---|
| **R1** | **Explicit CLI flag required.** E.g., `--replace` or `--amend`. Without the flag, re-import of existing decisions is rejected. | Prevents accidental overwrite. The founder must explicitly opt in. |
| **R2** | **Fail-closed.** If any input in a replace batch is invalid, no artifacts are written. | Preserves the existing fail-closed contract. Partial replacements are dangerous. |
| **R3** | **All-or-nothing.** A replace batch either fully succeeds or fully fails. No partial replacements. | Consistency with existing import semantics. |
| **R4** | **Source URL traceability preserved.** Replaced decisions must carry real `linked_source_urls` propagated from the inbox index. | Must satisfy the v2.7 source URL traceability contract (item 1.1). |
| **R5** | **All downstream artifacts rebuilt deterministically.** Feedback mappings, preference profile, and parking lot records must be consistent with the replaced decisions. | No stale or orphaned derived artifacts. |
| **R6** | **No portfolio mutation.** `advisory_only=True` must remain true. | Preserves the founder-control boundary. |
| **R7** | **No decision inference.** The system must not create, modify, or delete decisions the founder did not explicitly address. | Preserves the explicit-founder-decision-only contract. |
| **R8** | **No silent deletion of unrelated decisions.** Only decisions explicitly targeted by `--replace` are affected. | Safety property: replacing decision A must not affect decision B. |
| **R9** | **Clear import result/report.** The `FounderDecisionImportResult` must report which decisions were replaced, which artifacts were updated, and any warnings. | Auditability and transparency. |
| **R10** | **Idempotent.** Replacing the same decision twice with the same input yields identical artifact state. | Determinism and predictability. |
| **R11** | **Archival of replaced decisions.** Original decisions must be preserved in a `replaced_decisions/` subdirectory or with a `_replaced` suffix for audit trail. | The original decision history must not be lost. |
| **R12** | **Parking lot records cleaned up.** If a replaced decision was PARK or REVISIT_LATER, the corresponding `ParkingLotRecord` must be removed. Conversely, if the new decision is PARK/REVISIT_LATER, a new record must be created. | Prevents orphaned parking lot records that reference non-existent decisions. |
| **R13** | **Tested with before/after artifacts.** At least 12 focused tests must cover replace, replace-idempotency, replace-safety, parking lot cleanup, and fail-closed rejection. | Comprehensive test coverage. |

---

## 4. Options Evaluated

### Option A: Keep current reject-on-reimport behavior (status quo)

**Description:** No change. Re-import of any decision for an already-decided opportunity is rejected. The founder must re-run the entire weekly cycle to change a decision.

**Pros:**
- Zero implementation risk.
- No new code paths to test or maintain.
- Guaranteed safety — the system never overwrites decisions.

**Cons:**
- Inflexible. The founder's only correction path is a full pipeline re-run.
- Manual artifact editing is tempting but dangerous.

**Verdict:** Safe but inflexible. Acceptable for v2.7 given the "hardening, not feature expansion" roadmap scope.

---

### Option B: Add `--replace-review-items` for selected `review_item_ids`

**Description:** A CLI flag `--replace-review-items inbox_review_001,inbox_review_002` allows re-import of decisions for specific review items. Only those items are replaced; other existing decisions are untouched.

**Pros:**
- Surgical. Only targeted items are affected.
- Clear audit trail.

**Cons:**
- Requires parking lot record cleanup (see R12).
- Requires archival logic (see R11).
- Requires careful validation (skip existing-decision check only for flagged items).
- Touches `founder_decision_import.py`, `cli.py`, `parking_lot.py`, and `weekly_run_manifest.py`.

**Verdict:** The cleanest replacement semantics, but non-trivial implementation.

---

### Option C: Add `--replace-all` for whole run

**Description:** A CLI flag `--replace-all` allows replacing ALL existing decisions in a run with a new decisions file.

**Pros:**
- Simpler than per-item replacement (no selective cleanup).
- Closest to "re-run the cycle" semantics.

**Cons:**
- Destructive. All prior decisions are wiped, not just the ones the founder wants to fix.
- Violates R8 (silent deletion of unrelated decisions) unless the founder carefully crafts the new decisions file.
- Does not solve the core use case (correcting one or two decisions).

**Verdict:** Too coarse. Not recommended.

---

### Option D: Add `--amend-notes-only`

**Description:** A CLI flag `--amend-notes-only` allows updating only the `notes` field of an existing decision without changing the decision value, reason categories, or any downstream artifacts.

**Pros:**
- Minimal scope. Only the notes field changes.
- No parking lot cleanup needed.
- No feedback mapping or preference profile impact.

**Cons:**
- Does not address the primary use case (changing a wrong decision).
- Requires a separate code path from normal import.
- Adds complexity for a narrow feature.

**Verdict:** Useful but insufficient. Not a replacement for full replace mode.

---

### Option E: Defer replace mode to v2.8+

**Description:** Do not implement any replace/amend mode in v2.7. Document the policy, record the decision, and add a v2.8 hook note. Keep the current reject-on-reimport behavior.

**Pros:**
- Zero implementation risk for v2.7.
- Item 3.1 completes as policy review only — no code changes, no test changes.
- Roadmap item closes cleanly.
- Founder workaround ("re-run the weekly cycle") works for v2.7.
- Replacement semantics get proper design attention in v2.8 alongside other deferred features (LLM integration, Pain Discovery Layer, etc.).

**Cons:**
- Founder flexibility deferred by one roadmap cycle.
- Manual workaround (full cycle re-run) remains the only correction path.

**Verdict:** **RECOMMENDED.** Appropriate for v2.7's "hardening, not feature expansion" scope.

---

## 5. Recommendation

### FINAL RECOMMENDATION: Option E — Defer to v2.8+

**Rationale:**

1. **v2.7 is a hardening roadmap, not a feature expansion roadmap.** The v2.7 strategic principles state: _"Do not rewrite v2.6. Only fix known gaps and add workflow support."_ A replace mode is feature expansion, not gap-fixing.

2. **Safe replace requires non-trivial downstream artifact surgery.** The parking lot record cleanup (R12) alone requires a new function that reads, filters, and re-writes `parking_lot_records.json` — removing records whose `source_decision_id` matches replaced decisions. This touches `parking_lot.py` and the import artifact writer.

3. **Archival logic (R11) adds a new directory and new file-writing conventions** that must be consistent with the existing artifact store and manifest.

4. **The existing workaround works.** A founder who needs to correct a decision can:
   - Create a new decisions file with the corrected entries.
   - Re-run `run-weekly-cycle-v2` with the same input signals and the corrected decisions file.
   - This is a full re-run but is safe, deterministic, and preserves traceability.

5. **v2.8+ is the appropriate venue.** v2.8 is planned to include LLM integration, Pain Discovery Layer integration, and other feature work. A replace mode fits naturally alongside those features as part of a more mature founder workflow.

6. **The policy review itself has value.** This document serves as a design reference for v2.8+. The safety requirements (R1–R13) are recorded and can inform the implementation when it happens.

---

## 6. Decision

| Field | Value |
|---|---|
| **Decision** | Defer founder decision replace/amend mode to v2.8+ |
| **Phase A status** | Complete (policy review) |
| **Phase B status** | Deferred (no implementation in v2.7) |
| **Roadmap item 3.1** | **Complete as policy review only** |
| **Impact on roadmap counters** | Completed advances from 4/8 → 5/8; Remaining advances from 4/8 → 3/8 |
| **Current item advances to** | 4.1 Developer workflow helper scripts |
| **Rationale** | Safe replace requires non-trivial downstream artifact surgery (parking lot record cleanup, archival logic, manifest tracking). This crosses the "hardening, not feature expansion" boundary. Deferring keeps v2.7 focused and safe. |
| **v2.8 hook note** | See Section 7 below. |

---

## 7. v2.8 Hook Note

When v2.8 is planned, the replace mode should be one of the first items scoped. The following artifacts from this policy review should be carried forward:

### 7.1 Design inputs
- Safety requirements R1–R13 (Section 3 above) are the authoritative acceptance criteria.
- Option B (`--replace-review-items`) is the recommended approach for surgical replacement.
- Option D (`--amend-notes-only`) can be considered as a lighter-weight companion.

### 7.2 Expected implementation scope (v2.8 estimate)
| File | Change |
|---|---|
| `src/oos/founder_decision_import.py` | Add `--replace` parameter to `import_founder_decisions()`; skip existing-decision validation for flagged items; add `_archive_replaced_decisions()` helper; add `_cleanup_orphaned_parking_lot_records()` helper |
| `src/oos/cli.py` | Add `--replace-review-items` flag to `import-founder-decisions-v2` subcommand |
| `src/oos/founder_decision_taxonomy.py` | Possibly no changes (existing validation covers placeholder URNs) |
| `src/oos/founder_feedback_mapping.py` | Possibly no changes (already rebuilt from scratch each import) |
| `src/oos/founder_preference_profile.py` | Possibly no changes (already rebuilt from scratch each import) |
| `src/oos/parking_lot.py` | May need no changes if cleanup is done in the import module |
| `src/oos/weekly_run_manifest.py` | May need a `replaced_decision_ids` field in the manifest model |
| `tests/test_founder_decision_import_v2.py` | Add ≥15 focused tests for replace, replace-idempotency, replace-safety, parking lot cleanup, archival, and fail-closed rejection |

### 7.3 Pre-conditions for v2.8 implementation
- All v2.7 items must be complete and validated.
- The source URL traceability contract must be satisfied (no placeholder URNs).
- The controlled weekly run smoke test must pass with non-replace import first.

### 7.4 Known v2.8 integration points
- **LLM integration.** If v2.8 enables LLM-assisted decision suggestions, replace mode must handle the case where an LLM-suggested decision is corrected by the founder.
- **Pain Discovery Layer.** If PDL feeds auto-discovered signals into the pipeline, replace mode must work with decisions on PDL-derived opportunities.
- **Recurrence memory.** The preference profile's recurring kill reasons and rejected patterns derive from decisions. Replace mode must ensure these are correctly rebuilt.

---

## 8. Validation Checklist (Phase A — Policy Review Only)

- [x] **8.1** Policy document exists at `docs/decisions/founder_decision_reimport_policy.md`.
- [x] **8.2** Document covers: current behavior (Section 1), problem statement (Section 2), safety requirements (Section 3), options evaluated (Section 4), recommendation (Section 5), decision (Section 6), v2.8 hook note (Section 7).
- [x] **8.3** Decision is explicit: DEFER to v2.8+.
- [x] **8.4** Rationale is recorded with specific code-path analysis.
- [x] **8.5** No source code was modified.
- [x] **8.6** No tests were modified.
- [x] **8.7** No import behavior was changed.
- [x] **8.8** Founder-control assumptions preserved.
- [x] **8.9** No live APIs/LLMs invoked.

---

## 9. Self-Audit

| Question | Answer |
|---|---|
| Did this avoid source code changes? | **Yes.** No `.py` files modified. |
| Did this avoid changing import behavior? | **Yes.** Re-import rejection is unchanged. |
| Did this preserve founder-control assumptions? | **Yes.** Advisory-only and explicit-founder-decision-only preserved. |
| Did this avoid live APIs/LLMs? | **Yes.** No network, API, or LLM calls. |
| Is the final decision explicit? | **Yes.** Documented in Section 6. |
| Is the impact on roadmap counters clear? | **Yes.** 3.1 complete as policy review; completed 5/8; remaining 3/8; current advances to 4.1. |
