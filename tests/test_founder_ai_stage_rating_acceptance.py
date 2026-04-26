from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "oos" / "founder_ai_stage_rating.py"
CLI_PATH = ROOT / "src" / "oos" / "cli.py"
ROADMAP_PATH = ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_2_8_weeks_checklist.md"


class TestFounderAIStageRatingAcceptance(unittest.TestCase):
    def test_founder_rating_is_advisory_not_automatic_decision_making(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")

        self.assertIn("advisory_only", source)
        self.assertNotIn("PortfolioStateEnum", source)
        self.assertNotIn("FounderReviewDecisionEnum", source)

    def test_existing_founder_decision_workflow_is_preserved(self) -> None:
        cli_source = CLI_PATH.read_text(encoding="utf-8")

        self.assertIn("record-founder-review", cli_source)
        self.assertIn("record-ai-stage-rating", cli_source)
        self.assertIn("_record_founder_review_by_review_id", cli_source)

    def test_no_live_llm_or_api_calls_are_added(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        forbidden_tokens = [
            "OpenAI(",
            "Anthropic(",
            "requests.post",
            "httpx.post",
            "chat.completions",
            "responses.create",
        ]
        for token in forbidden_tokens:
            self.assertNotIn(token, source)

    def test_active_roadmap_has_7_2_in_progress_or_completed(self) -> None:
        text = ROADMAP_PATH.read_text(encoding="utf-8")

        self.assertRegex(text, r"## 7\.2\. Founder rating by AI stage \+ evaluation dataset v1 expansion")
        self.assertRegex(text, r"Current item: \*\*(7\.2|8\.1|8\.2|Completed / final milestone state)\*\*")

        completed_match = re.search(r"Completed from this roadmap: \*\*(\d+) / 16\*\*", text)
        remaining_match = re.search(r"Remaining: \*\*(\d+) / 16\*\*", text)
        self.assertIsNotNone(completed_match)
        self.assertIsNotNone(remaining_match)
        self.assertGreaterEqual(int(completed_match.group(1)), 13)
        self.assertLessEqual(int(remaining_match.group(1)), 3)

    def test_milestone_g_is_not_required_unless_roadmap_defines_it(self) -> None:
        text = ROADMAP_PATH.read_text(encoding="utf-8")
        if "Milestone G" in text:
            completed_match = re.search(r"Completed from this roadmap: \*\*(\d+) / 16\*\*", text)
            self.assertIsNotNone(completed_match)
            if int(completed_match.group(1)) >= 14:
                self.assertRegex(
                    text,
                    r"- \[x\] \*\*9\.7\*\* Milestone G: Founder review and AI quality feedback operational after \*\*7\.2\*\*",
                )


if __name__ == "__main__":
    unittest.main()
