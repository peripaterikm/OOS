import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.cli import main
from oos.models import Signal, SignalStatus
from oos.signal_dedup import (
    NEAR_DUPLICATE_COSINE_THRESHOLD,
    build_dedup_metadata,
    canonical_signal_set,
    cosine_similarity_on_normalized_text,
    normalize_signal_text,
    original_signal_ids_by_canonical,
    signal_fingerprint,
)
from oos.signal_layer import RawSignal


def make_raw(signal_id: str, text: str) -> RawSignal:
    return RawSignal(
        id=signal_id,
        source="test",
        timestamp="2026-04-24T00:00:00+00:00",
        raw_content=text,
        extracted_pain=text[:80],
        candidate_icp="ops lead",
    )


def make_signal(signal_id: str, *, is_duplicate: bool, canonical_signal_id: str) -> Signal:
    return Signal(
        id=signal_id,
        source="test",
        timestamp="2026-04-24T00:00:00+00:00",
        raw_content="Every morning ops copies failed export rows into a spreadsheet for 45 minutes.",
        extracted_pain="Ops copies failed exports manually",
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
            "is_duplicate": is_duplicate,
            "canonical_signal_id": canonical_signal_id,
        },
    )


class TestSignalDedupFingerprinting(unittest.TestCase):
    def test_normalized_fingerprint_is_stable(self) -> None:
        first = signal_fingerprint("Ops Lead copies failed exports into a spreadsheet.")
        second = signal_fingerprint("ops lead   copies failed exports into a spreadsheet!!!")

        self.assertEqual(normalize_signal_text("A  B!!!"), "a b")
        self.assertEqual(first, second)

    def test_exact_duplicates_are_detected(self) -> None:
        metadata = build_dedup_metadata(
            [
                make_raw("sig_a", "Every morning ops copies failed export rows into a spreadsheet."),
                make_raw("sig_b", "every morning ops copies failed export rows into a spreadsheet!!!"),
            ]
        )

        self.assertFalse(metadata["sig_a"].is_duplicate)
        self.assertTrue(metadata["sig_b"].is_duplicate)
        self.assertEqual(metadata["sig_b"].duplicate_reason, "exact_duplicate")
        self.assertEqual(metadata["sig_b"].canonical_signal_id, "sig_a")

    def test_near_duplicates_above_threshold_are_detected(self) -> None:
        canonical = "Ops lead copies failed export rows into a spreadsheet every morning for support review."
        near_duplicate = "Ops lead copies failed export rows into a spreadsheet every morning for support checks."

        similarity = cosine_similarity_on_normalized_text(canonical, near_duplicate)
        metadata = build_dedup_metadata([make_raw("sig_a", canonical), make_raw("sig_b", near_duplicate)])

        self.assertGreaterEqual(similarity, NEAR_DUPLICATE_COSINE_THRESHOLD)
        self.assertTrue(metadata["sig_b"].is_duplicate)
        self.assertEqual(metadata["sig_b"].duplicate_reason, "near_duplicate")
        self.assertEqual(metadata["sig_b"].canonical_signal_id, "sig_a")

    def test_non_duplicates_below_threshold_are_not_merged(self) -> None:
        left = "Ops lead copies failed export rows into a spreadsheet every morning."
        right = "Clinic admin screenshots payer portal status before claims denials."

        similarity = cosine_similarity_on_normalized_text(left, right)
        metadata = build_dedup_metadata([make_raw("sig_a", left), make_raw("sig_b", right)])

        self.assertLess(similarity, NEAR_DUPLICATE_COSINE_THRESHOLD)
        self.assertFalse(metadata["sig_b"].is_duplicate)
        self.assertEqual(metadata["sig_b"].canonical_signal_id, "sig_b")

    def test_duplicate_metadata_and_traceability_are_preserved(self) -> None:
        metadata = build_dedup_metadata(
            [
                make_raw("sig_a", "Every morning ops copies failed export rows into a spreadsheet."),
                make_raw("sig_b", "Every morning ops copies failed export rows into a spreadsheet."),
            ]
        )
        duplicate_payload = metadata["sig_b"].to_dict()

        self.assertEqual(duplicate_payload["duplicate_group_id"], "dupgrp_sig_a")
        self.assertTrue(duplicate_payload["is_duplicate"])
        self.assertEqual(duplicate_payload["canonical_signal_id"], "sig_a")
        self.assertEqual(duplicate_payload["near_duplicate_method"], "cosine_similarity_on_normalized_signal_text")

    def test_canonical_signal_set_does_not_count_duplicates_as_recurrence(self) -> None:
        signals = [
            make_signal("sig_a", is_duplicate=False, canonical_signal_id="sig_a"),
            make_signal("sig_b", is_duplicate=True, canonical_signal_id="sig_a"),
            make_signal("sig_c", is_duplicate=False, canonical_signal_id="sig_c"),
        ]

        canonical = canonical_signal_set(signals)
        grouped = original_signal_ids_by_canonical(signals)

        self.assertEqual([signal.id for signal in canonical], ["sig_a", "sig_c"])
        self.assertEqual(grouped["sig_a"], ["sig_a", "sig_b"])
        self.assertEqual(grouped["sig_c"], ["sig_c"])

    def test_real_signal_batch_preserves_duplicates_but_frames_canonical_set(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            input_file = Path(tmp) / "signals.jsonl"
            records = [
                {
                    "signal_id": "sig_dup_a",
                    "captured_at": "2026-04-20T09:00:00+00:00",
                    "source_type": "customer_interview",
                    "title": "Ops copies failed export rows every morning",
                    "text": "Every morning the ops lead spends 45 minutes copying failed export rows into a spreadsheet workaround before support can reply.",
                    "source_ref": "dup-a",
                },
                {
                    "signal_id": "sig_dup_b",
                    "captured_at": "2026-04-20T10:00:00+00:00",
                    "source_type": "support_ticket",
                    "title": "Ops copies failed export rows every morning",
                    "text": "Every morning the ops lead spends 45 minutes copying failed export rows into a spreadsheet workaround before support can reply.",
                    "source_ref": "dup-b",
                },
            ]
            input_file.write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    ["run-signal-batch", "--project-root", str(project_root), "--input-file", str(input_file)]
                )

            self.assertEqual(exit_code, 0)
            artifacts = project_root / "artifacts"
            signal_artifacts = list((artifacts / "signals").glob("*.json"))
            first = json.loads((artifacts / "signals" / "sig_dup_a.json").read_text(encoding="utf-8"))
            second = json.loads((artifacts / "signals" / "sig_dup_b.json").read_text(encoding="utf-8"))
            opportunity = json.loads((artifacts / "opportunities" / "opp_batch_1.json").read_text(encoding="utf-8"))

            self.assertEqual(len(signal_artifacts), len(records))
            self.assertTrue((artifacts / "signals" / "sig_dup_a.json").exists())
            self.assertTrue((artifacts / "signals" / "sig_dup_b.json").exists())
            self.assertFalse(first["metadata"]["is_duplicate"])
            self.assertTrue(second["metadata"]["is_duplicate"])
            self.assertEqual(second["metadata"]["canonical_signal_id"], "sig_dup_a")
            self.assertEqual(opportunity["source_signal_ids"], ["sig_dup_a"])


if __name__ == "__main__":
    unittest.main()
