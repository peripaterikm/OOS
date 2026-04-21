import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.config import OOSConfig
from oos.model_routing import ModelRouter
from oos.models import SignalStatus
from oos.orchestrator import Orchestrator


class TestWeek8EndToEnd(unittest.TestCase):
    def test_model_routing_selection_by_stage(self) -> None:
        router = ModelRouter(config_path=None)
        self.assertEqual(router.select("signal"), "cheap")
        self.assertEqual(router.select("council"), "strong")

    def test_end_to_end_dry_run_artifacts_and_weekly_review(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            artifacts_dir = project_root / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            # Write a routing config to prove configurability is used.
            cfg_dir = project_root / "config"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "model_routing.json").write_text(
                json.dumps({"rules_by_stage": {"signal": "cheap", "council": "strong"}}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            config = OOSConfig(project_root=project_root, artifacts_dir=artifacts_dir, env="test")
            orch = Orchestrator(config=config)

            now = datetime(2026, 4, 16, tzinfo=timezone.utc)
            paths = orch.run_v1_dry_run(now=now)

            # Weekly review exists
            self.assertTrue(paths["weekly_review"].exists())

            # Readiness report exists and references written artifacts
            self.assertTrue(paths["readiness_report"].exists())
            readiness = json.loads(paths["readiness_report"].read_text(encoding="utf-8"))
            self.assertEqual(readiness["status"], "ok")
            self.assertIn("routing", readiness)
            self.assertIn("weekly_review", readiness["artifacts_written"])

            # Operational checklist exists (UTF-8)
            self.assertTrue(paths["operational_checklist"].exists())
            checklist = paths["operational_checklist"].read_text(encoding="utf-8")
            self.assertIn("Operational Checklist", checklist)
            self.assertTrue(paths["founder_review_checklist"].exists())
            founder_checklist = paths["founder_review_checklist"].read_text(encoding="utf-8")
            self.assertIn("## Review Objective", founder_checklist)
            self.assertIn("## Signals And Opportunities To Inspect", founder_checklist)
            self.assertIn("## Kill / Proceed Decisions", founder_checklist)
            self.assertIn("## Hypotheses And Experiments To Review", founder_checklist)
            self.assertIn("## Council Concerns", founder_checklist)
            self.assertIn("## Portfolio State Review", founder_checklist)
            self.assertIn("## Founder Action Checklist", founder_checklist)
            self.assertIn("artifacts/signals/sig_dry_valid.json", founder_checklist)
            self.assertIn("artifacts/weak_signals/sig_dry_weak.json", founder_checklist)
            self.assertIn("artifacts/opportunities/opp_dry_1.json", founder_checklist)
            self.assertIn("artifacts/portfolio/ps_opp_dry_1.json", founder_checklist)

            # Artifact consistency: signals/opportunity/ideas exist
            self.assertTrue((artifacts_dir / "signals" / "sig_dry_valid.json").exists())
            self.assertTrue((artifacts_dir / "signals" / "sig_dry_weak.json").exists())
            weak_signal = json.loads((artifacts_dir / "signals" / "sig_dry_weak.json").read_text(encoding="utf-8"))
            self.assertEqual(weak_signal["status"], SignalStatus.weak.value)
            self.assertEqual(weak_signal["validity_score"], 2)
            self.assertTrue((artifacts_dir / "weak_signals" / "sig_dry_weak.json").exists())
            self.assertFalse((artifacts_dir / "noise_archive" / "sig_dry_weak.json").exists())
            self.assertTrue((artifacts_dir / "opportunities" / "opp_dry_1.json").exists())
            opportunity = json.loads((artifacts_dir / "opportunities" / "opp_dry_1.json").read_text(encoding="utf-8"))
            self.assertIn("sig_dry_weak", opportunity["source_signal_ids"])
            idea_ids = readiness["artifacts_written"]["ideas"]
            self.assertGreaterEqual(len(idea_ids), 1)
            for iid in idea_ids:
                self.assertTrue((artifacts_dir / "ideas" / f"{iid}.json").exists())

            # Portfolio state exists
            self.assertTrue((artifacts_dir / "portfolio" / "ps_opp_dry_1.json").exists())

            # Weekly review payload references the opportunity state
            weekly_payload = json.loads(paths["weekly_review"].read_text(encoding="utf-8"))
            by_state = weekly_payload["by_state"]
            self.assertIn("opp_dry_1", by_state["Active"] + by_state["Parked"] + by_state["Killed"] + by_state["Graduated"])

    def test_end_to_end_dry_run_is_repeatable_for_same_artifact_root(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            artifacts_dir = project_root / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            config = OOSConfig(project_root=project_root, artifacts_dir=artifacts_dir, env="test")
            orch = Orchestrator(config=config)

            first_now = datetime(2026, 4, 16, 10, 0, tzinfo=timezone.utc)
            second_now = first_now + timedelta(minutes=5)
            orch.run_v1_dry_run(now=first_now)
            paths = orch.run_v1_dry_run(now=second_now)

            self.assertTrue(paths["weekly_review"].exists())
            self.assertTrue(paths["readiness_report"].exists())
            self.assertTrue(paths["operational_checklist"].exists())
            self.assertTrue(paths["founder_review_checklist"].exists())
            self.assertTrue((artifacts_dir / "signals" / "sig_dry_valid.json").exists())
            self.assertTrue((artifacts_dir / "weak_signals" / "sig_dry_weak.json").exists())
            self.assertTrue((artifacts_dir / "opportunities" / "opp_dry_1.json").exists())

            portfolio_path = artifacts_dir / "portfolio" / "ps_opp_dry_1.json"
            self.assertTrue(portfolio_path.exists())
            self.assertEqual(len(list((artifacts_dir / "portfolio").glob("ps_opp_dry_1.json"))), 1)
            portfolio_state = json.loads(portfolio_path.read_text(encoding="utf-8"))
            self.assertEqual(portfolio_state["state"], "Active")
            self.assertEqual(portfolio_state["reason"], "Dry run 2026-04-16T10:05:00+00:00 [needs_review]")


if __name__ == "__main__":
    unittest.main()

