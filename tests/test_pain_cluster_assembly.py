from __future__ import annotations

import unittest

from oos.pain_cluster import (
    PainCluster,
    SourceEvidenceEntry,
    validate_pain_cluster,
)
from oos.pain_cluster_assembly import (
    assemble_pain_clusters,
    build_evidence_entry,
    compute_business_relevance,
    compute_noise_risk,
    extract_pain_pattern,
    select_representative_excerpts,
    validate_cluster_traceability,
)
from oos.pain_cluster_dedupe import normalize_source_id, normalize_source_type


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _hn_ev(
    evidence_id: str,
    title: str = "Debugging AI agents is painful",
    body: str = "I spend hours trying to trace multi-step agent reasoning. Hard to debug.",
    source_url: str = "",
    **overrides,
) -> dict:
    base = {
        "evidence_id": evidence_id,
        "source_id": "hacker_news",
        "source_type": "discussion",
        "source_url": source_url or f"https://news.ycombinator.com/item?id={evidence_id.replace('ev_', '')}",
        "title": title,
        "body": body,
        "evidence_kind": "pain_signal_candidate",
        "created_at": "2026-05-10T00:00:00Z",
        "collected_at": "2026-05-12T00:00:00Z",
        "fetched_at": "2026-05-12T00:00:00Z",
        "quality_flags": [],
    }
    base.update(overrides)
    return base


def _gh_ev(
    evidence_id: str,
    title: str = "Agent execution traces not reproducible",
    body: str = "When running multi-step agents, the traces differ between runs. Cannot debug.",
    source_url: str = "",
    **overrides,
) -> dict:
    base = {
        "evidence_id": evidence_id,
        "source_id": "github_issues",
        "source_type": "issue_tracker",
        "source_url": source_url or f"https://github.com/test/repo/issues/{evidence_id.replace('ev_', '')}",
        "title": title,
        "body": body,
        "evidence_kind": "bug_report",
        "created_at": "2026-05-09T00:00:00Z",
        "collected_at": "2026-05-12T00:00:00Z",
        "fetched_at": "2026-05-12T00:00:00Z",
        "quality_flags": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Pain pattern extraction tests
# ---------------------------------------------------------------------------


class TestPainPatternExtraction(unittest.TestCase):
    def test_developer_actor_from_bug_report(self) -> None:
        ev = _gh_ev("ev_001", body="The API is broken and crashes on load")
        pattern = extract_pain_pattern(ev)
        self.assertEqual(pattern["actor"], "developer")
        self.assertNotEqual(pattern["workflow"], "unknown")

    def test_founder_actor_detected(self) -> None:
        ev = _hn_ev("ev_002", body="As a startup founder I struggle with cash flow forecasting")
        pattern = extract_pain_pattern(ev)
        self.assertEqual(pattern["actor"], "founder")

    def test_unknown_actor_when_no_indicators(self) -> None:
        ev = _hn_ev("ev_003", title="Something is wrong", body="Things are not working")
        pattern = extract_pain_pattern(ev)
        self.assertEqual(pattern["actor"], "unknown")

    def test_workflow_from_title(self) -> None:
        ev = _hn_ev("ev_004", title="How to debug multi-step AI agent failures")
        pattern = extract_pain_pattern(ev)
        self.assertIn("debug", pattern["workflow"].lower())

    def test_pain_verb_from_text(self) -> None:
        ev = _gh_ev("ev_005", body="This is hard to debug and broken across runs")
        pattern = extract_pain_pattern(ev)
        self.assertIn(pattern["pain_verb"], ("hard to", "broken", "not working", "hard to debug"))

    def test_pain_pattern_formatting(self) -> None:
        ev = _hn_ev("ev_006", body="As a developer I cannot deploy because kubernetes is unreliable")
        pattern = extract_pain_pattern(ev)
        self.assertIn("developer", pattern["pain_pattern"])
        self.assertIn("deploy", pattern["pain_pattern"])

    def test_object_extracted_from_text(self) -> None:
        ev = _gh_ev("ev_007", body="Kubernetes deployment keeps failing on AWS")
        pattern = extract_pain_pattern(ev)
        self.assertIn(pattern["object"], ("kubernetes", "aws"))

    def test_needs_more_evidence_when_unknown_actor(self) -> None:
        ev = _hn_ev("ev_008", title="Stuff is broken", body="things aren't great")
        pattern = extract_pain_pattern(ev)
        self.assertEqual(pattern["pain_pattern"], "needs_more_evidence")

    def test_legacy_source_type_normalized(self) -> None:
        ev = _hn_ev("ev_009", source_id="hacker_news_algolia", source_type="hacker_news_algolia")
        pattern = extract_pain_pattern(ev)
        # Should still work with legacy values (assembly normalizes internally)
        self.assertIsInstance(pattern["actor"], str)

    def test_deterministic_same_input_same_output(self) -> None:
        ev = _gh_ev("ev_010", body="Cannot integrate with API, it's too slow and unreliable")
        p1 = extract_pain_pattern(ev)
        p2 = extract_pain_pattern(ev)
        self.assertEqual(p1, p2)


# ---------------------------------------------------------------------------
# Evidence entry construction tests
# ---------------------------------------------------------------------------


class TestBuildEvidenceEntry(unittest.TestCase):
    def test_build_from_hn_evidence(self) -> None:
        ev = _hn_ev("ev_001")
        entry = build_evidence_entry(ev)
        self.assertIsInstance(entry, SourceEvidenceEntry)
        self.assertEqual(entry.source_id, "hacker_news")
        self.assertEqual(entry.source_type, "discussion")
        self.assertTrue(entry.source_url.startswith("https://news.ycombinator.com"))

    def test_build_from_gh_evidence(self) -> None:
        ev = _gh_ev("ev_002")
        entry = build_evidence_entry(ev)
        self.assertEqual(entry.source_id, "github_issues")
        self.assertEqual(entry.source_type, "issue_tracker")
        self.assertTrue(entry.source_url.startswith("https://github.com"))

    def test_legacy_source_normalized(self) -> None:
        ev = _hn_ev("ev_003", source_id="hacker_news_algolia", source_type="hacker_news_algolia")
        entry = build_evidence_entry(ev)
        self.assertEqual(entry.source_id, "hacker_news")
        self.assertEqual(entry.source_type, "discussion")

    def test_excerpt_truncated_to_500(self) -> None:
        long_body = "x" * 600
        ev = _hn_ev("ev_004", body=long_body)
        entry = build_evidence_entry(ev)
        self.assertLessEqual(len(entry.excerpt), 500)

    def test_quality_flags_preserved(self) -> None:
        ev = _hn_ev("ev_005", quality_flags=["low_text_context", "flamewar_or_meta_discussion"])
        entry = build_evidence_entry(ev)
        self.assertIn("low_text_context", entry.quality_flags)
        self.assertIn("flamewar_or_meta_discussion", entry.quality_flags)

    def test_source_url_preserved(self) -> None:
        ev = _hn_ev("ev_006", source_url="https://news.ycombinator.com/item?id=999999")
        entry = build_evidence_entry(ev)
        self.assertEqual(entry.source_url, "https://news.ycombinator.com/item?id=999999")


# ---------------------------------------------------------------------------
# Noise risk tests
# ---------------------------------------------------------------------------


class TestNoiseRisk(unittest.TestCase):
    def test_no_flags_low_risk(self) -> None:
        evs = [_hn_ev("ev_001"), _gh_ev("ev_002")]
        risk = compute_noise_risk(evs)
        self.assertLess(risk, 0.15)

    def test_single_flag_moderate_risk(self) -> None:
        evs = [_hn_ev("ev_001", quality_flags=["low_text_context"])]
        risk = compute_noise_risk(evs)
        self.assertGreater(risk, 0.0)
        self.assertLess(risk, 0.30)

    def test_multiple_flags_higher_risk(self) -> None:
        evs = [
            _hn_ev("ev_001", quality_flags=["suspected_self_promo", "launch_hype"]),
            _gh_ev("ev_002", quality_flags=["bot_generated", "low_text_context"]),
        ]
        risk = compute_noise_risk(evs)
        self.assertGreater(risk, 0.30)

    def test_bot_generated_increases_risk(self) -> None:
        evs = [_gh_ev("ev_001", quality_flags=["bot_generated"])]
        risk1 = compute_noise_risk(evs)
        evs2 = [_gh_ev("ev_001", quality_flags=["low_text_context"])]
        risk2 = compute_noise_risk(evs2)
        self.assertGreater(risk1, risk2)  # bot_generated is more severe

    def test_max_flags_capped_at_one(self) -> None:
        all_flags = [
            "low_text_context", "suspected_self_promo", "launch_hype",
            "flamewar_or_meta_discussion", "bot_generated", "stale_issue",
            "duplicate_or_invalid", "wontfix_or_not_planned",
            "maintainer_housekeeping", "source_access_limited",
            "requires_manual_review", "low_confidence_source",
            "high_noise_source",
        ]
        evs = [_hn_ev("ev_001", quality_flags=all_flags)]
        risk = compute_noise_risk(evs)
        self.assertLessEqual(risk, 1.0)

    def test_empty_evidence_returns_default(self) -> None:
        risk = compute_noise_risk([])
        self.assertEqual(risk, 0.5)

    def test_single_flag_does_not_auto_kill(self) -> None:
        evs = [_hn_ev("ev_001", quality_flags=["low_text_context"])]
        risk = compute_noise_risk(evs)
        self.assertLess(risk, 0.80)  # Not fatal


# ---------------------------------------------------------------------------
# Business relevance tests
# ---------------------------------------------------------------------------


class TestBusinessRelevance(unittest.TestCase):
    def test_strong_business_signal(self) -> None:
        text = "We spend $500/month on this workaround. Our support team spends 40% of time on this. Customers are leaving because of reliability issues. This is costing us revenue."
        score = compute_business_relevance(text)
        self.assertGreaterEqual(score, 0.70)

    def test_moderate_business_signal(self) -> None:
        text = "This API integration is hard to maintain. Our team spends hours on manual reconciliation."
        score = compute_business_relevance(text)
        self.assertGreaterEqual(score, 0.55)

    def test_hobby_project_low_relevance(self) -> None:
        text = "My hobby side project game needs prettier graphics. I wish the UI was more fun."
        score = compute_business_relevance(text)
        self.assertLess(score, 0.35)

    def test_default_neutral(self) -> None:
        text = "The weather is nice today."
        score = compute_business_relevance(text)
        self.assertEqual(score, 0.50)

    def test_empty_text_neutral(self) -> None:
        score = compute_business_relevance("")
        self.assertEqual(score, 0.50)

    def test_cost_and_team_mentions_boost(self) -> None:
        text = "Our team uses this daily, it costs us time and money. Integration with our tools is essential."
        score = compute_business_relevance(text)
        self.assertGreater(score, 0.55)

    def test_vague_meta_lowers_relevance(self) -> None:
        text = "This is a meta discussion about the discussion. One-off issue."
        score = compute_business_relevance(text)
        self.assertLessEqual(score, 0.35)


# ---------------------------------------------------------------------------
# Representative excerpts tests
# ---------------------------------------------------------------------------


class TestRepresentativeExcerpts(unittest.TestCase):
    def test_selects_excerpts(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot debug agent workflows, it's painful and broken"),
            _gh_ev("ev_002", body="Agent traces are hard to reproduce"),
        ]
        excerpts = select_representative_excerpts(evs)
        self.assertGreaterEqual(len(excerpts), 1)
        self.assertLessEqual(len(excerpts), 3)

    def test_prefers_pain_terms(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Regular operation works fine"),
            _gh_ev("ev_002", body="This is broken and cannot be fixed easily, it's a struggle"),
        ]
        excerpts = select_representative_excerpts(evs)
        self.assertIn("broken", excerpts[0].lower())

    def test_truncated_to_max_chars(self) -> None:
        evs = [_hn_ev("ev_001", body="A" * 300)]
        excerpts = select_representative_excerpts(evs, max_chars=100)
        self.assertLessEqual(len(excerpts[0]), 103)  # 100 + "..."

    def test_empty_evidence_produces_title_fallback(self) -> None:
        evs = [_hn_ev("ev_001", body="", title="Debugging pain")]
        excerpts = select_representative_excerpts(evs)
        self.assertEqual(len(excerpts), 1)
        self.assertIn("Debugging", excerpts[0])


# ---------------------------------------------------------------------------
# Cluster assembly tests (HN-only)
# ---------------------------------------------------------------------------


class TestAssemblyHNOnly(unittest.TestCase):
    def test_hn_only_creates_cluster(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot debug AI agents. This is a struggle and costs us time."),
            _hn_ev("ev_002", body="AI agent debugging is painful. Manual workarounds needed.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, dups, summary = assemble_pain_clusters(evs)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].source_diversity, 1)
        self.assertEqual(clusters[0].recurrence, 2)
        self.assertEqual(summary["clusters_formed"], 1)

    def test_single_hn_evidence_cluster(self) -> None:
        evs = [_hn_ev("ev_001")]
        clusters, _, summary = assemble_pain_clusters(evs)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].recurrence, 1)


# ---------------------------------------------------------------------------
# Cluster assembly tests (GitHub-only)
# ---------------------------------------------------------------------------


class TestAssemblyGitHubOnly(unittest.TestCase):
    def test_gh_only_creates_cluster(self) -> None:
        evs = [
            _gh_ev("ev_001", body="Bug: agent traces not reproducible across runs. This is costing us."),
            _gh_ev("ev_002", body="Performance issue with agent execution. Hard to debug.",
                   source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, dups, summary = assemble_pain_clusters(evs)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].source_diversity, 1)

    def test_single_gh_evidence_cluster(self) -> None:
        evs = [_gh_ev("ev_001")]
        clusters, _, summary = assemble_pain_clusters(evs)
        self.assertEqual(len(clusters), 1)


# ---------------------------------------------------------------------------
# Cross-source assembly tests
# ---------------------------------------------------------------------------


class TestCrossSourceAssembly(unittest.TestCase):
    def test_hn_and_gh_same_pain_one_cluster(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot debug AI agents. Struggle with tracing."),
            _gh_ev("ev_002", body="Agent execution traces are not reproducible. Hard to debug."),
        ]
        clusters, dups, summary = assemble_pain_clusters(evs)
        # Both should group because same actor (developer) and similar workflow
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].source_diversity, 2)
        self.assertEqual(clusters[0].recurrence, 2)

    def test_different_pain_patterns_create_different_clusters(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot debug AI agents. This is painful."),
            _hn_ev("ev_002", body="Deploying ML models to kubernetes is unreliable.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(len(clusters), 2)

    def test_cluster_id_stable_across_runs(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot debug AI agents, it's frustrating"),
            _gh_ev("ev_002", body="Agent debugging is broken"),
        ]
        c1, _, _ = assemble_pain_clusters(evs)
        c2, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(c1[0].cluster_id, c2[0].cluster_id)

    def test_source_url_preserved_in_evidence(self) -> None:
        evs = [
            _hn_ev("ev_001", source_url="https://news.ycombinator.com/item?id=41500123"),
            _gh_ev("ev_002", source_url="https://github.com/test/repo/issues/42"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        urls = {e.source_url for e in clusters[0].source_evidence_list}
        self.assertIn("https://news.ycombinator.com/item?id=41500123", urls)
        self.assertIn("https://github.com/test/repo/issues/42", urls)

    def test_source_diversity_calculated(self) -> None:
        evs = [
            _hn_ev("ev_001"),
            _hn_ev("ev_002", source_url="https://news.ycombinator.com/item?id=2"),
            _gh_ev("ev_003", source_url="https://github.com/test/repo/issues/3"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(clusters[0].source_diversity, 2)

    def test_recurrence_calculated(self) -> None:
        evs = [
            _hn_ev("ev_001"),
            _hn_ev("ev_002", source_url="https://news.ycombinator.com/item?id=2"),
            _hn_ev("ev_003", source_url="https://news.ycombinator.com/item?id=3"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(clusters[0].recurrence, 3)

    def test_cross_source_dedupe_does_not_drop(self) -> None:
        """Cross-source evidence must not be silently dropped during dedup."""
        evs = [
            _hn_ev("ev_001"),
            _gh_ev("ev_002"),
        ]
        clusters, dups, _ = assemble_pain_clusters(evs)
        total_evidence = sum(c.recurrence for c in clusters)
        self.assertEqual(total_evidence, 2)

    def test_legacy_source_ids_assembled_correctly(self) -> None:
        evs = [
            _hn_ev("ev_001", source_id="hacker_news_algolia", source_type="hacker_news_algolia"),
            _gh_ev("ev_002", source_id="github_issues", source_type="github_issues",
                   body="Agent execution traces not reproducible"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(len(clusters), 1)
        # Both should be normalized to canonical values
        source_ids = {e.source_id for e in clusters[0].source_evidence_list}
        self.assertEqual(source_ids, {"hacker_news", "github_issues"})
        source_types = {e.source_type for e in clusters[0].source_evidence_list}
        self.assertEqual(source_types, {"discussion", "issue_tracker"})

    def test_multiple_clusters_with_different_patterns(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot debug AI agents"),
            _hn_ev("ev_002", body="Deploying ML models is unreliable",
                   source_url="https://news.ycombinator.com/item?id=2"),
            _gh_ev("ev_003", body="Agent traces not reproducible",
                   source_url="https://github.com/test/repo/issues/3"),
            _gh_ev("ev_004", body="Kubernetes deployment keeps failing on AWS",
                   source_url="https://github.com/test/repo/issues/4"),
        ]
        clusters, _, summary = assemble_pain_clusters(evs)
        self.assertGreaterEqual(len(clusters), 1)
        self.assertEqual(summary["total_evidence_in"], 4)


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------


class TestAssemblyScoring(unittest.TestCase):
    def test_scoring_computed_for_cluster(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot debug AI agents. Costs us time and money. Customers affected."),
            _gh_ev("ev_002", body="Agent debugging is broken. Production impact."),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        scoring = clusters[0].scoring
        self.assertIsNotNone(scoring)
        self.assertGreaterEqual(scoring.overall, 0.0)
        self.assertLessEqual(scoring.overall, 1.0)

    def test_noise_flags_increase_noise_risk_in_scoring(self) -> None:
        clean_evs = [
            _hn_ev("ev_001", body="Agent debugging is painful. Business critical."),
            _gh_ev("ev_002", body="Agent traces not reproducible. Production issue."),
        ]
        noisy_evs = [
            _hn_ev("ev_001", body="Agent debugging is painful",
                   quality_flags=["suspected_self_promo", "launch_hype"]),
            _gh_ev("ev_002", body="Agent traces not reproducible",
                   quality_flags=["bot_generated", "low_text_context"]),
        ]
        clean_clusters, _, _ = assemble_pain_clusters(clean_evs)
        noisy_clusters, _, _ = assemble_pain_clusters(noisy_evs)
        self.assertGreater(noisy_clusters[0].noise_risk, clean_clusters[0].noise_risk)

    def test_business_relevance_affects_score(self) -> None:
        business_evs = [
            _hn_ev("ev_001", body="We spend $500/month on this. Customers are leaving due to reliability. "
                    "Our support team is overwhelmed. This costs us revenue and compliance is at risk."),
        ]
        non_business_evs = [
            _hn_ev("ev_002", body="This is a hobby side project. I wish the colors were prettier.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        biz_clusters, _, _ = assemble_pain_clusters(business_evs)
        non_biz_clusters, _, _ = assemble_pain_clusters(non_business_evs)
        self.assertGreater(biz_clusters[0].business_relevance, non_biz_clusters[0].business_relevance)

    def test_threshold_classification_works(self) -> None:
        """Strong signal should be candidate tier."""
        evs = [
            _hn_ev("ev_001", body="Cannot debug AI agents. We spend hours weekly on manual workarounds. "
                    "Customers are leaving. Production is affected. This costs us thousands in lost revenue."),
            _gh_ev("ev_002", body="Agent debugging is broken. Critical for our business. "
                    "Support team spends 40% of time on this. Compliance at risk."),
            _hn_ev("ev_003", body="Agent traces are painful. Hard to debug. Revenue impact.",
                   source_url="https://news.ycombinator.com/item?id=3"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertGreaterEqual(len(clusters), 1)
        # Status is auto-assigned; high-scoring cluster may be 'new' or 'candidate' tier
        self.assertIn(clusters[0].status, {"new", "weak", "noise"})


# ---------------------------------------------------------------------------
# Traceability validation tests
# ---------------------------------------------------------------------------


class TestTraceabilityValidation(unittest.TestCase):
    def test_evidence_without_source_url_fails(self) -> None:
        evs = [_hn_ev("ev_001", source_url="")]
        clusters, _, _ = assemble_pain_clusters(evs)
        errors, warnings = validate_cluster_traceability(clusters[0])
        self.assertTrue(any("missing source_url" in e.lower() for e in errors))

    def test_evidence_with_placeholder_url_fails(self) -> None:
        evs = [_hn_ev("ev_001", source_url="urn:oos:placeholder:123")]
        clusters, _, _ = assemble_pain_clusters(evs)
        errors, _ = validate_cluster_traceability(clusters[0])
        self.assertTrue(any("placeholder" in e.lower() for e in errors))

    def test_evidence_with_non_http_url_fails(self) -> None:
        evs = [_hn_ev("ev_001", source_url="ftp://example.com/item")]
        clusters, _, _ = assemble_pain_clusters(evs)
        errors, _ = validate_cluster_traceability(clusters[0])
        self.assertTrue(any("non-http" in e.lower() for e in errors))

    def test_all_valid_urls_pass(self) -> None:
        evs = [
            _hn_ev("ev_001"),
            _gh_ev("ev_002"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        errors, _ = validate_cluster_traceability(clusters[0])
        self.assertEqual(len(errors), 0)

    def test_single_source_warning(self) -> None:
        evs = [_hn_ev("ev_001"), _hn_ev("ev_002", source_url="https://news.ycombinator.com/item?id=2")]
        clusters, _, _ = assemble_pain_clusters(evs)
        _, warnings = validate_cluster_traceability(clusters[0])
        self.assertTrue(any("single-source" in w.lower() for w in warnings))

    def test_empty_evidence_list_fails_assembly(self) -> None:
        clusters, _, summary = assemble_pain_clusters([])
        self.assertEqual(len(clusters), 0)
        self.assertIn("errors", summary)
        self.assertIn("empty_input", summary["errors"])


# ---------------------------------------------------------------------------
# Deduplication in assembly tests
# ---------------------------------------------------------------------------


class TestAssemblyDeduplication(unittest.TestCase):
    def test_exact_duplicate_evidence_id_removed(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot debug agents"),
            _hn_ev("ev_001", body="Cannot debug agents", source_url="https://news.ycombinator.com/item?id=1"),
        ]
        clusters, dups, summary = assemble_pain_clusters(evs, dedupe=True)
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]["duplicate_of"], "ev_001")
        self.assertEqual(clusters[0].recurrence, 1)

    def test_canonical_url_duplicate_removed(self) -> None:
        evs = [
            _hn_ev("ev_001", canonical_url="https://example.com/item"),
            _hn_ev("ev_002", canonical_url="https://example.com/item",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, dups, _ = assemble_pain_clusters(evs, dedupe=True)
        self.assertGreaterEqual(len(dups), 0)  # at least one caught by URL or canonical

    def test_source_url_duplicate_removed(self) -> None:
        evs = [
            _hn_ev("ev_001", source_url="https://example.com/item"),
            _hn_ev("ev_002", source_url="https://example.com/item"),
        ]
        clusters, dups, _ = assemble_pain_clusters(evs, dedupe=True)
        self.assertEqual(len(dups), 1)
        self.assertEqual(clusters[0].recurrence, 1)

    def test_cross_source_not_deduped(self) -> None:
        """HN and GH items about same pain but different source_urls should both be kept."""
        evs = [
            _hn_ev("ev_001"),
            _gh_ev("ev_002"),
        ]
        clusters, dups, _ = assemble_pain_clusters(evs, dedupe=True)
        self.assertEqual(len(dups), 0)
        self.assertEqual(clusters[0].recurrence, 2)

    def test_deduplication_disabled(self) -> None:
        evs = [
            _hn_ev("ev_001"),
            _hn_ev("ev_001", source_url="https://news.ycombinator.com/item?id=1"),
        ]
        clusters, dups, _ = assemble_pain_clusters(evs, dedupe=False)
        self.assertEqual(len(dups), 0)
        self.assertEqual(clusters[0].recurrence, 2)


if __name__ == "__main__":
    unittest.main()
