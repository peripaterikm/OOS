from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CandidateSignal, EvidenceClassification, PriceSignal


QUALITY_SECTION_KEYS = [
    "time_sensitive_opportunities",
    "implied_burdens",
    "price_signals",
    "weak_pattern_candidates",
    "kill_archive_warnings",
    "customer_voice_query_yield",
    "llm_review_outputs",
    "evidence_confidence_risk_notes",
]


def build_founder_package_quality_sections(
    *,
    candidate_signals: list[CandidateSignal],
    classifications: list[EvidenceClassification],
    price_signals: list[PriceSignal],
    run_dir: Path | None = None,
    collection_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ranked = sorted(candidate_signals, key=lambda signal: (-float(signal.confidence), signal.signal_id))
    classifications_by_evidence_id = {item.evidence_id: item for item in classifications}
    price_by_evidence_id = {item.evidence_id: item for item in price_signals if item.has_explicit_signal}
    run_dir = run_dir.resolve() if run_dir is not None else None
    metadata = collection_metadata or {}

    sections = {
        "time_sensitive_opportunities": _time_sensitive_opportunities(ranked),
        "implied_burdens": _implied_burdens(ranked, price_by_evidence_id),
        "price_signals": _price_signal_items(price_signals),
        "weak_pattern_candidates": _optional_items(run_dir, "weak_pattern_candidates.json"),
        "kill_archive_warnings": _optional_items(run_dir, "kill_archive_warnings.json"),
        "customer_voice_query_yield": _customer_voice_query_yield(ranked, metadata, run_dir),
        "llm_review_outputs": _llm_review_outputs(run_dir),
        "evidence_confidence_risk_notes": _evidence_confidence_risk_notes(ranked, classifications_by_evidence_id),
    }
    return {
        "version": "founder_package_quality_sections_v1",
        "sections": sections,
        "section_order": list(QUALITY_SECTION_KEYS),
    }


def render_founder_package_quality_sections(quality_sections: dict[str, Any]) -> str:
    sections = quality_sections.get("sections", {}) if isinstance(quality_sections, dict) else {}
    lines = ["## Quality review sections", ""]
    for key in QUALITY_SECTION_KEYS:
        title = key.replace("_", " ").title()
        payload = sections.get(key, {})
        items = payload.get("items", []) if isinstance(payload, dict) else []
        lines.extend([f"### {title}", ""])
        if not items:
            empty_state = payload.get("empty_state") if isinstance(payload, dict) else None
            lines.extend([f"- {empty_state or 'No items available.'}", ""])
            continue
        for item in items:
            lines.append(f"- `{item.get('id', 'unknown')}`: {_md(item.get('summary', 'No summary available.'))}")
            for label, field_name in (
                ("Evidence", "evidence_id"),
                ("Source", "source_url"),
                ("Confidence", "confidence"),
                ("Risk", "risk_note"),
                ("Citation", "evidence_cited"),
            ):
                value = item.get(field_name)
                if value not in (None, "", []):
                    lines.append(f"  - {label}: {_md(value)}")
        lines.append("")
    return "\n".join(lines)


def _time_sensitive_opportunities(candidate_signals: list[CandidateSignal]) -> dict[str, Any]:
    items = [
        _signal_item(signal, risk_note="Urgency hint is high; founder should inspect timing and trigger.")
        for signal in candidate_signals
        if signal.urgency_hint == "high"
    ]
    return _section(items, "No high-urgency candidate signals available.")


def _implied_burdens(
    candidate_signals: list[CandidateSignal],
    price_by_evidence_id: dict[str, PriceSignal],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for signal in candidate_signals:
        price_signal = price_by_evidence_id.get(signal.evidence_id)
        burden_hint = price_signal.effort_cost_hint if price_signal else None
        workaround = signal.current_workaround if signal.current_workaround != "unknown" else ""
        text = f"{signal.pain_summary} {workaround}".lower()
        if not burden_hint and not any(term in text for term in ("manual", "spreadsheet", "workaround", "hours/", "hrs/")):
            continue
        summary_parts = [signal.pain_summary]
        if burden_hint:
            summary_parts.append(f"effort: {burden_hint}")
        elif workaround:
            summary_parts.append(f"workaround: {workaround}")
        items.append(_signal_item(signal, summary="; ".join(summary_parts), risk_note="Implied burden is display-only unless explicit effort is cited."))
    return _section(items, "No implied burden signals available.")


def _price_signal_items(price_signals: list[PriceSignal]) -> dict[str, Any]:
    items = []
    for signal in sorted(price_signals, key=lambda item: (-float(item.confidence), item.price_signal_id)):
        if not signal.has_explicit_signal:
            continue
        hints = [
            signal.current_spend_hint,
            signal.effort_cost_hint,
            signal.price_complaint,
            f"wtp:{signal.willingness_to_pay_indicator}" if signal.willingness_to_pay_indicator != "not_detected" else None,
        ]
        items.append(
            {
                "id": signal.price_signal_id,
                "summary": "; ".join(str(hint) for hint in hints if hint),
                "evidence_id": signal.evidence_id,
                "source_url": signal.source_url,
                "confidence": signal.confidence,
                "evidence_cited": signal.evidence_cited,
                "risk_note": "Evidence-only price hint; no budget normalization or inference.",
            }
        )
    return _section(items, "No explicit price signals available.")


def _customer_voice_query_yield(
    candidate_signals: list[CandidateSignal],
    collection_metadata: dict[str, Any],
    run_dir: Path | None,
) -> dict[str, Any]:
    artifact_items = _optional_items(run_dir, "customer_voice_query_yield.json")["items"]
    if artifact_items:
        return _section(artifact_items, "No customer voice query yield artifact available.")
    customer_voice_signals = [signal for signal in candidate_signals if signal.query_kind == "customer_voice_query"]
    if not customer_voice_signals and not collection_metadata.get("query_plan_count"):
        return _section([], "No customer voice query yield available.")
    items = [
        {
            "id": "customer_voice_query_yield",
            "summary": (
                f"{len(customer_voice_signals)} candidate signals from customer_voice_query; "
                f"{collection_metadata.get('query_plan_count', 0)} query plans; "
                f"{collection_metadata.get('scheduled_query_count', 0)} scheduled queries"
            ),
            "confidence": _ratio(len(customer_voice_signals), max(1, int(collection_metadata.get("query_plan_count", 0) or 0))),
        }
    ]
    return _section(items, "No customer voice query yield available.")


def _llm_review_outputs(run_dir: Path | None) -> dict[str, Any]:
    report = _load_optional_json(run_dir, "llm_signal_review_dry_run.json")
    if not isinstance(report, dict):
        return _section([], "No offline LLM review outputs available.")
    items = []
    for item in sorted(report.get("items", []), key=lambda raw: str(raw.get("review_id", ""))):
        output = item.get("review_output") if isinstance(item, dict) else None
        summary = "Advisory dry-run output available."
        confidence = item.get("original_confidence")
        if isinstance(output, dict):
            summary = str(output.get("pain_summary") or summary)
            confidence = output.get("pain_score", confidence)
        items.append(
            {
                "id": str(item.get("review_id") or item.get("candidate_signal_id") or "llm_review"),
                "summary": summary,
                "evidence_id": item.get("evidence_id"),
                "source_url": item.get("source_url"),
                "confidence": confidence,
                "risk_note": "Advisory offline dry-run only; no live LLM/API call.",
            }
        )
    return _section(items, "No offline LLM review outputs available.")


def _evidence_confidence_risk_notes(
    candidate_signals: list[CandidateSignal],
    classifications_by_evidence_id: dict[str, EvidenceClassification],
) -> dict[str, Any]:
    items = []
    for signal in candidate_signals:
        classification = classifications_by_evidence_id.get(signal.evidence_id)
        risk_notes = []
        if signal.signal_type == "needs_human_review":
            risk_notes.append("needs human review")
        if float(signal.confidence) < 0.5:
            risk_notes.append("low confidence")
        if classification and classification.requires_human_review:
            risk_notes.append("classification requires human review")
        if classification and classification.is_noise:
            risk_notes.append("classified noise")
        if not risk_notes:
            continue
        items.append(_signal_item(signal, risk_note=", ".join(risk_notes)))
    return _section(items, "No confidence or risk notes available.")


def _optional_items(run_dir: Path | None, filename: str) -> dict[str, Any]:
    payload = _load_optional_json(run_dir, filename)
    if payload is None:
        return _section([], f"No {filename} artifact available.")
    raw_items = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_items, list):
        return _section([], f"No usable {filename} items available.")
    items = [_normalize_optional_item(item, fallback_prefix=filename.removesuffix(".json")) for item in raw_items if isinstance(item, dict)]
    return _section(sorted(items, key=lambda item: str(item.get("id", ""))), f"No {filename} items available.")


def _normalize_optional_item(item: dict[str, Any], *, fallback_prefix: str) -> dict[str, Any]:
    item_id = item.get("id") or item.get("warning_id") or item.get("pattern_id") or item.get("candidate_id")
    item_id = item_id or item.get("review_id") or item.get("query_id") or fallback_prefix
    summary = item.get("summary") or item.get("warning") or item.get("reason") or item.get("description") or "Optional artifact item."
    return {
        "id": str(item_id),
        "summary": str(summary),
        "evidence_id": item.get("evidence_id") or item.get("evidence_ids"),
        "source_url": item.get("source_url"),
        "confidence": item.get("confidence") or item.get("score"),
        "risk_note": item.get("risk_note") or item.get("risk") or item.get("severity"),
        "evidence_cited": item.get("evidence_cited"),
    }


def _signal_item(signal: CandidateSignal, *, summary: str | None = None, risk_note: str | None = None) -> dict[str, Any]:
    return {
        "id": signal.signal_id,
        "summary": summary or signal.pain_summary,
        "evidence_id": signal.evidence_id,
        "source_url": signal.source_url,
        "confidence": signal.confidence,
        "risk_note": risk_note,
    }


def _section(items: list[dict[str, Any]], empty_state: str) -> dict[str, Any]:
    return {
        "items": items,
        "count": len(items),
        "empty_state": empty_state,
    }


def _load_optional_json(run_dir: Path | None, filename: str) -> Any:
    if run_dir is None:
        return None
    path = run_dir / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(min(1.0, numerator / denominator), 3)


def _md(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(f"`{item}`" for item in value)
    if isinstance(value, (int, float)):
        return f"`{value}`"
    return str(value).replace("\n", " ").replace("|", "\\|").strip()
