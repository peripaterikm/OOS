from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .ai_contracts import AI_METADATA_REQUIRED_FIELDS, AIStageStatus, PromptIdentity, build_ai_metadata
from .ideation_mode_comparison import IdeaEvaluationScore
from .models import IdeationGenerationMode
from .pattern_guided_ideation import PatternGuidedIdea


COUNCIL_CRITIQUE_PROMPT = PromptIdentity(
    prompt_name="isolated_ai_council_critique",
    prompt_version="isolated_ai_council_critique_v1",
)
COUNCIL_CRITIQUE_MODEL_ID = "static_isolated_council_provider"
COUNCIL_THRESHOLD = 12
STANDARD_MAX_IDEAS_PER_OPPORTUNITY = 3
RECOMMENDATIONS = {"kill", "park", "test now", "needs more evidence"}


@dataclass(frozen=True)
class CouncilRole:
    role_id: str
    name: str
    instruction: str

    def validate(self) -> None:
        for field_name in ("role_id", "name", "instruction"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

    def to_dict(self) -> Dict[str, str]:
        self.validate()
        return asdict(self)


COUNCIL_ROLES = [
    CouncilRole(
        role_id="skeptic",
        name="Skeptic",
        instruction="Search for ways the idea can die; do not merely balance pros and cons.",
    ),
    CouncilRole(
        role_id="market_reality_checker",
        name="Market Reality Checker",
        instruction="Check whether the buyer, urgency, market pull, and existing alternatives are believable.",
    ),
    CouncilRole(
        role_id="founder_bottleneck_checker",
        name="Founder Bottleneck Checker",
        instruction="Find founder-time-heavy, service-heavy, or expertise bottlenecks that block scale.",
    ),
    CouncilRole(
        role_id="commercialization_critic",
        name="Commercialization Critic",
        instruction="Critique pricing, buyer willingness, sales motion, and path to first revenue.",
    ),
    CouncilRole(
        role_id="genericness_detector",
        name="Genericness Detector",
        instruction="Flag ideas that are too generic for the specific source signals and opportunity context.",
    ),
]
COUNCIL_ROLE_BY_ID = {role.role_id: role for role in COUNCIL_ROLES}


class CouncilRoleProvider:
    def critique(self, *, role: CouncilRole, idea: Any) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class StaticCouncilRoleProvider(CouncilRoleProvider):
    payloads_by_role: Mapping[str, Dict[str, Any]]

    def critique(self, *, role: CouncilRole, idea: Any) -> Dict[str, Any]:
        if role.role_id not in self.payloads_by_role:
            raise KeyError(f"missing provider payload for role {role.role_id}")
        return dict(self.payloads_by_role[role.role_id])


@dataclass(frozen=True)
class CouncilCritique:
    role: str
    idea_id: str
    risks: List[str]
    kill_candidates: List[str]
    unsupported_claims: List[str]
    weakest_assumption: str
    recommendation: str
    explanation: str
    confidence: float
    linked_signal_ids: List[str]
    linked_opportunity_id: str
    ai_metadata: Dict[str, Any]

    def validate(self, *, expected_idea_id: str, expected_signal_ids: Iterable[str], expected_opportunity_id: str) -> None:
        if self.role not in COUNCIL_ROLE_BY_ID:
            raise ValueError("role must be a known council role ID")
        if self.idea_id != expected_idea_id:
            raise ValueError("critique idea_id must match the selected idea")
        if self.linked_opportunity_id != expected_opportunity_id:
            raise ValueError("critique linked_opportunity_id must match the selected idea")
        if list(self.linked_signal_ids) != list(expected_signal_ids):
            raise ValueError("critique linked_signal_ids must preserve selected idea traceability")
        if self.recommendation not in RECOMMENDATIONS:
            raise ValueError("recommendation has an unknown value")
        for field_name in ("weakest_assumption", "explanation"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name in ("risks", "kill_candidates", "unsupported_claims", "linked_signal_ids"):
            value = getattr(self, field_name)
            if not isinstance(value, list):
                raise ValueError(f"{field_name} must be a list")
            if any(not isinstance(item, str) or not item.strip() for item in value):
                raise ValueError(f"{field_name} must contain only non-empty strings")
        if not isinstance(self.confidence, (int, float)) or not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be a number between 0 and 1")
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")

    @property
    def has_serious_risk(self) -> bool:
        return bool(self.kill_candidates) or self.recommendation == "kill" or len(self.risks) >= 2

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["confidence"] = float(data["confidence"])
        return data


@dataclass(frozen=True)
class CouncilRecommendation:
    idea_id: str
    recommendation: str
    explanation: str
    next_action: str
    founder_final_authority: bool = True
    requires_founder_manual_review: bool = False

    def validate(self) -> None:
        if not self.idea_id.strip():
            raise ValueError("idea_id must be non-empty")
        if self.recommendation not in RECOMMENDATIONS:
            raise ValueError("recommendation has an unknown value")
        for field_name in ("explanation", "next_action"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-empty")
        if not self.founder_final_authority:
            raise ValueError("founder_final_authority must remain true")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class CouncilCritiqueSummary:
    idea_id: str
    linked_signal_ids: List[str]
    linked_opportunity_id: str
    critiques: List[CouncilCritique]
    suspiciously_clean: bool
    critique_unavailable: bool
    serious_risk_count: int
    kill_candidate_count: int
    unsupported_claim_count: int
    recommendation: CouncilRecommendation
    rejected_role_outputs: List[str]
    ai_metadata: Dict[str, Any]

    def validate(self) -> None:
        if not self.idea_id.strip():
            raise ValueError("idea_id must be non-empty")
        if not self.linked_opportunity_id.strip():
            raise ValueError("linked_opportunity_id must be non-empty")
        if not isinstance(self.linked_signal_ids, list):
            raise ValueError("linked_signal_ids must be a list")
        for critique in self.critiques:
            critique.validate(
                expected_idea_id=self.idea_id,
                expected_signal_ids=self.linked_signal_ids,
                expected_opportunity_id=self.linked_opportunity_id,
            )
        if not isinstance(self.suspiciously_clean, bool):
            raise ValueError("suspiciously_clean must be a bool")
        if not isinstance(self.critique_unavailable, bool):
            raise ValueError("critique_unavailable must be a bool")
        self.recommendation.validate()
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "idea_id": self.idea_id,
            "linked_signal_ids": list(self.linked_signal_ids),
            "linked_opportunity_id": self.linked_opportunity_id,
            "critiques": [critique.to_dict() for critique in self.critiques],
            "suspiciously_clean": self.suspiciously_clean,
            "critique_unavailable": self.critique_unavailable,
            "serious_risk_count": self.serious_risk_count,
            "kill_candidate_count": self.kill_candidate_count,
            "unsupported_claim_count": self.unsupported_claim_count,
            "recommendation": self.recommendation.to_dict(),
            "rejected_role_outputs": list(self.rejected_role_outputs),
            "ai_metadata": dict(self.ai_metadata),
        }


@dataclass(frozen=True)
class CouncilRunResult:
    selected_idea_ids: List[str]
    summaries: List[CouncilCritiqueSummary]
    critiques: List[CouncilCritique]
    rejected_role_outputs: List[str]
    critique_unavailable: bool
    founder_final_authority: bool
    ai_metadata: Dict[str, Any]

    def validate(self) -> None:
        if not self.founder_final_authority:
            raise ValueError("founder_final_authority must remain true")
        for summary in self.summaries:
            summary.validate()
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "selected_idea_ids": list(self.selected_idea_ids),
            "summaries": [summary.to_dict() for summary in self.summaries],
            "critiques": [critique.to_dict() for critique in self.critiques],
            "rejected_role_outputs": list(self.rejected_role_outputs),
            "critique_unavailable": self.critique_unavailable,
            "founder_final_authority": self.founder_final_authority,
            "ai_metadata": dict(self.ai_metadata),
        }


def select_top_ideas_for_council(
    scores: Iterable[IdeaEvaluationScore],
    *,
    council_threshold: int = COUNCIL_THRESHOLD,
    max_per_opportunity: int = STANDARD_MAX_IDEAS_PER_OPPORTUNITY,
    fallback_top_n: int = 1,
) -> List[IdeaEvaluationScore]:
    grouped: Dict[str, List[IdeaEvaluationScore]] = {}
    for score in scores:
        grouped.setdefault(score.linked_opportunity_id, []).append(score)

    selected: List[IdeaEvaluationScore] = []
    for opportunity_id in sorted(grouped):
        ranked = sorted(grouped[opportunity_id], key=lambda item: item.total_score, reverse=True)
        threshold_hits = [
            score
            for score in ranked
            if score.total_score >= council_threshold and score.schema_valid and score.traceability_valid
        ]
        opportunity_selected = threshold_hits or ranked[:fallback_top_n]
        selected.extend(opportunity_selected[:max_per_opportunity])
    return selected


def run_isolated_council_critique(
    *,
    ideas: Iterable[Any],
    scores: Iterable[IdeaEvaluationScore],
    providers_by_role: Mapping[str, CouncilRoleProvider],
    roles: Optional[List[CouncilRole]] = None,
    council_threshold: int = COUNCIL_THRESHOLD,
    max_per_opportunity: int = STANDARD_MAX_IDEAS_PER_OPPORTUNITY,
) -> CouncilRunResult:
    role_list = roles or COUNCIL_ROLES
    for role in role_list:
        role.validate()
    idea_by_id = {_idea_id(idea): idea for idea in ideas}
    selected_scores = select_top_ideas_for_council(
        scores,
        council_threshold=council_threshold,
        max_per_opportunity=max_per_opportunity,
    )
    run_metadata = _metadata_for(
        selected_scores=selected_scores,
        linked_input_ids=[score.idea_id for score in selected_scores],
        fallback_used=False,
        stage_status=AIStageStatus.success,
        stage_confidence=1.0,
        failure_reason="",
    )
    summaries: List[CouncilCritiqueSummary] = []
    all_critiques: List[CouncilCritique] = []
    rejected_role_outputs: List[str] = []

    for score in selected_scores:
        idea = idea_by_id.get(score.idea_id)
        if idea is None:
            rejected_role_outputs.append(f"{score.idea_id}: selected idea artifact was unavailable")
            summaries.append(_fallback_summary(score, reason="selected idea artifact was unavailable"))
            continue
        critiques: List[CouncilCritique] = []
        summary_errors: List[str] = []
        for role in role_list:
            provider = providers_by_role.get(role.role_id)
            if provider is None:
                summary_errors.append(f"{score.idea_id}/{role.role_id}: missing isolated role provider")
                continue
            try:
                raw = provider.critique(role=role, idea=idea)
                critique = _coerce_critique(raw, role=role, score=score)
                critiques.append(critique)
            except Exception as exc:
                summary_errors.append(f"{score.idea_id}/{role.role_id}: {exc}")
        summary = _summarize_critiques(score=score, critiques=critiques, errors=summary_errors)
        summaries.append(summary)
        all_critiques.extend(critiques)
        rejected_role_outputs.extend(summary_errors)

    if rejected_role_outputs:
        run_metadata = _metadata_for(
            selected_scores=selected_scores,
            linked_input_ids=[score.idea_id for score in selected_scores],
            fallback_used=True,
            stage_status=AIStageStatus.degraded,
            stage_confidence=0.4,
            failure_reason="; ".join(rejected_role_outputs),
        )
    result = CouncilRunResult(
        selected_idea_ids=[score.idea_id for score in selected_scores],
        summaries=summaries,
        critiques=all_critiques,
        rejected_role_outputs=rejected_role_outputs,
        critique_unavailable=bool(rejected_role_outputs),
        founder_final_authority=True,
        ai_metadata=run_metadata,
    )
    result.validate()
    return result


def _metadata_for(
    *,
    selected_scores: List[IdeaEvaluationScore],
    linked_input_ids: List[str],
    fallback_used: bool,
    stage_status: AIStageStatus,
    stage_confidence: float,
    failure_reason: str,
) -> Dict[str, Any]:
    return build_ai_metadata(
        prompt=COUNCIL_CRITIQUE_PROMPT,
        model_id=COUNCIL_CRITIQUE_MODEL_ID,
        input_payload=[score.to_dict() for score in selected_scores],
        generation_mode=IdeationGenerationMode.llm_assisted.value,
        linked_input_ids=linked_input_ids,
        fallback_used=fallback_used,
        stage_confidence=stage_confidence,
        stage_status=stage_status,
        failure_reason=failure_reason,
        fallback_recommendation="Preserve idea and require founder manual review when critique is unavailable.",
        degraded_mode=fallback_used or stage_status == AIStageStatus.degraded,
    ).to_dict()


def _coerce_critique(raw: Mapping[str, Any], *, role: CouncilRole, score: IdeaEvaluationScore) -> CouncilCritique:
    if not isinstance(raw, Mapping):
        raise ValueError("role output must be an object")
    confidence = float(raw.get("confidence"))
    critique = CouncilCritique(
        role=str(raw.get("role") or role.role_id).strip(),
        idea_id=str(raw.get("idea_id") or "").strip(),
        risks=_as_string_list(raw.get("risks")),
        kill_candidates=_as_string_list(raw.get("kill_candidates")),
        unsupported_claims=_as_string_list(raw.get("unsupported_claims")),
        weakest_assumption=str(raw.get("weakest_assumption") or "").strip(),
        recommendation=str(raw.get("recommendation") or "").strip(),
        explanation=str(raw.get("explanation") or "").strip(),
        confidence=confidence,
        linked_signal_ids=_as_string_list(raw.get("linked_signal_ids")),
        linked_opportunity_id=str(raw.get("linked_opportunity_id") or "").strip(),
        ai_metadata=_metadata_for(
            selected_scores=[score],
            linked_input_ids=[score.idea_id],
            fallback_used=False,
            stage_status=AIStageStatus.success,
            stage_confidence=confidence,
            failure_reason="",
        ),
    )
    critique.validate(
        expected_idea_id=score.idea_id,
        expected_signal_ids=score.linked_signal_ids,
        expected_opportunity_id=score.linked_opportunity_id,
    )
    return critique


def _summarize_critiques(
    *,
    score: IdeaEvaluationScore,
    critiques: List[CouncilCritique],
    errors: List[str],
) -> CouncilCritiqueSummary:
    critique_unavailable = bool(errors) or len(critiques) < len(COUNCIL_ROLES)
    serious_risk_count = sum(1 for critique in critiques if critique.has_serious_risk)
    kill_candidate_count = sum(len(critique.kill_candidates) for critique in critiques)
    unsupported_claim_count = sum(len(critique.unsupported_claims) for critique in critiques)
    suspiciously_clean = not critique_unavailable and serious_risk_count == 0 and kill_candidate_count == 0
    recommendation = _aggregate_recommendation(
        score=score,
        critiques=critiques,
        critique_unavailable=critique_unavailable,
        suspiciously_clean=suspiciously_clean,
    )
    metadata = _metadata_for(
        selected_scores=[score],
        linked_input_ids=[score.idea_id],
        fallback_used=critique_unavailable,
        stage_status=AIStageStatus.degraded if critique_unavailable else AIStageStatus.success,
        stage_confidence=_average_confidence(critiques) if critiques else 0.0,
        failure_reason="; ".join(errors),
    )
    summary = CouncilCritiqueSummary(
        idea_id=score.idea_id,
        linked_signal_ids=list(score.linked_signal_ids),
        linked_opportunity_id=score.linked_opportunity_id,
        critiques=critiques,
        suspiciously_clean=suspiciously_clean,
        critique_unavailable=critique_unavailable,
        serious_risk_count=serious_risk_count,
        kill_candidate_count=kill_candidate_count,
        unsupported_claim_count=unsupported_claim_count,
        recommendation=recommendation,
        rejected_role_outputs=list(errors),
        ai_metadata=metadata,
    )
    summary.validate()
    return summary


def _fallback_summary(score: IdeaEvaluationScore, *, reason: str) -> CouncilCritiqueSummary:
    metadata = _metadata_for(
        selected_scores=[score],
        linked_input_ids=[score.idea_id],
        fallback_used=True,
        stage_status=AIStageStatus.degraded,
        stage_confidence=0.0,
        failure_reason=reason,
    )
    recommendation = CouncilRecommendation(
        idea_id=score.idea_id,
        recommendation="needs more evidence",
        explanation=f"Critique unavailable: {reason}. Founder manual review is required.",
        next_action="Preserve the idea and request isolated critique outputs before making a final decision.",
        founder_final_authority=True,
        requires_founder_manual_review=True,
    )
    return CouncilCritiqueSummary(
        idea_id=score.idea_id,
        linked_signal_ids=list(score.linked_signal_ids),
        linked_opportunity_id=score.linked_opportunity_id,
        critiques=[],
        suspiciously_clean=False,
        critique_unavailable=True,
        serious_risk_count=0,
        kill_candidate_count=0,
        unsupported_claim_count=0,
        recommendation=recommendation,
        rejected_role_outputs=[reason],
        ai_metadata=metadata,
    )


def _aggregate_recommendation(
    *,
    score: IdeaEvaluationScore,
    critiques: List[CouncilCritique],
    critique_unavailable: bool,
    suspiciously_clean: bool,
) -> CouncilRecommendation:
    if critique_unavailable:
        return CouncilRecommendation(
            idea_id=score.idea_id,
            recommendation="needs more evidence",
            explanation="At least one isolated council role was missing or invalid, so the critique is unavailable.",
            next_action="Require founder manual review and rerun isolated role critique before relying on the council output.",
            founder_final_authority=True,
            requires_founder_manual_review=True,
        )
    if any(critique.recommendation == "kill" or critique.kill_candidates for critique in critiques):
        return CouncilRecommendation(
            idea_id=score.idea_id,
            recommendation="kill",
            explanation="One or more council roles found a kill candidate or direct kill recommendation.",
            next_action="Founder reviews the kill candidate before deciding whether to stop or reframe the idea.",
            founder_final_authority=True,
            requires_founder_manual_review=False,
        )
    if suspiciously_clean:
        return CouncilRecommendation(
            idea_id=score.idea_id,
            recommendation="needs more evidence",
            explanation="No role found a serious risk; this is suspiciously clean and must be manually reviewed.",
            next_action="Founder challenges the clean critique and asks for disconfirming evidence.",
            founder_final_authority=True,
            requires_founder_manual_review=True,
        )
    if any(critique.recommendation == "park" for critique in critiques):
        return CouncilRecommendation(
            idea_id=score.idea_id,
            recommendation="park",
            explanation="At least one council role recommends parking until the weak point is resolved.",
            next_action="Clarify the weak assumption or missing evidence before running another experiment.",
            founder_final_authority=True,
            requires_founder_manual_review=False,
        )
    return CouncilRecommendation(
        idea_id=score.idea_id,
        recommendation="test now",
        explanation="Council critique found risks but no kill candidate; a narrow test is warranted.",
        next_action="Run the smallest founder-approved experiment against the weakest assumption.",
        founder_final_authority=True,
        requires_founder_manual_review=False,
    )


def _as_string_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("value must be a list")
    return [str(value).strip() for value in raw if str(value).strip()]


def _average_confidence(critiques: List[CouncilCritique]) -> float:
    if not critiques:
        return 0.0
    return round(sum(float(critique.confidence) for critique in critiques) / len(critiques), 3)


def _idea_id(idea: Any) -> str:
    if isinstance(idea, PatternGuidedIdea):
        return idea.idea_id
    if isinstance(idea, Mapping):
        return str(idea.get("idea_id") or idea.get("id") or "").strip()
    return str(getattr(idea, "idea_id", getattr(idea, "id", ""))).strip()
