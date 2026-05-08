"""Founder Inbox v2 — deterministic advisory founder-facing Markdown + JSON index.

Roadmap v2.6 item 4.1. Replaces the placeholder founder_inbox_v2 artifacts
with real, structured inbox output built from the weekly cycle pipeline.

No live LLM/API calls. No autonomous decisions. No portfolio mutations.
Advisory-only. Deterministic. Traceability-preserving.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

FOUNDER_INBOX_V2_SCHEMA_VERSION = "founder_inbox_v2.v1"
FOUNDER_INBOX_ADVISORY_NOTE = (
    "This inbox is advisory only. The system does NOT auto-promote, "
    "auto-park, auto-kill, or mutate portfolio state. "
    "All decisions remain with the founder."
)
FOUNDER_INBOX_NO_LIVE_NOTE = (
    "No live APIs or LLMs were called to produce this inbox. "
    "All data is derived from deterministic pipeline artifacts."
)

DECISION_OPTIONS = [
    "PROMOTE",
    "PARK",
    "KILL",
    "NEEDS_MORE_EVIDENCE",
    "REVISIT_LATER",
]

# ── Canonical section definitions ─────────────────────────────────────

_SECTION_DEFS: list[dict[str, Any]] = [
    {
        "section_id": "executive_summary",
        "title": "Executive Summary",
        "empty_state": "No run metadata available. The weekly cycle may have failed.",
    },
    {
        "section_id": "top_opportunities_to_review",
        "title": "Top Opportunities to Review",
        "empty_state": "No opportunities to review this cycle.",
    },
    {
        "section_id": "promote_candidates",
        "title": "Promote Candidates",
        "empty_state": "No promote candidates this cycle.",
    },
    {
        "section_id": "park_candidates",
        "title": "Park / Revisit Later Candidates",
        "empty_state": "No park candidates this cycle.",
    },
    {
        "section_id": "kill_candidates",
        "title": "Kill / Reject Candidates",
        "empty_state": "No kill candidates this cycle.",
    },
    {
        "section_id": "needs_more_evidence",
        "title": "Needs More Evidence",
        "empty_state": "No items flagged as needing more evidence.",
    },
    {
        "section_id": "revisit_queue",
        "title": "Revisit Queue / Parking Lot",
        "empty_state": "No items in the revisit queue. No parking lot matches found.",
    },
    {
        "section_id": "next_best_actions",
        "title": "Suggested Next Actions",
        "empty_state": "No suggested actions for this cycle.",
    },
    {
        "section_id": "preference_profile_warnings",
        "title": "Preference Profile Warnings",
        "empty_state": "No preference profile warnings.",
    },
    {
        "section_id": "decision_recording_commands",
        "title": "Decision Recording Commands",
        "empty_state": "No review items to record decisions against.",
    },
]

_SECTION_IDS = tuple(s["section_id"] for s in _SECTION_DEFS)


# ── Helpers ────────────────────────────────────────────────────────────


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))


def _make_review_item_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"inbox_review_{digest}"


def _truncate(text: str, max_len: int) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


# ── Models ─────────────────────────────────────────────────────────────


@dataclass
class FounderInboxReviewItem:
    """A single reviewable item in the founder inbox."""

    review_item_id: str
    section_id: str
    title: str
    summary: str
    recommended_founder_action: str
    decision_options: list[str] = field(default_factory=lambda: list(DECISION_OPTIONS))
    priority: int | None = None  # 1=high, 2=normal, 3=low
    linked_opportunity_ids: list[str] = field(default_factory=list)
    linked_evidence_pack_ids: list[str] = field(default_factory=list)
    linked_evidence_ids: list[str] = field(default_factory=list)
    linked_quality_gate_ids: list[str] = field(default_factory=list)
    linked_action_ids: list[str] = field(default_factory=list)
    linked_parking_lot_record_ids: list[str] = field(default_factory=list)
    linked_revisit_match_ids: list[str] = field(default_factory=list)
    linked_source_artifact_ids: list[str] = field(default_factory=list)
    linked_source_urls: list[str] = field(default_factory=list)
    source_section: str = ""
    advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_item_id": self.review_item_id,
            "section_id": self.section_id,
            "title": self.title,
            "summary": self.summary,
            "recommended_founder_action": self.recommended_founder_action,
            "decision_options": list(self.decision_options),
            "priority": self.priority,
            "linked_opportunity_ids": list(self.linked_opportunity_ids),
            "linked_evidence_pack_ids": list(self.linked_evidence_pack_ids),
            "linked_evidence_ids": list(self.linked_evidence_ids),
            "linked_quality_gate_ids": list(self.linked_quality_gate_ids),
            "linked_action_ids": list(self.linked_action_ids),
            "linked_parking_lot_record_ids": list(self.linked_parking_lot_record_ids),
            "linked_revisit_match_ids": list(self.linked_revisit_match_ids),
            "linked_source_artifact_ids": list(self.linked_source_artifact_ids),
            "linked_source_urls": list(self.linked_source_urls),
            "source_section": self.source_section,
            "advisory_only": self.advisory_only,
        }


@dataclass
class FounderInboxSection:
    """A section in the founder inbox."""

    section_id: str
    title: str
    items: list[FounderInboxReviewItem] = field(default_factory=list)
    empty_state: str = "No items available."

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "items": [item.to_dict() for item in self.items],
            "empty_state": self.empty_state,
        }


@dataclass
class FounderInboxV2:
    """The complete founder inbox v2 for one weekly run."""

    schema_version: str = FOUNDER_INBOX_V2_SCHEMA_VERSION
    inbox_id: str = ""
    run_id: str = ""
    generated_at: str = ""
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True
    source_manifest_path: str = ""
    markdown_path: str = ""
    sections: list[FounderInboxSection] = field(default_factory=list)
    review_items: list[FounderInboxReviewItem] = field(default_factory=list)
    review_item_count: int = 0
    traceability_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "inbox_id": self.inbox_id,
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
            "source_manifest_path": self.source_manifest_path,
            "markdown_path": self.markdown_path,
            "sections": [s.to_dict() for s in self.sections],
            "review_items": [item.to_dict() for item in self.review_items],
            "review_item_count": self.review_item_count,
            "traceability_summary": dict(self.traceability_summary),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


# ── Source URL resolution ──────────────────────────────────────────────


def _resolve_source_urls(
    *,
    linked_evidence_pack_ids: list[str],
    linked_opportunity_ids: list[str],
    linked_quality_gate_ids: list[str],
    linked_evidence_ids: list[str],
    evidence_packs: list[dict[str, Any]],
    opportunity_candidates: list[dict[str, Any]],
    gate_results: list[dict[str, Any]],
) -> list[str]:
    """Resolve source URLs for a review item from upstream artifacts.

    Resolution order:
    1. Evidence packs matching linked_evidence_pack_ids → their source_urls
    2. Opportunity candidates matching linked_opportunity_ids → their source_urls
    3. Quality gate results matching linked_quality_gate_ids → their source_urls
    4. Evidence packs matching linked_evidence_ids via items[].evidence_id → pack source_urls

    Returns deduplicated, deterministically sorted list of non-empty http/https URLs.
    No placeholder URNs are created. Empty list if no upstream URLs exist.
    """
    urls: list[str] = []
    seen: set[str] = set()
    pack_by_id: dict[str, dict[str, Any]] = {}
    opp_by_id: dict[str, dict[str, Any]] = {}
    gate_by_id: dict[str, dict[str, Any]] = {}

    for p in evidence_packs:
        if isinstance(p, dict):
            pid = str(p.get("evidence_pack_id", ""))
            if pid:
                pack_by_id[pid] = p
    for o in opportunity_candidates:
        if isinstance(o, dict):
            oid = str(o.get("opportunity_id", o.get("id", "")))
            if oid:
                opp_by_id[oid] = o
    for g in gate_results:
        if isinstance(g, dict):
            gid = str(g.get("gate_result_id", ""))
            if gid:
                gate_by_id[gid] = g

    def _collect(pack: dict[str, Any]) -> None:
        for u in pack.get("source_urls", []):
            u_str = str(u).strip() if isinstance(u, str) else ""
            if u_str and u_str.startswith(("http://", "https://")) and u_str not in seen:
                urls.append(u_str)
                seen.add(u_str)

    # 1. Evidence packs by linked pack IDs
    for pack_id in linked_evidence_pack_ids:
        pack = pack_by_id.get(pack_id)
        if pack:
            _collect(pack)

    # 2. Opportunity candidates by linked opp IDs
    for opp_id in linked_opportunity_ids:
        opp = opp_by_id.get(opp_id)
        if opp:
            _collect(opp)

    # 3. Quality gate results by linked gate IDs
    for gate_id in linked_quality_gate_ids:
        gate = gate_by_id.get(gate_id)
        if gate:
            _collect(gate)

    # 4. Evidence packs that contain linked evidence IDs in their items
    for ev_id in linked_evidence_ids:
        for pack in evidence_packs:
            if not isinstance(pack, dict):
                continue
            items = pack.get("items", [])
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and str(item.get("evidence_id", "")) == ev_id:
                    _collect(pack)
                    break

    return sorted(urls)


def _post_process_source_urls(
    all_items: list[FounderInboxReviewItem],
    packs: list[dict[str, Any]],
    opps: list[dict[str, Any]],
    gates: list[dict[str, Any]],
) -> None:
    """Resolve and populate linked_source_urls for every review item in place."""
    for item in all_items:
        item.linked_source_urls = _resolve_source_urls(
            linked_evidence_pack_ids=item.linked_evidence_pack_ids,
            linked_opportunity_ids=item.linked_opportunity_ids,
            linked_quality_gate_ids=item.linked_quality_gate_ids,
            linked_evidence_ids=item.linked_evidence_ids,
            evidence_packs=packs,
            opportunity_candidates=opps,
            gate_results=gates,
        )


# ── Builder ────────────────────────────────────────────────────────────


def build_founder_inbox_v2(
    *,
    run_id: str,
    manifest_path: str,
    generated_at: str,
    review_package: dict[str, Any] | None = None,
    actions: list[dict[str, Any]] | None = None,
    gate_results: list[dict[str, Any]] | None = None,
    evidence_packs: list[dict[str, Any]] | None = None,
    opportunity_candidates: list[dict[str, Any]] | None = None,
    revisit_matches: list[dict[str, Any]] | None = None,
    parking_lot_records: list[dict[str, Any]] | None = None,
    marks_path: str = "founder_inbox_v2.md",
    index_path: str = "founder_inbox_v2_index.json",
) -> FounderInboxV2:
    """Build a deterministic FounderInboxV2 from weekly cycle pipeline outputs.

    All inputs are optional. When absent, sections render with clear empty states.
    No live LLM/API calls. No autonomous decisions. Advisory-only.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # ── Normalize inputs ────────────────────────────────────────────
    rp = review_package or {}
    acts = list(actions or [])
    gates = list(gate_results or [])
    packs = list(evidence_packs or [])
    opps = list(opportunity_candidates or [])
    rmatches = list(revisit_matches or [])
    pl_records = list(parking_lot_records or [])

    rp_sections: list[dict[str, Any]] = rp.get("sections", [])
    decision_summary: dict[str, Any] = rp.get("decision_summary", {})

    # ── Build inbox_id ──────────────────────────────────────────────
    inbox_id_seed = run_id
    inbox_digest = hashlib.sha256(inbox_id_seed.encode("utf-8")).hexdigest()[:12]
    inbox_id = f"founder_inbox_v2_{inbox_digest}"

    # ── Build sections ──────────────────────────────────────────────
    sections: list[FounderInboxSection] = []
    all_items: list[FounderInboxReviewItem] = []

    # Section 1: Executive Summary
    exec_items, exec_warnings = _build_executive_summary(
        run_id=run_id,
        generated_at=generated_at,
        rp=rp,
        acts=acts,
        gates=gates,
        packs=packs,
        opps=opps,
        rmatches=rmatches,
        pl_records=pl_records,
    )
    all_items.extend(exec_items)
    sections.append(
        FounderInboxSection(
            section_id="executive_summary",
            title="Executive Summary",
            items=exec_items,
            empty_state="No run metadata available. The weekly cycle may have failed.",
        )
    )
    warnings.extend(exec_warnings)

    # Section 2: Top Opportunities to Review
    top_items = _build_top_opportunities(rp_sections, gates, opps, packs)
    all_items.extend(top_items)
    sections.append(
        FounderInboxSection(
            section_id="top_opportunities_to_review",
            title="Top Opportunities to Review",
            items=top_items,
            empty_state="No opportunities to review this cycle.",
        )
    )

    # Section 3: Promote Candidates
    promote_items = _build_promote_candidates(rp_sections, gates)
    all_items.extend(promote_items)
    sections.append(
        FounderInboxSection(
            section_id="promote_candidates",
            title="Promote Candidates",
            items=promote_items,
            empty_state="No promote candidates this cycle.",
        )
    )

    # Section 4: Park Candidates
    park_items = _build_park_candidates(rp_sections, gates, pl_records)
    all_items.extend(park_items)
    sections.append(
        FounderInboxSection(
            section_id="park_candidates",
            title="Park / Revisit Later Candidates",
            items=park_items,
            empty_state="No park candidates this cycle.",
        )
    )

    # Section 5: Kill Candidates
    kill_items = _build_kill_candidates(rp_sections, gates)
    all_items.extend(kill_items)
    sections.append(
        FounderInboxSection(
            section_id="kill_candidates",
            title="Kill / Reject Candidates",
            items=kill_items,
            empty_state="No kill candidates this cycle.",
        )
    )

    # Section 6: Needs More Evidence
    nme_items = _build_needs_more_evidence(rp_sections, gates)
    all_items.extend(nme_items)
    sections.append(
        FounderInboxSection(
            section_id="needs_more_evidence",
            title="Needs More Evidence",
            items=nme_items,
            empty_state="No items flagged as needing more evidence.",
        )
    )

    # Section 7: Revisit Queue
    revisit_items = _build_revisit_queue(rp_sections, rmatches)
    all_items.extend(revisit_items)
    sections.append(
        FounderInboxSection(
            section_id="revisit_queue",
            title="Revisit Queue / Parking Lot",
            items=revisit_items,
            empty_state="No items in the revisit queue. No parking lot matches found.",
        )
    )

    # Section 8: Next Best Actions
    action_items = _build_next_best_actions(acts)
    all_items.extend(action_items)
    sections.append(
        FounderInboxSection(
            section_id="next_best_actions",
            title="Suggested Next Actions",
            items=action_items,
            empty_state="No suggested actions for this cycle.",
        )
    )

    # Section 9: Preference Profile Warnings
    pref_items = _build_preference_warnings(rp_sections)
    all_items.extend(pref_items)
    sections.append(
        FounderInboxSection(
            section_id="preference_profile_warnings",
            title="Preference Profile Warnings",
            items=pref_items,
            empty_state="No preference profile warnings.",
        )
    )

    # Section 10: Decision Recording Commands
    cmd_items = _build_decision_recording_commands(all_items)
    all_items.extend(cmd_items)
    sections.append(
        FounderInboxSection(
            section_id="decision_recording_commands",
            title="Decision Recording Commands",
            items=cmd_items,
            empty_state="No review items to record decisions against.",
        )
    )

    # ── Post-process source URLs for all review items ──────────────
    _post_process_source_urls(
        all_items=all_items,
        packs=packs,
        opps=opps,
        gates=gates,
    )

    # ── Build traceability summary ──────────────────────────────────
    traceability = _build_traceability_summary(all_items, gates, packs, acts, rmatches, pl_records)

    # ── Assemble inbox ──────────────────────────────────────────────
    return FounderInboxV2(
        schema_version=FOUNDER_INBOX_V2_SCHEMA_VERSION,
        inbox_id=inbox_id,
        run_id=run_id,
        generated_at=generated_at,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
        source_manifest_path=manifest_path,
        markdown_path=marks_path,
        sections=sections,
        review_items=all_items,
        review_item_count=len(all_items),
        traceability_summary=traceability,
        warnings=warnings,
        errors=errors,
    )


# ── Section builders ───────────────────────────────────────────────────


def _build_executive_summary(
    *,
    run_id: str,
    generated_at: str,
    rp: dict[str, Any],
    acts: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    packs: list[dict[str, Any]],
    opps: list[dict[str, Any]],
    rmatches: list[dict[str, Any]],
    pl_records: list[dict[str, Any]],
) -> tuple[list[FounderInboxReviewItem], list[str]]:
    """Build executive summary review item."""
    items: list[FounderInboxReviewItem] = []
    warnings: list[str] = []

    pass_count = sum(1 for g in gates if isinstance(g, dict) and g.get("decision") == "pass")
    park_count = sum(1 for g in gates if isinstance(g, dict) and g.get("decision") == "park")
    reject_count = sum(1 for g in gates if isinstance(g, dict) and g.get("decision") == "reject")
    signal_count = 0
    for p in packs:
        signal_count += len(p.get("source_signal_ids", []))

    summary_lines = [
        f"Weekly run {run_id} generated at {generated_at}.",
        f"Evidence packs: {len(packs)}",
        f"Opportunity candidates: {len(opps)}",
        f"Quality gate: {pass_count} pass, {park_count} park, {reject_count} reject",
        f"Founder actions suggested: {len(acts)}",
        f"Revisit matches: {len(rmatches)}",
        f"Parking lot records: {len(pl_records)}",
        "This inbox is ADVISORY ONLY. All decisions remain with the founder.",
        "No live APIs or LLMs were called.",
    ]

    item = FounderInboxReviewItem(
        review_item_id=_make_review_item_id(f"exec|{run_id}"),
        section_id="executive_summary",
        title=f"Weekly Run {run_id}",
        summary=" ".join(summary_lines),
        recommended_founder_action="Review this inbox. Record decisions for each review item.",
        decision_options=[],
        priority=None,
        linked_evidence_pack_ids=_ordered_strings(p.get("evidence_pack_id", "") for p in packs),
        linked_opportunity_ids=_ordered_strings(o.get("opportunity_id", o.get("id", "")) for o in opps),
        linked_source_artifact_ids=[run_id],
        source_section="executive_summary",
        advisory_only=True,
    )
    items.append(item)
    return items, warnings


def _build_top_opportunities(
    rp_sections: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    opps: list[dict[str, Any]],
    packs: list[dict[str, Any]],
) -> list[FounderInboxReviewItem]:
    """Build top-opportunities review items from quality gate results and review package."""
    items: list[FounderInboxReviewItem] = []

    # First, look for the "top_opportunities_to_review" section in the review package
    for section in rp_sections:
        if not isinstance(section, dict):
            continue
        if section.get("section_id") != "top_opportunities_to_review":
            continue
        for rp_item in section.get("items", []):
            if not isinstance(rp_item, dict):
                continue
            item_id = str(rp_item.get("item_id", ""))
            summary = str(rp_item.get("summary", ""))
            action_hint = str(rp_item.get("action_hint", ""))
            urgency = str(rp_item.get("urgency", "normal"))
            priority_map = {"high": 1, "normal": 2, "low": 3}
            priority = priority_map.get(urgency, 2)

            linked_opp_ids = _ordered_strings(rp_item.get("linked_opportunity_ids", []))
            linked_ev_ids = _ordered_strings(rp_item.get("linked_evidence_ids", []))
            linked_pack_ids = _ordered_strings(rp_item.get("linked_pack_ids", []))
            linked_dec_ids = _ordered_strings(rp_item.get("linked_decision_ids", []))

            seed = f"top|{item_id}|{';'.join(linked_opp_ids)}"
            review_item_id = _make_review_item_id(seed)

            # Match quality gate results for this opportunity
            linked_gate_ids: list[str] = []
            for g in gates:
                if not isinstance(g, dict):
                    continue
                g_opp_id = str(g.get("opportunity_id", ""))
                if g_opp_id and g_opp_id in linked_opp_ids:
                    linked_gate_ids.append(str(g.get("gate_result_id", "")))

            items.append(
                FounderInboxReviewItem(
                    review_item_id=review_item_id,
                    section_id="top_opportunities_to_review",
                    title=_truncate(summary, 150),
                    summary=summary,
                    recommended_founder_action=action_hint or "Review and decide: PROMOTE, PARK, KILL, or NEEDS_MORE_EVIDENCE.",
                    priority=priority,
                    linked_opportunity_ids=linked_opp_ids,
                    linked_evidence_pack_ids=linked_pack_ids,
                    linked_evidence_ids=linked_ev_ids,
                    linked_quality_gate_ids=_ordered_strings(linked_gate_ids),
                    linked_source_artifact_ids=linked_dec_ids,
                    source_section="top_opportunities_to_review",
                    advisory_only=True,
                )
            )
        break  # only process the first matching section

    # Also add quality-gate-pass candidates not already covered
    covered_opp_ids = set()
    for item in items:
        covered_opp_ids.update(item.linked_opportunity_ids)

    for g in gates:
        if not isinstance(g, dict):
            continue
        opp_id = str(g.get("opportunity_id", ""))
        if opp_id and opp_id not in covered_opp_ids and g.get("decision") == "pass":
            covered_opp_ids.add(opp_id)
            seed = f"top|gate|{opp_id}"
            review_item_id = _make_review_item_id(seed)
            gid = str(g.get("gate_result_id", ""))
            items.append(
                FounderInboxReviewItem(
                    review_item_id=review_item_id,
                    section_id="top_opportunities_to_review",
                    title=f"Quality-gate PASS: {opp_id}",
                    summary=f"Opportunity {opp_id} passed the quality gate (confidence={g.get('confidence', 0):.3f}). Founder review required.",
                    recommended_founder_action="Review and decide: PROMOTE, PARK, KILL, or NEEDS_MORE_EVIDENCE.",
                    priority=2,
                    linked_opportunity_ids=[opp_id],
                    linked_evidence_pack_ids=_ordered_strings([g.get("evidence_pack_id", "")]),
                    linked_evidence_ids=_ordered_strings(g.get("evidence_ids", [])),
                    linked_quality_gate_ids=_ordered_strings([gid]),
                    source_section="top_opportunities_to_review",
                    advisory_only=True,
                )
            )

    return items


def _build_promote_candidates(
    rp_sections: list[dict[str, Any]],
    gates: list[dict[str, Any]],
) -> list[FounderInboxReviewItem]:
    """Build promote-candidate review items."""
    return _extract_from_rp_section(rp_sections, "promote_candidates", gates)


def _build_park_candidates(
    rp_sections: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    pl_records: list[dict[str, Any]],
) -> list[FounderInboxReviewItem]:
    """Build park-candidate review items."""
    items = _extract_from_rp_section(rp_sections, "park_candidates", gates)

    # Also include parking lot records as advisory items
    for pl in pl_records:
        if not isinstance(pl, dict):
            continue
        record_id = str(pl.get("record_id", ""))
        opp_id = str(pl.get("linked_opportunity_id", ""))
        summary = str(pl.get("summary", ""))
        reason = str(pl.get("reason", ""))
        status = str(pl.get("status", "parked"))

        seed = f"park|pl|{record_id}"
        review_item_id = _make_review_item_id(seed)

        items.append(
            FounderInboxReviewItem(
                review_item_id=review_item_id,
                section_id="park_candidates",
                title=f"[{status}] {opp_id}",
                summary=f"{summary} (Reason: {reason})",
                recommended_founder_action="Keep parked. Revisit when new evidence or signals appear.",
                priority=3,
                linked_opportunity_ids=_ordered_strings([opp_id]),
                linked_parking_lot_record_ids=[record_id],
                linked_source_artifact_ids=_ordered_strings(pl.get("source_artifact_ids", [])),
                source_section="park_candidates",
                advisory_only=True,
            )
        )

    return items


def _build_kill_candidates(
    rp_sections: list[dict[str, Any]],
    gates: list[dict[str, Any]],
) -> list[FounderInboxReviewItem]:
    """Build kill-candidate review items."""
    items = _extract_from_rp_section(rp_sections, "kill_candidates", gates)

    # Also include quality-gate-reject candidates
    covered_opp_ids = set()
    for item in items:
        covered_opp_ids.update(item.linked_opportunity_ids)

    for g in gates:
        if not isinstance(g, dict):
            continue
        opp_id = str(g.get("opportunity_id", ""))
        if opp_id and opp_id not in covered_opp_ids and g.get("decision") == "reject":
            covered_opp_ids.add(opp_id)
            seed = f"kill|gate|{opp_id}"
            review_item_id = _make_review_item_id(seed)
            gid = str(g.get("gate_result_id", ""))
            blocking = g.get("blocking_issues", [])
            reasons_str = ", ".join(
                r.get("message", r.get("code", "")) for r in g.get("reasons", [])
                if r.get("severity") in ("fatal", "high")
            )
            items.append(
                FounderInboxReviewItem(
                    review_item_id=review_item_id,
                    section_id="kill_candidates",
                    title=f"Quality-gate REJECT: {opp_id}",
                    summary=f"Opportunity {opp_id} was rejected: {reasons_str}. Blocking issues: {', '.join(blocking) if blocking else 'none'}.",
                    recommended_founder_action="Record kill reason. Do not re-surface in future cycles.",
                    priority=2,
                    linked_opportunity_ids=[opp_id],
                    linked_evidence_pack_ids=_ordered_strings([g.get("evidence_pack_id", "")]),
                    linked_evidence_ids=_ordered_strings(g.get("evidence_ids", [])),
                    linked_quality_gate_ids=_ordered_strings([gid]),
                    source_section="kill_candidates",
                    advisory_only=True,
                )
            )

    return items


def _build_needs_more_evidence(
    rp_sections: list[dict[str, Any]],
    gates: list[dict[str, Any]],
) -> list[FounderInboxReviewItem]:
    """Build needs-more-evidence review items."""
    items = _extract_from_rp_section(rp_sections, "needs_more_evidence", gates)

    # Also include quality-gate-park with missing evidence
    covered_opp_ids = set()
    for item in items:
        covered_opp_ids.update(item.linked_opportunity_ids)

    for g in gates:
        if not isinstance(g, dict):
            continue
        opp_id = str(g.get("opportunity_id", ""))
        if opp_id and opp_id not in covered_opp_ids and g.get("decision") == "park":
            missing = g.get("missing_evidence", [])
            if missing:
                covered_opp_ids.add(opp_id)
                seed = f"nme|gate|{opp_id}"
                review_item_id = _make_review_item_id(seed)
                gid = str(g.get("gate_result_id", ""))
                items.append(
                    FounderInboxReviewItem(
                        review_item_id=review_item_id,
                        section_id="needs_more_evidence",
                        title=f"Insufficient evidence: {opp_id}",
                        summary=f"Opportunity {opp_id} was parked due to missing: {', '.join(missing)}.",
                        recommended_founder_action="Collect the missing evidence types before the next review cycle.",
                        priority=2,
                        linked_opportunity_ids=[opp_id],
                        linked_evidence_pack_ids=_ordered_strings([g.get("evidence_pack_id", "")]),
                        linked_evidence_ids=_ordered_strings(g.get("evidence_ids", [])),
                        linked_quality_gate_ids=_ordered_strings([gid]),
                        source_section="needs_more_evidence",
                        advisory_only=True,
                    )
                )

    return items


def _build_revisit_queue(
    rp_sections: list[dict[str, Any]],
    rmatches: list[dict[str, Any]],
) -> list[FounderInboxReviewItem]:
    """Build revisit-queue review items from review package and revisit matches."""
    items: list[FounderInboxReviewItem] = []

    # Extract from review package's revisit_queue section
    for section in rp_sections:
        if not isinstance(section, dict):
            continue
        if section.get("section_id") != "revisit_queue":
            continue
        for rp_item in section.get("items", []):
            if not isinstance(rp_item, dict):
                continue
            item_id = str(rp_item.get("item_id", ""))
            summary = str(rp_item.get("summary", ""))
            action_hint = str(rp_item.get("action_hint", ""))
            urgency = str(rp_item.get("urgency", "normal"))
            priority_map = {"high": 1, "normal": 2, "low": 3}
            priority = priority_map.get(urgency, 2)
            linked_opp_ids = _ordered_strings(rp_item.get("linked_opportunity_ids", []))
            linked_ev_ids = _ordered_strings(rp_item.get("linked_evidence_ids", []))
            linked_pack_ids = _ordered_strings(rp_item.get("linked_pack_ids", []))
            linked_dec_ids = _ordered_strings(rp_item.get("linked_decision_ids", []))

            seed = f"revisit|{item_id}|{';'.join(linked_opp_ids)}"
            review_item_id = _make_review_item_id(seed)

            items.append(
                FounderInboxReviewItem(
                    review_item_id=review_item_id,
                    section_id="revisit_queue",
                    title=_truncate(summary, 150),
                    summary=summary,
                    recommended_founder_action=action_hint or "Check for new matching evidence before next review cycle.",
                    priority=priority,
                    linked_opportunity_ids=linked_opp_ids,
                    linked_evidence_pack_ids=linked_pack_ids,
                    linked_evidence_ids=linked_ev_ids,
                    linked_source_artifact_ids=linked_dec_ids,
                    source_section="revisit_queue",
                    advisory_only=True,
                )
            )
        break

    # Add direct revisit matches
    for m in rmatches:
        if not isinstance(m, dict):
            continue
        match_id = str(m.get("match_id", ""))
        pl_id = str(m.get("parking_lot_record_id", ""))
        opp_id = str(m.get("matched_opportunity_id", ""))
        reason = str(m.get("match_reason", ""))
        confidence = str(m.get("confidence", "low"))
        priority_map = {"high": 1, "medium": 2, "low": 3}
        priority = priority_map.get(confidence, 3)
        suggested = str(m.get("suggested_founder_action", ""))

        seed = f"revisit|match|{match_id}"
        review_item_id = _make_review_item_id(seed)

        items.append(
            FounderInboxReviewItem(
                review_item_id=review_item_id,
                section_id="revisit_queue",
                title=f"[{confidence.upper()} MATCH] {match_id}",
                summary=f"Parking lot record {pl_id} matched new evidence: {reason}. Opportunity: {opp_id or 'unknown'}.",
                recommended_founder_action=suggested or "Review parked opportunity for possible revisit.",
                priority=priority,
                linked_opportunity_ids=_ordered_strings([opp_id]),
                linked_parking_lot_record_ids=[pl_id],
                linked_revisit_match_ids=[match_id],
                source_section="revisit_queue",
                advisory_only=True,
            )
        )

    return items


def _build_next_best_actions(
    acts: list[dict[str, Any]],
) -> list[FounderInboxReviewItem]:
    """Build next-best-actions review items."""
    items: list[FounderInboxReviewItem] = []
    for a in acts:
        if not isinstance(a, dict):
            continue
        action_id = str(a.get("action_id", ""))
        action_type = str(a.get("action_type", ""))
        title = str(a.get("title", ""))
        rationale = str(a.get("rationale", ""))
        next_step = str(a.get("suggested_next_step", ""))
        priority = a.get("priority", 2)
        if not isinstance(priority, int):
            priority = 2
        linked_opp_ids = _ordered_strings(a.get("linked_opportunity_ids", []))
        linked_ev_ids = _ordered_strings(a.get("linked_evidence_ids", []))
        linked_pack_ids = _ordered_strings(a.get("linked_pack_ids", []))
        linked_dec_ids = _ordered_strings(a.get("linked_decision_ids", []))
        linked_item_ids = _ordered_strings(a.get("linked_item_ids", []))

        seed = f"action|{action_id}"
        review_item_id = _make_review_item_id(seed)

        items.append(
            FounderInboxReviewItem(
                review_item_id=review_item_id,
                section_id="next_best_actions",
                title=f"[{priority_label(priority)}] {action_type}: {title}",
                summary=f"{rationale} Next step: {next_step}",
                recommended_founder_action=next_step or "Review and execute this action.",
                priority=priority,
                linked_opportunity_ids=linked_opp_ids,
                linked_evidence_pack_ids=linked_pack_ids,
                linked_evidence_ids=linked_ev_ids,
                linked_action_ids=[action_id],
                linked_source_artifact_ids=linked_dec_ids + linked_item_ids,
                source_section="next_best_actions",
                advisory_only=True,
            )
        )

    return items


def _build_preference_warnings(
    rp_sections: list[dict[str, Any]],
) -> list[FounderInboxReviewItem]:
    """Build preference-profile-warnings review items."""
    items: list[FounderInboxReviewItem] = []
    for section in rp_sections:
        if not isinstance(section, dict):
            continue
        if section.get("section_id") != "preference_profile_warnings":
            continue
        for rp_item in section.get("items", []):
            if not isinstance(rp_item, dict):
                continue
            item_id = str(rp_item.get("item_id", ""))
            summary = str(rp_item.get("summary", ""))
            action_hint = str(rp_item.get("action_hint", ""))
            linked_dec_ids = _ordered_strings(rp_item.get("linked_decision_ids", []))

            seed = f"pref|{item_id}"
            review_item_id = _make_review_item_id(seed)

            items.append(
                FounderInboxReviewItem(
                    review_item_id=review_item_id,
                    section_id="preference_profile_warnings",
                    title=item_id,
                    summary=summary,
                    recommended_founder_action=action_hint or "Review preference warning and adjust strategy if needed.",
                    priority=2,
                    linked_source_artifact_ids=linked_dec_ids,
                    source_section="preference_profile_warnings",
                    advisory_only=True,
                )
            )
        break
    return items


def _build_decision_recording_commands(
    all_review_items: list[FounderInboxReviewItem],
) -> list[FounderInboxReviewItem]:
    """Build decision-recording-commands section items.

    Creates one item with copy-paste-able PowerShell commands for each review item
    that has decision options.
    """
    items: list[FounderInboxReviewItem] = []
    actionable = [ri for ri in all_review_items if ri.decision_options and ri.section_id != "decision_recording_commands"]

    if not actionable:
        return items

    commands: list[str] = []
    commands.append("# PowerShell decision recording commands")
    commands.append("# Copy the relevant lines below, edit the decision value, and run.")
    commands.append("")

    for ri in actionable:
        decision_opt_str = "|".join(ri.decision_options) if ri.decision_options else "PROMOTE|PARK|KILL|NEEDS_MORE_EVIDENCE|REVISIT_LATER"
        cmd = (
            f"# {ri.title}\n"
            f"echo '{{\"review_item_id\": \"{ri.review_item_id}\", "
            f"\"decision\": \"<{decision_opt_str}>\", "
            f"\"reason\": \"<your reason here>\", "
            f"\"note\": \"\"}}' "
            f">> decisions_file.json"
        )
        commands.append(cmd)
        commands.append("")

    cmd_text = "\n".join(commands)

    seed = "decision_cmds"
    review_item_id = _make_review_item_id(seed)

    items.append(
        FounderInboxReviewItem(
            review_item_id=review_item_id,
            section_id="decision_recording_commands",
            title="Decision Recording Commands",
            summary=(
                f"Use the PowerShell commands below to record your founder decisions. "
                f"Edit the decision value and reason, then save as a decisions file "
                f"for import via `import-founder-decisions` (v2.6 item 5.1).\n\n{cmd_text}"
            ),
            recommended_founder_action="Review all items above, record decisions, and import them.",
            decision_options=[],
            priority=None,
            source_section="decision_recording_commands",
            advisory_only=True,
        )
    )

    return items


def _extract_from_rp_section(
    rp_sections: list[dict[str, Any]],
    target_section_id: str,
    gates: list[dict[str, Any]],
) -> list[FounderInboxReviewItem]:
    """Extract review items from a review-package section by section_id."""
    items: list[FounderInboxReviewItem] = []
    for section in rp_sections:
        if not isinstance(section, dict):
            continue
        if section.get("section_id") != target_section_id:
            continue
        for rp_item in section.get("items", []):
            if not isinstance(rp_item, dict):
                continue
            item_id = str(rp_item.get("item_id", ""))
            summary = str(rp_item.get("summary", ""))
            action_hint = str(rp_item.get("action_hint", ""))
            urgency = str(rp_item.get("urgency", "normal"))
            priority_map = {"high": 1, "normal": 2, "low": 3}
            priority = priority_map.get(urgency, 2)
            linked_opp_ids = _ordered_strings(rp_item.get("linked_opportunity_ids", []))
            linked_ev_ids = _ordered_strings(rp_item.get("linked_evidence_ids", []))
            linked_pack_ids = _ordered_strings(rp_item.get("linked_pack_ids", []))
            linked_dec_ids = _ordered_strings(rp_item.get("linked_decision_ids", []))
            linked_map_ids = _ordered_strings(rp_item.get("linked_feedback_mapping_ids", []))

            seed = f"{target_section_id}|{item_id}|{';'.join(linked_opp_ids)}"
            review_item_id = _make_review_item_id(seed)

            # Match quality gate results
            linked_gate_ids: list[str] = []
            for g in gates:
                if not isinstance(g, dict):
                    continue
                g_opp_id = str(g.get("opportunity_id", ""))
                if g_opp_id and g_opp_id in linked_opp_ids:
                    linked_gate_ids.append(str(g.get("gate_result_id", "")))

            items.append(
                FounderInboxReviewItem(
                    review_item_id=review_item_id,
                    section_id=target_section_id,
                    title=_truncate(summary, 150),
                    summary=summary,
                    recommended_founder_action=action_hint or "Review and decide.",
                    priority=priority,
                    linked_opportunity_ids=linked_opp_ids,
                    linked_evidence_pack_ids=linked_pack_ids,
                    linked_evidence_ids=linked_ev_ids,
                    linked_quality_gate_ids=_ordered_strings(linked_gate_ids),
                    linked_source_artifact_ids=linked_dec_ids + linked_map_ids,
                    source_section=target_section_id,
                    advisory_only=True,
                )
            )
        break
    return items


def _build_traceability_summary(
    all_items: list[FounderInboxReviewItem],
    gates: list[dict[str, Any]],
    packs: list[dict[str, Any]],
    acts: list[dict[str, Any]],
    rmatches: list[dict[str, Any]],
    pl_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a traceability summary from all inbox review items."""
    all_opp_ids: set[str] = set()
    all_ev_ids: set[str] = set()
    all_pack_ids: set[str] = set()
    all_gate_ids: set[str] = set()
    all_action_ids: set[str] = set()
    all_pl_ids: set[str] = set()
    all_match_ids: set[str] = set()
    all_artifact_ids: set[str] = set()
    all_source_urls: set[str] = set()
    items_with_source_urls: int = 0
    items_without_source_urls: int = 0

    for item in all_items:
        all_opp_ids.update(item.linked_opportunity_ids)
        all_ev_ids.update(item.linked_evidence_ids)
        all_pack_ids.update(item.linked_evidence_pack_ids)
        all_gate_ids.update(item.linked_quality_gate_ids)
        all_action_ids.update(item.linked_action_ids)
        all_pl_ids.update(item.linked_parking_lot_record_ids)
        all_match_ids.update(item.linked_revisit_match_ids)
        all_artifact_ids.update(item.linked_source_artifact_ids)
        all_source_urls.update(item.linked_source_urls)
        if item.linked_source_urls:
            items_with_source_urls += 1
        else:
            items_without_source_urls += 1

    return {
        "unique_opportunity_ids": len(all_opp_ids),
        "unique_evidence_ids": len(all_ev_ids),
        "unique_evidence_pack_ids": len(all_pack_ids),
        "unique_quality_gate_ids": len(all_gate_ids),
        "unique_action_ids": len(all_action_ids),
        "unique_parking_lot_record_ids": len(all_pl_ids),
        "unique_revisit_match_ids": len(all_match_ids),
        "unique_source_artifact_ids": len(all_artifact_ids),
        "unique_source_urls": len(all_source_urls),
        "items_with_source_urls": items_with_source_urls,
        "items_without_source_urls": items_without_source_urls,
        "review_item_count": len(all_items),
    }


def priority_label(priority: int) -> str:
    labels = {1: "HIGH", 2: "NORMAL", 3: "LOW"}
    return labels.get(priority, "NORMAL")


# ── Markdown renderer ──────────────────────────────────────────────────


def render_founder_inbox_v2_markdown(inbox: FounderInboxV2) -> str:
    """Render a FounderInboxV2 to a deterministic Markdown string."""
    lines: list[str] = []
    lines.append("# Founder Inbox v2")
    lines.append("")
    lines.append(f"- **Inbox ID**: `{inbox.inbox_id}`")
    lines.append(f"- **Run ID**: `{inbox.run_id}`")
    lines.append(f"- **Generated**: {inbox.generated_at}")
    lines.append(f"- **Schema**: {inbox.schema_version}")
    lines.append("")
    lines.append("## Advisory-Only Notice")
    lines.append("")
    lines.append(f"> {FOUNDER_INBOX_ADVISORY_NOTE}")
    lines.append("")
    lines.append(f"> {FOUNDER_INBOX_NO_LIVE_NOTE}")
    lines.append("")
    lines.append("## How to Use This Inbox")
    lines.append("")
    lines.append("1. Read the Executive Summary for an overview of this weekly run.")
    lines.append("2. Review each section below — every section has explicit empty states when no items exist.")
    lines.append("3. For each review item, the inbox provides:")
    lines.append("   - A title, summary, and recommended action.")
    lines.append("   - Decision options: PROMOTE, PARK, KILL, NEEDS_MORE_EVIDENCE, REVISIT_LATER.")
    lines.append("4. Record your decisions using the commands in Section 10.")
    lines.append("5. Import your decisions back into the system via `import-founder-decisions` (v2.6 item 5.1).")
    lines.append("")
    lines.append("---")
    lines.append("")

    if inbox.warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in inbox.warnings:
            lines.append(f"- ⚠ {w}")
        lines.append("")

    if inbox.errors:
        lines.append("## Errors")
        lines.append("")
        for e in inbox.errors:
            lines.append(f"- ❌ {e}")
        lines.append("")

    for section in inbox.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        if not section.items:
            lines.append(f"*{section.empty_state}*")
            lines.append("")
            continue

        for item in section.items:
            pri_str = f" [{priority_label(item.priority)}]" if item.priority is not None else ""
            lines.append(f"### `{item.review_item_id}`{pri_str}")
            lines.append("")
            lines.append(f"- **Title**: {item.title}")
            lines.append(f"- **Summary**: {item.summary}")
            if item.recommended_founder_action:
                lines.append(f"- **Recommended Action**: {item.recommended_founder_action}")
            if item.decision_options:
                lines.append(f"- **Decision Options**: {', '.join(item.decision_options)}")
            if item.linked_opportunity_ids:
                lines.append(f"- **Opportunity IDs**: {', '.join(item.linked_opportunity_ids)}")
            if item.linked_evidence_pack_ids:
                lines.append(f"- **Evidence Pack IDs**: {', '.join(item.linked_evidence_pack_ids)}")
            if item.linked_evidence_ids:
                lines.append(f"- **Evidence IDs**: {', '.join(item.linked_evidence_ids)}")
            if item.linked_quality_gate_ids:
                lines.append(f"- **Quality Gate IDs**: {', '.join(item.linked_quality_gate_ids)}")
            if item.linked_action_ids:
                lines.append(f"- **Action IDs**: {', '.join(item.linked_action_ids)}")
            if item.linked_parking_lot_record_ids:
                lines.append(f"- **Parking Lot Record IDs**: {', '.join(item.linked_parking_lot_record_ids)}")
            if item.linked_revisit_match_ids:
                lines.append(f"- **Revisit Match IDs**: {', '.join(item.linked_revisit_match_ids)}")
            if item.linked_source_urls:
                lines.append(f"- **Source URLs**: {', '.join(item.linked_source_urls)}")
            lines.append(f"- **Advisory Only**: {str(item.advisory_only).lower()}")
            lines.append("")

    # Traceability appendix
    lines.append("## Traceability Appendix")
    lines.append("")
    ts = inbox.traceability_summary
    lines.append(f"- **Review Items**: {ts.get('review_item_count', 0)}")
    lines.append(f"- **Items With Source URLs**: {ts.get('items_with_source_urls', 0)}")
    lines.append(f"- **Items Without Source URLs**: {ts.get('items_without_source_urls', 0)}")
    lines.append(f"- **Unique Source URLs**: {ts.get('unique_source_urls', 0)}")
    lines.append(f"- **Unique Opportunity IDs**: {ts.get('unique_opportunity_ids', 0)}")
    lines.append(f"- **Unique Evidence IDs**: {ts.get('unique_evidence_ids', 0)}")
    lines.append(f"- **Unique Evidence Pack IDs**: {ts.get('unique_evidence_pack_ids', 0)}")
    lines.append(f"- **Unique Quality Gate IDs**: {ts.get('unique_quality_gate_ids', 0)}")
    lines.append(f"- **Unique Action IDs**: {ts.get('unique_action_ids', 0)}")
    lines.append(f"- **Unique Parking Lot Record IDs**: {ts.get('unique_parking_lot_record_ids', 0)}")
    lines.append(f"- **Unique Revisit Match IDs**: {ts.get('unique_revisit_match_ids', 0)}")
    lines.append(f"- **Unique Source Artifact IDs**: {ts.get('unique_source_artifact_ids', 0)}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Founder decision required for all items. No autonomous portfolio transitions.*")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ── JSON serialization ─────────────────────────────────────────────────


def founder_inbox_v2_to_json(inbox: FounderInboxV2) -> dict[str, Any]:
    """Serialize a FounderInboxV2 to a JSON-serializable dict."""
    return inbox.to_dict()
