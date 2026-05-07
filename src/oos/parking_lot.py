"""Parking lot / revisit logic — deterministic advisory matching for parked opportunities.

Provides two advisory-only models:
- ``ParkingLotRecord`` — a parked or revisit-later opportunity snapshot.
- ``RevisitMatch`` — a match between new evidence/signals and a parked record.

Matching is purely deterministic (pattern keys, normalized substring/token overlap).
No embeddings, ML, LLM, network calls, or live APIs.
No autonomous portfolio transitions. Founder remains final decision-maker.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from oos.founder_decision_taxonomy import (
    PARK,
    REVISIT_LATER,
    FounderDecisionV2,
    founder_decision_from_dict,
)

PARKING_LOT_SCHEMA_VERSION = "parking_lot.v1"

# ---------------------------------------------------------------------------
# Stop words for conservative token matching
# ---------------------------------------------------------------------------

_STOP_WORDS: set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "of", "at", "by", "for",
    "with", "about", "to", "from", "in", "on", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "shall",
    "not", "no", "nor", "so", "than", "too", "very", "just", "that",
    "this", "these", "those", "it", "its", "we", "you", "he", "she",
    "they", "them", "i", "me", "my", "our", "your", "his", "her",
    "some", "any", "each", "every", "all", "both", "few", "more",
    "most", "other", "such", "only", "own", "same", "into", "up",
    "out", "then", "now", "also",
}

# Minimum significant token overlap required for a substring/token match
_MIN_SIGNIFICANT_TOKEN_OVERLAP = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _make_record_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"parking_lot_{digest}"


def _make_match_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"revisit_match_{digest}"


def _is_non_empty(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace, strip non-alphanumeric except spaces."""
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _significant_tokens(text: str) -> set[str]:
    """Return set of normalized, non-stopword tokens from text."""
    normalized = _normalize_text(text)
    tokens = normalized.split()
    return {t for t in tokens if t not in _STOP_WORDS and len(t) > 1}


def _extract_pattern_keys_from_text(text: str) -> list[str]:
    """Extract potential pattern keys from arbitrary text.

    Produces normalized, deduplicated, sorted keyword-like tokens.
    """
    tokens = _significant_tokens(text)
    # Only keep tokens that look like meaningful keywords (3+ chars)
    meaningful = sorted(t for t in tokens if len(t) >= 3)
    return meaningful


# ---------------------------------------------------------------------------
# ParkingLotRecord
# ---------------------------------------------------------------------------


@dataclass
class ParkingLotRecord:
    """A parked or revisit-later opportunity snapshot.

    advisory_only=True: this record does not change portfolio state.
    """

    record_id: str
    source_decision_id: str
    source_artifact_ids: list[str] = field(default_factory=list)
    linked_opportunity_id: str = ""
    title: str = ""
    summary: str = ""
    reason: str = ""
    pattern_keys: list[str] = field(default_factory=list)
    status: str = "parked"
    advisory_only: bool = True
    schema_version: str = PARKING_LOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParkingLotRecord:
        return cls(
            record_id=str(data.get("record_id", "")),
            source_decision_id=str(data.get("source_decision_id", "")),
            source_artifact_ids=_ordered_strings(data.get("source_artifact_ids", [])),
            linked_opportunity_id=str(data.get("linked_opportunity_id", "")),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            reason=str(data.get("reason", "")),
            pattern_keys=_ordered_strings(data.get("pattern_keys", [])),
            status=str(data.get("status", "parked")),
            advisory_only=bool(data.get("advisory_only", True)),
            schema_version=str(data.get("schema_version", PARKING_LOT_SCHEMA_VERSION)),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.record_id or not self.record_id.strip():
            errors.append("record_id must be a non-empty string")
        if not self.source_decision_id or not self.source_decision_id.strip():
            errors.append("source_decision_id must be a non-empty string")
        if self.status not in ("parked", "revisit_later"):
            errors.append("status must be 'parked' or 'revisit_later'")
        if not self.advisory_only:
            errors.append("ParkingLotRecord must be advisory_only=True")
        if self.schema_version != PARKING_LOT_SCHEMA_VERSION:
            errors.append(f"schema_version must be {PARKING_LOT_SCHEMA_VERSION}")
        return errors


# ---------------------------------------------------------------------------
# RevisitMatch
# ---------------------------------------------------------------------------


@dataclass
class RevisitMatch:
    """A deterministic match between new evidence/opportunity and a parked record.

    advisory_only=True: founder remains final decision-maker.
    """

    match_id: str
    parking_lot_record_id: str
    matched_artifact_id: str = ""
    matched_evidence_id: str = ""
    matched_opportunity_id: str = ""
    match_reason: str = ""
    matched_pattern_keys: list[str] = field(default_factory=list)
    confidence: str = "low"
    suggested_founder_action: str = ""
    advisory_only: bool = True
    schema_version: str = PARKING_LOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RevisitMatch:
        return cls(
            match_id=str(data.get("match_id", "")),
            parking_lot_record_id=str(data.get("parking_lot_record_id", "")),
            matched_artifact_id=str(data.get("matched_artifact_id", "")),
            matched_evidence_id=str(data.get("matched_evidence_id", "")),
            matched_opportunity_id=str(data.get("matched_opportunity_id", "")),
            match_reason=str(data.get("match_reason", "")),
            matched_pattern_keys=_ordered_strings(data.get("matched_pattern_keys", [])),
            confidence=str(data.get("confidence", "low")),
            suggested_founder_action=str(data.get("suggested_founder_action", "")),
            advisory_only=bool(data.get("advisory_only", True)),
            schema_version=str(data.get("schema_version", PARKING_LOT_SCHEMA_VERSION)),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id or not self.match_id.strip():
            errors.append("match_id must be a non-empty string")
        if not self.parking_lot_record_id or not self.parking_lot_record_id.strip():
            errors.append("parking_lot_record_id must be a non-empty string")
        if self.confidence not in ("low", "medium", "high"):
            errors.append("confidence must be 'low', 'medium', or 'high'")
        if not self.advisory_only:
            errors.append("RevisitMatch must be advisory_only=True")
        if self.schema_version != PARKING_LOT_SCHEMA_VERSION:
            errors.append(f"schema_version must be {PARKING_LOT_SCHEMA_VERSION}")
        return errors


# ---------------------------------------------------------------------------
# Builder: decisions -> parking lot records
# ---------------------------------------------------------------------------


def build_parking_lot_records(
    decisions: list[FounderDecisionV2 | dict[str, Any]] | None = None,
) -> list[ParkingLotRecord]:
    """Build ParkingLotRecord items from PARK and REVISIT_LATER founder decisions.

    PROMOTE and KILL decisions are NOT turned into parking lot records.
    NEEDS_MORE_EVIDENCE is also excluded (it's not parked, it's actively being gathered).

    Empty input returns empty list.
    Malformed records are skipped with an explicit warning pattern (no crash).
    """
    if not decisions:
        return []

    eligible: list[FounderDecisionV2] = []
    for d in decisions:
        try:
            normalized = founder_decision_from_dict(d) if isinstance(d, dict) else d
            normalized.validate()
        except (ValueError, TypeError):
            # Skip malformed decisions safely
            continue
        if normalized.decision in (PARK, REVISIT_LATER):
            eligible.append(normalized)

    records: list[ParkingLotRecord] = []
    for d in eligible:
        reasons_str = ", ".join(r.category for r in d.reasons)
        summary_parts = [f"{d.opportunity_id} from {d.evidence_pack_id}"]
        if d.notes:
            summary_parts.append(d.notes)
        summary = "; ".join(summary_parts)

        # Build pattern keys from reasons, opportunity_id, and content
        pattern_keys: list[str] = []
        # Decision reasons as pattern keys
        for r in d.reasons:
            pattern_keys.append(r.category)
        # Extract keywords from opportunity_id and notes
        pattern_keys.extend(_extract_pattern_keys_from_text(d.opportunity_id))
        if d.notes:
            pattern_keys.extend(_extract_pattern_keys_from_text(d.notes))

        pattern_keys = _ordered_strings(pattern_keys)

        source_artifact_ids: list[str] = [d.decision_id]
        source_artifact_ids.extend(d.linked_evidence_ids)
        source_artifact_ids.extend(d.linked_source_signal_ids)
        source_artifact_ids = _ordered_strings(source_artifact_ids)

        record_id = _make_record_id(
            "|".join([d.decision_id, d.decision, reasons_str])
        )

        status = "revisit_later" if d.decision == REVISIT_LATER else "parked"

        records.append(
            ParkingLotRecord(
                record_id=record_id,
                source_decision_id=d.decision_id,
                source_artifact_ids=source_artifact_ids,
                linked_opportunity_id=d.opportunity_id,
                title=d.opportunity_id,
                summary=summary,
                reason=reasons_str,
                pattern_keys=pattern_keys,
                status=status,
            )
        )

    # Deterministic ordering by record_id
    records.sort(key=lambda r: r.record_id)
    return records


# ---------------------------------------------------------------------------
# Matching: new evidence/signals -> parking lot records
# ---------------------------------------------------------------------------


def _match_by_pattern_keys(
    record: ParkingLotRecord,
    evidence_keys: set[str],
) -> tuple[bool, list[str]]:
    """Check for exact pattern key intersection."""
    matched = sorted(record_pattern_keys_set(record) & evidence_keys)
    if matched:
        return True, matched
    return False, []


def _match_by_token_overlap(
    record: ParkingLotRecord,
    evidence_text: str,
) -> tuple[bool, int]:
    """Conservative normalized token overlap.

    Requires at least _MIN_SIGNIFICANT_TOKEN_OVERLAP overlapping tokens.
    Returns (matched, overlap_count).
    """
    record_text = " ".join([record.title, record.summary, record.reason])
    record_tokens = _significant_tokens(record_text)
    evidence_tokens = _significant_tokens(evidence_text)

    if not record_tokens or not evidence_tokens:
        return False, 0

    overlap = record_tokens & evidence_tokens
    overlap_count = len(overlap)
    if overlap_count >= _MIN_SIGNIFICANT_TOKEN_OVERLAP:
        return True, overlap_count
    return False, 0


def _match_by_substring(
    record: ParkingLotRecord,
    evidence_text: str,
) -> tuple[bool, list[str]]:
    """Conservative normalized substring matching.

    Only matches when a significant token (3+ chars) from the record
    appears as a substring in evidence_text, AND the token is not a
    common English word.
    """
    record_text = " ".join([record.title, record.summary, record.reason])
    record_tokens = _significant_tokens(record_text)
    evidence_normalized = _normalize_text(evidence_text)

    matched: list[str] = []
    for token in record_tokens:
        if len(token) >= 4 and token in evidence_normalized:
            matched.append(token)

    if len(matched) >= _MIN_SIGNIFICANT_TOKEN_OVERLAP:
        return True, sorted(matched)
    return False, []


def record_pattern_keys_set(record: ParkingLotRecord) -> set[str]:
    """Return the set of pattern keys for a parking lot record."""
    return set(record.pattern_keys)


def match_revisit_candidates(
    parking_lot_records: list[ParkingLotRecord | dict[str, Any]] | None = None,
    new_evidence: list[dict[str, Any]] | None = None,
) -> list[RevisitMatch]:
    """Match new evidence/opportunity signals against parked/revisit records.

    Matching strategy (in priority order):
    1. Exact pattern_key intersection -> confidence "high"
    2. Conservative normalized token overlap (>=2 sig tokens) -> confidence "medium"
    3. Conservative normalized substring match (>=2 tokens) -> confidence "low"

    Empty inputs return empty outputs.
    No matching occurs for inputs with no pattern_keys or no extractable text.
    Malformed records are safely skipped.
    No autonomous portfolio transitions.
    Results are deterministically ordered.
    """
    if not parking_lot_records or not new_evidence:
        return []

    # Normalize records
    records: list[ParkingLotRecord] = []
    for r in parking_lot_records:
        try:
            if isinstance(r, dict):
                rec = ParkingLotRecord.from_dict(r)
            else:
                rec = r
            errors = rec.validate()
            if errors:
                continue
            records.append(rec)
        except (ValueError, TypeError):
            continue

    if not records:
        return []

    matches: list[RevisitMatch] = []

    for evidence in new_evidence:
        if not isinstance(evidence, dict):
            continue

        evidence_id = str(evidence.get("evidence_id", evidence.get("id", "")))
        artifact_id = str(evidence.get("artifact_id", evidence.get("opportunity_id", "")))
        opportunity_id = str(evidence.get("opportunity_id", ""))
        evidence_summary = str(evidence.get("summary", evidence.get("text", evidence.get("pain_summary", ""))))
        evidence_title = str(evidence.get("title", evidence.get("opportunity_id", "")))
        evidence_pattern_keys_raw = evidence.get("pattern_keys", [])

        if not isinstance(evidence_pattern_keys_raw, list):
            evidence_pattern_keys_raw = []

        evidence_keys: set[str] = set(
            str(k).strip().lower() for k in evidence_pattern_keys_raw if str(k).strip()
        )
        # Also extract pattern keys from evidence text
        evidence_keys |= set(_extract_pattern_keys_from_text(evidence_summary))
        evidence_keys |= set(_extract_pattern_keys_from_text(evidence_title))

        evidence_full_text = " ".join(
            part for part in [evidence_title, evidence_summary] if part
        )

        if not evidence_keys and not evidence_full_text.strip():
            continue

        for record in records:
            matched_keys: list[str] = []
            match_confidence = "low"
            match_reason = ""

            # 1. Pattern key intersection
            pk_match, pk_matched = _match_by_pattern_keys(record, evidence_keys)
            if pk_match:
                matched_keys = pk_matched
                match_confidence = "high"
                match_reason = f"pattern_key_match: {', '.join(pk_matched)}"
            else:
                # 2. Token overlap
                token_match, overlap_count = _match_by_token_overlap(
                    record, evidence_full_text
                )
                if token_match:
                    match_confidence = "medium"
                    match_reason = f"token_overlap: {overlap_count} significant tokens shared"
                else:
                    # 3. Substring match
                    sub_match, sub_matched = _match_by_substring(
                        record, evidence_full_text
                    )
                    if sub_match:
                        matched_keys = sub_matched
                        match_confidence = "low"
                        match_reason = f"substring_match: {', '.join(sub_matched)}"

            if not match_reason:
                continue  # No match

            # Build match_id deterministically
            matched_artifact = artifact_id or evidence_id or opportunity_id
            match_id_seed = "|".join([
                record.record_id,
                matched_artifact,
                match_confidence,
                match_reason,
            ])
            match_id = _make_match_id(match_id_seed)

            suggested_action = (
                f"Review parked opportunity '{record.linked_opportunity_id}' "
                f"(record: {record.record_id}) — new matching evidence found. "
                f"Revisit and decide whether to promote, keep parked, or kill."
            )

            matches.append(
                RevisitMatch(
                    match_id=match_id,
                    parking_lot_record_id=record.record_id,
                    matched_artifact_id=matched_artifact,
                    matched_evidence_id=evidence_id,
                    matched_opportunity_id=opportunity_id or record.linked_opportunity_id,
                    match_reason=match_reason,
                    matched_pattern_keys=matched_keys,
                    confidence=match_confidence,
                    suggested_founder_action=suggested_action,
                )
            )

    # Deterministic ordering: by confidence priority (high > medium > low),
    # then by match_id
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    matches.sort(key=lambda m: (confidence_order.get(m.confidence, 3), m.match_id))

    return matches


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def parking_lot_records_to_json(records: list[ParkingLotRecord]) -> str:
    """Serialize parking lot records to JSON."""
    import json
    return json.dumps(
        [r.to_dict() for r in records],
        ensure_ascii=False,
        indent=2,
    )


def revisit_matches_to_json(matches: list[RevisitMatch]) -> str:
    """Serialize revisit matches to JSON."""
    import json
    return json.dumps(
        [m.to_dict() for m in matches],
        ensure_ascii=False,
        indent=2,
    )


def render_revisit_matches_markdown(matches: list[RevisitMatch]) -> str:
    """Render revisit matches as Markdown."""
    lines: list[str] = []
    lines.append("## Revisit Matches (Advisory)")
    lines.append("")
    lines.append(f"- **Total matches**: {len(matches)}")
    lines.append(f"- **Advisory only**: all matches require founder review")
    lines.append("")

    if not matches:
        lines.append("_No revisit matches found for current evidence._")
        lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    for i, m in enumerate(matches, start=1):
        lines.append(f"### {i}. [{m.confidence.upper()}] `{m.match_id}`")
        lines.append("")
        lines.append(f"- **Parking Lot Record**: `{m.parking_lot_record_id}`")
        if m.matched_opportunity_id:
            lines.append(f"- **Matched Opportunity**: `{m.matched_opportunity_id}`")
        if m.matched_evidence_id:
            lines.append(f"- **Matched Evidence**: `{m.matched_evidence_id}`")
        if m.matched_artifact_id:
            lines.append(f"- **Matched Artifact**: `{m.matched_artifact_id}`")
        lines.append(f"- **Match Reason**: {m.match_reason}")
        if m.matched_pattern_keys:
            lines.append(f"- **Pattern Keys**: {', '.join(m.matched_pattern_keys)}")
        lines.append(f"- **Confidence**: {m.confidence}")
        if m.suggested_founder_action:
            lines.append(f"- **Suggested Action**: {m.suggested_founder_action}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
