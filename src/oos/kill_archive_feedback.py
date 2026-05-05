from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List

from .models import CandidateSignal, KillReason, model_from_dict
from .signal_scoring import apply_kill_pattern_penalty


KILL_ARCHIVE_FEEDBACK_VERSION = "kill_archive_feedback_v1"
DEFAULT_KILL_PATTERN_PENALTY = 0.08
MAX_KILL_PATTERN_PENALTY = 0.16

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "not",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "too",
    "was",
    "with",
}


@dataclass(frozen=True)
class KillArchiveFeedback:
    warning_id: str
    signal_id: str
    evidence_id: str
    kill_pattern_flag: bool
    kill_pattern_penalty: float
    similar_killed_opportunity: str
    kill_reason_id: str
    kill_reason: str
    matched_terms: List[str]
    evidence_linkage: dict[str, str]
    confidence: float
    summary: str
    feedback_mode: str = KILL_ARCHIVE_FEEDBACK_VERSION

    @property
    def id(self) -> str:
        return self.warning_id

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class KillArchiveFeedbackResult:
    candidate_signals: List[CandidateSignal]
    warnings: List[KillArchiveFeedback]


def load_kill_archive(project_root: Path) -> List[KillReason]:
    kills_dir = project_root / "artifacts" / "kills"
    if not kills_dir.exists():
        return []
    kill_reasons: list[KillReason] = []
    for path in sorted(kills_dir.glob("*.json"), key=lambda item: item.name):
        payload = json.loads(path.read_text(encoding="utf-8"))
        kill_reasons.append(model_from_dict(KillReason, payload))
    return kill_reasons


def apply_kill_archive_feedback(
    candidate_signals: Iterable[CandidateSignal],
    *,
    kill_reasons: Iterable[KillReason] | None = None,
    project_root: Path | None = None,
) -> KillArchiveFeedbackResult:
    if kill_reasons is None:
        kill_reasons = load_kill_archive(project_root) if project_root is not None else []
    kill_archive = sorted(list(kill_reasons), key=lambda item: item.id)
    updated_signals: list[CandidateSignal] = []
    warnings: list[KillArchiveFeedback] = []
    for signal in candidate_signals:
        warning = find_kill_archive_match(signal, kill_archive)
        if warning is None:
            updated_signals.append(signal)
            continue
        updated_signals.append(_signal_with_warning(signal, warning))
        warnings.append(warning)
    return KillArchiveFeedbackResult(
        candidate_signals=updated_signals,
        warnings=sorted(warnings, key=lambda item: (item.signal_id, item.kill_reason_id)),
    )


def find_kill_archive_match(
    signal: CandidateSignal,
    kill_reasons: Iterable[KillReason],
) -> KillArchiveFeedback | None:
    signal_terms = _tokens(_signal_text(signal))
    if not signal_terms:
        return None
    matches: list[tuple[float, KillReason, list[str]]] = []
    for kill_reason in kill_reasons:
        kill_terms = _tokens(_kill_reason_text(kill_reason))
        matched_terms = sorted(signal_terms & kill_terms)
        if not _is_match(signal_terms=signal_terms, kill_terms=kill_terms, matched_terms=matched_terms):
            continue
        overlap_score = _overlap_score(signal_terms, kill_terms, matched_terms)
        matches.append((overlap_score, kill_reason, matched_terms))
    if not matches:
        return None

    overlap_score, kill_reason, matched_terms = sorted(matches, key=lambda item: (-item[0], item[1].id))[0]
    penalty = _penalty_for_overlap(overlap_score)
    return KillArchiveFeedback(
        warning_id=f"kill_warning_{signal.signal_id}_{kill_reason.id}",
        signal_id=signal.signal_id,
        evidence_id=signal.evidence_id,
        kill_pattern_flag=True,
        kill_pattern_penalty=penalty,
        similar_killed_opportunity=kill_reason.idea_id,
        kill_reason_id=kill_reason.id,
        kill_reason=kill_reason.summary,
        matched_terms=matched_terms,
        evidence_linkage={
            "signal_id": signal.signal_id,
            "evidence_id": signal.evidence_id,
            "source_url": signal.source_url,
        },
        confidence=overlap_score,
        summary=(
            f"Signal resembles killed opportunity `{kill_reason.idea_id}`; "
            f"score downgraded by {penalty} for founder review only."
        ),
    )


def write_kill_archive_warnings(path: Path, warnings: Iterable[KillArchiveFeedback]) -> None:
    payload = {"items": [warning.to_dict() for warning in sorted(warnings, key=lambda item: item.warning_id)]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _signal_with_warning(signal: CandidateSignal, warning: KillArchiveFeedback) -> CandidateSignal:
    breakdown = dict(signal.scoring_breakdown)
    original_score = float(breakdown.get("final_score", signal.confidence))
    adjusted_score = apply_kill_pattern_penalty(original_score, warning.kill_pattern_penalty)
    explanation = list(breakdown.get("explanation", []))
    if "kill_archive:similar_killed_pattern_penalty" not in explanation:
        explanation.append("kill_archive:similar_killed_pattern_penalty")
    breakdown.update(
        {
            "final_score": adjusted_score,
            "kill_pattern_flag": True,
            "kill_pattern_penalty": warning.kill_pattern_penalty,
            "kill_archive_warning_id": warning.warning_id,
            "similar_killed_opportunity": warning.similar_killed_opportunity,
            "linked_kill_reason_id": warning.kill_reason_id,
            "kill_reason": warning.kill_reason,
            "explanation": explanation,
        }
    )
    return CandidateSignal(
        signal_id=signal.signal_id,
        evidence_id=signal.evidence_id,
        source_id=signal.source_id,
        source_type=signal.source_type,
        source_url=signal.source_url,
        topic_id=signal.topic_id,
        query_kind=signal.query_kind,
        signal_type=signal.signal_type,
        pain_summary=signal.pain_summary,
        target_user=signal.target_user,
        current_workaround=signal.current_workaround,
        buying_intent_hint=signal.buying_intent_hint,
        urgency_hint=signal.urgency_hint,
        confidence=adjusted_score,
        measurement_methods=dict(signal.measurement_methods),
        extraction_mode=signal.extraction_mode,
        classification=signal.classification,
        classification_confidence=signal.classification_confidence,
        traceability=dict(signal.traceability),
        scoring_model_version=signal.scoring_model_version,
        scoring_breakdown=breakdown,
    )


def _is_match(*, signal_terms: set[str], kill_terms: set[str], matched_terms: list[str]) -> bool:
    if len(matched_terms) < 3:
        return False
    if _contains_explicit_phrase(signal_terms, kill_terms, matched_terms):
        return True
    return _overlap_score(signal_terms, kill_terms, matched_terms) >= 0.30


def _contains_explicit_phrase(signal_terms: set[str], kill_terms: set[str], matched_terms: list[str]) -> bool:
    strong_terms = {
        "custom",
        "consulting",
        "spreadsheet",
        "reconciliation",
        "invoice",
        "cash",
        "forecast",
        "manual",
        "workflow",
    }
    return len(set(matched_terms) & strong_terms) >= 2 and bool(signal_terms & kill_terms)


def _overlap_score(signal_terms: set[str], kill_terms: set[str], matched_terms: list[str]) -> float:
    denominator = max(1, min(len(signal_terms), len(kill_terms)))
    return round(min(0.95, len(matched_terms) / denominator), 2)


def _penalty_for_overlap(overlap_score: float) -> float:
    return round(min(MAX_KILL_PATTERN_PENALTY, DEFAULT_KILL_PATTERN_PENALTY + overlap_score * 0.10), 2)


def _signal_text(signal: CandidateSignal) -> str:
    return " ".join(
        [
            signal.pain_summary,
            signal.target_user,
            signal.current_workaround,
            signal.buying_intent_hint,
            signal.urgency_hint,
            signal.signal_type,
        ]
    )


def _kill_reason_text(kill_reason: KillReason) -> str:
    return " ".join(
        [
            kill_reason.idea_id,
            kill_reason.summary,
            kill_reason.looked_attractive_because,
            kill_reason.notes,
            " ".join(kill_reason.failed_checks),
            " ".join(kill_reason.matched_anti_patterns),
        ]
    )


def _tokens(text: str) -> set[str]:
    tokens = {token for token in _TOKEN_RE.findall(str(text or "").lower()) if len(token) >= 3}
    return {token for token in tokens if token not in _STOPWORDS}
