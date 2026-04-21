from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


DEFAULT_RULES: Dict[str, str] = {
    "signal": "cheap",
    "opportunity": "medium",
    "ideation": "strong",
    "screen": "medium",
    "hypothesis": "medium",
    "council": "strong",
    "portfolio": "cheap",
    "weekly_review": "cheap",
}


@dataclass(frozen=True)
class ModelRoutingConfig:
    rules_by_stage: Dict[str, str]


class ModelRouter:
    """
    Week 8: explicit, configurable model routing by stage.

    This does not execute models. It only selects a model class label
    (cheap/medium/strong) to keep routing explicit and testable.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.config = ModelRoutingConfig(rules_by_stage=dict(DEFAULT_RULES))
        if config_path is not None and config_path.exists():
            self.config = self._load(config_path)

    def select(self, stage: str) -> str:
        if stage not in self.config.rules_by_stage:
            raise ValueError(f"Unknown stage for routing: {stage}")
        return self.config.rules_by_stage[stage]

    def _load(self, path: Path) -> ModelRoutingConfig:
        data = json.loads(path.read_text(encoding="utf-8"))
        rules = data.get("rules_by_stage")
        if not isinstance(rules, dict):
            raise ValueError("model routing config must contain rules_by_stage dict")
        merged = dict(DEFAULT_RULES)
        for k, v in rules.items():
            merged[str(k)] = str(v)
        return ModelRoutingConfig(rules_by_stage=merged)

