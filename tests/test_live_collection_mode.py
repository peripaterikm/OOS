from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from oos.cli import main
from oos.collection_scheduler import ScheduledCollectionItem
from oos.collectors import BaseCollector, CollectionResult
from oos.live_collection import collect_raw_evidence_for_topic
from oos.models import RawEvidence, compute_raw_evidence_content_hash


ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / "codex_tmp_live_collection_mode"


HN_PAYLOAD = {
    "hits": [
        {
            "objectID": "401",
            "title": "Cashflow problem for SMB finance teams",
            "story_text": "We struggle with cashflow forecasting and need a tool.",
            "created_at": "2026-01-01T00:00:00Z",
            "author": "raw_hn_user",
            "points": 10,
            "_tags": ["story"],
        }
    ]
}

GITHUB_PAYLOAD = {
    "items": [
        {
            "id": 90210,
            "node_id": "I_kwDO",
            "number": 17,
            "html_url": "https://github.com/example/project/issues/17",
            "title": "Need a tool for finance reporting",
            "body": "Looking for a better way to handle SMB cashflow reporting.",
            "created_at": "2026-01-02T00:00:00Z",
            "state": "open",
            "comments": 3,
            "labels": [{"name": "enhancement"}],
            "user": {"login": "raw_github_login"},
        }
    ]
}


class FailingCollector(BaseCollector):
    def supports(self, scheduled_item: ScheduledCollectionItem) -> bool:
        return scheduled_item.source_type == "hacker_news_algolia"

    def collect(self, scheduled_item: ScheduledCollectionItem) -> CollectionResult:
        raise RuntimeError("simulated collector failure")


class TestLiveCollectionMode(unittest.TestCase):
    def setUp(self) -> None:
        if TMP_ROOT.exists():
            shutil.rmtree(TMP_ROOT)
        TMP_ROOT.mkdir(parents=True)
        self.project_root = TMP_ROOT / "project"
        shutil.copytree(ROOT / "examples", self.project_root / "examples")

    def tearDown(self) -> None:
        if TMP_ROOT.exists():
            shutil.rmtree(TMP_ROOT)

    def test_default_weekly_discovery_cli_still_runs_fixture_mode_without_network(self) -> None:
        with patch("oos.hn_algolia_collector.urlopen", side_effect=AssertionError("network not allowed")):
            exit_code = main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "fixture_default",
                ]
            )
        self.assertEqual(exit_code, 0)
        summary = self._summary("fixture_default")
        self.assertEqual(summary["collection_mode"], "fixture")
        self.assertFalse(summary["live_network_enabled"])

    def test_use_collectors_without_allow_live_network_does_not_call_network(self) -> None:
        with patch("oos.hn_algolia_collector.urlopen", side_effect=AssertionError("network not allowed")):
            exit_code = main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "collectors_offline",
                    "--use-collectors",
                    "--source-id",
                    "hacker_news_algolia",
                ]
            )
        self.assertEqual(exit_code, 0)
        summary = self._summary("collectors_offline")
        self.assertEqual(summary["collection_mode"], "collectors_offline")
        self.assertFalse(summary["live_network_enabled"])
        self.assertEqual(summary["raw_evidence_count"], 0)

    def test_use_collectors_with_allow_live_network_routes_to_mocked_collectors(self) -> None:
        self._run_hn_live("hn_live")
        summary = self._summary("hn_live")
        self.assertEqual(summary["collection_mode"], "live_collectors")
        self.assertTrue(summary["live_network_enabled"])
        self.assertEqual(summary["raw_evidence_count"], 1)
        self.assertGreaterEqual(summary["candidate_signal_count"], 1)

    def test_cli_writes_standard_discovery_artifacts_in_collector_mode(self) -> None:
        self._run_hn_live("artifacts")
        run_dir = self.project_root / "artifacts" / "discovery_runs" / "artifacts"
        for filename in (
            "raw_evidence_index.json",
            "cleaned_evidence.json",
            "evidence_classifications.json",
            "candidate_signals.json",
            "discovery_run_summary.json",
            "founder_discovery_package.md",
        ):
            self.assertTrue((run_dir / filename).exists(), filename)

    def test_summary_includes_collection_mode_and_counts(self) -> None:
        self._run_hn_live("summary_counts")
        summary = self._summary("summary_counts")
        self.assertEqual(summary["collection_mode"], "live_collectors")
        self.assertGreater(summary["query_plan_count"], 0)
        self.assertEqual(summary["scheduled_query_count"], 1)

    def test_collection_limits_are_honored(self) -> None:
        with patch("oos.hn_algolia_collector.HNAlgoliaCollector._fetch_live_payload", return_value=HN_PAYLOAD):
            exit_code = main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "limits",
                    "--use-collectors",
                    "--allow-live-network",
                    "--source-id",
                    "hacker_news_algolia",
                    "--max-total-queries",
                    "1",
                    "--max-results-per-query",
                    "1",
                ]
            )
        self.assertEqual(exit_code, 0)
        summary = self._summary("limits")
        self.assertEqual(summary["scheduled_query_count"], 1)
        self.assertEqual(summary["max_results_per_query"], 1)
        self.assertEqual(summary["raw_evidence_count"], 1)

    def test_source_id_filtering_works(self) -> None:
        self._run_hn_live("source_filter")
        summary = self._summary("source_filter")
        self.assertEqual(summary["source_ids_filter"], ["hacker_news_algolia"])
        self.assertEqual(summary["collectors_attempted"], ["hacker_news_algolia"])

    def test_source_type_filtering_works(self) -> None:
        with patch("oos.github_issues_collector.GitHubIssuesCollector._fetch_live_payload", return_value=GITHUB_PAYLOAD):
            exit_code = main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "source_type_filter",
                    "--use-collectors",
                    "--allow-live-network",
                    "--source-type",
                    "github_issues",
                    "--max-total-queries",
                    "1",
                ]
            )
        self.assertEqual(exit_code, 0)
        summary = self._summary("source_type_filter")
        self.assertEqual(summary["source_types_filter"], ["github_issues"])
        self.assertEqual(summary["collectors_attempted"], ["github_issues"])

    def test_hn_mocked_live_response_becomes_raw_evidence_and_candidate_signal(self) -> None:
        self._run_hn_live("hn_signal")
        raw_index = self._json("hn_signal", "raw_evidence_index.json")
        signals = self._json("hn_signal", "candidate_signals.json")
        self.assertEqual(raw_index[0]["source_type"], "hacker_news_algolia")
        self.assertEqual(raw_index[0]["source_url"], "https://news.ycombinator.com/item?id=401")
        self.assertTrue(signals)

    def test_github_mocked_live_response_becomes_raw_evidence_and_candidate_signal(self) -> None:
        with patch("oos.github_issues_collector.GitHubIssuesCollector._fetch_live_payload", return_value=GITHUB_PAYLOAD):
            exit_code = main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "github_signal",
                    "--use-collectors",
                    "--allow-live-network",
                    "--source-id",
                    "github_issues",
                    "--max-total-queries",
                    "1",
                    "--max-results-per-query",
                    "1",
                ]
            )
        self.assertEqual(exit_code, 0)
        raw_index = self._json("github_signal", "raw_evidence_index.json")
        signals = self._json("github_signal", "candidate_signals.json")
        self.assertEqual(raw_index[0]["source_type"], "github_issues")
        self.assertEqual(raw_index[0]["source_url"], "https://github.com/example/project/issues/17")
        self.assertTrue(signals)

    def test_collector_error_is_recorded_without_killing_whole_run(self) -> None:
        result = collect_raw_evidence_for_topic(
            topic_id="ai_cfo_smb",
            allow_live_network=True,
            max_total_queries=1,
            allowed_source_ids={"hacker_news_algolia"},
            collector_factories={"hacker_news_algolia": lambda allow_live_network: FailingCollector()},
        )
        self.assertEqual(result.raw_evidence, [])
        self.assertEqual(result.collection_metadata["collectors_failed"], ["hacker_news_algolia"])
        self.assertIn("simulated collector failure", result.collection_metadata["collection_errors"][0]["error"])

    def test_source_url_and_evidence_id_traceability_is_preserved(self) -> None:
        self._run_hn_live("traceability", "--include-meaning-loop-dry-run")
        raw_index = self._json("traceability", "raw_evidence_index.json")
        signals = self._json("traceability", "candidate_signals.json")
        dry_run = self._json("traceability", "meaning_loop_dry_run.json")
        self.assertEqual(signals[0]["evidence_id"], raw_index[0]["evidence_id"])
        trace = dry_run["traceability_map"][signals[0]["signal_id"]]
        self.assertEqual(trace["evidence_id"], raw_index[0]["evidence_id"])
        self.assertEqual(trace["source_url"], raw_index[0]["source_url"])

    def test_usernames_logins_and_display_names_are_not_stored_in_raw_metadata(self) -> None:
        result = collect_raw_evidence_for_topic(
            topic_id="ai_cfo_smb",
            allow_live_network=True,
            max_total_queries=1,
            max_results_per_query=1,
            allowed_source_ids={"github_issues"},
            collector_factories={
                "github_issues": lambda allow_live_network: _GitHubFixtureCollector(),
            },
        )
        metadata_text = json.dumps(result.raw_evidence[0].raw_metadata, sort_keys=True)
        self.assertNotIn("raw_github_login", metadata_text)
        self.assertNotIn("login", metadata_text)

    def test_meaning_loop_dry_run_works_with_collector_outputs(self) -> None:
        self._run_hn_live("meaning_loop", "--include-meaning-loop-dry-run")
        self.assertTrue((self._run_dir("meaning_loop") / "meaning_loop_dry_run.json").exists())
        self.assertTrue((self._run_dir("meaning_loop") / "meaning_loop_dry_run.md").exists())

    def test_invalid_topic_fails_gracefully(self) -> None:
        exit_code = main(
            [
                "run-discovery-weekly",
                "--topic",
                "unknown_topic",
                "--project-root",
                str(self.project_root),
                "--use-collectors",
            ]
        )
        self.assertEqual(exit_code, 2)

    def test_no_internet_api_or_llm_calls_required_during_tests(self) -> None:
        with patch("oos.hn_algolia_collector.urlopen", side_effect=AssertionError("network not allowed")):
            exit_code = main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    "offline_guard",
                    "--use-collectors",
                    "--source-id",
                    "hacker_news_algolia",
                ]
            )
        self.assertEqual(exit_code, 0)

    def _run_hn_live(self, run_id: str, *extra_args: str) -> None:
        with patch("oos.hn_algolia_collector.HNAlgoliaCollector._fetch_live_payload", return_value=HN_PAYLOAD):
            exit_code = main(
                [
                    "run-discovery-weekly",
                    "--topic",
                    "ai_cfo_smb",
                    "--project-root",
                    str(self.project_root),
                    "--run-id",
                    run_id,
                    "--use-collectors",
                    "--allow-live-network",
                    "--source-id",
                    "hacker_news_algolia",
                    "--max-total-queries",
                    "1",
                    "--max-results-per-query",
                    "1",
                    *extra_args,
                ]
            )
        self.assertEqual(exit_code, 0)

    def _run_dir(self, run_id: str) -> Path:
        return self.project_root / "artifacts" / "discovery_runs" / run_id

    def _summary(self, run_id: str) -> dict:
        return self._json(run_id, "discovery_run_summary.json")

    def _json(self, run_id: str, filename: str):
        return json.loads((self._run_dir(run_id) / filename).read_text(encoding="utf-8"))


class _GitHubFixtureCollector(BaseCollector):
    def supports(self, scheduled_item: ScheduledCollectionItem) -> bool:
        return scheduled_item.source_type == "github_issues"

    def collect(self, scheduled_item: ScheduledCollectionItem) -> CollectionResult:
        title = "Need a tool for finance reporting"
        body = "Looking for a better way to handle SMB cashflow reporting."
        evidence = RawEvidence(
            evidence_id="raw_github_issue_90210",
            source_id=scheduled_item.source_id,
            source_type=scheduled_item.source_type,
            source_name="GitHub Issues",
            source_url="https://github.com/example/project/issues/17",
            collected_at="2026-01-02T00:00:00+00:00",
            title=title,
            body=body,
            language="unknown",
            topic_id=scheduled_item.topic_id,
            query_kind=scheduled_item.query_kind,
            content_hash=compute_raw_evidence_content_hash(title=title, body=body),
            author_or_context="unverified public issue reporter",
            raw_metadata={
                "issue_id": 90210,
                "user_present": True,
                "query_plan_id": scheduled_item.query_plan_id,
            },
            access_policy="public_github_issues_fixture",
            collection_method="github_issues_fixture",
        )
        return CollectionResult(
            scheduled_item=scheduled_item,
            evidence=[evidence],
            collector_name="github_fixture",
            live_network_used=False,
        )


if __name__ == "__main__":
    unittest.main()
