from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path.cwd()
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
REPORTS_DIR = PROJECT_ROOT / "reports"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(value: Any, limit: int = 220) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def load_expected(input_file: Path) -> dict[str, dict[str, Any]]:
    """
    Map raw_content -> expected row from sample_signals_batch_01.json.
    """
    if not input_file.exists():
        return {}

    data = load_json(input_file)
    result = {}

    if isinstance(data, list):
        for i, item in enumerate(data, start=1):
            raw_content = item.get("raw_content", "")
            if raw_content:
                result[raw_content.strip()] = {
                    "input_index": i,
                    "expected_status": item.get("expected_status", ""),
                    "expected_source": item.get("source", ""),
                    "expected_icp": item.get("candidate_icp", ""),
                }

    return result


def collect_artifacts() -> list[dict[str, Any]]:
    """
    Collect signal-like artifacts from:
    - artifacts/signals
    - artifacts/weak_signals
    - artifacts/noise_archive

    Handles both full Signal objects and lightweight refs.
    """
    folders = [
        ("validated", ARTIFACTS_DIR / "signals"),
        ("weak", ARTIFACTS_DIR / "weak_signals"),
        ("noise", ARTIFACTS_DIR / "noise_archive"),
    ]

    rows = []

    for folder_status, folder in folders:
        if not folder.exists():
            continue

        for path in sorted(folder.glob("*.json")):
            try:
                obj = load_json(path)
            except Exception as e:
                rows.append({
                    "actual_status": folder_status,
                    "artifact_file": str(path),
                    "error": f"Could not parse JSON: {e}",
                })
                continue

            # Some weak/noise artifacts may be refs rather than full Signal objects.
            raw_content = obj.get("raw_content", "")
            extracted_pain = obj.get("extracted_pain", "")

            rows.append({
                "artifact_file": str(path.relative_to(PROJECT_ROOT)),
                "actual_status": str(obj.get("status", folder_status)),
                "id": obj.get("id", obj.get("signal_id", "")),
                "source": obj.get("source", ""),
                "timestamp": obj.get("timestamp", ""),
                "raw_content": raw_content,
                "extracted_pain": extracted_pain,
                "candidate_icp": obj.get("candidate_icp", ""),
                "validity_score": obj.get("validity_score", ""),
                "validity_specificity": obj.get("validity_specificity", ""),
                "validity_recurrence": obj.get("validity_recurrence", ""),
                "validity_workaround": obj.get("validity_workaround", ""),
                "validity_cost_signal": obj.get("validity_cost_signal", ""),
                "validity_icp_match": obj.get("validity_icp_match", ""),
                "rejection_reason": obj.get("rejection_reason", obj.get("reason", "")),
            })

    return rows


def merge_expected(rows: list[dict[str, Any]], expected_by_raw: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        raw = str(row.get("raw_content", "")).strip()
        expected = expected_by_raw.get(raw, {})

        row["input_index"] = expected.get("input_index", "")
        row["expected_status"] = expected.get("expected_status", "")
        row["status_match"] = (
            "yes"
            if expected.get("expected_status") and expected.get("expected_status") == row.get("actual_status")
            else "no"
            if expected.get("expected_status")
            else ""
        )

        if not row.get("candidate_icp"):
            row["candidate_icp"] = expected.get("expected_icp", "")

    return rows


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    fields = [
        "input_index",
        "expected_status",
        "actual_status",
        "status_match",
        "validity_score",
        "validity_specificity",
        "validity_recurrence",
        "validity_workaround",
        "validity_cost_signal",
        "validity_icp_match",
        "candidate_icp",
        "source",
        "raw_content",
        "extracted_pain",
        "rejection_reason",
        "id",
        "artifact_file",
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            safe_row = {field: normalize_text(row.get(field, ""), limit=500) for field in fields}
            writer.writerow(safe_row)


def write_markdown(rows: list[dict[str, Any]], output_path: Path) -> None:
    fields = [
        "input_index",
        "expected_status",
        "actual_status",
        "status_match",
        "validity_score",
        "candidate_icp",
        "raw_content",
        "rejection_reason",
    ]

    lines = []
    lines.append("# Signal Audit Table")
    lines.append("")
    lines.append("| # | Expected | Actual | Match | Score | ICP | Raw content | Rejection reason |")
    lines.append("|---:|---|---|---|---:|---|---|---|")

    for row in rows:
        values = []
        for field in fields:
            text = normalize_text(row.get(field, ""), limit=120)
            text = text.replace("|", "\\|")
            values.append(text)

        lines.append(
            f"| {values[0]} | {values[1]} | {values[2]} | {values[3]} | {values[4]} | {values[5]} | {values[6]} | {values[7]} |"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(rows: list[dict[str, Any]]) -> None:
    total = len(rows)
    by_actual = {}
    matches = 0
    expected_known = 0

    for row in rows:
        actual = row.get("actual_status", "")
        by_actual[actual] = by_actual.get(actual, 0) + 1

        if row.get("expected_status"):
            expected_known += 1
            if row.get("status_match") == "yes":
                matches += 1

    print("Signal audit completed.")
    print(f"Rows: {total}")
    print("Actual classification:")
    for key, value in sorted(by_actual.items()):
        print(f"  {key}: {value}")

    if expected_known:
        print(f"Expected statuses known: {expected_known}")
        print(f"Matches: {matches}")
        print(f"Mismatches: {expected_known - matches}")


def main() -> int:
    input_file = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "sample_signals_batch_01.json"

    REPORTS_DIR.mkdir(exist_ok=True)

    expected_by_raw = load_expected(input_file)
    rows = collect_artifacts()
    rows = merge_expected(rows, expected_by_raw)

    # Sort by original input order when available, otherwise by artifact file.
    rows.sort(key=lambda r: (r.get("input_index") == "", r.get("input_index") or 9999, r.get("artifact_file", "")))

    csv_path = REPORTS_DIR / "signal_audit.csv"
    md_path = REPORTS_DIR / "signal_audit.md"

    write_csv(rows, csv_path)
    write_markdown(rows, md_path)
    print_summary(rows)

    print(f"CSV: {csv_path}")
    print(f"Markdown: {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())