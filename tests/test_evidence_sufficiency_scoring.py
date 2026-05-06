import json
import unittest
from dataclasses import replace
from pathlib import Path

from oos.evidence_pack import EvidencePack, EvidencePackItem, EvidencePackRiskNote
from oos.evidence_sufficiency_scoring import (
    ADEQUATE,
    INSUFFICIENT,
    STRONG,
    WEAK,
    DIMENSION_NAMES,
    score_evidence_sufficiency,
)
from oos.opportunity_quality_gate import evaluate_opportunity_quality
from oos.opportunity_sketch import OpportunityCandidate, build_opportunity_sketch_from_evidence_pack


class EvidenceSufficiencyScoringTests(unittest.TestCase):
    def test_strong_cash_collection_opportunity_receives_strong_or_adequate_score(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, product_wedge="invoice follow-up workflow support", unsupported_assumptions=[])

        score = score_evidence_sufficiency(candidate, pack)

        self.assertIn(score.score_band, {STRONG, ADEQUATE})
        self.assertGreaterEqual(score.dimension_scores["pain_evidence_strength"], 0.7)
        self.assertGreaterEqual(score.dimension_scores["traceability_strength"], 0.9)

    def test_ynab_month_end_reporting_scores_adequate_or_weak_for_buyer_wtp_gaps(self):
        pack = self._ynab_reporting_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        score = score_evidence_sufficiency(candidate, pack)

        self.assertIn(score.score_band, {ADEQUATE, WEAK})
        self.assertIn("willingness_to_pay_evidence", score.missing_evidence)

    def test_missing_evidence_ids_produces_insufficient_score(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, evidence_ids=[])

        score = score_evidence_sufficiency(candidate, None)

        self.assertEqual(score.score_band, INSUFFICIENT)
        self.assertIn("evidence_ids", score.missing_evidence)

    def test_missing_source_urls_lowers_traceability(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, source_urls=[])

        score = score_evidence_sufficiency(candidate, None)

        self.assertLess(score.dimension_scores["traceability_strength"], 1.0)
        self.assertIn("source_urls", score.missing_evidence)

    def test_unknown_buyer_lowers_buyer_clarity(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, possible_buyer="unknown", target_user="unknown")

        score = score_evidence_sufficiency(candidate, pack)

        self.assertEqual(score.dimension_scores["buyer_clarity"], 0.0)
        self.assertIn("buyer_clarity", score.missing_evidence)

    def test_missing_price_wtp_lowers_willingness_to_pay_evidence(self):
        pack = replace(self._cash_collection_pack(), price_signal_ids=[])
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        score = score_evidence_sufficiency(candidate, pack)

        self.assertLess(score.dimension_scores["willingness_to_pay_evidence"], 0.5)
        self.assertIn("willingness_to_pay_evidence", score.missing_evidence)

    def test_recurrence_and_source_diversity_help_but_do_not_override_missing_pain(self):
        pack = self._generic_high_recurrence_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, problem_statement="unknown")

        score = score_evidence_sufficiency(candidate, pack)

        self.assertGreaterEqual(score.dimension_scores["recurrence_strength"], 0.75)
        self.assertGreaterEqual(score.dimension_scores["source_diversity_strength"], 0.75)
        self.assertEqual(score.score_band, INSUFFICIENT)

    def test_vendor_generic_risk_notes_reduce_score(self):
        pack = self._vendor_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        score = score_evidence_sufficiency(candidate, pack)

        self.assertGreaterEqual(score.dimension_scores["risk_penalty"], 0.55)
        self.assertIn("risk_notes", score.risk_factors)
        self.assertIn(score.score_band, {WEAK, INSUFFICIENT})

    def test_ambiguity_needs_more_evidence_reduces_score(self):
        pack = replace(
            self._cash_collection_pack(),
            risk_notes=[
                EvidencePackRiskNote(
                    risk_type="needs_more_evidence",
                    severity="medium",
                    evidence_id="raw_hn_47082761",
                    note="Founder should review ambiguity before promotion.",
                )
            ],
        )
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        score = score_evidence_sufficiency(candidate, pack)

        self.assertGreater(score.dimension_scores["ambiguity_penalty"], 0.0)
        self.assertIn("unsupported_or_ambiguous_evidence", score.risk_factors)

    def test_score_is_deterministic(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        self.assertEqual(
            score_evidence_sufficiency(candidate, pack).to_dict(),
            score_evidence_sufficiency(candidate, pack).to_dict(),
        )

    def test_score_is_json_serializable_and_has_all_dimensions(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        payload = score_evidence_sufficiency(candidate, pack).to_dict()

        self.assertEqual(set(payload["dimension_scores"]), set(DIMENSION_NAMES))
        json.dumps(payload, sort_keys=True)

    def test_quality_gate_includes_score_without_auto_promoting(self):
        pack = self._cash_collection_pack()
        candidate = build_opportunity_sketch_from_evidence_pack(pack)
        candidate = replace(candidate, product_wedge="invoice follow-up workflow support", unsupported_assumptions=[])

        result = evaluate_opportunity_quality(candidate, pack)

        payload = result.to_dict()
        self.assertIn("evidence_sufficiency_score", payload)
        self.assertFalse(payload["auto_promote"])
        self.assertTrue(payload["founder_decision_required"])

    def test_no_live_network_or_llm_calls_are_present(self):
        source = Path("src/oos/evidence_sufficiency_scoring.py").read_text(encoding="utf-8")

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
                "https://github.com/example/invoice/issues/2",
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
                )
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

    def _generic_high_recurrence_pack(self) -> EvidencePack:
        return EvidencePack(
            evidence_pack_id="pack_generic",
            cluster_id="generic_ops",
            source_signal_ids=["sig_1", "sig_2", "sig_3", "sig_4"],
            evidence_ids=["ev_1", "ev_2", "ev_3", "ev_4"],
            source_urls=[
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
                "https://example.com/4",
            ],
            summaries=["Business software exists."],
            source_types=["github", "hn"],
            topic_id="generic",
            confidence_values=[0.6, 0.6, 0.6, 0.6],
            source_diversity=2,
            recurrence_count=4,
            created_from="test_fixture",
        )


if __name__ == "__main__":
    unittest.main()
