from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .ai_contracts import AI_METADATA_REQUIRED_FIELDS, AIStageStatus, PromptIdentity, build_ai_metadata
from .models import Signal
from .semantic_clustering import SemanticCluster
from .signal_dedup import canonical_signal_set
from .signal_understanding import SignalUnderstandingRecord


CONTRADICTION_DETECTION_PROMPT = PromptIdentity(
    prompt_name="contradiction_detection",
    prompt_version="contradiction_detection_v1",
)
CONTRADICTION_DETECTION_MODEL_ID = "static_contradiction_detection_provider"
CONTRADICTION_SEVERITIES = {"low", "medium", "high"}


class ContradictionDetectionProvider:
    def detect(
        self,
        *,
        signals: List[Signal],
        understanding_records: Optional[List[SignalUnderstandingRecord]] = None,
        semantic_clusters: Optional[List[SemanticCluster]] = None,
    ) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class StaticContradictionDetectionProvider(ContradictionDetectionProvider):
    payload: Dict[str, Any]

    def detect(
        self,
        *,
        signals: List[Signal],
        understanding_records: Optional[List[SignalUnderstandingRecord]] = None,
        semantic_clusters: Optional[List[SemanticCluster]] = None,
    ) -> Dict[str, Any]:
        return self.payload


@dataclass(frozen=True)
class ContradictionRecord:
    contradiction_id: str
    signal_ids: List[str]
    canonical_signal_ids: List[str]
    contradiction_type: str
    description: str
    conflicting_fields: List[str]
    evidence: List[str]
    severity: str
    confidence: float
    recommendation: str
    next_action: str
    source_signal_ids: List[str]
    source_canonical_signal_ids: List[str]

    def validate(self, *, valid_signal_ids: Iterable[str], valid_canonical_signal_ids: Iterable[str]) -> None:
        valid_signal_id_set = set(valid_signal_ids)
        valid_canonical_id_set = set(valid_canonical_signal_ids)
        for field_name in ("contradiction_id", "contradiction_type", "description", "severity", "recommendation", "next_action"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.severity not in CONTRADICTION_SEVERITIES:
            raise ValueError("severity must be low, medium, or high")
        if not self.signal_ids:
            raise ValueError("signal_ids must be non-empty")
        if not self.conflicting_fields:
            raise ValueError("conflicting_fields must be non-empty")
        if not isinstance(self.evidence, list):
            raise ValueError("evidence must be a list")
        missing_signal_ids = [signal_id for signal_id in self.signal_ids if signal_id not in valid_signal_id_set]
        if missing_signal_ids:
            raise ValueError(f"signal_ids contain unknown IDs: {missing_signal_ids}")
        missing_canonical_ids = [
            signal_id for signal_id in self.canonical_signal_ids if signal_id not in valid_canonical_id_set
        ]
        if missing_canonical_ids:
            raise ValueError(f"canonical_signal_ids contain unknown IDs: {missing_canonical_ids}")
        if not isinstance(self.confidence, (int, float)) or not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be a number between 0 and 1")
        if self.source_signal_ids != self.signal_ids:
            raise ValueError("source_signal_ids must preserve signal_ids")
        if self.source_canonical_signal_ids != self.canonical_signal_ids:
            raise ValueError("source_canonical_signal_ids must preserve canonical_signal_ids")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["confidence"] = float(data["confidence"])
        return data


@dataclass(frozen=True)
class MergeCandidate:
    merge_candidate_id: str
    signal_ids: List[str]
    canonical_signal_id: str
    reason: str
    similarity: float
    confidence: float
    recommendation: str
    do_not_auto_merge: bool
    source_signal_ids: List[str]

    def validate(self, *, valid_signal_ids: Iterable[str], valid_canonical_signal_ids: Iterable[str]) -> None:
        valid_signal_id_set = set(valid_signal_ids)
        valid_canonical_id_set = set(valid_canonical_signal_ids)
        for field_name in ("merge_candidate_id", "canonical_signal_id", "reason", "recommendation"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not self.signal_ids:
            raise ValueError("signal_ids must be non-empty")
        missing_signal_ids = [signal_id for signal_id in self.signal_ids if signal_id not in valid_signal_id_set]
        if missing_signal_ids:
            raise ValueError(f"merge candidate signal_ids contain unknown IDs: {missing_signal_ids}")
        if self.canonical_signal_id not in valid_canonical_id_set:
            raise ValueError(f"canonical_signal_id contains unknown ID: {self.canonical_signal_id}")
        for field_name in ("similarity", "confidence"):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
                raise ValueError(f"{field_name} must be a number between 0 and 1")
        if self.do_not_auto_merge is not True:
            raise ValueError("do_not_auto_merge must be true")
        if self.source_signal_ids != self.signal_ids:
            raise ValueError("source_signal_ids must preserve signal_ids")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["similarity"] = float(data["similarity"])
        data["confidence"] = float(data["confidence"])
        return data


@dataclass(frozen=True)
class ContradictionReport:
    contradictions: List[ContradictionRecord]
    merge_candidates: List[MergeCandidate]
    source_signal_ids: List[str]
    source_canonical_signal_ids: List[str]
    skipped_duplicate_signal_ids: List[str]
    rejected_record_errors: List[str]
    fallback_used: bool
    stage_status: str
    failure_reason: str
    ai_metadata: Dict[str, Any]

    def validate(self) -> None:
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")
        if self.stage_status not in {status.value for status in AIStageStatus}:
            raise ValueError("stage_status must be success, failed, or degraded")
        if not isinstance(self.fallback_used, bool):
            raise ValueError("fallback_used must be a bool")
        valid_signal_ids = set(self.source_signal_ids)
        valid_canonical_signal_ids = set(self.source_canonical_signal_ids)
        for contradiction in self.contradictions:
            contradiction.validate(valid_signal_ids=valid_signal_ids, valid_canonical_signal_ids=valid_canonical_signal_ids)
        for merge_candidate in self.merge_candidates:
            merge_candidate.validate(valid_signal_ids=valid_signal_ids, valid_canonical_signal_ids=valid_canonical_signal_ids)

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "contradictions": [contradiction.to_dict() for contradiction in self.contradictions],
            "merge_candidates": [candidate.to_dict() for candidate in self.merge_candidates],
            "source_signal_ids": self.source_signal_ids,
            "source_canonical_signal_ids": self.source_canonical_signal_ids,
            "skipped_duplicate_signal_ids": self.skipped_duplicate_signal_ids,
            "rejected_record_errors": self.rejected_record_errors,
            "fallback_used": self.fallback_used,
            "stage_status": self.stage_status,
            "failure_reason": self.failure_reason,
            "ai_metadata": self.ai_metadata,
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
            "metadata": signal.metadata,
        }
        for signal in signals
    ]


def _stage_input_payload(
    *,
    signals: List[Signal],
    understanding_records: Optional[List[SignalUnderstandingRecord]],
    semantic_clusters: Optional[List[SemanticCluster]],
) -> Dict[str, Any]:
    return {
        "signals": _signal_input_payload(signals),
        "understanding_record_ids": [
            record.signal_id for record in (understanding_records or [])
        ],
        "semantic_cluster_ids": [
            cluster.cluster_id for cluster in (semantic_clusters or [])
        ],
    }


def _metadata_for(
    *,
    signals: List[Signal],
    understanding_records: Optional[List[SignalUnderstandingRecord]],
    semantic_clusters: Optional[List[SemanticCluster]],
    linked_input_ids: List[str],
    fallback_used: bool,
    stage_confidence: float,
    stage_status: AIStageStatus,
    failure_reason: str = "",
) -> Dict[str, Any]:
    return build_ai_metadata(
        prompt=CONTRADICTION_DETECTION_PROMPT,
        model_id=CONTRADICTION_DETECTION_MODEL_ID,
        input_payload=_stage_input_payload(
            signals=signals,
            understanding_records=understanding_records,
            semantic_clusters=semantic_clusters,
        ),
        generation_mode="contradiction_detection_fallback" if fallback_used else "llm_assisted",
        linked_input_ids=linked_input_ids,
        fallback_used=fallback_used,
        stage_confidence=stage_confidence,
        stage_status=stage_status,
        failure_reason=failure_reason,
        fallback_recommendation=(
            "Preserve all signals and continue without contradiction claims."
            if fallback_used
            else ""
        ),
        degraded_mode=fallback_used or stage_status == AIStageStatus.degraded,
    ).to_dict()


def _as_string_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("value must be a list")
    return [str(value).strip() for value in raw if str(value).strip()]


def _coerce_contradiction(
    raw: Dict[str, Any],
    *,
    valid_signal_ids: List[str],
    valid_canonical_signal_ids: List[str],
) -> ContradictionRecord:
    signal_ids = _as_string_list(raw.get("signal_ids"))
    canonical_signal_ids = _as_string_list(raw.get("canonical_signal_ids"))
    record = ContradictionRecord(
        contradiction_id=str(raw.get("contradiction_id") or "").strip(),
        signal_ids=signal_ids,
        canonical_signal_ids=canonical_signal_ids,
        contradiction_type=str(raw.get("contradiction_type") or "").strip(),
        description=str(raw.get("description") or "").strip(),
        conflicting_fields=_as_string_list(raw.get("conflicting_fields")),
        evidence=_as_string_list(raw.get("evidence")),
        severity=str(raw.get("severity") or "").strip(),
        confidence=float(raw.get("confidence")),
        recommendation=str(raw.get("recommendation") or "").strip(),
        next_action=str(raw.get("next_action") or raw.get("recommendation") or "").strip(),
        source_signal_ids=signal_ids,
        source_canonical_signal_ids=canonical_signal_ids,
    )
    record.validate(valid_signal_ids=valid_signal_ids, valid_canonical_signal_ids=valid_canonical_signal_ids)
    return record


def _coerce_merge_candidate(
    raw: Dict[str, Any],
    *,
    valid_signal_ids: List[str],
    valid_canonical_signal_ids: List[str],
) -> MergeCandidate:
    signal_ids = _as_string_list(raw.get("signal_ids"))
    candidate = MergeCandidate(
        merge_candidate_id=str(raw.get("merge_candidate_id") or "").strip(),
        signal_ids=signal_ids,
        canonical_signal_id=str(raw.get("canonical_signal_id") or "").strip(),
        reason=str(raw.get("reason") or "").strip(),
        similarity=float(raw.get("similarity")),
        confidence=float(raw.get("confidence")),
        recommendation=str(raw.get("recommendation") or "").strip(),
        do_not_auto_merge=bool(raw.get("do_not_auto_merge")),
        source_signal_ids=signal_ids,
    )
    candidate.validate(valid_signal_ids=valid_signal_ids, valid_canonical_signal_ids=valid_canonical_signal_ids)
    return candidate


def _fallback_report(
    *,
    all_signals: List[Signal],
    canonical_signals: List[Signal],
    skipped_duplicate_signal_ids: List[str],
    understanding_records: Optional[List[SignalUnderstandingRecord]],
    semantic_clusters: Optional[List[SemanticCluster]],
    failure_reason: str,
    rejected_record_errors: Optional[List[str]] = None,
) -> ContradictionReport:
    source_signal_ids = [signal.id for signal in all_signals]
    source_canonical_signal_ids = [signal.id for signal in canonical_signals]
    report = ContradictionReport(
        contradictions=[],
        merge_candidates=[],
        source_signal_ids=source_signal_ids,
        source_canonical_signal_ids=source_canonical_signal_ids,
        skipped_duplicate_signal_ids=skipped_duplicate_signal_ids,
        rejected_record_errors=rejected_record_errors or [],
        fallback_used=True,
        stage_status=AIStageStatus.degraded.value,
        failure_reason=failure_reason,
        ai_metadata=_metadata_for(
            signals=canonical_signals,
            understanding_records=understanding_records,
            semantic_clusters=semantic_clusters,
            linked_input_ids=source_canonical_signal_ids,
            fallback_used=True,
            stage_confidence=0.0,
            stage_status=AIStageStatus.degraded,
            failure_reason=failure_reason,
        ),
    )
    report.validate()
    return report


def detect_contradictions(
    *,
    signals: List[Signal],
    provider: ContradictionDetectionProvider,
    understanding_records: Optional[List[SignalUnderstandingRecord]] = None,
    semantic_clusters: Optional[List[SemanticCluster]] = None,
    use_canonical_signal_set: bool = True,
) -> ContradictionReport:
    canonical_signals = canonical_signal_set(signals) if use_canonical_signal_set else list(signals)
    canonical_id_set = {signal.id for signal in canonical_signals}
    skipped_duplicate_signal_ids = [signal.id for signal in signals if signal.id not in canonical_id_set]
    valid_signal_ids = [signal.id for signal in signals]
    valid_canonical_signal_ids = [signal.id for signal in canonical_signals]

    try:
        raw_payload = provider.detect(
            signals=canonical_signals,
            understanding_records=understanding_records,
            semantic_clusters=semantic_clusters,
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("provider payload must be an object")
    except Exception as exc:
        return _fallback_report(
            all_signals=signals,
            canonical_signals=canonical_signals,
            skipped_duplicate_signal_ids=skipped_duplicate_signal_ids,
            understanding_records=understanding_records,
            semantic_clusters=semantic_clusters,
            failure_reason=str(exc),
        )

    contradictions: List[ContradictionRecord] = []
    merge_candidates: List[MergeCandidate] = []
    rejected_record_errors: List[str] = []

    for index, raw_contradiction in enumerate(raw_payload.get("contradictions", [])):
        try:
            if not isinstance(raw_contradiction, dict):
                raise ValueError("contradiction item must be an object")
            contradictions.append(
                _coerce_contradiction(
                    raw_contradiction,
                    valid_signal_ids=valid_signal_ids,
                    valid_canonical_signal_ids=valid_canonical_signal_ids,
                )
            )
        except Exception as exc:
            rejected_record_errors.append(f"contradictions[{index}]: {exc}")

    for index, raw_merge_candidate in enumerate(raw_payload.get("merge_candidates", [])):
        try:
            if not isinstance(raw_merge_candidate, dict):
                raise ValueError("merge candidate item must be an object")
            merge_candidates.append(
                _coerce_merge_candidate(
                    raw_merge_candidate,
                    valid_signal_ids=valid_signal_ids,
                    valid_canonical_signal_ids=valid_canonical_signal_ids,
                )
            )
        except Exception as exc:
            rejected_record_errors.append(f"merge_candidates[{index}]: {exc}")

    fallback_used = bool(rejected_record_errors)
    stage_status = AIStageStatus.degraded if fallback_used else AIStageStatus.success
    stage_confidence = min(
        [item.confidence for item in contradictions] + [item.confidence for item in merge_candidates] + [1.0]
    )
    failure_reason = "; ".join(rejected_record_errors)
    report = ContradictionReport(
        contradictions=contradictions,
        merge_candidates=merge_candidates,
        source_signal_ids=valid_signal_ids,
        source_canonical_signal_ids=valid_canonical_signal_ids,
        skipped_duplicate_signal_ids=skipped_duplicate_signal_ids,
        rejected_record_errors=rejected_record_errors,
        fallback_used=fallback_used,
        stage_status=stage_status.value,
        failure_reason=failure_reason,
        ai_metadata=_metadata_for(
            signals=canonical_signals,
            understanding_records=understanding_records,
            semantic_clusters=semantic_clusters,
            linked_input_ids=valid_canonical_signal_ids,
            fallback_used=fallback_used,
            stage_confidence=stage_confidence,
            stage_status=stage_status,
            failure_reason=failure_reason,
        ),
    )
    report.validate()
    return report


def write_contradiction_report_artifact(report: ContradictionReport, artifacts_root: Path) -> Path:
    output_dir = artifacts_root / "contradiction_detection"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "contradiction_report.json"
    report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path
