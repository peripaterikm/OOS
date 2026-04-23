import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from oos.cli import main
from oos.config import OOSConfig
from oos.ideation import AIIdeationProvider, build_ideation_engine
from oos.models import OpportunityCard
from oos.orchestrator import Orchestrator


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "examples" / "real_signal_batch.jsonl"


class SuccessfulProvider(AIIdeationProvider):
    def generate(self, opportunity: OpportunityCard) -> list[dict]:
        return [
            {
                "id": "idea_ai_success",
                "short_concept": f"AI-assisted workflow mapper for {opportunity.icp}",
                "business_model": "subscription",
                "standardization_focus": "repeatable workflow templates and fixed intake schema",
                "ai_leverage": "AI-assisted clustering of workflow breakdowns",
                "external_execution_needed": "none",
                "rough_monetization_model": "monthly subscription",
            }
        ]


class FailingProvider(AIIdeationProvider):
    def generate(self, opportunity: OpportunityCard) -> list[dict]:
        raise RuntimeError("AI unavailable")


def make_opportunity() -> OpportunityCard:
    return OpportunityCard(
        id="opp_test",
        title="Manual workflow pain",
        source_signal_ids=["sig_test"],
        pain_summary="Manual workflow creates repeated errors",
        icp="ops manager",
        opportunity_type="workflow_friction",
        why_it_matters="Recurring pain worth validating.",
    )


class TestAIIdeationFlag(unittest.TestCase):
    def test_flag_off_uses_deterministic_ideation_path(self) -> None:
        engine = build_ideation_engine(
            store=None,
            ai_enabled=False,
            provider=SuccessfulProvider(),
        )

        ideas = engine.generate(make_opportunity())

        self.assertEqual(len(ideas), 2)
        self.assertTrue(all(idea.id.startswith("idea_") for idea in ideas))
        self.assertIn("Structured intake + standardized workflow", ideas[0].short_concept)

    def test_flag_on_successful_stubbed_ai_response_uses_ai_path(self) -> None:
        engine = build_ideation_engine(
            store=None,
            ai_enabled=True,
            provider=SuccessfulProvider(),
        )

        ideas = engine.generate(make_opportunity())

        self.assertEqual(len(ideas), 1)
        self.assertEqual(ideas[0].id, "idea_ai_success")
        self.assertIn("AI-assisted workflow mapper", ideas[0].short_concept)

    def test_flag_on_ai_failure_uses_deterministic_fallback_path(self) -> None:
        engine = build_ideation_engine(
            store=None,
            ai_enabled=True,
            provider=FailingProvider(),
        )

        ideas = engine.generate(make_opportunity())

        self.assertEqual(len(ideas), 2)
        self.assertTrue(all(idea.id.startswith("idea_") for idea in ideas))
        self.assertIn("Structured intake + standardized workflow", ideas[0].short_concept)

    def test_downstream_pipeline_works_with_ai_assisted_ideation_output(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            ai_payload = json.dumps(SuccessfulProvider().generate(make_opportunity()), ensure_ascii=False)
            config = OOSConfig(
                project_root=project_root,
                artifacts_dir=project_root / "artifacts",
                env="test",
                ai_ideation_enabled=True,
                ai_ideation_response_json=ai_payload,
            )

            paths = Orchestrator(config=config).run_signal_batch(input_file=FIXTURE_PATH)

            self.assertTrue(paths["weekly_review"].exists())
            self.assertTrue((config.artifacts_dir / "ideas" / "idea_ai_success.json").exists())
            self.assertTrue(any((config.artifacts_dir / "hypotheses").glob("*.json")))
            self.assertTrue(any((config.artifacts_dir / "council").glob("*.json")))

    def test_cli_env_flag_on_ai_failure_still_completes_with_fallback(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            stdout = io.StringIO()

            with patch.dict(
                "os.environ",
                {"OOS_AI_IDEATION_ENABLED": "1", "OOS_AI_IDEATION_RESPONSE_JSON": "not json"},
                clear=False,
            ):
                with redirect_stdout(stdout):
                    exit_code = main(
                        ["run-weekly-cycle", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)]
                    )

            self.assertEqual(exit_code, 0)
            self.assertIn("OOS weekly cycle completed.", stdout.getvalue())
            ideas = list((project_root / "artifacts" / "ideas").glob("idea_*.json"))
            self.assertGreaterEqual(len(ideas), 1)


if __name__ == "__main__":
    unittest.main()
