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
from .live_collection import collect_raw_evidence_for_topic
from .meaning_loop_adapter import build_meaning_loop_dry_run, write_meaning_loop_dry_run_artifacts
from .models import CandidateSignal, CleanedEvidence, EvidenceClassification, RawEvidence, model_from_dict, model_to_dict
from .price_signal_extractor import extract_price_signal
from .source_registry import default_topic_profiles


DEFAULT_RAW_EVIDENCE_FIXTURE = Path("examples") / "source_intelligence_mvp" / "raw_evidence_seed.json"

SIGNAL_TYPE_RANK = {
    "buying_intent": 0,
    "pain_signal": 1,
    "workaround": 2,
    "competitor_weakness": 3,
    "trend_trigger": 4,
    "needs_human_review": 5,
}

RECOMMENDED_FOUNDER_ACTIONS = [
    "Review top candidate signals and open the linked source URLs for the highest-confidence items.",
    "Mark promising signals as advance, park, or kill in a future founder review flow.",
    "Use the strongest signals as input for opportunity framing once meaning-loop integration is enabled.",
    "Treat needs-human-review signals as a queue for quick founder judgment, not as automated decisions.",
]


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
    include_meaning_loop_dry_run: bool = False,
    use_collectors: bool = False,
    allow_live_network: bool = False,
    max_total_queries: int = 4,
    max_queries_per_source: int = 2,
    max_queries_per_topic: int | None = None,
    max_results_per_query: int = 5,
    source_ids: list[str] | None = None,
    source_types: list[str] | None = None,
) -> DiscoveryRunResult:
    project_root = project_root.resolve()
    _require_active_topic(topic_id)
    resolved_run_id = _resolve_run_id(run_id)
    if use_collectors:
        collection_run = collect_raw_evidence_for_topic(
            topic_id=topic_id,
            allow_live_network=allow_live_network,
            max_total_queries=max_total_queries,
            max_queries_per_source=max_queries_per_source,
            max_queries_per_topic=max_queries_per_topic,
            max_results_per_query=max_results_per_query,
            allowed_source_ids=set(source_ids or []),
            allowed_source_types=set(source_types or []),
        )
        raw_evidence = collection_run.raw_evidence
        collection_metadata = collection_run.collection_metadata
    else:
        evidence_path = _resolve_input_path(project_root=project_root, input_raw_evidence=input_raw_evidence)
        raw_evidence = _load_raw_evidence(evidence_path)
        collection_metadata = {
            "collection_mode": "fixture",
            "live_network_enabled": False,
            "query_plan_count": 0,
            "scheduled_query_count": 0,
            "collectors_attempted": [],
            "collectors_succeeded": [],
            "collectors_failed": [],
            "collection_errors": [],
        }
    topic_evidence = [evidence for evidence in raw_evidence if evidence.topic_id == topic_id]

    cleaned_items = [clean_evidence(evidence) for evidence in topic_evidence]
    classifications = [classify_evidence(cleaned) for cleaned in cleaned_items]
    candidate_signals = _extract_signals(cleaned_items, classifications)
    price_signals = [price_signal for cleaned in cleaned_items if (price_signal := extract_price_signal(cleaned)) is not None]

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
        "price_signals": [model_to_dict(item) for item in price_signals],
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
    founder_package_json_path = run_dir / "founder_discovery_package.json"
    founder_package_md_path = run_dir / "founder_discovery_package.md"
    artifact_paths["founder_discovery_package_json"] = founder_package_json_path
    artifact_paths["founder_discovery_package_md"] = founder_package_md_path
    if include_meaning_loop_dry_run:
        meaning_loop_json_path = run_dir / "meaning_loop_dry_run.json"
        meaning_loop_md_path = run_dir / "meaning_loop_dry_run.md"
        artifact_paths["meaning_loop_dry_run_json"] = meaning_loop_json_path
        artifact_paths["meaning_loop_dry_run_md"] = meaning_loop_md_path

    summary = _build_summary(
        run_id=resolved_run_id,
        topic_id=topic_id,
        raw_evidence=topic_evidence,
        cleaned_items=cleaned_items,
        classifications=classifications,
        candidate_signals=candidate_signals,
        price_signal_count=len(price_signals),
        artifact_paths=artifact_paths,
        collection_metadata=collection_metadata,
    )
    _write_json(summary_json_path, summary)
    summary_md_path.write_text(_summary_markdown(summary, candidate_signals), encoding="utf-8")
    founder_package = _build_founder_package(summary=summary, candidate_signals=candidate_signals)
    _write_json(founder_package_json_path, founder_package)
    founder_package_md_path.write_text(_founder_package_markdown(founder_package), encoding="utf-8")
    if include_meaning_loop_dry_run:
        meaning_loop_report = build_meaning_loop_dry_run(
            run_id=resolved_run_id,
            topic_id=topic_id,
            candidate_signals=candidate_signals,
            artifact_paths=artifact_paths,
        )
        write_meaning_loop_dry_run_artifacts(
            report=meaning_loop_report,
            json_path=artifact_paths["meaning_loop_dry_run_json"],
            markdown_path=artifact_paths["meaning_loop_dry_run_md"],
        )

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


def rank_candidate_signals(candidate_signals: Iterable[CandidateSignal]) -> List[CandidateSignal]:
    return sorted(
        candidate_signals,
        key=lambda signal: (
            -float(signal.confidence),
            SIGNAL_TYPE_RANK.get(signal.signal_type, 99),
            signal.signal_id,
        ),
    )


def deduplicate_ranked_candidate_signals(candidate_signals: Iterable[CandidateSignal]) -> List[CandidateSignal]:
    deduped: Dict[str, CandidateSignal] = {}
    for signal in rank_candidate_signals(candidate_signals):
        key = _candidate_signal_dedup_key(signal)
        if key not in deduped:
            deduped[key] = signal
    return list(deduped.values())


def _candidate_signal_dedup_key(signal: CandidateSignal) -> str:
    source_url = signal.source_url.strip().lower()
    if source_url:
        return f"url:{signal.source_type}:{source_url}"
    if signal.evidence_id.strip():
        return f"evidence:{signal.evidence_id.strip().lower()}"
    summary = re.sub(r"[^a-z0-9]+", " ", signal.pain_summary.lower()).strip()
    return f"summary:{signal.source_type}:{summary}"


def _build_summary(
    *,
    run_id: str,
    topic_id: str,
    raw_evidence: List[RawEvidence],
    cleaned_items: List[CleanedEvidence],
    classifications: List[EvidenceClassification],
    candidate_signals: List[CandidateSignal],
    artifact_paths: Dict[str, Path],
    collection_metadata: Dict[str, Any],
    price_signal_count: int = 0,
) -> Dict[str, Any]:
    classification_counts = Counter(item.classification for item in classifications)
    signal_counts = Counter(item.signal_type for item in candidate_signals)
    source_type_counts = Counter(item.source_type for item in raw_evidence)
    signal_source_counts = Counter(item.source_type for item in candidate_signals)
    summary = {
        "run_id": run_id,
        "topic_id": topic_id,
        "mode": "mvp_cli_lite_offline",
        "collection_mode": collection_metadata.get("collection_mode", "fixture"),
        "live_network_enabled": bool(collection_metadata.get("live_network_enabled", False)),
        "query_plan_count": collection_metadata.get("query_plan_count", 0),
        "scheduled_query_count": collection_metadata.get("scheduled_query_count", 0),
        "collectors_attempted": collection_metadata.get("collectors_attempted", []),
        "collectors_succeeded": collection_metadata.get("collectors_succeeded", []),
        "collectors_failed": collection_metadata.get("collectors_failed", []),
        "collection_errors": collection_metadata.get("collection_errors", []),
        "raw_evidence_count": len(raw_evidence),
        "cleaned_evidence_count": len(cleaned_items),
        "classification_count": len(classifications),
        "candidate_signal_count": len(candidate_signals),
        "price_signal_count": price_signal_count,
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
            "Live network calls require explicit collector mode and --allow-live-network.",
            "No live LLM/API calls are made.",
        ],
    }
    for key in (
        "source_ids_filter",
        "source_types_filter",
        "max_total_queries",
        "max_queries_per_source",
        "max_queries_per_topic",
        "max_results_per_query",
    ):
        if key in collection_metadata:
            summary[key] = collection_metadata[key]
    return summary


def _build_founder_package(
    *,
    summary: Dict[str, Any],
    candidate_signals: List[CandidateSignal],
) -> Dict[str, Any]:
    ranked_signals = rank_candidate_signals(candidate_signals)
    deduped_ranked_signals = deduplicate_ranked_candidate_signals(candidate_signals)
    top_signals = [signal for signal in deduped_ranked_signals if signal.signal_type != "needs_human_review"]
    review_signals = [signal for signal in ranked_signals if signal.signal_type == "needs_human_review"]
    return {
        "run_id": summary["run_id"],
        "topic_id": summary["topic_id"],
        "generated_at": "deterministic_mvp_lite",
        "mode": "founder_discovery_package_lite",
        "collection_mode": summary["collection_mode"],
        "live_network_enabled": summary["live_network_enabled"],
        "raw_evidence_count": summary["raw_evidence_count"],
        "candidate_signal_count": summary["candidate_signal_count"],
        "price_signal_count": summary.get("price_signal_count", 0),
        "needs_human_review_count": summary["needs_human_review_count"],
        "noise_count": summary["noise_count"],
        "counts_by_source_type": summary["counts_by_source_type"],
        "counts_by_classification": summary["counts_by_classification"],
        "counts_by_signal_type": summary["counts_by_signal_type"],
        "top_candidate_signals": [_signal_package_item(signal) for signal in top_signals[:10]],
        "needs_human_review_signals": [_signal_package_item(signal) for signal in review_signals],
        "recommended_founder_actions": list(RECOMMENDED_FOUNDER_ACTIONS),
        "artifact_paths": summary["artifact_paths"],
        "collection_errors": summary["collection_errors"],
        "limitations": [
            "MVP package lite.",
            "Rule-based only.",
            "No live LLM/API calls.",
            "No Reddit collector yet.",
            "No full source yield analytics yet.",
            "No final 7.2 traceability/compliance hardening yet.",
        ],
    }


def _signal_package_item(signal: CandidateSignal) -> Dict[str, Any]:
    price_signal = signal.scoring_breakdown.get("price_signal") if isinstance(signal.scoring_breakdown, dict) else None
    return {
        "signal_id": signal.signal_id,
        "signal_type": signal.signal_type,
        "source_type": signal.source_type,
        "source_url": signal.source_url,
        "pain_summary": signal.pain_summary,
        "target_user": signal.target_user,
        "current_workaround": signal.current_workaround,
        "buying_intent_hint": signal.buying_intent_hint,
        "urgency_hint": signal.urgency_hint,
        "confidence": signal.confidence,
        "evidence_id": signal.evidence_id,
        "query_kind": signal.query_kind,
        "price_signal": price_signal if isinstance(price_signal, dict) else None,
    }


def _summary_markdown(summary: Dict[str, Any], candidate_signals: List[CandidateSignal]) -> str:
    lines = [
        "# Discovery Run Summary - MVP CLI Lite",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Topic: `{summary['topic_id']}`",
        "- Mode: `mvp_cli_lite_offline`",
        f"- Collection mode: `{summary['collection_mode']}`",
        f"- Live network enabled: `{str(summary['live_network_enabled']).lower()}`",
        "- Note: This is the compact run summary; Founder Discovery Package lite is generated separately.",
        "",
        "## Counts",
        "",
        f"- Raw evidence: `{summary['raw_evidence_count']}`",
        f"- Cleaned evidence: `{summary['cleaned_evidence_count']}`",
        f"- Classifications: `{summary['classification_count']}`",
        f"- Candidate signals: `{summary['candidate_signal_count']}`",
        f"- Price signals: `{summary.get('price_signal_count', 0)}`",
        f"- Needs human review: `{summary['needs_human_review_count']}`",
        f"- Noise: `{summary['noise_count']}`",
        f"- Query plans: `{summary['query_plan_count']}`",
        f"- Scheduled queries: `{summary['scheduled_query_count']}`",
        f"- Collectors attempted: `{', '.join(summary['collectors_attempted']) or 'none'}`",
        f"- Collection errors: `{len(summary['collection_errors'])}`",
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
            "- Live network requires explicit collector mode and --allow-live-network.",
            "- No live LLM/API calls.",
            "- Founder Discovery Package lite is generated as a separate artifact.",
        ]
    )
    return "\n".join(lines) + "\n"


def _founder_package_markdown(package: Dict[str, Any]) -> str:
    source_counts = package["counts_by_source_type"]
    classification_counts = package["counts_by_classification"]
    signal_counts = package["counts_by_signal_type"]
    lines = [
        "# Founder Discovery Package",
        "",
        "## Executive summary",
        "",
        (
            f"This MVP package processed `{package['raw_evidence_count']}` raw evidence items "
            f"and surfaced `{package['candidate_signal_count']}` candidate signals for founder review."
        ),
        "",
        "## Run context",
        "",
        f"- Run ID: `{package['run_id']}`",
        f"- Topic ID: `{package['topic_id']}`",
        f"- Generated at: `{package['generated_at']}`",
        f"- Collection mode: `{package['collection_mode']}`",
        f"- Live network enabled: `{str(package['live_network_enabled']).lower()}`",
        f"- Source coverage: {_format_counts(source_counts)}",
        "- Artifact paths:",
    ]
    for name, path in sorted(package["artifact_paths"].items()):
        lines.append(f"  - `{name}`: `{path}`")

    lines.extend(
        [
            "",
            "## Signal overview",
            "",
            f"- Classifications: {_format_counts(classification_counts)}",
            f"- Signal types: {_format_counts(signal_counts)}",
        f"- Needs human review: `{package['needs_human_review_count']}`",
        f"- Noise: `{package['noise_count']}`",
        f"- Price signals: `{package.get('price_signal_count', 0)}`",
        "",
        "## Top candidate signals",
            "",
        ]
    )
    if package["top_candidate_signals"]:
        lines.extend(
            [
                "| Signal | Confidence | Summary | Source | Buying intent | Urgency | Price hints | Evidence |",
                "| --- | ---: | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for signal in package["top_candidate_signals"]:
            lines.append(
                "| "
                f"`{signal['signal_type']}` | "
                f"`{signal['confidence']}` | "
                f"{_md_cell(signal['pain_summary'])} | "
                f"{_md_cell(signal['source_type'])} / {signal['source_url']} | "
                f"`{signal['buying_intent_hint']}` | "
                f"`{signal['urgency_hint']}` | "
                f"{_md_cell(_format_price_hint(signal.get('price_signal')))} | "
                f"`{signal['evidence_id']}` |"
            )
    else:
        lines.append("- No candidate signals extracted.")

    lines.extend(
        [
            "",
            "## Needs human review",
            "",
        ]
    )
    if package["needs_human_review_signals"]:
        for signal in package["needs_human_review_signals"]:
            lines.extend(
                [
                    f"- `{signal['signal_id']}`",
                    f"  - Summary: {signal['pain_summary']}",
                    f"  - Source: {signal['source_type']} / {signal['source_url']}",
                    f"  - Evidence ID: `{signal['evidence_id']}`",
                ]
            )
    else:
        lines.append("- No signals currently require human review.")

    lines.extend(
        [
            "",
            "## Noise / low-signal summary",
            "",
            f"- Noise count: `{package['noise_count']}`",
            "- Noise evidence is counted only and not dumped in full in this MVP package.",
            "",
            "## Recommended founder actions",
            "",
        ]
    )
    for action in package["recommended_founder_actions"]:
        lines.append(f"- {action}")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
        ]
    )
    for limitation in package["limitations"]:
        lines.append(f"- {limitation}")
    return "\n".join(lines) + "\n"


def _format_counts(counts: Dict[str, Any]) -> str:
    if not counts:
        return "`none`"
    return ", ".join(f"`{name}: {count}`" for name, count in sorted(counts.items()))


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _format_price_hint(price_signal: Any) -> str:
    if not isinstance(price_signal, dict):
        return "none"
    parts = []
    for key in ("current_spend_hint", "effort_cost_hint", "price_complaint"):
        value = price_signal.get(key)
        if value:
            parts.append(str(value))
    wtp = price_signal.get("willingness_to_pay_indicator")
    if wtp and wtp != "not_detected":
        parts.append(f"wtp:{wtp}")
    if not parts:
        return "none"
    return "; ".join(parts)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_")
