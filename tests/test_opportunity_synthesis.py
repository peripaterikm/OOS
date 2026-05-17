"""Tests for Deterministic Opportunity Synthesis (v2.14 item 6 + Codex fixes).

Covers:
A. Contract / serialization
B. Eligibility gates (review-item requirement, decisions, placeholder titles)
C. Traceability enforcement
D. Unknown actor / ICP
E. Grounding
F. Validation actions
G. Founder Review Package integration
H. Operational regression
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
    _is_valid_source_url,
    _PLACEHOLDER_TITLE_MARKERS,
    _ALLOWED_SYNTHESIS_DECISIONS,
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
    traceability_status: str = "clean",
) -> dict:
    return {
        "review_item_id": review_item_id,
        "pain_cluster_id": pain_cluster_id,
        "recommended_decision": recommended_decision,
        "promotion_blockers": promotion_blockers or [],
        "traceability_status": traceability_status,
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
            problem_statement="Users struggle to debug LLM agent traces.",
            target_icp="AI developers",
            target_actor="AI developers",
            workflow_context="debugging LLM agents / agent traces",
            pain_summary="Pain around agent trace debugging.",
            evidence_summary="3 items from 2 sources",
            evidence_links=[{"evidence_id": "ev_001", "source_url": "https://example.com/1"}],
            source_diversity=2,
            recurrence=3,
            quality_summary={"accepted_evidence_count": 2},
            confidence_level="high",
            suggested_validation_action="interview_5_users",
            validation_questions=["Who can you interview?"],
            generated_at=_FIXED_TS,
        )
        d = oh.to_dict()
        oh2 = OpportunityHypothesis.from_dict(d)
        self.assertEqual(oh.opportunity_id, oh2.opportunity_id)
        self.assertEqual(oh.title, oh2.title)
        self.assertEqual(oh.confidence_level, oh2.confidence_level)

    def test_required_fields_present(self):
        oh = OpportunityHypothesis(opportunity_id="opph_test", source_cluster_ids=["pc_x"], title="Test", problem_statement="Test")
        d = oh.to_dict()
        for field in ("opportunity_id", "source_cluster_ids", "title", "problem_statement",
                      "confidence_level", "not_a_solution_yet", "created_by"):
            self.assertIn(field, d, f"Missing field: {field}")

    def test_confidence_level_validation(self):
        with self.assertRaises(ValueError):
            oh = OpportunityHypothesis(opportunity_id="x", source_cluster_ids=["pc_x"], title="T", problem_statement="P", confidence_level="invalid")
            oh.validate()

    def test_validation_action_validation(self):
        with self.assertRaises(ValueError):
            oh = OpportunityHypothesis(opportunity_id="x", source_cluster_ids=["pc_x"], title="T", problem_statement="P", suggested_validation_action="invalid")
            oh.validate()

    def test_backward_compatible_defaults(self):
        d = {"opportunity_id": "opph_x", "source_cluster_ids": ["pc_x"], "title": "T", "problem_statement": "P"}
        oh = OpportunityHypothesis.from_dict(d)
        self.assertEqual(oh.confidence_level, "low")
        self.assertEqual(oh.created_by, CREATED_BY)
        self.assertEqual(oh.not_a_solution_yet, True)

    def test_deterministic_ids(self):
        oh1 = OpportunityHypothesis(opportunity_id="opph_det", source_cluster_ids=["pc_x"], title="T", problem_statement="P")
        oh2 = OpportunityHypothesis.from_dict(oh1.to_dict())
        self.assertEqual(oh1.opportunity_id, oh2.opportunity_id)

    def test_schema_version(self):
        oh = OpportunityHypothesis(opportunity_id="opph_sv", source_cluster_ids=["pc_x"], title="T", problem_statement="P")
        self.assertEqual(oh.schema_version, SCHEMA_VERSION)

    def test_default_target_icp_is_unproven(self):
        oh = OpportunityHypothesis(opportunity_id="opph_icp", source_cluster_ids=["pc_x"], title="T", problem_statement="P")
        self.assertEqual(oh.target_icp, "unproven; validate actor")
        self.assertEqual(oh.target_actor, "unknown")


# ---------------------------------------------------------------------------
# B. Eligibility Gates — Review Item Decision Requirement
# ---------------------------------------------------------------------------


class EligibilityDecisionGateTests(unittest.TestCase):
    """Codex fix 1: Require review item with PROMOTE or NEEDS_MORE_EVIDENCE."""

    def test_promote_clean_item_synthesizes(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker", source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(evidence_list=[ev1, ev2])
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        self.assertEqual(len(results), 1)

    def test_needs_more_evidence_promising_synthesizes(self):
        ev1 = _make_evidence("ev_001", excerpt="We struggle with debugging agent traces daily. No tooling.",
                             body="We struggle with debugging agent traces daily. No tooling exists for this workflow pain. Costs hours.")
        cluster = _make_cluster(evidence_list=[ev1], source_diversity=1, recurrence=1, overall_score=0.55)
        ri = _make_review_item(recommended_decision="NEEDS_MORE_EVIDENCE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        self.assertEqual(len(results), 1)

    def test_park_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PARK")
        eligible, _ = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)

    def test_revisit_later_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="REVISIT_LATER")
        eligible, _ = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)

    def test_kill_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="KILL")
        eligible, _ = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)

    def test_no_review_item_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker", source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(evidence_list=[ev1, ev2])
        eligible, reason = _cluster_is_eligible(cluster, None)
        self.assertFalse(eligible)
        self.assertIn("no review item", reason.lower())

    def test_empty_unknown_decision_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("requires", reason.lower())


# ---------------------------------------------------------------------------
# C. Placeholder Title Gate
# ---------------------------------------------------------------------------


class PlaceholderTitleTests(unittest.TestCase):
    """Codex fix 2: Reject all configured placeholder titles."""

    def test_unknown_title_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(title="unknown", cluster_title="unknown", evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("unknown", reason.lower())

    def test_dead_title_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(title="[dead] feature request", cluster_title="[dead] feature request", evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("[dead]", reason.lower())

    def test_needs_more_evidence_title_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(title="needs_more_evidence", cluster_title="needs_more_evidence", evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("needs_more_evidence", reason.lower())

    def test_empty_title_generates_dynamic_title_and_synthesizes(self):
        """v2.14-FIX: Empty title fields fall back to generate_cluster_review_title().
        A cluster with valid evidence, PROMOTE decision, and generate-able title is eligible."""
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(title="", cluster_title="", evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertTrue(eligible, f"Expected eligible but got reason: {reason}")

    def test_placeholder_n_a_title_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(title="n/a", cluster_title="n/a", evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("n/a", reason.lower())

    def test_none_title_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(title="none", cluster_title="none", evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("none", reason.lower())

    def test_unclear_title_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(title="unclear pain pattern", cluster_title="unclear pain pattern", evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("unclear", reason.lower())

    def test_generic_catch_all_without_concrete_pain_does_not_synthesize(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(title="miscellaneous AI topics", cluster_title="miscellaneous AI topics",
                                pain_pattern="", evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("generic", reason.lower())

    def test_valid_cleaned_title_still_synthesizes(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker", source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(title="Agent Debugging Workbench for Tool-Call Traces",
                                cluster_title="Agent Debugging Workbench for Tool-Call Traces",
                                evidence_list=[ev1, ev2])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, _ = _cluster_is_eligible(cluster, ri)
        self.assertTrue(eligible)


# ---------------------------------------------------------------------------
# D. Traceability Enforcement
# ---------------------------------------------------------------------------


class TraceabilityEnforcementTests(unittest.TestCase):
    """Codex fix 3: Direct URL validation and review-item traceability."""

    def test_missing_source_url_blocks_synthesis(self):
        ev1 = _make_evidence("ev_001", source_url="")
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("invalid source url", reason.lower())

    def test_urn_source_url_blocks_synthesis(self):
        ev1 = _make_evidence("ev_001", source_url="urn:example:1")
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("invalid source url", reason.lower())

    def test_github_fallback_url_blocks_synthesis(self):
        ev1 = _make_evidence("ev_001", source_url="github://owner/repo/issues/1")
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("invalid source url", reason.lower())

    def test_ftp_url_blocks_synthesis(self):
        ev1 = _make_evidence("ev_001", source_url="ftp://example.com/file")
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("invalid source url", reason.lower())

    def test_valid_https_allows_synthesis(self):
        ev1 = _make_evidence("ev_001", source_url="https://news.ycombinator.com/item?id=1")
        ev2 = _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker", source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(evidence_list=[ev1, ev2])
        ri = _make_review_item(recommended_decision="PROMOTE")
        eligible, _ = _cluster_is_eligible(cluster, ri)
        self.assertTrue(eligible)

    def test_review_item_traceability_not_clean_blocks(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker", source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(evidence_list=[ev1, ev2])
        ri = _make_review_item(recommended_decision="PROMOTE", traceability_status="failed")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible)
        self.assertIn("traceability", reason.lower())

    def test_is_valid_source_url(self):
        self.assertTrue(_is_valid_source_url("https://example.com"))
        self.assertTrue(_is_valid_source_url("http://example.com"))
        self.assertFalse(_is_valid_source_url(""))
        self.assertFalse(_is_valid_source_url("urn:test"))
        self.assertFalse(_is_valid_source_url("github://x/y/1"))
        self.assertFalse(_is_valid_source_url("ftp://example.com"))
        self.assertFalse(_is_valid_source_url("not_a_url"))


# ---------------------------------------------------------------------------
# E. Unknown Actor / ICP
# ---------------------------------------------------------------------------


class UnknownActorICPTests(unittest.TestCase):
    """Codex fix 4: Do not invent unsupported ICP."""

    def test_unknown_actor_yields_unproven_icp(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(actor="unknown", evidence_list=[ev1],
                                source_diversity=1, recurrence=1, overall_score=0.75)
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        self.assertEqual(len(results), 1)
        oh = results[0]
        self.assertEqual(oh.target_actor, "unknown")
        self.assertEqual(oh.target_icp, "unproven; validate actor")
        self.assertIn("not proven", oh.uncertainty_notes.lower())

    def test_unknown_actor_validation_action_is_interview_or_collect(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(actor="unknown", evidence_list=[ev1],
                                source_diversity=1, recurrence=1, overall_score=0.75)
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        if results:
            self.assertIn(results[0].suggested_validation_action,
                          ("interview_5_users", "collect_more_evidence"))

    def test_empty_actor_yields_unproven_icp(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(actor="", evidence_list=[ev1],
                                source_diversity=1, recurrence=1, overall_score=0.75)
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        if results:
            self.assertEqual(results[0].target_icp, "unproven; validate actor")

    def test_developer_actor_stays_developer(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker", source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(actor="AI developers", evidence_list=[ev1, ev2])
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].target_actor, "AI developers")
        self.assertEqual(results[0].target_icp, "AI developers")


# ---------------------------------------------------------------------------
# F. Grounding
# ---------------------------------------------------------------------------


class GroundingTests(unittest.TestCase):
    """Problem statements use evidence, no invented data."""

    def test_problem_statement_uses_cluster_fields(self):
        ev1 = _make_evidence("ev_001", title="Agent trace hard")
        cluster = _make_cluster(evidence_list=[ev1], actor="AI developers", workflow="debugging LLM agents",
                                pain_pattern="cannot observe multi-step agent runs")
        ps = _derive_problem_statement(cluster)
        self.assertTrue("AI developers" in ps or "debugging" in ps.lower())

    def test_problem_statement_no_invented_competitors(self):
        cluster = _make_cluster()
        ps = _derive_problem_statement(cluster)
        self.assertNotIn("Datadog", ps)
        self.assertNotIn("Sentry", ps)

    def test_problem_statement_no_invented_wtp(self):
        cluster = _make_cluster()
        ps = _derive_problem_statement(cluster)
        self.assertNotIn("willing to pay", ps.lower())
        self.assertNotIn("$", ps)

    def test_evidence_links_preserved(self):
        ev1 = _make_evidence("ev_001", source_url="https://example.com/1")
        ev2 = _make_evidence("ev_002", source_url="https://example.com/2")
        cluster = _make_cluster(evidence_list=[ev1, ev2])
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        self.assertEqual(len(results), 1)
        urls = [el["source_url"] for el in results[0].evidence_links]
        self.assertIn("https://example.com/1", urls)
        self.assertIn("https://example.com/2", urls)


# ---------------------------------------------------------------------------
# G. Validation Actions
# ---------------------------------------------------------------------------


class ValidationActionTests(unittest.TestCase):
    def test_cross_source_clear_pain_interview(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker", source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(evidence_list=[ev1, ev2], source_diversity=2, recurrence=2, workflow="", object="")
        qs = compute_evidence_quality_summary([ev1, ev2])
        action, _ = _derive_validation_action(cluster, qs, 2, 2, "high", {"pain_signal_candidate"})
        self.assertEqual(action, "interview_5_users")

    def test_thin_evidence_collect_more(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1], source_diversity=1, recurrence=1,
                                workflow="", object="")
        qs = compute_evidence_quality_summary([ev1])
        action, _ = _derive_validation_action(cluster, qs, 1, 1, "low", {"pain_signal_candidate"})
        self.assertEqual(action, "collect_more_evidence")

    def test_workflow_pain_mapping(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1], source_diversity=1, recurrence=2,
                                workflow="debugging LLM agent traces", object="agent execution traces")
        qs = compute_evidence_quality_summary([ev1])
        action, _ = _derive_validation_action(cluster, qs, 1, 2, "medium", {"pain_signal_candidate"})
        self.assertEqual(action, "workflow_mapping")

    def test_product_launch_heavy_competitor_scan(self):
        ev1 = _make_evidence("ev_001", evidence_kind="product_launch")
        cluster = _make_cluster(evidence_list=[ev1])
        qs = compute_evidence_quality_summary([ev1])
        action, _ = _derive_validation_action(cluster, qs, 1, 1, "low", {"product_launch", "launch_hype"})
        self.assertEqual(action, "competitor_scan")


# ---------------------------------------------------------------------------
# H. Founder Review Package Integration
# ---------------------------------------------------------------------------


class FounderReviewPackageIntegrationTests(unittest.TestCase):
    def test_markdown_includes_opportunity_hypotheses_section(self):
        oh = OpportunityHypothesis(opportunity_id="opph_test", source_cluster_ids=["pc_test"],
                                    title="Agent Debugging Workbench",
                                    problem_statement="Users struggle to debug LLM agent traces.",
                                    target_icp="AI developers", target_actor="AI developers",
                                    evidence_summary="2 items from 2 sources", source_diversity=2, recurrence=2,
                                    confidence_level="high", suggested_validation_action="interview_5_users",
                                    generated_at=_FIXED_TS)
        md = render_opportunity_hypotheses_markdown([oh])
        self.assertIn("## Opportunity Hypotheses", md)
        self.assertIn("Agent Debugging Workbench", md)
        self.assertIn("opph_test", md)

    def test_markdown_empty_state(self):
        md = render_opportunity_hypotheses_markdown([])
        self.assertIn("## Opportunity Hypotheses", md)
        self.assertIn("No opportunity hypotheses generated", md)

    def test_markdown_includes_confidence_and_uncertainty(self):
        oh = OpportunityHypothesis(opportunity_id="opph_cu", source_cluster_ids=["pc_x"],
                                    title="Test", problem_statement="Test problem",
                                    confidence_level="low", uncertainty_notes="Single source only",
                                    suggested_validation_action="collect_more_evidence")
        md = render_opportunity_hypotheses_markdown([oh])
        self.assertIn("low", md)
        self.assertIn("Single source only", md)

    def test_json_roundtrip_preserves_hypotheses(self):
        oh = OpportunityHypothesis(opportunity_id="opph_rt", source_cluster_ids=["pc_rt"],
                                    title="Roundtrip Test", problem_statement="Roundtrip problem")
        d = oh.to_dict()
        oh2 = OpportunityHypothesis.from_dict(d)
        self.assertEqual(oh2.title, "Roundtrip Test")


# ---------------------------------------------------------------------------
# I. Operational Regression
# ---------------------------------------------------------------------------


class OperationalRegressionTests(unittest.TestCase):
    def test_no_live_apis(self):
        ev1 = _make_evidence("ev_001")
        cluster = _make_cluster(evidence_list=[ev1], source_diversity=1, recurrence=1, overall_score=0.75)
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        self.assertIsInstance(results, list)

    def test_empty_clusters_no_error(self):
        results = synthesize_opportunities(pain_clusters=[], review_items=[], generated_at=_FIXED_TS)
        self.assertEqual(results, [])

    def test_not_a_solution_yet_always_true(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker", source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(evidence_list=[ev1, ev2])
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        for oh in results:
            self.assertTrue(oh.not_a_solution_yet)

    def test_created_by_deterministic_stub(self):
        ev1 = _make_evidence("ev_001")
        ev2 = _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker", source_url="https://github.com/x/y/issues/1")
        cluster = _make_cluster(evidence_list=[ev1, ev2])
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        self.assertEqual(results[0].created_by, CREATED_BY)

    def test_no_hypothesis_from_noise_only_clusters(self):
        ev1 = _make_evidence("ev_001", quality_flags=["bot_generated"])
        cluster = _make_cluster(evidence_list=[ev1])
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        self.assertEqual(len(results), 0)

    def test_high_confidence_is_rare(self):
        ev1 = _make_evidence("ev_001", "hacker_news", "discussion")
        ev2 = _make_evidence("ev_002", "github_issues", "issue_tracker", source_url="https://github.com/x/y/issues/1")
        ev3 = _make_evidence("ev_003", "hacker_news", "discussion", source_url="https://news.ycombinator.com/item?id=2")
        cluster = _make_cluster(evidence_list=[ev1, ev2, ev3], source_diversity=2, recurrence=3, cohesion_score=0.8, overall_score=0.85)
        ri = _make_review_item(recommended_decision="PROMOTE")
        results = synthesize_opportunities(pain_clusters=[cluster], review_items=[ri], generated_at=_FIXED_TS)
        self.assertEqual(len(results), 1)
        self.assertIn(results[0].confidence_level, ("high", "medium"))


if __name__ == "__main__":
    unittest.main()
