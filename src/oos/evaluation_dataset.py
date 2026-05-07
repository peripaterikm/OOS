from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


EVALUATION_DATASET_V0_DIR = Path(__file__).resolve().parents[2] / "examples" / "evaluation_dataset_v0"
EVALUATION_DATASET_V0_SIGNALS = EVALUATION_DATASET_V0_DIR / "signals.json"
EVALUATION_DATASET_V1_DIR = Path(__file__).resolve().parents[2] / "examples" / "evaluation_dataset_v1"
EVALUATION_DATASET_V1_SIGNALS = EVALUATION_DATASET_V1_DIR / "signals.json"
EVALUATION_QUALITY_DATASET_V1_DIR = Path(__file__).resolve().parents[2] / "examples" / "evaluation_dataset_v2_5"
EVALUATION_QUALITY_DATASET_V1_PATH = EVALUATION_QUALITY_DATASET_V1_DIR / "opportunity_quality_cases_v1.json"


def load_evaluation_dataset_v0(dataset_dir: Path = EVALUATION_DATASET_V0_DIR) -> List[Dict[str, Any]]:
    signals_path = dataset_dir / "signals.json"
    data = json.loads(signals_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("evaluation dataset v0 signals.json must contain a JSON list")
    return data


def load_evaluation_dataset_v1(dataset_dir: Path = EVALUATION_DATASET_V1_DIR) -> List[Dict[str, Any]]:
    signals_path = dataset_dir / "signals.json"
    data = json.loads(signals_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("evaluation dataset v1 signals.json must contain a JSON list")
    return data


def load_opportunity_quality_cases_v1(
    fixture_path: Path | None = None,
) -> List[Dict[str, Any]]:
    path = fixture_path or EVALUATION_QUALITY_DATASET_V1_PATH
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("opportunity quality cases v1 fixture must contain a JSON list")
    for case in data:
        if not isinstance(case.get("case_id"), str) or not case["case_id"].strip():
            raise ValueError("each quality case must have a non-empty case_id")
        if not isinstance(case.get("title"), str) or not case["title"].strip():
            raise ValueError(f"quality case {case.get('case_id', '?')} must have a non-empty title")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValueError(f"quality case {case['case_id']} must have an 'expected' object")
        if not isinstance(expected.get("quality_label"), str) or not expected["quality_label"].strip():
            raise ValueError(f"quality case {case['case_id']} must have expected.quality_label")
        if not isinstance(expected.get("founder_review_posture"), str) or not expected["founder_review_posture"].strip():
            raise ValueError(f"quality case {case['case_id']} must have expected.founder_review_posture")
        if not isinstance(expected.get("gate_decision"), str) or not expected["gate_decision"].strip():
            raise ValueError(f"quality case {case['case_id']} must have expected.gate_decision")
        if not isinstance(case.get("rationale"), str) or not case["rationale"].strip():
            raise ValueError(f"quality case {case['case_id']} must have rationale")
        if case.get("synthetic_data") is not True:
            raise ValueError(f"quality case {case['case_id']} must have synthetic_data = true")
    return data
