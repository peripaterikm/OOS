from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import CandidateSignal


COMPATIBILITY_STATUS = "adapter_only"


@dataclass(frozen=True)
class MeaningLoopAdaptedRecord:
    signal_id: str
    candidate_signal_id: str
    captured_at: str
    source_type: str
    title: str
    text: str
    source_ref: str
    candidate_icp: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "candidate_signal_id": self.candidate_signal_id,
            "captured_at": self.captured_at,
            "source_type": self.source_type,
            "title": self.title,
            "text": self.text,
            "source_ref": self.source_ref,
            "candidate_icp": self.candidate_icp,
            "metadata": dict(self.metadata),
        }

    def to_canonical_signal_jsonl_record(self) -> Dict[str, str]:
        return {
            "signal_id": self.signal_id,
            "captured_at": self.captured_at,
            "source_type": self.source_type,
            "title": self.title,
            "text": self.text,
            "source_ref": self.source_ref,
        }


def adapt_candidate_signal(signal: CandidateSignal) -> MeaningLoopAdaptedRecord:
    signal.validate()
    metadata = {
        "source_intelligence_version": "v2.3_mvp_lite",
        "candidate_signal_id": signal.signal_id,
        "evidence_id": signal.evidence_id,
        "source_url": signal.source_url,
        "source_id": signal.source_id,
        "source_type": signal.source_type,
        "topic_id": signal.topic_id,
        "query_kind": signal.query_kind,
        "signal_type": signal.signal_type,
        "confidence": signal.confidence,
        "classification": signal.classification,
        "classification_confidence": signal.classification_confidence,
    }
    return MeaningLoopAdaptedRecord(
        signal_id=signal.signal_id,
        candidate_signal_id=signal.signal_id,
        captured_at="deterministic_mvp_lite",
        source_type=f"source_intelligence:{signal.source_type}",
        title=signal.pain_summary,
        text=_adapted_text(signal),
        source_ref=signal.source_url,
        candidate_icp=signal.target_user or "unknown",
        metadata=metadata,
    )


def adapt_candidate_signals(signals: Iterable[CandidateSignal]) -> List[MeaningLoopAdaptedRecord]:
    return [adapt_candidate_signal(signal) for signal in signals]


def build_meaning_loop_dry_run(
    *,
    run_id: str,
    topic_id: str,
    candidate_signals: List[CandidateSignal],
    artifact_paths: Dict[str, Path],
) -> Dict[str, Any]:
    adapted_records = adapt_candidate_signals(candidate_signals)
    traceability_map = {
        signal.signal_id: {
            "evidence_id": signal.evidence_id,
            "source_url": signal.source_url,
            "source_id": signal.source_id,
            "source_type": signal.source_type,
            "topic_id": signal.topic_id,
            "query_kind": signal.query_kind,
        }
        for signal in candidate_signals
    }
    return {
        "run_id": run_id,
        "topic_id": topic_id,
        "candidate_signal_count": len(candidate_signals),
        "adapted_record_count": len(adapted_records),
        "compatibility_status": COMPATIBILITY_STATUS,
        "adapted_records": [record.to_dict() for record in adapted_records],
        "canonical_signal_jsonl_preview": [
            record.to_canonical_signal_jsonl_record() for record in adapted_records
        ],
        "unsupported_fields": [
            "evidence_id is preserved in metadata and traceability_map, not native canonical signal JSONL.",
            "source_url is preserved as source_ref plus metadata, not a first-class v2.2 Signal field.",
            "topic_id, query_kind, signal_type, and confidence are preserved in metadata for future full integration.",
        ],
        "downstream_artifacts_created": [],
        "traceability_map": traceability_map,
        "notes": [
            "Adapter-only MVP dry run; no v2.2 meaning-loop artifacts are created yet.",
            "The adapted records are compatible with the existing canonical signal JSONL shape plus metadata.",
            "Founder decisions remain manual and are not automated.",
            "No live network, API, or LLM calls are made.",
        ],
        "limitations": [
            "Full 6.1 Source Yield Analytics remains deferred.",
            "Full 7.2 traceability/compliance hardening remains deferred.",
            "8.2 completion checkpoint is not complete.",
        ],
        "next_integration_targets": [
            "Write adapted records to a temporary canonical JSONL file.",
            "Run the existing deterministic run-signal-batch path against adapted records.",
            "Propagate source_url and evidence_id into downstream founder review package indexes.",
        ],
        "artifact_paths": {name: str(path) for name, path in sorted(artifact_paths.items())},
    }


def meaning_loop_dry_run_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Meaning Loop Dry Run",
        "",
        "## Summary",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Topic ID: `{report['topic_id']}`",
        f"- Candidate signals: `{report['candidate_signal_count']}`",
        f"- Adapted records: `{report['adapted_record_count']}`",
        f"- Compatibility status: `{report['compatibility_status']}`",
        "",
        "## Candidate signals adapted",
        "",
    ]
    if report["adapted_records"]:
        for record in report["adapted_records"]:
            lines.extend(
                [
                    f"- `{record['candidate_signal_id']}`",
                    f"  - Source: `{record['source_type']}`",
                    f"  - Source URL: {record['source_ref']}",
                    f"  - Title: {record['title']}",
                ]
            )
    else:
        lines.append("- No candidate signals were available to adapt.")

    lines.extend(
        [
            "",
            "## Downstream artifacts / compatibility status",
            "",
            f"- Compatibility status: `{report['compatibility_status']}`",
            f"- Downstream artifacts created: `{len(report['downstream_artifacts_created'])}`",
        ]
    )
    for note in report["notes"]:
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Traceability",
            "",
        ]
    )
    if report["traceability_map"]:
        for signal_id, trace in sorted(report["traceability_map"].items()):
            lines.extend(
                [
                    f"- `{signal_id}` -> `{trace['evidence_id']}` -> {trace['source_url']}",
                    f"  - Source ID: `{trace['source_id']}`",
                    f"  - Topic/query: `{trace['topic_id']}` / `{trace['query_kind']}`",
                ]
            )
    else:
        lines.append("- No traceability records because no candidate signals were adapted.")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
        ]
    )
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            "## Recommended next steps",
            "",
        ]
    )
    for target in report["next_integration_targets"]:
        lines.append(f"- {target}")
    return "\n".join(lines) + "\n"


def write_meaning_loop_dry_run_artifacts(*, report: Dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(meaning_loop_dry_run_markdown(report), encoding="utf-8")


def _adapted_text(signal: CandidateSignal) -> str:
    parts = [
        f"Signal type: {signal.signal_type}",
        f"Pain summary: {signal.pain_summary}",
        f"Target user: {signal.target_user}",
        f"Current workaround: {signal.current_workaround}",
        f"Buying intent hint: {signal.buying_intent_hint}",
        f"Urgency hint: {signal.urgency_hint}",
        f"Confidence: {signal.confidence}",
        f"Evidence ID: {signal.evidence_id}",
        f"Source URL: {signal.source_url}",
    ]
    return "\n".join(parts)
