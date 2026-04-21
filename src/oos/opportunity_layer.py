from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence, Set

from .artifact_store import ArtifactStore
from .models import OpportunityCard, Signal, SignalStatus


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_opportunity_id() -> str:
    return f"opp_{uuid.uuid4().hex}"


@dataclass(frozen=True)
class OpportunityFramer:
    """
    Week 4: Create OpportunityCard artifacts from validated Signals.

    - Only validated signals are accepted by default.
    - Weak signals can be explicitly promoted via `promote_weak_signal_ids`.
    - Noise signals are never accepted.
    """

    store: ArtifactStore

    def frame_from_signals(
        self,
        signals: Sequence[Signal],
        *,
        opportunity_id: Optional[str] = None,
        promote_weak_signal_ids: Optional[Set[str]] = None,
        initial_notes: str = "",
        opportunity_type: str = "unknown",
    ) -> OpportunityCard:
        promote_weak_signal_ids = promote_weak_signal_ids or set()

        selected: List[Signal] = []
        for s in signals:
            if s.status == SignalStatus.validated:
                selected.append(s)
            elif s.status == SignalStatus.weak and s.id in promote_weak_signal_ids:
                selected.append(s)
            elif s.status == SignalStatus.noise:
                continue

        if not selected:
            raise ValueError("No eligible signals provided (validated or explicitly promoted weak).")

        # Minimal deterministic framing:
        # - title: first extracted pain (truncated)
        # - pain_summary: join extracted pains
        # - icp: most common candidate_icp among selected, fallback to first
        pains = [s.extracted_pain.strip() for s in selected if s.extracted_pain.strip()]
        if not pains:
            pains = [selected[0].raw_content.strip()[:200]]

        title = pains[0][:80]
        pain_summary = " | ".join(p[:200] for p in pains[:5])

        icp_counts = {}
        for s in selected:
            icp = (s.candidate_icp or "unknown").strip() or "unknown"
            icp_counts[icp] = icp_counts.get(icp, 0) + 1
        icp = sorted(icp_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

        why_it_matters = "Validated pain signals suggest recurring operational friction worth testing."

        now = _iso_utc_now_seconds()
        card = OpportunityCard(
            id=opportunity_id or _new_opportunity_id(),
            title=title,
            source_signal_ids=[s.id for s in selected],
            pain_summary=pain_summary,
            icp=icp,
            opportunity_type=opportunity_type,
            why_it_matters=why_it_matters,
            early_monetization_options=[],
            initial_notes=initial_notes,
            created_at=now,
            updated_at=now,
        )

        self.store.write_model(card)
        return card

