import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.ai_contracts import AI_METADATA_REQUIRED_FIELDS, compute_input_hash
from oos.models import Signal, SignalStatus
from oos.semantic_clustering import (
    LOW_CONFIDENCE_CLUSTERING_THRESHOLD,
    SemanticClusteringProvider,
    StaticSemanticClusteringProvider,
    cluster_canonical_signals,
    write_semantic_cluster_artifacts,
)


def make_signal(signal_id: str, pain: str = "manual export reconciliation", *, duplicate: bool = False, canonical_id: str = "") -> Signal:
    canonical_signal_id = canonical_id or signal_id
    return Signal(
        id=signal_id,
        source="customer_interview",
        timestamp="2026-04-24T00:00:00+00:00",
        raw_content=f"Ops lead has recurring pain around {pain} and uses a spreadsheet workaround.",
        extracted_pain=pain,
        candidate_icp="ops lead",
        validity_specificity=1,
        validity_recurrence=1,
        validity_workaround=1,
        validity_cost_signal=1,
        validity_icp_match=1,
        validity_score=5,
        status=SignalStatus.validated,
        metadata={
            "duplicate_group_id": f"dupgrp_{canonical_signal_id}",
            "is_duplicate": duplicate,
            "canonical_signal_id": canonical_signal_id,
        },
    )


def valid_cluster(*, cluster_id: str = "cluster_ops", signal_ids: list[str] | None = None, confidence: float = 0.82) -> dict:
    ids = signal_ids or ["sig_1", "sig_2"]
    return {
        "cluster_id": cluster_id,
        "title": "Manual operations exception handling",
        "summary": "Ops users repeatedly handle failed workflow exceptions with spreadsheets.",
        "linked_signal_ids": ids,
        "linked_canonical_signal_ids": ids,
        "reasoning": "Signals share the same operator, manual workaround, and recurring exception context.",
        "confidence": confidence,
        "uncertainty": "Buyer budget still unknown.",
    }


class RecordingProvider(SemanticClusteringProvider):
    def __init__(self, payload: list[dict]):
        self.payload = payload
        self.calls = 0
        self.seen_batch_sizes: list[int] = []

    def cluster(self, signals: list[Signal]) -> list[dict]:
        self.calls += 1
        self.seen_batch_sizes.append(len(signals))
        return self.payload


class TestSemanticClustering(unittest.TestCase):
    def test_valid_provider_response_creates_structured_clusters(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticSemanticClusteringProvider(payload=[valid_cluster()])

        result = cluster_canonical_signals(signals=signals, provider=provider)

        self.assertFalse(result.fallback_used)
        self.assertEqual(result.stage_status, "success")
        self.assertEqual(len(result.clusters), 1)
        self.assertEqual(result.clusters[0].cluster_id, "cluster_ops")
        self.assertEqual(result.clusters[0].linked_canonical_signal_ids, ["sig_1", "sig_2"])

    def test_every_cluster_links_to_real_and_canonical_signal_ids(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        result = cluster_canonical_signals(signals=signals, provider=StaticSemanticClusteringProvider(payload=[valid_cluster()]))
        cluster = result.clusters[0]

        self.assertEqual(cluster.linked_signal_ids, ["sig_1", "sig_2"])
        self.assertEqual(cluster.linked_canonical_signal_ids, ["sig_1", "sig_2"])

    def test_empty_cluster_output_falls_back(self) -> None:
        signals = [make_signal("sig_1")]

        result = cluster_canonical_signals(signals=signals, provider=StaticSemanticClusteringProvider(payload=[]))

        self.assertTrue(result.fallback_used)
        self.assertTrue(result.low_confidence_clustering)
        self.assertEqual(result.clusters[0].linked_canonical_signal_ids, ["sig_1"])
        self.assertTrue(result.clusters[0].fallback_used)

    def test_missing_signal_references_fall_back(self) -> None:
        signals = [make_signal("sig_1")]
        bad_cluster = valid_cluster(signal_ids=["sig_missing"])

        result = cluster_canonical_signals(signals=signals, provider=StaticSemanticClusteringProvider(payload=[bad_cluster]))

        self.assertTrue(result.fallback_used)
        self.assertIn("unknown IDs", result.failure_reason)
        self.assertEqual(result.clusters[0].linked_signal_ids, ["sig_1"])

    def test_confidence_validation_falls_back(self) -> None:
        signals = [make_signal("sig_1")]
        bad_cluster = valid_cluster(signal_ids=["sig_1"], confidence=1.5)

        result = cluster_canonical_signals(signals=signals, provider=StaticSemanticClusteringProvider(payload=[bad_cluster]))

        self.assertTrue(result.fallback_used)
        self.assertIn("confidence", result.failure_reason)

    def test_all_clusters_below_threshold_trigger_low_confidence_fallback(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        low_cluster = valid_cluster(signal_ids=["sig_1", "sig_2"], confidence=0.39)

        result = cluster_canonical_signals(signals=signals, provider=StaticSemanticClusteringProvider(payload=[low_cluster]))

        self.assertEqual(LOW_CONFIDENCE_CLUSTERING_THRESHOLD, 0.4)
        self.assertTrue(result.low_confidence_clustering)
        self.assertTrue(result.fallback_used)
        self.assertEqual([cluster.linked_canonical_signal_ids for cluster in result.clusters], [["sig_1"], ["sig_2"]])

    def test_duplicate_signals_do_not_inflate_cluster_recurrence(self) -> None:
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
        self.assertNotIn("sig_dup", result.clusters[0].linked_canonical_signal_ids)

    def test_ai_metadata_is_present(self) -> None:
        signals = [make_signal("sig_1")]
        result = cluster_canonical_signals(
            signals=signals,
            provider=StaticSemanticClusteringProvider(payload=[valid_cluster(signal_ids=["sig_1"])]),
        )
        metadata = result.clusters[0].ai_metadata

        for field in AI_METADATA_REQUIRED_FIELDS:
            self.assertIn(field, metadata)
        self.assertEqual(metadata["prompt_version"], "semantic_clustering_v1")
        self.assertEqual(metadata["linked_input_ids"], ["sig_1"])

    def test_input_hash_uses_ai_contracts_helper(self) -> None:
        signal = make_signal("sig_1")
        result = cluster_canonical_signals(
            signals=[signal],
            provider=StaticSemanticClusteringProvider(payload=[valid_cluster(signal_ids=["sig_1"])]),
        )
        expected_hash = compute_input_hash(
            [
                {
                    "id": signal.id,
                    "source": signal.source,
                    "timestamp": signal.timestamp,
                    "raw_content": signal.raw_content,
                    "extracted_pain": signal.extracted_pain,
                    "candidate_icp": signal.candidate_icp,
                    "metadata": signal.metadata,
                }
            ]
        )

        self.assertEqual(result.clusters[0].ai_metadata["input_hash"], expected_hash)

    def test_no_live_llm_call_is_made(self) -> None:
        provider = RecordingProvider(payload=[valid_cluster(signal_ids=["sig_1"])])

        result = cluster_canonical_signals(signals=[make_signal("sig_1")], provider=provider)

        self.assertEqual(provider.calls, 1)
        self.assertEqual(provider.seen_batch_sizes, [1])
        self.assertFalse(result.fallback_used)

    def test_semantic_cluster_artifacts_can_be_written(self) -> None:
        result = cluster_canonical_signals(
            signals=[make_signal("sig_1")],
            provider=StaticSemanticClusteringProvider(payload=[valid_cluster(signal_ids=["sig_1"])]),
        )
        with TemporaryDirectory() as tmp:
            index_path = write_semantic_cluster_artifacts(result, Path(tmp))
            cluster_path = Path(tmp) / "semantic_clusters" / "cluster_ops.json"

            self.assertTrue(index_path.exists())
            self.assertTrue(cluster_path.exists())
            payload = json.loads(cluster_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["cluster_id"], "cluster_ops")


if __name__ == "__main__":
    unittest.main()
