import json
import unittest

from oos.evidence_pack import (
    EVIDENCE_PACK_SCHEMA_VERSION,
    INSUFFICIENT_EVIDENCE_CREATED_FROM,
    EvidencePack,
    EvidencePackItem,
    EvidencePackRiskNote,
    EvidencePackSourceSummary,
    evidence_pack_from_dict,
    evidence_pack_to_dict,
    make_evidence_pack_id,
    normalize_evidence_pack_order,
    validate_evidence_pack,
)


class EvidencePackContractTests(unittest.TestCase):
    def test_evidence_pack_can_be_created_and_validated(self):
        pack = _sample_pack()

        validate_evidence_pack(pack)

        self.assertEqual(pack.evidence_pack_id, make_evidence_pack_id("cluster_cash_collection"))
        self.assertEqual(pack.schema_version, EVIDENCE_PACK_SCHEMA_VERSION)

    def test_evidence_pack_serializes_to_json_compatible_dict(self):
        payload = evidence_pack_to_dict(_sample_pack())

        encoded = json.dumps(payload, sort_keys=True)

        self.assertIn("raw_hn_47082761", encoded)
        self.assertEqual(payload["schema_version"], EVIDENCE_PACK_SCHEMA_VERSION)

    def test_evidence_pack_round_trips_from_dict(self):
        pack = _sample_pack()

        restored = evidence_pack_from_dict(evidence_pack_to_dict(pack))

        self.assertEqual(restored, pack)
        restored.validate()

    def test_traceability_fields_are_preserved(self):
        pack = _sample_pack()

        self.assertEqual(pack.evidence_ids, ["raw_hn_47082761", "raw_github_issue_1182773055"])
        self.assertEqual(pack.source_signal_ids, ["signal_hn_invoice", "signal_github_ynab"])
        self.assertEqual(
            pack.source_urls,
            ["https://news.ycombinator.com/item?id=47082761", "https://github.com/ynab/issues/123"],
        )

    def test_source_diversity_and_recurrence_are_represented(self):
        pack = _sample_pack()

        self.assertEqual(pack.source_diversity, 2)
        self.assertEqual(pack.recurrence_count, 2)

    def test_optional_price_weak_pattern_and_kill_ids_are_preserved(self):
        pack = _sample_pack()

        self.assertEqual(pack.price_signal_ids, ["price_signal_affordability"])
        self.assertEqual(pack.weak_pattern_ids, ["weak_pattern_cash_collection"])
        self.assertEqual(pack.kill_warning_ids, ["kill_warning_old_invoice_tool"])

    def test_risk_notes_are_preserved(self):
        pack = _sample_pack()

        self.assertEqual(pack.risk_notes[0].risk_type, "weak_price_evidence")
        self.assertEqual(pack.risk_notes[0].evidence_id, "raw_hn_47082761")

    def test_deterministic_ordering_normalizes_lists_and_items(self):
        pack = EvidencePack(
            evidence_pack_id="evidence_pack_z",
            cluster_id="cluster_z",
            source_signal_ids=["signal_b", "signal_a", "signal_a"],
            evidence_ids=["evidence_b", "evidence_a", "evidence_a"],
            source_urls=["https://b.example", "https://a.example", "https://a.example"],
            summaries=["z summary", "a summary"],
            source_types=["github_issue", "hn", "hn"],
            topic_id="ai_cfo_smb",
            confidence_values=[0.4, 0.2, 0.4],
            source_diversity=2,
            recurrence_count=2,
            created_from="contract_test",
            price_signal_ids=["price_b", "price_a"],
            weak_pattern_ids=["weak_b", "weak_a"],
            kill_warning_ids=["kill_b", "kill_a"],
            risk_notes=[
                EvidencePackRiskNote(risk_type="buyer", note="Buyer unclear", severity="medium"),
                EvidencePackRiskNote(risk_type="price", note="Price unclear", evidence_id="evidence_a", severity="low"),
            ],
            items=[
                EvidencePackItem(
                    evidence_id="evidence_b",
                    source_signal_id="signal_b",
                    source_url="https://b.example",
                    source_type="github_issue",
                    summary="B",
                ),
                EvidencePackItem(
                    evidence_id="evidence_a",
                    source_signal_id="signal_a",
                    source_url="https://a.example",
                    source_type="hn",
                    summary="A",
                ),
            ],
        )

        normalized = normalize_evidence_pack_order(pack)

        self.assertEqual(normalized.evidence_ids, ["evidence_a", "evidence_b"])
        self.assertEqual(normalized.source_signal_ids, ["signal_a", "signal_b"])
        self.assertEqual([item.evidence_id for item in normalized.items], ["evidence_a", "evidence_b"])
        self.assertEqual([note.risk_type for note in normalized.risk_notes], ["price", "buyer"])

    def test_validation_rejects_missing_evidence_ids_for_regular_pack(self):
        pack = _sample_pack(evidence_ids=[])

        with self.assertRaisesRegex(ValueError, "evidence_ids"):
            validate_evidence_pack(pack)

    def test_validation_rejects_missing_source_urls_for_regular_pack(self):
        pack = _sample_pack(source_urls=[])

        with self.assertRaisesRegex(ValueError, "source_urls"):
            validate_evidence_pack(pack)

    def test_insufficient_evidence_state_is_explicit_and_allowed(self):
        pack = EvidencePack(
            evidence_pack_id="evidence_pack_empty",
            cluster_id="cluster_empty",
            source_signal_ids=[],
            evidence_ids=[],
            source_urls=[],
            summaries=[],
            source_types=[],
            topic_id="ai_cfo_smb",
            confidence_values=[],
            source_diversity=0,
            recurrence_count=0,
            created_from=INSUFFICIENT_EVIDENCE_CREATED_FROM,
            risk_notes=[
                EvidencePackRiskNote(
                    risk_type="insufficient_evidence",
                    note="No qualifying evidence exists for this opportunity seed.",
                    severity="high",
                )
            ],
        )

        validate_evidence_pack(pack)

        self.assertTrue(pack.is_insufficient_evidence)

    def test_no_live_network_or_llm_calls_are_needed(self):
        payload = evidence_pack_to_dict(_sample_pack())

        self.assertNotIn("provider.complete", json.dumps(payload))
        self.assertNotIn("allow_live_network", json.dumps(payload))


def _sample_pack(**overrides):
    values = {
        "evidence_pack_id": make_evidence_pack_id("cluster_cash_collection"),
        "cluster_id": "cluster_cash_collection",
        "source_signal_ids": ["signal_hn_invoice", "signal_github_ynab"],
        "evidence_ids": ["raw_hn_47082761", "raw_github_issue_1182773055"],
        "source_urls": ["https://news.ycombinator.com/item?id=47082761", "https://github.com/ynab/issues/123"],
        "summaries": [
            "Small business operator describes unpaid invoice follow-up pain.",
            "YNAB user requests historical balance-sheet reporting.",
        ],
        "source_types": ["hn", "github_issue"],
        "topic_id": "ai_cfo_smb",
        "confidence_values": [0.72, 0.66],
        "price_signal_ids": ["price_signal_affordability"],
        "weak_pattern_ids": ["weak_pattern_cash_collection"],
        "kill_warning_ids": ["kill_warning_old_invoice_tool"],
        "source_diversity": 2,
        "recurrence_count": 2,
        "risk_notes": [
            EvidencePackRiskNote(
                risk_type="weak_price_evidence",
                note="Price evidence is affordability context, not explicit budget.",
                evidence_id="raw_hn_47082761",
                severity="medium",
            )
        ],
        "items": [
            EvidencePackItem(
                evidence_id="raw_hn_47082761",
                source_signal_id="signal_hn_invoice",
                source_url="https://news.ycombinator.com/item?id=47082761",
                source_type="hn",
                summary="Small business operator describes unpaid invoice follow-up pain.",
                confidence=0.72,
            ),
            EvidencePackItem(
                evidence_id="raw_github_issue_1182773055",
                source_signal_id="signal_github_ynab",
                source_url="https://github.com/ynab/issues/123",
                source_type="github_issue",
                summary="YNAB user requests historical balance-sheet reporting.",
                confidence=0.66,
            ),
        ],
        "source_summaries": [
            EvidencePackSourceSummary(source_type="hn", source_count=1, evidence_ids=["raw_hn_47082761"]),
            EvidencePackSourceSummary(
                source_type="github_issue",
                source_count=1,
                evidence_ids=["raw_github_issue_1182773055"],
            ),
        ],
        "created_from": "contract_test_fixture",
    }
    values.update(overrides)
    return EvidencePack(**values)


if __name__ == "__main__":
    unittest.main()
