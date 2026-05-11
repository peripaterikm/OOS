# Product Hunt Feasibility and Connector Plan

**Roadmap:** v2.11
**Item:** 6
**Status:** Feasibility plan finalized / implementation pending

---

## 1. Context

Product Hunt is a candidate new external discovery source for the OOS pipeline. It should be treated as a **product_launch / solution-pattern source**, not a pure pain-signal source. Product Hunt can provide:

- Product launches and descriptions revealing what founders are building
- Market categories and topic trends showing where attention is flowing
- Solution patterns: how problems are being solved, what features are emphasized
- Launch positioning: taglines, descriptions, target customer framing
- Maker claims and commentary about target problems
- User comments revealing objections, alternatives, missing features, and use-case requests
- Engagement metrics (upvotes, comment counts) as traction indicators

Product Hunt is useful for understanding **"what people are building"** and **"what markets are getting attention,"** but it is weaker for direct pain evidence. Products are announced with promotional framing; genuine user pain surfaces primarily in comments, not in launch copy. This source complements Hacker News (discussion/pain) and GitHub Issues (bug/feature/pain) by adding a solution-pattern and market-trend dimension to the discovery funnel.

**This item is planning only.** No implementation, no live API calls, no code modifications. The plan defines whether Product Hunt is feasible, under what constraints, and what a future implementation would require.

---

## 2. Feasibility Summary

**Product Hunt is: feasible with constraints.**

| Dimension | Assessment |
|-----------|-----------|
| **Official API available** | Yes — GraphQL API v2 at `api.producthunt.com/v2` |
| **Auth/token requirements** | Yes — OAuth 2.0 client credentials grant required; client-level token sufficient for read-only public data |
| **Rate limits** | Documented; rate-limit headers available; GraphQL complexity limits apply |
| **GraphQL complexity limits** | Yes — cost-based complexity scoring per query; must design minimal queries |
| **Public data access** | Yes — client-level token grants read access to public posts, products, topics, comments |
| **Comments availability** | Yes — comments available via GraphQL, but may require separate query or nested field |
| **Stable source URLs** | Yes — `https://www.producthunt.com/products/{slug}` pattern is stable |
| **Legal/ToS risk** | Low-Medium — API access is documented and intended for developer use; reasonable excerpting for signal extraction is consistent with public platform norms |
| **Implementation complexity** | Medium — GraphQL client required; auth token flow needed; complexity cost management needed |
| **Signal quality** | Medium — strong on solution-pattern, market-trend, and launch context; weak on direct pain evidence without comment corroboration |

**Recommendation:** Implement as fixture-only connector in a later v2.11 or v2.12 item, only after explicit founder approval. Do not include in default weekly run. Treat as solution-pattern source; do not treat Product Hunt launches alone as validated demand.

---

## 3. Current-State Assessment

### 3.1 Existing Product Hunt Code/Paths

| Artifact | Status |
|----------|--------|
| Product Hunt collector / adapter | **Does not exist.** No file in `src/` references `product_hunt`, `Product Hunt`, or `producthunt`. |
| Product Hunt tests | **None.** No tests reference Product Hunt. |
| Product Hunt fixtures | **None.** No fixture files exist. |
| Source registry (config) | **Present** in [`config/source_registry.json`](../../config/source_registry.json): `source_id: product_hunt`, `source_type: product_launch`, `status: feasibility_required`. |
| Source registry (runtime) | **No entry.** Existing [`src/oos/source_registry.py`](../../src/oos/source_registry.py) does not reference Product Hunt. |
| Adapter contract reference | **Present** in [`docs/contracts/discovery_source_adapter_contract.md`](../contracts/discovery_source_adapter_contract.md) Section 8.3. |
| Raw evidence schema reference | **Present** in [`docs/contracts/raw_evidence_artifact_schema.md`](../contracts/raw_evidence_artifact_schema.md) Sections 9.1, 19. |
| Allowlist policy reference | **Present** in [`docs/contracts/source_allowlist_policy.md`](../contracts/source_allowlist_policy.md) Section 7.1.3. |
| Architecture docs references | **Present** in archived specs (v0.1, v0.2) — historical planning only. |

### 3.2 Gaps Relative to v2.11 Contracts

#### 3.2.1 Gaps vs Discovery Source Adapter Contract

| Contract Requirement | Status | Gap Description |
|---------------------|--------|----------------|
| Adapter exists | **Absent** | No collector or adapter code exists |
| Phase 1: Discover / Fetch | **Absent** | No fetch logic |
| Phase 2: Normalize | **Absent** | No field mapping code |
| Phase 3: Validate | **Absent** | No validation |
| Phase 4: Deduplicate | **Absent** | No dedup logic |
| Phase 5: Persist | **Absent** | No artifact output |
| Phase 7: Source Quality Summary | **Absent** | No quality summary |
| `evidence_kind` field | **Absent** | Would need classification heuristics |
| `source_type: "product_launch"` | **Absent** | Would need to emit this in every record |
| `source_id: "product_hunt"` | **Absent** | Would need adapter constant |
| Explicit `drop_reason` reporting | **Absent** | Would need per-item drop tracking |
| Rate-limit awareness | **Absent** | Would need GraphQL cost awareness + header parsing |
| Auth/token handling | **Absent** | Would need OAuth client credentials flow |

#### 3.2.2 Gaps vs Raw Evidence Artifact Schema

All fields in the schema are currently absent for Product Hunt. A complete field mapping is proposed in Section 8 of this plan.

#### 3.2.3 Gaps vs Source Allowlist Policy

| Policy Requirement | Status | Gap Description |
|-------------------|--------|----------------|
| `source_id: "product_hunt"` | **Registered** | Present in config registry |
| `source_type: "product_launch"` | **Registered** | Aligned |
| `status: feasibility_required` | **Aligned** | This item addresses feasibility |
| `implementation_authorized: false` | **Aligned** | This item does not authorize implementation |
| `default_enabled: false` | **Aligned** | Must remain false |
| `live_access_allowed: false` | **Aligned** | Must remain false |
| `unit_test_mode: fixture_only` | **Aligned** | Must be fixture-only |
| `stable_source_url_required: true` | **Satisfiable** | URL pattern exists |
| `no_placeholder_urls` | **Satisfiable** | Must be enforced in implementation |

### 3.3 Summary of Pre-Implementation State

Product Hunt is a **greenfield source**. No code, tests, fixtures, or runtime integration exists. The config registry entry is a planning placeholder. All gaps must be filled by a future implementation item after explicit founder approval. This plan defines the target state that implementation must achieve.

---

## 4. Access-Method Options

### 4.1 Product Hunt GraphQL API v2 (`api.producthunt.com/v2`)

| Aspect | Assessment |
|--------|-----------|
| **Endpoint** | `POST https://api.producthunt.com/v2/api/graphql` |
| **Data model** | GraphQL schema: `Post` type with `id`, `name`, `tagline`, `description`, `url`, `website`, `votesCount`, `commentsCount`, `createdAt`, `featuredAt`, `topics { edges { node { id, name } } }`, `makers { edges { node { id, name, headline } } }`, `comments { edges { node { id, body, createdAt, user { name } } } }`, `thumbnail { url }`, `media { url }` |
| **Search support** | `posts` query with filters: `featured: true/false`, `topic: "topic-slug"`, `postedAfter`, `postedBefore`, `order: RANKING/NEWEST/VOTES`, `first: N` (pagination via cursors) |
| **Comments access** | Available as nested `comments` field on `Post`, paginated via cursor |
| **Topics access** | `topics` query returns topic list with slugs; can filter posts by topic |
| **Rate limits** | Documented at `api.producthunt.com/v2/docs/rate_limits/headers`; GraphQL complexity (cost) limits; header-based rate info expected (`X-RateLimit-Remaining`, `X-RateLimit-Reset`, `X-Cost`) |
| **Auth type** | OAuth 2.0 client credentials grant; requires `client_id` + `client_secret` → access token |
| **Client-only token** | Confirmed by docs: client-level token for read-only public data access; sufficient for OOS needs |
| **URL stability** | Stable since API v2 launch (~2017); no deprecation announcements |
| **Use for** | Fetching featured posts, posts by topic, product details, comments, makers, engagement metrics |
| **Verification needed (later)** | Confirm exact `X-RateLimit-*` header names; confirm GraphQL cost per query; test pagination cursor format; confirm `comments` field availability on `Post` type; confirm `topics` query response structure; confirm `featuredAt` vs `createdAt` semantics; test `postedAfter` filter behavior |

### 4.2 Static Fixtures Only

| Aspect | Assessment |
|--------|-----------|
| **Use for** | Unit tests, deterministic validation, CI/CD |
| **Data** | Pre-saved JSON payloads mirroring Product Hunt GraphQL responses |
| **Network** | None required |
| **Verification needed (later)** | Fixture determinism across runs; fixture representativeness of real Product Hunt data; no PII in fixture maker/user names |

### 4.3 Manual Curated Import

| Aspect | Assessment |
|--------|-----------|
| **Use for** | Ad-hoc context enrichment; founder-curated product lists |
| **Data** | JSONL files with manually selected Product Hunt product URLs and metadata |
| **Network** | None required |
| **Verification needed (later)** | Schema compatibility with raw evidence; manual curation workflow |

### 4.4 RSS / Sitemap / Static Crawl

| Aspect | Assessment |
|--------|-----------|
| **Feasibility** | Product Hunt does not offer a documented RSS feed or sitemap designed for automated ingestion. The GraphQL API is the intended and documented access method. |
| **Recommendation** | **Do not use.** Use the official GraphQL API exclusively. Any static/scraped access risks ToS violation and URL instability. |

### 4.5 Pre-Implementation Verification Checklist

Before any implementation begins, the following must be verified (not by this plan; by the future implementation item):

- [ ] Exact GraphQL schema fields available on `Post` type (confirm `comments`, `topics`, `makers`, `media`, `thumbnail` edge structures)
- [ ] `comments` field: is `body` (comment text) available? Is `user.name` exposed?
- [ ] `topics` query: response structure, available topic slugs, pagination
- [ ] Client credentials OAuth flow: exact token endpoint, token expiry, refresh policy
- [ ] GraphQL complexity/cost calculation: what is cost per `Post` query with nested fields?
- [ ] Rate-limit header names: confirm `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `X-Cost` or equivalents
- [ ] Pagination cursor format: `endCursor` on `edges` and `pageInfo { hasNextPage }`
- [ ] Product Hunt product URL pattern `https://www.producthunt.com/products/{slug}` confirmed stable
- [ ] `postedAfter` filter: ISO 8601 date format confirmed; behavior for edge dates
- [ ] `featured: true` filter: does it return only featured (launched) products?
- [ ] Maker name exposure: can maker names be safely recorded as `author` without PII concerns?
- [ ] Fixture files can be created from real API responses without storing tokens or PII
- [ ] Comment content length and ToS-safe excerpting policy for user-generated content

---

## 5. API / Auth / Rate-Limit Findings

### 5.1 API Endpoint Type

- **Type:** GraphQL API v2
- **Endpoint:** `POST https://api.producthunt.com/v2/api/graphql`
- **Content-Type:** `application/json`
- **Query format:** Standard GraphQL `{ "query": "...", "variables": {...} }`

### 5.2 Token / Access Requirement

- **Auth type:** OAuth 2.0 client credentials grant
- **Token endpoint:** `POST https://api.producthunt.com/v2/oauth/token`
- **Grant type:** `client_credentials`
- **Required credentials:** `client_id` + `client_secret` (obtained from Product Hunt API dashboard)
- **Token scope:** Public read-only access for client-level token
- **Token handling:** Token must be provided via environment variable (`PRODUCT_HUNT_CLIENT_ID`, `PRODUCT_HUNT_CLIENT_SECRET` or `PRODUCT_HUNT_ACCESS_TOKEN`), never hardcoded
- **No token required for fixture mode.** Unit tests run without any credentials.

### 5.3 Client-Only Token Feasibility

The Product Hunt API docs confirm that a **client-level token** (obtained via client credentials grant) is sufficient for read-only access to public posts, products, and topics. No user-level OAuth is required for OOS's needs (public data reading only). This is documented at:
- `https://api.producthunt.com/v2/docs/oauth_client_only_authentication/oauth_test_use_the_client_level_token_for_read_api_access`

An alternative **developer token** (long-lived, generated from the Product Hunt API dashboard) may also be available and simpler. This requires confirmation during implementation.

### 5.4 Rate-Limit Headers

From Product Hunt rate-limit documentation (`https://api.producthunt.com/v2/docs/rate_limits/headers`):

| Header | Expected | Description |
|--------|----------|-------------|
| `X-RateLimit-Remaining` | Integer | Remaining requests in current window |
| `X-RateLimit-Limit` | Integer | Total requests allowed per window |
| `X-RateLimit-Reset` | Epoch seconds | When the rate-limit window resets |
| `Retry-After` | Seconds | Seconds to wait before retry (on 429) |
| `X-Cost` (or similar) | Integer | GraphQL query cost consumed |

**Note:** Exact header names and values must be confirmed against live responses during implementation. The GraphQL cost model means simple queries may have different limits than complex queries.

### 5.5 GraphQL Complexity Limit

Product Hunt's GraphQL API uses cost-based rate limiting:
- Each query is assigned a cost based on requested fields and nesting depth
- There is a maximum cost per request (exact value TBD — verify during implementation)
- Nested connections (`comments`, `makers`, `topics`) increase query cost significantly
- Minimal queries (product name, tagline, description, URL, votes) have very low cost

**Implication for OOS:** The initial adapter should use minimal queries. Comment fetching, if authorized, should be a separate, explicitly opted-in operation with its own cost management.

### 5.6 Unclear Areas Requiring Later Verification

- Exact rate-limit window size and request count for client-level tokens
- Whether `X-Cost` (or equivalent) header is returned on every response
- Maximum number of nested `comments` edges retrievable in one query
- Topic slug list stability and completeness
- Token expiry behavior for client-credentials tokens
- Whether `developer token` (non-expiring) is a valid alternative to client-credentials flow
- Pagination: exact `pageInfo` field names (`hasNextPage`, `endCursor`)

---

## 6. Proposed Source Registry Alignment

The Product Hunt adapter must align with [`config/source_registry.json`](../../config/source_registry.json). The current registry entry is correct as-is for the planning state:

### 6.1 Current Registry State (Aligned, No Changes Needed)

```json
{
  "source_id": "product_hunt",
  "source_type": "product_launch",
  "source_name": "Product Hunt",
  "status": "feasibility_required",
  "implementation_authorized": false,
  "default_enabled": false,
  "live_access_allowed": false,
  "unit_test_mode": "fixture_only",
  "likely_access_methods": ["product_hunt_graphql_api"],
  "stable_source_url_required": true,
  "source_url_policy": "mandatory_external_url",
  "risk_level": "medium",
  "notes": "solution-signal/product-pattern source, not pure pain source"
}
```

### 6.2 Target State After Implementation (Not Authorized by This Plan)

```json
{
  "source_id": "product_hunt",
  "source_type": "product_launch",
  "source_name": "Product Hunt",
  "status": "implemented_fixture_only",
  "implementation_authorized": true,
  "default_enabled": false,
  "live_access_allowed": false,
  "unit_test_mode": "fixture_only",
  "likely_access_methods": ["product_hunt_graphql_api"],
  "stable_source_url_required": true,
  "source_url_policy": "mandatory_external_url",
  "risk_level": "medium",
  "notes": "implemented per v2.11 item 6 plan; fixture-only until controlled smoke passes; solution-pattern source; anti-hype filters required; not default-enabled"
}
```

**This target state is not authorized by this plan. It is noted here for the future implementation item.**

### 6.3 Key Implementation-Time Constants

| Field | Value | Notes |
|-------|-------|-------|
| `source_id` | `"product_hunt"` | Adapter constant |
| `source_type` | `"product_launch"` | Per adapter contract Section 7.3 |
| `source_name` | `"Product Hunt"` | Human-readable |
| `evidence_id` prefix | `"raw_product_hunt_{product_id}"` | Using Product Hunt's native product ID |
| `source_url` pattern | `"https://www.producthunt.com/products/{slug}"` | Stable canonical URL |
| `access_policy` | `"public_api_auth_required"` | Client credentials required for live access |
| `collection_method` | `"fixture"` / `"live_opt_in"` / `"dry_run"` | Standard values |

---

## 7. Raw Evidence Mapping

### 7.1 Product Hunt Post/Product → RawEvidence Field Mapping

| RawEvidence Field | Required | Source from Product Hunt GraphQL | Fallback / Notes |
|------------------|----------|----------------------------------|------------------|
| `evidence_id` | Yes | `"raw_product_hunt_{product_id}"` | Stable per product; uses Product Hunt's native `id` field from `Post.id` |
| `source_id` | Yes | `"product_hunt"` | Adapter constant |
| `source_type` | Yes | `"product_launch"` | Per source category |
| `source_name` | Yes | `"Product Hunt"` | Human-readable constant |
| `source_url` | Yes | `"https://www.producthunt.com/products/{slug}"` | Constructed from `Post.slug` or `Post.url` |
| `collected_at` | Yes | ISO 8601 of fetch time | Fixture mode: fixed timestamp |
| `title` | Yes | `Post.name` or `Post.tagline` | If both present: `{name}: {tagline}` |
| `body` | Yes | `Post.description` | Full product description; truncate if over 10,000 chars |
| `language` | Yes | `"en"` (default) | Product Hunt is English-dominant; detect if needed |
| `topic_id` | Yes | From `scheduled_item.topic_id` | — |
| `query_kind` | Yes | From `scheduled_item.query_kind` | — |
| `content_hash` | Yes | SHA-256 of `normalize_raw_evidence_content(title, body)` | Deterministic |
| `author_or_context` | Yes | Role label (see 7.2) | Privacy-safe; no personal handles |
| `raw_metadata` | Yes | Source-specific metadata dict (see 7.3) | Must be JSON object |
| `access_policy` | Yes | `"public_api_auth_required"` | Live mode requires token |
| `collection_method` | Yes | `"fixture"` / `"live_opt_in"` / `"dry_run"` | Per fetch mode |
| `evidence_kind` | Yes | Classification result (see Section 10) | Must be valid enum |
| `summary` | No | `Post.tagline` or first 500 chars of `Post.description` | Marked in extraction_notes |
| `author` | No | Privacy-safe maker display name (see 7.2) | `null` if not safe to display |
| `created_at` | No | `Post.createdAt` or `Post.featuredAt` (ISO 8601) | `null` if missing |
| `updated_at` | No | `null` | Product Hunt does not expose an update timestamp |
| `tags` | No | `Post.topics.edges[].node.name` | Topic names as string array |
| `categories` | No | `Post.topics.edges[].node.name` | Same as tags for Product Hunt |
| `engagement_metrics` | No | `{"votes": Post.votesCount, "comments": Post.commentsCount}` | `null` if both zero/missing |
| `source_specific_id` | No | `Post.id` | Product Hunt's native product ID |
| `extraction_notes` | No | Notes about truncation, missing fields | `null` if no issues |
| `quality_flags` | No | Quality indicators (see Section 14) | `null` if no flags |
| `duplicate_of` | No | `evidence_id` of canonical record | `null` if not a duplicate |
| `canonical_url` | No | `Post.website` (the product's external website) | `null` if same as `source_url` or no external website |

### 7.2 `author` and `author_or_context` Privacy Policy

| Context | `author_or_context` | `author` |
|---------|-------------------|---------|
| Product with makers | `"product maker(s)"` | `null` (no safe public display of personal names without consent review) |
| Product with single maker | `"product maker"` | `null` |
| Product with no makers | `"unattributed launch"` | `null` |
| Comment author | `"Product Hunt commenter"` | `null` |
| Maker comment | `"product maker (comment)"` | `null` |

**Policy:** Maker names on Product Hunt are public profile names. However, the OOS privacy policy defaults to `author = null` and uses `author_or_context` for role context. The `author_present` boolean in `raw_metadata` indicates whether the source reports an author. The `makers` field in `raw_metadata` stores the count and role labels (e.g., `"3 makers"`), not individual names.

### 7.3 `raw_metadata` Structure

```json
{
  "product_id": "abc123",
  "slug": "example-product",
  "featured_at": "2026-05-08T00:00:00Z",
  "created_at": "2026-05-08T00:00:00Z",
  "topics": ["ai", "developer-tools"],
  "makers_count": 3,
  "makers_roles": ["CEO", "CTO", "Designer"],
  "votes_count": 250,
  "comments_count": 40,
  "author_present": true,
  "product_website": "https://example.com",
  "thumbnail_url": "https://ph-files.imgix.net/abc123.png",
  "query_plan_id": "qp_abc123",
  "dedup_key": "dk_def456",
  "description_length": 1200,
  "comment_excerpt_included": false
}
```

Additional fields to add during implementation:

| Metadata Field | Purpose |
|---------------|---------|
| `product_id` | Product Hunt's native product ID |
| `slug` | URL slug for constructing `source_url` |
| `featured_at` | When the product was featured/launched |
| `topic_names` | Topic names as list |
| `makers_count` | Number of makers |
| `product_website` | External product website URL |
| `thumbnail_url` | Product thumbnail image URL |
| `comment_excerpt_included` | Whether comment text was included in body |
| `description_length` | Character count of the description |

---

## 8. Product Hunt Evidence Kinds

### 8.1 Valid Evidence Kinds for Product Hunt

Every Product Hunt raw evidence record must carry an `evidence_kind`. Product Hunt is a `product_launch` source type, so its primary evidence kinds are:

| `evidence_kind` | When to Use | Frequency Expectation |
|-----------------|-------------|----------------------|
| `product_launch` | A new product or major feature launch described in a post | Most common — default for featured products |
| `solution_pattern` | A product that exemplifies a solution approach, architectural pattern, or market positioning strategy | Common — products with clear problem/solution framing |
| `market_trend` | Multiple launches or comment activity indicating a market direction or category emergence | Moderate — inferred from topic clusters and launch frequency |
| `curated_context` | Product description or maker commentary that provides industry/domain insight beyond the product itself | Uncommon |
| `pain_signal_candidate` | Comment or description that explicitly describes a user frustration, unmet need, or workaround | Rare — only when user comments contain pain language |
| `unknown` | Cannot classify; requires downstream review | Fallback |

### 8.2 Classification Decision Tree (Proposed)

```
Input: Product Hunt post with name, tagline, description, topics, comments (if available), votesCount, commentsCount

1. IF description OR comments contain explicit pain_keywords:
   → evidence_kind = "pain_signal_candidate"
   (Note: this is RARE on Product Hunt; most pain is in comments, not descriptions)

2. IF description contains solution_pattern_keywords AND has clear problem/solution framing:
   → evidence_kind = "solution_pattern"

3. IF post is part of a topic/category cluster with >= 3 posts in same topic within 30 days:
   → evidence_kind = "market_trend"

4. IF description contains curated_context_keywords OR maker commentary provides industry/domain insight:
   → evidence_kind = "curated_context"

5. DEFAULT for featured/launched products:
   → evidence_kind = "product_launch"

6. FALLBACK:
   → evidence_kind = "unknown"
```

### 8.3 Keyword Sets (Proposed, to be Refined During Implementation)

**pain_keywords:** `"frustrated"`, `"couldn't find"`, `"nothing worked"`, `"had to build"`, `"spent hours"`, `"manual process"`, `"pain point"`, `"sick of"`, `"tired of"`, `"waste of"`, `"broken"`, `"terrible"`, `"nightmare"`

**solution_pattern_keywords:** `"built with"`, `"automates"`, `"replaces"`, `"integrates with"`, `"alternative to"`, `"open source"`, `"no-code"`, `"low-code"`, `"AI-powered"`, `"workflow"`, `"pipeline"`

**curated_context_keywords:** `"lessons learned"`, `"we discovered"`, `"industry insight"`, `"market research"`, `"user research"`, `"trends in"`, `"state of"`, `"future of"`

### 8.4 Classification Tiebreakers

1. Pain signal from comments takes highest priority (it is the rarest and most valuable).
2. Longest keyword match wins.
3. If description is under 100 characters, lean toward `"unknown"` (insufficient context).
4. `"unknown"` is the safe default. The downstream [`EvidenceClassifier`](../../src/oos/evidence_classifier.py) may reclassify.
5. Products with `votesCount >= 100` AND `commentsCount >= 20` slightly boost `market_trend` confidence.

---

## 9. Comments Policy

### 9.1 Product Description as Primary Evidence

The product description, tagline, and maker commentary are the primary evidence source for Product Hunt records. These are directly available on the `Post` type without additional nesting cost.

### 9.2 Comments as Optional Context

| Aspect | Policy |
|--------|--------|
| **Default behavior** | Comments are **not fetched**. Product description only. |
| **Comment count** | Captured as `commentsCount` in `engagement_metrics.comments`. |
| **When to fetch comments** | Only when explicitly authorized via configuration toggle (`include_comments: true`) AND API feasibility confirms access and ToS-safe usage. |
| **Comments are valuable for** | Pain evidence ("I tried this, it didn't work for X"), objections, alternatives mentioned, missing features, use-case requests |
| **Comment fetching is deferred** | Unless a specific implementation item authorizes comment enrichment after confirming field availability and cost. |
| **Comment content in evidence** | If fetched, appended to `body` with clear delimiter (`\n\n--- COMMENTS ---\n\n`) and documented in `extraction_notes`. |

### 9.3 Maker Comments vs User Comments

| Comment Type | Signal Value | Privacy Note |
|-------------|-------------|-------------|
| **Maker comments** | Medium — explains product reasoning, target problem, future plans | Maker names are public; still use role labels only |
| **User comments** | High — reveals objections, alternatives, missing features, use cases, pain evidence | Use role labels only (`"Product Hunt commenter"`) |
| **Maker responses to users** | Medium-High — reveals how founders think about their problem, what objections they hear | Same privacy treatment |

### 9.4 Copyright and Content Concerns

- Product Hunt descriptions and comments are user-generated content.
- Storing full comment threads may exceed reasonable excerpting for signal extraction.
- The `comment_excerpt_included` boolean in `raw_metadata` tracks whether comments were included.
- If comment fetching is authorized, prefer summarization or top-N most relevant comments rather than full-thread reproduction.
- No silent full-text reproduction of lengthy comment threads.

### 9.5 `source_url` for Comments

If comments are included as part of an evidence record:
- The `source_url` remains the product page URL (`https://www.producthunt.com/products/{slug}`).
- Individual comments are not separate evidence records in the default configuration.
- If individual comments become separate records (future), each must carry its own comment URL. The comment URL pattern on Product Hunt needs verification (likely `https://www.producthunt.com/products/{slug}/comments/{comment_id}` or similar anchor-based pattern).

---

## 10. Source URL Traceability

### 10.1 Product Hunt Product URL Format

Every Product Hunt product has a canonical URL:

```
https://www.producthunt.com/products/{slug}
```

Where `slug` is the product's URL slug (e.g., `example-product`). This URL pattern is stable and has been consistent since Product Hunt's launch.

### 10.2 Comment URL Expectation

If individual comments become separate evidence records (deferred), the comment URL pattern must be verified against Product Hunt's actual URL structure. Likely patterns:
- `https://www.producthunt.com/products/{slug}?comment={comment_id}`
- `https://www.producthunt.com/products/{slug}#comment-{comment_id}`

**Verification needed before comment-as-separate-records implementation.**

### 10.3 Fixture URL Policy

- Fixture records must use deterministic, stable URLs.
- **Good:** `"https://www.producthunt.com/products/example-product"` (deterministic test slug)
- **Good:** `"https://www.producthunt.com/products/fixture-product-1"` (deterministic test slug)
- **Bad:** `"urn:oos:test:fixture:product_hunt"` (placeholder, forbidden)
- **Bad:** `"https://www.producthunt.com/products/{dynamic-slug}"` (non-deterministic)

### 10.4 URL Validation Rules (Per Source URL Traceability Contract)

| Rule | Implementation |
|------|---------------|
| `source_url` must be present | Required field; missing `slug`/`url` → drop record + report |
| `source_url` must use `https://` | `producthunt.com` URLs are always HTTPS |
| No `urn:oos:*` placeholders | Never generated by Product Hunt adapter |
| Stable, canonical link | Always `https://www.producthunt.com/products/{slug}` |
| Fixture URLs deterministic | Fixed slugs in fixture data |
| Missing `source_url` → validation failure | Record dropped; counted in `missing_url_count` |
| No placeholder URNs | Zero tolerance per traceability contract |
| `canonical_url` vs `source_url` | `source_url` = Product Hunt product page; `canonical_url` = external product website (`Post.website`) |

### 10.5 No Placeholder URLs

Per [`source_url_traceability_contract.md`](../contracts/source_url_traceability_contract.md) Section 5: `urn:oos:*` and any other placeholder URNs are forbidden. The Product Hunt adapter must never generate a placeholder URL. If a product cannot produce a valid `source_url` (missing slug), it must be dropped with an explicit `drop_reason: "missing_source_url"`.

---

## 11. Deduplication Plan

### 11.1 Product ID-Based Dedupe (Primary)

Every Product Hunt product has a unique `id` (native identifier). Within a single collection session:

- `evidence_id = "raw_product_hunt_{product_id}"`
- If the same product appears in multiple query results (e.g., same product in different topic queries), the first occurrence is kept; subsequent occurrences are dropped.
- The `duplicate_count` in the source quality summary tracks exact duplicates.

### 11.2 Canonical URL Dedupe

Since `source_url = "https://www.producthunt.com/products/{slug}"` is unique per product, `source_url`-based dedupe is equivalent to product ID-based dedupe. Products with the same slug are the same product.

### 11.3 Maker/Product Slug Dedupe

- A product slug is unique on Product Hunt. The same slug always refers to the same product.
- Makers may appear on multiple products; this is not a deduplication concern (different products are different evidence records).

### 11.4 Duplicate Launches / Relaunches

- Product Hunt may list the same product featured on multiple dates (relaunches, major feature launches).
- If the same `product_id` appears with different `featuredAt` dates: the later occurrence is a near-duplicate.
- Both records are retained; the later record sets `duplicate_of` to the earlier record's `evidence_id`.
- The `near_duplicate_count` tracks this.
- `extraction_notes` documents: `"relaunch or feature launch of previously featured product"`.

### 11.5 Cross-Source Deduplication

- The Product Hunt adapter does **not** compare its output against HN, GitHub Issues, or any other source.
- Cross-source duplication (e.g., a Product Hunt product's GitHub repo being discussed on HN) is handled downstream in [`CandidateSignalExtractor`](../../src/oos/candidate_signal_extractor.py) or [`signal_dedup.py`](../../src/oos/signal_dedup.py).
- Per the raw evidence schema (Section 15.3): cross-source records are never silently dropped at the raw evidence layer.

### 11.6 No Silent Drops

Per the adapter contract (Section 5.5):
- Every excluded Product Hunt item must be reported with `product_id`, title excerpt, and `drop_reason`.
- Drop reasons must be specific: `"missing_product_id"`, `"duplicate_evidence_id"`, `"empty_title_and_body"`, `"missing_source_url"`, `"validation_failure"`, `"below_minimum_context"`.
- All drop counts appear in the source quality summary.

---

## 12. Anti-Hype and Quality Filters

### 12.1 Proposed Filters

| Filter | Trigger | Action |
|--------|---------|--------|
| **Launch hype** | `votesCount` < 10 AND `commentsCount` < 3 AND `description_length` > 1000 (promotional fluff) | Set `quality_flags: ["launch_hype_suspected"]` |
| **Shallow tagline-only record** | `description_length` < 100 chars | Set `quality_flags: ["low_text_context"]`; do not drop but flag |
| **Suspected self-promotion** | Description contains excessive marketing language (e.g., "revolutionary", "game-changing", "world's first") without substance | Set `quality_flags: ["suspected_self_promo"]` |
| **Low-context launch** | `description_length` < 200 AND `topics` is empty | Set `quality_flags: ["low_text_context"]`; do not drop |
| **Unclear customer / problem statement** | Description does not mention target user, problem, or use case | Set `quality_flags: ["unclear_icp_or_problem"]` |
| **Generic AI claims** | Description contains "AI-powered", "AI-driven", "AI-first" without describing specific mechanism | Set `quality_flags: ["generic_ai_claims"]` |
| **Prefer products with clear ICP** | Description mentions specific user/customer persona ("for developers", "for SMB owners", "for freelancers") | Boost priority; clear ICP = more actionable signal |
| **Prefer products with traction** | `votesCount >= 20` OR `commentsCount >= 10` | Boost priority; traction suggests real market interest |
| **Prefer products with topic context** | `topics` non-empty AND includes relevant OOS verticals | Boost priority for AI, productivity, devtools, finance, automation |
| **Prefer products with comments** | `commentsCount >= 5` | Boost priority; comments often contain pain/objection/alternative signals |

### 12.2 Launch Hype Detection Keywords

`"revolutionary"`, `"game-changing"`, `"world's first"`, `"disrupting"`, `"the future of"`, `"never before"`, `"unprecedented"`, `"magical"`, `"seamless"`, `"effortless"`, `"all-in-one"`, `"one-stop shop"`

### 12.3 Generic AI Claims Detection

`"AI-powered"`, `"AI-driven"`, `"powered by AI"`, `"AI-first"`, `"AI-native"`, `"built with AI"` — when not accompanied by specific description of what the AI does.

### 12.4 Filtering Policy

1. **Filters are advisory, not blocking.** Records with quality flags are retained in `records`.
2. **No silent drops.** Every record that triggers a filter is included with flags; filtering decisions happen downstream.
3. **Quality flag provenance.** Every flag set must have a traceable reason (the matching keyword or heuristic).
4. **Records dropped for validation failures** (missing `product_id`, empty title+body, missing `source_url`) are excluded from `records` and counted in `records_rejected`.
5. **Do not silently drop records without reason.** Every excluded item must have a documented `drop_reason`.

---

## 13. Query / Collection Strategy

### 13.1 Phased Approach

| Phase | Scope | Fetch Mode | Authorization |
|-------|-------|-----------|---------------|
| **Phase 1: Fixture-only** | Pre-saved JSON payloads; all tests pass | `fixture` | This plan recommends it; implementation requires separate authorization |
| **Phase 2: Curated historical launches** | Fixed set of known Product Hunt products, fixture-backed | `fixture` | Separate authorization |
| **Phase 3: Topic/category allowlist** | Products by topic, fixture-backed with pre-fetched responses | `fixture` | Separate authorization |
| **Phase 4: Live opt-in** | Controlled live GraphQL queries with explicit founder approval | `live_opt_in` | Explicit founder approval **only** |
| **Phase 5: Default weekly run** | Not in v2.11 scope | — | v2.12+ after sustained smoke evidence |

### 13.2 Candidate Topics / Categories

The following Product Hunt topics are relevant to OOS's opportunity thesis. These are **planning proposals only**; the actual allowlist must be curated during implementation with founder review.

| Topic | Relevance | Notes |
|-------|-----------|-------|
| **AI** | High — AI tooling, automation, and workflow products | Core OOS vertical |
| **Productivity** | High — tools that help people work more efficiently | Adjacent to automation thesis |
| **Developer Tools** | High — devtools, APIs, infrastructure | Developer audience signal |
| **No-Code** | Medium-High — democratized tool creation | Adjacent to SMB/freelancer thesis |
| **Marketing** | Medium — marketing automation, content tools | SMB marketing pain |
| **Sales** | Medium — sales automation, CRM | SMB sales process pain |
| **Analytics** | Medium — data analysis, reporting | Operations insight |
| **Finance / Accounting** | Medium-High — finops, bookkeeping, invoicing | Direct OOS relevance |
| **Customer Support** | Medium — support automation, helpdesks | SMB operations pain |
| **Automation** | High — workflow automation, integrations | Direct OOS relevance |
| **Remote Work** | Medium — collaboration, async communication | SMB workflow context |
| **Design Tools** | Medium — UI/UX, graphic design | Adjacent; lower priority |

### 13.3 Query Configuration

- Queries are configured externally (not hardcoded in the adapter).
- Each query has a `query_kind` (e.g., `"featured_by_topic"`, `"recent_launches"`).
- The query planner generates `ScheduledCollectionItem` entries with `query_text` (topic slug or GraphQL query parameters).
- Product Hunt adapter receives `query_kind` and `topic_id` via `ScheduledCollectionItem`.
- Topic allowlist is separate from queries and configurable.

### 13.4 Default Weekly Run

- **No default weekly run inclusion** until:
  1. Connector is implemented and fixture tests pass.
  2. Controlled smoke with live GraphQL API passes at least 3 times.
  3. Source quality report shows healthy metrics.
  4. Noise rate is below configured threshold or adequate anti-hype filters exist.
  5. Source URL validation is clean (no placeholders, no missing URLs).
  6. Founder approval is recorded.

---

## 14. Validation Plan

### 14.1 Required Tests (Future Implementation Item)

| # | Test Case | What It Validates |
|---|-----------|-------------------|
| T1 | Fixture loads without error | Adapter can read and parse fixture GraphQL response JSON |
| T2 | Every output record has a stable `source_url` | `https://www.producthunt.com/products/{slug}`; no placeholders |
| T3 | `source_url` format matches expected pattern | `https://` scheme, valid hostname `www.producthunt.com` |
| T4 | No `urn:oos:*` placeholders anywhere | Zero tolerance per traceability contract |
| T5 | `content_hash` matches normalized content | `validate()` passes on all records |
| T6 | `author_or_context` is privacy-safe | No personal maker names/handles exposed |
| T7 | `evidence_id` follows `raw_product_hunt_{product_id}` | Stable ID pattern |
| T8 | Duplicate `evidence_id` items deduplicated within batch | `duplicate_count` reported |
| T9 | Missing `product_id` produces warning and drop | Item excluded; reported in quality summary |
| T10 | Empty title AND body produces warning and drop | Item excluded; reported in quality summary |
| T11 | Fixture file not found produces error | Error surfaced in quality summary |
| T12 | Malformed fixture produces error | Error surfaced; no partial output |
| T13 | All required `RawEvidence` fields populated | Validation passes for every output record |
| T14 | `source_quality_summary` is produced | All counts and metadata present |
| T15 | `evidence_kind` is set for every record | Must be valid enum value; `"unknown"` is acceptable |
| T16 | Classification heuristics match expected results | Launch post → `"product_launch"`; solution pattern → `"solution_pattern"` |
| T17 | Anti-hype flags set correctly | Shallow description gets `"low_text_context"`; promotional language gets `"suspected_self_promo"` |
| T18 | `engagement_metrics` populated when available | Votes and comment counts in structured object |
| T19 | `tags` populated from topics | Topic names as string array |
| T20 | `source_type` is `"product_launch"` | Not any other value |
| T21 | `canonical_url` populated when product has external website | `Post.website` mapped to `canonical_url` |
| T22 | `created_at` mapped from `featuredAt` | ISO 8601 timestamp |
| T23 | Maker count and roles in `raw_metadata` | `makers_count`, `makers_roles` populated |
| T24 | `summary` populated from tagline | Tagline or truncated description |

### 14.2 Failure Case Tests

| # | Failure Scenario | Expected Behavior |
|---|-----------------|-------------------|
| F1 | Fixture file not found | Error in quality summary; no records emitted |
| F2 | Fixture file with invalid JSON | Error in quality summary; no records emitted |
| F3 | Fixture with item missing `id` | Warning; item dropped; `missing_url_count` or `records_rejected` incremented |
| F4 | Fixture with item having `slug: ""` | Warning; item dropped (`missing_source_url`) |
| F5 | Fixture with item having empty name AND empty description | Warning; item dropped |
| F6 | Fixture with duplicate `product_id` entries | First kept; duplicate dropped; `duplicate_count = 1` |
| F7 | Fixture with empty `topics` | No crash; `tags` is `null`; classification defaults to `"product_launch"` |
| F8 | Live mode (mocked): API returning 5xx after retries | Error; quality summary reports failure |
| F9 | Live mode (mocked): API returning 429 with `Retry-After` | Warning; delay honored; retry attempted |
| F10 | Live mode (mocked): API returning 401/403 | Error; auth failure reported |
| F11 | Live mode (mocked): empty `edges` array | No records; quality summary reports 0 records_seen |
| F12 | Fixture with excessive promotional language | `quality_flags` contains `"suspected_self_promo"`; record retained |
| F13 | Fixture with AI claims without specifics | `quality_flags` contains `"generic_ai_claims"`; record retained |
| F14 | Fixture with no topic data | `tags` is `null`; record retained |

### 14.3 No Live API in Unit Tests

All tests in T1–T24 and F1–F14 must use `fixture` mode or mocked responses. Zero live network calls in the default test suite. Auth/token absence must not affect unit tests — they must pass without any `PRODUCT_HUNT_*` environment variables set.

---

## 15. Controlled Smoke Plan

### 15.1 Smoke Phases

| Phase | Description | Authorization |
|-------|-------------|---------------|
| **Smoke 1: Fixture validation** | Load all Product Hunt fixtures; validate every record; verify quality summary | No live calls; can run in CI |
| **Smoke 2: Dry-run** | Run the adapter in `dry_run` mode; verify configuration loading | No live calls; can run in CI |
| **Smoke 3: Live smoke** | Run against live Product Hunt GraphQL API with minimal query | Explicit founder approval required |
| **Smoke 4: Live smoke (multi-topic)** | Run against topic allowlist with live data | Explicit founder approval; deferred |

### 15.2 Smoke 1: Fixture Validation (Always Allowed)

1. Load all Product Hunt fixture files.
2. Run the adapter in `fixture` mode for each fixture.
3. Validate:
   - Every `RawEvidence` record passes `.validate()`.
   - Every `source_url` is `https://www.producthunt.com/products/{slug}`.
   - Zero `urn:oos:*` placeholders.
   - `content_hash` matches for every record.
   - `source_quality_summary` has correct counts.
   - `evidence_kind` is set on every record.
   - `source_type` is `"product_launch"` on every record.
   - Anti-hype flags are correctly applied.
4. Output: pass/fail per fixture.

### 15.3 Smoke 3: Live Smoke (Founder Approval Only)

1. Run a single minimal GraphQL query against Product Hunt API:
   ```graphql
   query {
     posts(featured: true, first: 10, order: VOTES) {
       edges {
         node {
           id
           name
           tagline
           description
           slug
           url
           website
           votesCount
           commentsCount
           createdAt
           featuredAt
           topics { edges { node { id name } } }
         }
       }
     }
   }
   ```
2. **Requires:** `PRODUCT_HUNT_CLIENT_ID` and `PRODUCT_HUNT_CLIENT_SECRET` (or `PRODUCT_HUNT_ACCESS_TOKEN`) environment variables.
3. Validate that all 10 records have:
   - Real `source_url` → real Product Hunt product pages.
   - Valid `evidence_id` → `raw_product_hunt_{product_id}`.
   - Non-empty name and description.
   - `evidence_kind` set.
4. Check rate-limit headers in response (`X-RateLimit-Remaining`, `X-RateLimit-Reset`, cost header).
5. Produce a `source_quality_summary` with live metadata including rate-limit snapshot.
6. Record the run in a smoke report artifact.
7. **No default weekly run inclusion until smoke passes at least 3 times.**

### 15.4 Expected Smoke Outputs

| Output | Description |
|--------|-------------|
| `records` | 10 RawEvidence records per fixture or live query (configurable via `first`) |
| `source_quality_summary` | Counts for records_seen, records_emitted, records_rejected, duplicate_count, warnings, errors, rate-limit info |
| `validation_summary` | Pass/fail/warn counts |
| Smoke report | Markdown or JSON report with pass/fail determination |

### 15.5 Source Quality Summary Required

Every smoke run (fixture and live) must produce a source quality summary containing:
- `source_id`, `source_type`, `fetch_mode`
- `records_seen`, `records_emitted`, `records_rejected`
- `duplicate_count`, `near_duplicate_count`
- `warning_count`, `error_count`
- `placeholder_url_count`, `missing_url_count`
- `missing_date_count`, `low_text_context_count`
- `noise_indicators` (anti-hype flag summaries)
- `rate_limit_remaining`, `rate_limit_reset` (live mode only)
- `quality_score` (null until item 8 defines scoring)

---

## 16. Implementation Plan for Later Roadmap Item

This is a **compact, ordered sequence** for the future Product Hunt connector implementation item. Not authorized by this plan.

### 16.1 Implementation Sequence

```
Step 1: Create comprehensive fixture files
  └─ tests/fixtures/product_hunt/featured_launches.json
  └─ tests/fixtures/product_hunt/ai_topic_products.json
  └─ tests/fixtures/product_hunt/low_context_and_edge_cases.json
  └─ tests/fixtures/product_hunt/hype_and_noise_examples.json
  └─ tests/fixtures/product_hunt/multi_topic_sample.json

Step 2: Implement Product Hunt adapter in fixture mode
  └─ Create src/oos/product_hunt_collector.py
  └─ Define adapter constant: SOURCE_ID = "product_hunt"
  └─ Define adapter constant: SOURCE_TYPE = "product_launch"
  └─ Implement ph_post_to_raw_evidence() field mapping
  └─ Map Post fields to RawEvidence per Section 7
  └─ Add evidence_kind classification per Section 8
  └─ Add source_quality_summary production
  └─ Add anti-hype/quality flags per Section 12
  └─ Add source_url construction (slug → producthunt.com/products/{slug})
  └─ Add explicit drop_reason reporting
  └─ Support fixture and live_opt_in modes

Step 3: Define minimal GraphQL query
  └─ Only after API field review during implementation
  └─ Start with minimal query: id, name, tagline, description, slug, url,
      website, votesCount, commentsCount, createdAt, featuredAt,
      topics { name }, makers count only
  └─ Defer comments, media, thumbnail for later optimization

Step 4: Add topic/category allowlist config
  └─ External config file or registry entry for allowed topic slugs
  └─ Default: AI, productivity, devtools, no-code, automation, finance

Step 5: Add unit tests
  └─ 24 positive tests + 14 failure tests per Sections 14.1–14.2
  └─ Fixture-only mode; no live calls
  └─ Auth/token absence does not affect unit tests

Step 6: Add controlled smoke
  └─ Fixture smoke: always runs
  └─ Live smoke: gated behind --allow-live-network and PRODUCT_HUNT_* env vars

Step 7: Keep default_enabled=false
  └─ No default weekly run inclusion
  └─ No registry status change without founder approval
```

### 16.2 Files Expected to Change (During Implementation)

| File | Change Type |
|------|------------|
| `src/oos/product_hunt_collector.py` | **Create:** new Product Hunt adapter |
| `tests/test_product_hunt_collector.py` | **Create:** 38+ tests with fixtures |
| `tests/fixtures/product_hunt/*.json` | **Create:** 5+ fixture files |
| `config/source_registry.json` | Possibly update status (requires separate approval) |
| `src/oos/source_registry.py` | Possibly add runtime registry entry (requires separate approval) |

---

## 17. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Launch hype** (products are promotional, not pain signals) | High | Anti-hype scoring; `quality_flags` for promotional language; classify as `product_launch`/`solution_pattern` not `pain_signal_candidate`; do not treat launches as validated demand |
| **Weak pain evidence** (Product Hunt is not a complaint forum) | High | Product Hunt is a solution-pattern source by design. Accept this; downstream classification must account for source type. Complement with HN/GitHub for pain evidence. |
| **Auth/token setup** (requires OAuth client credentials) | Medium | Client-credentials flow is well-documented; developer token may simplify. Token handling via env vars only. Fixture mode needs no token. |
| **GraphQL complexity limits** (cost per query with nested fields) | Medium | Start with minimal queries; defer comments; measure cost during implementation; batch queries carefully |
| **API schema changes** (GraphQL schema may evolve) | Low-Medium | Product Hunt API v2 is stable; GraphQL introspection allows adaptation; fixture tests catch schema changes |
| **Missing comments or limited fields** (API may not expose all needed fields) | Medium | Verify fields during pre-implementation phase; if comments are unavailable, treat as known limitation and document |
| **Maker self-promotion** (makers hype their own products in comments/descriptions) | Medium | Anti-hype filters; `quality_flags: ["suspected_self_promo"]`; comment content flagged but not excluded |
| **Survivorship / visibility bias** (only successful/popular products get votes and comments) | Medium | Product Hunt naturally biases toward popular products; accept as known limitation; complement with curated historical launches for less-visible products |
| **Duplicate / relaunch handling** (same product featured multiple times) | Medium | `duplicate_of` for relaunches; `near_duplicate_count` tracking; `extraction_notes` documenting relaunch status |
| **`source_url` mistakes** (wrong slug, URL construction errors) | Low | Slug is stable and comes directly from API; URL pattern `https://www.producthunt.com/products/{slug}` is deterministic; validate in tests |
| **Copyright / user-generated content concerns** (storing product descriptions, comments) | Low-Medium | Reasonable excerpting for signal extraction; truncate long descriptions; do not store full comment threads by default; `comment_excerpt_included` tracking |
| **Over-indexing on AI products** (Product Hunt is currently AI-heavy) | Medium | Topic allowlist controls scope; do not over-weight Product Hunt signals in AI-heavy pipeline decisions; complement with non-AI sources |
| **Developer-tool bias** (Product Hunt audience skews toward developers/tech) | Medium | Accept as known limitation; complement with pimenov.ai, and future SMB-oriented sources; do not treat Product Hunt as representative of all markets |
| **Rate-limit exhaustion during live smoke** | Low | Fixture-first; live smoke uses minimal queries (10 items); rate-limit headers respected; staggered smoke runs |

---

## 18. Non-Goals

This plan explicitly **excludes**:

| Non-Goal | Reason |
|----------|--------|
| Implementing the Product Hunt connector | This is a plan, not implementation |
| Making live Product Hunt API calls | Prohibited during planning; no live calls in any validation |
| Scraping producthunt.com | Prohibited; GraphQL API only |
| Enabling Product Hunt by default | `default_enabled` stays `false` |
| Adding Product Hunt to the default weekly run | Prohibited until controlled smoke passes + founder approval |
| Modifying `config/source_registry.json` | Registry changes require separate authorization |
| Modifying `src/`, `tests/`, `scripts/` | No code changes in this item |
| Creating fixture files | Implementation concern; not in planning item |
| LLM-based extraction or classification | Not in v2.11 scope for source planning |
| Setting up OAuth credentials or API keys | Not in planning scope |
| Treating Product Hunt launches as validated demand | Product Hunt is a solution-pattern source; launches are not validated demand signals |
| Comment fetching and enrichment | Deferred; product description only in initial implementation |
| Full-text reproduction of product descriptions or comments | Reasonable excerpting only |
| Real-time product launch monitoring | Out of scope for v2.11 |
| Cross-source deduplication | Handled downstream, not in Product Hunt adapter |

---

## 19. Recommendation

**Implement Product Hunt as a fixture-only connector in a later roadmap item, only after explicit founder approval.**

Specific recommendations:

1. **Start with fixture-only connector.** All tests use pre-saved GraphQL response fixtures. No live API calls in unit tests.
2. **Treat as solution-pattern source.** Classify Product Hunt evidence as `product_launch`, `solution_pattern`, or `market_trend`. Do not treat as `pain_signal_candidate` without comment corroboration.
3. **Do not include in default weekly run.** Keep `default_enabled: false` until sustained smoke evidence and founder approval.
4. **Do not treat Product Hunt launches as validated demand.** A Product Hunt launch indicates what someone built, not what the market demands. Downstream classification must account for this.
5. **Implement anti-hype filters from day one.** Launch hype, self-promotion, generic AI claims, and shallow tagline-only records must be flagged.
6. **Defer comment fetching.** Product description is sufficient for initial implementation. Comments add complexity and cost without proportionate signal gain for solution-pattern detection.
7. **Align with source registry and contracts.** `source_id: "product_hunt"`, `source_type: "product_launch"`, `source_url: "https://www.producthunt.com/products/{slug}"`, `evidence_kind` on every record.

---

## 20. Decision

**v2.11 item 6 creates the Product Hunt Feasibility and Connector Plan only.**

- No implementation of any Product Hunt connector, adapter, collector, or related code is authorized by this plan.
- No live Product Hunt API calls are authorized by this plan.
- No fixture files are created or modified by this plan.
- No source code, tests, scripts, or artifacts are modified by this plan.
- No registry status changes are authorized by this plan.
- The plan documents the feasibility assessment, API/auth/rate-limit findings, current-state assessment, raw evidence mapping, evidence kind classification heuristics, anti-hype filter design, source URL traceability strategy, deduplication plan, query/collection strategy, validation plan, controlled smoke design, and implementation sequence.
- Product Hunt implementation remains unauthorized. A future roadmap item (on a separate branch, with explicit founder approval) may implement the connector described in this plan.
- The next step after this plan is item 7 (pimenov.ai Feasibility and Connector Plan), which is a similar planning-only item.

---

## 21. References

- [`docs/contracts/discovery_source_adapter_contract.md`](../contracts/discovery_source_adapter_contract.md) — Section 8.3 (Product Hunt-specific adapter expectations)
- [`docs/contracts/raw_evidence_artifact_schema.md`](../contracts/raw_evidence_artifact_schema.md) — Sections 5–7 (field mapping, evidence kinds, source types), Section 19 (Product Hunt metadata example)
- [`docs/contracts/source_allowlist_policy.md`](../contracts/source_allowlist_policy.md) — Section 7.1.3 (Product Hunt registry entry)
- [`docs/contracts/source_url_traceability_contract.md`](../contracts/source_url_traceability_contract.md) — Section 5 (placeholder URN policy)
- [`config/source_registry.json`](../../config/source_registry.json) — Product Hunt entry: `source_id: product_hunt`, `source_type: product_launch`, `status: feasibility_required`
- [`docs/decisions/hacker_news_connector_hardening_plan.md`](../decisions/hacker_news_connector_hardening_plan.md) — HN hardening plan (structural reference)
- [`docs/decisions/github_issues_connector_hardening_plan.md`](../decisions/github_issues_connector_hardening_plan.md) — GitHub Issues hardening plan (structural reference)
- [`docs/roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md`](../roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md) — Item 6 definition
- Product Hunt API v2 docs: `https://api.producthunt.com/v2/docs`
- Product Hunt rate limits: `https://api.producthunt.com/v2/docs/rate_limits/headers`
- Product Hunt OAuth client credentials: `https://api.producthunt.com/v2/docs/oauth_client_only_authentication/oauth_test_use_the_client_level_token_for_read_api_access`

---

*Product Hunt Feasibility and Connector Plan. v2.11 item 6. Feasibility plan finalized / implementation pending.*
