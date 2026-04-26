from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "oos" / "ai_council_critique.py"
ORCHESTRATOR_PATH = ROOT / "src" / "oos" / "orchestrator.py"
ROADMAP_PATH = ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_2_8_weeks_checklist.md"


class TestAICouncilCritiqueAcceptance(unittest.TestCase):
    def test_module_contains_no_live_llm_or_api_calls(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")

        for token in ("OpenAI(", "Anthropic(", "requests.post", "httpx.post", "chat.completions", "responses.create"):
            self.assertNotIn(token, source)

    def test_not_prematurely_wired_into_orchestrator(self) -> None:
        source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")

        for token in ("ai_council_critique", "run_isolated_council_critique", "CouncilCritique"):
            self.assertNotIn(token, source)

    def test_isolated_role_architecture_is_enforced(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")

        self.assertIn("class CouncilRoleProvider", source)
        self.assertIn("providers_by_role", source)
        self.assertIn("provider.critique(role=role", source)
        self.assertNotIn("combined prompt", source.lower())

    def test_suspiciously_clean_protection_exists(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")

        self.assertIn("suspiciously_clean", source)
        self.assertIn("requires_founder_manual_review", source)

    def test_founder_final_authority_is_preserved(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")

        self.assertIn("founder_final_authority", source)
        self.assertIn("must remain true", source)

    def test_active_roadmap_has_completed_6_2_and_not_regressed(self) -> None:
        roadmap = ROADMAP_PATH.read_text(encoding="utf-8")

        self.assertRegex(roadmap, r"\*\*0\.2\.2\*\* Current item: \*\*(7\.1|7\.2|8\.1)\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.4\*\* Completed from this roadmap: \*\*(12|13|14) / 16\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.5\*\* Remaining: \*\*(4|3|2) / 16\*\*")
        self.assertIn("## 6.2. Isolated AI council critique with suspiciously_clean protection", roadmap)
        self.assertIn("**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done", roadmap)
        self.assertIn("**9.6** Milestone F: Anti-pattern and AI council critique operational after **6.2**", roadmap)


if __name__ == "__main__":
    unittest.main()
