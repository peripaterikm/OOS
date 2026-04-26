# OOS Source Intelligence Layer v0.2

**Project:** OOS — Opportunity Operating System  
**Document purpose:** detailed architecture/specification for an autonomous internet signal-mining layer  
**Target reader:** Claude / Codex / technical architect / product strategist  
**Status:** draft v0.2, revised after Claude review and source-priority correction  
**Authoring context:** Roadmap v2.2 is complete. Existing OOS can process structured signals through the meaning loop. This document defines the missing upstream layer: autonomous acquisition of raw market evidence from public internet sources.

---

## 0. Executive summary

OOS must not depend on the founder manually finding and copying discussions into `signals.jsonl`.

The goal of the Source Intelligence Layer is:

```text
public internet sources
→ autonomous collection of raw evidence
→ normalization and classification
→ extraction of pain / workaround / buying-intent signals
→ scoring and deduplication
→ existing OOS meaning loop
→ opportunity cards
→ idea variants
→ critique / shortlist / next experiments
→ founder decision
→ feedback into future collection strategy
```

The founder should define strategic themes, approve source categories, and make final decisions. The system should do the mining.

The revised v0.2 plan changes the previous v0.1 emphasis:

1. Reddit is no longer treated as a normal Phase C source. It is a high-value but commercially/legally gated source requiring an explicit terms/cost decision.
2. Source priority shifts toward lower-friction, higher-signal sources first: HN Algolia, GitHub Issues, Stack Exchange, approved RSS feeds, regulator feeds, and G2 only through official/approved access.
3. Signal scoring must define `measurement_method` for every dimension.
4. Stage 1 evidence classification must prefer false positives over false negatives for HN and GitHub.
5. Query planning must cap query volume and rank query kinds.
6. Feedback scoring must operate at `source_id × topic_id × query_kind`, not only source level.
7. Traceability from final weekly package back to `source_url` must be an explicit acceptance test.

---

## 1. Core thesis

OOS is not a generic “startup idea generator.” It is an autonomous opportunity intelligence system.

The system should discover external evidence first, then derive opportunities and ideas from that evidence.

```text
Raw market evidence is primary.
Ideas are derived artifacts.
Founder decisions are final.
```

Correct flow:

```text
Source Registry
→ Topic Profiles
→ Query Planner
→ Collection Scheduler
→ Collectors
→ Raw Evidence Store
→ Evidence Cleaner
→ Evidence Classifier
→ Signal Candidate Extractor
→ Signal Scoring
→ Existing OOS Meaning Loop
→ Weekly Discovery Package
→ Founder Decision
→ Source Yield Feedback
```

Incorrect flow:

```text
Founder thinks of idea
→ AI writes business plan
→ system pretends it discovered evidence
```

That path is banned. The machine must not launder speculation into evidence.

---

## 2. Existing downstream OOS context

Roadmap v2.2 already verified the full AI meaning loop without live LLM/API calls.

Existing downstream flow:

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

The Source Intelligence Layer sits before this flow and provides structured, traceable signal inputs.

---

## 3. Primary product goal

Build an autonomous weekly discovery system that can answer:

```text
What new market pains appeared or strengthened this week?
Which sources produced real buying-intent or workaround signals?
Which clusters deserve opportunity framing?
Which ideas are evidence-backed rather than hallucinated?
Which experiments should the founder run next?
What should the system search more or less next week?
```

The ideal weekly founder output is not a data dump. It is:

```text
Top evidence-backed opportunities
Top idea variants
Top risks / anti-patterns
Top next experiments
Founder decisions needed
Source yield report
```

---

## 4. Non-goals

The Source Intelligence Layer must not initially attempt to:

1. Scrape arbitrary websites aggressively.
2. Bypass paywalls, authentication, robots restrictions, or platform terms.
3. Store unnecessary personal data.
4. Build a general-purpose search engine.
5. Build enterprise social listening infrastructure.
6. Replace founder judgment.
7. Use live LLM calls in v2.3 unless a future roadmap item explicitly permits it.
8. Treat AI-generated content as evidence unless clearly labeled as synthetic/non-evidence.
9. Use Reddit, LinkedIn, Quora, Telegram, or app-store competitor review scraping without explicit compliance review.

---

## 5. Signal types by source class

Different source types produce different signal classes.

### 5.1 Direct pain — best category

Typical sources:

1. **GitHub Issues**
   - Concrete problems from real product users.
   - Often includes reproduction steps, workaround, missing feature, urgency, and stakeholder context.
   - Strong for B2B SaaS, devtools, data tooling, automation, AI tools.

2. **G2 / Capterra / Trustpilot reviews**
   - Structured complaints about competitors.
   - Often includes rating, pros/cons, company size, role, and category.
   - Must be accessed only through official/approved access paths or compliance-reviewed mechanisms.

3. **App Store / Google Play reviews**
   - Strong for mobile products and consumer/prosumer workflows.
   - Competitive review access is constrained. Official Google Play review API is for apps you own. Apple public RSS is limited and primarily for public feed discovery, not a full competitive review API.

### 5.2 Discussions and questions

1. **Hacker News / Algolia**
   - Ask HN threads are highly valuable.
   - Good for workflows, tools, AI, dev, founder, and B2B product pain.

2. **Stack Overflow / Stack Exchange**
   - Unanswered or repeatedly asked questions are strong unresolved-problem signals.
   - Good for developer workflows, technical adoption blockers, and integration friction.

3. **Quora**
   - Potentially useful but weak API/compliance footing.
   - Treat as Phase D/manual or via explicit approved access only.

### 5.3 Buying intent

1. **Product Hunt**
   - Comments around launches and alternatives.
   - Useful for competitor positioning and “what users expected but did not get.”

2. **Indie Hackers**
   - Founder posts and comments can reveal market pains and willingness-to-pay hints.
   - RSS/API availability must be verified. Unofficial feeds must be disabled by default until approved.

3. **Gumroad / Lemon Squeezy**
   - Product catalogs and public sales pages show what people sell.
   - Actual purchase/order data is accessible only for owned stores/accounts, not general market intelligence.

### 5.4 Regulatory and macro triggers

1. Official regulator feeds/pages:
   - Israel Tax Authority
   - Bank of Israel
   - Israel Corporations Authority
   - EU regulatory feeds where relevant

2. Competitor changelogs:
   - What competitors fix repeatedly often reveals user pain.

3. GDELT:
   - Too noisy for early solo-founder discovery.
   - Phase D / experimental only.

### 5.5 Niche but valuable

1. **LinkedIn**
   - Valuable but do not automate without official API/access approval.

2. **Telegram public channels**
   - Possible through Telegram API/MTProto for public channels, but requires explicit legal/terms review.

3. **Newsletter aggregators / Substack / Beehiiv RSS**
   - Useful for trend and niche intelligence.

---

## 6. Practical source priority

### 6.1 Phase A — no-internet architecture skeleton

Goal: implement contracts, schemas, mock collectors, fixtures, and tests.

Sources:

```text
mock_hn
mock_github_issues
mock_stackexchange
mock_rss
mock_g2_reviews
mock_regulator_feed
```

No live network calls.

### 6.2 Phase B — low-friction, high-signal real collectors

Priority order:

1. HN Algolia collector
2. GitHub Issues collector
3. Stack Exchange questions collector
4. Approved RSS collector
5. Regulator RSS/page-monitor collector
6. G2 collector only if official/approved access is available
7. Indie Hackers RSS/feed only if official or approved public feed exists

Key rule:

```text
Do not build a scraper-first system.
Build API/RSS/approved-source collectors first.
```

### 6.3 Phase C — product and app-review intelligence

Candidates:

1. Product Hunt API collector
2. Apple public RSS collector for app/product discovery
3. App review aggregator adapter after explicit legal check
4. Competitor changelog collector
5. Telegram public-channel collector after explicit terms/legal review

### 6.4 Phase D — expensive / noisy / compliance-sensitive sources

Candidates:

1. Reddit Data API
2. GDELT
3. LinkedIn
4. Quora
5. Google Play competitor reviews through third-party/approved services
6. Broad web search APIs

These require explicit decision records before implementation.

---

## 7. Source Registry

The Source Registry defines what the system is allowed to collect.

File:

```text
config/source_registry.yml
```

Example:

```yaml
sources:
  - id: hn_algolia
    source_type: hacker_news_algolia
    enabled: true
    phase: B
    auth_required: false
    commercial_review_required: false
    terms_review_required: true
    default_priority: 90
    allowed_query_kinds:
      - pain_query
      - workaround_query
      - alternative_query
      - ask_query
    max_queries_per_topic_per_run: 8
    max_items_per_query: 30
    max_items_per_run: 150
    default_classification_floor: needs_human_review

  - id: github_issues
    source_type: github_issues
    enabled: true
    phase: B
    auth_required: optional
    commercial_review_required: false
    terms_review_required: true
    default_priority: 95
    allowed_query_kinds:
      - bug_query
      - feature_request_query
      - workaround_query
      - integration_pain_query
    max_queries_per_topic_per_run: 10
    max_items_per_query: 25
    max_items_per_run: 200
    default_classification_floor: needs_human_review

  - id: stackexchange
    source_type: stackexchange_questions
    enabled: true
    phase: B
    auth_required: false
    commercial_review_required: false
    terms_review_required: true
    default_priority: 80
    allowed_query_kinds:
      - unanswered_question_query
      - repeated_question_query
      - integration_pain_query
    max_queries_per_topic_per_run: 8
    max_items_per_query: 30
    max_items_per_run: 120

  - id: g2_reviews
    source_type: g2_reviews
    enabled: false
    phase: B
    auth_required: likely
    commercial_review_required: true
    terms_review_required: true
    access_mode: official_api_or_approved_only
    default_priority: 85
    notes: "Do not assume public scraping or RSS. Enable only after access/terms decision."

  - id: reddit_data_api
    source_type: reddit
    enabled: false
    phase: D
    auth_required: true
    commercial_review_required: true
    terms_review_required: true
    default_priority: 70
    notes: "High signal potential but explicit cost/terms decision required before implementation."

  - id: gdelt
    source_type: gdelt
    enabled: false
    phase: D
    experimental: true
    default_priority: 20
    notes: "High noise for opportunity intelligence; use only after targeted regulator/news feeds."
```

### 7.1 Required fields

```python
@dataclass(frozen=True)
class SourceConfig:
    id: str
    source_type: str
    enabled: bool
    phase: str
    auth_required: bool | str
    commercial_review_required: bool
    terms_review_required: bool
    default_priority: int
    allowed_query_kinds: list[str]
    max_queries_per_topic_per_run: int
    max_items_per_query: int
    max_items_per_run: int
    default_classification_floor: str | None = None
    access_mode: str | None = None
    experimental: bool = False
    notes: str | None = None
```

---

## 8. Topic Profiles

A Topic Profile defines what the system is hunting for.

File:

```text
config/topic_profiles.yml
```

Example:

```yaml
topics:
  - id: ai_cfo_smb
    title: "AI CFO for small and medium businesses"
    status: active
    founder_relevance: high
    domains:
      - finance
      - smb
      - management_reporting
      - cashflow
      - automation
    target_users:
      - small_business_owner
      - founder
      - finance_manager
      - bookkeeper
      - fractional_cfo
    pain_keywords:
      - cash flow forecast
      - profit is not cash
      - bookkeeping mess
      - management reporting
      - spreadsheet finance
      - invoice reconciliation
      - accounts receivable
      - payment calendar
    workaround_keywords:
      - spreadsheet
      - manual report
      - google sheets
      - zapier
      - virtual assistant
      - accountant sends pdf
    competitor_keywords:
      - quickbooks
      - xero
      - freshbooks
      - liveplan
      - fintopia
    excluded_keywords:
      - personal budgeting
      - enterprise erp
      - crypto trading
    preferred_sources:
      - github_issues
      - hn_algolia
      - stackexchange
      - g2_reviews
      - approved_rss
    query_budget_per_run: 40
```

### 8.1 Topic profile principles

A topic should be narrow enough to produce useful queries.

Bad:

```text
AI tools
```

Good:

```text
AI-assisted management reporting for SMB owners who still run finance in spreadsheets
```

Topic profiles must define:

1. domain
2. target user
3. pain keywords
4. workaround keywords
5. competitor keywords
6. excluded keywords
7. preferred sources
8. query budget
9. founder relevance

---

## 9. Query Planner

The Query Planner converts topic profiles into source-specific query plans.

### 9.1 Core problem

Naive query generation creates a combinatorial explosion:

```text
7 topic keywords × 6 query kinds × 4 sources = 168 queries/week
```

This is banned.

### 9.2 v2.3 strategy

For each `topic_id × source_id`, generate a capped, prioritized query list.

Rules:

1. Maximum 10 queries per `topic_id × source_id` by default.
2. Prioritize query kinds:
   1. `pain_query`
   2. `workaround_query`
   3. `alternative_query`
   4. `feature_request_query`
   5. `unanswered_question_query`
   6. `trend_query`
3. Deduplicate generated queries by normalized query text.
4. Use source-specific syntax.
5. Track query yield over time.
6. Never generate queries solely by full cartesian product.

### 9.3 Query kinds

```python
class QueryKind(str, Enum):
    PAIN_QUERY = "pain_query"
    WORKAROUND_QUERY = "workaround_query"
    ALTERNATIVE_QUERY = "alternative_query"
    FEATURE_REQUEST_QUERY = "feature_request_query"
    BUG_QUERY = "bug_query"
    UNANSWERED_QUESTION_QUERY = "unanswered_question_query"
    INTEGRATION_PAIN_QUERY = "integration_pain_query"
    ASK_QUERY = "ask_query"
    TREND_QUERY = "trend_query"
```

### 9.4 QueryPlan contract

```python
@dataclass(frozen=True)
class QueryPlan:
    query_id: str
    topic_id: str
    source_id: str
    query_kind: str
    query_text: str
    source_specific_params: dict[str, Any]
    priority: int
    max_items: int
    created_at: str
    generated_by: str  # rule_based_v1 | founder_seeded | future_llm_stub
    query_hash: str
```

### 9.5 Query examples

For `ai_cfo_smb`:

HN:

```text
"cash flow forecasting" "spreadsheet"
"Ask HN" "bookkeeping" "small business"
"QuickBooks alternative" "small business"
"profit is not cash" "business"
```

GitHub Issues:

```text
cash flow forecast spreadsheet is:issue
bookkeeping export problem is:issue
quickbooks integration problem is:issue
invoice reconciliation is:issue
```

Stack Exchange:

```text
cash flow forecast spreadsheet unanswered
quickbooks api invoice reconciliation
bookkeeping automation error
```

---

## 10. Collection Scheduler

The Collection Scheduler turns QueryPlans into an execution queue.

Claude review noted that v0.1 mentioned a scheduler but did not define it. v0.2 fixes this.

### 10.1 v2.3 minimal contract

```python
@dataclass(frozen=True)
class CollectionLimits:
    max_total_jobs: int
    max_items_total: int
    max_items_per_source: dict[str, int]
    max_runtime_seconds: int | None
    dry_run: bool = False

@dataclass(frozen=True)
class CollectionJob:
    job_id: str
    query_plan: QueryPlan
    source_config: SourceConfig
    topic_profile_id: str
    scheduled_priority: int
    reason: str

class CollectionScheduler:
    def schedule(
        self,
        query_plans: list[QueryPlan],
        source_configs: dict[str, SourceConfig],
        limits: CollectionLimits,
        yield_history: list[SourceYieldMetric],
    ) -> list[CollectionJob]:
        ...
```

### 10.2 v2.3 implementation

Simple deterministic sort:

```text
priority = source.default_priority
         + topic founder_relevance bonus
         + query_kind bonus
         + historical_yield bonus
         - previous_noise penalty
```

No complex optimization in v2.3.

### 10.3 Required behavior

1. Enforce source and global item limits.
2. Prefer high-yield `source × topic × query_kind` combinations.
3. Keep deterministic ordering.
4. Produce a schedule artifact before running collectors.
5. Support `--dry-run` to preview what would be collected.

---

## 11. Collectors

Collectors fetch raw evidence from approved sources.

Directory:

```text
src/oos/collectors/
  __init__.py
  base.py
  hn_algolia.py
  github_issues.py
  stackexchange.py
  rss.py
  g2_reviews.py
  producthunt.py
  app_store_rss.py
  reddit.py
  mock.py
```

### 11.1 Collector interface

```python
class Collector(Protocol):
    source_type: str

    def collect(self, job: CollectionJob) -> list[RawEvidence]:
        ...
```

### 11.2 Collector result rule

Collectors return `RawEvidence`, never `Signal`.

Why:

```text
RawEvidence is the source-of-truth artifact.
Signal is an interpretation.
```

### 11.3 Collector safety rules

1. Respect rate limits.
2. Use official API/RSS paths where available.
3. Preserve source URLs.
4. Preserve enough context to verify interpretation.
5. Do not store unnecessary personal data.
6. Do not scrape pages behind login.
7. Do not bypass robots or technical restrictions.
8. Do not use credentials unless explicitly configured outside repo.

---

## 12. RawEvidence model

```python
@dataclass(frozen=True)
class RawEvidence:
    evidence_id: str
    source_id: str
    source_type: str
    source_name: str
    source_url: str
    collected_at: str
    topic_ids: list[str]
    query_id: str
    query_kind: str
    title: str | None
    body: str
    body_format: str  # text | markdown | html_stripped | json_summary
    author_or_context: str | None
    language: str | None
    published_at: str | None
    source_metadata: dict[str, Any]
    content_hash: str
    collection_run_id: str
    terms_profile_id: str | None
```

### 12.1 Required RawEvidence fields

Must have:

```text
evidence_id
source_id
source_type
source_url
collected_at
query_id
query_kind
body or title
content_hash
collection_run_id
```

No evidence can enter the signal extractor without these.

### 12.2 Raw evidence storage

```text
artifacts/raw_evidence/<collection_run_id>/<source_id>/<evidence_id>.json
artifacts/raw_evidence/<collection_run_id>/raw_evidence_index.json
```

---

## 13. Evidence Cleaner

v0.1 included vague “remove boilerplate when safe.” Claude correctly flagged this as underdefined.

### 13.1 v2.3 allowed cleaning only

Evidence Cleaner may do only:

1. Normalize whitespace.
2. Normalize URLs.
3. Compute content hash.
4. Detect language with deterministic/simple method or mark `unknown`.
5. Strip obviously empty fields.
6. Preserve original/raw text in metadata if transformation is non-trivial.

### 13.2 v2.3 banned cleaning

Do not do:

1. Boilerplate removal.
2. Aggressive HTML pruning beyond collector-level text extraction.
3. Summarization.
4. LLM rewriting.
5. Removal of context that may contain pain/workaround clues.

Boilerplate stripping is Phase v2.4+ after real corpus analysis.

---

## 14. Evidence Classifier

The Evidence Classifier classifies RawEvidence before signal extraction.

### 14.1 Classification labels

```python
class EvidenceClass(str, Enum):
    DIRECT_PAIN = "direct_pain"
    WORKAROUND = "workaround"
    BUYING_INTENT = "buying_intent"
    COMPETITOR_WEAKNESS = "competitor_weakness"
    FEATURE_REQUEST = "feature_request"
    INTEGRATION_PROBLEM = "integration_problem"
    TREND_TRIGGER = "trend_trigger"
    HIGH_POTENTIAL_DISCUSSION = "high_potential_discussion"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    NOISE = "noise"
```

### 14.2 Critical v2.3 rule: avoid false negatives on HN/GitHub

For `hacker_news_algolia` and `github_issues`, the default fallback must be:

```text
needs_human_review
```

not:

```text
noise
```

Reason:

```text
HN and GitHub contain valuable indirect pain signals. Keyword-only classifiers will miss many of them.
```

### 14.3 Stage 1 classifier method

v2.3 uses deterministic/rule-based heuristics only:

```python
@dataclass(frozen=True)
class EvidenceClassification:
    evidence_id: str
    evidence_class: str
    confidence: float
    matched_rules: list[str]
    classification_floor_applied: bool
    classifier_version: str
```

### 14.4 Classifier rules

Examples:

Direct pain:

```text
"I hate"
"frustrated"
"pain"
"problem with"
"does not work"
"hard to"
"too expensive"
"missing"
"why is there no"
```

Workaround:

```text
"we use a spreadsheet"
"manual process"
"built my own"
"hack"
"workaround"
"zapier + airtable"
"virtual assistant"
```

Buying intent:

```text
"looking for"
"recommend a tool"
"would pay"
"need software"
"any alternative"
"vendor"
"pricing"
```

Feature request:

```text
"feature request"
"please add"
"support for"
"would be nice if"
"missing integration"
```

Trend trigger:

```text
"new regulation"
"compliance requirement"
"law changed"
"API deprecated"
"policy update"
```

### 14.5 Classifier output storage

```text
artifacts/evidence_classifications/<collection_run_id>/<evidence_id>.json
```

---

## 15. Signal Candidate Extractor

The extractor converts classified evidence into structured candidate signals.

### 15.1 Core rule

One RawEvidence item can produce:

```text
0 signals
1 signal
many signals
```

Example:

A single HN thread may contain 20 comments. It can produce multiple signals:

```text
- pain signal
- workaround signal
- buying-intent signal
- competitor weakness signal
```

### 15.2 CandidateSignal model

```python
@dataclass(frozen=True)
class CandidateSignal:
    signal_id: str
    evidence_id: str
    source_id: str
    source_url: str
    topic_ids: list[str]
    signal_type: str
    target_user: str | None
    pain_summary: str | None
    current_workaround: str | None
    buying_intent: str | None
    competitor_or_tool: str | None
    trigger_event: str | None
    quote_or_excerpt: str | None
    inferred_from: list[str]
    confidence: float
    extraction_method: str  # rule_based | llm_stub | founder_manual
    extraction_version: str
    traceability_status: str
    created_at: str
```

### 15.3 Signal types

```python
class SignalType(str, Enum):
    PAIN = "pain"
    WORKAROUND = "workaround"
    BUYING_INTENT = "buying_intent"
    COMPETITOR_WEAKNESS = "competitor_weakness"
    FEATURE_REQUEST = "feature_request"
    INTEGRATION_PROBLEM = "integration_problem"
    REGULATORY_TRIGGER = "regulatory_trigger"
    TREND_TRIGGER = "trend_trigger"
```

---

## 16. Signal scoring with measurement_method

Claude correctly noted that v0.1 listed scoring dimensions without specifying how they are measured.

v0.2 requires every score dimension to declare `measurement_method`.

### 16.1 ScoreDimension model

```python
@dataclass(frozen=True)
class ScoreDimension:
    name: str
    value: float
    weight: float
    measurement_method: str  # rule_based | llm_stub | founder_manual
    evidence: list[str]
    explanation: str
```

### 16.2 v2.3 allowed methods

In v2.3:

```text
Allowed:
- rule_based
- llm_stub
- founder_manual

Banned:
- live_llm
```

Live LLM scoring is v2.4+ only after explicit roadmap approval.

### 16.3 Required scoring dimensions

| Dimension | Meaning | v2.3 measurement_method |
|---|---|---|
| pain_clarity | Is the pain concrete and understandable? | rule_based / llm_stub |
| target_user_clarity | Is a user segment identifiable? | rule_based / llm_stub |
| workaround_presence | Does the evidence show a workaround? | rule_based |
| buying_intent | Is there search/purchase/vendor intent? | rule_based |
| urgency_hint | Is timing/pressure visible? | rule_based / llm_stub |
| frequency_hint | Does this recur in source/thread/query history? | rule_based |
| economic_value_hint | Money/time/risk/compliance value? | llm_stub / founder_manual |
| competitor_weakness | Is an existing tool criticized? | rule_based |
| ai_leverage_hint | Could AI materially improve the workflow? | llm_stub / founder_manual |
| founder_fit | Does it match founder thesis? | founder_manual / rule_based from thesis file |
| evidence_strength | Source quality + content specificity | rule_based |

### 16.4 SignalScore model

```python
@dataclass(frozen=True)
class SignalScore:
    signal_id: str
    total_score: float
    dimensions: list[ScoreDimension]
    score_version: str
    score_method: str  # deterministic_v1 | mixed_stub_v1
    live_llm_used: bool
```

### 16.5 Scoring principle

Do not fake precision.

Bad:

```text
score = 0.837 because the formula says so
```

Good:

```text
score = 0.78
because pain clarity, workaround presence, and buying intent were observed;
founder_fit is stubbed/manual pending; economic value is uncertain.
```

---

## 17. Raw evidence and signal deduplication

Deduplication occurs at two levels.

### 17.1 Evidence deduplication

Before storage:

```text
URL normalization
content_hash
source item id when available
```

If the same item is collected via multiple queries, store once and append query provenance.

### 17.2 Signal deduplication

After extraction:

```text
same pain
same user
same workaround
same source family
```

Use existing OOS dedup/fingerprint logic where possible.

### 17.3 Query deduplication before evidence store

Mandatory:

```text
collector result → normalize URL → check content_hash/source_item_id → store once
```

This prevents query explosions from inflating signal frequency.

---

## 18. Source Yield Analytics

The system must learn where useful evidence comes from.

### 18.1 Critical granularity

Feedback must operate at:

```text
source_id × topic_id × query_kind
```

not only at `source_id`.

Reason:

```text
A source can be excellent for one query kind and useless for another.
```

Example:

```text
HN + ai_cfo_smb + workaround_query = useful
HN + ai_cfo_smb + trend_query = noisy
```

Do not downgrade all HN because one query kind performed badly.

### 18.2 SourceYieldMetric model

```python
@dataclass(frozen=True)
class SourceYieldMetric:
    collection_run_id: str
    source_id: str
    topic_id: str
    query_kind: str
    queries_run: int
    items_collected: int
    duplicate_items: int
    evidence_classified_non_noise: int
    candidate_signals_extracted: int
    high_quality_signals: int
    clusters_created: int
    opportunities_created: int
    ideas_shortlisted: int
    founder_advanced: int
    founder_parked: int
    founder_killed: int
    noise_rate: float
    yield_score: float
```

### 18.3 Yield score formula v2.3

Simple deterministic formula:

```text
yield_score =
  0.20 * non_noise_rate
+ 0.25 * signal_extraction_rate
+ 0.25 * high_quality_signal_rate
+ 0.15 * opportunity_conversion_rate
+ 0.15 * founder_positive_decision_rate
```

Where founder positive decision means:

```text
advance OR park_with_interest OR request_more_evidence
```

### 18.4 Yield feedback rules

Next run:

1. Increase priority for high-yield combinations.
2. Reduce priority for high-noise combinations.
3. Do not disable a source globally unless all topic/query combinations perform badly across multiple runs.
4. Require founder confirmation before disabling a source permanently.

---

## 19. Traceability constraints

Traceability is a hard invariant.

Every final weekly discovery package must preserve this chain:

```text
WeeklyDiscoveryPackage
→ IdeaVariant
→ OpportunityCard
→ Cluster
→ CandidateSignal / CanonicalSignal
→ RawEvidence
→ source_url
```

### 19.1 Acceptance test requirement

Add an explicit acceptance test:

```text
Traceability from weekly_discovery_package to source_url must not break at any link.
```

Suggested test file:

```text
tests/test_source_intelligence_traceability_acceptance.py
```

Test should verify:

1. every shortlisted idea links to an opportunity id;
2. every opportunity links to one or more cluster/signal ids;
3. every signal links to raw evidence id;
4. every raw evidence item has a source_url;
5. no generated idea can enter weekly shortlist without evidence traceability;
6. founder_hunch-only ideas are allowed only if explicitly labeled `unsupported_by_external_evidence`.

---

## 20. Compliance and source policy

### 20.1 Access modes

```python
class AccessMode(str, Enum):
    OFFICIAL_API = "official_api"
    PUBLIC_RSS = "public_rss"
    PUBLIC_PAGE_MONITOR_APPROVED = "public_page_monitor_approved"
    OWN_ACCOUNT_DATA = "own_account_data"
    THIRD_PARTY_PROVIDER_APPROVED = "third_party_provider_approved"
    MANUAL_ONLY = "manual_only"
    DISABLED_PENDING_REVIEW = "disabled_pending_review"
```

### 20.2 Source policy fields

```python
@dataclass(frozen=True)
class SourcePolicy:
    source_id: str
    access_mode: str
    commercial_review_required: bool
    terms_review_required: bool
    stores_personal_data: bool
    allowed_to_store_excerpt: bool
    allowed_to_store_url: bool
    max_excerpt_chars: int | None
    notes: str
```

### 20.3 Reddit policy

Reddit must be marked:

```yaml
commercial_review_required: true
requires_explicit_cost_decision: true
enabled: false
phase: D
```

Rationale:

- high signal potential;
- commercial usage and data API access require explicit review;
- rate limits and usage policy must be monitored;
- not suitable as a first collector dependency.

### 20.4 LinkedIn policy

LinkedIn must be:

```yaml
enabled: false
access_mode: disabled_pending_review
commercial_review_required: true
terms_review_required: true
```

No automation without approved API/access.

### 20.5 G2 / Capterra / Trustpilot policy

These are valuable review sources but must not be treated as free scraping targets.

Allowed only through:

1. official API;
2. partner/export access;
3. approved third-party provider;
4. explicit compliance-reviewed public page monitoring.

Do not assume RSS availability unless verified for the specific target.

### 20.6 App reviews policy

Apple:

- use public iTunes/Apple RSS only where available and sufficient;
- App Store Connect API is relevant to apps you own, not broad competitor intelligence;
- competitor review collection requires explicit legal/access review.

Google Play:

- Google Play Developer Reply to Reviews API is for your own production apps with authorization;
- it is not a general competitor review API;
- third-party or scraping-based competitor review collection requires explicit legal/access review.

### 20.7 Quora policy

No official broad public API assumption.

Default:

```yaml
enabled: false
phase: D
access_mode: manual_only_or_approved_provider
```

### 20.8 Telegram policy

Public Telegram channels may be technically accessible through MTProto/API, but:

```yaml
enabled: false
phase: C_or_D
terms_review_required: true
privacy_review_required: true
```

---

## 21. Weekly discovery CLI

Target command:

```powershell
python -m oos.cli discover-weekly `
  --topic-profile ai_cfo_smb `
  --source-registry config\source_registry.yml `
  --since-days 7 `
  --max-items-total 500 `
  --project-root .
```

### 21.1 Dry run

```powershell
python -m oos.cli discover-weekly `
  --topic-profile ai_cfo_smb `
  --dry-run `
  --project-root .
```

Dry run outputs:

```text
planned queries
scheduled collection jobs
expected item budgets
disabled sources and reasons
```

### 21.2 No-live-LLM default

Default:

```text
--no-live-llm = true
```

Live LLM must require explicit future flag:

```powershell
--allow-live-llm
```

and must be prohibited in v2.3 unless roadmap allows it.

### 21.3 Output artifacts

```text
artifacts/discovery_runs/<run_id>/
  collection_plan.json
  collection_schedule.json
  raw_evidence_index.json
  evidence_classification_summary.json
  candidate_signals.json
  signal_scores.json
  source_yield_report.json
  source_yield_report.md
  weekly_discovery_package/
    index.json
    01_executive_summary.md
    02_source_yield.md
    03_strongest_signals.md
    04_clusters.md
    05_opportunities.md
    06_shortlisted_ideas.md
    07_risks_and_antipatterns.md
    08_next_experiments.md
    09_founder_decisions_needed.md
```

---

## 22. Weekly Discovery Package

### 22.1 Purpose

The package should make founder review fast.

Not:

```text
Here are 500 collected items.
```

But:

```text
Here are the 5 strongest new market pains, 3 opportunities, 5 idea variants, and 3 experiments.
```

### 22.2 Required sections

1. Executive summary
2. Source yield summary
3. Strongest evidence-backed signals
4. New or strengthened clusters
5. Opportunity shortlist
6. Idea shortlist
7. Risks / anti-patterns
8. Next experiments
9. Founder decision queue
10. Traceability appendix

### 22.3 Decision queue

Every item should ask founder to choose:

```text
advance
park
kill
request_more_evidence
change_topic_priority
disable_query_kind
```

### 22.4 Unsupported ideas

If an idea comes from founder hunch or synthetic generation but lacks evidence, it must be labeled:

```text
unsupported_by_external_evidence
```

and cannot be ranked above evidence-backed opportunities unless founder explicitly overrides.

---

## 23. Founder thesis filter

The system should not search for all possible businesses. It should search for ideas matching founder strategy.

File:

```text
config/founder_thesis.yml
```

Example:

```yaml
founder_thesis:
  preferred_business_models:
    - recurring_revenue
    - self_serve_saas
    - ai_assisted_service
    - subscription_intelligence_product
    - marketplace_with_automated_front_office
  avoid:
    - pure_consulting
    - high_founder_time_dependency
    - heavy_regulation_first_step
    - low_willingness_to_pay
    - one_off_services
  advantages:
    - finance_expertise
    - smb_consulting
    - russian_speaking_business_audience
    - israel_context
    - ai_workflow_design
  scoring_weights:
    recurring_revenue_potential: 0.20
    automation_potential: 0.20
    founder_fit: 0.20
    distribution_feasibility: 0.15
    regulatory_simplicity: 0.10
    time_to_mvp: 0.10
    personal_energy: 0.05
```

Founder thesis is used in:

1. topic prioritization;
2. signal scoring;
3. opportunity quality gate;
4. idea comparison;
5. next experiment selection.

---

## 24. Source-specific notes

### 24.1 HN Algolia

Use for:

```text
Ask HN
Show HN
tool complaints
workflow questions
AI/tooling discussions
```

Advantages:

- search API available;
- rich comments/discussions;
- no login for public search;
- high density of founder/dev/tooling pain.

Classifier rule:

```text
classification floor = needs_human_review
```

### 24.2 GitHub Issues

Use for:

```text
bug reports
feature requests
integration friction
workflow gaps
open-source competitor pain
```

Advantages:

- structured issue metadata;
- labels;
- comments;
- concrete technical context;
- strong workaround evidence.

Classifier rule:

```text
classification floor = needs_human_review
```

### 24.3 Stack Exchange

Use for:

```text
unanswered questions
repeated technical blockers
API integration pain
confusing workflows
```

Priority signals:

```text
unanswered + high views
many duplicates
accepted answer absent
recent activity
```

### 24.4 G2 / Capterra / Trustpilot

Use for:

```text
competitor weakness
buyer complaints
pricing pain
missing feature patterns
```

Access:

```text
official/approved only
```

Do not assume RSS.

### 24.5 Product Hunt

Use for:

```text
new product patterns
comments on launches
alternative discussions
feature expectation gaps
```

Limitations:

- more trend/product-positioning than raw pain;
- comments may be promotional;
- useful after pain sources are already running.

### 24.6 Indie Hackers

Use for:

```text
founder pain
product validation stories
monetization discussion
bootstrapper workflow problems
```

Access:

```text
official or approved feed/API only
unofficial feeds disabled by default
```

### 24.7 App Store / Google Play

Use for:

```text
mobile competitor complaints
missing features
UX friction
regional limitations
```

Caution:

```text
Official APIs generally target apps you own, not broad competitor intelligence.
```

### 24.8 Regulator feeds/pages

Use for:

```text
why-now triggers
compliance shifts
new reporting duties
financial/regulatory process changes
```

Better than GDELT for early OOS because signal/noise ratio is higher.

### 24.9 Reddit

Use eventually for:

```text
SMB pain
consumer pain
buying intent
community recommendations
```

But:

```text
Phase D only
requires_commercial_review = true
requires_explicit_cost_decision = true
```

### 24.10 GDELT

Use eventually for:

```text
large-scale macro trend detection
```

But:

```text
experimental = true
phase = D
```

For v2.3, replace with specific regulator/RSS feeds.

---

## 25. Testing strategy

### 25.1 Unit tests

Required:

```text
test_source_registry_loads_and_validates.py
test_topic_profiles_validate.py
test_query_planner_caps_queries.py
test_collection_scheduler_prioritizes_deterministically.py
test_mock_collectors_return_raw_evidence.py
test_evidence_cleaner_preserves_context.py
test_evidence_classifier_floors_hn_github_to_review.py
test_signal_candidate_extractor_preserves_evidence_links.py
test_signal_scoring_measurement_methods.py
test_source_yield_scoring_granularity.py
```

### 25.2 Acceptance tests

Required:

```text
test_source_intelligence_traceability_acceptance.py
test_discovery_weekly_cli_acceptance.py
test_no_live_llm_or_api_calls_without_explicit_flags.py
test_disabled_sources_are_not_collected.py
test_reddit_requires_commercial_review.py
test_gdelt_is_experimental_not_phase_b.py
test_app_review_collectors_do_not_claim_competitor_api_without_policy.py
```

### 25.3 Critical acceptance test: traceability

The most important test:

```text
weekly_discovery_package → idea → opportunity → signal → raw_evidence → source_url
```

must never break.

### 25.4 Test data

Fixtures:

```text
tests/fixtures/source_intelligence/
  hn_algolia_sample.json
  github_issues_sample.json
  stackexchange_sample.json
  rss_sample.xml
  g2_review_sample.json
  regulator_feed_sample.xml
```

---

## 26. Run-report standardization

Every Codex/CLI run must write validation and discovery logs to files.

Directory:

```text
docs/dev_ledger/03_run_reports/
```

or for runtime artifacts:

```text
artifacts/run_reports/
```

Required report fields:

```text
run_id
branch
command
started_at
completed_at
source_registry_version
topic_profiles
queries_planned
collection_jobs_run
items_collected
candidate_signals_extracted
validation_commands
validation_results
known_warnings
no_live_llm_confirmed
no_push_merge_tag_confirmed
```

This prevents the founder from becoming a manual CI server. A noble fate, but no.

---

## 27. Recommended Roadmap v2.3

Theme:

```text
Autonomous Source Intelligence + Weekly Opportunity Discovery
```

### 27.1 Item 1 — Source registry + topic profiles

Goal:

```text
Define what sources and topics OOS is allowed to monitor.
```

Deliverables:

```text
config/source_registry.yml
config/topic_profiles.yml
src/oos/source_registry.py
src/oos/topic_profiles.py
tests for validation
```

Acceptance:

```text
invalid source configs rejected
Reddit disabled pending review
GDELT experimental Phase D
G2 official/approved only
```

### 27.2 Item 2 — Query planner + collection scheduler

Goal:

```text
Generate bounded, prioritized source-specific queries.
```

Acceptance:

```text
max N queries per source/topic
query_kind priority respected
deterministic scheduling
source × topic × query_kind yield history supported
```

### 27.3 Item 3 — Raw evidence schema + mock collectors

Goal:

```text
Store traceable RawEvidence artifacts from mock sources.
```

Acceptance:

```text
RawEvidence includes source_url
content_hash generated
dedup works
mock weekly collection run produces evidence index
```

### 27.4 Item 4 — Evidence cleaner + classifier

Goal:

```text
Classify evidence without losing high-potential HN/GitHub discussions.
```

Acceptance:

```text
no boilerplate stripping
HN/GitHub fallback floor = needs_human_review
classification artifacts written
```

### 27.5 Item 5 — Candidate signal extraction + scoring

Goal:

```text
Extract structured signals and score them with explicit measurement_method.
```

Acceptance:

```text
every score dimension has measurement_method
live_llm_used = false
signal links to evidence_id and source_url
```

### 27.6 Item 6 — First real low-friction collectors

Goal:

```text
Implement HN Algolia + GitHub Issues + Stack Exchange/RSS collectors.
```

Acceptance:

```text
network calls behind explicit collector boundary
rate limits respected
raw evidence stored
no secrets in repo
can run in dry-run/mock mode
```

### 27.7 Item 7 — Weekly discovery CLI

Goal:

```text
One command runs discovery and produces a weekly package.
```

Acceptance:

```text
discover-weekly command
collection plan artifact
source yield report
weekly discovery package
traceability acceptance test passes
```

### 27.8 Item 8 — Source yield feedback loop

Goal:

```text
Adjust future discovery priorities using source × topic × query_kind performance.
```

Acceptance:

```text
yield metrics stored
query priorities updated deterministically
no whole-source downgrades without repeated poor performance
```

### 27.9 Item 9 — Completion checkpoint

Goal:

```text
Close v2.3 with validation evidence and Dev Ledger updates.
```

Acceptance:

```text
full unittest discovery OK
oos-validate OK
verify OK
roadmap updated
Dev Ledger updated
local commit only
no push/merge/tag unless explicitly approved
```

---

## 28. Suggested module layout

```text
src/oos/source_intelligence/
  __init__.py
  models.py
  source_registry.py
  topic_profiles.py
  query_planner.py
  collection_scheduler.py
  collectors/
    __init__.py
    base.py
    mock.py
    hn_algolia.py
    github_issues.py
    stackexchange.py
    rss.py
  evidence_store.py
  evidence_cleaner.py
  evidence_classifier.py
  signal_extractor.py
  signal_scoring.py
  source_yield.py
  weekly_discovery.py
```

CLI additions:

```text
src/oos/cli.py
  discover-weekly
  plan-discovery
  source-yield-status
```

Config:

```text
config/source_registry.yml
config/topic_profiles.yml
config/founder_thesis.yml
```

Artifacts:

```text
artifacts/discovery_runs/
artifacts/raw_evidence/
artifacts/evidence_classifications/
artifacts/candidate_signals/
artifacts/source_yield/
```

---

## 29. Implementation guardrails for Codex

Codex must:

1. Work on one roadmap item at a time.
2. Use Windows-native commands.
3. Avoid WSL/Linux-first assumptions.
4. Run focused tests, then full unittest discovery, then validation scripts.
5. Save validation evidence to run reports.
6. Use targeted `git add`, never `git add .`.
7. Not push, merge, or tag without explicit approval.
8. Not add dependencies without explicit approval.
9. Not make live LLM/API calls unless the item explicitly permits it.
10. Keep all secrets out of repo.

---

## 30. Open questions for Claude / architecture review

1. Should Phase B include G2 if official API access is not immediately available, or should it be moved to Phase C?
2. Should Stack Exchange be prioritized above HN for specific developer-pain discovery?
3. How aggressive should the HN/GitHub `needs_human_review` floor be?
4. Should source yield feedback modify query generation automatically or only suggest changes for founder approval?
5. Which first topic profile should be used for real discovery: `ai_cfo_smb`, `insurance_israel`, `life_management_system`, or `ai_agents_for_smb`?
6. What minimum evidence threshold should be required before an opportunity can enter the founder shortlist?
7. Should app-review intelligence be deferred entirely until an approved third-party provider is selected?
8. Is the `source_id × topic_id × query_kind` feedback granularity sufficient, or should it include `query_template_id` too?
9. Should the system preserve raw excerpts, summaries only, or both, per source policy?
10. What is the safest long-term strategy for Reddit: paid API, no Reddit, or third-party provider?

---

## 31. v0.2 changes based on Claude review

Claude review recommendations incorporated:

1. Reddit marked as commercial/cost/terms gated; moved to Phase D.
2. Every signal scoring dimension now requires `measurement_method`.
3. Evidence classifier adds HN/GitHub fallback floor to `needs_human_review`.
4. Query planner includes max queries per topic/source and query-kind prioritization.
5. Boilerplate removal removed from v2.3.
6. Feedback loop moved from source-level to `source_id × topic_id × query_kind`.
7. GDELT moved to Phase D / experimental.
8. Traceability acceptance test added as hard requirement.
9. App Store Connect / Google Play review APIs clarified as mostly own-app data, not broad competitor intel.
10. CLI topic examples standardized around defined topic profiles.
11. Collection Scheduler contract added.
12. Source priority updated: HN + GitHub + Stack Exchange + approved RSS/regulator feeds first; Reddit later.

---

## 32. Source-specific public references

These are factual anchors for future implementation. Check again before coding real collectors because API policies change.

1. HN Algolia API documentation: https://hn.algolia.com/api
2. GitHub REST API documentation: https://docs.github.com/rest
3. GitHub REST Issues API: https://docs.github.com/rest/issues/issues
4. Stack Exchange API documentation: https://api.stackexchange.com/docs
5. Stack Exchange `/questions` endpoint: https://api.stackexchange.com/docs/questions
6. Product Hunt API v2 documentation: https://api.producthunt.com/v2/docs
7. Product Hunt API rate limits: https://api.producthunt.com/v2/docs/rate_limits/headers
8. Reddit Data API terms: https://redditinc.com/policies/data-api-terms
9. Reddit Data API Wiki / rate limits: https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
10. Apple RSS feed generator: https://rss.marketingtools.apple.com/
11. Apple RSS information: https://www.apple.com/rss/
12. Google Play Developer Reply to Reviews API: https://developers.google.com/android-publisher/reply-to-reviews
13. Google Play Developer API reviews resource: https://developers.google.com/android-publisher/api-ref/rest/v3/reviews
14. G2 API documentation: https://data.g2.com/api/docs
15. Lemon Squeezy API documentation: https://docs.lemonsqueezy.com/api
16. Bank of Israel publications/press releases: https://www.boi.org.il/en/

---

## 33. Final summary

Source Intelligence Layer v0.2 reframes OOS v2.3 around autonomous discovery, not manual founder input.

The next OOS build should implement:

```text
Source Registry
→ Topic Profiles
→ Query Planner
→ Collection Scheduler
→ Mock Collectors
→ Raw Evidence Store
→ Evidence Classifier
→ Candidate Signal Extraction
→ Signal Scoring with measurement methods
→ Source Yield Analytics
→ Weekly Discovery CLI
→ Traceable Founder Package
```

The founder should receive:

```text
what the system found;
why it matters;
where it came from;
how strong the evidence is;
what to test next;
what decision is needed.
```

That is the difference between an idea generator and an opportunity operating system.
