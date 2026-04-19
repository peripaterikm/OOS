from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Type

from .models import MODEL_KIND, model_from_dict, model_to_dict


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    id: str
    path: Path


class ArtifactStore:
    """
    Minimal structured file storage for OOS v1 artifacts.

    Week 2 scope:
    - JSON files (UTF-8),
    - stable directory per kind,
    - explicit read/write,
    - minimal validation on load (via model.validate()).

    No database, no indexing, no business logic.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def _kind_dir(self, kind: str) -> Path:
        return self.root_dir / kind

    def path_for(self, kind: str, artifact_id: str) -> Path:
        return self._kind_dir(kind) / f"{artifact_id}.json"

    def write_model(self, model: Any) -> ArtifactRef:
        model.validate()
        kind = MODEL_KIND[type(model)]
        path = self.path_for(kind, model.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, Any] = model_to_dict(model)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return ArtifactRef(kind=kind, id=model.id, path=path)

    def read_model(self, model_cls: Type[Any], artifact_id: str) -> Any:
        kind = MODEL_KIND[model_cls]
        path = self.path_for(kind, artifact_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return model_from_dict(model_cls, data)

