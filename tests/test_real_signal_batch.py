import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main
from oos.real_signal_batch import CanonicalSignalBatchLoader


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "examples" / "real_signal_batch.jsonl"


class TestRealSignalBatch(unittest.TestCase):
    def test_valid_jsonl_batch_is_accepted(self) -> None:
        items = CanonicalSignalBatchLoader().load(FIXTURE_PATH)

        self.assertEqual([item.signal_id for item in items], ["sig_real_ops_001", "sig_real_ops_002"])
        self.assertEqual(items[0].source_ref, "interview-ops-2026-04-20-a")

    def test_missing_required_field_is_rejected_with_actionable_message(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            project_root.mkdir()
            input_file = Path(tmp) / "missing_field.jsonl"
            input_file.write_text(
                json.dumps(
                    {
                        "signal_id": "sig_missing_text",
                        "captured_at": "2026-04-20T09:15:00+00:00",
                        "source_type": "customer_interview",
                        "title": "Missing text field",
                        "source_ref": "interview-missing-text",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    ["run-signal-batch", "--project-root", str(project_root), "--input-file", str(input_file)]
                )

            self.assertEqual(exit_code, 2)
            self.assertIn("Invalid signal batch: line 1 missing required field 'text'", stdout.getvalue())
            self.assertFalse((project_root / "artifacts").exists())

    def test_run_signal_batch_writes_signal_artifacts_from_input_file(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    ["run-signal-batch", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("OOS signal batch run completed.", stdout.getvalue())
            artifacts_dir = project_root / "artifacts"
            first_signal = json.loads((artifacts_dir / "signals" / "sig_real_ops_001.json").read_text(encoding="utf-8"))
            second_signal = json.loads((artifacts_dir / "signals" / "sig_real_ops_002.json").read_text(encoding="utf-8"))
            self.assertEqual(first_signal["id"], "sig_real_ops_001")
            self.assertEqual(second_signal["id"], "sig_real_ops_002")
            self.assertEqual(first_signal["metadata"]["source_ref"], "interview-ops-2026-04-20-a")
            self.assertEqual(second_signal["metadata"]["source_ref"], "ticket-finance-1842")

    def test_run_signal_batch_produces_end_to_end_outputs_from_fixture_batch(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    ["run-signal-batch", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)]
                )

            self.assertEqual(exit_code, 0)
            artifacts_dir = project_root / "artifacts"
            self.assertTrue((artifacts_dir / "opportunities" / "opp_batch_1.json").exists())
            self.assertTrue(any((artifacts_dir / "ideas").glob("*.json")))
            self.assertTrue(any((artifacts_dir / "hypotheses").glob("*.json")))
            self.assertTrue(any((artifacts_dir / "experiments").glob("*.json")))
            self.assertTrue(any((artifacts_dir / "council").glob("*.json")))
            self.assertTrue((artifacts_dir / "portfolio" / "ps_opp_batch_1.json").exists())
            self.assertTrue(any((artifacts_dir / "weekly_reviews").glob("weekly_review_*.json")))
            self.assertTrue(any((artifacts_dir / "readiness").glob("v1_readiness_*.json")))

    def test_produced_artifacts_trace_to_input_signal_ids_and_references(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    ["run-signal-batch", "--project-root", str(project_root), "--input-file", str(FIXTURE_PATH)]
                )

            self.assertEqual(exit_code, 0)
            artifacts_dir = project_root / "artifacts"
            opportunity = json.loads((artifacts_dir / "opportunities" / "opp_batch_1.json").read_text(encoding="utf-8"))
            readiness_path = next((artifacts_dir / "readiness").glob("v1_readiness_*.json"))
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))

            self.assertEqual(opportunity["source_signal_ids"], ["sig_real_ops_001", "sig_real_ops_002"])
            self.assertEqual(readiness["artifacts_written"]["signals"], ["sig_real_ops_001", "sig_real_ops_002"])
            self.assertEqual(
                readiness["artifacts_written"]["validated_signals"], ["sig_real_ops_001", "sig_real_ops_002"]
            )
            for idea_id in readiness["artifacts_written"]["ideas"]:
                idea = json.loads((artifacts_dir / "ideas" / f"{idea_id}.json").read_text(encoding="utf-8"))
                self.assertEqual(idea["opportunity_id"], "opp_batch_1")


if __name__ == "__main__":
    unittest.main()
