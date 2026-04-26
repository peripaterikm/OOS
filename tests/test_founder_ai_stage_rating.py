from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main
from oos.founder_ai_stage_rating import (
    ALLOWED_AI_RATING_STAGES,
    ALLOWED_AI_STAGE_RATINGS,
    FounderAIStageRating,
    load_ai_stage_ratings,
    record_ai_stage_rating,
)
from oos.founder_review_package import FounderReviewEntry, FounderReviewPackageWriter
from oos.weekly_review import WeeklyReviewGenerator


class TestFounderAIStageRating(unittest.TestCase):
    def test_valid_ratings_are_accepted(self) -> None:
        for rating in ALLOWED_AI_STAGE_RATINGS:
            artifact = FounderAIStageRating(
                rating_id=f"rating-{rating}",
                stage="ideation",
                rating=rating,
                explanation="Founder reviewed the stage output.",
                linked_artifact_ids=["ideas/idea-1.json"],
            )
            artifact.validate()

    def test_invalid_ratings_are_rejected(self) -> None:
        artifact = FounderAIStageRating(
            rating_id="rating-bad",
            stage="ideation",
            rating="great",
            explanation="Invalid rating.",
            linked_artifact_ids=["ideas/idea-1.json"],
        )
        with self.assertRaises(ValueError):
            artifact.validate()

    def test_valid_stages_are_accepted(self) -> None:
        for stage in ALLOWED_AI_RATING_STAGES:
            FounderAIStageRating(
                rating_id=f"rating-{stage.replace(' ', '-')}",
                stage=stage,
                rating="okay",
                explanation="Founder reviewed the stage output.",
                linked_artifact_ids=["artifact.json"],
            ).validate()

    def test_invalid_stages_are_rejected(self) -> None:
        artifact = FounderAIStageRating(
            rating_id="rating-bad-stage",
            stage="pricing",
            rating="okay",
            explanation="Invalid stage.",
            linked_artifact_ids=["artifact.json"],
        )
        with self.assertRaises(ValueError):
            artifact.validate()

    def test_ratings_preserve_linked_artifact_and_signal_ids(self) -> None:
        artifact = FounderAIStageRating(
            rating_id="rating-links",
            stage="signal understanding",
            rating="good",
            explanation="Extraction matched the source signal.",
            linked_artifact_ids=["signal_understanding/su-1.json"],
            linked_signal_ids=["sig-1", "sig-2"],
        )

        payload = artifact.to_dict()

        self.assertEqual(["signal_understanding/su-1.json"], payload["linked_artifact_ids"])
        self.assertEqual(["sig-1", "sig-2"], payload["linked_signal_ids"])

    def test_rating_artifacts_can_be_serialized_and_loaded(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            path = record_ai_stage_rating(
                project_root=project_root,
                stage="clustering",
                rating="weak",
                explanation="Cluster split one recurring pain into two groups.",
                linked_artifact_ids=["semantic_clusters/cluster-report.json"],
                linked_signal_ids=["sig-1"],
                rating_id="rating-001",
                created_at="2026-04-26T10:00:00+00:00",
            )

            payload = json.loads(path.read_text(encoding="utf-8"))
            loaded = load_ai_stage_ratings(project_root / "artifacts")

            self.assertEqual("rating-001", payload["rating_id"])
            self.assertEqual("clustering", loaded[0].stage)
            self.assertTrue(loaded[0].advisory_only)

    def test_cli_records_rating(self) -> None:
        with TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "record-ai-stage-rating",
                        "--project-root",
                        tmp,
                        "--stage",
                        "opportunity framing",
                        "--rating",
                        "okay",
                        "--explanation",
                        "Evidence was useful but assumptions needed review.",
                        "--linked-artifact-id",
                        "opportunities/opp-1.json",
                        "--linked-signal-id",
                        "sig-1",
                        "--rating-id",
                        "rating-cli-001",
                        "--created-at",
                        "2026-04-26T11:00:00+00:00",
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("Founder AI-stage rating recorded.", stdout.getvalue())
            path = Path(tmp) / "artifacts" / "ai_stage_ratings" / "rating-cli-001.json"
            self.assertTrue(path.exists())

    def test_founder_review_package_v2_includes_ratings(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            artifacts = project_root / "artifacts"
            record_ai_stage_rating(
                project_root=project_root,
                stage="critique",
                rating="wrong",
                explanation="Critique missed the main buyer risk.",
                linked_artifact_ids=["critiques/critique-1.json"],
                rating_id="rating-package-001",
                created_at="2026-04-26T12:00:00+00:00",
            )
            FounderReviewPackageWriter(artifacts_root=artifacts).write(
                entries=[
                    FounderReviewEntry(
                        review_id="review-001",
                        entity_type="opportunity",
                        entity_id="opp-1",
                        title="Review opportunity",
                        summary="Review package",
                        decision_options=["pass", "park", "kill"],
                        linked_signal_ids=[],
                        linked_artifact_ids={"opportunity": "opp-1"},
                    )
                ],
                project_root=project_root,
            )

            section = (artifacts / "founder_review" / "sections" / "ai_quality.md").read_text(encoding="utf-8")

            self.assertIn("rating-package-001.json", section)

    def test_weekly_summary_includes_ai_stage_ratings(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            record_ai_stage_rating(
                project_root=project_root,
                stage="ideation",
                rating="good",
                explanation="Ideas were traceable and specific.",
                linked_artifact_ids=["ideas/idea-1.json"],
                rating_id="rating-weekly-001",
                created_at="2026-04-26T13:00:00+00:00",
            )

            weekly_path = WeeklyReviewGenerator(artifacts_root=project_root / "artifacts").generate()
            payload = json.loads(weekly_path.read_text(encoding="utf-8"))

            self.assertEqual("rating-weekly-001", payload["recent_ai_stage_ratings"][0]["rating_id"])
            self.assertTrue(payload["recent_ai_stage_ratings"][0]["advisory_only"])


if __name__ == "__main__":
    unittest.main()
