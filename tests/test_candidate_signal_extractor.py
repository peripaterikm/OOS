import shutil
import unittest
from pathlib import Path

from oos.artifact_store import ArtifactStore
from oos.candidate_signal_extractor import (
    MEASUREMENT_METHODS,
    extract_candidate_signal,
    extract_candidate_signal_from_raw,
    extract_candidate_signals,
)
from oos.evidence_classifier import clean_evidence
from oos.models import (
    CleanedEvidence,
    EvidenceClassification,
    RawEvidence,
    compute_raw_evidence_content_hash,
)


def raw_evidence(
    *,
    evidence_id: str = "raw_signal_1",
    source_type: str = "github_issues",
    source_id: str = "",
    title: str = "Finance export issue",
    body: str = "This bug is broken and blocks finance reporting.",
    source_url: str = "https://github.com/example/project/issues/42",
    query_kind: str = "pain_query",
) -> RawEvidence:
    resolved_source_id = source_id or source_type
    return RawEvidence(
        evidence_id=evidence_id,
        source_id=resolved_source_id,
        source_type=source_type,
        source_name=source_type,
        source_url=source_url,
        collected_at="2024-01-02T03:04:05+00:00",
        title=title,
        body=body,
        language="en",
        topic_id="ai_cfo_smb",
        query_kind=query_kind,
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="developer",
        raw_metadata={"fixture": True},
        access_policy="fixture",
        collection_method="fixture",
    )


def classification_for(
    cleaned: CleanedEvidence,
    classification: str,
    *,
    confidence: float = 0.75,
    matched_rules: list[str] | None = None,
) -> EvidenceClassification:
    result = EvidenceClassification(
        evidence_id=cleaned.evidence_id,
        source_id=cleaned.source_id,
        source_type=cleaned.source_type,
        source_url=cleaned.source_url,
        topic_id=cleaned.topic_id,
        query_kind=cleaned.query_kind,
        classification=classification,
        confidence=confidence,
        matched_rules=matched_rules or [f"{classification}:fixture"],
        reason="Fixture classification for extractor tests.",
        requires_human_review=classification == "needs_human_review",
        is_noise=classification == "noise",
    )
    result.validate()
    return result


def signal_for(
    classification: str,
    *,
    source_type: str = "github_issues",
    body: str = "This bug is broken and blocks finance reporting.",
) :
    cleaned = clean_evidence(raw_evidence(source_type=source_type, body=body))
    return extract_candidate_signal(cleaned, classification_for(cleaned, classification))


class TestCandidateSignalExtractor(unittest.TestCase):
    def test_pain_signal_candidate_produces_candidate_signal(self) -> None:
        signal = signal_for("pain_signal_candidate")

        self.assertIsNotNone(signal)
        self.assertEqual(signal.signal_type, "pain_signal")

    def test_workaround_signal_candidate_produces_candidate_signal(self) -> None:
        signal = signal_for("workaround_signal_candidate", body="Our workaround is a manual spreadsheet.")

        self.assertEqual(signal.signal_type, "workaround")
        self.assertIn("manual spreadsheet", signal.current_workaround)

    def test_buying_intent_candidate_produces_candidate_signal(self) -> None:
        signal = signal_for("buying_intent_candidate", body="Looking for any tool with pricing.")

        self.assertEqual(signal.signal_type, "buying_intent")
        self.assertEqual(signal.buying_intent_hint, "present")

    def test_competitor_weakness_candidate_produces_candidate_signal(self) -> None:
        signal = signal_for("competitor_weakness_candidate", body="The current tool is too expensive.")

        self.assertEqual(signal.signal_type, "competitor_weakness")

    def test_trend_trigger_candidate_produces_candidate_signal(self) -> None:
        signal = signal_for("trend_trigger_candidate", body="New regulation recently changed finance workflows.")

        self.assertEqual(signal.signal_type, "trend_trigger")
        self.assertEqual(signal.urgency_hint, "high")

    def test_needs_human_review_produces_low_confidence_signal(self) -> None:
        signal = signal_for("needs_human_review", body="Teams are talking about finance reporting.")

        self.assertEqual(signal.signal_type, "needs_human_review")
        self.assertLessEqual(signal.confidence, 0.45)
        self.assertGreater(signal.confidence, 0)

    def test_noise_produces_no_candidate_signal(self) -> None:
        cleaned = clean_evidence(raw_evidence(title="Hi", body="ok"))
        signal = extract_candidate_signal(cleaned, classification_for(cleaned, "noise", confidence=0.95))

        self.assertIsNone(signal)

    def test_signal_id_is_deterministic(self) -> None:
        cleaned = clean_evidence(raw_evidence(evidence_id="raw signal/1"))
        classification = classification_for(cleaned, "pain_signal_candidate")

        first = extract_candidate_signal(cleaned, classification)
        second = extract_candidate_signal(cleaned, classification)

        self.assertEqual(first.signal_id, second.signal_id)
        self.assertEqual(first.signal_id, "candidate_signal_raw_signal_1_pain_signal_candidate")

    def test_traceability_fields_are_preserved(self) -> None:
        cleaned = clean_evidence(
            raw_evidence(
                evidence_id="raw_trace_1",
                source_id="github_issues",
                source_url="https://github.com/example/project/issues/77",
                query_kind="buying_intent_query",
            )
        )
        signal = extract_candidate_signal(cleaned, classification_for(cleaned, "buying_intent_candidate"))

        self.assertEqual(signal.evidence_id, "raw_trace_1")
        self.assertEqual(signal.source_url, "https://github.com/example/project/issues/77")
        self.assertEqual(signal.traceability["source_id"], "github_issues")
        self.assertEqual(signal.traceability["topic_id"], "ai_cfo_smb")
        self.assertEqual(signal.traceability["query_kind"], "buying_intent_query")

    def test_measurement_methods_exist_for_required_dimensions(self) -> None:
        signal = signal_for("pain_signal_candidate")

        self.assertEqual(signal.measurement_methods, MEASUREMENT_METHODS)
        self.assertEqual(
            set(signal.measurement_methods),
            {
                "signal_type",
                "pain_summary",
                "target_user",
                "current_workaround",
                "buying_intent_hint",
                "urgency_hint",
                "confidence",
            },
        )

    def test_no_field_claims_live_llm_measurement(self) -> None:
        signal = signal_for("pain_signal_candidate")

        self.assertNotIn("llm", signal.extraction_mode)
        self.assertTrue(all(method == "rule_based" for method in signal.measurement_methods.values()))

    def test_target_user_defaults_safely_without_overclaiming(self) -> None:
        hn_signal = signal_for(
            "needs_human_review",
            source_type="hacker_news_algolia",
            body="People discuss finance reporting tools.",
        )
        github_signal = signal_for("pain_signal_candidate", source_type="github_issues")

        self.assertEqual(hn_signal.target_user, "unknown")
        self.assertEqual(github_signal.target_user, "developer")

    def test_current_workaround_extraction_uses_simple_workaround_text(self) -> None:
        signal = signal_for(
            "workaround_signal_candidate",
            body="We use a manual spreadsheet as a temporary solution. It breaks often.",
        )

        self.assertEqual(signal.current_workaround, "We use a manual spreadsheet as a temporary solution.")

    def test_buying_intent_hint_detects_buying_text(self) -> None:
        signal = signal_for("pain_signal_candidate", body="This is painful and we need a tool.")

        self.assertEqual(signal.buying_intent_hint, "possible")

    def test_urgency_hint_detects_urgent_or_blocked_text(self) -> None:
        signal = signal_for("pain_signal_candidate", body="We are blocked because this critical export is broken.")

        self.assertEqual(signal.urgency_hint, "high")

    def test_candidate_signal_artifact_roundtrip(self) -> None:
        signal = signal_for("pain_signal_candidate")
        tmp = Path("codex_tmp_candidate_signal")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            store = ArtifactStore(root_dir=tmp / "artifacts")
            store.write_model(signal)

            self.assertEqual(store.read_model(type(signal), signal.signal_id), signal)
            self.assertTrue(store.path_for("candidate_signals", signal.signal_id).exists())
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)

    def test_batch_extraction_preserves_ordering_and_determinism(self) -> None:
        cleaned_items = [
            clean_evidence(raw_evidence(evidence_id="raw_a", body="This bug is broken.")),
            clean_evidence(raw_evidence(evidence_id="raw_b", body="Looking for any tool.")),
        ]
        classifications = [
            classification_for(cleaned_items[0], "pain_signal_candidate"),
            classification_for(cleaned_items[1], "buying_intent_candidate"),
        ]

        first = extract_candidate_signals(cleaned_items, classifications)
        second = extract_candidate_signals(cleaned_items, classifications)

        self.assertEqual([signal.evidence_id for signal in first], ["raw_a", "raw_b"])
        self.assertEqual([signal.signal_id for signal in first], [signal.signal_id for signal in second])

    def test_no_internet_api_or_llm_calls_required(self) -> None:
        signal = extract_candidate_signal_from_raw(
            raw_evidence(body="This issue is broken and frustrating.")
        )

        self.assertEqual(signal.extraction_mode, "rule_based_v1")
        self.assertEqual(signal.measurement_methods["confidence"], "rule_based")


if __name__ == "__main__":
    unittest.main()
