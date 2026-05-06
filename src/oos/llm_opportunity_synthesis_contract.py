from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .evidence_pack import EvidencePack, evidence_pack_from_dict, evidence_pack_to_dict
from .llm_contracts import LLMMessage, LLMRequest
from .opportunity_sketch import OpportunityCandidate, opportunity_sketch_from_dict, opportunity_sketch_to_dict
from .prompt_safety import build_prompt_safety_envelope_message


LLM_OPPORTUNITY_SYNTHESIS_CONTRACT_VERSION = "llm_opportunity_synthesis.v1"
LLM_OPPORTUNITY_SYNTHESIS_TASK_TYPE = "opportunity_synthesis"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class LLMOpportunitySynthesisInput:
    synthesis_id: str
    evidence_pack: EvidencePack
    baseline_candidate: OpportunityCandidate
    synthesis_goal: str = "Synthesize an advisory opportunity sketch from the supplied evidence pack and deterministic baseline only."
    founder_review_context: dict[str, object] | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.synthesis_id:
            raise ValueError("synthesis_id is required")
        self.evidence_pack.validate()
        self.baseline_candidate.validate()
        if self.evidence_pack.evidence_pack_id != self.baseline_candidate.evidence_pack_id:
            raise ValueError("baseline_candidate must reference the supplied evidence_pack")

    def to_dict(self) -> dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "evidence_pack": evidence_pack_to_dict(self.evidence_pack),
            "baseline_candidate": opportunity_sketch_to_dict(self.baseline_candidate),
            "synthesis_goal": self.synthesis_goal,
            "founder_review_context": self.founder_review_context,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class LLMOpportunitySynthesisContract:
    contract_version: str = LLM_OPPORTUNITY_SYNTHESIS_CONTRACT_VERSION
    task_type: str = LLM_OPPORTUNITY_SYNTHESIS_TASK_TYPE
    budget_role: str = LLM_OPPORTUNITY_SYNTHESIS_TASK_TYPE
    role_statement: str = "LLM is a synthesis helper only; not a judge, decision-maker, market-size estimator, or autonomous strategy generator."
    requires_pii_redaction: bool = True
    requires_evidence_pack: bool = True
    requires_baseline_candidate: bool = True
    requires_evidence_citations: bool = True
    fail_closed_on_missing_citations: bool = True
    advisory_only_required: bool = True
    output_format: str = "json"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_opportunity_synthesis_prompt(synthesis_input: LLMOpportunitySynthesisInput) -> str:
    payload = {
        "contract": LLMOpportunitySynthesisContract().to_dict(),
        "evidence_pack_context": evidence_pack_to_dict(synthesis_input.evidence_pack),
        "deterministic_baseline_candidate": opportunity_sketch_to_dict(synthesis_input.baseline_candidate),
        "founder_review_context": synthesis_input.founder_review_context,
        "requested_json_schema": opportunity_synthesis_response_schema(),
        "hard_rules": [
            "Use the EvidencePack as the source of truth; do not answer from a vague prompt.",
            "Cite evidence IDs for every substantive claim.",
            "Preserve source signal IDs and source URLs exactly.",
            "Do not invent buyer, price, market size, product, strategy, or urgency.",
            "Mark unsupported assumptions explicitly.",
            "Return low confidence when evidence is weak, generic, vendor-promo-like, duplicated, or insufficient.",
            "Keep possible_buyer, product_wedge, and why_now as unknown when unsupported.",
            "Output is advisory only and cannot promote, reject, or decide an opportunity.",
            "Return JSON only.",
        ],
        "forbidden_claims": [
            "invented buyer",
            "invented price or budget",
            "market size estimate",
            "unsupported product wedge",
            "autonomous strategy recommendation",
            "urgency not cited from evidence",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def build_opportunity_synthesis_messages(synthesis_input: LLMOpportunitySynthesisInput) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="system",
            content="\n".join(
                [
                    "You synthesize opportunity sketches from grounded OOS evidence packs.",
                    "You are a synthesis helper only; you are not a judge, not a decision-maker, not a market-size estimator, and not an autonomous strategy generator.",
                    "Use only the supplied EvidencePack and deterministic baseline candidate.",
                    "Cite evidence IDs for every substantive claim and preserve source signal IDs and source URLs.",
                    "Do not invent buyer, price, market size, product, strategy, or urgency.",
                    "Use unknown and low confidence when support is missing, weak, generic, duplicated, vendor-promo-like, or insufficient.",
                    "Return structured JSON only with advisory_only set to true.",
                ]
            ),
        ),
        build_prompt_safety_envelope_message(),
        LLMMessage(role="user", content=build_opportunity_synthesis_prompt(synthesis_input)),
    ]


def build_opportunity_synthesis_request(synthesis_input: LLMOpportunitySynthesisInput) -> LLMRequest:
    contract = LLMOpportunitySynthesisContract()
    return LLMRequest(
        task_type=contract.task_type,
        messages=build_opportunity_synthesis_messages(synthesis_input),
        model_hint=None,
        max_input_tokens=None,
        max_output_tokens=None,
        temperature=0.0,
        metadata={
            "synthesis_id": synthesis_input.synthesis_id,
            "evidence_pack_id": synthesis_input.evidence_pack.evidence_pack_id,
            "baseline_opportunity_id": synthesis_input.baseline_candidate.opportunity_id,
            "contract_version": contract.contract_version,
            "budget_role": contract.budget_role,
            "external_calls_made": False,
            "future_only": True,
        },
    )


def opportunity_synthesis_response_schema() -> dict[str, Any]:
    return {
        "problem_statement": "string",
        "target_user": "string|unknown",
        "current_workaround": "string|unknown",
        "opportunity_sketch": "string",
        "why_now": "string|unknown",
        "possible_buyer": "string|unknown",
        "product_wedge": "string|unknown",
        "evidence_ids": ["evidence_id"],
        "source_signal_ids": ["source_signal_id"],
        "source_urls": ["source_url"],
        "unsupported_assumptions": ["string"],
        "confidence": "number 0..1",
        "risk_notes": ["string"],
        "cited_evidence": [{"evidence_id": "string", "claim": "string", "citation": "exact supporting evidence"}],
        "advisory_only": True,
    }


def parse_opportunity_synthesis_response(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Opportunity synthesis response must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Opportunity synthesis response must be a JSON object")
    validate_opportunity_synthesis_response_schema(payload)
    return payload


def validate_opportunity_synthesis_response_schema(payload: dict[str, Any]) -> None:
    required = {
        "problem_statement",
        "target_user",
        "current_workaround",
        "opportunity_sketch",
        "why_now",
        "possible_buyer",
        "product_wedge",
        "evidence_ids",
        "source_signal_ids",
        "source_urls",
        "unsupported_assumptions",
        "confidence",
        "risk_notes",
        "cited_evidence",
        "advisory_only",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Missing required opportunity synthesis fields: {', '.join(missing)}")
    if payload["advisory_only"] is not True:
        raise ValueError("Opportunity synthesis response must be advisory_only=true")
    for field_name in ("evidence_ids", "source_signal_ids", "source_urls", "unsupported_assumptions", "risk_notes"):
        if not isinstance(payload[field_name], list):
            raise ValueError(f"{field_name} must be a list")
    if not payload["evidence_ids"]:
        raise ValueError("evidence_ids must be non-empty")
    if not payload["source_signal_ids"]:
        raise ValueError("source_signal_ids must be non-empty")
    if not payload["source_urls"]:
        raise ValueError("source_urls must be non-empty")
    confidence = float(payload["confidence"])
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    cited = payload["cited_evidence"]
    if not isinstance(cited, list) or not cited:
        raise ValueError("cited_evidence must be a non-empty list")
    cited_ids = set()
    for item in cited:
        if not isinstance(item, dict):
            raise ValueError("cited_evidence entries must be objects")
        evidence_id = str(item.get("evidence_id", "")).strip()
        claim = str(item.get("claim", "")).strip()
        citation = str(item.get("citation", "")).strip()
        if not evidence_id or not claim or not citation:
            raise ValueError("cited_evidence entries must include evidence_id, claim, and citation")
        cited_ids.add(evidence_id)
    missing_citations = sorted(set(str(item) for item in payload["evidence_ids"]) - cited_ids)
    if missing_citations:
        raise ValueError(f"evidence_ids missing cited_evidence entries: {', '.join(missing_citations)}")


def ensure_evidence_bound_response(
    payload: dict[str, Any],
    synthesis_input: LLMOpportunitySynthesisInput | dict[str, Any],
) -> None:
    validate_opportunity_synthesis_response_schema(payload)
    resolved_input = _input_from_dict(synthesis_input) if isinstance(synthesis_input, dict) else synthesis_input
    allowed_evidence_ids = set(resolved_input.evidence_pack.evidence_ids)
    allowed_signal_ids = set(resolved_input.evidence_pack.source_signal_ids)
    allowed_urls = set(resolved_input.evidence_pack.source_urls)
    response_evidence_ids = set(str(item) for item in payload["evidence_ids"])
    response_signal_ids = set(str(item) for item in payload["source_signal_ids"])
    response_urls = set(str(item) for item in payload["source_urls"])
    if not response_evidence_ids <= allowed_evidence_ids:
        raise ValueError("response evidence_ids must be drawn from the supplied EvidencePack")
    if not response_signal_ids <= allowed_signal_ids:
        raise ValueError("response source_signal_ids must be drawn from the supplied EvidencePack")
    if not response_urls <= allowed_urls:
        raise ValueError("response source_urls must be drawn from the supplied EvidencePack")
    cited_ids = {str(item["evidence_id"]) for item in payload["cited_evidence"]}
    if not cited_ids <= allowed_evidence_ids:
        raise ValueError("cited_evidence IDs must be drawn from the supplied EvidencePack")
    if _contains_high_risk_context(resolved_input) and float(payload["confidence"]) > 0.55:
        raise ValueError("weak, generic, vendor, duplicated, or insufficient evidence must keep confidence low")


def _input_from_dict(data: dict[str, Any]) -> LLMOpportunitySynthesisInput:
    return LLMOpportunitySynthesisInput(
        synthesis_id=str(data.get("synthesis_id", "")),
        evidence_pack=evidence_pack_from_dict(data.get("evidence_pack", {})),
        baseline_candidate=opportunity_sketch_from_dict(data.get("baseline_candidate", {})),
        synthesis_goal=str(data.get("synthesis_goal", "")),
        founder_review_context=data.get("founder_review_context"),
        metadata=dict(data.get("metadata", {})),
    )


def _contains_high_risk_context(synthesis_input: LLMOpportunitySynthesisInput) -> bool:
    risk_text = " ".join(
        [note.note for note in synthesis_input.evidence_pack.risk_notes]
        + list(synthesis_input.baseline_candidate.risk_notes)
        + list(synthesis_input.baseline_candidate.unsupported_assumptions)
    ).lower()
    markers = (
        "weak",
        "generic",
        "vendor",
        "promo",
        "duplicate",
        "duplicated",
        "insufficient",
        "source_quality_issue",
        "needs_human_review",
    )
    return any(marker in risk_text for marker in markers) or synthesis_input.evidence_pack.is_insufficient_evidence
