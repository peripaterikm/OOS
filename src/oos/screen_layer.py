from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from .artifact_store import ArtifactStore
from .models import IdeaVariant, KillReason


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_kill_reason_id() -> str:
    return f"kr_{uuid.uuid4().hex}"


MANDATORY_CHECKS = [
    "pain_real_and_recurring",
    "icp_identifiable_and_can_pay",
    "productizable_systematizable",
    "market_not_closed",
    "founder_not_blocked_by_regulatory_gatekeeping",
]

ANTI_PATTERNS = [
    "custom_per_client_handling",  # disguised consulting
    "founder_bottleneck",
    "traffic_ads_monetization",
    "no_repeatable_workflow",
]


@dataclass(frozen=True)
class ScreenResult:
    outcome: str  # pass | park | kill
    failed_checks: List[str]
    matched_anti_patterns: List[str]
    rationale: str
    kill_reason_id: Optional[str] = None


class ScreenEvaluator:
    """
    Week 4 Screen Layer.

    Per docs:
    - kill if fails >=2 mandatory checks OR matches any anti-pattern.
    - output must be explicit: pass/park/kill + which checks failed + which anti-patterns matched.

    This implementation is deterministic and allows explicit overrides for testing.
    """

    _re_custom = re.compile(r"\b(custom|per[- ]client|bespoke|ручн\w*|под каждого)\b", re.IGNORECASE)
    _re_founder = re.compile(r"\b(founder|only me|только я|мо[её]|лично)\b", re.IGNORECASE)
    _re_ads = re.compile(r"\b(ads?|traffic|seo|arbitrage|реклама|трафик)\b", re.IGNORECASE)
    _re_repeatable = re.compile(r"\b(repeatable|standard|template|workflow|шаблон|стандарт|процесс)\b", re.IGNORECASE)

    def __init__(self, store: ArtifactStore):
        self.store = store

    def evaluate(
        self,
        idea: IdeaVariant,
        *,
        checks_override: Optional[Dict[str, bool]] = None,
        anti_patterns_override: Optional[Dict[str, bool]] = None,
    ) -> ScreenResult:
        checks_override = checks_override or {}
        anti_patterns_override = anti_patterns_override or {}

        failed_checks = [c for c in MANDATORY_CHECKS if checks_override.get(c) is False]
        matched_anti_patterns = [a for a in ANTI_PATTERNS if anti_patterns_override.get(a) is True]

        # If no overrides provided for a given item, use minimal heuristics.
        if "custom_per_client_handling" not in anti_patterns_override:
            if self._re_custom.search(idea.external_execution_needed) or self._re_custom.search(idea.short_concept):
                matched_anti_patterns.append("custom_per_client_handling")
        if "founder_bottleneck" not in anti_patterns_override:
            if self._re_founder.search(idea.external_execution_needed) or self._re_founder.search(idea.short_concept):
                matched_anti_patterns.append("founder_bottleneck")
        if "traffic_ads_monetization" not in anti_patterns_override:
            if self._re_ads.search(idea.business_model) or self._re_ads.search(idea.rough_monetization_model):
                matched_anti_patterns.append("traffic_ads_monetization")
        if "no_repeatable_workflow" not in anti_patterns_override:
            combined = " ".join([idea.standardization_focus, idea.short_concept])
            if not self._re_repeatable.search(combined):
                matched_anti_patterns.append("no_repeatable_workflow")

        # De-dup
        matched_anti_patterns = sorted(set(matched_anti_patterns))
        failed_checks = sorted(set(failed_checks))

        if matched_anti_patterns or len(failed_checks) >= 2:
            outcome = "kill"
        elif len(failed_checks) == 1:
            outcome = "park"
        else:
            outcome = "pass"

        rationale = self._build_rationale(outcome, failed_checks, matched_anti_patterns)

        kill_reason_id = None
        if outcome == "kill":
            kill = KillReason(
                id=_new_kill_reason_id(),
                idea_id=idea.id,
                kill_date=_iso_utc_now_seconds(),
                failed_checks=failed_checks,
                matched_anti_patterns=matched_anti_patterns,
                summary=rationale,
                looked_attractive_because=idea.short_concept[:200],
                notes="",
            )
            self.store.write_model(kill)
            kill_reason_id = kill.id

        return ScreenResult(
            outcome=outcome,
            failed_checks=failed_checks,
            matched_anti_patterns=matched_anti_patterns,
            rationale=rationale,
            kill_reason_id=kill_reason_id,
        )

    def _build_rationale(self, outcome: str, failed: List[str], anti: List[str]) -> str:
        if outcome == "pass":
            return "Passed mandatory checks and did not match immediate anti-patterns."
        if outcome == "park":
            return f"Parked due to 1 failed mandatory check: {', '.join(failed)}."
        if anti and failed:
            return f"Killed due to anti-patterns ({', '.join(anti)}) and failed checks ({', '.join(failed)})."
        if anti:
            return f"Killed due to anti-pattern(s): {', '.join(anti)}."
        return f"Killed due to failed mandatory checks: {', '.join(failed)}."

