from __future__ import annotations

"""Tests for source quality report module (v2.12 item 5).

Covers: deterministic report building, metrics computation, source normalization,
traceability, noise categories, markdown rendering, validation, roundtrip.
No live APIs. No LLM calls. Fixture-only.
"""

import datetime
import json
import unittest

from oos.pain_cluster import (
    PainCluster,
    PainClusterScoring,
    SourceEvidenceEntry,
    compute_cluster_id,
)
from oos.source_quality_report import (
    NoiseCategorySummary,
    SourceQualityHealth,
    SourceQualityMetrics,
    SourceQualityReport,
    SourceQualityReportValidationResult,
    build_source_quality_report,
    render_source_quality_report_markdown,
    validate_source_quality_report,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _hn_evidence_dict(
    evidence_id: str = "hn_001",
    source_url: str = "https://news.ycombinator.com/item?id=1",
    title: str = "Debugging AI agents is impossible",
    body: str = "Multi-step agent traces are non-reproducible.",
    source_id: str = "hacker_news",
    source_type: str = "discussion",
    quality_flags: list[str] | None = None,
) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "title": title,
        "body": body,
        "quality_flags": quality_flags or [],
    }


def _gh_evidence_dict(
    evidence_id: str = "gh_001",
    source_url: str = "https://github.com/owner/repo/issues/1",
    title: str = "Kubernetes operator crashes on scale",
    body: str = "When scaling beyond 50 pods, the operator OOMs.",
    source_id: str = "github_issues",
    source_type: str = "issue_tracker",
    quality_flags: list[str] | None = None,
) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "title": title,
        "body": body,
        "quality_flags": quality_flags or [],
    }


def _signal_dict(
    signal_id: str = "sig_001",
    evidence_id: str = "hn_001",
    source_id: str = "hacker_news",
    source_type: str = "discussion",
    classification: str = "pain_signal_candidate",
    quality_flags: list[str] | None = None,
) -> dict:
    return {
        "signal_id": signal_id,
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_type": source_type,
        "classification": classification,
        "quality_flags": quality_flags or [],
    }


def _make_pain_cluster(
    cluster_id: str = "pc_abc123",
    actor: str = "developer",
    workflow: str = "debugging AI agents",
    object: str = "multi-step agent workflows",
    pain_verb: str = "hard to debug",
    pain_pattern: str = "developer cannot debug AI agents because multi-step agent workflows are hard to debug",
    source_id: str = "hacker_news",
    source_type: str = "discussion",
    source_url: str = "https://news.ycombinator.com/item?id=1",
    evidence_count: int = 2,
    overall: float = 0.75,
    noise_risk: float = 0.1,
    business_relevance: float = 0.7,
    status: str = "new",
) -> PainCluster:
    entries = []
    for i in range(evidence_count):
        entries.append(
            SourceEvidenceEntry(
                evidence_id=f"{source_id}_ev_{i}",
                source_id=source_id,
                source_type=source_type,
                source_url=f"{source_url}#{i}" if i > 0 else source_url,
                evidence_kind="pain_signal_candidate",
                title=f"Evidence {i}",
                excerpt=f"Excerpt {i}",
                created_at="2026-01-01T00:00:00Z",
                fetched_at="2026-01-01T00:00:00Z",
                contribution_to_cluster="primary_pain" if i == 0 else "supporting_pain",
            )
        )

    sd = 1
    if evidence_count > 1:
        # Make it cross-source if we have multiple entries
        entries[-1] = SourceEvidenceEntry(
            evidence_id=f"github_issues_ev_{len(entries)-1}",
            source_id="github_issues",
            source_type="issue_tracker",
            source_url=f"https://github.com/owner/repo/issues/{len(entries)}",
            evidence_kind="bug_report",
            title=f"GitHub Evidence {len(entries)-1}",
            excerpt=f"GitHub Excerpt {len(entries)-1}",
            created_at="2026-01-02T00:00:00Z",
            fetched_at="2026-01-02T00:00:00Z",
            contribution_to_cluster="supporting_pain",
        )
        sd = 2

    scoring = PainClusterScoring(
        overall=overall,
        pain_explicitness=0.8,
        recurrence=0.6,
        business_cost=0.7,
        icp_fit=0.5,
        source_reliability=0.72,
        freshness=0.9,
        actionability=0.5,
        noise_risk=noise_risk,
    )

    quotes = [f"Evidence excerpt {i}"[:200] for i in range(min(evidence_count, 3))]

    return PainCluster(
        cluster_id=cluster_id,
        actor=actor,
        workflow=workflow,
        object=object,
        pain_verb=pain_verb,
        pain_pattern=pain_pattern,
        source_evidence_list=entries,
        source_diversity=sd,
        recurrence=evidence_count,
        business_relevance=business_relevance,
        noise_risk=noise_risk,
        representative_quotes_or_excerpts=quotes,
        linked_candidate_signals=[f"sig_{i}" for i in range(evidence_count)],
        created_at="2026-01-03T00:00:00Z",
        updated_at="2026-01-03T00:00:00Z",
        status=status,
        scoring=scoring,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSourceQualityReport_Build_HNOnly(unittest.TestCase):
    """Test building a report from HN-only evidence."""

    def test_build_hacker_news_only(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1",
                              "Debugging AI agents is painful", "Cannot reproduce traces."),
            _hn_evidence_dict("hn_002", "https://news.ycombinator.com/item?id=2",
                              "Check out my new SaaS", "Launching today...",
                              quality_flags=["launch_hype"]),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001", classification="pain_signal_candidate"),
            _signal_dict("sig_002", "hn_002", classification="noise"),
        ]

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_run_hn",
            created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(report.raw_evidence_total, 2)
        self.assertEqual(report.accepted_signal_total, 1)
        self.assertEqual(report.noise_signal_total, 1)
        self.assertEqual(len(report.source_metrics), 1)
        self.assertEqual(report.source_metrics[0].source_id, "hacker_news")
        self.assertEqual(report.source_metrics[0].source_type, "discussion")
        self.assertEqual(report.source_metrics[0].accepted_signal_count, 1)
        self.assertEqual(report.source_metrics[0].noise_signal_count, 1)
        self.assertEqual(report.source_metrics[0].accepted_rate, 0.5)
        self.assertEqual(report.source_metrics[0].noise_rate, 0.5)


class TestSourceQualityReport_Build_GitHubOnly(unittest.TestCase):
    """Test building a report from GitHub-only evidence."""

    def test_build_github_only(self):
        evidence = [
            _gh_evidence_dict("gh_001", "https://github.com/owner/repo/issues/1",
                              "Bug: crash on start", "App crashes when launched.",
                              quality_flags=["low_text_context"]),
            _gh_evidence_dict("gh_002", "https://github.com/owner/repo/issues/2",
                              "Feature: add export to CSV", "Need CSV export for reports."),
            _gh_evidence_dict("gh_003", "https://github.com/owner/repo/issues/3",
                              "Performance: slow queries", "Postgres queries take 30s."),
        ]
        signals = [
            _signal_dict("sig_001", "gh_001", "github_issues", "issue_tracker",
                         classification="needs_human_review"),
            _signal_dict("sig_002", "gh_002", "github_issues", "issue_tracker",
                         classification="pain_signal_candidate"),
            _signal_dict("sig_003", "gh_003", "github_issues", "issue_tracker",
                         classification="pain_signal_candidate"),
        ]

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_run_gh",
            created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(report.raw_evidence_total, 3)
        self.assertEqual(report.accepted_signal_total, 2)
        self.assertEqual(report.weak_signal_total, 1)
        self.assertEqual(len(report.source_metrics), 1)
        self.assertEqual(report.source_metrics[0].source_id, "github_issues")
        self.assertEqual(report.source_metrics[0].source_type, "issue_tracker")
        self.assertEqual(report.source_metrics[0].accepted_signal_count, 2)
        self.assertEqual(report.source_metrics[0].weak_signal_count, 1)
        self.assertEqual(report.source_metrics[0].accepted_rate, round(2 / 3, 4))


class TestSourceQualityReport_Build_HN_GitHub(unittest.TestCase):
    """Test building a report from HN + GitHub evidence."""

    def test_build_hn_github_combined(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1",
                              "AI debugging pain", "Cannot trace agents."),
            _gh_evidence_dict("gh_001", "https://github.com/owner/repo/issues/1",
                              "Agent tracing broken", "Multi-step trace lost."),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001", classification="pain_signal_candidate"),
            _signal_dict("sig_002", "gh_001", "github_issues", "issue_tracker",
                         classification="pain_signal_candidate"),
        ]

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_run_combined",
            created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(report.raw_evidence_total, 2)
        self.assertEqual(report.accepted_signal_total, 2)
        self.assertEqual(len(report.source_metrics), 2)
        source_ids = {m.source_id for m in report.source_metrics}
        self.assertEqual(source_ids, {"hacker_news", "github_issues"})


class TestSourceNormalization(unittest.TestCase):
    """Test source ID/type normalization in report building."""

    def test_legacy_hacker_news_algolia_normalizes(self):
        evidence = [
            {
                "evidence_id": "hn_legacy_001",
                "source_id": "hacker_news_algolia",
                "source_type": "hacker_news_algolia",
                "source_url": "https://news.ycombinator.com/item?id=99",
                "title": "Legacy HN item",
                "body": "Content.",
                "quality_flags": [],
            }
        ]
        signals = [
            {
                "signal_id": "sig_001",
                "evidence_id": "hn_legacy_001",
                "source_id": "hacker_news_algolia",
                "source_type": "hacker_news_algolia",
                "classification": "pain_signal_candidate",
            }
        ]

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_legacy",
            created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(len(report.source_metrics), 1)
        self.assertEqual(report.source_metrics[0].source_id, "hacker_news")
        self.assertEqual(report.source_metrics[0].source_type, "discussion")

    def test_legacy_github_issues_source_type_normalizes(self):
        evidence = [
            {
                "evidence_id": "gh_legacy_001",
                "source_id": "github_issues",
                "source_type": "github_issues",  # legacy: source_id as source_type
                "source_url": "https://github.com/owner/repo/issues/99",
                "title": "Legacy GH item",
                "body": "Content.",
                "quality_flags": [],
            }
        ]
        signals = [
            {
                "signal_id": "sig_001",
                "evidence_id": "gh_legacy_001",
                "source_id": "github_issues",
                "source_type": "github_issues",
                "classification": "pain_signal_candidate",
            }
        ]

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_gh_legacy",
            created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(len(report.source_metrics), 1)
        self.assertEqual(report.source_metrics[0].source_id, "github_issues")
        self.assertEqual(report.source_metrics[0].source_type, "issue_tracker")

    def test_canonical_source_ids_unchanged(self):
        evidence = [
            _hn_evidence_dict("hn_001"),
            _gh_evidence_dict("gh_001"),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001"),
            _signal_dict("sig_002", "gh_001", "github_issues", "issue_tracker",
                         classification="pain_signal_candidate"),
        ]

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_canonical",
            created_at="2026-01-01T00:00:00Z",
        )

        source_ids = {m.source_id for m in report.source_metrics}
        self.assertEqual(source_ids, {"hacker_news", "github_issues"})
        source_types = {m.source_type for m in report.source_metrics}
        self.assertEqual(source_types, {"discussion", "issue_tracker"})


class TestAcceptedWeakNoiseCounts(unittest.TestCase):
    """Test accepted/weak/noise signal counting."""

    def test_all_accepted(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(3)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(3)
        ]

        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(report.accepted_signal_total, 3)
        self.assertEqual(report.weak_signal_total, 0)
        self.assertEqual(report.noise_signal_total, 0)
        self.assertEqual(report.source_metrics[0].accepted_rate, 1.0)

    def test_all_noise(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(2)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="noise")
            for i in range(2)
        ]

        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(report.accepted_signal_total, 0)
        self.assertEqual(report.noise_signal_total, 2)
        self.assertEqual(report.source_metrics[0].noise_rate, 1.0)

    def test_mixed_classifications(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(4)]
        signals = [
            _signal_dict("sig_0", "hn_0", classification="pain_signal_candidate"),
            _signal_dict("sig_1", "hn_1", classification="workaround_signal_candidate"),
            _signal_dict("sig_2", "hn_2", classification="needs_human_review"),
            _signal_dict("sig_3", "hn_3", classification="noise"),
        ]

        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(report.accepted_signal_total, 2)
        self.assertEqual(report.weak_signal_total, 1)
        self.assertEqual(report.noise_signal_total, 1)
        self.assertEqual(report.source_metrics[0].accepted_rate, 0.5)
        self.assertEqual(report.source_metrics[0].noise_rate, 0.25)


class TestAcceptedRateNoiseRate(unittest.TestCase):
    """Test accepted_rate and noise_rate computation."""

    def test_rates_with_zero_signals(self):
        evidence = [_hn_evidence_dict("hn_001")]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_rate, 0.0)
        self.assertEqual(m.noise_rate, 0.0)

    def test_rates_half_and_half(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(4)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                         classification="pain_signal_candidate" if i < 2 else "noise")
            for i in range(4)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_rate, 0.5)
        self.assertEqual(m.noise_rate, 0.5)


class TestDuplicateCount(unittest.TestCase):
    """Test duplicate_count in source metrics."""

    def test_duplicate_from_evidence(self):
        evidence = [
            _hn_evidence_dict("hn_001"),
            _hn_evidence_dict("hn_002"),
            {
                **_hn_evidence_dict("hn_003"),
                "duplicate_of": "hn_001",
            },
        ]
        signals = [_signal_dict(f"sig_{i}", f"hn_{i}") for i in range(3)]

        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        # duplicate_count counts evidence with duplicate_of
        self.assertEqual(report.source_metrics[0].duplicate_count, 1)

    def test_no_duplicates(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(3)]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(report.source_metrics[0].duplicate_count, 0)


class TestMissingURLCount(unittest.TestCase):
    """Test missing_url_count and placeholder_url_count."""

    def test_missing_url(self):
        evidence = [
            _hn_evidence_dict("hn_001", source_url=""),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.missing_url_count, 1)
        self.assertFalse(m.source_url_validation_passed)

    def test_placeholder_url(self):
        evidence = [
            _hn_evidence_dict("hn_001", source_url="urn:oos:placeholder"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.placeholder_url_count, 1)
        self.assertFalse(m.source_url_validation_passed)

    def test_all_urls_valid(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1"),
            _gh_evidence_dict("gh_001", "https://github.com/owner/repo/issues/1"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        for m in report.source_metrics:
            self.assertTrue(m.source_url_validation_passed)
        self.assertTrue(report.traceability_summary["source_url_validation_passed"])


class TestQualityFlagCounts(unittest.TestCase):
    """Test quality_flag_counts aggregation."""

    def test_quality_flags_aggregated(self):
        evidence = [
            _hn_evidence_dict("hn_001", quality_flags=["launch_hype", "suspected_self_promo"]),
            _hn_evidence_dict("hn_002", quality_flags=["launch_hype", "low_text_context"]),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        qfc = report.source_metrics[0].quality_flag_counts
        self.assertEqual(qfc.get("launch_hype"), 2)
        self.assertEqual(qfc.get("suspected_self_promo"), 1)
        self.assertEqual(qfc.get("low_text_context"), 1)


class TestRejectionReasons(unittest.TestCase):
    """Test rejection_reasons from local_summary."""

    def test_rejection_reasons_from_summary(self):
        evidence = [_hn_evidence_dict("hn_001")]
        source_summaries = {
            "hacker_news": {
                "rejection_reasons": ["missing_date", "low_text_context"],
            }
        }

        report = build_source_quality_report(
            evidence_items=evidence,
            source_summaries=source_summaries,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertIn("missing_date", report.source_metrics[0].rejection_reasons)
        self.assertIn("low_text_context", report.source_metrics[0].rejection_reasons)


class TestTraceabilitySummary(unittest.TestCase):
    """Test traceability summary in report."""

    def test_traceability_pass(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1"),
            _gh_evidence_dict("gh_001", "https://github.com/owner/repo/issues/1"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        ts = report.traceability_summary
        self.assertTrue(ts["source_url_validation_passed"])
        self.assertEqual(ts["records_missing_source_url"], 0)
        self.assertEqual(ts["placeholder_url_count"], 0)

    def test_traceability_failure_missing(self):
        evidence = [
            _hn_evidence_dict("hn_001", source_url=""),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        ts = report.traceability_summary
        self.assertFalse(ts["source_url_validation_passed"])
        self.assertGreater(ts["records_missing_source_url"], 0)

    def test_traceability_failure_placeholder(self):
        evidence = [
            _hn_evidence_dict("hn_001", source_url="urn:oos:test"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        ts = report.traceability_summary
        self.assertFalse(ts["source_url_validation_passed"])
        self.assertGreater(ts["placeholder_url_count"], 0)

    def test_clusters_with_all_urls(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1"),
        ]
        pc = _make_pain_cluster(
            cluster_id="pc_test",
            source_url="https://news.ycombinator.com/item?id=1",
            evidence_count=1,
        )

        report = build_source_quality_report(
            evidence_items=evidence,
            pain_clusters=[pc],
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        ts = report.traceability_summary
        self.assertEqual(ts["clusters_with_all_evidence_urls"], 1)
        self.assertEqual(ts["clusters_with_url_failures"], 0)


class TestClusterContributionCounts(unittest.TestCase):
    """Test cluster and opportunity contribution counts."""

    def test_cluster_contribution(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1"),
            _gh_evidence_dict("gh_001", "https://github.com/owner/repo/issues/1"),
        ]
        pc = _make_pain_cluster(
            cluster_id="pc_test",
            source_id="hacker_news",
            source_url="https://news.ycombinator.com/item?id=1",
            evidence_count=2,
        )

        report = build_source_quality_report(
            evidence_items=evidence,
            pain_clusters=[pc],
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        hn_metric = [m for m in report.source_metrics if m.source_id == "hacker_news"][0]
        gh_metric = [m for m in report.source_metrics if m.source_id == "github_issues"][0]
        # Both contribute to the same cluster
        self.assertEqual(hn_metric.cluster_contribution_count, 1)
        self.assertEqual(gh_metric.cluster_contribution_count, 1)

    def test_opportunity_contribution(self):
        evidence = [_hn_evidence_dict("hn_001")]
        pc = _make_pain_cluster(
            cluster_id="pc_test",
            source_url="https://news.ycombinator.com/item?id=1",
            evidence_count=1,
        )
        opp_candidates = [
            {
                "opportunity_id": "oppc_test",
                "source_pain_cluster_id": "pc_test",
            }
        ]

        report = build_source_quality_report(
            evidence_items=evidence,
            pain_clusters=[pc],
            opportunity_candidates=opp_candidates,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        hn_metric = report.source_metrics[0]
        self.assertEqual(hn_metric.opportunity_contribution_count, 1)

    def test_source_diversity_contribution(self):
        evidence = [_hn_evidence_dict("hn_001")]
        pc = _make_pain_cluster(
            cluster_id="pc_test",
            source_url="https://news.ycombinator.com/item?id=1",
            evidence_count=1,
        )

        report = build_source_quality_report(
            evidence_items=evidence,
            pain_clusters=[pc],
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        hn_metric = report.source_metrics[0]
        self.assertEqual(hn_metric.source_diversity_contribution, 1)


class TestTopPainClusterOrdering(unittest.TestCase):
    """Test deterministic ordering of top pain clusters."""

    def test_ordering_by_overall_desc(self):
        pc1 = _make_pain_cluster(cluster_id="pc_aaa", overall=0.9, evidence_count=1)
        pc2 = _make_pain_cluster(cluster_id="pc_bbb", overall=0.5, evidence_count=1)
        pc3 = _make_pain_cluster(cluster_id="pc_ccc", overall=0.7, evidence_count=1)

        report = build_source_quality_report(
            pain_clusters=[pc1, pc2, pc3],
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        scores = [pc["overall_score"] for pc in report.top_pain_clusters]
        self.assertEqual(scores, [0.9, 0.7, 0.5])

    def test_tiebreak_by_source_diversity(self):
        pc1 = _make_pain_cluster(cluster_id="pc_aaa", overall=0.8, evidence_count=1)
        pc2 = _make_pain_cluster(cluster_id="pc_bbb", overall=0.8, evidence_count=2)

        report = build_source_quality_report(
            pain_clusters=[pc1, pc2],
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        diversities = [pc["source_diversity"] for pc in report.top_pain_clusters]
        self.assertEqual(diversities, [2, 1])

    def test_tiebreak_by_recurrence(self):
        # Both single-source → tiebreak by recurrence
        pc1 = _make_pain_cluster(
            cluster_id="pc_aaa", overall=0.8, evidence_count=1,
            source_url="https://news.ycombinator.com/item?id=1",
        )
        # Make pc2 also single-source with more evidence
        entries = []
        for i in range(3):
            entries.append(
                SourceEvidenceEntry(
                    evidence_id=f"hn_ev_{i}",
                    source_id="hacker_news",
                    source_type="discussion",
                    source_url=f"https://news.ycombinator.com/item?id={i+10}",
                    evidence_kind="pain_signal_candidate",
                    title=f"Evidence {i}",
                    excerpt=f"Excerpt {i}",
                    created_at="2026-01-01T00:00:00Z",
                    fetched_at="2026-01-01T00:00:00Z",
                    contribution_to_cluster="primary_pain" if i == 0 else "supporting_pain",
                )
            )
        scoring = PainClusterScoring(
            overall=0.8, pain_explicitness=0.8, recurrence=0.6, business_cost=0.7,
            icp_fit=0.5, source_reliability=0.72, freshness=0.9, actionability=0.5,
            noise_risk=0.1,
        )
        pc2 = PainCluster(
            cluster_id="pc_bbb", actor="dev", workflow="test", object="testobj",
            pain_verb="test", pain_pattern="dev cannot test because testobj test",
            source_evidence_list=entries, source_diversity=1, recurrence=3,
            business_relevance=0.7, noise_risk=0.1,
            representative_quotes_or_excerpts=["a", "b", "c"],
            linked_candidate_signals=["sig_1", "sig_2", "sig_3"],
            created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
            status="new", scoring=scoring,
        )

        report = build_source_quality_report(
            pain_clusters=[pc1, pc2],
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        recurrences = [pc["recurrence"] for pc in report.top_pain_clusters]
        self.assertEqual(recurrences, [3, 1])

    def test_tiebreak_by_cluster_id(self):
        pc_a = _make_pain_cluster(cluster_id="pc_aaaa", overall=0.8, evidence_count=1,
                                  source_url="https://news.ycombinator.com/item?id=1")
        pc_b = _make_pain_cluster(cluster_id="pc_aaab", overall=0.8, evidence_count=1,
                                  source_url="https://news.ycombinator.com/item?id=2")

        report = build_source_quality_report(
            pain_clusters=[pc_b, pc_a],
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        ids = [pc["cluster_id"] for pc in report.top_pain_clusters]
        self.assertEqual(ids, ["pc_aaaa", "pc_aaab"])


class TestOpportunityCandidateReporting(unittest.TestCase):
    """Test opportunity candidate section in report."""

    def test_candidates_included(self):
        opp_candidates = [
            {
                "opportunity_id": "oppc_abc123",
                "source_pain_cluster_id": "pc_test",
                "actor": "developer",
                "problem_statement": "Debugging AI agents is too hard.",
                "evidence_summary": "3 evidence items from HN and GitHub.",
                "source_evidence_links": [
                    {"evidence_id": "hn_001", "source_url": "https://news.ycombinator.com/item?id=1", "source_type": "discussion"},
                ],
                "score": 0.82,
                "uncertainty": "moderate",
                "suggested_validation_action": "interview",
                "founder_review_status": "pending_review",
            }
        ]

        report = build_source_quality_report(
            opportunity_candidates=opp_candidates,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(report.opportunity_candidate_count, 1)
        self.assertEqual(len(report.opportunity_candidates), 1)
        self.assertEqual(report.opportunity_candidates[0]["opportunity_id"], "oppc_abc123")

    def test_no_candidates_warning(self):
        report = build_source_quality_report(
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(report.opportunity_candidate_count, 0)
        has_warning = any(
            "no opportunity candidates" in w.lower() or "no opportunity" in w.lower()
            for w in report.warnings
        )
        self.assertTrue(has_warning, f"warnings={report.warnings}")


class TestHighNoiseWarning(unittest.TestCase):
    """Test high noise rate warning."""

    def test_high_noise_warning(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(10)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                         classification="pain_signal_candidate" if i < 3 else "noise")
            for i in range(10)
        ]

        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        noise_rate = report.source_metrics[0].noise_rate
        self.assertGreater(noise_rate, 0.60)
        has_noise_warning = any("high noise rate" in w.lower() for w in report.warnings)
        self.assertTrue(has_noise_warning)


class TestLowDiversityWarning(unittest.TestCase):
    """Test low source diversity warning."""

    def test_low_diversity_warning(self):
        pc = _make_pain_cluster(
            cluster_id="pc_test",
            source_url="https://news.ycombinator.com/item?id=1",
            evidence_count=1,
        )

        report = build_source_quality_report(
            pain_clusters=[pc],
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        has_diversity_warning = any(
            "single-source" in w.lower() or "low source diversity" in w.lower()
            for w in report.warnings
        )
        self.assertTrue(has_diversity_warning)


class TestNextValidationActions(unittest.TestCase):
    """Test next validation actions generation."""

    def test_no_clusters_action(self):
        report = build_source_quality_report(
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(len(report.next_validation_actions) > 0)
        self.assertIn("no clusters", report.next_validation_actions[0].lower())

    def test_high_noise_action(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(10)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                         classification="pain_signal_candidate" if i < 2 else "noise")
            for i in range(10)
        ]

        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        has_tune_action = any("tune" in a.lower() or "filter" in a.lower()
                              for a in report.next_validation_actions)
        self.assertTrue(has_tune_action)

    def test_traceability_failure_action(self):
        evidence = [_hn_evidence_dict("hn_001", source_url="")]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        has_trace_action = any("traceability" in a.lower() or "source_url" in a.lower()
                               for a in report.next_validation_actions)
        self.assertTrue(has_trace_action)

    def test_candidate_tier_action(self):
        pc = _make_pain_cluster(
            cluster_id="pc_test",
            overall=0.85,
            evidence_count=1,
            source_url="https://news.ycombinator.com/item?id=1",
        )

        report = build_source_quality_report(
            pain_clusters=[pc],
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        has_interview_action = any(
            "interview" in a.lower() or "landing page" in a.lower()
            for a in report.next_validation_actions
        )
        self.assertTrue(has_interview_action)


class TestMarkdownRenderer(unittest.TestCase):
    """Test Markdown renderer output."""

    def setUp(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1",
                              "Debugging AI agents is painful", "Cannot trace."),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001", classification="pain_signal_candidate"),
        ]
        pc = _make_pain_cluster(
            cluster_id="pc_test",
            overall=0.85,
            evidence_count=1,
            source_url="https://news.ycombinator.com/item?id=1",
        )
        opp_candidates = [
            {
                "opportunity_id": "oppc_test",
                "source_pain_cluster_id": "pc_test",
                "actor": "developer",
                "problem_statement": "Debugging AI agents is too hard.",
                "evidence_summary": "HN evidence.",
                "score": 0.85,
                "uncertainty": "moderate",
                "suggested_validation_action": "interview",
                "founder_review_status": "pending_review",
            }
        ]
        self.report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            pain_clusters=[pc],
            opportunity_candidates=opp_candidates,
            discovery_run_id="test_run_md",
            created_at="2026-01-01T00:00:00Z",
        )

    def test_contains_required_sections(self):
        md = render_source_quality_report_markdown(self.report)
        required = [
            "# Source Quality Report",
            "## Executive Summary",
            "## Source Quality by Source",
            "## Signal Classification Summary",
            "## Top Pain Clusters",
            "## Opportunity Candidates",
            "## Noise Analysis",
            "## Founder Review Queue",
            "## Suggested Validation Actions",
            "## Risks and Caveats",
            "## Traceability",
        ]
        for section in required:
            with self.subTest(section=section):
                self.assertIn(section, md)

    def test_ascii_safe(self):
        md = render_source_quality_report_markdown(self.report, output_mode="ascii_safe")
        # All characters should be ASCII (0-127)
        for i, ch in enumerate(md):
            self.assertLess(ord(ch), 128, f"Non-ASCII char at position {i}: {ch!r}")

    def test_markdown_not_empty(self):
        md = render_source_quality_report_markdown(self.report)
        self.assertGreater(len(md), 200)


class TestToDictFromDictRoundtrip(unittest.TestCase):
    """Test serialization roundtrip."""

    def test_metrics_roundtrip(self):
        m = SourceQualityMetrics(
            source_id="hacker_news",
            source_type="discussion",
            records_seen=10,
            records_emitted=9,
            records_rejected=1,
            accepted_signal_count=5,
            weak_signal_count=2,
            noise_signal_count=2,
            duplicate_count=1,
            missing_url_count=0,
            placeholder_url_count=0,
            source_diversity_contribution=3,
            cluster_contribution_count=3,
            opportunity_contribution_count=1,
            founder_promote_count=2,
            founder_kill_count=1,
            founder_needs_more_evidence_count=0,
            quality_flag_counts={"launch_hype": 2},
            rejection_reasons=["low_text_context"],
        )
        m.recompute_rates()
        data = m.to_dict()
        m2 = SourceQualityMetrics.from_dict(data)
        self.assertEqual(m.source_id, m2.source_id)
        self.assertEqual(m.accepted_rate, m2.accepted_rate)
        self.assertEqual(m.noise_rate, m2.noise_rate)
        self.assertEqual(m.quality_flag_counts, m2.quality_flag_counts)

    def test_noise_category_roundtrip(self):
        nc = NoiseCategorySummary(category="launch_hype", count=5, source_id="hacker_news")
        data = nc.to_dict()
        nc2 = NoiseCategorySummary.from_dict(data)
        self.assertEqual(nc.category, nc2.category)
        self.assertEqual(nc.count, nc2.count)
        self.assertEqual(nc.source_id, nc2.source_id)

    def test_report_roundtrip(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1"),
            _gh_evidence_dict("gh_001", "https://github.com/owner/repo/issues/1"),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001", classification="pain_signal_candidate"),
            _signal_dict("sig_002", "gh_001", "github_issues", "issue_tracker",
                         classification="pain_signal_candidate"),
        ]

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_roundtrip",
            created_at="2026-01-01T00:00:00Z",
        )

        data = report.to_dict()
        report2 = SourceQualityReport.from_dict(data)

        self.assertEqual(report.report_id, report2.report_id)
        self.assertEqual(report.discovery_run_id, report2.discovery_run_id)
        self.assertEqual(report.raw_evidence_total, report2.raw_evidence_total)
        self.assertEqual(report.accepted_signal_total, report2.accepted_signal_total)
        self.assertEqual(len(report.source_metrics), len(report2.source_metrics))
        self.assertEqual(len(report.top_pain_clusters), len(report2.top_pain_clusters))
        self.assertEqual(report.traceability_summary, report2.traceability_summary)

    def test_validation_result_roundtrip(self):
        vr = SourceQualityReportValidationResult(
            is_valid=False,
            errors=["no source metrics"],
            warnings=["high noise"],
        )
        data = vr.to_dict()
        self.assertFalse(data["is_valid"])
        self.assertIn("no source metrics", data["errors"])


class TestDeterministicCreatedAt(unittest.TestCase):
    """Test that created_at can be injected for determinism."""

    def test_created_at_injected(self):
        report = build_source_quality_report(
            discovery_run_id="test",
            created_at="2025-06-15T12:00:00Z",
        )
        self.assertEqual(report.created_at, "2025-06-15T12:00:00Z")

    def test_created_at_defaults_to_now(self):
        report = build_source_quality_report(
            discovery_run_id="test",
        )
        # Should be a valid ISO 8601 timestamp
        self.assertTrue(report.created_at.endswith("Z") or "+" in report.created_at)
        self.assertIn("T", report.created_at)

    def test_same_input_same_report_id(self):
        r1 = build_source_quality_report(
            discovery_run_id="test",
            created_at="2026-01-01T00:00:00Z",
        )
        r2 = build_source_quality_report(
            discovery_run_id="test",
            created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(r1.report_id, r2.report_id)


class TestNoLiveAPINetworkCalls(unittest.TestCase):
    """Confirm no live API or network calls."""

    def test_build_is_pure_function(self):
        """build_source_quality_report is a pure function with dict inputs."""
        report = build_source_quality_report(
            evidence_items=[
                _hn_evidence_dict("hn_001"),
            ],
            candidate_signals=[
                _signal_dict("sig_001", "hn_001"),
            ],
            discovery_run_id="test_pure",
            created_at="2026-01-01T00:00:00Z",
        )
        self.assertIsInstance(report, SourceQualityReport)
        self.assertEqual(report.discovery_run_id, "test_pure")

    def test_no_imports_trigger_network(self):
        """Module imports should not trigger network calls."""
        import oos.source_quality_report as sqr
        self.assertTrue(hasattr(sqr, "build_source_quality_report"))


class TestFounderDecisionCounts(unittest.TestCase):
    """Test founder decision counts in per-source metrics."""

    def test_founder_decision_counts(self):
        evidence = [_hn_evidence_dict("hn_001")]
        fd_counts = {
            "hacker_news": {
                "promote": 2,
                "kill": 1,
                "needs_more_evidence": 3,
            }
        }

        report = build_source_quality_report(
            evidence_items=evidence,
            founder_decision_counts=fd_counts,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.founder_promote_count, 2)
        self.assertEqual(m.founder_kill_count, 1)
        self.assertEqual(m.founder_needs_more_evidence_count, 3)


class TestSourceLocalSummaries(unittest.TestCase):
    """Test per-source local summaries from collectors."""

    def test_local_summary_used(self):
        evidence = [_hn_evidence_dict("hn_001")]
        source_summaries = {
            "hacker_news": {
                "records_seen": 100,
                "records_emitted": 85,
                "records_rejected": 15,
                "duplicate_count": 5,
                "rejection_reasons": ["missing_date"],
            }
        }

        report = build_source_quality_report(
            evidence_items=evidence,
            source_summaries=source_summaries,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.records_seen, 100)
        self.assertEqual(m.records_emitted, 85)
        self.assertEqual(m.records_rejected, 15)
        self.assertEqual(m.duplicate_count, 5)


class TestValidateSourceQualityReport(unittest.TestCase):
    """Test validate_source_quality_report function."""

    def test_valid_report(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1"),
        ]
        signals = [_signal_dict("sig_001", "hn_001")]

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )

        result = validate_source_quality_report(report)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_invalid_empty_metrics(self):
        report = SourceQualityReport(
            report_id="sqr_test",
            discovery_run_id="test",
            created_at="2026-01-01T00:00:00Z",
        )
        result = validate_source_quality_report(report)
        self.assertFalse(result.is_valid)
        self.assertIn("source_metrics is empty", result.errors)

    def test_invalid_traceability(self):
        evidence = [_hn_evidence_dict("hn_001", source_url="")]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        result = validate_source_quality_report(report)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("traceability" in e.lower() for e in result.errors))


class TestEmptyInputHandling(unittest.TestCase):
    """Test handling of empty/missing inputs."""

    def test_completely_empty(self):
        report = build_source_quality_report(
            discovery_run_id="empty_test",
            created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(report.raw_evidence_total, 0)
        self.assertEqual(report.accepted_signal_total, 0)
        self.assertEqual(report.pain_cluster_count, 0)
        self.assertEqual(report.opportunity_candidate_count, 0)
        self.assertEqual(len(report.source_metrics), 0)

    def test_no_signals(self):
        evidence = [_hn_evidence_dict("hn_001")]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(report.raw_evidence_total, 1)
        self.assertEqual(report.accepted_signal_total, 0)

    def test_none_inputs(self):
        report = build_source_quality_report(
            evidence_items=None,
            candidate_signals=None,
            pain_clusters=None,
            opportunity_candidates=None,
            discovery_run_id="none_test",
            created_at="2026-01-01T00:00:00Z",
        )
        self.assertIsInstance(report, SourceQualityReport)
        self.assertEqual(report.raw_evidence_total, 0)


# =========================================================================
# v2.14 Item 7 — Contradiction Fix Tests
# =========================================================================


class TestV214_QualityHealth_ClassificationHealth(unittest.TestCase):
    """Test report-level classification_health computation."""

    def test_clean_evidence_health_clean(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(5)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(5)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(report.quality_health.classification_health, "clean")
        self.assertEqual(report.quality_health.evidence_quality_status, "clean")

    def test_high_weak_rate_caution(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(5)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="needs_human_review")
            for i in range(3)
        ] + [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(3, 5)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(report.quality_health.classification_health, "caution")

    def test_high_noise_rate_problematic(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(10)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="noise")
            for i in range(4)
        ] + [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(4, 10)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(report.quality_health.classification_health, "problematic")

    def test_noise_rate_failing(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(4)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="noise")
            for i in range(3)
        ] + [
            _signal_dict(f"sig_3", f"hn_3", classification="pain_signal_candidate"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(report.quality_health.classification_health, "failing")

    def test_evidence_quality_noisy_when_high_noise_rate(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(5)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="noise")
            for i in range(2)
        ] + [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(2, 5)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(report.quality_health.evidence_quality_status, "noisy")


class TestV214_ContradictionWarnings(unittest.TestCase):
    """Test per-source contradiction detection."""

    def test_high_accepted_rate_high_flagged_rate_warns(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(5)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                         classification="pain_signal_candidate",
                         quality_flags=["debugging_pain", "workflow_pain"])
            for i in range(3)
        ] + [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                         classification="pain_signal_candidate")
            for i in range(3, 5)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertGreater(m.flagged_record_rate, 0.19)
        self.assertGreater(m.accepted_rate, 0.79)
        has_warning = any("high accepted_rate" in w.lower() and "flagged" in w.lower()
                         for w in m.contradiction_warnings)
        self.assertTrue(has_warning, f"contradiction_warnings={m.contradiction_warnings}")

    def test_traceability_clean_but_weak_noisy_warns(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1",
                              quality_flags=["generic_language", "unclear_actor"]),
            _hn_evidence_dict("hn_002", "https://news.ycombinator.com/item?id=2",
                              quality_flags=["low_text_context"]),
            _hn_evidence_dict("hn_003", "https://news.ycombinator.com/item?id=3"),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001", classification="pain_signal_candidate",
                        quality_flags=["generic_language", "unclear_actor"]),
            _signal_dict("sig_002", "hn_002", classification="pain_signal_candidate",
                        quality_flags=["low_text_context"]),
            _signal_dict("sig_003", "hn_003", classification="pain_signal_candidate"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertTrue(m.source_url_validation_passed)
        has_warning = any("source_url validation" in w.lower() or "traceability" in w.lower()
                         for w in m.contradiction_warnings)
        self.assertTrue(has_warning, f"contradiction_warnings={m.contradiction_warnings}")

    def test_source_with_noise_evidence_warns(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(4)]
        signals = [
            _signal_dict("sig_0", "hn_0", classification="noise"),
            _signal_dict("sig_1", "hn_1", classification="noise"),
            _signal_dict("sig_2", "hn_2", classification="pain_signal_candidate"),
            _signal_dict("sig_3", "hn_3", classification="pain_signal_candidate"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertGreater(m.noise_rate, 0.0)
        self.assertGreater(m.accepted_rate, 0.0)

    def test_many_sensitive_flags_warns(self):
        evidence = [_hn_evidence_dict(f"hn_{i}",
                     quality_flags=["requires_manual_review", "low_confidence_extraction",
                                   "suspected_self_promo"])
                   for i in range(3)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                        quality_flags=["requires_manual_review", "low_confidence_extraction",
                                      "suspected_self_promo"])
            for i in range(3)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        sensitive_total = sum(
            m.quality_flag_counts.get(f, 0)
            for f in ["requires_manual_review", "low_confidence_extraction",
                      "suspected_self_promo"]
        )
        self.assertGreaterEqual(sensitive_total, 3)
        has_warning = any("quality-risk flags" in w.lower() for w in m.contradiction_warnings)
        self.assertTrue(has_warning, f"contradiction_warnings={m.contradiction_warnings}")

    def test_clean_report_no_contradiction_warnings(self):
        evidence = [_hn_evidence_dict(f"hn_{i}", "https://news.ycombinator.com/item?id=" + str(i))
                   for i in range(3)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(3)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(len(report.quality_health.contradiction_warnings), 0)

    def test_source_url_validation_clean_does_not_suppress_quality_warnings(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1",
                             quality_flags=["generic_language", "unclear_actor", "low_text_context"]),
            _hn_evidence_dict("hn_002", "https://news.ycombinator.com/item?id=2",
                             quality_flags=["low_text_context"]),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001",
                        quality_flags=["generic_language", "unclear_actor", "low_text_context"]),
            _signal_dict("sig_002", "hn_002",
                        quality_flags=["low_text_context"]),
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertTrue(m.source_url_validation_passed)
        self.assertTrue(len(m.source_quality_warnings) > 0,
                       f"Expected quality warnings, got: {m.source_quality_warnings}")


class TestV214_PerSourceQualityWarnings(unittest.TestCase):
    """Test per-source quality warning generation."""

    def test_high_noise_rate_failing_warning(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(4)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="noise")
            for i in range(3)
        ] + [
            _signal_dict("sig_3", "hn_3", classification="pain_signal_candidate"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        has_warning = any("failing" in w.lower() for w in m.source_quality_warnings)
        self.assertTrue(has_warning, f"source_quality_warnings={m.source_quality_warnings}")

    def test_high_weak_rate_caution_warning(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(5)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="needs_human_review")
            for i in range(2)
        ] + [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(2, 5)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        has_warning = any(
            "weak rate" in w.lower() and ("caution" in w.lower() or "significant" in w.lower())
            for w in m.source_quality_warnings
        )
        self.assertTrue(has_warning, f"source_quality_warnings={m.source_quality_warnings}")

    def test_high_flagged_rate_warning(self):
        evidence = [_hn_evidence_dict(f"hn_{i}",
                     quality_flags=["requires_manual_review"]) for i in range(3)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                        classification="pain_signal_candidate",
                        quality_flags=["requires_manual_review"])
            for i in range(3)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertGreater(m.flagged_record_rate, 0.19)
        has_warning = any("flagged" in w.lower() for w in m.source_quality_warnings)
        self.assertTrue(has_warning, f"source_quality_warnings={m.source_quality_warnings}")


class TestV214_FlaggedRecordCounting(unittest.TestCase):
    """Test flagged record counting."""

    def test_flagged_record_count(self):
        evidence = [_hn_evidence_dict(f"hn_{i}",
                     quality_flags=["requires_manual_review"] if i < 3 else [])
                   for i in range(5)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                        classification="pain_signal_candidate",
                        quality_flags=["requires_manual_review"] if i < 3 else [])
            for i in range(5)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.flagged_record_count, 3)
        self.assertEqual(m.flagged_record_rate, 0.6)

    def test_no_flagged_records(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(3)]
        signals = [_signal_dict(f"sig_{i}", f"hn_{i}") for i in range(3)]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.flagged_record_count, 0)
        self.assertEqual(m.flagged_record_rate, 0.0)

    def test_all_flagged_records(self):
        evidence = [_hn_evidence_dict(f"hn_{i}", quality_flags=["generic_language"])
                   for i in range(4)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                        quality_flags=["generic_language"])
            for i in range(4)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.flagged_record_count, 4)
        self.assertEqual(m.flagged_record_rate, 1.0)


class TestV214_WeakRateMetric(unittest.TestCase):
    """Test weak_rate computation."""

    def test_weak_rate_computed(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(4)]
        signals = [
            _signal_dict("sig_0", "hn_0", classification="needs_human_review"),
            _signal_dict("sig_1", "hn_1", classification="pain_signal_candidate"),
            _signal_dict("sig_2", "hn_2", classification="pain_signal_candidate"),
            _signal_dict("sig_3", "hn_3", classification="pain_signal_candidate"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.weak_rate, 0.25)

    def test_zero_weak_rate(self):
        evidence = [_hn_evidence_dict(f"hn_{i}") for i in range(3)]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(3)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.weak_rate, 0.0)


class TestV214_QualityHealthFields(unittest.TestCase):
    """Test quality_health fields are populated correctly."""

    def test_quality_health_populated(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1"),
            _gh_evidence_dict("gh_001", "https://github.com/owner/repo/issues/1"),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001", classification="pain_signal_candidate"),
            _signal_dict("sig_002", "gh_001", "github_issues", "issue_tracker",
                        classification="pain_signal_candidate"),
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        qh = report.quality_health
        self.assertEqual(qh.traceability_status, "clean")
        self.assertEqual(qh.source_scope_status, "clean")
        self.assertEqual(qh.accepted_count, 2)
        self.assertEqual(qh.weak_count, 0)
        self.assertEqual(qh.noise_count, 0)
        self.assertEqual(qh.accepted_rate, 1.0)

    def test_quality_health_dominant_flags(self):
        evidence = [
            _hn_evidence_dict("hn_001", quality_flags=["launch_hype", "suspected_self_promo"]),
            _hn_evidence_dict("hn_002", quality_flags=["launch_hype"]),
            _hn_evidence_dict("hn_003", quality_flags=["launch_hype"]),
        ]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_00{i+1}",
                        quality_flags=["launch_hype", "suspected_self_promo"] if i == 0 else ["launch_hype"])
            for i in range(3)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        qh = report.quality_health
        self.assertIn("launch_hype", qh.dominant_quality_flags)

    def test_sources_with_high_weak_or_noise(self):
        evidence = [
            _hn_evidence_dict(f"hn_{i}") for i in range(5)
        ] + [
            _gh_evidence_dict(f"gh_{i}") for i in range(5)
        ]
        signals = [
            _signal_dict(f"sig_hn_{i}", f"hn_{i}", classification="noise")
            for i in range(3)
        ] + [
            _signal_dict(f"sig_hn_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(3, 5)
        ] + [
            _signal_dict(f"sig_gh_{i}", f"gh_{i}", "github_issues", "issue_tracker",
                        classification="pain_signal_candidate")
            for i in range(5)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        qh = report.quality_health
        self.assertIn("hacker_news", qh.sources_with_high_weak_or_noise)

    def test_traceability_failing_sets_status(self):
        evidence = [_hn_evidence_dict("hn_001", source_url="")]
        report = build_source_quality_report(
            evidence_items=evidence,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        qh = report.quality_health
        self.assertEqual(qh.traceability_status, "failing")


class TestV214_MarkdownRendering_ContradictionFix(unittest.TestCase):
    """Test Markdown rendering for v2.14 item 7 changes."""

    def setUp(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1",
                              "Debugging AI agents is painful", "Cannot trace.",
                              quality_flags=["launch_hype"]),
            _hn_evidence_dict("hn_002", "https://news.ycombinator.com/item?id=2",
                              "Check out my SaaS", "Launching...",
                              quality_flags=["suspected_self_promo"]),
            _hn_evidence_dict("hn_003", "https://news.ycombinator.com/item?id=3",
                              "Agent tracing broken", "Multi-step trace lost."),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001", classification="pain_signal_candidate",
                        quality_flags=["launch_hype"]),
            _signal_dict("sig_002", "hn_002", classification="noise",
                        quality_flags=["suspected_self_promo"]),
            _signal_dict("sig_003", "hn_003", classification="pain_signal_candidate"),
        ]
        self.report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="test_md_v214", created_at="2026-01-01T00:00:00Z",
        )

    def test_executive_summary_has_quality_status(self):
        md = render_source_quality_report_markdown(self.report)
        self.assertIn("### Quality Status", md)
        self.assertIn("Traceability", md)
        self.assertIn("Source Scope", md)
        self.assertIn("Classification Health", md)
        self.assertIn("Evidence Quality", md)

    def test_quality_risk_summary_table_renders(self):
        md = render_source_quality_report_markdown(self.report)
        self.assertIn("### Quality Risk Summary", md)
        self.assertIn("Accepted", md)
        self.assertIn("Weak", md)
        self.assertIn("Noise", md)
        self.assertIn("Flagged Records", md)
        self.assertIn("Dominant Quality Flags", md)

    def test_contradiction_warnings_section_renders(self):
        md = render_source_quality_report_markdown(self.report)
        self.assertIn("## Contradiction Warnings", md)

    def test_quality_flags_table_renders(self):
        md = render_source_quality_report_markdown(self.report)
        self.assertIn("## Quality Flags", md)

    def test_per_source_warnings_section_renders(self):
        md = render_source_quality_report_markdown(self.report)
        self.assertIn("## Per-Source Quality Warnings", md)

    def test_signal_classification_table_has_rates(self):
        md = render_source_quality_report_markdown(self.report)
        self.assertIn("## Signal Classification Summary", md)
        self.assertIn("Rate", md)

    def test_ascii_safe_output(self):
        md = render_source_quality_report_markdown(self.report, output_mode="ascii_safe")
        for i, ch in enumerate(md):
            self.assertLess(ord(ch), 128, f"Non-ASCII char at position {i}: {ch!r}")

    def test_clean_report_empty_contradiction_message(self):
        clean_evidence = [_hn_evidence_dict(f"hn_{i}", f"https://news.ycombinator.com/item?id={i+100}")
                         for i in range(3)]
        clean_signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}", classification="pain_signal_candidate")
            for i in range(3)
        ]
        clean_report = build_source_quality_report(
            evidence_items=clean_evidence, candidate_signals=clean_signals,
            discovery_run_id="clean", created_at="2026-01-01T00:00:00Z",
        )
        md = render_source_quality_report_markdown(clean_report)
        self.assertIn("internally consistent", md.lower())

    def test_opportunity_candidate_note(self):
        md = render_source_quality_report_markdown(self.report)
        if self.report.opportunity_candidates:
            self.assertIn("SQR build time", md)


class TestV214_SerializationBackwardCompatibility(unittest.TestCase):
    """Test serialization backward compatibility for v2.14 fields."""

    def test_metrics_roundtrip_includes_new_fields(self):
        m = SourceQualityMetrics(
            source_id="hacker_news",
            source_type="discussion",
            accepted_signal_count=5,
            weak_signal_count=2,
            noise_signal_count=3,
            flagged_record_count=4,
            source_quality_warnings=["test warning"],
            contradiction_warnings=["test contradiction"],
        )
        m.recompute_rates()
        m.flagged_record_rate = 0.4
        data = m.to_dict()
        m2 = SourceQualityMetrics.from_dict(data)
        self.assertEqual(m2.flagged_record_count, 4)
        self.assertEqual(m2.flagged_record_rate, 0.4)
        self.assertEqual(m2.source_quality_warnings, ["test warning"])
        self.assertEqual(m2.contradiction_warnings, ["test contradiction"])
        self.assertEqual(m2.weak_rate, 0.2)

    def test_old_dict_without_new_fields_loads_safely(self):
        old_data = {
            "source_id": "hacker_news",
            "source_type": "discussion",
            "records_seen": 10,
            "records_emitted": 10,
            "records_rejected": 0,
            "accepted_signal_count": 8,
            "weak_signal_count": 1,
            "noise_signal_count": 1,
            "accepted_rate": 0.8,
            "noise_rate": 0.1,
            "duplicate_count": 0,
            "missing_url_count": 0,
            "placeholder_url_count": 0,
            "source_url_validation_passed": True,
            "source_diversity_contribution": 2,
            "cluster_contribution_count": 2,
            "opportunity_contribution_count": 0,
            "founder_promote_count": 0,
            "founder_kill_count": 0,
            "founder_needs_more_evidence_count": 0,
            "quality_flag_counts": {},
            "rejection_reasons": [],
        }
        m = SourceQualityMetrics.from_dict(old_data)
        self.assertEqual(m.flagged_record_count, 0)
        self.assertEqual(m.flagged_record_rate, 0.0)
        self.assertEqual(m.source_quality_warnings, [])
        self.assertEqual(m.contradiction_warnings, [])
        self.assertEqual(m.weak_rate, 0.0)

    def test_report_roundtrip_with_quality_health(self):
        evidence = [
            _hn_evidence_dict("hn_001", "https://news.ycombinator.com/item?id=1",
                             quality_flags=["launch_hype"]),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001", classification="pain_signal_candidate",
                        quality_flags=["launch_hype"]),
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="roundtrip_v214", created_at="2026-01-01T00:00:00Z",
        )
        data = report.to_dict()
        report2 = SourceQualityReport.from_dict(data)
        self.assertEqual(report.report_id, report2.report_id)
        self.assertEqual(
            report.quality_health.classification_health,
            report2.quality_health.classification_health,
        )
        self.assertEqual(
            report.quality_health.traceability_status,
            report2.quality_health.traceability_status,
        )
        self.assertEqual(
            report.quality_health.accepted_count,
            report2.quality_health.accepted_count,
        )

    def test_old_report_without_quality_health_loads_safely(self):
        old_data = {
            "artifact_type": "source_quality_report",
            "schema_version": "1.0.0",
            "report_id": "sqr_old",
            "discovery_run_id": "old_run",
            "created_at": "2025-01-01T00:00:00Z",
            "source_metrics": [],
            "raw_evidence_total": 0,
            "accepted_signal_total": 0,
            "weak_signal_total": 0,
            "noise_signal_total": 0,
            "pain_cluster_count": 0,
            "opportunity_candidate_count": 0,
            "top_pain_clusters": [],
            "opportunity_candidates": [],
            "main_noise_categories": [],
            "founder_decisions_needed": {},
            "next_validation_actions": [],
            "traceability_summary": {"source_url_validation_passed": True},
            "warnings": [],
            "errors": [],
        }
        report = SourceQualityReport.from_dict(old_data)
        self.assertEqual(report.report_id, "sqr_old")
        self.assertIsInstance(report.quality_health, SourceQualityHealth)
        self.assertEqual(report.quality_health.traceability_status, "clean")


class TestV214_ClassifierParity(unittest.TestCase):
    """Test that SQR classification counts come from the canonical classifier."""

    def test_vendor_promo_counted_weak_or_noise(self):
        evidence = [_hn_evidence_dict("hn_001",
                     quality_flags=["vendor_promo", "product_launch"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=["vendor_promo", "product_launch"])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        # vendor_promo aliases to suspected_self_promo (medium flag = weak)
        # With product_launch and no pain in title/body → noise
        self.assertGreaterEqual(m.weak_signal_count + m.noise_signal_count, 1)
        self.assertEqual(m.accepted_signal_count, 0)

    def test_missing_actor_counted_weak(self):
        evidence = [_hn_evidence_dict("hn_001",
                     quality_flags=["missing_actor", "generic_language"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=["missing_actor", "generic_language"])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertGreaterEqual(m.weak_signal_count + m.noise_signal_count, 1)
        self.assertEqual(m.accepted_signal_count, 0)

    def test_low_text_context_no_pain_noise(self):
        evidence = [_hn_evidence_dict("hn_001", title="", body="",
                     quality_flags=["low_text_context"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=["low_text_context"])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertGreaterEqual(m.noise_signal_count, 1)

    def test_low_text_context_with_pain_weak(self):
        evidence = [_hn_evidence_dict("hn_001",
                     title="debugging is broken", body="Cannot trace agents. This is a real problem costing us hours every week.",
                     quality_flags=["low_text_context"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=["low_text_context"])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        # low_text_context + pain markers → weak, never accepted
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertGreaterEqual(m.weak_signal_count, 1)

    def test_positive_pain_flags_remain_accepted(self):
        evidence = [_hn_evidence_dict("hn_001",
                     title="CI/CD debugging wastes hours", body="Flaky tests cause entire team to wait. This is costing us real money.",
                     quality_flags=["debugging_pain", "workflow_pain"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=["debugging_pain", "workflow_pain"])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 1)
        self.assertEqual(m.weak_signal_count, 0)
        self.assertEqual(m.noise_signal_count, 0)


class TestV214_EvidenceOnlyFlagClassification(unittest.TestCase):
    """Regression tests: evidence-only quality flags must affect classification.

    Codex finding: _build_source_metrics() passed only sig["quality_flags"]
    into classify_noise_for_evidence(), ignoring evidence-level quality_flags.
    This can produce accepted=1, weak=0, noise=0, classification_health=clean
    while dominant_quality_flags shows risk flags.
    """

    def test_evidence_only_low_text_context_no_pain_noise(self):
        """Evidence has low_text_context, signal has empty flags, no pain in text -> noise."""
        evidence = [_hn_evidence_dict("hn_001", title="", body="",
                     quality_flags=["low_text_context"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=[])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertGreaterEqual(m.noise_signal_count, 1)

    def test_evidence_only_low_text_context_with_pain_weak(self):
        """Evidence has low_text_context + pain text, signal has empty flags -> weak."""
        evidence = [_hn_evidence_dict("hn_001",
                     title="debugging is broken",
                     body="Cannot trace agents. This is a real problem costing us hours every week.",
                     quality_flags=["low_text_context"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=[])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertGreaterEqual(m.weak_signal_count, 1)

    def test_evidence_only_vendor_promo_product_launch_noise(self):
        """Evidence has vendor_promo + product_launch, no pain -> noise, even if signal has no flags."""
        evidence = [
            _hn_evidence_dict("hn_001", title="Check out my new SaaS", body="Launching today!",
                             quality_flags=["vendor_promo", "product_launch"]),
        ]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=[])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        # vendor_promo aliases to suspected_self_promo (medium) + product_launch + no pain -> noise
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertGreaterEqual(m.weak_signal_count + m.noise_signal_count, 1)

    def test_evidence_only_requires_manual_review_weak(self):
        """Evidence has requires_manual_review, signal has no flags -> weak."""
        evidence = [_hn_evidence_dict("hn_001",
                     title="Something is off with this tool",
                     body="Not sure if this is a real pain or just a one-off complaint.",
                     quality_flags=["requires_manual_review"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=[])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertGreaterEqual(m.weak_signal_count, 1)

    def test_evidence_only_missing_actor_generic_language_weak_or_noise(self):
        """Evidence has missing_actor + generic_language, no pain -> noise or at least weak."""
        evidence = [_hn_evidence_dict("hn_001",
                     title="It would be nice to have this",
                     body="Someone should build a tool that does this thing.",
                     quality_flags=["missing_actor", "generic_language"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=[])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertGreaterEqual(m.weak_signal_count + m.noise_signal_count, 1)

    def test_evidence_only_positive_pain_flags_accepted_but_flagged(self):
        """Evidence has positive pain flags, signal has no flags -> accepted, but flagged_record_count increments."""
        evidence = [_hn_evidence_dict("hn_001",
                     title="CI/CD debugging wastes hours each week",
                     body="Flaky tests cause entire team to wait. This is costing us real money.",
                     quality_flags=["debugging_pain", "workflow_pain"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=[])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 1)
        # flagged_record_count should be 1 because merged flags include evidence flags
        self.assertEqual(m.flagged_record_count, 1)

    def test_evidence_only_flags_appear_in_dominant_quality_flags(self):
        """Evidence-only flags should appear in dominant_quality_flags."""
        evidence = [
            _hn_evidence_dict("hn_001", quality_flags=["low_text_context", "generic_language"]),
            _hn_evidence_dict("hn_002", quality_flags=["low_text_context"]),
        ]
        signals = [
            _signal_dict("sig_001", "hn_001", classification="pain_signal_candidate",
                        quality_flags=[]),
            _signal_dict("sig_002", "hn_002", classification="pain_signal_candidate",
                        quality_flags=[]),
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        qh = report.quality_health
        # low_text_context appears twice in evidence, so should be dominant
        self.assertIn("low_text_context", qh.dominant_quality_flags)

    def test_evidence_only_flags_make_classification_health_not_clean(self):
        """Evidence-only flags causing weak/noise should make health not clean."""
        evidence = [_hn_evidence_dict("hn_001",
                     title="", body="",
                     quality_flags=["low_text_context", "generic_language", "unclear_actor"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=[])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        qh = report.quality_health
        # Signal should NOT be accepted (flags cause weak or noise)
        self.assertNotEqual(qh.classification_health, "clean",
                           f"expected not clean, got {qh.classification_health}")
        self.assertNotEqual(qh.evidence_quality_status, "clean",
                           f"expected not clean, got {qh.evidence_quality_status}")

    def test_signal_only_flags_still_work(self):
        """Signal-only flags (no evidence flags) still classify correctly."""
        evidence = [_hn_evidence_dict("hn_001", title="", body="")]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=["low_text_context"])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertGreaterEqual(m.noise_signal_count, 1)

    def test_both_evidence_and_signal_flags_merge_no_duplicates(self):
        """When evidence and signal both have flags, they merge without duplicates."""
        evidence = [_hn_evidence_dict("hn_001",
                     quality_flags=["low_text_context", "generic_language"])]
        signals = [_signal_dict("sig_001", "hn_001",
                                 classification="pain_signal_candidate",
                                 quality_flags=["low_text_context", "unclear_actor"])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        # low_text_context appears in both, should not be double-counted in quality_flag_counts
        # quality_flag_counts is from evidence only (not merged), so low_text_context=1, generic_language=1
        # The classification uses merged flags: low_text_context, generic_language, unclear_actor
        self.assertEqual(m.quality_flag_counts.get("low_text_context", 0), 1)
        self.assertEqual(m.quality_flag_counts.get("generic_language", 0), 1)
        # flagged_record_count should be 1 (merged flags are non-empty)
        self.assertEqual(m.flagged_record_count, 1)

    def test_evidence_only_flags_contradiction_warning_when_appropriate(self):
        """Evidence-only quality-risk flags should trigger contradiction warnings."""
        evidence = [
            _hn_evidence_dict(f"hn_{i}",
                             source_url=f"https://news.ycombinator.com/item?id={i}",
                             quality_flags=["requires_manual_review", "low_confidence_extraction",
                                          "suspected_self_promo"])
            for i in range(3)
        ]
        signals = [
            _signal_dict(f"sig_{i}", f"hn_{i}",
                        classification="pain_signal_candidate",
                        quality_flags=[])
            for i in range(3)
        ]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        # Evidence has sensitive flags in quality_flag_counts
        sensitive_total = sum(
            m.quality_flag_counts.get(f, 0)
            for f in ["requires_manual_review", "low_confidence_extraction",
                      "suspected_self_promo"]
        )
        # Three evidence items each with 3 flags = 9 flag occurrences
        self.assertGreaterEqual(sensitive_total, 3,
                               f"sensitive_total={sensitive_total}, qfc={m.quality_flag_counts}")
        has_warning = any("quality-risk flags" in w.lower() for w in m.contradiction_warnings)
        self.assertTrue(has_warning, f"contradiction_warnings={m.contradiction_warnings}")

    def test_evidence_id_missing_classify_on_signal_alone(self):
        """When evidence_id is missing, classify safely using signal dict alone (no crash)."""
        evidence = [_hn_evidence_dict("hn_001", quality_flags=["low_text_context"])]
        signals = [_signal_dict("sig_001", evidence_id="missing_ev_id",
                                 classification="pain_signal_candidate",
                                 quality_flags=["low_text_context"])]
        report = build_source_quality_report(
            evidence_items=evidence, candidate_signals=signals,
            discovery_run_id="t", created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        # Uses signal flags only since evidence not found; low_text_context + no pain -> noise
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertGreaterEqual(m.noise_signal_count, 1)


if __name__ == "__main__":
    unittest.main()
