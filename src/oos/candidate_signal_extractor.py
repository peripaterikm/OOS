from __future__ import annotations

import re
from typing import Iterable, List, Optional

from .evidence_classifier import (
    BUYING_INTENT_CANDIDATE,
    COMPETITOR_WEAKNESS_CANDIDATE,
    NEEDS_HUMAN_REVIEW,
    NOISE,
    PAIN_SIGNAL_CANDIDATE,
    TREND_TRIGGER_CANDIDATE,
    WORKAROUND_SIGNAL_CANDIDATE,
    anti_marketing_penalty,
    buying_indicator_score,
    classify_raw_evidence,
    clean_evidence,
    pain_indicator_score,
    topic_relevance_score,
    urgency_indicator_score,
    user_pain_marker_score,
    workaround_indicator_score,
)
from .models import CandidateSignal, CleanedEvidence, EvidenceClassification, RawEvidence


SIGNAL_TYPE_BY_CLASSIFICATION = {
    PAIN_SIGNAL_CANDIDATE: "pain_signal",
    WORKAROUND_SIGNAL_CANDIDATE: "workaround",
    BUYING_INTENT_CANDIDATE: "buying_intent",
    COMPETITOR_WEAKNESS_CANDIDATE: "competitor_weakness",
    TREND_TRIGGER_CANDIDATE: "trend_trigger",
    NEEDS_HUMAN_REVIEW: "needs_human_review",
}

MEASUREMENT_METHODS = {
    "signal_type": "rule_based",
    "pain_summary": "rule_based",
    "target_user": "rule_based",
    "current_workaround": "rule_based",
    "buying_intent_hint": "rule_based",
    "urgency_hint": "rule_based",
    "confidence": "rule_based",
}

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_MARKDOWN_SUMMARY_RE = re.compile(r"^\s*(?:#{1,6}\s+|\*\*+|```+|[-*_]{3,}\s*)+")
_WORKAROUND_TERMS = (
    "workaround",
    "manual",
    "spreadsheet",
    "hack",
    "we use",
    "i built",
    "temporary solution",
)
_BUYING_TERMS = (
    "looking for",
    "recommend",
    "alternative",
    "would pay",
    "need a tool",
    "any tool",
    "pricing",
)
_HIGH_URGENCY_TERMS = (
    "urgent",
    "asap",
    "blocked",
    "critical",
    "broken",
    "can't",
    "deadline",
    "regulation",
    "compliance",
)
_MEDIUM_URGENCY_TERMS = (
    "recently",
    "changed",
    "hard to",
    "problem",
    "issue",
    "bug",
)


def extract_candidate_signal(
    cleaned: CleanedEvidence,
    classification: EvidenceClassification,
) -> Optional[CandidateSignal]:
    cleaned.validate()
    classification.validate()
    _require_matching_trace(cleaned, classification)

    if classification.classification == NOISE:
        return None

    signal_type = SIGNAL_TYPE_BY_CLASSIFICATION[classification.classification]
    text = _combined_text(cleaned)
    signal = CandidateSignal(
        signal_id=_signal_id(cleaned.evidence_id, classification.classification),
        evidence_id=cleaned.evidence_id,
        source_id=cleaned.source_id,
        source_type=cleaned.source_type,
        source_url=cleaned.source_url,
        topic_id=cleaned.topic_id,
        query_kind=cleaned.query_kind,
        signal_type=signal_type,
        pain_summary=_pain_summary(cleaned),
        target_user=_target_user(cleaned, text),
        current_workaround=_current_workaround(cleaned, text),
        buying_intent_hint=_buying_intent_hint(classification.classification, text),
        urgency_hint=_urgency_hint(classification.classification, text),
        confidence=_confidence(classification, text),
        measurement_methods=dict(MEASUREMENT_METHODS),
        extraction_mode="rule_based_v1",
        classification=classification.classification,
        classification_confidence=float(classification.confidence),
        traceability={
            "evidence_id": cleaned.evidence_id,
            "source_url": cleaned.source_url,
            "source_id": cleaned.source_id,
            "topic_id": cleaned.topic_id,
            "query_kind": cleaned.query_kind,
        },
    )
    signal.validate()
    return signal


def extract_candidate_signals(
    cleaned_items: Iterable[CleanedEvidence],
    classifications: Iterable[EvidenceClassification],
) -> List[CandidateSignal]:
    signals: List[CandidateSignal] = []
    for cleaned, classification in zip(cleaned_items, classifications):
        signal = extract_candidate_signal(cleaned, classification)
        if signal is not None:
            signals.append(signal)
    return signals


def extract_candidate_signal_from_raw(evidence: RawEvidence) -> Optional[CandidateSignal]:
    cleaned = clean_evidence(evidence)
    classification = classify_raw_evidence(evidence)
    return extract_candidate_signal(cleaned, classification)


def extract_candidate_signals_from_raw(evidence_items: Iterable[RawEvidence]) -> List[CandidateSignal]:
    signals: List[CandidateSignal] = []
    for evidence in evidence_items:
        signal = extract_candidate_signal_from_raw(evidence)
        if signal is not None:
            signals.append(signal)
    return signals


def _signal_id(evidence_id: str, classification: str) -> str:
    safe_evidence_id = _SAFE_ID_RE.sub("_", evidence_id.strip()).strip("_")
    safe_classification = _SAFE_ID_RE.sub("_", classification.strip()).strip("_")
    return f"candidate_signal_{safe_evidence_id}_{safe_classification}"


def _combined_text(cleaned: CleanedEvidence) -> str:
    return f"{cleaned.normalized_title} {cleaned.normalized_body}".strip().lower()


def _pain_summary(cleaned: CleanedEvidence) -> str:
    content = cleaned.normalized_body or cleaned.normalized_title
    if not content:
        return "unknown"
    jtbd_match = re.search(r"\bWhen\s+[^.!?]+[.!?]?", content)
    if jtbd_match:
        summary = _clean_summary_sentence(jtbd_match.group(0))
        if len(summary) <= 180:
            return summary
        return f"{summary[:177].rstrip()}..."
    sentences = [_clean_summary_sentence(sentence) for sentence in _SENTENCE_SPLIT_RE.split(content)]
    preferred_terms = (
        "jtbd",
        "when ",
        "i want",
        "manual",
        "spreadsheet",
        "invoice",
        "cash flow",
        "cashflow",
        "payment",
        "bill",
        "bookkeeping",
        "accounting",
        "reporting",
        "workaround",
    )
    summary = ""
    for sentence in sentences:
        lowered = sentence.lower()
        if sentence and any(term in lowered for term in preferred_terms):
            summary = sentence
            break
    if not summary:
        summary = next((sentence for sentence in sentences if sentence), content)
    if len(summary) <= 180:
        return summary
    return f"{summary[:177].rstrip()}..."


def _target_user(cleaned: CleanedEvidence, text: str) -> str:
    if cleaned.source_type in {"github_issues", "stack_exchange"}:
        return "developer"
    if cleaned.source_type == "rss_feed":
        if any(term in text for term in ("regulation", "compliance", "law")):
            return "regulated organization"
        return "market participant"
    if cleaned.source_type == "hacker_news_algolia":
        if any(term in text for term in ("founder", "startup", "smb owner")):
            return "founder"
        if any(term in text for term in ("developer", "api", "code", "engineer")):
            return "developer"
    return "unknown"


def _current_workaround(cleaned: CleanedEvidence, text: str) -> str:
    if not any(term in text for term in _WORKAROUND_TERMS):
        return "unknown"
    content = cleaned.normalized_body or cleaned.normalized_title
    for sentence in _SENTENCE_SPLIT_RE.split(content):
        sentence_text = sentence.strip()
        if sentence_text and any(term in sentence_text.lower() for term in _WORKAROUND_TERMS):
            if len(sentence_text) <= 160:
                return sentence_text
            return f"{sentence_text[:157].rstrip()}..."
    return "workaround mentioned"


def _buying_intent_hint(classification: str, text: str) -> str:
    if classification == BUYING_INTENT_CANDIDATE:
        return "present"
    if any(term in text for term in _BUYING_TERMS):
        return "possible"
    if classification == NEEDS_HUMAN_REVIEW:
        return "unknown"
    return "not_detected"


def _urgency_hint(classification: str, text: str) -> str:
    if any(term in text for term in _HIGH_URGENCY_TERMS):
        return "high"
    if classification == TREND_TRIGGER_CANDIDATE or any(term in text for term in _MEDIUM_URGENCY_TERMS):
        return "medium"
    if classification == NEEDS_HUMAN_REVIEW:
        return "unknown"
    return "low"


def _confidence(classification: EvidenceClassification, text: str) -> float:
    base = float(classification.confidence)
    relevance = topic_relevance_score(text, classification.topic_id)
    marketing = anti_marketing_penalty(text)
    genuine_pain = user_pain_marker_score(text)
    if classification.classification == NEEDS_HUMAN_REVIEW:
        score = base * 0.65 + relevance * 0.12 + genuine_pain * 0.08 - marketing * 0.12
        return round(max(0.25, min(0.4, score)), 2)
    pain_score = pain_indicator_score(text)
    workaround_score = workaround_indicator_score(text)
    score = base * 0.55
    score += relevance * 0.32
    score += pain_score * 0.08
    score += workaround_score * 0.12
    score += buying_indicator_score(text) * 0.05
    score += urgency_indicator_score(text) * 0.04
    score += genuine_pain * 0.1
    score -= marketing * 0.22
    if relevance >= 0.45 and (pain_score >= 0.2 or workaround_score >= 0.2):
        score += 0.08
    if classification.source_type in {"github_issues", "stack_exchange"}:
        score += 0.02
    return round(max(0.1, min(0.95, score)), 2)


def _clean_summary_sentence(sentence: str) -> str:
    summary = _MARKDOWN_SUMMARY_RE.sub("", sentence).strip()
    return summary.strip("*`_ -")


def _require_matching_trace(cleaned: CleanedEvidence, classification: EvidenceClassification) -> None:
    for field_name in ("evidence_id", "source_id", "source_type", "source_url", "topic_id", "query_kind"):
        if getattr(cleaned, field_name) != getattr(classification, field_name):
            raise ValueError(f"CleanedEvidence.{field_name} must match EvidenceClassification.{field_name}")
