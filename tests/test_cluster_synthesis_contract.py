import unittest
from pathlib import Path

from oos.cluster_synthesis import (
    CLUSTER_SYNTHESIS_TASK_TYPE,
    ClusterSynthesisInput,
    build_cluster_synthesis_input,
    build_cluster_synthesis_messages,
    build_cluster_synthesis_request,
    run_deterministic_cluster_synthesis_stub,
)
from oos.llm_contracts import LLMBudgetState, check_llm_budget, default_local_preview_llm_budget_policy
from oos.models import CandidateSignal, ClusterSynthesis, WeakPatternCandidate, model_from_dict, model_to_dict


def candidate_signal(
    signal_id: str,
    *,
    confidence: float = 0.42,
    source_id: str = "github_issues",
    cluster_key: str = "invoice_reconciliation",
) -> CandidateSignal:
    signal = CandidateSignal(
        signal_id=signal_id,
        evidence_id=f"ev_{signal_id}",
        source_id=source_id,
        source_type=source_id,
        source_url=f"https://example.com/{source_id}/{signal_id}",
        topic_id="ai_cfo_smb",
        query_kind="customer_voice_query",
        signal_type="pain_signal",
        pain_summary="Invoice reconciliation still takes manual spreadsheet work.",
        target_user="small_business_owner",
        current_workaround="manual spreadsheet",
        buying_intent_hint="unknown",
        urgency_hint="medium",
        confidence=confidence,
        measurement_methods={
            "signal_type": "rule_based",
            "pain_summary": "rule_based",
            "target_user": "rule_based",
            "current_workaround": "rule_based",
            "buying_intent_hint": "rule_based",
            "urgency_hint": "rule_based",
            "confidence": "rule_based",
        },
        extraction_mode="rule_based_v2",
        classification="pain_signal_candidate",
        classification_confidence=confidence,
        traceability={
            "evidence_id": f"ev_{signal_id}",
            "source_url": f"https://example.com/{source_id}/{signal_id}",
            "source_id": source_id,
            "topic_id": "ai_cfo_smb",
            "query_kind": "customer_voice_query",
            "weak_cluster_key": cluster_key,
        },
        scoring_model_version="signal_scoring_v2_embeddings_disabled",
        scoring_breakdown={"final_score": confidence, "weak_cluster_key": cluster_key},
    )
    signal.validate()
    return signal


def cluster_signals() -> list[CandidateSignal]:
    return [
        candidate_signal("sig_1", confidence=0.35, source_id="hacker_news_algolia"),
        candidate_signal("sig_2", confidence=0.48, source_id="github_issues"),
        candidate_signal("sig_3", confidence=0.39, source_id="stack_exchange"),
        candidate_signal("sig_4", confidence=0.44, source_id="github_issues"),
        candidate_signal("sig_5", confidence=0.41, source_id="hacker_news_algolia"),
        candidate_signal("sig_6", confidence=0.33, source_id="rss"),
    ]


def weak_pattern() -> WeakPatternCandidate:
    pattern = WeakPatternCandidate(
        pattern_id="weak_pattern_invoice_reconciliation",
        classification="weak_pattern_candidate",
        review_priority="elevated",
        signal_ids=[f"sig_{index}" for index in range(1, 7)],
        signal_count=6,
        avg_confidence=0.4,
        max_confidence=0.48,
        source_diversity=4,
        sources=["github_issues", "hacker_news_algolia", "rss", "stack_exchange"],
        evidence_ids=[f"ev_sig_{index}" for index in range(1, 7)],
        summary="Repeated weak invoice reconciliation pattern.",
        confidence=0.4,
        cluster_key="invoice_reconciliation",
    )
    pattern.validate()
    return pattern


class TestClusterSynthesisContract(unittest.TestCase):
    def test_cluster_synthesis_model_exists_and_serializes(self) -> None:
        synthesis_input = build_cluster_synthesis_input(
            cluster_id="cluster_invoice_reconciliation",
            topic_id="ai_cfo_smb",
            candidate_signals=cluster_signals(),
            weak_pattern=weak_pattern(),
        )
        synthesis = run_deterministic_cluster_synthesis_stub(synthesis_input)
        loaded = model_from_dict(ClusterSynthesis, model_to_dict(synthesis))

        self.assertEqual(loaded, synthesis)
        self.assertEqual(loaded.cluster_id, "cluster_invoice_reconciliation")

    def test_deterministic_stub_returns_stable_output(self) -> None:
        signals = cluster_signals()
        first = run_deterministic_cluster_synthesis_stub(
            build_cluster_synthesis_input(cluster_id="cluster_invoice_reconciliation", topic_id="ai_cfo_smb", candidate_signals=list(reversed(signals)))
        )
        second = run_deterministic_cluster_synthesis_stub(
            build_cluster_synthesis_input(cluster_id="cluster_invoice_reconciliation", topic_id="ai_cfo_smb", candidate_signals=signals)
        )

        self.assertEqual(first, second)
        self.assertIn("Invoice reconciliation", first.emerging_pain_pattern)

    def test_evidence_ids_are_preserved_and_strongest_selected_deterministically(self) -> None:
        synthesis = run_deterministic_cluster_synthesis_stub(
            build_cluster_synthesis_input(cluster_id="cluster_invoice_reconciliation", topic_id="ai_cfo_smb", candidate_signals=cluster_signals())
        )

        self.assertEqual(synthesis.strongest_evidence_ids, ["ev_sig_2", "ev_sig_4", "ev_sig_5"])
        self.assertEqual([item["evidence_id"] for item in synthesis.evidence_cited], synthesis.strongest_evidence_ids)
        self.assertEqual(synthesis.signal_ids, ["sig_2", "sig_4", "sig_5", "sig_3", "sig_1", "sig_6"])

    def test_prompt_contains_cluster_context_and_multiple_signals(self) -> None:
        synthesis_input = build_cluster_synthesis_input(
            cluster_id="cluster_invoice_reconciliation",
            topic_id="ai_cfo_smb",
            candidate_signals=cluster_signals(),
        )
        prompt_text = "\n".join(message.content for message in build_cluster_synthesis_messages(synthesis_input))

        self.assertIn("cluster-level synthesis", prompt_text)
        self.assertIn("do not summarize an isolated single signal", prompt_text)
        self.assertIn('"cluster_context"', prompt_text)
        self.assertIn("sig_1", prompt_text)
        self.assertIn("sig_6", prompt_text)
        self.assertIn("Preserve evidence IDs exactly", prompt_text)

    def test_prompt_rejects_isolated_signal_only_context(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 5 signals"):
            build_cluster_synthesis_input(
                cluster_id="cluster_too_small",
                topic_id="ai_cfo_smb",
                candidate_signals=[candidate_signal("sig_1")],
            )

    def test_no_provider_llm_call_is_made(self) -> None:
        source = Path("src/oos/cluster_synthesis.py").read_text(encoding="utf-8")

        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("provider.complete", source)

    def test_cluster_synthesis_budget_role_exists(self) -> None:
        synthesis_input = build_cluster_synthesis_input(
            cluster_id="cluster_invoice_reconciliation",
            topic_id="ai_cfo_smb",
            candidate_signals=cluster_signals(),
        )
        request = build_cluster_synthesis_request(synthesis_input)
        allowed, reasons = check_llm_budget(default_local_preview_llm_budget_policy(), LLMBudgetState(), request, estimated_output_tokens=100)

        self.assertEqual(request.task_type, CLUSTER_SYNTHESIS_TASK_TYPE)
        self.assertTrue(allowed)
        self.assertEqual(reasons, [])


if __name__ == "__main__":
    unittest.main()
