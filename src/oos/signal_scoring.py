from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .evidence_classifier import (
    NEEDS_HUMAN_REVIEW,
    NOISE,
    anti_marketing_penalty,
    buying_indicator_score,
    pain_indicator_score,
    topic_relevance_score,
    urgency_indicator_score,
    user_pain_marker_score,
    workaround_indicator_score,
)


SCORING_MODEL_VERSION = "signal_scoring_v2_embeddings_disabled"

EMBEDDINGS_DISABLED_WEIGHTS: Dict[str, float] = {
    "topic_relevance_score": 0.25,
    "pain_strength_score": 0.25,
    "workaround_score": 0.15,
    "buying_intent_score": 0.10,
    "urgency_score": 0.10,
    "source_quality_weight": 0.10,
    "customer_voice_match_bonus": 0.05,
}

SIGNAL_TYPE_MULTIPLIERS: Dict[str, float] = {
    "pain_signal": 1.06,
    "workaround": 1.04,
    "buying_intent": 1.04,
    "competitor_weakness": 0.98,
    "trend_trigger": 0.96,
    "needs_human_review": 0.88,
}

SOURCE_QUALITY_WEIGHTS: Dict[str, float] = {
    "github_issues": 0.78,
    "hacker_news_algolia": 0.72,
    "stack_exchange": 0.62,
    "rss_feed": 0.45,
}

_LOW_RELEVANCE_CAP = 0.50
_HUMAN_REVIEW_CAP = 0.40
_MARKETING_REVIEW_CAP = 0.35


@dataclass(frozen=True)
class SignalScoringInput:
    topic_id: str
    source_type: str
    query_kind: str
    classification_label: str
    signal_type: str
    title: str = ""
    body: str = ""
    pain_summary: str = ""
    current_workaround: str = ""
    buying_intent_hint: str = ""
    urgency_hint: str = ""
    classification_confidence: float = 0.0
    matched_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    semantic_relevance_score: float | None = None
    semantic_relevance_provider_id: str | None = None
    semantic_relevance_available: bool = False
    price_signal_explicit: bool = False
    price_signal_confidence: float = 0.0
    kill_pattern_flag: bool = False
    kill_pattern_penalty: float = 0.0


@dataclass(frozen=True)
class SignalScoreBreakdown:
    topic_relevance_score: float
    pain_strength_score: float
    workaround_score: float
    buying_intent_score: float
    urgency_score: float
    source_quality_weight: float
    customer_voice_match_bonus: float
    price_signal_boost: float
    kill_pattern_flag: bool
    kill_pattern_penalty: float
    semantic_relevance_score: float
    semantic_relevance_provider_id: str
    semantic_relevance_available: bool
    anti_marketing_penalty: float
    signal_type_multiplier: float
    classification_confidence_factor: float
    human_review_cap_applied: bool
    noise_cap_applied: bool
    final_score: float
    explanation: List[str]
    scoring_model_version: str = SCORING_MODEL_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def scoring_weights_sum() -> float:
    return round(sum(EMBEDDINGS_DISABLED_WEIGHTS.values()), 6)


def build_signal_score_breakdown(scoring_input: SignalScoringInput) -> SignalScoreBreakdown:
    text = _combined_text(scoring_input)
    explanation: List[str] = ["embeddings_disabled_formula"]

    semantic_score, semantic_provider_id, semantic_available = _semantic_relevance_diagnostic(scoring_input)
    topic_score = topic_relevance_score(text, scoring_input.topic_id)
    pain_score = _pain_strength_score(text, scoring_input)
    workaround_score = _workaround_score(text, scoring_input)
    buying_score = _buying_intent_score(text, scoring_input)
    urgency_score = _urgency_score(text, scoring_input)
    source_weight = source_quality_weight(scoring_input.source_type)
    customer_voice_bonus = customer_voice_match_bonus(scoring_input)
    price_boost = explicit_price_signal_boost(scoring_input)
    kill_penalty = kill_pattern_penalty(scoring_input)
    marketing_penalty = anti_marketing_penalty(text)
    signal_multiplier = SIGNAL_TYPE_MULTIPLIERS.get(scoring_input.signal_type, 1.0)
    classification_factor = _classification_confidence_factor(scoring_input.classification_confidence)

    component_score = (
        EMBEDDINGS_DISABLED_WEIGHTS["topic_relevance_score"] * topic_score
        + EMBEDDINGS_DISABLED_WEIGHTS["pain_strength_score"] * pain_score
        + EMBEDDINGS_DISABLED_WEIGHTS["workaround_score"] * workaround_score
        + EMBEDDINGS_DISABLED_WEIGHTS["buying_intent_score"] * buying_score
        + EMBEDDINGS_DISABLED_WEIGHTS["urgency_score"] * urgency_score
        + EMBEDDINGS_DISABLED_WEIGHTS["source_quality_weight"] * source_weight
        + EMBEDDINGS_DISABLED_WEIGHTS["customer_voice_match_bonus"] * customer_voice_bonus
    )
    score = component_score * signal_multiplier * classification_factor
    if topic_score >= 0.55 and pain_score >= 0.50 and workaround_score >= 0.45:
        score += 0.13
        explanation.append("synergy:finance_pain_workaround")
    elif topic_score >= 0.45 and pain_score >= 0.35:
        score += 0.04
        explanation.append("synergy:finance_pain")
    if urgency_score >= 0.65 and topic_score >= 0.45:
        score += 0.04
        explanation.append("synergy:urgency_with_finance_context")
    if customer_voice_bonus > 0:
        score += customer_voice_bonus * 0.20
    if price_boost > 0:
        score += price_boost
        explanation.append("price_signal:explicit_evidence_boost")
    if kill_penalty > 0:
        score = apply_kill_pattern_penalty(score, kill_penalty)
        explanation.append("kill_archive:similar_killed_pattern_penalty")
    score -= marketing_penalty * 0.32

    if topic_score < 0.20 and scoring_input.topic_id == "ai_cfo_smb":
        score = min(score, _LOW_RELEVANCE_CAP)
        explanation.append("low_topic_relevance_cap")
    if marketing_penalty >= 0.50:
        score = min(score, _MARKETING_REVIEW_CAP)
        explanation.append("anti_marketing_cap")

    human_review_cap_applied = False
    if scoring_input.classification_label == NEEDS_HUMAN_REVIEW or scoring_input.signal_type == "needs_human_review":
        score = min(score, _HUMAN_REVIEW_CAP)
        human_review_cap_applied = True
        explanation.append("needs_human_review_cap")

    noise_cap_applied = False
    if scoring_input.classification_label == NOISE:
        score = 0.0
        noise_cap_applied = True
        explanation.append("noise_cap")

    if topic_score >= 0.55:
        explanation.append("topic_relevance:finance_anchor")
    if pain_score >= 0.50:
        explanation.append("pain_strength:user_or_friction_language")
    if workaround_score >= 0.45:
        explanation.append("workaround:manual_or_spreadsheet")
    if buying_score > 0:
        explanation.append("buying_intent:detected")
    if urgency_score >= 0.40:
        explanation.append("urgency:detected")
    if customer_voice_bonus > 0:
        explanation.append("customer_voice_query_bonus")
        if scoring_input.metadata.get("persona_id"):
            explanation.append(f"persona:{scoring_input.metadata['persona_id']}")
    if marketing_penalty > 0:
        explanation.append("anti_marketing_penalty")
    if semantic_available:
        explanation.append(f"semantic_relevance:diagnostic_only:{semantic_provider_id}")
    else:
        explanation.append("semantic_relevance:disabled")

    return SignalScoreBreakdown(
        topic_relevance_score=topic_score,
        pain_strength_score=pain_score,
        workaround_score=workaround_score,
        buying_intent_score=buying_score,
        urgency_score=urgency_score,
        source_quality_weight=source_weight,
        customer_voice_match_bonus=customer_voice_bonus,
        price_signal_boost=price_boost,
        kill_pattern_flag=bool(scoring_input.kill_pattern_flag and kill_penalty > 0),
        kill_pattern_penalty=kill_penalty,
        semantic_relevance_score=semantic_score,
        semantic_relevance_provider_id=semantic_provider_id,
        semantic_relevance_available=semantic_available,
        anti_marketing_penalty=marketing_penalty,
        signal_type_multiplier=signal_multiplier,
        classification_confidence_factor=classification_factor,
        human_review_cap_applied=human_review_cap_applied,
        noise_cap_applied=noise_cap_applied,
        final_score=round(_clamp(score), 2),
        explanation=explanation,
    )


def source_quality_weight(source_type: str) -> float:
    return SOURCE_QUALITY_WEIGHTS.get(str(source_type or ""), 0.50)


def customer_voice_match_bonus(scoring_input: SignalScoringInput) -> float:
    if scoring_input.query_kind != "customer_voice_query":
        return 0.0
    bonus = 0.06
    if scoring_input.metadata.get("persona_id") or scoring_input.metadata.get("customer_voice_query_id"):
        bonus += 0.02
    return round(min(0.10, bonus), 2)


def explicit_price_signal_boost(scoring_input: SignalScoringInput) -> float:
    if not scoring_input.price_signal_explicit:
        return 0.0
    try:
        confidence = float(scoring_input.price_signal_confidence)
    except (TypeError, ValueError):
        return 0.0
    if confidence < 0.35:
        return 0.0
    return round(min(0.05, 0.02 + confidence * 0.04), 2)


def kill_pattern_penalty(scoring_input: SignalScoringInput) -> float:
    if not scoring_input.kill_pattern_flag:
        return 0.0
    try:
        penalty = float(scoring_input.kill_pattern_penalty)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(0.16, penalty)), 2)


def apply_kill_pattern_penalty(score: float, penalty: float) -> float:
    try:
        raw_score = float(score)
        raw_penalty = float(penalty)
    except (TypeError, ValueError):
        return 0.0
    return round(_clamp(raw_score - max(0.0, raw_penalty)), 2)


def _semantic_relevance_diagnostic(scoring_input: SignalScoringInput) -> tuple[float, str, bool]:
    provider_id = scoring_input.semantic_relevance_provider_id or "disabled"
    if not scoring_input.semantic_relevance_available or scoring_input.semantic_relevance_score is None:
        return 0.0, provider_id, False
    try:
        score = float(scoring_input.semantic_relevance_score)
    except (TypeError, ValueError):
        return 0.0, provider_id, False
    return round(max(0.0, min(1.0, score)), 2), provider_id, True


def _combined_text(scoring_input: SignalScoringInput) -> str:
    parts = [
        scoring_input.title,
        scoring_input.body,
        scoring_input.pain_summary,
        scoring_input.current_workaround,
        scoring_input.buying_intent_hint,
        scoring_input.urgency_hint,
        " ".join(scoring_input.matched_rules),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _pain_strength_score(text: str, scoring_input: SignalScoringInput) -> float:
    score = max(pain_indicator_score(text), user_pain_marker_score(text))
    if scoring_input.signal_type == "pain_signal":
        score = max(score, 0.35)
    if "manual" in text or "too long" in text or "no visibility" in text:
        score += 0.15
    if "cash gap" in text or "can't pay" in text or "cannot pay" in text:
        score += 0.15
    return round(min(1.0, score), 2)


def _workaround_score(text: str, scoring_input: SignalScoringInput) -> float:
    score = workaround_indicator_score(text)
    if scoring_input.current_workaround and scoring_input.current_workaround != "unknown":
        score = max(score, 0.50)
    if "manual spreadsheet" in text or "separate spreadsheet" in text:
        score += 0.18
    if "copy/paste" in text or "copy paste" in text or "export/import" in text or "reconcile manually" in text:
        score += 0.12
    return round(min(1.0, score), 2)


def _buying_intent_score(text: str, scoring_input: SignalScoringInput) -> float:
    score = buying_indicator_score(text)
    if scoring_input.buying_intent_hint == "present":
        score = max(score, 0.70)
    elif scoring_input.buying_intent_hint == "possible":
        score = max(score, 0.35)
    if "automate" in text or "any software" in text or "best app" in text or "alternative to" in text:
        score += 0.15
    return round(min(1.0, score), 2)


def _urgency_score(text: str, scoring_input: SignalScoringInput) -> float:
    score = urgency_indicator_score(text)
    if scoring_input.urgency_hint == "high":
        score = max(score, 0.70)
    elif scoring_input.urgency_hint == "medium":
        score = max(score, 0.40)
    for term in ("late payments", "can't pay suppliers", "can't pay bills", "tax deadline", "payroll", "month-end close", "due dates", "cash gap"):
        if term in text:
            score += 0.12
    return round(min(1.0, score), 2)


def _classification_confidence_factor(classification_confidence: float) -> float:
    try:
        confidence = float(classification_confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    return round(0.75 + confidence * 0.25, 3)


def _clamp(score: float) -> float:
    return max(0.0, min(0.99, score))
