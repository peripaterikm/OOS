import unittest
from dataclasses import replace

from oos.query_planner import (
    PlanningLimits,
    QueryPlanner,
    make_query_plan_dedup_key,
    make_query_plan_id,
)
from oos.source_registry import (
    QUERY_KIND_PRIORITY,
    SourceRegistry,
    TopicProfile,
    default_source_registry,
    default_topic_profiles,
)


def registry_by_id() -> dict:
    return default_source_registry().by_id()


def active_plan_source_ids() -> set[str]:
    plans = QueryPlanner().build_plans(
        registry=default_source_registry(),
        topic_profiles=default_topic_profiles(),
    )
    return {plan.source_id for plan in plans}


class TestSourceRegistryQueryPlanner(unittest.TestCase):
    def test_default_registry_contains_expected_phase_b_policies(self) -> None:
        sources = registry_by_id()

        hn = sources["hacker_news_algolia"]
        self.assertEqual(hn.source_type, "hacker_news_algolia")
        self.assertEqual(hn.phase, "Phase B")
        self.assertTrue(hn.enabled)
        self.assertFalse(hn.auth_required)
        self.assertFalse(hn.requires_registered_app_key)
        self.assertFalse(hn.commercial_review_required)
        self.assertTrue(hn.access_realistic_for_solo_founder)
        self.assertTrue(hn.live_network_disabled_by_default)

        github = sources["github_issues"]
        self.assertEqual(github.source_type, "github_issues")
        self.assertEqual(github.phase, "Phase B")
        self.assertTrue(github.enabled)
        self.assertFalse(github.auth_required)
        self.assertFalse(github.commercial_review_required)
        self.assertTrue(github.access_realistic_for_solo_founder)
        self.assertTrue(github.live_network_disabled_by_default)

        stack_exchange = sources["stack_exchange"]
        self.assertEqual(stack_exchange.source_type, "stack_exchange")
        self.assertEqual(stack_exchange.phase, "Phase B")
        self.assertTrue(stack_exchange.enabled)
        self.assertTrue(stack_exchange.requires_registered_app_key)
        self.assertFalse(stack_exchange.commercial_review_required)
        self.assertTrue(stack_exchange.live_network_disabled_by_default)

        rss = sources["rss_feeds"]
        self.assertEqual(rss.source_type, "rss_feed")
        self.assertEqual(rss.phase, "Phase B")
        self.assertTrue(rss.enabled)
        self.assertFalse(rss.auth_required)
        self.assertFalse(rss.commercial_review_required)
        self.assertTrue(rss.live_network_disabled_by_default)
        self.assertIn("no_scraping", rss.access_policy)

    def test_disabled_and_deferred_sources_do_not_generate_active_query_plans(self) -> None:
        plan_source_ids = active_plan_source_ids()

        for disabled_source_id in ("g2", "reddit", "linkedin", "gdelt", "trustpilot", "capterra"):
            self.assertNotIn(disabled_source_id, plan_source_ids)

    def test_ai_cfo_smb_is_only_first_active_topic(self) -> None:
        profiles = default_topic_profiles()
        active_topic_ids = [profile.topic_id for profile in profiles if profile.active]

        self.assertEqual(active_topic_ids, ["ai_cfo_smb"])

    def test_future_topics_are_inactive_stubs(self) -> None:
        profiles = {profile.topic_id: profile for profile in default_topic_profiles()}

        self.assertEqual(profiles["insurance_israel"].status, "inactive_future")
        self.assertFalse(profiles["insurance_israel"].active)
        self.assertEqual(profiles["life_management_system"].status, "inactive_future")
        self.assertFalse(profiles["life_management_system"].active)

    def test_planner_generates_deterministic_query_plans_for_active_topic(self) -> None:
        registry = default_source_registry()
        profiles = default_topic_profiles()

        first = QueryPlanner().build_plans(registry=registry, topic_profiles=profiles)
        second = QueryPlanner().build_plans(registry=registry, topic_profiles=profiles)

        self.assertEqual(first, second)
        self.assertTrue(first)
        self.assertEqual({plan.topic_id for plan in first}, {"ai_cfo_smb"})
        self.assertTrue(all(plan.query_plan_id.startswith("qp_") for plan in first))

    def test_planner_enforces_max_query_plans_per_source_topic(self) -> None:
        plans = QueryPlanner(limits=PlanningLimits(max_query_plans_per_source_topic=2)).build_plans(
            registry=default_source_registry(),
            topic_profiles=default_topic_profiles(),
        )
        counts = {}
        for plan in plans:
            key = (plan.source_id, plan.topic_id)
            counts[key] = counts.get(key, 0) + 1

        self.assertTrue(counts)
        self.assertTrue(all(count <= 2 for count in counts.values()))

    def test_planner_prioritizes_query_kinds_in_expected_order(self) -> None:
        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=default_topic_profiles(),
        )
        for source_id in {plan.source_id for plan in plans}:
            source_priorities = [
                plan.priority
                for plan in plans
                if plan.source_id == source_id and plan.topic_id == "ai_cfo_smb"
            ]
            self.assertEqual(source_priorities, sorted(source_priorities))
        self.assertEqual(QUERY_KIND_PRIORITY[0], "pain_query")
        self.assertEqual(QUERY_KIND_PRIORITY[-1], "trend_trigger_query")

    def test_planner_deduplicates_equivalent_query_text(self) -> None:
        base = [profile for profile in default_topic_profiles() if profile.topic_id == "ai_cfo_smb"][0]
        duplicate_profile = replace(
            base,
            allowed_source_ids=["hacker_news_algolia"],
            query_kinds=["pain_query"],
            query_templates={"pain_query": ["AI CFO SMB pain", "  ai   cfo smb   pain  "]},
        )

        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=[duplicate_profile],
        )

        self.assertEqual(len(plans), 1)
        self.assertEqual(len({plan.dedup_key for plan in plans}), 1)

    def test_disabled_sources_are_skipped(self) -> None:
        registry = default_source_registry()
        sources = [
            replace(source, enabled=False) if source.source_id == "hacker_news_algolia" else source
            for source in registry.sources
        ]
        plans = QueryPlanner().build_plans(
            registry=SourceRegistry(sources=sources),
            topic_profiles=default_topic_profiles(),
        )

        self.assertNotIn("hacker_news_algolia", {plan.source_id for plan in plans})

    def test_inactive_topics_are_skipped(self) -> None:
        inactive_profiles = [replace(profile, status="inactive_future") for profile in default_topic_profiles()]

        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=inactive_profiles,
        )

        self.assertEqual(plans, [])

    def test_live_network_enabled_defaults_to_false(self) -> None:
        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=default_topic_profiles(),
        )

        self.assertTrue(plans)
        self.assertTrue(all(plan.live_network_enabled is False for plan in plans))

    def test_query_plan_ids_and_dedup_keys_are_deterministic(self) -> None:
        dedup_key = make_query_plan_dedup_key(
            source_id="hacker_news_algolia",
            topic_id="ai_cfo_smb",
            query_kind="pain_query",
            query_text=" AI   CFO SMB Pain ",
        )
        equivalent_dedup_key = make_query_plan_dedup_key(
            source_id="hacker_news_algolia",
            topic_id="ai_cfo_smb",
            query_kind="pain_query",
            query_text="ai cfo smb pain",
        )
        query_plan_id = make_query_plan_id(
            source_id="hacker_news_algolia",
            topic_id="ai_cfo_smb",
            query_kind="pain_query",
            query_text="AI CFO SMB Pain",
        )

        self.assertEqual(dedup_key, equivalent_dedup_key)
        self.assertEqual(query_plan_id, "qp_710221edcd60c0c1")

    def test_undefined_active_topic_source_is_rejected(self) -> None:
        profile = TopicProfile(
            topic_id="ai_cfo_smb",
            status="active",
            topic_keywords=["AI CFO"],
            allowed_source_ids=["missing_source"],
            query_kinds=["pain_query"],
            query_templates={"pain_query": ["AI CFO pain"]},
        )

        with self.assertRaisesRegex(ValueError, "undefined source_id"):
            QueryPlanner().build_plans(registry=default_source_registry(), topic_profiles=[profile])

    def test_no_network_api_llm_or_secrets_required(self) -> None:
        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=default_topic_profiles(),
        )

        self.assertTrue(plans)
        self.assertTrue(all(plan.live_network_enabled is False for plan in plans))
        self.assertTrue(all("token" not in plan.query_text.lower() for plan in plans))
        self.assertTrue(all("api key" not in plan.query_text.lower() for plan in plans))


if __name__ == "__main__":
    unittest.main()
