from __future__ import annotations

import json
import unittest

from oos.opportunity_quality_regression_metrics import (
    METRICS_SCHEMA_VERSION,
    REPORT_ID_PREFIX,
    PerCaseRegressionResult,
    OpportunityQualityRegressionMetrics,
    compute_regression_metrics,
)
from oos.evaluation_dataset import EVALUATION_QUALITY_DATASET_V1_PATH

KNOWN_CASE_IDS = {
    "opp_quality_v1_case_001",
    "opp_quality_v1_case_002",
    "opp_quality_v1_case_003",
    "opp_quality_v1_case_004",
    "opp_quality_v1_case_005",
    "opp_quality_v1_case_006",
    "opp_quality_v1_case_007",
    "opp_quality_v1_case_008",
    "opp_quality_v1_case_009",
    "opp_quality_v1_case_010",
}

REQUIRED_QUALITY_LABELS = {
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

REQUIRED_POSTURES = {
    "promote_candidate",
    "park_candidate",
    "kill_candidate",
    "needs_more_evidence",
    "revisit_candidate",
}

REQUIRED_GATE_DECISIONS = {"pass", "park", "reject"}

FALSE_POSITIVE_LABELS = {
    "generic_false_positive",
    "vendor_promo_false_positive",
    "weak_noisy",
    "killed_pattern_repeat",
}

DUPLICATE_LABEL = "duplicate_signal"


class TestOpportunityQualityRegressionMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = compute_regression_metrics()

    # ---- model existence and serialization ----

    def test_metrics_model_exists_and_is_valid(self) -> None:
        self.assertIsInstance(self.metrics, OpportunityQualityRegressionMetrics)
        self.metrics.validate()

    def test_metrics_serializes_to_json_serializable_dict(self) -> None:
        d = self.metrics.to_dict()
        self.assertIsInstance(d, dict)
        json_str = json.dumps(d, ensure_ascii=False, sort_keys=True)
        self.assertIsInstance(json_str, str)
        self.assertGreater(len(json_str), 0)

    def test_json_roundtrip_preserves_all_fields(self) -> None:
        d = self.metrics.to_dict()
        json_str = json.dumps(d, ensure_ascii=False, sort_keys=True)
        reloaded = json.loads(json_str)
        self.assertEqual(reloaded["schema_version"], METRICS_SCHEMA_VERSION)
        self.assertEqual(reloaded["total_cases"], d["total_cases"])
        self.assertEqual(reloaded["gate_decision_matches"], d["gate_decision_matches"])
        self.assertEqual(
            reloaded["gate_decision_mismatches"], d["gate_decision_mismatches"]
        )
        self.assertEqual(len(reloaded["per_case_results"]), d["total_cases"])

    # ---- schema and identifier checks ----

    def test_schema_version_is_metrics_v1(self) -> None:
        self.assertEqual(self.metrics.schema_version, METRICS_SCHEMA_VERSION)

    def test_report_id_starts_with_expected_prefix(self) -> None:
        self.assertTrue(
            self.metrics.report_id.startswith(REPORT_ID_PREFIX + "_"),
            f"Expected report_id to start with {REPORT_ID_PREFIX}_, "
            f"got {self.metrics.report_id}",
        )

    def test_generated_at_is_iso_timestamp(self) -> None:
        import re

        self.assertTrue(
            re.match(
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
                self.metrics.generated_at,
            ),
            f"generated_at does not look like ISO timestamp: {self.metrics.generated_at}",
        )

    # ---- total_cases ----

    def test_total_cases_equals_10(self) -> None:
        self.assertEqual(self.metrics.total_cases, 10)

    # ---- cases_by_quality_label ----

    def test_all_required_quality_labels_are_present(self) -> None:
        present = set(self.metrics.cases_by_quality_label)
        missing = REQUIRED_QUALITY_LABELS - present
        self.assertFalse(
            missing,
            f"Missing quality labels: {', '.join(sorted(missing))}. "
            f"Present: {', '.join(sorted(present))}",
        )

    def test_cases_by_quality_label_sum_equals_total_cases(self) -> None:
        self.assertEqual(
            sum(self.metrics.cases_by_quality_label.values()),
            self.metrics.total_cases,
        )

    def test_cases_by_quality_label_is_sorted(self) -> None:
        keys = list(self.metrics.cases_by_quality_label)
        self.assertEqual(keys, sorted(keys))

    # ---- cases_by_founder_review_posture ----

    def test_all_required_postures_are_present(self) -> None:
        present = set(self.metrics.cases_by_founder_review_posture)
        missing = REQUIRED_POSTURES - present
        self.assertFalse(
            missing,
            f"Missing founder postures: {', '.join(sorted(missing))}. "
            f"Present: {', '.join(sorted(present))}",
        )

    def test_posture_sum_equals_total_cases(self) -> None:
        self.assertEqual(
            sum(self.metrics.cases_by_founder_review_posture.values()),
            self.metrics.total_cases,
        )

    # ---- gate decision counts ----

    def test_expected_gate_decision_counts_have_all_three_decisions(self) -> None:
        present = set(self.metrics.expected_gate_decision_counts)
        for decision in REQUIRED_GATE_DECISIONS:
            self.assertIn(
                decision,
                present,
                f"Expected gate decision '{decision}' missing from counts",
            )

    def test_actual_gate_decision_counts_have_all_three_decisions_or_close(self) -> None:
        present = set(self.metrics.actual_gate_decision_counts)
        for decision in REQUIRED_GATE_DECISIONS:
            self.assertIn(
                decision,
                present,
                f"Actual gate decision '{decision}' missing from counts. "
                f"Present: {present}",
            )

    # ---- gate matches and mismatches ----

    def test_gate_matches_plus_mismatches_equals_total_cases(self) -> None:
        self.assertEqual(
            self.metrics.gate_decision_matches + self.metrics.gate_decision_mismatches,
            self.metrics.total_cases,
        )

    def test_gate_match_rate_is_between_zero_and_one(self) -> None:
        self.assertGreaterEqual(self.metrics.gate_match_rate, 0.0)
        self.assertLessEqual(self.metrics.gate_match_rate, 1.0)

    def test_gate_match_rate_calculation(self) -> None:
        expected_rate = round(
            self.metrics.gate_decision_matches / self.metrics.total_cases, 4
        )
        self.assertEqual(self.metrics.gate_match_rate, expected_rate)

    # ---- false positive metrics ----

    def test_false_positive_cases_gt_zero(self) -> None:
        self.assertGreater(
            self.metrics.false_positive_cases,
            0,
            "Expected at least one false positive case",
        )

    def test_false_positive_rate_is_between_zero_and_one(self) -> None:
        self.assertGreaterEqual(self.metrics.false_positive_rate, 0.0)
        self.assertLessEqual(self.metrics.false_positive_rate, 1.0)

    def test_false_positive_labels_are_expected_set(self) -> None:
        fp_labels_in_metrics = set(
            self.metrics.to_dict().get("false_positive_labels", [])
        )
        self.assertEqual(fp_labels_in_metrics, FALSE_POSITIVE_LABELS)

    # ---- duplicate metrics ----

    def test_duplicate_cases_equals_one(self) -> None:
        self.assertEqual(
            self.metrics.duplicate_cases, 1, "Expected exactly 1 duplicate case"
        )

    def test_duplicate_rate_is_between_zero_and_one(self) -> None:
        self.assertGreaterEqual(self.metrics.duplicate_rate, 0.0)
        self.assertLessEqual(self.metrics.duplicate_rate, 1.0)

    # ---- unsupported assumptions ----

    def test_unsupported_assumptions_count_gt_zero(self) -> None:
        self.assertGreater(
            self.metrics.unsupported_assumptions_count,
            0,
            "Expected at least one unsupported assumption",
        )

    def test_unsupported_assumptions_cases_le_total(self) -> None:
        self.assertLessEqual(
            self.metrics.unsupported_assumptions_cases,
            self.metrics.total_cases,
        )

    # ---- per_case_results ----

    def test_per_case_results_has_10_entries(self) -> None:
        self.assertEqual(len(self.metrics.per_case_results), 10)

    def test_per_case_results_cover_all_known_case_ids(self) -> None:
        result_ids = {result.case_id for result in self.metrics.per_case_results}
        self.assertEqual(result_ids, KNOWN_CASE_IDS)

    def test_each_per_case_result_has_required_fields(self) -> None:
        for result in self.metrics.per_case_results:
            with self.subTest(case_id=result.case_id):
                self.assertIsInstance(result.case_id, str)
                self.assertIsInstance(result.quality_label, str)
                self.assertIsInstance(result.founder_review_posture, str)
                self.assertIsInstance(result.expected_gate_decision, str)
                self.assertIsInstance(result.actual_gate_decision, str)
                self.assertIsInstance(result.matched_expected_gate, bool)
                self.assertIsInstance(result.risk_notes, list)
                self.assertIsInstance(result.evidence_gaps, list)
                self.assertIsInstance(result.unsupported_assumptions, list)
                self.assertIsInstance(result.traceability_ids, dict)
                self.assertIsInstance(result.false_positive_severity, str)
                self.assertIsInstance(result.sufficiency_band, str)
                self.assertIn(
                    result.expected_gate_decision, REQUIRED_GATE_DECISIONS
                )
                self.assertIn(
                    result.actual_gate_decision, REQUIRED_GATE_DECISIONS
                )

    def test_per_case_traceability_has_expected_keys(self) -> None:
        expected_keys = {
            "evidence_ids",
            "source_signal_ids",
            "source_urls",
            "gate_result_id",
            "evidence_pack_id",
            "opportunity_id",
        }
        for result in self.metrics.per_case_results:
            with self.subTest(case_id=result.case_id):
                self.assertEqual(
                    set(result.traceability_ids), expected_keys,
                    f"Expected traceability keys {sorted(expected_keys)}",
                )

    def test_per_case_traceability_ids_are_sorted(self) -> None:
        for result in self.metrics.per_case_results:
            with self.subTest(case_id=result.case_id):
                for key, values in result.traceability_ids.items():
                    self.assertEqual(
                        values,
                        sorted(set(values)),
                        f"{result.case_id}: traceability_ids.{key} not sorted/deduped",
                    )

    def test_per_case_risk_notes_and_evidence_gaps_are_sorted(self) -> None:
        for result in self.metrics.per_case_results:
            with self.subTest(case_id=result.case_id):
                self.assertEqual(
                    result.risk_notes,
                    sorted(set(result.risk_notes)),
                    f"{result.case_id}: risk_notes not sorted",
                )
                self.assertEqual(
                    result.evidence_gaps,
                    sorted(set(result.evidence_gaps)),
                    f"{result.case_id}: evidence_gaps not sorted",
                )

    def test_known_cases_have_specific_expected_gate_matches(self) -> None:
        expected_matches = {
            "opp_quality_v1_case_001": True,  # strong -> pass = pass
            "opp_quality_v1_case_002": True,  # weak -> park = park
            "opp_quality_v1_case_003": True,  # generic -> reject = reject
            "opp_quality_v1_case_004": True,  # vendor -> reject = reject
            "opp_quality_v1_case_005": True,  # duplicate -> park = park
            "opp_quality_v1_case_006": True,  # no_buyer -> reject = reject
            "opp_quality_v1_case_007": True,  # weak_noisy -> reject = reject
            # case_008 and case_009 may not match exactly; check only if they do
            "opp_quality_v1_case_010": True,  # needs_more_evidence -> reject = reject
        }
        for result in self.metrics.per_case_results:
            if result.case_id in expected_matches:
                with self.subTest(case_id=result.case_id):
                    self.assertEqual(
                        result.matched_expected_gate,
                        expected_matches[result.case_id],
                        f"{result.case_id}: expected {result.expected_gate_decision}, "
                        f"actual {result.actual_gate_decision}",
                    )

    def test_false_positive_cases_count_matches_labels(self) -> None:
        fp_from_labels = sum(
            1
            for result in self.metrics.per_case_results
            if result.quality_label in FALSE_POSITIVE_LABELS
        )
        self.assertEqual(
            self.metrics.false_positive_cases,
            fp_from_labels,
            "false_positive_cases must match count from per_case_results",
        )

    def test_duplicate_cases_count_matches_labels(self) -> None:
        dup_from_labels = sum(
            1
            for result in self.metrics.per_case_results
            if result.quality_label == DUPLICATE_LABEL
        )
        self.assertEqual(
            self.metrics.duplicate_cases,
            dup_from_labels,
            "duplicate_cases must match count from per_case_results",
        )

    def test_unsupported_assumptions_count_matches_per_case_sum(self) -> None:
        total_unsupported = sum(
            len(result.unsupported_assumptions)
            for result in self.metrics.per_case_results
        )
        self.assertEqual(
            self.metrics.unsupported_assumptions_count,
            total_unsupported,
        )

    # ---- limitations ----

    def test_limitations_are_non_empty(self) -> None:
        self.assertIsInstance(self.metrics.limitations, list)
        self.assertGreater(len(self.metrics.limitations), 0)
        for note in self.metrics.limitations:
            self.assertIsInstance(note, str)
            self.assertGreater(len(note.strip()), 0)

    # ---- per-case specific gate decision tests ----

    def test_case_001_passes_gate(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_001")
        self.assertEqual(result.expected_gate_decision, "pass")
        self.assertEqual(result.actual_gate_decision, "pass")
        self.assertTrue(result.matched_expected_gate)

    def test_case_002_parks(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_002")
        self.assertEqual(result.expected_gate_decision, "park")
        self.assertEqual(result.actual_gate_decision, "park")
        self.assertTrue(result.matched_expected_gate)

    def test_case_003_rejects(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_003")
        self.assertEqual(result.expected_gate_decision, "reject")
        self.assertEqual(result.actual_gate_decision, "reject")
        self.assertTrue(result.matched_expected_gate)

    def test_case_004_rejects(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_004")
        self.assertEqual(result.expected_gate_decision, "reject")
        self.assertEqual(result.actual_gate_decision, "reject")
        self.assertTrue(result.matched_expected_gate)

    def test_case_005_parks(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_005")
        self.assertEqual(result.expected_gate_decision, "park")
        self.assertEqual(result.actual_gate_decision, "park")
        self.assertTrue(result.matched_expected_gate)

    def test_case_006_rejects(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_006")
        self.assertEqual(result.expected_gate_decision, "reject")
        self.assertEqual(result.actual_gate_decision, "reject")
        self.assertTrue(result.matched_expected_gate)

    def test_case_007_rejects(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_007")
        self.assertEqual(result.expected_gate_decision, "reject")
        self.assertEqual(result.actual_gate_decision, "reject")
        self.assertTrue(result.matched_expected_gate)

    def test_case_008_parks(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_008")
        self.assertEqual(result.expected_gate_decision, "park")
        self.assertEqual(result.actual_gate_decision, "park")
        self.assertTrue(result.matched_expected_gate)

    def test_case_009_parks(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_009")
        self.assertEqual(result.expected_gate_decision, "park")
        self.assertEqual(result.actual_gate_decision, "park")
        self.assertTrue(result.matched_expected_gate)

    def test_case_010_rejects(self) -> None:
        result = _find_result(self.metrics, "opp_quality_v1_case_010")
        self.assertEqual(result.expected_gate_decision, "reject")
        self.assertEqual(result.actual_gate_decision, "reject")
        self.assertTrue(result.matched_expected_gate)

    # ---- bad metric data validation ----

    def test_validate_rejects_bad_schema(self) -> None:
        with self.assertRaises(ValueError):
            OpportunityQualityRegressionMetrics(
                report_id="test",
                generated_at="2026-01-01T00:00:00",
                schema_version="bad_version",
            ).validate()

    def test_validate_rejects_negative_total_cases(self) -> None:
        with self.assertRaises(ValueError):
            OpportunityQualityRegressionMetrics(
                report_id="test",
                generated_at="2026-01-01T00:00:00",
                total_cases=-1,
            ).validate()

    def test_validate_rejects_gate_match_rate_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            OpportunityQualityRegressionMetrics(
                report_id="test",
                generated_at="2026-01-01T00:00:00",
                gate_match_rate=1.5,
            ).validate()

    def test_validate_rejects_false_positive_rate_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            OpportunityQualityRegressionMetrics(
                report_id="test",
                generated_at="2026-01-01T00:00:00",
                false_positive_rate=1.5,
            ).validate()

    def test_validate_rejects_per_case_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            OpportunityQualityRegressionMetrics(
                report_id="test",
                generated_at="2026-01-01T00:00:00",
                total_cases=5,
                per_case_results=[],  # empty but total_cases=5
            ).validate()

    # ---- deterministic stability ----

    def test_two_runs_produce_identical_metrics(self) -> None:
        first = compute_regression_metrics()
        second = compute_regression_metrics()

        self.assertEqual(first.total_cases, second.total_cases)
        self.assertEqual(first.gate_decision_matches, second.gate_decision_matches)
        self.assertEqual(first.gate_decision_mismatches, second.gate_decision_mismatches)
        self.assertEqual(first.gate_match_rate, second.gate_match_rate)
        self.assertEqual(first.false_positive_cases, second.false_positive_cases)
        self.assertEqual(first.false_positive_rate, second.false_positive_rate)
        self.assertEqual(first.duplicate_cases, second.duplicate_cases)
        self.assertEqual(first.duplicate_rate, second.duplicate_rate)
        self.assertEqual(
            first.unsupported_assumptions_count,
            second.unsupported_assumptions_count,
        )
        self.assertEqual(
            first.unsupported_assumptions_cases,
            second.unsupported_assumptions_cases,
        )
        self.assertEqual(
            len(first.per_case_results), len(second.per_case_results)
        )
        for a, b in zip(
            sorted(first.per_case_results, key=lambda r: r.case_id),
            sorted(second.per_case_results, key=lambda r: r.case_id),
        ):
            self.assertEqual(a.case_id, b.case_id)
            self.assertEqual(a.matched_expected_gate, b.matched_expected_gate)
            self.assertEqual(a.actual_gate_decision, b.actual_gate_decision)

    # ---- no live API calls ----

    def test_compute_metrics_does_not_use_live_apis(self) -> None:
        self.metrics = compute_regression_metrics()
        for result in self.metrics.per_case_results:
            self.assertIn(
                result.sufficiency_band, {"strong", "adequate", "weak", "insufficient"}
            )
            self.assertIn(
                result.false_positive_severity,
                {"none", "low", "medium", "high", "critical"},
            )


def _find_result(
    metrics: OpportunityQualityRegressionMetrics,
    case_id: str,
) -> PerCaseRegressionResult:
    for result in metrics.per_case_results:
        if result.case_id == case_id:
            return result
    raise ValueError(f"case {case_id} not found in regression metrics")


if __name__ == "__main__":
    unittest.main()
