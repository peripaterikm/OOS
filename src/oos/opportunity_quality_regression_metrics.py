from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .evaluation_dataset import load_opportunity_quality_cases_v1
from .evidence_pack import evidence_pack_from_dict
from .opportunity_quality_gate import evaluate_opportunity_quality
from .opportunity_sketch import opportunity_sketch_from_dict

METRICS_SCHEMA_VERSION = "opportunity_quality_regression_metrics.v1"
REPORT_ID_PREFIX = "opp_quality_regression"

FALSE_POSITIVE_LABELS = frozenset(
    {
        "generic_false_positive",
        "vendor_promo_false_positive",
        "weak_noisy",
        "killed_pattern_repeat",
    }
)

DUPLICATE_LABEL = "duplicate_signal"


@dataclass(frozen=True)
class PerCaseRegressionResult:
    case_id: str
    quality_label: str
    founder_review_posture: str
    expected_gate_decision: str
    actual_gate_decision: str
    matched_expected_gate: bool
    risk_notes: list[str]
    evidence_gaps: list[str]
    unsupported_assumptions: list[str]
    traceability_ids: dict[str, list[str]]
    false_positive_severity: str
    sufficiency_band: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "quality_label": self.quality_label,
            "founder_review_posture": self.founder_review_posture,
            "expected_gate_decision": self.expected_gate_decision,
            "actual_gate_decision": self.actual_gate_decision,
            "matched_expected_gate": self.matched_expected_gate,
            "risk_notes": list(self.risk_notes),
            "evidence_gaps": list(self.evidence_gaps),
            "unsupported_assumptions": list(self.unsupported_assumptions),
            "traceability_ids": {
                key: list(value) for key, value in self.traceability_ids.items()
            },
            "false_positive_severity": self.false_positive_severity,
            "sufficiency_band": self.sufficiency_band,
        }


@dataclass(frozen=True)
class OpportunityQualityRegressionMetrics:
    report_id: str
    generated_at: str
    schema_version: str = METRICS_SCHEMA_VERSION

    total_cases: int = 0
    cases_by_quality_label: dict[str, int] = field(default_factory=dict)
    cases_by_founder_review_posture: dict[str, int] = field(default_factory=dict)
    expected_gate_decision_counts: dict[str, int] = field(default_factory=dict)
    actual_gate_decision_counts: dict[str, int] = field(default_factory=dict)

    gate_decision_matches: int = 0
    gate_decision_mismatches: int = 0
    gate_match_rate: float = 0.0

    false_positive_cases: int = 0
    false_positive_rate: float = 0.0
    duplicate_cases: int = 0
    duplicate_rate: float = 0.0

    unsupported_assumptions_count: int = 0
    unsupported_assumptions_cases: int = 0

    per_case_results: list[PerCaseRegressionResult] = field(default_factory=list)

    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
            "total_cases": self.total_cases,
            "cases_by_quality_label": dict(
                sorted(self.cases_by_quality_label.items())
            ),
            "cases_by_founder_review_posture": dict(
                sorted(self.cases_by_founder_review_posture.items())
            ),
            "expected_gate_decision_counts": dict(
                sorted(self.expected_gate_decision_counts.items())
            ),
            "actual_gate_decision_counts": dict(
                sorted(self.actual_gate_decision_counts.items())
            ),
            "gate_decision_matches": self.gate_decision_matches,
            "gate_decision_mismatches": self.gate_decision_mismatches,
            "gate_match_rate": self.gate_match_rate,
            "false_positive_cases": self.false_positive_cases,
            "false_positive_rate": self.false_positive_rate,
            "duplicate_cases": self.duplicate_cases,
            "duplicate_rate": self.duplicate_rate,
            "unsupported_assumptions_count": self.unsupported_assumptions_count,
            "unsupported_assumptions_cases": self.unsupported_assumptions_cases,
            "per_case_results": [
                result.to_dict() for result in self.per_case_results
            ],
            "limitations": list(self.limitations),
            "false_positive_labels": sorted(FALSE_POSITIVE_LABELS),
        }

    def validate(self) -> None:
        if self.schema_version != METRICS_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {METRICS_SCHEMA_VERSION}"
            )
        if not isinstance(self.report_id, str) or not self.report_id.strip():
            raise ValueError("report_id must be a non-empty string")
        if not isinstance(self.generated_at, str) or not self.generated_at.strip():
            raise ValueError("generated_at must be a non-empty string")
        if self.total_cases < 0:
            raise ValueError("total_cases must not be negative")
        if not 0.0 <= self.gate_match_rate <= 1.0:
            raise ValueError("gate_match_rate must be between 0 and 1")
        if not 0.0 <= self.false_positive_rate <= 1.0:
            raise ValueError("false_positive_rate must be between 0 and 1")
        if not 0.0 <= self.duplicate_rate <= 1.0:
            raise ValueError("duplicate_rate must be between 0 and 1")
        expected_per_case = len(self.per_case_results)
        if expected_per_case != self.total_cases:
            raise ValueError(
                f"per_case_results length ({expected_per_case}) must equal "
                f"total_cases ({self.total_cases})"
            )
        label_total = sum(self.cases_by_quality_label.values())
        if label_total != self.total_cases and label_total != 0:
            raise ValueError(
                f"cases_by_quality_label total ({label_total}) must equal "
                f"total_cases ({self.total_cases})"
            )
        posture_total = sum(self.cases_by_founder_review_posture.values())
        if posture_total != self.total_cases and posture_total != 0:
            raise ValueError(
                f"cases_by_founder_review_posture total ({posture_total}) must equal "
                f"total_cases ({self.total_cases})"
            )


def _make_report_id(timestamp: str) -> str:
    digest = hashlib.sha256(timestamp.encode("utf-8")).hexdigest()[:12]
    return f"{REPORT_ID_PREFIX}_{digest}"


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(
        dict.fromkeys(str(item).strip() for item in values if str(item).strip())
    )


def compute_regression_metrics(
    fixture_path: Any = None,
) -> OpportunityQualityRegressionMetrics:
    cases = load_opportunity_quality_cases_v1(fixture_path=fixture_path)
    generated_at = datetime.now(timezone.utc).isoformat()
    report_id = _make_report_id(generated_at)

    per_case_results: list[PerCaseRegressionResult] = []
    cases_by_quality_label: dict[str, int] = {}
    cases_by_founder_review_posture: dict[str, int] = {}
    expected_gate_decision_counts: dict[str, int] = {}
    actual_gate_decision_counts: dict[str, int] = {}
    gate_decision_matches = 0
    gate_decision_mismatches = 0
    false_positive_count = 0
    duplicate_count = 0
    unsupported_assumptions_total = 0
    unsupported_assumptions_cases_count = 0

    for case in cases:
        case_id = case["case_id"]
        expected = case["expected"]

        quality_label = str(expected.get("quality_label", "")).strip()
        founder_posture = str(expected.get("founder_review_posture", "")).strip()
        expected_gate = str(expected.get("gate_decision", "")).strip()

        pack = evidence_pack_from_dict(case["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(
            case["input_artifacts"]["opportunity_candidate"]
        )
        gate_result = evaluate_opportunity_quality(candidate, pack)
        actual_gate = gate_result.decision

        matched = actual_gate == expected_gate

        risk_notes = _ordered_strings(
            list(candidate.risk_notes)
            + list(expected.get("risk_notes", []))
            + list(gate_result.missing_evidence)
        )
        evidence_gaps = _ordered_strings(list(expected.get("evidence_gaps", [])))
        unsupported = _ordered_strings(list(candidate.unsupported_assumptions))

        traceability_ids = {
            "evidence_ids": _ordered_strings(list(candidate.evidence_ids)),
            "source_signal_ids": _ordered_strings(list(candidate.source_signal_ids)),
            "source_urls": _ordered_strings(list(candidate.source_urls)),
            "gate_result_id": [gate_result.gate_result_id],
            "evidence_pack_id": [candidate.evidence_pack_id],
            "opportunity_id": [candidate.opportunity_id],
        }

        false_positive_assessment = gate_result.false_positive_assessment or {}
        fp_severity = str(
            false_positive_assessment.get("severity", "none")
            if isinstance(false_positive_assessment, dict)
            else getattr(false_positive_assessment, "severity", "none")
        )

        sufficiency_score = gate_result.evidence_sufficiency_score or {}
        sufficiency_band = str(
            sufficiency_score.get("score_band", "unknown")
            if isinstance(sufficiency_score, dict)
            else getattr(sufficiency_score, "score_band", "unknown")
        )

        per_case_results.append(
            PerCaseRegressionResult(
                case_id=case_id,
                quality_label=quality_label,
                founder_review_posture=founder_posture,
                expected_gate_decision=expected_gate,
                actual_gate_decision=actual_gate,
                matched_expected_gate=matched,
                risk_notes=risk_notes,
                evidence_gaps=evidence_gaps,
                unsupported_assumptions=unsupported,
                traceability_ids=traceability_ids,
                false_positive_severity=fp_severity,
                sufficiency_band=sufficiency_band,
            )
        )

        cases_by_quality_label[quality_label] = (
            cases_by_quality_label.get(quality_label, 0) + 1
        )
        cases_by_founder_review_posture[founder_posture] = (
            cases_by_founder_review_posture.get(founder_posture, 0) + 1
        )
        expected_gate_decision_counts[expected_gate] = (
            expected_gate_decision_counts.get(expected_gate, 0) + 1
        )
        actual_gate_decision_counts[actual_gate] = (
            actual_gate_decision_counts.get(actual_gate, 0) + 1
        )

        if matched:
            gate_decision_matches += 1
        else:
            gate_decision_mismatches += 1

        if quality_label in FALSE_POSITIVE_LABELS:
            false_positive_count += 1
        if quality_label == DUPLICATE_LABEL:
            duplicate_count += 1

        unsupported_len = len(unsupported)
        unsupported_assumptions_total += unsupported_len
        if unsupported_len > 0:
            unsupported_assumptions_cases_count += 1

    total_cases = len(cases)

    gate_match_rate = round(gate_decision_matches / total_cases, 4) if total_cases > 0 else 0.0
    false_positive_rate = round(false_positive_count / total_cases, 4) if total_cases > 0 else 0.0
    duplicate_rate = round(duplicate_count / total_cases, 4) if total_cases > 0 else 0.0

    limitations: list[str] = []
    limitations.append(
        "Metrics are computed from synthetic evaluation dataset v1 (10 cases); "
        "rates reflect baseline behavior against labeled expectations, "
        "not production accuracy."
    )
    limitations.append(
        "Unsupported assumptions are counted from opportunity candidate "
        "unsupported_assumptions fields only; dataset-level unsupported "
        "assumptions may be broader than what the model captures."
    )
    limitations.append(
        "Duplicate cases are identified by quality_label == 'duplicate_signal'; "
        "near-duplicate evidence within a single case is tracked in risk_notes "
        "but not counted as separate duplicate cases."
    )
    limitations.append(
        "Gate decisions are deterministic and may disagree with expected labels "
        "where the expected label reflects a desired outcome rather than the "
        "current gate logic output."
    )

    metrics = OpportunityQualityRegressionMetrics(
        report_id=report_id,
        generated_at=generated_at,
        total_cases=total_cases,
        cases_by_quality_label=dict(
            sorted(cases_by_quality_label.items())
        ),
        cases_by_founder_review_posture=dict(
            sorted(cases_by_founder_review_posture.items())
        ),
        expected_gate_decision_counts=dict(
            sorted(expected_gate_decision_counts.items())
        ),
        actual_gate_decision_counts=dict(
            sorted(actual_gate_decision_counts.items())
        ),
        gate_decision_matches=gate_decision_matches,
        gate_decision_mismatches=gate_decision_mismatches,
        gate_match_rate=gate_match_rate,
        false_positive_cases=false_positive_count,
        false_positive_rate=false_positive_rate,
        duplicate_cases=duplicate_count,
        duplicate_rate=duplicate_rate,
        unsupported_assumptions_count=unsupported_assumptions_total,
        unsupported_assumptions_cases=unsupported_assumptions_cases_count,
        per_case_results=per_case_results,
        limitations=limitations,
    )
    metrics.validate()
    return metrics
