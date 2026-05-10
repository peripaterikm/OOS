"""Run Reports and Dashboard Index — deterministic per-run and cross-run reporting.

Roadmap v2.6 item 7.1. Aggregates existing weekly run artifacts and status
reports into:

1. Per-run report artifacts: ``run_report.json`` + ``run_report.md``
2. Cross-run dashboard index: ``dashboard_index.json`` + ``dashboard.md``

Builds on WeeklyRunManifest, WeeklyCycleStatus, existing run artifacts, and
founder inbox / decision import artifacts.

No live API/LLM calls. No rebuild. No import. No portfolio mutation.
No autonomous decisions. Deterministic. Advisory-only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from oos.weekly_cycle_status import (
    WeeklyCycleStatus,
    build_weekly_cycle_status,
)
from oos.weekly_run_manifest import (
    _CANONICAL_ARTIFACT_KEYS,
    canonical_artifact_paths,
    read_weekly_run_manifest,
)
from oos.founder_decision_import import build_import_history_summary

WEEKLY_RUN_REPORT_SCHEMA_VERSION = "weekly_run_report.v1"
WEEKLY_DASHBOARD_INDEX_SCHEMA_VERSION = "weekly_dashboard_index.v1"


# ============================================================================
# Models
# ============================================================================


@dataclass
class WeeklyRunReport:
    """Deterministic per-run report aggregating everything known about one run."""

    schema_version: str = WEEKLY_RUN_REPORT_SCHEMA_VERSION
    run_id: str = ""
    generated_at: str = ""
    status_summary: dict[str, Any] = field(default_factory=dict)
    artifact_summary: dict[str, Any] = field(default_factory=dict)
    pipeline_counts: dict[str, int] = field(default_factory=dict)
    founder_inbox_summary: dict[str, Any] = field(default_factory=dict)
    decision_import_summary: dict[str, Any] = field(default_factory=dict)
    import_history_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommended_next_step: str = ""
    artifact_paths: dict[str, str] = field(default_factory=dict)
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True
    validation_passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "status_summary": dict(self.status_summary),
            "artifact_summary": dict(self.artifact_summary),
            "pipeline_counts": dict(self.pipeline_counts),
            "founder_inbox_summary": dict(self.founder_inbox_summary),
            "decision_import_summary": dict(self.decision_import_summary),
            "import_history_summary": dict(self.import_history_summary),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommended_next_step": self.recommended_next_step,
            "artifact_paths": dict(self.artifact_paths),
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
            "validation_passed": self.validation_passed,
        }


@dataclass
class WeeklyDashboardRunSummary:
    """One row in the dashboard index for a single run."""

    run_id: str = ""
    run_dir: str = ""
    manifest_valid: bool = False
    validation_passed: bool = False
    present_artifact_count: int = 0
    expected_artifact_count: int = 0
    missing_artifact_count: int = 0
    founder_inbox_review_item_count: int = 0
    founder_decision_count: int = 0
    next_best_action_count: int = 0
    correction_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    recommended_next_step: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_dir": self.run_dir,
            "manifest_valid": self.manifest_valid,
            "validation_passed": self.validation_passed,
            "present_artifact_count": self.present_artifact_count,
            "expected_artifact_count": self.expected_artifact_count,
            "missing_artifact_count": self.missing_artifact_count,
            "founder_inbox_review_item_count": self.founder_inbox_review_item_count,
            "founder_decision_count": self.founder_decision_count,
            "next_best_action_count": self.next_best_action_count,
            "correction_count": self.correction_count,
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "recommended_next_step": self.recommended_next_step,
        }


@dataclass
class WeeklyDashboardIndex:
    """Cross-run dashboard aggregating all known weekly runs."""

    schema_version: str = WEEKLY_DASHBOARD_INDEX_SCHEMA_VERSION
    generated_at: str = ""
    project_root: str = ""
    total_runs: int = 0
    latest_run_id: str = ""
    complete_run_count: int = 0
    incomplete_run_count: int = 0
    invalid_run_count: int = 0
    runs: list[WeeklyDashboardRunSummary] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "project_root": self.project_root,
            "total_runs": self.total_runs,
            "latest_run_id": self.latest_run_id,
            "complete_run_count": self.complete_run_count,
            "incomplete_run_count": self.incomplete_run_count,
            "invalid_run_count": self.invalid_run_count,
            "runs": [r.to_dict() for r in self.runs],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
        }


# ============================================================================
# Helpers
# ============================================================================


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def _safe_read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    """Read and parse a JSON file. Returns None on failure."""
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return None


def _safe_count_items(data: Any) -> int | None:
    """Count items in a JSON artifact."""
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


def _discover_run_dirs(weekly_runs_root: Path) -> list[Path]:
    """Discover all run directories under artifacts/weekly_runs/ (sorted by name desc)."""
    if not weekly_runs_root.is_dir():
        return []
    dirs: list[Path] = []
    for entry in sorted(weekly_runs_root.iterdir(), key=lambda p: p.name, reverse=True):
        if entry.is_dir() and (entry / "manifest.json").is_file():
            dirs.append(entry)
    return dirs


# ============================================================================
# Per-run report builder
# ============================================================================


def build_weekly_run_report(
    project_root: Path,
    run_id: str,
    *,
    generated_at: str | None = None,
) -> WeeklyRunReport:
    """Build a deterministic per-run report for a single weekly run.

    Args:
        project_root: Root directory of the OOS project.
        run_id: The weekly run ID to report on.
        generated_at: Optional fixed timestamp for deterministic artifact bytes.

    Returns:
        WeeklyRunReport with all aggregated information.
    """
    project_root = project_root.resolve()
    weekly_runs_root = project_root / "artifacts" / "weekly_runs"
    run_dir = weekly_runs_root / run_id
    resolved_generated_at = generated_at if generated_at else _iso_utc_now()
    warnings: list[str] = []
    errors: list[str] = []

    # ── 1. Validate run directory exists ──────────────────────────────
    if not run_dir.is_dir():
        return WeeklyRunReport(
            run_id=run_id,
            generated_at=resolved_generated_at,
            errors=[f"Run directory does not exist: {run_dir}"],
            warnings=[f"No run found for run_id: {run_id}"],
            recommended_next_step="Check the run_id or run the weekly cycle builder.",
            validation_passed=False,
        )

    # ── 2. Build status via WeeklyCycleStatus (source of truth) ──────
    status = build_weekly_cycle_status(project_root=project_root, run_id=run_id)

    # ── 3. Read manifest for artifact paths ──────────────────────────
    manifest = None
    try:
        manifest = read_weekly_run_manifest(run_dir)
    except (FileNotFoundError, ValueError):
        pass

    # ── 4. Build artifact paths absolute and relative ────────────────
    paths = canonical_artifact_paths()
    artifact_paths: dict[str, str] = {}
    for key in _CANONICAL_ARTIFACT_KEYS:
        filename = paths.get(key, "")
        rel = str(Path(run_id) / filename)
        artifact_paths[key] = rel

    # ── 5. Pipeline counts ───────────────────────────────────────────
    pipeline_counts: dict[str, int] = {}
    pipeline_counts["evidence_packs"] = _safe_count_items(
        _safe_read_json(run_dir / paths.get("evidence_packs", "evidence_packs.json"))
    ) or 0
    pipeline_counts["opportunity_candidates"] = _safe_count_items(
        _safe_read_json(run_dir / paths.get("opportunity_candidates", "opportunity_candidates.json"))
    ) or 0
    pipeline_counts["quality_gate_decisions"] = _safe_count_items(
        _safe_read_json(run_dir / paths.get("quality_gate_decisions", "quality_gate_decisions.json"))
    ) or 0
    pipeline_counts["founder_decisions"] = status.founder_decision_count
    pipeline_counts["feedback_mappings"] = status.feedback_mapping_count
    pipeline_counts["parking_lot_records"] = status.parking_lot_record_count
    pipeline_counts["next_best_actions"] = status.next_best_action_count

    # ── 6. Quality gate summary ──────────────────────────────────────
    quality_gate_summary: dict[str, int] = {"total": pipeline_counts.get("quality_gate_decisions", 0)}
    gate_data = _safe_read_json(run_dir / paths.get("quality_gate_decisions", "quality_gate_decisions.json"))
    if isinstance(gate_data, dict):
        items = gate_data.get("items", [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    decision = str(item.get("decision", "")).lower()
                    quality_gate_summary[decision] = quality_gate_summary.get(decision, 0) + 1

    # ── 7. Decision import summary ───────────────────────────────────
    decision_summary: dict[str, int] = {
        "promote": 0, "park": 0, "kill": 0,
        "needs_more_evidence": 0, "revisit_later": 0,
    }
    dec_data = _safe_read_json(run_dir / paths.get("founder_decisions_v2", "founder_decisions_v2.json"))
    if isinstance(dec_data, dict):
        dec_items = dec_data.get("items", [])
        if isinstance(dec_items, list):
            for d in dec_items:
                if isinstance(d, dict):
                    dv = str(d.get("decision", "")).lower()
                    decision_summary[dv] = decision_summary.get(dv, 0) + 1

    # ── 8. Action summary ──────────────────────────────────────────
    action_summary: dict[str, int] = {}
    act_data = _safe_read_json(run_dir / paths.get("next_best_actions", "next_best_actions.json"))
    if isinstance(act_data, dict):
        act_items = act_data.get("items", [])
        if isinstance(act_items, list):
            for a in act_items:
                if isinstance(a, dict):
                    at = str(a.get("action_type", "unknown")).lower()
                    action_summary[at] = action_summary.get(at, 0) + 1

    # ── 9. Collect errors from status ───────────────────────────────
    for e in status.errors:
        if e not in errors:
            errors.append(e)

    # ── 10. Collect warnings from status ────────────────────────────
    for w in status.warnings:
        if w not in warnings:
            warnings.append(w)

    # ── 11. Traceability summary ────────────────────────────────────
    traceability_summary: dict[str, int] = {}
    # Count unique evidence IDs from evidence packs
    ep_data = _safe_read_json(run_dir / paths.get("evidence_packs", "evidence_packs.json"))
    if isinstance(ep_data, dict) and isinstance(ep_data.get("items"), list):
        evidence_ids: set[str] = set()
        signal_ids: set[str] = set()
        source_urls: set[str] = set()
        for ep in ep_data["items"]:
            if isinstance(ep, dict):
                for eid in ep.get("evidence_ids", []):
                    if isinstance(eid, str):
                        evidence_ids.add(eid)
                for sid in ep.get("source_signal_ids", []):
                    if isinstance(sid, str):
                        signal_ids.add(sid)
                for su in ep.get("source_urls", []):
                    if isinstance(su, str):
                        source_urls.add(su)
        traceability_summary["unique_evidence_ids"] = len(evidence_ids)
        traceability_summary["unique_signal_ids"] = len(signal_ids)
        traceability_summary["unique_source_urls"] = len(source_urls)
    traceability_summary["unique_opportunity_ids"] = pipeline_counts.get("opportunity_candidates", 0)

    # ── 12. Preference warnings ─────────────────────────────────────
    preference_warnings: list[str] = []
    profile_data = _safe_read_json(run_dir / paths.get("founder_preference_profile", "founder_preference_profile.json"))
    if isinstance(profile_data, dict):
        pw = profile_data.get("warnings", [])
        if isinstance(pw, list):
            preference_warnings = [str(w) for w in pw]

    # ── 13. Review completion ────────────────────────────────────────
    review_items = status.founder_inbox_review_item_count
    decisions_made = sum(decision_summary.values())
    review_completion = decisions_made / review_items if review_items > 0 else 0.0

    # ── 14. Status summary ──────────────────────────────────────────
    status_summary = {
        "manifest_valid": status.manifest_valid,
        "expected_artifact_count": status.expected_artifact_count,
        "present_artifact_count": status.present_artifact_count,
        "missing_artifact_keys": list(status.missing_artifact_keys),
        "warnings_count": len(warnings),
        "errors_count": len(errors),
    }

    # ── 15. Artifact summary ────────────────────────────────────────
    artifact_summary: dict[str, dict[str, Any]] = {}
    for art_status in status.artifact_statuses:
        artifact_summary[art_status.artifact_key] = {
            "relative_path": art_status.relative_path,
            "exists": art_status.exists,
            "is_empty_state": art_status.is_empty_state,
            "item_count": art_status.item_count,
        }

    # ── 16. Founder inbox summary ───────────────────────────────────
    founder_inbox_summary = {
        "present": status.founder_inbox_present,
        "review_item_count": status.founder_inbox_review_item_count,
    }

    # ── 17. Recommendation ──────────────────────────────────────────
    recommended_next_step = status.recommended_next_step

    # ── 18. Validation ──────────────────────────────────────────────
    validation_passed = status.validation_passed and len(errors) == 0

    return WeeklyRunReport(
        run_id=run_id,
        generated_at=resolved_generated_at,
        status_summary=status_summary,
        artifact_summary=artifact_summary,
        pipeline_counts=pipeline_counts,
        founder_inbox_summary=founder_inbox_summary,
        decision_import_summary={
            "quality_gate_summary": quality_gate_summary,
            "decision_summary": decision_summary,
            "action_summary": action_summary,
            "parking_lot_summary": {
                "record_count": status.parking_lot_record_count,
                "revisit_match_count": 0,
            },
            "traceability_summary": traceability_summary,
            "preference_warnings": preference_warnings,
            "review_completion": review_completion,
        },
        import_history_summary=build_import_history_summary(run_dir),
        warnings=warnings,
        errors=errors,
        recommended_next_step=recommended_next_step,
        artifact_paths=artifact_paths,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
        validation_passed=validation_passed,
    )


# ============================================================================
# Per-run report writers
# ============================================================================


def write_weekly_run_report(
    report: WeeklyRunReport,
    run_dir: Path,
) -> tuple[Path, Path]:
    """Write run_report.json and run_report.md into *run_dir*.

    Returns (json_path, md_path).
    """
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    json_path = run_dir / "run_report.json"
    json_path.write_text(
        _stable_json_dumps(report.to_dict()),
        encoding="utf-8",
    )

    md_path = run_dir / "run_report.md"
    md_content = render_weekly_run_report_markdown(report)
    md_path.write_text(md_content, encoding="utf-8")

    return json_path, md_path


# ============================================================================
# Per-run Markdown renderer
# ============================================================================


def render_weekly_run_report_markdown(report: WeeklyRunReport) -> str:
    """Render a WeeklyRunReport as a human-readable Markdown string."""
    lines: list[str] = []
    lines.append("# Weekly Run Report")
    lines.append("")
    lines.append(f"- **Run ID**: `{report.run_id}`")
    lines.append(f"- **Generated**: {report.generated_at}")
    lines.append("")
    lines.append(f"## Status Summary")
    lines.append("")
    ss = report.status_summary
    lines.append(f"- **Manifest valid**: `{str(ss.get('manifest_valid', False)).lower()}`")
    lines.append(f"- **Expected artifacts**: {ss.get('expected_artifact_count', 0)}")
    lines.append(f"- **Present artifacts**: {ss.get('present_artifact_count', 0)}")
    missing = ss.get("missing_artifact_keys", [])
    if missing:
        lines.append(f"- **Missing artifacts**: {', '.join(f'`{k}`' for k in missing)}")
    lines.append("")

    lines.append("## Pipeline Counts")
    lines.append("")
    pc = report.pipeline_counts
    lines.append(f"- **Evidence packs**: {pc.get('evidence_packs', 0)}")
    lines.append(f"- **Opportunity candidates**: {pc.get('opportunity_candidates', 0)}")
    lines.append(f"- **Quality gate decisions**: {pc.get('quality_gate_decisions', 0)}")
    lines.append(f"- **Founder decisions**: {pc.get('founder_decisions', 0)}")
    lines.append(f"- **Feedback mappings**: {pc.get('feedback_mappings', 0)}")
    lines.append(f"- **Next best actions**: {pc.get('next_best_actions', 0)}")
    lines.append(f"- **Parking lot records**: {pc.get('parking_lot_records', 0)}")
    lines.append("")

    dis = report.decision_import_summary
    qgs = dis.get("quality_gate_summary", {})
    lines.append("## Quality Gate Summary")
    lines.append("")
    if qgs:
        for k, v in sorted(qgs.items()):
            lines.append(f"- **{k}**: {v}")
    else:
        lines.append("- No quality gate results.")
    lines.append("")

    ds = dis.get("decision_summary", {})
    lines.append("## Decision Summary")
    lines.append("")
    if any(ds.values()):
        for k, v in sorted(ds.items()):
            lines.append(f"- **{k}**: {v}")
    else:
        lines.append("- No founder decisions imported yet.")
    lines.append("")

    action_s = dis.get("action_summary", {})
    lines.append("## Action Summary")
    lines.append("")
    if action_s:
        for k, v in sorted(action_s.items()):
            lines.append(f"- **{k}**: {v}")
    else:
        lines.append("- No next-best actions.")
    lines.append("")

    fis = report.founder_inbox_summary
    lines.append("## Founder Inbox")
    lines.append("")
    lines.append(f"- **Present**: `{str(fis.get('present', False)).lower()}`")
    lines.append(f"- **Review items**: {fis.get('review_item_count', 0)}")
    lines.append("")

    pls = dis.get("parking_lot_summary", {})
    lines.append("## Parking Lot")
    lines.append("")
    lines.append(f"- **Records**: {pls.get('record_count', 0)}")
    lines.append(f"- **Revisit matches**: {pls.get('revisit_match_count', 0)}")
    lines.append("")

    trace = dis.get("traceability_summary", {})
    lines.append("## Traceability")
    lines.append("")
    lines.append(f"- **Unique evidence IDs**: {trace.get('unique_evidence_ids', 0)}")
    lines.append(f"- **Unique signal IDs**: {trace.get('unique_signal_ids', 0)}")
    lines.append(f"- **Unique source URLs**: {trace.get('unique_source_urls', 0)}")
    lines.append(f"- **Unique opportunity IDs**: {trace.get('unique_opportunity_ids', 0)}")
    lines.append("")

    pw = dis.get("preference_warnings", [])
    lines.append("## Import History / Audit Trail")
    lines.append("")
    ihs = report.import_history_summary
    if ihs.get("present"):
        lines.append(f"- **Correction entries**: {ihs.get('entry_count', 0)}")
        lines.append(f"- **Latest correction mode**: `{ihs.get('latest_correction_mode', '')}`")
        mode_counts = ihs.get("mode_counts", {})
        if mode_counts:
            mc_str = ", ".join(f"`{m}`: {c}" for m, c in sorted(mode_counts.items()))
            lines.append(f"- **Corrections by mode**: {mc_str}")
        replaced = ihs.get("replaced_decision_ids", [])
        if replaced:
            lines.append(f"- **Replaced decision IDs**: {', '.join(f'`{did}`' for did in replaced)}")
        amended = ihs.get("amended_decision_ids", [])
        if amended:
            lines.append(f"- **Amended decision IDs**: {', '.join(f'`{did}`' for did in amended)}")
        # Per-correction details (v2.8 item 3.1)
        if ihs.get("entry_count", 0) > 0:
            lines.append("")
            lines.append("### Per-Correction Details")
            lines.append("")
            for i in range(ihs.get("entry_count", 0)):
                lines.append(f"**Correction {i+1}**: see `weekly_cycle_status` / `import_history.json` for full details.")
            lines.append("")
    else:
        lines.append("- No corrections recorded.")
    lines.append("")
    lines.append("## Preference Profile Warnings")
    lines.append("")
    if pw:
        for w in pw:
            lines.append(f"- {w}")
    else:
        lines.append("- None")
    lines.append("")

    rc = dis.get("review_completion", 0.0)
    lines.append(f"## Review Completion: {rc:.0%}")
    lines.append("")

    lines.append("## Warnings")
    lines.append("")
    if report.warnings:
        for w in report.warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Errors")
    lines.append("")
    if report.errors:
        for e in report.errors:
            lines.append(f"- {e}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Recommended Next Step")
    lines.append("")
    lines.append(report.recommended_next_step if report.recommended_next_step else "N/A")
    lines.append("")

    lines.append("## Artifact Paths")
    lines.append("")
    for key in sorted(report.artifact_paths.keys()):
        lines.append(f"- `{report.artifact_paths[key]}`")
    lines.append("")

    lines.append("## Safety Flags")
    lines.append("")
    lines.append(f"- **advisory_only**: `{str(report.advisory_only).lower()}`")
    lines.append(f"- **no_live_api**: `{str(report.no_live_api).lower()}`")
    lines.append(f"- **no_live_llm**: `{str(report.no_live_llm).lower()}`")
    lines.append(f"- **validation_passed**: `{str(report.validation_passed).lower()}`")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ============================================================================
# Dashboard index builder
# ============================================================================


def build_weekly_dashboard_index(
    project_root: Path,
) -> WeeklyDashboardIndex:
    """Build a deterministic cross-run dashboard index.

    Scans all run directories under ``artifacts/weekly_runs/``, reads each
    run's manifest and status, and builds a cross-run summary.

    Args:
        project_root: Root directory of the OOS project.

    Returns:
        WeeklyDashboardIndex with cross-run aggregation.
    """
    project_root = project_root.resolve()
    weekly_runs_root = project_root / "artifacts" / "weekly_runs"
    generated_at = _iso_utc_now()
    warnings: list[str] = []
    errors: list[str] = []

    run_dirs = _discover_run_dirs(weekly_runs_root)

    if not run_dirs:
        return WeeklyDashboardIndex(
            generated_at=generated_at,
            project_root=str(project_root),
            total_runs=0,
            latest_run_id="",
            complete_run_count=0,
            incomplete_run_count=0,
            invalid_run_count=0,
            runs=[],
            warnings=["No weekly runs found under artifacts/weekly_runs/."],
            advisory_only=True,
            no_live_api=True,
            no_live_llm=True,
        )

    latest_run_id = run_dirs[0].name  # sorted desc by name
    summaries: list[WeeklyDashboardRunSummary] = []
    complete_count = 0
    incomplete_count = 0
    invalid_count = 0

    for run_dir in run_dirs:
        rid = run_dir.name
        status = build_weekly_cycle_status(project_root=project_root, run_id=rid)

        present_count = status.present_artifact_count
        expected_count = status.expected_artifact_count
        missing_count = expected_count - present_count

        if not status.manifest_valid:
            invalid_count += 1
        elif status.validation_passed and status.founder_decisions_imported:
            complete_count += 1
        elif status.validation_passed:
            incomplete_count += 1
        else:
            incomplete_count += 1

        summary = WeeklyDashboardRunSummary(
            run_id=rid,
            run_dir=str(run_dir),
            manifest_valid=status.manifest_valid,
            validation_passed=status.validation_passed,
            present_artifact_count=present_count,
            expected_artifact_count=expected_count,
            missing_artifact_count=missing_count,
            founder_inbox_review_item_count=status.founder_inbox_review_item_count,
            founder_decision_count=status.founder_decision_count,
            next_best_action_count=status.next_best_action_count,
            correction_count=status.import_history_entry_count,
            warning_count=len(status.warnings),
            error_count=len(status.errors),
            recommended_next_step=status.recommended_next_step,
        )
        summaries.append(summary)

        # Collect dashboard-level warnings/errors
        for w in status.warnings:
            warnings.append(f"[{rid}] {w}")
        for e in status.errors:
            errors.append(f"[{rid}] {e}")

    return WeeklyDashboardIndex(
        generated_at=generated_at,
        project_root=str(project_root),
        total_runs=len(summaries),
        latest_run_id=latest_run_id,
        complete_run_count=complete_count,
        incomplete_run_count=incomplete_count,
        invalid_run_count=invalid_count,
        runs=summaries,
        warnings=warnings,
        errors=errors,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )


# ============================================================================
# Dashboard writers
# ============================================================================


def write_weekly_dashboard_index(
    dashboard: WeeklyDashboardIndex,
    weekly_runs_root: Path,
) -> tuple[Path, Path]:
    """Write dashboard_index.json and dashboard.md into *weekly_runs_root*.

    Returns (json_path, md_path).
    """
    weekly_runs_root = weekly_runs_root.resolve()
    weekly_runs_root.mkdir(parents=True, exist_ok=True)

    json_path = weekly_runs_root / "dashboard_index.json"
    json_path.write_text(
        _stable_json_dumps(dashboard.to_dict()),
        encoding="utf-8",
    )

    md_path = weekly_runs_root / "dashboard.md"
    md_content = render_weekly_dashboard_markdown(dashboard)
    md_path.write_text(md_content, encoding="utf-8")

    return json_path, md_path


# ============================================================================
# Dashboard Markdown renderer
# ============================================================================


def render_weekly_dashboard_markdown(dashboard: WeeklyDashboardIndex) -> str:
    """Render a WeeklyDashboardIndex as a human-readable Markdown string."""
    lines: list[str] = []
    lines.append("# Weekly Runs Dashboard")
    lines.append("")
    lines.append(f"- **Generated**: {dashboard.generated_at}")
    lines.append(f"- **Project root**: `{dashboard.project_root}`")
    lines.append("")

    lines.append("## Aggregate Metrics")
    lines.append("")
    lines.append(f"- **Total runs**: {dashboard.total_runs}")
    lines.append(f"- **Latest run**: `{dashboard.latest_run_id}`")
    lines.append(f"- **Complete runs**: {dashboard.complete_run_count}")
    lines.append(f"- **Incomplete runs**: {dashboard.incomplete_run_count}")
    lines.append(f"- **Invalid runs**: {dashboard.invalid_run_count}")
    lines.append("")

    if dashboard.runs:
        lines.append("## Run Summary Table")
        lines.append("")
        lines.append(
            "| Run ID | Manifest | Valid | Artifacts | Inbox Items | Decisions | Corrections | Actions | Warnings | Errors | Recommended Next Step |"
        )
        lines.append(
            "|--------|----------|-------|-----------|-------------|-----------|-------------|---------|----------|--------|------------------------|"
        )
        for r in dashboard.runs:
            manifest_mark = "✓" if r.manifest_valid else "✗"
            valid_mark = "✓" if r.validation_passed else "✗"
            artifacts_str = f"{r.present_artifact_count}/{r.expected_artifact_count}"
            corr_str = f"{r.correction_count} [CORRECTED]" if r.correction_count > 0 else "0"
            rec = r.recommended_next_step[:60] + "..." if len(r.recommended_next_step) > 60 else r.recommended_next_step
            lines.append(
                f"| `{r.run_id}` | {manifest_mark} | {valid_mark} | {artifacts_str} | {r.founder_inbox_review_item_count} | {r.founder_decision_count} | {corr_str} | {r.next_best_action_count} | {r.warning_count} | {r.error_count} | {rec} |"
            )
        lines.append("")

    lines.append("## Warnings")
    lines.append("")
    if dashboard.warnings:
        for w in dashboard.warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Errors")
    lines.append("")
    if dashboard.errors:
        for e in dashboard.errors:
            lines.append(f"- {e}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Safety Flags")
    lines.append("")
    lines.append(f"- **advisory_only**: `{str(dashboard.advisory_only).lower()}`")
    lines.append(f"- **no_live_api**: `{str(dashboard.no_live_api).lower()}`")
    lines.append(f"- **no_live_llm**: `{str(dashboard.no_live_llm).lower()}`")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
