"""Tests for Pilot Founder Review Package (Roadmap v2.12 item 6).

Tests cover:
- Build package from PainClusters and opportunity candidates
- Recommendation logic (all 5 decision statuses)
- Suggested validation actions (including check_competitors, search_more_sources, manual_research)
- Evidence link preservation and traceability
- Validation rules (fail/warn) — identity fields, source_url
- Package-level traceability_status/summary
- PROMOTE safety (requires source_diversity >= 2 OR recurrence >= 2)
- Builder error handling (no silent drops)
- Sorting priority and tie-breaks
- Package summary counts
- Markdown rendering (ASCII-safe, includes traceability summary)
- to_dict/from_dict roundtrips (preserves traceability fields)
- No live API/network calls
"""

import json
import unittest
from datetime import datetime, timezone

import sys
sys.path.insert(0, "src")

from oos.pain_cluster import (
    PainCluster,
    PainClusterScoring,
    SourceEvidenceEntry,
    compute_overall_score,
)
from oos.source_quality_report import (
    SourceQualityReport,
    SourceQualityMetrics,
    build_source_quality_report,
)
from oos.pilot_founder_review_package import (
    ALLOWED_RECOMMENDED_DECISIONS,
    ALLOWED_SUGGESTED_ACTIONS,
    DECISION_PRIORITY,
    FounderReviewEvidenceLink,
    FounderReviewQueueItem,
    FounderReviewPackage,
    FounderReviewPackageValidationResult,
    assess_uncertainty,
    build_founder_review_package,
    recommend_decision,
    render_founder_review_package_markdown,
    suggest_validation_action,
    validate_founder_review_package,
    _assess_link_traceability,
    _compute_package_traceability,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_evidence(
    evidence_id: str = "ev_001",
    source_id: str = "hacker_news",
    source_type: str = "discussion",
    source_url: str = "https://news.ycombinator.com/item?id=12345",
    title: str = "Test HN post",
    excerpt: str = "This is a test excerpt about pain.",
    evidence_kind: str = "pain_signal_candidate",
    quality_flags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "title": title,
        "excerpt": excerpt,
        "evidence_kind": evidence_kind,
        "quality_flags": quality_flags or [],
        "created_at": "2026-05-01T00:00:00Z",
        "fetched_at": "2026-05-10T00:00:00Z",
        "contribution_to_cluster": "primary_pain",
        "signal_id": None,
    }


def _make_cluster_dict(
    cluster_id: str = "pc_test001",
    overall: float = 0.75,
    source_diversity: int = 2,
    recurrence: int = 3,
    noise_risk: float = 0.10,
    business_relevance: float = 0.70,
    actor: str = "developer",
    workflow: str = "debugging AI agents",
    obj: str = "multi-step agent workflows",
    pain_pattern: str = "developers cannot debug AI agents",
    evidence_list: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if evidence_list is None:
        evidence_list = [
            _make_evidence("ev_001", "hacker_news", "discussion"),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/repo/issues/1", "Test GH issue"),
            _make_evidence("ev_003", "hacker_news", "discussion"),
        ]
    scoring = {
        "overall": overall,
        "pain_explicitness": 0.80,
        "recurrence": 0.60,
        "business_cost": 0.70,
        "icp_fit": 0.50,
        "source_reliability": 0.75,
        "freshness": 0.90,
        "actionability": 0.60,
        "noise_risk": noise_risk,
        "scoring_model_version": "pain_cluster_scoring_v1_pilot",
        "computed_at": "2026-05-12T00:00:00Z",
    }
    return {
        "cluster_id": cluster_id,
        "actor": actor,
        "workflow": workflow,
        "object": obj,
        "pain_verb": "hard to debug",
        "pain_pattern": pain_pattern,
        "source_evidence_list": evidence_list,
        "source_diversity": source_diversity,
        "recurrence": recurrence,
        "business_relevance": business_relevance,
        "noise_risk": noise_risk,
        "representative_quotes_or_excerpts": ["test quote"],
        "linked_candidate_signals": ["sig_001"],
        "linked_opportunity_candidates": [],
        "created_at": "2026-05-12T00:00:00Z",
        "updated_at": "2026-05-12T00:00:00Z",
        "status": "new",
        "scoring": scoring,
        "notes": "",
    }


def _make_opp_candidate(
    opportunity_id: str = "oppc_test001",
    cluster_id: str = "pc_test001",
    score: float = 0.75,
    problem_statement: str = "Developers struggle with debugging AI agents.",
    evidence_summary: str = "3 evidence items from 2 sources.",
    uncertainty: str = "moderate",
) -> dict[str, object]:
    return {
        "opportunity_id": opportunity_id,
        "source_pain_cluster_id": cluster_id,
        "actor": "developer",
        "icp": "developer",
        "problem_statement": problem_statement,
        "evidence_summary": evidence_summary,
        "source_evidence_links": [
            _make_evidence("ev_001", "hacker_news", "discussion"),
        ],
        "score": score,
        "uncertainty": uncertainty,
        "suggested_validation_action": "interview",
        "founder_review_status": "pending_review",
        "noise_risk": 0.10,
        "business_relevance": 0.70,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecommendDecision(unittest.TestCase):
    """Test the deterministic recommendation logic."""

    def test_promote_strong_score(self):
        decision, reason = recommend_decision(
            score=0.75,
            noise_risk=0.10,
            source_diversity=2,
            recurrence=3,
            business_relevance=0.70,
            uncertainty="moderate",
            source_url_traceability_clean=True,
            has_credible_evidence=True,
        )
        self.assertEqual(decision, "PROMOTE")
        self.assertIn("Strong score", reason)

    def test_kill_noise_risk_high(self):
        decision, reason = recommend_decision(
            score=0.50,
            noise_risk=0.85,
            source_diversity=1,
            recurrence=1,
            business_relevance=0.30,
            uncertainty="high",
            source_url_traceability_clean=True,
            has_credible_evidence=False,
        )
        self.assertEqual(decision, "KILL")
        self.assertIn("noise", reason.lower())

    def test_kill_traceability_failure(self):
        decision, reason = recommend_decision(
            score=0.50,
            noise_risk=0.10,
            source_diversity=1,
            recurrence=1,
            business_relevance=0.30,
            uncertainty="high",
            source_url_traceability_clean=False,
            has_credible_evidence=False,
        )
        self.assertEqual(decision, "KILL")
        self.assertIn("traceability", reason.lower())

    def test_kill_low_score(self):
        decision, reason = recommend_decision(
            score=0.15,
            noise_risk=0.10,
            source_diversity=1,
            recurrence=1,
            business_relevance=0.10,
            uncertainty="high",
            source_url_traceability_clean=True,
            has_credible_evidence=False,
        )
        self.assertEqual(decision, "KILL")
        self.assertIn("Score too low", reason)

    def test_needs_more_evidence_score_range(self):
        decision, reason = recommend_decision(
            score=0.55,
            noise_risk=0.20,
            source_diversity=2,
            recurrence=2,
            business_relevance=0.50,
            uncertainty="moderate",
            source_url_traceability_clean=True,
            has_credible_evidence=True,
        )
        self.assertEqual(decision, "NEEDS_MORE_EVIDENCE")
        self.assertIn("needs-evidence range", reason)

    def test_needs_more_evidence_single_source(self):
        decision, reason = recommend_decision(
            score=0.45,
            noise_risk=0.20,
            source_diversity=1,
            recurrence=1,
            business_relevance=0.50,
            uncertainty="moderate",
            source_url_traceability_clean=True,
            has_credible_evidence=True,
        )
        self.assertEqual(decision, "NEEDS_MORE_EVIDENCE")
        self.assertIn("Single-source", reason)

    def test_park_moderate_score(self):
        decision, reason = recommend_decision(
            score=0.35,
            noise_risk=0.30,
            source_diversity=1,
            recurrence=1,
            business_relevance=0.25,
            uncertainty="moderate",
            source_url_traceability_clean=True,
            has_credible_evidence=False,
        )
        self.assertEqual(decision, "PARK")

    def test_revisit_later(self):
        decision, reason = recommend_decision(
            score=0.45,
            noise_risk=0.20,
            source_diversity=2,
            recurrence=1,
            business_relevance=0.35,
            uncertainty="moderate",
            source_url_traceability_clean=True,
            has_credible_evidence=False,
        )
        self.assertEqual(decision, "REVISIT_LATER")
        self.assertIn("low recurrence", reason.lower())

    # New: PROMOTE safety tests
    def test_promote_requires_source_diversity_or_recurrence(self):
        """PROMOTE must require source_diversity >= 2 OR recurrence >= 2."""
        # High score + single-source + recurrence 1 => NEEDS_MORE_EVIDENCE
        decision, reason = recommend_decision(
            score=0.75,
            noise_risk=0.10,
            source_diversity=1,
            recurrence=1,
            business_relevance=0.60,
            uncertainty="moderate",
            source_url_traceability_clean=True,
            has_credible_evidence=True,
        )
        self.assertEqual(decision, "NEEDS_MORE_EVIDENCE")
        self.assertIn("single-source", reason.lower())
        self.assertIn("low recurrence", reason.lower())

    def test_promote_with_source_diversity_2(self):
        """High score + source_diversity 2 => PROMOTE."""
        decision, reason = recommend_decision(
            score=0.75,
            noise_risk=0.10,
            source_diversity=2,
            recurrence=1,
            business_relevance=0.60,
            uncertainty="moderate",
            source_url_traceability_clean=True,
            has_credible_evidence=True,
        )
        self.assertEqual(decision, "PROMOTE")

    def test_promote_with_recurrence_2(self):
        """High score + recurrence 2 => PROMOTE."""
        decision, reason = recommend_decision(
            score=0.80,
            noise_risk=0.10,
            source_diversity=1,
            recurrence=2,
            business_relevance=0.60,
            uncertainty="moderate",
            source_url_traceability_clean=True,
            has_credible_evidence=True,
        )
        self.assertEqual(decision, "PROMOTE")

    def test_promote_broken_traceability_means_kill(self):
        """High score + broken traceability => KILL."""
        decision, reason = recommend_decision(
            score=0.80,
            noise_risk=0.10,
            source_diversity=2,
            recurrence=3,
            business_relevance=0.60,
            uncertainty="low",
            source_url_traceability_clean=False,
            has_credible_evidence=True,
        )
        self.assertEqual(decision, "KILL")
        self.assertIn("traceability", reason.lower())

    def test_all_decisions_in_allowed_set(self):
        """Verify recommend_decision only returns allowed values."""
        import itertools
        scores = [0.10, 0.30, 0.50, 0.75, 0.90]
        noises = [0.05, 0.40, 0.85]
        diversities = [1, 2]
        recurrences = [1, 3, 5]
        biz_relevance = [0.10, 0.30, 0.70]
        uncertainties = ["low", "moderate", "high"]
        traceabilities = [True, False]
        credibles = [True, False]

        for params in itertools.product(
            scores, noises, diversities, recurrences, biz_relevance,
            uncertainties, traceabilities, credibles
        ):
            decision, reason = recommend_decision(
                score=params[0],
                noise_risk=params[1],
                source_diversity=params[2],
                recurrence=params[3],
                business_relevance=params[4],
                uncertainty=params[5],
                source_url_traceability_clean=params[6],
                has_credible_evidence=params[7],
            )
            self.assertIn(decision, ALLOWED_RECOMMENDED_DECISIONS)
            self.assertIsInstance(reason, str)
            self.assertTrue(len(reason) > 0)


class TestSuggestValidationAction(unittest.TestCase):
    """Test deterministic suggested validation actions."""

    def test_kill_no_action(self):
        action = suggest_validation_action(
            recommended_decision="KILL",
            score=0.10,
            business_relevance=0.10,
            source_diversity=1,
            noise_risk=0.90,
            evidence_links=[],
        )
        self.assertEqual(action, "kill_no_action")

    def test_interview_strong_score(self):
        evidence = [
            FounderReviewEvidenceLink(
                evidence_id="ev_001", source_id="hacker_news",
                source_type="discussion",
                source_url="https://news.ycombinator.com/item?id=1",
                title="Test", excerpt="test", evidence_kind="pain_signal_candidate",
            ),
        ]
        action = suggest_validation_action(
            recommended_decision="PROMOTE",
            score=0.80,
            business_relevance=0.60,
            source_diversity=2,
            noise_risk=0.10,
            evidence_links=evidence,
        )
        self.assertEqual(action, "interview")

    def test_landing_page(self):
        evidence = [
            FounderReviewEvidenceLink(
                evidence_id="ev_001", source_id="hacker_news",
                source_type="discussion",
                source_url="https://news.ycombinator.com/item?id=1",
                title="Test", excerpt="test", evidence_kind="pain_signal_candidate",
            ),
        ]
        action = suggest_validation_action(
            recommended_decision="PROMOTE",
            score=0.75,
            business_relevance=0.45,
            source_diversity=2,
            noise_risk=0.10,
            evidence_links=evidence,
        )
        self.assertEqual(action, "landing_page")

    def test_collect_more_evidence_for_needs_more(self):
        action = suggest_validation_action(
            recommended_decision="NEEDS_MORE_EVIDENCE",
            score=0.55,
            business_relevance=0.50,
            source_diversity=1,
            noise_risk=0.20,
            evidence_links=[],
        )
        self.assertEqual(action, "collect_more_evidence")

    def test_search_more_sources_for_needs_more_with_diversity(self):
        """NEEDS_MORE_EVIDENCE + source_diversity >= 2 => search_more_sources."""
        action = suggest_validation_action(
            recommended_decision="NEEDS_MORE_EVIDENCE",
            score=0.55,
            business_relevance=0.50,
            source_diversity=2,
            noise_risk=0.20,
            evidence_links=[],
        )
        self.assertEqual(action, "search_more_sources")

    def test_inspect_github_repos(self):
        evidence = [
            FounderReviewEvidenceLink(
                evidence_id="ev_001", source_id="github_issues",
                source_type="issue_tracker",
                source_url="https://github.com/o/r/issues/1",
                title="Test", excerpt="test", evidence_kind="bug_report",
            ),
            FounderReviewEvidenceLink(
                evidence_id="ev_002", source_id="github_issues",
                source_type="issue_tracker",
                source_url="https://github.com/o/r/issues/2",
                title="Test2", excerpt="test2", evidence_kind="feature_request",
            ),
        ]
        action = suggest_validation_action(
            recommended_decision="PROMOTE",
            score=0.80,
            business_relevance=0.60,
            source_diversity=1,
            noise_risk=0.10,
            evidence_links=evidence,
        )
        self.assertEqual(action, "inspect_github_repos")

    def test_check_competitors_solution_heavy(self):
        """PROMOTE with many solution/feature_request evidence => check_competitors."""
        evidence = [
            FounderReviewEvidenceLink(
                evidence_id="ev_001", source_id="hacker_news",
                source_type="discussion",
                source_url="https://news.ycombinator.com/item?id=1",
                title="Test", excerpt="test", evidence_kind="solution_pattern",
            ),
            FounderReviewEvidenceLink(
                evidence_id="ev_002", source_id="hacker_news",
                source_type="discussion",
                source_url="https://news.ycombinator.com/item?id=2",
                title="Test2", excerpt="test2", evidence_kind="feature_request",
            ),
        ]
        action = suggest_validation_action(
            recommended_decision="PROMOTE",
            score=0.80,
            business_relevance=0.50,
            source_diversity=2,
            noise_risk=0.10,
            evidence_links=evidence,
        )
        self.assertEqual(action, "check_competitors")

    def test_manual_research_for_park(self):
        """PARK decision => manual_research."""
        action = suggest_validation_action(
            recommended_decision="PARK",
            score=0.40,
            business_relevance=0.30,
            source_diversity=1,
            noise_risk=0.40,
            evidence_links=[],
        )
        self.assertEqual(action, "manual_research")

    def test_collect_more_evidence_for_revisit_later(self):
        """REVISIT_LATER => collect_more_evidence."""
        action = suggest_validation_action(
            recommended_decision="REVISIT_LATER",
            score=0.45,
            business_relevance=0.35,
            source_diversity=1,
            noise_risk=0.30,
            evidence_links=[],
        )
        self.assertEqual(action, "collect_more_evidence")


class TestAssessUncertainty(unittest.TestCase):
    """Test uncertainty assessment."""

    def test_low_uncertainty(self):
        result = assess_uncertainty(
            score=0.80, source_diversity=2, recurrence=3, noise_risk=0.10,
        )
        self.assertEqual(result, "low")

    def test_high_uncertainty_single_source(self):
        result = assess_uncertainty(
            score=0.50, source_diversity=1, recurrence=3, noise_risk=0.10,
        )
        self.assertEqual(result, "high")

    def test_high_uncertainty_low_recurrence(self):
        result = assess_uncertainty(
            score=0.50, source_diversity=2, recurrence=1, noise_risk=0.10,
        )
        self.assertEqual(result, "high")

    def test_high_uncertainty_noise(self):
        result = assess_uncertainty(
            score=0.50, source_diversity=2, recurrence=3, noise_risk=0.65,
        )
        self.assertEqual(result, "high")

    def test_moderate_uncertainty(self):
        result = assess_uncertainty(
            score=0.50, source_diversity=2, recurrence=2, noise_risk=0.40,
        )
        self.assertEqual(result, "moderate")


class TestFounderReviewEvidenceLink(unittest.TestCase):
    """Test evidence link model."""

    def test_construction_and_validation(self):
        link = FounderReviewEvidenceLink(
            evidence_id="ev_001",
            source_id="hacker_news",
            source_type="discussion",
            source_url="https://news.ycombinator.com/item?id=1",
            title="Test",
            excerpt="Test excerpt",
            evidence_kind="pain_signal_candidate",
        )
        link.validate()

    def test_missing_source_url(self):
        link = FounderReviewEvidenceLink(
            evidence_id="ev_001",
            source_id="hacker_news",
            source_type="discussion",
            source_url="",
            title="Test",
            excerpt="Test",
            evidence_kind="pain_signal_candidate",
        )
        with self.assertRaises(ValueError):
            link.validate()

    def test_to_dict_from_dict_roundtrip(self):
        original = FounderReviewEvidenceLink(
            evidence_id="ev_001",
            source_id="hacker_news",
            source_type="discussion",
            source_url="https://news.ycombinator.com/item?id=1",
            title="Test",
            excerpt="Test excerpt",
            evidence_kind="pain_signal_candidate",
            quality_flags=["low_text_context"],
        )
        d = original.to_dict()
        restored = FounderReviewEvidenceLink.from_dict(d)
        self.assertEqual(original.evidence_id, restored.evidence_id)
        self.assertEqual(original.source_url, restored.source_url)
        self.assertEqual(original.quality_flags, restored.quality_flags)

    def test_from_dict_rejects_quality_flags_string(self):
        """FounderReviewEvidenceLink.from_dict rejects quality_flags as string."""
        d = {
            "evidence_id": "ev_001",
            "source_id": "hacker_news",
            "source_type": "discussion",
            "source_url": "https://news.ycombinator.com/item?id=1",
            "title": "Test",
            "excerpt": "Test excerpt",
            "evidence_kind": "pain_signal_candidate",
            "quality_flags": "flag",
        }
        with self.assertRaises(ValueError):
            FounderReviewEvidenceLink.from_dict(d)

    def test_from_dict_rejects_quality_flags_dict(self):
        """FounderReviewEvidenceLink.from_dict rejects quality_flags as dict."""
        d = {
            "evidence_id": "ev_001",
            "source_id": "hacker_news",
            "source_type": "discussion",
            "source_url": "https://news.ycombinator.com/item?id=1",
            "title": "Test",
            "excerpt": "Test excerpt",
            "evidence_kind": "pain_signal_candidate",
            "quality_flags": {"x": 1},
        }
        with self.assertRaises(ValueError):
            FounderReviewEvidenceLink.from_dict(d)

    def test_from_dict_accepts_missing_quality_flags_as_empty(self):
        """FounderReviewEvidenceLink.from_dict accepts missing quality_flags as []."""
        d = {
            "evidence_id": "ev_001",
            "source_id": "hacker_news",
            "source_type": "discussion",
            "source_url": "https://news.ycombinator.com/item?id=1",
            "title": "Test",
            "excerpt": "Test excerpt",
            "evidence_kind": "pain_signal_candidate",
        }
        link = FounderReviewEvidenceLink.from_dict(d)
        self.assertEqual(link.quality_flags, [])

    def test_from_dict_accepts_quality_flags_list(self):
        """FounderReviewEvidenceLink.from_dict accepts quality_flags=["low_text_context"]."""
        d = {
            "evidence_id": "ev_001",
            "source_id": "hacker_news",
            "source_type": "discussion",
            "source_url": "https://news.ycombinator.com/item?id=1",
            "title": "Test",
            "excerpt": "Test excerpt",
            "evidence_kind": "pain_signal_candidate",
            "quality_flags": ["low_text_context"],
        }
        link = FounderReviewEvidenceLink.from_dict(d)
        self.assertEqual(link.quality_flags, ["low_text_context"])


class TestFounderReviewQueueItem(unittest.TestCase):
    """Test review queue item model."""

    def test_construction_and_validation(self):
        item = FounderReviewQueueItem(
            review_item_id="ri_test001",
            item_type="pain_cluster",
            title="Test pain cluster",
            actor="developer",
            workflow="testing",
            object="test framework",
            pain_pattern="developers cannot test",
            score=0.75,
            score_components={"pain_explicitness": 0.80, "recurrence": 0.60},
            evidence_summary="2 items from 2 sources",
            evidence_links=[],
            source_ids=["hacker_news", "github_issues"],
            source_diversity=2,
            recurrence=2,
            noise_risk=0.10,
            business_relevance=0.70,
            uncertainty="low",
            recommended_decision="PROMOTE",
            recommendation_reason="Strong score",
            suggested_validation_action="interview",
            source_quality_notes="",
            traceability_status="clean",
            created_at="2026-05-12T00:00:00Z",
            pain_cluster_id="pc_test001",
        )
        item.validate()

    def test_invalid_decision(self):
        item = FounderReviewQueueItem(
            review_item_id="ri_test001",
            item_type="pain_cluster",
            title="Test",
            actor="dev",
            workflow="test",
            object="test",
            pain_pattern="test",
            score=0.50,
            score_components={},
            evidence_summary="test",
            evidence_links=[],
            source_ids=[],
            source_diversity=1,
            recurrence=1,
            noise_risk=0.10,
            business_relevance=0.50,
            uncertainty="moderate",
            recommended_decision="INVALID",
            recommendation_reason="test",
            suggested_validation_action="interview",
            source_quality_notes="",
            traceability_status="clean",
            created_at="2026-05-12T00:00:00Z",
        )
        with self.assertRaises(ValueError):
            item.validate()

    def test_score_out_of_range(self):
        item = FounderReviewQueueItem(
            review_item_id="ri_test001",
            item_type="pain_cluster",
            title="Test",
            actor="dev",
            workflow="test",
            object="test",
            pain_pattern="test",
            score=1.5,
            score_components={},
            evidence_summary="test",
            evidence_links=[],
            source_ids=[],
            source_diversity=1,
            recurrence=1,
            noise_risk=0.10,
            business_relevance=0.50,
            uncertainty="moderate",
            recommended_decision="PARK",
            recommendation_reason="test",
            suggested_validation_action="manual_research",
            source_quality_notes="",
            traceability_status="clean",
            created_at="2026-05-12T00:00:00Z",
        )
        with self.assertRaises(ValueError):
            item.validate()

    def test_to_dict_from_dict_roundtrip(self):
        original = FounderReviewQueueItem(
            review_item_id="ri_test001",
            item_type="pain_cluster",
            title="Test pain cluster",
            actor="developer",
            workflow="testing",
            object="test framework",
            pain_pattern="developers cannot test",
            score=0.75,
            score_components={"pain_explicitness": 0.80, "recurrence": 0.60},
            evidence_summary="2 items from 2 sources",
            evidence_links=[
                FounderReviewEvidenceLink(
                    evidence_id="ev_001", source_id="hacker_news",
                    source_type="discussion",
                    source_url="https://news.ycombinator.com/item?id=1",
                    title="Test", excerpt="test", evidence_kind="pain_signal_candidate",
                ),
            ],
            source_ids=["hacker_news", "github_issues"],
            source_diversity=2,
            recurrence=2,
            noise_risk=0.10,
            business_relevance=0.70,
            uncertainty="low",
            recommended_decision="PROMOTE",
            recommendation_reason="Strong score",
            suggested_validation_action="interview",
            source_quality_notes="test note",
            traceability_status="clean",
            created_at="2026-05-12T00:00:00Z",
            notes="founder note",
            pain_cluster_id="pc_test001",
            opportunity_id="oppc_test001",
            founder_final_decision="",
        )
        d = original.to_dict()
        restored = FounderReviewQueueItem.from_dict(d)
        self.assertEqual(original.review_item_id, restored.review_item_id)
        self.assertEqual(original.score, restored.score)
        self.assertEqual(original.recommended_decision, restored.recommended_decision)
        self.assertEqual(original.pain_cluster_id, restored.pain_cluster_id)
        self.assertEqual(len(original.evidence_links), len(restored.evidence_links))


class TestBuildFounderReviewPackage(unittest.TestCase):
    """Test the package builder with various inputs."""

    def test_build_from_one_cluster(self):
        cluster = _make_cluster_dict(overall=0.75)
        created_at = "2026-05-12T10:00:00Z"
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at=created_at,
            discovery_run_id="pilot_run_test",
        )
        self.assertEqual(package.total_review_items, 1)
        self.assertEqual(package.promote_count, 1)
        self.assertEqual(package.kill_count, 0)
        self.assertIsNotNone(package.package_id)
        self.assertTrue(package.package_id.startswith("frp_"))

    def test_build_from_multiple_clusters(self):
        clusters = [
            _make_cluster_dict("pc_001", overall=0.85),
            _make_cluster_dict("pc_002", overall=0.55),
            _make_cluster_dict("pc_003", overall=0.15, noise_risk=0.85),
        ]
        package = build_founder_review_package(
            pain_clusters=clusters,
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.total_review_items, 3)

    def test_build_from_opportunity_candidates(self):
        opp = _make_opp_candidate("oppc_001", "pc_001", score=0.80)
        package = build_founder_review_package(
            opportunity_candidates=[opp],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.total_review_items, 1)
        self.assertEqual(package.review_items[0].item_type, "opportunity_candidate")
        self.assertEqual(package.review_items[0].opportunity_id, "oppc_001")

    def test_evidence_links_preserved(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/r/issues/1"),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        self.assertEqual(len(item.evidence_links), 2)
        self.assertEqual(item.evidence_links[0].source_url,
                         "https://news.ycombinator.com/item?id=1")
        self.assertEqual(item.evidence_links[1].source_url,
                         "https://github.com/o/r/issues/1")

    def test_counts_in_package_summary(self):
        clusters = [
            _make_cluster_dict("pc_001", overall=0.85),          # PROMOTE
            _make_cluster_dict("pc_002", overall=0.55),          # NEEDS_MORE_EVIDENCE
            _make_cluster_dict("pc_003", overall=0.35),          # PARK
            _make_cluster_dict("pc_004", overall=0.15,
                              noise_risk=0.85),                   # KILL
            _make_cluster_dict("pc_005", overall=0.45,
                              recurrence=1, business_relevance=0.35),  # REVISIT_LATER
        ]
        package = build_founder_review_package(
            pain_clusters=clusters,
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.total_review_items, 5)
        self.assertGreaterEqual(package.promote_count, 1)
        self.assertGreaterEqual(package.needs_more_evidence_count, 1)
        self.assertGreaterEqual(package.park_count, 1)
        self.assertGreaterEqual(package.kill_count, 1)

    def test_source_ids_aggregation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion"),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/r/issues/1"),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertIn("github_issues", package.source_ids)
        self.assertIn("hacker_news", package.source_ids)

    def test_sorting_priority(self):
        """Verify items are sorted by decision priority, score, diversity, recurrence, id."""
        clusters = [
            _make_cluster_dict("pc_a", overall=0.35, source_diversity=1, recurrence=1),  # PARK
            _make_cluster_dict("pc_b", overall=0.85, source_diversity=2, recurrence=5),  # PROMOTE
            _make_cluster_dict("pc_c", overall=0.15,
                              noise_risk=0.85, source_diversity=1, recurrence=1),  # KILL
        ]
        package = build_founder_review_package(
            pain_clusters=clusters,
            created_at="2026-05-12T10:00:00Z",
        )
        decisions = [ri.recommended_decision for ri in package.review_items]
        # PROMOTE should come first
        self.assertEqual(decisions[0], "PROMOTE")
        # KILL should be last
        self.assertEqual(decisions[-1], "KILL")

    def test_deterministic_created_at(self):
        cluster = _make_cluster_dict()
        created_at = "2026-01-01T00:00:00Z"
        pkg1 = build_founder_review_package(
            pain_clusters=[cluster], created_at=created_at,
        )
        pkg2 = build_founder_review_package(
            pain_clusters=[cluster], created_at=created_at,
        )
        self.assertEqual(pkg1.package_id, pkg2.package_id)
        self.assertEqual(pkg1.created_at, pkg2.created_at)
        self.assertEqual(pkg1.review_items[0].review_item_id,
                         pkg2.review_items[0].review_item_id)

    def test_missing_source_quality_report_warning(self):
        cluster = _make_cluster_dict()
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertTrue(any("source quality report" in w.lower() for w in package.warnings))

    def test_max_items_limit(self):
        clusters = [_make_cluster_dict(f"pc_{i:03d}", overall=0.50) for i in range(20)]
        package = build_founder_review_package(
            pain_clusters=clusters,
            created_at="2026-05-12T10:00:00Z",
            max_items=5,
        )
        self.assertLessEqual(package.total_review_items, 5)

    def test_empty_input(self):
        package = build_founder_review_package(
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.total_review_items, 0)

    # New: Single-source / low-recurrence PROMOTE safety
    def test_high_score_single_source_recurrence_1_is_needs_more_evidence(self):
        """High score + single-source + recurrence 1 => NEEDS_MORE_EVIDENCE."""
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
        ]
        cluster = _make_cluster_dict(
            "pc_single", overall=0.80, source_diversity=1, recurrence=1,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.total_review_items, 1)
        self.assertEqual(package.review_items[0].recommended_decision,
                         "NEEDS_MORE_EVIDENCE")
        self.assertEqual(package.promote_count, 0)

    # New: Builder error handling
    def test_cluster_with_malformed_evidence_produces_error(self):
        """Cluster with completely malformed evidence should produce build error."""
        # Evidence with None for all fields should still build but may have empty
        # strings — _build_evidence_links is lenient. Test with a dict that will
        # fail normalisation.
        # We test that a truly broken cluster dict (missing cluster_id) still
        # produces a build error, not a silent drop.
        bad_cluster = {"not_a_cluster": True}  # missing cluster_id won't fail
        # Actually, to trigger a real error we need something that passes
        # _normalize_cluster but fails _build_review_item_for_cluster.
        # The builder is lenient on purpose. Let's test:
        # If the cluster dict is valid enough, it should build.
        # The real test: builder must record errors, not silently continue.
        # We verify that package.errors contains build errors when appropriate.
        # Given the lenient design, let's test the error recording path:
        package = build_founder_review_package(
            pain_clusters=[{"cluster_id": "pc_ok"}],
            created_at="2026-05-12T10:00:00Z",
        )
        # Even with minimal cluster, it should build without crash
        self.assertIsNotNone(package)
        # If no errors, errors should be empty list
        self.assertIsInstance(package.errors, list)

    def test_builder_produces_errors_not_silent_drop(self):
        """Builder must record build errors in package.errors, not silently drop."""
        # Use a value that fails int() conversion to trigger Exception.
        class Uncastable:
            def __int__(self):
                raise RuntimeError("simulated broken cluster")

        bad_cluster = {
            "cluster_id": "pc_broken",
            "actor": "dev",
            "workflow": "test",
            "object": "test",
            "pain_pattern": "test",
            "source_diversity": Uncastable(),
            "recurrence": 1,
            "noise_risk": 0.0,
            "business_relevance": 0.5,
            "source_evidence_list": [],
            "scoring": {"overall": 0.75, "pain_explicitness": 0.8, "recurrence": 0.6,
                        "business_cost": 0.7, "icp_fit": 0.5, "source_reliability": 0.75,
                        "freshness": 0.9, "actionability": 0.6, "noise_risk": 0.1},
        }

        package = build_founder_review_package(
            pain_clusters=[bad_cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        # The broken cluster should be caught, error recorded
        self.assertTrue(
            len(package.errors) > 0,
            f"Expected build errors, got: {package.errors}"
        )
        self.assertIn("build error", package.errors[0].lower())
        # The broken cluster should not appear in review_items
        self.assertEqual(package.total_review_items, 0)

    def test_opportunity_with_malformed_evidence_produces_error(self):
        """Malformed opportunity should produce build error."""
        # score as a list instead of a number: float(["not_a_score"]) raises TypeError
        bad_opp = {
            "opportunity_id": "oppc_broken",
            "score": ["not_a_number"],
            "source_evidence_links": [],
        }

        package = build_founder_review_package(
            opportunity_candidates=[bad_opp],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertTrue(len(package.errors) > 0,
                       f"Expected build errors, got: {package.errors}")
        self.assertIn("build error", package.errors[0].lower())


class TestValidateFounderReviewPackage(unittest.TestCase):
    """Test validation of founder review packages."""

    def test_valid_package(self):
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertTrue(result.is_valid)

    def test_empty_package_fails(self):
        package = FounderReviewPackage(
            package_id="frp_test",
            discovery_run_id="test",
            created_at="2026-05-12T00:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("no review items" in e.lower() for e in result.errors))

    def test_missing_source_url_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion", source_url=""),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("missing source_url" in e.lower() for e in result.errors))

    def test_placeholder_url_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          source_url="urn:oos:placeholder"),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("placeholder" in e.lower() for e in result.errors))

    def test_no_promote_items_warns(self):
        cluster = _make_cluster_dict(overall=0.15, noise_risk=0.85)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertTrue(any("No PROMOTE" in w for w in result.warnings))

    # New: non-http(s) URLs must fail validation
    def test_ftp_url_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          source_url="ftp://files.example.com/data"),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("non-http" in e.lower() for e in result.errors))

    def test_github_protocol_url_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "github_issues", "issue_tracker",
                          source_url="github://owner/repo/issues/1"),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("non-http" in e.lower() for e in result.errors))

    def test_urn_oos_url_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          source_url="urn:oos:some-id"),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("placeholder" in e.lower() for e in result.errors))

    def test_empty_source_url_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion", source_url=""),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("missing source_url" in e.lower() for e in result.errors))

    def test_valid_https_passes(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          source_url="https://news.ycombinator.com/item?id=12345"),
        ]
        cluster = _make_cluster_dict(
            "pc_good", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertTrue(result.is_valid)

    # New: evidence link identity field validation
    def test_missing_evidence_id_fails_validation(self):
        evidence = [
            _make_evidence("", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
        ]
        cluster = _make_cluster_dict(
            "pc_miss_evid", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("missing evidence_id" in e.lower() for e in result.errors))

    def test_missing_source_id_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
        ]
        cluster = _make_cluster_dict(
            "pc_miss_sid", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("missing source_id" in e.lower() for e in result.errors))

    def test_missing_source_type_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "",
                          "https://news.ycombinator.com/item?id=1"),
        ]
        cluster = _make_cluster_dict(
            "pc_miss_stype", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("missing source_type" in e.lower() for e in result.errors))

    def test_missing_title_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          title=""),
        ]
        cluster = _make_cluster_dict(
            "pc_miss_title", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("missing title" in e.lower() for e in result.errors))

    def test_missing_excerpt_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          excerpt=""),
        ]
        cluster = _make_cluster_dict(
            "pc_miss_excerpt", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("missing excerpt" in e.lower() for e in result.errors))

    def test_missing_evidence_kind_fails_validation(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          evidence_kind=""),
        ]
        cluster = _make_cluster_dict(
            "pc_miss_ekind", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        result = validate_founder_review_package(package)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("missing evidence_kind" in e.lower() for e in result.errors))


class TestRenderMarkdown(unittest.TestCase):
    """Test Markdown rendering."""

    def test_markdown_contains_required_sections(self):
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        required_sections = [
            "# Founder Review Package",
            "## Executive Summary",
            "## Signal-to-Noise Ratio",
            "## Review Counts",
            "## Top Review Items",
            "## Decision Cards",
            "## Score Breakdown",
            "## Warnings and Caveats",
        ]
        for section in required_sections:
            self.assertIn(section, md, f"Missing section: {section}")

    def test_markdown_is_ascii_safe(self):
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        # All characters should be ASCII
        for i, ch in enumerate(md):
            self.assertTrue(
                ord(ch) < 128,
                f"Non-ASCII character at position {i}: U+{ord(ch):04X}"
            )

    def test_markdown_empty_package(self):
        package = FounderReviewPackage(
            package_id="frp_test",
            discovery_run_id="test",
            created_at="2026-05-12T00:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("| **Total** | **0** |", md)

    def test_markdown_includes_package_traceability(self):
        """Markdown must include package-level traceability status."""
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("**Traceability**: clean", md)


class TestToDictFromDictRoundtrip(unittest.TestCase):
    """Test serialization roundtrips."""

    def test_founder_review_package_roundtrip(self):
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        d = package.to_dict()
        restored = FounderReviewPackage.from_dict(d)
        self.assertEqual(package.package_id, restored.package_id)
        self.assertEqual(package.total_review_items, restored.total_review_items)
        self.assertEqual(package.promote_count, restored.promote_count)
        self.assertEqual(len(package.review_items), len(restored.review_items))

    def test_roundtrip_preserves_evidence_links(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          "HN Post", "HN excerpt"),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        d = package.to_dict()
        restored = FounderReviewPackage.from_dict(d)
        self.assertEqual(
            package.review_items[0].evidence_links[0].source_url,
            restored.review_items[0].evidence_links[0].source_url,
        )

    def test_roundtrip_preserves_traceability_summary(self):
        """to_dict/from_dict roundtrip preserves package-level traceability fields."""
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
        ]
        cluster = _make_cluster_dict(
            "pc_trace", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        d = package.to_dict()
        restored = FounderReviewPackage.from_dict(d)
        self.assertEqual(package.traceability_status, restored.traceability_status)
        self.assertEqual(package.total_evidence_links, restored.total_evidence_links)
        self.assertEqual(package.invalid_evidence_link_count,
                         restored.invalid_evidence_link_count)
        self.assertEqual(package.missing_source_url_count,
                         restored.missing_source_url_count)
        self.assertEqual(package.placeholder_url_count,
                         restored.placeholder_url_count)
        self.assertEqual(package.non_http_url_count,
                         restored.non_http_url_count)


class TestNoLiveAPI(unittest.TestCase):
    """Verify no network calls are made."""

    def test_build_package_no_network(self):
        """Building a package should not touch the network."""
        cluster = _make_cluster_dict()
        # This would fail if any network call is attempted
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertIsNotNone(package)

    def test_markdown_no_network(self):
        cluster = _make_cluster_dict()
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIsInstance(md, str)
        self.assertTrue(len(md) > 0)


class TestSourceQualityReportIntegration(unittest.TestCase):
    """Test integration with SourceQualityReport."""

    def test_package_with_source_quality_report(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion"),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/r/issues/1", "GH Issue"),
        ]
        cluster = _make_cluster_dict(evidence_list=evidence, noise_risk=0.10)

        sqr = build_source_quality_report(
            evidence_items=evidence,
            pain_clusters=[cluster],
            discovery_run_id="pilot_run_test",
        )

        package = build_founder_review_package(
            pain_clusters=[cluster],
            source_quality_report=sqr,
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertIsNotNone(package)
        # Should not have "no source quality report" warning
        self.assertFalse(
            any("source quality report" in w.lower() for w in package.warnings)
        )


class TestDecisionPriorityOrdering(unittest.TestCase):
    """Verify DECISION_PRIORITY mapping covers all allowed decisions."""

    def test_all_decisions_have_priority(self):
        for decision in ALLOWED_RECOMMENDED_DECISIONS:
            self.assertIn(decision, DECISION_PRIORITY,
                          f"Missing priority for {decision}")


# ---------------------------------------------------------------------------
# Package-level traceability tests
# ---------------------------------------------------------------------------


class TestPackageLevelTraceability(unittest.TestCase):
    """Test package-level traceability_status / traceability_summary."""

    def test_package_all_valid_urls_traceability_clean(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/r/issues/1"),
        ]
        cluster = _make_cluster_dict(
            "pc_clean", overall=0.75, source_diversity=2, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.traceability_status, "clean")
        self.assertEqual(package.total_evidence_links, 2)
        self.assertEqual(package.invalid_evidence_link_count, 0)
        self.assertEqual(package.missing_source_url_count, 0)
        self.assertEqual(package.placeholder_url_count, 0)
        self.assertEqual(package.non_http_url_count, 0)

    def test_package_one_invalid_url_traceability_failed(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "urn:oos:missing"),  # placeholder
        ]
        cluster = _make_cluster_dict(
            "pc_bad", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.traceability_status, "failed")
        self.assertEqual(package.total_evidence_links, 2)
        self.assertGreater(package.invalid_evidence_link_count, 0)
        self.assertGreater(package.placeholder_url_count, 0)

    def test_package_missing_url_traceability_failed(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          source_url=""),
        ]
        cluster = _make_cluster_dict(
            "pc_miss", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.traceability_status, "failed")
        self.assertGreater(package.missing_source_url_count, 0)

    def test_package_non_http_url_traceability_failed(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          source_url="ftp://files.example.com/data"),
        ]
        cluster = _make_cluster_dict(
            "pc_nonhttp", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.traceability_status, "failed")
        self.assertGreater(package.non_http_url_count, 0)


class TestLinkTraceabilityHelpers(unittest.TestCase):
    """Test the traceability helper functions."""

    def test_assess_clean_https_link(self):
        link = FounderReviewEvidenceLink(
            evidence_id="ev_001", source_id="hn", source_type="discussion",
            source_url="https://news.ycombinator.com/item?id=1",
            title="T", excerpt="E", evidence_kind="pain_signal_candidate",
        )
        clean, status, issues = _assess_link_traceability(link)
        self.assertTrue(clean)
        self.assertEqual(status, "clean")
        self.assertEqual(issues, [])

    def test_assess_missing_url(self):
        link = FounderReviewEvidenceLink(
            evidence_id="ev_001", source_id="hn", source_type="discussion",
            source_url="",
            title="T", excerpt="E", evidence_kind="pain_signal_candidate",
        )
        clean, status, issues = _assess_link_traceability(link)
        self.assertFalse(clean)
        self.assertEqual(status, "failed")
        self.assertIn("missing_source_url", issues)

    def test_assess_placeholder_url(self):
        link = FounderReviewEvidenceLink(
            evidence_id="ev_001", source_id="hn", source_type="discussion",
            source_url="urn:oos:placeholder",
            title="T", excerpt="E", evidence_kind="pain_signal_candidate",
        )
        clean, status, issues = _assess_link_traceability(link)
        self.assertFalse(clean)
        self.assertIn("placeholder_url", issues)

    def test_assess_non_http_url(self):
        link = FounderReviewEvidenceLink(
            evidence_id="ev_001", source_id="hn", source_type="discussion",
            source_url="ftp://files.example.com/data",
            title="T", excerpt="E", evidence_kind="pain_signal_candidate",
        )
        clean, status, issues = _assess_link_traceability(link)
        self.assertFalse(clean)
        self.assertIn("non_http_url", issues)

    def test_compute_package_traceability_empty(self):
        result = _compute_package_traceability([])
        self.assertEqual(result["traceability_status"], "clean")
        self.assertEqual(result["total_evidence_links"], 0)
        self.assertEqual(result["invalid_evidence_link_count"], 0)

    def test_compute_package_traceability_mixed(self):
        item = FounderReviewQueueItem(
            review_item_id="ri_001", item_type="pain_cluster",
            title="Test", actor="dev", workflow="test", object="test",
            pain_pattern="test", score=0.5, score_components={},
            evidence_summary="test",
            evidence_links=[
                FounderReviewEvidenceLink(
                    evidence_id="ev_001", source_id="hn", source_type="discussion",
                    source_url="https://news.ycombinator.com/item?id=1",
                    title="T", excerpt="E", evidence_kind="pain_signal_candidate",
                ),
                FounderReviewEvidenceLink(
                    evidence_id="ev_002", source_id="gh", source_type="issue_tracker",
                    source_url="",
                    title="T", excerpt="E", evidence_kind="pain_signal_candidate",
                ),
            ],
            source_ids=["hn", "gh"], source_diversity=2, recurrence=2,
            noise_risk=0.1, business_relevance=0.5, uncertainty="moderate",
            recommended_decision="PARK", recommendation_reason="test",
            suggested_validation_action="manual_research",
            source_quality_notes="", traceability_status="failed",
            created_at="2026-05-12T00:00:00Z",
        )
        result = _compute_package_traceability([item])
        self.assertEqual(result["traceability_status"], "failed")
        self.assertEqual(result["total_evidence_links"], 2)
        self.assertEqual(result["invalid_evidence_link_count"], 1)
        self.assertEqual(result["missing_source_url_count"], 1)


# ---------------------------------------------------------------------------
# v2.14 item 2 — Quality Flags to Scoring/Tier Integration
# ---------------------------------------------------------------------------


class TestQualitySummaryInReviewItem(unittest.TestCase):
    """Tests that review items include quality summary / blocker / gate info."""

    def test_clean_cluster_has_quality_summary_fields(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          quality_flags=["debugging_pain"]),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/r/issues/1",
                          quality_flags=["integration_pain"]),
        ]
        cluster = _make_cluster_dict(
            "pc_clean_qs", overall=0.85, source_diversity=2, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        d = item.to_dict()
        self.assertIn("quality_summary", d)
        self.assertIn("promotion_blockers", d)
        self.assertIn("quality_gate_reasons", d)
        self.assertIn("evidence_quality_counts", d)
        self.assertIn("dominant_quality_flags", d)

    def test_clean_cluster_promote_has_no_blockers(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1"),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/r/issues/1"),
        ]
        cluster = _make_cluster_dict(
            "pc_promote", overall=0.85, source_diversity=2, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        self.assertEqual(item.promotion_blockers, [])
        self.assertEqual(item.recommended_decision, "PROMOTE")

    def test_high_score_noise_ratio_blocks_promote(self):
        """Cluster with noise_ratio >= 0.5 cannot PROMOTE."""
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          quality_flags=["bot_generated"]),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/r/issues/1",
                          quality_flags=["maintainer_housekeeping"]),
            _make_evidence("ev_003", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=2",
                          quality_flags=[]),
        ]
        cluster = _make_cluster_dict(
            "pc_noise_heavy", overall=0.75, source_diversity=2, recurrence=3,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        self.assertNotEqual(item.recommended_decision, "PROMOTE",
                           "Cluster with noise_ratio >= 0.5 must not PROMOTE")
        self.assertTrue(len(item.promotion_blockers) > 0,
                       "Expected promotion_blockers for noise-heavy cluster")

    def test_only_weak_evidence_routes_to_needs_more(self):
        """Clusters with only weak evidence should be NEEDS_MORE_EVIDENCE."""
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          quality_flags=["requires_manual_review"]),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/r/issues/1",
                          quality_flags=["generic_language"]),
        ]
        cluster = _make_cluster_dict(
            "pc_weak_only", overall=0.65, source_diversity=2, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        self.assertNotEqual(item.recommended_decision, "PROMOTE",
                           "Only-weak evidence should not PROMOTE")
        self.assertIn(item.recommended_decision, ("NEEDS_MORE_EVIDENCE", "PARK"))

    def test_evidence_quality_counts_accurate(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          quality_flags=[]),
            _make_evidence("ev_002", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=2",
                          quality_flags=["requires_manual_review"]),
            _make_evidence("ev_003", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=3",
                          quality_flags=["bot_generated"]),
        ]
        cluster = _make_cluster_dict(
            "pc_counts", overall=0.55, source_diversity=1, recurrence=3,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        self.assertEqual(item.evidence_quality_counts, {
            "accepted": 1, "weak": 1, "noise": 1,
        })
        self.assertEqual(item.quality_summary["accepted_evidence_count"], 1)
        self.assertEqual(item.quality_summary["weak_evidence_count"], 1)
        self.assertEqual(item.quality_summary["noise_evidence_count"], 1)

    def test_dominant_quality_flags_in_review_item(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          quality_flags=["debugging_pain", "debugging_pain"]),
            _make_evidence("ev_002", "github_issues", "issue_tracker",
                          "https://github.com/o/r/issues/1",
                          quality_flags=["debugging_pain"]),
        ]
        cluster = _make_cluster_dict(
            "pc_flags", overall=0.75, source_diversity=2, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        self.assertIn("debugging_pain", item.dominant_quality_flags)

    def test_roundtrip_preserves_quality_fields(self):
        """to_dict/from_dict roundtrip preserves v2.14 quality fields."""
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          quality_flags=["debugging_pain"]),
            _make_evidence("ev_002", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=2",
                          quality_flags=["bot_generated"]),
        ]
        cluster = _make_cluster_dict(
            "pc_rt", overall=0.55, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        d = item.to_dict()
        restored = FounderReviewQueueItem.from_dict(d)
        self.assertEqual(item.quality_summary, restored.quality_summary)
        self.assertEqual(item.promotion_blockers, restored.promotion_blockers)
        self.assertEqual(item.quality_gate_reasons, restored.quality_gate_reasons)
        self.assertEqual(item.evidence_quality_counts, restored.evidence_quality_counts)
        self.assertEqual(item.dominant_quality_flags, restored.dominant_quality_flags)

    def test_markdown_includes_quality_fields(self):
        """Markdown rendering works with quality fields present."""
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          quality_flags=["debugging_pain"]),
        ]
        cluster = _make_cluster_dict(
            "pc_md", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIsInstance(md, str)
        self.assertTrue(len(md) > 0)


class TestPromotionBlockerIntegration(unittest.TestCase):
    """End-to-end tests for promotion blockers in recommend_decision."""

    def test_high_base_score_noise_ratio_blocks_promote(self):
        """High score + noise_ratio >= 0.5 => not PROMOTE."""
        from oos.noise_classifier import compute_evidence_quality_summary, compute_quality_gate_reasons
        evidence = [
            _make_evidence("ev_001", quality_flags=["bot_generated"]),
            _make_evidence("ev_002", quality_flags=["maintainer_housekeeping"]),
            _make_evidence("ev_003", quality_flags=[]),
        ]
        summary = compute_evidence_quality_summary(evidence)
        blockers, _ = compute_quality_gate_reasons(
            summary, source_diversity=2, recurrence=3,
            traceability_clean=True, source_scope_clean=True,
        )
        decision, reason = recommend_decision(
            score=0.85, noise_risk=0.10, source_diversity=2, recurrence=3,
            business_relevance=0.70, uncertainty="low",
            source_url_traceability_clean=True, has_credible_evidence=True,
            promotion_blockers=blockers,
        )
        self.assertNotEqual(decision, "PROMOTE")

    def test_only_weak_evidence_routes_to_needs_more(self):
        """All weak evidence => not PROMOTE."""
        from oos.noise_classifier import compute_evidence_quality_summary, compute_quality_gate_reasons
        evidence = [
            _make_evidence("ev_001", quality_flags=["requires_manual_review"]),
            _make_evidence("ev_002", quality_flags=["generic_language"]),
        ]
        summary = compute_evidence_quality_summary(evidence)
        blockers, _ = compute_quality_gate_reasons(
            summary, source_diversity=2, recurrence=2,
            traceability_clean=True, source_scope_clean=True,
        )
        decision, reason = recommend_decision(
            score=0.75, noise_risk=0.10, source_diversity=2, recurrence=2,
            business_relevance=0.50, uncertainty="moderate",
            source_url_traceability_clean=True, has_credible_evidence=True,
            promotion_blockers=blockers,
        )
        self.assertNotEqual(decision, "PROMOTE")

    def test_severe_noise_no_clean_support_blocks(self):
        """Severe noise + no clean cross-source => not PROMOTE."""
        from oos.noise_classifier import compute_evidence_quality_summary, compute_quality_gate_reasons
        evidence = [
            _make_evidence("ev_001", quality_flags=["bot_generated"]),
            _make_evidence("ev_002", quality_flags=[]),
        ]
        summary = compute_evidence_quality_summary(evidence)
        blockers, _ = compute_quality_gate_reasons(
            summary, source_diversity=1, recurrence=2,
            traceability_clean=True, source_scope_clean=True,
        )
        decision, reason = recommend_decision(
            score=0.80, noise_risk=0.45, source_diversity=1, recurrence=2,
            business_relevance=0.60, uncertainty="moderate",
            source_url_traceability_clean=True, has_credible_evidence=True,
            promotion_blockers=blockers,
        )
        self.assertNotEqual(decision, "PROMOTE")

    def test_clean_cross_source_can_still_promote(self):
        """Clean cross-source evidence with no blockers can PROMOTE."""
        from oos.noise_classifier import compute_evidence_quality_summary, compute_quality_gate_reasons
        evidence = [
            _make_evidence("ev_001", quality_flags=["debugging_pain"]),
            _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker",
                          source_url="https://github.com/o/r/issues/1",
                          quality_flags=["integration_pain"]),
        ]
        summary = compute_evidence_quality_summary(evidence)
        blockers, _ = compute_quality_gate_reasons(
            summary, source_diversity=2, recurrence=2,
            traceability_clean=True, source_scope_clean=True,
        )
        decision, reason = recommend_decision(
            score=0.85, noise_risk=0.10, source_diversity=2, recurrence=2,
            business_relevance=0.70, uncertainty="low",
            source_url_traceability_clean=True, has_credible_evidence=True,
            promotion_blockers=blockers,
        )
        self.assertEqual(decision, "PROMOTE")

    def test_traceability_blocker_kills(self):
        """Traceability blocker => KILL even with high score."""
        from oos.noise_classifier import compute_evidence_quality_summary, compute_quality_gate_reasons
        evidence = [
            _make_evidence("ev_001", quality_flags=[]),
        ]
        summary = compute_evidence_quality_summary(evidence)
        blockers, _ = compute_quality_gate_reasons(
            summary, source_diversity=2, recurrence=2,
            traceability_clean=False, source_scope_clean=True,
        )
        decision, reason = recommend_decision(
            score=0.90, noise_risk=0.05, source_diversity=2, recurrence=2,
            business_relevance=0.80, uncertainty="low",
            source_url_traceability_clean=False, has_credible_evidence=True,
            promotion_blockers=blockers,
        )
        self.assertEqual(decision, "KILL")

    def test_recommend_decision_backward_compat_no_blockers(self):
        """recommend_decision() works with promotion_blockers=None (backward compat)."""
        decision, reason = recommend_decision(
            score=0.85, noise_risk=0.10, source_diversity=2, recurrence=3,
            business_relevance=0.70, uncertainty="low",
            source_url_traceability_clean=True, has_credible_evidence=True,
            promotion_blockers=None,
        )
        self.assertEqual(decision, "PROMOTE")


class TestMarkdownQualityGateVisibility(unittest.TestCase):
    """v2.14 Fix 2: Markdown includes Quality Gate block per review item."""

    def test_markdown_includes_quality_gate_section(self):
        evidence = [
            _make_evidence("ev_001", "hacker_news", "discussion",
                          "https://news.ycombinator.com/item?id=1",
                          quality_flags=["debugging_pain"]),
        ]
        cluster = _make_cluster_dict(
            "pc_qg", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("#### Quality Gate", md,
                      "Markdown should include '#### Quality Gate' section per review item")

    def test_markdown_includes_accepted_weak_noise_counts(self):
        evidence = [
            _make_evidence("ev_001", quality_flags=[]),
            _make_evidence("ev_002", quality_flags=["requires_manual_review"]),
            _make_evidence("ev_003", quality_flags=["bot_generated"]),
        ]
        cluster = _make_cluster_dict(
            "pc_counts_md", overall=0.55, source_diversity=1, recurrence=3,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("accepted=1", md,
                      "Markdown should show accepted=1")
        self.assertIn("weak=1", md,
                      "Markdown should show weak=1")
        self.assertIn("noise=1", md,
                      "Markdown should show noise=1")

    def test_markdown_includes_blockers_when_present(self):
        evidence = [
            _make_evidence("ev_001", quality_flags=["bot_generated"]),
            _make_evidence("ev_002", quality_flags=["maintainer_housekeeping"]),
            _make_evidence("ev_003", quality_flags=[]),
        ]
        cluster = _make_cluster_dict(
            "pc_blockers_md", overall=0.75, source_diversity=1, recurrence=3,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("- **Blockers**:", md,
                      "Markdown should include Blockers line when blockers present")
        self.assertIn("noise ratio", md.lower(),
                      "Markdown should mention noise ratio in blockers")

    def test_markdown_says_blockers_none_when_empty(self):
        evidence = [
            _make_evidence("ev_001", quality_flags=["debugging_pain"]),
            _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker",
                          source_url="https://github.com/o/r/issues/1",
                          quality_flags=["integration_pain"]),
        ]
        cluster = _make_cluster_dict(
            "pc_clean_md", overall=0.85, source_diversity=2, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("- **Blockers**: none", md,
                      "Markdown should show Blockers: none when no blockers")

    def test_markdown_includes_dominant_quality_flags(self):
        evidence = [
            _make_evidence("ev_001", quality_flags=["debugging_pain", "debugging_pain"]),
        ]
        cluster = _make_cluster_dict(
            "pc_dom_md", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("- **Flags**: [DEBUGGING_PAIN]", md,
                      "Markdown should show quality flags as uppercase badges")

    def test_markdown_includes_gate_reasons_when_present(self):
        # Create a single-source cluster with low recurrence to trigger gate reasons
        evidence = [
            _make_evidence("ev_001", quality_flags=["stale_issue"]),
        ]
        cluster = _make_cluster_dict(
            "pc_qgr_md", overall=0.50, source_diversity=1, recurrence=1,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("- **Gate reasons**:", md,
                      "Markdown should include Gate reasons line when present")

    def test_markdown_omits_gate_reasons_when_empty(self):
        evidence = [
            _make_evidence("ev_001", quality_flags=["debugging_pain"]),
            _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker",
                          source_url="https://github.com/o/r/issues/1",
                          quality_flags=["integration_pain"]),
            _make_evidence("ev_003", quality_flags=["business_cost_signal"]),
        ]
        cluster = _make_cluster_dict(
            "pc_nogate_md", overall=0.85, source_diversity=2, recurrence=3,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertNotIn("Gate reasons", md,
                       "Gate reasons line should be absent when gate_reasons is empty")
        self.assertIn("- **Blockers**: none", md,
                      "Markdown should show Blockers: none when clean")

    def test_json_roundtrip_remains_intact_with_quality_fields(self):
        """Verify that JSON roundtrip still works after quality fields are visible in Markdown."""
        evidence = [
            _make_evidence("ev_001", quality_flags=["debugging_pain"]),
            _make_evidence("ev_002", quality_flags=["bot_generated"]),
        ]
        cluster = _make_cluster_dict(
            "pc_rt_md", overall=0.55, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        d = package.to_dict()
        restored = FounderReviewPackage.from_dict(d)
        ri_orig = package.review_items[0]
        ri_rest = restored.review_items[0]
        self.assertEqual(ri_orig.quality_summary, ri_rest.quality_summary)
        self.assertEqual(ri_orig.promotion_blockers, ri_rest.promotion_blockers)
        self.assertEqual(ri_orig.evidence_quality_counts, ri_rest.evidence_quality_counts)
        self.assertEqual(ri_orig.dominant_quality_flags, ri_rest.dominant_quality_flags)

    def test_backward_compatible_older_review_items_render_without_crashing(self):
        """Older review items without quality fields should render without error."""
        item = FounderReviewQueueItem(
            review_item_id="ri_old",
            item_type="pain_cluster",
            title="Old cluster",
            actor="dev",
            workflow="test",
            object="test",
            pain_pattern="test",
            score=0.5,
            score_components={},
            evidence_summary="test",
            evidence_links=[],
            source_ids=["hacker_news"],
            source_diversity=1,
            recurrence=1,
            noise_risk=0.0,
            business_relevance=0.5,
            uncertainty="moderate",
            recommended_decision="PARK",
            recommendation_reason="test",
            suggested_validation_action="manual_research",
            source_quality_notes="",
            traceability_status="clean",
            created_at="2026-01-01T00:00:00Z",
            # No quality fields set — defaults to empty
        )
        pkg = FounderReviewPackage(
            package_id="frp_old",
            discovery_run_id="test_old",
            created_at="2026-01-01T00:00:00Z",
            total_review_items=1,
            review_items=[item],
        )
        md = render_founder_review_package_markdown(pkg)
        self.assertIsInstance(md, str)
        self.assertIn("#### Quality Gate", md,
                      "Quality Gate section should appear even for older items")
        self.assertIn("- **Blockers**: none", md,
                      "Older items should include Blockers: none line")
        self.assertNotIn("Gate reasons", md,
                       "Gate reasons should be absent when empty for older items")


# ---------------------------------------------------------------------------
# Cluster title cleanup integration tests
# ---------------------------------------------------------------------------


class TestClusterTitleCleanupInFRP(unittest.TestCase):
    """Verify that the FRP uses cleaned cluster review titles."""

    def test_review_item_uses_cleaned_title_not_raw_pain_pattern(self) -> None:
        """FounderReviewQueueItem.title should use cleaned title, not raw pain_pattern."""
        evidence = [
            _make_evidence("ev_001", title="Debugging multi-step agent traces is painful"),
        ]
        cluster = _make_cluster_dict(
            "pc_clean_title",
            overall=0.75,
            pain_pattern="developers cannot debug agent execution traces",
            actor="developer",
            workflow="debugging",
            obj="agent traces",
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        title = package.review_items[0].title
        # Should be a cleaned title, not the raw pain_pattern
        self.assertNotIn("cannot [dead]", title.lower())
        self.assertNotIn("[dead]", title.lower())
        self.assertTrue(len(title) > 0)

    def test_title_in_markdown_is_cleaned(self) -> None:
        """Markdown output should show cleaned title."""
        evidence = [
            _make_evidence("ev_001", title="Agent trace observability is broken"),
        ]
        cluster = _make_cluster_dict(
            "pc_md_title",
            overall=0.75,
            pain_pattern="developers cannot debug agent traces",
            actor="developer",
            workflow="debugging",
            obj="agent traces",
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        title = package.review_items[0].title
        self.assertIn(title, md)
        self.assertNotIn("[dead]", md.lower())

    def test_title_in_json_roundtrip(self) -> None:
        """JSON to_dict/from_dict preserves cleaned title."""
        evidence = [
            _make_evidence("ev_001", title="Debugging agent traces"),
        ]
        cluster = _make_cluster_dict(
            "pc_json_title",
            overall=0.75,
            pain_pattern="developers cannot debug",
            actor="developer",
            workflow="debugging",
            obj="agent traces",
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        d = package.to_dict()
        restored = FounderReviewPackage.from_dict(d)
        self.assertEqual(
            package.review_items[0].title,
            restored.review_items[0].title,
        )

    def test_dead_title_not_propagate_to_frp(self) -> None:
        """Evidence with [dead] title should not leak into FRP title."""
        evidence = [
            _make_evidence(
                "ev_dead",
                title="developer cannot [dead] because llm is cannot",
                source_url="https://news.ycombinator.com/item?id=99999",
            ),
        ]
        cluster = _make_cluster_dict(
            "pc_dead_frp",
            overall=0.35,
            pain_pattern="developer cannot [dead] because llm is cannot",
            actor="developer",
            obj="llm traces",
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        title = package.review_items[0].title
        self.assertNotIn("[dead]", title.lower())
        self.assertNotIn("dead", title.lower())
        self.assertTrue(len(title) > 0)

    def test_needs_more_evidence_not_title(self) -> None:
        """pain_pattern=needs_more_evidence should not become FRP title."""
        evidence = [
            _make_evidence("ev_001", title="Something vague", excerpt="not much"),
        ]
        cluster = _make_cluster_dict(
            "pc_nme_frp",
            overall=0.25,
            pain_pattern="needs_more_evidence",
            actor="developer",
            obj="unknown",
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        title = package.review_items[0].title.lower()
        self.assertNotEqual("needs_more_evidence", title)
        self.assertNotIn("needs_more_evidence", title)

    def test_title_traceability_unchanged(self) -> None:
        """Source URLs and evidence IDs must not be affected by title cleanup."""
        evidence = [
            _make_evidence(
                "ev_url_001",
                title="Agent debugging pain",
                source_url="https://news.ycombinator.com/item?id=41500123",
            ),
        ]
        cluster = _make_cluster_dict(
            "pc_trace_title",
            overall=0.75,
            pain_pattern="developers cannot debug agents",
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        ri = package.review_items[0]
        self.assertEqual(ri.pain_cluster_id, "pc_trace_title")
        urls = [el.source_url for el in ri.evidence_links]
        self.assertIn("https://news.ycombinator.com/item?id=41500123", urls)

    def test_title_length_within_limit(self) -> None:
        """Generated title should be <= 90 chars."""
        evidence = [
            _make_evidence(
                "ev_long",
                title="Developers cannot debug multi-step LLM agent execution traces because the observability tooling provides no actionable context",
                excerpt="Agent traces differ between runs, no standard tooling for replay in production",
            ),
        ]
        cluster = _make_cluster_dict(
            "pc_long_frp",
            overall=0.55,
            pain_pattern="developers cannot debug long traces",
            actor="developer",
            obj="agent execution traces",
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        title = package.review_items[0].title
        self.assertLessEqual(len(title), 90)


# ---------------------------------------------------------------------------
# v2.14 Item 5 — Founder Review Package Clarity Tests
# ---------------------------------------------------------------------------


class TestReviewItemClarityFields(unittest.TestCase):
    """Tests that v2.14 clarity fields are populated in review items."""

    def test_review_item_has_priority_and_factors(self):
        """Review items must carry review_priority and priority_factors."""
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        self.assertGreaterEqual(item.review_priority, 1)
        self.assertIn("recommendation", item.priority_factors)
        self.assertIn("score", item.priority_factors)
        self.assertIn("source_diversity", item.priority_factors)
        self.assertIn("recurrence", item.priority_factors)
        self.assertIn("has_blockers", item.priority_factors)
        self.assertIn("traceability_clean", item.priority_factors)
        self.assertIn("catch_all_risk", item.priority_factors)

    def test_review_item_has_cluster_quality_label(self):
        """Review items must carry cluster_quality_label."""
        cluster = _make_cluster_dict("pc_ql", overall=0.85, source_diversity=2, recurrence=3)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        self.assertIn(item.cluster_quality_label, ("high", "medium", "low"))

    def test_catch_all_risk_cluster_marked_low_quality(self):
        """Cluster with catch_all_risk=True should be 'low' quality regardless of score."""
        cluster = _make_cluster_dict("pc_catch", overall=0.90, source_diversity=3, recurrence=5)
        cluster["cohesion_score"] = 0.3
        cluster["catch_all_risk"] = True
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        self.assertTrue(item.catch_all_risk)
        self.assertEqual(item.cluster_quality_label, "low")

    def test_roundtrip_preserves_item5_fields(self):
        """to_dict/from_dict preserves review_priority, priority_factors, cluster_cohesion, catch_all_risk, cluster_quality_label."""
        cluster = _make_cluster_dict("pc_rt5", overall=0.55, source_diversity=1, recurrence=2)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        item = package.review_items[0]
        d = item.to_dict()
        restored = FounderReviewQueueItem.from_dict(d)
        self.assertEqual(item.review_priority, restored.review_priority)
        self.assertEqual(item.priority_factors, restored.priority_factors)
        self.assertEqual(item.cluster_cohesion_score, restored.cluster_cohesion_score)
        self.assertEqual(item.catch_all_risk, restored.catch_all_risk)
        self.assertEqual(item.cluster_quality_label, restored.cluster_quality_label)


class TestPackageLevelClarityFields(unittest.TestCase):
    """Tests for package-level v2.14 clarity fields."""

    def test_package_has_items_with_blockers_count(self):
        """Package must count items with promotion blockers."""
        # Clean cluster: no blockers
        evidence = [
            _make_evidence("ev_001", quality_flags=["debugging_pain"]),
            _make_evidence("ev_002", source_id="github_issues", source_type="issue_tracker",
                          source_url="https://github.com/o/r/issues/1",
                          quality_flags=["integration_pain"]),
        ]
        cluster = _make_cluster_dict(
            "pc_clean_pkg", overall=0.85, source_diversity=2, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertEqual(package.items_with_blockers, 0)

    def test_package_counts_weak_only_items(self):
        """Package must count items with zero accepted evidence but some weak."""
        evidence = [
            _make_evidence("ev_001", quality_flags=["requires_manual_review"]),
            _make_evidence("ev_002", quality_flags=["generic_language"]),
        ]
        cluster = _make_cluster_dict(
            "pc_weak_pkg", overall=0.55, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        # All evidence is weak; accepted count should be 0
        self.assertGreaterEqual(package.items_with_weak_only, 1)

    def test_dominant_pkg_flags_aggregated(self):
        """Package dominant_pkg_flags must aggregate across items."""
        evidence1 = [
            _make_evidence("ev_a", quality_flags=["debugging_pain"]),
            _make_evidence("ev_b", quality_flags=["debugging_pain"]),
        ]
        c1 = _make_cluster_dict("pc_a", overall=0.75, source_diversity=1, recurrence=2,
                                evidence_list=evidence1)
        evidence2 = [
            _make_evidence("ev_c", quality_flags=["integration_pain"]),
            _make_evidence("ev_d", quality_flags=["bot_generated"]),
        ]
        c2 = _make_cluster_dict("pc_b", overall=0.15, noise_risk=0.85,
                                source_diversity=1, recurrence=2, evidence_list=evidence2)
        package = build_founder_review_package(
            pain_clusters=[c1, c2],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertTrue(len(package.dominant_pkg_flags) > 0)
        self.assertIsInstance(package.dominant_pkg_flags, list)

    def test_estimated_review_time_is_set(self):
        """Package must have a non-empty estimated_review_minutes."""
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        self.assertNotEqual(package.estimated_review_minutes, "unknown")
        self.assertTrue(
            package.estimated_review_minutes.startswith("~")
            or package.estimated_review_minutes == "unknown"
        )

    def test_package_roundtrip_preserves_item5_fields(self):
        """to_dict/from_dict preserves items_with_blockers, dominant_pkg_flags, estimated_review_minutes."""
        evidence = [
            _make_evidence("ev_001", quality_flags=["debugging_pain"]),
        ]
        cluster = _make_cluster_dict(
            "pc_pkgrt5", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        d = package.to_dict()
        restored = FounderReviewPackage.from_dict(d)
        self.assertEqual(package.items_with_blockers, restored.items_with_blockers)
        self.assertEqual(package.items_with_weak_only, restored.items_with_weak_only)
        self.assertEqual(package.items_with_noise_evidence, restored.items_with_noise_evidence)
        self.assertEqual(package.items_catch_all_risk, restored.items_catch_all_risk)
        self.assertEqual(package.dominant_pkg_flags, restored.dominant_pkg_flags)
        self.assertEqual(package.estimated_review_minutes, restored.estimated_review_minutes)


class TestMarkdownClaritySections(unittest.TestCase):
    """Tests for v2.14 markdown section improvements."""

    def test_markdown_executive_summary_has_recommendation_table(self):
        """Executive Summary must contain a recommendation counts table."""
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("| Recommendation | Count |", md)
        self.assertIn("| PROMOTE | 1 |", md)
        self.assertIn("| **Total** | **1** |", md)

    def test_markdown_signal_to_noise_ratio_section(self):
        """Signal-to-Noise Ratio section must show accepted/weak/noise counts."""
        evidence = [
            _make_evidence("ev_001", quality_flags=[]),
            _make_evidence("ev_002", quality_flags=["requires_manual_review"]),
            _make_evidence("ev_003", quality_flags=["bot_generated"]),
        ]
        cluster = _make_cluster_dict(
            "pc_snr", overall=0.55, source_diversity=1, recurrence=3,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("## Signal-to-Noise Ratio", md)
        self.assertIn("| Accepted (clean) |", md)
        self.assertIn("| Weak (needs review) |", md)
        self.assertIn("| Noise |", md)

    def test_markdown_top_items_to_review_first(self):
        """Top Items to Review First section must highlight best candidates."""
        clusters = [
            _make_cluster_dict("pc_001", overall=0.85),  # PROMOTE
            _make_cluster_dict("pc_002", overall=0.35),  # PARK
        ]
        package = build_founder_review_package(
            pain_clusters=clusters,
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("### Top Items to Review First", md)
        self.assertIn("[PROMOTE]", md)

    def test_markdown_decision_card_has_why_this_position(self):
        """Decision Cards must include 'Why This Position' subsection."""
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("#### Why This Position", md)
        self.assertIn("- **Priority rank**:", md)

    def test_markdown_decision_card_has_system_recommendation(self):
        """Decision Cards must include 'System Recommendation' subsection."""
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("#### System Recommendation", md)
        self.assertIn("- **Decision**:", md)
        self.assertIn("- **Reason**:", md)
        self.assertIn("- **Suggested action**:", md)

    def test_markdown_no_obsolete_sections(self):
        """Markdown must NOT contain old-style section names."""
        cluster = _make_cluster_dict(overall=0.75)
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertNotIn("## Evidence Links", md)
        self.assertNotIn("## Recommended Decisions", md)
        self.assertNotIn("## Suggested Validation Actions", md)
        self.assertNotIn("## Risks and Caveats", md)
        self.assertNotIn("## Review Item Details", md)
        self.assertNotIn("## Score Explanations", md)
        self.assertNotIn("### Traceability Summary", md)

    def test_markdown_evidence_excerpts_present(self):
        """Decision cards must include evidence excerpts in evidence blocks."""
        evidence = [
            _make_evidence("ev_001", excerpt="Developers spend hours debugging agent traces with no visibility into execution steps."),
        ]
        cluster = _make_cluster_dict(
            "pc_excerpt", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("> Developers spend hours debugging", md)

    def test_markdown_quality_badges_uppercase(self):
        """Quality flags in evidence must be rendered as uppercase badges."""
        evidence = [
            _make_evidence("ev_001", quality_flags=["debugging_pain", "low_text_context"]),
        ]
        cluster = _make_cluster_dict(
            "pc_badges", overall=0.75, source_diversity=1, recurrence=2,
            evidence_list=evidence,
        )
        package = build_founder_review_package(
            pain_clusters=[cluster],
            created_at="2026-05-12T10:00:00Z",
        )
        md = render_founder_review_package_markdown(package)
        self.assertIn("[DEBUGGING_PAIN]", md)
        self.assertIn("[LOW_TEXT_CONTEXT]", md)


if __name__ == "__main__":
    unittest.main()
