import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main


class TestCli(unittest.TestCase):
    def test_v1_dry_run_proceeds_without_artifacts_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["v1-dry-run", "--project-root", tmp])

            self.assertEqual(exit_code, 0)
            self.assertIn("OOS v1 dry run completed.", stdout.getvalue())
            self.assertTrue((Path(tmp) / "artifacts").exists())

    def test_v1_dry_run_proceeds_with_empty_artifacts_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "artifacts"
            artifacts_dir.mkdir()
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["v1-dry-run", "--project-root", tmp])

            self.assertEqual(exit_code, 0)
            self.assertIn("OOS v1 dry run completed.", stdout.getvalue())
            self.assertTrue((artifacts_dir / "signals" / "sig_dry_valid.json").exists())

    def test_v1_dry_run_refuses_non_empty_artifacts_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "artifacts"
            artifacts_dir.mkdir()
            existing_path = artifacts_dir / "existing.txt"
            existing_path.write_text("existing artifact", encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["v1-dry-run", "--project-root", tmp])

            output = stdout.getvalue()
            self.assertEqual(exit_code, 2)
            self.assertIn("v1-dry-run refused: dirty project root detected.", output)
            self.assertIn(f"Existing artifacts found at: {artifacts_dir.resolve()}", output)
            self.assertIn("Next steps:", output)
            self.assertIn("  1) remove or rename the artifacts directory, or", output)
            self.assertIn("  2) run against a clean project root", output)
            self.assertEqual(existing_path.read_text(encoding="utf-8"), "existing artifact")
            self.assertFalse((artifacts_dir / "signals").exists())

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
            artifacts_dir = Path(tmp) / "artifacts"
            readiness_path = next((artifacts_dir / "readiness").glob("v1_readiness_*.json"))
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            weekly_review_id = readiness["artifacts_written"]["weekly_review"]
            council_id = readiness["artifacts_written"]["council"][0]
            hypothesis_id = readiness["artifacts_written"]["hypotheses"][0]
            experiment_id = readiness["artifacts_written"]["experiments"][0]
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
                        "--readiness-report-id",
                        readiness_path.name,
                        "--weekly-review-id",
                        weekly_review_id,
                        "--council-decision-id",
                        council_id,
                        "--hypothesis-id",
                        hypothesis_id,
                        "--experiment-id",
                        experiment_id,
                    ]
                )

            output = stdout.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Founder review decision recorded.", output)
            self.assertIn("decision_artifact:", output)
            self.assertIn("portfolio_updated: true", output)

            review_path = artifacts_dir / "founder_reviews" / "frd_opp_dry_1_2026-04-16T12_00_00_00_00.json"
            self.assertTrue(review_path.exists())
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["opportunity_id"], "opp_dry_1")
            self.assertEqual(review["decision"], "Parked")
            self.assertEqual(review["reason"], "Founder wants more evidence before keeping this active.")
            self.assertEqual(review["selected_next_experiment_or_action"], "Run exp_dry customer interviews.")
            self.assertEqual(review["timestamp"], "2026-04-16T12:00:00+00:00")
            self.assertTrue(review["portfolio_updated"])
            self.assertEqual(review["readiness_report_id"], readiness_path.name)
            self.assertEqual(review["weekly_review_id"], weekly_review_id)
            self.assertEqual(review["council_decision_ids"], [council_id])
            self.assertEqual(review["hypothesis_ids"], [hypothesis_id])
            self.assertEqual(review["experiment_ids"], [experiment_id])

            portfolio = json.loads((artifacts_dir / "portfolio" / "ps_opp_dry_1.json").read_text(encoding="utf-8"))
            self.assertEqual(portfolio["state"], "Parked")
            self.assertIn("Founder review 2026-04-16T12:00:00+00:00", portfolio["reason"])

    def test_record_founder_review_killed_requires_and_links_kill_reason(self) -> None:
        with TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                main(["v1-dry-run", "--project-root", tmp])

            artifacts_dir = Path(tmp) / "artifacts"
            kill_reason_id = next((artifacts_dir / "kills").glob("*.json")).stem
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
                        "Killed",
                        "--reason",
                        "Founder accepts the existing kill reason.",
                        "--next-action",
                        "Archive the opportunity and reuse the pattern.",
                        "--timestamp",
                        "2026-04-16T13:00:00+00:00",
                        "--linked-kill-reason-id",
                        kill_reason_id,
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("portfolio_updated: true", stdout.getvalue())
            review_path = artifacts_dir / "founder_reviews" / "frd_opp_dry_1_2026-04-16T13_00_00_00_00.json"
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["decision"], "Killed")
            self.assertTrue(review["portfolio_updated"])
            self.assertEqual(review["linked_kill_reason_id"], kill_reason_id)

            portfolio = json.loads((artifacts_dir / "portfolio" / "ps_opp_dry_1.json").read_text(encoding="utf-8"))
            self.assertEqual(portfolio["state"], "Killed")
            self.assertEqual(portfolio["linked_kill_reason_id"], kill_reason_id)

    def test_record_founder_review_killed_requires_kill_reason_id(self) -> None:
        with TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                main(["v1-dry-run", "--project-root", tmp])

            with self.assertRaisesRegex(ValueError, "--linked-kill-reason-id is required"):
                main(
                    [
                        "record-founder-review",
                        "--project-root",
                        tmp,
                        "--opportunity-id",
                        "opp_dry_1",
                        "--decision",
                        "Killed",
                        "--reason",
                        "Founder accepts the kill case.",
                        "--next-action",
                        "Archive the opportunity.",
                    ]
                )

    def test_record_founder_review_rejects_missing_linked_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                main(["v1-dry-run", "--project-root", tmp])

            base_args = [
                "record-founder-review",
                "--project-root",
                tmp,
                "--opportunity-id",
                "opp_dry_1",
                "--decision",
                "Parked",
                "--reason",
                "Founder wants more evidence.",
                "--next-action",
                "Run interviews.",
            ]
            missing_cases = [
                ("readiness", ["--readiness-report-id", "missing_readiness"]),
                ("weekly_reviews", ["--weekly-review-id", "missing_weekly_review"]),
                ("council", ["--council-decision-id", "missing_council"]),
                ("hypotheses", ["--hypothesis-id", "missing_hypothesis"]),
                ("experiments", ["--experiment-id", "missing_experiment"]),
            ]
            for kind, args in missing_cases:
                with self.subTest(kind=kind):
                    with self.assertRaisesRegex(ValueError, f"Linked {kind} artifact not found"):
                        main(base_args + args)

            killed_args = [
                "record-founder-review",
                "--project-root",
                tmp,
                "--opportunity-id",
                "opp_dry_1",
                "--decision",
                "Killed",
                "--reason",
                "Founder accepts the kill case.",
                "--next-action",
                "Archive the opportunity.",
                "--linked-kill-reason-id",
                "missing_kill_reason",
            ]
            with self.assertRaisesRegex(ValueError, "Linked kills artifact not found"):
                main(killed_args)

    def test_record_founder_review_rejects_path_like_linked_artifact_ids(self) -> None:
        with TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                main(["v1-dry-run", "--project-root", tmp])

            args = [
                "record-founder-review",
                "--project-root",
                tmp,
                "--opportunity-id",
                "opp_dry_1",
                "--decision",
                "Parked",
                "--reason",
                "Founder wants more evidence.",
                "--next-action",
                "Run interviews.",
                "--weekly-review-id",
                "../weekly_review_2026-W16",
            ]

            with self.assertRaisesRegex(ValueError, "pass an artifact id or .json filename, not a path"):
                main(args)


if __name__ == "__main__":
    unittest.main()
