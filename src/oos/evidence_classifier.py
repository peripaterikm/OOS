from __future__ import annotations

import hashlib
import html
import re
from typing import Iterable, List
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import CleanedEvidence, EvidenceClassification, RawEvidence


PAIN_SIGNAL_CANDIDATE = "pain_signal_candidate"
WORKAROUND_SIGNAL_CANDIDATE = "workaround_signal_candidate"
BUYING_INTENT_CANDIDATE = "buying_intent_candidate"
COMPETITOR_WEAKNESS_CANDIDATE = "competitor_weakness_candidate"
TREND_TRIGGER_CANDIDATE = "trend_trigger_candidate"
NEEDS_HUMAN_REVIEW = "needs_human_review"
NOISE = "noise"


_WHITESPACE_RE = re.compile(r"\s+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_BR_BLOCK_TAG_RE = re.compile(r"</?(?:p|div|br|li|ul|ol|pre|code|blockquote|h[1-6])\b[^>]*>", re.IGNORECASE)
_MARKDOWN_PREFIX_RE = re.compile(r"^\s*(?:#{1,6}\s+|\*\*+|```+|[-*_]{3,}\s*)+")
_DAY_ENTRY_RE = re.compile(r"\bday\s+\d+\b", re.IGNORECASE)

_RULES: list[tuple[str, list[str]]] = [
    (
        PAIN_SIGNAL_CANDIDATE,
        [
            "problem",
            "pain",
            "struggle",
            "hard to",
            "can't",
            "doesn't work",
            "broken",
            "frustrating",
            "issue",
            "bug",
        ],
    ),
    (
        WORKAROUND_SIGNAL_CANDIDATE,
        [
            "workaround",
            "manual",
            "spreadsheet",
            "hack",
            "we use",
            "i built",
            "temporary solution",
        ],
    ),
    (
        BUYING_INTENT_CANDIDATE,
        [
            "looking for",
            "recommend",
            "alternative",
            "would pay",
            "need a tool",
            "any tool",
            "pricing",
        ],
    ),
    (
        COMPETITOR_WEAKNESS_CANDIDATE,
        [
            "too expensive",
            "missing feature",
            "switching from",
            "alternative to",
            "support is bad",
            "doesn't support",
        ],
    ),
    (
        TREND_TRIGGER_CANDIDATE,
        [
            "new regulation",
            "law changed",
            "api changed",
            "ai now",
            "recently",
            "market changed",
        ],
    ),
]

_SPAM_PHRASES = (
    "buy now",
    "casino",
    "viagra",
    "free money",
    "crypto giveaway",
    "click here",
)

_MOJIBAKE_FRAGMENTS = ("рџ", "вЂ", "Рџ")

_AI_CFO_STRONG_ANCHORS = (
    "cash flow",
    "cashflow",
    "invoice",
    "invoices",
    "invoicing",
    "billing",
    "accounting",
    "bookkeeping",
    "financial",
    "finance",
    "reporting",
    "management reporting",
    "budget",
    "budgeting",
    "forecast",
    "forecasting",
    "cfo",
    "controller",
    "reconciliation",
    "accounts payable",
    "accounts receivable",
    "payables",
    "receivables",
    "payroll",
    "expenses",
    "expense",
    "runway",
    "p&l",
    "profit and loss",
    "working capital",
    "payment cycles",
    "payment status",
    "due dates",
    "bills",
    "quickbooks",
    "xero",
    "netsuite",
)
_AI_CFO_WEAK_ANCHORS = ("spreadsheet", "spreadsheets")
_AI_CFO_CONTEXT_TERMS = (
    "small business",
    "smb",
    "freelancer",
    "founder",
    "bookkeeper",
    "client",
    "vendor",
)

_MARKETING_MARKERS = (
    "30-day linkedin content calendar",
    "copy-paste ready posts",
    "copy-pasteable linkedin posts",
    "post topic",
    "post type",
    "content calendar",
    "executive summary",
    "product launch",
    "product pitch",
    "campaign variants",
    "dynamic creative",
    "competitive target",
    "parent epic",
    "priority: p1",
    "effort:",
    "market context & zone analysis",
    "portfolio position",
    "landing page",
    "marketing copy",
    "linkedin's dco",
    "creative personalization engine",
)


def normalize_whitespace(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", str(value or "").strip())


def normalize_signal_text(value: str) -> str:
    text = str(value or "")
    text = html.unescape(text)
    text = _BR_BLOCK_TAG_RE.sub(" ", text)
    text = _HTML_TAG_RE.sub(" ", text)
    lines = []
    for line in text.splitlines():
        cleaned = _MARKDOWN_PREFIX_RE.sub("", line).strip()
        cleaned = cleaned.strip("*`_ ")
        if cleaned:
            lines.append(cleaned)
    return normalize_whitespace(" ".join(lines))


def normalize_url(url: str) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    parts = urlsplit(text)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path or ""
    if path != "/":
        path = path.rstrip("/")
    else:
        path = ""
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    query = urlencode(sorted(query_pairs))
    return urlunsplit((scheme, netloc, path, query, ""))


def compute_normalized_content_hash(*, normalized_title: str, normalized_body: str) -> str:
    content = f"{normalized_title}\n{normalized_body}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def clean_evidence(evidence: RawEvidence) -> CleanedEvidence:
    normalized_title = normalize_signal_text(evidence.title)
    normalized_body = normalize_signal_text(evidence.body)
    normalized_url = normalize_url(evidence.source_url)
    language = normalize_whitespace(evidence.language) or "unknown"
    notes = [
        "whitespace_normalized",
        "html_entities_unescaped",
        "simple_html_tags_stripped",
        "markdown_markers_softened",
        "url_normalized",
        "normalized_content_hash_generated",
        "boilerplate_removal_not_applied",
    ]
    cleaned = CleanedEvidence(
        evidence_id=evidence.evidence_id,
        source_id=evidence.source_id,
        source_type=evidence.source_type,
        source_url=evidence.source_url,
        topic_id=evidence.topic_id,
        query_kind=evidence.query_kind,
        title=evidence.title,
        body=evidence.body,
        normalized_title=normalized_title,
        normalized_body=normalized_body,
        normalized_url=normalized_url,
        normalized_content_hash=compute_normalized_content_hash(
            normalized_title=normalized_title,
            normalized_body=normalized_body,
        ),
        language=language,
        original_content_hash=evidence.content_hash,
        cleaning_notes=notes,
    )
    cleaned.validate()
    return cleaned


def clean_evidence_batch(evidence_items: Iterable[RawEvidence]) -> List[CleanedEvidence]:
    return [clean_evidence(evidence) for evidence in evidence_items]


def classify_evidence(cleaned: CleanedEvidence) -> EvidenceClassification:
    text = f"{cleaned.normalized_title} {cleaned.normalized_body}".lower()
    if _is_noise_text(text):
        return _classification(
            cleaned=cleaned,
            classification=NOISE,
            confidence=0.95,
            matched_rules=["noise:empty_or_spam"],
            reason="Evidence is empty, near-empty, or matches obvious spam/noise patterns.",
            requires_human_review=False,
            is_noise=True,
        )

    relevance = topic_relevance_score(text, cleaned.topic_id)
    marketing_penalty = anti_marketing_penalty(text)
    if cleaned.topic_id == "ai_cfo_smb":
        if marketing_penalty >= 0.7 and relevance < 0.45:
            return _classification(
                cleaned=cleaned,
                classification=NOISE,
                confidence=0.9,
                matched_rules=["noise:marketing_generated_content"],
                reason="Marketing/generated content markers dominate and finance relevance is weak.",
                requires_human_review=False,
                is_noise=True,
            )

    for classification, phrases in _RULES:
        matches = [phrase for phrase in phrases if phrase in text]
        if matches:
            if cleaned.topic_id == "ai_cfo_smb":
                if relevance < 0.2:
                    return _low_relevance_review(cleaned, matches)
                if marketing_penalty >= 0.4 and relevance < 0.6:
                    return _classification(
                        cleaned=cleaned,
                        classification=NEEDS_HUMAN_REVIEW,
                        confidence=0.3,
                        matched_rules=["review:marketing_generated_content"] + [
                            f"{classification}:{phrase}" for phrase in matches
                        ],
                        reason="Signal keywords were present, but generated/marketing markers reduce trust.",
                        requires_human_review=True,
                        is_noise=False,
                    )
            return _classification(
                cleaned=cleaned,
                classification=classification,
                confidence=_rule_confidence(classification, matches, relevance, marketing_penalty, text),
                matched_rules=[f"{classification}:{phrase}" for phrase in matches],
                reason=f"Matched deterministic {classification} keyword rule.",
                requires_human_review=False,
                is_noise=False,
            )

    if cleaned.topic_id == "ai_cfo_smb" and marketing_penalty >= 0.4:
        return _classification(
            cleaned=cleaned,
            classification=NEEDS_HUMAN_REVIEW,
            confidence=0.3,
            matched_rules=["review:marketing_generated_content"],
            reason="Generated/marketing markers are present, but no deterministic signal rule was strong enough.",
            requires_human_review=True,
            is_noise=False,
        )

    return _classification(
        cleaned=cleaned,
        classification=NEEDS_HUMAN_REVIEW,
        confidence=0.4 if cleaned.source_type in {"hacker_news_algolia", "github_issues"} else 0.35,
        matched_rules=["default:ambiguous_non_empty"],
        reason="Non-empty evidence did not match a deterministic signal rule and is retained for human review.",
        requires_human_review=True,
        is_noise=False,
    )


def classify_raw_evidence(evidence: RawEvidence) -> EvidenceClassification:
    return classify_evidence(clean_evidence(evidence))


def classify_evidence_batch(evidence_items: Iterable[RawEvidence]) -> List[EvidenceClassification]:
    return [classify_raw_evidence(evidence) for evidence in evidence_items]


def _is_noise_text(text: str) -> bool:
    compact = normalize_whitespace(text)
    if len(compact) < 10:
        return True
    return any(phrase in compact for phrase in _SPAM_PHRASES)


def contains_mojibake(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(fragment.lower() in lowered for fragment in _MOJIBAKE_FRAGMENTS)


def topic_relevance_score(text: str, topic_id: str) -> float:
    if topic_id != "ai_cfo_smb":
        return 0.5
    lowered = normalize_whitespace(text).lower()
    strong_matches = sum(1 for anchor in _AI_CFO_STRONG_ANCHORS if anchor in lowered)
    weak_matches = sum(1 for anchor in _AI_CFO_WEAK_ANCHORS if anchor in lowered)
    context_matches = sum(1 for term in _AI_CFO_CONTEXT_TERMS if term in lowered)
    score = min(0.9, strong_matches * 0.18 + min(context_matches, 2) * 0.05)
    if weak_matches and strong_matches:
        score += 0.08
    elif weak_matches and context_matches >= 2:
        score += 0.04
    return round(min(1.0, score), 2)


def anti_marketing_penalty(text: str) -> float:
    lowered = normalize_whitespace(text).lower()
    marker_hits = sum(1 for marker in _MARKETING_MARKERS if marker in lowered)
    day_hits = len(_DAY_ENTRY_RE.findall(lowered))
    structural_hits = 0
    if lowered.count("post topic") >= 2 or lowered.count("post type") >= 2:
        structural_hits += 2
    if "executive summary" in lowered and "market context" in lowered:
        structural_hits += 2
    if lowered.count("priority:") >= 2 or lowered.count("effort:") >= 2:
        structural_hits += 1
    if day_hits >= 5:
        structural_hits += 2
    return round(min(1.0, marker_hits * 0.18 + structural_hits * 0.16), 2)


def pain_indicator_score(text: str) -> float:
    lowered = str(text or "").lower()
    pain_terms = ("problem", "pain", "struggle", "hard to", "can't", "doesn't work", "broken", "frustrating", "issue", "bug")
    return round(min(1.0, sum(1 for term in pain_terms if term in lowered) * 0.2), 2)


def workaround_indicator_score(text: str) -> float:
    lowered = str(text or "").lower()
    terms = ("workaround", "manual", "spreadsheet", "spreadsheets", "hack", "we use", "i built", "temporary solution")
    return round(min(1.0, sum(1 for term in terms if term in lowered) * 0.22), 2)


def buying_indicator_score(text: str) -> float:
    lowered = str(text or "").lower()
    terms = ("looking for", "recommend", "alternative", "would pay", "need a tool", "any tool", "pricing")
    return round(min(1.0, sum(1 for term in terms if term in lowered) * 0.25), 2)


def urgency_indicator_score(text: str) -> float:
    lowered = str(text or "").lower()
    terms = ("urgent", "asap", "blocked", "critical", "broken", "can't", "deadline", "regulation", "compliance")
    return round(min(1.0, sum(1 for term in terms if term in lowered) * 0.2), 2)


def _low_relevance_review(cleaned: CleanedEvidence, matches: List[str]) -> EvidenceClassification:
    if cleaned.source_type in {"hacker_news_algolia", "github_issues"}:
        return _classification(
            cleaned=cleaned,
            classification=NEEDS_HUMAN_REVIEW,
            confidence=0.32,
            matched_rules=["review:ai_cfo_smb_low_finance_relevance"] + [f"keyword:{match}" for match in matches],
            reason="Signal keyword matched, but ai_cfo_smb finance anchors are missing or too weak.",
            requires_human_review=True,
            is_noise=False,
        )
    return _classification(
        cleaned=cleaned,
        classification=NOISE,
        confidence=0.82,
        matched_rules=["noise:ai_cfo_smb_low_finance_relevance"],
        reason="Signal keyword matched, but finance relevance is too weak for ai_cfo_smb.",
        requires_human_review=False,
        is_noise=True,
    )


def _rule_confidence(
    classification: str,
    matches: List[str],
    relevance: float,
    marketing_penalty: float,
    text: str,
) -> float:
    base = 0.62 + min(len(matches), 3) * 0.04
    base += relevance * 0.14
    if classification == PAIN_SIGNAL_CANDIDATE:
        base += pain_indicator_score(text) * 0.08
    if classification == WORKAROUND_SIGNAL_CANDIDATE:
        base += workaround_indicator_score(text) * 0.08
    if classification == BUYING_INTENT_CANDIDATE:
        base += buying_indicator_score(text) * 0.08
    base -= marketing_penalty * 0.22
    return round(max(0.25, min(0.92, base)), 2)


def _classification(
    *,
    cleaned: CleanedEvidence,
    classification: str,
    confidence: float,
    matched_rules: List[str],
    reason: str,
    requires_human_review: bool,
    is_noise: bool,
) -> EvidenceClassification:
    result = EvidenceClassification(
        evidence_id=cleaned.evidence_id,
        source_id=cleaned.source_id,
        source_type=cleaned.source_type,
        source_url=cleaned.source_url,
        topic_id=cleaned.topic_id,
        query_kind=cleaned.query_kind,
        classification=classification,
        confidence=confidence,
        matched_rules=matched_rules,
        reason=reason,
        requires_human_review=requires_human_review,
        is_noise=is_noise,
    )
    result.validate()
    return result
