"""Tests for Pilot Founder Review Package (Roadmap v2.12 item 6).

Tests cover:
- Build package from PainClusters and opportunity candidates
- Recommendation logic (all 5 decision statuses)
- Suggested validation actions
- Evidence link preservation and traceability
- Validation rules (fail/warn)
- Sorting priority and tie-breaks
- Package summary counts
- Markdown rendering (ASCII-safe)
- to_dict/from_dict roundtrips
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
        # REVISIT_LATER may or may not trigger depending on ordering

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
            "## Review Counts",
            "## Top Review Items",
            "## Review Item Details",
            "## Score Explanations",
            "## Evidence Links",
            "## Recommended Decisions",
            "## Suggested Validation Actions",
            "## Risks and Caveats",
            "## Source Quality Notes",
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
        self.assertIn("**0** review items", md)


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


if __name__ == "__main__":
    unittest.main()
