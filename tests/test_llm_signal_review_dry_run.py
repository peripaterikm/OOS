from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from oos.cli import main
from oos.llm_contracts import DeterministicMockLLMProvider
from oos.llm_signal_review import LLMSignalReviewInput, LLMSignalReviewOutput, run_deterministic_mock_signal_review
from oos.llm_signal_review import build_safe_signal_review_request
from oos.llm_signal_review_dry_run import (
    LLMSignalReviewDryRunInput,
    build_signal_review_input,
    load_llm_signal_review_dry_run_artifacts,
    run_llm_signal_review_dry_run,
    select_candidate_signals_for_review,
    write_llm_signal_review_dry_run_report,
)
from oos.models import CandidateSignal, CleanedEvidence, model_to_dict


ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / "codex_tmp_llm_signal_review_dry_run"


def _candidate(
    signal_id: str,
    evidence_id: str,
    confidence: float,
    *,
    signal_type: str = "pain_signal",
    source_url: str = "https://example.test/issues/1",
) -> CandidateSignal:
    return CandidateSignal(
        signal_id=signal_id,
        evidence_id=evidence_id,
        source_id="github_ai_cfo",
        source_type="github_issues",
        source_url=source_url,
        topic_id="ai_cfo_smb",
        query_kind="customer_voice_query",
        signal_type=signal_type,
        pain_summary="Manual invoice payment tracking is painful.",
        target_user="freelancer",
        current_workaround="manual spreadsheet",
        buying_intent_hint="looking for automation",
        urgency_hint="late payment due dates",
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
        extraction_mode="deterministic_rules",
        classification="pain_signal_candidate",
        classification_confidence=confidence,
        traceability={
            "evidence_id": evidence_id,
            "source_url": source_url,
            "source_id": "github_ai_cfo",
            "topic_id": "ai_cfo_smb",
            "query_kind": "customer_voice_query",
        },
        scoring_model_version="signal_scoring_v2",
        scoring_breakdown={"final_score": confidence},
    )


def _cleaned(evidence_id: str, *, body: str = "I use a manual spreadsheet to track invoice payments.") -> CleanedEvidence:
    return CleanedEvidence(
        evidence_id=evidence_id,
        source_id="github_ai_cfo",
        source_type="github_issues",
        source_url=f"https://example.test/issues/{evidence_id}",
        topic_id="ai_cfo_smb",
        query_kind="customer_voice_query",
        title="Invoice payment tracking",
        body=body,
        normalized_title="invoice payment tracking",
        normalized_body=body,
        normalized_url=f"https://example.test/issues/{evidence_id}",
        normalized_content_hash=f"hash_{evidence_id}",
        language="en",
        original_content_hash=f"raw_{evidence_id}",
        cleaning_notes=["fixture"],
    )


class TestLLMSignalReviewDryRun(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)
        self.project_root = TMP_ROOT / "project"
        self.run_dir = self.project_root / "artifacts" / "discovery_runs" / "fixture_run"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.candidates = [
            _candidate("sig_b", "ev_b", 0.91, source_url="https://example.test/issues/b"),
            _candidate("sig_a", "ev_a", 0.82, source_url="https://example.test/issues/a"),
            _candidate("sig_review", "ev_review", 0.79, signal_type="needs_human_review"),
            _candidate("sig_low", "ev_low", 0.31, source_url="https://example.test/issues/low"),
        ]
        self.cleaned = [
            _cleaned("ev_b"),
            _cleaned("ev_a"),
            _cleaned("ev_review"),
            _cleaned("ev_low"),
        ]
        self._write_artifacts()

    def tearDown(self) -> None:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def _write_artifacts(self) -> None:
        (self.run_dir / "candidate_signals.json").write_text(
            json.dumps([model_to_dict(item) for item in self.candidates], indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (self.run_dir / "cleaned_evidence.json").write_text(
            json.dumps([model_to_dict(item) for item in self.cleaned], indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _input(self, **overrides) -> LLMSignalReviewDryRunInput:
        values = {
            "project_root": self.project_root,
            "discovery_run_id": "fixture_run",
            "review_run_id": "dry_run_001",
            "topic_id": "ai_cfo_smb",
            "max_signals": 5,
            "min_confidence": 0.0,
            "include_needs_human_review": False,
        }
        values.update(overrides)
        return LLMSignalReviewDryRunInput(**values)

    def test_dry_run_loads_candidate_signals_and_cleaned_evidence(self) -> None:
        candidates, cleaned = load_llm_signal_review_dry_run_artifacts(self._input())

        self.assertEqual(len(candidates), 4)
        self.assertEqual(len(cleaned), 4)

    def test_missing_candidate_signals_json_fails_clearly(self) -> None:
        (self.run_dir / "candidate_signals.json").unlink()

        with self.assertRaisesRegex(ValueError, "candidate_signals.json not found"):
            load_llm_signal_review_dry_run_artifacts(self._input())

    def test_missing_cleaned_evidence_json_fails_clearly(self) -> None:
        (self.run_dir / "cleaned_evidence.json").unlink()

        with self.assertRaisesRegex(ValueError, "cleaned_evidence.json not found"):
            load_llm_signal_review_dry_run_artifacts(self._input())

    def test_selected_candidate_signals_are_ordered_deterministically(self) -> None:
        selected = select_candidate_signals_for_review(
            self.candidates,
            max_signals=3,
            min_confidence=0.0,
            include_needs_human_review=True,
        )

        self.assertEqual([item.signal_id for item in selected], ["sig_b", "sig_a", "sig_review"])

    def test_max_signals_cap_works(self) -> None:
        report = run_llm_signal_review_dry_run(self._input(max_signals=1))

        self.assertEqual(report.review_items_created, 1)
        self.assertEqual(report.items[0].candidate_signal_id, "sig_b")

    def test_min_confidence_filter_works(self) -> None:
        report = run_llm_signal_review_dry_run(self._input(min_confidence=0.9))

        self.assertEqual(report.review_items_created, 1)
        self.assertEqual(report.items[0].candidate_signal_id, "sig_b")

    def test_builds_safe_llm_request_via_prompt_safety(self) -> None:
        report = run_llm_signal_review_dry_run(self._input(max_signals=1))

        self.assertEqual(report.safe_requests_built, 1)
        self.assertFalse(report.llm_calls_made)

    def test_pii_in_evidence_is_redacted_in_safe_request_path(self) -> None:
        signal = self.candidates[0]
        cleaned = _cleaned("ev_b", body="Email owner@example.com about invoice payment tracking.")
        review_input = build_signal_review_input(dry_run_input=self._input(), signal=signal, cleaned=cleaned)
        safe_request, report = build_safe_signal_review_request(review_input)

        self.assertIsNotNone(safe_request)
        self.assertIn("[EMAIL_REDACTED]", "\n".join(message.content for message in safe_request.messages))
        self.assertFalse(report.external_calls_made)

    def test_secrets_private_keys_cards_block_item_fail_closed(self) -> None:
        self.cleaned[0] = _cleaned("ev_b", body="Secret sk-1234567890abcdefghijkl should block.")
        self._write_artifacts()

        report = run_llm_signal_review_dry_run(self._input(max_signals=1))

        self.assertEqual(report.blocked_by_prompt_safety, 1)
        self.assertTrue(report.items[0].blocked_by_prompt_safety)
        self.assertIn("blocked_pii_type:secret", report.items[0].prompt_safety_reasons)

    def test_blocked_items_do_not_produce_review_output(self) -> None:
        self.cleaned[0] = _cleaned("ev_b", body="Card 4111111111111111 should block.")
        self._write_artifacts()

        report = run_llm_signal_review_dry_run(self._input(max_signals=1))

        self.assertIsNone(report.items[0].review_output)
        self.assertFalse(report.items[0].mock_review_valid)

    def test_deterministic_mock_review_produces_valid_output_with_evidence_citation(self) -> None:
        report = run_llm_signal_review_dry_run(self._input(max_signals=1))

        self.assertEqual(report.valid_reviews, 1)
        output = report.items[0].review_output
        self.assertIsNotNone(output)
        self.assertEqual(output["evidence_ids_cited"], ["ev_b"])
        self.assertTrue(output["evidence_cited"])

    def test_validation_errors_are_recorded_if_output_invalid(self) -> None:
        def invalid_runner(review_input: LLMSignalReviewInput) -> LLMSignalReviewOutput:
            output = run_deterministic_mock_signal_review(review_input)
            return LLMSignalReviewOutput(
                **{
                    **output.to_dict(),
                    "evidence_ids_cited": ["unknown_ev"],
                    "jtbd_statements": output.jtbd_statements,
                }
            )

        report = run_llm_signal_review_dry_run(self._input(max_signals=1), mock_review_runner=invalid_runner)

        self.assertEqual(report.invalid_reviews, 1)
        self.assertIn("unknown_evidence_ids:unknown_ev", report.items[0].validation_errors)

    def test_json_report_is_deterministic(self) -> None:
        output_dir = self.project_root / "reports" / "dry"
        report = run_llm_signal_review_dry_run(self._input(max_signals=2))
        json_path, _ = write_llm_signal_review_dry_run_report(report, output_dir=output_dir)
        first = json_path.read_text(encoding="utf-8")
        write_llm_signal_review_dry_run_report(report, output_dir=output_dir)
        second = json_path.read_text(encoding="utf-8")

        self.assertEqual(first, second)

    def test_markdown_report_includes_summary_safety_and_limitations(self) -> None:
        output_dir = self.project_root / "reports" / "dry"
        report = run_llm_signal_review_dry_run(self._input(max_signals=1))
        _, md_path = write_llm_signal_review_dry_run_report(report, output_dir=output_dir)
        markdown = md_path.read_text(encoding="utf-8")

        self.assertIn("## Summary", markdown)
        self.assertIn("## Safety", markdown)
        self.assertIn("## Limitations", markdown)

    def test_cli_writes_json_and_markdown(self) -> None:
        output_dir = self.project_root / "custom_output"
        exit_code = main(
            [
                "run-llm-signal-review-dry-run",
                "--project-root",
                str(self.project_root),
                "--discovery-run-id",
                "fixture_run",
                "--review-run-id",
                "cli_dry",
                "--topic",
                "ai_cfo_smb",
                "--max-signals",
                "2",
                "--min-confidence",
                "0.5",
                "--output-dir",
                str(output_dir),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((output_dir / "llm_signal_review_dry_run.json").exists())
        self.assertTrue((output_dir / "llm_signal_review_dry_run.md").exists())

    def test_no_provider_complete_is_called(self) -> None:
        with patch.object(DeterministicMockLLMProvider, "complete", side_effect=AssertionError("provider called")):
            report = run_llm_signal_review_dry_run(self._input(max_signals=1))

        self.assertFalse(report.llm_calls_made)
        self.assertFalse(report.external_calls_made)

    def test_report_says_no_llm_or_external_calls(self) -> None:
        report = run_llm_signal_review_dry_run(self._input(max_signals=1))

        self.assertFalse(report.llm_calls_made)
        self.assertFalse(report.external_calls_made)
        self.assertEqual(report.provider_used, "deterministic_mock_contract_only")

    def test_traceability_preserves_candidate_signal_evidence_and_source_url(self) -> None:
        report = run_llm_signal_review_dry_run(self._input(max_signals=1))
        item = report.items[0]

        self.assertEqual(item.candidate_signal_id, "sig_b")
        self.assertEqual(item.evidence_id, "ev_b")
        self.assertEqual(item.source_url, "https://example.test/issues/b")


if __name__ == "__main__":
    unittest.main()
