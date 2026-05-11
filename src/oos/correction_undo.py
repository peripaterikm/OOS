"""Undo-Last Correction — deterministic undo of the most recent correction.

Roadmap v2.10 item 2.1. Implements the narrow U1 undo-last mode as specified in
docs/contracts/undo_last_contract.md.

Satisfies all 12 safety requirements (U-R1 through U-R12) from
docs/decisions/correction_rollback_undo_policy.md.

This module:
- Reads import_history.json to find the most recent non-undo CorrectionEntry.
- Validates pre-conditions before any writes (fail-closed).
- Undoes replace corrections: restores old decisions from replaced_decisions/,
  removes replacement decisions, rebuilds derived artifacts.
- Undoes amend corrections: restores old notes from amended_decisions/,
  no derived artifact rebuild.
- Rejects replace_all corrections with a clear message (future compatibility).
- Rejects unknown correction modes (fail-closed).
- Appends a new CorrectionEntry with correction_mode = "undo" to import_history.json.
- Preserves advisory_only=True, no_live_api=True, no_live_llm=True throughout.
- Verifies source URL traceability after undo.

No live LLM/API calls. No autonomous decisions. No portfolio mutations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from oos.decision_correction_rebuild import (
    rebuild_founder_decision_derived_artifacts,
)
from oos.founder_decision_taxonomy import (
    FounderDecisionV2,
    founder_decision_from_dict,
    founder_decision_to_dict,
)
from oos.founder_feedback_mapping import (
    founder_feedback_mapping_to_dict,
)
from oos.founder_preference_profile import (
    founder_preference_profile_to_dict,
)
from oos.parking_lot import (
    parking_lot_records_to_json,
)
from oos.source_url_traceability import (
    check_source_url_traceability,
)
from oos.weekly_run_manifest import (
    canonical_artifact_paths,
    canonical_artifact_schema_versions,
)
from oos.weekly_run_reports import (
    build_weekly_dashboard_index,
    build_weekly_run_report,
    write_weekly_dashboard_index,
    write_weekly_run_report,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNDO_LAST_SCHEMA_VERSION = "correction_undo.v1"

# Valid correction modes that undo-last supports
_SUPPORTED_UNDO_MODES = frozenset({"replace", "amend"})

# All recognized correction modes
_RECOGNIZED_MODES = frozenset({"replace", "amend", "undo", "replace_all"})


# ---------------------------------------------------------------------------
# UndoResult model
# ---------------------------------------------------------------------------


@dataclass
class UndoResult:
    """Result of an undo-last correction operation.

    advisory_only=True throughout. No live API/LLM calls.
    """

    run_id: str = ""
    run_dir: str = ""
    undone_correction_id: str = ""
    undone_correction_mode: str = ""
    undone_at: str = ""
    restored_decision_ids: list[str] = field(default_factory=list)
    removed_decision_ids: list[str] = field(default_factory=list)
    derived_artifacts_rebuilt: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    artifacts_updated: list[str] = field(default_factory=list)
    validation_passed: bool = False
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True
    schema_version: str = UNDO_LAST_SCHEMA_VERSION
    source_url_placeholder_count: int = 0
    source_url_missing_count: int = 0
    archive_refs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_dir": self.run_dir,
            "undone_correction_id": self.undone_correction_id,
            "undone_correction_mode": self.undone_correction_mode,
            "undone_at": self.undone_at,
            "restored_decision_ids": list(self.restored_decision_ids),
            "removed_decision_ids": list(self.removed_decision_ids),
            "derived_artifacts_rebuilt": self.derived_artifacts_rebuilt,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "artifacts_updated": list(self.artifacts_updated),
            "validation_passed": self.validation_passed,
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
            "schema_version": self.schema_version,
            "source_url_placeholder_count": self.source_url_placeholder_count,
            "source_url_missing_count": self.source_url_missing_count,
            "archive_refs": dict(self.archive_refs),
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def undo_last_correction(
    run_dir: Path,
    *,
    use_utf8: bool = False,
) -> UndoResult:
    """Undo the most recent non-undo correction in a weekly run directory.

    Args:
        run_dir: Path to the weekly run directory.
        use_utf8: If True, use Unicode symbols in output strings (internal use only;
                  does not affect artifact content).

    Returns:
        UndoResult with validation status, restored/removed decision IDs,
        and artifact update info.

    Implements the U1 undo-last mode per docs/contracts/undo_last_contract.md.
    """
    run_dir = run_dir.resolve()
    corrected_at = datetime.now(timezone.utc).isoformat()
    project_root = run_dir.parent.parent.parent  # run_dir is <pr>/artifacts/weekly_runs/<run_id>
    output_mode = "utf8" if use_utf8 else "ascii_safe"

    # ------------------------------------------------------------------
    # PHASE 0 — Pre-write validation (no writes)
    # ------------------------------------------------------------------

    # Load import history
    history_path = run_dir / "import_history.json"
    if not history_path.is_file():
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message="No import history found. Cannot undo — nothing to undo.",
        )

    try:
        history_data = json.loads(history_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=f"Import history is corrupt: {history_path}. JSON parse error: {exc.msg}.",
        )

    entries_list = history_data.get("entries", [])
    if not isinstance(entries_list, list) or not entries_list:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message="Import history is empty. No corrections to undo.",
        )

    # Find the most recent non-undo entry
    target_entry: dict[str, Any] | None = None
    target_index: int = -1
    for i in range(len(entries_list) - 1, -1, -1):
        entry = entries_list[i]
        if isinstance(entry, dict) and entry.get("correction_mode") != "undo":
            target_entry = entry
            target_index = i
            break

    if target_entry is None:
        # All entries are undo entries
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                "Import history contains only undo entries. "
                "No non-undo correction to undo."
            ),
        )

    # Check if most recent entry is already an undo
    last_entry = entries_list[-1] if entries_list else {}
    if isinstance(last_entry, dict) and last_entry.get("correction_mode") == "undo":
        last_undo_at = last_entry.get("corrected_at", "unknown")
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Most recent correction was already undone at {last_undo_at}. "
                f"No newer non-undo correction to undo."
            ),
        )

    correction_mode = str(target_entry.get("correction_mode", ""))
    old_decision_ids = _safe_string_list(target_entry.get("old_decision_ids", []))
    new_decision_ids = _safe_string_list(target_entry.get("new_decision_ids", []))
    undone_correction_id = str(target_entry.get("correction_id", ""))

    # Validate correction mode
    if correction_mode not in _RECOGNIZED_MODES:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Unknown correction mode: '{correction_mode}'. "
                f"Cannot undo. Supported modes: replace, amend."
            ),
        )

    if correction_mode == "replace_all":
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                "Undo of replace_all correction is not yet implemented. "
                "This capability will be available when Roadmap v2.10 item 5 "
                "(replace-all implementation) passes the readiness gate (item 4)."
            ),
        )

    if correction_mode not in _SUPPORTED_UNDO_MODES:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Correction mode '{correction_mode}' is recognized but not yet "
                f"supported for undo. Supported modes: replace, amend."
            ),
        )

    # Load manifesto for run_id
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=f"Manifest not found: {manifest_path}.",
        )

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=f"Invalid manifest JSON: {exc.msg}.",
        )

    run_id = str(manifest_data.get("run_id", run_dir.name))

    # Load current founder decisions
    paths = canonical_artifact_paths()
    decisions_path = run_dir / paths["founder_decisions_v2"]
    if not decisions_path.is_file():
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                "Primary artifact missing or corrupt: "
                "founder_decisions_v2.json. Cannot proceed with undo."
            ),
        )

    try:
        decisions_raw = json.loads(decisions_path.read_text(encoding="utf-8"))
        current_items = decisions_raw.get("items", []) if isinstance(decisions_raw, dict) else []
    except json.JSONDecodeError as exc:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Primary artifact is corrupt: founder_decisions_v2.json. "
                f"JSON parse error: {exc.msg}."
            ),
        )

    # Build current decision lookup by decision_id
    current_by_did: dict[str, dict[str, Any]] = {}
    for item in current_items:
        if isinstance(item, dict) and item.get("decision_id"):
            current_by_did[str(item["decision_id"])] = item

    # ------------------------------------------------------------------
    # Branch by correction_mode
    # ------------------------------------------------------------------

    if correction_mode == "replace":
        return _undo_replace(
            run_dir=run_dir,
            project_root=project_root,
            run_id=run_id,
            corrected_at=corrected_at,
            target_entry=target_entry,
            target_index=target_index,
            old_decision_ids=old_decision_ids,
            new_decision_ids=new_decision_ids,
            undone_correction_id=undone_correction_id,
            current_by_did=current_by_did,
            current_items=current_items,
            manifest_data=manifest_data,
            history_data=history_data,
            entries_list=entries_list,
            output_mode=output_mode,
        )
    elif correction_mode == "amend":
        return _undo_amend(
            run_dir=run_dir,
            project_root=project_root,
            run_id=run_id,
            corrected_at=corrected_at,
            target_entry=target_entry,
            target_index=target_index,
            old_decision_ids=old_decision_ids,
            undone_correction_id=undone_correction_id,
            current_by_did=current_by_did,
            current_items=current_items,
            manifest_data=manifest_data,
            history_data=history_data,
            entries_list=entries_list,
            output_mode=output_mode,
        )
    else:
        # Should not reach here due to validation above
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=f"Unreachable: unsupported correction mode '{correction_mode}'.",
        )


# ---------------------------------------------------------------------------
# Undo replace
# ---------------------------------------------------------------------------


def _undo_replace(
    *,
    run_dir: Path,
    project_root: Path,
    run_id: str,
    corrected_at: str,
    target_entry: dict[str, Any],
    target_index: int,
    old_decision_ids: list[str],
    new_decision_ids: list[str],
    undone_correction_id: str,
    current_by_did: dict[str, dict[str, Any]],
    current_items: list[dict[str, Any]],
    manifest_data: dict[str, Any],
    history_data: dict[str, Any],
    entries_list: list[dict[str, Any]],
    output_mode: str = "ascii_safe",
) -> UndoResult:
    """Undo a replace correction."""
    warnings: list[str] = []

    # Locate and validate the replaced_decisions/ archive
    archive_refs = _find_replace_archive(
        run_dir=run_dir,
        target_entry=target_entry,
        old_decision_ids=old_decision_ids,
    )
    if isinstance(archive_refs, UndoResult):
        return archive_refs  # error result

    archive_path = run_dir / archive_refs["replaced_decisions"]
    try:
        archive_data = json.loads(archive_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Archive is corrupt: {archive_path}. "
                f"JSON parse error: {exc.msg}."
            ),
        )

    archived_decisions_raw = archive_data.get("decisions", [])
    if not isinstance(archived_decisions_raw, list):
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Archive is corrupt: {archive_path}. "
                f"'decisions' field is not a list."
            ),
        )

    # Build archived decision lookup
    archived_by_did: dict[str, dict[str, Any]] = {}
    archived_dids: set[str] = set()
    for item in archived_decisions_raw:
        if isinstance(item, dict) and item.get("decision_id"):
            did = str(item["decision_id"])
            archived_by_did[did] = item
            archived_dids.add(did)

    # Validate archive content matches old_decision_ids
    expected = set(old_decision_ids)
    found = archived_dids
    missing_from_archive = expected - found
    extra_in_archive = found - expected
    if missing_from_archive:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Archive content mismatch: expected decision IDs "
                f"{sorted(expected)}, found {sorted(found)}. "
                f"Missing from archive: {sorted(missing_from_archive)}."
            ),
        )
    if extra_in_archive:
        warnings.append(
            f"Archive contains extra decision IDs not listed in correction entry: "
            f"{sorted(extra_in_archive)}. Only expected IDs will be restored."
        )

    # Verify new_decision_ids exist in current state
    for did in new_decision_ids:
        if did not in current_by_did:
            return _fail(
                run_dir=run_dir,
                corrected_at=corrected_at,
                message=(
                    f"Replacement decision '{did}' not found in current "
                    f"founder_decisions_v2.json. Cannot undo."
                ),
            )

    # Build restored decision set: keep non-replaced + insert archived
    removed_decision_ids = [did for did in new_decision_ids if did in current_by_did]
    restored_decision_ids = sorted(archived_dids)

    kept_items: list[dict[str, Any]] = []
    for item in current_items:
        if isinstance(item, dict):
            did = str(item.get("decision_id", ""))
            if did not in set(new_decision_ids):
                kept_items.append(item)

    final_items = kept_items + [
        archived_by_did[did] for did in sorted(archived_dids)
    ]

    # Convert to FounderDecisionV2 for rebuild
    final_decisions: list[FounderDecisionV2] = []
    failed_parse_count = 0
    for item in final_items:
        try:
            final_decisions.append(founder_decision_from_dict(item))
        except (ValueError, TypeError):
            failed_parse_count += 1

    if failed_parse_count > 0:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Archive decision parse failure: {failed_parse_count} of "
                f"{len(final_items)} restored decisions failed to parse as "
                f"FounderDecisionV2. Undo aborted — no artifacts modified."
            ),
        )

    # Pre-check source URL traceability on projected state (in-memory)
    _unsafe_trace = _precheck_source_url_traceability(
        decisions=final_decisions,
        context="pre-check",
    )
    if _unsafe_trace and not _unsafe_trace.get("validation_passed", False):
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Undo would violate source URL traceability: "
                f"placeholder_count={_unsafe_trace.get('placeholder_count', '?')}, "
                f"missing_count={_unsafe_trace.get('missing_count', '?')}. "
                f"Undo rejected."
            ),
        )

    # ------------------------------------------------------------------
    # PHASE 1 & 2 — Restore primary and rebuild derived
    # ------------------------------------------------------------------

    # Load existing parking lot records
    existing_pl_records: list[dict[str, Any]] = []
    pl_path = run_dir / paths().get("parking_lot_records", "parking_lot_records.json")
    if pl_path.is_file():
        try:
            pl_raw = json.loads(pl_path.read_text(encoding="utf-8"))
            existing_pl_records = pl_raw.get("items", []) if isinstance(pl_raw, dict) else []
        except (json.JSONDecodeError, ValueError):
            pass

    # Rebuild derived artifacts
    from oos.parking_lot import ParkingLotRecord
    pl_as_objects: list[ParkingLotRecord] = []
    for item in existing_pl_records:
        if isinstance(item, dict):
            try:
                pl_as_objects.append(ParkingLotRecord.from_dict(item))
            except (ValueError, TypeError):
                pass

    rebuild_result = rebuild_founder_decision_derived_artifacts(
        decisions=final_decisions,
        existing_parking_lot_records=pl_as_objects,
        replaced_decision_ids=set(removed_decision_ids),
    )

    if rebuild_result.errors:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Derived artifact rebuild failed: "
                f"{'; '.join(rebuild_result.errors)}. "
                f"Undo aborted — no artifacts modified."
            ),
        )

    warnings.extend(rebuild_result.warnings)
    all_mappings = rebuild_result.feedback_mappings
    preference_profile = rebuild_result.preference_profile
    rebuilt_pl_records = rebuild_result.parking_lot_records

    # ------------------------------------------------------------------
    # PHASE 3 & 4 — Write artifacts (all-or-nothing via pre-build)
    # ------------------------------------------------------------------
    schemas = canonical_artifact_schema_versions()
    artifacts_updated: list[str] = []

    try:
        # 1. founder_decisions_v2.json
        decisions_write: dict[str, Any] = {
            "items": [founder_decision_to_dict(d) if hasattr(d, 'to_dict') else _to_safe_dict(d)
                      for d in final_decisions],
            "schema_version": schemas["founder_decisions_v2"],
            "empty": len(final_decisions) == 0,
            "imported": True,
            "note": "Founder decisions restored via undo-last (v2.10 item 2.1).",
        }
        decisions_write["items"] = [founder_decision_to_dict(d) for d in final_decisions]
        _write_json_atomic(run_dir, paths()["founder_decisions_v2"], decisions_write)
        artifacts_updated.append("founder_decisions_v2")

        # 2. founder_feedback_mappings.json
        mappings_write: dict[str, Any] = {
            "items": [founder_feedback_mapping_to_dict(m) for m in all_mappings],
            "schema_version": schemas["founder_feedback_mappings"],
            "empty": len(all_mappings) == 0,
            "imported": True,
            "note": "Feedback mappings rebuilt after undo-last.",
        }
        _write_json_atomic(run_dir, paths()["founder_feedback_mappings"], mappings_write)
        artifacts_updated.append("founder_feedback_mappings")

        # 3. founder_preference_profile.json
        if preference_profile:
            profile_data = founder_preference_profile_to_dict(preference_profile)
            _write_json_atomic(run_dir, paths()["founder_preference_profile"], profile_data)
            artifacts_updated.append("founder_preference_profile")

        # 4. parking_lot_records.json
        pl_dicts = json.loads(parking_lot_records_to_json(rebuilt_pl_records))
        pl_write: dict[str, Any] = {
            "items": pl_dicts,
            "schema_version": schemas["parking_lot_records"],
            "empty": len(rebuilt_pl_records) == 0,
            "import_updated": True,
            "cleanup_applied": True,
        }
        _write_json_atomic(run_dir, paths()["parking_lot_records"], pl_write)
        artifacts_updated.append("parking_lot_records")

        # 5. Update manifest
        manifest_data["empty_states"] = {
            **(manifest_data.get("empty_states", {})),
            "founder_decisions_v2": len(final_decisions) == 0,
            "founder_feedback_mappings": len(all_mappings) == 0,
            "founder_preference_profile": preference_profile is None,
            "parking_lot_records": len(rebuilt_pl_records) == 0,
        }
        manifest_data["undone_decision_ids"] = restored_decision_ids
        manifest_data["undone_at"] = corrected_at
        manifest_data["undone_correction_id"] = undone_correction_id
        manifest_data["undo_result_summary"] = {
            "undo_mode": "undo_last",
            "undone_correction_mode": "replace",
            "undone_correction_id": undone_correction_id,
            "restored_decision_count": len(restored_decision_ids),
            "removed_decision_count": len(removed_decision_ids),
            "derived_artifacts_rebuilt": True,
            "source_url_traceability_passed": False,  # updated after post-check
            "source_url_placeholder_count": 0,
            "source_url_missing_count": 0,
        }
        _write_json_atomic(run_dir, paths()["manifest"], manifest_data)
        artifacts_updated.append("manifest")

    except (OSError, ValueError, TypeError) as exc:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=f"Artifact write failed: {exc}.",
        )

    # ------------------------------------------------------------------
    # PHASE 4 — Regenerate reports and dashboard
    # ------------------------------------------------------------------
    regen_ok, regen_errors = _regenerate_reports_and_dashboard(
        project_root=project_root,
        run_dir=run_dir,
        run_id=run_id,
        output_mode=output_mode,
    )
    if not regen_ok:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Report/dashboard regeneration failed: "
                f"{'; '.join(regen_errors)}. "
                f"Undo aborted — no undo CorrectionEntry appended."
            ),
        )

    # ------------------------------------------------------------------
    # PHASE 5 — Append undo entry to import_history.json
    # ------------------------------------------------------------------
    _append_undo_history_entry(
        run_dir=run_dir,
        run_id=run_id,
        corrected_at=corrected_at,
        undone_correction_id=undone_correction_id,
        undone_correction_mode="replace",
        undone_decision_ids=restored_decision_ids,
        source_history_entry_index=target_index,
        archive_refs=archive_refs,
        history_data=history_data,
        entries_list=entries_list,
        warnings=warnings,
    )

    # ------------------------------------------------------------------
    # PHASE 6 — Post-validation
    # ------------------------------------------------------------------
    trace_result = _postcheck_source_url_traceability(run_dir)
    if not trace_result.get("validation_passed", False):
        # Update manifest with actual traceability result even on failure
        _update_manifest_traceability(run_dir, manifest_data, trace_result)
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Post-undo source URL traceability check failed: "
                f"placeholder_count={trace_result.get('placeholder_count', '?')}, "
                f"missing_count={trace_result.get('missing_count', '?')}. "
                f"Artifacts may be in inconsistent state."
            ),
        )

    _update_manifest_traceability(run_dir, manifest_data, trace_result)

    return UndoResult(
        run_id=run_id,
        run_dir=str(run_dir),
        undone_correction_id=undone_correction_id,
        undone_correction_mode="replace",
        undone_at=corrected_at,
        restored_decision_ids=restored_decision_ids,
        removed_decision_ids=removed_decision_ids,
        derived_artifacts_rebuilt=True,
        warnings=warnings,
        errors=[],
        artifacts_updated=artifacts_updated,
        validation_passed=True,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
        source_url_placeholder_count=trace_result.get("placeholder_count", 0),
        source_url_missing_count=trace_result.get("missing_count", 0),
        archive_refs=archive_refs,
    )


# ---------------------------------------------------------------------------
# Undo amend
# ---------------------------------------------------------------------------


def _undo_amend(
    *,
    run_dir: Path,
    project_root: Path,
    run_id: str,
    corrected_at: str,
    target_entry: dict[str, Any],
    target_index: int,
    old_decision_ids: list[str],
    undone_correction_id: str,
    current_by_did: dict[str, dict[str, Any]],
    current_items: list[dict[str, Any]],
    manifest_data: dict[str, Any],
    history_data: dict[str, Any],
    entries_list: list[dict[str, Any]],
    output_mode: str = "ascii_safe",
) -> UndoResult:
    """Undo an amend correction."""
    warnings: list[str] = []

    # Locate and validate the amended_decisions/ archive
    archive_refs = _find_amend_archive(
        run_dir=run_dir,
        target_entry=target_entry,
        old_decision_ids=old_decision_ids,
    )
    if isinstance(archive_refs, UndoResult):
        return archive_refs  # error result

    archive_path = run_dir / archive_refs["amended_decisions"]
    try:
        archive_data = json.loads(archive_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Archive is corrupt: {archive_path}. "
                f"JSON parse error: {exc.msg}."
            ),
        )

    archived_items_raw = archive_data.get("items", [])
    if not isinstance(archived_items_raw, list):
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Archive is corrupt: {archive_path}. "
                f"'items' field is not a list."
            ),
        )

    # Build archived item lookup by decision_id
    archived_by_did: dict[str, dict[str, Any]] = {}
    archived_dids: set[str] = set()
    for item in archived_items_raw:
        if isinstance(item, dict) and item.get("decision_id"):
            did = str(item["decision_id"])
            archived_by_did[did] = item
            archived_dids.add(did)

    # Validate: each old_decision_id must exist in the archive
    for did in old_decision_ids:
        if did not in archived_by_did:
            return _fail(
                run_dir=run_dir,
                corrected_at=corrected_at,
                message=(
                    f"Archive content mismatch: decision ID '{did}' "
                    f"listed in correction entry but not found in archive: {archive_path}."
                ),
            )

    # Validate: each old_decision_id must still exist in current decisions
    for did in old_decision_ids:
        if did not in current_by_did:
            return _fail(
                run_dir=run_dir,
                corrected_at=corrected_at,
                message=(
                    f"Decision '{did}' not found in current "
                    f"founder_decisions_v2.json. Cannot restore notes."
                ),
            )

    # Restore notes from archive
    updated_items: list[dict[str, Any]] = []
    for item in current_items:
        if isinstance(item, dict):
            did = str(item.get("decision_id", ""))
            if did in archived_by_did:
                archived_item = archived_by_did[did]
                # Copy the item but restore notes (and optionally reasons)
                restored = dict(item)
                restored["notes"] = str(archived_item.get("notes", ""))
                # Also restore reason_categories from archive's reasons
                archived_reasons = archived_item.get("reasons", [])
                if archived_reasons:
                    restored["reasons"] = list(archived_reasons)
                updated_items.append(restored)
            else:
                updated_items.append(item)
        else:
            updated_items.append(item)

    restored_decision_ids = sorted(old_decision_ids)
    schemas = canonical_artifact_schema_versions()
    artifacts_updated: list[str] = []

    try:
        # Write updated founder_decisions_v2.json
        decisions_write: dict[str, Any] = {
            "items": updated_items,
            "schema_version": schemas["founder_decisions_v2"],
            "empty": len(updated_items) == 0,
            "imported": True,
            "note": "Founder decision notes restored via undo-last (v2.10 item 2.1).",
        }
        _write_json_atomic(run_dir, paths()["founder_decisions_v2"], decisions_write)
        artifacts_updated.append("founder_decisions_v2")

        # Update manifest (no derived artifact rebuild)
        manifest_data["undone_decision_ids"] = restored_decision_ids
        manifest_data["undone_at"] = corrected_at
        manifest_data["undone_correction_id"] = undone_correction_id
        manifest_data["undo_result_summary"] = {
            "undo_mode": "undo_last",
            "undone_correction_mode": "amend",
            "undone_correction_id": undone_correction_id,
            "restored_decision_count": len(restored_decision_ids),
            "removed_decision_count": 0,
            "derived_artifacts_rebuilt": False,
            "source_url_traceability_passed": False,
            "source_url_placeholder_count": 0,
            "source_url_missing_count": 0,
        }
        _write_json_atomic(run_dir, paths()["manifest"], manifest_data)
        artifacts_updated.append("manifest")

    except (OSError, ValueError, TypeError) as exc:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=f"Artifact write failed: {exc}.",
        )

    # ------------------------------------------------------------------
    # PHASE 3 — Regenerate reports and dashboard
    # ------------------------------------------------------------------
    regen_ok, regen_errors = _regenerate_reports_and_dashboard(
        project_root=project_root,
        run_dir=run_dir,
        run_id=run_id,
        output_mode=output_mode,
    )
    if not regen_ok:
        return _fail(
            run_dir=run_dir,
            corrected_at=corrected_at,
            message=(
                f"Report/dashboard regeneration failed: "
                f"{'; '.join(regen_errors)}. "
                f"Undo aborted — no undo CorrectionEntry appended."
            ),
        )

    # Append undo entry to import_history.json
    _append_undo_history_entry(
        run_dir=run_dir,
        run_id=run_id,
        corrected_at=corrected_at,
        undone_correction_id=undone_correction_id,
        undone_correction_mode="amend",
        undone_decision_ids=restored_decision_ids,
        source_history_entry_index=target_index,
        archive_refs=archive_refs,
        history_data=history_data,
        entries_list=entries_list,
        warnings=warnings,
    )

    # Post-check source URL traceability
    trace_result = _postcheck_source_url_traceability(run_dir)
    _update_manifest_traceability(run_dir, manifest_data, trace_result)

    if not trace_result.get("validation_passed", False):
        warnings.append(
            f"Post-undo source URL traceability check had issues: "
            f"placeholder_count={trace_result.get('placeholder_count', 0)}, "
            f"missing_count={trace_result.get('missing_count', 0)}."
        )

    return UndoResult(
        run_id=run_id,
        run_dir=str(run_dir),
        undone_correction_id=undone_correction_id,
        undone_correction_mode="amend",
        undone_at=corrected_at,
        restored_decision_ids=restored_decision_ids,
        removed_decision_ids=[],
        derived_artifacts_rebuilt=False,
        warnings=warnings + trace_result.get("warnings", []),
        errors=[],
        artifacts_updated=artifacts_updated,
        validation_passed=trace_result.get("validation_passed", True),
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
        source_url_placeholder_count=trace_result.get("placeholder_count", 0),
        source_url_missing_count=trace_result.get("missing_count", 0),
        archive_refs=archive_refs,
    )


# ---------------------------------------------------------------------------
# Archive location helpers
# ---------------------------------------------------------------------------


def _find_replace_archive(
    *,
    run_dir: Path,
    target_entry: dict[str, Any],
    old_decision_ids: list[str],
) -> dict[str, str] | UndoResult:
    """Locate and validate the replaced_decisions/ archive for undo-replace.

    Returns dict of {archive_type: archive_filename} on success,
    or UndoResult on failure.
    """
    archive_dir = run_dir / "replaced_decisions"

    # Try to locate the archive from old_artifact_checksums in the entry
    old_checksums = target_entry.get("old_artifact_checksums", {})
    archive_rel_path: str | None = None

    if isinstance(old_checksums, dict):
        # Look for the archive file referenced by checksums
        # The archive file may be referenced via the corrected_at or entry metadata
        pass

    # Fall back to finding the most recent archive in replaced_decisions/
    if archive_dir.is_dir():
        archive_files = sorted(
            archive_dir.glob("founder_decisions_v2_replaced_*.json"),
            key=lambda p: p.name,
            reverse=True,
        )
        if archive_files:
            archive_rel_path = str(archive_files[0].relative_to(run_dir))
        else:
            return _fail(
                run_dir=run_dir,
                corrected_at="",
                message=(
                    f"Archive not found: no replaced_decisions/ archive in {archive_dir}. "
                    f"Cannot restore pre-correction state."
                ),
            )
    else:
        return _fail(
            run_dir=run_dir,
            corrected_at="",
            message=(
                f"Archive not found: {archive_dir}. "
                f"Cannot restore pre-correction state."
            ),
        )

    # Verify the archive contains the expected decision IDs
    archive_path = run_dir / archive_rel_path
    if not archive_path.is_file():
        return _fail(
            run_dir=run_dir,
            corrected_at="",
            message=(
                f"Archive not found: {archive_path}. "
                f"Cannot restore pre-correction state."
            ),
        )

    try:
        archive_check = json.loads(archive_path.read_text(encoding="utf-8"))
        archived_ids_raw = archive_check.get("replaced_decision_ids", [])
        if not isinstance(archived_ids_raw, list):
            return _fail(
                run_dir=run_dir,
                corrected_at="",
                message=(
                    f"Archive is corrupt: {archive_path}. "
                    f"'replaced_decision_ids' field is not a list."
                ),
            )
        archived_ids = set(str(did) for did in archived_ids_raw)

        # Validate the archive contains the expected old_decision_ids
        expected = set(old_decision_ids)
        if not expected.issubset(archived_ids):
            missing = expected - archived_ids
            return _fail(
                run_dir=run_dir,
                corrected_at="",
                message=(
                    f"Archive content mismatch: expected decision IDs "
                    f"{sorted(expected)}, found {sorted(archived_ids)} "
                    f"in {archive_path}. Missing: {sorted(missing)}."
                ),
            )
    except json.JSONDecodeError as exc:
        return _fail(
            run_dir=run_dir,
            corrected_at="",
            message=(
                f"Archive is corrupt: {archive_path}. "
                f"JSON parse error: {exc.msg}."
            ),
        )

    return {"replaced_decisions": archive_rel_path}


def _find_amend_archive(
    *,
    run_dir: Path,
    target_entry: dict[str, Any],
    old_decision_ids: list[str],
) -> dict[str, str] | UndoResult:
    """Locate and validate the amended_decisions/ archive for undo-amend."""
    archive_dir = run_dir / "amended_decisions"

    if not archive_dir.is_dir():
        return _fail(
            run_dir=run_dir,
            corrected_at="",
            message=(
                f"Archive not found: {archive_dir}. "
                f"Cannot restore pre-amendment notes."
            ),
        )

    archive_files = sorted(
        archive_dir.glob("founder_decisions_v2_amended_*.json"),
        key=lambda p: p.name,
        reverse=True,
    )

    if not archive_files:
        return _fail(
            run_dir=run_dir,
            corrected_at="",
            message=(
                f"Archive not found: no amended_decisions/ archive in {archive_dir}. "
                f"Cannot restore pre-amendment notes."
            ),
        )

    archive_rel_path = str(archive_files[0].relative_to(run_dir))
    archive_path = run_dir / archive_rel_path

    if not archive_path.is_file():
        return _fail(
            run_dir=run_dir,
            corrected_at="",
            message=(
                f"Archive not found: {archive_path}. "
                f"Cannot restore pre-amendment notes."
            ),
        )

    try:
        archive_check = json.loads(archive_path.read_text(encoding="utf-8"))
        amended_ids_raw = archive_check.get("amended_decision_ids", [])
        if not isinstance(amended_ids_raw, list):
            return _fail(
                run_dir=run_dir,
                corrected_at="",
                message=(
                    f"Archive is corrupt: {archive_path}. "
                    f"'amended_decision_ids' field is not a list."
                ),
            )
        amended_ids = set(str(did) for did in amended_ids_raw)

        expected = set(old_decision_ids)
        if not expected.issubset(amended_ids):
            missing = expected - amended_ids
            return _fail(
                run_dir=run_dir,
                corrected_at="",
                message=(
                    f"Archive content mismatch: expected decision IDs "
                    f"{sorted(expected)}, found {sorted(amended_ids)} "
                    f"in {archive_path}. Missing: {sorted(missing)}."
                ),
            )
    except json.JSONDecodeError as exc:
        return _fail(
            run_dir=run_dir,
            corrected_at="",
            message=(
                f"Archive is corrupt: {archive_path}. "
                f"JSON parse error: {exc.msg}."
            ),
        )

    return {"amended_decisions": archive_rel_path}


# ---------------------------------------------------------------------------
# Report/dashboard regeneration
# ---------------------------------------------------------------------------


def _regenerate_reports_and_dashboard(
    *,
    project_root: Path,
    run_dir: Path,
    run_id: str,
    output_mode: str = "ascii_safe",
) -> tuple[bool, list[str]]:
    """Regenerate per-run report and cross-run dashboard after undo.

    Calls the existing deterministic builder + writer APIs from
    weekly_run_reports.py. These are read-only builders that inspect the
    on-disk artifacts — which are now in the post-undo state.

    Regeneration is required by contract (docs/contracts/undo_last_contract.md
    Sections 5.2 and 5.3). Failures propagate upward so undo can fail-closed
    before appending the undo CorrectionEntry.

    Returns:
        (True, []) on success, (False, [error_messages]) on failure.

    No live API/LLM calls. No new decisions. Deterministic.
    """
    errors: list[str] = []

    # Regenerate per-run report
    try:
        report = build_weekly_run_report(
            project_root=project_root,
            run_id=run_id,
        )
        write_weekly_run_report(report, run_dir, output_mode=output_mode)
    except Exception as exc:
        errors.append(f"run_report regeneration failed: {exc}")

    # Regenerate cross-run dashboard
    try:
        weekly_runs_root = run_dir.parent  # <pr>/artifacts/weekly_runs/
        dashboard = build_weekly_dashboard_index(project_root=project_root)
        write_weekly_dashboard_index(dashboard, weekly_runs_root, output_mode=output_mode)
    except Exception as exc:
        errors.append(f"dashboard_index regeneration failed: {exc}")

    if errors:
        return (False, errors)
    return (True, [])


# ---------------------------------------------------------------------------
# History append
# ---------------------------------------------------------------------------


def _append_undo_history_entry(
    *,
    run_dir: Path,
    run_id: str,
    corrected_at: str,
    undone_correction_id: str,
    undone_correction_mode: str,
    undone_decision_ids: list[str],
    source_history_entry_index: int,
    archive_refs: dict[str, str],
    history_data: dict[str, Any],
    entries_list: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    """Append a new CorrectionEntry with correction_mode = "undo" to import_history.json.

    Existing entries are never modified or deleted (append-only).
    """
    history_path = run_dir / "import_history.json"

    # Generate deterministic undo correction_id
    key = "|".join([
        run_id,
        corrected_at,
        undone_correction_id,
        ",".join(sorted(undone_decision_ids)),
    ])
    undo_correction_id = "undo_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    # Build the undo entry dict
    undo_entry: dict[str, Any] = {
        "correction_id": undo_correction_id,
        "corrected_at": corrected_at,
        "correction_mode": "undo",
        "replaced_review_item_ids": [],
        "old_decision_ids": [],
        "new_decision_ids": [],
        "old_artifact_checksums": {},
        "new_artifact_checksums": {},
        "warnings": sorted(warnings),
        "errors": [],
        "advisory_only": True,
        "no_live_api": True,
        "no_live_llm": True,
        "undone_correction_id": undone_correction_id,
        "undone_correction_mode": undone_correction_mode,
        "undone_decision_ids": sorted(undone_decision_ids),
        "undone_at": corrected_at,
        "source_history_entry_index": source_history_entry_index,
        "archive_refs": dict(archive_refs),
        "notes": [
            f"Undid {undone_correction_mode} correction "
            f"'{undone_correction_id}' "
            f"restoring {len(undone_decision_ids)} decision(s)."
        ],
    }

    # Append to existing entries
    new_entries = list(entries_list) + [undo_entry]

    history_data["entries"] = new_entries

    history_path.write_text(
        json.dumps(history_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Source URL traceability helpers
# ---------------------------------------------------------------------------


def _precheck_source_url_traceability(
    *,
    decisions: list[FounderDecisionV2],
    context: str = "pre-check",
) -> dict[str, Any] | None:
    """Perform an in-memory source URL traceability pre-check.

    Checks that every decision has real http/https source URLs and no
    placeholder URNs. Returns None if check cannot be performed,
    or a dict with validation_passed, placeholder_count, missing_count.
    """
    from oos.source_url_traceability import (
        is_placeholder_source_url,
        is_real_source_url,
    )
    placeholder_count = 0
    missing_count = 0

    for d in decisions:
        urls = list(d.linked_source_urls)
        if not urls:
            missing_count += 1
            continue
        has_real = False
        for url in urls:
            if is_placeholder_source_url(url):
                placeholder_count += 1
            elif is_real_source_url(url):
                has_real = True
        if not has_real:
            missing_count += 1

    return {
        "validation_passed": placeholder_count == 0 and missing_count == 0,
        "placeholder_count": placeholder_count,
        "missing_count": missing_count,
    }


def _postcheck_source_url_traceability(run_dir: Path) -> dict[str, Any]:
    """Run the full source URL traceability check on the on-disk state."""
    try:
        report = check_source_url_traceability(run_dir)
        return {
            "validation_passed": report.validation_passed,
            "placeholder_count": report.placeholder_url_count,
            "missing_count": report.missing_source_url_count,
            "warnings": [],
        }
    except (OSError, ValueError, TypeError) as exc:
        return {
            "validation_passed": False,
            "placeholder_count": -1,
            "missing_count": -1,
            "warnings": [f"Source URL traceability check failed: {exc}"],
        }


def _update_manifest_traceability(
    run_dir: Path,
    manifest_data: dict[str, Any],
    trace_result: dict[str, Any],
) -> None:
    """Update manifest.json with source URL traceability result."""
    summary = manifest_data.get("undo_result_summary", {})
    if isinstance(summary, dict):
        summary["source_url_traceability_passed"] = trace_result.get(
            "validation_passed", False
        )
        summary["source_url_placeholder_count"] = trace_result.get(
            "placeholder_count", 0
        )
        summary["source_url_missing_count"] = trace_result.get(
            "missing_count", 0
        )
        manifest_data["undo_result_summary"] = summary
    _write_json_atomic(run_dir, paths()["manifest"], manifest_data)


# ---------------------------------------------------------------------------
# Atomic write helper (mirrors founder_decision_import._write_json_atomic)
# ---------------------------------------------------------------------------


def _write_json_atomic(run_dir: Path, filename: str, data: Any) -> Path:
    """Write JSON data atomically via write-then-rename pattern."""
    path = run_dir / filename
    tmp_path = run_dir / f"{filename}.tmp"

    content = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    tmp_path.write_text(content, encoding="utf-8")

    # Read back and validate parseable
    try:
        json.loads(tmp_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        tmp_path.unlink(missing_ok=True)
        raise ValueError(f"Atomic write validation failed for {filename}: {exc}") from exc

    tmp_path.replace(path)
    return path


# ---------------------------------------------------------------------------
# CLI output helpers
# ---------------------------------------------------------------------------


def format_undo_result_output(
    result: UndoResult,
    *,
    use_utf8: bool = False,
) -> str:
    """Format an UndoResult as terminal output (ASCII-safe or UTF-8).

    Follows the output format specified in docs/contracts/undo_last_contract.md
    Section 9.3–9.6.
    """
    ok_marker = "\u2713" if use_utf8 else "OK"
    fail_marker = "\u2717" if use_utf8 else "FAIL"

    if not result.validation_passed:
        lines = [
            f"Undo-last correction: {fail_marker}",
            "",
            f"Error: {result.errors[0] if result.errors else 'Unknown error'}",
            "",
            "No artifacts were modified.",
        ]
        return "\n".join(lines)

    lines = [
        f"Undo-last correction: {ok_marker}",
        "",
        "Undone correction:",
        f"  correction_id:   {result.undone_correction_id}",
        f"  correction_mode: {result.undone_correction_mode}",
        f"  corrected_at:    {result.undone_at}",
        "",
    ]

    # Restored decisions
    lines.append("Restored:")
    for did in result.restored_decision_ids:
        lines.append(f"  Decision ID: {did}")
    lines.append(f"  Total restored: {len(result.restored_decision_ids)}")
    lines.append("")

    # Removed decisions (replace only)
    if result.removed_decision_ids:
        lines.append("Removed:")
        for did in result.removed_decision_ids:
            lines.append(f"  Decision ID: {did}")
        lines.append(f"  Total removed: {len(result.removed_decision_ids)}")
        lines.append("")

    # Derived artifacts
    if result.derived_artifacts_rebuilt:
        lines.append("Derived artifacts rebuilt:")
        for artifact in result.artifacts_updated:
            if artifact != "manifest":
                lines.append(f"  {artifact}  — {ok_marker}")
        lines.append("")
    else:
        lines.append(
            "Derived artifacts: No rebuild needed "
            "(amend undo restores notes only)."
        )
        lines.append("")

    # Source URL traceability
    lines.append(
        f"Source URL traceability: {ok_marker} "
        f"(placeholder_count={result.source_url_placeholder_count}, "
        f"missing_count={result.source_url_missing_count})"
    )
    lines.append("")

    lines.append(
        "Undo complete. A new undo entry has been appended to import_history.json."
    )
    lines.append(
        "Original correction entry preserved. Archive files preserved."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fail(
    *,
    run_dir: Path,
    corrected_at: str,
    message: str,
) -> UndoResult:
    """Return a failed UndoResult with no artifacts modified."""
    return UndoResult(
        run_dir=str(run_dir),
        undone_at=corrected_at,
        errors=[message],
        validation_passed=False,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )


def _safe_string_list(raw: Any) -> list[str]:
    """Normalize to a sorted list of non-empty strings."""
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    for item in raw:
        if item is None:
            continue
        s = str(item).strip()
        if s:
            result.append(s)
    return sorted(dict.fromkeys(result))


def _to_safe_dict(obj: Any) -> dict[str, Any]:
    """Convert an object to a dict safely, falling back to empty dict."""
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return {}


def paths() -> dict[str, str]:
    """Shortcut for canonical_artifact_paths()."""
    return canonical_artifact_paths()
