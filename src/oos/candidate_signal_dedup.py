from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, replace
from typing import Iterable

from .models import CandidateSignal


DEDUP_VERSION = "candidate_signal_dedup_v1"

_SIGNAL_TYPE_RANK = {
    "buying_intent": 0,
    "pain_signal": 1,
    "workaround": 2,
    "competitor_weakness": 3,
    "trend_trigger": 4,
    "needs_human_review": 5,
}
_URL_NOISE_RE = re.compile(r"(?i)(?:[?#].*)$")


@dataclass(frozen=True)
class CandidateSignalDedupResult:
    canonical_signals: list[CandidateSignal]
    suppressed_duplicates: list[CandidateSignal]
    duplicate_group_count: int
    duplicate_signal_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "version": DEDUP_VERSION,
            "canonical_signal_count": len(self.canonical_signals),
            "suppressed_duplicate_count": self.duplicate_signal_count,
            "duplicate_group_count": self.duplicate_group_count,
            "canonical_signal_ids": [signal.signal_id for signal in self.canonical_signals],
            "suppressed_duplicate_signal_ids": [signal.signal_id for signal in self.suppressed_duplicates],
        }


def deduplicate_candidate_signals(signals: Iterable[CandidateSignal]) -> CandidateSignalDedupResult:
    indexed_groups: list[list[tuple[int, CandidateSignal]]] = []
    key_to_group_index: dict[str, int] = {}

    for index, signal in enumerate(signals):
        signal.validate()
        keys = _dedup_keys(signal)
        group_index = _existing_group_index(keys, key_to_group_index)
        if group_index is None:
            group_index = len(indexed_groups)
            indexed_groups.append([])
        indexed_groups[group_index].append((index, signal))
        for key in keys:
            key_to_group_index.setdefault(key, group_index)

    canonical: list[CandidateSignal] = []
    suppressed: list[CandidateSignal] = []
    for group in indexed_groups:
        representative_index, representative = _choose_representative(group)
        duplicates = [(index, signal) for index, signal in group if index != representative_index]
        canonical.append(_with_duplicate_metadata(representative, group))
        suppressed.extend(_mark_suppressed(signal, representative.signal_id) for _, signal in sorted(duplicates, key=lambda item: item[0]))

    canonical.sort(key=_rank_key)
    return CandidateSignalDedupResult(
        canonical_signals=canonical,
        suppressed_duplicates=suppressed,
        duplicate_group_count=sum(1 for group in indexed_groups if len(group) > 1),
        duplicate_signal_count=sum(max(0, len(group) - 1) for group in indexed_groups),
    )


def deduplicate_ranked_candidate_signals(signals: Iterable[CandidateSignal]) -> list[CandidateSignal]:
    return deduplicate_candidate_signals(sorted(signals, key=_rank_key)).canonical_signals


def _dedup_keys(signal: CandidateSignal) -> list[str]:
    keys = []
    evidence_id = signal.evidence_id.strip().lower()
    signal_id = signal.signal_id.strip().lower()
    source_url = _normalize_source_url(signal.source_url)
    if evidence_id:
        keys.append(f"evidence:{evidence_id}")
    if signal_id:
        keys.append(f"signal:{signal_id}")
    if source_url:
        keys.append(f"url:{signal.source_type.strip().lower()}:{source_url}")
    return keys


def _existing_group_index(keys: list[str], key_to_group_index: dict[str, int]) -> int | None:
    for key in keys:
        if key in key_to_group_index:
            return key_to_group_index[key]
    return None


def _choose_representative(group: list[tuple[int, CandidateSignal]]) -> tuple[int, CandidateSignal]:
    return min(group, key=lambda item: (-float(item[1].confidence), item[0]))


def _with_duplicate_metadata(representative: CandidateSignal, group: list[tuple[int, CandidateSignal]]) -> CandidateSignal:
    ordered = [signal for _, signal in sorted(group, key=lambda item: item[0])]
    duplicate_metadata = {
        "version": DEDUP_VERSION,
        "duplicate_count": len(ordered),
        "suppressed_duplicate_count": max(0, len(ordered) - 1),
        "duplicate_evidence_ids": _unique(signal.evidence_id for signal in ordered),
        "duplicate_signal_ids": _unique(signal.signal_id for signal in ordered),
        "duplicate_source_urls": _unique(signal.source_url for signal in ordered),
    }
    scoring_breakdown = dict(representative.scoring_breakdown)
    scoring_breakdown["candidate_dedup"] = duplicate_metadata
    traceability = dict(representative.traceability)
    traceability["duplicate_count"] = str(len(ordered))
    traceability["duplicate_evidence_ids"] = ",".join(duplicate_metadata["duplicate_evidence_ids"])
    updated = replace(representative, traceability=traceability, scoring_breakdown=scoring_breakdown)
    updated.validate()
    return updated


def _mark_suppressed(signal: CandidateSignal, canonical_signal_id: str) -> CandidateSignal:
    scoring_breakdown = dict(signal.scoring_breakdown)
    scoring_breakdown["candidate_dedup"] = {
        "version": DEDUP_VERSION,
        "suppressed_from_founder_package": True,
        "canonical_signal_id": canonical_signal_id,
    }
    updated = replace(signal, scoring_breakdown=scoring_breakdown)
    updated.validate()
    return updated


def _rank_key(signal: CandidateSignal) -> tuple[float, int, str]:
    return (-float(signal.confidence), _SIGNAL_TYPE_RANK.get(signal.signal_type, 99), signal.signal_id)


def _normalize_source_url(source_url: str) -> str:
    normalized = _URL_NOISE_RE.sub("", source_url.strip().lower()).rstrip("/")
    return normalized


def _unique(values: Iterable[str]) -> list[str]:
    seen = set()
    unique_values = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values
