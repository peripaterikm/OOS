from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .evidence_pack import EvidencePack, evidence_pack_from_dict
from .llm_opportunity_synthesis_contract import (
    LLM_OPPORTUNITY_SYNTHESIS_TASK_TYPE,
    LLMOpportunitySynthesisInput,
    build_opportunity_synthesis_request,
    ensure_evidence_bound_response,
    parse_opportunity_synthesis_response,
)
from .opportunity_sketch import (
    UNKNOWN,
    OpportunityCandidate,
    build_opportunity_sketch_from_evidence_pack,
    opportunity_sketch_to_dict,
)


OPPORTUNITY_SYNTHESIS_DRY_RUN_SCHEMA_VERSION = "llm_opportunity_synthesis_dry_run.v1"
OFFLINE_MOCK_PROVIDER_USED = "deterministic_mock_contract_only"
DEFAULT_LIMITATIONS = [
    "Offline dry-run only.",
    "Deterministic mock synthesis only.",
    "No live provider calls.",
    "No live internet/API calls.",
    "No founder decision or quality gate execution.",
]


@dataclass(frozen=True)
class OpportunitySynthesisDryRunResult:
    dry_run_id: str
    evidence_pack_id: str
    baseline_opportunity_id: str
    request_role: str
    prompt_hash: str
    prompt_preview: str
    mock_response_valid: bool
    evidence_bound_check_passed: bool
    unsupported_assumptions: list[str]
    confidence: float
    risk_notes: list[str]
    cited_evidence_ids: list[str]
    mock_response: dict[str, Any]
    no_live_provider_call: bool = True
    external_calls_made: bool = False
    provider_used: str = OFFLINE_MOCK_PROVIDER_USED
    schema_version: str = OPPORTUNITY_SYNTHESIS_DRY_RUN_SCHEMA_VERSION
    validation_errors: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=lambda: list(DEFAULT_LIMITATIONS))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self) -> None:
        validate_offline_opportunity_synthesis_result(self)


def run_offline_opportunity_synthesis_dry_run(
    evidence_pack: EvidencePack | dict[str, Any],
    *,
    dry_run_id: str = "offline_opportunity_synthesis_dry_run_001",
) -> OpportunitySynthesisDryRunResult:
    pack = evidence_pack_from_dict(evidence_pack) if isinstance(evidence_pack, dict) else evidence_pack
    pack.validate()
    baseline = build_opportunity_sketch_from_evidence_pack(pack)
    synthesis_input = LLMOpportunitySynthesisInput(
        synthesis_id=_synthesis_id(dry_run_id, pack.evidence_pack_id),
        evidence_pack=pack,
        baseline_candidate=baseline,
        metadata={"offline_dry_run": True, "no_live_provider_call": True},
    )
    request = build_opportunity_synthesis_request(synthesis_input)
    prompt_text = "\n".join(message.content for message in request.messages)
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16]
    response = build_mock_opportunity_synthesis_response(synthesis_input)
    validation_errors: list[str] = []
    parsed_response: dict[str, Any] = {}
    mock_response_valid = False
    evidence_bound_check_passed = False

    try:
        parsed_response = parse_opportunity_synthesis_response(json.dumps(response, ensure_ascii=False, sort_keys=True))
        mock_response_valid = True
        ensure_evidence_bound_response(parsed_response, synthesis_input)
        evidence_bound_check_passed = True
    except ValueError as exc:
        validation_errors.append(str(exc))
        parsed_response = response

    result = OpportunitySynthesisDryRunResult(
        dry_run_id=dry_run_id,
        evidence_pack_id=pack.evidence_pack_id,
        baseline_opportunity_id=baseline.opportunity_id,
        request_role=str(request.metadata.get("budget_role") or request.task_type),
        prompt_hash=prompt_hash,
        prompt_preview=" ".join(prompt_text.split())[:240],
        mock_response_valid=mock_response_valid,
        evidence_bound_check_passed=evidence_bound_check_passed,
        unsupported_assumptions=list(parsed_response.get("unsupported_assumptions", baseline.unsupported_assumptions)),
        confidence=float(parsed_response.get("confidence", baseline.confidence)),
        risk_notes=list(parsed_response.get("risk_notes", baseline.risk_notes)),
        cited_evidence_ids=_ordered_strings([item.get("evidence_id", "") for item in parsed_response.get("cited_evidence", [])]),
        mock_response=parsed_response,
        validation_errors=validation_errors,
    )
    result.validate()
    return result


def build_mock_opportunity_synthesis_response(synthesis_input: LLMOpportunitySynthesisInput) -> dict[str, Any]:
    pack = synthesis_input.evidence_pack
    baseline = synthesis_input.baseline_candidate
    summaries_by_id = _summaries_by_evidence_id(pack)
    selected_evidence_ids = _ordered_strings(pack.evidence_ids)[: max(1, min(3, len(pack.evidence_ids)))]
    cited = [
        {
            "evidence_id": evidence_id,
            "claim": _claim_for_evidence(evidence_id, baseline),
            "citation": summaries_by_id.get(evidence_id) or _summary_for_index(pack, selected_evidence_ids.index(evidence_id)),
        }
        for evidence_id in selected_evidence_ids
    ]
    high_risk = _is_high_risk(pack, baseline)
    confidence = _mock_confidence(pack, baseline, high_risk)
    return {
        "problem_statement": baseline.problem_statement,
        "target_user": baseline.target_user if not high_risk or baseline.target_user != UNKNOWN else UNKNOWN,
        "current_workaround": baseline.current_workaround,
        "opportunity_sketch": baseline.opportunity_sketch,
        "why_now": baseline.why_now if baseline.why_now != UNKNOWN and not pack.is_insufficient_evidence else UNKNOWN,
        "possible_buyer": baseline.possible_buyer if baseline.possible_buyer != UNKNOWN and not high_risk else UNKNOWN,
        "product_wedge": baseline.product_wedge if baseline.product_wedge != UNKNOWN and not high_risk else UNKNOWN,
        "evidence_ids": selected_evidence_ids,
        "source_signal_ids": _ordered_strings(pack.source_signal_ids),
        "source_urls": _ordered_strings(pack.source_urls),
        "unsupported_assumptions": _unsupported_assumptions(baseline, high_risk=high_risk, insufficient=pack.is_insufficient_evidence),
        "confidence": confidence,
        "risk_notes": _risk_notes(baseline, high_risk=high_risk, insufficient=pack.is_insufficient_evidence),
        "cited_evidence": cited,
        "advisory_only": True,
    }


def validate_offline_opportunity_synthesis_result(result: OpportunitySynthesisDryRunResult) -> None:
    for field_name in ("dry_run_id", "evidence_pack_id", "baseline_opportunity_id", "request_role", "prompt_hash", "schema_version"):
        _require_non_empty(getattr(result, field_name), f"OpportunitySynthesisDryRunResult.{field_name}")
    if result.schema_version != OPPORTUNITY_SYNTHESIS_DRY_RUN_SCHEMA_VERSION:
        raise ValueError("OpportunitySynthesisDryRunResult.schema_version must be llm_opportunity_synthesis_dry_run.v1")
    if result.request_role != LLM_OPPORTUNITY_SYNTHESIS_TASK_TYPE:
        raise ValueError("request_role must be opportunity_synthesis")
    if result.no_live_provider_call is not True:
        raise ValueError("no_live_provider_call must be true")
    if result.external_calls_made:
        raise ValueError("external_calls_made must be false")
    if not 0 <= float(result.confidence) <= 1:
        raise ValueError("confidence must be between 0 and 1")
    for field_name in ("unsupported_assumptions", "risk_notes", "cited_evidence_ids", "limitations", "validation_errors"):
        if not isinstance(getattr(result, field_name), list):
            raise ValueError(f"{field_name} must be a list")
    if result.mock_response_valid and not result.evidence_bound_check_passed:
        raise ValueError("valid mock response must pass evidence-bound checks")


def _synthesis_id(dry_run_id: str, evidence_pack_id: str) -> str:
    return f"opportunity_synthesis_{_safe_id(dry_run_id)}_{_safe_id(evidence_pack_id)}"


def _summaries_by_evidence_id(pack: EvidencePack) -> dict[str, str]:
    result = {item.evidence_id: item.summary for item in pack.items if item.evidence_id and item.summary}
    for index, evidence_id in enumerate(pack.evidence_ids):
        result.setdefault(evidence_id, _summary_for_index(pack, index))
    return result


def _summary_for_index(pack: EvidencePack, index: int) -> str:
    if not pack.summaries:
        return "No summary supplied."
    return pack.summaries[index % len(pack.summaries)]


def _claim_for_evidence(evidence_id: str, baseline: OpportunityCandidate) -> str:
    lower = f"{baseline.problem_statement} {baseline.current_workaround}".lower()
    if "cash" in lower or "invoice" in lower:
        return "cash-collection pain evidence"
    if "balance" in lower or "report" in lower:
        return "finance reporting pain evidence"
    return f"evidence-supported claim for {evidence_id}"


def _mock_confidence(pack: EvidencePack, baseline: OpportunityCandidate, high_risk: bool) -> float:
    confidence = min(0.72, max(0.1, float(baseline.confidence) + 0.04))
    if pack.is_insufficient_evidence:
        confidence = min(confidence, 0.25)
    elif high_risk:
        confidence = min(confidence, 0.45)
    return round(confidence, 3)


def _unsupported_assumptions(baseline: OpportunityCandidate, *, high_risk: bool, insufficient: bool) -> list[str]:
    assumptions = list(baseline.unsupported_assumptions)
    if high_risk and "buyer" not in assumptions:
        assumptions.append("buyer")
    if high_risk and "product_wedge" not in assumptions:
        assumptions.append("product_wedge")
    if insufficient and "insufficient_evidence" not in assumptions:
        assumptions.append("insufficient_evidence")
    return _ordered_strings(assumptions)


def _risk_notes(baseline: OpportunityCandidate, *, high_risk: bool, insufficient: bool) -> list[str]:
    notes = list(baseline.risk_notes)
    if high_risk:
        notes.append("offline_mock_guardrail: weak/generic/vendor-like evidence kept low confidence")
    if insufficient:
        notes.append("offline_mock_guardrail: insufficient evidence cannot support synthesis confidence")
    return _ordered_strings(notes)


def _is_high_risk(pack: EvidencePack, baseline: OpportunityCandidate) -> bool:
    risk_text = " ".join([note.note for note in pack.risk_notes] + baseline.risk_notes).lower()
    markers = ("generic", "vendor", "promo", "source_quality_issue", "duplicate", "insufficient", "needs_human_review")
    return pack.is_insufficient_evidence or any(marker in risk_text for marker in markers)


def _safe_id(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value.strip()).strip("_")
    return safe or "unknown"


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
