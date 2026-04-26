from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "examples" / "real_signal_batch.jsonl"
REQUIRED_SECTIONS = [
    "signals",
    "dedup",
    "clusters",
    "opportunities",
    "ideas",
    "anti_patterns",
    "critiques",
    "decisions",
    "ai_quality",
]


def run_signal_batch(project_root: Path) -> None:
    with redirect_stdout(io.StringIO()):
        exit_code = main(["run-signal-batch", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)])
    if exit_code != 0:
        raise AssertionError(f"run-signal-batch failed with exit code {exit_code}")


class TestFounderReviewPackageV2(unittest.TestCase):
    def test_package_structure_is_created(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_signal_batch(project_root)

            package_root = project_root / "artifacts" / "founder_review"
            self.assertTrue((package_root / "inbox.md").exists())
            self.assertTrue((package_root / "index.json").exists())
            for section in REQUIRED_SECTIONS:
                self.assertTrue((package_root / "sections" / f"{section}.md").exists(), section)

    def test_index_json_lists_required_sections(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_signal_batch(project_root)

            index = json.loads((project_root / "artifacts" / "founder_review" / "index.json").read_text(encoding="utf-8"))

            self.assertEqual("founder_review_package_v2", index["version"])
            self.assertEqual(["review-001"], index["review_ids"])
            self.assertEqual(set(REQUIRED_SECTIONS), set(index["sections"]))
            self.assertEqual("ops/founder_review_index.json", index["legacy_index"])

    def test_sections_link_to_source_artifacts_where_available(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_signal_batch(project_root)

            package_root = project_root / "artifacts" / "founder_review"
            signals = (package_root / "sections" / "signals.md").read_text(encoding="utf-8")
            opportunities = (package_root / "sections" / "opportunities.md").read_text(encoding="utf-8")
            decisions = (package_root / "sections" / "decisions.md").read_text(encoding="utf-8")

            self.assertIn("sig_real_ops_001", signals)
            self.assertIn("sig_real_ops_002", signals)
            self.assertIn("opportunity:opp_batch_1", opportunities)
            self.assertIn("--review-id review-001 --decision pass", decisions)

    def test_review_id_workflow_still_works(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_signal_batch(project_root)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    ["record-founder-review", "--project-root", str(project_root), "--review-id", "review-001", "--decision", "pass"]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("Founder review decision recorded.", stdout.getvalue())
            review_path = next((project_root / "artifacts" / "founder_reviews").glob("*.json"))
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual("review-001", review["review_id"])

    def test_package_generation_does_not_delete_existing_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_signal_batch(project_root)

            artifacts = project_root / "artifacts"
            self.assertTrue((artifacts / "signals" / "sig_real_ops_001.json").exists())
            self.assertTrue((artifacts / "ops" / "founder_review_index.json").exists())
            self.assertTrue((artifacts / "founder_review" / "index.json").exists())

    def test_missing_optional_ai_stage_artifacts_do_not_crash_package_generation(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_signal_batch(project_root)

            ai_quality = (project_root / "artifacts" / "founder_review" / "sections" / "ai_quality.md").read_text(
                encoding="utf-8"
            )

            self.assertIn("Optional artifacts not available yet", ai_quality)


if __name__ == "__main__":
    unittest.main()
