from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


AI_METADATA_REQUIRED_FIELDS = [
    "prompt_name",
    "prompt_version",
    "model_id",
    "input_hash",
    "generation_mode",
    "created_at",
    "linked_input_ids",
    "fallback_used",
    "stage_confidence",
    "stage_status",
]


class AIBudgetMode(str, Enum):
    economy = "economy"
    standard = "standard"
    deep = "deep"


class AIStageStatus(str, Enum):
    success = "success"
    failed = "failed"
    degraded = "degraded"


LLM_CALL_WARNING_THRESHOLDS = {
    AIBudgetMode.economy: 12,
    AIBudgetMode.standard: 25,
    AIBudgetMode.deep: 40,
}


def _utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def normalize_for_input_hash(payload: Any) -> str:
    return json.dumps(_json_safe(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_input_hash(payload: Any) -> str:
    normalized = normalize_for_input_hash(payload)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_cache_key(*, input_hash: str, prompt_version: str, model_id: str) -> str:
    for name, value in {
        "input_hash": input_hash,
        "prompt_version": prompt_version,
        "model_id": model_id,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
    return f"{input_hash}:{prompt_version}:{model_id}"


@dataclass(frozen=True)
class PromptIdentity:
    prompt_name: str
    prompt_version: str

    def validate(self) -> None:
        if not self.prompt_name.strip():
            raise ValueError("prompt_name must be a non-empty string")
        if not self.prompt_version.strip():
            raise ValueError("prompt_version must be a non-empty string")

    def to_dict(self) -> Dict[str, str]:
        self.validate()
        return {
            "prompt_name": self.prompt_name,
            "prompt_version": self.prompt_version,
        }


@dataclass(frozen=True)
class AIArtifactMetadata:
    prompt_name: str
    prompt_version: str
    model_id: str
    input_hash: str
    generation_mode: str
    linked_input_ids: List[str]
    fallback_used: bool
    stage_confidence: float
    stage_status: str
    created_at: str = field(default_factory=_utc_now_seconds)
    timeout_seconds: Optional[int] = None
    failure_reason: str = ""
    fallback_recommendation: str = ""
    degraded_mode: bool = False

    def validate(self) -> None:
        for field_name in AI_METADATA_REQUIRED_FIELDS:
            value = getattr(self, field_name)
            if isinstance(value, str) and not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.linked_input_ids, list):
            raise ValueError("linked_input_ids must be a list")
        if any(not isinstance(item, str) or not item.strip() for item in self.linked_input_ids):
            raise ValueError("linked_input_ids must contain non-empty strings")
        if not isinstance(self.fallback_used, bool):
            raise ValueError("fallback_used must be a bool")
        if not 0 <= self.stage_confidence <= 1:
            raise ValueError("stage_confidence must be between 0 and 1")
        if self.stage_status not in {status.value for status in AIStageStatus}:
            raise ValueError("stage_status must be success, failed, or degraded")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive when provided")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)

    @property
    def cache_key(self) -> str:
        return build_cache_key(
            input_hash=self.input_hash,
            prompt_version=self.prompt_version,
            model_id=self.model_id,
        )


@dataclass(frozen=True)
class LLMCallBudget:
    mode: AIBudgetMode
    expected_calls: int
    actual_calls: int = 0

    def validate(self) -> None:
        if self.expected_calls < 0:
            raise ValueError("expected_calls must be non-negative")
        if self.actual_calls < 0:
            raise ValueError("actual_calls must be non-negative")

    @property
    def warning_threshold(self) -> int:
        return LLM_CALL_WARNING_THRESHOLDS[self.mode]

    @property
    def warning_triggered(self) -> bool:
        self.validate()
        return self.actual_calls > self.warning_threshold

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "mode": self.mode.value,
            "expected_calls": self.expected_calls,
            "actual_calls": self.actual_calls,
            "warning_threshold": self.warning_threshold,
            "warning_triggered": self.warning_triggered,
        }


def build_ai_metadata(
    *,
    prompt: PromptIdentity,
    model_id: str,
    input_payload: Any,
    generation_mode: str,
    linked_input_ids: List[str],
    fallback_used: bool,
    stage_confidence: float,
    stage_status: AIStageStatus,
    timeout_seconds: Optional[int] = None,
    failure_reason: str = "",
    fallback_recommendation: str = "",
    degraded_mode: bool = False,
) -> AIArtifactMetadata:
    prompt.validate()
    return AIArtifactMetadata(
        prompt_name=prompt.prompt_name,
        prompt_version=prompt.prompt_version,
        model_id=model_id,
        input_hash=compute_input_hash(input_payload),
        generation_mode=generation_mode,
        linked_input_ids=linked_input_ids,
        fallback_used=fallback_used,
        stage_confidence=stage_confidence,
        stage_status=stage_status.value,
        timeout_seconds=timeout_seconds,
        failure_reason=failure_reason,
        fallback_recommendation=fallback_recommendation,
        degraded_mode=degraded_mode,
    )
