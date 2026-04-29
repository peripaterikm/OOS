import unittest

from oos.llm_contracts import (
    DeterministicMockLLMProvider,
    DisabledLLMProvider,
    LLMBudgetCircuitBreaker,
    LLMBudgetPolicy,
    LLMBudgetState,
    LLMMessage,
    LLMRequest,
    LLMUsage,
    check_llm_budget,
    default_disabled_llm_budget_policy,
    default_local_preview_llm_budget_policy,
    estimate_request_tokens,
    estimate_tokens,
    get_llm_provider,
    record_llm_usage,
)


def request(
    content: str = "Review this evidence for finance pain.",
    *,
    task_type: str = "test_task",
    max_output_tokens: int | None = 10,
    model_hint: str | None = "deterministic-mock",
) -> LLMRequest:
    return LLMRequest(
        task_type=task_type,
        messages=[LLMMessage(role="system", content="You are a deterministic test provider."), LLMMessage(role="user", content=content)],
        model_hint=model_hint,
        max_input_tokens=1000,
        max_output_tokens=max_output_tokens,
        temperature=0.0,
        metadata={"fixture": True},
    )


class TestLLMContractsAndBudgets(unittest.TestCase):
    def test_disabled_provider_is_default(self) -> None:
        provider = get_llm_provider()

        self.assertIsInstance(provider, DisabledLLMProvider)
        self.assertFalse(provider.is_available())

    def test_disabled_provider_is_unavailable_and_makes_no_external_calls(self) -> None:
        result = get_llm_provider("disabled").complete(request())

        self.assertFalse(result.is_available)
        self.assertIsNone(result.response)
        self.assertEqual(result.error_code, "llm_disabled")
        self.assertIn("No external LLM/API call was made.", result.explanation)

    def test_deterministic_mock_provider_is_available_and_makes_no_external_calls(self) -> None:
        result = get_llm_provider("deterministic_mock").complete(request())

        self.assertTrue(result.is_available)
        self.assertIsNotNone(result.response)
        self.assertFalse(result.response.external_calls_made)
        self.assertEqual(result.response.provider_id, "deterministic_mock")
        self.assertEqual(result.response.model_name, "deterministic-mock")
        self.assertIn("no external calls", " ".join(result.response.safety_notes))

    def test_deterministic_mock_output_is_stable_for_same_request(self) -> None:
        provider = DeterministicMockLLMProvider()
        first = provider.complete(request()).response
        second = provider.complete(request()).response

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.content, second.content)
        self.assertEqual(first.usage, second.usage)

    def test_token_estimator_is_deterministic_and_positive_for_non_empty_text(self) -> None:
        self.assertEqual(estimate_tokens("hello world"), estimate_tokens("hello world"))
        self.assertGreater(estimate_tokens("hello world"), 0)
        self.assertEqual(estimate_tokens(""), 0)
        self.assertGreater(estimate_request_tokens(request("abc")), 0)

    def test_budget_rejects_when_max_calls_per_run_exceeded(self) -> None:
        policy = LLMBudgetPolicy(0, 1000, 100, 1000, 0.0, ["test_task"], True)
        allowed, reasons = check_llm_budget(policy, LLMBudgetState(), request())

        self.assertFalse(allowed)
        self.assertIn("max_calls_per_run_exceeded", reasons)

    def test_budget_rejects_when_input_tokens_exceed_per_call_limit(self) -> None:
        policy = LLMBudgetPolicy(1, 1, 100, 1000, 0.0, ["test_task"], True)
        allowed, reasons = check_llm_budget(policy, LLMBudgetState(), request("x" * 100))

        self.assertFalse(allowed)
        self.assertIn("max_input_tokens_per_call_exceeded", reasons)

    def test_budget_rejects_when_output_tokens_exceed_per_call_limit(self) -> None:
        policy = LLMBudgetPolicy(1, 1000, 5, 1000, 0.0, ["test_task"], True)
        allowed, reasons = check_llm_budget(policy, LLMBudgetState(), request(max_output_tokens=10))

        self.assertFalse(allowed)
        self.assertIn("max_output_tokens_per_call_exceeded", reasons)

    def test_budget_rejects_when_total_run_tokens_exceeded(self) -> None:
        policy = LLMBudgetPolicy(2, 1000, 100, 20, 0.0, ["test_task"], True)
        state = LLMBudgetState(total_tokens_used=19)
        allowed, reasons = check_llm_budget(policy, state, request("tiny", max_output_tokens=1))

        self.assertFalse(allowed)
        self.assertIn("max_total_tokens_per_run_exceeded", reasons)

    def test_budget_rejects_disallowed_task_type(self) -> None:
        policy = LLMBudgetPolicy(1, 1000, 100, 1000, 0.0, ["signal_review"], True)
        allowed, reasons = check_llm_budget(policy, LLMBudgetState(), request(task_type="cluster_synthesis"))

        self.assertFalse(allowed)
        self.assertIn("task_type_not_allowed", reasons)

    def test_circuit_breaker_open_rejects_requests(self) -> None:
        policy = default_local_preview_llm_budget_policy()
        state = LLMBudgetState(circuit_breaker_open=True)
        allowed, reasons = check_llm_budget(policy, state, request())

        self.assertFalse(allowed)
        self.assertIn("circuit_breaker_open", reasons)

    def test_record_llm_usage_updates_counters(self) -> None:
        policy = default_local_preview_llm_budget_policy()
        usage = LLMUsage(input_tokens=10, output_tokens=5, total_tokens=15, estimated_cost_usd=0.0)
        state = record_llm_usage(LLMBudgetState(), usage, policy)

        self.assertEqual(state.calls_used, 1)
        self.assertEqual(state.input_tokens_used, 10)
        self.assertEqual(state.output_tokens_used, 5)
        self.assertEqual(state.total_tokens_used, 15)
        self.assertFalse(state.circuit_breaker_open)

    def test_record_llm_usage_opens_circuit_breaker_when_limits_exceeded(self) -> None:
        policy = LLMBudgetPolicy(1, 100, 100, 10, 0.0, ["test_task"], True)
        usage = LLMUsage(input_tokens=8, output_tokens=5, total_tokens=13, estimated_cost_usd=0.0)
        state = record_llm_usage(LLMBudgetState(), usage, policy)

        self.assertTrue(state.circuit_breaker_open)
        self.assertIn("max_total_tokens_per_run_exceeded", state.rejection_reasons)

    def test_budget_circuit_breaker_model_opens_and_closes(self) -> None:
        breaker = LLMBudgetCircuitBreaker()

        self.assertFalse(breaker.is_open())
        breaker.open("manual_test")
        self.assertTrue(breaker.is_open())
        self.assertIn("manual_test", breaker.state.rejection_reasons)
        breaker.close()
        self.assertFalse(breaker.is_open())

    def test_disabled_budget_policy_fails_closed(self) -> None:
        allowed, reasons = check_llm_budget(default_disabled_llm_budget_policy(), LLMBudgetState(), request())

        self.assertFalse(allowed)
        self.assertIn("task_type_not_allowed", reasons)
        self.assertIn("max_calls_per_run_exceeded", reasons)

    def test_provider_factory_rejects_unknown_provider_deterministically(self) -> None:
        with self.assertRaises(ValueError):
            get_llm_provider("openai")

    def test_local_preview_budget_allows_llm_signal_review_task_type(self) -> None:
        policy = default_local_preview_llm_budget_policy()
        review_request = LLMRequest(
            task_type="llm_signal_review",
            messages=[LLMMessage("user", "review this signal")],
        )

        allowed, reasons = check_llm_budget(policy, LLMBudgetState(), review_request, estimated_output_tokens=20)

        self.assertTrue(allowed)
        self.assertEqual(reasons, [])

    def test_no_network_api_or_llm_calls_are_made(self) -> None:
        result = DeterministicMockLLMProvider().complete(request("No external call, just a fixture."))

        self.assertIsNotNone(result.response)
        self.assertFalse(result.response.external_calls_made)
        self.assertEqual(result.response.usage.estimated_cost_usd, 0.0)


if __name__ == "__main__":
    unittest.main()
