from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    FounderDecisionV2,
)
from oos.founder_feedback_mapping import (
    BUYER_UNCLEAR,
    FOUNDER_FIT_NEGATIVE,
    FOUNDER_FIT_POSITIVE,
    GENERIC_FALSE_POSITIVE,
    NEEDS_MORE_EVIDENCE_IMPACT,
    NO_REAL_PAIN,
    PRICE_EVIDENCE_MISSING,
    PROMOTED_PATTERN,
    STRONG_PAIN_CONFIRMED,
    SUPPRESS_PATTERN,
    VENDOR_PROMO_FALSE_POSITIVE,
    WORKAROUND_CONFIRMED,
    FounderFeedbackMapping,
)


FOUNDER_PREFERENCE_PROFILE_SCHEMA_VERSION = "founder_preference_profile.v1"

ALLOWED_PAIN_TYPES = (
    "cash_collection",
    "invoice_workflow",
    "reconciliation",
    "reporting",
    "bookkeeping",
    "tax_compliance",
    "payroll",
    "expense_management",
    "financial_visibility",
    "vendor_management",
    "regulatory",
    "other",
)

ALLOWED_SCORING_HINT_KINDS = (
    "boost_preferred_pain",
    "suppress_rejected_pattern",
    "require_price_evidence",
    "require_buyer_clarity",
    "suppress_killed_pattern",
    "watch_vendor_promo_signal",
    "no_advisory_change",
)


@dataclass(frozen=True)
class FounderPreferenceScoringHint:
    kind: str
    adjustment: float
    reason: str
    linked_mapping_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FounderPreferencePackageWarning:
    warning_id: str
    category: str
    message: str
    linked_decision_ids: list[str] = field(default_factory=list)
    linked_mapping_ids: list[str] = field(default_factory=list)
    severity: str = "advisory"

    def to_dict(self) -> dict[str, Any]:
        return {
            "warning_id": self.warning_id,
            "category": self.category,
            "message": self.message,
            "linked_decision_ids": list(self.linked_decision_ids),
            "linked_mapping_ids": list(self.linked_mapping_ids),
            "severity": self.severity,
        }


@dataclass(frozen=True)
class FounderPreferenceProfile:
    profile_id: str
    preferred_pain_types: list[str]
    rejected_patterns: list[str]
    promoted_patterns: list[str]
    recurring_kill_reasons: list[str]
    areas_needing_more_evidence: list[str]
    source_decision_ids: list[str]
    source_feedback_mapping_ids: list[str]
    generated_at: str
    decision_count: int
    promote_count: int
    park_count: int
    kill_count: int
    revisit_count: int
    needs_more_evidence_count: int
    schema_version: str = FOUNDER_PREFERENCE_PROFILE_SCHEMA_VERSION
    ml_training_claimed: bool = False
    autonomous_decisions_made: bool = False

    def validate(self) -> None:
        validate_founder_preference_profile(self)

    def to_dict(self) -> dict[str, Any]:
        return founder_preference_profile_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderPreferenceProfile:
        return founder_preference_profile_from_dict(data)


def build_founder_preference_profile(
    decisions: list[FounderDecisionV2 | dict[str, Any]],
    feedback_mappings: list[FounderFeedbackMapping | dict[str, Any]] | None = None,
) -> FounderPreferenceProfile:
    from oos.founder_decision_taxonomy import founder_decision_from_dict
    from oos.founder_feedback_mapping import founder_feedback_mapping_from_dict

    normalized_decisions: list[FounderDecisionV2] = [
        founder_decision_from_dict(d) if isinstance(d, dict) else d
        for d in decisions
    ]
    for d in normalized_decisions:
        d.validate()

    mappings: list[FounderFeedbackMapping] = []
    if feedback_mappings:
        mappings = [
            founder_feedback_mapping_from_dict(m) if isinstance(m, dict) else m
            for m in feedback_mappings
        ]
        for m in mappings:
            m.validate()

    preferred_pain_types = _aggregate_preferred_pain_types(normalized_decisions)
    rejected_patterns = _aggregate_rejected_patterns(normalized_decisions, mappings)
    promoted_patterns = _aggregate_promoted_patterns(mappings)
    recurring_kill_reasons = _aggregate_recurring_kill_reasons(normalized_decisions)
    areas_needing_more_evidence = _aggregate_evidence_gaps(normalized_decisions, mappings)
    decision_ids = [d.decision_id for d in normalized_decisions]
    mapping_ids = [m.mapping_id for m in mappings]

    counts = _count_by_decision(normalized_decisions)

    profile = FounderPreferenceProfile(
        profile_id=make_founder_preference_profile_id(decision_ids, mapping_ids),
        preferred_pain_types=_ordered_strings(preferred_pain_types),
        rejected_patterns=_ordered_strings(rejected_patterns),
        promoted_patterns=_ordered_strings(promoted_patterns),
        recurring_kill_reasons=_ordered_strings(recurring_kill_reasons),
        areas_needing_more_evidence=_ordered_strings(areas_needing_more_evidence),
        source_decision_ids=_ordered_strings(decision_ids),
        source_feedback_mapping_ids=_ordered_strings(mapping_ids),
        generated_at=datetime.now(timezone.utc).isoformat(),
        decision_count=counts["total"],
        promote_count=counts.get(PROMOTE, 0),
        park_count=counts.get(PARK, 0),
        kill_count=counts.get(KILL, 0),
        revisit_count=counts.get(REVISIT_LATER, 0),
        needs_more_evidence_count=counts.get(NEEDS_MORE_EVIDENCE, 0),
    )
    profile.validate()
    return profile


def make_founder_preference_profile_id(
    decision_ids: list[str],
    mapping_ids: list[str],
) -> str:
    seed = "|".join(
        [
            ",".join(_ordered_strings(decision_ids)),
            ",".join(_ordered_strings(mapping_ids)),
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"founder_preference_profile_{digest}"


def profile_scoring_adjustment(
    profile: FounderPreferenceProfile,
    pain_type: str,
    *,
    matched_kill_reason: str | None = None,
    matched_rejected_pattern: str | None = None,
    has_price_evidence: bool = True,
    has_buyer_clarity: bool = True,
    source_tagged_vendor_promo: bool = False,
    linked_mapping_ids: list[str] | None = None,
) -> FounderPreferenceScoringHint:
    profile.validate()
    hints: list[tuple[str, float, str]] = []

    if pain_type and profile.preferred_pain_types and pain_type in profile.preferred_pain_types:
        hints.append(
            (
                "boost_preferred_pain",
                0.08,
                f"pain_type '{pain_type}' matches promoted founder preference",
            )
        )

    if matched_rejected_pattern and matched_rejected_pattern in profile.rejected_patterns:
        hints.append(
            (
                "suppress_rejected_pattern",
                -0.10,
                f"pattern '{matched_rejected_pattern}' matches recurring founder rejection",
            )
        )

    if matched_kill_reason and matched_kill_reason in profile.recurring_kill_reasons:
        hints.append(
            (
                "suppress_killed_pattern",
                -0.12,
                f"kill reason '{matched_kill_reason}' matches recurring kill pattern",
            )
        )

    if profile.areas_needing_more_evidence and "price_evidence_missing" in profile.areas_needing_more_evidence and not has_price_evidence:
        hints.append(
            (
                "require_price_evidence",
                -0.06,
                "founder profile requires price evidence; signal lacks explicit price hint",
            )
        )

    if profile.areas_needing_more_evidence and "buyer_unclear" in profile.areas_needing_more_evidence and not has_buyer_clarity:
        hints.append(
            (
                "require_buyer_clarity",
                -0.06,
                "founder profile requires buyer clarity; signal lacks buyer indication",
            )
        )

    if source_tagged_vendor_promo and profile.rejected_patterns and "vendor_promo_false_positive" in profile.rejected_patterns:
        hints.append(
            (
                "watch_vendor_promo_signal",
                -0.15,
                "founder profile rejects vendor-promo patterns; signal matches vendor promo",
            )
        )

    if not hints:
        return FounderPreferenceScoringHint(
            kind="no_advisory_change",
            adjustment=0.0,
            reason="no founder preference signal triggers matched",
            linked_mapping_ids=_ordered_strings(linked_mapping_ids or []),
        )

    best_hint = max(hints, key=lambda h: abs(h[1]))
    adjustment = round(sum(h[1] for h in hints), 3)
    adjustment = max(-0.20, min(0.10, adjustment))

    combined_reason = "; ".join(h[2] for h in hints)
    return FounderPreferenceScoringHint(
        kind=best_hint[0],
        adjustment=adjustment,
        reason=combined_reason,
        linked_mapping_ids=_ordered_strings(linked_mapping_ids or []),
    )


def profile_founder_package_warnings(
    profile: FounderPreferenceProfile,
) -> list[FounderPreferencePackageWarning]:
    profile.validate()
    warnings: list[FounderPreferencePackageWarning] = []

    if profile.kill_count >= 2 and profile.promote_count == 0 and profile.decision_count >= 2:
        warnings.append(
            FounderPreferencePackageWarning(
                warning_id=_make_warning_id("many_kills_no_promote"),
                category="portfolio_health",
                message=(
                    f"Founder profile shows {profile.kill_count} kills and 0 promotes "
                    f"across {profile.decision_count} decisions. "
                    "Review whether source/query quality filters too aggressively or "
                    "whether existing sources lack founder-relevant pain."
                ),
                linked_decision_ids=list(profile.source_decision_ids),
                linked_mapping_ids=list(profile.source_feedback_mapping_ids),
            )
        )

    if profile.promote_count == 0 and profile.decision_count >= 2:
        warnings.append(
            FounderPreferencePackageWarning(
                warning_id=_make_warning_id("no_promoted_opportunities"),
                category="opportunity_discovery",
                message=(
                    f"No promoted opportunities across {profile.decision_count} decisions. "
                    "Consider broadening query scope, adjusting source selection, or "
                    "reviewing whether opportunity criteria are too narrow."
                ),
                linked_decision_ids=list(profile.source_decision_ids),
                linked_mapping_ids=list(profile.source_feedback_mapping_ids),
            )
        )

    if profile.needs_more_evidence_count >= 2:
        gaps = profile.areas_needing_more_evidence[:4] if profile.areas_needing_more_evidence else ["unspecified"]
        warnings.append(
            FounderPreferencePackageWarning(
                warning_id=_make_warning_id("many_needs_evidence"),
                category="evidence_gap",
                message=(
                    f"{profile.needs_more_evidence_count} opportunities need more evidence: "
                    f"{', '.join(gaps)}. "
                    "Consider running customer-voice queries or collecting from "
                    "additional source types."
                ),
                linked_decision_ids=list(profile.source_decision_ids),
                linked_mapping_ids=list(profile.source_feedback_mapping_ids),
            )
        )

    if profile.recurring_kill_reasons:
        top_kill = profile.recurring_kill_reasons[:3]
        warnings.append(
            FounderPreferencePackageWarning(
                warning_id=_make_warning_id("recurring_kill_patterns"),
                category="kill_pattern_memory",
                message=(
                    f"Recurring kill reasons: {', '.join(top_kill)}. "
                    "Future signals matching these patterns will receive advisory "
                    "scoring suppression hints."
                ),
                linked_decision_ids=list(profile.source_decision_ids),
                linked_mapping_ids=list(profile.source_feedback_mapping_ids),
            )
        )

    if not profile.preferred_pain_types:
        warnings.append(
            FounderPreferencePackageWarning(
                warning_id=_make_warning_id("no_preferred_pain_types"),
                category="preference_gap",
                message=(
                    "No preferred pain types identified from founder decisions. "
                    "Profile will not boost any pain-domain scoring until "
                    "at least one promote decision is recorded."
                ),
                linked_decision_ids=list(profile.source_decision_ids),
                linked_mapping_ids=list(profile.source_feedback_mapping_ids),
            )
        )

    return warnings


def founder_preference_profile_to_dict(profile: FounderPreferenceProfile) -> dict[str, Any]:
    return {
        "profile_id": profile.profile_id,
        "preferred_pain_types": list(profile.preferred_pain_types),
        "rejected_patterns": list(profile.rejected_patterns),
        "promoted_patterns": list(profile.promoted_patterns),
        "recurring_kill_reasons": list(profile.recurring_kill_reasons),
        "areas_needing_more_evidence": list(profile.areas_needing_more_evidence),
        "source_decision_ids": list(profile.source_decision_ids),
        "source_feedback_mapping_ids": list(profile.source_feedback_mapping_ids),
        "generated_at": profile.generated_at,
        "decision_count": profile.decision_count,
        "promote_count": profile.promote_count,
        "park_count": profile.park_count,
        "kill_count": profile.kill_count,
        "revisit_count": profile.revisit_count,
        "needs_more_evidence_count": profile.needs_more_evidence_count,
        "schema_version": profile.schema_version,
        "ml_training_claimed": profile.ml_training_claimed,
        "autonomous_decisions_made": profile.autonomous_decisions_made,
    }


def founder_preference_profile_from_dict(data: dict[str, Any]) -> FounderPreferenceProfile:
    profile = FounderPreferenceProfile(
        profile_id=str(data.get("profile_id", "")),
        preferred_pain_types=_ordered_strings(data.get("preferred_pain_types", [])),
        rejected_patterns=_ordered_strings(data.get("rejected_patterns", [])),
        promoted_patterns=_ordered_strings(data.get("promoted_patterns", [])),
        recurring_kill_reasons=_ordered_strings(data.get("recurring_kill_reasons", [])),
        areas_needing_more_evidence=_ordered_strings(data.get("areas_needing_more_evidence", [])),
        source_decision_ids=_ordered_strings(data.get("source_decision_ids", [])),
        source_feedback_mapping_ids=_ordered_strings(data.get("source_feedback_mapping_ids", [])),
        generated_at=str(data.get("generated_at", "")),
        decision_count=int(data.get("decision_count", 0)),
        promote_count=int(data.get("promote_count", 0)),
        park_count=int(data.get("park_count", 0)),
        kill_count=int(data.get("kill_count", 0)),
        revisit_count=int(data.get("revisit_count", 0)),
        needs_more_evidence_count=int(data.get("needs_more_evidence_count", 0)),
        schema_version=str(data.get("schema_version", FOUNDER_PREFERENCE_PROFILE_SCHEMA_VERSION)),
        ml_training_claimed=bool(data.get("ml_training_claimed", False)),
        autonomous_decisions_made=bool(data.get("autonomous_decisions_made", False)),
    )
    profile.validate()
    return profile


def validate_founder_preference_profile(
    profile: FounderPreferenceProfile,
) -> list[str]:
    errors: list[str] = []

    for field_name in (
        "profile_id",
        "generated_at",
        "schema_version",
    ):
        value = getattr(profile, field_name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field_name} must be a non-empty string")

    if profile.schema_version != FOUNDER_PREFERENCE_PROFILE_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {FOUNDER_PREFERENCE_PROFILE_SCHEMA_VERSION}"
        )

    expected_total = (
        profile.promote_count
        + profile.park_count
        + profile.kill_count
        + profile.revisit_count
        + profile.needs_more_evidence_count
    )
    if expected_total != profile.decision_count:
        errors.append(
            f"decision_count ({profile.decision_count}) must equal sum of "
            f"per-decision counts ({expected_total})"
        )

    if profile.promote_count < 0:
        errors.append("promote_count must be non-negative")
    if profile.park_count < 0:
        errors.append("park_count must be non-negative")
    if profile.kill_count < 0:
        errors.append("kill_count must be non-negative")
    if profile.revisit_count < 0:
        errors.append("revisit_count must be non-negative")
    if profile.needs_more_evidence_count < 0:
        errors.append("needs_more_evidence_count must be non-negative")

    invalid_pain_types = sorted(
        set(profile.preferred_pain_types) - set(ALLOWED_PAIN_TYPES)
    )
    if invalid_pain_types:
        errors.append(
            f"preferred_pain_types contains unsupported values: "
            f"{', '.join(invalid_pain_types)}"
        )

    if profile.ml_training_claimed:
        errors.append("profile must not claim ML training; this is deterministic memory")

    if profile.autonomous_decisions_made:
        errors.append("profile must not make autonomous portfolio decisions")

    if not profile.source_decision_ids and profile.decision_count > 0:
        errors.append("source_decision_ids must not be empty when decisions exist")

    if errors:
        raise ValueError("; ".join(errors))
    return errors


def _aggregate_preferred_pain_types(
    decisions: list[FounderDecisionV2],
) -> list[str]:
    """Extract preferred pain types from PROMOTE decisions only.

    When no PROMOTE decisions exist, returns an empty list so that
    downstream scoring hints and warnings behave correctly.
    """
    pain_types: list[str] = []
    for d in decisions:
        if d.decision != PROMOTE:
            continue
        found = False
        for reason in d.reasons:
            category = reason.category.strip().lower()
            if category in {
                "strong_pain",
                "clear_buyer",
                "strong_willingness_to_pay",
                "founder_expertise_fit",
                "good_wedge",
                "worth_interviews",
            }:
                if d.notes:
                    for pain_type in ALLOWED_PAIN_TYPES:
                        if pain_type != "other" and (
                            pain_type in d.notes.lower()
                            or pain_type.replace("_", " ") in d.notes.lower()
                        ):
                            pain_types.append(pain_type)
                            found = True
        if not found:
            pain_types.append("other")
    return _ordered_strings(pain_types)


def _aggregate_rejected_patterns(
    decisions: list[FounderDecisionV2],
    mappings: list[FounderFeedbackMapping],
) -> list[str]:
    patterns: list[str] = []
    for m in mappings:
        if m.signal_impact in (SUPPRESS_PATTERN, "negative"):
            for tag in m.feedback_tags:
                if tag in {
                    GENERIC_FALSE_POSITIVE,
                    VENDOR_PROMO_FALSE_POSITIVE,
                    NO_REAL_PAIN,
                    FOUNDER_FIT_NEGATIVE,
                }:
                    patterns.append(tag)
    for d in decisions:
        if d.decision == KILL:
            for reason in d.reasons:
                category = reason.category.strip().lower()
                if category in {
                    "too_generic",
                    "vendor_promo_false_positive",
                    "no_real_pain",
                    "no_buyer",
                    "disguised_consulting",
                    "founder_bottleneck",
                    "not_aligned",
                }:
                    patterns.append(category)
    return _ordered_strings(patterns)


def _aggregate_promoted_patterns(
    mappings: list[FounderFeedbackMapping],
) -> list[str]:
    patterns: list[str] = []
    for m in mappings:
        if m.signal_impact == "positive":
            patterns.append(PROMOTED_PATTERN)
            for tag in m.feedback_tags:
                if tag in {
                    STRONG_PAIN_CONFIRMED,
                    WORKAROUND_CONFIRMED,
                    FOUNDER_FIT_POSITIVE,
                }:
                    patterns.append(tag)
    return _ordered_strings(patterns)


def _aggregate_recurring_kill_reasons(
    decisions: list[FounderDecisionV2],
) -> list[str]:
    frequency: dict[str, int] = {}
    for d in decisions:
        if d.decision != KILL:
            continue
        for reason in d.reasons:
            category = reason.category.strip().lower()
            if category:
                frequency[category] = frequency.get(category, 0) + 1
    return _ordered_strings(
        sorted(frequency, key=lambda k: (-frequency[k], k))
    )


def _aggregate_evidence_gaps(
    decisions: list[FounderDecisionV2],
    mappings: list[FounderFeedbackMapping],
) -> list[str]:
    gaps: list[str] = []
    for m in mappings:
        if m.signal_impact == NEEDS_MORE_EVIDENCE_IMPACT:
            if PRICE_EVIDENCE_MISSING in m.feedback_tags:
                gaps.append("price_evidence_missing")
            if BUYER_UNCLEAR in m.feedback_tags:
                gaps.append("buyer_unclear")
    for d in decisions:
        if d.decision in (PARK, NEEDS_MORE_EVIDENCE):
            for reason in d.reasons:
                category = reason.category.strip().lower()
                if category in {
                    "weak_evidence",
                    "unclear_buyer",
                    "weak_price_evidence",
                    "needs_more_examples",
                    "need_customer_voice",
                    "need_price_evidence",
                    "need_buyer_clarity",
                    "need_workaround_evidence",
                    "need_source_diversity",
                    "need_non_vendor_source",
                }:
                    gaps.append(category)
    return _ordered_strings(gaps)


def _count_by_decision(
    decisions: list[FounderDecisionV2],
) -> dict[str, int]:
    counts: dict[str, int] = {
        PROMOTE: 0,
        PARK: 0,
        KILL: 0,
        REVISIT_LATER: 0,
        NEEDS_MORE_EVIDENCE: 0,
    }
    for d in decisions:
        if d.decision in counts:
            counts[d.decision] += 1
    counts["total"] = sum(counts.values())
    return counts


def _make_warning_id(seed: str) -> str:
    return f"founder_preference_warning_{seed}"


def _ordered_strings(values: list[Any]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))
