import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = REPO_ROOT / "docs" / "dev_ledger" / "operations"


class TestAutonomousWorkflowDocs(unittest.TestCase):
    def test_operations_directory_exists(self) -> None:
        self.assertTrue(OPERATIONS.is_dir())

    def test_required_operation_docs_exist(self) -> None:
        required_docs = [
            "codex_autonomous_protocol.md",
            "autonomous_phase_prompt_template.md",
            "stop_conditions.md",
            "commit_policy.md",
            "validation_policy.md",
            "permissions_policy.md",
        ]
        for filename in required_docs:
            with self.subTest(filename=filename):
                self.assertTrue((OPERATIONS / filename).exists())

    def test_autonomous_phase_prompt_template_exists(self) -> None:
        self.assertTrue((OPERATIONS / "autonomous_phase_prompt_template.md").exists())

    def test_helper_scripts_exist(self) -> None:
        self.assertTrue((REPO_ROOT / "scripts" / "oos-validate.ps1").exists())
        self.assertTrue((REPO_ROOT / "scripts" / "oos-status.ps1").exists())

    def test_readme_mentions_autonomous_codex_workflow(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("Autonomous Codex workflow", readme)
        self.assertIn("docs/dev_ledger/operations/", readme)
        self.assertIn(".\\scripts\\oos-status.ps1", readme)
        self.assertIn(".\\scripts\\oos-validate.ps1", readme)

    def test_dev_ledger_has_support_b_record(self) -> None:
        self.assertTrue(
            (
                REPO_ROOT
                / "docs"
                / "dev_ledger"
                / "02_mini_epics"
                / "support-b-autonomous-codex-workflow.md"
            ).exists()
        )

    def test_operation_docs_mention_no_push_without_explicit_approval(self) -> None:
        combined = self._combined_operations_text()

        self.assertIn("No push unless explicitly requested", combined)
        self.assertIn("Do not push unless explicitly requested", combined)

    def test_operation_docs_mention_stop_conditions(self) -> None:
        combined = self._combined_operations_text()

        self.assertIn("Stop Conditions", combined)
        self.assertIn("tests fail after 2 repair attempts", combined)

    def test_operation_docs_mention_local_commits_after_green_validation(self) -> None:
        combined = self._combined_operations_text()

        self.assertIn("local commit", combined)
        self.assertIn("green validation", combined)

    def _combined_operations_text(self) -> str:
        return "\n".join(path.read_text(encoding="utf-8") for path in OPERATIONS.glob("*.md"))


if __name__ == "__main__":
    unittest.main()
