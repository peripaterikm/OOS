# Discovery Source Adapter Contract

**Version:** discovery_source_adapter.v1
**Roadmap:** v2.11 item 1
**Status:** Contract finalized / implementation pending
**Depends on:**
- [`source_url_traceability_contract.md`](source_url_traceability_contract.md) (v2.7 item 1.1)
**Precedes:**
- Roadmap v2.11 item 2 — Raw Evidence Artifact Schema
- Roadmap v2.11 items 4–7 — Source-specific hardening and feasibility plans

---

## 1. Scope

### 1.1 What a Discovery Source Adapter Is

A **discovery source adapter** is a deterministic connector boundary that converts one external source into raw evidence records consumable by the OOS pipeline. It is the single point of contact between the outside world and the OOS processing pipeline.

An adapter:

- Converts exactly one external source into `RawEvidence` records.
- Operates deterministically — same input configuration yields identical output in fixture mode.
- Does **not** create [`OpportunityCard`](../vision.md), [`CandidateSignal`](../../src/oos/models.py), or any downstream pipeline artifact directly.
- Does **not** make founder decisions, portfolio transitions, or signal validity judgments.
- Does **not** call LLMs by default.
- Does **not** use live APIs in unit tests.

### 1.2 What an Adapter Must Produce

Every adapter invocation must yield:

1. A list of [`RawEvidence`](../../src/oos/models.py:77) records — one per source item fetched.
2. A source quality summary reporting counts, errors, warnings, and metadata about the fetch session.
3. Explicit errors or warnings when any item cannot be converted.

### 1.3 Relationship to the Pipeline

```
┌──────────────────────┐      ┌──────────────────┐      ┌──────────────────────┐
│  External Source     │ ──── │  Source Adapter   │ ──── │  RawEvidence Records │
│  (API, RSS, file)    │      │  (this contract)  │      │  (→ item 2 schema)   │
└──────────────────────┘      └──────────────────┘      └──────────┬───────────┘
                                                                    │
                                                    ┌───────────────▼───────────┐
                                                    │  Evidence Classifier /     │
                                                    │  Candidate Signal Extractor│
                                                    │  (existing pipeline)       │
                                                    └───────────────────────────┘
```

Adapters are **upstream boundary components**. They feed the pipeline; they do not drive it.

---

## 2. Non-Goals

This contract explicitly excludes:

- Broad web scraping (each source must have a defined, narrow access method).
- Reddit, review sites, job boards, LinkedIn, X/Twitter, Telegram implementation in v2.11.
- Database or persistent server architecture.
- UI or dashboard work.
- Autonomous founder decisions.
- Replacing existing signal scoring in [`src/oos/signal_scoring.py`](../../src/oos/signal_scoring.py).
- Live API calls in unit tests.
- LLM-based extraction in default validation.
- Stack Overflow / Q&A sites, app marketplaces, newsletters (deferred to v2.12+).

---

## 3. Adapter Lifecycle

Every source adapter must implement these seven phases:

### Phase 1: Discover / Fetch

Retrieve raw items from the external source using the configured access method (API endpoint, RSS feed, static file, sitemap allowlist). No LLM processing. No scoring. Just raw data retrieval.

### Phase 2: Normalize

Convert each raw source item into an internal normalized structure that maps to [`RawEvidence`](../../src/oos/models.py:77) fields. Field mapping must be explicit and inspectable — no opaque transformations.

### Phase 3: Validate

Validate that:
- Every item has a stable, non-placeholder `source_url`.
- All required [`RawEvidence`](../../src/oos/models.py:77) fields are populated.
- `content_hash` matches normalized title/body content (per existing contract in [`compute_raw_evidence_content_hash`](../../src/oos/models.py:35)).
- `author_or_context` does not expose private handles (per [`author_or_context_is_private_safe`](../../src/oos/models.py:40)).

### Phase 4: Deduplicate

Detect and remove duplicate raw evidence records within the same fetch session. Deduplication uses `content_hash` equivalence. The first occurrence is retained. Duplicates are reported with explicit reason.

### Phase 5: Persist

Write raw evidence records as structured artifacts. The exact artifact format is defined in item 2 (Raw Evidence Artifact Schema). Adapters must be able to output to the artifact store but do not own the schema.

### Phase 6: Convert to Candidate Signals (Later Pipeline Stage)

Adapters do **not** perform this conversion. The conversion from [`RawEvidence`](../../src/oos/models.py:77) to [`CandidateSignal`](../../src/oos/models.py) happens downstream in the existing [`CandidateSignalExtractor`](../../src/oos/candidate_signal_extractor.py). Adapters must ensure their output is compatible with this downstream stage.

### Phase 7: Report Source Quality

Every adapter invocation must produce a source quality summary containing:
- `source_id`
- `source_type`
- `items_fetched` — total raw items retrieved
- `items_converted` — successfully converted to RawEvidence
- `items_dropped` — items excluded with explicit reasons
- `items_duplicate` — duplicates detected within session
- `errors` — list of error descriptions
- `warnings` — list of warning descriptions
- `fetch_mode` — `fixture` | `dry_run` | `live_opt_in`

---

## 4. Adapter Interface (Conceptual)

This section defines the adapter's **implementation-facing concepts**. It does not prescribe a specific Python class, method signature, or module path. The actual implementation interface is defined in item 2 and later implementation items.

### 4.1 Identity

| Field | Description | Example |
|-------|-------------|---------|
| `source_id` | Stable, unique machine identifier | `hacker_news_algolia` |
| `source_type` | Category of source (see Section 8) | `discussion` |
| `source_name` | Human-readable label | `Hacker News Algolia` |

### 4.2 Fetch Mode

Every adapter must support three fetch modes:

| Mode | Behavior | Network Calls? | Used In |
|------|----------|---------------|---------|
| `fixture` | Read from local fixture files | No | Unit tests, deterministic validation |
| `dry_run` | Validate configuration without fetching | No | Configuration checks, pre-smoke validation |
| `live_opt_in` | Connect to the live external source | Yes, only with explicit opt-in | Controlled smoke tests, approved live runs |

Defaults:
- Adapters default to `fixture` mode.
- Live mode requires an explicit CLI flag or configuration toggle.
- No adapter may silently fall back from live to fixture mode without logging the fallback reason.

### 4.3 Input Configuration

Each adapter accepts:

| Parameter | Description |
|-----------|-------------|
| `source_id` | Which source this adapter targets |
| `query_kind` | What kind of query to run (search, top, new, by-tag, etc.) |
| `topic_id` | The pipeline topic driving this fetch |
| `fetch_mode` | `fixture` / `dry_run` / `live_opt_in` |
| `fixture_path` | Path to fixture file (required in fixture mode) |
| `auth_token_env_var` | Environment variable name for API key/token (never the token itself) |
| `rate_limit_config` | Max requests per window, window duration, retry policy |

### 4.4 Output

Every adapter invocation returns:

1. **`list[RawEvidence]`** — converted and validated evidence records.
2. **Source Quality Summary** — as defined in Section 3, Phase 7.
3. **Errors/Warnings** — explicit, structured messages for every problem encountered.

### 4.5 Errors and Warnings

Errors are blocking: the adapter cannot continue or the output is incomplete.
Warnings are non-blocking: the adapter continues but notes the issue.

| Condition | Classification |
|-----------|---------------|
| Fixture file not found | Error |
| Fixture file malformed (invalid JSON) | Error |
| Live API returns 5xx after retries exhausted | Error |
| Live API auth failure (401/403) | Error |
| Live API rate limit hit, retry failed | Error |
| Source item missing required field (e.g., no `source_url`) | Warning (item dropped) |
| Duplicate content_hash detected | Warning (item deduplicated) |
| Live API returns 429 with Retry-After (honored) | Warning (delay recorded) |
| Source item truncated at max length | Warning |
| Non-critical metadata field missing | Warning |

---

## 5. Required Adapter Behavior

Every adapter **must** satisfy the following behavioral requirements:

### 5.1 Deterministic Output

- Fixture mode output must be deterministic: same fixture file, same configuration → identical `list[RawEvidence]` (with identical `content_hash` values for each record).
- No random ordering, no timestamp-based non-determinism (except `collected_at` which may differ in live mode).
- Test fixtures must produce identical output across operating systems (Windows/Unix line-ending differences must be handled).

### 5.2 Stable `source_url`

- Every `RawEvidence` record must carry a stable, real `source_url`.
- Stable means: the URL resolves to the same conceptual resource across time. Query parameters that change result ordering are acceptable; parameters that change resource identity are not.
- No `urn:oos:*` placeholder URLs. Ever. Per [`source_url_traceability_contract.md`](source_url_traceability_contract.md) Section 5.
- `source_url` must use `http://` or `https://` scheme.
- The URL must be the canonical, direct link to the source item — not a search result page, not a proxy.

### 5.3 Source URL Traceability

- `source_url` is mandatory and non-negotiable.
- Every item that cannot produce a `source_url` must be dropped with an explicit reason.
- No silent drops without reason — every excluded item must appear in the source quality summary with a `drop_reason`.

### 5.4 Explicit `source_id`

- Every adapter must declare its `source_id` as a constant.
- The `source_id` appears in every `RawEvidence.source_id` field produced by that adapter.
- No adapter may use a different `source_id` depending on runtime conditions.

### 5.5 No Silent Drops

- Every source item that fails conversion must be reported with:
  - The item's identifying information (enough to locate it in the source).
  - The reason for the drop.
  - Whether the drop was due to validation failure, missing fields, or other causes.
- The drop count and reasons appear in the source quality summary.

### 5.6 No Live Network Calls in Unit Tests

- Adapter unit tests must use `fixture` mode exclusively.
- Tests that require live data must be gated behind explicit `live_opt_in` configuration and must not run in the default test suite.
- Network mocking (e.g., `unittest.mock`, `responses`, `httpx_mock`) is acceptable for simulating live behavior in tests, provided the mocked responses are deterministic fixtures themselves.

### 5.7 Rate Limit Awareness

- Live mode adapters must read and respect:
  - `Retry-After` header
  - `X-RateLimit-Remaining` / `X-RateLimit-Reset` headers (where available)
  - Source-specific rate limit documentation
- Adapters must implement exponential backoff for transient failures.
- Rate limit exhaustion must be reported as a warning with the retry delay used.

### 5.8 Explicit Failure Reporting

- All adapter failures must be observable and reportable.
- Failures must surface through the source quality summary.
- Stack traces alone are not sufficient — failures must be translated into structured error messages.
- Transient failures (network timeouts, 5xx responses) and permanent failures (auth errors, 404) must be distinguished.

### 5.9 Raw Source Data Traceability

- The adapter must preserve enough raw source data for audit.
- For each `RawEvidence` record, the `raw_metadata` field must include source-specific identifying information (e.g., HN `objectID`, GitHub issue number, Product Hunt product ID).
- This allows downstream debugging: "what source item produced this evidence record?"

---

## 6. Raw Evidence Record Handoff

### 6.1 What the Adapter Outputs

Each adapter invocation produces records mapping to the existing [`RawEvidence`](../../src/oos/models.py:77) model. The adapter must populate these fields:

| Field | Required? | Description | Source |
|-------|-----------|-------------|--------|
| `evidence_id` | **Required** | Unique within the source; deterministic from source item ID | Derived from source item ID (e.g., `raw_hn_{objectID}`) |
| `source_id` | **Required** | The adapter's `source_id` constant | Adapter constant |
| `source_type` | **Required** | Source category (see Section 8) | Adapter constant |
| `source_name` | **Required** | Human-readable source label | Adapter constant |
| `source_url` | **Required** | Stable, canonical URL to the source item | Derived from source item data |
| `collected_at` | **Required** | ISO 8601 timestamp of fetch (or source item's timestamp) | Source item or fetch time |
| `title` | **Required** | Source item title; must be non-empty | Source item field |
| `body` | **Required** | Source item body, summary, or excerpt; must be non-empty | Source item field |
| `language` | **Required** | Language code or `"unknown"` | Source metadata or default |
| `topic_id` | **Required** | Pipeline topic driving this fetch | Input configuration |
| `query_kind` | **Required** | Query type for this fetch | Input configuration |
| `content_hash` | **Required** | SHA-256 of `normalize_raw_evidence_content(title, body)` | Computed |
| `author_or_context` | **Required** | Role/context label (NOT username/handle) | Derived per privacy policy |
| `raw_metadata` | **Required** | Dict of source-specific metadata | Source item fields |
| `access_policy` | **Required** | Policy label describing access method | Adapter constant |
| `collection_method` | **Required** | `fixture` / `live_opt_in` / `dry_run` | Current fetch mode |

### 6.2 Optional / Source-Specific Metadata

The `raw_metadata` dict carries source-specific fields. These include:

| Metadata Field | Applicable Sources | Description |
|----------------|-------------------|-------------|
| `objectID` | Hacker News | HN Algolia object ID |
| `created_at` | All | Original creation timestamp from source |
| `points` | HN, Product Hunt | Score / upvotes / votes |
| `num_comments` | HN, GitHub Issues | Comment count |
| `tags` | All | Source-specific tags or topics |
| `original_url` | All | External URL the item points to (if different from `source_url`) |
| `author_present` | All | Boolean: does the source report an author? |
| `query_plan_id` | All | Reference to the query plan that triggered this fetch |
| `dedup_key` | All | Key used for deduplication |
| `issue_number` | GitHub Issues | Issue number in the repository |
| `repo` | GitHub Issues | Repository full name (owner/repo) |
| `labels` | GitHub Issues | Issue labels |
| `state` | GitHub Issues | Issue state (open/closed) |
| `product_id` | Product Hunt | Product identifier |
| `topics` | Product Hunt | Product topics |
| `makers` | Product Hunt | Maker names (roles only, not personal handles) |
| `section` | pimenov.ai | Site section (blog, cases, kb) |

### 6.3 Quality Flags

The adapter may set quality flags in `raw_metadata`:

| Flag | Meaning |
|------|---------|
| `truncated` | Body was truncated to max length |
| `language_uncertain` | Language detection confidence below threshold |
| `missing_author` | Source reports no author information |
| `low_score` | Source item score below configured threshold |
| `old_item` | Source item date older than configured recency threshold |

---

## 7. Source Categories

Every adapter belongs to one of these categories. The `source_type` field in [`RawEvidence`](../../src/oos/models.py:77) must match one of these values:

### 7.1 Discussion Source

- **Description:** Public discussion forums where users post about problems, ask for help, or debate solutions.
- **Example:** Hacker News
- **Signal type expected:** User-reported pains, workflow frustrations, tool complaints, "I wish X existed" posts.
- **Noise risk:** High — many posts are opinion, entertainment, or meta-discussion without pain signal.
- **Filtering strategy:** Score thresholds, topic-based query narrowing, off-topic keyword exclusion.

### 7.2 Issue Tracker Source

- **Description:** Public issue trackers where users report bugs, request features, or describe workarounds.
- **Example:** GitHub Issues
- **Signal type expected:** Bug reports, feature requests, workaround descriptions, integration pain points.
- **Noise risk:** Medium — many issues are low-impact, already-fixed, or specific to a single repo's implementation.
- **Filtering strategy:** Repo allowlist, keyword queries on pain/workaround terms, label-based filtering, PR exclusion.

### 7.3 Product Launch / Solution Pattern Source

- **Description:** Platforms where products are launched and discussed, revealing what problems founders are targeting.
- **Example:** Product Hunt
- **Signal type expected:** Product descriptions, launch patterns, maker commentary — reveals solution-pattern trends, not raw pain.
- **Noise risk:** High — promotional content, hype, products with no real traction.
- **Filtering strategy:** Anti-hype scoring (vote velocity vs quality), comment substance measurement, maker reputation signals.

### 7.4 Curated Expert / Context Source

- **Description:** Curated, expert-authored content about industry trends, use-cases, and implementations.
- **Example:** pimenov.ai
- **Signal type expected:** Trend awareness, idea expansion context, AI use-case patterns — not raw pain signals.
- **Noise risk:** Low (curated) but signal type is different — more context than pain.
- **Filtering strategy:** Section allowlist (only specific content areas), recency threshold, topic tagging.

### 7.5 Deferred Risky Sources

The following source categories are **excluded from v2.11** and deferred to v2.12+:

- Review sites (G2, Capterra, etc.) — ToS risk, scraping barriers.
- Job boards (LinkedIn, Indeed, etc.) — ToS barriers, structured data access unclear.
- Social media (Reddit, Twitter/X, Telegram) — API changes, legal review required.
- Q&A sites (Stack Overflow) — Signal type fit needs analysis.
- App marketplaces (Google Play, App Store) — Review-based signals, scraping risk.
- Newsletters / media bundles — Ingest complexity, copyright considerations.

---

## 8. Source-Specific Adapter Expectations

This section defines expectations for the four v2.11 source candidates. **No implementation is authorized by this item.** Implementation requires later roadmap items and explicit founder approval.

### 8.1 Hacker News

| Aspect | Specification |
|--------|--------------|
| **Adapter status** | Existing collector in [`src/oos/hn_algolia_collector.py`](../../src/oos/hn_algolia_collector.py) |
| **`source_id`** | `hacker_news_algolia` |
| **`source_type`** | `discussion` |
| **Access method** | Algolia Search API (`hn.algolia.com/api/v1`) |
| **Expected signal type** | User-reported pains, workflow frustrations, "Ask HN" / "Show HN" posts |
| **Required fields** | `objectID` → `evidence_id`, `source_url` = `https://news.ycombinator.com/item?id={objectID}` |
| **Traceability** | Every item must map to `https://news.ycombinator.com/item?id={objectID}` |
| **Risk notes** | Rate limit: 10,000 requests/hour (Algolia); comment-only posts may have low signal; "Launch HN" is promotional |
| **Implementation authorized?** | **No.** This item defines the contract only. Hardening plan is item 4. |

### 8.2 GitHub Issues

| Aspect | Specification |
|--------|--------------|
| **Adapter status** | Existing collector in [`src/oos/github_issues_collector.py`](../../src/oos/github_issues_collector.py) |
| **`source_id`** | `github_issues` |
| **`source_type`** | `issue_tracker` |
| **Access method** | GitHub REST API (`api.github.com`) |
| **Expected signal type** | Bug reports, feature requests, workaround descriptions, integration pain |
| **Required fields** | `issue_number`, `repo` (owner/repo) → `source_url` = `https://github.com/{repo}/issues/{number}` |
| **Traceability** | Every item must map to `https://github.com/{owner}/{repo}/issues/{issue_number}` |
| **Risk notes** | Rate limit: 5,000 requests/hour (authenticated); PRs must be excluded from issue results; closed issues may be stale |
| **Implementation authorized?** | **No.** This item defines the contract only. Hardening plan is item 5. |

### 8.3 Product Hunt

| Aspect | Specification |
|--------|--------------|
| **Adapter status** | **Does not exist.** Feasibility and connector plan is item 6. |
| **`source_id`** | `product_hunt` (proposed) |
| **`source_type`** | `product_launch` |
| **Access method** | Product Hunt GraphQL API (proposed) |
| **Expected signal type** | Solution-pattern signals: what products are being built, which problems founders target, launch trends |
| **Required fields** | `product_id` → `evidence_id`, `source_url` = `https://www.producthunt.com/products/{slug}` |
| **Traceability** | Every item must map to a product page URL on producthunt.com |
| **Risk notes** | GraphQL API auth requirements TBD; anti-hype filters needed; signal is solution-pattern, not pain — downstream classification must account for this |
| **Implementation authorized?** | **No.** This item defines the contract only. Feasibility plan is item 6. |

### 8.4 pimenov.ai

| Aspect | Specification |
|--------|--------------|
| **Adapter status** | **Does not exist.** Feasibility and connector plan is item 7. |
| **`source_id`** | `pimenov_ai` (proposed) |
| **`source_type`** | `curated_context` |
| **Access method** | RSS feed / sitemap / static page allowlist (proposed; no broad scraping) |
| **Expected signal type** | AI use-case patterns, trend context, idea-expansion evidence — not raw pain |
| **Required fields** | Page URL → `source_url`, title, section/category, publication date (if available) |
| **Traceability** | Every item must map to a specific page URL on pimenov.ai |
| **Risk notes** | Russian-language content (UTF-8 encoding required); curation bias; update frequency unknown; no broad scraping |
| **Implementation authorized?** | **No.** This item defines the contract only. Feasibility plan is item 7. |

---

## 9. Validation and Testing Policy

### 9.1 Fixture-First Testing

- All adapter unit tests **must** use fixture mode (`fetch_mode = fixture`).
- Fixture files must be deterministic: same fixture file produces identical test output every time.
- Fixture files must be checked into the repository (under `tests/` or a dedicated fixtures directory).
- Fixture files must not contain secrets, API keys, or personally identifiable information (PII).

### 9.2 Live API Call Policy

- **Live API calls are forbidden in unit tests.** Tests that would require live network access must be skipped in the default test suite.
- Controlled smoke tests may use `live_opt_in` mode but only after explicit founder approval.
- The `live_opt_in` toggle must be a distinct CLI flag or configuration value, not a default behavior.

### 9.3 Fixture Snapshots

- Fixture snapshots must be deterministic.
- Fixtures should be representative of real source data (not synthetic, minimal examples).
- Fixture files must be versioned alongside the adapter code.
- Tests must validate that fixture output is identical between runs (snapshot testing pattern).

### 9.4 Required Test Coverage

Every adapter must have tests covering:

| Test Case | What It Validates |
|-----------|-------------------|
| Fixture loads without error | Adapter can read and parse fixture inputs |
| Every output record has a stable `source_url` | No placeholders, no missing URLs |
| `source_url` format matches expected pattern | `http://` or `https://` scheme, valid hostname |
| `content_hash` matches normalized content | `validate()` passes on all records |
| `author_or_context` is privacy-safe | No username/handle leakage |
| Duplicate items are deduplicated | Duplicates detected and reported |
| Missing required fields produce warnings | Items dropped with explicit reason |
| Fixture file not found produces error | Error surfaced in quality summary |
| Malformed fixture produces error | Error surfaced, no partial output |
| All required `RawEvidence` fields are populated | Validation passes for every output record |

### 9.5 Failure Case Testing

Adapters must test these failure scenarios:

- Fixture file not found.
- Fixture file with invalid JSON.
- Fixture with item missing `source_url`.
- Fixture with item having empty title or body.
- Fixture with duplicate items.
- Fixture with malformed source URL.
- Live mode (mocked): API returning 5xx.
- Live mode (mocked): API returning 429 with `Retry-After`.
- Live mode (mocked): API returning 401/403 (auth failure).

---

## 10. Risk Gates

The following gates apply to every source adapter. An adapter that cannot satisfy any gate must remain `inactive` in the source registry.

| # | Gate | Applies To |
|---|------|------------|
| **G1** | No source without stable `source_url` | Every adapter |
| **G2** | No connector without deterministic fixture tests | Every adapter |
| **G3** | No live API calls in unit tests | All tests |
| **G4** | No scraping if ToS/robots risk is unclear | Every new source |
| **G5** | No default weekly run inclusion until controlled smoke passes | Source registry `status: active` |
| **G6** | No source accepted if noise rate is too high and no filter exists | Source quality scoring |
| **G7** | No source without defined rate-limit and auth policy | Every adapter |
| **G8** | No source that cannot produce valid `RawEvidence` with `source_url` | Every adapter |

These gates are identical to the risk gates in [`OOS_roadmap_v2_11_discovery_sources_checklist.md`](../roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md#risk-gates).

---

## 11. Artifact Integration Boundaries

This contract defines the **adapter boundary**. Adapter output feeds into downstream components. The boundaries between components are:

### 11.1 Adapter Contract (this document)

- Defines how a source becomes raw evidence records.
- Covers: fetch mode, field mapping, validation, deduplication, errors, quality summary.
- **Does not** define: final JSON schema, artifact storage format, downstream processing rules.

### 11.2 Raw Evidence Artifact Schema (item 2)

- Defines the canonical JSON schema for persisted raw evidence artifacts.
- All adapters must produce output compatible with this schema.
- The schema document (to be created in item 2) is authoritative for field names, types, and validation rules for persisted artifacts.

### 11.3 Source Registry (item 3)

- Defines the canonical list of approved sources and their configuration.
- Adapters use the registry to discover their configuration.
- The registry gates which sources participate in the default weekly run.

### 11.4 Signal Normalization (existing pipeline)

- The existing [`CandidateSignalExtractor`](../../src/oos/candidate_signal_extractor.py) converts `RawEvidence` records into `CandidateSignal` objects.
- Adapters feed this pipeline but do not control it.

### Boundary Diagram

```
┌─────────────────────────────┐
│  Source Registry (item 3)   │  ← lists approved sources, status, config
└──────────┬──────────────────┘
           │ references
           ▼
┌─────────────────────────────┐
│  Adapter Contract (item 1)  │  ← this document
│  ┌───────────────────────┐  │
│  │  HN Adapter           │  │
│  │  GitHub Issues Adapter│  │
│  │  Product Hunt Adapter │  │
│  │  pimenov.ai Adapter   │  │
│  └───────────┬───────────┘  │
└──────────────┼──────────────┘
               │ produces
               ▼
┌─────────────────────────────┐
│  Raw Evidence Schema        │  ← item 2: canonical JSON format
│  (item 2)                   │
└──────────┬──────────────────┘
           │ feeds
           ▼
┌─────────────────────────────┐
│  Evidence Classifier /      │  ← existing pipeline
│  Candidate Signal Extractor │
└─────────────────────────────┘
```

---

## 12. Git / Validation Discipline

### 12.1 Environment

- **Windows-native.** All development, testing, and validation must work on Windows with PowerShell.
- **No WSL/Linux-first assumptions.**
- **Python venv** for dependency isolation.

### 12.2 Script Wrappers

Use only the approved wrapper scripts for validation:

```
.\scripts\dev-git-check.ps1
.\scripts\dev-test.ps1
.\scripts\run-controlled-smoke.ps1
.\scripts\dev-validate-final.ps1
```

### 12.3 Prohibited Patterns

- **No chained shell commands** for validation. Each validation step uses a single wrapper script.
- **No live APIs/LLMs in tests.**
- **No `urn:oos:*` placeholders** anywhere in source URLs.
- **No secret commits** — no `.env`, no API keys, no tokens in versioned files.

### 12.4 Commit Discipline

- One local commit per v2.11 roadmap item.
- Always run `.\scripts\dev-git-check.ps1` after each item completion.
- Push/PR/merge/tag only when explicitly requested.

---

## 13. Future Work

The following implementation items are planned but **not authorized** by this contract:

### 13.1 HN Connector Hardening (item 4)

- Assessment of current implementation quality.
- Coverage gap analysis (comments, Ask HN, Show HN, Launch HN).
- `source_url` traceability audit.
- Noise filter recommendations.
- Rate-limit compliance review.
- **Implementation: not authorized by item 1.**

### 13.2 GitHub Issues Connector Hardening (item 5)

- PR filtering effectiveness assessment.
- Repo allowlist coverage review.
- Keyword search quality evaluation.
- Label/comment/state capture completeness audit.
- Rate-limit/auth policy review.
- **Implementation: not authorized by item 1.**

### 13.3 Product Hunt Feasibility Plan (item 6)

- API assessment (GraphQL availability, auth, rate limits).
- Data model mapping to `RawEvidence`.
- Anti-hype scoring design.
- Fixture strategy.
- **Implementation: not authorized by item 1.**

### 13.4 pimenov.ai Feasibility Plan (item 7)

- Site structure analysis.
- Access method recommendation (RSS/sitemap/static).
- Language handling strategy.
- Fixture strategy.
- **Implementation: not authorized by item 1.**

### 13.5 Source Quality Scoring (item 8)

- Quality dimensions: `signal_relevance_score`, `noise_rate`, `traceability_compliance`, `yield_consistency`.
- Scoring formula (deterministic).
- Thresholds: `healthy`, `warning`, `unhealthy`.
- **Implementation: not authorized by item 1.**

### 13.6 Controlled Discovery Smoke (item 9)

- Smoke test design: fixture load → dry-run → traceability check → noise measurement → pass/fail.
- Gating new sources before default weekly run.
- **Implementation: not authorized by item 1.**

---

## 14. Decision

**v2.11 item 1 creates the adapter contract only.**

- No source implementation is authorized by this item.
- No connector, collector, or adapter code may be written under the authority of this contract.
- No fixtures may be created or modified under the authority of this contract.
- No tests may be modified under the authority of this contract.
- Implementation of source adapters requires later roadmap items and explicit founder approval.
- The contract defines the standard; it does not enforce it in code.

---

## 15. Self-Audit

| Question | Answer |
|----------|--------|
| Did this avoid implementation? | **Yes.** Contract/advisory only. No `.py` files modified. |
| Did this avoid source/test changes? | **Yes.** No source, test, script, or example files changed. |
| Did this define the adapter lifecycle? | **Yes.** Section 3 defines 7 phases. |
| Did this define the adapter interface? | **Yes.** Section 4 defines identity, fetch modes, input config, output, and error classification. |
| Did this define required behaviors? | **Yes.** Section 5 defines 9 mandatory behaviors. |
| Did this define raw evidence handoff? | **Yes.** Section 6 maps all fields with required/optional classification. |
| Did this define source categories? | **Yes.** Section 7 defines 5 categories (4 active + 1 deferred). |
| Did this cover source-specific expectations? | **Yes.** Section 8 covers HN, GitHub Issues, Product Hunt, and pimenov.ai. |
| Did this define testing policy? | **Yes.** Section 9 covers fixture-first, live-call prohibition, snapshot, required coverage, and failure cases. |
| Did this define risk gates? | **Yes.** Section 10 defines 8 gates matching the roadmap. |
| Did this define artifact integration boundaries? | **Yes.** Section 11 maps adapter → schema → registry → signal normalization. |
| Did this reference `source_url_traceability_contract.md`? | **Yes.** Sections 5.2 and 10. |
| Did this respect the non-goals? | **Yes.** No scraping, no Reddit/X/LinkedIn/Telegram, no live API, no LLM, no UI, no DB. |
| Did this state that implementation is not authorized? | **Yes.** Sections 8, 13, and 14 explicitly state no implementation. |
| Did this avoid defining final JSON schema? | **Yes.** Deferred to item 2 (Section 11.2). |
| Did this state Windows-native and PowerShell wrapper requirements? | **Yes.** Section 12. |
| Did this avoid live APIs/LLMs in validation? | **Yes.** No API/LLM calls were made. |

---

*Discovery Source Adapter Contract. v2.11 item 1. Contract finalized / implementation pending.*
