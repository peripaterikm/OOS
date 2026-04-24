from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .artifact_store import ArtifactStore
from .models import IdeationGenerationMode, IdeaScreenStatus, IdeaVariant, OpportunityCard


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_idea_id() -> str:
    return f"idea_{uuid.uuid4().hex}"


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
        except Exception:
            return self._generate_heuristic_fallback(opportunity)

        if not ideas:
            return self._generate_heuristic_fallback(opportunity)

        if self.store is not None:
            for idea in ideas:
                self.store.write_model(idea)
        return ideas

    def _generate_heuristic_fallback(self, opportunity: OpportunityCard) -> List[IdeaVariant]:
        if isinstance(self.deterministic, DeterministicIdeationStub):
            return DeterministicIdeationStub(
                store=self.deterministic.store,
                generation_mode=IdeationGenerationMode.heuristic_fallback_after_llm_failure,
            ).generate(opportunity)
        return self.deterministic.generate(opportunity)

    def _generate_ai_ideas(self, opportunity: OpportunityCard) -> List[IdeaVariant]:
        now = _iso_utc_now_seconds()
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

