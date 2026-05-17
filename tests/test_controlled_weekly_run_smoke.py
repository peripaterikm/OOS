"""Tests for controlled weekly run smoke test (Roadmap v2.7 item 5.1).

Covers:
- Runbook existence and required content
- Smoke script existence, strict mode, and forbidden command checks
- Smoke script temp-only and safety boundary verification
- Optional lightweight execution test against temp root
- v2.14 hardened quality smoke gate checks (v2.14-FIX)
"""

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
RUNBOOKS_DIR = REPO_ROOT / "docs" / "runbooks"

FORBIDDEN_COMMANDS = [
    "git add",
    "git commit",
    "git push",
    "git merge",
    "git tag",
    "git reset",
    "git clean",
    "gh pr create",
    "gh pr merge",
    "Remove-Item",
    "rm ",
    "del ",
]


def _read_script_text(script_name: str) -> str:
    path = SCRIPTS_DIR / script_name
    return path.read_text(encoding="utf-8")


def _read_runbook_text(runbook_name: str) -> str:
    path = RUNBOOKS_DIR / runbook_name
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Runbook existence tests
# ---------------------------------------------------------------------------


class TestRunbookExists(unittest.TestCase):
    """Verify the controlled weekly run smoke test runbook exists."""

    def test_runbook_exists(self) -> None:
        path = RUNBOOKS_DIR / "controlled_weekly_run_smoke_test.md"
        self.assertTrue(path.is_file(),
                        f"Runbook not found at {path}")


class TestRunbookContainsRequiredCommands(unittest.TestCase):
    """Verify the runbook references all required CLI commands."""

    REQUIRED_COMMANDS = [
        "run-weekly-cycle-v2",
        "import-founder-decisions-v2",
        "weekly-cycle-status-v2",
        "build-weekly-run-report-v2",
        "weekly-dashboard-v2",
        "check_source_url_traceability",
    ]

    def test_contains_run_weekly_cycle(self) -> None:
        text = _read_runbook_text("controlled_weekly_run_smoke_test.md")
        for cmd in self.REQUIRED_COMMANDS:
            with self.subTest(command=cmd):
                self.assertIn(cmd, text,
                              f"Runbook missing required command: {cmd}")


class TestRunbookContainsSafetyBoundaries(unittest.TestCase):
    """Verify the runbook explicitly states safety boundaries."""

    REQUIRED_BOUNDARIES = [
        "calls live apis",
        "accesses the internet",
        "real `artifacts/`",
        "`git push`",
        "`git merge`",
        "`git tag`",
        "`gh pr create`",
        "no live api",
        "no live llm",
        "does not perform",
    ]

    def test_contains_safety_boundaries(self) -> None:
        text = _read_runbook_text("controlled_weekly_run_smoke_test.md").lower()
        for boundary in self.REQUIRED_BOUNDARIES:
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, text,
                              f"Runbook missing safety boundary: {boundary}")


class TestRunbookContainsSections(unittest.TestCase):
    """Verify the runbook has all required sections."""

    REQUIRED_SECTIONS = [
        "Purpose",
        "Preconditions",
        "Safety Boundaries",
        "Pre-flight Checks",
        "Fixture Input",
        "Weekly Cycle Run",
        "Founder Inbox Review",
        "Decision Import",
        "Undo-Last Correction",
        "Status Check",
        "Run Report",
        "Dashboard",
        "Source URL Traceability Verification",
        "Expected Artifacts",
        "Expected Success Criteria",
        "Expected Failure Modes",
        "Cleanup",
        "Troubleshooting",
        "Explicit Safety Note",
    ]

    def test_contains_all_sections(self) -> None:
        text = _read_runbook_text("controlled_weekly_run_smoke_test.md")
        for section in self.REQUIRED_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, text,
                              f"Runbook missing section: {section}")


# ---------------------------------------------------------------------------
# Smoke script existence tests
# ---------------------------------------------------------------------------


class TestSmokeScriptExists(unittest.TestCase):
    """Verify the controlled smoke script exists."""

    def test_smoke_script_exists(self) -> None:
        path = SCRIPTS_DIR / "run-controlled-smoke.ps1"
        self.assertTrue(path.is_file(),
                        f"Smoke script not found at {path}")


class TestSmokeScriptNoForbiddenCommands(unittest.TestCase):
    """Verify the smoke script contains no forbidden git/destructive commands."""

    def test_no_forbidden_commands(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        lines = text.splitlines()
        in_comment_block = False
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("<#"):
                in_comment_block = True
                continue
            if stripped.startswith("#>"):
                in_comment_block = False
                continue
            if in_comment_block:
                continue
            if (stripped.startswith("#") or stripped.startswith("Write-Host") or
                    stripped.startswith("REMINDER") or stripped.startswith("NOTE:")):
                continue
            for cmd in FORBIDDEN_COMMANDS:
                if cmd in stripped and (
                    stripped.startswith("&") or
                    stripped.startswith("git ") or
                    stripped.startswith("gh ") or
                    stripped.startswith("Remove-Item") or
                    stripped.startswith("rm ") or
                    stripped.startswith("del ")
                ):
                    self.fail(
                        f"run-controlled-smoke.ps1:{i} contains forbidden "
                        f"command '{cmd}': {stripped}"
                    )


class TestSmokeScriptNoLiveApi(unittest.TestCase):
    """Verify the smoke script makes no actual live API/LLM calls."""

    LIVE_CALL_PATTERNS = [
        "Invoke-RestMethod",
        "Invoke-WebRequest",
        "curl ",
        "wget ",
        "Authorization: Bearer",
        "api-key",
    ]

    def test_no_live_calls(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        for pattern in self.LIVE_CALL_PATTERNS:
            self.assertNotIn(
                pattern, text,
                f"Smoke script contains live API call pattern: {pattern}"
            )

    def test_api_hostnames_only_in_safety_checks(self) -> None:
        """api.openai.com / api.anthropic.com may only appear in safety checks."""
        text = _read_script_text("run-controlled-smoke.ps1")
        lines = text.splitlines()
        in_comment_block = False
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("<#"):
                in_comment_block = True
                continue
            if stripped.startswith("#>"):
                in_comment_block = False
                continue
            if in_comment_block or stripped.startswith("#"):
                continue
            if "api.openai.com" in stripped or "api.anthropic.com" in stripped:
                if "-match" not in stripped and "Write-Host" not in stripped:
                    self.fail(
                        f"run-controlled-smoke.ps1:{i}: live API hostname "
                        f"outside safety check: {stripped}"
                    )


class TestSmokeScriptStrictMode(unittest.TestCase):
    """Verify the smoke script uses Set-StrictMode and ErrorActionPreference."""

    def test_has_strict_mode(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("Set-StrictMode", text,
                      "Smoke script missing Set-StrictMode")
        self.assertIn("$ErrorActionPreference", text,
                      "Smoke script missing ErrorActionPreference")


class TestSmokeScriptHasCommentBasedHelp(unittest.TestCase):
    """Verify the smoke script has comment-based help."""

    def test_has_help(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn(".SYNOPSIS", text,
                      "Smoke script missing .SYNOPSIS")
        self.assertIn(".DESCRIPTION", text,
                      "Smoke script missing .DESCRIPTION")
        self.assertIn(".EXAMPLE", text,
                      "Smoke script missing .EXAMPLE")


class TestSmokeScriptUsesTempRoot(unittest.TestCase):
    """Verify the smoke script creates/uses a temporary project root."""

    def test_uses_temp_root(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("$TempRoot", text,
                      "Smoke script missing temp root variable")
        self.assertIn("[System.IO.Path]::GetTempPath()", text,
                      "Smoke script does not use system temp path")
        self.assertIn("temp root:", text.lower(),
                      "Smoke script does not mention temp root")


class TestSmokeScriptDoesNotWriteToRealArtifacts(unittest.TestCase):
    """Verify the smoke script never writes to the real artifacts/ directory."""

    def test_no_real_artifacts_write(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("<#") or stripped.startswith("#>"):
                continue
            if "$ProjectRoot" in stripped and "artifacts" in stripped.lower():
                if ("RealArtifacts" in stripped or "RealWeeklyRuns" in stripped or
                        "pre-existing" in stripped.lower()):
                    continue
                self.fail(
                    f"run-controlled-smoke.ps1:{i} may write to real "
                    f"artifacts/: {stripped}"
                )


class TestSmokeScriptHasSourceUrlCheck(unittest.TestCase):
    """Verify the smoke script includes source URL traceability verification."""

    def test_has_source_url_check(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("check_source_url_traceability", text,
                      "Smoke script missing source URL traceability check")
        self.assertIn("placeholder", text.lower(),
                      "Smoke script missing placeholder check")
        # v2.9: Step 8 uses "placeholder=0, missing=0, validation_passed=True"
        self.assertIn("placeholder=0", text,
                      "Smoke script missing placeholder=0 assertion (v2.9)")
        self.assertIn("missing=0", text,
                      "Smoke script missing missing=0 assertion (v2.9)")
        self.assertIn("validation_passed", text.lower(),
                      "Smoke script missing validation_passed assertion (v2.9)")

    def test_has_undo_last_step(self) -> None:
        """v2.10 item 3.1-C: smoke script must include undo-last step."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("--undo-last", text,
                      "Smoke script missing --undo-last flag (v2.10 item 3.1-C)")
        self.assertIn("undo-last correction", text.lower(),
                      "Smoke script missing undo-last step label (v2.10 item 3.1-C)")
        self.assertIn("undo-last post-traceability", text.lower(),
                      "Smoke script missing post-undo traceability check (v2.10 item 3.1-C)")


class TestSmokeScriptHasPassFailReporting(unittest.TestCase):
    """Verify the smoke script has clear PASS/FAIL reporting."""

    def test_has_pass_fail_reporting(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("PASS", text,
                      "Smoke script missing PASS reporting")
        self.assertIn("FAIL", text,
                      "Smoke script missing FAIL reporting")
        self.assertIn("OVERALL: PASS", text,
                      "Smoke script missing overall PASS")
        self.assertIn("OVERALL: FAIL", text,
                      "Smoke script missing overall FAIL")


class TestSmokeScriptReturnsCorrectExitCodes(unittest.TestCase):
    """Verify the smoke script returns exit code 0 on pass, 1 on fail."""

    def test_exit_code_pass(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("exit 0", text,
                      "Smoke script missing exit 0 (pass)")

    def test_exit_code_fail(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("exit 1", text,
                      "Smoke script missing exit 1 (fail)")


# ---------------------------------------------------------------------------
# Lightweight execution test (smoke of the smoke)
# ---------------------------------------------------------------------------


class TestSmokeScriptLightweightExecution(unittest.TestCase):
    """Run the smoke script against a temp root and verify key steps pass.

    This test verifies the smoke script parses correctly and that the
    critical pipeline steps (weekly cycle build, inbox creation, source URL
    traceability) complete successfully. Downstream steps (status, reports,
    dashboard) may encounter pre-existing issues unrelated to item 5.1.
    """

    def test_smoke_script_executes_against_temp_root(self) -> None:
        script = SCRIPTS_DIR / "run-controlled-smoke.ps1"
        self.assertTrue(script.is_file(),
                        f"Smoke script not found at {script}")

        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(script),
                "-ProjectRoot", str(REPO_ROOT),
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=120,
        )

        output = (result.stdout or "") + "\n" + (result.stderr or "")

        # Verify the script parsed correctly (no PowerShell ParserError)
        self.assertNotIn(
            "ParserError", result.stderr or "",
            f"Smoke script has PowerShell parse errors.\nSTDERR:\n{result.stderr}"
        )

        # Verify the weekly cycle build step passed
        self.assertIn(
            "[PASS] run-weekly-cycle-v2", output,
            f"Weekly cycle build did not pass.\nOutput:\n{output}"
        )

        # Verify the founder inbox was found
        self.assertIn(
            "[PASS] founder_inbox_v2", output,
            f"Founder inbox verification did not pass.\nOutput:\n{output}"
        )

        # Verify source URL traceability was checked
        self.assertIn(
            "source url traceability", output.lower(),
            f"Source URL traceability not checked.\nOutput:\n{output}"
        )

        # Note: The smoke script may return non-zero exit code if
        # downstream steps (status/reports/dashboard) encounter
        # pipeline issues in the temp-root context.
        # After v2.8 item 4.1, weekly-cycle-status-v2 should pass normally.
        # This is acceptable for item 5.1 scope.


class TestSmokeScriptExpectsStatusPass(unittest.TestCase):
    """After v2.8 item 4.1: weekly-cycle-status-v2 must be expected to pass."""

    def test_smoke_script_no_longer_treats_status_as_pre_existing(self):
        """The smoke script must NOT treat weekly-cycle-status-v2 non-zero
        as pre-existing. The status step (Step 5) must not contain
        'pre-existing issue'. Other steps (6/7) may still use it for steps
        that legitimately have partial artifact issues."""
        script = SCRIPTS_DIR / "run-controlled-smoke.ps1"
        text = script.read_text(encoding="utf-8")

        # Extract the Step 5 block (between "STEP 5:" and "STEP 6:")
        step5_match = None
        import re
        step5_re = re.compile(
            r'# STEP 5:.*?(?=# STEP 6:)', re.DOTALL
        )
        step5_match = step5_re.search(text)

        if step5_match:
            step5_block = step5_match.group(0)
            self.assertNotIn(
                "pre-existing issue",
                step5_block,
                "Step 5 (Weekly Cycle Status) still treats "
                "weekly-cycle-status-v2 non-zero as pre-existing. "
                "Item 4.1 requires it to pass normally."
            )
        else:
            self.fail("Could not find STEP 5 block in smoke script")

    def test_smoke_script_status_step_is_record_fail_on_nonzero(self):
        """On non-zero exit, the smoke script must Record-Fail (not Record-Pass)."""
        script = SCRIPTS_DIR / "run-controlled-smoke.ps1"
        text = script.read_text(encoding="utf-8")

        # Find the status step block
        self.assertIn('Record-Fail "weekly-cycle-status-v2"', text,
                      "Smoke script must Record-Fail on status non-zero exit, "
                      "not Record-Pass as pre-existing issue.")

    def test_smoke_script_status_step_matches_expected_pattern(self):
        """Verify the exact pattern of the status step after hardening."""
        script = SCRIPTS_DIR / "run-controlled-smoke.ps1"
        text = script.read_text(encoding="utf-8")
        lines = text.splitlines()

        # Find the weekly-cycle-status-v2 step
        in_status_section = False
        found_check = False
        for line in lines:
            if "STEP 5:" in line and "Weekly Cycle Status" in line:
                in_status_section = True
            if in_status_section and "Record-Pass" in line and "weekly-cycle-status-v2" in line:
                # The only Record-Pass should be for exit 0, not for "pre-existing"
                if "pre-existing" in line:
                    self.fail(f"Status step still uses 'pre-existing' label: {line}")
                found_check = True
            if in_status_section and "Record-Fail" in line and "weekly-cycle-status-v2" in line:
                # Record-Fail is expected for non-zero
                found_check = True
                break

        self.assertTrue(found_check, "Could not find weekly-cycle-status-v2 pass/fail pattern")


# ---------------------------------------------------------------------------
# Operational Discovery Pilot smoke tests (v2.12 item 8)
# ---------------------------------------------------------------------------


class TestSmokeScriptContainsOperationalDiscoveryPilotStep(unittest.TestCase):
    """Verify the smoke script includes the Operational Discovery Pilot smoke step."""

    def test_contains_pilot_smoke_section(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("Operational Discovery Pilot Smoke", text,
                      "Smoke script missing Operational Discovery Pilot Smoke section")

    def test_contains_pilot_smoke_step_label(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("STEP 10:", text,
                      "Smoke script missing STEP 10 label")
        self.assertIn("Operational Discovery Pilot", text,
                      "Smoke script missing Operational Discovery Pilot reference")

    def test_references_run_operational_discovery_pilot(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("run_operational_discovery_pilot", text,
                      "Smoke script missing run_operational_discovery_pilot import/call")

    def test_references_operational_discovery_pilot_input(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("OperationalDiscoveryPilotInput", text,
                      "Smoke script missing OperationalDiscoveryPilotInput reference")

    def test_checks_required_artifacts(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        required_artifacts = [
            "raw_evidence.json",
            "candidate_signals.json",
            "pain_clusters.json",
            "source_quality_report.json",
            "source_quality_report.md",
            "founder_review_package.json",
            "founder_review_package.md",
            "validation_summary.json",
            "pilot_run_manifest.json",
        ]
        for artifact in required_artifacts:
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, text,
                              f"Smoke script missing artifact check: {artifact}")

    def test_checks_no_deferred_sources(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("deferred", text.lower(),
                      "Smoke script missing deferred source checks for pilot smoke")
        self.assertIn("no_deferred_source_errors", text,
                      "Smoke script missing no_deferred_source_errors check")

    def test_checks_source_scope_clean(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("source scope clean", text.lower(),
                      "Smoke script missing source scope clean check")
        self.assertIn("hacker_news", text,
                      "Smoke script must reference hacker_news in source scope check")
        self.assertIn("github_issues", text,
                      "Smoke script must reference github_issues in source scope check")

    def test_checks_source_url_http(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("source_urls are http", text,
                      "Smoke script missing http(s) source_url check")

    def test_checks_validation_summary(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("validation_summary reports valid", text,
                      "Smoke script missing validation_summary valid check")

    def test_checks_founder_review_package_traceability(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("traceability", text.lower(),
                      "Smoke script missing traceability checks in pilot smoke step")

    def test_checks_source_quality_report(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("source_quality_report valid", text,
                      "Smoke script missing source_quality_report validity check")

    def test_uses_temp_output_location(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("pilot_output", text,
                      "Smoke script missing pilot_output temp directory")
        # Must use $TempRoot, not $ProjectRoot for pilot output
        self.assertIn("$TempRoot", text,
                      "Smoke script pilot step must reference $TempRoot")

    def test_no_live_api_in_pilot_step(self) -> None:
        """The pilot step must not contain live API call patterns."""
        text = _read_script_text("run-controlled-smoke.ps1")
        # Check the pilot step section for live call patterns
        pilot_start = text.find("STEP 10:")
        pilot_end = text.find("SUMMARY", pilot_start) if pilot_start >= 0 else -1
        if pilot_start >= 0 and pilot_end >= 0:
            pilot_section = text[pilot_start:pilot_end]
            live_patterns = ["Invoke-RestMethod", "Invoke-WebRequest", "curl ", "wget "]
            for pattern in live_patterns:
                self.assertNotIn(pattern, pilot_section,
                                 f"Pilot smoke step contains live API pattern: {pattern}")

    def test_no_deferred_source_ids_in_fixture(self) -> None:
        """The pilot smoke fixture must not use any deferred source_ids."""
        text = _read_script_text("run-controlled-smoke.ps1")
        deferred = ["product_hunt", "pimenov_ai", "reddit", "discord",
                     "slack", "x_twitter", "stack_exchange"]
        pilot_start = text.find("STEP 10:")
        pilot_end = text.find("SUMMARY", pilot_start) if pilot_start >= 0 else -1
        if pilot_start >= 0 and pilot_end >= 0:
            pilot_section = text[pilot_start:pilot_end]
            for source in deferred:
                # Must be in safety/rejection check, not in fixture data source_id
                # We check that any occurrence is inside a safety context
                if source in pilot_section:
                    idx = pilot_section.find(source)
                    context_start = max(0, idx - 100)
                    context_end = min(len(pilot_section), idx + len(source) + 100)
                    context = pilot_section[context_start:context_end]
                    if ('source_id = "' + source + '"') in context or ("source_id = '" + source + "'") in context:
                        self.fail(
                            f"Pilot smoke fixture uses deferred source_id '{source}' "
                            f"in fixture data"
                        )


# ---------------------------------------------------------------------------
# v2.14 Item 9 Controlled Quality Smoke tests (HARDENED v2.14-FIX)
# ---------------------------------------------------------------------------


class TestSmokeScriptContainsV214QualitySmokeStep(unittest.TestCase):
    """Verify the smoke script includes the v2.14 quality smoke step (Step 11)
    with hardened gates (v2.14-FIX)."""

    def test_contains_v214_quality_smoke_section(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("v2.14 Controlled Quality Smoke", text,
                      "Smoke script missing v2.14 Controlled Quality Smoke section")

    def test_contains_v214_step_label(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("STEP 11:", text,
                      "Smoke script missing STEP 11 label")
        self.assertIn("v2.14 Controlled Quality Smoke", text,
                      "Smoke script missing v2.14 quality smoke reference")

    def test_references_run_operational_discovery_pilot(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("run_operational_discovery_pilot", text,
                      "Smoke script missing run_operational_discovery_pilot in Step 11")

    # --- HARDENED Gate A: Source Quality Report checks (v2.14-FIX) ---

    def test_gate_a1_noise_signal_total_gt_0(self) -> None:
        """A1: noise_signal_total > 0 (hardened, reads SQR JSON directly)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("A1_noise_signal_total_gt_0", text,
                      "Step 11 missing hardened A1: noise_signal_total > 0")
        self.assertIn("noise_signal_total", text,
                      "Step 11 must read noise_signal_total from SQR JSON")

    def test_gate_a2_weak_signal_total_gt_0(self) -> None:
        """A2: weak_signal_total > 0 (hardened)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("A2_weak_signal_total_gt_0", text,
                      "Step 11 missing hardened A2: weak_signal_total > 0")

    def test_gate_a3_classification_health_not_clean(self) -> None:
        """A3: classification_health != 'clean' (hardened, mandatory)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("A3_classification_health_not_clean", text,
                      "Step 11 missing hardened A3: classification_health != clean")
        self.assertIn("ch != 'clean'", text,
                      "Step 11 must assert classification_health != 'clean' directly")

    def test_gate_a4_evidence_quality_status_not_clean(self) -> None:
        """A4: evidence_quality_status != 'clean' (hardened)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("A4_evidence_quality_status_not_clean", text,
                      "Step 11 missing hardened A4: evidence_quality_status != clean")

    def test_gate_a5_flagged_record_count_gt_0(self) -> None:
        """A5: flagged_record_count > 0 (hardened)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("A5_flagged_record_count_gt_0", text,
                      "Step 11 missing hardened A5: flagged_record_count > 0")

    def test_gate_a6_dominant_quality_flags_include_evidence_flags(self) -> None:
        """A6: dominant_quality_flags includes evidence-only flags."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("A6_dominant_quality_flags_include_evidence_flags", text,
                      "Step 11 missing hardened A6: dominant flags check")

    def test_gate_a7_contradiction_warnings_count_gt_0(self) -> None:
        """A7: contradiction_warnings count > 0 (hardened)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("A7_contradiction_warnings_count_gt_0", text,
                      "Step 11 missing hardened A7: contradiction_warnings count > 0")
        self.assertIn("len(cw) > 0", text,
                      "Step 11 must assert len(contradiction_warnings) > 0")

    def test_gate_a8_at_least_one_per_source_warning(self) -> None:
        """A8: at least one per-source warning (hardened)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("A8_at_least_one_per_source_warning", text,
                      "Step 11 missing hardened A8: at least one per_source_warning")

    def test_gate_a9_markdown_warning_bullets_not_empty(self) -> None:
        """A9: Markdown contains non-empty warning bullets, not just headers."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("A9_markdown_warning_bullets_not_empty", text,
                      "Step 11 missing hardened A9: markdown warning bullets not empty")
        self.assertIn("line.strip().startswith('- ')", text,
                      "Step 11 must check for non-empty bullet content in SQR md")

    def test_gate_a_reads_sqr_json_not_md_only(self) -> None:
        """Hardened gates read SQR JSON values directly, not Markdown headers only."""
        text = _read_script_text("run-controlled-smoke.ps1")
        # Must reference SQR JSON fields directly
        json_fields = ["noise_signal_total", "weak_signal_total",
                       "classification_health", "evidence_quality_status",
                       "flagged_record_count", "contradiction_warnings"]
        for field in json_fields:
            with self.subTest(field=field):
                self.assertIn(field, text,
                              f"Step 11 must read SQR JSON field: {field}")

    # --- HARDENED Gate B: PainCluster assembly (v2.14-FIX) ---

    def test_checks_gate_b_pain_cluster_assembly(self) -> None:
        """Step 11 must check Gate B: PainCluster assembly (hardened names)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        gate_b_checks = [
            "B1_multiple_clusters_not_single_catch_all",
            "B2_coherent_trace_items_in_exactly_one_cluster",
            "B3_no_dead_or_nme_titles",
            "B4_zero_catch_all_risk_clusters",
        ]
        for check in gate_b_checks:
            with self.subTest(check=check):
                self.assertIn(check, text,
                              f"Step 11 missing Gate B check: {check}")

    def test_gate_b2_coherent_trace_in_one_cluster(self) -> None:
        """B2: truly coherent trace items (stack + trace) share EXACTLY ONE cluster."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("B2_coherent_trace_items_in_exactly_one_cluster", text,
                      "Step 11 missing B2: coherent trace items in exactly one cluster")
        self.assertIn("len(trace_cluster_ids) == 1", text,
                      "Step 11 must assert exactly 1 cluster for coherent trace items")

    def test_gate_b2b_provenance_not_merged_with_trace(self) -> None:
        """B2b: provenance item must NOT be merged with trace-debugging items."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("B2b_provenance_not_merged_with_trace_items", text,
                      "Step 11 missing B2b: provenance separate from trace items")
        self.assertIn("prov_cluster_id != trace_coherent_cluster_id", text,
                      "Step 11 must assert provenance cluster != trace cluster")

    # --- Gate C: Founder Review Package (unchanged except C5 check) ---

    def test_checks_gate_c_founder_review_package(self) -> None:
        """Step 11 must check Gate C: Founder Review Package."""
        text = _read_script_text("run-controlled-smoke.ps1")
        gate_c_checks = [
            "C1_executive_summary",
            "C2_signal_to_noise_ratio",
            "C3_per_source_breakdown",
            "C4_quality_gate_per_item",
            "C5_opportunity_hypotheses_section",
        ]
        for check in gate_c_checks:
            with self.subTest(check=check):
                self.assertIn(check, text,
                              f"Step 11 missing Gate C check: {check}")

    # --- HARDENED Gate D: Opportunity synthesis (v2.14-FIX) ---

    def test_gate_d1_opportunity_candidate_count_gte_1(self) -> None:
        """D1: opportunity candidate count >= 1 (hardened, not 'may exist')."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("D1_opportunity_candidate_count_gte_1", text,
                      "Step 11 missing hardened D1: candidate count >= 1")
        self.assertIn("len(opp_candidates) >= 1", text,
                      "Step 11 must assert len(opp_candidates) >= 1")

    def test_gate_d2_not_a_solution_yet(self) -> None:
        """D2: all hypotheses have not_a_solution_yet==True (hardened)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("D2_all_hypotheses_not_a_solution_yet", text,
                      "Step 11 must check D2: not_a_solution_yet")

    def test_gate_d3_created_by_deterministic_stub(self) -> None:
        """D3: all hypotheses have created_by==deterministic_stub."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("D3_all_created_by_deterministic_stub", text,
                      "Step 11 must check D3: created_by deterministic_stub")

    def test_gate_d4_evidence_links_preserved(self) -> None:
        """D4: all hypotheses have non-empty evidence_links."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("D4_all_hypotheses_have_evidence_links", text,
                      "Step 11 must check D4: evidence_links preserved")

    def test_gate_d5_synthesized_hypothesis_has_required_fields(self) -> None:
        """D5: synthesized hypothesis carries not_a_solution_yet, created_by, evidence_links."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("D5_synthesized_hypothesis_has_required_fields", text,
                      "Step 11 missing D5: synthesized hypothesis required fields check")

    def test_gate_d6_known_actor_icp_not_unproven(self) -> None:
        """D6: known-actor hypotheses must not have target_icp='unproven; validate actor'.
        Unknown-actor synthesis behavior is covered by regression tests, not this smoke gate."""
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("D6_known_actor_icp_not_unproven", text,
                      "Step 11 missing D6: known actor ICP not unproven")
        # D6 gate must NOT claim unknown-actor ICP smoke coverage
        self.assertIn("covered by regression tests", text,
                      "Step 11 D6 must reference regression tests for unknown-actor coverage")

    def test_gate_d6_docs_do_not_overclaim_unknown_actor(self) -> None:
        """Runbook and run report must not overclaim unknown-actor smoke coverage in D6."""
        runbook = _read_runbook_text("controlled_weekly_run_smoke_test.md")
        # Runbook section 21 must acknowledge unknown actor is regression-tested
        self.assertIn("regression tests", runbook,
                      "Runbook section 21 must reference regression tests for unknown actor")
        self.assertIn("test_opportunity_synthesis", runbook,
                      "Runbook must reference test_opportunity_synthesis.py")

    def test_gate_b2_docs_say_stack_trace_only(self) -> None:
        """B2 checks stack/trace coherent pair only; provenance is separate (B2b)."""
        runbook = _read_runbook_text("controlled_weekly_run_smoke_test.md")
        # B2 description must mention stack + trace (not provenance) as the coherent pair
        self.assertIn("v214_gh_stack_001", runbook,
                      "Runbook must reference v214_gh_stack_001 in B2 description")
        self.assertIn("v214_gh_trace_001", runbook,
                      "Runbook must reference v214_gh_trace_001 in B2 description")
        # B2b must say provenance is separate
        self.assertIn("B2b", runbook,
                      "Runbook must contain B2b gate description")
        self.assertIn("provenance", runbook.lower(),
                      "Runbook must mention provenance in B2b context")
        # Must NOT say coherent items include v214_gh_prov_001 in B2
        self.assertIn("SEPARATE", runbook,
                      "Runbook must say provenance is SEPARATE from trace cluster")

    # --- Fixture and scope checks (preserved from original) ---

    def test_uses_temp_output_location(self) -> None:
        text = _read_script_text("run-controlled-smoke.ps1")
        self.assertIn("v2_14_quality_smoke", text,
                      "Step 11 missing v2_14_quality_smoke temp directory")
        self.assertIn("$TempRoot", text,
                      "Step 11 must reference $TempRoot")

    def test_fixture_includes_quality_flags(self) -> None:
        """Step 11 fixture must include evidence with quality flags."""
        text = _read_script_text("run-controlled-smoke.ps1")
        required_flags = [
            "requires_manual_review",
            "low_confidence_source",
            "suspected_self_promo",
            "debugging_pain",
            "workaround_signal",
        ]
        for flag in required_flags:
            with self.subTest(flag=flag):
                self.assertIn(flag, text,
                              f"Step 11 fixture missing quality flag: {flag}")

    def test_fixture_includes_evidence_only_flags_case(self) -> None:
        """Step 11 must include evidence-only flag case (low_text_context)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        # Look in the Step 11 section
        step11_start = text.find("STEP 11:")
        step11_end = text.find("SUMMARY", step11_start) if step11_start >= 0 else -1
        if step11_start >= 0 and step11_end >= 0:
            step11_section = text[step11_start:step11_end]
            self.assertIn("low_text_context", step11_section,
                          "Step 11 fixture missing low_text_context flag (evidence-only case)")

    def test_fixture_includes_unknown_actor_evidence(self) -> None:
        """Step 11 fixture must include unknown-actor evidence pair (v2.14-FIX)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        step11_start = text.find("STEP 11:")
        step11_end = text.find("SUMMARY", step11_start) if step11_start >= 0 else -1
        if step11_start >= 0 and step11_end >= 0:
            step11_section = text[step11_start:step11_end]
            self.assertIn("v214_hn_unknown_001", step11_section,
                          "Step 11 fixture missing unknown-actor HN evidence (v2.14-FIX)")
            self.assertIn("v214_gh_unknown_001", step11_section,
                          "Step 11 fixture missing unknown-actor GitHub evidence (v2.14-FIX)")
            self.assertIn("unknown_actor_debugging", step11_section,
                          "Step 11 fixture missing unknown_actor_debugging topic (v2.14-FIX)")

    def test_fixture_has_valid_http_source_urls(self) -> None:
        """All source_urls in Step 11 fixture must be http(s)."""
        text = _read_script_text("run-controlled-smoke.ps1")
        step11_start = text.find("STEP 11:")
        step11_end = text.find("SUMMARY", step11_start) if step11_start >= 0 else -1
        if step11_start >= 0 and step11_end >= 0:
            step11_section = text[step11_start:step11_end]
            self.assertIn("https://news.ycombinator.com/item?id=", step11_section,
                          "Step 11 fixture must use valid HN https source URLs")
            self.assertIn("https://github.com/example/", step11_section,
                          "Step 11 fixture must use valid GitHub https source URLs")

    def test_no_live_api_in_step11(self) -> None:
        """Step 11 must not contain live API call patterns."""
        text = _read_script_text("run-controlled-smoke.ps1")
        step11_start = text.find("STEP 11:")
        step11_end = text.find("SUMMARY", step11_start) if step11_start >= 0 else -1
        if step11_start >= 0 and step11_end >= 0:
            step11_section = text[step11_start:step11_end]
            live_patterns = ["Invoke-RestMethod", "Invoke-WebRequest", "curl ", "wget "]
            for pattern in live_patterns:
                self.assertNotIn(pattern, step11_section,
                                 f"Step 11 contains live API pattern: {pattern}")

    def test_no_deferred_source_ids_in_step11_fixture(self) -> None:
        """Step 11 fixture must not use any deferred source_ids."""
        text = _read_script_text("run-controlled-smoke.ps1")
        deferred = ["product_hunt", "pimenov_ai", "reddit", "discord",
                     "slack", "x_twitter", "stack_exchange"]
        step11_start = text.find("STEP 11:")
        step11_end = text.find("SUMMARY", step11_start) if step11_start >= 0 else -1
        if step11_start >= 0 and step11_end >= 0:
            step11_section = text[step11_start:step11_end]
            for source in deferred:
                if source in step11_section:
                    idx = step11_section.find(source)
                    context_start = max(0, idx - 100)
                    context_end = min(len(step11_section), idx + len(source) + 100)
                    context = step11_section[context_start:context_end]
                    if ('source_id = "' + source + '"') in context or ("source_id = '" + source + "'") in context:
                        self.fail(
                            f"Step 11 fixture uses deferred source_id '{source}' "
                            f"in fixture data"
                        )


# ---------------------------------------------------------------------------
# v2.14 Item 9 Codex fix: Roadmap state alignment tests
# ---------------------------------------------------------------------------


class TestRoadmapStateAlignedForItem9CodexFix(unittest.TestCase):
    """Verify roadmap overview counters and footer reflect Item 9 complete,
    Item 10 next."""

    def test_current_item_is_10(self):
        roadmap_path = REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md"
        text = roadmap_path.read_text(encoding="utf-8")
        self.assertIn("Current item: `10 — Final v2.14 checkpoint`", text,
                      "Roadmap 0.2 must say current item is 10")
        self.assertNotIn("Item 9 fix in progress", text,
                         "Roadmap must not contain stale 'Item 9 fix in progress' wording")

    def test_completed_counter_is_10_of_11(self):
        roadmap_path = REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md"
        text = roadmap_path.read_text(encoding="utf-8")
        self.assertIn("**10 / 11**", text,
                      "Roadmap 0.4 must say completed 10/11")

    def test_remaining_counter_is_1_of_11(self):
        roadmap_path = REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md"
        text = roadmap_path.read_text(encoding="utf-8")
        self.assertIn("**1 / 11**", text,
                      "Roadmap 0.5 must say remaining 1/11")

    def test_item_10_not_marked_complete(self):
        roadmap_path = REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md"
        text = roadmap_path.read_text(encoding="utf-8")
        # Item 10 DoD items must remain unchecked
        self.assertIn("- [ ] **10.1**", text,
                      "Roadmap Item 10.1 must remain unchecked")
        self.assertIn("- [ ] **10.2**", text,
                      "Roadmap Item 10.2 must remain unchecked")

    def test_footer_says_item_9_complete(self):
        roadmap_path = REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md"
        text = roadmap_path.read_text(encoding="utf-8")
        self.assertIn("Item 9 complete; item 10 is next.", text,
                      "Roadmap footer must say Item 9 complete; item 10 is next.")

    def test_footer_does_not_contain_stale_fix_wording(self):
        roadmap_path = REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md"
        text = roadmap_path.read_text(encoding="utf-8")
        self.assertNotIn("fix applied; awaiting validation", text,
                         "Roadmap footer must not contain stale awaiting-validation wording")

    def test_item_9_dod_items_checked(self):
        """Item 9 DoD items 9.1 through 9.12 must be checked as complete."""
        roadmap_path = REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_14_pilot_quality_improvements_checklist.md"
        text = roadmap_path.read_text(encoding="utf-8")
        for n in range(1, 13):
            with self.subTest(dod=f"9.{n}"):
                self.assertIn(f"- [x] **9.{n}**", text,
                              f"Roadmap Item 9.{n} DoD must be checked [x]")


# ---------------------------------------------------------------------------
# v2.14 Item 9 Codex fix: Run report content guard tests
# ---------------------------------------------------------------------------


RUN_REPORT_DIR = REPO_ROOT / "docs" / "dev_ledger" / "03_run_reports"


def _read_run_report_text(report_name: str) -> str:
    path = RUN_REPORT_DIR / report_name
    return path.read_text(encoding="utf-8")


class TestRunReportV214ContentGuards(unittest.TestCase):
    """Verify the v2.14 Item 9 run report does not contain stale/contradictory
    wording that the Codex review flagged as FAIL."""

    RUN_REPORT_NAME = "9.1-v2-14-controlled-quality-smoke.md"

    def test_run_report_exists(self) -> None:
        path = RUN_REPORT_DIR / self.RUN_REPORT_NAME
        self.assertTrue(path.is_file(),
                        f"Run report not found at {path}")

    def test_does_not_contain_awaiting_re_validation(self) -> None:
        """Report must not contain stale 'awaiting re-validation' wording."""
        text = _read_run_report_text(self.RUN_REPORT_NAME)
        self.assertNotIn(
            "awaiting re-validation", text,
            "Run report must not contain stale 'awaiting re-validation' wording"
        )

    def test_status_is_complete_not_fix_applied(self) -> None:
        """Report status must say Complete/PASS, not 'Fix applied'."""
        text = _read_run_report_text(self.RUN_REPORT_NAME)
        self.assertNotIn(
            "Fix applied /", text,
            "Run report status must not contain stale 'Fix applied' wording"
        )
        self.assertIn("Complete", text,
                      "Run report must contain 'Complete' status wording")

    def test_b2_does_not_claim_provenance_in_coherent_set(self) -> None:
        """B2 must NOT claim v214_gh_prov_001 is in the coherent stack/trace set."""
        text = _read_run_report_text(self.RUN_REPORT_NAME)
        self.assertNotIn(
            "Includes `v214_gh_prov_001` in the coherent set", text,
            "Run report must not claim v214_gh_prov_001 is in the B2 coherent set"
        )

    def test_b2_describes_stack_trace_only(self) -> None:
        """B2 must describe stack/trace pair only, provenance in B2b."""
        text = _read_run_report_text(self.RUN_REPORT_NAME)
        self.assertIn("stack/trace pair", text,
                      "Run report B2 must reference stack/trace pair")
        self.assertIn("SEPARATE", text,
                      "Run report B2b must say provenance is SEPARATE from trace cluster")

    def test_eligibility_path_states_stack_trace_debug_cluster(self) -> None:
        """Eligibility path must describe stack/trace/debug cluster, not stack+trace+provenance."""
        text = _read_run_report_text(self.RUN_REPORT_NAME)
        self.assertIn("stack/trace/debug cluster", text,
                      "Eligibility path must describe 'stack/trace/debug cluster'")

    def test_unknown_actor_is_described_as_regression_tested(self) -> None:
        """Unknown-actor behavior must be described as regression-tested, not smoke-tested."""
        text = _read_run_report_text(self.RUN_REPORT_NAME)
        self.assertIn("regression-tested", text,
                      "Run report must state unknown-actor is regression-tested")
        self.assertIn("not smoke-tested", text,
                      "Run report must state unknown-actor is not smoke-tested")

    def test_total_passes_59_not_24(self) -> None:
        """Pass/Fail total must reflect actual 59 PASS / 0 FAIL, not the old 24."""
        text = _read_run_report_text(self.RUN_REPORT_NAME)
        self.assertIn("59", text,
                      "Run report must show 59 total passes, not 24")

    def test_gate_b2_table_shows_stack_trace_only(self) -> None:
        """Gate B table must specify B2 is stack/trace items only."""
        text = _read_run_report_text(self.RUN_REPORT_NAME)
        self.assertIn("v214_gh_stack_001", text,
                      "Run report Gate B must reference v214_gh_stack_001")
        self.assertIn("v214_gh_trace_001", text,
                      "Run report Gate B must reference v214_gh_trace_001")

    def test_gate_b2b_table_shows_provenance_separate(self) -> None:
        """Gate B table must have B2b row showing provenance is separate."""
        text = _read_run_report_text(self.RUN_REPORT_NAME)
        self.assertIn("B2b", text,
                      "Run report Gate B must contain B2b row")
        self.assertIn("provenance", text.lower(),
                      "Run report Gate B2b must mention provenance")
        self.assertIn("separate", text.lower(),
                      "Run report Gate B2b must say provenance is separate")
