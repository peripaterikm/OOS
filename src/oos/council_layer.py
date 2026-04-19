from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence

from .artifact_store import ArtifactStore
from .models import CouncilDecision, IdeaVariant, KillReason


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_council_decision_id() -> str:
    return f"cd_{uuid.uuid4().hex}"


@dataclass(frozen=True)
class SkepticOutput:
    kill_scenarios: List[str]


@dataclass(frozen=True)
class AssumptionAuditorOutput:
    least_proven_critical_assumption: str


@dataclass(frozen=True)
class PatternMatcherOutput:
    similarity: List[str]


@dataclass(frozen=True)
class ChairOutput:
    final_recommendation: str
    notes: str = ""


class CouncilRoleEngine:
    """
    Interface for Council role generation.

    Week 6 provides a deterministic implementation.
    Any LLM-based council should be isolated behind this interface.
    """

    def skeptic(self, idea: IdeaVariant) -> SkepticOutput:  # pragma: no cover
        raise NotImplementedError

    def assumption_auditor(self, idea: IdeaVariant) -> AssumptionAuditorOutput:  # pragma: no cover
        raise NotImplementedError

    def pattern_matcher(self, idea: IdeaVariant, kill_archive: Sequence[KillReason]) -> PatternMatcherOutput:  # pragma: no cover
        raise NotImplementedError

    def chair(
        self,
        idea: IdeaVariant,
        skeptic: SkepticOutput,
        auditor: AssumptionAuditorOutput,
        matcher: PatternMatcherOutput,
    ) -> ChairOutput:  # pragma: no cover
        raise NotImplementedError


class DeterministicCouncilEngine(CouncilRoleEngine):
    """
    Deterministic, structured council generation.

    - No debates.
    - Outputs are explicit lists/strings suitable for artifacts and tests.
    """

    _re_custom = re.compile(r"\b(custom|per[- ]client|bespoke|ручн\w*|под каждого)\b", re.IGNORECASE)
    _re_founder = re.compile(r"\b(founder|only me|только я|лично)\b", re.IGNORECASE)
    _re_ads = re.compile(r"\b(ads?|traffic|seo|реклама|трафик)\b", re.IGNORECASE)

    def skeptic(self, idea: IdeaVariant) -> SkepticOutput:
        scenarios: List[str] = []

        combined = " ".join(
            [
                idea.short_concept,
                idea.business_model,
                idea.standardization_focus,
                idea.external_execution_needed,
                idea.rough_monetization_model,
            ]
        )
        if self._re_custom.search(combined):
            scenarios.append("Requires custom per-client handling → disguised consulting risk.")
        if self._re_founder.search(combined):
            scenarios.append("Core value depends on founder presence → founder bottleneck.")
        if self._re_ads.search(combined):
            scenarios.append("Monetization depends on traffic/ads → weak unit economics.")

        # Always include at least one generic failure mode only if nothing was found.
        # (This keeps the output structured but allows suspiciously_clean logic to trigger.)
        return SkepticOutput(kill_scenarios=scenarios)

    def assumption_auditor(self, idea: IdeaVariant) -> AssumptionAuditorOutput:
        # Default least-proven critical assumption for early stage: willingness to pay.
        return AssumptionAuditorOutput(
            least_proven_critical_assumption="The ICP is willing to pay for this as a product/system."
        )

    def pattern_matcher(self, idea: IdeaVariant, kill_archive: Sequence[KillReason]) -> PatternMatcherOutput:
        if not kill_archive:
            return PatternMatcherOutput(similarity=["Kill archive empty: no prior failures to compare."])

        idea_text = " ".join([idea.short_concept, idea.standardization_focus, idea.external_execution_needed]).lower()
        similar: List[str] = []
        for kr in kill_archive:
            # Similarity heuristic: overlap of anti-pattern tags OR keyword overlap in summary.
            overlap = set(kr.matched_anti_patterns)
            if any(tag in overlap for tag in ["custom_per_client_handling", "founder_bottleneck"]):
                if ("custom" in idea_text and "custom_per_client_handling" in overlap) or (
                    "founder" in idea_text and "founder_bottleneck" in overlap
                ):
                    similar.append(f"Similar to kill {kr.id}: anti-pattern overlap {sorted(list(overlap))}.")
                    continue
            # Fallback: simple keyword match against kill summary
            summary = (kr.summary or "").lower()
            if ("consult" in summary and "custom" in idea_text) or ("bottleneck" in summary and "founder" in idea_text):
                similar.append(f"Similar to kill {kr.id}: keyword overlap in summary.")

        if not similar:
            similar = ["No strong similarity found in current kill archive."]
        return PatternMatcherOutput(similarity=similar)

    def chair(
        self,
        idea: IdeaVariant,
        skeptic: SkepticOutput,
        auditor: AssumptionAuditorOutput,
        matcher: PatternMatcherOutput,
    ) -> ChairOutput:
        # Simple deterministic synthesis:
        # - If skeptic found multiple kill scenarios => "park"
        # - If one kill scenario => "park"
        # - If none => "proceed_to_hypothesis_tests"
        if len(skeptic.kill_scenarios) >= 1:
            rec = "park"
        else:
            rec = "proceed_to_hypothesis_tests"

        notes = (
            f"Auditor focus: {auditor.least_proven_critical_assumption} "
            f"| Pattern match: {matcher.similarity[0]}"
        )
        return ChairOutput(final_recommendation=rec, notes=notes[:500])


class KillArchiveReader:
    """
    Minimal reader for Kill Archive (KillReason artifacts) via ArtifactStore.
    """

    def __init__(self, store: ArtifactStore):
        self.store = store

    def list_kill_ids(self) -> List[str]:
        kills_dir = self.store.root_dir / "kills"
        if not kills_dir.exists():
            return []
        return [p.stem for p in kills_dir.glob("*.json")]

    def load_all(self) -> List[KillReason]:
        out: List[KillReason] = []
        for kid in self.list_kill_ids():
            out.append(self.store.read_model(KillReason, kid))
        return out


class CouncilLayer:
    """
    Week 6 Council Layer: structured council decision generation.
    """

    def __init__(self, artifacts_root: Path, engine: Optional[CouncilRoleEngine] = None):
        self.store = ArtifactStore(root_dir=artifacts_root)
        self.engine = engine or DeterministicCouncilEngine()
        self.kill_reader = KillArchiveReader(store=self.store)

    def generate_for_shortlisted_idea(self, idea: IdeaVariant, *, decision_id: Optional[str] = None) -> CouncilDecision:
        kills = self.kill_reader.load_all()

        skeptic_out = self.engine.skeptic(idea)
        auditor_out = self.engine.assumption_auditor(idea)
        matcher_out = self.engine.pattern_matcher(idea, kills)
        chair_out = self.engine.chair(idea, skeptic_out, auditor_out, matcher_out)

        suspiciously_clean = len(skeptic_out.kill_scenarios) <= 1

        decision = CouncilDecision(
            id=decision_id or _new_council_decision_id(),
            idea_id=idea.id,
            skeptic_kill_scenarios=skeptic_out.kill_scenarios,
            assumption_auditor_least_proven=auditor_out.least_proven_critical_assumption,
            pattern_matcher_similarity=matcher_out.similarity,
            final_recommendation=chair_out.final_recommendation,
            suspiciously_clean=suspiciously_clean,
            notes=chair_out.notes,
            created_at=_iso_utc_now_seconds(),
        )

        self.store.write_model(decision)
        return decision

