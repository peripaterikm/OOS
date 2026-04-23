from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from .artifact_store import ArtifactStore
from .config import OOSConfig
from .models import FounderReviewDecision, FounderReviewDecisionEnum, PortfolioStateEnum
from .orchestrator import Orchestrator
from .portfolio_layer import PortfolioManager


def _safe_artifact_id_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)


def _artifact_path(root_dir: Path, kind: str, artifact_id_or_filename: str) -> Path:
    artifact_id_or_filename = artifact_id_or_filename.strip()
    path_fragment = Path(artifact_id_or_filename)
    if (
        not artifact_id_or_filename
        or path_fragment.is_absolute()
        or len(path_fragment.parts) != 1
        or "\\" in artifact_id_or_filename
    ):
        raise ValueError(
            f"Invalid linked {kind} artifact id {artifact_id_or_filename!r}: "
            f"pass an artifact id or .json filename, not a path. "
            f"Expected file under {root_dir / kind}."
        )
    if path_fragment.suffix and path_fragment.suffix != ".json":
        raise ValueError(
            f"Invalid linked {kind} artifact id {artifact_id_or_filename!r}: "
            "use the artifact id or its .json filename."
        )

    path = root_dir / kind / artifact_id_or_filename
    if path.suffix != ".json":
        path = path.with_suffix(".json")
    return path


def _require_existing_artifact(root_dir: Path, kind: str, artifact_id_or_filename: str) -> None:
    path = _artifact_path(root_dir, kind, artifact_id_or_filename)
    if not path.exists():
        raise ValueError(f"Linked {kind} artifact not found for {artifact_id_or_filename!r}: expected {path}")


def _validate_founder_review_links(
    *,
    artifacts_dir: Path,
    readiness_report_id: str | None,
    weekly_review_id: str | None,
    council_decision_ids: list[str],
    hypothesis_ids: list[str],
    experiment_ids: list[str],
    linked_kill_reason_id: str | None,
) -> None:
    if readiness_report_id:
        _require_existing_artifact(artifacts_dir, "readiness", readiness_report_id)
    if weekly_review_id:
        _require_existing_artifact(artifacts_dir, "weekly_reviews", weekly_review_id)
    for council_decision_id in council_decision_ids:
        _require_existing_artifact(artifacts_dir, "council", council_decision_id)
    for hypothesis_id in hypothesis_ids:
        _require_existing_artifact(artifacts_dir, "hypotheses", hypothesis_id)
    for experiment_id in experiment_ids:
        _require_existing_artifact(artifacts_dir, "experiments", experiment_id)
    if linked_kill_reason_id:
        _require_existing_artifact(artifacts_dir, "kills", linked_kill_reason_id)


def _refuse_dirty_dry_run(project_root: Path) -> bool:
    artifacts_dir = project_root / "artifacts"
    if not artifacts_dir.is_dir() or not any(artifacts_dir.iterdir()):
        return False

    print("v1-dry-run refused: dirty project root detected.")
    print(f"Existing artifacts found at: {artifacts_dir.resolve()}")
    print("Next steps:")
    print("  1) remove or rename the artifacts directory, or")
    print("  2) run against a clean project root")
    return True


def _record_founder_review_decision(
    *,
    project_root: Path,
    opportunity_id: str,
    decision: FounderReviewDecisionEnum,
    reason: str,
    next_action: str,
    timestamp: str | None,
    readiness_report_id: str | None,
    weekly_review_id: str | None,
    council_decision_ids: list[str],
    hypothesis_ids: list[str],
    experiment_ids: list[str],
    linked_kill_reason_id: str | None,
) -> tuple[Path, bool]:
    config = OOSConfig.from_env(project_root=project_root)
    ts = timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
    safe_ts = _safe_artifact_id_part(ts)
    artifact_id = f"frd_{_safe_artifact_id_part(opportunity_id)}_{safe_ts}"
    _validate_founder_review_links(
        artifacts_dir=config.artifacts_dir,
        readiness_report_id=readiness_report_id,
        weekly_review_id=weekly_review_id,
        council_decision_ids=council_decision_ids,
        hypothesis_ids=hypothesis_ids,
        experiment_ids=experiment_ids,
        linked_kill_reason_id=linked_kill_reason_id,
    )

    portfolio_updated = False
    if decision in (FounderReviewDecisionEnum.Active, FounderReviewDecisionEnum.Parked):
        portfolio = PortfolioManager(artifacts_root=config.artifacts_dir)
        portfolio.transition(
            opportunity_id=opportunity_id,
            to_state=PortfolioStateEnum(decision.value),
            reason=f"Founder review {ts}: {reason}",
        )
        portfolio_updated = True
    elif decision == FounderReviewDecisionEnum.Killed:
        if not linked_kill_reason_id:
            raise ValueError("--linked-kill-reason-id is required when --decision Killed")
        portfolio = PortfolioManager(artifacts_root=config.artifacts_dir)
        portfolio.transition(
            opportunity_id=opportunity_id,
            to_state=PortfolioStateEnum.Killed,
            reason=f"Founder review {ts}: {reason}",
            linked_kill_reason_id=linked_kill_reason_id,
        )
        portfolio_updated = True

    review = FounderReviewDecision(
        id=artifact_id,
        opportunity_id=opportunity_id,
        decision=decision,
        reason=reason,
        selected_next_experiment_or_action=next_action,
        timestamp=ts,
        portfolio_updated=portfolio_updated,
        readiness_report_id=readiness_report_id,
        weekly_review_id=weekly_review_id,
        council_decision_ids=council_decision_ids,
        hypothesis_ids=hypothesis_ids,
        experiment_ids=experiment_ids,
        linked_kill_reason_id=linked_kill_reason_id,
    )
    ref = ArtifactStore(root_dir=config.artifacts_dir).write_model(review)
    return ref.path, portfolio_updated


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

    batch_parser = subparsers.add_parser(
        "run-signal-batch",
        help="Run an end-to-end v1 pipeline from a canonical JSONL signal batch.",
    )
    batch_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the OOS project root (defaults to current working directory).",
    )
    batch_parser.add_argument(
        "--input-file",
        type=Path,
        required=True,
        help="Path to a canonical JSONL signal batch file.",
    )

    review_parser = subparsers.add_parser(
        "record-founder-review",
        help="Record a founder review decision as an artifact.",
    )
    review_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the OOS project root (defaults to current working directory).",
    )
    review_parser.add_argument("--opportunity-id", required=True, help="Opportunity id under founder review.")
    review_parser.add_argument(
        "--decision",
        required=True,
        choices=[d.value for d in FounderReviewDecisionEnum],
        help="Founder decision for the opportunity.",
    )
    review_parser.add_argument("--reason", required=True, help="Concrete reason for the decision.")
    review_parser.add_argument(
        "--next-action",
        required=True,
        help="Selected next experiment or next action.",
    )
    review_parser.add_argument(
        "--timestamp",
        default=None,
        help="Optional ISO timestamp for deterministic recording.",
    )
    review_parser.add_argument(
        "--readiness-report-id",
        default=None,
        help="Optional readiness report artifact id or filename reviewed.",
    )
    review_parser.add_argument(
        "--weekly-review-id",
        default=None,
        help="Optional weekly review artifact id or filename reviewed.",
    )
    review_parser.add_argument(
        "--council-decision-id",
        action="append",
        default=[],
        help="Optional council decision id reviewed; repeat for multiple.",
    )
    review_parser.add_argument(
        "--hypothesis-id",
        action="append",
        default=[],
        help="Optional hypothesis id reviewed; repeat for multiple.",
    )
    review_parser.add_argument(
        "--experiment-id",
        action="append",
        default=[],
        help="Optional experiment id reviewed; repeat for multiple.",
    )
    review_parser.add_argument(
        "--linked-kill-reason-id",
        default=None,
        help="Required when --decision Killed; existing KillReason id to link to portfolio state.",
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
        if _refuse_dirty_dry_run(args.project_root):
            return 2

        config = OOSConfig.from_env(project_root=args.project_root)
        orchestrator = Orchestrator(config=config)
        paths = orchestrator.run_v1_dry_run()

        print("OOS v1 dry run completed.")
        for k, p in paths.items():
            print(f"{k}: {p}")
        return 0

    if args.command == "run-signal-batch":
        config = OOSConfig.from_env(project_root=args.project_root)
        orchestrator = Orchestrator(config=config)
        try:
            paths = orchestrator.run_signal_batch(input_file=args.input_file)
        except ValueError as exc:
            print(str(exc))
            return 2

        print("OOS signal batch run completed.")
        for k, p in paths.items():
            print(f"{k}: {p}")
        return 0

    if args.command == "record-founder-review":
        path, portfolio_updated = _record_founder_review_decision(
            project_root=args.project_root,
            opportunity_id=args.opportunity_id,
            decision=FounderReviewDecisionEnum(args.decision),
            reason=args.reason,
            next_action=args.next_action,
            timestamp=args.timestamp,
            readiness_report_id=args.readiness_report_id,
            weekly_review_id=args.weekly_review_id,
            council_decision_ids=args.council_decision_id,
            hypothesis_ids=args.hypothesis_id,
            experiment_ids=args.experiment_id,
            linked_kill_reason_id=args.linked_kill_reason_id,
        )

        print("Founder review decision recorded.")
        print(f"decision_artifact: {path}")
        print(f"portfolio_updated: {str(portfolio_updated).lower()}")
        return 0

    # In Week 1 there are no other commands.
    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

