from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ALLOWED_AI_STAGE_RATINGS = {"good", "okay", "weak", "wrong"}
ALLOWED_AI_RATING_STAGES = {
    "signal understanding",
    "clustering",
    "opportunity framing",
    "ideation",
    "critique",
}


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


@dataclass(frozen=True)
class FounderAIStageRating:
    rating_id: str
    stage: str
    rating: str
    explanation: str
    linked_artifact_ids: List[str]
    linked_signal_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_iso_utc_now_seconds)
    founder: str = "founder"
    advisory_only: bool = True

    def validate(self) -> None:
        if not self.rating_id.strip():
            raise ValueError("rating_id is required")
        if self.stage not in ALLOWED_AI_RATING_STAGES:
            raise ValueError(f"stage must be one of: {sorted(ALLOWED_AI_RATING_STAGES)}")
        if self.rating not in ALLOWED_AI_STAGE_RATINGS:
            raise ValueError(f"rating must be one of: {sorted(ALLOWED_AI_STAGE_RATINGS)}")
        if not self.explanation.strip():
            raise ValueError("explanation is required")
        if not isinstance(self.linked_artifact_ids, list):
            raise ValueError("linked_artifact_ids must be a list")
        if not isinstance(self.linked_signal_ids, list):
            raise ValueError("linked_signal_ids must be a list")
        if not self.created_at.strip():
            raise ValueError("created_at is required")
        if not self.founder.strip():
            raise ValueError("founder is required")
        if self.advisory_only is not True:
            raise ValueError("founder AI-stage ratings are advisory/observational only")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FounderAIStageRating":
        rating = cls(
            rating_id=str(data.get("rating_id", "")),
            stage=str(data.get("stage", "")),
            rating=str(data.get("rating", "")),
            explanation=str(data.get("explanation", "")),
            linked_artifact_ids=[str(item) for item in data.get("linked_artifact_ids", [])],
            linked_signal_ids=[str(item) for item in data.get("linked_signal_ids", [])],
            created_at=str(data.get("created_at", "")),
            founder=str(data.get("founder", "founder")),
            advisory_only=bool(data.get("advisory_only", True)),
        )
        rating.validate()
        return rating


def build_rating_id(*, stage: str, rating: str, created_at: str) -> str:
    safe_timestamp = re.sub(r"[^0-9A-Za-z]+", "_", created_at).strip("_")
    return f"ai_stage_rating_{_slug(stage)}_{_slug(rating)}_{safe_timestamp}"


def write_ai_stage_rating(artifacts_root: Path, rating: FounderAIStageRating) -> Path:
    rating.validate()
    out_dir = artifacts_root / "ai_stage_ratings"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{rating.rating_id}.json"
    out_path.write_text(json.dumps(rating.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def record_ai_stage_rating(
    *,
    project_root: Path,
    stage: str,
    rating: str,
    explanation: str,
    linked_artifact_ids: List[str],
    linked_signal_ids: Optional[List[str]] = None,
    rating_id: Optional[str] = None,
    created_at: Optional[str] = None,
    founder: str = "founder",
) -> Path:
    created_at = created_at or _iso_utc_now_seconds()
    rating_id = rating_id or build_rating_id(stage=stage, rating=rating, created_at=created_at)
    artifact = FounderAIStageRating(
        rating_id=rating_id,
        stage=stage,
        rating=rating,
        explanation=explanation,
        linked_artifact_ids=linked_artifact_ids,
        linked_signal_ids=linked_signal_ids or [],
        created_at=created_at,
        founder=founder,
    )
    return write_ai_stage_rating(project_root / "artifacts", artifact)


def load_ai_stage_ratings(artifacts_root: Path) -> List[FounderAIStageRating]:
    rating_dir = artifacts_root / "ai_stage_ratings"
    if not rating_dir.exists():
        return []
    ratings: List[FounderAIStageRating] = []
    for path in sorted(rating_dir.glob("*.json")):
        ratings.append(FounderAIStageRating.from_dict(json.loads(path.read_text(encoding="utf-8"))))
    return ratings
