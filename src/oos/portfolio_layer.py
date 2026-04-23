from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .artifact_store import ArtifactStore
from .models import KillReason, PortfolioState, PortfolioStateEnum


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _portfolio_state_id(opportunity_id: str) -> str:
    # Stable ID per opportunity makes updates idempotent.
    return f"ps_{opportunity_id}"


ALLOWED_TRANSITIONS: Dict[PortfolioStateEnum, List[PortfolioStateEnum]] = {
    PortfolioStateEnum.Active: [PortfolioStateEnum.Parked, PortfolioStateEnum.Killed, PortfolioStateEnum.Graduated],
    PortfolioStateEnum.Parked: [PortfolioStateEnum.Active, PortfolioStateEnum.Killed],
    PortfolioStateEnum.Killed: [],
    PortfolioStateEnum.Graduated: [],
}


class PortfolioManager:
    """
    Week 7 Portfolio Layer: explicit storage + state transitions.

    - Persists PortfolioState via ArtifactStore (UTF-8 JSON).
    - Enforces minimal transition rules.
    - Requires explicit transition reasons.
    - Links kills to existing KillReason artifacts when transitioning to Killed.
    """

    def __init__(self, artifacts_root: Path):
        self.store = ArtifactStore(root_dir=artifacts_root)

    def get_state(self, opportunity_id: str) -> Optional[PortfolioState]:
        pid = _portfolio_state_id(opportunity_id)
        try:
            return self.store.read_model(PortfolioState, pid)
        except FileNotFoundError:
            return None

    def upsert_state(
        self,
        *,
        opportunity_id: str,
        state: PortfolioStateEnum,
        reason: str,
        linked_council_decision_id: Optional[str] = None,
        linked_kill_reason_id: Optional[str] = None,
        last_transition_at: Optional[str] = None,
    ) -> PortfolioState:
        if not reason or not str(reason).strip():
            raise ValueError("reason is required for PortfolioState")

        if state == PortfolioStateEnum.Killed:
            self._require_kill_reason(linked_kill_reason_id)

        ps = PortfolioState(
            id=_portfolio_state_id(opportunity_id),
            opportunity_id=opportunity_id,
            state=state,
            last_transition_at=last_transition_at or _iso_utc_now_seconds(),
            reason=reason,
            linked_council_decision_id=linked_council_decision_id,
            linked_kill_reason_id=linked_kill_reason_id,
        )
        self.store.write_model(ps)
        return ps

    def transition(
        self,
        *,
        opportunity_id: str,
        to_state: PortfolioStateEnum,
        reason: str,
        linked_council_decision_id: Optional[str] = None,
        linked_kill_reason_id: Optional[str] = None,
    ) -> PortfolioState:
        current = self.get_state(opportunity_id)
        if current is None:
            # Creation is allowed only into Active or Parked (explicitly).
            if to_state not in (PortfolioStateEnum.Active, PortfolioStateEnum.Parked):
                raise ValueError("Initial portfolio state must be Active or Parked")
            return self.upsert_state(
                opportunity_id=opportunity_id,
                state=to_state,
                reason=reason,
                linked_council_decision_id=linked_council_decision_id,
                linked_kill_reason_id=linked_kill_reason_id,
            )

        allowed = ALLOWED_TRANSITIONS[current.state]
        if to_state not in allowed and to_state != current.state:
            raise ValueError(f"Transition {current.state.value} -> {to_state.value} is not allowed")

        # Disallow no-op without a new reason (forces explicitness in audit trail).
        if to_state == current.state and (not reason or reason.strip() == current.reason.strip()):
            raise ValueError("No-op transition requires a new explicit reason")

        # If moving into Killed, require KillReason id and ensure it exists.
        if to_state == PortfolioStateEnum.Killed:
            self._require_kill_reason(linked_kill_reason_id)

        return self.upsert_state(
            opportunity_id=opportunity_id,
            state=to_state,
            reason=reason,
            linked_council_decision_id=linked_council_decision_id or current.linked_council_decision_id,
            linked_kill_reason_id=linked_kill_reason_id or current.linked_kill_reason_id,
        )

    def list_all(self) -> List[PortfolioState]:
        portfolio_dir = self.store.root_dir / "portfolio"
        if not portfolio_dir.exists():
            return []
        states: List[PortfolioState] = []
        for p in sorted(portfolio_dir.glob("*.json")):
            states.append(self.store.read_model(PortfolioState, p.stem))
        return states

    def _require_kill_reason(self, kill_reason_id: Optional[str]) -> None:
        if not kill_reason_id or not str(kill_reason_id).strip():
            raise ValueError("linked_kill_reason_id is required when state=Killed")
        # Ensure kill reason exists in Kill Archive.
        _ = self.store.read_model(KillReason, kill_reason_id)

