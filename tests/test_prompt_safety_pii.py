import unittest
from unittest.mock import patch

from oos.llm_contracts import LLMMessage, LLMRequest
from oos.prompt_safety import (
    PII_TYPE_CREDIT_CARD,
    PII_TYPE_EMAIL,
    PII_TYPE_IBAN,
    PII_TYPE_IPV4,
    PII_TYPE_ISRAELI_ID,
    PII_TYPE_PHONE,
    PII_TYPE_PRIVATE_KEY,
    PII_TYPE_SECRET,
    PII_TYPE_URL,
    PromptSafetyPolicy,
    build_safe_llm_request,
    build_prompt_safety_envelope_message,
    default_prompt_safety_policy,
    evaluate_prompt_safety,
    redact_pii,
)


class TestPromptSafetyPII(unittest.TestCase):
    def test_email_is_detected_and_redacted(self):
        result = redact_pii("Contact founder@example.com about invoices.")

        self.assertIn("[EMAIL_REDACTED]", result.redacted_text)
        self.assertNotIn("founder@example.com", result.redacted_text)
        self.assertEqual([finding.pii_type for finding in result.findings], [PII_TYPE_EMAIL])

    def test_phone_like_number_is_detected_and_redacted(self):
        result = redact_pii("Call +1 (415) 555-2671 after close.")

        self.assertIn("[PHONE_REDACTED]", result.redacted_text)
        self.assertTrue(any(finding.pii_type == PII_TYPE_PHONE for finding in result.findings))

    def test_hyphenated_phone_like_number_is_not_bank_account(self):
        result = redact_pii("Call 415-555-2671 after close.")

        self.assertIn("[PHONE_REDACTED]", result.redacted_text)
        self.assertTrue(any(finding.pii_type == PII_TYPE_PHONE for finding in result.findings))

    def test_url_is_detected_and_redacted_by_default(self):
        report = evaluate_prompt_safety("Review https://example.com/private/customer?id=12")

        self.assertIn("[URL_REDACTED]", report.redacted_text)
        self.assertIn("url_redacted", report.warnings)
        self.assertTrue(any(finding.pii_type == PII_TYPE_URL for finding in report.pii_findings))

    def test_ipv4_is_detected_and_redacted(self):
        result = redact_pii("Server address is 192.168.1.10")

        self.assertIn("[IP_REDACTED]", result.redacted_text)
        self.assertTrue(any(finding.pii_type == PII_TYPE_IPV4 for finding in result.findings))

    def test_credit_card_like_number_passes_luhn_and_is_redacted(self):
        report = evaluate_prompt_safety("Card 4111 1111 1111 1111 paid the invoice.")

        self.assertIn("[CARD_REDACTED]", report.redacted_text)
        self.assertIn("blocked_pii_type:credit_card", report.block_reasons)
        self.assertTrue(report.blocked)

    def test_non_card_short_numbers_are_not_treated_as_cards(self):
        result = redact_pii("Invoice 12345 is due in 30 days.")

        self.assertFalse(any(finding.pii_type == PII_TYPE_CREDIT_CARD for finding in result.findings))

    def test_israeli_id_like_number_is_redacted(self):
        result = redact_pii("Israeli ID 123456782 belongs in a private record.")

        self.assertIn("[ISRAELI_ID_REDACTED]", result.redacted_text)
        self.assertTrue(any(finding.pii_type == PII_TYPE_ISRAELI_ID for finding in result.findings))

    def test_iban_like_string_is_redacted(self):
        result = redact_pii("Transfer to GB82WEST12345698765432 for AP testing.")

        self.assertIn("[IBAN_REDACTED]", result.redacted_text)
        self.assertTrue(any(finding.pii_type == PII_TYPE_IBAN for finding in result.findings))

    def test_obvious_secret_token_is_redacted_and_blocked(self):
        report = evaluate_prompt_safety("Use token sk-abcdefghijklmnopqrstuvwxyz123456")

        self.assertIn("[SECRET_REDACTED]", report.redacted_text)
        self.assertIn("blocked_pii_type:secret", report.block_reasons)
        self.assertTrue(report.blocked)
        self.assertTrue(any(finding.pii_type == PII_TYPE_SECRET for finding in report.pii_findings))

    def test_private_key_marker_is_redacted_and_blocked(self):
        text = "-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----"
        report = evaluate_prompt_safety(text)

        self.assertEqual(report.redacted_text, "[SECRET_REDACTED]")
        self.assertIn("blocked_pii_type:private_key", report.block_reasons)
        self.assertTrue(report.blocked)
        self.assertTrue(any(finding.pii_type == PII_TYPE_PRIVATE_KEY for finding in report.pii_findings))

    def test_default_policy_redacts_pii_before_llm_request(self):
        request = LLMRequest(
            task_type="signal_review",
            messages=[LLMMessage(role="user", content="Email me at owner@example.com")],
            model_hint="future-model",
            temperature=0.2,
            metadata={"source": "test"},
        )

        safe_request, report = build_safe_llm_request(request)

        self.assertIsNotNone(safe_request)
        self.assertTrue(report.is_safe)
        self.assertIn("[EMAIL_REDACTED]", safe_request.messages[0].content)
        self.assertEqual(safe_request.task_type, request.task_type)
        self.assertEqual(safe_request.model_hint, request.model_hint)
        self.assertEqual(safe_request.temperature, request.temperature)
        self.assertEqual(safe_request.metadata["source"], "test")

    def test_original_text_remains_available_after_redaction(self):
        result = redact_pii("Email owner@example.com")

        self.assertEqual(result.original_text, "Email owner@example.com")
        self.assertNotEqual(result.original_text, result.redacted_text)

    def test_prompt_safety_envelope_has_asymmetric_prior_and_evidence_cited(self):
        message = build_prompt_safety_envelope_message()

        self.assertEqual(message.role, "system")
        self.assertIn("asymmetric prior", message.content)
        self.assertIn("default recommendation is review, not advance", message.content)
        self.assertIn("evidence_cited = true", message.content)
        self.assertIn("Do not invent facts", message.content)

    def test_blocked_prompt_returns_none_when_fail_closed(self):
        request = LLMRequest(
            task_type="signal_review",
            messages=[LLMMessage(role="user", content="Use card 4111111111111111")],
        )

        safe_request, report = build_safe_llm_request(request)

        self.assertIsNone(safe_request)
        self.assertTrue(report.blocked)

    def test_non_sensitive_prompt_passes_and_preserves_request(self):
        request = LLMRequest(
            task_type="signal_review",
            messages=[LLMMessage(role="system", content="Review signal."), LLMMessage(role="user", content="Cash flow is hard.")],
            model_hint="future-model",
            max_input_tokens=1000,
            max_output_tokens=300,
            temperature=0.1,
            metadata={"run_id": "dry"},
        )

        safe_request, report = build_safe_llm_request(request)

        self.assertIsNotNone(safe_request)
        self.assertFalse(report.blocked)
        self.assertEqual([message.role for message in safe_request.messages], ["system", "user"])
        self.assertEqual(safe_request.task_type, request.task_type)
        self.assertEqual(safe_request.model_hint, request.model_hint)
        self.assertEqual(safe_request.max_input_tokens, request.max_input_tokens)
        self.assertEqual(safe_request.max_output_tokens, request.max_output_tokens)
        self.assertEqual(safe_request.temperature, request.temperature)
        self.assertEqual(safe_request.metadata["run_id"], "dry")

    def test_max_prompt_chars_violation_blocks(self):
        policy = PromptSafetyPolicy(max_prompt_chars=10)

        report = evaluate_prompt_safety("This prompt is too long.", policy=policy)

        self.assertTrue(report.blocked)
        self.assertIn("max_prompt_chars_exceeded", report.block_reasons)

    def test_external_calls_made_is_always_false(self):
        report = evaluate_prompt_safety("owner@example.com")

        self.assertFalse(report.external_calls_made)

    def test_redaction_is_deterministic(self):
        text = "Email owner@example.com and call +1 (415) 555-2671"

        self.assertEqual(redact_pii(text), redact_pii(text))

    def test_llm_message_roles_are_preserved(self):
        request = LLMRequest(
            task_type="signal_review",
            messages=[
                LLMMessage(role="system", content="System prompt"),
                LLMMessage(role="user", content="User prompt with owner@example.com"),
                LLMMessage(role="assistant", content="Assistant context"),
            ],
        )

        safe_request, _report = build_safe_llm_request(request)

        self.assertEqual([message.role for message in safe_request.messages], ["system", "user", "assistant"])

    def test_no_network_api_or_llm_calls_are_made(self):
        with patch("urllib.request.urlopen") as urlopen:
            evaluate_prompt_safety("Email owner@example.com")

        urlopen.assert_not_called()
        self.assertTrue(default_prompt_safety_policy().fail_closed)


if __name__ == "__main__":
    unittest.main()
