import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.ai_contracts import AI_METADATA_REQUIRED_FIELDS
from oos.opportunity_framing import (
    EVIDENCE_MISSING_STATUS,
    OpportunityFramingProvider,
    StaticOpportunityFramingProvider,
    frame_opportunities,
    write_opportunity_framing_artifacts,
)
from oos.semantic_clustering import StaticSemanticClusteringProvider, cluster_canonical_signals
from tests.test_semantic_clustering import make_signal, valid_cluster


def make_cluster():
    result = cluster_canonical_signals(
        signals=[make_signal("sig_1"), make_signal("sig_2")],
        provider=StaticSemanticClusteringProvider(payload=[valid_cluster(signal_ids=["sig_1", "sig_2"])]),
    )
    return result.clusters[0]


def valid_opportunity(**overrides: object) -> dict:
    payload = {
        "opportunity_id": "opp_reporting_trust",
        "title": "Weekly reconciliation narratives for owner trust",
        "target_user": "SMB owner-operators",
        "pain": "Owners do not trust financial reports when spreadsheets and bank balances diverge.",
        "current_workaround": "Manual spreadsheet reconciliation before weekly reporting.",
        "why_it_matters": "Trust gaps delay decisions and create repeated manual review work.",
        "evidence": [
            {
                "evidence_id": "ev_reporting_trust",
                "claim": "Two canonical signals mention manual reconciliation around reporting trust.",
                "source_signal_ids": ["sig_1", "sig_2"],
                "source_cluster_id": "cluster_ops",
            }
        ],
        "urgency": "Weekly reporting cadence creates repeated urgency.",
        "possible_wedge": "Start with reconciliation narratives instead of another dashboard.",
        "monetization_hypothesis": "Charge a monthly fee for owner-ready reconciliation summaries.",
        "risks": ["Buyer may see this as bookkeeping services."],
        "assumptions": [
            {
                "assumption_id": "asm_budget",
                "statement": "Owners will pay for trust restoration rather than faster report generation alone.",
                "reason": "Budget intent is not directly present in the source signals.",
            }
        ],
        "non_obvious_angle": (
            "The wedge may not be reporting itself, but restoring owner trust through weekly reconciliation narratives."
        ),
        "linked_cluster_id": "cluster_ops",
        "linked_signal_ids": ["sig_1", "sig_2"],
        "linked_canonical_signal_ids": ["sig_1", "sig_2"],
        "confidence": 0.82,
    }
    payload.update(overrides)
    return payload


class RecordingProvider(OpportunityFramingProvider):
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = 0
        self.seen_cluster_ids: list[list[str]] = []
        self.seen_signal_ids: list[list[str]] = []

    def frame(self, *, clusters, signals, understanding_records=None, contradiction_report=None):
        self.calls += 1
        self.seen_cluster_ids.append([cluster.cluster_id for cluster in clusters])
        self.seen_signal_ids.append([signal.id for signal in signals])
        return self.payload


class TestOpportunityFraming(unittest.TestCase):
    def test_valid_provider_response_creates_structured_opportunity_cards(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        cluster = make_cluster()
        provider = StaticOpportunityFramingProvider(payload={"opportunities": [valid_opportunity()]})

        result = frame_opportunities(clusters=[cluster], signals=signals, provider=provider)

        self.assertFalse(result.fallback_used)
        self.assertEqual(result.stage_status, "success")
        self.assertEqual(result.opportunities[0].opportunity_id, "opp_reporting_trust")
        self.assertEqual(result.opportunities[0].status, "candidate")
        self.assertFalse(result.opportunities[0].evidence_missing)

    def test_every_opportunity_links_to_real_cluster_id(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticOpportunityFramingProvider(
            payload={"opportunities": [valid_opportunity(linked_cluster_id="cluster_missing")]}
        )

        result = frame_opportunities(clusters=[make_cluster()], signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.opportunities, [])
        self.assertIn("linked_cluster_id contains unknown ID", result.failure_reason)

    def test_every_linked_signal_id_exists(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticOpportunityFramingProvider(
            payload={"opportunities": [valid_opportunity(linked_signal_ids=["sig_1", "sig_missing"])]}
        )

        result = frame_opportunities(clusters=[make_cluster()], signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.opportunities, [])
        self.assertIn("linked_signal_ids contain unknown IDs", result.failure_reason)

    def test_every_linked_canonical_signal_id_exists_when_provided(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticOpportunityFramingProvider(
            payload={"opportunities": [valid_opportunity(linked_canonical_signal_ids=["sig_1", "sig_missing"])]}
        )

        result = frame_opportunities(clusters=[make_cluster()], signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.opportunities, [])
        self.assertIn("linked_canonical_signal_ids contain unknown IDs", result.failure_reason)

    def test_evidence_cannot_reference_unknown_source_ids(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        opportunity = valid_opportunity()
        opportunity["evidence"] = [
            {
                "evidence_id": "ev_bad",
                "claim": "Unsupported source reference.",
                "source_signal_ids": ["sig_missing"],
                "source_cluster_id": "cluster_ops",
            }
        ]
        provider = StaticOpportunityFramingProvider(payload={"opportunities": [opportunity]})

        result = frame_opportunities(clusters=[make_cluster()], signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.opportunities, [])
        self.assertIn("evidence source_signal_ids contain unknown IDs", result.failure_reason)

    def test_opportunity_without_evidence_is_marked_evidence_missing_and_parked(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticOpportunityFramingProvider(payload={"opportunities": [valid_opportunity(evidence=[])]})

        result = frame_opportunities(clusters=[make_cluster()], signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.stage_status, "degraded")
        self.assertEqual(len(result.opportunities), 1)
        self.assertTrue(result.opportunities[0].evidence_missing)
        self.assertEqual(result.opportunities[0].status, EVIDENCE_MISSING_STATUS)

    def test_unsupported_claims_can_be_captured_as_assumptions(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticOpportunityFramingProvider(payload={"opportunities": [valid_opportunity()]})

        result = frame_opportunities(clusters=[make_cluster()], signals=signals, provider=provider)

        assumption = result.opportunities[0].assumptions[0]
        self.assertIn("not directly present", assumption.reason)
        self.assertIn("will pay", assumption.statement)

    def test_non_obvious_angle_is_required(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticOpportunityFramingProvider(payload={"opportunities": [valid_opportunity(non_obvious_angle="")]})

        result = frame_opportunities(clusters=[make_cluster()], signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.opportunities, [])
        self.assertIn("non_obvious_angle must be a non-empty string", result.failure_reason)

    def test_confidence_validation_works(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticOpportunityFramingProvider(payload={"opportunities": [valid_opportunity(confidence=1.4)]})

        result = frame_opportunities(clusters=[make_cluster()], signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.opportunities, [])
        self.assertIn("confidence must be a number between 0 and 1", result.failure_reason)

    def test_ai_metadata_is_present(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        result = frame_opportunities(
            clusters=[make_cluster()],
            signals=signals,
            provider=StaticOpportunityFramingProvider(payload={"opportunities": [valid_opportunity()]}),
        )

        for field in AI_METADATA_REQUIRED_FIELDS:
            self.assertIn(field, result.ai_metadata)
            self.assertIn(field, result.opportunities[0].ai_metadata)
        self.assertEqual(result.ai_metadata["prompt_name"], "opportunity_framing")
        self.assertEqual(result.opportunities[0].ai_metadata["prompt_version"], "opportunity_framing_v1")

    def test_no_live_llm_call_is_made(self) -> None:
        provider = RecordingProvider(payload={"opportunities": [valid_opportunity()]})

        result = frame_opportunities(
            clusters=[make_cluster()],
            signals=[make_signal("sig_1"), make_signal("sig_2")],
            provider=provider,
        )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(provider.seen_cluster_ids, [["cluster_ops"]])
        self.assertEqual(provider.seen_signal_ids, [["sig_1", "sig_2"]])
        self.assertFalse(result.fallback_used)

    def test_valid_records_survive_when_one_provider_record_is_bad(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticOpportunityFramingProvider(
            payload={"opportunities": [valid_opportunity(), valid_opportunity(opportunity_id="bad", confidence=-0.1)]}
        )

        result = frame_opportunities(clusters=[make_cluster()], signals=signals, provider=provider)

        self.assertTrue(result.fallback_used)
        self.assertEqual([opportunity.opportunity_id for opportunity in result.opportunities], ["opp_reporting_trust"])
        self.assertEqual(len(result.rejected_record_errors), 1)

    def test_opportunity_framing_artifacts_can_be_written(self) -> None:
        result = frame_opportunities(
            clusters=[make_cluster()],
            signals=[make_signal("sig_1"), make_signal("sig_2")],
            provider=StaticOpportunityFramingProvider(payload={"opportunities": [valid_opportunity()]}),
        )

        with TemporaryDirectory() as tmp:
            index_path = write_opportunity_framing_artifacts(result, Path(tmp))
            payload = json.loads(index_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["opportunities"][0]["opportunity_id"], "opp_reporting_trust")


if __name__ == "__main__":
    unittest.main()
