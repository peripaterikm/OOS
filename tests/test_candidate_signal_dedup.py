import json
import shutil
import unittest
from pathlib import Path

from oos.candidate_signal_dedup import deduplicate_candidate_signals, deduplicate_ranked_candidate_signals
from oos.discovery_weekly import run_discovery_weekly
from oos.models import CandidateSignal, RawEvidence, compute_raw_evidence_content_hash
from oos.weak_signal_aggregation import aggregate_weak_pattern_candidates


TMP_ROOT = Path("codex_tmp_candidate_signal_dedup")


def candidate_signal(
    signal_id: str,
    *,
    evidence_id: str | None = None,
    source_url: str | None = None,
    confidence: float = 0.42,
    source_id: str = "github_issues",
    cluster_key: str = "invoice_reconciliation",
    pain_summary: str = "Invoice reconciliation still takes manual spreadsheet work.",
) -> CandidateSignal:
    evidence_id = evidence_id or f"ev_{signal_id}"
    source_url = source_url or f"https://example.com/{source_id}/{signal_id}"
    signal = CandidateSignal(
        signal_id=signal_id,
        evidence_id=evidence_id,
        source_id=source_id,
        source_type=source_id,
        source_url=source_url,
        topic_id="ai_cfo_smb",
        query_kind="customer_voice_query",
        signal_type="pain_signal",
        pain_summary=pain_summary,
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
            "evidence_id": evidence_id,
            "source_url": source_url,
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


def raw_evidence(evidence_id: str, *, body: str, source_url: str) -> dict:
    title = "Finance workflow pain"
    evidence = RawEvidence(
        evidence_id=evidence_id,
        source_id="src_hacker_news_algolia",
        source_type="hacker_news_algolia",
        source_name="Hacker News",
        source_url=source_url,
        collected_at="2026-05-05T00:00:00+00:00",
        title=title,
        body=body,
        language="en",
        topic_id="ai_cfo_smb",
        query_kind="customer_voice_query",
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="small business operator",
        raw_metadata={"fixture": True},
        access_policy="fixture",
        collection_method="fixture",
    )
    return evidence.__dict__


class TestCandidateSignalDedup(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_duplicate_evidence_id_collapses_to_one_representative(self) -> None:
        result = deduplicate_candidate_signals(
            [
                candidate_signal("sig_a", evidence_id="raw_hn_47844178"),
                candidate_signal("sig_b", evidence_id="raw_hn_47844178"),
            ]
        )

        self.assertEqual(len(result.canonical_signals), 1)
        self.assertEqual(result.duplicate_signal_count, 1)

    def test_duplicate_signal_id_collapses_to_one_representative(self) -> None:
        result = deduplicate_candidate_signals(
            [
                candidate_signal("candidate_signal_raw_hn_47401563_pain_signal_candidate", evidence_id="ev_a"),
                candidate_signal("candidate_signal_raw_hn_47401563_pain_signal_candidate", evidence_id="ev_b"),
            ]
        )

        self.assertEqual(len(result.canonical_signals), 1)

    def test_duplicate_source_url_collapses_to_one_representative(self) -> None:
        duplicate_url = "https://news.ycombinator.com/item?id=47401563"
        result = deduplicate_candidate_signals(
            [
                candidate_signal("sig_a", evidence_id="ev_a", source_url=duplicate_url),
                candidate_signal("sig_b", evidence_id="ev_b", source_url=f"{duplicate_url}?utm_source=test"),
            ]
        )

        self.assertEqual(len(result.canonical_signals), 1)
        metadata = result.canonical_signals[0].scoring_breakdown["candidate_dedup"]
        self.assertEqual(metadata["duplicate_evidence_ids"], ["ev_a", "ev_b"])

    def test_higher_confidence_representative_is_kept(self) -> None:
        lower = candidate_signal("sig_lower", evidence_id="ev_dup", confidence=0.35)
        higher = candidate_signal("sig_higher", evidence_id="ev_dup", confidence=0.55)

        result = deduplicate_candidate_signals([lower, higher])

        self.assertEqual(result.canonical_signals[0].signal_id, "sig_higher")

    def test_first_occurrence_is_kept_on_confidence_tie(self) -> None:
        first = candidate_signal("sig_first", evidence_id="ev_dup", confidence=0.42)
        second = candidate_signal("sig_second", evidence_id="ev_dup", confidence=0.42)

        result = deduplicate_candidate_signals([first, second])

        self.assertEqual(result.canonical_signals[0].signal_id, "sig_first")

    def test_duplicate_metadata_is_preserved(self) -> None:
        result = deduplicate_candidate_signals(
            [
                candidate_signal("sig_a", evidence_id="raw_hn_47844178"),
                candidate_signal("sig_b", evidence_id="raw_hn_47844178"),
            ]
        )
        metadata = result.canonical_signals[0].scoring_breakdown["candidate_dedup"]

        self.assertEqual(metadata["duplicate_count"], 2)
        self.assertEqual(metadata["suppressed_duplicate_count"], 1)
        self.assertEqual(metadata["duplicate_signal_ids"], ["sig_a", "sig_b"])
        self.assertEqual(result.suppressed_duplicates[0].scoring_breakdown["candidate_dedup"]["canonical_signal_id"], "sig_a")

    def test_unique_signals_are_not_collapsed(self) -> None:
        result = deduplicate_candidate_signals(
            [
                candidate_signal("sig_a", evidence_id="ev_a", source_url="https://example.com/a"),
                candidate_signal("sig_b", evidence_id="ev_b", source_url="https://example.com/b"),
            ]
        )

        self.assertEqual(len(result.canonical_signals), 2)
        self.assertEqual(result.duplicate_signal_count, 0)

    def test_no_duplicate_inflation_in_founder_facing_output(self) -> None:
        project_root = TMP_ROOT / "project"
        project_root.mkdir(parents=True)
        duplicate_url = "https://news.ycombinator.com/item?id=47082761"
        evidence_path = project_root / "raw_evidence.json"
        evidence_path.write_text(
            json.dumps(
                {
                    "raw_evidence": [
                        raw_evidence(
                            "raw_hn_47082761",
                            source_url=duplicate_url,
                            body="When invoices go unpaid, I manually follow up by email and track the cash impact in a spreadsheet.",
                        ),
                        raw_evidence(
                            "raw_hn_47082761_duplicate",
                            source_url=duplicate_url,
                            body="When invoices go unpaid, I manually follow up by email and track the cash impact in a spreadsheet.",
                        ),
                    ]
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        result = run_discovery_weekly(
            project_root=project_root,
            topic_id="ai_cfo_smb",
            run_id="dedup_founder_package",
            input_raw_evidence=evidence_path.resolve(),
        )
        package = json.loads(result.artifact_paths["founder_discovery_package_json"].read_text(encoding="utf-8"))

        self.assertEqual(package["candidate_signal_count"], 2)
        self.assertEqual(package["canonical_candidate_signal_count"], 1)
        self.assertEqual(package["suppressed_duplicate_candidate_signal_count"], 1)
        self.assertEqual(len(package["top_candidate_signals"]), 1)
        self.assertEqual(package["top_candidate_signals"][0]["dedup"]["suppressed_duplicate_count"], 1)

    def test_weak_pattern_aggregation_does_not_count_exact_duplicates_as_independent_signals(self) -> None:
        duplicate_url = "https://news.ycombinator.com/item?id=47844178"
        signals = [
            candidate_signal("sig_1", source_id="hacker_news_algolia", source_url=duplicate_url),
            candidate_signal("sig_2", source_id="hacker_news_algolia", source_url=f"{duplicate_url}?ref=dupe"),
            candidate_signal("sig_3", source_id="github_issues"),
            candidate_signal("sig_4", source_id="stack_exchange"),
            candidate_signal("sig_5", source_id="github_issues", source_url="https://example.com/github/other"),
        ]

        self.assertEqual(aggregate_weak_pattern_candidates(signals), [])

    def test_ranked_dedup_keeps_existing_rank_order(self) -> None:
        duplicate_url = "https://news.ycombinator.com/item?id=12345"
        lower = candidate_signal("sig_lower", source_url=duplicate_url, confidence=0.35)
        higher = candidate_signal("sig_higher", source_url=duplicate_url, confidence=0.55)
        unique = candidate_signal("sig_unique", source_url="https://example.com/unique", confidence=0.5)

        ranked = deduplicate_ranked_candidate_signals([lower, higher, unique])

        self.assertEqual([signal.signal_id for signal in ranked], ["sig_higher", "sig_unique"])

    def test_no_live_network_or_llm_calls_are_made(self) -> None:
        source = Path("src/oos/candidate_signal_dedup.py").read_text(encoding="utf-8")

        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("provider.complete", source)


if __name__ == "__main__":
    unittest.main()
