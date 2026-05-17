# OOS v2.13 — Pilot Cycle 1 Run Plan

**Title:** OOS v2.13 — Pilot Cycle 1 Run Plan
**Status:** Active — ready for bounded manual input preparation
**Roadmap item:** v2.13 Operational Pilot Cycle 1 execution
**Branch:** `ops/v2-13-pilot-cycle-1-run`
**Created:** 2026-05-13
**Based on:**
- [Founder ICP and Preference Profile v2.13](../decisions/founder_icp_preference_profile_v2_13.md)
- [Pilot Cycle 1 Brief v2.13](../decisions/pilot_cycle_1_brief_v2_13.md)
- [HN Pilot Query Plan v2.13](../decisions/hacker_news_pilot_query_plan_v2_13.md)
- [GitHub Issues Repo Allowlist and Query Plan v2.13](../decisions/github_issues_repo_allowlist_query_plan_v2_13.md)
- [Pilot Input Preparation Procedure v2.13](../decisions/pilot_input_preparation_procedure_v2_13.md)
- [Pilot Run Procedure v2.13](../decisions/pilot_run_procedure_v2_13.md)
- [Founder Review Protocol v2.13](../decisions/founder_review_protocol_v2_13.md)

---

## 1. Run Mode

**Selected mode: Mode A/B — Bounded Manual Input**

| Attribute | Value |
|-----------|-------|
| | **Mode A** (Manual Bounded Input) — founder/operator manually curates HN + GitHub URLs with human-written summaries |
| | **Mode B** (Fixture / Prepared JSON Input) — manual evidence prepared into deterministic JSON following the input template |
| | **Live API calls** | **None** — no HN Algolia API, no GitHub Issues API |
| | **Live collection approval required** | **No** — Mode A/B does not require AG-1, AG-2, or AG-3 |
| | **Deterministic** | Yes — same input produces same output |
| | **Repeatable** | Yes — re-run reproduces identical artifacts |

### Reason for Mode A/B Selection

- Live HN collection and live GitHub Issues collection have **not been approved**.
- The Pilot Cycle 1 Brief authorizes Mode A/B as the default path when live approval is not granted.
- This bounded manual input cycle provides a controlled, inspectable, small-volume dry run to validate the pipeline before any live API calls.

---

## 2. Target Input Volume

| Source | Target | Minimum | Absolute Cap |
|--------|--------|---------|-------------|
| Hacker News | 5–15 records | 5 | 15 |
| GitHub Issues | 5–15 records | 5 | 15 |
| **Total raw evidence** | **10–25 records** | **10** | **25** |

### Additional Volume Constraints

| Constraint | Value |
|------------|-------|
| No single source > 75% of total evidence | Enforced |
| No GitHub repo > 25% of GitHub evidence | Enforced |
| No HN query bucket > 30% of HN evidence | Enforced |
| Minimum sources represented | 2 (HN + GitHub); if only 1 source used, document why |

---

## 3. Source Scope

### Included Sources

| Source | `source_id` | `source_type` | URL Pattern |
|--------|-------------|---------------|-------------|
| Hacker News | `hacker_news` | `discussion` | `https://news.ycombinator.com/item?id=<id>` |
| GitHub Issues | `github_issues` | `issue_tracker` | `https://github.com/<owner>/<repo>/issues/<number>` |

### Focus Themes (from Pilot Cycle 1 Brief, Section 3)

| # | Focus Area | Description |
|---|------------|-------------|
| F-1 | AI agents debugging / observability / reliability | Agent debugging pain, observability gaps, reliability failures |
| F-2 | Devtools pain around AI workflows | LLM testing, evaluation, prompt management pain |
| F-3 | Data workflow / ETL / automation pain | Data pipeline, ETL, spreadsheet automation pain |
| F-4 | Finance / management reporting automation pain | Accounting, reconciliation, reporting burden |
| F-5 | SMB operational automation | Small business operations, workflow automation |
| F-6 | Integration pain between tools | Cross-tool integration, API, connector pain |
| F-7 | Manual reporting / reconciliation / monitoring | Manual processes, reporting burden, monitoring gaps |

### HN Query Buckets to Cover (from HN Pilot Query Plan, Section 11)

P0 queries are prioritized. At least 5 of 10 P0 queries must be covered.

| Priority | Bucket | Example Query |
|----------|--------|---------------|
| P0 | A | "AI agent debugging", "agent observability" |
| P0 | B | "testing LLM apps" |
| P0 | C | "ETL pain", "manual data entry" |
| P0 | D | "reconciliation automation" |
| P0 | E | "integration pain" |
| P0 | F | "Ask HN: What are you using for", "Ask HN: How do you manage", "Ask HN: Alternatives to" |

### GitHub Repos to Cover (from GitHub Issues Allowlist, Section 6)

First-cycle recommended subset of 10 repos. At least 5 of 7 P0 repos must be covered; at least 3 P0 repos with ≥ 1 issue.

| Priority | Repo | Group |
|----------|------|-------|
| P0 | `langchain-ai/langchain` | A — AI agent / LLM workflow |
| P0 | `langchain-ai/langgraph` | A — AI agent / LLM workflow |
| P0 | `langfuse/langfuse` | B — LLM observability / eval |
| P0 | `promptfoo/promptfoo` | B — LLM observability / eval |
| P0 | `dbt-labs/dbt-core` | C — Data workflows / ETL |
| P0 | `apache/airflow` | C — Data workflows / ETL |
| P0 | `n8n-io/n8n` | D — Automation / integrations |
| P1 | `microsoft/autogen` | A — AI agent / LLM workflow |
| P1 | `Arize-ai/phoenix` | B — LLM observability / eval |
| P1 | `frappe/erpnext` | E — Finance / ops / reporting |

### Excluded Sources

The following sources are **excluded** from Pilot Cycle 1. Their presence in any input record is a gate violation:

| Source | `source_id` | Reason |
|--------|-------------|--------|
| Product Hunt | `product_hunt` | Deferred to v2.14+ (conditional on Go) |
| pimenov.ai | `pimenov_ai` | Deferred to v2.14+ (conditional on Go) |
| Reddit | `reddit` | Deferred to v2.14+ (conditional on Go) |
| X / Twitter | `x_twitter` / `twitter` / `x` | Deferred to v2.14+ (conditional on Go) |
| Discord | `discord` | Deferred to v2.14+ (conditional on Go) |
| Slack | `slack` | Deferred to v2.14+ (conditional on Go) |
| YC / Crunchbase | `yc` / `y_combinator` / `crunchbase` | Deferred to v2.14+ (conditional on Go) |
| AlternativeTo | `alternative_to` | Deferred to v2.14+ (conditional on Go) |
| Stack Exchange / Stack Overflow | `stack_exchange` / `stack_overflow` | Excluded unless founder explicitly approves AG-4 stretch |
| App marketplaces | — | Deferred to v2.14+ |
| Job boards | — | Deferred to v2.14+ |
| Blogs / newsletters | — | Deferred to v2.14+ |
| Broad web crawl | `broad_web_crawl` | Deferred; scope violation |

---

## 4. Required Fields

Every raw evidence record must include the following mandatory fields. See [Pilot Input Preparation Procedure v2.13](../decisions/pilot_input_preparation_procedure_v2_13.md), Section 3.

### Mandatory Fields

| # | Field | Type | Description |
|---|-------|------|-------------|
| 1 | `evidence_id` | `string` | Format: `raw_{source_id}_{source_specific_id}` |
| 2 | `source_id` | `string` | `hacker_news` or `github_issues` |
| 3 | `source_type` | `string` | `discussion` or `issue_tracker` |
| 4 | `source_url` | `string` | Real `http(s)://` URL — no placeholders, no URNs |
| 5 | `title` | `string` | Source item title, non-empty |
| 6 | `body` or `excerpt` | `string` | Source item body or excerpt, non-empty |
| 7 | `evidence_kind` | `string` | One of: `pain_signal_candidate`, `workaround`, `complaint`, `feature_request`, `bug_report`, `solution_pattern`, `unknown` |
| 8 | `collected_at` or `prepared_at` | `string` | ISO 8601 UTC timestamp |
| 9 | `raw_metadata` | `object` | Source-specific metadata dict |
| 10 | `quality_flags` | `array[string]` | Quality flags list (may be empty `[]` but must be present) |
| 11 | `author_or_context` | `string` | Privacy-safe role/context label (if available) |

### Strongly Recommended Fields

| # | Field | Type | Description |
|---|-------|------|-------------|
| 12 | `source_created_at` | `string` or `null` | Original item creation timestamp (ISO 8601) |
| 13 | `language` | `string` | Language code or `"unknown"` |
| 14 | `topic_id` | `string` | Pipeline topic |
| 15 | `query_kind` | `string` | Query type for this fetch |
| 16 | `content_hash` | `string` | SHA-256 of normalized `title + body` |

---

## 5. Source URL Rules

### HN URL Format

```
https://news.ycombinator.com/item?id=<objectID>
```

### GitHub Issues URL Format

```
https://github.com/<owner>/<repo>/issues/<number>
```

### Rejection Rules

| # | Condition | Action |
|---|-----------|--------|
| R-1 | Missing `source_url` | Reject record |
| R-2 | `source_url` is `urn:oos:*` | Reject record |
| R-3 | `source_url` is `github://*` | Reject record |
| R-4 | `source_url` is an API URL (e.g., `https://api.github.com/repos/...`) | Reject record |
| R-5 | `source_url` is guessed / uncertain | Reject record |
| R-6 | `source_url` is non-http(s) | Reject record |
| R-7 | `source_url` is malformed (no hostname) | Reject record |
| R-8 | URL does not match expected source identity pattern | Reject record |
| R-9 | URL is a PR URL (`/pull/` path) | Reject record (PRs excluded) |

---

## 6. Manual Collection Instructions

### Step 1: Prepare Input Template

Use the template at [`pilot_cycle_1_manual_input_template_v2_13.json`](pilot_cycle_1_manual_input_template_v2_13.json) as the starting structure.

### Step 2: Collect HN Evidence (5–15 items)

1. Visit `https://hn.algolia.com/` and search for P0 queries from the HN Pilot Query Plan (Section 11).
2. For each query, identify items that match inclusion criteria:
   - Specific actor (role, job title, clear persona)
   - Specific workflow (described steps, inputs, outputs)
   - Clear pain verb or pain pattern
   - Repeated workaround
   - Time loss, money loss, or business cost
   - Integration friction, reliability/debugging issue, operational burden
3. Collect the `objectID`, title, and a human-written excerpt/summary of the body.
4. Build the `source_url` as `https://news.ycombinator.com/item?id=<objectID>`.
5. Set `source_id = "hacker_news"`, `source_type = "discussion"`.
6. Populate `raw_metadata` with `objectID`, `points`, `num_comments`, `type`, `tags`.
7. Apply quality flags based on visible content.
8. Mark `collection_method = "manual_bounded"`, `extraction_notes = "manual_summary"`.
9. Exclude items matching noise patterns (hype, self-promo, flamewar, generic "AI is cool", low-context comments < 100 chars).

### Step 3: Collect GitHub Issues Evidence (5–15 items)

1. Visit the P0 repos from the GitHub Issues Allowlist (Section 6, recommended first-cycle subset).
2. Navigate to the Issues tab, filter by `is:issue` (exclude PRs).
3. Look for issues that match inclusion criteria:
   - Clear bug / defect / failure with reproduction steps or impact
   - Feature gap with described workflow pain and business/user impact
   - Repeated failure mode (multiple reports)
   - Integration friction, debugging/observability problem
   - Manual workaround described, reliability issue with production impact
4. Collect the `html_url`, issue number, title, and a human-written excerpt of the body.
5. Set `source_id = "github_issues"`, `source_type = "issue_tracker"`.
6. Populate `raw_metadata` with `issue_number`, `repo`, `labels`, `state`, `comments_count`, `is_pull_request: false`.
7. Apply quality flags (bot_generated, stale_issue, low_text_context, maintainer_housekeeping, duplicate_or_invalid, wontfix_or_not_planned).
8. Mark `collection_method = "manual_bounded"`, `extraction_notes = "manual_summary"`.
9. Exclude: PRs, dependency update bots, release/changelog tasks, stale with no evidence, duplicates with no extra evidence, low-context "does not work" without details.

### Step 4: Populate the JSON Template

1. Fill the `metadata` section with actual run metadata.
2. Populate the `raw_evidence` array with real collected records.
3. Ensure every record has all mandatory fields.
4. Ensure `evidence_id` follows the pattern `raw_{source_id}_{source_specific_id}`.
5. Ensure `source_url` is a real, verifiable URL (not a synthetic placeholder).

### Step 5: Validate Input Before Run

Run all 34 validation checks from the [Pilot Input Preparation Procedure](../decisions/pilot_input_preparation_procedure_v2_13.md), Section 6.

---

## 7. Validation Checklist Before Run

Before running the pilot, confirm **all** of the following. If any check fails, do not run the pilot.

### Source Identity Validation

- [ ] **V-1** All records have non-empty `source_id`
- [ ] **V-2** All records have non-empty `source_type`
- [ ] **V-3** Only `hacker_news` and `github_issues` present
- [ ] **V-4** Only `discussion` and `issue_tracker` present
- [ ] **V-5** No deferred `source_id` values present
- [ ] **V-6** No unknown `source_id` values present
- [ ] **V-7** No Stack Exchange unless stretch-approved

### Source URL Validation

- [ ] **V-8** Every record has a non-empty `source_url`
- [ ] **V-9** Every `source_url` uses `http://` or `https://`
- [ ] **V-10** No `urn:oos:*` placeholders
- [ ] **V-11** No `github://*` fallback URLs
- [ ] **V-12** No API URLs as `source_url`
- [ ] **V-13** HN URLs match `https://news.ycombinator.com/item?id=<id>`
- [ ] **V-14** GitHub URLs match `https://github.com/<owner>/<repo>/issues/<number>`
- [ ] **V-15** No PR URLs in GitHub input
- [ ] **V-16** No malformed URLs
- [ ] **V-17** URL matches record's `source_id`

### Content Validation

- [ ] **V-18** Every record has non-empty `title`
- [ ] **V-19** Every record has non-empty `body` or excerpt
- [ ] **V-20** Every record has valid `evidence_kind`
- [ ] **V-21** Every record has `quality_flags` array present
- [ ] **V-22** Every record has `raw_metadata` as a JSON object

### Volume and Balance Validation

- [ ] **V-23** Total raw evidence count is 10–25
- [ ] **V-24** HN evidence count is 5–15
- [ ] **V-25** GitHub evidence count is 5–15
- [ ] **V-26** No source exceeds 75% of total evidence
- [ ] **V-27** No GitHub repo exceeds 25% of GitHub evidence
- [ ] **V-28** No HN query bucket exceeds 30% of HN evidence

### Duplicate and Integrity Validation

- [ ] **V-29** Duplicate `evidence_id` values identified and documented
- [ ] **V-30** Duplicates not silently dropped
- [ ] **V-31** No synthetic/placeholder `evidence_id`

### Output Directory

- [ ] **V-32** `output_dir` selected and recorded
- [ ] **V-33** `output_dir` outside committed repository artifacts (unless AG-5 approved)
- [ ] **V-34** If `output_dir` within repository tree, explicit founder approval recorded

### Validation Outcome

- **All V-1 through V-34 pass** → input is ready for pilot run.
- **Any V-1 through V-31 fail** → input is **rejected**; do not run the pilot; fix input and re-validate.
- **V-32 through V-34 fail** → fix output directory; re-validate.

---

## 8. Explicit `output_dir` Rule

| # | Rule |
|---|------|
| 1 | Runtime outputs must use an **explicit `output_dir`** provided by the caller. |
| 2 | **No default writes** to `artifacts/` or any repository path. |
| 3 | Generated pilot outputs **stay uncommitted** unless AG-5 explicitly approves. |
| 4 | `output_dir` must be recorded in pilot run notes and in the input manifest. |
| 5 | The path must be absolute or relative to a well-defined, documented root. |

### Recommended `output_dir` Conventions

| Convention | Example |
|------------|---------|
| External directory outside repo | `C:\pilot_outputs\cycle_1\` |
| Temp directory | `%TEMP%\oos_pilot_cycle_1\` |
| Repository path with explicit approval | `artifacts\discovery\pilot_runs\cycle_1\` (only if AG-5 approved) |

---

## 9. Do-Not-Proceed Gates

Do **not** proceed to pilot run if any of the following conditions are true:

| # | Condition | Rationale |
|---|-----------|-----------|
| DNP-1 | Input validation incomplete (any V-1 through V-34 not confirmed) | Cannot trust input quality |
| DNP-2 | Traceability is broken (missing URLs, placeholder URLs, API URLs as `source_url`) | Founder cannot verify evidence origin |
| DNP-3 | Deferred sources present in input | Source scope violation |
| DNP-4 | `output_dir` not selected or recorded | No destination for runtime outputs |
| DNP-5 | Live APIs called without founder approval | Violates AG-1, AG-2 approval gates |
| DNP-6 | Source scope expanded beyond HN + GitHub Issues without founder approval | Violates AG-6 |
| DNP-7 | Runtime artifacts committed without AG-5 approval | Violates artifact policy |
| DNP-8 | Portfolio mutated | Violates operational constraint C-6 |
| DNP-9 | `KillReason` records created | Violates operational constraint C-7 |
| DNP-10 | Go/No-Go decision pre-populated before founder review | Founders must make the decision |

---

## 10. What This Run Plan Does NOT Authorize

| # | Prohibited Action | Reason |
|---|-------------------|--------|
| 1 | Live HN Algolia API calls | Requires AG-1 founder approval |
| 2 | Live GitHub Issues API calls | Requires AG-2 founder approval |
| 3 | Source expansion beyond HN + GitHub Issues | Requires Go decision and AG-6 |
| 4 | Stack Exchange inclusion | Requires AG-4 founder approval |
| 5 | Portfolio mutation | Violates operational constraint C-6 |
| 6 | `KillReason` record creation | Violates operational constraint C-7 |
| 7 | Automated Go/No-Go decision | Founder review is mandatory (AG-7) |
| 8 | Committing runtime artifacts without approval | Requires AG-5 |
| 9 | Running the pilot itself | This plan defines the procedure; it does not execute it |
| 10 | Modifying source code, tests, scripts, config, or examples | Docs-only operational item |

---

## 11. Next Step After Templates Are Filled

1. **Fill the manual input template** — replace synthetic placeholders with real collected evidence following the collection instructions (Section 6).
2. **Fill the input manifest template** — document source counts, query buckets used, repos used, selection notes, known limitations.
3. **Fill the approval record template** — document approval status for all gates (all live/source expansion approvals default to NOT APPROVED).
4. **Validate input** — run all 34 checks from Section 7.
5. **Select `output_dir`** — choose an explicit directory outside committed repository paths.
6. **Handoff to pilot run** — execute `run_operational_discovery_pilot()` per the [Pilot Run Procedure v2.13](../decisions/pilot_run_procedure_v2_13.md), Section 5.
7. **Post-run validation** — verify all 21 post-run checks from the Pilot Run Procedure, Section 8.
8. **Founder review** — per the [Founder Review Protocol v2.13](../decisions/founder_review_protocol_v2_13.md).
9. **Go/No-Go decision** — after founder review completes.

---

## 12. References

- [Founder ICP and Preference Profile v2.13](../decisions/founder_icp_preference_profile_v2_13.md)
- [Pilot Cycle 1 Brief v2.13](../decisions/pilot_cycle_1_brief_v2_13.md)
- [HN Pilot Query Plan v2.13](../decisions/hacker_news_pilot_query_plan_v2_13.md)
- [GitHub Issues Repo Allowlist and Query Plan v2.13](../decisions/github_issues_repo_allowlist_query_plan_v2_13.md)
- [Pilot Input Preparation Procedure v2.13](../decisions/pilot_input_preparation_procedure_v2_13.md)
- [Pilot Run Procedure v2.13](../decisions/pilot_run_procedure_v2_13.md)
- [Founder Review Protocol v2.13](../decisions/founder_review_protocol_v2_13.md)
- [Go/No-Go Decision Framework v2.13](../decisions/go_no_go_decision_framework_v2_13.md)
- [Manual Input Template](pilot_cycle_1_manual_input_template_v2_13.json)
- [Input Manifest Template](pilot_cycle_1_input_manifest_template_v2_13.md)
- [Approval Record Template](pilot_cycle_1_approval_record_template_v2_13.md)

---

*Pilot Cycle 1 Run Plan v2.13. Operational execution document. Does not authorize live API calls. Does not run the pilot. Does not modify source code, tests, scripts, or pipeline behavior.*
