import unittest
from dataclasses import replace
from unittest.mock import patch

from oos.collection_scheduler import CollectionLimits, CollectionScheduler
from oos.github_issues_collector import (
    GitHubIssuesCollector,
    github_issue_to_raw_evidence,
    parse_github_issues,
)
from oos.models import RawEvidence, compute_raw_evidence_content_hash
from oos.query_planner import QueryPlanner
from oos.source_registry import default_source_registry, default_topic_profiles


def github_scheduled_item(max_results: int = 25):
    plans = QueryPlanner().build_plans(
        registry=default_source_registry(),
        topic_profiles=default_topic_profiles(),
    )
    github_plan = [plan for plan in plans if plan.source_id == "github_issues"][0]
    queue = CollectionScheduler(
        limits=CollectionLimits(
            max_total_queries=1,
            max_results_per_query=max_results,
            allowed_source_ids={"github_issues"},
        )
    ).build_queue([github_plan])
    return queue[0]


def fixture_payload():
    return {
        "items": [
            {
                "id": 123456789,
                "node_id": "I_kwDOExample",
                "number": 42,
                "html_url": "https://github.com/example/finance-tool/issues/42",
                "url": "https://api.github.com/repos/example/finance-tool/issues/42",
                "repository_url": "https://api.github.com/repos/example/finance-tool",
                "comments_url": "https://api.github.com/repos/example/finance-tool/issues/42/comments",
                "title": "Cashflow report export is painful for SMB users",
                "body": "Our finance team keeps stitching monthly reports together by hand.",
                "state": "open",
                "created_at": "2024-02-03T04:05:06Z",
                "updated_at": "2024-02-04T04:05:06Z",
                "closed_at": None,
                "comments": 5,
                "labels": [{"name": "feature request"}, {"name": "reporting"}],
                "reactions": {"total_count": 3, "+1": 2, "eyes": 1, "url": "ignored"},
                "user": {"login": "raw_github_login"},
            },
            {
                "id": 123456790,
                "number": 43,
                "html_url": "https://github.com/example/finance-tool/issues/43",
                "title": "Need better management reporting workaround",
                "body": "We export CSVs and clean them manually.",
                "state": "open",
                "created_at": "2024-02-05T04:05:06Z",
                "comments": 1,
                "labels": ["workaround"],
                "user": {"login": "another_login"},
            },
        ]
    }


class TestGitHubIssuesCollector(unittest.TestCase):
    def test_declares_and_supports_github_issues_source_type(self) -> None:
        item = github_scheduled_item()
        collector = GitHubIssuesCollector(fixture_payload=fixture_payload())

        self.assertTrue(collector.supports(item))
        self.assertFalse(collector.allow_live_network)

    def test_fixture_issue_converts_to_raw_evidence(self) -> None:
        item = github_scheduled_item()
        evidence = github_issue_to_raw_evidence(fixture_payload()["items"][0], scheduled_item=item)

        self.assertIsInstance(evidence, RawEvidence)
        self.assertEqual(evidence.evidence_id, "raw_github_issue_123456789")
        self.assertEqual(evidence.source_name, "GitHub Issues")
        self.assertEqual(evidence.collection_method, "github_issues_fixture")

    def test_source_url_uses_github_issue_html_url(self) -> None:
        item = github_scheduled_item()
        evidence = github_issue_to_raw_evidence(fixture_payload()["items"][0], scheduled_item=item)

        self.assertEqual(evidence.source_url, "https://github.com/example/finance-tool/issues/42")

    def test_source_topic_query_kind_are_preserved_from_scheduled_item(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)
        evidence = result.evidence[0]

        self.assertEqual(evidence.source_id, item.source_id)
        self.assertEqual(evidence.source_type, item.source_type)
        self.assertEqual(evidence.topic_id, item.topic_id)
        self.assertEqual(evidence.query_kind, item.query_kind)

    def test_raw_metadata_preserves_safe_github_issue_fields(self) -> None:
        item = github_scheduled_item()
        evidence = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item).evidence[0]

        self.assertEqual(evidence.raw_metadata["issue_id"], 123456789)
        self.assertEqual(evidence.raw_metadata["node_id"], "I_kwDOExample")
        self.assertEqual(evidence.raw_metadata["number"], 42)
        self.assertEqual(evidence.raw_metadata["labels"], ["feature request", "reporting"])
        self.assertEqual(evidence.raw_metadata["state"], "open")
        self.assertEqual(evidence.raw_metadata["comments_count"], 5)
        self.assertEqual(evidence.raw_metadata["reactions"], {"total_count": 3, "+1": 2, "eyes": 1})
        self.assertFalse(evidence.raw_metadata["pull_request_present"])
        self.assertTrue(evidence.raw_metadata["user_present"])
        self.assertIn("repository_url", evidence.raw_metadata)
        self.assertIn("comments_url", evidence.raw_metadata)

    def test_author_or_context_does_not_store_raw_github_username_or_login(self) -> None:
        item = github_scheduled_item()
        evidence = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item).evidence[0]

        self.assertEqual(evidence.author_or_context, "unverified public issue reporter")
        self.assertNotIn("user", evidence.raw_metadata)
        self.assertNotIn("login", evidence.raw_metadata)
        self.assertNotIn("raw_github_login", evidence.author_or_context)
        self.assertNotIn("raw_github_login", str(evidence.raw_metadata))

    def test_content_hash_is_deterministic_for_same_issue_title_and_body(self) -> None:
        item = github_scheduled_item()
        first = github_issue_to_raw_evidence(fixture_payload()["items"][0], scheduled_item=item)
        second = github_issue_to_raw_evidence(fixture_payload()["items"][0], scheduled_item=item)

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(
            first.content_hash,
            compute_raw_evidence_content_hash(title=first.title, body=first.body),
        )

    def test_collector_respects_max_results(self) -> None:
        item = github_scheduled_item(max_results=1)
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)

        self.assertEqual(len(result.evidence), 1)

    def test_no_network_call_when_live_network_is_disabled(self) -> None:
        item = github_scheduled_item()
        collector = GitHubIssuesCollector()

        with patch.object(collector, "_fetch_live_payload", side_effect=AssertionError("network called")):
            result = collector.collect(item)

        self.assertEqual(result.evidence, [])
        self.assertFalse(result.live_network_used)

    def test_rejects_unsupported_source_type_or_source_id(self) -> None:
        item = replace(github_scheduled_item(), source_type="hacker_news_algolia")

        with self.assertRaisesRegex(ValueError, "does not support"):
            GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)

    def test_empty_fixture_response_returns_empty_evidence_safely(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload={"items": []}).collect(item)

        self.assertEqual(result.evidence, [])

    def test_malformed_or_incomplete_issues_do_not_crash_collection(self) -> None:
        item = github_scheduled_item()
        payload = {
            "items": [
                {"title": "missing id"},
                "not a dict",
                {"id": 987654321, "title": "", "body": ""},
            ]
        }

        evidence = parse_github_issues(payload, scheduled_item=item)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_id, "raw_github_issue_987654321")
        self.assertEqual(evidence[0].title, "GitHub issue 987654321")

    def test_pull_request_shaped_issue_is_skipped_by_default(self) -> None:
        item = github_scheduled_item()
        payload = {
            "items": [
                {
                    "id": 555,
                    "number": 7,
                    "title": "Pull request should not be collected as issue pain",
                    "body": "Implementation details",
                    "pull_request": {"url": "https://api.github.com/repos/example/repo/pulls/7"},
                },
                fixture_payload()["items"][0],
            ]
        }

        evidence = parse_github_issues(payload, scheduled_item=item)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_id, "raw_github_issue_123456789")

    def test_registry_planner_scheduler_github_fixture_offline_flow(self) -> None:
        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=default_topic_profiles(),
        )
        queue = CollectionScheduler(
            limits=CollectionLimits(max_total_queries=2, allowed_source_ids={"github_issues"})
        ).build_queue(plans)
        collector = GitHubIssuesCollector(fixture_payload=fixture_payload())

        evidence = []
        for item in queue:
            evidence.extend(collector.collect(item).evidence)

        self.assertTrue(evidence)
        self.assertTrue(all(item.source_id == "github_issues" for item in evidence))
        self.assertTrue(all(item.source_url.startswith("https://github.com/") for item in evidence))

    def test_no_secrets_or_api_keys_required(self) -> None:
        item = github_scheduled_item()
        evidence = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item).evidence

        self.assertTrue(evidence)
        self.assertTrue(all("api_key" not in item.raw_metadata for item in evidence))
        self.assertTrue(all("token" not in item.raw_metadata for item in evidence))

    def test_no_live_internet_api_or_llm_calls_are_made_during_tests(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)

        self.assertTrue(result.evidence)
        self.assertFalse(result.live_network_used)
        self.assertTrue(all(item.collection_method == "github_issues_fixture" for item in result.evidence))


if __name__ == "__main__":
    unittest.main()
