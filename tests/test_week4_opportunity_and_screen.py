import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.artifact_store import ArtifactStore
from oos.models import IdeaVariant, SignalStatus
from oos.opportunity_layer import OpportunityFramer
from oos.screen_layer import ScreenEvaluator
from oos.signal_layer import SignalLayer


class TestWeek4OpportunityFraming(unittest.TestCase):
    def test_opportunity_created_from_validated_signals(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            layer = SignalLayer(artifacts_root=artifacts_root)

            sig = layer.ingest_manual(
                raw_content="Every day I manually export and copy data; it takes 30 minutes.",
                extracted_pain="Manual export/copy wastes time daily.",
                candidate_icp="ops manager",
                signal_id="sig_v1",
                timestamp="2026-04-16T00:00:00+00:00",
            )
            self.assertEqual(sig.status, SignalStatus.validated)

            framer = OpportunityFramer(store=ArtifactStore(root_dir=artifacts_root))
            card = framer.frame_from_signals([sig], opportunity_id="opp_1")

            self.assertEqual(card.id, "opp_1")
            self.assertIn("sig_v1", card.source_signal_ids)
            self.assertTrue((artifacts_root / "opportunities" / "opp_1.json").exists())

    def test_weak_signal_manual_promotion(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            layer = SignalLayer(artifacts_root=artifacts_root)

            # Force a deterministic weak signal (score=2) via file import overrides.
            import_path = Path(tmp) / "weak.jsonl"
            import_path.write_text(
                json.dumps(
                    {
                        "id": "sig_w1",
                        "source": "file_import",
                        "timestamp": "2026-04-16T00:00:00+00:00",
                        "raw_content": "Minor annoyance.",
                        "extracted_pain": "Minor annoyance in workflow.",
                        "candidate_icp": "unknown",
                        "validity_specificity": 1,
                        "validity_recurrence": 1,
                        "validity_workaround": 0,
                        "validity_cost_signal": 0,
                        "validity_icp_match": 0,
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            weak = layer.ingest_file(import_path)[0]
            self.assertEqual(weak.status, SignalStatus.weak)

            framer = OpportunityFramer(store=ArtifactStore(root_dir=artifacts_root))
            # without promotion -> error
            with self.assertRaises(ValueError):
                framer.frame_from_signals([weak], opportunity_id="opp_fail")

            # with explicit promotion -> ok
            card = framer.frame_from_signals(
                [weak],
                opportunity_id="opp_ok",
                promote_weak_signal_ids={"sig_w1"},
            )
            self.assertEqual(card.id, "opp_ok")
            self.assertIn("sig_w1", card.source_signal_ids)


class TestWeek4ScreenLayer(unittest.TestCase):
    def test_disguised_consulting_kill_case(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=artifacts_root)
            screen = ScreenEvaluator(store=store)

            idea = IdeaVariant(
                id="idea_dc",
                opportunity_id="opp_1",
                short_concept="We do a custom build per client.",
                business_model="subscription",
                standardization_focus="none",
                ai_leverage="n/a",
                external_execution_needed="custom per client handling required",
                rough_monetization_model="custom project fees",
            )
            res = screen.evaluate(
                idea,
                anti_patterns_override={"custom_per_client_handling": True, "no_repeatable_workflow": False},
            )
            self.assertEqual(res.outcome, "kill")
            self.assertIn("custom_per_client_handling", res.matched_anti_patterns)
            self.assertIsNotNone(res.kill_reason_id)
            self.assertTrue((artifacts_root / "kills" / f"{res.kill_reason_id}.json").exists())

    def test_founder_bottleneck_kill_case(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=artifacts_root)
            screen = ScreenEvaluator(store=store)

            idea = IdeaVariant(
                id="idea_fb",
                opportunity_id="opp_1",
                short_concept="Only me (founder) can deliver the core value.",
                business_model="subscription",
                standardization_focus="templates",
                ai_leverage="n/a",
                external_execution_needed="founder must be present for each client",
                rough_monetization_model="subscription",
            )
            res = screen.evaluate(
                idea,
                anti_patterns_override={"founder_bottleneck": True, "no_repeatable_workflow": False},
            )
            self.assertEqual(res.outcome, "kill")
            self.assertIn("founder_bottleneck", res.matched_anti_patterns)

    def test_pass_park_kill_behavior(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=artifacts_root)
            screen = ScreenEvaluator(store=store)

            idea = IdeaVariant(
                id="idea_base",
                opportunity_id="opp_1",
                short_concept="Standardized workflow templates for ops teams.",
                business_model="subscription",
                standardization_focus="templates + workflow",
                ai_leverage="classification",
                external_execution_needed="none",
                rough_monetization_model="subscription",
            )

            # pass: no failed checks, no anti-patterns
            res_pass = screen.evaluate(
                idea,
                checks_override={
                    "pain_real_and_recurring": True,
                    "icp_identifiable_and_can_pay": True,
                    "productizable_systematizable": True,
                    "market_not_closed": True,
                    "founder_not_blocked_by_regulatory_gatekeeping": True,
                },
                anti_patterns_override={
                    "custom_per_client_handling": False,
                    "founder_bottleneck": False,
                    "traffic_ads_monetization": False,
                    "no_repeatable_workflow": False,
                },
            )
            self.assertEqual(res_pass.outcome, "pass")

            # park: 1 failed mandatory check
            res_park = screen.evaluate(
                idea,
                checks_override={
                    "pain_real_and_recurring": True,
                    "icp_identifiable_and_can_pay": False,
                    "productizable_systematizable": True,
                    "market_not_closed": True,
                    "founder_not_blocked_by_regulatory_gatekeeping": True,
                },
                anti_patterns_override={a: False for a in ["custom_per_client_handling", "founder_bottleneck", "traffic_ads_monetization", "no_repeatable_workflow"]},
            )
            self.assertEqual(res_park.outcome, "park")

            # kill: 2 failed mandatory checks
            res_kill = screen.evaluate(
                idea,
                checks_override={
                    "pain_real_and_recurring": False,
                    "icp_identifiable_and_can_pay": False,
                    "productizable_systematizable": True,
                    "market_not_closed": True,
                    "founder_not_blocked_by_regulatory_gatekeeping": True,
                },
                anti_patterns_override={a: False for a in ["custom_per_client_handling", "founder_bottleneck", "traffic_ads_monetization", "no_repeatable_workflow"]},
            )
            self.assertEqual(res_kill.outcome, "kill")


if __name__ == "__main__":
    unittest.main()

