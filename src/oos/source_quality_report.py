from __future__ import annotations

"""Source Quality Report — deterministic source performance and quality metrics.

Implements the Source Quality Report specified in
docs/contracts/operational_discovery_pilot_run_contract.md Sections 10–11.

Accepts plain deterministic inputs (no live sources, no APIs, no LLM).

v2.14 item 7: Source Quality Report Contradiction Fix.
Adds report-level quality status, per-source contradiction detection,
and separates traceability/scope/classification/evidence-quality dimensions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .noise_classifier import (
    ACCEPTED,
    NOISE as NC_NOISE,
    WEAK,
    classify_noise_for_evidence,
)
from .pain_cluster_dedupe import (
    normalize_source_id,
    normalize_source_type,
    SOURCE_ID_NORMALIZATION,
)
from .pain_cluster import PainCluster

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.1.0"
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
# Quality thresholds (v2.14 item 7)
# ---------------------------------------------------------------------------

# Classification health thresholds
NOISE_RATE_FAILING = 0.50
NOISE_RATE_PROBLEMATIC = 0.20
WEAK_RATE_PROBLEMATIC = 0.70
WEAK_RATE_CAUTION = 0.20
FLAGGED_RATE_CAUTION = 0.20
FLAGGED_RATE_LOW = 0.10

# Per-source contradiction thresholds
ACCEPTED_RATE_HIGH = 0.80
FLAGGED_RATE_HIGH = 0.20

# Quality-risk flags that trigger contradiction warnings
CONTRADICTION_SENSITIVE_FLAGS: frozenset[str] = frozenset({
    "requires_manual_review",
    "low_confidence_extraction",
    "suspected_self_promo",
    "generic_language",
    "low_text_context",
    "launch_hype",
    "stale_issue",
    "unclear_actor",
    "unclear_workflow",
    "unclear_buyer",
    "no_business_cost",
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
    """Per-source quality metrics (contract Section 11).

    v2.14 item 7: added weak_rate, flagged_record_count, flagged_record_rate,
    source_quality_warnings, contradiction_warnings.
    """

    source_id: str
    source_type: str
    records_seen: int = 0
    records_emitted: int = 0
    records_rejected: int = 0
    accepted_signal_count: int = 0
    weak_signal_count: int = 0
    noise_signal_count: int = 0
    accepted_rate: float = 0.0
    weak_rate: float = 0.0
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
    # v2.14 item 7 additions:
    flagged_record_count: int = 0
    flagged_record_rate: float = 0.0
    source_quality_warnings: list[str] = field(default_factory=list)
    contradiction_warnings: list[str] = field(default_factory=list)

    def recompute_rates(self) -> None:
        total_classified = (
            self.accepted_signal_count
            + self.weak_signal_count
            + self.noise_signal_count
        )
        self.accepted_rate = _safe_rate(self.accepted_signal_count, total_classified)
        self.weak_rate = _safe_rate(self.weak_signal_count, total_classified)
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
            "weak_rate": self.weak_rate,
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
            "flagged_record_count": self.flagged_record_count,
            "flagged_record_rate": self.flagged_record_rate,
            "source_quality_warnings": list(self.source_quality_warnings),
            "contradiction_warnings": list(self.contradiction_warnings),
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
            weak_rate=float(data.get("weak_rate", data.get("weak_count", 0.0))),
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
            # v2.14 item 7 additions — default safely for old data
            flagged_record_count=int(data.get("flagged_record_count", 0)),
            flagged_record_rate=float(data.get("flagged_record_rate", 0.0)),
            source_quality_warnings=list(data.get("source_quality_warnings", [])),
            contradiction_warnings=list(data.get("contradiction_warnings", [])),
        )


@dataclass
class SourceQualityHealth:
    """Report-level quality status (v2.14 item 7).

    Separates distinct quality dimensions so the report doesn't conflate
    traceability cleanliness with classification or evidence quality.
    """

    traceability_status: str = "clean"        # clean | failing
    source_scope_status: str = "clean"         # clean | failing
    classification_health: str = "clean"       # clean | caution | problematic | failing
    evidence_quality_status: str = "clean"     # clean | caution | noisy

    # Aggregate counts and rates
    accepted_count: int = 0
    weak_count: int = 0
    noise_count: int = 0
    accepted_rate: float = 0.0
    weak_rate: float = 0.0
    noise_rate: float = 0.0
    flagged_record_count: int = 0
    flagged_record_rate: float = 0.0

    # Dominant quality flags across all sources
    dominant_quality_flags: list[str] = field(default_factory=list)
    # Source IDs with high weak/noise evidence
    sources_with_high_weak_or_noise: list[str] = field(default_factory=list)

    # Contradiction warnings detected across the report
    contradiction_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "traceability_status": self.traceability_status,
            "source_scope_status": self.source_scope_status,
            "classification_health": self.classification_health,
            "evidence_quality_status": self.evidence_quality_status,
            "accepted_count": self.accepted_count,
            "weak_count": self.weak_count,
            "noise_count": self.noise_count,
            "accepted_rate": self.accepted_rate,
            "weak_rate": self.weak_rate,
            "noise_rate": self.noise_rate,
            "flagged_record_count": self.flagged_record_count,
            "flagged_record_rate": self.flagged_record_rate,
            "dominant_quality_flags": list(self.dominant_quality_flags),
            "sources_with_high_weak_or_noise": list(self.sources_with_high_weak_or_noise),
            "contradiction_warnings": list(self.contradiction_warnings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceQualityHealth:
        return cls(
            traceability_status=str(data.get("traceability_status", "clean")),
            source_scope_status=str(data.get("source_scope_status", "clean")),
            classification_health=str(data.get("classification_health", "clean")),
            evidence_quality_status=str(data.get("evidence_quality_status", "clean")),
            accepted_count=int(data.get("accepted_count", 0)),
            weak_count=int(data.get("weak_count", 0)),
            noise_count=int(data.get("noise_count", 0)),
            accepted_rate=float(data.get("accepted_rate", 0.0)),
            weak_rate=float(data.get("weak_rate", 0.0)),
            noise_rate=float(data.get("noise_rate", 0.0)),
            flagged_record_count=int(data.get("flagged_record_count", 0)),
            flagged_record_rate=float(data.get("flagged_record_rate", 0.0)),
            dominant_quality_flags=list(data.get("dominant_quality_flags", [])),
            sources_with_high_weak_or_noise=list(data.get("sources_with_high_weak_or_noise", [])),
            contradiction_warnings=list(data.get("contradiction_warnings", [])),
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
    """Structured source quality report (contract Section 10).

    v2.14 item 7: added quality_health field for report-level quality status
    that separates traceability/scope/classification/evidence-quality dimensions.
    """

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
    # v2.14 item 7: report-level quality health
    quality_health: SourceQualityHealth = field(default_factory=SourceQualityHealth)

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
            "quality_health": self.quality_health.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceQualityReport:
        qh_data = data.get("quality_health", None)
        quality_health = SourceQualityHealth.from_dict(qh_data) if qh_data else SourceQualityHealth()
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
            quality_health=quality_health,
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

    # ---- Quality Health (v2.14 item 7) ----
    quality_health = _compute_quality_health(
        source_metrics=source_metrics,
        evidence_items=evidence_items,
        traceability_summary=traceability_summary,
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
        quality_health=quality_health,
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
    """Build per-source metrics (v2.14 item 7 updated with flagged counts + warnings)."""

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

    # Build evidence lookup by evidence_id so the noise classifier can
    # access title/body/excerpt from the original evidence item.
    evidence_by_id: dict[str, dict[str, Any]] = {}
    for ev in evidence_items:
        eid = str(ev.get("evidence_id", "") or "")
        if eid:
            evidence_by_id[eid] = ev

    # Signal classification — infer from classification field + noise classifier
    accepted = weak = noise = 0
    for sig in source_signals:
        classification = str(sig.get("classification", "") or "").lower()
        sig_type = str(sig.get("signal_type", "") or "").lower()

        if classification in ("noise",):
            noise += 1
            continue
        elif classification in ("needs_human_review",) or sig_type in ("needs_human_review",):
            weak += 1
            continue

        # Merge signal flags with evidence fields so the classifier sees
        # title, body, and excerpt from the original evidence item.
        sig_eid = str(sig.get("evidence_id", "") or "")
        ev = evidence_by_id.get(sig_eid, {})
        merged = {
            "quality_flags": sig.get("quality_flags", []) or [],
            "evidence_kind": str(ev.get("evidence_kind", "") or ""),
            "title": str(ev.get("title", "") or ""),
            "body": str(ev.get("body", "") or ""),
            "excerpt": str(ev.get("excerpt", "") or ""),
            "source_url": str(ev.get("source_url", "") or ""),
        }

        nc_result = classify_noise_for_evidence(merged)
        if nc_result == NC_NOISE:
            noise += 1
        elif nc_result == WEAK:
            weak += 1
        else:
            if classification in ("pain_signal_candidate", "workaround_signal_candidate",
                                  "buying_intent_candidate", "competitor_weakness_candidate",
                                  "trend_trigger_candidate"):
                accepted += 1
            elif sig_type in ("pain_signal", "workaround", "buying_intent",
                            "competitor_weakness", "trend_trigger"):
                accepted += 1
            else:
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
        sid_normalized = normalize_source_id(source_id)
        contributed = False
        for e in pc.get("source_evidence_list", []):
            e_sid = normalize_source_id(str(e.get("source_id", "") or ""))
            if e_sid == sid_normalized:
                contributed = True
                break
        if contributed:
            cluster_contribution_count += 1
            cluster_id = pc.get("cluster_id", "")
            for oc in opp_candidates:
                oc_cluster = str(oc.get("source_pain_cluster_id", "") or "")
                if oc_cluster == cluster_id:
                    opportunity_contribution_count += 1

    source_diversity_contribution = cluster_contribution_count

    # Quality flag counts
    quality_flag_counts: dict[str, int] = {}
    for ev in source_evidence:
        for flag in ev.get("quality_flags", []) or []:
            flag_key = str(flag).lower().replace(" ", "_")
            quality_flag_counts[flag_key] = quality_flag_counts.get(flag_key, 0) + 1

    rejection_reasons = list(local_summary.get("rejection_reasons", []) or [])

    founder_promote = int(fd_counts.get("promote", 0))
    founder_kill = int(fd_counts.get("kill", 0))
    founder_needs_more = int(fd_counts.get("needs_more_evidence", 0))

    # v2.14 item 7: flagged record counting
    flagged_record_count = 0
    for sig in source_signals:
        flags = sig.get("quality_flags", []) or []
        if flags:
            flagged_record_count += 1

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
        flagged_record_count=flagged_record_count,
    )
    metrics.recompute_rates()
    metrics.flagged_record_rate = _safe_rate(flagged_record_count, len(source_signals))

    # v2.14 item 7: per-source quality + contradiction warnings
    _compute_source_quality_warnings(metrics, source_signals)

    return metrics


def _compute_source_quality_warnings(
    metrics: SourceQualityMetrics,
    source_signals: list[dict[str, Any]],
) -> None:
    """Compute per-source quality and contradiction warnings (v2.14 item 7)."""
    source_id = metrics.source_id or "unknown"
    total = metrics.accepted_signal_count + metrics.weak_signal_count + metrics.noise_signal_count

    if total == 0:
        return

    # Quality warnings based on evidence health
    if metrics.noise_rate >= NOISE_RATE_FAILING:
        metrics.source_quality_warnings.append(
            f"{source_id} noise rate {metrics.noise_rate:.2f} >= {NOISE_RATE_FAILING}; "
            f"evidence quality is failing."
        )
    elif metrics.noise_rate >= NOISE_RATE_PROBLEMATIC:
        metrics.source_quality_warnings.append(
            f"{source_id} noise rate {metrics.noise_rate:.2f} >= {NOISE_RATE_PROBLEMATIC}; "
            f"evidence quality is problematic."
        )

    if metrics.weak_rate >= WEAK_RATE_PROBLEMATIC:
        metrics.source_quality_warnings.append(
            f"{source_id} weak rate {metrics.weak_rate:.2f} >= {WEAK_RATE_PROBLEMATIC}; "
            f"most evidence is unclassified or weakly classified."
        )
    elif metrics.weak_rate >= WEAK_RATE_CAUTION:
        metrics.source_quality_warnings.append(
            f"{source_id} weak rate {metrics.weak_rate:.2f} >= {WEAK_RATE_CAUTION}; "
            f"significant portion of evidence is weak."
        )

    if metrics.flagged_record_rate >= FLAGGED_RATE_CAUTION:
        metrics.source_quality_warnings.append(
            f"{source_id} flagged record rate {metrics.flagged_record_rate:.2f} >= "
            f"{FLAGGED_RATE_CAUTION}; many records carry quality flags."
        )

    # Contradiction detection
    _detect_per_source_contradictions(metrics, source_signals, source_id, total)


def _detect_per_source_contradictions(
    metrics: SourceQualityMetrics,
    source_signals: list[dict[str, Any]],
    source_id: str,
    total: int,
) -> None:
    """Detect per-source contradictions (v2.14 item 7)."""
    if total == 0:
        return

    # Contradiction 1: high accepted_rate but high flagged_record_rate
    if metrics.accepted_rate >= ACCEPTED_RATE_HIGH and metrics.flagged_record_rate >= FLAGGED_RATE_HIGH:
        metrics.contradiction_warnings.append(
            f"{source_id} has high accepted_rate ({metrics.accepted_rate:.2f}) but "
            f"high flagged_record_rate ({metrics.flagged_record_rate:.2f}); "
            f"treat as caution: accepted signals carry quality risk flags."
        )

    # Contradiction 2: noise/weak non-zero but accepted_rate looks clean
    if (metrics.noise_rate > 0.0 or metrics.weak_rate > 0.0) and metrics.accepted_rate >= ACCEPTED_RATE_HIGH:
        if metrics.noise_rate > 0.0 and metrics.weak_rate > 0.0:
            metrics.contradiction_warnings.append(
                f"{source_id}: accepted_rate is high ({metrics.accepted_rate:.2f}) but "
                f"noise_rate={metrics.noise_rate:.2f} and weak_rate={metrics.weak_rate:.2f} "
                f"are non-zero. 0% noise does not imply clean source quality."
            )
        elif metrics.noise_rate > 0.0:
            metrics.contradiction_warnings.append(
                f"{source_id}: accepted_rate is high ({metrics.accepted_rate:.2f}) but "
                f"noise_rate={metrics.noise_rate:.2f} is non-zero."
            )
        elif metrics.weak_rate > 0.0:
            metrics.contradiction_warnings.append(
                f"{source_id}: accepted_rate is high ({metrics.accepted_rate:.2f}) but "
                f"weak_rate={metrics.weak_rate:.2f} is non-zero."
            )

    # Contradiction 3: source_url validation clean but classification/evidence noisy
    if metrics.source_url_validation_passed:
        if metrics.noise_rate >= NOISE_RATE_PROBLEMATIC or metrics.weak_rate >= WEAK_RATE_CAUTION:
            metrics.contradiction_warnings.append(
                f"{source_id}: source_url validation is clean (PASS) but evidence quality "
                f"is weak/noisy (noise_rate={metrics.noise_rate:.2f}, "
                f"weak_rate={metrics.weak_rate:.2f}). Source traceability does not imply "
                f"classification quality."
            )

    # Contradiction 4: source contributes clusters but mostly weak/noisy evidence
    if metrics.cluster_contribution_count > 0:
        if metrics.accepted_signal_count == 0:
            metrics.contradiction_warnings.append(
                f"{source_id} contributes to {metrics.cluster_contribution_count} "
                f"clusters but has zero accepted signals (all weak/noise)."
            )
        elif metrics.accepted_rate <= 0.5:
            metrics.contradiction_warnings.append(
                f"{source_id} contributes to {metrics.cluster_contribution_count} "
                f"clusters but accepted_rate is only {metrics.accepted_rate:.2f}; "
                f"cluster evidence is mostly weak/noisy."
            )

    # Contradiction 5: many quality-risk flags
    sensitive_count = sum(
        metrics.quality_flag_counts.get(f, 0)
        for f in CONTRADICTION_SENSITIVE_FLAGS
        if f in metrics.quality_flag_counts
    )
    if sensitive_count >= 3:
        metrics.contradiction_warnings.append(
            f"{source_id} has {sensitive_count} quality-risk flags "
            f"(requires_manual_review, low_confidence, self_promo, etc.); "
            f"treat as caution even if overall acceptance looks clean."
        )


# ---------------------------------------------------------------------------
# Quality Health (v2.14 item 7)
# ---------------------------------------------------------------------------


def _compute_quality_health(
    *,
    source_metrics: list[SourceQualityMetrics],
    evidence_items: list[dict[str, Any]],
    traceability_summary: dict[str, Any],
) -> SourceQualityHealth:
    """Compute report-level quality health status (v2.14 item 7)."""
    # Traceability
    trace_pass = traceability_summary.get("source_url_validation_passed", False)
    traceability_status = "clean" if trace_pass else "failing"

    # Source scope — check for scope violations from evidence
    scope_violations = 0
    for ev in evidence_items:
        flags = ev.get("quality_flags", []) or []
        if "source_scope_violation" in [str(f).lower().replace(" ", "_") for f in flags]:
            scope_violations += 1
    source_scope_status = "failing" if scope_violations > 0 else "clean"

    # Aggregate classification counts
    accepted_total = sum(m.accepted_signal_count for m in source_metrics)
    weak_total = sum(m.weak_signal_count for m in source_metrics)
    noise_total = sum(m.noise_signal_count for m in source_metrics)
    total_classified = accepted_total + weak_total + noise_total

    accepted_rate = _safe_rate(accepted_total, total_classified)
    weak_rate = _safe_rate(weak_total, total_classified)
    noise_rate = _safe_rate(noise_total, total_classified)

    flagged_total = sum(m.flagged_record_count for m in source_metrics)
    flagged_rate = _safe_rate(flagged_total, total_classified)

    # Classification health
    if noise_rate >= NOISE_RATE_FAILING:
        classification_health = "failing"
    elif noise_rate >= NOISE_RATE_PROBLEMATIC or weak_rate >= WEAK_RATE_PROBLEMATIC:
        classification_health = "problematic"
    elif weak_rate >= WEAK_RATE_CAUTION or flagged_rate >= FLAGGED_RATE_CAUTION:
        classification_health = "caution"
    else:
        classification_health = "clean"

    # Evidence quality status
    if noise_rate >= NOISE_RATE_PROBLEMATIC:
        evidence_quality_status = "noisy"
    elif weak_rate >= WEAK_RATE_CAUTION or flagged_rate >= FLAGGED_RATE_CAUTION:
        evidence_quality_status = "caution"
    else:
        evidence_quality_status = "clean"

    # Dominant quality flags
    all_flag_counts: dict[str, int] = {}
    for m in source_metrics:
        for f, c in m.quality_flag_counts.items():
            all_flag_counts[f] = all_flag_counts.get(f, 0) + c
    sorted_flags = sorted(all_flag_counts.items(), key=lambda x: (-x[1], x[0]))
    dominant_quality_flags = [f for f, _ in sorted_flags[:5]]

    # Sources with high weak/noise
    sources_with_high = []
    for m in source_metrics:
        if m.noise_rate >= NOISE_RATE_PROBLEMATIC or m.weak_rate >= WEAK_RATE_CAUTION:
            sources_with_high.append(m.source_id)

    # Report-level contradiction warnings (from per-source)
    contradiction_warnings: list[str] = []
    for m in source_metrics:
        contradiction_warnings.extend(m.contradiction_warnings)

    # Additional report-level contradiction: traceability clean but classification failing
    if traceability_status == "clean" and classification_health in ("problematic", "failing"):
        contradiction_warnings.append(
            f"Traceability is clean ({traceability_status}) but classification health "
            f"is {classification_health} (noise_rate={noise_rate:.2f}, "
            f"weak_rate={weak_rate:.2f}). Source URL validity does not guarantee "
            f"evidence quality."
        )

    return SourceQualityHealth(
        traceability_status=traceability_status,
        source_scope_status=source_scope_status,
        classification_health=classification_health,
        evidence_quality_status=evidence_quality_status,
        accepted_count=accepted_total,
        weak_count=weak_total,
        noise_count=noise_total,
        accepted_rate=accepted_rate,
        weak_rate=weak_rate,
        noise_rate=noise_rate,
        flagged_record_count=flagged_total,
        flagged_record_rate=flagged_rate,
        dominant_quality_flags=dominant_quality_flags,
        sources_with_high_weak_or_noise=sources_with_high,
        contradiction_warnings=contradiction_warnings,
    )


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
        "opportunity_candidates_with_traceability": 0,
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

    if not source_metrics:
        errors.append("no source metrics computed")

    for m in source_metrics:
        if not m.source_id:
            errors.append("source metric missing source_id")

    if not traceability_summary.get("source_url_validation_passed", False):
        failures = traceability_summary.get("failures", [])
        for f in failures:
            errors.append(f"traceability failure: {f}")

    if len(clusters) == 0:
        warnings.append("zero pain clusters formed")

    for m in source_metrics:
        if m.noise_rate > 0.60:
            warnings.append(
                f"high noise rate for {m.source_id}: {m.noise_rate}"
            )

    if clusters:
        all_single_source = all(
            int(pc.get("source_diversity", 1)) == 1
            for pc in clusters
        )
        if all_single_source:
            warnings.append("all clusters are single-source (low source diversity)")

    if not opp_candidates:
        warnings.append("no opportunity candidates supplied")

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

    for m in source_metrics:
        if m.noise_rate > 0.60:
            actions.append(
                f"High noise rate ({m.noise_rate}) for {m.source_id}. "
                f"Tune noise filters and review quality flags."
            )

    all_single = all(
        int(pc.get("source_diversity", 1)) == 1
        for pc in clusters
    )
    if all_single and len(clusters) > 0:
        actions.append(
            "Low source diversity: all clusters are single-source. "
            "Adjust source mix or queries to enable cross-source validation."
        )

    if not traceability_summary.get("source_url_validation_passed", False):
        actions.append(
            "Traceability failures detected. Fix source_url handling "
            "before founder review."
        )

    if clusters and not opp_candidates:
        actions.append(
            "Clusters exist but no opportunity candidates. "
            "Consider founder review or collecting more evidence."
        )

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

    v2.14 item 7: added Executive Summary statuses, quality health table,
    quality flags table, per-source quality warnings, contradiction warnings.

    Args:
        report: The SourceQualityReport to render.
        output_mode: 'ascii_safe' (default) or 'utf8'.

    Returns:
        Markdown string.
    """
    lines: list[str] = []
    qh = report.quality_health

    # Title
    lines.append("# Source Quality Report")
    lines.append("")
    lines.append(f"- **Report ID**: `{report.report_id}`")
    lines.append(f"- **Discovery Run ID**: `{report.discovery_run_id}`")
    lines.append(f"- **Generated**: {report.created_at}")
    lines.append("")

    # Executive Summary with quality dimensions
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

    # Quality status table (v2.14 item 7)
    lines.append("### Quality Status")
    lines.append("")
    lines.append("| Dimension | Status |")
    lines.append("|-----------|--------|")
    lines.append(f"| Traceability | {qh.traceability_status} |")
    lines.append(f"| Source Scope | {qh.source_scope_status} |")
    lines.append(f"| Classification Health | {qh.classification_health} |")
    lines.append(f"| Evidence Quality | {qh.evidence_quality_status} |")
    lines.append("")

    # Quality risk summary (v2.14 item 7)
    lines.append("### Quality Risk Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Accepted | {qh.accepted_count} ({qh.accepted_rate:.2%}) |")
    lines.append(f"| Weak | {qh.weak_count} ({qh.weak_rate:.2%}) |")
    lines.append(f"| Noise | {qh.noise_count} ({qh.noise_rate:.2%}) |")
    lines.append(f"| Flagged Records | {qh.flagged_record_count} ({qh.flagged_record_rate:.2%}) |")
    lines.append(f"| Dominant Quality Flags | {', '.join(qh.dominant_quality_flags) if qh.dominant_quality_flags else 'none'} |")
    lines.append(f"| Sources with High Weak/Noise | {', '.join(qh.sources_with_high_weak_or_noise) if qh.sources_with_high_weak_or_noise else 'none'} |")
    lines.append("")

    # Source quality table
    lines.append("## Source Quality by Source")
    lines.append("")
    if report.source_metrics:
        lines.append(
            "| Source | Type | Seen | Emitted | Rejected | Accepted | Weak | "
            "Noise | Accept Rate | Weak Rate | Noise Rate | Dups | Missing URL | "
            "Placeholder URL | URL OK | Flagged | Clusters | Opportunities |"
        )
        lines.append(
            "|--------|------|------|---------|----------|----------|------|"
            "-------|-------------|-----------|------------|------|-------------|"
            "----------------|--------|---------|----------|---------------|"
        )
        for m in report.source_metrics:
            url_ok = "PASS" if m.source_url_validation_passed else "FAIL"
            lines.append(
                f"| {m.source_id} | {m.source_type} | {m.records_seen} | "
                f"{m.records_emitted} | {m.records_rejected} | "
                f"{m.accepted_signal_count} | {m.weak_signal_count} | "
                f"{m.noise_signal_count} | {m.accepted_rate} | "
                f"{m.weak_rate} | {m.noise_rate} | {m.duplicate_count} | "
                f"{m.missing_url_count} | {m.placeholder_url_count} | "
                f"{url_ok} | {m.flagged_record_count} | "
                f"{m.cluster_contribution_count} | "
                f"{m.opportunity_contribution_count} |"
            )
    else:
        lines.append("_No source metrics available._")
    lines.append("")

    # Signal Classification Summary
    lines.append("## Signal Classification Summary")
    lines.append("")
    lines.append("| Metric | Count | Rate |")
    lines.append("|--------|-------|------|")
    total_sig = report.accepted_signal_total + report.weak_signal_total + report.noise_signal_total
    lines.append(f"| Accepted | {report.accepted_signal_total} | {_safe_rate(report.accepted_signal_total, total_sig):.2%} |")
    lines.append(f"| Weak | {report.weak_signal_total} | {_safe_rate(report.weak_signal_total, total_sig):.2%} |")
    lines.append(f"| Noise | {report.noise_signal_total} | {_safe_rate(report.noise_signal_total, total_sig):.2%} |")
    lines.append(f"| **Total** | **{total_sig}** | |")
    lines.append("")

    # Quality Flags table (v2.14 item 7)
    lines.append("## Quality Flags")
    lines.append("")
    all_flags: dict[str, int] = {}
    for m in report.source_metrics:
        for f, c in m.quality_flag_counts.items():
            all_flags[f] = all_flags.get(f, 0) + c
    if all_flags:
        lines.append("| Flag | Count |")
        lines.append("|------|-------|")
        sorted_flags = sorted(all_flags.items(), key=lambda x: (-x[1], x[0]))
        for flag, count in sorted_flags:
            lines.append(f"| {flag} | {count} |")
    else:
        lines.append("_No quality flags detected._")
    lines.append("")

    # Per-source quality warnings (v2.14 item 7)
    has_source_warnings = any(
        m.source_quality_warnings for m in report.source_metrics
    )
    if has_source_warnings:
        lines.append("## Per-Source Quality Warnings")
        lines.append("")
        for m in report.source_metrics:
            if m.source_quality_warnings:
                lines.append(f"### {m.source_id}")
                lines.append("")
                for w in m.source_quality_warnings:
                    lines.append(f"- {w}")
                lines.append("")
    else:
        lines.append("## Per-Source Quality Warnings")
        lines.append("")
        lines.append("_No per-source quality warnings._")
        lines.append("")

    # Contradiction warnings (v2.14 item 7)
    lines.append("## Contradiction Warnings")
    lines.append("")
    if qh.contradiction_warnings:
        for w in qh.contradiction_warnings:
            lines.append(f"- {w}")
    else:
        lines.append("_No contradiction warnings detected. Report is internally consistent._")
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
        lines.append(
            "_Note: opportunity candidate counts reflect candidates available at SQR build time. "
            "Deterministic synthesis timing and hypothesis generation may affect when candidates appear._"
        )
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
    lines.append("**Quality dimensions are separate:**")
    lines.append("- **Traceability clean** does not imply classification quality.")
    lines.append("- **Source scope clean** does not imply evidence quality.")
    lines.append("- **High accepted_rate** does not mean evidence is clean if weak/noise rates are non-zero.")
    lines.append("- **0% noise** does not imply clean source quality when flagged or weak records exist.")
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

    if not report.source_metrics:
        errors.append("source_metrics is empty")

    for m in report.source_metrics:
        if not m.source_id:
            errors.append("source metric has empty source_id")

    ts = report.traceability_summary
    if not ts.get("source_url_validation_passed", False):
        errors.append("source_url traceability validation failed")

    if report.pain_cluster_count == 0:
        warnings.append("zero pain clusters")

    for m in report.source_metrics:
        if m.noise_rate > 0.60:
            warnings.append(
                f"high noise rate ({m.noise_rate}) for source {m.source_id}"
            )

    if report.top_pain_clusters:
        all_single = all(
            pc.get("source_diversity", 1) == 1
            for pc in report.top_pain_clusters
        )
        if all_single:
            warnings.append("all clusters are single-source (low diversity)")

    if report.opportunity_candidate_count == 0:
        warnings.append("no opportunity candidates")

    fdn = report.founder_decisions_needed
    if fdn.get("total_pending_decisions", 0) > 0 and report.opportunity_candidate_count == 0:
        warnings.append("founder decisions needed but no review package exists")

    is_valid = len(errors) == 0
    return SourceQualityReportValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
    )
