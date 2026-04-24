from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import sys
from typing import Dict, List, Optional

from .config import OOSConfig
from .council_layer import CouncilLayer
from .founder_review_package import FounderReviewEntry, FounderReviewPackageWriter
from .hypothesis_layer import HypothesisLayer
from .ideation import build_ideation_engine
from .model_routing import ModelRouter
from .opportunity_layer import OpportunityFramer
from .portfolio_layer import PortfolioManager
from .models import PortfolioStateEnum, Signal, SignalStatus
from .screen_layer import ScreenEvaluator
from .signal_dedup import build_dedup_metadata, canonical_signal_set
from .signal_layer import SignalLayer
from .real_signal_batch import CanonicalSignalBatchLoader
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

    def _shell_code_fence(self) -> str:
        return "powershell" if os.name == "nt" else "bash"

    def _quote_command_arg(self, value: str) -> str:
        if os.name == "nt":
            escaped = value.replace('"', '\\"')
            return f'"{escaped}"' if any(ch.isspace() for ch in value) else escaped
        return shlex.quote(value)

    def _format_review_command(self, command_parts: List[str]) -> str:
        continuation = " `" if os.name == "nt" else " \\"
        return f"{continuation}\n  ".join(command_parts)

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
        # One validated signal and one weak signal; the weak fixture is intentionally
        # recurrence + workaround only, so it routes to weak_signals before manual promotion.
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
            raw_content="Often I paste between tools because the handoff is annoying.",
            extracted_pain="Repeated paste-based handoff creates friction.",
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
        ideation = build_ideation_engine(
            store=signal_layer.router.store,
            ai_enabled=self.config.ai_ideation_enabled,
            ai_response_json=self.config.ai_ideation_response_json,
        )
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
        transition_reason = f"Dry run {now.isoformat(timespec='seconds')} [needs_review]"
        if "pass" in outcomes:
            portfolio.transition(opportunity_id=opp.id, to_state=PortfolioStateEnum.Active, reason=transition_reason)
        elif "park" in outcomes:
            portfolio.transition(opportunity_id=opp.id, to_state=PortfolioStateEnum.Parked, reason=transition_reason)
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
        ops_dir = artifacts_root / "ops"
        ops_dir.mkdir(parents=True, exist_ok=True)
        founder_checklist_path = ops_dir / "v1_founder_review_checklist.md"

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
                "founder_review_checklist": founder_checklist_path.name,
            },
            "status": "ok",
            "notes": "Dry-run validates artifact coherence and stage connectivity (no execution layer).",
        }
        readiness_path.write_text(json.dumps(readiness_payload, ensure_ascii=False, indent=2), encoding="utf-8")

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

        command_parts = [
            f"{self._quote_command_arg(sys.executable)} -m oos.cli record-founder-review",
            f"--project-root {self._quote_command_arg(str(self.config.project_root))}",
            f"--opportunity-id {opp.id}",
            "--decision Parked",
            f"--reason {self._quote_command_arg('Founder reviewed the v1 dry-run package and wants more evidence before proceeding.')}",
            f"--next-action {self._quote_command_arg('Run the selected cheapest next experiment before the next portfolio review.')}",
            f"--readiness-report-id {readiness_path.name}",
            f"--weekly-review-id {weekly_path.name}",
            *[f"--council-decision-id {decision.id}" for decision in council_decisions],
            *[f"--hypothesis-id {hyp.id}" for hyp, _ in hyp_exp_pairs],
            *[f"--experiment-id {exp.id}" for _, exp in hyp_exp_pairs],
        ]
        founder_review_command = self._format_review_command(command_parts)
        kill_reason_ids = [res.kill_reason_id for _, res in screened if res.kill_reason_id]
        killed_command_lines = []
        if kill_reason_ids:
            killed_command_parts = [
                f"{self._quote_command_arg(sys.executable)} -m oos.cli record-founder-review",
                f"--project-root {self._quote_command_arg(str(self.config.project_root))}",
                f"--opportunity-id {opp.id}",
                "--decision Killed",
                f"--reason {self._quote_command_arg('Founder reviewed the kill evidence and accepts the kill decision.')}",
                f"--next-action {self._quote_command_arg('Archive the opportunity and reuse the failure pattern in future screening.')}",
                f"--linked-kill-reason-id {kill_reason_ids[0]}",
                f"--readiness-report-id {readiness_path.name}",
                f"--weekly-review-id {weekly_path.name}",
                *[f"--council-decision-id {decision.id}" for decision in council_decisions],
                *[f"--hypothesis-id {hyp.id}" for hyp, _ in hyp_exp_pairs],
                *[f"--experiment-id {exp.id}" for _, exp in hyp_exp_pairs],
            ]
            killed_command_lines = [
                "",
                "## Ready-To-Run Killed Decision Command",
                f"```{self._shell_code_fence()}",
                self._format_review_command(killed_command_parts),
                "```",
            ]

        founder_checklist = [
            "# OOS v1 Founder Review Checklist",
            "",
            "## Review Objective",
            f"- Review the dry-run package generated at `{now.isoformat(timespec='seconds')}`.",
            f"- Start with readiness: `artifacts/readiness/{readiness_path.name}`.",
            f"- Use weekly review: `artifacts/weekly_reviews/{weekly_path.name}`.",
            f"- Commands below are generated for `{sys.platform}` using `{sys.executable}`.",
            "",
            "## Signals And Opportunities To Inspect",
            "- Validated signal: `artifacts/signals/sig_dry_valid.json`.",
            "- Weak signal promoted for review: `artifacts/weak_signals/sig_dry_weak.json`.",
            f"- Opportunity card: `artifacts/opportunities/{opp.id}.json`.",
            "",
            "## Kill / Proceed Decisions",
            *[
                f"- `{idea.id}`: `{res.outcome}`"
                + (f" with kill reason `artifacts/kills/{res.kill_reason_id}.json`." if res.kill_reason_id else ".")
                for idea, res in screened
            ],
            "",
            "## Hypotheses And Experiments To Review",
            *[
                f"- Hypothesis `artifacts/hypotheses/{hyp.id}.json`; experiment `artifacts/experiments/{exp.id}.json`."
                for hyp, exp in hyp_exp_pairs
            ],
            "",
            "## Council Concerns",
            *[f"- Council decision: `artifacts/council/{decision.id}.json`." for decision in council_decisions],
            "",
            "## Portfolio State Review",
            f"- Portfolio state: `artifacts/portfolio/ps_{opp.id}.json`.",
            f"- Weekly review package: `artifacts/weekly_reviews/{weekly_path.name}`.",
            "",
            "## Founder Action Checklist",
            "- Decide whether `opp_dry_1` should stay Active, be Parked, or be Killed.",
            "- Approve or reject the weak signal promotion from `sig_dry_weak`.",
            "- Pick the cheapest next experiment to run this week.",
            "- Record any kill decision with a concrete reason, not only a label.",
            "- Update portfolio state after the review decision.",
            "",
            "## Decision Writing Template",
            "- Good `reason`: name the evidence reviewed, the remaining uncertainty, and why the state is changing or staying.",
            "- Examples: `Council flagged founder bottleneck risk; park until 5 ICP interviews confirm urgency.`",
            "- Examples: `Validated signal is specific, but willingness to pay is unproven; keep Active for one pricing test.`",
            "- Examples: `Kill because the strongest idea depends on custom per-client handling, not a repeatable product.`",
            "- Good `next_action`: name one concrete experiment or operational action with a clear owner/timebox.",
            "- Examples: `Run 5 ops-manager interviews this week using hyp_1 assumptions.`",
            "- Examples: `Send pricing smoke test to 10 target buyers before next review.`",
            "- Examples: `Write kill summary and add pattern to future screen checks.`",
            "",
            "## Ready-To-Run Decision Command",
            f"```{self._shell_code_fence()}",
            founder_review_command,
            "```",
            *killed_command_lines,
        ]
        founder_checklist_path.write_text("\n".join(founder_checklist), encoding="utf-8")
        return {
            "weekly_review": weekly_path,
            "readiness_report": readiness_path,
            "operational_checklist": checklist_path,
            "founder_review_checklist": founder_checklist_path,
        }

    def run_signal_batch(self, *, input_file: Path, now: Optional[datetime] = None) -> Dict[str, Path]:
        now = now or datetime.now(timezone.utc)
        artifacts_root = self.config.artifacts_dir
        batch_items = CanonicalSignalBatchLoader().load(input_file)

        signal_layer = SignalLayer(artifacts_root=artifacts_root)
        raw_signals = [item.to_raw_signal() for item in batch_items]
        dedup_metadata = build_dedup_metadata(raw_signals)
        signals: List[Signal] = []
        for item, raw_signal in zip(batch_items, raw_signals):
            dedup = dedup_metadata[raw_signal.id or item.signal_id].to_dict()
            metadata = {**item.metadata(), "input_file": str(input_file.resolve()), **dedup}
            signals.append(signal_layer.ingest_raw_signal(raw_signal, metadata=metadata))

        eligible_signals = [signal for signal in canonical_signal_set(signals) if signal.status == SignalStatus.validated]
        if not eligible_signals:
            raise ValueError(
                "run-signal-batch refused: no validated signals found. "
                "Add at least one signal with recurring, specific pain and cost/workaround evidence."
            )

        router = ModelRouter(config_path=self.config.project_root / "config" / "model_routing.json")
        routing_selected = {stage: router.select(stage) for stage in router.config.rules_by_stage.keys()}

        framer = OpportunityFramer(store=signal_layer.router.store)
        opp = framer.frame_from_signals(
            eligible_signals,
            opportunity_id="opp_batch_1",
            initial_notes=f"Real signal batch imported from {input_file.name}.",
            opportunity_type="real_signal_batch",
        )

        ideation = build_ideation_engine(
            store=signal_layer.router.store,
            ai_enabled=self.config.ai_ideation_enabled,
            ai_response_json=self.config.ai_ideation_response_json,
        )
        ideas = ideation.generate(opp)

        screen = ScreenEvaluator(store=signal_layer.router.store)
        screened = []
        for idea in ideas:
            screened.append((idea, screen.evaluate(idea)))

        hyp_layer = HypothesisLayer(artifacts_root=artifacts_root)
        hyp_exp_pairs = []
        for idea, res in screened:
            out = hyp_layer.generate_for_screened_idea(idea, screen_outcome=res.outcome)
            if out is not None:
                hyp_exp_pairs.append(out)

        council = CouncilLayer(artifacts_root=artifacts_root)
        council_decisions = []
        for idea, res in screened:
            if res.outcome in {"pass", "park"}:
                council_decisions.append(council.generate_for_shortlisted_idea(idea))

        portfolio = PortfolioManager(artifacts_root=artifacts_root)
        outcomes = [res.outcome for _, res in screened]
        first_kill_reason = next((res.kill_reason_id for _, res in screened if res.kill_reason_id), None)
        transition_reason = f"Signal batch {now.isoformat(timespec='seconds')} [needs_review]"
        if "pass" in outcomes:
            portfolio.transition(opportunity_id=opp.id, to_state=PortfolioStateEnum.Active, reason=transition_reason)
        elif "park" in outcomes:
            portfolio.transition(opportunity_id=opp.id, to_state=PortfolioStateEnum.Parked, reason=transition_reason)
        else:
            portfolio.transition(
                opportunity_id=opp.id,
                to_state=PortfolioStateEnum.Killed,
                reason="Signal batch [recommend_kill]",
                linked_kill_reason_id=first_kill_reason,
            )

        weekly = WeeklyReviewGenerator(artifacts_root=artifacts_root)
        weekly_path = weekly.generate(now=now)

        ops_dir = artifacts_root / "ops"
        ops_dir.mkdir(parents=True, exist_ok=True)
        checklist_path = ops_dir / "v1_operational_checklist.txt"
        founder_checklist_path = ops_dir / "v1_founder_review_checklist.md"

        readiness_dir = artifacts_root / "readiness"
        readiness_dir.mkdir(parents=True, exist_ok=True)
        safe_ts = now.isoformat(timespec="seconds").replace(":", "-")
        readiness_path = readiness_dir / f"v1_readiness_{safe_ts}.json"
        readiness_payload = {
            "version": "v1",
            "generated_at": now.isoformat(timespec="seconds"),
            "source": "signal_batch",
            "input_file": str(input_file.resolve()),
            "routing": routing_selected,
            "artifacts_written": {
                "signals": [signal.id for signal in signals],
                "validated_signals": [signal.id for signal in eligible_signals],
                "opportunity": opp.id,
                "ideas": [idea.id for idea, _ in screened],
                "kills": [res.kill_reason_id for _, res in screened if res.kill_reason_id],
                "hypotheses": [hyp.id for hyp, _ in hyp_exp_pairs],
                "experiments": [exp.id for _, exp in hyp_exp_pairs],
                "council": [decision.id for decision in council_decisions],
                "portfolio": [f"ps_{opp.id}"],
                "weekly_review": weekly_path.name,
                "founder_review_checklist": founder_checklist_path.name,
            },
            "status": "ok",
            "notes": "Real signal batch run; downstream artifacts trace to input signal ids.",
        }
        readiness_path.write_text(json.dumps(readiness_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        checklist = [
            "OOS v1 Operational Checklist (signal batch)",
            "",
            f"1) Review imported signal artifacts from {input_file.name}.",
            "2) Review OpportunityCard source_signal_ids for input traceability.",
            "3) Review IdeaVariants, Screen outputs, Hypotheses, Experiments and CouncilDecision artifacts.",
            "4) Review PortfolioState and weekly review package.",
            "",
            "Founder remains the final decision maker (human-in-the-loop).",
        ]
        checklist_path.write_text("\n".join(checklist), encoding="utf-8")

        founder_checklist = [
            "# OOS v1 Founder Review Checklist",
            "",
            "## Review Objective",
            f"- Review the real signal batch imported from `{input_file.name}`.",
            f"- Start with readiness: `artifacts/readiness/{readiness_path.name}`.",
            f"- Use weekly review: `artifacts/weekly_reviews/{weekly_path.name}`.",
            "",
            "## Signals And Opportunity To Inspect",
            *[f"- Input signal: `artifacts/signals/{signal.id}.json`." for signal in signals],
            f"- Opportunity card: `artifacts/opportunities/{opp.id}.json`.",
            "",
            "## Founder Action Checklist",
            "- Confirm whether the source signals represent real, recurring pain.",
            "- Pick the cheapest next experiment to run this week.",
            "- Record any founder decision with a concrete reason.",
        ]
        founder_checklist_path.write_text("\n".join(founder_checklist), encoding="utf-8")
        review_entry = FounderReviewEntry(
            review_id="review-001",
            entity_type="opportunity",
            entity_id=opp.id,
            title=opp.title,
            summary=opp.pain_summary,
            decision_options=["pass", "park", "kill"],
            linked_signal_ids=opp.source_signal_ids,
            linked_artifact_ids={
                "opportunity": opp.id,
                "readiness_report": readiness_path.name,
                "weekly_review": weekly_path.name,
                "council": [decision.id for decision in council_decisions],
                "hypotheses": [hyp.id for hyp, _ in hyp_exp_pairs],
                "experiments": [exp.id for _, exp in hyp_exp_pairs],
                "kills": [res.kill_reason_id for _, res in screened if res.kill_reason_id],
                "portfolio": [f"ps_{opp.id}"],
            },
        )
        founder_review_paths = FounderReviewPackageWriter(artifacts_root=artifacts_root).write(
            entries=[review_entry],
            project_root=self.config.project_root,
        )

        return {
            "weekly_review": weekly_path,
            "readiness_report": readiness_path,
            "operational_checklist": checklist_path,
            "founder_review_checklist": founder_checklist_path,
            **founder_review_paths,
        }

    def run_weekly_cycle(self, *, input_file: Path, now: Optional[datetime] = None) -> Dict[str, Path]:
        return self.run_signal_batch(input_file=input_file, now=now)

