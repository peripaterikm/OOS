from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .ai_contracts import AI_METADATA_REQUIRED_FIELDS, AIStageStatus, PromptIdentity, build_ai_metadata
from .models import Signal
from .signal_dedup import canonical_signal_set


SIGNAL_UNDERSTANDING_PROMPT = PromptIdentity(
    prompt_name="signal_meaning_extractor",
    prompt_version="signal_meaning_extractor_v1",
)
SIGNAL_UNDERSTANDING_MODEL_ID = "static_signal_understanding_provider"
SIGNAL_UNDERSTANDING_VALIDITY_THRESHOLD = 0.80

SIGNAL_MEANING_REQUIRED_FIELDS = [
    "actor_user_segment",
    "pain",
    "context",
    "current_workaround",
    "urgency",
    "cost_signal",
    "evidence",
    "uncertainty",
    "confidence",
]

SIGNAL_QUALITY_REQUIRED_FIELDS = [
    "specificity",
    "recurrence_potential",
    "workaround",
    "cost_signal",
    "urgency",
    "confidence",
    "explanation",
]


class SignalUnderstandingProvider:
    def extract(self, signals: List[Signal]) -> List[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class StaticSignalUnderstandingProvider(SignalUnderstandingProvider):
    payload: List[Dict[str, Any]]

    def extract(self, signals: List[Signal]) -> List[Dict[str, Any]]:
        return self.payload


@dataclass(frozen=True)
class SignalMeaning:
    actor_user_segment: str
    pain: str
    context: str
    current_workaround: str
    urgency: str
    cost_signal: str
    evidence: str
    uncertainty: str
    confidence: float

    def validate(self) -> None:
        for field_name in SIGNAL_MEANING_REQUIRED_FIELDS:
            value = getattr(self, field_name)
            if field_name == "confidence":
                if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
                    raise ValueError("meaning.confidence must be a number between 0 and 1")
            elif not isinstance(value, str) or not value.strip():
                raise ValueError(f"meaning.{field_name} must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        data = asdict(self)
        data["confidence"] = float(data["confidence"])
        return data


@dataclass(frozen=True)
class SignalQualityScore:
    specificity: int
    recurrence_potential: int
    workaround: int
    cost_signal: int
    urgency: int
    confidence: float
    explanation: str

    def validate(self) -> None:
        for field_name in ("specificity", "recurrence_potential", "workaround", "cost_signal", "urgency"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or not 0 <= value <= 5:
                raise ValueError(f"quality.{field_name} must be an integer between 0 and 5")
        if not isinstance(self.confidence, (int, float)) or not 0 <= float(self.confidence) <= 1:
            raise ValueError("quality.confidence must be a number between 0 and 1")
        if not isinstance(self.explanation, str) or not self.explanation.strip():
            raise ValueError("quality.explanation must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        data = asdict(self)
        data["confidence"] = float(data["confidence"])
        return data


@dataclass(frozen=True)
class SignalUnderstandingRecord:
    signal_id: str
    analysis_mode: str
    meaning: Optional[SignalMeaning]
    quality: Optional[SignalQualityScore]
    ai_metadata: Dict[str, Any]
    raw_signal_preserved: bool = True
    failure_reason: str = ""

    def validate(self) -> None:
        if not isinstance(self.signal_id, str) or not self.signal_id.strip():
            raise ValueError("signal_id must be a non-empty string")
        if self.analysis_mode == "structured_extraction":
            if self.meaning is None or self.quality is None:
                raise ValueError("structured_extraction requires meaning and quality")
            self.meaning.validate()
            self.quality.validate()
        elif self.analysis_mode == "analysis_unavailable":
            if not self.failure_reason.strip():
                raise ValueError("analysis_unavailable requires failure_reason")
        else:
            raise ValueError("analysis_mode must be structured_extraction or analysis_unavailable")
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "signal_id": self.signal_id,
            "analysis_mode": self.analysis_mode,
            "meaning": self.meaning.to_dict() if self.meaning is not None else None,
            "quality": self.quality.to_dict() if self.quality is not None else None,
            "ai_metadata": self.ai_metadata,
            "raw_signal_preserved": self.raw_signal_preserved,
            "failure_reason": self.failure_reason,
        }


@dataclass(frozen=True)
class SignalUnderstandingBatchResult:
    records: List[SignalUnderstandingRecord]
    processed_signal_ids: List[str]
    skipped_duplicate_signal_ids: List[str]
    valid_count: int
    total_count: int
    valid_ratio: float
    degraded_mode: bool
    stage_status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "records": [record.to_dict() for record in self.records],
            "processed_signal_ids": self.processed_signal_ids,
            "skipped_duplicate_signal_ids": self.skipped_duplicate_signal_ids,
            "valid_count": self.valid_count,
            "total_count": self.total_count,
            "valid_ratio": self.valid_ratio,
            "degraded_mode": self.degraded_mode,
            "stage_status": self.stage_status,
        }


def _signal_input_payload(signals: Iterable[Signal]) -> List[Dict[str, Any]]:
    return [
        {
            "id": signal.id,
            "source": signal.source,
            "timestamp": signal.timestamp,
            "raw_content": signal.raw_content,
            "extracted_pain": signal.extracted_pain,
            "candidate_icp": signal.candidate_icp,
        }
        for signal in signals
    ]


def _coerce_meaning(raw: Dict[str, Any]) -> SignalMeaning:
    meaning = raw.get("meaning")
    if not isinstance(meaning, dict):
        raise ValueError("meaning must be an object")
    obj = SignalMeaning(
        actor_user_segment=str(meaning.get("actor_user_segment") or "").strip(),
        pain=str(meaning.get("pain") or "").strip(),
        context=str(meaning.get("context") or "").strip(),
        current_workaround=str(meaning.get("current_workaround") or "").strip(),
        urgency=str(meaning.get("urgency") or "").strip(),
        cost_signal=str(meaning.get("cost_signal") or "").strip(),
        evidence=str(meaning.get("evidence") or "").strip(),
        uncertainty=str(meaning.get("uncertainty") or "").strip(),
        confidence=float(meaning.get("confidence")),
    )
    obj.validate()
    return obj


def _coerce_quality(raw: Dict[str, Any]) -> SignalQualityScore:
    quality = raw.get("quality")
    if not isinstance(quality, dict):
        raise ValueError("quality must be an object")
    obj = SignalQualityScore(
        specificity=int(quality.get("specificity")),
        recurrence_potential=int(quality.get("recurrence_potential")),
        workaround=int(quality.get("workaround")),
        cost_signal=int(quality.get("cost_signal")),
        urgency=int(quality.get("urgency")),
        confidence=float(quality.get("confidence")),
        explanation=str(quality.get("explanation") or "").strip(),
    )
    obj.validate()
    return obj


def _metadata_for(
    *,
    input_signals: List[Signal],
    linked_signal_id: str,
    generation_mode: str,
    fallback_used: bool,
    stage_confidence: float,
    stage_status: AIStageStatus,
    failure_reason: str = "",
) -> Dict[str, Any]:
    metadata = build_ai_metadata(
        prompt=SIGNAL_UNDERSTANDING_PROMPT,
        model_id=SIGNAL_UNDERSTANDING_MODEL_ID,
        input_payload=_signal_input_payload(input_signals),
        generation_mode=generation_mode,
        linked_input_ids=[linked_signal_id],
        fallback_used=fallback_used,
        stage_confidence=stage_confidence,
        stage_status=stage_status,
        failure_reason=failure_reason,
        fallback_recommendation=(
            "Preserve raw signal and mark analysis_unavailable for this signal."
            if fallback_used
            else ""
        ),
        degraded_mode=stage_status == AIStageStatus.degraded,
    )
    return metadata.to_dict()


def _fallback_record(*, signal: Signal, input_signals: List[Signal], failure_reason: str) -> SignalUnderstandingRecord:
    return SignalUnderstandingRecord(
        signal_id=signal.id,
        analysis_mode="analysis_unavailable",
        meaning=None,
        quality=None,
        ai_metadata=_metadata_for(
            input_signals=input_signals,
            linked_signal_id=signal.id,
            generation_mode="signal_understanding_fallback",
            fallback_used=True,
            stage_confidence=0.0,
            stage_status=AIStageStatus.degraded,
            failure_reason=failure_reason,
        ),
        raw_signal_preserved=True,
        failure_reason=failure_reason,
    )


def extract_signal_understanding(
    *,
    signals: List[Signal],
    provider: SignalUnderstandingProvider,
    use_canonical_signal_set: bool = True,
) -> SignalUnderstandingBatchResult:
    input_signals = canonical_signal_set(signals) if use_canonical_signal_set else list(signals)
    processed_ids = [signal.id for signal in input_signals]
    skipped_duplicate_ids = [signal.id for signal in signals if signal.id not in set(processed_ids)]
    by_signal = {signal.id: signal for signal in input_signals}

    raw_items_by_signal_id: Dict[str, Dict[str, Any]] = {}
    try:
        raw_items = provider.extract(input_signals)
    except Exception:
        raw_items = []
    if isinstance(raw_items, list):
        for raw_item in raw_items:
            if isinstance(raw_item, dict):
                signal_id = str(raw_item.get("signal_id") or "").strip()
                if signal_id in by_signal and signal_id not in raw_items_by_signal_id:
                    raw_items_by_signal_id[signal_id] = raw_item

    records: List[SignalUnderstandingRecord] = []
    valid_count = 0
    for signal in input_signals:
        raw_item = raw_items_by_signal_id.get(signal.id)
        if raw_item is None:
            records.append(
                _fallback_record(
                    signal=signal,
                    input_signals=input_signals,
                    failure_reason="provider returned no valid item for signal_id",
                )
            )
            continue
        try:
            meaning = _coerce_meaning(raw_item)
            quality = _coerce_quality(raw_item)
            record = SignalUnderstandingRecord(
                signal_id=signal.id,
                analysis_mode="structured_extraction",
                meaning=meaning,
                quality=quality,
                ai_metadata=_metadata_for(
                    input_signals=input_signals,
                    linked_signal_id=signal.id,
                    generation_mode="llm_assisted",
                    fallback_used=False,
                    stage_confidence=min(meaning.confidence, quality.confidence),
                    stage_status=AIStageStatus.success,
                ),
                raw_signal_preserved=True,
            )
            record.validate()
            records.append(record)
            valid_count += 1
        except Exception as exc:
            records.append(_fallback_record(signal=signal, input_signals=input_signals, failure_reason=str(exc)))

    total_count = len(input_signals)
    valid_ratio = (valid_count / total_count) if total_count else 1.0
    degraded_mode = valid_ratio < SIGNAL_UNDERSTANDING_VALIDITY_THRESHOLD
    return SignalUnderstandingBatchResult(
        records=records,
        processed_signal_ids=processed_ids,
        skipped_duplicate_signal_ids=skipped_duplicate_ids,
        valid_count=valid_count,
        total_count=total_count,
        valid_ratio=valid_ratio,
        degraded_mode=degraded_mode,
        stage_status=AIStageStatus.degraded.value if degraded_mode else AIStageStatus.success.value,
    )


def write_signal_understanding_artifacts(result: SignalUnderstandingBatchResult, artifacts_root: Path) -> Path:
    output_dir = artifacts_root / "signal_understanding"
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.json"
    for record in result.records:
        record_path = output_dir / f"{record.signal_id}.json"
        record_path.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    index_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return index_path
