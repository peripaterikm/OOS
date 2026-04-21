import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main


class TestCli(unittest.TestCase):
    def test_v1_dry_run_command_writes_expected_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["v1-dry-run", "--project-root", tmp])

            output = stdout.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("OOS v1 dry run completed.", output)
            self.assertIn("weekly_review:", output)
            self.assertIn("readiness_report:", output)
            self.assertIn("operational_checklist:", output)
            self.assertIn("founder_review_checklist:", output)

            artifacts_dir = Path(tmp) / "artifacts"
            self.assertTrue((artifacts_dir / "signals" / "sig_dry_valid.json").exists())
            self.assertTrue((artifacts_dir / "weak_signals" / "sig_dry_weak.json").exists())
            self.assertTrue((artifacts_dir / "opportunities" / "opp_dry_1.json").exists())
            self.assertTrue((artifacts_dir / "portfolio" / "ps_opp_dry_1.json").exists())
            self.assertTrue((artifacts_dir / "ops" / "v1_operational_checklist.txt").exists())
            self.assertTrue((artifacts_dir / "ops" / "v1_founder_review_checklist.md").exists())

            readiness_paths = list((artifacts_dir / "readiness").glob("v1_readiness_*.json"))
            self.assertEqual(len(readiness_paths), 1)
            readiness = json.loads(readiness_paths[0].read_text(encoding="utf-8"))
            self.assertEqual(readiness["status"], "ok")


if __name__ == "__main__":
    unittest.main()
