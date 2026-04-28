import io
import json
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from oos.cli import build_arg_parser, main


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "examples" / "source_intelligence_mvp" / "raw_evidence_seed.json"


class TestDiscoveryWeeklyCli(unittest.TestCase):
    def setUp(self) -> None:
        self.project_root = ROOT / "codex_tmp_discovery_weekly_cli"
        if self.project_root.exists():
            shutil.rmtree(self.project_root)
        (self.project_root / "examples" / "source_intelligence_mvp").mkdir(parents=True)
        shutil.copy2(FIXTURE_PATH, self.project_root / "examples" / "source_intelligence_mvp" / "raw_evidence_seed.json")

    def tearDown(self) -> None:
        if self.project_root.exists():
            shutil.rmtree(self.project_root)

    def test_cli_command_exists_and_runs_in_default_fixture_mode(self) -> None:
        result = self._run_cli("--run-id", "weekly_fixture_default")

        self.assertEqual(result, 0)
        self.assertTrue(self._run_dir("weekly_fixture_default").exists())

    def test_cli_accepts_ai_cfo_smb_topic(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "weekly_topic",
                ]
            )

        self.assertEqual(result, 0)
        self.assertIn("run_id: weekly_topic", output.getvalue())

    def test_cli_writes_discovery_run_directory(self) -> None:
        self._run_cli("--run-id", "weekly_directory")

        self.assertEqual(self._run_dir("weekly_directory"), self.project_root / "artifacts" / "discovery_runs" / "weekly_directory")

    def test_cli_writes_raw_evidence_index(self) -> None:
        self._run_cli("--run-id", "weekly_raw")

        self.assertTrue((self._run_dir("weekly_raw") / "raw_evidence_index.json").exists())

    def test_cli_writes_cleaned_evidence(self) -> None:
        self._run_cli("--run-id", "weekly_cleaned")

        self.assertTrue((self._run_dir("weekly_cleaned") / "cleaned_evidence.json").exists())

    def test_cli_writes_evidence_classifications(self) -> None:
        self._run_cli("--run-id", "weekly_classifications")

        self.assertTrue((self._run_dir("weekly_classifications") / "evidence_classifications.json").exists())

    def test_cli_writes_candidate_signals(self) -> None:
        self._run_cli("--run-id", "weekly_signals")

        self.assertTrue((self._run_dir("weekly_signals") / "candidate_signals.json").exists())

    def test_cli_writes_summary_json(self) -> None:
        self._run_cli("--run-id", "weekly_summary_json")

        self.assertTrue((self._run_dir("weekly_summary_json") / "discovery_run_summary.json").exists())

    def test_cli_writes_summary_markdown(self) -> None:
        self._run_cli("--run-id", "weekly_summary_md")

        summary = (self._run_dir("weekly_summary_md") / "discovery_run_summary.md").read_text(encoding="utf-8")
        self.assertIn("Discovery Run Summary - MVP CLI Lite", summary)
        self.assertIn("not the final founder discovery package", summary)

    def test_summary_counts_are_correct_for_fixture_input(self) -> None:
        self._run_cli("--run-id", "weekly_counts")
        summary = self._read_summary("weekly_counts")

        self.assertEqual(summary["raw_evidence_count"], 5)
        self.assertEqual(summary["cleaned_evidence_count"], 5)
        self.assertEqual(summary["classification_count"], 5)
        self.assertEqual(summary["candidate_signal_count"], 5)
        self.assertEqual(summary["needs_human_review_count"], 1)
        self.assertEqual(summary["noise_count"], 0)
        self.assertEqual(summary["counts_by_source_type"]["github_issues"], 2)
        self.assertEqual(summary["counts_by_signal_type"]["needs_human_review"], 1)

    def test_candidate_signal_traceability_is_preserved(self) -> None:
        self._run_cli("--run-id", "weekly_traceability")
        signals = self._read_json("weekly_traceability", "candidate_signals.json")

        for signal in signals:
            self.assertTrue(signal["evidence_id"])
            self.assertTrue(signal["source_url"].startswith("http"))
            self.assertEqual(signal["traceability"]["evidence_id"], signal["evidence_id"])
            self.assertEqual(signal["traceability"]["source_url"], signal["source_url"])
            self.assertEqual(signal["traceability"]["source_id"], signal["source_id"])
            self.assertEqual(signal["traceability"]["topic_id"], signal["topic_id"])
            self.assertEqual(signal["traceability"]["query_kind"], signal["query_kind"])

    def test_no_live_network_api_or_llm_calls_required(self) -> None:
        self._run_cli("--run-id", "weekly_no_live")
        summary = self._read_summary("weekly_no_live")

        self.assertFalse(summary["live_network_enabled"])
        self.assertEqual(summary["mode"], "mvp_cli_lite_offline")
        self.assertIn("No live network, API, or LLM calls are made.", summary["notes"])

    def test_rerunning_same_run_id_is_deterministic(self) -> None:
        self._run_cli("--run-id", "weekly_repeat")
        first_summary = self._read_summary("weekly_repeat")
        first_signals = self._read_json("weekly_repeat", "candidate_signals.json")

        self._run_cli("--run-id", "weekly_repeat")
        second_summary = self._read_summary("weekly_repeat")
        second_signals = self._read_json("weekly_repeat", "candidate_signals.json")

        self.assertEqual(first_summary, second_summary)
        self.assertEqual(first_signals, second_signals)

    def test_invalid_unknown_topic_fails_gracefully(self) -> None:
        result = self._run_cli("--topic", "unknown_topic", "--run-id", "weekly_bad_topic")

        self.assertEqual(result, 2)
        self.assertFalse(self._run_dir("weekly_bad_topic").exists())

    def test_empty_input_produces_valid_zero_signal_run(self) -> None:
        empty_input = self.project_root / "empty_raw_evidence.json"
        empty_input.write_text(json.dumps({"raw_evidence": []}, indent=2), encoding="utf-8")

        result = self._run_cli(
            "--run-id",
            "weekly_empty",
            "--input-raw-evidence",
            str(empty_input),
        )
        summary = self._read_summary("weekly_empty")

        self.assertEqual(result, 0)
        self.assertEqual(summary["raw_evidence_count"], 0)
        self.assertEqual(summary["candidate_signal_count"], 0)
        self.assertEqual(self._read_json("weekly_empty", "candidate_signals.json"), [])

    def test_existing_cli_commands_are_not_broken(self) -> None:
        parser = build_arg_parser()
        args = parser.parse_args(["smoke-test", "--project-root", str(self.project_root)])

        self.assertEqual(args.command, "smoke-test")

    def _run_cli(self, *extra_args: str) -> int:
        args = [
            "run-discovery-weekly",
            "--topic",
            "ai_cfo_smb",
            "--project-root",
            str(self.project_root),
            *extra_args,
        ]
        output = io.StringIO()
        with redirect_stdout(output):
            return main(args)

    def _run_dir(self, run_id: str) -> Path:
        return self.project_root / "artifacts" / "discovery_runs" / run_id

    def _read_json(self, run_id: str, filename: str):
        return json.loads((self._run_dir(run_id) / filename).read_text(encoding="utf-8"))

    def _read_summary(self, run_id: str):
        return self._read_json(run_id, "discovery_run_summary.json")


if __name__ == "__main__":
    unittest.main()
