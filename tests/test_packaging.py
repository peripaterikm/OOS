import sys
import unittest
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


class TestPackaging(unittest.TestCase):
    def test_console_script_entrypoint_is_declared(self) -> None:
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["scripts"]["oos"], "oos.cli:main")


if __name__ == "__main__":
    unittest.main()
