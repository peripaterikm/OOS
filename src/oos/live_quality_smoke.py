from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


STATUS_PASS = "pass"
STATUS_WARNING = "warning"
STATUS_FAIL = "fail"

_STATUS_RANK = {STATUS_PASS: 0, STATUS_WARNING: 1, STATUS_FAIL: 2}

_MOJIBAKE_MARKERS = (
    "\u0432\u0402",  # Cyrillic mojibake for smart punctuation, e.g. вЂ
    "\u0440\u045f",  # Cyrillic mojibake for emoji fragments, e.g. рџ
    "\u0420\u045f",  # uppercase variant, e.g. Рџ
    "\u00e2\u20ac\u2122",  # â€™
    "\u00e2\u20ac\u201d",  # â€”
)

_INSTALL_TUTORIAL_MARKERS = (
    "installation process",
    "will restart",
    "will launch",
    "click next",
    "setup wizard",
    "how to install",
    "installation guide",
)

_GENERIC_COPY_MARKERS = (
    "in today's fast-moving business environment",
    "are no longer optional",
    "gain visibility into their operations",
    "financial transparency",
    "strategic reporting",
    "trusted partner",
    "our services",
)

_USER_PAIN_MARKERS = (
    "describe alternatives",
    "describe the solution you'd like",
    "would need to maintain",
    "separate spreadsheet",
    "balance sheet",
    "invoice",
    "invoice payment",
    "following up on my invoice",
    "manual spreadsheet",
    "current workaround",
    "i would like",
    "i want to",
    "i built this because",
    "tired of",
    "cash flow",
    "bookkeeping",
    "accounting software",
)

KNOWN_LIMITATIONS = [
    "Generic finance or consulting copy can still rank too high until semantic/LLM review layers are added.",
    "User-pain-like matching is deterministic and heuristic; founder review remains required.",
]

RECOMMENDED_NEXT_STEP = "Proceed to Roadmap v2.4 item 2.1: Customer Voice Query Generator contract and artifacts."


@dataclass(frozen=True)
class LiveQualitySmokeReport:
    run_id: str
    role: str
    collection_mode: str
    live_network_enabled: bool
    raw_evidence_count: int
    candidate_signal_count: int
    needs_human_review_count: int
    noise_count: int
    collectors_attempted: list[str]
    collectors_succeeded: list[str]
    collectors_failed: list[str]
    duplicate_top_source_urls: list[str]
    mojibake_findings: list[str]
    install_tutorial_top_findings: list[str]
    generic_copy_top_findings: list[str]
    rss_missing_feed_url_controlled_skip: bool
    top_user_pain_like_count: int
    passed_checks: list[str]
    failed_checks: list[str]
    warnings: list[str]
    overall_status: str


@dataclass(frozen=True)
class LiveQualitySmokeAggregateReport:
    runs: list[LiveQualitySmokeReport]
    aggregate_status: str
    aggregate_failed_checks: list[str]
    aggregate_warnings: list[str]
    known_limitations: list[str]
    recommended_next_step: str


def build_live_quality_smoke_report(
    *,
    project_root: Path,
    run_ids: Iterable[str] | None = None,
    run_roles: Mapping[str, str] | None = None,
    run_dirs: Iterable[Path] | None = None,
) -> LiveQualitySmokeAggregateReport:
    project_root = Path(project_root).resolve()
    roles = dict(run_roles or {})
    reports: list[LiveQualitySmokeReport] = []
    for run_id in run_ids or []:
        run_dir = project_root / "artifacts" / "discovery_runs" / run_id
        reports.append(validate_live_quality_run(run_dir=run_dir, role=roles.get(run_id) or infer_run_role(run_id)))
    for run_dir in run_dirs or []:
        run_path = Path(run_dir)
        reports.append(validate_live_quality_run(run_dir=run_path, role=roles.get(run_path.name) or infer_run_role(run_path.name)))

    aggregate_status = _combine_status(report.overall_status for report in reports)
    aggregate_failed_checks = [f"{report.run_id}: {check}" for report in reports for check in report.failed_checks]
    aggregate_warnings = [f"{report.run_id}: {warning}" for report in reports for warning in report.warnings]
    return LiveQualitySmokeAggregateReport(
        runs=reports,
        aggregate_status=aggregate_status,
        aggregate_failed_checks=aggregate_failed_checks,
        aggregate_warnings=aggregate_warnings,
        known_limitations=list(KNOWN_LIMITATIONS),
        recommended_next_step=RECOMMENDED_NEXT_STEP,
    )


def validate_live_quality_run(*, run_dir: Path, role: str | None = None) -> LiveQualitySmokeReport:
    run_dir = Path(run_dir)
    run_id = run_dir.name
    resolved_role = role or infer_run_role(run_id)
    summary = _read_json(run_dir / "discovery_run_summary.json", default={})
    founder_package = _read_json(run_dir / "founder_discovery_package.json", default={})
    meaning_loop = _read_json(run_dir / "meaning_loop_dry_run.json", default=None)

    top_signals = _as_list(founder_package.get("top_candidate_signals"))
    collection_errors = _as_list(summary.get("collection_errors"))
    duplicate_urls = _duplicate_top_source_urls(top_signals)
    mojibake_findings = _top_findings(top_signals, _MOJIBAKE_MARKERS)
    install_findings = _top_findings(top_signals[:5], _INSTALL_TUTORIAL_MARKERS)
    generic_findings = _top_findings(top_signals[:5], _GENERIC_COPY_MARKERS)
    user_pain_count = _top_user_pain_like_count(top_signals[:3])
    rss_controlled_skip = _is_rss_controlled_skip(summary, collection_errors)

    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []

    if summary:
        passed.append("summary_present")
    else:
        failed.append("summary_missing")
    if founder_package:
        passed.append("founder_package_present")
    else:
        failed.append("founder_package_missing")

    collection_mode = str(summary.get("collection_mode", ""))
    live_network_enabled = bool(summary.get("live_network_enabled", False))
    if collection_mode == "live_collectors":
        passed.append("collection_mode_live_collectors")
    else:
        failed.append("collection_mode_not_live_collectors")
    if live_network_enabled:
        passed.append("live_network_enabled_true")
    else:
        failed.append("live_network_not_enabled")

    if meaning_loop is None:
        failed.append("meaning_loop_dry_run_missing")
    elif int(meaning_loop.get("adapted_record_count", -1)) == int(summary.get("candidate_signal_count", 0)):
        passed.append("meaning_loop_adapted_count_matches_candidate_signal_count")
    else:
        failed.append("meaning_loop_adapted_count_mismatch")

    if duplicate_urls:
        failed.append("duplicate_top_source_urls")
    else:
        passed.append("top_source_urls_deduplicated")
    if mojibake_findings:
        failed.append("mojibake_in_top_signal_summary")
    else:
        passed.append("top_signal_summaries_mojibake_free")
    if install_findings:
        failed.append("install_or_tutorial_content_in_top_5")
    else:
        passed.append("no_install_or_tutorial_content_in_top_5")

    if generic_findings:
        warnings.append("generic_consulting_or_marketing_copy_in_top_5")
    else:
        passed.append("no_generic_consulting_copy_in_top_5")

    if resolved_role in {"github", "mixed"}:
        if int(summary.get("noise_count", 0)) > 0:
            passed.append("noise_present_for_github_or_mixed_run")
        else:
            failed.append("noise_missing_for_github_or_mixed_run")

    if user_pain_count >= 2:
        passed.append("top_3_contains_at_least_two_user_pain_like_signals")
    elif top_signals:
        warnings.append("top_3_user_pain_like_count_below_threshold")

    if resolved_role == "rss":
        if rss_controlled_skip:
            passed.append("rss_missing_feed_url_controlled_skip")
        else:
            failed.append("rss_missing_feed_url_not_controlled")
        if _has_unknown_url_type(collection_errors):
            failed.append("rss_unknown_url_type_error")
        else:
            passed.append("rss_has_no_unknown_url_type_error")
        if _rss_failed_only_for_missing_feed(summary, collection_errors):
            failed.append("rss_missing_feed_url_marked_as_collector_failure")

    status = STATUS_FAIL if failed else STATUS_WARNING if warnings else STATUS_PASS
    return LiveQualitySmokeReport(
        run_id=run_id,
        role=resolved_role,
        collection_mode=collection_mode,
        live_network_enabled=live_network_enabled,
        raw_evidence_count=int(summary.get("raw_evidence_count", 0)),
        candidate_signal_count=int(summary.get("candidate_signal_count", 0)),
        needs_human_review_count=int(summary.get("needs_human_review_count", 0)),
        noise_count=int(summary.get("noise_count", 0)),
        collectors_attempted=sorted(str(item) for item in _as_list(summary.get("collectors_attempted"))),
        collectors_succeeded=sorted(str(item) for item in _as_list(summary.get("collectors_succeeded"))),
        collectors_failed=sorted(str(item) for item in _as_list(summary.get("collectors_failed"))),
        duplicate_top_source_urls=duplicate_urls,
        mojibake_findings=mojibake_findings,
        install_tutorial_top_findings=install_findings,
        generic_copy_top_findings=generic_findings,
        rss_missing_feed_url_controlled_skip=rss_controlled_skip,
        top_user_pain_like_count=user_pain_count,
        passed_checks=passed,
        failed_checks=failed,
        warnings=warnings,
        overall_status=status,
    )


def infer_run_role(run_id: str) -> str:
    lowered = run_id.lower()
    if "rss" in lowered:
        return "rss"
    if "github" in lowered:
        return "github"
    if "mix" in lowered or "mixed" in lowered:
        return "mixed"
    if "hn" in lowered or "hacker" in lowered:
        return "hn"
    return "live"


def write_live_quality_smoke_reports(
    *,
    aggregate: LiveQualitySmokeAggregateReport,
    output_json: Path,
    output_md: Path,
) -> tuple[Path, Path]:
    output_json = Path(output_json)
    output_md = Path(output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(aggregate_to_dict(aggregate), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(live_quality_smoke_markdown(aggregate), encoding="utf-8")
    return output_json, output_md


def aggregate_to_dict(aggregate: LiveQualitySmokeAggregateReport) -> dict[str, Any]:
    return {
        "runs": [asdict(report) for report in aggregate.runs],
        "aggregate_status": aggregate.aggregate_status,
        "aggregate_failed_checks": list(aggregate.aggregate_failed_checks),
        "aggregate_warnings": list(aggregate.aggregate_warnings),
        "known_limitations": list(aggregate.known_limitations),
        "recommended_next_step": aggregate.recommended_next_step,
    }


def live_quality_smoke_markdown(aggregate: LiveQualitySmokeAggregateReport) -> str:
    lines = [
        "# Live Quality Acceptance Smoke",
        "",
        "## Summary",
        "",
        f"- Aggregate status: `{aggregate.aggregate_status}`",
        f"- Runs checked: `{len(aggregate.runs)}`",
        f"- Failed checks: `{len(aggregate.aggregate_failed_checks)}`",
        f"- Warnings: `{len(aggregate.aggregate_warnings)}`",
        "",
        "## Runs checked",
        "",
    ]
    if aggregate.runs:
        for report in aggregate.runs:
            lines.extend(
                [
                    f"- `{report.run_id}` ({report.role}) -> `{report.overall_status}`",
                    f"  - Raw evidence: `{report.raw_evidence_count}`",
                    f"  - Candidate signals: `{report.candidate_signal_count}`",
                    f"  - Noise: `{report.noise_count}`",
                    f"  - Top user-pain-like count: `{report.top_user_pain_like_count}`",
                ]
            )
    else:
        lines.append("- No runs were checked.")

    lines.extend(["", "## Acceptance checks", ""])
    for report in aggregate.runs:
        lines.append(f"### `{report.run_id}`")
        lines.append("")
        for check in report.passed_checks:
            lines.append(f"- PASS: `{check}`")
        for check in report.failed_checks:
            lines.append(f"- FAIL: `{check}`")
        for warning in report.warnings:
            lines.append(f"- WARNING: `{warning}`")
        lines.append("")

    lines.extend(["## Failures", ""])
    if aggregate.aggregate_failed_checks:
        for check in aggregate.aggregate_failed_checks:
            lines.append(f"- `{check}`")
    else:
        lines.append("- None.")

    lines.extend(["", "## Warnings / known limitations", ""])
    if aggregate.aggregate_warnings:
        for warning in aggregate.aggregate_warnings:
            lines.append(f"- `{warning}`")
    else:
        lines.append("- No run-specific warnings.")
    for limitation in aggregate.known_limitations:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            "## Recommended next step",
            "",
            f"- {aggregate.recommended_next_step}",
            "",
            "## Manual live commands used or expected",
            "",
            "- `live_hn_002`",
            "- `live_github_003`",
            "- `live_mix_003`",
            "- `live_rss_002`",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_json(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _duplicate_top_source_urls(top_signals: list[Any]) -> list[str]:
    seen: set[tuple[str, str]] = set()
    duplicates: set[str] = set()
    for signal in top_signals:
        if not isinstance(signal, dict):
            continue
        source_url = str(signal.get("source_url", "")).strip()
        if not source_url:
            continue
        source_type = str(signal.get("source_type", "")).strip()
        key = (source_type, source_url)
        if key in seen:
            duplicates.add(f"{source_type}:{source_url}")
        seen.add(key)
    return sorted(duplicates)


def _top_findings(top_signals: list[Any], markers: Iterable[str]) -> list[str]:
    findings: list[str] = []
    lowered_markers = [marker.lower() for marker in markers]
    for signal in top_signals:
        if not isinstance(signal, dict):
            continue
        summary = str(signal.get("pain_summary", ""))
        lowered = summary.lower()
        matched = [marker for marker in lowered_markers if marker in lowered]
        if matched:
            findings.append(f"{signal.get('signal_id', 'unknown')}: {', '.join(matched)}")
    return findings


def _top_user_pain_like_count(top_signals: list[Any]) -> int:
    count = 0
    markers = [marker.lower() for marker in _USER_PAIN_MARKERS]
    for signal in top_signals:
        if not isinstance(signal, dict):
            continue
        text = " ".join(
            str(signal.get(key, ""))
            for key in ("pain_summary", "current_workaround", "buying_intent_hint", "source_type")
        ).lower()
        if any(marker in text for marker in markers):
            count += 1
    return count


def _is_rss_controlled_skip(summary: dict[str, Any], collection_errors: list[Any]) -> bool:
    return (
        int(summary.get("raw_evidence_count", -1)) == 0
        and _has_error_code(collection_errors, "rss_feed_url_missing")
        and not _as_list(summary.get("collectors_failed"))
    )


def _has_error_code(collection_errors: list[Any], code: str) -> bool:
    return any(isinstance(error, dict) and str(error.get("code", "")) == code for error in collection_errors)


def _has_unknown_url_type(collection_errors: list[Any]) -> bool:
    return any("unknown url type" in str(error).lower() for error in collection_errors)


def _rss_failed_only_for_missing_feed(summary: dict[str, Any], collection_errors: list[Any]) -> bool:
    failed = {str(item) for item in _as_list(summary.get("collectors_failed"))}
    return bool(failed & {"rss_feed", "rss"}) and _has_error_code(collection_errors, "rss_feed_url_missing")


def _combine_status(statuses: Iterable[str]) -> str:
    result = STATUS_PASS
    for status in statuses:
        if _STATUS_RANK.get(status, 0) > _STATUS_RANK[result]:
            result = status
    return result
