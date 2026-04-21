from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class OOSConfig:
    """
    Minimal configuration for v1 OOS.

    Week 1 keeps configuration explicit and file-based.
    No dynamic environment or secrets handling is required yet.
    """

    # Root directory of the project (resolved at runtime)
    project_root: Path

    # Base directory where artifacts are stored.
    artifacts_dir: Path

    # Optional environment name (e.g., "dev", "test").
    env: str = "dev"

    @classmethod
    def from_env(cls, project_root: Optional[Path] = None) -> "OOSConfig":
        """
        Construct configuration from the current process environment.

        Week 1 keeps this very simple:
        - project_root defaults to the current working directory,
        - artifacts_dir is "<project_root>/artifacts".
        """
        base_root = project_root or Path.cwd()
        artifacts_dir = base_root / "artifacts"
        return cls(project_root=base_root, artifacts_dir=artifacts_dir)

