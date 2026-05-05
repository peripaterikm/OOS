from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from .models import CandidateSignal, WeakPatternCandidate


MIN_SIGNAL_COUNT = 5
MIN_AVG_CONFIDENCE = 0.30
MIN_SOURCE_DIVERSITY = 2
MAX_CONFIDENCE_EXCLUSIVE = 0.60

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "before",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "our",
    "the",
    "to",
    "too",
    "we",
    "with",
}


def aggregate_weak_pattern_candidates(signals: Iterable[CandidateSignal]) -> list[WeakPatternCandidate]:
    clusters: dict[str, list[CandidateSignal]] = defaultdict(list)
    for signal in signals:
        signal.validate()
        if not _is_weak_signal(signal):
            continue
        clusters[_cluster_key(signal)].append(signal)

    candidates = []
    for cluster_key, cluster_signals in clusters.items():
        candidate = _build_candidate(cluster_key, cluster_signals)
        if candidate is not None:
            candidates.append(candidate)
    return sorted(candidates, key=lambda item: (-item.confidence, item.pattern_id))


def _is_weak_signal(signal: CandidateSignal) -> bool:
    return signal.signal_type == "needs_human_review" or float(signal.confidence) < MAX_CONFIDENCE_EXCLUSIVE


def _cluster_key(signal: CandidateSignal) -> str:
    for container in (signal.traceability, signal.scoring_breakdown):
        if isinstance(container, dict):
            value = container.get("weak_cluster_key") or container.get("cluster_key") or container.get("pattern_key")
            if isinstance(value, str) and value.strip():
                return _safe_key(value)
    return _safe_key(f"{signal.topic_id}:{signal.query_kind}:{signal.target_user}:{_summary_key(signal.pain_summary)}")


def _summary_key(summary: str) -> str:
    tokens = [token for token in _TOKEN_RE.findall(summary.lower()) if token not in _STOPWORDS]
    return "_".join(tokens[:6]) or "unknown_pattern"


def _build_candidate(cluster_key: str, signals: list[CandidateSignal]) -> WeakPatternCandidate | None:
    ordered = sorted(signals, key=lambda signal: signal.signal_id)
    signal_count = len(ordered)
    confidences = [float(signal.confidence) for signal in ordered]
    avg_confidence = round(sum(confidences) / signal_count, 3) if signal_count else 0.0
    max_confidence = round(max(confidences), 3) if confidences else 0.0
    sources = sorted({signal.source_id for signal in ordered})
    source_diversity = len(sources)

    if signal_count < MIN_SIGNAL_COUNT:
        return None
    if avg_confidence < MIN_AVG_CONFIDENCE:
        return None
    if source_diversity < MIN_SOURCE_DIVERSITY:
        return None
    if max_confidence >= MAX_CONFIDENCE_EXCLUSIVE:
        return None

    candidate = WeakPatternCandidate(
        pattern_id=f"weak_pattern_{cluster_key}",
        classification="weak_pattern_candidate",
        review_priority="elevated",
        signal_ids=[signal.signal_id for signal in ordered],
        signal_count=signal_count,
        avg_confidence=avg_confidence,
        max_confidence=max_confidence,
        source_diversity=source_diversity,
        sources=sources,
        evidence_ids=sorted({signal.evidence_id for signal in ordered}),
        summary=_summary(ordered, source_diversity=source_diversity, avg_confidence=avg_confidence),
        confidence=avg_confidence,
        cluster_key=cluster_key,
    )
    candidate.validate()
    return candidate


def _summary(signals: list[CandidateSignal], *, source_diversity: int, avg_confidence: float) -> str:
    first = signals[0].pain_summary.rstrip(".")
    return (
        f"Weak pattern across {len(signals)} signals from {source_diversity} sources "
        f"(avg confidence {avg_confidence}): {first}."
    )


def _safe_key(value: str) -> str:
    return _SAFE_ID_RE.sub("_", value.strip().lower()).strip("_") or "weak_pattern"
