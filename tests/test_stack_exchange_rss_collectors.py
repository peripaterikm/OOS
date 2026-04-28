import unittest
from dataclasses import replace
from unittest.mock import patch

from oos.collection_scheduler import CollectionLimits, CollectionScheduler
from oos.models import RawEvidence, compute_raw_evidence_content_hash
from oos.query_planner import QueryPlanner
from oos.rss_collector import RSSFeedCollector, parse_rss_feed
from oos.source_registry import default_source_registry, default_topic_profiles
from oos.stack_exchange_collector import (
    StackExchangeCollector,
    parse_stack_exchange_questions,
    stack_exchange_question_to_raw_evidence,
)


def scheduled_item_for(source_id: str, max_results: int = 25):
    plans = QueryPlanner().build_plans(
        registry=default_source_registry(),
        topic_profiles=default_topic_profiles(),
    )
    plan = [item for item in plans if item.source_id == source_id][0]
    queue = CollectionScheduler(
        limits=CollectionLimits(
            max_total_queries=1,
            max_results_per_query=max_results,
            allowed_source_ids={source_id},
        )
    ).build_queue([plan])
    return queue[0]


def stack_exchange_fixture_payload():
    return {
        "items": [
            {
                "question_id": 777001,
                "link": "https://stackoverflow.com/questions/777001/cashflow-reporting-pain",
                "title": "Cashflow reporting pain for small finance teams",
                "body": "We stitch together monthly finance reports by hand.",
                "tags": ["finance", "reporting", "automation"],
                "answer_count": 2,
                "is_answered": False,
                "score": 11,
                "view_count": 314,
                "creation_date": 1704164645,
                "last_activity_date": 1704251045,
                "site": "stackoverflow",
                "owner": {"display_name": "raw_stack_user", "user_id": 12345},
            },
            {
                "question_id": 777002,
                "link": "https://stackoverflow.com/questions/777002/spreadsheet-workaround",
                "title": "Spreadsheet workaround for SMB forecasts",
                "excerpt": "CSV exports are cleaned manually each week.",
                "tags": ["spreadsheet"],
                "answer_count": 1,
                "is_answered": True,
                "score": 3,
                "view_count": 99,
                "creation_date": 1704337445,
                "owner": {"display_name": "another_raw_user", "user_id": 67890},
            },
        ]
    }


def rss_fixture_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Regulatory Finance Updates</title>
    <item>
      <title>New SMB reporting guidance</title>
      <link>https://regulator.example/guidance/smb-reporting</link>
      <description>Small businesses need clearer monthly reporting controls.</description>
      <guid>reg-guidance-001</guid>
      <pubDate>Tue, 02 Jan 2024 03:04:05 GMT</pubDate>
      <category>regulatory</category>
      <category>finance</category>
      <author>raw_author@example.test</author>
    </item>
    <item>
      <title>Accounting platform changelog</title>
      <link>https://vendor.example/changelog/reporting-export</link>
      <description>Export workflows now include management reports.</description>
      <guid>changelog-002</guid>
      <pubDate>Wed, 03 Jan 2024 03:04:05 GMT</pubDate>
      <category>changelog</category>
    </item>
  </channel>
</rss>
"""


class TestStackExchangeAndRSSCollectors(unittest.TestCase):
    def test_stack_exchange_declares_and_supports_source_type(self) -> None:
        item = scheduled_item_for("stack_exchange")
        collector = StackExchangeCollector(fixture_payload=stack_exchange_fixture_payload())

        self.assertTrue(collector.supports(item))
        self.assertFalse(collector.allow_live_network)

    def test_stack_exchange_fixture_question_converts_to_raw_evidence(self) -> None:
        item = scheduled_item_for("stack_exchange")
        evidence = stack_exchange_question_to_raw_evidence(
            stack_exchange_fixture_payload()["items"][0],
            scheduled_item=item,
        )

        self.assertIsInstance(evidence, RawEvidence)
        self.assertEqual(evidence.evidence_id, "raw_stackexchange_question_777001")
        self.assertEqual(evidence.source_name, "Stack Exchange")
        self.assertEqual(evidence.collection_method, "stack_exchange_fixture")

    def test_stack_exchange_source_url_uses_question_link(self) -> None:
        item = scheduled_item_for("stack_exchange")
        evidence = stack_exchange_question_to_raw_evidence(
            stack_exchange_fixture_payload()["items"][0],
            scheduled_item=item,
        )

        self.assertEqual(evidence.source_url, "https://stackoverflow.com/questions/777001/cashflow-reporting-pain")

    def test_stack_exchange_source_topic_query_kind_are_preserved(self) -> None:
        item = scheduled_item_for("stack_exchange")
        result = StackExchangeCollector(fixture_payload=stack_exchange_fixture_payload()).collect(item)
        evidence = result.evidence[0]

        self.assertEqual(evidence.source_id, item.source_id)
        self.assertEqual(evidence.source_type, item.source_type)
        self.assertEqual(evidence.topic_id, item.topic_id)
        self.assertEqual(evidence.query_kind, item.query_kind)

    def test_stack_exchange_raw_metadata_preserves_safe_fields(self) -> None:
        item = scheduled_item_for("stack_exchange")
        evidence = StackExchangeCollector(fixture_payload=stack_exchange_fixture_payload()).collect(item).evidence[0]

        self.assertEqual(evidence.raw_metadata["question_id"], 777001)
        self.assertEqual(evidence.raw_metadata["tags"], ["finance", "reporting", "automation"])
        self.assertEqual(evidence.raw_metadata["answer_count"], 2)
        self.assertFalse(evidence.raw_metadata["is_answered"])
        self.assertEqual(evidence.raw_metadata["score"], 11)
        self.assertEqual(evidence.raw_metadata["view_count"], 314)
        self.assertTrue(evidence.raw_metadata["owner_present"])
        self.assertEqual(evidence.raw_metadata["site"], "stackoverflow")

    def test_stack_exchange_author_or_context_does_not_store_user_identity(self) -> None:
        item = scheduled_item_for("stack_exchange")
        evidence = StackExchangeCollector(fixture_payload=stack_exchange_fixture_payload()).collect(item).evidence[0]

        self.assertEqual(evidence.author_or_context, "unverified public question asker")
        self.assertNotIn("owner", evidence.raw_metadata)
        self.assertNotIn("display_name", str(evidence.raw_metadata))
        self.assertNotIn("raw_stack_user", str(evidence.raw_metadata))
        self.assertNotIn("12345", str(evidence.raw_metadata))

    def test_stack_exchange_content_hash_is_deterministic(self) -> None:
        item = scheduled_item_for("stack_exchange")
        first = stack_exchange_question_to_raw_evidence(stack_exchange_fixture_payload()["items"][0], scheduled_item=item)
        second = stack_exchange_question_to_raw_evidence(stack_exchange_fixture_payload()["items"][0], scheduled_item=item)

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.content_hash, compute_raw_evidence_content_hash(title=first.title, body=first.body))

    def test_stack_exchange_collector_respects_max_results(self) -> None:
        item = scheduled_item_for("stack_exchange", max_results=1)
        result = StackExchangeCollector(fixture_payload=stack_exchange_fixture_payload()).collect(item)

        self.assertEqual(len(result.evidence), 1)

    def test_stack_exchange_no_network_call_when_live_network_disabled(self) -> None:
        item = scheduled_item_for("stack_exchange")
        collector = StackExchangeCollector()

        with patch.object(collector, "_fetch_live_payload", side_effect=AssertionError("network called")):
            result = collector.collect(item)

        self.assertEqual(result.evidence, [])
        self.assertFalse(result.live_network_used)

    def test_stack_exchange_rejects_unsupported_source_type_or_source_id(self) -> None:
        item = replace(scheduled_item_for("stack_exchange"), source_type="github_issues")

        with self.assertRaisesRegex(ValueError, "does not support"):
            StackExchangeCollector(fixture_payload=stack_exchange_fixture_payload()).collect(item)

    def test_stack_exchange_empty_response_returns_empty_evidence_safely(self) -> None:
        item = scheduled_item_for("stack_exchange")
        result = StackExchangeCollector(fixture_payload={"items": []}).collect(item)

        self.assertEqual(result.evidence, [])

    def test_stack_exchange_malformed_or_incomplete_questions_do_not_crash(self) -> None:
        item = scheduled_item_for("stack_exchange")
        payload = {
            "items": [
                {"title": "missing id"},
                "not a dict",
                {"question_id": 777999, "title": "", "body": ""},
            ]
        }

        evidence = parse_stack_exchange_questions(payload, scheduled_item=item)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_id, "raw_stackexchange_question_777999")
        self.assertEqual(evidence[0].title, "Stack Exchange question 777999")

    def test_stack_exchange_registry_planner_scheduler_fixture_offline_flow(self) -> None:
        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=default_topic_profiles(),
        )
        queue = CollectionScheduler(
            limits=CollectionLimits(max_total_queries=2, allowed_source_ids={"stack_exchange"})
        ).build_queue(plans)
        collector = StackExchangeCollector(fixture_payload=stack_exchange_fixture_payload())

        evidence = []
        for item in queue:
            evidence.extend(collector.collect(item).evidence)

        self.assertTrue(evidence)
        self.assertTrue(all(item.source_id == "stack_exchange" for item in evidence))
        self.assertTrue(all(item.source_url.startswith("https://stackoverflow.com/questions/") for item in evidence))

    def test_stack_exchange_no_secrets_or_api_keys_required(self) -> None:
        item = scheduled_item_for("stack_exchange")
        evidence = StackExchangeCollector(fixture_payload=stack_exchange_fixture_payload()).collect(item).evidence

        self.assertTrue(evidence)
        self.assertTrue(all("api_key" not in item.raw_metadata for item in evidence))
        self.assertTrue(all("token" not in item.raw_metadata for item in evidence))

    def test_rss_declares_and_supports_source_type(self) -> None:
        item = scheduled_item_for("rss_feeds")
        collector = RSSFeedCollector(fixture_xml=rss_fixture_xml())

        self.assertTrue(collector.supports(item))
        self.assertFalse(collector.allow_live_network)

    def test_rss_fixture_item_converts_to_raw_evidence(self) -> None:
        item = scheduled_item_for("rss_feeds")
        evidence = parse_rss_feed(rss_fixture_xml(), scheduled_item=item)[0]

        self.assertIsInstance(evidence, RawEvidence)
        self.assertTrue(evidence.evidence_id.startswith("raw_rss_"))
        self.assertEqual(evidence.source_name, "RSS / Regulator / Changelog Feeds")
        self.assertEqual(evidence.collection_method, "rss_feed_fixture")

    def test_rss_source_url_from_item_link_is_preserved(self) -> None:
        item = scheduled_item_for("rss_feeds")
        evidence = parse_rss_feed(rss_fixture_xml(), scheduled_item=item)[0]

        self.assertEqual(evidence.source_url, "https://regulator.example/guidance/smb-reporting")

    def test_rss_source_topic_query_kind_are_preserved(self) -> None:
        item = scheduled_item_for("rss_feeds")
        result = RSSFeedCollector(fixture_xml=rss_fixture_xml()).collect(item)
        evidence = result.evidence[0]

        self.assertEqual(evidence.source_id, item.source_id)
        self.assertEqual(evidence.source_type, item.source_type)
        self.assertEqual(evidence.topic_id, item.topic_id)
        self.assertEqual(evidence.query_kind, item.query_kind)

    def test_rss_raw_metadata_preserves_safe_feed_fields(self) -> None:
        item = scheduled_item_for("rss_feeds")
        evidence = RSSFeedCollector(fixture_xml=rss_fixture_xml()).collect(item).evidence[0]

        self.assertEqual(evidence.raw_metadata["guid"], "reg-guidance-001")
        self.assertEqual(evidence.raw_metadata["pubDate"], "Tue, 02 Jan 2024 03:04:05 GMT")
        self.assertEqual(evidence.raw_metadata["feed_title"], "Regulatory Finance Updates")
        self.assertEqual(evidence.raw_metadata["categories"], ["regulatory", "finance"])
        self.assertTrue(evidence.raw_metadata["original_author_present"])

    def test_rss_author_or_context_is_role_context_only(self) -> None:
        item = scheduled_item_for("rss_feeds")
        evidence = RSSFeedCollector(fixture_xml=rss_fixture_xml()).collect(item).evidence[0]

        self.assertEqual(evidence.author_or_context, "public feed item")
        self.assertNotIn("author", evidence.raw_metadata)
        self.assertNotIn("raw_author@example.test", str(evidence.raw_metadata))
        self.assertNotIn("raw_author@example.test", evidence.author_or_context)

    def test_rss_content_hash_is_deterministic(self) -> None:
        item = scheduled_item_for("rss_feeds")
        first = parse_rss_feed(rss_fixture_xml(), scheduled_item=item)[0]
        second = parse_rss_feed(rss_fixture_xml(), scheduled_item=item)[0]

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.content_hash, compute_raw_evidence_content_hash(title=first.title, body=first.body))

    def test_rss_collector_respects_max_results(self) -> None:
        item = scheduled_item_for("rss_feeds", max_results=1)
        result = RSSFeedCollector(fixture_xml=rss_fixture_xml()).collect(item)

        self.assertEqual(len(result.evidence), 1)

    def test_rss_no_network_call_when_live_network_disabled(self) -> None:
        item = scheduled_item_for("rss_feeds")
        collector = RSSFeedCollector()

        with patch.object(collector, "_fetch_live_payload", side_effect=AssertionError("network called")):
            result = collector.collect(item)

        self.assertEqual(result.evidence, [])
        self.assertFalse(result.live_network_used)

    def test_rss_search_text_query_is_skipped_not_fetched(self) -> None:
        item = replace(
            scheduled_item_for("rss_feeds"),
            query_text='"accounting software" "spreadsheet"',
            live_network_enabled=True,
        )
        collector = RSSFeedCollector(allow_live_network=True)

        with patch.object(collector, "_fetch_live_payload", side_effect=AssertionError("network called")):
            result = collector.collect(item)

        self.assertEqual(result.evidence, [])
        self.assertFalse(result.live_network_used)
        self.assertEqual(result.collection_errors[0]["code"], "rss_feed_url_missing")
        self.assertNotIn("unknown url type", result.collection_errors[0]["error"])

    def test_rss_valid_query_url_uses_mocked_fetch(self) -> None:
        item = replace(
            scheduled_item_for("rss_feeds"),
            query_text="https://feeds.example.test/finance.xml",
            live_network_enabled=True,
        )
        collector = RSSFeedCollector(allow_live_network=True)

        with patch.object(collector, "_fetch_live_payload", return_value=rss_fixture_xml()) as fetch:
            result = collector.collect(item)

        fetch.assert_called_once_with("https://feeds.example.test/finance.xml")
        self.assertTrue(result.evidence)
        self.assertTrue(result.live_network_used)

    def test_rss_missing_feed_url_yields_nonfatal_skip(self) -> None:
        item = replace(scheduled_item_for("rss_feeds"), live_network_enabled=True)
        collector = RSSFeedCollector(allow_live_network=True)

        result = collector.collect(item)

        self.assertEqual(result.evidence, [])
        self.assertEqual(result.collection_errors[0]["code"], "rss_feed_url_missing")

    def test_rss_rejects_unsupported_source_type_or_source_id(self) -> None:
        item = replace(scheduled_item_for("rss_feeds"), source_type="github_issues")

        with self.assertRaisesRegex(ValueError, "does not support"):
            RSSFeedCollector(fixture_xml=rss_fixture_xml()).collect(item)

    def test_rss_empty_feed_returns_empty_evidence_safely(self) -> None:
        item = scheduled_item_for("rss_feeds")
        result = RSSFeedCollector(fixture_xml="<rss><channel><title>Empty</title></channel></rss>").collect(item)

        self.assertEqual(result.evidence, [])

    def test_rss_malformed_feed_is_handled_deterministically(self) -> None:
        item = scheduled_item_for("rss_feeds")

        evidence = parse_rss_feed("<rss><channel><item>", scheduled_item=item)

        self.assertEqual(evidence, [])

    def test_rss_registry_planner_scheduler_fixture_offline_flow(self) -> None:
        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=default_topic_profiles(),
        )
        queue = CollectionScheduler(
            limits=CollectionLimits(max_total_queries=2, allowed_source_ids={"rss_feeds"})
        ).build_queue(plans)
        collector = RSSFeedCollector(fixture_xml=rss_fixture_xml())

        evidence = []
        for item in queue:
            evidence.extend(collector.collect(item).evidence)

        self.assertTrue(evidence)
        self.assertTrue(all(item.source_id == "rss_feeds" for item in evidence))
        self.assertTrue(all(item.source_url.startswith(("https://regulator.example/", "https://vendor.example/")) for item in evidence))

    def test_rss_no_secrets_or_api_keys_required(self) -> None:
        item = scheduled_item_for("rss_feeds")
        evidence = RSSFeedCollector(fixture_xml=rss_fixture_xml()).collect(item).evidence

        self.assertTrue(evidence)
        self.assertTrue(all("api_key" not in item.raw_metadata for item in evidence))
        self.assertTrue(all("token" not in item.raw_metadata for item in evidence))

    def test_no_live_internet_api_or_llm_calls_are_made_during_tests(self) -> None:
        stack_item = scheduled_item_for("stack_exchange")
        rss_item = scheduled_item_for("rss_feeds")

        stack_result = StackExchangeCollector(fixture_payload=stack_exchange_fixture_payload()).collect(stack_item)
        rss_result = RSSFeedCollector(fixture_xml=rss_fixture_xml()).collect(rss_item)

        self.assertFalse(stack_result.live_network_used)
        self.assertFalse(rss_result.live_network_used)
        self.assertTrue(all(item.collection_method == "stack_exchange_fixture" for item in stack_result.evidence))
        self.assertTrue(all(item.collection_method == "rss_feed_fixture" for item in rss_result.evidence))


if __name__ == "__main__":
    unittest.main()
