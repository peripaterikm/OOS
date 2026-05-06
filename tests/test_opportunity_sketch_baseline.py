import json
import unittest

from oos.evidence_pack import (
    INSUFFICIENT_EVIDENCE_CREATED_FROM,
    EvidencePack,
    EvidencePackItem,
    EvidencePackRiskNote,
    EvidencePackSourceSummary,
    make_evidence_pack_id,
)
from oos.opportunity_sketch import (
    OPPORTUNITY_SKETCH_SCHEMA_VERSION,
    OpportunityCandidate,
    build_opportunity_sketch_from_evidence_pack,
    opportunity_sketch_from_dict,
    opportunity_sketch_to_dict,
)


class OpportunitySketchBaselineTests(unittest.TestCase):
    def test_opportunity_candidate_can_be_created(self):
        candidate = build_opportunity_sketch_from_evidence_pack(_cash_collection_pack())

        self.assertIsInstance(candidate, OpportunityCandidate)
        self.assertEqual(candidate.schema_version, OPPORTUNITY_SKETCH_SCHEMA_VERSION)
        candidate.validate()

    def test_opportunity_candidate_serializes_and_round_trips(self):
        candidate = build_opportunity_sketch_from_evidence_pack(_cash_collection_pack())

        restored = opportunity_sketch_from_dict(json.loads(json.dumps(opportunity_sketch_to_dict(candidate), sort_keys=True)))

        self.assertEqual(restored, candidate)

    def test_build_preserves_evidence_pack_id_and_traceability(self):
        pack = _cash_collection_pack()

        candidate = build_opportunity_sketch_from_evidence_pack(pack)

        self.assertEqual(candidate.evidence_pack_id, pack.evidence_pack_id)
        self.assertEqual(candidate.evidence_ids, ["evidence_invoice_a", "evidence_invoice_b"])
        self.assertEqual(candidate.source_signal_ids, ["signal_invoice_a", "signal_invoice_b"])
        self.assertEqual(
            candidate.source_urls,
            ["https://example.com/evidence_invoice_a", "https://example.com/evidence_invoice_b"],
        )

    def test_unpaid_invoice_follow_up_produces_cash_collection_problem_statement(self):
        candidate = build_opportunity_sketch_from_evidence_pack(_cash_collection_pack())

        self.assertIn("cash-collection", candidate.problem_statement)
        self.assertIn("unpaid invoice", candidate.problem_statement)
        self.assertIn("manual follow-up", candidate.current_workaround)
        self.assertEqual(candidate.target_user, "small business operator")

    def test_month_end_balance_evidence_produces_reporting_problem_statement(self):
        candidate = build_opportunity_sketch_from_evidence_pack(_month_end_reporting_pack())

        self.assertIn("month-end", candidate.problem_statement)
        self.assertIn("balance-sheet reporting", candidate.problem_statement)
        self.assertEqual(candidate.product_wedge, "reporting workflow support")

    def test_missing_buyer_and_product_wedge_are_unknown_and_marked_unsupported(self):
        candidate = build_opportunity_sketch_from_evidence_pack(
            _pack(
                cluster_id="generic_finance",
                summaries=["Accurate financial records matter for tax obligations."],
                risk_notes=[EvidencePackRiskNote("source_quality_issue", "Generic accounting copy.", severity="medium")],
            )
        )

        self.assertEqual(candidate.possible_buyer, "unknown")
        self.assertEqual(candidate.product_wedge, "unknown")
        self.assertIn("buyer", candidate.unsupported_assumptions)
        self.assertIn("product_wedge", candidate.unsupported_assumptions)

    def test_missing_price_and_why_now_are_marked_unsupported(self):
        candidate = build_opportunity_sketch_from_evidence_pack(
            _pack(
                cluster_id="generic_smb_finance",
                summaries=["Small business operator has finance workflow friction."],
                evidence_ids=["evidence_generic"],
                signal_ids=["signal_generic"],
                source_urls=["https://example.com/evidence_generic"],
                price_signal_ids=[],
            )
        )

        self.assertIn("price_or_budget", candidate.unsupported_assumptions)
        self.assertIn("why_now", candidate.unsupported_assumptions)

    def test_insufficient_evidence_produces_low_confidence(self):
        candidate = build_opportunity_sketch_from_evidence_pack(_insufficient_pack())

        self.assertLessEqual(candidate.confidence, 0.25)
        self.assertTrue(any("insufficient_evidence" in note for note in candidate.risk_notes))

    def test_vendor_generic_risk_note_lowers_confidence_or_adds_risk(self):
        baseline = build_opportunity_sketch_from_evidence_pack(_cash_collection_pack())
        risky = build_opportunity_sketch_from_evidence_pack(
            _pack(
                cluster_id="generic_vendor_copy",
                summaries=["Transform your business with generic accounting software and affordable pricing."],
                risk_notes=[EvidencePackRiskNote("source_quality_issue", "Vendor-promo source quality issue.", severity="medium")],
            )
        )

        self.assertLess(risky.confidence, baseline.confidence)
        self.assertTrue(any("source_quality_issue" in note for note in risky.risk_notes))

    def test_output_ordering_is_deterministic(self):
        pack = _pack(
            cluster_id="order_test",
            summaries=["Small business owner sends email follow up for unpaid invoices.", "Manual spreadsheet tracking."],
            evidence_ids=["evidence_b", "evidence_a"],
            signal_ids=["signal_b", "signal_a"],
            source_urls=["https://example.com/b", "https://example.com/a"],
        )

        first = opportunity_sketch_to_dict(build_opportunity_sketch_from_evidence_pack(pack))
        second = opportunity_sketch_to_dict(build_opportunity_sketch_from_evidence_pack(pack))

        self.assertEqual(first, second)
        self.assertEqual(first["evidence_ids"], ["evidence_a", "evidence_b"])

    def test_no_live_network_or_llm_calls_are_made(self):
        candidate = build_opportunity_sketch_from_evidence_pack(_cash_collection_pack())

        payload = json.dumps(opportunity_sketch_to_dict(candidate), sort_keys=True)
        self.assertNotIn("provider.complete", payload)
        self.assertNotIn("allow_live_network", payload)


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
        price_signal_ids=["price_affordability"],
        weak_pattern_ids=["weak_pattern_cash_collection"],
    )


def _month_end_reporting_pack(price_signal_ids=None):
    return _pack(
        cluster_id="month_end_reporting",
        summaries=[
            "YNAB user asks for balance sheet and historical month-end balances.",
            "Finance user needs month-end reporting from existing records.",
        ],
        evidence_ids=["evidence_reporting_a", "evidence_reporting_b"],
        signal_ids=["signal_reporting_a", "signal_reporting_b"],
        source_urls=["https://example.com/evidence_reporting_a", "https://example.com/evidence_reporting_b"],
        price_signal_ids=[] if price_signal_ids is None else price_signal_ids,
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
    evidence_ids=None,
    signal_ids=None,
    source_urls=None,
    risk_notes=None,
    price_signal_ids=None,
    weak_pattern_ids=None,
    kill_warning_ids=None,
    created_from="fixture_evidence_pack",
    confidence_values=None,
):
    evidence_ids = evidence_ids or ["evidence_a", "evidence_b"]
    signal_ids = signal_ids or ["signal_a", "signal_b"]
    source_urls = source_urls or ["https://example.com/evidence_a", "https://example.com/evidence_b"]
    source_types = ["github_issue", "hn"][: len(evidence_ids)]
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
        price_signal_ids=price_signal_ids or [],
        weak_pattern_ids=weak_pattern_ids or [],
        kill_warning_ids=kill_warning_ids or [],
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
