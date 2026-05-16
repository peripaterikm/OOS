from __future__ import annotations

"""Deterministic Opportunity Synthesis — v2.14 Item 6.

Converts high-quality PainClusters and Founder Review queue items into
structured, traceable opportunity hypotheses for founder review.

This is NOT full LLM synthesis.
This is NOT source expansion.
This is NOT a product strategy engine.

This is a deterministic contract/stub that produces structured opportunity
hypotheses from clusters. Every hypothesis is traceable back to one or more
clusters/evidence links.

No live APIs. No LLM calls. Deterministic only.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .noise_classifier import (
    classify_noise_for_evidence,
    compute_evidence_quality_summary,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "opportunity_synthesis_stub.v1"
CREATED_BY = "deterministic_stub"

ALLOWED_CONFIDENCE_LEVELS: frozenset[str] = frozenset({
    "high",
    "medium",
    "low",
    "diagnostic_only",
})

ALLOWED_VALIDATION_ACTIONS: frozenset[str] = frozenset({
    "interview_5_users",
    "competitor_scan",
    "landing_page_smoke",
    "manual_concierge_test",
    "collect_more_evidence",
    "prototype_probe",
    "workflow_mapping",
})

# Allowed review-item decisions for synthesis
_ALLOWED_SYNTHESIS_DECISIONS: frozenset[str] = frozenset({
    "PROMOTE",
    "NEEDS_MORE_EVIDENCE",
})

# Placeholder-title markers that always block synthesis
_PLACEHOLDER_TITLE_MARKERS: frozenset[str] = frozenset({
    "needs_more_evidence",
    "unknown",
    "[dead]",
    "unclear",
    "placeholder",
    "n/a",
    "none",
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _capped_str(value: str, max_len: int = 500) -> str:
    s = " ".join(str(value).split())
    if len(s) <= max_len:
        return s
    return s[:max_len - 3].rstrip() + "..."


def _is_valid_source_url(url: str) -> bool:
    """Return True if url is a valid http(s) URL for synthesis."""
    if not url or not url.strip():
        return False
    u = url.strip()
    if u.lower().startswith("urn:"):
        return False
    if u.lower().startswith("github://"):
        return False
    return u.startswith(("http://", "https://"))


# ---------------------------------------------------------------------------
# OpportunityHypothesis
# ---------------------------------------------------------------------------


@dataclass
class OpportunityHypothesis:
    """A deterministic opportunity hypothesis synthesized from clusters."""

    opportunity_id: str
    source_cluster_ids: list[str] = field(default_factory=list)
    source_review_item_ids: list[str] = field(default_factory=list)
    title: str = ""
    problem_statement: str = ""
    target_icp: str = "unproven; validate actor"
    target_actor: str = "unknown"
    workflow_context: str = ""
    pain_summary: str = ""
    evidence_summary: str = ""
    evidence_links: list[dict[str, Any]] = field(default_factory=list)
    source_diversity: int = 0
    recurrence: int = 0
    quality_summary: dict[str, Any] = field(default_factory=dict)
    promotion_blockers: list[str] = field(default_factory=list)
    confidence_level: str = "low"
    uncertainty_notes: str = ""
    suggested_validation_action: str = "collect_more_evidence"
    validation_questions: list[str] = field(default_factory=list)
    not_a_solution_yet: bool = True
    created_by: str = CREATED_BY
    generated_at: str = field(default_factory=_iso_utc_now)
    schema_version: str = SCHEMA_VERSION

    def validate(self) -> None:
        _require_non_empty(self.opportunity_id, "OpportunityHypothesis.opportunity_id")
        _require_non_empty(self.title, "OpportunityHypothesis.title")
        _require_non_empty(self.problem_statement, "OpportunityHypothesis.problem_statement")
        if not self.source_cluster_ids:
            raise ValueError("OpportunityHypothesis.source_cluster_ids must be non-empty")
        if self.confidence_level not in ALLOWED_CONFIDENCE_LEVELS:
            raise ValueError(
                f"OpportunityHypothesis.confidence_level must be one of "
                f"{sorted(ALLOWED_CONFIDENCE_LEVELS)}, got {self.confidence_level!r}"
            )
        if self.suggested_validation_action not in ALLOWED_VALIDATION_ACTIONS:
            raise ValueError(
                f"OpportunityHypothesis.suggested_validation_action must be one of "
                f"{sorted(ALLOWED_VALIDATION_ACTIONS)}, got {self.suggested_validation_action!r}"
            )
        if not 0 <= len(self.evidence_links):
            raise ValueError("OpportunityHypothesis.evidence_links must be a list")

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "source_cluster_ids": list(self.source_cluster_ids),
            "source_review_item_ids": list(self.source_review_item_ids),
            "title": self.title,
            "problem_statement": self.problem_statement,
            "target_icp": self.target_icp,
            "target_actor": self.target_actor,
            "workflow_context": self.workflow_context,
            "pain_summary": self.pain_summary,
            "evidence_summary": self.evidence_summary,
            "evidence_links": [dict(el) for el in self.evidence_links],
            "source_diversity": self.source_diversity,
            "recurrence": self.recurrence,
            "quality_summary": dict(self.quality_summary),
            "promotion_blockers": list(self.promotion_blockers),
            "confidence_level": self.confidence_level,
            "uncertainty_notes": self.uncertainty_notes,
            "suggested_validation_action": self.suggested_validation_action,
            "validation_questions": list(self.validation_questions),
            "not_a_solution_yet": self.not_a_solution_yet,
            "created_by": self.created_by,
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpportunityHypothesis:
        oh = cls(
            opportunity_id=str(data.get("opportunity_id", "")),
            source_cluster_ids=list(data.get("source_cluster_ids", [])),
            source_review_item_ids=list(data.get("source_review_item_ids", [])),
            title=str(data.get("title", "")),
            problem_statement=str(data.get("problem_statement", "")),
            target_icp=str(data.get("target_icp", "unproven; validate actor")),
            target_actor=str(data.get("target_actor", "unknown")),
            workflow_context=str(data.get("workflow_context", "")),
            pain_summary=str(data.get("pain_summary", "")),
            evidence_summary=str(data.get("evidence_summary", "")),
            evidence_links=[dict(el) for el in data.get("evidence_links", [])],
            source_diversity=int(data.get("source_diversity", 0)),
            recurrence=int(data.get("recurrence", 0)),
            quality_summary=dict(data.get("quality_summary", {})),
            promotion_blockers=list(data.get("promotion_blockers", [])),
            confidence_level=str(data.get("confidence_level", "low")),
            uncertainty_notes=str(data.get("uncertainty_notes", "")),
            suggested_validation_action=str(data.get("suggested_validation_action", "collect_more_evidence")),
            validation_questions=list(data.get("validation_questions", [])),
            not_a_solution_yet=bool(data.get("not_a_solution_yet", True)),
            created_by=str(data.get("created_by", CREATED_BY)),
            generated_at=str(data.get("generated_at", "")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )
        return oh


# ---------------------------------------------------------------------------
# Eligibility Gates
# ---------------------------------------------------------------------------


def _cluster_is_eligible(
    cluster: dict[str, Any],
    review_item: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Determine if a cluster is eligible for opportunity synthesis.

    Returns (is_eligible, reason_if_not).

    Eligibility requires:
    - A matching review item with PROMOTE or NEEDS_MORE_EVIDENCE decision.
    - No catch-all risk.
    - Non-placeholder title.
    - Evidence present with acceptable noise ratio.
    - Not product_launch/self-promo only.
    - Not all low_text_context.
    - Traceability clean (review_item traceability_status and source URLs).
    - Minimum evidence diversity/recurrence/score.
    """
    cluster_id = str(cluster.get("cluster_id", "?"))

    # --- Require a review item with allowed decision ---
    if not review_item:
        return (False, f"Cluster {cluster_id} has no review item; synthesis requires a review item.")
    rec = str(review_item.get("recommended_decision", ""))
    if rec not in _ALLOWED_SYNTHESIS_DECISIONS:
        return (False, f"Cluster {cluster_id} review decision is {rec!r}; synthesis requires PROMOTE or NEEDS_MORE_EVIDENCE.")

    # --- Catch-all risk ---
    catch_all = bool(cluster.get("catch_all_risk", False))
    if catch_all:
        return (False, f"Cluster {cluster_id} is catch-all risk; not eligible for synthesis.")

    # --- Traceability enforcement ---
    ri_trace = str(review_item.get("traceability_status", "") or "").strip()
    if ri_trace and ri_trace != "clean":
        return (False, f"Cluster {cluster_id} review item traceability is {ri_trace!r}; must be clean.")

    # --- Evidence existence ---
    evidence_list = cluster.get("source_evidence_list", [])
    if not evidence_list:
        return (False, f"Cluster {cluster_id} has no evidence; not eligible.")

    # Validate source URLs on all evidence links
    invalid_urls: list[str] = []
    for ev in evidence_list:
        url = str(ev.get("source_url", "") or "")
        if not _is_valid_source_url(url):
            ev_id = str(ev.get("evidence_id", "?"))
            invalid_urls.append(f"{ev_id}: {url!r}")
    if invalid_urls:
        return (False, f"Cluster {cluster_id} has invalid source URLs: {'; '.join(invalid_urls[:3])}")

    # --- Quality checks ---
    quality_summary = compute_evidence_quality_summary(evidence_list)
    noise_ratio = float(quality_summary.get("noise_ratio", 0.0))
    accepted_count = int(quality_summary.get("accepted_evidence_count", 0))
    weak_count = int(quality_summary.get("weak_evidence_count", 0))
    total = int(quality_summary.get("total_evidence_count", 0))

    if noise_ratio >= 0.5:
        return (False, f"Cluster {cluster_id} noise ratio {noise_ratio:.2f} >= 0.5; not eligible.")

    if accepted_count == 0 and weak_count > 0:
        if rec != "NEEDS_MORE_EVIDENCE":
            return (False, f"Cluster {cluster_id} has zero accepted evidence; not eligible without NEEDS_MORE_EVIDENCE recommendation.")

    # Product_launch / self-promo only
    evidence_kinds_set = {str(ev.get("evidence_kind", "")).lower() for ev in evidence_list}
    if evidence_kinds_set and evidence_kinds_set <= {"product_launch", "launch_hype"}:
        return (False, f"Cluster {cluster_id} evidence is product_launch/self-promo only; not eligible.")

    # All low_text_context
    all_low_text = all(
        "low_text_context" in (ev.get("quality_flags", []) or [])
        for ev in evidence_list
    )
    if all_low_text and total > 0:
        return (False, f"Cluster {cluster_id} all evidence is low_text_context; not eligible.")

    # --- Placeholder title check ---
    title = str(cluster.get("title", ""))
    cluster_title = str(cluster.get("cluster_title", ""))
    combined_title = (title or cluster_title).strip()

    if not combined_title:
        return (False, f"Cluster {cluster_id} has empty title; not eligible.")

    combined_lower = combined_title.lower()
    for marker in _PLACEHOLDER_TITLE_MARKERS:
        if marker in combined_lower:
            return (False, f"Cluster {cluster_id} title contains placeholder marker {marker!r}; not eligible.")

    # Generic catch-all title without concrete pain
    generic_catch_all_terms = {"catch-all", "miscellaneous", "various", "general", "other"}
    if any(term in combined_lower for term in generic_catch_all_terms):
        pain_pattern = str(cluster.get("pain_pattern", ""))
        if not pain_pattern or pain_pattern in ("unknown", ""):
            return (False, f"Cluster {cluster_id} title appears generic/catch-all without concrete pain; not eligible.")

    # --- Source diversity / recurrence ---
    source_diversity = int(cluster.get("source_diversity", 1))
    recurrence = int(cluster.get("recurrence", 1))
    overall_score = float((cluster.get("scoring", {}) or {}).get("overall", 0.0))

    min_score_for_single = 0.70 if rec != "NEEDS_MORE_EVIDENCE" else 0.50
    has_minimum_evidence = (
        source_diversity >= 2
        or recurrence >= 2
        or (recurrence >= 1 and overall_score >= min_score_for_single)
    )
    if not has_minimum_evidence:
        return (False, f"Cluster {cluster_id} lacks minimum evidence diversity/recurrence/score (src_div={source_diversity}, rec={recurrence}, score={overall_score:.2f}).")

    # --- Fatal blocker check ---
    blockers = list(cluster.get("promotion_blockers", []) or [])
    blockers_from_ri = review_item.get("promotion_blockers", [])
    if blockers_from_ri:
        blockers = list(blockers_from_ri)

    fatal_blockers = [b for b in blockers if "traceability" in b.lower() or "source scope" in b.lower()]
    if fatal_blockers:
        return (False, f"Cluster {cluster_id} has fatal promotion blockers: {'; '.join(fatal_blockers[:2])}")

    return (True, "")


# ---------------------------------------------------------------------------
# Confidence Level Determination
# ---------------------------------------------------------------------------


def _determine_confidence(
    cluster: dict[str, Any],
    quality_summary: dict[str, Any],
    source_diversity: int,
    recurrence: int,
    blockers: list[str],
    catch_all: bool,
) -> tuple[str, str]:
    """Determine confidence level and uncertainty notes.

    Returns (confidence_level, uncertainty_notes).
    """
    accepted_count = int(quality_summary.get("accepted_evidence_count", 0))
    noise_ratio = float(quality_summary.get("noise_ratio", 0.0))
    weak_ratio = float(quality_summary.get("weak_ratio", 0.0))

    if catch_all:
        return ("diagnostic_only", "Catch-all risk cluster; opportunity is diagnostic only, not actionable.")

    notes: list[str] = []

    if (
        accepted_count >= 2
        and source_diversity >= 2
        and recurrence >= 2
        and noise_ratio < 0.2
        and not blockers
        and weak_ratio < 0.3
    ):
        return ("high", "")

    if source_diversity == 1:
        notes.append("Single source only; cross-source validation missing.")
    if recurrence < 2:
        notes.append(f"Low recurrence ({recurrence}); may be anecdotal.")
    if noise_ratio > 0:
        notes.append(f"Noise evidence present (ratio={noise_ratio:.2f}).")
    if weak_ratio >= 0.5:
        notes.append(f"Majority of evidence is weak (ratio={weak_ratio:.2f}).")
    if blockers:
        notes.append(f"Quality blockers present: {'; '.join(blockers[:3])}.")
    if accepted_count == 0:
        notes.append("No accepted (clean) evidence; all evidence is weak.")

    if accepted_count >= 1 and source_diversity >= 1 and recurrence >= 1 and noise_ratio < 0.5:
        return ("medium", "; ".join(notes) if notes else "")

    return ("low", "; ".join(notes) if notes else "Insufficient evidence quality for higher confidence.")


# ---------------------------------------------------------------------------
# Deterministic Title and Problem Statement
# ---------------------------------------------------------------------------


def _derive_title(cluster: dict[str, Any]) -> str:
    """Derive a founder-readable opportunity title from cluster data."""
    title = str(cluster.get("cluster_title", "") or cluster.get("title", ""))
    if title and len(title) >= 10 and not any(
        m in title.lower() for m in _PLACEHOLDER_TITLE_MARKERS | {"catch-all", "miscellaneous", "various"}
    ):
        cleaned = title.strip().rstrip(".")
        if len(cleaned) <= 80:
            return cleaned
        return cleaned[:77].rstrip() + "..."

    actor = str(cluster.get("actor", ""))
    workflow = str(cluster.get("workflow", ""))
    obj = str(cluster.get("object", ""))
    pain_pattern = str(cluster.get("pain_pattern", ""))

    parts: list[str] = []
    if workflow:
        parts.append(workflow)
    if obj and obj not in ("unknown", ""):
        parts.append(f"for {obj}")
    if actor and actor not in ("unknown", ""):
        parts.append(f"({actor})")

    if parts:
        return " ".join(parts)[:80]

    if pain_pattern and pain_pattern not in ("unknown", ""):
        return _capped_str(pain_pattern, 80)

    return f"Opportunity from cluster {str(cluster.get('cluster_id', '?'))[:12]}"


def _derive_problem_statement(cluster: dict[str, Any]) -> str:
    """Derive a founder-readable problem statement grounded in cluster evidence."""
    actor = str(cluster.get("actor", "users"))
    workflow = str(cluster.get("workflow", "their workflow"))
    pain_pattern = str(cluster.get("pain_pattern", ""))
    obj = str(cluster.get("object", ""))

    if actor in ("unknown", ""):
        actor = "users"

    if pain_pattern and pain_pattern not in ("unknown", "") and len(pain_pattern) >= 20:
        if any(verb in pain_pattern.lower() for verb in ("struggle", "cannot", "hard to", "difficult", "pain", "lack")):
            if actor.lower() not in pain_pattern.lower():
                return _capped_str(f"{actor} report: {pain_pattern}", 300)
            return _capped_str(pain_pattern, 300)

    evidence_list = cluster.get("source_evidence_list", [])
    titles = [str(ev.get("title", "")) for ev in evidence_list[:3] if ev.get("title")]

    if workflow and workflow not in ("unknown", ""):
        if pain_pattern and pain_pattern not in ("unknown", ""):
            return _capped_str(f"{actor} building {workflow} struggle with {pain_pattern.lower()}.", 300)
        if titles:
            return _capped_str(f"{actor} building {workflow} report pain related to: {'; '.join(titles[:2])}.", 300)
        return _capped_str(f"{actor} building {workflow} experience recurring friction evidenced by cluster data.", 300)

    if pain_pattern and pain_pattern not in ("unknown", ""):
        return _capped_str(f"{actor} report: {pain_pattern}.", 300)

    if obj and obj not in ("unknown", ""):
        return _capped_str(f"{actor} working with {obj} encounter workflow friction.", 300)

    return _capped_str(f"{actor} experience recurring pain evidenced by cluster data.", 300)


# ---------------------------------------------------------------------------
# Validation Action Mapping
# ---------------------------------------------------------------------------


def _derive_validation_action(
    cluster: dict[str, Any],
    quality_summary: dict[str, Any],
    source_diversity: int,
    recurrence: int,
    confidence_level: str,
    evidence_kinds: set[str],
) -> tuple[str, list[str]]:
    """Derive suggested validation action and validation questions."""
    accepted_count = int(quality_summary.get("accepted_evidence_count", 0))
    questions: list[str] = []

    # Strong cross-source + clear pain (highest priority)
    if source_diversity >= 2 and recurrence >= 2 and accepted_count >= 2:
        questions.append("Who are 5 people you can interview about this pain this week?")
        questions.append("What workarounds are they currently using?")
        questions.append("What would they pay to eliminate this pain?")
        return ("interview_5_users", questions)

    # Product-launch-heavy evidence
    is_product_launch_heavy = evidence_kinds and evidence_kinds <= {"product_launch", "launch_hype"}
    if is_product_launch_heavy:
        return ("competitor_scan", ["Who are the existing competitors in this space?", "What gaps do users report in existing solutions?"])

    # Unclear buyer / target_actor
    actor = str(cluster.get("actor", "unknown"))
    if actor in ("unknown", ""):
        questions.append("Who exactly experiences this pain? Can you name 5 specific people?")
        questions.append("What is their job title, company size, and daily workflow?")
        return ("interview_5_users", questions)

    # Workflow/tooling pain
    workflow = str(cluster.get("workflow", ""))
    obj = str(cluster.get("object", ""))
    is_workflow_pain = (
        workflow and workflow not in ("unknown", "")
        and obj and obj not in ("unknown", "")
    )
    if is_workflow_pain and "debug" in f"{workflow} {obj}".lower():
        questions.append("What does the current debugging workflow look like step by step?")
        questions.append("What specific tool or step causes the most friction?")
        return ("workflow_mapping", questions)

    if is_workflow_pain:
        questions.append("Can you map the end-to-end workflow that is painful?")
        questions.append("Where exactly in the workflow does friction occur?")
        return ("workflow_mapping", questions)

    # Thin evidence
    if recurrence < 2 and source_diversity < 2:
        questions.append("Is this pain recurring across multiple independent sources?")
        questions.append("Can you find 3+ more evidence items from different sources?")
        return ("collect_more_evidence", questions)

    # Low confidence
    if confidence_level == "low":
        questions.append("Is there stronger evidence from additional sources?")
        questions.append("Can you find direct quotes describing this pain?")
        return ("collect_more_evidence", questions)

    # Default
    questions.append("What additional evidence would increase confidence?")
    return ("collect_more_evidence", questions)


# ---------------------------------------------------------------------------
# Evidence Links Extraction
# ---------------------------------------------------------------------------


def _extract_evidence_links(cluster: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract clean evidence links from a cluster dict."""
    evidence_list = cluster.get("source_evidence_list", [])
    links: list[dict[str, Any]] = []
    for ev in evidence_list:
        link = {
            "evidence_id": str(ev.get("evidence_id", "")),
            "source_id": str(ev.get("source_id", "")),
            "source_type": str(ev.get("source_type", "")),
            "source_url": str(ev.get("source_url", "")),
            "title": str(ev.get("title", "")),
            "evidence_kind": str(ev.get("evidence_kind", "")),
        }
        links.append(link)
    return links


# ---------------------------------------------------------------------------
# Main Synthesis Function
# ---------------------------------------------------------------------------


def _build_opportunity_id(cluster_ids: list[str], generated_at: str) -> str:
    """Build a deterministic opportunity_id."""
    key = "|".join(_ordered_strings(cluster_ids)) + f"|{generated_at}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"opph_{digest}"


def synthesize_opportunities(
    *,
    pain_clusters: list[dict[str, Any]],
    review_items: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> list[OpportunityHypothesis]:
    """Synthesize opportunity hypotheses from eligible clusters.

    Args:
        pain_clusters: List of PainCluster dicts.
        review_items: Required list of FounderReviewQueueItem dicts for
            recommendation context. A cluster without a matching review
            item with PROMOTE or NEEDS_MORE_EVIDENCE decision is ineligible.
        generated_at: ISO 8601 timestamp. Uses UTC now if None.

    Returns:
        List of OpportunityHypothesis objects for eligible clusters.
    """
    ts = generated_at or _iso_utc_now()

    # Build review item lookup by pain_cluster_id
    ri_lookup: dict[str, dict[str, Any]] = {}
    if review_items:
        for ri in review_items:
            pc_id = str(ri.get("pain_cluster_id", ""))
            if pc_id:
                ri_lookup[pc_id] = ri

    hypotheses: list[OpportunityHypothesis] = []

    for cluster in pain_clusters:
        cluster_id = str(cluster.get("cluster_id", ""))
        if not cluster_id:
            continue

        ri = ri_lookup.get(cluster_id)

        # --- Eligibility gate ---
        eligible, reason = _cluster_is_eligible(cluster, ri)
        if not eligible:
            continue

        # --- Extract cluster data ---
        evidence_list = cluster.get("source_evidence_list", [])
        quality_summary = compute_evidence_quality_summary(evidence_list)
        source_diversity = int(cluster.get("source_diversity", 1))
        recurrence = int(cluster.get("recurrence", 1))
        catch_all = bool(cluster.get("catch_all_risk", False))

        # Gather blockers from cluster and review item
        blockers: list[str] = []
        if ri:
            blockers.extend(ri.get("promotion_blockers", []) or [])
        cluster_blockers = cluster.get("promotion_blockers", [])
        if cluster_blockers:
            blockers.extend(cluster_blockers)
        blockers = list(dict.fromkeys(blockers))

        # --- Evidence kinds ---
        evidence_kinds = {str(ev.get("evidence_kind", "")).lower() for ev in evidence_list}

        # --- Confidence ---
        confidence_level, uncertainty_notes = _determine_confidence(
            cluster, quality_summary, source_diversity, recurrence, blockers, catch_all
        )

        # --- Title and problem statement ---
        title = _derive_title(cluster)
        problem_statement = _derive_problem_statement(cluster)

        # --- ICP / Actor ---
        actor = str(cluster.get("actor", "unknown"))
        if actor in ("unknown", ""):
            target_icp = "unproven; validate actor"
            target_actor = "unknown"
            # Append uncertainty note re: unproven actor
            actor_note = "Actor/ICP is not proven by evidence."
            if actor_note not in uncertainty_notes:
                uncertainty_notes = ("; ".join([s for s in [uncertainty_notes, actor_note] if s]) if uncertainty_notes else actor_note)
        else:
            target_icp = actor
            target_actor = actor

        # --- Workflow context ---
        workflow = str(cluster.get("workflow", ""))
        obj = str(cluster.get("object", ""))
        workflow_context = f"{workflow} / {obj}" if workflow and obj else (workflow or obj or "not specified")

        # --- Pain summary ---
        pain_pattern = str(cluster.get("pain_pattern", ""))
        pain_summary = pain_pattern if pain_pattern and pain_pattern not in ("unknown", "") else problem_statement

        # --- Evidence summary ---
        source_types = sorted(set(
            str(ev.get("source_type", "")) for ev in evidence_list if ev.get("source_type")
        ))
        evidence_summary = (
            f"{recurrence} evidence item(s) from {source_diversity} source type(s) "
            f"({', '.join(source_types) if source_types else 'unknown'})"
        )

        # --- Evidence links ---
        evidence_links = _extract_evidence_links(cluster)

        # --- Validation action ---
        validation_action, validation_questions = _derive_validation_action(
            cluster, quality_summary, source_diversity, recurrence, confidence_level, evidence_kinds
        )

        # --- Review item IDs ---
        review_item_ids: list[str] = []
        if ri:
            ri_id = str(ri.get("review_item_id", ""))
            if ri_id:
                review_item_ids.append(ri_id)

        # --- Build hypothesis ---
        opportunity_id = _build_opportunity_id([cluster_id], ts)

        hypothesis = OpportunityHypothesis(
            opportunity_id=opportunity_id,
            source_cluster_ids=[cluster_id],
            source_review_item_ids=review_item_ids,
            title=title,
            problem_statement=problem_statement,
            target_icp=target_icp,
            target_actor=target_actor,
            workflow_context=workflow_context,
            pain_summary=pain_summary,
            evidence_summary=evidence_summary,
            evidence_links=evidence_links,
            source_diversity=source_diversity,
            recurrence=recurrence,
            quality_summary=quality_summary,
            promotion_blockers=blockers,
            confidence_level=confidence_level,
            uncertainty_notes=uncertainty_notes,
            suggested_validation_action=validation_action,
            validation_questions=validation_questions,
            not_a_solution_yet=True,
            created_by=CREATED_BY,
            generated_at=ts,
        )
        hypotheses.append(hypothesis)

    return hypotheses


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def render_opportunity_hypotheses_markdown(
    hypotheses: list[OpportunityHypothesis],
) -> str:
    """Render opportunity hypotheses as a Markdown section.

    Always includes `## Opportunity Hypotheses` header.
    Returns a string suitable for inclusion in a founder review package.
    """
    lines: list[str] = []
    lines.append("## Opportunity Hypotheses")
    lines.append("")

    if not hypotheses:
        lines.append("No opportunity hypotheses generated under deterministic eligibility gates.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"*{len(hypotheses)} hypothesis/hypotheses synthesized from qualifying clusters.*")
    lines.append("")
    lines.append("**All hypotheses are validation candidates only — NOT final business ideas.**")
    lines.append("")

    for i, h in enumerate(hypotheses, 1):
        lines.append(f"### {i}. {h.title}")
        lines.append("")
        lines.append(f"- **Opportunity ID**: `{h.opportunity_id}`")
        lines.append(f"- **Source Clusters**: {', '.join(f'`{cid}`' for cid in h.source_cluster_ids)}")
        if h.source_review_item_ids:
            lines.append(f"- **Review Items**: {', '.join(f'`{rid}`' for rid in h.source_review_item_ids)}")
        lines.append("")

        lines.append("#### Problem Statement")
        lines.append("")
        lines.append(f"> {h.problem_statement}")
        lines.append("")

        lines.append("#### Target ICP / Actor")
        lines.append("")
        lines.append(f"- **ICP**: {h.target_icp}")
        lines.append(f"- **Actor**: {h.target_actor}")
        lines.append(f"- **Workflow Context**: {h.workflow_context}")
        lines.append("")

        lines.append("#### Evidence Basis")
        lines.append("")
        lines.append(f"- **Source Diversity**: {h.source_diversity}")
        lines.append(f"- **Recurrence**: {h.recurrence}")
        lines.append(f"- **Evidence Summary**: {h.evidence_summary}")
        if h.evidence_links:
            lines.append("")
            for el in h.evidence_links[:5]:
                url = el.get("source_url", "")
                title = el.get("title", "")
                sid = el.get("source_id", "")
                if url:
                    lines.append(f"- [{title or url}]({url}) (`{sid}`)")
                else:
                    lines.append(f"- {title or 'untitled'} (`{sid}`)")
        lines.append("")

        lines.append("#### Quality & Confidence")
        lines.append("")
        lines.append(f"- **Confidence Level**: `{h.confidence_level}`")
        if h.uncertainty_notes:
            lines.append(f"- **Uncertainty**: {h.uncertainty_notes}")
        if h.promotion_blockers:
            lines.append(f"- **Blockers**: {'; '.join(h.promotion_blockers[:3])}")
        eqc = h.quality_summary
        accepted = int(eqc.get("accepted_evidence_count", 0))
        weak = int(eqc.get("weak_evidence_count", 0))
        noise = int(eqc.get("noise_evidence_count", 0))
        lines.append(f"- **Evidence Quality**: accepted={accepted} / weak={weak} / noise={noise}")
        lines.append("")

        lines.append("#### Suggested Validation")
        lines.append("")
        lines.append(f"- **Action**: `{h.suggested_validation_action}`")
        if h.validation_questions:
            for q in h.validation_questions:
                lines.append(f"  - {q}")
        lines.append("")

        lines.append("#### Caveats")
        lines.append("")
        lines.append(f"- **Not a solution yet**: {'YES' if h.not_a_solution_yet else 'NO'}")
        lines.append(f"- **Created by**: `{h.created_by}`")
        lines.append(f"- **Generated**: {h.generated_at}")
        lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
