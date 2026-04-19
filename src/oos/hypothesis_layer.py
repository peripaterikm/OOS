from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from .artifact_store import ArtifactStore
from .models import Experiment, Hypothesis, IdeaVariant


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_hypothesis_id() -> str:
    return f"hyp_{uuid.uuid4().hex}"


def _new_experiment_id() -> str:
    return f"exp_{uuid.uuid4().hex}"


class HypothesisGenerator:
    """
    Interface for generating Hypothesis/Experiment artifacts.

    Week 5 uses a deterministic implementation to keep outputs testable.
    Any future LLM-based generator should be isolated behind this interface.
    """

    def generate_hypothesis(self, idea: IdeaVariant) -> Hypothesis:  # pragma: no cover
        raise NotImplementedError

    def generate_experiment(self, idea: IdeaVariant, hypothesis: Hypothesis) -> Experiment:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class DeterministicHypothesisGenerator(HypothesisGenerator):
    """
    Deterministic, inspectable generator (no LLMs).

    Produces small, structured outputs aligned with `docs/scope-v1.md`:
    - critical assumptions,
    - most fragile assumption,
    - success signals,
    - kill criteria,
    plus an Experiment with cheapest-next test and 7/14 day plans.
    """

    def generate_hypothesis(self, idea: IdeaVariant) -> Hypothesis:
        # Keep assumptions concrete and tied to the IdeaVariant.
        assumptions = [
            "The pain is real and recurring for the target segment.",
            "The workflow can be standardized enough to productize.",
            "The target segment is willing to pay for a product/system.",
        ]

        # Most fragile assumption heuristic: willingness to pay is typically least proven early.
        most_fragile = "The target segment is willing to pay for a product/system."

        success_signals = [
            "At least 7/10 target users confirm the pain and current workaround.",
            "At least 3 target users agree to a follow-up test or pilot.",
        ]

        kill_criteria = [
            "Most interviews show the pain is rare or low-priority.",
            "No credible willingness to pay or no path to productization appears.",
        ]

        return Hypothesis(
            id=_new_hypothesis_id(),
            idea_id=idea.id,
            critical_assumptions=assumptions,
            most_fragile_assumption=most_fragile,
            success_signals=success_signals,
            kill_criteria=kill_criteria,
            notes=f"Derived from idea: {idea.short_concept[:140]}",
        )

    def generate_experiment(self, idea: IdeaVariant, hypothesis: Hypothesis) -> Experiment:
        # Keep a single cheap, founder-friendly validation plan (no build required).
        cheapest_next = (
            "Run 10 structured interviews with the ICP and validate: pain recurrence, workaround, and willingness to pay."
        )

        plan_7d = (
            "Days 1–2: recruit 5 ICP interviews.\n"
            "Days 3–5: run 5 interviews using a fixed script; capture evidence.\n"
            "Days 6–7: summarize patterns and update kill/pass decision."
        )

        plan_14d = (
            "Days 1–7: complete 10 ICP interviews.\n"
            "Days 8–10: create a simple clickable mock or structured workflow demo (no full build).\n"
            "Days 11–14: test the demo with 3 ICP users and capture objections + pricing signals."
        )

        success_metrics: Dict[str, Any] = {
            "interviews_completed": 10,
            "pain_confirm_rate_min": 0.7,
            "followup_interest_min": 3,
        }
        failure_metrics: Dict[str, Any] = {
            "pain_confirm_rate_max": 0.3,
            "followup_interest_max": 0,
        }

        now = _iso_utc_now_seconds()
        return Experiment(
            id=_new_experiment_id(),
            idea_id=idea.id,
            hypothesis_id=hypothesis.id,
            cheapest_next_test=cheapest_next,
            plan_7d=plan_7d,
            plan_14d=plan_14d,
            success_metrics=success_metrics,
            failure_metrics=failure_metrics,
            status="planned",
            results_summary="",
            created_at=now,
            updated_at=now,
        )


class HypothesisLayer:
    """
    Week 5 Hypothesis Layer.

    Input: surviving ideas after Screen (pass or park).
    Output: persisted Hypothesis and Experiment artifacts (UTF-8 JSON via ArtifactStore).
    """

    def __init__(self, artifacts_root, generator: Optional[HypothesisGenerator] = None):
        self.store = ArtifactStore(root_dir=artifacts_root)
        self.generator = generator or DeterministicHypothesisGenerator()

    def generate_for_screened_idea(
        self,
        idea: IdeaVariant,
        *,
        screen_outcome: str,
    ) -> Optional[Tuple[Hypothesis, Experiment]]:
        """
        Generate artifacts only for survivors.

        - pass / park => generate Hypothesis + Experiment
        - kill => return None
        """
        if screen_outcome not in {"pass", "park", "kill"}:
            raise ValueError("screen_outcome must be one of: pass, park, kill")

        if screen_outcome == "kill":
            return None

        hyp = self.generator.generate_hypothesis(idea)
        exp = self.generator.generate_experiment(idea, hyp)

        self.store.write_model(hyp)
        self.store.write_model(exp)

        return hyp, exp

