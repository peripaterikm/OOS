import unittest
from dataclasses import replace

from oos.collection_scheduler import CollectionLimits, CollectionScheduler
from oos.collectors import FixtureCollector, collect_with_fixture_collectors
from oos.models import RawEvidence, compute_raw_evidence_content_hash
from oos.query_planner import QueryPlanner
from oos.source_registry import default_source_registry, default_topic_profiles


def default_plans():
    return QueryPlanner().build_plans(
        registry=default_source_registry(),
        topic_profiles=default_topic_profiles(),
    )


def make_fixture_evidence(**overrides: object) -> RawEvidence:
    title = str(overrides.pop("title", "Fixture source title"))
    body = str(overrides.pop("body", "Fixture source body"))
    values = {
        "evidence_id": "fixture_raw_ev_1",
        "source_id": "hacker_news_algolia",
        "source_type": "hacker_news_algolia",
        "source_name": "Hacker News Algolia",
        "source_url": "https://example.test/source/1",
        "collected_at": "2026-01-01T00:00:00+00:00",
        "title": title,
        "body": body,
        "language": "en",
        "topic_id": "ai_cfo_smb",
        "query_kind": "pain_query",
        "content_hash": compute_raw_evidence_content_hash(title=title, body=body),
        "author_or_context": "developer",
        "raw_metadata": {"fixture": True},
        "access_policy": "offline_fixture",
        "collection_method": "fixture_collector",
    }
    values.update(overrides)
    evidence = RawEvidence(**values)
    evidence.validate()
    return evidence


class TestCollectionSchedulerCollectorInterface(unittest.TestCase):
    def test_collection_limits_defaults_disable_live_network(self) -> None:
        limits = CollectionLimits()

        limits.validate()
        self.assertFalse(limits.allow_live_network)

    def test_scheduler_creates_deterministic_bounded_queue_from_query_plans(self) -> None:
        plans = default_plans()

        first = CollectionScheduler(limits=CollectionLimits(max_total_queries=5)).build_queue(plans)
        second = CollectionScheduler(limits=CollectionLimits(max_total_queries=5)).build_queue(reversed(plans))

        self.assertEqual(first, second)
        self.assertEqual([item.scheduled_order for item in first], [1, 2, 3, 4, 5])

    def test_scheduler_enforces_max_total_queries(self) -> None:
        queue = CollectionScheduler(limits=CollectionLimits(max_total_queries=3)).build_queue(default_plans())

        self.assertEqual(len(queue), 3)

    def test_scheduler_enforces_max_queries_per_source(self) -> None:
        queue = CollectionScheduler(limits=CollectionLimits(max_queries_per_source=1)).build_queue(default_plans())
        counts = {}
        for item in queue:
            counts[item.source_id] = counts.get(item.source_id, 0) + 1

        self.assertTrue(counts)
        self.assertTrue(all(count == 1 for count in counts.values()))

    def test_scheduler_enforces_max_queries_per_topic(self) -> None:
        queue = CollectionScheduler(limits=CollectionLimits(max_queries_per_topic=2)).build_queue(default_plans())
        counts = {}
        for item in queue:
            counts[item.topic_id] = counts.get(item.topic_id, 0) + 1

        self.assertEqual(counts, {"ai_cfo_smb": 2})

    def test_scheduler_respects_allowed_source_ids(self) -> None:
        queue = CollectionScheduler(
            limits=CollectionLimits(allowed_source_ids={"github_issues"})
        ).build_queue(default_plans())

        self.assertTrue(queue)
        self.assertEqual({item.source_id for item in queue}, {"github_issues"})

    def test_scheduler_respects_allowed_topic_ids(self) -> None:
        allowed = CollectionScheduler(
            limits=CollectionLimits(allowed_topic_ids={"ai_cfo_smb"})
        ).build_queue(default_plans())
        blocked = CollectionScheduler(
            limits=CollectionLimits(allowed_topic_ids={"insurance_israel"})
        ).build_queue(default_plans())

        self.assertTrue(allowed)
        self.assertEqual(blocked, [])

    def test_scheduler_skips_live_network_query_plans_unless_allowed(self) -> None:
        live_plan = replace(default_plans()[0], live_network_enabled=True)

        blocked = CollectionScheduler().build_queue([live_plan])
        allowed = CollectionScheduler(limits=CollectionLimits(allow_live_network=True)).build_queue([live_plan])

        self.assertEqual(blocked, [])
        self.assertEqual(len(allowed), 1)
        self.assertTrue(allowed[0].live_network_enabled)

    def test_scheduler_deduplicates_repeated_query_plans_or_dedup_keys(self) -> None:
        plan = default_plans()[0]
        duplicate = replace(plan, query_plan_id="qp_duplicate_same_dedup_key")

        queue = CollectionScheduler().build_queue([duplicate, plan, plan])

        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0].dedup_key, plan.dedup_key)

    def test_fixture_collector_returns_raw_evidence_without_network(self) -> None:
        item = CollectionScheduler(limits=CollectionLimits(max_total_queries=1)).build_queue(default_plans())[0]
        result = FixtureCollector(source_id=item.source_id).collect(item)

        self.assertEqual(len(result.evidence), 1)
        self.assertFalse(result.live_network_used)
        self.assertIsInstance(result.evidence[0], RawEvidence)

    def test_fixture_collector_preserves_source_url_topic_query_kind_and_source_id(self) -> None:
        item = CollectionScheduler(limits=CollectionLimits(max_total_queries=1)).build_queue(default_plans())[0]
        fixture = make_fixture_evidence(
            source_id=item.source_id,
            source_type=item.source_type,
            topic_id=item.topic_id,
            query_kind=item.query_kind,
            source_url="https://example.test/preserved-source",
        )

        result = FixtureCollector(
            source_id=item.source_id,
            evidence_by_dedup_key={item.dedup_key: [fixture]},
        ).collect(item)
        evidence = result.evidence[0]

        self.assertEqual(evidence.source_url, "https://example.test/preserved-source")
        self.assertEqual(evidence.topic_id, item.topic_id)
        self.assertEqual(evidence.query_kind, item.query_kind)
        self.assertEqual(evidence.source_id, item.source_id)

    def test_base_collector_contract_rejects_unsupported_source(self) -> None:
        item = CollectionScheduler(limits=CollectionLimits(max_total_queries=1)).build_queue(default_plans())[0]

        with self.assertRaisesRegex(ValueError, "does not support"):
            FixtureCollector(source_id="other_source").collect(item)

    def test_source_registry_query_planner_scheduler_fixture_collector_offline_flow(self) -> None:
        plans = default_plans()
        queue = CollectionScheduler(limits=CollectionLimits(max_total_queries=4)).build_queue(plans)
        collectors = [
            FixtureCollector(source_id="github_issues"),
            FixtureCollector(source_id="hacker_news_algolia"),
            FixtureCollector(source_id="rss_feeds"),
            FixtureCollector(source_id="stack_exchange"),
        ]

        evidence = collect_with_fixture_collectors(queue, collectors)

        self.assertEqual(len(evidence), len(queue))
        self.assertTrue(all(item.source_url.startswith("fixture://") for item in evidence))
        self.assertEqual({item.topic_id for item in evidence}, {"ai_cfo_smb"})

    def test_no_secrets_api_keys_required(self) -> None:
        queue = CollectionScheduler(limits=CollectionLimits(max_total_queries=3)).build_queue(default_plans())
        evidence = collect_with_fixture_collectors(queue, [FixtureCollector()])

        self.assertTrue(evidence)
        self.assertTrue(all("api_key" not in item.raw_metadata for item in evidence))
        self.assertTrue(all("token" not in item.raw_metadata for item in evidence))

    def test_no_internet_api_or_llm_calls_are_made(self) -> None:
        queue = CollectionScheduler(limits=CollectionLimits(max_total_queries=2)).build_queue(default_plans())
        evidence = collect_with_fixture_collectors(queue, [FixtureCollector()])

        self.assertTrue(queue)
        self.assertTrue(evidence)
        self.assertTrue(all(not item.live_network_enabled for item in queue))
        self.assertTrue(all(item.collection_method == "fixture_collector" for item in evidence))


if __name__ == "__main__":
    unittest.main()
