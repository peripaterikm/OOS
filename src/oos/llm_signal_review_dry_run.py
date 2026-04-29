from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .llm_signal_review import (
    EvidenceForReview,
    LLMSignalReviewInput,
    LLMSignalReviewOutput,
    build_safe_signal_review_request,
    run_deterministic_mock_signal_review,
    validate_signal_review_output,
)
from .models import CandidateSignal, CleanedEvidence, model_from_dict
from .prompt_safety import PromptSafetyPolicy


REVIEW_GOAL = "Validate whether this candidate signal reflects real user pain and extract JTBD if supported by evidence."
PROVIDER_USED = "deterministic_mock_contract_only"
DEFAULT_LIMITATIONS = [
    "Offline dry-run only.",
    "Deterministic mock review only.",
    "No real LLM provider calls.",
    "No live internet/API calls.",
    "No production LLM review execution.",
]


@dataclass(frozen=True)
class LLMSignalReviewDryRunInput:
    project_root: Path
    discovery_run_id: str | None = None
    input_candidate_signals_path: Path | None = None
    input_cleaned_evidence_path: Path | None = None
    review_run_id: str = "llm_review_dry_run_001"
    topic_id: str = "ai_cfo_smb"
    max_signals: int = 5
    min_confidence: float = 0.0
    include_needs_human_review: bool = False
    output_dir: Path | None = None

    def __post_init__(self) -> None:
        if not self.review_run_id:
            raise ValueError("review_run_id is required")
        if not self.topic_id:
            raise ValueError("topic_id is required")
        if self.max_signals < 1:
            raise ValueError("max_signals must be positive")
        if not 0.0 <= float(self.min_confidence) <= 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class LLMSignalReviewDryRunItem:
    candidate_signal_id: str
    evidence_id: str
    source_type: str | None
    source_url: str | None
    original_confidence: float | None
    review_id: str
    safe_request_built: bool
    blocked_by_prompt_safety: bool
    prompt_safety_reasons: list[str] = field(default_factory=list)
    mock_review_valid: bool = False
    validation_errors: list[str] = field(default_factory=list)
    review_output: dict[str, object] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LLMSignalReviewDryRunReport:
    review_run_id: str
    topic_id: str
    discovery_run_id: str | None
    candidate_signals_considered: int
    review_items_created: int
    safe_requests_built: int
    blocked_by_prompt_safety: int
    valid_reviews: int
    invalid_reviews: int
    llm_calls_made: bool
    external_calls_made: bool
    provider_used: str
    items: list[LLMSignalReviewDryRunItem]
    limitations: list[str]
    recommended_next_step: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["items"] = [item.to_dict() for item in self.items]
        return data


def run_llm_signal_review_dry_run(
    dry_run_input: LLMSignalReviewDryRunInput,
    *,
    policy: PromptSafetyPolicy | None = None,
    mock_review_runner: Callable[[LLMSignalReviewInput], LLMSignalReviewOutput] = run_deterministic_mock_signal_review,
) -> LLMSignalReviewDryRunReport:
    candidate_signals, cleaned_evidence = load_llm_signal_review_dry_run_artifacts(dry_run_input)
    selected_signals = select_candidate_signals_for_review(
        candidate_signals,
        max_signals=dry_run_input.max_signals,
        min_confidence=dry_run_input.min_confidence,
        include_needs_human_review=dry_run_input.include_needs_human_review,
    )
    cleaned_by_id = {item.evidence_id: item for item in cleaned_evidence}
    items: list[LLMSignalReviewDryRunItem] = []

    for signal in selected_signals:
        cleaned = cleaned_by_id.get(signal.evidence_id)
        if cleaned is None:
            items.append(
                LLMSignalReviewDryRunItem(
                    candidate_signal_id=signal.signal_id,
                    evidence_id=signal.evidence_id,
                    source_type=signal.source_type,
                    source_url=signal.source_url,
                    original_confidence=signal.confidence,
                    review_id=_review_id(dry_run_input.review_run_id, signal),
                    safe_request_built=False,
                    blocked_by_prompt_safety=False,
                    mock_review_valid=False,
                    validation_errors=["cleaned_evidence_missing"],
                    review_output=None,
                )
            )
            continue

        review_input = build_signal_review_input(
            dry_run_input=dry_run_input,
            signal=signal,
            cleaned=cleaned,
        )
        safe_request, safety_report = build_safe_signal_review_request(review_input, policy=policy)
        if safe_request is None:
            items.append(
                LLMSignalReviewDryRunItem(
                    candidate_signal_id=signal.signal_id,
                    evidence_id=signal.evidence_id,
                    source_type=signal.source_type,
                    source_url=signal.source_url,
                    original_confidence=signal.confidence,
                    review_id=review_input.review_id,
                    safe_request_built=False,
                    blocked_by_prompt_safety=True,
                    prompt_safety_reasons=list(safety_report.block_reasons),
                    mock_review_valid=False,
                    validation_errors=[],
                    review_output=None,
                )
            )
            continue

        review_output = mock_review_runner(review_input)
        valid, validation_errors = validate_signal_review_output(review_output, review_input)
        items.append(
            LLMSignalReviewDryRunItem(
                candidate_signal_id=signal.signal_id,
                evidence_id=signal.evidence_id,
                source_type=signal.source_type,
                source_url=signal.source_url,
                original_confidence=signal.confidence,
                review_id=review_input.review_id,
                safe_request_built=True,
                blocked_by_prompt_safety=False,
                prompt_safety_reasons=list(safety_report.block_reasons),
                mock_review_valid=valid,
                validation_errors=validation_errors,
                review_output=review_output.to_dict(),
            )
        )

    return LLMSignalReviewDryRunReport(
        review_run_id=dry_run_input.review_run_id,
        topic_id=dry_run_input.topic_id,
        discovery_run_id=dry_run_input.discovery_run_id,
        candidate_signals_considered=len(candidate_signals),
        review_items_created=len(items),
        safe_requests_built=sum(1 for item in items if item.safe_request_built),
        blocked_by_prompt_safety=sum(1 for item in items if item.blocked_by_prompt_safety),
        valid_reviews=sum(1 for item in items if item.mock_review_valid),
        invalid_reviews=sum(1 for item in items if item.safe_request_built and not item.mock_review_valid),
        llm_calls_made=False,
        external_calls_made=False,
        provider_used=PROVIDER_USED,
        items=items,
        limitations=list(DEFAULT_LIMITATIONS),
        recommended_next_step="Review the dry-run report; enable real provider review only in a later explicitly approved item.",
    )


def load_llm_signal_review_dry_run_artifacts(
    dry_run_input: LLMSignalReviewDryRunInput,
) -> tuple[list[CandidateSignal], list[CleanedEvidence]]:
    candidate_path, cleaned_path = _resolve_input_paths(dry_run_input)
    candidates_payload = _load_json_file(candidate_path, "candidate_signals.json")
    cleaned_payload = _load_json_file(cleaned_path, "cleaned_evidence.json")
    if not isinstance(candidates_payload, list):
        raise ValueError(f"candidate_signals.json must contain a list: {candidate_path}")
    if not isinstance(cleaned_payload, list):
        raise ValueError(f"cleaned_evidence.json must contain a list: {cleaned_path}")
    return (
        [model_from_dict(CandidateSignal, item) for item in candidates_payload],
        [model_from_dict(CleanedEvidence, item) for item in cleaned_payload],
    )


def select_candidate_signals_for_review(
    candidate_signals: list[CandidateSignal],
    *,
    max_signals: int,
    min_confidence: float,
    include_needs_human_review: bool,
) -> list[CandidateSignal]:
    selected = [
        signal
        for signal in candidate_signals
        if float(signal.confidence) >= min_confidence
        and (include_needs_human_review or signal.signal_type != "needs_human_review")
    ]
    return sorted(
        selected,
        key=lambda signal: (-float(signal.confidence), signal.signal_id, signal.evidence_id),
    )[:max_signals]


def build_signal_review_input(
    *,
    dry_run_input: LLMSignalReviewDryRunInput,
    signal: CandidateSignal,
    cleaned: CleanedEvidence,
) -> LLMSignalReviewInput:
    evidence = EvidenceForReview(
        evidence_id=signal.evidence_id,
        source_type=signal.source_type or cleaned.source_type,
        source_url=signal.source_url or cleaned.source_url,
        title=cleaned.normalized_title or cleaned.title,
        body=cleaned.normalized_body or cleaned.body,
        pain_summary=signal.pain_summary,
        current_workaround=signal.current_workaround,
        candidate_signal_type=signal.signal_type,
        confidence=signal.confidence,
        scoring_breakdown=signal.scoring_breakdown,
    )
    return LLMSignalReviewInput(
        review_id=_review_id(dry_run_input.review_run_id, signal),
        topic_id=dry_run_input.topic_id,
        evidence=[evidence],
        review_goal=REVIEW_GOAL,
        max_evidence_items=1,
        require_evidence_citations=True,
        metadata={
            "candidate_signal_id": signal.signal_id,
            "evidence_id": signal.evidence_id,
            "source_url": signal.source_url,
            "source_type": signal.source_type,
            "offline_dry_run": True,
        },
    )


def write_llm_signal_review_dry_run_report(
    report: LLMSignalReviewDryRunReport,
    *,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "llm_signal_review_dry_run.json"
    md_path = output_dir / "llm_signal_review_dry_run.md"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(llm_signal_review_dry_run_markdown(report), encoding="utf-8")
    return json_path, md_path


def default_llm_signal_review_dry_run_output_dir(
    *,
    project_root: Path,
    review_run_id: str,
) -> Path:
    return project_root / "artifacts" / "llm_signal_review_dry_runs" / _safe_id(review_run_id)


def llm_signal_review_dry_run_markdown(report: LLMSignalReviewDryRunReport) -> str:
    lines = [
        "# LLM Signal Review Offline Dry Run",
        "",
        "## Summary",
        f"- Review run ID: `{report.review_run_id}`",
        f"- Topic ID: `{report.topic_id}`",
        f"- Discovery run ID: `{report.discovery_run_id or 'explicit_paths'}`",
        f"- Candidate signals considered: `{report.candidate_signals_considered}`",
        f"- Review items created: `{report.review_items_created}`",
        f"- Valid reviews: `{report.valid_reviews}`",
        f"- Invalid reviews: `{report.invalid_reviews}`",
        "",
        "## Safety",
        f"- Safe requests built: `{report.safe_requests_built}`",
        f"- Blocked by prompt safety: `{report.blocked_by_prompt_safety}`",
        f"- LLM calls made: `{str(report.llm_calls_made).lower()}`",
        f"- External calls made: `{str(report.external_calls_made).lower()}`",
        f"- Provider used: `{report.provider_used}`",
        "",
        "## Inputs",
        f"- Source: `{report.discovery_run_id or 'explicit file paths'}`",
        "",
        "## Review items",
    ]
    if not report.items:
        lines.append("- None")
    for item in report.items:
        lines.extend(
            [
                f"- `{item.review_id}`",
                f"  - Candidate signal: `{item.candidate_signal_id}`",
                f"  - Evidence: `{item.evidence_id}`",
                f"  - Source: `{item.source_type or 'unknown'}` / {item.source_url or 'none'}",
                f"  - Safe request built: `{str(item.safe_request_built).lower()}`",
                f"  - Mock review valid: `{str(item.mock_review_valid).lower()}`",
            ]
        )
    lines.extend(["", "## Blocked items"])
    blocked = [item for item in report.items if item.blocked_by_prompt_safety]
    if not blocked:
        lines.append("- None")
    for item in blocked:
        lines.append(f"- `{item.review_id}`: {', '.join(item.prompt_safety_reasons) or 'blocked'}")
    lines.extend(["", "## Validation errors"])
    invalid = [item for item in report.items if item.validation_errors]
    if not invalid:
        lines.append("- None")
    for item in invalid:
        lines.append(f"- `{item.review_id}`: {', '.join(item.validation_errors)}")
    lines.extend(["", "## Limitations"])
    for limitation in report.limitations:
        lines.append(f"- {limitation}")
    lines.extend(["", "## Recommended next step", "", report.recommended_next_step])
    return "\n".join(lines) + "\n"


def _resolve_input_paths(dry_run_input: LLMSignalReviewDryRunInput) -> tuple[Path, Path]:
    project_root = dry_run_input.project_root
    if dry_run_input.input_candidate_signals_path or dry_run_input.input_cleaned_evidence_path:
        if dry_run_input.input_candidate_signals_path is None:
            raise ValueError("input_candidate_signals_path is required when explicit paths are used")
        if dry_run_input.input_cleaned_evidence_path is None:
            raise ValueError("input_cleaned_evidence_path is required when explicit paths are used")
        return (
            _resolve_path(project_root, dry_run_input.input_candidate_signals_path),
            _resolve_path(project_root, dry_run_input.input_cleaned_evidence_path),
        )
    if dry_run_input.discovery_run_id is None:
        raise ValueError("discovery_run_id or explicit input paths are required")
    run_dir = project_root / "artifacts" / "discovery_runs" / dry_run_input.discovery_run_id
    return run_dir / "candidate_signals.json", run_dir / "cleaned_evidence.json"


def _resolve_path(project_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else project_root / path


def _load_json_file(path: Path, label: str) -> Any:
    if not path.exists():
        raise ValueError(f"{label} not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _review_id(review_run_id: str, signal: CandidateSignal) -> str:
    suffix = signal.signal_id or signal.evidence_id
    return f"llm_review_{_safe_id(review_run_id)}_{_safe_id(suffix)}"


def _safe_id(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value.strip()).strip("_")
    return safe or "unknown"
