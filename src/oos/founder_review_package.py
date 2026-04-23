from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class FounderReviewEntry:
    review_id: str
    entity_type: str
    entity_id: str
    title: str
    summary: str
    decision_options: List[str]
    linked_signal_ids: List[str]
    linked_artifact_ids: Dict[str, Any]


class FounderReviewPackageWriter:
    def __init__(self, artifacts_root: Path):
        self.artifacts_root = artifacts_root
        self.ops_dir = artifacts_root / "ops"

    @property
    def index_path(self) -> Path:
        return self.ops_dir / "founder_review_index.json"

    @property
    def inbox_path(self) -> Path:
        return self.ops_dir / "founder_review_inbox.md"

    def write(self, *, entries: List[FounderReviewEntry], project_root: Path) -> Dict[str, Path]:
        self.ops_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "founder_review_index_v1",
            "entries": [entry.__dict__ for entry in entries],
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.inbox_path.write_text(self._render_markdown(entries=entries, project_root=project_root), encoding="utf-8")
        return {"founder_review_index": self.index_path, "founder_review_inbox": self.inbox_path}

    def _render_markdown(self, *, entries: List[FounderReviewEntry], project_root: Path) -> str:
        lines = [
            "# Founder Review Inbox",
            "",
            "Use review IDs to record decisions without looking up internal artifact IDs.",
            "",
        ]
        for entry in entries:
            lines.extend(
                [
                    f"## {entry.review_id}: {entry.title}",
                    "",
                    f"- Entity: `{entry.entity_type}/{entry.entity_id}`",
                    f"- Summary: {entry.summary}",
                    f"- Linked signals: {', '.join(f'`{signal_id}`' for signal_id in entry.linked_signal_ids)}",
                    f"- Decision options: {', '.join(f'`{option}`' for option in entry.decision_options)}",
                    "",
                    "Record a decision:",
                    "",
                    "```powershell",
                    (
                        f".\\.venv\\Scripts\\python.exe -m oos.cli record-founder-review "
                        f"--project-root {project_root} --review-id {entry.review_id} --decision pass"
                    ),
                    "```",
                    "",
                ]
            )
        return "\n".join(lines)


class FounderReviewIndex:
    def __init__(self, artifacts_root: Path):
        self.path = artifacts_root / "ops" / "founder_review_index.json"

    def get_entry(self, review_id: str) -> FounderReviewEntry:
        if not self.path.exists():
            raise ValueError(f"Founder review index not found: expected {self.path}")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        entries = data.get("entries")
        if not isinstance(entries, list):
            raise ValueError(f"Founder review index is invalid: expected entries list in {self.path}")
        for entry in entries:
            if isinstance(entry, dict) and entry.get("review_id") == review_id:
                return FounderReviewEntry(
                    review_id=str(entry["review_id"]),
                    entity_type=str(entry["entity_type"]),
                    entity_id=str(entry["entity_id"]),
                    title=str(entry["title"]),
                    summary=str(entry["summary"]),
                    decision_options=[str(option) for option in entry["decision_options"]],
                    linked_signal_ids=[str(signal_id) for signal_id in entry["linked_signal_ids"]],
                    linked_artifact_ids=dict(entry["linked_artifact_ids"]),
                )
        raise ValueError(f"Founder review id not found: {review_id}")
