from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable


_WHITESPACE_RE = re.compile(r"\s+")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)", re.IGNORECASE)


@dataclass(frozen=True)
class VendorPromoAssessment:
    is_vendor_promo: bool
    suppressor_confidence: float
    matched_patterns: list[str]
    reason: str
    recommended_classification: str
    suppression_action: str
    scoring_cap: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_PRODUCT_SUBMISSION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("product_submission:mcp_server_submission", "mcp server submission"),
    ("product_submission:hosted_mcp_server", "hosted mcp server"),
    ("product_submission:hosted_server_for_quickbooks", "hosted server for quickbooks"),
    ("product_submission:commercial_license", "license:** commercial"),
    ("product_submission:commercial_type", "type:** mcp server"),
    ("product_submission:submit_marker", "[submit]"),
)

_VENDOR_PROMO_PATTERNS: tuple[tuple[str, str], ...] = (
    ("vendor_promo:free_demo", "free demo"),
    ("vendor_promo:authorized_provider", "authorized"),
    ("vendor_promo:key_advantages", "key advantages"),
    ("vendor_promo:professional_training_support", "professional training support"),
    ("vendor_promo:technical_assistance", "technical assistance"),
    ("vendor_promo:affordable_pricing", "affordable pricing"),
    ("vendor_promo:transform_your_business", "transform your business"),
    ("vendor_promo:discover_efficient_accounting", "discover efficient accounting"),
    ("vendor_promo:all_in_one_solution", "all-in-one solution"),
    ("vendor_promo:simplify_billing", "simplify billing"),
    ("vendor_promo:zoho_books", "zoho books"),
    ("vendor_promo:cloud_on_premise_setup", "cloud and on-premise setup"),
    ("vendor_promo:bookkeeping_expert", "bookkeeping expert"),
    ("vendor_promo:our_services", "our services"),
    ("vendor_promo:contact_us", "contact us"),
    ("vendor_promo:trusted_partner", "trusted partner"),
    ("vendor_promo:smooth_process", "smooth process"),
    ("vendor_promo:accounting_software_for_small_business", "accounting software for small business"),
    ("vendor_promo:accounting_software_for_small_businesses", "accounting software for small businesses"),
    ("vendor_promo:accounting_program", "accounting program"),
)

_GENERIC_ACCOUNTING_COPY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("seo_copy:accurate_records", "financial records remain accurate"),
    ("seo_copy:tax_obligations", "tax obligations"),
    ("seo_copy:gain_visibility", "gain visibility into their operations"),
    ("seo_copy:plan_for_sustainable_growth", "plan for sustainable growth"),
    ("seo_copy:financial_transparency", "financial transparency"),
    ("seo_copy:strategic_reporting", "strategic reporting"),
    ("seo_copy:competitive_business_environment", "competitive business environment"),
    ("seo_copy:traditional_accounting_tools", "traditional accounting tools"),
)

_SEO_LINK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("seo_link:tumblr", "tumblr.com"),
    ("seo_link:nurtureu", "nurtureu.tech"),
    ("seo_link:external_service_page", "bookkeeping-expert"),
)

_GENUINE_USER_REQUEST_PATTERNS: tuple[str, ...] = (
    "describe the problem",
    "describe the solution you'd like",
    "describe alternatives you've considered",
    "current workaround",
    "i would like to be able to",
    "i would like",
    "i want to",
    "we would need",
    "actual behavior",
    "expected behavior",
)


def assess_vendor_promo(
    *,
    title: str = "",
    body: str = "",
    source_type: str = "",
    source_url: str = "",
) -> VendorPromoAssessment:
    text = _normalize(f"{title} {body}")
    source_type = str(source_type or "")
    source_url_text = str(source_url or "").lower()
    matched_patterns = _matched_patterns(text, source_url_text)
    genuine_user_request = any(pattern in text for pattern in _GENUINE_USER_REQUEST_PATTERNS)
    product_listing = any(pattern.startswith("product_submission:") for pattern in matched_patterns)
    generic_copy_hits = sum(1 for pattern in matched_patterns if pattern.startswith("seo_copy:"))
    vendor_hits = sum(1 for pattern in matched_patterns if pattern.startswith("vendor_promo:"))
    seo_link_hits = sum(1 for pattern in matched_patterns if pattern.startswith("seo_link:"))
    markdown_external_links = len(_MARKDOWN_LINK_RE.findall(f"{title} {body}"))

    confidence = 0.0
    confidence += min(0.58, vendor_hits * 0.14)
    confidence += min(0.48, generic_copy_hits * 0.12)
    confidence += min(0.28, seo_link_hits * 0.14)
    confidence += 0.50 if product_listing else 0.0
    confidence += min(0.16, markdown_external_links * 0.04)
    if source_type == "github_issues":
        confidence += 0.10
    if genuine_user_request:
        confidence -= 0.34
    if source_type == "hacker_news_algolia" and not product_listing:
        confidence -= 0.12
    confidence = round(max(0.0, min(0.98, confidence)), 2)

    is_vendor_promo = bool(matched_patterns) and confidence >= 0.55
    if source_type == "hacker_news_algolia" and not product_listing and confidence < 0.75:
        is_vendor_promo = False

    if not is_vendor_promo:
        return VendorPromoAssessment(
            is_vendor_promo=False,
            suppressor_confidence=confidence,
            matched_patterns=matched_patterns,
            reason="No deterministic vendor-promo/SEO suppression threshold met.",
            recommended_classification="unchanged",
            suppression_action="none",
            scoring_cap=0.99,
        )

    if product_listing or confidence >= 0.72:
        action = "classify_as_noise"
        recommended_classification = "noise"
        scoring_cap = 0.12
    else:
        action = "cap_for_review"
        recommended_classification = "needs_human_review"
        scoring_cap = 0.30

    return VendorPromoAssessment(
        is_vendor_promo=True,
        suppressor_confidence=confidence,
        matched_patterns=matched_patterns,
        reason=_reason(matched_patterns, product_listing=product_listing, generic_copy_hits=generic_copy_hits),
        recommended_classification=recommended_classification,
        suppression_action=action,
        scoring_cap=scoring_cap,
    )


def _matched_patterns(text: str, source_url: str) -> list[str]:
    matched: list[str] = []
    for pattern_id, phrase in _all_patterns():
        if phrase in text or phrase in source_url:
            matched.append(pattern_id)
    return sorted(dict.fromkeys(matched))


def _all_patterns() -> Iterable[tuple[str, str]]:
    yield from _PRODUCT_SUBMISSION_PATTERNS
    yield from _VENDOR_PROMO_PATTERNS
    yield from _GENERIC_ACCOUNTING_COPY_PATTERNS
    yield from _SEO_LINK_PATTERNS


def _reason(matched_patterns: list[str], *, product_listing: bool, generic_copy_hits: int) -> str:
    if product_listing:
        return "Product listing/submission markers dominate; treat as vendor promo rather than user pain."
    if generic_copy_hits >= 2:
        return "Generic accounting/SEO copy markers dominate without concrete user-request evidence."
    return "Vendor promotional markers dominate without concrete user-request evidence."


def _normalize(value: str) -> str:
    text = str(value or "").replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    return _WHITESPACE_RE.sub(" ", text.lower()).strip()
