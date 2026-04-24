import re
import unittest
from pathlib import Path

from oos.semantic_clustering import (
    LOW_CONFIDENCE_CLUSTERING_THRESHOLD,
    StaticSemanticClusteringProvider,
    cluster_canonical_signals,
)
from tests.test_semantic_clustering import make_signal, valid_cluster


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestSemanticClusteringAcceptance(unittest.TestCase):
    def test_semantic_clustering_module_has_no_live_llm_or_api_calls(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "semantic_clustering.py").read_text(encoding="utf-8")
        forbidden_tokens = [
            "OpenAI(",
            "Anthropic(",
            "requests.post",
            "httpx.post",
            "chat.completions",
            "responses.create",
        ]

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_semantic_clustering_is_not_wired_into_run_signal_batch(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "orchestrator.py").read_text(encoding="utf-8")
        forbidden_tokens = [
            "semantic_clustering",
            "cluster_signals",
            "SemanticCluster",
        ]

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_canonical_signals_prevent_duplicate_recurrence_inflation(self) -> None:
        signals = [
            make_signal("sig_1"),
            make_signal("sig_dup", duplicate=True, canonical_id="sig_1"),
            make_signal("sig_2", pain="manual invoice reconciliation"),
        ]
        provider = StaticSemanticClusteringProvider(payload=[valid_cluster(signal_ids=["sig_1", "sig_2"])])

        result = cluster_canonical_signals(signals=signals, provider=provider)

        self.assertEqual(result.processed_canonical_signal_ids, ["sig_1", "sig_2"])
        self.assertEqual(result.skipped_duplicate_signal_ids, ["sig_dup"])
        self.assertEqual(result.clusters[0].linked_canonical_signal_ids, ["sig_1", "sig_2"])
        self.assertNotIn("sig_dup", result.clusters[0].linked_signal_ids)
        self.assertNotIn("sig_dup", result.clusters[0].linked_canonical_signal_ids)

    def test_low_confidence_clusters_trigger_low_confidence_fallback(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticSemanticClusteringProvider(
            payload=[valid_cluster(signal_ids=["sig_1", "sig_2"], confidence=0.39)]
        )

        result = cluster_canonical_signals(signals=signals, provider=provider)

        self.assertEqual(LOW_CONFIDENCE_CLUSTERING_THRESHOLD, 0.4)
        self.assertTrue(result.low_confidence_clustering)
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.stage_status, "degraded")
        self.assertEqual([cluster.linked_canonical_signal_ids for cluster in result.clusters], [["sig_1"], ["sig_2"]])

    def test_invalid_linked_signal_ids_are_not_silently_accepted(self) -> None:
        signals = [make_signal("sig_1")]
        provider = StaticSemanticClusteringProvider(payload=[valid_cluster(signal_ids=["sig_missing"])])

        result = cluster_canonical_signals(signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.stage_status, "degraded")
        self.assertIn("linked_signal_ids contain unknown IDs", result.failure_reason)
        self.assertEqual(result.clusters[0].linked_signal_ids, ["sig_1"])

    def test_invalid_linked_canonical_signal_ids_are_not_silently_accepted(self) -> None:
        signals = [make_signal("sig_1")]
        bad_cluster = valid_cluster(signal_ids=["sig_1"])
        bad_cluster["linked_canonical_signal_ids"] = ["sig_missing"]
        provider = StaticSemanticClusteringProvider(payload=[bad_cluster])

        result = cluster_canonical_signals(signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.stage_status, "degraded")
        self.assertIn("linked_canonical_signal_ids contain unknown IDs", result.failure_reason)
        self.assertEqual(result.clusters[0].linked_canonical_signal_ids, ["sig_1"])

    def test_active_roadmap_is_advanced_to_3_2(self) -> None:
        source = (REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_2_8_weeks_checklist.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("**0.2.2** Current item: **3.2**", source)
        self.assertIn("**0.2.4** Completed from this roadmap: **5 / 16**", source)
        self.assertIn("**0.2.5** Remaining: **11 / 16**", source)
        self.assertRegex(
            source,
            re.compile(
                r"## 3\.1\. LLM semantic clustering of canonical signals\s+"
                r"\*\*Status:\*\* \[ \] Not started  \[ \] In progress  \[ \] Blocked  \[x\] Done",
                re.MULTILINE,
            ),
        )


if __name__ == "__main__":
    unittest.main()
