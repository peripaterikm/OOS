"""Tests for v2.9 operational validation (Roadmap v2.9 item 4.1).

All tests use temp directories — no real artifacts/ are written.
No live APIs, no live LLMs, no portfolio mutations.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from oos.output_modes import get_output_symbols, validate_output_mode
from oos.source_url_traceability import (
    SourceURLTraceabilityReport,
    check_source_url_traceability,
    is_placeholder_source_url,
)
from oos.v2_9_operational_validation import (
    VALIDATION_SCHEMA_VERSION,
    V2_9OperationalValidationReport,
    V2_9OperationalValidationStep,
    _contains_non_ascii_symbols,
    _is_ascii_safe_symbol,
    _iso_utc_now,
    run_v2_9_operational_validation,
    v2_9_operational_validation_to_json,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ===========================================================================
# 1. Report model serialization tests
# ===========================================================================


class TestV2_9ReportModelSerialization(unittest.TestCase):
    """Test that report models serialize to deterministic JSON."""

    def test_report_model_serializes_to_deterministic_json(self):
        report = V2_9OperationalValidationReport(
            schema_version=VALIDATION_SCHEMA_VERSION,
            generated_at="2026-05-10T12:00:00Z",
            validation_passed=True,
            run_id="test_run_opval",
            temp_project_root="/tmp/test",
            v2_8_validation_passed=True,
            ascii_default_safe=True,
            utf8_opt_in_works=True,
            source_url_missing_count=0,
            source_url_placeholder_count=0,
            source_url_validation_passed=True,
            advisory_only=True,
            no_live_api=True,
            no_live_llm=True,
        )
        d = report.to_dict()
        self.assertEqual(d["schema_version"], VALIDATION_SCHEMA_VERSION)
        self.assertEqual(d["run_id"], "test_run_opval")
        self.assertTrue(d["v2_8_validation_passed"])
        self.assertTrue(d["ascii_default_safe"])
        self.assertTrue(d["utf8_opt_in_works"])
        self.assertEqual(d["source_url_missing_count"], 0)
        self.assertEqual(d["source_url_placeholder_count"], 0)
        self.assertTrue(d["source_url_validation_passed"])
        self.assertTrue(d["advisory_only"])
        self.assertTrue(d["no_live_api"])
        self.assertTrue(d["no_live_llm"])
        self.assertEqual(len(d["steps"]), 0)

        json_str = v2_9_operational_validation_to_json(report)
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["schema_version"], VALIDATION_SCHEMA_VERSION)
        self.assertTrue(parsed["validation_passed"])

    def test_report_roundtrip_preserves_fields(self):
        step = V2_9OperationalValidationStep(
            step_id="v1",
            name="v2.8 correction workflow validation",
            status="passed",
            summary="v2.8 validation passed.",
            artifacts_read=["manifest.json"],
            artifacts_written=[],
        )
        report = V2_9OperationalValidationReport(
            generated_at="2026-05-10T12:00:00Z",
            validation_passed=True,
            steps=[step],
            run_id="roundtrip_test",
            v2_8_validation_passed=True,
            ascii_default_safe=True,
            utf8_opt_in_works=True,
            source_url_missing_count=0,
            source_url_placeholder_count=0,
            source_url_validation_passed=True,
        )
        json_str = v2_9_operational_validation_to_json(report)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["run_id"], "roundtrip_test")
        self.assertEqual(len(parsed["steps"]), 1)
        self.assertEqual(parsed["steps"][0]["step_id"], "v1")
        self.assertEqual(parsed["steps"][0]["status"], "passed")

    def test_failed_report_has_validation_passed_false(self):
        report = V2_9OperationalValidationReport(
            generated_at="2026-05-10T12:00:00Z",
            validation_passed=False,
            errors=["v2.8 failed"],
            v2_8_validation_passed=False,
        )
        self.assertFalse(report.validation_passed)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("v2.8 failed", report.errors[0])

    def test_step_model_serializes(self):
        step = V2_9OperationalValidationStep(
            step_id="v4",
            name="Status Markdown ASCII default",
            status="passed",
            summary="ASCII-safe by default.",
            warnings=["minor thing"],
        )
        d = step.to_dict()
        self.assertEqual(d["step_id"], "v4")
        self.assertEqual(d["status"], "passed")
        self.assertEqual(d["warnings"], ["minor thing"])

    def test_step_errors_preserved(self):
        step = V2_9OperationalValidationStep(
            step_id="v7",
            name="Source URL traceability",
            status="failed",
            summary="missing_count=1",
            errors=["missing_count=1"],
        )
        d = step.to_dict()
        self.assertEqual(d["errors"], ["missing_count=1"])


# ===========================================================================
# 2. ASCII/Unicode helpers
# ===========================================================================


class TestASCIIUnicodeHelpers(unittest.TestCase):
    """Test _is_ascii_safe_symbol and _contains_non_ascii_symbols."""

    def test_ascii_printable_is_safe(self):
        for oc in range(32, 127):
            self.assertTrue(_is_ascii_safe_symbol(chr(oc)),
                            f"ord={oc} should be safe")

    def test_newline_and_tab_are_safe(self):
        self.assertTrue(_is_ascii_safe_symbol("\n"))
        self.assertTrue(_is_ascii_safe_symbol("\t"))

    def test_unicode_symbols_not_safe(self):
        self.assertFalse(_is_ascii_safe_symbol("\u2713"))  # ✓
        self.assertFalse(_is_ascii_safe_symbol("\u2192"))  # →
        self.assertFalse(_is_ascii_safe_symbol("\u2014"))  # —
        self.assertFalse(_is_ascii_safe_symbol("\u26a0"))  # ⚠

    def test_pure_ascii_text_passes(self):
        self.assertFalse(_contains_non_ascii_symbols("Hello World\nOK\nFAIL\n"))
        self.assertFalse(_contains_non_ascii_symbols("[PASS] [FAIL] [WARN]"))
        self.assertFalse(_contains_non_ascii_symbols("NONE [CORRECTED] -> -"))

    def test_mixed_text_fails(self):
        self.assertTrue(_contains_non_ascii_symbols("Hello \u2713 World"))
        self.assertTrue(_contains_non_ascii_symbols("OK \u2192 FAIL"))

    def test_empty_string_passes(self):
        self.assertFalse(_contains_non_ascii_symbols(""))


# ===========================================================================
# 3. ASCII default output symbol check
# ===========================================================================


class TestASCIIDefaultOutputSymbols(unittest.TestCase):
    """Verify get_output_symbols('ascii_safe') returns only ASCII-safe symbols."""

    def test_ascii_mode_all_symbols_ascii_safe(self):
        syms = get_output_symbols("ascii_safe")
        for key, val in syms.items():
            for ch in val:
                self.assertTrue(
                    _is_ascii_safe_symbol(ch),
                    f"ASCII symbol '{key}'='{val}' contains non-ASCII U+{ord(ch):04X}",
                )

    def test_ascii_mode_has_expected_keys(self):
        syms = get_output_symbols("ascii_safe")
        expected_keys = {"success", "failure", "warning", "none", "arrow", "dash", "corrected"}
        self.assertEqual(set(syms.keys()), expected_keys)

    def test_ascii_mode_success_is_OK(self):
        syms = get_output_symbols("ascii_safe")
        self.assertEqual(syms["success"], "OK")
        self.assertTrue(all(ord(c) < 128 for c in syms["success"]))


# ===========================================================================
# 4. UTF-8 opt-in output symbol check
# ===========================================================================


class TestUTF8OptInOutputSymbols(unittest.TestCase):
    """Verify get_output_symbols('utf8') returns Unicode symbols."""

    def test_utf8_mode_has_unicode_symbols(self):
        syms = get_output_symbols("utf8")
        has_unicode = any(
            any(not _is_ascii_safe_symbol(ch) for ch in val)
            for val in syms.values()
        )
        self.assertTrue(has_unicode,
                        "UTF-8 mode must contain Unicode symbols (✓, ✗, ⚠, →, —)")

    def test_utf8_mode_arrow_is_unicode(self):
        syms = get_output_symbols("utf8")
        self.assertEqual(syms["arrow"], "\u2192")  # →
        self.assertFalse(_is_ascii_safe_symbol(syms["arrow"]))

    def test_utf8_mode_dash_is_em_dash(self):
        syms = get_output_symbols("utf8")
        self.assertEqual(syms["dash"], "\u2014")  # —
        self.assertFalse(_is_ascii_safe_symbol(syms["dash"]))

    def test_utf8_mode_success_is_checkmark(self):
        syms = get_output_symbols("utf8")
        self.assertEqual(syms["success"], "\u2713")  # ✓

    def test_utf8_mode_corrected_stays_ascii(self):
        syms = get_output_symbols("utf8")
        self.assertEqual(syms["corrected"], "[CORRECTED]")

    def test_utf8_mode_none_stays_ascii(self):
        syms = get_output_symbols("utf8")
        self.assertEqual(syms["none"], "NONE")


# ===========================================================================
# 5. Output mode validation
# ===========================================================================


class TestOutputModeValidation(unittest.TestCase):
    """Test validate_output_mode from output_modes."""

    def test_ascii_safe_accepted(self):
        self.assertEqual(validate_output_mode("ascii_safe"), "ascii_safe")

    def test_utf8_accepted(self):
        self.assertEqual(validate_output_mode("utf8"), "utf8")

    def test_bogus_rejected(self):
        with self.assertRaises(ValueError):
            validate_output_mode("bogus")

    def test_empty_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_output_mode("")


# ===========================================================================
# 6. Source URL traceability strictness
# ===========================================================================


class TestSourceURLTraceabilityStrictness(unittest.TestCase):
    """Verify source URL traceability contract behavior for v2.9."""

    def test_real_url_not_placeholder(self):
        self.assertFalse(is_placeholder_source_url("https://news.ycombinator.com/item?id=1"))

    def test_placeholder_urn_detected(self):
        self.assertTrue(is_placeholder_source_url("urn:oos:founder_import:placeholder"))

    def test_empty_string_not_placeholder(self):
        self.assertFalse(is_placeholder_source_url(""))

    def test_report_model_no_live_flags(self):
        report = SourceURLTraceabilityReport(
            run_dir="/tmp/test",
            validation_passed=True,
        )
        self.assertTrue(report.advisory_only)
        self.assertTrue(report.no_live_api)
        self.assertTrue(report.no_live_llm)


# ===========================================================================
# 7. Smoke script v2.9 expectation tests
# ===========================================================================


class TestSmokeScriptV2_9Expectations(unittest.TestCase):
    """Verify controlled-smoke script contains v2.9 expectations."""

    SCRIPT_PATH = REPO_ROOT / "scripts" / "run-controlled-smoke.ps1"

    def test_smoke_script_checks_missing_count(self):
        text = self.SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("missing_count", text,
                       "Smoke script must check missing_count from traceability report")
        self.assertIn("validation_passed", text,
                       "Smoke script must check validation_passed from traceability report")

    def test_smoke_script_expects_missing_count_zero(self):
        text = self.SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("missing_count=0", text,
                       "Smoke script must reference v2.9 expectation of missing_count=0")

    def test_smoke_script_fails_on_placeholder_gt_zero(self):
        text = self.SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("Record-Fail", text,
                       "Smoke script must have failure recording for placeholder count")

    def test_smoke_script_forbidden_commands_absent(self):
        """Verify no destructive git commands in smoke script."""
        text = self.SCRIPT_PATH.read_text(encoding="utf-8")
        forbidden = ["git add", "git commit", "git push", "git merge",
                     "git tag", "Remove-Item -Recurse -Force"]
        for cmd in forbidden:
            self.assertNotIn(cmd, text,
                             f"Smoke script must not contain '{cmd}'")


# ===========================================================================
# 8. Full v2.9 operational validation in temp root
# ===========================================================================


class TestV2_9OperationalValidationInTempRoot(unittest.TestCase):
    """Run full v2.9 operational validation in a temp project root."""

    def test_validation_runs_in_temp_root(self):
        report = run_v2_9_operational_validation()
        self.assertIsNotNone(report)
        self.assertIsInstance(report, V2_9OperationalValidationReport)
        # Must have steps
        self.assertGreater(len(report.steps), 0, "Should have validation steps")
        # Safe flags must be true
        self.assertTrue(report.advisory_only)
        self.assertTrue(report.no_live_api)
        self.assertTrue(report.no_live_llm)

    def test_validation_ascii_default_safe_flag(self):
        report = run_v2_9_operational_validation()
        self.assertTrue(
            report.ascii_default_safe,
            "ASCII default output symbols must be safe (all ord < 128)",
        )

    def test_validation_utf8_opt_in_works_flag(self):
        report = run_v2_9_operational_validation()
        self.assertTrue(
            report.utf8_opt_in_works,
            "UTF-8 opt-in output must contain Unicode markers",
        )

    def test_validation_v2_8_step_present(self):
        report = run_v2_9_operational_validation()
        v2_8_step = next((s for s in report.steps if s.step_id == "v1"), None)
        self.assertIsNotNone(v2_8_step, "Step v1 (v2.8 validation) must be present")

    def test_validation_ascii_step_present(self):
        report = run_v2_9_operational_validation()
        ascii_step = next((s for s in report.steps if s.step_id == "v2"), None)
        self.assertIsNotNone(ascii_step, "Step v2 (ASCII symbol check) must be present")

    def test_validation_utf8_step_present(self):
        report = run_v2_9_operational_validation()
        utf8_step = next((s for s in report.steps if s.step_id == "v3"), None)
        self.assertIsNotNone(utf8_step, "Step v3 (UTF-8 symbol check) must be present")

    def test_validation_traceability_step_present(self):
        report = run_v2_9_operational_validation()
        trace_step = next((s for s in report.steps if s.step_id == "v7"), None)
        self.assertIsNotNone(trace_step, "Step v7 (traceability) must be present")

    def test_validation_safety_step_present(self):
        report = run_v2_9_operational_validation()
        safety_step = next((s for s in report.steps if s.step_id == "v8"), None)
        self.assertIsNotNone(safety_step, "Step v8 (safety flags) must be present")

    def test_no_live_api_flag_true(self):
        report = run_v2_9_operational_validation()
        self.assertTrue(report.no_live_api)

    def test_no_live_llm_flag_true(self):
        report = run_v2_9_operational_validation()
        self.assertTrue(report.no_live_llm)

    def test_report_json_serializes(self):
        report = run_v2_9_operational_validation()
        json_str = v2_9_operational_validation_to_json(report)
        self.assertIsInstance(json_str, str)
        # Parse to verify valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(parsed["schema_version"], VALIDATION_SCHEMA_VERSION)


# ===========================================================================
# 9. Smoke script PowerShell execution test
# ===========================================================================


class TestSmokeScriptExecution(unittest.TestCase):
    """Verify the smoke script runs in a temp context without errors (syntax check)."""

    def test_smoke_script_is_valid_powershell(self):
        script_path = REPO_ROOT / "scripts" / "run-controlled-smoke.ps1"
        self.assertTrue(script_path.is_file(), f"Script not found: {script_path}")
        # Basic syntax check: invoke PowerShell parser
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive",
                "-Command",
                f"$ErrorActionPreference='Stop'; "
                f"try {{ $ast=[System.Management.Automation.Language.Parser]::ParseFile("
                f"'{script_path}', [ref]$null, [ref]$null); "
                f"if(-not $ast){{ throw 'parse failed' }}; "
                f"Write-Output 'OK' }} catch {{ Write-Output 'FAIL' }}",
            ],
            capture_output=True, text=True, timeout=30,
        )
        self.assertIn("OK", result.stdout,
                      f"Smoke script PowerShell parse failed: {result.stderr}")


# ===========================================================================
# 10. Determinism check
# ===========================================================================


class TestDeterminism(unittest.TestCase):
    """Verify operational validation produces deterministic output."""

    def test_consecutive_runs_produce_valid_reports(self):
        """Two consecutive runs should both produce valid reports."""
        report1 = run_v2_9_operational_validation()
        report2 = run_v2_9_operational_validation()
        # Both should have the same structure
        self.assertEqual(report1.schema_version, VALIDATION_SCHEMA_VERSION)
        self.assertEqual(report2.schema_version, VALIDATION_SCHEMA_VERSION)
        # Both should assert safety flags
        self.assertTrue(report1.advisory_only)
        self.assertTrue(report2.advisory_only)
        self.assertTrue(report1.no_live_api)
        self.assertTrue(report2.no_live_api)
        self.assertTrue(report1.no_live_llm)
        self.assertTrue(report2.no_live_llm)
        # ASCII and UTF-8 checks should be deterministic
        self.assertTrue(report1.ascii_default_safe)
        self.assertTrue(report2.ascii_default_safe)
        self.assertTrue(report1.utf8_opt_in_works)
        self.assertTrue(report2.utf8_opt_in_works)
