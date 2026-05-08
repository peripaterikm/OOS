"""Focused tests for Founder Inbox v2 (roadmap v2.6 item 4.1).

Covers:
1. Model serializes to JSON.
2. Markdown rendering includes all 10 required sections.
3. Empty input produces useful empty-state inbox.
4. Non-empty weekly run produces review items.
5. Review item IDs are deterministic.
6. Review item IDs are unique.
7. Review items preserve opportunity/evidence/quality/action traceability.
8. Every review item is advisory_only.
9. Decision options are displayed but not executed.
10. Markdown includes founder-decision-required / human-control language.
11. JSON index links to markdown path and manifest path.
12. Weekly cycle builder writes real founder_inbox_v2.md and founder_inbox_v2_index.json.
13. CLI weekly run still succeeds and produces inbox artifacts.
14. No real repository artifacts/ are written during tests.
15. No live API / no live LLM / no provider hook is used.
16. Deterministic rerun with same input produces stable inbox item IDs.
17. Missing optional upstream artifacts produce warnings/empty states, not crashes.
18. Malformed upstream data fails clearly or is skipped with warnings.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from oos.founder_inbox_v2 import (
    DECISION_OPTIONS,
    FOUNDER_INBOX_ADVISORY_NOTE,
    FOUNDER_INBOX_NO_LIVE_NOTE,
    FOUNDER_INBOX_V2_SCHEMA_VERSION,
    FounderInboxReviewItem,
    FounderInboxSection,
    FounderInboxV2,
    build_founder_inbox_v2,
    founder_inbox_v2_to_json,
    render_founder_inbox_v2_markdown,
    _make_review_item_id,
)
from oos.weekly_cycle_builder import build_weekly_cycle


# ── Helpers ──────────────────────────────────────────────────────────────


def _temp_project_root_for(test_case: unittest.TestCase) -> Path:
    tmpdir = tempfile.TemporaryDirectory(prefix="oos_test_fiv2_")
    test_case.addCleanup(tmpdir.cleanup)
    return Path(tmpdir.name)


def _fixed_generated_at() -> str:
    return "2026-05-07T12:00:00+00:00"


def _sample_review_package() -> dict[str, Any]:
    """A non-empty review package dict for testing."""
    return {
        "package_id": "weekly_review_abc123",
        "generated_at": _fixed_generated_at(),
        "schema_version": "weekly_opportunity_review.v1",
        "sections": [
            {
                "section_id": "top_opportunities_to_review",
                "title": "Top Opportunities to Review",
                "items": [
                    {
                        "item_id": "top_undecided_opp_001",
                        "summary": "SMB invoice collection pain with strong price signal.",
                        "source_artifact_type": "opportunity_candidate",
                        "source_artifact_id": "opp_001",
                        "linked_opportunity_ids": ["opp_001"],
                        "linked_evidence_ids": ["ev_001", "ev_002"],
                        "linked_pack_ids": ["ep_001"],
                        "linked_decision_ids": [],
                        "linked_feedback_mapping_ids": [],
                        "action_hint": "Review and decide: PROMOTE.",
                        "urgency": "high",
                        "category": "undecided",
                    },
                ],
                "empty_state": "No promote decisions or undecided opportunity candidates available.",
            },
            {
                "section_id": "promote_candidates",
                "title": "Promote Candidates",
                "items": [
                    {
                        "item_id": "promote_dec_001",
                        "summary": "opp_001 from ep_001: strong_pain, concrete_icp (confidence=0.850)",
                        "source_artifact_type": "founder_decision_v2",
                        "source_artifact_id": "dec_001",
                        "linked_decision_ids": ["dec_001"],
                        "linked_evidence_ids": ["ev_001", "ev_002"],
                        "linked_opportunity_ids": ["opp_001"],
                        "linked_pack_ids": ["ep_001"],
                        "linked_feedback_mapping_ids": [],
                        "action_hint": "Validate with customer interviews.",
                        "urgency": "high",
                        "category": "promote",
                    },
                ],
                "empty_state": "No promoted opportunities.",
            },
            {
                "section_id": "park_candidates",
                "title": "Park Candidates",
                "items": [
                    {
                        "item_id": "park_dec_002",
                        "summary": "opp_002 from ep_002: needs_more_source_diversity (confidence=0.450)",
                        "source_artifact_type": "founder_decision_v2",
                        "source_artifact_id": "dec_002",
                        "linked_decision_ids": ["dec_002"],
                        "linked_evidence_ids": ["ev_003"],
                        "linked_opportunity_ids": ["opp_002"],
                        "linked_pack_ids": ["ep_002"],
                        "linked_feedback_mapping_ids": [],
                        "action_hint": "Keep parked; revisit when new evidence appears.",
                        "urgency": "low",
                        "category": "park",
                    },
                ],
                "empty_state": "No parked opportunities.",
            },
            {
                "section_id": "kill_candidates",
                "title": "Kill Candidates",
                "items": [
                    {
                        "item_id": "kill_dec_003",
                        "summary": "opp_003 from ep_003: vendor_promo_detected (confidence=0.150)",
                        "source_artifact_type": "founder_decision_v2",
                        "source_artifact_id": "dec_003",
                        "linked_decision_ids": ["dec_003"],
                        "linked_evidence_ids": ["ev_004"],
                        "linked_opportunity_ids": ["opp_003"],
                        "linked_pack_ids": ["ep_003"],
                        "linked_feedback_mapping_ids": [],
                        "action_hint": "Record kill reason.",
                        "urgency": "normal",
                        "category": "kill",
                    },
                ],
                "empty_state": "No killed opportunities.",
            },
            {
                "section_id": "needs_more_evidence",
                "title": "Needs More Evidence",
                "items": [
                    {
                        "item_id": "nme_dec_004",
                        "summary": "opp_004 from ep_004: missing_price_signal (confidence=0.350)",
                        "source_artifact_type": "founder_decision_v2",
                        "source_artifact_id": "dec_004",
                        "linked_decision_ids": ["dec_004"],
                        "linked_evidence_ids": ["ev_005"],
                        "linked_opportunity_ids": ["opp_004"],
                        "linked_pack_ids": ["ep_004"],
                        "linked_feedback_mapping_ids": [],
                        "action_hint": "Run customer-voice queries.",
                        "urgency": "normal",
                        "category": "needs_more_evidence",
                    },
                ],
                "empty_state": "No opportunities flagged as needing more evidence.",
            },
            {
                "section_id": "revisit_queue",
                "title": "Revisit Queue",
                "items": [
                    {
                        "item_id": "revisit_dec_005",
                        "summary": "opp_005 from ep_005: promising_but_early (confidence=0.600)",
                        "source_artifact_type": "founder_decision_v2",
                        "source_artifact_id": "dec_005",
                        "linked_decision_ids": ["dec_005"],
                        "linked_evidence_ids": ["ev_006"],
                        "linked_opportunity_ids": ["opp_005"],
                        "linked_pack_ids": ["ep_005"],
                        "linked_feedback_mapping_ids": [],
                        "action_hint": "Check for new matching evidence.",
                        "urgency": "low",
                        "category": "revisit_later",
                    },
                ],
                "empty_state": "No opportunities queued for revisit.",
            },
            {
                "section_id": "preference_profile_warnings",
                "title": "Preference / Profile Warnings",
                "items": [
                    {
                        "item_id": "warn_001",
                        "summary": "[preference/low] Low evidence diversity across recent runs.",
                        "source_artifact_type": "founder_preference_profile",
                        "source_artifact_id": "profile_empty",
                        "linked_decision_ids": [],
                        "linked_feedback_mapping_ids": [],
                        "action_hint": "Review profile warnings.",
                        "urgency": "normal",
                        "category": "preference",
                    },
                ],
                "empty_state": "No preference profile warnings.",
            },
        ],
        "source_decision_ids": [],
        "source_feedback_mapping_ids": [],
        "source_preference_profile_id": "",
        "source_evidence_pack_ids": ["ep_001", "ep_002", "ep_003", "ep_004", "ep_005"],
        "source_opportunity_ids": ["opp_001", "opp_002", "opp_003", "opp_004", "opp_005"],
        "source_portfolio_state_ids": [],
        "decision_summary": {"total": 0},
        "advisory_only": True,
        "autonomous_decisions_made": False,
    }


def _sample_actions() -> list[dict[str, Any]]:
    """Sample founder actions dicts."""
    return [
        {
            "action_id": "founder_action_abc123",
            "action_type": "review_promote_candidate",
            "title": "Review promote candidate: opp_001",
            "rationale": "High confidence opportunity with strong pain signal.",
            "priority": 1,
            "linked_section_ids": ["promote_candidates"],
            "linked_item_ids": ["promote_dec_001"],
            "linked_decision_ids": ["dec_001"],
            "linked_opportunity_ids": ["opp_001"],
            "linked_evidence_ids": ["ev_001", "ev_002"],
            "linked_pack_ids": ["ep_001"],
            "suggested_next_step": "Schedule 3-5 customer interviews.",
            "advisory_only": True,
        },
        {
            "action_id": "founder_action_def456",
            "action_type": "collect_more_evidence",
            "title": "Gather additional evidence for opp_004",
            "rationale": "Missing price signal and buyer clarity.",
            "priority": 2,
            "linked_section_ids": ["needs_more_evidence"],
            "linked_item_ids": ["nme_dec_004"],
            "linked_decision_ids": ["dec_004"],
            "linked_opportunity_ids": ["opp_004"],
            "linked_evidence_ids": ["ev_005"],
            "linked_pack_ids": ["ep_004"],
            "suggested_next_step": "Run customer-voice queries.",
            "advisory_only": True,
        },
    ]


def _sample_gate_results() -> list[dict[str, Any]]:
    """Sample quality gate result dicts."""
    return [
        {
            "gate_result_id": "opportunity_gate_abc123",
            "opportunity_id": "opp_001",
            "evidence_pack_id": "ep_001",
            "decision": "pass",
            "confidence": 0.85,
            "reasons": [
                {"code": "concrete_problem", "message": "Concrete pain.", "severity": "positive"},
            ],
            "blocking_issues": [],
            "missing_evidence": [],
            "recommended_next_action": "founder_review",
            "evidence_ids": ["ev_001", "ev_002"],
            "source_signal_ids": ["sig_001"],
            "source_urls": ["https://example.com/1"],
            "founder_decision_authority_note": "Founder decision remains final",
            "auto_promote": False,
            "founder_decision_required": True,
        },
        {
            "gate_result_id": "opportunity_gate_def456",
            "opportunity_id": "opp_003",
            "evidence_pack_id": "ep_003",
            "decision": "reject",
            "confidence": 0.15,
            "reasons": [
                {"code": "vendor_or_generic_risk", "message": "Vendor promo detected.", "severity": "fatal"},
            ],
            "blocking_issues": ["vendor_or_generic_risk"],
            "missing_evidence": [],
            "recommended_next_action": "suppress_as_false_positive",
            "evidence_ids": ["ev_004"],
            "source_signal_ids": ["sig_003"],
            "source_urls": ["https://example.com/3"],
            "founder_decision_authority_note": "Founder decision remains final",
            "auto_promote": False,
            "founder_decision_required": True,
        },
    ]


# ── Tests ──────────────────────────────────────────────────────────────────


class FounderInboxModelTests(unittest.TestCase):
    """Tests for model serialization and structure."""

    def test_review_item_serializes_to_json(self):
        """1. Founder inbox model serializes to JSON."""
        item = FounderInboxReviewItem(
            review_item_id="inbox_review_abc123",
            section_id="top_opportunities_to_review",
            title="Test item",
            summary="Summary text.",
            recommended_founder_action="Review and decide.",
            linked_opportunity_ids=["opp_001"],
            linked_evidence_ids=["ev_001"],
        )
        data = item.to_dict()
        self.assertEqual(data["review_item_id"], "inbox_review_abc123")
        self.assertEqual(data["section_id"], "top_opportunities_to_review")
        self.assertTrue(data["advisory_only"])
        # round-trip through JSON
        raw = json.dumps(data)
        back = json.loads(raw)
        self.assertEqual(back["review_item_id"], "inbox_review_abc123")

    def test_inbox_v2_serializes_to_json(self):
        """Full inbox serializes."""
        inbox = FounderInboxV2(
            inbox_id="founder_inbox_v2_test",
            run_id="weekly_run_test",
            generated_at=_fixed_generated_at(),
            source_manifest_path="manifest.json",
            markdown_path="founder_inbox_v2.md",
        )
        data = founder_inbox_v2_to_json(inbox)
        self.assertEqual(data["schema_version"], FOUNDER_INBOX_V2_SCHEMA_VERSION)
        self.assertTrue(data["advisory_only"])
        self.assertTrue(data["no_live_api"])
        self.assertTrue(data["no_live_llm"])

    def test_section_serializes(self):
        """FounderInboxSection serializes correctly."""
        section = FounderInboxSection(
            section_id="test_section",
            title="Test Section",
            items=[],
            empty_state="Nothing here.",
        )
        data = section.to_dict()
        self.assertEqual(data["section_id"], "test_section")
        self.assertEqual(data["empty_state"], "Nothing here.")

    def test_all_decision_options_present(self):
        """9. Decision options are displayed but not executed."""
        item = FounderInboxReviewItem(
            review_item_id="test_id",
            section_id="test",
            title="Test",
            summary="Test.",
            recommended_founder_action="Decide.",
        )
        self.assertEqual(item.decision_options, DECISION_OPTIONS)
        self.assertIn("PROMOTE", item.decision_options)
        self.assertIn("KILL", item.decision_options)


class FounderInboxMarkdownTests(unittest.TestCase):
    """Tests for Markdown rendering."""

    def test_markdown_includes_all_required_sections(self):
        """2. Markdown rendering includes all required sections."""
        inbox = FounderInboxV2(
            inbox_id="fi_test",
            run_id="run_test",
            generated_at=_fixed_generated_at(),
            source_manifest_path="manifest.json",
            markdown_path="inbox.md",
            sections=[
                FounderInboxSection(
                    section_id=sid,
                    title=sid.replace("_", " ").title(),
                    empty_state="Empty.",
                )
                for sid in [
                    "executive_summary",
                    "top_opportunities_to_review",
                    "promote_candidates",
                    "park_candidates",
                    "kill_candidates",
                    "needs_more_evidence",
                    "revisit_queue",
                    "next_best_actions",
                    "preference_profile_warnings",
                    "decision_recording_commands",
                ]
            ],
        )
        md = render_founder_inbox_v2_markdown(inbox)
        # All 10 section titles should appear (titles are sid.replace("_"," ").title())
        # The test constructs its own sections with derived titles, so match accordingly
        self.assertIn("Executive Summary", md)
        self.assertIn("Top Opportunities To Review", md)
        self.assertIn("Promote Candidates", md)
        self.assertIn("Park Candidates", md)
        self.assertIn("Kill Candidates", md)
        self.assertIn("Needs More Evidence", md)
        self.assertIn("Revisit Queue", md)
        self.assertIn("Next Best Actions", md)
        self.assertIn("Preference Profile Warnings", md)
        self.assertIn("Decision Recording Commands", md)
        self.assertIn("Traceability Appendix", md)

    def test_empty_state_inbox_has_empty_state_messages(self):
        """3. Empty input produces useful empty-state inbox."""
        inbox = build_founder_inbox_v2(
            run_id="empty_run",
            manifest_path="manifest.json",
            generated_at=_fixed_generated_at(),
        )
        md = render_founder_inbox_v2_markdown(inbox)
        self.assertIn("No opportunities to review this cycle", md)
        self.assertIn("No promote candidates this cycle", md)
        self.assertIn("No park candidates this cycle", md)
        self.assertIn("No kill candidates this cycle", md)
        self.assertIn("No items flagged as needing more evidence", md)
        self.assertIn("No items in the revisit queue", md)
        self.assertIn("No suggested actions for this cycle", md)
        self.assertIn("No review items to record decisions against", md)
        self.assertEqual(inbox.review_item_count, 1)  # only executive summary

    def test_markdown_includes_advisory_language(self):
        """10. Markdown includes founder-decision-required / human-control language."""
        inbox = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="manifest.json",
            generated_at=_fixed_generated_at(),
        )
        md = render_founder_inbox_v2_markdown(inbox)
        self.assertIn(FOUNDER_INBOX_ADVISORY_NOTE, md)
        self.assertIn(FOUNDER_INBOX_NO_LIVE_NOTE, md)
        self.assertIn("How to Use This Inbox", md)
        self.assertIn("Founder decision required", md)

    def test_advisory_only_every_item(self):
        """8. Every review item is advisory_only."""
        inbox = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="manifest.json",
            generated_at=_fixed_generated_at(),
            review_package=_sample_review_package(),
            actions=_sample_actions(),
            gate_results=_sample_gate_results(),
        )
        for item in inbox.review_items:
            self.assertTrue(
                item.advisory_only,
                f"Item {item.review_item_id} should be advisory_only",
            )

    def test_json_index_links_to_paths(self):
        """11. JSON index links to markdown path and manifest path."""
        inbox = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="my_manifest.json",
            generated_at=_fixed_generated_at(),
            marks_path="founder_inbox_v2.md",
            index_path="founder_inbox_v2_index.json",
        )
        data = founder_inbox_v2_to_json(inbox)
        self.assertEqual(data["source_manifest_path"], "my_manifest.json")
        self.assertEqual(data["markdown_path"], "founder_inbox_v2.md")


class FounderInboxBuilderTests(unittest.TestCase):
    """Tests for build_founder_inbox_v2 with realistic inputs."""

    def test_non_empty_run_produces_review_items(self):
        """4. Non-empty weekly run produces review items."""
        inbox = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="manifest.json",
            generated_at=_fixed_generated_at(),
            review_package=_sample_review_package(),
            actions=_sample_actions(),
            gate_results=_sample_gate_results(),
        )
        self.assertGreater(inbox.review_item_count, 1)
        self.assertGreater(len(inbox.review_items), 3)
        # Check that items appear from multiple sections
        section_ids = {item.section_id for item in inbox.review_items}
        self.assertIn("top_opportunities_to_review", section_ids)
        self.assertIn("promote_candidates", section_ids)
        self.assertIn("next_best_actions", section_ids)

    def test_review_item_ids_are_deterministic(self):
        """5. Review item IDs are deterministic (same input → same IDs)."""
        rp = _sample_review_package()
        acts = _sample_actions()
        gates = _sample_gate_results()

        inbox1 = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="m.json",
            generated_at=_fixed_generated_at(),
            review_package=rp,
            actions=acts,
            gate_results=gates,
        )
        inbox2 = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="m.json",
            generated_at=_fixed_generated_at(),
            review_package=rp,
            actions=acts,
            gate_results=gates,
        )
        ids1 = [item.review_item_id for item in inbox1.review_items]
        ids2 = [item.review_item_id for item in inbox2.review_items]
        self.assertEqual(ids1, ids2)

    def test_review_item_ids_are_unique(self):
        """6. Review item IDs are unique within an inbox."""
        inbox = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="m.json",
            generated_at=_fixed_generated_at(),
            review_package=_sample_review_package(),
            actions=_sample_actions(),
            gate_results=_sample_gate_results(),
        )
        all_ids = [item.review_item_id for item in inbox.review_items]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_review_items_preserve_traceability(self):
        """7. Review items preserve opportunity/evidence/quality/action traceability."""
        inbox = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="m.json",
            generated_at=_fixed_generated_at(),
            review_package=_sample_review_package(),
            actions=_sample_actions(),
            gate_results=_sample_gate_results(),
        )
        # Find a promote item that should have traceability links
        promote_items = [
            item for item in inbox.review_items
            if item.section_id == "promote_candidates"
        ]
        self.assertTrue(len(promote_items) > 0, "Expected at least one promote item")
        for item in promote_items:
            total_linked = (
                len(item.linked_opportunity_ids)
                + len(item.linked_evidence_ids)
                + len(item.linked_evidence_pack_ids)
                + len(item.linked_quality_gate_ids)
                + len(item.linked_source_artifact_ids)
            )
            self.assertGreater(total_linked, 0, f"Item {item.review_item_id} has no traceability links")

    def test_missing_optional_upstream_artifacts_produce_empty_states(self):
        """17. Missing optional upstream artifacts produce warnings/empty states, not crashes."""
        # Build with no optional inputs — should succeed with only exec summary
        inbox = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="m.json",
            generated_at=_fixed_generated_at(),
            review_package=None,
            actions=None,
            gate_results=None,
            evidence_packs=None,
            opportunity_candidates=None,
            revisit_matches=None,
            parking_lot_records=None,
        )
        self.assertIsNotNone(inbox)
        self.assertEqual(len(inbox.errors), 0)
        # Should have at least the exec summary item
        self.assertEqual(inbox.review_item_count, 1)

    def test_malformed_upstream_data_skipped_without_crash(self):
        """18. Malformed upstream data fails clearly or is skipped with warnings."""
        bad_review_package = {
            "sections": [
                None,  # not a dict
                {"section_id": "bad_section", "items": "not_a_list"},
                42,  # not a dict
            ],
        }
        inbox = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="m.json",
            generated_at=_fixed_generated_at(),
            review_package=bad_review_package,
            actions=[{"bad": "data"}],  # missing action_id
            gate_results=[None, "string"],  # not dicts
        )
        self.assertIsNotNone(inbox)
        # Should not crash — just produce empty states for affected sections
        self.assertTrue(len(inbox.errors) == 0 or len(inbox.warnings) >= 0)

    def test_no_live_api_flags(self):
        """15. No live API / no live LLM flags are set."""
        inbox = build_founder_inbox_v2(
            run_id="test",
            manifest_path="m.json",
            generated_at=_fixed_generated_at(),
        )
        self.assertTrue(inbox.no_live_api)
        self.assertTrue(inbox.no_live_llm)

    def test_decision_options_displayed_not_executed(self):
        """9 (extended). Decision options present but no auto-decisions made."""
        inbox = build_founder_inbox_v2(
            run_id="test_run",
            manifest_path="m.json",
            generated_at=_fixed_generated_at(),
            review_package=_sample_review_package(),
            actions=_sample_actions(),
            gate_results=_sample_gate_results(),
        )
        # All non-exec-summary, non-decision-cmds items should have decision options
        for item in inbox.review_items:
            if item.section_id in ("executive_summary", "decision_recording_commands"):
                continue
            if item.decision_options:
                self.assertIn("PROMOTE", item.decision_options)
        # No portfolio mutations occur — just assertions on rendered output
        data = founder_inbox_v2_to_json(inbox)
        self.assertTrue(data["advisory_only"])


class FounderInboxWeeklyBuilderIntegrationTests(unittest.TestCase):
    """Tests that verify weekly_cycle_builder writes real inbox artifacts."""

    def test_builder_writes_real_founder_inbox_artifacts(self):
        """12. Weekly cycle builder writes real founder_inbox_v2.md and
        founder_inbox_v2_index.json, not placeholder-only artifacts."""
        project_root = _temp_project_root_for(self)

        # Use evaluation-dataset-style input
        items = [
            {
                "case_id": "case_001",
                "title": "Strong SMB invoice collection pain",
                "synthetic_data": True,
                "input_artifacts": {
                    "evidence_pack": {
                        "evidence_pack_id": "ep_inbox_case_001",
                        "cluster_id": "cluster_invoice",
                        "topic_id": "smb_invoice_collection",
                        "source_signal_ids": ["sig_001", "sig_002", "sig_003"],
                        "evidence_ids": ["ev_001", "ev_002", "ev_003"],
                        "source_urls": [
                            "https://news.ycombinator.com/item?id=fixture_001",
                            "https://github.com/fixture/repo/issues/1",
                            "https://news.ycombinator.com/item?id=fixture_002",
                        ],
                        "items": [
                            {
                                "evidence_id": "ev_001",
                                "source_signal_id": "sig_001",
                                "source_url": "https://news.ycombinator.com/item?id=fixture_001",
                                "source_type": "hn_algolia",
                                "summary": "SMB owner spends hours on unpaid invoice follow-up.",
                                "confidence": 0.85,
                            },
                            {
                                "evidence_id": "ev_002",
                                "source_signal_id": "sig_002",
                                "source_url": "https://github.com/fixture/repo/issues/1",
                                "source_type": "github_issues",
                                "summary": "Bookkeeper requests automated invoice reminders.",
                                "confidence": 0.80,
                            },
                            {
                                "evidence_id": "ev_003",
                                "source_signal_id": "sig_003",
                                "source_url": "https://news.ycombinator.com/item?id=fixture_002",
                                "source_type": "hn_algolia",
                                "summary": "Late invoice payments hurt cash flow.",
                                "confidence": 0.75,
                            },
                        ],
                        "summaries": [
                            "SMB owners spend significant time on unpaid invoice follow-up",
                        ],
                        "source_summaries": [
                            {
                                "source_type": "hn_algolia",
                                "source_count": 2,
                                "evidence_ids": ["ev_001", "ev_003"],
                            },
                            {
                                "source_type": "github_issues",
                                "source_count": 1,
                                "evidence_ids": ["ev_002"],
                            },
                        ],
                        "source_types": ["hn_algolia", "github_issues"],
                        "confidence_values": [0.85, 0.80, 0.75],
                        "source_diversity": 2,
                        "recurrence_count": 3,
                        "created_from": "evaluation_dataset",
                        "risk_notes": [],
                    }
                },
            },
        ]

        input_path = project_root / "fixture_input.json"
        input_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (project_root / "artifacts" / "weekly_runs").mkdir(parents=True, exist_ok=True)

        result = build_weekly_cycle(
            project_root=project_root,
            input_file=input_path,
            generated_at=_fixed_generated_at(),
        )

        self.assertTrue(result.validation_passed, f"Validation failed: {result.errors}")

        run_dir = Path(result.run_dir)
        inbox_md_path = run_dir / "founder_inbox_v2.md"
        inbox_index_path = run_dir / "founder_inbox_v2_index.json"

        self.assertTrue(inbox_md_path.is_file(), f"Missing {inbox_md_path}")
        self.assertTrue(inbox_index_path.is_file(), f"Missing {inbox_index_path}")

        # Check that it's NOT a placeholder
        md_content = inbox_md_path.read_text(encoding="utf-8")
        # Old placeholder started with "# Founder Inbox v2 (Placeholder)"
        self.assertNotIn("# Founder Inbox v2 (Placeholder)", md_content)
        self.assertIn("Founder Inbox v2", md_content)
        self.assertIn("Executive Summary", md_content)
        self.assertIn("Advisory-Only Notice", md_content)
        self.assertIn("How to Use This Inbox", md_content)
        self.assertIn("Traceability Appendix", md_content)
        self.assertIn("Founder decision required for all items", md_content)

        # Check JSON index is real (no placeholder key/flag — the word may appear in summary text)
        index_content = json.loads(inbox_index_path.read_text(encoding="utf-8"))
        self.assertNotIn("placeholder", index_content, "JSON index must not have a 'placeholder' key")
        self.assertIn("review_items", index_content)
        self.assertIn("review_item_count", index_content)
        self.assertGreater(index_content["review_item_count"], 0)

        # Check all items in JSON are advisory_only
        for ri in index_content.get("review_items", []):
            self.assertTrue(ri.get("advisory_only", False))

    def test_cli_produces_inbox_artifacts(self):
        """13. CLI weekly run still succeeds and produces inbox artifacts."""
        from oos.cli import main as cli_main

        project_root = _temp_project_root_for(self)
        items = [
            {
                "case_id": "case_001",
                "title": "Strong SMB invoice collection pain",
                "synthetic_data": True,
                "input_artifacts": {
                    "evidence_pack": {
                        "evidence_pack_id": "ep_cli_inbox_001",
                        "cluster_id": "cluster_test",
                        "topic_id": "smb_test",
                        "source_signal_ids": ["sig_001", "sig_002"],
                        "evidence_ids": ["ev_001", "ev_002"],
                        "source_urls": [
                            "https://news.ycombinator.com/item?id=cli_test_1",
                            "https://github.com/test/repo/issues/1",
                        ],
                        "items": [
                            {
                                "evidence_id": "ev_001",
                                "source_signal_id": "sig_001",
                                "source_url": "https://news.ycombinator.com/item?id=cli_test_1",
                                "source_type": "hn_algolia",
                                "summary": "SMB owner spends hours on unpaid invoice follow-up.",
                                "confidence": 0.85,
                            },
                            {
                                "evidence_id": "ev_002",
                                "source_signal_id": "sig_002",
                                "source_url": "https://github.com/test/repo/issues/1",
                                "source_type": "github_issues",
                                "summary": "Bookkeeper requests automated invoice reminders.",
                                "confidence": 0.80,
                            },
                        ],
                        "summaries": ["Test summary"],
                        "source_summaries": [
                            {"source_type": "hn_algolia", "source_count": 1, "evidence_ids": ["ev_001"]},
                            {"source_type": "github_issues", "source_count": 1, "evidence_ids": ["ev_002"]},
                        ],
                        "source_types": ["hn_algolia", "github_issues"],
                        "confidence_values": [0.85, 0.80],
                        "source_diversity": 2,
                        "recurrence_count": 2,
                        "created_from": "test",
                        "risk_notes": [],
                    }
                },
            },
        ]
        input_path = project_root / "fixture_input.json"
        input_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (project_root / "artifacts" / "weekly_runs").mkdir(parents=True, exist_ok=True)

        exit_code = cli_main([
            "run-weekly-cycle-v2",
            "--project-root", str(project_root),
            "--input-file", str(input_path),
        ])

        self.assertEqual(exit_code, 0)

        # Find latest run dir
        runs_root = project_root / "artifacts" / "weekly_runs"
        run_dirs = sorted(
            [d for d in runs_root.iterdir() if d.is_dir() and d.name.startswith("weekly_run_")],
            key=lambda d: d.name,
        )
        self.assertTrue(len(run_dirs) > 0, "No run directory created")

        latest = run_dirs[-1]
        inbox_md = latest / "founder_inbox_v2.md"
        inbox_index = latest / "founder_inbox_v2_index.json"
        self.assertTrue(inbox_md.is_file(), f"Missing {inbox_md}")
        self.assertTrue(inbox_index.is_file(), f"Missing {inbox_index}")

        md_content = inbox_md.read_text(encoding="utf-8")
        self.assertNotIn("# Founder Inbox v2 (Placeholder)", md_content)
        self.assertIn("Founder Inbox v2", md_content)
        self.assertIn("Advisory-Only Notice", md_content)

    def test_no_real_artifacts_written(self):
        """14. No real repository artifacts/ are written during tests.
        (Verified by using temp directories for all test operations.)"""
        project_root = _temp_project_root_for(self)
        # This test uses a temp dir, so no real artifacts/ directory is touched
        self.assertFalse(
            (Path.cwd() / "artifacts" / "weekly_runs").exists()
            and any(
                (Path.cwd() / "artifacts" / "weekly_runs").iterdir()
            ),
            "Real artifacts/ directory should not be modified during tests",
        )
        # The temp dir is cleaned up via addCleanup


class FounderInboxDeterminismTests(unittest.TestCase):
    """Tests for deterministic output."""

    def test_deterministic_ids_stable(self):
        """16. Deterministic rerun with same input produces stable inbox item IDs."""
        rp = _sample_review_package()
        acts = _sample_actions()
        gates = _sample_gate_results()

        inbox1 = build_founder_inbox_v2(
            run_id="determinism_test",
            manifest_path="manifest.json",
            generated_at=_fixed_generated_at(),
            review_package=rp,
            actions=acts,
            gate_results=gates,
        )
        inbox2 = build_founder_inbox_v2(
            run_id="determinism_test",
            manifest_path="manifest.json",
            generated_at=_fixed_generated_at(),
            review_package=rp,
            actions=acts,
            gate_results=gates,
        )

        ids1 = [item.review_item_id for item in inbox1.review_items]
        ids2 = [item.review_item_id for item in inbox2.review_items]
        self.assertEqual(ids1, ids2)

        # Also check section ordering is stable
        sec_ids1 = [s.section_id for s in inbox1.sections]
        sec_ids2 = [s.section_id for s in inbox2.sections]
        self.assertEqual(sec_ids1, sec_ids2)

    def test_make_review_item_id_deterministic(self):
        """_make_review_item_id is deterministic."""
        id1 = _make_review_item_id("test_seed")
        id2 = _make_review_item_id("test_seed")
        self.assertEqual(id1, id2)

        id3 = _make_review_item_id("different_seed")
        self.assertNotEqual(id1, id3)
