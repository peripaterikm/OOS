import io
import json
import os
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main
from oos.config import OOSConfig
from oos.weekly_review import WeeklyReviewGenerator


@contextmanager
def changed_cwd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def run_dry_run(project_root: Path, cwd: Path) -> str:
    stdout = io.StringIO()
    with changed_cwd(cwd), redirect_stdout(stdout):
        exit_code = main(["v1-dry-run", "--project-root", str(project_root)])
    if exit_code != 0:
        raise AssertionError(f"v1-dry-run failed with exit code {exit_code}:\n{stdout.getvalue()}")
    return stdout.getvalue()


def artifact_class(project_root: Path) -> set[tuple[str, str]]:
    artifacts_dir = project_root / "artifacts"
    out: set[tuple[str, str]] = set()
    for path in artifacts_dir.rglob("*"):
        if path.is_file():
            relative = path.relative_to(artifacts_dir)
            filename = relative.name
            if relative.parts[0] == "readiness" and filename.startswith("v1_readiness_"):
                filename = "v1_readiness_<timestamp>.json"
            elif relative.parts[0] in {"council", "experiments", "hypotheses", "ideas", "kills"}:
                filename = f"{relative.parts[0]}_artifact.json"
            out.add((relative.parts[0], filename))
    return out


class TestRuntimeContract(unittest.TestCase):
    def test_same_project_root_is_independent_of_current_working_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            project_root = base / "project"
            cwd_one = base / "cwd_one"
            cwd_two = base / "cwd_two"
            project_root.mkdir()
            cwd_one.mkdir()
            cwd_two.mkdir()

            with changed_cwd(cwd_one):
                config_one = OOSConfig.from_env(project_root=project_root)
            with changed_cwd(cwd_two):
                config_two = OOSConfig.from_env(project_root=project_root)

            self.assertEqual(config_one.project_root, project_root.resolve())
            self.assertEqual(config_two.project_root, project_root.resolve())
            self.assertEqual(config_one.artifacts_dir, project_root.resolve() / "artifacts")
            self.assertEqual(config_two.artifacts_dir, project_root.resolve() / "artifacts")

            run_dry_run(project_root, cwd_one)
            weekly_path_one = WeeklyReviewGenerator(config_one.artifacts_dir).generate()
            with changed_cwd(cwd_two):
                weekly_path_two = WeeklyReviewGenerator(config_two.artifacts_dir).generate()

            self.assertEqual(weekly_path_one, weekly_path_two)
            self.assertTrue((project_root / "artifacts" / "signals" / "sig_dry_valid.json").exists())
            self.assertFalse((cwd_one / "artifacts").exists())
            self.assertFalse((cwd_two / "artifacts").exists())

    def test_dirty_repo_root_does_not_affect_different_clean_project_root(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dirty_cwd = base / "dirty_repo"
            clean_project_root = base / "clean_project"
            dirty_artifacts = dirty_cwd / "artifacts"
            dirty_artifacts.mkdir(parents=True)
            clean_project_root.mkdir()
            (dirty_artifacts / "stale.txt").write_text("stale repo-root artifact", encoding="utf-8")

            output = run_dry_run(clean_project_root, dirty_cwd)

            self.assertIn("OOS v1 dry run completed.", output)
            self.assertEqual((dirty_artifacts / "stale.txt").read_text(encoding="utf-8"), "stale repo-root artifact")
            self.assertFalse((dirty_artifacts / "signals").exists())
            self.assertTrue((clean_project_root / "artifacts" / "signals" / "sig_dry_valid.json").exists())

    def test_separate_clean_roots_produce_same_class_of_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            cwd = base / "cwd"
            first_root = base / "first_root"
            second_root = base / "second_root"
            cwd.mkdir()
            first_root.mkdir()
            second_root.mkdir()

            run_dry_run(first_root, cwd)
            run_dry_run(second_root, cwd)

            self.assertEqual(artifact_class(first_root), artifact_class(second_root))

    def test_weekly_review_top_level_keys_match_across_clean_runs(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            cwd = base / "cwd"
            first_root = base / "first_root"
            second_root = base / "second_root"
            cwd.mkdir()
            first_root.mkdir()
            second_root.mkdir()

            run_dry_run(first_root, cwd)
            run_dry_run(second_root, cwd)

            first_weekly = next((first_root / "artifacts" / "weekly_reviews").glob("weekly_review_*.json"))
            second_weekly = next((second_root / "artifacts" / "weekly_reviews").glob("weekly_review_*.json"))
            first_payload = json.loads(first_weekly.read_text(encoding="utf-8"))
            second_payload = json.loads(second_weekly.read_text(encoding="utf-8"))

            self.assertEqual(set(first_payload.keys()), set(second_payload.keys()))


if __name__ == "__main__":
    unittest.main()
