from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Optional

from .config import OOSConfig
from .council_layer import CouncilLayer
from .hypothesis_layer import HypothesisLayer
from .ideation import DeterministicIdeationStub
from .model_routing import ModelRouter
from .opportunity_layer import OpportunityFramer
from .portfolio_layer import PortfolioManager
from .models import PortfolioStateEnum
from .screen_layer import ScreenEvaluator
from .signal_layer import SignalLayer
from .weekly_review import WeeklyReviewGenerator


@dataclass
class Orchestrator:
    """
    Lightweight orchestrator skeleton for OOS v1.

    Week 1 responsibilities:
    - hold configuration,
    - define the shape of the batch pipeline,
    - provide a smoke-test flow that runs an "empty" pipeline
      and writes dummy artifacts.

    Signal, Opportunity, Screen, Hypothesis, Council and Portfolio
    logic are intentionally *not* implemented yet.
    """

    config: OOSConfig

    def run_empty_pipeline(self) -> Path:
        """
        Run an empty pipeline and write a dummy artifact.

        This is used by the Week 1 smoke test to confirm that:
        - the orchestrator can be constructed,
        - the artifacts directory is writable,
        - a basic end-to-end run completes without errors.
        """
        smoke_dir = self.config.artifacts_dir / "smoke"
        smoke_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        safe_timestamp = timestamp.replace(":", "-")
        artifact_path = smoke_dir / f"smoke_run_{safe_timestamp}.txt"
        contents = [
            "OOS v1 — Week 1 Smoke Test",
            f"timestamp_utc={timestamp}",
            f"project_root={self.config.project_root}",
            f"artifacts_dir={self.config.artifacts_dir}",
            "status=ok",
        ]
        artifact_path.write_text("\n".join(contents), encoding="utf-8")
        return artifact_path

    def run_v1_dry_run(self, *, now: Optional[datetime] = None) -> Dict[str, Path]:
        """
        Week 8: end-to-end deterministic dry run of the v1 pipeline.

        Produces coherent artifacts across:
        Signal -> Opportunity -> Ideation -> Screen -> Hypothesis -> Council -> Portfolio -> Weekly Review
        plus:
        - v1 readiness report artifact
        - minimal operational checklist artifact
        """
        now = now or datetime.now(timezone.utc)
        artifacts_root = self.config.artifacts_dir

        # Model routing (explicit & configurable)
        router = ModelRouter(config_path=self.config.project_root / "config" / "model_routing.json")
        routing_selected = {stage: router.select(stage) for stage in router.config.rules_by_stage.keys()}

        # Stage 1: Signals (manual ingestion)
        signal_layer = SignalLayer(artifacts_root=artifacts_root)
        # One "validated" and one "weak" signal; deterministic via explicit validity overrides through file-import path is
        # not needed here—use manual signals that should score high/medium.
        sig_valid = signal_layer.ingest_manual(
            raw_content="Every day I manually export and copy data; it takes 30 minutes and causes errors.",
            extracted_pain="Manual export/copy wastes time daily and causes errors.",
            candidate_icp="ops manager",
            source="dry_run",
            timestamp=now.isoformat(timespec="seconds"),
            signal_id="sig_dry_valid",
            metadata={"dry_run": True},
        )
        sig_weak = signal_layer.ingest_manual(
            raw_content="Often annoying, but not sure why.",
            extracted_pain="Annoying workflow friction.",
            candidate_icp="unknown",
            source="dry_run",
            timestamp=now.isoformat(timespec="seconds"),
            signal_id="sig_dry_weak",
            metadata={"dry_run": True},
        )

        # Stage 2: Opportunity framing (validated + optional weak promotion)
        framer = OpportunityFramer(store=signal_layer.router.store)
        opp = framer.frame_from_signals(
            [sig_valid, sig_weak],
            opportunity_id="opp_dry_1",
            promote_weak_signal_ids={"sig_dry_weak"},
            initial_notes="Dry run opportunity card.",
            opportunity_type="workflow_friction",
        )

        # Stage 3: Ideation (deterministic stub)
        ideation = DeterministicIdeationStub(store=signal_layer.router.store)
        ideas = ideation.generate(opp)

        # Stage 4: Screen (force one kill and one pass via overrides for deterministic coverage)
        screen = ScreenEvaluator(store=signal_layer.router.store)
        screened = []
        for idx, idea in enumerate(ideas):
            if idx == 0:
                # pass: override to avoid accidental anti-pattern match
                res = screen.evaluate(
                    idea,
                    checks_override={
                        "pain_real_and_recurring": True,
                        "icp_identifiable_and_can_pay": True,
                        "productizable_systematizable": True,
                        "market_not_closed": True,
                        "founder_not_blocked_by_regulatory_gatekeeping": True,
                    },
                    anti_patterns_override={
                        "custom_per_client_handling": False,
                        "founder_bottleneck": False,
                        "traffic_ads_monetization": False,
                        "no_repeatable_workflow": False,
                    },
                )
            else:
                # kill: force founder bottleneck anti-pattern
                res = screen.evaluate(
                    idea,
                    anti_patterns_override={"founder_bottleneck": True, "no_repeatable_workflow": False},
                )
            screened.append((idea, res))

        # Stage 5: Hypothesis (only pass/park)
        hyp_layer = HypothesisLayer(artifacts_root=artifacts_root)
        hyp_exp_pairs = []
        for idea, res in screened:
            out = hyp_layer.generate_for_screened_idea(idea, screen_outcome=res.outcome)
            if out is not None:
                hyp_exp_pairs.append(out)

        # Stage 6: Council (only survivors)
        council = CouncilLayer(artifacts_root=artifacts_root)
        council_decisions = []
        for idea, res in screened:
            if res.outcome in {"pass", "park"}:
                council_decisions.append(council.generate_for_shortlisted_idea(idea))

        # Stage 7: Portfolio transition (opportunity-centric)
        portfolio = PortfolioManager(artifacts_root=artifacts_root)
        # Set portfolio state once:
        # - If any pass exists => Active
        # - Else if any park exists => Parked
        # - Else if any kill exists => Killed (with first kill reason)
        outcomes = [res.outcome for _, res in screened]
        first_kill_reason = next((res.kill_reason_id for _, res in screened if res.kill_reason_id), None)
        if "pass" in outcomes:
            portfolio.transition(opportunity_id=opp.id, to_state=PortfolioStateEnum.Active, reason="Dry run [needs_review]")
        elif "park" in outcomes:
            portfolio.transition(opportunity_id=opp.id, to_state=PortfolioStateEnum.Parked, reason="Dry run [needs_review]")
        else:
            portfolio.transition(
                opportunity_id=opp.id,
                to_state=PortfolioStateEnum.Killed,
                reason="Dry run [recommend_kill]",
                linked_kill_reason_id=first_kill_reason,
            )

        # Stage 8: Weekly review package
        weekly = WeeklyReviewGenerator(artifacts_root=artifacts_root)
        weekly_path = weekly.generate(now=now)

        # Readiness report + operational checklist artifacts
        readiness_dir = artifacts_root / "readiness"
        readiness_dir.mkdir(parents=True, exist_ok=True)
        safe_ts = now.isoformat(timespec="seconds").replace(":", "-")
        readiness_path = readiness_dir / f"v1_readiness_{safe_ts}.json"
        readiness_payload = {
            "version": "v1",
            "generated_at": now.isoformat(timespec="seconds"),
            "routing": routing_selected,
            "artifacts_written": {
                "signals": ["sig_dry_valid", "sig_dry_weak"],
                "opportunity": opp.id,
                "ideas": [i.id for i, _ in screened],
                "kills": [res.kill_reason_id for _, res in screened if res.kill_reason_id],
                "hypotheses": [h.id for h, _ in hyp_exp_pairs],
                "experiments": [e.id for _, e in hyp_exp_pairs],
                "council": [d.id for d in council_decisions],
                "portfolio": [f"ps_{opp.id}"],
                "weekly_review": weekly_path.name,
            },
            "status": "ok",
            "notes": "Dry-run validates artifact coherence and stage connectivity (no execution layer).",
        }
        readiness_path.write_text(json.dumps(readiness_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        ops_dir = artifacts_root / "ops"
        ops_dir.mkdir(parents=True, exist_ok=True)
        checklist_path = ops_dir / "v1_operational_checklist.txt"
        checklist = [
            "OOS v1 Operational Checklist (minimal)",
            "",
            "1) Run batch pipeline dry-run (or real run when sources are configured).",
            "2) Review weak/noise routing outputs in artifacts/weak_signals and artifacts/noise_archive.",
            "3) Review OpportunityCards, IdeaVariants, Screen outputs (kills).",
            "4) Review Hypotheses and Experiments (7/14-day plans).",
            "5) Review CouncilDecision artifacts and suspiciously_clean flags.",
            "6) Review PortfolioState and weekly review package.",
            "",
            "Founder remains the final decision maker (human-in-the-loop).",
        ]
        checklist_path.write_text("\n".join(checklist), encoding="utf-8")

        return {
            "weekly_review": weekly_path,
            "readiness_report": readiness_path,
            "operational_checklist": checklist_path,
        }

