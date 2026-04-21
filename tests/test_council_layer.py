import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.artifact_store import ArtifactStore
from oos.council_layer import CouncilLayer, DeterministicCouncilEngine
from oos.models import CouncilDecision, IdeaVariant, KillReason


class TestCouncilLayer(unittest.TestCase):
    def test_council_decision_generation_and_roundtrip(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            layer = CouncilLayer(artifacts_root=artifacts_root, engine=DeterministicCouncilEngine())

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

            decision = layer.generate_for_shortlisted_idea(idea, decision_id="cd_1")
            self.assertEqual(decision.id, "cd_1")
            self.assertEqual(decision.idea_id, "idea_1")
            self.assertTrue((artifacts_root / "council" / "cd_1.json").exists())

            store = ArtifactStore(root_dir=artifacts_root)
            rt = store.read_model(CouncilDecision, "cd_1")
            self.assertEqual(rt, decision)

    def test_suspiciously_clean_true_when_0_or_1_kill_scenarios(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            layer = CouncilLayer(artifacts_root=artifacts_root, engine=DeterministicCouncilEngine())

            # No obvious skeptic scenarios -> 0 => suspiciously_clean true
            idea_clean = IdeaVariant(
                id="idea_clean",
                opportunity_id="opp_1",
                short_concept="Standardized workflow templates for ops teams.",
                business_model="subscription",
                standardization_focus="templates + workflow",
                ai_leverage="classification",
                external_execution_needed="none",
                rough_monetization_model="subscription",
            )
            d1 = layer.generate_for_shortlisted_idea(idea_clean)
            self.assertTrue(d1.suspiciously_clean)

            # One obvious scenario -> 1 => suspiciously_clean true
            idea_one = IdeaVariant(
                id="idea_one",
                opportunity_id="opp_1",
                short_concept="Custom per client build.",
                business_model="subscription",
                standardization_focus="templates",
                ai_leverage="n/a",
                external_execution_needed="custom per client handling required",
                rough_monetization_model="subscription",
            )
            d2 = layer.generate_for_shortlisted_idea(idea_one)
            self.assertTrue(d2.suspiciously_clean)

    def test_pattern_matcher_empty_kill_archive(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            layer = CouncilLayer(artifacts_root=artifacts_root, engine=DeterministicCouncilEngine())

            idea = IdeaVariant(
                id="idea_pm0",
                opportunity_id="opp_1",
                short_concept="Standardized workflow templates.",
                business_model="subscription",
                standardization_focus="templates + workflow",
                ai_leverage="classification",
                external_execution_needed="none",
                rough_monetization_model="subscription",
            )
            decision = layer.generate_for_shortlisted_idea(idea)
            self.assertIn("Kill archive empty", decision.pattern_matcher_similarity[0])

    def test_pattern_matcher_finds_similar_failure(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=artifacts_root)

            # Seed kill archive with a known anti-pattern
            kill = KillReason(
                id="kr_1",
                idea_id="old_idea",
                kill_date="2026-04-16T00:00:00+00:00",
                failed_checks=[],
                matched_anti_patterns=["custom_per_client_handling"],
                summary="Killed due to anti-pattern(s): custom_per_client_handling.",
                looked_attractive_because="custom build sounded easy",
                notes="",
            )
            store.write_model(kill)

            layer = CouncilLayer(artifacts_root=artifacts_root, engine=DeterministicCouncilEngine())
            idea_custom = IdeaVariant(
                id="idea_custom",
                opportunity_id="opp_1",
                short_concept="Custom per client build.",
                business_model="subscription",
                standardization_focus="none",
                ai_leverage="n/a",
                external_execution_needed="custom per client handling required",
                rough_monetization_model="project fees",
            )
            decision = layer.generate_for_shortlisted_idea(idea_custom)
            joined = " ".join(decision.pattern_matcher_similarity)
            self.assertIn("kr_1", joined)


if __name__ == "__main__":
    unittest.main()

