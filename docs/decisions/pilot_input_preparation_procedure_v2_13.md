# OOS v2.13 — Pilot Input Preparation Procedure

**Title:** OOS v2.13 — Pilot Input Preparation Procedure
**Status:** Draft / operational procedure
**Roadmap item:** v2.13 item 5
**Branch:** `ops/v2-13-operational-pilot-cycle-1`
**Created:** 2026-05-13
**Based on:**
- [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md)
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md)
- [HN Pilot Query Plan v2.13](hacker_news_pilot_query_plan_v2_13.md)
- [GitHub Issues Repo Allowlist and Query Plan v2.13](github_issues_repo_allowlist_query_plan_v2_13.md)
- [Raw Evidence Artifact Schema](../contracts/raw_evidence_artifact_schema.md)
- [Operational Discovery Pilot Run Contract](../contracts/operational_discovery_pilot_run_contract.md)

---

## 1. Purpose

The purpose of this procedure is to prepare bounded, traceable, source-scoped input for Pilot Cycle 1 without broad scraping, uncontrolled artifacts, or unapproved live source access.

This procedure answers:

- **What input modes are allowed** — manual bounded, fixture/prepared JSON, live opt-in collection.
- **What approvals are required** — explicit gates for live collection, repo allowlist, and output commitments.
- **What each raw evidence item must contain** — minimum required fields, canonical source identity, URL policy.
- **How to validate input before pilot run** — checklist of mandatory pre-run checks.
- **How to prevent deferred sources from entering the pilot** — explicit source identity allowlist and rejection rules.
- **Where runtime outputs may be written** — `output_dir` policy, no committed repository artifacts by default.

### 1.1 What This Procedure Does NOT Authorize

- Live HN collection — requires explicit founder approval (Approval Gate AG-1).
- Live GitHub Issues collection — requires explicit founder approval (Approval Gate AG-2).
- GitHub repo allowlist finalization — requires explicit founder approval (Approval Gate AG-3).
- Stack Exchange stretch inclusion — requires explicit founder approval (Approval Gate AG-4).
- Committing runtime pilot artifacts to the repository — requires explicit founder approval (Approval Gate AG-5).
- Source expansion beyond HN + GitHub Issues.
- Any modification of source code, tests, scripts, or pipeline behavior.

---

## 2. Input Modes

Three input modes are defined. The mode must be explicitly chosen before any input is prepared.

### Mode A — Manual Bounded Input

Manual curation of HN and GitHub URLs with human-written summaries.

| Attribute | Value |
|-----------|-------|
| **Allowed without live API approval** | Yes |
| **Requires founder approval** | No — manual curation is inherently approved as part of the pilot brief |
| **Requires live API calls** | No |
| **Requires `source_url`** | Yes — every record must have a valid `http(s)://` URL |
| **Traceability** | Must preserve `source_url` for every item |
| **Recommended for** | First dry cycle when live approval is not yet given |
| **Volume** | Small and traceable; dry-cycle minimums apply (see Section 8) |
| **Preparation method** | Founder or operator manually enters URLs and summaries into the input template format |

#### Mode A Rules

1. Every record must have a real `source_url` — no placeholders, no URNs.
2. Manual summaries must be clearly marked as human-authored (use `extraction_notes: "manual_summary"`).
3. The preparer must apply quality flags (see Section 9) based on visible content.
4. The preparer must not guess or fabricate `source_created_at` — use `null` if the source date is not known.
5. Records must not include deferred sources (see Section 6 rejection rules).

### Mode B — Fixture / Prepared JSON Input

Local deterministic JSON prepared from approved public URLs. No live API calls during validation.

| Attribute | Value |
|-----------|-------|
| **Allowed without live API approval** | Yes |
| **Requires founder approval** | No — fixture files assembled from approved public URLs |
| **Requires live API calls** | No — data is pre-assembled into JSON; no network calls during validation or pilot run |
| **Useful for** | Dry cycle repeatability; deterministic testing; validating pipeline before live collection |
| **Traceability** | Every record must have a stable, non-synthetic `source_url` |

#### Mode B Rules

1. Fixture JSON must follow the Raw Evidence Artifact Schema (Section 6 of the schema document).
2. `collected_at` in fixture records should use a fixed timestamp (e.g., `"2026-01-01T00:00:00Z"`).
3. `fetch_mode` must be `"fixture"`.
4. `collection_method` must be `"fixture"`.
5. Fixture records must produce identical output on every run (deterministic).
6. Source URLs in fixture data must be stable and verifiable — real HN item URLs or GitHub issue URLs, not synthetic placeholders.
7. The preparer must document where the fixture data originated (e.g., "manually collected from HN on 2026-05-13").

### Mode C — Live Opt-In Collection

HN Algolia or GitHub Issues live collection with explicit founder approval.

| Attribute | Value |
|-----------|-------|
| **Allowed without live API approval** | **No** — explicitly forbidden |
| **Requires founder approval** | Yes — AG-1 (live HN), AG-2 (live GitHub), AG-3 (repo allowlist) |
| **Requires live API calls** | Yes — HN Algolia API or GitHub Issues API |
| **Query plan** | Must use the approved HN Pilot Query Plan and/or GitHub Issues Repo Allowlist and Query Plan |
| **Output policy** | Must write runtime outputs only to explicit `output_dir` |
| **Repository artifacts** | No default writes to `artifacts/` or any repository path |

#### Mode C Rules

1. Live collection must not be the default. It requires explicit, recorded founder approval.
2. If founder approves live HN but not live GitHub, combine live HN (Mode C for HN) + manual bounded GitHub input (Mode A for GitHub).
3. If founder approves live GitHub but not live HN, combine manual bounded HN input (Mode A for HN) + live GitHub (Mode C for GitHub).
4. If both live sources are approved, still enforce collection caps (see Section 8) and `output_dir` (see Section 12).
5. The `fetch_mode` field must be `"live_opt_in"`.
6. Each live collection call must be logged with timestamp, query, and record count.
7. Rate limiting must be respected. If rate-limited, record in `quality_flags: ["source_access_limited"]`.

### 2.1 Default Mode Recommendation

| Scenario | Recommendation |
|----------|---------------|
| Live HN + live GitHub not approved | Use **Mode A** (manual bounded) or **Mode B** (fixture/prepared JSON) |
| Live HN approved, live GitHub not approved | **Mode C for HN** + **Mode A for GitHub** |
| Live GitHub approved, live HN not approved | **Mode A for HN** + **Mode C for GitHub** |
| Both live sources approved | **Mode C for both**, still enforcing caps and `output_dir` |

**For the first operational dry cycle:** Mode A or Mode B is recommended unless the founder explicitly approves live collection.

---

## 3. Required Raw Evidence Fields

Every input record, regardless of input mode, must have these minimum required fields populated. These align with the [Raw Evidence Artifact Schema](../contracts/raw_evidence_artifact_schema.md) and the existing `RawEvidence` dataclass.

### 3.1 Mandatory Fields

| # | Field | Type | Description | Mode A (Manual) | Mode B (Fixture) | Mode C (Live) |
|---|-------|------|-------------|-----------------|------------------|---------------|
| 1 | `evidence_id` | `string` | Stable, deterministic ID — format `raw_{source_id}_{source_specific_id}` | Required | Required | Required |
| 2 | `source_id` | `string` | Canonical source identifier | Required | Required | Required |
| 3 | `source_type` | `string` | Source category enum | Required | Required | Required |
| 4 | `source_url` | `string` | Real `http(s)://` URL to source item | Required | Required | Required |
| 5 | `title` | `string` | Source item title, non-empty | Required | Required | Required |
| 6 | `body` or `excerpt` | `string` | Source item body or excerpt, non-empty | Required | Required | Required |
| 7 | `evidence_kind` | `string` | Classification hint (see Section 3.3) | Required | Required | Required |
| 8 | `collected_at` or `prepared_at` | `string` | ISO 8601 UTC timestamp of collection/preparation | Required | Required | Required |
| 9 | `raw_metadata` | `object` | Source-specific metadata dict | Required | Required | Required |
| 10 | `quality_flags` | `array[string]` | Quality flags list (may be empty but must be present) | Required | Required | Required |
| 11 | `author_or_context` | `string` | Privacy-safe role/context label (if available) | Required if available | Required if available | Required if available |

### 3.2 Additional Fields (Strongly Recommended)

| # | Field | Type | Description |
|---|-------|------|-------------|
| 12 | `created_at` or `source_created_at` | `string` or `null` | Original item creation timestamp from source (ISO 8601) |
| 13 | `language` | `string` | Language code or `"unknown"` |
| 14 | `topic_id` | `string` | Pipeline topic driving this fetch |
| 15 | `query_kind` | `string` | Query type for this fetch |
| 16 | `content_hash` | `string` | SHA-256 of normalized `title + body` |

### 3.3 Valid `evidence_kind` Values

| `evidence_kind` | Description | Typical Source |
|-----------------|-------------|---------------|
| `pain_signal_candidate` | User describes frustration, problem, or unmet need | HN, GitHub Issues |
| `workaround` | User describes a workaround, hack, or makeshift solution | HN, GitHub Issues |
| `complaint` | User voices a complaint about existing tool/service | HN |
| `feature_request` | User requests a specific feature or capability | GitHub Issues |
| `bug_report` | User reports a bug or defect | GitHub Issues |
| `solution_pattern` | Describes an existing solution approach or product pattern | HN (Show HN) |
| `unknown` | Cannot be classified; requires downstream review | Any |

### 3.4 Explicitly Forbidden Fields

- `source_url` as `urn:oos:*` — forbidden. Reject the record.
- `source_url` as `github://issues/{id}` — forbidden. Reject the record.
- `source_url` as an API URL (e.g., `https://api.github.com/repos/...`) — forbidden as `source_url`. May be preserved in `raw_metadata` but `source_url` must be the canonical `html_url`.
- Placeholder or guessed `evidence_id` — forbidden. Must follow the `raw_{source_id}_{source_specific_id}` pattern.

---

## 4. Canonical Source Identity

### 4.1 Allowed Source Identities

| Source | `source_id` | `source_type` | URL Pattern |
|--------|-------------|---------------|-------------|
| Hacker News | `hacker_news` | `discussion` | `https://news.ycombinator.com/item?id=<id>` |
| GitHub Issues | `github_issues` | `issue_tracker` | `https://github.com/<owner>/<repo>/issues/<number>` |

### 4.2 Rejected Source Identities

The following `source_id` values are **rejected** if they appear in any pilot input record. This is a gate violation:

| Rejected `source_id` | Reason |
|----------------------|--------|
| `product_hunt` | Deferred to v2.14+ |
| `pimenov_ai` | Deferred to v2.14+ |
| `reddit` | Deferred to v2.14+ |
| `discord` | Deferred to v2.14+ |
| `slack` | Deferred to v2.14+ |
| `x_twitter` / `twitter` / `x` | Deferred to v2.14+ |
| `alternative_to` | Deferred to v2.14+ |
| `yc` / `y_combinator` / `crunchbase` | Deferred to v2.14+ |
| App marketplace identifiers | Deferred to v2.14+ |
| Job board identifiers | Deferred to v2.14+ |
| Blog / newsletter identifiers | Deferred to v2.14+ |
| `broad_web_crawl` | Deferred; scope violation |
| Unknown `source_id` not in allowed list | Scope violation |
| Unknown `source_type` not in allowed list | Scope violation |

### 4.3 Stack Exchange Policy

`stack_exchange` / `stack_overflow` are **rejected by default**. They may only appear if:
1. The founder has explicitly approved the Stack Exchange stretch (AG-4).
2. The approval is recorded in the approval record.
3. The input preparation notes document the stretch approval.

Without explicit stretch approval, Stack Exchange records are treated identically to other deferred sources — rejected.

---

## 5. Source URL Policy

### 5.1 HN URL Format

| Item Type | Required `source_url` Format | Example |
|-----------|------------------------------|---------|
| Story / Ask HN / Show HN / Launch HN | `https://news.ycombinator.com/item?id=<objectID>` | `https://news.ycombinator.com/item?id=41712345` |
| Comment | `https://news.ycombinator.com/item?id=<comment_id>` | `https://news.ycombinator.com/item?id=41712346` |

### 5.2 GitHub URL Format

| Item Type | Required `source_url` Format | Example |
|-----------|------------------------------|---------|
| Issue | `https://github.com/<owner>/<repo>/issues/<number>` | `https://github.com/langchain-ai/langchain/issues/12345` |

### 5.3 URL Rejection Rules

| # | Condition | Action |
|---|-----------|--------|
| R-1 | Missing `source_url` | **Reject record** — count in `missing_url_count` |
| R-2 | `source_url` is `urn:oos:*` | **Reject record** — count in `placeholder_url_count` |
| R-3 | `source_url` is `github://*` | **Reject record** — count in `placeholder_url_count` |
| R-4 | `source_url` is an API URL (e.g., `https://api.github.com/repos/...`) | **Reject record** — `source_url` must be canonical, not API |
| R-5 | `source_url` is guessed (preparer is uncertain) | **Reject record** — do not include |
| R-6 | `source_url` is non-http(s) (e.g., `ftp://`, no scheme) | **Reject record** |
| R-7 | `source_url` is malformed (no hostname, e.g., `"https://"`) | **Reject record** |
| R-8 | URL does not match expected source identity pattern | **Reject record** (e.g., GitHub URL on an HN record) |

### 5.4 PR URL Rejection (GitHub)

Any URL matching `https://github.com/<owner>/<repo>/pull/<number>` is a **pull request URL**, not an issue URL. These must be rejected from GitHub Issues input. The `pull_request` key check is mandatory and non-configurable.

---

## 6. Input Validation Checklist

Before running the pilot, the preparer must confirm **all** of the following:

### 6.1 Source Identity Validation

- [ ] **V-1** All records have non-empty `source_id`.
- [ ] **V-2** All records have non-empty `source_type`.
- [ ] **V-3** Only allowed `source_id` values present: `hacker_news`, `github_issues`.
- [ ] **V-4** Only allowed `source_type` values present: `discussion`, `issue_tracker`.
- [ ] **V-5** No deferred `source_id` values present (see Section 4.2 rejection list).
- [ ] **V-6** No unknown `source_id` values present.
- [ ] **V-7** Stack Exchange present only if explicitly stretch-approved.

### 6.2 Source URL Validation

- [ ] **V-8** Every record has a non-empty `source_url`.
- [ ] **V-9** Every `source_url` uses `http://` or `https://` scheme.
- [ ] **V-10** No `urn:oos:*` placeholders.
- [ ] **V-11** No `github://*` fallback URLs.
- [ ] **V-12** No API URLs as `source_url`.
- [ ] **V-13** HN URLs match `https://news.ycombinator.com/item?id=<id>`.
- [ ] **V-14** GitHub URLs match `https://github.com/<owner>/<repo>/issues/<number>`.
- [ ] **V-15** No PR URLs in GitHub input (`/pull/` path).
- [ ] **V-16** No malformed URLs (missing hostname, invalid scheme).
- [ ] **V-17** URL matches the record's `source_id` (HN URL for HN record, GitHub URL for GitHub record).

### 6.3 Content Validation

- [ ] **V-18** Every record has non-empty `title`.
- [ ] **V-19** Every record has non-empty `body` or excerpt.
- [ ] **V-20** Every record has an `evidence_kind` from the valid enum list.
- [ ] **V-21** Every record has a `quality_flags` list present (may be empty `[]`).
- [ ] **V-22** Every record has `raw_metadata` as a JSON object (not null, not string, not array).

### 6.4 Volume and Balance Validation

- [ ] **V-23** Total raw evidence count is within approved caps (see Section 8).
- [ ] **V-24** HN evidence count is within approved caps.
- [ ] **V-25** GitHub evidence count is within approved caps.
- [ ] **V-26** No source exceeds 75% of total evidence (unless founder explicitly approves).
- [ ] **V-27** No GitHub repo exceeds 25% of GitHub evidence.
- [ ] **V-28** No HN query bucket exceeds 30% of HN evidence.

### 6.5 Duplicate and Integrity Validation

- [ ] **V-29** Duplicate `evidence_id` values are identified and documented.
- [ ] **V-30** Duplicates are not silently dropped — either merged with `duplicate_of` set, or documented with drop reason.
- [ ] **V-31** No record has a synthetic/placeholder `evidence_id`.

### 6.6 Output Directory

- [ ] **V-32** `output_dir` is selected and recorded in pilot run notes.
- [ ] **V-33** `output_dir` is outside committed repository artifacts (unless explicitly approved).
- [ ] **V-34** If `output_dir` is within the repository tree, explicit founder approval is recorded.

### 6.7 Validation Outcome

- **All V-1 through V-34 pass** → input is ready for pilot run.
- **Any V-1 through V-31 fail** → input is **rejected**; do not run the pilot; fix input and re-validate.
- **V-32 through V-34 fail** → fix output directory; re-validate.

---

## 7. Volume Targets

### 7.1 Operational Run Targets (Mode C or combined)

| Artifact | Target | Cap |
|----------|--------|-----|
| Total raw evidence | 50–150 | Hard cap: 150 |
| HN raw evidence | 25–75 | Cap: 100 |
| GitHub raw evidence | 25–75 | Cap: 100 |

### 7.2 Dry/Manual Cycle Targets (Mode A or Mode B)

| Artifact | Target | Minimum |
|----------|--------|---------|
| Total raw evidence | 10–25 | 10 |
| HN raw evidence | 5–15 | 5 |
| GitHub raw evidence | 5–15 | 5 |

Additional dry-cycle constraints:
- Minimum **two sources represented** if possible.
- If only **one source** is used, document why the other source could not be prepared.
- A dry cycle producing fewer than 10 total records is not automatically a failure but requires a documented explanation.

### 7.3 Caps

| Cap | Value |
|-----|-------|
| No source > 75% of total evidence | Enforced; requires founder approval to override |
| No GitHub repo > 25% of GitHub evidence | Enforced; requires founder approval to override |
| No HN query bucket > 30% of HN evidence | Enforced; requires founder approval to override |
| Hard cap total | 150 unless founder explicitly approves more |

### 7.4 Cap Enforcement

- Caps are counted and enforced during input validation (Section 6).
- If a cap is exceeded, the preparer must either:
  - Trim input to comply with caps (documenting which records were removed and why), OR
  - Obtain explicit founder approval to exceed the cap (recorded in approval record).
- Caps cannot be exceeded silently.

---

## 8. Quality Labeling Before Run

The preparer must mark or preserve quality flags on every record before the pilot run. Flags are set in the `quality_flags` array.

### 8.1 Required Quality Flags to Apply

The preparer must inspect each record and apply any applicable flags:

| Flag | Trigger | When Required |
|------|---------|---------------|
| `low_text_context` | Body < 100 characters or missing substantive content | Always when applicable |
| `suspected_self_promo` | Content appears self-promotional (launch, "check out my startup") | Always when applicable |
| `launch_hype` | Record is a product launch or announcement without pain context | Always when applicable |
| `flamewar_or_meta_discussion` | Heated debate about tools/languages; meta-discussion about the platform itself | Always when applicable |
| `bot_generated` | Record created by automated bot (dependabot, renovate, etc.) | Always when applicable |
| `stale_issue` | No activity in > 365 days; issue is old and abandoned | Always when applicable |
| `maintainer_housekeeping` | Chore/build/CI/release task, not user pain | Always when applicable |
| `duplicate_or_invalid` | Labeled `duplicate` or `invalid` in source | Always when applicable |
| `wontfix_or_not_planned` | `state_reason == "not_planned"` or label `wontfix` | Always when applicable |
| `requires_manual_review` | Classification uncertain; preparer cannot determine signal quality | When uncertain |

### 8.2 Relevance Boosting Flags

These flags may be set to boost relevance for downstream processing:

| Flag | Trigger |
|------|---------|
| `integration_pain` | Body contains integration/connector/compatibility pain keywords |
| `debugging_pain` | Body contains debug/trace/observability pain keywords |
| `reliability_pain` | Body contains reliability/flaky/timeout/crash keywords |
| `workflow_pain` | Body contains manual/workaround/automation gap keywords |
| `business_cost_signal` | Evidence of time loss, money loss, or revenue impact |
| `workaround_signal` | Evidence of user-built hacks, scripts, or manual workarounds |

### 8.3 Flag Policy

- `quality_flags` must always be present as an array — use `[]` if no flags apply.
- Flags are advisory, not blocking. A flagged record is still included in input.
- The preparer should be conservative: when in doubt, use `requires_manual_review`.
- Downstream processing may use flags to prioritize or deprioritize records.

---

## 9. Manual Input Template

The following is a compact JSON example showing the minimum expected shape for manual (Mode A) or fixture (Mode B) input. Content is synthetic but follows the required schema.

**Do not use this example as live input. It is a structural template only.**

### 9.1 HN Record Example (Synthetic)

```json
{
  "evidence_id": "raw_hacker_news_41712345",
  "source_id": "hacker_news",
  "source_type": "discussion",
  "source_url": "https://news.ycombinator.com/item?id=41712345",
  "title": "Ask HN: How do you debug failing AI agent workflows in production?",
  "body": "We have a multi-agent setup with LangChain and keep running into cases where agents silently fail mid-workflow. Tracing shows the agent stopped but no error was thrown. We're resorting to manual log inspection and it's taking hours per incident. Has anyone solved this reliably?",
  "evidence_kind": "pain_signal_candidate",
  "collected_at": "2026-05-13T12:00:00Z",
  "source_created_at": "2026-05-10T15:30:00Z",
  "language": "en",
  "author_or_context": "Ask HN author (privacy-safe)",
  "raw_metadata": {
    "objectID": "41712345",
    "points": 85,
    "num_comments": 42,
    "type": "story",
    "tags": ["ask-hn", "ai", "debugging"],
    "author_present": true
  },
  "quality_flags": ["debugging_pain", "reliability_pain", "workaround_signal"],
  "collection_method": "fixture",
  "access_policy": "public_api",
  "extraction_notes": "manual_summary; synthetic example"
}
```

### 9.2 GitHub Issues Record Example (Synthetic)

```json
{
  "evidence_id": "raw_github_issues_langchain_ai_langchain_28456",
  "source_id": "github_issues",
  "source_type": "issue_tracker",
  "source_url": "https://github.com/langchain-ai/langchain/issues/28456",
  "title": "AgentExecutor silently drops tool call results when output exceeds context window",
  "body": "When using AgentExecutor with a tool that returns large outputs, the agent occasionally receives an empty result instead of a truncated or errored response. There is no warning, no error log, and no way to detect this happened except by manually comparing tool output to agent input. This has caused production incidents where the agent made decisions based on missing data.\n\nReproduction: Use any tool returning >10KB output with gpt-4-turbo. About 20% of calls show this behavior.\n\nImpact: Blocking production deployment for 3 teams in our org.",
  "evidence_kind": "bug_report",
  "collected_at": "2026-05-13T12:00:00Z",
  "source_created_at": "2026-05-09T08:15:00Z",
  "source_updated_at": "2026-05-12T22:30:00Z",
  "language": "en",
  "author_or_context": "Issue reporter (privacy-safe)",
  "raw_metadata": {
    "issue_number": 28456,
    "repo": "langchain-ai/langchain",
    "labels": ["bug", "high-priority", "needs-repro"],
    "state": "open",
    "comments_count": 12,
    "is_pull_request": false,
    "author_present": true
  },
  "quality_flags": ["reliability_pain", "debugging_pain", "business_cost_signal"],
  "collection_method": "fixture",
  "access_policy": "public_api",
  "extraction_notes": "manual_summary; synthetic example"
}
```

### 9.3 Template Notes

- Replace synthetic content with real data when preparing actual input.
- `evidence_id` must be deterministic: `raw_{source_id}_{source_specific_id}`.
- `source_url` must be a real, verifiable URL — never a synthetic placeholder.
- `collected_at` for fixture/manual should use a fixed date, not the current timestamp (for determinism).
- `quality_flags` should reflect actual content quality, not be copy-pasted from this template.
- In a real input package, HN and GitHub records go into separate artifacts (one `source_id` per artifact), but the combined example here illustrates both shapes.

---

## 10. Approval Matrix

| # | Action | Approval Required? | Approver | Notes |
|---|--------|-------------------|----------|-------|
| 1 | Manual bounded input (Mode A) | No | — | Manual curation is inherently approved as part of pilot execution |
| 2 | Fixture/prepared JSON input (Mode B) | No | — | Fixture assembly from approved public URLs is within pilot scope |
| 3 | Live HN collection (Mode C for HN) | **Yes** | Founder | AG-1: Must not be default; explicit opt-in required |
| 4 | Live GitHub Issues collection (Mode C for GitHub) | **Yes** | Founder | AG-2: Must not be default; explicit opt-in required |
| 5 | Final GitHub repo allowlist | **Yes** | Founder | AG-3: Founder must review and approve the specific repos before collection |
| 6 | Stack Exchange stretch inclusion | **Yes** | Founder | AG-4: Must not be included in default pilot path |
| 7 | Committing runtime pilot artifacts to repository | **Yes** | Founder | AG-5: No runtime outputs committed without explicit approval |
| 8 | Source expansion beyond HN + GitHub | **Yes** | Founder | AG-6: No additional sources may be added to the pilot |
| 9 | Exceeding collection caps | **Yes** | Founder | Document which cap is exceeded and why |
| 10 | Single-source-only dry cycle | No | — | Must document why the second source could not be prepared |
| 11 | Go/No-Go finalization | **Yes** | Founder | AG-7: Decision is founder-made, evidence-supported |

### 10.1 Approval Gate Timing

| Gate | When Required |
|------|---------------|
| AG-1, AG-2, AG-3 | Before Pilot Input Preparation (this procedure) if live collection is chosen |
| AG-4 | Before Pilot Input Preparation if stretch is desired |
| AG-5 | After pilot run, before committing outputs |
| AG-6 | Anytime before source expansion (enforced by scope) |
| AG-7 | After founder review, before finalizing v2.13 |

### 10.2 Recording Approvals

Every approval must be recorded in the `approval_record.md` or `approval_record.json` (see Section 13) with:
- What was approved.
- Who approved it (founder).
- When it was approved (timestamp).
- Any conditions or notes.

---

## 11. Output Directory Policy

### 11.1 Core Rules

| # | Rule |
|---|------|
| 1 | Runtime outputs must use an **explicit `output_dir`** provided by the caller. |
| 2 | **No default writes** to `artifacts/` or any repository path. |
| 3 | Generated pilot outputs **stay uncommitted** unless explicitly approved (AG-5). |
| 4 | If outputs are retained for evidence, they must be stored under a **clearly named pilot output folder** outside normal repository commit flow. |
| 5 | `output_dir` should be recorded in pilot run notes and in the input manifest. |
| 6 | The `output_dir` path must be absolute or relative to a well-defined, documented root. |

### 11.2 Acceptable `output_dir` Conventions

| Convention | Example | Committed? |
|------------|---------|------------|
| External directory outside repo | `C:\pilot_outputs\cycle_1\` | No |
| Temp directory | `%TEMP%\oos_pilot_cycle_1\` | No |
| Repository path with explicit approval | `artifacts\discovery\pilot_runs\cycle_1\` | Only if AG-5 approved |

### 11.3 What Must NOT Happen

- The pilot orchestrator must not write to `artifacts/` unless the caller explicitly provides it as `output_dir`.
- Input preparation scripts (if any) must not write output to committed paths.
- Validation outputs must not be committed as repository artifacts.
- No file in `docs/`, `src/`, `tests/`, `scripts/`, `config/`, or `examples/` may be created or modified as a pilot runtime output.

---

## 12. Prepared Input Package

The input preparation procedure produces the following files before the pilot run begins. These are **runtime/pre-run files** and should not be committed unless explicitly approved.

### 12.1 Package Contents

| # | File | Format | Description | Required? |
|---|------|--------|-------------|-----------|
| 1 | `raw_evidence.json` (or per-source equivalents) | JSON | Bounded input evidence records | **Yes** |
| 2 | `input_manifest.md` or `input_manifest.json` | Markdown or JSON | Manifest describing what is in the input package | **Yes** |
| 3 | `source_scope_check.md` or `source_scope_check.json` | Markdown or JSON | Results of source scope validation (V-1 through V-7) | **Yes** |
| 4 | `traceability_check.md` or `traceability_check.json` | Markdown or JSON | Results of traceability validation (V-8 through V-17) | **Yes** |
| 5 | `approval_record.md` or `approval_record.json` | Markdown or JSON | Record of all approvals granted for this input preparation | **Yes** |
| 6 | `notes_on_manual_selection.md` | Markdown | Notes explaining manual selection decisions (required if Mode A used) | Only if Mode A |

### 12.2 Input Manifest Contents

The input manifest must describe:

- Chosen input mode(s) — which mode for HN, which mode for GitHub.
- Total record count, per-source record count.
- Time range of evidence (earliest and latest `source_created_at`).
- Query buckets covered (for HN) and repos covered (for GitHub).
- List of any records excluded and why.
- `output_dir` selected.
- Approvals granted (cross-reference to approval record).
- Known limitations or gaps (e.g., "only 3 HN records because...", "finance repos underrepresented because...").

### 12.3 Commitment Policy

- These files are pre-run preparation artifacts.
- They must **not** be committed to the repository unless the founder explicitly approves committing them (AG-5).
- If the founder wants to preserve the input preparation package for audit, it should be stored in the `output_dir` alongside pilot outputs.
- The input manifest path should be recorded in the pilot run manifest (`pilot_run_manifest.json`).

---

## 13. Pre-Run Go/No-Go Checklist

Before the pilot run can begin, confirm all of the following. If any item is not confirmed, the pilot run must be blocked until it is resolved.

| # | Question | Expected Answer | Status |
|---|----------|----------------|--------|
| 1 | Source scope approved? | Only `hacker_news` and `github_issues` present; no deferred sources | [ ] |
| 2 | Live access approved if used? | If Mode C: AG-1/AG-2 recorded in approval record. If Mode A/B: N/A, confirmed no live access needed. | [ ] |
| 3 | GitHub repo allowlist approved if used? | If GitHub data present: AG-3 recorded. If no GitHub data: N/A, documented why. | [ ] |
| 4 | Input volume within caps? | Total ≤ 150; per-source within caps; no dominance violations | [ ] |
| 5 | Source URL traceability clean? | Zero missing URLs, zero placeholders, zero API URLs as `source_url` | [ ] |
| 6 | Deferred sources absent? | Validation V-5 through V-7 pass | [ ] |
| 7 | `output_dir` selected? | Explicit directory chosen and recorded in input manifest | [ ] |
| 8 | Founder review time reserved? | Founder has confirmed availability within the review timebox (48 hours, max 2 hours active) | [ ] |
| 9 | Dry/manual fallback documented? | If live access not used: Mode A or Mode B notes explain why and how input was prepared | [ ] |
| 10 | Input validation passed? | All V-1 through V-34 pass (Section 6) | [ ] |
| 11 | Approval record complete? | All required approvals recorded with timestamps | [ ] |
| 12 | Input manifest complete? | Manifest describes all required fields | [ ] |

**All items must be confirmed before the pilot run begins.**

---

## 14. Failure Handling

### 14.1 If Input Validation Fails

| # | Rule |
|---|------|
| 1 | **Do not run the pilot.** Block execution. |
| 2 | **Document the reason** for the failure in the input manifest. |
| 3 | **Fix the input** or reduce scope to eliminate the failure. |
| 4 | **Do not silently drop malformed records** unless the drop reason is recorded in the input manifest. |
| 5 | **Do not patch source identity** to bypass the gate (e.g., do not change `source_id` from `product_hunt` to `hacker_news`). |
| 6 | **Do not replace missing `source_url`** with a placeholder. Records without `source_url` must be removed. |
| 7 | **Do not edit `source_url`** to make a malformed URL pass validation. |
| 8 | After fixing, **re-run the full validation checklist** (Section 6). |

### 14.2 If Caps Are Exceeded

1. Identify which cap is exceeded.
2. Trim input to comply, documenting which records were removed and why.
3. If trimming would eliminate valuable evidence, request founder approval to exceed the cap (recorded in approval record).
4. Do not proceed with exceeded caps without approval.

### 14.3 If Source Scope Violation Detected

1. Identify the violating record(s).
2. Remove them from input.
3. Document removal in input manifest.
4. Do not run the pilot with deferred source data present.
5. If the violation is systemic (e.g., many records from the wrong source), escalate.

### 14.4 If Traceability Fails

1. Identify records with missing, placeholder, or malformed URLs.
2. If `source_url` can be corrected (e.g., API URL → canonical `html_url`), correct it and document the correction.
3. If `source_url` cannot be corrected, remove the record.
4. Do not proceed with untraceable records.

---

## 15. Dry Cycle / Manual Fallback

### 15.1 When to Use

Dry cycle (Mode A or Mode B) is the default path when:
- Live HN collection is not approved (AG-1 not granted).
- Live GitHub Issues collection is not approved (AG-2 not granted).
- The founder wants to test the pipeline with small, controlled input before authorizing live collection.

### 15.2 Dry Cycle Minimum Requirements

| Requirement | Value |
|-------------|-------|
| Total raw evidence | 10–25 records |
| HN raw evidence | 5–15 records |
| GitHub raw evidence | 5–15 records |
| Minimum sources | 2 (HN + GitHub) if possible |
| P0 HN queries covered | At least 5 of 10 P0 queries |
| P0 GitHub repos covered | At least 5 of 7 P0 repos |
| P0 GitHub repos with ≥ 1 issue | At least 3 |
| Documentation | If only one source used, document why |

### 15.3 Manual Fallback Procedure

If live collection was planned but cannot proceed:

1. Stop live collection path.
2. Switch to Mode A (manual bounded input).
3. Manually collect URLs from HN and GitHub matching P0 queries and recommended repos.
4. Prepare input JSON following this procedure.
5. Document the fallback in `notes_on_manual_selection.md`.
6. Re-validate input (Section 6) before running pilot.

---

## 16. Definition of Done

Item 5 is done when:

- [ ] **5.1** Input preparation procedure exists at `docs/decisions/pilot_input_preparation_procedure_v2_13.md`.
- [ ] **5.2** Input modes are defined: Mode A (manual bounded), Mode B (fixture/prepared JSON), Mode C (live opt-in collection).
- [ ] **5.3** Default mode recommendation is stated: first dry cycle should use Mode A or Mode B.
- [ ] **5.4** Required raw evidence fields are defined: 11 mandatory fields, 5 recommended fields, valid `evidence_kind` values.
- [ ] **5.5** Canonical source identity rules are defined: allowed `source_id`/`source_type` pairs, rejection list.
- [ ] **5.6** Source URL policy is explicit: HN and GitHub URL formats, rejection rules, PR URL rejection.
- [ ] **5.7** Input validation checklist exists: 34 checks across 7 categories.
- [ ] **5.8** Volume targets defined: operational (50–150) and dry-cycle (10–25) with caps.
- [ ] **5.9** Quality labeling rules defined: 16 quality flags with triggers.
- [ ] **5.10** Manual input template exists: compact JSON with one HN record, one GitHub record, synthetic content.
- [ ] **5.11** Approval matrix exists: 11 rows covering all actions.
- [ ] **5.12** Output directory policy exists: 6 rules, acceptable conventions, prohibited behaviors.
- [ ] **5.13** Prepared input package contents defined: 6 expected files with commitment policy.
- [ ] **5.14** Pre-run go/no-go checklist exists: 12 questions.
- [ ] **5.15** Failure handling defined: input validation failure, cap exceedance, source scope violation, traceability failure.
- [ ] **5.16** Dry cycle / manual fallback procedure defined.
- [ ] **5.17** `.\scripts\dev-git-check.ps1` passes.
- [ ] **5.18** One local commit exists with message: `[v2.13] 5 define pilot input preparation`.

---

*Pilot Input Preparation Procedure v2.13. Operational planning document. Does not authorize live collection. Does not modify source code, tests, scripts, or pipeline behavior.*
