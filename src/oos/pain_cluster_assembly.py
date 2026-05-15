from __future__ import annotations

"""PainCluster assembly: deterministic pain pattern extraction and cluster formation.

Takes RawEvidence / CandidateSignal-style dict inputs from HN and GitHub Issues
and assembles PainCluster artifacts with full provenance and source_url traceability.

v2.14 Item 4: Canonical pain anchors, cohesion scoring, catch-all splitting,
over-merge prevention, and quality-aware clustering.

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
# v2.14 Item 4: Canonical pain anchors
# ---------------------------------------------------------------------------

# Canonical pain anchors map known v2.13 themes to deterministic keyword sets.
# Each anchor has a name and a tuple of keyword terms.
# An evidence item may match multiple anchors (multi-anchor).
# The anchor with the most keyword matches wins; ties go to first defined.

_CANONICAL_PAIN_ANCHORS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "agent_trace_debugging",
        (
            "trace", "tracing", "spans", "callbacks", "run tree",
            "agent traces", "observability",
        ),
    ),
    (
        "tool_call_inspection",
        (
            "tool call", "function call", "tool execution", "callback", "span",
        ),
    ),
    (
        "output_provenance",
        (
            "provenance", "source attribution", "which agent",
            "contributed which part", "claim provenance", "source tracking",
        ),
    ),
    (
        "prompt_trace_replay",
        (
            "prompt variables", "prompt playground", "production trace",
            "replay", "rerun trace", "generation variables",
        ),
    ),
    (
        "stack_trace_context",
        (
            "stack trace", "exception context", "error context",
            "traceback", "missing error message",
        ),
    ),
    (
        "checkpoint_state_reproducibility",
        (
            "checkpoint", "state", "reproduce", "reproducibility",
            "deterministic", "corruption",
        ),
    ),
    (
        "structured_output_reliability",
        (
            "structured output", "schema", "json mode", "parser", "tool schema",
        ),
    ),
    (
        "llm_eval_testing",
        (
            "eval", "evaluation", "regression testing", "test cases",
            "prompt tests",
        ),
    ),
    (
        "integration_pipeline_friction",
        (
            "integration", "connector", "pipeline", "sync", "import", "export",
        ),
    ),
    (
        "generic_agent_debugging",
        (
            "agent", "debugging", "debug", "ai agent", "llm agent",
        ),
    ),
)

# Fallback anchor name when no specific anchor matches
_FALLBACK_ANCHOR = "generic_agent_debugging"

# Over-merge prevention: anchor pairs that must NOT be merged
# These anchor pairs represent distinct pain domains that should stay separate
# even if some keywords overlap.
_ANCHOR_MERGE_BLOCK_PAIRS: frozenset[tuple[str, str]] = frozenset({
    ("output_provenance", "prompt_trace_replay"),
    ("output_provenance", "stack_trace_context"),
    ("stack_trace_context", "prompt_trace_replay"),
    ("checkpoint_state_reproducibility", "llm_eval_testing"),
    ("checkpoint_state_reproducibility", "prompt_trace_replay"),
    ("structured_output_reliability", "agent_trace_debugging"),
    ("structured_output_reliability", "checkpoint_state_reproducibility"),
})

# Generic terms that should NOT alone justify a merge
_GENERIC_MERGE_TERMS: frozenset[str] = frozenset({
    "agent", "llm", "ai", "debugging", "observability",
    "github", "api", "prompt",
})


def _detect_canonical_anchors(evidence: dict[str, Any]) -> list[str]:
    """Detect which canonical pain anchors match this evidence.

    Returns a list of anchor names, sorted by match strength (most keywords
    matched first). Falls back to ``["generic_agent_debugging"]`` if no
    specific anchor matches.

    Uses the evidence title, body, and excerpt for keyword matching.
    """
    title = str(evidence.get("title", "") or "").lower()
    body = str(evidence.get("body", "") or "").lower()
    excerpt = str(evidence.get("excerpt", "") or "").lower()
    combined = f"{title} {body} {excerpt}"

    scored: list[tuple[int, str]] = []
    for anchor_name, keywords in _CANONICAL_PAIN_ANCHORS:
        raw_score = sum(1 for kw in keywords if kw in combined)
        if raw_score > 0:
            # Specific anchors get 2x multiplier to always outrank generic fallback
            if anchor_name == _FALLBACK_ANCHOR:
                score = raw_score
            else:
                score = raw_score * 2
            scored.append((score, anchor_name))

    if not scored:
        return [_FALLBACK_ANCHOR]

    # Sort: specific anchors always outrank generic fallback; then by score
    # descending; then alphabetical as tiebreaker.
    scored.sort(key=lambda x: (1 if x[1] == _FALLBACK_ANCHOR else 0, -x[0], x[1]))
    return [name for _, name in scored]


def _primary_canonical_anchor(evidence: dict[str, Any]) -> str:
    """Return the strongest canonical anchor for a single evidence item."""
    anchors = _detect_canonical_anchors(evidence)
    return anchors[0] if anchors else _FALLBACK_ANCHOR


def _anchors_allow_merge(anchor_a: str, anchor_b: str) -> bool:
    """Return True if two canonical anchors are allowed to merge.

    Same anchor always merges. Different anchors merge unless they
    appear in _ANCHOR_MERGE_BLOCK_PAIRS.
    """
    if anchor_a == anchor_b:
        return True
    pair = (anchor_a, anchor_b)
    reverse = (anchor_b, anchor_a)
    if pair in _ANCHOR_MERGE_BLOCK_PAIRS or reverse in _ANCHOR_MERGE_BLOCK_PAIRS:
        return False
    return True


def _compute_cohesion_score(
    ev_group: list[dict[str, Any]],
) -> float:
    """Compute cluster cohesion score (0.0-1.0).

    Based on:
    - Anchor overlap: fraction of evidence sharing the primary anchor.
    - Actor overlap: fraction sharing the same actor.
    - Workflow overlap: fraction sharing the same workflow (normalized).
    - Object domain overlap: fraction sharing the same object.

    High cohesion = evidence is tightly related.
    Low cohesion (< 0.4) = potential catch-all cluster.
    """
    if not ev_group or len(ev_group) <= 1:
        return 1.0 if ev_group else 0.5

    n = len(ev_group)

    # Anchor cohesion
    anchors = [_primary_canonical_anchor(ev) for ev in ev_group]
    primary_anchor = max(set(anchors), key=anchors.count)
    anchor_cohesion = anchors.count(primary_anchor) / n

    # Actor cohesion
    actors = [str(ev.get("_pain_actor", ev.get("target_user", "unknown"))).lower()
              for ev in ev_group]
    primary_actor = max(set(actors), key=actors.count)
    actor_cohesion = actors.count(primary_actor) / n

    # Workflow cohesion (normalize to known buckets)
    workflows = [str(ev.get("_pain_workflow", "unknown")).lower()
                 for ev in ev_group]
    _COARSE_WORKFLOW_MAP: dict[str, str] = {
        "debug": "debugging",
        "debugging": "debugging",
        "test": "testing",
        "testing": "testing",
        "deploy": "deployment",
        "deployment": "deployment",
        "build": "build_and_ci",
        "integrate": "integration",
        "integration": "integration",
        "monitor": "monitoring",
        "monitoring": "monitoring",
    }
    coarse_wfs = []
    for wf in workflows:
        coarse = "other"
        for key, val in _COARSE_WORKFLOW_MAP.items():
            if key in wf:
                coarse = val
                break
        coarse_wfs.append(coarse)
    primary_cwf = max(set(coarse_wfs), key=coarse_wfs.count)
    workflow_cohesion = coarse_wfs.count(primary_cwf) / n

    # Object cohesion (coarse)
    objects = [str(ev.get("_pain_object", "unknown")).lower()
               for ev in ev_group]
    primary_obj = max(set(objects), key=objects.count)
    object_cohesion = objects.count(primary_obj) / n

    # Weighted combination
    cohesion = (
        0.35 * anchor_cohesion
        + 0.25 * actor_cohesion
        + 0.20 * workflow_cohesion
        + 0.20 * object_cohesion
    )
    return round(max(0.0, min(1.0, cohesion)), 4)


def _classify_catch_all(
    cohesion_score: float,
    recurrence: int,
) -> bool:
    """Determine if a cluster is a catch-all risk.

    A cluster is catch-all if cohesion < 0.4 AND recurrence > 6.
    A cluster with many signals but low coherence is likely a catch-all.
    """
    return cohesion_score < 0.4 and recurrence > 6


def _suggest_split(
    ev_group: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Suggest splitting a low-cohesion cluster into sub-groups.

    Groups evidence by primary canonical anchor. If a sub-group has
    >= 2 items and a different anchor than the parent, it's a viable split.

    Returns a list of sub-groups (lists of evidence dicts). If no viable
    split is found, returns [ev_group] (original group unchanged).
    """
    if len(ev_group) <= 2:
        return [list(ev_group)]

    # Group by primary canonical anchor
    anchor_groups: dict[str, list[dict[str, Any]]] = {}
    for ev in ev_group:
        anchor = _primary_canonical_anchor(ev)
        anchor_groups.setdefault(anchor, []).append(ev)

    # If only one anchor group, try sub-anchor splitting by actor|object
    if len(anchor_groups) == 1:
        # Try splitting by actor|object instead
        ao_groups: dict[str, list[dict[str, Any]]] = {}
        for ev in ev_group:
            a = str(ev.get("_pain_actor", "unknown"))
            o = str(ev.get("_pain_object", "unknown"))
            ao_key = f"{a}|{o}"
            ao_groups.setdefault(ao_key, []).append(ev)

        if len(ao_groups) >= 2:
            viable = [g for g in ao_groups.values() if len(g) >= 2]
            if viable:
                return viable

        return [list(ev_group)]

    # Filter to viable sub-groups (>= 2 items)
    viable = [g for g in anchor_groups.values() if len(g) >= 2]

    if len(viable) >= 2:
        return viable

    # Not enough viable sub-groups; return unsplit
    return [list(ev_group)]


def _should_merge(
    ev_a: dict[str, Any],
    ev_b: dict[str, Any],
) -> bool:
    """Determine if two evidence items should merge into the same cluster.

    v2.14 rules:
    - Must share at least 2 of {actor, workflow_family, object_domain}
      OR share a specific (non-generic) canonical anchor.
    - Product launch / self-promo evidence does NOT merge with concrete
      bug reports unless they share a specific pain anchor.
    - Low text context / context_only does NOT dominate merge decisions.
    - Noise evidence does NOT merge with accepted evidence unless they
      share a specific anchor.
    """
    # Quality-based filtering.
    # Pre-computed _contribution and _noise_classification are set in step 3.
    flags_a = set(ev_a.get("quality_flags", []) or [])
    flags_b = set(ev_b.get("quality_flags", []) or [])
    kind_a = str(ev_a.get("evidence_kind", "")).lower()
    kind_b = str(ev_b.get("evidence_kind", "")).lower()
    contrib_a = str(ev_a.get("contribution_to_cluster",
                             ev_a.get("_contribution", "primary_pain"))).lower()
    contrib_b = str(ev_b.get("contribution_to_cluster",
                             ev_b.get("_contribution", "primary_pain"))).lower()

    # Product launch + bug report -> no merge without specific anchor overlap
    is_launch_a = ("product_launch" in kind_a or "launch_hype" in flags_a
                   or "suspected_self_promo" in flags_a)
    is_launch_b = ("product_launch" in kind_b or "launch_hype" in flags_b
                   or "suspected_self_promo" in flags_b)
    is_bug_a = "bug_report" in kind_a or "primary_pain" in contrib_a
    is_bug_b = "bug_report" in kind_b or "primary_pain" in contrib_b

    if (is_launch_a and is_bug_b) or (is_launch_b and is_bug_a):
        # Only merge if they share a specific (non-generic) anchor
        anchor_a = _primary_canonical_anchor(ev_a)
        anchor_b = _primary_canonical_anchor(ev_b)
        if anchor_a == anchor_b and anchor_a != _FALLBACK_ANCHOR:
            return True
        return False

    # Low text context / context_only should not drive merging
    is_weak_a = "low_text_context" in flags_a or contrib_a == "context_only"
    is_weak_b = "low_text_context" in flags_b or contrib_b == "context_only"
    if is_weak_a and is_weak_b:
        # Both weak: only merge if same specific anchor
        anchor_a = _primary_canonical_anchor(ev_a)
        anchor_b = _primary_canonical_anchor(ev_b)
        return anchor_a == anchor_b and anchor_a != _FALLBACK_ANCHOR
    if is_weak_a or is_weak_b:
        # One weak, one not: weak can follow the strong only if anchor matches
        anchor_a = _primary_canonical_anchor(ev_a)
        anchor_b = _primary_canonical_anchor(ev_b)
        return anchor_a == anchor_b and anchor_a != _FALLBACK_ANCHOR

    # Noise classification check: noise does NOT merge with accepted.
    # Uses pre-computed _noise_classification set during assembly step 3.
    noise_a = str(ev_a.get("_noise_classification", "accepted"))
    noise_b = str(ev_b.get("_noise_classification", "accepted"))
    if noise_a == "noise" and noise_b != "noise":
        return False
    if noise_b == "noise" and noise_a != "noise":
        return False

    # Canonical anchor check: shared specific anchor -> merge.
    # v2.14: same strong specific anchor can override actor mismatch
    # when one actor is unknown or generic.
    anchor_a = _primary_canonical_anchor(ev_a)
    anchor_b = _primary_canonical_anchor(ev_b)
    if anchor_a == anchor_b and anchor_a != _FALLBACK_ANCHOR:
        # Check if this pair is blocked from merging
        if not _anchors_allow_merge(anchor_a, anchor_b):
            return False
        return True

    # Different anchors that are blocked -> no merge
    if not _anchors_allow_merge(anchor_a, anchor_b):
        return False

    # When one anchor is specific (non-generic) and the other is the
    # generic fallback, require all 3 dimensions to match to prevent
    # the generic anchor from pulling specific evidence into broad groups.
    if (anchor_a != _FALLBACK_ANCHOR and anchor_b == _FALLBACK_ANCHOR) or \
       (anchor_a == _FALLBACK_ANCHOR and anchor_b != _FALLBACK_ANCHOR):
        actor_a = str(ev_a.get("_pain_actor", ev_a.get("target_user", "unknown"))).lower()
        actor_b = str(ev_b.get("_pain_actor", ev_b.get("target_user", "unknown"))).lower()
        match_actor = (actor_a == actor_b and actor_a != "unknown")

        wf_a = str(ev_a.get("_pain_workflow", "unknown")).lower()
        wf_b = str(ev_b.get("_pain_workflow", "unknown")).lower()
        _WF_NORMALIZE: dict[str, str] = {
            "debug": "debugging", "debugging": "debugging",
            "test": "testing", "testing": "testing",
            "deploy": "deployment", "deployment": "deployment",
            "build": "build", "integrate": "integration", "integration": "integration",
            "monitor": "monitoring", "monitoring": "monitoring",
        }
        wf_ca = _WF_NORMALIZE.get(wf_a, wf_a)
        wf_cb = _WF_NORMALIZE.get(wf_b, wf_b)
        match_workflow = (wf_ca == wf_cb and wf_a != "unknown")

        obj_a = str(ev_a.get("_pain_object", "unknown")).lower()
        obj_b = str(ev_b.get("_pain_object", "unknown")).lower()
        match_object = (obj_a == obj_b and obj_a != "unknown")

        # Need all 3 when crossing generic/specific boundary
        return match_actor and match_workflow and match_object

    # Generic anchor case: need at least 2 of {actor, workflow_family, object}
    # to match.  unknown actor does NOT block merge if workflow+object match.
    actor_a = str(ev_a.get("_pain_actor", ev_a.get("target_user", "unknown"))).lower()
    actor_b = str(ev_b.get("_pain_actor", ev_b.get("target_user", "unknown"))).lower()
    match_actor = (actor_a == actor_b and actor_a != "unknown")

    wf_a = str(ev_a.get("_pain_workflow", "unknown")).lower()
    wf_b = str(ev_b.get("_pain_workflow", "unknown")).lower()
    _WF_NORMALIZE: dict[str, str] = {
        "debug": "debugging", "debugging": "debugging",
        "test": "testing", "testing": "testing",
        "deploy": "deployment", "deployment": "deployment",
        "build": "build", "integrate": "integration", "integration": "integration",
        "monitor": "monitoring", "monitoring": "monitoring",
    }
    wf_ca = _WF_NORMALIZE.get(wf_a, wf_a)
    wf_cb = _WF_NORMALIZE.get(wf_b, wf_b)
    match_workflow = (wf_ca == wf_cb and wf_a != "unknown")

    obj_a = str(ev_a.get("_pain_object", "unknown")).lower()
    obj_b = str(ev_b.get("_pain_object", "unknown")).lower()
    match_object = (obj_a == obj_b and obj_a != "unknown")

    matches = sum([match_actor, match_workflow, match_object])
    return matches >= 2


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
                       "api", "code", "coding", "repo", "repository",
                       "debug", "debugging", "trace", "tracing",
                       "agent", "deploy", "deployment", "pull request")
    founder_terms = ("founder", "startup", "saas", "smb owner", "small business")
    finance_terms = ("accountant", "bookkeeper", "cfo", "finance", "controller",
                     "payroll", "invoice", "invoicing")

    dev_count = sum(1 for t in developer_terms if t in text)
    founder_count = sum(1 for t in founder_terms if t in text)
    finance_count = sum(1 for t in finance_terms if t in text)

    if source_type == "issue_tracker":
        return "developer"
    # Founder / finance take priority over developer when explicitly signalled
    if founder_count >= 1:
        return "founder"
    if finance_count >= 2:
        return "finance professional"
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
    body = str(evidence.get("body", "") or "").strip().lower()

    # Body-based workflow extraction: if body mentions a specific
    # workflow keyword not already captured by the title, prefer it.
    _BODY_WORKFLOW_KEYWORDS: tuple[tuple[str, str], ...] = (
        ("deploy", "software deployment"),
        ("debug", "software debugging"),
        ("test", "software testing"),
        ("build", "software build and CI"),
        ("integrate", "system integration"),
        ("monitor", "system monitoring"),
        ("migrate", "data migration"),
        ("scale", "system scaling"),
        ("forecast", "financial forecasting"),
    )
    if body:
        for keyword, workflow_label in _BODY_WORKFLOW_KEYWORDS:
            if keyword in body and (not title or keyword not in title):
                return workflow_label

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

    # Heuristics: look for tool/system mentions.
    # Search body-only to avoid title pollution (titles often generic labels).
    body = str(evidence.get("body", "") or "").strip().lower()
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
        if tool in body:
            return tool

    # Fallback: search full text (title + body) for broader signal
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
    3. Extract pain patterns, canonical anchors, and noise classification.
    4. Union-find clustering: merge evidence when _should_merge() returns true.
       Initial candidate groups are seeded by canonical anchor; then each
       evidence pair is tested via _should_merge() and merged incrementally.
    5. Build PainCluster for each union-find group with scoring and cohesion.
    6. Auto-split catch-all clusters.
    7. Return clusters, unassigned evidence, and assembly summary.

    v2.14 Item 4 (active): _should_merge() governs cluster membership using
    same-anchor merge (with actor-override for unknown/generic), anchor
    blocking pairs, quality/noise filtering, product-launch isolation,
    and at-least-2-of-{actor,workflow,object} compatibility for generic
    anchors.  Deterministic ordering: stable sort by evidence_id ensures
    reproducible clusters.

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

    # Step 3: Extract pain patterns, detect canonical anchors,
    # pre-compute noise classification, and determine contribution
    # (all used later by _should_merge and _build_single_cluster).
    from .noise_classifier import classify_noise_for_evidence

    for ev in normalized:
        pattern = extract_pain_pattern(ev)
        ev["_pain_actor"] = pattern["actor"]
        ev["_pain_workflow"] = pattern["workflow"]
        ev["_pain_object"] = pattern["object"]
        ev["_pain_verb"] = pattern["pain_verb"]
        ev["_pain_pattern"] = pattern["pain_pattern"]
        ev["_canonical_anchor"] = _primary_canonical_anchor(ev)
        ev["_canonical_anchors"] = _detect_canonical_anchors(ev)
        ev["_noise_classification"] = classify_noise_for_evidence(ev)
        ev["_contribution"] = _determine_contribution(ev)

    # Step 4: v2.14 active union-find clustering via _should_merge().
    # Phase 4a: Pre-group by canonical anchor as seed candidates.
    # Evidence with the same non-generic anchor always starts together.
    anchor_groups: dict[str, list[int]] = {}
    for idx, ev in enumerate(normalized):
        anchor = str(ev.get("_canonical_anchor", _FALLBACK_ANCHOR))
        anchor_groups.setdefault(anchor, []).append(idx)

    # Union-find helpers
    n = len(normalized)
    parent = list(range(n))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(a: int, b: int) -> None:
        ra, rb = _find(a), _find(b)
        if ra != rb:
            parent[rb] = ra

    # Phase 4b: Merge evidence pairs within each anchor seed group.
    # Stable order: indices within each group are processed deterministically.
    for anchor, indices in anchor_groups.items():
        m = len(indices)
        for i in range(m):
            for j in range(i + 1, m):
                idx_a, idx_b = indices[i], indices[j]
                if _find(idx_a) == _find(idx_b):
                    continue
                if _should_merge(normalized[idx_a], normalized[idx_b]):
                    _union(idx_a, idx_b)

    # Phase 4c: Cross-anchor merging for anchors that _should_merge() allows.
    # v2.14 fix: compare ALL evidence pairs across compatible anchor groups,
    # not just first representatives.  This prevents representative-order
    # fragmentation where a matching pair is missed because the first-index
    # representative does not satisfy _should_merge().
    #
    # v2.14 Codex fix (stale root_to_items): fixed-point loop rebuilds the
    # root-to-items map after each successful cross-anchor union.  Without
    # this rebuild, later root-pair scans can see the updated union-find
    # root but retrieve stale item lists, missing compatible evidence that
    # was just merged into that root.
    #
    # Bounded: at most n-1 successful unions; evidence counts are small
    # in expected pilot runs.
    sorted_anchors = sorted(anchor_groups.keys())
    changed = True
    while changed:
        changed = False

        # Rebuild root-to-items map fresh from current union-find state.
        # This ensures that evidence merged in a previous iteration is
        # visible when deciding further root-pair merges.
        root_to_items: dict[int, list[int]] = {}
        for idx in range(n):
            root = _find(idx)
            root_to_items.setdefault(root, []).append(idx)

        for ai in range(len(sorted_anchors)):
            anchor_a = sorted_anchors[ai]
            for aj in range(ai + 1, len(sorted_anchors)):
                anchor_b = sorted_anchors[aj]
                if not _anchors_allow_merge(anchor_a, anchor_b):
                    continue
                indices_a = anchor_groups[anchor_a]
                indices_b = anchor_groups[anchor_b]
                if not indices_a or not indices_b:
                    continue

                # Collect current union-find roots in each anchor group
                roots_a: set[int] = {_find(idx) for idx in indices_a}
                roots_b: set[int] = {_find(idx) for idx in indices_b}

                # For every pair of roots from different anchor groups,
                # compare all evidence items deterministically.
                for root_a in sorted(roots_a):
                    for root_b in sorted(roots_b):
                        if root_a == root_b:
                            continue
                        items_a = root_to_items.get(root_a, [])
                        items_b = root_to_items.get(root_b, [])
                        if not items_a or not items_b:
                            continue

                        # Sort deterministically by evidence_id
                        items_a.sort(key=lambda idx: str(normalized[idx].get("evidence_id", "")))
                        items_b.sort(key=lambda idx: str(normalized[idx].get("evidence_id", "")))

                        merged = False
                        for idx_a in items_a:
                            if merged:
                                break
                            for idx_b in items_b:
                                if _find(idx_a) == _find(idx_b):
                                    continue
                                if _should_merge(normalized[idx_a], normalized[idx_b]):
                                    _union(idx_a, idx_b)
                                    merged = True
                                    break
                        if merged:
                            # root_to_items is now stale; break to outer
                            # loop to rebuild and restart the scan
                            break
                    if merged:
                        break
                if merged:
                    break
            if merged:
                changed = True
                break

    # Phase 4d: Collect groups by union-find root.
    pattern_groups: dict[int, list[dict[str, Any]]] = {}
    for idx in range(n):
        root = _find(idx)
        pattern_groups.setdefault(root, []).append(normalized[idx])

    # Step 5: Build initial clusters
    clusters: list[PainCluster] = []
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for _root, ev_group in pattern_groups.items():
        cluster = _build_single_cluster(ev_group, now_iso)
        clusters.append(cluster)

    # Step 6: v2.14 Auto-split catch-all clusters
    clusters = _apply_catch_all_split(clusters, now_iso)

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
    """Build a single PainCluster from a group of evidence items.

    v2.14: Computes cohesion_score, catch_all_risk, canonical_anchor.
    """
    first = ev_group[0]
    actor = str(first.get("_pain_actor", "unknown"))
    workflow = str(first.get("_pain_workflow", "unknown"))
    object_ = str(first.get("_pain_object", "unknown"))
    pain_verb = str(first.get("_pain_verb", "unknown"))
    pain_pattern = str(first.get("_pain_pattern", "needs_more_evidence"))

    # v2.14: Canonical anchors
    canonical_anchor = str(first.get("_canonical_anchor", _FALLBACK_ANCHOR))
    canonical_anchors: list[str] = []
    all_anchors: set[str] = set()
    for ev in ev_group:
        for a in ev.get("_canonical_anchors", [canonical_anchor]):
            all_anchors.add(str(a))
    canonical_anchors = sorted(all_anchors)
    if not canonical_anchors:
        canonical_anchors = [canonical_anchor]

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

    # v2.14: Cohesion score and catch-all detection
    cohesion_score = _compute_cohesion_score(ev_group)
    catch_all_risk = _classify_catch_all(cohesion_score, recurrence)

    # Cluster identity (v2.14: use canonical_anchor)
    cluster_id = compute_cluster_id(
        f"{canonical_anchor}:{actor}",
        workflow,
        object_,
        pain_pattern,
    )

    # Initial scoring (defaults for pain_explicitness, icp_fit, actionability)
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
        cohesion_score=cohesion_score,
        catch_all_risk=catch_all_risk,
        canonical_anchor=canonical_anchor,
        canonical_anchors=list(canonical_anchors),
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
        cohesion_score=cohesion_score,
        catch_all_risk=catch_all_risk,
        canonical_anchor=canonical_anchor,
        canonical_anchors=list(canonical_anchors),
    )

    return final_cluster


def _apply_catch_all_split(
    clusters: list[PainCluster],
    now_iso: str,
) -> list[PainCluster]:
    """Apply catch-all splitting to clusters with low cohesion and many signals.

    For each cluster flagged as catch_all_risk, attempt to split into
    sub-groups with higher internal cohesion.
    """
    result: list[PainCluster] = []

    for cluster in clusters:
        if not cluster.catch_all_risk or cluster.recurrence <= 6:
            result.append(cluster)
            continue

        ev_dicts: list[dict[str, Any]] = []
        for entry in cluster.source_evidence_list:
            ev = {
                "evidence_id": entry.evidence_id,
                "source_id": entry.source_id,
                "source_type": entry.source_type,
                "source_url": entry.source_url,
                "title": entry.title,
                "body": entry.excerpt,
                "excerpt": entry.excerpt,
                "evidence_kind": entry.evidence_kind,
                "quality_flags": list(entry.quality_flags),
                "_pain_actor": cluster.actor,
                "_pain_workflow": cluster.workflow,
                "_pain_object": cluster.object,
                "_pain_verb": cluster.pain_verb,
                "_pain_pattern": cluster.pain_pattern,
                "_canonical_anchor": cluster.canonical_anchor,
                "_canonical_anchors": list(cluster.canonical_anchors),
                "created_at": entry.created_at,
                "collected_at": entry.fetched_at,
                "signal_id": entry.signal_id,
            }
            ev_dicts.append(ev)

        sub_groups = _suggest_split(ev_dicts)
        if len(sub_groups) <= 1:
            result.append(cluster)
            continue

        for sub_group in sub_groups:
            for ev in sub_group:
                ev["_canonical_anchor"] = _primary_canonical_anchor(ev)
                ev["_canonical_anchors"] = _detect_canonical_anchors(ev)
            sub_cluster = _build_single_cluster(sub_group, now_iso)
            result.append(sub_cluster)

    return result


def _determine_contribution(evidence: dict[str, Any]) -> str:
    """Determine contribution_to_cluster for an evidence item."""
    evidence_kind = str(evidence.get("evidence_kind", "") or "").lower()
    body = str(evidence.get("body", "") or "").lower()

    # Pain-explicit kinds -> primary_pain
    primary_kinds = {"pain_signal_candidate", "bug_report", "complaint",
                     "integration_pain", "performance_pain"}
    if evidence_kind in primary_kinds:
        return "primary_pain"

    # Workaround-related -> workaround_description
    if evidence_kind == "workaround" or "workaround" in body:
        return "workaround_description"

    # Cost-related -> cost_evidence
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


# ---------------------------------------------------------------------------
# Cluster review title generation (deterministic, founder-facing)
# ---------------------------------------------------------------------------


# Pattern-based title matching: keyword groups -> normalized titles.
# Ordered: first match wins. Prefer more specific patterns first.
_PATTERN_TITLE_MAP: list[tuple[tuple[str, ...], str]] = [
    # Trace / tracing / observability
    (("trace", "tracing", "observability", "observable"), "Agent traces lack actionable debugging context"),
    # Tool calls / spans / callbacks
    (("tool call", "tool calls", "span", "spans", "callback", "callbacks"), "Agent tool-call traces are hard to inspect"),
    # Provenance / source attribution
    (("provenance", "source attribution", "output provenance", "which agent",
      "source tracking", "claim provenance", "trust and sources", "agent output metadata",
      "contributed which part"), "Multi-agent outputs lose provenance"),
    # Prompt variables / playground / production trace
    (("prompt variable", "production trace", "prompt playground", "replay"), "Prompt workflows cannot replay production trace inputs"),
    # Stack trace / exception / error context
    (("stack trace", "exception", "error context", "debugging context"), "Stack traces lack actionable state details"),
    # Checkpoint / state / reproducibility
    (("checkpoint", "reproduc", "state serializ", "deterministic"), "Agent state is hard to reproduce and debug"),
    # Structured output / schema
    (("structured output", "schema", "json schema", "output format", "output schema"), "Structured LLM outputs fail unpredictably"),
    # Eval / testing / regression
    (("eval", "testing", "regression test", "test suite", "benchmark"), "LLM app testing lacks reliable regression workflow"),
    # Debug / debugging (generic, lower priority)
    (("debug", "debugging"), "Agent debugging workflows lack actionable context"),
]

# Terms to strip from raw titles
_TITLE_PREFIXES_TO_STRIP: tuple[str, ...] = (
    "[dead]", "(dead)", "[dead] ",
    "Show HN:", "Ask HN:", "Launch HN:", "Tell HN:",
    "[Feature]", "[Bug]", "[RFC]", "RFC:",
    "[Feature Request]", "[Request]",
)

# Placeholder values that should never appear as titles
_TITLE_PLACEHOLDERS: frozenset[str] = frozenset({
    "needs_more_evidence", "unknown", "[dead]", "dead",
})

# Malformed grammar patterns to clean from derived titles
_MALFORMED_PATTERNS: list[tuple[str, str]] = [
    # "because X is cannot" -> remove trailing " is cannot" / " is missing" etc.
    (" because it is cannot", ""),
    (" because it is unknown", ""),
    (" because it is painful", " is painful"),
    (" because X is cannot", ""),
    (" because X is missing", " is unavailable"),
    # "developer cannot [dead]" -> remove noise words
    (" cannot [dead]", ""),
    (" cannot dead", ""),
    (" cannot needs_more_evidence", ""),
]

# Maximum title length
_MAX_TITLE_LENGTH: int = 90

# Quality flags that suggest noise (prefer other evidence)
_SEVERE_QUALITY_FLAGS: frozenset[str] = frozenset({
    "bot_generated", "maintainer_housekeeping", "flamewar_or_meta_discussion",
    "high_noise_source", "duplicate_or_invalid",
})
_MODERATE_QUALITY_FLAGS: frozenset[str] = frozenset({
    "suspected_self_promo", "vendor_promo", "launch_hype", "low_text_context",
    "generic_language", "low_confidence_extraction", "missing_actor", "unclear_actor",
})

# Contribution priority for evidence selection (higher = prefer)
_CONTRIBUTION_PRIORITY: dict[str, int] = {
    "primary_pain": 5,
    "supporting_pain": 4,
    "workaround_description": 3,
    "cost_evidence": 2,
    "context_only": 1,
}


def generate_cluster_review_title(cluster: dict[str, Any]) -> str:
    """Generate a clean, founder-readable cluster review title.

    Deterministic only. No LLM calls. Uses cluster evidence titles/excerpts
    and pattern-based heuristics to produce short, readable, business-relevant titles.

    Fallback hierarchy:
      A. Pattern-based match against known pain patterns (trace, debugging, etc.)
      B. Actor + object + pain verb normalization
      C. Cleaned best evidence title
      D. ``"Unclear developer workflow pain"``

    Args:
        cluster: A cluster dict (from ``PainCluster.to_dict()`` or similar).

    Returns:
        A cleaned, founder-readable title string (non-empty, <= 90 chars).
    """
    evidence_list: list[dict[str, Any]] = cluster.get("source_evidence_list", [])
    actor = str(cluster.get("actor", "developer"))
    obj = str(cluster.get("object", "unknown"))
    workflow = str(cluster.get("workflow", "unknown"))
    pain_verb = str(cluster.get("pain_verb", "unknown"))
    pain_pattern = str(cluster.get("pain_pattern", ""))

    # Step 1: Select best evidence for title derivation
    best_evidence = _select_best_evidence_for_title(evidence_list)

    # Step 2: Build combined text for pattern detection
    combined_text = _build_combined_text(best_evidence, actor, obj, workflow, pain_verb)

    # Step 3: Pattern-based matching (Tier A)
    pattern_title = _match_known_pattern(combined_text)
    if pattern_title:
        return pattern_title

    # Step 4: Derived from components (Tier B)
    derived = _derive_from_components(actor, obj, workflow, pain_verb, pain_pattern)
    if derived and derived not in _TITLE_PLACEHOLDERS:
        return _clean_and_truncate(derived)

    # Step 5: Best evidence title (Tier C)
    evidence_title = _best_evidence_title_cleaned(best_evidence)
    if evidence_title and evidence_title not in _TITLE_PLACEHOLDERS:
        return _clean_and_truncate(evidence_title)

    # Step 6: Fallback (Tier D)
    return "Unclear developer workflow pain"


def _select_best_evidence_for_title(
    evidence_list: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Select and rank evidence items best suited for title generation.

    Prioritizes primary_pain with fewer quality flags.
    Returns up to 3 items, sorted by quality.
    """
    if not evidence_list:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    for ev in evidence_list:
        contribution = str(ev.get("contribution_to_cluster", "context_only"))
        quality_flags: list[str] = list(ev.get("quality_flags", []) or [])

        # Score: higher = better for title
        contrib_score = _CONTRIBUTION_PRIORITY.get(contribution, 1)

        # Penalize noise/weak evidence
        severe_count = sum(1 for f in quality_flags if f in _SEVERE_QUALITY_FLAGS)
        moderate_count = sum(1 for f in quality_flags if f in _MODERATE_QUALITY_FLAGS)
        flag_penalty = severe_count * 10 + moderate_count * 3

        score = contrib_score * 10 - flag_penalty
        scored.append((score, ev))

    scored.sort(key=lambda x: -x[0])
    return [ev for _, ev in scored[:3]]


def _build_combined_text(
    evidence_items: list[dict[str, Any]],
    actor: str,
    obj: str,
    workflow: str,
    pain_verb: str,
) -> str:
    """Build combined text from evidence for pattern matching."""
    parts: list[str] = []
    for ev in evidence_items:
        title = str(ev.get("title", ""))
        excerpt = str(ev.get("excerpt", ""))
        if title:
            parts.append(title)
        if excerpt and excerpt != title:
            parts.append(excerpt)

    # Add cluster field context
    parts.append(actor)
    parts.append(obj)
    parts.append(workflow)
    parts.append(pain_verb)

    return " ".join(parts).lower()


def _match_known_pattern(combined_text: str) -> str | None:
    """Try to match combined text against known pattern -> title map.

    Uses a scoring approach: each matching keyword gives +1. The pattern
    with the most matching keywords wins (break ties by order in the map).
    """
    best_score = 0
    best_title: str | None = None
    for keywords, title in _PATTERN_TITLE_MAP:
        score = sum(1 for kw in keywords if kw in combined_text)
        if score > best_score:
            best_score = score
            best_title = title
    return best_title


def _derive_from_components(
    actor: str,
    obj: str,
    workflow: str,
    pain_verb: str,
    pain_pattern: str,
) -> str | None:
    """Derive a title from actor + object + normalized pain phrase.

    Produces titles like: "Developers lack debugging context for agent traces"
    """
    # Map pain verbs to cleaner phrases
    pain_verb_map: dict[str, str] = {
        "cannot": "struggle with",
        "hard to": "struggle with",
        "hard to use": "struggle with",
        "hard to debug": "struggle to debug",
        "hard to understand": "struggle to understand",
        "broken": "experience broken",
        "too slow": "experience slow",
        "unreliable": "experience unreliable",
        "requires manual workaround": "need manual workarounds for",
        "too expensive": "find expensive",
        "missing": "lack",
        "not working": "experience broken",
        "confusing": "find confusing",
        "cannot integrate": "cannot integrate",
        "frustrating": "find frustrating",
        "painful": "find painful",
        "loses data": "lose data from",
    }

    # Map actors to readable labels
    actor_label_map: dict[str, str] = {
        "developer": "Developers",
        "founder": "Founders",
        "finance professional": "Finance professionals",
        "unknown": "Developers",
    }

    pv = pain_verb_map.get(pain_verb, "struggle with")
    al = actor_label_map.get(actor, actor.capitalize())

    # Build readable object phrase
    obj_clean = _clean_object_for_title(obj, workflow)

    if not obj_clean or obj_clean in ("unknown", "needs_more_evidence"):
        return f"{al} {pv} {workflow}"

    return f"{al} {pv} {obj_clean}"


def _clean_object_for_title(obj: str, workflow: str) -> str:
    """Clean object field for use in a title."""
    if obj == "unknown":
        # Use workflow as substitute
        wf = workflow.strip().lower()
        # Clean workflow of raw HN prefixes
        for prefix in _TITLE_PREFIXES_TO_STRIP:
            wf = wf.replace(prefix.lower(), "")
        wf = wf.strip().rstrip(".")
        if wf and wf not in ("unknown", "needs_more_evidence"):
            return wf[:60]
        return ""

    # Clean object of known noise
    obj_clean = obj.strip()
    # Remove long repo-like prefixes
    if obj_clean.startswith("github repository "):
        obj_clean = obj_clean[len("github repository "):]

    if not obj_clean or obj_clean in ("unknown", "needs_more_evidence"):
        return ""

    return obj_clean[:60]


def _best_evidence_title_cleaned(evidence_items: list[dict[str, Any]]) -> str:
    """Return the cleaned title from the best evidence item."""
    if not evidence_items:
        return ""
    best = evidence_items[0]
    title = str(best.get("title", ""))
    return _clean_raw_title(title)


def _clean_raw_title(raw_title: str) -> str:
    """Clean a raw evidence title for display.

    - Strip HN/GitHub prefixes like [Feature], Show HN:, etc.
    - Remove [dead] markers
    - Remove trailing junk
    - Collapse whitespace
    """
    title = raw_title.strip()
    if not title or title.lower() in _TITLE_PLACEHOLDERS:
        return ""

    # Remove known prefixes (case-insensitive)
    title_lower = title.lower()
    for prefix in _TITLE_PREFIXES_TO_STRIP:
        if title_lower.startswith(prefix.lower()):
            title = title[len(prefix):].strip()
            title_lower = title.lower()
            break

    # Remove [dead] anywhere
    title = title.replace("[dead]", "").replace("(dead)", "").strip()

    # Remove leading/trailing special chars
    title = title.strip(" :-.,;!?")

    if not title:
        return ""

    # Capitalize first letter
    title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()

    return title


def _clean_and_truncate(title: str, max_len: int = _MAX_TITLE_LENGTH) -> str:
    """Apply final cleaning and truncation to a generated title.

    - Fix malformed grammar patterns
    - Capitalize first letter
    - Truncate at word boundary
    """
    if not title:
        return "Unclear developer workflow pain"

    title = title.strip()

    # Fix malformed patterns
    for pattern, replacement in _MALFORMED_PATTERNS:
        title = title.replace(pattern, replacement)

    # Remove double spaces
    while "  " in title:
        title = title.replace("  ", " ")

    # Remove leading/trailing junk
    title = title.strip(" :-.,;!?")

    # Capitalize first letter
    if len(title) > 1:
        title = title[0].upper() + title[1:]

    # Truncate at word boundary
    if len(title) > max_len:
        # Try to break at last space before max_len
        cutoff = title.rfind(" ", 0, max_len)
        if cutoff > max_len // 2:
            title = title[:cutoff].strip()
        else:
            title = title[:max_len - 3].strip() + "..."

    return title if title else "Unclear developer workflow pain"


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
