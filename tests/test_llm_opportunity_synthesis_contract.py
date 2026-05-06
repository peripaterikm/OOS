import json
import unittest
from pathlib import Path

from oos.evidence_pack import EvidencePack, EvidencePackItem, EvidencePackRiskNote, EvidencePackSourceSummary, make_evidence_pack_id
from oos.llm_contracts import LLMBudgetState, check_llm_budget, default_local_preview_llm_budget_policy
from oos.llm_opportunity_synthesis_contract import (
    LLM_OPPORTUNITY_SYNTHESIS_TASK_TYPE,
    LLMOpportunitySynthesisInput,
    build_opportunity_synthesis_messages,
    build_opportunity_synthesis_prompt,
    build_opportunity_synthesis_request,
    ensure_evidence_bound_response,
    parse_opportunity_synthesis_response,
    validate_opportunity_synthesis_response_schema,
)
from oos.opportunity_sketch import build_opportunity_sketch_from_evidence_pack


class LLMOpportunitySynthesisContractTests(unittest.TestCase):
    def test_prompt_includes_evidence_pack_context(self):
        prompt = build_opportunity_synthesis_prompt(_synthesis_input())

        self.assertIn('"evidence_pack_context"', prompt)
        self.assertIn("evidence_invoice_a", prompt)
        self.assertIn("https://example.com/evidence_invoice_a", prompt)
        self.assertIn("source_signal_ids", prompt)

    def test_prompt_includes_deterministic_baseline_context(self):
        synthesis_input = _synthesis_input()
        prompt = build_opportunity_synthesis_prompt(synthesis_input)

        self.assertIn('"deterministic_baseline_candidate"', prompt)
        self.assertIn(synthesis_input.baseline_candidate.opportunity_id, prompt)
        self.assertIn("cash-collection", prompt)

    def test_prompt_requires_evidence_ids_and_unsupported_assumptions(self):
        prompt_text = "\n".join(message.content for message in build_opportunity_synthesis_messages(_synthesis_input()))

        self.assertIn("Cite evidence IDs for every substantive claim", prompt_text)
        self.assertIn("Mark unsupported assumptions explicitly", prompt_text)
        self.assertIn("unsupported_assumptions", prompt_text)
        self.assertIn("cited_evidence", prompt_text)

    def test_prompt_prohibits_invented_buyer_price_market_product_strategy(self):
        prompt_text = "\n".join(message.content for message in build_opportunity_synthesis_messages(_synthesis_input())).lower()

        self.assertIn("do not invent buyer, price, market size, product, strategy, or urgency", prompt_text)
        self.assertIn("not a decision-maker", prompt_text)
        self.assertIn("not a market-size estimator", prompt_text)
        self.assertIn("advisory only", prompt_text)

    def test_weak_generic_vendor_risk_notes_force_low_confidence_guidance(self):
        prompt_text = "\n".join(message.content for message in build_opportunity_synthesis_messages(_risky_synthesis_input())).lower()

        self.assertIn("vendor-promo-like", prompt_text)
        self.assertIn("insufficient", prompt_text)
        self.assertIn("return low confidence", prompt_text)
        self.assertIn("source_quality_issue", prompt_text)

    def test_schema_validation_accepts_valid_response(self):
        response = _valid_response()

        validate_opportunity_synthesis_response_schema(response)
        ensure_evidence_bound_response(response, _synthesis_input())

    def test_parse_response_round_trips_valid_json(self):
        parsed = parse_opportunity_synthesis_response(json.dumps(_valid_response(), sort_keys=True))

        self.assertEqual(parsed["advisory_only"], True)
        self.assertEqual(parsed["evidence_ids"], ["evidence_invoice_a", "evidence_invoice_b"])

    def test_schema_validation_rejects_missing_evidence_ids(self):
        response = _valid_response()
        response.pop("evidence_ids")

        with self.assertRaisesRegex(ValueError, "Missing required"):
            validate_opportunity_synthesis_response_schema(response)

    def test_schema_validation_rejects_missing_cited_evidence_for_claim(self):
        response = _valid_response()
        response["cited_evidence"] = [response["cited_evidence"][0]]

        with self.assertRaisesRegex(ValueError, "missing cited_evidence"):
            validate_opportunity_synthesis_response_schema(response)

    def test_evidence_bound_response_rejects_unsupported_evidence_id(self):
        response = _valid_response()
        response["evidence_ids"] = ["evidence_invoice_a", "evidence_unknown"]
        response["cited_evidence"].append(
            {"evidence_id": "evidence_unknown", "claim": "unsupported", "citation": "not in pack"}
        )

        with self.assertRaisesRegex(ValueError, "drawn from the supplied EvidencePack"):
            ensure_evidence_bound_response(response, _synthesis_input())

    def test_evidence_bound_response_rejects_high_confidence_for_risky_context(self):
        response = _valid_response()
        response["confidence"] = 0.8

        with self.assertRaisesRegex(ValueError, "must keep confidence low"):
            ensure_evidence_bound_response(response, _risky_synthesis_input())

    def test_budget_role_opportunity_synthesis_exists(self):
        request = build_opportunity_synthesis_request(_synthesis_input())
        allowed, reasons = check_llm_budget(
            default_local_preview_llm_budget_policy(),
            LLMBudgetState(),
            request,
            estimated_output_tokens=120,
        )

        self.assertEqual(request.task_type, LLM_OPPORTUNITY_SYNTHESIS_TASK_TYPE)
        self.assertEqual(request.metadata["budget_role"], LLM_OPPORTUNITY_SYNTHESIS_TASK_TYPE)
        self.assertTrue(allowed)
        self.assertEqual(reasons, [])

    def test_contract_only_no_provider_or_network_calls(self):
        source = Path("src/oos/llm_opportunity_synthesis_contract.py").read_text(encoding="utf-8")

        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("complete(", source)


def _synthesis_input() -> LLMOpportunitySynthesisInput:
    pack = _cash_collection_pack()
    return LLMOpportunitySynthesisInput(
        synthesis_id="synthesis_cash_collection",
        evidence_pack=pack,
        baseline_candidate=build_opportunity_sketch_from_evidence_pack(pack),
    )


def _risky_synthesis_input() -> LLMOpportunitySynthesisInput:
    pack = _cash_collection_pack(
        risk_notes=[
            EvidencePackRiskNote(
                risk_type="source_quality_issue",
                note="Vendor-promo-like generic evidence requires review.",
                evidence_id="evidence_invoice_a",
                severity="high",
            )
        ]
    )
    return LLMOpportunitySynthesisInput(
        synthesis_id="synthesis_risky",
        evidence_pack=pack,
        baseline_candidate=build_opportunity_sketch_from_evidence_pack(pack),
    )


def _valid_response():
    return {
        "problem_statement": "SMB operators have recurring cash-collection pain around unpaid invoice follow-up.",
        "target_user": "small business operator",
        "current_workaround": "manual follow-up; spreadsheet",
        "opportunity_sketch": "Advisory sketch only: review a narrow cash-collection follow-up workflow.",
        "why_now": "Evidence includes unpaid invoice timing language.",
        "possible_buyer": "small business operator",
        "product_wedge": "unknown",
        "evidence_ids": ["evidence_invoice_a", "evidence_invoice_b"],
        "source_signal_ids": ["signal_invoice_a", "signal_invoice_b"],
        "source_urls": ["https://example.com/evidence_invoice_a", "https://example.com/evidence_invoice_b"],
        "unsupported_assumptions": ["product_wedge", "price_or_budget"],
        "confidence": 0.52,
        "risk_notes": ["price_or_budget unsupported"],
        "cited_evidence": [
            {
                "evidence_id": "evidence_invoice_a",
                "claim": "unpaid invoice follow-up pain",
                "citation": "Small business operator has unpaid invoice follow-up email pain.",
            },
            {
                "evidence_id": "evidence_invoice_b",
                "claim": "manual spreadsheet workaround",
                "citation": "Small business owner tracks cash collection with manual spreadsheet follow-up.",
            },
        ],
        "advisory_only": True,
    }


def _cash_collection_pack(risk_notes=None):
    evidence_ids = ["evidence_invoice_a", "evidence_invoice_b"]
    signal_ids = ["signal_invoice_a", "signal_invoice_b"]
    source_urls = ["https://example.com/evidence_invoice_a", "https://example.com/evidence_invoice_b"]
    source_types = ["hn", "github_issue"]
    summaries = [
        "Small business operator has unpaid invoice follow-up email pain.",
        "Small business owner tracks cash collection with manual spreadsheet follow-up.",
    ]
    items = [
        EvidencePackItem(
            evidence_id=evidence_id,
            source_signal_id=signal_ids[index],
            source_url=source_urls[index],
            source_type=source_types[index],
            summary=summaries[index],
            confidence=[0.62, 0.66][index],
        )
        for index, evidence_id in enumerate(evidence_ids)
    ]
    return EvidencePack(
        evidence_pack_id=make_evidence_pack_id("cash_collection"),
        cluster_id="cash_collection",
        source_signal_ids=signal_ids,
        evidence_ids=evidence_ids,
        source_urls=source_urls,
        summaries=summaries,
        source_types=source_types,
        topic_id="ai_cfo_smb",
        confidence_values=[0.62, 0.66],
        source_diversity=2,
        recurrence_count=2,
        created_from="fixture_evidence_pack",
        price_signal_ids=[],
        weak_pattern_ids=["weak_pattern_cash_collection"],
        kill_warning_ids=[],
        risk_notes=risk_notes or [],
        items=items,
        source_summaries=[
            EvidencePackSourceSummary("hn", 1, ["evidence_invoice_a"]),
            EvidencePackSourceSummary("github_issue", 1, ["evidence_invoice_b"]),
        ],
    )


if __name__ == "__main__":
    unittest.main()
