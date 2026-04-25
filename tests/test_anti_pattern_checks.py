import copy
import unittest
from pathlib import Path

from oos.anti_pattern_checks import check_anti_patterns, check_idea_for_anti_patterns, compute_genericness_penalty
from oos.pattern_guided_ideation import StaticPatternGuidedIdeationProvider, generate_pattern_guided_ideas
from tests.test_pattern_guided_ideation import idea_payload, make_opportunity


def idea(**overrides):
    payload = idea_payload("idea_test", "SaaS / tool")
    payload.update(overrides)
    return payload


class TestAntiPatternChecks(unittest.TestCase):
    def assert_detects(self, anti_pattern_id: str, payload: dict) -> None:
        result = check_idea_for_anti_patterns(payload)
        self.assertIn(anti_pattern_id, {finding.anti_pattern_id for finding in result.findings})

    def test_each_listed_anti_pattern_can_be_detected(self) -> None:
        cases = {
            "generic_dashboard": idea(product_concept="A generic dashboard for owners"),
            "generic_chatbot": idea(product_concept="A chatbot for finance questions"),
            "generic_ai_assistant": idea(product_concept="A generic AI assistant for everyone"),
            "uber_for_x": idea(product_concept="Uber for bookkeepers"),
            "pure_consulting_disguised_as_product": idea(product_concept="Custom consulting wrapped in a portal"),
            "founder_time_heavy_service": idea(first_experiment="Founder manually reconciles every report"),
            "unclear_buyer": idea(target_user="everyone"),
            "no_urgent_pain": idea(pain_addressed="Nice to have reporting polish"),
            "no_clear_first_experiment": idea(first_experiment="Research more"),
        }

        for anti_pattern_id, payload in cases.items():
            with self.subTest(anti_pattern_id=anti_pattern_id):
                self.assert_detects(anti_pattern_id, payload)

    def test_pattern_guided_idea_object_is_supported(self) -> None:
        result = generate_pattern_guided_ideas(
            opportunities=[make_opportunity()],
            provider=StaticPatternGuidedIdeationProvider(
                payload={"ideas": [idea_payload("idea_object", "SaaS / tool", product_concept="A generic dashboard")]}
            ),
        )

        finding_result = check_idea_for_anti_patterns(result.ideas[0])

        self.assertIn("generic_dashboard", {finding.anti_pattern_id for finding in finding_result.findings})

    def test_clean_idea_does_not_receive_false_severe_finding(self) -> None:
        result = check_idea_for_anti_patterns(
            idea(
                idea_id="clean",
                product_concept="Weekly reconciliation narrative workflow for owner trust gaps",
                wedge="Start with bank balance variance narratives",
                first_experiment="Run a concierge prototype with 5 SMB owners and measure trust lift",
            )
        )

        self.assertFalse(result.has_high_severity)

    def test_findings_include_explanation_and_severity(self) -> None:
        result = check_idea_for_anti_patterns(idea(product_concept="A chatbot for every business"))

        self.assertTrue(result.findings)
        self.assertTrue(all(finding.explanation for finding in result.findings))
        self.assertTrue(all(finding.severity in {"low", "medium", "high"} for finding in result.findings))

    def test_deterministic_layer_contains_no_live_llm_api_calls(self) -> None:
        source = Path("src/oos/anti_pattern_checks.py").read_text(encoding="utf-8")

        for forbidden in ["OpenAI(", "Anthropic(", "requests.post", "httpx.post", "chat.completions", "responses.create"]:
            self.assertNotIn(forbidden, source)

    def test_original_idea_objects_are_not_mutated(self) -> None:
        original = idea(product_concept="A generic dashboard")
        before = copy.deepcopy(original)

        check_idea_for_anti_patterns(original)

        self.assertEqual(original, before)

    def test_genericness_penalty_can_be_computed(self) -> None:
        penalty = compute_genericness_penalty(idea(product_concept="A generic dashboard assistant"))

        self.assertEqual(penalty, -2)

    def test_summary_counts_findings(self) -> None:
        summary = check_anti_patterns(
            [
                idea(idea_id="one", product_concept="A chatbot"),
                idea(idea_id="two", product_concept="A reconciliation narrative workflow"),
            ]
        )

        self.assertGreaterEqual(summary.total_findings, 1)
        self.assertIn("one", summary.total_penalty_by_idea_id)


if __name__ == "__main__":
    unittest.main()
