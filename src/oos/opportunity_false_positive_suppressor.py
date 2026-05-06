from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from .evidence_pack import EvidencePack, evidence_pack_from_dict
from .evidence_sufficiency_scoring import (
    EvidenceSufficiencyScore,
    score_evidence_sufficiency,
)
from .opportunity_sketch import UNKNOWN, OpportunityCandidate, opportunity_sketch_from_dict


OPPORTUNITY_FALSE_POSITIVE_SCHEMA_VERSION = "opportunity_false_positive_assessment.v1"

SEVERITY_NONE = "none"
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

KEEP = "keep"
PARK = "park"
REJECT = "reject"

FOUNDER_REVIEW = "founder_review"
COLLECT_MORE_EVIDENCE = "collect_more_evidence"
SUPPRESS_AS_FALSE_POSITIVE = "suppress_as_false_positive"
CLARIFY_BUYER = "clarify_buyer"
CLARIFY_WORKAROUND = "clarify_workaround"

ALLOWED_SEVERITIES = {SEVERITY_NONE, SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL}
ALLOWED_GATE_DECISIONS = {KEEP, PARK, REJECT}
ALLOWED_NEXT_ACTIONS = {
    FOUNDER_REVIEW,
    COLLECT_MORE_EVIDENCE,
    SUPPRESS_AS_FALSE_POSITIVE,
    CLARIFY_BUYER,
    CLARIFY_WORKAROUND,
}

GENERIC_OPPORTUNITY_PATTERNS = (
    "ai dashboard",
    "dashboard for finance",
    "generic finance dashboard",
    "generic accounting",
    "accounting solution",
    "all-in-one",
    "all in one",
    "transform your business",
    "streamline your business",
    "unlock growth",
    "improve efficiency",
)

VENDOR_PROMO_PATTERNS = (
    "vendor_promo",
    "vendor promo",
    "seo",
    "seo_noise",
    "source_quality_issue",
    "free demo",
    "affordable pricing",
    "authorized provider",
    "professional training",
    "technical assistance",
    "key advantages",
)

PRODUCT_SUBMISSION_PATTERNS = (
    "product_submission",
    "product submission",
    "marketplace listing",
    "mcp server submission",
    "hosted server for quickbooks",
    "solution pitch",
)

DISGUISED_CONSULTING_PATTERNS = (
    "consulting service",
    "consultation",
    "bookkeeping expert",
    "hire our experts",
    "done-for-you",
    "done for you",
    "professional services",
)

PAIN_PATTERNS = (
    "unpaid invoice",
    "invoice follow",
    "cash collection",
    "payment follow",
    "balance sheet",
    "month-end",
    "month end",
    "sticky notes",
    "spreadsheet",
    "can't afford",
    "cannot afford",
)


@dataclass(frozen=True)
class OpportunityFalsePositiveReason:
    code: str
    message: str
    severity: str = SEVERITY_MEDIUM

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpportunityFalsePositiveReason:
        return cls(
            code=str(data.get("code", "")),
            message=str(data.get("message", "")),
            severity=str(data.get("severity", SEVERITY_MEDIUM)),
        )


@dataclass(frozen=True)
class OpportunityFalsePositiveAssessment:
    assessment_id: str
    opportunity_id: str
    evidence_pack_id: str
    is_false_positive: bool
    severity: str
    reasons: list[OpportunityFalsePositiveReason]
    matched_patterns: list[str]
    recommended_gate_decision: str
    recommended_next_action: str
    evidence_ids: list[str]
    source_signal_ids: list[str]
    source_urls: list[str]
    schema_version: str = OPPORTUNITY_FALSE_POSITIVE_SCHEMA_VERSION
    auto_promote: bool = False
    founder_decision_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "opportunity_id": self.opportunity_id,
            "evidence_pack_id": self.evidence_pack_id,
            "is_false_positive": self.is_false_positive,
            "severity": self.severity,
            "reasons": [reason.to_dict() for reason in self.reasons],
            "matched_patterns": list(self.matched_patterns),
            "recommended_gate_decision": self.recommended_gate_decision,
            "recommended_next_action": self.recommended_next_action,
            "evidence_ids": list(self.evidence_ids),
            "source_signal_ids": list(self.source_signal_ids),
            "source_urls": list(self.source_urls),
            "schema_version": self.schema_version,
            "auto_promote": self.auto_promote,
            "founder_decision_required": self.founder_decision_required,
        }

    def validate(self) -> None:
        validate_opportunity_false_positive_assessment(self)


def assess_opportunity_false_positive(
    opportunity: OpportunityCandidate | dict[str, Any],
    evidence_pack: EvidencePack | dict[str, Any] | None = None,
    *,
    evidence_sufficiency_score: EvidenceSufficiencyScore | dict[str, Any] | None = None,
) -> OpportunityFalsePositiveAssessment:
    candidate = opportunity_sketch_from_dict(opportunity) if isinstance(opportunity, dict) else opportunity
    pack = evidence_pack_from_dict(evidence_pack) if isinstance(evidence_pack, dict) else evidence_pack
    if pack is not None:
        pack.validate()
        if candidate.evidence_pack_id and candidate.evidence_pack_id != pack.evidence_pack_id:
            raise ValueError("opportunity and evidence_pack must reference the same evidence_pack_id")

    score = _score_from_input(evidence_sufficiency_score, candidate, pack)
    combined_text = _combined_text(candidate, pack)
    risk_text = _risk_text(candidate, pack, score)
    evidence_ids = _ordered_strings(candidate.evidence_ids)
    source_signal_ids = _ordered_strings(candidate.source_signal_ids)
    source_urls = _ordered_strings(candidate.source_urls)
    reasons: list[OpportunityFalsePositiveReason] = []
    matched_patterns: list[str] = []

    _add_traceability_reasons(reasons, evidence_ids, source_urls)
    _add_pattern_reasons(reasons, matched_patterns, combined_text, risk_text)
    _add_structure_reasons(reasons, candidate)
    _add_sufficiency_reasons(reasons, score)
    _add_recurrence_reasons(reasons, pack)

    severity = _assessment_severity(reasons)
    recommended_gate_decision = _recommended_gate_decision(severity)
    recommended_next_action = _recommended_next_action(candidate, severity, reasons)
    assessment = OpportunityFalsePositiveAssessment(
        assessment_id=make_false_positive_assessment_id(candidate.opportunity_id or candidate.evidence_pack_id),
        opportunity_id=candidate.opportunity_id,
        evidence_pack_id=candidate.evidence_pack_id,
        is_false_positive=severity in {SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL},
        severity=severity,
        reasons=sorted(reasons, key=lambda reason: (reason.severity, reason.code, reason.message)),
        matched_patterns=_ordered_strings(matched_patterns),
        recommended_gate_decision=recommended_gate_decision,
        recommended_next_action=recommended_next_action,
        evidence_ids=evidence_ids,
        source_signal_ids=source_signal_ids,
        source_urls=source_urls,
    )
    assessment.validate()
    return assessment


def make_false_positive_assessment_id(opportunity_id: str) -> str:
    value = str(opportunity_id).strip() or "unknown_opportunity"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"opportunity_false_positive_{digest}"


def validate_opportunity_false_positive_assessment(assessment: OpportunityFalsePositiveAssessment) -> None:
    for field_name in (
        "assessment_id",
        "opportunity_id",
        "evidence_pack_id",
        "severity",
        "recommended_gate_decision",
        "recommended_next_action",
        "schema_version",
    ):
        _require_non_empty(getattr(assessment, field_name), f"OpportunityFalsePositiveAssessment.{field_name}")
    if assessment.schema_version != OPPORTUNITY_FALSE_POSITIVE_SCHEMA_VERSION:
        raise ValueError("OpportunityFalsePositiveAssessment.schema_version must be opportunity_false_positive_assessment.v1")
    if assessment.severity not in ALLOWED_SEVERITIES:
        raise ValueError("OpportunityFalsePositiveAssessment.severity is invalid")
    if assessment.recommended_gate_decision not in ALLOWED_GATE_DECISIONS:
        raise ValueError("OpportunityFalsePositiveAssessment.recommended_gate_decision is invalid")
    if assessment.recommended_next_action not in ALLOWED_NEXT_ACTIONS:
        raise ValueError("OpportunityFalsePositiveAssessment.recommended_next_action is invalid")
    if assessment.auto_promote:
        raise ValueError("False-positive suppressor must never auto-promote")
    if not assessment.founder_decision_required:
        raise ValueError("Founder decision authority must be preserved")
    for field_name in ("matched_patterns", "evidence_ids", "source_signal_ids", "source_urls"):
        _require_string_list(getattr(assessment, field_name), f"OpportunityFalsePositiveAssessment.{field_name}")
    for reason in assessment.reasons:
        _require_non_empty(reason.code, "OpportunityFalsePositiveReason.code")
        _require_non_empty(reason.message, "OpportunityFalsePositiveReason.message")
        if reason.severity not in ALLOWED_SEVERITIES - {SEVERITY_NONE}:
            raise ValueError("OpportunityFalsePositiveReason.severity is invalid")


def _score_from_input(
    score: EvidenceSufficiencyScore | dict[str, Any] | None,
    candidate: OpportunityCandidate,
    pack: EvidencePack | None,
) -> EvidenceSufficiencyScore:
    if isinstance(score, EvidenceSufficiencyScore):
        return score
    if isinstance(score, dict):
        return EvidenceSufficiencyScore(
            total_score=float(score.get("total_score", 0.0)),
            score_band=str(score.get("score_band", "insufficient")),
            dimension_scores={str(key): float(value) for key, value in score.get("dimension_scores", {}).items()},
            positive_factors=[str(item) for item in score.get("positive_factors", [])],
            missing_evidence=[str(item) for item in score.get("missing_evidence", [])],
            risk_factors=[str(item) for item in score.get("risk_factors", [])],
            evidence_ids=[str(item) for item in score.get("evidence_ids", [])],
            source_signal_ids=[str(item) for item in score.get("source_signal_ids", [])],
            source_urls=[str(item) for item in score.get("source_urls", [])],
            schema_version=str(score.get("schema_version", "evidence_sufficiency_score.v1")),
            auto_promote=bool(score.get("auto_promote", False)),
            founder_decision_required=bool(score.get("founder_decision_required", True)),
        )
    return score_evidence_sufficiency(candidate, pack)


def _add_traceability_reasons(
    reasons: list[OpportunityFalsePositiveReason],
    evidence_ids: list[str],
    source_urls: list[str],
) -> None:
    if not evidence_ids:
        reasons.append(
            OpportunityFalsePositiveReason(
                "missing_evidence_ids",
                "Opportunity has no evidence IDs and cannot be traced.",
                SEVERITY_CRITICAL,
            )
        )
    if not source_urls:
        reasons.append(
            OpportunityFalsePositiveReason(
                "missing_source_urls",
                "Opportunity has no source URLs and cannot be traced.",
                SEVERITY_CRITICAL,
            )
        )


def _add_pattern_reasons(
    reasons: list[OpportunityFalsePositiveReason],
    matched_patterns: list[str],
    combined_text: str,
    risk_text: str,
) -> None:
    _match_patterns(matched_patterns, GENERIC_OPPORTUNITY_PATTERNS, combined_text)
    _match_patterns(matched_patterns, VENDOR_PROMO_PATTERNS, combined_text + " " + risk_text)
    _match_patterns(matched_patterns, PRODUCT_SUBMISSION_PATTERNS, combined_text + " " + risk_text)
    _match_patterns(matched_patterns, DISGUISED_CONSULTING_PATTERNS, combined_text + " " + risk_text)
    if any(pattern in matched_patterns for pattern in GENERIC_OPPORTUNITY_PATTERNS):
        reasons.append(
            OpportunityFalsePositiveReason(
                "generic_opportunity",
                "Opportunity language is generic and not anchored to a concrete pain.",
                SEVERITY_HIGH if not _has_pain_marker(combined_text) else SEVERITY_MEDIUM,
            )
        )
    if any(pattern in matched_patterns for pattern in VENDOR_PROMO_PATTERNS):
        reasons.append(
            OpportunityFalsePositiveReason(
                "vendor_or_seo_derived",
                "Opportunity appears derived from vendor, SEO, or promotional copy.",
                SEVERITY_HIGH,
            )
        )
    if any(pattern in matched_patterns for pattern in PRODUCT_SUBMISSION_PATTERNS):
        reasons.append(
            OpportunityFalsePositiveReason(
                "product_submission_derived",
                "Opportunity appears derived from a product submission or marketplace listing.",
                SEVERITY_HIGH,
            )
        )
    if any(pattern in matched_patterns for pattern in DISGUISED_CONSULTING_PATTERNS):
        reasons.append(
            OpportunityFalsePositiveReason(
                "disguised_consulting",
                "Opportunity appears derived from consulting or service-page copy rather than user pain.",
                SEVERITY_HIGH,
            )
        )


def _add_structure_reasons(
    reasons: list[OpportunityFalsePositiveReason],
    candidate: OpportunityCandidate,
) -> None:
    if _unknown(candidate.possible_buyer) and _unknown(candidate.current_workaround):
        reasons.append(
            OpportunityFalsePositiveReason(
                "buyer_and_workaround_missing",
                "No clear buyer and no current workaround are supported.",
                SEVERITY_MEDIUM,
            )
        )
    elif _unknown(candidate.possible_buyer):
        reasons.append(OpportunityFalsePositiveReason("buyer_missing", "Possible buyer is not supported.", SEVERITY_LOW))
    elif _unknown(candidate.current_workaround):
        reasons.append(OpportunityFalsePositiveReason("workaround_missing", "Current workaround is not supported.", SEVERITY_LOW))
    unsupported_count = len(_ordered_strings(candidate.unsupported_assumptions))
    if unsupported_count >= 4:
        reasons.append(
            OpportunityFalsePositiveReason(
                "unsupported_assumptions_dominate",
                "Opportunity relies on too many unsupported assumptions.",
                SEVERITY_HIGH,
            )
        )
    elif unsupported_count >= 3:
        reasons.append(
            OpportunityFalsePositiveReason(
                "unsupported_assumptions_heavy",
                "Opportunity has several unsupported assumptions.",
                SEVERITY_MEDIUM,
            )
        )
    if _solution_pitch_without_pain(candidate):
        reasons.append(
            OpportunityFalsePositiveReason(
                "solution_pitch_without_user_pain",
                "Opportunity is framed as a solution pitch without concrete user pain.",
                SEVERITY_HIGH,
            )
        )


def _add_sufficiency_reasons(
    reasons: list[OpportunityFalsePositiveReason],
    score: EvidenceSufficiencyScore,
) -> None:
    if score.score_band == "insufficient":
        reasons.append(
            OpportunityFalsePositiveReason(
                "evidence_sufficiency_insufficient",
                "Evidence sufficiency score is insufficient.",
                SEVERITY_CRITICAL,
            )
        )
    elif score.score_band == "weak":
        reasons.append(
            OpportunityFalsePositiveReason(
                "evidence_sufficiency_weak",
                "Evidence sufficiency score is weak.",
                SEVERITY_MEDIUM,
            )
        )


def _add_recurrence_reasons(
    reasons: list[OpportunityFalsePositiveReason],
    pack: EvidencePack | None,
) -> None:
    if pack is None:
        return
    duplicate_text = " ".join(f"{note.risk_type} {note.note}" for note in pack.risk_notes).lower()
    if pack.recurrence_count < 2 and pack.source_diversity < 2:
        severity = SEVERITY_MEDIUM if "duplicate" in duplicate_text else SEVERITY_LOW
        reasons.append(
            OpportunityFalsePositiveReason(
                "single_source_or_non_recurring",
                "Evidence is single-source or non-recurring and should not pretend to prove recurrence.",
                severity,
            )
        )
    if "duplicate" in duplicate_text:
        reasons.append(
            OpportunityFalsePositiveReason(
                "duplicate_evidence_risk",
                "Duplicate evidence risk is present and must not inflate recurrence.",
                SEVERITY_MEDIUM,
            )
        )


def _assessment_severity(reasons: list[OpportunityFalsePositiveReason]) -> str:
    order = {
        SEVERITY_NONE: 0,
        SEVERITY_LOW: 1,
        SEVERITY_MEDIUM: 2,
        SEVERITY_HIGH: 3,
        SEVERITY_CRITICAL: 4,
    }
    if not reasons:
        return SEVERITY_NONE
    return max((reason.severity for reason in reasons), key=lambda severity: order[severity])


def _recommended_gate_decision(severity: str) -> str:
    if severity == SEVERITY_CRITICAL:
        return REJECT
    if severity in {SEVERITY_HIGH, SEVERITY_MEDIUM}:
        return PARK
    return KEEP


def _recommended_next_action(
    candidate: OpportunityCandidate,
    severity: str,
    reasons: list[OpportunityFalsePositiveReason],
) -> str:
    reason_codes = {reason.code for reason in reasons}
    if severity in {SEVERITY_HIGH, SEVERITY_CRITICAL}:
        return SUPPRESS_AS_FALSE_POSITIVE
    if "buyer_missing" in reason_codes or "buyer_and_workaround_missing" in reason_codes:
        return CLARIFY_BUYER
    if "workaround_missing" in reason_codes:
        return CLARIFY_WORKAROUND
    if severity == SEVERITY_MEDIUM:
        return COLLECT_MORE_EVIDENCE
    return FOUNDER_REVIEW


def _combined_text(candidate: OpportunityCandidate, pack: EvidencePack | None) -> str:
    values = [
        candidate.problem_statement,
        candidate.target_user,
        candidate.current_workaround,
        candidate.opportunity_sketch,
        candidate.why_now,
        candidate.possible_buyer,
        candidate.product_wedge,
        " ".join(candidate.unsupported_assumptions),
        " ".join(candidate.risk_notes),
    ]
    if pack is not None:
        values.extend(pack.summaries)
        values.extend(item.summary for item in pack.items)
    return " ".join(str(value) for value in values).lower()


def _risk_text(
    candidate: OpportunityCandidate,
    pack: EvidencePack | None,
    score: EvidenceSufficiencyScore,
) -> str:
    values = list(candidate.risk_notes) + list(score.risk_factors) + list(score.missing_evidence)
    if pack is not None:
        values.extend(f"{note.risk_type} {note.severity} {note.note}" for note in pack.risk_notes)
    return " ".join(str(value) for value in values).lower()


def _match_patterns(matched_patterns: list[str], patterns: tuple[str, ...], text: str) -> None:
    for pattern in patterns:
        if pattern in text:
            matched_patterns.append(pattern)


def _has_pain_marker(text: str) -> bool:
    return any(pattern in text for pattern in PAIN_PATTERNS)


def _solution_pitch_without_pain(candidate: OpportunityCandidate) -> bool:
    text = f"{candidate.problem_statement} {candidate.opportunity_sketch} {candidate.product_wedge}".lower()
    solution_terms = ("platform", "dashboard", "all-in-one", "all in one", "tool", "software", "solution")
    return any(term in text for term in solution_terms) and not _has_pain_marker(text)


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
