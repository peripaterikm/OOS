import unittest
import shutil
from pathlib import Path

from oos.artifact_store import ArtifactStore
from oos.evidence_classifier import (
    BUYING_INTENT_CANDIDATE,
    COMPETITOR_WEAKNESS_CANDIDATE,
    NEEDS_HUMAN_REVIEW,
    NOISE,
    PAIN_SIGNAL_CANDIDATE,
    TREND_TRIGGER_CANDIDATE,
    WORKAROUND_SIGNAL_CANDIDATE,
    classify_evidence_batch,
    classify_raw_evidence,
    clean_evidence,
    compute_normalized_content_hash,
)
from oos.models import CleanedEvidence, EvidenceClassification, RawEvidence, compute_raw_evidence_content_hash


def raw_evidence(
    *,
    evidence_id: str = "raw_test_1",
    source_type: str = "stack_exchange",
    title: str = "Finance reporting",
    body: str = "This is hard to reconcile every week.",
    source_url: str = "HTTPS://Example.COM/path/?b=2&a=1#frag",
) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        source_id=source_type if source_type != "rss_feed" else "rss_feeds",
        source_type=source_type,
        source_name=source_type,
        source_url=source_url,
        collected_at="2024-01-02T03:04:05+00:00",
        title=title,
        body=body,
        language="",
        topic_id="ai_cfo_smb",
        query_kind="pain_query",
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="unverified public commenter",
        raw_metadata={"fixture": True},
        access_policy="fixture",
        collection_method="fixture",
    )


class TestEvidenceCleanerClassifier(unittest.TestCase):
    def test_cleaner_normalizes_whitespace(self) -> None:
        cleaned = clean_evidence(
            raw_evidence(
                title="  Manual     finance\n reporting  ",
                body=" We\tcopy   exports\r\n into   spreadsheets. ",
            )
        )

        self.assertEqual(cleaned.normalized_title, "Manual finance reporting")
        self.assertEqual(cleaned.normalized_body, "We copy exports into spreadsheets.")
        self.assertIn("boilerplate_removal_not_applied", cleaned.cleaning_notes)

    def test_cleaner_normalizes_urls_deterministically(self) -> None:
        first = clean_evidence(raw_evidence(source_url="HTTPS://Example.COM/path/?b=2&a=1#frag"))
        second = clean_evidence(raw_evidence(source_url="https://example.com/path?a=1&b=2"))

        self.assertEqual(first.normalized_url, "https://example.com/path?a=1&b=2")
        self.assertEqual(first.normalized_url, second.normalized_url)
        self.assertEqual(first.source_url, "HTTPS://Example.COM/path/?b=2&a=1#frag")

    def test_cleaner_produces_deterministic_normalized_content_hash(self) -> None:
        first = clean_evidence(raw_evidence(title=" Manual   report ", body=" Body\ntext "))
        second = clean_evidence(raw_evidence(title="Manual report", body="Body text"))

        self.assertEqual(first.normalized_content_hash, second.normalized_content_hash)
        self.assertEqual(
            first.normalized_content_hash,
            compute_normalized_content_hash(normalized_title="Manual report", normalized_body="Body text"),
        )

    def test_cleaner_unescapes_html_entities_and_strips_simple_tags(self) -> None:
        cleaned = clean_evidence(
            raw_evidence(
                body="Cash flow doesn&#x27;t work<p>Manual spreadsheet<br><strong>workaround</strong>",
            )
        )

        self.assertEqual(cleaned.normalized_body, "Cash flow doesn't work Manual spreadsheet workaround")
        self.assertNotIn("&#x27;", cleaned.normalized_body)
        self.assertNotIn("<p>", cleaned.normalized_body)

    def test_cleaner_repairs_common_mojibake_fragments(self) -> None:
        cleaned = clean_evidence(
            raw_evidence(
                body="In todayвЂ™s reporting flow, optionalвЂ”they track invoices рџљЂ manually.",
            )
        )

        self.assertIn("today's", cleaned.normalized_body)
        self.assertIn("optional—they", cleaned.normalized_body)
        self.assertNotIn("вЂ", cleaned.normalized_body)
        self.assertNotIn("рџ", cleaned.normalized_body.lower())

    def test_pain_phrases_classify_as_pain_signal_candidate(self) -> None:
        classification = classify_raw_evidence(raw_evidence(body="This reporting problem is frustrating."))

        self.assertEqual(classification.classification, PAIN_SIGNAL_CANDIDATE)
        self.assertFalse(classification.is_noise)

    def test_generic_hn_small_business_without_finance_anchor_is_not_high_confidence_pain(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(
                source_type="hacker_news_algolia",
                title="Small business competition",
                body="Small business owners can't compete with large corporations and unfair competition.",
            )
        )

        self.assertNotEqual(classification.classification, PAIN_SIGNAL_CANDIDATE)
        self.assertLessEqual(classification.confidence, 0.4)

    def test_small_business_alone_is_not_enough_for_ai_cfo_relevance(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(
                source_type="github_issues",
                title="Small business calendar",
                body="Small business content calendar is hard to keep updated.",
            )
        )

        self.assertNotEqual(classification.classification, PAIN_SIGNAL_CANDIDATE)
        self.assertLessEqual(classification.confidence, 0.4)

    def test_linkedin_content_calendar_spreadsheet_is_downgraded(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(
                source_type="github_issues",
                title="LinkedIn content plan",
                body=(
                    "30-Day LinkedIn Content Calendar with Copy-Paste Ready Posts. "
                    "Day 1 Post Topic spreadsheet. Day 2 Post Type campaign. Day 3 Post Topic marketing copy."
                ),
            )
        )

        self.assertIn(classification.classification, {NOISE, NEEDS_HUMAN_REVIEW})
        self.assertLessEqual(classification.confidence, 0.4 if classification.classification == NEEDS_HUMAN_REVIEW else 1.0)

    def test_product_pitch_marketing_artifacts_are_not_high_confidence_pain(self) -> None:
        examples = [
            "FraudNet Product pitch Executive Summary Market Context & Zone Analysis Portfolio Position.",
            "Productico 30-Day LinkedIn Content Calendar Copy-Pasteable LinkedIn Posts Post Topic Post Type.",
            "Dynamic Creative Personalization engine Campaign variants Competitive Target Landing page marketing copy.",
        ]

        for body in examples:
            classification = classify_raw_evidence(
                raw_evidence(source_type="github_issues", title="Marketing artifact", body=body)
            )

            self.assertNotEqual(classification.classification, PAIN_SIGNAL_CANDIDATE)
            if classification.classification == NEEDS_HUMAN_REVIEW:
                self.assertLessEqual(classification.confidence, 0.35)

    def test_quickbooks_installation_text_is_noise_or_low_confidence_review(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(
                source_type="github_issues",
                title="QuickBooks installation guide",
                body=(
                    "When the installation process is over, the computer will restart, "
                    "and then QuickBooks will launch. Click Next and follow these steps."
                ),
            )
        )

        self.assertIn(classification.classification, {NOISE, NEEDS_HUMAN_REVIEW})
        if classification.classification == NEEDS_HUMAN_REVIEW:
            self.assertLessEqual(classification.confidence, 0.25)

    def test_generic_finance_consulting_copy_is_downgraded(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(
                source_type="github_issues",
                title="Finance consulting article",
                body=(
                    "In today's fast-moving business environment, financial records remain accurate and up to date. "
                    "Financial transparency and strategic reporting are no longer optional. Contact us."
                ),
            )
        )

        self.assertIn(classification.classification, {NOISE, NEEDS_HUMAN_REVIEW})
        if classification.classification == NEEDS_HUMAN_REVIEW:
            self.assertLessEqual(classification.confidence, 0.3)

    def test_separate_spreadsheet_issue_remains_valid_user_pain(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(
                source_type="github_issues",
                body=(
                    "Describe the problem: we would need to maintain a separate spreadsheet "
                    "to reconcile invoices and payment status for accounting."
                ),
            )
        )

        self.assertIn(classification.classification, {PAIN_SIGNAL_CANDIDATE, WORKAROUND_SIGNAL_CANDIDATE})
        self.assertFalse(classification.is_noise)

    def test_balance_sheet_request_remains_valid_user_pain(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(
                source_type="github_issues",
                body="I would like to be able to produce a balance sheet for small business accounting.",
            )
        )

        self.assertEqual(classification.classification, PAIN_SIGNAL_CANDIDATE)
        self.assertFalse(classification.is_noise)

    def test_invoice_payment_cycles_manual_spreadsheets_remain_pain_candidate(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(
                source_type="github_issues",
                body=(
                    "Freelancer has irregular invoice payment cycles and can't plan bills from expected "
                    "incoming payments. Current workaround is manual spreadsheets tracking invoice dates, "
                    "payment status, and upcoming bill due dates."
                ),
            )
        )

        self.assertEqual(classification.classification, PAIN_SIGNAL_CANDIDATE)
        self.assertGreaterEqual(classification.confidence, 0.7)

    def test_cash_flow_reporting_pain_remains_relevant(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(body="Cash flow reporting is hard and frustrating for bookkeeping teams.")
        )

        self.assertEqual(classification.classification, PAIN_SIGNAL_CANDIDATE)
        self.assertGreaterEqual(classification.confidence, 0.7)

    def test_workaround_phrases_classify_as_workaround_signal_candidate(self) -> None:
        classification = classify_raw_evidence(raw_evidence(body="Our workaround is a manual spreadsheet."))

        self.assertEqual(classification.classification, WORKAROUND_SIGNAL_CANDIDATE)

    def test_buying_intent_phrases_classify_as_buying_intent_candidate(self) -> None:
        classification = classify_raw_evidence(raw_evidence(body="Looking for any tool and pricing guidance."))

        self.assertEqual(classification.classification, BUYING_INTENT_CANDIDATE)

    def test_competitor_weakness_phrases_classify_as_competitor_weakness_candidate(self) -> None:
        classification = classify_raw_evidence(raw_evidence(body="QuickBooks is too expensive and missing feature support."))

        self.assertEqual(classification.classification, COMPETITOR_WEAKNESS_CANDIDATE)

    def test_trend_trigger_phrases_classify_as_trend_trigger_candidate(self) -> None:
        classification = classify_raw_evidence(raw_evidence(body="New regulation recently changed reporting requirements."))

        self.assertEqual(classification.classification, TREND_TRIGGER_CANDIDATE)

    def test_hn_ambiguous_non_empty_defaults_to_needs_human_review_not_noise(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(source_type="hacker_news_algolia", body="I wonder how teams think about finance tools.")
        )

        self.assertEqual(classification.classification, NEEDS_HUMAN_REVIEW)
        self.assertTrue(classification.requires_human_review)
        self.assertFalse(classification.is_noise)

    def test_github_ambiguous_non_empty_defaults_to_needs_human_review_not_noise(self) -> None:
        classification = classify_raw_evidence(
            raw_evidence(source_type="github_issues", body="Finance export behavior should be discussed.")
        )

        self.assertEqual(classification.classification, NEEDS_HUMAN_REVIEW)
        self.assertTrue(classification.requires_human_review)
        self.assertFalse(classification.is_noise)

    def test_empty_or_near_empty_evidence_can_classify_as_noise(self) -> None:
        classification = classify_raw_evidence(raw_evidence(title="Hi", body="ok"))

        self.assertEqual(classification.classification, NOISE)
        self.assertTrue(classification.is_noise)

    def test_classification_includes_matched_rules_and_reason(self) -> None:
        classification = classify_raw_evidence(raw_evidence(body="This bug is hard to debug."))

        self.assertTrue(classification.matched_rules)
        self.assertTrue(classification.reason)
        self.assertIn("pain_signal_candidate", classification.matched_rules[0])

    def test_batch_classification_preserves_evidence_id_and_source_url_traceability(self) -> None:
        items = [
            raw_evidence(evidence_id="raw_a", source_url="https://example.com/a", body="This pain is real."),
            raw_evidence(evidence_id="raw_b", source_url="https://example.com/b", body="Looking for a tool."),
        ]

        classifications = classify_evidence_batch(items)

        self.assertEqual([item.evidence_id for item in classifications], ["raw_a", "raw_b"])
        self.assertEqual([item.source_url for item in classifications], ["https://example.com/a", "https://example.com/b"])

    def test_no_network_api_or_llm_calls_required(self) -> None:
        classification = classify_raw_evidence(raw_evidence(body="Manual spreadsheet workaround."))

        self.assertEqual(classification.classification, WORKAROUND_SIGNAL_CANDIDATE)
        self.assertTrue(all("api" not in rule for rule in classification.matched_rules))
        self.assertTrue(all("llm" not in rule for rule in classification.matched_rules))

    def test_cleaned_and_classification_artifacts_roundtrip(self) -> None:
        evidence = raw_evidence(body="This reporting pain needs a better workflow.")
        cleaned = clean_evidence(evidence)
        classification = classify_raw_evidence(evidence)

        tmp = Path("codex_tmp_evidence_classifier")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            store = ArtifactStore(root_dir=tmp / "artifacts")
            store.write_model(cleaned)
            store.write_model(classification)

            self.assertEqual(store.read_model(CleanedEvidence, evidence.evidence_id), cleaned)
            self.assertEqual(store.read_model(EvidenceClassification, evidence.evidence_id), classification)
            self.assertTrue(store.path_for("evidence_classifications", evidence.evidence_id).exists())
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
