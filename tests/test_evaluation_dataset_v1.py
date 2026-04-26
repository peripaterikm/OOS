from __future__ import annotations

import unittest
from pathlib import Path

from oos.evaluation_dataset import EVALUATION_DATASET_V1_DIR, load_evaluation_dataset_v1


class TestEvaluationDatasetV1(unittest.TestCase):
    def test_evaluation_dataset_v1_exists(self) -> None:
        self.assertTrue(EVALUATION_DATASET_V1_DIR.exists())
        self.assertTrue((EVALUATION_DATASET_V1_DIR / "signals.json").exists())

    def test_dataset_v1_can_be_loaded(self) -> None:
        signals = load_evaluation_dataset_v1()

        self.assertGreaterEqual(len(signals), 20)
        self.assertLessEqual(len(signals), 30)

    def test_synthetic_cases_are_explicitly_labeled(self) -> None:
        signals = load_evaluation_dataset_v1()

        synthetic_signals = [signal for signal in signals if signal.get("synthetic") is True]

        self.assertEqual(len(signals), len(synthetic_signals))

    def test_expected_notes_files_exist(self) -> None:
        expected_files = [
            "expected_clusters.md",
            "expected_opportunities.md",
            "expected_idea_quality_notes.md",
            "founder_quality_notes.md",
        ]
        for filename in expected_files:
            self.assertTrue((EVALUATION_DATASET_V1_DIR / filename).exists(), filename)

    def test_dataset_v1_targets_expected_cluster_opportunity_and_idea_counts(self) -> None:
        clusters = (EVALUATION_DATASET_V1_DIR / "expected_clusters.md").read_text(encoding="utf-8")
        opportunities = (EVALUATION_DATASET_V1_DIR / "expected_opportunities.md").read_text(encoding="utf-8")
        idea_notes = (EVALUATION_DATASET_V1_DIR / "expected_idea_quality_notes.md").read_text(encoding="utf-8")

        self.assertIn("5-8 semantic clusters", clusters)
        self.assertIn("5 opportunity cards", opportunities)
        self.assertIn("15-25 idea variants", idea_notes)

    def test_dataset_v1_preserves_edge_and_quality_cases(self) -> None:
        signals = load_evaluation_dataset_v1()
        tags = {tag for signal in signals for tag in signal.get("edge_case_tags", [])}

        self.assertIn("ambiguous", tags)
        self.assertIn("near_duplicate", tags)
        self.assertIn("weak_noisy", tags)
        self.assertIn("unclear_buyer", tags)


if __name__ == "__main__":
    unittest.main()
