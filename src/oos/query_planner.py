from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .customer_voice_queries import APPROVAL_STATE_APPROVED, CustomerVoiceQuery
from .source_registry import QUERY_KIND_PRIORITY, SourceConfig, SourceRegistry, TopicProfile


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_query_text(query_text: str) -> str:
    return _WHITESPACE_RE.sub(" ", query_text.strip()).lower()


def make_query_plan_dedup_key(source_id: str, topic_id: str, query_kind: str, query_text: str) -> str:
    return "|".join(
        [
            source_id.strip(),
            topic_id.strip(),
            query_kind.strip(),
            normalize_query_text(query_text),
        ]
    )


def make_query_plan_id(source_id: str, topic_id: str, query_kind: str, query_text: str) -> str:
    dedup_key = make_query_plan_dedup_key(
        source_id=source_id,
        topic_id=topic_id,
        query_kind=query_kind,
        query_text=query_text,
    )
    digest = hashlib.sha256(dedup_key.encode("utf-8")).hexdigest()[:16]
    return f"qp_{digest}"


@dataclass(frozen=True)
class PlanningLimits:
    max_query_plans_per_source_topic: int = 10
    default_max_results: int = 25

    def validate(self) -> None:
        if not isinstance(self.max_query_plans_per_source_topic, int) or self.max_query_plans_per_source_topic <= 0:
            raise ValueError("PlanningLimits.max_query_plans_per_source_topic must be a positive int")
        if not isinstance(self.default_max_results, int) or self.default_max_results <= 0:
            raise ValueError("PlanningLimits.default_max_results must be a positive int")


@dataclass(frozen=True)
class QueryPlan:
    query_plan_id: str
    source_id: str
    source_type: str
    topic_id: str
    query_kind: str
    query_text: str
    priority: int
    max_results: int
    live_network_enabled: bool
    generated_from: str
    dedup_key: str
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        for field_name in (
            "query_plan_id",
            "source_id",
            "source_type",
            "topic_id",
            "query_kind",
            "query_text",
            "generated_from",
            "dedup_key",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"QueryPlan.{field_name} must be a non-empty string")
        if not isinstance(self.priority, int) or self.priority <= 0:
            raise ValueError("QueryPlan.priority must be a positive int")
        if not isinstance(self.max_results, int) or self.max_results <= 0:
            raise ValueError("QueryPlan.max_results must be a positive int")
        if not isinstance(self.live_network_enabled, bool):
            raise ValueError("QueryPlan.live_network_enabled must be a bool")
        expected_key = make_query_plan_dedup_key(
            source_id=self.source_id,
            topic_id=self.topic_id,
            query_kind=self.query_kind,
            query_text=self.query_text,
        )
        if self.dedup_key != expected_key:
            raise ValueError("QueryPlan.dedup_key must match source/topic/kind/normalized query_text")
        expected_id = make_query_plan_id(
            source_id=self.source_id,
            topic_id=self.topic_id,
            query_kind=self.query_kind,
            query_text=self.query_text,
        )
        if self.query_plan_id != expected_id:
            raise ValueError("QueryPlan.query_plan_id must be deterministic from dedup_key")
        if not isinstance(self.raw_metadata, dict):
            raise ValueError("QueryPlan.raw_metadata must be a dict")


class QueryPlanner:
    def __init__(
        self,
        *,
        query_kind_priority: Optional[List[str]] = None,
        limits: Optional[PlanningLimits] = None,
    ):
        self.query_kind_priority = query_kind_priority or list(QUERY_KIND_PRIORITY)
        self.limits = limits or PlanningLimits()
        self.limits.validate()

    def build_plans(self, registry: SourceRegistry, topic_profiles: Iterable[TopicProfile]) -> List[QueryPlan]:
        registry.validate()
        sources_by_id = registry.by_id()
        active_topics = self._active_topics(topic_profiles)
        plans: List[QueryPlan] = []
        seen: Set[str] = set()

        for topic in sorted(active_topics, key=lambda item: item.topic_id):
            topic_cap = min(topic.max_queries_per_source_topic, self.limits.max_query_plans_per_source_topic)
            for source in self._eligible_sources_for_topic(sources_by_id=sources_by_id, topic=topic):
                source_topic_count = 0
                for query_kind in self._ordered_query_kinds(topic=topic, source=source):
                    for query_text in topic.query_templates.get(query_kind, []):
                        dedup_key = make_query_plan_dedup_key(
                            source_id=source.source_id,
                            topic_id=topic.topic_id,
                            query_kind=query_kind,
                            query_text=query_text,
                        )
                        if dedup_key in seen:
                            continue
                        if source_topic_count >= topic_cap:
                            break

                        plan = QueryPlan(
                            query_plan_id=make_query_plan_id(
                                source_id=source.source_id,
                                topic_id=topic.topic_id,
                                query_kind=query_kind,
                                query_text=query_text,
                            ),
                            source_id=source.source_id,
                            source_type=source.source_type,
                            topic_id=topic.topic_id,
                            query_kind=query_kind,
                            query_text=query_text,
                            priority=self.query_kind_priority.index(query_kind) + 1,
                            max_results=self.limits.default_max_results,
                            live_network_enabled=False,
                            generated_from="default_topic_profile_v1",
                            dedup_key=dedup_key,
                        )
                        plan.validate()
                        plans.append(plan)
                        seen.add(dedup_key)
                        source_topic_count += 1
                    if source_topic_count >= topic_cap:
                        break

        return plans

    def _active_topics(self, topic_profiles: Iterable[TopicProfile]) -> List[TopicProfile]:
        active_topics: List[TopicProfile] = []
        seen: Set[str] = set()
        for topic in topic_profiles:
            topic.validate()
            if topic.topic_id in seen:
                raise ValueError(f"Duplicate topic_id: {topic.topic_id}")
            seen.add(topic.topic_id)
            if topic.active:
                active_topics.append(topic)
        return active_topics

    def _eligible_sources_for_topic(
        self,
        *,
        sources_by_id: Dict[str, SourceConfig],
        topic: TopicProfile,
    ) -> List[SourceConfig]:
        eligible: List[SourceConfig] = []
        for source_id in topic.allowed_source_ids:
            source = sources_by_id.get(source_id)
            if source is None:
                raise ValueError(f"TopicProfile {topic.topic_id} references undefined source_id: {source_id}")
            if not self._source_can_plan_for_topic(source=source, topic=topic):
                continue
            eligible.append(source)
        return sorted(eligible, key=lambda item: item.source_id)

    def _source_can_plan_for_topic(self, *, source: SourceConfig, topic: TopicProfile) -> bool:
        if not source.enabled:
            return False
        if not source.collector_available:
            return False
        if source.commercial_review_required:
            return False
        if not source.access_realistic_for_solo_founder:
            return False
        if topic.topic_id not in source.topic_ids:
            return False
        return True

    def _ordered_query_kinds(self, *, topic: TopicProfile, source: SourceConfig) -> List[str]:
        supported = set(source.supported_query_kinds)
        requested = set(topic.query_kinds)
        ordered = [kind for kind in self.query_kind_priority if kind in supported and kind in requested]
        extra = sorted((supported & requested) - set(ordered))
        return ordered + extra


def build_default_query_plans(registry: SourceRegistry, topic_profiles: Iterable[TopicProfile]) -> List[QueryPlan]:
    return QueryPlanner().build_plans(registry=registry, topic_profiles=topic_profiles)


def build_customer_voice_query_plans(
    *,
    topic_id: str,
    customer_voice_queries: List[CustomerVoiceQuery],
    source_registry: SourceRegistry,
    source_type_filter: Optional[List[str]] = None,
    max_queries_per_persona: Optional[int] = None,
    max_total_queries: Optional[int] = None,
    max_results_per_query: int = 25,
    live_network_enabled: bool = False,
) -> List[QueryPlan]:
    if not isinstance(topic_id, str) or not topic_id.strip():
        raise ValueError("topic_id must be a non-empty string")
    if max_queries_per_persona is not None and max_queries_per_persona < 0:
        raise ValueError("max_queries_per_persona must be non-negative")
    if max_total_queries is not None and max_total_queries < 0:
        raise ValueError("max_total_queries must be non-negative")
    if max_results_per_query <= 0:
        raise ValueError("max_results_per_query must be positive")

    source_registry.validate()
    source_type_filter_set = {item.strip() for item in source_type_filter or [] if item.strip()}
    eligible_sources = _eligible_customer_voice_sources(
        source_registry=source_registry,
        topic_id=topic_id,
        source_type_filter=source_type_filter_set,
    )

    approved_queries = [
        query
        for query in customer_voice_queries
        if query.topic_id == topic_id and query.approval_state == APPROVAL_STATE_APPROVED
    ]
    for query in approved_queries:
        query.validate()

    plans: List[QueryPlan] = []
    emitted_by_persona: Dict[str, int] = {}
    seen: Set[str] = set()

    for query in sorted(approved_queries, key=_customer_voice_query_sort_key):
        if max_queries_per_persona is not None:
            count = emitted_by_persona.get(query.persona_id, 0)
            if count >= max_queries_per_persona:
                continue

        matching_sources = [
            source
            for source in eligible_sources
            if source.source_type in query.expected_source_fit or source.source_id in query.expected_source_fit
        ]

        emitted_for_query = False
        for source in sorted(matching_sources, key=lambda item: (item.source_type, item.source_id)):
            if max_total_queries is not None and len(plans) >= max_total_queries:
                return plans

            dedup_key = make_query_plan_dedup_key(
                source_id=source.source_id,
                topic_id=query.topic_id,
                query_kind=query.query_kind,
                query_text=query.query_text,
            )
            if dedup_key in seen:
                continue

            plan = QueryPlan(
                query_plan_id=make_query_plan_id(
                    source_id=source.source_id,
                    topic_id=query.topic_id,
                    query_kind=query.query_kind,
                    query_text=query.query_text,
                ),
                source_id=source.source_id,
                source_type=source.source_type,
                topic_id=query.topic_id,
                query_kind=query.query_kind,
                query_text=query.query_text,
                priority=query.priority,
                max_results=max_results_per_query,
                live_network_enabled=live_network_enabled,
                generated_from="customer_voice_query_generator_v1",
                dedup_key=dedup_key,
                raw_metadata={
                    "persona_id": query.persona_id,
                    "customer_voice_query_id": query.query_id,
                    "query_intent": query.query_intent,
                    "generation_method": query.generation_method,
                    "approval_state": query.approval_state,
                },
            )
            plan.validate()
            plans.append(plan)
            seen.add(dedup_key)
            emitted_for_query = True

        if emitted_for_query:
            emitted_by_persona[query.persona_id] = emitted_by_persona.get(query.persona_id, 0) + 1

    return plans


def _eligible_customer_voice_sources(
    *,
    source_registry: SourceRegistry,
    topic_id: str,
    source_type_filter: Set[str],
) -> List[SourceConfig]:
    eligible: List[SourceConfig] = []
    for source in source_registry.sources:
        if source_type_filter and source.source_type not in source_type_filter and source.source_id not in source_type_filter:
            continue
        if not source.enabled:
            continue
        if not source.collector_available:
            continue
        if source.commercial_review_required:
            continue
        if not source.access_realistic_for_solo_founder:
            continue
        if topic_id not in source.topic_ids:
            continue
        eligible.append(source)
    return sorted(eligible, key=lambda item: (item.source_type, item.source_id))


def _customer_voice_query_sort_key(query: CustomerVoiceQuery) -> Tuple[str, int, int, str]:
    return (query.topic_id, _customer_voice_persona_sort_priority(query.persona_id), query.priority, query.query_id)


def _customer_voice_persona_sort_priority(persona_id: str) -> int:
    parts = persona_id.split("_")
    if persona_id == "smb_owner":
        return 10
    if persona_id == "bookkeeper":
        return 20
    if persona_id == "accountant":
        return 30
    if persona_id == "fractional_cfo":
        return 40
    if persona_id == "finance_manager":
        return 50
    if persona_id == "operations_manager":
        return 60
    if persona_id == "freelancer_solo_operator":
        return 70
    return 10_000 + len(parts)
