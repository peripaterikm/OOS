from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional

from .ai_contracts import AI_METADATA_REQUIRED_FIELDS, AIStageStatus, PromptIdentity, build_ai_metadata
from .opportunity_framing import OpportunityCard


OPPORTUNITY_GATE_PROMPT = PromptIdentity(
    prompt_name="opportunity_quality_gate",
    prompt_version="opportunity_quality_gate_v1",
)
OPPORTUNITY_GATE_MODEL_ID = "deterministic_opportunity_quality_gate"
OPPORTUNITY_GATE_STATUSES = {"pass", "park", "reject"}


@dataclass(frozen=True)
class OpportunityGateCriterionResult:
    criterion: str
    passed: bool
    explanation: str
    severity: str = "info"

    def validate(self) -> None:
        for field_name in ("criterion", "explanation", "severity"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be a bool")
        if self.severity not in {"info", "warning", "blocking"}:
            raise ValueError("severity must be info, warning, or blocking")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class OpportunityGateDecision:
    opportunity_id: str
    status: str
    explanation: str
    criteria_results: List[OpportunityGateCriterionResult]
    missing_fields: List[str]
    weaknesses: List[str]
    recommendation: str
    next_action: str
    confidence: float
    linked_signal_ids: List[str]
    linked_cluster_id: str
    source_opportunity_id: str
    source_signal_ids: List[str]
    source_cluster_id: str
    founder_override_status: Optional[str] = None
    ai_metadata: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        for field_name in (
            "opportunity_id",
            "status",
            "explanation",
            "recommendation",
            "next_action",
            "linked_cluster_id",
            "source_opportunity_id",
            "source_cluster_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.status not in OPPORTUNITY_GATE_STATUSES:
            raise ValueError("status must be pass, park, or reject")
        if not isinstance(self.confidence, (int, float)) or not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be a number between 0 and 1")
        if not self.linked_signal_ids or any(not str(value).strip() for value in self.linked_signal_ids):
            raise ValueError("linked_signal_ids must contain non-empty strings")
        if self.source_signal_ids != self.linked_signal_ids:
            raise ValueError("source_signal_ids must preserve linked_signal_ids")
        if self.source_cluster_id != self.linked_cluster_id:
            raise ValueError("source_cluster_id must preserve linked_cluster_id")
        for criterion in self.criteria_results:
            criterion.validate()
        if self.founder_override_status is not None and self.founder_override_status not in OPPORTUNITY_GATE_STATUSES:
            raise ValueError("founder_override_status must be pass, park, reject, or None")
        if self.ai_metadata is not None:
            for field_name in AI_METADATA_REQUIRED_FIELDS:
                if field_name not in self.ai_metadata:
                    raise ValueError(f"ai_metadata missing required field: {field_name}")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        data = asdict(self)
        data["confidence"] = float(data["confidence"])
        data["criteria_results"] = [criterion.to_dict() for criterion in self.criteria_results]
        return data


@dataclass(frozen=True)
class OpportunityGateResult:
    decisions: List[OpportunityGateDecision]
    source_opportunity_ids: List[str]
    stage_status: str
    fallback_used: bool
    rejected_record_errors: List[str]
    ai_metadata: Dict[str, Any]

    def validate(self) -> None:
        if self.stage_status not in {status.value for status in AIStageStatus}:
            raise ValueError("stage_status must be success, failed, or degraded")
        if not isinstance(self.fallback_used, bool):
            raise ValueError("fallback_used must be a bool")
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")
        if len(self.decisions) != len(self.source_opportunity_ids):
            raise ValueError("gate result should preserve one decision per source opportunity")
        for decision in self.decisions:
            decision.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "decisions": [decision.to_dict() for decision in self.decisions],
            "source_opportunity_ids": self.source_opportunity_ids,
            "stage_status": self.stage_status,
            "fallback_used": self.fallback_used,
            "rejected_record_errors": self.rejected_record_errors,
            "ai_metadata": self.ai_metadata,
        }


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _metadata_for(
    *,
    opportunities: List[OpportunityCard],
    linked_input_ids: List[str],
    fallback_used: bool,
    stage_confidence: float,
    stage_status: AIStageStatus,
    failure_reason: str = "",
) -> Dict[str, Any]:
    return build_ai_metadata(
        prompt=OPPORTUNITY_GATE_PROMPT,
        model_id=OPPORTUNITY_GATE_MODEL_ID,
        input_payload=[asdict(opportunity) for opportunity in opportunities],
        generation_mode="deterministic_gate",
        linked_input_ids=linked_input_ids,
        fallback_used=fallback_used,
        stage_confidence=stage_confidence,
        stage_status=stage_status,
        failure_reason=failure_reason,
        fallback_recommendation="Founder decision remains final; use this deterministic recommendation as advisory only.",
        degraded_mode=fallback_used or stage_status == AIStageStatus.degraded,
    ).to_dict()


def _criterion(name: str, passed: bool, explanation: str, *, severity: str = "info") -> OpportunityGateCriterionResult:
    return OpportunityGateCriterionResult(
        criterion=name,
        passed=passed,
        explanation=explanation,
        severity=severity,
    )


def _safe_ids(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _safe_reject_decision(opportunity: OpportunityCard, *, reason: str) -> OpportunityGateDecision:
    opportunity_id = str(getattr(opportunity, "opportunity_id", "") or "invalid_opportunity").strip()
    linked_signal_ids = _safe_ids(getattr(opportunity, "linked_signal_ids", [])) or ["unknown_signal"]
    linked_cluster_id = str(getattr(opportunity, "linked_cluster_id", "") or "unknown_cluster").strip()
    return OpportunityGateDecision(
        opportunity_id=opportunity_id,
        status="reject",
        explanation=f"Opportunity failed quality gate validation: {reason}",
        criteria_results=[
            _criterion("valid_opportunity_contract", False, reason, severity="blocking"),
        ],
        missing_fields=["valid_opportunity_contract"],
        weaknesses=[reason],
        recommendation="Reject until the opportunity card contract is valid.",
        next_action="Regenerate or repair the opportunity card before founder review.",
        confidence=0.0,
        linked_signal_ids=linked_signal_ids,
        linked_cluster_id=linked_cluster_id,
        source_opportunity_id=opportunity_id,
        source_signal_ids=linked_signal_ids,
        source_cluster_id=linked_cluster_id,
    )


def evaluate_opportunity(opportunity: OpportunityCard) -> OpportunityGateDecision:
    linked_signal_ids = list(opportunity.linked_signal_ids)
    linked_cluster_id = opportunity.linked_cluster_id
    criteria: List[OpportunityGateCriterionResult] = []
    missing_fields: List[str] = []
    weaknesses: List[str] = []

    checks = [
        ("clear_user", _non_empty(opportunity.target_user), "target_user is present", "target_user is missing", "target_user", "blocking"),
        ("concrete_pain", _non_empty(opportunity.pain), "pain is present", "pain is missing", "pain", "blocking"),
        (
            "evidence",
            bool(opportunity.evidence) and not opportunity.evidence_missing,
            "linked evidence is present",
            "linked evidence is missing",
            "evidence",
            "blocking",
        ),
        (
            "urgency_or_cost",
            _non_empty(opportunity.urgency) or _non_empty(opportunity.monetization_hypothesis),
            "urgency or cost signal is present",
            "urgency or cost signal is missing",
            "urgency_or_cost",
            "warning",
        ),
        (
            "possible_product_angle",
            _non_empty(opportunity.possible_wedge),
            "possible wedge/product angle is present",
            "possible wedge/product angle is missing",
            "possible_wedge",
            "warning",
        ),
        (
            "risks_uncertainty",
            bool(opportunity.risks) or bool(opportunity.assumptions),
            "risks or assumptions are present",
            "risks and uncertainty are missing",
            "risks_uncertainty",
            "warning",
        ),
        (
            "traceability",
            bool(opportunity.linked_signal_ids) and _non_empty(opportunity.linked_cluster_id),
            "signal and cluster traceability is present",
            "signal or cluster traceability is missing",
            "traceability",
            "blocking",
        ),
    ]

    for criterion_name, passed, ok_message, fail_message, field_name, severity in checks:
        criteria.append(_criterion(criterion_name, passed, ok_message if passed else fail_message, severity=severity if not passed else "info"))
        if not passed:
            missing_fields.append(field_name)
            weaknesses.append(fail_message)

    blocking_failures = [criterion for criterion in criteria if not criterion.passed and criterion.severity == "blocking"]
    warning_failures = [criterion for criterion in criteria if not criterion.passed and criterion.severity == "warning"]
    if any(criterion.criterion in {"clear_user", "concrete_pain", "traceability"} for criterion in blocking_failures):
        status = "reject"
        recommendation = "Reject until core user, pain, and traceability are repaired."
        next_action = "Regenerate the opportunity card or return to signal analysis."
        confidence = 0.2
    elif any(criterion.criterion == "evidence" for criterion in blocking_failures):
        status = "park"
        recommendation = "Park until linked evidence is added."
        next_action = "Attach evidence or reject if evidence cannot be found."
        confidence = 0.35
    elif warning_failures:
        status = "park"
        recommendation = "Park until the missing product angle, urgency, or uncertainty is clarified."
        next_action = "Add the missing fields before ideation."
        confidence = 0.55
    else:
        status = "pass"
        recommendation = "Pass to pattern-guided ideation."
        next_action = "Use as input for Roadmap 5.1 ideation."
        confidence = 0.9

    explanation = (
        "Opportunity passes the deterministic quality gate."
        if status == "pass"
        else "Opportunity does not yet meet the deterministic quality gate: " + "; ".join(weaknesses)
    )
    return OpportunityGateDecision(
        opportunity_id=opportunity.opportunity_id,
        status=status,
        explanation=explanation,
        criteria_results=criteria,
        missing_fields=missing_fields,
        weaknesses=weaknesses,
        recommendation=recommendation,
        next_action=next_action,
        confidence=confidence,
        linked_signal_ids=linked_signal_ids,
        linked_cluster_id=linked_cluster_id,
        source_opportunity_id=opportunity.opportunity_id,
        source_signal_ids=linked_signal_ids,
        source_cluster_id=linked_cluster_id,
        founder_override_status=None,
    )


def evaluate_opportunity_batch(opportunities: List[OpportunityCard]) -> OpportunityGateResult:
    decisions: List[OpportunityGateDecision] = []
    rejected_record_errors: List[str] = []
    for index, opportunity in enumerate(opportunities):
        try:
            decision = evaluate_opportunity(opportunity)
            decision.validate()
            decisions.append(decision)
        except Exception as exc:
            rejected_record_errors.append(f"opportunities[{index}]: {exc}")
            decisions.append(_safe_reject_decision(opportunity, reason=str(exc)))

    source_opportunity_ids = [decision.source_opportunity_id for decision in decisions]
    fallback_used = bool(rejected_record_errors)
    stage_status = AIStageStatus.degraded if fallback_used else AIStageStatus.success
    stage_confidence = min([decision.confidence for decision in decisions] + [1.0])
    failure_reason = "; ".join(rejected_record_errors)
    metadata = _metadata_for(
        opportunities=opportunities,
        linked_input_ids=source_opportunity_ids,
        fallback_used=fallback_used,
        stage_confidence=stage_confidence,
        stage_status=stage_status,
        failure_reason=failure_reason,
    )
    decisions_with_metadata = [
        OpportunityGateDecision(
            **{
                **decision.to_dict(),
                "criteria_results": decision.criteria_results,
                "ai_metadata": metadata,
            }
        )
        for decision in decisions
    ]
    result = OpportunityGateResult(
        decisions=decisions_with_metadata,
        source_opportunity_ids=source_opportunity_ids,
        stage_status=stage_status.value,
        fallback_used=fallback_used,
        rejected_record_errors=rejected_record_errors,
        ai_metadata=metadata,
    )
    result.validate()
    return result
