"""Source URL traceability contract — deterministic advisory validation layer.

Roadmap v2.7 item 1.1. Defines models, helpers, and a scanner to verify
that every artifact in the v2.6+ weekly loop carries real ``source_urls``
and that placeholder URNs (``urn:oos:*``) are detected as traceability gaps.

This module is **contract / advisory only**. It does NOT:
- change source URL propagation in any pipeline module,
- modify FounderInboxReviewItem, FounderDecisionImport, or any other schema,
- write artifacts,
- call live APIs or LLMs.

What it does:
- Document the canonical source URL traceability path.
- Detect placeholder URNs, missing source URLs, and malformed URLs.
- Exempt explicitly insufficient-evidence artifacts.
- Produce a deterministic ``SourceURLTraceabilityReport`` with structured issues.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_URL_TRACEABILITY_SCHEMA_VERSION = "source_url_traceability.v1"

# Placeholder URN patterns to detect
_PLACEHOLDER_URN_RE = re.compile(r"^urn:oos:", re.IGNORECASE)
# Real URL patterns: http/https only
_REAL_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
# Malformed: scheme followed by // but no actual hostname, or scheme-only
_MALFORMED_URL_RE = re.compile(r"^https?:(//)?$")

# Canonical artifact keys (from weekly_run_manifest.py) that carry source_urls
_CANONICAL_SOURCE_URL_KEYS: tuple[str, ...] = (
    "evidence_packs",
    "opportunity_candidates",
    "quality_gate_decisions",
    "founder_decisions_v2",
    "founder_feedback_mappings",
    "founder_inbox_v2_index",
)

# Per-artifact field paths where source_urls / linked_source_urls live
_ARTIFACT_SOURCE_URL_FIELD_PATHS: dict[str, str] = {
    "evidence_packs": "items[].source_urls",
    "opportunity_candidates": "items[].source_urls",
    "quality_gate_decisions": "items[].source_urls",
    "founder_decisions_v2": "items[].linked_source_urls",
    "founder_feedback_mappings": "items[].source_urls",
    "founder_inbox_v2_index": "review_items[].linked_source_urls",
}

# Per-artifact list item key name
_ARTIFACT_ITEMS_KEY: dict[str, str] = {
    "evidence_packs": "items",
    "opportunity_candidates": "items",
    "quality_gate_decisions": "items",
    "founder_decisions_v2": "items",
    "founder_feedback_mappings": "items",
    "founder_inbox_v2_index": "review_items",
}

# Per-artifact item ID field name
_ARTIFACT_ITEM_ID_KEY: dict[str, str] = {
    "evidence_packs": "evidence_pack_id",
    "opportunity_candidates": "opportunity_id",
    "quality_gate_decisions": "gate_result_id",
    "founder_decisions_v2": "decision_id",
    "founder_feedback_mappings": "feedback_mapping_id",
    "founder_inbox_v2_index": "review_item_id",
}

# Filenames mapping (subset of weekly_run_manifest canonical paths)
_ARTIFACT_FILENAMES: dict[str, str] = {
    "evidence_packs": "evidence_packs.json",
    "opportunity_candidates": "opportunity_candidates.json",
    "quality_gate_decisions": "quality_gate_decisions.json",
    "founder_decisions_v2": "founder_decisions_v2.json",
    "founder_feedback_mappings": "founder_feedback_mappings.json",
    "founder_inbox_v2_index": "founder_inbox_v2_index.json",
}

# Evidence-pack-specific constant matching evidence_pack.py
_INSUFFICIENT_EVIDENCE_MARKER = "insufficient_evidence"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceURLTraceabilityIssue:
    """A single issue found during source URL traceability validation."""

    issue_id: str
    artifact_key: str
    artifact_path: str
    item_id: str
    field_path: str
    issue_type: str  # placeholder_source_url | missing_source_url | malformed_source_url | unsupported_artifact
    source_url_value: str
    severity: str  # error | warning
    explanation: str
    advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "artifact_key": self.artifact_key,
            "artifact_path": self.artifact_path,
            "item_id": self.item_id,
            "field_path": self.field_path,
            "issue_type": self.issue_type,
            "source_url_value": self.source_url_value,
            "severity": self.severity,
            "explanation": self.explanation,
            "advisory_only": self.advisory_only,
        }


@dataclass(frozen=True)
class SourceURLTraceabilityArtifactStatus:
    """Status of source URL traceability for one artifact type in a run."""

    artifact_key: str
    artifact_path: str
    present: bool = False
    parseable: bool = False
    item_count: int = 0
    items_with_placeholder_urls: int = 0
    items_with_missing_source_urls: int = 0
    items_with_malformed_source_urls: int = 0
    items_exempt_insufficient_evidence: int = 0
    issues: list[SourceURLTraceabilityIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_key": self.artifact_key,
            "artifact_path": self.artifact_path,
            "present": self.present,
            "parseable": self.parseable,
            "item_count": self.item_count,
            "items_with_placeholder_urls": self.items_with_placeholder_urls,
            "items_with_missing_source_urls": self.items_with_missing_source_urls,
            "items_with_malformed_source_urls": self.items_with_malformed_source_urls,
            "items_exempt_insufficient_evidence": self.items_exempt_insufficient_evidence,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class SourceURLTraceabilityReport:
    """Canonical source URL traceability report for one weekly run."""

    schema_version: str = SOURCE_URL_TRACEABILITY_SCHEMA_VERSION
    run_dir: str = ""
    checked_at: str = ""
    artifact_statuses: list[SourceURLTraceabilityArtifactStatus] = field(default_factory=list)
    issues: list[SourceURLTraceabilityIssue] = field(default_factory=list)
    issue_count: int = 0
    placeholder_url_count: int = 0
    missing_source_url_count: int = 0
    exempt_insufficient_evidence_count: int = 0
    malformed_url_count: int = 0
    artifacts_checked: int = 0
    validation_passed: bool = False
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_dir": self.run_dir,
            "checked_at": self.checked_at,
            "artifact_statuses": [s.to_dict() for s in self.artifact_statuses],
            "issues": [i.to_dict() for i in self.issues],
            "issue_count": self.issue_count,
            "placeholder_url_count": self.placeholder_url_count,
            "missing_source_url_count": self.missing_source_url_count,
            "exempt_insufficient_evidence_count": self.exempt_insufficient_evidence_count,
            "malformed_url_count": self.malformed_url_count,
            "artifacts_checked": self.artifacts_checked,
            "validation_passed": self.validation_passed,
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# Placeholder / URL helpers
# ---------------------------------------------------------------------------


def is_placeholder_source_url(value: str) -> bool:
    """Return True if ``value`` is a placeholder URN (``urn:oos:*``)."""
    if not isinstance(value, str) or not value.strip():
        return False
    return bool(_PLACEHOLDER_URN_RE.match(value.strip()))


def is_real_source_url(value: str) -> bool:
    """Return True if ``value`` is a real http/https URL."""
    if not isinstance(value, str) or not value.strip():
        return False
    return bool(_REAL_URL_RE.match(value.strip()))


def is_malformed_source_url(value: str) -> bool:
    """Return True if ``value`` looks like a URL but is structurally broken."""
    if not isinstance(value, str) or not value.strip():
        return False
    stripped = value.strip()
    # Must start with http: or https: but not followed by //
    if _MALFORMED_URL_RE.match(stripped):
        return True
    # Empty scheme-like strings
    if stripped in ("http:", "https:", "http://", "https://"):
        return True
    return False


def collect_source_urls_from_artifact(
    artifact_data: dict[str, Any],
    artifact_key: str,
) -> list[str]:
    """Collect all source_url/linked_source_url values from an artifact dict.

    Returns a deduplicated, ordered list of source URL strings found across
    all items in the artifact.
    """
    urls: list[str] = []
    field_path = _ARTIFACT_SOURCE_URL_FIELD_PATHS.get(artifact_key, "")
    if not field_path:
        return urls

    # Determine the field name within each item
    if "linked_source_urls" in field_path:
        url_field = "linked_source_urls"
    else:
        url_field = "source_urls"

    items_key = _ARTIFACT_ITEMS_KEY.get(artifact_key, "items")
    items = artifact_data.get(items_key, [])
    if not isinstance(items, list):
        return urls

    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        item_urls = item.get(url_field, [])
        if isinstance(item_urls, list):
            for u in item_urls:
                if isinstance(u, str) and u.strip() and u.strip() not in seen:
                    urls.append(u.strip())
                    seen.add(u.strip())

    return urls


# ---------------------------------------------------------------------------
# Artifact-level scanner
# ---------------------------------------------------------------------------


def _make_issue_id(artifact_key: str, item_id: str, issue_type: str, idx: int) -> str:
    """Deterministic issue ID from hash of composite key."""
    seed = f"{artifact_key}|{item_id}|{issue_type}|{idx}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"src_url_{digest}"


def _is_insufficient_evidence_item(item: dict[str, Any], artifact_key: str) -> bool:
    """Check if an evidence pack item is marked as insufficient evidence."""
    if artifact_key != "evidence_packs":
        return False
    created_from = str(item.get("created_from", ""))
    return created_from == _INSUFFICIENT_EVIDENCE_MARKER


def _check_artifact_source_urls(
    run_dir: Path,
    artifact_key: str,
) -> SourceURLTraceabilityArtifactStatus:
    """Scan one artifact file for source URL traceability issues."""
    filename = _ARTIFACT_FILENAMES.get(artifact_key, "")
    artifact_path = run_dir / filename

    if not artifact_path.is_file():
        return SourceURLTraceabilityArtifactStatus(
            artifact_key=artifact_key,
            artifact_path=str(artifact_path),
            present=False,
        )

    # Parse JSON
    try:
        raw = artifact_path.read_text(encoding="utf-8-sig")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        issue = SourceURLTraceabilityIssue(
            issue_id=_make_issue_id(artifact_key, "", "unsupported_artifact", 0),
            artifact_key=artifact_key,
            artifact_path=str(artifact_path),
            item_id="",
            field_path="",
            issue_type="unsupported_artifact",
            source_url_value="",
            severity="error",
            explanation=f"Malformed JSON in artifact: {exc.msg}",
        )
        return SourceURLTraceabilityArtifactStatus(
            artifact_key=artifact_key,
            artifact_path=str(artifact_path),
            present=True,
            parseable=False,
            issues=[issue],
        )

    if not isinstance(data, dict):
        issue = SourceURLTraceabilityIssue(
            issue_id=_make_issue_id(artifact_key, "", "unsupported_artifact", 0),
            artifact_key=artifact_key,
            artifact_path=str(artifact_path),
            item_id="",
            field_path="",
            issue_type="unsupported_artifact",
            source_url_value="",
            severity="error",
            explanation="Artifact root is not a JSON object",
        )
        return SourceURLTraceabilityArtifactStatus(
            artifact_key=artifact_key,
            artifact_path=str(artifact_path),
            present=True,
            parseable=False,
            issues=[issue],
        )

    # Determine URL field and items key
    field_path = _ARTIFACT_SOURCE_URL_FIELD_PATHS.get(artifact_key, "")
    if "linked_source_urls" in field_path:
        url_field = "linked_source_urls"
    else:
        url_field = "source_urls"

    items_key = _ARTIFACT_ITEMS_KEY.get(artifact_key, "items")
    id_key = _ARTIFACT_ITEM_ID_KEY.get(artifact_key, "")

    items = data.get(items_key, [])
    if not isinstance(items, list):
        items = []

    issues: list[SourceURLTraceabilityIssue] = []
    items_with_placeholder: int = 0
    items_with_missing: int = 0
    items_with_malformed: int = 0
    items_exempt: int = 0
    issue_idx: dict[str, int] = {}  # per (item_id, issue_type) counter

    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get(id_key, ""))
        is_exempt = _is_insufficient_evidence_item(item, artifact_key)

        item_urls = item.get(url_field)
        if not isinstance(item_urls, list):
            item_urls = []

        if is_exempt:
            items_exempt += 1
            # Insufficient-evidence items are exempt from placeholder/missing checks
            continue

        if not item_urls:
            items_with_missing += 1
            idx_key = f"{item_id}|missing_source_url"
            cnt = issue_idx.get(idx_key, 0)
            issue_idx[idx_key] = cnt + 1
            issues.append(
                SourceURLTraceabilityIssue(
                    issue_id=_make_issue_id(artifact_key, item_id, "missing_source_url", cnt),
                    artifact_key=artifact_key,
                    artifact_path=str(artifact_path),
                    item_id=item_id,
                    field_path=field_path,
                    issue_type="missing_source_url",
                    source_url_value="",
                    severity="error",
                    explanation=f"Item '{item_id}' in {artifact_key} has empty {url_field}",
                )
            )
            continue

        has_placeholder = False
        for idx, url in enumerate(item_urls):
            url_str = str(url).strip() if isinstance(url, str) else ""
            if not url_str:
                continue
            if is_placeholder_source_url(url_str):
                has_placeholder = True
                cnt = issue_idx.get(f"{item_id}|placeholder_source_url", 0)
                issue_idx[f"{item_id}|placeholder_source_url"] = cnt + 1
                issues.append(
                    SourceURLTraceabilityIssue(
                        issue_id=_make_issue_id(artifact_key, item_id, "placeholder_source_url", cnt),
                        artifact_key=artifact_key,
                        artifact_path=str(artifact_path),
                        item_id=item_id,
                        field_path=f"{field_path}[{idx}]",
                        issue_type="placeholder_source_url",
                        source_url_value=url_str,
                        severity="error",
                        explanation=f"Placeholder URN '{url_str}' found in {artifact_key} item '{item_id}'. "
                        f"Real source URLs must be propagated from upstream artifacts.",
                    )
                )
            elif is_malformed_source_url(url_str):
                cnt = issue_idx.get(f"{item_id}|malformed_source_url", 0)
                issue_idx[f"{item_id}|malformed_source_url"] = cnt + 1
                issues.append(
                    SourceURLTraceabilityIssue(
                        issue_id=_make_issue_id(artifact_key, item_id, "malformed_source_url", cnt),
                        artifact_key=artifact_key,
                        artifact_path=str(artifact_path),
                        item_id=item_id,
                        field_path=f"{field_path}[{idx}]",
                        issue_type="malformed_source_url",
                        source_url_value=url_str,
                        severity="warning",
                        explanation=f"Malformed source URL '{url_str}' in {artifact_key} item '{item_id}'",
                    )
                )

        if has_placeholder:
            items_with_placeholder += 1
        # Check malformed separately
        if any(is_malformed_source_url(str(u).strip()) for u in item_urls if isinstance(u, str)):
            items_with_malformed += 1

    return SourceURLTraceabilityArtifactStatus(
        artifact_key=artifact_key,
        artifact_path=str(artifact_path),
        present=True,
        parseable=True,
        item_count=len(items),
        items_with_placeholder_urls=items_with_placeholder,
        items_with_missing_source_urls=items_with_missing,
        items_with_malformed_source_urls=items_with_malformed,
        items_exempt_insufficient_evidence=items_exempt,
        issues=issues,
    )


# ---------------------------------------------------------------------------
# Main traceability checker
# ---------------------------------------------------------------------------


def check_source_url_traceability(run_dir: str | Path) -> SourceURLTraceabilityReport:
    """Scan a weekly run directory and report source URL traceability issues.

    Checks each canonical artifact for:
    - Placeholder URNs (``urn:oos:*``)
    - Missing source URLs (empty list where URLs are expected)
    - Malformed source URLs (broken http: strings)
    - Unparseable artifacts (malformed JSON)

    Insufficient-evidence evidence packs are exempt from placeholder/missing checks.

    Args:
        run_dir: Path to the weekly run directory.

    Returns:
        SourceURLTraceabilityReport with structured results.
    """
    run_path = Path(run_dir).resolve()
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    warnings: list[str] = []
    errors: list[str] = []

    if not run_path.is_dir():
        return SourceURLTraceabilityReport(
            run_dir=str(run_path),
            checked_at=checked_at,
            validation_passed=False,
            warnings=[],
            errors=[f"Run directory not found: {run_path}"],
        )

    manifest_path = run_path / "manifest.json"
    if not manifest_path.is_file():
        warnings.append(f"Manifest not found at {manifest_path}; scanning artifacts anyway")

    artifact_statuses: list[SourceURLTraceabilityArtifactStatus] = []
    all_issues: list[SourceURLTraceabilityIssue] = []

    for artifact_key in _CANONICAL_SOURCE_URL_KEYS:
        status = _check_artifact_source_urls(run_path, artifact_key)
        artifact_statuses.append(status)
        all_issues.extend(status.issues)

    # Aggregate counts
    placeholder_count = sum(
        1 for issue in all_issues if issue.issue_type == "placeholder_source_url"
    )
    missing_count = sum(
        1 for issue in all_issues if issue.issue_type == "missing_source_url"
    )
    malformed_count = sum(
        1 for issue in all_issues if issue.issue_type == "malformed_source_url"
    )
    exempt_count = sum(
        s.items_exempt_insufficient_evidence for s in artifact_statuses
    )
    artifacts_checked = sum(1 for s in artifact_statuses if s.present)

    # Validation passes if no placeholder URNs are found and no errors
    # (missing source URLs in non-exempt items are also treated as blockers)
    has_blockers = placeholder_count > 0 or missing_count > 0 or any(
        issue.issue_type == "unsupported_artifact" for issue in all_issues
    )
    validation_passed = not has_blockers

    return SourceURLTraceabilityReport(
        run_dir=str(run_path),
        checked_at=checked_at,
        artifact_statuses=artifact_statuses,
        issues=all_issues,
        issue_count=len(all_issues),
        placeholder_url_count=placeholder_count,
        missing_source_url_count=missing_count,
        malformed_url_count=malformed_count,
        exempt_insufficient_evidence_count=exempt_count,
        artifacts_checked=artifacts_checked,
        validation_passed=validation_passed,
        warnings=warnings,
        errors=errors,
    )


def source_url_traceability_to_json(report: SourceURLTraceabilityReport) -> str:
    """Serialize a SourceURLTraceabilityReport to deterministic JSON."""
    return json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)
