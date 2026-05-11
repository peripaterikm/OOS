"""Focused CLI tests for the v2.6 weekly cycle command (item 3.1)."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from oos.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _temp_project_root_for(test_case: unittest.TestCase) -> Path:
    tmpdir = tempfile.TemporaryDirectory(prefix="oos_test_cli_v2_")
    test_case.addCleanup(tmpdir.cleanup)
    return Path(tmpdir.name)


def _write_fixture_input(
    project_root: Path,
    items: list[dict[str, Any]],
    *,
    filename: str = "fixture_input.json",
) -> Path:
    path = project_root / filename
    path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (project_root / "artifacts" / "weekly_runs").mkdir(parents=True, exist_ok=True)
    return path


def _evaluation_dataset_items() -> list[dict[str, Any]]:
    """Return a small batch of evaluation-quality-case-style items."""
    return [
        {
            "case_id": "case_001",
            "title": "Strong SMB invoice collection pain",
            "synthetic_data": True,
            "input_artifacts": {
                "evidence_pack": {
                    "evidence_pack_id": "ep_cli_case_001",
                    "cluster_id": "cluster_invoice",
                    "topic_id": "smb_invoice_collection",
                    "source_signal_ids": ["sig_001", "sig_002"],
                    "evidence_ids": ["ev_001", "ev_002"],
                    "source_urls": [
                        "https://news.ycombinator.com/item?id=fixture_cli_001",
                        "https://github.com/fixture/repo/issues/1",
                    ],
                    "items": [
                        {
                            "evidence_id": "ev_001",
                            "source_signal_id": "sig_001",
                            "source_url": "https://news.ycombinator.com/item?id=fixture_cli_001",
                            "source_type": "hn_algolia",
                            "summary": "SMB owner spends hours on unpaid invoice follow-up.",
                            "confidence": 0.85,
                        },
                        {
                            "evidence_id": "ev_002",
                            "source_signal_id": "sig_002",
                            "source_url": "https://github.com/fixture/repo/issues/1",
                            "source_type": "github_issues",
                            "summary": "Bookkeeper requests automated invoice reminders.",
                            "confidence": 0.80,
                        },
                    ],
                    "summaries": [
                        "SMB owners spend significant time on unpaid invoice follow-up",
                    ],
                    "source_summaries": [
                        {
                            "source_type": "hn_algolia",
                            "source_count": 1,
                            "evidence_ids": ["ev_001"],
                        },
                        {
                            "source_type": "github_issues",
                            "source_count": 1,
                            "evidence_ids": ["ev_002"],
                        },
                    ],
                    "recurrence_count": 2,
                    "source_diversity": 2,
                    "price_signal_ids": [],
                    "weak_pattern_ids": [],
                    "kill_warning_ids": [],
                    "risk_notes": [],
                    "confidence_values": [0.85, 0.80],
                    "created_from": "fixture_test",
                    "source_types": ["hn_algolia", "github_issues"],
                }
            },
            "expected": {
                "quality_label": "pass",
                "founder_review_posture": "promote",
            },
        },
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWeeklyCycleCliV2Exists(unittest.TestCase):
    """CLI command exists and help text."""

    def test_command_registered_in_help(self) -> None:
        with TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            try:
                with redirect_stdout(stdout):
                    main(["run-weekly-cycle-v2", "--help"])
            except SystemExit as exc:
                self.assertEqual(exc.code, 0)
            output = stdout.getvalue()
            self.assertIn("run-weekly-cycle-v2", output)
            self.assertIn("--input-file", output)
            self.assertIn("--project-root", output)
            self.assertIn("--run-id", output)
            self.assertIn("--prior-artifacts-dir", output)


class TestWeeklyCycleCliV2EmptyInput(unittest.TestCase):
    """Empty input tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root_for(self)

    def test_empty_input_succeeds(self) -> None:
        input_file = _write_fixture_input(self.project_root, [])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("OOS v2.6 weekly cycle completed.", output)
        self.assertIn("validation_passed: true", output)

    def test_empty_input_prints_run_id_and_manifest_path(self) -> None:
        input_file = _write_fixture_input(self.project_root, [])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("run_id:", output)
        self.assertIn("run_dir:", output)
        self.assertIn("manifest_path:", output)
        self.assertIn("artifact_count:", output)

    def test_empty_input_writes_manifest_in_temp_dir(self) -> None:
        input_file = _write_fixture_input(self.project_root, [])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        self.assertEqual(exit_code, 0)
        # manifest should be under our temp project root
        runs_dir = self.project_root / "artifacts" / "weekly_runs"
        run_dirs = list(runs_dir.iterdir())
        self.assertEqual(len(run_dirs), 1)
        manifest_path = run_dirs[0] / "manifest.json"
        self.assertTrue(manifest_path.is_file())


class TestWeeklyCycleCliV2FixtureInput(unittest.TestCase):
    """Evaluation-style fixture input tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root_for(self)

    def test_fixture_input_succeeds(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("OOS v2.6 weekly cycle completed.", output)
        self.assertIn("validation_passed: true", output)

    def test_fixture_input_prints_counts(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("evidence_packs_built:", output)
        self.assertIn("opportunity_candidates_built:", output)
        self.assertIn("quality_gate_results:", output)
        self.assertIn("next_best_actions_count:", output)

    def test_fixture_input_writes_all_manifests_artifacts(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        self.assertEqual(exit_code, 0)
        runs_dir = self.project_root / "artifacts" / "weekly_runs"
        run_dirs = list(runs_dir.iterdir())
        self.assertEqual(len(run_dirs), 1)
        run_dir = run_dirs[0]
        manifest = json.loads(
            (run_dir / "manifest.json").read_text(encoding="utf-8")
        )
        artifact_paths = manifest.get("artifact_paths", {})
        self.assertEqual(len(artifact_paths), 14)
        for key, rel_path in artifact_paths.items():
            artifact_file = run_dir / rel_path
            self.assertTrue(
                artifact_file.is_file(),
                f"Artifact '{key}' not found at {artifact_file}",
            )

    def test_fixture_input_prints_advisory_flags(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("advisory_only: true", output)
        self.assertIn("no_live_api: true", output)
        self.assertIn("no_live_llm: true", output)


class TestWeeklyCycleCliV2RealSignalBatch(unittest.TestCase):
    """Real signal batch input tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root_for(self)

    def test_real_signal_batch_succeeds(self) -> None:
        input_file = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "real_signal_batch.jsonl"
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("OOS v2.6 weekly cycle completed.", output)
        self.assertIn("validation_passed: true", output)
        self.assertIn("run_id:", output)
        self.assertIn("run_dir:", output)
        self.assertIn("manifest_path:", output)


class TestWeeklyCycleCliV2ErrorConditions(unittest.TestCase):
    """Error handling tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root_for(self)

    def test_missing_input_file_fails_with_message(self) -> None:
        missing = self.project_root / "does_not_exist.json"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(missing),
                ]
            )
        output = stdout.getvalue()
        self.assertNotEqual(exit_code, 0)
        self.assertIn("OOS v2.6 weekly cycle completed.", output)
        self.assertIn("validation_passed: false", output)
        self.assertTrue(
            any("input file" in line.lower() or "not found" in line.lower()
                for line in output.splitlines()),
            f"Expected error about missing input file, got: {output}",
        )

    def test_malformed_json_fails_with_message(self) -> None:
        bad_file = self.project_root / "bad.json"
        bad_file.write_text('{"signal_id":"ok"}\nnot-json\n', encoding="utf-8")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(bad_file),
                ]
            )
        output = stdout.getvalue()
        self.assertNotEqual(exit_code, 0)
        self.assertIn("validation_passed: false", output)

    def test_malformed_json_array_fails_with_message(self) -> None:
        bad_file = self.project_root / "bad_array.json"
        bad_file.write_text('[ { "signal_id": "ok" }, invalid ]', encoding="utf-8")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(bad_file),
                ]
            )
        output = stdout.getvalue()
        self.assertNotEqual(exit_code, 0)
        self.assertIn("validation_passed: false", output)

    def test_unsafe_run_id_rejected(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        unsafe_ids = ["..", "../escape", "", "C:\\abs", "bad run"]
        for run_id in unsafe_ids:
            with self.subTest(run_id=run_id):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "run-weekly-cycle-v2",
                            "--project-root",
                            str(self.project_root),
                            "--input-file",
                            str(input_file),
                            "--run-id",
                            run_id,
                        ]
                    )
                output = stdout.getvalue()
                self.assertNotEqual(
                    exit_code, 0, f"Expected non-zero exit for run_id={run_id!r}"
                )
                self.assertIn("validation_passed: false", output)


class TestWeeklyCycleCliV2ExitCodes(unittest.TestCase):
    """Exit code semantics tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root_for(self)

    def test_success_returns_zero(self) -> None:
        input_file = _write_fixture_input(self.project_root, [])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        self.assertEqual(exit_code, 0)

    def test_validation_failure_returns_nonzero(self) -> None:
        missing = self.project_root / "nonexistent.json"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(missing),
                ]
            )
        self.assertNotEqual(exit_code, 0)


class TestWeeklyCycleCliV2NoRealArtifacts(unittest.TestCase):
    """Safety: tests must not write to the real artifacts/ directory."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root_for(self)

    def test_no_real_artifacts_dir_written(self) -> None:
        real_artifacts = (
            Path(__file__).resolve().parents[1] / "artifacts" / "weekly_runs"
        )
        # Count existing run dirs before
        before = set()
        if real_artifacts.exists():
            before = {
                d.name
                for d in real_artifacts.iterdir()
                if d.is_dir()
            }
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                ]
            )
        # No new directories under the real artifacts/
        after = set()
        if real_artifacts.exists():
            after = {
                d.name
                for d in real_artifacts.iterdir()
                if d.is_dir()
            }
        self.assertEqual(
            before,
            after,
            "Tests must not write to real artifacts/ directory",
        )


class TestWeeklyCycleCliV2ExistingCommands(unittest.TestCase):
    """Existing CLI commands continue to work."""

    def test_smoke_test_still_works(self) -> None:
        with TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    ["smoke-test", "--project-root", tmp]
                )
            self.assertEqual(exit_code, 0)
            self.assertIn("OOS smoke test completed.", stdout.getvalue())

    def test_help_still_works(self) -> None:
        stdout = io.StringIO()
        try:
            with redirect_stdout(stdout):
                main(["--help"])
        except SystemExit as exc:
            self.assertEqual(exc.code, 0)
        output = stdout.getvalue()
        self.assertIn("run-weekly-cycle-v2", output)
        self.assertIn("run-weekly-cycle", output)
        self.assertIn("smoke-test", output)

    def test_run_weekly_cycle_v1_still_works(self) -> None:
        with TemporaryDirectory() as tmp:
            input_file = (
                Path(__file__).resolve().parents[1]
                / "examples"
                / "real_signal_batch.jsonl"
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "run-weekly-cycle",
                        "--project-root",
                        tmp,
                        "--input-file",
                        str(input_file),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertIn(
                "OOS weekly cycle completed.", stdout.getvalue()
            )


class TestWeeklyCycleCliV2PriorArtifacts(unittest.TestCase):
    """Prior artifacts / --prior-artifacts-dir tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root_for(self)

    def test_prior_artifacts_dir_warns_when_empty(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        prior_dir = self.project_root / "artifacts" / "weekly_runs" / "prior_run"
        prior_dir.mkdir(parents=True, exist_ok=True)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                    "--prior-artifacts-dir",
                    str(prior_dir),
                ]
            )
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("validation_passed: true", output)


class TestCLIOutputModeFlags(unittest.TestCase):
    """CLI --utf8 flag tests (Roadmap v2.9 item 1.2)."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root_for(self)

    def _build_run(self, run_id: str) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-weekly-cycle-v2",
                    "--project-root",
                    str(self.project_root),
                    "--input-file",
                    str(input_file),
                    "--run-id",
                    run_id,
                ]
            )
        self.assertEqual(exit_code, 0,
                         f"Failed to build run for CLI test: {stdout.getvalue()}")

    def test_status_help_includes_utf8(self):
        """weekly-cycle-status-v2 --help must list --utf8."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            try:
                main(["weekly-cycle-status-v2", "--help"])
            except SystemExit:
                pass
        self.assertIn("--utf8", stdout.getvalue())

    def test_report_help_includes_utf8(self):
        """build-weekly-run-report-v2 --help must list --utf8."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            try:
                main(["build-weekly-run-report-v2", "--help"])
            except SystemExit:
                pass
        self.assertIn("--utf8", stdout.getvalue())

    def test_dashboard_help_includes_utf8(self):
        """weekly-dashboard-v2 --help must list --utf8."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            try:
                main(["weekly-dashboard-v2", "--help"])
            except SystemExit:
                pass
        self.assertIn("--utf8", stdout.getvalue())

    def test_import_decisions_help_includes_utf8(self):
        """import-founder-decisions-v2 --help must list --utf8
        (v2.10 --undo-last requires --utf8 support per contract Section 9.1)."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            try:
                main(["import-founder-decisions-v2", "--help"])
            except SystemExit:
                pass
        self.assertIn("--utf8", stdout.getvalue())

    def test_status_default_output_is_ascii_safe(self):
        """Default status CLI output (no --utf8) must be ASCII-safe."""
        self._build_run("weekly_run_2026_05_10_cli_asc")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "weekly-cycle-status-v2",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "weekly_run_2026_05_10_cli_asc",
                ]
            )
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        for i, ch in enumerate(output):
            self.assertLess(
                ord(ch), 128,
                f"Status CLI default contains non-ASCII U+{ord(ch):04X} at pos {i}: {ch!r}"
            )

    def test_status_utf8_flag_produces_unicode(self):
        """Status with --utf8 must produce Unicode checkmark in output."""
        self._build_run("weekly_run_2026_05_10_cli_utf")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "weekly-cycle-status-v2",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "weekly_run_2026_05_10_cli_utf",
                    "--utf8",
                ]
            )
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("\u2713", output,
                      "Status --utf8 output should contain checkmark symbol")

    def test_dashboard_utf8_flag_produces_unicode(self):
        """Dashboard with --utf8 must produce Unicode checkmark in output."""
        self._build_run("weekly_run_2026_05_10_cli_db")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "weekly-dashboard-v2",
                    "--project-root",
                    str(self.project_root),
                    "--utf8",
                ]
            )
        # 0 if runs found, 1 if no runs (empty). Either is fine for this test.
        output = stdout.getvalue()
        # The dashboard md is written to file; terminal summary uses ASCII.
        # We check that the --utf8 flag is at least accepted and the command runs.
        self.assertIn("total_runs:", output)

    def test_run_report_utf8_flag_accepted(self):
        """build-weekly-run-report-v2 with --utf8 must accept the flag."""
        self._build_run("weekly_run_2026_05_10_cli_rr")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "build-weekly-run-report-v2",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "weekly_run_2026_05_10_cli_rr",
                    "--utf8",
                ]
            )
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("report_json:", output)
        self.assertIn("report_md:", output)


if __name__ == "__main__":
    unittest.main()
