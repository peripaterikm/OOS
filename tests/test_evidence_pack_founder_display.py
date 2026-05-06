import json
import unittest

from oos.discovery_weekly import _build_founder_package, _founder_package_markdown
from oos.evidence_pack import evidence_pack_to_dict
from oos.evidence_pack_builder import build_evidence_pack_from_signals
from oos.founder_package import build_founder_evidence_pack_section, render_founder_evidence_pack_section
from oos.models import CandidateSignal, PriceSignal


class EvidencePackFounderDisplayTests(unittest.TestCase):
    def test_founder_package_json_includes_evidence_pack_section(self):
        pack = _evidence_pack()

        package = _package_with_evidence_packs([pack])

        section = package["evidence_packs"]
        self.assertEqual(section["count"], 1)
        self.assertEqual(section["items"][0]["evidence_pack_id"], pack.evidence_pack_id)
        self.assertEqual(section["items"][0]["cluster_id"], "cash_collection")

    def test_founder_package_markdown_includes_evidence_pack_section(self):
        pack = _evidence_pack()

        markdown = _founder_package_markdown(_package_with_evidence_packs([pack]))

        self.assertIn("## Evidence packs", markdown)
        self.assertIn(pack.evidence_pack_id, markdown)
        self.assertIn("cash_collection", markdown)

    def test_display_includes_traceable_counts_and_references(self):
        pack = _evidence_pack()

        item = _package_with_evidence_packs([pack])["evidence_packs"]["items"][0]

        self.assertEqual(item["source_signal_count"], 2)
        self.assertEqual(item["evidence_count"], 2)
        self.assertEqual(item["source_diversity"], 2)
        self.assertEqual(item["recurrence_count"], 2)
        self.assertEqual(item["evidence_ids"], ["evidence_a", "evidence_b"])
        self.assertEqual(item["source_signal_ids"], ["signal_a", "signal_b"])
        self.assertIn("https://example.com/evidence_a", item["source_urls"])

    def test_display_includes_linked_quality_ids_and_risk_notes(self):
        pack = _evidence_pack()

        item = _package_with_evidence_packs([pack])["evidence_packs"]["items"][0]
        markdown = _founder_package_markdown(_package_with_evidence_packs([pack]))

        self.assertEqual(item["price_signal_ids"], ["price_a"])
        self.assertEqual(item["weak_pattern_ids"], ["weak_pattern_cash_collection"])
        self.assertEqual(item["kill_warning_ids"], ["kill_warning_a"])
        self.assertTrue(any("kill_archive_warning" in note for note in item["risk_notes"]))
        self.assertIn("price_a", markdown)
        self.assertIn("weak_pattern_cash_collection", markdown)
        self.assertIn("kill_warning_a", markdown)
        self.assertIn("Risk notes", markdown)

    def test_empty_evidence_pack_state_renders_without_crash(self):
        package = _package_with_evidence_packs([])

        self.assertEqual(package["evidence_packs"]["items"], [])
        self.assertIn("No evidence packs generated for this run.", _founder_package_markdown(package))

    def test_evidence_pack_output_ordering_is_deterministic(self):
        first_pack = _evidence_pack(cluster_id="cash_collection")
        second_pack = _evidence_pack(cluster_id="month_end_reporting")

        first = build_founder_evidence_pack_section([second_pack, first_pack])
        second = build_founder_evidence_pack_section([first_pack, second_pack])

        self.assertEqual(first, second)
        self.assertEqual([item["cluster_id"] for item in first["items"]], ["cash_collection", "month_end_reporting"])

    def test_section_accepts_serialized_evidence_pack_dicts(self):
        pack = _evidence_pack()

        section = build_founder_evidence_pack_section([evidence_pack_to_dict(pack)])
        markdown = render_founder_evidence_pack_section(section)

        self.assertEqual(section["items"][0]["evidence_pack_id"], pack.evidence_pack_id)
        self.assertIn("Evidence IDs", markdown)

    def test_existing_founder_quality_sections_still_render(self):
        markdown = _founder_package_markdown(_package_with_evidence_packs([_evidence_pack()]))

        self.assertIn("## Quality review sections", markdown)
        self.assertIn("### Price Signals", markdown)
        self.assertIn("## Evidence packs", markdown)

    def test_no_live_network_or_llm_calls_are_made(self):
        package = _package_with_evidence_packs([_evidence_pack()])

        payload = json.dumps(package, sort_keys=True)
        self.assertNotIn("provider.complete", payload)
        self.assertNotIn("allow_live_network", payload)


def _package_with_evidence_packs(evidence_packs):
    signals = [_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")]
    return _build_founder_package(
        summary=_summary(evidence_pack_count=len(evidence_packs)),
        candidate_signals=signals,
        classifications=[],
        price_signals=[_price_signal("price_a", "evidence_a")],
        evidence_packs=evidence_packs,
        run_dir=None,
        collection_metadata={},
    )


def _summary(*, evidence_pack_count):
    return {
        "run_id": "evidence_pack_founder_display",
        "topic_id": "ai_cfo_smb",
        "collection_mode": "fixture",
        "live_network_enabled": False,
        "raw_evidence_count": 2,
        "candidate_signal_count": 2,
        "canonical_candidate_signal_count": 2,
        "suppressed_duplicate_candidate_signal_count": 0,
        "duplicate_candidate_group_count": 0,
        "price_signal_count": 1,
        "weak_pattern_candidate_count": 1,
        "evidence_pack_count": evidence_pack_count,
        "needs_human_review_count": 0,
        "noise_count": 0,
        "counts_by_source_type": {"github_issue": 1, "hn": 1},
        "counts_by_classification": {"pain_signal_candidate": 2},
        "counts_by_signal_type": {"pain_signal": 2},
        "candidate_signal_dedup": {"canonical_signal_count": 2, "suppressed_duplicate_count": 0},
        "artifact_paths": {"evidence_packs": "artifacts/discovery_runs/run/evidence_packs.json"},
        "collection_errors": [],
    }


def _evidence_pack(cluster_id="cash_collection"):
    return build_evidence_pack_from_signals(
        cluster_id=cluster_id,
        candidate_signals=[_signal("signal_a", "evidence_a", "hn"), _signal("signal_b", "evidence_b", "github_issue")],
        price_signals=[_price_signal("price_a", "evidence_a")],
        weak_pattern=_weak_pattern(),
        kill_warnings=[
            {
                "warning_id": "kill_warning_a",
                "signal_id": "signal_b",
                "evidence_id": "evidence_b",
                "summary": "Similar killed invoice tool warning.",
            }
        ],
    )


def _signal(signal_id, evidence_id, source_type):
    return CandidateSignal(
        signal_id=signal_id,
        evidence_id=evidence_id,
        source_id=f"{source_type}_source",
        source_type=source_type,
        source_url=f"https://example.com/{evidence_id}",
        topic_id="ai_cfo_smb",
        query_kind="pain",
        signal_type="pain_signal",
        pain_summary=f"{evidence_id} describes SMB finance workflow pain.",
        target_user="small business operator",
        current_workaround="manual spreadsheet follow-up",
        buying_intent_hint="not_detected",
        urgency_hint="not_detected",
        confidence=0.62,
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
        classification="pain_signal_candidate",
        classification_confidence=0.62,
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


def _weak_pattern():
    return type(
        "WeakPatternFixture",
        (),
        {
            "pattern_id": "weak_pattern_cash_collection",
            "cluster_key": "cash_collection",
        },
    )()


if __name__ == "__main__":
    unittest.main()
