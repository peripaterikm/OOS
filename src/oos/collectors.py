from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Optional

from .collection_scheduler import ScheduledCollectionItem
from .models import RawEvidence, compute_raw_evidence_content_hash


@dataclass(frozen=True)
class CollectionResult:
    scheduled_item: ScheduledCollectionItem
    evidence: List[RawEvidence]
    collector_name: str
    live_network_used: bool = False

    def validate(self) -> None:
        self.scheduled_item.validate()
        if not isinstance(self.collector_name, str) or not self.collector_name.strip():
            raise ValueError("CollectionResult.collector_name must be a non-empty string")
        if not isinstance(self.live_network_used, bool):
            raise ValueError("CollectionResult.live_network_used must be a bool")
        if not isinstance(self.evidence, list):
            raise ValueError("CollectionResult.evidence must be a list")
        for item in self.evidence:
            item.validate()
            if item.source_id != self.scheduled_item.source_id:
                raise ValueError("CollectionResult evidence source_id must match scheduled item")
            if item.topic_id != self.scheduled_item.topic_id:
                raise ValueError("CollectionResult evidence topic_id must match scheduled item")
            if item.query_kind != self.scheduled_item.query_kind:
                raise ValueError("CollectionResult evidence query_kind must match scheduled item")


class BaseCollector(ABC):
    @abstractmethod
    def supports(self, scheduled_item: ScheduledCollectionItem) -> bool:
        raise NotImplementedError

    @abstractmethod
    def collect(self, scheduled_item: ScheduledCollectionItem) -> CollectionResult:
        raise NotImplementedError


class FixtureCollector(BaseCollector):
    def __init__(
        self,
        *,
        source_id: Optional[str] = None,
        source_type: Optional[str] = None,
        evidence_by_dedup_key: Optional[Dict[str, List[RawEvidence]]] = None,
    ):
        self.source_id = source_id
        self.source_type = source_type
        self.evidence_by_dedup_key = evidence_by_dedup_key or {}

    def supports(self, scheduled_item: ScheduledCollectionItem) -> bool:
        scheduled_item.validate()
        if self.source_id is not None and scheduled_item.source_id != self.source_id:
            return False
        if self.source_type is not None and scheduled_item.source_type != self.source_type:
            return False
        return True

    def collect(self, scheduled_item: ScheduledCollectionItem) -> CollectionResult:
        scheduled_item.validate()
        if not self.supports(scheduled_item):
            raise ValueError("FixtureCollector does not support scheduled item source")
        evidence = self._fixture_evidence_for(scheduled_item)
        result = CollectionResult(
            scheduled_item=scheduled_item,
            evidence=evidence,
            collector_name="fixture_collector",
            live_network_used=False,
        )
        result.validate()
        return result

    def _fixture_evidence_for(self, scheduled_item: ScheduledCollectionItem) -> List[RawEvidence]:
        fixture_items = self.evidence_by_dedup_key.get(scheduled_item.dedup_key)
        if fixture_items is None:
            return [self._default_evidence_for(scheduled_item)]
        return [self._align_fixture_evidence(evidence=item, scheduled_item=scheduled_item) for item in fixture_items]

    def _default_evidence_for(self, scheduled_item: ScheduledCollectionItem) -> RawEvidence:
        title = f"Fixture evidence for {scheduled_item.query_kind}"
        body = f"Offline fixture result for query: {scheduled_item.query_text}"
        evidence = RawEvidence(
            evidence_id=f"fixture_{scheduled_item.query_plan_id}_{scheduled_item.scheduled_order}",
            source_id=scheduled_item.source_id,
            source_type=scheduled_item.source_type,
            source_name=scheduled_item.source_id,
            source_url=f"fixture://{scheduled_item.source_id}/{scheduled_item.query_plan_id}",
            collected_at="2026-01-01T00:00:00+00:00",
            title=title,
            body=body,
            language="en",
            topic_id=scheduled_item.topic_id,
            query_kind=scheduled_item.query_kind,
            content_hash=compute_raw_evidence_content_hash(title=title, body=body),
            author_or_context="unverified public commenter",
            raw_metadata={
                "fixture": True,
                "query_plan_id": scheduled_item.query_plan_id,
                "dedup_key": scheduled_item.dedup_key,
            },
            access_policy="offline_fixture",
            collection_method="fixture_collector",
        )
        evidence.validate()
        return evidence

    def _align_fixture_evidence(
        self,
        *,
        evidence: RawEvidence,
        scheduled_item: ScheduledCollectionItem,
    ) -> RawEvidence:
        aligned = replace(
            evidence,
            source_id=scheduled_item.source_id,
            source_type=scheduled_item.source_type,
            topic_id=scheduled_item.topic_id,
            query_kind=scheduled_item.query_kind,
            collection_method="fixture_collector",
        )
        aligned.validate()
        return aligned

MockCollector = FixtureCollector


def collect_with_fixture_collectors(
    scheduled_items: Iterable[ScheduledCollectionItem],
    collectors: Iterable[FixtureCollector],
) -> List[RawEvidence]:
    evidence: List[RawEvidence] = []
    collector_list = list(collectors)
    for scheduled_item in scheduled_items:
        for collector in collector_list:
            if collector.supports(scheduled_item):
                evidence.extend(collector.collect(scheduled_item).evidence)
                break
        else:
            raise ValueError(f"No fixture collector supports source_id={scheduled_item.source_id}")
    return evidence
