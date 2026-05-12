from __future__ import annotations

"""PainCluster assembly: deterministic pain pattern extraction and cluster formation.

Takes RawEvidence / CandidateSignal-style dict inputs from HN and GitHub Issues
and assembles PainCluster artifacts with full provenance and source_url traceability.

No LLM calls. No semantic embeddings. No live APIs.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .pain_cluster import (
    PainCluster,
    PainClusterScoring,
    SourceEvidenceEntry,
    SCORING_MODEL_VERSION,
    compute_cluster_id,
    compute_pain_cluster_scoring,
    assign_auto_status,
    default_pain_cluster_scoring,
)
from .pain_cluster_dedupe import (
    compute_source_diversity,
    dedupe_full,
    normalize_evidence_source,
    normalize_source_id,
    normalize_source_type,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Quality flags that contribute to noise risk (ordered by severity)
# Each flag has a base contribution. The more flags present, the higher the risk.
_NOISE_FLAG_CONTRIBUTIONS: dict[str, float] = {
    "low_text_context": 0.10,
    "suspected_self_promo": 0.25,
    "launch_hype": 0.20,
    "flamewar_or_meta_discussion": 0.15,
    "bot_generated": 0.30,
    "stale_issue": 0.12,
    "duplicate_or_invalid": 0.18,
    "wontfix_or_not_planned": 0.10,
    "maintainer_housekeeping": 0.08,
    "source_access_limited": 0.15,
    "requires_manual_review": 0.10,
    "low_confidence_source": 0.20,
    "missing_date": 0.05,
    "high_noise_source": 0.35,
    "one_off_bug": 0.12,
}

# Business relevance indicator terms
_BUSINESS_POSITIVE_TERMS: tuple[str, ...] = (
    "cost", "pricing", "price", "pay", "paid", "spend", "spending",
    "time loss", "hours per", "days per", "weeks per",
    "manual", "spreadsheet", "hack", "workaround",
    "broken workflow", "broken pipeline",
    "production", "production issue", "production data",
    "compliance", "regulation", "regulatory", "audit",
    "customers", "customer", "client", "clients",
    "revenue", "revenue loss", "money",
    "support", "support team", "support burden",
    "teams", "team", "our team", "my team",
    "integration", "integrations", "integrate",
    "reliability", "reliable", "unreliable",
    "deploy", "deployment", "deploying",
    "scale", "scaling", "doesn't scale",
    "enterprise", "business", "company",
)

_BUSINESS_NEGATIVE_TERMS: tuple[str, ...] = (
    "hobby", "hobby project", "side project",
    "fun", "game", "gaming",
    "personal preference", "i wish",
    "aesthetic", "pretty", "ugly",
    "meta", "meta discussion",
    "one-off", "one off",
)


# ---------------------------------------------------------------------------
# Pain pattern extraction / normalization
# ---------------------------------------------------------------------------


def extract_pain_pattern(
    evidence: dict[str, Any],
) -> dict[str, str]:
    """Extract actor, workflow, object, pain_verb, pain_pattern from evidence.

    Deterministic only. Uses explicit metadata if present; otherwise falls
    back to conservative heuristics based on title/body/evidence_kind.

    If insufficient information is available, assigns "unknown" or
    "needs_more_evidence" rather than inventing a precise claim.

    Input dict may contain:
        title, body, raw_metadata, evidence_kind, source_id, source_type,
        quality_flags, signal_type, pain_summary, target_user
    """
    title = str(evidence.get("title", "") or "")
    body = str(evidence.get("body", "") or "")
    text = f"{title} {body}".lower()

    # Actor extraction
    actor = _extract_actor(evidence, text)

    # Workflow extraction
    workflow = _extract_workflow(evidence, text)

    # Object extraction
    object_ = _extract_object(evidence, text)

    # Pain verb extraction
    pain_verb = _extract_pain_verb(evidence, text)

    # Pain pattern: normalized single sentence
    if actor == "unknown" or workflow == "unknown":
        pain_pattern = "needs_more_evidence"
    else:
        pain_pattern = _format_pain_pattern(actor, workflow, object_, pain_verb)

    return {
        "actor": actor,
        "workflow": workflow,
        "object": object_,
        "pain_verb": pain_verb,
        "pain_pattern": pain_pattern,
    }


def _extract_actor(evidence: dict[str, Any], text: str) -> str:
    """Extract actor (who experiences the pain)."""
    # Check explicit metadata first
    raw_meta = evidence.get("raw_metadata") or {}
    if isinstance(raw_meta, dict):
        # Some adapters may store an explicit actor hint
        actor_hint = raw_meta.get("actor") or raw_meta.get("target_user") or ""
        if actor_hint and actor_hint not in ("unknown", "none", ""):
            return str(actor_hint).strip().lower()

    # Check CandidateSignal fields
    target_user = str(evidence.get("target_user", "") or "").strip()
    if target_user and target_user != "unknown":
        return target_user.lower()

    # Heuristics based on source_type and content
    source_type = normalize_source_type(str(evidence.get("source_type", "")))
    evidence_kind = str(evidence.get("evidence_kind", "") or "").lower()

    # Developer indicators
    developer_terms = ("developer", "dev ", "engineer", "programmer", "coder",
                       "api", "code", "coding", "repo", "repository")
    founder_terms = ("founder", "startup", "saas", "smb owner", "small business")
    finance_terms = ("accountant", "bookkeeper", "cfo", "finance", "controller",
                     "payroll", "invoice", "invoicing")

    dev_count = sum(1 for t in developer_terms if t in text)
    founder_count = sum(1 for t in founder_terms if t in text)
    finance_count = sum(1 for t in finance_terms if t in text)

    if source_type == "issue_tracker":
        return "developer"
    if dev_count >= 2:
        return "developer"
    if founder_count >= 2:
        return "founder"
    if finance_count >= 2:
        return "finance professional"
    if evidence_kind in ("bug_report", "feature_request", "integration_pain",
                         "performance_pain", "ux_pain", "documentation_gap"):
        return "developer"

    # Default conservative
    return "unknown"


def _extract_workflow(evidence: dict[str, Any], text: str) -> str:
    """Extract workflow (the task/process being disrupted)."""
    # Check explicit metadata
    raw_meta = evidence.get("raw_metadata") or {}
    if isinstance(raw_meta, dict):
        wf_hint = raw_meta.get("workflow") or raw_meta.get("pain_area") or ""
        if wf_hint and wf_hint not in ("unknown", "none", ""):
            return str(wf_hint).strip().lower()

    # Check pain_summary from CandidateSignal
    pain_summary = str(evidence.get("pain_summary", "") or "").strip()
    if pain_summary and pain_summary != "unknown" and len(pain_summary) <= 80:
        return pain_summary.lower()

    # Heuristics from title
    title = str(evidence.get("title", "") or "").strip().lower()
    if title:
        # Clean common prefixes
        title = title.replace("ask hn:", "").replace("show hn:", "").strip()
        if 10 <= len(title) <= 80:
            return title

    # Fallback: use evidence_kind as rough workflow hint
    evidence_kind = str(evidence.get("evidence_kind", "") or "").lower()
    kind_to_workflow: dict[str, str] = {
        "bug_report": "software debugging and issue resolution",
        "feature_request": "software feature development",
        "integration_pain": "system integration",
        "performance_pain": "performance optimization",
        "ux_pain": "user experience and workflow",
        "documentation_gap": "technical documentation",
        "pain_signal_candidate": "pain discovery",
        "workaround": "workaround maintenance",
        "complaint": "issue resolution",
    }
    if evidence_kind in kind_to_workflow:
        return kind_to_workflow[evidence_kind]

    return "unknown"


def _extract_object(evidence: dict[str, Any], text: str) -> str:
    """Extract object (tool/system/process causing the pain)."""
    raw_meta = evidence.get("raw_metadata") or {}
    if isinstance(raw_meta, dict):
        obj_hint = raw_meta.get("object") or raw_meta.get("tool") or ""
        if obj_hint and obj_hint not in ("unknown", "none", ""):
            return str(obj_hint).strip().lower()

    # Heuristics: look for tool/system mentions
    tool_indicators = (
        "kubernetes", "docker", "aws", "azure", "gcp",
        "github", "gitlab", "bitbucket",
        "jenkins", "circleci", "github actions",
        "terraform", "ansible", "pulumi",
        "vscode", "intellij", "eclipse",
        "quickbooks", "xero", "netsuite",
        "spreadsheet", "excel", "google sheets",
        "slack", "discord", "teams",
        "api", "sdk", "library", "framework",
        "database", "postgres", "mysql", "mongodb",
        "llm", "ai model", "agent", "ai agent",
    )
    for tool in tool_indicators:
        if tool in text:
            return tool

    # Use source_type as context
    source_id = normalize_source_id(str(evidence.get("source_id", "")))
    if source_id == "github_issues":
        raw_meta = evidence.get("raw_metadata") or {}
        if isinstance(raw_meta, dict):
            repo = raw_meta.get("repo") or ""
            if repo:
                return f"github repository {repo}"

    return "unknown"


def _extract_pain_verb(evidence: dict[str, Any], text: str) -> str:
    """Extract pain_verb (what hurts)."""
    raw_meta = evidence.get("raw_metadata") or {}
    if isinstance(raw_meta, dict):
        pv_hint = raw_meta.get("pain_verb") or ""
        if pv_hint and pv_hint not in ("unknown", "none", ""):
            return str(pv_hint).strip().lower()

    # Pattern-based extraction
    pain_patterns: list[tuple[tuple[str, ...], str]] = [
        (("cannot", "can't", "can not", "unable to", "impossible"), "cannot"),
        (("hard to", "difficult to", "painful to", "frustrating"), "hard to"),
        (("broken", "break", "breaks", "breaking"), "broken"),
        (("slow", "too slow", "slowness", "performance issue"), "too slow"),
        (("unreliable", "flaky", "unstable", "brittle"), "unreliable"),
        (("manual", "manual workaround", "workaround needed"), "requires manual workaround"),
        (("expensive", "costly", "too expensive", "overpriced"), "too expensive"),
        (("missing", "lacking", "no support", "not supported"), "missing"),
        (("lost", "loses", "losing", "data loss"), "loses data"),
        (("doesn't work", "not working", "fails", "failure"), "not working"),
        (("confusing", "unclear", "confusing ui", "hard to understand"), "confusing"),
    ]

    for terms, verb in pain_patterns:
        for term in terms:
            if term in text:
                return verb

    # Check evidence_kind
    evidence_kind = str(evidence.get("evidence_kind", "") or "").lower()
    kind_to_verb: dict[str, str] = {
        "bug_report": "not working",
        "feature_request": "missing",
        "integration_pain": "cannot integrate",
        "performance_pain": "too slow",
        "ux_pain": "hard to use",
        "documentation_gap": "hard to understand",
        "pain_signal_candidate": "painful",
        "complaint": "frustrating",
    }
    if evidence_kind in kind_to_verb:
        return kind_to_verb[evidence_kind]

    return "unknown"


def _format_pain_pattern(
    actor: str, workflow: str, object_: str, pain_verb: str
) -> str:
    """Format a pain_pattern sentence from components."""
    if actor == "unknown" or pain_verb == "unknown":
        return "needs_more_evidence"

    if object_ == "unknown":
        return f"{actor} cannot {workflow} because it is {pain_verb}"

    return f"{actor} cannot {workflow} because {object_} is {pain_verb}"


# ---------------------------------------------------------------------------
# Evidence entry construction
# ---------------------------------------------------------------------------


def build_evidence_entry(
    evidence: dict[str, Any],
    contribution: str = "primary_pain",
    signal_id: str | None = None,
) -> SourceEvidenceEntry:
    """Build a SourceEvidenceEntry from a normalized evidence dict.

    The evidence dict should have at minimum:
        evidence_id, source_id, source_type, source_url,
        title, body/excerpt, created_at, fetched_at/collected_at

    Quality flags are read from evidence['quality_flags'] if present.
    """
    ev_norm = normalize_evidence_source(evidence)

    evidence_id = str(ev_norm.get("evidence_id", ""))
    source_id = normalize_source_id(str(ev_norm.get("source_id", "")))
    source_type = normalize_source_type(str(ev_norm.get("source_type", "")))
    source_url = str(ev_norm.get("source_url", ""))
    evidence_kind = str(ev_norm.get("evidence_kind", "unknown"))
    title = str(ev_norm.get("title", ""))
    body = str(ev_norm.get("body", ""))
    created_at = str(ev_norm.get("created_at", "") or ev_norm.get("collected_at", ""))
    fetched_at = str(ev_norm.get("fetched_at", "") or ev_norm.get("collected_at", ""))
    quality_flags = list(ev_norm.get("quality_flags") or [])

    # Create excerpt from body, truncated to 500 chars
    excerpt = body.strip() if body.strip() else title.strip()
    if len(excerpt) > 500:
        excerpt = excerpt[:497] + "..."

    entry = SourceEvidenceEntry(
        evidence_id=evidence_id,
        source_id=source_id,
        source_type=source_type,
        source_url=source_url,
        evidence_kind=evidence_kind,
        title=title.strip(),
        excerpt=excerpt,
        created_at=created_at,
        fetched_at=fetched_at,
        contribution_to_cluster=contribution,
        signal_id=signal_id,
        quality_flags=quality_flags,
    )
    entry.validate()
    return entry


# ---------------------------------------------------------------------------
# Noise risk computation
# ---------------------------------------------------------------------------


def compute_noise_risk(
    evidence_list: list[dict[str, Any]],
    quality_flags_list: list[list[str]] | None = None,
) -> float:
    """Compute aggregate noise risk from quality flags across evidence items.

    Each quality flag contributes a base amount. Multiple flags compound
    (sum, capped at 1.0). A single flag does NOT auto-kill.
    """
    if not evidence_list:
        return 0.5

    if quality_flags_list is None:
        quality_flags_list = [
            list(ev.get("quality_flags") or []) for ev in evidence_list
        ]

    total_contribution = 0.0
    total_flags = 0

    for flags in quality_flags_list:
        for flag in flags:
            flag_lower = flag.lower().replace(" ", "_")
            contrib = _NOISE_FLAG_CONTRIBUTIONS.get(flag_lower, 0.05)
            total_contribution += contrib
            total_flags += 1

    # Base noise risk from evidence count (single evidence = slightly higher risk)
    base_risk = 0.05 if len(evidence_list) == 1 else 0.0

    # Normalize: more flags = higher risk, but a single flag is not fatal
    if total_flags == 0:
        noise = base_risk
    elif total_flags == 1:
        noise = base_risk + total_contribution
    else:
        # Compound: sum with diminishing returns
        noise = base_risk + min(1.0, total_contribution * (1.0 + 0.1 * (total_flags - 1)))

    return round(max(0.0, min(1.0, noise)), 4)


# ---------------------------------------------------------------------------
# Business relevance computation
# ---------------------------------------------------------------------------


def compute_business_relevance(text: str) -> float:
    """Compute simple deterministic business relevance heuristic.

    Higher if evidence mentions cost, pricing, time loss, manual work,
    broken workflow, production, compliance, customers, revenue, support,
    teams, integration, reliability.

    Lower for hobby-only, vague, meta, or one-off issues.

    Default neutral (0.5) if unclear.
    """
    if not text or not text.strip():
        return 0.5

    lowered = text.lower()
    positive_count = sum(1 for term in _BUSINESS_POSITIVE_TERMS if term in lowered)
    negative_count = sum(1 for term in _BUSINESS_NEGATIVE_TERMS if term in lowered)

    # Strong signals
    if positive_count >= 6 and negative_count == 0:
        return 0.85
    if positive_count >= 4 and negative_count == 0:
        return 0.70
    if positive_count >= 3 and negative_count <= 1:
        return 0.60
    if positive_count >= 2:
        return 0.55
    if negative_count >= 3 and positive_count == 0:
        return 0.20
    if negative_count >= 2 and positive_count <= 1:
        return 0.30
    if negative_count >= 1 and positive_count == 0:
        return 0.35

    return 0.50  # neutral


# ---------------------------------------------------------------------------
# Representative excerpt selection
# ---------------------------------------------------------------------------


def select_representative_excerpts(
    evidence_list: list[dict[str, Any]],
    max_excerpts: int = 3,
    max_chars: int = 200,
) -> list[str]:
    """Select representative excerpts from evidence list.

    Deterministic: picks the first N non-empty excerpts, preferring
    those with pain_indicator signals.
    """
    pain_terms = ("cannot", "can't", "hard to", "broken", "manual", "workaround",
                  "frustrating", "pain", "issue", "problem", "bug", "struggle")

    excerpts: list[str] = []
    for ev in evidence_list:
        body = str(ev.get("body", "") or "").strip()
        title = str(ev.get("title", "") or "").strip()
        text = body if body else title
        if not text:
            continue
        if len(text) > max_chars:
            text = text[:max_chars - 3] + "..."
        excerpts.append(text)

    # Prefer excerpts with pain terms
    scored = []
    for ex in excerpts:
        score = sum(1 for t in pain_terms if t in ex.lower())
        scored.append((score, ex))

    scored.sort(key=lambda x: (-x[0], x[1]))

    result = [ex for _, ex in scored[:max_excerpts]]
    if not result and excerpts:
        result = [excerpts[0]]
    return result


# ---------------------------------------------------------------------------
# Main assembly function
# ---------------------------------------------------------------------------


def assemble_pain_clusters(
    evidence_items: list[dict[str, Any]],
    *,
    dedupe: bool = True,
) -> tuple[list[PainCluster], list[dict[str, Any]], dict[str, Any]]:
    """Assemble PainCluster objects from a list of evidence/candidate-signal dicts.

    Steps:
    1. Normalize source_id/source_type on all inputs.
    2. Optionally deduplicate by evidence_id, canonical_url, source_url.
    3. Extract pain patterns (actor, workflow, object, pain_verb).
    4. Group by normalized pattern key.
    5. Build PainCluster for each group with scoring.
    6. Return clusters, unassigned evidence, and assembly summary.

    Args:
        evidence_items: List of dicts with fields like evidence_id, source_id,
            source_type, source_url, title, body, evidence_kind, quality_flags,
            created_at, collected_at, fetched_at.
        dedupe: If True, run full deduplication before clustering.

    Returns:
        (clusters, duplicates, summary) where:
        - clusters: list of PainCluster objects
        - duplicates: list of deduplicated evidence dicts
        - summary: dict with assembly metadata
    """
    if not evidence_items:
        return [], [], {
            "clusters_formed": 0,
            "total_evidence_in": 0,
            "total_evidence_out": 0,
            "duplicates_dropped": 0,
            "errors": ["empty_input"],
        }

    # Step 1: Normalize source_id/source_type
    normalized = [normalize_evidence_source(ev) for ev in evidence_items]

    # Step 2: Deduplicate
    duplicates: list[dict[str, Any]] = []
    if dedupe:
        normalized, duplicates = dedupe_full(normalized)

    # Step 3: Extract pain patterns and group
    pattern_groups: dict[str, list[dict[str, Any]]] = {}
    for ev in normalized:
        pattern = extract_pain_pattern(ev)
        ev["_pain_actor"] = pattern["actor"]
        ev["_pain_workflow"] = pattern["workflow"]
        ev["_pain_object"] = pattern["object"]
        ev["_pain_verb"] = pattern["pain_verb"]
        ev["_pain_pattern"] = pattern["pain_pattern"]

        group_key = f"{pattern['actor']}|{pattern['workflow']}|{pattern['object']}"
        if group_key not in pattern_groups:
            pattern_groups[group_key] = []
        pattern_groups[group_key].append(ev)

    # Step 4: Build clusters
    clusters: list[PainCluster] = []
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for group_key, ev_group in pattern_groups.items():
        cluster = _build_single_cluster(ev_group, now_iso)
        clusters.append(cluster)

    # Sort clusters by overall score descending
    clusters.sort(key=lambda c: c.scoring.overall, reverse=True)

    summary = {
        "clusters_formed": len(clusters),
        "total_evidence_in": len(evidence_items),
        "total_evidence_out": len(normalized),
        "duplicates_dropped": len(duplicates),
        "cluster_ids": [c.cluster_id for c in clusters],
        "assembly_timestamp": now_iso,
    }

    return clusters, duplicates, summary


def _build_single_cluster(
    ev_group: list[dict[str, Any]],
    now_iso: str,
) -> PainCluster:
    """Build a single PainCluster from a group of evidence items."""
    # Use the first item's extracted pattern (all items in group share it)
    first = ev_group[0]
    actor = str(first.get("_pain_actor", "unknown"))
    workflow = str(first.get("_pain_workflow", "unknown"))
    object_ = str(first.get("_pain_object", "unknown"))
    pain_verb = str(first.get("_pain_verb", "unknown"))
    pain_pattern = str(first.get("_pain_pattern", "needs_more_evidence"))

    # Build evidence entries
    entries: list[SourceEvidenceEntry] = []
    linked_signals: list[str] = []
    quality_flags_all: list[list[str]] = []

    for ev in ev_group:
        signal_id = str(ev.get("signal_id", "") or "")
        contribution = _determine_contribution(ev)
        entry = build_evidence_entry(ev, contribution=contribution, signal_id=signal_id if signal_id else None)
        entries.append(entry)
        if signal_id:
            linked_signals.append(signal_id)
        quality_flags_all.append(list(ev.get("quality_flags") or []))

    # Compute metrics
    source_diversity = compute_source_diversity(ev_group)
    recurrence = len(entries)
    noise_risk = compute_noise_risk(ev_group, quality_flags_all)

    # Combine text for business relevance
    combined_text = " ".join(
        str(ev.get("title", "") or "") + " " + str(ev.get("body", "") or "")
        for ev in ev_group
    )
    business_relevance = compute_business_relevance(combined_text)

    # Representative excerpts
    excerpts = select_representative_excerpts(ev_group)

    # Cluster identity
    cluster_id = compute_cluster_id(actor, workflow, object_, pain_pattern)

    # Initial scoring (defaults for pain_explicitness, icp_fit, actionability)
    # We'll compute these from evidence quality
    pain_explicitness = _estimate_pain_explicitness(ev_group)
    icp_fit = 0.5  # default neutral; founder reviews later
    actionability = 0.5  # default neutral

    # Build temporary cluster for scoring computation
    temp_cluster = PainCluster(
        cluster_id=cluster_id,
        actor=actor,
        workflow=workflow,
        object=object_,
        pain_verb=pain_verb,
        pain_pattern=pain_pattern,
        source_evidence_list=entries,
        source_diversity=source_diversity,
        recurrence=recurrence,
        business_relevance=business_relevance,
        noise_risk=noise_risk,
        representative_quotes_or_excerpts=excerpts,
        linked_candidate_signals=linked_signals,
        created_at=now_iso,
        updated_at=now_iso,
        status="new",
        scoring=default_pain_cluster_scoring(),
    )

    scoring = compute_pain_cluster_scoring(
        temp_cluster,
        pain_explicitness=pain_explicitness,
        icp_fit=icp_fit,
        actionability=actionability,
    )

    auto_status = assign_auto_status(
        overall=scoring.overall,
        noise_risk=noise_risk,
        recurrence=recurrence,
    )

    # Build final cluster
    final_cluster = PainCluster(
        cluster_id=cluster_id,
        actor=actor,
        workflow=workflow,
        object=object_,
        pain_verb=pain_verb,
        pain_pattern=pain_pattern,
        source_evidence_list=entries,
        source_diversity=source_diversity,
        recurrence=recurrence,
        business_relevance=business_relevance,
        noise_risk=noise_risk,
        representative_quotes_or_excerpts=excerpts,
        linked_candidate_signals=linked_signals,
        created_at=now_iso,
        updated_at=now_iso,
        status=auto_status,
        scoring=scoring,
    )

    return final_cluster


def _determine_contribution(evidence: dict[str, Any]) -> str:
    """Determine contribution_to_cluster for an evidence item."""
    evidence_kind = str(evidence.get("evidence_kind", "") or "").lower()
    body = str(evidence.get("body", "") or "").lower()

    # Pain-explicit kinds → primary_pain
    primary_kinds = {"pain_signal_candidate", "bug_report", "complaint",
                     "integration_pain", "performance_pain"}
    if evidence_kind in primary_kinds:
        return "primary_pain"

    # Workaround-related → workaround_description
    if evidence_kind == "workaround" or "workaround" in body:
        return "workaround_description"

    # Cost-related → cost_evidence
    cost_terms = ("cost", "price", "pricing", "pay", "spend", "expensive",
                  "dollars", "$", "budget")
    if any(t in body for t in cost_terms):
        return "cost_evidence"

    # Supporting
    supporting_kinds = {"feature_request", "ux_pain", "documentation_gap"}
    if evidence_kind in supporting_kinds:
        return "supporting_pain"

    return "context_only"


def _estimate_pain_explicitness(
    ev_group: list[dict[str, Any]],
) -> float:
    """Estimate pain_explicitness from evidence quality.

    Higher when:
    - Evidence has explicit pain terms
    - Actor, workflow, object are all known
    - Body text is substantial
    """
    pain_terms = ("pain", "struggle", "frustrating", "hard to", "can't",
                   "cannot", "broken", "doesn't work", "issue", "bug",
                   "describe the problem", "i would like", "i want to",
                   "we would need")

    total_score = 0.0
    for ev in ev_group:
        text = str(ev.get("title", "") or "") + " " + str(ev.get("body", "") or "")
        text_lower = text.lower()
        pain_count = sum(1 for t in pain_terms if t in text_lower)
        score = min(1.0, 0.3 + pain_count * 0.12)

        # Bonus for having substantial body
        if len(str(ev.get("body", "") or "")) > 200:
            score = min(1.0, score + 0.1)

        total_score += score

    avg = total_score / len(ev_group) if ev_group else 0.5
    return round(min(1.0, max(0.1, avg)), 4)


# ---------------------------------------------------------------------------
# Traceability validation
# ---------------------------------------------------------------------------


def validate_cluster_traceability(
    cluster: PainCluster,
) -> tuple[list[str], list[str]]:
    """Validate source_url traceability for all evidence entries in a cluster.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    for i, entry in enumerate(cluster.source_evidence_list):
        if not entry.source_url:
            errors.append(
                f"evidence[{i}] (id={entry.evidence_id}): missing source_url"
            )
        elif entry.source_url.startswith("urn:"):
            errors.append(
                f"evidence[{i}] (id={entry.evidence_id}): "
                f"placeholder URL: {entry.source_url}"
            )
        elif not entry.source_url.startswith(("http://", "https://")):
            errors.append(
                f"evidence[{i}] (id={entry.evidence_id}): "
                f"non-http(s) URL: {entry.source_url}"
            )

    if cluster.source_evidence_list and not errors:
        source_ids = {e.source_id for e in cluster.source_evidence_list}
        if len(source_ids) == 1:
            warnings.append(
                f"single-source cluster: only {list(source_ids)[0]}"
            )

    return errors, warnings
