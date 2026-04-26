from __future__ import annotations

import inspect
import io
import json
import shutil
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path

from oos import (
    ai_council_critique,
    anti_pattern_checks,
    contradiction_detection,
    ideation_mode_comparison,
    opportunity_framing,
    pattern_guided_ideation,
    semantic_clustering,
    signal_understanding,
)
from oos.ai_council_critique import COUNCIL_ROLES, StaticCouncilRoleProvider, run_isolated_council_critique
from oos.anti_pattern_checks import check_anti_patterns
from oos.cli import main
from oos.contradiction_detection import (
    StaticContradictionDetectionProvider,
    detect_contradictions,
    write_contradiction_report_artifact,
)
from oos.evaluation_dataset import load_evaluation_dataset_v1
from oos.founder_ai_stage_rating import record_ai_stage_rating
from oos.founder_review_package import FounderReviewEntry, FounderReviewPackageWriter
from oos.ideation_mode_comparison import compare_ideation_modes
from oos.opportunity_framing import StaticOpportunityFramingProvider, frame_opportunities, write_opportunity_framing_artifacts
from oos.opportunity_quality_gate import evaluate_opportunity_batch
from oos.pattern_guided_ideation import StaticPatternGuidedIdeationProvider, generate_pattern_guided_ideas
from oos.semantic_clustering import StaticSemanticClusteringProvider, cluster_canonical_signals, write_semantic_cluster_artifacts
from oos.signal_dedup import build_dedup_metadata, canonical_signal_set
from oos.signal_understanding import StaticSignalUnderstandingProvider, extract_signal_understanding, write_signal_understanding_artifacts
from oos.weekly_review import WeeklyReviewGenerator
from tests.test_contradiction_detection import valid_contradiction, valid_merge_candidate
from tests.test_pattern_guided_ideation import idea_payload
from tests.test_semantic_clustering import make_signal, valid_cluster
from tests.test_signal_understanding import valid_item


FORBIDDEN_LIVE_PROVIDER_TOKENS = (
    "OpenAI(",
    "Anthropic(",
    "requests.post",
    "httpx.post",
    "chat.completions",
    "responses.create",
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _council_payload(role_id: str, *, idea_id: str, linked_signal_ids: list[str], linked_opportunity_id: str) -> dict:
    return {
        "role": role_id,
        "idea_id": idea_id,
        "risks": ["Buyer urgency may be episodic without a recurring close process."],
        "kill_candidates": ["If owners will not share source financial data, the wedge dies."],
        "unsupported_claims": ["Willingness to pay is not proven by the signal set yet."],
        "weakest_assumption": "The owner will pay for trust restoration before full automation exists.",
        "recommendation": "needs more evidence",
        "explanation": "Role-specific critique is isolated, traceable, and advisory.",
        "confidence": 0.76,
        "linked_signal_ids": linked_signal_ids,
        "linked_opportunity_id": linked_opportunity_id,
    }


class TestFullAIMeaningLoopVerification(unittest.TestCase):
    def test_full_ai_meaning_loop_preserves_traceability_without_live_llm_calls(self) -> None:
        dataset_v1 = load_evaluation_dataset_v1()
        self.assertGreaterEqual(len(dataset_v1), 20)
        self.assertTrue(all(signal.get("synthetic") is True for signal in dataset_v1))

        raw_signals = [
            make_signal("sig_1", pain="owner cannot trust weekly financial reports"),
            make_signal("sig_dup", pain="owner cannot trust weekly financial reports", duplicate=True, canonical_id="sig_1"),
            make_signal("sig_2", pain="reconciliation narrative preparation is too slow"),
        ]
        dedup_metadata = build_dedup_metadata(raw_signals)
        canonical_signals = canonical_signal_set(raw_signals)
        canonical_ids = [signal.id for signal in canonical_signals]

        self.assertEqual(["sig_1", "sig_2"], canonical_ids)
        self.assertEqual(len(raw_signals), 3)
        self.assertTrue(dedup_metadata["sig_dup"].is_duplicate)
        self.assertEqual(dedup_metadata["sig_dup"].canonical_signal_id, "sig_1")

        understanding = extract_signal_understanding(
            signals=canonical_signals,
            provider=StaticSignalUnderstandingProvider(payload=[valid_item("sig_1"), valid_item("sig_2")]),
        )
        self.assertEqual(understanding.valid_count, 2)
        self.assertEqual([record.signal_id for record in understanding.records], canonical_ids)
        self.assertTrue(all(record.ai_metadata["linked_input_ids"] == [record.signal_id] for record in understanding.records))

        clusters = cluster_canonical_signals(
            signals=raw_signals,
            provider=StaticSemanticClusteringProvider(payload=[valid_cluster(signal_ids=canonical_ids)]),
        )
        self.assertEqual(clusters.processed_canonical_signal_ids, canonical_ids)
        self.assertEqual(clusters.skipped_duplicate_signal_ids, ["sig_dup"])
        self.assertEqual(clusters.clusters[0].linked_canonical_signal_ids, canonical_ids)
        self.assertNotIn("sig_dup", clusters.clusters[0].linked_canonical_signal_ids)

        contradiction_report = detect_contradictions(
            signals=raw_signals,
            understanding_records=understanding.records,
            semantic_clusters=clusters.clusters,
            provider=StaticContradictionDetectionProvider(
                payload={
                    "contradictions": [valid_contradiction(signal_ids=canonical_ids, canonical_signal_ids=canonical_ids)],
                    "merge_candidates": [
                        valid_merge_candidate(signal_ids=canonical_ids, canonical_signal_id="sig_1", do_not_auto_merge=True)
                    ],
                }
            ),
        )
        self.assertEqual(contradiction_report.source_signal_ids, ["sig_1", "sig_dup", "sig_2"])
        self.assertTrue(contradiction_report.merge_candidates[0].do_not_auto_merge)
        self.assertEqual(contradiction_report.contradictions[0].canonical_signal_ids, canonical_ids)

        opportunity_payload = {
            "opportunities": [
                {
                    "opportunity_id": "opp_reporting_trust",
                    "title": "Weekly reconciliation narratives",
                    "target_user": "SMB owner-operators",
                    "pain": "Owners do not trust weekly financial reports when balances diverge.",
                    "current_workaround": "Manually compare exports and bank balances in spreadsheets.",
                    "why_it_matters": "Trust gaps delay cash decisions and create repeated founder anxiety.",
                    "evidence": [
                        {
                            "evidence_id": "ev_reporting_trust",
                            "claim": "Owners need trust-restoring reconciliation context.",
                            "source_signal_ids": canonical_ids,
                            "source_cluster_id": "cluster_ops",
                        }
                    ],
                    "urgency": "Weekly reporting cadence creates recurring urgency.",
                    "possible_wedge": "Start with a weekly reconciliation narrative before dashboards.",
                    "monetization_hypothesis": "Charge a monthly subscription for owner-ready reconciliation reports.",
                    "risks": ["May look like bookkeeping unless the narrative wedge is clear."],
                    "assumptions": [
                        {
                            "assumption_id": "asm_budget",
                            "statement": "Owners will pay for trust restoration.",
                            "reason": "Budget not proven yet.",
                        }
                    ],
                    "non_obvious_angle": (
                        "The wedge is not another dashboard; it is restoring owner trust through recurring reconciliation narratives."
                    ),
                    "linked_cluster_id": "cluster_ops",
                    "linked_signal_ids": canonical_ids,
                    "linked_canonical_signal_ids": canonical_ids,
                    "confidence": 0.84,
                }
            ]
        }
        opportunities = frame_opportunities(
            clusters=clusters.clusters,
            signals=raw_signals,
            understanding_records=understanding.records,
            contradiction_report=contradiction_report,
            provider=StaticOpportunityFramingProvider(payload=opportunity_payload),
        )
        opportunity = opportunities.opportunities[0]
        self.assertEqual(opportunity.linked_cluster_id, clusters.clusters[0].cluster_id)
        self.assertEqual(opportunity.linked_signal_ids, canonical_ids)
        self.assertFalse(opportunity.evidence_missing)

        gate = evaluate_opportunity_batch(opportunities.opportunities)
        self.assertEqual(gate.decisions[0].status, "pass")
        self.assertEqual(gate.decisions[0].linked_signal_ids, canonical_ids)
        self.assertIsNone(gate.decisions[0].founder_override_status)

        ideation = generate_pattern_guided_ideas(
            opportunities=opportunities.opportunities,
            provider=StaticPatternGuidedIdeationProvider(
                payload={
                    "ideas": [
                        idea_payload("idea_saas", "SaaS / tool"),
                        idea_payload("idea_service", "service-assisted workflow"),
                        idea_payload("idea_radar", "audit / risk radar"),
                    ]
                }
            ),
        )
        self.assertEqual(len(ideation.ideas), 3)
        self.assertFalse(ideation.low_diversity_warning)
        self.assertTrue(all(idea.linked_opportunity_id == opportunity.opportunity_id for idea in ideation.ideas))
        self.assertTrue(all(idea.linked_signal_ids == canonical_ids for idea in ideation.ideas))

        comparison = compare_ideation_modes(
            ideas_by_mode={"pattern_guided": ideation.ideas},
            valid_opportunity_ids=[opportunity.opportunity_id],
            expected_signal_ids_by_opportunity={opportunity.opportunity_id: canonical_ids},
        )
        self.assertTrue(all(score.schema_valid and score.traceability_valid for score in comparison.scores))
        self.assertTrue(any(score.recommendation == "candidate_for_council_review" for score in comparison.scores))

        anti_patterns = check_anti_patterns(ideation.ideas)
        self.assertEqual([result.idea_id for result in anti_patterns.results], [idea.idea_id for idea in ideation.ideas])

        top_idea = ideation.ideas[0]
        council = run_isolated_council_critique(
            ideas=[top_idea],
            scores=[comparison.scores[0]],
            providers_by_role={
                role.role_id: StaticCouncilRoleProvider(
                    {
                        role.role_id: _council_payload(
                            role.role_id,
                            idea_id=top_idea.idea_id,
                            linked_signal_ids=canonical_ids,
                            linked_opportunity_id=opportunity.opportunity_id,
                        )
                    }
                )
                for role in COUNCIL_ROLES
            },
        )
        self.assertEqual(council.selected_idea_ids[:1], [top_idea.idea_id])
        self.assertTrue(council.founder_final_authority)
        self.assertFalse(council.summaries[0].suspiciously_clean)
        self.assertFalse(council.critique_unavailable)

        project_root = Path("artifacts") / "_test_full_ai_meaning_loop"
        if project_root.exists():
            shutil.rmtree(project_root, ignore_errors=True)
        try:
            project_root.mkdir(parents=True, exist_ok=True)
            artifacts_root = project_root / "artifacts"
            for signal in raw_signals:
                payload = asdict(signal)
                payload["status"] = signal.status.value
                _write_json(artifacts_root / "signals" / f"{signal.id}.json", payload)

            understanding_path = write_signal_understanding_artifacts(understanding, artifacts_root)
            cluster_path = write_semantic_cluster_artifacts(clusters, artifacts_root)
            contradiction_path = write_contradiction_report_artifact(contradiction_report, artifacts_root)
            opportunity_path = write_opportunity_framing_artifacts(opportunities, artifacts_root)
            _write_json(artifacts_root / "opportunity_gate" / "opportunity_gate_result.json", gate.to_dict())
            _write_json(artifacts_root / "ideas" / "pattern_guided_ideas.json", ideation.to_dict())
            _write_json(artifacts_root / "ideation_mode_comparison" / "comparison.json", comparison.to_dict())
            _write_json(artifacts_root / "anti_patterns" / "anti_pattern_summary.json", anti_patterns.to_dict())
            _write_json(artifacts_root / "council" / "council_run_result.json", council.to_dict())

            rating_path = record_ai_stage_rating(
                project_root=project_root,
                stage="ideation",
                rating="good",
                explanation="Pattern-guided ideas preserved traceability and gave multiple product shapes.",
                linked_artifact_ids=["pattern_guided_ideas", "ideation_mode_comparison"],
                linked_signal_ids=canonical_ids,
                rating_id="ai_stage_rating_ideation_good_loop",
            )
            review_entry = FounderReviewEntry(
                review_id="review-ai-loop-001",
                entity_type="opportunity",
                entity_id=opportunity.opportunity_id,
                title=opportunity.title,
                summary=opportunity.why_it_matters,
                decision_options=["pass", "park", "kill"],
                linked_signal_ids=canonical_ids,
                linked_artifact_ids={
                    "signals": canonical_ids,
                    "semantic_clusters": [clusters.clusters[0].cluster_id],
                    "opportunities": [opportunity.opportunity_id],
                    "ideas": [idea.idea_id for idea in ideation.ideas],
                    "anti_patterns": ["anti_pattern_summary"],
                    "council": ["council_run_result"],
                    "ai_quality": ["ai_stage_rating_ideation_good_loop"],
                },
            )
            package_paths = FounderReviewPackageWriter(artifacts_root).write(entries=[review_entry], project_root=project_root)
            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "record-founder-review",
                        "--project-root",
                        str(project_root),
                        "--review-id",
                        "review-ai-loop-001",
                        "--decision",
                        "pass",
                    ]
                )
            weekly_path = WeeklyReviewGenerator(artifacts_root).generate()

            self.assertEqual(exit_code, 0)
            self.assertTrue((artifacts_root / "founder_review" / "inbox.md").exists())
            self.assertTrue((artifacts_root / "founder_review" / "sections" / "ai_quality.md").exists())
            self.assertTrue((artifacts_root / "founder_reviews").exists())
            self.assertTrue(rating_path.exists())
            weekly = json.loads(weekly_path.read_text(encoding="utf-8"))
            self.assertEqual(weekly["recent_ai_stage_ratings"][0]["rating_id"], "ai_stage_rating_ideation_good_loop")
            self.assertEqual(weekly["recent_ai_stage_ratings"][0]["linked_signal_ids"], canonical_ids)
            self.assertEqual(weekly["recent_founder_reviews"][0]["review_id"], "review-ai-loop-001")
            self.assertIn("founder_review_v2_index", package_paths)
            self.assertTrue(understanding_path.exists())
            self.assertTrue(cluster_path.exists())
            self.assertTrue(contradiction_path.exists())
            self.assertTrue(opportunity_path.exists())
        finally:
            shutil.rmtree(project_root, ignore_errors=True)

        llm_call_report = {
            "live_llm_calls": 0,
            "provider_boundary": "static_stubbed_providers_only",
            "stubbed_provider_stages": [
                "signal_understanding",
                "semantic_clustering",
                "contradiction_detection",
                "opportunity_framing",
                "pattern_guided_ideation",
                "isolated_ai_council_critique",
            ],
        }
        self.assertEqual(llm_call_report["live_llm_calls"], 0)
        self.assertTrue(all(record.ai_metadata["prompt_name"] for record in understanding.records))
        self.assertTrue(all(cluster.ai_metadata["prompt_name"] for cluster in clusters.clusters))
        self.assertTrue(all(idea.ai_metadata["prompt_name"] for idea in ideation.ideas))

        for module in (
            signal_understanding,
            semantic_clustering,
            contradiction_detection,
            opportunity_framing,
            pattern_guided_ideation,
            ideation_mode_comparison,
            anti_pattern_checks,
            ai_council_critique,
        ):
            source = inspect.getsource(module)
            for forbidden in FORBIDDEN_LIVE_PROVIDER_TOKENS:
                self.assertNotIn(forbidden, source, module.__name__)


if __name__ == "__main__":
    unittest.main()
