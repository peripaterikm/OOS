from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Local validators (duplicated from models.py to avoid circular imports)
# ---------------------------------------------------------------------------


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_list(value: Any, field_name: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCORING_MODEL_VERSION = "pain_cluster_scoring_v1_pilot"

ALLOWED_STATUSES: frozenset[str] = frozenset(
    {
        "new",
        "accepted",
        "weak",
        "noise",
        "needs_more_evidence",
        "promoted_to_opportunity",
        "parked",
        "killed",
    }
)

ALLOWED_CONTRIBUTION_TYPES: frozenset[str] = frozenset(
    {
        "primary_pain",
        "supporting_pain",
        "workaround_description",
        "cost_evidence",
        "context_only",
    }
)

SOURCE_RELIABILITY_PRIORS: dict[str, float] = {
    "github_issues": 0.78,
    "hacker_news": 0.72,
    "stack_exchange": 0.62,
}

SOURCE_TYPE_RELIABILITY_FALLBACK: dict[str, float] = {
    "issue_tracker": 0.78,
    "discussion": 0.72,
    "qa": 0.62,
}

# ---------------------------------------------------------------------------
# SourceEvidenceEntry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceEvidenceEntry:
    """A single evidence item supporting a PainCluster (contract Section 6.1)."""

    evidence_id: str
    source_id: str
    source_type: str
    source_url: str
    evidence_kind: str
    title: str
    excerpt: str
    created_at: str
    fetched_at: str
    contribution_to_cluster: str
    signal_id: str | None = None
    quality_flags: list[str] = field(default_factory=list)

    def validate(self) -> None:
        _require_non_empty(self.evidence_id, "SourceEvidenceEntry.evidence_id")
        _require_non_empty(self.source_id, "SourceEvidenceEntry.source_id")
        _require_non_empty(self.source_type, "SourceEvidenceEntry.source_type")
        _require_non_empty(self.source_url, "SourceEvidenceEntry.source_url")
        _require_non_empty(self.evidence_kind, "SourceEvidenceEntry.evidence_kind")
        _require_non_empty(self.title, "SourceEvidenceEntry.title")
        _require_non_empty(self.excerpt, "SourceEvidenceEntry.excerpt")
        _require_non_empty(self.created_at, "SourceEvidenceEntry.created_at")
        _require_non_empty(self.fetched_at, "SourceEvidenceEntry.fetched_at")
        _require_non_empty(self.contribution_to_cluster, "SourceEvidenceEntry.contribution_to_cluster")

        if self.contribution_to_cluster not in ALLOWED_CONTRIBUTION_TYPES:
            raise ValueError(
                f"SourceEvidenceEntry.contribution_to_cluster must be one of "
                f"{sorted(ALLOWED_CONTRIBUTION_TYPES)}"
            )

        # Note: http(s):// scheme validation is handled by validate_pain_cluster
        # as VF7/VF8/VF9 fail rules (contract Section 19.1).

        if self.excerpt and len(self.excerpt) > 500:
            raise ValueError(
                f"SourceEvidenceEntry.excerpt must be <= 500 characters"
            )

        if self.signal_id is not None and not isinstance(self.signal_id, str):
            raise ValueError("SourceEvidenceEntry.signal_id must be a string or None")

        _require_list(self.quality_flags, "SourceEvidenceEntry.quality_flags")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceEvidenceEntry:
        entry = cls(**data)
        entry.validate()
        return entry


# ---------------------------------------------------------------------------
# PainClusterScoring
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PainClusterScoring:
    """Full scoring breakdown for a PainCluster (contract Section 3.2.18)."""

    overall: float
    pain_explicitness: float
    recurrence: float
    business_cost: float
    icp_fit: float
    source_reliability: float
    freshness: float
    actionability: float
    noise_risk: float
    scoring_model_version: str = SCORING_MODEL_VERSION
    computed_at: str = field(default_factory=_iso_utc_now_seconds)

    def validate(self) -> None:
        components: dict[str, float] = {
            "overall": self.overall,
            "pain_explicitness": self.pain_explicitness,
            "recurrence": self.recurrence,
            "business_cost": self.business_cost,
            "icp_fit": self.icp_fit,
            "source_reliability": self.source_reliability,
            "freshness": self.freshness,
            "actionability": self.actionability,
            "noise_risk": self.noise_risk,
        }
        for name, value in components.items():
            if not isinstance(value, (int, float)) or not (0.0 <= float(value) <= 1.0):
                raise ValueError(
                    f"PainClusterScoring.{name} must be 0.0–1.0, got {value!r}"
                )

        _require_non_empty(self.scoring_model_version, "PainClusterScoring.scoring_model_version")
        _require_non_empty(self.computed_at, "PainClusterScoring.computed_at")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PainClusterScoring:
        scoring = cls(**data)
        scoring.validate()
        return scoring


# ---------------------------------------------------------------------------
# Default / zero scoring factory
# ---------------------------------------------------------------------------


def default_pain_cluster_scoring() -> PainClusterScoring:
    """Return a neutral-state scoring object for a newly created cluster.

    All components default to 0.5 (neutral) except recurrence (0.0)
    and noise_risk (0.0). The overall is computed from the formula so
    it remains internally consistent for validation.
    """
    pain_explicitness = 0.5
    recurrence = 0.0
    business_cost = 0.5
    icp_fit = 0.5
    source_reliability = 0.5
    freshness = 0.5
    actionability = 0.5
    noise_risk = 0.0

    overall = compute_overall_score(
        pain_explicitness=pain_explicitness,
        recurrence=recurrence,
        business_cost=business_cost,
        icp_fit=icp_fit,
        source_reliability=source_reliability,
        freshness=freshness,
        actionability=actionability,
        noise_risk=noise_risk,
    )

    return PainClusterScoring(
        overall=overall,
        pain_explicitness=pain_explicitness,
        recurrence=recurrence,
        business_cost=business_cost,
        icp_fit=icp_fit,
        source_reliability=source_reliability,
        freshness=freshness,
        actionability=actionability,
        noise_risk=noise_risk,
    )


# ---------------------------------------------------------------------------
# PainCluster
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PainCluster:
    """First-class artifact for cross-source pain consolidation (contract Section 3.1)."""

    cluster_id: str
    actor: str
    workflow: str
    object: str
    pain_verb: str
    pain_pattern: str
    source_evidence_list: list[SourceEvidenceEntry]
    source_diversity: int
    recurrence: int
    business_relevance: float
    noise_risk: float
    representative_quotes_or_excerpts: list[str]
    linked_candidate_signals: list[str]
    created_at: str
    updated_at: str
    status: str
    scoring: PainClusterScoring
    linked_opportunity_candidates: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def id(self) -> str:
        return self.cluster_id

    def validate(self) -> None:
        _require_non_empty(self.cluster_id, "PainCluster.cluster_id")
        _require_non_empty(self.actor, "PainCluster.actor")
        _require_non_empty(self.workflow, "PainCluster.workflow")
        _require_non_empty(self.object, "PainCluster.object")
        _require_non_empty(self.pain_verb, "PainCluster.pain_verb")
        _require_non_empty(self.pain_pattern, "PainCluster.pain_pattern")
        _require_non_empty(self.created_at, "PainCluster.created_at")
        _require_non_empty(self.updated_at, "PainCluster.updated_at")
        _require_non_empty(self.status, "PainCluster.status")

        if self.status not in ALLOWED_STATUSES:
            raise ValueError(
                f"PainCluster.status must be one of {sorted(ALLOWED_STATUSES)}"
            )

        if not isinstance(self.business_relevance, (int, float)) or not (
            0.0 <= float(self.business_relevance) <= 1.0
        ):
            raise ValueError("PainCluster.business_relevance must be 0.0–1.0")

        if not isinstance(self.noise_risk, (int, float)) or not (
            0.0 <= float(self.noise_risk) <= 1.0
        ):
            raise ValueError("PainCluster.noise_risk must be 0.0–1.0")

        _require_list(self.source_evidence_list, "PainCluster.source_evidence_list")
        if not self.source_evidence_list:
            raise ValueError("PainCluster.source_evidence_list must be non-empty")

        for i, entry in enumerate(self.source_evidence_list):
            if not isinstance(entry, SourceEvidenceEntry):
                raise ValueError(
                    f"PainCluster.source_evidence_list[{i}] must be a SourceEvidenceEntry"
                )
            entry.validate()

        if not isinstance(self.source_diversity, int) or self.source_diversity < 1:
            raise ValueError("PainCluster.source_diversity must be an int >= 1")

        if not isinstance(self.recurrence, int) or self.recurrence < 1:
            raise ValueError("PainCluster.recurrence must be an int >= 1")

        actual_diversity = len({e.source_type for e in self.source_evidence_list})
        if self.source_diversity != actual_diversity:
            raise ValueError(
                f"PainCluster.source_diversity ({self.source_diversity}) must match "
                f"distinct source types in evidence list ({actual_diversity})"
            )

        actual_recurrence = len(self.source_evidence_list)
        if self.recurrence != actual_recurrence:
            raise ValueError(
                f"PainCluster.recurrence ({self.recurrence}) must match "
                f"source_evidence_list length ({actual_recurrence})"
            )

        _require_list(
            self.representative_quotes_or_excerpts,
            "PainCluster.representative_quotes_or_excerpts",
        )
        if not self.representative_quotes_or_excerpts:
            raise ValueError(
                "PainCluster.representative_quotes_or_excerpts must be non-empty"
            )
        for i, quote in enumerate(self.representative_quotes_or_excerpts):
            if not isinstance(quote, str) or not quote.strip():
                raise ValueError(
                    f"PainCluster.representative_quotes_or_excerpts[{i}] must be a non-empty string"
                )
            if len(quote) > 200:
                raise ValueError(
                    f"PainCluster.representative_quotes_or_excerpts[{i}] must be <= 200 chars"
                )

        _require_list(
            self.linked_candidate_signals, "PainCluster.linked_candidate_signals"
        )
        for i, sig_id in enumerate(self.linked_candidate_signals):
            if not isinstance(sig_id, str) or not sig_id.strip():
                raise ValueError(
                    f"PainCluster.linked_candidate_signals[{i}] must be a non-empty string"
                )

        _require_list(
            self.linked_opportunity_candidates,
            "PainCluster.linked_opportunity_candidates",
        )
        for i, opp_id in enumerate(self.linked_opportunity_candidates):
            if not isinstance(opp_id, str) or not opp_id.strip():
                raise ValueError(
                    f"PainCluster.linked_opportunity_candidates[{i}] must be a non-empty string"
                )

        if not isinstance(self.scoring, PainClusterScoring):
            raise ValueError("PainCluster.scoring must be a PainClusterScoring")
        self.scoring.validate()

        if not isinstance(self.notes, str):
            raise ValueError("PainCluster.notes must be a string")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = asdict(self)
        d["source_evidence_list"] = [
            entry.to_dict() for entry in self.source_evidence_list
        ]
        d["scoring"] = self.scoring.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PainCluster:
        data = dict(data)
        data["source_evidence_list"] = [
            SourceEvidenceEntry.from_dict(e) for e in data.get("source_evidence_list", [])
        ]
        scoring_data = data.get("scoring", {})
        if not isinstance(scoring_data, PainClusterScoring):
            scoring_data = PainClusterScoring.from_dict(scoring_data)
        data["scoring"] = scoring_data
        cluster = cls(**data)
        cluster.validate()
        return cluster


# ---------------------------------------------------------------------------
# Deterministic cluster_id generation (contract Section 4)
# ---------------------------------------------------------------------------


def compute_cluster_id(
    actor: str, workflow: str, object: str, pain_pattern: str
) -> str:
    """Generate a stable, deterministic cluster_id from normalized pain pattern fields."""
    normalized_actor = actor.strip().lower()
    normalized_workflow = workflow.strip().lower()
    normalized_object = object.strip().lower()
    normalized_pain_pattern = pain_pattern.strip().lower()

    cluster_key = (
        f"{normalized_actor}|{normalized_workflow}|"
        f"{normalized_object}|{normalized_pain_pattern}"
    )
    hash_hex = hashlib.sha256(cluster_key.encode("utf-8")).hexdigest()
    return f"pc_{hash_hex[:16]}"


# ---------------------------------------------------------------------------
# Scoring components (contract Section 12)
# ---------------------------------------------------------------------------


def compute_recurrence_score(raw_count: int, source_diversity: int) -> float:
    """
    Normalize raw recurrence count to 0.0–1.0 with cross-source bonus
    (contract Sections 8.3, 8.4, 12.2).
    """
    score = min(1.0, raw_count / 5.0)
    if source_diversity >= 2:
        score = min(1.0, score * 1.15)
    return round(score, 4)


def compute_freshness_score(
    newest_evidence_created_at: str,
    now: datetime | None = None,
) -> float:
    """
    Compute freshness score from newest evidence timestamp (contract Section 12.6).
    Uses the NEWEST evidence's created_at for freshness.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    try:
        evidence_dt = datetime.fromisoformat(newest_evidence_created_at)
        if evidence_dt.tzinfo is None:
            evidence_dt = evidence_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.5

    age_days = (now - evidence_dt).days

    if age_days <= 7:
        freshness = 1.0
    elif age_days <= 30:
        freshness = 1.0 - (age_days - 7) / 23.0 * 0.4  # 1.0 → 0.6
    elif age_days <= 90:
        freshness = 0.6 - (age_days - 30) / 60.0 * 0.3  # 0.6 → 0.3
    else:
        freshness = max(0.1, 0.3 - (age_days - 90) / 270.0 * 0.2)  # 0.3 → 0.1

    return round(max(0.0, min(1.0, freshness)), 4)


def compute_source_reliability(
    evidence_entries: list[SourceEvidenceEntry],
    source_reliability_priors: dict[str, float] | None = None,
) -> float:
    """
    Compute source_reliability as weighted average of source reliability priors
    by evidence count per source (contract Section 13.3).
    """
    if source_reliability_priors is None:
        source_reliability_priors = SOURCE_RELIABILITY_PRIORS

    if not evidence_entries:
        return 0.5

    source_counts: dict[str, int] = {}
    for entry in evidence_entries:
        source_id = entry.source_id
        source_counts[source_id] = source_counts.get(source_id, 0) + 1

    total = sum(source_counts.values())
    weighted_sum = 0.0

    for source_id, count in source_counts.items():
        prior = source_reliability_priors.get(source_id)
        if prior is None:
            prior = SOURCE_TYPE_RELIABILITY_FALLBACK.get(entry.source_type, 0.5) if False else 0.5
        # Compute per-source reliability with fallback through source_type
        prior = source_reliability_priors.get(
            source_id,
            _source_type_reliability(source_id, evidence_entries),
        )
        weighted_sum += prior * count

    return round(weighted_sum / total, 4)


def _source_type_reliability(
    source_id: str, evidence_entries: list[SourceEvidenceEntry]
) -> float:
    """Look up reliability by matching source_id→source_type in evidence entries."""
    for entry in evidence_entries:
        if entry.source_id == source_id:
            return SOURCE_TYPE_RELIABILITY_FALLBACK.get(entry.source_type, 0.5)
    return 0.5


# ---------------------------------------------------------------------------
# Overall scoring formula (contract Section 11)
# ---------------------------------------------------------------------------

SCORING_WEIGHTS: dict[str, float] = {
    "pain_explicitness": 0.25,
    "recurrence": 0.20,
    "business_cost": 0.15,
    "icp_fit": 0.15,
    "source_reliability": 0.10,
    "freshness": 0.10,
    "actionability": 0.05,
    "noise_risk": -0.20,
}


def compute_overall_score(
    *,
    pain_explicitness: float,
    recurrence: float,
    business_cost: float,
    icp_fit: float,
    source_reliability: float,
    freshness: float,
    actionability: float,
    noise_risk: float,
) -> float:
    """Compute the overall cluster score using the deterministic formula and clamp."""
    overall = (
        SCORING_WEIGHTS["pain_explicitness"] * pain_explicitness
        + SCORING_WEIGHTS["recurrence"] * recurrence
        + SCORING_WEIGHTS["business_cost"] * business_cost
        + SCORING_WEIGHTS["icp_fit"] * icp_fit
        + SCORING_WEIGHTS["source_reliability"] * source_reliability
        + SCORING_WEIGHTS["freshness"] * freshness
        + SCORING_WEIGHTS["actionability"] * actionability
        + SCORING_WEIGHTS["noise_risk"] * noise_risk
    )
    return round(max(0.0, min(1.0, overall)), 4)


def compute_pain_cluster_scoring(
    cluster: PainCluster,
    *,
    pain_explicitness: float = 0.5,
    icp_fit: float = 0.5,
    actionability: float = 0.5,
    now: datetime | None = None,
    source_reliability_priors: dict[str, float] | None = None,
) -> PainClusterScoring:
    """
    Compute the complete PainClusterScoring for a cluster.

    Parameters:
        cluster: The PainCluster to score.
        pain_explicitness: 0.0–1.0 (set by cluster assembler; default 0.5).
        icp_fit: 0.0–1.0 (default 0.5 = neutral before founder review).
        actionability: 0.0–1.0 (default 0.5).
        now: Reference time for freshness (default: UTC now).
        source_reliability_priors: Per-source reliability map.

    Returns:
        PainClusterScoring with all 8 components and overall.
    """
    # Validate input ranges
    for name, value in [
        ("pain_explicitness", pain_explicitness),
        ("icp_fit", icp_fit),
        ("actionability", actionability),
    ]:
        if not (0.0 <= float(value) <= 1.0):
            raise ValueError(f"{name} must be 0.0–1.0, got {value}")

    recurrence_score = compute_recurrence_score(
        cluster.recurrence, cluster.source_diversity
    )

    # Find newest evidence timestamp
    newest_ts = cluster.created_at
    for entry in cluster.source_evidence_list:
        if entry.created_at > newest_ts:
            newest_ts = entry.created_at

    freshness_score = compute_freshness_score(newest_ts, now=now)
    source_reliability_score = compute_source_reliability(
        cluster.source_evidence_list, source_reliability_priors
    )

    overall = compute_overall_score(
        pain_explicitness=pain_explicitness,
        recurrence=recurrence_score,
        business_cost=float(cluster.business_relevance),
        icp_fit=icp_fit,
        source_reliability=source_reliability_score,
        freshness=freshness_score,
        actionability=actionability,
        noise_risk=float(cluster.noise_risk),
    )

    scoring = PainClusterScoring(
        overall=overall,
        pain_explicitness=round(float(pain_explicitness), 4),
        recurrence=recurrence_score,
        business_cost=round(float(cluster.business_relevance), 4),
        icp_fit=round(float(icp_fit), 4),
        source_reliability=source_reliability_score,
        freshness=freshness_score,
        actionability=round(float(actionability), 4),
        noise_risk=round(float(cluster.noise_risk), 4),
    )
    scoring.validate()
    return scoring


# ---------------------------------------------------------------------------
# Tier classification (contract Section 15.2)
# ---------------------------------------------------------------------------


def classify_cluster_tier(overall: float, noise_risk: float) -> str:
    """
    Return the tier recommendation based on overall score and noise_risk.

    Returns one of:
        - "candidate"            (overall >= 0.70, noise_risk < 0.80)
        - "needs_more_evidence"  (0.50 <= overall < 0.70)
        - "noise_or_park"        (overall < 0.50)
    Special case: any score with noise_risk >= 0.80 -> "noise_or_park"
    """
    if noise_risk >= 0.80:
        return "noise_or_park"
    if overall >= 0.70:
        return "candidate"
    if overall >= 0.50:
        return "needs_more_evidence"
    return "noise_or_park"


# ---------------------------------------------------------------------------
# Automatic status assignment (contract Section 14.3)
# ---------------------------------------------------------------------------


def assign_auto_status(overall: float, noise_risk: float, recurrence: int) -> str:
    """
    Compute the advisory automatic status for a cluster.

    Contract Section 14.3 rules:
        - noise_risk >= 0.80 → "noise"
        - overall < 0.30 AND recurrence < 2 → "weak"
        - overall < 0.50 AND noise_risk >= 0.50 → "noise"
        - otherwise → "new"
    """
    if noise_risk >= 0.80:
        return "noise"
    if overall < 0.30 and recurrence < 2:
        return "weak"
    if overall < 0.50 and noise_risk >= 0.50:
        return "noise"
    return "new"


# ---------------------------------------------------------------------------
# Validation (contract Section 19)
# ---------------------------------------------------------------------------


def validate_pain_cluster(cluster: PainCluster) -> tuple[list[str], list[str]]:
    """
    Validate a PainCluster and return (errors, warnings).

    Errors are blocking fail rules (Section 19.1).
    Warnings are non-blocking warn rules (Section 19.2).

    This performs structural validation. The PainCluster.validate() method
    handles field-level validation. This function adds cross-field and
    evidence-level validation checks.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # --- Field-level validation (delegates to model) ---
    try:
        cluster.validate()
    except ValueError as exc:
        errors.append(str(exc))
        return errors, warnings  # Cannot continue with invalid structure

    # --- Fail rules (VF1–VF16) ---
    # VF1–VF5 handled by validate()
    # VF6: empty evidence list
    if not cluster.source_evidence_list:
        errors.append("VF6: source_evidence_list is empty")

    # VF7–VF9: source_url checks
    for i, entry in enumerate(cluster.source_evidence_list):
        if not entry.source_url:
            errors.append(f"VF7: evidence[{i}] missing source_url")
        elif entry.source_url.startswith("urn:"):
            errors.append(f"VF8: evidence[{i}] has placeholder URL: {entry.source_url}")
        elif not entry.source_url.startswith(("http://", "https://")):
            errors.append(
                f"VF9: evidence[{i}] source_url not http(s)://: {entry.source_url}"
            )

    # VF10–VF12: scoring checks
    scoring = cluster.scoring
    if not (0.0 <= scoring.overall <= 1.0):
        errors.append(
            f"VF10: scoring.overall outside 0.0–1.0: {scoring.overall}"
        )

    component_names = [
        "pain_explicitness",
        "recurrence",
        "business_cost",
        "icp_fit",
        "source_reliability",
        "freshness",
        "actionability",
        "noise_risk",
    ]
    for name in component_names:
        value = getattr(scoring, name)
        if not (0.0 <= value <= 1.0):
            errors.append(
                f"VF11: scoring.{name} outside 0.0–1.0: {value}"
            )

    # VF12: overall must match formula
    expected_overall = compute_overall_score(
        pain_explicitness=scoring.pain_explicitness,
        recurrence=scoring.recurrence,
        business_cost=scoring.business_cost,
        icp_fit=scoring.icp_fit,
        source_reliability=scoring.source_reliability,
        freshness=scoring.freshness,
        actionability=scoring.actionability,
        noise_risk=scoring.noise_risk,
    )
    if scoring.overall != expected_overall:
        errors.append(
            f"VF12: scoring.overall ({scoring.overall}) does not match "
            f"formula result ({expected_overall})"
        )

    # VF13: source_diversity must match distinct source types
    actual_diversity = len({e.source_type for e in cluster.source_evidence_list})
    if cluster.source_diversity != actual_diversity:
        errors.append(
            f"VF13: source_diversity ({cluster.source_diversity}) != "
            f"distinct source types ({actual_diversity})"
        )

    # VF14: recurrence must match evidence list length
    if cluster.recurrence != len(cluster.source_evidence_list):
        errors.append(
            f"VF14: recurrence ({cluster.recurrence}) != "
            f"evidence list length ({len(cluster.source_evidence_list)})"
        )

    # VF15: timestamps must be valid ISO 8601
    for ts_name in ("created_at", "updated_at"):
        ts_value = getattr(cluster, ts_name)
        try:
            datetime.fromisoformat(ts_value)
        except (ValueError, TypeError):
            errors.append(f"VF15: {ts_name} is not valid ISO 8601: {ts_value!r}")

    # VF16: status must be valid
    if cluster.status not in ALLOWED_STATUSES:
        errors.append(
            f"VF16: status '{cluster.status}' not in {sorted(ALLOWED_STATUSES)}"
        )

    # --- Warn rules (VW1–VW8) ---
    # VW1: single-source only
    if cluster.source_diversity == 1:
        warnings.append("VW1: single-source evidence only")

    # VW2: high noise risk
    if cluster.noise_risk >= 0.60:
        warnings.append(f"VW2: high noise risk ({cluster.noise_risk})")

    # VW3: all evidence older than 90 days
    now = datetime.now(timezone.utc)
    all_stale = True
    for entry in cluster.source_evidence_list:
        try:
            dt = datetime.fromisoformat(entry.created_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if (now - dt).days <= 90:
                all_stale = False
                break
        except (ValueError, TypeError):
            pass
    if all_stale and cluster.source_evidence_list:
        warnings.append("VW3: all evidence older than 90 days (stale cluster)")

    # VW4: low business relevance
    if cluster.business_relevance < 0.30:
        warnings.append(
            f"VW4: low business relevance ({cluster.business_relevance})"
        )

    # VW5: missing representative quotes
    if not cluster.representative_quotes_or_excerpts:
        warnings.append("VW5: representative_quotes_or_excerpts is empty")

    # VW6: no primary_pain evidence
    has_primary = any(
        e.contribution_to_cluster == "primary_pain"
        for e in cluster.source_evidence_list
    )
    if not has_primary:
        warnings.append(
            "VW6: no evidence entry has contribution_to_cluster=primary_pain"
        )

    # VW7: empty linked_candidate_signals
    if not cluster.linked_candidate_signals:
        warnings.append(
            "VW7: linked_candidate_signals is empty (evidence-only cluster)"
        )

    # VW8: icp_fit is exactly 0.5 (default, not founder-reviewed)
    if cluster.scoring.icp_fit == 0.5:
        warnings.append("VW8: icp_fit is default 0.5 (not founder-reviewed)")

    return errors, warnings


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def pain_cluster_to_dict(cluster: PainCluster) -> dict[str, Any]:
    """Convert a PainCluster to a JSON-serializable dict."""
    return cluster.to_dict()


def pain_cluster_from_dict(data: dict[str, Any]) -> PainCluster:
    """Build a PainCluster from a dict with full nested object reconstruction."""
    return PainCluster.from_dict(data)


def scoring_to_dict(scoring: PainClusterScoring) -> dict[str, Any]:
    """Convert PainClusterScoring to a JSON-serializable dict."""
    return scoring.to_dict()


def scoring_from_dict(data: dict[str, Any]) -> PainClusterScoring:
    """Build a PainClusterScoring from a dict."""
    return PainClusterScoring.from_dict(data)


def evidence_entry_to_dict(entry: SourceEvidenceEntry) -> dict[str, Any]:
    """Convert a SourceEvidenceEntry to a JSON-serializable dict."""
    return entry.to_dict()


def evidence_entry_from_dict(data: dict[str, Any]) -> SourceEvidenceEntry:
    """Build a SourceEvidenceEntry from a dict."""
    return SourceEvidenceEntry.from_dict(data)
