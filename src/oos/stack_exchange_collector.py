from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .collection_scheduler import ScheduledCollectionItem
from .collectors import BaseCollector, CollectionResult
from .models import RawEvidence, compute_raw_evidence_content_hash


STACK_EXCHANGE_SOURCE_ID = "stack_exchange"
STACK_EXCHANGE_SOURCE_TYPE = "stack_exchange"
STACK_EXCHANGE_SOURCE_NAME = "Stack Exchange"
STACK_EXCHANGE_SEARCH_URL = "https://api.stackexchange.com/2.3/search/advanced"


def stack_exchange_question_to_raw_evidence(
    question: Dict[str, Any],
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "stack_exchange_fixture",
) -> Optional[RawEvidence]:
    question_id = _first_non_empty(question.get("question_id"))
    if not question_id:
        return None

    title = _first_non_empty(question.get("title"), f"Stack Exchange question {question_id}")
    body = _first_non_empty(question.get("body"), question.get("excerpt"), title)
    source_url = _first_non_empty(question.get("link"), f"stackexchange://questions/{question_id}")
    collected_at = _timestamp_to_iso(question.get("creation_date"))

    metadata = {
        "question_id": question.get("question_id"),
        "answer_count": question.get("answer_count"),
        "is_answered": question.get("is_answered"),
        "score": question.get("score"),
        "view_count": question.get("view_count"),
        "tags": _string_list(question.get("tags")),
        "creation_date": question.get("creation_date"),
        "last_activity_date": question.get("last_activity_date"),
        "site": question.get("site") or question.get("api_site_parameter"),
        "owner_present": isinstance(question.get("owner"), dict) and bool(question.get("owner")),
        "query_plan_id": scheduled_item.query_plan_id,
        "dedup_key": scheduled_item.dedup_key,
    }

    evidence = RawEvidence(
        evidence_id=f"raw_stackexchange_question_{question_id}",
        source_id=scheduled_item.source_id,
        source_type=scheduled_item.source_type,
        source_name=STACK_EXCHANGE_SOURCE_NAME,
        source_url=source_url,
        collected_at=collected_at,
        title=title,
        body=body,
        language="unknown",
        topic_id=scheduled_item.topic_id,
        query_kind=scheduled_item.query_kind,
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="unverified public question asker",
        raw_metadata=metadata,
        access_policy="public_stack_exchange_api_registered_app_key_for_high_volume_fixture_or_live_disabled_default",
        collection_method=collection_method,
    )
    evidence.validate()
    return evidence


def parse_stack_exchange_questions(
    payload: Any,
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "stack_exchange_fixture",
) -> List[RawEvidence]:
    if isinstance(payload, dict):
        questions = payload.get("items", [])
    elif isinstance(payload, list):
        questions = payload
    else:
        questions = []
    if not isinstance(questions, list):
        return []

    evidence: List[RawEvidence] = []
    seen_ids: set[str] = set()
    for question in questions:
        if not isinstance(question, dict):
            continue
        item = stack_exchange_question_to_raw_evidence(
            question,
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


class StackExchangeCollector(BaseCollector):
    def __init__(
        self,
        *,
        source_id: str = STACK_EXCHANGE_SOURCE_ID,
        allow_live_network: bool = False,
        fixture_payload: Optional[Any] = None,
        timeout_seconds: int = 10,
        site: str = "stackoverflow",
    ):
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("StackExchangeCollector.timeout_seconds must be a positive int")
        if not isinstance(site, str) or not site.strip():
            raise ValueError("StackExchangeCollector.site must be a non-empty string")
        self.source_id = source_id
        self.allow_live_network = allow_live_network
        self.fixture_payload = fixture_payload
        self.timeout_seconds = timeout_seconds
        self.site = site

    def supports(self, scheduled_item: ScheduledCollectionItem) -> bool:
        scheduled_item.validate()
        return scheduled_item.source_id == self.source_id and scheduled_item.source_type == STACK_EXCHANGE_SOURCE_TYPE

    def collect(self, scheduled_item: ScheduledCollectionItem) -> CollectionResult:
        scheduled_item.validate()
        if not self.supports(scheduled_item):
            raise ValueError("StackExchangeCollector does not support scheduled item source")

        payload = self.fixture_payload
        collection_method = "stack_exchange_fixture"
        live_network_used = False

        if payload is None:
            if not self.allow_live_network or not scheduled_item.live_network_enabled:
                payload = {"items": []}
            else:
                payload = self._fetch_live_payload(scheduled_item)
                collection_method = "stack_exchange_search"
                live_network_used = True

        evidence = parse_stack_exchange_questions(
            payload,
            scheduled_item=scheduled_item,
            collection_method=collection_method,
        )
        result = CollectionResult(
            scheduled_item=scheduled_item,
            evidence=evidence,
            collector_name="stack_exchange_collector",
            live_network_used=live_network_used,
        )
        result.validate()
        return result

    def _fetch_live_payload(self, scheduled_item: ScheduledCollectionItem) -> Dict[str, Any]:
        query = urlencode(
            {
                "q": scheduled_item.query_text,
                "site": self.site,
                "pagesize": scheduled_item.max_results,
                "filter": "withbody",
            }
        )
        request = Request(
            f"{STACK_EXCHANGE_SEARCH_URL}?{query}",
            headers={"User-Agent": "OOS-source-intelligence-fixture-first"},
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            data = response.read().decode("utf-8")
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise ValueError("Stack Exchange response must be a JSON object")
        return payload


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _string_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _timestamp_to_iso(value: Any) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="seconds")
    text = str(value or "").strip()
    return text or "1970-01-01T00:00:00+00:00"
