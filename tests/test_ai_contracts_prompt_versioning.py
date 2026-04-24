import unittest

from oos.ai_contracts import (
    AIArtifactMetadata,
    AIBudgetMode,
    AI_METADATA_REQUIRED_FIELDS,
    AIStageStatus,
    LLMCallBudget,
    PromptIdentity,
    build_ai_metadata,
    build_cache_key,
    compute_input_hash,
)
from oos.ideation import AIIdeationProvider, build_ideation_engine
from oos.models import IdeationGenerationMode, OpportunityCard


class SuccessfulProvider(AIIdeationProvider):
    def generate(self, opportunity: OpportunityCard) -> list[dict]:
        return [
            {
                "id": "idea_contract_ai",
                "short_concept": "AI-assisted exception workflow mapper",
                "business_model": "subscription",
                "standardization_focus": "repeatable exception workflow template",
                "ai_leverage": "summarize recurring exception evidence",
                "external_execution_needed": "none",
                "rough_monetization_model": "monthly subscription",
            }
        ]


def make_opportunity() -> OpportunityCard:
    return OpportunityCard(
        id="opp_contract",
        title="Manual exception workflow",
        source_signal_ids=["sig_contract_1", "sig_contract_2"],
        pain_summary="Manual exception handling creates repeated customer risk",
        icp="ops lead",
        opportunity_type="workflow_exception_handling",
        why_it_matters="Recurring manual workaround with measurable delay.",
    )


class TestAIContractsPromptVersioning(unittest.TestCase):
    def test_common_ai_metadata_can_be_created_and_serialized(self) -> None:
        metadata = build_ai_metadata(
            prompt=PromptIdentity(prompt_name="ideation_constrained", prompt_version="ideation_constrained_v1"),
            model_id="test-model",
            input_payload={"b": 2, "a": 1},
            generation_mode=IdeationGenerationMode.llm_assisted.value,
            linked_input_ids=["sig_1"],
            fallback_used=False,
            stage_confidence=0.9,
            stage_status=AIStageStatus.success,
            timeout_seconds=60,
        )

        payload = metadata.to_dict()

        for field in AI_METADATA_REQUIRED_FIELDS:
            self.assertIn(field, payload)
        self.assertEqual(payload["prompt_name"], "ideation_constrained")
        self.assertEqual(payload["prompt_version"], "ideation_constrained_v1")
        self.assertEqual(payload["timeout_seconds"], 60)

    def test_metadata_rejects_missing_required_identity(self) -> None:
        metadata = AIArtifactMetadata(
            prompt_name="",
            prompt_version="prompt_v1",
            model_id="model",
            input_hash=compute_input_hash({"x": 1}),
            generation_mode=IdeationGenerationMode.llm_assisted.value,
            linked_input_ids=["sig_1"],
            fallback_used=False,
            stage_confidence=1.0,
            stage_status=AIStageStatus.success.value,
        )

        with self.assertRaises(ValueError):
            metadata.to_dict()

    def test_input_hash_is_deterministic_for_normalized_input(self) -> None:
        first = compute_input_hash({"z": [3, 2, 1], "a": {"b": True}})
        second = compute_input_hash({"a": {"b": True}, "z": [3, 2, 1]})

        self.assertEqual(first, second)

    def test_cache_key_uses_input_hash_prompt_version_and_model_id(self) -> None:
        input_hash = compute_input_hash({"signal": "pain"})

        cache_key = build_cache_key(
            input_hash=input_hash,
            prompt_version="signal_extractor_v1",
            model_id="model-a",
        )

        self.assertEqual(cache_key, f"{input_hash}:signal_extractor_v1:model-a")

    def test_prompt_version_identity_is_explicit(self) -> None:
        prompt_v1 = PromptIdentity(prompt_name="signal_extractor", prompt_version="signal_extractor_v1")
        prompt_v2 = PromptIdentity(prompt_name="signal_extractor", prompt_version="signal_extractor_v2")

        self.assertNotEqual(prompt_v1.to_dict()["prompt_version"], prompt_v2.to_dict()["prompt_version"])

    def test_budget_warning_thresholds_work(self) -> None:
        self.assertFalse(LLMCallBudget(mode=AIBudgetMode.economy, expected_calls=12, actual_calls=12).warning_triggered)
        self.assertTrue(LLMCallBudget(mode=AIBudgetMode.economy, expected_calls=12, actual_calls=13).warning_triggered)
        self.assertTrue(LLMCallBudget(mode=AIBudgetMode.standard, expected_calls=25, actual_calls=26).warning_triggered)
        self.assertTrue(LLMCallBudget(mode=AIBudgetMode.deep, expected_calls=40, actual_calls=41).warning_triggered)

    def test_ai_assisted_ideation_artifact_can_carry_common_metadata(self) -> None:
        engine = build_ideation_engine(store=None, ai_enabled=True, provider=SuccessfulProvider())

        ideas = engine.generate(make_opportunity())

        self.assertEqual(len(ideas), 1)
        self.assertIsNotNone(ideas[0].ai_metadata)
        payload = ideas[0].ai_metadata or {}
        for field in AI_METADATA_REQUIRED_FIELDS:
            self.assertIn(field, payload)
        self.assertEqual(payload["generation_mode"], IdeationGenerationMode.llm_assisted.value)
        self.assertEqual(payload["prompt_version"], "ideation_constrained_v1")


if __name__ == "__main__":
    unittest.main()
