from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import OOSConfig
from .orchestrator import Orchestrator


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oos",
        description=(
            "Opportunity Operating System (OOS) — v1 core runner.\n"
            "Provides minimal commands for v1 build milestones."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Smoke-test command: runs an empty pipeline and writes a dummy artifact.
    smoke_parser = subparsers.add_parser(
        "smoke-test",
        help="Run an empty pipeline and write a dummy artifact.",
    )
    smoke_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the OOS project root (defaults to current working directory).",
    )

    dry_parser = subparsers.add_parser(
        "v1-dry-run",
        help="Run an end-to-end v1 dry-run pipeline and write artifacts.",
    )
    dry_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the OOS project root (defaults to current working directory).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "smoke-test":
        config = OOSConfig.from_env(project_root=args.project_root)
        orchestrator = Orchestrator(config=config)
        artifact_path = orchestrator.run_empty_pipeline()

        print("OOS smoke test completed.")
        print(f"Dummy artifact written to: {artifact_path}")
        return 0

    if args.command == "v1-dry-run":
        config = OOSConfig.from_env(project_root=args.project_root)
        orchestrator = Orchestrator(config=config)
        paths = orchestrator.run_v1_dry_run()

        print("OOS v1 dry run completed.")
        for k, p in paths.items():
            print(f"{k}: {p}")
        return 0

    # In Week 1 there are no other commands.
    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

