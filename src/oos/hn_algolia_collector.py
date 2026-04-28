from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen

from .collection_scheduler import ScheduledCollectionItem
from .collectors import BaseCollector, CollectionResult
from .models import RawEvidence, compute_raw_evidence_content_hash


HN_ALGOLIA_SOURCE_ID = "hacker_news_algolia"
HN_ALGOLIA_SOURCE_TYPE = "hacker_news_algolia"
HN_ALGOLIA_SOURCE_NAME = "Hacker News Algolia"
HN_ALGOLIA_BASE_URL = "https://hn.algolia.com/api/v1"


def hn_hit_to_raw_evidence(
    hit: Dict[str, Any],
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "hn_algolia_fixture",
) -> Optional[RawEvidence]:
    object_id = str(hit.get("objectID") or "").strip()
    if not object_id:
        return None

    title = _first_non_empty(hit.get("title"), hit.get("story_title"), f"HN item {object_id}")
    body = _first_non_empty(
        hit.get("story_text"),
        hit.get("comment_text"),
        hit.get("url"),
        hit.get("story_url"),
        title,
    )
    collected_at = _first_non_empty(hit.get("created_at"), "1970-01-01T00:00:00+00:00")
    source_url = f"https://news.ycombinator.com/item?id={object_id}"
    original_url = _first_non_empty(hit.get("url"), hit.get("story_url"), "")

    metadata = {
        "objectID": object_id,
        "created_at": hit.get("created_at"),
        "created_at_i": hit.get("created_at_i"),
        "points": hit.get("points"),
        "num_comments": hit.get("num_comments"),
        "tags": hit.get("_tags") or hit.get("tags") or [],
        "original_url": original_url,
        "author_present": bool(str(hit.get("author") or "").strip()),
        "query_plan_id": scheduled_item.query_plan_id,
        "dedup_key": scheduled_item.dedup_key,
    }

    evidence = RawEvidence(
        evidence_id=f"raw_hn_{object_id}",
        source_id=scheduled_item.source_id,
        source_type=scheduled_item.source_type,
        source_name=HN_ALGOLIA_SOURCE_NAME,
        source_url=source_url,
        collected_at=collected_at,
        title=title,
        body=body,
        language="unknown",
        topic_id=scheduled_item.topic_id,
        query_kind=scheduled_item.query_kind,
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="unverified public commenter",
        raw_metadata=metadata,
        access_policy="public_hn_algolia_fixture_or_live_disabled_default",
        collection_method=collection_method,
    )
    evidence.validate()
    return evidence


def parse_hn_algolia_hits(
    payload: Dict[str, Any],
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "hn_algolia_fixture",
) -> List[RawEvidence]:
    hits = payload.get("hits", [])
    if not isinstance(hits, list):
        return []

    evidence: List[RawEvidence] = []
    seen_ids: set[str] = set()
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        item = hn_hit_to_raw_evidence(
            hit,
            scheduled_item=scheduled_item,
            collection_method=collection_method,
        )
        if item is None or item.evidence_id in seen_ids:
            continue
        evidence.append(item)
        seen_ids.add(item.evidence_id)
        if len(evidence) >= scheduled_item.max_results:
            break
    return evidence


class HNAlgoliaCollector(BaseCollector):
    def __init__(
        self,
        *,
        source_id: str = HN_ALGOLIA_SOURCE_ID,
        allow_live_network: bool = False,
        fixture_payload: Optional[Dict[str, Any]] = None,
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
        return scheduled_item.source_id == self.source_id and scheduled_item.source_type == HN_ALGOLIA_SOURCE_TYPE

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

        evidence = parse_hn_algolia_hits(
            payload,
            scheduled_item=scheduled_item,
            collection_method=collection_method,
        )
        result = CollectionResult(
            scheduled_item=scheduled_item,
            evidence=evidence,
            collector_name="hn_algolia_collector",
            live_network_used=live_network_used,
        )
        result.validate()
        return result

    def _fetch_live_payload(self, scheduled_item: ScheduledCollectionItem) -> Dict[str, Any]:
        query = urlencode({"query": scheduled_item.query_text, "hitsPerPage": scheduled_item.max_results})
        url = f"{HN_ALGOLIA_BASE_URL}/{self.endpoint}?{query}"
        with urlopen(url, timeout=self.timeout_seconds) as response:
            data = response.read().decode("utf-8", errors="replace")
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise ValueError("HN Algolia response must be a JSON object")
        return payload


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""
