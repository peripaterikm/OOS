import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestIdeationModeComparisonAcceptance(unittest.TestCase):
    def test_module_contains_no_live_llm_or_api_calls(self) -> None:
        source = (ROOT / "src/oos/ideation_mode_comparison.py").read_text(encoding="utf-8")

        for forbidden in ["OpenAI(", "Anthropic(", "requests.post", "httpx.post", "chat.completions", "responses.create"]:
            self.assertNotIn(forbidden, source)

    def test_not_prematurely_wired_into_orchestrator(self) -> None:
        source = (ROOT / "src/oos/orchestrator.py").read_text(encoding="utf-8")

        for forbidden in ["ideation_mode_comparison", "compare_ideation_modes", "IdeationModeComparisonResult"]:
            self.assertNotIn(forbidden, source)

    def test_active_roadmap_has_completed_5_2_and_not_regressed(self) -> None:
        roadmap = (ROOT / "docs/roadmaps/OOS_roadmap_v2_2_8_weeks_checklist.md").read_text(encoding="utf-8")

        self.assertRegex(roadmap, r"\*\*0\.2\.2\*\* Current item: \*\*(6\.1|6\.2|7\.1|7\.2|8\.1)\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.4\*\* Completed from this roadmap: \*\*(10|11|12|13|14) / 16\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.5\*\* Remaining: \*\*(6|5|4|3|2) / 16\*\*")
        self.assertIn("## 5.2. Ideation mode comparison with weighted metrics\n**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done", roadmap)
        self.assertIn("**9.5** Milestone E: LLM primary ideation and comparison operational after **5.2**", roadmap)


if __name__ == "__main__":
    unittest.main()
