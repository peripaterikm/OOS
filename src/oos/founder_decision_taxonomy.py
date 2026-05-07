from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any


FOUNDER_DECISION_V2_SCHEMA_VERSION = "founder_decision_v2.v1"
DEFAULT_DECIDED_AT = "manual_review_pending"

PROMOTE = "promote"
PARK = "park"
KILL = "kill"
REVISIT_LATER = "revisit_later"
NEEDS_MORE_EVIDENCE = "needs_more_evidence"

PROMOTE_REASONS = (
    "strong_pain",
    "clear_buyer",
    "strong_willingness_to_pay",
    "founder_expertise_fit",
    "good_wedge",
    "worth_interviews",
)

PARK_REASONS = (
    "weak_evidence",
    "unclear_buyer",
    "too_early",
    "needs_more_examples",
    "interesting_but_not_now",
    "weak_price_evidence",
)

KILL_REASONS = (
    "too_generic",
    "no_buyer",
    "no_willingness_to_pay",
    "disguised_consulting",
    "founder_bottleneck",
    "not_aligned",
    "already_tried",
    "repeated_killed_pattern",
    "vendor_promo_false_positive",
    "no_real_pain",
)

REVISIT_REASONS = (
    "waiting_for_more_signals",
    "revisit_after_new_price_signal",
    "revisit_after_source_diversity_improves",
    "revisit_after_founder_strategy_change",
)

NEEDS_MORE_EVIDENCE_REASONS = (
    "need_customer_voice",
    "need_price_evidence",
    "need_buyer_clarity",
    "need_workaround_evidence",
    "need_source_diversity",
    "need_non_vendor_source",
)

ALLOWED_DECISIONS = (PROMOTE, PARK, KILL, REVISIT_LATER, NEEDS_MORE_EVIDENCE)
REASONS_BY_DECISION = {
    PROMOTE: PROMOTE_REASONS,
    PARK: PARK_REASONS,
    KILL: KILL_REASONS,
    REVISIT_LATER: REVISIT_REASONS,
    NEEDS_MORE_EVIDENCE: NEEDS_MORE_EVIDENCE_REASONS,
}


@dataclass(frozen=True)
class FounderDecisionReason:
    category: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderDecisionReason:
        return cls(
            category=str(data.get("category", "")),
            note=str(data.get("note", "")),
        )


@dataclass(frozen=True)
class FounderDecisionTaxonomy:
    decisions: list[str]
    reasons_by_decision: dict[str, list[str]]
    schema_version: str = FOUNDER_DECISION_V2_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": list(self.decisions),
            "reasons_by_decision": {decision: list(reasons) for decision, reasons in self.reasons_by_decision.items()},
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class FounderDecisionValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    schema_version: str = FOUNDER_DECISION_V2_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FounderDecisionV2:
    decision_id: str
    opportunity_id: str
    evidence_pack_id: str
    decision: str
    reasons: list[FounderDecisionReason]
    notes: str
    confidence: float
    linked_evidence_ids: list[str]
    linked_source_signal_ids: list[str]
    linked_source_urls: list[str]
    decided_by: str
    decided_at: str = DEFAULT_DECIDED_AT
    schema_version: str = FOUNDER_DECISION_V2_SCHEMA_VERSION
    auto_promote: bool = False
    founder_decision_authority: str = "founder_decision_record_only"

    def validate(self) -> None:
        validate_founder_decision(self)

    def to_dict(self) -> dict[str, Any]:
        return founder_decision_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderDecisionV2:
        return founder_decision_from_dict(data)


def create_founder_decision(
    *,
    opportunity_id: str,
    evidence_pack_id: str,
    decision: str,
    reasons: list[str | FounderDecisionReason],
    notes: str = "",
    confidence: float = 0.5,
    linked_evidence_ids: list[str] | None = None,
    linked_source_signal_ids: list[str] | None = None,
    linked_source_urls: list[str] | None = None,
    decided_by: str = "founder",
    decided_at: str = DEFAULT_DECIDED_AT,
    decision_id: str | None = None,
) -> FounderDecisionV2:
    normalized_reasons = [
        reason if isinstance(reason, FounderDecisionReason) else FounderDecisionReason(category=str(reason))
        for reason in reasons
    ]
    candidate = FounderDecisionV2(
        decision_id=decision_id
        or make_founder_decision_id(
            opportunity_id=opportunity_id,
            evidence_pack_id=evidence_pack_id,
            decision=decision,
            reasons=[reason.category for reason in normalized_reasons],
        ),
        opportunity_id=opportunity_id,
        evidence_pack_id=evidence_pack_id,
        decision=decision,
        reasons=normalized_reasons,
        notes=notes,
        confidence=round(float(confidence), 3),
        linked_evidence_ids=_ordered_strings(linked_evidence_ids or []),
        linked_source_signal_ids=_ordered_strings(linked_source_signal_ids or []),
        linked_source_urls=_ordered_strings(linked_source_urls or []),
        decided_by=decided_by,
        decided_at=decided_at,
    )
    candidate.validate()
    return candidate


def make_founder_decision_id(
    *,
    opportunity_id: str,
    evidence_pack_id: str,
    decision: str,
    reasons: list[str],
) -> str:
    seed = "|".join(
        [
            str(opportunity_id).strip(),
            str(evidence_pack_id).strip(),
            str(decision).strip(),
            ",".join(_ordered_strings(reasons)),
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"founder_decision_v2_{digest}"


def founder_decision_to_dict(decision: FounderDecisionV2) -> dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "opportunity_id": decision.opportunity_id,
        "evidence_pack_id": decision.evidence_pack_id,
        "decision": decision.decision,
        "reasons": [reason.to_dict() for reason in decision.reasons],
        "notes": decision.notes,
        "confidence": float(decision.confidence),
        "linked_evidence_ids": list(decision.linked_evidence_ids),
        "linked_source_signal_ids": list(decision.linked_source_signal_ids),
        "linked_source_urls": list(decision.linked_source_urls),
        "decided_by": decision.decided_by,
        "decided_at": decision.decided_at,
        "schema_version": decision.schema_version,
        "auto_promote": decision.auto_promote,
        "founder_decision_authority": decision.founder_decision_authority,
    }


def founder_decision_from_dict(data: dict[str, Any]) -> FounderDecisionV2:
    decision = FounderDecisionV2(
        decision_id=str(data.get("decision_id", "")),
        opportunity_id=str(data.get("opportunity_id", "")),
        evidence_pack_id=str(data.get("evidence_pack_id", "")),
        decision=str(data.get("decision", "")),
        reasons=[FounderDecisionReason.from_dict(item) for item in data.get("reasons", [])],
        notes=str(data.get("notes", "")),
        confidence=float(data.get("confidence", 0.0)),
        linked_evidence_ids=[str(item) for item in data.get("linked_evidence_ids", [])],
        linked_source_signal_ids=[str(item) for item in data.get("linked_source_signal_ids", [])],
        linked_source_urls=[str(item) for item in data.get("linked_source_urls", [])],
        decided_by=str(data.get("decided_by", "")),
        decided_at=str(data.get("decided_at", DEFAULT_DECIDED_AT)),
        schema_version=str(data.get("schema_version", FOUNDER_DECISION_V2_SCHEMA_VERSION)),
        auto_promote=bool(data.get("auto_promote", False)),
        founder_decision_authority=str(data.get("founder_decision_authority", "founder_decision_record_only")),
    )
    decision.validate()
    return decision


def allowed_reasons_for_decision(decision: str) -> list[str]:
    if decision not in REASONS_BY_DECISION:
        raise ValueError(f"unknown founder decision: {decision}")
    return list(REASONS_BY_DECISION[decision])


def founder_decision_taxonomy() -> FounderDecisionTaxonomy:
    return FounderDecisionTaxonomy(
        decisions=list(ALLOWED_DECISIONS),
        reasons_by_decision={decision: list(reasons) for decision, reasons in REASONS_BY_DECISION.items()},
    )


def validate_founder_decision(decision: FounderDecisionV2) -> FounderDecisionValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    for field_name in (
        "decision_id",
        "opportunity_id",
        "evidence_pack_id",
        "decision",
        "decided_by",
        "decided_at",
        "schema_version",
        "founder_decision_authority",
    ):
        if not _is_non_empty(getattr(decision, field_name)):
            errors.append(f"{field_name} must be a non-empty string")
    if decision.schema_version != FOUNDER_DECISION_V2_SCHEMA_VERSION:
        errors.append("schema_version must be founder_decision_v2.v1")
    if decision.decision not in ALLOWED_DECISIONS:
        errors.append("decision must be one of the allowed v2 values")
    if not 0 <= float(decision.confidence) <= 1:
        errors.append("confidence must be between 0 and 1")
    if decision.auto_promote:
        errors.append("FounderDecisionV2 records decisions only and must not auto-promote")
    if decision.founder_decision_authority != "founder_decision_record_only":
        errors.append("founder_decision_authority must preserve record-only semantics")
    reason_categories = [reason.category for reason in decision.reasons]
    if not reason_categories:
        errors.append("at least one reason is required")
    if decision.decision in REASONS_BY_DECISION:
        allowed = set(REASONS_BY_DECISION[decision.decision])
        invalid = sorted(category for category in reason_categories if category not in allowed)
        if invalid:
            errors.append(f"invalid reasons for {decision.decision}: {', '.join(invalid)}")
    for reason in decision.reasons:
        if not _is_non_empty(reason.category):
            errors.append("reason.category must be non-empty")
        if reason.note is not None and not isinstance(reason.note, str):
            errors.append("reason.note must be a string")
    for field_name in ("linked_evidence_ids", "linked_source_signal_ids", "linked_source_urls"):
        values = getattr(decision, field_name)
        if not isinstance(values, list):
            errors.append(f"{field_name} must be a list")
        elif any(not isinstance(item, str) or not item.strip() for item in values):
            errors.append(f"{field_name} must contain non-empty strings")
    if not decision.linked_evidence_ids:
        warnings.append("linked_evidence_ids is empty")
    if not decision.linked_source_signal_ids:
        warnings.append("linked_source_signal_ids is empty")
    if not decision.linked_source_urls:
        warnings.append("linked_source_urls is empty")
    result = FounderDecisionValidationResult(
        is_valid=not errors,
        errors=_ordered_strings(errors),
        warnings=_ordered_strings(warnings),
    )
    if errors:
        raise ValueError("; ".join(result.errors))
    return result


def summarize_founder_decision(decision: FounderDecisionV2 | dict[str, Any]) -> str:
    item = founder_decision_from_dict(decision) if isinstance(decision, dict) else decision
    item.validate()
    reasons = ", ".join(reason.category for reason in sorted(item.reasons, key=lambda reason: reason.category))
    traceability = f"{len(item.linked_evidence_ids)} evidence / {len(item.linked_source_signal_ids)} signals / {len(item.linked_source_urls)} urls"
    return (
        f"{item.decision} `{item.opportunity_id}` from `{item.evidence_pack_id}` "
        f"because {reasons}; confidence={item.confidence:.3f}; traceability={traceability}."
    )


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _is_non_empty(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())
