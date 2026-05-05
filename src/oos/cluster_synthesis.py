from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .llm_contracts import LLMMessage, LLMRequest
from .models import CandidateSignal, ClusterSynthesis, WeakPatternCandidate
from .prompt_safety import build_prompt_safety_envelope_message


CLUSTER_SYNTHESIS_CONTRACT_VERSION = "cluster_synthesis.v1"
CLUSTER_SYNTHESIS_TASK_TYPE = "cluster_synthesis"
MIN_CLUSTER_SIGNALS = 5
MAX_CLUSTER_SIGNALS = 10


@dataclass(frozen=True)
class ClusterSignalContext:
    signal_id: str
    evidence_id: str
    source_id: str
    source_type: str
    source_url: str
    pain_summary: str
    target_user: str
    current_workaround: str
    confidence: float

    @classmethod
    def from_candidate_signal(cls, signal: CandidateSignal) -> ClusterSignalContext:
        signal.validate()
        return cls(
            signal_id=signal.signal_id,
            evidence_id=signal.evidence_id,
            source_id=signal.source_id,
            source_type=signal.source_type,
            source_url=signal.source_url,
            pain_summary=signal.pain_summary,
            target_user=signal.target_user,
            current_workaround=signal.current_workaround,
            confidence=float(signal.confidence),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClusterSynthesisInput:
    cluster_id: str
    topic_id: str
    signals: list[ClusterSignalContext]
    weak_pattern: dict[str, Any] | None = None
    synthesis_goal: str = "Summarize the evidence-supported pattern across this cluster, not an individual signal."
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.cluster_id:
            raise ValueError("cluster_id is required")
        if not self.topic_id:
            raise ValueError("topic_id is required")
        if len(self.signals) < MIN_CLUSTER_SIGNALS:
            raise ValueError("cluster synthesis requires at least 5 signals; isolated signal-only context is insufficient")
        if len(self.signals) > MAX_CLUSTER_SIGNALS:
            raise ValueError("cluster synthesis accepts at most 10 signals")

    def ordered_signals(self) -> list[ClusterSignalContext]:
        return sorted(self.signals, key=lambda item: (-float(item.confidence), item.signal_id, item.evidence_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "topic_id": self.topic_id,
            "signals": [item.to_dict() for item in self.signals],
            "weak_pattern": self.weak_pattern,
            "synthesis_goal": self.synthesis_goal,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ClusterSynthesisLLMContract:
    contract_version: str = CLUSTER_SYNTHESIS_CONTRACT_VERSION
    task_type: str = CLUSTER_SYNTHESIS_TASK_TYPE
    budget_role: str = CLUSTER_SYNTHESIS_TASK_TYPE
    requires_pii_redaction: bool = True
    requires_evidence_citations: bool = True
    requires_cluster_context: bool = True
    minimum_signal_count: int = MIN_CLUSTER_SIGNALS
    maximum_signal_count: int = MAX_CLUSTER_SIGNALS
    output_format: str = "json"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_cluster_synthesis_input(
    *,
    cluster_id: str,
    topic_id: str,
    candidate_signals: list[CandidateSignal],
    weak_pattern: WeakPatternCandidate | None = None,
) -> ClusterSynthesisInput:
    ordered = sorted(candidate_signals, key=lambda signal: (-float(signal.confidence), signal.signal_id, signal.evidence_id))
    selected = ordered[:MAX_CLUSTER_SIGNALS]
    return ClusterSynthesisInput(
        cluster_id=cluster_id,
        topic_id=topic_id,
        signals=[ClusterSignalContext.from_candidate_signal(signal) for signal in selected],
        weak_pattern=weak_pattern.to_dict() if hasattr(weak_pattern, "to_dict") else _weak_pattern_payload(weak_pattern),
        metadata={"input_signal_count": len(candidate_signals), "selected_signal_count": len(selected)},
    )


def run_deterministic_cluster_synthesis_stub(synthesis_input: ClusterSynthesisInput) -> ClusterSynthesis:
    ordered = synthesis_input.ordered_signals()
    strongest = ordered[: min(3, len(ordered))]
    evidence_ids = [item.evidence_id for item in strongest]
    summaries = [item.pain_summary.rstrip(".") for item in ordered[:2]]
    target_users = sorted({item.target_user for item in ordered if item.target_user and item.target_user != "unknown"})
    workarounds = sorted({item.current_workaround for item in ordered if item.current_workaround and item.current_workaround != "unknown"})
    avg_confidence = round(sum(float(item.confidence) for item in ordered) / len(ordered), 3)
    confidence = round(min(0.75, max(0.2, avg_confidence)), 3)

    synthesis = ClusterSynthesis(
        cluster_id=synthesis_input.cluster_id,
        emerging_pain_pattern=_join_sentence(summaries) or "Cluster contains weak, related finance pain signals.",
        strongest_evidence_ids=evidence_ids,
        icp_synthesis=", ".join(target_users[:3]) or "ICP not strongly proven by cluster evidence.",
        opportunity_sketch=_opportunity_sketch(workarounds),
        why_now_signal="Evidence is cluster-level and weak; review because related signals recur across multiple cited items.",
        confidence=confidence,
        evidence_cited=[
            {
                "evidence_id": item.evidence_id,
                "citation": item.pain_summary,
            }
            for item in strongest
        ],
        signal_ids=[item.signal_id for item in ordered],
    )
    synthesis.validate()
    return synthesis


def build_cluster_synthesis_messages(synthesis_input: ClusterSynthesisInput) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="system",
            content="\n".join(
                [
                    "You are performing cluster-level synthesis across multiple related signals.",
                    "Use the cluster as the unit of analysis; do not summarize an isolated single signal.",
                    "Use only supplied cluster evidence; do not invent market size, budgets, buyers, urgency, or product details.",
                    "Cite exact evidence IDs and evidence text for every conclusion.",
                    "Return low confidence when the cluster is weak, mixed, or ambiguous.",
                    "Return structured JSON only.",
                ]
            ),
        ),
        build_prompt_safety_envelope_message(),
        LLMMessage(role="user", content=_cluster_synthesis_user_prompt(synthesis_input)),
    ]


def build_cluster_synthesis_request(synthesis_input: ClusterSynthesisInput) -> LLMRequest:
    contract = ClusterSynthesisLLMContract()
    return LLMRequest(
        task_type=contract.task_type,
        messages=build_cluster_synthesis_messages(synthesis_input),
        model_hint=None,
        max_input_tokens=None,
        max_output_tokens=None,
        temperature=0.0,
        metadata={
            "cluster_id": synthesis_input.cluster_id,
            "topic_id": synthesis_input.topic_id,
            "contract_version": contract.contract_version,
            "budget_role": contract.budget_role,
            "evidence_count": len(synthesis_input.signals),
            "external_calls_made": False,
        },
    )


def _cluster_synthesis_user_prompt(synthesis_input: ClusterSynthesisInput) -> str:
    payload = {
        "contract": ClusterSynthesisLLMContract().to_dict(),
        "cluster_context": synthesis_input.to_dict(),
        "requested_json_schema": {
            "cluster_id": "string",
            "emerging_pain_pattern": "string",
            "strongest_evidence_ids": ["evidence_id"],
            "icp_synthesis": "string",
            "opportunity_sketch": "string",
            "why_now_signal": "string",
            "confidence": "number 0..1",
            "evidence_cited": [{"evidence_id": "string", "citation": "exact supporting text"}],
            "no_invention_confirmed": True,
        },
        "rules": [
            "Synthesize only when at least five related signals are present.",
            "Reason over the whole cluster, not one strongest signal alone.",
            "Preserve evidence IDs exactly.",
            "If evidence is weak or mixed, state uncertainty and keep confidence low.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def _weak_pattern_payload(weak_pattern: WeakPatternCandidate | None) -> dict[str, Any] | None:
    if weak_pattern is None:
        return None
    return {
        "pattern_id": weak_pattern.pattern_id,
        "classification": weak_pattern.classification,
        "review_priority": weak_pattern.review_priority,
        "signal_ids": list(weak_pattern.signal_ids),
        "evidence_ids": list(weak_pattern.evidence_ids),
        "confidence": weak_pattern.confidence,
        "summary": weak_pattern.summary,
    }


def _join_sentence(parts: list[str]) -> str:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    if not cleaned:
        return ""
    return "; ".join(cleaned) + "."


def _opportunity_sketch(workarounds: list[str]) -> str:
    if not workarounds:
        return "Potential opportunity remains unproven; founder should inspect cited evidence before ideation."
    return f"Review whether repeated workaround evidence ({'; '.join(workarounds[:2])}) points to a narrow workflow wedge."
