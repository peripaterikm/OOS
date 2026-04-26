from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "oos" / "founder_review_package.py"
ROADMAP_PATH = ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_2_8_weeks_checklist.md"


class TestFounderReviewPackageV2Acceptance(unittest.TestCase):
    def test_package_v2_structure_matches_roadmap(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")

        self.assertIn('self.review_dir = artifacts_root / "founder_review"', source)
        self.assertIn('self.sections_dir = self.review_dir / "sections"', source)
        for section in (
            "signals",
            "dedup",
            "clusters",
            "opportunities",
            "ideas",
            "anti_patterns",
            "critiques",
            "decisions",
            "ai_quality",
        ):
            self.assertIn(f'"{section}"', source)

    def test_module_contains_no_live_llm_or_api_calls(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")

        for token in ("OpenAI(", "Anthropic(", "requests.post", "httpx.post", "chat.completions", "responses.create"):
            self.assertNotIn(token, source)

    def test_existing_founder_decision_workflow_is_preserved(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")

        self.assertIn("founder_review_index.json", source)
        self.assertIn("FounderReviewIndex", source)
        self.assertIn("get_entry", source)
        self.assertIn("review_id", source)

    def test_active_roadmap_has_7_1_in_progress_or_completed(self) -> None:
        roadmap = ROADMAP_PATH.read_text(encoding="utf-8")

        self.assertRegex(roadmap, r"\*\*0\.2\.2\*\* Current item: \*\*(7\.1|7\.2|8\.1|8\.2|Completed / final milestone state)\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.4\*\* Completed from this roadmap: \*\*(12|13|14|15|16) / 16\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.5\*\* Remaining: \*\*(4|3|2|1|0) / 16\*\*")
        self.assertIn("## 7.1. FounderReviewPackage v2 implementation", roadmap)
        self.assertRegex(
            roadmap,
            r"## 7\.1\. FounderReviewPackage v2 implementation\s+"
            r"\*\*Status:\*\* \[ \] Not started  \[ \] In progress  \[ \] Blocked  \[( |x)\] Done",
        )


if __name__ == "__main__":
    unittest.main()
