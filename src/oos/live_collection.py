from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Dict, Iterable, List, Optional, Set

from .collection_scheduler import CollectionLimits, CollectionScheduler, ScheduledCollectionItem
from .collectors import BaseCollector
from .github_issues_collector import GitHubIssuesCollector
from .hn_algolia_collector import HNAlgoliaCollector
from .models import RawEvidence
from .query_planner import QueryPlanner
from .rss_collector import RSSFeedCollector
from .source_registry import SourceRegistry, TopicProfile, default_source_registry, default_topic_profiles
from .stack_exchange_collector import StackExchangeCollector


CollectorFactory = Callable[[bool], BaseCollector]


def default_collector_factories() -> Dict[str, CollectorFactory]:
    return {
        "hacker_news_algolia": lambda allow_live_network: HNAlgoliaCollector(
            allow_live_network=allow_live_network
        ),
        "github_issues": lambda allow_live_network: GitHubIssuesCollector(
            allow_live_network=allow_live_network
        ),
        "stack_exchange": lambda allow_live_network: StackExchangeCollector(
            allow_live_network=allow_live_network
        ),
        "rss_feed": lambda allow_live_network: RSSFeedCollector(
            allow_live_network=allow_live_network
        ),
    }


@dataclass(frozen=True)
class LiveCollectionRun:
    raw_evidence: List[RawEvidence]
    collection_metadata: Dict[str, object]


def collect_raw_evidence_for_topic(
    *,
    topic_id: str,
    allow_live_network: bool = False,
    max_total_queries: int = 4,
    max_queries_per_source: int = 2,
    max_queries_per_topic: Optional[int] = None,
    max_results_per_query: int = 5,
    allowed_source_ids: Optional[Set[str]] = None,
    allowed_source_types: Optional[Set[str]] = None,
    registry: Optional[SourceRegistry] = None,
    topic_profiles: Optional[Iterable[TopicProfile]] = None,
    collector_factories: Optional[Dict[str, CollectorFactory]] = None,
) -> LiveCollectionRun:
    registry = registry or default_source_registry()
    topic_profiles = list(topic_profiles or default_topic_profiles())
    source_ids = set(allowed_source_ids or set())
    source_types = set(allowed_source_types or set())
    if source_types:
        matching_source_ids = {
            source.source_id for source in registry.sources if source.source_type in source_types
        }
        source_ids = source_ids & matching_source_ids if source_ids else matching_source_ids

    planning_limits = QueryPlanner().limits
    query_plans = QueryPlanner(limits=planning_limits).build_plans(
        registry=registry,
        topic_profiles=topic_profiles,
    )
    topic_query_plans = [plan for plan in query_plans if plan.topic_id == topic_id]
    if source_ids:
        topic_query_plans = [plan for plan in topic_query_plans if plan.source_id in source_ids]

    limits = CollectionLimits(
        max_total_queries=max_total_queries,
        max_queries_per_source=max_queries_per_source,
        max_queries_per_topic=max_queries_per_topic or max_total_queries,
        max_results_per_query=max_results_per_query,
        allow_live_network=allow_live_network,
        allowed_source_ids=source_ids or None,
        allowed_topic_ids={topic_id},
    )
    scheduled_items = CollectionScheduler(limits=limits).build_queue(topic_query_plans)
    scheduled_items = [
        replace(item, live_network_enabled=allow_live_network)
        for item in scheduled_items
    ]

    factories = collector_factories or default_collector_factories()
    collectors_by_type = {
        source_type: factory(allow_live_network)
        for source_type, factory in factories.items()
    }

    raw_evidence: List[RawEvidence] = []
    collectors_attempted: List[str] = []
    collectors_succeeded: List[str] = []
    collectors_failed: List[str] = []
    collection_errors: List[Dict[str, str]] = []

    for scheduled_item in scheduled_items:
        collector = collectors_by_type.get(scheduled_item.source_type)
        collectors_attempted.append(scheduled_item.source_type)
        if collector is None:
            collectors_failed.append(scheduled_item.source_type)
            collection_errors.append(
                _collection_error(
                    scheduled_item,
                    f"No collector registered for source_type={scheduled_item.source_type}",
                )
            )
            continue
        if not collector.supports(scheduled_item):
            collectors_failed.append(scheduled_item.source_type)
            collection_errors.append(
                _collection_error(
                    scheduled_item,
                    f"Collector does not support source_id={scheduled_item.source_id}",
                )
            )
            continue
        try:
            result = collector.collect(scheduled_item)
        except Exception as exc:  # noqa: BLE001 - deliberate per-source isolation for dry-safe collection
            collectors_failed.append(scheduled_item.source_type)
            collection_errors.append(_collection_error(scheduled_item, str(exc)))
            continue
        for error in result.collection_errors or []:
            merged_error = _collection_error(scheduled_item, error.get("error", "collector reported nonfatal error"))
            merged_error.update({key: str(value) for key, value in error.items()})
            collection_errors.append(merged_error)
        raw_evidence.extend(result.evidence[: scheduled_item.max_results])
        collectors_succeeded.append(scheduled_item.source_type)

    mode = "live_collectors" if allow_live_network else "collectors_offline"
    metadata: Dict[str, object] = {
        "collection_mode": mode,
        "live_network_enabled": allow_live_network,
        "query_plan_count": len(topic_query_plans),
        "scheduled_query_count": len(scheduled_items),
        "collectors_attempted": sorted(set(collectors_attempted)),
        "collectors_succeeded": sorted(set(collectors_succeeded)),
        "collectors_failed": sorted(set(collectors_failed)),
        "collection_errors": collection_errors,
        "source_ids_filter": sorted(source_ids),
        "source_types_filter": sorted(source_types),
        "max_total_queries": max_total_queries,
        "max_queries_per_source": max_queries_per_source,
        "max_queries_per_topic": max_queries_per_topic or max_total_queries,
        "max_results_per_query": max_results_per_query,
    }
    if not allow_live_network:
        metadata["notes"] = [
            "Collector mode ran with live network disabled.",
            "No live collector network calls were allowed.",
        ]
    return LiveCollectionRun(raw_evidence=raw_evidence, collection_metadata=metadata)


def _collection_error(scheduled_item: ScheduledCollectionItem, error: str) -> Dict[str, str]:
    return {
        "query_plan_id": scheduled_item.query_plan_id,
        "source_id": scheduled_item.source_id,
        "source_type": scheduled_item.source_type,
        "topic_id": scheduled_item.topic_id,
        "query_kind": scheduled_item.query_kind,
        "error": error,
    }
