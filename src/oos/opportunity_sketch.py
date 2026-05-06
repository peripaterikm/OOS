from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from .evidence_pack import EvidencePack, evidence_pack_from_dict


OPPORTUNITY_SKETCH_SCHEMA_VERSION = "opportunity_sketch.v1"
OPPORTUNITY_SKETCH_CREATED_FROM = "deterministic_evidence_pack_baseline.v1"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class OpportunityCandidate:
    opportunity_id: str
    evidence_pack_id: str
    cluster_id: str
    problem_statement: str
    target_user: str
    current_workaround: str
    opportunity_sketch: str
    why_now: str
    possible_buyer: str
    product_wedge: str
    evidence_ids: list[str]
    source_signal_ids: list[str]
    source_urls: list[str]
    unsupported_assumptions: list[str]
    confidence: float
    risk_notes: list[str]
    created_from: str = OPPORTUNITY_SKETCH_CREATED_FROM
    schema_version: str = OPPORTUNITY_SKETCH_SCHEMA_VERSION

    @property
    def id(self) -> str:
        return self.opportunity_id

    def validate(self) -> None:
        validate_opportunity_sketch(self)

    def to_dict(self) -> dict[str, Any]:
        return opportunity_sketch_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpportunityCandidate:
        return opportunity_sketch_from_dict(data)


def make_opportunity_id(evidence_pack_id: str) -> str:
    _require_non_empty(evidence_pack_id, "evidence_pack_id")
    digest = hashlib.sha256(evidence_pack_id.strip().encode("utf-8")).hexdigest()[:12]
    return f"opportunity_{digest}"


def build_opportunity_sketch_from_evidence_pack(pack: EvidencePack | dict[str, Any]) -> OpportunityCandidate:
    evidence_pack = evidence_pack_from_dict(pack) if isinstance(pack, dict) else pack
    evidence_pack.validate()
    summaries = _ordered_strings(evidence_pack.summaries)
    combined_text = " ".join(summaries).lower()
    risk_notes = _risk_notes(evidence_pack)
    problem_statement = _problem_statement(evidence_pack.cluster_id, summaries, combined_text)
    target_user = _target_user(combined_text)
    current_workaround = _current_workaround(combined_text)
    why_now = _why_now(evidence_pack, combined_text)
    possible_buyer = target_user
    product_wedge = _product_wedge(combined_text)
    unsupported = _unsupported_assumptions(
        target_user=target_user,
        possible_buyer=possible_buyer,
        product_wedge=product_wedge,
        why_now=why_now,
        price_signal_ids=evidence_pack.price_signal_ids,
    )
    sketch_text = _opportunity_sketch(problem_statement, current_workaround, product_wedge)
    candidate = OpportunityCandidate(
        opportunity_id=make_opportunity_id(evidence_pack.evidence_pack_id),
        evidence_pack_id=evidence_pack.evidence_pack_id,
        cluster_id=evidence_pack.cluster_id,
        problem_statement=problem_statement,
        target_user=target_user,
        current_workaround=current_workaround,
        opportunity_sketch=sketch_text,
        why_now=why_now,
        possible_buyer=possible_buyer,
        product_wedge=product_wedge,
        evidence_ids=_ordered_strings(evidence_pack.evidence_ids),
        source_signal_ids=_ordered_strings(evidence_pack.source_signal_ids),
        source_urls=_ordered_strings(evidence_pack.source_urls),
        unsupported_assumptions=unsupported,
        confidence=_confidence(evidence_pack, unsupported, risk_notes),
        risk_notes=risk_notes,
    )
    normalized = normalize_opportunity_sketch_order(candidate)
    normalized.validate()
    return normalized


def opportunity_sketch_to_dict(candidate: OpportunityCandidate) -> dict[str, Any]:
    return asdict(candidate)


def opportunity_sketch_from_dict(data: dict[str, Any]) -> OpportunityCandidate:
    return OpportunityCandidate(
        opportunity_id=str(data.get("opportunity_id", "")),
        evidence_pack_id=str(data.get("evidence_pack_id", "")),
        cluster_id=str(data.get("cluster_id", "")),
        problem_statement=str(data.get("problem_statement", "")),
        target_user=str(data.get("target_user", UNKNOWN)),
        current_workaround=str(data.get("current_workaround", UNKNOWN)),
        opportunity_sketch=str(data.get("opportunity_sketch", "")),
        why_now=str(data.get("why_now", UNKNOWN)),
        possible_buyer=str(data.get("possible_buyer", UNKNOWN)),
        product_wedge=str(data.get("product_wedge", UNKNOWN)),
        evidence_ids=[str(item) for item in data.get("evidence_ids", [])],
        source_signal_ids=[str(item) for item in data.get("source_signal_ids", [])],
        source_urls=[str(item) for item in data.get("source_urls", [])],
        unsupported_assumptions=[str(item) for item in data.get("unsupported_assumptions", [])],
        confidence=float(data.get("confidence", 0.0)),
        risk_notes=[str(item) for item in data.get("risk_notes", [])],
        created_from=str(data.get("created_from", OPPORTUNITY_SKETCH_CREATED_FROM)),
        schema_version=str(data.get("schema_version", OPPORTUNITY_SKETCH_SCHEMA_VERSION)),
    )


def normalize_opportunity_sketch_order(candidate: OpportunityCandidate) -> OpportunityCandidate:
    return replace(
        candidate,
        evidence_ids=_ordered_strings(candidate.evidence_ids),
        source_signal_ids=_ordered_strings(candidate.source_signal_ids),
        source_urls=_ordered_strings(candidate.source_urls),
        unsupported_assumptions=_ordered_strings(candidate.unsupported_assumptions),
        risk_notes=_ordered_strings(candidate.risk_notes),
    )


def validate_opportunity_sketch(candidate: OpportunityCandidate) -> None:
    for field_name in (
        "opportunity_id",
        "evidence_pack_id",
        "cluster_id",
        "problem_statement",
        "target_user",
        "current_workaround",
        "opportunity_sketch",
        "why_now",
        "possible_buyer",
        "product_wedge",
        "created_from",
        "schema_version",
    ):
        _require_non_empty(getattr(candidate, field_name), f"OpportunityCandidate.{field_name}")
    if candidate.schema_version != OPPORTUNITY_SKETCH_SCHEMA_VERSION:
        raise ValueError("OpportunityCandidate.schema_version must be opportunity_sketch.v1")
    for field_name in ("evidence_ids", "source_signal_ids", "source_urls", "unsupported_assumptions", "risk_notes"):
        if not isinstance(getattr(candidate, field_name), list):
            raise ValueError(f"OpportunityCandidate.{field_name} must be a list")
        _require_string_list(getattr(candidate, field_name), f"OpportunityCandidate.{field_name}")
    if not candidate.evidence_ids:
        raise ValueError("OpportunityCandidate.evidence_ids must preserve source evidence IDs")
    if not candidate.source_signal_ids:
        raise ValueError("OpportunityCandidate.source_signal_ids must preserve source signal IDs")
    if not candidate.source_urls:
        raise ValueError("OpportunityCandidate.source_urls must preserve source URLs")
    if not 0 <= float(candidate.confidence) <= 1:
        raise ValueError("OpportunityCandidate.confidence must be between 0 and 1")


def _problem_statement(cluster_id: str, summaries: list[str], combined_text: str) -> str:
    if any(term in combined_text for term in ("unpaid invoice", "invoice follow", "cash collection", "payment follow")):
        return "SMB operators have recurring cash-collection pain around unpaid invoice follow-up."
    if any(term in combined_text for term in ("balance sheet", "month-end", "month end", "historical balance")):
        return "Finance users need clearer month-end and balance-sheet reporting from existing accounting records."
    if summaries:
        return _compact_sentence(summaries[0])
    return f"Evidence pack `{cluster_id}` does not contain enough summary text to state a problem."


def _target_user(combined_text: str) -> str:
    if any(term in combined_text for term in ("small business", "smb", "business owner", "operator")):
        return "small business operator"
    if any(term in combined_text for term in ("finance user", "accounting user", "bookkeeper", "bookkeeping")):
        return "finance or bookkeeping user"
    return UNKNOWN


def _current_workaround(combined_text: str) -> str:
    matches = []
    for label, terms in (
        ("manual follow-up", ("manual", "follow-up", "follow up")),
        ("spreadsheet", ("spreadsheet", "excel")),
        ("sticky notes", ("sticky notes",)),
        ("email", ("email",)),
        ("existing tool/service", ("ynab", "quickbooks", "bookkeeping service", "accounting software")),
    ):
        if any(term in combined_text for term in terms):
            matches.append(label)
    if not matches:
        return UNKNOWN
    return "; ".join(_ordered_strings(matches))


def _why_now(pack: EvidencePack, combined_text: str) -> str:
    if any(term in combined_text for term in ("urgent", "deadline", "overdue", "unpaid", "month-end", "month end")):
        return "Evidence includes timing-sensitive finance workflow language."
    if pack.recurrence_count >= 3 or pack.source_diversity >= 2:
        return "Evidence recurs across multiple items or source types."
    return UNKNOWN


def _product_wedge(combined_text: str) -> str:
    if any(term in combined_text for term in ("balance sheet", "month-end", "month end", "reporting", "historical balance")):
        return "reporting workflow support"
    return UNKNOWN


def _opportunity_sketch(problem_statement: str, current_workaround: str, product_wedge: str) -> str:
    parts = [f"Evidence-bound baseline: {problem_statement}"]
    if current_workaround != UNKNOWN:
        parts.append(f"Current workaround evidence: {current_workaround}.")
    if product_wedge != UNKNOWN:
        parts.append(f"Possible wedge explicitly supported by evidence: {product_wedge}.")
    else:
        parts.append("No product wedge is asserted without further evidence.")
    return " ".join(parts)


def _unsupported_assumptions(
    *,
    target_user: str,
    possible_buyer: str,
    product_wedge: str,
    why_now: str,
    price_signal_ids: list[str],
) -> list[str]:
    assumptions = []
    if target_user == UNKNOWN or possible_buyer == UNKNOWN:
        assumptions.append("buyer")
    if product_wedge == UNKNOWN:
        assumptions.append("product_wedge")
    if why_now == UNKNOWN:
        assumptions.append("why_now")
    if not price_signal_ids:
        assumptions.append("price_or_budget")
    return _ordered_strings(assumptions)


def _risk_notes(pack: EvidencePack) -> list[str]:
    notes = []
    for note in pack.risk_notes:
        prefix = f"{note.risk_type}/{note.severity}"
        if note.evidence_id:
            prefix = f"{prefix}/{note.evidence_id}"
        notes.append(f"{prefix}: {note.note}")
    for price_signal_id in pack.price_signal_ids:
        notes.append(f"linked_price_signal: {price_signal_id}")
    for weak_pattern_id in pack.weak_pattern_ids:
        notes.append(f"linked_weak_pattern: {weak_pattern_id}")
    for kill_warning_id in pack.kill_warning_ids:
        notes.append(f"linked_kill_warning: {kill_warning_id}")
    return _ordered_strings(notes)


def _confidence(pack: EvidencePack, unsupported_assumptions: list[str], risk_notes: list[str]) -> float:
    base = sum(float(value) for value in pack.confidence_values) / max(1, len(pack.confidence_values))
    if pack.is_insufficient_evidence:
        base = min(base, 0.25)
    if pack.recurrence_count < 2:
        base = min(base, 0.35)
    penalty = 0.03 * len(unsupported_assumptions)
    lower_risks = " ".join(risk_notes).lower()
    if any(term in lower_risks for term in ("source_quality_issue", "vendor", "generic", "kill_archive_warning")):
        penalty += 0.12
    if "insufficient_evidence" in lower_risks or "insufficient_evidence_count" in lower_risks:
        penalty += 0.12
    return round(max(0.0, min(0.85, base - penalty)), 3)


def _compact_sentence(value: str) -> str:
    clean = " ".join(str(value).split())
    if not clean:
        return UNKNOWN
    if len(clean) <= 180:
        return clean
    return clean[:177].rstrip() + "..."


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_string_list(values: list[str], field_name: str) -> None:
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{field_name} must contain non-empty strings")
