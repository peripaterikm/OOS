from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evidence_pack import EvidencePack, evidence_pack_from_dict
from .opportunity_sketch import UNKNOWN, OpportunityCandidate, opportunity_sketch_from_dict


EVIDENCE_SUFFICIENCY_SCHEMA_VERSION = "evidence_sufficiency_score.v1"

STRONG = "strong"
ADEQUATE = "adequate"
WEAK = "weak"
INSUFFICIENT = "insufficient"

DIMENSION_NAMES = (
    "pain_evidence_strength",
    "workaround_evidence_strength",
    "buyer_clarity",
    "willingness_to_pay_evidence",
    "recurrence_strength",
    "source_diversity_strength",
    "traceability_strength",
    "risk_penalty",
    "ambiguity_penalty",
)

PAIN_MARKERS = (
    "unpaid invoice",
    "invoice follow",
    "cash collection",
    "payment follow",
    "balance sheet",
    "month-end",
    "month end",
    "reporting",
    "sticky notes",
    "spreadsheet",
    "can't afford",
    "cannot afford",
)

WORKAROUND_MARKERS = (
    "manual",
    "follow-up",
    "follow up",
    "spreadsheet",
    "excel",
    "sticky notes",
    "email",
    "existing tool",
    "ynab",
    "quickbooks",
)

WTP_MARKERS = (
    "price",
    "budget",
    "pay",
    "paid",
    "afford",
    "too expensive",
    "overpriced",
    "subscription",
)

FATAL_RISK_MARKERS = (
    "vendor",
    "vendor_promo",
    "seo",
    "generic_accounting_copy",
    "generic accounting",
    "source_quality_issue",
    "false_positive",
    "product_submission",
)

AMBIGUITY_MARKERS = (
    "needs_human_review",
    "needs_more_evidence",
    "ambiguous",
    "insufficient",
    "duplicate",
    "weak_price_evidence",
    "weak_buyer_evidence",
)


@dataclass(frozen=True)
class EvidenceSufficiencyScore:
    total_score: float
    score_band: str
    dimension_scores: dict[str, float]
    positive_factors: list[str]
    missing_evidence: list[str]
    risk_factors: list[str]
    evidence_ids: list[str]
    source_signal_ids: list[str]
    source_urls: list[str]
    schema_version: str = EVIDENCE_SUFFICIENCY_SCHEMA_VERSION
    auto_promote: bool = False
    founder_decision_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_score": self.total_score,
            "score_band": self.score_band,
            "dimension_scores": dict(self.dimension_scores),
            "positive_factors": list(self.positive_factors),
            "missing_evidence": list(self.missing_evidence),
            "risk_factors": list(self.risk_factors),
            "evidence_ids": list(self.evidence_ids),
            "source_signal_ids": list(self.source_signal_ids),
            "source_urls": list(self.source_urls),
            "schema_version": self.schema_version,
            "auto_promote": self.auto_promote,
            "founder_decision_required": self.founder_decision_required,
        }

    def validate(self) -> None:
        validate_evidence_sufficiency_score(self)


def score_evidence_sufficiency(
    opportunity: OpportunityCandidate | dict[str, Any],
    evidence_pack: EvidencePack | dict[str, Any] | None = None,
    *,
    extra_risk_notes: list[str] | None = None,
) -> EvidenceSufficiencyScore:
    candidate = opportunity_sketch_from_dict(opportunity) if isinstance(opportunity, dict) else opportunity
    pack = evidence_pack_from_dict(evidence_pack) if isinstance(evidence_pack, dict) else evidence_pack
    if pack is not None:
        pack.validate()
        if candidate.evidence_pack_id and candidate.evidence_pack_id != pack.evidence_pack_id:
            raise ValueError("opportunity and evidence_pack must reference the same evidence_pack_id")

    evidence_ids = _ordered_strings(candidate.evidence_ids)
    source_signal_ids = _ordered_strings(candidate.source_signal_ids)
    source_urls = _ordered_strings(candidate.source_urls)
    combined_text = _combined_text(candidate, pack)
    risk_notes = _risk_notes(candidate, pack, extra_risk_notes or [])
    risk_text = " ".join(risk_notes).lower()

    dimension_scores = {
        "pain_evidence_strength": _pain_score(candidate, combined_text),
        "workaround_evidence_strength": _workaround_score(candidate, combined_text),
        "buyer_clarity": _buyer_score(candidate),
        "willingness_to_pay_evidence": _willingness_to_pay_score(candidate, pack, combined_text),
        "recurrence_strength": _recurrence_score(pack),
        "source_diversity_strength": _source_diversity_score(pack),
        "traceability_strength": _traceability_score(evidence_ids, source_signal_ids, source_urls),
        "risk_penalty": _risk_penalty(risk_text),
        "ambiguity_penalty": _ambiguity_penalty(candidate, pack, risk_text),
    }
    positive_factors = _positive_factors(dimension_scores)
    missing_evidence = _missing_evidence(candidate, pack, dimension_scores, evidence_ids, source_urls)
    risk_factors = _risk_factors(risk_notes, dimension_scores)
    total_score = _total_score(dimension_scores)
    score = EvidenceSufficiencyScore(
        total_score=total_score,
        score_band=_score_band(total_score, dimension_scores, missing_evidence),
        dimension_scores={key: round(float(dimension_scores[key]), 3) for key in DIMENSION_NAMES},
        positive_factors=positive_factors,
        missing_evidence=missing_evidence,
        risk_factors=risk_factors,
        evidence_ids=evidence_ids,
        source_signal_ids=source_signal_ids,
        source_urls=source_urls,
    )
    score.validate()
    return score


def validate_evidence_sufficiency_score(score: EvidenceSufficiencyScore) -> None:
    if score.schema_version != EVIDENCE_SUFFICIENCY_SCHEMA_VERSION:
        raise ValueError("EvidenceSufficiencyScore.schema_version must be evidence_sufficiency_score.v1")
    if score.score_band not in {STRONG, ADEQUATE, WEAK, INSUFFICIENT}:
        raise ValueError("EvidenceSufficiencyScore.score_band is invalid")
    if not 0 <= float(score.total_score) <= 1:
        raise ValueError("EvidenceSufficiencyScore.total_score must be between 0 and 1")
    missing_dimensions = sorted(set(DIMENSION_NAMES) - set(score.dimension_scores))
    if missing_dimensions:
        raise ValueError(f"dimension_scores missing dimensions: {', '.join(missing_dimensions)}")
    for name, value in score.dimension_scores.items():
        if name not in DIMENSION_NAMES:
            raise ValueError(f"unknown dimension score: {name}")
        if not 0 <= float(value) <= 1:
            raise ValueError(f"dimension score {name} must be between 0 and 1")
    if score.auto_promote:
        raise ValueError("Evidence sufficiency score must not auto-promote")
    if not score.founder_decision_required:
        raise ValueError("Founder decision authority must be preserved")
    for field_name in ("positive_factors", "missing_evidence", "risk_factors", "evidence_ids", "source_signal_ids", "source_urls"):
        values = getattr(score, field_name)
        if not isinstance(values, list):
            raise ValueError(f"EvidenceSufficiencyScore.{field_name} must be a list")
        if any(not isinstance(item, str) or not item.strip() for item in values):
            raise ValueError(f"EvidenceSufficiencyScore.{field_name} must contain non-empty strings")


def _total_score(dimensions: dict[str, float]) -> float:
    positive_weights = {
        "pain_evidence_strength": 0.18,
        "workaround_evidence_strength": 0.12,
        "buyer_clarity": 0.13,
        "willingness_to_pay_evidence": 0.11,
        "recurrence_strength": 0.1,
        "source_diversity_strength": 0.1,
        "traceability_strength": 0.16,
    }
    positive_total = sum(dimensions[name] * weight for name, weight in positive_weights.items())
    penalty = dimensions["risk_penalty"] * 0.12 + dimensions["ambiguity_penalty"] * 0.08
    return round(max(0.0, min(1.0, positive_total - penalty)), 3)


def _score_band(total_score: float, dimensions: dict[str, float], missing_evidence: list[str]) -> str:
    if "evidence_ids" in missing_evidence or "source_urls" in missing_evidence:
        return INSUFFICIENT
    if dimensions["traceability_strength"] < 0.35 or dimensions["pain_evidence_strength"] < 0.25:
        return INSUFFICIENT
    if total_score >= 0.68 and dimensions["risk_penalty"] < 0.25 and len(missing_evidence) <= 1:
        return STRONG
    if total_score >= 0.48 and dimensions["risk_penalty"] < 0.55:
        return ADEQUATE
    if total_score >= 0.28:
        return WEAK
    return INSUFFICIENT


def _pain_score(candidate: OpportunityCandidate, combined_text: str) -> float:
    problem = candidate.problem_statement.strip().lower()
    if _unknown(candidate.problem_statement) or problem in {"generic", "generic problem"}:
        return 0.0
    marker_hits = sum(1 for marker in PAIN_MARKERS if marker in combined_text)
    if marker_hits >= 2:
        return 0.9
    if marker_hits == 1:
        return 0.7
    return 0.45


def _workaround_score(candidate: OpportunityCandidate, combined_text: str) -> float:
    if _unknown(candidate.current_workaround):
        return 0.0
    marker_hits = sum(1 for marker in WORKAROUND_MARKERS if marker in combined_text)
    if marker_hits >= 2:
        return 0.9
    if marker_hits == 1:
        return 0.7
    return 0.45


def _buyer_score(candidate: OpportunityCandidate) -> float:
    if _unknown(candidate.possible_buyer) or _unknown(candidate.target_user):
        return 0.0
    buyer_text = f"{candidate.possible_buyer} {candidate.target_user}".lower()
    if any(marker in buyer_text for marker in ("small business", "smb", "owner", "operator", "finance", "bookkeeper")):
        return 0.85
    return 0.55


def _willingness_to_pay_score(candidate: OpportunityCandidate, pack: EvidencePack | None, combined_text: str) -> float:
    if pack is not None and pack.price_signal_ids:
        return 0.85
    if "price_or_budget" in candidate.unsupported_assumptions:
        return 0.0
    if any(marker in combined_text for marker in WTP_MARKERS):
        return 0.45
    return 0.2


def _recurrence_score(pack: EvidencePack | None) -> float:
    if pack is None:
        return 0.25
    if pack.recurrence_count >= 5:
        return 1.0
    if pack.recurrence_count >= 3:
        return 0.75
    if pack.recurrence_count >= 2:
        return 0.55
    if pack.recurrence_count == 1:
        return 0.25
    return 0.0


def _source_diversity_score(pack: EvidencePack | None) -> float:
    if pack is None:
        return 0.25
    if pack.source_diversity >= 3:
        return 1.0
    if pack.source_diversity == 2:
        return 0.75
    if pack.source_diversity == 1:
        return 0.3
    return 0.0


def _traceability_score(evidence_ids: list[str], source_signal_ids: list[str], source_urls: list[str]) -> float:
    parts = [
        1.0 if evidence_ids else 0.0,
        1.0 if source_signal_ids else 0.0,
        1.0 if source_urls else 0.0,
    ]
    return round(sum(parts) / len(parts), 3)


def _risk_penalty(risk_text: str) -> float:
    if any(marker in risk_text for marker in FATAL_RISK_MARKERS):
        return 1.0
    if "kill_archive" in risk_text:
        return 0.65
    if any(marker in risk_text for marker in ("source_quality", "false positive", "generic")):
        return 0.55
    return 0.0


def _ambiguity_penalty(candidate: OpportunityCandidate, pack: EvidencePack | None, risk_text: str) -> float:
    penalty = min(1.0, 0.18 * len(candidate.unsupported_assumptions))
    if any(marker in risk_text for marker in AMBIGUITY_MARKERS):
        penalty += 0.35
    if pack is not None and (pack.is_insufficient_evidence or pack.recurrence_count < 2):
        penalty += 0.25
    return round(min(1.0, penalty), 3)


def _positive_factors(dimensions: dict[str, float]) -> list[str]:
    labels = []
    for name in DIMENSION_NAMES:
        if name.endswith("_penalty"):
            continue
        if dimensions[name] >= 0.7:
            labels.append(name)
    return _ordered_strings(labels)


def _missing_evidence(
    candidate: OpportunityCandidate,
    pack: EvidencePack | None,
    dimensions: dict[str, float],
    evidence_ids: list[str],
    source_urls: list[str],
) -> list[str]:
    missing = []
    if not evidence_ids:
        missing.append("evidence_ids")
    if not source_urls:
        missing.append("source_urls")
    if dimensions["pain_evidence_strength"] < 0.25:
        missing.append("pain_evidence")
    if dimensions["workaround_evidence_strength"] < 0.25:
        missing.append("workaround_evidence")
    if dimensions["buyer_clarity"] < 0.25:
        missing.append("buyer_clarity")
    if dimensions["willingness_to_pay_evidence"] < 0.25:
        missing.append("willingness_to_pay_evidence")
    if pack is not None and pack.source_diversity < 2:
        missing.append("source_diversity")
    if pack is not None and pack.recurrence_count < 2:
        missing.append("recurrence")
    if _unknown(candidate.why_now):
        missing.append("why_now")
    return _ordered_strings(missing)


def _risk_factors(risk_notes: list[str], dimensions: dict[str, float]) -> list[str]:
    factors = []
    if dimensions["risk_penalty"] > 0:
        factors.append("risk_notes")
    if dimensions["ambiguity_penalty"] > 0:
        factors.append("unsupported_or_ambiguous_evidence")
    for note in risk_notes:
        factors.append(note)
    return _ordered_strings(factors)


def _combined_text(candidate: OpportunityCandidate, pack: EvidencePack | None) -> str:
    values = [
        candidate.problem_statement,
        candidate.target_user,
        candidate.current_workaround,
        candidate.opportunity_sketch,
        candidate.why_now,
        candidate.possible_buyer,
        candidate.product_wedge,
        " ".join(candidate.risk_notes),
    ]
    if pack is not None:
        values.extend(pack.summaries)
        values.extend(item.summary for item in pack.items)
    return " ".join(str(value) for value in values).lower()


def _risk_notes(candidate: OpportunityCandidate, pack: EvidencePack | None, extra_risk_notes: list[str]) -> list[str]:
    notes = list(candidate.risk_notes) + list(extra_risk_notes)
    if pack is not None:
        notes.extend(f"{note.risk_type}/{note.severity}: {note.note}" for note in pack.risk_notes)
    return _ordered_strings(notes)


def _unknown(value: str) -> bool:
    clean = str(value).strip().lower()
    return not clean or clean == UNKNOWN or clean in {"n/a", "none"}


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))
