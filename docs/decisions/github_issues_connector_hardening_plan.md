# GitHub Issues Connector Hardening Plan

**Roadmap:** v2.11
**Item:** 5
**Status:** Plan finalized / implementation pending

---

## 1. Context

GitHub Issues is one of the two narrow external discovery sources already present in the OOS codebase. The existing collector adapter at [`src/oos/github_issues_collector.py`](../../src/oos/github_issues_collector.py) was built during v2.3 (item 4.2) and has operated since as a fixture-driven source feeding the signal pipeline via the GitHub REST Search API.

Roadmap v2.11 focuses on hardening source inputs before expanding to new sources. Before adding Product Hunt, pimenov.ai, or any deferred risky source, the existing sources — HN and GitHub Issues — must be assessed for gaps, aligned with the new v2.11 contracts, and brought to a documented, inspectable baseline.

GitHub Issues should be treated as an **issue_tracker source** per [`source_allowlist_policy.md`](../contracts/source_allowlist_policy.md) Section 7 and [`discovery_source_adapter_contract.md`](../contracts/discovery_source_adapter_contract.md) Section 7.2. GitHub Issues can provide:

- Bug reports revealing real-world defects and friction points
- Feature requests indicating unmet needs and desired capabilities
- Recurring developer pain across repos and ecosystems
- Integration pain between tools, APIs, and platforms
- Documentation gaps flagged by users
- Workflow friction described in issue bodies and discussions
- Workaround descriptions ("we built a script to handle X")

**This item is planning only.** No implementation, no live API calls, no code modifications. The plan documents what a hardened GitHub Issues adapter must look like; it does not build one.

---

## 2. Current-State Assessment

### 2.1 Existing GitHub Issues-Related Code

| Artifact | Path | Status |
|----------|------|--------|
| **GitHub Issues collector** | [`src/oos/github_issues_collector.py`](../../src/oos/github_issues_collector.py) | Exists, functional, 223 lines |
| **GitHub Issues collector tests** | [`tests/test_github_issues_collector.py`](../../tests/test_github_issues_collector.py) | Exists, 279 lines, 14 test methods |
| **GitHub Issues fixture data** | Inline in test file (71-line function, 2 issues) | Single synthetic fixture from one repo (`example/finance-tool`) |
| **Source registry (config)** | [`config/source_registry.json`](../../config/source_registry.json) | Registered as `github_issues`, status `planned_hardening` |
| **Adapter contract reference** | [`docs/contracts/discovery_source_adapter_contract.md`](../contracts/discovery_source_adapter_contract.md) | Section 8.2 defines GitHub Issues expectations |

### 2.2 What Currently Works

The existing [`GitHubIssuesCollector`](../../src/oos/github_issues_collector.py) is a working fixture-mode adapter that:

1. **Converts GitHub Search API hits to [`RawEvidence`](../../src/oos/models.py:77)** — the [`github_issue_to_raw_evidence`](../../src/oos/github_issues_collector.py:19) function maps `id`, `node_id`, `number`, `html_url`, `title`, `body`, `state`, `created_at`, `updated_at`, `closed_at`, `comments`, `labels`, `reactions`, `repository_url`, `comments_url`, and `user` presence.
2. **Filters pull requests** — the `skip_pull_requests` parameter (default `True`) excludes records where `pull_request` is a non-empty dict. Test `test_pull_request_shaped_issue_is_skipped_by_default` validates this.
3. **Produces `source_url` from `html_url`** — prefers `html_url` → `url` → fallback `github://issues/{issue_id}`. The `html_url` path produces real `https://github.com/` URLs. The fallback `github://` path is a non-HTTP scheme and a hardening concern.
4. **Preserves metadata safely** — `issue_id`, `node_id`, `number`, `repository_url`, `comments_url`, `labels`, `state`, `created_at`, `updated_at`, `closed_at`, `comments_count`, `reactions`, `pull_request_present`, `user_present`.
5. **Uses privacy-safe `author_or_context`** — hardcoded to `"unverified public issue reporter"`. Does not store `user` object or login in metadata.
6. **Supports fixture and live modes** — fixture payload injected via `__init__`; live mode requires `allow_live_network=True` and `live_network_enabled` on the scheduled item.
7. **Handles malformed hits gracefully** — issues without `id` return `None`; non-dict hits are skipped; empty title/body fall back to `"GitHub issue {issue_id}"`.
8. **Respects `max_results`** — stops after emitting the scheduled result count.
9. **No secrets required in fixture mode** — fixture mode has zero credential requirements; test `test_no_secrets_or_api_keys_required` validates this.
10. **Tests validate core behaviors** — 14 tests cover fixture conversion, source_url format, metadata preservation, privacy, content_hash determinism, max_results, no-network enforcement, PR filtering, malformed input handling, UTF-8 decoding, and empty/malformed payloads.

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
| `source_type` uses `"github_issues"` | **Non-standard** | Contract requires `"issue_tracker"` as `source_type`; current code uses `"github_issues"` |
| Explicit `drop_reason` for excluded items | **Absent** | Items with no `id`, PR-shaped records, malformed issues are silently skipped |
| `tags` / `categories` structured fields | Partial | Present in `raw_metadata["labels"]` but not as top-level `tags` |
| `engagement_metrics` object | Partial | Comments/reactions in `raw_metadata` but not as structured `engagement_metrics` |
| `created_at` / `updated_at` top-level fields | Partial | Present in `raw_metadata` only, not as top-level optional fields |

#### 2.3.2 Gaps vs Raw Evidence Artifact Schema

| Schema Requirement | Status | Gap Description |
|-------------------|--------|----------------|
| `evidence_kind` (required field) | **Missing** | Schema requires `evidence_kind` on every record |
| `summary` optional field | Absent | Not populated |
| `author` optional field | Absent | Privacy-safe display name not set (only `author_or_context`) |
| `created_at` top-level optional | Absent | Present in `raw_metadata` only |
| `updated_at` top-level optional | Absent | Present in `raw_metadata` only |
| `tags` top-level optional | Absent | Present in `raw_metadata["labels"]` only |
| `categories` top-level optional | Absent | Not populated |
| `engagement_metrics` top-level optional | Absent | Not populated as structured object |
| `source_specific_id` top-level optional | Absent | `node_id` present only in `raw_metadata` |
| `extraction_notes` | Absent | Not populated |
| `quality_flags` | Absent | Not populated |
| `duplicate_of` | Absent | Not populated |
| `canonical_url` | Absent | Not populated |
| `source_quality_summary` in artifact | **Absent** | Not produced |
| `validation_summary` in artifact | **Absent** | Not produced |

#### 2.3.3 Gaps vs Source Allowlist Policy

| Policy Requirement | Status | Gap Description |
|-------------------|--------|----------------|
| `source_type: "issue_tracker"` | **Divergence** | Code uses `"github_issues"` |
| `status: planned_hardening` | Aligned | Config registry says `planned_hardening` |
| `implementation_authorized: false` | Aligned | Config registry says false; code exists from pre-v2.11 |
| `default_enabled: false` | **Divergence** | Code may be reachable via scheduler (depends on runtime registry) |
| `live_access_allowed: false` | Partial | Live access gated behind `allow_live_network` flag |
| `unit_test_mode: fixture_only` | Aligned | Tests use fixtures only |
| `stable_source_url_required: true` | Partial | `html_url` path is stable; fallback `github://` is not |
| `no_placeholder_urls` | **Divergence** | Fallback `github://issues/{issue_id}` is a URN-like placeholder |

#### 2.3.4 Gaps vs Source URL Traceability Contract

| Contract Requirement | Status | Gap Description |
|---------------------|--------|----------------|
| `source_url` must use `http(s)://` | **Divergence** | Fallback `github://issues/{issue_id}` uses non-HTTP scheme |
| No `urn:oos:*` placeholders | Satisfied | No `urn:oos:*` uses anywhere |
| Stable, canonical URL | Partial | `html_url` path is canonical; `url` (API URL) and `github://` fallback are not |
| Missing `source_url` → drop + report | Partial | Items missing both `html_url` and `url` get `github://` fallback, not dropped |

### 2.4 Summary of Critical Gaps

1. **No source quality summary** — the adapter contract Phase 7 requirement is entirely unaddressed.
2. **`source_type` divergence** — code uses `"github_issues"`; contracts and config registry expect `"issue_tracker"`.
3. **`source_url` fallback is non-HTTP** — `github://issues/{issue_id}` is a URN-like placeholder, violating the source URL traceability contract.
4. **Missing `evidence_kind`** — every record per the schema must carry `evidence_kind`.
5. **Missing optional fields** — `summary`, `author`, `tags`, `categories`, `engagement_metrics`, `source_specific_id`, `extraction_notes`, `quality_flags`, `duplicate_of`, `canonical_url` are not populated at top level.
6. **No classification heuristics** — GitHub issues are not classified into evidence kinds (bug_report, feature_request, complaint, workaround, pain_signal_candidate).
7. **No noise filters beyond PR exclusion** — bot-generated issues, stale issues, low-context issues, maintainer-only housekeeping, duplicate/invalid/wontfix issues pass through unfiltered.
8. **Single minimal fixture** — only 2 synthetic issues from one repo (`example/finance-tool`); no representative bug reports, feature requests, bot issues, stale issues, or multi-repo examples.
9. **No deduplication reporting** — duplicates within batch are dropped silently (no `duplicate_count` in a quality summary).
10. **`author_or_context` is a single static string** — all GitHub issues get `"unverified public issue reporter"`, losing the distinction between bug reporters, feature requesters, maintainers, and bot accounts.
11. **No repo allowlist or query strategy** — no configuration for which repos to query or which keywords to search.
12. **No rate limit or auth handling** — live mode `_fetch_live_payload` has no token support, no rate-limit header handling, no retry logic, no `Retry-After` awareness.
13. **`collection_method` uses non-standard value** — `"github_issues_fixture"` instead of standard `"fixture"` per adapter contract.
14. **`access_policy` uses non-standard value** — `"public_github_issues_fixture_or_live_disabled_default"` instead of a standard policy label.
15. **No comments policy** — comments are not fetched, included, or addressed; `comments_count` is captured in metadata but comment content is absent.

---

## 3. GitHub Source Categories

GitHub Issues contain distinct issue types, each with different signal potential for the OOS pipeline:

| Issue Area | Signal Value | Noise Risk | Priority |
|-----------|-------------|------------|----------|
| **Bug reports** | High — reveals real-world defects, friction, and breaking points in tools users depend on | Low-Medium — some are low-severity or already-fixed | Primary |
| **Feature requests** | High — users explicitly describe what they need, revealing market gaps | Medium — many are niche or low-demand | Primary |
| **Workaround descriptions** | Very High — users describe makeshift solutions, indicating unmet needs | Low — inherently signal-rich | Primary |
| **Integration pain** | High — issues about tool A not working with tool B reveal ecosystem gaps | Low-Medium | Primary |
| **Documentation complaints** | Medium-High — reveals onboarding friction and missing information | Medium — may be low-effort complaints | Secondary |
| **Questions / support issues** | Medium — reveals confusion and usability gaps | High — many are RTFM or one-off | Filtered only |
| **Workflow friction** | Medium-High — describes inefficient processes and toolchain pain | Medium | Secondary |
| **Recurring issues across repos** | Very High — same problem reported in multiple repos indicates ecosystem-level pain | Low — confirmed by multiple sources | Primary (cross-repo) |
| **Labels: `bug`, `enhancement`, `help wanted`** | High — structured signal from maintainers | Low — label meaning is repo-specific | Primary |
| **Labels: `question`, `documentation`** | Medium — reveals user confusion and gaps | Medium — label usage varies | Secondary |
| **Labels: `duplicate`, `invalid`, `wontfix`** | Low — already resolved or rejected | High — these are noise | Exclude / flag |

### 3.1 Recommended Collection Priority

1. **Cross-repo pain-keyword search** (targeted, deterministic, high signal)
2. **Bug reports with `bug` label and active discussion** (confirmed real-world defects)
3. **Feature requests with `enhancement` label and community engagement** (market gap signals)
4. **Issues with workaround language in body** (unmet need signals)
5. **Integration pain issues** (ecosystem gap signals)
6. **Documentation gap issues** (onboarding friction signals)
7. **Questions/support issues** (deferred; high noise, low standalone signal)

---

## 4. Access-Method Options

### 4.1 GitHub REST Issues API (`api.github.com/repos/{owner}/{repo}/issues`)

| Aspect | Assessment |
|--------|-----------|
| **Endpoint** | `GET /repos/{owner}/{repo}/issues` |
| **Data model** | Array of issue objects with `id`, `node_id`, `number`, `title`, `body`, `state`, `labels`, `comments`, `created_at`, `updated_at`, `closed_at`, `html_url`, `url`, `repository_url`, `user`, `pull_request`, `reactions` |
| **PR filtering** | Issues endpoint **includes pull requests** by default. PRs are identified by the presence of a `pull_request` key. Must filter explicitly. |
| **Search support** | **None.** Per-repo listing only. Must use Search API for cross-repo queries. |
| **Comments access** | Separate endpoint: `GET /repos/{owner}/{repo}/issues/{number}/comments` |
| **Rate limits** | 60 req/hr unauthenticated; 5,000 req/hr authenticated (per user) |
| **Auth required** | No for public repos, but heavily rate-limited without auth |
| **Use for** | Fetching issues from a known allowlisted repo; comment fetching when authorized |
| **Verification needed** | Confirm PR field presence on all issue-type records; confirm labels array format; confirm `body` is always present (may be `null` or empty); confirm pagination via `Link` header |

### 4.2 GitHub Search API (`api.github.com/search/issues`)

| Aspect | Assessment |
|--------|-----------|
| **Endpoint** | `GET /search/issues?q={query}` |
| **Data model** | `total_count`, `incomplete_results`, `items` array with same issue objects as REST API |
| **PR filtering** | Search results **include pull requests** unless `is:issue` qualifier is used. Must include `is:issue` in query. |
| **Search support** | Full-text search with qualifiers: `is:issue`, `is:open`, `label:`, `repo:`, `language:`, `created:`, `updated:`, `comments:`, `reactions:` |
| **Rate limits** | 10 req/min unauthenticated; 30 req/min authenticated (Search API has stricter limits) |
| **Auth required** | Strongly recommended; unauthenticated limit is very restrictive (10 req/min) |
| **Use for** | Keyword-based discovery across repos; label-filtered queries; date-range queries |
| **Verification needed** | Confirm `is:issue` qualifier reliably excludes PRs; confirm `incomplete_results` flag behavior; confirm `items` ordering stability; confirm `per_page` max (100); test pagination with `page` parameter |

### 4.3 GitHub GraphQL API (`api.github.com/graphql`)

| Aspect | Assessment |
|--------|-----------|
| **Endpoint** | `POST /graphql` |
| **Data model** | Nodes with requested fields via GraphQL query |
| **PR filtering** | Explicit separation: `Issue` and `PullRequest` are distinct GraphQL types |
| **Search support** | `search(query: "...", type: ISSUE, first: N)` with field selection |
| **Rate limits** | Based on points (5,000 points/hr authenticated); complex queries cost more points |
| **Auth required** | **Yes.** No unauthenticated access. |
| **Use for** | Complex multi-field queries; precise field selection; PR/Issue type safety |
| **Verification needed** | Confirm auth token scope requirements; measure point cost per query; test pagination via cursor; confirm `Issue` vs `PullRequest` type distinction |
| **Deferred?** | **Yes — deferred.** REST/Search API are sufficient for v2.11 scope. GraphQL adds auth complexity without proportionate gain for initial hardening. |

### 4.4 Static Fixtures Only

| Aspect | Assessment |
|--------|-----------|
| **Use for** | Unit tests, deterministic validation, CI/CD |
| **Data** | Pre-saved JSON payloads mirroring GitHub Search API responses |
| **Network** | None required |
| **Verification needed** | Fixture determinism across runs; fixture representativeness of real data; no PII in fixture `user` fields |

### 4.5 Pre-Implementation Verification Checklist

Before any implementation begins, the following must be verified (not by this plan; by the future implementation item):

- [ ] GitHub Search API `is:issue` qualifier reliably excludes pull requests (including alongside other qualifiers)
- [ ] Search API `incomplete_results` flag behavior confirmed (does it truncate or just indicate timeout?)
- [ ] Search API pagination: `page` parameter and `Link` header behavior confirmed
- [ ] REST Issues API includes `pull_request` key on PR-type records (confirmed by existing test)
- [ ] Requester's own token provides 5,000 req/hr for REST, 30 req/min for Search (documented limits confirmed in practice)
- [ ] Rate-limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`) are present and reliable
- [ ] Issue `body` can be `null` or empty string; both cases must be handled
- [ ] `labels` is always an array of objects with `name`, `color`, `description` (or empty array)
- [ ] `reactions` object contains `total_count`, `+1`, `-1`, `laugh`, `hooray`, `confused`, `heart`, `rocket`, `eyes`
- [ ] GitHub issue URL pattern `https://github.com/{owner}/{repo}/issues/{number}` is stable
- [ ] Comment URL pattern `https://github.com/{owner}/{repo}/issues/{number}#issuecomment-{comment_id}` confirmed
- [ ] Fixture files can be created from real API responses without PII leakage (user logins mapped to roles, no email exposure)

---

## 5. Proposed Source Registry Alignment

The hardened GitHub Issues adapter must align with [`config/source_registry.json`](../../config/source_registry.json):

| Field | Current Code Value | Registry Value | Hardened Value |
|-------|-------------------|---------------|----------------|
| `source_id` | `github_issues` | `github_issues` | `github_issues` (already aligned) |
| `source_type` | `github_issues` | `issue_tracker` | `issue_tracker` |
| `status` | (runtime) | `planned_hardening` | `planned_hardening` → `implemented_fixture_only` (after implementation) |
| `implementation_authorized` | (runtime) | `false` | `false` (this plan does not authorize) |
| `default_enabled` | (runtime) | `false` | `false` |
| `live_access_allowed` | gated by flag | `false` | `false` |
| `unit_test_mode` | `fixture` | `fixture_only` | `fixture_only` |

### 5.1 `source_type` Naming Decision

The code currently uses `"github_issues"` as the `source_type` constant. The config registry and adapter contract both specify `"issue_tracker"`. This plan recommends:

- The config registry value `"issue_tracker"` is the canonical `source_type` for registry purposes.
- The adapter implementation must emit `source_type: "issue_tracker"` in every `RawEvidence` record.
- The internal constant `GITHUB_ISSUES_SOURCE_TYPE` should be changed to `"issue_tracker"`.
- All downstream references (evidence classification, signal scoring) that check `source_type == "github_issues"` must be updated to check `source_type == "issue_tracker"`.

### 5.2 Registry Field Alignment (Target State After Implementation)

```json
{
  "source_id": "github_issues",
  "source_type": "issue_tracker",
  "source_name": "GitHub Issues",
  "status": "implemented_fixture_only",
  "implementation_authorized": true,
  "default_enabled": false,
  "live_access_allowed": false,
  "unit_test_mode": "fixture_only",
  "likely_access_methods": ["github_rest_api", "github_search_api"],
  "stable_source_url_required": true,
  "source_url_policy": "mandatory_external_url",
  "risk_level": "medium",
  "notes": "hardened per v2.11 item 5 plan; fixture-only until controlled smoke passes; PR filtering required; no github:// fallback URLs"
}
```

**This target state is not authorized by this plan. It is noted here for the future implementation item.**

---

## 6. Raw Evidence Mapping

### 6.1 GitHub Issue → RawEvidence Field Mapping

| RawEvidence Field | Required | Source from GitHub Issue | Fallback / Notes |
|------------------|----------|--------------------------|------------------|
| `evidence_id` | Yes | `"raw_github_issues_{node_id}"` | Use `node_id` (stable), not `id` (numeric, may vary across installations) |
| `source_id` | Yes | `"github_issues"` | Adapter constant |
| `source_type` | Yes | `"issue_tracker"` | Per source category |
| `source_name` | Yes | `"GitHub Issues"` | Human-readable constant |
| `source_url` | Yes | `issue.html_url` | `https://github.com/{owner}/{repo}/issues/{number}` |
| `collected_at` | Yes | ISO 8601 of fetch time | Fixture mode: fixed timestamp |
| `title` | Yes | `issue.title` | Fallback: `"GitHub issue {node_id}"` |
| `body` | Yes | `issue.body` or `""` | Fallback: title if body is empty/null |
| `language` | Yes | `"unknown"` | GitHub issues are language-agnostic; could detect from body |
| `topic_id` | Yes | From `scheduled_item.topic_id` | — |
| `query_kind` | Yes | From `scheduled_item.query_kind` | — |
| `content_hash` | Yes | SHA-256 of `normalize_raw_evidence_content(title, body)` | Deterministic |
| `author_or_context` | Yes | Role label (see 6.2) | Privacy-safe; no usernames |
| `raw_metadata` | Yes | Source-specific metadata dict (see 6.3) | Must be JSON object |
| `access_policy` | Yes | `"public_api_auth_optional"` | Standard policy label |
| `collection_method` | Yes | `"fixture"` / `"live_opt_in"` / `"dry_run"` | Per fetch mode |
| `evidence_kind` | Yes | Classification result (see Section 9) | Must be valid enum |
| `summary` | No | `issue.body` truncated to 500 chars, or `null` | Marked in extraction_notes |
| `author` | No | Privacy-safe display name (see 6.2) | `null` if not safe to display |
| `created_at` | No | `issue.created_at` (ISO 8601) | `null` if missing |
| `updated_at` | No | `issue.updated_at` (ISO 8601) | `null` if missing |
| `tags` | No | `issue.labels[].name` | Label names only |
| `categories` | No | Derived from labels and state | `["bug"]`, `["enhancement"]`, etc. |
| `engagement_metrics` | No | `{"comments": int, "reactions": {...}}` | `null` if both zero/missing |
| `source_specific_id` | No | `issue.node_id` | — |
| `extraction_notes` | No | Notes about truncation, missing fields, body null | `null` if no issues |
| `quality_flags` | No | Quality indicators (see Section 12) | `null` if no flags |
| `duplicate_of` | No | `evidence_id` of canonical record | `null` if not a duplicate |
| `canonical_url` | No | `issue.html_url` | `null` if same as `source_url` |

### 6.2 `author` and `author_or_context` Privacy Policy

| Issue Context | `author_or_context` | `author` |
|--------------|-------------------|---------|
| Issue with user present | `"issue reporter"` | `null` (no safe public display) |
| Bug report | `"bug reporter"` | `null` |
| Feature request | `"feature requester"` | `null` |
| Issue from maintainer | `"project maintainer"` | `null` |
| Issue from bot account | `"automated system (bot)"` | `null` |

**Policy:** GitHub usernames are public but should not be directly stored as `author` in OOS artifacts without a clear justification. The `user_present` boolean in `raw_metadata` indicates whether the source reports an author. The `author` string field remains `null` by default; the `author_or_context` provides role context without exposing handles. Bot detection: if the user login matches known bot patterns (e.g., ends in `[bot]`, contains `dependabot`, `renovate`, `stale`, `github-actions`), `author_or_context` is set to `"automated system (bot)"`.

### 6.3 `raw_metadata` Structure

```json
{
  "issue_id": 123456789,
  "node_id": "I_kwDOExample",
  "number": 42,
  "repo_full_name": "example/finance-tool",
  "repository_url": "https://api.github.com/repos/example/finance-tool",
  "comments_url": "https://api.github.com/repos/example/finance-tool/issues/42/comments",
  "labels": ["bug", "needs-repro"],
  "state": "open",
  "state_reason": "completed",
  "created_at": "2024-02-03T04:05:06Z",
  "updated_at": "2024-02-04T04:05:06Z",
  "closed_at": null,
  "comments_count": 5,
  "reactions": {"total_count": 3, "+1": 2, "eyes": 1},
  "pull_request_present": false,
  "user_present": true,
  "author_association": "NONE",
  "locked": false,
  "query_plan_id": "qp_abc123",
  "dedup_key": "dk_def456"
}
```

Additional fields to add during hardening:

| Metadata Field | Purpose |
|---------------|---------|
| `repo_full_name` | `owner/repo` from `repository_url` or issue context |
| `author_association` | GitHub's `author_association` field (NONE, CONTRIBUTOR, MEMBER, OWNER, COLLABORATOR) |
| `state_reason` | `completed`, `not_planned`, `reopened`, or `null` (GitHub's close reason) |
| `locked` | Whether the issue is locked |
| `issue_text_length` | Character count of body for quality assessment |

### 6.4 `source_url` Policy (Critical Hardening Item)

The current code has a three-tier `source_url` fallback chain:

```python
source_url = _first_non_empty(issue.get("html_url"), issue.get("url"), f"github://issues/{issue_id}")
```

This plan mandates:

1. **`html_url` is the only acceptable `source_url`.** It produces `https://github.com/{owner}/{repo}/issues/{number}`.
2. **`url` (API URL) must NOT be used as `source_url`.** API URLs (`https://api.github.com/repos/...`) are not canonical item links.
3. **`github://issues/{issue_id}` fallback must be removed.** This is a URN-like placeholder that violates the source URL traceability contract.
4. **If `html_url` is missing or empty, the item must be dropped** with an explicit `drop_reason: "missing_source_url"` reported in the source quality summary.
5. **No silent fallback.** A missing `html_url` is a validation failure, not a recoverable condition.

This is the single most important hardening change for GitHub Issues. Every other field can be enhanced incrementally; `source_url` must be correct from the first hardened record.

---

## 7. Pull Request Filtering

### 7.1 The Problem

GitHub's REST Issues API and Search API both include pull requests in issue listings. PRs are GitHub issues with an additional `pull_request` key. Without filtering, PRs contaminate the issue signal pipeline with implementation details, code review discussions, and merge activity — none of which are useful pain signals for OOS.

### 7.2 Current Filtering

The existing code at [`github_issue_to_raw_evidence`](../../src/oos/github_issues_collector.py:26) filters PRs:

```python
if skip_pull_requests and isinstance(issue.get("pull_request"), dict):
    return None
```

This correctly checks for the `pull_request` field being a non-empty dict. The existing test `test_pull_request_shaped_issue_is_skipped_by_default` validates this behavior.

### 7.3 Recommended Filtering Rules

1. **PR filtering must be mandatory and non-configurable.** `skip_pull_requests` should not be a parameter — it should always be `True`. No scenario in the OOS pipeline justifies collecting PRs as issue-derived evidence.
2. **Search API queries must include `is:issue` qualifier.** This reduces (but does not eliminate) PR results at the API level. The `pull_request` key check is the definitive filter.
3. **Dropped PRs must be reported.** Each PR-shaped item dropped must increment a `pr_filtered_count` in the source quality summary.
4. **Tests must cover PR filtering explicitly** — including:
   - PR with `pull_request` key present → dropped
   - Issue without `pull_request` key → retained
   - Issue with `pull_request` as `null` or missing → retained
   - Search result with `is:issue` and `pull_request` key → dropped (defense in depth)

### 7.4 No PR-Derived Evidence

- **No PR mining in GitHub Issues connector.** PRs represent solution implementation, not pain discovery.
- A future connector (e.g., `github_pull_requests`) could be considered for trend/solution-pattern signals, but this is out of scope for v2.11.
- The GitHub Issues connector is strictly for issues. PRs are contamination and must be excluded.

---

## 8. Comments Policy

### 8.1 Issue Body as Primary Evidence

The issue body is the primary evidence source. It contains the reporter's description of the problem, feature request, or workaround. Comments provide additional context but are secondary.

### 8.2 Comments as Optional Context

| Aspect | Policy |
|--------|--------|
| **Default behavior** | Comments are **not fetched**. Issue body only. |
| **Comment count** | Captured as `comments_count` in `raw_metadata` and `engagement_metrics.comments`. |
| **When to fetch comments** | Only when explicitly authorized via configuration toggle (`include_comments: true`). |
| **Comment fetching is deferred** | Unless a specific hardening/runtime item authorizes comment enrichment. |
| **Comment content in evidence** | If fetched, appended to `body` with clear delimiter (`\n\n--- COMMENTS ---\n\n`) and documented in `extraction_notes`. |

### 8.3 Copyright and Content Concerns

- GitHub issue bodies and comments are user-generated content subject to GitHub's Terms of Service.
- Storing full comment threads may exceed reasonable excerpting for signal extraction.
- The `body` field should contain the issue body (source-provided content).
- Comments, if included, should be summarized or truncated with explicit notes.
- No silent full-text reproduction of lengthy comment threads.

### 8.4 `source_url` for Comments

If comments are included as part of an evidence record:
- The `source_url` remains the issue URL (`https://github.com/{owner}/{repo}/issues/{number}`).
- Individual comments are not separate evidence records in the default configuration.
- If individual comments become separate records (future), each must carry its own comment URL: `https://github.com/{owner}/{repo}/issues/{number}#issuecomment-{comment_id}`.

### 8.5 Comment Fetching Deferred

Comment fetching is deferred unless explicitly authorized by a later roadmap item. The initial hardened implementation operates on issue body only, with `comments_count` as an engagement metric.

---

## 9. `evidence_kind` Classification Rules

Every GitHub Issues raw evidence record must carry an `evidence_kind`. The following deterministic heuristics are proposed. These are **planning heuristics**, not implementation — they will be refined, tested, and calibrated during implementation.

### 9.1 Classification Decision Tree (Proposed)

```
Input: GitHub issue with title, body, labels, state, state_reason

1. IF labels contains "bug" (case-insensitive):
   → IF body contains pain_keywords:          evidence_kind = "pain_signal_candidate"
   → ELSE:                                     evidence_kind = "bug_report"

2. IF labels contains "enhancement" OR "feature" OR "feature-request":
   → IF body contains need_keywords:           evidence_kind = "pain_signal_candidate"
   → ELSE:                                     evidence_kind = "feature_request"

3. IF labels contains "documentation" OR "docs":
   → evidence_kind = "unknown" (set quality_flags: ["documentation_gap"])

4. IF labels contains "question" OR "support":
   → evidence_kind = "unknown" (set quality_flags: ["requires_manual_review"])

5. IF body contains workaround_keywords:
   → evidence_kind = "workaround"

6. IF body contains integration_pain_keywords:
   → evidence_kind = "pain_signal_candidate" (set quality_flags: ["integration_pain"])

7. IF body contains pain_keywords:
   → evidence_kind = "pain_signal_candidate"

8. IF body contains complaint_keywords:
   → evidence_kind = "complaint"

9. IF body contains feature_request_keywords:
   → evidence_kind = "feature_request"

10. DEFAULT: evidence_kind = "unknown"
```

### 9.2 Keyword Sets (Proposed, to be Refined During Implementation)

**pain_keywords:** `"frustrating"`, `"pain"`, `"struggle"`, `"nightmare"`, `"waste of time"`, `"drives me crazy"`, `"so hard to"`, `"impossible to"`, `"hours of"`, `"biggest problem"`, `"hate"`, `"terrible"`, `"broken"`, `"can't"`, `"unusable"`, `"blocker"`, `"critical"`, `"showstopper"`

**workaround_keywords:** `"workaround"`, `"hack"`, `"spreadsheet"`, `"manual process"`, `"duct tape"`, `"makeshift"`, `"temporary solution"`, `"script to"`, `"zapier"`, `"ifttt"`, `"cron job"`, `"work around"`, `"kludge"`, `"jury rig"`, `"export to CSV"`, `"manual work"`

**complaint_keywords:** `"why is"`, `"why does"`, `"should be easier"`, `"too expensive"`, `"overpriced"`, `"not worth"`, `"disappointed"`, `"regret"`, `"wish I hadn't"`, `"ridiculous"`, `"absurd"`, `"unacceptable"`

**feature_request_keywords:** `"wish it had"`, `"would be great if"`, `"feature request"`, `"missing"`, `"needs"`, `"should support"`, `"please add"`, `"looking for a tool that"`, `"it would be nice"`, `"I'd love to see"`

**need_keywords:** `"we need"`, `"requires"`, `"must have"`, `"essential"`, `"critical for"`, `"blocking"`, `"can't proceed without"`, `"dealbreaker"`

**integration_pain_keywords:** `"doesn't work with"`, `"integration"`, `"connect to"`, `"api broken"`, `"incompatible"`, `"not compatible"`, `"sync"`, `"webhook"`, `"connector"`

### 9.3 Classification Tiebreakers

1. Label-based classification takes priority over keyword-based classification (labels are structured maintainer metadata).
2. Longest keyword match wins (prefer specific over generic).
3. If body is under 100 characters, lean toward `"unknown"` (insufficient context).
4. If `state_reason == "not_planned"`, lean toward `"unknown"` and set `quality_flags: ["wontfix_or_rejected"]`.
5. `"unknown"` is the safe default. Adapters set `evidence_kind`; the downstream [`EvidenceClassifier`](../../src/oos/evidence_classifier.py) may reclassify.

### 9.4 Special Cases

| Condition | Classification | Notes |
|-----------|---------------|-------|
| Locked issue | Any (based on content) | Set `quality_flags: ["locked_issue"]` |
| Bot-authored issue | `unknown` | Set `quality_flags: ["bot_generated"]` |
| Stale issue (no update > 365 days) | Any (based on content) | Set `quality_flags: ["stale_issue"]` |
| Issue with `duplicate` label | `unknown` | Set `quality_flags: ["duplicate_labeled"]` |
| Issue with `invalid` or `wontfix` label | `unknown` | Set `quality_flags: ["invalid_or_wontfix"]` |
| Issue with `good first issue` or `help wanted` | Any (based on content) | Boost priority; active community interest |

---

## 10. Source URL Traceability

### 10.1 GitHub Issue URL Format

Every GitHub issue has a canonical URL:

```
https://github.com/{owner}/{repo}/issues/{number}
```

This URL pattern is stable and works for all issue types (bug reports, feature requests, questions) across all public repositories.

### 10.2 Comment URL Format

Individual comments have their own URL:

```
https://github.com/{owner}/{repo}/issues/{number}#issuecomment-{comment_id}
```

Comment URLs are only needed if comments become separate evidence records (deferred).

### 10.3 Fixture URL Policy

- Fixture records must use deterministic, stable URLs.
- **Good:** `"https://github.com/example/finance-tool/issues/42"` (deterministic test URL)
- **Good:** `"https://github.com/test-owner/test-repo/issues/1"` (deterministic test URL)
- **Bad:** `"github://issues/123456789"` (non-HTTP scheme, URN-like placeholder)
- **Bad:** `"https://api.github.com/repos/example/repo/issues/42"` (API URL, not canonical)
- **Bad:** `"urn:oos:test:fixture:1"` (placeholder, forbidden)

### 10.4 URL Validation Rules (Per Source URL Traceability Contract)

| Rule | Implementation |
|------|---------------|
| `source_url` must be present | Required field; missing `html_url` → drop record + report |
| `source_url` must use `https://` | `github.com` URLs are always HTTPS |
| No `github://` fallback | Never generated by hardened adapter |
| No `urn:oos:*` placeholders | Never generated by GitHub adapter |
| Stable, canonical link | Always `https://github.com/{owner}/{repo}/issues/{number}` |
| Fixture URLs deterministic | Fixed owner/repo/number in fixture data |
| Missing `source_url` → validation failure | Record dropped; counted in `missing_url_count` |
| No API URLs as `source_url` | `https://api.github.com/...` is not a canonical item URL |

### 10.5 The `github://` Fallback Must Be Removed

The current fallback `github://issues/{issue_id}` is a URN-like string that:
- Uses a non-standard scheme (`github://`)
- Contains an unstable numeric `id` (not the stable `node_id`)
- Does not resolve to any real page
- Violates the source URL traceability contract

**This fallback must be removed entirely.** If `html_url` is missing, the item must be dropped with an explicit reason, not silently converted with a non-URL `source_url`.

---

## 11. Deduplication Plan

### 11.1 `node_id`-Based Dedupe (Primary)

Every GitHub issue has a globally unique `node_id` (GraphQL ID, e.g., `"I_kwDOExample"`). Within a single collection session:

- `evidence_id = "raw_github_issues_{node_id}"`
- If the same `node_id` appears in multiple query results (e.g., same issue returned by different search queries), the first occurrence is kept; subsequent occurrences are dropped.
- The `duplicate_count` in the source quality summary tracks exact duplicates.

**Note:** The current code uses `issue.get("id")` (numeric database ID) for `evidence_id`. This plan recommends switching to `node_id` for global uniqueness. The numeric `id` is unique per-GitHub-instance but not globally unique across GitHub.com. In practice for GitHub.com, both are unique, but `node_id` is the more stable, future-proof identifier.

### 11.2 Repo + Issue Number Dedupe (Secondary)

Within a session, `{repo_full_name}/{issue_number}` provides a natural deduplication key:
- If two items have the same `repo_full_name` and `issue_number`, they are the same issue.
- The `node_id`-based dedupe is sufficient and preferred.

### 11.3 Canonical URL Dedupe

Since `html_url` is unique per issue, `source_url` is inherently deduplicating. Records with identical `source_url` are exact duplicates.

### 11.4 Issue/Comment Relationship

- An issue and its comments are **the same evidence record** in the default configuration (comments optionally enrich the issue body).
- If comments become separate records (future), they must have distinct `evidence_id` values and reference the parent issue via `raw_metadata.parent_issue_node_id`.
- Comment-to-issue relationship is not a deduplication concern in the default configuration.

### 11.5 Cross-Source Deduplication

- The GitHub Issues adapter does **not** compare its output against HN, Product Hunt, or any other source.
- Cross-source duplication (e.g., a GitHub issue being discussed on HN) is handled downstream in [`CandidateSignalExtractor`](../../src/oos/candidate_signal_extractor.py) or [`signal_dedup.py`](../../src/oos/signal_dedup.py).
- Per the raw evidence schema (Section 15.3): cross-source records are never silently dropped at the raw evidence layer.

### 11.6 No Silent Drops

Per the adapter contract (Section 5.5):
- Every excluded GitHub issue must be reported with `node_id` (or `repo/number`), title excerpt, and `drop_reason`.
- Drop reasons must be specific: `"missing_node_id"`, `"pull_request"`, `"duplicate_evidence_id"`, `"empty_title_and_body"`, `"missing_source_url"`, `"validation_failure"`, `"bot_generated_excluded"`.
- All drop counts appear in the source quality summary.

---

## 12. Noise and Quality Filters

### 12.1 Proposed Filters

| Filter | Trigger | Action |
|--------|---------|--------|
| **Pull request** | `pull_request` key present and non-null | **Drop** — PRs are not issues |
| **Bot-generated issue** | `author_association` is bot-like OR user login matches bot patterns | Set `quality_flags: ["bot_generated"]`; do not drop but mark |
| **Stale issue** | No `updated_at` within 365 days AND `state == "open"` | Set `quality_flags: ["stale_issue"]`; do not drop |
| **Low-context issue** | Body < 100 chars | Set `quality_flags: ["low_text_context"]`; do not drop |
| **Duplicate-labeled issue** | `labels` contains `"duplicate"` | Set `quality_flags: ["duplicate_labeled"]`; do not drop |
| **Invalid/wontfix issue** | `labels` contains `"invalid"` or `"wontfix"` OR `state_reason == "not_planned"` | Set `quality_flags: ["invalid_or_wontfix"]`; do not drop |
| **Locked issue** | `locked == true` | Set `quality_flags: ["locked_issue"]`; do not drop |
| **Housekeeping issue** | Title matches patterns: `"update dependency"`, `"bump version"`, `"chore:"`, `"ci:"`, `"refactor:"` | Set `quality_flags: ["maintainer_housekeeping"]`; do not drop |
| **Good signal boost** | Labels: `"bug"`/`"enhancement"` + `comments_count >= 3` + `reactions.total_count >= 2` | Prefer over low-engagement issues |
| **Cross-repo recurrence** | Same/similar issue across multiple repos in allowlist | Boost priority; flag as ecosystem-level signal |

### 12.2 Bot Detection Patterns

GitHub usernames matching these patterns indicate automated accounts:

- Ends with `[bot]` (e.g., `dependabot[bot]`, `renovate[bot]`)
- Contains `dependabot`, `renovate`, `stale`, `github-actions`, `codecov`, `coveralls`, `sonarcloud`, `imgbot`, `allcontributors`
- The `author_association` field from GitHub API can supplement: bots typically have `NONE` or specific patterns

### 12.3 Maintainer Housekeeping Patterns

Issue titles matching these regex patterns are likely maintainer-generated housekeeping, not user pain:

- `^(chore|build|ci|test|refactor|docs|style)(\(.*\))?:`
- `^(bump|update|upgrade) (dependency|dependencies|version)`
- `^\[?(chore|build|ci|test|refactor|docs|style)\]?`
- `^(release|prepare) v?\d+\.\d+`

### 12.4 Filtering Policy

1. **Only PRs are dropped silently** (but still counted in `pr_filtered_count`). All other filters set `quality_flags` without dropping.
2. **No silent drops** of non-PR items. Every excluded issue must have a documented `drop_reason`.
3. **Quality flag provenance.** Every flag set must have a traceable reason.
4. **Filters are advisory, not blocking.** Records with quality flags are retained in `records`. Downstream classifiers may use flags to prioritize or deprioritize.

---

## 13. Repo Allowlist and Query Strategy

### 13.1 Phased Approach

| Phase | Scope | Fetch Mode | Authorization |
|-------|-------|-----------|---------------|
| **Phase 1: Fixture-only** | Pre-saved JSON payloads; all tests pass | `fixture` | This plan recommends it; implementation requires separate authorization |
| **Phase 2: Small repo allowlist** | Curated set of 5–10 repos in fixture mode | `fixture` | Separate authorization |
| **Phase 3: Curated keyword search** | Keyword queries against GitHub Search API, fixture-backed | `fixture` | Separate authorization |
| **Phase 4: Live opt-in** | Controlled live search with explicit founder approval | `live_opt_in` | Explicit founder approval **only** |
| **Phase 5: Default weekly run** | Not in v2.11 scope | — | v2.12+ after sustained smoke evidence |

### 13.2 Candidate Repo Domains

The repo allowlist should target domains relevant to OOS's opportunity thesis:

| Domain | Example Repos | Signal Value | Rationale |
|--------|--------------|-------------|-----------|
| **AI / LLM tools** | `langchain-ai/langchain`, `openai/openai-python`, `huggingface/transformers` | High — AI tooling pain, integration gaps, feature needs | Core OOS vertical |
| **DevTools** | `microsoft/vscode`, `vercel/next.js`, `prettier/prettier` | High — developer workflow pain, tooling gaps | Developer audience signal |
| **Data / ETL** | `apache/airflow`, `dbt-labs/dbt-core`, `prefecthq/prefect` | High — data pipeline pain, automation gaps | OOS automation angle |
| **Automation** | `n8n-io/n8n`, `home-assistant/core` | Medium-High — workflow automation pain | Adjacent to OOS value prop |
| **Finance ops / accounting tooling** | Open-source finance/accounting repos, invoicing tools | Medium-High — SMB finance pain, reporting gaps | Direct OOS relevance |
| **Documentation-heavy developer frameworks** | `sphinx-doc/sphinx`, `storybookjs/storybook` | Medium — documentation/onboarding friction | Broad audience signal |

**Note:** These are candidate suggestions, not authorized selections. The actual repo allowlist must be curated during implementation with founder review.

### 13.3 Query Strategy

Queries are **proposed planning concepts**. Each will be tuned during implementation.

#### Pain Queries
- `"pain point" OR "frustrating" OR "drives me crazy" is:issue`
- `"spend way too much time" OR "hours of" is:issue`
- `"nightmare" OR "impossible to" is:issue`
- `"blocker" OR "showstopper" OR "critical bug" is:issue`

#### Workaround Queries
- `"workaround" OR "hack" OR "makeshift" is:issue`
- `"spreadsheet" OR "manual process" OR "export to CSV" is:issue`
- `"script to" OR "cron job to" OR "temporary solution" is:issue`

#### Need / Feature Request Queries
- `"feature request" OR "please add" OR "would be great if" is:issue`
- `"we need" OR "must have" OR "essential" is:issue`
- `"blocking" OR "dealbreaker" OR "can't proceed without" is:issue`

#### Integration Pain Queries
- `"doesn't work with" OR "incompatible" OR "integration broken" is:issue`
- `"api" AND ("broken" OR "frustrat" OR "pain") is:issue`

#### Domain-Specific Queries (FinOps / AI / DevTools)
- `repo:microsoft/vscode label:bug "frustrat" OR "pain" OR "broken"`
- `("invoicing" OR "bookkeeping" OR "reporting") AND ("pain" OR "problem" OR "broken") is:issue`
- `("AI" OR "LLM" OR "GPT") AND ("workflow" OR "automation" OR "operations") AND ("pain" OR "frustrat") is:issue`

### 13.4 Query Configuration

- Queries are configured externally (not hardcoded in the adapter).
- Each query has a `query_kind` (e.g., `"pain_query"`, `"workaround_query"`).
- The query planner generates `ScheduledCollectionItem` entries with `query_text`.
- The adapter receives `query_text` and `query_kind` via `ScheduledCollectionItem`.
- Repo allowlist is separate from queries and can be applied as a `repo:` qualifier or post-fetch filter.

---

## 14. Rate Limit and Auth Policy

### 14.1 Unauthenticated vs Authenticated Limits

| API | Unauthenticated | Authenticated (Personal Access Token) |
|-----|----------------|--------------------------------------|
| **REST API** | 60 req/hr per IP | 5,000 req/hr per user |
| **Search API** | 10 req/min per IP | 30 req/min per user |
| **GraphQL API** | Not available | 5,000 points/hr per user |

### 14.2 Auth Policy

- **Token is not required for fixture mode.** Unit tests run without any credentials.
- **Token handling for live mode:**
  - Token must be provided via environment variable (`GITHUB_TOKEN`), never hardcoded.
  - The adapter reads the `auth_token_env_var` from configuration (e.g., `"GITHUB_TOKEN"`).
  - No `.env` files, no tokens in versioned files, no tokens in fixture data.
  - If live mode is enabled but no token is found, the adapter logs a warning and falls back to unauthenticated mode with reduced rate limits.
- **Credentials must not be committed.** The `.gitignore` already excludes `.env`; confirm it excludes any GitHub token files.

### 14.3 Rate Limit Handling

- **Rate limit headers must be respected:**
  - `X-RateLimit-Remaining` — remaining requests in window
  - `X-RateLimit-Reset` — epoch seconds when window resets
  - `Retry-After` — seconds to wait before retry (on 429)
- **Exponential backoff** for transient failures (429, 5xx).
  - Initial delay: 1s (or `Retry-After` value if present)
  - Max delay: 60s
  - Max retries: 3
- **Rate limit exhaustion must be reported** in the source quality summary with:
  - `rate_limit_remaining` at start and end
  - `rate_limit_reset` timestamp
  - Whether the collection was truncated due to rate limits
- **Search API limits are stricter.** The Search API (30 req/min authenticated) is the primary bottleneck. Query batching and staggered requests are recommended.

### 14.4 Pagination Policy

- GitHub Search API returns max 100 results per page (via `per_page` parameter).
- Pagination is via `page` parameter (1-based) and `Link` header.
- The adapter should respect the `Link` header rather than hardcoding pagination.
- `max_results` from `ScheduledCollectionItem` caps the total items emitted, regardless of pagination.

### 14.5 Deterministic Behavior

- Fixture mode: no network calls, no rate limits, no pagination. Deterministic.
- Live mode: non-deterministic by nature, but behavior (retry, backoff, pagination) must be deterministic given the same API state.
- Rate-limit failures should be explicit: the source quality summary must document any rate-limit impacts.

---

## 15. Validation Plan

### 15.1 Required Tests (Future Implementation Item)

| # | Test Case | What It Validates |
|---|-----------|-------------------|
| T1 | Fixture loads without error | Adapter can read and parse fixture JSON payloads |
| T2 | Every output record has a stable `source_url` | `https://github.com/{owner}/{repo}/issues/{number}`; no `github://` fallback, no API URLs |
| T3 | `source_url` format matches expected pattern | `https://` scheme, valid hostname `github.com` |
| T4 | No `github://` fallback URLs anywhere | The fallback path in `_first_non_empty` is removed |
| T5 | No `urn:oos:*` placeholders anywhere | Zero tolerance per traceability contract |
| T6 | `content_hash` matches normalized content | `validate()` passes on all records |
| T7 | `author_or_context` is privacy-safe | No username/handle leakage; bot detection works |
| T8 | `evidence_id` follows `raw_github_issues_{node_id}` | Stable ID pattern using `node_id` |
| T9 | Duplicate `evidence_id` items deduplicated within batch | `duplicate_count` reported |
| T10 | Missing `node_id` produces warning and drop | Item excluded; reported in quality summary |
| T11 | Empty title AND body produces warning and drop | Item excluded; reported in quality summary |
| T12 | Fixture file not found produces error | Error surfaced in quality summary |
| T13 | Malformed fixture produces error | Error surfaced; no partial output |
| T14 | All required `RawEvidence` fields populated | Validation passes for every output record |
| T15 | `source_quality_summary` is produced | All counts and metadata present |
| T16 | `evidence_kind` is set for every record | Must be valid enum value; `"unknown"` is acceptable |
| T17 | Classification heuristics match expected results | Bug with `bug` label → `"bug_report"`; feature request → `"feature_request"` |
| T18 | Noise flags set correctly | Bot issues get `"bot_generated"`; stale issues get `"stale_issue"` |
| T19 | `engagement_metrics` populated when available | Comments and reactions in structured object |
| T20 | `tags` populated from labels | Label names as string array |
| T21 | `source_type` is `"issue_tracker"` | Not `"github_issues"` |
| T22 | `collection_method` uses standard values | `"fixture"`, `"live_opt_in"`, `"dry_run"` — not `"github_issues_fixture"` |
| T23 | `access_policy` uses standard label | `"public_api_auth_optional"` — not the long custom string |
| T24 | Missing `html_url` drops item with explicit reason | `drop_reason: "missing_source_url"` |

### 15.2 Pull Request Filtering Tests

| # | Test Case | Expected Behavior |
|---|-----------|-------------------|
| P1 | Issue with `pull_request` present → dropped | Item excluded; `pr_filtered_count` incremented |
| P2 | Issue without `pull_request` key → retained | Normal conversion |
| P3 | Issue with `pull_request: null` → retained | Normal conversion |
| P4 | Issue with `pull_request: {}` → dropped | Non-null dict triggers filter |
| P5 | Search response with mixed issues and PRs | PRs dropped; issues retained; correct counts |
| P6 | All items in response are PRs | All dropped; `pr_filtered_count == total`; `records_emitted == 0` |

### 15.3 Failure Case Tests

| # | Failure Scenario | Expected Behavior |
|---|-----------------|-------------------|
| F1 | Fixture file not found | Error in quality summary; no records emitted |
| F2 | Fixture file with invalid JSON | Error in quality summary; no records emitted |
| F3 | Fixture with item missing `html_url` | Warning; item dropped; `missing_url_count` incremented |
| F4 | Fixture with item having `html_url: ""` | Warning; item dropped |
| F5 | Fixture with item having empty title AND empty body | Warning; item dropped |
| F6 | Fixture with duplicate `node_id` entries | First kept; duplicate dropped; `duplicate_count = 1` |
| F7 | Fixture with `labels` missing | No crash; `tags` is `null`; classification defaults to `"unknown"` |
| F8 | Live mode (mocked): API returning 5xx after retries | Error; quality summary reports failure |
| F9 | Live mode (mocked): API returning 429 with `Retry-After` | Warning; delay honored; retry attempted |
| F10 | Live mode (mocked): API returning 401/403 | Error; auth failure reported |
| F11 | Live mode (mocked): empty `items` array | No records; quality summary reports 0 records_seen |
| F12 | Live mode (mocked): `incomplete_results: true` | Warning set; records still processed |
| F13 | Fixture with bot-authored issue | `quality_flags` contains `"bot_generated"`; record retained |
| F14 | Fixture with stale issue (>365 days) | `quality_flags` contains `"stale_issue"`; record retained |
| F15 | Fixture item with `html_url` as API URL (`api.github.com`) | Dropped — not a canonical URL (if enforcing canonical check) |

### 15.4 No Live API in Unit Tests

All tests in T1–T24, P1–P6, and F1–F15 must use `fixture` mode or mocked responses. Zero live network calls in the default test suite. The existing pattern (inject `fixture_payload` via constructor) is correct and should be preserved.

---

## 16. Controlled Smoke Plan

### 16.1 Smoke Phases

| Phase | Description | Authorization |
|-------|-------------|---------------|
| **Smoke 1: Fixture validation** | Load all GitHub Issues fixtures; validate every record; verify quality summary | No live calls; can run in CI |
| **Smoke 2: Dry-run** | Run the adapter in `dry_run` mode; verify configuration loading | No live calls; can run in CI |
| **Smoke 3: Live smoke (single query)** | Run authenticated live search with limited scope | Explicit founder approval required |
| **Smoke 4: Live smoke (multi-repo)** | Run against small repo allowlist | Explicit founder approval; deferred |

### 16.2 Smoke 1: Fixture Validation (Always Allowed)

1. Load all GitHub Issues fixture files.
2. Run the adapter in `fixture` mode for each fixture.
3. Validate:
   - Every `RawEvidence` record passes `.validate()`.
   - Every `source_url` is `https://github.com/{owner}/{repo}/issues/{number}`.
   - Zero `github://` fallback URLs.
   - Zero `urn:oos:*` placeholders.
   - `content_hash` matches for every record.
   - `source_quality_summary` has correct counts.
   - `evidence_kind` is set on every record.
   - `source_type` is `"issue_tracker"` on every record.
   - PRs are filtered; `pr_filtered_count` is correct.
   - Bot issues, stale issues, low-context issues get appropriate `quality_flags`.
4. Output: pass/fail per fixture.

### 16.3 Smoke 3: Live Smoke (Founder Approval Only)

1. Run a single search query against GitHub Search API (`is:issue label:bug`, `per_page=10`).
2. **Requires:** `GITHUB_TOKEN` environment variable with a classic PAT (public repo access only).
3. Validate that all records have:
   - Real `source_url` → real GitHub issue pages.
   - Valid `evidence_id` → `raw_github_issues_{node_id}`.
   - Non-empty title and body.
   - `evidence_kind` set.
4. Check rate-limit headers in response (`X-RateLimit-Remaining`, `X-RateLimit-Reset`).
5. Produce a `source_quality_summary` with live metadata including rate-limit snapshot.
6. Record the run in a smoke report artifact.
7. **No default weekly run inclusion until smoke passes at least 3 times.**

### 16.4 Expected Smoke Outputs

| Output | Description |
|--------|-------------|
| `records` | 10–50 RawEvidence records from fixture or live queries |
| `source_quality_summary` | Counts for records_seen, records_emitted, records_rejected, pr_filtered_count, duplicate_count, warnings, errors, rate_limit info |
| `validation_summary` | Pass/fail/warn counts |
| Smoke report | Markdown or JSON report with pass/fail determination |

---

## 17. Implementation Plan for Later Roadmap Item

This is a **compact, ordered sequence** for the future hardening implementation item. Not authorized by this plan.

### 17.1 Implementation Sequence

```
Step 1: Create comprehensive fixture files
  └─ tests/fixtures/github_issues/bug_reports.json
  └─ tests/fixtures/github_issues/feature_requests.json
  └─ tests/fixtures/github_issues/workaround_issues.json
  └─ tests/fixtures/github_issues/noise_and_edge_cases.json
  └─ tests/fixtures/github_issues/search_pain_keywords.json
  └─ tests/fixtures/github_issues/multi_repo_sample.json

Step 2: Update GitHub Issues adapter to align with contracts
  └─ Change GITHUB_ISSUES_SOURCE_TYPE from "github_issues" to "issue_tracker"
  └─ Change evidence_id from "raw_github_issue_{id}" to "raw_github_issues_{node_id}"
  └─ Add evidence_kind classification (Section 9)
  └─ Add source_quality_summary production
  └─ Add optional fields (summary, author, created_at, updated_at, tags,
       categories, engagement_metrics, source_specific_id, extraction_notes,
       quality_flags, duplicate_of, canonical_url)
  └─ Remove github:// fallback URL; drop records missing html_url
  └─ Add explicit drop_reason reporting for all excluded items
  └─ Change collection_method to standard values
  └─ Change access_policy to standard label
  └─ Add bot detection for author_or_context
  └─ Add noise/quality filters (stale, bot, housekeeping, low-context)
  └─ Add pr_filtered_count to quality summary
  └─ Add rate-limit header handling in _fetch_live_payload
  └─ Add auth token support via GITHUB_TOKEN env var

Step 3: Add registry loader integration (if authorized)
  └─ Align runtime source_type with config/source_registry.json
  └─ Ensure default_enabled=false in runtime

Step 4: Add comprehensive unit tests
  └─ 24 positive tests + 15 failure tests + 6 PR-specific tests (Sections 15.1–15.3)
  └─ Fixture-only mode; no live calls

Step 5: Add controlled smoke (founder approval required for live)
  └─ Fixture smoke: always runs
  └─ Live smoke: gated behind --allow-live-network and GITHUB_TOKEN

Step 6: Add source quality summary validation
  └─ Tests validate quality summary fields
  └─ Manual inspection of summary output

Step 7: Keep default_enabled=false
  └─ No default weekly run inclusion
  └─ No registry status change without founder approval
```

### 17.2 Files Expected to Change (During Implementation)

| File | Change Type |
|------|------------|
| `src/oos/github_issues_collector.py` | Modify: align fields, add evidence_kind, quality summary, optional fields, remove github:// fallback, add bot detection, add noise filters |
| `tests/test_github_issues_collector.py` | Modify: expand to 45+ tests with new fixtures |
| `tests/fixtures/github_issues/*.json` | Create: 6+ fixture files |
| `src/oos/models.py` | Possibly: no changes needed (RawEvidence already has all optional fields) |
| `config/source_registry.json` | Possibly: update status after implementation (requires separate approval) |

---

## 18. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **API rate limits** (Search API: 30 req/min authenticated) | High | Fixture-first strategy; query batching; staggered requests; token authentication; respect `Retry-After` and rate-limit headers |
| **Auth/token handling** | Medium | Token via env var only; no hardcoded secrets; fixture mode needs no token; live mode explicitly opt-in |
| **PR pollution of issue results** | High | Dual filter: `is:issue` query qualifier + `pull_request` key check; mandatory and non-configurable; separate `pr_filtered_count` |
| **Issue spam/bots** | Medium | Bot detection by username pattern; `author_or_context` set to `"automated system (bot)"`; `quality_flags: ["bot_generated"]`; bot issues retained but flagged |
| **Stale issues** | Medium | `quality_flags: ["stale_issue"]` for issues with no update > 365 days; retained but flagged for downstream deprioritization |
| **Noisy repos** (low-quality issues, drive-by bug reports) | Medium | Repo allowlist curation; keyword-based search rather than bulk repo pull; quality flags for low-context issues |
| **Repo-selection bias** (only devtools, missing business/finance context) | Medium | Curate allowlist to include finance ops, automation, SMB tooling repos; cross-domain query strategy |
| **Developer-tooling bias** (GitHub user base skews developer) | High | GitHub Issues is inherently developer-biased. Accept this as a known limitation. Complement with non-developer sources (Product Hunt, pimenov.ai). Do not weight GitHub Issues too heavily in signal scoring for non-dev opportunities. |
| **Missing business context** (issues are technical, not business-oriented) | Medium | GitHub Issues signals typically describe technical pain; downstream opportunity framing must translate to business value. Not a source-layer concern but a pipeline concern. |
| **`source_url` mistakes** (API URLs, fallback `github://`) | High | **Hard requirement:** only `html_url` as `source_url`. Remove `github://` fallback. Drop items without `html_url`. Validate in tests. |
| **Comments/copyright concerns** | Low-Medium | Comments not fetched by default; `comments_count` as engagement metric; explicit opt-in for comment enrichment; comment truncation policy |
| **`node_id` vs numeric `id` stability** | Low | `node_id` is the GraphQL global ID, stable across time. Switching from numeric `id` to `node_id` for `evidence_id` is a hardening improvement. Backward compatibility not a concern (records are not persisted between runs in current architecture). |
| **Search API `incomplete_results`** | Low | If `incomplete_results: true`, set warning in quality summary; records are still valid but collection may be incomplete |
| **GitHub API deprecation / version changes** | Low | REST API v3 is stable (2013–present). Accept `application/vnd.github+json` header for current version. GraphQL API exists as fallback if REST ever deprecated. |

---

## 19. Non-Goals

This plan explicitly **excludes**:

| Non-Goal | Reason |
|----------|--------|
| Implementing the GitHub Issues connector | This is a plan, not implementation |
| Making live GitHub API calls | Prohibited during planning; no live calls in any validation |
| Enabling GitHub Issues by default | `default_enabled` stays `false` |
| Adding GitHub Issues to the default weekly run | Prohibited until controlled smoke passes + founder approval |
| Modifying `config/source_registry.json` | Registry changes require separate authorization |
| Modifying `src/`, `tests/`, `scripts/` | No code changes in this item |
| Modifying existing fixtures or creating new fixtures | Implementation concern; not in planning item |
| LLM-based extraction or classification | Not in v2.11 scope for source hardening |
| Comment fetching and enrichment | Deferred; issue body only in initial hardening |
| GraphQL API integration | Deferred; REST/Search API sufficient |
| GitHub Actions/workflow mining | Out of scope |
| PR mining or code-review-derived signals | PRs are explicitly excluded from GitHub Issues connector |
| Repository metadata or star/activity-based source quality | Out of scope |
| Cross-source deduplication with HN or other sources | Handled downstream, not in GitHub Issues adapter |
| GitHub Discussions or GitHub Wiki ingestion | Separate source type; not in scope |
| Real-time issue monitoring or webhooks | Out of scope for v2.11 |

---

## 20. Decision

**v2.11 item 5 creates the GitHub Issues Connector Hardening Plan only.**

- No implementation of any GitHub Issues connector, adapter, collector, or related code is authorized by this plan.
- No live GitHub API calls are authorized by this plan.
- No fixture files are created or modified by this plan.
- No source code, tests, scripts, or artifacts are modified by this plan.
- No registry status changes are authorized by this plan.
- The plan documents the current state, identifies gaps relative to v2.11 contracts, defines target alignment, proposes classification heuristics, mandates `source_url` hardening (removal of `github://` fallback), defines PR filtering requirements, and provides a sequenced implementation roadmap.
- GitHub Issues implementation remains unauthorized. A future roadmap item (on a separate branch, with explicit founder approval) may implement the hardening changes described in this plan.
- The next step after this plan is item 6 (Product Hunt Feasibility and Connector Plan), which is a similar planning-only item.

---

## 21. References

- [`docs/contracts/discovery_source_adapter_contract.md`](../contracts/discovery_source_adapter_contract.md) — Section 8.2 (GitHub Issues-specific adapter expectations)
- [`docs/contracts/raw_evidence_artifact_schema.md`](../contracts/raw_evidence_artifact_schema.md) — Sections 5–7 (field mapping, evidence kinds, source types)
- [`docs/contracts/source_allowlist_policy.md`](../contracts/source_allowlist_policy.md) — Section 7.1.2 (GitHub Issues registry entry)
- [`docs/contracts/source_url_traceability_contract.md`](../contracts/source_url_traceability_contract.md) — Section 5 (placeholder URN policy)
- [`config/source_registry.json`](../../config/source_registry.json) — GitHub Issues entry: `source_id: github_issues`, `source_type: issue_tracker`
- [`src/oos/github_issues_collector.py`](../../src/oos/github_issues_collector.py) — Existing collector (223 lines)
- [`tests/test_github_issues_collector.py`](../../tests/test_github_issues_collector.py) — Existing tests (279 lines, 14 tests)
- [`docs/decisions/hacker_news_connector_hardening_plan.md`](../decisions/hacker_news_connector_hardening_plan.md) — HN hardening plan (structural reference)
- [`docs/roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md`](../roadmaps/OOS_roadmap_v2_11_discovery_sources_checklist.md) — Item 5 definition

---

*GitHub Issues Connector Hardening Plan. v2.11 item 5. Plan finalized / implementation pending.*
