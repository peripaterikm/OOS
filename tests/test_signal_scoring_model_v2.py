import unittest

from oos.candidate_signal_extractor import extract_candidate_signal
from oos.evidence_classifier import clean_evidence
from oos.models import CleanedEvidence, EvidenceClassification, RawEvidence, compute_raw_evidence_content_hash
from oos.signal_scoring import (
    EMBEDDINGS_DISABLED_WEIGHTS,
    SCORING_MODEL_VERSION,
    SignalScoringInput,
    build_signal_score_breakdown,
    scoring_weights_sum,
    source_quality_weight,
)


def scoring_input(
    body: str,
    *,
    query_kind: str = "pain_query",
    classification_label: str = "pain_signal_candidate",
    signal_type: str = "pain_signal",
    source_type: str = "github_issues",
    confidence: float = 0.82,
    metadata: dict | None = None,
) -> SignalScoringInput:
    return SignalScoringInput(
        topic_id="ai_cfo_smb",
        source_type=source_type,
        query_kind=query_kind,
        classification_label=classification_label,
        signal_type=signal_type,
        title="Customer voice issue",
        body=body,
        pain_summary=body,
        current_workaround="manual spreadsheet" if "spreadsheet" in body.lower() else "unknown",
        buying_intent_hint="possible" if "tool" in body.lower() or "software" in body.lower() else "not_detected",
        urgency_hint="high" if "can't pay" in body.lower() or "deadline" in body.lower() else "low",
        classification_confidence=confidence,
        matched_rules=[classification_label],
        metadata=metadata or {},
    )


def raw_evidence(body: str, *, evidence_id: str = "raw_score_1", source_type: str = "github_issues") -> RawEvidence:
    title = "Finance issue"
    return RawEvidence(
        evidence_id=evidence_id,
        source_id=source_type,
        source_type=source_type,
        source_name=source_type,
        source_url=f"https://example.com/{evidence_id}",
        collected_at="2026-04-29T00:00:00+00:00",
        title=title,
        body=body,
        language="en",
        topic_id="ai_cfo_smb",
        query_kind="pain_query",
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="developer",
        raw_metadata={"fixture": True},
        access_policy="fixture",
        collection_method="fixture",
    )


def classification_for(cleaned: CleanedEvidence, classification: str, *, confidence: float = 0.82) -> EvidenceClassification:
    result = EvidenceClassification(
        evidence_id=cleaned.evidence_id,
        source_id=cleaned.source_id,
        source_type=cleaned.source_type,
        source_url=cleaned.source_url,
        topic_id=cleaned.topic_id,
        query_kind=cleaned.query_kind,
        classification=classification,
        confidence=confidence,
        matched_rules=[classification],
        reason="Fixture classification for scoring v2 tests.",
        requires_human_review=classification == "needs_human_review",
        is_noise=classification == "noise",
    )
    result.validate()
    return result


class TestSignalScoringModelV2(unittest.TestCase):
    def test_scoring_weights_sum_to_one_in_embeddings_disabled_mode(self) -> None:
        self.assertEqual(scoring_weights_sum(), 1.0)
        self.assertEqual(round(sum(EMBEDDINGS_DISABLED_WEIGHTS.values()), 6), 1.0)

    def test_strong_invoice_payment_manual_spreadsheet_pain_scores_high(self) -> None:
        breakdown = build_signal_score_breakdown(
            scoring_input(
                "Freelancer can't plan bills because invoice payment cycles are irregular. "
                "Manual spreadsheet tracks invoice dates, payment status, and due dates."
            )
        )

        self.assertGreaterEqual(breakdown.final_score, 0.78)
        self.assertIn("topic_relevance:finance_anchor", breakdown.explanation)
        self.assertIn("workaround:manual_or_spreadsheet", breakdown.explanation)

    def test_separate_spreadsheet_workaround_scores_above_generic_consulting_copy(self) -> None:
        pain = build_signal_score_breakdown(
            scoring_input("Describe the problem: we would need to maintain a separate spreadsheet for invoice reconciliation.")
        )
        generic = build_signal_score_breakdown(
            scoring_input("In today's fast-moving business environment financial transparency and strategic reporting are no longer optional.")
        )

        self.assertGreater(pain.final_score, generic.final_score)

    def test_customer_voice_query_gets_small_bonus_but_does_not_override_weak_relevance(self) -> None:
        regular = build_signal_score_breakdown(scoring_input("Generic small business operations discussion."))
        customer_voice = build_signal_score_breakdown(
            scoring_input(
                "Generic small business operations discussion.",
                query_kind="customer_voice_query",
                metadata={"persona_id": "smb_owner", "customer_voice_query_id": "cvq_1"},
            )
        )
        strong = build_signal_score_breakdown(
            scoring_input("Cash flow reporting is hard and the workaround is a manual spreadsheet.")
        )

        self.assertGreater(customer_voice.final_score, regular.final_score)
        self.assertLess(customer_voice.final_score, strong.final_score)
        self.assertLessEqual(customer_voice.customer_voice_match_bonus, 0.10)

    def test_marketing_install_tutorial_content_gets_penalty_and_low_score(self) -> None:
        breakdown = build_signal_score_breakdown(
            scoring_input("When the installation process is over, the computer will restart and QuickBooks will launch.")
        )

        self.assertGreaterEqual(breakdown.anti_marketing_penalty, 0.4)
        self.assertLessEqual(breakdown.final_score, 0.35)

    def test_needs_human_review_is_capped_low(self) -> None:
        breakdown = build_signal_score_breakdown(
            scoring_input(
                "Teams are talking about finance reporting.",
                classification_label="needs_human_review",
                signal_type="needs_human_review",
                confidence=0.55,
            )
        )

        self.assertTrue(breakdown.human_review_cap_applied)
        self.assertLessEqual(breakdown.final_score, 0.40)

    def test_noise_final_score_is_zero(self) -> None:
        breakdown = build_signal_score_breakdown(
            scoring_input("Hi", classification_label="noise", signal_type="needs_human_review", confidence=0.9)
        )

        self.assertTrue(breakdown.noise_cap_applied)
        self.assertEqual(breakdown.final_score, 0.0)

    def test_generic_small_business_without_finance_anchors_scores_low(self) -> None:
        breakdown = build_signal_score_breakdown(scoring_input("Small business owners can't compete with large corporations."))

        self.assertLessEqual(breakdown.topic_relevance_score, 0.2)
        self.assertLessEqual(breakdown.final_score, 0.50)

    def test_spreadsheet_alone_does_not_create_strong_relevance(self) -> None:
        breakdown = build_signal_score_breakdown(scoring_input("Spreadsheet template for a content calendar."))

        self.assertLessEqual(breakdown.topic_relevance_score, 0.2)
        self.assertLessEqual(breakdown.final_score, 0.50)

    def test_finance_anchor_plus_workaround_scores_above_finance_anchor_alone(self) -> None:
        anchor_only = build_signal_score_breakdown(scoring_input("Cash flow reporting for small business."))
        workaround = build_signal_score_breakdown(scoring_input("Cash flow reporting is hard and we use a manual spreadsheet workaround."))

        self.assertGreater(workaround.final_score, anchor_only.final_score)

    def test_urgency_terms_increase_score(self) -> None:
        baseline = build_signal_score_breakdown(scoring_input("Invoice reporting is hard."))
        urgent = build_signal_score_breakdown(scoring_input("Invoice reporting is hard before payroll deadline and we can't pay suppliers."))

        self.assertGreater(urgent.urgency_score, baseline.urgency_score)
        self.assertGreater(urgent.final_score, baseline.final_score)

    def test_final_score_is_clamped_to_valid_range(self) -> None:
        breakdown = build_signal_score_breakdown(
            scoring_input(
                " ".join(["invoice cash flow manual spreadsheet workaround deadline can't pay suppliers"] * 50),
                confidence=99.0,
            )
        )

        self.assertGreaterEqual(breakdown.final_score, 0.0)
        self.assertLessEqual(breakdown.final_score, 0.99)

    def test_scoring_explanation_includes_key_reasons(self) -> None:
        breakdown = build_signal_score_breakdown(
            scoring_input("Cash flow reporting is frustrating and the current workaround is a manual spreadsheet.")
        )

        self.assertIn("embeddings_disabled_formula", breakdown.explanation)
        self.assertIn("pain_strength:user_or_friction_language", breakdown.explanation)

    def test_source_quality_weight_is_deterministic_by_source_type(self) -> None:
        self.assertEqual(source_quality_weight("github_issues"), source_quality_weight("github_issues"))
        self.assertGreater(source_quality_weight("github_issues"), source_quality_weight("rss_feed"))

    def test_ranking_order_is_deterministic_in_mixed_fixture(self) -> None:
        bodies = [
            "Invoice payment cycles are broken and manual spreadsheets track due dates.",
            "Cash flow reporting is hard.",
            "Teams discuss finance reporting.",
            "Executive Summary Product pitch Market Context & Zone Analysis Priority: P1 Effort: high.",
        ]
        first = [build_signal_score_breakdown(scoring_input(body)).final_score for body in bodies]
        second = [build_signal_score_breakdown(scoring_input(body)).final_score for body in bodies]

        self.assertEqual(first, second)
        self.assertGreater(len(set(first)), 1)
        self.assertGreater(first[0], first[1])
        self.assertGreater(first[1], first[3])

    def test_candidate_signal_uses_scoring_model_v2_artifact_fields(self) -> None:
        cleaned = clean_evidence(
            raw_evidence("Invoice payment cycles are broken and manual spreadsheets track due dates.")
        )
        signal = extract_candidate_signal(cleaned, classification_for(cleaned, "pain_signal_candidate"))

        self.assertEqual(signal.scoring_model_version, SCORING_MODEL_VERSION)
        self.assertEqual(signal.scoring_breakdown["final_score"], signal.confidence)
        self.assertIn("topic_relevance_score", signal.scoring_breakdown)
        self.assertEqual(signal.extraction_mode, "rule_based_v2")


if __name__ == "__main__":
    unittest.main()
