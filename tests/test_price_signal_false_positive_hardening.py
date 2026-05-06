import unittest

from oos.evidence_classifier import clean_evidence
from oos.models import RawEvidence, compute_raw_evidence_content_hash
from oos.price_signal_extractor import extract_price_signal, price_signal_scoring_boost
from oos.signal_scoring import SignalScoringInput, build_signal_score_breakdown


def raw_evidence(
    body: str,
    *,
    evidence_id: str = "raw_price_false_positive",
    title: str = "Finance evidence",
    source_type: str = "github_issues",
) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        source_id=source_type,
        source_type=source_type,
        source_name=source_type,
        source_url=f"https://example.com/{evidence_id}",
        collected_at="2026-05-05T00:00:00+00:00",
        title=title,
        body=body,
        language="en",
        topic_id="ai_cfo_smb",
        query_kind="pain_query",
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="fixture_context",
        raw_metadata={"fixture": True},
        access_policy="fixture",
        collection_method="fixture",
    )


class TestPriceSignalFalsePositiveHardening(unittest.TestCase):
    def test_receipt_threshold_is_not_current_spend(self) -> None:
        signal = extract_price_signal(
            clean_evidence(
                raw_evidence(
                    "Small organizations make the mistake of not recovering receipts lesser than $75.",
                    evidence_id="raw_github_issue_194268452",
                )
            )
        )

        self.assertIsNone(signal)

    def test_section_179_deduction_limit_is_not_truncated_into_spend(self) -> None:
        signal = extract_price_signal(
            clean_evidence(
                raw_evidence(
                    "Small businesses compare accounting software because Section 179 has a $1.25M deduction limit for 2025.",
                    evidence_id="raw_hn_46725518",
                    source_type="hacker_news_algolia",
                )
            )
        )

        self.assertIsNone(signal)

    def test_tax_macrs_irs_limit_contexts_are_filtered(self) -> None:
        examples = [
            "IRS rules include a $2,500 statutory threshold for expense treatment.",
            "MACRS bonus depreciation has a $500,000 deduction limit.",
            "Luxury vehicle caps set a $20,400 limit for 2025.",
            "A compliance threshold of $10,000 is not a customer payment.",
        ]

        for index, body in enumerate(examples):
            with self.subTest(body=body):
                signal = extract_price_signal(clean_evidence(raw_evidence(body, evidence_id=f"raw_tax_limit_{index}")))
                self.assertIsNone(signal)

    def test_affordable_pricing_in_vendor_promo_does_not_boost(self) -> None:
        signal = extract_price_signal(
            clean_evidence(
                raw_evidence(
                    "Key Advantages: free demo and consultation, affordable pricing, professional training support, technical assistance.",
                    evidence_id="raw_github_issue_4369704245",
                )
            )
        )

        self.assertIsNone(signal)
        breakdown = build_signal_score_breakdown(
            SignalScoringInput(
                topic_id="ai_cfo_smb",
                source_type="github_issues",
                query_kind="pain_query",
                classification_label="pain_signal_candidate",
                signal_type="pain_signal",
                body="Key Advantages: free demo and consultation, affordable pricing, professional training support.",
                classification_confidence=0.8,
                price_signal_explicit=False,
                price_signal_confidence=0.0,
            )
        )
        self.assertEqual(breakdown.price_signal_boost, 0.0)

    def test_free_demo_and_consultation_do_not_create_wtp(self) -> None:
        signal = extract_price_signal(
            clean_evidence(raw_evidence("Free demo and consultation with technical assistance are available."))
        )

        self.assertIsNone(signal)

    def test_valid_cannot_afford_developer_remains_price_complaint(self) -> None:
        signal = extract_price_signal(
            clean_evidence(
                raw_evidence(
                    "Sticky notes and Excel would work better, but they can't afford a full time software developer.",
                    evidence_id="raw_hn_47009152",
                    source_type="hacker_news_algolia",
                )
            )
        )

        self.assertIsNotNone(signal)
        self.assertEqual(signal.price_complaint, "can't afford")
        self.assertIn("can't afford", signal.evidence_cited.lower())

    def test_valid_too_expensive_remains_price_complaint(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("The accounting platform is too expensive for us.")))

        self.assertIsNotNone(signal)
        self.assertEqual(signal.price_complaint, "too expensive")

    def test_false_positive_filtered_price_signals_have_no_boost(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("Section 179 has a $1.25M deduction limit.")))

        self.assertIsNone(signal)
        self.assertEqual(price_signal_scoring_boost(signal), 0.0)

    def test_no_live_network_or_llm_calls_are_made(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("The vendor is too expensive.")))

        self.assertIsNotNone(signal)


if __name__ == "__main__":
    unittest.main()
