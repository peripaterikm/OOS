"""Founder Decision Import — deterministic import of explicit founder decisions.

Roadmap v2.6 item 5.1. Reads a founder decisions file (JSON array or JSONL)
and integrates validated decisions into a weekly run's artifacts.

Fail-closed: if any input decision is invalid, no artifacts are written.
Reject duplicates: duplicate review_item_id entries are rejected.
Idempotent: re-running the same import yields identical artifact state.

Roadmap v2.8 item 1.3: Safe replace/amend correction modes:
- replace_review_item_ids: surgical replacement of listed review items
- amend_notes_only: notes/reason amendment (decision value unchanged)

Roadmap v2.8 item 2.1: Import history / audit trail (hardened here).
- import_history.json is append-only; entries are never modified or deleted.
- CorrectionEntry JSON roundtrip is deterministic (sort_keys=True).
- correction_id is deterministic (SHA-256 of composite key).
- Failed correction attempts do NOT append history entries.
- read_import_history() and build_import_history_summary() are the public
  read API for status/report visibility.

No live LLM/API calls. No autonomous decisions. No portfolio mutations.
Advisory-only throughout.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from oos.founder_decision_taxonomy import (
    ALLOWED_DECISIONS,
    REASONS_BY_DECISION,
    FounderDecisionReason,
    FounderDecisionV2,
    create_founder_decision,
    founder_decision_to_dict,
)
from oos.founder_feedback_mapping import (
    FounderFeedbackMapping,
    founder_feedback_mapping_to_dict,
    map_founder_decision_to_feedback,
)
from oos.founder_preference_profile import (
    FounderPreferenceProfile,
    build_founder_preference_profile,
    founder_preference_profile_to_dict,
)
from oos.parking_lot import (
    ParkingLotRecord,
    build_parking_lot_records,
    parking_lot_records_to_json,
)
from oos.source_url_traceability import is_placeholder_source_url, is_real_source_url
from oos.weekly_run_manifest import (
    canonical_artifact_paths,
    canonical_artifact_schema_versions,
)
from oos.decision_correction_rebuild import (
    cleanup_orphaned_parking_lot_records,
    rebuild_founder_decision_derived_artifacts,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FOUNDER_DECISION_IMPORT_SCHEMA_VERSION = "founder_decision_import.v1"
IMPORT_HISTORY_SCHEMA_VERSION = "import_history.v1"

# Mapping from input decision values (uppercase) to taxonomy values (lowercase)
_DECISION_ALIASES: dict[str, str] = {
    "PROMOTE": "promote",
    "PARK": "park",
    "KILL": "kill",
    "NEEDS_MORE_EVIDENCE": "needs_more_evidence",
    "REVISIT_LATER": "revisit_later",
}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class FounderDecisionImportInput:
    """Parsed input decisions ready for validation."""

    decisions: list[dict[str, Any]]


@dataclass
class FounderDecisionImportResult:
    """Result of a founder decision import operation."""

    run_id: str = ""
    imported_count: int = 0
    rejected_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    artifacts_updated: list[str] = field(default_factory=list)
    validation_passed: bool = False
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True
    schema_version: str = FOUNDER_DECISION_IMPORT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "imported_count": self.imported_count,
            "rejected_count": self.rejected_count,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "artifacts_updated": list(self.artifacts_updated),
            "validation_passed": self.validation_passed,
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
            "schema_version": self.schema_version,
        }


# ---------------------------------------------------------------------------
# Correction entry / import history models (v2.8 item 1.3)
# ---------------------------------------------------------------------------


@dataclass
class CorrectionEntry:
    """A single correction operation record for the import history audit trail.

    Roadmap v2.8 items 1.3 + 2.1 — every replace or amend operation produces
    one CorrectionEntry appended to {run_dir}/import_history.json.

    Append-only contract: entries are never modified or deleted once written.
    Failed correction attempts do NOT create entries.
    correction_id is deterministic: SHA-256(run_id|corrected_at|mode|old_ids|new_ids)[:12].
    JSON roundtrip is deterministic via sort_keys=True in _write_import_history().
    """

    correction_id: str
    corrected_at: str
    correction_mode: str  # "replace" | "amend"
    replaced_review_item_ids: list[str] = field(default_factory=list)
    old_decision_ids: list[str] = field(default_factory=list)
    new_decision_ids: list[str] = field(default_factory=list)
    old_artifact_checksums: dict[str, str] = field(default_factory=dict)
    new_artifact_checksums: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "correction_id": self.correction_id,
            "corrected_at": self.corrected_at,
            "correction_mode": self.correction_mode,
            "replaced_review_item_ids": sorted(self.replaced_review_item_ids),
            "old_decision_ids": sorted(self.old_decision_ids),
            "new_decision_ids": sorted(self.new_decision_ids),
            "old_artifact_checksums": dict(sorted(self.old_artifact_checksums.items())),
            "new_artifact_checksums": dict(sorted(self.new_artifact_checksums.items())),
            "warnings": sorted(self.warnings),
            "errors": sorted(self.errors),
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
        }


@dataclass
class ImportHistoryLog:
    """Append-only log of correction operations for a single run.

    Written to {run_dir}/import_history.json.  Entries are never modified
    or deleted once written (append-only contract per v2.8 item 2.1).

    The file uses sort_keys=True for deterministic JSON roundtrip.
    """

    schema_version: str = IMPORT_HISTORY_SCHEMA_VERSION
    run_id: str = ""
    entries: list[CorrectionEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "entries": [e.to_dict() for e in self.entries],
        }

    def entry_count(self) -> int:
        """Return the number of correction entries in this log."""
        return len(self.entries)

    def latest_correction_mode(self) -> str:
        """Return the correction_mode of the last entry, or empty string."""
        if not self.entries:
            return ""
        return self.entries[-1].correction_mode

    def correction_modes_summary(self) -> dict[str, int]:
        """Return counts of correction entries by mode."""
        counts: dict[str, int] = {}
        for e in self.entries:
            mode = e.correction_mode
            counts[mode] = counts.get(mode, 0) + 1
        return counts

    def all_replaced_decision_ids(self) -> list[str]:
        """Return sorted unique replaced decision IDs across all entries
        that are 'replace' mode (not amend)."""
        ids: set[str] = set()
        for e in self.entries:
            if e.correction_mode == "replace":
                ids.update(e.old_decision_ids)
        return sorted(ids)

    def all_amended_decision_ids(self) -> list[str]:
        """Return sorted unique amended decision IDs across all entries."""
        ids: set[str] = set()
        for e in self.entries:
            if e.correction_mode == "amend":
                ids.update(e.old_decision_ids)
        return sorted(ids)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ImportHistoryLog":
        log = ImportHistoryLog(
            schema_version=str(data.get("schema_version", IMPORT_HISTORY_SCHEMA_VERSION)),
            run_id=str(data.get("run_id", "")),
        )
        for entry_data in data.get("entries", []):
            if isinstance(entry_data, dict):
                log.entries.append(
                    CorrectionEntry(
                        correction_id=str(entry_data.get("correction_id", "")),
                        corrected_at=str(entry_data.get("corrected_at", "")),
                        correction_mode=str(entry_data.get("correction_mode", "")),
                        replaced_review_item_ids=_safe_string_list(entry_data.get("replaced_review_item_ids", [])),
                        old_decision_ids=_safe_string_list(entry_data.get("old_decision_ids", [])),
                        new_decision_ids=_safe_string_list(entry_data.get("new_decision_ids", [])),
                        old_artifact_checksums=_safe_str_dict(entry_data.get("old_artifact_checksums", {})),
                        new_artifact_checksums=_safe_str_dict(entry_data.get("new_artifact_checksums", {})),
                        warnings=_safe_string_list(entry_data.get("warnings", [])),
                        errors=_safe_string_list(entry_data.get("errors", [])),
                        advisory_only=bool(entry_data.get("advisory_only", True)),
                        no_live_api=bool(entry_data.get("no_live_api", True)),
                        no_live_llm=bool(entry_data.get("no_live_llm", True)),
                    )
                )
        return log


# ---------------------------------------------------------------------------
# Loading / parsing
# ---------------------------------------------------------------------------


def load_founder_decision_inputs(decisions_file: Path) -> FounderDecisionImportInput:
    """Load and parse a founder decisions file.

    Supports:
    - JSON array: [{"review_item_id": "...", "decision": "PARK", ...}, ...]
    - JSONL: one JSON object per line

    Args:
        decisions_file: Path to the decisions file.

    Returns:
        FounderDecisionImportInput with parsed decisions.

    Raises:
        FileNotFoundError: decisions_file does not exist.
        ValueError: malformed or empty input.
    """
    if not decisions_file.is_file():
        raise FileNotFoundError(f"Decisions file not found: {decisions_file}")

    raw = decisions_file.read_text(encoding="utf-8-sig").strip()
    if not raw:
        raise ValueError("Decisions file is empty")

    # Try JSON array first
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            if len(data) == 0:
                raise ValueError("Decisions file contains empty JSON array")
            return FounderDecisionImportInput(decisions=list(data))
        if isinstance(data, dict):
            # Single decision object
            return FounderDecisionImportInput(decisions=[data])
        raise ValueError("Decisions file must contain a JSON array or single JSON object")
    except json.JSONDecodeError:
        pass

    # Try JSONL
    decisions: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {line_number}: {exc.msg}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"Invalid JSONL at line {line_number}: expected object")
        decisions.append(obj)

    if not decisions:
        raise ValueError("Decisions file contains no valid decision entries")

    return FounderDecisionImportInput(decisions=decisions)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_founder_decision_inputs(
    inputs: FounderDecisionImportInput,
    inbox_index: dict[str, Any],
    *,
    existing_decisions: list[FounderDecisionV2] | None = None,
    replace_review_item_ids: set[str] | None = None,
    amend_notes_only: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate parsed decision inputs against the founder inbox v2 index.

    Checks:
    - review_item_id is present and non-empty
    - review_item_id exists in the inbox index
    - decision value is allowed
    - reason_categories are valid for the given decision (if taxonomy requires)
    - no duplicate review_item_id entries in the input
    - no review_item_id already has an existing decision (idempotency guard)

    Correction modes (v2.8 item 1.3):
    - replace_review_item_ids: if set, skip idempotency guard for these rids.
    - amend_notes_only: if True, only notes/reason_categories may change;
      decision value changes are rejected.

    Returns:
        Tuple of (valid_decisions, validation_errors).
        If validation_errors is non-empty, valid_decisions is empty
        and no artifacts should be written (fail-closed).
    """
    errors: list[str] = []
    valid: list[dict[str, Any]] = []
    existing_decision_ids: set[str] = set()
    replace_rids: set[str] = replace_review_item_ids or set()

    if existing_decisions:
        for ed in existing_decisions:
            existing_decision_ids.add(ed.decision_id)

    # Build lookup: review_item_id -> inbox item
    review_items = inbox_index.get("review_items", [])
    if not isinstance(review_items, list):
        errors.append("inbox_index.review_items must be a list")
        return [], errors

    inbox_by_review_id: dict[str, dict[str, Any]] = {}
    for item in review_items:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("review_item_id", ""))
        if rid:
            inbox_by_review_id[rid] = item

    if not inbox_by_review_id:
        errors.append("Inbox index contains no review items with valid review_item_id values")
        return [], errors

    # Track seen review_item_ids in input for duplicate detection
    seen_rids: set[str] = set()

    for idx, decision_input in enumerate(inputs.decisions, start=1):
        item_errors: list[str] = []

        review_item_id = str(decision_input.get("review_item_id", "")).strip()
        if not review_item_id:
            item_errors.append(f"Item {idx}: review_item_id is missing or empty")
            errors.extend(item_errors)
            continue

        # Duplicate in input?
        if review_item_id in seen_rids:
            item_errors.append(
                f"Item {idx}: duplicate review_item_id '{review_item_id}' — "
                f"each review_item_id must appear only once"
            )
        else:
            seen_rids.add(review_item_id)

        # Exists in inbox?
        inbox_item = inbox_by_review_id.get(review_item_id)
        if inbox_item is None:
            item_errors.append(
                f"Item {idx}: review_item_id '{review_item_id}' not found in inbox index"
            )
        else:
            # Already decided? (check by looking for matching decision with this review_item_id
            # in existing founder decisions; we check by opportunity_id match below)
            pass

        # Decision value
        raw_decision = str(decision_input.get("decision", "")).strip()
        if not raw_decision:
            item_errors.append(f"Item {idx}: decision is missing")
        elif raw_decision.upper() not in _DECISION_ALIASES:
            allowed = sorted(_DECISION_ALIASES.keys())
            item_errors.append(
                f"Item {idx}: invalid decision '{raw_decision}'. "
                f"Allowed: {', '.join(allowed)}"
            )
        elif inbox_item is not None:
            # Check that decision is in the item's decision_options (if present)
            item_options = inbox_item.get("decision_options", [])
            if item_options and raw_decision.upper() not in item_options:
                item_errors.append(
                    f"Item {idx}: decision '{raw_decision}' not in inbox item's "
                    f"decision_options: {item_options}"
                )

        # Reason categories
        reason_categories = _extract_reason_categories(decision_input.get("reason_categories", None))
        notes = str(decision_input.get("notes", "")).strip()

        # If decision is valid, validate reason categories
        normalized_decision = _DECISION_ALIASES.get(raw_decision.upper(), "")
        if normalized_decision and normalized_decision in REASONS_BY_DECISION:
            allowed_reasons = set(REASONS_BY_DECISION[normalized_decision])
            invalid_reasons = sorted(set(reason_categories) - allowed_reasons)
            if invalid_reasons:
                item_errors.append(
                    f"Item {idx}: invalid reason categories for '{normalized_decision}': "
                    f"{', '.join(invalid_reasons)}. "
                    f"Allowed: {', '.join(sorted(allowed_reasons))}"
                )
            if not reason_categories:
                item_errors.append(
                    f"Item {idx}: at least one reason category is required for '{normalized_decision}'"
                )

        if item_errors:
            errors.extend(item_errors)
            continue

        # Check for existing decision via inbox item traceability
        # v2.8 item 1.3: skip idempotency guard for replace_review_item_ids
        if inbox_item is not None and existing_decisions:
            # In amend_notes_only mode, we don't check idempotency against
            # existing decisions (amend targets existing decisions, not new ones).
            # The amend validation is handled separately.
            if not amend_notes_only and review_item_id not in replace_rids:
                linked_opp_ids = inbox_item.get("linked_opportunity_ids", [])
                for ed in existing_decisions:
                    if ed.opportunity_id in linked_opp_ids:
                        item_errors.append(
                            f"Item {idx}: review_item_id '{review_item_id}' maps to "
                            f"opportunity '{ed.opportunity_id}' which already has a decision "
                            f"({ed.decision_id}); import is idempotent — remove this item "
                            f"or use a new review_item_id"
                        )
                        break

        if item_errors:
            errors.extend(item_errors)
            continue

        valid.append(decision_input)

    if errors:
        return [], errors

    return valid, []


def _extract_reason_categories(raw: Any) -> list[str]:
    """Extract reason_categories from various input shapes."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(r).strip() for r in raw if str(r).strip()]
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(r).strip() for r in parsed if str(r).strip()]
            except json.JSONDecodeError:
                pass
        return [s.strip() for s in stripped.split(",") if s.strip()]
    return []


# ---------------------------------------------------------------------------
# Main importer
# ---------------------------------------------------------------------------


def import_founder_decisions(
    project_root: Path,
    run_id: str,
    decisions_file: Path,
    *,
    replace_review_item_ids: list[str] | None = None,
    amend_notes_only: bool = False,
) -> FounderDecisionImportResult:
    """Import explicit founder decisions into a weekly run.

    Fail-closed: if any input decision is invalid, no artifacts are written.

    Correction modes (v2.8 item 1.3):
    - replace_review_item_ids: if provided, only listed review_item_ids are
      replaced; all others are untouched. Requires explicit opt-in.
    - amend_notes_only: if True, only notes/reason_categories may change;
      decision values are preserved.

    Without any correction flags, the default reject-on-reimport behavior
    is unchanged (v2.6/v2.7 behavior preserved).

    Args:
        project_root: Root directory of the OOS project.
        run_id: The weekly run ID to import decisions into.
        decisions_file: Path to the founder decisions file (JSON array or JSONL).
        replace_review_item_ids: Optional list of review_item_ids to replace.
        amend_notes_only: If True, only notes/reason_categories may change.

    Returns:
        FounderDecisionImportResult with import status and artifact paths.
    """
    project_root = project_root.resolve()
    decisions_file = decisions_file.resolve()
    run_dir = project_root / "artifacts" / "weekly_runs" / run_id
    corrected_at = datetime.now(timezone.utc).isoformat()

    # Normalize params
    replace_rids: set[str] = set()
    if replace_review_item_ids:
        replace_rids = {str(r).strip() for r in replace_review_item_ids if str(r).strip()}

    if not run_dir.is_dir():
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Run directory not found: {run_dir}"],
            validation_passed=False,
        )

    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Manifest not found: {manifest_path}"],
            validation_passed=False,
        )

    # Load manifest
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Invalid manifest JSON: {exc.msg}"],
            validation_passed=False,
        )

    # Load inbox index
    inbox_index_path = run_dir / canonical_artifact_paths()["founder_inbox_v2_index"]
    if not inbox_index_path.is_file():
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Founder inbox v2 index not found: {inbox_index_path}"],
            validation_passed=False,
        )

    try:
        inbox_index = json.loads(inbox_index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Invalid inbox index JSON: {exc.msg}"],
            validation_passed=False,
        )

    # Load existing decisions (for idempotency)
    existing_decisions: list[FounderDecisionV2] = []
    existing_decisions_raw: list[dict[str, Any]] = []
    existing_decision_path = run_dir / canonical_artifact_paths()["founder_decisions_v2"]
    if existing_decision_path.is_file():
        try:
            existing_data = json.loads(existing_decision_path.read_text(encoding="utf-8"))
            existing_items = existing_data.get("items", []) if isinstance(existing_data, dict) else []
            for item in existing_items:
                if isinstance(item, dict) and item.get("decision_id"):
                    existing_decisions_raw.append(item)
                    try:
                        existing_decisions.append(FounderDecisionV2.from_dict(item))
                    except (ValueError, TypeError):
                        pass
        except (json.JSONDecodeError, ValueError):
            pass

    # Load existing parking lot records
    existing_pl_records: list[dict[str, Any]] = []
    pl_path = run_dir / canonical_artifact_paths()["parking_lot_records"]
    if pl_path.is_file():
        try:
            pl_raw = json.loads(pl_path.read_text(encoding="utf-8"))
            existing_pl_records = pl_raw.get("items", []) if isinstance(pl_raw, dict) else []
            if not isinstance(existing_pl_records, list):
                existing_pl_records = []
        except (json.JSONDecodeError, ValueError):
            pass

    # Load inputs
    try:
        inputs = load_founder_decision_inputs(decisions_file)
    except (FileNotFoundError, ValueError) as exc:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[str(exc)],
            validation_passed=False,
        )

    # ------------------------------------------------------------------
    # Amend-notes-only: separate validation path
    # ------------------------------------------------------------------
    if amend_notes_only:
        return _import_amend_notes_only(
            run_dir=run_dir,
            run_id=run_id,
            inputs=inputs,
            inbox_index=inbox_index,
            existing_decisions=existing_decisions,
            manifest_data=manifest_data,
            corrected_at=corrected_at,
        )

    # Validate (with replace_review_item_ids awareness)
    valid_inputs, validation_errors = validate_founder_decision_inputs(
        inputs,
        inbox_index,
        existing_decisions=existing_decisions if existing_decisions else None,
        replace_review_item_ids=replace_rids if replace_rids else None,
    )

    if validation_errors:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=validation_errors,
            rejected_count=len(inputs.decisions),
            validation_passed=False,
        )

    # If in replace mode, ensure ALL incoming items are listed
    if replace_rids:
        incoming_rids = {str(d.get("review_item_id", "")).strip() for d in valid_inputs}
        extra = incoming_rids - replace_rids
        if extra:
            return FounderDecisionImportResult(
                run_id=run_id,
                errors=[
                    f"review_item_id(s) not in --replace-review-items: "
                    f"{', '.join(sorted(extra))}. All incoming review_item_ids "
                    f"must be explicitly listed when using replace mode."
                ],
                rejected_count=len(inputs.decisions),
                validation_passed=False,
            )
        # Ensure targets exist in existing decisions
        existing_by_rid, _missing = _map_existing_decisions_to_rid(
            existing_decisions=existing_decisions,
            inbox_index=inbox_index,
        )
        for rid in replace_rids:
            if rid not in existing_by_rid:
                return FounderDecisionImportResult(
                    run_id=run_id,
                    errors=[
                        f"review_item_id '{rid}' has no existing decision to replace."
                    ],
                    rejected_count=len(inputs.decisions),
                    validation_passed=False,
                )

    # Convert to FounderDecisionV2 (shared path)
    new_decisions, conversion_errors, warnings = _convert_inputs_to_decisions(
        valid_inputs=valid_inputs,
        inbox_index=inbox_index,
    )

    if conversion_errors:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=conversion_errors,
            rejected_count=len(inputs.decisions),
            validation_passed=False,
        )

    # ------------------------------------------------------------------
    # Replace mode: surgical replacement with derived artifact rebuild
    # ------------------------------------------------------------------
    if replace_rids:
        return _import_replace_mode(
            run_dir=run_dir,
            run_id=run_id,
            new_decisions=new_decisions,
            existing_decisions=existing_decisions,
            existing_decisions_raw=existing_decisions_raw,
            existing_pl_records=existing_pl_records,
            manifest_data=manifest_data,
            warnings=warnings,
            replace_rids=replace_rids,
            inbox_index=inbox_index,
            corrected_at=corrected_at,
        )

    # ------------------------------------------------------------------
    # Default mode: normal import (unchanged v2.6/v2.7 behavior)
    # ------------------------------------------------------------------

    # Merge with existing decisions (replace if same opportunity_id)
    all_decisions = _merge_decisions(existing_decisions, new_decisions)

    # Build feedback mappings
    all_mappings: list[FounderFeedbackMapping] = []
    for d in all_decisions:
        try:
            mapping = map_founder_decision_to_feedback(d)
            all_mappings.append(mapping)
        except (ValueError, TypeError) as exc:
            warnings.append(f"Feedback mapping skipped for {d.decision_id}: {exc}")

    # Build preference profile
    try:
        preference_profile = build_founder_preference_profile(
            decisions=all_decisions,
            feedback_mappings=all_mappings,
        )
    except (ValueError, TypeError) as exc:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Failed to build preference profile: {exc}"],
            validation_passed=False,
        )

    # Build parking lot records
    parking_lot_records = build_parking_lot_records(decisions=all_decisions)

    # Write artifacts
    artifacts_updated = _write_import_artifacts(
        run_dir=run_dir,
        all_decisions=all_decisions,
        all_mappings=all_mappings,
        preference_profile=preference_profile,
        parking_lot_records=parking_lot_records,
    )

    return FounderDecisionImportResult(
        run_id=run_id,
        imported_count=len(new_decisions),
        rejected_count=0,
        warnings=warnings,
        artifacts_updated=artifacts_updated,
        validation_passed=True,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )


# ---------------------------------------------------------------------------
# Convert helper
# ---------------------------------------------------------------------------


def _convert_inputs_to_decisions(
    *,
    valid_inputs: list[dict[str, Any]],
    inbox_index: dict[str, Any],
) -> tuple[list[FounderDecisionV2], list[str], list[str]]:
    """Convert validated input dicts to FounderDecisionV2 objects.

    Returns: (new_decisions, conversion_errors, warnings)
    """
    new_decisions: list[FounderDecisionV2] = []
    conversion_errors: list[str] = []
    warnings: list[str] = []

    inbox_items = inbox_index.get("review_items", [])
    inbox_by_rid: dict[str, dict[str, Any]] = {}
    for item in inbox_items:
        if isinstance(item, dict):
            rid = str(item.get("review_item_id", ""))
            if rid:
                inbox_by_rid[rid] = item

    for vi in valid_inputs:
        review_item_id = str(vi.get("review_item_id", "")).strip()
        raw_decision = str(vi.get("decision", "")).strip().upper()
        normalized_decision = _DECISION_ALIASES[raw_decision]
        reason_categories = _extract_reason_categories(vi.get("reason_categories", None))
        notes = str(vi.get("notes", "")).strip()

        inbox_item = inbox_by_rid.get(review_item_id)
        if inbox_item is None:
            conversion_errors.append(
                f"review_item_id '{review_item_id}' not found in inbox (unexpected)"
            )
            continue

        linked_opportunity_ids = _safe_string_list(inbox_item.get("linked_opportunity_ids", []))
        linked_evidence_pack_ids = _safe_string_list(inbox_item.get("linked_evidence_pack_ids", []))
        linked_evidence_ids = _safe_string_list(inbox_item.get("linked_evidence_ids", []))
        linked_quality_gate_ids = _safe_string_list(inbox_item.get("linked_quality_gate_ids", []))
        linked_action_ids = _safe_string_list(inbox_item.get("linked_action_ids", []))

        opportunity_id = linked_opportunity_ids[0] if linked_opportunity_ids else f"unknown_{review_item_id}"
        evidence_pack_id = linked_evidence_pack_ids[0] if linked_evidence_pack_ids else f"unknown_ep_{review_item_id}"

        inbox_source_urls = _safe_string_list(inbox_item.get("linked_source_urls", []))
        source_urls = _resolve_import_source_urls(
            review_item_id=review_item_id,
            inbox_source_urls=inbox_source_urls,
        )

        source_signal_ids = _dedupe_sorted(
            linked_opportunity_ids + linked_quality_gate_ids + linked_action_ids
        )

        if not source_urls:
            conversion_errors.append(
                f"review_item_id '{review_item_id}': no source URLs resolved from inbox "
                f"linked_source_urls. The source URL traceability contract requires at "
                f"least one real http/https URL per imported decision."
            )
            continue

        try:
            decision = create_founder_decision(
                opportunity_id=opportunity_id,
                evidence_pack_id=evidence_pack_id,
                decision=normalized_decision,
                reasons=reason_categories,
                notes=notes,
                confidence=0.9,
                linked_evidence_ids=linked_evidence_ids,
                linked_source_signal_ids=source_signal_ids,
                linked_source_urls=source_urls,
                decided_by="founder",
                decided_at=datetime.now(timezone.utc).isoformat(),
            )
        except (ValueError, TypeError) as exc:
            conversion_errors.append(
                f"Failed to create FounderDecisionV2 for review_item_id '{review_item_id}': {exc}"
            )
            continue

        new_decisions.append(decision)

    return new_decisions, conversion_errors, warnings


# ---------------------------------------------------------------------------
# Replace mode
# ---------------------------------------------------------------------------


def _import_replace_mode(
    *,
    run_dir: Path,
    run_id: str,
    new_decisions: list[FounderDecisionV2],
    existing_decisions: list[FounderDecisionV2],
    existing_decisions_raw: list[dict[str, Any]],
    existing_pl_records: list[dict[str, Any]],
    manifest_data: dict[str, Any],
    warnings: list[str],
    replace_rids: set[str],
    inbox_index: dict[str, Any],
    corrected_at: str,
) -> FounderDecisionImportResult:
    """Perform surgical decision replacement with derived artifact rebuild."""
    errors: list[str] = []

    # Identify which existing decisions to replace
    existing_by_rid, _missing = _map_existing_decisions_to_rid(
        existing_decisions=existing_decisions,
        inbox_index=inbox_index,
    )
    replaced_decisions: list[FounderDecisionV2] = []
    for rid in replace_rids:
        ed = existing_by_rid.get(rid)
        if ed:
            replaced_decisions.append(ed)

    old_decision_ids = sorted([d.decision_id for d in replaced_decisions])
    new_decision_ids = sorted([d.decision_id for d in new_decisions])

    # Build the new decision set: keep non-replaced + add new
    replaced_opp_ids = {d.opportunity_id for d in replaced_decisions}
    kept_decisions = [d for d in existing_decisions if d.opportunity_id not in replaced_opp_ids]
    all_decisions = sorted(
        kept_decisions + list(new_decisions),
        key=lambda d: d.decision_id,
    )

    # Archive replaced decisions
    archive_dir = run_dir / "replaced_decisions"
    archive_dir.mkdir(exist_ok=True)
    timestamp = corrected_at.replace(":", "-").replace(".", "-")
    archive_path = archive_dir / f"founder_decisions_v2_replaced_{timestamp}.json"
    try:
        archive_data = {
            "replaced_at": corrected_at,
            "replaced_decision_ids": old_decision_ids,
            "replaced_by": new_decision_ids,
            "decisions": [d.to_dict() for d in replaced_decisions],
        }
        archive_path.write_text(
            json.dumps(archive_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Failed to archive replaced decisions: {exc}"],
            validation_passed=False,
        )

    # Rebuild derived artifacts using decision_correction_rebuild
    pl_as_objects = _load_parking_lot_as_objects(existing_pl_records)
    rebuild_result = rebuild_founder_decision_derived_artifacts(
        decisions=all_decisions,
        existing_parking_lot_records=pl_as_objects,
        replaced_decision_ids={
            d.decision_id for d in replaced_decisions
        },
    )

    if rebuild_result.errors:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=rebuild_result.errors,
            validation_passed=False,
        )

    all_mappings = rebuild_result.feedback_mappings
    preference_profile = rebuild_result.preference_profile
    rebuilt_pl_records = rebuild_result.parking_lot_records

    # Compute artifact checksums before writing
    old_checksums = _compute_artifact_checksums(run_dir)

    # Write all artifacts (all-or-nothing via pre-build + individual writes)
    paths = canonical_artifact_paths()
    schemas = canonical_artifact_schema_versions()
    artifacts_updated: list[str] = []

    try:
        # 1. founder_decisions_v2.json
        decisions_data: dict[str, Any] = {
            "items": [founder_decision_to_dict(d) for d in all_decisions],
            "schema_version": schemas["founder_decisions_v2"],
            "empty": len(all_decisions) == 0,
            "imported": True,
            "note": "Founder decisions corrected via replace mode (v2.8 item 1.3).",
        }
        _write_json_atomic(run_dir, paths["founder_decisions_v2"], decisions_data)
        artifacts_updated.append("founder_decisions_v2")

        # 2. founder_feedback_mappings.json
        mappings_data: dict[str, Any] = {
            "items": [founder_feedback_mapping_to_dict(m) for m in all_mappings],
            "schema_version": schemas["founder_feedback_mappings"],
            "empty": len(all_mappings) == 0,
            "imported": True,
            "note": "Feedback mappings rebuilt after decision replacement.",
        }
        _write_json_atomic(run_dir, paths["founder_feedback_mappings"], mappings_data)
        artifacts_updated.append("founder_feedback_mappings")

        # 3. founder_preference_profile.json
        if preference_profile:
            profile_data = founder_preference_profile_to_dict(preference_profile)
            _write_json_atomic(run_dir, paths["founder_preference_profile"], profile_data)
            artifacts_updated.append("founder_preference_profile")

        # 4. parking_lot_records.json
        pl_dicts = json.loads(parking_lot_records_to_json(rebuilt_pl_records))
        pl_data: dict[str, Any] = {
            "items": pl_dicts,
            "schema_version": schemas["parking_lot_records"],
            "empty": len(rebuilt_pl_records) == 0,
            "import_updated": True,
            "cleanup_applied": True,
        }
        _write_json_atomic(run_dir, paths["parking_lot_records"], pl_data)
        artifacts_updated.append("parking_lot_records")

        # 5. Update manifest
        manifest_data["empty_states"] = {
            **(manifest_data.get("empty_states", {})),
            "founder_decisions_v2": len(all_decisions) == 0,
            "founder_feedback_mappings": len(all_mappings) == 0,
            "founder_preference_profile": preference_profile is None,
            "parking_lot_records": len(rebuilt_pl_records) == 0,
        }
        manifest_data["replaced_decision_ids"] = old_decision_ids
        manifest_data["replaced_at"] = corrected_at
        _write_json_atomic(run_dir, paths["manifest"], manifest_data)
        artifacts_updated.append("manifest")

    except (OSError, ValueError, TypeError) as exc:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Artifact write failed: {exc}"],
            validation_passed=False,
        )

    # 6. Write import history
    new_checksums = _compute_artifact_checksums(run_dir)
    _write_import_history(
        run_dir=run_dir,
        run_id=run_id,
        corrected_at=corrected_at,
        correction_mode="replace",
        replaced_review_item_ids=sorted(replace_rids),
        old_decision_ids=old_decision_ids,
        new_decision_ids=new_decision_ids,
        old_artifact_checksums=old_checksums,
        new_artifact_checksums=new_checksums,
        warnings=list(warnings) + rebuild_result.warnings,
        errors=[],
    )

    return FounderDecisionImportResult(
        run_id=run_id,
        imported_count=len(new_decisions),
        rejected_count=0,
        warnings=list(warnings) + rebuild_result.warnings,
        artifacts_updated=artifacts_updated,
        validation_passed=True,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )


# ---------------------------------------------------------------------------
# Amend-notes-only mode
# ---------------------------------------------------------------------------


def _import_amend_notes_only(
    *,
    run_dir: Path,
    run_id: str,
    inputs: FounderDecisionImportInput,
    inbox_index: dict[str, Any],
    existing_decisions: list[FounderDecisionV2],
    manifest_data: dict[str, Any],
    corrected_at: str,
) -> FounderDecisionImportResult:
    """Perform notes-only amendment of existing founder decisions."""
    errors: list[str] = []
    warnings: list[str] = []

    if len(inputs.decisions) == 0:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=["Amend mode requires at least one decision input"],
            validation_passed=False,
        )

    # Build lookup: review_item_id -> existing decision
    existing_by_rid, _missing = _map_existing_decisions_to_rid(
        existing_decisions=existing_decisions,
        inbox_index=inbox_index,
    )

    amended_decision_ids: list[str] = []
    amended_review_item_ids: list[str] = []

    # We'll build updated decisions in memory
    updated_decisions: dict[str, dict[str, Any]] = {}  # decision_id -> updated dict

    # Load current decisions file for in-place update
    paths = canonical_artifact_paths()
    decision_path = run_dir / paths["founder_decisions_v2"]
    try:
        current_data = json.loads(decision_path.read_text(encoding="utf-8"))
        current_items = current_data.get("items", []) if isinstance(current_data, dict) else []
    except (json.JSONDecodeError, ValueError) as exc:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Failed to read founder_decisions_v2.json: {exc}"],
            validation_passed=False,
        )

    # Build current items index by decision_id
    current_by_did: dict[str, dict[str, Any]] = {}
    for item in current_items:
        if isinstance(item, dict) and item.get("decision_id"):
            current_by_did[str(item["decision_id"])] = item

    for idx, amend_input in enumerate(inputs.decisions, start=1):
        review_item_id = str(amend_input.get("review_item_id", "")).strip()
        if not review_item_id:
            errors.append(f"Item {idx}: review_item_id is missing or empty")
            continue

        existing = existing_by_rid.get(review_item_id)
        if existing is None:
            errors.append(
                f"Item {idx}: no existing decision found for "
                f"review_item_id '{review_item_id}'"
            )
            continue

        # Check: decision value must NOT change in amend mode
        raw_decision = str(amend_input.get("decision", "")).strip()
        if raw_decision:
            new_decision_normalized = _DECISION_ALIASES.get(raw_decision.upper(), "")
            if new_decision_normalized and new_decision_normalized != existing.decision:
                errors.append(
                    f"Item {idx}: amend-notes-only mode cannot change decision value. "
                    f"Existing: '{existing.decision}', attempted: '{new_decision_normalized}'. "
                    f"Use --replace-review-items to change a decision value."
                )
                continue

        # Get new notes
        new_notes = str(amend_input.get("notes", "")).strip()
        if not new_notes:
            errors.append(
                f"Item {idx}: notes is required for amend-notes-only mode"
            )
            continue

        # Optional: reason_categories update
        new_reason_categories = _extract_reason_categories(
            amend_input.get("reason_categories", None)
        )

        # Validate reason categories against existing decision
        if new_reason_categories:
            allowed_reasons = set(REASONS_BY_DECISION.get(existing.decision, set()))
            invalid_reasons = sorted(set(new_reason_categories) - allowed_reasons)
            if invalid_reasons:
                errors.append(
                    f"Item {idx}: invalid reason categories for "
                    f"'{existing.decision}': {', '.join(invalid_reasons)}. "
                    f"Allowed: {', '.join(sorted(allowed_reasons))}"
                )
                continue

        # Update in place
        did = existing.decision_id
        if did in current_by_did:
            current_item = dict(current_by_did[did])
            current_item["notes"] = new_notes
            if new_reason_categories:
                # Update reasons list in the item
                current_item["reasons"] = [
                    {"category": rc, "note": ""} for rc in new_reason_categories
                ]
            updated_decisions[did] = current_item
            amended_decision_ids.append(did)
            amended_review_item_ids.append(review_item_id)

    if errors:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=errors,
            rejected_count=len(inputs.decisions),
            validation_passed=False,
        )

    if not amended_decision_ids:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=["No decisions were amended"],
            validation_passed=False,
        )

    # Archive old notes
    archive_dir = run_dir / "amended_decisions"
    archive_dir.mkdir(exist_ok=True)
    timestamp = corrected_at.replace(":", "-").replace(".", "-")

    old_items: list[dict[str, Any]] = []
    for did in amended_decision_ids:
        if did in current_by_did:
            old_items.append(dict(current_by_did[did]))
    if old_items:
        archive_path = archive_dir / f"founder_decisions_v2_amended_{timestamp}.json"
        try:
            archive_data = {
                "amended_at": corrected_at,
                "amended_decision_ids": amended_decision_ids,
                "items": old_items,
            }
            archive_path.write_text(
                json.dumps(archive_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except (OSError, ValueError) as exc:
            return FounderDecisionImportResult(
                run_id=run_id,
                errors=[f"Failed to archive amended decisions: {exc}"],
                validation_passed=False,
            )

    # Build final items: current items with amendments applied
    final_items: list[dict[str, Any]] = []
    for item in current_items:
        if isinstance(item, dict):
            did = str(item.get("decision_id", ""))
            if did in updated_decisions:
                final_items.append(updated_decisions[did])
            else:
                final_items.append(item)
        else:
            final_items.append(item)

    # Write updated decisions
    old_checksums = _compute_artifact_checksums(run_dir)
    schemas = canonical_artifact_schema_versions()
    artifacts_updated: list[str] = []

    try:
        decisions_data: dict[str, Any] = {
            "items": final_items,
            "schema_version": schemas["founder_decisions_v2"],
            "empty": len(final_items) == 0,
            "imported": True,
            "note": "Founder decisions amended via amend-notes-only mode (v2.8 item 1.3).",
        }
        _write_json_atomic(run_dir, paths["founder_decisions_v2"], decisions_data)
        artifacts_updated.append("founder_decisions_v2")

        # Update manifest
        manifest_data["amended_decision_ids"] = amended_decision_ids
        manifest_data["amended_at"] = corrected_at
        _write_json_atomic(run_dir, paths["manifest"], manifest_data)
        artifacts_updated.append("manifest")

    except (OSError, ValueError, TypeError) as exc:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=[f"Artifact write failed: {exc}"],
            validation_passed=False,
        )

    # Write import history
    new_checksums = _compute_artifact_checksums(run_dir)
    _write_import_history(
        run_dir=run_dir,
        run_id=run_id,
        corrected_at=corrected_at,
        correction_mode="amend",
        replaced_review_item_ids=amended_review_item_ids,
        old_decision_ids=amended_decision_ids,
        new_decision_ids=amended_decision_ids,
        old_artifact_checksums=old_checksums,
        new_artifact_checksums=new_checksums,
        warnings=warnings,
        errors=[],
    )

    return FounderDecisionImportResult(
        run_id=run_id,
        imported_count=len(amended_decision_ids),
        rejected_count=0,
        warnings=warnings,
        artifacts_updated=artifacts_updated,
        validation_passed=True,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------


def _write_import_artifacts(
    run_dir: Path,
    all_decisions: list[FounderDecisionV2],
    all_mappings: list[FounderFeedbackMapping],
    preference_profile: FounderPreferenceProfile,
    parking_lot_records: list[ParkingLotRecord],
) -> list[str]:
    """Write updated artifacts to the run directory. Returns list of updated artifact keys."""
    artifacts_updated: list[str] = []

    paths = canonical_artifact_paths()
    schemas = canonical_artifact_schema_versions()

    # 1. founder_decisions_v2.json
    decisions_data: dict[str, Any] = {
        "items": [founder_decision_to_dict(d) for d in all_decisions],
        "schema_version": schemas["founder_decisions_v2"],
        "empty": len(all_decisions) == 0,
        "imported": True,
        "note": "Founder decisions imported via founder decision import (v2.6 item 5.1).",
    }
    _write_json(run_dir, paths["founder_decisions_v2"], decisions_data)
    artifacts_updated.append("founder_decisions_v2")

    # 2. founder_feedback_mappings.json
    mappings_data: dict[str, Any] = {
        "items": [founder_feedback_mapping_to_dict(m) for m in all_mappings],
        "schema_version": schemas["founder_feedback_mappings"],
        "empty": len(all_mappings) == 0,
        "imported": True,
        "note": "Feedback mappings derived from imported founder decisions.",
    }
    _write_json(run_dir, paths["founder_feedback_mappings"], mappings_data)
    artifacts_updated.append("founder_feedback_mappings")

    # 3. founder_preference_profile.json
    profile_data = founder_preference_profile_to_dict(preference_profile)
    _write_json(run_dir, paths["founder_preference_profile"], profile_data)
    artifacts_updated.append("founder_preference_profile")

    # 4. parking_lot_records.json (merge with existing)
    existing_pl: list[ParkingLotRecord] = []
    pl_path = run_dir / paths["parking_lot_records"]
    if pl_path.is_file():
        try:
            pl_raw = json.loads(pl_path.read_text(encoding="utf-8"))
            pl_items = pl_raw.get("items", []) if isinstance(pl_raw, dict) else []
            for item in pl_items:
                if isinstance(item, dict):
                    existing_pl.append(ParkingLotRecord.from_dict(item))
        except (json.JSONDecodeError, ValueError):
            pass

    combined_pl_records = _merge_parking_lot_records(existing_pl, parking_lot_records)
    pl_data = json.loads(parking_lot_records_to_json(combined_pl_records))
    _write_json(run_dir, paths["parking_lot_records"], {
        "items": pl_data,
        "schema_version": schemas["parking_lot_records"],
        "empty": len(combined_pl_records) == 0,
        "import_updated": True,
    })
    artifacts_updated.append("parking_lot_records")

    # 5. Update manifest empty_states
    manifest_path = run_dir / paths["manifest"]
    if manifest_path.is_file():
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            empty_states = manifest_data.get("empty_states", {})
            if isinstance(empty_states, dict):
                empty_states["founder_decisions_v2"] = len(all_decisions) == 0
                empty_states["founder_feedback_mappings"] = len(all_mappings) == 0
                empty_states["founder_preference_profile"] = False
                if len(combined_pl_records) == 0:
                    empty_states["parking_lot_records"] = True
                else:
                    empty_states["parking_lot_records"] = False
            manifest_data["empty_states"] = empty_states
            _write_json(run_dir, paths["manifest"], manifest_data)
            artifacts_updated.append("manifest")
        except (json.JSONDecodeError, ValueError):
            pass

    return artifacts_updated


def _write_json(run_dir: Path, filename: str, data: Any) -> Path:
    path = run_dir / filename
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path


def _write_json_atomic(run_dir: Path, filename: str, data: Any) -> Path:
    """Write JSON data atomically via write-then-rename pattern.

    Writes to {filename}.tmp, validates parseability, then renames.
    On validation failure, deletes the .tmp file and raises ValueError.
    """
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

    # Rename .tmp -> final
    tmp_path.replace(path)
    return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _merge_decisions(
    existing: list[FounderDecisionV2],
    new: list[FounderDecisionV2],
) -> list[FounderDecisionV2]:
    """Merge new decisions into existing, replacing by opportunity_id."""
    by_opp_id: dict[str, FounderDecisionV2] = {}
    for d in existing:
        by_opp_id[d.opportunity_id] = d
    for d in new:
        by_opp_id[d.opportunity_id] = d
    return sorted(by_opp_id.values(), key=lambda d: d.decision_id)


def _merge_parking_lot_records(
    existing: list[ParkingLotRecord],
    new: list[ParkingLotRecord],
) -> list[ParkingLotRecord]:
    """Merge new parking lot records into existing, deduplicating by record_id."""
    by_id: dict[str, ParkingLotRecord] = {}
    for r in existing:
        by_id[r.record_id] = r
    for r in new:
        by_id[r.record_id] = r
    return sorted(by_id.values(), key=lambda r: r.record_id)


def _resolve_import_source_urls(
    *,
    review_item_id: str,
    inbox_source_urls: list[str],
) -> list[str]:
    """Resolve source URLs for a founder decision import from inbox data.

    Policy:
    - Accept only non-empty real http:// or https:// URLs from inbox.
    - Deduplicate deterministically.
    - Do NOT create urn:oos:* placeholder URNs.
    - If no real URLs are available, return empty list.
    - The caller decides whether empty source_urls is acceptable.

    Returns:
        Deduplicated, sorted list of real http/https source URLs.
    """
    if not inbox_source_urls:
        return []

    urls: list[str] = []
    seen: set[str] = set()
    for url in inbox_source_urls:
        url_str = url.strip() if isinstance(url, str) else ""
        if not url_str:
            continue
        if not is_real_source_url(url_str):
            if is_placeholder_source_url(url_str):
                continue
            continue
        if url_str not in seen:
            urls.append(url_str)
            seen.add(url_str)

    return sorted(urls)


def _safe_string_list(raw: Any) -> list[str]:
    """Normalize to a list of non-empty strings, skipping None."""
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    for item in raw:
        if item is None:
            continue
        s = str(item).strip()
        if s and s.lower() != "none":
            result.append(s)
    return sorted(dict.fromkeys(result))


def _safe_str_dict(raw: Any) -> dict[str, str]:
    """Normalize to a dict of str -> str."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for k, v in raw.items():
        result[str(k).strip()] = str(v).strip()
    return result


def _dedupe_sorted(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(v for v in values if v))


def _map_existing_decisions_to_rid(
    *,
    existing_decisions: list[FounderDecisionV2],
    inbox_index: dict[str, Any],
) -> tuple[dict[str, FounderDecisionV2], set[str]]:
    """Map review_item_ids to existing FounderDecisionV2 objects.

    Returns:
        (existing_by_rid, missing_rids) where existing_by_rid maps
        review_item_id -> FounderDecisionV2.
    """
    existing_by_rid: dict[str, FounderDecisionV2] = {}
    missing_rids: set[str] = set()

    # Build inbox lookup
    inbox_by_rid: dict[str, dict[str, Any]] = {}
    for item in inbox_index.get("review_items", []):
        if isinstance(item, dict):
            rid = str(item.get("review_item_id", ""))
            if rid:
                inbox_by_rid[rid] = item

    # For each existing decision, find matching review_item_id
    for ed in existing_decisions:
        found = False
        for rid, item in inbox_by_rid.items():
            linked_opp_ids = _safe_string_list(item.get("linked_opportunity_ids", []))
            if ed.opportunity_id in linked_opp_ids:
                existing_by_rid[rid] = ed
                found = True
                break
        if not found:
            missing_rids.add(ed.decision_id)

    return existing_by_rid, missing_rids


def _generate_correction_id(
    run_id: str,
    corrected_at: str,
    correction_mode: str,
    old_ids: list[str],
    new_ids: list[str],
) -> str:
    """Generate a deterministic correction ID."""
    key = "|".join([
        run_id,
        corrected_at,
        correction_mode,
        ",".join(sorted(old_ids)),
        ",".join(sorted(new_ids)),
    ])
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"correction_{digest}"


def _compute_artifact_checksums(run_dir: Path) -> dict[str, str]:
    """Compute SHA-256 checksums of key artifacts in the run directory.

    Returns dict of {artifact_key: sha256_hex}.
    """
    checksums: dict[str, str] = {}
    paths = canonical_artifact_paths()
    artifact_keys = [
        "founder_decisions_v2",
        "founder_feedback_mappings",
        "founder_preference_profile",
        "parking_lot_records",
        "manifest",
    ]
    for key in artifact_keys:
        artifact_path = run_dir / paths.get(key, f"{key}.json")
        if artifact_path.is_file():
            try:
                content = artifact_path.read_text(encoding="utf-8")
                checksums[key] = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            except (OSError, ValueError):
                pass
    return checksums


def _write_import_history(
    *,
    run_dir: Path,
    run_id: str,
    corrected_at: str,
    correction_mode: str,
    replaced_review_item_ids: list[str],
    old_decision_ids: list[str],
    new_decision_ids: list[str],
    old_artifact_checksums: dict[str, str],
    new_artifact_checksums: dict[str, str],
    warnings: list[str],
    errors: list[str],
) -> Path:
    """Write (or append to) the import_history.json for a run."""
    history_path = run_dir / "import_history.json"

    # Load existing history if present
    if history_path.is_file():
        try:
            existing_data = json.loads(history_path.read_text(encoding="utf-8"))
            log = ImportHistoryLog.from_dict(existing_data)
        except (json.JSONDecodeError, ValueError):
            log = ImportHistoryLog(run_id=run_id)
    else:
        log = ImportHistoryLog(run_id=run_id)

    correction_id = _generate_correction_id(
        run_id=run_id,
        corrected_at=corrected_at,
        correction_mode=correction_mode,
        old_ids=old_decision_ids,
        new_ids=new_decision_ids,
    )

    entry = CorrectionEntry(
        correction_id=correction_id,
        corrected_at=corrected_at,
        correction_mode=correction_mode,
        replaced_review_item_ids=sorted(replaced_review_item_ids),
        old_decision_ids=sorted(old_decision_ids),
        new_decision_ids=sorted(new_decision_ids),
        old_artifact_checksums=old_artifact_checksums,
        new_artifact_checksums=new_artifact_checksums,
        warnings=list(warnings),
        errors=list(errors),
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )
    log.entries.append(entry)

    history_path.write_text(
        json.dumps(log.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return history_path


def _load_parking_lot_as_objects(
    pl_records: list[dict[str, Any]],
) -> list[ParkingLotRecord]:
    """Convert dict-based parking lot records to ParkingLotRecord objects.

    Invalid records are silently skipped.
    """
    result: list[ParkingLotRecord] = []
    for item in pl_records:
        if isinstance(item, dict):
            try:
                result.append(ParkingLotRecord.from_dict(item))
            except (ValueError, TypeError):
                pass
    return result


# ---------------------------------------------------------------------------
# Public import history read API (v2.8 item 2.1)
# ---------------------------------------------------------------------------


def read_import_history(run_dir: Path) -> ImportHistoryLog | None:
    """Read import_history.json from a run directory.

    Returns ImportHistoryLog on success, None if the file is missing
    or unparseable.  Read-only — never modifies the file.
    """
    history_path = run_dir / "import_history.json"
    if not history_path.is_file():
        return None
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        return ImportHistoryLog.from_dict(data)
    except (json.JSONDecodeError, ValueError):
        return None


def build_import_history_summary(run_dir: Path) -> dict[str, Any]:
    """Build a summary dict describing the import history for a run.

    Used by status and report builders to surface correction state.

    Returns:
        dict with keys:
        - present: bool — whether import_history.json exists and is readable
        - entry_count: int — number of correction entries
        - latest_correction_mode: str — mode of latest entry ('' if none)
        - mode_counts: dict[str, int] — counts by correction_mode
        - replaced_decision_ids: list[str] — all replaced decision IDs
        - amended_decision_ids: list[str] — all amended decision IDs
    """
    history = read_import_history(run_dir)
    if history is None:
        return {
            "present": False,
            "entry_count": 0,
            "latest_correction_mode": "",
            "mode_counts": {},
            "replaced_decision_ids": [],
            "amended_decision_ids": [],
        }
    return {
        "present": True,
        "entry_count": history.entry_count(),
        "latest_correction_mode": history.latest_correction_mode(),
        "mode_counts": history.correction_modes_summary(),
        "replaced_decision_ids": history.all_replaced_decision_ids(),
        "amended_decision_ids": history.all_amended_decision_ids(),
    }
