import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.models import SignalStatus
from oos.signal_layer import (
    RawSignal,
    RuleBasedSignalValidityEvaluator,
    SignalLayer,
    SignalRouter,
)


class TestSignalValidityEvaluator(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = RuleBasedSignalValidityEvaluator()

    def test_validated_case_score_3(self) -> None:
        raw = RawSignal(
            id="sig_v",
            raw_content="Каждый день вручную копирую данные в таблицу — это занимает 30 минут и часто приводит к ошибкам.",
            extracted_pain="Ручное копирование данных занимает время и приводит к ошибкам.",
            candidate_icp="операционный менеджер",
            validity_specificity=1,
            validity_recurrence=1,
            validity_workaround=1,
            validity_cost_signal=0,
            validity_icp_match=0,
        )
        res = self.evaluator.evaluate(raw)
        self.assertEqual(res.score, 3)
        self.assertEqual(res.status, SignalStatus.validated)
        self.assertIsNone(res.rejection_reason)

    def test_weak_case_score_2(self) -> None:
        raw = RawSignal(
            id="sig_w",
            raw_content="Часто неудобно, но терпимо.",
            extracted_pain="Небольшое неудобство в процессе.",
            candidate_icp="unknown",
            validity_specificity=1,
            validity_recurrence=1,
            validity_workaround=0,
            validity_cost_signal=0,
            validity_icp_match=0,
        )
        res = self.evaluator.evaluate(raw)
        self.assertEqual(res.score, 2)
        self.assertEqual(res.status, SignalStatus.weak)
        self.assertIsNone(res.rejection_reason)

    def test_noise_case_score_1_requires_reason(self) -> None:
        raw = RawSignal(
            id="sig_n",
            raw_content="Это просто бесит.",
            extracted_pain="Раздражение без конкретики.",
            candidate_icp="unknown",
            validity_specificity=1,
            validity_recurrence=0,
            validity_workaround=0,
            validity_cost_signal=0,
            validity_icp_match=0,
        )
        res = self.evaluator.evaluate(raw)
        self.assertEqual(res.score, 1)
        self.assertEqual(res.status, SignalStatus.noise)
        self.assertIsNotNone(res.rejection_reason)

    def test_borderline_cases(self) -> None:
        # score=2 -> weak
        raw2 = RawSignal(
            id="sig_b2",
            raw_content="Два измерения.",
            extracted_pain="Боль есть.",
            candidate_icp="unknown",
            validity_specificity=1,
            validity_recurrence=0,
            validity_workaround=1,
            validity_cost_signal=0,
            validity_icp_match=0,
        )
        res2 = self.evaluator.evaluate(raw2)
        self.assertEqual(res2.score, 2)
        self.assertEqual(res2.status, SignalStatus.weak)

        # score=3 -> validated
        raw3 = RawSignal(
            id="sig_b3",
            raw_content="Три измерения.",
            extracted_pain="Боль есть.",
            candidate_icp="операции",
            validity_specificity=1,
            validity_recurrence=0,
            validity_workaround=1,
            validity_cost_signal=0,
            validity_icp_match=1,
        )
        res3 = self.evaluator.evaluate(raw3)
        self.assertEqual(res3.score, 3)
        self.assertEqual(res3.status, SignalStatus.validated)


class TestSignalLayerRouting(unittest.TestCase):
    def test_routing_writes_refs(self) -> None:
        with TemporaryDirectory() as tmp:
            artifacts_root = Path(tmp) / "artifacts"
            layer = SignalLayer(artifacts_root=artifacts_root)

            # validated -> only main store
            s1 = layer.ingest_manual(
                raw_content="Every day I manually copy data (workaround). Pain: it takes 30 minutes.",
                extracted_pain="Manual copy takes time.",
                candidate_icp="ops manager",
                source="manual",
                timestamp="2026-04-16T00:00:00+00:00",
                signal_id="sig_1",
            )
            self.assertEqual(s1.status, SignalStatus.validated)
            self.assertTrue((artifacts_root / "signals" / "sig_1.json").exists())
            self.assertFalse((artifacts_root / "weak_signals" / "sig_1.json").exists())
            self.assertFalse((artifacts_root / "noise_archive" / "sig_1.json").exists())

            # force noise via explicit overrides
            raw_noise = RawSignal(
                id="sig_2",
                source="manual",
                timestamp="2026-04-16T00:00:00+00:00",
                raw_content="meh",
                extracted_pain="meh",
                candidate_icp="unknown",
                validity_specificity=1,
                validity_recurrence=0,
                validity_workaround=0,
                validity_cost_signal=0,
                validity_icp_match=0,
            )
            # internal ingest path via file-like single ingestion:
            # simplest: call private route through importer contract by writing a JSONL file.
            import_path = artifacts_root.parent / "import.jsonl"
            import_path.write_text(json.dumps(raw_noise.__dict__, ensure_ascii=False) + "\n", encoding="utf-8")
            signals = layer.ingest_file(import_path)
            self.assertEqual(len(signals), 1)
            self.assertEqual(signals[0].id, "sig_2")
            self.assertEqual(signals[0].status, SignalStatus.noise)
            self.assertTrue((artifacts_root / "signals" / "sig_2.json").exists())
            self.assertTrue((artifacts_root / "noise_archive" / "sig_2.json").exists())


if __name__ == "__main__":
    unittest.main()

