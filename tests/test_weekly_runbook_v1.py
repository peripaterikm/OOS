import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "examples" / "real_signal_batch.jsonl"


def run_command(args: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(args)
    return exit_code, stdout.getvalue()


def run_weekly_cycle(project_root: Path) -> None:
    exit_code, output = run_command(
        ["run-weekly-cycle", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)]
    )
    if exit_code != 0:
        raise AssertionError(f"run-weekly-cycle failed with exit code {exit_code}:\n{output}")


def record_pass_decision(project_root: Path) -> None:
    exit_code, output = run_command(
        ["record-founder-review", "--project-root", str(project_root), "--review-id", "review-001", "--decision", "pass"]
    )
    if exit_code != 0:
        raise AssertionError(f"record-founder-review failed with exit code {exit_code}:\n{output}")


class TestWeeklyRunbookV1(unittest.TestCase):
    def test_weekly_cycle_status_works_after_real_weekly_cycle_run(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_weekly_cycle(project_root)

            exit_code, output = run_command(["weekly-cycle-status", "--project-root", str(project_root)])

            self.assertEqual(exit_code, 0)
            self.assertIn("OOS weekly cycle status", output)
            self.assertIn("founder_review_inbox:", output)
            self.assertIn("founder_review_index:", output)
            self.assertIn("latest_weekly_review:", output)

    def test_weekly_cycle_status_shows_review_id_and_linked_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_weekly_cycle(project_root)

            exit_code, output = run_command(["weekly-cycle-status", "--project-root", str(project_root)])

            self.assertEqual(exit_code, 0)
            self.assertIn("review-001", output)
            self.assertIn("decision_options: pass, park, kill", output)
            self.assertIn("sig_real_ops_001, sig_real_ops_002", output)
            self.assertIn("--review-id review-001 --decision pass", output)
            self.assertIn("Portfolio/result summary:", output)

    def test_weekly_cycle_status_reflects_founder_decision_after_record_founder_review(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_weekly_cycle(project_root)
            record_pass_decision(project_root)

            exit_code, output = run_command(["weekly-cycle-status", "--project-root", str(project_root)])

            self.assertEqual(exit_code, 0)
            self.assertIn("Founder decisions:", output)
            self.assertIn("review-001: Active for opp_batch_1", output)
            self.assertIn("opp_batch_1: Active", output)
            self.assertIn("Founder review", output)

    def test_weekly_cycle_status_fails_cleanly_when_no_cycle_artifacts_exist(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            exit_code, output = run_command(["weekly-cycle-status", "--project-root", str(project_root)])

            self.assertEqual(exit_code, 2)
            self.assertIn("weekly-cycle-status refused: no real weekly cycle artifacts found.", output)
            self.assertIn("Next step:", output)
            self.assertIn("run-weekly-cycle", output)

    def test_weekly_cycle_is_reproducible_through_documented_command_flow(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            run_exit, run_output = run_command(
                ["run-weekly-cycle", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)]
            )
            status_before_exit, status_before = run_command(["weekly-cycle-status", "--project-root", str(project_root)])
            decision_exit, decision_output = run_command(
                [
                    "record-founder-review",
                    "--project-root",
                    str(project_root),
                    "--review-id",
                    "review-001",
                    "--decision",
                    "pass",
                ]
            )
            status_after_exit, status_after = run_command(["weekly-cycle-status", "--project-root", str(project_root)])

            self.assertEqual(run_exit, 0)
            self.assertIn("OOS weekly cycle completed.", run_output)
            self.assertEqual(status_before_exit, 0)
            self.assertIn("- none recorded yet", status_before)
            self.assertEqual(decision_exit, 0)
            self.assertIn("Founder review decision recorded.", decision_output)
            self.assertEqual(status_after_exit, 0)
            self.assertIn("review-001: Active for opp_batch_1", status_after)


if __name__ == "__main__":
    unittest.main()
