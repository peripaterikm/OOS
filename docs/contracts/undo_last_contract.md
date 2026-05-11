# OOS Undo-Last Contract

**Roadmap:** v2.10
**Item:** 1.1 — Undo-Last Contract Finalization
**Status:** Contract finalized / implementation pending
**Depends on:**
- [`docs/decisions/correction_rollback_undo_policy.md`](../decisions/correction_rollback_undo_policy.md) (v2.9 item 3.1 — policy review)
- [`docs/contracts/founder_decision_correction_artifact_contract.md`](founder_decision_correction_artifact_contract.md) (v2.8 item 1.1 — correction artifact contract)
- [`docs/contracts/source_url_traceability_contract.md`](source_url_traceability_contract.md) (v2.7 item 1.1)
- [`docs/contracts/output_mode_contract.md`](output_mode_contract.md) (v2.9 item 1.1)
- [`docs/decisions/replace_all_mode_policy.md`](../decisions/replace_all_mode_policy.md) (v2.9 item 3.2 — for replace_all forward compatibility)
**Precedes:**
- Roadmap v2.10 item 2.1 — Undo-Last Implementation
- Roadmap v2.10 item 3.1 — Undo-Last Validation and Smoke Coverage

---

## 1. Purpose

This contract translates the 12 safety requirements (U-R1 through U-R12) from the [Correction Rollback / Undo Policy](../decisions/correction_rollback_undo_policy.md) into an **implementation-ready specification** for the `--undo-last` correction mode. It defines exact artifact write order, the `CorrectionEntry` schema for `correction_mode = "undo"`, manifest fields, CLI output expectations, fail-closed cases, idempotency behavior, and source URL traceability requirements.

This document is **contract-first**. It does **not** implement any behavior. It serves as the acceptance criteria for Roadmap v2.10 implementation items 2 (implementation) and 3 (validation).

---

## 2. Scope

### 2.1 Implemented mode: U1 (`--undo-last`) only

| Property | Value |
|---|---|
| Mode | U1 — undo most recent correction |
| CLI flag | `--undo-last` |
| Command target | `import-founder-decisions-v2` |
| Scope | Exactly one `CorrectionEntry` — the most recent non-undo entry in `import_history.json` |
| Multi-step undo | **Excluded.** Only the most recent correction can be undone. |
| Run-level undo (`--undo-run`) | **Excluded.** Requires pre-correction snapshots; v2.11+. |
| Restore-archived (`--restore-archived`) | **Excluded.** Manual, error-prone mode; not recommended per policy. |
| Autonomous portfolio transitions | **Excluded.** `advisory_only=True` throughout. |
| Live APIs/LLMs | **Excluded.** All logic deterministic and local. |

### 2.2 Supported correction modes for undo

| Correction mode of last entry | Undo supported? | Behavior |
|---|---|---|
| `"replace"` | **Yes** | Restore old decisions from `replaced_decisions/`; remove replacement decisions; rebuild derived artifacts. |
| `"amend"` | **Yes** | Restore old notes from `amended_decisions/`; no derived artifact rebuild. |
| `"replace_all"` | **Future compatibility** | Defined in Section 9.3 for implementation when `--replace-all` gate passes (Roadmap v2.10 item 5). Until then, if a `replace_all` entry is encountered, undo-last **must reject with a clear message** that `replace_all` undo is not yet implemented. |
| Unknown `correction_mode` | **Rejected (fail-closed)** | Any unrecognized `correction_mode` value → undo rejected with error listing the unknown mode. |

---

## 3. Safety Requirements Mapping

This section maps each safety requirement from the policy document (Section 7, U-R1 through U-R12) to concrete contract behavior.

| # | Requirement | Contract Behavior |
|---|---|---|
| **U-R1** | Explicit CLI flag required | `--undo-last` must be explicitly passed to `import-founder-decisions-v2`. No implicit undo. The flag is mutually exclusive with `--replace-review-items`, `--amend-notes-only`, and `--replace-all`. |
| **U-R2** | Fail-closed | If any validation step fails (missing history, missing archive, corrupt archive, source URL regression, rebuild failure), **no artifacts are written**. Original state is untouched. |
| **U-R3** | All-or-nothing | Undo either fully succeeds (all artifacts written, audit appended, manifest updated) or fully fails (no artifacts touched). No partial state. |
| **U-R4** | Append-only audit | A new `CorrectionEntry` with `correction_mode = "undo"` is appended to `import_history.json`. Existing entries are **never modified or deleted**. |
| **U-R5** | No silent deletion | Old decisions remain in `replaced_decisions/` or `amended_decisions/` archives. The correction entry being undone is **not** deleted — a new undo entry is appended. |
| **U-R6** | No portfolio mutation | `advisory_only=True` on all undo operations. `no_live_api=True`. `no_live_llm=True`. |
| **U-R7** | No autonomous inference | The system reads the most recent non-undo `CorrectionEntry` from `import_history.json`. It does not guess which correction to undo or which decisions to restore. |
| **U-R8** | Source URL traceability preserved | After undo, every `FounderDecisionV2.linked_source_urls` must contain real `http`/`https` URLs. `placeholder_count = 0`. `missing_count = 0`. Source URL traceability check must pass before undo is considered complete. |
| **U-R9** | Deterministic | Same input state + same `--undo-last` invocation yields identical artifact checksums. Undo is a pure function of the current artifact state. |
| **U-R10** | Undo-last only (single-step) | Only the most recent non-undo `CorrectionEntry` (by `corrected_at`) can be undone. Multi-step undo is v2.11+. |
| **U-R11** | Derived artifacts rebuilt | After undo-replace: feedback mappings, preference profile, and parking lot records must be consistent with restored decisions. After undo-amend: no rebuild needed (notes-only change). |
| **U-R12** | Archive integrity verified | Before restoring, the relevant archive file (`replaced_decisions/` or `amended_decisions/`) must exist, be readable, and contain valid JSON matching the `old_decision_ids` or `old_artifact_checksums` from the `CorrectionEntry`. If not, undo is rejected. |

---

## 4. Artifact Model

### 4.1 Artifacts affected by undo-last

| # | Artifact | Classification | Undo would need to |
|---|---|---|---|
| 1 | `founder_decisions_v2.json` | Primary | Restore old decisions from archive; remove replacement decisions (replace/replace_all); restore old notes (amend). |
| 2 | `founder_feedback_mappings.json` | Derived | Full rebuild from restored decisions (replace/replace_all). No change (amend). |
| 3 | `founder_preference_profile.json` | Derived | Full rebuild from restored decisions + mappings (replace/replace_all). No change (amend). |
| 4 | `parking_lot_records.json` | Derived | Orphan cleanup of replacement parking records + rebuild from restored decisions (replace/replace_all). No change (amend). |
| 5 | `manifest.json` | Metadata | Record `undone_decision_ids`, `undone_at`, `undone_correction_id`, `undo_result_summary`. |
| 6 | `run_report.json` / `run_report.md` | Derived | Regenerate with undo summary (replace/replace_all/amend). |
| 7 | `dashboard_index.json` / `dashboard.md` | Derived | Regenerate with `[UNDONE]` indicator (replace/replace_all/amend). |
| 8 | `import_history.json` | Audit | Append new `CorrectionEntry` with `correction_mode = "undo"`. Existing entries never modified. |
| 9 | `replaced_decisions/` | Archive | **Read** old decisions (replace/replace_all undo). Never written during undo. |
| 10 | `amended_decisions/` | Archive | **Read** old notes (amend undo). Never written during undo. |

### 4.2 Artifact state before undo

The following artifacts must exist before undo-last can proceed:

| Artifact | Required? | Validation |
|---|---|---|
| `import_history.json` | **Yes** | Must exist, be non-empty, and contain at least one non-undo `CorrectionEntry`. |
| `founder_decisions_v2.json` | **Yes** | Must exist and be parseable. |
| `replaced_decisions/` | **Conditional** | Required if undoing a `replace` or `replace_all` entry. Must contain the archive file referenced by `old_artifact_checksums` or `old_decision_ids`. |
| `amended_decisions/` | **Conditional** | Required if undoing an `amend` entry. Must contain the archive file with old notes. |
| `manifest.json` | **Yes** | Must exist and be parseable. |
| `founder_feedback_mappings.json` | **Yes** | Must exist (may be empty `"empty": true`). |
| `founder_preference_profile.json` | **Yes** | Must exist (may be empty `"empty": true`). |
| `parking_lot_records.json` | **Yes** | Must exist (may be empty `"empty": true`). |

### 4.3 What undo-last does NOT create or touch

- Does **not** create new archive files in `replaced_decisions/` or `amended_decisions/`.
- Does **not** modify any existing `CorrectionEntry` in `import_history.json`.
- Does **not** modify the inbox index (`founder_inbox_v2_index.json`).
- Does **not** modify any upstream artifacts (signals, evidence packs, opportunity candidates, quality gate outputs).
- Does **not** call the weekly cycle pipeline.

---

## 5. Artifact Write Order

### 5.1 General write-order principle

All undo paths follow the same structural pattern as the replace-mode write path defined in the [correction artifact contract](founder_decision_correction_artifact_contract.md) Section 8.1, but reversed in direction: old decisions become active, replacement decisions are removed.

**Mandatory pre-write validation sequence (all modes):**
1. Read `import_history.json` — confirm it exists and is non-empty.
2. Find the most recent non-undo `CorrectionEntry` by `corrected_at`.
3. If the most recent entry has `correction_mode = "undo"`, reject: "Most recent correction already undone."
4. Identify `correction_mode` of the target entry.
5. Validate the relevant archive exists and is parseable.
6. Validate archive content matches `old_decision_ids` from the `CorrectionEntry`.
7. Validate that source URL traceability can pass after undo (pre-check).
8. If any validation fails, abort with no writes.

**Mandatory post-write validation (all modes):**
1. Readback every written artifact and confirm parseable JSON.
2. Run `check_source_url_traceability()` — must return `validation_passed=True`, `placeholder_count=0`, `missing_count=0`.
3. Confirm decision counts match expected values.
4. Confirm no orphaned parking lot records.
5. If any post-write validation fails, the implementation should report the error. Since true transactional rollback is not available, the implementation must validate pre-write to minimize post-write failure risk.

### 5.2 Write order: undo of `replace`

```
PHASE 0 — VALIDATE (no writes)
  import_history.json          READ   — find most recent non-undo CorrectionEntry
  replaced_decisions/          READ   — confirm archive exists and is parseable
  founder_decisions_v2.json    READ   — confirm current state is parseable
  source URL traceability      CHECK  — pre-check that restored decisions will pass

PHASE 1 — RESTORE PRIMARY
  founder_decisions_v2.json    WRITE  — merge: remove decisions with new_decision_ids,
                                        insert decisions from replaced_decisions/ archive

PHASE 2 — REBUILD DERIVED
  founder_feedback_mappings.json      REBUILD + WRITE  — from restored decisions
  founder_preference_profile.json     REBUILD + WRITE  — from restored decisions + mappings
  parking_lot_records.json            CLEANUP + REBUILD + WRITE
    — Remove records whose source_decision_id matches any new_decision_ids (orphan cleanup)
    — Add records for restored PARK/REVISIT_LATER decisions

PHASE 3 — UPDATE METADATA
  manifest.json                UPDATE  — set undone_decision_ids, undone_at,
                                        undone_correction_id, undo_result_summary

PHASE 4 — REGENERATE REPORTS
  run_report.json / .md        REGENERATE  — include undo summary section
  dashboard_index.json / .md   REGENERATE  — include [UNDONE] indicator

PHASE 5 — APPEND AUDIT
  import_history.json          APPEND  — new CorrectionEntry with correction_mode = "undo"

PHASE 6 — POST-VALIDATE
  All written artifacts        READBACK — confirm parseable
  Source URL traceability      CHECK    — must pass (placeholder_count=0, missing_count=0)
  Parking lot integrity        CHECK    — no orphaned records
```

### 5.3 Write order: undo of `amend`

```
PHASE 0 — VALIDATE (no writes)
  import_history.json          READ   — find most recent non-undo CorrectionEntry
  amended_decisions/           READ   — confirm archive exists and is parseable
  founder_decisions_v2.json    READ   — confirm target decision exists

PHASE 1 — RESTORE NOTES
  founder_decisions_v2.json    WRITE  — restore old notes from amended_decisions/ archive
                                        to the matching decision by decision_id

PHASE 2 — UPDATE METADATA
  manifest.json                UPDATE — set undone_decision_ids, undone_at,
                                       undone_correction_id, undo_result_summary

PHASE 3 — REGENERATE REPORTS
  run_report.json / .md        REGENERATE — include undo summary section
  dashboard_index.json / .md   REGENERATE — include [UNDONE] indicator

PHASE 4 — APPEND AUDIT
  import_history.json          APPEND — new CorrectionEntry with correction_mode = "undo"

PHASE 5 — POST-VALIDATE
  All written artifacts        READBACK — confirm parseable
  Source URL traceability      CHECK    — must pass (placeholder_count=0, missing_count=0)

Note: amend undo does NOT rebuild derived artifacts (feedback mappings, preference profile,
parking lot records). Amend mode only changes notes, which are not inputs to derived artifacts.
```

### 5.4 Write order: undo of `replace_all` (future compatibility)

```
This write order is defined for forward compatibility when --replace-all is implemented
(Roadmap v2.10 item 5, gated by item 4).

Until replace_all is implemented: if the most recent correction_mode is "replace_all",
undo-last MUST reject with:
  "Undo of replace_all correction is not yet implemented. This capability
   will be available when Roadmap v2.10 item 5 (replace-all implementation) passes
   the readiness gate (item 4)."

PHASE 0 — VALIDATE (no writes)
  import_history.json          READ   — find most recent non-undo CorrectionEntry
  replaced_decisions/          READ   — confirm full-decision-set archive exists and is parseable
  founder_decisions_v2.json    READ   — confirm current state is parseable
  source URL traceability      CHECK  — pre-check that restored full set will pass

PHASE 1 — RESTORE PRIMARY
  founder_decisions_v2.json    WRITE  — replace entire decision set with archived decisions

PHASE 2 — REBUILD DERIVED
  founder_feedback_mappings.json      REBUILD + WRITE  — full rebuild from restored decisions
  founder_preference_profile.json     REBUILD + WRITE  — full rebuild
  parking_lot_records.json            CLEANUP + REBUILD + WRITE
    — Remove all records whose source_decision_id is not in restored decisions
    — Rebuild from restored decisions

PHASE 3 — UPDATE METADATA
  manifest.json                UPDATE  — set undone_decision_ids, undone_at,
                                        undone_correction_id, undo_result_summary

PHASE 4 — REGENERATE REPORTS
  run_report.json / .md        REGENERATE
  dashboard_index.json / .md   REGENERATE  — include [UNDONE] indicator

PHASE 5 — APPEND AUDIT
  import_history.json          APPEND  — new CorrectionEntry with correction_mode = "undo"

PHASE 6 — POST-VALIDATE
  (same as replace undo post-validation)
```

### 5.5 Failure rollback / fail-closed behavior

- **Pre-write validation failure:** No artifacts written. Error message returned. Exit code non-zero.
- **Write-time failure (disk full, permission denied):** The implementation must validate pre-conditions thoroughly to minimize this risk. If a write-time failure occurs, the system reports the failure with affected artifact paths. Since true transactional rollback is not available in the current file-system architecture, the pre-write validation is the primary safety mechanism.
- **Post-write validation failure:** Error returned with details. The system reports which artifact failed validation. The founder may need to manually restore from `replaced_decisions/`.
- **No partial writes are allowed:** The implementation must structure writes so that all artifact content is prepared and validated in-memory before any file is written.

---

## 6. CorrectionEntry Schema for Undo

### 6.1 Extended `CorrectionEntry` model

The existing `CorrectionEntry` model (defined in [`founder_decision_correction_artifact_contract.md`](founder_decision_correction_artifact_contract.md) Section 9.1) must be extended to support `correction_mode = "undo"`. The base fields are preserved; undo-specific fields are added.

```python
@dataclass(frozen=True)
class CorrectionEntry:
    # === Base fields (unchanged from v2.8) ===
    correction_id: str            # Deterministic ID: sha256 of composite key
    corrected_at: str             # ISO 8601 UTC timestamp
    correction_mode: str          # "replace" | "amend" | "undo" | "replace_all" (future)

    # === Replace/amend fields (populated when correction_mode is "replace" or "amend") ===
    replaced_review_item_ids: list[str]   # review_item_id values targeted
    old_decision_ids: list[str]          # decision_id values before correction
    new_decision_ids: list[str]          # decision_id values after correction
    old_artifact_checksums: dict[str, str]  # {artifact_key: sha256_hex}
    new_artifact_checksums: dict[str, str]  # {artifact_key: sha256_hex}
    warnings: list[str]
    errors: list[str]

    # === Safety flags (always populated) ===
    advisory_only: bool           # Always True
    no_live_api: bool             # Always True
    no_live_llm: bool             # Always True

    # === Undo-specific fields (populated when correction_mode = "undo") ===
    undone_correction_id: str | None        # correction_id of the entry being undone
    undone_correction_mode: str | None      # "replace" | "amend" | "replace_all"
    undone_decision_ids: list[str] | None   # decision_ids restored by this undo
    undone_at: str | None                   # ISO 8601 UTC timestamp (redundant with corrected_at but explicit)
    source_history_entry_index: int | None  # 0-based index in import_history.json entries list
    archive_refs: dict[str, str] | None     # {archive_type: archive_file_path} — e.g.,
                                            # {"replaced_decisions": "replaced_decisions/founder_decisions_v2_replaced_2026-05-10T12...json"}
    source_url_traceability_result: dict | None  # Snapshot of source URL traceability check after undo
                                            # {"validation_passed": true/false, "placeholder_count": N, "missing_count": N}
    notes: list[str] | None                 # Human-readable summary of what was undone
```

### 6.2 Undo-specific field specifications

| Field | Type | Required for undo? | Description |
|---|---|---|---|
| `correction_id` | `str` | **Yes** | Deterministic hash: `undo_{sha256(run_id + corrected_at + undone_correction_id + undone_decision_ids)[:16]}` |
| `corrected_at` | `str` | **Yes** | ISO 8601 UTC timestamp when undo was executed. |
| `correction_mode` | `str` | **Yes** | Must be `"undo"`. |
| `undone_correction_id` | `str` | **Yes** | The `correction_id` of the `CorrectionEntry` being undone. |
| `undone_correction_mode` | `str` | **Yes** | The `correction_mode` of the entry being undone (`"replace"`, `"amend"`, or `"replace_all"`). |
| `undone_decision_ids` | `list[str]` | **Yes** | The `decision_id` values of decisions restored by this undo. For amend undo, the decision ID whose notes were restored. |
| `undone_at` | `str` | **Yes** | ISO 8601 UTC timestamp — same as `corrected_at`, explicit for clarity. |
| `source_history_entry_index` | `int` | **Yes** | 0-based index of the undone entry in `import_history.json` `entries` list at the time of undo. |
| `archive_refs` | `dict[str, str]` | **Yes** | Maps archive type key to relative file path. Keys: `"replaced_decisions"` or `"amended_decisions"`. Values: archive file path relative to run directory. |
| `source_url_traceability_result` | `dict` | **Yes** | Snapshot of `check_source_url_traceability()` output after undo. Must show `validation_passed=True`, `placeholder_count=0`, `missing_count=0`. |
| `notes` | `list[str]` | **No** | Human-readable summary. Recommended for operational clarity. |
| `advisory_only` | `bool` | **Yes** | Always `True`. |
| `no_live_api` | `bool` | **Yes** | Always `True`. |
| `no_live_llm` | `bool` | **Yes** | Always `True`. |

### 6.3 Fields NOT populated for undo entries

When `correction_mode = "undo"`, the following base fields are set to empty/zero values:
- `replaced_review_item_ids`: `[]` (not applicable)
- `old_decision_ids`: `[]` (use `undone_decision_ids` instead)
- `new_decision_ids`: `[]` (not applicable — undo restores old decisions)
- `old_artifact_checksums`: `{}` (use `archive_refs` instead)
- `new_artifact_checksums`: `{}` (artifacts after undo are checksummed in post-validation)

### 6.4 Correction ID determinism

The `correction_id` for undo entries is computed as:

```
undo_{sha256(run_id || corrected_at || undone_correction_id || joined(undone_decision_ids, ","))[:16]}
```

Where:
- `run_id` is from `manifest.json`
- `corrected_at` is the ISO 8601 timestamp of the undo operation
- `undone_correction_id` is the `correction_id` of the entry being undone
- `joined(undone_decision_ids, ",")` is the comma-joined, sorted list of restored decision IDs

This ensures idempotency: undoing the same correction twice with the same state produces the same `correction_id`.

---

## 7. Manifest Fields

### 7.1 Required manifest additions for undo

The following fields must be added to or updated in `manifest.json` after a successful undo:

| Field | Type | Description |
|---|---|---|
| `undone_decision_ids` | `list[str]` | The `decision_id` values restored by this undo operation. For amend undo, a single-element list with the amended decision's ID. |
| `undone_at` | `str` | ISO 8601 UTC timestamp when the undo was executed. |
| `undone_correction_id` | `str` | The `correction_id` of the `CorrectionEntry` that was undone. |
| `undo_result_summary` | `dict` | Structured summary of the undo operation: |

```python
{
    "undo_mode": "undo_last",                    # Always "undo_last" for v2.10
    "undone_correction_mode": "replace",         # "replace" | "amend" | "replace_all"
    "undone_correction_id": "correction_abc123", # The undone entry's correction_id
    "restored_decision_count": 3,                # Number of decisions restored
    "removed_decision_count": 3,                 # Number of replacement decisions removed (0 for amend)
    "derived_artifacts_rebuilt": True,           # True for replace/replace_all; False for amend
    "source_url_traceability_passed": True,      # Must be True
    "source_url_placeholder_count": 0,           # Must be 0
    "source_url_missing_count": 0,               # Must be 0
}
```

### 7.2 Existing manifest fields preserved

All existing manifest fields are preserved unchanged:
- `run_id`, `run_started_at`, `run_completed_at`
- `schema_versions`
- `empty_states` (updated to reflect post-undo state)
- `replaced_decision_ids`, `replaced_at` (from previous replace operations — preserved in history)
- `amended_decision_ids`, `amended_at` (from previous amend operations — preserved in history)
- `advisory_only` (remains `true`)

### 7.3 Manifest field update timing

Manifest fields are updated in Phase 3 of the write order (Section 5), after the primary artifact is restored and derived artifacts are rebuilt, but before report regeneration and audit append.

---

## 8. Undo Behavior by Correction Type

### 8.1 Undo of `replace`

**Pre-conditions:**
- The most recent non-undo `CorrectionEntry` has `correction_mode = "replace"`.
- `replaced_decisions/` archive file exists and contains valid decisions matching `old_decision_ids`.
- `founder_decisions_v2.json` contains decisions matching `new_decision_ids`.

**Behavior:**
1. Read the archived decisions from `replaced_decisions/` archive file.
2. Validate that archived decisions match `old_decision_ids` from the `CorrectionEntry`.
3. Read current `founder_decisions_v2.json`.
4. Remove decisions whose `decision_id` matches any `new_decision_ids`.
5. Insert restored decisions from the archive.
6. Write updated `founder_decisions_v2.json`.
7. Rebuild `founder_feedback_mappings.json` from restored decisions.
8. Rebuild `founder_preference_profile.json` from restored decisions + mappings.
9. Cleanup + rebuild `parking_lot_records.json`:
   - Remove records whose `source_decision_id` matches any `new_decision_ids` (orphan cleanup).
   - Rebuild parking lot records for restored PARK/REVISIT_LATER decisions.
10. Update `manifest.json` with undo fields.
11. Regenerate `run_report.json` / `run_report.md` with undo summary.
12. Regenerate `dashboard_index.json` / `dashboard.md` with `[UNDONE]` indicator.
13. Append undo `CorrectionEntry` to `import_history.json`.
14. Verify source URL traceability passes.

**Parking lot edge cases:**
- If a replaced decision was KILL → the new decision was PROMOTE → undo restores KILL. No parking lot impact (neither was PARK/REVISIT_LATER).
- If a replaced decision was PARK → the new decision was PROMOTE → undo restores PARK. The parking lot record for the PROMOTE decision is orphaned (removed). A new parking lot record is created for the restored PARK decision.
- If a replaced decision was PROMOTE → the new decision was PARK → undo restores PROMOTE. The parking lot record for the PARK decision is orphaned (removed). No new parking lot record is created (PROMOTE is not a parking decision).
- Parking lot cleanup uses the same `cleanup_orphaned_parking_lot_records()` function as replace mode (from [`decision_correction_rebuild.py`](../../src/oos/decision_correction_rebuild.py)).

**Source URL traceability:**
- Restored decisions carry their original `linked_source_urls` from the archive.
- These URLs were validated during the original replace operation.
- The post-undo traceability check confirms no `urn:oos:*` placeholders and `missing_count = 0`.

### 8.2 Undo of `amend`

**Pre-conditions:**
- The most recent non-undo `CorrectionEntry` has `correction_mode = "amend"`.
- `amended_decisions/` archive file exists and contains valid old notes matching `old_decision_ids`.
- The amended decision still exists in `founder_decisions_v2.json` with its decision value unchanged.

**Behavior:**
1. Read the archived notes from `amended_decisions/` archive file.
2. Validate that archived notes match `old_decision_ids` from the `CorrectionEntry`.
3. Read current `founder_decisions_v2.json`.
4. Locate the decision by `decision_id` (from `old_decision_ids`).
5. Restore the old `notes` field (and optionally `reason_categories`) from the archive.
6. Write updated `founder_decisions_v2.json`.
7. **Do not** rebuild feedback mappings, preference profile, or parking lot records.
8. Update `manifest.json` with undo fields.
9. Regenerate `run_report.json` / `run_report.md` with undo summary (notes restored, no decision change).
10. Regenerate `dashboard_index.json` / `dashboard.md` with `[UNDONE]` indicator.
11. Append undo `CorrectionEntry` to `import_history.json`.
12. Verify source URL traceability passes (should be unchanged from pre-undo state).

**Why no derived artifact rebuild for amend undo:**
- Amend mode only changes `notes` and optionally `reason_categories`.
- Feedback mappings, preference profiles, and parking lot records are derived from decision **values** (PROMOTE, PARK, KILL, NEEDS_MORE_EVIDENCE), not from notes.
- Since amend does not change decision values, amend undo does not change decision values either.
- Therefore, derived artifacts remain consistent without rebuild.

**Audit trail preservation:**
- The original amend `CorrectionEntry` remains in `import_history.json`.
- A new undo `CorrectionEntry` is appended.
- The full sequence is reconstructable: original import → amend → undo-amend.

### 8.3 Undo of `replace_all` (future compatibility)

**Status:** Implementation-pending until Roadmap v2.10 item 5 (replace-all implementation) passes the readiness gate (item 4).

**Pre-conditions (when implemented):**
- The most recent non-undo `CorrectionEntry` has `correction_mode = "replace_all"`.
- `replaced_decisions/` archive file exists and contains the full pre-replacement decision set.
- The archive file is validated for completeness (all expected decision IDs present).

**Behavior (when implemented):**
1. Read the full archived decision set from `replaced_decisions/` archive.
2. Validate completeness: every `old_decision_ids` entry from the `CorrectionEntry` is present in the archive.
3. Replace the entire `founder_decisions_v2.json` with the archived decision set.
4. Full rebuild of `founder_feedback_mappings.json`.
5. Full rebuild of `founder_preference_profile.json`.
6. Full cleanup + rebuild of `parking_lot_records.json`.
7. Update `manifest.json` with undo fields.
8. Regenerate reports and dashboard.
9. Append undo `CorrectionEntry` to `import_history.json`.
10. Verify source URL traceability passes.

**Until replace_all is implemented:** If a `replace_all` entry is encountered as the most recent correction, undo-last must reject with a clear message and exit code 1. The error message must state that `replace_all` undo is not yet available and reference Roadmap v2.10 item 5.

---

## 9. CLI Behavior

### 9.1 Command invocation

```
import-founder-decisions-v2 --undo-last [--run-dir <path>] [--utf8]
```

| Flag | Required | Description |
|---|---|---|
| `--undo-last` | **Yes** | Triggers U1 undo mode. |
| `--run-dir` | No | Path to run directory. Defaults to the most recent run directory. |
| `--utf8` | No | Use Unicode symbols in terminal output. Default is ASCII-safe. |

### 9.2 Mutual exclusion

`--undo-last` is mutually exclusive with:
- `--replace-review-items`
- `--amend-notes-only`
- `--replace-all`
- `--decisions-file` (undo does not accept a new decisions file)

If any of these flags is combined with `--undo-last`, the command must exit with error code 2 and a message listing the conflicting flags.

### 9.3 Success output (ASCII-safe default)

```
Undo-last correction: OK

Undone correction:
  correction_id:   correction_abc123def456
  correction_mode: replace
  corrected_at:    2026-05-10T14:30:00Z

Restored:
  Decision ID: dec_abc123 — opportunity: "Browser extension for code review"
  Decision ID: dec_def456 — opportunity: "CI/CD pipeline visualizer"
  Decision ID: dec_ghi789 — opportunity: "Automated dependency updater"
  Total restored: 3

Removed:
  Decision ID: dec_jkl012 — opportunity: "Browser extension for code review"
  Decision ID: dec_mno345 — opportunity: "CI/CD pipeline visualizer"
  Decision ID: dec_pqr678 — opportunity: "Automated dependency updater"
  Total removed: 3

Derived artifacts rebuilt:
  founder_feedback_mappings.json  — OK
  founder_preference_profile.json — OK
  parking_lot_records.json        — OK (orphans cleaned: 0, records added: 1)

Source URL traceability: OK (placeholder_count=0, missing_count=0)

Undo complete. A new undo entry has been appended to import_history.json.
Original correction entry preserved. Archive files preserved.
```

### 9.4 Success output (--utf8 mode)

```
Undo-last correction: ✓

Undone correction:
  correction_id:   correction_abc123def456
  correction_mode: replace
  corrected_at:    2026-05-10T14:30:00Z

Restored:
  Decision ID: dec_abc123 — opportunity: "Browser extension for code review"
  Decision ID: dec_def456 — opportunity: "CI/CD pipeline visualizer"
  Decision ID: dec_ghi789 — opportunity: "Automated dependency updater"
  Total restored: 3

Removed:
  Decision ID: dec_jkl012 — opportunity: "Browser extension for code review"
  Decision ID: dec_mno345 — opportunity: "CI/CD pipeline visualizer"
  Decision ID: dec_pqr678 — opportunity: "Automated dependency updater"
  Total removed: 3

Derived artifacts rebuilt:
  founder_feedback_mappings.json  — ✓
  founder_preference_profile.json — ✓
  parking_lot_records.json        — ✓ (orphans cleaned: 0, records added: 1)

Source URL traceability: ✓ (placeholder_count=0, missing_count=0)

Undo complete. A new undo entry has been appended to import_history.json.
Original correction entry preserved. Archive files preserved.
```

### 9.5 Amend undo success output (ASCII-safe default)

```
Undo-last correction: OK

Undone correction:
  correction_id:   correction_xyz789abc012
  correction_mode: amend
  corrected_at:    2026-05-10T15:00:00Z

Restored notes for:
  Decision ID: dec_abc123 — opportunity: "Browser extension for code review"
  Old notes restored from: amended_decisions/founder_decisions_v2_amended_2026-05-10T15...json

Derived artifacts: No rebuild needed (amend undo restores notes only).

Source URL traceability: OK (placeholder_count=0, missing_count=0)

Undo complete. A new undo entry has been appended to import_history.json.
Original correction entry preserved. Archive files preserved.
```

### 9.6 Failure output

All failure outputs follow the ASCII-safe default. Format:

```
Undo-last correction: FAIL

Error: <specific error message>

No artifacts were modified.
```

### 9.7 Exit codes

| Exit code | Meaning |
|---|---|
| 0 | Undo completed successfully. All artifacts written, audit appended. |
| 1 | Undo failed. Validation error. No artifacts modified. |
| 2 | Invalid CLI arguments (conflicting flags, missing required flag). No artifacts modified. |

### 9.8 No interactive prompt

Undo-last does not require an interactive prompt. The `--undo-last` flag is explicit and unambiguous. The founder must explicitly type the flag, which serves as the confirmation step.

This is consistent with the policy document's finding that "the re-replace workaround is adequate" — undo-last is an operator-initiated recovery action, not a dangerous operation requiring additional confirmation beyond the CLI flag itself.

If future feedback indicates a need for a confirmation prompt, it can be added as a non-breaking enhancement in v2.11+.

---

## 10. Fail-Closed Cases

### 10.1 Explicitly rejected conditions

| # | Condition | Error Message | Exit Code |
|---|---|---|---|
| F1 | `import_history.json` is missing | `"No import history found. Cannot undo — nothing to undo."` | 1 |
| F2 | `import_history.json` is empty (`entries: []`) | `"Import history is empty. No corrections to undo."` | 1 |
| F3 | Most recent entry already has `correction_mode = "undo"` | `"Most recent correction was already undone at {corrected_at}. No newer non-undo correction to undo."` | 1 |
| F4 | `replaced_decisions/` archive missing (replace/replace_all undo) | `"Archive not found: {archive_path}. Cannot restore pre-correction state."` | 1 |
| F5 | `replaced_decisions/` archive present but not parseable JSON | `"Archive is corrupt: {archive_path}. JSON parse error: {error_detail}."` | 1 |
| F6 | `replaced_decisions/` archive parseable but `old_decision_ids` mismatch | `"Archive content mismatch: expected decision IDs {expected_ids}, found {found_ids}."` | 1 |
| F7 | `amended_decisions/` archive missing (amend undo) | `"Archive not found: {archive_path}. Cannot restore pre-amendment notes."` | 1 |
| F8 | `amended_decisions/` archive present but not parseable JSON | `"Archive is corrupt: {archive_path}. JSON parse error: {error_detail}."` | 1 |
| F9 | Unknown `correction_mode` in most recent entry | `"Unknown correction mode: '{mode}'. Cannot undo. Supported modes: replace, amend."` | 1 |
| F10 | Source URL traceability pre-check fails | `"Undo would violate source URL traceability: placeholder_count={N}, missing_count={N}. Undo rejected."` | 1 |
| F11 | Source URL traceability post-check fails after undo | `"Post-undo source URL traceability check failed: placeholder_count={N}, missing_count={N}. Artifacts may be in inconsistent state."` | 1 |
| F12 | Derived artifact rebuild fails (replace/replace_all undo) | `"Derived artifact rebuild failed: {artifact_name}. Error: {error_detail}. Undo aborted — no artifacts modified."` | 1 |
| F13 | `founder_decisions_v2.json` missing or corrupt | `"Primary artifact missing or corrupt: founder_decisions_v2.json. Cannot proceed with undo."` | 1 |
| F14 | Target decision not found in current state (amend undo) | `"Decision '{decision_id}' not found in current founder_decisions_v2.json. Cannot restore notes."` | 1 |
| F15 | `correction_mode = "replace_all"` encountered (before item 5) | `"Undo of replace_all correction is not yet implemented. This capability will be available when Roadmap v2.10 item 5 (replace-all implementation) passes the readiness gate (item 4)."` | 1 |
| F16 | Conflicting flags: `--undo-last` with `--replace-review-items`, `--amend-notes-only`, `--replace-all`, or `--decisions-file` | `"Conflicting flags: --undo-last cannot be combined with {conflicting_flags}."` | 2 |

### 10.2 Pre-check vs post-check ordering

All conditions F1–F9 and F10 (pre-check), F13–F16 are detected **before any writes**. Conditions F11–F12 are detected **after writes** and indicate an implementation bug if they ever trigger (all inputs should have been validated pre-write).

### 10.3 Partial undo prevention

The implementation must:
1. Prepare all write content in-memory (restored decisions, rebuilt mappings, rebuilt profile, cleaned parking lot records).
2. Validate all in-memory content before touching any file.
3. Write all files in the defined order.
4. If any pre-write validation fails, return error without any file writes.
5. Not attempt to "roll back" partial writes at the file level (the file-system architecture does not support transactional rollback). Instead, prevent partial writes through comprehensive pre-validation.

---

## 11. Idempotency and Repeat Behavior

### 11.1 Chosen behavior: reject already-undone correction

If `--undo-last` is run twice consecutively (without any new correction between invocations):

1. First invocation: succeeds. The most recent `CorrectionEntry` (e.g., `correction_mode = "replace"`) is undone. A new `CorrectionEntry` with `correction_mode = "undo"` is appended.
2. Second invocation: **rejected**. The most recent entry now has `correction_mode = "undo"`. The system detects this and rejects with: `"Most recent correction was already undone at {corrected_at}. No newer non-undo correction to undo."`

This behavior is chosen because:
- **Safety.** It prevents accidentally undoing the correction *before* the already-undone correction, which would be a multi-step undo (explicitly excluded from v2.10 scope per U-R10).
- **Clarity.** The error message explicitly states when the last undo occurred, so the founder knows the state.
- **Predictability.** Running `--undo-last` twice always either succeeds (first time) or fails with a clear message (second time). It never silently undoes a different correction than intended.
- **Audit integrity.** Each undo appends its own entry. The history shows: replace → undo → (rejected second undo). The state is unambiguous.

### 11.2 Alternative considered and rejected

**Alternative:** "Skip over undo entries and undo the newest non-undo correction."
- Rejected because it violates U-R10 (undo-last only). Skipping over undo entries to find the next non-undo entry is equivalent to multi-step undo, which requires correction-stack navigation that v2.10 explicitly defers to v2.11+.
- The founder can achieve the same effect by re-issuing the original correction (using `--replace-review-items` or `--amend-notes-only`) and then running `--undo-last` again.

### 11.3 Idempotency within a single undo operation

Within a single successful undo operation:
- Undoing the same correction with the same artifact state yields identical artifact checksums (U-R9).
- The `correction_id` of the undo entry is deterministic (Section 6.4), so two undo operations against the same state would produce the same `correction_id`.
- However, since the second invocation is rejected (Section 11.1), this idempotency property is a safety guarantee rather than an exercised code path.

---

## 12. Source URL Traceability

### 12.1 Hard requirements

| Requirement | Value | Enforcement |
|---|---|---|
| `placeholder_count` | `0` | Pre-check and post-check via `check_source_url_traceability()` |
| `missing_count` | `0` | Pre-check and post-check via `check_source_url_traceability()` |
| No `urn:oos:*` placeholders introduced by undo | Guaranteed | Restored decisions carry their original `http`/`https` URLs from the archive |
| Synthetic inbox exemption | Narrow and unchanged | Same exemption policy as replace/amend modes |

### 12.2 How undo preserves traceability

- **Restored decisions carry original source URLs.** The `replaced_decisions/` archive stores full `FounderDecisionV2` objects including `linked_source_urls`. These URLs were validated during the original import and during the original replace operation.
- **Removed replacement decisions are discarded.** The replacement decisions' `linked_source_urls` are also real URLs, but they are no longer active.
- **No new decisions are created.** Undo only restores existing decisions from archives. It never synthesizes new decisions, so it never needs to create source URLs.
- **Derived artifact rebuild propagates real URLs.** When feedback mappings and preference profiles are rebuilt from restored decisions, they inherit the real `http`/`https` URLs from the restored decisions.

### 12.3 Pre-check traceability validation

Before any writes occur, the implementation must:
1. Build the projected post-undo `founder_decisions_v2.json` in memory.
2. Build projected derived artifacts in memory.
3. Run `check_source_url_traceability()` against the projected state.
4. If `validation_passed != True` or `placeholder_count > 0` or `missing_count > 0`, abort.

### 12.4 Post-check traceability validation

After all writes:
1. Run `check_source_url_traceability()` against the actual on-disk state.
2. Record the result in the undo `CorrectionEntry` (`source_url_traceability_result` field).
3. Record the result in `manifest.json` (`undo_result_summary.source_url_traceability_passed`).
4. If the post-check fails, report the error. This should not happen if the pre-check passed, but serves as a defense-in-depth measure.

### 12.5 Exemption policy unchanged

The source URL exemption policy from the [correction artifact contract](founder_decision_correction_artifact_contract.md) Section 10.5 remains in effect:
- Items whose inbox `linked_source_urls` is empty **and** the item has a documented `empty_source_urls_reason` field are exempt.
- This exemption is narrow and must be explicitly justified by the founder.

---

## 13. Testing Expectations for Item 3

### 13.1 Test categories

The following test categories are expected in Roadmap v2.10 item 3 (Undo-Last Validation and Smoke Coverage). These are listed here for contract completeness; implementation is deferred to item 3.

| # | Test Category | Description |
|---|---|---|
| T1 | Undo replace | Undo a `replace` correction. Verify old decisions restored, replacement decisions removed, derived artifacts rebuilt, manifest updated, audit appended. |
| T2 | Undo amend | Undo an `amend` correction. Verify old notes restored, decision value unchanged, no derived artifact rebuild, manifest updated, audit appended. |
| T3 | Undo replace_all compatibility | Verify that attempting to undo a `replace_all` entry (before item 5 is implemented) is rejected with a clear message. |
| T4 | Empty history rejected | Verify `--undo-last` with empty or missing `import_history.json` is rejected (F1, F2). |
| T5 | Missing archive rejected | Verify `--undo-last` when `replaced_decisions/` or `amended_decisions/` archive is missing is rejected (F4, F7). |
| T6 | Corrupt archive rejected | Verify `--undo-last` when archive file is not parseable JSON is rejected (F5, F8). |
| T7 | Archive content mismatch | Verify `--undo-last` when archive `old_decision_ids` don't match the `CorrectionEntry` is rejected (F6). |
| T8 | Idempotency / repeat undo | Verify running `--undo-last` twice: first succeeds, second is rejected with "already undone" message (F3). |
| T9 | Source URL traceability | Verify post-undo `placeholder_count = 0` and `missing_count = 0`. Verify pre-check catches traceability regression before writes. |
| T10 | Parking lot consistency | Verify parking lot records are correct after undo: orphaned records removed, new records for restored PARK/REVISIT_LATER decisions created, unrelated records untouched. |
| T11 | Fail-closed partial write prevention | Verify that when pre-validation fails, no files are modified on disk. |
| T12 | Advisory-only preservation | Verify `advisory_only=True`, `no_live_api=True`, `no_live_llm=True` on undo entry. |
| T13 | Deterministic undo | Verify that undoing the same correction from the same state twice produces identical artifact checksums (even though the second undo is rejected per idempotency, the first undo's output is deterministic). |
| T14 | Undo after multiple corrections | Verify that only the most recent non-undo correction is undone; earlier corrections remain untouched. |
| T15 | Conflicting flags | Verify `--undo-last` combined with `--replace-review-items`, `--amend-notes-only`, `--replace-all`, or `--decisions-file` exits with code 2. |
| T16 | CLI output format | Verify success output contains all required sections (correction info, restored decisions, removed decisions, rebuild status, traceability). Verify failure output contains error message and "No artifacts were modified." |
| T17 | --utf8 output mode | Verify `--utf8` flag produces Unicode symbols (✓) and ASCII-safe default produces ASCII symbols (OK). |
| T18 | Amend undo: decision not found | Verify undo-amend when the target decision has been removed from `founder_decisions_v2.json` is rejected (F14). |
| T19 | Unknown correction_mode rejected | Verify undo when the most recent entry has an unrecognized `correction_mode` is rejected (F9). |
| T20 | Manifest field correctness | Verify `undone_decision_ids`, `undone_at`, `undone_correction_id`, and `undo_result_summary` are correctly populated in `manifest.json`. |

### 13.2 Minimum test count

The policy document estimates 20+ tests for the undo test suite. This contract defines 20 test categories (T1–T20). Some categories may require multiple test methods (e.g., T10 parking lot consistency may need separate tests for PARK→PROMOTE undo, KILL→PARK undo, etc.).

---

## 14. Non-Goals

The following are **explicitly excluded** from the undo-last contract and implementation:

1. **Multi-step undo.** Undoing more than the most recent correction (`--undo-correction <id>`, U2 mode). Deferred to v2.11+.
2. **Run-level undo.** Restoring an entire run from archive (`--undo-run <run_id>`, U3 mode). Requires pre-correction snapshots. Deferred to v2.11+.
3. **Restore archived.** Manual restore of a specific decision from archive (`--restore-archived <decision_id>`, U4 mode). Error-prone; not recommended.
4. **UI or graphical interface.** CLI-only.
5. **Live API/LLM calls.** All undo logic is deterministic and local.
6. **Automatic terminal encoding detection.** `--utf8` remains opt-in.
7. **replace-all implementation.** Defined for forward compatibility only. Implementation is gated by Roadmap v2.10 item 4.
8. **New archive creation.** Undo reads from existing archives; it does not create new archive files.
9. **Pre-correction snapshots.** Not introduced in v2.10. The existing `replaced_decisions/` and `amended_decisions/` archives are sufficient for undo-last.
10. **Cross-run undo.** Undo only operates within a single run directory.
11. **Undo of initial import.** If `import_history.json` contains only the initial import entry (not a correction), there is nothing to undo. The initial import is not a "correction" and is not undoable.

---

## 15. Implementation Notes

### 15.1 Likely future module

The implementation (Roadmap v2.10 item 2) is expected to create:

```
src/oos/correction_undo.py
```

This module will contain:
- `UndoResult` model — structured result of an undo operation
- `undo_last_correction(run_dir: Path, *, use_utf8: bool = False) -> UndoResult` — main entry point
- `_validate_undo_preconditions(run_dir: Path) -> CorrectionEntry` — pre-write validation
- `_undo_replace(run_dir: Path, entry: CorrectionEntry) -> dict` — replace undo logic
- `_undo_amend(run_dir: Path, entry: CorrectionEntry) -> dict` — amend undo logic
- `_rebuild_derived_artifacts(run_dir: Path, decisions: list[FounderDecisionV2]) -> dict` — derived artifact rebuild
- `_post_validate_undo(run_dir: Path) -> SourceURLTraceabilityReport` — post-write validation

### 15.2 Integration points

The undo path integrates with:
- [`src/oos/founder_decision_import.py`](../../src/oos/founder_decision_import.py) — for reading `import_history.json`, reading/writing `manifest.json`, and appending undo `CorrectionEntry`
- [`src/oos/decision_correction_rebuild.py`](../../src/oos/decision_correction_rebuild.py) — for derived artifact rebuild functions (reuse existing `cleanup_orphaned_parking_lot_records()`, `build_feedback_mappings_for_decisions()`, `build_preference_profile_for_decisions()`, `build_parking_lot_records_for_decisions()`)
- [`src/oos/cli.py`](../../src/oos/cli.py) — for adding `--undo-last` flag to `import-founder-decisions-v2` subcommand
- [`src/oos/source_url_traceability.py`](../../src/oos/source_url_traceability.py) — for `check_source_url_traceability()` pre-check and post-check

### 15.3 Reuse of existing rebuild infrastructure

The undo implementation must reuse the existing derived artifact rebuild functions from `decision_correction_rebuild.py` rather than reimplementing them. This ensures:
- Consistency with replace-mode rebuild behavior.
- Single source of truth for rebuild logic.
- Reduced implementation surface area.

### 15.4 Atomic-ish write considerations

The undo implementation should follow the same write discipline as replace mode:
- Prepare all content in-memory.
- Validate in-memory content.
- Write files sequentially.
- If `write-then-rename` pattern is adopted for replace mode in the future, undo must adopt it too.

### 15.5 This contract does not implement

This contract is a specification document only. It does **not**:
- Create `src/oos/correction_undo.py`
- Modify `src/oos/cli.py` or `src/oos/founder_decision_import.py`
- Create `tests/test_correction_undo.py`
- Add CLI flags
- Run any code

---

## 16. Self-Audit

| Question | Answer |
|---|---|
| Did this avoid implementation? | **Yes.** Contract/docs only. No `.py` files modified. |
| Did this avoid source/test changes? | **Yes.** No source or test files changed. |
| Did this translate all 12 safety requirements? | **Yes.** Section 3 maps U-R1 through U-R12 to concrete contract behavior. |
| Did this define artifact write order? | **Yes.** Section 5 defines exact write order for replace, amend, and replace_all undo. |
| Did this define CorrectionEntry schema for undo? | **Yes.** Section 6 defines all undo-specific fields and their specifications. |
| Did this define manifest fields? | **Yes.** Section 7 defines `undone_decision_ids`, `undone_at`, `undone_correction_id`, `undo_result_summary`. |
| Did this define CLI behavior? | **Yes.** Section 9 defines invocation, success output, failure output, exit codes, and mutual exclusion. |
| Did this define fail-closed cases? | **Yes.** Section 10 defines 16 explicit fail-closed conditions with error messages and exit codes. |
| Did this define idempotency behavior? | **Yes.** Section 11 specifies reject-already-undone with justification. |
| Did this define source URL traceability requirements? | **Yes.** Section 12 requires `placeholder_count=0`, `missing_count=0`, and both pre-check and post-check. |
| Did this define testing expectations? | **Yes.** Section 13 lists 20 test categories for item 3. |
| Did this define non-goals? | **Yes.** Section 14 explicitly excludes multi-step undo, run-level undo, restore-archived, UI, live APIs/LLMs, auto-detection, replace-all implementation, and cross-run undo. |
| Did this preserve founder-control assumptions? | **Yes.** `advisory_only=True`, explicit CLI flag, founder-initiated, no autonomous decisions. |
| Did this avoid live APIs/LLMs? | **Yes.** `no_live_api=True`, `no_live_llm=True`. |
| Did this resolve the design pre-work items from policy Section 9.4? | **Yes.** Pre-correction snapshot decision (not needed), undo entry schema (Section 6), CLI output format (Section 9), manifest updates (Section 7), interaction with replace-all (Section 8.3). |
| Is this contract self-consistent with the 12 safety requirements? | **Yes.** Section 3 provides full traceability. |

---

## Appendix A: Design Decisions Resolved

This appendix records the resolution of the five design pre-work items from the [undo policy](../decisions/correction_rollback_undo_policy.md) Section 9.4.

### A.1 Pre-correction snapshot

**Decision:** Not needed for undo-last. The existing `replaced_decisions/` and `amended_decisions/` archives are sufficient. Pre-correction snapshots of all artifacts would increase storage complexity without adding safety for single-step undo. If full snapshots become necessary for multi-step undo (v2.11+), they can be introduced then.

### A.2 Undo entry in CorrectionEntry

**Decision:** The `correction_mode` field accepts `"undo"` as a valid value. The `CorrectionEntry` model is extended with undo-specific fields (`undone_correction_id`, `undone_correction_mode`, `undone_decision_ids`, `undone_at`, `source_history_entry_index`, `archive_refs`, `source_url_traceability_result`, `notes`) as defined in Section 6. The existing `correction_mode` field already accepts arbitrary strings, so no schema migration is needed.

### A.3 CLI output for undo

**Decision:** Defined in Section 9. Success output includes: undone correction info, restored decisions, removed decisions, derived artifact rebuild status, and source URL traceability result. Failure output includes error message and "No artifacts were modified." UTF-8 mode uses Unicode symbols; ASCII-safe default uses ASCII equivalents.

### A.4 Undo and the manifest

**Decision:** Manifest records `undone_decision_ids`, `undone_at`, `undone_correction_id`, and `undo_result_summary` as defined in Section 7.

### A.5 Interaction with `--replace-all`

**Decision:** Defined in Section 8.3. Undo of `replace_all` is specified for forward compatibility but implementation is deferred until Roadmap v2.10 item 5 passes the readiness gate. Until then, attempting to undo a `replace_all` entry is rejected with a clear message.

---

## Appendix B: Comparison — All Correction Modes Including Undo

| Mode | CLI Flag | Scope | Direction | Implemented |
|---|---|---|---|---|
| Reject-on-reimport | (default) | All decisions | N/A | v2.6 |
| Replace-review-items | `--replace-review-items` | Listed `review_item_id` values | Forward (old→new) | v2.8 |
| Amend-notes-only | `--amend-notes-only` | Listed `review_item_id` values | In-place (notes only) | v2.8 |
| Replace-all | `--replace-all` | All decisions in run | Forward (old→new) | Policy only (v2.9 item 3.2); gated implementation in v2.10 item 5 |
| Undo-last | `--undo-last` | Most recent correction | Backward (new→old) | Contract (this document); implementation in v2.10 item 2 |
| Undo-specific | `--undo-correction <id>` | Specific `correction_id` | Backward (new→old) | v2.11+ |
| Undo-run | `--undo-run <run_id>` | Entire run | Backward (new→old) | v2.11+ |
| Restore-archived | `--restore-archived <id>` | Specific `decision_id` | Archive→active | Not recommended |

---

## Appendix C: Artifact State Transition Diagram for Undo-Replace

```
BEFORE UNDO:
  founder_decisions_v2.json:  [D_new_1, D_new_2, D_untouched_3, D_untouched_4]
  replaced_decisions/:        {archive: [D_old_1, D_old_2]}
  import_history.json:        [..., Entry{correction_mode="replace", old=[D_old_1,D_old_2], new=[D_new_1,D_new_2]}]
  parking_lot_records.json:   [PLR_new_1 (PARK), PLR_untouched_3]

AFTER UNDO:
  founder_decisions_v2.json:  [D_old_1, D_old_2, D_untouched_3, D_untouched_4]
  replaced_decisions/:        {archive: [D_old_1, D_old_2]}  (unchanged)
  import_history.json:        [..., Entry_replace, Entry_undo{correction_mode="undo", undone_correction_id=...}]
  parking_lot_records.json:   [PLR_old_1 (if D_old_1 was PARK), PLR_untouched_3]
                               (PLR_new_1 orphaned → removed)
```

---

## Appendix D: References

| Document | Relationship |
|---|---|
| [`correction_rollback_undo_policy.md`](../decisions/correction_rollback_undo_policy.md) | Authoritative source of 12 safety requirements (U-R1–U-R12) and policy decisions |
| [`founder_decision_correction_artifact_contract.md`](founder_decision_correction_artifact_contract.md) | Defines artifact dependency graph, rebuild order, `CorrectionEntry` base model, parking lot policy |
| [`source_url_traceability_contract.md`](source_url_traceability_contract.md) | Defines `placeholder_count=0`, `missing_count=0`, and traceability checker interface |
| [`output_mode_contract.md`](output_mode_contract.md) | Defines ASCII-safe default and `--utf8` opt-in behavior |
| [`replace_all_mode_policy.md`](../decisions/replace_all_mode_policy.md) | Defines replace-all safety requirements and gates; referenced for forward compatibility |
| [`OOS_roadmap_v2_10_recovery_correction_checklist.md`](../roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md) | Roadmap item 1.1 definition of done and validation expectations |
