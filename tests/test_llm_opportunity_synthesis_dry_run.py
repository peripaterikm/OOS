import json
import unittest
from pathlib import Path
from unittest.mock import patch

from oos.evidence_pack import (
    INSUFFICIENT_EVIDENCE_CREATED_FROM,
    EvidencePack,
    EvidencePackItem,
    EvidencePackRiskNote,
    EvidencePackSourceSummary,
    make_evidence_pack_id,
)
from oos.llm_contracts import DeterministicMockLLMProvider
from oos.llm_opportunity_synthesis_contract import (
    ensure_evidence_bound_response,
    validate_opportunity_synthesis_response_schema,
)
from oos.llm_opportunity_synthesis_dry_run import (
    OPPORTUNITY_SYNTHESIS_DRY_RUN_SCHEMA_VERSION,
    OpportunitySynthesisDryRunResult,
    build_mock_opportunity_synthesis_response,
    run_offline_opportunity_synthesis_dry_run,
    validate_offline_opportunity_synthesis_result,
)
from oos.opportunity_sketch import build_opportunity_sketch_from_evidence_pack


class LLMOpportunitySynthesisDryRunTests(unittest.TestCase):
    def test_dry_run_builds_request_from_evidence_pack(self):
        result = run_offline_opportunity_synthesis_dry_run(_cash_collection_pack(), dry_run_id="dry_cash")

        self.assertEqual(result.request_role, "opportunity_synthesis")
        self.assertEqual(result.schema_version, OPPORTUNITY_SYNTHESIS_DRY_RUN_SCHEMA_VERSION)
        self.assertTrue(result.prompt_hash)
        self.assertIn("evidence packs", result.prompt_preview)

    def test_dry_run_builds_deterministic_baseline(self):
        pack = _cash_collection_pack()
        baseline = build_opportunity_sketch_from_evidence_pack(pack)
        result = run_offline_opportunity_synthesis_dry_run(pack)

        self.assertEqual(result.baseline_opportunity_id, baseline.opportunity_id)
        self.assertIn("cash-collection", result.mock_response["problem_statement"])

    def test_mock_response_validates_against_contract_schema(self):
        pack = _cash_collection_pack()
        synthesis_input = _synthesis_input_for_pack(pack)
        response = build_mock_opportunity_synthesis_response(synthesis_input)

        validate_opportunity_synthesis_response_schema(response)
        ensure_evidence_bound_response(response, synthesis_input)

    def test_response_evidence_ids_are_subset_of_pack(self):
        pack = _cash_collection_pack()
        result = run_offline_opportunity_synthesis_dry_run(pack)

        self.assertTrue(set(result.mock_response["evidence_ids"]) <= set(pack.evidence_ids))
        self.assertEqual(result.cited_evidence_ids, ["evidence_invoice_a", "evidence_invoice_b"])

    def test_source_signal_ids_and_urls_are_preserved(self):
        pack = _cash_collection_pack()
        result = run_offline_opportunity_synthesis_dry_run(pack)

        self.assertEqual(result.mock_response["source_signal_ids"], ["signal_invoice_a", "signal_invoice_b"])
        self.assertEqual(
            result.mock_response["source_urls"],
            ["https://example.com/evidence_invoice_a", "https://example.com/evidence_invoice_b"],
        )

    def test_advisory_only_and_no_live_provider_flags_are_true(self):
        result = run_offline_opportunity_synthesis_dry_run(_cash_collection_pack())

        self.assertTrue(result.mock_response["advisory_only"])
        self.assertTrue(result.no_live_provider_call)
        self.assertFalse(result.external_calls_made)
        self.assertEqual(result.provider_used, "deterministic_mock_contract_only")

    def test_provider_complete_is_not_called(self):
        with patch.object(DeterministicMockLLMProvider, "complete", side_effect=AssertionError("provider called")):
            result = run_offline_opportunity_synthesis_dry_run(_cash_collection_pack())

        self.assertTrue(result.no_live_provider_call)
        self.assertTrue(result.mock_response_valid)

    def test_strong_cash_collection_fixture_produces_valid_result(self):
        result = run_offline_opportunity_synthesis_dry_run(_cash_collection_pack())

        self.assertIsInstance(result, OpportunitySynthesisDryRunResult)
        self.assertTrue(result.mock_response_valid)
        self.assertTrue(result.evidence_bound_check_passed)
        self.assertGreaterEqual(result.confidence, 0.5)

    def test_weak_vendor_fixture_produces_low_confidence(self):
        result = run_offline_opportunity_synthesis_dry_run(_vendor_pack())

        self.assertTrue(result.mock_response_valid)
        self.assertLessEqual(result.confidence, 0.45)
        self.assertIn("buyer", result.unsupported_assumptions)
        self.assertTrue(any("vendor-like" in note for note in result.risk_notes))

    def test_insufficient_evidence_marks_unsupported_assumptions(self):
        result = run_offline_opportunity_synthesis_dry_run(_insufficient_pack())

        self.assertTrue(result.mock_response_valid)
        self.assertLessEqual(result.confidence, 0.25)
        self.assertIn("insufficient_evidence", result.unsupported_assumptions)
        self.assertEqual(result.mock_response["why_now"], "unknown")

    def test_output_is_deterministic_across_repeated_runs(self):
        pack = _cash_collection_pack()
        first = run_offline_opportunity_synthesis_dry_run(pack, dry_run_id="stable").to_dict()
        second = run_offline_opportunity_synthesis_dry_run(pack, dry_run_id="stable").to_dict()

        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_result_validation_rejects_live_provider_flags(self):
        result = run_offline_opportunity_synthesis_dry_run(_cash_collection_pack())
        invalid = OpportunitySynthesisDryRunResult(**{**result.to_dict(), "no_live_provider_call": False})

        with self.assertRaisesRegex(ValueError, "no_live_provider_call"):
            validate_offline_opportunity_synthesis_result(invalid)

    def test_no_live_network_or_llm_api_calls_are_made(self):
        source = Path("src/oos/llm_opportunity_synthesis_dry_run.py").read_text(encoding="utf-8")

        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("complete(", source)


def _synthesis_input_for_pack(pack):
    from oos.llm_opportunity_synthesis_contract import LLMOpportunitySynthesisInput

    return LLMOpportunitySynthesisInput(
        synthesis_id="fixture_synthesis",
        evidence_pack=pack,
        baseline_candidate=build_opportunity_sketch_from_evidence_pack(pack),
    )


def _cash_collection_pack():
    return _pack(
        cluster_id="cash_collection",
        summaries=[
            "Small business operator has unpaid invoice follow-up email pain.",
            "Small business owner tracks cash collection with manual spreadsheet follow-up.",
        ],
        evidence_ids=["evidence_invoice_a", "evidence_invoice_b"],
        signal_ids=["signal_invoice_a", "signal_invoice_b"],
        source_urls=["https://example.com/evidence_invoice_a", "https://example.com/evidence_invoice_b"],
        confidence_values=[0.7, 0.74],
    )


def _vendor_pack():
    return _pack(
        cluster_id="vendor_generic",
        summaries=[
            "Transform your business with generic accounting software and professional support.",
            "Affordable pricing and consultation for bookkeeping services.",
        ],
        risk_notes=[
            EvidencePackRiskNote(
                "source_quality_issue",
                "Vendor-promo-like generic evidence requires review.",
                evidence_id="evidence_vendor_a",
                severity="high",
            )
        ],
        evidence_ids=["evidence_vendor_a", "evidence_vendor_b"],
        signal_ids=["signal_vendor_a", "signal_vendor_b"],
        source_urls=["https://example.com/vendor-a", "https://example.com/vendor-b"],
        confidence_values=[0.34, 0.38],
    )


def _insufficient_pack():
    return _pack(
        cluster_id="single_weak",
        summaries=["A generic accounting note lacks buyer or workaround evidence."],
        evidence_ids=["evidence_single"],
        signal_ids=["signal_single"],
        source_urls=["https://example.com/evidence_single"],
        risk_notes=[
            EvidencePackRiskNote(
                "insufficient_evidence_count",
                "Evidence pack has fewer than 2 distinct evidence items.",
                severity="high",
            )
        ],
        created_from=INSUFFICIENT_EVIDENCE_CREATED_FROM,
        confidence_values=[0.7],
    )


def _pack(
    *,
    cluster_id,
    summaries,
    evidence_ids,
    signal_ids,
    source_urls,
    risk_notes=None,
    created_from="fixture_evidence_pack",
    confidence_values=None,
):
    source_types = ["hn", "github_issue"][: len(evidence_ids)]
    items = [
        EvidencePackItem(
            evidence_id=evidence_id,
            source_signal_id=signal_ids[index],
            source_url=source_urls[index],
            source_type=source_types[index % len(source_types)],
            summary=summaries[index % len(summaries)],
            confidence=(confidence_values or [0.62, 0.66])[index % len(confidence_values or [0.62, 0.66])],
        )
        for index, evidence_id in enumerate(evidence_ids)
    ]
    return EvidencePack(
        evidence_pack_id=make_evidence_pack_id(cluster_id),
        cluster_id=cluster_id,
        source_signal_ids=signal_ids,
        evidence_ids=evidence_ids,
        source_urls=source_urls,
        summaries=summaries,
        source_types=source_types,
        topic_id="ai_cfo_smb",
        confidence_values=confidence_values or [0.62, 0.66],
        source_diversity=len(set(source_types)),
        recurrence_count=len(set(evidence_ids)),
        created_from=created_from,
        risk_notes=risk_notes or [],
        items=items,
        source_summaries=[
            EvidencePackSourceSummary(
                source_type=source_type,
                source_count=1,
                evidence_ids=[evidence_ids[index]],
            )
            for index, source_type in enumerate(source_types)
        ],
    )


if __name__ == "__main__":
    unittest.main()
