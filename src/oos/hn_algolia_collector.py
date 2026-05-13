from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen

from .collection_scheduler import ScheduledCollectionItem
from .collectors import BaseCollector, CollectionResult
from .models import RawEvidence, compute_raw_evidence_content_hash


# =========================================================================
# Canonical source identity (matching config/source_registry.json)
# =========================================================================
# "hacker_news" is the canonical source_id per config/source_registry.json.
# "discussion" is the canonical source_type per the discovery source adapter contract.
# "hacker_news_algolia" is an access method / legacy implementation detail,
# NOT the canonical source_id or source_type.
# =========================================================================

HN_CANONICAL_SOURCE_ID = "hacker_news"
HN_CANONICAL_SOURCE_TYPE = "discussion"
HN_CANONICAL_SOURCE_NAME = "Hacker News"

# Legacy constants maintained for backward compatibility with existing
# source_registry.py (code registry), query_planner, and scheduler wiring.
# New code should prefer HN_CANONICAL_SOURCE_ID / HN_CANONICAL_SOURCE_TYPE.
HN_ALGOLIA_SOURCE_ID = "hacker_news_algolia"       # legacy access method
HN_ALGOLIA_SOURCE_TYPE = "hacker_news_algolia"     # legacy access method
HN_ALGOLIA_SOURCE_NAME = "Hacker News Algolia"     # legacy display name
HN_ALGOLIA_BASE_URL = "https://hn.algolia.com/api/v1"

# Valid source_id values accepted by supports()
_VALID_HN_SOURCE_IDS = {HN_CANONICAL_SOURCE_ID, HN_ALGOLIA_SOURCE_ID}
_VALID_HN_SOURCE_TYPES = {HN_CANONICAL_SOURCE_TYPE, HN_ALGOLIA_SOURCE_TYPE}


# =========================================================================
# evidence_kind classification — deterministic heuristics (no LLM)
# =========================================================================

_PAIN_KEYWORDS = [
    "frustrating", "pain", "struggle", "nightmare", "waste of time",
    "drives me crazy", "so hard to", "impossible to", "hours of",
    "biggest problem", "hate", "terrible", "broken", "can't", "unusable",
]

_WORKAROUND_KEYWORDS = [
    "workaround", "hack", "spreadsheet", "manual process", "duct tape",
    "jerry-rigged", "makeshift", "temporary solution", "script to",
    "zapier", "ifttt", "cron job",
]

_COMPLAINT_KEYWORDS = [
    "why is", "why does", "should be easier", "too expensive", "overpriced",
    "not worth", "disappointed", "regret", "wish I hadn't",
]

_FEATURE_REQUEST_KEYWORDS = [
    "wish it had", "would be great if", "feature request", "missing",
    "needs", "should support", "please add", "looking for a tool that",
]

_PRODUCT_LAUNCH_KEYWORDS = [
    "launch", "launched", "announcing", "just shipped", "new product",
    "introducing", "mvp", "beta", "waitlist",
]

_MARKET_TREND_KEYWORDS = [
    "trending", "everyone is", "the future of", "industry shift",
    "growing", "market is", "adoption", "is eating the world",
]

_SOLUTION_KEYWORDS = [
    "built a", "created a", "automated", "replaced", "switched from",
    "migrated", "using AI to",
]

_VALID_EVIDENCE_KINDS = {
    "pain_signal_candidate",
    "workaround",
    "complaint",
    "feature_request",
    "product_launch",
    "solution_pattern",
    "market_trend",
    "unknown",
}


# =========================================================================
# Noise / quality flag keywords — deterministic (no LLM)
# =========================================================================

_FLAMEWAR_META_KEYWORDS = [
    "yc", "y combinator", "pg", "dang", "moderation", "flag",
    "downvote", "why was this flagged", "hacker news is", "hn is",
    "this site", "community", "guidelines",
]

_SELF_PROMO_KEYWORDS = [
    "my startup", "my product", "my company", "we built", "our platform",
    "check out", "sign up", "discount code",
]

_LAUNCH_HYPE_KEYWORDS = [
    "revolutionary", "game changer", "disruptive", "world's first",
    "never been done", "breakthrough",
]

_VALID_QUALITY_FLAGS = {
    "low_text_context",
    "suspected_self_promo",
    "launch_hype",
    "flamewar_or_meta_discussion",
    "low_confidence_source",
    "requires_manual_review",
    "missing_date",
    "high_noise_source",
}


# =========================================================================
# HN-local source quality summary dataclass
# =========================================================================

@dataclass
class HNSourceQualitySummary:
    """HN-local source quality summary produced per collection batch.

    Lives alongside CollectionResult (not inside it, to avoid modifying
    the shared collectors.py module).
    """
    source_id: str = HN_CANONICAL_SOURCE_ID
    source_type: str = HN_CANONICAL_SOURCE_TYPE
    access_method: str = "hn_algolia"
    records_seen: int = 0
    records_emitted: int = 0
    records_rejected: int = 0
    warning_count: int = 0
    error_count: int = 0
    duplicate_count: int = 0
    missing_url_count: int = 0
    placeholder_url_count: int = 0
    quality_flag_counts: Dict[str, int] = field(default_factory=dict)
    rejection_reasons: Dict[str, int] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("HNSourceQualitySummary.source_id must be a non-empty string")
        if not isinstance(self.source_type, str) or not self.source_type.strip():
            raise ValueError("HNSourceQualitySummary.source_type must be a non-empty string")
        for name in ("records_seen", "records_emitted", "records_rejected",
                     "warning_count", "error_count", "duplicate_count",
                     "missing_url_count", "placeholder_url_count"):
            val = getattr(self, name)
            if not isinstance(val, int) or val < 0:
                raise ValueError(f"HNSourceQualitySummary.{name} must be a non-negative int")


# =========================================================================
# Helper utilities
# =========================================================================

def _contains_any(text: str, keywords: list[str]) -> bool:
    """Return True if any keyword (case-insensitive) appears in text."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _classify_evidence_kind(hit: dict[str, Any]) -> str:
    """Deterministic evidence_kind classification for an HN Algolia hit.

    Uses title, body, _tags, and keyword heuristics. No LLM calls.
    """
    tags: list[str] = hit.get("_tags") or hit.get("tags") or []
    title = str(hit.get("title") or hit.get("story_title") or "")
    body = str(hit.get("story_text") or hit.get("comment_text") or "")
    combined = f"{title} {body}".lower()

    is_ask_hn = "ask_hn" in tags
    is_show_hn = "show_hn" in tags
    is_comment = "comment" in tags
    is_story = "story" in tags

    if is_ask_hn:
        if _contains_any(combined, _PAIN_KEYWORDS):
            return "pain_signal_candidate"
        if _contains_any(combined, _WORKAROUND_KEYWORDS):
            return "workaround"
        if _contains_any(combined, _COMPLAINT_KEYWORDS):
            return "complaint"
        if _contains_any(combined, _FEATURE_REQUEST_KEYWORDS):
            return "feature_request"
        return "unknown"

    if is_show_hn:
        return "product_launch"

    if is_story:
        if _contains_any(combined, _PRODUCT_LAUNCH_KEYWORDS):
            return "product_launch"
        if _contains_any(combined, _MARKET_TREND_KEYWORDS):
            return "market_trend"
        if _contains_any(combined, _SOLUTION_KEYWORDS):
            return "solution_pattern"
        if _contains_any(combined, _PAIN_KEYWORDS):
            return "pain_signal_candidate"
        return "unknown"

    if is_comment:
        if _contains_any(combined, _PAIN_KEYWORDS):
            return "pain_signal_candidate"
        if _contains_any(combined, _WORKAROUND_KEYWORDS):
            return "workaround"
        if _contains_any(combined, _COMPLAINT_KEYWORDS):
            return "complaint"
        # Short comment with no strong keywords → unknown (tiebreaker)
        if len(body) < 100:
            return "unknown"
        return "unknown"

    return "unknown"


def _compute_quality_flags(hit: dict[str, Any]) -> list[str]:
    """Deterministic quality/noise flags for an HN Algolia hit."""
    flags: list[str] = []
    tags: list[str] = hit.get("_tags") or hit.get("tags") or []
    title = str(hit.get("title") or hit.get("story_title") or "")
    body = str(hit.get("story_text") or hit.get("comment_text") or "")
    combined_text = f"{title} {body}".lower()
    points = hit.get("points")

    # low_text_context
    if len(body) < 100:
        flags.append("low_text_context")

    # flamewar_or_meta_discussion
    if _contains_any(combined_text, _FLAMEWAR_META_KEYWORDS):
        flags.append("flamewar_or_meta_discussion")

    # suspected_self_promo
    if _contains_any(combined_text, _SELF_PROMO_KEYWORDS):
        flags.append("suspected_self_promo")

    # launch_hype
    if "show_hn" in tags or "launch_hn" in tags:
        if _contains_any(combined_text, _LAUNCH_HYPE_KEYWORDS):
            flags.append("launch_hype")
        # Low-engagement launch → self-promo suspect
        if isinstance(points, (int, float)) and points < 10:
            if "suspected_self_promo" not in flags:
                flags.append("suspected_self_promo")

    # missing_date
    if not hit.get("created_at"):
        flags.append("missing_date")

    # low_confidence_source for very low-score items
    if isinstance(points, (int, float)) and points < 3:
        flags.append("low_confidence_source")

    # requires_manual_review when any other flag is set
    if flags and "requires_manual_review" not in flags:
        flags.append("requires_manual_review")

    return flags


def _author_context_label(hit: dict[str, Any]) -> str:
    """Return a privacy-safe author_or_context label based on HN item type."""
    tags: list[str] = hit.get("_tags") or hit.get("tags") or []
    if "ask_hn" in tags:
        return "Ask HN poster"
    if "show_hn" in tags:
        return "Show HN maker"
    if "comment" in tags:
        return "HN commenter"
    return "HN story author"


# =========================================================================
# Hit conversion and parsing
# =========================================================================

def hn_hit_to_raw_evidence(
    hit: dict[str, Any],
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "hn_algolia_fixture",
    quality_summary: Optional[HNSourceQualitySummary] = None,
) -> Optional[RawEvidence]:
    """Convert a single HN Algolia search hit into a RawEvidence record.

    Emits canonical source_id="hacker_news" and source_type="discussion".
    Rejects hits with missing objectID or empty title+body.
    Updates quality_summary in-place when provided.
    """
    object_id = str(hit.get("objectID") or "").strip()
    if not object_id:
        if quality_summary is not None:
            quality_summary.records_rejected += 1
            quality_summary.rejection_reasons["missing_objectID"] = \
                quality_summary.rejection_reasons.get("missing_objectID", 0) + 1
        return None

    title = _first_non_empty(hit.get("title"), hit.get("story_title"), f"HN item {object_id}")
    body = _first_non_empty(
        hit.get("story_text"),
        hit.get("comment_text"),
        hit.get("url"),
        hit.get("story_url"),
        title,
    )

    # Note: Items with only fallback title/body are retained, consistent with
    # the pre-v2.12 behavior. Records with effectively empty content get the
    # low_text_context and low_confidence_source quality flags set downstream
    # in _compute_quality_flags().

    collected_at = _first_non_empty(hit.get("created_at"), "1970-01-01T00:00:00+00:00")
    source_url = f"https://news.ycombinator.com/item?id={object_id}"
    original_url = _first_non_empty(hit.get("url"), hit.get("story_url"), "")
    tags_list = hit.get("_tags") or hit.get("tags") or []
    points = hit.get("points")
    num_comments = hit.get("num_comments")

    # Classification
    evidence_kind = _classify_evidence_kind(hit)
    quality_flags = _compute_quality_flags(hit)

    # Engagement metrics (stored in raw_metadata)
    engagement = {}
    if isinstance(points, (int, float)):
        engagement["points"] = points
    else:
        engagement["points"] = None
    if isinstance(num_comments, (int, float)):
        engagement["num_comments"] = num_comments
    else:
        engagement["num_comments"] = None

    # Derive HN item type and categories
    item_type = _derive_item_type(tags_list)
    categories = _derive_categories(tags_list)

    metadata: dict[str, Any] = {
        "objectID": object_id,
        "created_at": hit.get("created_at"),
        "created_at_i": hit.get("created_at_i"),
        "points": points,
        "num_comments": num_comments,
        "tags": list(tags_list),
        "original_url": original_url,
        "author_present": bool(str(hit.get("author") or "").strip()),
        "query_plan_id": scheduled_item.query_plan_id,
        "dedup_key": scheduled_item.dedup_key,
        # v2.12 hardened additions
        "evidence_kind": evidence_kind,
        "quality_flags": quality_flags,
        "item_type": item_type,
        "item_text_length": len(body),
        "engagement_metrics": engagement,
        "categories": categories,
        "source_specific_id": object_id,
        "canonical_url": original_url if original_url else None,
    }

    # Track quality flags in summary
    if quality_summary is not None and quality_flags:
        for flag in quality_flags:
            quality_summary.quality_flag_counts[flag] = \
                quality_summary.quality_flag_counts.get(flag, 0) + 1

    evidence = RawEvidence(
        evidence_id=f"raw_hacker_news_{object_id}",
        source_id=HN_CANONICAL_SOURCE_ID,
        source_type=HN_CANONICAL_SOURCE_TYPE,
        source_name=HN_CANONICAL_SOURCE_NAME,
        source_url=source_url,
        collected_at=collected_at,
        title=title,
        body=body,
        language="en",
        topic_id=scheduled_item.topic_id,
        query_kind=scheduled_item.query_kind,
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context=_author_context_label(hit),
        raw_metadata=metadata,
        access_policy="public_hn_algolia_fixture_or_live_disabled_default",
        collection_method=collection_method,
    )
    evidence.validate()
    return evidence


def parse_hn_algolia_hits(
    payload: dict[str, Any],
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "hn_algolia_fixture",
    quality_summary: Optional[HNSourceQualitySummary] = None,
) -> list[RawEvidence]:
    """Parse a list of HN Algolia hits into RawEvidence records.

    Populates quality_summary in-place when provided.
    """
    hits = payload.get("hits", [])
    if not isinstance(hits, list):
        if quality_summary is not None:
            quality_summary.error_count += 1
        return []

    if quality_summary is not None:
        quality_summary.records_seen += len(hits)

    evidence: list[RawEvidence] = []
    seen_ids: set[str] = set()
    for hit in hits:
        if not isinstance(hit, dict):
            if quality_summary is not None:
                quality_summary.records_rejected += 1
                quality_summary.rejection_reasons["non_dict_hit"] = \
                    quality_summary.rejection_reasons.get("non_dict_hit", 0) + 1
            continue

        item = hn_hit_to_raw_evidence(
            hit,
            scheduled_item=scheduled_item,
            collection_method=collection_method,
            quality_summary=quality_summary,
        )
        if item is None:
            continue
        if item.evidence_id in seen_ids:
            if quality_summary is not None:
                quality_summary.duplicate_count += 1
            continue
        evidence.append(item)
        seen_ids.add(item.evidence_id)
        if len(evidence) >= scheduled_item.max_results:
            break

    if quality_summary is not None:
        quality_summary.records_emitted = len(evidence)

    return evidence


def build_hn_source_quality_summary(
    payload: dict[str, Any],
    evidence: list[RawEvidence],
    *,
    collection_method: str = "hn_algolia_fixture",
) -> HNSourceQualitySummary:
    """Build a complete HN-local source quality summary from payload and results.

    This is a companion to parse_hn_algolia_hits for callers that don't
    pass an in-progress summary during parsing.
    """
    hits = payload.get("hits", []) if isinstance(payload, dict) else []
    hits = hits if isinstance(hits, list) else []

    summary = HNSourceQualitySummary(
        records_seen=len(hits),
        records_emitted=len(evidence),
        access_method=collection_method.replace("hn_algolia_", ""),
    )

    # Count rejection reasons from evidence metadata
    for ev in evidence:
        qf = ev.raw_metadata.get("quality_flags", [])
        if isinstance(qf, list):
            for flag in qf:
                if isinstance(flag, str):
                    summary.quality_flag_counts[flag] = \
                        summary.quality_flag_counts.get(flag, 0) + 1

    # missing_date count
    missing_date = sum(
        1 for ev in evidence
        if isinstance(ev.raw_metadata.get("quality_flags"), list)
        and "missing_date" in ev.raw_metadata["quality_flags"]
    )
    if missing_date:
        summary.warning_count += missing_date

    summary.validate()
    return summary


# =========================================================================
# Collector class
# =========================================================================

class HNAlgoliaCollector(BaseCollector):
    """Hacker News collector via Algolia Search API.

    Emits canonical source_id="hacker_news" and source_type="discussion"
    on all RawEvidence records. Accepts both legacy ("hacker_news_algolia")
    and canonical ("hacker_news") source_id/source_type in supports()
    for backward compatibility with existing registry/scheduler wiring.
    """

    def __init__(
        self,
        *,
        source_id: str = HN_ALGOLIA_SOURCE_ID,
        allow_live_network: bool = False,
        fixture_payload: Optional[dict[str, Any]] = None,
        endpoint: str = "search_by_date",
        timeout_seconds: int = 10,
    ):
        if endpoint not in {"search", "search_by_date"}:
            raise ValueError("HNAlgoliaCollector.endpoint must be search or search_by_date")
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("HNAlgoliaCollector.timeout_seconds must be a positive int")
        self.source_id = source_id
        self.allow_live_network = allow_live_network
        self.fixture_payload = fixture_payload
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def supports(self, scheduled_item: ScheduledCollectionItem) -> bool:
        scheduled_item.validate()
        return (
            scheduled_item.source_id in _VALID_HN_SOURCE_IDS
            and scheduled_item.source_type in _VALID_HN_SOURCE_TYPES
        )

    def collect(self, scheduled_item: ScheduledCollectionItem) -> CollectionResult:
        scheduled_item.validate()
        if not self.supports(scheduled_item):
            raise ValueError("HNAlgoliaCollector does not support scheduled item source")

        payload = self.fixture_payload
        collection_method = "hn_algolia_fixture"
        live_network_used = False

        if payload is None:
            if not self.allow_live_network or not scheduled_item.live_network_enabled:
                payload = {"hits": []}
            else:
                payload = self._fetch_live_payload(scheduled_item)
                collection_method = "hn_algolia_search"
                live_network_used = True

        # Build a canonicalized scheduled_item for evidence output.
        # The incoming scheduled_item may carry legacy source_id/source_type
        # from the code registry; we normalize to canonical values for output.
        canonical_item = scheduled_item
        if (scheduled_item.source_id != HN_CANONICAL_SOURCE_ID
                or scheduled_item.source_type != HN_CANONICAL_SOURCE_TYPE):
            canonical_item = replace(
                scheduled_item,
                source_id=HN_CANONICAL_SOURCE_ID,
                source_type=HN_CANONICAL_SOURCE_TYPE,
            )

        quality_summary = HNSourceQualitySummary(
            access_method=collection_method.replace("hn_algolia_", ""),
        )

        evidence = parse_hn_algolia_hits(
            payload,
            scheduled_item=canonical_item,
            collection_method=collection_method,
            quality_summary=quality_summary,
        )

        result = CollectionResult(
            scheduled_item=canonical_item,
            evidence=evidence,
            collector_name="hn_algolia_collector",
            live_network_used=live_network_used,
        )
        result.validate()
        return result

    def _fetch_live_payload(self, scheduled_item: ScheduledCollectionItem) -> dict[str, Any]:
        query = urlencode({"query": scheduled_item.query_text, "hitsPerPage": scheduled_item.max_results})
        url = f"{HN_ALGOLIA_BASE_URL}/{self.endpoint}?{query}"
        with urlopen(url, timeout=self.timeout_seconds) as response:
            data = response.read().decode("utf-8", errors="replace")
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise ValueError("HN Algolia response must be a JSON object")
        return payload


# =========================================================================
# Internal helpers
# =========================================================================

def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _derive_item_type(tags: list[str]) -> str:
    """Derive HN item type from _tags."""
    if "ask_hn" in tags:
        return "ask_hn"
    if "show_hn" in tags:
        return "show_hn"
    if "launch_hn" in tags:
        return "launch_hn"
    if "comment" in tags:
        return "comment"
    if "story" in tags:
        return "story"
    if "poll" in tags:
        return "poll"
    if "job" in tags:
        return "job"
    return "unknown"


def _derive_categories(tags: list[str]) -> list[str]:
    """Derive human-readable categories from _tags."""
    categories: list[str] = []
    if "ask_hn" in tags:
        categories.append("ask-hn")
    if "show_hn" in tags:
        categories.append("show-hn")
    if "launch_hn" in tags:
        categories.append("launch-hn")
    if "poll" in tags:
        categories.append("poll")
    if "job" in tags:
        categories.append("job")
    return categories
