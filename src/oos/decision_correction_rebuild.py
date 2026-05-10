"""Decision Correction Rebuild — deterministic parking lot orphan cleanup
and derived artifact rebuild primitives.

Roadmap v2.8 item 1.2. Provides the internal primitives that item 1.3 can
use when safe replace/amend is enabled.

This module is **advisory / primitive only**. It does NOT:
- expose CLI flags,
- enable replace/amend behavior,
- change default import behavior,
- write to real artifacts/,
- call live APIs or LLMs.

What it does:
- Identify orphaned parking lot records (records whose source_decision_id
  no longer exists in the active founder decisions set).
- Produce cleanup reports (no file deletion, no mutation of unrelated records).
- Rebuild derived artifacts (feedback mappings, preference profile, parking lot
  records) from active founder decisions.
- Validate rebuild inputs for correctness and source URL traceability.

Source-decision reference policy:
  A ParkingLotRecord.source_decision_id references a FounderDecisionV2.decision_id.
  An orphan is any record whose source_decision_id does not appear in the
  active FounderDecisionV2 set. This is the deterministic policy — no guessing.

Deterministic rebuild order (from contract Section 8.1):
  1. Write founder_decisions_v2.json (primary — handled by caller)
  2. Rebuild founder_feedback_mappings.json (derived from decisions)
  3. Rebuild founder_preference_profile.json (derived from decisions + mappings)
  4. Cleanup and rebuild parking_lot_records.json
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    FounderDecisionV2,
    founder_decision_from_dict,
)
from oos.founder_feedback_mapping import (
    FounderFeedbackMapping,
    founder_feedback_mapping_from_dict,
    map_founder_decision_to_feedback,
)
from oos.founder_preference_profile import (
    FounderPreferenceProfile,
    build_founder_preference_profile,
)
from oos.parking_lot import (
    ParkingLotRecord,
    build_parking_lot_records,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DECISION_CORRECTION_REBUILD_SCHEMA_VERSION = "decision_correction_rebuild.v1"

# Placeholder URN pattern matching (avoiding circular import)
_PLACEHOLDER_URN_RE = re.compile(r"^urn:oos:", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass
class ParkingLotCleanupResult:
    """Result of parking lot orphan identification and cleanup.

    advisory_only=True: this result does NOT delete files or mutate state.
    It identifies which records are orphaned so the caller (item 1.3) can
    decide when and how to write cleaned records.
    """

    schema_version: str = DECISION_CORRECTION_REBUILD_SCHEMA_VERSION
    active_record_count_before: int = 0
    active_record_count_after: int = 0
    orphaned_record_count: int = 0
    retained_record_ids: list[str] = field(default_factory=list)
    orphaned_record_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    validation_passed: bool = False
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "active_record_count_before": self.active_record_count_before,
            "active_record_count_after": self.active_record_count_after,
            "orphaned_record_count": self.orphaned_record_count,
            "retained_record_ids": list(self.retained_record_ids),
            "orphaned_record_ids": list(self.orphaned_record_ids),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "validation_passed": self.validation_passed,
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
        }


@dataclass
class DerivedArtifactRebuildPlan:
    """Plan describing what derived artifacts will be rebuilt.

    This is a planning artifact — it describes what *would* be done without
    actually writing anything. Item 1.3 uses this to confirm the rebuild
    plan before executing writes.
    """

    schema_version: str = DECISION_CORRECTION_REBUILD_SCHEMA_VERSION
    active_decision_count: int = 0
    expected_feedback_mapping_count: int = 0
    expected_preference_profile_present: bool = False
    expected_parking_lot_record_count: int = 0
    parking_lot_orphans_to_remove: int = 0
    parking_lot_new_records_to_add: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    validation_passed: bool = False
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "active_decision_count": self.active_decision_count,
            "expected_feedback_mapping_count": self.expected_feedback_mapping_count,
            "expected_preference_profile_present": self.expected_preference_profile_present,
            "expected_parking_lot_record_count": self.expected_parking_lot_record_count,
            "parking_lot_orphans_to_remove": self.parking_lot_orphans_to_remove,
            "parking_lot_new_records_to_add": self.parking_lot_new_records_to_add,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "validation_passed": self.validation_passed,
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
        }


@dataclass
class DerivedArtifactRebuildResult:
    """Result of a derived artifact rebuild operation.

    This contains the rebuilt data AND the cleanup result. The caller
    (item 1.3) is responsible for writing these to disk.

    advisory_only=True: no files are written by this module.
    """

    schema_version: str = DECISION_CORRECTION_REBUILD_SCHEMA_VERSION
    active_founder_decision_count: int = 0
    feedback_mapping_count: int = 0
    preference_profile_present: bool = False
    parking_lot_record_count: int = 0
    orphaned_parking_lot_record_count: int = 0

    # Rebuilt data (not written to disk by this module)
    feedback_mappings: list[FounderFeedbackMapping] = field(default_factory=list)
    preference_profile: FounderPreferenceProfile | None = None
    parking_lot_records: list[ParkingLotRecord] = field(default_factory=list)
    cleanup_result: ParkingLotCleanupResult | None = None
    rebuild_plan: DerivedArtifactRebuildPlan | None = None

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    validation_passed: bool = False
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "active_founder_decision_count": self.active_founder_decision_count,
            "feedback_mapping_count": self.feedback_mapping_count,
            "preference_profile_present": self.preference_profile_present,
            "parking_lot_record_count": self.parking_lot_record_count,
            "orphaned_parking_lot_record_count": self.orphaned_parking_lot_record_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "validation_passed": self.validation_passed,
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
        }
        if self.cleanup_result:
            result["cleanup_result"] = self.cleanup_result.to_dict()
        if self.rebuild_plan:
            result["rebuild_plan"] = self.rebuild_plan.to_dict()
        return result


# ---------------------------------------------------------------------------
# Source URL validation helpers
# ---------------------------------------------------------------------------


def _is_real_source_url(url: str) -> bool:
    """Return True if url starts with http:// or https://."""
    if not isinstance(url, str):
        return False
    stripped = url.strip()
    return stripped.startswith("http://") or stripped.startswith("https://")


def _is_placeholder_urn(url: str) -> bool:
    """Return True if url matches the urn:oos:* placeholder pattern."""
    if not isinstance(url, str):
        return False
    return bool(_PLACEHOLDER_URN_RE.match(url.strip()))


def _validate_source_urls(
    source_urls: list[str],
    context_label: str = "",
) -> tuple[list[str], list[str]]:
    """Validate source URLs for traceability contract compliance.

    Returns (errors, warnings).

    Requirements:
    - Must contain at least one real http/https URL.
    - Must NOT contain any urn:oos:* placeholder URNs.
    - Fail-closed: missing URLs are an error, not a warning.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not source_urls:
        errors.append(
            f"{context_label}: no source URLs found. "
            f"At least one real http/https URL is required per the source URL "
            f"traceability contract."
        )
        return errors, warnings

    real_urls = [u for u in source_urls if _is_real_source_url(u)]
    placeholder_urls = [u for u in source_urls if _is_placeholder_urn(u)]

    if placeholder_urls:
        errors.append(
            f"{context_label}: source URLs contain placeholder URNs: "
            f"{', '.join(placeholder_urls[:5])}. "
            f"urn:oos:* placeholders are banned by the source URL traceability contract."
        )

    if not real_urls:
        errors.append(
            f"{context_label}: no real http/https source URLs found. "
            f"All source URLs must be real URLs, not placeholder URNs."
        )

    return errors, warnings


# ---------------------------------------------------------------------------
# Orphan identification
# ---------------------------------------------------------------------------


def identify_orphaned_parking_lot_records(
    parking_lot_records: list[ParkingLotRecord | dict[str, Any]],
    active_decision_ids: set[str],
) -> tuple[list[ParkingLotRecord], list[ParkingLotRecord]]:
    """Identify orphaned parking lot records.

    A parking lot record is orphaned when its source_decision_id does not
    appear in active_decision_ids.

    Source-decision reference policy:
      ParkingLotRecord.source_decision_id references a
      FounderDecisionV2.decision_id. If the decision no longer exists in the
      active set (e.g., it was replaced), the parking record is orphaned and
      must be excluded from the active parking lot.

    Args:
        parking_lot_records: Current parking lot records (can be mixed dict/object).
        active_decision_ids: Set of decision_id values from active FounderDecisionV2 items.

    Returns:
        (active_records, orphaned_records) — deterministic, sorted by record_id.
        No files are deleted.
    """
    normalized: list[ParkingLotRecord] = []
    for r in parking_lot_records:
        try:
            if isinstance(r, dict):
                rec = ParkingLotRecord.from_dict(r)
            else:
                rec = r
            # Skip records that fail validation
            errors = rec.validate()
            if errors:
                continue
            normalized.append(rec)
        except (ValueError, TypeError, AttributeError):
            continue

    active: list[ParkingLotRecord] = []
    orphaned: list[ParkingLotRecord] = []

    for rec in normalized:
        source_id = rec.source_decision_id.strip()
        if source_id and source_id in active_decision_ids:
            active.append(rec)
        else:
            orphaned.append(rec)

    # Deterministic ordering
    active.sort(key=lambda r: r.record_id)
    orphaned.sort(key=lambda r: r.record_id)

    return active, orphaned


def cleanup_orphaned_parking_lot_records(
    parking_lot_records: list[ParkingLotRecord | dict[str, Any]],
    active_decision_ids: set[str],
) -> tuple[list[ParkingLotRecord], ParkingLotCleanupResult]:
    """Clean orphaned parking lot records without deleting files.

    Returns the active (retained) records and a cleanup report describing
    what was identified. Does NOT write to disk or delete files.

    Args:
        parking_lot_records: Current parking lot records.
        active_decision_ids: Set of decision_id values from active FounderDecisionV2 items.

    Returns:
        (retained_records, cleanup_result)
    """
    active_records, orphaned_records = identify_orphaned_parking_lot_records(
        parking_lot_records=parking_lot_records,
        active_decision_ids=active_decision_ids,
    )

    warnings: list[str] = []
    errors: list[str] = []

    active_before = len(parking_lot_records)
    active_after = len(active_records)
    orphaned_count = len(orphaned_records)

    if orphaned_count > 0:
        warnings.append(
            f"Detected {orphaned_count} orphaned parking lot record(s). "
            f"These records reference source_decision_id values that no longer "
            f"exist in the active founder decisions set. "
            f"Orphaned record IDs: {', '.join(r.record_id for r in orphaned_records)}."
        )

    if active_before == 0:
        warnings.append(
            "No parking lot records provided for cleanup — "
            "this may indicate no PARK/REVISIT_LATER decisions exist."
        )

    # Validate retained records
    for rec in active_records:
        validation_errors = rec.validate()
        if validation_errors:
            errors.append(
                f"Retained record '{rec.record_id}' failed validation: "
                f"{'; '.join(validation_errors)}"
            )

    validation_passed = len(errors) == 0

    result = ParkingLotCleanupResult(
        schema_version=DECISION_CORRECTION_REBUILD_SCHEMA_VERSION,
        active_record_count_before=active_before,
        active_record_count_after=active_after,
        orphaned_record_count=orphaned_count,
        retained_record_ids=[r.record_id for r in active_records],
        orphaned_record_ids=[r.record_id for r in orphaned_records],
        warnings=warnings,
        errors=errors,
        validation_passed=validation_passed,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )

    return active_records, result


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def validate_rebuild_inputs(
    decisions: list[FounderDecisionV2 | dict[str, Any]],
    existing_parking_lot_records: list[ParkingLotRecord | dict[str, Any]] | None = None,
) -> tuple[list[FounderDecisionV2], list[ParkingLotRecord], list[str], list[str]]:
    """Validate all inputs before a rebuild operation.

    Checks:
    - Every decision is a valid FounderDecisionV2.
    - Every decision has real http/https source URLs (no urn:oos:* placeholders).
    - Every decision's decision value is one of the allowed values.
    - Parking lot records are valid (if provided).
    - No portfolio state mutation indicators.

    Returns:
        (normalized_decisions, normalized_parking_lot_records, errors, warnings).

    If errors is non-empty, no rebuild should proceed (fail-closed).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Normalize and validate decisions
    normalized_decisions: list[FounderDecisionV2] = []
    for i, d in enumerate(decisions):
        try:
            decision = founder_decision_from_dict(d) if isinstance(d, dict) else d
            decision.validate()
        except (ValueError, TypeError) as exc:
            errors.append(f"Decision [{i}] is invalid: {exc}")
            continue

        # Source URL traceability check
        url_errors, url_warnings = _validate_source_urls(
            source_urls=list(decision.linked_source_urls),
            context_label=f"Decision '{decision.decision_id}'",
        )
        errors.extend(url_errors)
        warnings.extend(url_warnings)

        # Check for forbidden placeholder URNs in linked_source_urls
        for url in decision.linked_source_urls:
            if _is_placeholder_urn(url):
                errors.append(
                    f"Decision '{decision.decision_id}': linked_source_urls contains "
                    f"placeholder URN '{url}'. Real http/https URLs are required."
                )
                break

        # Advisory-only check
        if decision.auto_promote:
            errors.append(
                f"Decision '{decision.decision_id}': auto_promote must be False "
                f"(advisory-only)."
            )
        if decision.founder_decision_authority != "founder_decision_record_only":
            errors.append(
                f"Decision '{decision.decision_id}': founder_decision_authority "
                f"must be 'founder_decision_record_only' (advisory-only)."
            )

        normalized_decisions.append(decision)

    # Normalize and validate parking lot records
    normalized_pl_records: list[ParkingLotRecord] = []
    if existing_parking_lot_records:
        for i, r in enumerate(existing_parking_lot_records):
            try:
                rec = ParkingLotRecord.from_dict(r) if isinstance(r, dict) else r
                validation_errors = rec.validate()
                if validation_errors:
                    errors.append(
                        f"Parking lot record [{i}] '{rec.record_id}' "
                        f"failed validation: {'; '.join(validation_errors)}"
                    )
                    continue
                normalized_pl_records.append(rec)
            except (ValueError, TypeError) as exc:
                errors.append(f"Parking lot record [{i}] is invalid: {exc}")
                continue

    return normalized_decisions, normalized_pl_records, errors, warnings


# ---------------------------------------------------------------------------
# Rebuild plan
# ---------------------------------------------------------------------------


def plan_derived_artifact_rebuild(
    decisions: list[FounderDecisionV2],
    existing_parking_lot_records: list[ParkingLotRecord] | None = None,
    replaced_decision_ids: set[str] | None = None,
) -> DerivedArtifactRebuildPlan:
    """Plan a derived artifact rebuild without executing any writes.

    Produces a DerivedArtifactRebuildPlan describing:
    - How many feedback mappings will be created.
    - Whether a preference profile will be created.
    - How many parking lot records will exist after cleanup + rebuild.
    - How many parking lot records are orphaned.

    Args:
        decisions: Active founder decisions after replacement.
        existing_parking_lot_records: Current parking lot records (pre-cleanup).
        replaced_decision_ids: Set of replaced decision_id values
            (used to identify which parking lot records to orphan).

    Returns:
        DerivedArtifactRebuildPlan.
    """
    warnings: list[str] = []
    errors: list[str] = []

    if not decisions:
        warnings.append(
            "No active founder decisions — derived artifacts will be empty."
        )

    # Count decisions by type
    park_decision_count = sum(
        1 for d in decisions if d.decision in (PARK, REVISIT_LATER)
    )

    # Identify orphans
    active_ids = {d.decision_id for d in decisions}
    existing_pl = existing_parking_lot_records or []

    orphaned_ids: set[str] = set()
    if replaced_decision_ids:
        orphaned_ids = replaced_decision_ids
    else:
        # Without explicit replaced IDs, determine orphans by checking
        # which parking lot records reference non-existent decision IDs
        active_pl, orphaned_pl = identify_orphaned_parking_lot_records(
            parking_lot_records=existing_pl,
            active_decision_ids=active_ids,
        )
        orphaned_ids = {r.source_decision_id for r in orphaned_pl}
        existing_pl = active_pl

    # Build new parking lot records from PARK/REVISIT_LATER decisions
    new_pl_records = build_parking_lot_records(decisions=decisions)

    # Merge: existing (non-orphaned) + new, deduplicated by record_id
    pl_by_id: dict[str, ParkingLotRecord] = {}
    for r in existing_pl:
        # Skip records whose source_decision_id is in orphaned_ids
        if r.source_decision_id in orphaned_ids:
            continue
        pl_by_id[r.record_id] = r
    for r in new_pl_records:
        pl_by_id[r.record_id] = r

    combined_pl = sorted(pl_by_id.values(), key=lambda r: r.record_id)

    orphan_count = sum(
        1 for r in existing_parking_lot_records or []
        if r.source_decision_id in orphaned_ids
    )

    validation_passed = len(errors) == 0

    plan = DerivedArtifactRebuildPlan(
        schema_version=DECISION_CORRECTION_REBUILD_SCHEMA_VERSION,
        active_decision_count=len(decisions),
        expected_feedback_mapping_count=len(decisions),
        expected_preference_profile_present=len(decisions) > 0,
        expected_parking_lot_record_count=len(combined_pl),
        parking_lot_orphans_to_remove=orphan_count,
        parking_lot_new_records_to_add=park_decision_count,
        warnings=warnings,
        errors=errors,
        validation_passed=validation_passed,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )

    return plan


# ---------------------------------------------------------------------------
# Rebuild execution
# ---------------------------------------------------------------------------


def rebuild_founder_decision_derived_artifacts(
    decisions: list[FounderDecisionV2 | dict[str, Any]],
    existing_parking_lot_records: list[ParkingLotRecord | dict[str, Any]] | None = None,
    replaced_decision_ids: set[str] | None = None,
) -> DerivedArtifactRebuildResult:
    """Rebuild derived artifacts from active founder decisions.

    This produces the rebuilt data that item 1.3 can write to disk.
    Does NOT write files.

    Derivation order (from contract Section 8.1):
    1. Normalize all decisions.
    2. Build feedback mappings from all decisions.
    3. Build preference profile from decisions + feedback mappings.
    4. Cleanup orphaned parking lot records.
    5. Build new parking lot records from PARK/REVISIT_LATER decisions.

    Args:
        decisions: Active founder decisions (post-replace).
        existing_parking_lot_records: Pre-cleanup parking lot records.
        replaced_decision_ids: Set of replaced decision_id values.

    Returns:
        DerivedArtifactRebuildResult with rebuilt data and cleanup report.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # Validate inputs
    validated_decisions, validated_pl_records, val_errors, val_warnings = validate_rebuild_inputs(
        decisions=decisions,
        existing_parking_lot_records=existing_parking_lot_records,
    )
    errors.extend(val_errors)
    warnings.extend(val_warnings)

    if errors:
        # Fail-closed: return no data, only errors
        return DerivedArtifactRebuildResult(
            schema_version=DECISION_CORRECTION_REBUILD_SCHEMA_VERSION,
            active_founder_decision_count=0,
            feedback_mapping_count=0,
            preference_profile_present=False,
            parking_lot_record_count=0,
            orphaned_parking_lot_record_count=0,
            warnings=warnings,
            errors=errors,
            validation_passed=False,
            advisory_only=True,
            no_live_api=True,
            no_live_llm=True,
        )

    # Build feedback mappings
    all_mappings: list[FounderFeedbackMapping] = []
    for d in validated_decisions:
        try:
            mapping = map_founder_decision_to_feedback(d)
            all_mappings.append(mapping)
        except (ValueError, TypeError) as exc:
            warnings.append(
                f"Feedback mapping skipped for '{d.decision_id}': {exc}"
            )

    # Build preference profile (only if there are decisions)
    preference_profile: FounderPreferenceProfile | None = None
    if validated_decisions:
        try:
            preference_profile = build_founder_preference_profile(
                decisions=validated_decisions,
                feedback_mappings=all_mappings,
            )
        except (ValueError, TypeError) as exc:
            errors.append(f"Failed to build preference profile: {exc}")
            return DerivedArtifactRebuildResult(
                schema_version=DECISION_CORRECTION_REBUILD_SCHEMA_VERSION,
                active_founder_decision_count=len(validated_decisions),
                feedback_mapping_count=len(all_mappings),
                preference_profile_present=False,
                parking_lot_record_count=0,
                orphaned_parking_lot_record_count=0,
                feedback_mappings=all_mappings,
                warnings=warnings,
                errors=errors,
                validation_passed=False,
                advisory_only=True,
                no_live_api=True,
                no_live_llm=True,
            )

    # Cleanup orphaned parking lot records
    active_decision_ids = {d.decision_id for d in validated_decisions}
    retained_pl, cleanup_result = cleanup_orphaned_parking_lot_records(
        parking_lot_records=validated_pl_records,
        active_decision_ids=active_decision_ids,
    )
    warnings.extend(cleanup_result.warnings)
    errors.extend(cleanup_result.errors)

    if cleanup_result.orphaned_record_count > 0:
        warnings.append(
            f"Orphaned {cleanup_result.orphaned_record_count} parking lot record(s): "
            f"{', '.join(cleanup_result.orphaned_record_ids)}. "
            f"These records have been excluded from the active parking lot."
        )

    # Build new parking lot records from PARK/REVISIT_LATER decisions
    new_pl_records = build_parking_lot_records(decisions=validated_decisions)

    # Merge retained + new, deduplicating by record_id
    pl_by_id: dict[str, ParkingLotRecord] = {}
    for r in retained_pl:
        pl_by_id[r.record_id] = r
    for r in new_pl_records:
        pl_by_id[r.record_id] = r
    combined_pl = sorted(pl_by_id.values(), key=lambda r: r.record_id)

    # Build rebuild plan
    rebuild_plan = plan_derived_artifact_rebuild(
        decisions=validated_decisions,
        existing_parking_lot_records=validated_pl_records,
        replaced_decision_ids=replaced_decision_ids,
    )

    # Source URL traceability: verify all feedback mappings carry real URLs
    for m in all_mappings:
        url_errors, url_warnings = _validate_source_urls(
            source_urls=list(m.source_urls),
            context_label=f"Feedback mapping '{m.mapping_id}'",
        )
        errors.extend(url_errors)
        warnings.extend(url_warnings)

    # Verify preference profile has no autonomous decisions or ML claims
    if preference_profile:
        if preference_profile.autonomous_decisions_made:
            errors.append(
                "Preference profile must not make autonomous portfolio decisions."
            )
        if preference_profile.ml_training_claimed:
            errors.append(
                "Preference profile must not claim ML training."
            )

    validation_passed = len(errors) == 0

    result = DerivedArtifactRebuildResult(
        schema_version=DECISION_CORRECTION_REBUILD_SCHEMA_VERSION,
        active_founder_decision_count=len(validated_decisions),
        feedback_mapping_count=len(all_mappings),
        preference_profile_present=preference_profile is not None,
        parking_lot_record_count=len(combined_pl),
        orphaned_parking_lot_record_count=cleanup_result.orphaned_record_count,
        feedback_mappings=all_mappings,
        preference_profile=preference_profile,
        parking_lot_records=combined_pl,
        cleanup_result=cleanup_result,
        rebuild_plan=rebuild_plan,
        warnings=warnings,
        errors=errors,
        validation_passed=validation_passed,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))
