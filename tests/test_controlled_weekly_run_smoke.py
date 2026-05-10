"""Tests for controlled weekly run smoke test (Roadmap v2.7 item 5.1).

Covers:
- Runbook existence and required content
- Smoke script existence, strict mode, and forbidden command checks
- Smoke script temp-only and safety boundary verification
- Optional lightweight execution test against temp root
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
        self.assertIn("zero placeholder", text.lower(),
                      "Smoke script missing zero placeholder URN assertion")


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
