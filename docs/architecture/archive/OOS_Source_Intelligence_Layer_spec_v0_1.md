# OOS Source Intelligence Layer v0.1

**Project:** OOS — Opportunity Operating System  
**Document purpose:** detailed architecture/specification for an autonomous internet signal-mining layer  
**Target reader:** Claude / Codex / technical architect / product strategist  
**Authoring context:** Roadmap v2.2 is complete. Existing OOS can process signals through the meaning loop. This document defines the missing upstream layer: autonomous acquisition of raw market evidence from public internet sources.

---

## 0. Core thesis

The goal of OOS is not to make the founder manually collect business ideas, copy posts, or format JSONL files. The goal is to build an autonomous opportunity intelligence system:

```text
public sources on the internet
→ raw evidence collection
→ evidence normalization
→ pain / workaround / buying-intent signal extraction
→ signal scoring and deduplication
→ clusters
→ opportunity cards
→ idea variants
→ critique / kill / park / advance recommendations
→ founder decision
→ feedback loop into future discovery
```

The new layer is called **Source Intelligence Layer**.

It sits before the existing OOS meaning loop.

Existing OOS v2.2 already has the downstream logic:

```text
raw/evaluation signals
→ dedup / fingerprint / canonicalization
→ signal meaning extraction
→ signal quality scoring
→ semantic clustering
→ contradiction detection / merge candidates
→ opportunity framing
→ opportunity quality gate
→ pattern-guided ideation
→ ideation mode comparison
→ deterministic anti-pattern checks
→ isolated AI council critique
→ FounderReviewPackage v2
→ founder AI-stage ratings
```

The missing capability is autonomous upstream discovery:

```text
Source Registry
→ Query Planner
→ Collectors
→ Raw Evidence Store
→ Evidence Cleaner
→ Evidence Classifier
→ Signal Candidate Extractor
→ Source Yield Analytics
→ Existing OOS Meaning Loop
```

The founder’s role should be strategic, not clerical:

```text
Founder does:
- chooses strategic themes / domains;
- approves source categories;
- reviews opportunity shortlist;
- makes final decisions: advance / park / kill;
- gives feedback on relevance and quality.

Founder does NOT:
- manually read Reddit / HN / reviews every week;
- copy discussions into files;
- format JSONL;
- act as a biological web scraper.
```

---

## 1. Design goals

### 1.1 Product goals

1. **Autonomously discover business opportunity signals** from public internet sources.
2. **Convert noisy internet content into structured evidence artifacts** with traceability.
3. **Extract real market signals**, not generic AI ideas.
4. **Prioritize evidence-backed opportunities** over speculative ideas.
5. **Build a weekly discovery package** for the founder with shortlist, risks, and recommended next actions.
6. **Measure source yield** so the system learns which sources produce useful signals.
7. **Respect source terms, rate limits, privacy, and robots/legal boundaries.**

### 1.2 Engineering goals

1. Preserve the existing OOS architecture: file-based artifacts, deterministic tests, traceability.
2. Avoid live LLM/API calls by default unless explicitly allowed per roadmap item.
3. Implement source collection via clear provider boundaries.
4. Make collectors pluggable.
5. Support mock collectors first, then real collectors.
6. Store raw evidence separately from extracted signals.
7. Ensure every extracted signal references one or more evidence artifacts.
8. Ensure every opportunity / idea remains traceable back to source evidence.
9. Maintain Windows-native compatibility: PowerShell + Python venv + VS Code/Codex.
10. Keep secrets out of repo.

---

## 2. Non-goals

The Source Intelligence Layer should **not** initially attempt to:

1. Scrape arbitrary websites aggressively.
2. Ignore terms of service or robots restrictions.
3. Store personal data unnecessarily.
4. Build a full search engine.
5. Build a social listening platform at enterprise scale.
6. Replace founder judgment.
7. Auto-launch products.
8. Depend on live LLM calls for deterministic test coverage.
9. Use paid APIs as hidden dependencies without explicit approval.
10. Treat AI-generated content as real evidence unless it is clearly marked as such.

---

## 3. Conceptual distinction: evidence vs signal vs opportunity vs idea

This distinction is central.

### 3.1 Raw Evidence

Raw evidence is collected material from a source:

```text
HN thread, Reddit post, GitHub issue, Product Hunt comment, review, RSS article, newsletter post, regulatory update, etc.
```

Raw evidence may contain:

```text
- actual pain;
- noise;
- marketing fluff;
- jokes;
- opinions;
- competitor positioning;
- feature requests;
- weak trend clues;
- duplicates;
- irrelevant content.
```

Raw evidence is **not yet a signal**.

### 3.2 Signal

A signal is a structured interpretation extracted from evidence.

Examples:

```text
Pain signal:
"Small business owners do not understand why accounting profit differs from available cash."

Workaround signal:
"Users build spreadsheets to track cash flow because existing tools are too complex."

Buying-intent signal:
"Several users ask for recommendations for a tool and mention willingness to pay."

Competitor weakness signal:
"Users complain that a specific product is too complex for non-accountants."

Trend/trigger signal:
"A new regulation creates a reporting burden for a specific segment."
```

### 3.3 Opportunity

An opportunity is a market hypothesis formed from a cluster of signals:

```text
For target segment X,
problem Y is frequent/urgent/expensive enough,
current alternatives are insufficient,
and there may be a product wedge Z.
```

### 3.4 Idea

An idea is one possible solution/product/business model for an opportunity.

Bad process:

```text
idea → excitement → build MVP
```

Good OOS process:

```text
evidence → signal → cluster → opportunity → multiple idea variants → critique → experiment → founder decision
```

---

## 4. High-level architecture

```text
+-----------------------------------------------------------+
|                   Source Intelligence Layer               |
+-----------------------------------------------------------+
| 1. Source Registry                                        |
| 2. Topic & Query Planner                                  |
| 3. Collection Scheduler                                   |
| 4. Collectors / Adapters                                  |
|    - HN / Algolia                                         |
|    - RSS                                                  |
|    - GitHub Issues                                        |
|    - Reddit                                               |
|    - Product Hunt                                         |
|    - GDELT / News                                         |
|    - App reviews                                          |
|    - Web search API                                       |
| 5. Raw Evidence Store                                     |
| 6. Evidence Cleaner / Normalizer                          |
| 7. Evidence Classifier                                    |
| 8. Signal Candidate Extractor                             |
| 9. Source Yield Analytics                                 |
+-----------------------------------------------------------+
                         |
                         v
+-----------------------------------------------------------+
|                   Existing OOS Meaning Loop               |
+-----------------------------------------------------------+
| dedup → meaning → scoring → clustering → opportunity      |
| framing → quality gate → ideation → critique → founder    |
| package → founder rating                                  |
+-----------------------------------------------------------+
```

---

## 5. Proposed module layout

```text
src/oos/source_intelligence/
  __init__.py
  models.py
  source_registry.py
  query_planner.py
  collection_scheduler.py
  collectors/
    __init__.py
    base.py
    mock_collector.py
    rss_collector.py
    hn_algolia_collector.py
    github_issues_collector.py
    reddit_collector.py
    producthunt_collector.py
    gdelt_collector.py
    app_reviews_collector.py
    web_search_collector.py
  evidence_store.py
  evidence_cleaner.py
  evidence_classifier.py
  signal_candidate_extractor.py
  source_yield.py
  discovery_run.py
  weekly_discovery_package.py
```

Suggested tests:

```text
tests/test_source_registry.py
tests/test_query_planner.py
tests/test_collectors_base_contract.py
tests/test_mock_collector.py
tests/test_raw_evidence_store.py
tests/test_evidence_cleaner.py
tests/test_signal_candidate_extractor.py
tests/test_source_yield_analytics.py
tests/test_weekly_discovery_cli.py
tests/test_source_intelligence_acceptance.py
```

Suggested config:

```text
config/source_registry.yml
config/topic_profiles.yml
config/query_templates.yml
```

Suggested artifacts:

```text
artifacts/source_intelligence/
artifacts/raw_evidence/
artifacts/evidence_batches/
artifacts/signal_candidates/
artifacts/source_yield_reports/
artifacts/discovery_runs/
```

---

## 6. Data model: SourceConfig

### 6.1 Purpose

`SourceConfig` defines where OOS should look for evidence and under what constraints.

### 6.2 Fields

```python
@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    source_type: str
    display_name: str
    enabled: bool
    auth_required: bool
    allowed_use: str
    topic_tags: list[str]
    query_templates: list[str]
    collection_frequency: str
    max_items_per_run: int
    max_age_days: int
    rate_limit_policy: str
    dedup_policy: str
    language_filter: list[str]
    region_filter: list[str]
    source_quality_prior: float
    compliance_notes: list[str]
```

### 6.3 Example YAML

```yaml
sources:
  - source_id: hn_ai_tools
    source_type: hacker_news_algolia
    display_name: Hacker News AI / Tools Search
    enabled: true
    auth_required: false
    allowed_use: public_api
    topic_tags:
      - ai_agents
      - workflow_automation
      - founder_tools
    query_templates:
      - 'Ask HN {topic}'
      - '{topic} pain point'
      - '{topic} alternative'
      - '{topic} spreadsheet'
    collection_frequency: weekly
    max_items_per_run: 100
    max_age_days: 14
    rate_limit_policy: conservative_public_api
    dedup_policy: url_and_source_native_id
    language_filter: ['en']
    region_filter: []
    source_quality_prior: 0.70
    compliance_notes:
      - Use public API only.
      - Store URL and excerpt/summary; avoid full unnecessary copying.

  - source_id: github_finance_issues
    source_type: github_issues
    display_name: GitHub Issues for finance/data/workflow tools
    enabled: true
    auth_required: optional
    allowed_use: official_api
    topic_tags:
      - finance_tools
      - data_workflows
      - open_source_complaints
    query_templates:
      - 'cash flow forecast is:issue'
      - 'finance dashboard is:issue'
      - 'reconciliation spreadsheet is:issue'
    collection_frequency: weekly
    max_items_per_run: 100
    max_age_days: 90
    rate_limit_policy: github_rest_api
    dedup_policy: repo_issue_id
    language_filter: ['en']
    region_filter: []
    source_quality_prior: 0.75
    compliance_notes:
      - GitHub issues can include bug reports and feature requests.
      - Pull requests may appear through some issue endpoints; filter carefully.
```

---

## 7. Data model: TopicProfile

### 7.1 Purpose

`TopicProfile` defines strategic hunting areas. The founder should configure topics, not manually collect posts.

### 7.2 Fields

```python
@dataclass(frozen=True)
class TopicProfile:
    topic_id: str
    display_name: str
    description: str
    strategic_priority: int
    included_keywords: list[str]
    excluded_keywords: list[str]
    source_ids: list[str]
    target_segments: list[str]
    preferred_business_models: list[str]
    founder_thesis_tags: list[str]
    min_evidence_threshold: float
```

### 7.3 Example YAML

```yaml
topics:
  - topic_id: ai_cfo_smb
    display_name: AI-CFO for small and medium businesses
    description: Find evidence of recurring finance/reporting/cash-flow pains in SMBs.
    strategic_priority: 10
    included_keywords:
      - cash flow
      - management reporting
      - financial dashboard
      - bookkeeping frustration
      - spreadsheet finance
      - profit but no cash
      - fractional CFO
    excluded_keywords:
      - crypto trading
      - personal budgeting only
      - enterprise ERP only
    source_ids:
      - hn_ai_tools
      - github_finance_issues
      - reddit_smallbusiness_finance
      - rss_finance_ops
    target_segments:
      - small business owners
      - immigrant entrepreneurs
      - finance operators
      - fractional CFOs
    preferred_business_models:
      - subscription SaaS
      - AI-assisted workflow automation
      - managed software-enabled service
    founder_thesis_tags:
      - recurring_revenue
      - low_founder_time
      - finance_domain_advantage
      - ai_leverage
    min_evidence_threshold: 0.65
```

---

## 8. Data model: QueryPlan

### 8.1 Purpose

The Query Planner converts topic profiles into source-specific queries.

Example:

```text
Topic: AI-CFO for SMB
Source: HN
Generated queries:
- Ask HN cash flow forecasting tool
- small business financial dashboard spreadsheet
- bookkeeping software frustration
- profit but no cash
```

### 8.2 Fields

```python
@dataclass(frozen=True)
class QueryPlan:
    query_plan_id: str
    topic_id: str
    source_id: str
    generated_at: str
    query_text: str
    query_kind: str
    priority: int
    max_items: int
    since_days: int
    expected_signal_types: list[str]
    negative_keywords: list[str]
```

### 8.3 Query kinds

```text
pain_query:
  Searches for explicit frustration/problem language.

alternative_query:
  Searches for people looking for alternatives.

workaround_query:
  Searches for spreadsheet/manual/Zapier/Airtable/freelancer workarounds.

buying_intent_query:
  Searches for “recommend tool”, “looking for software”, “would pay”.

competitor_weakness_query:
  Searches for complaints about known products.

trend_query:
  Searches for new regulation, new capability, new behavior.
```

---

## 9. Data model: RawEvidence

### 9.1 Purpose

`RawEvidence` is the immutable source-level artifact. It preserves provenance.

### 9.2 Fields

```python
@dataclass(frozen=True)
class RawEvidence:
    evidence_id: str
    source_id: str
    source_type: str
    source_native_id: str | None
    source_url: str | None
    collected_at: str
    published_at: str | None
    query_plan_id: str | None
    topic_id: str
    title: str
    body: str
    body_excerpt: str
    language: str | None
    author_context: str | None
    discussion_context: str | None
    engagement_metrics: dict[str, int | float | str]
    raw_metadata: dict[str, Any]
    content_hash: str
    license_or_terms_note: str | None
```

### 9.3 Evidence ID format

```text
ev_{source_type}_{YYYYMMDD}_{short_hash}
```

Examples:

```text
ev_hn_20260426_8a72fc
ev_github_20260426_19ff02
ev_rss_20260426_ba93e1
```

### 9.4 Storage layout

```text
artifacts/raw_evidence/YYYY-WW/{evidence_id}.json
artifacts/raw_evidence/YYYY-WW/index.json
```

---

## 10. Data model: EvidenceBatch

### 10.1 Purpose

A batch groups evidence collected in one discovery run.

```python
@dataclass(frozen=True)
class EvidenceBatch:
    batch_id: str
    run_id: str
    topic_id: str
    source_id: str
    query_plan_ids: list[str]
    collected_at: str
    evidence_ids: list[str]
    collection_status: str
    errors: list[dict[str, str]]
    rate_limit_observations: dict[str, Any]
```

Storage:

```text
artifacts/evidence_batches/{run_id}/{batch_id}.json
```

---

## 11. Data model: SignalCandidate

### 11.1 Purpose

A signal candidate is extracted from raw evidence before full downstream OOS validation.

### 11.2 Fields

```python
@dataclass(frozen=True)
class SignalCandidate:
    signal_candidate_id: str
    evidence_ids: list[str]
    topic_id: str
    source_id: str
    signal_type: str
    target_user: str | None
    pain_summary: str | None
    current_workaround: str | None
    buying_intent: str | None
    competitor_or_alternative: str | None
    urgency_clues: list[str]
    willingness_to_pay_clues: list[str]
    frequency_clues: list[str]
    market_context: str | None
    raw_quote_or_excerpt: str | None
    extraction_method: str
    confidence: float
    evidence_strength: float
    founder_thesis_tags: list[str]
    risks: list[str]
    traceability: dict[str, Any]
```

### 11.3 Allowed `signal_type`

```text
pain
workaround
buying_intent
competitor_weakness
feature_request
trend_trigger
regulatory_trigger
pricing_complaint
integration_gap
manual_process
language_or_localization_gap
trust_gap
```

---

## 12. Evidence cleaning and normalization

### 12.1 Purpose

Raw internet content is noisy. Cleaning should normalize enough for signal extraction while preserving original evidence.

### 12.2 Cleaning steps

1. Normalize whitespace.
2. Remove boilerplate when safe.
3. Preserve title/body distinction.
4. Detect language.
5. Normalize URLs.
6. Generate content hash.
7. Remove exact duplicates by source-native ID and content hash.
8. Mark low-value content:
   - pure marketing;
   - job posts;
   - memes;
   - unrelated debates;
   - generic AI hype;
   - duplicate reposts.
9. Extract basic metadata:
   - source type;
   - topic;
   - query;
   - date;
   - engagement metrics;
   - author/context if available and allowed.

### 12.3 Non-destructive rule

Cleaning should not overwrite raw evidence. It should create derived artifacts:

```text
raw_evidence → cleaned_evidence
```

---

## 13. Evidence classifier

### 13.1 Purpose

Classify evidence before extracting signals.

### 13.2 Evidence classes

```text
high_potential_discussion:
  Contains multiple user pain points, workarounds, or buying intent.

single_pain_report:
  One user describes a concrete problem.

competitor_review_or_complaint:
  User complains about an existing product.

trend_or_news:
  Useful for “why now” but not direct pain.

product_launch:
  Useful for market map, not necessarily pain.

noise:
  Low value.

needs_human_review:
  Ambiguous or potentially sensitive.
```

### 13.3 Classifier implementation stages

Stage 1 — deterministic baseline:

```text
keyword patterns + source metadata + simple heuristics
```

Stage 2 — stubbed AI provider boundary:

```text
No live calls in tests. Provider interface accepts evidence and returns structured classification.
```

Stage 3 — optional live provider later:

```text
Only if explicitly enabled by config and roadmap item.
```

---

## 14. Signal extraction strategy

### 14.1 Extraction modes

```text
deterministic_baseline:
  Rule-based extraction using patterns.

stubbed_ai:
  Test provider that simulates structured extraction.

live_ai_optional_future:
  Future provider. Disabled by default.
```

### 14.2 Extraction prompt contract for future AI provider

Even before live AI is enabled, the structured contract should exist.

Input:

```json
{
  "evidence_id": "ev_hn_20260426_8a72fc",
  "source_type": "hacker_news_algolia",
  "title": "Ask HN: How do you forecast cash flow?",
  "body_excerpt": "...",
  "topic_profile": {...},
  "allowed_signal_types": ["pain", "workaround", "buying_intent", "competitor_weakness"]
}
```

Output:

```json
{
  "signals": [
    {
      "signal_type": "workaround",
      "target_user": "small business owner",
      "pain_summary": "Cash-flow forecasting is managed manually because existing tools are too complex or disconnected.",
      "current_workaround": "spreadsheet",
      "buying_intent": "looking for recommendations",
      "raw_quote_or_excerpt": "...",
      "confidence": 0.78,
      "evidence_strength": 0.72,
      "risks": ["single-thread evidence", "technical audience bias"]
    }
  ]
}
```

### 14.3 Extraction quality gates

A signal candidate should be rejected or marked weak if:

1. It has no concrete pain or opportunity clue.
2. It is pure solution hype.
3. It has no target user.
4. It is too generic.
5. It is generated by AI without external evidence.
6. It cannot be traced to source evidence.
7. It is a duplicate of an existing signal candidate.

---

## 15. Signal scoring

### 15.1 Purpose

Score signals before sending them into the existing OOS meaning loop.

### 15.2 Proposed score dimensions

```text
evidence_strength:
  How strong is the source evidence?

pain_specificity:
  Is the pain concrete or vague?

frequency_hint:
  Does it appear repeatedly or only once?

urgency_hint:
  Does the user need a solution soon?

money_hint:
  Is there money, risk, loss, or budget?

workaround_strength:
  Are users already using manual tools or paid alternatives?

buying_intent:
  Are users asking for products/recommendations or saying they would pay?

founder_fit:
  Does this match founder thesis?

ai_leverage:
  Is AI meaningfully useful here?

automation_potential:
  Can this become low-founder-time business?

distribution_hint:
  Is there a reachable channel?
```

### 15.3 Formula draft

```text
signal_score =
  0.18 * evidence_strength
+ 0.14 * pain_specificity
+ 0.10 * frequency_hint
+ 0.10 * urgency_hint
+ 0.12 * money_hint
+ 0.10 * workaround_strength
+ 0.10 * buying_intent
+ 0.08 * founder_fit
+ 0.08 * ai_leverage
+ 0.05 * automation_potential
+ 0.05 * distribution_hint
```

This should initially be transparent and deterministic, not magic.

---

## 16. Source yield analytics

### 16.1 Purpose

OOS should learn where good signals come from.

### 16.2 Metrics per source

```python
@dataclass(frozen=True)
class SourceYieldReport:
    source_id: str
    run_id: str
    topic_id: str
    queries_run: int
    items_collected: int
    items_after_dedup: int
    high_potential_evidence_count: int
    signal_candidates_extracted: int
    high_quality_signal_candidates: int
    clusters_created: int
    opportunities_created: int
    ideas_shortlisted: int
    founder_advanced_count: int
    founder_killed_count: int
    noise_ratio: float
    yield_score: float
    notes: list[str]
```

### 16.3 Yield score draft

```text
yield_score =
  high_quality_signal_candidates / max(items_collected, 1)
  adjusted by downstream survival:
    + opportunity_created_bonus
    + founder_advanced_bonus
    - noise_penalty
```

### 16.4 Output example

```markdown
# Source Yield Report — 2026-W18

## Best sources this week

1. GitHub issues — finance/data tools
   - 93 items collected
   - 21 signal candidates
   - 8 high-quality signals
   - 3 opportunity cards
   - yield score: 0.71

2. Hacker News — Ask HN / workflow automation
   - 77 items collected
   - 12 signal candidates
   - 5 high-quality signals
   - 2 opportunity cards
   - yield score: 0.58

## Weak sources this week

1. Product Hunt launches
   - many product descriptions
   - low direct pain signal
   - useful mostly for market map and trend awareness
```

---

## 17. Collector interface

### 17.1 Base contract

```python
class EvidenceCollector(Protocol):
    source_type: str

    def collect(self, plan: QueryPlan, limits: CollectionLimits) -> CollectionResult:
        ...
```

```python
@dataclass(frozen=True)
class CollectionLimits:
    max_items: int
    timeout_seconds: int
    since_days: int
    allow_network: bool
```

```python
@dataclass(frozen=True)
class CollectionResult:
    source_id: str
    query_plan_id: str
    collected_at: str
    evidence: list[RawEvidence]
    errors: list[CollectionError]
    rate_limit_observations: dict[str, Any]
    partial: bool
```

### 17.2 Rules

1. Collectors return `RawEvidence`, not signals.
2. Collectors do not run downstream OOS logic.
3. Collectors must be deterministic under mock mode.
4. Network access must be explicit.
5. Auth tokens must be passed through environment/config, never committed.
6. Collectors should record rate-limit observations.
7. Collectors should not crash the whole run if one source fails.

---

## 18. Recommended source roadmap

### 18.1 Phase A — no-network skeleton

Purpose: architecture and tests.

Implement:

```text
- SourceConfig model
- TopicProfile model
- QueryPlan model
- RawEvidence model
- SignalCandidate model
- source registry loader
- query planner
- mock collector
- raw evidence store
- deterministic evidence classifier
- deterministic signal extractor baseline
- source yield report
```

No real internet calls yet.

### 18.2 Phase B — first real collectors

Start with sources that are technically and legally easier:

1. **Hacker News / Algolia API**
2. **RSS feeds**
3. **GitHub Issues**
4. **GDELT / news trends**

Why these first:

```text
- public APIs / feeds;
- useful for AI/tools/founder/product/technical pain;
- easy to test with recorded fixtures;
- lower legal and operational friction than scraping social platforms.
```

### 18.3 Phase C — constrained high-value sources

1. Reddit API
2. Product Hunt API
3. App reviews through permitted APIs/RSS / App Store Connect where authorized
4. Google Programmable Search or alternative search API

### 18.4 Phase D — advanced sources

1. Telegram exports / channels where legally available
2. LinkedIn only via compliant mechanisms, not scraping
3. Facebook groups only via official/allowed export/API/manual authorization, not scraping
4. Paid data providers if economics justify

---

## 19. Source-specific notes

This section includes current official reference points. The implementation must re-check current docs before using any source in production.

### 19.1 Hacker News / Algolia

Official/public reference:

```text
https://hn.algolia.com/api
```

Use cases:

```text
- Ask HN threads
- Show HN product launches
- comments with pain/workarounds
- developer/founder tool complaints
```

Useful query patterns:

```text
Ask HN {topic}
{topic} alternative
{topic} spreadsheet
{topic} pain point
{topic} workflow
{topic} tool recommendations
```

Risks:

```text
- technical-founder audience bias;
- overrepresentation of developer tools;
- not ideal for mainstream SMB unless query-targeted.
```

### 19.2 GitHub Issues

Official references:

```text
https://docs.github.com/en/rest
https://docs.github.com/rest/issues/issues
```

Use cases:

```text
- bug reports;
- missing feature requests;
- integration gaps;
- workflow friction;
- repeated unresolved issues in open-source tools.
```

Important note:

```text
GitHub issue endpoints may include pull requests in some contexts. Implementation should filter pull requests where needed.
```

Good query targets:

```text
- repositories in finance/data/automation/AI tooling;
- issues labeled enhancement / bug / question;
- repeated phrases like “workaround”, “manual”, “spreadsheet”, “integration”.
```

### 19.3 RSS

Use cases:

```text
- newsletters;
- industry blogs;
- regulatory updates;
- product changelogs;
- competitor blogs;
- public agency updates.
```

Advantages:

```text
- simple;
- stable;
- low friction;
- good for trend and trigger detection.
```

Limitations:

```text
- less direct pain;
- often marketing-heavy;
- requires source curation.
```

### 19.4 Reddit

Official references:

```text
https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
https://redditinc.com/policies/data-api-terms
```

Use cases:

```text
- explicit pain mining;
- buying-intent posts;
- alternative/tool recommendation requests;
- community-specific workflows;
- consumer and SMB frustration.
```

Risks:

```text
- API access and terms must be respected;
- rate limits;
- commercial use constraints;
- noisy data;
- privacy considerations.
```

Reddit should be a Phase C collector, not the first collector, unless the legal/API path is already clear.

### 19.5 Product Hunt

Official references:

```text
https://api.producthunt.com/v2/docs
https://api.producthunt.com/v2/docs/rate_limits/headers
```

Use cases:

```text
- new product launches;
- positioning patterns;
- market map;
- comments;
- repeated product categories;
- competitor discovery.
```

Limitations:

```text
- more supply-side than demand-side;
- may show what builders launch, not what customers need;
- useful as market-trend input, not primary pain evidence.
```

### 19.6 GDELT / news trends

Official references:

```text
https://www.gdeltproject.org/
https://www.gdeltproject.org/data.html
https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
```

Use cases:

```text
- “why now” signals;
- regulation;
- macro trends;
- local market changes;
- emerging topic monitoring.
```

Limitations:

```text
- not direct customer pain;
- needs careful filtering;
- high volume/noise.
```

### 19.7 App Store / app reviews

Official references:

```text
https://developer.apple.com/documentation/appstoreconnectapi/customer-reviews
https://developer.apple.com/app-store/review/guidelines/
```

Use cases:

```text
- competitor weakness;
- missing features;
- pricing complaints;
- UX frustration;
- localization gaps.
```

Important:

```text
Use approved APIs/feeds. Do not scrape Apple sites. Apple’s review guidelines explicitly restrict scraping of Apple sites and permit approved RSS feeds in certain contexts.
```

### 19.8 Web search APIs

Official reference example:

```text
https://developers.google.com/custom-search/v1/overview
```

Use cases:

```text
- general discovery;
- source finding;
- competitor discovery;
- locating public discussions.
```

Caution:

```text
Search APIs can change, be deprecated, or become costly. Treat search as an adapter, not the foundation.
```

---

## 20. Discovery run lifecycle

### 20.1 Command draft

```powershell
python -m oos.cli run-discovery-weekly `
  --topics ai_cfo_smb,insurance_israel,lms_ai_assistant `
  --since-days 7 `
  --max-items-per-source 100 `
  --project-root .
```

### 20.2 Internal lifecycle

```text
1. Load source registry.
2. Load topic profiles.
3. Generate query plans.
4. Schedule source/query pairs.
5. Run collectors.
6. Store raw evidence.
7. Clean / normalize evidence.
8. Classify evidence.
9. Extract signal candidates.
10. Score signal candidates.
11. Send accepted signal candidates into existing OOS signal pipeline.
12. Run dedup / meaning / scoring / clustering / opportunity framing / ideation / critique.
13. Generate weekly discovery package.
14. Generate source yield report.
15. Generate validation/run report.
```

### 20.3 Failure behavior

The run should be resilient:

```text
- One source fails → run continues with other sources.
- API rate limit hit → record partial result and retry later.
- Invalid evidence item → reject item, not full batch.
- Extraction fails → mark evidence as extraction_unavailable.
- Downstream pipeline fails → preserve raw evidence and partial reports.
```

---

## 21. Weekly Discovery Package

### 21.1 Purpose

The founder should receive a concise decision package, not a raw dump.

### 21.2 Folder layout

```text
artifacts/discovery_runs/2026-W18/
  run_manifest.json
  query_plans.json
  raw_evidence_index.json
  evidence_batch_summary.md
  signal_candidates.json
  source_yield_report.md
  discovery_summary.md
  opportunity_shortlist.md
  idea_shortlist.md
  next_experiments.md
  founder_review_package/
    index.json
    01_executive_summary.md
    02_sources_and_yield.md
    03_signal_clusters.md
    04_opportunities.md
    05_idea_variants.md
    06_council_critique.md
    07_recommended_next_actions.md
    08_founder_decision_form.md
```

### 21.3 Executive summary content

```markdown
# Weekly Discovery Summary — 2026-W18

## Main takeaways
- 427 items collected from 5 sources.
- 81 signal candidates extracted.
- 19 high-quality signals passed to the OOS meaning loop.
- 5 clusters created.
- 3 opportunities shortlisted.
- 7 idea variants generated.
- 3 experiments recommended.

## Strongest opportunity
AI-assisted cash-flow explanation cockpit for small business owners who cannot connect accounting profit to actual available cash.

## Recommended founder actions
1. Review Opportunity OPP-2026-W18-001.
2. Approve or kill Experiment EXP-2026-W18-001.
3. Mark whether AI-CFO / SMB finance remains a priority topic next week.
```

---

## 22. Integration with existing OOS artifacts

### 22.1 Mapping from SignalCandidate to existing Signal model

The Source Intelligence Layer should not bypass existing OOS signal validation. It should produce input compatible with the current signal layer.

Mapping:

```text
SignalCandidate.signal_candidate_id → RawSignal.external_id or source_ref
SignalCandidate.pain_summary → raw signal text
SignalCandidate.evidence_ids → source references / metadata
SignalCandidate.evidence_strength → initial evidence score
SignalCandidate.topic_id → tags/context
```

### 22.2 Traceability chain

Required chain:

```text
IdeaVariant
→ OpportunityCard
→ SemanticCluster
→ CanonicalSignal
→ SignalCandidate
→ RawEvidence
→ source_url / source_native_id
```

No downstream artifact should lose the upstream evidence links.

### 22.3 Founder decision feedback

Founder decisions should update:

```text
- opportunity status;
- idea status;
- experiment status;
- source yield analytics;
- topic priority;
- killed-pattern memory.
```

If founder repeatedly kills ideas from a source/topic due to low relevance, the system should reduce the priority of that source/topic combination.

---

## 23. Compliance, privacy, and safety rules

### 23.1 Collection policy

1. Prefer official APIs, RSS feeds, exports, and permitted public endpoints.
2. Do not scrape sites where scraping is prohibited.
3. Respect robots.txt and terms where applicable.
4. Respect rate limits.
5. Store only what is necessary.
6. Preserve URLs and metadata.
7. Avoid storing personal data unless necessary for signal interpretation.
8. Avoid collecting private groups/chats without authorization.
9. Do not bypass paywalls.
10. Do not bypass authentication.

### 23.2 Data minimization

For public discussions, store:

```text
- URL / source reference;
- title;
- short excerpt or summary;
- structured signal;
- engagement metrics;
- source metadata.
```

Avoid storing:

```text
- full personal profiles;
- unnecessary usernames;
- sensitive personal information;
- large copyrighted bodies of text unless allowed.
```

### 23.3 Secret management

No tokens in repo.

Use:

```text
.env.local ignored by git
Windows environment variables
secret manager later
```

Example environment variables:

```text
OOS_REDDIT_CLIENT_ID
OOS_REDDIT_CLIENT_SECRET
OOS_PRODUCTHUNT_TOKEN
OOS_GITHUB_TOKEN
OOS_GOOGLE_SEARCH_API_KEY
```

---

## 24. Determinism and testability

### 24.1 Test strategy

Use three levels:

```text
Level 1 — pure unit tests:
  no network, no filesystem except temp dirs.

Level 2 — fixture tests:
  recorded source responses stored as test fixtures.

Level 3 — optional integration tests:
  live network, disabled by default, explicit flag required.
```

### 24.2 Test fixtures

Suggested fixture layout:

```text
tests/fixtures/source_intelligence/
  hn_algolia_response_cashflow.json
  github_issues_response_finance_dashboard.json
  rss_feed_sample.xml
  reddit_response_smallbusiness.json
  producthunt_response_ai_tools.json
  gdelt_response_ai_regulation.json
```

### 24.3 Live network gate

Live tests should require explicit opt-in:

```powershell
$env:OOS_ALLOW_LIVE_SOURCE_TESTS="1"
```

Default:

```text
No live network calls.
```

### 24.4 Acceptance tests

Acceptance tests should verify:

1. Source registry loads.
2. Query planner generates source-specific query plans.
3. Mock collector returns RawEvidence.
4. RawEvidence is persisted with stable IDs and hashes.
5. SignalCandidate extraction preserves evidence IDs.
6. Source yield report is generated.
7. Downstream OOS pipeline can consume extracted signal candidates.
8. FounderReviewPackage includes source/evidence traceability.
9. No live network calls occur unless explicitly allowed.
10. Roadmap progress tests are progress-tolerant.

---

## 25. CLI design

### 25.1 Discover sources

```powershell
python -m oos.cli source-list --project-root .
```

Output:

```text
Enabled sources:
- hn_ai_tools [hacker_news_algolia]
- github_finance_issues [github_issues]
- rss_finance_ops [rss]
```

### 25.2 Dry-run query planning

```powershell
python -m oos.cli plan-discovery `
  --topics ai_cfo_smb `
  --since-days 7 `
  --project-root .
```

Output artifacts:

```text
artifacts/source_intelligence/query_plans/...
```

### 25.3 Collect raw evidence

```powershell
python -m oos.cli collect-evidence `
  --topics ai_cfo_smb `
  --sources hn_ai_tools,github_finance_issues `
  --since-days 7 `
  --project-root .
```

### 25.4 Extract signal candidates

```powershell
python -m oos.cli extract-signal-candidates `
  --evidence-batch-id batch_2026_W18_ai_cfo `
  --project-root .
```

### 25.5 Run full weekly discovery

```powershell
python -m oos.cli run-discovery-weekly `
  --topics ai_cfo_smb,insurance_israel,lms_ai_assistant `
  --since-days 7 `
  --max-items-per-source 100 `
  --project-root .
```

### 25.6 Show discovery status

```powershell
python -m oos.cli discovery-status --project-root .
```

---

## 26. Founder thesis integration

The system should not search for random opportunities. It should hunt inside the founder thesis.

### 26.1 Founder thesis filters

```text
- recurring revenue potential;
- low founder-time dependency;
- AI leverage;
- small-team feasibility;
- digital / mostly online business;
- scalable information or workflow product;
- possible advantage in finance / Israel / Russian-speaking immigrants / SMB / AI workflows;
- avoid classic consulting unless software-enabled and scalable;
- avoid high-regulation products as first wedge unless compliance is manageable.
```

### 26.2 Founder fit scoring

```text
founder_fit_score =
  domain_advantage
+ distribution_advantage
+ personal_energy
+ ability_to_validate_fast
+ automation_potential
+ recurring_revenue_fit
- founder_bottleneck_risk
- regulatory_complexity
```

### 26.3 Use in discovery

The system should prioritize signals that match founder thesis but should still record out-of-thesis signals if strong. It should label them:

```text
strong_market_signal_but_low_founder_fit
```

This prevents missed opportunities while keeping founder workload sane.

---

## 27. Opportunity search logic

The system should search for opportunity patterns, not just keywords.

### 27.1 Valuable patterns

```text
Repeated pain:
  Same problem appears across independent sources.

Manual workaround:
  Users use spreadsheets, VAs, Zapier, Airtable, Notion, email, screenshots, or custom scripts.

Buying intent:
  Users ask for tools, recommendations, consultants, templates, or say they would pay.

Competitor dissatisfaction:
  Users complain about complexity, price, missing localization, poor UX, lack of integration.

Regulatory trigger:
  New rule creates recurring compliance burden.

Data fragmentation:
  Users manually combine data from several systems.

Trust gap:
  Users need interpretation, not just data.

Localization gap:
  Existing tools do not fit country/language/culture/workflow.

Expert bottleneck:
  Human expert is expensive or hard to access; AI-assisted product may reduce bottleneck.
```

### 27.2 Low-value patterns

```text
Generic AI hype:
  “AI for X” without pain or buyer.

One-off curiosity:
  Interesting but no recurrence or urgency.

Free-user complaint only:
  Users complain but show no willingness to pay.

Enterprise-only complexity:
  Requires long sales and large team.

Heavy regulated core:
  Legal/regulatory burden dominates MVP.

Founder-as-service trap:
  Looks like recurring consulting disguised as product.
```

---

## 28. Scoring opportunities from autonomous evidence

Opportunity score should combine:

```text
signal cluster strength
+ evidence diversity
+ pain intensity
+ buying intent
+ workaround strength
+ buyer clarity
+ channel clarity
+ AI leverage
+ founder fit
+ recurring revenue potential
+ automation potential
- legal/regulatory risk
- founder bottleneck risk
- competition intensity
- data acquisition difficulty
```

### 28.1 Evidence diversity

Evidence diversity is critical.

```text
Weak:
  10 comments in the same thread.

Better:
  3 independent threads from one source.

Strong:
  Same pain appears in Reddit, GitHub, reviews, and HN.

Very strong:
  Same pain appears across sources and users already pay for alternatives/workarounds.
```

---

## 29. Run reports and logs

Every autonomous run must write evidence of what happened.

Suggested layout:

```text
docs/dev_ledger/03_run_reports/source-intelligence-YYYY-WW.md
artifacts/discovery_runs/YYYY-WW/run_log.txt
artifacts/discovery_runs/YYYY-WW/validation_report.md
```

Run report sections:

```markdown
# Source Intelligence Run Report — 2026-W18

## Scope
Topics, sources, time window.

## Collection summary
Items collected, errors, rate limits.

## Signal extraction summary
Candidates, accepted, rejected, weak.

## Source yield
Best/worst sources.

## Downstream results
Clusters, opportunities, idea variants.

## Validation
Commands run and outcomes.

## Known issues
Rate limits, missing auth, noisy sources, failed collectors.

## Safety/compliance
No prohibited scraping, no live LLM calls unless explicitly enabled.
```

---

## 30. Suggested Roadmap v2.3 rewrite

Roadmap v2.3 should focus on autonomous source intelligence, not manual founder input.

### 30.1 Proposed title

```text
Roadmap v2.3 — Autonomous Source Intelligence and Weekly Opportunity Discovery
```

### 30.2 Proposed mini-epics

```text
9.1 Source Registry and Topic Profiles
9.2 Raw Evidence Schema and Evidence Store
9.3 Query Planner and Collection Scheduler
9.4 Collector Interface and Mock Collector
9.5 First Real Collectors: HN Algolia, RSS, GitHub Issues
9.6 Evidence Cleaner and Classifier
9.7 Evidence-to-Signal Candidate Extraction
9.8 Source Yield Analytics
9.9 Discovery Weekly CLI
9.10 Founder Discovery Package with Source Traceability
9.11 Acceptance Hardening and No-Live-Call Boundaries
9.12 Roadmap v2.3 Completion Checkpoint
```

### 30.3 What to postpone to v2.4

```text
- Reddit collector if API/commercial terms need more analysis;
- Product Hunt integration if auth/rate-limit setup takes time;
- App review ingestion beyond approved feeds/APIs;
- live LLM extraction;
- advanced decision memory;
- autonomous experiment outreach;
- paid data sources;
- web UI.
```

---

## 31. Definition of Done for Source Intelligence Layer MVP

The MVP is done when:

1. Founder can configure topics and source registry.
2. System can generate query plans.
3. System can collect evidence from mock sources and at least 2 real public sources.
4. Raw evidence is stored as traceable artifacts.
5. Evidence is cleaned and classified.
6. Signal candidates are extracted and scored.
7. Signal candidates can enter the existing OOS meaning loop.
8. Weekly discovery package is produced.
9. Every opportunity and idea links back to evidence.
10. Source yield report identifies useful and noisy sources.
11. Full tests pass.
12. No live LLM calls are required.
13. No prohibited scraping is introduced.
14. Validation logs are saved automatically.

---

## 32. Claude review request

Please review this architecture as a technical/product advisor.

Focus on:

1. Is the Source Intelligence Layer correctly separated from the existing OOS meaning loop?
2. Are the data models sufficient for traceability from idea back to internet source?
3. Is the source roadmap realistic for a solo founder / tiny team?
4. Which collectors should be implemented first?
5. What legal/compliance risks need to be addressed before implementation?
6. How should evidence scoring be improved?
7. How should we avoid building a noisy content scraper instead of a business-opportunity intelligence system?
8. How should this be converted into a Roadmap v2.3 with numbered mini-epics and acceptance criteria?
9. What should remain deterministic/no-live-call in v2.3, and what can be prepared as provider boundaries for future live AI?
10. What are the biggest architecture risks and simplifications you recommend?

---

## 33. Short final summary

The Source Intelligence Layer turns OOS from a passive signal-processing system into an autonomous opportunity-discovery system.

It should:

```text
- monitor approved public sources;
- collect raw evidence;
- extract structured pain/workaround/buying-intent signals;
- score and deduplicate them;
- feed the existing OOS meaning loop;
- produce weekly founder-ready opportunity packages;
- measure which sources actually produce useful opportunities.
```

The central design rule:

```text
OOS should bring opportunities to the founder — not force the founder to bring raw signals to OOS.
```
