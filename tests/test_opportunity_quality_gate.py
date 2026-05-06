import json
import unittest
from dataclasses import replace
from pathlib import Path

from oos.evidence_pack import EvidencePack, EvidencePackItem, EvidencePackRiskNote
from oos.opportunity_quality_gate import (
    FOUNDER_REVIEW,
    PARK,
    PASS,
    REJECT,
    OpportunityGateResult,
    evaluate_opportunity_batch,
    evaluate_opportunity_quality,
)
from oos.opportunity_sketch import OpportunityCandidate, build_opportunity_sketch_from_evidence_pack


class OpportunityQualityGateTests(unittest.TestCase):
    def test_strong_unpaid_invoice_opportunity_passes_for_founder_review(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, product_wedge="invoice follow-up workflow support", unsupported_assumptions=[])

        result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(result.decision, PASS)
        self.assertEqual(result.recommended_next_action, FOUNDER_REVIEW)
        self.assertFalse(result.auto_promote)
        self.assertTrue(result.founder_decision_required)

    def test_ynab_month_end_reporting_parks_with_clear_rationale(self):
        pack = self._ynab_reporting_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        result = evaluate_opportunity_quality(candidate, pack)

        self.assertIn(result.decision, {PASS, PARK})
        self.assertTrue(result.reasons)
        self.assertIn("raw_github_issue_1182773055", result.evidence_ids)

    def test_missing_buyer_causes_park_not_pass(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, possible_buyer="unknown", target_user="unknown")

        result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(result.decision, PARK)
        self.assertIn("possible_buyer", result.missing_evidence)

    def test_missing_evidence_ids_causes_reject(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, evidence_ids=[])

        result = evaluate_opportunity_quality(candidate, None)

        self.assertEqual(result.decision, REJECT)
        self.assertIn("missing_evidence_ids", result.blocking_issues)

    def test_missing_source_urls_causes_reject(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, source_urls=[])

        result = evaluate_opportunity_quality(candidate, None)

        self.assertEqual(result.decision, REJECT)
        self.assertIn("missing_source_urls", result.blocking_issues)

    def test_unknown_generic_problem_rejects(self):
        candidate = self._manual_candidate(problem_statement="unknown", confidence=0.4)

        result = evaluate_opportunity_quality(candidate)

        self.assertEqual(result.decision, REJECT)
        self.assertIn("generic_or_unknown_problem", result.blocking_issues)

    def test_vendor_generic_risk_note_rejects(self):
        pack = self._vendor_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(result.decision, REJECT)
        self.assertIn("vendor_or_generic_risk", result.blocking_issues)

    def test_insufficient_evidence_parks_or_rejects_by_severity(self):
        pack = self._insufficient_pack()
        candidate = self._manual_candidate(
            evidence_pack_id=pack.evidence_pack_id,
            cluster_id=pack.cluster_id,
            problem_statement="SMB operators mention unpaid invoice follow-up but evidence is thin.",
            evidence_ids=["raw_hn_1"],
            source_signal_ids=["sig_1"],
            source_urls=["https://news.ycombinator.com/item?id=1"],
            current_workaround="manual follow-up",
            possible_buyer="small business operator",
            product_wedge="unknown",
            confidence=0.28,
            unsupported_assumptions=["product_wedge", "price_or_budget"],
            risk_notes=["insufficient_evidence_count: only one signal"],
        )

        result = evaluate_opportunity_quality(candidate, pack)

        self.assertIn(result.decision, {PARK, REJECT})
        self.assertIn("sufficient_evidence", result.missing_evidence)

    def test_too_many_unsupported_assumptions_prevents_pass(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(
            candidate,
            unsupported_assumptions=["buyer", "product_wedge", "why_now", "price_or_budget"],
            possible_buyer="unknown",
            product_wedge="unknown",
            confidence=0.7,
        )

        result = evaluate_opportunity_quality(candidate, pack)

        self.assertNotEqual(result.decision, PASS)

    def test_result_preserves_traceability(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(result.evidence_ids, sorted(pack.evidence_ids))
        self.assertEqual(result.source_signal_ids, sorted(pack.source_signal_ids))
        self.assertEqual(result.source_urls, sorted(pack.source_urls))

    def test_result_serializes_to_json_compatible_dict(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        result = evaluate_opportunity_quality(candidate, pack)
        payload = result.to_dict()

        self.assertEqual(payload["schema_version"], "opportunity_quality_gate.v1")
        self.assertIn(payload["decision"], {PASS, PARK, REJECT})
        json.dumps(payload, sort_keys=True)

    def test_output_is_deterministic(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        first = evaluate_opportunity_quality(candidate, pack).to_dict()
        second = evaluate_opportunity_quality(candidate, pack).to_dict()

        self.assertEqual(first, second)

    def test_gate_result_validation_rejects_auto_promote(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        result = evaluate_opportunity_quality(candidate, pack)
        invalid = OpportunityGateResult(**{**result.to_dict(), "auto_promote": True})

        with self.assertRaises(ValueError):
            invalid.validate()

    def test_legacy_batch_wrapper_preserves_signal_ids_and_founder_override_none(self):
        opportunity = {
            "opportunity_id": "opp_reporting_trust",
            "confidence": 0.84,
            "linked_signal_ids": ["sig_2", "sig_1"],
            "assumptions": [{"assumption_id": "asm_budget"}],
            "risks": ["Budget not proven yet."],
            "evidence_missing": False,
        }

        result = evaluate_opportunity_batch([opportunity])

        self.assertEqual(result.decisions[0].status, PASS)
        self.assertEqual(result.decisions[0].linked_signal_ids, ["sig_1", "sig_2"])
        self.assertIsNone(result.decisions[0].founder_override_status)

    def test_no_live_network_or_llm_calls_are_present(self):
        source = Path("src/oos/opportunity_quality_gate.py").read_text(encoding="utf-8")

        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("complete(", source)

    def _cash_collection_pack(self) -> EvidencePack:
        return EvidencePack(
            evidence_pack_id="pack_cash_collection",
            cluster_id="cash_collection",
            source_signal_ids=["sig_invoice_1", "sig_invoice_2"],
            evidence_ids=["raw_hn_47082761", "raw_hn_invoice_2"],
            source_urls=[
                "https://news.ycombinator.com/item?id=47082761",
                "https://news.ycombinator.com/item?id=47082762",
            ],
            summaries=[
                "Small business operator describes unpaid invoice follow-up email pain and manual follow-up.",
                "Another SMB owner mentions overdue invoice payment follow up by email.",
            ],
            source_types=["github", "hn"],
            topic_id="cash_collection",
            confidence_values=[0.78, 0.74],
            source_diversity=2,
            recurrence_count=2,
            created_from="test_fixture",
            price_signal_ids=["price_affordability_1"],
            items=[
                EvidencePackItem(
                    evidence_id="raw_hn_47082761",
                    source_signal_id="sig_invoice_1",
                    source_url="https://news.ycombinator.com/item?id=47082761",
                    source_type="hn",
                    summary="Small business operator describes unpaid invoice follow-up email pain and manual follow-up.",
                    confidence=0.78,
                ),
                EvidencePackItem(
                    evidence_id="raw_hn_invoice_2",
                    source_signal_id="sig_invoice_2",
                    source_url="https://news.ycombinator.com/item?id=47082762",
                    source_type="hn",
                    summary="Another SMB owner mentions overdue invoice payment follow up by email.",
                    confidence=0.74,
                ),
            ],
        )

    def _ynab_reporting_pack(self) -> EvidencePack:
        return EvidencePack(
            evidence_pack_id="pack_reporting",
            cluster_id="month_end_reporting",
            source_signal_ids=["sig_ynab"],
            evidence_ids=["raw_github_issue_1182773055"],
            source_urls=["https://github.com/example/ynab/issues/1"],
            summaries=["YNAB user asks for balance sheet and historical month-end balance reporting."],
            source_types=["github"],
            topic_id="finance_reporting",
            confidence_values=[0.68],
            source_diversity=1,
            recurrence_count=1,
            created_from="test_fixture",
            items=[
                EvidencePackItem(
                    evidence_id="raw_github_issue_1182773055",
                    source_signal_id="sig_ynab",
                    source_url="https://github.com/example/ynab/issues/1",
                    source_type="github",
                    summary="YNAB user asks for balance sheet and historical month-end balance reporting.",
                    confidence=0.68,
                )
            ],
        )

    def _vendor_pack(self) -> EvidencePack:
        return EvidencePack(
            evidence_pack_id="pack_vendor",
            cluster_id="vendor_copy",
            source_signal_ids=["sig_vendor"],
            evidence_ids=["raw_github_issue_3565323722"],
            source_urls=["https://github.com/example/vendor/issues/1"],
            summaries=["Zoho Books free demo affordable pricing transform your business promotional copy."],
            source_types=["github"],
            topic_id="vendor_noise",
            confidence_values=[0.2],
            source_diversity=1,
            recurrence_count=1,
            created_from="test_fixture",
            risk_notes=[
                EvidencePackRiskNote(
                    risk_type="vendor_promo",
                    severity="high",
                    evidence_id="raw_github_issue_3565323722",
                    note="Vendor promo and SEO copy dominates.",
                )
            ],
        )

    def _insufficient_pack(self) -> EvidencePack:
        return EvidencePack(
            evidence_pack_id="pack_insufficient",
            cluster_id="thin_cash_collection",
            source_signal_ids=["sig_1"],
            evidence_ids=["raw_hn_1"],
            source_urls=["https://news.ycombinator.com/item?id=1"],
            summaries=["One mention of unpaid invoice follow-up.",
            ],
            source_types=["hn"],
            topic_id="cash_collection",
            confidence_values=[0.3],
            source_diversity=1,
            recurrence_count=1,
            created_from="insufficient_evidence",
            risk_notes=[
                EvidencePackRiskNote(
                    risk_type="insufficient_evidence_count",
                    severity="medium",
                    evidence_id="raw_hn_1",
                    note="Only one supporting item.",
                )
            ],
        )

    def _manual_candidate(
        self,
        *,
        opportunity_id: str = "opportunity_manual",
        evidence_pack_id: str = "pack_manual",
        cluster_id: str = "manual_cluster",
        problem_statement: str = "Generic problem",
        target_user: str = "unknown",
        current_workaround: str = "unknown",
        opportunity_sketch: str = "Evidence-bound baseline: Generic problem.",
        why_now: str = "unknown",
        possible_buyer: str = "unknown",
        product_wedge: str = "unknown",
        evidence_ids: list[str] | None = None,
        source_signal_ids: list[str] | None = None,
        source_urls: list[str] | None = None,
        unsupported_assumptions: list[str] | None = None,
        confidence: float = 0.3,
        risk_notes: list[str] | None = None,
    ) -> OpportunityCandidate:
        return OpportunityCandidate(
            opportunity_id=opportunity_id,
            evidence_pack_id=evidence_pack_id,
            cluster_id=cluster_id,
            problem_statement=problem_statement,
            target_user=target_user,
            current_workaround=current_workaround,
            opportunity_sketch=opportunity_sketch,
            why_now=why_now,
            possible_buyer=possible_buyer,
            product_wedge=product_wedge,
            evidence_ids=evidence_ids or ["evidence_1"],
            source_signal_ids=source_signal_ids or ["signal_1"],
            source_urls=source_urls or ["https://example.com/evidence"],
            unsupported_assumptions=unsupported_assumptions or [],
            confidence=confidence,
            risk_notes=risk_notes or [],
        )


if __name__ == "__main__":
    unittest.main()
