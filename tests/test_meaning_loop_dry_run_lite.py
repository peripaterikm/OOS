import io
import json
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from oos.cli import main
from oos.meaning_loop_adapter import adapt_candidate_signal, adapt_candidate_signals
from oos.models import CandidateSignal


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "examples" / "source_intelligence_mvp" / "raw_evidence_seed.json"


class TestMeaningLoopDryRunLite(unittest.TestCase):
    def setUp(self) -> None:
        self.project_root = ROOT / "codex_tmp_meaning_loop_dry_run_lite"
        if self.project_root.exists():
            shutil.rmtree(self.project_root)
        (self.project_root / "examples" / "source_intelligence_mvp").mkdir(parents=True)
        shutil.copy2(FIXTURE_PATH, self.project_root / "examples" / "source_intelligence_mvp" / "raw_evidence_seed.json")

    def tearDown(self) -> None:
        if self.project_root.exists():
            shutil.rmtree(self.project_root)

    def test_adapter_preserves_evidence_source_topic_and_query_traceability(self) -> None:
        signal = self._candidate_signal()

        adapted = adapt_candidate_signal(signal)

        self.assertEqual(adapted.candidate_signal_id, signal.signal_id)
        self.assertEqual(adapted.metadata["evidence_id"], signal.evidence_id)
        self.assertEqual(adapted.metadata["source_url"], signal.source_url)
        self.assertEqual(adapted.metadata["source_id"], signal.source_id)
        self.assertEqual(adapted.metadata["topic_id"], signal.topic_id)
        self.assertEqual(adapted.metadata["query_kind"], signal.query_kind)

    def test_adapter_produces_deterministic_meaning_loop_compatible_records(self) -> None:
        signal = self._candidate_signal()

        first = adapt_candidate_signals([signal])[0].to_dict()
        second = adapt_candidate_signals([signal])[0].to_dict()

        self.assertEqual(first, second)
        self.assertEqual(first["captured_at"], "deterministic_mvp_lite")
        self.assertEqual(
            set(adapt_candidate_signal(signal).to_canonical_signal_jsonl_record()),
            {"signal_id", "captured_at", "source_type", "title", "text", "source_ref"},
        )

    def test_cli_with_flag_writes_meaning_loop_dry_run_json(self) -> None:
        self._run_cli("meaning_json", "--include-meaning-loop-dry-run")

        self.assertTrue((self._run_dir("meaning_json") / "meaning_loop_dry_run.json").exists())

    def test_cli_with_flag_writes_meaning_loop_dry_run_markdown(self) -> None:
        self._run_cli("meaning_md", "--include-meaning-loop-dry-run")

        self.assertTrue((self._run_dir("meaning_md") / "meaning_loop_dry_run.md").exists())

    def test_dry_run_json_includes_signal_and_adapted_counts(self) -> None:
        self._run_cli("meaning_counts", "--include-meaning-loop-dry-run")
        report = self._read_json("meaning_counts", "meaning_loop_dry_run.json")

        self.assertEqual(report["candidate_signal_count"], 5)
        self.assertEqual(report["adapted_record_count"], 5)

    def test_dry_run_json_includes_compatibility_status(self) -> None:
        self._run_cli("meaning_status", "--include-meaning-loop-dry-run")
        report = self._read_json("meaning_status", "meaning_loop_dry_run.json")

        self.assertEqual(report["compatibility_status"], "adapter_only")

    def test_dry_run_json_includes_traceability_map(self) -> None:
        self._run_cli("meaning_trace", "--include-meaning-loop-dry-run")
        report = self._read_json("meaning_trace", "meaning_loop_dry_run.json")

        self.assertEqual(len(report["traceability_map"]), 5)
        for trace in report["traceability_map"].values():
            self.assertTrue(trace["evidence_id"])
            self.assertTrue(trace["source_url"].startswith("http"))
            self.assertEqual(trace["topic_id"], "ai_cfo_smb")
            self.assertTrue(trace["query_kind"])

    def test_dry_run_markdown_includes_required_sections(self) -> None:
        self._run_cli("meaning_sections", "--include-meaning-loop-dry-run")
        markdown = (self._run_dir("meaning_sections") / "meaning_loop_dry_run.md").read_text(encoding="utf-8")

        self.assertIn("## Summary", markdown)
        self.assertIn("## Traceability", markdown)
        self.assertIn("## Limitations", markdown)
        self.assertIn("## Recommended next steps", markdown)

    def test_default_cli_without_flag_still_works_and_skips_dry_run_outputs(self) -> None:
        result = self._run_cli("meaning_default")

        self.assertEqual(result, 0)
        self.assertTrue((self._run_dir("meaning_default") / "founder_discovery_package.json").exists())
        self.assertFalse((self._run_dir("meaning_default") / "meaning_loop_dry_run.json").exists())

    def test_no_internet_api_or_llm_calls_required(self) -> None:
        self._run_cli("meaning_no_live", "--include-meaning-loop-dry-run")
        report = self._read_json("meaning_no_live", "meaning_loop_dry_run.json")

        self.assertIn("No live network, API, or LLM calls are made.", report["notes"])

    def test_empty_zero_signal_run_produces_safe_dry_run_output(self) -> None:
        empty_input = self.project_root / "empty_raw_evidence.json"
        empty_input.write_text(json.dumps({"raw_evidence": []}, indent=2), encoding="utf-8")

        self._run_cli(
            "meaning_empty",
            "--include-meaning-loop-dry-run",
            "--input-raw-evidence",
            str(empty_input),
        )
        report = self._read_json("meaning_empty", "meaning_loop_dry_run.json")
        markdown = (self._run_dir("meaning_empty") / "meaning_loop_dry_run.md").read_text(encoding="utf-8")

        self.assertEqual(report["candidate_signal_count"], 0)
        self.assertEqual(report["adapted_record_count"], 0)
        self.assertEqual(report["traceability_map"], {})
        self.assertIn("No candidate signals were available to adapt.", markdown)

    def test_adapter_only_status_clearly_reports_no_downstream_artifacts(self) -> None:
        self._run_cli("meaning_adapter_only", "--include-meaning-loop-dry-run")
        report = self._read_json("meaning_adapter_only", "meaning_loop_dry_run.json")

        self.assertEqual(report["compatibility_status"], "adapter_only")
        self.assertEqual(report["downstream_artifacts_created"], [])
        self.assertGreaterEqual(len(report["next_integration_targets"]), 1)

    def test_existing_discovery_package_outputs_still_pass_with_flag(self) -> None:
        self._run_cli("meaning_package", "--include-meaning-loop-dry-run")

        self.assertTrue((self._run_dir("meaning_package") / "founder_discovery_package.json").exists())
        self.assertTrue((self._run_dir("meaning_package") / "discovery_run_summary.json").exists())

    def test_traceability_chain_candidate_signal_to_evidence_to_source_url_is_visible(self) -> None:
        self._run_cli("meaning_chain", "--include-meaning-loop-dry-run")
        markdown = (self._run_dir("meaning_chain") / "meaning_loop_dry_run.md").read_text(encoding="utf-8")

        self.assertIn("->", markdown)
        self.assertIn("https://", markdown)

    def _run_cli(self, run_id: str, *extra_args: str) -> int:
        output = io.StringIO()
        with redirect_stdout(output):
            return main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    run_id,
                    *extra_args,
                ]
            )

    def _run_dir(self, run_id: str) -> Path:
        return self.project_root / "artifacts" / "discovery_runs" / run_id

    def _read_json(self, run_id: str, filename: str):
        return json.loads((self._run_dir(run_id) / filename).read_text(encoding="utf-8"))

    def _candidate_signal(self) -> CandidateSignal:
        signal = CandidateSignal(
            signal_id="candidate_signal_raw_github_001_pain_signal_candidate",
            evidence_id="raw_github_001",
            source_id="src_github_issues",
            source_type="github_issues",
            source_url="https://github.com/example/project/issues/123",
            topic_id="ai_cfo_smb",
            query_kind="pain_query",
            signal_type="pain_signal",
            pain_summary="Developers cannot trust finance webhook retries.",
            target_user="developer",
            current_workaround="manual spreadsheet retry tracking",
            buying_intent_hint="possible",
            urgency_hint="high",
            confidence=0.72,
            measurement_methods={
                "signal_type": "rule_based",
                "pain_summary": "rule_based",
                "target_user": "rule_based",
                "current_workaround": "rule_based",
                "buying_intent_hint": "rule_based",
                "urgency_hint": "rule_based",
                "confidence": "rule_based",
            },
            extraction_mode="rule_based_v1",
            classification="pain_signal_candidate",
            classification_confidence=0.75,
            traceability={
                "evidence_id": "raw_github_001",
                "source_url": "https://github.com/example/project/issues/123",
                "source_id": "src_github_issues",
                "topic_id": "ai_cfo_smb",
                "query_kind": "pain_query",
            },
        )
        signal.validate()
        return signal


if __name__ == "__main__":
    unittest.main()
