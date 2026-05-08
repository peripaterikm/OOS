"""Weekly Cycle Status — deterministic read-only status inspector for v2.6 weekly runs.

Roadmap v2.6 item 6.1. Inspects an existing weekly run directory and reports:
- whether the run exists;
- whether manifest.json exists and validates;
- which expected artifacts exist / are missing;
- whether founder inbox v2 exists;
- whether founder decisions were imported;
- whether feedback mappings, preference profile, and parking lot records exist;
- whether next-best actions exist;
- whether run report artifacts exist;
- warnings/errors from manifest or artifacts where available;
- recommended next step for the founder/developer.

Read-only. No artifact modification. No rebuild. No import. No portfolio mutation.
No live APIs/LLMs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from oos.weekly_run_manifest import (
    _CANONICAL_ARTIFACT_KEYS,
    KNOWN_ARTIFACT_KEYS,
    canonical_artifact_paths,
    read_weekly_run_manifest,
)

WEEKLY_CYCLE_STATUS_SCHEMA_VERSION = "weekly_cycle_status.v1"

# ---------------------------------------------------------------------------
# Artifact status model
# ---------------------------------------------------------------------------


@dataclass
class WeeklyCycleArtifactStatus:
    """Per-artifact status entry."""

    artifact_key: str = ""
    relative_path: str = ""
    exists: bool = False
    is_empty_state: bool = True
    schema_version: str = ""
    item_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_key": self.artifact_key,
            "relative_path": self.relative_path,
            "exists": self.exists,
            "is_empty_state": self.is_empty_state,
            "schema_version": self.schema_version,
            "item_count": self.item_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# Main status model
# ---------------------------------------------------------------------------


@dataclass
class WeeklyCycleStatus:
    """Complete read-only status for one v2.6 weekly run."""

    schema_version: str = WEEKLY_CYCLE_STATUS_SCHEMA_VERSION
    run_id: str = ""
    run_dir: str = ""
    manifest_path: str = ""
    manifest_valid: bool = False
    manifest_errors: list[str] = field(default_factory=list)
    expected_artifact_count: int = 0
    present_artifact_count: int = 0
    missing_artifact_keys: list[str] = field(default_factory=list)
    artifact_statuses: list[WeeklyCycleArtifactStatus] = field(default_factory=list)
    founder_inbox_present: bool = False
    founder_inbox_review_item_count: int = 0
    founder_decisions_imported: bool = False
    founder_decision_count: int = 0
    feedback_mapping_count: int = 0
    preference_profile_present: bool = False
    parking_lot_record_count: int = 0
    next_best_action_count: int = 0
    run_report_present: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommended_next_step: str = ""
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True
    validation_passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "run_dir": self.run_dir,
            "manifest_path": self.manifest_path,
            "manifest_valid": self.manifest_valid,
            "manifest_errors": list(self.manifest_errors),
            "expected_artifact_count": self.expected_artifact_count,
            "present_artifact_count": self.present_artifact_count,
            "missing_artifact_keys": list(self.missing_artifact_keys),
            "artifact_statuses": [s.to_dict() for s in self.artifact_statuses],
            "founder_inbox_present": self.founder_inbox_present,
            "founder_inbox_review_item_count": self.founder_inbox_review_item_count,
            "founder_decisions_imported": self.founder_decisions_imported,
            "founder_decision_count": self.founder_decision_count,
            "feedback_mapping_count": self.feedback_mapping_count,
            "preference_profile_present": self.preference_profile_present,
            "parking_lot_record_count": self.parking_lot_record_count,
            "next_best_action_count": self.next_best_action_count,
            "run_report_present": self.run_report_present,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommended_next_step": self.recommended_next_step,
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
            "validation_passed": self.validation_passed,
        }


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


def weekly_cycle_status_to_json(status: WeeklyCycleStatus) -> str:
    """Serialize a WeeklyCycleStatus to a JSON string."""
    return json.dumps(status.to_dict(), ensure_ascii=False, indent=2, sort_keys=False) + "\n"


# ---------------------------------------------------------------------------
# Helpers: safe JSON reading
# ---------------------------------------------------------------------------


def _safe_read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    """Read and parse a JSON file. Returns None on failure."""
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return None


def _safe_count_items(data: Any) -> int | None:
    """Count items in a JSON artifact.

    - List artifacts: count list length.
    - Dict artifacts with 'items' key: count items list length.
    - Dict artifacts without clear collection: return 0 (present but non-list).
    - None: return None (not countable).
    """
    if data is None:
        return None
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return len(items)
        return 0
    return 0


# ---------------------------------------------------------------------------
# Helpers: file-system artifact collection counts
# ---------------------------------------------------------------------------


def _count_from_json_artifact(run_dir: Path, filename: str) -> int:
    """Read a JSON artifact file and return its item count. Returns 0 on
    missing, invalid, or empty artifacts."""
    path = run_dir / filename
    if not path.is_file():
        return 0
    data = _safe_read_json(path)
    count = _safe_count_items(data)
    return count if count is not None else 0


def _count_review_items_from_inbox_index(run_dir: Path) -> int:
    """Read founder_inbox_v2_index.json and return review item count."""
    path = run_dir / "founder_inbox_v2_index.json"
    if not path.is_file():
        return 0
    data = _safe_read_json(path)
    if isinstance(data, dict):
        items = data.get("review_items")
        if isinstance(items, list):
            return len(items)
    return 0


def _is_present(run_dir: Path, filename: str) -> bool:
    """Check if a file exists under the run directory."""
    return (run_dir / filename).is_file()


# ---------------------------------------------------------------------------
# Artifact-specific schema version extraction
# ---------------------------------------------------------------------------


def _extract_schema_version(data: Any) -> str:
    """Extract schema_version from a JSON artifact dict, if available."""
    if isinstance(data, dict):
        sv = data.get("schema_version", "")
        if isinstance(sv, str):
            return sv
    return ""


# ---------------------------------------------------------------------------
# Build artifact status list
# ---------------------------------------------------------------------------


def _build_artifact_statuses(
    run_dir: Path,
    manifest_empty_states: dict[str, bool],
) -> list[WeeklyCycleArtifactStatus]:
    """Build per-artifact status entries for all canonical artifacts."""
    paths = canonical_artifact_paths()
    statuses: list[WeeklyCycleArtifactStatus] = []

    for key in _CANONICAL_ARTIFACT_KEYS:
        filename = paths.get(key, "")
        artifact_path = run_dir / filename
        exists = artifact_path.is_file()
        is_empty = manifest_empty_states.get(key, True)
        schema_version = ""
        item_count = 0
        art_warnings: list[str] = []
        art_errors: list[str] = []

        if exists and filename.endswith(".json"):
            data = _safe_read_json(artifact_path)
            if data is None:
                art_errors.append(f"Artifact {key} is not valid JSON")
            else:
                schema_version = _extract_schema_version(data)
                count = _safe_count_items(data)
                item_count = count if count is not None else 0
        else:
            schema_version = ""

        # Override empty state based on actual presence
        if exists and item_count > 0:
            is_empty = False

        statuses.append(
            WeeklyCycleArtifactStatus(
                artifact_key=key,
                relative_path=filename,
                exists=exists,
                is_empty_state=is_empty,
                schema_version=schema_version,
                item_count=item_count,
                warnings=art_warnings,
                errors=art_errors,
            )
        )

    return statuses


# ---------------------------------------------------------------------------
# Auto-discover latest run
# ---------------------------------------------------------------------------


def _discover_latest_run(weekly_runs_root: Path) -> str | None:
    """Find the latest run directory under artifacts/weekly_runs/.

    Sorting is deterministic: directory name (descending). Since run_id
    contains an ISO date prefix (YYYY-MM-DD), this naturally sorts by date
    first, then by content hash.
    """
    if not weekly_runs_root.is_dir():
        return None

    run_dirs: list[Path] = []
    for entry in weekly_runs_root.iterdir():
        if entry.is_dir():
            # Prefer directories that contain manifest.json
            if (entry / "manifest.json").is_file():
                run_dirs.append(entry)
            else:
                # Include directories without manifest too (for error reporting)
                run_dirs.append(entry)

    if not run_dirs:
        return None

    # Sort by directory name descending
    run_dirs.sort(key=lambda p: p.name, reverse=True)
    return run_dirs[0].name


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------


def build_weekly_cycle_status(
    project_root: Path,
    run_id: str | None = None,
) -> WeeklyCycleStatus:
    """Build a read-only status report for a v2.6 weekly run.

    Args:
        project_root: Root directory of the OOS project.
        run_id: Optional run ID. Auto-discovered (latest) if not provided.

    Returns:
        WeeklyCycleStatus with full inspection results.
    """
    project_root = project_root.resolve()
    weekly_runs_root = project_root / "artifacts" / "weekly_runs"
    warnings: list[str] = []
    errors: list[str] = []

    # ── 1. Resolve run_id ──────────────────────────────────────────
    if run_id is None:
        discovered = _discover_latest_run(weekly_runs_root)
        if discovered is None:
            return WeeklyCycleStatus(
                run_dir=str(weekly_runs_root),
                manifest_path="",
                errors=["No weekly runs found under artifacts/weekly_runs/"],
                warnings=["Run the weekly cycle builder first: python -m oos.cli run-weekly-cycle-v2 --project-root . --input-file <path>"],
                recommended_next_step="Run the weekly cycle builder (run-weekly-cycle-v2) to create a run.",
                validation_passed=False,
            )
        run_id = discovered

    # ── 2. Validate run directory exists ───────────────────────────
    run_dir = weekly_runs_root / run_id
    if not run_dir.is_dir():
        return WeeklyCycleStatus(
            run_id=run_id,
            run_dir=str(run_dir),
            manifest_path="",
            errors=[f"Run directory does not exist: {run_dir}"],
            recommended_next_step="Check the run_id or run the weekly cycle builder.",
            validation_passed=False,
        )

    manifest_path = run_dir / "manifest.json"

    # ── 3. Read and validate manifest ──────────────────────────────
    manifest_valid = False
    manifest_errors: list[str] = []
    manifest_empty_states: dict[str, bool] = {}
    manifest = None

    try:
        manifest = read_weekly_run_manifest(run_dir)
        manifest_valid = True
        manifest_empty_states = dict(manifest.empty_states)
    except FileNotFoundError:
        errors.append(f"Manifest not found: {manifest_path}")
        manifest_errors.append("manifest.json is missing")
    except (ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Manifest invalid: {exc}")
        manifest_errors.append(str(exc))

    # ── 4. Build artifact statuses ─────────────────────────────────
    artifact_statuses = _build_artifact_statuses(run_dir, manifest_empty_states)
    expected_count = len(_CANONICAL_ARTIFACT_KEYS)
    present_count = sum(1 for s in artifact_statuses if s.exists)
    missing_keys = [s.artifact_key for s in artifact_statuses if not s.exists]

    # ── 5. Inspect specific artifacts ──────────────────────────────
    paths = canonical_artifact_paths()

    # Founder inbox
    founder_inbox_present = _is_present(run_dir, paths.get("founder_inbox_v2_md", "founder_inbox_v2.md"))
    founder_inbox_review_item_count = _count_review_items_from_inbox_index(run_dir)

    # Founder decisions
    founder_decisions_count = _count_from_json_artifact(
        run_dir, paths.get("founder_decisions_v2", "founder_decisions_v2.json")
    )
    founder_decisions_imported = founder_decisions_count > 0

    # Feedback mappings
    feedback_mapping_count = _count_from_json_artifact(
        run_dir, paths.get("founder_feedback_mappings", "founder_feedback_mappings.json")
    )

    # Preference profile
    preference_profile_present = _is_present(
        run_dir, paths.get("founder_preference_profile", "founder_preference_profile.json")
    )
    # Check if profile is empty (has decision_count > 0)
    if preference_profile_present:
        profile_data = _safe_read_json(run_dir / paths.get("founder_preference_profile", "founder_preference_profile.json"))
        if isinstance(profile_data, dict) and profile_data.get("decision_count", 0) == 0:
            # Profile exists but is empty
            pass

    # Parking lot
    parking_lot_record_count = _count_from_json_artifact(
        run_dir, paths.get("parking_lot_records", "parking_lot_records.json")
    )

    # Next best actions
    next_best_action_count = _count_from_json_artifact(
        run_dir, paths.get("next_best_actions", "next_best_actions.json")
    )

    # Run report
    run_report_present = _is_present(run_dir, paths.get("run_report", "run_report.json"))

    # ── 6. Collect per-artifact JSON errors ────────────────────────
    for art_status in artifact_statuses:
        for art_err in art_status.errors:
            if art_err not in errors:
                errors.append(art_err)

    # ── 7. Determine recommended next step ─────────────────────────
    recommended_next_step = _compute_recommended_next_step(
        manifest_valid=manifest_valid,
        founder_inbox_present=founder_inbox_present,
        founder_decisions_imported=founder_decisions_imported,
        present_count=present_count,
        expected_count=expected_count,
        has_errors=len(errors) > 0,
    )

    # ── 8. Add missing artifact errors ────────────────────────────
    if missing_keys:
        errors.append(f"Missing artifacts ({len(missing_keys)}): {', '.join(missing_keys)}")

    # ── 9. Validation passed ───────────────────────────────────────
    validation_passed = manifest_valid and len(errors) == 0

    return WeeklyCycleStatus(
        run_id=run_id,
        run_dir=str(run_dir),
        manifest_path=str(manifest_path),
        manifest_valid=manifest_valid,
        manifest_errors=manifest_errors,
        expected_artifact_count=expected_count,
        present_artifact_count=present_count,
        missing_artifact_keys=missing_keys,
        artifact_statuses=artifact_statuses,
        founder_inbox_present=founder_inbox_present,
        founder_inbox_review_item_count=founder_inbox_review_item_count,
        founder_decisions_imported=founder_decisions_imported,
        founder_decision_count=founder_decisions_count,
        feedback_mapping_count=feedback_mapping_count,
        preference_profile_present=preference_profile_present,
        parking_lot_record_count=parking_lot_record_count,
        next_best_action_count=next_best_action_count,
        run_report_present=run_report_present,
        warnings=warnings,
        errors=errors,
        recommended_next_step=recommended_next_step,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
        validation_passed=validation_passed,
    )


def _compute_recommended_next_step(
    *,
    manifest_valid: bool,
    founder_inbox_present: bool,
    founder_decisions_imported: bool,
    present_count: int,
    expected_count: int,
    has_errors: bool,
) -> str:
    """Compute the recommended next step based on current run state."""
    if not manifest_valid:
        if present_count == 0:
            return (
                "No manifest found and no artifacts exist. "
                "Run the weekly cycle builder: python -m oos.cli run-weekly-cycle-v2 --project-root . --input-file <path>"
            )
        return (
            "Manifest is missing or invalid. "
            "Run directory may be corrupted. Consider re-running the weekly cycle builder."
        )

    if has_errors:
        return (
            "Errors detected in run artifacts. "
            "Review errors above and consider re-running the weekly cycle builder or restoring from a previous run."
        )

    if present_count < expected_count:
        missing_count = expected_count - present_count
        return (
            f"Run is incomplete: {missing_count} of {expected_count} artifacts missing. "
            "Re-run the weekly cycle builder to regenerate missing artifacts."
        )

    if not founder_inbox_present:
        return (
            "Founder inbox v2 is missing. "
            "Re-run the weekly cycle builder to generate the inbox."
        )

    if not founder_decisions_imported:
        return (
            "Weekly cycle build is complete. Founder inbox is ready for review. "
            "Next: review founder_inbox_v2.md, record decisions, and import them via: "
            "python -m oos.cli import-founder-decisions-v2 --project-root . --run-id <run_id> --decisions-file <path>"
        )

    return (
        "Founder decisions have been imported. "
        "Review updated preference profile, feedback mappings, and parking lot records. "
        "Run is complete. You may start a new weekly cycle with new inputs."
    )


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def render_weekly_cycle_status_markdown(status: WeeklyCycleStatus) -> str:
    """Render a WeeklyCycleStatus as a human-readable Markdown string."""

    lines: list[str] = []
    lines.append("# Weekly Cycle Status")
    lines.append("")

    # ── 1. Run identity ──────────────────────────────────
    lines.append("## 1. Run Identity")
    lines.append("")
    lines.append(f"- **Run ID**: `{status.run_id}`")
    lines.append(f"- **Run Directory**: `{status.run_dir}`")
    lines.append(f"- **Manifest Path**: `{status.manifest_path}`")
    lines.append("")

    # ── 2. Manifest status ───────────────────────────────
    lines.append("## 2. Manifest Status")
    lines.append("")
    lines.append(f"- **Manifest valid**: `{str(status.manifest_valid).lower()}`")
    if status.manifest_errors:
        for e in status.manifest_errors:
            lines.append(f"- **Manifest error**: {e}")
    lines.append("")

    # ── 3. Artifact completeness ─────────────────────────
    lines.append("## 3. Artifact Completeness")
    lines.append("")
    lines.append(f"- **Expected**: {status.expected_artifact_count}")
    lines.append(f"- **Present**: {status.present_artifact_count}")
    if status.missing_artifact_keys:
        lines.append(f"- **Missing**: {', '.join(f'`{k}`' for k in status.missing_artifact_keys)}")
    lines.append("")

    # ── 4. Pipeline artifact counts ──────────────────────
    lines.append("## 4. Pipeline Artifact Counts")
    lines.append("")
    for art in status.artifact_statuses:
        present_mark = "✓" if art.exists else "✗"
        empty_note = " (empty)" if art.is_empty_state and art.exists else ""
        count_info = f" — {art.item_count} items" if art.exists else " — missing"
        lines.append(f"- {present_mark} **{art.artifact_key}**{count_info}{empty_note}")
    lines.append("")

    # ── 5. Founder inbox status ──────────────────────────
    lines.append("## 5. Founder Inbox Status")
    lines.append("")
    lines.append(f"- **Founder inbox present**: `{str(status.founder_inbox_present).lower()}`")
    lines.append(f"- **Review items**: {status.founder_inbox_review_item_count}")
    lines.append("")

    # ── 6. Founder decision import status ────────────────
    lines.append("## 6. Founder Decision Import Status")
    lines.append("")
    lines.append(f"- **Decisions imported**: `{str(status.founder_decisions_imported).lower()}`")
    lines.append(f"- **Decision count**: {status.founder_decision_count}")
    lines.append("")

    # ── 7. Feedback / Profile / Parking Lot status ───────
    lines.append("## 7. Feedback / Profile / Parking Lot Status")
    lines.append("")
    lines.append(f"- **Feedback mappings**: {status.feedback_mapping_count}")
    lines.append(f"- **Preference profile present**: `{str(status.preference_profile_present).lower()}`")
    lines.append(f"- **Parking lot records**: {status.parking_lot_record_count}")
    lines.append(f"- **Next best actions**: {status.next_best_action_count}")
    lines.append(f"- **Run report present**: `{str(status.run_report_present).lower()}`")
    lines.append("")

    # ── 8. Warnings / Errors ─────────────────────────────
    lines.append("## 8. Warnings / Errors")
    lines.append("")
    if status.warnings:
        lines.append("### Warnings")
        for w in status.warnings:
            lines.append(f"- {w}")
        lines.append("")
    else:
        lines.append("### Warnings")
        lines.append("- None")
        lines.append("")
    if status.errors:
        lines.append("### Errors")
        for e in status.errors:
            lines.append(f"- {e}")
        lines.append("")
    else:
        lines.append("### Errors")
        lines.append("- None")
        lines.append("")

    # ── 9. Recommended next step ─────────────────────────
    lines.append("## 9. Recommended Next Step")
    lines.append("")
    lines.append(status.recommended_next_step)
    lines.append("")

    # ── 10. Artifact paths ───────────────────────────────
    lines.append("## 10. Artifact Paths")
    lines.append("")
    for art in status.artifact_statuses:
        abs_path = Path(status.run_dir) / art.relative_path
        lines.append(f"- `{art.relative_path}` → `{abs_path}`")
    lines.append("")

    # ── Safety flags ─────────────────────────────────────
    lines.append("## Safety")
    lines.append("")
    lines.append(f"- **advisory_only**: `{str(status.advisory_only).lower()}`")
    lines.append(f"- **no_live_api**: `{str(status.no_live_api).lower()}`")
    lines.append(f"- **no_live_llm**: `{str(status.no_live_llm).lower()}`")
    lines.append(f"- **validation_passed**: `{str(status.validation_passed).lower()}`")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
