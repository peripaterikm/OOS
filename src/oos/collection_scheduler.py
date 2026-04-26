from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Set

from .query_planner import QueryPlan


@dataclass(frozen=True)
class CollectionLimits:
    max_total_queries: int = 50
    max_queries_per_source: int = 20
    max_queries_per_topic: int = 30
    max_results_per_query: int = 25
    allow_live_network: bool = False
    allowed_source_ids: Optional[Set[str]] = None
    allowed_topic_ids: Optional[Set[str]] = None

    def validate(self) -> None:
        for field_name in (
            "max_total_queries",
            "max_queries_per_source",
            "max_queries_per_topic",
            "max_results_per_query",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"CollectionLimits.{field_name} must be a positive int")
        if not isinstance(self.allow_live_network, bool):
            raise ValueError("CollectionLimits.allow_live_network must be a bool")
        for field_name in ("allowed_source_ids", "allowed_topic_ids"):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, set) or any(not isinstance(item, str) or not item.strip() for item in value)
            ):
                raise ValueError(f"CollectionLimits.{field_name} must be None or a set of non-empty strings")


@dataclass(frozen=True)
class ScheduledCollectionItem:
    query_plan_id: str
    source_id: str
    source_type: str
    topic_id: str
    query_kind: str
    query_text: str
    priority: int
    max_results: int
    live_network_enabled: bool
    scheduled_order: int
    dedup_key: str

    def validate(self) -> None:
        for field_name in (
            "query_plan_id",
            "source_id",
            "source_type",
            "topic_id",
            "query_kind",
            "query_text",
            "dedup_key",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"ScheduledCollectionItem.{field_name} must be a non-empty string")
        if not isinstance(self.priority, int) or self.priority <= 0:
            raise ValueError("ScheduledCollectionItem.priority must be a positive int")
        if not isinstance(self.max_results, int) or self.max_results <= 0:
            raise ValueError("ScheduledCollectionItem.max_results must be a positive int")
        if not isinstance(self.live_network_enabled, bool):
            raise ValueError("ScheduledCollectionItem.live_network_enabled must be a bool")
        if not isinstance(self.scheduled_order, int) or self.scheduled_order <= 0:
            raise ValueError("ScheduledCollectionItem.scheduled_order must be a positive int")

    @classmethod
    def from_query_plan(
        cls,
        *,
        query_plan: QueryPlan,
        scheduled_order: int,
        max_results: int,
    ) -> "ScheduledCollectionItem":
        item = cls(
            query_plan_id=query_plan.query_plan_id,
            source_id=query_plan.source_id,
            source_type=query_plan.source_type,
            topic_id=query_plan.topic_id,
            query_kind=query_plan.query_kind,
            query_text=query_plan.query_text,
            priority=query_plan.priority,
            max_results=max_results,
            live_network_enabled=query_plan.live_network_enabled,
            scheduled_order=scheduled_order,
            dedup_key=query_plan.dedup_key,
        )
        item.validate()
        return item


class CollectionScheduler:
    def __init__(self, *, limits: Optional[CollectionLimits] = None):
        self.limits = limits or CollectionLimits()
        self.limits.validate()

    def build_queue(self, query_plans: Iterable[QueryPlan]) -> List[ScheduledCollectionItem]:
        seen: Set[str] = set()
        source_counts: dict[str, int] = {}
        topic_counts: dict[str, int] = {}
        queue: List[ScheduledCollectionItem] = []

        for plan in sorted(query_plans, key=self._sort_key):
            if not self._plan_allowed(plan):
                continue
            dedup_key = plan.dedup_key or plan.query_plan_id
            if dedup_key in seen:
                continue
            if len(queue) >= self.limits.max_total_queries:
                break
            if source_counts.get(plan.source_id, 0) >= self.limits.max_queries_per_source:
                continue
            if topic_counts.get(plan.topic_id, 0) >= self.limits.max_queries_per_topic:
                continue

            max_results = min(plan.max_results, self.limits.max_results_per_query)
            item = ScheduledCollectionItem.from_query_plan(
                query_plan=plan,
                scheduled_order=len(queue) + 1,
                max_results=max_results,
            )
            queue.append(item)
            seen.add(dedup_key)
            source_counts[plan.source_id] = source_counts.get(plan.source_id, 0) + 1
            topic_counts[plan.topic_id] = topic_counts.get(plan.topic_id, 0) + 1

        return queue

    def _plan_allowed(self, plan: QueryPlan) -> bool:
        if plan.live_network_enabled and not self.limits.allow_live_network:
            return False
        if self.limits.allowed_source_ids is not None and plan.source_id not in self.limits.allowed_source_ids:
            return False
        if self.limits.allowed_topic_ids is not None and plan.topic_id not in self.limits.allowed_topic_ids:
            return False
        return True

    def _sort_key(self, plan: QueryPlan) -> tuple[int, str, str, str, str, str]:
        return (
            plan.priority,
            plan.source_id,
            plan.topic_id,
            plan.query_kind,
            plan.dedup_key,
            plan.query_plan_id,
        )
