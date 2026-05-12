from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .collection_scheduler import ScheduledCollectionItem
from .collectors import BaseCollector, CollectionResult
from .models import RawEvidence, compute_raw_evidence_content_hash


# =========================================================================
# Canonical source identity (matching config/source_registry.json)
# =========================================================================
# "github_issues" is the canonical source_id per config/source_registry.json.
# "issue_tracker" is the canonical source_type per the discovery source adapter contract.
# =========================================================================

GH_CANONICAL_SOURCE_ID = "github_issues"
GH_CANONICAL_SOURCE_TYPE = "issue_tracker"
GH_CANONICAL_SOURCE_NAME = "GitHub Issues"

# Legacy source_type maintained for backward compatibility with existing
# source_registry.py (code registry), query_planner, and scheduler wiring.
GH_LEGACY_SOURCE_TYPE = "github_issues"

# Valid source_type values accepted by supports()
_VALID_GH_SOURCE_TYPES = {GH_CANONICAL_SOURCE_TYPE, GH_LEGACY_SOURCE_TYPE}

GITHUB_SEARCH_ISSUES_URL = "https://api.github.com/search/issues"


# =========================================================================
# evidence_kind classification — deterministic heuristics (no LLM)
# =========================================================================

_BUG_REPORT_KEYWORDS = [
    "bug", "broken", "crash", "error", "fails", "failure",
    "doesn't work", "not working", "incorrect", "wrong",
    "exception", "traceback", "regression",
]

_FEATURE_REQUEST_KEYWORDS = [
    "feature request", "please add", "would be great if",
    "would be nice", "wish it had", "should support",
    "it would be", "I'd love to see", "support for",
    "needs to support", "missing feature", "lacks",
]

_COMPLAINT_KEYWORDS = [
    "frustrating", "frustrated", "painful", "terrible",
    "hate", "nightmare", "unusable", "drives me crazy",
    "awful", "horrible", "ridiculous", "absurd",
    "waste of time", "should be easier", "too hard",
    "unacceptable",
]

_WORKAROUND_KEYWORDS = [
    "workaround", "hack", "spreadsheet", "manual process",
    "makeshift", "temporary solution", "script to",
    "export to CSV", "manual work", "duct tape",
    "jury rig", "kludge", "work around",
    "zapier", "ifttt", "cron job",
]

_PAIN_KEYWORDS = [
    "pain", "struggle", "blocker", "critical",
    "showstopper", "can't", "impossible to",
    "biggest problem", "so hard to", "hours of",
    "dealbreaker", "can't proceed",
]

_VALID_EVIDENCE_KINDS = {
    "bug_report",
    "feature_request",
    "complaint",
    "workaround",
    "pain_signal_candidate",
    "unknown",
}


# =========================================================================
# Noise / quality flag keywords — deterministic (no LLM)
# =========================================================================

_BOT_PATTERNS = [
    "dependabot", "renovate", "stale", "github-actions",
    "codecov", "coveralls", "sonarcloud", "imgbot",
    "allcontributors", "greenkeeper", "snyk-bot",
    "fossabot", "pyup-bot", "imgbotapp",
]

_MAINTAINER_HOUSEKEEPING_PREFIXES = [
    "chore", "build", "ci", "test", "refactor", "docs", "style",
]

_MAINTAINER_HOUSEKEEPING_PATTERNS = [
    "bump", "update dependency", "update dependencies",
    "upgrade dependency", "upgrade dependencies",
    "release v", "prepare v",
    "drop support for", "deprecate",
]

_VALID_QUALITY_FLAGS = {
    "bot_generated",
    "stale_issue",
    "low_text_context",
    "maintainer_housekeeping",
    "duplicate_or_invalid",
    "wontfix_or_not_planned",
    "source_access_limited",
    "requires_manual_review",
}


# =========================================================================
# GitHub-local source quality summary dataclass
# =========================================================================

@dataclass
class GitHubSourceQualitySummary:
    """GitHub-local source quality summary produced per collection batch.

    Lives alongside CollectionResult (not inside it, to avoid modifying
    the shared collectors.py module).
    """
    source_id: str = GH_CANONICAL_SOURCE_ID
    source_type: str = GH_CANONICAL_SOURCE_TYPE
    access_method: str = "github_search_api"
    records_seen: int = 0
    records_emitted: int = 0
    records_rejected: int = 0
    pr_filtered_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    duplicate_count: int = 0
    missing_url_count: int = 0
    placeholder_url_count: int = 0
    quality_flag_counts: Dict[str, int] = field(default_factory=dict)
    rejection_reasons: Dict[str, int] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("GitHubSourceQualitySummary.source_id must be a non-empty string")
        if not isinstance(self.source_type, str) or not self.source_type.strip():
            raise ValueError("GitHubSourceQualitySummary.source_type must be a non-empty string")
        for name in ("records_seen", "records_emitted", "records_rejected",
                     "pr_filtered_count", "warning_count", "error_count",
                     "duplicate_count", "missing_url_count", "placeholder_url_count"):
            val = getattr(self, name)
            if not isinstance(val, int) or val < 0:
                raise ValueError(f"GitHubSourceQualitySummary.{name} must be a non-negative int")


# =========================================================================
# Helper utilities
# =========================================================================

def _contains_any(text: str, keywords: list[str]) -> bool:
    """Return True if any keyword (case-insensitive) appears in text."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _classify_evidence_kind(issue: dict[str, Any]) -> str:
    """Deterministic evidence_kind classification for a GitHub issue.

    Uses title, body, labels, and keyword heuristics. No LLM calls.
    Priority: labels > keywords with heuristics.
    """
    labels = _label_names(issue.get("labels"))
    title = str(issue.get("title") or "")
    body = str(issue.get("body") or "")
    state = str(issue.get("state") or "")
    combined = f"{title} {body}".lower()
    labels_lower = [l.lower() for l in labels]

    # Label-based classification (highest priority)
    if "bug" in labels_lower:
        if _contains_any(combined, _PAIN_KEYWORDS):
            return "pain_signal_candidate"
        return "bug_report"

    if any(label in labels_lower for label in ("enhancement", "feature", "feature-request")):
        if _contains_any(combined, _PAIN_KEYWORDS):
            return "pain_signal_candidate"
        return "feature_request"

    if any(label in labels_lower for label in ("documentation", "docs")):
        return "unknown"

    if any(label in labels_lower for label in ("question", "support")):
        return "unknown"

    if any(label in labels_lower for label in ("duplicate", "invalid", "wontfix")):
        return "unknown"

    # Keyword-based classification
    if _contains_any(combined, _WORKAROUND_KEYWORDS):
        return "workaround"

    if _contains_any(combined, _PAIN_KEYWORDS):
        return "pain_signal_candidate"

    if _contains_any(combined, _BUG_REPORT_KEYWORDS):
        return "bug_report"

    if _contains_any(combined, _FEATURE_REQUEST_KEYWORDS):
        return "feature_request"

    if _contains_any(combined, _COMPLAINT_KEYWORDS):
        return "complaint"

    # Closed issues checked last
    if state == "closed":
        return "unknown"

    return "unknown"


def _compute_quality_flags(issue: dict[str, Any]) -> list[str]:
    """Deterministic quality/noise flags for a GitHub issue."""
    flags: list[str] = []
    labels = _label_names(issue.get("labels"))
    labels_lower = [l.lower() for l in labels]
    title = str(issue.get("title") or "")
    body = str(issue.get("body") or "")
    combined_text = f"{title} {body}".lower()
    user = issue.get("user") or {}
    user_login = str(user.get("login") or "").lower() if isinstance(user, dict) else ""

    # bot_generated
    is_bot = False
    if isinstance(user, dict):
        user_type = str(user.get("type") or "").lower()
        if user_type == "bot":
            is_bot = True
        elif any(pattern in user_login for pattern in _BOT_PATTERNS):
            is_bot = True
        elif user_login.endswith("[bot]") or user_login.endswith("-bot"):
            is_bot = True
    if is_bot:
        flags.append("bot_generated")

    # stale_issue: no updated_at OR updated > 365 days ago
    updated_at = issue.get("updated_at")
    if updated_at:
        try:
            from datetime import datetime, timezone, timedelta
            updated_dt = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - updated_dt
            if age > timedelta(days=365):
                flags.append("stale_issue")
        except (ValueError, TypeError):
            pass
    else:
        flags.append("stale_issue")

    # low_text_context
    if len(body) < 100:
        flags.append("low_text_context")

    # duplicate_or_invalid
    if "duplicate" in labels_lower or "invalid" in labels_lower:
        flags.append("duplicate_or_invalid")

    # wontfix_or_not_planned
    if "wontfix" in labels_lower or issue.get("state_reason") == "not_planned":
        flags.append("wontfix_or_not_planned")

    # maintainer_housekeeping
    title_lower = title.lower()
    for prefix in _MAINTAINER_HOUSEKEEPING_PREFIXES:
        if title_lower.startswith(f"{prefix}:") or title_lower.startswith(f"{prefix}("):
            flags.append("maintainer_housekeeping")
            break
    else:
        for pattern in _MAINTAINER_HOUSEKEEPING_PATTERNS:
            if title_lower.startswith(pattern):
                flags.append("maintainer_housekeeping")
                break

    # source_access_limited: locked issue
    if issue.get("locked") is True:
        flags.append("source_access_limited")

    # requires_manual_review when any other flag is set
    if flags and "requires_manual_review" not in flags:
        flags.append("requires_manual_review")

    return flags


def _author_context_label(issue: dict[str, Any]) -> str:
    """Return a privacy-safe author_or_context label based on issue context."""
    user = issue.get("user") or {}
    user_login = str(user.get("login") or "").lower() if isinstance(user, dict) else ""
    labels = _label_names(issue.get("labels"))
    labels_lower = [l.lower() for l in labels]

    # Bot detection
    if isinstance(user, dict):
        user_type = str(user.get("type") or "").lower()
        if user_type == "bot":
            return "automated system (bot)"
        if any(pattern in user_login for pattern in _BOT_PATTERNS):
            return "automated system (bot)"
        if user_login.endswith("[bot]") or user_login.endswith("-bot"):
            return "automated system (bot)"

    # Maintainer detection via author_association
    author_assoc = str(issue.get("author_association") or "").upper()
    if author_assoc in ("OWNER", "MEMBER", "COLLABORATOR"):
        return "project maintainer"

    # Label-based context hints
    if "bug" in labels_lower:
        return "bug reporter"
    if any(label in labels_lower for label in ("enhancement", "feature", "feature-request")):
        return "feature requester"

    return "issue reporter"


def _derive_repo_full_name(issue: dict[str, Any]) -> str:
    """Derive owner/repo from repository_url or html_url."""
    repo_url = str(issue.get("repository_url") or "")
    html_url = str(issue.get("html_url") or "")
    # repository_url: https://api.github.com/repos/{owner}/{repo}
    if repo_url.startswith("https://api.github.com/repos/"):
        return repo_url[len("https://api.github.com/repos/"):].strip("/")
    # html_url: https://github.com/{owner}/{repo}/issues/{number}
    if html_url.startswith("https://github.com/"):
        parts = html_url[len("https://github.com/"):].split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    return ""


def _derive_categories(labels: list[str]) -> list[str]:
    """Derive human-readable categories from issue labels."""
    categories: list[str] = []
    labels_lower = [l.lower() for l in labels]
    if "bug" in labels_lower:
        categories.append("bug")
    if any(l in labels_lower for l in ("enhancement", "feature", "feature-request")):
        categories.append("enhancement")
    if "documentation" in labels_lower:
        categories.append("documentation")
    if "question" in labels_lower:
        categories.append("question")
    if "help wanted" in labels_lower:
        categories.append("help-wanted")
    if "good first issue" in labels_lower:
        categories.append("good-first-issue")
    return categories


# =========================================================================
# Repo allowlist support
# =========================================================================

def _load_repo_allowlist(allowlist: Optional[list[str]] = None) -> Optional[list[str]]:
    """Return the repo allowlist, or None if no allowlist is configured.

    If allowlist is None, all repos are allowed (no filtering).
    If allowlist is an empty list, no repos are allowed.
    """
    return allowlist


def _is_allowlisted(repo_full_name: str, allowlist: Optional[list[str]]) -> bool:
    """Check if a repo full name is in the allowlist (case-insensitive)."""
    if allowlist is None:
        return True
    repo_lower = repo_full_name.lower()
    return any(allowed.lower() == repo_lower for allowed in allowlist)


# =========================================================================
# Issue conversion and parsing
# =========================================================================

def github_issue_to_raw_evidence(
    issue: dict[str, Any],
    *,
    scheduled_item: ScheduledCollectionItem,
    collection_method: str = "fixture",
    quality_summary: Optional[GitHubSourceQualitySummary] = None,
    repo_allowlist: Optional[list[str]] = None,
) -> Optional[RawEvidence]:
    """Convert a single GitHub issue into a RawEvidence record.

    Emits canonical source_id="github_issues" and source_type="issue_tracker".
    Rejects PRs, items with missing html_url, and items with missing id.
    Updates quality_summary in-place when provided.
    """
    # --- Pull request filtering (mandatory) ---
    if isinstance(issue.get("pull_request"), dict):
        if quality_summary is not None:
            quality_summary.pr_filtered_count += 1
            quality_summary.rejection_reasons["pull_request"] = \
                quality_summary.rejection_reasons.get("pull_request", 0) + 1
        return None

    # --- Missing node_id / issue_id ---
    issue_id = _first_non_empty(issue.get("node_id"), issue.get("id"), issue.get("number"))
    if not issue_id:
        if quality_summary is not None:
            quality_summary.records_rejected += 1
            quality_summary.rejection_reasons["missing_node_id"] = \
                quality_summary.rejection_reasons.get("missing_node_id", 0) + 1
        return None

    # --- source_url: only html_url (no github:// fallback) ---
    html_url = str(issue.get("html_url") or "").strip()
    if not html_url or not (html_url.startswith("https://github.com/") or html_url.startswith("http://github.com/")):
        if quality_summary is not None:
            quality_summary.missing_url_count += 1
            quality_summary.records_rejected += 1
            quality_summary.rejection_reasons["missing_source_url"] = \
                quality_summary.rejection_reasons.get("missing_source_url", 0) + 1
        return None
    source_url = html_url

    # --- Repo allowlist ---
    repo_full_name = _derive_repo_full_name(issue)
    if not _is_allowlisted(repo_full_name, repo_allowlist):
        if quality_summary is not None:
            quality_summary.records_rejected += 1
            quality_summary.rejection_reasons["not_in_allowlist"] = \
                quality_summary.rejection_reasons.get("not_in_allowlist", 0) + 1
        return None

    # --- Title and body ---
    title = _first_non_empty(issue.get("title"), f"GitHub issue {issue_id}")
    body = _first_non_empty(issue.get("body"), title)

    # --- Timestamps ---
    collected_at = _first_non_empty(issue.get("created_at"), "1970-01-01T00:00:00+00:00")
    created_at = issue.get("created_at")
    updated_at = issue.get("updated_at")

    # --- Labels and tags ---
    labels = _label_names(issue.get("labels"))
    tags = list(labels)

    # --- Classification ---
    evidence_kind = _classify_evidence_kind(issue)
    quality_flags = _compute_quality_flags(issue)

    # --- Engagement metrics ---
    comments_count = issue.get("comments")
    reactions = _safe_reactions(issue.get("reactions"))
    engagement = {}
    if isinstance(comments_count, (int, float)):
        engagement["comments"] = comments_count
    if reactions:
        engagement["reactions"] = reactions

    # --- Categories ---
    categories = _derive_categories(labels)

    # --- Raw metadata ---
    metadata: dict[str, Any] = {
        "issue_id": issue.get("id"),
        "node_id": issue.get("node_id"),
        "number": issue.get("number"),
        "repository_url": issue.get("repository_url"),
        "comments_url": issue.get("comments_url"),
        "labels": labels,
        "state": issue.get("state"),
        "state_reason": issue.get("state_reason"),
        "created_at": created_at,
        "updated_at": updated_at,
        "closed_at": issue.get("closed_at"),
        "comments_count": comments_count,
        "reactions": reactions,
        "pull_request_present": isinstance(issue.get("pull_request"), dict),
        "user_present": isinstance(issue.get("user"), dict) and bool(issue.get("user")),
        "author_association": issue.get("author_association"),
        "locked": issue.get("locked"),
        "query_plan_id": scheduled_item.query_plan_id,
        "dedup_key": scheduled_item.dedup_key,
        # v2.12 hardened additions
        "repo_full_name": repo_full_name,
        "evidence_kind": evidence_kind,
        "quality_flags": quality_flags,
        "item_text_length": len(body),
        "engagement_metrics": engagement,
        "categories": categories,
        "source_specific_id": str(issue.get("node_id") or issue_id),
        "canonical_url": source_url,
    }

    # Track quality flags in summary
    if quality_summary is not None and quality_flags:
        for flag in quality_flags:
            quality_summary.quality_flag_counts[flag] = \
                quality_summary.quality_flag_counts.get(flag, 0) + 1

    evidence = RawEvidence(
        evidence_id=f"raw_github_issue_{issue_id}",
        source_id=GH_CANONICAL_SOURCE_ID,
        source_type=GH_CANONICAL_SOURCE_TYPE,
        source_name=GH_CANONICAL_SOURCE_NAME,
        source_url=source_url,
        collected_at=collected_at,
        title=title,
        body=body,
        language="unknown",
        topic_id=scheduled_item.topic_id,
        query_kind=scheduled_item.query_kind,
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context=_author_context_label(issue),
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
    collection_method: str = "fixture",
    quality_summary: Optional[GitHubSourceQualitySummary] = None,
    repo_allowlist: Optional[list[str]] = None,
) -> List[RawEvidence]:
    """Parse a GitHub Search API response into RawEvidence records.

    Populates quality_summary in-place when provided.
    """
    if isinstance(payload, dict):
        issues = payload.get("items", [])
    elif isinstance(payload, list):
        issues = payload
    else:
        issues = []

    if not isinstance(issues, list):
        if quality_summary is not None:
            quality_summary.error_count += 1
        return []

    if quality_summary is not None:
        quality_summary.records_seen += len(issues)

    evidence: List[RawEvidence] = []
    seen_ids: set[str] = set()
    for issue in issues:
        if not isinstance(issue, dict):
            if quality_summary is not None:
                quality_summary.records_rejected += 1
                quality_summary.rejection_reasons["non_dict_hit"] = \
                    quality_summary.rejection_reasons.get("non_dict_hit", 0) + 1
            continue

        item = github_issue_to_raw_evidence(
            issue,
            scheduled_item=scheduled_item,
            collection_method=collection_method,
            quality_summary=quality_summary,
            repo_allowlist=repo_allowlist,
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


def build_github_source_quality_summary(
    payload: Any,
    evidence: list[RawEvidence],
    *,
    collection_method: str = "fixture",
) -> GitHubSourceQualitySummary:
    """Build a complete GitHub-local source quality summary from payload and results.

    This is a companion to parse_github_issues for callers that don't
    pass an in-progress summary during parsing.
    """
    if isinstance(payload, dict):
        issues = payload.get("items", [])
    elif isinstance(payload, list):
        issues = payload
    else:
        issues = []
    issues = issues if isinstance(issues, list) else []

    summary = GitHubSourceQualitySummary(
        records_seen=len(issues),
        records_emitted=len(evidence),
        access_method=collection_method.replace("github_issues_", ""),
    )

    # Count quality flags from evidence metadata
    for ev in evidence:
        qf = ev.raw_metadata.get("quality_flags", [])
        if isinstance(qf, list):
            for flag in qf:
                if isinstance(flag, str):
                    summary.quality_flag_counts[flag] = \
                        summary.quality_flag_counts.get(flag, 0) + 1

    # Count warning-level conditions
    for ev in evidence:
        qf = ev.raw_metadata.get("quality_flags", [])
        if isinstance(qf, list) and qf:
            summary.warning_count += 1

    summary.validate()
    return summary


# =========================================================================
# Collector class
# =========================================================================

class GitHubIssuesCollector(BaseCollector):
    """GitHub Issues collector via GitHub REST/Search API.

    Emits canonical source_id="github_issues" and source_type="issue_tracker"
    on all RawEvidence records. Accepts both legacy ("github_issues") and
    canonical ("issue_tracker") source_type in supports() for backward
    compatibility with existing registry/scheduler wiring.
    """

    def __init__(
        self,
        *,
        source_id: str = GH_CANONICAL_SOURCE_ID,
        allow_live_network: bool = False,
        fixture_payload: Optional[Any] = None,
        timeout_seconds: int = 10,
        repo_allowlist: Optional[list[str]] = None,
    ):
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("GitHubIssuesCollector.timeout_seconds must be a positive int")
        self.source_id = source_id
        self.allow_live_network = allow_live_network
        self.fixture_payload = fixture_payload
        self.timeout_seconds = timeout_seconds
        self.repo_allowlist = repo_allowlist

    def supports(self, scheduled_item: ScheduledCollectionItem) -> bool:
        scheduled_item.validate()
        return (
            scheduled_item.source_id == self.source_id
            and scheduled_item.source_type in _VALID_GH_SOURCE_TYPES
        )

    def collect(self, scheduled_item: ScheduledCollectionItem) -> CollectionResult:
        scheduled_item.validate()
        if not self.supports(scheduled_item):
            raise ValueError("GitHubIssuesCollector does not support scheduled item source")

        payload = self.fixture_payload
        collection_method = "fixture"
        live_network_used = False

        if payload is None:
            if not self.allow_live_network or not scheduled_item.live_network_enabled:
                payload = {"items": []}
            else:
                payload = self._fetch_live_payload(scheduled_item)
                collection_method = "github_issues_search"
                live_network_used = True

        # Build a canonicalized scheduled_item for evidence output.
        # The incoming scheduled_item may carry legacy source_type
        # from the code registry; we normalize to canonical values for output.
        canonical_item = scheduled_item
        if scheduled_item.source_type != GH_CANONICAL_SOURCE_TYPE:
            canonical_item = replace(
                scheduled_item,
                source_type=GH_CANONICAL_SOURCE_TYPE,
            )

        quality_summary = GitHubSourceQualitySummary(
            access_method=collection_method.replace("github_issues_", ""),
        )

        evidence = parse_github_issues(
            payload,
            scheduled_item=canonical_item,
            collection_method=collection_method,
            quality_summary=quality_summary,
            repo_allowlist=self.repo_allowlist,
        )

        result = CollectionResult(
            scheduled_item=canonical_item,
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
            data = response.read().decode("utf-8", errors="replace")
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise ValueError("GitHub Issues response must be a JSON object")
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
