# Founder Decision Correction Artifact Contract

**Version:** founder_decision_correction.v1
**Roadmap:** v2.8 item 1.1 (contract); item 1.2 (implementation)
**Status:** contract active; implementation completed in `src/oos/decision_correction_rebuild.py`
**Depends on:**
- [`founder_decision_reimport_policy.md`](../decisions/founder_decision_reimport_policy.md) (v2.7 item 3.1)
- [`source_url_traceability_contract.md`](source_url_traceability_contract.md) (v2.7 item 1.1)
**Precedes:**
- Roadmap v2.8 item 1.2 — Parking lot orphan cleanup and derived artifact rebuild model
- Roadmap v2.8 item 1.3 — Safe replace/amend implementation in founder decision import

---

## 1. Purpose

This contract defines the **authoritative specification** for safe founder decision correction in the OOS weekly loop. It formalizes the replace/amend semantics, artifact rewrite rules, parking lot integrity policy, derived artifact rebuild order, import history / audit trail schema, and source URL traceability guarantee that any correction implementation **must** satisfy.

This document is **contract-first**. It does **not** implement any behavior. It serves as the acceptance criteria for implementation items 1.2 and 1.3.

---

## 2. Current Behavior (v2.6 + v2.7)

### 2.1 Import contract ([`founder_decision_import.py`](../../src/oos/founder_decision_import.py))

| Property | Value |
|---|---|
| Decision source | Founder-authored JSON array or JSONL file |
| Validation | Fail-closed — any invalid input → no artifacts written |
| Partial writes | None — all-or-nothing atomic-ish write (individual JSON writes, no transactional rollback) |
| Portfolio mutation | None — `advisory_only=True` throughout |
| Live APIs/LLMs | None — all logic deterministic and local |
| Source URLs | Real `http`/`https` URLs propagated from inbox index; `urn:oos:*` rejected |

### 2.2 Re-import / idempotency behavior

- **Duplicate `review_item_id` rejection.** If an inbox review item's `linked_opportunity_ids` overlap with any existing `FounderDecisionV2.opportunity_id`, the import is rejected with a hard error.
- **No override mechanism.** No `--replace` flag, no `--amend` flag.
- **The validation layer enforces this** in [`validate_founder_decision_inputs()`](../../src/oos/founder_decision_import.py:300-311), before any artifacts are touched.

### 2.3 Derived artifact behavior on import

| Artifact | How derived | Rebuilt on each import? |
|---|---|---|
| `founder_decisions_v2.json` | Written directly from imported + merged decisions | Yes |
| `founder_feedback_mappings.json` | `map_founder_decision_to_feedback()` for each decision | Yes (full rebuild) |
| `founder_preference_profile.json` | `build_founder_preference_profile()` from all decisions + mappings | Yes (full rebuild) |
| `parking_lot_records.json` | `build_parking_lot_records()` for PARK/REVISIT_LATER decisions; merged via `_merge_parking_lot_records()` | Partial (new records added; old records **never removed**) |
| `manifest.json` | Empty states updated | Yes |

### 2.4 Source URL traceability (v2.7)

- Real `http`/`https` source URLs are required in every `FounderDecisionV2.linked_source_urls` and `FounderFeedbackMapping.source_urls`.
- `urn:oos:*` placeholders are rejected at validation time.
- Source URLs propagate from the inbox index's `linked_source_urls` field.

---

## 3. Problem Statement

A founder who records decisions may need to correct them:

1. **Correct a wrong decision.** E.g., promoted something that should have been PARKed, or KILLed something that deserves a second look.
2. **Amend notes or reason categories.** The decision value stays the same but the rationale changes.
3. **Replace PARK with PROMOTE or KILL.** A PARKed opportunity may later be re-evaluated within the same run.
4. **Replace KILL with PARK or PROMOTE.** A KILLed opportunity may be reconsidered.

Without a replace/amend mode, the founder's only options are:
- **Manually edit JSON artifacts** (error-prone, breaks traceability, violates artifact immutability).
- **Re-run the entire weekly cycle** with corrected decisions (expensive, loses original decision history).

---

## 4. Correction Modes

### 4.1 Mode 0: `reject-on-reimport` (current behavior, unchanged)

**Description:** Re-import of any decision for an already-decided opportunity is rejected.

**When to use:** Default behavior. No flags needed. Preserves idempotency.

**Artifact impact:** None. No writes occur.

**Safety:** Maximum. No risk of overwrite.

---

### 4.2 Mode 1: `replace-review-items` (surgical replacement)

**Trigger:** `--replace-review-items <review_item_id_1>,<review_item_id_2>,...`

**Description:** Only explicitly listed `review_item_id` values are targeted for replacement. All other existing decisions are untouched.

**Behavior:**

1. **Validation phase:**
   - Skip the existing-decision idempotency check **only** for the listed `review_item_id` values.
   - All other validation checks remain enforced:
     - `review_item_id` must exist in the inbox index.
     - Decision value must be allowed.
     - Reason categories must be valid for the given decision.
     - No duplicate `review_item_id` entries in the input batch.
     - Source URLs must carry real `http`/`https` URLs (no `urn:oos:*`).
   - If **any** validation error occurs, the entire batch is rejected (fail-closed).

2. **Write phase (all-or-nothing):**
   - Archive old decisions to `{run_dir}/replaced_decisions/` with `_replaced_{timestamp}` suffix.
   - Remove old decisions from the merged decision set.
   - Insert new decisions.
   - Call orphan cleanup for replaced PARK/REVISIT_LATER decisions.
   - Rebuild feedback mappings, preference profile, and parking lot records.
   - Update run manifest with `replaced_decision_ids`.
   - Regenerate run report and dashboard.

**Idempotency:** Replacing the same decision twice with identical input yields identical artifact state.

**Safety constraints:**
- Only `review_item_id` values in the explicit list are targeted (R8: no silent deletion of unrelated decisions).
- No portfolio mutation (R6).
- No decision inference (R7).
- Founder-controlled only.

---

### 4.3 Mode 2: `amend-notes-only` (notes/reason amendment)

**Trigger:** `--amend-notes-only <review_item_id_1>,<review_item_id_2>,...`

**Description:** Only the `notes` field (and optionally `reason_categories`) is updated. The decision value is unchanged. Downstream artifacts (feedback mappings, preference profile, parking lot) are **not** rebuilt.

**Behavior:**

1. **Validation phase:**
   - The target `review_item_id` must have an existing decision.
   - The new `notes` (and optional `reason_categories`) must be valid.
   - Decision value must match the existing decision (cannot change decision type in amend mode).

2. **Write phase:**
   - Archive old notes to `{run_dir}/amended_decisions/` with `_amended_{timestamp}` suffix.
   - Update `notes` (and optionally `reason_categories`) in place in `founder_decisions_v2.json`.
   - **Do not** rebuild feedback mappings, preference profile, or parking lot records.
   - Update run manifest with `amended_decision_ids`.
   - Regenerate run report and dashboard to reflect the amendment note.

**Idempotency:** Amending the same decision twice with identical notes input yields identical artifact state.

**Safety constraints:**
- Decision value cannot change.
- Downstream artifacts are not affected.
- No portfolio mutation (R6).

---

### 4.4 Mode 3: `replace-all` (whole-run replacement)

**Trigger:** `--replace-all`

**Description:** Replaces ALL existing decisions in a run with a new decisions file.

**Recommendation:** **NOT recommended** unless explicitly justified. This mode is coarse and violates R8 (silent deletion of unrelated decisions) unless the founder carefully crafts the new decisions file to include all previously decided opportunities.

**Behavior (if implemented):**
- All existing decisions are archived.
- All new decisions from the input file are written.
- Full rebuild of all derived artifacts.
- Manifest records `replaced_decision_ids` for all old decisions.

**Deferral note:** Implementation of `--replace-all` is **not required** for v2.8. Documented here for completeness. May be revisited in v2.9+.

---

## 5. Artifact Dependency Graph

The following graph shows the read/write dependencies between artifacts during a correction operation. Arrows indicate "is derived from" / "must be consistent with."

```
founder_inbox_v2_index.json          (read-only — source of linked_source_urls)
         │
         ▼
founder_decisions_v2.json            (PRIMARY — written by replace/amend)
         │
         ├──► founder_feedback_mappings.json   (DERIVED — rebuilt on replace; untouched on amend)
         │         │
         │         ▼
         ├──► founder_preference_profile.json  (DERIVED — rebuilt on replace; untouched on amend)
         │
         ├──► parking_lot_records.json         (DERIVED — orphan cleanup + rebuild on replace; untouched on amend)
         │
         ├──► manifest.json                    (METADATA — empty_states updated; replaced_decision_ids / amended_decision_ids added)
         │
         ├──► run_report.json / run_report.md  (DERIVED — regenerated after replace/amend)
         │
         └──► dashboard_index.json / dashboard.md  (DERIVED — regenerated after replace/amend)

replaced_decisions/                  (ARCHIVE — old decisions stored on replace)
amended_decisions/                   (ARCHIVE — old notes stored on amend)
import_history.json                  (AUDIT — correction entries appended)
```

### 5.1 Artifact write classification

| Artifact | Classification | Replace | Amend |
|---|---|---|---|
| `founder_decisions_v2.json` | Primary | Rewritten (merge) | Updated in place (notes only) |
| `founder_feedback_mappings.json` | Derived | Full rebuild | No change |
| `founder_preference_profile.json` | Derived | Full rebuild | No change |
| `parking_lot_records.json` | Derived | Orphan cleanup + rebuild | No change |
| `manifest.json` | Metadata | Updated (empty_states + replaced_decision_ids) | Updated (amended_decision_ids) |
| `run_report.json` / `run_report.md` | Derived | Regenerated | Regenerated |
| `dashboard_index.json` / `dashboard.md` | Derived | Regenerated | Regenerated |
| `replaced_decisions/` | Archive | Written (new) | Not written |
| `amended_decisions/` | Archive | Not written | Written (new) |
| `import_history.json` | Audit | Appended (replace entry) | Appended (amend entry) |

---

## 6. Rewrite Rules by Artifact

### 6.1 `founder_decisions_v2.json`

**Replace behavior:**
1. Read existing `founder_decisions_v2.json` items into `list[FounderDecisionV2]`.
2. Identify decisions whose `opportunity_id` matches any `linked_opportunity_ids` from the targeted `review_item_id` values.
3. Archive matched decisions to `{run_dir}/replaced_decisions/founder_decisions_v2_replaced_{iso_timestamp}.json`.
4. Remove matched decisions from the list.
5. Insert new decisions (validated, converted `FounderDecisionV2` objects).
6. Write the updated list to `founder_decisions_v2.json`.
7. Update `empty` flag and `note` field.

**Amend behavior:**
1. Read existing `founder_decisions_v2.json` items.
2. Identify the decision whose `decision_id` matches the target.
3. Archive old `notes` field to `{run_dir}/amended_decisions/founder_decisions_v2_amended_{iso_timestamp}.json`.
4. Update `notes` (and optionally `reasons`) in place.
5. Write the updated list to `founder_decisions_v2.json`.
6. Update `note` field to reflect amendment.

**Constraints:**
- Schema version preserved: `founder_decision_v2.v1`.
- `decided_by` remains `"founder"`.
- `founder_decision_authority` remains `"founder_decision_record_only"`.
- `auto_promote` remains `false`.
- `linked_source_urls` must carry real `http`/`https` URLs.

---

### 6.2 `founder_feedback_mappings.json`

**Replace behavior:**
1. Read existing `founder_feedback_mappings.json` items.
2. Full rebuild: for every decision in the updated `founder_decisions_v2.json`, call `map_founder_decision_to_feedback()`.
3. Write the rebuilt list.
4. Update `empty` flag.

**Amend behavior:**
- **No change.** Feedback mappings are derived from decision values, which are unchanged in amend mode.

**Constraints:**
- Schema version preserved: `founder_feedback_mapping.v1`.
- `source_urls` must carry real `http`/`https` URLs.
- `scoring_mutation_applied` remains `false`.
- `founder_decision_final` remains `true`.

---

### 6.3 `founder_preference_profile.json`

**Replace behavior:**
1. Full rebuild: call `build_founder_preference_profile(decisions=all_decisions, feedback_mappings=all_mappings)` with the updated decision set.
2. Write the rebuilt profile.

**Amend behavior:**
- **No change.** Preference profile is derived from decision values and feedback mappings, which are unchanged in amend mode.

**Constraints:**
- Schema version preserved: `founder_preference_profile.v1`.
- `ml_training_claimed` remains `false`.
- `autonomous_decisions_made` remains `false`.
- Per-decision counts must sum correctly.

---

### 6.4 `parking_lot_records.json`

**Replace behavior:**
1. Orphan cleanup: remove records whose `source_decision_id` matches any replaced decision ID.
2. Rebuild: call `build_parking_lot_records(decisions=all_decisions)` with the updated decision set.
3. Merge rebuilt records with surviving existing records (deduplicating by `record_id`).
4. Write the cleaned-and-rebuilt list.
5. Update `empty` flag.

**Amend behavior:**
- **No change.** Parking lot records are derived from decision values (PARK/REVISIT_LATER), which are unchanged in amend mode.

**Constraints:**
- Schema version preserved: `parking_lot.v1`.
- `advisory_only` remains `true` on all records.
- No orphaned records with dangling `source_decision_id` references.

---

### 6.5 `manifest.json`

**Replace behavior:**
1. Update `empty_states`:
   - `founder_decisions_v2`: `true` if no decisions remain, `false` otherwise.
   - `founder_feedback_mappings`: `true` if no mappings remain, `false` otherwise.
   - `founder_preference_profile`: `false` (always present if there are decisions).
   - `parking_lot_records`: `true` if no records remain, `false` otherwise.
2. Add/update `replaced_decision_ids: list[str]` — the `decision_id` values of replaced decisions.
3. Add/update `replaced_at: str` — ISO 8601 timestamp of replacement.

**Amend behavior:**
1. Add/update `amended_decision_ids: list[str]` — the `decision_id` values of amended decisions.
2. Add/update `amended_at: str` — ISO 8601 timestamp of amendment.

**Constraint:** All existing manifest fields (run metadata, schema versions, advisory flags) are preserved.

---

### 6.6 `run_report.json` / `run_report.md`

**Replace behavior:**
1. Regenerate the run report with correction summary:
   - `correction_count`: number of replaced decisions.
   - `replaced_decision_ids`: list of old decision IDs.
   - `new_decision_ids`: list of new decision IDs.
   - `correction_mode`: `"replace"`.
   - `orphaned_parking_lot_records_removed`: count.
   - `parking_lot_records_added`: count.
   - Source URL traceability pass/fail after correction.

**Amend behavior:**
1. Regenerate the run report with amendment summary:
   - `amendment_count`: number of amended decisions.
   - `amended_decision_ids`: list of amended decision IDs.
   - `correction_mode`: `"amend"`.
   - Source URL traceability pass/fail after amendment.

---

### 6.7 `dashboard_index.json` / `dashboard.md`

**Replace behavior:**
1. Regenerate the dashboard index with per-run correction summary:
   - `correction_count` in `WeeklyDashboardRunSummary`.
   - `[CORRECTED]` indicator on corrected run entries.

**Amend behavior:**
1. Regenerate the dashboard index with per-run amendment summary:
   - `amendment_count` in `WeeklyDashboardRunSummary`.
   - `[AMENDED]` indicator on amended run entries.

---

## 7. Parking Lot Orphan / Supersession Policy

### 7.1 What happens when PARK/REVISIT becomes PROMOTE/KILL/NEEDS_MORE_EVIDENCE

When a founder replaces a PARK or REVISIT_LATER decision with a non-parking decision:

1. **Orphan detection:** The old `ParkingLotRecord` whose `source_decision_id` matches the replaced decision's `decision_id` is identified.
2. **Orphan removal:** The record is **removed** from `parking_lot_records.json` during the cleanup phase.
3. **No supersession record:** A parking lot record that is removed because its source decision was replaced does **not** get a supersession marker in the parking lot file. The replacement is recorded in `import_history.json` instead.
4. **Archive preservation:** The old parking lot record is preserved in the archived `parking_lot_records.json` that was written as part of the replaced run state (via `replaced_decisions/`).

### 7.2 What happens when PROMOTE/KILL/NME becomes PARK/REVISIT

When a founder replaces a non-parking decision with PARK or REVISIT_LATER:

1. **New record creation:** `build_parking_lot_records()` creates a new `ParkingLotRecord` for the new PARK/REVISIT_LATER decision.
2. **No orphan to clean:** The old decision had no parking lot record (it was PROMOTE/KILL/NME), so no orphan cleanup is needed.
3. **Record merge:** The new record is merged into `parking_lot_records.json` via `_merge_parking_lot_records()`.

### 7.3 Orphaned parking lot records — definition

A `ParkingLotRecord` is **orphaned** when its `source_decision_id` references a `FounderDecisionV2.decision_id` that no longer exists in `founder_decisions_v2.json`.

**Causes of orphans:**
- A PARK/REVISIT_LATER decision was replaced with a non-parking decision.
- A PARK/REVISIT_LATER decision was replaced with another PARK/REVISIT_LATER decision (the old record is orphaned, a new record is created for the new decision).

**Cleanup rule:** Orphaned records are **always removed** during the replace write phase. They are never left in the active `parking_lot_records.json`.

### 7.4 Superseded records

A `ParkingLotRecord` is **superseded** when a new record with a different `record_id` but same `linked_opportunity_id` is created for the same opportunity.

**Policy:**
- Superseded records are **removed** during orphan cleanup (they are identified by `source_decision_id` matching a replaced decision ID).
- Supersession is tracked in `import_history.json`, not in the parking lot file itself.
- The `status` field of parking lot records is `"parked"` or `"revisit_later"` — there is no `"superseded"` status.

### 7.5 Active vs historical records

- **Active records:** Records in `parking_lot_records.json` whose `source_decision_id` references an existing `FounderDecisionV2.decision_id`.
- **Historical records:** Records preserved in `replaced_decisions/` archives.

### 7.6 Deletion vs superseding

- **Deletion is allowed** for orphaned parking lot records (those whose source decision no longer exists).
- **Superseding is preferred** over silent deletion — the replacement is always recorded in `import_history.json`.
- **Active records are never deleted** unless their source decision is explicitly replaced.

---

## 8. Derived Artifact Rebuild Policy

### 8.1 Deterministic rebuild order

When a replace operation triggers derived artifact rebuild, the following order is **mandatory**:

1. **Write** `founder_decisions_v2.json` (primary artifact).
2. **Rebuild and write** `founder_feedback_mappings.json` (derived from decisions).
3. **Rebuild and write** `founder_preference_profile.json` (derived from decisions + mappings).
4. **Cleanup and rebuild** `parking_lot_records.json` (orphan removal from old decisions, rebuild from new decisions).
5. **Update** `manifest.json` (metadata).
6. **Regenerate** `run_report.json` / `run_report.md`.
7. **Regenerate** `dashboard_index.json` / `dashboard.md`.
8. **Write** `replaced_decisions/` archive.
9. **Append** `import_history.json`.

### 8.2 All-or-nothing write policy

- **No partial writes.** If any step in the rebuild sequence fails, no artifacts are written.
- **Pre-validation.** All input decisions are validated before any artifact is touched.
- **Post-validation.** After all artifacts are written, a readback validation confirms artifact integrity.

### 8.3 Temp file / atomic-ish write policy

The current project uses direct `path.write_text()` writes (see [`_write_json()`](../../src/oos/founder_decision_import.py:706-712)). There is no transactional rollback mechanism.

**For v2.8 implementation (item 1.3):**
- Implementers may introduce a `write-then-rename` pattern for atomicity:
  1. Write new content to `{filename}.tmp`.
  2. Validate the `.tmp` file is parseable.
  3. Rename `.tmp` → final filename.
  4. If any `.tmp` file fails validation, delete all `.tmp` files and abort.
- If `write-then-rename` is not feasible, the existing direct-write pattern is acceptable provided:
  - Validation passes before any write.
  - Readback validation passes after all writes.
  - On failure, a clear error message is returned (no silent corruption).

### 8.4 Validation before writing

Before any artifact is written during a replace/amend operation:

1. All input decisions pass `validate_founder_decision_inputs()`.
2. All `FounderDecisionV2` objects pass `validate_founder_decision()`.
3. All `FounderFeedbackMapping` objects pass `validate_founder_feedback_mapping()`.
4. All `FounderPreferenceProfile` objects pass `validate_founder_preference_profile()`.
5. All `ParkingLotRecord` objects pass `ParkingLotRecord.validate()`.
6. Source URL traceability check passes — zero `urn:oos:*` placeholders.
7. Artifact schema versions match canonical versions.

### 8.5 Validation after writing

After all artifacts are written:

1. Readback every written artifact and confirm it is parseable JSON.
2. Confirm `manifest.json` `empty_states` are consistent with artifact contents.
3. Confirm source URL traceability scanner passes (`check_source_url_traceability()` returns `validation_passed=True`).
4. Confirm decision counts match expected values.
5. Confirm no orphaned parking lot records (every `source_decision_id` resolves to an existing `decision_id` in `founder_decisions_v2.json`).

---

## 9. Import History / Audit Trail Schema

### 9.1 `CorrectionEntry` model

Every correction operation produces one or more `CorrectionEntry` records written to `{run_dir}/import_history.json`.

```python
@dataclass(frozen=True)
class CorrectionEntry:
    correction_id: str            # Deterministic ID: sha256 of composite key
    corrected_at: str             # ISO 8601 timestamp
    correction_mode: str          # "replace" | "amend"
    replaced_review_item_ids: list[str]   # review_item_id values targeted
    old_decision_ids: list[str]          # decision_id values before correction
    new_decision_ids: list[str]          # decision_id values after correction
    old_artifact_checksums: dict[str, str]  # {artifact_key: sha256_hex}
    new_artifact_checksums: dict[str, str]  # {artifact_key: sha256_hex}
    warnings: list[str]
    errors: list[str]
    advisory_only: bool           # Always True
    no_live_api: bool             # Always True
    no_live_llm: bool             # Always True
```

### 9.2 `ImportHistoryLog` model

```python
@dataclass
class ImportHistoryLog:
    schema_version: str           # "import_history.v1"
    run_id: str
    entries: list[CorrectionEntry]
```

### 9.3 Fields specification

| Field | Type | Description |
|---|---|---|
| `correction_id` | `str` | Deterministic ID: `correction_{sha256(run_id\|timestamp\|mode\|old_ids\|new_ids)[:12]}` |
| `corrected_at` | `str` | ISO 8601 UTC timestamp of correction operation |
| `correction_mode` | `str` | `"replace"` or `"amend"` |
| `replaced_review_item_ids` | `list[str]` | The `review_item_id` values from the founder's input that triggered the correction |
| `old_decision_ids` | `list[str]` | The `decision_id` values of decisions that were replaced/amended |
| `new_decision_ids` | `list[str]` | The `decision_id` values of decisions after correction |
| `old_artifact_checksums` | `dict[str, str]` | SHA-256 hex digests of affected artifacts before correction (if feasible) |
| `new_artifact_checksums` | `dict[str, str]` | SHA-256 hex digests of affected artifacts after correction (if feasible) |
| `warnings` | `list[str]` | Non-blocking issues encountered during correction |
| `errors` | `list[str]` | Blocking issues (entry only present when correction failed and was rolled back) |
| `advisory_only` | `bool` | Always `true` — no autonomous decisions |
| `no_live_api` | `bool` | Always `true` — no live API calls |
| `no_live_llm` | `bool` | Always `true` — no live LLM calls |

### 9.4 Checksum policy

- **Feasible:** SHA-256 checksums of artifact JSON content (canonicalized — sorted keys, no trailing whitespace).
- **If infeasible** (e.g., artifact too large, performance concern): omit the checksum field and note in `warnings`.
- **Minimum requirement:** `old_decision_ids` and `new_decision_ids` are always populated. Checksums are optional but recommended.

### 9.5 History file location

```
{run_dir}/import_history.json
```

The file is append-only: new entries are appended to the existing `entries` list. Entries are never modified or deleted.

---

## 10. Source URL Traceability Rules

### 10.1 No `urn:oos:*` placeholders

This is a **hard requirement** carried forward from the [Source URL Traceability Contract](source_url_traceability_contract.md) (v2.7 item 1.1).

- After any correction (replace or amend), every `FounderDecisionV2.linked_source_urls` must contain at least one real `http://` or `https://` URL.
- Zero `urn:oos:*` placeholder URNs are permitted.
- The source URL traceability checker (`check_source_url_traceability()`) must pass after correction.

### 10.2 Real `http`/`https` source URLs preserved

- Source URLs are propagated from the inbox index's `linked_source_urls` field.
- If the inbox item has no `linked_source_urls`, the decision import must fail (fail-closed) unless the item is explicitly exempt.
- No synthetic or placeholder URLs are created during correction.

### 10.3 Source URL traceability checker must pass after correction

After a replace or amend operation completes:

```python
from oos.source_url_traceability import check_source_url_traceability

report = check_source_url_traceability(run_dir)
assert report.validation_passed == True
assert report.placeholder_url_count == 0
```

### 10.4 Missing source URLs fail closed

If a correction would result in a decision with empty `linked_source_urls` (and the item is not exempt), the correction is rejected. No artifacts are written.

### 10.5 Exemption policy

The only exemption from the source URL requirement is:
- Items whose inbox `linked_source_urls` is empty **and** the item has a documented `empty_source_urls_reason` field.

This exemption is narrow and must be explicitly justified by the founder.

---

## 11. Failure Modes

### 11.1 Validation failure before writes

| Failure | Result | Artifacts affected |
|---|---|---|
| Unknown `review_item_id` in replace list | Batch rejected | None |
| Invalid decision value | Batch rejected | None |
| Invalid reason categories | Batch rejected | None |
| Duplicate `review_item_id` in input | Batch rejected | None |
| Source URL placeholder detected | Batch rejected | None |
| Missing source URLs (non-exempt) | Batch rejected | None |
| Decision value mismatch in amend mode | Batch rejected | None |
| Existing decision not found in amend mode | Batch rejected | None |

### 11.2 Write-time failure

| Failure | Result | Artifacts affected |
|---|---|---|
| Disk full | Abort; any `.tmp` files deleted | None (if atomic-ish) or partial (if direct write) |
| Permission denied | Abort | None (if pre-checked) |
| JSON serialization error | Batch rejected before any write | None |
| Rebuild function exception | Batch rejected before any write | None |

### 11.3 Post-write validation failure

| Failure | Result | Recovery |
|---|---|---|
| Artifact not parseable | Error returned; run state may be inconsistent | Founder must restore from `replaced_decisions/` |
| Source URL check fails | Error returned | Founder must provide valid source URLs |
| Orphaned parking lot record detected | Error returned | Implementation bug — must not happen if cleanup is correct |

### 11.4 Fail-closed guarantee

**Primary rule:** If any validation check fails before writes begin, no artifacts are written. The original state is untouched.

**Secondary rule:** If a write-time failure occurs, the system must:
- Attempt to leave artifacts in their pre-correction state (if atomic-ish writes are implemented).
- Report the failure clearly with the affected artifact paths.
- Never silently corrupt artifacts.

---

## 12. Acceptance Criteria for Implementation Items 1.2 and 1.3

### 12.1 For item 1.2 (parking lot cleanup + rebuild model)

1. `cleanup_orphaned_parking_lot_records()` correctly removes records whose `source_decision_id` matches replaced decision IDs.
2. Unrelated parking lot records are untouched.
3. `build_parking_lot_records_for_decisions()` produces identical records to existing `build_parking_lot_records()` for equivalent input.
4. Rebuild model is deterministic: same input decisions → same derived artifacts.
5. Rebuild model is fail-closed: any inconsistency in input → no writes.
6. Feedback mappings rebuild correctly after replacing a decision.
7. Preference profile rebuilds correctly after replacing a decision.
8. Source URL traceability is preserved through all rebuild paths.

### 12.2 For item 1.3 (replace/amend implementation)

1. `--replace-review-items` flag exists and targets only listed `review_item_id` values.
2. `--amend-notes-only` flag exists and updates only `notes` (and optionally `reason_categories`).
3. Replace mode archives old decisions to `replaced_decisions/`.
4. Replace mode cleans up orphaned parking lot records.
5. Replace mode rebuilds feedback mappings, preference profile, and parking lot records.
6. Amend mode does **not** change decision values.
7. Amend mode does **not** rebuild downstream artifacts.
8. Manifest records `replaced_decision_ids` and `amended_decision_ids`.
9. Run report and dashboard are regenerated after replace/amend.
10. Fail-closed: any invalid input → no writes.
11. All-or-nothing: batch succeeds or fails entirely.
12. Idempotent: same input twice → same state.
13. Source URL traceability passes after every correction.
14. All 13 safety requirements (R1–R13) from the v2.7 re-import policy are satisfied.

---

## 13. Non-Goals

This contract does **not**:

1. Implement replace/amend behavior (deferred to item 1.3).
2. Add CLI flags (deferred to item 1.3).
3. Modify `founder_decision_import.py`, `cli.py`, `parking_lot.py`, or any source file.
4. Perform portfolio transitions.
5. Make live API or LLM calls.
6. Interpret founder intent automatically.
7. Add a database, UI, or persistent server.
8. Implement undo/rollback of corrections (v2.9+ candidate).
9. Implement batch correction across multiple runs (v2.9+ candidate).
10. Implement `--replace-all` mode (deferred; documented in Section 4.4).
11. Change the existing import contract for non-replace/non-amend paths.

---

## 14. Open Questions / Deferred Items

| # | Question / Item | Disposition |
|---|---|---|
| 1 | Should `amend-notes-only` also allow amending `reason_categories`? | Yes — if reason categories change but decision value stays the same, this is still an amend. The contract allows optional `reason_categories` update in amend mode. |
| 2 | Should replaced parking lot records be archived separately? | They are implicitly archived as part of the `replaced_decisions/` snapshot. No separate parking-lot-only archive is needed. |
| 3 | What happens if `run_report.json`/`dashboard_index.json` don't exist yet when correction occurs? | The correction operation should regenerate them. If they don't exist, create them. |
| 4 | Should `import_history.json` be included in the manifest? | Yes — it should be added to `manifest.json` as an artifact reference once implemented (item 2.1). |
| 5 | Should checksums be mandatory? | Recommended but not mandatory for v2.8. If omitted, note in `warnings`. |
| 6 | What is the `empty_source_urls_reason` field for inbox items without URLs? | To be designed in item 1.3. The inbox item must carry an explicit reason string when `linked_source_urls` is empty. |
| 7 | Should the `CorrectionEntry` model be in `import_history.py` or `founder_decision_import.py`? | In `import_history.py` (item 2.1). The import module will call `record_correction_history()`. |
| 8 | Do we need a pre-correction snapshot of all artifacts? | The `replaced_decisions/` archive serves this purpose for replace mode. For amend mode, only the old notes are archived. |

---

## Appendix A: Safety Requirements Traceability (R1–R13)

This section traces each safety requirement from the [v2.7 re-import policy](../decisions/founder_decision_reimport_policy.md) to this contract.

| # | Requirement | Contract Section | Status |
|---|---|---|---|
| **R1** | Explicit CLI flag required | Section 4 (Correction Modes) — `--replace-review-items`, `--amend-notes-only` | Covered |
| **R2** | Fail-closed | Section 11 (Failure Modes), Section 8.2 (All-or-nothing) | Covered |
| **R3** | All-or-nothing | Section 8.2 | Covered |
| **R4** | Source URL traceability preserved | Section 10 | Covered |
| **R5** | All downstream artifacts rebuilt deterministically | Section 8 (Derived Artifact Rebuild Policy) | Covered |
| **R6** | No portfolio mutation | Section 4 (advisory_only=True throughout) | Covered |
| **R7** | No decision inference | Section 4.2 (only listed review_item_ids targeted) | Covered |
| **R8** | No silent deletion of unrelated decisions | Section 4.2 (only listed review_item_ids targeted) | Covered |
| **R9** | Clear import result/report | Section 9 (Import History / Audit Trail) | Covered |
| **R10** | Idempotent | Section 4.2, 4.3 | Covered |
| **R11** | Archival of replaced decisions | Section 4.2 (replaced_decisions/), Section 4.3 (amended_decisions/) | Covered |
| **R12** | Parking lot records cleaned up | Section 7 (Parking Lot Orphan / Supersession Policy) | Covered |
| **R13** | Tested with before/after artifacts | Section 12 (Acceptance Criteria) — deferred to items 1.2/1.3 | Deferred to implementation |

---

## Appendix B: Artifact Checksum Reference

For `old_artifact_checksums` and `new_artifact_checksums` in the audit trail, the following artifacts are in scope:

| Artifact Key | File | Checksum of |
|---|---|---|
| `founder_decisions_v2` | `founder_decisions_v2.json` | Canonicalized JSON (sorted keys, no trailing whitespace) |
| `founder_feedback_mappings` | `founder_feedback_mappings.json` | Canonicalized JSON |
| `founder_preference_profile` | `founder_preference_profile.json` | Canonicalized JSON |
| `parking_lot_records` | `parking_lot_records.json` | Canonicalized JSON |
| `manifest` | `manifest.json` | Canonicalized JSON |

Checksum algorithm: `hashlib.sha256(content.encode("utf-8")).hexdigest()`.

---

## Appendix C: Self-Audit

| Question | Answer |
|---|---|
| Did this avoid implementation? | **Yes.** Contract/advisory only. No `.py` files modified. |
| Did this avoid source/test changes? | **Yes.** No source or test files changed. |
| Did this define replace/amend semantics clearly? | **Yes.** Section 4 defines all four modes with trigger, behavior, and constraints. |
| Did this define artifact integrity rules? | **Yes.** Section 6 covers all 8 derived artifacts with replace and amend behaviors. |
| Did this preserve founder-control/advisory-only assumptions? | **Yes.** `advisory_only=True`, `founder_decision_authority="founder_decision_record_only"`, no autonomous decisions. |
| Did this avoid live APIs/LLMs? | **Yes.** `no_live_api=True`, `no_live_llm=True` throughout. |
| Did this address all 13 safety requirements (R1–R13)? | **Yes.** Appendix A traces each requirement. |
| Did this define parking lot integrity policy? | **Yes.** Section 7 covers orphans, supersession, active/historical, and deletion policy. |
| Did this define import history/audit schema? | **Yes.** Section 9 defines `CorrectionEntry` and `ImportHistoryLog` models. |
| Did this define source URL traceability guarantee? | **Yes.** Section 10 enforces zero placeholder URNs post-correction. |
