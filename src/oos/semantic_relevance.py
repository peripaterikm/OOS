from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


PROVIDER_ID_DISABLED = "disabled"
PROVIDER_ID_KEYWORD_STUB = "keyword_stub"

PROVIDER_KIND_DISABLED = "disabled"
PROVIDER_KIND_KEYWORD_STUB = "keyword_stub"
PROVIDER_KIND_FUTURE_EMBEDDINGS = "future_embeddings"

_PROVIDER_KINDS = {
    PROVIDER_KIND_DISABLED,
    PROVIDER_KIND_KEYWORD_STUB,
    PROVIDER_KIND_FUTURE_EMBEDDINGS,
}

_AI_CFO_FINANCE_TERMS = (
    "cash flow",
    "cashflow",
    "invoice",
    "invoices",
    "invoicing",
    "billing",
    "accounting",
    "bookkeeping",
    "financial reporting",
    "management reporting",
    "budget",
    "budgeting",
    "forecast",
    "forecasting",
    "reconciliation",
    "accounts payable",
    "accounts receivable",
    "payroll",
    "expenses",
    "p&l",
    "profit and loss",
    "balance sheet",
    "quickbooks",
    "xero",
    "netsuite",
)

_AI_CFO_WEAK_TERMS = (
    "small business",
    "spreadsheet",
)

_AI_CFO_WORKFLOW_TERMS = (
    "manual",
    "workaround",
    "hard",
    "difficult",
    "frustrating",
    "can't",
    "cannot",
    "late",
    "missing",
    "scattered",
    "messy",
    "reconcile",
    "export",
    "import",
    "copy/paste",
    "copy paste",
    "cash gap",
    "due date",
    "due dates",
    "takes too long",
    "no visibility",
)


@dataclass(frozen=True)
class SemanticRelevanceInput:
    topic_id: str
    title: str = ""
    body: str = ""
    query_text: str | None = None
    source_type: str | None = None
    query_kind: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def combined_text(self) -> str:
        parts = [
            self.title,
            self.body,
            self.query_text or "",
            self.source_type or "",
            self.query_kind or "",
            " ".join(self.tags),
        ]
        return " ".join(str(part or "") for part in parts).lower()


@dataclass(frozen=True)
class SemanticRelevanceResult:
    provider_id: str
    provider_kind: str
    is_available: bool
    score: float | None
    confidence: float
    matched_terms: list[str]
    explanation: list[str]
    model_name: str | None
    embeddings_used: bool
    external_calls_made: bool

    def __post_init__(self) -> None:
        if self.provider_kind not in _PROVIDER_KINDS:
            raise ValueError(f"Unsupported semantic relevance provider kind: {self.provider_kind}")
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError("Semantic relevance score must be None or between 0.0 and 1.0")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Semantic relevance confidence must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SemanticRelevanceProvider(Protocol):
    provider_id: str
    provider_kind: str

    def is_available(self) -> bool:
        ...

    def score(self, relevance_input: SemanticRelevanceInput) -> SemanticRelevanceResult:
        ...


@dataclass(frozen=True)
class DisabledSemanticRelevanceProvider:
    provider_id: str = PROVIDER_ID_DISABLED
    provider_kind: str = PROVIDER_KIND_DISABLED

    def is_available(self) -> bool:
        return False

    def score(self, relevance_input: SemanticRelevanceInput) -> SemanticRelevanceResult:
        return SemanticRelevanceResult(
            provider_id=self.provider_id,
            provider_kind=self.provider_kind,
            is_available=False,
            score=None,
            confidence=0.0,
            matched_terms=[],
            explanation=["semantic relevance disabled; embeddings are not configured"],
            model_name=None,
            embeddings_used=False,
            external_calls_made=False,
        )


@dataclass(frozen=True)
class KeywordSemanticRelevanceProvider:
    provider_id: str = PROVIDER_ID_KEYWORD_STUB
    provider_kind: str = PROVIDER_KIND_KEYWORD_STUB

    def is_available(self) -> bool:
        return True

    def score(self, relevance_input: SemanticRelevanceInput) -> SemanticRelevanceResult:
        text = relevance_input.combined_text()
        if relevance_input.topic_id != "ai_cfo_smb":
            return SemanticRelevanceResult(
                provider_id=self.provider_id,
                provider_kind=self.provider_kind,
                is_available=True,
                score=0.0,
                confidence=0.15,
                matched_terms=[],
                explanation=[f"unknown topic for keyword semantic relevance: {relevance_input.topic_id}"],
                model_name=None,
                embeddings_used=False,
                external_calls_made=False,
            )

        finance_matches = _matched_terms(text, _AI_CFO_FINANCE_TERMS)
        weak_matches = _matched_terms(text, _AI_CFO_WEAK_TERMS)
        workflow_matches = _matched_terms(text, _AI_CFO_WORKFLOW_TERMS)
        matched_terms = sorted(set(finance_matches + weak_matches + workflow_matches))

        score = len(finance_matches) * 0.14 + len(workflow_matches) * 0.07
        if finance_matches and workflow_matches:
            score += 0.16
        elif finance_matches:
            score += 0.08
        if weak_matches and finance_matches:
            score += 0.04
        elif weak_matches and not finance_matches:
            score = min(score + 0.08, 0.22)
        if "spreadsheet" in weak_matches and not finance_matches:
            score = min(score, 0.22)
        if "small business" in weak_matches and not finance_matches:
            score = min(score, 0.20)

        score = round(_clamp(score), 2)
        confidence = 0.75 if finance_matches else 0.35 if weak_matches or workflow_matches else 0.20
        explanation = ["keyword_stub semantic relevance; no embeddings used"]
        if finance_matches:
            explanation.append("finance anchors matched")
        if workflow_matches:
            explanation.append("workflow or pain terms matched")
        if weak_matches and not finance_matches:
            explanation.append("weak anchors only; capped low")
        if not matched_terms:
            explanation.append("no topic terms matched")

        return SemanticRelevanceResult(
            provider_id=self.provider_id,
            provider_kind=self.provider_kind,
            is_available=True,
            score=score,
            confidence=confidence,
            matched_terms=matched_terms,
            explanation=explanation,
            model_name=None,
            embeddings_used=False,
            external_calls_made=False,
        )


def get_semantic_relevance_provider(provider_id: str | None = None) -> SemanticRelevanceProvider:
    normalized_provider_id = (provider_id or PROVIDER_ID_DISABLED).strip().lower()
    if normalized_provider_id == PROVIDER_ID_DISABLED:
        return DisabledSemanticRelevanceProvider()
    if normalized_provider_id == PROVIDER_ID_KEYWORD_STUB:
        return KeywordSemanticRelevanceProvider()
    raise ValueError(f"Unknown semantic relevance provider: {provider_id}")


def semantic_relevance_available(provider_id: str | None = None) -> bool:
    return get_semantic_relevance_provider(provider_id).is_available()


def _matched_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    return sorted({term for term in terms if term in text})


def _clamp(score: float) -> float:
    return max(0.0, min(1.0, float(score)))
