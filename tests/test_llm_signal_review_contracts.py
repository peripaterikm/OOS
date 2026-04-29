import json
import unittest
from unittest.mock import patch

from oos.llm_signal_review import (
    EvidenceForReview,
    JTBDStatement,
    LLMSignalReviewInput,
    LLMSignalReviewOutput,
    build_jtbd_review_messages,
    build_safe_signal_review_request,
    build_signal_review_messages,
    parse_signal_review_json,
    run_deterministic_mock_signal_review,
    validate_signal_review_output,
)


def _review_input(text: str = "I need a manual spreadsheet to track invoice payments.") -> LLMSignalReviewInput:
    return LLMSignalReviewInput(
        review_id="review_001",
        topic_id="ai_cfo_smb",
        evidence=[
            EvidenceForReview(
                evidence_id="ev_001",
                source_type="github_issues",
                source_url="https://example.test/issues/1",
                title="Invoice payment tracking",
                body=text,
                pain_summary="Manual invoice payment tracking is painful.",
                current_workaround="manual spreadsheet",
                candidate_signal_type="pain_signal",
                confidence=0.82,
                scoring_breakdown={"final_score": 0.82},
            )
        ],
    )


def _valid_output_payload() -> dict:
    return {
        "review_id": "review_001",
        "topic_id": "ai_cfo_smb",
        "is_valid_signal": True,
        "signal_strength": "high",
        "signal_type": "pain_signal",
        "relevance_score": 0.9,
        "pain_score": 0.85,
        "buying_intent_score": 0.3,
        "icp_fit_score": 0.75,
        "recommendation": "advance",
        "jtbd_statements": [
            {
                "job_statement": "When invoices are paid late, I want to track expected payment dates so that I can plan bills.",
                "actor": "freelancer",
                "situation": "invoices are paid late",
                "desired_outcome": "plan bills",
                "when": "invoices are paid late",
                "want_to": "track expected payment dates",
                "so_that": "I can plan bills",
                "current_workaround": "manual spreadsheet",
                "evidence_ids": ["ev_001"],
                "confidence": 0.8,
            }
        ],
        "pain_summary": "Manual invoice payment tracking is painful.",
        "implied_burden_summary": "The user maintains a spreadsheet to plan payments.",
        "buying_intent_summary": None,
        "evidence_ids_cited": ["ev_001"],
        "evidence_cited": True,
        "uncertainty": "single evidence item",
        "reviewer_notes": ["evidence-bound"],
        "no_invention_confirmed": True,
        "jtbd_extracted": True,
    }


class TestLLMSignalReviewContracts(unittest.TestCase):
    def test_signal_review_prompt_includes_evidence_ids(self):
        messages = build_signal_review_messages(_review_input())
        prompt_text = "\n".join(message.content for message in messages)

        self.assertIn("ev_001", prompt_text)
        self.assertIn("review_001", prompt_text)

    def test_prompt_includes_no_invention_and_evidence_bound_instruction(self):
        messages = build_signal_review_messages(_review_input())
        prompt_text = "\n".join(message.content for message in messages)

        self.assertIn("evidence-bound", prompt_text)
        self.assertIn("do not invent facts", prompt_text.lower())
        self.assertIn("Cite evidence IDs", prompt_text)

    def test_prompt_includes_asymmetric_prior(self):
        messages = build_signal_review_messages(_review_input())
        prompt_text = "\n".join(message.content for message in messages)

        self.assertIn("asymmetric prior", prompt_text)
        self.assertIn("weak or noisy", prompt_text)

    def test_jtbd_prompt_schema_includes_when_want_to_so_that(self):
        messages = build_jtbd_review_messages(_review_input())
        prompt_text = "\n".join(message.content for message in messages)

        self.assertIn('"when"', prompt_text)
        self.assertIn('"want_to"', prompt_text)
        self.assertIn('"so_that"', prompt_text)
        self.assertIn('"confidence"', prompt_text)

    def test_safe_request_builder_redacts_pii(self):
        review_input = _review_input("Email owner@example.com about invoice tracking.")

        safe_request, report = build_safe_signal_review_request(review_input)

        self.assertIsNotNone(safe_request)
        self.assertIn("[EMAIL_REDACTED]", "\n".join(message.content for message in safe_request.messages))
        self.assertFalse(report.external_calls_made)
        self.assertEqual(safe_request.task_type, "llm_signal_review")
        self.assertEqual(safe_request.metadata["review_id"], "review_001")
        self.assertTrue(safe_request.metadata["requires_evidence_citations"])

    def test_safe_request_builder_blocks_secrets_private_keys_and_cards(self):
        for text in (
            "Use sk-abcdefghijklmnopqrstuvwxyz123456",
            "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
            "Card 4111111111111111",
        ):
            safe_request, report = build_safe_signal_review_request(_review_input(text))
            self.assertIsNone(safe_request)
            self.assertTrue(report.blocked)

    def test_safe_request_builder_makes_no_external_calls(self):
        with patch("urllib.request.urlopen") as urlopen:
            safe_request, report = build_safe_signal_review_request(_review_input())

        self.assertIsNotNone(safe_request)
        self.assertFalse(report.external_calls_made)
        urlopen.assert_not_called()

    def test_parse_valid_structured_json_output(self):
        output = parse_signal_review_json(json.dumps(_valid_output_payload()))

        self.assertEqual(output.review_id, "review_001")
        self.assertEqual(output.jtbd_statements[0].when, "invoices are paid late")
        self.assertTrue(output.evidence_cited)

    def test_invalid_json_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, "Invalid signal review JSON"):
            parse_signal_review_json("{not-json")

    def test_validation_fails_if_evidence_ids_are_missing(self):
        payload = _valid_output_payload()
        payload["evidence_ids_cited"] = []
        output = parse_signal_review_json(json.dumps(payload))

        valid, errors = validate_signal_review_output(output, _review_input())

        self.assertFalse(valid)
        self.assertIn("missing_evidence_citations", errors)

    def test_validation_fails_if_cited_evidence_id_is_unknown(self):
        payload = _valid_output_payload()
        payload["evidence_ids_cited"] = ["ev_missing"]
        payload["jtbd_statements"][0]["evidence_ids"] = ["ev_missing"]
        output = parse_signal_review_json(json.dumps(payload))

        valid, errors = validate_signal_review_output(output, _review_input())

        self.assertFalse(valid)
        self.assertIn("unknown_evidence_ids:ev_missing", errors)
        self.assertIn("jtbd_unknown_evidence_ids:ev_missing", errors)

    def test_validation_fails_if_no_invention_confirmed_is_false(self):
        payload = _valid_output_payload()
        payload["no_invention_confirmed"] = False
        output = parse_signal_review_json(json.dumps(payload))

        valid, errors = validate_signal_review_output(output, _review_input())

        self.assertFalse(valid)
        self.assertIn("no_invention_not_confirmed", errors)

    def test_jtbd_statements_must_cite_evidence_ids(self):
        output = LLMSignalReviewOutput(
            review_id="review_001",
            topic_id="ai_cfo_smb",
            is_valid_signal=True,
            signal_strength="medium",
            signal_type="pain_signal",
            jtbd_statements=[
                JTBDStatement(
                    job_statement="When cash is unclear, I want visibility so that I can decide.",
                    actor="owner",
                    situation="cash is unclear",
                    desired_outcome="decide",
                    when="cash is unclear",
                    want_to="get visibility",
                    so_that="I can decide",
                    current_workaround=None,
                    evidence_ids=[],
                    confidence=0.7,
                )
            ],
            pain_summary="Cash is unclear.",
            implied_burden_summary=None,
            buying_intent_summary=None,
            evidence_ids_cited=["ev_001"],
            evidence_cited=True,
            uncertainty="test",
            reviewer_notes=[],
            no_invention_confirmed=True,
            relevance_score=0.7,
            pain_score=0.7,
            buying_intent_score=0.0,
            icp_fit_score=0.7,
            recommendation="review",
            jtbd_extracted=True,
        )

        valid, errors = validate_signal_review_output(output, _review_input())

        self.assertFalse(valid)
        self.assertIn("jtbd_missing_evidence_ids", errors)

    def test_confidence_must_be_in_valid_range(self):
        payload = _valid_output_payload()
        payload["jtbd_statements"][0]["confidence"] = 1.5

        with self.assertRaisesRegex(ValueError, "JTBD confidence"):
            parse_signal_review_json(json.dumps(payload))

    def test_deterministic_mock_review_cites_evidence_and_is_stable(self):
        first = run_deterministic_mock_signal_review(_review_input())
        second = run_deterministic_mock_signal_review(_review_input())

        self.assertEqual(first, second)
        self.assertTrue(first.evidence_cited)
        self.assertEqual(first.evidence_ids_cited, ["ev_001"])
        self.assertTrue(first.no_invention_confirmed)

    def test_marketing_generic_evidence_gets_low_strength_in_mock(self):
        review_input = LLMSignalReviewInput(
            review_id="review_001",
            topic_id="ai_cfo_smb",
            evidence=[
                EvidenceForReview(
                    evidence_id="ev_001",
                    source_type="github_issues",
                    source_url=None,
                    title="Finance consulting landing page",
                    body="Our services are a trusted partner landing page with executive summary.",
                    pain_summary=None,
                    current_workaround=None,
                    candidate_signal_type="needs_human_review",
                    confidence=0.2,
                )
            ],
        )

        output = run_deterministic_mock_signal_review(review_input)

        self.assertEqual(output.signal_strength, "low")
        self.assertFalse(output.is_valid_signal)
        self.assertEqual(output.recommendation, "reject")

    def test_real_pain_workaround_evidence_gets_medium_or_high_strength_in_mock(self):
        output = run_deterministic_mock_signal_review(_review_input())

        self.assertIn(output.signal_strength, {"medium", "high"})
        self.assertTrue(output.is_valid_signal)

    def test_no_live_provider_calls_are_made(self):
        with patch("oos.llm_contracts.DeterministicMockLLMProvider.complete") as complete:
            output = run_deterministic_mock_signal_review(_review_input())

        self.assertTrue(output.evidence_cited)
        complete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
