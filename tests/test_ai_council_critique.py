from __future__ import annotations

import inspect
import unittest

from oos import ai_council_critique
from oos.ai_council_critique import (
    COUNCIL_ROLES,
    CouncilRoleProvider,
    StaticCouncilRoleProvider,
    run_isolated_council_critique,
    select_top_ideas_for_council,
)
from oos.ideation_mode_comparison import IdeaEvaluationScore


def _score(
    idea_id: str,
    *,
    total_score: int = 13,
    opportunity_id: str = "opp-1",
    signal_ids: list[str] | None = None,
) -> IdeaEvaluationScore:
    return IdeaEvaluationScore(
        idea_id=idea_id,
        mode="pattern_guided",
        schema_valid=True,
        traceability_valid=True,
        relevance_to_pain=3,
        novelty=2,
        commercial_usefulness=3,
        founder_fit=3,
        testability=2,
        automation_potential=2,
        hallucination_risk=1,
        genericness_penalty=0,
        total_score=total_score,
        recommendation="candidate_for_council_review" if total_score >= 12 else "park_low_priority",
        explanation="candidate_for_council_review: weighted score for council test",
        linked_signal_ids=signal_ids or ["sig-1", "sig-2"],
        linked_opportunity_id=opportunity_id,
        validation_errors=[],
    )


def _idea(idea_id: str, opportunity_id: str = "opp-1") -> dict:
    return {
        "idea_id": idea_id,
        "idea_title": f"Test idea {idea_id}",
        "linked_opportunity_id": opportunity_id,
        "linked_signal_ids": ["sig-1", "sig-2"],
    }


def _payload(
    *,
    role: str,
    idea_id: str = "idea-1",
    recommendation: str = "test now",
    risks: list[str] | None = None,
    kill_candidates: list[str] | None = None,
    unsupported_claims: list[str] | None = None,
) -> dict:
    return {
        "role": role,
        "idea_id": idea_id,
        "risks": risks if risks is not None else ["Buyer may not prioritize this workflow"],
        "kill_candidates": kill_candidates if kill_candidates is not None else [],
        "unsupported_claims": unsupported_claims if unsupported_claims is not None else [],
        "weakest_assumption": "The buyer will pay before a full automation exists.",
        "recommendation": recommendation,
        "explanation": "Role-specific critique is isolated and traceable.",
        "confidence": 0.74,
        "linked_signal_ids": ["sig-1", "sig-2"],
        "linked_opportunity_id": "opp-1",
    }


class RecordingProvider(CouncilRoleProvider):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def critique(self, *, role, idea):
        self.calls.append(role.role_id)
        return _payload(role=role.role_id)


class TestAICouncilCritique(unittest.TestCase):
    def test_top_idea_selection_respects_score_threshold(self) -> None:
        scores = [_score("low", total_score=9), _score("high", total_score=14)]

        selected = select_top_ideas_for_council(scores)

        self.assertEqual(["high"], [score.idea_id for score in selected])

    def test_standard_mode_max_3_ideas_per_opportunity(self) -> None:
        scores = [_score(f"idea-{index}", total_score=15 - index) for index in range(5)]

        selected = select_top_ideas_for_council(scores)

        self.assertEqual(3, len(selected))
        self.assertEqual(["idea-0", "idea-1", "idea-2"], [score.idea_id for score in selected])

    def test_each_council_role_output_is_isolated(self) -> None:
        provider = RecordingProvider()
        providers = {role.role_id: provider for role in COUNCIL_ROLES}

        result = run_isolated_council_critique(
            ideas=[_idea("idea-1")],
            scores=[_score("idea-1")],
            providers_by_role=providers,
        )

        self.assertEqual([role.role_id for role in COUNCIL_ROLES], provider.calls)
        self.assertEqual(len(COUNCIL_ROLES), len(result.critiques))
        self.assertFalse(result.critique_unavailable)

    def test_structured_critique_is_validated(self) -> None:
        providers = {
            role.role_id: StaticCouncilRoleProvider({role.role_id: _payload(role=role.role_id)})
            for role in COUNCIL_ROLES
        }

        result = run_isolated_council_critique(
            ideas=[_idea("idea-1")],
            scores=[_score("idea-1")],
            providers_by_role=providers,
        )

        critique = result.critiques[0]
        self.assertEqual("idea-1", critique.idea_id)
        self.assertEqual(["sig-1", "sig-2"], critique.linked_signal_ids)
        self.assertIn(critique.recommendation, {"kill", "park", "test now", "needs more evidence"})
        self.assertIn("prompt_name", critique.ai_metadata)

    def test_missing_or_invalid_role_output_triggers_critique_unavailable(self) -> None:
        providers = {
            COUNCIL_ROLES[0].role_id: StaticCouncilRoleProvider(
                {COUNCIL_ROLES[0].role_id: {**_payload(role=COUNCIL_ROLES[0].role_id), "recommendation": "unknown"}}
            )
        }

        result = run_isolated_council_critique(
            ideas=[_idea("idea-1")],
            scores=[_score("idea-1")],
            providers_by_role=providers,
        )

        self.assertTrue(result.critique_unavailable)
        self.assertTrue(result.summaries[0].critique_unavailable)
        self.assertTrue(result.summaries[0].recommendation.requires_founder_manual_review)

    def test_unsupported_claims_are_captured(self) -> None:
        providers = {
            role.role_id: StaticCouncilRoleProvider(
                {role.role_id: _payload(role=role.role_id, unsupported_claims=["Claims buyer has budget without evidence"])}
            )
            for role in COUNCIL_ROLES
        }

        result = run_isolated_council_critique(
            ideas=[_idea("idea-1")],
            scores=[_score("idea-1")],
            providers_by_role=providers,
        )

        self.assertGreater(result.summaries[0].unsupported_claim_count, 0)

    def test_suspiciously_clean_true_when_no_role_finds_serious_risk(self) -> None:
        providers = {
            role.role_id: StaticCouncilRoleProvider(
                {
                    role.role_id: _payload(
                        role=role.role_id,
                        recommendation="test now",
                        risks=["Minor calibration risk"],
                        kill_candidates=[],
                    )
                }
            )
            for role in COUNCIL_ROLES
        }

        result = run_isolated_council_critique(
            ideas=[_idea("idea-1")],
            scores=[_score("idea-1")],
            providers_by_role=providers,
        )

        self.assertTrue(result.summaries[0].suspiciously_clean)
        self.assertTrue(result.summaries[0].recommendation.requires_founder_manual_review)

    def test_founder_decision_authority_is_not_replaced(self) -> None:
        providers = {
            role.role_id: StaticCouncilRoleProvider({role.role_id: _payload(role=role.role_id)})
            for role in COUNCIL_ROLES
        }

        result = run_isolated_council_critique(
            ideas=[_idea("idea-1")],
            scores=[_score("idea-1")],
            providers_by_role=providers,
        )

        self.assertTrue(result.founder_final_authority)
        self.assertTrue(result.summaries[0].recommendation.founder_final_authority)

    def test_no_live_llm_api_call_is_made(self) -> None:
        source = inspect.getsource(ai_council_critique)

        for token in ("OpenAI(", "Anthropic(", "requests.post", "httpx.post", "chat.completions", "responses.create"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
