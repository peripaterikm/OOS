import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


class TestDevGitCheckNullFileGuard(unittest.TestCase):
    """dev-git-check.ps1 detects and warns about $null file."""

    def test_warns_about_null_file_when_present(self) -> None:
        """When a literal $null file exists, script prints warning."""
        script = SCRIPTS_DIR / "dev-git-check.ps1"
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "repo"
            tmp_root.mkdir()
            subprocess.run(["git", "init"], cwd=str(tmp_root), capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=str(tmp_root), capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_root), capture_output=True, check=True)
            (tmp_root / "README.md").write_text("# Test")
            subprocess.run(["git", "add", "README.md"], cwd=str(tmp_root), capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_root), capture_output=True, check=True)
            # Create literal $null file
            (tmp_root / "$null").write_text("")
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(script), "-ProjectRoot", str(tmp_root)],
                capture_output=True, text=True)
            self.assertIn("WARNING: File named", result.stdout)

    def test_null_file_is_detected_not_created_by_script(self) -> None:
        """Script must NOT create a $null file."""
        script = SCRIPTS_DIR / "dev-git-check.ps1"
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "repo"
            tmp_root.mkdir()
            subprocess.run(["git", "init"], cwd=str(tmp_root), capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=str(tmp_root), capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_root), capture_output=True, check=True)
            (tmp_root / "README.md").write_text("# Test")
            subprocess.run(["git", "add", "README.md"], cwd=str(tmp_root), capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_root), capture_output=True, check=True)
            null_path = tmp_root / "$null"
            self.assertFalse(null_path.exists(), "$null must NOT exist before script runs")
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(script), "-ProjectRoot", str(tmp_root)],
                capture_output=True, text=True)
            self.assertFalse(null_path.exists(), "Script must NOT create $null file")


if __name__ == "__main__":
    unittest.main()
