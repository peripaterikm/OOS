from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Protocol


LLM_PROVIDER_ID_DISABLED = "disabled"
LLM_PROVIDER_ID_DETERMINISTIC_MOCK = "deterministic_mock"

LLM_PROVIDER_KIND_DISABLED = "disabled"
LLM_PROVIDER_KIND_DETERMINISTIC_MOCK = "deterministic_mock"
LLM_PROVIDER_KIND_FUTURE_EXTERNAL = "future_external"

LLM_ERROR_DISABLED = "llm_disabled"
LLM_ERROR_BUDGET_REJECTED = "llm_budget_rejected"

LLM_MESSAGE_ROLES = {"system", "user", "assistant"}
LLM_PROVIDER_KINDS = {
    LLM_PROVIDER_KIND_DISABLED,
    LLM_PROVIDER_KIND_DETERMINISTIC_MOCK,
    LLM_PROVIDER_KIND_FUTURE_EXTERNAL,
}

_ZERO_COST_MODELS = {
    None: 0.0,
    "": 0.0,
    "deterministic-mock": 0.0,
    "disabled": 0.0,
}


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in LLM_MESSAGE_ROLES:
            raise ValueError(f"Unsupported LLM message role: {self.role}")
        if not isinstance(self.content, str):
            raise ValueError("LLM message content must be a string")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LLMRequest:
    task_type: str
    messages: list[LLMMessage]
    model_hint: str | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    temperature: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_type:
            raise ValueError("LLM request task_type is required")
        if not self.messages:
            raise ValueError("LLM request must include at least one message")
        if not 0.0 <= float(self.temperature) <= 2.0:
            raise ValueError("LLM request temperature must be between 0.0 and 2.0")
        for field_name in ("max_input_tokens", "max_output_tokens"):
            value = getattr(self, field_name)
            if value is not None and int(value) < 0:
                raise ValueError(f"{field_name} must be non-negative when provided")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["messages"] = [message.to_dict() for message in self.messages]
        return data


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0 or self.total_tokens < 0:
            raise ValueError("LLM usage token counts must be non-negative")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("LLM usage total_tokens must equal input_tokens + output_tokens")
        if self.estimated_cost_usd < 0:
            raise ValueError("LLM estimated cost must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LLMResponse:
    provider_id: str
    model_name: str | None
    content: str
    usage: LLMUsage
    finish_reason: str
    external_calls_made: bool
    safety_notes: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["usage"] = self.usage.to_dict()
        return data


@dataclass(frozen=True)
class LLMProviderResult:
    is_available: bool
    response: LLMResponse | None = None
    error_code: str | None = None
    explanation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["response"] = self.response.to_dict() if self.response else None
        return data


class LLMProvider(Protocol):
    provider_id: str
    provider_kind: str

    def is_available(self) -> bool:
        ...

    def complete(self, request: LLMRequest) -> LLMProviderResult:
        ...


@dataclass(frozen=True)
class DisabledLLMProvider:
    provider_id: str = LLM_PROVIDER_ID_DISABLED
    provider_kind: str = LLM_PROVIDER_KIND_DISABLED

    def is_available(self) -> bool:
        return False

    def complete(self, request: LLMRequest) -> LLMProviderResult:
        return LLMProviderResult(
            is_available=False,
            response=None,
            error_code=LLM_ERROR_DISABLED,
            explanation=[
                "LLM provider is disabled by default.",
                "No external LLM/API call was made.",
            ],
        )


@dataclass(frozen=True)
class DeterministicMockLLMProvider:
    provider_id: str = LLM_PROVIDER_ID_DETERMINISTIC_MOCK
    provider_kind: str = LLM_PROVIDER_KIND_DETERMINISTIC_MOCK
    model_name: str = "deterministic-mock"

    def is_available(self) -> bool:
        return True

    def complete(self, request: LLMRequest) -> LLMProviderResult:
        request_text = _request_text(request)
        digest = hashlib.sha256(f"{request.task_type}\n{request_text}".encode("utf-8")).hexdigest()[:12]
        preview = " ".join(request_text.split())[:120]
        content = f"deterministic_mock:{request.task_type}:{digest}:{preview}"
        input_tokens = estimate_request_tokens(request)
        output_tokens = estimate_tokens(content)
        usage = LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=estimate_cost_usd(self.model_name, input_tokens, output_tokens),
        )
        response = LLMResponse(
            provider_id=self.provider_id,
            model_name=self.model_name,
            content=content,
            usage=usage,
            finish_reason="mock_complete",
            external_calls_made=False,
            safety_notes=["deterministic mock provider; no external calls", "not an intelligent model response"],
            metadata={"request_hash": digest, "task_type": request.task_type},
        )
        return LLMProviderResult(
            is_available=True,
            response=response,
            error_code=None,
            explanation=["deterministic mock completion generated locally"],
        )


@dataclass(frozen=True)
class LLMBudgetPolicy:
    max_calls_per_run: int
    max_input_tokens_per_call: int
    max_output_tokens_per_call: int
    max_total_tokens_per_run: int
    max_estimated_cost_usd_per_run: float
    allowed_task_types: list[str] = field(default_factory=list)
    circuit_breaker_enabled: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "max_calls_per_run",
            "max_input_tokens_per_call",
            "max_output_tokens_per_call",
            "max_total_tokens_per_run",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")
        if self.max_estimated_cost_usd_per_run < 0:
            raise ValueError("max_estimated_cost_usd_per_run must be non-negative")


@dataclass(frozen=True)
class LLMBudgetState:
    calls_used: int = 0
    input_tokens_used: int = 0
    output_tokens_used: int = 0
    total_tokens_used: int = 0
    estimated_cost_usd_used: float = 0.0
    circuit_breaker_open: bool = False
    rejection_reasons: list[str] = field(default_factory=list)

    def with_rejection(self, reasons: list[str]) -> LLMBudgetState:
        return replace(self, rejection_reasons=list(reasons))


class LLMBudgetCircuitBreaker:
    def __init__(self, state: LLMBudgetState | None = None) -> None:
        self.state = state or LLMBudgetState()

    def is_open(self) -> bool:
        return self.state.circuit_breaker_open

    def open(self, reason: str) -> LLMBudgetState:
        reasons = list(self.state.rejection_reasons)
        if reason not in reasons:
            reasons.append(reason)
        self.state = replace(self.state, circuit_breaker_open=True, rejection_reasons=reasons)
        return self.state

    def close(self) -> LLMBudgetState:
        self.state = replace(self.state, circuit_breaker_open=False)
        return self.state


def default_disabled_llm_budget_policy() -> LLMBudgetPolicy:
    return LLMBudgetPolicy(
        max_calls_per_run=0,
        max_input_tokens_per_call=0,
        max_output_tokens_per_call=0,
        max_total_tokens_per_run=0,
        max_estimated_cost_usd_per_run=0.0,
        allowed_task_types=[],
        circuit_breaker_enabled=True,
    )


def default_local_preview_llm_budget_policy() -> LLMBudgetPolicy:
    return LLMBudgetPolicy(
        max_calls_per_run=20,
        max_input_tokens_per_call=4000,
        max_output_tokens_per_call=800,
        max_total_tokens_per_run=20000,
        max_estimated_cost_usd_per_run=0.0,
        allowed_task_types=[
            "query_generator",
            "signal_review",
            "llm_signal_review",
            "cluster_synthesis",
            "query_refinement_advisor",
            "implied_burden_detection",
            "price_signal_extraction",
            "experiment_blueprint",
            "test_task",
        ],
        circuit_breaker_enabled=True,
    )


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(str(text)) / 4))


def estimate_request_tokens(request: LLMRequest) -> int:
    total = estimate_tokens(request.task_type)
    if request.model_hint:
        total += estimate_tokens(request.model_hint)
    for message in request.messages:
        total += estimate_tokens(message.role) + estimate_tokens(message.content)
    return total


def estimate_cost_usd(model_name: str | None, input_tokens: int, output_tokens: int) -> float:
    if model_name in _ZERO_COST_MODELS:
        return 0.0
    return 0.0


def check_llm_budget(
    policy: LLMBudgetPolicy,
    state: LLMBudgetState,
    request: LLMRequest,
    estimated_output_tokens: int | None = None,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    input_tokens = estimate_request_tokens(request)
    output_tokens = estimated_output_tokens if estimated_output_tokens is not None else request.max_output_tokens or 0
    if state.circuit_breaker_open:
        reasons.append("circuit_breaker_open")
    if not policy.allowed_task_types or request.task_type not in policy.allowed_task_types:
        reasons.append("task_type_not_allowed")
    if state.calls_used >= policy.max_calls_per_run:
        reasons.append("max_calls_per_run_exceeded")
    if input_tokens > policy.max_input_tokens_per_call:
        reasons.append("max_input_tokens_per_call_exceeded")
    if output_tokens > policy.max_output_tokens_per_call:
        reasons.append("max_output_tokens_per_call_exceeded")
    if state.total_tokens_used + input_tokens + output_tokens > policy.max_total_tokens_per_run:
        reasons.append("max_total_tokens_per_run_exceeded")
    estimated_cost = estimate_cost_usd(request.model_hint, input_tokens, output_tokens)
    if state.estimated_cost_usd_used + estimated_cost > policy.max_estimated_cost_usd_per_run:
        reasons.append("max_estimated_cost_usd_per_run_exceeded")
    return len(reasons) == 0, reasons


def record_llm_usage(state: LLMBudgetState, usage: LLMUsage, policy: LLMBudgetPolicy) -> LLMBudgetState:
    calls_used = state.calls_used + 1
    input_tokens_used = state.input_tokens_used + usage.input_tokens
    output_tokens_used = state.output_tokens_used + usage.output_tokens
    total_tokens_used = state.total_tokens_used + usage.total_tokens
    estimated_cost_usd_used = round(state.estimated_cost_usd_used + usage.estimated_cost_usd, 8)
    rejection_reasons = list(state.rejection_reasons)
    circuit_breaker_open = state.circuit_breaker_open

    if policy.circuit_breaker_enabled:
        if calls_used > policy.max_calls_per_run:
            rejection_reasons.append("max_calls_per_run_exceeded")
            circuit_breaker_open = True
        if input_tokens_used > policy.max_total_tokens_per_run or total_tokens_used > policy.max_total_tokens_per_run:
            rejection_reasons.append("max_total_tokens_per_run_exceeded")
            circuit_breaker_open = True
        if estimated_cost_usd_used > policy.max_estimated_cost_usd_per_run:
            rejection_reasons.append("max_estimated_cost_usd_per_run_exceeded")
            circuit_breaker_open = True

    return LLMBudgetState(
        calls_used=calls_used,
        input_tokens_used=input_tokens_used,
        output_tokens_used=output_tokens_used,
        total_tokens_used=total_tokens_used,
        estimated_cost_usd_used=estimated_cost_usd_used,
        circuit_breaker_open=circuit_breaker_open,
        rejection_reasons=_dedupe_preserving_order(rejection_reasons),
    )


def get_llm_provider(provider_id: str | None = None) -> LLMProvider:
    normalized_provider_id = (provider_id or LLM_PROVIDER_ID_DISABLED).strip().lower()
    if normalized_provider_id in {LLM_PROVIDER_ID_DISABLED, "none", "noop"}:
        return DisabledLLMProvider()
    if normalized_provider_id in {LLM_PROVIDER_ID_DETERMINISTIC_MOCK, "stub", "mock"}:
        return DeterministicMockLLMProvider()
    raise ValueError(f"Unknown LLM provider: {provider_id}")


def _request_text(request: LLMRequest) -> str:
    return "\n".join(f"{message.role}: {message.content}" for message in request.messages)


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
