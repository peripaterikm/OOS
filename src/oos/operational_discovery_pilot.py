from __future__ import annotations

"""Operational Discovery Pilot Orchestrator — deterministic fixture/input-driven pipeline.

Runs the bounded pipeline:
  RawEvidence -> CandidateSignals -> PainClusters -> SourceQualityReport
  -> FounderReviewPackage -> pilot run artifacts

Accepts explicit inputs only. No live APIs. No network. No LLM calls.
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pain_cluster_assembly import assemble_pain_clusters, normalize_evidence_source
from .pain_cluster_dedupe import (
    CANONICAL_SOURCE_IDS,
    CANONICAL_SOURCE_TYPES,
    normalize_source_id,
    normalize_source_type,
)
from .source_quality_report import (
    SourceQualityReport,
    build_source_quality_report,
    render_source_quality_report_markdown,
    validate_source_quality_report,
)
from .pilot_founder_review_package import (
    FounderReviewPackage,
    build_founder_review_package,
    render_founder_review_package_markdown,
    validate_founder_review_package,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Deferred source IDs that must be rejected during preflight
DEFERRED_SOURCE_IDS: frozenset[str] = frozenset({
    "product_hunt",
    "pimenov_ai",
    "reddit",
    "discord",
    "slack",
    "x_twitter",
    "twitter",
    "alternativeto",
    "yc",
    "crunchbase",
    "blogs",
    "newsletters",
    "app_marketplaces",
    "app_store",
    "google_play",
    "job_boards",
    "linkedin",
    "indeed",
})

# Source IDs requiring stretch mode
STRETCH_SOURCE_IDS: frozenset[str] = frozenset({
    "stack_exchange",
    "stack_overflow",
    "stackexchange",
})

# Default allowed source_ids
DEFAULT_ALLOWED_SOURCE_IDS: frozenset[str] = frozenset({
    "hacker_news",
    "github_issues",
})

# Allowed source_types
ALLOWED_SOURCE_TYPES: frozenset[str] = frozenset({
    "discussion",
    "issue_tracker",
})

# Artifact filenames
ARTIFACT_FILENAMES: tuple[str, ...] = (
    "raw_evidence.json",
    "candidate_signals.json",
    "pain_clusters.json",
    "source_quality_report.json",
    "source_quality_report.md",
    "founder_review_package.json",
    "founder_review_package.md",
    "validation_summary.json",
    "pilot_run_manifest.json",
)

OPTIONAL_ARTIFACT_FILENAMES: tuple[str, ...] = (
    "opportunity_candidates.json",
    "duplicates.json",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _build_run_id(created_at: str | None = None) -> str:
    """Build a deterministic pilot run ID.

    Format: pilot_run_YYYY-MM-DD_<8char_hex>
    """
    ts = created_at or _iso_utc_now()
    try:
        dt = datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        dt = datetime.now(timezone.utc)
    date_part = dt.strftime("%Y-%m-%d")
    hash_input = f"pilot_run_{ts}"
    hex_part = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:8]
    return f"pilot_run_{date_part}_{hex_part}"


def _is_valid_http_url(url: str) -> bool:
    """Return True if url starts with http:// or https://."""
    return url.startswith(("http://", "https://"))


def _is_placeholder_url(url: str) -> bool:
    """Return True if url is a placeholder (starts with urn:)."""
    return url.lower().startswith("urn:")


# Conservative pattern for safe discovery_run_id.
# Allows: letters, digits, underscore, dash, dot.
# Rejects: path separators, drive prefixes, absolute paths, "..", spaces, other special chars.
_SAFE_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def _is_safe_discovery_run_id(run_id: str) -> bool:
    """Return True if discovery_run_id is safe for filesystem path use.

    Rejects path separators (/ \\), parent references (..), drive prefixes
    (C:\\), absolute paths (/tmp/...), and any character outside the
    conservative set [a-zA-Z0-9_\\-.].
    """
    if not run_id:
        return False
    # Reject anything with path separators or parent traversal
    if "/" in run_id or "\\" in run_id or run_id.startswith("..") or ".." in run_id:
        return False
    # Reject absolute paths (Unix or Windows)
    if run_id.startswith("/") or (len(run_id) >= 2 and run_id[1] == ":"):
        return False
    return bool(_SAFE_RUN_ID_RE.fullmatch(run_id))


def _validate_discovery_run_id(run_id: str) -> list[str]:
    """Validate discovery_run_id for filesystem safety.

    Returns a list of error strings (empty if valid).
    """
    errors: list[str] = []
    if not run_id:
        errors.append("discovery_run_id is empty")
        return errors
    if "/" in run_id or "\\" in run_id:
        errors.append(
            f"discovery_run_id contains path separator: {run_id!r}"
        )
    if ".." in run_id:
        errors.append(
            f"discovery_run_id contains parent traversal: {run_id!r}"
        )
    if run_id.startswith("/") or (len(run_id) >= 2 and run_id[1] == ":"):
        errors.append(
            f"discovery_run_id looks like an absolute path or drive: {run_id!r}"
        )
    if not errors and not _SAFE_RUN_ID_RE.fullmatch(run_id):
        errors.append(
            f"discovery_run_id contains disallowed characters: {run_id!r}"
        )
    return errors


def _normalize_input_evidence(ev: dict[str, Any]) -> dict[str, Any]:
    """Normalize source_id/source_type on an evidence dict."""
    return normalize_evidence_source(ev)


def _validate_source_url(evidence: dict[str, Any]) -> list[str]:
    """Validate source_url on a single evidence dict. Returns list of error strings."""
    errors: list[str] = []
    url = str(evidence.get("source_url", "") or "").strip()
    ev_id = str(evidence.get("evidence_id", "?") or "?")

    if not url:
        errors.append(f"evidence[{ev_id}]: missing source_url")
    elif _is_placeholder_url(url):
        errors.append(f"evidence[{ev_id}]: placeholder URL ({url})")
    elif url.lower().startswith("github://"):
        errors.append(f"evidence[{ev_id}]: github:// fallback URL not allowed ({url})")
    elif not _is_valid_http_url(url):
        errors.append(f"evidence[{ev_id}]: non-http(s) URL ({url})")
    return errors


def _validate_source_scope(
    evidence_items: list[dict[str, Any]],
    *,
    stretch_allowed: bool = False,
    label: str = "evidence",
) -> tuple[list[str], list[str]]:
    """Validate that all evidence/candidate_signals come from allowed sources.

    Returns (errors, warnings).
    Unknown source_id/source_type are errors, not warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for ev in evidence_items:
        raw_sid = str(ev.get("source_id", "") or "")
        raw_stype = str(ev.get("source_type", "") or "")
        sid = normalize_source_id(raw_sid)
        stype = normalize_source_type(raw_stype)
        item_id = ev.get("evidence_id") or ev.get("signal_id") or "?"

        if sid in DEFERRED_SOURCE_IDS:
            errors.append(
                f"{label}[{item_id}]: "
                f"deferred source '{sid}' is not allowed in pilot"
            )
            continue

        if sid in STRETCH_SOURCE_IDS:
            if not stretch_allowed:
                errors.append(
                    f"{label}[{item_id}]: "
                    f"stretch source '{sid}' requires stretch_allowed=True"
                )
            continue

        # Unknown source_id is an error, not a warning
        if sid and sid not in DEFAULT_ALLOWED_SOURCE_IDS:
            errors.append(
                f"{label}[{item_id}]: "
                f"unknown source_id '{raw_sid}' (normalized: '{sid}') — not in default allowed set"
            )

        # Unknown source_type is an error, not a warning
        if stype and stype not in ALLOWED_SOURCE_TYPES:
            errors.append(
                f"{label}[{item_id}]: "
                f"unknown source_type '{raw_stype}' (normalized: '{stype}') — not in allowed types"
            )

    return errors, warnings


def _derive_minimal_candidate_signals(
    evidence_items: list[dict[str, Any]],
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    """Derive minimal candidate-signal-like records from raw evidence.

    Deterministic only. Does NOT implement LLM classification.
    Maps available fields from evidence to candidate-signal fields.

    Propagates quality_flags from evidence so that noise classification
    can act on them downstream in Source Quality Report.
    """
    ts = created_at or _iso_utc_now()
    candidates: list[dict[str, Any]] = []

    for i, ev in enumerate(evidence_items):
        ev_norm = _normalize_input_evidence(ev)
        ev_id = str(ev_norm.get("evidence_id", ""))
        sid = normalize_source_id(str(ev_norm.get("source_id", "")))
        stype = normalize_source_type(str(ev_norm.get("source_type", "")))
        source_url = str(ev_norm.get("source_url", ""))
        title = str(ev_norm.get("title", "") or "")
        body = str(ev_norm.get("body", "") or "")

        # Derive signal_type from evidence_kind if available
        evidence_kind = str(ev_norm.get("evidence_kind", "") or "").lower()
        signal_type_map: dict[str, str] = {
            "pain_signal_candidate": "pain_signal",
            "bug_report": "pain_signal",
            "complaint": "pain_signal",
            "feature_request": "pain_signal",
            "integration_pain": "pain_signal",
            "performance_pain": "pain_signal",
            "ux_pain": "pain_signal",
            "documentation_gap": "pain_signal",
            "workaround": "workaround",
        }
        signal_type = signal_type_map.get(evidence_kind, "pain_signal")

        # Derive pain_summary from title or pain_summary metadata
        pain_summary = str(ev_norm.get("pain_summary", "") or "")
        if not pain_summary:
            pain_summary = title[:200] if title else f"Evidence from {sid}"

        # Derive target_user from metadata
        raw_meta = ev_norm.get("raw_metadata") or {}
        if isinstance(raw_meta, dict):
            target_user = str(raw_meta.get("target_user", "") or "")
        else:
            target_user = ""
        if not target_user:
            target_user = "unknown"

        # Propagate quality_flags from evidence for noise classification downstream
        quality_flags = list(ev_norm.get("quality_flags", []) or [])

        # Build signal_id
        sig_key = f"{ev_id}|{signal_type}|{sid}|{ts}"
        sig_hash = hashlib.sha256(sig_key.encode("utf-8")).hexdigest()[:12]
        signal_id = f"cs_{sig_hash}"

        candidate = {
            "signal_id": signal_id,
            "evidence_id": ev_id,
            "source_id": sid,
            "source_type": stype,
            "source_url": source_url,
            "topic_id": str(ev_norm.get("topic_id", "pilot_v2_12") or "pilot_v2_12"),
            "query_kind": str(ev_norm.get("query_kind", "pilot_fixture") or "pilot_fixture"),
            "signal_type": signal_type,
            "pain_summary": pain_summary,
            "target_user": target_user,
            "current_workaround": str(ev_norm.get("current_workaround", "") or ""),
            "buying_intent_hint": "",
            "urgency_hint": "",
            "confidence": 0.5,
            "measurement_methods": {},
            "extraction_mode": "deterministic_pilot",
            "classification": signal_type,
            "classification_confidence": 0.5,
            "traceability": {
                "source_url": source_url,
                "evidence_id": ev_id,
            },
            "scoring_model_version": "",
            "scoring_breakdown": {},
            "quality_flags": quality_flags,
            "evidence_kind": evidence_kind,
            "title": title,
            "body": body,
            "excerpt": str(ev_norm.get("excerpt", "") or ""),
            "_derived": True,
        }
        candidates.append(candidate)

    return candidates


def _to_json_lines(obj: Any) -> str:
    """Serialize to JSON with deterministic formatting."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PilotRunValidationResult:
    """Validation summary for a pilot run."""

    is_valid: bool = True
    preflight_passed: bool = True
    source_scope_errors: list[str] = field(default_factory=list)
    source_scope_warnings: list[str] = field(default_factory=list)
    url_validation_errors: list[str] = field(default_factory=list)
    cluster_traceability_errors: list[str] = field(default_factory=list)
    cluster_traceability_warnings: list[str] = field(default_factory=list)
    source_quality_validation: dict[str, Any] = field(default_factory=dict)
    founder_review_validation: dict[str, Any] = field(default_factory=dict)
    general_errors: list[str] = field(default_factory=list)
    general_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "preflight_passed": self.preflight_passed,
            "source_scope_errors": list(self.source_scope_errors),
            "source_scope_warnings": list(self.source_scope_warnings),
            "url_validation_errors": list(self.url_validation_errors),
            "cluster_traceability_errors": list(self.cluster_traceability_errors),
            "cluster_traceability_warnings": list(self.cluster_traceability_warnings),
            "source_quality_validation": dict(self.source_quality_validation),
            "founder_review_validation": dict(self.founder_review_validation),
            "general_errors": list(self.general_errors),
            "general_warnings": list(self.general_warnings),
        }


@dataclass
class OperationalDiscoveryPilotInput:
    """Input container for the operational discovery pilot orchestrator."""

    raw_evidence: list[dict[str, Any]] = field(default_factory=list)
    candidate_signals: list[dict[str, Any]] | None = None
    opportunity_candidates: list[dict[str, Any]] | None = None
    source_local_summaries: dict[str, dict[str, Any]] | None = None
    discovery_run_id: str | None = None
    created_at: str | None = None
    output_dir: str | None = None
    max_review_items: int = 10
    stretch_allowed: bool = False


@dataclass
class OperationalDiscoveryPilotResult:
    """Output container for the operational discovery pilot orchestrator."""

    discovery_run_id: str
    created_at: str
    raw_evidence: list[dict[str, Any]] = field(default_factory=list)
    raw_evidence_count: int = 0
    candidate_signals: list[dict[str, Any]] = field(default_factory=list)
    candidate_signal_count: int = 0
    pain_clusters: list[dict[str, Any]] = field(default_factory=list)
    pain_cluster_count: int = 0
    duplicates: list[dict[str, Any]] = field(default_factory=list)
    assembly_summary: dict[str, Any] = field(default_factory=dict)
    opportunity_candidates: list[dict[str, Any]] = field(default_factory=list)
    opportunity_candidate_count: int = 0
    source_quality_report: dict[str, Any] | None = None
    founder_review_package: dict[str, Any] | None = None
    validation_summary: dict[str, Any] = field(default_factory=dict)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    is_valid: bool = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_pilot_run_id(created_at: str | None = None) -> str:
    """Generate a deterministic pilot run ID.

    Format: pilot_run_YYYY-MM-DD_<8char_hex>

    Args:
        created_at: ISO 8601 timestamp. If None, uses UTC now.

    Returns:
        Run ID string.
    """
    return _build_run_id(created_at)


def run_operational_discovery_pilot(
    input: OperationalDiscoveryPilotInput,
) -> OperationalDiscoveryPilotResult:
    """Run the full operational discovery pilot pipeline.

    Accepts explicit, bounded inputs only. No live APIs. No network. No LLM.

    Pipeline phases:
    1. Preflight (source scope validation)
    2. Raw evidence validation (URL checks)
    3. Candidate signal handling
    4. PainCluster assembly
    5. Source Quality Report
    6. Founder Review Package
    7. Validation
    8. Artifact writing (if output_dir supplied)

    Args:
        input: OperationalDiscoveryPilotInput with raw_evidence and optional
            candidate_signals, opportunity_candidates, etc.

    Returns:
        OperationalDiscoveryPilotResult with all pipeline outputs.
    """
    created_at = input.created_at or _iso_utc_now()
    discovery_run_id = input.discovery_run_id or _build_run_id(created_at)

    # Validate discovery_run_id for path traversal safety (Fix 3)
    run_id_errors = _validate_discovery_run_id(discovery_run_id)
    if run_id_errors and input.output_dir:
        raise ValueError(
            f"Invalid discovery_run_id for artifact writing: {'; '.join(run_id_errors)}"
        )

    errors: list[str] = []
    warnings: list[str] = []
    all_url_errors: list[str] = []

    # ---- Normalize raw evidence ----
    raw_evidence = [_normalize_input_evidence(ev) for ev in input.raw_evidence]
    raw_evidence_count = len(raw_evidence)

    # ---------------------------------------------------------------
    # Phase 1: Preflight — Source Scope Validation
    # ---------------------------------------------------------------
    scope_errors, scope_warnings = _validate_source_scope(
        raw_evidence,
        stretch_allowed=input.stretch_allowed,
    )
    preflight_passed = len(scope_errors) == 0
    if scope_errors:
        errors.extend(scope_errors)
    if scope_warnings:
        warnings.extend(scope_warnings)

    # ---------------------------------------------------------------
    # Phase 2: Raw Evidence Validation — URL checks
    # ---------------------------------------------------------------
    for ev in raw_evidence:
        url_errs = _validate_source_url(ev)
        if url_errs:
            all_url_errors.extend(url_errs)
    if all_url_errors:
        errors.extend(all_url_errors)

    # ---------------------------------------------------------------
    # Phase 3: Candidate Signal Handling
    # ---------------------------------------------------------------
    if input.candidate_signals is not None:
        candidate_signals = [
            _normalize_input_evidence(sig) for sig in input.candidate_signals
        ]
        # Validate source scope on candidate_signals (Fix 1: candidate_signals scope)
        cand_scope_errors, cand_scope_warnings = _validate_source_scope(
            candidate_signals,
            stretch_allowed=input.stretch_allowed,
            label="candidate_signal",
        )
        if cand_scope_errors:
            errors.extend(cand_scope_errors)
            scope_errors.extend(cand_scope_errors)
            preflight_passed = False
        if cand_scope_warnings:
            scope_warnings.extend(cand_scope_warnings)
        # Validate source URLs in candidate signals too
        for sig in candidate_signals:
            url_errs = _validate_source_url(sig)
            if url_errs:
                all_url_errors.extend(url_errs)
    else:
        candidate_signals = _derive_minimal_candidate_signals(
            raw_evidence, created_at=created_at
        )
        # Add derived signals to raw evidence as a note; they inherit URLs
    candidate_signal_count = len(candidate_signals)

    # ---------------------------------------------------------------
    # Phase 4: PainCluster Assembly
    # ---------------------------------------------------------------
    # Combine raw_evidence and candidate_signals into evidence_items for assembly
    evidence_for_assembly: list[dict[str, Any]] = []
    evidence_for_assembly.extend(raw_evidence)

    # Merge candidate signal fields into evidence items for assembly
    for sig in candidate_signals:
        ev_id = str(sig.get("evidence_id", ""))
        # Check if this evidence is already in the list
        found = False
        for ev in evidence_for_assembly:
            if str(ev.get("evidence_id", "")) == ev_id:
                # Augment with signal fields
                if not ev.get("signal_id"):
                    ev["signal_id"] = sig.get("signal_id", "")
                if not ev.get("pain_summary"):
                    ev["pain_summary"] = sig.get("pain_summary", "")
                if not ev.get("target_user"):
                    ev["target_user"] = sig.get("target_user", "")
                found = True
                break
        if not found:
            # Add as standalone evidence entry; fill required assembly fields
            # with sensible defaults so downstream assembly does not crash
            standalone = dict(sig)
            standalone.setdefault("title", str(sig.get("pain_summary", "") or sig.get("source_id", "untitled")))
            standalone.setdefault("evidence_kind", "pain_signal_candidate")
            standalone.setdefault("created_at", str(sig.get("created_at", "") or created_at))
            standalone.setdefault("fetched_at", str(sig.get("fetched_at", "") or created_at))
            standalone.setdefault("excerpt", str(sig.get("pain_summary", "") or sig.get("title", "") or ""))
            standalone.setdefault("contribution_to_cluster", "primary")
            standalone.setdefault("body", "")
            standalone.setdefault("quality_flags", [])
            evidence_for_assembly.append(standalone)

    try:
        clusters, duplicates, assembly_summary = assemble_pain_clusters(
            evidence_for_assembly, dedupe=True
        )
    except Exception as exc:
        errors.append(f"PainCluster assembly failed: {type(exc).__name__}: {exc}")
        clusters = []
        duplicates = []
        assembly_summary = {"error": str(exc)}

    pain_cluster_dicts = [pc.to_dict() for pc in clusters]
    pain_cluster_count = len(pain_cluster_dicts)

    # ---------------------------------------------------------------
    # Phase 5: Source Quality Report
    # ---------------------------------------------------------------

    # Combine evidence items enriched with candidate signal info
    evidence_for_report = list(raw_evidence)
    for sig in candidate_signals:
        # Merge candidate signal classification into evidence for report metrics
        ev_id = str(sig.get("evidence_id", ""))
        found = False
        for ev in evidence_for_report:
            if str(ev.get("evidence_id", "")) == ev_id:
                if not ev.get("classification"):
                    ev["classification"] = sig.get("classification", "")
                if not ev.get("signal_type"):
                    ev["signal_type"] = sig.get("signal_type", "pain_signal")
                found = True
                break
        if not found:
            evidence_for_report.append(dict(sig))

    opp_candidates = list(input.opportunity_candidates or [])

    sqr = build_source_quality_report(
        evidence_items=evidence_for_report,
        candidate_signals=candidate_signals,
        pain_clusters=pain_cluster_dicts,
        opportunity_candidates=opp_candidates,
        source_summaries=input.source_local_summaries,
        discovery_run_id=discovery_run_id,
        created_at=created_at,
    )
    sqr_dict = sqr.to_dict()

    sqr_validation = validate_source_quality_report(sqr)
    sqr_valid_dict = sqr_validation.to_dict()

    # ---------------------------------------------------------------
    # Phase 6: Founder Review Package
    # ---------------------------------------------------------------
    frp = build_founder_review_package(
        pain_clusters=pain_cluster_dicts,
        opportunity_candidates=opp_candidates,
        source_quality_report=sqr,
        discovery_run_id=discovery_run_id,
        created_at=created_at,
        max_items=input.max_review_items,
    )
    frp_dict = frp.to_dict()

    frp_validation = validate_founder_review_package(frp)
    frp_valid_dict = frp_validation.to_dict()

    # ---------------------------------------------------------------
    # Phase 7: Validation
    # ---------------------------------------------------------------
    cluster_traceability_errors: list[str] = []
    cluster_traceability_warnings: list[str] = []

    # Validate traceability in pain clusters
    for pc in pain_cluster_dicts:
        for i, entry in enumerate(pc.get("source_evidence_list", [])):
            url = str(entry.get("source_url", "") or "").strip()
            ev_id = entry.get("evidence_id", "?")
            if not url:
                cluster_traceability_errors.append(
                    f"cluster[{pc.get('cluster_id', '?')}].evidence[{i}] "
                    f"(id={ev_id}): missing source_url"
                )
            elif _is_placeholder_url(url):
                cluster_traceability_errors.append(
                    f"cluster[{pc.get('cluster_id', '?')}].evidence[{i}] "
                    f"(id={ev_id}): placeholder URL ({url})"
                )
            elif not _is_valid_http_url(url):
                cluster_traceability_errors.append(
                    f"cluster[{pc.get('cluster_id', '?')}].evidence[{i}] "
                    f"(id={ev_id}): non-http(s) URL ({url})"
                )

    # Gather all validation errors
    all_errors = list(errors)
    if not sqr_valid_dict.get("is_valid", True):
        all_errors.extend(sqr_valid_dict.get("errors", []))
    if not frp_valid_dict.get("is_valid", True):
        all_errors.extend(frp_valid_dict.get("errors", []))
    all_errors.extend(cluster_traceability_errors)

    all_warnings = list(warnings)
    all_warnings.extend(sqr_valid_dict.get("warnings", []))
    all_warnings.extend(frp_valid_dict.get("warnings", []))
    all_warnings.extend(cluster_traceability_warnings)

    is_valid = (
        preflight_passed
        and len(all_url_errors) == 0
        and len(cluster_traceability_errors) == 0
        and sqr_valid_dict.get("is_valid", True)
        and frp_valid_dict.get("is_valid", True)
    )

    validation_summary = PilotRunValidationResult(
        is_valid=is_valid,
        preflight_passed=preflight_passed,
        source_scope_errors=scope_errors,
        source_scope_warnings=scope_warnings,
        url_validation_errors=all_url_errors,
        cluster_traceability_errors=cluster_traceability_errors,
        cluster_traceability_warnings=cluster_traceability_warnings,
        source_quality_validation=sqr_valid_dict,
        founder_review_validation=frp_valid_dict,
        general_errors=[e for e in all_errors if e not in scope_errors and e not in all_url_errors and e not in cluster_traceability_errors],
        general_warnings=all_warnings,
    )

    # ---------------------------------------------------------------
    # Phase 8: Artifact Writing (only if output_dir supplied)
    # ---------------------------------------------------------------
    artifact_paths: dict[str, str] = {}
    if input.output_dir:
        run_dir = Path(input.output_dir) / discovery_run_id
        artifact_paths = _write_artifacts(
            run_dir=run_dir,
            discovery_run_id=discovery_run_id,
            created_at=created_at,
            raw_evidence=raw_evidence,
            candidate_signals=candidate_signals,
            pain_clusters=pain_cluster_dicts,
            duplicates=duplicates,
            source_quality_report=sqr,
            founder_review_package=frp,
            validation_summary=validation_summary,
            opportunity_candidates=opp_candidates,
            warnings=all_warnings,
            errors=all_errors,
        )

    return OperationalDiscoveryPilotResult(
        discovery_run_id=discovery_run_id,
        created_at=created_at,
        raw_evidence=raw_evidence,
        raw_evidence_count=raw_evidence_count,
        candidate_signals=candidate_signals,
        candidate_signal_count=candidate_signal_count,
        pain_clusters=pain_cluster_dicts,
        pain_cluster_count=pain_cluster_count,
        duplicates=duplicates,
        assembly_summary=assembly_summary,
        opportunity_candidates=opp_candidates,
        opportunity_candidate_count=len(opp_candidates),
        source_quality_report=sqr_dict,
        founder_review_package=frp_dict,
        validation_summary=validation_summary.to_dict(),
        artifact_paths=artifact_paths,
        warnings=all_warnings,
        errors=all_errors,
        is_valid=is_valid,
    )


def validate_pilot_run_result(
    result: OperationalDiscoveryPilotResult,
) -> PilotRunValidationResult:
    """Validate a pilot run result post-hoc.

    Returns a PilotRunValidationResult.
    """
    return PilotRunValidationResult(
        is_valid=result.is_valid,
        preflight_passed=result.validation_summary.get("preflight_passed", False),
        source_scope_errors=result.validation_summary.get("source_scope_errors", []),
        source_scope_warnings=result.validation_summary.get("source_scope_warnings", []),
        url_validation_errors=result.validation_summary.get("url_validation_errors", []),
        cluster_traceability_errors=result.validation_summary.get("cluster_traceability_errors", []),
        cluster_traceability_warnings=result.validation_summary.get("cluster_traceability_warnings", []),
        source_quality_validation=result.validation_summary.get("source_quality_validation", {}),
        founder_review_validation=result.validation_summary.get("founder_review_validation", {}),
        general_errors=result.validation_summary.get("general_errors", []),
        general_warnings=result.validation_summary.get("general_warnings", []),
    )


def write_pilot_run_artifacts(
    result: OperationalDiscoveryPilotResult,
    output_dir: str | Path,
) -> dict[str, str]:
    """Write pilot run artifacts to the specified output directory.

    Only writes if result has artifact data. Uses the result's discovery_run_id
    as the subdirectory name.

    Args:
        result: OperationalDiscoveryPilotResult from a prior run.
        output_dir: Base directory for pilot run output.

    Returns:
        Dict mapping artifact name to written file path.
    """
    # Validate discovery_run_id for path traversal safety (Fix 3)
    run_id_errors = _validate_discovery_run_id(result.discovery_run_id)
    if run_id_errors:
        raise ValueError(
            f"Invalid discovery_run_id for post-hoc artifact writing: "
            f"{'; '.join(run_id_errors)}"
        )

    run_dir = Path(output_dir) / result.discovery_run_id

    # Reconstruct objects from dicts for writing
    sqr = None
    if result.source_quality_report:
        sqr = SourceQualityReport.from_dict(result.source_quality_report)

    frp = None
    if result.founder_review_package:
        frp = FounderReviewPackage.from_dict(result.founder_review_package)

    # Reconstruct validation summary from result dict, avoiding key conflicts
    vs_dict = dict(result.validation_summary or {})
    vs_dict.pop("is_valid", None)  # will be set explicitly below
    vs = PilotRunValidationResult(
        is_valid=result.is_valid,
        **vs_dict
    )

    return _write_artifacts(
        run_dir=run_dir,
        discovery_run_id=result.discovery_run_id,
        created_at=result.created_at,
        raw_evidence=result.raw_evidence,
        candidate_signals=result.candidate_signals,
        pain_clusters=result.pain_clusters,
        duplicates=result.duplicates,
        source_quality_report=sqr,
        founder_review_package=frp,
        validation_summary=vs,
        opportunity_candidates=result.opportunity_candidates,
        warnings=result.warnings,
        errors=result.errors,
    )


# ---------------------------------------------------------------------------
# Internal artifact writer
# ---------------------------------------------------------------------------


def _write_artifacts(
    *,
    run_dir: Path,
    discovery_run_id: str,
    created_at: str,
    raw_evidence: list[dict[str, Any]],
    candidate_signals: list[dict[str, Any]],
    pain_clusters: list[dict[str, Any]],
    duplicates: list[dict[str, Any]],
    source_quality_report: SourceQualityReport | None,
    founder_review_package: FounderReviewPackage | None,
    validation_summary: PilotRunValidationResult,
    opportunity_candidates: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, str]:
    """Write all pilot run artifacts to disk. Returns mapping of artifact name to path."""
    run_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}

    # raw_evidence.json
    raw_evidence_path = run_dir / "raw_evidence.json"
    raw_evidence_path.write_text(
        _to_json_lines(raw_evidence), encoding="utf-8"
    )
    paths["raw_evidence"] = str(raw_evidence_path)

    # candidate_signals.json
    cs_path = run_dir / "candidate_signals.json"
    cs_path.write_text(
        _to_json_lines(candidate_signals), encoding="utf-8"
    )
    paths["candidate_signals"] = str(cs_path)

    # pain_clusters.json
    pc_path = run_dir / "pain_clusters.json"
    pc_path.write_text(
        _to_json_lines(pain_clusters), encoding="utf-8"
    )
    paths["pain_clusters"] = str(pc_path)

    # duplicates.json (optional)
    if duplicates:
        dup_path = run_dir / "duplicates.json"
        dup_path.write_text(
            _to_json_lines(duplicates), encoding="utf-8"
        )
        paths["duplicates"] = str(dup_path)

    # opportunity_candidates.json (optional)
    if opportunity_candidates:
        oc_path = run_dir / "opportunity_candidates.json"
        oc_path.write_text(
            _to_json_lines(opportunity_candidates), encoding="utf-8"
        )
        paths["opportunity_candidates"] = str(oc_path)

    # source_quality_report.json + .md
    if source_quality_report:
        sqr_json = run_dir / "source_quality_report.json"
        sqr_md = run_dir / "source_quality_report.md"
        sqr_json.write_text(
            _to_json_lines(source_quality_report.to_dict()), encoding="utf-8"
        )
        sqr_md.write_text(
            render_source_quality_report_markdown(source_quality_report) + "\n",
            encoding="utf-8",
        )
        paths["source_quality_report"] = str(sqr_json)
        paths["source_quality_report_md"] = str(sqr_md)

    # founder_review_package.json + .md
    if founder_review_package:
        frp_json = run_dir / "founder_review_package.json"
        frp_md = run_dir / "founder_review_package.md"
        frp_json.write_text(
            _to_json_lines(founder_review_package.to_dict()), encoding="utf-8"
        )
        frp_md.write_text(
            render_founder_review_package_markdown(founder_review_package) + "\n",
            encoding="utf-8",
        )
        paths["founder_review_package"] = str(frp_json)
        paths["founder_review_package_md"] = str(frp_md)

    # validation_summary.json
    vs_path = run_dir / "validation_summary.json"
    vs_path.write_text(
        _to_json_lines(validation_summary.to_dict()), encoding="utf-8"
    )
    paths["validation_summary"] = str(vs_path)

    # pilot_run_manifest.json
    manifest: dict[str, Any] = {
        "artifact_type": "pilot_run_manifest",
        "discovery_run_id": discovery_run_id,
        "created_at": created_at,
        "raw_evidence_count": len(raw_evidence),
        "candidate_signal_count": len(candidate_signals),
        "pain_cluster_count": len(pain_clusters),
        "opportunity_candidate_count": len(opportunity_candidates or []),
        "duplicate_count": len(duplicates),
        "warnings": list(warnings or []),
        "errors": list(errors or []),
        "is_valid": validation_summary.is_valid,
        "artifact_paths": {k: str(v) for k, v in paths.items()},
    }
    manifest_path = run_dir / "pilot_run_manifest.json"
    manifest_path.write_text(
        _to_json_lines(manifest), encoding="utf-8"
    )
    paths["pilot_run_manifest"] = str(manifest_path)

    return paths
