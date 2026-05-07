import json
from pathlib import Path
import unittest

from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    create_founder_decision,
)
from oos.founder_feedback_mapping import (
    BUYER_UNCLEAR,
    GENERIC_FALSE_POSITIVE,
    NEEDS_MORE_EVIDENCE_IMPACT,
    POSITIVE,
    PRICE_EVIDENCE_MISSING,
    REQUIRE_BUYER_CLARITY,
    REQUIRE_PRICE_EVIDENCE,
    REVISIT_PATTERN,
    STRONG_PAIN_CONFIRMED,
    SUPPRESS_PATTERN,
    VENDOR_PROMO_FALSE_POSITIVE,
    founder_feedback_mapping_from_dict,
    founder_feedback_mapping_to_dict,
    map_founder_decision_to_feedback,
    summarize_founder_feedback_mapping,
    validate_founder_feedback_mapping,
)


class FounderFeedbackMappingTests(unittest.TestCase):
    def _decision(self, decision: str, reasons: list[str]):
        return create_founder_decision(
            opportunity_id="opp_cash_collection",
            evidence_pack_id="evidence_pack_cash_collection",
            decision=decision,
            reasons=reasons,
            linked_evidence_ids=["ev_2", "ev_1"],
            linked_source_signal_ids=["sig_2", "sig_1"],
            linked_source_urls=["https://example.com/b", "https://example.com/a"],
            confidence=0.7,
            decided_by="founder",
            decided_at="2026-05-06T00:00:00Z",
        )

    def test_promote_maps_to_positive_impact(self):
        mapping = map_founder_decision_to_feedback(self._decision(PROMOTE, ["strong_pain"]))

        self.assertEqual(POSITIVE, mapping.signal_impact)
        self.assertIn("promoted_pattern", mapping.feedback_tags)

    def test_promote_strong_pain_creates_confirmed_tag(self):
        mapping = map_founder_decision_to_feedback(self._decision(PROMOTE, ["strong_pain"]))

        self.assertIn(STRONG_PAIN_CONFIRMED, mapping.feedback_tags)

    def test_park_unclear_buyer_creates_buyer_tag_and_handling(self):
        mapping = map_founder_decision_to_feedback(self._decision(PARK, ["unclear_buyer"]))

        self.assertEqual(NEEDS_MORE_EVIDENCE_IMPACT, mapping.signal_impact)
        self.assertIn(BUYER_UNCLEAR, mapping.feedback_tags)
        self.assertIn(REQUIRE_BUYER_CLARITY, mapping.recommended_future_handling)

    def test_park_weak_price_evidence_creates_price_tag(self):
        mapping = map_founder_decision_to_feedback(self._decision(PARK, ["weak_price_evidence"]))

        self.assertIn(PRICE_EVIDENCE_MISSING, mapping.feedback_tags)
        self.assertIn(REQUIRE_PRICE_EVIDENCE, mapping.recommended_future_handling)

    def test_kill_too_generic_creates_suppress_mapping(self):
        mapping = map_founder_decision_to_feedback(self._decision(KILL, ["too_generic"]))

        self.assertEqual(SUPPRESS_PATTERN, mapping.signal_impact)
        self.assertIn(GENERIC_FALSE_POSITIVE, mapping.feedback_tags)
        self.assertIn("suppress_similar_pattern", mapping.recommended_future_handling)

    def test_kill_vendor_promo_creates_vendor_tag(self):
        mapping = map_founder_decision_to_feedback(self._decision(KILL, ["vendor_promo_false_positive"]))

        self.assertEqual(SUPPRESS_PATTERN, mapping.signal_impact)
        self.assertIn(VENDOR_PROMO_FALSE_POSITIVE, mapping.feedback_tags)

    def test_needs_more_evidence_maps_to_needs_more_evidence(self):
        mapping = map_founder_decision_to_feedback(self._decision(NEEDS_MORE_EVIDENCE, ["need_price_evidence"]))

        self.assertEqual(NEEDS_MORE_EVIDENCE_IMPACT, mapping.signal_impact)
        self.assertIn(PRICE_EVIDENCE_MISSING, mapping.feedback_tags)

    def test_revisit_later_maps_to_revisit_pattern(self):
        mapping = map_founder_decision_to_feedback(
            self._decision(REVISIT_LATER, ["waiting_for_more_signals"]),
            cluster_id="cluster_cash_collection",
        )

        self.assertEqual(REVISIT_PATTERN, mapping.signal_impact)
        self.assertEqual("cluster_cash_collection", mapping.cluster_id)
        self.assertIn("revisit_on_new_evidence", mapping.feedback_tags)

    def test_traceability_fields_are_preserved(self):
        mapping = map_founder_decision_to_feedback(self._decision(PROMOTE, ["strong_pain"]))

        self.assertEqual(["ev_1", "ev_2"], mapping.evidence_ids)
        self.assertEqual(["sig_1", "sig_2"], mapping.source_signal_ids)
        self.assertEqual(["https://example.com/a", "https://example.com/b"], mapping.source_urls)
        self.assertEqual(mapping.evidence_ids, mapping.target.evidence_ids)
        self.assertEqual(mapping.source_signal_ids, mapping.target.source_signal_ids)
        self.assertEqual(mapping.source_urls, mapping.target.source_urls)

    def test_serialization_round_trip_works(self):
        mapping = map_founder_decision_to_feedback(self._decision(PROMOTE, ["strong_pain"]))
        data = founder_feedback_mapping_to_dict(mapping)
        json.dumps(data)

        restored = founder_feedback_mapping_from_dict(data)

        self.assertEqual(data, founder_feedback_mapping_to_dict(restored))

    def test_validation_rejects_missing_decision_id(self):
        mapping = map_founder_decision_to_feedback(self._decision(PROMOTE, ["strong_pain"]))
        data = founder_feedback_mapping_to_dict(mapping)
        data["decision_id"] = ""

        with self.assertRaises(ValueError):
            founder_feedback_mapping_from_dict(data)

    def test_validation_rejects_missing_traceability(self):
        mapping = map_founder_decision_to_feedback(self._decision(PROMOTE, ["strong_pain"]))
        data = founder_feedback_mapping_to_dict(mapping)
        data["evidence_ids"] = []
        data["target"]["evidence_ids"] = []

        with self.assertRaises(ValueError):
            founder_feedback_mapping_from_dict(data)

    def test_summary_is_deterministic(self):
        mapping = map_founder_decision_to_feedback(self._decision(PROMOTE, ["strong_pain"]))

        self.assertEqual(
            summarize_founder_feedback_mapping(mapping),
            summarize_founder_feedback_mapping(mapping),
        )
        self.assertIn("positive feedback", summarize_founder_feedback_mapping(mapping))

    def test_validation_result_serializes(self):
        mapping = map_founder_decision_to_feedback(self._decision(PROMOTE, ["strong_pain"]))
        result = validate_founder_feedback_mapping(mapping)

        self.assertTrue(result.is_valid)
        json.dumps(result.to_dict())

    def test_no_live_network_or_llm_calls_are_present(self):
        source = Path("src/oos/founder_feedback_mapping.py").read_text(encoding="utf-8")

        self.assertNotIn("provider.complete", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.request", source)


if __name__ == "__main__":
    unittest.main()
