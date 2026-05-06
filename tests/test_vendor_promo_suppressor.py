import unittest

from oos.candidate_signal_extractor import extract_candidate_signal
from oos.evidence_classifier import classify_evidence, clean_evidence
from oos.founder_package import build_founder_package_quality_sections
from oos.models import RawEvidence, compute_raw_evidence_content_hash
from oos.signal_scoring import SignalScoringInput, build_signal_score_breakdown
from oos.vendor_promo_suppressor import assess_vendor_promo


def raw_evidence(
    evidence_id: str,
    title: str,
    body: str,
    *,
    source_type: str = "github_issues",
    source_url: str | None = None,
) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        source_id=source_type,
        source_type=source_type,
        source_name=source_type,
        source_url=source_url or f"https://github.com/example/repo/issues/{evidence_id}",
        collected_at="2026-05-05T00:00:00+00:00",
        title=title,
        body=body,
        language="en",
        topic_id="ai_cfo_smb",
        query_kind="pain_query",
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="public_issue_context",
        raw_metadata={"fixture": True},
        access_policy="fixture",
        collection_method="fixture",
    )


ZOHO_PROMO = (
    "[Zoho Books Accounting Software](https://nurtureu.tech/zoho-books/) for Small Businesses | NurtureU "
    "Discover efficient accounting with Zoho Books software."
)
BUSY_PROMO = (
    "Simplify Billing, GST, Inventory, and Financial Management with BUSY Software. "
    "Key Advantages: Authorized BUSY Software provider, free demo and consultation, "
    "cloud and on-premise setup options, professional training support, affordable pricing, technical assistance."
)
CORPORATE_SEO = (
    "Corporate accounting software transform your business into an integrated "
    "[accounting program](https://www.tumblr.com/new/text) that carries the size of your business."
)
GENERIC_ACCOUNTING_COPY = (
    "When financial records remain accurate and up to date, business owners gain visibility into their operations. "
    "Accurate records help business owners track performance, meet tax obligations and plan for sustainable growth."
)
QUICKBOOKS_MCP = (
    "[Submit] quickbooks-mcp — Hosted MCP server for QuickBooks Online accounting. "
    "MCP Server Submission Name:** quickbooks-mcp URL:** https://automadic.ai "
    "License:** Commercial Type:** MCP Server (Remote/Hosted)."
)
YNAB_FEATURE_REQUEST = (
    "Describe the solution you'd like I would like to be able to produce a balance sheet, "
    "which describes the current and historical month-end balances in my account."
)
HN_INVOICE_PAIN = (
    "I built a tool because I was tired of writing this email: "
    "\"Hi, just following up on my invoice from 3 weeks ago...\" I ran a small business and lost it "
    "because cash collection was hard."
)


class TestVendorPromoSuppressor(unittest.TestCase):
    def test_zoho_books_promo_is_detected(self) -> None:
        assessment = assess_vendor_promo(body=ZOHO_PROMO, source_type="github_issues")

        self.assertTrue(assessment.is_vendor_promo)
        self.assertIn("vendor_promo:zoho_books", assessment.matched_patterns)
        self.assertIn(assessment.recommended_classification, {"needs_human_review", "noise"})

    def test_busy_software_promo_is_detected(self) -> None:
        assessment = assess_vendor_promo(body=BUSY_PROMO, source_type="github_issues")

        self.assertTrue(assessment.is_vendor_promo)
        self.assertIn("vendor_promo:free_demo", assessment.matched_patterns)
        self.assertIn("vendor_promo:technical_assistance", assessment.matched_patterns)

    def test_corporate_accounting_software_seo_text_is_detected(self) -> None:
        assessment = assess_vendor_promo(body=CORPORATE_SEO, source_type="github_issues")

        self.assertTrue(assessment.is_vendor_promo)
        self.assertIn("seo_link:tumblr", assessment.matched_patterns)
        self.assertIn("vendor_promo:transform_your_business", assessment.matched_patterns)

    def test_quickbooks_mcp_submission_is_detected_as_product_listing(self) -> None:
        assessment = assess_vendor_promo(body=QUICKBOOKS_MCP, source_type="github_issues")

        self.assertTrue(assessment.is_vendor_promo)
        self.assertEqual(assessment.recommended_classification, "noise")
        self.assertIn("product_submission:mcp_server_submission", assessment.matched_patterns)

    def test_generic_accounting_copy_is_suppressed_or_capped(self) -> None:
        evidence = raw_evidence("raw_github_issue_4058309053", "Accounting records", GENERIC_ACCOUNTING_COPY)
        cleaned = clean_evidence(evidence)
        classification = classify_evidence(cleaned)
        signal = extract_candidate_signal(cleaned, classification)

        self.assertIn(classification.classification, {"needs_human_review", "noise"})
        self.assertTrue(classification.requires_human_review or classification.is_noise)
        if signal is not None:
            self.assertLessEqual(signal.confidence, 0.30)
            self.assertTrue(signal.scoring_breakdown["vendor_promo_flag"])

    def test_ynab_balance_sheet_feature_request_is_not_suppressed(self) -> None:
        evidence = raw_evidence("raw_github_issue_1182773055", "Balance sheet report", YNAB_FEATURE_REQUEST)
        cleaned = clean_evidence(evidence)
        classification = classify_evidence(cleaned)
        assessment = assess_vendor_promo(body=cleaned.normalized_body, source_type=cleaned.source_type)

        self.assertFalse(assessment.is_vendor_promo)
        self.assertNotEqual(classification.classification, "noise")
        self.assertFalse(any(rule == "vendor_promo_suppressor" for rule in classification.matched_rules))

    def test_hn_invoice_follow_up_is_not_suppressed(self) -> None:
        evidence = raw_evidence(
            "raw_hn_47082761",
            "Invoice follow-up",
            HN_INVOICE_PAIN,
            source_type="hacker_news_algolia",
            source_url="https://news.ycombinator.com/item?id=47082761",
        )
        cleaned = clean_evidence(evidence)
        classification = classify_evidence(cleaned)
        assessment = assess_vendor_promo(body=cleaned.normalized_body, source_type=cleaned.source_type)

        self.assertFalse(assessment.is_vendor_promo)
        self.assertNotEqual(classification.classification, "noise")
        self.assertFalse(any(rule == "vendor_promo_suppressor" for rule in classification.matched_rules))

    def test_suppressor_returns_matched_patterns_and_reason(self) -> None:
        assessment = assess_vendor_promo(body=BUSY_PROMO, source_type="github_issues")

        self.assertTrue(assessment.matched_patterns)
        self.assertTrue(assessment.reason)
        self.assertIn(assessment.suppression_action, {"cap_for_review", "classify_as_noise"})

    def test_scoring_cap_applies_to_vendor_promo_examples(self) -> None:
        breakdown = build_signal_score_breakdown(
            SignalScoringInput(
                topic_id="ai_cfo_smb",
                source_type="github_issues",
                query_kind="pain_query",
                classification_label="pain_signal_candidate",
                signal_type="pain_signal",
                title="BUSY Software",
                body=BUSY_PROMO,
                pain_summary=BUSY_PROMO,
                current_workaround="manual errors",
                buying_intent_hint="possible",
                urgency_hint="low",
                classification_confidence=0.9,
                matched_rules=["fixture"],
            )
        )

        self.assertTrue(breakdown.vendor_promo_flag)
        self.assertLessEqual(breakdown.final_score, breakdown.vendor_promo_scoring_cap)
        self.assertIn("vendor_promo_suppressor_cap", breakdown.explanation)

    def test_founder_package_explains_vendor_promo_suppression_when_retained(self) -> None:
        evidence = raw_evidence("raw_github_issue_3565323722", "Zoho Books", ZOHO_PROMO)
        cleaned = clean_evidence(evidence)
        classification = classify_evidence(cleaned)
        signal = extract_candidate_signal(cleaned, classification)

        self.assertIsNotNone(signal)
        sections = build_founder_package_quality_sections(
            candidate_signals=[signal],
            classifications=[classification],
            price_signals=[],
        )
        risk_items = sections["sections"]["evidence_confidence_risk_notes"]["items"]

        self.assertTrue(any("vendor promo/SEO suppression cap" in item["risk_note"] for item in risk_items))

    def test_no_live_network_or_llm_calls_are_made(self) -> None:
        assessment = assess_vendor_promo(body=QUICKBOOKS_MCP, source_type="github_issues")

        self.assertTrue(assessment.is_vendor_promo)


if __name__ == "__main__":
    unittest.main()
