import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_LEDGER = REPO_ROOT / "docs" / "dev_ledger"


class TestDevLedgerStructure(unittest.TestCase):
    def test_dev_ledger_root_and_project_state_exist(self) -> None:
        self.assertTrue(DEV_LEDGER.exists())
        self.assertTrue((DEV_LEDGER / "00_project_state.md").exists())

    def test_required_top_level_folders_exist(self) -> None:
        for folder in [
            "01_decisions",
            "02_mini_epics",
            "03_run_reports",
            "04_known_issues",
            "05_architecture",
            "templates",
        ]:
            with self.subTest(folder=folder):
                self.assertTrue((DEV_LEDGER / folder).is_dir())

    def test_adr_0001_through_0004_exist(self) -> None:
        required_adrs = [
            "ADR-0001-roadmap-v2-2-source-of-truth.md",
            "ADR-0002-heuristic-ideation-as-baseline.md",
            "ADR-0003-no-live-llm-before-provider-boundaries.md",
            "ADR-0004-local-commits-batched-github-push.md",
        ]
        for filename in required_adrs:
            with self.subTest(filename=filename):
                self.assertTrue((DEV_LEDGER / "01_decisions" / filename).exists())

    def test_completed_mini_epic_records_exist_through_4_2(self) -> None:
        required_records = [
            "1.1-evaluation-dataset-v0.md",
            "1.2-ai-contracts-prompt-versioning.md",
            "2.1-pre-clustering-dedup.md",
            "2.2-signal-understanding.md",
            "3.1-semantic-clustering.md",
            "3.2-contradiction-detection.md",
            "4.1-opportunity-framing.md",
            "4.2-opportunity-quality-gate.md",
            "5.1-pattern-guided-ideation.md",
        ]
        for filename in required_records:
            with self.subTest(filename=filename):
                self.assertTrue((DEV_LEDGER / "02_mini_epics" / filename).exists())

    def test_templates_exist(self) -> None:
        for filename in [
            "mini_epic_record_template.md",
            "adr_template.md",
            "run_report_template.md",
        ]:
            with self.subTest(filename=filename):
                self.assertTrue((DEV_LEDGER / "templates" / filename).exists())

    def test_known_issue_docs_exist(self) -> None:
        for filename in [
            "windows-temp-acl.md",
            "codex-sandbox-tempdirectory.md",
        ]:
            with self.subTest(filename=filename):
                self.assertTrue((DEV_LEDGER / "04_known_issues" / filename).exists())

    def test_architecture_docs_exist(self) -> None:
        for filename in [
            "ai-meaning-layer-map.md",
            "artifact-flow.md",
        ]:
            with self.subTest(filename=filename):
                self.assertTrue((DEV_LEDGER / "05_architecture" / filename).exists())

    def test_readme_mentions_dev_ledger(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("Dev Ledger", readme)
        self.assertIn("docs/dev_ledger/", readme)
        self.assertIn("docs/dev_ledger/00_project_state.md", readme)


if __name__ == "__main__":
    unittest.main()
