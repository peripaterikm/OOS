import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestOpportunityQualityGateAcceptance(unittest.TestCase):
    def test_opportunity_quality_gate_module_has_no_live_llm_or_api_calls(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "opportunity_quality_gate.py").read_text(encoding="utf-8")
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

    def test_opportunity_quality_gate_is_not_wired_into_run_signal_batch(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "orchestrator.py").read_text(encoding="utf-8")
        forbidden_tokens = [
            "opportunity_quality_gate",
            "evaluate_opportunity_batch",
            "OpportunityGateResult",
            "OpportunityGateDecision",
        ]

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_gate_is_advisory_and_preserves_founder_decision_authority(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "opportunity_quality_gate.py").read_text(encoding="utf-8")

        self.assertIn("founder_override_status", source)
        self.assertIn("Founder decision remains final", source)
        self.assertNotIn("FounderReviewDecision", source)
        self.assertNotIn("record_founder_review", source)

    def test_active_roadmap_is_advanced_to_5_1(self) -> None:
        source = (REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_2_8_weeks_checklist.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("**0.2.2** Current item: **5.1**", source)
        self.assertIn("**0.2.4** Completed from this roadmap: **8 / 16**", source)
        self.assertIn("**0.2.5** Remaining: **8 / 16**", source)
        self.assertRegex(
            source,
            re.compile(
                r"## 4\.2\. Opportunity quality gate\s+"
                r"\*\*Status:\*\* \[ \] Not started  \[ \] In progress  \[ \] Blocked  \[x\] Done",
                re.MULTILINE,
            ),
        )
        self.assertIn("**9.4** Milestone D: AI opportunity framing operational after **4.2**", source)


if __name__ == "__main__":
    unittest.main()
