import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.artifact_store import ArtifactStore
from oos.models import FounderReviewDecision, FounderReviewDecisionEnum, KillReason, PortfolioStateEnum
from oos.portfolio_layer import PortfolioManager
from oos.weekly_review import WeeklyReviewGenerator


class TestPortfolioTransitions(unittest.TestCase):
    def test_valid_transitions(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=artifacts_root)

            # seed kill reason to allow Killed transitions
            store.write_model(
                KillReason(
                    id="kr_1",
                    idea_id="idea_x",
                    kill_date="2026-04-16T00:00:00+00:00",
                    failed_checks=[],
                    matched_anti_patterns=["founder_bottleneck"],
                    summary="Killed due to anti-pattern(s): founder_bottleneck.",
                    looked_attractive_because="Looked simple at first glance.",
                    notes="",
                )
            )

            pm = PortfolioManager(artifacts_root=artifacts_root)
            s1 = pm.transition(opportunity_id="opp_1", to_state=PortfolioStateEnum.Active, reason="Start [needs_review]")
            self.assertEqual(s1.state, PortfolioStateEnum.Active)

            s2 = pm.transition(opportunity_id="opp_1", to_state=PortfolioStateEnum.Parked, reason="Pause [recommend_kill]")
            self.assertEqual(s2.state, PortfolioStateEnum.Parked)

            s3 = pm.transition(
                opportunity_id="opp_1",
                to_state=PortfolioStateEnum.Killed,
                reason="Kill with link",
                linked_kill_reason_id="kr_1",
            )
            self.assertEqual(s3.state, PortfolioStateEnum.Killed)
            self.assertEqual(s3.linked_kill_reason_id, "kr_1")

    def test_invalid_or_blocked_transitions(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            pm = PortfolioManager(artifacts_root=artifacts_root)

            # initial cannot be Graduated
            with self.assertRaises(ValueError):
                pm.transition(opportunity_id="opp_1", to_state=PortfolioStateEnum.Graduated, reason="nope")

            # create Active
            pm.transition(opportunity_id="opp_1", to_state=PortfolioStateEnum.Active, reason="start")

            # cannot go Active -> Active with same reason (no-op blocked)
            with self.assertRaises(ValueError):
                pm.transition(opportunity_id="opp_1", to_state=PortfolioStateEnum.Active, reason="start")

            # cannot kill without kill reason
            with self.assertRaises(ValueError):
                pm.transition(opportunity_id="opp_1", to_state=PortfolioStateEnum.Killed, reason="kill")

    def test_killed_and_graduated_are_terminal(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=artifacts_root)
            store.write_model(
                KillReason(
                    id="kr_1",
                    idea_id="idea_x",
                    kill_date="2026-04-16T00:00:00+00:00",
                    failed_checks=[],
                    matched_anti_patterns=["custom_per_client_handling"],
                    summary="Killed due to anti-pattern(s): custom_per_client_handling.",
                    looked_attractive_because="Seemed easy to sell quickly.",
                    notes="",
                )
            )
            pm = PortfolioManager(artifacts_root=artifacts_root)
            pm.transition(opportunity_id="opp_1", to_state=PortfolioStateEnum.Active, reason="start")
            pm.transition(opportunity_id="opp_1", to_state=PortfolioStateEnum.Killed, reason="k", linked_kill_reason_id="kr_1")

            with self.assertRaises(ValueError):
                pm.transition(opportunity_id="opp_1", to_state=PortfolioStateEnum.Active, reason="revive")


class TestWeeklyReview(unittest.TestCase):
    def test_weekly_summary_generation_and_mixed_states(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=artifacts_root)
            store.write_model(
                KillReason(
                    id="kr_1",
                    idea_id="idea_x",
                    kill_date="2026-04-16T00:00:00+00:00",
                    failed_checks=[],
                    matched_anti_patterns=["founder_bottleneck"],
                    summary="Killed due to anti-pattern(s): founder_bottleneck.",
                    looked_attractive_because="Sounded like a fast win.",
                    notes="",
                )
            )

            pm = PortfolioManager(artifacts_root=artifacts_root)
            pm.transition(opportunity_id="opp_a", to_state=PortfolioStateEnum.Active, reason="Active [needs_review]")
            pm.transition(opportunity_id="opp_p", to_state=PortfolioStateEnum.Parked, reason="Park [recommend_park]")
            pm.transition(opportunity_id="opp_k", to_state=PortfolioStateEnum.Active, reason="tmp")
            pm.transition(
                opportunity_id="opp_k",
                to_state=PortfolioStateEnum.Killed,
                reason="Killed [recommend_kill]",
                linked_kill_reason_id="kr_1",
            )
            pm.transition(opportunity_id="opp_g", to_state=PortfolioStateEnum.Active, reason="tmp")
            pm.transition(opportunity_id="opp_g", to_state=PortfolioStateEnum.Graduated, reason="Done [recommend_graduate]")

            gen = WeeklyReviewGenerator(artifacts_root=artifacts_root)
            out_path = gen.generate(now=datetime(2026, 4, 16, tzinfo=timezone.utc))
            self.assertTrue(out_path.exists())

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["week"], "2026-W16")
            self.assertEqual(payload["counts"]["Active"], 1)
            self.assertEqual(payload["counts"]["Parked"], 1)
            self.assertEqual(payload["counts"]["Killed"], 1)
            self.assertEqual(payload["counts"]["Graduated"], 1)

            # surfaced lists from explicit tags
            self.assertIn("opp_a", payload["needs_founder_review"])
            self.assertIn("opp_k", payload["should_be_killed"])
            self.assertIn("opp_p", payload["should_be_parked"])
            self.assertIn("opp_g", payload["may_be_graduated"])

            # killed includes kill link
            self.assertEqual(payload["killed_with_kill_links"]["opp_k"], "kr_1")
            self.assertEqual(payload["recent_founder_reviews"], [])

    def test_weekly_summary_surfaces_founder_review_decisions(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=artifacts_root)
            store.write_model(
                FounderReviewDecision(
                    id="frd_old",
                    opportunity_id="opp_old",
                    decision=FounderReviewDecisionEnum.Active,
                    reason="Founder keeps this active after reviewing interview evidence.",
                    selected_next_experiment_or_action="Run pricing smoke test.",
                    timestamp="2026-04-15T12:00:00+00:00",
                    portfolio_updated=True,
                    weekly_review_id="weekly_review_2026-W15.json",
                )
            )
            store.write_model(
                FounderReviewDecision(
                    id="frd_new",
                    opportunity_id="opp_new",
                    decision=FounderReviewDecisionEnum.Parked,
                    reason="Founder parks until buyer urgency is proven.",
                    selected_next_experiment_or_action="Run 5 ICP interviews.",
                    timestamp="2026-04-16T12:00:00+00:00",
                    portfolio_updated=True,
                    readiness_report_id="v1_readiness_2026-04-16.json",
                    weekly_review_id="weekly_review_2026-W16.json",
                    council_decision_ids=["cd_1"],
                    hypothesis_ids=["hyp_1"],
                    experiment_ids=["exp_1"],
                )
            )

            out_path = WeeklyReviewGenerator(artifacts_root=artifacts_root).generate(
                now=datetime(2026, 4, 16, tzinfo=timezone.utc)
            )
            payload = json.loads(out_path.read_text(encoding="utf-8"))

            reviews = payload["recent_founder_reviews"]
            self.assertEqual([review["id"] for review in reviews], ["frd_new", "frd_old"])
            latest = reviews[0]
            self.assertEqual(latest["opportunity_id"], "opp_new")
            self.assertEqual(latest["decision"], "Parked")
            self.assertEqual(latest["reason"], "Founder parks until buyer urgency is proven.")
            self.assertEqual(latest["selected_next_action"], "Run 5 ICP interviews.")
            self.assertEqual(
                latest["linked_evidence_ids"],
                {
                    "readiness_report_id": "v1_readiness_2026-04-16.json",
                    "weekly_review_id": "weekly_review_2026-W16.json",
                    "council_decision_ids": ["cd_1"],
                    "hypothesis_ids": ["hyp_1"],
                    "experiment_ids": ["exp_1"],
                },
            )


if __name__ == "__main__":
    unittest.main()

