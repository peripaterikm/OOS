"""Tests for Deterministic Opportunity Synthesis (v2.14 item 6).

Covers:
A. Contract / serialization
B. Eligibility gates
C. Grounding (problem statement, no invented data)
D. Validation actions
E. Founder Review Package integration
F. Operational regression
"""

import json
import unittest
from datetime import datetime, timezone

import sys
sys.path.insert(0, "src")

from oos.opportunity_synthesis import (
    ALLOWED_CONFIDENCE_LEVELS,
    ALLOWED_VALIDATION_ACTIONS,
    CREATED_BY,
    SCHEMA_VERSION,
    OpportunityHypothesis,
    render_opportunity_hypotheses_markdown,
    synthesize_opportunities,
    _cluster_is_eligible,
    _derive_title,
    _derive_problem_statement,
    _derive_validation_action,
    _determine_confidence,
)
from oos.noise_classifier import compute_evidence_quality_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXED_TS = "2026-05-16T10:00:00Z"


def _make_evidence(
    evidence_id: str = "ev_001",
    source_id: str = "hacker_news",
    source_type: str = "discussion",
    source_url: str = "https://news.ycombinator.com/item?id=40000001",
    title: str = "Debugging LLM agent execution traces is painful",
    excerpt: str = "We struggle to trace multi-step agent runs. No tooling exists.",
    evidence_kind: str = "pain_signal_candidate",
    quality_flags: list[str] | None = None,
    body: str | None = None,
) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "title": title,
        "excerpt": excerpt,
        "evidence_kind": evidence_kind,
        "quality_flags": quality_flags or [],
        "body": body if body is not None else excerpt,
        "created_at": "2026-05-10T12:00:00Z",
    }


def _make_cluster(
    cluster_id: str = "pc_abc123",
    title: str = "Debugging LLM Agent Execution Traces",
    cluster_title: str = "",
    actor: str = "AI developers",
    workflow: str = "debugging LLM agents",
    object: str = "agent traces",
    pain_pattern: str = "AI developers struggle to debug multi-step LLM agent runs because no standard tooling exists for trace replay and provenance",
    evidence_list: list[dict] | None = None,
    source_diversity: int = 2,
    recurrence: int = 3,
    cohesion_score: float = 0.7,
    catch_all_risk: bool = False,
    overall_score: float = 0.75,
    promotion_blockers: list[str] | None = None,
) -> dict:
    return {
        "cluster_id": cluster_id,
        "title": title,
        "cluster_title": cluster_title or title,
        "actor": actor,
        "workflow": workflow,
        "object": object,
        "pain_pattern": pain_pattern,
        "source_evidence_list": evidence_list or [],
        "source_diversity": source_diversity,
        "recurrence": recurrence,
        "cohesion_score": cohesion_score,
        "catch_all_risk": catch_all_risk,
        "scoring": {"overall": overall_score},
        "promotion_blockers": promotion_blockers or [],
    }


def _make_review_item(
    review_item_id: str = "ri_abc123",
    pain_cluster_id: str = "pc_abc123",
    recommended_decision: str = "PROMOTE",
    promotion_blockers: list[str] | None = None,
) -> dict:
    return {
        "review_item_id": review_item_id,
        "pain_cluster_id": pain_cluster_id,
        "recommended_decision": recommended_decision,
        "promotion_blockers": promotion_blockers or [],
    }


# ---------------------------------------------------------------------------
# A. Contract / Serialization
# ---------------------------------------------------------------------------


class OpportunityHypothesisContractTests(unittest.TestCase):
    """Test A: Contract, serialization, required fields."""

    def test_to_dict_from_dict_roundtrip(self):
        oh = OpportunityHypothesis(
            opportunity_id="opph_test1234",
            source_cluster_ids=["pc_abc123"],
            source_review_item_ids=["ri_abc123"],
            title="Agent Debugging Workbench",
            problem_statement="Developers struggle to debug LLM agent traces.",
            target_icp="AI developers",
            target_actor="AI developers",
            workflow_context="debugging LLM agents / agent traces",
            pain_summary="Pain around agent trace debugging.",
            evidence_summary="3 items from 2 sources",
            evidence_links=[
                {"evidence_id": "ev_001", "source_url": "https://example.com/1"}
            ],
            source_diversity=2,
            recurrence=3,
            quality_summary={"accepted_evidence_count": 2},
            promotion_blockers=[],
            confidence_level="high",
            uncertainty_notes="",
            suggested_validation_action="interview_5_users",
            validation_questions=["Who can you interview?"],
            not_a_solution_yet=True,
            created_by=CREATED_BY,
            generated_at=_FIXED_TS,
        )
        d = oh.to_dict()
        oh2 = OpportunityHypothesis.from_dict(d)
        self.assertEqual(oh.opportunity_id, oh2.opportunity_id)
        self.assertEqual(oh.title, oh2.title)
        self.assertEqual(oh.confidence_level, oh2.confidence_level)
        self.assertEqual(oh.source_cluster_ids, oh2.source_cluster_ids)
        self.assertEqual(oh.not_a_solution_yet, oh2.not_a_solution_yet)

    def test_required_fields_present(self):
        oh = OpportunityHypothesis(
            opportunity_id="opph_test",
            source_cluster_ids=["pc_x"],
            title="Test",
            problem_statement="Test problem",
        )
        d = oh.to_dict()
        for field in (
            "opportunity_id", "source_cluster_ids", "title", "problem_statement",
            "confidence_level", "not_a_solution_yet", "created_by",
            "generated_at", "schema_version",
        ):
            self.assertIn(field, d, f"Missing field: {field}")

    def test_confidence_level_validation(self):
        with self.assertRaises(ValueError):
            oh = OpportunityHypothesis(
                opportunity_id="opph_x", source_cluster_ids=["pc_x"],
                title="T", problem_statement="P",
                confidence_level="invalid",
            )
            oh.validate()

    def test_validation_action_validation(self):
        with self.assertRaises(ValueError):
            oh = OpportunityHypothesis(
                opportunity_id="opph_x", source_cluster_ids=["pc_x"],
                title="T", problem_statement="P",
                suggested_validation_action="invalid_action",
            )
            oh.validate()

    def test_backward_compatible_defaults(self):
        d = {
            "opportunity_id": "opph_x",
            "source_cluster_ids": ["pc_x"],
            "title": "T",
            "problem_statement": "P",
        }
        oh = OpportunityHypothesis.from_dict(d)
        self.assertEqual(oh.confidence_level, "low")
        self.assertEqual(oh.created_by, CREATED_BY)
        self.assertEqual(oh.not_a_solution_yet, True)
        self.assertEqual(oh.suggested_validation_action, "collect_more_evidence")

    def test_deterministic_ids(self):
        oh1 = OpportunityHypothesis(
            opportunity_id="opph_det", source_cluster_ids=["pc_x"],
            title="T", problem_statement="P",
        )
        oh2 = OpportunityHypothesis.from_dict(oh1.to_dict())
        self.assertEqual(oh1.opportunity_id, oh2.opportunity_id)

    def test_schema_version(self):
        oh = OpportunityHypothesis(
            opportunity_id="opph_sv", source_cluster_ids=["pc_x"],
            title="T", problem_statement="P",
        )
        self.assertEqual(oh.schema_version, SCHEMA_VERSION)


# ---------------------------------------------------------------------------
# B. Eligibility Gates
# ---------------------------------------------------------------------------


class EligibilityGatesTests(unittest.TestCase):
    """Test B: Eligibility gates for synthesis."""

    def test_promote_clean_cross_source_generates(self):
        ev1 = _make_evidence("ev_001", "hacker_news", "discussion")
        ev2 = _make_evidence("ev_002", "github_issues", "issue_tracker",
                             source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(
            evidence_list=[ev1, ev2], source_diversity=2, recurrence=2,
        )
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertTrue(eligible, f"Should be eligible but got: {reason}")

    def test_needs_more_evidence_promising_eligible(self):
        ev1 = _make_evidence("ev_001",
                             excerpt="We struggle with debugging agent traces daily. No tooling.",
                             body="We struggle with debugging agent traces daily. No tooling exists for this workflow pain. It costs us hours.")
        cluster = _make_cluster(
            evidence_list=[ev1], source_diversity=1, recurrence=1,
            overall_score=0.55,
        )
        ri = _make_review_item(recommended_decision="NEEDS_MORE_EVIDENCE")
        eligible, _ = _cluster_is_eligible(cluster, ri)
        self.assertTrue(eligible)

    def test_kill_item_no_hypothesis(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="KILL")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("KILL", reason)

    def test_blocker_heavy_no_hypothesis(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(
            evidence_list=[ev1],
            promotion_blockers=["Source URL traceability failure"],
        )
        ri = _make_review_item(recommended_decision="PROMOTE",
                               promotion_blockers=["Source URL traceability failure"])
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("fatal", reason.lower())

    def test_high_noise_no_hypothesis(self):
        ev1 = _make_evidence("ev_001", quality_flags=["generic_language", "unclear_actor"])
        ev2 = _make_evidence("ev_002", quality_flags=["generic_language", "unclear_actor"])
        cluster = _make_cluster(evidence_list=[ev1, ev2], source_diversity=1, recurrence=2)
        ri = _make_review_item(recommended_decision="PARK")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        # generic+unclear+no pain -> weak classification, zero accepted -> block
        self.assertFalse(eligible)

    def test_catch_all_risk_no_hypothesis(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1], catch_all_risk=True)
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("catch-all", reason.lower())

    def test_product_launch_only_no_hypothesis(self):
        ev1 = _make_evidence("ev_001", evidence_kind="product_launch")
        ev2 = _make_evidence("ev_002", evidence_kind="launch_hype")
        cluster = _make_cluster(evidence_list=[ev1, ev2], source_diversity=1, recurrence=2)
        eligible, reason = _cluster_is_eligible(cluster)
        self.assertFalse(eligible)
        self.assertIn("product_launch", reason.lower())

    def test_low_text_context_all_no_hypothesis(self):
        ev1 = _make_evidence("ev_001", quality_flags=["low_text_context"],
                             excerpt="short", body="short")
        ev2 = _make_evidence("ev_002", quality_flags=["low_text_context"],
                             excerpt="tiny", body="tiny")
        cluster = _make_cluster(evidence_list=[ev1, ev2], source_diversity=1, recurrence=2)
        eligible, reason = _cluster_is_eligible(cluster)
        self.assertFalse(eligible)
        # low_text_context with no pain -> noise, noise_ratio >= 0.5
        self.assertIn("noise", reason.lower())

    def test_weak_only_evidence_needs_more_eligible(self):
        ev1 = _make_evidence("ev_001", quality_flags=["generic_language"],
                             excerpt="some vague text about AI development with specific problem debugging tools",
                             body="some vague text about AI development with specific problem debugging tools causing real hours lost")
        cluster = _make_cluster(
            evidence_list=[ev1], source_diversity=1, recurrence=1,
            overall_score=0.55,
        )
        ri = _make_review_item(recommended_decision="NEEDS_MORE_EVIDENCE")
        eligible, _ = _cluster_is_eligible(cluster, ri)
        self.assertTrue(eligible)

    def test_placeholder_title_no_hypothesis(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(
            title="needs_more_evidence", cluster_title="needs_more_evidence",
            evidence_list=[ev1],
        )
        eligible, reason = _cluster_is_eligible(cluster)
        self.assertFalse(eligible)
        self.assertIn("placeholder", reason.lower())


# ---------------------------------------------------------------------------
# C. Grounding
# ---------------------------------------------------------------------------


class GroundingTests(unittest.TestCase):
    """Test C: Problem statements use evidence, no invented data."""

    def test_problem_statement_uses_cluster_fields(self):
        ev1 = _make_evidence("ev_001", title="Agent trace debugging is hard",
                             excerpt="We struggle with debugging LLM agents because traces are opaque.",
                             body="We struggle with debugging LLM agents because traces are opaque. No tooling exists.")
        cluster = _make_cluster(
            evidence_list=[ev1],
            actor="AI developers",
            workflow="debugging LLM agents",
            pain_pattern="cannot observe multi-step agent runs",
        )
        ps = _derive_problem_statement(cluster)
        self.assertTrue("AI developers" in ps or "debugging" in ps.lower())

    def test_problem_statement_no_invented_competitors(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1])
        ps = _derive_problem_statement(cluster)
        self.assertNotIn("Datadog", ps)
        self.assertNotIn("Sentry", ps)

    def test_problem_statement_no_invented_wtp(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1])
        ps = _derive_problem_statement(cluster)
        self.assertNotIn("willing to pay", ps.lower())
        self.assertNotIn("$", ps)

    def test_title_no_market_claims(self):
        cluster = _make_cluster(title="Agent Debugging Workbench")
        title = _derive_title(cluster)
        self.assertNotIn("$1B", title)
        self.assertNotIn("market", title.lower())

    def test_evidence_links_preserved(self):
        ev1 = _make_evidence("ev_001", source_url="https://example.com/1")
        ev2 = _make_evidence("ev_002", source_url="https://example.com/2")
        cluster = _make_cluster(evidence_list=[ev1, ev2])
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(
            pain_clusters=[cluster],
            review_items=[ri],
            generated_at=_FIXED_TS,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0].evidence_links), 2)
        urls = [el["source_url"] for el in results[0].evidence_links]
        self.assertIn("https://example.com/1", urls)
        self.assertIn("https://example.com/2", urls)

    def test_no_unsupported_icp_claims(self):
        cluster = _make_cluster(actor="unknown")
        title = _derive_title(cluster)
        self.assertNotIn("enterprise", title.lower())


# ---------------------------------------------------------------------------
# D. Validation Actions
# ---------------------------------------------------------------------------


class ValidationActionTests(unittest.TestCase):
    """Test D: Validation action mapping."""

    def test_cross_source_clear_pain_interview(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues",
                             source_type="issue_tracker",
                             source_url="https://github.com/x/y/issues/1")
        # Cross-source + high recurrence cluster without strong workflow/object
        # specificity defaults to interview when evidence is clean.
        cluster = _make_cluster(
            evidence_list=[ev1, ev2], source_diversity=2, recurrence=2,
            workflow="",
            object="",
        )
        qs = compute_evidence_quality_summary([ev1, ev2])
        action, questions = _derive_validation_action(
            cluster, qs, source_diversity=2, recurrence=2,
            confidence_level="high", evidence_kinds={"pain_signal_candidate"},
        )
        self.assertEqual(action, "interview_5_users")
        self.assertTrue(len(questions) >= 1)

    def test_thin_evidence_collect_more(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1], source_diversity=1, recurrence=1)
        qs = compute_evidence_quality_summary([ev1])
        action, questions = _derive_validation_action(
            cluster, qs, source_diversity=1, recurrence=1,
            confidence_level="low", evidence_kinds={"pain_signal_candidate"},
        )
        self.assertEqual(action, "collect_more_evidence")

    def test_workflow_pain_mapping(self):
        ev1 = _make_evidence("ev_001", title="Debugging traces is impossible")
        cluster = _make_cluster(
            evidence_list=[ev1],
            source_diversity=1, recurrence=2,
            workflow="debugging LLM agent traces",
            object="agent execution traces",
        )
        qs = compute_evidence_quality_summary([ev1])
        action, _ = _derive_validation_action(
            cluster, qs, source_diversity=1, recurrence=2,
            confidence_level="medium", evidence_kinds={"pain_signal_candidate"},
        )
        self.assertEqual(action, "workflow_mapping")

    def test_product_launch_heavy_competitor_scan(self):
        ev1 = _make_evidence("ev_001", evidence_kind="product_launch")
        cluster = _make_cluster(evidence_list=[ev1])
        qs = compute_evidence_quality_summary([ev1])
        action, questions = _derive_validation_action(
            cluster, qs, source_diversity=1, recurrence=1,
            confidence_level="low", evidence_kinds={"product_launch", "launch_hype"},
        )
        self.assertEqual(action, "competitor_scan")

    def test_unclear_actor_interview(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(actor="unknown", evidence_list=[ev1],
                                source_diversity=2, recurrence=2)
        qs = compute_evidence_quality_summary([ev1])
        action, _ = _derive_validation_action(
            cluster, qs, source_diversity=2, recurrence=2,
            confidence_level="medium", evidence_kinds={"pain_signal_candidate"},
        )
        self.assertEqual(action, "interview_5_users")


# ---------------------------------------------------------------------------
# E. Founder Review Package Rendering
# ---------------------------------------------------------------------------


class FounderReviewPackageIntegrationTests(unittest.TestCase):
    """Test E: Founder Review Package integration."""

    def test_markdown_includes_opportunity_hypotheses_section(self):
        oh = OpportunityHypothesis(
            opportunity_id="opph_test",
            source_cluster_ids=["pc_test"],
            source_review_item_ids=["ri_test"],
            title="Agent Debugging Workbench",
            problem_statement="Developers struggle to debug LLM agent traces.",
            target_icp="AI developers",
            target_actor="AI developers",
            workflow_context="debugging / traces",
            pain_summary="Pain with agent debugging.",
            evidence_summary="2 items from 2 sources",
            evidence_links=[
                {"evidence_id": "ev_001", "source_url": "https://example.com/1",
                 "title": "Post 1", "source_id": "hacker_news", "source_type": "discussion"}
            ],
            source_diversity=2,
            recurrence=2,
            quality_summary={"accepted_evidence_count": 2},
            confidence_level="high",
            suggested_validation_action="interview_5_users",
            validation_questions=["Who to interview?"],
            generated_at=_FIXED_TS,
        )
        md = render_opportunity_hypotheses_markdown([oh])
        self.assertIn("## Opportunity Hypotheses", md)
        self.assertIn("Agent Debugging Workbench", md)
        self.assertIn("opph_test", md)
        self.assertIn("interview_5_users", md)

    def test_markdown_empty_state(self):
        md = render_opportunity_hypotheses_markdown([])
        self.assertIn("No opportunity hypotheses generated", md)

    def test_markdown_includes_confidence_and_uncertainty(self):
        oh = OpportunityHypothesis(
            opportunity_id="opph_cu",
            source_cluster_ids=["pc_x"],
            title="Test",
            problem_statement="Test problem",
            confidence_level="low",
            uncertainty_notes="Single source only",
            suggested_validation_action="collect_more_evidence",
        )
        md = render_opportunity_hypotheses_markdown([oh])
        self.assertIn("low", md)
        self.assertIn("Single source only", md)

    def test_json_roundtrip_preserves_hypotheses(self):
        oh = OpportunityHypothesis(
            opportunity_id="opph_rt",
            source_cluster_ids=["pc_rt"],
            title="Roundtrip Test",
            problem_statement="Roundtrip problem",
        )
        d = oh.to_dict()
        self.assertIn("opportunity_id", d)
        oh2 = OpportunityHypothesis.from_dict(d)
        self.assertEqual(oh2.title, "Roundtrip Test")


# ---------------------------------------------------------------------------
# F. Operational Regression
# ---------------------------------------------------------------------------


class OperationalRegressionTests(unittest.TestCase):
    """Test F: Operational regression -- no live APIs, pilot passes."""

    def test_no_live_apis(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1], source_diversity=1, recurrence=1,
                                overall_score=0.75)
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(
            pain_clusters=[cluster],
            review_items=[ri],
            generated_at=_FIXED_TS,
        )
        self.assertIsInstance(results, list)

    def test_empty_clusters_no_error(self):
        results = synthesize_opportunities(
            pain_clusters=[],
            review_items=[],
            generated_at=_FIXED_TS,
        )
        self.assertEqual(results, [])

    def test_high_confidence_is_rare(self):
        ev1 = _make_evidence("ev_001", "hacker_news", "discussion")
        ev2 = _make_evidence("ev_002", "github_issues", "issue_tracker",
                             source_url="https://github.com/x/y/issues/1")
        ev3 = _make_evidence("ev_003", "hacker_news", "discussion",
                             source_url="https://news.ycombinator.com/item?id=2")
        cluster = _make_cluster(
            evidence_list=[ev1, ev2, ev3],
            source_diversity=2, recurrence=3, cohesion_score=0.8,
            overall_score=0.85, catch_all_risk=False,
        )
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(
            pain_clusters=[cluster],
            review_items=[ri],
            generated_at=_FIXED_TS,
        )
        self.assertEqual(len(results), 1)
        self.assertIn(results[0].confidence_level, ("high", "medium"))

    def test_diagnostic_only_for_catch_all_marked(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1], catch_all_risk=True)
        eligible, _ = _cluster_is_eligible(cluster)
        self.assertFalse(eligible)

    def test_not_a_solution_yet_always_true(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues",
                             source_type="issue_tracker",
                             source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(evidence_list=[ev1, ev2], source_diversity=2, recurrence=2)
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(
            pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS,
        )
        if results:
            for oh in results:
                self.assertTrue(oh.not_a_solution_yet)

    def test_created_by_deterministic_stub(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues",
                             source_type="issue_tracker",
                             source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(evidence_list=[ev1, ev2], source_diversity=2, recurrence=2)
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(
            pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS,
        )
        if results:
            self.assertEqual(results[0].created_by, CREATED_BY)

    def test_no_hypothesis_from_noise_only_clusters(self):
        ev1 = _make_evidence("ev_001", quality_flags=["bot_generated"])
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="KILL")
        results = synthesize_opportunities(
            pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS,
        )
        self.assertEqual(len(results), 0)

    def test_synthesis_without_review_items_still_works(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues",
                             source_type="issue_tracker",
                             source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(
            evidence_list=[ev1, ev2], source_diversity=2, recurrence=2,
            overall_score=0.75,
        )
        results = synthesize_opportunities(
            pain_clusters=[cluster], review_items=None, generated_at=_FIXED_TS,
        )
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
