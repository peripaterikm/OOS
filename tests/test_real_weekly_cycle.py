import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "examples" / "real_signal_batch.jsonl"


def run_weekly_cycle(project_root: Path) -> str:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(["run-weekly-cycle", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)])
    if exit_code != 0:
        raise AssertionError(f"run-weekly-cycle failed with exit code {exit_code}:\n{stdout.getvalue()}")
    return stdout.getvalue()


def record_pass_decision(project_root: Path) -> None:
    with redirect_stdout(io.StringIO()):
        exit_code = main(
            ["record-founder-review", "--project-root", str(project_root), "--review-id", "review-001", "--decision", "pass"]
        )
    if exit_code != 0:
        raise AssertionError(f"record-founder-review failed with exit code {exit_code}")


class TestRealWeeklyCycle(unittest.TestCase):
    def test_run_weekly_cycle_produces_real_weekly_package_from_fixture_batch(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            output = run_weekly_cycle(project_root)

            artifacts_dir = project_root / "artifacts"
            self.assertIn("OOS weekly cycle completed.", output)
            self.assertTrue(any((artifacts_dir / "weekly_reviews").glob("weekly_review_*.json")))
            self.assertTrue(any((artifacts_dir / "readiness").glob("v1_readiness_*.json")))
            self.assertTrue((artifacts_dir / "signals" / "sig_real_ops_001.json").exists())
            self.assertTrue((artifacts_dir / "signals" / "sig_real_ops_002.json").exists())

    def test_founder_review_package_is_included_in_cycle_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            output = run_weekly_cycle(project_root)

            artifacts_dir = project_root / "artifacts"
            self.assertIn("founder_review_index:", output)
            self.assertIn("founder_review_inbox:", output)
            self.assertTrue((artifacts_dir / "ops" / "founder_review_index.json").exists())
            self.assertTrue((artifacts_dir / "ops" / "founder_review_inbox.md").exists())

    def test_record_founder_review_after_cycle_updates_weekly_review(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_weekly_cycle(project_root)

            record_pass_decision(project_root)

            weekly_path = next((project_root / "artifacts" / "weekly_reviews").glob("weekly_review_*.json"))
            weekly = json.loads(weekly_path.read_text(encoding="utf-8"))
            self.assertEqual(len(weekly["recent_founder_reviews"]), 1)
            self.assertEqual(weekly["recent_founder_reviews"][0]["review_id"], "review-001")
            self.assertEqual(weekly["recent_founder_reviews"][0]["decision"], "Active")

    def test_portfolio_reflects_founder_decision_after_cycle(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_weekly_cycle(project_root)

            record_pass_decision(project_root)

            portfolio_path = project_root / "artifacts" / "portfolio" / "ps_opp_batch_1.json"
            portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
            self.assertEqual(portfolio["state"], "Active")
            self.assertIn("Founder review", portfolio["reason"])

    def test_input_signal_traceability_is_preserved_through_cycle(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_weekly_cycle(project_root)

            record_pass_decision(project_root)

            artifacts_dir = project_root / "artifacts"
            index = json.loads((artifacts_dir / "ops" / "founder_review_index.json").read_text(encoding="utf-8"))
            opportunity = json.loads((artifacts_dir / "opportunities" / "opp_batch_1.json").read_text(encoding="utf-8"))
            review_path = next((artifacts_dir / "founder_reviews").glob("*.json"))
            review = json.loads(review_path.read_text(encoding="utf-8"))

            expected_signal_ids = ["sig_real_ops_001", "sig_real_ops_002"]
            self.assertEqual(index["entries"][0]["linked_signal_ids"], expected_signal_ids)
            self.assertEqual(opportunity["source_signal_ids"], expected_signal_ids)
            self.assertEqual(review["linked_signal_ids"], expected_signal_ids)


if __name__ == "__main__":
    unittest.main()
