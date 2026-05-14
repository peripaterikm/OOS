from __future__ import annotations

"""Deterministic noise classification based on quality_flags, evidence_kind, and content signals.

Provides a single function classify_noise() that maps quality flags and content
signals to one of three outcomes: accepted, weak, noise.

This module is the implementation of v2.14 item 1 — Noise Classification Hardening.
It ensures that evidence with clear noise/risk flags is not reported as clean accepted.

Classification rules (priority order):
1. Severe/fatal flags → noise (overrides everything)
2. low_text_context + no clear pain → noise
3. low_text_context + clear pain → weak (never accepted)
4. suspected_self_promo / vendor_promo + product_launch + no clear pain → noise
5. generic_language + unclear_actor / missing_actor + no clear pain → noise
6. Medium-risk flags → weak (stale_issue + strong pain → accepted exception)
7. No negative flags → accepted
"""

import re
from typing import Any

# ---------------------------------------------------------------------------
# Classification outcomes
# ---------------------------------------------------------------------------

ACCEPTED = "accepted"
WEAK = "weak"
NOISE = "noise"

# ---------------------------------------------------------------------------
# Flag alias mapping
# ---------------------------------------------------------------------------

_FLAG_ALIASES: dict[str, str] = {
    "vendor_promo": "suspected_self_promo",
    "missing_actor": "unclear_actor",
}

# ---------------------------------------------------------------------------
# Flag severity groups
# ---------------------------------------------------------------------------

# Severe/fatal quality flags — classify as NOISE immediately
SEVERE_NOISE_FLAGS: frozenset[str] = frozenset({
    "source_scope_violation",
    "traceability_failure",
    "invalid_source_url",
    "missing_source_url",
    "placeholder_source_url",
    "non_http_source_url",
    "bot_generated",
    "maintainer_housekeeping",
    "flamewar_or_meta_discussion",
})

# Medium-risk quality flags — classify as WEAK unless overridden
MEDIUM_NOISE_FLAGS: frozenset[str] = frozenset({
    "requires_manual_review",
    "suspected_self_promo",
    "launch_hype",
    "low_confidence_source",
    "low_confidence_extraction",
    "generic_language",
    "stale_issue",
    "duplicate_or_invalid",
    "wontfix_or_not_planned",
    "wishlist_without_pain",
    "one_off_bug",
    "unclear_actor",
    "unclear_workflow",
    "unclear_buyer",
    "no_business_cost",
})

# Positive/contextual flags — do NOT by themselves make evidence noise
# These are pain indicators that signal quality, not noise risk.
POSITIVE_PAIN_FLAGS: frozenset[str] = frozenset({
    "integration_pain",
    "debugging_pain",
    "reliability_pain",
    "workflow_pain",
    "business_cost_signal",
    "workaround_signal",
})

# ---------------------------------------------------------------------------
# Pain marker terms for detecting clear/strong pain in text
# ---------------------------------------------------------------------------

# Single-word markers: must match word boundaries only (regex \\b).
# "bug" must NOT match inside "debugging".
_SINGLE_WORD_PAIN_MARKERS: tuple[str, ...] = (
    "problem",
    "pain",
    "struggle",
    "broken",
    "frustrating",
    "frustrated",
    "issue",
    "bug",
    "expensive",
    "costs",
    "costing",
    "wasting",
    "manual",
    "workaround",
    "spreadsheet",
    "hack",
    "hours",
    "days",
    "weeks",
    "deadline",
    "blocked",
    "critical",
    "urgent",
    "lost",
    "losing",
    "failed",
    "fails",
    "crash",
    "crashes",
    "error",
    "errors",
    "slow",
    "unreliable",
    "missing",
    "lacks",
    "need",
    "wish",
    "please",
    "help",
)

# Phrase markers: matched as substrings in normalized text.
# These are specific enough that accidental substring matches are unlikely.
_PHRASE_PAIN_MARKERS: tuple[str, ...] = (
    "hard to",
    "can't",
    "cannot",
    "doesn't work",
    "would like",
    "how do i",
    "anyone else",
    "does anyone",
)

# Combined set of all pain marker terms for _has_strong_pain count.
_ALL_PAIN_MARKER_TERMS: tuple[str, ...] = _SINGLE_WORD_PAIN_MARKERS + _PHRASE_PAIN_MARKERS

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_noise(
    *,
    quality_flags: list[str] | None = None,
    evidence_kind: str = "",
    title: str = "",
    body: str = "",
    excerpt: str = "",
    source_url: str = "",
) -> str:
    """Deterministic noise classification based on quality flags and content signals.

    Returns one of: ``"accepted"``, ``"weak"``, ``"noise"``.

    Classification rules (in priority order):

    1. **Severe/fatal flags** → ``"noise"`` (overrides everything).
       Includes: source_scope_violation, traceability_failure, invalid_source_url,
       missing_source_url, placeholder_source_url, non_http_source_url,
       bot_generated, maintainer_housekeeping, flamewar_or_meta_discussion.

    2. **low_text_context + no clear pain** → ``"noise"``.
       Evidence with too little text and no pain markers is noise.

    3. **low_text_context + clear pain** → ``"weak"``.
       Low-text evidence with pain is suspicious but not clean. Never accepted.

    4. **suspected_self_promo / vendor_promo + product_launch + no clear pain** → ``"noise"``.
       Self-promotional launch announcements without pain evidence.
       (vendor_promo is an alias for suspected_self_promo.)

    5. **generic_language + unclear_actor/missing_actor + no clear pain** → ``"noise"``.
       Vague, actor-less text with no concrete pain.
       (missing_actor is an alias for unclear_actor.)

    6. **Medium-risk flags** → ``"weak"`` (needs human review).
       Includes: requires_manual_review, suspected_self_promo, vendor_promo,
       launch_hype, low_confidence_source, low_confidence_extraction,
       generic_language, stale_issue, duplicate_or_invalid,
       wontfix_or_not_planned, wishlist_without_pain, one_off_bug,
       unclear_actor, missing_actor, unclear_workflow, unclear_buyer,
       no_business_cost.

       Exception: ``stale_issue`` with strong pain evidence stays ``"accepted"``.

    7. **No negative flags, or only positive flags** → ``"accepted"``.

    Positive pain flags (integration_pain, debugging_pain, reliability_pain,
    workflow_pain, business_cost_signal, workaround_signal) do NOT by themselves
    make evidence noise.

    Args:
        quality_flags: List of quality flag strings from the evidence item.
        evidence_kind: The evidence kind (e.g., "product_launch", "pain_signal_candidate").
        title: Evidence title text.
        body: Evidence body text.
        excerpt: Evidence excerpt text.
        source_url: Source URL (used for traceability validation only in caller).

    Returns:
        "accepted", "weak", or "noise".
    """
    flags = [_normalize_flag(f) for f in (quality_flags or [])]
    flags = _resolve_aliases(flags)

    combined_text = f"{title} {body} {excerpt}".strip()
    has_clear_pain = _has_clear_pain(combined_text)
    has_strong_pain = _has_strong_pain(combined_text)

    # Rule 1: Severe flags → noise
    for flag in flags:
        if flag in SEVERE_NOISE_FLAGS:
            return NOISE

    # Rule 2: low_text_context + no clear pain → noise
    if "low_text_context" in flags and not has_clear_pain:
        return NOISE

    # Rule 3: low_text_context + clear pain → weak (never accepted by itself)
    if "low_text_context" in flags and has_clear_pain:
        return WEAK

    # Determine product_launch context
    is_product_launch = (
        evidence_kind.lower() in ("product_launch", "launch_hype")
        or "launch_hype" in flags
    )

    # Rule 4: suspected_self_promo + product_launch + no clear pain → noise
    has_self_promo = "suspected_self_promo" in flags
    if has_self_promo and is_product_launch and not has_clear_pain:
        return NOISE

    # Rule 5: generic_language + unclear_actor + no clear pain → noise
    has_generic = "generic_language" in flags
    has_unclear_actor = "unclear_actor" in flags
    if has_generic and has_unclear_actor and not has_clear_pain:
        return NOISE

    # Rule 6: Medium-risk flags → weak (with exceptions)
    medium_flags_present = [f for f in flags if f in MEDIUM_NOISE_FLAGS]
    if medium_flags_present:
        # Exception: stale_issue + strong pain → accepted
        if medium_flags_present == ["stale_issue"] and has_strong_pain:
            return ACCEPTED
        return WEAK

    # Rule 7: No negative flags → accepted
    # (positive flags like debugging_pain, integration_pain don't cause noise)
    return ACCEPTED


def classify_noise_for_evidence(evidence: dict[str, Any]) -> str:
    """Convenience wrapper that extracts fields from an evidence dict.

    Args:
        evidence: Evidence dict with fields: quality_flags, evidence_kind,
                  title, body, excerpt, source_url.

    Returns:
        "accepted", "weak", or "noise".
    """
    return classify_noise(
        quality_flags=evidence.get("quality_flags", []) or [],
        evidence_kind=str(evidence.get("evidence_kind", "") or ""),
        title=str(evidence.get("title", "") or ""),
        body=str(evidence.get("body", "") or ""),
        excerpt=str(evidence.get("excerpt", "") or ""),
        source_url=str(evidence.get("source_url", "") or ""),
    )


def classify_noise_for_signal(signal: dict[str, Any]) -> str:
    """Convenience wrapper that extracts fields from a candidate signal dict.

    Args:
        signal: Signal dict with fields: quality_flags, evidence_kind
                (may be missing), pain_summary (used as excerpt fallback).

    Returns:
        "accepted", "weak", or "noise".
    """
    return classify_noise(
        quality_flags=signal.get("quality_flags", []) or [],
        evidence_kind=str(signal.get("evidence_kind", "") or ""),
        title=str(signal.get("pain_summary", "") or ""),
        body="",
        excerpt="",
        source_url=str(signal.get("source_url", "") or ""),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_flag(flag: str) -> str:
    """Normalize a quality flag string to lowercase with underscores."""
    return str(flag or "").strip().lower().replace(" ", "_")


def _resolve_aliases(flags: list[str]) -> list[str]:
    """Resolve known flag aliases (e.g., vendor_promo → suspected_self_promo).

    Returns a new list with aliases resolved. Preserves original flags that
    don't have an alias mapping.
    """
    result: list[str] = []
    seen: set[str] = set()
    for f in flags:
        resolved = _FLAG_ALIASES.get(f, f)
        if resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    return result


# Compiled regex for single-word boundary matching
_WORD_BOUNDARY_PATTERNS: dict[str, re.Pattern[str]] = {
    w: re.compile(r"\b" + re.escape(w) + r"\b") for w in _SINGLE_WORD_PAIN_MARKERS
}


def _has_clear_pain(text: str) -> bool:
    """Return True if the text contains at least 1 pain marker term.

    Single-word markers require word-boundary match (\\\\b). This prevents
    \"bug\" from matching inside \"debugging\", \"debug\", \"debugger\", etc.

    Phrase markers are matched as substrings in normalized text.
    Requires minimum 50 characters of text.
    """
    if not text or len(text.strip()) < 50:
        return False
    lowered = text.lower()

    # Check single-word markers with word boundaries
    for word, pattern in _WORD_BOUNDARY_PATTERNS.items():
        if pattern.search(lowered):
            return True

    # Check phrase markers as substrings
    for phrase in _PHRASE_PAIN_MARKERS:
        if phrase in lowered:
            return True

    return False


def _has_strong_pain(text: str) -> bool:
    """Return True if the text contains strong pain evidence.

    Requires: >= 150 characters AND at least 2 distinct pain marker terms
    (single-word markers found with word boundaries, phrase markers as substrings).
    """
    if not text or len(text.strip()) < 150:
        return False
    lowered = text.lower()
    matches = 0
    seen: set[str] = set()

    # Count single-word matches with word boundaries
    for word, pattern in _WORD_BOUNDARY_PATTERNS.items():
        if pattern.search(lowered):
            seen.add(word)
            matches += 1

    # Count phrase matches
    for phrase in _PHRASE_PAIN_MARKERS:
        if phrase in lowered:
            if phrase not in seen:
                seen.add(phrase)
                matches += 1

    return matches >= 2
