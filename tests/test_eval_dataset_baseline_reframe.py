import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.artifact_store import ArtifactStore
from oos.evaluation_dataset import EVALUATION_DATASET_V0_DIR, load_evaluation_dataset_v0
from oos.ideation import AIIdeationProvider, build_ideation_engine
from oos.models import IdeationGenerationMode, OpportunityCard


class FailingProvider(AIIdeationProvider):
    def generate(self, opportunity: OpportunityCard) -> list[dict]:
        raise RuntimeError("LLM unavailable")


class SuccessfulProvider(AIIdeationProvider):
    def generate(self, opportunity: OpportunityCard) -> list[dict]:
        return [
            {
                "id": "idea_eval_llm",
                "short_concept": "LLM-assisted exception workflow control plane",
                "business_model": "subscription",
                "standardization_focus": "repeatable exception workflow templates",
                "ai_leverage": "summarize recurring exception patterns from linked evidence",
                "external_execution_needed": "none",
                "rough_monetization_model": "monthly subscription",
            }
        ]


def make_opportunity() -> OpportunityCard:
    return OpportunityCard(
        id="opp_eval_dataset",
        title="Exception workflow pain",
        source_signal_ids=["eval_v0_sig_001", "eval_v0_sig_002"],
        pain_summary="Manual exception workflows create repeated delays",
        icp="ops lead",
        opportunity_type="workflow_exception_handling",
        why_it_matters="Recurring manual workaround with operational cost.",
    )


class TestEvaluationDatasetBaselineReframe(unittest.TestCase):
    def test_evaluation_dataset_v0_exists_and_loads(self) -> None:
        self.assertTrue(EVALUATION_DATASET_V0_DIR.exists())

        signals = load_evaluation_dataset_v0()

        self.assertGreaterEqual(len(signals), 15)
        self.assertTrue(all("signal_id" in signal for signal in signals))

    def test_synthetic_signals_are_explicitly_labeled(self) -> None:
        signals = load_evaluation_dataset_v0()
        synthetic_signals = [signal for signal in signals if signal.get("synthetic") is True]

        self.assertEqual(len(synthetic_signals), len(signals))

    def test_required_edge_cases_exist(self) -> None:
        signals = load_evaluation_dataset_v0()
        tags = [tag for signal in signals for tag in signal.get("edge_case_tags", [])]

        self.assertGreaterEqual(tags.count("ambiguous"), 2)
        self.assertIn("near_duplicate", tags)
        self.assertIn("weak_noisy", tags)
        self.assertTrue({"unclear_buyer", "unclear_pain"} & set(tags))

    def test_expected_notes_files_exist(self) -> None:
        self.assertTrue((EVALUATION_DATASET_V0_DIR / "expected_clusters.md").exists())
        self.assertTrue((EVALUATION_DATASET_V0_DIR / "expected_opportunities.md").exists())
        self.assertTrue((EVALUATION_DATASET_V0_DIR / "founder_quality_notes.md").exists())

    def test_heuristic_idea_artifacts_include_generation_mode(self) -> None:
        with TemporaryDirectory() as tmp:
            store = ArtifactStore(root_dir=Path(tmp))
            engine = build_ideation_engine(store=store, ai_enabled=False)

            ideas = engine.generate(make_opportunity())

            self.assertGreaterEqual(len(ideas), 1)
            for idea in ideas:
                path = Path(tmp) / "ideas" / f"{idea.id}.json"
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["generation_mode"], IdeationGenerationMode.heuristic_baseline.value)

    def test_generation_mode_values_are_allowed(self) -> None:
        allowed = {mode.value for mode in IdeationGenerationMode}

        with TemporaryDirectory() as tmp:
            baseline = build_ideation_engine(store=ArtifactStore(root_dir=Path(tmp) / "baseline"), ai_enabled=False)
            assisted = build_ideation_engine(
                store=ArtifactStore(root_dir=Path(tmp) / "assisted"),
                ai_enabled=True,
                provider=SuccessfulProvider(),
            )
            fallback = build_ideation_engine(
                store=ArtifactStore(root_dir=Path(tmp) / "fallback"),
                ai_enabled=True,
                provider=FailingProvider(),
            )

            ideas = []
            ideas.extend(baseline.generate(make_opportunity()))
            ideas.extend(assisted.generate(make_opportunity()))
            ideas.extend(fallback.generate(make_opportunity()))

            self.assertGreaterEqual(len(ideas), 4)
            for idea in ideas:
                self.assertIn(idea.generation_mode.value, allowed)

            observed = {idea.generation_mode.value for idea in ideas}
            self.assertIn(IdeationGenerationMode.heuristic_baseline.value, observed)
            self.assertIn(IdeationGenerationMode.llm_assisted.value, observed)
            self.assertIn(IdeationGenerationMode.heuristic_fallback_after_llm_failure.value, observed)


if __name__ == "__main__":
    unittest.main()
