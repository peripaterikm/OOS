"""Next best founder actions — deterministic advisory action recommendations.

Converts a WeeklyOpportunityReviewPackage (or equivalent serialized dict)
into a prioritized, flattened list of advisory FounderAction items for the
founder to work through.

No autonomous decisions. No LLM/API calls. No portfolio transitions.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


FOUNDER_ACTION_SCHEMA_VERSION = "founder_action.v1"

ALLOWED_ACTION_TYPES = (
    "review_promote_candidate",
    "collect_more_evidence",
    "interview_customer",
    "validate_price_signal",
    "revisit_parked_opportunity",
    "consider_kill_candidate",
    "review_preference_warning",
    "run_customer_voice_queries",
    "address_evidence_gap",
    "review_undecided_opportunity",
)

# Priority bands: lower = more urgent
PRIORITY_HIGH = 1
PRIORITY_NORMAL = 2
PRIORITY_LOW = 3


# ---------------------------------------------------------------------------
# FounderAction model
# ---------------------------------------------------------------------------


@dataclass
class FounderAction:
    """A single advisory action recommendation for the founder.

    Every action is advisory_only=True. The system never makes autonomous
    portfolio decisions.
    """

    action_id: str
    action_type: str
    title: str
    rationale: str
    priority: int = PRIORITY_NORMAL
    linked_section_ids: list[str] = field(default_factory=list)
    linked_item_ids: list[str] = field(default_factory=list)
    linked_decision_ids: list[str] = field(default_factory=list)
    linked_opportunity_ids: list[str] = field(default_factory=list)
    linked_evidence_ids: list[str] = field(default_factory=list)
    linked_pack_ids: list[str] = field(default_factory=list)
    suggested_next_step: str = ""
    advisory_only: bool = True
    schema_version: str = FOUNDER_ACTION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "title": self.title,
            "rationale": self.rationale,
            "priority": self.priority,
            "linked_section_ids": list(self.linked_section_ids),
            "linked_item_ids": list(self.linked_item_ids),
            "linked_decision_ids": list(self.linked_decision_ids),
            "linked_opportunity_ids": list(self.linked_opportunity_ids),
            "linked_evidence_ids": list(self.linked_evidence_ids),
            "linked_pack_ids": list(self.linked_pack_ids),
            "suggested_next_step": self.suggested_next_step,
            "advisory_only": self.advisory_only,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FounderAction:
        return cls(
            action_id=str(data.get("action_id", "")),
            action_type=str(data.get("action_type", "")),
            title=str(data.get("title", "")),
            rationale=str(data.get("rationale", "")),
            priority=int(data.get("priority", PRIORITY_NORMAL)),
            linked_section_ids=_ordered_strings(data.get("linked_section_ids", [])),
            linked_item_ids=_ordered_strings(data.get("linked_item_ids", [])),
            linked_decision_ids=_ordered_strings(data.get("linked_decision_ids", [])),
            linked_opportunity_ids=_ordered_strings(data.get("linked_opportunity_ids", [])),
            linked_evidence_ids=_ordered_strings(data.get("linked_evidence_ids", [])),
            linked_pack_ids=_ordered_strings(data.get("linked_pack_ids", [])),
            suggested_next_step=str(data.get("suggested_next_step", "")),
            advisory_only=bool(data.get("advisory_only", True)),
            schema_version=str(data.get("schema_version", FOUNDER_ACTION_SCHEMA_VERSION)),
        )


# ---------------------------------------------------------------------------
# Action ID helpers
# ---------------------------------------------------------------------------


def _make_action_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]
    return f"founder_action_{digest}"


def _ordered_strings(values: list[Any]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


# ---------------------------------------------------------------------------
# Builder: weekly review package dict -> list[FounderAction]
# ---------------------------------------------------------------------------


def build_next_best_founder_actions(
    weekly_review_package: dict[str, Any],
) -> list[FounderAction]:
    """Convert a weekly opportunity review package dict into a
    deterministic, prioritized list of advisory founder actions.

    Accepts:
      - A dict matching ``WeeklyOpportunityReviewPackage.to_dict()``.
      - An empty dict for graceful empty-handling.

    Returns:
      A list of ``FounderAction`` items sorted by priority (ascending),
      then by action_type, then by action_id for full determinism.
      Empty input yields an empty list.
    """
    if not weekly_review_package:
        return []

    sections: list[dict[str, Any]] = weekly_review_package.get("sections", [])
    if not sections:
        return []

    actions: list[FounderAction] = []

    for section in sections:
        section_id = str(section.get("section_id", ""))
        items = section.get("items", [])

        for item in items:
            item_dict = item if isinstance(item, dict) else {}
            action = _item_to_action(item_dict, section_id)
            if action is not None:
                actions.append(action)

    # Deterministic sort: priority asc, then action_type, then action_id
    actions.sort(key=lambda a: (a.priority, a.action_type, a.action_id))

    # Ensure every action has an action_id
    for i, action in enumerate(actions):
        if not action.action_id:
            action.action_id = _make_action_id(
                f"{action.action_type}|{action.title}|{i}"
            )

    return actions


# ---------------------------------------------------------------------------
# Section item -> FounderAction mapping
# ---------------------------------------------------------------------------


def _item_to_action(
    item: dict[str, Any],
    section_id: str,
) -> FounderAction | None:
    """Map a single WeeklyReviewSectionItem dict to a FounderAction, or
    return None when the item does not warrant a standalone action."""
    item_id = str(item.get("item_id", ""))
    if not item_id:
        return None

    summary = str(item.get("summary", ""))
    action_hint = str(item.get("action_hint", ""))
    urgency = str(item.get("urgency", "normal"))
    category = str(item.get("category", ""))
    source_artifact_type = str(item.get("source_artifact_type", ""))
    source_artifact_id = str(item.get("source_artifact_id", ""))

    linked_decisions = _ordered_strings(item.get("linked_decision_ids", []))
    linked_opp_ids = _ordered_strings(item.get("linked_opportunity_ids", []))
    linked_evidence = _ordered_strings(item.get("linked_evidence_ids", []))
    linked_packs = _ordered_strings(item.get("linked_pack_ids", []))
    linked_mappings = _ordered_strings(item.get("linked_feedback_mapping_ids", []))

    # Determine action_type and title from section + category
    action_type, title = _derive_action_type_and_title(
        section_id=section_id,
        category=category,
        summary=summary,
    )

    # Determine priority from urgency
    priority = PRIORITY_NORMAL
    if urgency == "high":
        priority = PRIORITY_HIGH
    elif urgency == "low":
        priority = PRIORITY_LOW

    # Build rationale from summary and action_hint
    rationale = summary
    if action_hint:
        rationale = f"{summary} Next step: {action_hint}"

    # Suggested next step
    suggested_next_step = action_hint or _default_next_step(action_type)

    action_id = _make_action_id(
        "|".join([action_type, section_id, item_id, source_artifact_id])
    )

    return FounderAction(
        action_id=action_id,
        action_type=action_type,
        title=title,
        rationale=rationale,
        priority=priority,
        linked_section_ids=[section_id],
        linked_item_ids=[item_id],
        linked_decision_ids=linked_decisions,
        linked_opportunity_ids=linked_opp_ids,
        linked_evidence_ids=linked_evidence,
        linked_pack_ids=linked_packs,
        suggested_next_step=suggested_next_step,
        advisory_only=True,
    )


# ---------------------------------------------------------------------------
# Action type derivation
# ---------------------------------------------------------------------------


_SECTION_TO_ACTION_TYPE: dict[str, str] = {
    "promote_candidates": "review_promote_candidate",
    "park_candidates": "collect_more_evidence",
    "kill_candidates": "consider_kill_candidate",
    "needs_more_evidence": "collect_more_evidence",
    "revisit_queue": "revisit_parked_opportunity",
    "evidence_gaps": "address_evidence_gap",
    "suggested_interviews_or_validation": "interview_customer",
    "suggested_next_queries": "run_customer_voice_queries",
    "preference_profile_warnings": "review_preference_warning",
    "top_opportunities_to_review": "review_undecided_opportunity",
}


_SECTION_TO_TITLE_PREFIX: dict[str, str] = {
    "promote_candidates": "Review promote candidate",
    "park_candidates": "Collect more evidence for parked opportunity",
    "kill_candidates": "Consider kill decision for",
    "needs_more_evidence": "Gather additional evidence for",
    "revisit_queue": "Revisit parked opportunity",
    "evidence_gaps": "Address evidence gap",
    "suggested_interviews_or_validation": "Schedule customer interview for",
    "suggested_next_queries": "Run customer voice queries",
    "preference_profile_warnings": "Review preference warning",
    "top_opportunities_to_review": "Review undecided opportunity",
}

_CATEGORY_SPECIFIC_ACTION_TYPE: dict[str, str] = {
    "suggested_interview": "interview_customer",
    "suggested_validation": "review_undecided_opportunity",
    "suggested_query": "run_customer_voice_queries",
    "evidence_gap": "address_evidence_gap",
    "promote": "review_promote_candidate",
    "park": "collect_more_evidence",
    "kill": "consider_kill_candidate",
    "needs_more_evidence": "collect_more_evidence",
    "revisit_later": "revisit_parked_opportunity",
    "undecided": "review_undecided_opportunity",
}


def _derive_action_type_and_title(
    *,
    section_id: str,
    category: str,
    summary: str,
) -> tuple[str, str]:
    """Derive the action_type and human-readable title from section and
    category info."""
    # First try category-specific mapping
    action_type = _CATEGORY_SPECIFIC_ACTION_TYPE.get(category)
    if action_type is None:
        action_type = _SECTION_TO_ACTION_TYPE.get(section_id, "collect_more_evidence")

    prefix = _SECTION_TO_TITLE_PREFIX.get(section_id, "Review")
    # Build a concise title from the summary
    short_summary = _truncate_summary(summary, 120)
    title = f"{prefix}: {short_summary}"

    return action_type, title


def _truncate_summary(text: str, max_len: int) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def _default_next_step(action_type: str) -> str:
    defaults: dict[str, str] = {
        "review_promote_candidate": "Review the promoted opportunity and plan next validation step.",
        "collect_more_evidence": "Identify and collect the missing evidence types.",
        "interview_customer": "Schedule 3-5 customer discovery interviews.",
        "validate_price_signal": "Validate the price signal against real customer willingness-to-pay.",
        "revisit_parked_opportunity": "Check for new matching evidence before next review cycle.",
        "consider_kill_candidate": "Review kill rationale; record in kill archive for future pattern suppression.",
        "review_preference_warning": "Review preference profile warnings and adjust strategy if needed.",
        "run_customer_voice_queries": "Generate and run customer-voice queries for related pain types.",
        "address_evidence_gap": "Collect the specific evidence type flagged as missing.",
        "review_undecided_opportunity": "Review the opportunity and record a promote/park/kill/needs-more-evidence decision.",
    }
    return defaults.get(action_type, "Review the item and decide next action.")


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def next_best_actions_to_json(actions: list[FounderAction]) -> str:
    """Serialize a list of FounderAction items to JSON."""
    import json

    return json.dumps(
        [a.to_dict() for a in actions],
        ensure_ascii=False,
        indent=2,
    )


def render_next_best_actions_markdown(actions: list[FounderAction]) -> str:
    """Render a list of FounderAction items as Markdown."""
    lines: list[str] = []
    lines.append("# Next Best Founder Actions")
    lines.append("")
    lines.append(f"- **Total actions**: {len(actions)}")
    lines.append(f"- **Advisory only**: all actions require founder review and approval")
    lines.append("")

    if not actions:
        lines.append("_No actions to recommend. The weekly review package is empty._")
        lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    priority_labels = {
        PRIORITY_HIGH: "HIGH",
        PRIORITY_NORMAL: "NORMAL",
        PRIORITY_LOW: "LOW",
    }

    for i, action in enumerate(actions, start=1):
        pri_label = priority_labels.get(action.priority, "NORMAL")
        lines.append(f"## {i}. [{pri_label}] {action.action_type}")
        lines.append("")
        lines.append(f"- **Action ID**: `{action.action_id}`")
        lines.append(f"- **Title**: {action.title}")
        lines.append(f"- **Rationale**: {action.rationale}")
        if action.suggested_next_step:
            lines.append(f"- **Next step**: {action.suggested_next_step}")
        if action.linked_section_ids:
            lines.append(f"- **Section IDs**: {', '.join(action.linked_section_ids)}")
        if action.linked_item_ids:
            lines.append(f"- **Item IDs**: {', '.join(action.linked_item_ids)}")
        if action.linked_decision_ids:
            lines.append(f"- **Decision IDs**: {', '.join(action.linked_decision_ids)}")
        if action.linked_opportunity_ids:
            lines.append(f"- **Opportunity IDs**: {', '.join(action.linked_opportunity_ids)}")
        if action.linked_evidence_ids:
            lines.append(f"- **Evidence IDs**: {', '.join(action.linked_evidence_ids)}")
        if action.linked_pack_ids:
            lines.append(f"- **Evidence Pack IDs**: {', '.join(action.linked_pack_ids)}")
        lines.append(f"- **Advisory only**: {str(action.advisory_only).lower()}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
