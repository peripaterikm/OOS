# Pilot Cycle 1 — Input Manifest

**Manifest ID:** `pilot_cycle_1_input_manifest_v2_13`
**Run ID:** `<pilot_run_YYYY-MM-DD_XXXXXXXX>`
**Input Mode:** Mode A/B — Bounded Manual Input
**Prepared by:** `<founder_or_operator_name>`
**Prepared at:** `<ISO_8601_UTC_timestamp>`
**Template version:** v2.13

---

## 1. Input Package Summary

| Field | Value |
|-------|-------|
| Input mode selected | Mode A/B — Bounded Manual Input |
| Live APIs called during preparation | No |
| Collection method | Manual curation of public HN and GitHub URLs |
| Total raw evidence records | `<N>` |
| HN raw evidence records | `<N>` |
| GitHub Issues raw evidence records | `<N>` |
| Earliest `source_created_at` | `<ISO_8601_UTC>` |
| Latest `source_created_at` | `<ISO_8601_UTC>` |
| `output_dir` selected | `<path>` |
| Input template file | `pilot_cycle_1_manual_input_template_v2_13.json` |

---

## 2. Source Counts

| Source | `source_id` | `source_type` | Count | % of Total |
|--------|-------------|---------------|-------|-----------|
| Hacker News | `hacker_news` | `discussion` | `<N>` | `<N>%` |
| GitHub Issues | `github_issues` | `issue_tracker` | `<N>` | `<N>%` |
| **Total** | | | **`<N>`** | **100%** |

### Anti-Dominance Check

| Rule | Status |
|------|--------|
| No source > 75% of total | [ ] Passed / [ ] Not applicable (2-source split) |
| No GitHub repo > 25% of GitHub evidence | [ ] Passed — list repos and counts below |
| No HN query bucket > 30% of HN evidence | [ ] Passed — list buckets and counts below |

---

## 3. HN Query Buckets Used

List each HN query bucket that contributed evidence. Reference the [HN Pilot Query Plan v2.13](../decisions/hacker_news_pilot_query_plan_v2_13.md), Sections 4 and 11.

| # | Priority | Bucket | Query | Items Collected |
|---|----------|--------|-------|----------------|
| 1 | P0 | A | "AI agent debugging" | `<N>` |
| 2 | P0 | A | "agent observability" | `<N>` |
| 3 | P0 | B | "testing LLM apps" | `<N>` |
| 4 | P0 | C | "ETL pain" | `<N>` |
| 5 | P0 | C | "manual data entry" | `<N>` |
| 6 | P0 | D | "reconciliation automation" | `<N>` |
| 7 | P0 | E | "integration pain" | `<N>` |
| 8 | P0 | F | "Ask HN: What are you using for" | `<N>` |
| 9 | P0 | F | "Ask HN: How do you manage" | `<N>` |
| 10 | P0 | F | "Ask HN: Alternatives to" | `<N>` |
| 11 | P1 | ... | ... | `<N>` |
| 12 | P2 | ... | ... | `<N>` |

### HN Coverage Summary

| Metric | Value |
|--------|-------|
| Total P0 queries (of 10) | `<N>` / 10 |
| P0 queries with ≥ 1 item | `<N>` |
| Total P1 queries used | `<N>` |
| Total P2 queries used | `<N>` |

---

## 4. GitHub Repos Used

List each GitHub repository from which issues were collected. Reference the [GitHub Issues Repo Allowlist and Query Plan v2.13](../decisions/github_issues_repo_allowlist_query_plan_v2_13.md), Sections 5 and 6.

| # | Priority | Repo | Group | Theme | Items Collected |
|---|----------|------|-------|-------|----------------|
| 1 | P0 | `langchain-ai/langchain` | A | AI agent / LLM workflow | `<N>` |
| 2 | P0 | `langchain-ai/langgraph` | A | AI agent / LLM workflow | `<N>` |
| 3 | P0 | `langfuse/langfuse` | B | LLM observability / eval | `<N>` |
| 4 | P0 | `promptfoo/promptfoo` | B | LLM observability / eval | `<N>` |
| 5 | P0 | `dbt-labs/dbt-core` | C | Data workflows / ETL | `<N>` |
| 6 | P0 | `apache/airflow` | C | Data workflows / ETL | `<N>` |
| 7 | P0 | `n8n-io/n8n` | D | Automation / integrations | `<N>` |
| 8 | P1 | `microsoft/autogen` | A | AI agent / LLM workflow | `<N>` |
| 9 | P1 | `Arize-ai/phoenix` | B | LLM observability / eval | `<N>` |
| 10 | P1 | `frappe/erpnext` | E | Finance / ops / reporting | `<N>` |
| 11 | P1/P2 | ... | ... | ... | `<N>` |

### GitHub Coverage Summary

| Metric | Value |
|--------|-------|
| Total P0 repos (of 7) | `<N>` / 7 |
| P0 repos with ≥ 1 issue | `<N>` / 7 |
| Total P1 repos used | `<N>` |
| Total P2 repos used | `<N>` |

---

## 5. Manual Selection Notes

### Inclusion Decisions

- **Why these items were selected:** `<explain the manual curation logic: which criteria were applied, which themes were prioritized, how noise was excluded>`

### Exclusion Decisions

- **Items excluded and why:** `<list any items considered but excluded, with reasons>`

| # | Item | Reason for Exclusion |
|---|------|---------------------|
| 1 | `<title or URL>` | `<reason>` |
| 2 | `<title or URL>` | `<reason>` |

### Evidence Kind Distribution

| `evidence_kind` | Count |
|-----------------|-------|
| `pain_signal_candidate` | `<N>` |
| `workaround` | `<N>` |
| `complaint` | `<N>` |
| `feature_request` | `<N>` |
| `bug_report` | `<N>` |
| `solution_pattern` | `<N>` |
| `unknown` | `<N>` |

### Quality Flag Distribution

| Flag | Count |
|------|-------|
| `debugging_pain` | `<N>` |
| `reliability_pain` | `<N>` |
| `workflow_pain` | `<N>` |
| `integration_pain` | `<N>` |
| `business_cost_signal` | `<N>` |
| `workaround_signal` | `<N>` |
| `low_text_context` | `<N>` |
| `suspected_self_promo` | `<N>` |
| `launch_hype` | `<N>` |
| `stale_issue` | `<N>` |
| `maintainer_housekeeping` | `<N>` |
| `requires_manual_review` | `<N>` |
| Other | `<N>` |

---

## 6. Excluded / Deferred Source Confirmation

| Source | Status | Notes |
|--------|--------|-------|
| Product Hunt | Confirmed excluded | Deferred to v2.14+ |
| pimenov.ai | Confirmed excluded | Deferred to v2.14+ |
| Reddit | Confirmed excluded | Deferred to v2.14+ |
| X / Twitter | Confirmed excluded | Deferred to v2.14+ |
| Discord | Confirmed excluded | Deferred to v2.14+ |
| Slack | Confirmed excluded | Deferred to v2.14+ |
| YC / Crunchbase | Confirmed excluded | Deferred to v2.14+ |
| AlternativeTo | Confirmed excluded | Deferred to v2.14+ |
| Stack Exchange / Stack Overflow | Confirmed excluded | AG-4 NOT APPROVED |
| App marketplaces | Confirmed excluded | Deferred to v2.14+ |
| Job boards | Confirmed excluded | Deferred to v2.14+ |
| Blogs / newsletters | Confirmed excluded | Deferred to v2.14+ |
| Broad web crawl | Confirmed excluded | Scope violation |

**No deferred source records are present in the input package.**

---

## 7. Traceability Confirmation

| Check | Status |
|-------|--------|
| Every record has non-empty `source_url` | [ ] Confirmed |
| All `source_url`s use `http://` or `https://` | [ ] Confirmed |
| Zero `urn:oos:*` placeholders | [ ] Confirmed |
| Zero `github://*` fallback URLs | [ ] Confirmed |
| Zero API URLs as `source_url` | [ ] Confirmed |
| HN URLs match expected pattern | [ ] Confirmed |
| GitHub URLs match expected pattern | [ ] Confirmed |
| Zero PR URLs in GitHub input | [ ] Confirmed |
| Zero malformed URLs | [ ] Confirmed |
| URL matches record `source_id` | [ ] Confirmed |

---

## 8. Known Limitations

Document any known limitations of this input package:

| # | Limitation | Impact | Mitigation |
|---|-----------|--------|------------|
| 1 | `<e.g., Only 3 HN records in Bucket D (finance/SMB)>` | `<impact>` | `<what was done or should be done>` |
| 2 | `<e.g., Finance/SMB repos underrepresented in GitHub evidence>` | `<impact>` | `<what was done or should be done>` |
| 3 | `<e.g., Manual summaries are human-authored and may introduce subjective bias>` | `<impact>` | `<what was done or should be done>` |
| 4 | `<e.g., Dry-cycle volume (10–25) is small; conclusions are tentative>` | `<impact>` | `<what was done or should be done>` |

**Source bias note:** HN skews toward developers and technical founders. GitHub Issues skews toward developers and open-source contributors. Finance, SMB operations, and non-technical ICPs are expected to be underrepresented relative to devtools and AI agent pain. This bias should be documented in the pilot results report and considered in source expansion planning.

---

## 9. Approval Record Cross-Reference

Cross-reference to the approval record at [`pilot_cycle_1_approval_record_template_v2_13.md`](pilot_cycle_1_approval_record_template_v2_13.md).

All live/source expansion approvals default to NOT APPROVED for Mode A/B bounded manual input.

---

## 10. Next Step

After this manifest is complete:

1. Confirm all traceability checks pass (Section 7).
2. Confirm the approval record is complete.
3. Validate input against all 34 checks from the [Run Plan](pilot_cycle_1_run_plan_v2_13.md), Section 7.
4. Select `output_dir` and record it above.
5. Proceed to pilot run per the [Pilot Run Procedure v2.13](../decisions/pilot_run_procedure_v2_13.md).

---

*Input Manifest Template v2.13. Fill all placeholder values with real data after manual collection. Does not contain real evidence. Does not modify source code, tests, scripts, or pipeline behavior.*
