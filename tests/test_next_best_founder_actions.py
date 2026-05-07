"""Tests for next_best_founder_actions — deterministic advisory action recommendations."""

import json
import unittest

from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    create_founder_decision,
)
from oos.founder_feedback_mapping import map_founder_decision_to_feedback
from oos.founder_preference_profile import build_founder_preference_profile
from oos.next_best_founder_actions import (
    ALLOWED_ACTION_TYPES,
    FOUNDER_ACTION_SCHEMA_VERSION,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    FounderAction,
    build_next_best_founder_actions,
    next_best_actions_to_json,
    render_next_best_actions_markdown,
)
from oos.weekly_opportunity_review import (
    WeeklyOpportunityReviewPackage,
    build_weekly_opportunity_review_package,
    weekly_review_package_to_json,
)


def _make_test_decision(
    opportunity_id: str,
    decision: str,
    reasons: list[str],
    confidence: float = 0.6,
):
    return create_founder_decision(
        opportunity_id=opportunity_id,
        evidence_pack_id=f"ep_{opportunity_id}",
        decision=decision,
        reasons=reasons,
        confidence=confidence,
        linked_evidence_ids=[f"ev_{opportunity_id}_1"],
        linked_source_signal_ids=[f"sig_{opportunity_id}_1"],
        linked_source_urls=[f"https://example.com/{opportunity_id}"],
    )


def _package_to_dict(*args, **kwargs):
    """Build a weekly review package and return as a plain dict."""
    package = build_weekly_opportunity_review_package(*args, **kwargs)
    return json.loads(weekly_review_package_to_json(package))


# ---------------------------------------------------------------------------
# FounderAction model tests
# ---------------------------------------------------------------------------


class FounderActionModelTests(unittest.TestCase):
    def test_action_roundtrip_to_dict_and_back(self):
        action = FounderAction(
            action_id="fa_test_01",
            action_type="review_promote_candidate",
            title="Review promote candidate: test summary",
            rationale="Test rationale",
            priority=PRIORITY_HIGH,
            linked_section_ids=["promote_candidates"],
            linked_item_ids=["item_1"],
            linked_decision_ids=["fd_1"],
            linked_opportunity_ids=["opp_a"],
            linked_evidence_ids=["ev_1"],
            linked_pack_ids=["ep_1"],
            suggested_next_step="Review and validate.",
            advisory_only=True,
        )
        data = action.to_dict()
        restored = FounderAction.from_dict(data)
        self.assertEqual(restored.action_id, "fa_test_01")
        self.assertEqual(restored.action_type, "review_promote_candidate")
        self.assertEqual(restored.title, "Review promote candidate: test summary")
        self.assertEqual(restored.priority, PRIORITY_HIGH)
        self.assertTrue(restored.advisory_only)
        self.assertEqual(restored.linked_decision_ids, ["fd_1"])
        self.assertEqual(restored.linked_opportunity_ids, ["opp_a"])
        self.assertEqual(restored.schema_version, FOUNDER_ACTION_SCHEMA_VERSION)

    def test_action_defaults(self):
        action = FounderAction(
            action_id="fa_default",
            action_type="collect_more_evidence",
            title="Test",
            rationale="Test",
        )
        self.assertEqual(action.priority, PRIORITY_NORMAL)
        self.assertEqual(action.linked_section_ids, [])
        self.assertEqual(action.linked_item_ids, [])
        self.assertTrue(action.advisory_only)
        self.assertEqual(action.schema_version, FOUNDER_ACTION_SCHEMA_VERSION)

    def test_advisory_only_is_true_by_default(self):
        action = FounderAction(
            action_id="fa_check",
            action_type="review_promote_candidate",
            title="T",
            rationale="R",
        )
        self.assertTrue(action.advisory_only)

    def test_allowed_action_types(self):
        """Verify ALLOWED_ACTION_TYPES covers the required categories."""
        self.assertIn("review_promote_candidate", ALLOWED_ACTION_TYPES)
        self.assertIn("collect_more_evidence", ALLOWED_ACTION_TYPES)
        self.assertIn("interview_customer", ALLOWED_ACTION_TYPES)
        self.assertIn("validate_price_signal", ALLOWED_ACTION_TYPES)
        self.assertIn("revisit_parked_opportunity", ALLOWED_ACTION_TYPES)
        self.assertIn("consider_kill_candidate", ALLOWED_ACTION_TYPES)
        self.assertIn("review_preference_warning", ALLOWED_ACTION_TYPES)
        self.assertIn("run_customer_voice_queries", ALLOWED_ACTION_TYPES)
        self.assertIn("address_evidence_gap", ALLOWED_ACTION_TYPES)
        self.assertIn("review_undecided_opportunity", ALLOWED_ACTION_TYPES)
        self.assertEqual(len(ALLOWED_ACTION_TYPES), 10)


# ---------------------------------------------------------------------------
# Empty / edge case tests
# ---------------------------------------------------------------------------


class EmptyPackageTests(unittest.TestCase):
    def test_empty_dict_returns_empty_list(self):
        actions = build_next_best_founder_actions({})
        self.assertEqual(actions, [])

    def test_no_sections_returns_empty_list(self):
        actions = build_next_best_founder_actions({"sections": []})
        self.assertEqual(actions, [])

    def test_empty_weekly_package_returns_empty_list(self):
        package = _package_to_dict()
        actions = build_next_best_founder_actions(package)
        # Empty package has 10 sections all with no items
        self.assertEqual(actions, [])

    def test_none_input_returns_empty_list(self):
        actions = build_next_best_founder_actions(None)
        self.assertEqual(actions, [])


# ---------------------------------------------------------------------------
# Action generation tests with various decisions
# ---------------------------------------------------------------------------


class ActionGenerationTests(unittest.TestCase):
    def test_promote_decisions_generate_actions(self):
        decisions = [
            _make_test_decision("opp_p", PROMOTE, ["strong_pain", "worth_interviews"], 0.85),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        promote_actions = [a for a in actions if a.action_type == "review_promote_candidate"]
        self.assertGreaterEqual(len(promote_actions), 1)
        for a in promote_actions:
            self.assertTrue(a.advisory_only)
            self.assertIn("opp_p", a.rationale)

    def test_all_decision_types_produce_actions(self):
        decisions = [
            _make_test_decision("opp_promote", PROMOTE, ["strong_pain", "worth_interviews"], 0.85),
            _make_test_decision("opp_park", PARK, ["weak_evidence"], 0.5),
            _make_test_decision("opp_kill", KILL, ["too_generic", "no_buyer"], 0.9),
            _make_test_decision("opp_revisit", REVISIT_LATER, ["waiting_for_more_signals"], 0.4),
            _make_test_decision("opp_nme", NEEDS_MORE_EVIDENCE, ["need_customer_voice"], 0.55),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        action_types = {a.action_type for a in actions}
        self.assertIn("review_promote_candidate", action_types)
        self.assertIn("collect_more_evidence", action_types)
        self.assertIn("consider_kill_candidate", action_types)
        self.assertIn("revisit_parked_opportunity", action_types)
        self.assertIn("interview_customer", action_types)

        # Every action must be advisory_only
        for a in actions:
            self.assertTrue(
                a.advisory_only,
                f"Action {a.action_id} ({a.action_type}) must be advisory_only",
            )

    def test_opportunity_candidates_produce_actions(self):
        decisions = [
            _make_test_decision("opp_decided", PROMOTE, ["strong_pain"], 0.75),
        ]
        opp_candidates = [
            {
                "opportunity_id": "opp_undecided_1",
                "pain_summary": "SMB cash collection pain",
                "confidence": 0.65,
            },
            {
                "opportunity_id": "opp_undecided_2",
                "pain_summary": "Month-end reporting need",
                "confidence": 0.4,
            },
        ]
        package = _package_to_dict(
            decisions=decisions,
            opportunity_candidates=opp_candidates,
        )
        actions = build_next_best_founder_actions(package)

        # undecided_1 should produce review actions (confidence >= 0.5)
        review_actions = [a for a in actions if a.action_type == "review_undecided_opportunity"]
        self.assertTrue(any("opp_undecided_1" in a.rationale for a in review_actions))

        # undecided_2 (confidence 0.4 < 0.5) should NOT produce validation actions
        self.assertFalse(any("opp_undecided_2" in a.rationale for a in review_actions))


class PreferenceProfileActionTests(unittest.TestCase):
    def test_preference_profile_warnings_produce_actions(self):
        decisions = [
            _make_test_decision("opp_p1", PROMOTE, ["strong_pain", "clear_buyer"], 0.8),
            _make_test_decision("opp_k1", KILL, ["too_generic"], 0.7),
            _make_test_decision("opp_k2", KILL, ["no_buyer"], 0.6),
        ]
        feedback_mappings = [map_founder_decision_to_feedback(d) for d in decisions]
        profile = build_founder_preference_profile(decisions, feedback_mappings)
        package = _package_to_dict(
            decisions=decisions,
            feedback_mappings=feedback_mappings,
            preference_profile=profile,
        )
        actions = build_next_best_founder_actions(package)

        warn_actions = [a for a in actions if a.action_type == "review_preference_warning"]
        self.assertGreaterEqual(len(warn_actions), 1)
        for a in warn_actions:
            self.assertTrue(a.advisory_only)

    def test_suggested_queries_produce_actions(self):
        decisions = [
            _make_test_decision("opp_p1", PROMOTE, ["strong_pain", "clear_buyer"], 0.8),
        ]
        feedback_mappings = [map_founder_decision_to_feedback(d) for d in decisions]
        profile = build_founder_preference_profile(decisions, feedback_mappings)
        package = _package_to_dict(
            decisions=decisions,
            feedback_mappings=feedback_mappings,
            preference_profile=profile,
        )
        actions = build_next_best_founder_actions(package)

        query_actions = [a for a in actions if a.action_type == "run_customer_voice_queries"]
        self.assertGreaterEqual(len(query_actions), 1)
        for a in query_actions:
            self.assertTrue(a.advisory_only)
            self.assertIn("customer-voice", a.rationale.lower())


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


class DeterminismTests(unittest.TestCase):
    def test_same_input_produces_same_output(self):
        decisions = [
            _make_test_decision("opp_p", PROMOTE, ["strong_pain", "worth_interviews"], 0.85),
            _make_test_decision("opp_k", KILL, ["too_generic"], 0.9),
            _make_test_decision("opp_r", REVISIT_LATER, ["waiting_for_more_signals"], 0.4),
        ]
        package = _package_to_dict(decisions=decisions)

        actions1 = build_next_best_founder_actions(package)
        actions2 = build_next_best_founder_actions(package)

        self.assertEqual(len(actions1), len(actions2))
        for a1, a2 in zip(actions1, actions2):
            self.assertEqual(a1.action_id, a2.action_id)
            self.assertEqual(a1.action_type, a2.action_type)
            self.assertEqual(a1.priority, a2.priority)
            self.assertEqual(a1.title, a2.title)

    def test_ordering_is_deterministic(self):
        decisions = [
            _make_test_decision("opp_b", PROMOTE, ["strong_pain"], 0.7),
            _make_test_decision("opp_a", PROMOTE, ["clear_buyer"], 0.9),
            _make_test_decision("opp_c", KILL, ["no_buyer"], 0.8),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        # Verify ordering: priority asc, then action_type, then action_id
        for i in range(len(actions) - 1):
            self.assertLessEqual(
                (actions[i].priority, actions[i].action_type, actions[i].action_id),
                (actions[i + 1].priority, actions[i + 1].action_type, actions[i + 1].action_id),
            )


# ---------------------------------------------------------------------------
# Priority ordering tests
# ---------------------------------------------------------------------------


class PriorityOrderingTests(unittest.TestCase):
    def test_high_priority_actions_come_first(self):
        decisions = [
            _make_test_decision("opp_p", PROMOTE, ["strong_pain"], 0.85),
            _make_test_decision("opp_r", REVISIT_LATER, ["waiting_for_more_signals"], 0.4),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        # First action should be high priority (promote -> review_promote_candidate)
        if actions:
            self.assertEqual(actions[0].priority, PRIORITY_HIGH)

    def test_low_priority_actions_come_later(self):
        decisions = [
            _make_test_decision("opp_park", PARK, ["weak_evidence"], 0.5),
            _make_test_decision("opp_rev", REVISIT_LATER, ["waiting_for_more_signals"], 0.4),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        # Park and revisit should be normal or low
        for a in actions:
            self.assertIn(a.priority, (PRIORITY_NORMAL, PRIORITY_LOW))


# ---------------------------------------------------------------------------
# Traceability tests
# ---------------------------------------------------------------------------


class TraceabilityTests(unittest.TestCase):
    def test_actions_preserve_linked_ids(self):
        decisions = [
            _make_test_decision("opp_x", PROMOTE, ["strong_pain"], 0.8),
            _make_test_decision("opp_y", PARK, ["weak_evidence"], 0.5),
        ]
        opp_candidates = [
            {"opportunity_id": "opp_z", "pain_summary": "test", "confidence": 0.6},
        ]
        package = _package_to_dict(
            decisions=decisions,
            opportunity_candidates=opp_candidates,
        )
        actions = build_next_best_founder_actions(package)

        promote_actions = [a for a in actions if a.action_type == "review_promote_candidate"]
        for a in promote_actions:
            self.assertTrue(a.linked_decision_ids, f"Action {a.action_id} missing linked_decision_ids")
            self.assertTrue(a.linked_opportunity_ids, f"Action {a.action_id} missing linked_opportunity_ids")

    def test_every_action_has_action_id(self):
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain"], 0.8),
            _make_test_decision("opp_b", KILL, ["too_generic"], 0.7),
            _make_test_decision("opp_c", REVISIT_LATER, ["waiting_for_more_signals"], 0.4),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        self.assertGreater(len(actions), 0)
        for a in actions:
            self.assertTrue(a.action_id, f"Action missing action_id")
            self.assertTrue(a.action_id.startswith("founder_action_"))

    def test_every_action_has_suggested_next_step(self):
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain"], 0.8),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        for a in actions:
            self.assertTrue(a.suggested_next_step, f"Action {a.action_id} missing suggested_next_step")


# ---------------------------------------------------------------------------
# JSON serialization tests
# ---------------------------------------------------------------------------


class SerializationTests(unittest.TestCase):
    def test_json_serialization(self):
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain"], 0.8),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        json_str = next_best_actions_to_json(actions)
        self.assertIsInstance(json_str, str)
        self.assertGreater(len(json_str), 0)

        data = json.loads(json_str)
        self.assertIsInstance(data, list)
        for item in data:
            self.assertIn("action_id", item)
            self.assertIn("action_type", item)
            self.assertIn("advisory_only", item)
            self.assertTrue(item["advisory_only"])

    def test_json_roundtrip(self):
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain"], 0.8),
            _make_test_decision("opp_b", KILL, ["too_generic"], 0.7),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        json_str = next_best_actions_to_json(actions)
        data = json.loads(json_str)
        restored = [FounderAction.from_dict(item) for item in data]

        self.assertEqual(len(restored), len(actions))
        for orig, rest in zip(actions, restored):
            self.assertEqual(orig.action_id, rest.action_id)
            self.assertEqual(orig.action_type, rest.action_type)
            self.assertEqual(orig.priority, rest.priority)
            self.assertTrue(rest.advisory_only)


# ---------------------------------------------------------------------------
# Markdown rendering tests
# ---------------------------------------------------------------------------


class MarkdownRenderingTests(unittest.TestCase):
    def test_markdown_rendering_with_actions(self):
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain", "worth_interviews"], 0.85),
            _make_test_decision("opp_b", KILL, ["too_generic"], 0.7),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        md = render_next_best_actions_markdown(actions)
        self.assertIn("# Next Best Founder Actions", md)
        self.assertIn("opp_a", md)
        self.assertIn("Advisory only", md)
        self.assertIn("review_promote_candidate", md)
        self.assertIn("consider_kill_candidate", md)

    def test_markdown_rendering_empty(self):
        md = render_next_best_actions_markdown([])
        self.assertIn("# Next Best Founder Actions", md)
        self.assertIn("No actions to recommend", md)

    def test_markdown_includes_traceability(self):
        decisions = [
            _make_test_decision("opp_x", PROMOTE, ["strong_pain"], 0.8),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        md = render_next_best_actions_markdown(actions)
        self.assertIn("Decision IDs", md)
        self.assertIn("Opportunity IDs", md)
        self.assertIn("Evidence IDs", md)


# ---------------------------------------------------------------------------
# Integration: weekly review package -> actions
# ---------------------------------------------------------------------------


class WeeklyReviewIntegrationTests(unittest.TestCase):
    def test_full_package_produces_actions_for_all_sections(self):
        decisions = [
            _make_test_decision("opp_promote", PROMOTE, ["strong_pain", "worth_interviews"], 0.85),
            _make_test_decision("opp_park", PARK, ["weak_evidence"], 0.5),
            _make_test_decision("opp_kill", KILL, ["too_generic", "no_buyer"], 0.9),
            _make_test_decision("opp_revisit", REVISIT_LATER, ["waiting_for_more_signals"], 0.4),
            _make_test_decision("opp_nme", NEEDS_MORE_EVIDENCE, ["need_customer_voice"], 0.55),
        ]
        feedback_mappings = [map_founder_decision_to_feedback(d) for d in decisions]
        profile = build_founder_preference_profile(decisions, feedback_mappings)
        opp_candidates = [
            {"opportunity_id": "opp_undec", "pain_summary": "test pain", "confidence": 0.65},
        ]
        package = _package_to_dict(
            decisions=decisions,
            feedback_mappings=feedback_mappings,
            preference_profile=profile,
            opportunity_candidates=opp_candidates,
        )
        actions = build_next_best_founder_actions(package)

        self.assertGreater(len(actions), 0)

        # Verify all actions are advisory_only
        for a in actions:
            self.assertTrue(a.advisory_only, f"Action {a.action_id} must be advisory_only")

        # Verify we have coverage across expected types
        action_types = {a.action_type for a in actions}
        expected_types = {
            "review_promote_candidate",
            "collect_more_evidence",
            "consider_kill_candidate",
            "revisit_parked_opportunity",
            "interview_customer",
            "review_preference_warning",
            "run_customer_voice_queries",
            "review_undecided_opportunity",
        }
        found_expected = action_types & expected_types
        self.assertGreaterEqual(
            len(found_expected), 3,
            f"Expected at least 3 of {expected_types}, got {action_types}",
        )

    def test_no_autonomous_decisions(self):
        """Verify no action claims autonomous decision-making authority."""
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain"], 0.8),
        ]
        package = _package_to_dict(decisions=decisions)
        actions = build_next_best_founder_actions(package)

        for a in actions:
            self.assertTrue(a.advisory_only)
            self.assertNotEqual(a.action_type, "auto_promote")
            self.assertNotIn("autonomous", a.action_type.lower())
            self.assertNotIn("autonomous", a.rationale.lower())
