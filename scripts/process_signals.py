from __future__ import annotations

import sys
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from oos.artifact_store import ArtifactStore
from oos.config import OOSConfig
from oos.models import Signal
from oos.signal_layer import (
    RawSignalFileImporter,
    RuleBasedSignalValidityEvaluator,
    SignalRouter,
)
from oos.opportunity_layer import OpportunityFramer
from oos.ideation import DeterministicIdeationStub
from oos.screen_layer import ScreenEvaluator
from oos.hypothesis_layer import HypothesisLayer
from oos.council_layer import CouncilLayer
from oos.portfolio_layer import PortfolioManager, PortfolioStateEnum
from oos.weekly_review import WeeklyReviewGenerator


def enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def status_name(value: Any) -> str:
    value = enum_value(value)
    return str(value)


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def to_signal(raw, validity) -> Signal:
    raw_id = getattr(raw, "id", None) or make_id("sig")
    timestamp = getattr(raw, "timestamp", "") or now_iso()

    raw_content = getattr(raw, "raw_content", "") or ""
    extracted_pain = getattr(raw, "extracted_pain", "") or ""

    # Trial fallback:
    # If the importer did not provide extracted_pain, use raw_content as the initial pain statement.
    # This keeps the trial pipeline running without pretending to have a real NLP extractor yet.
    if not extracted_pain:
        extracted_pain = raw_content[:500] if raw_content else "Unspecified pain signal"

    candidate_icp = getattr(raw, "candidate_icp", "") or "unknown"

    return Signal(
        id=raw_id,
        source=getattr(raw, "source", "file_import"),
        timestamp=timestamp,
        raw_content=raw_content,
        extracted_pain=extracted_pain,
        candidate_icp=candidate_icp,
        validity_specificity=getattr(validity, "specificity"),
        validity_recurrence=getattr(validity, "recurrence"),
        validity_workaround=getattr(validity, "active_workaround"),
        validity_cost_signal=getattr(validity, "cost_signal"),
        validity_icp_match=getattr(validity, "icp_match"),
        validity_score=getattr(validity, "score"),
        status=getattr(validity, "status"),
        rejection_reason=getattr(validity, "rejection_reason", None),
        metadata={},
    )


def get_screen_outcome(screen_result: Any) -> str:
    for field in ("outcome", "decision", "status", "screen_outcome"):
        if hasattr(screen_result, field):
            return status_name(getattr(screen_result, field))
    return status_name(screen_result)


def get_kill_reason_id(screen_result: Any) -> str | None:
    for field in ("kill_reason_id", "linked_kill_reason_id"):
        if hasattr(screen_result, field):
            return getattr(screen_result, field)
    if hasattr(screen_result, "kill_reason"):
        kr = getattr(screen_result, "kill_reason")
        return getattr(kr, "id", None)
    return None


def build_store(project_root: Path) -> ArtifactStore:
    artifacts_dir = project_root / "artifacts"
    try:
        return ArtifactStore(artifacts_dir)
    except TypeError:
        try:
            return ArtifactStore(base_dir=artifacts_dir)
        except TypeError:
            return ArtifactStore(root=artifacts_dir)


def build_component(cls, store: ArtifactStore):
    """
    Cursor-generated classes may accept ArtifactStore in different ways.
    This keeps the trial script tolerant without changing project code.
    """
    for args, kwargs in (
        ((store,), {}),
        ((), {"store": store}),
        ((), {"artifact_store": store}),
        ((), {}),
    ):
        try:
            return cls(*args, **kwargs)
        except TypeError:
            continue
    raise TypeError(f"Cannot construct {cls.__name__}")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: py scripts/process_signals.py <signals_json_file>")
        return 1

    input_path = Path(sys.argv[1]).resolve()
    project_root = Path.cwd().resolve()

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    config = OOSConfig.from_env(project_root=project_root)
    artifacts_root = project_root / "artifacts"
    store = build_store(project_root)

    importer = RawSignalFileImporter()
    evaluator = RuleBasedSignalValidityEvaluator()

    router = SignalRouter(artifacts_root)
    framer = OpportunityFramer(store)
    ideator = DeterministicIdeationStub(store)
    screener = ScreenEvaluator(store)

    hypothesis_layer = HypothesisLayer(artifacts_root)
    council_layer = CouncilLayer(artifacts_root)
    portfolio = PortfolioManager(artifacts_root)
    weekly_review = WeeklyReviewGenerator(artifacts_root)
    raw_signals = importer.load(input_path)

    counts = {
        "signals_processed": 0,
        "validated": 0,
        "weak": 0,
        "noise": 0,
        "opportunities_created": 0,
        "ideas_created": 0,
        "killed": 0,
        "hypotheses_created": 0,
        "experiments_created": 0,
        "council_decisions_created": 0,
    }

    for raw in raw_signals:
        counts["signals_processed"] += 1

        validity = evaluator.evaluate(raw)
        signal = to_signal(raw, validity)
        router.write_and_route(signal)

        signal_status = status_name(signal.status)

        if signal_status == "validated":
            counts["validated"] += 1
        elif signal_status == "weak":
            counts["weak"] += 1
            continue
        elif signal_status == "noise":
            counts["noise"] += 1
            continue
        else:
            continue

        opportunity = framer.frame_from_signals([signal])
        counts["opportunities_created"] += 1

        ideas = ideator.generate(opportunity)
        counts["ideas_created"] += len(ideas)

        for idea in ideas:
            screen_result = screener.evaluate(idea)
            outcome = get_screen_outcome(screen_result)

            if outcome == "kill":
                counts["killed"] += 1
                kill_reason_id = get_kill_reason_id(screen_result)

                portfolio.upsert_state(
                    opportunity_id=opportunity.id,
                    state=PortfolioStateEnum.Killed,
                    reason="[recommend_kill] killed by screen",
                    linked_kill_reason_id=kill_reason_id,
                )
                continue

            generated = hypothesis_layer.generate_for_screened_idea(
                idea,
                screen_outcome=outcome,
            )

            if generated is None:
                continue

            hypothesis, experiment = generated
            counts["hypotheses_created"] += 1
            counts["experiments_created"] += 1

            council_decision = council_layer.generate_for_shortlisted_idea(idea)
            counts["council_decisions_created"] += 1

            portfolio.upsert_state(
                opportunity_id=opportunity.id,
                state=PortfolioStateEnum.Active,
                reason="[needs_review] survived screen and mapped to hypothesis",
                linked_council_decision_id=council_decision.id,
            )

    review_path = weekly_review.generate()

    print("OOS process-signals completed.")
    for key, value in counts.items():
        print(f"{key}: {value}")
    print(f"weekly_review: {review_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())