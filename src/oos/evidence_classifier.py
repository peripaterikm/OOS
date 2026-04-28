from __future__ import annotations

import hashlib
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


def normalize_whitespace(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", str(value or "").strip())


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
    normalized_title = normalize_whitespace(evidence.title)
    normalized_body = normalize_whitespace(evidence.body)
    normalized_url = normalize_url(evidence.source_url)
    language = normalize_whitespace(evidence.language) or "unknown"
    notes = [
        "whitespace_normalized",
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

    for classification, phrases in _RULES:
        matches = [phrase for phrase in phrases if phrase in text]
        if matches:
            return _classification(
                cleaned=cleaned,
                classification=classification,
                confidence=0.75,
                matched_rules=[f"{classification}:{phrase}" for phrase in matches],
                reason=f"Matched deterministic {classification} keyword rule.",
                requires_human_review=False,
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
