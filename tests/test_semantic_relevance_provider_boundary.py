import unittest

from oos.semantic_relevance import (
    DisabledSemanticRelevanceProvider,
    KeywordSemanticRelevanceProvider,
    SemanticRelevanceInput,
    SemanticRelevanceResult,
    get_semantic_relevance_provider,
    semantic_relevance_available,
)
from oos.signal_scoring import SignalScoringInput, build_signal_score_breakdown


def relevance_input(body: str, *, topic_id: str = "ai_cfo_smb", query_text: str | None = None) -> SemanticRelevanceInput:
    return SemanticRelevanceInput(
        topic_id=topic_id,
        title="Finance workflow",
        body=body,
        query_text=query_text,
        source_type="github_issues",
        query_kind="pain_query",
        tags=["fixture"],
        metadata={"test": True},
    )


def scoring_input(body: str, **overrides: object) -> SignalScoringInput:
    kwargs = {
        "topic_id": "ai_cfo_smb",
        "source_type": "github_issues",
        "query_kind": "pain_query",
        "classification_label": "pain_signal_candidate",
        "signal_type": "pain_signal",
        "title": "Finance issue",
        "body": body,
        "pain_summary": body,
        "current_workaround": "manual spreadsheet" if "spreadsheet" in body.lower() else "unknown",
        "buying_intent_hint": "not_detected",
        "urgency_hint": "low",
        "classification_confidence": 0.82,
        "matched_rules": ["pain_signal_candidate"],
        "metadata": {},
    }
    kwargs.update(overrides)
    return SignalScoringInput(**kwargs)


class TestSemanticRelevanceProviderBoundary(unittest.TestCase):
    def test_disabled_provider_is_default(self) -> None:
        provider = get_semantic_relevance_provider()

        self.assertIsInstance(provider, DisabledSemanticRelevanceProvider)
        self.assertFalse(provider.is_available())
        self.assertFalse(semantic_relevance_available())

    def test_disabled_provider_makes_no_embeddings_or_external_calls(self) -> None:
        result = get_semantic_relevance_provider("disabled").score(relevance_input("cash flow is hard"))

        self.assertFalse(result.is_available)
        self.assertIsNone(result.score)
        self.assertEqual(result.confidence, 0.0)
        self.assertFalse(result.embeddings_used)
        self.assertFalse(result.external_calls_made)
        self.assertIn("disabled", " ".join(result.explanation))

    def test_keyword_stub_makes_no_embeddings_or_external_calls(self) -> None:
        result = get_semantic_relevance_provider("keyword_stub").score(
            relevance_input("Cash flow reporting is hard and the workaround is a manual spreadsheet.")
        )

        self.assertTrue(result.is_available)
        self.assertIsNotNone(result.score)
        self.assertFalse(result.embeddings_used)
        self.assertFalse(result.external_calls_made)
        self.assertIn("cash flow", result.matched_terms)

    def test_keyword_stub_scores_finance_workflow_above_generic_small_business(self) -> None:
        provider = KeywordSemanticRelevanceProvider()
        generic = provider.score(relevance_input("Small business owners discuss hiring and competition."))
        finance = provider.score(relevance_input("Invoice reconciliation is hard and payments are tracked manually."))

        self.assertGreater(finance.score or 0.0, generic.score or 0.0)
        self.assertLessEqual(generic.score or 0.0, 0.25)

    def test_spreadsheet_alone_does_not_score_high(self) -> None:
        result = KeywordSemanticRelevanceProvider().score(relevance_input("Spreadsheet template for a content calendar."))

        self.assertLessEqual(result.score or 0.0, 0.25)
        self.assertIn("weak anchors only; capped low", result.explanation)

    def test_finance_anchor_plus_workaround_scores_above_finance_anchor_alone(self) -> None:
        provider = KeywordSemanticRelevanceProvider()
        anchor_only = provider.score(relevance_input("Cash flow reporting for small business."))
        workaround = provider.score(relevance_input("Cash flow reporting is hard and uses a manual spreadsheet workaround."))

        self.assertGreater(workaround.score or 0.0, anchor_only.score or 0.0)

    def test_unknown_topic_returns_low_score_with_explanation(self) -> None:
        result = KeywordSemanticRelevanceProvider().score(
            relevance_input("Cash flow reporting is hard.", topic_id="personal_finance_household")
        )

        self.assertEqual(result.score, 0.0)
        self.assertIn("unknown topic", result.explanation[0])
        self.assertFalse(result.embeddings_used)
        self.assertFalse(result.external_calls_made)

    def test_unknown_provider_id_behavior_is_deterministic(self) -> None:
        with self.assertRaises(ValueError):
            get_semantic_relevance_provider("made_up_provider")

    def test_semantic_relevance_result_score_is_clamped_by_validation(self) -> None:
        result = KeywordSemanticRelevanceProvider().score(
            relevance_input(
                "Cash flow invoice billing accounting bookkeeping financial reporting management reporting "
                "budget forecast reconciliation payroll expenses P&L balance sheet QuickBooks Xero NetSuite "
                "manual workaround hard frustrating missing messy due dates."
            )
        )

        self.assertGreaterEqual(result.score or 0.0, 0.0)
        self.assertLessEqual(result.score or 0.0, 1.0)
        with self.assertRaises(ValueError):
            SemanticRelevanceResult(
                provider_id="bad",
                provider_kind="keyword_stub",
                is_available=True,
                score=1.5,
                confidence=0.5,
                matched_terms=[],
                explanation=[],
                model_name=None,
                embeddings_used=False,
                external_calls_made=False,
            )

    def test_scoring_v2_default_remains_embeddings_disabled_without_semantic_relevance(self) -> None:
        body = "Cash flow reporting is hard and the current workaround is a manual spreadsheet."
        default = build_signal_score_breakdown(scoring_input(body))
        disabled = build_signal_score_breakdown(
            scoring_input(
                body,
                semantic_relevance_provider_id="disabled",
                semantic_relevance_score=None,
                semantic_relevance_available=False,
            )
        )

        self.assertEqual(default.final_score, disabled.final_score)
        self.assertEqual(default.semantic_relevance_score, 0.0)
        self.assertFalse(default.semantic_relevance_available)
        self.assertIn("semantic_relevance:disabled", default.explanation)

    def test_explicit_available_semantic_score_is_diagnostic_only(self) -> None:
        body = "Cash flow reporting is hard and the current workaround is a manual spreadsheet."
        baseline = build_signal_score_breakdown(scoring_input(body))
        diagnostic = build_signal_score_breakdown(
            scoring_input(
                body,
                semantic_relevance_provider_id="keyword_stub",
                semantic_relevance_score=0.91,
                semantic_relevance_available=True,
            )
        )

        self.assertEqual(diagnostic.final_score, baseline.final_score)
        self.assertEqual(diagnostic.semantic_relevance_score, 0.91)
        self.assertTrue(diagnostic.semantic_relevance_available)
        self.assertIn("semantic_relevance:diagnostic_only:keyword_stub", diagnostic.explanation)


if __name__ == "__main__":
    unittest.main()
