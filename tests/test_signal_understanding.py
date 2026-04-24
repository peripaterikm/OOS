import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.ai_contracts import AI_METADATA_REQUIRED_FIELDS, compute_input_hash
from oos.models import Signal, SignalStatus
from oos.signal_understanding import (
    SIGNAL_UNDERSTANDING_VALIDITY_THRESHOLD,
    SignalUnderstandingProvider,
    StaticSignalUnderstandingProvider,
    extract_signal_understanding,
    write_signal_understanding_artifacts,
)


def make_signal(signal_id: str, *, duplicate: bool = False, canonical_id: str = "") -> Signal:
    canonical_signal_id = canonical_id or signal_id
    return Signal(
        id=signal_id,
        source="customer_interview",
        timestamp="2026-04-24T00:00:00+00:00",
        raw_content=(
            "Every morning the ops lead spends 45 minutes copying failed export rows "
            "into a spreadsheet workaround before support can reply."
        ),
        extracted_pain="Ops lead manually reconciles failed exports",
        candidate_icp="ops lead",
        validity_specificity=1,
        validity_recurrence=1,
        validity_workaround=1,
        validity_cost_signal=1,
        validity_icp_match=1,
        validity_score=5,
        status=SignalStatus.validated,
        metadata={
            "duplicate_group_id": f"dupgrp_{canonical_signal_id}",
            "is_duplicate": duplicate,
            "canonical_signal_id": canonical_signal_id,
        },
    )


def valid_item(signal_id: str) -> dict:
    return {
        "signal_id": signal_id,
        "meaning": {
            "actor_user_segment": "ops lead",
            "pain": "manual failed export reconciliation",
            "context": "daily support operations",
            "current_workaround": "copy failed export rows into a spreadsheet",
            "urgency": "daily customer response risk",
            "cost_signal": "45 minutes every morning",
            "evidence": "reported recurring manual workflow",
            "uncertainty": "buyer budget not yet proven",
            "confidence": 0.91,
        },
        "quality": {
            "specificity": 5,
            "recurrence_potential": 5,
            "workaround": 5,
            "cost_signal": 4,
            "urgency": 4,
            "confidence": 0.88,
            "explanation": "Specific recurring workaround with time cost and operational risk.",
        },
    }


class RecordingProvider(SignalUnderstandingProvider):
    def __init__(self, payload: list[dict]):
        self.payload = payload
        self.calls = 0
        self.seen_batch_sizes: list[int] = []

    def extract(self, signals: list[Signal]) -> list[dict]:
        self.calls += 1
        self.seen_batch_sizes.append(len(signals))
        return self.payload


class TestSignalUnderstanding(unittest.TestCase):
    def test_valid_batched_extraction_creates_structured_records(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        provider = StaticSignalUnderstandingProvider(payload=[valid_item("sig_1"), valid_item("sig_2")])

        result = extract_signal_understanding(signals=signals, provider=provider)

        self.assertFalse(result.degraded_mode)
        self.assertEqual(result.valid_count, 2)
        self.assertEqual([record.signal_id for record in result.records], ["sig_1", "sig_2"])
        self.assertTrue(all(record.analysis_mode == "structured_extraction" for record in result.records))
        self.assertEqual(result.records[0].meaning.actor_user_segment, "ops lead")
        self.assertEqual(result.records[0].quality.specificity, 5)

    def test_every_output_links_to_original_signal_id_and_metadata(self) -> None:
        signal = make_signal("sig_trace")
        provider = StaticSignalUnderstandingProvider(payload=[valid_item("sig_trace")])

        result = extract_signal_understanding(signals=[signal], provider=provider)
        payload = result.records[0].to_dict()

        self.assertEqual(payload["signal_id"], "sig_trace")
        for field in AI_METADATA_REQUIRED_FIELDS:
            self.assertIn(field, payload["ai_metadata"])
        self.assertEqual(payload["ai_metadata"]["linked_input_ids"], ["sig_trace"])
        self.assertEqual(payload["ai_metadata"]["prompt_version"], "signal_meaning_extractor_v1")

    def test_input_hash_is_deterministic_and_uses_ai_contracts_helper(self) -> None:
        signal = make_signal("sig_hash")
        provider = StaticSignalUnderstandingProvider(payload=[valid_item("sig_hash")])

        first = extract_signal_understanding(signals=[signal], provider=provider)
        second = extract_signal_understanding(signals=[signal], provider=provider)
        expected_hash = compute_input_hash(
            [
                {
                    "id": signal.id,
                    "source": signal.source,
                    "timestamp": signal.timestamp,
                    "raw_content": signal.raw_content,
                    "extracted_pain": signal.extracted_pain,
                    "candidate_icp": signal.candidate_icp,
                }
            ]
        )

        self.assertEqual(first.records[0].ai_metadata["input_hash"], expected_hash)
        self.assertEqual(first.records[0].ai_metadata["input_hash"], second.records[0].ai_metadata["input_hash"])

    def test_invalid_provider_item_falls_back_for_that_signal(self) -> None:
        signals = [make_signal("sig_good"), make_signal("sig_bad")]
        invalid = valid_item("sig_bad")
        invalid["meaning"]["confidence"] = 1.5
        provider = StaticSignalUnderstandingProvider(payload=[valid_item("sig_good"), invalid])

        result = extract_signal_understanding(signals=signals, provider=provider)
        by_id = {record.signal_id: record for record in result.records}

        self.assertEqual(by_id["sig_good"].analysis_mode, "structured_extraction")
        self.assertEqual(by_id["sig_bad"].analysis_mode, "analysis_unavailable")
        self.assertTrue(by_id["sig_bad"].ai_metadata["fallback_used"])
        self.assertEqual(by_id["sig_bad"].ai_metadata["stage_status"], "degraded")

    def test_fewer_than_80_percent_valid_outputs_triggers_degraded_mode(self) -> None:
        signals = [make_signal(f"sig_{index}") for index in range(1, 6)]
        provider = StaticSignalUnderstandingProvider(payload=[valid_item("sig_1"), valid_item("sig_2"), valid_item("sig_3")])

        result = extract_signal_understanding(signals=signals, provider=provider)

        self.assertEqual(SIGNAL_UNDERSTANDING_VALIDITY_THRESHOLD, 0.80)
        self.assertEqual(result.valid_count, 3)
        self.assertEqual(result.total_count, 5)
        self.assertTrue(result.degraded_mode)
        self.assertEqual(result.stage_status, "degraded")

    def test_fallback_preserves_raw_signal_id_and_marks_analysis_unavailable(self) -> None:
        signal = make_signal("sig_missing")
        provider = StaticSignalUnderstandingProvider(payload=[])

        result = extract_signal_understanding(signals=[signal], provider=provider)
        record = result.records[0]

        self.assertEqual(record.signal_id, "sig_missing")
        self.assertEqual(record.analysis_mode, "analysis_unavailable")
        self.assertTrue(record.raw_signal_preserved)
        self.assertIn("provider returned no valid item", record.failure_reason)

    def test_duplicate_signals_do_not_inflate_denominator_with_canonical_set(self) -> None:
        signals = [
            make_signal("sig_canonical"),
            make_signal("sig_duplicate", duplicate=True, canonical_id="sig_canonical"),
        ]
        provider = StaticSignalUnderstandingProvider(payload=[valid_item("sig_canonical")])

        result = extract_signal_understanding(signals=signals, provider=provider)

        self.assertEqual(result.total_count, 1)
        self.assertEqual(result.processed_signal_ids, ["sig_canonical"])
        self.assertEqual(result.skipped_duplicate_signal_ids, ["sig_duplicate"])
        self.assertFalse(result.degraded_mode)

    def test_no_live_llm_call_is_made(self) -> None:
        provider = RecordingProvider(payload=[valid_item("sig_1")])

        result = extract_signal_understanding(signals=[make_signal("sig_1")], provider=provider)

        self.assertEqual(provider.calls, 1)
        self.assertEqual(provider.seen_batch_sizes, [1])
        self.assertEqual(result.records[0].analysis_mode, "structured_extraction")

    def test_signal_understanding_artifacts_can_be_written(self) -> None:
        result = extract_signal_understanding(
            signals=[make_signal("sig_artifact")],
            provider=StaticSignalUnderstandingProvider(payload=[valid_item("sig_artifact")]),
        )
        with TemporaryDirectory() as tmp:
            index_path = write_signal_understanding_artifacts(result, Path(tmp))
            record_path = Path(tmp) / "signal_understanding" / "sig_artifact.json"

            self.assertTrue(index_path.exists())
            self.assertTrue(record_path.exists())
            payload = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["signal_id"], "sig_artifact")


if __name__ == "__main__":
    unittest.main()
