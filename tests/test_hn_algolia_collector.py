import unittest
from dataclasses import replace
from unittest.mock import patch

from oos.collection_scheduler import CollectionLimits, CollectionScheduler
from oos.hn_algolia_collector import (
    HN_CANONICAL_SOURCE_ID,
    HN_CANONICAL_SOURCE_TYPE,
    HN_CANONICAL_SOURCE_NAME,
    HNAlgoliaCollector,
    HNSourceQualitySummary,
    build_hn_source_quality_summary,
    hn_hit_to_raw_evidence,
    parse_hn_algolia_hits,
)
from oos.models import RawEvidence, compute_raw_evidence_content_hash
from oos.query_planner import QueryPlanner
from oos.source_registry import default_source_registry, default_topic_profiles


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def hn_scheduled_item(max_results: int = 25):
    """Build a scheduled item for HN using the legacy code registry.

    The code registry still uses source_id="hacker_news_algolia",
    so the scheduled_item carries that. The collector normalizes
    to canonical values internally.
    """
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
    """Base fixture payload with two representative HN hits."""
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
                "_tags": ["story", "ask_hn", "author_raw_hn_username"],
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


def rich_fixture_payload():
    """Extended fixture covering all evidence_kind values and quality flags."""
    return {
        "hits": [
            # Ask HN with pain keywords → pain_signal_candidate
            {
                "objectID": "40100001",
                "created_at": "2025-03-01T08:00:00Z",
                "title": "Ask HN: What's the most frustrating part of your dev workflow?",
                "story_text": "I waste hours of my life on flaky CI pipelines. It's a nightmare.",
                "author": "dev_author",
                "points": 55,
                "num_comments": 23,
                "_tags": ["story", "ask_hn"],
            },
            # Ask HN with workaround keywords → workaround
            {
                "objectID": "40100002",
                "created_at": "2025-03-02T09:00:00Z",
                "title": "Ask HN: How do you manage cash flow spreadsheets?",
                "story_text": "My workaround is a cron job that scrapes bank data into a spreadsheet.",
                "author": "finance_author",
                "points": 31,
                "num_comments": 12,
                "_tags": ["story", "ask_hn"],
            },
            # Ask HN with complaint keywords → complaint
            {
                "objectID": "40100003",
                "created_at": "2025-03-03T10:00:00Z",
                "title": "Ask HN: Why is QuickBooks so overpriced?",
                "story_text": "Too expensive for small businesses. Should be easier.",
                "author": "complaint_author",
                "points": 18,
                "num_comments": 7,
                "_tags": ["story", "ask_hn"],
            },
            # Ask HN with feature_request keywords → feature_request
            {
                "objectID": "40100004",
                "created_at": "2025-03-04T11:00:00Z",
                "title": "Ask HN: Looking for a tool that does automated invoicing?",
                "story_text": "Would be great if something existed for freelancers.",
                "author": "request_author",
                "points": 22,
                "num_comments": 9,
                "_tags": ["story", "ask_hn"],
            },
            # Show HN → product_launch
            {
                "objectID": "40100005",
                "created_at": "2025-03-05T12:00:00Z",
                "title": "Show HN: Launching our AI invoice processor",
                "story_text": "We built an automated invoicing platform using AI to extract data.",
                "author": "launch_author",
                "points": 8,
                "num_comments": 4,
                "_tags": ["story", "show_hn"],
            },
            # Story with market_trend keywords → market_trend
            {
                "objectID": "40100006",
                "created_at": "2025-03-06T13:00:00Z",
                "title": "The future of automated finance is here",
                "story_text": "AI adoption in finance is growing rapidly.",
                "url": "https://example.com/trend",
                "author": "trend_author",
                "points": 67,
                "num_comments": 28,
                "_tags": ["story"],
            },
            # Story with solution keywords → solution_pattern
            {
                "objectID": "40100007",
                "created_at": "2025-03-07T14:00:00Z",
                "title": "How we migrated from spreadsheets to automated reporting",
                "story_text": "We replaced our manual process with a Python script.",
                "url": "https://example.com/solution",
                "author": "solution_author",
                "points": 44,
                "num_comments": 15,
                "_tags": ["story"],
            },
            # Product launch keywords in story → product_launch
            {
                "objectID": "40100008",
                "created_at": "2025-03-08T15:00:00Z",
                "title": "Introducing our new SaaS analytics platform",
                "story_text": "Just shipped our MVP after 6 months of beta testing.",
                "url": "https://example.com/launch",
                "author": "saas_author",
                "points": 12,
                "num_comments": 6,
                "_tags": ["story"],
            },
            # Comment with pain keywords → pain_signal_candidate
            {
                "objectID": "40100009",
                "created_at": "2025-03-09T16:00:00Z",
                "title": None,
                "story_title": "Original story",
                "comment_text": "This is my biggest problem too. The existing tools are broken and unusable.",
                "author": "commenter",
                "points": None,
                "num_comments": None,
                "_tags": ["comment"],
            },
            # Short comment (< 100 chars) → unknown, low_text_context
            {
                "objectID": "40100010",
                "created_at": "2025-03-10T17:00:00Z",
                "title": None,
                "comment_text": "nice work",
                "author": "brief_commenter",
                "points": None,
                "num_comments": None,
                "_tags": ["comment"],
            },
            # Flamewar/meta comment → flamewar_or_meta_discussion
            {
                "objectID": "40100011",
                "created_at": "2025-03-11T18:00:00Z",
                "title": None,
                "story_title": "HN moderation discussion",
                "comment_text": "Dang why was this flagged? The moderation on this site is terrible. HN is becoming unusable because the guidelines are not followed.",
                "author": "meta_commenter",
                "points": None,
                "num_comments": None,
                "_tags": ["comment"],
            },
            # Self-promo comment → suspected_self_promo
            {
                "objectID": "40100012",
                "created_at": "2025-03-12T19:00:00Z",
                "title": None,
                "comment_text": "Check out my startup we built an amazing platform for this. Sign up for our beta.",
                "author": "promo_commenter",
                "points": None,
                "num_comments": None,
                "_tags": ["comment"],
            },
            # Low points item → low_confidence_source
            {
                "objectID": "40100013",
                "created_at": "2025-03-13T20:00:00Z",
                "title": "Unknown random post",
                "story_text": "Some random discussion about something.",
                "author": "random_author",
                "points": 1,
                "num_comments": 0,
                "_tags": ["story"],
            },
            # Empty content hit → rejected
            {
                "objectID": "40100014",
                "title": None,
                "story_text": None,
                "comment_text": None,
                "url": None,
                "story_url": None,
                "author": None,
                "_tags": ["comment"],
            },
            # Duplicate objectID → deduped
            {
                "objectID": "40100001",
                "created_at": "2025-03-01T08:00:00Z",
                "title": "Duplicate entry",
                "story_text": "This should be deduplicated.",
                "author": "dup_author",
                "points": 55,
                "num_comments": 23,
                "_tags": ["story"],
            },
        ]
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHNAlgoliaCollectorCanonicalIdentity(unittest.TestCase):
    """Test canonical source_id/source_type alignment."""

    def test_emits_canonical_source_id_hacker_news(self) -> None:
        item = hn_scheduled_item()
        evidence = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)
        self.assertEqual(evidence.source_id, "hacker_news")
        self.assertNotEqual(evidence.source_id, "hacker_news_algolia")

    def test_emits_canonical_source_type_discussion(self) -> None:
        item = hn_scheduled_item()
        evidence = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)
        self.assertEqual(evidence.source_type, "discussion")
        self.assertNotEqual(evidence.source_type, "hacker_news_algolia")

    def test_emits_canonical_source_name(self) -> None:
        item = hn_scheduled_item()
        evidence = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)
        self.assertEqual(evidence.source_name, "Hacker News")

    def test_evidence_id_uses_canonical_prefix(self) -> None:
        item = hn_scheduled_item()
        evidence = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)
        self.assertTrue(evidence.evidence_id.startswith("raw_hacker_news_"))
        self.assertNotIn("raw_hn_", evidence.evidence_id)

    def test_legacy_hacker_news_algolia_not_canonical_source_id(self) -> None:
        item = hn_scheduled_item()
        result = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item)
        for ev in result.evidence:
            self.assertNotEqual(ev.source_id, "hacker_news_algolia")
            self.assertEqual(ev.source_id, "hacker_news")

    def test_legacy_hacker_news_algolia_not_canonical_source_type(self) -> None:
        item = hn_scheduled_item()
        result = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item)
        for ev in result.evidence:
            self.assertNotEqual(ev.source_type, "hacker_news_algolia")
            self.assertEqual(ev.source_type, "discussion")


class TestHNAlgoliaCollectorSupports(unittest.TestCase):
    """Test collector supports() with both legacy and canonical source_id/source_type."""

    def test_declares_and_supports_hacker_news_algolia_source_type(self) -> None:
        item = hn_scheduled_item()
        collector = HNAlgoliaCollector(fixture_payload=fixture_payload())
        self.assertTrue(collector.supports(item))
        self.assertFalse(collector.allow_live_network)

    def test_supports_canonical_source_id(self) -> None:
        item = replace(hn_scheduled_item(), source_id="hacker_news", source_type="discussion")
        collector = HNAlgoliaCollector(fixture_payload=fixture_payload())
        self.assertTrue(collector.supports(item))

    def test_does_not_support_github_source_type(self) -> None:
        item = hn_scheduled_item()
        collector = HNAlgoliaCollector(fixture_payload=fixture_payload())
        unsupported = replace(item, source_type="github_issues")
        self.assertFalse(collector.supports(unsupported))


class TestHNAlgoliaCollectorLegacy(TestHNAlgoliaCollectorCanonicalIdentity):
    """Preserve existing test behavior patterns with canonical field verification."""

    def test_fixture_hit_converts_to_raw_evidence(self) -> None:
        item = hn_scheduled_item()
        evidence = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)
        self.assertIsInstance(evidence, RawEvidence)
        self.assertEqual(evidence.evidence_id, "raw_hacker_news_38600123")
        self.assertEqual(evidence.source_name, "Hacker News")
        self.assertEqual(evidence.collection_method, "hn_algolia_fixture")

    def test_source_url_points_to_hacker_news_item_url(self) -> None:
        item = hn_scheduled_item()
        evidence = hn_hit_to_raw_evidence(fixture_payload()["hits"][0], scheduled_item=item)
        self.assertEqual(evidence.source_url, "https://news.ycombinator.com/item?id=38600123")

    def test_source_topic_query_kind_are_preserved_from_scheduled_item(self) -> None:
        item = hn_scheduled_item()
        result = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item)
        evidence = result.evidence[0]
        self.assertEqual(evidence.topic_id, item.topic_id)
        self.assertEqual(evidence.query_kind, item.query_kind)

    def test_raw_metadata_preserves_safe_hn_fields(self) -> None:
        item = hn_scheduled_item()
        evidence = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item).evidence[0]
        self.assertEqual(evidence.raw_metadata["objectID"], "38600123")
        self.assertEqual(evidence.raw_metadata["points"], 42)
        self.assertEqual(evidence.raw_metadata["num_comments"], 17)
        self.assertEqual(evidence.raw_metadata["tags"], ["story", "ask_hn", "author_raw_hn_username"])
        self.assertEqual(evidence.raw_metadata["original_url"], "https://example.com/original")
        self.assertTrue(evidence.raw_metadata["author_present"])

    def test_author_or_context_does_not_store_raw_hn_username(self) -> None:
        item = hn_scheduled_item()
        evidence = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item).evidence[0]
        self.assertEqual(evidence.author_or_context, "Ask HN poster")
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
        self.assertEqual(evidence[0].evidence_id, "raw_hacker_news_38600999")
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
        # All evidence should have canonical source_id
        self.assertTrue(all(ev.source_id == "hacker_news" for ev in evidence))
        self.assertTrue(all(ev.source_url.startswith("https://news.ycombinator.com/item?id=") for ev in evidence))

    def test_no_secrets_or_api_keys_required(self) -> None:
        item = hn_scheduled_item()
        evidence = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item).evidence
        self.assertTrue(evidence)
        self.assertTrue(all("api_key" not in ev.raw_metadata for ev in evidence))
        self.assertTrue(all("token" not in ev.raw_metadata for ev in evidence))

    def test_no_live_internet_api_or_llm_calls_are_made_during_tests(self) -> None:
        item = hn_scheduled_item()
        result = HNAlgoliaCollector(fixture_payload=fixture_payload()).collect(item)
        self.assertTrue(result.evidence)
        self.assertFalse(result.live_network_used)
        self.assertTrue(all(ev.collection_method == "hn_algolia_fixture" for ev in result.evidence))


# ---------------------------------------------------------------------------
# evidence_kind classification tests
# ---------------------------------------------------------------------------

class TestEvidenceKindClassification(unittest.TestCase):
    """Test deterministic evidence_kind classification for HN hits."""

    def setUp(self) -> None:
        self.item = hn_scheduled_item()

    def _kind(self, hit: dict) -> str:
        ev = hn_hit_to_raw_evidence(hit, scheduled_item=self.item)
        return ev.raw_metadata["evidence_kind"]

    def test_ask_hn_pain_keywords_classifies_as_pain_signal_candidate(self) -> None:
        hit = {
            "objectID": "1001",
            "title": "Ask HN: Frustrating invoice workflows",
            "story_text": "This is a nightmare. I struggle every month.",
            "_tags": ["story", "ask_hn"],
        }
        self.assertEqual(self._kind(hit), "pain_signal_candidate")

    def test_ask_hn_workaround_keywords_classifies_as_workaround(self) -> None:
        hit = {
            "objectID": "1002",
            "title": "Ask HN: How do you handle cash flow?",
            "story_text": "My workaround is a spreadsheet and a cron job.",
            "_tags": ["story", "ask_hn"],
        }
        self.assertEqual(self._kind(hit), "workaround")

    def test_ask_hn_complaint_keywords_classifies_as_complaint(self) -> None:
        hit = {
            "objectID": "1003",
            "title": "Ask HN: Why is accounting software so overpriced?",
            "story_text": "Too expensive, not worth the money.",
            "_tags": ["story", "ask_hn"],
        }
        self.assertEqual(self._kind(hit), "complaint")

    def test_ask_hn_feature_request_keywords_classifies_as_feature_request(self) -> None:
        hit = {
            "objectID": "1004",
            "title": "Ask HN: Looking for a tool that does X",
            "story_text": "Wish it had automated reports. Please add this feature.",
            "_tags": ["story", "ask_hn"],
        }
        self.assertEqual(self._kind(hit), "feature_request")

    def test_show_hn_classifies_as_product_launch(self) -> None:
        hit = {
            "objectID": "1005",
            "title": "Show HN: My new invoicing tool",
            "story_text": "Launching our beta.",
            "_tags": ["story", "show_hn"],
        }
        self.assertEqual(self._kind(hit), "product_launch")

    def test_story_with_market_trend_keywords_classifies_as_market_trend(self) -> None:
        hit = {
            "objectID": "1006",
            "title": "The future of finance ops",
            "story_text": "AI adoption is growing and the market is shifting.",
            "_tags": ["story"],
        }
        self.assertEqual(self._kind(hit), "market_trend")

    def test_story_with_solution_keywords_classifies_as_solution_pattern(self) -> None:
        hit = {
            "objectID": "1007",
            "title": "How we migrated from manual bookkeeping",
            "story_text": "We built a Python script and automated everything.",
            "_tags": ["story"],
        }
        self.assertEqual(self._kind(hit), "solution_pattern")

    def test_story_with_product_launch_keywords_classifies_as_product_launch(self) -> None:
        hit = {
            "objectID": "1008",
            "title": "Introducing our new platform",
            "story_text": "Just shipped our MVP.",
            "_tags": ["story"],
        }
        self.assertEqual(self._kind(hit), "product_launch")

    def test_comment_with_pain_keywords_classifies_as_pain_signal_candidate(self) -> None:
        hit = {
            "objectID": "1009",
            "title": None,
            "story_title": "Some story",
            "comment_text": "This is the biggest problem I face. Existing tools are broken and terrible.",
            "_tags": ["comment"],
        }
        self.assertEqual(self._kind(hit), "pain_signal_candidate")

    def test_short_comment_defaults_to_unknown(self) -> None:
        hit = {
            "objectID": "1010",
            "title": None,
            "comment_text": "this is a short comment",
            "_tags": ["comment"],
        }
        self.assertEqual(self._kind(hit), "unknown")

    def test_unclassifiable_story_defaults_to_unknown(self) -> None:
        hit = {
            "objectID": "1011",
            "title": "Something random",
            "story_text": "Just a normal discussion.",
            "_tags": ["story"],
        }
        self.assertEqual(self._kind(hit), "unknown")

    def test_rich_fixture_all_records_have_evidence_kind(self) -> None:
        item = hn_scheduled_item(max_results=50)
        evidence = parse_hn_algolia_hits(rich_fixture_payload(), scheduled_item=item)
        for ev in evidence:
            self.assertIn("evidence_kind", ev.raw_metadata)
            self.assertIn(ev.raw_metadata["evidence_kind"], {
                "pain_signal_candidate", "workaround", "complaint",
                "feature_request", "product_launch", "solution_pattern",
                "market_trend", "unknown",
            })

    def test_rich_fixture_specific_kinds(self) -> None:
        item = hn_scheduled_item(max_results=50)
        evidence = parse_hn_algolia_hits(rich_fixture_payload(), scheduled_item=item)
        kinds = {ev.raw_metadata["objectID"]: ev.raw_metadata["evidence_kind"] for ev in evidence}
        self.assertEqual(kinds["40100001"], "pain_signal_candidate")
        self.assertEqual(kinds["40100002"], "workaround")
        self.assertEqual(kinds["40100003"], "complaint")
        self.assertEqual(kinds["40100004"], "feature_request")
        self.assertEqual(kinds["40100005"], "product_launch")
        self.assertEqual(kinds["40100006"], "market_trend")
        self.assertEqual(kinds["40100007"], "solution_pattern")
        self.assertEqual(kinds["40100008"], "product_launch")
        self.assertEqual(kinds["40100009"], "pain_signal_candidate")
        self.assertEqual(kinds["40100010"], "unknown")
        # 40100011 contains pain keywords ("broken", "terrible", "unusable") in a comment > 100 chars
        self.assertEqual(kinds["40100011"], "pain_signal_candidate")
        self.assertEqual(kinds["40100012"], "unknown")  # self-promo comment, no pain keywords


# ---------------------------------------------------------------------------
# Noise / quality flag tests
# ---------------------------------------------------------------------------

class TestQualityFlags(unittest.TestCase):
    """Test deterministic noise/quality flags for HN hits."""

    def setUp(self) -> None:
        self.item = hn_scheduled_item()

    def _flags(self, hit: dict) -> list:
        ev = hn_hit_to_raw_evidence(hit, scheduled_item=self.item)
        return ev.raw_metadata.get("quality_flags", [])

    def test_low_text_context_flag_for_short_body(self) -> None:
        hit = {
            "objectID": "2001",
            "title": "Short post",
            "comment_text": "nice",
            "_tags": ["comment"],
        }
        self.assertIn("low_text_context", self._flags(hit))

    def test_flamewar_meta_discussion_flag(self) -> None:
        hit = {
            "objectID": "2002",
            "title": None,
            "comment_text": "HN is becoming toxic. The moderation on this site is terrible. Dang why was this flagged?",
            "_tags": ["comment"],
        }
        self.assertIn("flamewar_or_meta_discussion", self._flags(hit))

    def test_suspected_self_promo_flag(self) -> None:
        hit = {
            "objectID": "2003",
            "title": None,
            "comment_text": "Check out my startup we built an amazing product. Sign up today!",
            "_tags": ["comment"],
        }
        self.assertIn("suspected_self_promo", self._flags(hit))

    def test_launch_hype_flag_on_show_hn_with_hype_keywords(self) -> None:
        hit = {
            "objectID": "2004",
            "title": "Show HN: Revolutionary AI platform",
            "story_text": "This is a game changer and a breakthrough.",
            "points": 50,
            "_tags": ["story", "show_hn"],
        }
        self.assertIn("launch_hype", self._flags(hit))

    def test_missing_date_flag_when_no_created_at(self) -> None:
        hit = {
            "objectID": "2005",
            "title": "Post without date",
            "story_text": "Some content here.",
            "points": 10,
            "_tags": ["story"],
        }
        self.assertIn("missing_date", self._flags(hit))

    def test_low_confidence_source_for_low_points(self) -> None:
        hit = {
            "objectID": "2006",
            "title": "Low score post",
            "story_text": "Some text here for context.",
            "points": 1,
            "created_at": "2025-01-01T00:00:00Z",
            "_tags": ["story"],
        }
        self.assertIn("low_confidence_source", self._flags(hit))

    def test_requires_manual_review_when_any_flag_set(self) -> None:
        hit = {
            "objectID": "2007",
            "title": None,
            "comment_text": "nice",
            "_tags": ["comment"],
        }
        self.assertIn("requires_manual_review", self._flags(hit))

    def test_no_flags_for_clean_record(self) -> None:
        hit = {
            "objectID": "2008",
            "title": "Good discussion about fintech pain points",
            "story_text": "A detailed analysis of the pain points small businesses face with cash flow management. "
                           "We surveyed 500 small business owners and found that manual reporting is the biggest "
                           "time sink. This is a substantial article with good context.",
            "points": 25,
            "created_at": "2025-06-01T00:00:00Z",
            "_tags": ["story"],
        }
        self.assertEqual(self._flags(hit), [])

    def test_rich_fixture_flags_populated(self) -> None:
        item = hn_scheduled_item(max_results=50)
        evidence = parse_hn_algolia_hits(rich_fixture_payload(), scheduled_item=item)
        # Records 40100010 (short comment), 40100011 (flamewar),
        # 40100012 (self-promo), 40100013 (low points) should have flags
        flagged = {ev.raw_metadata["objectID"]: ev.raw_metadata.get("quality_flags", [])
                   for ev in evidence}
        self.assertIn("low_text_context", flagged.get("40100010", []))
        self.assertIn("flamewar_or_meta_discussion", flagged.get("40100011", []))
        self.assertIn("suspected_self_promo", flagged.get("40100012", []))
        self.assertIn("low_confidence_source", flagged.get("40100013", []))


# ---------------------------------------------------------------------------
# Source URL traceability tests
# ---------------------------------------------------------------------------

class TestSourceURLTraceability(unittest.TestCase):
    """Test source URL enforcement for HN collector."""

    def test_all_emitted_records_have_stable_source_url(self) -> None:
        item = hn_scheduled_item(max_results=50)
        evidence = parse_hn_algolia_hits(rich_fixture_payload(), scheduled_item=item)
        self.assertTrue(len(evidence) > 0)
        for ev in evidence:
            self.assertTrue(ev.source_url.startswith("https://news.ycombinator.com/item?id="))

    def test_no_placeholder_urls_in_output(self) -> None:
        item = hn_scheduled_item(max_results=50)
        evidence = parse_hn_algolia_hits(rich_fixture_payload(), scheduled_item=item)
        for ev in evidence:
            self.assertNotIn("urn:oos", ev.source_url.lower())
            self.assertNotIn("placeholder", ev.source_url.lower())

    def test_fixture_urls_are_deterministic(self) -> None:
        item = hn_scheduled_item(max_results=50)
        first = parse_hn_algolia_hits(rich_fixture_payload(), scheduled_item=item)
        second = parse_hn_algolia_hits(rich_fixture_payload(), scheduled_item=item)
        first_urls = [ev.source_url for ev in first]
        second_urls = [ev.source_url for ev in second]
        self.assertEqual(first_urls, second_urls)

    def test_rich_fixture_no_missing_urls(self) -> None:
        item = hn_scheduled_item(max_results=50)
        evidence = parse_hn_algolia_hits(rich_fixture_payload(), scheduled_item=item)
        for ev in evidence:
            self.assertTrue(ev.source_url)
            self.assertTrue(ev.source_url.startswith("https://"))


# ---------------------------------------------------------------------------
# Source quality summary tests
# ---------------------------------------------------------------------------

class TestSourceQualitySummary(unittest.TestCase):
    """Test HN-local source quality summary."""

    def test_basic_summary_counts(self) -> None:
        item = hn_scheduled_item(max_results=50)
        payload = rich_fixture_payload()
        evidence = parse_hn_algolia_hits(payload, scheduled_item=item)
        summary = build_hn_source_quality_summary(payload, evidence)

        self.assertEqual(summary.source_id, "hacker_news")
        self.assertEqual(summary.source_type, "discussion")
        self.assertEqual(summary.records_seen, 15)  # 15 hits in rich fixture
        self.assertGreater(summary.records_emitted, 0)
        self.assertGreaterEqual(summary.records_rejected, 0)

    def test_duplicate_count_tracks_exact_duplicates(self) -> None:
        item = hn_scheduled_item(max_results=50)
        payload = rich_fixture_payload()
        summary = HNSourceQualitySummary()
        evidence = parse_hn_algolia_hits(payload, scheduled_item=item, quality_summary=summary)
        # Rich fixture has 2 hits with objectID "40100001"
        self.assertEqual(summary.duplicate_count, 1)

    def test_empty_payload_produces_valid_summary(self) -> None:
        summary = build_hn_source_quality_summary({"hits": []}, [])
        self.assertEqual(summary.records_seen, 0)
        self.assertEqual(summary.records_emitted, 0)

    def test_summary_with_malformed_payload(self) -> None:
        summary = build_hn_source_quality_summary({"hits": "not_a_list"}, [])
        self.assertEqual(summary.records_seen, 0)

    def test_summary_validate_rejects_invalid_counts(self) -> None:
        summary = HNSourceQualitySummary(records_seen=-1)
        with self.assertRaises(ValueError):
            summary.validate()

    def test_quality_flag_counts_in_summary(self) -> None:
        item = hn_scheduled_item(max_results=50)
        payload = rich_fixture_payload()
        evidence = parse_hn_algolia_hits(payload, scheduled_item=item)
        summary = build_hn_source_quality_summary(payload, evidence)
        self.assertIsInstance(summary.quality_flag_counts, dict)


# ---------------------------------------------------------------------------
# Privacy-safe author/context tests
# ---------------------------------------------------------------------------

class TestPrivacySafeAuthorContext(unittest.TestCase):
    """Test privacy-safe author_or_context behavior."""

    def setUp(self) -> None:
        self.item = hn_scheduled_item()

    def test_ask_hn_poster_context(self) -> None:
        hit = {"objectID": "p1", "title": "Ask HN: test", "story_text": "test body",
               "_tags": ["story", "ask_hn"]}
        ev = hn_hit_to_raw_evidence(hit, scheduled_item=self.item)
        self.assertEqual(ev.author_or_context, "Ask HN poster")

    def test_show_hn_maker_context(self) -> None:
        hit = {"objectID": "p2", "title": "Show HN: test", "story_text": "test body",
               "_tags": ["story", "show_hn"]}
        ev = hn_hit_to_raw_evidence(hit, scheduled_item=self.item)
        self.assertEqual(ev.author_or_context, "Show HN maker")

    def test_commenter_context(self) -> None:
        hit = {"objectID": "p3", "title": None, "comment_text": "test comment",
               "_tags": ["comment"]}
        ev = hn_hit_to_raw_evidence(hit, scheduled_item=self.item)
        self.assertEqual(ev.author_or_context, "HN commenter")

    def test_story_author_context(self) -> None:
        hit = {"objectID": "p4", "title": "A story", "story_text": "story body",
               "_tags": ["story"]}
        ev = hn_hit_to_raw_evidence(hit, scheduled_item=self.item)
        self.assertEqual(ev.author_or_context, "HN story author")

    def test_no_username_in_author_or_context(self) -> None:
        for hit in rich_fixture_payload()["hits"]:
            if not hit.get("objectID"):
                continue
            ev = hn_hit_to_raw_evidence(hit, scheduled_item=self.item)
            if ev is None:
                continue
            self.assertNotIn("@", ev.author_or_context)
            self.assertNotIn("raw_hn_username", ev.author_or_context)


# ---------------------------------------------------------------------------
# Malformed / low-quality input handling tests
# ---------------------------------------------------------------------------

class TestMalformedInputHandling(unittest.TestCase):
    """Test handling of malformed and edge-case inputs."""

    def setUp(self) -> None:
        self.item = hn_scheduled_item(max_results=50)

    def test_non_dict_hits_are_skipped(self) -> None:
        payload = {"hits": ["not_a_dict", 42, None]}
        evidence = parse_hn_algolia_hits(payload, scheduled_item=self.item)
        self.assertEqual(len(evidence), 0)

    def test_hits_is_not_a_list(self) -> None:
        evidence = parse_hn_algolia_hits({"hits": "not_a_list"}, scheduled_item=self.item)
        self.assertEqual(evidence, [])

    def test_completely_empty_hit_retained_with_fallback(self) -> None:
        """Empty-content hits are retained with fallback title/body (pre-v2.12 behavior preserved).

        The quality flags low_text_context and low_confidence_source will flag these
        for downstream review, but they are not silently dropped.
        """
        evidence = parse_hn_algolia_hits(
            {"hits": [{"objectID": "e1", "title": None, "story_text": None,
                       "comment_text": None, "url": None, "story_url": None,
                       "_tags": []}]},
            scheduled_item=self.item,
        )
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_id, "raw_hacker_news_e1")
        self.assertIn("low_text_context", evidence[0].raw_metadata.get("quality_flags", []))


if __name__ == "__main__":
    unittest.main()
