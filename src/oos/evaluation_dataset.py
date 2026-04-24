from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


EVALUATION_DATASET_V0_DIR = Path(__file__).resolve().parents[2] / "examples" / "evaluation_dataset_v0"
EVALUATION_DATASET_V0_SIGNALS = EVALUATION_DATASET_V0_DIR / "signals.json"


def load_evaluation_dataset_v0(dataset_dir: Path = EVALUATION_DATASET_V0_DIR) -> List[Dict[str, Any]]:
    signals_path = dataset_dir / "signals.json"
    data = json.loads(signals_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("evaluation dataset v0 signals.json must contain a JSON list")
    return data
