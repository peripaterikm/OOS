from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List

from .ai_contracts import AI_METADATA_REQUIRED_FIELDS, AIStageStatus, PromptIdentity, build_ai_metadata
from .models import IdeationGenerationMode
from .opportunity_framing import OpportunityCard


PATTERN_GUIDED_IDEATION_PROMPT = PromptIdentity(
    prompt_name="pattern_guided_ideation",
    prompt_version="pattern_guided_ideation_v1",
)
PATTERN_GUIDED_IDEATION_MODEL_ID = "static_pattern_guided_ideation_provider"
MIN_IDEAS_PER_OPPORTUNITY = 3
MAX_IDEAS_PER_OPPORTUNITY = 5
MIN_DISTINCT_PATTERNS = 2


@dataclass(frozen=True)
class ProductPattern:
    pattern_id: str
    name: str
    description: str

    def validate(self) -> None:
        for field_name in ("pattern_id", "name", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

    def to_dict(self) -> Dict[str, str]:
        self.validate()
        return asdict(self)


PRODUCT_PATTERNS = [
    ProductPattern(
        pattern_id="saas_tool",
        name="SaaS / tool",
        description="Self-serve or team software that standardizes a recurring workflow.",
    ),
    ProductPattern(
        pattern_id="service_assisted_workflow",
        name="service-assisted workflow",
        description="Software plus constrained human/service assistance for hard edge cases.",
    ),
    ProductPattern(
        pattern_id="data_product",
        name="data product",
        description="Packaged data, benchmark, feed, or insight product derived from repeated signals.",
    ),
    ProductPattern(
        pattern_id="marketplace_brokered_workflow",
        name="marketplace / brokered workflow",
        description="Brokered workflow that matches supply, demand, or specialist capacity.",
    ),
    ProductPattern(
        pattern_id="internal_automation_product",
        name="internal automation product",
        description="Internal-facing automation for repeatable operational work.",
    ),
    ProductPattern(
        pattern_id="audit_risk_radar",
        name="audit / risk radar",
        description="Monitoring, review, or risk surfacing product for recurring failure modes.",
    ),
    ProductPattern(
        pattern_id="expert_in_the_loop_workflow",
        name="expert-in-the-loop workflow",
        description="Structured workflow where expert judgment is routed only to high-value moments.",
    ),
]
PRODUCT_PATTERN_BY_NAME = {pattern.name: pattern for pattern in PRODUCT_PATTERNS}
PRODUCT_PATTERN_BY_ID = {pattern.pattern_id: pattern for pattern in PRODUCT_PATTERNS}


class PatternGuidedIdeationProvider:
    def generate(self, *, opportunities: List[OpportunityCard], product_patterns: List[ProductPattern]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class StaticPatternGuidedIdeationProvider(PatternGuidedIdeationProvider):
    payload: Dict[str, Any]

    def generate(self, *, opportunities: List[OpportunityCard], product_patterns: List[ProductPattern]) -> Dict[str, Any]:
        return self.payload


@dataclass(frozen=True)
class PatternGuidedIdea:
    idea_id: str
    idea_title: str
    target_user: str
    pain_addressed: str
    product_concept: str
    wedge: str
    why_now: str
    business_model_options: List[str]
    first_experiment: str
    key_assumptions: List[str]
    risks: List[str]
    selected_product_pattern: str
    linked_opportunity_id: str
    linked_signal_ids: List[str]
    generation_mode: str
    confidence: float
    ai_metadata: Dict[str, Any]
    fallback_used: bool = False
    failure_reason: str = ""

    def validate(self, *, valid_opportunity_ids: Iterable[str], expected_signal_ids_by_opportunity: Dict[str, List[str]]) -> None:
        valid_opportunity_id_set = set(valid_opportunity_ids)
        for field_name in (
            "idea_id",
            "idea_title",
            "target_user",
            "pain_addressed",
            "product_concept",
            "wedge",
            "why_now",
            "first_experiment",
            "selected_product_pattern",
            "linked_opportunity_id",
            "generation_mode",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.selected_product_pattern not in PRODUCT_PATTERN_BY_NAME:
            raise ValueError("selected_product_pattern must be from the product pattern library")
        if self.linked_opportunity_id not in valid_opportunity_id_set:
            raise ValueError(f"linked_opportunity_id contains unknown ID: {self.linked_opportunity_id}")
        expected_signal_ids = expected_signal_ids_by_opportunity[self.linked_opportunity_id]
        if self.linked_signal_ids != expected_signal_ids:
            raise ValueError("linked_signal_ids must preserve the opportunity linked signal IDs")
        if not isinstance(self.confidence, (int, float)) or not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be a number between 0 and 1")
        for field_name in ("business_model_options", "key_assumptions", "risks"):
            value = getattr(self, field_name)
            if not isinstance(value, list) or not value or any(not str(item).strip() for item in value):
                raise ValueError(f"{field_name} must contain non-empty strings")
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["confidence"] = float(data["confidence"])
        return data


@dataclass(frozen=True)
class PatternGuidedIdeationResult:
    ideas: List[PatternGuidedIdea]
    source_opportunity_ids: List[str]
    rejected_record_errors: List[str]
    low_diversity_warning: bool
    fallback_used: bool
    stage_status: str
    failure_reason: str
    ai_metadata: Dict[str, Any]

    def validate(self, *, opportunities: List[OpportunityCard]) -> None:
        if self.stage_status not in {status.value for status in AIStageStatus}:
            raise ValueError("stage_status must be success, failed, or degraded")
        if not isinstance(self.low_diversity_warning, bool):
            raise ValueError("low_diversity_warning must be a bool")
        if not isinstance(self.fallback_used, bool):
            raise ValueError("fallback_used must be a bool")
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")
        expected_signal_ids_by_opportunity = {
            opportunity.opportunity_id: list(opportunity.linked_signal_ids)
            for opportunity in opportunities
        }
        for idea in self.ideas:
            idea.validate(
                valid_opportunity_ids=self.source_opportunity_ids,
                expected_signal_ids_by_opportunity=expected_signal_ids_by_opportunity,
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ideas": [idea.to_dict() for idea in self.ideas],
            "source_opportunity_ids": self.source_opportunity_ids,
            "rejected_record_errors": self.rejected_record_errors,
            "low_diversity_warning": self.low_diversity_warning,
            "fallback_used": self.fallback_used,
            "stage_status": self.stage_status,
            "failure_reason": self.failure_reason,
            "ai_metadata": self.ai_metadata,
        }


def _opportunity_payload(opportunities: Iterable[OpportunityCard]) -> List[Dict[str, Any]]:
    return [opportunity.to_dict() for opportunity in opportunities]


def _metadata_for(
    *,
    opportunities: List[OpportunityCard],
    linked_input_ids: List[str],
    generation_mode: str,
    fallback_used: bool,
    stage_confidence: float,
    stage_status: AIStageStatus,
    failure_reason: str = "",
) -> Dict[str, Any]:
    return build_ai_metadata(
        prompt=PATTERN_GUIDED_IDEATION_PROMPT,
        model_id=PATTERN_GUIDED_IDEATION_MODEL_ID,
        input_payload={
            "opportunities": _opportunity_payload(opportunities),
            "product_patterns": [pattern.to_dict() for pattern in PRODUCT_PATTERNS],
        },
        generation_mode=generation_mode,
        linked_input_ids=linked_input_ids,
        fallback_used=fallback_used,
        stage_confidence=stage_confidence,
        stage_status=stage_status,
        failure_reason=failure_reason,
        fallback_recommendation="Use heuristic fallback ideas only for continuity and comparison.",
        degraded_mode=fallback_used or stage_status == AIStageStatus.degraded,
    ).to_dict()


def _as_string_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("value must be a list")
    return [str(value).strip() for value in raw if str(value).strip()]


def _coerce_idea(
    raw: Dict[str, Any],
    *,
    opportunities: List[OpportunityCard],
    opportunity_by_id: Dict[str, OpportunityCard],
    result_metadata: Dict[str, Any],
) -> PatternGuidedIdea:
    linked_opportunity_id = str(raw.get("linked_opportunity_id") or "").strip()
    opportunity = opportunity_by_id.get(linked_opportunity_id)
    linked_signal_ids = _as_string_list(raw.get("linked_signal_ids"))
    confidence = float(raw.get("confidence"))
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be a number between 0 and 1")
    idea = PatternGuidedIdea(
        idea_id=str(raw.get("idea_id") or "").strip(),
        idea_title=str(raw.get("idea_title") or "").strip(),
        target_user=str(raw.get("target_user") or "").strip(),
        pain_addressed=str(raw.get("pain_addressed") or "").strip(),
        product_concept=str(raw.get("product_concept") or "").strip(),
        wedge=str(raw.get("wedge") or "").strip(),
        why_now=str(raw.get("why_now") or "").strip(),
        business_model_options=_as_string_list(raw.get("business_model_options")),
        first_experiment=str(raw.get("first_experiment") or "").strip(),
        key_assumptions=_as_string_list(raw.get("key_assumptions")),
        risks=_as_string_list(raw.get("risks")),
        selected_product_pattern=str(raw.get("selected_product_pattern") or "").strip(),
        linked_opportunity_id=linked_opportunity_id,
        linked_signal_ids=linked_signal_ids,
        generation_mode=IdeationGenerationMode.llm_assisted.value,
        confidence=confidence,
        ai_metadata=result_metadata,
        fallback_used=False,
    )
    if opportunity is None:
        raise ValueError(f"linked_opportunity_id contains unknown ID: {linked_opportunity_id}")
    idea.validate(
        valid_opportunity_ids=[item.opportunity_id for item in opportunities],
        expected_signal_ids_by_opportunity={item.opportunity_id: list(item.linked_signal_ids) for item in opportunities},
    )
    return idea


def _fallback_idea(
    *,
    opportunity: OpportunityCard,
    pattern: ProductPattern,
    index: int,
    metadata: Dict[str, Any],
    reason: str,
) -> PatternGuidedIdea:
    return PatternGuidedIdea(
        idea_id=f"fallback_{opportunity.opportunity_id}_{pattern.pattern_id}_{index}",
        idea_title=f"{pattern.name} fallback for {opportunity.title}",
        target_user=opportunity.target_user,
        pain_addressed=opportunity.pain,
        product_concept=f"{pattern.name} concept for: {opportunity.possible_wedge}",
        wedge=opportunity.possible_wedge or "Use a narrow workflow wedge from the linked opportunity.",
        why_now=opportunity.urgency or opportunity.why_it_matters,
        business_model_options=[opportunity.monetization_hypothesis or "subscription"],
        first_experiment="Interview 5 target users and test whether the wedge is urgent enough to pay for.",
        key_assumptions=[assumption.statement for assumption in opportunity.assumptions[:2]] or [
            "The linked opportunity represents a recurring pain worth testing."
        ],
        risks=opportunity.risks or ["Fallback idea may be too generic until tested with users."],
        selected_product_pattern=pattern.name,
        linked_opportunity_id=opportunity.opportunity_id,
        linked_signal_ids=list(opportunity.linked_signal_ids),
        generation_mode=IdeationGenerationMode.heuristic_fallback_after_llm_failure.value,
        confidence=0.35,
        ai_metadata=metadata,
        fallback_used=True,
        failure_reason=reason,
    )


def _ensure_opportunity_coverage_and_diversity(
    *,
    opportunities: List[OpportunityCard],
    ideas: List[PatternGuidedIdea],
    fallback_metadata: Dict[str, Any],
    rejected_record_errors: List[str],
) -> tuple[List[PatternGuidedIdea], bool, bool]:
    final_ideas = list(ideas)
    low_diversity_warning = False
    fallback_used = False
    ideas_by_opportunity: Dict[str, List[PatternGuidedIdea]] = {
        opportunity.opportunity_id: [idea for idea in final_ideas if idea.linked_opportunity_id == opportunity.opportunity_id]
        for opportunity in opportunities
    }
    fallback_patterns = PRODUCT_PATTERNS
    for opportunity in opportunities:
        opportunity_ideas = ideas_by_opportunity[opportunity.opportunity_id]
        distinct_patterns = {idea.selected_product_pattern for idea in opportunity_ideas}
        if len(distinct_patterns) < MIN_DISTINCT_PATTERNS:
            low_diversity_warning = True
        while len(opportunity_ideas) < MIN_IDEAS_PER_OPPORTUNITY or len(distinct_patterns) < MIN_DISTINCT_PATTERNS:
            if len(opportunity_ideas) >= MAX_IDEAS_PER_OPPORTUNITY:
                break
            pattern = next(pattern for pattern in fallback_patterns if pattern.name not in distinct_patterns)
            reason = "low_diversity warning or too few valid provider ideas"
            fallback = _fallback_idea(
                opportunity=opportunity,
                pattern=pattern,
                index=len(opportunity_ideas) + 1,
                metadata=fallback_metadata,
                reason=reason,
            )
            final_ideas.append(fallback)
            opportunity_ideas.append(fallback)
            distinct_patterns.add(pattern.name)
            fallback_used = True
        if len(opportunity_ideas) > MAX_IDEAS_PER_OPPORTUNITY:
            rejected_record_errors.append(
                f"opportunity {opportunity.opportunity_id}: more than {MAX_IDEAS_PER_OPPORTUNITY} ideas were produced"
            )
            opportunity_ideas[:] = opportunity_ideas[:MAX_IDEAS_PER_OPPORTUNITY]
    return final_ideas, low_diversity_warning, fallback_used


def generate_pattern_guided_ideas(
    *,
    opportunities: List[OpportunityCard],
    provider: PatternGuidedIdeationProvider,
) -> PatternGuidedIdeationResult:
    source_opportunity_ids = [opportunity.opportunity_id for opportunity in opportunities]
    result_metadata = _metadata_for(
        opportunities=opportunities,
        linked_input_ids=source_opportunity_ids,
        generation_mode=IdeationGenerationMode.llm_assisted.value,
        fallback_used=False,
        stage_confidence=1.0,
        stage_status=AIStageStatus.success,
    )
    fallback_metadata = _metadata_for(
        opportunities=opportunities,
        linked_input_ids=source_opportunity_ids,
        generation_mode=IdeationGenerationMode.heuristic_fallback_after_llm_failure.value,
        fallback_used=True,
        stage_confidence=0.35,
        stage_status=AIStageStatus.degraded,
        failure_reason="fallback candidate generation used",
    )
    rejected_record_errors: List[str] = []
    ideas: List[PatternGuidedIdea] = []
    try:
        raw_payload = provider.generate(opportunities=opportunities, product_patterns=PRODUCT_PATTERNS)
        if not isinstance(raw_payload, dict):
            raise ValueError("provider payload must be an object")
        raw_ideas = raw_payload.get("ideas", [])
        if not isinstance(raw_ideas, list):
            raise ValueError("provider ideas must be a list")
    except Exception as exc:
        raw_ideas = []
        rejected_record_errors.append(f"provider: {exc}")

    opportunity_by_id = {opportunity.opportunity_id: opportunity for opportunity in opportunities}
    for index, raw_idea in enumerate(raw_ideas):
        try:
            if not isinstance(raw_idea, dict):
                raise ValueError("idea item must be an object")
            ideas.append(
                _coerce_idea(
                    raw_idea,
                    opportunities=opportunities,
                    opportunity_by_id=opportunity_by_id,
                    result_metadata=result_metadata,
                )
            )
        except Exception as exc:
            rejected_record_errors.append(f"ideas[{index}]: {exc}")

    ideas, low_diversity_warning, fallback_used_for_diversity = _ensure_opportunity_coverage_and_diversity(
        opportunities=opportunities,
        ideas=ideas,
        fallback_metadata=fallback_metadata,
        rejected_record_errors=rejected_record_errors,
    )
    fallback_used = bool(rejected_record_errors) or fallback_used_for_diversity
    stage_status = AIStageStatus.degraded if fallback_used or low_diversity_warning else AIStageStatus.success
    failure_reason = "; ".join(rejected_record_errors + (["low_diversity warning"] if low_diversity_warning else []))
    result_metadata = _metadata_for(
        opportunities=opportunities,
        linked_input_ids=source_opportunity_ids,
        generation_mode=IdeationGenerationMode.llm_assisted.value,
        fallback_used=fallback_used,
        stage_confidence=min([idea.confidence for idea in ideas] + [1.0]),
        stage_status=stage_status,
        failure_reason=failure_reason,
    )
    final_ideas = [
        PatternGuidedIdea(
            **{
                **idea.to_dict(),
                "ai_metadata": fallback_metadata if idea.fallback_used else result_metadata,
            }
        )
        for idea in ideas
    ]
    result = PatternGuidedIdeationResult(
        ideas=final_ideas,
        source_opportunity_ids=source_opportunity_ids,
        rejected_record_errors=rejected_record_errors,
        low_diversity_warning=low_diversity_warning,
        fallback_used=fallback_used,
        stage_status=stage_status.value,
        failure_reason=failure_reason,
        ai_metadata=result_metadata,
    )
    result.validate(opportunities=opportunities)
    return result
