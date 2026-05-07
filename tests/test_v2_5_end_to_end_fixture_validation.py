"""Tests for v2.5 end-to-end fixture validation.

Covers:
- Full pipeline validation report generation
- Deterministic ordering and stable IDs
- Traceability across evidence, gate, founder decision, feedback, weekly review, next actions
- Advisory-only enforcement
- Fixture coverage for all 10 v2.5 quality cases
- Validation report serialization
- Empty-input handling and graceful degradation
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.evaluation_dataset import load_opportunity_quality_cases_v1
from oos.v2_5_end_to_end_fixture_validation import (
    V2_5EndToEndCaseResult,
    V2_5EndToEndValidationReport,
    _derive_founder_decision_and_reasons,
    _regression_mismatch_count,
    run_v2_5_end_to_end_fixture_validation,
)


class V2_5EndToEndCaseResultTests(unittest.TestCase):
    """Unit tests for V2_5EndToEndCaseResult model."""

    def test_model_creation_defaults(self):
        result = V2_5EndToEndCaseResult(case_id="test_001", title="Test Case")
        self.assertEqual(result.case_id, "test_001")
        self.assertEqual(result.title, "Test Case")
        self.assertTrue(result.evidence_pack_valid)
        self.assertTrue(result.opportunity_candidate_valid)
        self.assertTrue(result.advisory_only)
        self.assertFalse(result.autonomous_action)
        self.assertEqual(result.evidence_pack_errors, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_model_to_dict(self):
        result = V2_5EndToEndCaseResult(case_id="test_001", title="Test Case")
        d = result.to_dict()
        self.assertEqual(d["case_id"], "test_001")
        self.assertEqual(d["title"], "Test Case")
        self.assertTrue(d["advisory_only"])
        self.assertIsInstance(d, dict)

    def test_model_with_errors(self):
        result = V2_5EndToEndCaseResult(
            case_id="test_fail",
            title="Fails",
            evidence_pack_valid=False,
            errors=["validation error"],
            warnings=["minor warning"],
        )
        self.assertFalse(result.evidence_pack_valid)
        self.assertIn("validation error", result.errors)
        self.assertIn("minor warning", result.warnings)

    def test_model_with_gate_data(self):
        result = V2_5EndToEndCaseResult(
            case_id="test_gate",
            title="Has gate",
            gate_decision="pass",
            gate_confidence=0.85,
            gate_result_id="gate_test_abc",
            regression_matched=True,
        )
        self.assertEqual(result.gate_decision, "pass")
        self.assertEqual(result.gate_confidence, 0.85)
        self.assertTrue(result.regression_matched)


class V2_5EndToEndValidationReportTests(unittest.TestCase):
    """Unit tests for V2_5EndToEndValidationReport model."""

    def test_report_creation_and_validation(self):
        report = V2_5EndToEndValidationReport(
            report_id="v2_5_e2e_test",
            generated_at="2025-01-01T00:00:00+00:00",
            total_cases=10,
            cases_processed=10,
            validation_passed=True,
        )
        report.validate()

    def test_report_mismatched_cases_raises(self):
        report = V2_5EndToEndValidationReport(
            report_id="v2_5_e2e_test",
            generated_at="2025-01-01T00:00:00+00:00",
            total_cases=10,
            cases_processed=8,
        )
        with self.assertRaises(ValueError):
            report.validate()

    def test_report_pass_rejects_per_case_regression_mismatch(self):
        report = V2_5EndToEndValidationReport(
            report_id="v2_5_e2e_test",
            generated_at="2025-01-01T00:00:00+00:00",
            total_cases=1,
            cases_processed=1,
            per_case_results=[
                V2_5EndToEndCaseResult(
                    case_id="case_001",
                    title="Mismatch case",
                    regression_expected_gate="pass",
                    regression_actual_gate="reject",
                    regression_matched=False,
                )
            ],
            validation_passed=True,
        )
        with self.assertRaises(ValueError):
            report.validate()

    def test_report_pass_rejects_metric_regression_mismatch(self):
        report = V2_5EndToEndValidationReport(
            report_id="v2_5_e2e_test",
            generated_at="2025-01-01T00:00:00+00:00",
            total_cases=0,
            cases_processed=0,
            regression_metrics_summary={"gate_decision_mismatches": 1},
            validation_passed=True,
        )
        with self.assertRaises(ValueError):
            report.validate()

    def test_report_empty_report_id_raises(self):
        report = V2_5EndToEndValidationReport(
            report_id="",
            generated_at="2025-01-01T00:00:00+00:00",
            total_cases=0,
            cases_processed=0,
        )
        with self.assertRaises(ValueError):
            report.validate()

    def test_report_to_dict_complete(self):
        report = V2_5EndToEndValidationReport(
            report_id="v2_5_e2e_full",
            generated_at="2025-01-01T00:00:00+00:00",
            total_cases=3,
            cases_processed=3,
            gate_decision_counts={"pass": 1, "park": 1, "reject": 1},
            weekly_review_sections_present=[
                "evidence_gaps",
                "promote_candidates",
                "top_opportunities_to_review",
            ],
            next_best_actions_count=5,
            traceability_checks={
                "evidence_pack_to_gate": 3,
                "gate_to_founder_decision": 3,
                "founder_decision_to_feedback": 3,
                "feedback_to_signals": 2,
                "signals_to_weekly_review": 1,
            },
            advisory_only_checks={
                "total_decisions": 3,
                "advisory_decisions": 3,
                "autonomous_decisions": 0,
            },
            failed_cases=[],
            warnings=[],
            validation_passed=True,
            limitations=["Test limitation"],
        )
        d = report.to_dict()
        self.assertEqual(d["report_id"], "v2_5_e2e_full")
        self.assertEqual(d["total_cases"], 3)
        self.assertEqual(d["next_best_actions_count"], 5)
        self.assertTrue(d["validation_passed"])
        self.assertEqual(len(d["weekly_review_sections_present"]), 3)
        self.assertEqual(d["advisory_only_checks"]["autonomous_decisions"], 0)
        # JSON roundtrip
        json_str = json.dumps(d)
        reloaded = json.loads(json_str)
        self.assertEqual(reloaded["report_id"], "v2_5_e2e_full")

    def test_report_serialization(self):
        report = V2_5EndToEndValidationReport(
            report_id="v2_5_e2e_serial",
            generated_at="2025-01-01T00:00:00+00:00",
            total_cases=0,
            cases_processed=0,
            validation_passed=True,
            limitations=["Test limitation 1", "Test limitation 2"],
        )
        d = report.to_dict()
        self.assertIn("limitations", d)
        self.assertEqual(len(d["limitations"]), 2)

    def test_regression_mismatch_count_detects_per_case_mismatch(self):
        count = _regression_mismatch_count(
            [
                V2_5EndToEndCaseResult(
                    case_id="case_001",
                    title="Mismatch case",
                    regression_expected_gate="pass",
                    regression_actual_gate="reject",
                    regression_matched=False,
                )
            ],
            {},
        )
        self.assertEqual(count, 1)

    def test_regression_mismatch_count_detects_metric_mismatch(self):
        count = _regression_mismatch_count(
            [],
            {"gate_decision_mismatches": 2},
        )
        self.assertEqual(count, 2)


class DeriveFounderDecisionAndReasonsTests(unittest.TestCase):
    """Unit tests for _derive_founder_decision_and_reasons."""

    def _base_args(self):
        return {
            "expected": {},
            "gate_decision": "pass",
            "evidence_ids": ["ev_1"],
            "source_signal_ids": ["sig_1"],
            "source_urls": ["https://example.com"],
            "opportunity_id": "opp_1",
            "evidence_pack_id": "ep_1",
        }

    def test_promote_posture(self):
        args = self._base_args()
        args["expected"] = {"founder_review_posture": "promote_candidate"}
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "promote")
        self.assertIn("strong_pain", reasons)
        self.assertIn("clear_buyer", reasons)

    def test_park_posture(self):
        args = self._base_args()
        args["expected"] = {"founder_review_posture": "park_candidate"}
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "park")
        self.assertIn("weak_evidence", reasons)
        self.assertIn("needs_more_examples", reasons)

    def test_needs_more_evidence_posture(self):
        args = self._base_args()
        args["expected"] = {"founder_review_posture": "needs_more_evidence"}
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "needs_more_evidence")

    def test_revisit_posture(self):
        args = self._base_args()
        args["expected"] = {"founder_review_posture": "revisit_candidate"}
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "revisit_later")
        self.assertIn("waiting_for_more_signals", reasons)

    def test_generic_false_positive_kill(self):
        args = self._base_args()
        args["expected"] = {
            "founder_review_posture": "kill_candidate",
            "quality_label": "generic_false_positive",
        }
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "kill")
        self.assertIn("too_generic", reasons)
        self.assertIn("no_buyer", reasons)

    def test_vendor_promo_false_positive_kill(self):
        args = self._base_args()
        args["expected"] = {
            "founder_review_posture": "kill_candidate",
            "quality_label": "vendor_promo_false_positive",
        }
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "kill")
        self.assertIn("vendor_promo_false_positive", reasons)

    def test_duplicate_signal_park(self):
        args = self._base_args()
        args["expected"] = {
            "founder_review_posture": "park_candidate",
            "quality_label": "duplicate_signal",
        }
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "park")

    def test_no_buyer_kill(self):
        args = self._base_args()
        args["expected"] = {
            "founder_review_posture": "kill_candidate",
            "quality_label": "no_buyer",
        }
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "kill")

    def test_weak_noisy_kill(self):
        args = self._base_args()
        args["expected"] = {
            "founder_review_posture": "kill_candidate",
            "quality_label": "weak_noisy",
        }
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "kill")

    def test_killed_pattern_repeat_kill(self):
        args = self._base_args()
        args["expected"] = {
            "founder_review_posture": "kill_candidate",
            "quality_label": "killed_pattern_repeat",
        }
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "kill")
        self.assertIn("repeated_killed_pattern", reasons)
        self.assertIn("disguised_consulting", reasons)

    def test_fallback_to_gate_decision_pass(self):
        args = self._base_args()
        args["gate_decision"] = "pass"
        args["expected"] = {"founder_review_posture": "unknown", "quality_label": "unknown"}
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "promote")

    def test_fallback_to_gate_decision_park(self):
        args = self._base_args()
        args["gate_decision"] = "park"
        args["expected"] = {"founder_review_posture": "unknown", "quality_label": "unknown"}
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "park")

    def test_fallback_to_gate_decision_reject(self):
        args = self._base_args()
        args["gate_decision"] = "reject"
        args["expected"] = {"founder_review_posture": "unknown", "quality_label": "unknown"}
        decision, reasons = _derive_founder_decision_and_reasons(**args)
        self.assertEqual(decision, "kill")


class V2_5EndToEndFixtureValidationIntegrationTests(unittest.TestCase):
    """Integration tests: run full pipeline validation on the fixture dataset."""

    def test_run_full_validation_succeeds(self):
        """End-to-end fixture validation should produce a passing report."""
        report = run_v2_5_end_to_end_fixture_validation()
        self.assertIsNotNone(report)
        self.assertTrue(report.validation_passed)
        self.assertEqual(report.total_cases, 10)
        self.assertEqual(report.cases_processed, 10)
        self.assertEqual(len(report.failed_cases), 0)

    def test_total_cases_matches_fixture(self):
        cases = load_opportunity_quality_cases_v1()
        report = run_v2_5_end_to_end_fixture_validation()
        self.assertEqual(report.total_cases, len(cases))
        self.assertEqual(report.cases_processed, len(cases))

    def test_gate_decision_counts_present(self):
        report = run_v2_5_end_to_end_fixture_validation()
        self.assertIsInstance(report.gate_decision_counts, dict)
        total_gate = sum(report.gate_decision_counts.values())
        self.assertEqual(total_gate, report.cases_processed)

    def test_regression_metrics_included(self):
        report = run_v2_5_end_to_end_fixture_validation()
        self.assertIn("report_id", report.regression_metrics_summary)
        self.assertIn("total_cases", report.regression_metrics_summary)
        self.assertIn("gate_match_rate", report.regression_metrics_summary)

    def test_weekly_review_sections_present(self):
        report = run_v2_5_end_to_end_fixture_validation()
        self.assertIsInstance(report.weekly_review_sections_present, list)
        self.assertGreater(len(report.weekly_review_sections_present), 0)

    def test_next_best_actions_generated(self):
        report = run_v2_5_end_to_end_fixture_validation()
        self.assertGreater(report.next_best_actions_count, 0)

    def test_traceability_checks_nonzero(self):
        report = run_v2_5_end_to_end_fixture_validation()
        checks = report.traceability_checks
        # evidence_pack_to_gate must cover all processed cases
        self.assertEqual(checks["evidence_pack_to_gate"], report.cases_processed)
        self.assertEqual(checks["gate_to_founder_decision"], report.cases_processed)
        self.assertEqual(checks["founder_decision_to_feedback"], report.cases_processed)
        self.assertGreater(checks["feedback_to_signals"], 0, "Feedback must map to signals/evidence")
        self.assertEqual(checks["signals_to_weekly_review"], 1)

    def test_advisory_only_enforcement(self):
        report = run_v2_5_end_to_end_fixture_validation()
        ac = report.advisory_only_checks
        self.assertEqual(ac["total_decisions"], report.cases_processed)
        self.assertEqual(ac["advisory_decisions"], report.cases_processed)
        self.assertEqual(ac["autonomous_decisions"], 0, "No autonomous decisions allowed")

    def test_no_failed_cases(self):
        report = run_v2_5_end_to_end_fixture_validation()
        self.assertEqual(len(report.failed_cases), 0, f"Failed cases: {report.failed_cases}")
        self.assertEqual(len(report.warnings), 0, f"Warnings: {report.warnings}")

    def test_per_case_results_complete(self):
        report = run_v2_5_end_to_end_fixture_validation()
        self.assertEqual(len(report.per_case_results), report.total_cases)
        for case_result in report.per_case_results:
            self.assertTrue(case_result.evidence_pack_valid,
                            f"Case {case_result.case_id}: evidence pack invalid")
            self.assertTrue(case_result.opportunity_candidate_valid,
                            f"Case {case_result.case_id}: opportunity candidate invalid")
            self.assertNotEqual(case_result.gate_decision, "",
                                f"Case {case_result.case_id}: no gate decision")
            self.assertNotEqual(case_result.founder_decision_id, "",
                                f"Case {case_result.case_id}: no founder decision ID")
            self.assertNotEqual(case_result.founder_decision, "",
                                f"Case {case_result.case_id}: no founder decision")
            self.assertTrue(case_result.feedback_mapping_valid,
                            f"Case {case_result.case_id}: feedback mapping invalid")
            self.assertTrue(case_result.advisory_only,
                            f"Case {case_result.case_id}: not advisory only")
            self.assertFalse(case_result.autonomous_action,
                             f"Case {case_result.case_id}: autonomous action detected")
            self.assertEqual(len(case_result.errors), 0,
                             f"Case {case_result.case_id}: errors={case_result.errors}")

    def test_report_to_dict_is_json_serializable(self):
        report = run_v2_5_end_to_end_fixture_validation()
        d = report.to_dict()
        json_str = json.dumps(d)
        reloaded = json.loads(json_str)
        self.assertEqual(reloaded["report_id"], report.report_id)
        self.assertEqual(reloaded["total_cases"], report.total_cases)
        self.assertTrue(reloaded["validation_passed"])

    def test_all_flow_stages_covered(self):
        report = run_v2_5_end_to_end_fixture_validation()
        for case_result in report.per_case_results:
            # Evidence pack feeds quality gate
            self.assertNotEqual(case_result.gate_result_id, "")
            # Quality gate outputs one of pass/park/reject
            self.assertIn(case_result.gate_decision, ("pass", "park", "reject"))
            # Founder decision derived
            self.assertIn(
                case_result.founder_decision,
                ("promote", "park", "kill", "revisit_later", "needs_more_evidence"),
            )
            # Feedback maps back to evidence
            self.assertTrue(case_result.feedback_mapping_valid)
            # Evidence IDs preserved
            self.assertGreater(len(case_result.evidence_ids), 0)
            self.assertGreater(len(case_result.source_signal_ids), 0)
            self.assertGreater(len(case_result.source_urls), 0)

    def test_deterministic_output(self):
        """Two runs with the same fixture should produce identical reports."""
        report1 = run_v2_5_end_to_end_fixture_validation()
        report2 = run_v2_5_end_to_end_fixture_validation()
        d1 = report1.to_dict()
        d2 = report2.to_dict()
        # timestamps differ, exclude generated_at
        d1.pop("generated_at", None)
        d2.pop("generated_at", None)
        # report_id is hash of timestamp, may differ
        d1.pop("report_id", None)
        d2.pop("report_id", None)
        # regression metrics contain its own timestamp
        d1["regression_metrics_summary"].pop("report_id", None)
        d2["regression_metrics_summary"].pop("report_id", None)
        self.assertEqual(d1, d2, "Two runs should produce deterministic output (excluding timestamps)")

    def test_all_fixture_cases_processed(self):
        cases = load_opportunity_quality_cases_v1()
        report = run_v2_5_end_to_end_fixture_validation()
        case_ids = [c["case_id"] for c in cases]
        processed_ids = [r.case_id for r in report.per_case_results]
        self.assertEqual(sorted(case_ids), sorted(processed_ids))

    def test_report_limitations_included(self):
        report = run_v2_5_end_to_end_fixture_validation()
        self.assertIsInstance(report.limitations, list)
        self.assertGreater(len(report.limitations), 0)
        self.assertIn("synthetic", report.limitations[0].lower())


if __name__ == "__main__":
    unittest.main()
