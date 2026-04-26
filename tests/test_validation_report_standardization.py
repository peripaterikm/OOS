from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_POLICY = ROOT / "docs" / "dev_ledger" / "operations" / "validation_policy.md"
AUTONOMOUS_PROTOCOL = ROOT / "docs" / "dev_ledger" / "operations" / "codex_autonomous_protocol.md"
HELPER_SCRIPT = ROOT / "scripts" / "oos-validation-report.ps1"
RUN_REPORT = ROOT / "docs" / "dev_ledger" / "03_run_reports" / "1.2-run-report-validation-standardization.md"


class TestValidationReportStandardization(unittest.TestCase):
    def test_validation_policy_defines_file_based_evidence(self) -> None:
        source = VALIDATION_POLICY.read_text(encoding="utf-8")

        self.assertIn("docs/dev_ledger/03_run_reports/<roadmap-item-slug>-validation.md", source)
        self.assertIn("command", source)
        self.assertIn("working directory", source)
        self.assertIn("result: `pass`, `fail`, or `blocked`", source)
        self.assertIn("do not invent success", source)
        self.assertIn("Manual validation is a fallback only", source)

    def test_validation_policy_lists_required_commands(self) -> None:
        source = VALIDATION_POLICY.read_text(encoding="utf-8")

        self.assertIn("unittest discover", source)
        self.assertIn(".\\scripts\\oos-validate.ps1", source)
        self.assertIn(".\\scripts\\verify.ps1", source)
        self.assertIn("git diff --check", source)

    def test_autonomous_protocol_requires_codex_written_run_reports(self) -> None:
        source = AUTONOMOUS_PROTOCOL.read_text(encoding="utf-8")

        self.assertIn("Codex should write run reports itself", source)
        self.assertIn("should not ask the user to manually run validation unless blocked", source)
        self.assertIn("Codex can push/open a PR only when explicitly authorized", source)

    def test_validation_report_helper_exists_and_uses_windows_native_commands(self) -> None:
        self.assertTrue(HELPER_SCRIPT.exists())
        source = HELPER_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("param(", source)
        self.assertIn("ReportPath", source)
        self.assertIn("Tee-Object", source)
        self.assertIn("oos-validate.ps1", source)
        self.assertIn("verify.ps1", source)
        self.assertIn("git diff --check", source)

    def test_item_run_report_exists_with_required_sections(self) -> None:
        self.assertTrue(RUN_REPORT.exists())
        source = RUN_REPORT.read_text(encoding="utf-8")

        self.assertIn("Roadmap Item", source)
        self.assertIn("Commands Run", source)
        self.assertIn("Results Summary", source)
        self.assertIn("Blocked Commands", source)
        self.assertIn("Known Warnings", source)
        self.assertIn("No push performed", source)


if __name__ == "__main__":
    unittest.main()
