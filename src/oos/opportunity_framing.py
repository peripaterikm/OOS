from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .ai_contracts import AI_METADATA_REQUIRED_FIELDS, AIStageStatus, PromptIdentity, build_ai_metadata
from .contradiction_detection import ContradictionReport
from .models import Signal
from .semantic_clustering import SemanticCluster
from .signal_dedup import canonical_signal_set
from .signal_understanding import SignalUnderstandingRecord


OPPORTUNITY_FRAMING_PROMPT = PromptIdentity(
    prompt_name="opportunity_framing",
    prompt_version="opportunity_framing_v1",
)
OPPORTUNITY_FRAMING_MODEL_ID = "static_opportunity_framing_provider"
EVIDENCE_MISSING_STATUS = "parked_evidence_missing"
OPPORTUNITY_CANDIDATE_STATUS = "candidate"


class OpportunityFramingProvider:
    def frame(
        self,
        *,
        clusters: List[SemanticCluster],
        signals: List[Signal],
        understanding_records: Optional[List[SignalUnderstandingRecord]] = None,
        contradiction_report: Optional[ContradictionReport] = None,
    ) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class StaticOpportunityFramingProvider(OpportunityFramingProvider):
    payload: Dict[str, Any]

    def frame(
        self,
        *,
        clusters: List[SemanticCluster],
        signals: List[Signal],
        understanding_records: Optional[List[SignalUnderstandingRecord]] = None,
        contradiction_report: Optional[ContradictionReport] = None,
    ) -> Dict[str, Any]:
        return self.payload


@dataclass(frozen=True)
class OpportunityEvidence:
    evidence_id: str
    claim: str
    source_signal_ids: List[str]
    source_cluster_id: str

    def validate(self, *, valid_signal_ids: Iterable[str], valid_cluster_ids: Iterable[str]) -> None:
        valid_signal_id_set = set(valid_signal_ids)
        valid_cluster_id_set = set(valid_cluster_ids)
        for field_name in ("evidence_id", "claim", "source_cluster_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.source_cluster_id not in valid_cluster_id_set:
            raise ValueError(f"evidence source_cluster_id contains unknown ID: {self.source_cluster_id}")
        if not self.source_signal_ids:
            raise ValueError("evidence source_signal_ids must be non-empty")
        missing_signal_ids = [signal_id for signal_id in self.source_signal_ids if signal_id not in valid_signal_id_set]
        if missing_signal_ids:
            raise ValueError(f"evidence source_signal_ids contain unknown IDs: {missing_signal_ids}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OpportunityAssumption:
    assumption_id: str
    statement: str
    reason: str

    def validate(self) -> None:
        for field_name in ("assumption_id", "statement", "reason"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class OpportunityCard:
    opportunity_id: str
    title: str
    target_user: str
    pain: str
    current_workaround: str
    why_it_matters: str
    evidence: List[OpportunityEvidence]
    urgency: str
    possible_wedge: str
    monetization_hypothesis: str
    risks: List[str]
    assumptions: List[OpportunityAssumption]
    non_obvious_angle: str
    linked_cluster_id: str
    linked_signal_ids: List[str]
    linked_canonical_signal_ids: List[str]
    confidence: float
    ai_metadata: Dict[str, Any]
    evidence_missing: bool = False
    status: str = OPPORTUNITY_CANDIDATE_STATUS
    fallback_used: bool = False
    failure_reason: str = ""

    def validate(
        self,
        *,
        valid_cluster_ids: Iterable[str],
        valid_signal_ids: Iterable[str],
        valid_canonical_signal_ids: Iterable[str],
    ) -> None:
        valid_cluster_id_set = set(valid_cluster_ids)
        valid_signal_id_set = set(valid_signal_ids)
        valid_canonical_id_set = set(valid_canonical_signal_ids)
        for field_name in (
            "opportunity_id",
            "title",
            "target_user",
            "pain",
            "current_workaround",
            "why_it_matters",
            "urgency",
            "possible_wedge",
            "monetization_hypothesis",
            "non_obvious_angle",
            "linked_cluster_id",
            "status",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.linked_cluster_id not in valid_cluster_id_set:
            raise ValueError(f"linked_cluster_id contains unknown ID: {self.linked_cluster_id}")
        if not self.linked_signal_ids:
            raise ValueError("linked_signal_ids must be non-empty")
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
        if not isinstance(self.evidence_missing, bool):
            raise ValueError("evidence_missing must be a bool")
        if not isinstance(self.fallback_used, bool):
            raise ValueError("fallback_used must be a bool")
        if self.evidence_missing:
            if self.status != EVIDENCE_MISSING_STATUS:
                raise ValueError("evidence_missing opportunities must use parked_evidence_missing status")
        elif not self.evidence:
            raise ValueError("evidence must be non-empty")
        for evidence in self.evidence:
            evidence.validate(valid_signal_ids=valid_signal_id_set, valid_cluster_ids=valid_cluster_id_set)
        for assumption in self.assumptions:
            assumption.validate()
        if not isinstance(self.risks, list):
            raise ValueError("risks must be a list")
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            if field_name not in self.ai_metadata:
                raise ValueError(f"ai_metadata missing required field: {field_name}")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["confidence"] = float(data["confidence"])
        data["evidence"] = [item.to_dict() for item in self.evidence]
        data["assumptions"] = [item.to_dict() for item in self.assumptions]
        return data


@dataclass(frozen=True)
class OpportunityFramingResult:
    opportunities: List[OpportunityCard]
    source_cluster_ids: List[str]
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
        for opportunity in self.opportunities:
            opportunity.validate(
                valid_cluster_ids=self.source_cluster_ids,
                valid_signal_ids=self.source_signal_ids,
                valid_canonical_signal_ids=self.source_canonical_signal_ids,
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "opportunities": [opportunity.to_dict() for opportunity in self.opportunities],
            "source_cluster_ids": self.source_cluster_ids,
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
    clusters: List[SemanticCluster],
    signals: List[Signal],
    understanding_records: Optional[List[SignalUnderstandingRecord]],
    contradiction_report: Optional[ContradictionReport],
) -> Dict[str, Any]:
    return {
        "clusters": [cluster.to_dict() for cluster in clusters],
        "signals": _signal_input_payload(signals),
        "understanding_record_ids": [record.signal_id for record in (understanding_records or [])],
        "contradiction_report_source_signal_ids": (
            contradiction_report.source_signal_ids if contradiction_report is not None else []
        ),
    }


def _metadata_for(
    *,
    clusters: List[SemanticCluster],
    signals: List[Signal],
    understanding_records: Optional[List[SignalUnderstandingRecord]],
    contradiction_report: Optional[ContradictionReport],
    linked_input_ids: List[str],
    fallback_used: bool,
    stage_confidence: float,
    stage_status: AIStageStatus,
    failure_reason: str = "",
) -> Dict[str, Any]:
    return build_ai_metadata(
        prompt=OPPORTUNITY_FRAMING_PROMPT,
        model_id=OPPORTUNITY_FRAMING_MODEL_ID,
        input_payload=_stage_input_payload(
            clusters=clusters,
            signals=signals,
            understanding_records=understanding_records,
            contradiction_report=contradiction_report,
        ),
        generation_mode="opportunity_framing_fallback" if fallback_used else "llm_assisted",
        linked_input_ids=linked_input_ids,
        fallback_used=fallback_used,
        stage_confidence=stage_confidence,
        stage_status=stage_status,
        failure_reason=failure_reason,
        fallback_recommendation="Park or reject opportunities missing linked evidence." if fallback_used else "",
        degraded_mode=fallback_used or stage_status == AIStageStatus.degraded,
    ).to_dict()


def _as_string_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("value must be a list")
    return [str(value).strip() for value in raw if str(value).strip()]


def _coerce_evidence(raw: Dict[str, Any]) -> OpportunityEvidence:
    return OpportunityEvidence(
        evidence_id=str(raw.get("evidence_id") or "").strip(),
        claim=str(raw.get("claim") or "").strip(),
        source_signal_ids=_as_string_list(raw.get("source_signal_ids")),
        source_cluster_id=str(raw.get("source_cluster_id") or "").strip(),
    )


def _coerce_assumption(raw: Dict[str, Any]) -> OpportunityAssumption:
    return OpportunityAssumption(
        assumption_id=str(raw.get("assumption_id") or "").strip(),
        statement=str(raw.get("statement") or "").strip(),
        reason=str(raw.get("reason") or "").strip(),
    )


def _coerce_opportunity(
    raw: Dict[str, Any],
    *,
    clusters: List[SemanticCluster],
    signals: List[Signal],
    understanding_records: Optional[List[SignalUnderstandingRecord]],
    contradiction_report: Optional[ContradictionReport],
    valid_cluster_ids: List[str],
    valid_signal_ids: List[str],
    valid_canonical_signal_ids: List[str],
) -> OpportunityCard:
    linked_signal_ids = _as_string_list(raw.get("linked_signal_ids"))
    linked_canonical_signal_ids = _as_string_list(raw.get("linked_canonical_signal_ids"))
    linked_cluster_id = str(raw.get("linked_cluster_id") or "").strip()
    evidence = [_coerce_evidence(item) for item in raw.get("evidence", []) if isinstance(item, dict)]
    assumptions = [_coerce_assumption(item) for item in raw.get("assumptions", []) if isinstance(item, dict)]
    evidence_missing = not evidence
    confidence = float(raw.get("confidence"))
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be a number between 0 and 1")
    failure_reason = "opportunity has no linked evidence" if evidence_missing else ""
    opportunity = OpportunityCard(
        opportunity_id=str(raw.get("opportunity_id") or "").strip(),
        title=str(raw.get("title") or "").strip(),
        target_user=str(raw.get("target_user") or "").strip(),
        pain=str(raw.get("pain") or "").strip(),
        current_workaround=str(raw.get("current_workaround") or "").strip(),
        why_it_matters=str(raw.get("why_it_matters") or "").strip(),
        evidence=evidence,
        urgency=str(raw.get("urgency") or "").strip(),
        possible_wedge=str(raw.get("possible_wedge") or "").strip(),
        monetization_hypothesis=str(raw.get("monetization_hypothesis") or "").strip(),
        risks=_as_string_list(raw.get("risks")),
        assumptions=assumptions,
        non_obvious_angle=str(raw.get("non_obvious_angle") or "").strip(),
        linked_cluster_id=linked_cluster_id,
        linked_signal_ids=linked_signal_ids,
        linked_canonical_signal_ids=linked_canonical_signal_ids,
        confidence=confidence,
        ai_metadata=_metadata_for(
            clusters=clusters,
            signals=signals,
            understanding_records=understanding_records,
            contradiction_report=contradiction_report,
            linked_input_ids=linked_canonical_signal_ids or linked_signal_ids,
            fallback_used=evidence_missing,
            stage_confidence=0.0 if evidence_missing else confidence,
            stage_status=AIStageStatus.degraded if evidence_missing else AIStageStatus.success,
            failure_reason=failure_reason,
        ),
        evidence_missing=evidence_missing,
        status=EVIDENCE_MISSING_STATUS if evidence_missing else OPPORTUNITY_CANDIDATE_STATUS,
        fallback_used=evidence_missing,
        failure_reason=failure_reason,
    )
    opportunity.validate(
        valid_cluster_ids=valid_cluster_ids,
        valid_signal_ids=valid_signal_ids,
        valid_canonical_signal_ids=valid_canonical_signal_ids,
    )
    return opportunity


def _fallback_result(
    *,
    clusters: List[SemanticCluster],
    signals: List[Signal],
    canonical_signals: List[Signal],
    skipped_duplicate_signal_ids: List[str],
    understanding_records: Optional[List[SignalUnderstandingRecord]],
    contradiction_report: Optional[ContradictionReport],
    failure_reason: str,
    rejected_record_errors: Optional[List[str]] = None,
) -> OpportunityFramingResult:
    source_cluster_ids = [cluster.cluster_id for cluster in clusters]
    source_signal_ids = [signal.id for signal in signals]
    source_canonical_signal_ids = [signal.id for signal in canonical_signals]
    result = OpportunityFramingResult(
        opportunities=[],
        source_cluster_ids=source_cluster_ids,
        source_signal_ids=source_signal_ids,
        source_canonical_signal_ids=source_canonical_signal_ids,
        skipped_duplicate_signal_ids=skipped_duplicate_signal_ids,
        rejected_record_errors=rejected_record_errors or [],
        fallback_used=True,
        stage_status=AIStageStatus.degraded.value,
        failure_reason=failure_reason,
        ai_metadata=_metadata_for(
            clusters=clusters,
            signals=canonical_signals,
            understanding_records=understanding_records,
            contradiction_report=contradiction_report,
            linked_input_ids=source_cluster_ids,
            fallback_used=True,
            stage_confidence=0.0,
            stage_status=AIStageStatus.degraded,
            failure_reason=failure_reason,
        ),
    )
    result.validate()
    return result


def frame_opportunities(
    *,
    clusters: List[SemanticCluster],
    signals: List[Signal],
    provider: OpportunityFramingProvider,
    understanding_records: Optional[List[SignalUnderstandingRecord]] = None,
    contradiction_report: Optional[ContradictionReport] = None,
    use_canonical_signal_set: bool = True,
) -> OpportunityFramingResult:
    canonical_signals = canonical_signal_set(signals) if use_canonical_signal_set else list(signals)
    canonical_id_set = {signal.id for signal in canonical_signals}
    skipped_duplicate_signal_ids = [signal.id for signal in signals if signal.id not in canonical_id_set]
    valid_cluster_ids = [cluster.cluster_id for cluster in clusters]
    valid_signal_ids = [signal.id for signal in signals]
    valid_canonical_signal_ids = [signal.id for signal in canonical_signals]

    try:
        raw_payload = provider.frame(
            clusters=clusters,
            signals=canonical_signals,
            understanding_records=understanding_records,
            contradiction_report=contradiction_report,
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("provider payload must be an object")
    except Exception as exc:
        return _fallback_result(
            clusters=clusters,
            signals=signals,
            canonical_signals=canonical_signals,
            skipped_duplicate_signal_ids=skipped_duplicate_signal_ids,
            understanding_records=understanding_records,
            contradiction_report=contradiction_report,
            failure_reason=str(exc),
        )

    opportunities: List[OpportunityCard] = []
    rejected_record_errors: List[str] = []
    for index, raw_opportunity in enumerate(raw_payload.get("opportunities", [])):
        try:
            if not isinstance(raw_opportunity, dict):
                raise ValueError("opportunity item must be an object")
            opportunities.append(
                _coerce_opportunity(
                    raw_opportunity,
                    clusters=clusters,
                    signals=canonical_signals,
                    understanding_records=understanding_records,
                    contradiction_report=contradiction_report,
                    valid_cluster_ids=valid_cluster_ids,
                    valid_signal_ids=valid_signal_ids,
                    valid_canonical_signal_ids=valid_canonical_signal_ids,
                )
            )
        except Exception as exc:
            rejected_record_errors.append(f"opportunities[{index}]: {exc}")

    fallback_used = bool(rejected_record_errors) or any(opportunity.evidence_missing for opportunity in opportunities)
    stage_status = AIStageStatus.degraded if fallback_used else AIStageStatus.success
    stage_confidence = min([opportunity.confidence for opportunity in opportunities] + [1.0])
    failure_reason = "; ".join(
        rejected_record_errors + [opportunity.failure_reason for opportunity in opportunities if opportunity.failure_reason]
    )
    result = OpportunityFramingResult(
        opportunities=opportunities,
        source_cluster_ids=valid_cluster_ids,
        source_signal_ids=valid_signal_ids,
        source_canonical_signal_ids=valid_canonical_signal_ids,
        skipped_duplicate_signal_ids=skipped_duplicate_signal_ids,
        rejected_record_errors=rejected_record_errors,
        fallback_used=fallback_used,
        stage_status=stage_status.value,
        failure_reason=failure_reason,
        ai_metadata=_metadata_for(
            clusters=clusters,
            signals=canonical_signals,
            understanding_records=understanding_records,
            contradiction_report=contradiction_report,
            linked_input_ids=valid_cluster_ids,
            fallback_used=fallback_used,
            stage_confidence=stage_confidence,
            stage_status=stage_status,
            failure_reason=failure_reason,
        ),
    )
    result.validate()
    return result


def write_opportunity_framing_artifacts(result: OpportunityFramingResult, artifacts_root: Path) -> Path:
    output_dir = artifacts_root / "opportunity_framing"
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.json"
    for opportunity in result.opportunities:
        opportunity_path = output_dir / f"{opportunity.opportunity_id}.json"
        opportunity_path.write_text(json.dumps(opportunity.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    index_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return index_path
