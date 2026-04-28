from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .ai_ideation_evaluation import evaluate_ai_ideation
from .artifact_store import ArtifactStore
from .config import OOSConfig
from .discovery_weekly import run_discovery_weekly
from .founder_ai_stage_rating import ALLOWED_AI_RATING_STAGES, ALLOWED_AI_STAGE_RATINGS, record_ai_stage_rating
from .founder_review_package import FounderReviewIndex
from .models import FounderReviewDecision, FounderReviewDecisionEnum, PortfolioStateEnum
from .orchestrator import Orchestrator
from .portfolio_layer import PortfolioManager
from .weekly_review import WeeklyReviewGenerator


DECISION_ALIASES = {
    "active": FounderReviewDecisionEnum.Active,
    "pass": FounderReviewDecisionEnum.Active,
    "parked": FounderReviewDecisionEnum.Parked,
    "park": FounderReviewDecisionEnum.Parked,
    "killed": FounderReviewDecisionEnum.Killed,
    "kill": FounderReviewDecisionEnum.Killed,
}


DECISION_REVIEW_OPTIONS = {
    FounderReviewDecisionEnum.Active: "pass",
    FounderReviewDecisionEnum.Parked: "park",
    FounderReviewDecisionEnum.Killed: "kill",
}


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


def _parse_founder_decision(value: str) -> FounderReviewDecisionEnum:
    decision = DECISION_ALIASES.get(value.strip().lower())
    if decision is None:
        allowed = ", ".join(["pass", "park", "kill", *[d.value for d in FounderReviewDecisionEnum]])
        raise ValueError(f"Invalid founder decision {value!r}. Expected one of: {allowed}")
    return decision


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
    review_id: str | None = None,
    linked_signal_ids: list[str] | None = None,
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
        review_id=review_id,
        linked_signal_ids=linked_signal_ids or [],
        readiness_report_id=readiness_report_id,
        weekly_review_id=weekly_review_id,
        council_decision_ids=council_decision_ids,
        hypothesis_ids=hypothesis_ids,
        experiment_ids=experiment_ids,
        linked_kill_reason_id=linked_kill_reason_id,
    )
    ref = ArtifactStore(root_dir=config.artifacts_dir).write_model(review)
    return ref.path, portfolio_updated


def _record_founder_review_by_review_id(
    *,
    project_root: Path,
    review_id: str,
    decision: FounderReviewDecisionEnum,
    reason: str | None,
    next_action: str | None,
    timestamp: str | None,
) -> tuple[Path, bool]:
    config = OOSConfig.from_env(project_root=project_root)
    entry = FounderReviewIndex(config.artifacts_dir).get_entry(review_id)
    decision_option = DECISION_REVIEW_OPTIONS[decision]
    if decision_option not in entry.decision_options:
        raise ValueError(
            f"Decision {decision_option!r} is not available for {review_id}. "
            f"Expected one of: {', '.join(entry.decision_options)}"
        )

    linked = entry.linked_artifact_ids
    linked_kill_reason_id = None
    kill_ids = linked.get("kills") or []
    if decision == FounderReviewDecisionEnum.Killed:
        if not kill_ids:
            raise ValueError(f"Cannot record kill for {review_id}: no linked kill reason exists in the review index")
        linked_kill_reason_id = str(kill_ids[0])

    result = _record_founder_review_decision(
        project_root=project_root,
        opportunity_id=entry.entity_id,
        decision=decision,
        reason=reason or f"Founder selected {decision_option} for {review_id}: {entry.title}",
        next_action=next_action or "Review the linked artifacts and run the next cheapest validation step.",
        timestamp=timestamp,
        review_id=review_id,
        linked_signal_ids=entry.linked_signal_ids,
        readiness_report_id=str(linked["readiness_report"]) if linked.get("readiness_report") else None,
        weekly_review_id=str(linked["weekly_review"]) if linked.get("weekly_review") else None,
        council_decision_ids=[str(item) for item in linked.get("council", [])],
        hypothesis_ids=[str(item) for item in linked.get("hypotheses", [])],
        experiment_ids=[str(item) for item in linked.get("experiments", [])],
        linked_kill_reason_id=linked_kill_reason_id,
    )
    WeeklyReviewGenerator(artifacts_root=config.artifacts_dir).generate()
    return result


def _latest_weekly_review_path(artifacts_dir: Path) -> Path | None:
    weekly_dir = artifacts_dir / "weekly_reviews"
    if not weekly_dir.exists():
        return None
    paths = sorted(weekly_dir.glob("weekly_review_*.json"), key=lambda path: (path.stat().st_mtime, path.name))
    return paths[-1] if paths else None


def _print_weekly_cycle_status(*, project_root: Path) -> int:
    config = OOSConfig.from_env(project_root=project_root)
    artifacts_dir = config.artifacts_dir
    inbox_path = artifacts_dir / "ops" / "founder_review_inbox.md"
    index_path = artifacts_dir / "ops" / "founder_review_index.json"
    weekly_path = _latest_weekly_review_path(artifacts_dir)

    if not inbox_path.exists() or not index_path.exists() or weekly_path is None:
        print("weekly-cycle-status refused: no real weekly cycle artifacts found.")
        print(f"Expected founder review inbox at: {inbox_path}")
        print(f"Expected founder review index at: {index_path}")
        print(f"Expected weekly reviews under: {artifacts_dir / 'weekly_reviews'}")
        print("Next step:")
        print(
            "  .\\.venv\\Scripts\\python.exe -m oos.cli run-weekly-cycle "
            f"--project-root {config.project_root} --input-file examples\\real_signal_batch.jsonl"
        )
        return 2

    index = json.loads(index_path.read_text(encoding="utf-8"))
    weekly = json.loads(weekly_path.read_text(encoding="utf-8"))
    entries = index.get("entries") or []
    if not isinstance(entries, list) or not entries:
        print(f"weekly-cycle-status refused: founder review index has no review entries: {index_path}")
        return 2

    print("OOS weekly cycle status")
    print(f"project_root: {config.project_root}")
    print(f"founder_review_inbox: {inbox_path}")
    print(f"founder_review_index: {index_path}")
    print(f"latest_weekly_review: {weekly_path}")
    print("")
    print("Reviewable items:")
    for entry in entries:
        review_id = entry["review_id"]
        decision_options = ", ".join(entry["decision_options"])
        print(f"- {review_id}: {entry['title']}")
        print(f"  summary: {entry['summary']}")
        print(f"  decision_options: {decision_options}")
        print(f"  linked_signal_ids: {', '.join(entry['linked_signal_ids'])}")
        print(
            "  example: "
            f".\\.venv\\Scripts\\python.exe -m oos.cli record-founder-review "
            f"--project-root {config.project_root} --review-id {review_id} --decision pass"
        )

    print("")
    print("Founder decisions:")
    recent_reviews = weekly.get("recent_founder_reviews") or []
    if recent_reviews:
        for review in recent_reviews:
            print(
                f"- {review.get('review_id') or '(manual)'}: {review.get('decision')} "
                f"for {review.get('opportunity_id')} at {review.get('timestamp')}"
            )
            linked_signal_ids = review.get("linked_signal_ids") or []
            if linked_signal_ids:
                print(f"  linked_signal_ids: {', '.join(linked_signal_ids)}")
    else:
        print("- none recorded yet")

    print("")
    print("Portfolio/result summary:")
    for entry in entries:
        linked_artifacts = entry.get("linked_artifact_ids", {})
        portfolio_ids = linked_artifacts.get("portfolio") or []
        for portfolio_id in portfolio_ids:
            portfolio_path = artifacts_dir / "portfolio" / f"{portfolio_id}.json"
            if portfolio_path.exists():
                portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
                print(f"- {portfolio['opportunity_id']}: {portfolio['state']} ({portfolio.get('reason', '')})")

    return 0


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

    weekly_parser = subparsers.add_parser(
        "run-weekly-cycle",
        help="Run one real weekly cycle from a canonical JSONL signal batch.",
    )
    weekly_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the OOS project root (defaults to current working directory).",
    )
    weekly_parser.add_argument(
        "--input-file",
        type=Path,
        required=True,
        help="Path to a canonical JSONL signal batch file.",
    )

    discovery_parser = subparsers.add_parser(
        "run-discovery-weekly",
        help="Run the offline Source Intelligence MVP weekly discovery loop.",
    )
    discovery_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the OOS project root (defaults to current working directory).",
    )
    discovery_parser.add_argument(
        "--topic",
        required=True,
        help="Active topic id to run, e.g. ai_cfo_smb.",
    )
    discovery_parser.add_argument(
        "--run-id",
        default=None,
        help="Optional deterministic discovery run id.",
    )
    discovery_parser.add_argument(
        "--input-raw-evidence",
        type=Path,
        default=None,
        help="Optional local RawEvidence JSON file. Defaults to the MVP example fixture.",
    )
    discovery_parser.add_argument(
        "--include-meaning-loop-dry-run",
        action="store_true",
        help="Also write adapter-only Source Intelligence -> meaning-loop dry-run artifacts.",
    )

    status_parser = subparsers.add_parser(
        "weekly-cycle-status",
        help="Print operator status for the latest real weekly cycle.",
    )
    status_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the OOS project root (defaults to current working directory).",
    )

    eval_parser = subparsers.add_parser(
        "evaluate-ai-ideation",
        help="Evaluate deterministic vs assisted ideation on a canonical JSONL signal batch.",
    )
    eval_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the OOS project root (defaults to current working directory).",
    )
    eval_parser.add_argument(
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
    review_parser.add_argument("--review-id", default=None, help="Founder review id from founder_review_index.json.")
    review_parser.add_argument("--opportunity-id", default=None, help="Opportunity id under founder review.")
    review_parser.add_argument(
        "--decision",
        required=True,
        choices=["pass", "park", "kill", *[d.value for d in FounderReviewDecisionEnum]],
        help="Founder decision for the opportunity.",
    )
    review_parser.add_argument("--reason", default=None, help="Concrete reason for the decision.")
    review_parser.add_argument(
        "--next-action",
        default=None,
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

    rating_parser = subparsers.add_parser(
        "record-ai-stage-rating",
        help="Record an advisory founder rating for an AI-stage artifact.",
    )
    rating_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the OOS project root (defaults to current working directory).",
    )
    rating_parser.add_argument("--stage", required=True, choices=sorted(ALLOWED_AI_RATING_STAGES))
    rating_parser.add_argument("--rating", required=True, choices=sorted(ALLOWED_AI_STAGE_RATINGS))
    rating_parser.add_argument("--explanation", required=True)
    rating_parser.add_argument("--linked-artifact-id", action="append", default=[])
    rating_parser.add_argument("--linked-signal-id", action="append", default=[])
    rating_parser.add_argument("--rating-id", default=None)
    rating_parser.add_argument("--created-at", default=None)
    rating_parser.add_argument("--founder", default="founder")

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

    if args.command == "run-weekly-cycle":
        config = OOSConfig.from_env(project_root=args.project_root)
        orchestrator = Orchestrator(config=config)
        try:
            paths = orchestrator.run_weekly_cycle(input_file=args.input_file)
        except ValueError as exc:
            print(str(exc))
            return 2

        print("OOS weekly cycle completed.")
        for k, p in paths.items():
            print(f"{k}: {p}")
        return 0

    if args.command == "run-discovery-weekly":
        try:
            result = run_discovery_weekly(
                project_root=args.project_root,
                topic_id=args.topic,
                run_id=args.run_id,
                input_raw_evidence=args.input_raw_evidence,
                include_meaning_loop_dry_run=args.include_meaning_loop_dry_run,
            )
        except ValueError as exc:
            print(str(exc))
            return 2

        print("OOS Source Intelligence weekly discovery completed.")
        print(f"run_id: {result.run_id}")
        print(f"run_dir: {result.run_dir}")
        for name, path in result.artifact_paths.items():
            print(f"{name}: {path}")
        return 0

    if args.command == "weekly-cycle-status":
        return _print_weekly_cycle_status(project_root=args.project_root)

    if args.command == "evaluate-ai-ideation":
        config = OOSConfig.from_env(project_root=args.project_root)
        try:
            report_path = evaluate_ai_ideation(
                project_root=config.project_root,
                input_file=args.input_file,
                ai_response_json=config.ai_ideation_response_json,
            )
        except ValueError as exc:
            print(str(exc))
            return 2

        print("OOS AI ideation evaluation completed.")
        print(f"evaluation_report: {report_path}")
        return 0

    if args.command == "record-founder-review":
        decision = _parse_founder_decision(args.decision)
        if args.review_id:
            try:
                path, portfolio_updated = _record_founder_review_by_review_id(
                    project_root=args.project_root,
                    review_id=args.review_id,
                    decision=decision,
                    reason=args.reason,
                    next_action=args.next_action,
                    timestamp=args.timestamp,
                )
            except ValueError as exc:
                print(str(exc))
                return 2
        else:
            if not args.opportunity_id:
                raise ValueError("--opportunity-id is required unless --review-id is provided")
            if not args.reason:
                raise ValueError("--reason is required unless --review-id is provided")
            if not args.next_action:
                raise ValueError("--next-action is required unless --review-id is provided")
            path, portfolio_updated = _record_founder_review_decision(
                project_root=args.project_root,
                opportunity_id=args.opportunity_id,
                decision=decision,
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

    if args.command == "record-ai-stage-rating":
        try:
            path = record_ai_stage_rating(
                project_root=args.project_root,
                stage=args.stage,
                rating=args.rating,
                explanation=args.explanation,
                linked_artifact_ids=args.linked_artifact_id,
                linked_signal_ids=args.linked_signal_id,
                rating_id=args.rating_id,
                created_at=args.created_at,
                founder=args.founder,
            )
        except ValueError as exc:
            print(str(exc))
            return 2

        print("Founder AI-stage rating recorded.")
        print("advisory_only: true")
        print(f"rating_artifact: {path}")
        return 0

    # In Week 1 there are no other commands.
    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

