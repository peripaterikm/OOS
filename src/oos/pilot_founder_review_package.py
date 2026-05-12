from __future__ import annotations

"""Pilot Founder Review Package — deterministic founder review bundle.

Implements the Founder Review Package specified in
docs/contracts/operational_discovery_pilot_run_contract.md Sections 14–15.

Produces a structured review package from PainClusters and opportunity
candidates with evidence links, score explanations, source quality context,
and recommended founder decisions (PROMOTE / PARK / KILL /
NEEDS_MORE_EVIDENCE / REVISIT_LATER).

All recommendations are advisory-only. This module does NOT ingest founder
decisions, does NOT create KillReason records, and does NOT mutate portfolio,
opportunity, or cluster state. It provides stable feedback hooks for later
ingestion by downstream modules.

No live APIs. No LLM calls. No filesystem writes. Deterministic only.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .pain_cluster import PainCluster
from .source_quality_report import SourceQualityReport

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.1.0"
ARTIFACT_TYPE = "founder_review_package"

ALLOWED_RECOMMENDED_DECISIONS: frozenset[str] = frozenset({
    "PROMOTE",
    "PARK",
    "KILL",
    "NEEDS_MORE_EVIDENCE",
    "REVISIT_LATER",
})

ALLOWED_ITEM_TYPES: frozenset[str] = frozenset({
    "pain_cluster",
    "opportunity_candidate",
    "linked_pair",
})

ALLOWED_SUGGESTED_ACTIONS: frozenset[str] = frozenset({
    "interview",
    "landing_page",
    "manual_research",
    "collect_more_evidence",
    "check_competitors",
    "inspect_github_repos",
    "search_more_sources",
    "kill_no_action",
})

DECISION_PRIORITY: dict[str, int] = {
    "PROMOTE": 0,
    "NEEDS_MORE_EVIDENCE": 1,
    "REVISIT_LATER": 2,
    "PARK": 3,
    "KILL": 4,
}


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_list(value: Any, field_name: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")


def _normalize_cluster(pc: Any) -> dict[str, Any]:
    if isinstance(pc, PainCluster):
        return pc.to_dict()
    if isinstance(pc, dict):
        return dict(pc)
    raise TypeError(f"Expected PainCluster or dict, got {type(pc).__name__}")


def _normalize_opportunity(oc: Any) -> dict[str, Any]:
    if isinstance(oc, dict):
        return dict(oc)
    if hasattr(oc, "to_dict"):
        return oc.to_dict()
    if hasattr(oc, "__dict__"):
        return {k: v for k, v in vars(oc).items() if not k.startswith("_")}
    return {"_raw": str(oc)}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FounderReviewEvidenceLink:
    """A traceable evidence link in a review item."""

    evidence_id: str
    source_id: str
    source_type: str
    source_url: str
    title: str
    excerpt: str
    evidence_kind: str
    quality_flags: list[str] = field(default_factory=list)

    def validate(self) -> None:
        _require_non_empty(self.evidence_id, "FounderReviewEvidenceLink.evidence_id")
        _require_non_empty(self.source_id, "FounderReviewEvidenceLink.source_id")
        _require_non_empty(self.source_type, "FounderReviewEvidenceLink.source_type")
        _require_non_empty(self.source_url, "FounderReviewEvidenceLink.source_url")
        _require_non_empty(self.title, "FounderReviewEvidenceLink.title")
        _require_non_empty(self.excerpt, "FounderReviewEvidenceLink.excerpt")
        _require_non_empty(self.evidence_kind, "FounderReviewEvidenceLink.evidence_kind")
        _require_list(self.quality_flags, "FounderReviewEvidenceLink.quality_flags")

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "title": self.title,
            "excerpt": self.excerpt,
            "evidence_kind": self.evidence_kind,
            "quality_flags": list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderReviewEvidenceLink:
        link = cls(
            evidence_id=str(data.get("evidence_id", "")),
            source_id=str(data.get("source_id", "")),
            source_type=str(data.get("source_type", "")),
            source_url=str(data.get("source_url", "")),
            title=str(data.get("title", "")),
            excerpt=str(data.get("excerpt", "")),
            evidence_kind=str(data.get("evidence_kind", "")),
            quality_flags=list(data.get("quality_flags", [])),
        )
        link.validate()
        return link


@dataclass(frozen=True)
class FounderReviewQueueItem:
    """A single review item in the founder review package."""

    review_item_id: str
    item_type: str
    title: str
    actor: str
    workflow: str
    object: str
    pain_pattern: str
    score: float
    score_components: dict[str, float]
    evidence_summary: str
    evidence_links: list[FounderReviewEvidenceLink]
    source_ids: list[str]
    source_diversity: int
    recurrence: int
    noise_risk: float
    business_relevance: float
    uncertainty: str
    recommended_decision: str
    recommendation_reason: str
    suggested_validation_action: str
    source_quality_notes: str
    traceability_status: str
    created_at: str
    notes: str = ""
    pain_cluster_id: str = ""
    opportunity_id: str = ""
    founder_final_decision: str = ""

    def validate(self) -> None:
        _require_non_empty(self.review_item_id, "FounderReviewQueueItem.review_item_id")
        _require_non_empty(self.item_type, "FounderReviewQueueItem.item_type")
        _require_non_empty(self.title, "FounderReviewQueueItem.title")
        _require_non_empty(self.recommended_decision, "FounderReviewQueueItem.recommended_decision")
        _require_non_empty(self.recommendation_reason, "FounderReviewQueueItem.recommendation_reason")
        _require_non_empty(self.suggested_validation_action, "FounderReviewQueueItem.suggested_validation_action")
        _require_non_empty(self.created_at, "FounderReviewQueueItem.created_at")

        if self.item_type not in ALLOWED_ITEM_TYPES:
            raise ValueError(
                f"FounderReviewQueueItem.item_type must be one of "
                f"{sorted(ALLOWED_ITEM_TYPES)}, got {self.item_type!r}"
            )

        if self.recommended_decision not in ALLOWED_RECOMMENDED_DECISIONS:
            raise ValueError(
                f"FounderReviewQueueItem.recommended_decision must be one of "
                f"{sorted(ALLOWED_RECOMMENDED_DECISIONS)}, got {self.recommended_decision!r}"
            )

        if self.suggested_validation_action not in ALLOWED_SUGGESTED_ACTIONS:
            raise ValueError(
                f"FounderReviewQueueItem.suggested_validation_action must be one of "
                f"{sorted(ALLOWED_SUGGESTED_ACTIONS)}, got {self.suggested_validation_action!r}"
            )

        if not (0.0 <= self.score <= 1.0):
            raise ValueError(
                f"FounderReviewQueueItem.score must be 0.0-1.0, got {self.score}"
            )

        if not (0.0 <= self.noise_risk <= 1.0):
            raise ValueError(
                f"FounderReviewQueueItem.noise_risk must be 0.0-1.0, got {self.noise_risk}"
            )

        if not (0.0 <= self.business_relevance <= 1.0):
            raise ValueError(
                f"FounderReviewQueueItem.business_relevance must be 0.0-1.0, got {self.business_relevance}"
            )

        if self.uncertainty not in ("low", "moderate", "high", "unknown"):
            raise ValueError(
                f"FounderReviewQueueItem.uncertainty must be low/moderate/high/unknown"
            )

        _require_list(self.evidence_links, "FounderReviewQueueItem.evidence_links")
        _require_list(self.source_ids, "FounderReviewQueueItem.source_ids")

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_item_id": self.review_item_id,
            "item_type": self.item_type,
            "title": self.title,
            "actor": self.actor,
            "workflow": self.workflow,
            "object": self.object,
            "pain_pattern": self.pain_pattern,
            "score": self.score,
            "score_components": dict(self.score_components),
            "evidence_summary": self.evidence_summary,
            "evidence_links": [el.to_dict() for el in self.evidence_links],
            "source_ids": list(self.source_ids),
            "source_diversity": self.source_diversity,
            "recurrence": self.recurrence,
            "noise_risk": self.noise_risk,
            "business_relevance": self.business_relevance,
            "uncertainty": self.uncertainty,
            "recommended_decision": self.recommended_decision,
            "recommendation_reason": self.recommendation_reason,
            "suggested_validation_action": self.suggested_validation_action,
            "source_quality_notes": self.source_quality_notes,
            "traceability_status": self.traceability_status,
            "created_at": self.created_at,
            "notes": self.notes,
            "pain_cluster_id": self.pain_cluster_id,
            "opportunity_id": self.opportunity_id,
            "founder_final_decision": self.founder_final_decision,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderReviewQueueItem:
        item = cls(
            review_item_id=str(data.get("review_item_id", "")),
            item_type=str(data.get("item_type", "")),
            title=str(data.get("title", "")),
            actor=str(data.get("actor", "")),
            workflow=str(data.get("workflow", "")),
            object=str(data.get("object", "")),
            pain_pattern=str(data.get("pain_pattern", "")),
            score=float(data.get("score", 0.0)),
            score_components=dict(data.get("score_components", {})),
            evidence_summary=str(data.get("evidence_summary", "")),
            evidence_links=[
                FounderReviewEvidenceLink.from_dict(el)
                for el in data.get("evidence_links", [])
            ],
            source_ids=list(data.get("source_ids", [])),
            source_diversity=int(data.get("source_diversity", 1)),
            recurrence=int(data.get("recurrence", 1)),
            noise_risk=float(data.get("noise_risk", 0.0)),
            business_relevance=float(data.get("business_relevance", 0.5)),
            uncertainty=str(data.get("uncertainty", "unknown")),
            recommended_decision=str(data.get("recommended_decision", "")),
            recommendation_reason=str(data.get("recommendation_reason", "")),
            suggested_validation_action=str(data.get("suggested_validation_action", "")),
            source_quality_notes=str(data.get("source_quality_notes", "")),
            traceability_status=str(data.get("traceability_status", "unchecked")),
            created_at=str(data.get("created_at", "")),
            notes=str(data.get("notes", "")),
            pain_cluster_id=str(data.get("pain_cluster_id", "")),
            opportunity_id=str(data.get("opportunity_id", "")),
            founder_final_decision=str(data.get("founder_final_decision", "")),
        )
        item.validate()
        return item


@dataclass
class FounderReviewPackage:
    """The complete founder review package for a discovery pilot run."""

    package_id: str
    discovery_run_id: str
    created_at: str
    total_review_items: int = 0
    promote_count: int = 0
    park_count: int = 0
    kill_count: int = 0
    needs_more_evidence_count: int = 0
    revisit_later_count: int = 0
    source_ids: list[str] = field(default_factory=list)
    top_clusters: list[dict[str, Any]] = field(default_factory=list)
    review_items: list[FounderReviewQueueItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # Package-level traceability summary (v1.1.0)
    traceability_status: str = "clean"
    total_evidence_links: int = 0
    invalid_evidence_link_count: int = 0
    missing_source_url_count: int = 0
    placeholder_url_count: int = 0
    non_http_url_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": ARTIFACT_TYPE,
            "schema_version": SCHEMA_VERSION,
            "package_id": self.package_id,
            "discovery_run_id": self.discovery_run_id,
            "created_at": self.created_at,
            "total_review_items": self.total_review_items,
            "promote_count": self.promote_count,
            "park_count": self.park_count,
            "kill_count": self.kill_count,
            "needs_more_evidence_count": self.needs_more_evidence_count,
            "revisit_later_count": self.revisit_later_count,
            "source_ids": list(self.source_ids),
            "top_clusters": list(self.top_clusters),
            "review_items": [ri.to_dict() for ri in self.review_items],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "traceability_status": self.traceability_status,
            "total_evidence_links": self.total_evidence_links,
            "invalid_evidence_link_count": self.invalid_evidence_link_count,
            "missing_source_url_count": self.missing_source_url_count,
            "placeholder_url_count": self.placeholder_url_count,
            "non_http_url_count": self.non_http_url_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderReviewPackage:
        return cls(
            package_id=str(data.get("package_id", "")),
            discovery_run_id=str(data.get("discovery_run_id", "")),
            created_at=str(data.get("created_at", "")),
            total_review_items=int(data.get("total_review_items", 0)),
            promote_count=int(data.get("promote_count", 0)),
            park_count=int(data.get("park_count", 0)),
            kill_count=int(data.get("kill_count", 0)),
            needs_more_evidence_count=int(data.get("needs_more_evidence_count", 0)),
            revisit_later_count=int(data.get("revisit_later_count", 0)),
            source_ids=list(data.get("source_ids", [])),
            top_clusters=list(data.get("top_clusters", [])),
            review_items=[
                FounderReviewQueueItem.from_dict(ri)
                for ri in data.get("review_items", [])
            ],
            warnings=list(data.get("warnings", [])),
            errors=list(data.get("errors", [])),
            traceability_status=str(data.get("traceability_status", "clean")),
            total_evidence_links=int(data.get("total_evidence_links", 0)),
            invalid_evidence_link_count=int(data.get("invalid_evidence_link_count", 0)),
            missing_source_url_count=int(data.get("missing_source_url_count", 0)),
            placeholder_url_count=int(data.get("placeholder_url_count", 0)),
            non_http_url_count=int(data.get("non_http_url_count", 0)),
        )


@dataclass
class FounderReviewPackageValidationResult:
    """Validation result for a FounderReviewPackage."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


# ---------------------------------------------------------------------------
# Traceability helpers
# ---------------------------------------------------------------------------


def _is_http_url(url: str) -> bool:
    """Return True if url starts with http:// or https://."""
    return url.startswith(("http://", "https://"))


def _is_placeholder_url(url: str) -> bool:
    """Return True if url is a placeholder (urn:*, or starts with urn:)."""
    if not url:
        return False
    return url.lower().startswith("urn:")


def _assess_link_traceability(
    el: FounderReviewEvidenceLink,
) -> tuple[bool, str, list[str]]:
    """Assess a single evidence link for traceability.

    Returns (clean, status, issues_list).
    """
    issues: list[str] = []
    url = el.source_url

    if not url:
        issues.append("missing_source_url")
    elif _is_placeholder_url(url):
        issues.append("placeholder_url")
    elif not _is_http_url(url):
        issues.append("non_http_url")

    if not issues:
        return (True, "clean", [])
    return (False, "failed", issues)


def _compute_package_traceability(
    review_items: list[FounderReviewQueueItem],
) -> dict[str, Any]:
    """Compute package-level traceability summary from all review items."""
    total_links = 0
    invalid_count = 0
    missing_url = 0
    placeholder_url = 0
    non_http_url = 0

    all_clean = True
    for ri in review_items:
        for el in ri.evidence_links:
            total_links += 1
            url = el.source_url
            if not url:
                missing_url += 1
                invalid_count += 1
                all_clean = False
            elif _is_placeholder_url(url):
                placeholder_url += 1
                invalid_count += 1
                all_clean = False
            elif not _is_http_url(url):
                non_http_url += 1
                invalid_count += 1
                all_clean = False

    return {
        "traceability_status": "clean" if all_clean else "failed",
        "total_evidence_links": total_links,
        "invalid_evidence_link_count": invalid_count,
        "missing_source_url_count": missing_url,
        "placeholder_url_count": placeholder_url,
        "non_http_url_count": non_http_url,
    }


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------


def recommend_decision(
    *,
    score: float,
    noise_risk: float,
    source_diversity: int,
    recurrence: int,
    business_relevance: float,
    uncertainty: str,
    source_url_traceability_clean: bool,
    has_credible_evidence: bool,
) -> tuple[str, str]:
    """Compute a recommended founder decision and reason.

    Returns (recommended_decision, recommendation_reason).
    """
    # ---- KILL ----
    if noise_risk >= 0.80:
        return ("KILL", "Noise risk >= 0.80: cluster is dominated by noise indicators.")
    if not source_url_traceability_clean:
        return ("KILL", "Source URL traceability failed: missing or placeholder URLs.")
    if score < 0.30:
        return ("KILL", f"Score too low ({score:.2f}): below minimum threshold.")
    if business_relevance < 0.20 and not has_credible_evidence:
        return ("KILL", "Low business relevance and no credible evidence.")

    # ---- PROMOTE ----
    # PROMOTE requires source_diversity >= 2 OR recurrence >= 2
    # to prevent single-source / single-signal promotion.
    if (
        score >= 0.70
        and noise_risk < 0.50
        and source_url_traceability_clean
        and has_credible_evidence
        and business_relevance >= 0.40
        and (source_diversity >= 2 or recurrence >= 2)
    ):
        return ("PROMOTE", f"Strong score ({score:.2f}), clean traceability, and credible evidence.")

    # High score but single-source and low recurrence: needs more evidence.
    if (
        score >= 0.70
        and noise_risk < 0.50
        and source_url_traceability_clean
        and has_credible_evidence
        and business_relevance >= 0.40
        and source_diversity == 1
        and recurrence < 2
    ):
        return ("NEEDS_MORE_EVIDENCE",
                f"High score ({score:.2f}) but single-source and low recurrence; "
                f"collect evidence from more sources.")

    # ---- NEEDS_MORE_EVIDENCE ----
    if 0.50 <= score < 0.70:
        return ("NEEDS_MORE_EVIDENCE", f"Score in needs-evidence range ({score:.2f}); collect more data.")
    if source_diversity == 1 and score >= 0.40:
        return ("NEEDS_MORE_EVIDENCE", "Single-source evidence; cross-source validation needed.")
    if recurrence < 2 and score >= 0.40 and business_relevance >= 0.40:
        return ("NEEDS_MORE_EVIDENCE", "Low recurrence but promising pain; collect more evidence.")
    if uncertainty == "high" and score >= 0.30:
        return ("NEEDS_MORE_EVIDENCE", "High uncertainty; collect additional evidence to reduce uncertainty.")

    # ---- REVISIT_LATER ----
    if 0.40 <= score < 0.55 and business_relevance >= 0.30 and recurrence < 2:
        return ("REVISIT_LATER", "Moderate score with low recurrence; may become relevant with more evidence.")
    if score < 0.55 and uncertainty in ("high",):
        return ("REVISIT_LATER", "High uncertainty; revisit later when more data is available.")

    # ---- PARK ----
    if 0.30 <= score < 0.50:
        return ("PARK", f"Moderate score ({score:.2f}) but below promotion threshold; park for later.")
    if business_relevance < 0.30:
        return ("PARK", "Low business relevance; park until ICP fit improves.")

    return ("PARK", "Does not meet clear criteria for other decisions; park for now.")


def suggest_validation_action(
    *,
    recommended_decision: str,
    score: float,
    business_relevance: float,
    source_diversity: int,
    noise_risk: float,
    evidence_links: list[FounderReviewEvidenceLink],
) -> str:
    """Generate a deterministic suggested validation action."""
    if recommended_decision == "KILL":
        return "kill_no_action"

    if recommended_decision == "NEEDS_MORE_EVIDENCE":
        if source_diversity < 2:
            return "collect_more_evidence"
        return "search_more_sources"

    if recommended_decision == "PARK":
        return "manual_research"

    if recommended_decision == "REVISIT_LATER":
        return "collect_more_evidence"

    # PROMOTE path
    github_count = sum(1 for el in evidence_links if el.source_type == "issue_tracker")
    total = len(evidence_links) if evidence_links else 1

    if total > 0 and github_count / total >= 0.5 and business_relevance >= 0.50:
        return "inspect_github_repos"

    solution_count = sum(
        1 for el in evidence_links
        if "solution" in el.evidence_kind.lower() or "feature_request" in el.evidence_kind.lower()
    )
    if total > 0 and solution_count / total >= 0.4:
        return "check_competitors"

    if score >= 0.70 and business_relevance >= 0.50:
        return "interview"

    if score >= 0.70 and business_relevance >= 0.40:
        return "landing_page"

    return "manual_research"


def assess_uncertainty(
    *,
    score: float,
    source_diversity: int,
    recurrence: int,
    noise_risk: float,
) -> str:
    """Assess evidence uncertainty: low, moderate, high."""
    if source_diversity >= 2 and recurrence >= 3 and noise_risk < 0.30:
        return "low"
    if source_diversity == 1 or recurrence < 2 or noise_risk >= 0.60:
        return "high"
    return "moderate"


# ---------------------------------------------------------------------------
# Evidence link builder
# ---------------------------------------------------------------------------


def _build_evidence_links(
    evidence_list: list[dict[str, Any]],
) -> list[FounderReviewEvidenceLink]:
    """Build evidence links, keeping all entries including those with missing fields."""
    links: list[FounderReviewEvidenceLink] = []
    for ev in evidence_list:
        link = FounderReviewEvidenceLink(
            evidence_id=str(ev.get("evidence_id", "")),
            source_id=str(ev.get("source_id", "")),
            source_type=str(ev.get("source_type", "")),
            source_url=str(ev.get("source_url", "")),
            title=str(ev.get("title", "")),
            excerpt=str(ev.get("excerpt", ""))[:500],
            evidence_kind=str(ev.get("evidence_kind", "")),
            quality_flags=list(ev.get("quality_flags", [])),
        )
        links.append(link)
    return links


# ---------------------------------------------------------------------------
# Review item builder
# ---------------------------------------------------------------------------


def _build_review_item_for_cluster(
    cluster: dict[str, Any],
    created_at: str,
    source_quality_report: dict[str, Any] | None,
    idx: int,
) -> FounderReviewQueueItem:
    cluster_id = str(cluster.get("cluster_id", ""))
    scoring = cluster.get("scoring", {})
    if isinstance(scoring, dict):
        overall = float(scoring.get("overall", 0.0))
        score_components = {
            "pain_explicitness": float(scoring.get("pain_explicitness", 0.0)),
            "recurrence": float(scoring.get("recurrence", 0.0)),
            "business_cost": float(scoring.get("business_cost", 0.0)),
            "icp_fit": float(scoring.get("icp_fit", 0.0)),
            "source_reliability": float(scoring.get("source_reliability", 0.0)),
            "freshness": float(scoring.get("freshness", 0.0)),
            "actionability": float(scoring.get("actionability", 0.0)),
            "noise_risk": float(scoring.get("noise_risk", 0.0)),
        }
    else:
        overall = 0.0
        score_components = {}

    source_diversity = int(cluster.get("source_diversity", 1))
    recurrence = int(cluster.get("recurrence", 1))
    noise_risk = float(cluster.get("noise_risk", 0.0))
    business_relevance = float(cluster.get("business_relevance", 0.5))
    actor = str(cluster.get("actor", ""))
    workflow = str(cluster.get("workflow", ""))
    obj = str(cluster.get("object", ""))
    pain_pattern = str(cluster.get("pain_pattern", ""))

    evidence_list = cluster.get("source_evidence_list", [])
    evidence_links = _build_evidence_links(evidence_list)

    source_url_traceability_clean = True
    traceability_status = "clean"
    for el in evidence_links:
        url = el.source_url
        if not url:
            source_url_traceability_clean = False
            traceability_status = "failed"
            break
        if url.lower().startswith("urn:"):
            source_url_traceability_clean = False
            traceability_status = "failed"
            break
        if not url.startswith(("http://", "https://")):
            source_url_traceability_clean = False
            traceability_status = "failed"
            break

    has_credible_evidence = any(
        el.evidence_kind not in ("", "unknown")
        for el in evidence_links
    )

    uncertainty = assess_uncertainty(
        score=overall,
        source_diversity=source_diversity,
        recurrence=recurrence,
        noise_risk=noise_risk,
    )

    recommended_decision, recommendation_reason = recommend_decision(
        score=overall,
        noise_risk=noise_risk,
        source_diversity=source_diversity,
        recurrence=recurrence,
        business_relevance=business_relevance,
        uncertainty=uncertainty,
        source_url_traceability_clean=source_url_traceability_clean,
        has_credible_evidence=has_credible_evidence,
    )

    suggested_action = suggest_validation_action(
        recommended_decision=recommended_decision,
        score=overall,
        business_relevance=business_relevance,
        source_diversity=source_diversity,
        noise_risk=noise_risk,
        evidence_links=evidence_links,
    )

    source_types = sorted(set(el.source_type for el in evidence_links))
    evidence_summary = (
        f"{recurrence} evidence item(s) from {source_diversity} source type(s) "
        f"({', '.join(source_types)})"
    )

    source_quality_notes = ""
    if source_quality_report:
        for metric in source_quality_report.get("source_metrics", []):
            sid = str(metric.get("source_id", ""))
            if sid in {el.source_id for el in evidence_links}:
                noise_rate = float(metric.get("noise_rate", 0.0))
                if noise_rate > 0.50:
                    source_quality_notes += (
                        f"Source '{sid}' has high noise rate ({noise_rate:.2f}). "
                    )

    source_ids = sorted(set(el.source_id for el in evidence_links))

    id_key = f"{cluster_id}|{created_at}|cluster"
    id_hash = hashlib.sha256(id_key.encode("utf-8")).hexdigest()[:12]
    review_item_id = f"ri_{id_hash}"

    title = pain_pattern if pain_pattern else f"Cluster {cluster_id}"

    return FounderReviewQueueItem(
        review_item_id=review_item_id,
        item_type="pain_cluster",
        title=title,
        actor=actor,
        workflow=workflow,
        object=obj,
        pain_pattern=pain_pattern,
        score=overall,
        score_components=score_components,
        evidence_summary=evidence_summary,
        evidence_links=evidence_links,
        source_ids=source_ids,
        source_diversity=source_diversity,
        recurrence=recurrence,
        noise_risk=noise_risk,
        business_relevance=business_relevance,
        uncertainty=uncertainty,
        recommended_decision=recommended_decision,
        recommendation_reason=recommendation_reason,
        suggested_validation_action=suggested_action,
        source_quality_notes=source_quality_notes.strip(),
        traceability_status=traceability_status,
        created_at=created_at,
        pain_cluster_id=cluster_id,
        opportunity_id="",
    )


def _build_review_item_for_opportunity(
    oc: dict[str, Any],
    created_at: str,
    source_quality_report: dict[str, Any] | None,
    idx: int,
) -> FounderReviewQueueItem | None:
    opportunity_id = str(oc.get("opportunity_id", ""))
    if not opportunity_id:
        return None

    cluster_id = str(oc.get("source_pain_cluster_id", ""))
    score = float(oc.get("score", 0.0))
    problem_statement = str(oc.get("problem_statement", ""))
    evidence_summary = str(oc.get("evidence_summary", ""))
    uncertainty = str(oc.get("uncertainty", "unknown"))
    suggested_action = str(oc.get("suggested_validation_action", ""))
    actor = str(oc.get("actor", "") or oc.get("icp", ""))
    title = problem_statement if problem_statement else f"Opportunity {opportunity_id}"

    raw_links = oc.get("source_evidence_links", [])
    evidence_links = _build_evidence_links(raw_links)

    source_diversity = len(set(el.source_type for el in evidence_links)) or 1
    recurrence = len(evidence_links) or 1
    noise_risk = float(oc.get("noise_risk", 0.0))
    business_relevance = float(oc.get("business_relevance", 0.5))

    source_url_traceability_clean = True
    traceability_status = "clean"
    for el in evidence_links:
        url = el.source_url
        if not url or url.lower().startswith("urn:") or not url.startswith(("http://", "https://")):
            source_url_traceability_clean = False
            traceability_status = "failed"
            break

    has_credible_evidence = len(evidence_links) > 0

    if suggested_action not in ALLOWED_SUGGESTED_ACTIONS:
        suggested_action = "manual_research"

    recommended_decision, recommendation_reason = recommend_decision(
        score=score,
        noise_risk=noise_risk,
        source_diversity=source_diversity,
        recurrence=recurrence,
        business_relevance=business_relevance,
        uncertainty=uncertainty,
        source_url_traceability_clean=source_url_traceability_clean,
        has_credible_evidence=has_credible_evidence,
    )

    suggested_v_action = suggest_validation_action(
        recommended_decision=recommended_decision,
        score=score,
        business_relevance=business_relevance,
        source_diversity=source_diversity,
        noise_risk=noise_risk,
        evidence_links=evidence_links,
    )

    source_ids = sorted(set(el.source_id for el in evidence_links))

    id_key = f"{opportunity_id}|{created_at}|opportunity"
    id_hash = hashlib.sha256(id_key.encode("utf-8")).hexdigest()[:12]
    review_item_id = f"ri_{id_hash}"

    return FounderReviewQueueItem(
        review_item_id=review_item_id,
        item_type="opportunity_candidate",
        title=title,
        actor=actor,
        workflow="",
        object="",
        pain_pattern="",
        score=score,
        score_components={},
        evidence_summary=evidence_summary,
        evidence_links=evidence_links,
        source_ids=source_ids,
        source_diversity=source_diversity,
        recurrence=recurrence,
        noise_risk=noise_risk,
        business_relevance=business_relevance,
        uncertainty=uncertainty,
        recommended_decision=recommended_decision,
        recommendation_reason=recommendation_reason,
        suggested_validation_action=suggested_v_action,
        source_quality_notes="",
        traceability_status=traceability_status,
        created_at=created_at,
        pain_cluster_id=cluster_id,
        opportunity_id=opportunity_id,
    )


# ---------------------------------------------------------------------------
# Package builder
# ---------------------------------------------------------------------------


def build_founder_review_package(
    *,
    pain_clusters: list[PainCluster] | list[dict[str, Any]] | None = None,
    opportunity_candidates: list[dict[str, Any]] | None = None,
    source_quality_report: SourceQualityReport | dict[str, Any] | None = None,
    created_at: str | None = None,
    max_items: int = 10,
    discovery_run_id: str = "pilot_run_unknown",
) -> FounderReviewPackage:
    """Build a deterministic Founder Review Package."""
    if created_at is None:
        created_at = _iso_utc_now()

    clusters: list[dict[str, Any]] = [_normalize_cluster(pc) for pc in (pain_clusters or [])]
    opps: list[dict[str, Any]] = [_normalize_opportunity(oc) for oc in (opportunity_candidates or [])]

    sqr_dict: dict[str, Any] | None = None
    if source_quality_report is not None:
        if isinstance(source_quality_report, SourceQualityReport):
            sqr_dict = source_quality_report.to_dict()
        elif isinstance(source_quality_report, dict):
            sqr_dict = dict(source_quality_report)

    review_items: list[FounderReviewQueueItem] = []
    build_errors: list[str] = []

    for i, cluster in enumerate(clusters):
        try:
            item = _build_review_item_for_cluster(
                cluster=cluster,
                created_at=created_at,
                source_quality_report=sqr_dict,
                idx=i,
            )
            review_items.append(item)
        except Exception as e:
            cluster_id = str(cluster.get("cluster_id", "?"))
            build_errors.append(
                f"cluster[{i}] (id={cluster_id}) build error: {type(e).__name__}: {e}"
            )

    for i, oc in enumerate(opps):
        try:
            item = _build_review_item_for_opportunity(
                oc=oc,
                created_at=created_at,
                source_quality_report=sqr_dict,
                idx=i,
            )
            if item is not None:
                review_items.append(item)
        except Exception as e:
            opportunity_id = str(oc.get("opportunity_id", "?"))
            build_errors.append(
                f"opportunity[{i}] (id={opportunity_id}) build error: {type(e).__name__}: {e}"
            )

    review_items.sort(key=lambda ri: (
        DECISION_PRIORITY.get(ri.recommended_decision, 99),
        -ri.score,
        -ri.source_diversity,
        -ri.recurrence,
        ri.review_item_id,
    ))

    review_items = review_items[:max_items]

    promote_count = sum(1 for ri in review_items if ri.recommended_decision == "PROMOTE")
    park_count = sum(1 for ri in review_items if ri.recommended_decision == "PARK")
    kill_count = sum(1 for ri in review_items if ri.recommended_decision == "KILL")
    needs_more_evidence_count = sum(1 for ri in review_items if ri.recommended_decision == "NEEDS_MORE_EVIDENCE")
    revisit_later_count = sum(1 for ri in review_items if ri.recommended_decision == "REVISIT_LATER")

    all_source_ids: set[str] = set()
    for ri in review_items:
        all_source_ids.update(ri.source_ids)
    source_ids = sorted(all_source_ids)

    # Compute package-level traceability summary
    traceability = _compute_package_traceability(review_items)

    warnings: list[str] = []
    if promote_count == 0 and review_items:
        warnings.append("No PROMOTE items in the review package.")
    if kill_count > 0 and kill_count >= len(review_items) * 0.5:
        warnings.append(f"High proportion of KILL items ({kill_count}/{len(review_items)}).")
    if sqr_dict is None:
        warnings.append("No source quality report supplied; source_quality_notes may be incomplete.")
    if not opps and clusters:
        warnings.append("No opportunity candidates supplied; review package may be cluster-only.")
    all_single_source = all(ri.source_diversity == 1 for ri in review_items)
    if all_single_source and review_items:
        warnings.append("All review items are single-source; cross-source validation missing.")

    if build_errors:
        warnings.append(f"Build errors encountered ({len(build_errors)} item(s) failed to build).")

    top_clusters: list[dict[str, Any]] = []
    for ri in review_items:
        if ri.pain_cluster_id:
            top_clusters.append({
                "cluster_id": ri.pain_cluster_id,
                "title": ri.title,
                "score": ri.score,
                "recommended_decision": ri.recommended_decision,
                "source_diversity": ri.source_diversity,
                "recurrence": ri.recurrence,
            })

    pkg_key = f"{discovery_run_id}|{created_at}|review"
    pkg_hash = hashlib.sha256(pkg_key.encode("utf-8")).hexdigest()[:12]
    package_id = f"frp_{pkg_hash}"

    return FounderReviewPackage(
        package_id=package_id,
        discovery_run_id=discovery_run_id,
        created_at=created_at,
        total_review_items=len(review_items),
        promote_count=promote_count,
        park_count=park_count,
        kill_count=kill_count,
        needs_more_evidence_count=needs_more_evidence_count,
        revisit_later_count=revisit_later_count,
        source_ids=source_ids,
        top_clusters=top_clusters,
        review_items=review_items,
        warnings=warnings,
        errors=build_errors,
        traceability_status=traceability["traceability_status"],
        total_evidence_links=traceability["total_evidence_links"],
        invalid_evidence_link_count=traceability["invalid_evidence_link_count"],
        missing_source_url_count=traceability["missing_source_url_count"],
        placeholder_url_count=traceability["placeholder_url_count"],
        non_http_url_count=traceability["non_http_url_count"],
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_founder_review_package(
    package: FounderReviewPackage,
) -> FounderReviewPackageValidationResult:
    """Validate a FounderReviewPackage and return structured result."""
    errors: list[str] = []
    warnings: list[str] = []

    if not package.review_items:
        errors.append("Package has no review items.")
        return FounderReviewPackageValidationResult(
            is_valid=False, errors=errors, warnings=warnings
        )

    for i, ri in enumerate(package.review_items):
        prefix = f"review_items[{i}]"

        if not ri.review_item_id:
            errors.append(f"{prefix} missing review_item_id")

        if ri.recommended_decision not in ALLOWED_RECOMMENDED_DECISIONS:
            errors.append(
                f"{prefix} invalid recommended_decision: {ri.recommended_decision!r}"
            )

        if not isinstance(ri.score, (int, float)):
            errors.append(f"{prefix} missing score")
        elif not (0.0 <= ri.score <= 1.0):
            errors.append(f"{prefix} score outside 0.0-1.0: {ri.score}")

        for j, el in enumerate(ri.evidence_links):
            el_prefix = f"{prefix}.evidence_links[{j}]"

            # Required identity fields
            if not el.evidence_id:
                errors.append(f"{el_prefix} missing evidence_id")
            if not el.source_id:
                errors.append(f"{el_prefix} missing source_id")
            if not el.source_type:
                errors.append(f"{el_prefix} missing source_type")
            if not el.title:
                errors.append(f"{el_prefix} missing title")
            if not el.excerpt:
                errors.append(f"{el_prefix} missing excerpt")
            if not el.evidence_kind:
                errors.append(f"{el_prefix} missing evidence_kind")

            # quality_flags must be list
            if not isinstance(el.quality_flags, list):
                errors.append(f"{el_prefix} quality_flags must be a list")

            # Source URL validation
            if not el.source_url:
                errors.append(f"{el_prefix} missing source_url")
            elif el.source_url.lower().startswith("urn:"):
                errors.append(f"{el_prefix} placeholder URL: {el.source_url}")
            elif not el.source_url.startswith(("http://", "https://")):
                errors.append(f"{el_prefix} non-http(s) URL: {el.source_url}")

    promote_count = sum(1 for ri in package.review_items if ri.recommended_decision == "PROMOTE")
    if promote_count == 0:
        warnings.append("No PROMOTE items in the review package.")

    kill_count = sum(1 for ri in package.review_items if ri.recommended_decision == "KILL")
    if kill_count > 0 and kill_count >= len(package.review_items) * 0.5:
        warnings.append(
            f"High proportion of KILL items ({kill_count}/{len(package.review_items)})."
        )

    all_single = all(ri.source_diversity == 1 for ri in package.review_items)
    if all_single and package.review_items:
        warnings.append("All review items are single-source evidence.")

    is_valid = len(errors) == 0
    all_warnings = list(warnings) + list(package.warnings)

    return FounderReviewPackageValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=all_warnings,
    )


# ---------------------------------------------------------------------------
# Markdown renderer (ASCII-safe)
# ---------------------------------------------------------------------------


def render_founder_review_package_markdown(
    package: FounderReviewPackage,
    output_mode: str = "ascii_safe",
) -> str:
    """Render a FounderReviewPackage to deterministic Markdown. ASCII-safe by default."""
    lines: list[str] = []

    lines.append("# Founder Review Package")
    lines.append("")
    lines.append(f"- **Package ID**: `{package.package_id}`")
    lines.append(f"- **Discovery Run ID**: `{package.discovery_run_id}`")
    lines.append(f"- **Generated**: {package.created_at}")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"This review package presents **{package.total_review_items}** review items "
        f"from the operational discovery pilot."
    )
    if package.promote_count > 0:
        lines.append(f"**{package.promote_count}** items are recommended for PROMOTE.")
    if package.needs_more_evidence_count > 0:
        lines.append(f"**{package.needs_more_evidence_count}** items need more evidence.")
    if package.park_count > 0:
        lines.append(f"**{package.park_count}** items are recommended to PARK.")
    if package.kill_count > 0:
        lines.append(f"**{package.kill_count}** items are recommended to KILL.")
    if package.revisit_later_count > 0:
        lines.append(f"**{package.revisit_later_count}** items are marked REVISIT_LATER.")
    lines.append("")

    if package.source_ids:
        lines.append(f"**Sources**: {', '.join(f'`{sid}`' for sid in package.source_ids)}")
        lines.append("")

    # Package-level traceability
    lines.append("### Traceability Summary")
    lines.append("")
    lines.append(f"- **Status**: {package.traceability_status}")
    lines.append(f"- **Total evidence links**: {package.total_evidence_links}")
    lines.append(f"- **Invalid evidence links**: {package.invalid_evidence_link_count}")
    lines.append(f"- **Missing source URLs**: {package.missing_source_url_count}")
    lines.append(f"- **Placeholder URLs**: {package.placeholder_url_count}")
    lines.append(f"- **Non-HTTP URLs**: {package.non_http_url_count}")
    lines.append("")

    lines.append("## Review Counts")
    lines.append("")
    lines.append("| Decision | Count |")
    lines.append("|----------|-------|")
    lines.append(f"| PROMOTE | {package.promote_count} |")
    lines.append(f"| NEEDS_MORE_EVIDENCE | {package.needs_more_evidence_count} |")
    lines.append(f"| REVISIT_LATER | {package.revisit_later_count} |")
    lines.append(f"| PARK | {package.park_count} |")
    lines.append(f"| KILL | {package.kill_count} |")
    lines.append(f"| **Total** | **{package.total_review_items}** |")
    lines.append("")

    lines.append("## Top Review Items")
    lines.append("")
    if package.review_items:
        lines.append(
            "| # | ID | Type | Title | Score | Decision | Sources | Diversity |"
        )
        lines.append(
            "|---|----|------|-------|-------|----------|---------|-----------|"
        )
        for idx, ri in enumerate(package.review_items, 1):
            short_title = ri.title[:60] + "..." if len(ri.title) > 60 else ri.title
            lines.append(
                f"| {idx} | `{ri.review_item_id}` | {ri.item_type} | "
                f"{short_title} | {ri.score:.2f} | {ri.recommended_decision} | "
                f"{', '.join(ri.source_ids) if ri.source_ids else 'none'} | "
                f"{ri.source_diversity} |"
            )
    else:
        lines.append("_No review items._")
    lines.append("")

    lines.append("## Review Item Details")
    lines.append("")
    for idx, ri in enumerate(package.review_items, 1):
        lines.append(f"### {idx}. {ri.review_item_id}")
        lines.append("")
        lines.append(f"- **Item Type**: {ri.item_type}")
        lines.append(f"- **Title**: {ri.title}")
        if ri.pain_cluster_id:
            lines.append(f"- **Pain Cluster**: `{ri.pain_cluster_id}`")
        if ri.opportunity_id:
            lines.append(f"- **Opportunity**: `{ri.opportunity_id}`")
        lines.append(f"- **Actor**: {ri.actor}" if ri.actor else "- **Actor**: _not specified_")
        if ri.workflow:
            lines.append(f"- **Workflow**: {ri.workflow}")
        if ri.object:
            lines.append(f"- **Object**: {ri.object}")
        if ri.pain_pattern:
            lines.append(f"- **Pain Pattern**: {ri.pain_pattern}")
        lines.append(f"- **Score**: {ri.score:.2f}")
        lines.append(f"- **Recurrence**: {ri.recurrence}")
        lines.append(f"- **Source Diversity**: {ri.source_diversity}")
        lines.append(f"- **Business Relevance**: {ri.business_relevance:.2f}")
        lines.append(f"- **Noise Risk**: {ri.noise_risk:.2f}")
        lines.append(f"- **Uncertainty**: {ri.uncertainty}")
        lines.append(f"- **Evidence Summary**: {ri.evidence_summary}")
        lines.append("")

    lines.append("## Score Explanations")
    lines.append("")
    for ri in package.review_items:
        if ri.score_components:
            lines.append(f"### {ri.review_item_id}")
            lines.append("")
            lines.append("| Component | Score |")
            lines.append("|-----------|-------|")
            for name, value in ri.score_components.items():
                lines.append(f"| {name} | {value:.2f} |")
            lines.append(f"| **Overall** | **{ri.score:.2f}** |")
            lines.append("")

    lines.append("## Evidence Links")
    lines.append("")
    for ri in package.review_items:
        if ri.evidence_links:
            lines.append(f"### {ri.review_item_id}")
            lines.append("")
            for el in ri.evidence_links:
                lines.append(f"- **{el.evidence_id}**")
                lines.append(f"  - Source: `{el.source_id}` ({el.source_type})")
                lines.append(f"  - Title: {el.title}")
                lines.append(f"  - Kind: {el.evidence_kind}")
                lines.append(f"  - URL: {el.source_url}")
                if el.quality_flags:
                    lines.append(f"  - Quality Flags: {', '.join(el.quality_flags)}")
                lines.append(f"  - Excerpt: {el.excerpt[:200]}")
            lines.append("")

    lines.append("## Recommended Decisions")
    lines.append("")
    lines.append("| ID | Decision | Reason |")
    lines.append("|----|----------|--------|")
    for ri in package.review_items:
        reason = (
            ri.recommendation_reason[:80] + "..."
            if len(ri.recommendation_reason) > 80
            else ri.recommendation_reason
        )
        lines.append(
            f"| `{ri.review_item_id}` | {ri.recommended_decision} | {reason} |"
        )
    lines.append("")

    lines.append("## Suggested Validation Actions")
    lines.append("")
    lines.append("| ID | Suggestion |")
    lines.append("|----|------------|")
    for ri in package.review_items:
        lines.append(
            f"| `{ri.review_item_id}` | {ri.suggested_validation_action} |"
        )
    lines.append("")

    lines.append("## Risks and Caveats")
    lines.append("")
    if package.errors:
        for e in package.errors:
            lines.append(f"- ERROR: {e}")
    if package.warnings:
        for w in package.warnings:
            lines.append(f"- WARNING: {w}")
    if not package.errors and not package.warnings:
        lines.append("- No risks or caveats identified.")
    lines.append("")
    lines.append(
        "Recommendations are advisory only. The founder must review each item "
        "and record final decisions."
    )
    lines.append("")
    lines.append(
        "This review package is generated from deterministic pipeline data. "
        "Small sample sizes and limited source scope (HN + GitHub Issues) are "
        "inherent limitations of the operational discovery pilot."
    )
    lines.append("")

    lines.append("## Source Quality Notes")
    lines.append("")
    items_with_notes = [ri for ri in package.review_items if ri.source_quality_notes]
    if items_with_notes:
        for ri in items_with_notes:
            lines.append(f"- **{ri.review_item_id}**: {ri.source_quality_notes}")
    else:
        lines.append("_No source quality concerns for any review item._")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        f"*Founder Review Package {package.package_id} -- "
        f"generated by OOS Pilot Founder Review Package*"
    )
    lines.append("")

    return "\n".join(lines)
