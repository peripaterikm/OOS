from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .ai_contracts import AI_METADATA_REQUIRED_FIELDS, AIStageStatus, PromptIdentity, build_ai_metadata
from .models import Signal
from .signal_dedup import canonical_signal_set


SEMANTIC_CLUSTERING_PROMPT = PromptIdentity(
    prompt_name="semantic_clustering",
    prompt_version="semantic_clustering_v1",
)
SEMANTIC_CLUSTERING_MODEL_ID = "static_semantic_clustering_provider"
LOW_CONFIDENCE_CLUSTERING_THRESHOLD = 0.4


class SemanticClusteringProvider:
    def cluster(self, signals: List[Signal]) -> List[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class StaticSemanticClusteringProvider(SemanticClusteringProvider):
    payload: List[Dict[str, Any]]

    def cluster(self, signals: List[Signal]) -> List[Dict[str, Any]]:
        return self.payload


@dataclass(frozen=True)
class SemanticCluster:
    cluster_id: str
    title: str
    summary: str
    linked_signal_ids: List[str]
    linked_canonical_signal_ids: List[str]
    reasoning: str
    confidence: float
    uncertainty: str
    ai_metadata: Dict[str, Any]
    fallback_used: bool = False
    low_confidence_clustering: bool = False

    def validate(self, valid_signal_ids: Iterable[str], valid_canonical_signal_ids: Iterable[str]) -> None:
        valid_signal_id_set = set(valid_signal_ids)
        valid_canonical_id_set = set(valid_canonical_signal_ids)
        for field_name in ("cluster_id", "title", "summary", "reasoning", "uncertainty"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not self.linked_signal_ids:
            raise ValueError("linked_signal_ids must be non-empty")
        if not self.linked_canonical_signal_ids:
            raise ValueError("linked_canonical_signal_ids must be non-empty")
        missing_signal_ids = [signal_id for signal_id in self.linked_signal_ids if signal_id not in valid_signal_id_set]
        if missing_signal_ids:
            raise ValueError(f"linked_signal_ids contain unknown IDs: {missing_signal_ids}")
        missing_canonical_ids = [
            signal_id for signal_id in self.linked_canonical_signal_ids if signal_id not in valid_canonical_id_set
        ]
        if missing_canonical_ids:
            raise ValueError(f"linked_canonical_signal_ids contain unknown IDs: {missing_canonical_ids}")
        if not isinstance(self.confidence, (int, float)) or not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be a number between 0 and 1")
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["confidence"] = float(data["confidence"])
        return data


@dataclass(frozen=True)
class SemanticClusteringResult:
    clusters: List[SemanticCluster]
    processed_canonical_signal_ids: List[str]
    skipped_duplicate_signal_ids: List[str]
    low_confidence_clustering: bool
    fallback_used: bool
    stage_status: str
    failure_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clusters": [cluster.to_dict() for cluster in self.clusters],
            "processed_canonical_signal_ids": self.processed_canonical_signal_ids,
            "skipped_duplicate_signal_ids": self.skipped_duplicate_signal_ids,
            "low_confidence_clustering": self.low_confidence_clustering,
            "fallback_used": self.fallback_used,
            "stage_status": self.stage_status,
            "failure_reason": self.failure_reason,
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


def _metadata_for(
    *,
    input_signals: List[Signal],
    linked_input_ids: List[str],
    fallback_used: bool,
    stage_confidence: float,
    stage_status: AIStageStatus,
    failure_reason: str = "",
) -> Dict[str, Any]:
    return build_ai_metadata(
        prompt=SEMANTIC_CLUSTERING_PROMPT,
        model_id=SEMANTIC_CLUSTERING_MODEL_ID,
        input_payload=_signal_input_payload(input_signals),
        generation_mode="semantic_clustering_fallback" if fallback_used else "llm_assisted",
        linked_input_ids=linked_input_ids,
        fallback_used=fallback_used,
        stage_confidence=stage_confidence,
        stage_status=stage_status,
        failure_reason=failure_reason,
        fallback_recommendation=(
            "Use simple per-signal grouping and mark low_confidence_clustering."
            if fallback_used
            else ""
        ),
        degraded_mode=fallback_used or stage_status == AIStageStatus.degraded,
    ).to_dict()


def _coerce_cluster(raw: Dict[str, Any], input_signals: List[Signal]) -> SemanticCluster:
    linked_signal_ids = [str(value).strip() for value in raw.get("linked_signal_ids", [])]
    linked_canonical_signal_ids = [str(value).strip() for value in raw.get("linked_canonical_signal_ids", [])]
    confidence = float(raw.get("confidence"))
    cluster = SemanticCluster(
        cluster_id=str(raw.get("cluster_id") or "").strip(),
        title=str(raw.get("title") or "").strip(),
        summary=str(raw.get("summary") or "").strip(),
        linked_signal_ids=linked_signal_ids,
        linked_canonical_signal_ids=linked_canonical_signal_ids,
        reasoning=str(raw.get("reasoning") or "").strip(),
        confidence=confidence,
        uncertainty=str(raw.get("uncertainty") or "").strip(),
        ai_metadata=_metadata_for(
            input_signals=input_signals,
            linked_input_ids=linked_canonical_signal_ids,
            fallback_used=False,
            stage_confidence=confidence,
            stage_status=AIStageStatus.success,
        ),
    )
    valid_ids = [signal.id for signal in input_signals]
    cluster.validate(valid_signal_ids=valid_ids, valid_canonical_signal_ids=valid_ids)
    return cluster


def _fallback_clusters(input_signals: List[Signal], *, failure_reason: str) -> List[SemanticCluster]:
    clusters: List[SemanticCluster] = []
    for signal in input_signals:
        cluster = SemanticCluster(
            cluster_id=f"fallback_cluster_{signal.id}",
            title=f"Fallback grouping for {signal.id}",
            summary="Simple one-signal grouping used because semantic clustering was unavailable or low confidence.",
            linked_signal_ids=[signal.id],
            linked_canonical_signal_ids=[signal.id],
            reasoning="Fallback preserves traceability without merging unrelated signals.",
            confidence=0.0,
            uncertainty=failure_reason,
            ai_metadata=_metadata_for(
                input_signals=input_signals,
                linked_input_ids=[signal.id],
                fallback_used=True,
                stage_confidence=0.0,
                stage_status=AIStageStatus.degraded,
                failure_reason=failure_reason,
            ),
            fallback_used=True,
            low_confidence_clustering=True,
        )
        cluster.validate(valid_signal_ids=[s.id for s in input_signals], valid_canonical_signal_ids=[s.id for s in input_signals])
        clusters.append(cluster)
    return clusters


def cluster_canonical_signals(
    *,
    signals: List[Signal],
    provider: SemanticClusteringProvider,
    use_canonical_signal_set: bool = True,
) -> SemanticClusteringResult:
    input_signals = canonical_signal_set(signals) if use_canonical_signal_set else list(signals)
    processed_ids = [signal.id for signal in input_signals]
    processed_id_set = set(processed_ids)
    skipped_duplicate_ids = [signal.id for signal in signals if signal.id not in processed_id_set]

    failure_reason = ""
    clusters: List[SemanticCluster] = []
    try:
        raw_clusters = provider.cluster(input_signals)
        if not isinstance(raw_clusters, list) or not raw_clusters:
            raise ValueError("provider returned no clusters")
        for raw_cluster in raw_clusters:
            if not isinstance(raw_cluster, dict):
                raise ValueError("cluster item must be an object")
            clusters.append(_coerce_cluster(raw_cluster, input_signals))
    except Exception as exc:
        failure_reason = str(exc)
        clusters = []

    low_confidence = bool(clusters) and all(
        cluster.confidence < LOW_CONFIDENCE_CLUSTERING_THRESHOLD for cluster in clusters
    )
    if not clusters or low_confidence:
        fallback_reason = (
            "all clusters below confidence threshold"
            if low_confidence
            else failure_reason or "semantic clustering unavailable"
        )
        return SemanticClusteringResult(
            clusters=_fallback_clusters(input_signals, failure_reason=fallback_reason),
            processed_canonical_signal_ids=processed_ids,
            skipped_duplicate_signal_ids=skipped_duplicate_ids,
            low_confidence_clustering=True,
            fallback_used=True,
            stage_status=AIStageStatus.degraded.value,
            failure_reason=fallback_reason,
        )

    return SemanticClusteringResult(
        clusters=clusters,
        processed_canonical_signal_ids=processed_ids,
        skipped_duplicate_signal_ids=skipped_duplicate_ids,
        low_confidence_clustering=False,
        fallback_used=False,
        stage_status=AIStageStatus.success.value,
    )


def write_semantic_cluster_artifacts(result: SemanticClusteringResult, artifacts_root: Path) -> Path:
    output_dir = artifacts_root / "semantic_clusters"
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.json"
    for cluster in result.clusters:
        cluster_path = output_dir / f"{cluster.cluster_id}.json"
        cluster_path.write_text(json.dumps(cluster.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    index_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return index_path
