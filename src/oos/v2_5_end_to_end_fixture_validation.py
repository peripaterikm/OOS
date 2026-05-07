"""v2.5 end-to-end fixture validation — deterministic pipeline validation report.

Validates that the full v2.5 pipeline can process the opportunity quality fixture
dataset through all advisory layers without live APIs or autonomous decisions.

Produces a JSON-serializable V2_5EndToEndValidationReport.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from oos.evaluation_dataset import load_opportunity_quality_cases_v1
from oos.evidence_pack import evidence_pack_from_dict
from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    FounderDecisionV2,
    create_founder_decision,
)
from oos.founder_feedback_mapping import map_founder_decision_to_feedback
from oos.founder_preference_profile import build_founder_preference_profile
from oos.next_best_founder_actions import build_next_best_founder_actions
from oos.opportunity_quality_gate import evaluate_opportunity_quality
from oos.opportunity_quality_regression_metrics import compute_regression_metrics
from oos.opportunity_sketch import opportunity_sketch_from_dict
from oos.parking_lot import build_parking_lot_records, match_revisit_candidates
from oos.weekly_opportunity_review import build_weekly_opportunity_review_package


VALIDATION_SCHEMA_VERSION = "v2_5_end_to_end_fixture_validation.v1"
SECTION_IDS = (
    "top_opportunities_to_review",
    "promote_candidates",
    "park_candidates",
    "kill_candidates",
    "needs_more_evidence",
    "revisit_queue",
    "evidence_gaps",
    "suggested_interviews_or_validation",
    "suggested_next_queries",
    "preference_profile_warnings",
)


_GATE_DECISION_TO_FOUNDER_DECISION: dict[str, str] = {
    "pass": PROMOTE,
    "park": PARK,
    "reject": KILL,
}


@dataclass
class V2_5EndToEndCaseResult:
    """Per-case result from the end-to-end fixture validation."""

    case_id: str
    title: str

    # Artifact validation
    evidence_pack_valid: bool = True
    opportunity_candidate_valid: bool = True
    evidence_pack_errors: list[str] = field(default_factory=list)
    opportunity_candidate_errors: list[str] = field(default_factory=list)

    # Quality gate
    gate_decision: str = ""
    gate_confidence: float = 0.0
    gate_result_id: str = ""

    # Regression metrics check
    regression_expected_gate: str = ""
    regression_actual_gate: str = ""
    regression_matched: bool = False

    # Founder decision
    founder_decision_id: str = ""
    founder_decision: str = ""

    # Feedback mapping
    feedback_mapping_id: str = ""
    feedback_mapping_valid: bool = False

    # Traceability
    evidence_ids: list[str] = field(default_factory=list)
    source_signal_ids: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    linked_opportunity_id: str = ""
    linked_pack_id: str = ""

    # Advisory check
    advisory_only: bool = True
    autonomous_action: bool = False

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class V2_5EndToEndValidationReport:
    """Full v2.5 end-to-end fixture validation report.

    Advisory only: no autonomous portfolio transitions.
    Deterministic ordering and stable IDs.
    JSON-serializable.
    """

    report_id: str
    generated_at: str
    schema_version: str = VALIDATION_SCHEMA_VERSION

    total_cases: int = 0
    cases_processed: int = 0
    gate_decision_counts: dict[str, int] = field(default_factory=dict)
    weekly_review_sections_present: list[str] = field(default_factory=list)
    next_best_actions_count: int = 0
    traceability_checks: dict[str, int] = field(
        default_factory=lambda: {
            "evidence_pack_to_gate": 0,
            "gate_to_founder_decision": 0,
            "founder_decision_to_feedback": 0,
            "feedback_to_signals": 0,
            "signals_to_weekly_review": 0,
        }
    )
    advisory_only_checks: dict[str, int] = field(
        default_factory=lambda: {
            "total_decisions": 0,
            "advisory_decisions": 0,
            "autonomous_decisions": 0,
        }
    )
    failed_cases: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validation_passed: bool = False

    per_case_results: list[V2_5EndToEndCaseResult] = field(default_factory=list)

    regression_metrics_summary: dict[str, Any] = field(default_factory=dict)

    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
            "total_cases": self.total_cases,
            "cases_processed": self.cases_processed,
            "gate_decision_counts": dict(sorted(self.gate_decision_counts.items())),
            "weekly_review_sections_present": list(self.weekly_review_sections_present),
            "next_best_actions_count": self.next_best_actions_count,
            "traceability_checks": dict(self.traceability_checks),
            "advisory_only_checks": dict(self.advisory_only_checks),
            "failed_cases": list(self.failed_cases),
            "warnings": list(self.warnings),
            "validation_passed": self.validation_passed,
            "per_case_results": [r.to_dict() for r in self.per_case_results],
            "regression_metrics_summary": self.regression_metrics_summary,
            "limitations": list(self.limitations),
        }

    def validate(self) -> None:
        if self.schema_version != VALIDATION_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {VALIDATION_SCHEMA_VERSION}"
            )
        if not self.report_id or not self.report_id.strip():
            raise ValueError("report_id must be a non-empty string")
        if not self.generated_at or not self.generated_at.strip():
            raise ValueError("generated_at must be a non-empty string")
        if self.cases_processed != self.total_cases:
            raise ValueError(
                f"cases_processed ({self.cases_processed}) must equal "
                f"total_cases ({self.total_cases})"
            )


def _ordered_strings(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _make_report_id(timestamp: str) -> str:
    digest = hashlib.sha256(timestamp.encode("utf-8")).hexdigest()[:12]
    return f"v2_5_e2e_{digest}"


def _derive_founder_decision_and_reasons(
    expected: dict[str, Any],
    gate_decision: str,
    evidence_ids: list[str],
    source_signal_ids: list[str],
    source_urls: list[str],
    opportunity_id: str,
    evidence_pack_id: str,
) -> tuple[str, list[str]]:
    """Derive founder decision and reason categories from expected labels and gate output.

    Uses expected.founder_review_posture as primary signal,
    falls back to gate_decision mapping.
    """
    posture = str(expected.get("founder_review_posture", "")).strip()
    quality_label = str(expected.get("quality_label", "")).strip()
    evidence_gaps = list(expected.get("evidence_gaps", []))
    risk_notes = list(expected.get("risk_notes", []))

    if posture == "promote_candidate":
        return PROMOTE, ["strong_pain", "clear_buyer"]
    if posture == "park_candidate":
        return PARK, ["weak_evidence", "needs_more_examples"]
    if posture == "needs_more_evidence":
        return NEEDS_MORE_EVIDENCE, ["need_customer_voice", "need_price_evidence"]
    if posture == "revisit_candidate":
        return REVISIT_LATER, ["waiting_for_more_signals"]

    # kill_candidate or fallback
    kill_reasons: list[str] = []
    if quality_label == "generic_false_positive":
        kill_reasons = ["too_generic", "no_buyer"]
    elif quality_label == "vendor_promo_false_positive":
        kill_reasons = ["vendor_promo_false_positive", "no_real_pain"]
    elif quality_label == "duplicate_signal":
        # Duplicate signals should be parked, not killed
        return PARK, ["needs_more_examples", "weak_evidence"]
    elif quality_label == "no_buyer":
        kill_reasons = ["no_buyer", "no_willingness_to_pay"]
    elif quality_label == "weak_noisy":
        kill_reasons = ["too_generic", "no_real_pain"]
    elif quality_label == "killed_pattern_repeat":
        kill_reasons = ["repeated_killed_pattern", "disguised_consulting"]
    elif quality_label == "needs_more_evidence":
        return NEEDS_MORE_EVIDENCE, ["need_customer_voice", "need_source_diversity"]

    if quality_label in (
        "generic_false_positive",
        "vendor_promo_false_positive",
        "weak_noisy",
        "no_buyer",
        "killed_pattern_repeat",
    ):
        return KILL, kill_reasons

    # Fallback: map gate decision
    fallback_decision = _GATE_DECISION_TO_FOUNDER_DECISION.get(gate_decision, PARK)
    if fallback_decision == PROMOTE:
        return PROMOTE, ["strong_pain", "clear_buyer"]
    if fallback_decision == PARK:
        return PARK, ["needs_more_examples", "weak_evidence"]
    return KILL, ["too_generic", "no_buyer"]


def run_v2_5_end_to_end_fixture_validation(
    fixture_path: Any = None,
) -> V2_5EndToEndValidationReport:
    """Run the full v2.5 end-to-end fixture validation.

    Loads the v2.5 opportunity quality evaluation dataset, validates
    each fixture case through evidence packs, quality gates, founder
    decisions, feedback mappings, preference profiles, weekly review
    packaging, and next-best actions, then returns a structured report.

    No live APIs, no LLM calls, no autonomous decisions.
    """
    cases = load_opportunity_quality_cases_v1(fixture_path=fixture_path)
    generated_at = datetime.now(timezone.utc).isoformat()
    report_id = _make_report_id(generated_at)

    per_case_results: list[V2_5EndToEndCaseResult] = []
    failed_cases: list[str] = []
    warnings: list[str] = []
    gate_decision_counts: dict[str, int] = {}
    traceability_checks: dict[str, int] = {
        "evidence_pack_to_gate": 0,
        "gate_to_founder_decision": 0,
        "founder_decision_to_feedback": 0,
        "feedback_to_signals": 0,
        "signals_to_weekly_review": 0,
    }
    advisory_only_checks: dict[str, int] = {
        "total_decisions": 0,
        "advisory_decisions": 0,
        "autonomous_decisions": 0,
    }

    all_founder_decisions: list[FounderDecisionV2] = []
    all_feedback_mappings: list[dict[str, Any]] = []
    all_packs: list[dict[str, Any]] = []

    for case in cases:
        case_id = case["case_id"]
        title = str(case.get("title", ""))
        expected = case["expected"]

        result = V2_5EndToEndCaseResult(
            case_id=case_id,
            title=title,
        )

        # --- 1. Validate evidence pack ---
        pack_errors: list[str] = []
        pack = None
        try:
            pack = evidence_pack_from_dict(case["input_artifacts"]["evidence_pack"])
            pack.validate()
            result.evidence_pack_valid = True
        except (ValueError, TypeError, KeyError) as exc:
            result.evidence_pack_valid = False
            pack_errors.append(str(exc))
            result.evidence_pack_errors = pack_errors
            result.errors.append(f"evidence_pack validation failed: {exc}")
            failed_cases.append(case_id)
            per_case_results.append(result)
            continue

        # --- 2. Validate opportunity candidate ---
        candidate = None
        try:
            candidate = opportunity_sketch_from_dict(
                case["input_artifacts"]["opportunity_candidate"]
            )
            result.opportunity_candidate_valid = True
        except (ValueError, TypeError, KeyError) as exc:
            result.opportunity_candidate_valid = False
            result.opportunity_candidate_errors.append(str(exc))
            result.errors.append(f"opportunity_candidate validation failed: {exc}")
            failed_cases.append(case_id)
            per_case_results.append(result)
            continue

        # --- 3. Run quality gate ---
        try:
            gate_result = evaluate_opportunity_quality(candidate, pack)
            result.gate_decision = gate_result.decision
            result.gate_confidence = gate_result.confidence
            result.gate_result_id = gate_result.gate_result_id
            gate_decision_counts[gate_result.decision] = (
                gate_decision_counts.get(gate_result.decision, 0) + 1
            )

            # Check regression expectation
            expected_gate = str(expected.get("gate_decision", "")).strip()
            result.regression_expected_gate = expected_gate
            result.regression_actual_gate = gate_result.decision
            result.regression_matched = gate_result.decision == expected_gate
            if not result.regression_matched:
                result.warnings.append(
                    f"Gate decision mismatch: expected={expected_gate}, "
                    f"actual={gate_result.decision}"
                )

            # Traceability: evidence pack -> gate
            traceability_checks["evidence_pack_to_gate"] += 1
        except (ValueError, TypeError) as exc:
            result.errors.append(f"quality gate failed: {exc}")
            failed_cases.append(case_id)
            per_case_results.append(result)
            continue

        # --- 4. Create representative founder decision ---
        founder_decision, reason_categories = _derive_founder_decision_and_reasons(
            expected=expected,
            gate_decision=gate_result.decision,
            evidence_ids=list(candidate.evidence_ids),
            source_signal_ids=list(candidate.source_signal_ids),
            source_urls=list(candidate.source_urls),
            opportunity_id=candidate.opportunity_id,
            evidence_pack_id=candidate.evidence_pack_id,
        )

        fd = create_founder_decision(
            opportunity_id=candidate.opportunity_id,
            evidence_pack_id=candidate.evidence_pack_id,
            decision=founder_decision,
            reasons=reason_categories,
            notes=f"Fixture-driven decision for {case_id}: {title}",
            confidence=float(candidate.confidence),
            linked_evidence_ids=list(candidate.evidence_ids),
            linked_source_signal_ids=list(candidate.source_signal_ids),
            linked_source_urls=list(candidate.source_urls),
            decided_by="fixture_validation",
        )
        all_founder_decisions.append(fd)

        result.founder_decision_id = fd.decision_id
        result.founder_decision = fd.decision
        result.linked_opportunity_id = candidate.opportunity_id
        result.linked_pack_id = candidate.evidence_pack_id
        result.evidence_ids = _ordered_strings(list(candidate.evidence_ids))
        result.source_signal_ids = _ordered_strings(list(candidate.source_signal_ids))
        result.source_urls = _ordered_strings(list(candidate.source_urls))

        # Traceability: gate -> founder decision
        if fd.decision_id:
            traceability_checks["gate_to_founder_decision"] += 1

        # Advisory only check
        advisory_only_checks["total_decisions"] += 1
        if not fd.auto_promote:
            advisory_only_checks["advisory_decisions"] += 1
        else:
            advisory_only_checks["autonomous_decisions"] += 1
            result.autonomous_action = True
            result.warnings.append(
                f"Founder decision {fd.decision_id} has auto_promote=True"
            )

        # --- 5. Create feedback mapping ---
        try:
            feedback_mapping = map_founder_decision_to_feedback(
                fd,
                cluster_id=candidate.cluster_id,
            )
            feedback_mapping.validate()
            result.feedback_mapping_id = feedback_mapping.mapping_id
            result.feedback_mapping_valid = True
            all_feedback_mappings.append(feedback_mapping.to_dict())

            # Traceability: founder decision -> feedback
            traceability_checks["founder_decision_to_feedback"] += 1
            # Traceability: feedback -> signals/evidence
            if feedback_mapping.evidence_ids:
                traceability_checks["feedback_to_signals"] += 1
        except (ValueError, TypeError) as exc:
            result.warnings.append(f"feedback mapping failed: {exc}")

        # --- Collect pack dict ---
        all_packs.append(pack.to_dict())

        per_case_results.append(result)

    # --- 6. Build founder preference profile ---
    profile = None
    if all_founder_decisions:
        try:
            profile = build_founder_preference_profile(
                all_founder_decisions,
                feedback_mappings=[
                    fm for fm in all_feedback_mappings
                ],
            )
        except (ValueError, TypeError) as exc:
            warnings.append(f"preference profile build failed: {exc}")

    # --- 7. Build parking lot records ---
    parking_lot_records: list[dict[str, Any]] = []
    if all_founder_decisions:
        try:
            records = build_parking_lot_records(all_founder_decisions)
            parking_lot_records = [r.to_dict() for r in records]
        except (ValueError, TypeError) as exc:
            warnings.append(f"parking lot records build failed: {exc}")

    # --- 8. Match revisit candidates ---
    revisit_matches: list[dict[str, Any]] = []
    if parking_lot_records and all_packs:
        try:
            # Build new_evidence items from evidence packs
            new_evidence_items: list[dict[str, Any]] = []
            for pack_dict in all_packs:
                new_evidence_items.append({
                    "text": " ".join(pack_dict.get("summaries", [])),
                    "evidence_id": pack_dict.get("evidence_pack_id", ""),
                    "source_urls": pack_dict.get("source_urls", []),
                })
            matches = match_revisit_candidates(
                parking_lot_records=parking_lot_records,
                new_evidence=new_evidence_items,
            )
            revisit_matches = [m.to_dict() for m in matches]
        except (ValueError, TypeError) as exc:
            warnings.append(f"revisit match build failed: {exc}")

    # --- 9. Build weekly opportunity review package ---
    weekly_package = None
    weekly_package_dict: dict[str, Any] = {}
    weekly_review_sections: list[str] = []
    try:
        weekly_package = build_weekly_opportunity_review_package(
            decisions=all_founder_decisions,
            feedback_mappings=all_feedback_mappings,
            preference_profile=profile.to_dict() if profile else {},
            evidence_packs=all_packs,
            portfolio_states=[],
            opportunity_candidates=[case["input_artifacts"]["opportunity_candidate"] for case in cases],
            parking_lot_records=parking_lot_records,
            revisit_matches=revisit_matches,
        )
        weekly_package_dict = weekly_package.to_dict()
        weekly_review_sections = [
            section.get("section_id", "")
            for section in weekly_package_dict.get("sections", [])
        ]

        # Verify all required sections
        present_section_ids = set(section.get("section_id", "") for section in weekly_package_dict.get("sections", []))
        for sid in SECTION_IDS:
            if sid in present_section_ids:
                weekly_review_sections.append(sid)

        # Traceability: signals -> weekly review
        if weekly_package.source_evidence_pack_ids:
            traceability_checks["signals_to_weekly_review"] += 1
    except (ValueError, TypeError) as exc:
        warnings.append(f"weekly review package build failed: {exc}")

    # --- 10. Build next-best founder actions ---
    next_best_actions_count = 0
    if weekly_package_dict:
        try:
            actions = build_next_best_founder_actions(weekly_package_dict)
            next_best_actions_count = len(actions)
        except (ValueError, TypeError) as exc:
            warnings.append(f"next best actions build failed: {exc}")

    # --- 11. Compute regression metrics ---
    regression_summary: dict[str, Any] = {}
    try:
        metrics = compute_regression_metrics(fixture_path=fixture_path)
        regression_summary = {
            "report_id": metrics.report_id,
            "total_cases": metrics.total_cases,
            "gate_decision_matches": metrics.gate_decision_matches,
            "gate_decision_mismatches": metrics.gate_decision_mismatches,
            "gate_match_rate": metrics.gate_match_rate,
            "false_positive_cases": metrics.false_positive_cases,
            "false_positive_rate": metrics.false_positive_rate,
            "duplicate_cases": metrics.duplicate_cases,
            "duplicate_rate": metrics.duplicate_rate,
            "unsupported_assumptions_count": metrics.unsupported_assumptions_count,
            "expected_gate_decision_counts": dict(metrics.expected_gate_decision_counts),
            "actual_gate_decision_counts": dict(metrics.actual_gate_decision_counts),
            "cases_by_quality_label": dict(metrics.cases_by_quality_label),
            "limitations": list(metrics.limitations),
        }
    except (ValueError, TypeError) as exc:
        warnings.append(f"regression metrics compute failed: {exc}")

    # --- Build the report ---
    total_cases = len(cases)
    cases_processed = len(per_case_results) - len(failed_cases)

    # Count actual processed (non-failed) cases
    succeeded = sum(
        1 for r in per_case_results
        if r.case_id not in failed_cases
    )

    validation_passed = (
        len(failed_cases) == 0
        and succeeded == total_cases
        and len(weekly_review_sections) > 0
        and next_best_actions_count > 0
        and advisory_only_checks["autonomous_decisions"] == 0
    )

    limitations = [
        "End-to-end validation is based on the synthetic v2.5 evaluation dataset "
        "(10 labeled cases); results reflect deterministic behavior against labeled "
        "expectations, not production accuracy.",
        "Founder decisions are derived from fixture expected posture/gate decision, "
        "not from real founder review. Real founder review may produce different "
        "decisions and feedback.",
        "Weekly review package sections vary based on fixture data; empty sections "
        "are expected for some inputs.",
        "Parking lot and revisit matching are deterministic based on fixture "
        "decisions; real-world parking lot records would accumulate over multiple "
        "weekly cycles.",
        "No live LLM/API calls were used. All validation is deterministic and "
        "offline.",
    ]

    report = V2_5EndToEndValidationReport(
        report_id=report_id,
        generated_at=generated_at,
        total_cases=total_cases,
        cases_processed=succeeded,
        gate_decision_counts=gate_decision_counts,
        weekly_review_sections_present=_ordered_strings(weekly_review_sections),
        next_best_actions_count=next_best_actions_count,
        traceability_checks=traceability_checks,
        advisory_only_checks=advisory_only_checks,
        failed_cases=failed_cases,
        warnings=warnings,
        validation_passed=validation_passed,
        per_case_results=per_case_results,
        regression_metrics_summary=regression_summary,
        limitations=limitations,
    )
    report.validate()
    return report
