import unittest

from oos.models import IdeationGenerationMode
from oos.opportunity_framing import StaticOpportunityFramingProvider, frame_opportunities
from oos.pattern_guided_ideation import (
    PRODUCT_PATTERNS,
    PatternGuidedIdeationProvider,
    StaticPatternGuidedIdeationProvider,
    generate_pattern_guided_ideas,
)
from tests.test_opportunity_framing import make_cluster, valid_opportunity
from tests.test_semantic_clustering import make_signal


def make_opportunity():
    result = frame_opportunities(
        clusters=[make_cluster()],
        signals=[make_signal("sig_1"), make_signal("sig_2")],
        provider=StaticOpportunityFramingProvider(payload={"opportunities": [valid_opportunity()]}),
    )
    return result.opportunities[0]


def idea_payload(idea_id: str, pattern: str, **overrides: object) -> dict:
    payload = {
        "idea_id": idea_id,
        "idea_title": f"{pattern} idea",
        "target_user": "SMB owner-operators",
        "pain_addressed": "Owners do not trust financial reports.",
        "product_concept": f"A {pattern} concept for reconciliation narratives.",
        "wedge": "Start with weekly reconciliation narratives.",
        "why_now": "Weekly reporting creates repeated urgency.",
        "business_model_options": ["monthly subscription"],
        "first_experiment": "Run 5 user interviews and test a concierge prototype.",
        "key_assumptions": ["Owners will pay for trust restoration."],
        "risks": ["May be perceived as bookkeeping services."],
        "selected_product_pattern": pattern,
        "linked_opportunity_id": "opp_reporting_trust",
        "linked_signal_ids": ["sig_1", "sig_2"],
        "confidence": 0.82,
    }
    payload.update(overrides)
    return payload


def valid_payload() -> dict:
    return {
        "ideas": [
            idea_payload("idea_saas", "SaaS / tool"),
            idea_payload("idea_service", "service-assisted workflow"),
            idea_payload("idea_radar", "audit / risk radar"),
        ]
    }


class RecordingProvider(PatternGuidedIdeationProvider):
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = 0
        self.seen_pattern_names: list[list[str]] = []
        self.seen_opportunity_ids: list[list[str]] = []

    def generate(self, *, opportunities, product_patterns):
        self.calls += 1
        self.seen_opportunity_ids.append([opportunity.opportunity_id for opportunity in opportunities])
        self.seen_pattern_names.append([pattern.name for pattern in product_patterns])
        return self.payload


class TestPatternGuidedIdeation(unittest.TestCase):
    def test_product_pattern_library_contains_required_patterns(self) -> None:
        names = {pattern.name for pattern in PRODUCT_PATTERNS}

        self.assertTrue(
            {
                "SaaS / tool",
                "service-assisted workflow",
                "data product",
                "marketplace / brokered workflow",
                "internal automation product",
                "audit / risk radar",
                "expert-in-the-loop workflow",
            }.issubset(names)
        )

    def test_valid_provider_response_creates_3_to_5_structured_ideas(self) -> None:
        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(payload=valid_payload()),
        )

        self.assertFalse(result.fallback_used)
        self.assertEqual(result.stage_status, "success")
        self.assertGreaterEqual(len(result.ideas), 3)
        self.assertLessEqual(len(result.ideas), 5)

    def test_each_idea_has_required_fields(self) -> None:
        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(payload=valid_payload()),
        )

        for idea in result.ideas:
            self.assertTrue(idea.idea_title)
            self.assertTrue(idea.target_user)
            self.assertTrue(idea.pain_addressed)
            self.assertTrue(idea.product_concept)
            self.assertTrue(idea.first_experiment)
            self.assertTrue(idea.business_model_options)
            self.assertTrue(idea.key_assumptions)
            self.assertTrue(idea.risks)

    def test_selected_product_pattern_is_valid(self) -> None:
        valid_pattern_names = {pattern.name for pattern in PRODUCT_PATTERNS}

        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(payload=valid_payload()),
        )

        self.assertTrue(all(idea.selected_product_pattern in valid_pattern_names for idea in result.ideas))

    def test_idea_variants_preserve_opportunity_id_and_signal_ids(self) -> None:
        opportunity = make_opportunity()

        result = generate_pattern_guided_ideas(
            opportunities=[opportunity],
            provider=StaticPatternGuidedIdeationProvider(payload=valid_payload()),
        )

        self.assertTrue(all(idea.linked_opportunity_id == opportunity.opportunity_id for idea in result.ideas))
        self.assertTrue(all(idea.linked_signal_ids == opportunity.linked_signal_ids for idea in result.ideas))

    def test_invalid_provider_item_is_rejected_safely(self) -> None:
        payload = valid_payload()
        payload["ideas"].append(idea_payload("idea_bad", "not a real pattern"))

        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(payload=payload),
        )

        self.assertTrue(result.fallback_used)
        self.assertEqual(len(result.rejected_record_errors), 1)
        self.assertNotIn("idea_bad", [idea.idea_id for idea in result.ideas])

    def test_fewer_than_2_distinct_product_patterns_triggers_low_diversity_warning(self) -> None:
        payload = {
            "ideas": [
                idea_payload("idea_1", "SaaS / tool"),
                idea_payload("idea_2", "SaaS / tool"),
                idea_payload("idea_3", "SaaS / tool"),
            ]
        }

        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(payload=payload),
        )

        self.assertTrue(result.low_diversity_warning)
        self.assertTrue(result.fallback_used)
        self.assertGreaterEqual(len({idea.selected_product_pattern for idea in result.ideas}), 2)

    def test_fallback_ideas_are_labeled_clearly(self) -> None:
        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(payload={"ideas": []}),
        )

        self.assertTrue(result.fallback_used)
        self.assertTrue(result.low_diversity_warning)
        self.assertTrue(result.ideas)
        self.assertTrue(
            all(
                idea.generation_mode == IdeationGenerationMode.heuristic_fallback_after_llm_failure.value
                for idea in result.ideas
            )
        )

    def test_ai_metadata_is_present(self) -> None:
        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(payload=valid_payload()),
        )

        for field in [
            "prompt_name",
            "prompt_version",
            "model_id",
            "input_hash",
            "generation_mode",
            "created_at",
            "linked_input_ids",
            "fallback_used",
            "stage_confidence",
            "stage_status",
        ]:
            self.assertIn(field, result.ai_metadata)
            self.assertIn(field, result.ideas[0].ai_metadata)

    def test_no_live_llm_call_is_made(self) -> None:
        provider = RecordingProvider(payload=valid_payload())

        result = generate_pattern_guided_ideas(opportunities=[make_opportunity()], provider=provider)

        self.assertEqual(provider.calls, 1)
        self.assertEqual(provider.seen_opportunity_ids, [["opp_reporting_trust"]])
        self.assertIn("SaaS / tool", provider.seen_pattern_names[0])
        self.assertFalse(result.fallback_used)


if __name__ == "__main__":
    unittest.main()
