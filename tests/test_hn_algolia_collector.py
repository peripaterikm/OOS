import unittest
from dataclasses import replace
from unittest.mock import patch

from oos.collection_scheduler import CollectionLimits, CollectionScheduler
from oos.hn_algolia_collector import HNAlgoliaCollector, hn_hit_to_raw_evidence, parse_hn_algolia_hits
from oos.models import RawEvidence, compute_raw_evidence_content_hash
from oos.query_planner import QueryPlanner
from oos.source_registry import default_source_registry, default_topic_profiles


def hn_scheduled_item(max_results: int = 25):
    plans = QueryPlanner().build_plans(
        registry=default_source_registry(),
        topic_profiles=default_topic_profiles(),
    )
    hn_plan = [plan for plan in plans if plan.source_id == "hacker_news_algolia"][0]
    queue = CollectionScheduler(
        limits=CollectionLimits(
            max_total_queries=1,
            max_results_per_query=max_results,
            allowed_source_ids={"hacker_news_algolia"},
        )
    ).build_queue([hn_plan])
    return queue[0]


def fixture_payload():
    return {
        "hits": [
            {
                "objectID": "38600123",
                "created_at": "2024-01-02T03:04:05Z",
                "created_at_i": 1704164645,
                "title": "Ask HN: Better cashflow reporting for small businesses?",
                "story_text": "I keep stitching finance reports together manually.",
                "url": "https://example.com/original",
                "author": "raw_hn_username",
                "points": 42,
                "num_comments": 17,
                "_tags": ["story", "author_raw_hn_username"],
            },
            {
                "objectID": "38600124",
                "created_at": "2024-01-03T03:04:05Z",
                "story_title": "Finance automation pain",
                "comment_text": "Spreadsheets are the current workaround.",
                "author": "another_user",
                "points": None,
                "num_comments": 3,
                "_tags": ["comment"],
            },
        ]
    }


class TestHNAlgoliaCollector(unittest.TestCase):
    def test_declares_and_supports_hacker_news_algolia_source_type(self) -> None:
        item = hn_scheduled_item()
        collector = HNAlgoliaCollector(fixture_payload=fixture_payload())

        self.assertTrue(collector.supports(item))
        self.assertFalse(collector.allow_live_network)

    def test_fixture_hit_converts_to_raw_evidence(self) -> None:
        item = hn_scheduled_item()
        evidence = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)

        self.assertIsInstance(evidence, RawEvidence)
        self.assertEqual(evidence.evidence_id, "raw_hn_38600123")
        self.assertEqual(evidence.source_name, "Hacker News Algolia")
        self.assertEqual(evidence.collection_method, "hn_algolia_fixture")

    def test_source_url_points_to_hacker_news_item_url(self) -> None:
        item = hn_scheduled_item()
        evidence = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)

        self.assertEqual(evidence.source_url, "https://news.ycombinator.com/item?id=38600123")

    def test_source_topic_query_kind_are_preserved_from_scheduled_item(self) -> None:
        item = hn_scheduled_item()
        result = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item)
        evidence = result.evidence[0]

        self.assertEqual(evidence.source_id, item.source_id)
        self.assertEqual(evidence.source_type, item.source_type)
        self.assertEqual(evidence.topic_id, item.topic_id)
        self.assertEqual(evidence.query_kind, item.query_kind)

    def test_raw_metadata_preserves_safe_hn_fields(self) -> None:
        item = hn_scheduled_item()
        evidence = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item).evidence[0]

        self.assertEqual(evidence.raw_metadata["objectID"], "38600123")
        self.assertEqual(evidence.raw_metadata["points"], 42)
        self.assertEqual(evidence.raw_metadata["num_comments"], 17)
        self.assertEqual(evidence.raw_metadata["tags"], ["story", "author_raw_hn_username"])
        self.assertEqual(evidence.raw_metadata["original_url"], "https://example.com/original")
        self.assertTrue(evidence.raw_metadata["author_present"])

    def test_author_or_context_does_not_store_raw_hn_username(self) -> None:
        item = hn_scheduled_item()
        evidence = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item).evidence[0]

        self.assertEqual(evidence.author_or_context, "unverified public commenter")
        self.assertNotIn("author", evidence.raw_metadata)
        self.assertNotIn("raw_hn_username", evidence.author_or_context)

    def test_content_hash_is_deterministic_for_same_hit_title_and_body(self) -> None:
        item = hn_scheduled_item()
        first = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)
        second = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(
            first.content_hash,
            compute_raw_evidence_content_hash(title=first.title, body=first.body),
        )

    def test_collector_respects_max_results(self) -> None:
        item = hn_scheduled_item(max_results=1)
        result = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item)

        self.assertEqual(len(result.evidence), 1)

    def test_no_network_call_when_live_network_is_disabled(self) -> None:
        item = hn_scheduled_item()
        collector = HNAlgoliaCollector()

        with patch.object(collector, "_fetch_live_payload", side_effect=AssertionError("network called")):
            result = collector.collect(item)

        self.assertEqual(result.evidence, [])
        self.assertFalse(result.live_network_used)

    def test_rejects_unsupported_source_type_or_source_id(self) -> None:
        item = replace(hn_scheduled_item(), source_type="github_issues")

        with self.assertRaisesRegex(ValueError, "does not support"):
            HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item)

    def test_empty_fixture_response_returns_empty_evidence_safely(self) -> None:
        item = hn_scheduled_item()
        result = HNAlgoliaCollector(fixture_payload={"hits": []}).collect(item)

        self.assertEqual(result.evidence, [])

    def test_malformed_or_incomplete_hits_do_not_crash_collection(self) -> None:
        item = hn_scheduled_item()
        payload = {
            "hits": [
                {"title": "missing object id"},
                "not a dict",
                {"objectID": "38600999", "title": "", "story_text": ""},
            ]
        }

        evidence = parse_hn_algolia_hits(payload, scheduled_item=item)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_id, "raw_hn_38600999")
        self.assertEqual(evidence[0].title, "HN item 38600999")

    def test_registry_planner_scheduler_hn_fixture_offline_flow(self) -> None:
        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=default_topic_profiles(),
        )
        queue = CollectionScheduler(
            limits=CollectionLimits(max_total_queries=2, allowed_source_ids={"hacker_news_algolia"})
        ).build_queue(plans)
        collector = HNAlgoliaCollector(fixture_payload=fixture_payload())

        evidence = []
        for item in queue:
            evidence.extend(collector.collect(item).evidence)

        self.assertTrue(evidence)
        self.assertTrue(all(item.source_id == "hacker_news_algolia" for item in evidence))
        self.assertTrue(all(item.source_url.startswith("https://news.ycombinator.com/item?id=") for item in evidence))

    def test_no_secrets_or_api_keys_required(self) -> None:
        item = hn_scheduled_item()
        evidence = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item).evidence

        self.assertTrue(evidence)
        self.assertTrue(all("api_key" not in item.raw_metadata for item in evidence))
        self.assertTrue(all("token" not in item.raw_metadata for item in evidence))

    def test_no_live_internet_api_or_llm_calls_are_made_during_tests(self) -> None:
        item = hn_scheduled_item()
        result = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item)

        self.assertTrue(result.evidence)
        self.assertFalse(result.live_network_used)
        self.assertTrue(all(item.collection_method == "hn_algolia_fixture" for item in result.evidence))


if __name__ == "__main__":
    unittest.main()
