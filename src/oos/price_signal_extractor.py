from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .llm_contracts import LLMMessage
from .models import CleanedEvidence, PriceSignal
from .prompt_safety import build_prompt_safety_envelope_message


PRICE_SIGNAL_CONTRACT_VERSION = "price_signal_extraction.v1"
PRICE_SIGNAL_TASK_TYPE = "price_signal_extraction"

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_DOLLAR_AMOUNT_RE = re.compile(
    r"\b(?:USD|US\$)\s*\d[\d,]*(?:\.\d{1,2})?\s*(?:/(?:mo|month|hr|hour|user)|per\s+(?:month|mo|hour|hr|user(?:/month)?|user\s+per\s+month))?"
    r"|(?<!\w)\$\s*\d[\d,]*(?:\.\d{1,2})?\s*(?:/(?:mo|month|hr|hour|user)|per\s+(?:month|mo|hour|hr|user(?:/month)?|user\s+per\s+month))?",
    re.IGNORECASE,
)
_BARE_PERIOD_SPEND_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d{1,2})?\s*(?:/(?:mo|month|hr|hour|user)|per\s+(?:month|mo|hour|hr|user(?:/month)?|user\s+per\s+month))\b",
    re.IGNORECASE,
)
_EFFORT_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:hours?|hrs?|days?)\s*(?:/(?:mo|month|week|wk)|per\s+(?:month|mo|week|wk))\b",
    re.IGNORECASE,
)
_PRICE_COMPLAINT_RE = re.compile(
    r"\b(?:too expensive|pricing is killing us|can't afford|cannot afford|overpriced|pricey|costs? too much|pricing hurts|pricing is painful)\b",
    re.IGNORECASE,
)
_WTP_PRESENT_RE = re.compile(
    r"\b(?:would pay|happy to pay|willing to pay|budget for|looking to buy|paid for|paying for|subscribe|subscribed)\b",
    re.IGNORECASE,
)
_WTP_POSSIBLE_RE = re.compile(r"\b(?:pricing|quote|license|subscription|plan)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PriceSignalExtractionInput:
    evidence_id: str
    source_type: str
    source_url: str | None
    title: str
    body: str
    topic_id: str = ""
    query_kind: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PriceSignalLLMContract:
    contract_version: str = PRICE_SIGNAL_CONTRACT_VERSION
    task_type: str = PRICE_SIGNAL_TASK_TYPE
    requires_pii_redaction: bool = True
    requires_evidence_citations: bool = True
    fail_closed_on_missing_citations: bool = True
    output_format: str = "json"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_price_signal(cleaned: CleanedEvidence) -> PriceSignal | None:
    cleaned.validate()
    text = _combined_text(cleaned)
    if not text.strip():
        return None

    current_spend_hint = _first_match(text, (_DOLLAR_AMOUNT_RE, _BARE_PERIOD_SPEND_RE))
    effort_cost_hint = _first_match(text, (_EFFORT_RE,))
    price_complaint = _first_match(text, (_PRICE_COMPLAINT_RE,))
    willingness_to_pay_indicator = _willingness_to_pay_indicator(text)

    if not any(
        (
            current_spend_hint,
            effort_cost_hint,
            price_complaint,
            willingness_to_pay_indicator != "not_detected",
        )
    ):
        return None

    evidence_cited = _evidence_snippet(
        text,
        [current_spend_hint, effort_cost_hint, price_complaint],
        include_wtp=willingness_to_pay_indicator != "not_detected",
    )
    signal = PriceSignal(
        price_signal_id=_price_signal_id(cleaned.evidence_id),
        evidence_id=cleaned.evidence_id,
        source_id=cleaned.source_id,
        source_type=cleaned.source_type,
        source_url=cleaned.source_url,
        topic_id=cleaned.topic_id,
        query_kind=cleaned.query_kind,
        current_spend_hint=current_spend_hint,
        effort_cost_hint=effort_cost_hint,
        price_complaint=price_complaint,
        willingness_to_pay_indicator=willingness_to_pay_indicator,
        evidence_cited=evidence_cited,
        confidence=_confidence(
            current_spend_hint=current_spend_hint,
            effort_cost_hint=effort_cost_hint,
            price_complaint=price_complaint,
            willingness_to_pay_indicator=willingness_to_pay_indicator,
        ),
    )
    signal.validate()
    return signal


def price_signal_scoring_boost(price_signal: PriceSignal | None) -> float:
    if price_signal is None or not price_signal.has_explicit_signal:
        return 0.0
    if not price_signal.evidence_cited.strip():
        return 0.0
    if price_signal.confidence < 0.35:
        return 0.0
    if price_signal.current_spend_hint or price_signal.effort_cost_hint:
        return 0.05
    if price_signal.willingness_to_pay_indicator == "present" or price_signal.price_complaint:
        return 0.03
    return 0.0


def build_price_signal_extraction_messages(review_input: PriceSignalExtractionInput) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="system",
            content="\n".join(
                [
                    "You are performing evidence-only price signal extraction.",
                    "Use only the supplied evidence item; do not invent budgets, prices, spend, effort, or willingness to pay.",
                    "Cite the exact evidence text for every non-null field.",
                    "Return null fields and low confidence when unsure.",
                    "Return structured JSON only.",
                ]
            ),
        ),
        build_prompt_safety_envelope_message(),
        LLMMessage(role="user", content=_price_signal_user_prompt(review_input)),
    ]


def _price_signal_user_prompt(review_input: PriceSignalExtractionInput) -> str:
    payload = {
        "contract": PriceSignalLLMContract().to_dict(),
        "evidence_item": review_input.to_dict(),
        "requested_json_schema": {
            "price_signal_id": "string",
            "evidence_id": "string",
            "current_spend_hint": "string|null",
            "effort_cost_hint": "string|null",
            "price_complaint": "string|null",
            "willingness_to_pay_indicator": "present|possible|not_detected",
            "evidence_cited": "exact supporting text snippet or empty string",
            "confidence": "number 0..1",
            "no_invention_confirmed": True,
        },
        "rules": [
            "Extract only explicit dollar, period spend, effort cost, price complaint, or willingness-to-pay text.",
            "Do not normalize monthly values.",
            "Do not infer a budget from company size, role, tool category, or pain intensity.",
            "Use null/not_detected when evidence is vague.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def _combined_text(cleaned: CleanedEvidence) -> str:
    return " ".join(part for part in (cleaned.normalized_title, cleaned.normalized_body) if part).strip()


def _first_match(text: str, patterns: tuple[re.Pattern[str], ...]) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _normalize_hint(match.group(0))
    return None


def _willingness_to_pay_indicator(text: str) -> str:
    if _WTP_PRESENT_RE.search(text):
        return "present"
    if _WTP_POSSIBLE_RE.search(text):
        return "possible"
    return "not_detected"


def _confidence(
    *,
    current_spend_hint: str | None,
    effort_cost_hint: str | None,
    price_complaint: str | None,
    willingness_to_pay_indicator: str,
) -> float:
    score = 0.0
    if current_spend_hint:
        score += 0.35
    if effort_cost_hint:
        score += 0.30
    if price_complaint:
        score += 0.18
    if willingness_to_pay_indicator == "present":
        score += 0.18
    elif willingness_to_pay_indicator == "possible":
        score += 0.08
    return round(min(0.88, max(0.0, score)), 2)


def _evidence_snippet(text: str, hints: list[str | None], *, include_wtp: bool) -> str:
    wanted = [hint.lower() for hint in hints if hint]
    sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT_RE.split(text) if sentence.strip()]
    for sentence in sentences or [text.strip()]:
        lowered = sentence.lower()
        if any(hint in lowered for hint in wanted):
            return _truncate(sentence)
        if include_wtp and (_WTP_PRESENT_RE.search(sentence) or _WTP_POSSIBLE_RE.search(sentence)):
            return _truncate(sentence)
    return _truncate(text.strip())


def _truncate(value: str, limit: int = 220) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _normalize_hint(value: str) -> str:
    return " ".join(value.strip().split())


def _price_signal_id(evidence_id: str) -> str:
    safe = _SAFE_ID_RE.sub("_", evidence_id.strip()).strip("_")
    return f"price_signal_{safe}"
