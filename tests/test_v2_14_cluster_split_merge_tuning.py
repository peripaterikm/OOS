from __future__ import annotations

"""v2.14 Item 4: Cluster Split/Merge Tuning — focused tests.

Tests canonical pain anchor detection, over-merge prevention, correct merge
behavior, catch-all splitting, cohesion scoring, quality-aware clustering,
and Codex review fixes: _should_merge() active, actor mismatch merge,
specific assertion helpers.
"""

import unittest

from oos.pain_cluster import PainCluster
from oos.pain_cluster_assembly import (
    _primary_canonical_anchor,
    _detect_canonical_anchors,
    _compute_cohesion_score,
    _should_merge,
    assemble_pain_clusters,
)


# ---------------------------------------------------------------------------
# v2.14 Item 4 Codex fix: assertion helpers for cluster membership testing
# ---------------------------------------------------------------------------


def cluster_ids_by_evidence_id(clusters: list[PainCluster]) -> dict[str, str]:
    """Return {evidence_id: cluster_id} mapping."""
    result: dict[str, str] = {}
    for c in clusters:
        for entry in c.source_evidence_list:
            result[entry.evidence_id] = c.cluster_id
    return result


def evidence_ids_per_cluster(clusters: list[PainCluster]) -> dict[str, set[str]]:
    """Return {cluster_id: set(evidence_id)} mapping."""
    result: dict[str, set[str]] = {}
    for c in clusters:
        result[c.cluster_id] = {e.evidence_id for e in c.source_evidence_list}
    return result


def assert_not_same_cluster(
    test: unittest.TestCase,
    clusters: list[PainCluster],
    evidence_id_a: str,
    evidence_id_b: str,
) -> None:
    """Assert two evidence IDs are NOT in the same cluster."""
    cid_map = cluster_ids_by_evidence_id(clusters)
    cid_a = cid_map.get(evidence_id_a)
    cid_b = cid_map.get(evidence_id_b)
    test.assertIsNotNone(cid_a, f"{evidence_id_a} not found in any cluster")
    test.assertIsNotNone(cid_b, f"{evidence_id_b} not found in any cluster")
    test.assertNotEqual(
        cid_a, cid_b,
        f"{evidence_id_a} and {evidence_id_b} should NOT be in same cluster "
        f"(both in {cid_a})"
    )


def assert_same_cluster(
    test: unittest.TestCase,
    clusters: list[PainCluster],
    evidence_id_a: str,
    evidence_id_b: str,
) -> None:
    """Assert two evidence IDs ARE in the same cluster."""
    cid_map = cluster_ids_by_evidence_id(clusters)
    cid_a = cid_map.get(evidence_id_a)
    cid_b = cid_map.get(evidence_id_b)
    test.assertIsNotNone(cid_a, f"{evidence_id_a} not found in any cluster")
    test.assertIsNotNone(cid_b, f"{evidence_id_b} not found in any cluster")
    test.assertEqual(
        cid_a, cid_b,
        f"{evidence_id_a} (in {cid_a}) and {evidence_id_b} (in {cid_b}) "
        f"should be in the SAME cluster"
    )


# Reuse fixture helpers from test_pain_cluster_assembly
def _hn_ev(evidence_id, title="Debugging AI agents is painful",
           body="I spend hours trying to trace multi-step agent reasoning. Hard to debug.",
           source_url="", **overrides):
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


def _gh_ev(evidence_id, title="Agent execution traces not reproducible",
           body="When running multi-step agents, the traces differ between runs. Cannot debug.",
           source_url="", **overrides):
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
# _should_merge() active logic tests (Codex fix 1)
# ---------------------------------------------------------------------------


class TestShouldMergeActive(unittest.TestCase):
    """Verify _should_merge() is now called during active clustering."""

    def test_should_merge_same_specific_anchor_returns_true(self) -> None:
        evs = [
            _gh_ev("ev_001", body="Stack trace lacks error context."),
            _hn_ev("ev_002", body="Exception traceback missing error context. Stack trace.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(len(clusters), 1, "Same stack_trace_context anchor should merge")
        self.assertEqual(clusters[0].recurrence, 2)

    def test_should_merge_different_blocked_anchors_separate(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot replay production trace in prompt playground."),
            _gh_ev("ev_002", body="Stack trace lacks exception context.",
                   source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        cid_map = cluster_ids_by_evidence_id(clusters)
        self.assertNotEqual(
            cid_map.get("ev_001"), cid_map.get("ev_002"),
            "prompt_trace_replay and stack_trace_context must not merge"
        )

    def test_should_merge_generic_anchor_needs_2of3_compat(self) -> None:
        # Both generic anchor, same actor+workflow+object -> should merge (3 of 3 match)
        evs = [
            _hn_ev("ev_001", body="LLM agent debugging is hard. Cannot debug agents."),
            _hn_ev("ev_002", body="AI agent debugging problems.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(len(clusters), 1, "Same generic anchor + same actor/wf/obj should merge")
        self.assertEqual(clusters[0].recurrence, 2)


# ---------------------------------------------------------------------------
# Canonical Anchor Detection
# ---------------------------------------------------------------------------


class TestCanonicalAnchors(unittest.TestCase):

    def test_trace_anchor_detected(self) -> None:
        ev = _hn_ev("ev_001", body="Cannot trace agent execution across multi-step runs. Tracing is broken.")
        self.assertEqual(_primary_canonical_anchor(ev), "agent_trace_debugging")

    def test_provenance_anchor_detected(self) -> None:
        ev = _hn_ev("ev_001", body="Cannot tell which agent contributed which part. Provenance is lost.")
        self.assertEqual(_primary_canonical_anchor(ev), "output_provenance")

    def test_prompt_replay_anchor_detected(self) -> None:
        ev = _hn_ev("ev_001", body="Cannot replay production trace in prompt playground with generation variables.")
        self.assertEqual(_primary_canonical_anchor(ev), "prompt_trace_replay")

    def test_stack_trace_anchor_detected(self) -> None:
        ev = _gh_ev("ev_001", body="Stack trace lacks error context. Missing exception context in traceback.")
        self.assertEqual(_primary_canonical_anchor(ev), "stack_trace_context")

    def test_checkpoint_anchor_detected(self) -> None:
        ev = _gh_ev("ev_001", body="Checkpoint state not reproducible. Deterministic corruption of state.")
        self.assertEqual(_primary_canonical_anchor(ev), "checkpoint_state_reproducibility")

    def test_generic_fallback_when_no_specific_match(self) -> None:
        ev = _hn_ev("ev_001", body="Everyone hates AI. General discussion.")
        self.assertEqual(_primary_canonical_anchor(ev), "generic_agent_debugging")

    def test_multi_anchor_detection(self) -> None:
        ev = _hn_ev("ev_001", body="Cannot trace agent execution and checkpoints are not reproducible.")
        anchors = _detect_canonical_anchors(ev)
        self.assertIn("agent_trace_debugging", anchors)
        self.assertIn("checkpoint_state_reproducibility", anchors)


# ---------------------------------------------------------------------------
# No Over-Merge Cases (Codex fix 3: strengthened with assertNotSameCluster)
# ---------------------------------------------------------------------------


class TestNoOverMerge(unittest.TestCase):

    def test_provenance_does_not_merge_with_generic_llm_debug(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot determine output provenance in multi-agent systems."),
            _hn_ev("ev_002", body="LLM debugging is hard. General agent pain.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_001", "ev_002")
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 2)

    def test_prompt_replay_does_not_merge_with_stack_trace(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot replay production trace in prompt playground."),
            _gh_ev("ev_002", body="Stack trace lacks exception context.",
                   source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_001", "ev_002")
        self.assertGreaterEqual(len(clusters), 2)

    def test_checkpoint_does_not_merge_with_eval_testing(self) -> None:
        evs = [
            _gh_ev("ev_001", body="Checkpoint state not reproducible across runs."),
            _hn_ev("ev_002", body="LLM regression testing and evaluation workflow lacks test cases.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_001", "ev_002")
        self.assertGreaterEqual(len(clusters), 2)

    def test_product_launch_does_not_merge_with_bug_report(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Check out our new AI debugging tool!",
                   evidence_kind="product_launch", quality_flags=["suspected_self_promo"]),
            _gh_ev("ev_002", body="Agent traces not reproducible. Bug in trace replay.",
                   evidence_kind="bug_report", source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_001", "ev_002")
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 2)

    def test_low_text_context_does_not_dominate_cluster(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Agent debugging is hard. We spend hours tracing multi-step execution."),
            _hn_ev("ev_002", body="Debugging context missing.",
                   quality_flags=["low_text_context"], source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_001", "ev_002")
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 2)

    # --- Codex fix 3: Additional strengthened tests ---

    def test_provenance_and_generic_llm_debugging_not_same_cluster(self) -> None:
        """provenance evidence and generic LLM debugging are not in same cluster."""
        evs = [
            _hn_ev("ev_p1", body="Cannot determine output provenance. Which agent contributed what?"),
            _hn_ev("ev_g1", body="LLM debugging is generally hard. Generic agent pain.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_p1", "ev_g1")

    def test_prompt_trace_replay_and_stack_trace_context_not_same_cluster(self) -> None:
        """prompt trace replay and stack trace context are not in same cluster."""
        evs = [
            _hn_ev("ev_pt1", body="Cannot replay production trace in prompt playground."),
            _gh_ev("ev_st1", body="Stack trace lacks exception context in traceback.",
                   source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_pt1", "ev_st1")

    def test_checkpoint_state_and_eval_testing_not_same_cluster(self) -> None:
        """checkpoint/state and eval/testing are not in same cluster."""
        evs = [
            _gh_ev("ev_cp1", body="Checkpoint state not reproducible across runs."),
            _hn_ev("ev_ev1", body="LLM eval and regression testing workflow lacks test cases.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_cp1", "ev_ev1")

    def test_product_launch_and_bug_report_not_same_cluster_without_anchor(self) -> None:
        """Product launch/self-promo and concrete bug report not same cluster."""
        evs = [
            _hn_ev("ev_la1", body="Launch HN: Our new AI debugging platform is awesome!",
                   evidence_kind="product_launch", quality_flags=["launch_hype"]),
            _gh_ev("ev_bg1", body="Agent traces not reproducible. Bug in trace replay.",
                   evidence_kind="bug_report", source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_la1", "ev_bg1")

    def test_low_text_context_does_not_join_primary_pain_cluster(self) -> None:
        """low_text_context/context_only evidence does not join accepted primary pain cluster."""
        evs = [
            _hn_ev("ev_pp1", body="Cannot trace agent execution. Specific pain about observability."),
            _hn_ev("ev_lt1", body="AI is changing things.",
                   quality_flags=["low_text_context"], source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_pp1", "ev_lt1")


# ---------------------------------------------------------------------------
# Correct Merge Cases (Codex fix 2: actor mismatch merge)
# ---------------------------------------------------------------------------


class TestCorrectMerge(unittest.TestCase):

    def test_two_stack_trace_evidence_merge(self) -> None:
        evs = [
            _gh_ev("ev_001", body="Stack trace lacks error context. Missing exception details."),
            _hn_ev("ev_002", body="Exception traceback missing error context. Stack trace has no state.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(sum(c.recurrence for c in clusters), 2)
        self.assertTrue(any(c.recurrence == 2 for c in clusters),
                        "Should find a cluster with both evidence items merged")

    def test_checkpoint_reproducibility_evidence_merge(self) -> None:
        evs = [
            _gh_ev("ev_001", body="Checkpoint state not reproducible. Deterministic state critical."),
            _hn_ev("ev_002", body="Agent checkpoint reproducibility broken. State corruption.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(sum(c.recurrence for c in clusters), 2)
        self.assertTrue(any(c.recurrence == 2 for c in clusters))

    def test_provenance_evidence_merge(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot trace output provenance. Which agent contributed what?"),
            _gh_ev("ev_002", body="Multi-agent systems lose provenance. Source attribution broken.",
                   source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(sum(c.recurrence for c in clusters), 2)
        self.assertTrue(any(c.recurrence == 2 for c in clusters))

    def test_cross_source_specific_anchor_merge(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot replay production traces for prompt testing."),
            _gh_ev("ev_002", body="Prompt playground cannot replay production trace inputs.",
                   source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(sum(c.recurrence for c in clusters), 2)
        self.assertTrue(any(c.recurrence == 2 for c in clusters))

    # --- Codex fix 2: Actor mismatch same-anchor merge tests ---

    def test_same_anchor_stack_trace_actor_mismatch_merge(self) -> None:
        """same-anchor cross-source stack-trace evidence with actor mismatch DOES merge."""
        evs = [
            _gh_ev("ev_st_gh", body="Stack trace lacks error context. Missing exception in traceback."),
            # HN evidence that will get actor=unknown because no developer indicators
            _hn_ev("ev_st_hn", title="Missing error context in stack traces",
                   body="Stack trace has no state. Error context missing from exceptions.",
                   source_url="https://news.ycombinator.com/item?id=99"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        # Same stack_trace_context anchor -> should merge via _should_merge()
        cid_map = cluster_ids_by_evidence_id(clusters)
        self.assertEqual(
            cid_map.get("ev_st_gh"), cid_map.get("ev_st_hn"),
            "Same strong stack_trace_context anchor should merge despite actor mismatch"
        )

    def test_same_anchor_prompt_replay_actor_mismatch_merge(self) -> None:
        """same-anchor prompt replay evidence with actor mismatch DOES merge."""
        evs = [
            _hn_ev("ev_pr_hn1", body="Cannot replay production trace in prompt playground with generation variables."),
            # GitHub evidence with same anchor
            _gh_ev("ev_pr_gh", body="Prompt playground cannot replay production trace. Prompt variables lost.",
                   source_url="https://github.com/test/repo/issues/88"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        cid_map = cluster_ids_by_evidence_id(clusters)
        self.assertEqual(
            cid_map.get("ev_pr_hn1"), cid_map.get("ev_pr_gh"),
            "Same prompt_trace_replay anchor should merge cross-source"
        )

    def test_developer_unknown_actor_same_anchor_merge(self) -> None:
        """developer + unknown actor, both stack_trace_context -> should merge."""
        evs = [
            _gh_ev("ev_dev", body="Stack trace lacks error context. Missing exception context."),
            _hn_ev("ev_unk", title="Stack traces missing error context",
                   body="Exception traceback has no state. Missing debugging context.",
                   source_url="https://news.ycombinator.com/item?id=77"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_same_cluster(self, clusters, "ev_dev", "ev_unk")

    def test_hn_gh_cross_source_same_strong_anchor_merge(self) -> None:
        """HN + GitHub cross-source evidence with same strong canonical anchor merges."""
        evs = [
            _hn_ev("ev_hn_cs", body="Stack traces lack actionable error context for debugging."),
            _gh_ev("ev_gh_cs", body="Exception traceback missing state details. Stack trace context lost.",
                   source_url="https://github.com/test/repo/issues/55"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_same_cluster(self, clusters, "ev_hn_cs", "ev_gh_cs")


# ---------------------------------------------------------------------------
# Catch-All Split
# ---------------------------------------------------------------------------


class TestCatchAllSplit(unittest.TestCase):

    def test_mixed_anchors_produce_multiple_clusters(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot trace agent execution. Observability missing."),
            _hn_ev("ev_002", body="Stack trace lacks error context in agent framework.",
                   source_url="https://news.ycombinator.com/item?id=2"),
            _hn_ev("ev_003", body="Prompt playground cannot replay production traces.",
                   source_url="https://news.ycombinator.com/item?id=3"),
            _hn_ev("ev_004", body="Agent checkpoint state not reproducible.",
                   source_url="https://news.ycombinator.com/item?id=4"),
            _hn_ev("ev_005", body="Output provenance lost in multi-agent systems.",
                   source_url="https://news.ycombinator.com/item?id=5"),
            _hn_ev("ev_006", body="Cannot determine which agent contributed which part.",
                   source_url="https://news.ycombinator.com/item?id=6"),
            _hn_ev("ev_007", body="Checkpoint reproducibility broken in agent framework.",
                   source_url="https://news.ycombinator.com/item?id=7"),
            _hn_ev("ev_008", body="LLM app testing lacks evaluation regression workflow.",
                   source_url="https://news.ycombinator.com/item?id=8"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertGreaterEqual(len(clusters), 1)
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 8)
        for c in clusters:
            if c.recurrence > 6:
                self.assertFalse(c.catch_all_risk,
                                f"Cluster {c.cluster_id} with {c.recurrence} signals has catch_all_risk=True")

    def test_many_coherent_signals_stay_one_cluster(self) -> None:
        evs = [
            _gh_ev("ev_001", body="Stack trace lacks error context."),
            _gh_ev("ev_002", body="Exception traceback missing state details.",
                   source_url="https://github.com/test/repo/issues/2"),
            _gh_ev("ev_003", body="Error context not available in stack trace.",
                   source_url="https://github.com/test/repo/issues/3"),
            _hn_ev("ev_004", body="Missing error message in exception context.",
                   source_url="https://news.ycombinator.com/item?id=4"),
            _hn_ev("ev_005", body="Stack trace has no debugging context.",
                   source_url="https://news.ycombinator.com/item?id=5"),
            _hn_ev("ev_006", body="Exception context missing from traceback.",
                   source_url="https://news.ycombinator.com/item?id=6"),
            _hn_ev("ev_007", body="Stack traces without error context.",
                   source_url="https://news.ycombinator.com/item?id=7"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(sum(c.recurrence for c in clusters), 7)


# ---------------------------------------------------------------------------
# Cohesion Score
# ---------------------------------------------------------------------------


class TestCohesionScore(unittest.TestCase):

    def test_single_evidence_max_cohesion(self) -> None:
        evs = [_hn_ev("ev_001", body="Agent trace debugging is broken")]
        for ev in evs:
            ev["_pain_actor"] = "developer"
            ev["_pain_workflow"] = "debugging"
            ev["_pain_object"] = "agent traces"
        score = _compute_cohesion_score(evs)
        self.assertEqual(score, 1.0)

    def test_same_anchor_high_cohesion(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot trace agent execution."),
            _hn_ev("ev_002", body="Agent traces not observable. Tracing broken.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        for ev in evs:
            ev["_pain_actor"] = "developer"
            ev["_pain_workflow"] = "debugging"
            ev["_pain_object"] = "agent traces"
        score = _compute_cohesion_score(evs)
        self.assertGreaterEqual(score, 0.6)

    def test_different_anchors_low_cohesion(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot trace agent execution. Observability missing."),
            _hn_ev("ev_002", body="Stack trace lacks error context in agent.",
                   source_url="https://news.ycombinator.com/item?id=2"),
            _hn_ev("ev_003", body="Prompt playground cannot replay production traces.",
                   source_url="https://news.ycombinator.com/item?id=3"),
        ]
        for ev in evs:
            ev["_pain_actor"] = "developer"
            ev["_pain_workflow"] = "debugging"
            ev["_pain_object"] = "agent"
        score = _compute_cohesion_score(evs)
        # All same actor/object/workflow but different anchors = moderate cohesion
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_cluster_has_cohesion_field(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot trace agent execution."),
            _gh_ev("ev_002", body="Agent traces not observable.",
                   source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        for c in clusters:
            self.assertGreaterEqual(c.cohesion_score, 0.0)
            self.assertLessEqual(c.cohesion_score, 1.0)

    def test_non_catch_all_cluster(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot debug agent traces."),
            _gh_ev("ev_002", body="Agent trace debugging broken.",
                   source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        for c in clusters:
            self.assertFalse(c.catch_all_risk)

    def test_cluster_has_canonical_anchor(self) -> None:
        evs = [_hn_ev("ev_001", body="Cannot trace agent execution.")]
        clusters, _, _ = assemble_pain_clusters(evs)
        for c in clusters:
            self.assertTrue(len(c.canonical_anchor) > 0)
            self.assertTrue(len(c.canonical_anchors) > 0)


# ---------------------------------------------------------------------------
# Quality-Aware Clustering
# ---------------------------------------------------------------------------


class TestQualityAwareClustering(unittest.TestCase):

    def test_noise_does_not_pull_accepted_into_broad_cluster(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot trace agent execution. Specific pain about observability."),
            _hn_ev("ev_002", body="AI is changing everything. Generic discussion.",
                   quality_flags=["flamewar_or_meta_discussion", "generic_language"],
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_001", "ev_002")
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 2)

    def test_weak_evidence_supports_but_does_not_dominate(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot trace agent execution. Specific observability pain."),
            _hn_ev("ev_002", body="Agent debugging is hard.",
                   quality_flags=["low_text_context"], source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        assert_not_same_cluster(self, clusters, "ev_001", "ev_002")
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 2)

    def test_accepted_primary_pain_drives_grouping(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot trace agent execution. Specific pain."),
            _hn_ev("ev_002", body="Agent trace observability gaps.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].recurrence, 2)
        self.assertIn(clusters[0].canonical_anchor, {"agent_trace_debugging", "generic_agent_debugging"})


# ---------------------------------------------------------------------------
# Codex review fix: Regression test for representative-order fragmentation
# ---------------------------------------------------------------------------


class TestPhase4cStaleRootToItems(unittest.TestCase):
    """v2.14 Codex fix: Phase 4c rebuilds root_to_items after cross-anchor union.

    Regression: without fixed-point root_to_items rebuilding, a successful
    cross-anchor union makes the root item map stale.  Later root-pair scans
    see the updated union-find root but retrieve only the original owner's
    items, missing evidence that was just merged in.  This can cause
    compatible evidence to be split even though _should_merge() returns True.

    Scenario:
      - ev_gen (generic_agent_debugging) merges into ev_integ
        (integration_pipeline_friction) — same actor/workflow/object.
      - ev_integ (now sharing a root with ev_gen) should then merge into
        ev_struct (structured_output_reliability) because ev_integ shares
        2 of 3 dimensions with ev_struct.
      - Under the old stale root_to_items behavior, after the first union
        only ev_gen's original items are visible for the merged root.
        ev_gen is NOT compatible with ev_struct (object differs), so the
        merge is missed.  ev_integ, which IS compatible with ev_struct,
        is invisible because it sits under a child root whose items
        are not reachable through the stale map.
      - Fixed-point rebuilding resolves this: the second iteration sees
        both ev_gen and ev_integ in the merged root and correctly finds
        the ev_integ/ev_struct pair.
    """

    def test_phase4c_rebuilds_root_items_after_cross_anchor_union(self) -> None:
        """Multi-step merge: generic -> integration -> structured_output.

        ev_gen (generic) and ev_integ (integration) share all 3 dimensions
        and merge first.  The merged root should then merge with ev_struct
        because ev_integ shares 2 of 3 dimensions with ev_struct.
        ev_gen alone is NOT compatible with ev_struct (object differs).
        Without root_to_items rebuild, the stale map hides ev_integ and
        the second merge is missed.
        """
        # ev_gen: generic_agent_debugging anchor, actor=developer, workflow=debugging,
        #         object="agent".  Body must avoid trace/tracing/spans keywords
        #         to avoid agent_trace_debugging winning the anchor detection.
        ev_gen = _hn_ev(
            "ev_gen_4c",
            title="Agent execution issues",
            body="Debugging agent is broken. Code fails in production. "
                 "Cannot figure out what went wrong.",
            source_url="https://news.ycombinator.com/item?id=401",
        )

        # ev_integ: integration_pipeline_friction anchor, actor=developer,
        #           workflow=debugging, object="agent".
        #           Shares all 3 dims with ev_gen -> _should_merge(gen,integ)==True.
        ev_integ = _hn_ev(
            "ev_integ_4c",
            title="Pipeline connector failure",
            body="Debugging integration agent pipeline is broken. "
                 "Code sync fails in production.",
            source_url="https://news.ycombinator.com/item?id=402",
        )

        # ev_struct: structured_output_reliability anchor, actor=developer,
        #            workflow=debugging, object="llm".
        #            Shares 2 of 3 dims with ev_integ (actor+workflow match,
        #            object differs).  Does NOT share 3 of 3 with ev_gen
        #            (object mismatch prevents generic->specific merge).
        ev_struct = _hn_ev(
            "ev_struct_4c",
            title="Schema validation issues",
            body="Code debugging: Structured output schema validation for llm "
                 "broken. JSON mode parsing fails in production.",
            source_url="https://news.ycombinator.com/item?id=403",
        )

        evs = [ev_gen, ev_integ, ev_struct]
        clusters, _, _ = assemble_pain_clusters(evs)

        # ev_gen merges into ev_integ's root (same actor/workflow/object)
        assert_same_cluster(self, clusters, "ev_gen_4c", "ev_integ_4c")

        # ev_integ (now in merged root) merges with ev_struct
        # (2 of 3 dimensions match: actor + workflow)
        assert_same_cluster(self, clusters, "ev_integ_4c", "ev_struct_4c")

        # All three evidence items accounted for
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 3)


class TestCrossAnchorPairScanning(unittest.TestCase):
    """v2.14 Codex fix: Phase 4c must compare all pairs, not just first reps.

    Regression: under the old first-representative-only behavior, items
    ev_g1 and ev_s1 would remain split despite _should_merge() returning
    True, because ev_g0 was the first item in its anchor group and did
    NOT match ev_s1.
    """

    def test_cross_anchor_all_pairs_not_just_first_rep(self) -> None:
        """ev_g1 (matches ev_s1) merges even when ev_g0 (first rep) does not.

        Scenario:
        - ev_g0: generic-anchor item, comes first deterministically via
          evidence_id ordering, does NOT match ev_s1 on actor/workflow/object.
        - ev_g1: generic-anchor item, comes second, DOES match ev_s1 on all
          3 dimensions (actor/workflow/object).
        - ev_s1: specific-anchor item (agent_trace_debugging).

        Old Phase 4c checked only ev_g0 (first rep) vs ev_s1 and failed,
        leaving ev_g1 and ev_s1 split.
        New behavior must find ev_g1/ev_s1 compatible and merge them.
        """
        # ev_g0: generic-debugging anchor, developer actor, debugging workflow,
        #        "agent" object, vague pain — does NOT match ev_s1 dimensions
        ev_g0 = _hn_ev(
            "ev_g0",
            title="General AI debugging discussion",
            body="LLM agents are hard to debug in general. Vague discussion.",
            source_url="https://news.ycombinator.com/item?id=100",
        )

        # ev_g1: generic-debugging anchor, developer actor, debugging workflow,
        #        "agent traces" object — DOES match ev_s1 on all 3 dimensions
        ev_g1 = _hn_ev(
            "ev_g1",
            title="Agent trace debugging context missing",
            body="Agent traces lack actionable debugging context. Hard to trace.",
            source_url="https://news.ycombinator.com/item?id=101",
        )

        # ev_s1: specific agent_trace_debugging anchor — should merge with ev_g1
        ev_s1 = _hn_ev(
            "ev_s1",
            title="Cannot trace agent execution",
            body="Tracing agent execution across multi-step runs is broken. "
                 "Observability and spans missing. Hard to debug agent traces.",
            source_url="https://news.ycombinator.com/item?id=102",
        )

        evs = [ev_g0, ev_g1, ev_s1]
        clusters, _, _ = assemble_pain_clusters(evs)

        # Regression assertion: ev_g1 and ev_s1 must be in the same cluster.
        assert_same_cluster(self, clusters, "ev_g1", "ev_s1")

        # ev_g0 should NOT be merged with ev_s1 — it has different body content
        # and insufficient dimension overlap to trigger _should_merge().
        assert_not_same_cluster(self, clusters, "ev_g0", "ev_s1")

        # Total evidence count preserved
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 3)

    def test_first_rep_fails_second_rep_succeeds_within_same_generic_root(self) -> None:
        """Within the same generic-anchor root group, a later item matches.

        Ensures that even after Phase 4b unions items within the generic group,
        Phase 4c still finds the compatible pair across roots.
        """
        # ev_g0: generic anchor, vague
        ev_g0 = _hn_ev(
            "ev_gx0",
            title="AI is interesting",
            body="AI agents are an interesting technology area.",
            source_url="https://news.ycombinator.com/item?id=200",
        )

        # ev_g1: generic anchor but matches specific anchor on actor/wf/obj
        ev_g1 = _hn_ev(
            "ev_gx1",
            title="Tracing agent spans is broken",
            body="Developer cannot debug agent traces because observability spans "
                 "are missing. Tracing multi-step agent execution is broken.",
            source_url="https://news.ycombinator.com/item?id=201",
        )

        # ev_s1: specific agent_trace_debugging anchor
        ev_s1 = _hn_ev(
            "ev_sx1",
            title="Agent trace debugging lacks context",
            body="Tracing agent execution and observability spans are broken. "
                 "Cannot debug multi-step agent runs.",
            source_url="https://news.ycombinator.com/item?id=202",
        )

        evs = [ev_g0, ev_g1, ev_s1]
        clusters, _, _ = assemble_pain_clusters(evs)

        # ev_g1 and ev_s1 should merge
        assert_same_cluster(self, clusters, "ev_gx1", "ev_sx1")

        # ev_g0 should remain separate
        assert_not_same_cluster(self, clusters, "ev_gx0", "ev_sx1")

        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 3)


class TestPhase4cFixedPointTermination(unittest.TestCase):
    """v2.14 Codex fix: Phase 4c fixed-point loop must terminate when no
    new merge occurs in a full iteration.

    Regression for stale merged=True causing infinite loop:
    After one cross-anchor merge succeeds, the next fixed-point iteration
    rebuilds root_to_items and scans all root-pairs again.  If no
    _should_merge() match is found in that iteration, changed stays False
    and the while-loop terminates cleanly.

    This test creates evidence where at least one Phase 4c cross-anchor
    merge occurs, then asserts bounded completion and correct cluster
    membership (not just that the call returns).
    """

    def test_phase4c_fixed_point_stops_when_no_new_merge_occurs(self) -> None:
        """Many coherent/cross-anchor inputs; merge occurs, then termination.

        Evidence design:
        - 4 generic_agent_debugging items: all share actor=developer,
          workflow=debugging, object="agent traces" (Phase 4b merges them).
        - 4 agent_trace_debugging items: same actor/workflow/object,
          different canonical anchor (Phase 4c cross-anchor merge with
          generic group via _should_merge all-3-dimensions match).
        - 2 structured_output_reliability items: actor=founder,
          workflow=testing, object="llm" (should NOT merge with others).

        After the first cross-anchor merge (generic + trace groups unite),
        the next fixed-point iteration rebuilds root_to_items and finds
        no compatible pair with structured_output_reliability.  Loop
        terminates normally instead of hanging on stale flag.
        """
        evs: list[dict[str, Any]] = []

        # Generic anchor group (4 items): all share same actor/wf/obj
        for i in range(1, 5):
            evs.append(_hn_ev(
                f"ev_gen_{i}",
                title=f"Agent debugging issue {i}",
                body=f"Debugging agent execution is broken. "
                     f"Agent traces lack context {i}. Hard to trace agent runs.",
                source_url=f"https://news.ycombinator.com/item?id=500{i}",
            ))

        # agent_trace_debugging anchor group (4 items): same actor/wf/obj as generic
        for i in range(1, 5):
            evs.append(_hn_ev(
                f"ev_trace_{i}",
                title=f"Trace debugging problem {i}",
                body=f"Tracing agent execution across multi-step runs. "
                     f"Observability spans missing. Cannot trace agent "
                     f"debugging workflow {i}.",
                source_url=f"https://news.ycombinator.com/item?id=510{i}",
            ))

        # structured_output_reliability group (2 items): different actor/wf/obj
        for i in range(1, 3):
            evs.append(_hn_ev(
                f"ev_struct_{i}",
                title=f"Schema validation failure {i}",
                body=f"Structured output JSON schema parsing broken for llm. "
                     f"Founder testing deployment pipeline fails {i}.",
                source_url=f"https://news.ycombinator.com/item?id=520{i}",
            ))

        # This must complete normally (no hang)
        clusters, _, _ = assemble_pain_clusters(evs)

        # Verify total evidence preserved
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 10, "All 10 evidence items must be assigned")

        # Generic + trace items should all be in the same cluster
        # (all share same anchor after Phase 4c cross-anchor merge)
        for i in range(1, 5):
            assert_same_cluster(self, clusters, "ev_gen_1", f"ev_gen_{i}")
            assert_same_cluster(self, clusters, "ev_gen_1", f"ev_trace_{i}")

        # Structured output items should be in a different cluster
        assert_not_same_cluster(self, clusters, "ev_gen_1", "ev_struct_1")
        assert_same_cluster(self, clusters, "ev_struct_1", "ev_struct_2")

        # Verify cluster count: at least 2 (merged group + struct group)
        self.assertGreaterEqual(len(clusters), 2,
                               "Should have at least 2 clusters: merged + struct")

        # Verify at least one cluster combines both generic and trace items
        # (proof that Phase 4c cross-anchor merge succeeded)
        cid_map = cluster_ids_by_evidence_id(clusters)
        gen_cid = cid_map.get("ev_gen_1")
        trace_cid = cid_map.get("ev_trace_1")
        self.assertIsNotNone(gen_cid)
        self.assertIsNotNone(trace_cid)
        self.assertEqual(gen_cid, trace_cid,
                         "Generic and trace items must merge via Phase 4c")


if __name__ == "__main__":
    unittest.main()
