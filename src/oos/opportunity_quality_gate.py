from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any

from .evidence_pack import EvidencePack, evidence_pack_from_dict
from .opportunity_sketch import UNKNOWN, OpportunityCandidate, opportunity_sketch_from_dict


OPPORTUNITY_QUALITY_GATE_SCHEMA_VERSION = "opportunity_quality_gate.v1"
FOUNDER_DECISION_AUTHORITY_NOTE = "Founder decision remains final"

PASS = "pass"
PARK = "park"
REJECT = "reject"

FOUNDER_REVIEW = "founder_review"
COLLECT_MORE_EVIDENCE = "collect_more_evidence"
CLARIFY_BUYER = "clarify_buyer"
CLARIFY_WORKAROUND = "clarify_workaround"
SUPPRESS_AS_FALSE_POSITIVE = "suppress_as_false_positive"
REJECT_AS_NOISE = "reject_as_noise"

ALLOWED_GATE_DECISIONS = {PASS, PARK, REJECT}
ALLOWED_NEXT_ACTIONS = {
    FOUNDER_REVIEW,
    COLLECT_MORE_EVIDENCE,
    CLARIFY_BUYER,
    CLARIFY_WORKAROUND,
    SUPPRESS_AS_FALSE_POSITIVE,
    REJECT_AS_NOISE,
}

FATAL_RISK_MARKERS = (
    "vendor",
    "vendor_promo",
    "seo",
    "generic_accounting_copy",
    "generic accounting",
    "source_quality_issue",
    "false_positive",
    "product_submission",
    "reject_as_noise",
)

INSUFFICIENT_RISK_MARKERS = (
    "insufficient",
    "missing_source_url",
    "missing evidence",
    "duplicate",
    "needs_more_evidence",
)

STRONG_PAIN_MARKERS = (
    "unpaid invoice",
    "invoice follow",
    "cash collection",
    "payment follow",
    "balance sheet",
    "month-end",
    "month end",
    "reporting",
    "sticky notes",
    "spreadsheet",
)


@dataclass(frozen=True)
class OpportunityGateReason:
    code: str
    message: str
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpportunityGateReason:
        return cls(
            code=str(data.get("code", "")),
            message=str(data.get("message", "")),
            severity=str(data.get("severity", "medium")),
        )


@dataclass(frozen=True)
class OpportunityGateResult:
    gate_result_id: str
    opportunity_id: str
    evidence_pack_id: str
    decision: str
    confidence: float
    reasons: list[OpportunityGateReason]
    blocking_issues: list[str]
    missing_evidence: list[str]
    recommended_next_action: str
    evidence_ids: list[str]
    source_signal_ids: list[str]
    source_urls: list[str]
    founder_override_status: str = "not_applied"
    founder_decision_authority_note: str = FOUNDER_DECISION_AUTHORITY_NOTE
    auto_promote: bool = False
    founder_decision_required: bool = True
    schema_version: str = OPPORTUNITY_QUALITY_GATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_result_id": self.gate_result_id,
            "opportunity_id": self.opportunity_id,
            "evidence_pack_id": self.evidence_pack_id,
            "decision": self.decision,
            "confidence": self.confidence,
            "reasons": [reason.to_dict() for reason in self.reasons],
            "blocking_issues": list(self.blocking_issues),
            "missing_evidence": list(self.missing_evidence),
            "recommended_next_action": self.recommended_next_action,
            "evidence_ids": list(self.evidence_ids),
            "source_signal_ids": list(self.source_signal_ids),
            "source_urls": list(self.source_urls),
            "founder_override_status": self.founder_override_status,
            "founder_decision_authority_note": self.founder_decision_authority_note,
            "auto_promote": self.auto_promote,
            "founder_decision_required": self.founder_decision_required,
            "schema_version": self.schema_version,
        }

    def validate(self) -> None:
        validate_opportunity_gate_result(self)


@dataclass(frozen=True)
class OpportunityBatchGateDecision:
    opportunity_id: str
    status: str
    confidence: float
    reasons: list[str]
    linked_signal_ids: list[str]
    founder_override_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OpportunityBatchGateResult:
    decisions: list[OpportunityBatchGateDecision]
    schema_version: str = OPPORTUNITY_QUALITY_GATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": [decision.to_dict() for decision in self.decisions],
            "schema_version": self.schema_version,
        }


def evaluate_opportunity_quality(
    opportunity: OpportunityCandidate | dict[str, Any],
    evidence_pack: EvidencePack | dict[str, Any] | None = None,
) -> OpportunityGateResult:
    candidate = opportunity_sketch_from_dict(opportunity) if isinstance(opportunity, dict) else opportunity
    pack = evidence_pack_from_dict(evidence_pack) if isinstance(evidence_pack, dict) else evidence_pack
    if pack is not None:
        pack.validate()
        if candidate.evidence_pack_id and candidate.evidence_pack_id != pack.evidence_pack_id:
            raise ValueError("opportunity and evidence_pack must reference the same evidence_pack_id")

    evidence_ids = _ordered_strings(candidate.evidence_ids)
    source_signal_ids = _ordered_strings(candidate.source_signal_ids)
    source_urls = _ordered_strings(candidate.source_urls)
    risk_notes = _risk_notes(candidate, pack)
    unsupported = _ordered_strings(candidate.unsupported_assumptions)
    missing_evidence = _missing_evidence(candidate, pack)
    reasons: list[OpportunityGateReason] = []
    blocking_issues: list[str] = []

    _add_traceability_reasons(reasons, blocking_issues, missing_evidence, evidence_ids, source_urls)
    _add_problem_reasons(reasons, blocking_issues, candidate)
    _add_risk_reasons(reasons, blocking_issues, risk_notes)
    _add_unsupported_reasons(reasons, unsupported)
    _add_support_reasons(reasons, candidate, pack)

    confidence = _gate_confidence(candidate, pack, reasons, blocking_issues, missing_evidence)
    decision = _decision(candidate, pack, confidence, reasons, blocking_issues, missing_evidence, unsupported)
    recommended_next_action = _recommended_next_action(decision, missing_evidence, reasons)
    result = OpportunityGateResult(
        gate_result_id=make_gate_result_id(candidate.opportunity_id or candidate.evidence_pack_id),
        opportunity_id=candidate.opportunity_id,
        evidence_pack_id=candidate.evidence_pack_id,
        decision=decision,
        confidence=confidence,
        reasons=sorted(reasons, key=lambda reason: (reason.severity, reason.code, reason.message)),
        blocking_issues=_ordered_strings(blocking_issues),
        missing_evidence=_ordered_strings(missing_evidence),
        recommended_next_action=recommended_next_action,
        evidence_ids=evidence_ids,
        source_signal_ids=source_signal_ids,
        source_urls=source_urls,
    )
    result.validate()
    return result


def evaluate_opportunity_batch(opportunities: list[Any]) -> OpportunityBatchGateResult:
    decisions = [_evaluate_legacy_opportunity_card(opportunity) for opportunity in opportunities]
    return OpportunityBatchGateResult(
        decisions=sorted(decisions, key=lambda decision: (decision.opportunity_id, decision.status))
    )


def make_gate_result_id(opportunity_id: str) -> str:
    value = str(opportunity_id).strip()
    if not value:
        value = "unknown_opportunity"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"opportunity_gate_{digest}"


def _evaluate_legacy_opportunity_card(opportunity: Any) -> OpportunityBatchGateDecision:
    opportunity_id = str(_get_value(opportunity, "opportunity_id", "unknown_opportunity"))
    linked_signal_ids = _ordered_strings(list(_get_value(opportunity, "linked_signal_ids", []) or []))
    confidence = float(_get_value(opportunity, "confidence", 0.0) or 0.0)
    evidence_missing = bool(_get_value(opportunity, "evidence_missing", False))
    risks = " ".join(str(item) for item in (_get_value(opportunity, "risks", []) or [])).lower()
    assumptions = _get_value(opportunity, "assumptions", []) or []
    reasons: list[str] = []
    status = PASS
    if evidence_missing:
        status = PARK
        reasons.append("evidence_missing")
    if confidence < 0.35:
        status = REJECT
        reasons.append("very_low_confidence")
    elif confidence < 0.65 and status == PASS:
        status = PARK
        reasons.append("confidence_needs_review")
    if assumptions:
        reasons.append("unsupported_assumptions_require_founder_review")
        if status == PASS and confidence < 0.8:
            status = PARK
    if any(marker in risks for marker in FATAL_RISK_MARKERS):
        status = REJECT
        reasons.append("vendor_or_generic_risk")
    if not linked_signal_ids:
        status = REJECT
        reasons.append("missing_linked_signal_ids")
    if not reasons:
        reasons.append("traceable_candidate_ready_for_founder_review")
    return OpportunityBatchGateDecision(
        opportunity_id=opportunity_id,
        status=status,
        confidence=round(max(0.0, min(1.0, confidence)), 3),
        reasons=_ordered_strings(reasons),
        linked_signal_ids=linked_signal_ids,
        founder_override_status=None,
    )


def validate_opportunity_gate_result(result: OpportunityGateResult) -> None:
    for field_name in (
        "gate_result_id",
        "opportunity_id",
        "evidence_pack_id",
        "decision",
        "recommended_next_action",
        "founder_override_status",
        "founder_decision_authority_note",
    ):
        _require_non_empty(getattr(result, field_name), f"OpportunityGateResult.{field_name}")
    if result.founder_decision_authority_note != FOUNDER_DECISION_AUTHORITY_NOTE:
        raise ValueError("Founder decision authority note must be preserved")
    if result.schema_version != OPPORTUNITY_QUALITY_GATE_SCHEMA_VERSION:
        raise ValueError("OpportunityGateResult.schema_version must be opportunity_quality_gate.v1")
    if result.decision not in ALLOWED_GATE_DECISIONS:
        raise ValueError("OpportunityGateResult.decision must be pass, park, or reject")
    if result.recommended_next_action not in ALLOWED_NEXT_ACTIONS:
        raise ValueError("OpportunityGateResult.recommended_next_action is not allowed")
    if result.auto_promote:
        raise ValueError("Opportunity quality gate must never auto-promote")
    if not result.founder_decision_required:
        raise ValueError("Founder decision authority must be preserved")
    if not 0 <= float(result.confidence) <= 1:
        raise ValueError("OpportunityGateResult.confidence must be between 0 and 1")
    for field_name in ("blocking_issues", "missing_evidence", "evidence_ids", "source_signal_ids", "source_urls"):
        if not isinstance(getattr(result, field_name), list):
            raise ValueError(f"OpportunityGateResult.{field_name} must be a list")
        _require_string_list(getattr(result, field_name), f"OpportunityGateResult.{field_name}")
    if not isinstance(result.reasons, list):
        raise ValueError("OpportunityGateResult.reasons must be a list")
    for reason in result.reasons:
        _require_non_empty(reason.code, "OpportunityGateReason.code")
        _require_non_empty(reason.message, "OpportunityGateReason.message")
        _require_non_empty(reason.severity, "OpportunityGateReason.severity")


def _decision(
    candidate: OpportunityCandidate,
    pack: EvidencePack | None,
    confidence: float,
    reasons: list[OpportunityGateReason],
    blocking_issues: list[str],
    missing_evidence: list[str],
    unsupported: list[str],
) -> str:
    if blocking_issues:
        return REJECT
    fatal_reasons = [reason for reason in reasons if reason.severity == "fatal"]
    if fatal_reasons or confidence < 0.2:
        return REJECT
    if missing_evidence:
        return PARK
    if confidence < 0.55 or len(unsupported) > 2:
        return PARK
    if _unknown(candidate.possible_buyer) or _unknown(candidate.product_wedge):
        return PARK
    if pack is not None and pack.source_diversity < 1:
        return PARK
    return PASS


def _recommended_next_action(
    decision: str,
    missing_evidence: list[str],
    reasons: list[OpportunityGateReason],
) -> str:
    reason_codes = {reason.code for reason in reasons}
    if decision == REJECT:
        if any(code in reason_codes for code in ("vendor_or_generic_risk", "generic_problem")):
            return SUPPRESS_AS_FALSE_POSITIVE
        return REJECT_AS_NOISE
    if "buyer_unknown" in reason_codes or "possible_buyer" in missing_evidence:
        return CLARIFY_BUYER
    if "workaround_unknown" in reason_codes or "current_workaround" in missing_evidence:
        return CLARIFY_WORKAROUND
    if decision == PARK:
        return COLLECT_MORE_EVIDENCE
    return FOUNDER_REVIEW


def _gate_confidence(
    candidate: OpportunityCandidate,
    pack: EvidencePack | None,
    reasons: list[OpportunityGateReason],
    blocking_issues: list[str],
    missing_evidence: list[str],
) -> float:
    confidence = max(0.0, min(1.0, float(candidate.confidence)))
    if pack is not None and pack.confidence_values:
        pack_confidence = sum(float(value) for value in pack.confidence_values) / len(pack.confidence_values)
        confidence = (confidence + pack_confidence) / 2
    confidence -= 0.08 * len(missing_evidence)
    confidence -= 0.12 * len(blocking_issues)
    confidence -= 0.08 * sum(1 for reason in reasons if reason.severity == "high")
    confidence -= 0.18 * sum(1 for reason in reasons if reason.severity == "fatal")
    confidence += 0.05 * sum(1 for reason in reasons if reason.severity == "positive")
    return round(max(0.0, min(0.95, confidence)), 3)


def _add_traceability_reasons(
    reasons: list[OpportunityGateReason],
    blocking_issues: list[str],
    missing_evidence: list[str],
    evidence_ids: list[str],
    source_urls: list[str],
) -> None:
    if not evidence_ids:
        blocking_issues.append("missing_evidence_ids")
        missing_evidence.append("evidence_ids")
        reasons.append(OpportunityGateReason("missing_evidence_ids", "No evidence IDs are attached.", "fatal"))
    if not source_urls:
        blocking_issues.append("missing_source_urls")
        missing_evidence.append("source_urls")
        reasons.append(OpportunityGateReason("missing_source_urls", "No source URLs are attached.", "fatal"))


def _add_problem_reasons(
    reasons: list[OpportunityGateReason],
    blocking_issues: list[str],
    candidate: OpportunityCandidate,
) -> None:
    problem_text = candidate.problem_statement.lower()
    if _unknown(candidate.problem_statement) or problem_text in {"generic", "generic problem"}:
        blocking_issues.append("generic_or_unknown_problem")
        reasons.append(OpportunityGateReason("generic_problem", "Problem statement is unknown or generic.", "fatal"))
    elif any(marker in problem_text for marker in STRONG_PAIN_MARKERS):
        reasons.append(OpportunityGateReason("concrete_problem", "Problem statement includes concrete finance pain.", "positive"))
    else:
        reasons.append(OpportunityGateReason("problem_needs_review", "Problem statement is plausible but not strongly specific.", "medium"))
    if _unknown(candidate.current_workaround):
        reasons.append(OpportunityGateReason("workaround_unknown", "Current workaround is unknown.", "medium"))
    else:
        reasons.append(OpportunityGateReason("workaround_present", "Current workaround evidence is present.", "positive"))
    if _unknown(candidate.possible_buyer):
        reasons.append(OpportunityGateReason("buyer_unknown", "Possible buyer is unknown.", "medium"))
    if _unknown(candidate.product_wedge):
        reasons.append(OpportunityGateReason("product_wedge_unknown", "Product wedge is unknown.", "medium"))


def _add_risk_reasons(
    reasons: list[OpportunityGateReason],
    blocking_issues: list[str],
    risk_notes: list[str],
) -> None:
    risk_text = " ".join(risk_notes).lower()
    if any(marker in risk_text for marker in FATAL_RISK_MARKERS):
        blocking_issues.append("vendor_or_generic_risk")
        reasons.append(OpportunityGateReason("vendor_or_generic_risk", "Vendor, SEO, generic, or false-positive risk dominates.", "fatal"))
    elif any(marker in risk_text for marker in INSUFFICIENT_RISK_MARKERS):
        reasons.append(OpportunityGateReason("insufficient_or_duplicate_risk", "Evidence has insufficient, duplicate, or needs-more-evidence risk.", "high"))


def _add_unsupported_reasons(
    reasons: list[OpportunityGateReason],
    unsupported: list[str],
) -> None:
    if not unsupported:
        reasons.append(OpportunityGateReason("unsupported_assumptions_limited", "No unsupported assumptions are listed.", "positive"))
        return
    severity = "high" if len(unsupported) > 2 else "medium"
    reasons.append(
        OpportunityGateReason(
            "unsupported_assumptions_present",
            f"Unsupported assumptions require founder review: {', '.join(unsupported)}.",
            severity,
        )
    )


def _add_support_reasons(
    reasons: list[OpportunityGateReason],
    candidate: OpportunityCandidate,
    pack: EvidencePack | None,
) -> None:
    combined = f"{candidate.problem_statement} {candidate.opportunity_sketch} {candidate.why_now}".lower()
    if any(marker in combined for marker in STRONG_PAIN_MARKERS):
        reasons.append(OpportunityGateReason("pain_evidence_present", "Evidence supports a concrete pain pattern.", "positive"))
    if pack is None:
        return
    if pack.is_insufficient_evidence or pack.recurrence_count < 2:
        reasons.append(OpportunityGateReason("insufficient_evidence", "Evidence pack is thin or explicitly insufficient.", "high"))
    if pack.source_diversity < 2:
        reasons.append(OpportunityGateReason("low_source_diversity", "Source diversity is limited.", "medium"))
    else:
        reasons.append(OpportunityGateReason("source_diversity_present", "Evidence spans multiple source types.", "positive"))


def _missing_evidence(candidate: OpportunityCandidate, pack: EvidencePack | None) -> list[str]:
    missing = []
    if _unknown(candidate.possible_buyer):
        missing.append("possible_buyer")
    if _unknown(candidate.product_wedge):
        missing.append("product_wedge")
    if _unknown(candidate.current_workaround):
        missing.append("current_workaround")
    if _unknown(candidate.why_now):
        missing.append("why_now")
    if pack is not None:
        if pack.is_insufficient_evidence:
            missing.append("sufficient_evidence")
        if pack.source_diversity < 2:
            missing.append("source_diversity")
        if not pack.price_signal_ids:
            missing.append("price_or_willingness_to_pay")
    return _ordered_strings(missing)


def _risk_notes(candidate: OpportunityCandidate, pack: EvidencePack | None) -> list[str]:
    notes = list(candidate.risk_notes)
    if pack is not None:
        notes.extend(f"{note.risk_type}/{note.severity}: {note.note}" for note in pack.risk_notes)
    return _ordered_strings(notes)


def _get_value(item: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(field_name, default)
    return getattr(item, field_name, default)


def _unknown(value: str) -> bool:
    clean = str(value).strip().lower()
    return not clean or clean == UNKNOWN or clean in {"n/a", "none"}


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_string_list(values: list[str], field_name: str) -> None:
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{field_name} must contain non-empty strings")
