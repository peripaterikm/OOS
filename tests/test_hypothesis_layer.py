import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.artifact_store import ArtifactStore
from oos.hypothesis_layer import HypothesisLayer
from oos.models import Experiment, Hypothesis, IdeaVariant
from oos.screen_layer import ScreenEvaluator


class TestHypothesisLayer(unittest.TestCase):
    def test_hypothesis_created_from_surviving_idea(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            layer = HypothesisLayer(artifacts_root=artifacts_root)

            idea = IdeaVariant(
                id="idea_1",
                opportunity_id="opp_1",
                short_concept="Standardized workflow templates for ops teams.",
                business_model="subscription",
                standardization_focus="templates + workflow",
                ai_leverage="classification",
                external_execution_needed="none",
                rough_monetization_model="subscription",
            )

            out = layer.generate_for_screened_idea(idea, screen_outcome="pass")
            self.assertIsNotNone(out)
            hyp, exp = out  # type: ignore[misc]
            self.assertEqual(hyp.idea_id, "idea_1")
            self.assertEqual(exp.idea_id, "idea_1")
            self.assertEqual(exp.hypothesis_id, hyp.id)

            # persisted
            store = ArtifactStore(root_dir=artifacts_root)
            hyp_rt = store.read_model(Hypothesis, hyp.id)
            exp_rt = store.read_model(Experiment, exp.id)
            self.assertEqual(hyp_rt, hyp)
            self.assertEqual(exp_rt, exp)

    def test_pass_and_park_survive_kill_excluded(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=artifacts_root)
            screen = ScreenEvaluator(store=store)
            hyp_layer = HypothesisLayer(artifacts_root=artifacts_root)

            base_idea = IdeaVariant(
                id="idea_base",
                opportunity_id="opp_1",
                short_concept="Standardized workflow templates for ops teams.",
                business_model="subscription",
                standardization_focus="templates + workflow",
                ai_leverage="classification",
                external_execution_needed="none",
                rough_monetization_model="subscription",
            )

            res_pass = screen.evaluate(
                base_idea,
                checks_override={c: True for c in [
                    "pain_real_and_recurring",
                    "icp_identifiable_and_can_pay",
                    "productizable_systematizable",
                    "market_not_closed",
                    "founder_not_blocked_by_regulatory_gatekeeping",
                ]},
                anti_patterns_override={a: False for a in [
                    "custom_per_client_handling",
                    "founder_bottleneck",
                    "traffic_ads_monetization",
                    "no_repeatable_workflow",
                ]},
            )
            self.assertEqual(res_pass.outcome, "pass")
            self.assertIsNotNone(hyp_layer.generate_for_screened_idea(base_idea, screen_outcome=res_pass.outcome))

            res_park = screen.evaluate(
                base_idea,
                checks_override={
                    "pain_real_and_recurring": True,
                    "icp_identifiable_and_can_pay": False,
                    "productizable_systematizable": True,
                    "market_not_closed": True,
                    "founder_not_blocked_by_regulatory_gatekeeping": True,
                },
                anti_patterns_override={a: False for a in [
                    "custom_per_client_handling",
                    "founder_bottleneck",
                    "traffic_ads_monetization",
                    "no_repeatable_workflow",
                ]},
            )
            self.assertEqual(res_park.outcome, "park")
            self.assertIsNotNone(hyp_layer.generate_for_screened_idea(base_idea, screen_outcome=res_park.outcome))

            # kill: either anti-pattern or >=2 failed checks => excluded
            res_kill = screen.evaluate(
                base_idea,
                checks_override={
                    "pain_real_and_recurring": False,
                    "icp_identifiable_and_can_pay": False,
                    "productizable_systematizable": True,
                    "market_not_closed": True,
                    "founder_not_blocked_by_regulatory_gatekeeping": True,
                },
                anti_patterns_override={a: False for a in [
                    "custom_per_client_handling",
                    "founder_bottleneck",
                    "traffic_ads_monetization",
                    "no_repeatable_workflow",
                ]},
            )
            self.assertEqual(res_kill.outcome, "kill")
            self.assertIsNone(hyp_layer.generate_for_screened_idea(base_idea, screen_outcome=res_kill.outcome))

    def test_utf8_persistence(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            layer = HypothesisLayer(artifacts_root=artifacts_root)

            idea = IdeaVariant(
                id="idea_utf8",
                opportunity_id="opp_1",
                short_concept="Проверка гипотез по боли и платежеспособности.",
                business_model="subscription",
                standardization_focus="шаблоны + процесс",
                ai_leverage="классификация",
                external_execution_needed="нет",
                rough_monetization_model="подписка",
            )
            hyp, exp = layer.generate_for_screened_idea(idea, screen_outcome="pass")  # type: ignore[misc]

            hyp_path = artifacts_root / "hypotheses" / f"{hyp.id}.json"
            text = hyp_path.read_text(encoding="utf-8")
            self.assertIn("Проверка гипотез", text)


if __name__ == "__main__":
    unittest.main()

