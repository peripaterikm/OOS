import io
import json
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from oos.cli import main
from oos.discovery_weekly import deduplicate_ranked_candidate_signals, rank_candidate_signals
from oos.models import CandidateSignal, compute_raw_evidence_content_hash


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "examples" / "source_intelligence_mvp" / "raw_evidence_seed.json"


class TestFounderDiscoveryPackageLite(unittest.TestCase):
    def setUp(self) -> None:
        self.project_root = ROOT / "codex_tmp_founder_package_lite"
        if self.project_root.exists():
            shutil.rmtree(self.project_root)
        (self.project_root / "examples" / "source_intelligence_mvp").mkdir(parents=True)
        shutil.copy2(FIXTURE_PATH, self.project_root / "examples" / "source_intelligence_mvp" / "raw_evidence_seed.json")

    def tearDown(self) -> None:
        if self.project_root.exists():
            shutil.rmtree(self.project_root)

    def test_weekly_discovery_cli_writes_founder_package_markdown(self) -> None:
        self._run_cli("founder_md")

        self.assertTrue((self._run_dir("founder_md") / "founder_discovery_package.md").exists())

    def test_weekly_discovery_cli_writes_founder_package_json(self) -> None:
        self._run_cli("founder_json")

        self.assertTrue((self._run_dir("founder_json") / "founder_discovery_package.json").exists())

    def test_package_json_includes_run_topic_and_counts(self) -> None:
        self._run_cli("founder_counts")
        package = self._package_json("founder_counts")

        self.assertEqual(package["run_id"], "founder_counts")
        self.assertEqual(package["topic_id"], "ai_cfo_smb")
        self.assertEqual(package["raw_evidence_count"], 5)
        self.assertEqual(package["candidate_signal_count"], 5)
        self.assertEqual(package["needs_human_review_count"], 1)
        self.assertEqual(package["noise_count"], 0)

    def test_package_json_includes_top_candidate_signals(self) -> None:
        self._run_cli("founder_top")
        package = self._package_json("founder_top")

        self.assertGreaterEqual(len(package["top_candidate_signals"]), 1)

    def test_package_json_preserves_traceability_fields(self) -> None:
        self._run_cli("founder_trace")
        package = self._package_json("founder_trace")

        for signal in package["top_candidate_signals"]:
            self.assertTrue(signal["evidence_id"])
            self.assertTrue(signal["source_url"].startswith("http"))
            self.assertTrue(signal["source_type"])
            self.assertTrue(signal["query_kind"])

    def test_package_markdown_includes_executive_summary(self) -> None:
        self._run_cli("founder_exec")

        self.assertIn("## Executive summary", self._package_md("founder_exec"))

    def test_package_markdown_includes_top_candidate_signals(self) -> None:
        self._run_cli("founder_top_md")

        self.assertIn("## Top candidate signals", self._package_md("founder_top_md"))

    def test_package_markdown_includes_needs_human_review(self) -> None:
        self._run_cli("founder_review_md")

        self.assertIn("## Needs human review", self._package_md("founder_review_md"))

    def test_package_markdown_includes_recommended_founder_actions(self) -> None:
        self._run_cli("founder_actions")

        package_md = self._package_md("founder_actions")
        self.assertIn("## Recommended founder actions", package_md)
        self.assertIn("Review top candidate signals", package_md)

    def test_ranking_is_deterministic(self) -> None:
        signals = [
            self._candidate_signal("candidate_signal_z", "pain_signal", 0.8),
            self._candidate_signal("candidate_signal_a", "buying_intent", 0.8),
            self._candidate_signal("candidate_signal_high", "trend_trigger", 0.9),
        ]

        first = [signal.signal_id for signal in rank_candidate_signals(signals)]
        second = [signal.signal_id for signal in rank_candidate_signals(reversed(signals))]

        self.assertEqual(first, ["candidate_signal_high", "candidate_signal_a", "candidate_signal_z"])
        self.assertEqual(first, second)

    def test_top_candidate_signal_dedup_keeps_highest_confidence_by_source_url(self) -> None:
        lower = self._candidate_signal("candidate_signal_lower", "pain_signal", 0.72)
        higher = self._candidate_signal("candidate_signal_higher", "pain_signal", 0.89)
        duplicate_url = "https://news.ycombinator.com/item?id=12345"
        lower = self._replace_signal_url(lower, duplicate_url)
        higher = self._replace_signal_url(higher, duplicate_url)

        deduped = deduplicate_ranked_candidate_signals([lower, higher])

        self.assertEqual([signal.signal_id for signal in deduped], ["candidate_signal_higher"])

    def test_top_candidate_signal_dedup_tie_breaks_by_signal_id(self) -> None:
        later = self._replace_signal_url(
            self._candidate_signal("candidate_signal_z", "pain_signal", 0.8),
            "https://news.ycombinator.com/item?id=67890",
        )
        earlier = self._replace_signal_url(
            self._candidate_signal("candidate_signal_a", "pain_signal", 0.8),
            "https://news.ycombinator.com/item?id=67890",
        )

        deduped = deduplicate_ranked_candidate_signals([later, earlier])

        self.assertEqual([signal.signal_id for signal in deduped], ["candidate_signal_a"])

    def test_noise_is_counted_but_not_dumped_in_full(self) -> None:
        noise_input = self.project_root / "noise_raw_evidence.json"
        noise_input.write_text(json.dumps({"raw_evidence": [self._noise_raw_evidence()]}, indent=2), encoding="utf-8")

        self._run_cli("founder_noise", "--input-raw-evidence", str(noise_input))
        package = self._package_json("founder_noise")
        package_md = self._package_md("founder_noise")

        self.assertEqual(package["noise_count"], 1)
        self.assertEqual(package["candidate_signal_count"], 0)
        self.assertIn("Noise count: `1`", package_md)
        self.assertNotIn("raw_noise_evidence", package_md)

    def test_empty_zero_signal_run_still_creates_valid_package(self) -> None:
        empty_input = self.project_root / "empty_raw_evidence.json"
        empty_input.write_text(json.dumps({"raw_evidence": []}, indent=2), encoding="utf-8")

        self._run_cli("founder_empty", "--input-raw-evidence", str(empty_input))
        package = self._package_json("founder_empty")

        self.assertEqual(package["candidate_signal_count"], 0)
        self.assertEqual(package["top_candidate_signals"], [])
        self.assertIn("No candidate signals extracted.", self._package_md("founder_empty"))

    def test_no_internet_api_or_llm_calls_required(self) -> None:
        self._run_cli("founder_no_live")
        package = self._package_json("founder_no_live")

        self.assertIn("No live LLM/API calls.", package["limitations"])
        self.assertIn("No Reddit collector yet.", package["limitations"])

    def test_existing_discovery_summary_is_still_written(self) -> None:
        self._run_cli("founder_summary")

        self.assertTrue((self._run_dir("founder_summary") / "discovery_run_summary.json").exists())
        self.assertTrue((self._run_dir("founder_summary") / "discovery_run_summary.md").exists())

    def _run_cli(self, run_id: str, *extra_args: str) -> int:
        output = io.StringIO()
        with redirect_stdout(output):
            return main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    run_id,
                    *extra_args,
                ]
            )

    def _run_dir(self, run_id: str) -> Path:
        return self.project_root / "artifacts" / "discovery_runs" / run_id

    def _package_json(self, run_id: str):
        return json.loads((self._run_dir(run_id) / "founder_discovery_package.json").read_text(encoding="utf-8"))

    def _package_md(self, run_id: str) -> str:
        return (self._run_dir(run_id) / "founder_discovery_package.md").read_text(encoding="utf-8")

    def _candidate_signal(self, signal_id: str, signal_type: str, confidence: float) -> CandidateSignal:
        signal = CandidateSignal(
            signal_id=signal_id,
            evidence_id=f"evidence_{signal_id}",
            source_id="src_github_issues",
            source_type="github_issues",
            source_url=f"https://github.com/example/project/issues/{signal_id}",
            topic_id="ai_cfo_smb",
            query_kind="pain_query",
            signal_type=signal_type,
            pain_summary="A deterministic test signal.",
            target_user="developer",
            current_workaround="unknown",
            buying_intent_hint="possible" if signal_type == "buying_intent" else "not_detected",
            urgency_hint="medium",
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
            extraction_mode="rule_based_v1",
            classification=(
                "buying_intent_candidate"
                if signal_type == "buying_intent"
                else "trend_trigger_candidate"
                if signal_type == "trend_trigger"
                else "pain_signal_candidate"
            ),
            classification_confidence=confidence,
            traceability={
                "evidence_id": f"evidence_{signal_id}",
                "source_url": f"https://github.com/example/project/issues/{signal_id}",
                "source_id": "src_github_issues",
                "topic_id": "ai_cfo_smb",
                "query_kind": "pain_query",
            },
        )
        signal.validate()
        return signal

    def _replace_signal_url(self, signal: CandidateSignal, source_url: str) -> CandidateSignal:
        replacement = CandidateSignal(
            signal_id=signal.signal_id,
            evidence_id=signal.evidence_id,
            source_id=signal.source_id,
            source_type=signal.source_type,
            source_url=source_url,
            topic_id=signal.topic_id,
            query_kind=signal.query_kind,
            signal_type=signal.signal_type,
            pain_summary=signal.pain_summary,
            target_user=signal.target_user,
            current_workaround=signal.current_workaround,
            buying_intent_hint=signal.buying_intent_hint,
            urgency_hint=signal.urgency_hint,
            confidence=signal.confidence,
            measurement_methods=dict(signal.measurement_methods),
            extraction_mode=signal.extraction_mode,
            classification=signal.classification,
            classification_confidence=signal.classification_confidence,
            traceability={
                "evidence_id": signal.evidence_id,
                "source_url": source_url,
                "source_id": signal.source_id,
                "topic_id": signal.topic_id,
                "query_kind": signal.query_kind,
            },
        )
        replacement.validate()
        return replacement

    def _noise_raw_evidence(self):
        title = "Hi"
        body = "ok"
        return {
            "evidence_id": "raw_noise_evidence",
            "source_id": "src_stack_exchange",
            "source_type": "stack_exchange",
            "source_name": "Stack Exchange",
            "source_url": "https://stackoverflow.com/questions/999999/noise",
            "collected_at": "2026-04-28T00:00:00Z",
            "title": title,
            "body": body,
            "language": "unknown",
            "topic_id": "ai_cfo_smb",
            "query_kind": "pain_query",
            "content_hash": compute_raw_evidence_content_hash(title=title, body=body),
            "author_or_context": "developer",
            "raw_metadata": {"fixture": True},
            "access_policy": "fixture_only",
            "collection_method": "test_fixture",
        }


if __name__ == "__main__":
    unittest.main()
