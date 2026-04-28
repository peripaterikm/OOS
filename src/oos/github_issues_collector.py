from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .collection_scheduler import ScheduledCollectionItem
from .collectors import BaseCollector, CollectionResult
from .models import RawEvidence, compute_raw_evidence_content_hash


GITHUB_ISSUES_SOURCE_ID = "github_issues"
GITHUB_ISSUES_SOURCE_TYPE = "github_issues"
GITHUB_ISSUES_SOURCE_NAME = "GitHub Issues"
GITHUB_SEARCH_ISSUES_URL = "https://api.github.com/search/issues"


def github_issue_to_raw_evidence(
    issue: Dict[str, Any],
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "github_issues_fixture",
    skip_pull_requests: bool = True,
) -> Optional[RawEvidence]:
    if skip_pull_requests and isinstance(issue.get("pull_request"), dict):
        return None

    issue_id = _first_non_empty(issue.get("id"), issue.get("node_id"), issue.get("number"))
    if not issue_id:
        return None

    title = _first_non_empty(issue.get("title"), f"GitHub issue {issue_id}")
    body = _first_non_empty(issue.get("body"), title)
    source_url = _first_non_empty(issue.get("html_url"), issue.get("url"), f"github://issues/{issue_id}")
    collected_at = _first_non_empty(issue.get("created_at"), "1970-01-01T00:00:00+00:00")

    metadata = {
        "issue_id": issue.get("id"),
        "node_id": issue.get("node_id"),
        "number": issue.get("number"),
        "repository_url": issue.get("repository_url"),
        "comments_url": issue.get("comments_url"),
        "labels": _label_names(issue.get("labels")),
        "state": issue.get("state"),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "closed_at": issue.get("closed_at"),
        "comments_count": issue.get("comments"),
        "reactions": _safe_reactions(issue.get("reactions")),
        "pull_request_present": isinstance(issue.get("pull_request"), dict),
        "user_present": isinstance(issue.get("user"), dict) and bool(issue.get("user")),
        "query_plan_id": scheduled_item.query_plan_id,
        "dedup_key": scheduled_item.dedup_key,
    }

    evidence = RawEvidence(
        evidence_id=f"raw_github_issue_{issue_id}",
        source_id=scheduled_item.source_id,
        source_type=scheduled_item.source_type,
        source_name=GITHUB_ISSUES_SOURCE_NAME,
        source_url=source_url,
        collected_at=collected_at,
        title=title,
        body=body,
        language="unknown",
        topic_id=scheduled_item.topic_id,
        query_kind=scheduled_item.query_kind,
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="unverified public issue reporter",
        raw_metadata=metadata,
        access_policy="public_github_issues_fixture_or_live_disabled_default",
        collection_method=collection_method,
    )
    evidence.validate()
    return evidence


def parse_github_issues(
    payload: Any,
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "github_issues_fixture",
    skip_pull_requests: bool = True,
) -> List[RawEvidence]:
    if isinstance(payload, dict):
        issues = payload.get("items", [])
    elif isinstance(payload, list):
        issues = payload
    else:
        issues = []
    if not isinstance(issues, list):
        return []

    evidence: List[RawEvidence] = []
    seen_ids: set[str] = set()
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        item = github_issue_to_raw_evidence(
            issue,
            scheduled_item=scheduled_item,
            collection_method=collection_method,
            skip_pull_requests=skip_pull_requests,
        )
        if item is None or item.evidence_id in seen_ids:
            continue
        evidence.append(item)
        seen_ids.add(item.evidence_id)
        if len(evidence) >= scheduled_item.max_results:
            break
    return evidence


class GitHubIssuesCollector(BaseCollector):
    def __init__(
        self,
        *,
        source_id: str = GITHUB_ISSUES_SOURCE_ID,
        allow_live_network: bool = False,
        fixture_payload: Optional[Any] = None,
        timeout_seconds: int = 10,
        skip_pull_requests: bool = True,
    ):
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("GitHubIssuesCollector.timeout_seconds must be a positive int")
        self.source_id = source_id
        self.allow_live_network = allow_live_network
        self.fixture_payload = fixture_payload
        self.timeout_seconds = timeout_seconds
        self.skip_pull_requests = skip_pull_requests

    def supports(self, scheduled_item: ScheduledCollectionItem) -> bool:
        scheduled_item.validate()
        return scheduled_item.source_id == self.source_id and scheduled_item.source_type == GITHUB_ISSUES_SOURCE_TYPE

    def collect(self, scheduled_item: ScheduledCollectionItem) -> CollectionResult:
        scheduled_item.validate()
        if not self.supports(scheduled_item):
            raise ValueError("GitHubIssuesCollector does not support scheduled item source")

        payload = self.fixture_payload
        collection_method = "github_issues_fixture"
        live_network_used = False

        if payload is None:
            if not self.allow_live_network or not scheduled_item.live_network_enabled:
                payload = {"items": []}
            else:
                payload = self._fetch_live_payload(scheduled_item)
                collection_method = "github_issues_search"
                live_network_used = True

        evidence = parse_github_issues(
            payload,
            scheduled_item=scheduled_item,
            collection_method=collection_method,
            skip_pull_requests=self.skip_pull_requests,
        )
        result = CollectionResult(
            scheduled_item=scheduled_item,
            evidence=evidence,
            collector_name="github_issues_collector",
            live_network_used=live_network_used,
        )
        result.validate()
        return result

    def _fetch_live_payload(self, scheduled_item: ScheduledCollectionItem) -> Dict[str, Any]:
        query = urlencode(
            {
                "q": f"{scheduled_item.query_text} is:issue",
                "per_page": scheduled_item.max_results,
            }
        )
        request = Request(
            f"{GITHUB_SEARCH_ISSUES_URL}?{query}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "OOS-source-intelligence-fixture-first",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            data = response.read().decode("utf-8")
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise ValueError("GitHub Issues response must be a JSON object")
        return payload


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _label_names(labels: Any) -> List[str]:
    if not isinstance(labels, list):
        return []
    names: List[str] = []
    for label in labels:
        if isinstance(label, dict):
            name = str(label.get("name") or "").strip()
        else:
            name = str(label or "").strip()
        if name:
            names.append(name)
    return names


def _safe_reactions(reactions: Any) -> Dict[str, Any]:
    if not isinstance(reactions, dict):
        return {}
    return {
        key: reactions.get(key)
        for key in ("total_count", "+1", "-1", "laugh", "hooray", "confused", "heart", "rocket", "eyes")
        if key in reactions
    }
