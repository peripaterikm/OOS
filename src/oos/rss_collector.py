from __future__ import annotations

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from typing import Any, List, Optional
from urllib.request import Request, urlopen

from .collection_scheduler import ScheduledCollectionItem
from .collectors import BaseCollector, CollectionResult
from .models import RawEvidence, compute_raw_evidence_content_hash


RSS_SOURCE_ID = "rss_feeds"
RSS_SOURCE_TYPE = "rss_feed"
RSS_SOURCE_NAME = "RSS / Regulator / Changelog Feeds"


def parse_rss_feed(
    xml_text: str,
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "rss_feed_fixture",
    collected_at: str = "1970-01-01T00:00:00+00:00",
    author_or_context: str = "public feed item",
) -> List[RawEvidence]:
    try:
        root = ET.fromstring(xml_text or "")
    except ET.ParseError:
        return []

    channel_node = _first_child(root, "channel")
    channel = channel_node if channel_node is not None else root
    feed_title = _child_text(channel, "title")
    items = [child for child in list(channel) if _local_name(child.tag) == "item"]
    if not items and _local_name(root.tag) == "feed":
        items = [child for child in list(root) if _local_name(child.tag) == "entry"]

    evidence: List[RawEvidence] = []
    seen_ids: set[str] = set()
    for item in items:
        raw = rss_item_to_raw_evidence(
            item,
            scheduled_item=scheduled_item,
            collection_method=collection_method,
            collected_at=collected_at,
            feed_title=feed_title,
            author_or_context=author_or_context,
        )
        if raw is None or raw.evidence_id in seen_ids:
            continue
        evidence.append(raw)
        seen_ids.add(raw.evidence_id)
        if len(evidence) >= scheduled_item.max_results:
            break
    return evidence


def rss_item_to_raw_evidence(
    item: ET.Element,
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "rss_feed_fixture",
    collected_at: str = "1970-01-01T00:00:00+00:00",
    feed_title: str = "",
    author_or_context: str = "public feed item",
) -> Optional[RawEvidence]:
    guid = _child_text(item, "guid", "id")
    link = _rss_link(item)
    title = _child_text(item, "title")
    description = _child_text(item, "description", "summary", "encoded", "content")
    identity = _first_non_empty(guid, link, title)
    if not identity:
        return None

    digest = hashlib.sha256(_normalize_identity(identity).encode("utf-8")).hexdigest()[:16]
    title = _first_non_empty(title, f"RSS item {digest}")
    body = _first_non_empty(_clean_text(description), title)
    source_url = _first_non_empty(link, f"rss://item/{digest}")
    categories = [_clean_text(child.text or "") for child in item if _local_name(child.tag) == "category"]

    metadata = {
        "guid": guid,
        "pubDate": _child_text(item, "pubDate", "published", "updated"),
        "feed_title": feed_title,
        "categories": [category for category in categories if category],
        "original_author_present": bool(_child_text(item, "author", "creator")),
        "query_plan_id": scheduled_item.query_plan_id,
        "dedup_key": scheduled_item.dedup_key,
    }

    evidence = RawEvidence(
        evidence_id=f"raw_rss_{digest}",
        source_id=scheduled_item.source_id,
        source_type=scheduled_item.source_type,
        source_name=RSS_SOURCE_NAME,
        source_url=source_url,
        collected_at=collected_at,
        title=title,
        body=body,
        language="unknown",
        topic_id=scheduled_item.topic_id,
        query_kind=scheduled_item.query_kind,
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context=author_or_context,
        raw_metadata=metadata,
        access_policy="public_rss_feed_no_scraping_outside_feed_fixture_or_live_disabled_default",
        collection_method=collection_method,
    )
    evidence.validate()
    return evidence


class RSSFeedCollector(BaseCollector):
    def __init__(
        self,
        *,
        source_id: str = RSS_SOURCE_ID,
        allow_live_network: bool = False,
        fixture_xml: Optional[str] = None,
        timeout_seconds: int = 10,
        feed_url: Optional[str] = None,
        author_or_context: str = "public feed item",
    ):
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("RSSFeedCollector.timeout_seconds must be a positive int")
        self.source_id = source_id
        self.allow_live_network = allow_live_network
        self.fixture_xml = fixture_xml
        self.timeout_seconds = timeout_seconds
        self.feed_url = feed_url
        self.author_or_context = author_or_context

    def supports(self, scheduled_item: ScheduledCollectionItem) -> bool:
        scheduled_item.validate()
        return scheduled_item.source_id == self.source_id and scheduled_item.source_type == RSS_SOURCE_TYPE

    def collect(self, scheduled_item: ScheduledCollectionItem) -> CollectionResult:
        scheduled_item.validate()
        if not self.supports(scheduled_item):
            raise ValueError("RSSFeedCollector does not support scheduled item source")

        xml_text = self.fixture_xml
        collection_method = "rss_feed_fixture"
        live_network_used = False

        if xml_text is None:
            if not self.allow_live_network or not scheduled_item.live_network_enabled:
                xml_text = "<rss><channel></channel></rss>"
            else:
                xml_text = self._fetch_live_payload(scheduled_item)
                collection_method = "rss_feed"
                live_network_used = True

        evidence = parse_rss_feed(
            xml_text,
            scheduled_item=scheduled_item,
            collection_method=collection_method,
            author_or_context=self.author_or_context,
        )
        result = CollectionResult(
            scheduled_item=scheduled_item,
            evidence=evidence,
            collector_name="rss_feed_collector",
            live_network_used=live_network_used,
        )
        result.validate()
        return result

    def _fetch_live_payload(self, scheduled_item: ScheduledCollectionItem) -> str:
        url = _first_non_empty(self.feed_url, scheduled_item.query_text)
        request = Request(url, headers={"User-Agent": "OOS-source-intelligence-fixture-first"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8")


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_child(element: ET.Element, *names: str) -> Optional[ET.Element]:
    wanted = set(names)
    for child in list(element):
        if _local_name(child.tag) in wanted:
            return child
    return None


def _child_text(element: ET.Element, *names: str) -> str:
    child = _first_child(element, *names)
    if child is None:
        return ""
    return _clean_text(child.text or "")


def _rss_link(item: ET.Element) -> str:
    link = _child_text(item, "link")
    if link:
        return link
    for child in list(item):
        if _local_name(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
    return ""


def _clean_text(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_identity(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()
