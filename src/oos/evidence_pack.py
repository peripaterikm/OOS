from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field, replace
from typing import Any


EVIDENCE_PACK_SCHEMA_VERSION = "evidence_pack.v1"
INSUFFICIENT_EVIDENCE_CREATED_FROM = "insufficient_evidence"


@dataclass(frozen=True)
class EvidencePackItem:
    evidence_id: str
    source_signal_id: str
    source_url: str
    source_type: str
    summary: str
    confidence: float | None = None

    def validate(self) -> None:
        _require_non_empty(self.evidence_id, "EvidencePackItem.evidence_id")
        _require_non_empty(self.source_signal_id, "EvidencePackItem.source_signal_id")
        _require_non_empty(self.source_url, "EvidencePackItem.source_url")
        _require_non_empty(self.source_type, "EvidencePackItem.source_type")
        if not isinstance(self.summary, str):
            raise ValueError("EvidencePackItem.summary must be a string")
        if self.confidence is not None and not 0 <= float(self.confidence) <= 1:
            raise ValueError("EvidencePackItem.confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidencePackItem:
        return cls(
            evidence_id=str(data.get("evidence_id", "")),
            source_signal_id=str(data.get("source_signal_id", "")),
            source_url=str(data.get("source_url", "")),
            source_type=str(data.get("source_type", "")),
            summary=str(data.get("summary", "")),
            confidence=data.get("confidence"),
        )


@dataclass(frozen=True)
class EvidencePackRiskNote:
    risk_type: str
    note: str
    evidence_id: str | None = None
    severity: str = "medium"

    def validate(self) -> None:
        _require_non_empty(self.risk_type, "EvidencePackRiskNote.risk_type")
        _require_non_empty(self.note, "EvidencePackRiskNote.note")
        _require_non_empty(self.severity, "EvidencePackRiskNote.severity")
        if self.evidence_id is not None:
            _require_non_empty(self.evidence_id, "EvidencePackRiskNote.evidence_id")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidencePackRiskNote:
        return cls(
            risk_type=str(data.get("risk_type", "")),
            note=str(data.get("note", "")),
            evidence_id=data.get("evidence_id"),
            severity=str(data.get("severity", "medium")),
        )


@dataclass(frozen=True)
class EvidencePackSourceSummary:
    source_type: str
    source_count: int
    evidence_ids: list[str] = field(default_factory=list)

    def validate(self) -> None:
        _require_non_empty(self.source_type, "EvidencePackSourceSummary.source_type")
        if not isinstance(self.source_count, int) or self.source_count < 0:
            raise ValueError("EvidencePackSourceSummary.source_count must be a non-negative integer")
        _require_string_list(self.evidence_ids, "EvidencePackSourceSummary.evidence_ids")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidencePackSourceSummary:
        return cls(
            source_type=str(data.get("source_type", "")),
            source_count=int(data.get("source_count", 0)),
            evidence_ids=[str(item) for item in data.get("evidence_ids", [])],
        )


@dataclass(frozen=True)
class EvidencePack:
    evidence_pack_id: str
    cluster_id: str
    source_signal_ids: list[str]
    evidence_ids: list[str]
    source_urls: list[str]
    summaries: list[str]
    source_types: list[str]
    topic_id: str
    confidence_values: list[float]
    source_diversity: int
    recurrence_count: int
    created_from: str
    price_signal_ids: list[str] = field(default_factory=list)
    weak_pattern_ids: list[str] = field(default_factory=list)
    kill_warning_ids: list[str] = field(default_factory=list)
    risk_notes: list[EvidencePackRiskNote] = field(default_factory=list)
    items: list[EvidencePackItem] = field(default_factory=list)
    source_summaries: list[EvidencePackSourceSummary] = field(default_factory=list)
    schema_version: str = EVIDENCE_PACK_SCHEMA_VERSION

    @property
    def id(self) -> str:
        return self.evidence_pack_id

    @property
    def is_insufficient_evidence(self) -> bool:
        return self.created_from == INSUFFICIENT_EVIDENCE_CREATED_FROM

    def validate(self) -> None:
        validate_evidence_pack(self)

    def to_dict(self) -> dict[str, Any]:
        return evidence_pack_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidencePack:
        return evidence_pack_from_dict(data)


def make_evidence_pack_id(cluster_id: str) -> str:
    _require_non_empty(cluster_id, "cluster_id")
    digest = hashlib.sha256(cluster_id.strip().encode("utf-8")).hexdigest()[:12]
    return f"evidence_pack_{digest}"


def evidence_pack_to_dict(pack: EvidencePack) -> dict[str, Any]:
    return {
        "evidence_pack_id": pack.evidence_pack_id,
        "cluster_id": pack.cluster_id,
        "source_signal_ids": list(pack.source_signal_ids),
        "evidence_ids": list(pack.evidence_ids),
        "source_urls": list(pack.source_urls),
        "summaries": list(pack.summaries),
        "source_types": list(pack.source_types),
        "topic_id": pack.topic_id,
        "confidence_values": [float(value) for value in pack.confidence_values],
        "price_signal_ids": list(pack.price_signal_ids),
        "weak_pattern_ids": list(pack.weak_pattern_ids),
        "kill_warning_ids": list(pack.kill_warning_ids),
        "source_diversity": pack.source_diversity,
        "recurrence_count": pack.recurrence_count,
        "risk_notes": [note.to_dict() for note in pack.risk_notes],
        "items": [item.to_dict() for item in pack.items],
        "source_summaries": [summary.to_dict() for summary in pack.source_summaries],
        "created_from": pack.created_from,
        "schema_version": pack.schema_version,
    }


def evidence_pack_from_dict(data: dict[str, Any]) -> EvidencePack:
    return EvidencePack(
        evidence_pack_id=str(data.get("evidence_pack_id", "")),
        cluster_id=str(data.get("cluster_id", "")),
        source_signal_ids=[str(item) for item in data.get("source_signal_ids", [])],
        evidence_ids=[str(item) for item in data.get("evidence_ids", [])],
        source_urls=[str(item) for item in data.get("source_urls", [])],
        summaries=[str(item) for item in data.get("summaries", [])],
        source_types=[str(item) for item in data.get("source_types", [])],
        topic_id=str(data.get("topic_id", "")),
        confidence_values=[float(item) for item in data.get("confidence_values", [])],
        price_signal_ids=[str(item) for item in data.get("price_signal_ids", [])],
        weak_pattern_ids=[str(item) for item in data.get("weak_pattern_ids", [])],
        kill_warning_ids=[str(item) for item in data.get("kill_warning_ids", [])],
        source_diversity=int(data.get("source_diversity", 0)),
        recurrence_count=int(data.get("recurrence_count", 0)),
        risk_notes=[EvidencePackRiskNote.from_dict(item) for item in data.get("risk_notes", [])],
        items=[EvidencePackItem.from_dict(item) for item in data.get("items", [])],
        source_summaries=[EvidencePackSourceSummary.from_dict(item) for item in data.get("source_summaries", [])],
        created_from=str(data.get("created_from", "")),
        schema_version=str(data.get("schema_version", EVIDENCE_PACK_SCHEMA_VERSION)),
    )


def normalize_evidence_pack_order(pack: EvidencePack) -> EvidencePack:
    ordered_items = sorted(pack.items, key=lambda item: (item.evidence_id, item.source_signal_id, item.source_url))
    ordered_notes = sorted(
        pack.risk_notes,
        key=lambda note: (note.severity, note.risk_type, note.evidence_id or "", note.note),
    )
    ordered_source_summaries = sorted(pack.source_summaries, key=lambda item: (item.source_type, tuple(item.evidence_ids)))
    return replace(
        pack,
        source_signal_ids=_unique_sorted(pack.source_signal_ids),
        evidence_ids=_unique_sorted(pack.evidence_ids),
        source_urls=_unique_sorted(pack.source_urls),
        summaries=sorted(pack.summaries),
        source_types=_unique_sorted(pack.source_types),
        confidence_values=sorted(float(value) for value in pack.confidence_values),
        price_signal_ids=_unique_sorted(pack.price_signal_ids),
        weak_pattern_ids=_unique_sorted(pack.weak_pattern_ids),
        kill_warning_ids=_unique_sorted(pack.kill_warning_ids),
        risk_notes=ordered_notes,
        items=ordered_items,
        source_summaries=ordered_source_summaries,
    )


def validate_evidence_pack(pack: EvidencePack) -> None:
    for field_name in ("evidence_pack_id", "cluster_id", "topic_id", "created_from", "schema_version"):
        _require_non_empty(getattr(pack, field_name), f"EvidencePack.{field_name}")
    if pack.schema_version != EVIDENCE_PACK_SCHEMA_VERSION:
        raise ValueError("EvidencePack.schema_version must be evidence_pack.v1")
    for field_name in (
        "source_signal_ids",
        "evidence_ids",
        "source_urls",
        "summaries",
        "source_types",
        "confidence_values",
        "price_signal_ids",
        "weak_pattern_ids",
        "kill_warning_ids",
    ):
        if not isinstance(getattr(pack, field_name), list):
            raise ValueError(f"EvidencePack.{field_name} must be a list")
    for field_name in (
        "source_signal_ids",
        "evidence_ids",
        "source_urls",
        "source_types",
        "price_signal_ids",
        "weak_pattern_ids",
        "kill_warning_ids",
    ):
        _require_string_list(getattr(pack, field_name), f"EvidencePack.{field_name}")
    if not pack.is_insufficient_evidence:
        if not pack.evidence_ids:
            raise ValueError("EvidencePack.evidence_ids must be non-empty unless pack is insufficient evidence")
        if not pack.source_urls:
            raise ValueError("EvidencePack.source_urls must be non-empty unless pack is insufficient evidence")
    if pack.is_insufficient_evidence and not pack.risk_notes:
        raise ValueError("EvidencePack.risk_notes must explain insufficient evidence")
    for value in pack.confidence_values:
        if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
            raise ValueError("EvidencePack.confidence_values must contain values between 0 and 1")
    if not isinstance(pack.source_diversity, int) or pack.source_diversity < 0:
        raise ValueError("EvidencePack.source_diversity must be a non-negative integer")
    if not isinstance(pack.recurrence_count, int) or pack.recurrence_count < 0:
        raise ValueError("EvidencePack.recurrence_count must be a non-negative integer")
    for item in pack.items:
        item.validate()
    for note in pack.risk_notes:
        note.validate()
    for source_summary in pack.source_summaries:
        source_summary.validate()


def _unique_sorted(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(values))


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_string_list(values: list[str], field_name: str) -> None:
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{field_name} must contain non-empty strings")
