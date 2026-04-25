import unittest
from dataclasses import asdict, replace

from oos.opportunity_quality_gate import (
    OPPORTUNITY_GATE_STATUSES,
    OpportunityGateDecision,
    evaluate_opportunity_batch,
)
from oos.opportunity_framing import StaticOpportunityFramingProvider, frame_opportunities
from tests.test_opportunity_framing import make_cluster, valid_opportunity
from tests.test_semantic_clustering import make_signal


def make_opportunity(**overrides):
    payload = valid_opportunity(**overrides)
    result = frame_opportunities(
        clusters=[make_cluster()],
        signals=[make_signal("sig_1"), make_signal("sig_2")],
        provider=StaticOpportunityFramingProvider(payload={"opportunities": [payload]}),
    )
    return result.opportunities[0]


class TestOpportunityQualityGate(unittest.TestCase):
    def test_strong_opportunity_with_clear_user_pain_evidence_wedge_passes(self) -> None:
        opportunity = make_opportunity()

        result = evaluate_opportunity_batch([opportunity])

        self.assertEqual(result.stage_status, "success")
        self.assertEqual(result.decisions[0].status, "pass")
        self.assertIn("Pass to pattern-guided ideation", result.decisions[0].recommendation)

    def test_opportunity_missing_evidence_is_parked_or_rejected(self) -> None:
        opportunity = make_opportunity(evidence=[])

        result = evaluate_opportunity_batch([opportunity])

        self.assertIn(result.decisions[0].status, {"park", "reject"})
        self.assertIn("evidence", result.decisions[0].missing_fields)
        self.assertIn("linked evidence is missing", result.decisions[0].weaknesses)

    def test_opportunity_missing_target_user_or_pain_is_rejected(self) -> None:
        missing_user = replace(make_opportunity(), target_user="")
        missing_pain = replace(make_opportunity(), pain="")

        result = evaluate_opportunity_batch([missing_user, missing_pain])

        self.assertEqual([decision.status for decision in result.decisions], ["reject", "reject"])
        self.assertIn("target_user", result.decisions[0].missing_fields)
        self.assertIn("pain", result.decisions[1].missing_fields)

    def test_opportunity_missing_product_angle_wedge_is_parked(self) -> None:
        opportunity = replace(make_opportunity(), possible_wedge="")

        result = evaluate_opportunity_batch([opportunity])

        self.assertEqual(result.decisions[0].status, "park")
        self.assertIn("possible_wedge", result.decisions[0].missing_fields)

    def test_opportunity_missing_risks_or_uncertainty_gets_parked_warning(self) -> None:
        opportunity = replace(make_opportunity(), risks=[], assumptions=[])

        result = evaluate_opportunity_batch([opportunity])

        decision = result.decisions[0]
        self.assertEqual(decision.status, "park")
        self.assertIn("risks_uncertainty", decision.missing_fields)
        self.assertTrue(any(item.criterion == "risks_uncertainty" and item.severity == "warning" for item in decision.criteria_results))

    def test_statuses_are_limited_to_pass_park_reject(self) -> None:
        opportunity = make_opportunity()
        decision = evaluate_opportunity_batch([opportunity]).decisions[0]

        self.assertIn(decision.status, OPPORTUNITY_GATE_STATUSES)
        bad_decision = OpportunityGateDecision(
            opportunity_id="opp_bad",
            status="maybe",
            explanation="Invalid status.",
            criteria_results=[],
            missing_fields=[],
            weaknesses=[],
            recommendation="Do not use.",
            next_action="Repair status.",
            confidence=0.1,
            linked_signal_ids=["sig_1"],
            linked_cluster_id="cluster_ops",
            source_opportunity_id="opp_bad",
            source_signal_ids=["sig_1"],
            source_cluster_id="cluster_ops",
        )
        with self.assertRaisesRegex(ValueError, "status must be pass, park, or reject"):
            bad_decision.validate()

    def test_linked_signal_ids_and_cluster_id_are_preserved(self) -> None:
        opportunity = make_opportunity()

        decision = evaluate_opportunity_batch([opportunity]).decisions[0]

        self.assertEqual(decision.linked_signal_ids, opportunity.linked_signal_ids)
        self.assertEqual(decision.source_signal_ids, opportunity.linked_signal_ids)
        self.assertEqual(decision.linked_cluster_id, opportunity.linked_cluster_id)
        self.assertEqual(decision.source_cluster_id, opportunity.linked_cluster_id)

    def test_invalid_opportunity_does_not_crash_full_batch(self) -> None:
        valid = make_opportunity()
        invalid = replace(make_opportunity(), opportunity_id="", linked_signal_ids=[])

        result = evaluate_opportunity_batch([valid, invalid])

        self.assertEqual(len(result.decisions), 2)
        self.assertEqual(result.decisions[0].status, "pass")
        self.assertEqual(result.decisions[1].status, "reject")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.stage_status, "degraded")

    def test_original_opportunity_card_is_not_mutated(self) -> None:
        opportunity = make_opportunity()
        before = asdict(opportunity)

        evaluate_opportunity_batch([opportunity])

        self.assertEqual(asdict(opportunity), before)

    def test_founder_override_field_is_optional_and_does_not_replace_gate_status(self) -> None:
        opportunity = make_opportunity()

        decision = evaluate_opportunity_batch([opportunity]).decisions[0]

        self.assertEqual(decision.status, "pass")
        self.assertIsNone(decision.founder_override_status)

    def test_deterministic_gate_metadata_is_present(self) -> None:
        opportunity = make_opportunity()

        result = evaluate_opportunity_batch([opportunity])

        self.assertEqual(result.ai_metadata["generation_mode"], "deterministic_gate")
        self.assertEqual(result.decisions[0].ai_metadata["generation_mode"], "deterministic_gate")


if __name__ == "__main__":
    unittest.main()
