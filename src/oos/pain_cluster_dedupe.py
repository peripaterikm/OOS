from __future__ import annotations

"""Cross-source deduplication and source normalization helpers.

Provides deterministic helpers for:
- Source ID / source_type normalization (legacy → canonical)
- Exact evidence_id dedupe
- Canonical URL dedupe
- Source URL dedupe
- Duplicate tracking with provenance preservation

No LLM calls. No live APIs. Deterministic only.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Canonical source_id / source_type registry
# ---------------------------------------------------------------------------

CANONICAL_SOURCE_IDS: frozenset[str] = frozenset({"hacker_news", "github_issues"})

CANONICAL_SOURCE_TYPES: frozenset[str] = frozenset({"discussion", "issue_tracker"})

# Legacy → canonical source_id mapping.
# "hacker_news_algolia" is an access method, not a canonical source_id.
SOURCE_ID_NORMALIZATION: dict[str, str] = {
    "hacker_news_algolia": "hacker_news",
}

# Legacy → canonical source_type mapping.
# Some existing code references source_type="github_issues" or
# source_type="hacker_news_algolia" as a source_type value.
SOURCE_TYPE_NORMALIZATION: dict[str, str] = {
    "github_issues": "issue_tracker",       # legacy: source_id mistaken as source_type
    "hacker_news_algolia": "discussion",     # legacy: access method mistaken as source_type
    "hacker_news": "discussion",             # canonical source_id → canonical source_type
    "github_issues_id": "issue_tracker",     # defensive
}


def normalize_source_id(source_id: str) -> str:
    """Map legacy source_id to canonical source_id.

    Examples:
        "hacker_news_algolia" → "hacker_news"
        "hacker_news" → "hacker_news" (unchanged)
        "github_issues" → "github_issues" (unchanged)
    """
    return SOURCE_ID_NORMALIZATION.get(source_id, source_id)


def normalize_source_type(source_type: str) -> str:
    """Map legacy source_type to canonical source_type.

    Examples:
        "github_issues" → "issue_tracker"
        "hacker_news_algolia" → "discussion"
        "discussion" → "discussion" (unchanged)
        "issue_tracker" → "issue_tracker" (unchanged)
    """
    return SOURCE_TYPE_NORMALIZATION.get(source_type, source_type)


def is_canonical_source_id(source_id: str) -> bool:
    """Return True if source_id is a canonical (non-legacy) value."""
    return source_id in CANONICAL_SOURCE_IDS


def is_canonical_source_type(source_type: str) -> bool:
    """Return True if source_type is a canonical value."""
    return source_type in CANONICAL_SOURCE_TYPES


def normalize_evidence_source(evidence: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of an evidence dict with source_id/source_type normalized.

    Does NOT mutate the input. Returns a new dict.
    """
    result = dict(evidence)
    if "source_id" in result:
        result["source_id"] = normalize_source_id(str(result["source_id"]))
    if "source_type" in result:
        result["source_type"] = normalize_source_type(str(result["source_type"]))
    return result


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------


def dedupe_by_evidence_id(
    evidence_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deduplicate by exact evidence_id. First occurrence wins.

    Returns:
        (unique, duplicates) — duplicates have duplicate_of set.
        Provenance is preserved: duplicate records are traceable.
    """
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []

    for ev in evidence_list:
        eid = str(ev.get("evidence_id", ""))
        if not eid:
            unique.append(ev)
            continue
        if eid in seen:
            dup = dict(ev)
            dup["duplicate_of"] = eid
            duplicates.append(dup)
        else:
            seen.add(eid)
            unique.append(dict(ev))

    return unique, duplicates


def dedupe_by_canonical_url(
    evidence_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deduplicate by canonical_url when available.

    If evidence items share the same canonical_url but have different
    evidence_ids, the second and subsequent are marked as duplicates.
    First occurrence wins.

    Returns:
        (unique, duplicates) — duplicates have duplicate_of set.
    """
    seen_urls: dict[str, str] = {}  # canonical_url → first evidence_id
    unique: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []

    for ev in evidence_list:
        canonical = (ev.get("canonical_url") or "").strip()
        if not canonical:
            unique.append(dict(ev))
            continue
        if canonical in seen_urls:
            dup = dict(ev)
            dup["duplicate_of"] = seen_urls[canonical]
            duplicates.append(dup)
        else:
            eid = str(ev.get("evidence_id", ""))
            seen_urls[canonical] = eid
            unique.append(dict(ev))

    return unique, duplicates


def dedupe_by_source_url(
    evidence_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deduplicate by source_url.

    Items with the same source_url are considered the same evidence
    (possibly fetched via different queries). First occurrence wins.

    Returns:
        (unique, duplicates) — duplicates have duplicate_of set.
    """
    seen_urls: dict[str, str] = {}  # source_url → first evidence_id
    unique: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []

    for ev in evidence_list:
        url = (ev.get("source_url") or "").strip()
        if not url:
            unique.append(dict(ev))
            continue
        if url in seen_urls:
            dup = dict(ev)
            dup["duplicate_of"] = seen_urls[url]
            duplicates.append(dup)
        else:
            eid = str(ev.get("evidence_id", ""))
            seen_urls[url] = eid
            unique.append(dict(ev))

    return unique, duplicates


def dedupe_full(
    evidence_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run all dedupe passes in order: evidence_id → canonical_url → source_url.

    This is the recommended entry point for full deduplication.
    Preserves provenance: all duplicates are returned with duplicate_of
    set to the first occurrence's evidence_id.

    Returns:
        (unique, all_duplicates)
    """
    current, dups1 = dedupe_by_evidence_id(evidence_list)
    current, dups2 = dedupe_by_canonical_url(current)
    current, dups3 = dedupe_by_source_url(current)

    all_duplicates = dups1 + dups2 + dups3
    return current, all_duplicates


# ---------------------------------------------------------------------------
# Cross-source dedupe policy helpers
# ---------------------------------------------------------------------------


def should_preserve_as_separate(
    ev1: dict[str, Any],
    ev2: dict[str, Any],
) -> bool:
    """Determine if two records should be preserved as separate despite
    appearing similar, because they come from different sources.

    Cross-source records provide source diversity and should not be
    silently dropped even if they reference similar content.
    """
    sid1 = normalize_source_id(str(ev1.get("source_id", "")))
    sid2 = normalize_source_id(str(ev2.get("source_id", "")))
    return sid1 != sid2


def compute_source_diversity(
    evidence_list: list[dict[str, Any]],
) -> int:
    """Count distinct canonical source_id values across evidence items.

    Legacy source_ids are normalized before counting.
    Returns at least 1 if evidence_list is non-empty.
    """
    if not evidence_list:
        return 0
    source_ids: set[str] = set()
    for ev in evidence_list:
        sid = normalize_source_id(str(ev.get("source_id", "")))
        if sid:
            source_ids.add(sid)
    return max(1, len(source_ids))
