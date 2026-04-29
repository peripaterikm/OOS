from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from oos.cli import main
from oos.live_quality_smoke import build_live_quality_smoke_report, validate_live_quality_run


TMP_ROOT = Path("codex_tmp_live_quality_smoke")


class TestLiveQualitySmoke(unittest.TestCase):
    def setUp(self) -> None:
        if TMP_ROOT.exists():
            shutil.rmtree(TMP_ROOT, ignore_errors=True)
        self.project_root = TMP_ROOT / "project"
        (self.project_root / "artifacts" / "discovery_runs").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if TMP_ROOT.exists():
            shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_passing_github_like_run_returns_pass(self) -> None:
        run_dir = self._write_run(
            "live_github_pass",
            role="github",
            noise_count=2,
            top_signals=[
                _signal("s1", "https://github.com/example/repo/issues/1", "We would need to maintain a separate spreadsheet for invoice payment status."),
                _signal("s2", "https://github.com/example/repo/issues/2", "I would like to produce a balance sheet from my accounting software."),
                _signal("s3", "https://github.com/example/repo/issues/3", "Manual spreadsheet current workaround for cash flow."),
            ],
        )

        report = validate_live_quality_run(run_dir=run_dir, role="github")

        self.assertEqual(report.overall_status, "pass")
        self.assertIn("noise_present_for_github_or_mixed_run", report.passed_checks)
        self.assertEqual(report.top_user_pain_like_count, 3)

    def test_duplicate_source_url_in_top_signals_is_detected(self) -> None:
        run_dir = self._write_run(
            "live_hn_duplicate",
            role="hn",
            top_signals=[
                _signal("s1", "https://news.ycombinator.com/item?id=1", "Invoice follow-up pain.", source_type="hacker_news_algolia"),
                _signal("s2", "https://news.ycombinator.com/item?id=1", "Invoice follow-up pain duplicate.", source_type="hacker_news_algolia"),
            ],
        )

        report = validate_live_quality_run(run_dir=run_dir, role="hn")

        self.assertEqual(report.overall_status, "fail")
        self.assertIn("duplicate_top_source_urls", report.failed_checks)
        self.assertEqual(report.duplicate_top_source_urls, ["hacker_news_algolia:https://news.ycombinator.com/item?id=1"])

    def test_mojibake_in_top_summary_is_detected(self) -> None:
        run_dir = self._write_run(
            "live_github_mojibake",
            role="github",
            noise_count=1,
            top_signals=[
                _signal("s1", "https://github.com/example/repo/issues/1", "today\u0432\u0402\u2122s invoice workflow is broken"),
                _signal("s2", "https://github.com/example/repo/issues/2", "I would like a balance sheet."),
            ],
        )

        report = validate_live_quality_run(run_dir=run_dir, role="github")

        self.assertEqual(report.overall_status, "fail")
        self.assertIn("mojibake_in_top_signal_summary", report.failed_checks)
        self.assertTrue(report.mojibake_findings)

    def test_install_tutorial_content_in_top_5_is_failure(self) -> None:
        run_dir = self._write_run(
            "live_github_install",
            role="github",
            noise_count=1,
            top_signals=[
                _signal("s1", "https://github.com/example/repo/issues/1", "When the installation process is over the computer will restart and QuickBooks will launch."),
                _signal("s2", "https://github.com/example/repo/issues/2", "I would like a balance sheet."),
            ],
        )

        report = validate_live_quality_run(run_dir=run_dir, role="github")

        self.assertEqual(report.overall_status, "fail")
        self.assertIn("install_or_tutorial_content_in_top_5", report.failed_checks)

    def test_github_or_mixed_run_with_zero_noise_fails(self) -> None:
        run_dir = self._write_run(
            "live_mix_zero_noise",
            role="mixed",
            noise_count=0,
            top_signals=[
                _signal("s1", "https://github.com/example/repo/issues/1", "We would need to maintain a separate spreadsheet."),
                _signal("s2", "https://github.com/example/repo/issues/2", "I would like a balance sheet."),
            ],
        )

        report = validate_live_quality_run(run_dir=run_dir, role="mixed")

        self.assertEqual(report.overall_status, "fail")
        self.assertIn("noise_missing_for_github_or_mixed_run", report.failed_checks)

    def test_rss_missing_feed_url_controlled_skip_passes(self) -> None:
        run_dir = self._write_run(
            "live_rss_002",
            role="rss",
            raw_evidence_count=0,
            candidate_signal_count=0,
            noise_count=0,
            top_signals=[],
            collection_errors=[{"source_type": "rss_feed", "code": "rss_feed_url_missing", "error": "missing feed"}],
            collectors_failed=[],
        )

        report = validate_live_quality_run(run_dir=run_dir, role="rss")

        self.assertEqual(report.overall_status, "pass")
        self.assertTrue(report.rss_missing_feed_url_controlled_skip)
        self.assertIn("rss_missing_feed_url_controlled_skip", report.passed_checks)

    def test_rss_unknown_url_type_fails(self) -> None:
        run_dir = self._write_run(
            "live_rss_bad",
            role="rss",
            raw_evidence_count=0,
            candidate_signal_count=0,
            top_signals=[],
            collection_errors=[{"source_type": "rss_feed", "error": "unknown url type: 'cash flow'"}],
            collectors_failed=[],
        )

        report = validate_live_quality_run(run_dir=run_dir, role="rss")

        self.assertEqual(report.overall_status, "fail")
        self.assertIn("rss_unknown_url_type_error", report.failed_checks)

    def test_generic_consulting_copy_in_top_5_is_warning_not_failure(self) -> None:
        run_dir = self._write_run(
            "live_github_generic",
            role="github",
            noise_count=1,
            top_signals=[
                _signal("s1", "https://github.com/example/repo/issues/1", "We would need to maintain a separate spreadsheet for invoices."),
                _signal("s2", "https://github.com/example/repo/issues/2", "I would like a balance sheet."),
                _signal("s3", "https://github.com/example/repo/issues/3", "In today's fast-moving business environment financial transparency is critical."),
            ],
        )

        report = validate_live_quality_run(run_dir=run_dir, role="github")

        self.assertEqual(report.overall_status, "warning")
        self.assertIn("generic_consulting_or_marketing_copy_in_top_5", report.warnings)
        self.assertNotIn("generic_consulting_or_marketing_copy_in_top_5", report.failed_checks)

    def test_top_user_pain_like_count_below_threshold_is_warning(self) -> None:
        run_dir = self._write_run(
            "live_hn_weak",
            role="hn",
            top_signals=[
                _signal("s1", "https://news.ycombinator.com/item?id=1", "Generic business discussion.", source_type="hacker_news_algolia"),
                _signal("s2", "https://news.ycombinator.com/item?id=2", "Small business operations.", source_type="hacker_news_algolia"),
                _signal("s3", "https://news.ycombinator.com/item?id=3", "Accounting software is frustrating.", source_type="hacker_news_algolia"),
            ],
        )

        report = validate_live_quality_run(run_dir=run_dir, role="hn")

        self.assertEqual(report.overall_status, "warning")
        self.assertIn("top_3_user_pain_like_count_below_threshold", report.warnings)

    def test_cli_command_writes_json_and_markdown_report(self) -> None:
        self._write_run(
            "live_github_cli",
            role="github",
            noise_count=1,
            top_signals=[
                _signal("s1", "https://github.com/example/repo/issues/1", "We would need to maintain a separate spreadsheet for invoice status."),
                _signal("s2", "https://github.com/example/repo/issues/2", "I would like to produce a balance sheet."),
            ],
        )
        output_json = self.project_root / "artifacts" / "discovery_runs" / "acceptance.json"
        output_md = self.project_root / "artifacts" / "discovery_runs" / "acceptance.md"

        exit_code = main(
            [
                "validate-live-quality-smoke",
                "--project-root",
                str(self.project_root),
                "--github-run-id",
                "live_github_cli",
                "--output",
                str(Path("artifacts") / "discovery_runs" / "acceptance.json"),
                "--output-md",
                str(Path("artifacts") / "discovery_runs" / "acceptance.md"),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(output_json.exists())
        self.assertTrue(output_md.exists())
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["aggregate_status"], "pass")
        self.assertIn("# Live Quality Acceptance Smoke", output_md.read_text(encoding="utf-8"))

    def test_aggregate_report_combines_warning_and_failure(self) -> None:
        self._write_run(
            "live_hn_warn",
            role="hn",
            top_signals=[_signal("s1", "https://news.ycombinator.com/item?id=1", "Generic business discussion.", source_type="hacker_news_algolia")],
        )
        self._write_run(
            "live_github_fail",
            role="github",
            noise_count=0,
            top_signals=[_signal("s1", "https://github.com/example/repo/issues/1", "I would like a balance sheet.")],
        )

        aggregate = build_live_quality_smoke_report(
            project_root=self.project_root,
            run_ids=["live_hn_warn", "live_github_fail"],
            run_roles={"live_hn_warn": "hn", "live_github_fail": "github"},
        )

        self.assertEqual(aggregate.aggregate_status, "fail")
        self.assertTrue(aggregate.aggregate_failed_checks)
        self.assertTrue(aggregate.aggregate_warnings)

    def _write_run(
        self,
        run_id: str,
        *,
        role: str,
        raw_evidence_count: int = 3,
        candidate_signal_count: int | None = None,
        noise_count: int = 1,
        top_signals: list[dict] | None = None,
        collection_errors: list[dict] | None = None,
        collectors_failed: list[str] | None = None,
    ) -> Path:
        top_signals = top_signals or []
        candidate_signal_count = len(top_signals) if candidate_signal_count is None else candidate_signal_count
        run_dir = self.project_root / "artifacts" / "discovery_runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "run_id": run_id,
            "topic_id": "ai_cfo_smb",
            "collection_mode": "live_collectors",
            "live_network_enabled": True,
            "raw_evidence_count": raw_evidence_count,
            "candidate_signal_count": candidate_signal_count,
            "needs_human_review_count": 0,
            "noise_count": noise_count,
            "collectors_attempted": [role if role != "github" else "github_issues"],
            "collectors_succeeded": [role if role != "github" else "github_issues"],
            "collectors_failed": [] if collectors_failed is None else collectors_failed,
            "collection_errors": [] if collection_errors is None else collection_errors,
        }
        founder_package = {
            "run_id": run_id,
            "topic_id": "ai_cfo_smb",
            "top_candidate_signals": top_signals,
        }
        meaning_loop = {
            "run_id": run_id,
            "topic_id": "ai_cfo_smb",
            "candidate_signal_count": candidate_signal_count,
            "adapted_record_count": candidate_signal_count,
        }
        _write_json(run_dir / "discovery_run_summary.json", summary)
        _write_json(run_dir / "founder_discovery_package.json", founder_package)
        _write_json(run_dir / "meaning_loop_dry_run.json", meaning_loop)
        return run_dir


def _signal(signal_id: str, source_url: str, pain_summary: str, *, source_type: str = "github_issues") -> dict:
    return {
        "signal_id": signal_id,
        "signal_type": "pain_signal",
        "source_type": source_type,
        "source_url": source_url,
        "pain_summary": pain_summary,
        "target_user": "developer",
        "current_workaround": "manual spreadsheet" if "spreadsheet" in pain_summary.lower() else "unknown",
        "buying_intent_hint": "possible",
        "urgency_hint": "medium",
        "confidence": 0.8,
        "evidence_id": f"evidence_{signal_id}",
        "query_kind": "pain_search",
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
