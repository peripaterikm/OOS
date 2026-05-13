# OOS v2.13 — Pilot Results Report Template

**Title:** OOS v2.13 — Pilot Results Report Template
**Status:** Draft / operational report template
**Roadmap item:** v2.13 item 8 — Pilot Results Report
**Branch:** `ops/v2-13-operational-pilot-cycle-1`
**Created:** 2026-05-13
**Schema version:** `pilot_results_report_template.v1`
**Based on:**
- [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md)
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md)
- [Pilot Run Procedure v2.13](pilot_run_procedure_v2_13.md)
- [Founder Review Protocol v2.13](founder_review_protocol_v2_13.md)
- [Operational Discovery Pilot Run Contract](../contracts/operational_discovery_pilot_run_contract.md)
- [PainCluster Contract](../contracts/pain_cluster_contract.md)

---

## 1. Purpose

The purpose of this template is to define a standardized report that answers:

- What did the pilot collect?
- What did OOS find?
- Which sources were useful or noisy?
- Which PainClusters and opportunity candidates were produced?
- What did the founder decide?
- Was review manageable?
- Does the pilot support GO, CONDITIONAL GO, or NO-GO?

This report is the input to **item 10 — Go / Conditional Go / No-Go Decision**.

### 1.1 What This Template Is

- A structural specification for the Pilot Cycle 1 Results Report.
- A list of required sections, fields, metrics, and interpretation rules.
- A Markdown template skeleton with placeholder fields.
- An optional JSON companion structure definition.
- An artifact and commit policy for the actual report.

### 1.2 What This Template Is Not

- The actual pilot results report (no runtime data is filled in).
- A pilot run authorization.
- A founder decision artifact.
- A `KillReason` record.
- A portfolio mutation.
- Source code, test, script, or artifact modification.

---

## 2. Required Source Documents / Inputs

The following inputs are expected to be available before the pilot results report is populated:

| # | Input | Format | Description |
|---|-------|--------|-------------|
| 1 | `pilot_run_manifest.json` | JSON | Run metadata: parameters, counts, approvals, limitations |
| 2 | `validation_summary.json` | JSON | Pipeline validation: format checks, traceability pass/fail, source scope compliance |
| 3 | `raw_evidence.json` | JSON | Validated raw evidence records used as input |
| 4 | `candidate_signals.json` | JSON | Extracted candidate signals with scores and source traceability |
| 5 | `pain_clusters.json` | JSON | Synthesized pain clusters with member signals and scores |
| 6 | `source_quality_report.json` | JSON | Machine-readable quality metrics per source/query/repo |
| 7 | `source_quality_report.md` | Markdown | Human-readable quality summary with recommendations |
| 8 | `founder_review_package.json` | JSON | Structured package for founder review |
| 9 | `founder_review_package.md` | Markdown | Human-readable review package |
| 10 | `founder_review_notes_v2_13.md` | Markdown | Structured review notes with decisions, rationales, and markers (from item 7 protocol) |
| 11 | `opportunity_candidates.json` | JSON | Opportunity candidates framed from top-scoring pain clusters (optional) |
| 12 | `duplicates.json` | JSON | Records of detected and merged duplicate evidence items (optional) |
| 13 | `input_manifest.json` or `input_manifest.md` | JSON/Markdown | Manifest describing input package contents, mode, counts, approvals, limitations |
| 14 | `approval_record.json` or `approval_record.md` | JSON/Markdown | Record of all approvals granted for this pilot input |

---

## 3. Report Sections

The pilot results report must contain at minimum the following 12 sections. Each section is defined with required sub-fields and placeholder values.

---

### Section 1 — Executive Summary

**Purpose:** One-page summary for the founder and decision record.

**Required fields:**

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | The explicit `discovery_run_id` used, e.g. `pilot_run_YYYY-MM-DD_<8char_hex>` |
| `run_date` | string | ISO 8601 UTC date of the pilot run |
| `input_mode` | string | One of: `Mode A — Dry/Manual`, `Mode B — Fixture`, `Mode C — Live-Approved` |
| `sources_used` | list[string] | Sources that contributed evidence, e.g. `["hacker_news", "github_issues"]` |
| `raw_evidence_count` | int | Total raw evidence items collected |
| `candidate_signal_count` | int | Total candidate signals extracted |
| `pain_cluster_count` | int | Total pain clusters formed |
| `opportunity_candidate_count` | int | Total opportunity candidates framed (0 if none) |
| `founder_review_completed` | bool | Whether founder review has been completed |
| `preliminary_recommendation` | string | One of: `GO`, `CONDITIONAL GO`, `NO-GO`, `undecided` |
| `summary_paragraph` | string | One-paragraph plain-English summary of the cycle: what was found, what was decided, whether the pipeline appears useful |

**Template skeleton:**

```markdown
## 1. Executive Summary

| Field | Value |
|-------|-------|
| **Run ID** | `<run_id>` |
| **Run Date** | `<date>` |
| **Input Mode** | `<input_mode>` |
| **Sources Used** | `<sources_used>` |
| **Raw Evidence** | `<raw_evidence_count>` |
| **Candidate Signals** | `<candidate_signal_count>` |
| **Pain Clusters** | `<pain_cluster_count>` |
| **Opportunity Candidates** | `<opportunity_candidate_count>` |
| **Founder Review Completed** | `<founder_review_completed>` |
| **Preliminary Recommendation** | `<preliminary_recommendation>` |

### Summary

<summary_paragraph>
```

---

### Section 2 — Source Scope and Compliance

**Purpose:** Confirm that the pilot respected source gates, approval gates, and artifact policy.

**Required checks:**

| # | Check | Expected | Actual | Pass? |
|---|-------|----------|--------|-------|
| SC-1 | Allowed sources used | `hacker_news`, `github_issues` | `<actual_sources>` | `<pass/fail>` |
| SC-2 | Deferred sources absent | Zero deferred sources | `<count>` | `<pass/fail>` |
| SC-3 | Stack Exchange status | Excluded (or stretch-approved) | `<status>` | `<pass/fail>` |
| SC-4 | Live approvals recorded (if Mode C) | AG-1/AG-2 recorded | `<recorded>` | `<pass/fail>` |
| SC-5 | `output_dir` policy followed | Explicit `output_dir` used; no default writes | `<output_dir>` | `<pass/fail>` |
| SC-6 | Committed artifacts approval status | AG-5 status | `<status>` | `<pass/fail>` |
| SC-7 | `source_url` traceability status | Clean — zero missing/placeholder URLs | `<status>` | `<pass/fail>` |

**Template skeleton:**

```markdown
## 2. Source Scope and Compliance

| # | Check | Expected | Actual | Pass? |
|---|-------|----------|--------|-------|
| SC-1 | Allowed sources used | `hacker_news`, `github_issues` | `<actual_sources>` | `<pass/fail>` |
| SC-2 | Deferred sources absent | Zero deferred sources | `<count>` | `<pass/fail>` |
| SC-3 | Stack Exchange status | Excluded (or stretch-approved) | `<status>` | `<pass/fail>` |
| SC-4 | Live approvals (if Mode C) | AG-1/AG-2 recorded | `<recorded>` | `<pass/fail>` |
| SC-5 | `output_dir` policy | Explicit dir; no default writes | `<output_dir>` | `<pass/fail>` |
| SC-6 | Commit artifacts approval | AG-5 status | `<status>` | `<pass/fail>` |
| SC-7 | `source_url` traceability | Clean | `<status>` | `<pass/fail>` |

**Compliance notes:** `<notes>`
```

---

### Section 3 — Evidence Volume and Funnel

**Purpose:** Show the full pipeline funnel from raw evidence to founder-promoted opportunities.

**Required counts:**

| # | Stage | Count |
|---|-------|-------|
| 1 | Raw evidence collected | `<raw_evidence_count>` |
| 2 | Accepted candidate signals | `<accepted_signal_count>` |
| 3 | Weak signals | `<weak_signal_count>` |
| 4 | Noise signals | `<noise_signal_count>` |
| 5 | Pain clusters | `<pain_cluster_count>` |
| 6 | Opportunity candidates | `<opportunity_candidate_count>` |
| 7 | Founder review items | `<reviewed_item_count>` |
| 8 | PROMOTE | `<promote_count>` |
| 9 | PARK | `<park_count>` |
| 10 | KILL | `<kill_count>` |
| 11 | NEEDS_MORE_EVIDENCE | `<needs_more_evidence_count>` |
| 12 | REVISIT_LATER | `<revisit_later_count>` |

**Funnel table:**

```
raw evidence (<N>)
  └── candidate signals (<N>)
        ├── accepted (<N>)
        ├── weak (<N>)
        └── noise (<N>)
              └── pain clusters (<N>)
                    └── opportunity candidates (<N>)
                          └── founder review (<N> items)
                                ├── PROMOTE (<N>)
                                ├── PARK (<N>)
                                ├── KILL (<N>)
                                ├── NEEDS_MORE_EVIDENCE (<N>)
                                └── REVISIT_LATER (<N>)
                                      └── founder-promoted opportunities (<N>)
```

**Template skeleton:**

```markdown
## 3. Evidence Volume and Funnel

### Volume Counts

| Stage | Count |
|-------|-------|
| Raw evidence collected | `<raw_evidence_count>` |
| Accepted candidate signals | `<accepted_signal_count>` |
| Weak signals | `<weak_signal_count>` |
| Noise signals | `<noise_signal_count>` |
| Pain clusters | `<pain_cluster_count>` |
| Opportunity candidates | `<opportunity_candidate_count>` |
| Founder review items | `<reviewed_item_count>` |
| PROMOTE | `<promote_count>` |
| PARK | `<park_count>` |
| KILL | `<kill_count>` |
| NEEDS_MORE_EVIDENCE | `<needs_more_evidence_count>` |
| REVISIT_LATER | `<revisit_later_count>` |

### Pipeline Funnel

```
raw evidence (<raw_evidence_count>)
  └── candidate signals (<candidate_signal_count>)
        ├── accepted (<accepted_signal_count>)
        ├── weak (<weak_signal_count>)
        └── noise (<noise_signal_count>)
              └── pain clusters (<pain_cluster_count>)
                    └── opportunity candidates (<opportunity_candidate_count>)
                          └── founder review (<reviewed_item_count> items)
                                ├── PROMOTE (<promote_count>)
                                ├── PARK (<park_count>)
                                ├── KILL (<kill_count>)
                                ├── NEEDS_MORE_EVIDENCE (<needs_more_evidence_count>)
                                └── REVISIT_LATER (<revisit_later_count>)
                                      └── founder-promoted opportunities (<promote_count>)
```
```

---

### Section 4 — Source Quality by Source

**Purpose:** Per-source breakdown of evidence quality, signal rates, noise rates, and recommendations.

**Required per-source metrics:**

| # | Metric | `hacker_news` | `github_issues` |
|---|--------|---------------|-----------------|
| 1 | Records collected | `<n>` | `<n>` |
| 2 | Accepted signals | `<n>` | `<n>` |
| 3 | Weak signals | `<n>` | `<n>` |
| 4 | Noise signals | `<n>` | `<n>` |
| 5 | Acceptance rate | `<x.x>` | `<x.x>` |
| 6 | Noise rate | `<x.x>` | `<x.x>` |
| 7 | Missing URL count | `<n>` | `<n>` |
| 8 | Placeholder URL count | `<n>` | `<n>` |
| 9 | Quality flags | `<flags>` | `<flags>` |
| 10 | Top noise categories | `<categories>` | `<categories>` |
| 11 | Useful query buckets/repos | `<buckets>` | `<repos>` |
| 12 | Bad query buckets/repos | `<buckets>` | `<repos>` |
| 13 | Recommended changes | `<recommendations>` | `<recommendations>` |

**Template skeleton:**

```markdown
## 4. Source Quality by Source

### Hacker News (`hacker_news`)

| Metric | Value |
|--------|-------|
| Records collected | `<n>` |
| Accepted signals | `<n>` |
| Weak signals | `<n>` |
| Noise signals | `<n>` |
| Acceptance rate | `<x.x>` |
| Noise rate | `<x.x>` |
| Missing URL count | `<n>` |
| Placeholder URL count | `<n>` |
| Quality flags | `<flags>` |
| Top noise categories | `<categories>` |
| Useful query buckets | `<buckets>` |
| Bad query buckets | `<buckets>` |
| Recommended changes | `<recommendations>` |

### GitHub Issues (`github_issues`)

| Metric | Value |
|--------|-------|
| Records collected | `<n>` |
| Accepted signals | `<n>` |
| Weak signals | `<n>` |
| Noise signals | `<n>` |
| Acceptance rate | `<x.x>` |
| Noise rate | `<x.x>` |
| Missing URL count | `<n>` |
| Placeholder URL count | `<n>` |
| Quality flags | `<flags>` |
| Top noise categories | `<categories>` |
| Useful repos | `<repos>` |
| Bad repos | `<repos>` |
| Recommended changes | `<recommendations>` |

### Source Quality Summary

<one-paragraph assessment of which sources worked and which need tuning>
```

---

### Section 5 — Top PainClusters

**Purpose:** Detailed review of the highest-scoring pain clusters.

**Required fields per cluster:**

| # | Field | Description |
|---|-------|-------------|
| 1 | `cluster_id` | Stable cluster identifier, format `pc_<16char_hex>` |
| 2 | `title` / short name | Human-readable cluster label |
| 3 | `actor` | Who experiences the pain |
| 4 | `workflow` | The task or workflow being disrupted |
| 5 | `object` | The tool, system, or process causing the pain |
| 6 | `pain_pattern` | Normalized pain statement |
| 7 | `overall_score` | Overall cluster score (0.0–1.0) |
| 8 | `source_diversity` | Count of distinct source types |
| 9 | `recurrence` | Number of distinct evidence items |
| 10 | `business_relevance` | 0.0–1.0 business relevance estimate |
| 11 | `noise_risk` | 0.0–1.0 noise risk estimate |
| 12 | `evidence_links_count` | Number of source URLs supporting this cluster |
| 13 | `source_ids` | Source identifiers for evidence |
| 14 | `founder_judgment` | Founder decision: PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER / pending |
| 15 | `notes` | Founder or system notes |

**Template skeleton:**

```markdown
## 5. Top PainClusters

### Cluster 1: `<title>` (`<cluster_id>`)

| Field | Value |
|-------|-------|
| **Cluster ID** | `<cluster_id>` |
| **Title** | `<title>` |
| **Actor** | `<actor>` |
| **Workflow** | `<workflow>` |
| **Object** | `<object>` |
| **Pain Pattern** | `<pain_pattern>` |
| **Overall Score** | `<overall_score>` |
| **Source Diversity** | `<source_diversity>` |
| **Recurrence** | `<recurrence>` |
| **Business Relevance** | `<business_relevance>` |
| **Noise Risk** | `<noise_risk>` |
| **Evidence Links** | `<evidence_links_count>` |
| **Source IDs** | `<source_ids>` |
| **Founder Judgment** | `<founder_judgment>` |
| **Notes** | `<notes>` |

### Cluster 2: `<title>` (`<cluster_id>`)
...

### Cluster N: `<title>` (`<cluster_id>`)
...

### Cluster Score Distribution

| Metric | Value |
|--------|-------|
| Min score | `<min>` |
| Max score | `<max>` |
| Median score | `<median>` |
| Mean score | `<mean>` |
| Clusters >= 0.70 (candidate tier) | `<count>` |
| Clusters 0.50–0.69 (weak tier) | `<count>` |
| Clusters < 0.50 (noise/park tier) | `<count>` |
```

---

### Section 6 — Opportunity Candidates

**Purpose:** List and describe all opportunity candidates framed from top-scoring clusters.

**Required fields per candidate:**

| # | Field | Description |
|---|-------|-------------|
| 1 | `opportunity_id` | Stable identifier, format `oppc_<8char_hex>` |
| 2 | `linked_cluster_id` | Source PainCluster ID |
| 3 | `problem_statement` | One-paragraph problem description |
| 4 | `target_icp` | Which ICP segment this addresses |
| 5 | `evidence_summary` | Summary of the supporting evidence |
| 6 | `score` | Inherited from parent cluster `overall_score` |
| 7 | `uncertainty` | Evidence confidence: `low`, `moderate`, `high` |
| 8 | `suggested_validation_action` | Recommended next step |
| 9 | `founder_decision` | PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER / pending |
| 10 | `founder_rationale` | One-sentence explanation |
| 11 | `next_action` | Concrete next step |

**Template skeleton:**

```markdown
## 6. Opportunity Candidates

### Candidate 1: `<opportunity_id>`

| Field | Value |
|-------|-------|
| **Opportunity ID** | `<opportunity_id>` |
| **Linked Cluster** | `<linked_cluster_id>` |
| **Problem Statement** | `<problem_statement>` |
| **Target ICP** | `<target_icp>` |
| **Evidence Summary** | `<evidence_summary>` |
| **Score** | `<score>` |
| **Uncertainty** | `<uncertainty>` |
| **Suggested Validation** | `<suggested_validation_action>` |
| **Founder Decision** | `<founder_decision>` |
| **Founder Rationale** | `<founder_rationale>` |
| **Next Action** | `<next_action>` |

### Candidate 2: `<opportunity_id>`
...

### Candidate N: `<opportunity_id>`
...

### Candidates Summary

| Metric | Count |
|--------|-------|
| Total candidates | `<n>` |
| PROMOTEd | `<n>` |
| PARKed | `<n>` |
| KILLed | `<n>` |
| NEEDS_MORE_EVIDENCE | `<n>` |
| REVISIT_LATER | `<n>` |
| Pending review | `<n>` |
```

---

### Section 7 — Founder Review Outcomes

**Purpose:** Summarize founder decisions, alignment with system recommendations, and review experience.

**Required summary:**

| # | Metric | Count |
|---|--------|-------|
| 1 | Total reviewed items | `<n>` |
| 2 | PROMOTE | `<n>` |
| 3 | PARK | `<n>` |
| 4 | KILL | `<n>` |
| 5 | NEEDS_MORE_EVIDENCE | `<n>` |
| 6 | REVISIT_LATER | `<n>` |
| 7 | System-founder match | `<n>` |
| 8 | System-founder partial match | `<n>` |
| 9 | System-founder mismatch | `<n>` |
| 10 | Match rate | `<n>%` |
| 11 | Review time (minutes) | `<n>` |
| 12 | Review burden assessment | `<summary>` |

**Template skeleton:**

```markdown
## 7. Founder Review Outcomes

### Decision Summary

| Decision | Count |
|----------|-------|
| PROMOTE | `<n>` |
| PARK | `<n>` |
| KILL | `<n>` |
| NEEDS_MORE_EVIDENCE | `<n>` |
| REVISIT_LATER | `<n>` |
| **Total Reviewed** | `<n>` |

### System-Founder Alignment

| Alignment | Count |
|-----------|-------|
| Match | `<n>` |
| Partial match | `<n>` |
| Mismatch | `<n>` |
| **Match rate** | `<n>%` |

### Review Experience

| Metric | Value |
|--------|-------|
| Review time (minutes) | `<n>` |
| Review manageable in 2h? | `<yes/no>` |
| Items understandable? | `<yes/partially/no>` |
| Evidence links useful? | `<yes/partially/no>` |
| Scoring helpful or distracting? | `<helped/neutral/distracted>` |
| Source Quality Report helpful? | `<yes/partially/no>` |
| Manual trash sorting burden? | `<yes/some/no>` |
| Approximate noise % | `<n>%` |

### Top 1–2 Ideas Worth Validation

1. `<title>` — validation action: `<action>`, rationale: `<rationale>`
2. `<title>` — validation action: `<action>`, rationale: `<rationale>`

*(If none, state: "No ideas met the validation threshold.")*
```

---

### Section 8 — Noise and Failure Analysis

**Purpose:** Structured diagnosis of what produced noise and where the pipeline failed.

**Required sub-sections:**

1. **Top noise categories** — list of `{category, count, source, example}`.
2. **Source/query/repo causes** — which specific queries or repos produced the most noise.
3. **Scoring failures** — where scores contradicted evidence quality or founder judgment.
4. **Clustering failures** — where clusters merged unrelated pains or split the same pain.
5. **Abstract/generic candidate issues** — which candidates were too vague to act on.
6. **Traceability issues** — any missing or placeholder URLs discovered.
7. **Review package friction** — what made the review package hard to use.
8. **Manual trash-sorting symptoms** — approximate % of items that were obvious noise requiring no thought to discard.

**Template skeleton:**

```markdown
## 8. Noise and Failure Analysis

### Top Noise Categories

| Category | Count | Source | Example |
|----------|-------|--------|---------|
| `<category>` | `<n>` | `<source>` | `<example>` |
| ... | ... | ... | ... |

### Source/Query/Repo Noise Causes

- **Hacker News:** `<which query buckets produced most noise; why>`
- **GitHub Issues:** `<which repos produced most noise; why>`

### Scoring Failures

<description of any systematic scoring issues; "none identified" if scoring was aligned>

### Clustering Failures

<description of any clustering issues: over-merge, under-merge, generic clusters>

### Abstract/Generic Candidate Issues

<list of candidates that were too abstract to act on, with reasons>

### Traceability Issues

<list of any traceability failures found; "none — traceability clean" if clean>

### Review Package Friction

<what made the review package hard to use: too many items, poor ordering, missing context>

### Manual Trash-Sorting Symptoms

<approximate % of items that were obvious noise; whether review felt like trash sorting>
```

---

### Section 9 — Validation Readiness of Top Ideas

**Purpose:** For each PROMOTEd or NEEDS_MORE_EVIDENCE item, define concrete validation steps.

**Required per item:**

| # | Field | Description |
|---|-------|-------------|
| 1 | `item_id` | `review_item_id` or `opportunity_id` |
| 2 | `title` | Short title |
| 3 | `validation_method` | One of: `interview`, `landing_page`, `manual_research`, `collect_more_evidence`, `check_competitors`, `inspect_github_repos`, `search_more_sources` |
| 4 | `next_steps` | 1–3 concrete actions |
| 5 | `expected_effort` | Estimated time/effort (e.g., "2–3 hours", "1 day") |
| 6 | `what_would_prove_it` | What evidence would confirm this is worth pursuing |
| 7 | `what_would_disprove_it` | What evidence would kill this idea |
| 8 | `owner` | Who is responsible (founder / delegated) |
| 9 | `follow_up_status` | `planned`, `in_progress`, `completed`, `blocked` |

**Template skeleton:**

```markdown
## 9. Validation Readiness of Top Ideas

### Item 1: `<title>` (`<item_id>`)

| Field | Value |
|-------|-------|
| **Validation Method** | `<validation_method>` |
| **Next Steps** | 1. `<step 1>` 2. `<step 2>` 3. `<step 3>` |
| **Expected Effort** | `<expected_effort>` |
| **What Would Prove It** | `<what_would_prove_it>` |
| **What Would Disprove It** | `<what_would_disprove_it>` |
| **Owner** | `<owner>` |
| **Follow-Up Status** | `<follow_up_status>` |

### Item 2: `<title>` (`<item_id>`)
...

*(If no items require validation, state: "No items reached validation readiness.")*
```

---

### Section 10 — Pilot Success / Failure Criteria Check

**Purpose:** Compare actual results against the Pilot Cycle 1 Brief success/failure criteria.

**Criteria check table (from Pilot Cycle 1 Brief, Sections 5–6):**

| # | Criterion | Threshold | Actual | Met? |
|---|-----------|-----------|--------|------|
| SC-1 | Actionable opportunity candidates | 1–2 specific enough to consider validation | `<actual>` | `<yes/no>` |
| SC-2 | Clean traceability | Zero placeholder/missing URLs | `<actual>` | `<yes/no>` |
| SC-3 | Manageable founder review | Review completes <2 hours | `<actual>` | `<yes/no>` |
| SC-4 | Diagnosable noise | Noise <60% OR Source Quality Report identifies noise sources | `<actual>` | `<yes/no>` |
| SC-5 | Useful Source Quality Report | Report identifies useful vs. noisy sources/queries | `<actual>` | `<yes/no>` |
| SC-6 | Non-banal clusters | Clusters are specific, not generic | `<actual>` | `<yes/no>` |
| SC-7 | Scoring aligns with founder judgment | Majority of scored items match founder assessment | `<actual>` | `<yes/no>` |

**Volume target check (from Pilot Cycle 1 Brief, Section 4):**

| Metric | Target | Minimum | Actual | Met? |
|--------|--------|---------|--------|------|
| Raw evidence items | 50–150 | 50 (dry: 10–25) | `<n>` | `<yes/no>` |
| Candidate signals | 10–30 | 10 (dry: 3–10) | `<n>` | `<yes/no>` |
| Pain clusters | 3–7 | 3 (dry: 2–4) | `<n>` | `<yes/no>` |
| Opportunity candidates | 3–5 | 3 (dry: 1) | `<n>` | `<yes/no>` |
| Ideas worth validation | 1–2 | 1 | `<n>` | `<yes/no>` |

**Template skeleton:**

```markdown
## 10. Pilot Success / Failure Criteria Check

### Success Criteria (from Pilot Cycle 1 Brief)

| # | Criterion | Threshold | Actual | Met? |
|---|-----------|-----------|--------|------|
| SC-1 | Actionable candidates | 1–2 specific | `<actual>` | `<yes/no>` |
| SC-2 | Clean traceability | Zero missing/placeholder | `<actual>` | `<yes/no>` |
| SC-3 | Manageable review | <2 hours | `<actual>` | `<yes/no>` |
| SC-4 | Diagnosable noise | <60% or report identifies | `<actual>` | `<yes/no>` |
| SC-5 | Useful Source Quality Report | Identifies useful/noisy | `<actual>` | `<yes/no>` |
| SC-6 | Non-banal clusters | Specific, not generic | `<actual>` | `<yes/no>` |
| SC-7 | Scoring aligns | Majority match founder | `<actual>` | `<yes/no>` |

### Volume Targets

| Metric | Target | Minimum | Actual | Met? |
|--------|--------|---------|--------|------|
| Raw evidence | 50–150 | 50 (dry: 10–25) | `<n>` | `<yes/no>` |
| Candidate signals | 10–30 | 10 (dry: 3–10) | `<n>` | `<yes/no>` |
| Pain clusters | 3–7 | 3 (dry: 2–4) | `<n>` | `<yes/no>` |
| Opportunity candidates | 3–5 | 3 (dry: 1) | `<n>` | `<yes/no>` |
| Ideas worth validation | 1–2 | 1 | `<n>` | `<yes/no>` |

### Criteria Met Summary

- Success criteria met: `<n>` / 7
- Volume targets met: `<n>` / 5
- **Overall:** `<assessment>`
```

---

### Section 11 — Operational Friction

**Purpose:** Document what slowed the cycle, what was unclear, and what should be improved operationally.

**Required friction categories:**

| # | Category | Description |
|---|----------|-------------|
| 1 | Input preparation friction | Issues assembling or validating the input package |
| 2 | Source collection friction | Issues with source collection (live API rate limits, fixture gaps) |
| 3 | Artifact verification friction | Issues verifying pilot outputs |
| 4 | Review friction | Issues during founder review (too many items, poor organization) |
| 5 | Unclear fields | Fields that were confusing or ambiguous during review |
| 6 | Missing data | Data that was expected but absent from outputs |
| 7 | Time spent | Actual time per phase vs. expected |
| 8 | What slowed the cycle | Root causes of delays or inefficiencies |

**Template skeleton:**

```markdown
## 11. Operational Friction

### Input Preparation Friction

<description of issues during input preparation>

### Source Collection Friction

<description of issues during collection>

### Artifact Verification Friction

<description of issues verifying outputs>

### Review Friction

<description of founder review friction>

### Unclear Fields

<list of fields that were confusing or ambiguous>

### Missing Data

<list of expected data that was absent>

### Time Spent

| Phase | Expected | Actual | Notes |
|-------|----------|--------|-------|
| Preparation | 1 day | `<actual>` | `<notes>` |
| Collection / Input Prep | 1–2 days | `<actual>` | `<notes>` |
| Pilot Run + Verification | Same day | `<actual>` | `<notes>` |
| Founder Review | 1–2 days | `<actual>` | `<notes>` |
| Decision + Report | Same day | `<actual>` | `<notes>` |

### What Slowed the Cycle

<root causes of delays or inefficiencies>
```

---

### Section 12 — Preliminary Go / Conditional Go / No-Go Recommendation

**Purpose:** Provide a preliminary recommendation to feed into item 10 (the formal decision). This is **preliminary only** — the founder makes the final decision in item 10.

**Required fields:**

| # | Field | Description |
|---|-------|-------------|
| 1 | `recommended_outcome` | `GO`, `CONDITIONAL GO`, or `NO-GO` |
| 2 | `rationale` | Paragraph explaining why this outcome is recommended |
| 3 | `evidence_supporting` | Specific pilot evidence supporting the recommendation |
| 4 | `risks_uncertainty` | Risks or uncertainties that could change the recommendation |
| 5 | `recommended_next_roadmap` | What the next roadmap should be based on this outcome |

**Template skeleton:**

```markdown
## 12. Preliminary Go / Conditional Go / No-Go Recommendation

> **Note:** This is a preliminary recommendation only. The formal Go/No-Go decision is made in item 10 by the founder.

| Field | Value |
|-------|-------|
| **Recommended Outcome** | `<GO / CONDITIONAL GO / NO-GO>` |
| **Rationale** | `<rationale_paragraph>` |
| **Evidence Supporting** | `<evidence>` |
| **Risks / Uncertainty** | `<risks>` |
| **Recommended Next Roadmap** | `<next_roadmap>` |
```

---

## 4. Metrics Table

The following metrics must be computed and reported in the pilot results report (aggregated or populated from the sections above):

| # | Metric | Type | Description |
|---|--------|------|-------------|
| M1 | `raw_evidence_count` | int | Total raw evidence items collected |
| M2 | `candidate_signal_count` | int | Total candidate signals extracted |
| M3 | `accepted_signal_count` | int | Candidate signals classified as accepted |
| M4 | `weak_signal_count` | int | Candidate signals classified as weak |
| M5 | `noise_signal_count` | int | Candidate signals classified as noise |
| M6 | `pain_cluster_count` | int | Total pain clusters formed |
| M7 | `opportunity_candidate_count` | int | Total opportunity candidates framed |
| M8 | `reviewed_item_count` | int | Total items presented for founder review |
| M9 | `promote_count` | int | Items with PROMOTE decision |
| M10 | `park_count` | int | Items with PARK decision |
| M11 | `kill_count` | int | Items with KILL decision |
| M12 | `needs_more_evidence_count` | int | Items with NEEDS_MORE_EVIDENCE decision |
| M13 | `revisit_later_count` | int | Items with REVISIT_LATER decision |
| M14 | `source_count` | int | Number of distinct sources used |
| M15 | `source_diversity_max` | int | Maximum `source_diversity` across all clusters |
| M16 | `traceability_failure_count` | int | Evidence items with missing or placeholder `source_url` |
| M17 | `missing_source_url_count` | int | Evidence items with empty `source_url` |
| M18 | `placeholder_url_count` | int | Evidence items with placeholder URLs (`urn:oos:*` or similar) |
| M19 | `non_http_url_count` | int | Evidence items with non-`http(s)://` `source_url` |
| M20 | `review_time_minutes` | int | Actual founder review time in minutes |
| M21 | `system_founder_match_rate` | float | Proportion of items where system recommendation matched founder decision (0.0–1.0) |
| M22 | `noise_rate` | float | Proportion of candidate signals classified as noise (0.0–1.0) |
| M23 | `accepted_rate` | float | Proportion of candidate signals classified as accepted (0.0–1.0) |

---

## 5. Decision Interpretation

The following rules guide interpretation of the report for the Go/No-Go decision. These are report-level interpretation guidelines, not automated decision rules.

### 5.1 GO-Leaning Indicators

A **GO** recommendation is supported when:

- **1–2 specific opportunities are PROMOTEd** with clear actor, workflow, ICP, business cost, and reachable validation path.
- **Traceability is clean** — zero missing, placeholder, or malformed URLs.
- **Founder review was manageable** — completed within 2 hours; not trash sorting.
- **Noise is not overwhelming** — noise rate <60%, or noise sources are clearly identified and tunable.
- **Scoring aligns reasonably with founder judgment** — match rate >60%, no systematic divergence.
- **At least one Source Quality Report insight** identifies actionable tuning for the next cycle.

### 5.2 CONDITIONAL GO-Leaning Indicators

A **CONDITIONAL GO** recommendation is supported when:

- **At least one interesting opportunity exists** (PROMOTE or NEEDS_MORE_EVIDENCE with plausible pain).
- **But noise, scoring, or clustering needs fixes** — e.g., noise rate 60–80%, scoring partially misaligned, clusters somewhat generic.
- **Founder review was somewhat burdensome** but produced useful insights.
- **Quality issues are specifically identified** and fixable in a v2.14 quality improvement cycle.
- **Traceability is clean** (broken traceability pushes toward NO-GO).

### 5.3 NO-GO-Leaning Indicators

A **NO-GO** recommendation is supported when:

- **No validatable opportunity** — zero PROMOTE items, nothing passes the "would I test this?" threshold.
- **Mostly noise** — >80% noise rate, banal clusters, abstract candidates.
- **Founder review burden too high** — review took >3 hours, felt like manual trash sorting, no learning.
- **Scoring systematically wrong** — high-scored items are banal, interesting items scored low; match rate <30%.
- **Traceability broken** — placeholder URLs present, evidence chains missing, unresolvable sources.
- **Source Quality Report provides no actionable insight** — metrics exist but don't help decide what to tune.

---

## 6. Report Template Skeleton (Full Markdown)

Below is the complete Markdown template skeleton with all sections and placeholder fields. Copy this skeleton and replace all `<placeholder>` values with actual pilot data.

```markdown
# Pilot Cycle 1 Results Report — OOS v2.13

**Report ID:** `pilot_results_report_<YYYY-MM-DD>_<8char_hex>`
**Run ID:** `<run_id>`
**Created At:** `<ISO 8601 UTC timestamp>`
**Template Version:** `pilot_results_report_template.v1`
**Based On:** Pilot Run Procedure v2.13, Founder Review Protocol v2.13

---

## 1. Executive Summary

| Field | Value |
|-------|-------|
| **Run ID** | `<run_id>` |
| **Run Date** | `<date>` |
| **Input Mode** | `<input_mode>` |
| **Sources Used** | `<sources_used>` |
| **Raw Evidence** | `<raw_evidence_count>` |
| **Candidate Signals** | `<candidate_signal_count>` |
| **Pain Clusters** | `<pain_cluster_count>` |
| **Opportunity Candidates** | `<opportunity_candidate_count>` |
| **Founder Review Completed** | `<founder_review_completed>` |
| **Preliminary Recommendation** | `<preliminary_recommendation>` |

### Summary

<summary_paragraph>

---

## 2. Source Scope and Compliance

| # | Check | Expected | Actual | Pass? |
|---|-------|----------|--------|-------|
| SC-1 | Allowed sources used | `hacker_news`, `github_issues` | `<actual_sources>` | `<pass/fail>` |
| SC-2 | Deferred sources absent | Zero deferred sources | `<count>` | `<pass/fail>` |
| SC-3 | Stack Exchange status | Excluded (or stretch-approved) | `<status>` | `<pass/fail>` |
| SC-4 | Live approvals (if Mode C) | AG-1/AG-2 recorded | `<recorded>` | `<pass/fail>` |
| SC-5 | `output_dir` policy | Explicit dir; no default writes | `<output_dir>` | `<pass/fail>` |
| SC-6 | Commit artifacts approval | AG-5 status | `<status>` | `<pass/fail>` |
| SC-7 | `source_url` traceability | Clean | `<status>` | `<pass/fail>` |

**Compliance notes:** `<notes>`

---

## 3. Evidence Volume and Funnel

### Volume Counts

| Stage | Count |
|-------|-------|
| Raw evidence collected | `<raw_evidence_count>` |
| Accepted candidate signals | `<accepted_signal_count>` |
| Weak signals | `<weak_signal_count>` |
| Noise signals | `<noise_signal_count>` |
| Pain clusters | `<pain_cluster_count>` |
| Opportunity candidates | `<opportunity_candidate_count>` |
| Founder review items | `<reviewed_item_count>` |
| PROMOTE | `<promote_count>` |
| PARK | `<park_count>` |
| KILL | `<kill_count>` |
| NEEDS_MORE_EVIDENCE | `<needs_more_evidence_count>` |
| REVISIT_LATER | `<revisit_later_count>` |

### Pipeline Funnel

```
raw evidence (<raw_evidence_count>)
  └── candidate signals (<candidate_signal_count>)
        ├── accepted (<accepted_signal_count>)
        ├── weak (<weak_signal_count>)
        └── noise (<noise_signal_count>)
              └── pain clusters (<pain_cluster_count>)
                    └── opportunity candidates (<opportunity_candidate_count>)
                          └── founder review (<reviewed_item_count> items)
                                ├── PROMOTE (<promote_count>)
                                ├── PARK (<park_count>)
                                ├── KILL (<kill_count>)
                                ├── NEEDS_MORE_EVIDENCE (<needs_more_evidence_count>)
                                └── REVISIT_LATER (<revisit_later_count>)
                                      └── founder-promoted opportunities (<promote_count>)
```

## 4. Source Quality by Source

### Hacker News (`hacker_news`)

| Metric | Value |
|--------|-------|
| Records collected | `<n>` |
| Accepted signals | `<n>` |
| Weak signals | `<n>` |
| Noise signals | `<n>` |
| Acceptance rate | `<x.x>` |
| Noise rate | `<x.x>` |
| Missing URL count | `<n>` |
| Placeholder URL count | `<n>` |
| Quality flags | `<flags>` |
| Top noise categories | `<categories>` |
| Useful query buckets | `<buckets>` |
| Bad query buckets | `<buckets>` |
| Recommended changes | `<recommendations>` |

### GitHub Issues (`github_issues`)

| Metric | Value |
|--------|-------|
| Records collected | `<n>` |
| Accepted signals | `<n>` |
| Weak signals | `<n>` |
| Noise signals | `<n>` |
| Acceptance rate | `<x.x>` |
| Noise rate | `<x.x>` |
| Missing URL count | `<n>` |
| Placeholder URL count | `<n>` |
| Quality flags | `<flags>` |
| Top noise categories | `<categories>` |
| Useful repos | `<repos>` |
| Bad repos | `<repos>` |
| Recommended changes | `<recommendations>` |

### Source Quality Summary

<one-paragraph assessment>

---

## 5. Top PainClusters

### Cluster 1: `<title>` (`<cluster_id>`)

| Field | Value |
|-------|-------|
| **Cluster ID** | `<cluster_id>` |
| **Title** | `<title>` |
| **Actor** | `<actor>` |
| **Workflow** | `<workflow>` |
| **Object** | `<object>` |
| **Pain Pattern** | `<pain_pattern>` |
| **Overall Score** | `<overall_score>` |
| **Source Diversity** | `<source_diversity>` |
| **Recurrence** | `<recurrence>` |
| **Business Relevance** | `<business_relevance>` |
| **Noise Risk** | `<noise_risk>` |
| **Evidence Links** | `<evidence_links_count>` |
| **Source IDs** | `<source_ids>` |
| **Founder Judgment** | `<founder_judgment>` |
| **Notes** | `<notes>` |

### Cluster 2: `<title>` (`<cluster_id>`)
...

### Cluster N: `<title>` (`<cluster_id>`)
...

### Cluster Score Distribution

| Metric | Value |
|--------|-------|
| Min score | `<min>` |
| Max score | `<max>` |
| Median score | `<median>` |
| Mean score | `<mean>` |
| Clusters >= 0.70 | `<count>` |
| Clusters 0.50–0.69 | `<count>` |
| Clusters < 0.50 | `<count>` |

---

## 6. Opportunity Candidates

### Candidate 1: `<opportunity_id>`

| Field | Value |
|-------|-------|
| **Opportunity ID** | `<opportunity_id>` |
| **Linked Cluster** | `<linked_cluster_id>` |
| **Problem Statement** | `<problem_statement>` |
| **Target ICP** | `<target_icp>` |
| **Evidence Summary** | `<evidence_summary>` |
| **Score** | `<score>` |
| **Uncertainty** | `<uncertainty>` |
| **Suggested Validation** | `<suggested_validation_action>` |
| **Founder Decision** | `<founder_decision>` |
| **Founder Rationale** | `<founder_rationale>` |
| **Next Action** | `<next_action>` |

### Candidate 2: `<opportunity_id>`
...

### Candidates Summary

| Metric | Count |
|--------|-------|
| Total candidates | `<n>` |
| PROMOTEd | `<n>` |
| PARKed | `<n>` |
| KILLed | `<n>` |
| NEEDS_MORE_EVIDENCE | `<n>` |
| REVISIT_LATER | `<n>` |
| Pending review | `<n>` |

---

## 7. Founder Review Outcomes

### Decision Summary

| Decision | Count |
|----------|-------|
| PROMOTE | `<n>` |
| PARK | `<n>` |
| KILL | `<n>` |
| NEEDS_MORE_EVIDENCE | `<n>` |
| REVISIT_LATER | `<n>` |
| **Total Reviewed** | `<n>` |

### System-Founder Alignment

| Alignment | Count |
|-----------|-------|
| Match | `<n>` |
| Partial match | `<n>` |
| Mismatch | `<n>` |
| **Match rate** | `<n>%` |

### Review Experience

| Metric | Value |
|--------|-------|
| Review time (minutes) | `<n>` |
| Review manageable in 2h? | `<yes/no>` |
| Items understandable? | `<yes/partially/no>` |
| Evidence links useful? | `<yes/partially/no>` |
| Scoring helpful or distracting? | `<helped/neutral/distracted>` |
| Source Quality Report helpful? | `<yes/partially/no>` |
| Manual trash sorting burden? | `<yes/some/no>` |
| Approximate noise % | `<n>%` |

### Top 1–2 Ideas Worth Validation

1. `<title>` — validation action: `<action>`, rationale: `<rationale>`
2. `<title>` — validation action: `<action>`, rationale: `<rationale>`

---

## 8. Noise and Failure Analysis

### Top Noise Categories

| Category | Count | Source | Example |
|----------|-------|--------|---------|
| `<category>` | `<n>` | `<source>` | `<example>` |

### Source/Query/Repo Noise Causes

- **Hacker News:** `<analysis>`
- **GitHub Issues:** `<analysis>`

### Scoring Failures

`<description or "none identified">`

### Clustering Failures

`<description or "none identified">`

### Abstract/Generic Candidate Issues

`<list or "none identified">`

### Traceability Issues

`<list or "none — traceability clean">`

### Review Package Friction

`<description>`

### Manual Trash-Sorting Symptoms

`<description; approximate noise %>`

---

## 9. Validation Readiness of Top Ideas

### Item 1: `<title>` (`<item_id>`)

| Field | Value |
|-------|-------|
| **Validation Method** | `<validation_method>` |
| **Next Steps** | 1. `<step 1>` 2. `<step 2>` 3. `<step 3>` |
| **Expected Effort** | `<expected_effort>` |
| **What Would Prove It** | `<what_would_prove_it>` |
| **What Would Disprove It** | `<what_would_disprove_it>` |
| **Owner** | `<owner>` |
| **Follow-Up Status** | `<follow_up_status>` |

---

## 10. Pilot Success / Failure Criteria Check

### Success Criteria (from Pilot Cycle 1 Brief)

| # | Criterion | Threshold | Actual | Met? |
|---|-----------|-----------|--------|------|
| SC-1 | Actionable candidates | 1–2 specific | `<actual>` | `<yes/no>` |
| SC-2 | Clean traceability | Zero missing/placeholder | `<actual>` | `<yes/no>` |
| SC-3 | Manageable review | <2 hours | `<actual>` | `<yes/no>` |
| SC-4 | Diagnosable noise | <60% or report identifies | `<actual>` | `<yes/no>` |
| SC-5 | Useful Source Quality Report | Identifies useful/noisy | `<actual>` | `<yes/no>` |
| SC-6 | Non-banal clusters | Specific, not generic | `<actual>` | `<yes/no>` |
| SC-7 | Scoring aligns | Majority match founder | `<actual>` | `<yes/no>` |

### Volume Targets

| Metric | Target | Minimum | Actual | Met? |
|--------|--------|---------|--------|------|
| Raw evidence | 50–150 | 50 (dry: 10–25) | `<n>` | `<yes/no>` |
| Candidate signals | 10–30 | 10 (dry: 3–10) | `<n>` | `<yes/no>` |
| Pain clusters | 3–7 | 3 (dry: 2–4) | `<n>` | `<yes/no>` |
| Opportunity candidates | 3–5 | 3 (dry: 1) | `<n>` | `<yes/no>` |
| Ideas worth validation | 1–2 | 1 | `<n>` | `<yes/no>` |

### Criteria Met Summary

- Success criteria met: `<n>` / 7
- Volume targets met: `<n>` / 5
- **Overall:** `<assessment>`

---

## 11. Operational Friction

### Input Preparation Friction

`<description>`

### Source Collection Friction

`<description>`

### Artifact Verification Friction

`<description>`

### Review Friction

`<description>`

### Unclear Fields

`<list>`

### Missing Data

`<list>`

### Time Spent

| Phase | Expected | Actual | Notes |
|-------|----------|--------|-------|
| Preparation | 1 day | `<actual>` | `<notes>` |
| Collection / Input Prep | 1–2 days | `<actual>` | `<notes>` |
| Pilot Run + Verification | Same day | `<actual>` | `<notes>` |
| Founder Review | 1–2 days | `<actual>` | `<notes>` |
| Decision + Report | Same day | `<actual>` | `<notes>` |

### What Slowed the Cycle

`<root causes>`

---

## 12. Preliminary Go / Conditional Go / No-Go Recommendation

> **Note:** This is a preliminary recommendation only. The formal Go/No-Go decision is made in item 10 by the founder.

| Field | Value |
|-------|-------|
| **Recommended Outcome** | `<GO / CONDITIONAL GO / NO-GO>` |
| **Rationale** | `<rationale_paragraph>` |
| **Evidence Supporting** | `<evidence>` |
| **Risks / Uncertainty** | `<risks>` |
| **Recommended Next Roadmap** | `<next_roadmap>` |

---

## Appendix A: Metrics Summary

| # | Metric | Value |
|---|--------|-------|
| M1 | `raw_evidence_count` | `<n>` |
| M2 | `candidate_signal_count` | `<n>` |
| M3 | `accepted_signal_count` | `<n>` |
| M4 | `weak_signal_count` | `<n>` |
| M5 | `noise_signal_count` | `<n>` |
| M6 | `pain_cluster_count` | `<n>` |
| M7 | `opportunity_candidate_count` | `<n>` |
| M8 | `reviewed_item_count` | `<n>` |
| M9 | `promote_count` | `<n>` |
| M10 | `park_count` | `<n>` |
| M11 | `kill_count` | `<n>` |
| M12 | `needs_more_evidence_count` | `<n>` |
| M13 | `revisit_later_count` | `<n>` |
| M14 | `source_count` | `<n>` |
| M15 | `source_diversity_max` | `<n>` |
| M16 | `traceability_failure_count` | `<n>` |
| M17 | `missing_source_url_count` | `<n>` |
| M18 | `placeholder_url_count` | `<n>` |
| M19 | `non_http_url_count` | `<n>` |
| M20 | `review_time_minutes` | `<n>` |
| M21 | `system_founder_match_rate` | `<x.x>` |
| M22 | `noise_rate` | `<x.x>` |
| M23 | `accepted_rate` | `<x.x>` |

---

*Pilot Results Report Template v2.13. Operational report template. Does not create the actual pilot results report. Does not run the pilot. Does not create founder decisions, KillReason records, or portfolio mutations.*
```

---

## 7. JSON Companion Structure

An optional JSON companion may accompany the Markdown report. The structure mirrors the report sections for machine readability.

```json
{
  "report_id": "pilot_results_report_<YYYY-MM-DD>_<8char_hex>",
  "run_id": "<run_id>",
  "created_at": "<ISO 8601 UTC>",
  "template_version": "pilot_results_report_template.v1",
  "input_mode": "<Mode A | Mode B | Mode C>",
  "source_scope": {
    "allowed_sources": ["hacker_news", "github_issues"],
    "sources_used": ["<source_id>"],
    "deferred_sources_present": false,
    "stack_exchange_included": false,
    "live_approvals_used": ["<AG-1/AG-2 if applicable>"]
  },
  "metrics": {
    "raw_evidence_count": 0,
    "candidate_signal_count": 0,
    "accepted_signal_count": 0,
    "weak_signal_count": 0,
    "noise_signal_count": 0,
    "pain_cluster_count": 0,
    "opportunity_candidate_count": 0,
    "reviewed_item_count": 0,
    "promote_count": 0,
    "park_count": 0,
    "kill_count": 0,
    "needs_more_evidence_count": 0,
    "revisit_later_count": 0,
    "source_count": 0,
    "source_diversity_max": 0,
    "traceability_failure_count": 0,
    "missing_source_url_count": 0,
    "placeholder_url_count": 0,
    "non_http_url_count": 0,
    "review_time_minutes": 0,
    "system_founder_match_rate": 0.0,
    "noise_rate": 0.0,
    "accepted_rate": 0.0
  },
  "source_quality_summary": {
    "hacker_news": {
      "records_collected": 0,
      "accepted_count": 0,
      "weak_count": 0,
      "noise_count": 0,
      "acceptance_rate": 0.0,
      "noise_rate": 0.0,
      "missing_url_count": 0,
      "placeholder_url_count": 0,
      "quality_flags": [],
      "top_noise_categories": [],
      "useful_query_buckets": [],
      "bad_query_buckets": [],
      "recommended_changes": ""
    },
    "github_issues": {
      "records_collected": 0,
      "accepted_count": 0,
      "weak_count": 0,
      "noise_count": 0,
      "acceptance_rate": 0.0,
      "noise_rate": 0.0,
      "missing_url_count": 0,
      "placeholder_url_count": 0,
      "quality_flags": [],
      "top_noise_categories": [],
      "useful_repos": [],
      "bad_repos": [],
      "recommended_changes": ""
    }
  },
  "top_pain_clusters": [
    {
      "cluster_id": "",
      "title": "",
      "actor": "",
      "workflow": "",
      "object": "",
      "pain_pattern": "",
      "overall_score": 0.0,
      "source_diversity": 0,
      "recurrence": 0,
      "business_relevance": 0.0,
      "noise_risk": 0.0,
      "evidence_links_count": 0,
      "source_ids": [],
      "founder_judgment": "",
      "notes": ""
    }
  ],
  "opportunity_candidates": [
    {
      "opportunity_id": "",
      "linked_cluster_id": "",
      "problem_statement": "",
      "target_icp": "",
      "evidence_summary": "",
      "score": 0.0,
      "uncertainty": "",
      "suggested_validation_action": "",
      "founder_decision": "",
      "founder_rationale": "",
      "next_action": ""
    }
  ],
  "founder_review_summary": {
    "total_reviewed": 0,
    "promote_count": 0,
    "park_count": 0,
    "kill_count": 0,
    "needs_more_evidence_count": 0,
    "revisit_later_count": 0,
    "system_founder_match_count": 0,
    "system_founder_partial_match_count": 0,
    "system_founder_mismatch_count": 0,
    "match_rate": 0.0,
    "review_time_minutes": 0,
    "review_manageable": true,
    "top_ideas_worth_validation": []
  },
  "noise_analysis": {
    "top_noise_categories": [],
    "source_noise_causes": {},
    "scoring_failures": "",
    "clustering_failures": "",
    "abstract_candidate_issues": [],
    "traceability_issues": [],
    "review_package_friction": "",
    "trash_sorting_symptoms": ""
  },
  "validation_readiness": [
    {
      "item_id": "",
      "title": "",
      "validation_method": "",
      "next_steps": [],
      "expected_effort": "",
      "what_would_prove_it": "",
      "what_would_disprove_it": "",
      "owner": "",
      "follow_up_status": ""
    }
  ],
  "criteria_check": {
    "success_criteria_met": 0,
    "success_criteria_total": 7,
    "volume_targets_met": 0,
    "volume_targets_total": 5,
    "overall_assessment": ""
  },
  "operational_friction": {
    "input_preparation_friction": "",
    "source_collection_friction": "",
    "artifact_verification_friction": "",
    "review_friction": "",
    "unclear_fields": [],
    "missing_data": [],
    "time_spent": {},
    "what_slowed_cycle": ""
  },
  "preliminary_recommendation": {
    "outcome": "",
    "rationale": "",
    "evidence_supporting": "",
    "risks_uncertainty": "",
    "recommended_next_roadmap": ""
  },
  "warnings": [],
  "errors": []
}
```

---

## 8. Artifact and Commit Policy

### 8.1 Core Rules

| # | Rule |
|---|------|
| 1 | The **actual pilot results report** (populated with runtime data) is a **runtime/output artifact**. |
| 2 | Runtime pilot outputs must **not be committed** to the repository unless explicitly approved by the founder (AG-5). |
| 3 | This **template** is a documentation artifact and may be committed as part of item 8. |
| 4 | The final v2.13 checkpoint (item 11) may commit a **dev ledger summary**, not raw runtime artifacts by default. |
| 5 | If sample/evidence artifacts are committed, they require **explicit founder approval** (AG-5) and must be documented as such. |
| 6 | The populated report must be written to the explicit `output_dir`, not to any default repository path. |

### 8.2 Template vs. Populated Report

| Artifact | Status | Commit Policy |
|----------|--------|---------------|
| `pilot_results_report_template_v2_13.md` (this file) | Documentation template | **Commit** as part of item 8 |
| `pilot_results_report_v2_13.md` (populated with actual data) | Runtime artifact | **Do not commit** unless AG-5 approved |
| `pilot_results_report_v2_13.json` (JSON companion, populated) | Runtime artifact | **Do not commit** unless AG-5 approved |

---

## 9. Self-Audit Checklist

- [ ] **Title and status present** (header): Title, status, roadmap item, branch, based-on references
- [ ] **Purpose stated** (Section 1): What the template is and is not
- [ ] **Required inputs listed** (Section 2): 14 expected input artifacts
- [ ] **Report sections defined** (Section 3): 12 sections enumerated
- [ ] **Section 1 — Executive Summary** defined: 11 required fields with template skeleton
- [ ] **Section 2 — Source Scope and Compliance** defined: 7 checks with template skeleton
- [ ] **Section 3 — Evidence Volume and Funnel** defined: 12 stage counts with funnel diagram and template
- [ ] **Section 4 — Source Quality by Source** defined: 13 per-source metrics with template skeleton
- [ ] **Section 5 — Top PainClusters** defined: 15 fields per cluster with template skeleton
- [ ] **Section 6 — Opportunity Candidates** defined: 11 fields per candidate with template skeleton
- [ ] **Section 7 — Founder Review Outcomes** defined: decision summary, alignment, review experience, top ideas
- [ ] **Section 8 — Noise and Failure Analysis** defined: 8 sub-sections with template skeleton
- [ ] **Section 9 — Validation Readiness of Top Ideas** defined: 9 fields per item with template skeleton
- [ ] **Section 10 — Pilot Success/Failure Criteria Check** defined: 7 success criteria + 5 volume targets
- [ ] **Section 11 — Operational Friction** defined: 8 categories with time-spent table
- [ ] **Section 12 — Preliminary Go/No-Go Recommendation** defined: 5 fields with template skeleton
- [ ] **Metrics table defined** (Section 4): 23 metrics with types
- [ ] **Decision interpretation defined** (Section 5): GO, CONDITIONAL GO, NO-GO leaning indicators
- [ ] **Report template skeleton provided** (Section 6): Full Markdown skeleton with all placeholder fields
- [ ] **JSON companion structure defined** (Section 7): Full JSON schema with all nested objects
- [ ] **Artifact and commit policy defined** (Section 8): 6 core rules, template vs. populated distinction
- [ ] **All placeholder fields use clear `<placeholder>` syntax**
- [ ] **No actual pilot data filled in** — this is a template only
- [ ] **No source code, test, script, or artifact modifications**
- [ ] **No runtime artifacts created**
- [ ] **No founder decisions created**
- [ ] **No KillReason records created**
- [ ] **No portfolio mutations**

---

## 10. Definition of Done

Item 8 (Pilot Results Report) is done when:

- [ ] **10.1** Pilot Results Report Template exists at `docs/decisions/pilot_results_report_template_v2_13.md`.
- [ ] **10.2** Required inputs are listed (Section 2): 14 expected input artifacts.
- [ ] **10.3** Required sections are defined (Section 3): 12 sections with all sub-fields.
- [ ] **10.4** Metrics table is defined (Section 4): 23 metrics with types.
- [ ] **10.5** Success/failure criteria check is defined (Section 10): 7 success criteria + 5 volume targets.
- [ ] **10.6** Preliminary Go/No-Go interpretation is defined (Section 5): GO, CONDITIONAL GO, NO-GO leaning indicators.
- [ ] **10.7** Markdown skeleton exists (Section 6): Full report template with placeholder fields.
- [ ] **10.8** JSON companion structure defined (Section 7): Full JSON schema.
- [ ] **10.9** Artifact/commit policy clear (Section 8): Template vs. populated report distinction.
- [ ] **10.10** `.\scripts\dev-git-check.ps1` passes.
- [ ] **10.11** Roadmap item 8 marked complete in the v2.13 checklist.
- [ ] **10.12** One local commit exists with message: `[v2.13] 8 define pilot results report`.

---

## 11. References

- [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md) — ICP definitions, excluded markets, relevance signals, noise definitions, review rubric
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md) — success/failure criteria, timebox, decision outcomes, evidence volume targets
- [Pilot Run Procedure v2.13](pilot_run_procedure_v2_13.md) — execution path, artifact verification, handoff to founder review
- [Founder Review Protocol v2.13](founder_review_protocol_v2_13.md) — review order, decision definitions, scoring rubric, alignment check, burden assessment
- [Operational Discovery Pilot Run Contract](../contracts/operational_discovery_pilot_run_contract.md) — pilot run lifecycle, source quality report structure, success/failure criteria
- [PainCluster Contract](../contracts/pain_cluster_contract.md) — cluster schema, scoring formula, status lifecycle, promotion rules
- [OOS Roadmap v2.13 Checklist](../roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md) — parent roadmap

---

*Pilot Results Report Template v2.13. Operational report template. Does not create the actual pilot results report. Does not run the pilot. Does not create founder decisions, KillReason records, or portfolio mutations. Does not modify source code, tests, scripts, or pipeline behavior.*
