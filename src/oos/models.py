from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_list(value: Any, field_name: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SignalStatus(str, Enum):
    validated = "validated"
    weak = "weak"
    noise = "noise"


class IdeaScreenStatus(str, Enum):
    candidate = "candidate"
    screened_pass = "screened_pass"
    screened_park = "screened_park"
    screened_kill = "screened_kill"


class IdeationGenerationMode(str, Enum):
    heuristic_baseline = "heuristic_baseline"
    llm_assisted = "llm_assisted"
    heuristic_fallback_after_llm_failure = "heuristic_fallback_after_llm_failure"


class PortfolioStateEnum(str, Enum):
    Active = "Active"
    Parked = "Parked"
    Killed = "Killed"
    Graduated = "Graduated"


class FounderReviewDecisionEnum(str, Enum):
    Active = "Active"
    Parked = "Parked"
    Killed = "Killed"


@dataclass(frozen=True)
class Signal:
    id: str
    source: str
    timestamp: str
    raw_content: str
    extracted_pain: str
    candidate_icp: str
    validity_specificity: int
    validity_recurrence: int
    validity_workaround: int
    validity_cost_signal: int
    validity_icp_match: int
    validity_score: int
    status: SignalStatus
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        _require_non_empty(self.id, "Signal.id")
        _require_non_empty(self.source, "Signal.source")
        _require_non_empty(self.timestamp, "Signal.timestamp")
        _require_non_empty(self.raw_content, "Signal.raw_content")
        _require_non_empty(self.extracted_pain, "Signal.extracted_pain")
        _require_non_empty(self.candidate_icp, "Signal.candidate_icp")
        for name in (
            "validity_specificity",
            "validity_recurrence",
            "validity_workaround",
            "validity_cost_signal",
            "validity_icp_match",
            "validity_score",
        ):
            v = getattr(self, name)
            if not isinstance(v, int) or v < 0:
                raise ValueError(f"Signal.{name} must be a non-negative int")
        if self.status == SignalStatus.noise:
            if self.rejection_reason is None or not str(self.rejection_reason).strip():
                raise ValueError("Signal.rejection_reason is required when status=noise")


@dataclass(frozen=True)
class OpportunityCard:
    id: str
    title: str
    source_signal_ids: List[str]
    pain_summary: str
    icp: str
    opportunity_type: str
    why_it_matters: str
    early_monetization_options: List[str] = field(default_factory=list)
    initial_notes: str = ""
    created_at: str = field(default_factory=_iso_utc_now_seconds)
    updated_at: str = field(default_factory=_iso_utc_now_seconds)

    def validate(self) -> None:
        _require_non_empty(self.id, "OpportunityCard.id")
        _require_non_empty(self.title, "OpportunityCard.title")
        _require_list(self.source_signal_ids, "OpportunityCard.source_signal_ids")
        if not self.source_signal_ids or any(not str(x).strip() for x in self.source_signal_ids):
            raise ValueError("OpportunityCard.source_signal_ids must be a non-empty list of strings")
        _require_non_empty(self.pain_summary, "OpportunityCard.pain_summary")
        _require_non_empty(self.icp, "OpportunityCard.icp")
        _require_non_empty(self.opportunity_type, "OpportunityCard.opportunity_type")
        _require_non_empty(self.why_it_matters, "OpportunityCard.why_it_matters")


@dataclass(frozen=True)
class IdeaVariant:
    id: str
    opportunity_id: str
    short_concept: str
    business_model: str
    standardization_focus: str
    ai_leverage: str
    external_execution_needed: str
    rough_monetization_model: str
    status: IdeaScreenStatus = IdeaScreenStatus.candidate
    generation_mode: IdeationGenerationMode = IdeationGenerationMode.heuristic_baseline
    ai_metadata: Optional[Dict[str, Any]] = None
    screen_result_id: Optional[str] = None
    created_at: str = field(default_factory=_iso_utc_now_seconds)
    updated_at: str = field(default_factory=_iso_utc_now_seconds)

    def validate(self) -> None:
        _require_non_empty(self.id, "IdeaVariant.id")
        _require_non_empty(self.opportunity_id, "IdeaVariant.opportunity_id")
        _require_non_empty(self.short_concept, "IdeaVariant.short_concept")
        _require_non_empty(self.business_model, "IdeaVariant.business_model")
        _require_non_empty(self.standardization_focus, "IdeaVariant.standardization_focus")
        _require_non_empty(self.ai_leverage, "IdeaVariant.ai_leverage")
        _require_non_empty(self.external_execution_needed, "IdeaVariant.external_execution_needed")
        _require_non_empty(self.rough_monetization_model, "IdeaVariant.rough_monetization_model")
        _require_non_empty(str(self.generation_mode.value), "IdeaVariant.generation_mode")
        if self.ai_metadata is not None and not isinstance(self.ai_metadata, dict):
            raise ValueError("IdeaVariant.ai_metadata must be a dict when provided")


@dataclass(frozen=True)
class Hypothesis:
    id: str
    idea_id: str
    critical_assumptions: List[str]
    most_fragile_assumption: str
    success_signals: List[str]
    kill_criteria: List[str]
    notes: str = ""

    def validate(self) -> None:
        _require_non_empty(self.id, "Hypothesis.id")
        _require_non_empty(self.idea_id, "Hypothesis.idea_id")
        _require_list(self.critical_assumptions, "Hypothesis.critical_assumptions")
        if not self.critical_assumptions:
            raise ValueError("Hypothesis.critical_assumptions must be non-empty")
        _require_non_empty(self.most_fragile_assumption, "Hypothesis.most_fragile_assumption")
        _require_list(self.success_signals, "Hypothesis.success_signals")
        _require_list(self.kill_criteria, "Hypothesis.kill_criteria")


@dataclass(frozen=True)
class Experiment:
    id: str
    idea_id: str
    hypothesis_id: Optional[str]
    cheapest_next_test: str
    plan_7d: str
    plan_14d: str
    success_metrics: Dict[str, Any] = field(default_factory=dict)
    failure_metrics: Dict[str, Any] = field(default_factory=dict)
    status: str = "planned"
    results_summary: str = ""
    created_at: str = field(default_factory=_iso_utc_now_seconds)
    updated_at: str = field(default_factory=_iso_utc_now_seconds)

    def validate(self) -> None:
        _require_non_empty(self.id, "Experiment.id")
        _require_non_empty(self.idea_id, "Experiment.idea_id")
        _require_non_empty(self.cheapest_next_test, "Experiment.cheapest_next_test")
        _require_non_empty(self.plan_7d, "Experiment.plan_7d")
        _require_non_empty(self.plan_14d, "Experiment.plan_14d")
        _require_non_empty(self.status, "Experiment.status")
        if not isinstance(self.success_metrics, dict) or not isinstance(self.failure_metrics, dict):
            raise ValueError("Experiment.success_metrics/failure_metrics must be dict")


@dataclass(frozen=True)
class Evidence:
    id: str
    experiment_id: str
    type: str
    content: str
    timestamp: str
    source: str

    def validate(self) -> None:
        _require_non_empty(self.id, "Evidence.id")
        _require_non_empty(self.experiment_id, "Evidence.experiment_id")
        _require_non_empty(self.type, "Evidence.type")
        _require_non_empty(self.content, "Evidence.content")
        _require_non_empty(self.timestamp, "Evidence.timestamp")
        _require_non_empty(self.source, "Evidence.source")


@dataclass(frozen=True)
class CouncilDecision:
    id: str
    idea_id: str
    skeptic_kill_scenarios: List[str]
    assumption_auditor_least_proven: str
    pattern_matcher_similarity: List[str]
    final_recommendation: str
    suspiciously_clean: bool = False
    notes: str = ""
    created_at: str = field(default_factory=_iso_utc_now_seconds)

    def validate(self) -> None:
        _require_non_empty(self.id, "CouncilDecision.id")
        _require_non_empty(self.idea_id, "CouncilDecision.idea_id")
        _require_list(self.skeptic_kill_scenarios, "CouncilDecision.skeptic_kill_scenarios")
        _require_non_empty(
            self.assumption_auditor_least_proven, "CouncilDecision.assumption_auditor_least_proven"
        )
        _require_list(self.pattern_matcher_similarity, "CouncilDecision.pattern_matcher_similarity")
        _require_non_empty(self.final_recommendation, "CouncilDecision.final_recommendation")
        if not isinstance(self.suspiciously_clean, bool):
            raise ValueError("CouncilDecision.suspiciously_clean must be bool")


@dataclass(frozen=True)
class PortfolioState:
    id: str
    opportunity_id: str
    state: PortfolioStateEnum
    last_transition_at: str = field(default_factory=_iso_utc_now_seconds)
    reason: str = ""
    linked_council_decision_id: Optional[str] = None
    linked_kill_reason_id: Optional[str] = None

    def validate(self) -> None:
        _require_non_empty(self.id, "PortfolioState.id")
        _require_non_empty(self.opportunity_id, "PortfolioState.opportunity_id")
        _require_non_empty(str(self.state.value), "PortfolioState.state")
        _require_non_empty(self.last_transition_at, "PortfolioState.last_transition_at")


@dataclass(frozen=True)
class KillReason:
    id: str
    idea_id: str
    kill_date: str
    failed_checks: List[str]
    matched_anti_patterns: List[str]
    summary: str
    looked_attractive_because: str
    notes: str = ""

    def validate(self) -> None:
        _require_non_empty(self.id, "KillReason.id")
        _require_non_empty(self.idea_id, "KillReason.idea_id")
        _require_non_empty(self.kill_date, "KillReason.kill_date")
        _require_list(self.failed_checks, "KillReason.failed_checks")
        _require_list(self.matched_anti_patterns, "KillReason.matched_anti_patterns")
        _require_non_empty(self.summary, "KillReason.summary")
        _require_non_empty(self.looked_attractive_because, "KillReason.looked_attractive_because")


@dataclass(frozen=True)
class FounderReviewDecision:
    id: str
    opportunity_id: str
    decision: FounderReviewDecisionEnum
    reason: str
    selected_next_experiment_or_action: str
    timestamp: str = field(default_factory=_iso_utc_now_seconds)
    portfolio_updated: bool = False
    review_id: Optional[str] = None
    linked_signal_ids: List[str] = field(default_factory=list)
    readiness_report_id: Optional[str] = None
    weekly_review_id: Optional[str] = None
    council_decision_ids: List[str] = field(default_factory=list)
    hypothesis_ids: List[str] = field(default_factory=list)
    experiment_ids: List[str] = field(default_factory=list)
    linked_kill_reason_id: Optional[str] = None

    def validate(self) -> None:
        _require_non_empty(self.id, "FounderReviewDecision.id")
        _require_non_empty(self.opportunity_id, "FounderReviewDecision.opportunity_id")
        _require_non_empty(str(self.decision.value), "FounderReviewDecision.decision")
        _require_non_empty(self.reason, "FounderReviewDecision.reason")
        _require_non_empty(
            self.selected_next_experiment_or_action,
            "FounderReviewDecision.selected_next_experiment_or_action",
        )
        _require_non_empty(self.timestamp, "FounderReviewDecision.timestamp")
        if not isinstance(self.portfolio_updated, bool):
            raise ValueError("FounderReviewDecision.portfolio_updated must be bool")
        _require_list(self.linked_signal_ids, "FounderReviewDecision.linked_signal_ids")
        _require_list(self.council_decision_ids, "FounderReviewDecision.council_decision_ids")
        _require_list(self.hypothesis_ids, "FounderReviewDecision.hypothesis_ids")
        _require_list(self.experiment_ids, "FounderReviewDecision.experiment_ids")
        if self.decision == FounderReviewDecisionEnum.Killed:
            _require_non_empty(self.linked_kill_reason_id, "FounderReviewDecision.linked_kill_reason_id")


MODEL_KIND = {
    Signal: "signals",
    OpportunityCard: "opportunities",
    IdeaVariant: "ideas",
    Hypothesis: "hypotheses",
    Experiment: "experiments",
    Evidence: "evidence",
    CouncilDecision: "council",
    PortfolioState: "portfolio",
    KillReason: "kills",
    FounderReviewDecision: "founder_reviews",
}


def model_to_dict(model: Any) -> Dict[str, Any]:
    """
    Convert a dataclass model into a JSON-serializable dict.
    Enums are stored by value.
    """
    data = asdict(model)
    for k, v in list(data.items()):
        if isinstance(v, Enum):
            data[k] = v.value
    return data


def _enum_from_value(enum_cls: Any, value: Any) -> Any:
    try:
        return enum_cls(value)
    except Exception as e:
        raise ValueError(f"Invalid value for {enum_cls.__name__}: {value!r}") from e


def model_from_dict(model_cls: Any, data: Dict[str, Any]) -> Any:
    """
    Build a model instance from dict and run minimal validation.
    """
    if model_cls is Signal:
        obj = Signal(
            **{
                **data,
                "status": _enum_from_value(SignalStatus, data.get("status")),
            }
        )
    elif model_cls is IdeaVariant:
        obj = IdeaVariant(
            **{
                **data,
                "status": _enum_from_value(IdeaScreenStatus, data.get("status", "candidate")),
                "generation_mode": _enum_from_value(
                    IdeationGenerationMode,
                    data.get("generation_mode", IdeationGenerationMode.heuristic_baseline.value),
                ),
            }
        )
    elif model_cls is PortfolioState:
        obj = PortfolioState(
            **{
                **data,
                "state": _enum_from_value(PortfolioStateEnum, data.get("state")),
            }
        )
    elif model_cls is FounderReviewDecision:
        obj = FounderReviewDecision(
            **{
                **data,
                "decision": _enum_from_value(FounderReviewDecisionEnum, data.get("decision")),
            }
        )
    else:
        obj = model_cls(**data)

    obj.validate()
    return obj

