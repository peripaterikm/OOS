from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List


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
    V2_SECTIONS = [
        "signals",
        "dedup",
        "clusters",
        "opportunities",
        "ideas",
        "anti_patterns",
        "critiques",
        "decisions",
        "ai_quality",
    ]

    def __init__(self, artifacts_root: Path):
        self.artifacts_root = artifacts_root
        self.ops_dir = artifacts_root / "ops"
        self.review_dir = artifacts_root / "founder_review"
        self.sections_dir = self.review_dir / "sections"

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
        v2_paths = self._write_v2(entries=entries, project_root=project_root)
        return {
            "founder_review_index": self.index_path,
            "founder_review_inbox": self.inbox_path,
            **v2_paths,
        }

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

    @property
    def v2_index_path(self) -> Path:
        return self.review_dir / "index.json"

    @property
    def v2_inbox_path(self) -> Path:
        return self.review_dir / "inbox.md"

    def _write_v2(self, *, entries: List[FounderReviewEntry], project_root: Path) -> Dict[str, Path]:
        self.sections_dir.mkdir(parents=True, exist_ok=True)
        section_paths: Dict[str, Path] = {}
        for section in self.V2_SECTIONS:
            path = self.sections_dir / f"{section}.md"
            path.write_text(
                self._render_section(section=section, entries=entries, project_root=project_root),
                encoding="utf-8",
            )
            section_paths[f"founder_review_{section}_section"] = path

        index_payload = {
            "version": "founder_review_package_v2",
            "review_ids": [entry.review_id for entry in entries],
            "legacy_index": _relative_path(self.index_path, self.artifacts_root),
            "legacy_inbox": _relative_path(self.inbox_path, self.artifacts_root),
            "inbox": _relative_path(self.v2_inbox_path, self.artifacts_root),
            "sections": {
                section: _relative_path(self.sections_dir / f"{section}.md", self.artifacts_root)
                for section in self.V2_SECTIONS
            },
            "entries": [entry.__dict__ for entry in entries],
        }
        self.v2_index_path.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.v2_inbox_path.write_text(self._render_v2_inbox(entries=entries, project_root=project_root), encoding="utf-8")
        return {
            "founder_review_v2_index": self.v2_index_path,
            "founder_review_v2_inbox": self.v2_inbox_path,
            **section_paths,
        }

    def _render_v2_inbox(self, *, entries: List[FounderReviewEntry], project_root: Path) -> str:
        lines = [
            "# Founder Review Package v2",
            "",
            "This inbox links the founder to reviewable AI meaning-loop sections without artifact hunting.",
            "",
            "## Sections",
            "",
        ]
        for section in self.V2_SECTIONS:
            lines.append(f"- [{section}](sections/{section}.md)")
        lines.extend(["", "## Reviewable Items", ""])
        for entry in entries:
            lines.extend(
                [
                    f"### {entry.review_id}: {entry.title}",
                    "",
                    f"- Entity: `{entry.entity_type}/{entry.entity_id}`",
                    f"- Summary: {entry.summary}",
                    f"- Linked signals: {_format_inline_ids(entry.linked_signal_ids)}",
                    f"- Decision options: {_format_inline_ids(entry.decision_options)}",
                    f"- Source artifacts: {_format_artifact_links(entry.linked_artifact_ids)}",
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

    def _render_section(self, *, section: str, entries: List[FounderReviewEntry], project_root: Path) -> str:
        title = section.replace("_", " ").title()
        lines = [
            f"# {title}",
            "",
            "Generated as part of FounderReviewPackage v2. Missing optional AI-stage artifacts are shown as not available.",
            "",
        ]
        if section == "signals":
            lines.extend(self._render_signal_section(entries))
        elif section == "decisions":
            lines.extend(self._render_decision_section(entries=entries, project_root=project_root))
        else:
            lines.extend(self._render_artifact_section(section=section, entries=entries))
        return "\n".join(lines)

    def _render_signal_section(self, entries: List[FounderReviewEntry]) -> List[str]:
        lines = ["## Linked Signals", ""]
        signal_ids = sorted({signal_id for entry in entries for signal_id in entry.linked_signal_ids})
        if not signal_ids:
            return lines + ["- No linked signals available.", ""]
        for signal_id in signal_ids:
            path = self.artifacts_root / "signals" / f"{signal_id}.json"
            lines.append(f"- `{signal_id}` — {_link_or_missing(path)}")
        lines.append("")
        return lines

    def _render_decision_section(self, *, entries: List[FounderReviewEntry], project_root: Path) -> List[str]:
        lines = ["## Decision Commands", ""]
        for entry in entries:
            lines.extend(
                [
                    f"### {entry.review_id}",
                    "",
                    f"- Entity: `{entry.entity_type}/{entry.entity_id}`",
                    f"- Decision options: {_format_inline_ids(entry.decision_options)}",
                    "- Command:",
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
        return lines

    def _render_artifact_section(self, *, section: str, entries: List[FounderReviewEntry]) -> List[str]:
        lines = ["## Review Links", ""]
        section_keys = _section_artifact_keys(section)
        found = False
        for entry in entries:
            links = []
            for key in section_keys:
                raw = entry.linked_artifact_ids.get(key)
                for artifact_id in _as_list(raw):
                    links.append(f"`{key}:{artifact_id}`")
            if links:
                found = True
                lines.append(f"- `{entry.review_id}`: {', '.join(links)}")
        if not found:
            discovered = list(self._discover_section_artifacts(section))
            if discovered:
                found = True
                for path in discovered:
                    lines.append(f"- {_link_or_missing(path)}")
        if not found:
            lines.append("- Optional artifacts not available yet for this package.")
        lines.append("")
        return lines

    def _discover_section_artifacts(self, section: str) -> Iterable[Path]:
        for directory in _section_directories(section):
            path = self.artifacts_root / directory
            if path.exists():
                yield from sorted(path.glob("*.json"))[:10]


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


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _format_inline_ids(values: List[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "`none`"


def _format_artifact_links(linked_artifact_ids: Dict[str, Any]) -> str:
    parts = []
    for key in sorted(linked_artifact_ids):
        for value in _as_list(linked_artifact_ids[key]):
            parts.append(f"`{key}:{value}`")
    return ", ".join(parts) if parts else "`none`"


def _link_or_missing(path: Path) -> str:
    if path.exists():
        return f"[{path.name}]({_relative_path(path, path.parents[1])})"
    return f"`{path.name}` (missing optional artifact)"


def _as_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return [str(raw)] if str(raw).strip() else []


def _section_artifact_keys(section: str) -> List[str]:
    return {
        "dedup": ["dedup", "signals"],
        "clusters": ["clusters", "semantic_clusters"],
        "opportunities": ["opportunity", "opportunities"],
        "ideas": ["ideas", "ideation"],
        "anti_patterns": ["anti_patterns"],
        "critiques": ["critiques", "council"],
        "ai_quality": ["ai_quality", "ratings"],
    }.get(section, [section])


def _section_directories(section: str) -> List[str]:
    return {
        "dedup": ["signals"],
        "clusters": ["clusters", "semantic_clusters"],
        "opportunities": ["opportunities"],
        "ideas": ["ideas"],
        "anti_patterns": ["anti_patterns"],
        "critiques": ["critiques", "council"],
        "ai_quality": ["ai_quality", "ai_stage_ratings"],
    }.get(section, [section])
