import json
import unittest
from dataclasses import replace
from pathlib import Path

from oos.evidence_pack import EvidencePack, EvidencePackItem, EvidencePackRiskNote
from oos.evidence_sufficiency_scoring import score_evidence_sufficiency
from oos.opportunity_false_positive_suppressor import (
    KEEP,
    PARK,
    REJECT,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    assess_opportunity_false_positive,
)
from oos.opportunity_quality_gate import PASS, evaluate_opportunity_quality
from oos.opportunity_sketch import OpportunityCandidate, build_opportunity_sketch_from_evidence_pack


class OpportunityFalsePositiveSuppressorTests(unittest.TestCase):
    def test_generic_ai_dashboard_with_weak_evidence_is_false_positive(self):
        candidate = self._manual_candidate(
            problem_statement="Finance teams need a generic AI dashboard.",
            opportunity_sketch="Build an AI dashboard for finance leaders.",
            product_wedge="AI dashboard",
            possible_buyer="unknown",
            current_workaround="unknown",
            unsupported_assumptions=["buyer", "product_wedge", "price_or_budget"],
            confidence=0.42,
        )

        assessment = assess_opportunity_false_positive(candidate)

        self.assertTrue(assessment.is_false_positive)
        self.assertIn(assessment.severity, {SEVERITY_HIGH, SEVERITY_CRITICAL})
        self.assertIn("ai dashboard", assessment.matched_patterns)
        self.assertIn(assessment.recommended_gate_decision, {PARK, REJECT})

    def test_vendor_seo_derived_opportunity_is_false_positive(self):
        pack = self._vendor_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        assessment = assess_opportunity_false_positive(candidate, pack)

        self.assertTrue(assessment.is_false_positive)
        self.assertIn(assessment.severity, {SEVERITY_HIGH, SEVERITY_CRITICAL})
        self.assertIn("vendor_promo", assessment.matched_patterns)
        self.assertEqual(assessment.recommended_next_action, "suppress_as_false_positive")

    def test_product_submission_derived_opportunity_is_false_positive(self):
        pack = self._product_submission_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        assessment = assess_opportunity_false_positive(candidate, pack)

        self.assertTrue(assessment.is_false_positive)
        self.assertIn(assessment.severity, {SEVERITY_HIGH, SEVERITY_CRITICAL})
        self.assertIn("product_submission", assessment.matched_patterns)

    def test_disguised_consulting_pattern_is_false_positive(self):
        candidate = self._manual_candidate(
            problem_statement="Small businesses need bookkeeping expert consultation.",
            opportunity_sketch="Offer a bookkeeping expert consulting service for small businesses.",
            product_wedge="professional services",
            unsupported_assumptions=["price_or_budget"],
            confidence=0.55,
        )

        assessment = assess_opportunity_false_positive(candidate)

        self.assertTrue(assessment.is_false_positive)
        self.assertIn(assessment.severity, {SEVERITY_HIGH, SEVERITY_CRITICAL})
        self.assertIn("disguised_consulting", {reason.code for reason in assessment.reasons})

    def test_no_evidence_ids_is_critical_false_positive(self):
        candidate = replace(self._strong_cash_candidate(), evidence_ids=[])

        assessment = assess_opportunity_false_positive(candidate)

        self.assertTrue(assessment.is_false_positive)
        self.assertEqual(assessment.severity, SEVERITY_CRITICAL)
        self.assertEqual(assessment.recommended_gate_decision, REJECT)

    def test_no_source_urls_is_critical_false_positive(self):
        candidate = replace(self._strong_cash_candidate(), source_urls=[])

        assessment = assess_opportunity_false_positive(candidate)

        self.assertTrue(assessment.is_false_positive)
        self.assertEqual(assessment.severity, SEVERITY_CRITICAL)
        self.assertEqual(assessment.recommended_gate_decision, REJECT)

    def test_no_buyer_and_no_workaround_produces_medium_severity(self):
        candidate = self._manual_candidate(
            possible_buyer="unknown",
            current_workaround="unknown",
            unsupported_assumptions=["buyer", "workaround"],
        )

        assessment = assess_opportunity_false_positive(candidate)

        self.assertTrue(assessment.is_false_positive)
        self.assertIn(assessment.severity, {SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL})
        self.assertIn("buyer_and_workaround_missing", {reason.code for reason in assessment.reasons})

    def test_too_many_unsupported_assumptions_produces_high_severity(self):
        candidate = self._manual_candidate(
            unsupported_assumptions=["buyer", "product_wedge", "why_now", "price_or_budget"],
            confidence=0.8,
        )

        assessment = assess_opportunity_false_positive(candidate)

        self.assertIn(assessment.severity, {SEVERITY_HIGH, SEVERITY_CRITICAL})
        self.assertIn("unsupported_assumptions_dominate", {reason.code for reason in assessment.reasons})

    def test_low_evidence_sufficiency_score_contributes_to_suppression(self):
        candidate = self._manual_candidate(
            problem_statement="unknown",
            opportunity_sketch="unknown",
            evidence_ids=[],
            source_urls=[],
            confidence=0.15,
        )
        score = score_evidence_sufficiency(candidate)

        assessment = assess_opportunity_false_positive(candidate, evidence_sufficiency_score=score)

        self.assertEqual(score.score_band, "insufficient")
        self.assertEqual(assessment.severity, SEVERITY_CRITICAL)
        self.assertIn("evidence_sufficiency_insufficient", {reason.code for reason in assessment.reasons})

    def test_strong_unpaid_invoice_cash_collection_opportunity_is_not_suppressed(self):
        pack = self._cash_collection_pack()
        candidate = self._strong_cash_candidate(pack)

        assessment = assess_opportunity_false_positive(candidate, pack)

        self.assertFalse(assessment.is_false_positive)
        self.assertEqual(assessment.severity, "none")
        self.assertEqual(assessment.recommended_gate_decision, KEEP)

    def test_ynab_month_end_reporting_is_not_rejected_as_false_positive(self):
        pack = self._ynab_reporting_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        assessment = assess_opportunity_false_positive(candidate, pack)

        self.assertIn(assessment.recommended_gate_decision, {KEEP, PARK})
        self.assertNotEqual(assessment.recommended_gate_decision, REJECT)

    def test_assessment_preserves_traceability(self):
        pack = self._cash_collection_pack()
        candidate = self._strong_cash_candidate(pack)

        assessment = assess_opportunity_false_positive(candidate, pack)

        self.assertEqual(assessment.evidence_ids, sorted(candidate.evidence_ids))
        self.assertEqual(assessment.source_signal_ids, sorted(candidate.source_signal_ids))
        self.assertEqual(assessment.source_urls, sorted(candidate.source_urls))

    def test_quality_gate_prevents_pass_for_high_or_critical_false_positives(self):
        candidate = self._manual_candidate(
            problem_statement="Finance teams need a generic AI dashboard.",
            opportunity_sketch="Build an AI dashboard for finance leaders.",
            product_wedge="AI dashboard",
            possible_buyer="finance leader",
            current_workaround="spreadsheet",
            why_now="Evidence recurs across multiple items.",
            unsupported_assumptions=["price_or_budget"],
            confidence=0.9,
        )

        result = evaluate_opportunity_quality(candidate)

        self.assertNotEqual(result.decision, PASS)
        self.assertFalse(result.auto_promote)
        self.assertTrue(result.founder_decision_required)
        self.assertIsNotNone(result.false_positive_assessment)

    def test_assessment_serializes_to_json_compatible_dict(self):
        assessment = assess_opportunity_false_positive(self._strong_cash_candidate(), self._cash_collection_pack())
        payload = assessment.to_dict()

        self.assertEqual(payload["schema_version"], "opportunity_false_positive_assessment.v1")
        json.dumps(payload, sort_keys=True)

    def test_output_is_deterministic(self):
        pack = self._vendor_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        first = assess_opportunity_false_positive(candidate, pack).to_dict()
        second = assess_opportunity_false_positive(candidate, pack).to_dict()

        self.assertEqual(first, second)

    def test_no_live_network_or_llm_calls_are_present(self):
        source = Path("src/oos/opportunity_false_positive_suppressor.py").read_text(encoding="utf-8")

        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("complete(", source)

    def _strong_cash_candidate(self, pack: EvidencePack | None = None) -> OpportunityCandidate:
        pack = pack or self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        return replace(
            candidate,
            product_wedge="invoice follow-up workflow support",
            possible_buyer="small business operator",
            unsupported_assumptions=[],
            confidence=0.78,
        )

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

    def _product_submission_pack(self) -> EvidencePack:
        return EvidencePack(
            evidence_pack_id="pack_product_submission",
            cluster_id="quickbooks_mcp_submission",
            source_signal_ids=["sig_qb_mcp"],
            evidence_ids=["raw_github_issue_4103786450"],
            source_urls=["https://github.com/example/mcp/issues/1"],
            summaries=["QuickBooks MCP hosted server product submission and marketplace listing."],
            source_types=["github"],
            topic_id="product_submission",
            confidence_values=[0.22],
            source_diversity=1,
            recurrence_count=1,
            created_from="test_fixture",
            risk_notes=[
                EvidencePackRiskNote(
                    risk_type="product_submission",
                    severity="high",
                    evidence_id="raw_github_issue_4103786450",
                    note="Product submission, not user pain.",
                )
            ],
        )

    def _manual_candidate(
        self,
        *,
        opportunity_id: str = "opportunity_manual",
        evidence_pack_id: str = "pack_manual",
        cluster_id: str = "manual_cluster",
        problem_statement: str = "SMB operators have recurring cash-collection pain around unpaid invoice follow-up.",
        target_user: str = "small business operator",
        current_workaround: str = "manual follow-up",
        opportunity_sketch: str = "Evidence-bound baseline: unpaid invoice follow-up pain.",
        why_now: str = "Evidence includes timing-sensitive finance workflow language.",
        possible_buyer: str = "small business operator",
        product_wedge: str = "invoice follow-up workflow support",
        evidence_ids: list[str] | None = None,
        source_signal_ids: list[str] | None = None,
        source_urls: list[str] | None = None,
        unsupported_assumptions: list[str] | None = None,
        confidence: float = 0.7,
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
            evidence_ids=evidence_ids if evidence_ids is not None else ["evidence_1"],
            source_signal_ids=source_signal_ids if source_signal_ids is not None else ["signal_1"],
            source_urls=source_urls if source_urls is not None else ["https://example.com/evidence"],
            unsupported_assumptions=unsupported_assumptions or [],
            confidence=confidence,
            risk_notes=risk_notes or [],
        )


if __name__ == "__main__":
    unittest.main()
