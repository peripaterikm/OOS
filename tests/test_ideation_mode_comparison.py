import unittest
from pathlib import Path

from oos.ideation_mode_comparison import (
    classify_score,
    compare_ideation_modes,
    compute_weighted_score,
    genericness_penalty_for_text,
)
from oos.ideation import DeterministicIdeationStub
from oos.models import OpportunityCard
from oos.pattern_guided_ideation import StaticPatternGuidedIdeationProvider, generate_pattern_guided_ideas
from tests.test_pattern_guided_ideation import idea_payload, make_opportunity, valid_payload


def pattern_ideas():
    result = generate_pattern_guided_ideas(
        opportunities=[make_opportunity()],
        provider=StaticPatternGuidedIdeationProvider(payload=valid_payload()),
    )
    return result.ideas


def legacy_opportunity() -> OpportunityCard:
    return OpportunityCard(
        id="opp_reporting_trust",
        title="Reporting trust",
        source_signal_ids=["sig_1", "sig_2"],
        pain_summary="Owners do not trust financial reports.",
        icp="SMB owner-operators",
        opportunity_type="workflow",
        why_it_matters="Trust gaps delay decisions.",
    )


def heuristic_ideas():
    metadata = {"linked_input_ids": ["sig_1", "sig_2"]}
    return [
        idea.__class__(**{**idea.__dict__, "ai_metadata": metadata})
        for idea in DeterministicIdeationStub().generate(legacy_opportunity())
    ]


class TestIdeationModeComparison(unittest.TestCase):
    def test_schema_validity_gate_works(self) -> None:
        invalid = dict(idea_payload("bad_schema", "SaaS / tool"), idea_title="")

        result = compare_ideation_modes(
            ideas_by_mode={"pattern_guided": [invalid]},
            valid_opportunity_ids=["opp_reporting_trust"],
            expected_signal_ids_by_opportunity={"opp_reporting_trust": ["sig_1", "sig_2"]},
        )

        self.assertFalse(result.scores[0].schema_valid)
        self.assertEqual(result.scores[0].recommendation, "auto_park")

    def test_traceability_gate_works(self) -> None:
        invalid = dict(idea_payload("bad_trace", "SaaS / tool"), linked_signal_ids=["sig_unknown"])

        result = compare_ideation_modes(
            ideas_by_mode={"pattern_guided": [invalid]},
            valid_opportunity_ids=["opp_reporting_trust"],
            expected_signal_ids_by_opportunity={"opp_reporting_trust": ["sig_1", "sig_2"]},
        )

        self.assertFalse(result.scores[0].traceability_valid)
        self.assertEqual(result.scores[0].recommendation, "auto_park")

    def test_weighted_score_is_computed_correctly(self) -> None:
        score = compute_weighted_score(
            relevance_to_pain=3,
            novelty=2,
            commercial_usefulness=3,
            founder_fit=2,
            testability=3,
            automation_potential=2,
            hallucination_risk=1,
            genericness_penalty=-1,
        )

        self.assertEqual(score, 21)

    def test_preliminary_thresholds_classify_ideas_correctly(self) -> None:
        self.assertEqual(classify_score(12), "candidate_for_council_review")
        self.assertEqual(classify_score(8), "park_low_priority")
        self.assertEqual(classify_score(7), "auto_park")

    def test_genericness_penalty_affects_score(self) -> None:
        self.assertEqual(genericness_penalty_for_text("A generic dashboard and generic assistant"), -2)

        result = compare_ideation_modes(
            ideas_by_mode={"llm_assisted": [dict(idea_payload("generic", "SaaS / tool"), product_concept="Generic dashboard assistant")]},
            valid_opportunity_ids=["opp_reporting_trust"],
            expected_signal_ids_by_opportunity={"opp_reporting_trust": ["sig_1", "sig_2"]},
            criterion_scores_by_idea_id={"generic": {"genericness_penalty": -2}},
        )

        self.assertEqual(result.scores[0].genericness_penalty, -2)

    def test_mode_summary_is_created(self) -> None:
        result = compare_ideation_modes(
            ideas_by_mode={"heuristic_baseline": heuristic_ideas(), "pattern_guided": pattern_ideas()},
            valid_opportunity_ids=["opp_reporting_trust"],
            expected_signal_ids_by_opportunity={"opp_reporting_trust": ["sig_1", "sig_2"]},
        )

        self.assertEqual({summary.mode for summary in result.mode_summaries}, {"heuristic_baseline", "pattern_guided"})
        self.assertTrue(all(summary.idea_count > 0 for summary in result.mode_summaries))

    def test_recommendation_is_explainable(self) -> None:
        result = compare_ideation_modes(
            ideas_by_mode={"heuristic_baseline": heuristic_ideas(), "pattern_guided": pattern_ideas()},
            valid_opportunity_ids=["opp_reporting_trust"],
            expected_signal_ids_by_opportunity={"opp_reporting_trust": ["sig_1", "sig_2"]},
        )

        self.assertIn(result.recommendation.preferred_mode, {"heuristic_baseline", "pattern_guided"})
        self.assertTrue(result.recommendation.explanation)

    def test_invalid_idea_does_not_crash_full_comparison(self) -> None:
        result = compare_ideation_modes(
            ideas_by_mode={"pattern_guided": [idea_payload("valid", "SaaS / tool"), {"idea_id": "broken"}]},
            valid_opportunity_ids=["opp_reporting_trust"],
            expected_signal_ids_by_opportunity={"opp_reporting_trust": ["sig_1", "sig_2"]},
        )

        self.assertEqual(len(result.scores), 2)
        self.assertEqual(result.scores[1].recommendation, "auto_park")

    def test_no_live_llm_call_is_made(self) -> None:
        source = Path("src/oos/ideation_mode_comparison.py").read_text(encoding="utf-8")

        for forbidden in ["OpenAI(", "Anthropic(", "requests.post", "httpx.post", "chat.completions", "responses.create"]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
