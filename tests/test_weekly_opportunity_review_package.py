import json
import unittest
from pathlib import Path

from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    create_founder_decision,
    founder_decision_to_dict,
)
from oos.founder_feedback_mapping import (
    FounderFeedbackMapping,
    founder_feedback_mapping_to_dict,
    map_founder_decision_to_feedback,
)
from oos.founder_preference_profile import (
    FounderPreferenceProfile,
    build_founder_preference_profile,
    founder_preference_profile_to_dict,
)
from oos.weekly_opportunity_review import (
    NO_DECISIONS_AVAILABLE,
    NO_EVIDENCE_PACKS,
    NO_FEEDBACK_AVAILABLE,
    NO_ITEMS_AVAILABLE,
    NO_OPPORTUNITY_CANDIDATES,
    NO_PORTFOLIO_STATES,
    NO_PREFERENCE_PROFILE,
    SECTION_IDS,
    WEEKLY_REVIEW_SCHEMA_VERSION,
    WeeklyOpportunityReviewPackage,
    WeeklyReviewSection,
    WeeklyReviewSectionItem,
    build_weekly_opportunity_review_package,
    render_weekly_review_package_markdown,
    weekly_review_package_to_json,
)


def _make_test_decision(opportunity_id: str, decision: str, reasons: list[str], confidence: float = 0.6):
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


class WeeklyReviewSectionItemTests(unittest.TestCase):
    def test_item_roundtrip_to_dict_and_back(self):
        item = WeeklyReviewSectionItem(
            item_id="test_item",
            summary="test summary",
            source_artifact_type="founder_decision_v2",
            source_artifact_id="fd_abc123",
            linked_decision_ids=["fd_abc123"],
            action_hint="look here",
            urgency="high",
        )
        data = item.to_dict()
        restored = WeeklyReviewSectionItem.from_dict(data)
        self.assertEqual(restored.item_id, "test_item")
        self.assertEqual(restored.summary, "test summary")
        self.assertEqual(restored.urgency, "high")

    def test_item_defaults(self):
        item = WeeklyReviewSectionItem(
            item_id="d", summary="s", source_artifact_type="t", source_artifact_id="a"
        )
        self.assertEqual(item.linked_decision_ids, [])
        self.assertEqual(item.urgency, "normal")
        self.assertEqual(item.action_hint, "")


class WeeklyReviewSectionTests(unittest.TestCase):
    def test_section_roundtrip(self):
        items = [
            WeeklyReviewSectionItem(
                item_id="i1", summary="s1", source_artifact_type="t", source_artifact_id="a"
            )
        ]
        section = WeeklyReviewSection(
            section_id="promote_candidates",
            title="Promote Candidates",
            items=items,
            empty_state="empty",
            source_artifact_counts={"decisions": 3},
        )
        data = section.to_dict()
        restored = WeeklyReviewSection.from_dict(data)
        self.assertEqual(restored.section_id, "promote_candidates")
        self.assertEqual(len(restored.items), 1)
        self.assertEqual(restored.source_artifact_counts, {"decisions": 3})


class WeeklyOpportunityReviewPackageTests(unittest.TestCase):
    def test_empty_package_has_all_sections_with_empty_states(self):
        package = build_weekly_opportunity_review_package()

        self.assertTrue(package.package_id.startswith("weekly_review_"))
        self.assertEqual(package.schema_version, WEEKLY_REVIEW_SCHEMA_VERSION)
        self.assertTrue(package.advisory_only)
        self.assertFalse(package.autonomous_decisions_made)

        section_ids = {s.section_id for s in package.sections}
        self.assertEqual(section_ids, set(SECTION_IDS))

        for section in package.sections:
            self.assertEqual(section.items, [])
            self.assertIsInstance(section.empty_state, str)
            self.assertTrue(len(section.empty_state) > 0)

    def test_decisions_populate_correct_sections(self):
        decisions = [
            _make_test_decision("opp_promote", PROMOTE, ["strong_pain", "worth_interviews"], 0.85),
            _make_test_decision("opp_park", PARK, ["weak_evidence"], 0.5),
            _make_test_decision("opp_kill", KILL, ["too_generic", "no_buyer"], 0.9),
            _make_test_decision("opp_revisit", REVISIT_LATER, ["waiting_for_more_signals"], 0.4),
            _make_test_decision("opp_nme", NEEDS_MORE_EVIDENCE, ["need_customer_voice"], 0.55),
        ]

        package = build_weekly_opportunity_review_package(decisions=decisions)

        self.assertEqual(package.source_decision_ids, sorted([d.decision_id for d in decisions]))
        self.assertEqual(package.decision_summary["total"], 5)
        self.assertEqual(package.decision_summary.get(PROMOTE, 0), 1)
        self.assertEqual(package.decision_summary.get(PARK, 0), 1)
        self.assertEqual(package.decision_summary.get(KILL, 0), 1)
        self.assertEqual(package.decision_summary.get(REVISIT_LATER, 0), 1)
        self.assertEqual(package.decision_summary.get(NEEDS_MORE_EVIDENCE, 0), 1)

        section_map = {s.section_id: s for s in package.sections}

        self.assertEqual(len(section_map["promote_candidates"].items), 1)
        self.assertEqual(section_map["promote_candidates"].items[0].urgency, "high")

        self.assertEqual(len(section_map["park_candidates"].items), 1)
        self.assertEqual(len(section_map["kill_candidates"].items), 1)
        self.assertEqual(len(section_map["revisit_queue"].items), 1)
        self.assertEqual(len(section_map["needs_more_evidence"].items), 1)

        # Top opportunities should include the promote decision
        top_items = section_map["top_opportunities_to_review"].items
        self.assertTrue(any("opp_promote" in i.summary for i in top_items))

        # Evidence gaps from needs_more_evidence
        gap_items = section_map["evidence_gaps"].items
        self.assertTrue(any("need_customer_voice" in i.summary for i in gap_items))

        # Suggested interviews for promote + needs_more_evidence
        interview_items = section_map["suggested_interviews_or_validation"].items
        self.assertTrue(any("opp_promote" in i.summary for i in interview_items))
        self.assertTrue(any("opp_nme" in i.summary for i in interview_items))

    def test_preference_profile_populates_warnings_and_queries(self):
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain", "clear_buyer"], 0.8),
            _make_test_decision("opp_b", KILL, ["too_generic"], 0.7),
            _make_test_decision("opp_c", KILL, ["no_buyer"], 0.6),
        ]
        feedback_mappings = [map_founder_decision_to_feedback(d) for d in decisions]
        profile = build_founder_preference_profile(decisions, feedback_mappings)

        package = build_weekly_opportunity_review_package(
            decisions=decisions,
            feedback_mappings=feedback_mappings,
            preference_profile=profile,
        )

        section_map = {s.section_id: s for s in package.sections}

        # Profile warnings section should have items (many_kills_no_promote + recurring_kill_patterns)
        warn_section = section_map["preference_profile_warnings"]
        self.assertTrue(len(warn_section.items) >= 1)

        # Suggested next queries should include preferred pain types from profile
        query_section = section_map["suggested_next_queries"]
        # Profile should derive preferred pain types from promote decision
        self.assertTrue(len(query_section.items) >= 1)

    def test_opportunity_candidates_appear_in_top_review_and_validation(self):
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

        package = build_weekly_opportunity_review_package(
            decisions=decisions,
            opportunity_candidates=opp_candidates,
        )

        section_map = {s.section_id: s for s in package.sections}

        top_items = section_map["top_opportunities_to_review"].items
        self.assertTrue(any("opp_undecided_1" in i.item_id for i in top_items))
        self.assertTrue(any("opp_undecided_2" in i.item_id for i in top_items))

        # Validation suggestions for undecided with confidence >= 0.5
        val_items = section_map["suggested_interviews_or_validation"].items
        self.assertTrue(any("opp_undecided_1" in i.summary for i in val_items))
        # opp_undecided_2 has confidence 0.4 < 0.5 so should not appear in validation
        self.assertFalse(any("opp_undecided_2" in i.summary for i in val_items))

    def test_deterministic_ordering(self):
        decisions = [
            _make_test_decision("opp_b", PROMOTE, ["strong_pain"], 0.7),
            _make_test_decision("opp_a", PROMOTE, ["clear_buyer"], 0.9),
            _make_test_decision("opp_c", KILL, ["no_buyer"], 0.8),
        ]

        package1 = build_weekly_opportunity_review_package(decisions=decisions)
        package2 = build_weekly_opportunity_review_package(decisions=decisions)

        # Compare deterministically: skip generated_at which varies per call
        d1 = json.loads(weekly_review_package_to_json(package1))
        d2 = json.loads(weekly_review_package_to_json(package2))
        d1.pop("generated_at", None)
        d2.pop("generated_at", None)
        self.assertEqual(d1, d2)

        # Promote section should have opp_a (higher confidence) first
        promote_section = next(s for s in package1.sections if s.section_id == "promote_candidates")
        self.assertEqual(len(promote_section.items), 2)
        self.assertIn("opp_a", promote_section.items[0].summary)
        self.assertIn("opp_b", promote_section.items[1].summary)

    def test_json_roundtrip(self):
        decisions = [
            _make_test_decision("opp_x", PROMOTE, ["strong_pain"], 0.8),
            _make_test_decision("opp_y", PARK, ["weak_evidence"], 0.5),
        ]
        opp_candidates = [
            {"opportunity_id": "opp_z", "pain_summary": "test", "confidence": 0.6},
        ]

        package = build_weekly_opportunity_review_package(
            decisions=decisions,
            opportunity_candidates=opp_candidates,
        )
        json_str = weekly_review_package_to_json(package)
        data = json.loads(json_str)
        restored = WeeklyOpportunityReviewPackage.from_dict(data)

        self.assertEqual(restored.package_id, package.package_id)
        self.assertEqual(restored.schema_version, package.schema_version)
        self.assertEqual(len(restored.sections), len(package.sections))
        self.assertEqual(restored.decision_summary, package.decision_summary)
        self.assertTrue(restored.advisory_only)
        self.assertFalse(restored.autonomous_decisions_made)

    def test_markdown_rendering(self):
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain", "worth_interviews"], 0.85),
        ]
        package = build_weekly_opportunity_review_package(decisions=decisions)
        md = render_weekly_review_package_markdown(package)

        self.assertIn("# Weekly Opportunity Review Package", md)
        self.assertIn(package.package_id, md)
        self.assertIn("opp_a", md)
        self.assertIn("strong_pain", md)
        self.assertIn("Decision Summary", md)
        self.assertIn("Promote Candidates", md)

    def test_markdown_empty_package(self):
        package = build_weekly_opportunity_review_package()
        md = render_weekly_review_package_markdown(package)

        self.assertIn("No decisions recorded", md)
        for section in package.sections:
            self.assertIn(section.title, md)
            self.assertIn(section.empty_state, md)

    def test_validation_rejects_autonomous_decisions(self):
        package = build_weekly_opportunity_review_package()
        package.autonomous_decisions_made = True
        errors = package.validate()
        self.assertTrue(any("autonomous" in e for e in errors))

    def test_validation_rejects_non_advisory(self):
        package = build_weekly_opportunity_review_package()
        package.advisory_only = False
        errors = package.validate()
        self.assertTrue(any("advisory" in e for e in errors))

    def test_validation_rejects_duplicate_sections(self):
        section = WeeklyReviewSection(
            section_id="promote_candidates",
            title="Test",
            items=[],
        )
        package = WeeklyOpportunityReviewPackage(
            package_id="test",
            generated_at="2025-01-01T00:00:00",
            sections=[section, section],
        )
        errors = package.validate()
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_validation_rejects_missing_sections(self):
        package = WeeklyOpportunityReviewPackage(
            package_id="test",
            generated_at="2025-01-01T00:00:00",
            sections=[],
        )
        errors = package.validate()
        self.assertTrue(any("missing required section" in e for e in errors))

    def test_validation_rejects_unknown_section_ids(self):
        section = WeeklyReviewSection(
            section_id="unknown_section",
            title="Test",
            items=[],
        )
        package = WeeklyOpportunityReviewPackage(
            package_id="test",
            generated_at="2025-01-01T00:00:00",
            sections=list(build_weekly_opportunity_review_package().sections) + [section],
        )
        errors = package.validate()
        self.assertTrue(any("unknown section_id" in e for e in errors))

    def test_package_id_is_stable_for_same_inputs(self):
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain"], 0.8),
        ]
        p1 = build_weekly_opportunity_review_package(decisions=decisions)
        p2 = build_weekly_opportunity_review_package(decisions=decisions)
        self.assertEqual(p1.package_id, p2.package_id)

    def test_package_id_changes_with_different_inputs(self):
        d1 = [_make_test_decision("opp_a", PROMOTE, ["strong_pain"], 0.8)]
        d2 = [_make_test_decision("opp_b", PARK, ["weak_evidence"], 0.5)]

        p1 = build_weekly_opportunity_review_package(decisions=d1)
        p2 = build_weekly_opportunity_review_package(decisions=d2)
        self.assertNotEqual(p1.package_id, p2.package_id)

    def test_all_ids_traceable(self):
        decisions = [
            _make_test_decision("opp_x", PROMOTE, ["strong_pain"], 0.8),
        ]
        opp_candidates = [
            {"opportunity_id": "opp_u", "pain_summary": "test", "confidence": 0.6},
        ]
        package = build_weekly_opportunity_review_package(
            decisions=decisions,
            opportunity_candidates=opp_candidates,
        )

        for section in package.sections:
            for item in section.items:
                self.assertTrue(
                    item.source_artifact_id, f"item {item.item_id} missing source_artifact_id"
                )
                self.assertTrue(
                    item.source_artifact_type, f"item {item.item_id} missing source_artifact_type"
                )
                if item.linked_decision_ids:
                    for did in item.linked_decision_ids:
                        self.assertIn(did, package.source_decision_ids)
                if item.linked_opportunity_ids:
                    for oid in item.linked_opportunity_ids:
                        self.assertTrue(
                            oid in package.source_opportunity_ids
                            or any(d.opportunity_id == oid for d in decisions)
                        )

    def test_section_item_count_in_source_artifact_counts(self):
        decisions = [
            _make_test_decision("opp_a", PROMOTE, ["strong_pain"], 0.8),
        ]
        package = build_weekly_opportunity_review_package(decisions=decisions)

        for section in package.sections:
            self.assertIsInstance(section.source_artifact_counts, dict)
            for v in section.source_artifact_counts.values():
                self.assertGreaterEqual(v, 0)

    def test_dict_decision_inputs_accepted(self):
        d = _make_test_decision("opp_d", PROMOTE, ["strong_pain"], 0.8)
        decisions_dicts = [founder_decision_to_dict(d)]

        package = build_weekly_opportunity_review_package(decisions=decisions_dicts)
        self.assertEqual(package.decision_summary.get(PROMOTE, 0), 1)

    def test_dict_feedback_and_profile_inputs_accepted(self):
        d = _make_test_decision("opp_f", PROMOTE, ["strong_pain"], 0.8)
        m = map_founder_decision_to_feedback(d)
        profile = build_founder_preference_profile([d], [m])

        package = build_weekly_opportunity_review_package(
            decisions=[d],
            feedback_mappings=[founder_feedback_mapping_to_dict(m)],
            preference_profile=founder_preference_profile_to_dict(profile),
        )
        self.assertEqual(package.source_preference_profile_id, profile.profile_id)

    def test_kill_candidates_includes_notes(self):
        decisions = [
            _make_test_decision("opp_dead", KILL, ["too_generic", "no_buyer"], 0.9),
        ]
        decisions[0] = create_founder_decision(
            opportunity_id="opp_dead",
            evidence_pack_id="ep_opp_dead",
            decision=KILL,
            reasons=["too_generic", "no_buyer"],
            confidence=0.9,
            notes="This opportunity died because no buyer could be identified.",
            linked_evidence_ids=["ev_1"],
            linked_source_signal_ids=["sig_1"],
            linked_source_urls=["https://example.com/dead"],
        )
        package = build_weekly_opportunity_review_package(decisions=decisions)
        kill_section = next(s for s in package.sections if s.section_id == "kill_candidates")
        self.assertEqual(len(kill_section.items), 1)
        self.assertIn("no buyer", kill_section.items[0].summary)
        self.assertIn("opp_dead", kill_section.items[0].summary)


if __name__ == "__main__":
    unittest.main()
