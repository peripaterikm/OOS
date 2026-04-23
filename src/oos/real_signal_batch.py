from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .signal_layer import RawSignal


REQUIRED_FIELDS = ("signal_id", "captured_at", "source_type", "title", "text", "source_ref")


@dataclass(frozen=True)
class CanonicalSignalBatchItem:
    signal_id: str
    captured_at: str
    source_type: str
    title: str
    text: str
    source_ref: str

    def to_raw_signal(self) -> RawSignal:
        return RawSignal(
            id=self.signal_id,
            source=self.source_type,
            timestamp=self.captured_at,
            raw_content=f"{self.title}\n\n{self.text}",
            extracted_pain=self.title,
            candidate_icp="unknown",
        )

    def metadata(self) -> Dict[str, str]:
        return {
            "batch_format": "canonical_signal_jsonl_v1",
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "title": self.title,
        }


class CanonicalSignalBatchLoader:
    def load(self, path: Path) -> List[CanonicalSignalBatchItem]:
        if not path.exists():
            raise ValueError(f"Invalid signal batch: input file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Invalid signal batch: input path is not a file: {path}")

        items: List[CanonicalSignalBatchItem] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            obj = self._load_line(line=line, line_number=line_number)
            self._validate_required_fields(obj=obj, line_number=line_number)
            items.append(
                CanonicalSignalBatchItem(
                    signal_id=str(obj["signal_id"]).strip(),
                    captured_at=str(obj["captured_at"]).strip(),
                    source_type=str(obj["source_type"]).strip(),
                    title=str(obj["title"]).strip(),
                    text=str(obj["text"]).strip(),
                    source_ref=str(obj["source_ref"]).strip(),
                )
            )

        if not items:
            raise ValueError("Invalid signal batch: input file contains no JSONL objects")
        return items

    def _load_line(self, *, line: str, line_number: int) -> Dict[str, Any]:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid signal batch: line {line_number} is not valid JSON: {exc.msg}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"Invalid signal batch: line {line_number} must be a JSON object")
        return obj

    def _validate_required_fields(self, *, obj: Dict[str, Any], line_number: int) -> None:
        for field in REQUIRED_FIELDS:
            if field not in obj:
                raise ValueError(f"Invalid signal batch: line {line_number} missing required field '{field}'")
            if not isinstance(obj[field], str) or not obj[field].strip():
                raise ValueError(f"Invalid signal batch: line {line_number} field '{field}' must be a non-empty string")
