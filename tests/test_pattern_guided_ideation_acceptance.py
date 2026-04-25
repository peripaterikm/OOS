import re
import unittest
from pathlib import Path

from oos.models import IdeationGenerationMode
from oos.pattern_guided_ideation import StaticPatternGuidedIdeationProvider, generate_pattern_guided_ideas
from tests.test_pattern_guided_ideation import idea_payload, make_opportunity


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestPatternGuidedIdeationAcceptance(unittest.TestCase):
    def test_pattern_guided_ideation_module_has_no_live_llm_or_api_calls(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "pattern_guided_ideation.py").read_text(encoding="utf-8")
        forbidden_tokens = [
            "OpenAI(",
            "Anthropic(",
            "requests.post",
            "httpx.post",
            "chat.completions",
            "responses.create",
        ]

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_pattern_guided_ideation_is_not_wired_into_run_signal_batch(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "orchestrator.py").read_text(encoding="utf-8")
        forbidden_tokens = [
            "pattern_guided_ideation",
            "generate_pattern_guided_ideas",
            "PatternGuidedIdeationResult",
        ]

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_heuristic_fallback_is_available_and_clearly_labeled(self) -> None:
        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(payload={"ideas": []}),
        )

        self.assertTrue(result.fallback_used)
        self.assertTrue(result.ideas)
        self.assertTrue(all(idea.fallback_used for idea in result.ideas))
        self.assertTrue(
            all(
                idea.generation_mode == IdeationGenerationMode.heuristic_fallback_after_llm_failure.value
                for idea in result.ideas
            )
        )

    def test_product_pattern_diversity_rule_warns_or_is_enforced(self) -> None:
        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(
                payload={
                    "ideas": [
                        idea_payload("idea_1", "SaaS / tool"),
                        idea_payload("idea_2", "SaaS / tool"),
                        idea_payload("idea_3", "SaaS / tool"),
                    ]
                }
            ),
        )

        self.assertTrue(result.low_diversity_warning)
        self.assertGreaterEqual(len({idea.selected_product_pattern for idea in result.ideas}), 2)

    def test_active_roadmap_has_completed_5_1_and_not_regressed(self) -> None:
        source = (REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_2_8_weeks_checklist.md").read_text(
            encoding="utf-8"
        )

        self.assertRegex(source, re.compile(r"\*\*0\.2\.2\*\* Current item: \*\*(5\.2|6\.1|6\.2|7\.1)\*\*"))
        self.assertRegex(source, re.compile(r"\*\*0\.2\.4\*\* Completed from this roadmap: \*\*(9|10|11|12) / 16\*\*"))
        self.assertRegex(source, re.compile(r"\*\*0\.2\.5\*\* Remaining: \*\*(7|6|5|4) / 16\*\*"))
        self.assertRegex(
            source,
            re.compile(
                r"## 5\.1\. Pattern-guided LLM ideation\s+"
                r"\*\*Status:\*\* \[ \] Not started  \[ \] In progress  \[ \] Blocked  \[x\] Done",
                re.MULTILINE,
            ),
        )


if __name__ == "__main__":
    unittest.main()
