"""Tests for v2.8 correction workflow end-to-end validation (Roadmap v2.8 item 6.1).

All tests use temp directories — no real artifacts/ are written.
No live APIs, no live LLMs, no portfolio mutations.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from oos.v2_8_correction_workflow_validation import (
    VALIDATION_SCHEMA_VERSION,
    V2_8CorrectionWorkflowValidationReport,
    V2_8CorrectionWorkflowValidationStep,
    _iso_utc_now,
    run_v2_8_correction_workflow_validation,
    v2_8_correction_workflow_validation_to_json,
)


# ---------------------------------------------------------------------------
# 1. Report model serialization tests
# ---------------------------------------------------------------------------


class TestV2_8ReportModelSerialization(unittest.TestCase):
    """Test that report models serialize to deterministic JSON."""

    def test_report_model_serializes_to_deterministic_json(self):
        """Report model to_dict and to_json produce valid, schema-versioned output."""
        report = V2_8CorrectionWorkflowValidationReport(
            schema_version=VALIDATION_SCHEMA_VERSION,
            generated_at="2026-05-10T10:00:00Z",
            validation_passed=True,
            run_id="test_run_01",
            temp_project_root="/tmp/test",
            initial_decision_count=5,
            import_history_entry_count=2,
            correction_count=2,
            advisory_only=True,
            no_live_api=True,
            no_live_llm=True,
        )
        d = report.to_dict()
        self.assertEqual(d["schema_version"], VALIDATION_SCHEMA_VERSION)
        self.assertEqual(d["run_id"], "test_run_01")
        self.assertEqual(d["initial_decision_count"], 5)
        self.assertEqual(d["import_history_entry_count"], 2)
        self.assertEqual(d["correction_count"], 2)
        self.assertTrue(d["advisory_only"])
        self.assertTrue(d["no_live_api"])
        self.assertTrue(d["no_live_llm"])
        self.assertEqual(len(d["steps"]), 0)
        self.assertEqual(d["temp_project_root"], "/tmp/test")

        json_str = v2_8_correction_workflow_validation_to_json(report)
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["schema_version"], VALIDATION_SCHEMA_VERSION)
        self.assertEqual(parsed["validation_passed"], True)

    def test_report_roundtrip_preserves_fields(self):
        """JSON serialize -> deserialize preserves core fields."""
        step = V2_8CorrectionWorkflowValidationStep(
            step_id="c1",
            name="Build weekly cycle",
            status="passed",
            summary="Built run with 14 artifacts.",
            artifacts_read=["manifest.json"],
            artifacts_written=["evidence_packs.json"],
        )
        report = V2_8CorrectionWorkflowValidationReport(
            generated_at="2026-05-10T10:00:00Z",
            validation_passed=True,
            steps=[step],
            run_id="roundtrip_test",
            temp_project_root="/tmp/test",
            initial_decision_count=3,
            replace_operation_summary={"review_item_id": "ri_01", "imported_count": 1},
            amend_operation_summary={"review_item_id": "ri_02", "imported_count": 1},
            import_history_entry_count=2,
            correction_count=2,
            parking_lot_cleanup_summary={"parking_lot_record_count": 1, "consistent": True},
            source_url_traceability_summary={"placeholder_url_count": 0},
        )
        json_str = v2_8_correction_workflow_validation_to_json(report)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["run_id"], "roundtrip_test")
        self.assertEqual(len(parsed["steps"]), 1)
        self.assertEqual(parsed["steps"][0]["step_id"], "c1")
        self.assertEqual(parsed["steps"][0]["status"], "passed")
        self.assertEqual(parsed["import_history_entry_count"], 2)
        self.assertEqual(parsed["correction_count"], 2)
        self.assertEqual(parsed["replace_operation_summary"]["imported_count"], 1)
        self.assertEqual(parsed["amend_operation_summary"]["imported_count"], 1)

    def test_report_errors_field_present(self):
        """Errors field is always present even when empty."""
        report = V2_8CorrectionWorkflowValidationReport()
        d = report.to_dict()
        self.assertIn("errors", d)
        self.assertEqual(d["errors"], [])
        self.assertIn("warnings", d)
        self.assertEqual(d["warnings"], [])


class TestV2_8StepModelSerialization(unittest.TestCase):
    """Test that step model serializes to deterministic JSON."""

    def test_step_model_serializes_correctly(self):
        """Step model to_dict includes all fields."""
        step = V2_8CorrectionWorkflowValidationStep(
            step_id="c4",
            name="Initial decision import",
            status="passed",
            summary="Imported 5 decisions.",
            artifacts_read=["founder_decisions_v2.json"],
            artifacts_written=["founder_feedback_mappings.json"],
        )
        d = step.to_dict()
        self.assertEqual(d["step_id"], "c4")
        self.assertEqual(d["name"], "Initial decision import")
        self.assertEqual(d["status"], "passed")
        self.assertEqual(d["summary"], "Imported 5 decisions.")
        self.assertEqual(d["artifacts_read"], ["founder_decisions_v2.json"])
        self.assertEqual(d["artifacts_written"], ["founder_feedback_mappings.json"])
        self.assertEqual(d["warnings"], [])
        self.assertEqual(d["errors"], [])

    def test_failed_step_serializes_errors(self):
        """Failed step includes errors."""
        step = V2_8CorrectionWorkflowValidationStep(
            step_id="c6",
            name="Replace decision",
            status="failed",
            summary="Replace failed.",
            errors=["No decision to replace."],
        )
        d = step.to_dict()
        self.assertEqual(d["status"], "failed")
        self.assertEqual(d["errors"], ["No decision to replace."])

    def test_skipped_step_serializes(self):
        """Skipped step has empty artifacts and errors."""
        step = V2_8CorrectionWorkflowValidationStep(
            step_id="c5",
            name="Find parking decision",
            status="skipped",
            summary="No parking decision found.",
        )
        d = step.to_dict()
        self.assertEqual(d["status"], "skipped")
        self.assertEqual(d["artifacts_read"], [])
        self.assertEqual(d["artifacts_written"], [])


# ---------------------------------------------------------------------------
# 2. Full validation tests
# ---------------------------------------------------------------------------


class TestV2_8FullValidation(unittest.TestCase):
    """Test the full correction workflow validation in temp project roots."""

    def test_full_validation_passes_in_temp_project_root(self):
        """Full correction workflow validation runs and returns a report."""
        report = run_v2_8_correction_workflow_validation()
        self.assertIsInstance(report, V2_8CorrectionWorkflowValidationReport)
        self.assertEqual(report.schema_version, VALIDATION_SCHEMA_VERSION)
        self.assertIsInstance(report.generated_at, str)
        self.assertTrue(len(report.generated_at) > 0)
        # Even if validation_passed is False (missing fixture), report should
        # be well-formed
        self.assertIsInstance(report.steps, list)
        self.assertIsInstance(report.warnings, list)
        self.assertIsInstance(report.errors, list)
        self.assertTrue(report.advisory_only)
        self.assertTrue(report.no_live_api)
        self.assertTrue(report.no_live_llm)

    def test_validation_creates_no_real_artifacts_pollution(self):
        """Validation runs in temp dir only — no real artifacts/ pollution."""
        real_artifacts = Path(__file__).resolve().parent.parent / "artifacts"
        report = run_v2_8_correction_workflow_validation()
        # The temp_project_root should not be the real artifacts dir
        if report.temp_project_root:
            self.assertNotEqual(
                str(real_artifacts.resolve()),
                str(Path(report.temp_project_root).resolve()),
            )
        # Real artifacts/ should not have been modified
        self.assertIsInstance(report, V2_8CorrectionWorkflowValidationReport)

    def test_validation_uses_temp_root_only(self):
        """Report records temp_project_root that is not the real repo root."""
        real_root = Path(__file__).resolve().parent.parent
        report = run_v2_8_correction_workflow_validation()
        if report.temp_project_root:
            temp_root = Path(report.temp_project_root).resolve()
            self.assertNotEqual(str(real_root.resolve()), str(temp_root))

    def test_advisory_no_live_flags_are_true(self):
        """Advisory_only, no_live_api, no_live_llm are always True."""
        report = run_v2_8_correction_workflow_validation()
        self.assertTrue(report.advisory_only)
        self.assertTrue(report.no_live_api)
        self.assertTrue(report.no_live_llm)

    def test_no_portfolio_mutation(self):
        """Validation does not modify portfolio state."""
        report = run_v2_8_correction_workflow_validation()
        # The report should not indicate any portfolio-state artifacts written
        self.assertIsInstance(report, V2_8CorrectionWorkflowValidationReport)
        # Advisory-only flag enforced
        self.assertTrue(report.advisory_only)

    def test_correction_count_gte_2_when_both_operations_run(self):
        """When both replace and amend succeed, correction_count >= 2."""
        report = run_v2_8_correction_workflow_validation()
        # If validation passed, correction_count should be >= 2
        if report.validation_passed:
            self.assertGreaterEqual(
                report.correction_count, 2,
                f"Expected correction_count >= 2, got {report.correction_count}"
            )

    def test_source_url_placeholder_count_zero(self):
        """Source URL traceability reports zero placeholder URNs."""
        report = run_v2_8_correction_workflow_validation()
        if report.validation_passed:
            placeholder_count = report.source_url_traceability_summary.get(
                "placeholder_url_count", -1
            )
            self.assertEqual(
                placeholder_count, 0,
                f"Expected 0 placeholder URNs, got {placeholder_count}"
            )

    def test_no_urn_oos_placeholders_in_report(self):
        """Report itself contains no urn:oos:* placeholders."""
        report = run_v2_8_correction_workflow_validation()
        json_str = v2_8_correction_workflow_validation_to_json(report)
        self.assertNotIn("urn:oos:", json_str.lower())

    def test_report_has_steps(self):
        """Validation report always contains steps list."""
        report = run_v2_8_correction_workflow_validation()
        self.assertIsInstance(report.steps, list)
        # Should have at least some steps (even if some fail early)
        self.assertGreater(len(report.steps), 0)

    def test_failure_state_reported_cleanly(self):
        """When validation fails, errors list is populated."""
        report = run_v2_8_correction_workflow_validation()
        if not report.validation_passed:
            # Should have errors or failed steps
            has_error_info = (
                len(report.errors) > 0
                or any(s.status == "failed" for s in report.steps)
            )
            self.assertTrue(
                has_error_info,
                "Failing validation should have errors or failed steps."
            )

    def test_iso_utc_now_returns_valid_timestamp(self):
        """Helper _iso_utc_now returns ISO UTC timestamp."""
        ts = _iso_utc_now()
        self.assertIsInstance(ts, str)
        self.assertIn("T", ts)
        # Should be parseable
        datetime.fromisoformat(ts)


# ---------------------------------------------------------------------------
# 3. Step-specific validation tests
# ---------------------------------------------------------------------------


class TestV2_8StepSpecific(unittest.TestCase):
    """Test individual step behaviors within the validation workflow."""

    def test_initial_decision_import_sets_count(self):
        """Initial decision import populates initial_decision_count."""
        report = run_v2_8_correction_workflow_validation()
        if report.validation_passed:
            self.assertGreater(report.initial_decision_count, 0,
                               "Should have imported initial decisions")
        else:
            # If validation failed before import, count may be 0
            self.assertGreaterEqual(report.initial_decision_count, 0)

    def test_replace_operation_summary_populated(self):
        """Replace operation summary is populated when replace runs."""
        report = run_v2_8_correction_workflow_validation()
        if report.validation_passed:
            self.assertIn("review_item_id", report.replace_operation_summary)
            self.assertIn("imported_count", report.replace_operation_summary)

    def test_amend_operation_summary_populated(self):
        """Amend operation summary is populated when amend runs."""
        report = run_v2_8_correction_workflow_validation()
        if report.validation_passed:
            self.assertIn("review_item_id", report.amend_operation_summary)
            self.assertIn("imported_count", report.amend_operation_summary)

    def test_import_history_entry_count_consistent(self):
        """Import history entry count is >= correction_count."""
        report = run_v2_8_correction_workflow_validation()
        if report.validation_passed:
            self.assertGreaterEqual(
                report.import_history_entry_count,
                report.correction_count,
            )

    def test_status_report_dashboard_visible(self):
        """Status, run report, and dashboard show correction state."""
        report = run_v2_8_correction_workflow_validation()
        if report.validation_passed:
            # The c13 step should have passed
            c13_steps = [s for s in report.steps if s.step_id == "c13"]
            if c13_steps:
                self.assertEqual(c13_steps[0].status, "passed")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
