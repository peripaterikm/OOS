import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.ai_contracts import AI_METADATA_REQUIRED_FIELDS
from oos.contradiction_detection import (
    ContradictionDetectionProvider,
    StaticContradictionDetectionProvider,
    detect_contradictions,
    write_contradiction_report_artifact,
)
from tests.test_semantic_clustering import make_signal


def valid_contradiction(**overrides: object) -> dict:
    payload = {
        "contradiction_id": "contradiction_reporting_trust",
        "signal_ids": ["sig_1", "sig_2"],
        "canonical_signal_ids": ["sig_1", "sig_2"],
        "contradiction_type": "pain_assessment_conflict",
        "description": "Signals describe the same reporting workflow but disagree about trust in current reports.",
        "conflicting_fields": ["pain", "trust_in_current_solution"],
        "evidence": [
            "sig_1 says the owner does not trust reports because balances diverge.",
            "sig_2 says the owner fully trusts reporting and only needs faster preparation.",
        ],
        "severity": "high",
        "confidence": 0.86,
        "recommendation": "Ask founder to inspect source context before opportunity framing.",
        "next_action": "Keep both signals and request clarification.",
    }
    payload.update(overrides)
    return payload


def valid_merge_candidate(**overrides: object) -> dict:
    payload = {
        "merge_candidate_id": "merge_reporting_speed",
        "signal_ids": ["sig_2", "sig_3"],
        "canonical_signal_id": "sig_2",
        "reason": "Both signals describe report preparation speed in the same owner reporting workflow.",
        "similarity": 0.88,
        "confidence": 0.8,
        "recommendation": "Review as a candidate duplicate, but keep all original signals.",
        "do_not_auto_merge": True,
    }
    payload.update(overrides)
    return payload


class RecordingProvider(ContradictionDetectionProvider):
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = 0
        self.seen_signal_ids: list[list[str]] = []

    def detect(self, *, signals, understanding_records=None, semantic_clusters=None):
        self.calls += 1
        self.seen_signal_ids.append([signal.id for signal in signals])
        return self.payload


class TestContradictionDetection(unittest.TestCase):
    def test_valid_provider_response_creates_structured_contradiction_report(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2"), make_signal("sig_3")]
        provider = StaticContradictionDetectionProvider(
            payload={
                "contradictions": [valid_contradiction()],
                "merge_candidates": [valid_merge_candidate()],
            }
        )

        report = detect_contradictions(signals=signals, provider=provider)

        self.assertFalse(report.fallback_used)
        self.assertEqual(report.stage_status, "success")
        self.assertEqual(report.contradictions[0].contradiction_id, "contradiction_reporting_trust")
        self.assertEqual(report.merge_candidates[0].merge_candidate_id, "merge_reporting_speed")
        self.assertEqual(report.source_signal_ids, ["sig_1", "sig_2", "sig_3"])

    def test_severity_values_are_validated(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticContradictionDetectionProvider(
            payload={"contradictions": [valid_contradiction(severity="critical")], "merge_candidates": []}
        )

        report = detect_contradictions(signals=signals, provider=provider)

        self.assertTrue(report.fallback_used)
        self.assertEqual(report.contradictions, [])
        self.assertIn("severity must be low, medium, or high", report.failure_reason)

    def test_unknown_linked_signal_id_is_rejected(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticContradictionDetectionProvider(
            payload={
                "contradictions": [valid_contradiction(signal_ids=["sig_1", "sig_missing"])],
                "merge_candidates": [],
            }
        )

        report = detect_contradictions(signals=signals, provider=provider)

        self.assertTrue(report.fallback_used)
        self.assertEqual(report.contradictions, [])
        self.assertIn("signal_ids contain unknown IDs", report.failure_reason)

    def test_unknown_canonical_signal_id_is_rejected(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticContradictionDetectionProvider(
            payload={
                "contradictions": [valid_contradiction(canonical_signal_ids=["sig_1", "sig_missing"])],
                "merge_candidates": [],
            }
        )

        report = detect_contradictions(signals=signals, provider=provider)

        self.assertTrue(report.fallback_used)
        self.assertEqual(report.contradictions, [])
        self.assertIn("canonical_signal_ids contain unknown IDs", report.failure_reason)

    def test_conflicting_fields_cannot_be_empty(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticContradictionDetectionProvider(
            payload={"contradictions": [valid_contradiction(conflicting_fields=[])], "merge_candidates": []}
        )

        report = detect_contradictions(signals=signals, provider=provider)

        self.assertTrue(report.fallback_used)
        self.assertEqual(report.contradictions, [])
        self.assertIn("conflicting_fields must be non-empty", report.failure_reason)

    def test_merge_candidates_do_not_delete_or_auto_merge_signals(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2"), make_signal("sig_3")]
        provider = StaticContradictionDetectionProvider(
            payload={"contradictions": [], "merge_candidates": [valid_merge_candidate()]}
        )

        report = detect_contradictions(signals=signals, provider=provider)

        self.assertEqual(report.source_signal_ids, ["sig_1", "sig_2", "sig_3"])
        self.assertEqual(report.merge_candidates[0].signal_ids, ["sig_2", "sig_3"])
        self.assertTrue(report.merge_candidates[0].do_not_auto_merge)

    def test_all_source_signal_ids_remain_traceable_with_duplicates(self) -> None:
        signals = [
            make_signal("sig_1"),
            make_signal("sig_dup", duplicate=True, canonical_id="sig_1"),
            make_signal("sig_2"),
        ]
        provider = StaticContradictionDetectionProvider(
            payload={"contradictions": [valid_contradiction(signal_ids=["sig_1", "sig_dup"])], "merge_candidates": []}
        )

        report = detect_contradictions(signals=signals, provider=provider)

        self.assertEqual(report.source_signal_ids, ["sig_1", "sig_dup", "sig_2"])
        self.assertEqual(report.source_canonical_signal_ids, ["sig_1", "sig_2"])
        self.assertEqual(report.skipped_duplicate_signal_ids, ["sig_dup"])
        self.assertEqual(report.contradictions[0].source_signal_ids, ["sig_1", "sig_dup"])

    def test_fallback_report_is_produced_for_invalid_provider_payload(self) -> None:
        signals = [make_signal("sig_1")]
        provider = StaticContradictionDetectionProvider(payload=["not", "an", "object"])  # type: ignore[arg-type]

        report = detect_contradictions(signals=signals, provider=provider)

        self.assertTrue(report.fallback_used)
        self.assertEqual(report.stage_status, "degraded")
        self.assertEqual(report.contradictions, [])
        self.assertEqual(report.merge_candidates, [])
        self.assertEqual(report.source_signal_ids, ["sig_1"])
        self.assertIn("provider payload must be an object", report.failure_reason)

    def test_ai_metadata_is_present(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticContradictionDetectionProvider(
            payload={"contradictions": [valid_contradiction()], "merge_candidates": []}
        )

        report = detect_contradictions(signals=signals, provider=provider)

        for field in AI_METADATA_REQUIRED_FIELDS:
            self.assertIn(field, report.ai_metadata)
        self.assertEqual(report.ai_metadata["prompt_name"], "contradiction_detection")
        self.assertEqual(report.ai_metadata["prompt_version"], "contradiction_detection_v1")
        self.assertEqual(report.ai_metadata["linked_input_ids"], ["sig_1", "sig_2"])

    def test_no_live_llm_call_is_made(self) -> None:
        provider = RecordingProvider(payload={"contradictions": [valid_contradiction()], "merge_candidates": []})

        report = detect_contradictions(signals=[make_signal("sig_1"), make_signal("sig_2")], provider=provider)

        self.assertEqual(provider.calls, 1)
        self.assertEqual(provider.seen_signal_ids, [["sig_1", "sig_2"]])
        self.assertFalse(report.fallback_used)

    def test_valid_records_survive_when_one_provider_record_is_bad(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticContradictionDetectionProvider(
            payload={
                "contradictions": [
                    valid_contradiction(),
                    valid_contradiction(contradiction_id="bad", conflicting_fields=[]),
                ],
                "merge_candidates": [],
            }
        )

        report = detect_contradictions(signals=signals, provider=provider)

        self.assertTrue(report.fallback_used)
        self.assertEqual(report.stage_status, "degraded")
        self.assertEqual([record.contradiction_id for record in report.contradictions], ["contradiction_reporting_trust"])
        self.assertEqual(len(report.rejected_record_errors), 1)

    def test_contradiction_report_artifact_can_be_written(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticContradictionDetectionProvider(
            payload={"contradictions": [valid_contradiction()], "merge_candidates": []}
        )
        report = detect_contradictions(signals=signals, provider=provider)

        with TemporaryDirectory() as tmp:
            report_path = write_contradiction_report_artifact(report, Path(tmp))
            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertTrue(report_path.name.endswith(".json"))
        self.assertEqual(payload["contradictions"][0]["contradiction_id"], "contradiction_reporting_trust")


if __name__ == "__main__":
    unittest.main()
