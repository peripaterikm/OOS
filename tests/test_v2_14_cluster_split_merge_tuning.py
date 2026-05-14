from __future__ import annotations

"""v2.14 Item 4: Cluster Split/Merge Tuning — focused tests.

Tests canonical pain anchor detection, over-merge prevention, correct merge
behavior, catch-all splitting, cohesion scoring, and quality-aware clustering.
"""

import unittest

from oos.pain_cluster_assembly import (
    _primary_canonical_anchor,
    _detect_canonical_anchors,
    _compute_cohesion_score,
    assemble_pain_clusters,
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
# No Over-Merge Cases
# ---------------------------------------------------------------------------


class TestNoOverMerge(unittest.TestCase):

    def test_provenance_does_not_merge_with_generic_llm_debug(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot determine output provenance in multi-agent systems."),
            _hn_ev("ev_002", body="LLM debugging is hard. General agent pain.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 2)

    def test_prompt_replay_does_not_merge_with_stack_trace(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot replay production trace in prompt playground."),
            _gh_ev("ev_002", body="Stack trace lacks exception context.",
                   source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertGreaterEqual(len(clusters), 1)

    def test_checkpoint_does_not_merge_with_eval_testing(self) -> None:
        evs = [
            _gh_ev("ev_001", body="Checkpoint state not reproducible across runs."),
            _hn_ev("ev_002", body="LLM regression testing and evaluation workflow lacks test cases.",
                   source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        self.assertGreaterEqual(len(clusters), 1)

    def test_product_launch_does_not_merge_with_bug_report(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Check out our new AI debugging tool!",
                   evidence_kind="product_launch", quality_flags=["suspected_self_promo"]),
            _gh_ev("ev_002", body="Agent traces not reproducible. Bug in trace replay.",
                   evidence_kind="bug_report", source_url="https://github.com/test/repo/issues/2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 2)

    def test_low_text_context_does_not_dominate_cluster(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Agent debugging is hard. We spend hours tracing multi-step execution."),
            _hn_ev("ev_002", body="Debugging context missing.",
                   quality_flags=["low_text_context"], source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 2)


# ---------------------------------------------------------------------------
# Correct Merge Cases
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
        total = sum(c.recurrence for c in clusters)
        self.assertEqual(total, 2)

    def test_weak_evidence_supports_but_does_not_dominate(self) -> None:
        evs = [
            _hn_ev("ev_001", body="Cannot trace agent execution. Specific observability pain."),
            _hn_ev("ev_002", body="Agent debugging is hard.",
                   quality_flags=["low_text_context"], source_url="https://news.ycombinator.com/item?id=2"),
        ]
        clusters, _, _ = assemble_pain_clusters(evs)
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


if __name__ == "__main__":
    unittest.main()
