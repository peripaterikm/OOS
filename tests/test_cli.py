import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main


class TestCli(unittest.TestCase):
    def test_v1_dry_run_command_writes_expected_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["v1-dry-run", "--project-root", tmp])

            output = stdout.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("OOS v1 dry run completed.", output)
            self.assertIn("weekly_review:", output)
            self.assertIn("readiness_report:", output)
            self.assertIn("operational_checklist:", output)
            self.assertIn("founder_review_checklist:", output)

            artifacts_dir = Path(tmp) / "artifacts"
            self.assertTrue((artifacts_dir / "signals" / "sig_dry_valid.json").exists())
            self.assertTrue((artifacts_dir / "weak_signals" / "sig_dry_weak.json").exists())
            self.assertTrue((artifacts_dir / "opportunities" / "opp_dry_1.json").exists())
            self.assertTrue((artifacts_dir / "portfolio" / "ps_opp_dry_1.json").exists())
            self.assertTrue((artifacts_dir / "ops" / "v1_operational_checklist.txt").exists())
            self.assertTrue((artifacts_dir / "ops" / "v1_founder_review_checklist.md").exists())

            readiness_paths = list((artifacts_dir / "readiness").glob("v1_readiness_*.json"))
            self.assertEqual(len(readiness_paths), 1)
            readiness = json.loads(readiness_paths[0].read_text(encoding="utf-8"))
            self.assertEqual(readiness["status"], "ok")

    def test_record_founder_review_writes_decision_and_updates_safe_portfolio_state(self) -> None:
        with TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                main(["v1-dry-run", "--project-root", tmp])
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "record-founder-review",
                        "--project-root",
                        tmp,
                        "--opportunity-id",
                        "opp_dry_1",
                        "--decision",
                        "Parked",
                        "--reason",
                        "Founder wants more evidence before keeping this active.",
                        "--next-action",
                        "Run exp_dry customer interviews.",
                        "--timestamp",
                        "2026-04-16T12:00:00+00:00",
                    ]
                )

            output = stdout.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Founder review decision recorded.", output)
            self.assertIn("decision_artifact:", output)
            self.assertIn("portfolio_updated: true", output)

            artifacts_dir = Path(tmp) / "artifacts"
            review_path = artifacts_dir / "founder_reviews" / "frd_opp_dry_1_2026-04-16T12_00_00_00_00.json"
            self.assertTrue(review_path.exists())
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["opportunity_id"], "opp_dry_1")
            self.assertEqual(review["decision"], "Parked")
            self.assertEqual(review["reason"], "Founder wants more evidence before keeping this active.")
            self.assertEqual(review["selected_next_experiment_or_action"], "Run exp_dry customer interviews.")
            self.assertEqual(review["timestamp"], "2026-04-16T12:00:00+00:00")
            self.assertTrue(review["portfolio_updated"])

            portfolio = json.loads((artifacts_dir / "portfolio" / "ps_opp_dry_1.json").read_text(encoding="utf-8"))
            self.assertEqual(portfolio["state"], "Parked")
            self.assertIn("Founder review 2026-04-16T12:00:00+00:00", portfolio["reason"])


if __name__ == "__main__":
    unittest.main()
