import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "examples" / "real_signal_batch.jsonl"


def run_signal_batch(project_root: Path) -> None:
    with redirect_stdout(io.StringIO()):
        exit_code = main(["run-signal-batch", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)])
    if exit_code != 0:
        raise AssertionError(f"run-signal-batch failed with exit code {exit_code}")


def load_founder_review_index(project_root: Path) -> dict:
    index_path = project_root / "artifacts" / "ops" / "founder_review_index.json"
    return json.loads(index_path.read_text(encoding="utf-8"))


class TestRealFounderPackage(unittest.TestCase):
    def test_founder_review_package_is_created_from_real_signal_batch_run(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            run_signal_batch(project_root)

            artifacts_dir = project_root / "artifacts"
            inbox_path = artifacts_dir / "ops" / "founder_review_inbox.md"
            index_path = artifacts_dir / "ops" / "founder_review_index.json"
            self.assertTrue(inbox_path.exists())
            self.assertTrue(index_path.exists())
            inbox = inbox_path.read_text(encoding="utf-8")
            self.assertIn("Founder Review Inbox", inbox)
            self.assertIn("--review-id review-001 --decision pass", inbox)

    def test_review_index_contains_review_id_and_linked_references(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            run_signal_batch(project_root)

            index = load_founder_review_index(project_root)
            entry = index["entries"][0]
            self.assertEqual(entry["review_id"], "review-001")
            self.assertEqual(entry["entity_type"], "opportunity")
            self.assertEqual(entry["entity_id"], "opp_batch_1")
            self.assertEqual(entry["decision_options"], ["pass", "park", "kill"])
            self.assertEqual(entry["linked_signal_ids"], ["sig_real_ops_001", "sig_real_ops_002"])
            self.assertEqual(entry["linked_artifact_ids"]["opportunity"], "opp_batch_1")
            self.assertIn("weekly_review", entry["linked_artifact_ids"])
            self.assertIn("readiness_report", entry["linked_artifact_ids"])

    def test_record_founder_review_by_review_id_works(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_signal_batch(project_root)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    ["record-founder-review", "--project-root", str(project_root), "--review-id", "review-001", "--decision", "pass"]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("Founder review decision recorded.", stdout.getvalue())
            review_path = next((project_root / "artifacts" / "founder_reviews").glob("*.json"))
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["review_id"], "review-001")
            self.assertEqual(review["opportunity_id"], "opp_batch_1")
            self.assertEqual(review["decision"], "Active")
            self.assertEqual(review["linked_signal_ids"], ["sig_real_ops_001", "sig_real_ops_002"])
            self.assertEqual(review["weekly_review_id"], load_founder_review_index(project_root)["entries"][0]["linked_artifact_ids"]["weekly_review"])

    def test_founder_decisions_remain_visible_in_weekly_review(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_signal_batch(project_root)

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    ["record-founder-review", "--project-root", str(project_root), "--review-id", "review-001", "--decision", "pass"]
                )

            self.assertEqual(exit_code, 0)
            weekly_path = next((project_root / "artifacts" / "weekly_reviews").glob("weekly_review_*.json"))
            weekly = json.loads(weekly_path.read_text(encoding="utf-8"))
            self.assertEqual(len(weekly["recent_founder_reviews"]), 1)
            review = weekly["recent_founder_reviews"][0]
            self.assertEqual(review["review_id"], "review-001")
            self.assertEqual(review["opportunity_id"], "opp_batch_1")
            self.assertEqual(review["linked_signal_ids"], ["sig_real_ops_001", "sig_real_ops_002"])

    def test_traceability_back_to_input_signal_ids_is_preserved(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_signal_batch(project_root)

            with redirect_stdout(io.StringIO()):
                main(["record-founder-review", "--project-root", str(project_root), "--review-id", "review-001", "--decision", "pass"])

            artifacts_dir = project_root / "artifacts"
            opportunity = json.loads((artifacts_dir / "opportunities" / "opp_batch_1.json").read_text(encoding="utf-8"))
            review_path = next((artifacts_dir / "founder_reviews").glob("*.json"))
            founder_review = json.loads(review_path.read_text(encoding="utf-8"))

            self.assertEqual(opportunity["source_signal_ids"], ["sig_real_ops_001", "sig_real_ops_002"])
            self.assertEqual(founder_review["linked_signal_ids"], opportunity["source_signal_ids"])


if __name__ == "__main__":
    unittest.main()
