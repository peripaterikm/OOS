import json
import shutil
import unittest
from pathlib import Path

from oos.founder_package import build_founder_package_quality_sections, render_founder_package_quality_sections
from oos.models import CandidateSignal, WeakPatternCandidate, model_from_dict, model_to_dict
from oos.weak_signal_aggregation import aggregate_weak_pattern_candidates


TMP_ROOT = Path("codex_tmp_weak_signal_aggregation")


def candidate_signal(
    signal_id: str,
    *,
    confidence: float = 0.42,
    source_id: str = "github_issues",
    cluster_key: str = "invoice_reconciliation",
    summary: str = "Invoice reconciliation still takes manual spreadsheet work.",
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
        pain_summary=summary,
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


def qualifying_signals(*, cluster_key: str = "invoice_reconciliation") -> list[CandidateSignal]:
    return [
        candidate_signal("sig_5", source_id="github_issues", confidence=0.41, cluster_key=cluster_key),
        candidate_signal("sig_1", source_id="hacker_news_algolia", confidence=0.35, cluster_key=cluster_key),
        candidate_signal("sig_3", source_id="github_issues", confidence=0.48, cluster_key=cluster_key),
        candidate_signal("sig_2", source_id="stack_exchange", confidence=0.39, cluster_key=cluster_key),
        candidate_signal("sig_4", source_id="hacker_news_algolia", confidence=0.44, cluster_key=cluster_key),
    ]


class TestWeakSignalAggregation(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_weak_pattern_model_exists_and_serializes(self) -> None:
        candidate = aggregate_weak_pattern_candidates(qualifying_signals())[0]
        loaded = model_from_dict(WeakPatternCandidate, model_to_dict(candidate))

        self.assertEqual(loaded, candidate)
        self.assertEqual(candidate.classification, "weak_pattern_candidate")
        self.assertEqual(candidate.review_priority, "elevated")

    def test_five_weak_signals_from_multiple_sources_elevate(self) -> None:
        candidates = aggregate_weak_pattern_candidates(qualifying_signals())

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].signal_count, 5)
        self.assertEqual(candidates[0].source_diversity, 3)
        self.assertEqual(candidates[0].classification, "weak_pattern_candidate")
        self.assertEqual(candidates[0].review_priority, "elevated")

    def test_average_confidence_threshold_is_enforced(self) -> None:
        weak_signals = qualifying_signals()
        too_low = [candidate_signal(signal.signal_id, confidence=0.25, source_id=signal.source_id) for signal in weak_signals]

        self.assertEqual(aggregate_weak_pattern_candidates(too_low), [])

    def test_max_confidence_must_remain_below_threshold(self) -> None:
        signals = qualifying_signals()
        signals[0] = candidate_signal("sig_5", source_id="github_issues", confidence=0.60)

        self.assertEqual(aggregate_weak_pattern_candidates(signals), [])

    def test_source_diversity_threshold_is_enforced(self) -> None:
        same_source = [candidate_signal(f"sig_{index}", source_id="github_issues") for index in range(5)]

        self.assertEqual(aggregate_weak_pattern_candidates(same_source), [])

    def test_single_weak_signal_does_not_elevate(self) -> None:
        self.assertEqual(aggregate_weak_pattern_candidates([candidate_signal("sig_1")]), [])

    def test_ids_sources_and_evidence_are_preserved(self) -> None:
        candidate = aggregate_weak_pattern_candidates(qualifying_signals())[0]

        self.assertEqual(candidate.signal_ids, ["sig_1", "sig_2", "sig_3", "sig_4", "sig_5"])
        self.assertEqual(candidate.evidence_ids, ["ev_sig_1", "ev_sig_2", "ev_sig_3", "ev_sig_4", "ev_sig_5"])
        self.assertEqual(candidate.sources, ["github_issues", "hacker_news_algolia", "stack_exchange"])

    def test_output_ordering_is_deterministic(self) -> None:
        low = qualifying_signals(cluster_key="low_priority_pattern")
        high = [candidate_signal(f"high_{index}", source_id=("github_issues" if index % 2 else "stack_exchange"), confidence=0.5, cluster_key="high_priority_pattern") for index in range(5)]
        first = aggregate_weak_pattern_candidates(list(reversed(low + high)))
        second = aggregate_weak_pattern_candidates(high + low)

        self.assertEqual([item.pattern_id for item in first], [item.pattern_id for item in second])
        self.assertEqual(first[0].pattern_id, "weak_pattern_high_priority_pattern")

    def test_founder_package_can_render_weak_pattern_candidates(self) -> None:
        run_dir = TMP_ROOT / "run"
        run_dir.mkdir(parents=True)
        candidate = aggregate_weak_pattern_candidates(qualifying_signals())[0]
        (run_dir / "weak_pattern_candidates.json").write_text(
            json.dumps({"items": [model_to_dict(candidate)]}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        sections = build_founder_package_quality_sections(
            candidate_signals=[],
            classifications=[],
            price_signals=[],
            run_dir=run_dir,
            collection_metadata={},
        )
        markdown = render_founder_package_quality_sections(sections)

        self.assertEqual(sections["sections"]["weak_pattern_candidates"]["count"], 1)
        self.assertIn("### Weak Pattern Candidates", markdown)
        self.assertIn("Weak pattern across 5 signals", markdown)

    def test_no_live_network_or_llm_calls(self) -> None:
        source = Path("src/oos/weak_signal_aggregation.py").read_text(encoding="utf-8")

        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("provider.complete", source)


if __name__ == "__main__":
    unittest.main()
