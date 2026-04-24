from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .ai_contracts import AIStageStatus, PromptIdentity, build_ai_metadata
from .artifact_store import ArtifactStore
from .models import IdeationGenerationMode, IdeaScreenStatus, IdeaVariant, OpportunityCard


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_idea_id() -> str:
    return f"idea_{uuid.uuid4().hex}"


IDEATION_PROMPT = PromptIdentity(prompt_name="ideation_constrained", prompt_version="ideation_constrained_v1")
IDEATION_MODEL_ID = "static_json_ai_ideation_provider"


def _opportunity_input_payload(opportunity: OpportunityCard) -> Dict[str, Any]:
    return {
        "id": opportunity.id,
        "title": opportunity.title,
        "source_signal_ids": opportunity.source_signal_ids,
        "pain_summary": opportunity.pain_summary,
        "icp": opportunity.icp,
        "opportunity_type": opportunity.opportunity_type,
        "why_it_matters": opportunity.why_it_matters,
    }


class IdeationEngine:
    """
    Interface for ideation.

    Week 4 provides a deterministic constrained stub implementation.
    Any future LLM-based ideation should be isolated behind this interface.
    """

    def generate(self, opportunity: OpportunityCard) -> List[IdeaVariant]:  # pragma: no cover
        raise NotImplementedError


class AIIdeationProvider:
    """
    Narrow provider boundary for optional model-assisted ideation.

    Implementations must return simple dict payloads that can be converted to
    IdeaVariant without changing downstream contracts.
    """

    def generate(self, opportunity: OpportunityCard) -> List[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class DeterministicIdeationStub(IdeationEngine):
    """
    Minimal constrained heuristic ideation baseline.

    Produces 1–2 IdeaVariant objects that are:
    - tied to the OpportunityCard pain/ICP,
    - product/system oriented,
    - not generic "AI assistant for everyone".

    This path is baseline / fallback / control-group plumbing, not the
    primary intelligence layer for strong opportunity discovery.
    """

    store: Optional[ArtifactStore] = None
    generation_mode: IdeationGenerationMode = IdeationGenerationMode.heuristic_baseline
    ai_metadata: Optional[Dict[str, Any]] = None

    def generate(self, opportunity: OpportunityCard) -> List[IdeaVariant]:
        now = _iso_utc_now_seconds()
        base = f"{opportunity.icp}: {opportunity.pain_summary[:120]}"

        ideas: List[IdeaVariant] = []
        ideas.append(
            IdeaVariant(
                id=_new_idea_id(),
                opportunity_id=opportunity.id,
                short_concept=f"Structured intake + standardized workflow to reduce: {base}",
                business_model="subscription",
                standardization_focus="fixed intake schema + repeatable workflow steps + templates",
                ai_leverage="extraction/classification of inputs into structured fields",
                external_execution_needed="none",
                rough_monetization_model="tiered subscription by seat or volume",
                status=IdeaScreenStatus.candidate,
                generation_mode=self.generation_mode,
                ai_metadata=self.ai_metadata,
                screen_result_id=None,
                created_at=now,
                updated_at=now,
            )
        )

        # Optional second variant: focused “validator” mode
        ideas.append(
            IdeaVariant(
                id=_new_idea_id(),
                opportunity_id=opportunity.id,
                short_concept=f"Validation assistant to catch errors early in: {base}",
                business_model="subscription",
                standardization_focus="ruleset templates + checklists + standardized outputs",
                ai_leverage="anomaly detection + summarization of failures and root causes",
                external_execution_needed="none",
                rough_monetization_model="subscription with usage-based add-on",
                status=IdeaScreenStatus.candidate,
                generation_mode=self.generation_mode,
                ai_metadata=self.ai_metadata,
                screen_result_id=None,
                created_at=now,
                updated_at=now,
            )
        )

        if self.store is not None:
            for i in ideas:
                self.store.write_model(i)

        return ideas


@dataclass(frozen=True)
class StaticJSONAIIdeationProvider(AIIdeationProvider):
    response_json: str

    def generate(self, opportunity: OpportunityCard) -> List[Dict[str, Any]]:
        if not self.response_json.strip():
            raise ValueError("AI ideation response payload is unavailable")
        data = json.loads(self.response_json)
        if not isinstance(data, list):
            raise ValueError("AI ideation response must be a JSON list")
        return data


@dataclass(frozen=True)
class SafeAIIdeationAdapter(IdeationEngine):
    store: Optional[ArtifactStore]
    deterministic: IdeationEngine
    provider: AIIdeationProvider

    def generate(self, opportunity: OpportunityCard) -> List[IdeaVariant]:
        try:
            ideas = self._generate_ai_ideas(opportunity)
        except Exception as exc:
            return self._generate_heuristic_fallback(opportunity, failure_reason=str(exc))

        if not ideas:
            return self._generate_heuristic_fallback(opportunity, failure_reason="AI ideation returned no ideas")

        if self.store is not None:
            for idea in ideas:
                self.store.write_model(idea)
        return ideas

    def _generate_heuristic_fallback(self, opportunity: OpportunityCard, *, failure_reason: str) -> List[IdeaVariant]:
        metadata = build_ai_metadata(
            prompt=IDEATION_PROMPT,
            model_id=IDEATION_MODEL_ID,
            input_payload=_opportunity_input_payload(opportunity),
            generation_mode=IdeationGenerationMode.heuristic_fallback_after_llm_failure.value,
            linked_input_ids=opportunity.source_signal_ids,
            fallback_used=True,
            stage_confidence=0.0,
            stage_status=AIStageStatus.degraded,
            failure_reason=failure_reason,
            fallback_recommendation="Use heuristic fallback output only for pipeline continuity.",
            degraded_mode=True,
        ).to_dict()
        if isinstance(self.deterministic, DeterministicIdeationStub):
            return DeterministicIdeationStub(
                store=self.deterministic.store,
                generation_mode=IdeationGenerationMode.heuristic_fallback_after_llm_failure,
                ai_metadata=metadata,
            ).generate(opportunity)
        return self.deterministic.generate(opportunity)

    def _generate_ai_ideas(self, opportunity: OpportunityCard) -> List[IdeaVariant]:
        now = _iso_utc_now_seconds()
        metadata = build_ai_metadata(
            prompt=IDEATION_PROMPT,
            model_id=IDEATION_MODEL_ID,
            input_payload=_opportunity_input_payload(opportunity),
            generation_mode=IdeationGenerationMode.llm_assisted.value,
            linked_input_ids=opportunity.source_signal_ids,
            fallback_used=False,
            stage_confidence=1.0,
            stage_status=AIStageStatus.success,
        ).to_dict()
        ideas: List[IdeaVariant] = []
        for raw in self.provider.generate(opportunity):
            if not isinstance(raw, dict):
                raise ValueError("AI ideation item must be a JSON object")
            idea = IdeaVariant(
                id=str(raw.get("id") or _new_idea_id()),
                opportunity_id=opportunity.id,
                short_concept=str(raw.get("short_concept") or "").strip(),
                business_model=str(raw.get("business_model") or "").strip(),
                standardization_focus=str(raw.get("standardization_focus") or "").strip(),
                ai_leverage=str(raw.get("ai_leverage") or "").strip(),
                external_execution_needed=str(raw.get("external_execution_needed") or "none").strip(),
                rough_monetization_model=str(raw.get("rough_monetization_model") or "").strip(),
                status=IdeaScreenStatus.candidate,
                generation_mode=IdeationGenerationMode.llm_assisted,
                ai_metadata=metadata,
                screen_result_id=None,
                created_at=now,
                updated_at=now,
            )
            idea.validate()
            ideas.append(idea)
        return ideas


def build_ideation_engine(
    *,
    store: Optional[ArtifactStore],
    ai_enabled: bool,
    ai_response_json: str = "",
    provider: Optional[AIIdeationProvider] = None,
) -> IdeationEngine:
    deterministic = DeterministicIdeationStub(store=store)
    if not ai_enabled:
        return deterministic
    return SafeAIIdeationAdapter(
        store=store,
        deterministic=deterministic,
        provider=provider or StaticJSONAIIdeationProvider(response_json=ai_response_json),
    )

