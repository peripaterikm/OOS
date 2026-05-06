import json
import shutil
import unittest
from pathlib import Path

from oos.evidence_pack import evidence_pack_from_dict, evidence_pack_to_dict
from oos.evidence_pack_builder import (
    EvidencePackBuilder,
    build_evidence_pack_from_signals,
    build_evidence_packs_for_clusters,
    build_evidence_packs_from_discovery_artifacts,
    link_kill_warnings_by_evidence_id,
    link_price_signals_by_evidence_id,
    read_evidence_packs,
    summarize_source_diversity,
    write_evidence_packs,
)
from oos.models import CandidateSignal, PriceSignal, WeakPatternCandidate, model_to_dict


class EvidencePackBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp_root = Path.cwd() / "codex_tmp_evidence_pack_builder_tests"
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)
        self.tmp_root.mkdir(parents=True)

    def tearDown(self):
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)

    def test_builder_creates_evidence_pack_from_candidate_signals(self):
        pack = build_evidence_pack_from_signals(
            cluster_id="cluster_cash_collection",
            candidate_signals=[_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")],
        )

        self.assertEqual(pack.cluster_id, "cluster_cash_collection")
        self.assertEqual(pack.topic_id, "ai_cfo_smb")
        self.assertEqual(pack.recurrence_count, 2)
        self.assertEqual(pack.source_diversity, 2)
        pack.validate()

    def test_evidence_urls_and_signal_ids_are_preserved(self):
        signals = [_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")]

        pack = build_evidence_pack_from_signals(cluster_id="cluster_traceability", candidate_signals=signals)

        self.assertEqual(pack.evidence_ids, ["evidence_a", "evidence_b"])
        self.assertEqual(pack.source_signal_ids, ["signal_a", "signal_b"])
        self.assertEqual(pack.source_urls, ["https://example.com/evidence_a", "https://example.com/evidence_b"])
        self.assertEqual([item.evidence_id for item in pack.items], ["evidence_a", "evidence_b"])

    def test_price_signals_are_linked_by_evidence_id(self):
        price_signal = _price_signal("price_a", "evidence_a")

        pack = build_evidence_pack_from_signals(
            cluster_id="cluster_price",
            candidate_signals=[_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")],
            price_signals=[price_signal, _price_signal("price_unrelated", "evidence_other")],
        )

        self.assertEqual(pack.price_signal_ids, ["price_a"])
        self.assertEqual(link_price_signals_by_evidence_id([price_signal], ["evidence_a"]), ["price_a"])

    def test_weak_pattern_id_is_preserved_when_available(self):
        signals = [_signal(f"signal_{index}", f"evidence_{index}", "hn" if index % 2 else "github_issue") for index in range(5)]
        weak_pattern = _weak_pattern(signals)

        packs = build_evidence_packs_for_clusters(candidate_signals=signals, weak_patterns=[weak_pattern])

        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0].weak_pattern_ids, ["weak_pattern_cash_collection"])
        self.assertEqual(packs[0].cluster_id, "cash_collection")

    def test_kill_warning_ids_are_preserved_when_available(self):
        warning = {
            "warning_id": "kill_warning_a",
            "signal_id": "signal_a",
            "evidence_id": "evidence_a",
            "summary": "Similar killed invoice tool warning.",
        }

        pack = build_evidence_pack_from_signals(
            cluster_id="cluster_kill",
            candidate_signals=[_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")],
            kill_warnings=[warning],
        )

        self.assertEqual(pack.kill_warning_ids, ["kill_warning_a"])
        self.assertEqual(link_kill_warnings_by_evidence_id([warning], ["evidence_a"], ["signal_a"]), ["kill_warning_a"])
        self.assertIn("kill_archive_warning", [note.risk_type for note in pack.risk_notes])

    def test_source_diversity_and_source_summaries_are_deterministic(self):
        signals = [_signal("signal_b", "evidence_b", "github_issue"), _signal("signal_a", "evidence_a", "hn")]

        pack = build_evidence_pack_from_signals(cluster_id="cluster_sources", candidate_signals=signals)

        self.assertEqual(summarize_source_diversity(signals), 2)
        self.assertEqual([summary.source_type for summary in pack.source_summaries], ["github_issue", "hn"])

    def test_risk_notes_are_generated_for_insufficient_evidence(self):
        pack = build_evidence_pack_from_signals(
            cluster_id="cluster_singleton",
            candidate_signals=[_signal("signal_a", "evidence_a", "hn")],
        )

        self.assertIn("insufficient_evidence_count", [note.risk_type for note in pack.risk_notes])
        self.assertIn("single_source_type", [note.risk_type for note in pack.risk_notes])

    def test_needs_human_review_produces_risk_note(self):
        pack = build_evidence_pack_from_signals(
            cluster_id="cluster_review",
            candidate_signals=[
                _signal("signal_a", "evidence_a", "hn", signal_type="needs_human_review", classification="needs_human_review"),
                _signal("signal_b", "evidence_b", "github_issue"),
            ],
        )

        self.assertIn("needs_human_review", [note.risk_type for note in pack.risk_notes])

    def test_duplicate_metadata_does_not_inflate_recurrence(self):
        signals = [
            _signal("signal_low", "evidence_a", "hn", confidence=0.4),
            _signal("signal_high", "evidence_a", "hn", confidence=0.7),
        ]

        pack = build_evidence_pack_from_signals(cluster_id="cluster_duplicates", candidate_signals=signals)

        self.assertEqual(pack.recurrence_count, 1)
        self.assertEqual(pack.source_signal_ids, ["signal_high"])
        self.assertIn("duplicate_collapsed", [note.risk_type for note in pack.risk_notes])

    def test_output_ordering_is_deterministic(self):
        signals = [_signal("signal_b", "evidence_b", "github_issue"), _signal("signal_a", "evidence_a", "hn")]

        first = evidence_pack_to_dict(build_evidence_pack_from_signals(cluster_id="cluster_order", candidate_signals=signals))
        second = evidence_pack_to_dict(
            build_evidence_pack_from_signals(cluster_id="cluster_order", candidate_signals=list(reversed(signals)))
        )

        self.assertEqual(first, second)

    def test_output_round_trips_through_evidence_pack_serialization(self):
        pack = build_evidence_pack_from_signals(
            cluster_id="cluster_roundtrip",
            candidate_signals=[_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")],
        )

        restored = evidence_pack_from_dict(json.loads(json.dumps(evidence_pack_to_dict(pack), sort_keys=True)))

        self.assertEqual(restored, pack)

    def test_builder_reads_existing_discovery_artifacts(self):
        run_dir = self.tmp_root / "discovery_run"
        run_dir.mkdir()
        signals = [_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")]
        (run_dir / "candidate_signals.json").write_text(
            json.dumps([model_to_dict(signal) for signal in signals]),
            encoding="utf-8",
        )
        (run_dir / "price_signals.json").write_text(
            json.dumps([model_to_dict(_price_signal("price_a", "evidence_a"))]),
            encoding="utf-8",
        )
        (run_dir / "weak_pattern_candidates.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        (run_dir / "kill_archive_warnings.json").write_text(
            json.dumps({"items": [{"warning_id": "kill_a", "signal_id": "signal_b", "evidence_id": "evidence_b"}]}),
            encoding="utf-8",
        )

        packs = build_evidence_packs_from_discovery_artifacts(run_dir)

        self.assertEqual(len(packs), 1)
        self.assertEqual(sum(len(pack.price_signal_ids) for pack in packs), 1)
        self.assertEqual(sum(len(pack.kill_warning_ids) for pack in packs), 1)

    def test_builder_writes_and_reads_evidence_pack_artifact(self):
        pack = build_evidence_pack_from_signals(
            cluster_id="cluster_artifact",
            candidate_signals=[_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")],
        )

        path = self.tmp_root / "evidence_packs.json"
        write_evidence_packs(path, [pack])

        restored = read_evidence_packs(path)

        self.assertEqual(restored, [pack])

    def test_class_api_builds_cluster_packs(self):
        builder = EvidencePackBuilder()

        packs = builder.build_for_clusters(
            candidate_signals=[_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")]
        )

        self.assertEqual(len(packs), 1)

    def test_no_live_network_or_llm_calls_are_made(self):
        pack = build_evidence_pack_from_signals(
            cluster_id="cluster_safe",
            candidate_signals=[_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")],
        )

        payload = json.dumps(evidence_pack_to_dict(pack), sort_keys=True)
        self.assertNotIn("provider.complete", payload)
        self.assertNotIn("allow_live_network", payload)


def _signal(
    signal_id,
    evidence_id,
    source_type,
    *,
    confidence=0.62,
    signal_type="pain_signal",
    classification="pain_signal_candidate",
):
    return CandidateSignal(
        signal_id=signal_id,
        evidence_id=evidence_id,
        source_id=f"{source_type}_source",
        source_type=source_type,
        source_url=f"https://example.com/{evidence_id}",
        topic_id="ai_cfo_smb",
        query_kind="pain",
        signal_type=signal_type,
        pain_summary=f"{evidence_id} describes SMB finance workflow pain.",
        target_user="small business operator",
        current_workaround="manual spreadsheet follow-up",
        buying_intent_hint="not_detected",
        urgency_hint="not_detected",
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
        extraction_mode="rule_based_candidate_signal_v1",
        classification=classification,
        classification_confidence=confidence,
        traceability={
            "evidence_id": evidence_id,
            "source_url": f"https://example.com/{evidence_id}",
            "source_id": f"{source_type}_source",
            "topic_id": "ai_cfo_smb",
            "query_kind": "pain",
        },
        scoring_breakdown={"cluster_key": "cash_collection"},
    )


def _price_signal(price_signal_id, evidence_id):
    return PriceSignal(
        price_signal_id=price_signal_id,
        evidence_id=evidence_id,
        source_id="hn_source",
        source_type="hn",
        source_url=f"https://example.com/{evidence_id}",
        topic_id="ai_cfo_smb",
        query_kind="pain",
        current_spend_hint=None,
        effort_cost_hint=None,
        price_complaint="can't afford a full time developer",
        willingness_to_pay_indicator="possible",
        evidence_cited="can't afford a full time developer",
        confidence=0.58,
    )


def _weak_pattern(signals):
    return WeakPatternCandidate(
        pattern_id="weak_pattern_cash_collection",
        classification="weak_pattern_candidate",
        review_priority="elevated",
        signal_ids=[signal.signal_id for signal in signals],
        signal_count=len(signals),
        avg_confidence=0.42,
        max_confidence=0.5,
        source_diversity=2,
        sources=["github_issue_source", "hn_source"],
        evidence_ids=[signal.evidence_id for signal in signals],
        summary="Weak repeated cash collection pattern.",
        confidence=0.42,
        cluster_key="cash_collection",
    )


if __name__ == "__main__":
    unittest.main()
