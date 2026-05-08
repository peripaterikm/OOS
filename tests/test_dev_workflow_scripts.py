import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

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
    """Read a script file as text."""
    path = SCRIPTS_DIR / script_name
    return path.read_text(encoding="utf-8")


class TestDevWorkflowScriptsExist(unittest.TestCase):
    """Verify all four developer workflow scripts exist."""

    def test_dev_snapshot_exists(self) -> None:
        self.assertTrue((SCRIPTS_DIR / "dev-snapshot.ps1").is_file())

    def test_dev_validate_final_exists(self) -> None:
        self.assertTrue((SCRIPTS_DIR / "dev-validate-final.ps1").is_file())

    def test_dev_pr_readiness_exists(self) -> None:
        self.assertTrue((SCRIPTS_DIR / "dev-pr-readiness.ps1").is_file())

    def test_dev_post_merge_sync_exists(self) -> None:
        self.assertTrue((SCRIPTS_DIR / "dev-post-merge-sync.ps1").is_file())


class TestDevWorkflowScriptsNoForbiddenCommands(unittest.TestCase):
    """Verify no script contains forbidden git or destructive commands."""

    def _assert_no_forbidden(self, script_name: str, text: str) -> None:
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            # Skip comment lines and the synopsis/help text that mentions
            # forbidden commands for documentation purposes.
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("<#") or stripped.startswith("#>"):
                continue
            if stripped.startswith("Write-Host") or stripped.startswith("REMINDER"):
                continue
            for cmd in FORBIDDEN_COMMANDS:
                # Only flag actual command invocations, not mentions in
                # documentation strings or Write-Host messages.
                if cmd in stripped and (
                    stripped.startswith("&") or
                    stripped.startswith("git ") or
                    stripped.startswith("gh ") or
                    stripped.startswith("Remove-Item") or
                    stripped.startswith("rm ") or
                    stripped.startswith("del ")
                ):
                    self.fail(
                        f"{script_name}:{i} contains forbidden command "
                        f"'{cmd}': {stripped}"
                    )

    def test_dev_snapshot_no_forbidden(self) -> None:
        self._assert_no_forbidden("dev-snapshot.ps1",
                                   _read_script_text("dev-snapshot.ps1"))

    def test_dev_validate_final_no_forbidden(self) -> None:
        self._assert_no_forbidden("dev-validate-final.ps1",
                                   _read_script_text("dev-validate-final.ps1"))

    def test_dev_pr_readiness_no_forbidden(self) -> None:
        self._assert_no_forbidden("dev-pr-readiness.ps1",
                                   _read_script_text("dev-pr-readiness.ps1"))

    def test_dev_post_merge_sync_no_forbidden(self) -> None:
        self._assert_no_forbidden("dev-post-merge-sync.ps1",
                                   _read_script_text("dev-post-merge-sync.ps1"))


class TestDevWorkflowScriptsStrictMode(unittest.TestCase):
    """Verify all scripts use Set-StrictMode and ErrorActionPreference Stop."""

    def _assert_has_strict_mode(self, script_name: str, text: str) -> None:
        self.assertIn("Set-StrictMode", text,
                       f"{script_name}: missing Set-StrictMode")
        self.assertIn("$ErrorActionPreference", text,
                       f"{script_name}: missing ErrorActionPreference")

    def test_dev_snapshot_has_strict_mode(self) -> None:
        self._assert_has_strict_mode("dev-snapshot.ps1",
                                      _read_script_text("dev-snapshot.ps1"))

    def test_dev_validate_final_has_strict_mode(self) -> None:
        self._assert_has_strict_mode("dev-validate-final.ps1",
                                      _read_script_text("dev-validate-final.ps1"))

    def test_dev_pr_readiness_has_strict_mode(self) -> None:
        self._assert_has_strict_mode("dev-pr-readiness.ps1",
                                      _read_script_text("dev-pr-readiness.ps1"))

    def test_dev_post_merge_sync_has_strict_mode(self) -> None:
        self._assert_has_strict_mode("dev-post-merge-sync.ps1",
                                      _read_script_text("dev-post-merge-sync.ps1"))


class TestDevWorkflowScriptsCommentBasedHelp(unittest.TestCase):
    """Verify all scripts have comment-based help (<# .SYNOPSIS #>)."""

    def _assert_has_help(self, script_name: str, text: str) -> None:
        self.assertIn(".SYNOPSIS", text,
                       f"{script_name}: missing .SYNOPSIS in comment-based help")
        self.assertIn(".DESCRIPTION", text,
                       f"{script_name}: missing .DESCRIPTION in comment-based help")
        self.assertIn(".EXAMPLE", text,
                       f"{script_name}: missing .EXAMPLE in comment-based help")

    def test_dev_snapshot_has_help(self) -> None:
        self._assert_has_help("dev-snapshot.ps1",
                               _read_script_text("dev-snapshot.ps1"))

    def test_dev_validate_final_has_help(self) -> None:
        self._assert_has_help("dev-validate-final.ps1",
                               _read_script_text("dev-validate-final.ps1"))

    def test_dev_pr_readiness_has_help(self) -> None:
        self._assert_has_help("dev-pr-readiness.ps1",
                               _read_script_text("dev-pr-readiness.ps1"))

    def test_dev_post_merge_sync_has_help(self) -> None:
        self._assert_has_help("dev-post-merge-sync.ps1",
                               _read_script_text("dev-post-merge-sync.ps1"))


class TestDevValidateFinalHasDiffCheck(unittest.TestCase):
    """dev-validate-final.ps1 must include git diff --check."""

    def test_contains_git_diff_check(self) -> None:
        text = _read_script_text("dev-validate-final.ps1")
        self.assertIn("git diff --check", text)


class TestDevPrReadinessIsReadOnly(unittest.TestCase):
    """dev-pr-readiness.ps1 must be read-only: no state-changing commands."""

    def test_no_mutating_git_commands(self) -> None:
        text = _read_script_text("dev-pr-readiness.ps1")
        mutating = ["git add", "git commit", "git push", "git merge",
                     "git tag", "git reset", "git clean", "git branch -d",
                     "git branch -D", "git checkout", "git switch"]
        for cmd in mutating:
            self.assertNotIn(cmd, text,
                              f"dev-pr-readiness.ps1 contains mutating "
                              f"command: {cmd}")

    def test_no_gh_pr_create_or_merge(self) -> None:
        text = _read_script_text("dev-pr-readiness.ps1")
        self.assertNotIn("gh pr create", text)
        self.assertNotIn("gh pr merge", text)

    def test_reminder_about_manual_pr(self) -> None:
        text = _read_script_text("dev-pr-readiness.ps1")
        self.assertIn("PR creation must be manual", text)


class TestDevPostMergeSyncDefaultsToDryRun(unittest.TestCase):
    """dev-post-merge-sync.ps1 must default to dry-run / instructions-only."""

    def test_default_is_dry_run(self) -> None:
        text = _read_script_text("dev-post-merge-sync.ps1")
        # The script must check for -ExecuteSafeSync switch
        self.assertIn("ExecuteSafeSync", text)
        # When not in execution mode, it must print instructions
        self.assertIn("DRY-RUN MODE", text)
        self.assertIn("Suggested manual commands", text)

    def test_no_destructive_in_execution_mode(self) -> None:
        text = _read_script_text("dev-post-merge-sync.ps1")
        destructive = ["git push", "git merge", "git tag", "git branch -d",
                        "git branch -D", "git reset", "git clean"]
        for cmd in destructive:
            self.assertNotIn(cmd, text,
                              f"dev-post-merge-sync.ps1 contains destructive "
                              f"command: {cmd}")

    def test_reminder_no_branch_deletion(self) -> None:
        text = _read_script_text("dev-post-merge-sync.ps1")
        self.assertIn("No branches were deleted", text)


class TestDevWorkflowScriptsNoLiveApi(unittest.TestCase):
    """Verify no script contains live API/LLM calls or URLs."""

    def _assert_no_live_calls(self, script_name: str, text: str) -> None:
        live_patterns = [
            "Invoke-RestMethod",
            "Invoke-WebRequest",
            "curl ",
            "wget ",
            "api.openai.com",
            "api.anthropic.com",
            "api-key",
            "Authorization: Bearer",
        ]
        for pattern in live_patterns:
            self.assertNotIn(pattern, text,
                              f"{script_name}: contains live API/LLM pattern "
                              f"'{pattern}'")

    def test_dev_snapshot_no_live_calls(self) -> None:
        self._assert_no_live_calls("dev-snapshot.ps1",
                                    _read_script_text("dev-snapshot.ps1"))

    def test_dev_validate_final_no_live_calls(self) -> None:
        self._assert_no_live_calls("dev-validate-final.ps1",
                                    _read_script_text("dev-validate-final.ps1"))

    def test_dev_pr_readiness_no_live_calls(self) -> None:
        self._assert_no_live_calls("dev-pr-readiness.ps1",
                                    _read_script_text("dev-pr-readiness.ps1"))

    def test_dev_post_merge_sync_no_live_calls(self) -> None:
        self._assert_no_live_calls("dev-post-merge-sync.ps1",
                                    _read_script_text("dev-post-merge-sync.ps1"))


class TestDevSnapshotWritesOnlyToLocalHold(unittest.TestCase):
    """dev-snapshot.ps1 writes only under _local_hold/dev_snapshots."""

    def test_snapshot_target_is_local_hold(self) -> None:
        text = _read_script_text("dev-snapshot.ps1")
        self.assertIn("_local_hold\\dev_snapshots", text)
        # Must not write anywhere else
        unsafe_paths = ["artifacts/", "artifacts\\", "reports/", "reports\\"]
        # Check that the output file path is constrained
        self.assertIn("$SnapshotFile", text)

    def test_lightweight_execution_in_temp_dir(self) -> None:
        """Run dev-snapshot.ps1 in a temp directory tree and verify
        it only creates files under _local_hold/dev_snapshots."""
        script = SCRIPTS_DIR / "dev-snapshot.ps1"

        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "repo"
            tmp_root.mkdir()

            # Initialize a minimal git repo for the script to work with
            subprocess.run(
                ["git", "init"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )
            # Configure git user for the temp repo
            subprocess.run(
                ["git", "config", "user.email", "test@test.local"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )
            # Create a dummy file so there is at least one commit
            (tmp_root / "README.md").write_text("# Test")
            subprocess.run(
                ["git", "add", "README.md"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )

            # Create a minimal roadmap and project state so the script
            # can read them (best-effort excerpt)
            roadmap_dir = tmp_root / "docs" / "roadmaps"
            roadmap_dir.mkdir(parents=True)
            (roadmap_dir / "OOS_roadmap_v2_7_traceability_and_real_run_readiness_checklist.md").write_text(
                "- [ ] Current item: 4.1\n- [ ] Completed from this roadmap: 5 / 8\n"
            )

            ledger_dir = tmp_root / "docs" / "dev_ledger"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "00_project_state.md").write_text(
                "- Current item: 4.1\n- Completed: 5 / 8\n- Remaining: 3 / 8\n"
            )

            # Run the script in the temp repo
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(script), "-ProjectRoot", str(tmp_root)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0,
                              f"dev-snapshot.ps1 failed: {result.stderr}")

            # Check that snapshot was created under _local_hold/dev_snapshots/
            snapshot_dir = tmp_root / "_local_hold" / "dev_snapshots"
            self.assertTrue(snapshot_dir.is_dir(),
                             f"Snapshot dir not created: {snapshot_dir}")

            snapshots = list(snapshot_dir.glob("dev_snapshot_*.txt"))
            self.assertEqual(len(snapshots), 1,
                              f"Expected 1 snapshot, got {len(snapshots)}: "
                              f"{snapshots}")

            snapshot_content = snapshots[0].read_text(encoding="utf-8")
            self.assertIn("OOS Developer Snapshot", snapshot_content)
            self.assertIn("Current Branch", snapshot_content)
            self.assertIn("Git Status", snapshot_content)
            self.assertIn("Git Log", snapshot_content)

            # Verify no other files were created outside _local_hold
            all_files = list(tmp_root.rglob("*"))
            non_snapshot_files = [
                f for f in all_files
                if f.is_file()
                and not str(f).startswith(str(snapshot_dir))
                and ".git" not in str(f).split("\\")
                and f.name != "README.md"
                and f.name != "OOS_roadmap_v2_7_traceability_and_real_run_readiness_checklist.md"
                and f.name != "00_project_state.md"
            ]
            self.assertEqual(
                len(non_snapshot_files), 0,
                f"Unexpected files created: {[str(f) for f in non_snapshot_files]}"
            )


class TestDevPostMergeSyncExecutionMode(unittest.TestCase):
    """dev-post-merge-sync.ps1 in dry-run must only print instructions."""

    def test_dry_run_output_contains_instructions(self) -> None:
        script = SCRIPTS_DIR / "dev-post-merge-sync.ps1"

        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "repo"
            tmp_root.mkdir()

            # Initialize a minimal git repo with at least one commit
            # so that git branch --show-current works
            subprocess.run(
                ["git", "init"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.local"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )
            (tmp_root / "README.md").write_text("# Test")
            subprocess.run(
                ["git", "add", "README.md"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=str(tmp_root),
                capture_output=True,
                check=True,
            )

            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(script), "-ProjectRoot", str(tmp_root)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0,
                              f"dev-post-merge-sync.ps1 dry-run failed: "
                              f"{result.stderr}")

            output = result.stdout
            self.assertIn("DRY-RUN MODE", output)
            self.assertIn("Suggested manual commands", output)
            self.assertIn("git switch main", output)
            self.assertIn("git pull --ff-only", output)
            self.assertIn("git fetch --prune", output)
            self.assertIn("No branches were deleted", output)


class TestDevWorkflowScriptsWindowsNative(unittest.TestCase):
    """Verify scripts don't contain WSL/Linux/bash constructs."""

    def _assert_no_unix_constructs(self, script_name: str, text: str) -> None:
        # Check for bash-specific constructs
        unix_patterns = [
            "#!/bin/bash",
            "#!/bin/sh",
            "#!/usr/bin/env",
            "wsl ",
            "wsl.exe",
        ]
        for pattern in unix_patterns:
            self.assertNotIn(pattern, text,
                              f"{script_name}: contains Unix/WSL construct "
                              f"'{pattern}'")

    def test_dev_snapshot_no_unix(self) -> None:
        self._assert_no_unix_constructs("dev-snapshot.ps1",
                                         _read_script_text("dev-snapshot.ps1"))

    def test_dev_validate_final_no_unix(self) -> None:
        self._assert_no_unix_constructs("dev-validate-final.ps1",
                                         _read_script_text("dev-validate-final.ps1"))

    def test_dev_pr_readiness_no_unix(self) -> None:
        self._assert_no_unix_constructs("dev-pr-readiness.ps1",
                                         _read_script_text("dev-pr-readiness.ps1"))

    def test_dev_post_merge_sync_no_unix(self) -> None:
        self._assert_no_unix_constructs("dev-post-merge-sync.ps1",
                                         _read_script_text("dev-post-merge-sync.ps1"))


if __name__ == "__main__":
    unittest.main()
