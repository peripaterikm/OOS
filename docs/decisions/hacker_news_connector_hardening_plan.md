# Hacker News Connector Hardening Plan

**Roadmap:** v2.11
**Item:** 4
**Status:** Plan finalized / implementation pending

---

## 1. Context

Hacker News (HN) is one of the two narrow external discovery sources already present in the OOS codebase. The existing collector adapter at [`src/oos/hn_algolia_collector.py`](../../src/oos/hn_algolia_collector.py) was built during v2.3 (item 4.1) and has operated since as a fixture-driven source feeding the signal pipeline via the HN Algolia Search API.

Roadmap v2.11 focuses on hardening source inputs before expanding to new sources. Before adding Product Hunt, pimenov.ai, or any deferred risky source, the existing sources — HN and GitHub Issues — must be assessed for gaps, aligned with the new v2.11 contracts, and brought to a documented, inspectable baseline.

HN should be treated as a **discussion source** per [`source_allowlist_policy.md`](../contracts/source_allowlist_policy.md) Section 7. HN can provide:

- Pain signals ("I spend way too much time on X")
- Workaround signals ("We built a spreadsheet to solve Y")
- Founder/developer complaints about existing tools
- Product-pattern hints from Show HN and Launch HN posts
- Market sentiment from high-comment discussion threads

**This item is planning only.** No implementation, no live API calls, no code modifications. The plan documents what a hardened HN adapter must look like; it does not build one.

---

## 2. Current-State Assessment

### 2.1 Existing HN-Related Code

| Artifact | Path | Status |
|----------|------|--------|
| **HN collector** | [`src/oos/hn_algolia_collector.py`](../../src/oos/hn_algolia_collector.py) | Exists, functional, 179 lines |
| **HN collector tests** | [`tests/test_hn_algolia_collector.py`](../../tests/test_hn_algolia_collector.py) | Exists, 201 lines, 11 test methods |
| **HN fixture data** | Inline in test file (28-line dict) | Single synthetic fixture with 2 hits |
| **Live collection references** | [`src/oos/live_collection.py`](../../src/oos/live_collection.py) | HNAlgoliaCollector registered via factory |
| **Source registry (code)** | [`src/oos/source_registry.py`](../../src/oos/source_registry.py) | HN registered as `hacker_news_algolia`, Phase B, enabled |
| **Source registry (config)** | [`config/source_registry.json`](../../config/source_registry.json) | HN registered as `hacker_news`, status `planned_hardening` |
| **Signal scoring** | [`src/oos/signal_scoring.py`](../../src/oos/signal_scoring.py) | HN base weight 0.72 |
| **Evidence classification** | [`src/oos/evidence_classifier.py`](../../src/oos/evidence_classifier.py) | HN-specific source_type handling |
| **Query planner** | [`src/oos/source_registry.py`](../../src/oos/source_registry.py) | HN queries configured for multiple persona types |
| **Customer voice queries** | [`src/oos/customer_voice_queries.py`](../../src/oos/customer_voice_queries.py) | HN referenced in ~18 query seeds |

### 2.2 What Currently Works

The existing [`HNAlgoliaCollector`](../../src/oos/hn_algolia_collector.py) is a working fixture-mode adapter that:

1. **Converts Algolia hits to [`RawEvidence`](../../src/oos/models.py:77)** — the [`hn_hit_to_raw_evidence`](../../src/oos/hn_algolia_collector.py:19) function maps `objectID`, `title`, `body` (from `story_text`/`comment_text`/`url`), `created_at`, points, comments, tags.
2. **Produces stable `source_url`** — every record gets `https://news.ycombinator.com/item?id={objectID}`. No placeholder URNs.
3. **Preserves metadata safely** — `objectID`, points, num_comments, tags, `original_url`, `author_present` flag.
4. **Uses privacy-safe `author_or_context`** — hardcoded to `"unverified public commenter"`, never exposes raw HN usernames.
5. **Supports fixture and live modes** — fixture payload is injected via `__init__`; live mode requires `allow_live_network=True` and `live_network_enabled` on the scheduled item.
6. **Handles malformed hits gracefully** — missing `objectID` returns `None`, non-dict hits are skipped, empty title/body fall back to `"HN item {objectID}"`.
7. **Respects `max_results`** — stops after emitting the scheduled result count.
8. **No secrets or API keys required** — fixture mode has zero credential requirements.
9. **Tests validate core behaviors** — 11 tests cover fixture conversion, source_url format, metadata preservation, privacy, content_hash determinism, max_results, no-network enforcement, and empty/malformed payloads.

### 2.3 Gaps Relative to v2.11 Contracts

#### 2.3.1 Gaps vs Discovery Source Adapter Contract

| Contract Requirement | Status | Gap Description |
|---------------------|--------|----------------|
| Phase 2: Normalize — explicit, inspectable field mapping | Partial | Mapping is implicit in code; no per-field mapping documentation |
| Phase 3: Validate — content_hash match check | Present | `evidence.validate()` called after construction |
| Phase 4: Deduplicate — within-session dedup | Partial | `seen_ids` set prevents duplicate `evidence_id` in same batch, but no explicit `duplicate_count` reporting |
| Phase 5: Persist — output to artifact store | Absent | Collector returns `CollectionResult` but does not persist artifacts |
| Phase 7: Source Quality Summary | **Absent** | No `source_quality_summary` is produced |
| `evidence_kind` field | **Absent** | `RawEvidence` records do not carry `evidence_kind` classification |
| `source_type` uses `"hacker_news_algolia"` | **Non-standard** | Contract requires `"discussion"` as `source_type`; current code uses `"hacker_news_algolia"` |
| `source_id` mismatch | **Divergence** | Code uses `"hacker_news_algolia"`; config registry uses `"hacker_news"` |
| Explicit `drop_reason` for excluded items | **Absent** | Hits with no `objectID` are silently skipped |
| `canonical_url` field | **Absent** | Not populated when `source_url` differs from `original_url` |
| `tags` / `categories` structured fields | Partial | Present in `raw_metadata["tags"]` but not as top-level `tags` |
| `engagement_metrics` object | Partial | Points/comments in `raw_metadata` but not as structured `engagement_metrics` |
| `created_at` / `updated_at` top-level fields | Partial | `created_at` only in `raw_metadata`, not as a top-level optional field |

#### 2.3.2 Gaps vs Raw Evidence Artifact Schema

| Schema Requirement | Status | Gap Description |
|-------------------|--------|----------------|
| `evidence_kind` (required field) | **Missing** | Schema requires `evidence_kind` on every record |
| `summary` optional field | Absent | Not populated |
| `author` optional field | Absent | Privacy-safe display name not set (only `author_or_context`) |
| `created_at` top-level optional | Absent | Present in `raw_metadata` only |
| `updated_at` top-level optional | Absent | Not populated |
| `tags` top-level optional | Absent | Present in `raw_metadata["tags"]` only |
| `categories` top-level optional | Absent | Not populated |
| `engagement_metrics` top-level optional | Absent | Not populated as structured object |
| `source_specific_id` top-level optional | Absent | `objectID` present only in `raw_metadata` |
| `extraction_notes` | Absent | Not populated |
| `quality_flags` | Absent | Not populated; no `low_text_context` flag for short comments |
| `duplicate_of` | Absent | Not populated |
| `canonical_url` | Absent | Not populated |
| `source_quality_summary` in artifact | **Absent** | Not produced |
| `validation_summary` in artifact | **Absent** | Not produced |

#### 2.3.3 Gaps vs Source Allowlist Policy

| Policy Requirement | Status | Gap Description |
|-------------------|--------|----------------|
| `source_type: "discussion"` | **Divergence** | Code uses `"hacker_news_algolia"` |
| `status: planned_hardening` | Aligned | Config registry says `planned_hardening` |
| `implementation_authorized: false` | **Divergence** | Code exists and runs; registry says not authorized |
| `default_enabled: false` | **Divergence** | Code registry (`source_registry.py`) has HN Phase B, enabled |
| `live_access_allowed: false` | Partial | Live access gated behind `allow_live_network` flag |
| `unit_test_mode: fixture_only` | Aligned | Tests use fixtures only |
| `stable_source_url_required: true` | Satisfied | All records get `https://news.ycombinator.com/item?id={objectID}` |
| `no_placeholder_urls` | Satisfied | No `urn:oos:*` anywhere in HN code |

### 2.4 Summary of Critical Gaps

1. **No source quality summary** — the adapter contract Phase 7 requirement is entirely unaddressed.
2. **`source_type` divergence** — code uses `"hacker_news_algolia"`; contracts and config registry expect `"discussion"`.
3. **`source_id` mismatch** — config registry uses `"hacker_news"`; code uses `"hacker_news_algolia"`. This is a known naming convention difference documented in the registry notes; alignment is a hardening concern.
4. **Missing `evidence_kind`** — every record per the schema must carry `evidence_kind`.
5. **Missing optional fields** — `summary`, `author`, `created_at`, `updated_at`, `tags`, `categories`, `engagement_metrics`, `source_specific_id`, `extraction_notes`, `quality_flags`, `duplicate_of`, `canonical_url` are not populated.
6. **No classification heuristics** — HN items are not classified into evidence kinds.
7. **No noise filters** — low-context comments, flamewars, self-promotion, and off-topic posts pass through unfiltered.
8. **Single minimal fixture** — only 2 synthetic hits; no representative Ask HN, Show HN, Launch HN, comment-only, or high-noise examples.
9. **No deduplication reporting** — duplicates within batch are dropped silently (no `duplicate_count` in a quality summary).
10. **`author_or_context` is a single static string** — all HN items get `"unverified public commenter"`, losing the distinction between story authors, commenters, Ask HN posters, and Show HN makers.

---

## 3. HN Source Categories

HN provides distinct content types, each with different signal potential:

| HN Area | Signal Value | Noise Risk | Priority |
|---------|-------------|------------|----------|
| **Ask HN** | High — users explicitly describe problems, ask for tools, seek advice | Low-to-Medium — some are curiosity/opinion | Primary |
| **Show HN** | Medium-High — founders show products addressing specific problems | Medium — self-promotion, launch theater | Primary |
| **Launch HN** | Medium — YC launches reveal founder-targeted problems | High — promotional, hype-heavy | Secondary |
| **Story posts (high-score)** | Medium — trending topics, market sentiment | High — general interest, not pain-specific | Secondary |
| **Comments on pain-related stories** | Medium-High — users describe workarounds, frustrations | Very High — many are low-context, meta, or tangential | Filtered only |
| **High-comment discussions** | Medium — reveals engagement intensity around topics | High — comment quality varies wildly | Filtered only |
| **Search results for pain/workaround keywords** | High — targeted retrieval of specific pain language | Medium — keyword false positives | Primary (query-driven) |
| **Search results for "looking for tool" / "how do you manage"** | High — explicit buying/need signals | Low — queries are inherently need-expressive | Primary |

### 3.1 Recommended Collection Priority

1. **Pain-keyword search queries** (targeted, deterministic, high signal)
2. **"Ask HN" filtered by recency and score** (explicit problem statements)
3. **"Show HN" filtered by comment substance** (solution-pattern signals)
4. **High-score stories with curated topic filters** (market context)
5. **Comments on high-signal items** (workaround/pain detail)
6. **"Launch HN"** (deferred; needs anti-hype filters first)

---

## 4. Access-Method Options

### 4.1 HN Official Firebase API (`hacker-news.firebaseio.com`)

| Aspect | Assessment |
|--------|-----------|
| **Endpoint** | `https://hacker-news.firebaseio.com/v0/` |
| **Data model** | Item tree: each item has `id`, `type` (story/comment/job/poll/pollopt), `by`, `time`, `title`, `text`, `url`, `score`, `descendants`, `kids` (comment IDs) |
| **Comments access** | Full comment tree reachable via `kids` array; recursive depth traversal required |
| **Search support** | **None.** No search endpoint. Must use Algolia for search. |
| **Rate limits** | Generous; no documented hard limit for reasonable usage |
| **URL stability** | Stable since ~2014; no deprecation announcements |
| **Auth required** | No |
| **Use for** | Fetching individual items by ID, comment trees, item metadata enrichment |
| **Verification needed** | Confirm `kids` array depth behavior; confirm item fetch latency for high-comment threads; document practical rate expectations |

### 4.2 HN Algolia Search API (`hn.algolia.com/api/v1`)

| Aspect | Assessment |
|--------|-----------|
| **Endpoint** | `https://hn.algolia.com/api/v1/search` and `/search_by_date` |
| **Data model** | Hits array with `objectID`, `title`, `story_title`, `story_text`, `comment_text`, `url`, `story_url`, `author`, `points`, `num_comments`, `created_at`, `_tags` |
| **Comments access** | Comments appear as hits when query matches comment text; no tree structure |
| **Search support** | Full-text search with tags filtering (`story`, `comment`, `ask_hn`, `show_hn`, `poll`) |
| **Rate limits** | 10,000 requests per hour per IP (documented) |
| **URL stability** | Stable since ~2014; no deprecation announcements |
| **Auth required** | No |
| **Use for** | Search queries, Ask HN/Show HN filtering, date-range queries |
| **Verification needed** | Confirm rate-limit header presence; test `_tags` filter reliability for `ask_hn`/`show_hn`; confirm `hitsPerPage` max |

### 4.3 Static Fixtures Only

| Aspect | Assessment |
|--------|-----------|
| **Use for** | Unit tests, deterministic validation, CI/CD |
| **Data** | Pre-saved JSON payloads mirroring Algolia/Firebase responses |
| **Network** | None required |
| **Verification needed** | Fixture determinism across runs; fixture representativeness of real data |

### 4.4 Pre-Implementation Verification Checklist

Before any implementation begins, the following must be verified (not by this plan; by the future implementation item):

- [ ] Algolia `_tags` field reliably distinguishes `ask_hn`, `show_hn`, `story`, `comment`
- [ ] Algolia rate-limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`) are present and reliable
- [ ] Firebase API `kids` array provides full comment tree for items up to 500+ comments
- [ ] Firebase `text` field is present for comments (contains the comment body)
- [ ] HN item URL pattern `https://news.ycombinator.com/item?id={id}` is stable for both stories and comments
- [ ] Comment permalink format confirmed (`https://news.ycombinator.com/item?id={comment_id}`)
- [ ] Fixture files can be created from real API responses without PII leakage (usernames mapped to roles)
- [ ] Algolia `search_by_date` endpoint returns results for queries older than 30 days

---

## 5. Proposed Source Registry Alignment

The hardened HN adapter must align with [`config/source_registry.json`](../../config/source_registry.json):

| Field | Current Code Value | Registry Value | Hardened Value |
|-------|-------------------|---------------|----------------|
| `source_id` | `hacker_news_algolia` | `hacker_news` | `hacker_news` |
| `source_type` | `hacker_news_algolia` | `discussion` | `discussion` |
| `status` | (runtime) | `planned_hardening` | `planned_hardening` → `implemented_fixture_only` (after implementation) |
| `implementation_authorized` | (runtime) | `false` | `false` (this plan does not authorize) |
| `default_enabled` | `true` in code registry | `false` | `false` |
| `live_access_allowed` | gated by flag | `false` | `false` |
| `unit_test_mode` | `fixture` | `fixture_only` | `fixture_only` |

### 5.1 `source_id` Naming Decision

The code currently uses `"hacker_news_algolia"` as the `source_id` constant. The config registry uses `"hacker_news"`. This plan recommends:

- The config registry value `"hacker_news"` is the canonical `source_id` for registry purposes.
- The adapter implementation may internally use a different constant name (e.g., `HN_SOURCE_ID = "hacker_news"`) but the `source_id` emitted in every `RawEvidence` record must be `"hacker_news"`.
- `evidence_id` format becomes `raw_hacker_news_{objectID}` (not `raw_hn_{objectID}`).
- All downstream references (signal scoring, evidence classification, customer voice queries, query planner) must be updated to use `"hacker_news"` consistently.

This alignment is an implementation concern for the future hardening item, not this plan.

### 5.2 Registry Field Alignment (Target State After Implementation)

```json
{
  "source_id": "hacker_news",
  "source_type": "discussion",
  "source_name": "Hacker News",
  "status": "implemented_fixture_only",
  "implementation_authorized": true,
  "default_enabled": false,
  "live_access_allowed": false,
  "unit_test_mode": "fixture_only",
  "likely_access_methods": ["hn_algolia_search", "hn_official_api"],
  "stable_source_url_required": true,
  "source_url_policy": "mandatory_external_url",
  "risk_level": "medium",
  "notes": "hardened per v2.11 item 4 plan; fixture-only until controlled smoke passes"
}
```

**This target state is not authorized by this plan. It is noted here for the future implementation item.**

---

## 6. Raw Evidence Mapping

### 6.1 HN Item → RawEvidence Field Mapping

| RawEvidence Field | Required | Source from HN Algolia | Fallback / Notes |
|------------------|----------|----------------------|------------------|
| `evidence_id` | Yes | `"raw_hacker_news_{objectID}"` | Stable per item |
| `source_id` | Yes | `"hacker_news"` | Adapter constant |
| `source_type` | Yes | `"discussion"` | Per source category |
| `source_name` | Yes | `"Hacker News"` | Human-readable constant |
| `source_url` | Yes | `"https://news.ycombinator.com/item?id={objectID}"` | Stable canonical URL |
| `collected_at` | Yes | ISO 8601 of fetch time | Fixture mode: fixed timestamp |
| `title` | Yes | `hit.title` or `hit.story_title` | Fallback: `"HN item {objectID}"` |
| `body` | Yes | `hit.story_text` or `hit.comment_text` or `hit.url` | Fallback: title if all empty |
| `language` | Yes | `"en"` (default) | HN is English-dominant; detect if needed |
| `topic_id` | Yes | From `scheduled_item.topic_id` | — |
| `query_kind` | Yes | From `scheduled_item.query_kind` | — |
| `content_hash` | Yes | SHA-256 of `normalize_raw_evidence_content(title, body)` | Deterministic |
| `author_or_context` | Yes | Role label (see 6.2) | Privacy-safe; no usernames |
| `raw_metadata` | Yes | Source-specific metadata dict (see 6.3) | Must be JSON object |
| `access_policy` | Yes | `"public_api_no_auth"` | — |
| `collection_method` | Yes | `"fixture"` / `"live_opt_in"` / `"dry_run"` | Per fetch mode |
| `evidence_kind` | Yes | Classification result (see Section 8) | Must be valid enum |
| `summary` | No | `hit.story_text` truncated to 500 chars, or `null` | Marked in extraction_notes |
| `author` | No | Privacy-safe display name (see 6.2) | `null` if username cannot be safely displayed |
| `created_at` | No | `hit.created_at` (ISO 8601) | `null` if missing |
| `updated_at` | No | `null` | HN items don't have update timestamps |
| `tags` | No | `hit._tags` filtered to topic tags | Exclude `author_*`, `comment_*` |
| `categories` | No | `null` or derived from tags | `["ask-hn"]`, `["show-hn"]`, etc. |
| `engagement_metrics` | No | `{"points": int, "num_comments": int}` | `null` if both missing |
| `source_specific_id` | No | `hit.objectID` | — |
| `extraction_notes` | No | Notes about truncation, missing fields | `null` if no issues |
| `quality_flags` | No | Quality indicators (see Section 11) | `null` if no flags |
| `duplicate_of` | No | `evidence_id` of canonical record | `null` if not a duplicate |
| `canonical_url` | No | `hit.url` or `hit.story_url` (the external link) | `null` if same as `source_url` or no external URL |

### 6.2 `author` and `author_or_context` Privacy Policy

| HN Item Type | `author_or_context` | `author` |
|-------------|-------------------|---------|
| Story with author | `"story author"` | `null` (no safe public display) |
| Ask HN | `"Ask HN poster"` | `null` |
| Show HN | `"Show HN maker"` | `null` |
| Comment on story | `"HN commenter on: {story_title_truncated}"` | `null` |
| Comment on Ask HN | `"Ask HN respondent"` | `null` |

**Policy:** HN usernames are public pseudonyms but should not be directly stored as `author` without a clear privacy justification. The `author_present` boolean in `raw_metadata` indicates whether the source reports an author. The `author` string field remains `null` by default; the `author_or_context` provides role context without exposing handles.

### 6.3 `raw_metadata` Structure

```json
{
  "objectID": "41712345",
  "parent_id": null,
  "story_id": "41712340",
  "points": 42,
  "num_comments": 15,
  "created_at": "2026-05-10T08:30:00Z",
  "created_at_i": 1715322600,
  "author_present": true,
  "original_url": "https://example.com/article",
  "tags": ["story", "ask_hn", "ai"],
  "type": "story",
  "query_plan_id": "qp_abc123",
  "dedup_key": "dk_def456"
}
```

Additional fields to add during hardening:

| Metadata Field | Purpose |
|---------------|---------|
| `parent_id` | For comments: the parent item ID (story or parent comment) |
| `story_id` | For comments: the root story ID |
| `type` | `story`, `comment`, `ask_hn`, `show_hn`, `launch_hn`, `job` |
| `item_text_length` | Character count of body for quality assessment |

---

## 7. evidence_kind Classification Rules

Every HN raw evidence record must carry an `evidence_kind`. The following deterministic heuristics are proposed. These are **planning heuristics**, not implementation — they will be refined, tested, and calibrated during implementation.

### 7.1 Classification Decision Tree (Proposed)

```
Input: HN hit with title, body, _tags, points, num_comments

1. IF _tags contains "ask_hn":
   → IF body contains pain_keywords:     evidence_kind = "pain_signal_candidate"
   → IF body contains workaround_kw:     evidence_kind = "workaround"
   → IF body contains complaint_kw:      evidence_kind = "complaint"
   → IF body contains feature_request_kw: evidence_kind = "feature_request"
   → ELSE:                               evidence_kind = "unknown"

2. IF _tags contains "show_hn":
   → evidence_kind = "product_launch"

3. IF type is "story" / "launch_hn":
   → IF body contains product_launch_kw: evidence_kind = "product_launch"
   → IF body contains market_trend_kw:   evidence_kind = "market_trend"
   → IF body contains solution_kw:       evidence_kind = "solution_pattern"
   → ELSE:                               evidence_kind = "unknown"

4. IF type is "comment":
   → IF body contains pain_keywords:     evidence_kind = "pain_signal_candidate"
   → IF body contains workaround_kw:     evidence_kind = "workaround"
   → IF body contains complaint_kw:      evidence_kind = "complaint"
   → ELSE:                               evidence_kind = "unknown"

5. DEFAULT: evidence_kind = "unknown"
```

### 7.2 Keyword Sets (Proposed, to be Refined During Implementation)

**pain_keywords:** `"frustrating"`, `"pain"`, `"struggle"`, `"nightmare"`, `"waste of time"`, `"drives me crazy"`, `"so hard to"`, `"impossible to"`, `"hours of"`, `"biggest problem"`, `"hate"`, `"terrible"`, `"broken"`, `"can't"`, `"unusable"`

**workaround_keywords:** `"workaround"`, `"hack"`, `"spreadsheet"`, `"manual process"`, `"duct tape"`, `"jerry-rigged"`, `"makeshift"`, `"temporary solution"`, `"script to"`, `"zapier"`, `"ifttt"`, `"cron job"`

**complaint_keywords:** `"why is"`, `"why does"`, `"should be easier"`, `"too expensive"`, `"overpriced"`, `"not worth"`, `"disappointed"`, `"regret"`, `"wish I hadn't"`

**feature_request_keywords:** `"wish it had"`, `"would be great if"`, `"feature request"`, `"missing"`, `"needs"`, `"should support"`, `"please add"`, `"looking for a tool that"`

**product_launch_keywords:** `"launch"`, `"launched"`, `"announcing"`, `"just shipped"`, `"new product"`, `"introducing"`, `"mvp"`, `"beta"`, `"waitlist"`

**market_trend_keywords:** `"trending"`, `"everyone is"`, `"the future of"`, `"industry shift"`, `"growing"`, `"market is"`, `"adoption"`, `"is eating the world"`

**solution_keywords:** `"built a"`, `"created a"`, `"automated"`, `"replaced"`, `"switched from"`, `"migrated"`, `"using AI to"`

### 7.3 Classification Tiebreakers

1. Longest keyword match wins (prefer specific over generic).
2. If body is under 100 characters, lean toward `"unknown"` (insufficient context).
3. For comments: if `parent_id` is a story tagged `ask_hn`, slightly boost `pain_signal_candidate` / `workaround` / `complaint`.
4. `"unknown"` is the safe default. Adapters set `evidence_kind`; the downstream [`EvidenceClassifier`](../../src/oos/evidence_classifier.py) may reclassify.

---

## 8. source_url Traceability

### 8.1 HN Item URL Format

Every HN item has a canonical URL:

```
https://news.ycombinator.com/item?id={objectID}
```

This URL pattern is stable (unchanged since HN's launch) and works for:
- Stories (including Ask HN, Show HN, Launch HN)
- Comments (each comment has its own item ID)
- Polls and poll options

### 8.2 Comment URL Handling

Comments are HN items with their own `objectID`. A comment's `source_url` is:

```
https://news.ycombinator.com/item?id={comment_objectID}
```

The parent story relationship is preserved in `raw_metadata.story_id` and `raw_metadata.parent_id`.

### 8.3 Fixture URL Policy

- Fixture records must use deterministic, stable URLs.
- **Good:** `"https://news.ycombinator.com/item?id=41712345"` (real HN item ID from fixture data)
- **Good:** `"https://news.ycombinator.com/item?id=1"` (deterministic test ID)
- **Bad:** `"urn:oos:test:fixture:1"` (placeholder, forbidden)
- **Bad:** `"http://example.com/dynamic-{timestamp}"` (non-deterministic)

### 8.4 URL Validation Rules (Per Source URL Traceability Contract)

| Rule | Implementation |
|------|---------------|
| `source_url` must be present | Required field; missing → drop record + report |
| `source_url` must use `http(s)://` | Validate scheme + hostname |
| No `urn:oos:*` placeholders | Never generated by HN adapter |
| Stable, canonical link | Always `https://news.ycombinator.com/item?id={objectID}` |
| Fixture URLs deterministic | Fixed IDs in fixture data |
| Missing `source_url` → validation failure | Record dropped; counted in `missing_url_count` |
| `canonical_url` vs `source_url` | `source_url` = HN item page; `canonical_url` = external link (e.g., `hit.url`) |

---

## 9. Deduplication Plan

### 9.1 `objectID`-Based Dedupe (Primary)

Every HN item has a unique `objectID`. Within a single collection session:

- `evidence_id = "raw_hacker_news_{objectID}"`
- If the same `objectID` appears in multiple query results (e.g., same story returned by different search queries), the first occurrence is kept; subsequent occurrences are dropped.
- The `duplicate_count` in the source quality summary tracks exact duplicates.

### 9.2 Canonical URL Dedupe

When `canonical_url` (the external URL the HN item links to) is the same across different HN items:

- Both records are retained (they are different HN items about the same external resource).
- The later record sets `duplicate_of` to the earlier record's `evidence_id`.
- The `near_duplicate_count` in the quality summary tracks this.

### 9.3 Story/Comment Relationship

- A story and its comments are **different items** (different `objectID`, different `evidence_id`).
- They are **not deduplicated** against each other.
- The relationship is preserved in `raw_metadata.story_id` (on comments) and `raw_metadata.parent_id` (on comments).

### 9.4 Cross-Source Deduplication

- The HN adapter does **not** compare its output against GitHub Issues, Product Hunt, or any other source.
- Cross-source duplication (e.g., a GitHub issue being discussed on HN) is handled downstream in [`CandidateSignalExtractor`](../../src/oos/candidate_signal_extractor.py) or [`signal_dedup.py`](../../src/oos/signal_dedup.py).
- Per the raw evidence schema (Section 15.3): cross-source records are never silently dropped at the raw evidence layer.

### 9.5 No Silent Drops

Per the adapter contract (Section 5.5):
- Every excluded HN hit must be reported with `objectID`, title excerpt, and `drop_reason`.
- Drop reasons must be specific: `"missing_objectID"`, `"duplicate_evidence_id"`, `"empty_title_and_body"`, `"missing_source_url"` (not expected for HN), `"validation_failure"`.
- All drop counts appear in the source quality summary.

---

## 10. Noise and Quality Filters

### 10.1 Proposed Filters

| Filter | Trigger | Action |
|--------|---------|--------|
| **Low-context comment** | Comment body < 100 chars | Set `quality_flags: ["low_text_context"]`; do not drop |
| **Flamewar / meta-discussion** | Title/body matches meta-HN keywords | Set `quality_flags: ["suspected_self_promo"]` or `["requires_manual_review"]`; do not drop |
| **Launch hype / self-promotion** | Show HN or Launch HN with low upvote-to-comment ratio | Set `quality_flags: ["suspected_self_promo"]` |
| **Recurring pain keywords** | Body contains 2+ pain_keywords | Boost priority; set `evidence_kind` more confidently |
| **High-engagement posts** | points ≥ 20 AND num_comments ≥ 10 | Prefer over low-engagement posts |
| **Ask HN by use case** | Ask HN with pain/workaround/need language | Primary signal; high-priority classification |
| **Off-topic / general interest** | Story about politics, sports, entertainment | Set `quality_flags: ["high_noise_source"]`; do not drop but flag |

### 10.2 Meta-Discussion Keywords (Flamewar/Hype Detection)

`"yc"`, `"y combinator"`, `"pg"`, `"dang"`, `"moderation"`, `"flag"`, `"downvote"`, `"why was this flagged"`, `"hacker news is"`, `"hn is"`, `"this site"`, `"community"`, `"guidelines"`

### 10.3 Off-Topic Domain Keywords

`"politics"`, `"election"`, `"trump"`, `"biden"`, `"congress"`, `"senate"`, `"climate"`, `"global warming"`, `"spacex"`, `"tesla"`, `"bitcoin"`, `"crypto"`, `"nft"`, `"sports"`, `"football"`, `"basketball"`, `"movie"`, `"netflix"`, `"tv show"`

### 10.4 Filtering Policy

1. **Filters are advisory, not blocking.** Records with quality flags are retained in `records`.
2. **No silent drops.** Every record that triggers a filter is included with flags; filtering decisions happen downstream.
3. **Quality flag provenance.** Every flag set must have a traceable reason (the matching keyword or heuristic).
4. **Records dropped for validation failures** (missing `objectID`, empty title+body) are excluded from `records` and counted in `records_rejected`. These are the only allowed silent-adjacent drops, and they must still be reported in the quality summary.

---

## 11. Query / Collection Strategy

### 11.1 Phased Approach

| Phase | Scope | Fetch Mode | Authorization |
|-------|-------|-----------|---------------|
| **Phase 1: Fixture-only** | Pre-saved JSON payloads; all tests pass | `fixture` | This plan recommends it; implementation requires separate authorization |
| **Phase 2: Curated query set** | Hardcoded set of high-signal queries against fixtures (not live) | `fixture` | Separate authorization |
| **Phase 3: Allowlisted HN sections** | Ask HN, Show HN filtered by date range, in fixture mode | `fixture` | Separate authorization |
| **Phase 4: Live opt-in** | Controlled live smoke with explicit founder approval | `live_opt_in` | Explicit founder approval **only** |
| **Phase 5: Default weekly run** | Not in v2.11 scope | — | v2.12+ after sustained smoke evidence |

### 11.2 Proposed Query Categories

These queries are **planning proposals only**. They will be tuned during implementation.

#### Pain Queries
- `"pain point" OR "frustrating" OR "drives me crazy"`
- `"spend way too much time" OR "hours of my life"`
- `"nightmare" OR "impossible to"`
- `"biggest problem with" OR "hate about"`

#### Workaround Queries
- `"workaround" OR "hack" OR "duct tape"`
- `"spreadsheet" OR "manual process" OR "still using excel"`
- `"script to automate" OR "cron job to"`

#### Need/Buying Intent Queries
- `"looking for a tool" OR "recommend a tool" OR "any tool that"`
- `"how do you manage" OR "how do you handle" OR "how do you deal with"`
- `"too expensive" OR "overpriced" OR "not worth the money"`
- `"wish there was" OR "someone should build" OR "why isn't there"`

#### AI / Automation / DevTools / Finance Ops (OOS-Relevant Verticals)
- `"automate" AND ("invoicing" OR "bookkeeping" OR "reporting")`
- `"AI" AND ("operations" OR "workflow" OR "finance")`
- `("small business" OR "smb" OR "freelancer") AND ("finance" OR "accounting" OR "cash flow")`
- `"devtools" AND ("frustration" OR "pain" OR "alternatives")`
- `("ci/cd" OR "deployment" OR "infrastructure") AND ("pain" OR "problem" OR "broken")`

### 11.3 Query Configuration

- Queries are configured in the source registry or a query configuration file (not hardcoded in the adapter).
- Each query has a `query_kind` (e.g., `"pain_query"`, `"workaround_query"`).
- The query planner (existing) generates `ScheduledCollectionItem` entries.
- The adapter receives `query_text` and `query_kind` via `ScheduledCollectionItem`.

---

## 12. Validation Plan

### 12.1 Required Tests (Future Implementation Item)

| # | Test Case | What It Validates |
|---|-----------|-------------------|
| T1 | Fixture loads without error | Adapter can read and parse fixture JSON payloads |
| T2 | Every output record has a stable `source_url` | `https://news.ycombinator.com/item?id={objectID}`; no placeholders |
| T3 | `source_url` format matches expected pattern | `http(s)://` scheme, valid hostname `news.ycombinator.com` |
| T4 | No `urn:oos:*` placeholders anywhere | Zero tolerance per traceability contract |
| T5 | `content_hash` matches normalized content | `validate()` passes on all records |
| T6 | `author_or_context` is privacy-safe | No username/handle leakage |
| T7 | `evidence_id` follows `raw_hacker_news_{objectID}` | Stable ID pattern |
| T8 | Duplicate `evidence_id` items deduplicated within batch | `duplicate_count` reported |
| T9 | Missing `objectID` produces warning and drop | Item excluded; reported in quality summary |
| T10 | Empty title AND body produces warning and drop | Item excluded; reported in quality summary |
| T11 | Fixture file not found produces error | Error surfaced in quality summary |
| T12 | Malformed fixture produces error | Error surfaced; no partial output |
| T13 | All required `RawEvidence` fields populated | Validation passes for every output record |
| T14 | `source_quality_summary` is produced | All counts and metadata present |
| T15 | `evidence_kind` is set for every record | Must be valid enum value; `"unknown"` is acceptable |
| T16 | Classification heuristics match expected results | Given a known Ask HN pain post, gets `"pain_signal_candidate"` |
| T17 | Noise flags set correctly | Low-context comments get `"low_text_context"` |
| T18 | `engagement_metrics` populated when available | Points and num_comments in structured object |
| T19 | `canonical_url` populated when different from `source_url` | External link from `hit.url` |
| T20 | Comment `story_id` / `parent_id` preserved | Relationship chain in `raw_metadata` |

### 12.2 Failure Case Tests

| # | Failure Scenario | Expected Behavior |
|---|-----------------|-------------------|
| F1 | Fixture file not found | Error in quality summary; no records emitted |
| F2 | Fixture file with invalid JSON | Error in quality summary; no records emitted |
| F3 | Fixture with item missing `objectID` | Warning; item dropped; `records_rejected` incremented |
| F4 | Fixture with item having `objectID=""` | Warning; item dropped |
| F5 | Fixture with item having empty title AND empty body | Warning; item dropped |
| F6 | Fixture with duplicate `objectID` entries | First kept; duplicate dropped; `duplicate_count = 1` |
| F7 | Fixture with `_tags` missing | No crash; classification defaults to `"unknown"` |
| F8 | Live mode (mocked): API returning 5xx after retries | Error; quality summary reports failure |
| F9 | Live mode (mocked): API returning 429 with `Retry-After` | Warning; delay honored; retry attempted |
| F10 | Live mode (mocked): empty hits array | No records; quality summary reports 0 records_seen |

### 12.3 No Live API in Unit Tests

All tests in T1–T20 and F1–F10 must use `fixture` mode or mocked responses. Zero live network calls in the default test suite. The existing pattern (inject `fixture_payload` via constructor) is correct and should be preserved.

---

## 13. Controlled Smoke Plan

### 13.1 Smoke Phases

| Phase | Description | Authorization |
|-------|-------------|---------------|
| **Smoke 1: Fixture validation** | Load all HN fixtures; validate every record; verify quality summary | No live calls; can run in CI |
| **Smoke 2: Dry-run** | Run the adapter in `dry_run` mode; verify configuration loading | No live calls; can run in CI |
| **Smoke 3: Live smoke** | Run against live HN Algolia API with limited queries | Explicit founder approval required |
| **Smoke 4: Live smoke with Firebase API** | Enrich items with comment trees from Firebase | Explicit founder approval; deferred |

### 13.2 Smoke 1: Fixture Validation (Always Allowed)

1. Load all HN fixture files.
2. Run the adapter in `fixture` mode for each fixture.
3. Validate:
   - Every `RawEvidence` record passes `.validate()`.
   - Every `source_url` is `https://news.ycombinator.com/item?id={objectID}`.
   - Zero `urn:oos:*` placeholders.
   - `content_hash` matches for every record.
   - `source_quality_summary` has correct counts.
   - `evidence_kind` is set on every record.
4. Output: pass/fail per fixture.

### 13.3 Smoke 3: Live Smoke (Founder Approval Only)

1. Run a single search query against HN Algolia (`search_by_date`, `hitsPerPage=10`).
2. Validate that all 10 records have:
   - Real `source_url` → real HN item pages.
   - Valid `evidence_id` → `raw_hacker_news_{objectID}`.
   - Non-empty title and body.
   - `evidence_kind` set.
3. Check Algolia rate-limit headers in response.
4. Produce a `source_quality_summary` with live metadata.
5. Record the run in a smoke report artifact.
6. **No default weekly run inclusion until smoke passes at least 3 times.**

### 13.4 Expected Smoke Outputs

| Output | Description |
|--------|-------------|
| `records` | 10–50 RawEvidence records from fixture or live queries |
| `source_quality_summary` | Counts for records_seen, records_emitted, records_rejected, duplicate_count, warnings, errors |
| `validation_summary` | Pass/fail/warn counts |
| Smoke report | Markdown or JSON report with pass/fail determination |

---

## 14. Implementation Plan for Later Roadmap Item

This is a **compact, ordered sequence** for the future hardening implementation item. Not authorized by this plan.

### 14.1 Implementation Sequence

```
Step 1: Create comprehensive fixture files
  └─ tests/fixtures/hn/ask_hn_pain.json
  └─ tests/fixtures/hn/show_hn_launch.json
  └─ tests/fixtures/hn/comments_low_context.json
  └─ tests/fixtures/hn/search_pain_keywords.json
  └─ tests/fixtures/hn/malformed_and_edge_cases.json

Step 2: Update HN adapter to align with contracts
  └─ Change source_id to "hacker_news"
  └─ Change source_type to "discussion"
  └─ Add evidence_kind classification
  └─ Add source_quality_summary production
  └─ Add optional fields (summary, author, created_at, tags,
       engagement_metrics, source_specific_id, quality_flags,
       duplicate_of, canonical_url)
  └─ Implement noise filters
  └─ Implement drop-reason reporting

Step 3: Add registry loader integration (if authorized)
  └─ Align code source_registry.py with config/source_registry.json
  └─ Ensure default_enabled=false in runtime

Step 4: Add comprehensive unit tests
  └─ 20 positive tests + 10 failure tests (Section 12)
  └─ Fixture-only mode; no live calls

Step 5: Add controlled smoke (founder approval required for live)
  └─ Fixture smoke: always runs
  └─ Live smoke: gated behind --allow-live-network

Step 6: Add source quality summary validation
  └─ Tests validate quality summary fields
  └─ Manual inspection of summary output

Step 7: Keep default_enabled=false
  └─ No default weekly run inclusion
  └─ No registry status change without founder approval
```

### 14.2 Files Expected to Change (During Implementation)

| File | Change Type |
|------|------------|
| `src/oos/hn_algolia_collector.py` | Modify: align fields, add evidence_kind, quality summary, optional fields |
| `tests/test_hn_algolia_collector.py` | Modify: expand to 20+ tests with new fixtures |
| `tests/fixtures/hn/*.json` | Create: 5+ fixture files |
| `src/oos/source_registry.py` | Modify: align source_id, source_type, enabled with config |
| `src/oos/models.py` | Possibly: no changes needed (RawEvidence already has all optional fields) |
| `config/source_registry.json` | Possibly: update status after implementation (requires separate approval) |

---

## 15. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **High noise from general-interest stories** | High | Query-drive collection; pain-keyword filtering; off-topic keyword exclusion |
| **Devtools bias** (HN skews heavily toward developer tools) | Medium | Use persona-driven query planner with non-dev personas (ops, finance, freelancer); the existing customer voice queries already target these |
| **Launch hype** (Show HN / Launch HN are promotional) | Medium | Anti-hype scoring (vote velocity vs comment substance); flag as `"suspected_self_promo"`; treat as `"solution_pattern"` not `"pain_signal_candidate"` |
| **Shallow comments** (many HN comments are one-liners, jokes, or meta) | Medium | `low_text_context` flag; prefer items with body > 100 chars; do not drop shallow comments (they may carry signal) |
| **Algolia API rate limits** (10,000 req/hr) | Low-Medium | Respect rate-limit headers; implement exponential backoff; batch queries; fixture-first strategy means live calls are rare |
| **Algolia search coverage** (search may miss older items or have ranking quirks) | Low | Use `search_by_date` for recency; accept that HN is not exhaustive; complement with curated query set |
| **Firebase API latency for deep comment trees** | Low | Defer Firebase integration; start with Algolia-only; add Firebase enrichment later if signal value justifies complexity |
| **`source_url` mistakes** (wrong objectID, comment vs story URL confusion) | Low | HN URL pattern is extremely stable; always `https://news.ycombinator.com/item?id={objectID}`; validate in tests |
| **Duplicate stories/comments** (same story returned by different queries) | Low | `evidence_id`-based dedupe within batch; `duplicate_of` for near-duplicates across batches |
| **Overfitting to technical founders** (HN audience is not representative of all SMB pain) | Medium | HN is one source among several; GitHub Issues, Product Hunt, and pimenov.ai provide different audiences; do not weight HN too heavily in signal scoring |
| **Algolia API deprecation** (low probability but high impact) | Low | HN also has Firebase API as fallback; document migration path in hardening plan |

---

## 16. Non-Goals

This plan explicitly **excludes**:

| Non-Goal | Reason |
|----------|--------|
| Implementing the HN connector | This is a plan, not implementation |
| Making live HN API calls | Prohibited during planning; no live calls in any validation |
| Scraping news.ycombinator.com | Prohibited; Algolia + Firebase APIs only |
| Enabling HN by default | `default_enabled` stays `false` |
| Adding HN to the default weekly run | Prohibited until controlled smoke passes + founder approval |
| Modifying `config/source_registry.json` | Registry changes require separate authorization |
| Modifying `src/`, `tests/`, `scripts/` | No code changes in this item |
| Modifying existing fixtures or creating new fixtures | Implementation concern; not in planning item |
| LLM-based extraction or classification | Not in v2.11 scope for source hardening |
| Firebase API integration | Deferred; Algolia-first strategy |
| Real-time HN monitoring or streaming | Out of scope for v2.11 |
| Comment tree traversal | Deferred; Algolia flat comment hits first |
| `author` display names from HN usernames | Privacy policy: `author` stays `null` |
| Cross-source deduplication | Handled downstream, not in HN adapter |

---

## 17. Decision

**v2.11 item 4 creates the Hacker News Connector Hardening Plan only.**

- No implementation of any HN connector, adapter, collector, or related code is authorized by this plan.
- No live HN API calls are authorized by this plan.
- No fixture files are created or modified by this plan.
- No source code, tests, scripts, or artifacts are modified by this plan.
- The plan documents the current state, identifies gaps relative to v2.11 contracts, defines target alignment, proposes classification heuristics, and provides a sequenced implementation roadmap.
- HN implementation remains unauthorized. A future roadmap item (on a separate branch, with explicit founder approval) may implement the hardening changes described in this plan.
- The next step after this plan is item 5 (GitHub Issues Connector Hardening Plan), which is a similar planning-only item.

---

## 18. References

- [`docs/contracts/discovery_source_adapter_contract.md`](../contracts/discovery_source_adapter_contract.md) — Section 8.1 (HN-specific adapter expectations)
- [`docs/contracts/raw_evidence_artifact_schema.md`](../contracts/raw_evidence_artifact_schema.md) — Sections 5–7 (field mapping, evidence kinds, source types)
- [`docs/contracts/source_allowlist_policy.md`](../contracts/source_allowlist_policy.md) — Section 7.1.1 (HN registry entry)
- [`docs/contracts/source_url_traceability_contract.md`](../contracts/source_url_traceability_contract.md) — Section 5 (placeholder URN policy)
- [`config/source_registry.json`](../../config/source_registry.json) — HN entry: `source_id: hacker_news`
- [`src/oos/hn_algolia_collector.py`](../../src/oos/hn_algolia_collector.py) — Existing collector (179 lines)
- [`tests/test_hn_algolia_collector.py`](../../tests/test_hn_algolia_collector.py) — Existing tests (201 lines, 11 tests)
- [`docs/roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md`](../roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md) — Item 4 definition

---

*Hacker News Connector Hardening Plan. v2.11 item 4. Plan finalized / implementation pending.*
