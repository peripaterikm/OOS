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

    def test_pain_phrases_classify_as_pain_signal_candidate(self) -> None:
        classification = classify_raw_evidence(raw_evidence(body="This reporting problem is frustrating."))

        self.assertEqual(classification.classification, PAIN_SIGNAL_CANDIDATE)
        self.assertFalse(classification.is_noise)

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
