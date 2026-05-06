from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .candidate_signal_dedup import deduplicate_candidate_signals
from .evidence_pack import (
    INSUFFICIENT_EVIDENCE_CREATED_FROM,
    EvidencePack,
    EvidencePackItem,
    EvidencePackRiskNote,
    EvidencePackSourceSummary,
    evidence_pack_from_dict,
    evidence_pack_to_dict,
    make_evidence_pack_id,
    normalize_evidence_pack_order,
)
from .models import CandidateSignal, PriceSignal, WeakPatternCandidate, model_from_dict


EVIDENCE_PACK_BUILDER_VERSION = "evidence_pack_builder.v1"


@dataclass(frozen=True)
class EvidencePackBuilder:
    min_evidence_count: int = 2

    def build_from_signals(
        self,
        *,
        cluster_id: str,
        candidate_signals: Iterable[CandidateSignal],
        price_signals: Iterable[PriceSignal] | None = None,
        weak_pattern: WeakPatternCandidate | None = None,
        kill_warnings: Iterable[Any] | None = None,
        created_from: str = EVIDENCE_PACK_BUILDER_VERSION,
    ) -> EvidencePack:
        return build_evidence_pack_from_signals(
            cluster_id=cluster_id,
            candidate_signals=candidate_signals,
            price_signals=price_signals or [],
            weak_pattern=weak_pattern,
            kill_warnings=kill_warnings or [],
            created_from=created_from,
            min_evidence_count=self.min_evidence_count,
        )

    def build_for_clusters(
        self,
        *,
        candidate_signals: Iterable[CandidateSignal],
        price_signals: Iterable[PriceSignal] | None = None,
        weak_patterns: Iterable[WeakPatternCandidate] | None = None,
        kill_warnings: Iterable[Any] | None = None,
    ) -> list[EvidencePack]:
        return build_evidence_packs_for_clusters(
            candidate_signals=candidate_signals,
            price_signals=price_signals or [],
            weak_patterns=weak_patterns or [],
            kill_warnings=kill_warnings or [],
            min_evidence_count=self.min_evidence_count,
        )


def build_evidence_pack(
    *,
    cluster_id: str,
    candidate_signals: Iterable[CandidateSignal],
    price_signals: Iterable[PriceSignal] | None = None,
    weak_pattern: WeakPatternCandidate | None = None,
    kill_warnings: Iterable[Any] | None = None,
) -> EvidencePack:
    return EvidencePackBuilder().build_from_signals(
        cluster_id=cluster_id,
        candidate_signals=candidate_signals,
        price_signals=price_signals or [],
        weak_pattern=weak_pattern,
        kill_warnings=kill_warnings or [],
    )


def build_evidence_pack_from_signals(
    *,
    cluster_id: str,
    candidate_signals: Iterable[CandidateSignal],
    price_signals: Iterable[PriceSignal] | None = None,
    weak_pattern: WeakPatternCandidate | None = None,
    kill_warnings: Iterable[Any] | None = None,
    created_from: str = EVIDENCE_PACK_BUILDER_VERSION,
    min_evidence_count: int = 2,
) -> EvidencePack:
    ordered_signals = _canonical_signals(candidate_signals)
    risk_notes = _risk_notes_for_signals(ordered_signals, min_evidence_count=min_evidence_count)
    evidence_ids = _unique_sorted(signal.evidence_id for signal in ordered_signals if signal.evidence_id)
    source_urls = _unique_sorted(signal.source_url for signal in ordered_signals if signal.source_url)
    topic_id = _topic_id(ordered_signals, weak_pattern)
    linked_price_signal_ids = link_price_signals_by_evidence_id(price_signals or [], evidence_ids)
    linked_kill_warning_ids = link_kill_warnings_by_evidence_id(kill_warnings or [], evidence_ids, [signal.signal_id for signal in ordered_signals])
    if not linked_price_signal_ids and ordered_signals:
        risk_notes.append(
            EvidencePackRiskNote(
                risk_type="missing_price_signal",
                note="No explicit price signal is linked to this evidence pack.",
                severity="low",
            )
        )
    risk_notes.extend(_risk_notes_for_kill_warnings(kill_warnings or [], linked_kill_warning_ids))

    created_from_value = created_from
    if not evidence_ids or not source_urls:
        created_from_value = INSUFFICIENT_EVIDENCE_CREATED_FROM
        risk_notes.append(
            EvidencePackRiskNote(
                risk_type="insufficient_evidence",
                note="Evidence pack has missing evidence IDs or source URLs.",
                severity="high",
            )
        )

    pack = EvidencePack(
        evidence_pack_id=make_evidence_pack_id(cluster_id),
        cluster_id=cluster_id,
        source_signal_ids=[signal.signal_id for signal in ordered_signals],
        evidence_ids=evidence_ids,
        source_urls=source_urls,
        summaries=[signal.pain_summary for signal in ordered_signals],
        source_types=_unique_sorted(signal.source_type for signal in ordered_signals if signal.source_type),
        topic_id=topic_id,
        confidence_values=[float(signal.confidence) for signal in ordered_signals],
        price_signal_ids=linked_price_signal_ids,
        weak_pattern_ids=[weak_pattern.pattern_id] if weak_pattern is not None else [],
        kill_warning_ids=linked_kill_warning_ids,
        source_diversity=summarize_source_diversity(ordered_signals),
        recurrence_count=len(evidence_ids),
        risk_notes=risk_notes,
        items=[
            EvidencePackItem(
                evidence_id=signal.evidence_id,
                source_signal_id=signal.signal_id,
                source_url=signal.source_url,
                source_type=signal.source_type,
                summary=signal.pain_summary,
                confidence=float(signal.confidence),
            )
            for signal in ordered_signals
            if signal.evidence_id and signal.source_url
        ],
        source_summaries=summarize_sources(ordered_signals),
        created_from=created_from_value,
    )
    normalized = normalize_evidence_pack_order(pack)
    normalized.validate()
    return normalized


def build_evidence_packs_for_clusters(
    *,
    candidate_signals: Iterable[CandidateSignal],
    price_signals: Iterable[PriceSignal] | None = None,
    weak_patterns: Iterable[WeakPatternCandidate] | None = None,
    kill_warnings: Iterable[Any] | None = None,
    min_evidence_count: int = 2,
) -> list[EvidencePack]:
    canonical_signals = _canonical_signals(candidate_signals)
    signal_by_id = {signal.signal_id: signal for signal in canonical_signals}
    packs: list[EvidencePack] = []
    for weak_pattern in sorted(weak_patterns or [], key=lambda item: item.pattern_id):
        cluster_signals = [signal_by_id[signal_id] for signal_id in weak_pattern.signal_ids if signal_id in signal_by_id]
        if not cluster_signals:
            continue
        packs.append(
            build_evidence_pack_from_signals(
                cluster_id=weak_pattern.cluster_key,
                candidate_signals=cluster_signals,
                price_signals=price_signals or [],
                weak_pattern=weak_pattern,
                kill_warnings=kill_warnings or [],
                created_from="weak_pattern_candidate",
                min_evidence_count=min_evidence_count,
            )
        )
    if packs:
        return sorted(packs, key=lambda pack: pack.cluster_id)

    grouped: dict[str, list[CandidateSignal]] = defaultdict(list)
    for signal in canonical_signals:
        grouped[_cluster_key(signal)].append(signal)
    for cluster_id, signals in sorted(grouped.items()):
        packs.append(
            build_evidence_pack_from_signals(
                cluster_id=cluster_id,
                candidate_signals=signals,
                price_signals=price_signals or [],
                kill_warnings=kill_warnings or [],
                created_from=EVIDENCE_PACK_BUILDER_VERSION,
                min_evidence_count=min_evidence_count,
            )
        )
    return sorted(packs, key=lambda pack: pack.cluster_id)


def build_evidence_packs_from_discovery_artifacts(run_dir: Path) -> list[EvidencePack]:
    candidate_signals = [model_from_dict(CandidateSignal, item) for item in _read_json_items(run_dir / "candidate_signals.json")]
    price_signals = [model_from_dict(PriceSignal, item) for item in _read_json_items(run_dir / "price_signals.json")]
    weak_patterns = [
        model_from_dict(WeakPatternCandidate, item) for item in _read_json_items(run_dir / "weak_pattern_candidates.json")
    ]
    kill_warnings = _read_json_items(run_dir / "kill_archive_warnings.json")
    return build_evidence_packs_for_clusters(
        candidate_signals=candidate_signals,
        price_signals=price_signals,
        weak_patterns=weak_patterns,
        kill_warnings=kill_warnings,
    )


def write_evidence_packs(path: Path, evidence_packs: Iterable[EvidencePack]) -> None:
    payload = {"items": [evidence_pack_to_dict(pack) for pack in sorted(evidence_packs, key=lambda item: item.cluster_id)]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_evidence_packs(path: Path) -> list[EvidencePack]:
    return [evidence_pack_from_dict(item) for item in _read_json_items(path)]


def link_price_signals_by_evidence_id(price_signals: Iterable[PriceSignal], evidence_ids: Iterable[str]) -> list[str]:
    evidence_id_set = set(evidence_ids)
    linked = []
    for price_signal in price_signals:
        price_signal.validate()
        if price_signal.evidence_id in evidence_id_set and price_signal.has_explicit_signal:
            linked.append(price_signal.price_signal_id)
    return _unique_sorted(linked)


def link_kill_warnings_by_evidence_id(
    kill_warnings: Iterable[Any],
    evidence_ids: Iterable[str],
    signal_ids: Iterable[str],
) -> list[str]:
    evidence_id_set = set(evidence_ids)
    signal_id_set = set(signal_ids)
    linked = []
    for warning in kill_warnings:
        evidence_id = _warning_value(warning, "evidence_id")
        signal_id = _warning_value(warning, "signal_id")
        warning_id = _warning_value(warning, "warning_id")
        if warning_id and (evidence_id in evidence_id_set or signal_id in signal_id_set):
            linked.append(warning_id)
    return _unique_sorted(linked)


def summarize_source_diversity(candidate_signals: Iterable[CandidateSignal]) -> int:
    return len({signal.source_type for signal in candidate_signals if signal.source_type})


def summarize_sources(candidate_signals: Iterable[CandidateSignal]) -> list[EvidencePackSourceSummary]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for signal in candidate_signals:
        if signal.source_type and signal.evidence_id:
            grouped[signal.source_type].append(signal.evidence_id)
    return [
        EvidencePackSourceSummary(
            source_type=source_type,
            source_count=len(_unique_sorted(evidence_ids)),
            evidence_ids=_unique_sorted(evidence_ids),
        )
        for source_type, evidence_ids in sorted(grouped.items())
    ]


def _canonical_signals(candidate_signals: Iterable[CandidateSignal]) -> list[CandidateSignal]:
    deduped = deduplicate_candidate_signals(candidate_signals).canonical_signals
    return sorted(deduped, key=lambda signal: (signal.evidence_id, signal.signal_id, signal.source_url))


def _risk_notes_for_signals(candidate_signals: list[CandidateSignal], *, min_evidence_count: int) -> list[EvidencePackRiskNote]:
    risk_notes = []
    if len({signal.evidence_id for signal in candidate_signals if signal.evidence_id}) < min_evidence_count:
        risk_notes.append(
            EvidencePackRiskNote(
                risk_type="insufficient_evidence_count",
                note=f"Evidence pack has fewer than {min_evidence_count} distinct evidence items.",
                severity="high",
            )
        )
    if summarize_source_diversity(candidate_signals) == 1 and candidate_signals:
        risk_notes.append(
            EvidencePackRiskNote(
                risk_type="single_source_type",
                note="Evidence comes from only one source type.",
                severity="medium",
            )
        )
    for signal in candidate_signals:
        if signal.signal_type == "needs_human_review" or signal.classification == "needs_human_review":
            risk_notes.append(
                EvidencePackRiskNote(
                    risk_type="needs_human_review",
                    note="Candidate signal was marked as needing human review.",
                    evidence_id=signal.evidence_id,
                    severity="medium",
                )
            )
        if _has_vendor_or_source_quality_note(signal):
            risk_notes.append(
                EvidencePackRiskNote(
                    risk_type="source_quality_issue",
                    note="Candidate signal carries vendor-promo or source-quality warning metadata.",
                    evidence_id=signal.evidence_id,
                    severity="medium",
                )
            )
        dedup_metadata = signal.scoring_breakdown.get("candidate_dedup", {}) if isinstance(signal.scoring_breakdown, dict) else {}
        if int(dedup_metadata.get("suppressed_duplicate_count", 0) or 0) > 0:
            risk_notes.append(
                EvidencePackRiskNote(
                    risk_type="duplicate_collapsed",
                    note="Duplicate candidate signals were collapsed before evidence-pack recurrence counting.",
                    evidence_id=signal.evidence_id,
                    severity="low",
                )
            )
    return _dedupe_risk_notes(risk_notes)


def _risk_notes_for_kill_warnings(kill_warnings: Iterable[Any], linked_warning_ids: list[str]) -> list[EvidencePackRiskNote]:
    warning_id_set = set(linked_warning_ids)
    risk_notes = []
    for warning in kill_warnings:
        warning_id = _warning_value(warning, "warning_id")
        if warning_id not in warning_id_set:
            continue
        risk_notes.append(
            EvidencePackRiskNote(
                risk_type="kill_archive_warning",
                note=str(_warning_value(warning, "summary") or "Similar killed opportunity warning is linked."),
                evidence_id=_warning_value(warning, "evidence_id") or None,
                severity="medium",
            )
        )
    return risk_notes


def _has_vendor_or_source_quality_note(signal: CandidateSignal) -> bool:
    haystack = " ".join(
        [
            " ".join(str(item) for item in signal.scoring_breakdown.get("explanation", []))
            if isinstance(signal.scoring_breakdown, dict)
            else "",
            json.dumps(signal.scoring_breakdown, sort_keys=True) if isinstance(signal.scoring_breakdown, dict) else "",
            json.dumps(signal.traceability, sort_keys=True) if isinstance(signal.traceability, dict) else "",
        ]
    ).lower()
    return any(token in haystack for token in ("vendor_promo", "vendor-promo", "source_quality", "seo_noise"))


def _cluster_key(signal: CandidateSignal) -> str:
    for container in (signal.traceability, signal.scoring_breakdown):
        if isinstance(container, dict):
            value = container.get("evidence_pack_cluster_id") or container.get("weak_cluster_key") or container.get("cluster_key")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return f"{signal.topic_id}:{signal.query_kind}:{signal.source_type}"


def _topic_id(candidate_signals: list[CandidateSignal], weak_pattern: WeakPatternCandidate | None) -> str:
    if candidate_signals:
        return sorted({signal.topic_id for signal in candidate_signals})[0]
    if weak_pattern is not None:
        return weak_pattern.cluster_key
    return "unknown_topic"


def _warning_value(warning: Any, key: str) -> str:
    if isinstance(warning, dict):
        value = warning.get(key, "")
    else:
        value = getattr(warning, key, "")
    return str(value or "")


def _dedupe_risk_notes(risk_notes: list[EvidencePackRiskNote]) -> list[EvidencePackRiskNote]:
    seen = set()
    deduped = []
    for note in risk_notes:
        key = (note.risk_type, note.note, note.evidence_id, note.severity)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(note)
    return deduped


def _read_json_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        items = payload.get("items", payload.get("candidate_signals", payload.get("price_signals", [])))
    else:
        items = payload
    if not isinstance(items, list):
        raise ValueError(f"Expected list-like artifact payload: {path}")
    return items


def _unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})
