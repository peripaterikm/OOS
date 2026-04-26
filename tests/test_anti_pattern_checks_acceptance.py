import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestAntiPatternChecksAcceptance(unittest.TestCase):
    def test_module_contains_no_live_llm_or_api_calls(self) -> None:
        source = (ROOT / "src/oos/anti_pattern_checks.py").read_text(encoding="utf-8")

        for forbidden in ["OpenAI(", "Anthropic(", "requests.post", "httpx.post", "chat.completions", "responses.create"]:
            self.assertNotIn(forbidden, source)

    def test_not_prematurely_wired_into_orchestrator(self) -> None:
        source = (ROOT / "src/oos/orchestrator.py").read_text(encoding="utf-8")

        for forbidden in ["anti_pattern_checks", "check_anti_patterns", "AntiPatternCheckResult"]:
            self.assertNotIn(forbidden, source)

    def test_anti_pattern_layer_is_deterministic(self) -> None:
        source = (ROOT / "src/oos/anti_pattern_checks.py").read_text(encoding="utf-8")

        self.assertIn("ANTI_PATTERN_RULES", source)
        self.assertNotIn("Provider", source)
        self.assertNotIn("generate(", source)

    def test_active_roadmap_has_completed_6_1_and_not_regressed(self) -> None:
        roadmap = (ROOT / "docs/roadmaps/OOS_roadmap_v2_2_8_weeks_checklist.md").read_text(encoding="utf-8")

        self.assertRegex(roadmap, r"\*\*0\.2\.2\*\* Current item: \*\*(6\.2|7\.1|7\.2|8\.1|8\.2|Completed / final milestone state)\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.4\*\* Completed from this roadmap: \*\*(11|12|13|14|15|16) / 16\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.5\*\* Remaining: \*\*(5|4|3|2|1|0) / 16\*\*")
        self.assertIn("## 6.1. Deterministic anti-pattern checks\n**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done", roadmap)


if __name__ == "__main__":
    unittest.main()
