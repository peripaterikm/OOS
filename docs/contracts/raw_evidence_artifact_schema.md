# Raw Evidence Artifact Schema

**Version:** raw_evidence_artifact_schema.v1
**Roadmap:** v2.11 item 2
**Status:** Schema finalized / implementation pending
**Depends on:**
- [`discovery_source_adapter_contract.md`](discovery_source_adapter_contract.md) (v2.11 item 1)
- [`source_url_traceability_contract.md`](source_url_traceability_contract.md) (v2.7 item 1.1)
**Precedes:**
- Roadmap v2.11 item 3 — Source Registry and Source Allowlist Policy
- Roadmap v2.11 items 4–7 — Source-specific hardening and feasibility plans

---

## 1. Scope

### 1.1 What Raw Evidence Is

**Raw Evidence** is the normalized, pre-signal artifact produced by discovery source adapters. It is the first stable artifact in the OOS pipeline — the point at which external source data becomes a structured, traceable, and validatable record inside the system.

Raw Evidence is **not yet**:
- A validated [`CandidateSignal`](../../src/oos/models.py)
- An [`OpportunityCard`](../vision.md) or [`OpportunityCandidate`](../../src/oos/models.py)
- A founder decision or portfolio state
- An LLM-generated synthesis, classification, or summary
- A pipeline-driven signal extraction

Raw Evidence is:
- A deterministic, schema-conformant JSON artifact.
- The handoff boundary between source adapters and the downstream pipeline.
- The first point at which `source_url` traceability is enforced per [`source_url_traceability_contract.md`](source_url_traceability_contract.md).
- Stored as structured file-system artifacts under `artifacts/discovery/`.

### 1.2 What This Schema Defines

This document defines:
1. The canonical JSON structure for a **Raw Evidence Artifact** (a batch of `RawEvidence` records from one discovery run).
2. The canonical JSON structure for a **Raw Evidence Index** (a registry of all discovery runs).
3. The field schemas for individual `RawEvidence` records, compatible with the existing [`RawEvidence`](../../src/oos/models.py:77) dataclass.
4. Validation rules, ID generation rules, deduplication policy, quality flags, and fixture policies.

### 1.3 What This Schema Does NOT Define

- Adapter implementation interfaces (those are in item 1).
- Source registry / allowlist policy (that is item 3).
- Downstream signal extraction or classification (existing pipeline).
- Database schemas, API endpoints, or server storage.
- LLM prompt templates or extraction logic.

---

## 2. Relationship to the Adapter Contract

### 2.1 Position in the Pipeline

```
┌─────────────────────────────┐
│  Source Adapter (item 1)    │  ← produces RawEvidence records
│  HN / GitHub / PH / pimenov │
└──────────┬──────────────────┘
           │ outputs
           ▼
┌─────────────────────────────┐
│  Raw Evidence Artifact      │  ← this document: canonical JSON format
│  (item 2)                   │
└──────────┬──────────────────┘
           │ feeds
           ▼
┌─────────────────────────────┐
│  Evidence Classifier /      │  ← existing pipeline
│  Candidate Signal Extractor │
└─────────────────────────────┘
```

### 2.2 Division of Responsibility

| Concern | Owned By | Document |
|---------|----------|----------|
| Adapter interface, lifecycle, fetch modes | Item 1 | [`discovery_source_adapter_contract.md`](discovery_source_adapter_contract.md) |
| Canonical JSON artifact schema, validation rules, ID policy | Item 2 | This document |
| Source registry, allowlist, status gating | Item 3 | `source_allowlist_policy.md` (future) |
| Source-specific field mappings (HN, GitHub, PH, pimenov) | Items 4–7 | Respective hardening/feasibility plans |
| Downstream signal extraction | Existing pipeline | [`candidate_signal_extractor.py`](../../src/oos/candidate_signal_extractor.py) |

### 2.3 Handoff Contract

Adapters produce `list[RawEvidence]`. This schema defines the JSON artifact that wraps that list for persistence. The adapter contract (Section 6) specifies the fields each adapter must populate on each `RawEvidence` record. This schema specifies how those records are serialized, validated, indexed, and stored as artifacts.

Adapters do not own the artifact format. They must produce records compatible with this schema, but the schema is authoritative for field names, types, and validation rules for persisted artifacts.

---

## 3. Artifact Location and Naming

### 3.1 Proposed Artifact Paths

```
artifacts/discovery/
├── raw_evidence_index.json                          ← index of all discovery runs
└── raw_evidence/
    ├── <source_id>/
    │   ├── <discovery_run_id>.json                  ← one artifact per run per source
    │   └── ...
    └── ...
```

**Path components:**

| Component | Description | Example |
|-----------|-------------|---------|
| `artifacts/discovery/` | Root for all discovery-layer artifacts | — |
| `raw_evidence_index.json` | Registry of all raw evidence discovery runs | — |
| `raw_evidence/<source_id>/` | Per-source subdirectory | `raw_evidence/hacker_news_algolia/` |
| `<discovery_run_id>.json` | Single discovery run artifact | `discovery_run_2026-05-11_a1b2c3.json` |

### 3.2 Discovery Run ID

The `discovery_run_id` is a deterministic identifier for a single adapter invocation:

```
discovery_run_id = "discovery_run_{YYYY-MM-DD}_{8-char-hex}"
```

Where:
- `YYYY-MM-DD` is the UTC date of the run.
- `8-char-hex` is the first 8 characters of `SHA-256(source_id + query_kind + topic_id + YYYY-MM-DD)`.

This ensures:
- Same source + query + topic + date → same `discovery_run_id`.
- Different sources or different days → different IDs.
- No timestamps in the ID (date is stable across a day; re-runs on the same day overwrite).

### 3.3 Raw Evidence Index

[`raw_evidence_index.json`](artifacts/discovery/raw_evidence_index.json) is a JSON array of run entries:

```json
{
  "artifact_type": "raw_evidence_index",
  "schema_version": "1.0.0",
  "runs": [
    {
      "discovery_run_id": "discovery_run_2026-05-11_a1b2c3d4",
      "source_id": "hacker_news_algolia",
      "source_type": "discussion",
      "topic_id": "ai_developer_tools",
      "query_kind": "search",
      "fetch_mode": "fixture",
      "artifact_path": "artifacts/discovery/raw_evidence/hacker_news_algolia/discovery_run_2026-05-11_a1b2c3d4.json",
      "created_at": "2026-05-11T10:00:00Z",
      "record_count": 42,
      "status": "complete"
    }
  ]
}
```

**Note:** This schema is advisory. The artifact paths and index format are proposed for later implementation. The field schemas in Sections 5–6 are the binding part of this contract.

---

## 4. Top-Level Artifact Structure

A single raw evidence artifact file has this structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_type` | `string` | **Yes** | Fixed value: `"raw_evidence"` |
| `schema_version` | `string` | **Yes** | Semantic version of this schema, e.g. `"1.0.0"` |
| `discovery_run_id` | `string` | **Yes** | Unique run identifier (see Section 3.2) |
| `source_id` | `string` | **Yes** | The adapter's `source_id` constant |
| `source_type` | `string` | **Yes** | Source category (see Section 8) |
| `source_name` | `string` | **Yes** | Human-readable source label |
| `fetch_mode` | `string` | **Yes** | `fixture` / `dry_run` / `live_opt_in` |
| `topic_id` | `string` | **Yes** | Pipeline topic that drove this fetch |
| `query_kind` | `string` | **Yes** | Query type for this fetch |
| `created_at` | `string` | **Yes** | ISO 8601 UTC timestamp of artifact creation |
| `records` | `array[RawEvidence]` | **Yes** | The evidence records (see Section 6) |
| `source_quality_summary` | `object` | **Yes** | Quality summary (see Section 17) |
| `validation_summary` | `object` | **Yes** | Validation pass/fail/warn counts (see Section 14) |
| `warnings` | `array[string]` | **No** | Non-blocking warning messages |
| `errors` | `array[string]` | **No** | Blocking error messages |

### 4.1 Example Top-Level Shell

```json
{
  "artifact_type": "raw_evidence",
  "schema_version": "1.0.0",
  "discovery_run_id": "discovery_run_2026-05-11_a1b2c3d4",
  "source_id": "hacker_news_algolia",
  "source_type": "discussion",
  "source_name": "Hacker News Algolia",
  "fetch_mode": "fixture",
  "topic_id": "ai_developer_tools",
  "query_kind": "search",
  "created_at": "2026-05-11T10:00:00Z",
  "records": [],
  "source_quality_summary": {},
  "validation_summary": {},
  "warnings": [],
  "errors": []
}
```

---

## 5. Compatibility with Existing `RawEvidence` Model

The `RawEvidence` records in the `records` array MUST be compatible with the existing [`RawEvidence`](../../src/oos/models.py:77) frozen dataclass. This schema does **not** redefine or replace that model. It defines the JSON serialization format and the additional wrapping artifact structure.

### 5.1 Field Mapping

Every field in the existing [`RawEvidence`](../../src/oos/models.py:77) dataclass maps to a JSON field of the same name:

| Python Field (`RawEvidence`) | JSON Field | Type | Notes |
|------------------------------|------------|------|-------|
| `evidence_id` | `evidence_id` | `string` | Stable, deterministic |
| `source_id` | `source_id` | `string` | Adapter constant |
| `source_type` | `source_type` | `string` | Enum value (Section 8) |
| `source_name` | `source_name` | `string` | Human-readable |
| `source_url` | `source_url` | `string` | Must be real `http(s)://` URL |
| `collected_at` | `collected_at` | `string` | ISO 8601 UTC |
| `title` | `title` | `string` | Non-empty |
| `body` | `body` | `string` | Non-empty |
| `language` | `language` | `string` | Language code or `"unknown"` |
| `topic_id` | `topic_id` | `string` | Pipeline topic |
| `query_kind` | `query_kind` | `string` | Query type |
| `content_hash` | `content_hash` | `string` | SHA-256 of normalized `title + body` |
| `author_or_context` | `author_or_context` | `string` | Privacy-safe role/context label |
| `raw_metadata` | `raw_metadata` | `object` | Source-specific metadata dict |
| `access_policy` | `access_policy` | `string` | Access method label |
| `collection_method` | `collection_method` | `string` | `fixture` / `live_opt_in` / `dry_run` |

### 5.2 Additional JSON-Only Fields

The JSON artifact may carry additional fields not present in the Python dataclass. These are metadata for the artifact layer and do not affect downstream processing:

| JSON Field | Type | Description |
|------------|------|-------------|
| `evidence_kind` | `string` | Classification hint (see Section 7) |
| `source_metadata` | `object` | Source-specific metadata (see Section 12) |
| `summary` | `string` or `null` | Human-written or source-provided summary |
| `author` | `string` or `null` | Author display name (privacy-safe) |
| `created_at` | `string` or `null` | Original item creation timestamp from source |
| `updated_at` | `string` or `null` | Original item last-update timestamp |
| `tags` | `array[string]` or `null` | Source-specific tags |
| `categories` | `array[string]` or `null` | Source-specific categories |
| `engagement_metrics` | `object` or `null` | Upvotes, comments, views, etc. |
| `source_specific_id` | `string` or `null` | Native identifier from the source |
| `extraction_notes` | `string` or `null` | Adapter notes about extraction |
| `quality_flags` | `array[string]` or `null` | Quality flags (see Section 13) |
| `duplicate_of` | `string` or `null` | `evidence_id` of the record this duplicates |
| `canonical_url` | `string` or `null` | Canonical URL if different from `source_url` |

---

## 6. RawEvidence Record Schema

### 6.1 Required Fields

Every `RawEvidence` record MUST have these fields populated with non-empty values:

| # | Field | Type | Description | Validation |
|---|-------|------|-------------|------------|
| 1 | `evidence_id` | `string` | Stable, deterministic ID (see Section 9) | Non-empty, matches ID pattern |
| 2 | `source_id` | `string` | Adapter's constant source identifier | Non-empty, valid source_id |
| 3 | `source_type` | `string` | Source category (see Section 8) | Must be one of the valid enum values |
| 4 | `source_name` | `string` | Human-readable source label | Non-empty |
| 5 | `source_url` | `string` | Stable, canonical URL to the source item | Must be `http(s)://`, not placeholder (see Section 10) |
| 6 | `collected_at` | `string` | ISO 8601 UTC timestamp of fetch | Valid ISO 8601 |
| 7 | `title` | `string` | Source item title | Non-empty, stripped |
| 8 | `body` | `string` | Source item body, excerpt, or summary | Non-empty |
| 9 | `language` | `string` | Language code or `"unknown"` | Non-empty |
| 10 | `topic_id` | `string` | Pipeline topic driving this fetch | Non-empty |
| 11 | `query_kind` | `string` | Query type for this fetch | Non-empty |
| 12 | `content_hash` | `string` | SHA-256 of normalized `title + body` | 64-char hex, matches computed hash |
| 13 | `author_or_context` | `string` | Privacy-safe role/context label | Non-empty, no usernames/handles |
| 14 | `raw_metadata` | `object` | Dict of source-specific metadata | Must be a JSON object |
| 15 | `access_policy` | `string` | Access method label | Non-empty |
| 16 | `collection_method` | `string` | `fixture` / `live_opt_in` / `dry_run` | Non-empty |
| 17 | `evidence_kind` | `string` | Classification hint (see Section 7) | Must be one of the valid enum values |

### 6.2 Optional Fields

| # | Field | Type | Description |
|---|-------|------|-------------|
| 18 | `summary` | `string` or `null` | Source-provided or adapter-generated summary |
| 19 | `author` | `string` or `null` | Display name (privacy-safe, no handles) |
| 20 | `created_at` | `string` or `null` | Original creation timestamp (ISO 8601) |
| 21 | `updated_at` | `string` or `null` | Original last-update timestamp (ISO 8601) |
| 22 | `tags` | `array[string]` or `null` | Source-specific tags |
| 23 | `categories` | `array[string]` or `null` | Source-specific categories |
| 24 | `engagement_metrics` | `object` or `null` | Upvotes, comment counts, views, etc. |
| 25 | `source_specific_id` | `string` or `null` | Native identifier from the source |
| 26 | `extraction_notes` | `string` or `null` | Adapter notes about extraction quality |
| 27 | `quality_flags` | `array[string]` or `null` | Quality flags (see Section 13) |
| 28 | `duplicate_of` | `string` or `null` | `evidence_id` of the canonical record |
| 29 | `canonical_url` | `string` or `null` | Canonical URL if different from `source_url` |

---

## 7. Evidence Kinds

Every raw evidence record carries an `evidence_kind` field indicating what type of signal the record represents. This is a classification hint for downstream processing, not a definitive signal label.

### 7.1 Valid Values

| `evidence_kind` | Description | Typical Source Types |
|-----------------|-------------|---------------------|
| `pain_signal_candidate` | User describes a frustration, problem, or unmet need | `discussion`, `issue_tracker` |
| `workaround` | User describes a workaround, hack, or makeshift solution | `discussion`, `issue_tracker` |
| `complaint` | User voices a complaint about existing tool/service | `discussion` |
| `feature_request` | User requests a specific feature or capability | `issue_tracker`, `discussion` |
| `bug_report` | User reports a bug or defect | `issue_tracker` |
| `product_launch` | A new product, service, or solution is announced | `product_launch` |
| `solution_pattern` | Describes an existing solution approach or product pattern | `product_launch`, `curated_context` |
| `curated_context` | Expert-authored context about trends, use-cases, implementations | `curated_context` |
| `market_trend` | Indicator of market direction, adoption, or shift | `curated_context`, `discussion` |
| `unknown` | Cannot be classified; requires downstream review | Any |

### 7.2 Classification Responsibility

- **Adapter default:** The adapter sets `evidence_kind` based on its source type knowledge (e.g., a GitHub Issues adapter tags bug reports as `bug_report` and feature requests as `feature_request`).
- **Downstream refinement:** The [`EvidenceClassifier`](../../src/oos/evidence_classifier.py) may reclassify `evidence_kind` based on content analysis.
- **`unknown` is acceptable:** Adapters are not required to classify perfectly. When uncertain, `unknown` is the safe default.

---

## 8. Source Type Values

The `source_type` field must be one of the values defined in the adapter contract (Section 7):

| `source_type` | Description | v2.11 Source |
|---------------|-------------|--------------|
| `discussion` | Public discussion forum | Hacker News |
| `issue_tracker` | Public issue tracker | GitHub Issues |
| `product_launch` | Product launch / solution pattern platform | Product Hunt |
| `curated_context` | Curated expert-authored content | pimenov.ai |
| `deferred_risky` | Deferred source (not in v2.11) | — |

Additional values may be added in v2.12+ for new source categories. The schema version field (`schema_version`) gates compatibility.

---

## 9. ID Rules

### 9.1 `evidence_id` Generation

`evidence_id` must be **stable** for the same conceptual source item. The same HN post, GitHub issue, or pimenov.ai page must always produce the same `evidence_id`, regardless of when or how many times it is fetched.

**Format:**
```
evidence_id = "raw_{source_id}_{source_specific_id}"
```

Where `source_specific_id` is:
- **HN:** `objectID` from Algolia (e.g., `raw_hacker_news_algolia_41712345`)
- **GitHub Issues:** `{owner}_{repo}_{issue_number}` (e.g., `raw_github_issues_microsoft_vscode_12345`)
- **Product Hunt:** `product_id` (e.g., `raw_product_hunt_abc123`)
- **pimenov.ai:** slug or URL-derived hash (e.g., `raw_pimenov_ai_a1b2c3d4`)

### 9.2 Stability Rules

| Rule | Description |
|------|-------------|
| **No timestamps in stable IDs** | `evidence_id` must not contain dates or timestamps |
| **Based on source-native ID** | The identifier comes from the source, not from when we fetched it |
| **`fetched_at` / `collected_at` vary** | These timestamps are metadata, not identity |
| **Same item → same `evidence_id`** | Across runs, across days, across fetch modes |
| **Different items → different `evidence_id`** | No collisions within a source |

### 9.3 Duplicate Traceability

When two records have the same `evidence_id`:
- They are the same source item.
- The second record must set `duplicate_of` to the first record's `evidence_id`.
- Both may be retained in different run artifacts.
- The raw evidence index allows cross-referencing duplicates.

---

## 10. `source_url` Rules

### 10.1 Mandatory Requirements

`source_url` is **mandatory** and **non-negotiable**. Per [`source_url_traceability_contract.md`](source_url_traceability_contract.md):

| Rule | Description |
|------|-------------|
| **Must be present** | Every `RawEvidence` record must have a non-empty `source_url` |
| **Must be real** | The URL must use `http://` or `https://` scheme with a valid hostname |
| **Must be stable** | The URL must resolve to the same conceptual resource over time |
| **Must be canonical** | Must be the direct link to the source item, not a search result or proxy |
| **No placeholders** | `urn:oos:*` is forbidden |
| **No URNs** | No `urn:*`, `doi:*`, or any non-URL identifier as `source_url` |
| **No proxy URLs** | Must link to the original source, not a cached copy or aggregator |

### 10.2 `canonical_url` vs `source_url`

- `source_url`: The URL from which the item was actually fetched. This is the primary traceability field.
- `canonical_url`: An alternative canonical form if the `source_url` is an API endpoint, redirect, or variant. Optional.

When they differ, both must be real `http(s)://` URLs. Neither may be a placeholder.

### 10.3 Fixture URLs

Test and fixture records must use deterministic, stable fixture URLs:

- **Good:** `https://news.ycombinator.com/item?id=41712345` (real, stable HN URL from fixture)
- **Good:** `https://github.com/test-owner/test-repo/issues/1` (deterministic test URL)
- **Bad:** `urn:oos:test:fixture:1` (placeholder, forbidden)
- **Bad:** `http://example.com/dynamic-timestamp-12345` (non-deterministic)

### 10.4 Missing `source_url`

A record missing `source_url` is a **validation failure** (error). The item must be dropped from the `records` array and reported in `source_quality_summary.missing_url_count`.

---

## 11. Text Fields Policy

### 11.1 `title` and `body`

- `title` and `body` are both **required** and must be **non-empty**.
- `title` should be the source item's original title, not a generated summary.
- `body` should contain the source item's primary text content.

### 11.2 `summary`

- `summary` is **optional** and may be `null`.
- If present, `summary` must be **explicitly marked** as a summary in `extraction_notes` (e.g., `"summary: truncated to 500 chars"`).
- Summaries must not be presented as original text.

### 11.3 Length Guidance

| Field | Recommended Max | Truncation Policy |
|-------|----------------|-------------------|
| `title` | 500 characters | Truncate with `…` suffix if over |
| `body` | 10,000 characters | Truncate with note in `extraction_notes` |
| `summary` | 2,000 characters | Truncate with note in `extraction_notes` |

These are guidance, not hard rules. Adapters may retain longer text when the source provides it, but must set `quality_flags: ["low_text_context"]` if body is under 100 characters (suggesting insufficient content for analysis).

### 11.4 Copyright and Content Retention

- Do **not** store entire long-form articles or pages unless the source's access policy explicitly allows it.
- Preserve enough context for audit: a reader should be able to understand what the source item was about without visiting the URL.
- Summaries must be marked as summaries.
- The `body` field should contain the **source-provided** content, not an AI-generated rewrite.

---

## 12. Metadata Policy

### 12.1 `raw_metadata` vs `source_metadata`

- **`raw_metadata`** (required): The existing Python dataclass field. Contains source-specific fields. Maps directly to the `RawEvidence.raw_metadata` dict.
- **`source_metadata`** (implied by `raw_metadata` in JSON): In the JSON artifact, `raw_metadata` is the serialized form of this dict.

### 12.2 Source-Specific Metadata Examples

**Hacker News (discussion):**

```json
{
  "objectID": "41712345",
  "parent_id": null,
  "story_id": "41712340",
  "points": 42,
  "num_comments": 15,
  "created_at": "2026-05-10T08:30:00Z",
  "author_present": true,
  "original_url": "https://example.com/article",
  "tags": ["ask-hn", "ai"],
  "type": "story"
}
```

**GitHub Issues (issue_tracker):**

```json
{
  "issue_number": 12345,
  "repo": "microsoft/vscode",
  "labels": ["bug", "needs-repro"],
  "state": "open",
  "comments_count": 8,
  "created_at": "2026-05-09T14:00:00Z",
  "updated_at": "2026-05-10T22:00:00Z",
  "author_present": true,
  "is_pull_request": false
}
```

**Product Hunt (product_launch):**

```json
{
  "product_id": "abc123",
  "slug": "example-product",
  "topics": ["ai", "developer-tools"],
  "makers": ["Jane Dev", "John Builder"],
  "votes_count": 250,
  "comments_count": 40,
  "created_at": "2026-05-08T00:00:00Z",
  "author_present": true
}
```

**pimenov.ai (curated_context):**

```json
{
  "section": "blog",
  "tags": ["ai-agents", "llm"],
  "categories": ["use-cases"],
  "page_type": "article",
  "published_at": "2026-05-07T12:00:00Z",
  "updated_at": null,
  "author_present": true,
  "language_detected": "ru"
}
```

### 12.3 Metadata Constraints

- `raw_metadata` must be a JSON object (dict), never a string, array, or null.
- Source-specific fields are unbounded but should favor structured data over raw blobs.
- No PII, no private handles, no API keys in `raw_metadata`.
- The `author_present` boolean indicates whether the source reports an author; the `author` string field (optional) carries the privacy-safe display name.

---

## 13. Quality Flags

Quality flags are advisory markers set by the adapter to indicate potential issues with a record. They appear in the `quality_flags` array (optional, may be `null` if no flags apply).

### 13.1 Defined Flags

| Flag | Meaning | Action |
|------|---------|--------|
| `missing_date` | Source item has no creation or publication date | Warn |
| `low_text_context` | `body` is very short (< 100 chars) or missing substantive content | Warn |
| `suspected_self_promo` | Content appears to be self-promotional, not a genuine signal | Flag for review |
| `likely_duplicate` | Record may be a near-duplicate of another (not exact hash match) | Flag for dedup check |
| `low_confidence_source` | Source reliability or signal quality is uncertain | Flag for review |
| `high_noise_source` | Source is known to produce high noise; record may be marginal | Flag for review |
| `requires_manual_review` | Record has characteristics requiring human judgment | Flag for review |
| `source_access_limited` | Access to the source is restricted; content may be incomplete | Warn |
| `rate_limited` | This record was affected by rate limiting during fetch | Warn |
| `paywall_or_access_restricted` | Source item requires payment or login for full access | Warn |

### 13.2 Flag Policy

- Flags are **advisory**, not blocking (warnings, not errors).
- A record with flags is still valid and included in `records`.
- Downstream classifiers and the founder review interface may use flags to prioritize or deprioritize records.
- Flags should be specific and minimal: set only the flags that actually apply.

---

## 14. Validation Rules

### 14.1 Fail Rules (Blocking Errors)

A record that fails any of these rules is **rejected** and counted in `validation_summary.fail_count`:

| # | Rule | Severity |
|---|------|----------|
| VF1 | `evidence_id` is missing or empty | Error |
| VF2 | `source_id` is missing or empty | Error |
| VF3 | `source_url` is missing or empty | Error |
| VF4 | `source_url` is a placeholder (`urn:oos:*` or similar) | Error |
| VF5 | `source_url` does not match `http(s)://` scheme | Error |
| VF6 | `title` is empty AND `body` is empty | Error |
| VF7 | `source_type` is not a recognized enum value | Error |
| VF8 | `content_hash` does not match computed `SHA-256(title + body)` | Error |
| VF9 | `collection_method` is not `fixture` / `live_opt_in` / `dry_run` | Error |

### 14.2 Warn Rules (Non-Blocking)

A record that triggers these rules is **retained** but counted in `validation_summary.warn_count`:

| # | Rule | Severity |
|---|------|----------|
| VW1 | `created_at` is missing or `null` | Warning |
| VW2 | `author` is missing or `null` | Warning |
| VW3 | `body` length < 100 characters (`low_text_context`) | Warning |
| VW4 | `engagement_metrics` is missing or `null` | Warning |
| VW5 | `language` is `"unknown"` | Warning |
| VW6 | `summary` is non-null but not marked in `extraction_notes` | Warning |
| VW7 | `quality_flags` contains `requires_manual_review` | Warning |

### 14.3 Pass Conditions

A record passes validation when:
- All required fields are non-empty.
- `source_url` is a real, stable `http(s)://` URL.
- `evidence_id` is stable and follows the `raw_{source_id}_{source_specific_id}` pattern.
- `content_hash` is correct.
- `source_metadata` / `raw_metadata` is a valid JSON object.

### 14.4 Validation Summary Structure

```json
{
  "validation_summary": {
    "records_seen": 100,
    "records_passed": 92,
    "records_failed": 3,
    "records_warned": 5,
    "fail_reasons": {
      "missing_source_url": 1,
      "placeholder_url": 1,
      "empty_title_and_body": 1
    },
    "warn_reasons": {
      "missing_date": 3,
      "low_text_context": 2
    },
    "validation_passed": true
  }
}
```

`validation_passed` is `true` when `records_failed == 0`.

---

## 15. Deduplication Policy

### 15.1 Exact Duplicates

Two records are **exact duplicates** when they have the same `evidence_id`.

**Policy:**
- Within a single run artifact: the first occurrence is retained; duplicates are dropped and counted in `duplicate_count`.
- Across run artifacts: both are retained (each run artifact is self-contained). The index allows cross-referencing.

### 15.2 Near Duplicates

Two records from the same source are **near duplicates** when they have the same `canonical_url` but different `evidence_id` (e.g., fetched via different query kinds).

**Policy:**
- Both records are retained.
- The later record sets `duplicate_of` to the earlier record's `evidence_id`.
- The `likely_duplicate` quality flag is set.
- The `duplicate_count` in the quality summary counts exact duplicates only; near duplicates are noted separately.

### 15.3 Cross-Source Duplicates

The same real-world item may appear in multiple sources (e.g., a GitHub issue is discussed on HN).

**Policy:**
- Cross-source records are **never silently dropped**.
- Each source adapter produces its own `RawEvidence` records independently.
- Cross-source deduplication happens downstream in the [`CandidateSignalExtractor`](../../src/oos/candidate_signal_extractor.py) or [`signal_dedup.py`](../../src/oos/signal_dedup.py), not at the raw evidence layer.
- Adapters do not compare their output against other sources.

### 15.4 No Silent Drops

Per the adapter contract (Section 5.5): every excluded item must be reported with:
- Identifying information.
- The reason for the drop.
- Whether the drop was due to validation failure, duplicate, or other cause.

---

## 16. Mapping to Candidate Signals

### 16.1 Raw Evidence Is Pre-Signal

Raw evidence records are **pre-signal** artifacts. They represent what was observed at the source, not what the pipeline has determined to be a valid signal.

### 16.2 Downstream Extraction

The conversion from `RawEvidence` to `CandidateSignal` happens in [`CandidateSignalExtractor`](../../src/oos/candidate_signal_extractor.py). This schema ensures that:

1. Every `RawEvidence` record has enough data for the extractor to work with.
2. `source_url` is always available for traceability in downstream artifacts.
3. `evidence_kind` provides a classification hint the extractor can use or override.
4. `quality_flags` allow the extractor to prioritize or filter records.

### 16.3 No Opportunity Framing at This Layer

Raw evidence records:
- Do **not** contain opportunity sketches, market estimates, or founder framing.
- Do **not** carry portfolio states or decisions.
- Do **not** have scores beyond source-provided metrics (upvotes, comments).
- Do **not** trigger automated decisions or autonomous actions.

### 16.4 Conceptual Flow

```
RawEvidence                    CandidateSignal              OpportunityCandidate
───────────                    ───────────────              ────────────────────
evidence_id          →         signal_id                    opportunity_id
source_url           →         source_url                   source_urls[]
evidence_kind        →         (informs signal_type)        (informs framing)
title + body         →         signal_description           opportunity_description
quality_flags        →         (informs signal_status)      (informs confidence)
raw_metadata         →         extracted_metadata           evidence_summary
```

---

## 17. Source Quality Summary

### 17.1 Summary Fields

Every raw evidence artifact carries a `source_quality_summary` with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | `string` | Adapter's source identifier |
| `source_type` | `string` | Source category |
| `fetch_mode` | `string` | `fixture` / `dry_run` / `live_opt_in` |
| `records_seen` | `integer` | Total raw items retrieved from the source |
| `records_emitted` | `integer` | Successfully converted to `RawEvidence` records |
| `records_rejected` | `integer` | Items dropped due to validation failures |
| `duplicate_count` | `integer` | Exact duplicates detected within this session |
| `near_duplicate_count` | `integer` | Near duplicates detected (same `canonical_url`) |
| `warning_count` | `integer` | Total warnings across all records |
| `error_count` | `integer` | Total errors (failed records) |
| `placeholder_url_count` | `integer` | Records rejected for placeholder URLs |
| `missing_url_count` | `integer` | Records rejected for missing `source_url` |
| `missing_date_count` | `integer` | Records with missing `created_at` |
| `low_text_context_count` | `integer` | Records with `body` < 100 chars |
| `noise_indicators` | `array[string]` | Descriptions of noise patterns observed |
| `quality_score` | `number` or `null` | Aggregate quality score (defined in item 8; `null` until then) |

### 17.2 Match with Adapter Contract

These fields align with the adapter contract Section 3, Phase 7 (Report Source Quality), with the following mapping:

| Adapter Contract Field | Schema Field | Notes |
|------------------------|--------------|-------|
| `items_fetched` | `records_seen` | Same concept |
| `items_converted` | `records_emitted` | Same concept |
| `items_dropped` | `records_rejected` | Same concept |
| `items_duplicate` | `duplicate_count` | Same concept |
| `errors` | (in `validation_summary`) | Error details in validation summary |
| `warnings` | (in `validation_summary`) | Warning details in validation summary |

---

## 18. Fixture and Test Policy

### 18.1 Fixture Determinism

- Fixture artifacts must produce **identical output** on every run.
- Fixture JSON files must not contain environment-specific timestamps.
- `collected_at` in fixtures should use a fixed timestamp (e.g., `"2026-01-01T00:00:00Z"`).
- `discovery_run_id` in fixtures should use a fixed date and deterministic hex (no random components).

### 18.2 Fixture Source URLs

- Fixture `source_url` values must be **stable and deterministic**.
- Real source URLs from fixture data are acceptable (e.g., real HN item URLs from a fixture snapshot).
- Synthetic fixture URLs must follow the `http(s)://` pattern with a valid hostname (e.g., `https://news.ycombinator.com/item?id=41712345`).
- No `urn:oos:*` placeholders in any fixture, ever.

### 18.3 Live API Policy

- **No live API calls in unit tests.**
- Tests that require live data must use mocked responses or fixture files.
- `live_opt_in` mode tests must be gated behind an explicit configuration toggle and excluded from the default test suite.
- The `fetch_mode` field in test artifacts must be `"fixture"` or `"dry_run"`.

### 18.4 Snapshot Testing

- Snapshot tests should validate that fixture output is byte-identical between runs.
- Use fixed timestamps in fixture artifacts.
- Content hashes must match between runs for identical input.

---

## 19. JSON Example

Below is a compact illustrative example with two records: one Hacker News-style discussion record and one pimenov.ai-style curated context record.

```json
{
  "artifact_type": "raw_evidence",
  "schema_version": "1.0.0",
  "discovery_run_id": "discovery_run_2026-05-11_a1b2c3d4",
  "source_id": "hacker_news_algolia",
  "source_type": "discussion",
  "source_name": "Hacker News Algolia",
  "fetch_mode": "fixture",
  "topic_id": "ai_developer_tools",
  "query_kind": "search",
  "created_at": "2026-05-11T10:00:00Z",
  "records": [
    {
      "evidence_id": "raw_hacker_news_algolia_41712345",
      "source_id": "hacker_news_algolia",
      "source_type": "discussion",
      "source_name": "Hacker News Algolia",
      "source_url": "https://news.ycombinator.com/item?id=41712345",
      "collected_at": "2026-05-11T10:00:00Z",
      "title": "Ask HN: What's your biggest frustration with CI/CD pipelines?",
      "body": "I spend more time debugging flaky CI than writing code. What tools or practices actually solved this for you?",
      "language": "en",
      "topic_id": "ai_developer_tools",
      "query_kind": "search",
      "content_hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
      "author_or_context": "Ask HN author",
      "raw_metadata": {
        "objectID": "41712345",
        "points": 142,
        "num_comments": 67,
        "created_at": "2026-05-10T15:30:00Z",
        "author_present": true,
        "tags": ["ask-hn", "devops"],
        "type": "story"
      },
      "access_policy": "public_api",
      "collection_method": "fixture",
      "evidence_kind": "pain_signal_candidate",
      "summary": null,
      "author": "Ask HN author",
      "created_at": "2026-05-10T15:30:00Z",
      "updated_at": null,
      "tags": ["ask-hn", "devops", "ci-cd"],
      "categories": null,
      "engagement_metrics": {
        "points": 142,
        "num_comments": 67
      },
      "source_specific_id": "41712345",
      "extraction_notes": null,
      "quality_flags": null,
      "duplicate_of": null,
      "canonical_url": null
    },
    {
      "evidence_id": "raw_pimenov_ai_a3f8c2e1",
      "source_id": "pimenov_ai",
      "source_type": "curated_context",
      "source_name": "pimenov.ai",
      "source_url": "https://pimenov.ai/blog/ai-agents-enterprise-2026",
      "collected_at": "2026-05-11T10:00:00Z",
      "title": "AI Agents in Enterprise: Lessons from 50 Deployments",
      "body": "Analysis of 50 enterprise AI agent deployments reveals 3 recurring failure modes: context window exhaustion, tool-calling instability, and human-in-the-loop bottlenecks. Teams that solved these invested heavily in structured observation logs and deterministic fallback paths.",
      "language": "ru",
      "topic_id": "ai_developer_tools",
      "query_kind": "by_section",
      "content_hash": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
      "author_or_context": "pimenov.ai contributor",
      "raw_metadata": {
        "section": "blog",
        "tags": ["ai-agents", "enterprise", "llm"],
        "categories": ["use-cases"],
        "page_type": "article",
        "published_at": "2026-05-07T12:00:00Z",
        "updated_at": null,
        "author_present": true,
        "language_detected": "ru"
      },
      "access_policy": "static_allowlist",
      "collection_method": "fixture",
      "evidence_kind": "curated_context",
      "summary": "Enterprise AI agent deployments reveal context window exhaustion, tool-calling instability, and human-in-the-loop bottlenecks as top failure modes.",
      "author": "pimenov.ai contributor",
      "created_at": "2026-05-07T12:00:00Z",
      "updated_at": null,
      "tags": ["ai-agents", "enterprise", "llm"],
      "categories": ["use-cases"],
      "engagement_metrics": null,
      "source_specific_id": "blog/ai-agents-enterprise-2026",
      "extraction_notes": "summary: truncated to 200 chars; body truncated to 500 chars; Russian-language original",
      "quality_flags": null,
      "duplicate_of": null,
      "canonical_url": "https://pimenov.ai/blog/ai-agents-enterprise-2026"
    }
  ],
  "source_quality_summary": {
    "source_id": "hacker_news_algolia",
    "source_type": "discussion",
    "fetch_mode": "fixture",
    "records_seen": 2,
    "records_emitted": 2,
    "records_rejected": 0,
    "duplicate_count": 0,
    "near_duplicate_count": 0,
    "warning_count": 0,
    "error_count": 0,
    "placeholder_url_count": 0,
    "missing_url_count": 0,
    "missing_date_count": 0,
    "low_text_context_count": 0,
    "noise_indicators": [],
    "quality_score": null
  },
  "validation_summary": {
    "records_seen": 2,
    "records_passed": 2,
    "records_failed": 0,
    "records_warned": 0,
    "fail_reasons": {},
    "warn_reasons": {},
    "validation_passed": true
  },
  "warnings": [],
  "errors": []
}
```

> **Note:** The example shows two records from different sources in one artifact for illustration. In practice, each artifact contains records from a single source (one `source_id` per artifact). The second record is shown as it would appear in its own `pimenov_ai` artifact.

---

## 20. Non-Goals

This schema explicitly **excludes**:

| Non-Goal | Rationale |
|----------|-----------|
| Implementing source adapters | Item 4–7; requires separate approval |
| Live fetching from external sources | Not in v2.11 item 2 scope |
| LLM-based extraction or classification | Not in v2.11 item 2 scope |
| Signal scoring changes | Existing pipeline; not a schema concern |
| Opportunity generation or framing | Existing pipeline; downstream of raw evidence |
| Database or server storage | File-system artifacts only per project architecture |
| Broad scraping of any source | Prohibited by adapter contract Section 2 |
| Modifying existing `RawEvidence` model | This schema is compatible; model changes require separate approval |
| Defining source registry or allowlist | Item 3 |
| Defining quality scoring formula | Item 8 |
| Creating test fixtures | Implementation concern; not in docs-only item |

---

## 21. Decision

**v2.11 item 2 defines the Raw Evidence Artifact Schema only.**

- No adapter implementation is authorized by this item.
- No source code, tests, scripts, or artifacts are modified.
- No runtime behavior is changed.
- The schema defines the canonical JSON format for raw evidence artifacts and the rules that all source adapters must satisfy when producing them.
- Implementation of artifact serialization, validation, and index management requires later roadmap items and explicit founder approval.
- The existing [`RawEvidence`](../../src/oos/models.py:77) dataclass remains the authoritative Python model. This schema defines the JSON serialization contract compatible with it.

---

## 22. Self-Audit

| Question | Answer |
|----------|--------|
| Did this avoid implementation? | **Yes.** Contract/advisory only. No `.py` files modified. |
| Did this avoid source/test changes? | **Yes.** No source, test, script, or example files changed. |
| Did this define the canonical artifact structure? | **Yes.** Sections 4–6 define top-level artifact, record schema, and field mapping. |
| Did this define evidence kinds? | **Yes.** Section 7 defines 10 evidence kind values. |
| Did this define source types? | **Yes.** Section 8 aligns with adapter contract. |
| Did this define ID rules? | **Yes.** Section 9 defines deterministic `evidence_id` generation. |
| Did this define `source_url` rules? | **Yes.** Section 10 references `source_url_traceability_contract.md`. |
| Did this define text field policies? | **Yes.** Section 11 covers title, body, summary, length, copyright. |
| Did this define metadata policy? | **Yes.** Section 12 covers `raw_metadata` with source-specific examples. |
| Did this define quality flags? | **Yes.** Section 13 defines 10 flags. |
| Did this define validation rules? | **Yes.** Section 14 defines fail/warn/pass rules and validation summary. |
| Did this define deduplication policy? | **Yes.** Section 15 covers exact, near, and cross-source duplicates. |
| Did this define mapping to candidate signals? | **Yes.** Section 16 explains the pre-signal role. |
| Did this define source quality summary? | **Yes.** Section 17 defines all summary fields. |
| Did this define fixture and test policy? | **Yes.** Section 18 covers determinism, fixture URLs, live API, snapshots. |
| Did this include a JSON example? | **Yes.** Section 19 provides a compact 2-record example. |
| Did this state non-goals? | **Yes.** Section 20. |
| Did this reference the adapter contract? | **Yes.** Sections 1, 2, 3, 6, 8, 17. |
| Did this reference `source_url_traceability_contract.md`? | **Yes.** Sections 1, 10. |
| Did this respect the non-goals? | **Yes.** No implementation, no live APIs, no LLM, no broad scraping. |
| Did this state that implementation is not authorized? | **Yes.** Section 21. |

---

*Raw Evidence Artifact Schema. v2.11 item 2. Schema finalized / implementation pending.*
