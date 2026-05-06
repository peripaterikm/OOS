from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
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


FOUNDER_FEEDBACK_MAPPING_SCHEMA_VERSION = "founder_feedback_mapping.v1"

POSITIVE = "positive"
NEGATIVE = "negative"
NEUTRAL = "neutral"
NEEDS_MORE_EVIDENCE_IMPACT = "needs_more_evidence"
SUPPRESS_PATTERN = "suppress_pattern"
REVISIT_PATTERN = "revisit_pattern"

ALLOWED_SIGNAL_IMPACTS = (
    POSITIVE,
    NEGATIVE,
    NEUTRAL,
    NEEDS_MORE_EVIDENCE_IMPACT,
    SUPPRESS_PATTERN,
    REVISIT_PATTERN,
)

BOOST_SIMILAR_PATTERN = "boost_similar_pattern"
PARK_SIMILAR_UNTIL_MORE_EVIDENCE = "park_similar_until_more_evidence"
SUPPRESS_SIMILAR_PATTERN = "suppress_similar_pattern"
REQUIRE_BUYER_CLARITY = "require_buyer_clarity"
REQUIRE_PRICE_EVIDENCE = "require_price_evidence"
REVISIT_IF_NEW_SIGNALS = "revisit_if_new_signals"
KEEP_AS_CONTEXT = "keep_as_context"

ALLOWED_RECOMMENDED_FUTURE_HANDLING = (
    BOOST_SIMILAR_PATTERN,
    PARK_SIMILAR_UNTIL_MORE_EVIDENCE,
    SUPPRESS_SIMILAR_PATTERN,
    REQUIRE_BUYER_CLARITY,
    REQUIRE_PRICE_EVIDENCE,
    REVISIT_IF_NEW_SIGNALS,
    KEEP_AS_CONTEXT,
)

PROMOTED_PATTERN = "promoted_pattern"
PARKED_PATTERN = "parked_pattern"
KILLED_PATTERN = "killed_pattern"
BUYER_UNCLEAR = "buyer_unclear"
PRICE_EVIDENCE_MISSING = "price_evidence_missing"
STRONG_PAIN_CONFIRMED = "strong_pain_confirmed"
WORKAROUND_CONFIRMED = "workaround_confirmed"
VENDOR_PROMO_FALSE_POSITIVE = "vendor_promo_false_positive"
GENERIC_FALSE_POSITIVE = "generic_false_positive"
NO_REAL_PAIN = "no_real_pain"
FOUNDER_FIT_POSITIVE = "founder_fit_positive"
FOUNDER_FIT_NEGATIVE = "founder_fit_negative"
REVISIT_ON_NEW_EVIDENCE = "revisit_on_new_evidence"

ALLOWED_FEEDBACK_TAGS = (
    PROMOTED_PATTERN,
    PARKED_PATTERN,
    KILLED_PATTERN,
    BUYER_UNCLEAR,
    PRICE_EVIDENCE_MISSING,
    STRONG_PAIN_CONFIRMED,
    WORKAROUND_CONFIRMED,
    VENDOR_PROMO_FALSE_POSITIVE,
    GENERIC_FALSE_POSITIVE,
    NO_REAL_PAIN,
    FOUNDER_FIT_POSITIVE,
    FOUNDER_FIT_NEGATIVE,
    REVISIT_ON_NEW_EVIDENCE,
)


@dataclass(frozen=True)
class FounderFeedbackTarget:
    opportunity_id: str
    evidence_pack_id: str
    cluster_id: str
    evidence_ids: list[str]
    source_signal_ids: list[str]
    source_urls: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderFeedbackTarget:
        return cls(
            opportunity_id=str(data.get("opportunity_id", "")),
            evidence_pack_id=str(data.get("evidence_pack_id", "")),
            cluster_id=str(data.get("cluster_id", "unknown")),
            evidence_ids=_ordered_strings(data.get("evidence_ids", [])),
            source_signal_ids=_ordered_strings(data.get("source_signal_ids", [])),
            source_urls=_ordered_strings(data.get("source_urls", [])),
        )


@dataclass(frozen=True)
class FounderFeedbackSignalImpact:
    impact: str
    feedback_tags: list[str]
    recommended_future_handling: list[str]
    reason_categories: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderFeedbackSignalImpact:
        return cls(
            impact=str(data.get("impact", "")),
            feedback_tags=_ordered_strings(data.get("feedback_tags", [])),
            recommended_future_handling=_ordered_strings(data.get("recommended_future_handling", [])),
            reason_categories=_ordered_strings(data.get("reason_categories", [])),
        )


@dataclass(frozen=True)
class FounderFeedbackMapping:
    mapping_id: str
    decision_id: str
    opportunity_id: str
    evidence_pack_id: str
    cluster_id: str
    evidence_ids: list[str]
    source_signal_ids: list[str]
    source_urls: list[str]
    decision: str
    reasons: list[str]
    feedback_tags: list[str]
    signal_impact: str
    recommended_future_handling: list[str]
    target: FounderFeedbackTarget
    impact_detail: FounderFeedbackSignalImpact
    schema_version: str = FOUNDER_FEEDBACK_MAPPING_SCHEMA_VERSION
    scoring_mutation_applied: bool = False
    founder_decision_final: bool = True

    def validate(self) -> None:
        validate_founder_feedback_mapping(self)

    def to_dict(self) -> dict[str, Any]:
        return founder_feedback_mapping_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderFeedbackMapping:
        return founder_feedback_mapping_from_dict(data)


@dataclass(frozen=True)
class FounderFeedbackMappingResult:
    mapping: FounderFeedbackMapping
    is_valid: bool
    errors: list[str]
    summary: str
    schema_version: str = FOUNDER_FEEDBACK_MAPPING_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping": self.mapping.to_dict(),
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "summary": self.summary,
            "schema_version": self.schema_version,
        }


def map_founder_decision_to_feedback(
    decision: FounderDecisionV2 | dict[str, Any],
    *,
    cluster_id: str | None = None,
) -> FounderFeedbackMapping:
    item = founder_decision_from_dict(decision) if isinstance(decision, dict) else decision
    item.validate()
    reasons = _ordered_strings([reason.category for reason in item.reasons])
    impact = _derive_signal_impact(item.decision, reasons)
    target = FounderFeedbackTarget(
        opportunity_id=item.opportunity_id,
        evidence_pack_id=item.evidence_pack_id,
        cluster_id=str(cluster_id or "unknown"),
        evidence_ids=_ordered_strings(item.linked_evidence_ids),
        source_signal_ids=_ordered_strings(item.linked_source_signal_ids),
        source_urls=_ordered_strings(item.linked_source_urls),
    )
    mapping = FounderFeedbackMapping(
        mapping_id=make_founder_feedback_mapping_id(
            decision_id=item.decision_id,
            opportunity_id=item.opportunity_id,
            evidence_pack_id=item.evidence_pack_id,
            cluster_id=target.cluster_id,
        ),
        decision_id=item.decision_id,
        opportunity_id=item.opportunity_id,
        evidence_pack_id=item.evidence_pack_id,
        cluster_id=target.cluster_id,
        evidence_ids=list(target.evidence_ids),
        source_signal_ids=list(target.source_signal_ids),
        source_urls=list(target.source_urls),
        decision=item.decision,
        reasons=list(reasons),
        feedback_tags=list(impact.feedback_tags),
        signal_impact=impact.impact,
        recommended_future_handling=list(impact.recommended_future_handling),
        target=target,
        impact_detail=impact,
    )
    mapping.validate()
    return mapping


def make_founder_feedback_mapping_id(
    *,
    decision_id: str,
    opportunity_id: str,
    evidence_pack_id: str,
    cluster_id: str,
) -> str:
    seed = "|".join(
        [
            str(decision_id).strip(),
            str(opportunity_id).strip(),
            str(evidence_pack_id).strip(),
            str(cluster_id).strip(),
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"founder_feedback_mapping_{digest}"


def founder_feedback_mapping_to_dict(mapping: FounderFeedbackMapping) -> dict[str, Any]:
    return {
        "mapping_id": mapping.mapping_id,
        "decision_id": mapping.decision_id,
        "opportunity_id": mapping.opportunity_id,
        "evidence_pack_id": mapping.evidence_pack_id,
        "cluster_id": mapping.cluster_id,
        "evidence_ids": list(mapping.evidence_ids),
        "source_signal_ids": list(mapping.source_signal_ids),
        "source_urls": list(mapping.source_urls),
        "decision": mapping.decision,
        "reasons": list(mapping.reasons),
        "feedback_tags": list(mapping.feedback_tags),
        "signal_impact": mapping.signal_impact,
        "recommended_future_handling": list(mapping.recommended_future_handling),
        "target": mapping.target.to_dict(),
        "impact_detail": mapping.impact_detail.to_dict(),
        "schema_version": mapping.schema_version,
        "scoring_mutation_applied": mapping.scoring_mutation_applied,
        "founder_decision_final": mapping.founder_decision_final,
    }


def founder_feedback_mapping_from_dict(data: dict[str, Any]) -> FounderFeedbackMapping:
    target = FounderFeedbackTarget.from_dict(data.get("target", {}))
    impact_detail = FounderFeedbackSignalImpact.from_dict(data.get("impact_detail", {}))
    mapping = FounderFeedbackMapping(
        mapping_id=str(data.get("mapping_id", "")),
        decision_id=str(data.get("decision_id", "")),
        opportunity_id=str(data.get("opportunity_id", "")),
        evidence_pack_id=str(data.get("evidence_pack_id", "")),
        cluster_id=str(data.get("cluster_id", "unknown")),
        evidence_ids=_ordered_strings(data.get("evidence_ids", [])),
        source_signal_ids=_ordered_strings(data.get("source_signal_ids", [])),
        source_urls=_ordered_strings(data.get("source_urls", [])),
        decision=str(data.get("decision", "")),
        reasons=_ordered_strings(data.get("reasons", [])),
        feedback_tags=_ordered_strings(data.get("feedback_tags", [])),
        signal_impact=str(data.get("signal_impact", "")),
        recommended_future_handling=_ordered_strings(data.get("recommended_future_handling", [])),
        target=target,
        impact_detail=impact_detail,
        schema_version=str(data.get("schema_version", FOUNDER_FEEDBACK_MAPPING_SCHEMA_VERSION)),
        scoring_mutation_applied=bool(data.get("scoring_mutation_applied", False)),
        founder_decision_final=bool(data.get("founder_decision_final", True)),
    )
    mapping.validate()
    return mapping


def validate_founder_feedback_mapping(mapping: FounderFeedbackMapping) -> FounderFeedbackMappingResult:
    errors: list[str] = []
    for field_name in (
        "mapping_id",
        "decision_id",
        "opportunity_id",
        "evidence_pack_id",
        "cluster_id",
        "decision",
        "signal_impact",
        "schema_version",
    ):
        if not _is_non_empty(getattr(mapping, field_name)):
            errors.append(f"{field_name} must be a non-empty string")
    if mapping.schema_version != FOUNDER_FEEDBACK_MAPPING_SCHEMA_VERSION:
        errors.append("schema_version must be founder_feedback_mapping.v1")
    if mapping.signal_impact not in ALLOWED_SIGNAL_IMPACTS:
        errors.append("signal_impact must be one of the allowed feedback impacts")
    if not mapping.reasons:
        errors.append("reasons must not be empty")
    invalid_tags = sorted(set(mapping.feedback_tags) - set(ALLOWED_FEEDBACK_TAGS))
    if invalid_tags:
        errors.append(f"feedback_tags contains unsupported values: {', '.join(invalid_tags)}")
    invalid_handling = sorted(set(mapping.recommended_future_handling) - set(ALLOWED_RECOMMENDED_FUTURE_HANDLING))
    if invalid_handling:
        errors.append(f"recommended_future_handling contains unsupported values: {', '.join(invalid_handling)}")
    for field_name in ("evidence_ids", "source_signal_ids", "source_urls", "recommended_future_handling"):
        values = getattr(mapping, field_name)
        if not isinstance(values, list):
            errors.append(f"{field_name} must be a list")
        elif any(not isinstance(item, str) or not item.strip() for item in values):
            errors.append(f"{field_name} must contain non-empty strings")
    if not mapping.evidence_ids:
        errors.append("evidence_ids must preserve at least one evidence reference")
    if not mapping.source_signal_ids:
        errors.append("source_signal_ids must preserve at least one source signal reference")
    if not mapping.source_urls:
        errors.append("source_urls must preserve at least one source URL")
    if mapping.scoring_mutation_applied:
        errors.append("5.2 records feedback only and must not mutate scoring")
    if not mapping.founder_decision_final:
        errors.append("founder_decision_final must remain true")
    if mapping.target.opportunity_id != mapping.opportunity_id:
        errors.append("target.opportunity_id must match mapping opportunity_id")
    if mapping.target.evidence_pack_id != mapping.evidence_pack_id:
        errors.append("target.evidence_pack_id must match mapping evidence_pack_id")
    if mapping.target.cluster_id != mapping.cluster_id:
        errors.append("target.cluster_id must match mapping cluster_id")
    if mapping.target.evidence_ids != mapping.evidence_ids:
        errors.append("target.evidence_ids must match mapping evidence_ids")
    if mapping.target.source_signal_ids != mapping.source_signal_ids:
        errors.append("target.source_signal_ids must match mapping source_signal_ids")
    if mapping.target.source_urls != mapping.source_urls:
        errors.append("target.source_urls must match mapping source_urls")
    if mapping.impact_detail.impact != mapping.signal_impact:
        errors.append("impact_detail.impact must match signal_impact")
    if mapping.impact_detail.feedback_tags != mapping.feedback_tags:
        errors.append("impact_detail.feedback_tags must match feedback_tags")
    if mapping.impact_detail.recommended_future_handling != mapping.recommended_future_handling:
        errors.append("impact_detail.recommended_future_handling must match recommended_future_handling")
    result = FounderFeedbackMappingResult(
        mapping=mapping,
        is_valid=not errors,
        errors=_ordered_strings(errors),
        summary="" if errors else summarize_founder_feedback_mapping(mapping),
    )
    if errors:
        raise ValueError("; ".join(result.errors))
    return result


def summarize_founder_feedback_mapping(mapping: FounderFeedbackMapping | dict[str, Any]) -> str:
    item = founder_feedback_mapping_from_dict(mapping) if isinstance(mapping, dict) else mapping
    reason_text = ", ".join(item.reasons)
    tag_text = ", ".join(item.feedback_tags)
    handling_text = ", ".join(item.recommended_future_handling)
    return (
        f"{item.signal_impact} feedback for `{item.opportunity_id}` / `{item.evidence_pack_id}` "
        f"from decision `{item.decision_id}` ({item.decision}; reasons={reason_text}; "
        f"tags={tag_text}; handling={handling_text}; traceability="
        f"{len(item.evidence_ids)} evidence/{len(item.source_signal_ids)} signals/{len(item.source_urls)} urls)."
    )


def _derive_signal_impact(decision: str, reasons: list[str]) -> FounderFeedbackSignalImpact:
    tags: list[str] = []
    handling: list[str] = []
    impact = NEUTRAL
    if decision == PROMOTE:
        impact = POSITIVE
        tags.append(PROMOTED_PATTERN)
        handling.append(BOOST_SIMILAR_PATTERN)
        if "strong_pain" in reasons:
            tags.append(STRONG_PAIN_CONFIRMED)
        if "good_wedge" in reasons or "worth_interviews" in reasons:
            tags.append(WORKAROUND_CONFIRMED)
        if "founder_expertise_fit" in reasons:
            tags.append(FOUNDER_FIT_POSITIVE)
    elif decision == PARK:
        impact = NEEDS_MORE_EVIDENCE_IMPACT if _has_missing_evidence_reason(reasons) else NEUTRAL
        tags.append(PARKED_PATTERN)
        handling.append(PARK_SIMILAR_UNTIL_MORE_EVIDENCE)
        if "unclear_buyer" in reasons:
            tags.append(BUYER_UNCLEAR)
            handling.append(REQUIRE_BUYER_CLARITY)
        if "weak_price_evidence" in reasons:
            tags.append(PRICE_EVIDENCE_MISSING)
            handling.append(REQUIRE_PRICE_EVIDENCE)
    elif decision == KILL:
        impact = SUPPRESS_PATTERN if _has_suppress_reason(reasons) else NEGATIVE
        tags.append(KILLED_PATTERN)
        handling.append(SUPPRESS_SIMILAR_PATTERN)
        if "too_generic" in reasons:
            tags.append(GENERIC_FALSE_POSITIVE)
        if "vendor_promo_false_positive" in reasons:
            tags.append(VENDOR_PROMO_FALSE_POSITIVE)
        if "no_real_pain" in reasons:
            tags.append(NO_REAL_PAIN)
        if "no_buyer" in reasons:
            tags.append(BUYER_UNCLEAR)
            handling.append(REQUIRE_BUYER_CLARITY)
        if "not_aligned" in reasons or "founder_bottleneck" in reasons:
            tags.append(FOUNDER_FIT_NEGATIVE)
    elif decision == REVISIT_LATER:
        impact = REVISIT_PATTERN
        tags.append(REVISIT_ON_NEW_EVIDENCE)
        handling.append(REVISIT_IF_NEW_SIGNALS)
    elif decision == NEEDS_MORE_EVIDENCE:
        impact = NEEDS_MORE_EVIDENCE_IMPACT
        tags.append(PARKED_PATTERN)
        handling.append(PARK_SIMILAR_UNTIL_MORE_EVIDENCE)
        if "need_buyer_clarity" in reasons:
            tags.append(BUYER_UNCLEAR)
            handling.append(REQUIRE_BUYER_CLARITY)
        if "need_price_evidence" in reasons:
            tags.append(PRICE_EVIDENCE_MISSING)
            handling.append(REQUIRE_PRICE_EVIDENCE)
        if "need_customer_voice" in reasons or "need_workaround_evidence" in reasons:
            handling.append(KEEP_AS_CONTEXT)
    return FounderFeedbackSignalImpact(
        impact=impact,
        feedback_tags=_ordered_strings(tags),
        recommended_future_handling=_ordered_strings(handling),
        reason_categories=_ordered_strings(reasons),
    )


def _has_missing_evidence_reason(reasons: list[str]) -> bool:
    return any(reason in {"weak_evidence", "unclear_buyer", "needs_more_examples", "weak_price_evidence"} for reason in reasons)


def _has_suppress_reason(reasons: list[str]) -> bool:
    return any(reason in {"too_generic", "no_buyer", "vendor_promo_false_positive", "no_real_pain"} for reason in reasons)


def _ordered_strings(values: list[Any]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _is_non_empty(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())
