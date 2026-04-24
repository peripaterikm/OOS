from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List

from .models import Signal
from .signal_layer import RawSignal


NEAR_DUPLICATE_COSINE_THRESHOLD = 0.85

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_signal_text(text: str) -> str:
    lowered = text.lower()
    tokens = _TOKEN_RE.findall(lowered)
    return _WHITESPACE_RE.sub(" ", " ".join(tokens)).strip()


def signal_fingerprint(text: str) -> str:
    normalized = normalize_signal_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _token_vector(normalized_text: str) -> Dict[str, int]:
    vector: Dict[str, int] = {}
    for token in normalized_text.split():
        vector[token] = vector.get(token, 0) + 1
    return vector


def cosine_similarity_on_normalized_text(left: str, right: str) -> float:
    left_vector = _token_vector(normalize_signal_text(left))
    right_vector = _token_vector(normalize_signal_text(right))
    if not left_vector or not right_vector:
        return 0.0

    common_tokens = set(left_vector) & set(right_vector)
    dot = sum(left_vector[token] * right_vector[token] for token in common_tokens)
    left_norm = math.sqrt(sum(count * count for count in left_vector.values()))
    right_norm = math.sqrt(sum(count * count for count in right_vector.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


@dataclass(frozen=True)
class SignalDedupMetadata:
    signal_id: str
    normalized_fingerprint: str
    duplicate_group_id: str
    is_duplicate: bool
    canonical_signal_id: str
    duplicate_reason: str
    similarity_to_canonical: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "normalized_fingerprint": self.normalized_fingerprint,
            "duplicate_group_id": self.duplicate_group_id,
            "is_duplicate": self.is_duplicate,
            "canonical_signal_id": self.canonical_signal_id,
            "duplicate_reason": self.duplicate_reason,
            "similarity_to_canonical": self.similarity_to_canonical,
            "near_duplicate_method": "cosine_similarity_on_normalized_signal_text",
            "near_duplicate_threshold": NEAR_DUPLICATE_COSINE_THRESHOLD,
        }


@dataclass(frozen=True)
class _CanonicalCandidate:
    signal_id: str
    normalized_text: str
    fingerprint: str


def build_dedup_metadata(raw_signals: Iterable[RawSignal]) -> Dict[str, SignalDedupMetadata]:
    canonical_candidates: List[_CanonicalCandidate] = []
    by_fingerprint: Dict[str, _CanonicalCandidate] = {}
    result: Dict[str, SignalDedupMetadata] = {}

    for index, raw in enumerate(raw_signals, start=1):
        signal_id = raw.id or f"raw_signal_{index}"
        normalized_text = normalize_signal_text(raw.raw_content)
        fingerprint = signal_fingerprint(raw.raw_content)

        exact_match = by_fingerprint.get(fingerprint)
        if exact_match is not None:
            result[signal_id] = SignalDedupMetadata(
                signal_id=signal_id,
                normalized_fingerprint=fingerprint,
                duplicate_group_id=f"dupgrp_{exact_match.signal_id}",
                is_duplicate=True,
                canonical_signal_id=exact_match.signal_id,
                duplicate_reason="exact_duplicate",
                similarity_to_canonical=1.0,
            )
            continue

        near_match = None
        near_match_similarity = 0.0
        for candidate in canonical_candidates:
            similarity = cosine_similarity_on_normalized_text(normalized_text, candidate.normalized_text)
            if similarity >= NEAR_DUPLICATE_COSINE_THRESHOLD:
                near_match = candidate
                near_match_similarity = similarity
                break

        if near_match is not None:
            result[signal_id] = SignalDedupMetadata(
                signal_id=signal_id,
                normalized_fingerprint=fingerprint,
                duplicate_group_id=f"dupgrp_{near_match.signal_id}",
                is_duplicate=True,
                canonical_signal_id=near_match.signal_id,
                duplicate_reason="near_duplicate",
                similarity_to_canonical=near_match_similarity,
            )
            continue

        candidate = _CanonicalCandidate(
            signal_id=signal_id,
            normalized_text=normalized_text,
            fingerprint=fingerprint,
        )
        canonical_candidates.append(candidate)
        by_fingerprint[fingerprint] = candidate
        result[signal_id] = SignalDedupMetadata(
            signal_id=signal_id,
            normalized_fingerprint=fingerprint,
            duplicate_group_id=f"dupgrp_{signal_id}",
            is_duplicate=False,
            canonical_signal_id=signal_id,
            duplicate_reason="canonical",
            similarity_to_canonical=1.0,
        )

    return result


def canonical_signal_set(signals: Iterable[Signal]) -> List[Signal]:
    return [signal for signal in signals if not bool(signal.metadata.get("is_duplicate", False))]


def original_signal_ids_by_canonical(signals: Iterable[Signal]) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = {}
    for signal in signals:
        canonical_id = str(signal.metadata.get("canonical_signal_id") or signal.id)
        grouped.setdefault(canonical_id, []).append(signal.id)
    return grouped
