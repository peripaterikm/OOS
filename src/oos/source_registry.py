from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


QUERY_KIND_PRIORITY = [
    "pain_query",
    "workaround_query",
    "buying_intent_query",
    "competitor_weakness_query",
    "trend_trigger_query",
]


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    source_type: str
    display_name: str
    phase: str
    enabled: bool
    topic_ids: List[str]
    supported_query_kinds: List[str]
    access_policy: str
    auth_required: bool
    requires_registered_app_key: bool
    commercial_review_required: bool
    access_realistic_for_solo_founder: bool
    live_network_disabled_by_default: bool
    notes: str = ""
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    enabled_by_default: bool = False
    included_in_standard_discovery_runs: bool = False
    collector_available: bool = True
    active_after_collector_implementation: bool = False
    usage_mode: str = "source_collection"

    def validate(self) -> None:
        for field_name in ("source_id", "source_type", "display_name", "phase", "access_policy"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"SourceConfig.{field_name} must be a non-empty string")
        for field_name in ("topic_ids", "supported_query_kinds"):
            value = getattr(self, field_name)
            if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                raise ValueError(f"SourceConfig.{field_name} must be a list of non-empty strings")
        for field_name in (
            "enabled",
            "auth_required",
            "requires_registered_app_key",
            "commercial_review_required",
            "access_realistic_for_solo_founder",
            "live_network_disabled_by_default",
            "enabled_by_default",
            "included_in_standard_discovery_runs",
            "collector_available",
            "active_after_collector_implementation",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"SourceConfig.{field_name} must be a bool")
        if not isinstance(self.usage_mode, str) or not self.usage_mode.strip():
            raise ValueError("SourceConfig.usage_mode must be a non-empty string")
        if not isinstance(self.raw_metadata, dict):
            raise ValueError("SourceConfig.raw_metadata must be a dict")


@dataclass(frozen=True)
class TopicProfile:
    topic_id: str
    status: str
    topic_keywords: List[str]
    allowed_source_ids: List[str]
    query_kinds: List[str]
    query_templates: Dict[str, List[str]]
    max_queries_per_source_topic: int = 10
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.status == "active"

    def validate(self) -> None:
        if not isinstance(self.topic_id, str) or not self.topic_id.strip():
            raise ValueError("TopicProfile.topic_id must be a non-empty string")
        if self.status not in {"active", "inactive_future", "disabled"}:
            raise ValueError("TopicProfile.status must be active, inactive_future, or disabled")
        for field_name in ("topic_keywords", "allowed_source_ids", "query_kinds"):
            value = getattr(self, field_name)
            if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                raise ValueError(f"TopicProfile.{field_name} must be a list of non-empty strings")
        if not isinstance(self.query_templates, dict):
            raise ValueError("TopicProfile.query_templates must be a dict")
        for query_kind, templates in self.query_templates.items():
            if not isinstance(query_kind, str) or not query_kind.strip():
                raise ValueError("TopicProfile.query_templates keys must be non-empty strings")
            if not isinstance(templates, list) or any(not isinstance(item, str) or not item.strip() for item in templates):
                raise ValueError("TopicProfile.query_templates values must be lists of non-empty strings")
        if not isinstance(self.max_queries_per_source_topic, int) or self.max_queries_per_source_topic <= 0:
            raise ValueError("TopicProfile.max_queries_per_source_topic must be a positive int")
        if not isinstance(self.raw_metadata, dict):
            raise ValueError("TopicProfile.raw_metadata must be a dict")
        if self.active:
            missing_templates = [kind for kind in self.query_kinds if kind not in self.query_templates]
            if missing_templates:
                raise ValueError(f"Active TopicProfile missing query templates: {', '.join(missing_templates)}")


@dataclass(frozen=True)
class SourceRegistry:
    sources: List[SourceConfig]

    def validate(self) -> None:
        seen: set[str] = set()
        for source in self.sources:
            source.validate()
            if source.source_id in seen:
                raise ValueError(f"Duplicate source_id: {source.source_id}")
            seen.add(source.source_id)

    def by_id(self) -> Dict[str, SourceConfig]:
        self.validate()
        return {source.source_id: source for source in self.sources}


def default_source_registry() -> SourceRegistry:
    registry = SourceRegistry(
        sources=[
            SourceConfig(
                source_id="hacker_news_algolia",
                source_type="hacker_news_algolia",
                display_name="Hacker News Algolia",
                phase="Phase B",
                enabled=True,
                topic_ids=["ai_cfo_smb"],
                supported_query_kinds=list(QUERY_KIND_PRIORITY),
                access_policy="public_api_fixture_offline_first",
                auth_required=False,
                requires_registered_app_key=False,
                commercial_review_required=False,
                access_realistic_for_solo_founder=True,
                live_network_disabled_by_default=True,
                enabled_by_default=True,
                included_in_standard_discovery_runs=True,
                collector_available=True,
                active_after_collector_implementation=True,
                notes="Public search adapter; live network remains disabled unless explicitly enabled later.",
            ),
            SourceConfig(
                source_id="github_issues",
                source_type="github_issues",
                display_name="GitHub Issues",
                phase="Phase B",
                enabled=True,
                topic_ids=["ai_cfo_smb"],
                supported_query_kinds=list(QUERY_KIND_PRIORITY),
                access_policy="public_unauthenticated_fixture_offline_first",
                auth_required=False,
                requires_registered_app_key=False,
                commercial_review_required=False,
                access_realistic_for_solo_founder=True,
                live_network_disabled_by_default=True,
                enabled_by_default=True,
                included_in_standard_discovery_runs=True,
                collector_available=True,
                active_after_collector_implementation=True,
                notes="Public issue search only; tests require no tokens or secrets.",
            ),
            SourceConfig(
                source_id="stack_exchange",
                source_type="stack_exchange",
                display_name="Stack Exchange",
                phase="Phase B",
                enabled=True,
                topic_ids=["ai_cfo_smb"],
                supported_query_kinds=["pain_query", "workaround_query", "trend_trigger_query"],
                access_policy="public_api_fixture_offline_first_registered_app_key_for_production",
                auth_required=False,
                requires_registered_app_key=True,
                commercial_review_required=False,
                access_realistic_for_solo_founder=True,
                live_network_disabled_by_default=True,
                enabled_by_default=True,
                included_in_standard_discovery_runs=True,
                collector_available=True,
                active_after_collector_implementation=True,
                notes="Production/high-volume use requires a registered app key; tests do not require a key.",
            ),
            SourceConfig(
                source_id="rss_feeds",
                source_type="rss_feed",
                display_name="RSS / Regulator / Changelog Feeds",
                phase="Phase B",
                enabled=True,
                topic_ids=["ai_cfo_smb"],
                supported_query_kinds=["trend_trigger_query", "competitor_weakness_query"],
                access_policy="public_feed_content_only_no_scraping",
                auth_required=False,
                requires_registered_app_key=False,
                commercial_review_required=False,
                access_realistic_for_solo_founder=True,
                live_network_disabled_by_default=True,
                enabled_by_default=True,
                included_in_standard_discovery_runs=True,
                collector_available=True,
                active_after_collector_implementation=True,
                notes="Feed content only; no scraping outside feed content.",
            ),
            SourceConfig(
                source_id="g2",
                source_type="g2",
                display_name="G2",
                phase="Later / access review",
                enabled=False,
                topic_ids=[],
                supported_query_kinds=[],
                access_policy="disabled_commercial_review_required",
                auth_required=True,
                requires_registered_app_key=False,
                commercial_review_required=True,
                access_realistic_for_solo_founder=False,
                live_network_disabled_by_default=True,
                enabled_by_default=False,
                included_in_standard_discovery_runs=False,
                collector_available=False,
                active_after_collector_implementation=False,
                notes="Disabled for v2.3; no G2 collector.",
            ),
            SourceConfig(
                source_id="reddit",
                source_type="reddit",
                display_name="Reddit",
                phase="Phase C - controlled internal research source",
                enabled=True,
                topic_ids=["ai_cfo_smb"],
                supported_query_kinds=list(QUERY_KIND_PRIORITY),
                access_policy="internal_research_source_productization_review_required",
                auth_required=True,
                requires_registered_app_key=False,
                commercial_review_required=False,
                access_realistic_for_solo_founder=True,
                live_network_disabled_by_default=True,
                enabled_by_default=True,
                included_in_standard_discovery_runs=True,
                collector_available=False,
                active_after_collector_implementation=True,
                usage_mode="internal_research",
                notes=(
                    "High-value default internal research source once collector_available=true; "
                    "external productization requires review."
                ),
                raw_metadata={
                    "status": "high-value default source",
                    "hard_constraints": {
                        "store_usernames_by_default": False,
                        "store_bulk_thread_dumps": False,
                        "third_party_distribution": False,
                        "model_training_on_reddit_content": False,
                        "external_productization_requires_review": True,
                    },
                    "storage_strategy": {
                        "source_url_required": True,
                        "relevant_excerpt_or_summary_required": True,
                        "selected_context_allowed": True,
                        "full_thread_archive_default": False,
                    },
                    "scaling_strategy": {
                        "scale_by_measured_yield": True,
                        "do_not_reduce_signal_quality_for_abstract_caution": True,
                    },
                },
            ),
            SourceConfig(
                source_id="linkedin",
                source_type="linkedin",
                display_name="LinkedIn",
                phase="Out of scope for v2.3",
                enabled=False,
                topic_ids=[],
                supported_query_kinds=[],
                access_policy="disabled_requires_official_legal_api_approval",
                auth_required=True,
                requires_registered_app_key=True,
                commercial_review_required=True,
                access_realistic_for_solo_founder=False,
                live_network_disabled_by_default=True,
                enabled_by_default=False,
                included_in_standard_discovery_runs=False,
                collector_available=False,
                active_after_collector_implementation=False,
                notes="Automation out of scope without official API and legal approval.",
            ),
            SourceConfig(
                source_id="gdelt",
                source_type="gdelt",
                display_name="GDELT",
                phase="Phase D / experimental",
                enabled=False,
                topic_ids=[],
                supported_query_kinds=[],
                access_policy="disabled_experimental_high_noise",
                auth_required=False,
                requires_registered_app_key=False,
                commercial_review_required=False,
                access_realistic_for_solo_founder=True,
                live_network_disabled_by_default=True,
                enabled_by_default=False,
                included_in_standard_discovery_runs=False,
                collector_available=False,
                active_after_collector_implementation=False,
                notes="High noise risk; disabled by default and not a Phase B core source.",
            ),
            SourceConfig(
                source_id="trustpilot",
                source_type="trustpilot",
                display_name="Trustpilot",
                phase="Later / access review",
                enabled=False,
                topic_ids=[],
                supported_query_kinds=[],
                access_policy="disabled_later_access_review",
                auth_required=True,
                requires_registered_app_key=False,
                commercial_review_required=True,
                access_realistic_for_solo_founder=False,
                live_network_disabled_by_default=True,
                enabled_by_default=False,
                included_in_standard_discovery_runs=False,
                collector_available=False,
                active_after_collector_implementation=False,
                notes="Later access-review candidate; not guaranteed free Phase B source.",
            ),
            SourceConfig(
                source_id="capterra",
                source_type="capterra",
                display_name="Capterra",
                phase="Later / access review",
                enabled=False,
                topic_ids=[],
                supported_query_kinds=[],
                access_policy="disabled_later_access_review",
                auth_required=True,
                requires_registered_app_key=False,
                commercial_review_required=True,
                access_realistic_for_solo_founder=False,
                live_network_disabled_by_default=True,
                enabled_by_default=False,
                included_in_standard_discovery_runs=False,
                collector_available=False,
                active_after_collector_implementation=False,
                notes="Later access-review candidate; not guaranteed free Phase B source.",
            ),
        ]
    )
    registry.validate()
    return registry


def default_topic_profiles() -> List[TopicProfile]:
    profiles = [
        TopicProfile(
            topic_id="ai_cfo_smb",
            status="active",
            topic_keywords=[
                "AI CFO",
                "SMB finance",
                "cashflow",
                "management reporting",
                "financial operations",
                "bookkeeping automation",
            ],
            allowed_source_ids=["hacker_news_algolia", "github_issues", "reddit", "stack_exchange", "rss_feeds"],
            query_kinds=list(QUERY_KIND_PRIORITY),
            query_templates={
                "pain_query": [
                    '"cash flow" "small business"',
                    '"bookkeeping" "small business"',
                    '"accounting software" "small business"',
                    '"spreadsheet" "cash flow"',
                    '"invoice" "small business"',
                    '"financial reporting" "small business"',
                ],
                "workaround_query": [
                    '"cash flow" "manual spreadsheet"',
                    '"invoice payment" "spreadsheet"',
                    '"accounting software" "manual"',
                    '"reconciliation" "spreadsheet"',
                ],
                "buying_intent_query": [
                    '"cash flow forecasting"',
                    '"SMB accounting"',
                    '"financial reporting" "small business"',
                ],
                "competitor_weakness_query": [
                    '"QuickBooks" "manual"',
                    '"QuickBooks" "cash flow"',
                    '"Xero" "invoice"',
                    '"Xero" "spreadsheet"',
                ],
                "trend_trigger_query": [
                    '"accounts payable" "small business"',
                    '"accounts receivable" "invoice"',
                ],
            },
            max_queries_per_source_topic=10,
        ),
        TopicProfile(
            topic_id="insurance_israel",
            status="inactive_future",
            topic_keywords=[],
            allowed_source_ids=[],
            query_kinds=[],
            query_templates={},
            raw_metadata={"reason": "future topic stub only"},
        ),
        TopicProfile(
            topic_id="life_management_system",
            status="inactive_future",
            topic_keywords=[],
            allowed_source_ids=[],
            query_kinds=[],
            query_templates={},
            raw_metadata={"reason": "future topic stub only"},
        ),
    ]
    for profile in profiles:
        profile.validate()
    return profiles
