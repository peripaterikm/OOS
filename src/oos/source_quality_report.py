from __future__ import annotations

"""Source Quality Report — deterministic source performance and quality metrics.

Implements the Source Quality Report specified in
docs/contracts/operational_discovery_pilot_run_contract.md Sections 10–11.

Accepts plain deterministic inputs (no live sources, no APIs, no LLM).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .pain_cluster_dedupe import (
    normalize_source_id,
    normalize_source_type,
    SOURCE_ID_NORMALIZATION,
)
from .pain_cluster import PainCluster

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0.0"
ARTIFACT_TYPE = "source_quality_report"

CANONICAL_SOURCE_IDS = frozenset({"hacker_news", "github_issues"})
CANONICAL_SOURCE_TYPES = frozenset({"discussion", "issue_tracker"})

# Expected noise categories (contract Section 10 / task description item 9)
KNOWN_NOISE_CATEGORIES: frozenset[str] = frozenset({
    "low_text_context",
    "suspected_self_promo",
    "launch_hype",
    "flamewar_or_meta_discussion",
    "bot_generated",
    "stale_issue",
    "duplicate_or_invalid",
    "wontfix_or_not_planned",
    "maintainer_housekeeping",
    "source_access_limited",
    "missing_source_url",
    "placeholder_url",
    "low_confidence_source",
    "requires_manual_review",
})

# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_rate(numerator: int, denominator: int) -> float:
    """Return numerator/denominator as float 0.0–1.0, avoiding div-by-zero."""
    if denominator <= 0:
        return 0.0
    return round(min(1.0, max(0.0, numerator / denominator)), 4)


def _strip_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_evidence_dict(ev: dict[str, Any]) -> dict[str, Any]:
    """Normalize source_id and source_type on an evidence dict."""
    result = dict(ev)
    if "source_id" in result:
        result["source_id"] = normalize_source_id(str(result["source_id"]))
    if "source_type" in result:
        result["source_type"] = normalize_source_type(str(result["source_type"]))
    return result


def _evidence_source_id(ev: dict[str, Any]) -> str:
    return normalize_source_id(str(ev.get("source_id", "") or ""))


def _evidence_source_type(ev: dict[str, Any]) -> str:
    return normalize_source_type(str(ev.get("source_type", "") or ""))


def _normalize_opportunity_candidate(oc: Any) -> dict[str, Any]:
    """Accept an opportunity candidate as dict or object with to_dict()."""
    if isinstance(oc, dict):
        return dict(oc)
    if hasattr(oc, "to_dict"):
        return oc.to_dict()  # type: ignore[union-attr]
    if hasattr(oc, "__dict__"):
        return {k: v for k, v in vars(oc).items() if not k.startswith("_")}
    return {"_raw": str(oc)}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SourceQualityMetrics:
    """Per-source quality metrics (contract Section 11)."""

    source_id: str
    source_type: str
    records_seen: int = 0
    records_emitted: int = 0
    records_rejected: int = 0
    accepted_signal_count: int = 0
    weak_signal_count: int = 0
    noise_signal_count: int = 0
    accepted_rate: float = 0.0
    noise_rate: float = 0.0
    duplicate_count: int = 0
    missing_url_count: int = 0
    placeholder_url_count: int = 0
    source_url_validation_passed: bool = False
    source_diversity_contribution: int = 0
    cluster_contribution_count: int = 0
    opportunity_contribution_count: int = 0
    founder_promote_count: int = 0
    founder_kill_count: int = 0
    founder_needs_more_evidence_count: int = 0
    quality_flag_counts: dict[str, int] = field(default_factory=dict)
    rejection_reasons: list[str] = field(default_factory=list)

    def recompute_rates(self) -> None:
        total_classified = (
            self.accepted_signal_count
            + self.weak_signal_count
            + self.noise_signal_count
        )
        self.accepted_rate = _safe_rate(self.accepted_signal_count, total_classified)
        self.noise_rate = _safe_rate(self.noise_signal_count, total_classified)
        self.source_url_validation_passed = (
            self.missing_url_count == 0 and self.placeholder_url_count == 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "records_seen": self.records_seen,
            "records_emitted": self.records_emitted,
            "records_rejected": self.records_rejected,
            "accepted_signal_count": self.accepted_signal_count,
            "weak_signal_count": self.weak_signal_count,
            "noise_signal_count": self.noise_signal_count,
            "accepted_rate": self.accepted_rate,
            "noise_rate": self.noise_rate,
            "duplicate_count": self.duplicate_count,
            "missing_url_count": self.missing_url_count,
            "placeholder_url_count": self.placeholder_url_count,
            "source_url_validation_passed": self.source_url_validation_passed,
            "source_diversity_contribution": self.source_diversity_contribution,
            "cluster_contribution_count": self.cluster_contribution_count,
            "opportunity_contribution_count": self.opportunity_contribution_count,
            "founder_promote_count": self.founder_promote_count,
            "founder_kill_count": self.founder_kill_count,
            "founder_needs_more_evidence_count": self.founder_needs_more_evidence_count,
            "quality_flag_counts": dict(self.quality_flag_counts),
            "rejection_reasons": list(self.rejection_reasons),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceQualityMetrics:
        return cls(
            source_id=str(data.get("source_id", "")),
            source_type=str(data.get("source_type", "")),
            records_seen=int(data.get("records_seen", 0)),
            records_emitted=int(data.get("records_emitted", 0)),
            records_rejected=int(data.get("records_rejected", 0)),
            accepted_signal_count=int(data.get("accepted_signal_count", 0)),
            weak_signal_count=int(data.get("weak_signal_count", 0)),
            noise_signal_count=int(data.get("noise_signal_count", 0)),
            accepted_rate=float(data.get("accepted_rate", 0.0)),
            noise_rate=float(data.get("noise_rate", 0.0)),
            duplicate_count=int(data.get("duplicate_count", 0)),
            missing_url_count=int(data.get("missing_url_count", 0)),
            placeholder_url_count=int(data.get("placeholder_url_count", 0)),
            source_url_validation_passed=bool(data.get("source_url_validation_passed", False)),
            source_diversity_contribution=int(data.get("source_diversity_contribution", 0)),
            cluster_contribution_count=int(data.get("cluster_contribution_count", 0)),
            opportunity_contribution_count=int(data.get("opportunity_contribution_count", 0)),
            founder_promote_count=int(data.get("founder_promote_count", 0)),
            founder_kill_count=int(data.get("founder_kill_count", 0)),
            founder_needs_more_evidence_count=int(
                data.get("founder_needs_more_evidence_count", 0)
            ),
            quality_flag_counts=dict(data.get("quality_flag_counts", {})),
            rejection_reasons=list(data.get("rejection_reasons", [])),
        )


@dataclass
class NoiseCategorySummary:
    """A single noise category aggregated across sources."""

    category: str
    count: int
    source_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "count": self.count,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NoiseCategorySummary:
        return cls(
            category=str(data.get("category", "")),
            count=int(data.get("count", 0)),
            source_id=str(data.get("source_id", "")),
        )


@dataclass
class SourceQualityReportValidationResult:
    """Validation result for a SourceQualityReport."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass
class SourceQualityReport:
    """Structured source quality report (contract Section 10)."""

    report_id: str
    discovery_run_id: str
    created_at: str
    source_metrics: list[SourceQualityMetrics] = field(default_factory=list)
    raw_evidence_total: int = 0
    accepted_signal_total: int = 0
    weak_signal_total: int = 0
    noise_signal_total: int = 0
    pain_cluster_count: int = 0
    opportunity_candidate_count: int = 0
    top_pain_clusters: list[dict[str, Any]] = field(default_factory=list)
    opportunity_candidates: list[dict[str, Any]] = field(default_factory=list)
    main_noise_categories: list[NoiseCategorySummary] = field(default_factory=list)
    founder_decisions_needed: dict[str, int] = field(default_factory=dict)
    next_validation_actions: list[str] = field(default_factory=list)
    traceability_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": ARTIFACT_TYPE,
            "schema_version": SCHEMA_VERSION,
            "report_id": self.report_id,
            "discovery_run_id": self.discovery_run_id,
            "created_at": self.created_at,
            "source_metrics": [m.to_dict() for m in self.source_metrics],
            "raw_evidence_total": self.raw_evidence_total,
            "accepted_signal_total": self.accepted_signal_total,
            "weak_signal_total": self.weak_signal_total,
            "noise_signal_total": self.noise_signal_total,
            "pain_cluster_count": self.pain_cluster_count,
            "opportunity_candidate_count": self.opportunity_candidate_count,
            "top_pain_clusters": list(self.top_pain_clusters),
            "opportunity_candidates": list(self.opportunity_candidates),
            "main_noise_categories": [nc.to_dict() for nc in self.main_noise_categories],
            "founder_decisions_needed": dict(self.founder_decisions_needed),
            "next_validation_actions": list(self.next_validation_actions),
            "traceability_summary": dict(self.traceability_summary),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceQualityReport:
        return cls(
            report_id=str(data.get("report_id", "")),
            discovery_run_id=str(data.get("discovery_run_id", "")),
            created_at=str(data.get("created_at", "")),
            source_metrics=[
                SourceQualityMetrics.from_dict(m)
                for m in data.get("source_metrics", [])
            ],
            raw_evidence_total=int(data.get("raw_evidence_total", 0)),
            accepted_signal_total=int(data.get("accepted_signal_total", 0)),
            weak_signal_total=int(data.get("weak_signal_total", 0)),
            noise_signal_total=int(data.get("noise_signal_total", 0)),
            pain_cluster_count=int(data.get("pain_cluster_count", 0)),
            opportunity_candidate_count=int(data.get("opportunity_candidate_count", 0)),
            top_pain_clusters=list(data.get("top_pain_clusters", [])),
            opportunity_candidates=list(data.get("opportunity_candidates", [])),
            main_noise_categories=[
                NoiseCategorySummary.from_dict(nc)
                for nc in data.get("main_noise_categories", [])
            ],
            founder_decisions_needed=dict(data.get("founder_decisions_needed", {})),
            next_validation_actions=list(data.get("next_validation_actions", [])),
            traceability_summary=dict(data.get("traceability_summary", {})),
            warnings=list(data.get("warnings", [])),
            errors=list(data.get("errors", [])),
        )


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def build_source_quality_report(
    *,
    evidence_items: list[dict[str, Any]] | None = None,
    candidate_signals: list[dict[str, Any]] | None = None,
    pain_clusters: list[PainCluster] | list[dict[str, Any]] | None = None,
    opportunity_candidates: list[dict[str, Any]] | None = None,
    source_summaries: dict[str, dict[str, Any]] | None = None,
    founder_decision_counts: dict[str, dict[str, int]] | None = None,
    discovery_run_id: str = "pilot_run_unknown",
    created_at: str | None = None,
) -> SourceQualityReport:
    """Build a deterministic Source Quality Report from pipeline inputs.

    All inputs are plain data (dicts, model objects). No live sources.
    No filesystem access. No LLM calls.

    Args:
        evidence_items: Raw evidence records as dicts (minimum: evidence_id,
            source_id, source_type, source_url, title, body).
        candidate_signals: Extracted candidate signals as dicts (minimum:
            signal_id, evidence_id, source_id, source_type, classification,
            quality_flags).
        pain_clusters: PainCluster objects or dicts.
        opportunity_candidates: Opportunity candidate dicts or objects.
        source_summaries: Optional per-source local summaries from collectors
            (records_seen, records_emitted, records_rejected, etc.).
        founder_decision_counts: Optional per-source founder decision counts
            (promote, kill, needs_more_evidence).
        discovery_run_id: Identifier for the pilot run.
        created_at: Timestamp string (defaults to UTC now). Inject for tests.

    Returns:
        SourceQualityReport with all metrics, clusters, and recommendations.
    """
    evidence_items = list(evidence_items or [])
    candidate_signals = list(candidate_signals or [])
    opp_candidates = [_normalize_opportunity_candidate(oc) for oc in (opportunity_candidates or [])]

    # Normalize source_id/source_type on all evidence
    evidence_items = [_normalize_evidence_dict(ev) for ev in evidence_items]
    candidate_signals = [_normalize_evidence_dict(sig) for sig in candidate_signals]

    # Normalize pain clusters to dicts
    clusters: list[dict[str, Any]] = []
    for pc in pain_clusters or []:
        if isinstance(pc, PainCluster):
            clusters.append(pc.to_dict())
        elif isinstance(pc, dict):
            clusters.append(dict(pc))
        # else skip unknown types

    if created_at is None:
        created_at = _iso_utc_now()

    report_id = _make_report_id(discovery_run_id, created_at)

    # ---- Discover active source_ids ----
    source_ids: set[str] = set()
    for ev in evidence_items:
        sid = _evidence_source_id(ev)
        if sid:
            source_ids.add(sid)
    for sig in candidate_signals:
        sid = _evidence_source_id(sig)
        if sid:
            source_ids.add(sid)
    for pc in clusters:
        for entry in pc.get("source_evidence_list", []):
            sid = normalize_source_id(str(entry.get("source_id", "") or ""))
            if sid:
                source_ids.add(sid)

    # Ensure canonical order
    ordered_source_ids = sorted(source_ids)

    # ---- Build per-source metrics ----
    source_metrics: list[SourceQualityMetrics] = []
    for sid in ordered_source_ids:
        stype = _infer_source_type(sid, evidence_items, clusters)
        local_summary = (source_summaries or {}).get(sid, {})
        fd_counts = (founder_decision_counts or {}).get(sid, {})

        metrics = _build_source_metrics(
            source_id=sid,
            source_type=stype,
            evidence_items=evidence_items,
            candidate_signals=candidate_signals,
            clusters=clusters,
            opp_candidates=opp_candidates,
            local_summary=local_summary,
            fd_counts=fd_counts,
        )
        source_metrics.append(metrics)

    # ---- Aggregate totals ----
    raw_evidence_total = len(evidence_items)
    accepted_signal_total = sum(m.accepted_signal_count for m in source_metrics)
    weak_signal_total = sum(m.weak_signal_count for m in source_metrics)
    noise_signal_total = sum(m.noise_signal_count for m in source_metrics)

    # ---- Top pain clusters ----
    top_pain_clusters = _build_top_pain_clusters(clusters, max_clusters=20)

    # ---- Opportunity candidates ----
    opportunity_candidates_list = _build_opportunity_candidates_section(opp_candidates)

    # ---- Main noise categories ----
    main_noise_categories = _build_noise_categories(evidence_items, candidate_signals)

    # ---- Founder decisions needed ----
    founder_decisions_needed = {
        "clusters_awaiting_review": sum(
            1 for pc in clusters
            if pc.get("status") in ("new", "needs_more_evidence", None)
        ),
        "opportunity_candidates_awaiting_review": sum(
            1 for oc in opp_candidates
            if oc.get("founder_review_status") in ("pending_review", None, "")
        ),
    }
    founder_decisions_needed["total_pending_decisions"] = (
        founder_decisions_needed["clusters_awaiting_review"]
        + founder_decisions_needed["opportunity_candidates_awaiting_review"]
    )

    # ---- Traceability summary ----
    traceability_summary = _build_traceability_summary(evidence_items, clusters)

    # ---- Validation warnings / errors ----
    errors, warnings = _validate_report_state(
        source_metrics=source_metrics,
        clusters=clusters,
        opp_candidates=opp_candidates,
        traceability_summary=traceability_summary,
        evidence_items=evidence_items,
    )

    # ---- Next validation actions ----
    next_validation_actions = _build_next_validation_actions(
        source_metrics=source_metrics,
        clusters=clusters,
        opp_candidates=opp_candidates,
        traceability_summary=traceability_summary,
        warnings=warnings,
    )

    report = SourceQualityReport(
        report_id=report_id,
        discovery_run_id=discovery_run_id,
        created_at=created_at,
        source_metrics=source_metrics,
        raw_evidence_total=raw_evidence_total,
        accepted_signal_total=accepted_signal_total,
        weak_signal_total=weak_signal_total,
        noise_signal_total=noise_signal_total,
        pain_cluster_count=len(clusters),
        opportunity_candidate_count=len(opp_candidates),
        top_pain_clusters=top_pain_clusters,
        opportunity_candidates=opportunity_candidates_list,
        main_noise_categories=main_noise_categories,
        founder_decisions_needed=founder_decisions_needed,
        next_validation_actions=next_validation_actions,
        traceability_summary=traceability_summary,
        warnings=warnings,
        errors=errors,
    )

    return report


# ---------------------------------------------------------------------------
# Internal metric builders
# ---------------------------------------------------------------------------


def _make_report_id(discovery_run_id: str, created_at: str) -> str:
    """Generate a stable report_id."""
    import hashlib
    key = f"{discovery_run_id}|{created_at}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"sqr_{digest}"


def _infer_source_type(
    source_id: str,
    evidence_items: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
) -> str:
    """Map source_id to canonical source_type."""
    # Check evidence first
    for ev in evidence_items:
        if _evidence_source_id(ev) == source_id:
            st = _evidence_source_type(ev)
            if st in CANONICAL_SOURCE_TYPES:
                return st
    # Check clusters
    for pc in clusters:
        for entry in pc.get("source_evidence_list", []):
            if normalize_source_id(str(entry.get("source_id", ""))) == source_id:
                st = normalize_source_type(str(entry.get("source_type", "")))
                if st in CANONICAL_SOURCE_TYPES:
                    return st
    # Fallback mapping
    if source_id == "hacker_news":
        return "discussion"
    if source_id == "github_issues":
        return "issue_tracker"
    return "unknown"


def _build_source_metrics(
    *,
    source_id: str,
    source_type: str,
    evidence_items: list[dict[str, Any]],
    candidate_signals: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    opp_candidates: list[dict[str, Any]],
    local_summary: dict[str, Any],
    fd_counts: dict[str, int],
) -> SourceQualityMetrics:
    """Build per-source metrics."""

    # Filter evidence for this source
    source_evidence = [
        ev for ev in evidence_items
        if _evidence_source_id(ev) == source_id
    ]
    source_signals = [
        sig for sig in candidate_signals
        if _evidence_source_id(sig) == source_id
    ]

    # Records seen/emitted/rejected from local_summary or from evidence
    records_seen = int(local_summary.get("records_seen", 0)) or len(source_evidence)
    records_emitted = int(local_summary.get("records_emitted", 0)) or len(source_evidence)
    records_rejected = max(0, records_seen - records_emitted)

    # Signal classification — infer from signal's classification field
    accepted = weak = noise = 0
    for sig in source_signals:
        classification = str(sig.get("classification", "") or "").lower()
        if classification in ("pain_signal_candidate", "workaround_signal_candidate",
                              "buying_intent_candidate", "competitor_weakness_candidate",
                              "trend_trigger_candidate"):
            accepted += 1
        elif classification in ("needs_human_review",):
            weak += 1
        elif classification in ("noise",):
            noise += 1
        else:
            # Try signal_type
            sig_type = str(sig.get("signal_type", "") or "").lower()
            if sig_type in ("pain_signal", "workaround", "buying_intent",
                            "competitor_weakness", "trend_trigger"):
                accepted += 1
            elif sig_type in ("needs_human_review",):
                weak += 1
            else:
                # Default: count as weak (unclassified)
                weak += 1

    # Duplicate count
    duplicate_count = int(local_summary.get("duplicate_count", 0))
    for ev in source_evidence:
        if ev.get("duplicate_of"):
            duplicate_count += 1

    # URL validation
    missing_url_count = 0
    placeholder_url_count = 0
    for ev in source_evidence:
        url = str(ev.get("source_url", "") or "").strip()
        if not url:
            missing_url_count += 1
        elif url.lower().startswith("urn:"):
            placeholder_url_count += 1

    # Cluster/opportunity contributions
    cluster_contribution_count = 0
    opportunity_contribution_count = 0
    for pc in clusters:
        ev_ids_in_cluster = {
            e.get("source_id") for e in pc.get("source_evidence_list", [])
        }
        # Check if this source contributed to this cluster
        sid_normalized = normalize_source_id(source_id)
        contributed = False
        for e in pc.get("source_evidence_list", []):
            e_sid = normalize_source_id(str(e.get("source_id", "") or ""))
            if e_sid == sid_normalized:
                contributed = True
                break
        if contributed:
            cluster_contribution_count += 1
            # Check if any opp candidate links to this cluster
            cluster_id = pc.get("cluster_id", "")
            for oc in opp_candidates:
                oc_cluster = str(oc.get("source_pain_cluster_id", "") or "")
                if oc_cluster == cluster_id:
                    opportunity_contribution_count += 1

    # Source diversity contribution = number of distinct clusters this source
    # contributed to (same as cluster_contribution_count)
    source_diversity_contribution = cluster_contribution_count

    # Quality flag counts
    quality_flag_counts: dict[str, int] = {}
    for ev in source_evidence:
        for flag in ev.get("quality_flags", []) or []:
            flag_key = str(flag).lower().replace(" ", "_")
            quality_flag_counts[flag_key] = quality_flag_counts.get(flag_key, 0) + 1

    # Rejection reasons from local_summary
    rejection_reasons = list(local_summary.get("rejection_reasons", []) or [])

    # Founder decision counts
    founder_promote = int(fd_counts.get("promote", 0))
    founder_kill = int(fd_counts.get("kill", 0))
    founder_needs_more = int(fd_counts.get("needs_more_evidence", 0))

    metrics = SourceQualityMetrics(
        source_id=source_id,
        source_type=source_type,
        records_seen=records_seen,
        records_emitted=records_emitted,
        records_rejected=records_rejected,
        accepted_signal_count=accepted,
        weak_signal_count=weak,
        noise_signal_count=noise,
        duplicate_count=duplicate_count,
        missing_url_count=missing_url_count,
        placeholder_url_count=placeholder_url_count,
        source_diversity_contribution=source_diversity_contribution,
        cluster_contribution_count=cluster_contribution_count,
        opportunity_contribution_count=opportunity_contribution_count,
        founder_promote_count=founder_promote,
        founder_kill_count=founder_kill,
        founder_needs_more_evidence_count=founder_needs_more,
        quality_flag_counts=quality_flag_counts,
        rejection_reasons=rejection_reasons,
    )
    metrics.recompute_rates()
    return metrics


# ---------------------------------------------------------------------------
# Top pain clusters
# ---------------------------------------------------------------------------


def _build_top_pain_clusters(
    clusters: list[dict[str, Any]],
    max_clusters: int = 20,
) -> list[dict[str, Any]]:
    """Build ranked list of top pain clusters for the report.

    Sort order (contract Section 12.2 / task item 7):
    1. scoring.overall descending
    2. source_diversity descending
    3. recurrence descending
    4. cluster_id ascending
    """
    scored: list[dict[str, Any]] = []
    for pc in clusters:
        scoring = pc.get("scoring", {})
        if isinstance(scoring, dict):
            overall = float(scoring.get("overall", 0))
        else:
            overall = 0.0
        sd = int(pc.get("source_diversity", 1))
        rec = int(pc.get("recurrence", 1))
        cid = str(pc.get("cluster_id", ""))

        entry = {
            "cluster_id": cid,
            "actor": str(pc.get("actor", "")),
            "workflow": str(pc.get("workflow", "")),
            "object": str(pc.get("object", "")),
            "pain_pattern": str(pc.get("pain_pattern", "")),
            "overall_score": overall,
            "recurrence": rec,
            "source_diversity": sd,
            "business_relevance": float(pc.get("business_relevance", 0)),
            "noise_risk": float(pc.get("noise_risk", 0)),
            "source_evidence_count": len(pc.get("source_evidence_list", [])),
            "source_ids": sorted(set(
                normalize_source_id(str(e.get("source_id", "")))
                for e in pc.get("source_evidence_list", [])
            )),
            "status": str(pc.get("status", "new")),
            "recommended_tier": _cluster_tier_label(
                overall, float(pc.get("noise_risk", 0))
            ),
        }
        scored.append(entry)

    scored.sort(key=lambda c: (
        -c["overall_score"],
        -c["source_diversity"],
        -c["recurrence"],
        c["cluster_id"],
    ))

    return scored[:max_clusters]


def _cluster_tier_label(overall: float, noise_risk: float) -> str:
    if noise_risk >= 0.80:
        return "noise_or_park"
    if overall >= 0.70:
        return "candidate"
    if overall >= 0.50:
        return "needs_more_evidence"
    return "noise_or_park"


# ---------------------------------------------------------------------------
# Opportunity candidates section
# ---------------------------------------------------------------------------


def _build_opportunity_candidates_section(
    opp_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the opportunity candidates list for the report."""
    result: list[dict[str, Any]] = []
    for oc in opp_candidates:
        entry: dict[str, Any] = {
            "opportunity_id": str(oc.get("opportunity_id", "")),
            "source_pain_cluster_id": str(oc.get("source_pain_cluster_id", "")),
            "actor_or_icp": str(oc.get("actor", "") or oc.get("icp", "")),
            "problem_statement": str(oc.get("problem_statement", "")),
            "evidence_summary": str(oc.get("evidence_summary", "")),
            "source_evidence_links": oc.get("source_evidence_links", []),
            "score": float(oc.get("score", 0)),
            "uncertainty": str(oc.get("uncertainty", "unknown")),
            "suggested_validation_action": str(
                oc.get("suggested_validation_action", "")
            ),
            "founder_review_status": str(
                oc.get("founder_review_status", "pending_review")
            ),
        }
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Noise categories
# ---------------------------------------------------------------------------


def _build_noise_categories(
    evidence_items: list[dict[str, Any]],
    candidate_signals: list[dict[str, Any]],
) -> list[NoiseCategorySummary]:
    """Aggregate noise categories from quality_flags and rejection_reasons."""

    category_counts: dict[str, dict[str, int]] = {}
    # category -> {source_id: count}

    def _add(category: str, source_id: str) -> None:
        cat_norm = category.lower().replace(" ", "_")
        if cat_norm not in category_counts:
            category_counts[cat_norm] = {}
        category_counts[cat_norm][source_id] = (
            category_counts[cat_norm].get(source_id, 0) + 1
        )

    # From evidence quality_flags
    for ev in evidence_items:
        sid = _evidence_source_id(ev)
        for flag in ev.get("quality_flags", []) or []:
            _add(str(flag), sid)

    # From candidate signal classification
    for sig in candidate_signals:
        sid = _evidence_source_id(sig)
        classification = str(sig.get("classification", "") or "").lower()
        if classification == "noise":
            reason = str(sig.get("rejection_reason", "") or "")
            if reason:
                _add(reason, sid)
            _add("noise_classified", sid)

    # Build summaries, sorted by total count descending
    flat: list[tuple[str, str, int]] = []
    for cat, src_counts in category_counts.items():
        for src_id, count in src_counts.items():
            flat.append((cat, src_id, count))

    flat.sort(key=lambda x: (-x[2], x[0], x[1]))

    return [
        NoiseCategorySummary(category=cat, count=cnt, source_id=sid)
        for cat, sid, cnt in flat
    ]


# ---------------------------------------------------------------------------
# Traceability summary
# ---------------------------------------------------------------------------


def _build_traceability_summary(
    evidence_items: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the traceability summary section."""

    total_records = len(evidence_items)
    missing = 0
    placeholder = 0
    for ev in evidence_items:
        url = str(ev.get("source_url", "") or "").strip()
        if not url:
            missing += 1
        elif url.lower().startswith("urn:"):
            placeholder += 1

    clusters_with_all_urls = 0
    clusters_with_failures = 0
    for pc in clusters:
        all_ok = True
        for entry in pc.get("source_evidence_list", []):
            url = str(entry.get("source_url", "") or "").strip()
            if not url or url.lower().startswith("urn:"):
                all_ok = False
                break
        if all_ok:
            clusters_with_all_urls += 1
        else:
            clusters_with_failures += 1

    failures: list[str] = []
    if missing > 0:
        failures.append(f"missing_source_url_count={missing}")
    if placeholder > 0:
        failures.append(f"placeholder_url_count={placeholder}")
    if clusters_with_failures > 0:
        failures.append(f"clusters_with_url_failures={clusters_with_failures}")

    return {
        "total_records": total_records,
        "records_missing_source_url": missing,
        "placeholder_url_count": placeholder,
        "source_url_validation_passed": (missing == 0 and placeholder == 0),
        "clusters_with_all_evidence_urls": clusters_with_all_urls,
        "clusters_with_url_failures": clusters_with_failures,
        "opportunity_candidates_with_traceability": 0,  # filled if candidates provided
        "failures": failures,
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_report_state(
    *,
    source_metrics: list[SourceQualityMetrics],
    clusters: list[dict[str, Any]],
    opp_candidates: list[dict[str, Any]],
    traceability_summary: dict[str, Any],
    evidence_items: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Validate report state and return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    # Fail: no source metrics
    if not source_metrics:
        errors.append("no source metrics computed")

    # Fail: source_id missing in any metric
    for m in source_metrics:
        if not m.source_id:
            errors.append("source metric missing source_id")

    # Fail: source_url traceability failure
    if not traceability_summary.get("source_url_validation_passed", False):
        failures = traceability_summary.get("failures", [])
        for f in failures:
            errors.append(f"traceability failure: {f}")

    # Warn: zero clusters
    if len(clusters) == 0:
        warnings.append("zero pain clusters formed")

    # Warn: high noise rate (> 60%)
    for m in source_metrics:
        if m.noise_rate > 0.60:
            warnings.append(
                f"high noise rate for {m.source_id}: {m.noise_rate}"
            )

    # Warn: low source diversity (all clusters single-source)
    if clusters:
        all_single_source = all(
            int(pc.get("source_diversity", 1)) == 1
            for pc in clusters
        )
        if all_single_source:
            warnings.append("all clusters are single-source (low source diversity)")

    # Warn: no opportunity candidates
    if not opp_candidates:
        warnings.append("no opportunity candidates supplied")

    # Warn: founder decisions needed but clusters exist
    pending = sum(
        1 for pc in clusters
        if pc.get("status") in ("new", "needs_more_evidence", None)
    )
    if pending > 0 and not opp_candidates:
        warnings.append(
            f"{pending} clusters awaiting founder review, but no review package"
        )

    return errors, warnings


# ---------------------------------------------------------------------------
# Next validation actions
# ---------------------------------------------------------------------------


def _build_next_validation_actions(
    *,
    source_metrics: list[SourceQualityMetrics],
    clusters: list[dict[str, Any]],
    opp_candidates: list[dict[str, Any]],
    traceability_summary: dict[str, Any],
    warnings: list[str],
) -> list[str]:
    """Build deterministic suggestions based on report state."""

    actions: list[str] = []

    if not clusters:
        actions.append(
            "No clusters formed. Improve evidence collection: broaden queries, "
            "increase collection window, or enable additional sources."
        )

    # High noise rate
    for m in source_metrics:
        if m.noise_rate > 0.60:
            actions.append(
                f"High noise rate ({m.noise_rate}) for {m.source_id}. "
                f"Tune noise filters and review quality flags."
            )

    # Low source diversity
    all_single = all(
        int(pc.get("source_diversity", 1)) == 1
        for pc in clusters
    )
    if all_single and len(clusters) > 0:
        actions.append(
            "Low source diversity: all clusters are single-source. "
            "Adjust source mix or queries to enable cross-source validation."
        )

    # Missing traceability
    if not traceability_summary.get("source_url_validation_passed", False):
        actions.append(
            "Traceability failures detected. Fix source_url handling "
            "before founder review."
        )

    # Few candidates despite clusters
    if clusters and not opp_candidates:
        actions.append(
            "Clusters exist but no opportunity candidates. "
            "Consider founder review or collecting more evidence."
        )

    # Top clusters exceed threshold → suggest validation
    candidate_clusters = [
        pc for pc in clusters
        if _cluster_tier_label(
            float(pc.get("scoring", {}).get("overall", 0)),
            float(pc.get("noise_risk", 0)),
        ) == "candidate"
    ]
    if candidate_clusters:
        actions.append(
            f"{len(candidate_clusters)} clusters at candidate tier. "
            f"Suggest: interview target users, build landing page test, "
            f"or conduct manual market research."
        )

    # No actions triggered? Default message
    if not actions:
        actions.append(
            "Source quality report is clean. Proceed with founder review."
        )

    return actions


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_source_quality_report_markdown(
    report: SourceQualityReport,
    output_mode: str = "ascii_safe",
) -> str:
    """Render a SourceQualityReport to deterministic Markdown.

    ASCII-safe by default. No colors. No Unicode symbols.

    Args:
        report: The SourceQualityReport to render.
        output_mode: 'ascii_safe' (default) or 'utf8'.

    Returns:
        Markdown string.
    """
    lines: list[str] = []

    # Title
    lines.append("# Source Quality Report")
    lines.append("")
    lines.append(f"- **Report ID**: `{report.report_id}`")
    lines.append(f"- **Discovery Run ID**: `{report.discovery_run_id}`")
    lines.append(f"- **Generated**: {report.created_at}")
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"This pilot run processed **{report.raw_evidence_total}** raw evidence items, "
        f"producing **{report.accepted_signal_total}** accepted signals, "
        f"**{report.weak_signal_total}** weak signals, and "
        f"**{report.noise_signal_total}** noise signals."
    )
    if report.pain_cluster_count:
        lines.append(
            f"Formed **{report.pain_cluster_count}** pain clusters "
            f"and **{report.opportunity_candidate_count}** opportunity candidates."
        )
    else:
        lines.append("No pain clusters were formed in this run.")
    lines.append("")

    # Source quality table
    lines.append("## Source Quality by Source")
    lines.append("")
    if report.source_metrics:
        lines.append(
            "| Source | Type | Seen | Emitted | Rejected | Accepted | Weak | "
            "Noise | Accept Rate | Noise Rate | Dups | Missing URL | "
            "Placeholder URL | URL OK | Clusters | Opportunities |"
        )
        lines.append(
            "|--------|------|------|---------|----------|----------|------|"
            "-------|-------------|------------|------|-------------|"
            "----------------|--------|----------|---------------|"
        )
        for m in report.source_metrics:
            url_ok = "PASS" if m.source_url_validation_passed else "FAIL"
            lines.append(
                f"| {m.source_id} | {m.source_type} | {m.records_seen} | "
                f"{m.records_emitted} | {m.records_rejected} | "
                f"{m.accepted_signal_count} | {m.weak_signal_count} | "
                f"{m.noise_signal_count} | {m.accepted_rate} | "
                f"{m.noise_rate} | {m.duplicate_count} | "
                f"{m.missing_url_count} | {m.placeholder_url_count} | "
                f"{url_ok} | {m.cluster_contribution_count} | "
                f"{m.opportunity_contribution_count} |"
            )
    else:
        lines.append("_No source metrics available._")
    lines.append("")

    # Accepted / weak / noise summary
    lines.append("## Signal Classification Summary")
    lines.append("")
    lines.append(f"- **Accepted**: {report.accepted_signal_total}")
    lines.append(f"- **Weak**: {report.weak_signal_total}")
    lines.append(f"- **Noise**: {report.noise_signal_total}")
    lines.append("")

    # Top pain clusters
    lines.append("## Top Pain Clusters")
    lines.append("")
    if report.top_pain_clusters:
        for i, pc in enumerate(report.top_pain_clusters, 1):
            lines.append(f"### {i}. {pc['cluster_id']}")
            lines.append("")
            lines.append(f"- **Pain Pattern**: {pc['pain_pattern']}")
            lines.append(f"- **Actor**: {pc['actor']}")
            lines.append(f"- **Workflow**: {pc['workflow']}")
            lines.append(f"- **Object**: {pc['object']}")
            lines.append(f"- **Overall Score**: {pc['overall_score']}")
            lines.append(f"- **Recurrence**: {pc['recurrence']}")
            lines.append(f"- **Source Diversity**: {pc['source_diversity']}")
            lines.append(f"- **Business Relevance**: {pc['business_relevance']}")
            lines.append(f"- **Noise Risk**: {pc['noise_risk']}")
            lines.append(f"- **Evidence Count**: {pc['source_evidence_count']}")
            lines.append(f"- **Sources**: {', '.join(pc['source_ids'])}")
            lines.append(f"- **Status**: {pc['status']}")
            lines.append(f"- **Tier**: {pc['recommended_tier']}")
            lines.append("")
    else:
        lines.append("_No pain clusters formed._")
    lines.append("")

    # Opportunity candidates
    lines.append("## Opportunity Candidates")
    lines.append("")
    if report.opportunity_candidates:
        for oc in report.opportunity_candidates:
            lines.append(f"### {oc['opportunity_id']}")
            lines.append("")
            lines.append(f"- **Source Cluster**: `{oc['source_pain_cluster_id']}`")
            lines.append(f"- **Actor / ICP**: {oc['actor_or_icp']}")
            lines.append(f"- **Problem Statement**: {oc['problem_statement']}")
            lines.append(f"- **Evidence Summary**: {oc['evidence_summary']}")
            lines.append(f"- **Score**: {oc['score']}")
            lines.append(f"- **Uncertainty**: {oc['uncertainty']}")
            lines.append(
                f"- **Suggested Validation**: {oc['suggested_validation_action']}"
            )
            lines.append(f"- **Review Status**: {oc['founder_review_status']}")
            lines.append("")
    else:
        lines.append("_No opportunity candidates._")
    lines.append("")

    # Noise analysis
    lines.append("## Noise Analysis")
    lines.append("")
    if report.main_noise_categories:
        lines.append("| Category | Count | Source |")
        lines.append("|----------|-------|--------|")
        for nc in report.main_noise_categories:
            lines.append(f"| {nc.category} | {nc.count} | {nc.source_id} |")
    else:
        lines.append("_No noise categories detected._")
    lines.append("")

    # Founder review queue
    lines.append("## Founder Review Queue")
    lines.append("")
    fdn = report.founder_decisions_needed
    lines.append(f"- **Clusters awaiting review**: {fdn.get('clusters_awaiting_review', 0)}")
    lines.append(
        f"- **Opportunity candidates awaiting review**: "
        f"{fdn.get('opportunity_candidates_awaiting_review', 0)}"
    )
    lines.append(f"- **Total pending decisions**: {fdn.get('total_pending_decisions', 0)}")
    lines.append("")

    # Suggested validation actions
    lines.append("## Suggested Validation Actions")
    lines.append("")
    if report.next_validation_actions:
        for action in report.next_validation_actions:
            lines.append(f"- {action}")
    else:
        lines.append("_No actions suggested._")
    lines.append("")

    # Risks / caveats
    lines.append("## Risks and Caveats")
    lines.append("")
    if report.warnings:
        for w in report.warnings:
            lines.append(f"- WARNING: {w}")
    if report.errors:
        for e in report.errors:
            lines.append(f"- ERROR: {e}")
    if not report.warnings and not report.errors:
        lines.append("- No warnings or errors.")
    lines.append("")
    lines.append("This report is generated from deterministic pipeline data. ")
    lines.append("Small sample sizes and limited source scope (HN + GitHub Issues) ")
    lines.append("are inherent limitations of the operational discovery pilot.")
    lines.append("")

    # Traceability
    lines.append("## Traceability")
    lines.append("")
    ts = report.traceability_summary
    lines.append(f"- **Total Records**: {ts.get('total_records', 0)}")
    lines.append(
        f"- **Missing Source URL**: {ts.get('records_missing_source_url', 0)}"
    )
    lines.append(f"- **Placeholder URL**: {ts.get('placeholder_url_count', 0)}")
    lines.append(
        f"- **Validation Passed**: "
        f"{str(ts.get('source_url_validation_passed', False)).lower()}"
    )
    lines.append(
        f"- **Clusters with All URLs**: "
        f"{ts.get('clusters_with_all_evidence_urls', 0)}"
    )
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Report {report.report_id} -- generated by OOS Source Quality Report*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation entrypoint
# ---------------------------------------------------------------------------


def validate_source_quality_report(
    report: SourceQualityReport,
) -> SourceQualityReportValidationResult:
    """Validate a SourceQualityReport and return structured result."""
    errors: list[str] = []
    warnings: list[str] = []

    # Fail: empty source_metrics
    if not report.source_metrics:
        errors.append("source_metrics is empty")

    # Fail: missing source_id
    for m in report.source_metrics:
        if not m.source_id:
            errors.append("source metric has empty source_id")

    # Fail: traceability not passed
    ts = report.traceability_summary
    if not ts.get("source_url_validation_passed", False):
        errors.append("source_url traceability validation failed")

    # Warn: zero clusters
    if report.pain_cluster_count == 0:
        warnings.append("zero pain clusters")

    # Warn: high noise
    for m in report.source_metrics:
        if m.noise_rate > 0.60:
            warnings.append(
                f"high noise rate ({m.noise_rate}) for source {m.source_id}"
            )

    # Warn: low source diversity
    if report.top_pain_clusters:
        all_single = all(
            pc.get("source_diversity", 1) == 1
            for pc in report.top_pain_clusters
        )
        if all_single:
            warnings.append("all clusters are single-source (low diversity)")

    # Warn: no opportunity candidates
    if report.opportunity_candidate_count == 0:
        warnings.append("no opportunity candidates")

    # Warn: pending decisions without review package
    fdn = report.founder_decisions_needed
    if fdn.get("total_pending_decisions", 0) > 0 and report.opportunity_candidate_count == 0:
        warnings.append("founder decisions needed but no review package exists")

    is_valid = len(errors) == 0
    return SourceQualityReportValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
    )
