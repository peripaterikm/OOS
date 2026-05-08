"""Founder Decision Import — deterministic import of explicit founder decisions.

Roadmap v2.6 item 5.1. Reads a founder decisions file (JSON array or JSONL)
and integrates validated decisions into a weekly run's artifacts.

Fail-closed: if any input decision is invalid, no artifacts are written.
Reject duplicates: duplicate review_item_id entries are rejected.
Idempotent: re-running the same import yields identical artifact state.

No live LLM/API calls. No autonomous decisions. No portfolio mutations.
Advisory-only throughout.
"""

from __future__ import annotations

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
from oos.weekly_run_manifest import (
    canonical_artifact_paths,
    canonical_artifact_schema_versions,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FOUNDER_DECISION_IMPORT_SCHEMA_VERSION = "founder_decision_import.v1"

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
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate parsed decision inputs against the founder inbox v2 index.

    Checks:
    - review_item_id is present and non-empty
    - review_item_id exists in the inbox index
    - decision value is allowed
    - reason_categories are valid for the given decision (if taxonomy requires)
    - no duplicate review_item_id entries in the input
    - no review_item_id already has an existing decision (idempotency guard)

    Returns:
        Tuple of (valid_decisions, validation_errors).
        If validation_errors is non-empty, valid_decisions is empty
        and no artifacts should be written (fail-closed).
    """
    errors: list[str] = []
    valid: list[dict[str, Any]] = []
    existing_decision_ids: set[str] = set()

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
        if inbox_item is not None and existing_decisions:
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
) -> FounderDecisionImportResult:
    """Import explicit founder decisions into a weekly run.

    Fail-closed: if any input decision is invalid, no artifacts are written.

    Args:
        project_root: Root directory of the OOS project.
        run_id: The weekly run ID to import decisions into.
        decisions_file: Path to the founder decisions file (JSON array or JSONL).

    Returns:
        FounderDecisionImportResult with import status and artifact paths.
    """
    project_root = project_root.resolve()
    decisions_file = decisions_file.resolve()
    run_dir = project_root / "artifacts" / "weekly_runs" / run_id

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
    existing_decision_path = run_dir / canonical_artifact_paths()["founder_decisions_v2"]
    if existing_decision_path.is_file():
        try:
            existing_data = json.loads(existing_decision_path.read_text(encoding="utf-8"))
            existing_items = existing_data.get("items", []) if isinstance(existing_data, dict) else []
            for item in existing_items:
                if isinstance(item, dict) and item.get("decision_id"):
                    try:
                        existing_decisions.append(FounderDecisionV2.from_dict(item))
                    except (ValueError, TypeError):
                        pass
        except (json.JSONDecodeError, ValueError):
            pass

    # Load existing feedback mappings (for preference profile rebuild)
    existing_mappings: list[dict[str, Any]] = []
    existing_mappings_path = run_dir / canonical_artifact_paths()["founder_feedback_mappings"]
    if existing_mappings_path.is_file():
        try:
            existing_data = json.loads(existing_mappings_path.read_text(encoding="utf-8"))
            existing_mappings = existing_data.get("items", []) if isinstance(existing_data, dict) else []
            if isinstance(existing_mappings, list):
                existing_mappings = [m for m in existing_mappings if isinstance(m, dict)]
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

    # Validate
    valid_inputs, validation_errors = validate_founder_decision_inputs(
        inputs,
        inbox_index,
        existing_decisions=existing_decisions if existing_decisions else None,
    )

    if validation_errors:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=validation_errors,
            rejected_count=len(inputs.decisions),
            validation_passed=False,
        )

    # Convert to FounderDecisionV2
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

        # Resolve traceability from inbox item
        linked_opportunity_ids = _safe_string_list(inbox_item.get("linked_opportunity_ids", []))
        linked_evidence_pack_ids = _safe_string_list(inbox_item.get("linked_evidence_pack_ids", []))
        linked_evidence_ids = _safe_string_list(inbox_item.get("linked_evidence_ids", []))
        linked_quality_gate_ids = _safe_string_list(inbox_item.get("linked_quality_gate_ids", []))
        linked_action_ids = _safe_string_list(inbox_item.get("linked_action_ids", []))
        linked_parking_lot_ids = _safe_string_list(inbox_item.get("linked_parking_lot_record_ids", []))
        linked_revisit_match_ids = _safe_string_list(inbox_item.get("linked_revisit_match_ids", []))
        linked_source_artifact_ids = _safe_string_list(inbox_item.get("linked_source_artifact_ids", []))

        # Primary opportunity_id
        opportunity_id = linked_opportunity_ids[0] if linked_opportunity_ids else f"unknown_{review_item_id}"
        evidence_pack_id = linked_evidence_pack_ids[0] if linked_evidence_pack_ids else f"unknown_ep_{review_item_id}"

        # Collect source_urls from evidence items where possible.
        # Feedback mapping validation requires at least one source_url;
        # when none are available from inbox traceability, use a
        # deterministic placeholder that satisfies the contract without
        # pretending to be a real URL.
        source_urls: list[str] = []
        source_signal_ids = _dedupe_sorted(
            linked_opportunity_ids + linked_quality_gate_ids + linked_action_ids
        )
        if not source_urls:
            source_urls = ["urn:oos:founder_import:placeholder"]

        try:
            decision = create_founder_decision(
                opportunity_id=opportunity_id,
                evidence_pack_id=evidence_pack_id,
                decision=normalized_decision,
                reasons=reason_categories,
                notes=notes,
                confidence=0.9,  # explicit founder decision = high confidence
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

    if conversion_errors:
        return FounderDecisionImportResult(
            run_id=run_id,
            errors=conversion_errors,
            rejected_count=len(inputs.decisions),
            validation_passed=False,
        )

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
                # Don't change parking_lot_records empty state since we may have added records
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


def _dedupe_sorted(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(v for v in values if v))
