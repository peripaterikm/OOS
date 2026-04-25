from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .models import IdeaVariant
from .pattern_guided_ideation import PatternGuidedIdea


IDEATION_MODES = {"heuristic_baseline", "pattern_guided", "llm_constrained", "llm_assisted"}
IDEA_RECOMMENDATIONS = {"candidate_for_council_review", "park_low_priority", "auto_park"}

GENERICNESS_TERMS = (
    "generic dashboard",
    "dashboard",
    "generic assistant",
    "assistant for everyone",
    "vague saas",
    "better saas",
)


@dataclass(frozen=True)
class IdeaEvaluationScore:
    idea_id: str
    mode: str
    schema_valid: bool
    traceability_valid: bool
    relevance_to_pain: int
    novelty: int
    commercial_usefulness: int
    founder_fit: int
    testability: int
    automation_potential: int
    hallucination_risk: int
    genericness_penalty: int
    total_score: int
    recommendation: str
    explanation: str
    linked_signal_ids: List[str]
    linked_opportunity_id: str
    validation_errors: List[str]

    def validate(self) -> None:
        if not self.idea_id.strip():
            raise ValueError("idea_id must be non-empty")
        if self.mode not in IDEATION_MODES:
            raise ValueError(f"mode must be one of {sorted(IDEATION_MODES)}")
        if self.recommendation not in IDEA_RECOMMENDATIONS:
            raise ValueError("recommendation has an unknown value")
        for field_name in (
            "relevance_to_pain",
            "novelty",
            "commercial_usefulness",
            "founder_fit",
            "testability",
            "automation_potential",
            "hallucination_risk",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or value < 1 or value > 3:
                raise ValueError(f"{field_name} must be an integer from 1 to 3")
        if self.genericness_penalty not in {0, -1, -2}:
            raise ValueError("genericness_penalty must be 0, -1, or -2")
        if not self.explanation.strip():
            raise ValueError("explanation must be non-empty")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class IdeationModeSummary:
    mode: str
    idea_count: int
    gate_pass_count: int
    candidate_for_council_review_count: int
    park_low_priority_count: int
    auto_park_count: int
    average_score: float
    diversity_summary: Dict[str, Any]
    recommendation: str
    explanation: str

    def validate(self) -> None:
        if self.mode not in IDEATION_MODES:
            raise ValueError(f"mode must be one of {sorted(IDEATION_MODES)}")
        if not self.recommendation.strip():
            raise ValueError("recommendation must be non-empty")
        if not self.explanation.strip():
            raise ValueError("explanation must be non-empty")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class IdeationModeRecommendation:
    preferred_mode: str
    fallback_mode: str
    explanation: str

    def validate(self) -> None:
        if self.preferred_mode not in IDEATION_MODES:
            raise ValueError(f"preferred_mode must be one of {sorted(IDEATION_MODES)}")
        if self.fallback_mode not in IDEATION_MODES:
            raise ValueError(f"fallback_mode must be one of {sorted(IDEATION_MODES)}")
        if not self.explanation.strip():
            raise ValueError("explanation must be non-empty")

    def to_dict(self) -> Dict[str, str]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class IdeationModeComparisonResult:
    scores: List[IdeaEvaluationScore]
    mode_summaries: List[IdeationModeSummary]
    recommendation: IdeationModeRecommendation
    rejected_record_errors: List[str]

    def validate(self) -> None:
        for score in self.scores:
            score.validate()
        for summary in self.mode_summaries:
            summary.validate()
        self.recommendation.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "scores": [score.to_dict() for score in self.scores],
            "mode_summaries": [summary.to_dict() for summary in self.mode_summaries],
            "recommendation": self.recommendation.to_dict(),
            "rejected_record_errors": list(self.rejected_record_errors),
        }


def compute_weighted_score(
    *,
    relevance_to_pain: int,
    novelty: int,
    commercial_usefulness: int,
    founder_fit: int,
    testability: int,
    automation_potential: int,
    hallucination_risk: int,
    genericness_penalty: int,
) -> int:
    return (
        2 * relevance_to_pain
        + novelty
        + 2 * commercial_usefulness
        + 2 * founder_fit
        + testability
        + automation_potential
        - hallucination_risk
        + genericness_penalty
    )


def classify_score(total_score: int, *, gates_pass: bool = True) -> str:
    if not gates_pass:
        return "auto_park"
    if total_score >= 12:
        return "candidate_for_council_review"
    if total_score >= 8:
        return "park_low_priority"
    return "auto_park"


def genericness_penalty_for_text(text: str) -> int:
    normalized = " ".join(text.lower().split())
    hit_count = sum(1 for term in GENERICNESS_TERMS if term in normalized)
    if hit_count >= 2:
        return -2
    if hit_count == 1:
        return -1
    return 0


def compare_ideation_modes(
    *,
    ideas_by_mode: Mapping[str, Iterable[Any]],
    valid_opportunity_ids: Optional[Iterable[str]] = None,
    expected_signal_ids_by_opportunity: Optional[Mapping[str, Iterable[str]]] = None,
    criterion_scores_by_idea_id: Optional[Mapping[str, Mapping[str, int]]] = None,
) -> IdeationModeComparisonResult:
    valid_opportunities = set(valid_opportunity_ids or [])
    expected_signal_ids = {
        opportunity_id: {str(signal_id) for signal_id in signal_ids}
        for opportunity_id, signal_ids in (expected_signal_ids_by_opportunity or {}).items()
    }
    criteria_by_id = criterion_scores_by_idea_id or {}
    scores: List[IdeaEvaluationScore] = []
    rejected_record_errors: List[str] = []

    for mode, ideas in ideas_by_mode.items():
        if mode not in IDEATION_MODES:
            rejected_record_errors.append(f"{mode}: unknown ideation mode")
            continue
        for index, idea in enumerate(ideas):
            try:
                score = evaluate_idea(
                    idea,
                    mode=mode,
                    valid_opportunity_ids=valid_opportunities,
                    expected_signal_ids_by_opportunity=expected_signal_ids,
                    criterion_scores=criteria_by_id.get(_idea_id(idea), {}),
                )
            except Exception as exc:
                rejected_record_errors.append(f"{mode}[{index}]: {exc}")
                score = fallback_score_for_invalid_idea(idea, mode=mode, reason=str(exc))
            scores.append(score)

    mode_summaries = [_summarize_mode(mode, [score for score in scores if score.mode == mode]) for mode in ideas_by_mode]
    recommendation = _recommend_mode(mode_summaries)
    result = IdeationModeComparisonResult(
        scores=scores,
        mode_summaries=mode_summaries,
        recommendation=recommendation,
        rejected_record_errors=rejected_record_errors,
    )
    result.validate()
    return result


def evaluate_idea(
    idea: Any,
    *,
    mode: str,
    valid_opportunity_ids: set[str],
    expected_signal_ids_by_opportunity: Mapping[str, set[str]],
    criterion_scores: Mapping[str, int],
) -> IdeaEvaluationScore:
    idea_id = _idea_id(idea)
    linked_opportunity_id = _linked_opportunity_id(idea)
    linked_signal_ids = _linked_signal_ids(idea)
    text = _idea_text(idea)
    validation_errors: List[str] = []

    schema_valid = _schema_is_valid(idea, validation_errors)
    traceability_valid = _traceability_is_valid(
        linked_opportunity_id=linked_opportunity_id,
        linked_signal_ids=linked_signal_ids,
        valid_opportunity_ids=valid_opportunity_ids,
        expected_signal_ids_by_opportunity=expected_signal_ids_by_opportunity,
        validation_errors=validation_errors,
    )
    criteria = _criteria_for(criterion_scores, text=text)
    total_score = compute_weighted_score(**criteria)
    gates_pass = schema_valid and traceability_valid
    recommendation = classify_score(total_score, gates_pass=gates_pass)
    explanation = _score_explanation(recommendation, total_score, validation_errors)
    score = IdeaEvaluationScore(
        idea_id=idea_id,
        mode=mode,
        schema_valid=schema_valid,
        traceability_valid=traceability_valid,
        relevance_to_pain=criteria["relevance_to_pain"],
        novelty=criteria["novelty"],
        commercial_usefulness=criteria["commercial_usefulness"],
        founder_fit=criteria["founder_fit"],
        testability=criteria["testability"],
        automation_potential=criteria["automation_potential"],
        hallucination_risk=criteria["hallucination_risk"],
        genericness_penalty=criteria["genericness_penalty"],
        total_score=total_score if gates_pass else min(total_score, 7),
        recommendation=recommendation,
        explanation=explanation,
        linked_signal_ids=linked_signal_ids,
        linked_opportunity_id=linked_opportunity_id,
        validation_errors=validation_errors,
    )
    score.validate()
    return score


def fallback_score_for_invalid_idea(idea: Any, *, mode: str, reason: str) -> IdeaEvaluationScore:
    idea_id = _safe_idea_id(idea)
    return IdeaEvaluationScore(
        idea_id=idea_id,
        mode=mode,
        schema_valid=False,
        traceability_valid=False,
        relevance_to_pain=1,
        novelty=1,
        commercial_usefulness=1,
        founder_fit=1,
        testability=1,
        automation_potential=1,
        hallucination_risk=3,
        genericness_penalty=-2,
        total_score=3,
        recommendation="auto_park",
        explanation=f"Invalid idea record was auto-parked: {reason}",
        linked_signal_ids=[],
        linked_opportunity_id="",
        validation_errors=[reason],
    )


def _schema_is_valid(idea: Any, validation_errors: List[str]) -> bool:
    required_values = [_idea_id(idea), _idea_title(idea), _target_user(idea), _pain(idea), _concept(idea)]
    if any(not value.strip() for value in required_values):
        validation_errors.append("schema validity failed: required idea fields are missing")
        return False
    if isinstance(idea, PatternGuidedIdea):
        for value in (idea.wedge, idea.first_experiment, idea.selected_product_pattern):
            if not str(value).strip():
                validation_errors.append("schema validity failed: pattern-guided fields are missing")
                return False
    return True


def _traceability_is_valid(
    *,
    linked_opportunity_id: str,
    linked_signal_ids: List[str],
    valid_opportunity_ids: set[str],
    expected_signal_ids_by_opportunity: Mapping[str, set[str]],
    validation_errors: List[str],
) -> bool:
    valid = True
    if not linked_opportunity_id.strip():
        validation_errors.append("traceability failed: linked opportunity ID is missing")
        valid = False
    elif valid_opportunity_ids and linked_opportunity_id not in valid_opportunity_ids:
        validation_errors.append(f"traceability failed: unknown opportunity ID {linked_opportunity_id}")
        valid = False
    if not linked_signal_ids:
        validation_errors.append("traceability failed: linked signal IDs are missing")
        valid = False
    expected = expected_signal_ids_by_opportunity.get(linked_opportunity_id)
    if expected is not None and not set(linked_signal_ids).issubset(expected):
        validation_errors.append("traceability failed: linked signal IDs are not in the expected source set")
        valid = False
    return valid


def _criteria_for(raw: Mapping[str, int], *, text: str) -> Dict[str, int]:
    criteria = {
        "relevance_to_pain": _score_value(raw.get("relevance_to_pain", 2)),
        "novelty": _score_value(raw.get("novelty", 2)),
        "commercial_usefulness": _score_value(raw.get("commercial_usefulness", 2)),
        "founder_fit": _score_value(raw.get("founder_fit", 2)),
        "testability": _score_value(raw.get("testability", 2)),
        "automation_potential": _score_value(raw.get("automation_potential", 2)),
        "hallucination_risk": _score_value(raw.get("hallucination_risk", 2)),
        "genericness_penalty": raw.get("genericness_penalty", genericness_penalty_for_text(text)),
    }
    if criteria["genericness_penalty"] not in {0, -1, -2}:
        raise ValueError("genericness_penalty must be 0, -1, or -2")
    return criteria


def _score_value(value: int) -> int:
    if not isinstance(value, int) or value < 1 or value > 3:
        raise ValueError("criterion scores must be integers from 1 to 3")
    return value


def _summarize_mode(mode: str, scores: List[IdeaEvaluationScore]) -> IdeationModeSummary:
    candidate_count = sum(1 for score in scores if score.recommendation == "candidate_for_council_review")
    park_count = sum(1 for score in scores if score.recommendation == "park_low_priority")
    auto_park_count = sum(1 for score in scores if score.recommendation == "auto_park")
    gate_pass_count = sum(1 for score in scores if score.schema_valid and score.traceability_valid)
    average_score = float(mean([score.total_score for score in scores])) if scores else 0.0
    linked_patterns = _mode_patterns(scores)
    recommendation = "use_as_default_candidate_mode" if candidate_count and gate_pass_count == len(scores) else "use_as_fallback_or_control"
    if mode in {"llm_constrained", "llm_assisted"} and gate_pass_count < len(scores):
        recommendation = "fallback_to_pattern_guided_or_heuristic"
    return IdeationModeSummary(
        mode=mode,
        idea_count=len(scores),
        gate_pass_count=gate_pass_count,
        candidate_for_council_review_count=candidate_count,
        park_low_priority_count=park_count,
        auto_park_count=auto_park_count,
        average_score=round(average_score, 2),
        diversity_summary={
            "distinct_linked_opportunities": len({score.linked_opportunity_id for score in scores if score.linked_opportunity_id}),
            "distinct_signal_ids": len({signal_id for score in scores for signal_id in score.linked_signal_ids}),
            "distinct_patterns_or_shapes": linked_patterns,
        },
        recommendation=recommendation,
        explanation=f"{mode} produced {candidate_count} council candidates, {park_count} parked ideas, and {auto_park_count} auto-parked ideas.",
    )


def _recommend_mode(summaries: List[IdeationModeSummary]) -> IdeationModeRecommendation:
    if not summaries:
        return IdeationModeRecommendation(
            preferred_mode="heuristic_baseline",
            fallback_mode="heuristic_baseline",
            explanation="No ideas were available; keep heuristic baseline as a control until artifacts exist.",
        )
    ranked = sorted(
        summaries,
        key=lambda summary: (
            summary.gate_pass_count == summary.idea_count and summary.idea_count > 0,
            summary.average_score,
            len(summary.diversity_summary.get("distinct_patterns_or_shapes", [])),
        ),
        reverse=True,
    )
    preferred = ranked[0]
    fallback_mode = "pattern_guided" if preferred.mode in {"llm_constrained", "llm_assisted"} else "heuristic_baseline"
    if preferred.mode == "pattern_guided":
        explanation = "Pattern-guided mode is preferred because it combines gate-passing traceability with product-shape diversity."
    elif preferred.mode in {"llm_constrained", "llm_assisted"}:
        explanation = "LLM-constrained mode is preferred only while its schema and traceability gates pass; fall back if those gates fail."
    else:
        explanation = "Heuristic baseline is preferred only because other modes did not produce stronger gate-passing results."
    return IdeationModeRecommendation(
        preferred_mode=preferred.mode,
        fallback_mode=fallback_mode,
        explanation=explanation,
    )


def _mode_patterns(scores: List[IdeaEvaluationScore]) -> List[str]:
    patterns = []
    for score in scores:
        marker = score.idea_id.split("_")[0]
        if marker and marker not in patterns:
            patterns.append(marker)
    return patterns


def _score_explanation(recommendation: str, total_score: int, validation_errors: List[str]) -> str:
    if validation_errors:
        return f"{recommendation}: gates failed; {'; '.join(validation_errors)}"
    return f"{recommendation}: weighted score {total_score} using relevance, usefulness, founder fit, testability, automation, risk, and genericness."


def _idea_id(idea: Any) -> str:
    if isinstance(idea, PatternGuidedIdea):
        return idea.idea_id
    if isinstance(idea, IdeaVariant):
        return idea.id
    if isinstance(idea, Mapping):
        return str(idea.get("idea_id") or idea.get("id") or "").strip()
    return str(getattr(idea, "idea_id", getattr(idea, "id", ""))).strip()


def _safe_idea_id(idea: Any) -> str:
    return _idea_id(idea) or "invalid_idea"


def _linked_opportunity_id(idea: Any) -> str:
    if isinstance(idea, PatternGuidedIdea):
        return idea.linked_opportunity_id
    if isinstance(idea, IdeaVariant):
        return idea.opportunity_id
    if isinstance(idea, Mapping):
        return str(idea.get("linked_opportunity_id") or idea.get("opportunity_id") or "").strip()
    return str(getattr(idea, "linked_opportunity_id", getattr(idea, "opportunity_id", ""))).strip()


def _linked_signal_ids(idea: Any) -> List[str]:
    if isinstance(idea, PatternGuidedIdea):
        return list(idea.linked_signal_ids)
    if isinstance(idea, IdeaVariant):
        metadata = idea.ai_metadata or {}
        return [str(signal_id) for signal_id in metadata.get("linked_input_ids", []) if str(signal_id).strip()]
    if isinstance(idea, Mapping):
        raw = idea.get("linked_signal_ids") or idea.get("source_signal_ids") or []
        return [str(signal_id) for signal_id in raw if str(signal_id).strip()] if isinstance(raw, list) else []
    return list(getattr(idea, "linked_signal_ids", []))


def _idea_title(idea: Any) -> str:
    if isinstance(idea, PatternGuidedIdea):
        return idea.idea_title
    if isinstance(idea, IdeaVariant):
        return idea.short_concept
    if isinstance(idea, Mapping):
        return str(idea.get("idea_title") or idea.get("short_concept") or idea.get("title") or "").strip()
    return str(getattr(idea, "idea_title", getattr(idea, "short_concept", ""))).strip()


def _target_user(idea: Any) -> str:
    if isinstance(idea, PatternGuidedIdea):
        return idea.target_user
    if isinstance(idea, Mapping):
        return str(idea.get("target_user") or idea.get("icp") or "legacy target user").strip()
    return str(getattr(idea, "target_user", "legacy target user")).strip()


def _pain(idea: Any) -> str:
    if isinstance(idea, PatternGuidedIdea):
        return idea.pain_addressed
    if isinstance(idea, Mapping):
        return str(idea.get("pain_addressed") or idea.get("pain") or idea.get("short_concept") or "").strip()
    return str(getattr(idea, "pain_addressed", getattr(idea, "short_concept", ""))).strip()


def _concept(idea: Any) -> str:
    if isinstance(idea, PatternGuidedIdea):
        return idea.product_concept
    if isinstance(idea, IdeaVariant):
        return idea.short_concept
    if isinstance(idea, Mapping):
        return str(idea.get("product_concept") or idea.get("short_concept") or "").strip()
    return str(getattr(idea, "product_concept", getattr(idea, "short_concept", ""))).strip()


def _idea_text(idea: Any) -> str:
    if isinstance(idea, PatternGuidedIdea):
        parts = [
            idea.idea_title,
            idea.target_user,
            idea.pain_addressed,
            idea.product_concept,
            idea.wedge,
            idea.why_now,
            idea.first_experiment,
            " ".join(idea.business_model_options),
            " ".join(idea.key_assumptions),
            " ".join(idea.risks),
        ]
    elif isinstance(idea, IdeaVariant):
        parts = [
            idea.short_concept,
            idea.business_model,
            idea.standardization_focus,
            idea.ai_leverage,
            idea.external_execution_needed,
            idea.rough_monetization_model,
        ]
    elif isinstance(idea, Mapping):
        parts = [str(value) for value in idea.values()]
    else:
        parts = [str(idea)]
    return " ".join(parts)
