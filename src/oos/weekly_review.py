from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .artifact_store import ArtifactStore
from .portfolio_layer import PortfolioManager
from .models import FounderReviewDecision, PortfolioState, PortfolioStateEnum


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _week_key(dt: datetime) -> str:
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


TAGS = {
    "needs_review": "[needs_review]",
    "recommend_kill": "[recommend_kill]",
    "recommend_park": "[recommend_park]",
    "recommend_graduate": "[recommend_graduate]",
}


@dataclass(frozen=True)
class WeeklyReviewPackage:
    """
    Deterministic weekly portfolio summary package.

    Stored as a plain UTF-8 JSON file (explicit, inspectable).
    PortfolioState artifacts remain persisted via ArtifactStore.

    Tagging convention (explicit, optional):
    - include any of these markers in PortfolioState.reason:
      [needs_review], [recommend_kill], [recommend_park], [recommend_graduate]
    """

    week: str
    created_at: str
    counts: Dict[str, int]
    by_state: Dict[str, List[str]]
    needs_founder_review: List[str]
    should_be_killed: List[str]
    should_be_parked: List[str]
    may_be_graduated: List[str]
    killed_with_kill_links: Dict[str, str]
    recent_founder_reviews: List[Dict[str, Any]]
    notes: str = ""


class WeeklyReviewGenerator:
    def __init__(self, artifacts_root: Path):
        self.artifacts_root = artifacts_root
        self.portfolio = PortfolioManager(artifacts_root=artifacts_root)

    def generate(self, now: datetime | None = None) -> Path:
        now = now or datetime.now(timezone.utc)
        states = self.portfolio.list_all()

        by_state: Dict[str, List[str]] = {
            PortfolioStateEnum.Active.value: [],
            PortfolioStateEnum.Parked.value: [],
            PortfolioStateEnum.Killed.value: [],
            PortfolioStateEnum.Graduated.value: [],
        }
        for ps in states:
            by_state[ps.state.value].append(ps.opportunity_id)

        needs_review = self._select_by_tag(states, TAGS["needs_review"])
        should_kill = self._select_by_tag(states, TAGS["recommend_kill"])
        should_park = self._select_by_tag(states, TAGS["recommend_park"])
        may_graduate = self._select_by_tag(states, TAGS["recommend_graduate"])

        killed_links: Dict[str, str] = {}
        for ps in states:
            if ps.state == PortfolioStateEnum.Killed and ps.linked_kill_reason_id:
                killed_links[ps.opportunity_id] = ps.linked_kill_reason_id

        pkg = WeeklyReviewPackage(
            week=_week_key(now),
            created_at=_iso_utc_now_seconds(),
            counts={k: len(v) for k, v in by_state.items()},
            by_state=by_state,
            needs_founder_review=sorted(set(needs_review)),
            should_be_killed=sorted(set(should_kill)),
            should_be_parked=sorted(set(should_park)),
            may_be_graduated=sorted(set(may_graduate)),
            killed_with_kill_links=killed_links,
            recent_founder_reviews=self._load_recent_founder_reviews(),
            notes=(
                "Deterministic weekly summary. Add explicit tags in PortfolioState.reason to surface decisions. "
                "Founder review decisions are surfaced from founder_reviews artifacts when present."
            ),
        )

        out_dir = self.artifacts_root / "weekly_reviews"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"weekly_review_{pkg.week}.json"
        out_path.write_text(json.dumps(pkg.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path

    def _select_by_tag(self, states: List[PortfolioState], tag: str) -> List[str]:
        out: List[str] = []
        for ps in states:
            if tag in (ps.reason or ""):
                out.append(ps.opportunity_id)
        return out

    def _load_recent_founder_reviews(self) -> List[Dict[str, Any]]:
        review_dir = self.artifacts_root / "founder_reviews"
        if not review_dir.exists():
            return []

        store = ArtifactStore(root_dir=self.artifacts_root)
        reviews: List[FounderReviewDecision] = []
        for path in review_dir.glob("*.json"):
            reviews.append(store.read_model(FounderReviewDecision, path.stem))

        reviews.sort(key=lambda review: (review.timestamp, review.id), reverse=True)
        return [self._format_founder_review(review) for review in reviews]

    def _format_founder_review(self, review: FounderReviewDecision) -> Dict[str, Any]:
        linked_evidence_ids: Dict[str, Any] = {}
        if review.readiness_report_id:
            linked_evidence_ids["readiness_report_id"] = review.readiness_report_id
        if review.weekly_review_id:
            linked_evidence_ids["weekly_review_id"] = review.weekly_review_id
        if review.council_decision_ids:
            linked_evidence_ids["council_decision_ids"] = review.council_decision_ids
        if review.hypothesis_ids:
            linked_evidence_ids["hypothesis_ids"] = review.hypothesis_ids
        if review.experiment_ids:
            linked_evidence_ids["experiment_ids"] = review.experiment_ids
        if review.linked_kill_reason_id:
            linked_evidence_ids["linked_kill_reason_id"] = review.linked_kill_reason_id

        return {
            "id": review.id,
            "review_id": review.review_id,
            "opportunity_id": review.opportunity_id,
            "decision": review.decision.value,
            "reason": review.reason,
            "selected_next_action": review.selected_next_experiment_or_action,
            "timestamp": review.timestamp,
            "linked_signal_ids": review.linked_signal_ids,
            "linked_evidence_ids": linked_evidence_ids,
        }

