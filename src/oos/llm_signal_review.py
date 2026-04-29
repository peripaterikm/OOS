from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .llm_contracts import LLMMessage, LLMRequest
from .prompt_safety import (
    PromptSafetyPolicy,
    PromptSafetyReport,
    build_prompt_safety_envelope_message,
    build_safe_llm_request,
)


LLM_SIGNAL_REVIEW_CONTRACT_VERSION = "llm_signal_review.v1"
LLM_SIGNAL_REVIEW_TASK_TYPE = "llm_signal_review"
LLM_SIGNAL_STRENGTHS = {"low", "medium", "high"}
LLM_SIGNAL_RECOMMENDATIONS = {"advance", "review", "park", "reject"}


@dataclass(frozen=True)
class EvidenceForReview:
    evidence_id: str
    source_type: str
    source_url: str | None
    title: str
    body: str
    pain_summary: str | None = None
    current_workaround: str | None = None
    candidate_signal_type: str | None = None
    confidence: float | None = None
    scoring_breakdown: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id is required")
        if self.confidence is not None and not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("evidence confidence must be in [0.0, 1.0]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LLMSignalReviewInput:
    review_id: str
    topic_id: str
    evidence: list[EvidenceForReview]
    review_goal: str = "Review whether the evidence supports a real customer pain signal and extract JTBD statements."
    max_evidence_items: int = 5
    require_evidence_citations: bool = True
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.review_id:
            raise ValueError("review_id is required")
        if not self.topic_id:
            raise ValueError("topic_id is required")
        if self.max_evidence_items < 1:
            raise ValueError("max_evidence_items must be positive")

    def evidence_for_prompt(self) -> list[EvidenceForReview]:
        return list(self.evidence[: self.max_evidence_items])

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence"] = [item.to_dict() for item in self.evidence]
        return data


@dataclass(frozen=True)
class JTBDStatement:
    job_statement: str
    actor: str
    situation: str
    desired_outcome: str
    when: str
    want_to: str
    so_that: str
    current_workaround: str | None
    evidence_ids: list[str]
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("JTBD confidence must be in [0.0, 1.0]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LLMSignalReviewOutput:
    review_id: str
    topic_id: str
    is_valid_signal: bool
    signal_strength: str
    signal_type: str
    jtbd_statements: list[JTBDStatement]
    pain_summary: str
    implied_burden_summary: str | None
    buying_intent_summary: str | None
    evidence_ids_cited: list[str]
    evidence_cited: bool
    uncertainty: str
    reviewer_notes: list[str]
    no_invention_confirmed: bool
    relevance_score: float = 0.0
    pain_score: float = 0.0
    buying_intent_score: float = 0.0
    icp_fit_score: float = 0.0
    recommendation: str = "review"
    jtbd_extracted: bool = False

    def __post_init__(self) -> None:
        if self.signal_strength not in LLM_SIGNAL_STRENGTHS:
            raise ValueError(f"signal_strength must be one of {sorted(LLM_SIGNAL_STRENGTHS)}")
        if self.recommendation not in LLM_SIGNAL_RECOMMENDATIONS:
            raise ValueError(f"recommendation must be one of {sorted(LLM_SIGNAL_RECOMMENDATIONS)}")
        for field_name in ("relevance_score", "pain_score", "buying_intent_score", "icp_fit_score"):
            value = float(getattr(self, field_name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be in [0.0, 1.0]")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["jtbd_statements"] = [statement.to_dict() for statement in self.jtbd_statements]
        return data


@dataclass(frozen=True)
class LLMSignalReviewContract:
    contract_version: str = LLM_SIGNAL_REVIEW_CONTRACT_VERSION
    task_type: str = LLM_SIGNAL_REVIEW_TASK_TYPE
    requires_pii_redaction: bool = True
    requires_evidence_citations: bool = True
    fail_closed_on_missing_citations: bool = True
    output_format: str = "json"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_signal_review_messages(review_input: LLMSignalReviewInput) -> list[LLMMessage]:
    return [
        _system_message("signal review"),
        build_prompt_safety_envelope_message(),
        LLMMessage(role="user", content=_user_prompt(review_input, schema=_review_schema())),
    ]


def build_jtbd_review_messages(review_input: LLMSignalReviewInput) -> list[LLMMessage]:
    return [
        _system_message("JTBD extraction"),
        build_prompt_safety_envelope_message(),
        LLMMessage(role="user", content=_user_prompt(review_input, schema=_jtbd_schema())),
    ]


def build_safe_signal_review_request(
    review_input: LLMSignalReviewInput,
    policy: PromptSafetyPolicy | None = None,
) -> tuple[LLMRequest | None, PromptSafetyReport]:
    contract = LLMSignalReviewContract()
    request = LLMRequest(
        task_type=contract.task_type,
        messages=build_signal_review_messages(review_input),
        model_hint=None,
        max_input_tokens=None,
        max_output_tokens=None,
        temperature=0.0,
        metadata={
            "review_id": review_input.review_id,
            "topic_id": review_input.topic_id,
            "contract_version": contract.contract_version,
            "evidence_count": len(review_input.evidence_for_prompt()),
            "requires_evidence_citations": contract.requires_evidence_citations,
            "external_calls_made": False,
        },
    )
    return build_safe_llm_request(request, policy=policy)


def parse_signal_review_json(content: str) -> LLMSignalReviewOutput:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid signal review JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Signal review JSON must be an object")
    return _output_from_payload(payload)


def validate_signal_review_output(
    output: LLMSignalReviewOutput,
    review_input: LLMSignalReviewInput,
    contract: LLMSignalReviewContract | None = None,
) -> tuple[bool, list[str]]:
    active_contract = contract or LLMSignalReviewContract()
    errors: list[str] = []
    evidence_ids = {item.evidence_id for item in review_input.evidence}
    cited_ids = set(output.evidence_ids_cited)

    if output.review_id != review_input.review_id:
        errors.append("review_id_mismatch")
    if output.topic_id != review_input.topic_id:
        errors.append("topic_id_mismatch")
    if output.signal_strength not in LLM_SIGNAL_STRENGTHS:
        errors.append("invalid_signal_strength")
    if output.recommendation not in LLM_SIGNAL_RECOMMENDATIONS:
        errors.append("invalid_recommendation")
    if not output.no_invention_confirmed:
        errors.append("no_invention_not_confirmed")
    if active_contract.requires_evidence_citations and not output.evidence_cited:
        errors.append("evidence_cited_required")
    if active_contract.fail_closed_on_missing_citations and not output.evidence_ids_cited:
        errors.append("missing_evidence_citations")
    unknown_ids = sorted(cited_ids - evidence_ids)
    if unknown_ids:
        errors.append(f"unknown_evidence_ids:{','.join(unknown_ids)}")
    for statement in output.jtbd_statements:
        if not statement.evidence_ids:
            errors.append("jtbd_missing_evidence_ids")
        unknown_jtbd_ids = sorted(set(statement.evidence_ids) - evidence_ids)
        if unknown_jtbd_ids:
            errors.append(f"jtbd_unknown_evidence_ids:{','.join(unknown_jtbd_ids)}")
        if not 0.0 <= statement.confidence <= 1.0:
            errors.append("jtbd_confidence_out_of_range")
    for field_name in ("relevance_score", "pain_score", "buying_intent_score", "icp_fit_score"):
        if not 0.0 <= float(getattr(output, field_name)) <= 1.0:
            errors.append(f"{field_name}_out_of_range")
    return not errors, errors


def run_deterministic_mock_signal_review(review_input: LLMSignalReviewInput) -> LLMSignalReviewOutput:
    evidence = review_input.evidence_for_prompt()
    evidence_ids = [item.evidence_id for item in evidence]
    combined_text = " ".join(
        " ".join(
            value or ""
            for value in (
                item.title,
                item.body,
                item.pain_summary,
                item.current_workaround,
                item.candidate_signal_type,
            )
        )
        for item in evidence
    ).lower()
    pain_score = _term_score(
        combined_text,
        ["can't", "cannot", "hard", "difficult", "manual", "messy", "late", "broken", "spreadsheet", "workaround"],
    )
    finance_score = _term_score(
        combined_text,
        ["cash flow", "invoice", "billing", "accounting", "bookkeeping", "budget", "forecast", "balance sheet"],
    )
    marketing_score = _term_score(
        combined_text,
        ["landing page", "our services", "trusted partner", "executive summary", "marketing", "content calendar"],
    )
    workaround = _extract_workaround(evidence)
    strength = "low"
    is_valid = False
    recommendation = "review"
    if marketing_score >= 0.2 and pain_score < 0.3:
        strength = "low"
        recommendation = "reject"
    elif pain_score >= 0.45 and finance_score >= 0.3:
        strength = "high" if workaround else "medium"
        is_valid = True
        recommendation = "advance" if strength == "high" else "review"
    elif pain_score > 0.2 or finance_score > 0.2:
        strength = "medium"
        is_valid = True
        recommendation = "review"

    confidence = 0.8 if strength == "high" else 0.6 if strength == "medium" else 0.3
    jtbd = []
    if evidence_ids:
        jtbd.append(
            JTBDStatement(
                job_statement="When finance work is unclear or manual, the user wants a reliable way to understand what to do next.",
                actor="user",
                situation="finance workflow evidence under review",
                desired_outcome="make a better finance decision with less manual effort",
                when="finance work is unclear or manual",
                want_to="understand what to do next",
                so_that="they can make a better finance decision with less manual effort",
                current_workaround=workaround,
                evidence_ids=[evidence_ids[0]],
                confidence=confidence,
            )
        )
    return LLMSignalReviewOutput(
        review_id=review_input.review_id,
        topic_id=review_input.topic_id,
        is_valid_signal=is_valid,
        signal_strength=strength,
        signal_type="pain_signal" if is_valid else "needs_human_review",
        jtbd_statements=jtbd,
        pain_summary=_extract_summary(evidence) or "No strong evidence-bound pain summary.",
        implied_burden_summary="Manual review burden appears in evidence." if "manual" in combined_text else None,
        buying_intent_summary="Automation language appears in evidence." if "automate" in combined_text else None,
        evidence_ids_cited=evidence_ids[:1],
        evidence_cited=bool(evidence_ids),
        uncertainty="Deterministic mock review; future LLM review is not active.",
        reviewer_notes=["deterministic mock; no provider call", "evidence-bound output"],
        no_invention_confirmed=True,
        relevance_score=finance_score,
        pain_score=pain_score,
        buying_intent_score=_term_score(combined_text, ["looking for", "tool", "software", "automate", "alternative"]),
        icp_fit_score=0.7 if review_input.topic_id == "ai_cfo_smb" and finance_score > 0 else 0.3,
        recommendation=recommendation,
        jtbd_extracted=bool(jtbd),
    )


def _system_message(task_label: str) -> LLMMessage:
    content = "\n".join(
        [
            f"You are performing an evidence-bound {task_label}.",
            "Use only the supplied evidence items; do not invent facts, identities, sources, prices, or claims.",
            "Cite evidence IDs for every conclusion.",
            "Apply an asymmetric prior: assume the signal is weak or noisy unless the evidence proves otherwise.",
            "Distinguish real user pain from marketing, generic copy, install instructions, or product pitch text.",
            "Return structured JSON only.",
        ]
    )
    return LLMMessage(role="system", content=content)


def _user_prompt(review_input: LLMSignalReviewInput, schema: dict[str, Any]) -> str:
    payload = {
        "review_id": review_input.review_id,
        "topic_id": review_input.topic_id,
        "review_goal": review_input.review_goal,
        "require_evidence_citations": review_input.require_evidence_citations,
        "evidence_items": [item.to_dict() for item in review_input.evidence_for_prompt()],
        "requested_json_schema": schema,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def _review_schema() -> dict[str, Any]:
    return {
        "review_id": "string",
        "topic_id": "string",
        "is_valid_signal": "boolean",
        "signal_strength": "low|medium|high",
        "signal_type": "string",
        "relevance_score": "number 0..1",
        "pain_score": "number 0..1",
        "buying_intent_score": "number 0..1",
        "icp_fit_score": "number 0..1",
        "recommendation": "advance|review|park|reject",
        "jtbd_statements": [_jtbd_schema()],
        "pain_summary": "string",
        "implied_burden_summary": "string|null",
        "buying_intent_summary": "string|null",
        "evidence_ids_cited": ["evidence_id"],
        "evidence_cited": True,
        "uncertainty": "string",
        "reviewer_notes": ["string"],
        "no_invention_confirmed": True,
        "jtbd_extracted": "boolean",
    }


def _jtbd_schema() -> dict[str, Any]:
    return {
        "job_statement": "string",
        "actor": "string",
        "situation": "string",
        "desired_outcome": "string",
        "when": "string",
        "want_to": "string",
        "so_that": "string",
        "current_workaround": "string|null",
        "evidence_ids": ["evidence_id"],
        "confidence": "number 0..1",
    }


def _output_from_payload(payload: dict[str, Any]) -> LLMSignalReviewOutput:
    required = {
        "review_id",
        "topic_id",
        "is_valid_signal",
        "signal_strength",
        "signal_type",
        "jtbd_statements",
        "pain_summary",
        "evidence_ids_cited",
        "evidence_cited",
        "uncertainty",
        "reviewer_notes",
        "no_invention_confirmed",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Missing required signal review fields: {', '.join(missing)}")
    jtbd_payloads = payload.get("jtbd_statements")
    if not isinstance(jtbd_payloads, list):
        raise ValueError("jtbd_statements must be a list")
    jtbd = [_jtbd_from_payload(item) for item in jtbd_payloads]
    return LLMSignalReviewOutput(
        review_id=str(payload["review_id"]),
        topic_id=str(payload["topic_id"]),
        is_valid_signal=bool(payload["is_valid_signal"]),
        signal_strength=str(payload["signal_strength"]),
        signal_type=str(payload["signal_type"]),
        jtbd_statements=jtbd,
        pain_summary=str(payload["pain_summary"]),
        implied_burden_summary=_optional_string(payload.get("implied_burden_summary")),
        buying_intent_summary=_optional_string(payload.get("buying_intent_summary")),
        evidence_ids_cited=[str(item) for item in payload["evidence_ids_cited"]],
        evidence_cited=bool(payload["evidence_cited"]),
        uncertainty=str(payload["uncertainty"]),
        reviewer_notes=[str(item) for item in payload["reviewer_notes"]],
        no_invention_confirmed=bool(payload["no_invention_confirmed"]),
        relevance_score=float(payload.get("relevance_score", 0.0)),
        pain_score=float(payload.get("pain_score", 0.0)),
        buying_intent_score=float(payload.get("buying_intent_score", 0.0)),
        icp_fit_score=float(payload.get("icp_fit_score", 0.0)),
        recommendation=str(payload.get("recommendation", "review")),
        jtbd_extracted=bool(payload.get("jtbd_extracted", bool(jtbd))),
    )


def _jtbd_from_payload(payload: Any) -> JTBDStatement:
    if not isinstance(payload, dict):
        raise ValueError("JTBD statement must be an object")
    required = {
        "job_statement",
        "actor",
        "situation",
        "desired_outcome",
        "when",
        "want_to",
        "so_that",
        "evidence_ids",
        "confidence",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Missing required JTBD fields: {', '.join(missing)}")
    return JTBDStatement(
        job_statement=str(payload["job_statement"]),
        actor=str(payload["actor"]),
        situation=str(payload["situation"]),
        desired_outcome=str(payload["desired_outcome"]),
        when=str(payload["when"]),
        want_to=str(payload["want_to"]),
        so_that=str(payload["so_that"]),
        current_workaround=_optional_string(payload.get("current_workaround")),
        evidence_ids=[str(item) for item in payload["evidence_ids"]],
        confidence=float(payload["confidence"]),
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _term_score(text: str, terms: list[str]) -> float:
    if not terms:
        return 0.0
    hits = sum(1 for term in terms if term in text)
    return round(min(1.0, hits / 4), 2)


def _extract_workaround(evidence: list[EvidenceForReview]) -> str | None:
    for item in evidence:
        if item.current_workaround:
            return item.current_workaround
        text = f"{item.title} {item.body}".lower()
        if "spreadsheet" in text:
            return "spreadsheet"
        if "manual" in text:
            return "manual process"
    return None


def _extract_summary(evidence: list[EvidenceForReview]) -> str | None:
    for item in evidence:
        if item.pain_summary:
            return item.pain_summary
    for item in evidence:
        text = " ".join(part for part in (item.title, item.body) if part).strip()
        if text:
            return text[:240]
    return None
