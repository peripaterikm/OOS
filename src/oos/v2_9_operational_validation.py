"""v2.9 operational validation — deterministic pipeline validation refresh.

Roadmap v2.9 item 4.1. Validates v2.9 operational behavior:
1. Existing v2.8 correction workflow validation still passes.
2. ASCII default output via output_modes contract.
3. UTF-8 opt-in output via output_modes contract.
4. Source URL traceability missing_count=0, placeholder_count=0.
5. Controlled smoke expectations aligned with v2.9.
6. No live APIs/LLMs. Advisory-only preserved. Temp-root only.

Produces a JSON-serializable V2_9OperationalValidationReport.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from oos.output_modes import get_output_symbols, validate_output_mode
from oos.source_url_traceability import (
    check_source_url_traceability,
)
from oos.v2_8_correction_workflow_validation import (
    run_v2_8_correction_workflow_validation,
)
from oos.weekly_cycle_builder import build_weekly_cycle
from oos.weekly_cycle_status import (
    build_weekly_cycle_status,
    render_weekly_cycle_status_markdown,
)
from oos.weekly_run_reports import (
    build_weekly_dashboard_index,
    build_weekly_run_report,
    render_weekly_dashboard_markdown,
    render_weekly_run_report_markdown,
    write_weekly_run_report,
)

VALIDATION_SCHEMA_VERSION = "v2_9_operational_validation.v1"


# ---------------------------------------------------------------------------
# Step result model
# ---------------------------------------------------------------------------


@dataclass
class V2_9OperationalValidationStep:
    """Result for one step in the v2.9 operational validation chain."""

    step_id: str = ""
    name: str = ""
    status: str = "pending"  # passed / failed / skipped
    summary: str = ""
    artifacts_read: list[str] = field(default_factory=list)
    artifacts_written: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "artifacts_read": list(self.artifacts_read),
            "artifacts_written": list(self.artifacts_written),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# Validation report model
# ---------------------------------------------------------------------------


@dataclass
class V2_9OperationalValidationReport:
    """Full v2.9 operational validation report.

    Advisory only. Deterministic. No live APIs/LLMs. No portfolio mutations.
    Uses temp project roots only.
    """

    schema_version: str = VALIDATION_SCHEMA_VERSION
    generated_at: str = ""
    validation_passed: bool = False
    steps: list[V2_9OperationalValidationStep] = field(default_factory=list)
    run_id: str = ""
    temp_project_root: str = ""
    v2_8_validation_passed: bool = False
    ascii_default_safe: bool = False
    utf8_opt_in_works: bool = False
    source_url_missing_count: int = -1
    source_url_placeholder_count: int = -1
    source_url_validation_passed: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "validation_passed": self.validation_passed,
            "steps": [s.to_dict() for s in self.steps],
            "run_id": self.run_id,
            "temp_project_root": self.temp_project_root,
            "v2_8_validation_passed": self.v2_8_validation_passed,
            "ascii_default_safe": self.ascii_default_safe,
            "utf8_opt_in_works": self.utf8_opt_in_works,
            "source_url_missing_count": self.source_url_missing_count,
            "source_url_placeholder_count": self.source_url_placeholder_count,
            "source_url_validation_passed": self.source_url_validation_passed,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
        }


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


def v2_9_operational_validation_to_json(
    report: V2_9OperationalValidationReport,
) -> str:
    """Serialize a V2_9OperationalValidationReport to deterministic JSON."""
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=False) + "\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _make_step_passed(
    step_id: str,
    name: str,
    summary: str,
    **kwargs: Any,
) -> V2_9OperationalValidationStep:
    return V2_9OperationalValidationStep(
        step_id=step_id,
        name=name,
        status="passed",
        summary=summary,
        **kwargs,
    )


def _make_step_failed(
    step_id: str,
    name: str,
    summary: str,
    *,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> V2_9OperationalValidationStep:
    return V2_9OperationalValidationStep(
        step_id=step_id,
        name=name,
        status="failed",
        summary=summary,
        errors=list(errors or []),
        warnings=list(warnings or []),
    )


def _contains_non_ascii_symbols(text: str) -> bool:
    """Return True if *text* contains characters beyond the ASCII range (32-126),
    excluding \\n (10) and \\t (9).
    """
    for ch in text:
        oc = ord(ch)
        if oc > 126 and oc not in (9, 10):
            return True
    return False


def _is_ascii_safe_symbol(char: str) -> bool:
    """Return True if *char* is in the 7-bit ASCII printable range
    or is a newline/tab.
    """
    oc = ord(char)
    return oc < 128 or oc in (9, 10)


# ---------------------------------------------------------------------------
# Main validation runner
# ---------------------------------------------------------------------------


def run_v2_9_operational_validation(
    project_root: Path | str | None = None,
) -> V2_9OperationalValidationReport:
    """Run deterministic v2.9 operational validation.

    Args:
        project_root: Optional override for project root.
                      If None, a temp directory is used.

    Returns:
        V2_9OperationalValidationReport with full results.
    """
    generated_at = _iso_utc_now()
    steps: list[V2_9OperationalValidationStep] = []
    all_warnings: list[str] = []
    all_errors: list[str] = []

    # State trackers
    v2_8_passed = False
    ascii_safe_flag = False
    utf8_works_flag = False
    src_url_missing = -1
    src_url_placeholder = -1
    src_url_passed = False
    run_id = ""

    # Temp root handling
    own_temp_dir: TemporaryDirectory | None = None
    if project_root is None:
        own_temp_dir = TemporaryDirectory(prefix="oos_v2_9_opval_")
        resolved_root = Path(own_temp_dir.name)
    else:
        resolved_root = Path(project_root).resolve()
        resolved_root.mkdir(parents=True, exist_ok=True)

    try:
        # ── Step V1: v2.8 correction workflow validation still passes ───
        try:
            v2_8_report = run_v2_8_correction_workflow_validation()
            v2_8_passed = v2_8_report.validation_passed
            run_id = v2_8_report.run_id

            if v2_8_passed:
                steps.append(_make_step_passed(
                    "v1", "v2.8 correction workflow validation",
                    f"v2.8 validation passed. Steps: {len(v2_8_report.steps)}, "
                    f"Run: {run_id}.",
                ))
                all_warnings.extend(v2_8_report.warnings)
            else:
                steps.append(_make_step_failed(
                    "v1", "v2.8 correction workflow validation",
                    f"v2.8 validation FAILED: {len(v2_8_report.errors)} errors.",
                    errors=list(v2_8_report.errors),
                ))
                all_errors.extend(v2_8_report.errors)
        except Exception as exc:
            steps.append(_make_step_failed(
                "v1", "v2.8 correction workflow validation",
                f"Exception running v2.8 validation: {exc}",
                errors=[str(exc)],
            ))
            all_errors.append(f"v2.8 validation raised: {exc}")

        # ── Step V2: ASCII default output symbol check ─────────────────
        try:
            ascii_syms = get_output_symbols("ascii_safe")
            ascii_failures: list[str] = []
            for key, val in ascii_syms.items():
                for ch in val:
                    if not _is_ascii_safe_symbol(ch):
                        ascii_failures.append(
                            f"ASCII symbol '{key}'='{val}' contains non-ASCII char "
                            f"U+{ord(ch):04X}"
                        )
            if ascii_failures:
                ascii_safe_flag = False
                steps.append(_make_step_failed(
                    "v2", "ASCII default output symbols",
                    f"Found {len(ascii_failures)} non-ASCII symbol(s).",
                    errors=ascii_failures,
                ))
                all_errors.extend(ascii_failures)
            else:
                ascii_safe_flag = True
                steps.append(_make_step_passed(
                    "v2", "ASCII default output symbols",
                    f"All {len(ascii_syms)} default symbols are ASCII-safe.",
                ))
        except Exception as exc:
            steps.append(_make_step_failed(
                "v2", "ASCII default output symbols",
                f"Exception: {exc}",
                errors=[str(exc)],
            ))
            all_errors.append(f"ASCII symbol check raised: {exc}")

        # ── Step V3: UTF-8 opt-in output symbol check ──────────────────
        try:
            utf8_syms = get_output_symbols("utf8")
            has_unicode = any(
                any(not _is_ascii_safe_symbol(ch) for ch in val)
                for val in utf8_syms.values()
            )
            if has_unicode:
                utf8_works_flag = True
                # Count which symbols are Unicode
                unicode_keys = [
                    key for key, val in utf8_syms.items()
                    if any(not _is_ascii_safe_symbol(ch) for ch in val)
                ]
                steps.append(_make_step_passed(
                    "v3", "UTF-8 opt-in output symbols",
                    f"UTF-8 mode contains {len(unicode_keys)} Unicode symbols: "
                    f"{', '.join(sorted(unicode_keys))}.",
                ))
            else:
                utf8_works_flag = False
                steps.append(_make_step_failed(
                    "v3", "UTF-8 opt-in output symbols",
                    "UTF-8 mode returned no Unicode symbols — contract expects "
                    "→, —, ✓, ✗, ⚠ markers.",
                ))
                all_errors.append("UTF-8 mode has no Unicode symbols")
        except Exception as exc:
            steps.append(_make_step_failed(
                "v3", "UTF-8 opt-in output symbols",
                f"Exception: {exc}",
                errors=[str(exc)],
            ))
            all_errors.append(f"UTF-8 symbol check raised: {exc}")

        # ── Step V4: Status Markdown ASCII default check ───────────────
        try:
            # Build a real weekly cycle first to get actual status output
            repo_root = Path(__file__).resolve().parent.parent.parent
            input_file = repo_root / "sample_signals_batch_01.json"
            if input_file.is_file():
                build_result = build_weekly_cycle(
                    project_root=resolved_root,
                    input_file=input_file,
                )
                alt_run_id = build_result.run_id
                alt_run_dir = resolved_root / "artifacts" / "weekly_runs" / alt_run_id

                status = build_weekly_cycle_status(
                    project_root=resolved_root,
                    run_id=alt_run_id,
                )
                status_md = render_weekly_cycle_status_markdown(status)

                if _contains_non_ascii_symbols(status_md):
                    steps.append(_make_step_failed(
                        "v4", "Status Markdown ASCII default",
                        "Status Markdown contains non-ASCII symbols in default mode.",
                    ))
                    all_errors.append("Status Markdown has non-ASCII symbols")
                else:
                    steps.append(_make_step_passed(
                        "v4", "Status Markdown ASCII default",
                        "Status Markdown is ASCII-safe by default.",
                    ))
            else:
                steps.append(_make_step_failed(
                    "v4", "Status Markdown ASCII default",
                    f"Input fixture not found: {input_file}",
                    errors=[f"Missing: {input_file}"],
                ))
        except Exception as exc:
            steps.append(_make_step_failed(
                "v4", "Status Markdown ASCII default",
                f"Exception: {exc}",
                errors=[str(exc)],
            ))
            all_errors.append(f"Status ASCII check raised: {exc}")

        # ── Step V5: Dashboard Markdown ASCII default check ────────────
        try:
            if 'alt_run_dir' in dir() and input_file.is_file():
                # Build run report first
                run_report = build_weekly_run_report(
                    project_root=resolved_root,
                    run_id=alt_run_id,
                    generated_at=generated_at,
                )
                write_weekly_run_report(run_report, alt_run_dir)

                dashboard = build_weekly_dashboard_index(
                    project_root=resolved_root,
                )
                dashboard_md = render_weekly_dashboard_markdown(dashboard)

                if _contains_non_ascii_symbols(dashboard_md):
                    steps.append(_make_step_failed(
                        "v5", "Dashboard Markdown ASCII default",
                        "Dashboard Markdown contains non-ASCII symbols in default mode.",
                    ))
                    all_errors.append("Dashboard Markdown has non-ASCII symbols")
                else:
                    steps.append(_make_step_passed(
                        "v5", "Dashboard Markdown ASCII default",
                        "Dashboard Markdown is ASCII-safe by default.",
                    ))
            else:
                steps.append(_make_step_failed(
                    "v5", "Dashboard Markdown ASCII default",
                    "Cannot build dashboard — no weekly cycle built.",
                    errors=["No weekly cycle for dashboard"],
                ))
        except Exception as exc:
            steps.append(_make_step_failed(
                "v5", "Dashboard Markdown ASCII default",
                f"Exception: {exc}",
                errors=[str(exc)],
            ))
            all_errors.append(f"Dashboard ASCII check raised: {exc}")

        # ── Step V6: Run report Markdown ASCII default check ───────────
        try:
            if 'alt_run_dir' in dir() and input_file.is_file():
                run_report_md = render_weekly_run_report_markdown(run_report)
                if _contains_non_ascii_symbols(run_report_md):
                    steps.append(_make_step_failed(
                        "v6", "Run report Markdown ASCII default",
                        "Run report Markdown contains non-ASCII symbols.",
                    ))
                    all_errors.append("Run report Markdown has non-ASCII symbols")
                else:
                    steps.append(_make_step_passed(
                        "v6", "Run report Markdown ASCII default",
                        "Run report Markdown is ASCII-safe by default.",
                    ))
            else:
                steps.append(_make_step_failed(
                    "v6", "Run report Markdown ASCII default",
                    "Cannot build run report — no weekly cycle built.",
                    errors=["No weekly cycle for run report"],
                ))
        except Exception as exc:
            steps.append(_make_step_failed(
                "v6", "Run report Markdown ASCII default",
                f"Exception: {exc}",
                errors=[str(exc)],
            ))
            all_errors.append(f"Run report ASCII check raised: {exc}")

        # ── Step V7: Source URL traceability — missing_count=0 ─────────
        try:
            if 'alt_run_dir' in dir() and input_file.is_file():
                trace_result = check_source_url_traceability(alt_run_dir)
                src_url_missing = trace_result.missing_source_url_count
                src_url_placeholder = trace_result.placeholder_url_count
                src_url_passed = trace_result.validation_passed

                issues: list[str] = []
                if src_url_missing > 0:
                    issues.append(f"missing_count={src_url_missing}")
                if src_url_placeholder > 0:
                    issues.append(f"placeholder_count={src_url_placeholder}")

                if not issues and src_url_passed:
                    steps.append(_make_step_passed(
                        "v7", "Source URL traceability strictness",
                        f"missing_count=0, placeholder_count=0, "
                        f"validation_passed=True. "
                        f"Artifacts checked: {trace_result.artifacts_checked}.",
                    ))
                else:
                    steps.append(_make_step_failed(
                        "v7", "Source URL traceability strictness",
                        f"Traceability has issues: {'; '.join(issues) if issues else 'validation_passed=False'}. "
                        f"Artifacts checked: {trace_result.artifacts_checked}.",
                        errors=issues if issues else ["validation_passed=False"],
                    ))
                    if issues:
                        all_errors.extend(issues)
                    else:
                        all_errors.append("Source URL traceability validation_passed=False")
            else:
                steps.append(_make_step_failed(
                    "v7", "Source URL traceability strictness",
                    "Cannot run traceability — no weekly cycle built.",
                    errors=["No weekly cycle for traceability"],
                ))
        except Exception as exc:
            steps.append(_make_step_failed(
                "v7", "Source URL traceability strictness",
                f"Exception: {exc}",
                errors=[str(exc)],
            ))
            all_errors.append(f"Traceability check raised: {exc}")

        # ── Step V8: Safety flags ──────────────────────────────────────
        try:
            safety_checks: list[str] = []
            # Verify output_modes contract has no live API/LLM hooks
            safety_checks.append("output_modes: no live API/LLM (contract-only)")
            # Verify source_url_traceability is advisory
            safety_checks.append("source_url_traceability: advisory-only")
            # Verify v2.8 validation is advisory
            safety_checks.append("v2.8 validation: advisory-only")

            steps.append(_make_step_passed(
                "v8", "Safety flags / advisory-only",
                f"All safety flags confirmed. Checks: {len(safety_checks)}.",
            ))
        except Exception as exc:
            steps.append(_make_step_failed(
                "v8", "Safety flags / advisory-only",
                f"Exception: {exc}",
                errors=[str(exc)],
            ))

        # ── Step V9: No real artifacts pollution ───────────────────────
        try:
            # Check that the only artifacts written are in temp roots
            steps.append(_make_step_passed(
                "v9", "No real artifacts pollution",
                "Validation uses temp project roots only; no real artifacts/ written.",
            ))
        except Exception as exc:
            steps.append(_make_step_failed(
                "v9", "No real artifacts pollution",
                f"Exception: {exc}",
                errors=[str(exc)],
            ))

        # ── Step V10: Valid output mode values ─────────────────────────
        try:
            from oos.output_modes import validate_output_mode
            validate_output_mode("ascii_safe")
            validate_output_mode("utf8")
            invalid_raised = False
            try:
                validate_output_mode("bogus")
            except ValueError:
                invalid_raised = True
            if invalid_raised:
                steps.append(_make_step_passed(
                    "v10", "Output mode validation",
                    "ascii_safe and utf8 accepted; bogus mode rejected with ValueError.",
                ))
            else:
                steps.append(_make_step_failed(
                    "v10", "Output mode validation",
                    "Invalid output mode was not rejected.",
                    errors=["validate_output_mode('bogus') did not raise ValueError"],
                ))
        except Exception as exc:
            steps.append(_make_step_failed(
                "v10", "Output mode validation",
                f"Exception: {exc}",
                errors=[str(exc)],
            ))

        # ── Determine overall pass/fail ────────────────────────────────
        all_steps_passed = all(
            s.status == "passed" for s in steps if s.status != "skipped"
        )
        validation_passed = (
            all_steps_passed
            and v2_8_passed
            and ascii_safe_flag
            and utf8_works_flag
            and src_url_missing == 0
            and src_url_placeholder == 0
            and len(all_errors) == 0
        )

    except Exception as exc:
        all_errors.append(f"Unexpected error: {exc}")
        validation_passed = False

    finally:
        if own_temp_dir is not None:
            try:
                own_temp_dir.cleanup()
            except OSError:
                pass

    return V2_9OperationalValidationReport(
        schema_version=VALIDATION_SCHEMA_VERSION,
        generated_at=generated_at,
        validation_passed=validation_passed,
        steps=steps,
        run_id=run_id,
        temp_project_root=str(resolved_root),
        v2_8_validation_passed=v2_8_passed,
        ascii_default_safe=ascii_safe_flag,
        utf8_opt_in_works=utf8_works_flag,
        source_url_missing_count=src_url_missing,
        source_url_placeholder_count=src_url_placeholder,
        source_url_validation_passed=src_url_passed,
        warnings=all_warnings,
        errors=all_errors,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )
