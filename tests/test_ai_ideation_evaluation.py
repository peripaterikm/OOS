import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from oos.cli import main


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "examples" / "real_signal_batch.jsonl"


VALID_AI_PAYLOAD = json.dumps(
    [
        {
            "id": "idea_ai_eval_success",
            "short_concept": "AI-assisted exception workflow mapper for recurring export failures",
            "business_model": "subscription",
            "standardization_focus": "repeatable workflow templates and fixed exception intake",
            "ai_leverage": "cluster workflow breakdowns and summarize recurring handoff failures",
            "external_execution_needed": "none",
            "rough_monetization_model": "monthly subscription",
        }
    ],
    ensure_ascii=False,
)


def run_evaluation(project_root: Path, payload: str) -> tuple[int, str, dict]:
    stdout = io.StringIO()
    with patch.dict("os.environ", {"OOS_AI_IDEATION_RESPONSE_JSON": payload}, clear=False):
        with redirect_stdout(stdout):
            exit_code = main(
                ["evaluate-ai-ideation", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)]
            )
    report_path = project_root / "artifacts" / "evaluation" / "ai_ideation_evaluation.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    return exit_code, stdout.getvalue(), report


class TestAIIdeationEvaluation(unittest.TestCase):
    def test_evaluation_report_is_produced(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            exit_code, output, report = run_evaluation(project_root, VALID_AI_PAYLOAD)

            self.assertEqual(exit_code, 0)
            self.assertIn("OOS AI ideation evaluation completed.", output)
            self.assertTrue((project_root / "artifacts" / "evaluation" / "ai_ideation_evaluation.json").exists())
            self.assertEqual(report["scope"], "ideation_only")
            self.assertEqual(report["opportunity"]["source_signal_ids"], ["sig_real_ops_001", "sig_real_ops_002"])

    def test_assisted_success_path_is_scored_and_reported(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            exit_code, _output, report = run_evaluation(project_root, VALID_AI_PAYLOAD)

            self.assertEqual(exit_code, 0)
            self.assertTrue(report["assisted"]["passed"])
            self.assertEqual(report["assisted"]["score"], report["approval_threshold"])
            self.assertEqual(report["assisted"]["idea_ids"], ["idea_ai_eval_success"])
            self.assertEqual(report["rollback_recommendation"], "assisted_ideation_approved")

    def test_assisted_invalid_output_triggers_rollback_recommendation(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            exit_code, _output, report = run_evaluation(project_root, "not json")

            self.assertEqual(exit_code, 0)
            self.assertFalse(report["assisted"]["passed"])
            self.assertLess(report["assisted"]["score"], report["approval_threshold"])
            self.assertIn("rollback_to_deterministic", report["rollback_recommendation"])
            self.assertTrue(report["assisted"]["error"])

    def test_deterministic_mode_remains_safe_baseline(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            exit_code, _output, report = run_evaluation(project_root, "[]")

            self.assertEqual(exit_code, 0)
            self.assertTrue(report["deterministic"]["passed"])
            self.assertEqual(report["deterministic"]["score"], report["approval_threshold"])
            self.assertGreaterEqual(report["deterministic"]["idea_count"], 1)
            self.assertIn("fallback to deterministic", " ".join(report["rollback_rules"]))


if __name__ == "__main__":
    unittest.main()
