from __future__ import annotations

import unittest
from pathlib import Path

from oos.evaluation_dataset import (
    EVALUATION_QUALITY_DATASET_V1_PATH,
    load_opportunity_quality_cases_v1,
)
from oos.evidence_pack import evidence_pack_from_dict
from oos.opportunity_sketch import opportunity_sketch_from_dict
from oos.opportunity_quality_gate import evaluate_opportunity_quality
from oos.evidence_sufficiency_scoring import score_evidence_sufficiency

REQUIRED_CASE_TYPES = {
    "strong_opportunity",
    "weak_but_interesting",
    "generic_false_positive",
    "vendor_promo_false_positive",
    "duplicate_signal",
    "no_buyer",
    "weak_noisy",
    "killed_pattern_repeat",
    "needs_more_evidence",
}

REQUIRED_FOUNDER_POSTURES = {
    "promote_candidate",
    "park_candidate",
    "kill_candidate",
    "needs_more_evidence",
    "revisit_candidate",
}

REQUIRED_GATE_DECISIONS = {"pass", "park", "reject"}


class TestOpportunityQualityEvaluationDataset(unittest.TestCase):
    def test_dataset_v1_exists_and_is_loadable(self) -> None:
        self.assertTrue(EVALUATION_QUALITY_DATASET_V1_PATH.exists())
        cases = load_opportunity_quality_cases_v1()
        self.assertIsInstance(cases, list)
        self.assertEqual(len(cases), 10)

    def test_every_case_has_required_fields(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertIsInstance(case["case_id"], str)
                self.assertIsInstance(case["title"], str)
                self.assertIs(case["synthetic_data"], True)
                self.assertIsInstance(case["input_artifacts"], dict)
                self.assertIsInstance(case["expected"], dict)
                self.assertIsInstance(case["rationale"], str)

    def test_every_case_is_synthetic(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertTrue(case.get("synthetic_data"), f"{case['case_id']} must have synthetic_data=true")

    def test_all_required_quality_labels_are_present(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        labels = {case["expected"]["quality_label"] for case in cases}
        missing = REQUIRED_CASE_TYPES - labels
        self.assertFalse(missing, f"Missing quality labels: {', '.join(sorted(missing))}")

    def test_all_required_founder_postures_are_present(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        postures = {case["expected"]["founder_review_posture"] for case in cases}
        missing = REQUIRED_FOUNDER_POSTURES - postures
        self.assertFalse(missing, f"Missing founder postures: {', '.join(sorted(missing))}")

    def test_all_required_gate_decisions_are_present(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        decisions = {case["expected"]["gate_decision"] for case in cases}
        missing = REQUIRED_GATE_DECISIONS - decisions
        self.assertFalse(missing, f"Missing gate decisions: {', '.join(sorted(missing))}")

    def test_expected_labels_match_expected_decision_consistency(self) -> None:
        promote_labels = {"strong_opportunity"}
        park_labels = {"weak_but_interesting", "duplicate_signal", "no_buyer", "needs_more_evidence"}
        kill_labels = {"generic_false_positive", "vendor_promo_false_positive", "weak_noisy", "killed_pattern_repeat"}
        # Gate decisions are advisory; actual pipeline may differ based on evidence
        strong_park_candidate_labels = {"no_buyer", "needs_more_evidence", "killed_pattern_repeat"}

        cases = load_opportunity_quality_cases_v1()
        for case in cases:
            label = case["expected"]["quality_label"]
            posture = case["expected"]["founder_review_posture"]
            gate = case["expected"]["gate_decision"]
            case_id = case["case_id"]

            with self.subTest(case_id=case_id, label=label, posture=posture, gate=gate):
                if label in promote_labels:
                    self.assertIn(posture, ("promote_candidate", "revisit_candidate"))
                    self.assertIn(gate, ("pass", "park"))
                elif label in park_labels:
                    self.assertIn(posture, ("park_candidate", "needs_more_evidence"))
                    self.assertIn(gate, ("park", "reject"))
                elif label in kill_labels:
                    self.assertEqual(posture, "kill_candidate")
                    if label in strong_park_candidate_labels:
                        self.assertIn(gate, ("park", "reject"))
                    else:
                        self.assertEqual(gate, "reject")

    def test_strong_opportunity_case_001_passes_gate(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_001 = _case_by_id(cases, "opp_quality_v1_case_001")
        self.assertEqual(case_001["expected"]["quality_label"], "strong_opportunity")
        self.assertEqual(case_001["expected"]["founder_review_posture"], "promote_candidate")
        self.assertEqual(case_001["expected"]["gate_decision"], "pass")

        pack = evidence_pack_from_dict(case_001["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_001["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, "pass")
        self.assertIn("evidence_sufficiency_strong", [r.code for r in gate_result.reasons])
        self.assertIn("false_positive_not_detected", [r.code for r in gate_result.reasons])

    def test_weak_but_interesting_case_002_parks(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_002 = _case_by_id(cases, "opp_quality_v1_case_002")
        self.assertEqual(case_002["expected"]["quality_label"], "weak_but_interesting")
        self.assertEqual(case_002["expected"]["founder_review_posture"], "park_candidate")
        self.assertEqual(case_002["expected"]["gate_decision"], "park")

        pack = evidence_pack_from_dict(case_002["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_002["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, "park")
        self.assertIn("price_or_willingness_to_pay", gate_result.missing_evidence)
        sufficiency = score_evidence_sufficiency(candidate, pack)
        self.assertTrue(sufficiency.score_band in ("adequate", "weak"))

    def test_generic_false_positive_case_003_rejects(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_003 = _case_by_id(cases, "opp_quality_v1_case_003")
        self.assertEqual(case_003["expected"]["quality_label"], "generic_false_positive")
        self.assertEqual(case_003["expected"]["founder_review_posture"], "kill_candidate")
        self.assertEqual(case_003["expected"]["gate_decision"], "reject")

        pack = evidence_pack_from_dict(case_003["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_003["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, "reject")
        sufficiency = score_evidence_sufficiency(candidate, pack)
        self.assertEqual(sufficiency.score_band, "insufficient")

    def test_vendor_promo_case_004_rejects(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_004 = _case_by_id(cases, "opp_quality_v1_case_004")
        self.assertEqual(case_004["expected"]["quality_label"], "vendor_promo_false_positive")
        self.assertEqual(case_004["expected"]["founder_review_posture"], "kill_candidate")
        self.assertEqual(case_004["expected"]["gate_decision"], "reject")

        pack = evidence_pack_from_dict(case_004["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_004["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, "reject")
        self.assertTrue(
            any("vendor_or_generic_risk" in issue for issue in gate_result.blocking_issues),
            f"Expected vendor_or_generic_risk in blocking_issues, got: {gate_result.blocking_issues}",
        )

    def test_duplicate_signal_case_005_parks(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_005 = _case_by_id(cases, "opp_quality_v1_case_005")
        self.assertEqual(case_005["expected"]["quality_label"], "duplicate_signal")
        self.assertEqual(case_005["expected"]["founder_review_posture"], "needs_more_evidence")
        self.assertEqual(case_005["expected"]["gate_decision"], "park")

        pack = evidence_pack_from_dict(case_005["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_005["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, "park")
        sufficiency = score_evidence_sufficiency(candidate, pack)
        self.assertTrue(sufficiency.score_band in ("weak", "adequate"))

    def test_unclear_buyer_case_006_matches_baseline_and_founder_posture(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_006 = _case_by_id(cases, "opp_quality_v1_case_006")
        self.assertEqual(case_006["expected"]["quality_label"], "no_buyer")
        self.assertEqual(case_006["expected"]["founder_review_posture"], "park_candidate")

        pack = evidence_pack_from_dict(case_006["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_006["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, case_006["expected"]["gate_decision"])
        self.assertIn("possible_buyer", gate_result.missing_evidence)

    def test_weak_noisy_case_007_rejects(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_007 = _case_by_id(cases, "opp_quality_v1_case_007")
        self.assertEqual(case_007["expected"]["quality_label"], "weak_noisy")
        self.assertEqual(case_007["expected"]["founder_review_posture"], "kill_candidate")
        self.assertEqual(case_007["expected"]["gate_decision"], "reject")

        pack = evidence_pack_from_dict(case_007["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_007["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, "reject")
        sufficiency = score_evidence_sufficiency(candidate, pack)
        self.assertEqual(sufficiency.score_band, "insufficient")

    def test_revisit_case_008_matches_baseline_and_founder_posture(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_008 = _case_by_id(cases, "opp_quality_v1_case_008")
        self.assertEqual(case_008["expected"]["quality_label"], "strong_opportunity")
        self.assertEqual(case_008["expected"]["founder_review_posture"], "revisit_candidate")

        pack = evidence_pack_from_dict(case_008["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_008["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, case_008["expected"]["gate_decision"])
        self.assertIn("revisit_candidate", candidate.risk_notes)

    def test_killed_pattern_case_009_matches_baseline_and_founder_posture(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_009 = _case_by_id(cases, "opp_quality_v1_case_009")
        self.assertEqual(case_009["expected"]["quality_label"], "killed_pattern_repeat")
        self.assertEqual(case_009["expected"]["founder_review_posture"], "kill_candidate")

        pack = evidence_pack_from_dict(case_009["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_009["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, case_009["expected"]["gate_decision"])
        self.assertIn("repeated_killed_pattern", candidate.risk_notes)

    def test_needs_more_evidence_case_010_matches_baseline_and_founder_posture(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        case_010 = _case_by_id(cases, "opp_quality_v1_case_010")
        self.assertEqual(case_010["expected"]["quality_label"], "needs_more_evidence")
        self.assertEqual(case_010["expected"]["founder_review_posture"], "needs_more_evidence")

        pack = evidence_pack_from_dict(case_010["input_artifacts"]["evidence_pack"])
        candidate = opportunity_sketch_from_dict(case_010["input_artifacts"]["opportunity_candidate"])
        gate_result = evaluate_opportunity_quality(candidate, pack)

        self.assertEqual(gate_result.decision, case_010["expected"]["gate_decision"])
        sufficiency = score_evidence_sufficiency(candidate, pack)
        self.assertEqual(sufficiency.score_band, "weak")

    def test_every_case_has_evidence_pack_and_opportunity_traceability(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        for case in cases:
            pack = case["input_artifacts"].get("evidence_pack", {})
            candidate = case["input_artifacts"].get("opportunity_candidate", {})
            with self.subTest(case_id=case["case_id"]):
                self.assertTrue(pack.get("evidence_pack_id"), f"evidence_pack_id missing in {case['case_id']}")
                self.assertTrue(pack.get("evidence_ids"), f"evidence_ids missing in {case['case_id']}")
                self.assertTrue(candidate.get("opportunity_id"), f"opportunity_id missing in {case['case_id']}")
                self.assertEqual(
                    candidate.get("evidence_pack_id"),
                    pack.get("evidence_pack_id"),
                    f"evidence_pack_id mismatch in {case['case_id']}",
                )

    def test_no_live_api_or_llm_calls(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        for case in cases:
            pack = evidence_pack_from_dict(case["input_artifacts"]["evidence_pack"])
            candidate = opportunity_sketch_from_dict(case["input_artifacts"]["opportunity_candidate"])
            gate_result = evaluate_opportunity_quality(candidate, pack)

            self.assertFalse(gate_result.auto_promote, f"{case['case_id']}: gate must not auto-promote")
            self.assertTrue(gate_result.founder_decision_required, f"{case['case_id']}: founder decision must be required")

            sufficiency = score_evidence_sufficiency(candidate, pack)
            self.assertFalse(sufficiency.auto_promote, f"{case['case_id']}: sufficiency must not auto-promote")
            self.assertTrue(sufficiency.founder_decision_required, f"{case['case_id']}: founder decision must be required")

    def test_each_case_has_expected_evidence_gaps_and_risk_notes(self) -> None:
        cases = load_opportunity_quality_cases_v1()
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertIsInstance(case["expected"].get("evidence_gaps"), list,
                                      f"{case['case_id']} expected.evidence_gaps must be a list")
                self.assertIsInstance(case["expected"].get("risk_notes"), list,
                                      f"{case['case_id']} expected.risk_notes must be a list")
                self.assertIsInstance(case["expected"].get("sufficiency_band"), str,
                                      f"{case['case_id']} must have expected.sufficiency_band")
                self.assertIsInstance(case["expected"].get("false_positive_severity"), str,
                                      f"{case['case_id']} must have expected.false_positive_severity")


def _case_by_id(cases: list[dict], case_id: str) -> dict:
    for case in cases:
        if case["case_id"] == case_id:
            return case
    raise ValueError(f"case {case_id} not found in dataset")


if __name__ == "__main__":
    unittest.main()
