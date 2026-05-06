import json
import unittest
from pathlib import Path

from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    FounderDecisionReason,
    allowed_reasons_for_decision,
    create_founder_decision,
    founder_decision_from_dict,
    founder_decision_taxonomy,
    founder_decision_to_dict,
    make_founder_decision_id,
    summarize_founder_decision,
)


class FounderDecisionTaxonomyTests(unittest.TestCase):
    def test_valid_promote_decision_with_promote_reason_passes(self):
        decision = self._decision(PROMOTE, ["strong_pain", "worth_interviews"])

        decision.validate()

        self.assertEqual(decision.decision, PROMOTE)
        self.assertFalse(decision.auto_promote)

    def test_valid_park_decision_with_park_reason_passes(self):
        decision = self._decision(PARK, ["weak_evidence"])

        decision.validate()

        self.assertEqual(decision.decision, PARK)

    def test_valid_kill_decision_with_kill_reason_passes(self):
        decision = self._decision(KILL, ["no_buyer"], notes="No buyer evidence after review.")

        decision.validate()

        self.assertEqual(decision.reasons[0].category, "no_buyer")

    def test_valid_revisit_later_decision_passes(self):
        decision = self._decision(REVISIT_LATER, ["waiting_for_more_signals"])

        decision.validate()

        self.assertEqual(decision.decision, REVISIT_LATER)

    def test_valid_needs_more_evidence_decision_passes(self):
        decision = self._decision(NEEDS_MORE_EVIDENCE, ["need_price_evidence"])

        decision.validate()

        self.assertEqual(decision.reasons[0].category, "need_price_evidence")

    def test_invalid_decision_value_is_rejected(self):
        with self.assertRaises(ValueError):
            self._decision("maybe", ["strong_pain"])

    def test_invalid_reason_for_decision_is_rejected(self):
        with self.assertRaises(ValueError):
            self._decision(PROMOTE, ["no_buyer"])

    def test_missing_reason_is_rejected_where_required(self):
        with self.assertRaises(ValueError):
            self._decision(KILL, [])

    def test_traceability_fields_preserve_evidence_signal_and_urls(self):
        decision = self._decision(
            PARK,
            ["weak_price_evidence"],
            linked_evidence_ids=["ev_2", "ev_1"],
            linked_source_signal_ids=["sig_2", "sig_1"],
            linked_source_urls=["https://example.com/b", "https://example.com/a"],
        )

        self.assertEqual(decision.linked_evidence_ids, ["ev_1", "ev_2"])
        self.assertEqual(decision.linked_source_signal_ids, ["sig_1", "sig_2"])
        self.assertEqual(decision.linked_source_urls, ["https://example.com/a", "https://example.com/b"])

    def test_serialization_round_trip_works(self):
        decision = self._decision(PROMOTE, ["clear_buyer"])
        payload = founder_decision_to_dict(decision)

        round_tripped = founder_decision_from_dict(json.loads(json.dumps(payload, sort_keys=True)))

        self.assertEqual(round_tripped, decision)

    def test_deterministic_decision_id_generation_or_explicit_id_works(self):
        first = self._decision(PROMOTE, ["strong_pain"])
        second = self._decision(PROMOTE, ["strong_pain"])
        explicit = self._decision(PROMOTE, ["strong_pain"], decision_id="fd_custom")

        self.assertEqual(first.decision_id, second.decision_id)
        self.assertEqual(explicit.decision_id, "fd_custom")
        self.assertEqual(
            first.decision_id,
            make_founder_decision_id(
                opportunity_id="opp_invoice",
                evidence_pack_id="pack_invoice",
                decision=PROMOTE,
                reasons=["strong_pain"],
            ),
        )

    def test_summary_is_deterministic(self):
        decision = self._decision(
            NEEDS_MORE_EVIDENCE,
            [FounderDecisionReason("need_buyer_clarity"), FounderDecisionReason("need_customer_voice")],
        )

        first = summarize_founder_decision(decision)
        second = summarize_founder_decision(decision)

        self.assertEqual(first, second)
        self.assertIn("needs_more_evidence", first)
        self.assertIn("need_buyer_clarity, need_customer_voice", first)

    def test_taxonomy_lists_all_decisions_and_reason_sets(self):
        taxonomy = founder_decision_taxonomy().to_dict()

        self.assertEqual(taxonomy["schema_version"], "founder_decision_v2.v1")
        self.assertEqual(taxonomy["decisions"], [PROMOTE, PARK, KILL, REVISIT_LATER, NEEDS_MORE_EVIDENCE])
        self.assertIn("vendor_promo_false_positive", allowed_reasons_for_decision(KILL))
        self.assertIn("need_non_vendor_source", allowed_reasons_for_decision(NEEDS_MORE_EVIDENCE))

    def test_no_live_network_or_llm_calls_are_present(self):
        source = Path("src/oos/founder_decision_taxonomy.py").read_text(encoding="utf-8")

        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("complete(", source)

    def _decision(
        self,
        decision: str,
        reasons: list[str | FounderDecisionReason],
        *,
        notes: str = "Founder review note.",
        linked_evidence_ids: list[str] | None = None,
        linked_source_signal_ids: list[str] | None = None,
        linked_source_urls: list[str] | None = None,
        decision_id: str | None = None,
    ):
        return create_founder_decision(
            opportunity_id="opp_invoice",
            evidence_pack_id="pack_invoice",
            decision=decision,
            reasons=reasons,
            notes=notes,
            confidence=0.72,
            linked_evidence_ids=linked_evidence_ids or ["raw_hn_47082761"],
            linked_source_signal_ids=linked_source_signal_ids or ["sig_invoice"],
            linked_source_urls=linked_source_urls or ["https://news.ycombinator.com/item?id=47082761"],
            decided_by="founder",
            decided_at="2026-05-06T00:00:00Z",
            decision_id=decision_id,
        )


if __name__ == "__main__":
    unittest.main()
