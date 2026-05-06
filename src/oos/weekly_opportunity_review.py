from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    FounderDecisionV2,
    founder_decision_from_dict,
)
from oos.founder_feedback_mapping import (
    FounderFeedbackMapping,
    founder_feedback_mapping_from_dict,
)
from oos.founder_preference_profile import (
    FounderPreferencePackageWarning,
    FounderPreferenceProfile,
    founder_preference_profile_from_dict,
    profile_founder_package_warnings,
)

WEEKLY_REVIEW_SCHEMA_VERSION = "weekly_opportunity_review.v1"

SECTION_IDS = (
    "top_opportunities_to_review",
    "promote_candidates",
    "park_candidates",
    "kill_candidates",
    "needs_more_evidence",
    "revisit_queue",
    "evidence_gaps",
    "suggested_interviews_or_validation",
    "suggested_next_queries",
    "preference_profile_warnings",
)

NO_ITEMS_AVAILABLE = "No items available."
NO_DECISIONS_AVAILABLE = "No founder decisions available."
NO_FEEDBACK_AVAILABLE = "No founder feedback mappings available."
NO_PREFERENCE_PROFILE = "No founder preference profile available."
NO_EVIDENCE_PACKS = "No evidence packs available."
NO_PORTFOLIO_STATES = "No portfolio states available."
NO_OPPORTUNITY_CANDIDATES = "No opportunity candidates available."


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _make_package_id(
    decision_ids: list[str],
    feedback_mapping_ids: list[str],
    profile_id: str,
    evidence_pack_ids: list[str],
    opportunity_ids: list[str],
) -> str:
    seed = "|".join(
        [
            ",".join(_ordered_strings(decision_ids)),
            ",".join(_ordered_strings(feedback_mapping_ids)),
            str(profile_id).strip(),
            ",".join(_ordered_strings(evidence_pack_ids)),
            ",".join(_ordered_strings(opportunity_ids)),
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"weekly_review_{digest}"


@dataclass
class WeeklyReviewSectionItem:
    item_id: str
    summary: str
    source_artifact_type: str
    source_artifact_id: str
    linked_decision_ids: list[str] = field(default_factory=list)
    linked_feedback_mapping_ids: list[str] = field(default_factory=list)
    linked_evidence_ids: list[str] = field(default_factory=list)
    linked_opportunity_ids: list[str] = field(default_factory=list)
    linked_pack_ids: list[str] = field(default_factory=list)
    action_hint: str = ""
    urgency: str = "normal"
    category: str = "general"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WeeklyReviewSectionItem:
        return cls(
            item_id=str(data.get("item_id", "")),
            summary=str(data.get("summary", "")),
            source_artifact_type=str(data.get("source_artifact_type", "")),
            source_artifact_id=str(data.get("source_artifact_id", "")),
            linked_decision_ids=_ordered_strings(data.get("linked_decision_ids", [])),
            linked_feedback_mapping_ids=_ordered_strings(data.get("linked_feedback_mapping_ids", [])),
            linked_evidence_ids=_ordered_strings(data.get("linked_evidence_ids", [])),
            linked_opportunity_ids=_ordered_strings(data.get("linked_opportunity_ids", [])),
            linked_pack_ids=_ordered_strings(data.get("linked_pack_ids", [])),
            action_hint=str(data.get("action_hint", "")),
            urgency=str(data.get("urgency", "normal")),
            category=str(data.get("category", "general")),
        )


@dataclass
class WeeklyReviewSection:
    section_id: str
    title: str
    items: list[WeeklyReviewSectionItem]
    empty_state: str = NO_ITEMS_AVAILABLE
    source_artifact_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "items": [item.to_dict() for item in self.items],
            "empty_state": self.empty_state,
            "source_artifact_counts": dict(self.source_artifact_counts),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WeeklyReviewSection:
        return cls(
            section_id=str(data.get("section_id", "")),
            title=str(data.get("title", "")),
            items=[WeeklyReviewSectionItem.from_dict(item) for item in data.get("items", [])],
            empty_state=str(data.get("empty_state", NO_ITEMS_AVAILABLE)),
            source_artifact_counts={str(k): int(v) for k, v in data.get("source_artifact_counts", {}).items()},
        )


@dataclass
class WeeklyOpportunityReviewPackage:
    package_id: str
    generated_at: str
    schema_version: str = WEEKLY_REVIEW_SCHEMA_VERSION
    sections: list[WeeklyReviewSection] = field(default_factory=list)
    source_decision_ids: list[str] = field(default_factory=list)
    source_feedback_mapping_ids: list[str] = field(default_factory=list)
    source_preference_profile_id: str = ""
    source_evidence_pack_ids: list[str] = field(default_factory=list)
    source_opportunity_ids: list[str] = field(default_factory=list)
    source_portfolio_state_ids: list[str] = field(default_factory=list)
    decision_summary: dict[str, int] = field(default_factory=dict)
    advisory_only: bool = True
    autonomous_decisions_made: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
            "sections": [section.to_dict() for section in self.sections],
            "source_decision_ids": list(self.source_decision_ids),
            "source_feedback_mapping_ids": list(self.source_feedback_mapping_ids),
            "source_preference_profile_id": self.source_preference_profile_id,
            "source_evidence_pack_ids": list(self.source_evidence_pack_ids),
            "source_opportunity_ids": list(self.source_opportunity_ids),
            "source_portfolio_state_ids": list(self.source_portfolio_state_ids),
            "decision_summary": dict(self.decision_summary),
            "advisory_only": self.advisory_only,
            "autonomous_decisions_made": self.autonomous_decisions_made,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WeeklyOpportunityReviewPackage:
        return cls(
            package_id=str(data.get("package_id", "")),
            generated_at=str(data.get("generated_at", "")),
            schema_version=str(data.get("schema_version", WEEKLY_REVIEW_SCHEMA_VERSION)),
            sections=[WeeklyReviewSection.from_dict(s) for s in data.get("sections", [])],
            source_decision_ids=_ordered_strings(data.get("source_decision_ids", [])),
            source_feedback_mapping_ids=_ordered_strings(data.get("source_feedback_mapping_ids", [])),
            source_preference_profile_id=str(data.get("source_preference_profile_id", "")),
            source_evidence_pack_ids=_ordered_strings(data.get("source_evidence_pack_ids", [])),
            source_opportunity_ids=_ordered_strings(data.get("source_opportunity_ids", [])),
            source_portfolio_state_ids=_ordered_strings(data.get("source_portfolio_state_ids", [])),
            decision_summary={str(k): int(v) for k, v in data.get("decision_summary", {}).items()},
            advisory_only=bool(data.get("advisory_only", True)),
            autonomous_decisions_made=bool(data.get("autonomous_decisions_made", False)),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.package_id or not self.package_id.strip():
            errors.append("package_id must be a non-empty string")
        if not self.generated_at or not self.generated_at.strip():
            errors.append("generated_at must be a non-empty string")
        if self.schema_version != WEEKLY_REVIEW_SCHEMA_VERSION:
            errors.append(f"schema_version must be {WEEKLY_REVIEW_SCHEMA_VERSION}")
        if self.autonomous_decisions_made:
            errors.append("weekly review package must not make autonomous portfolio decisions")
        if not self.advisory_only:
            errors.append("weekly review package must be advisory only")
        seen_section_ids = set()
        for section in self.sections:
            if section.section_id in seen_section_ids:
                errors.append(f"duplicate section_id: {section.section_id}")
            seen_section_ids.add(section.section_id)
            if section.section_id not in SECTION_IDS:
                errors.append(f"unknown section_id: {section.section_id}")
        for sid in SECTION_IDS:
            if sid not in seen_section_ids:
                errors.append(f"missing required section: {sid}")
        return errors


def build_weekly_opportunity_review_package(
    *,
    decisions: list[FounderDecisionV2 | dict[str, Any]] | None = None,
    feedback_mappings: list[FounderFeedbackMapping | dict[str, Any]] | None = None,
    preference_profile: FounderPreferenceProfile | dict[str, Any] | None = None,
    evidence_packs: list[dict[str, Any]] | None = None,
    portfolio_states: list[dict[str, Any]] | None = None,
    opportunity_candidates: list[dict[str, Any]] | None = None,
) -> WeeklyOpportunityReviewPackage:
    """Build a deterministic weekly opportunity review package.

    All inputs are optional. When an input is absent or empty, the corresponding
    sections render with clear empty states.

    The package is advisory only; it does not make autonomous portfolio decisions.
    """

    normalized_decisions: list[FounderDecisionV2] = [
        founder_decision_from_dict(d) if isinstance(d, dict) else d for d in (decisions or [])
    ]
    normalized_mappings: list[FounderFeedbackMapping] = [
        founder_feedback_mapping_from_dict(m) if isinstance(m, dict) else m for m in (feedback_mappings or [])
    ]
    normalized_profile: FounderPreferenceProfile | None = None
    if preference_profile is not None:
        normalized_profile = (
            founder_preference_profile_from_dict(preference_profile)
            if isinstance(preference_profile, dict)
            else preference_profile
        )

    packs = list(evidence_packs or [])
    portfolios = list(portfolio_states or [])
    opp_candidates = list(opportunity_candidates or [])

    decision_ids = _ordered_strings([d.decision_id for d in normalized_decisions])
    mapping_ids = _ordered_strings([m.mapping_id for m in normalized_mappings])
    profile_id = normalized_profile.profile_id if normalized_profile else ""
    pack_ids = _ordered_strings([str(p.get("evidence_pack_id", "")) for p in packs])
    opp_ids = _ordered_strings([str(o.get("opportunity_id", o.get("id", ""))) for o in opp_candidates])

    package_id = _make_package_id(decision_ids, mapping_ids, profile_id, pack_ids, opp_ids)

    decision_counts = _count_decisions(normalized_decisions)
    warnings = profile_founder_package_warnings(normalized_profile) if normalized_profile else []

    portfolio_state_ids = _ordered_strings(
        [str(p.get("id", "")) for p in portfolios]
    )

    package = WeeklyOpportunityReviewPackage(
        package_id=package_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        sections=[
            _build_top_opportunities_to_review(normalized_decisions, normalized_mappings, opp_candidates),
            _build_promote_candidates(normalized_decisions),
            _build_park_candidates(normalized_decisions),
            _build_kill_candidates(normalized_decisions),
            _build_needs_more_evidence(normalized_decisions),
            _build_revisit_queue(normalized_decisions),
            _build_evidence_gaps(normalized_decisions, normalized_mappings, normalized_profile),
            _build_suggested_interviews_or_validation(normalized_decisions, opp_candidates),
            _build_suggested_next_queries(normalized_profile, normalized_decisions, packs),
            _build_preference_profile_warnings(warnings, normalized_profile),
        ],
        source_decision_ids=decision_ids,
        source_feedback_mapping_ids=mapping_ids,
        source_preference_profile_id=profile_id,
        source_evidence_pack_ids=pack_ids,
        source_opportunity_ids=opp_ids,
        source_portfolio_state_ids=portfolio_state_ids,
        decision_summary=decision_counts,
    )
    errors = package.validate()
    if errors:
        raise ValueError("; ".join(errors))
    return package


def _count_decisions(
    decisions: list[FounderDecisionV2],
) -> dict[str, int]:
    counts: dict[str, int] = {"total": len(decisions)}
    for d in decisions:
        counts[d.decision] = counts.get(d.decision, 0) + 1
    return counts


def _build_top_opportunities_to_review(
    decisions: list[FounderDecisionV2],
    mappings: list[FounderFeedbackMapping],
    opp_candidates: list[dict[str, Any]],
) -> WeeklyReviewSection:
    items: list[WeeklyReviewSectionItem] = []

    # Priority: promote decisions first, then high-confidence opportunity candidates
    promote_decisions = [d for d in decisions if d.decision == PROMOTE]
    promote_decisions = sorted(promote_decisions, key=lambda d: (-d.confidence, d.decision_id))

    for d in promote_decisions:
        reasons_str = ", ".join(r.category for r in d.reasons)
        mapping_ids = [m.mapping_id for m in mappings if m.decision_id == d.decision_id]
        items.append(
            WeeklyReviewSectionItem(
                item_id=f"top_{d.decision_id}",
                summary=f"[PROMOTE] {d.opportunity_id}: confidence={d.confidence:.3f}; reasons: {reasons_str}; notes: {d.notes or 'none'}",
                source_artifact_type="founder_decision_v2",
                source_artifact_id=d.decision_id,
                linked_decision_ids=[d.decision_id],
                linked_feedback_mapping_ids=_ordered_strings(mapping_ids),
                linked_evidence_ids=list(d.linked_evidence_ids),
                linked_opportunity_ids=[d.opportunity_id],
                linked_pack_ids=[d.evidence_pack_id],
                action_hint="Review promoted opportunity; plan next validation step.",
                urgency="high",
                category="promote",
            )
        )

    # Also include non-decision opportunity candidates sorted by some score if available
    decide_opp_set = {d.opportunity_id for d in decisions}
    undecided = [o for o in opp_candidates if str(o.get("opportunity_id", o.get("id", ""))) not in decide_opp_set]
    undecided = sorted(undecided, key=lambda o: str(o.get("opportunity_id", o.get("id", ""))))

    for o in undecided:
        oid = str(o.get("opportunity_id", o.get("id", "unknown")))
        summary_parts = []
        if o.get("pain_summary"):
            summary_parts.append(str(o["pain_summary"]))
        if o.get("confidence") is not None:
            summary_parts.append(f"confidence={float(o['confidence']):.3f}")
        summary = "; ".join(summary_parts) if summary_parts else f"Opportunity candidate {oid}"
        items.append(
            WeeklyReviewSectionItem(
                item_id=f"top_undecided_{oid}",
                summary=summary,
                source_artifact_type="opportunity_candidate",
                source_artifact_id=oid,
                linked_opportunity_ids=[oid],
                action_hint="Founder review needed: no decision recorded yet.",
                urgency="normal",
                category="undecided",
            )
        )

    return WeeklyReviewSection(
        section_id="top_opportunities_to_review",
        title="Top Opportunities to Review",
        items=items,
        empty_state="No promote decisions or undecided opportunity candidates available.",
        source_artifact_counts={
            "decisions": len(decisions),
            "feedback_mappings": len(mappings),
            "opportunity_candidates": len(opp_candidates),
        },
    )


def _build_promote_candidates(
    decisions: list[FounderDecisionV2],
) -> WeeklyReviewSection:
    promote_list = [d for d in decisions if d.decision == PROMOTE]
    promote_list = sorted(promote_list, key=lambda d: (-d.confidence, d.decision_id))

    items: list[WeeklyReviewSectionItem] = []
    for d in promote_list:
        reasons_str = ", ".join(r.category for r in d.reasons)
        items.append(
            WeeklyReviewSectionItem(
                item_id=f"promote_{d.decision_id}",
                summary=f"{d.opportunity_id} from {d.evidence_pack_id}: {reasons_str} (confidence={d.confidence:.3f})",
                source_artifact_type="founder_decision_v2",
                source_artifact_id=d.decision_id,
                linked_decision_ids=[d.decision_id],
                linked_evidence_ids=list(d.linked_evidence_ids),
                linked_opportunity_ids=[d.opportunity_id],
                linked_pack_ids=[d.evidence_pack_id],
                action_hint="Validate with customer interviews; gather additional evidence.",
                urgency="high",
                category="promote",
            )
        )

    return WeeklyReviewSection(
        section_id="promote_candidates",
        title="Promote Candidates",
        items=items,
        empty_state="No promoted opportunities.",
        source_artifact_counts={"promote_decisions": len(promote_list)},
    )


def _build_park_candidates(
    decisions: list[FounderDecisionV2],
) -> WeeklyReviewSection:
    park_list = [d for d in decisions if d.decision == PARK]
    park_list = sorted(park_list, key=lambda d: (-d.confidence, d.decision_id))

    items: list[WeeklyReviewSectionItem] = []
    for d in park_list:
        reasons_str = ", ".join(r.category for r in d.reasons)
        items.append(
            WeeklyReviewSectionItem(
                item_id=f"park_{d.decision_id}",
                summary=f"{d.opportunity_id} from {d.evidence_pack_id}: {reasons_str} (confidence={d.confidence:.3f})",
                source_artifact_type="founder_decision_v2",
                source_artifact_id=d.decision_id,
                linked_decision_ids=[d.decision_id],
                linked_evidence_ids=list(d.linked_evidence_ids),
                linked_opportunity_ids=[d.opportunity_id],
                linked_pack_ids=[d.evidence_pack_id],
                action_hint="Keep parked; revisit when new evidence or signals appear.",
                urgency="low",
                category="park",
            )
        )

    return WeeklyReviewSection(
        section_id="park_candidates",
        title="Park Candidates",
        items=items,
        empty_state="No parked opportunities.",
        source_artifact_counts={"park_decisions": len(park_list)},
    )


def _build_kill_candidates(
    decisions: list[FounderDecisionV2],
) -> WeeklyReviewSection:
    kill_list = [d for d in decisions if d.decision == KILL]
    kill_list = sorted(kill_list, key=lambda d: (-d.confidence, d.decision_id))

    items: list[WeeklyReviewSectionItem] = []
    for d in kill_list:
        reasons_str = ", ".join(r.category for r in d.reasons)
        items.append(
            WeeklyReviewSectionItem(
                item_id=f"kill_{d.decision_id}",
                summary=f"{d.opportunity_id} from {d.evidence_pack_id}: {reasons_str} (confidence={d.confidence:.3f}); notes: {d.notes or 'none'}",
                source_artifact_type="founder_decision_v2",
                source_artifact_id=d.decision_id,
                linked_decision_ids=[d.decision_id],
                linked_evidence_ids=list(d.linked_evidence_ids),
                linked_opportunity_ids=[d.opportunity_id],
                linked_pack_ids=[d.evidence_pack_id],
                action_hint="Record kill reason for future pattern suppression; do not re-surface.",
                urgency="normal",
                category="kill",
            )
        )

    return WeeklyReviewSection(
        section_id="kill_candidates",
        title="Kill Candidates",
        items=items,
        empty_state="No killed opportunities.",
        source_artifact_counts={"kill_decisions": len(kill_list)},
    )


def _build_needs_more_evidence(
    decisions: list[FounderDecisionV2],
) -> WeeklyReviewSection:
    nme_list = [d for d in decisions if d.decision == NEEDS_MORE_EVIDENCE]
    nme_list = sorted(nme_list, key=lambda d: (-d.confidence, d.decision_id))

    items: list[WeeklyReviewSectionItem] = []
    for d in nme_list:
        reasons_str = ", ".join(r.category for r in d.reasons)
        items.append(
            WeeklyReviewSectionItem(
                item_id=f"needs_more_evidence_{d.decision_id}",
                summary=f"{d.opportunity_id} from {d.evidence_pack_id}: {reasons_str} (confidence={d.confidence:.3f})",
                source_artifact_type="founder_decision_v2",
                source_artifact_id=d.decision_id,
                linked_decision_ids=[d.decision_id],
                linked_evidence_ids=list(d.linked_evidence_ids),
                linked_opportunity_ids=[d.opportunity_id],
                linked_pack_ids=[d.evidence_pack_id],
                action_hint="Run customer-voice queries, collect from additional sources, or run interviews.",
                urgency="normal",
                category="needs_more_evidence",
            )
        )

    return WeeklyReviewSection(
        section_id="needs_more_evidence",
        title="Needs More Evidence",
        items=items,
        empty_state="No opportunities flagged as needing more evidence.",
        source_artifact_counts={"needs_more_evidence_decisions": len(nme_list)},
    )


def _build_revisit_queue(
    decisions: list[FounderDecisionV2],
) -> WeeklyReviewSection:
    revisit_list = [d for d in decisions if d.decision == REVISIT_LATER]
    revisit_list = sorted(revisit_list, key=lambda d: (-d.confidence, d.decision_id))

    items: list[WeeklyReviewSectionItem] = []
    for d in revisit_list:
        reasons_str = ", ".join(r.category for r in d.reasons)
        items.append(
            WeeklyReviewSectionItem(
                item_id=f"revisit_{d.decision_id}",
                summary=f"{d.opportunity_id} from {d.evidence_pack_id}: {reasons_str} (confidence={d.confidence:.3f})",
                source_artifact_type="founder_decision_v2",
                source_artifact_id=d.decision_id,
                linked_decision_ids=[d.decision_id],
                linked_evidence_ids=list(d.linked_evidence_ids),
                linked_opportunity_ids=[d.opportunity_id],
                linked_pack_ids=[d.evidence_pack_id],
                action_hint="Check for new matching evidence before next review cycle.",
                urgency="low",
                category="revisit_later",
            )
        )

    return WeeklyReviewSection(
        section_id="revisit_queue",
        title="Revisit Queue",
        items=items,
        empty_state="No opportunities queued for revisit.",
        source_artifact_counts={"revisit_decisions": len(revisit_list)},
    )


def _build_evidence_gaps(
    decisions: list[FounderDecisionV2],
    mappings: list[FounderFeedbackMapping],
    profile: FounderPreferenceProfile | None,
) -> WeeklyReviewSection:
    items: list[WeeklyReviewSectionItem] = []

    # From decisions: needs_more_evidence reasons
    for d in decisions:
        if d.decision == NEEDS_MORE_EVIDENCE:
            for r in d.reasons:
                items.append(
                    WeeklyReviewSectionItem(
                        item_id=f"gap_{d.decision_id}_{r.category}",
                        summary=f"Decision {d.decision_id} flagged: {r.category} — {r.note or 'no additional note'}",
                        source_artifact_type="founder_decision_v2",
                        source_artifact_id=d.decision_id,
                        linked_decision_ids=[d.decision_id],
                        linked_evidence_ids=list(d.linked_evidence_ids),
                        linked_opportunity_ids=[d.opportunity_id],
                        linked_pack_ids=[d.evidence_pack_id],
                        action_hint="Collect the missing evidence type before next review.",
                        urgency="normal",
                        category="evidence_gap",
                    )
                )

    # From profile: areas_needing_more_evidence
    if profile and profile.areas_needing_more_evidence:
        for area in profile.areas_needing_more_evidence:
            items.append(
                WeeklyReviewSectionItem(
                    item_id=f"gap_profile_{area}",
                    summary=f"Profile-level evidence gap: {area}",
                    source_artifact_type="founder_preference_profile",
                    source_artifact_id=profile.profile_id,
                    linked_decision_ids=list(profile.source_decision_ids),
                    linked_feedback_mapping_ids=list(profile.source_feedback_mapping_ids),
                    action_hint="Address profile-level evidence gaps by scoping new queries or sources.",
                    urgency="normal",
                    category="evidence_gap",
                )
            )

    items = sorted(items, key=lambda i: i.item_id)
    return WeeklyReviewSection(
        section_id="evidence_gaps",
        title="Evidence Gaps",
        items=items,
        empty_state="No evidence gaps identified.",
        source_artifact_counts={
            "decisions": len(decisions),
            "feedback_mappings": len(mappings),
            "profile_available": 1 if profile else 0,
        },
    )


def _build_suggested_interviews_or_validation(
    decisions: list[FounderDecisionV2],
    opp_candidates: list[dict[str, Any]],
) -> WeeklyReviewSection:
    items: list[WeeklyReviewSectionItem] = []

    # For promote and needs_more_evidence decisions, suggest interviews
    for d in decisions:
        if d.decision in (PROMOTE, NEEDS_MORE_EVIDENCE):
            items.append(
                WeeklyReviewSectionItem(
                    item_id=f"interview_{d.decision_id}",
                    summary=(
                        f"Suggested customer interview for {d.opportunity_id}: "
                        f"validate pain, workaround, and willingness-to-pay with real users. "
                        f"Decision: {d.decision}; evidence pack: {d.evidence_pack_id}."
                    ),
                    source_artifact_type="founder_decision_v2",
                    source_artifact_id=d.decision_id,
                    linked_decision_ids=[d.decision_id],
                    linked_evidence_ids=list(d.linked_evidence_ids),
                    linked_opportunity_ids=[d.opportunity_id],
                    linked_pack_ids=[d.evidence_pack_id],
                    action_hint="Schedule 3-5 customer discovery interviews.",
                    urgency="high" if d.decision == PROMOTE else "normal",
                    category="suggested_interview",
                )
            )

    # For non-decision opportunity candidates that look promising, suggest validation
    decide_opp_set = {d.opportunity_id for d in decisions}
    for o in opp_candidates:
        oid = str(o.get("opportunity_id", o.get("id", "")))
        if oid in decide_opp_set:
            continue
        confidence = o.get("confidence")
        if confidence is not None and float(confidence) >= 0.5:
            items.append(
                WeeklyReviewSectionItem(
                    item_id=f"validation_{oid}",
                    summary=(
                        f"Suggested validation for undecided opportunity {oid}: "
                        f"review source evidence and decide promote/park/kill/needs-more-evidence."
                    ),
                    source_artifact_type="opportunity_candidate",
                    source_artifact_id=oid,
                    linked_opportunity_ids=[oid],
                    action_hint="Review evidence pack and make a founder decision.",
                    urgency="normal",
                    category="suggested_validation",
                )
            )

    items = sorted(items, key=lambda i: (0 if i.urgency == "high" else 1, i.item_id))
    return WeeklyReviewSection(
        section_id="suggested_interviews_or_validation",
        title="Suggested Interviews or Validation Actions",
        items=items,
        empty_state="No interview or validation suggestions available.",
        source_artifact_counts={
            "decisions": len(decisions),
            "opportunity_candidates": len(opp_candidates),
        },
    )


def _build_suggested_next_queries(
    profile: FounderPreferenceProfile | None,
    decisions: list[FounderDecisionV2],
    packs: list[dict[str, Any]],
) -> WeeklyReviewSection:
    items: list[WeeklyReviewSectionItem] = []

    # If profile has preferred pain types, suggest running queries for them
    if profile and profile.preferred_pain_types:
        for pt in profile.preferred_pain_types[:3]:
            items.append(
                WeeklyReviewSectionItem(
                    item_id=f"query_preferred_{pt}",
                    summary=f"Run customer-voice or source queries for preferred pain type: {pt}",
                    source_artifact_type="founder_preference_profile",
                    source_artifact_id=profile.profile_id,
                    linked_decision_ids=list(profile.source_decision_ids),
                    action_hint="Generate customer-voice queries scoped to this pain type.",
                    urgency="normal",
                    category="suggested_query",
                )
            )

    # If there are needs_more_evidence decisions, suggest collecting more
    nme_decisions = [d for d in decisions if d.decision == NEEDS_MORE_EVIDENCE]
    if nme_decisions:
        items.append(
            WeeklyReviewSectionItem(
                item_id="query_more_evidence",
                summary=(
                    f"{len(nme_decisions)} opportunity(s) need more evidence. "
                    f"Consider running a broader discovery run or enabling additional source types."
                ),
                source_artifact_type="founder_decision_v2",
                source_artifact_id="needs_more_evidence_summary",
                linked_decision_ids=_ordered_strings([d.decision_id for d in nme_decisions]),
                action_hint="Run discovery-weakly with expanded query scope.",
                urgency="normal",
                category="suggested_query",
            )
        )

    if not items:
        return WeeklyReviewSection(
            section_id="suggested_next_queries",
            title="Suggested Next Queries",
            items=[],
            empty_state="No suggested queries. Run discovery to generate evidence.",
            source_artifact_counts={
                "profile_available": 1 if profile else 0,
                "decisions": len(decisions),
                "evidence_packs": len(packs),
            },
        )

    return WeeklyReviewSection(
        section_id="suggested_next_queries",
        title="Suggested Next Queries",
        items=items,
        empty_state="No suggested queries.",
        source_artifact_counts={
            "profile_available": 1 if profile else 0,
            "decisions": len(decisions),
            "evidence_packs": len(packs),
        },
    )


def _build_preference_profile_warnings(
    warnings: list[FounderPreferencePackageWarning],
    profile: FounderPreferenceProfile | None,
) -> WeeklyReviewSection:
    items: list[WeeklyReviewSectionItem] = []

    for w in warnings:
        items.append(
            WeeklyReviewSectionItem(
                item_id=w.warning_id,
                summary=f"[{w.category}/{w.severity}] {w.message}",
                source_artifact_type="founder_preference_profile",
                source_artifact_id=profile.profile_id if profile else "",
                linked_decision_ids=list(w.linked_decision_ids),
                linked_feedback_mapping_ids=list(w.linked_mapping_ids),
                action_hint="Review profile warnings and adjust query/collection strategy if needed.",
                urgency="normal",
                category=w.category,
            )
        )

    return WeeklyReviewSection(
        section_id="preference_profile_warnings",
        title="Preference / Profile Warnings",
        items=items,
        empty_state="No preference profile warnings." if profile else NO_PREFERENCE_PROFILE,
        source_artifact_counts={
            "profile_available": 1 if profile else 0,
            "warning_count": len(warnings),
        },
    )


def weekly_review_package_to_json(package: WeeklyOpportunityReviewPackage) -> str:
    import json

    return json.dumps(package.to_dict(), ensure_ascii=False, indent=2)


def render_weekly_review_package_markdown(package: WeeklyOpportunityReviewPackage) -> str:
    lines: list[str] = []
    lines.append(f"# Weekly Opportunity Review Package")
    lines.append("")
    lines.append(f"- **Package ID**: `{package.package_id}`")
    lines.append(f"- **Generated**: {package.generated_at}")
    lines.append(f"- **Schema**: {package.schema_version}")
    lines.append(f"- **Advisory only**: {str(package.advisory_only).lower()}")
    lines.append("")
    lines.append("## Decision Summary")
    lines.append("")
    if package.decision_summary and package.decision_summary.get("total", 0) > 0:
        for k, v in sorted(package.decision_summary.items()):
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- No decisions recorded.")
    lines.append("")

    for section in package.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        if not section.items:
            lines.append(f"- *{section.empty_state}*")
            lines.append("")
            continue
        for item in section.items:
            cat_line = f" [{item.category}]" if item.category else ""
            urg_line = f" (urgency: {item.urgency})" if item.urgency != "normal" else ""
            lines.append(f"### `{item.item_id}`{cat_line}{urg_line}")
            lines.append("")
            lines.append(f"- **Summary**: {item.summary}")
            lines.append(f"- **Source**: {item.source_artifact_type}/{item.source_artifact_id}")
            if item.action_hint:
                lines.append(f"- **Action**: {item.action_hint}")
            if item.linked_decision_ids:
                lines.append(f"- **Decision IDs**: {', '.join(item.linked_decision_ids)}")
            if item.linked_feedback_mapping_ids:
                lines.append(f"- **Feedback Mapping IDs**: {', '.join(item.linked_feedback_mapping_ids)}")
            if item.linked_evidence_ids:
                lines.append(f"- **Evidence IDs**: {', '.join(item.linked_evidence_ids)}")
            if item.linked_opportunity_ids:
                lines.append(f"- **Opportunity IDs**: {', '.join(item.linked_opportunity_ids)}")
            if item.linked_pack_ids:
                lines.append(f"- **Evidence Pack IDs**: {', '.join(item.linked_pack_ids)}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
