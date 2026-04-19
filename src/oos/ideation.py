from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from .artifact_store import ArtifactStore
from .models import IdeaScreenStatus, IdeaVariant, OpportunityCard


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


@dataclass(frozen=True)
class DeterministicIdeationStub(IdeationEngine):
    """
    Minimal constrained ideation stub.

    Produces 1–2 IdeaVariant objects that are:
    - tied to the OpportunityCard pain/ICP,
    - product/system oriented,
    - not generic "AI assistant for everyone".
    """

    store: Optional[ArtifactStore] = None

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
                screen_result_id=None,
                created_at=now,
                updated_at=now,
            )
        )

        if self.store is not None:
            for i in ideas:
                self.store.write_model(i)

        return ideas

