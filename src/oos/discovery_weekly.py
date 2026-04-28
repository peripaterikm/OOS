from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .candidate_signal_extractor import extract_candidate_signal
from .evidence_classifier import classify_evidence, clean_evidence
from .models import CandidateSignal, CleanedEvidence, EvidenceClassification, RawEvidence, model_from_dict, model_to_dict
from .source_registry import default_topic_profiles


DEFAULT_RAW_EVIDENCE_FIXTURE = Path("examples") / "source_intelligence_mvp" / "raw_evidence_seed.json"


@dataclass(frozen=True)
class DiscoveryRunResult:
    run_id: str
    run_dir: Path
    artifact_paths: Dict[str, Path]
    summary: Dict[str, Any]


def run_discovery_weekly(
    *,
    project_root: Path,
    topic_id: str,
    run_id: str | None = None,
    input_raw_evidence: Path | None = None,
) -> DiscoveryRunResult:
    project_root = project_root.resolve()
    _require_active_topic(topic_id)
    resolved_run_id = _resolve_run_id(run_id)
    evidence_path = _resolve_input_path(project_root=project_root, input_raw_evidence=input_raw_evidence)
    raw_evidence = _load_raw_evidence(evidence_path)
    topic_evidence = [evidence for evidence in raw_evidence if evidence.topic_id == topic_id]

    cleaned_items = [clean_evidence(evidence) for evidence in topic_evidence]
    classifications = [classify_evidence(cleaned) for cleaned in cleaned_items]
    candidate_signals = _extract_signals(cleaned_items, classifications)

    run_dir = project_root / "artifacts" / "discovery_runs" / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_index = [
        {
            "evidence_id": evidence.evidence_id,
            "source_id": evidence.source_id,
            "source_type": evidence.source_type,
            "source_url": evidence.source_url,
            "topic_id": evidence.topic_id,
            "query_kind": evidence.query_kind,
            "content_hash": evidence.content_hash,
        }
        for evidence in topic_evidence
    ]
    artifact_payloads: Dict[str, Any] = {
        "raw_evidence_index": raw_index,
        "cleaned_evidence": [model_to_dict(item) for item in cleaned_items],
        "evidence_classifications": [model_to_dict(item) for item in classifications],
        "candidate_signals": [model_to_dict(item) for item in candidate_signals],
    }
    artifact_paths: Dict[str, Path] = {}
    for artifact_name, payload in artifact_payloads.items():
        path = run_dir / f"{artifact_name}.json"
        _write_json(path, payload)
        artifact_paths[artifact_name] = path

    summary_json_path = run_dir / "discovery_run_summary.json"
    summary_md_path = run_dir / "discovery_run_summary.md"
    artifact_paths["discovery_run_summary_json"] = summary_json_path
    artifact_paths["discovery_run_summary_md"] = summary_md_path

    summary = _build_summary(
        run_id=resolved_run_id,
        topic_id=topic_id,
        raw_evidence=topic_evidence,
        cleaned_items=cleaned_items,
        classifications=classifications,
        candidate_signals=candidate_signals,
        artifact_paths=artifact_paths,
    )
    _write_json(summary_json_path, summary)
    summary_md_path.write_text(_summary_markdown(summary, candidate_signals), encoding="utf-8")

    return DiscoveryRunResult(
        run_id=resolved_run_id,
        run_dir=run_dir,
        artifact_paths=artifact_paths,
        summary=summary,
    )


def _require_active_topic(topic_id: str) -> None:
    for profile in default_topic_profiles():
        if profile.topic_id == topic_id:
            if profile.active:
                return
            raise ValueError(f"Topic {topic_id!r} is not active for discovery runs")
    raise ValueError(f"Unknown topic {topic_id!r}; define it in topic profiles before running discovery")


def _resolve_run_id(run_id: str | None) -> str:
    if run_id:
        safe = _safe_id(run_id)
        if not safe:
            raise ValueError("--run-id must contain at least one safe identifier character")
        return safe
    return "discovery_weekly_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_input_path(*, project_root: Path, input_raw_evidence: Path | None) -> Path:
    raw_path = input_raw_evidence or DEFAULT_RAW_EVIDENCE_FIXTURE
    if not raw_path.is_absolute():
        raw_path = project_root / raw_path
    return raw_path.resolve()


def _load_raw_evidence(path: Path) -> List[RawEvidence]:
    if not path.exists():
        raise ValueError(f"RawEvidence input file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        items = payload.get("raw_evidence", [])
    else:
        items = payload
    if not isinstance(items, list):
        raise ValueError("RawEvidence input must be a list or an object with raw_evidence list")
    evidence_items = [model_from_dict(RawEvidence, item) for item in items]
    return evidence_items


def _extract_signals(
    cleaned_items: Iterable[CleanedEvidence],
    classifications: Iterable[EvidenceClassification],
) -> List[CandidateSignal]:
    signals: List[CandidateSignal] = []
    for cleaned, classification in zip(cleaned_items, classifications):
        signal = extract_candidate_signal(cleaned, classification)
        if signal is not None:
            signals.append(signal)
    return signals


def _build_summary(
    *,
    run_id: str,
    topic_id: str,
    raw_evidence: List[RawEvidence],
    cleaned_items: List[CleanedEvidence],
    classifications: List[EvidenceClassification],
    candidate_signals: List[CandidateSignal],
    artifact_paths: Dict[str, Path],
) -> Dict[str, Any]:
    classification_counts = Counter(item.classification for item in classifications)
    signal_counts = Counter(item.signal_type for item in candidate_signals)
    source_type_counts = Counter(item.source_type for item in raw_evidence)
    signal_source_counts = Counter(item.source_type for item in candidate_signals)
    return {
        "run_id": run_id,
        "topic_id": topic_id,
        "mode": "mvp_cli_lite_offline",
        "live_network_enabled": False,
        "raw_evidence_count": len(raw_evidence),
        "cleaned_evidence_count": len(cleaned_items),
        "classification_count": len(classifications),
        "candidate_signal_count": len(candidate_signals),
        "counts_by_source_type": dict(sorted(source_type_counts.items())),
        "candidate_signal_counts_by_source_type": dict(sorted(signal_source_counts.items())),
        "counts_by_classification": dict(sorted(classification_counts.items())),
        "counts_by_signal_type": dict(sorted(signal_counts.items())),
        "needs_human_review_count": classification_counts.get("needs_human_review", 0),
        "noise_count": classification_counts.get("noise", 0),
        "artifact_paths": {name: str(path) for name, path in sorted(artifact_paths.items())},
        "notes": [
            "MVP weekly discovery CLI lite.",
            "Full 6.1 Source Yield Analytics is deferred.",
            "No live network, API, or LLM calls are made.",
        ],
    }


def _summary_markdown(summary: Dict[str, Any], candidate_signals: List[CandidateSignal]) -> str:
    lines = [
        "# Discovery Run Summary - MVP CLI Lite",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Topic: `{summary['topic_id']}`",
        "- Mode: `mvp_cli_lite_offline`",
        "- Note: This is MVP CLI lite, not the final founder discovery package.",
        "",
        "## Counts",
        "",
        f"- Raw evidence: `{summary['raw_evidence_count']}`",
        f"- Cleaned evidence: `{summary['cleaned_evidence_count']}`",
        f"- Classifications: `{summary['classification_count']}`",
        f"- Candidate signals: `{summary['candidate_signal_count']}`",
        f"- Needs human review: `{summary['needs_human_review_count']}`",
        f"- Noise: `{summary['noise_count']}`",
        "",
        "## Top Candidate Signals",
        "",
    ]
    if candidate_signals:
        for signal in candidate_signals[:5]:
            lines.extend(
                [
                    f"- `{signal.signal_id}` ({signal.signal_type}, confidence `{signal.confidence}`)",
                    f"  - Evidence: `{signal.evidence_id}`",
                    f"  - Source URL: {signal.source_url}",
                    f"  - Summary: {signal.pain_summary}",
                ]
            )
    else:
        lines.append("- No candidate signals extracted.")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Live network disabled.",
            "- No live LLM/API calls.",
            "- Full founder discovery package is not generated by this lite command.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_")
